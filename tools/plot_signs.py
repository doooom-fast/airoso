"""Top-down pictures of the W1-6 sign placement — Kevin, 2026-10-10: "it's hard to describe but
very easy to see when it's right or wrong". One PNG per sign (120 m window) + one track overview,
drawn for someone who thinks in maps, not meshes: pavement, sidewalk band, median island, where
the driver comes from, the NEW sign (bold yellow plate, post, which way it faces, which way the
arrow points) and the OLD rule's advance-warning point in grey for comparison.

Reads data/signs.local.json (tools/place_signs.py or tools/author_signs_blend.py) plus the
centreline / connectors / median bands. Pillow only (no matplotlib on this box).

Labels never sit on the plate or on each other: every caption is placed by Canvas.label, which
walks a widening ring of offsets around its anchor until the text box clears everything drawn so
far (the header, the footer, the plate, earlier captions) and draws a thin leader back to the
anchor when it had to move — at a tight corner the ray strike, the plate, the facing tick and the
arrow glyph all land within a few metres of each other.

    python tools/plot_signs.py <project-dir> [--out DIR]      (default: <project>/data/signs_plots/)
"""
from __future__ import annotations

import json
import math
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CURB_FACE_W, SIDEWALK_W = 0.08, {"MAINLINE": 1.8, "CONNECTOR": 1.5}
PLATE_W = 1.219
WIN_M, PX_PER_M = 120.0, 8.0
COL = {"grass": (84, 128, 70), "walk": (192, 189, 178), "road": (82, 82, 88), "island": (150, 172, 118),
       "lane": (232, 200, 74), "ray": (235, 60, 50), "driver": (255, 255, 255), "sign": (255, 204, 0),
       "post": (20, 20, 20), "old": (150, 150, 150), "text": (255, 255, 255), "shadow": (0, 0, 0),
       "built": (120, 220, 255), "warn": (255, 190, 120)}
LABEL_RINGS = (8, 18, 30, 46, 66, 90, 120, 160)
LABEL_ANGLES = (0, 45, -45, 90, -90, 135, -135, 180)


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


class Canvas:
    def __init__(self, cx, cz, win_m, px_per_m):
        self.cx, self.cz, self.win, self.s = cx, cz, win_m, px_per_m
        self.W = int(win_m * px_per_m)
        self.img = Image.new("RGB", (self.W, self.W), COL["grass"])
        self.d = ImageDraw.Draw(self.img)
        self.boxes = []          # (x0, y0, x1, y1) rectangles a caption must not cover

    def px(self, p):
        return (int((p[0] - self.cx + self.win / 2) * self.s), int((self.win / 2 - (p[1] - self.cz)) * self.s))

    def inside(self, p, pad=40.0):
        return abs(p[0] - self.cx) < self.win / 2 + pad and abs(p[1] - self.cz) < self.win / 2 + pad

    def clamp(self, q, pad=24):
        return (min(max(q[0], pad), self.W - pad), min(max(q[1], pad), self.W - pad))

    def text(self, xy, s, size=14, bold=False, fill=None):
        f = font(size, bold)
        x, y = xy
        self.d.text((x + 1, y + 1), s, font=f, fill=COL["shadow"])
        self.d.text((x, y), s, font=f, fill=fill or COL["text"])

    def text_size(self, s, size, bold=False):
        x0, y0, x1, y1 = self.d.textbbox((0, 0), s, font=font(size, bold))
        return x1 - x0 + 2, y1 - y0 + 2

    def reserve(self, box):
        self.boxes.append(tuple(box))

    def fits(self, box):
        if box[0] < 2 or box[1] < 2 or box[2] > self.W - 2 or box[3] > self.W - 2:
            return False
        return not any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in self.boxes)

    def label(self, anchor, s, size=13, bold=False, fill=None):
        """a caption near `anchor`, pushed off everything reserved so far; a leader line joins it
        to the anchor once it had to move more than one ring out; reserves its own box"""
        w, h = self.text_size(s, size, bold)
        ax, ay = anchor
        chosen = None
        for r in LABEL_RINGS:
            for ang in LABEL_ANGLES:
                th = math.radians(ang)
                cx, cy = ax + r * math.cos(th), ay + r * math.sin(th)
                bx = cx if math.cos(th) > 0.3 else (cx - w if math.cos(th) < -0.3 else cx - w / 2)
                by = cy if math.sin(th) > 0.3 else (cy - h if math.sin(th) < -0.3 else cy - h / 2)
                box = (bx, by, bx + w, by + h)
                if self.fits(box):
                    chosen = (r, box)
                    break
            if chosen:
                break
        if chosen is None:                       # nothing clears: the first ring, inside the canvas
            bx, by = min(max(ax + 8, 2), self.W - w - 2), min(max(ay - h / 2, 2), self.W - h - 2)
            chosen = (LABEL_RINGS[0], (bx, by, bx + w, by + h))
        r, box = chosen
        if r > LABEL_RINGS[1]:
            lx, ly = min(max(ax, box[0]), box[2]), min(max(ay, box[1]), box[3])
            self.d.line([anchor, (lx, ly)], fill=fill or COL["text"], width=1)
        self.text((box[0] + 1, box[1] + 1), s, size, bold, fill)
        self.reserve(box)
        return box

    def lines(self, y, items, max_chars=150):
        """header / footer prose: (text, size, bold, fill) rows wrapped to the canvas; returns the
        next free y and reserves the block"""
        y0 = y
        for s, size, bold, fill in items:
            for ln in textwrap.wrap(s, max_chars) or [""]:
                self.text((10, y), ln, size, bold, fill)
                y += size + 6
        self.reserve((0, y0 - 2, self.W, y + 2))
        return y

    def arrow(self, a, b, col, width=3, head=10):
        self.d.line([a, b], fill=col, width=width)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for da in (2.6, -2.6):
            self.d.line([b, (b[0] + head * math.cos(ang + da), b[1] + head * math.sin(ang + da))], fill=col, width=width)


DIRECTION_WORDS = {"fwd": "clockwise (increasing vertex index)", "rev": "anticlockwise (decreasing vertex index)"}


def driven_layouts(proj):
    """{"fwd": [layout ids], "rev": [...]} from <proj>/track.config.json layouts[].direction"""
    try:
        cfg = json.loads((Path(proj) / "track.config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for lay in cfg.get("layouts") or []:
        d = {"forward": "fwd", "reverse": "rev"}.get(str(lay.get("direction") or "forward").lower())
        if d:
            out.setdefault(d, []).append(str(lay.get("id")))
    return out


def serves(p, ribbon, driven):
    """which drivers a plate is for, in words (ledger 0051: the mainline is signed both ways; 0054 P4: a layout plate
    is one race layout's own, behind its sealing wall, in its closure kn5)"""
    if p.get("layout"):
        return "%s ONLY (its own plate, behind its sealing wall; ships in its closure kn5)" % p["layout"]
    if ribbon == "north":
        return "%s drivers on the north network (every layout; the turn across the junction pad)" % ("J1 -> J5" if p["direction"] == "fwd" else "J5 -> J1")
    if ribbon != "MAINLINE":
        return "%s approach of a two-way street (every layout)" % ("forward" if p["direction"] == "fwd" else "reverse")
    lays = driven.get(p["direction"], [])
    return "drivers going %s%s" % (DIRECTION_WORDS[p["direction"]].split(" (")[0], (" — " + ", ".join(lays)) if lays else " — no layout drives this way")


PADS = []        # ledger 0054 P4: the junction pads' built decks (pavement polygons), drawn under the ribbons


def load(proj):
    data = Path(proj) / "data"
    signs = json.loads((data / "signs.local.json").read_text(encoding="utf-8"))
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    ribbons = [("MAINLINE", [tuple(p) for p in cl["points_xyz_m"]], list(cl["widths_m"]), True)]
    cp = data / "connectors.local.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            P = [tuple(p) for p in c["points_xyz_m"]]
            ribbons.append((c["name"], P, list(c["widths_m"]), math.dist(P[0][::2], P[-1][::2]) < 1e-6))
    island = []
    mb = data / "median_bands.json"
    if mb.exists():
        isl = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", [])
        island = isl if isinstance(isl, list) else [isl.get(str(i), 0.0) for i in range(len(ribbons[0][1]))]
    # the north network (ledger 0054 P4): the pads' built decks as pavement; the stitched "north" ribbon is the
    # pieces already drawn, so a north sign's own ribbon is never drawn twice
    PADS[:] = []
    pb = data / "pads.built.json"
    if pb.exists():
        for pad in json.loads(pb.read_text(encoding="utf-8")).get("pads", []):
            PADS.append((pad["id"], [tuple(q) for q in pad["outline_xz"]]))
    return signs, ribbons, island


def draw_ribbons(cv, ribbons, island, detail=True):
    for pid, poly in PADS:
        if any(cv.inside(q) for q in poly):
            cv.d.polygon([cv.px(q) for q in poly], fill=COL["road"], outline=COL["walk"])
    layers = [("walk", True), ("road", False), ("island", False), ("lane", False)] if detail else [("road", False)]
    for layer, _ in layers:
        for name, P, W, closed in ribbons:
            walk = CURB_FACE_W + SIDEWALK_W["MAINLINE" if name == "MAINLINE" else "CONNECTOR"]
            n = len(P)
            for i in range(n - 1):
                a, b = P[i], P[i + 1]
                if not (cv.inside((a[0], a[2])) or cv.inside((b[0], b[2]))):
                    continue
                pa, pb = cv.px((a[0], a[2])), cv.px((b[0], b[2]))
                band = {"walk": (W[i] + 2 * walk, COL["walk"]), "road": (W[i], COL["road"]),
                        "island": (island[i] if name == "MAINLINE" and i < len(island) else 0.0, COL["island"])}.get(layer)
                if band and band[0] > 0:
                    wpx = max(1, int(band[0] * cv.s))
                    cv.d.line([pa, pb], fill=band[1], width=wpx)
                    for q in (pa, pb):      # round joints: a thick segment line alone leaves spokes on curves
                        cv.d.ellipse([q[0] - wpx // 2, q[1] - wpx // 2, q[0] + wpx // 2, q[1] + wpx // 2], fill=band[1])
                elif layer == "lane":
                    cv.d.line([pa, pb], fill=COL["lane"], width=1)


def header(cv, s, plates, driven=None):
    c = s["checks"]
    disc = "disc margin %+.2f m" % c["gate_margin_m"]
    if c.get("gate_ribbons", "all") != "all":
        disc += " (own street, logged%s; gated %s %+.2f m)" % (" - WARN" if c["gate_margin_m"] < 0 else "", c["gate_ribbons"], c.get("gate_margin_gated_m", c["gate_margin_m"]))
    else:
        disc += " (every centreline, gated)"
    wb = c.get("walk_behind_m")
    rows = [
        ("%s   %s   %s%s%s" % (s["id"], s["kind"], s.get("where", ""),
                               # signs.json's prose names the FORWARD approach (ledger 0051)
                               "  [named for the forward approach; this plate is for the reverse one]"
                               if s.get("where") and all(p["direction"] == "rev" for p in plates) else "",
                               "   (one post, two plates)" if s.get("pair") else ""), 18, True, None),
        ("corner: R %.0f m at the apex, turns %.0f deg %s   |   approach heading %s deg, plate faces %s deg"
         % (s["corner"]["R_apex_m"], abs(s["corner"]["D_deg"]), s["corner"]["turn"],
            "/".join("%.0f" % p["approach"]["bearing_deg"] for p in plates), "/".join("%.0f" % p["face_bearing_deg"] for p in plates)), 13, False, None),
        ("ray %.0f m to the curb, post %.2f m behind the %s curb face (measured)%s, plate bottom %.2f m up"
         % (plates[0]["ray"].get("len_mesh_m", plates[0]["ray"]["len_m"]), c.get("mesh_clear_m", c["edge_clear_m"]),
            "built" if "mesh_clear_m" in c else "polyline",
            "" if wb is None else (", %.2f m %s the back of the walk" % (abs(wb), "behind" if wb > 0 else "inside")), s["height_m"]), 13, False, None),
        ("lamp %.1f m, plant %.1f m, drive_test %s" % (c["lamp_m"], c["plant_m"], disc), 13, False, None),
    ]
    if driven is not None:
        rows.insert(1, ("for " + " / ".join(serves(p, s["ribbon"], driven) for p in plates), 14, True, COL["sign"]))
    if c.get("warnings"):
        rows.append(("WARN: " + "; ".join(c["warnings"]), 12, False, COL["warn"]))
    return cv.lines(8, rows)


def plot_sign(s, ribbons, island, out_dir, driven=None):
    cx, cz = s["base_xz"]
    cv = Canvas(cx, cz, WIN_M, PX_PER_M)
    draw_ribbons(cv, ribbons, island)
    plates = s.get("plates") or [s]
    W = cv.W
    # furniture first, so every caption keeps off it: header, footer, north arrow, scale bar
    header(cv, s, plates, driven)
    cv.lines(W - 44, [("yellow = the new W1-6 (post, plate, facing)   grey filled = old rule rev1: warning ~52 m BEFORE the bend", 12, False, None),
                      ("grey hollow = old rule rev2: at the apex, side flipped (= inside)   light blue = the built curb from the mesh", 12, False, None)])
    cv.arrow((W - 40, 110), (W - 40, 60), COL["text"], width=3, head=12)
    cv.text((W - 48, 112), "N", 16, bold=True)
    cv.reserve((W - 70, 50, W - 10, 136))
    cv.d.line([(14, W - 60), (14 + int(20 * PX_PER_M), W - 60)], fill=COL["text"], width=4)
    cv.text((14, W - 82), "20 m", 14, bold=True)
    cv.reserve((10, W - 86, 20 + int(20 * PX_PER_M), W - 52))
    # the NEW sign's geometry: post, plate(s) across the driver's right vector, facing tick, arrow
    # glyph — drawn before any caption so the captions keep off them
    b = cv.px((cx, cz))
    hw = PLATE_W * 1.6   # drawn 1.6x so the plate reads at 8 px/m
    cv.reserve((b[0] - 14, b[1] - 14, b[0] + 14, b[1] + 14))
    glyphs, ticks = [], []
    for k, p in enumerate(plates):
        f, r = p["face_dir_xz"], p["right_xz"]
        fp = cv.px((cx + f[0] * 9, cz + f[1] * 9))
        cv.arrow(b, fp, COL["sign"], width=3, head=10)
        ticks.append((fp, p))
        p1, p2 = cv.px((cx + r[0] * hw, cz + r[1] * hw)), cv.px((cx - r[0] * hw, cz - r[1] * hw))
        cv.d.line([p1, p2], fill=COL["post"], width=10)
        cv.d.line([p1, p2], fill=COL["sign"], width=6)
        cv.reserve((min(p1[0], p2[0]) - 6, min(p1[1], p2[1]) - 6, max(p1[0], p2[0]) + 6, max(p1[1], p2[1]) + 6))
        g = 1.0 if p["arrow"] == "right" else -1.0
        ga = cv.px((cx - f[0] * 5 - r[0] * g * 3.0, cz - f[1] * 5 - r[1] * g * 3.0))
        gb = cv.px((cx - f[0] * 5 + r[0] * g * 3.0, cz - f[1] * 5 + r[1] * g * 3.0))
        cv.arrow(ga, gb, COL["sign"], width=5, head=12)
        cv.reserve((min(ga[0], gb[0]) - 8, min(ga[1], gb[1]) - 8, max(ga[0], gb[0]) + 8, max(ga[1], gb[1]) + 8))
        glyphs.append(((ga, gb), p))
    cv.d.ellipse([b[0] - 5, b[1] - 5, b[0] + 5, b[1] + 5], fill=COL["post"], outline=COL["sign"], width=2)
    # the rays and where the driver comes from
    strikes = []
    for k, p in enumerate(plates):
        t = p["approach"]["t_xz"]
        A, C = p["ray"]["A_xz"], p["ray"]["C_xz"]
        tail = (A[0] - t[0] * 45, A[1] - t[1] * 45)
        pa, pb = cv.px(tail), cv.px(A)
        L = math.hypot(pb[0] - pa[0], pb[1] - pa[1]) or 1
        for j in range(0, int(L), 16):
            q0 = (pa[0] + (pb[0] - pa[0]) * j / L, pa[1] + (pb[1] - pa[1]) * j / L)
            q1 = (pa[0] + (pb[0] - pa[0]) * min(j + 9, L) / L, pa[1] + (pb[1] - pa[1]) * min(j + 9, L) / L)
            cv.d.line([q0, q1], fill=COL["driver"], width=3)
        cv.arrow(cv.px((A[0] - t[0] * 12, A[1] - t[1] * 12)), pb, COL["driver"], width=4, head=12)
        C = p["ray"].get("C_mesh_xz", C)      # the built mesh's curb crossing when Blender measured it
        cv.d.line([pb, cv.px(C)], fill=COL["ray"], width=2)
        pc = cv.px(C)
        cv.d.ellipse([pc[0] - 4, pc[1] - 4, pc[0] + 4, pc[1] + 4], outline=COL["ray"], width=2)
        cv.reserve((pc[0] - 6, pc[1] - 6, pc[0] + 6, pc[1] + 6))
        strikes.append((pc, pa, p))
    # the OLD rule's points, grey
    o1 = cv.px(s["old_rule"]["rev1_xz"])
    cv.d.ellipse([o1[0] - 7, o1[1] - 7, o1[0] + 7, o1[1] + 7], fill=COL["old"], outline=COL["post"], width=2)
    cv.reserve((o1[0] - 9, o1[1] - 9, o1[0] + 9, o1[1] + 9))
    o2 = cv.px(s["old_rule"]["rev2_xz"])
    cv.d.ellipse([o2[0] - 6, o2[1] - 6, o2[0] + 6, o2[1] + 6], outline=COL["old"], width=3)
    cv.reserve((o2[0] - 8, o2[1] - 8, o2[0] + 8, o2[1] + 8))
    # the BUILT pavement edge + back of walk (from the Blender pass) — the grey ribbon above is the
    # polyline width, which the swept mesh undercuts at tight apexes
    built = s.get("built") or {}
    for key, col, w in (("outside_edge_xz", COL["built"], 3), ("back_of_walk_xz", (235, 235, 235), 1)):
        pts = [cv.px(p) for p in built.get(key, [])]
        if len(pts) > 1:
            cv.d.line(pts, fill=col, width=w)
    # the un-slid mesh point (the ray strike) when the lamp/plant slide moved the post along the curb
    c = s["checks"]
    slid_pt = None
    if abs(c.get("slid_m", 0.0)) > 0.01 and s.get("curb_dir_xz"):
        u = s["curb_dir_xz"]
        q = cv.px((cx - u[0] * c["slid_m"], cz - u[1] * c["slid_m"]))
        cv.d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], outline=COL["sign"], width=2)
        cv.reserve((q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6))
        slid_pt = q
    # captions, most important first, each pushed off the plate and off the earlier ones
    many = len(plates) > 1
    for fp, p in ticks:
        cv.label(fp, "faces the driver" + (" (%s)" % p["direction"] if many else ""), 13, bold=True, fill=COL["sign"])
    for (ga, gb), p in glyphs:
        anchor = ((ga[0] + gb[0]) / 2, (ga[1] + gb[1]) / 2)
        cv.label(anchor, "arrow points %s (as the %sdriver sees it)" % (p["arrow"].upper(), (p["direction"] + " ") if many else ""), 13, bold=True, fill=COL["sign"])
    for k, (pc, pa, p) in enumerate(strikes):
        if k == 0:
            cv.label(pc, "a car that did not turn crosses the curb here", 12)
    if slid_pt:
        cv.label(slid_pt, "slid %+.2f m along the curb (lamp/plant clearance)" % c["slid_m"], 12, fill=COL["sign"])
    if built.get("outside_edge_xz"):
        e = cv.px(built["outside_edge_xz"][0])
        cv.label(cv.clamp(e), "built curb (mesh)", 12, fill=COL["built"])
    cv.label(o1, "OLD rule (advance warning)", 12, fill=(225, 225, 225))
    for k, (pc, pa, p) in enumerate(strikes):
        cv.label(cv.clamp(pa), "driver comes from here" + (" (%s)" % p["direction"] if many else ""), 15, bold=True)
    p = Path(out_dir) / ("sign_%s.png" % s["id"].replace("/", "_"))
    cv.img.save(p)
    return p


def plot_overview(signs, ribbons, out_dir, max_px=2200, driven=None):
    xs = [p[0] for _, P, _, _ in ribbons for p in P]
    zs = [p[2] for _, P, _, _ in ribbons for p in P]
    x0, x1, z0, z1 = min(xs) - 100, max(xs) + 100, min(zs) - 100, max(zs) + 100
    span = max(x1 - x0, z1 - z0)
    s = max_px / span
    cv = Canvas((x0 + x1) / 2, (z0 + z1) / 2, span, s)
    draw_ribbons(cv, ribbons, [], detail=False)
    driven = driven or {}
    nd = {"fwd": 0, "rev": 0}
    for sg in signs["signs"]:
        if sg["ribbon"] == "MAINLINE":
            for p in sg.get("plates") or [sg]:
                nd[p["direction"]] += 1
    dir_line = ("loop plates: %d for drivers going clockwise (%s), %d anticlockwise (%s, orange ring)"
                % (nd["fwd"], ", ".join(driven.get("fwd", [])) or "-", nd["rev"], ", ".join(driven.get("rev", [])) or "-")) \
        if nd["rev"] or driven.get("rev") else "driving direction on the loop: clockwise (increasing vertex index)"
    cv.lines(10, [("W1-6 Large Arrow signs — %d placed (yellow, arrow = which way the plate faces); hollow grey = detected but skipped" % len(signs["signs"]), 20, True, None),
                  (dir_line, 15, False, None)])
    W = cv.W
    cv.arrow((W - 50, 130), (W - 50, 60), COL["text"], width=4, head=14)
    cv.text((W - 60, 134), "N", 20, bold=True)
    cv.reserve((W - 80, 50, W - 20, 160))
    cv.d.line([(14, W - 24), (14 + int(500 * s), W - 24)], fill=COL["text"], width=5)
    cv.text((14, W - 50), "500 m", 16, bold=True)
    cv.reserve((10, W - 54, 20 + int(500 * s), W - 10))
    for sg in signs["signs"]:
        b = cv.px(sg["base_xz"])
        f = sg["face_dir_xz"]
        cv.arrow(b, cv.px((sg["base_xz"][0] + f[0] * 60, sg["base_xz"][1] + f[1] * 60)), COL["sign"], width=3, head=10)
        cv.d.ellipse([b[0] - 7, b[1] - 7, b[0] + 7, b[1] + 7], fill=COL["sign"], outline=COL["post"], width=2)
        if any(p["direction"] == "rev" for p in sg.get("plates") or [sg]) and sg["ribbon"] == "MAINLINE":
            cv.d.ellipse([b[0] - 11, b[1] - 11, b[0] + 11, b[1] + 11], outline=COL["warn"], width=3)
        cv.reserve((b[0] - 9, b[1] - 9, b[0] + 9, b[1] + 9))
    for sk in signs.get("skipped", []):
        if sk.get("would_be"):
            b = cv.px(sk["would_be"])
            cv.d.ellipse([b[0] - 5, b[1] - 5, b[0] + 5, b[1] + 5], outline=COL["old"], width=2)
    for sg in signs["signs"]:
        cv.label(cv.px(sg["base_xz"]), sg["id"], 15, bold=True, fill=COL["sign"])
    p = Path(out_dir) / "signs_overview.png"
    cv.img.save(p)
    return p


def main():
    argv = sys.argv[1:]
    if not argv:
        raise SystemExit(__doc__)
    proj = Path(argv[0])
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else proj / "data" / "signs_plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    signs, ribbons, island = load(proj)
    driven = driven_layouts(proj)
    paths = [plot_overview(signs, ribbons, out_dir, driven=driven)]
    for s in signs["signs"]:
        paths.append(plot_sign(s, ribbons, island, out_dir, driven))
    print("[plot-signs] %d PNGs -> %s" % (len(paths), out_dir))
    for p in paths:
        print("[plot-signs]  ", p)


if __name__ == "__main__":
    main()

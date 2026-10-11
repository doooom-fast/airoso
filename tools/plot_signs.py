"""Top-down pictures of the W1-6 sign placement — Kevin, 2026-10-10: "it's hard to describe but
very easy to see when it's right or wrong". One PNG per sign (120 m window) + one track overview,
drawn for someone who thinks in maps, not meshes: pavement, sidewalk band, median island, where
the driver comes from, the NEW sign (bold yellow plate, post, which way it faces, which way the
arrow points) and the OLD rule's advance-warning point in grey for comparison.

Reads data/signs.local.json (tools/place_signs.py or tools/author_signs_blend.py) plus the
centreline / connectors / median bands. Pillow only (no matplotlib on this box).

    python tools/plot_signs.py <project-dir> [--out DIR]      (default: <project>/data/signs_plots/)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CURB_FACE_W, SIDEWALK_W = 0.08, {"MAINLINE": 1.8, "CONNECTOR": 1.5}
PLATE_W = 1.219
WIN_M, PX_PER_M = 120.0, 8.0
COL = {"grass": (84, 128, 70), "walk": (192, 189, 178), "road": (82, 82, 88), "island": (150, 172, 118),
       "lane": (232, 200, 74), "ray": (235, 60, 50), "driver": (255, 255, 255), "sign": (255, 204, 0),
       "post": (20, 20, 20), "old": (150, 150, 150), "text": (255, 255, 255), "shadow": (0, 0, 0)}


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

    def px(self, p):
        return (int((p[0] - self.cx + self.win / 2) * self.s), int((self.win / 2 - (p[1] - self.cz)) * self.s))

    def inside(self, p, pad=40.0):
        return abs(p[0] - self.cx) < self.win / 2 + pad and abs(p[1] - self.cz) < self.win / 2 + pad

    def text(self, xy, s, size=14, bold=False, fill=None):
        f = font(size, bold)
        x, y = xy
        self.d.text((x + 1, y + 1), s, font=f, fill=COL["shadow"])
        self.d.text((x, y), s, font=f, fill=fill or COL["text"])

    def arrow(self, a, b, col, width=3, head=10):
        self.d.line([a, b], fill=col, width=width)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for da in (2.6, -2.6):
            self.d.line([b, (b[0] + head * math.cos(ang + da), b[1] + head * math.sin(ang + da))], fill=col, width=width)


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
    return signs, ribbons, island


def draw_ribbons(cv, ribbons, island, detail=True):
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


def plot_sign(s, ribbons, island, out_dir):
    cx, cz = s["base_xz"]
    cv = Canvas(cx, cz, WIN_M, PX_PER_M)
    draw_ribbons(cv, ribbons, island)
    plates = s.get("plates") or [s]
    for k, p in enumerate(plates):
        t = p["approach"]["t_xz"]
        A, C = p["ray"]["A_xz"], p["ray"]["C_xz"]
        # where the driver comes from: the approach heading, dashed back 45 m from the launch point
        tail = (A[0] - t[0] * 45, A[1] - t[1] * 45)
        pa, pb = cv.px(tail), cv.px(A)
        L = math.hypot(pb[0] - pa[0], pb[1] - pa[1]) or 1
        for j in range(0, int(L), 16):
            q0 = (pa[0] + (pb[0] - pa[0]) * j / L, pa[1] + (pb[1] - pa[1]) * j / L)
            q1 = (pa[0] + (pb[0] - pa[0]) * min(j + 9, L) / L, pa[1] + (pb[1] - pa[1]) * min(j + 9, L) / L)
            cv.d.line([q0, q1], fill=COL["driver"], width=3)
        cv.arrow(cv.px((A[0] - t[0] * 12, A[1] - t[1] * 12)), pb, COL["driver"], width=4, head=12)
        cv.text((pa[0] - 40, pa[1] + 8), "driver comes from here" + (" (%s)" % p["direction"] if len(plates) > 1 else ""), 15, bold=True)
        # the failed-to-turn ray: launch point -> the curb crossing (the built mesh's when Blender measured it) -> the sign
        C = p["ray"].get("C_mesh_xz", C)
        cv.d.line([pb, cv.px(C)], fill=COL["ray"], width=2)
        pc = cv.px(C)
        cv.d.ellipse([pc[0] - 4, pc[1] - 4, pc[0] + 4, pc[1] + 4], outline=COL["ray"], width=2)
        if k == 0:
            cv.text((pc[0] + 8, pc[1] - 18), "a car that did not turn crosses the curb here", 12)
    f, r = plates[0]["face_dir_xz"], plates[0]["right_xz"]
    # the OLD rule's points, grey
    o1 = cv.px(s["old_rule"]["rev1_xz"])
    cv.d.ellipse([o1[0] - 7, o1[1] - 7, o1[0] + 7, o1[1] + 7], fill=COL["old"], outline=COL["post"], width=2)
    cv.text((o1[0] + 10, o1[1] - 8), "OLD rule (advance warning)", 12, fill=(225, 225, 225))
    o2 = cv.px(s["old_rule"]["rev2_xz"])
    cv.d.ellipse([o2[0] - 6, o2[1] - 6, o2[0] + 6, o2[1] + 6], outline=COL["old"], width=3)
    # the BUILT pavement edge + back of walk (from the Blender pass) — the grey ribbon above is the
    # polyline width, which the swept mesh undercuts at tight apexes
    built = s.get("built") or {}
    for key, col, w in (("outside_edge_xz", (120, 220, 255), 3), ("back_of_walk_xz", (235, 235, 235), 1)):
        pts = [cv.px(p) for p in built.get(key, [])]
        if len(pts) > 1:
            cv.d.line(pts, fill=col, width=w)
    if built.get("outside_edge_xz"):
        e = cv.px(built["outside_edge_xz"][0])
        cv.text((e[0] + 6, e[1] - 16), "built curb (mesh)", 12, fill=(120, 220, 255))
    # the NEW sign: post, plate(s) across the driver's right vector, facing tick, arrow glyph
    b = cv.px((cx, cz))
    hw = PLATE_W * 1.6   # drawn 1.6x so the plate reads at 8 px/m
    for k, p in enumerate(plates):
        f, r = p["face_dir_xz"], p["right_xz"]
        fp = cv.px((cx + f[0] * 9, cz + f[1] * 9))
        cv.arrow(b, fp, COL["sign"], width=3, head=10)
        cv.text((fp[0] + 6, fp[1] - 8), "faces the driver" + (" (%s)" % p["direction"] if len(plates) > 1 else ""), 13, bold=True, fill=COL["sign"])
        p1, p2 = cv.px((cx + r[0] * hw, cz + r[1] * hw)), cv.px((cx - r[0] * hw, cz - r[1] * hw))
        cv.d.line([p1, p2], fill=COL["post"], width=10)
        cv.d.line([p1, p2], fill=COL["sign"], width=6)
        g = 1.0 if p["arrow"] == "right" else -1.0
        ga = cv.px((cx - f[0] * 5 - r[0] * g * 3.0, cz - f[1] * 5 - r[1] * g * 3.0))
        gb = cv.px((cx - f[0] * 5 + r[0] * g * 3.0, cz - f[1] * 5 + r[1] * g * 3.0))
        cv.arrow(ga, gb, COL["sign"], width=5, head=12)
        cv.text((min(ga[0], gb[0]) - 10, max(ga[1], gb[1]) + 6 + 16 * k), "arrow points %s (as the %sdriver sees it)"
                % (p["arrow"].upper(), (p["direction"] + " ") if len(plates) > 1 else ""), 13, bold=True, fill=COL["sign"])
    cv.d.ellipse([b[0] - 5, b[1] - 5, b[0] + 5, b[1] + 5], fill=COL["post"], outline=COL["sign"], width=2)
    # the un-slid mesh point (the ray strike) when the lamp/plant slide moved the post along the curb
    c = s["checks"]
    if abs(c.get("slid_m", 0.0)) > 0.01 and s.get("curb_dir_xz"):
        u = s["curb_dir_xz"]
        q = cv.px((cx - u[0] * c["slid_m"], cz - u[1] * c["slid_m"]))
        cv.d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], outline=COL["sign"], width=2)
        cv.text((q[0] + 6, q[1] + 4), "slid %+.2f m along the curb (lamp/plant clearance)" % c["slid_m"], 12, fill=COL["sign"])
    # furniture: title, numbers, north, scale
    cv.text((10, 8), "%s   %s   %s%s" % (s["id"], s["kind"], s.get("where", ""), "   (one post, two plates)" if s.get("pair") else ""), 18, bold=True)
    cv.text((10, 34), "corner: R %.0f m at the apex, turns %.0f deg %s   |   approach heading %s deg, plate faces %s deg"
            % (s["corner"]["R_apex_m"], abs(s["corner"]["D_deg"]), s["corner"]["turn"],
               "/".join("%.0f" % p["approach"]["bearing_deg"] for p in plates), "/".join("%.0f" % p["face_bearing_deg"] for p in plates)), 13)
    gate = "drive_test disc margin %+.2f m (plate footprint, every centreline)" % c["gate_margin_m"]
    cv.text((10, 54), "ray %.0f m to the curb, post %.2f m behind the %s curb face (measured), plate bottom %.2f m up   |   lamp %.1f m, plant %.1f m, %s"
            % (plates[0]["ray"].get("len_mesh_m", plates[0]["ray"]["len_m"]), c.get("mesh_clear_m", c["edge_clear_m"]),
               "built" if "mesh_clear_m" in c else "polyline", s["height_m"], c["lamp_m"], c["plant_m"], gate), 13)
    if s["checks"].get("warnings"):
        cv.text((10, 74), "WARN: " + "; ".join(s["checks"]["warnings"]), 12, fill=(255, 190, 120))
    W = cv.W
    cv.arrow((W - 40, 110), (W - 40, 60), COL["text"], width=3, head=12)
    cv.text((W - 48, 112), "N", 16, bold=True)
    cv.d.line([(14, W - 20), (14 + int(20 * PX_PER_M), W - 20)], fill=COL["text"], width=4)
    cv.text((14, W - 42), "20 m", 14, bold=True)
    cv.text((W - 560, W - 40), "yellow = the new W1-6 (post, plate, facing)   grey filled = old rule rev1: warning ~52 m BEFORE the bend", 12)
    cv.text((W - 560, W - 24), "grey hollow = old rule rev2: at the apex, side flipped (= inside)   light blue = the built curb from the mesh", 12)
    p = Path(out_dir) / ("sign_%s.png" % s["id"].replace("/", "_"))
    cv.img.save(p)
    return p


def plot_overview(signs, ribbons, out_dir, max_px=2200):
    xs = [p[0] for _, P, _, _ in ribbons for p in P]
    zs = [p[2] for _, P, _, _ in ribbons for p in P]
    x0, x1, z0, z1 = min(xs) - 100, max(xs) + 100, min(zs) - 100, max(zs) + 100
    span = max(x1 - x0, z1 - z0)
    s = max_px / span
    cv = Canvas((x0 + x1) / 2, (z0 + z1) / 2, span, s)
    draw_ribbons(cv, ribbons, [], detail=False)
    for sg in signs["signs"]:
        b = cv.px(sg["base_xz"])
        f = sg["face_dir_xz"]
        cv.arrow(b, cv.px((sg["base_xz"][0] + f[0] * 60, sg["base_xz"][1] + f[1] * 60)), COL["sign"], width=3, head=10)
        cv.d.ellipse([b[0] - 7, b[1] - 7, b[0] + 7, b[1] + 7], fill=COL["sign"], outline=COL["post"], width=2)
        cv.text((b[0] + 10, b[1] - 10), sg["id"], 15, bold=True, fill=COL["sign"])
    for sk in signs.get("skipped", []):
        if sk.get("would_be"):
            b = cv.px(sk["would_be"])
            cv.d.ellipse([b[0] - 5, b[1] - 5, b[0] + 5, b[1] + 5], outline=COL["old"], width=2)
    cv.text((12, 10), "W1-6 Large Arrow signs — %d placed (yellow, arrow = which way the plate faces); hollow grey = detected but skipped" % len(signs["signs"]), 20, bold=True)
    cv.text((12, 38), "driving direction on the loop: clockwise (increasing vertex index)", 15)
    W = cv.W
    cv.arrow((W - 50, 130), (W - 50, 60), COL["text"], width=4, head=14)
    cv.text((W - 60, 134), "N", 20, bold=True)
    cv.d.line([(14, W - 24), (14 + int(500 * s), W - 24)], fill=COL["text"], width=5)
    cv.text((14, W - 50), "500 m", 16, bold=True)
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
    paths = [plot_overview(signs, ribbons, out_dir)]
    for s in signs["signs"]:
        paths.append(plot_sign(s, ribbons, island, out_dir))
    print("[plot-signs] %d PNGs -> %s" % (len(paths), out_dir))
    for p in paths:
        print("[plot-signs]  ", p)


if __name__ == "__main__":
    main()

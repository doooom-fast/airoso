"""The numbered plan map of the Lake Murray north network (ledger 0054, EXPANSION-PLAN P1 step 4: "Show, don't
assert (L12)... draw every road, pad, mouth, station width and median, numbered so you can point at things").

    python tools/plot_expansion_plan.py [--track <tracks/san-diego-lake-murray>] --png <out.png> [--svg <out.svg>]
                                        [--cache <naip cache dir>] [--no-fetch]

Reads <track>/data/expansion.north.json (tools/author_expansion.py) and the loop (data/centerline.local.json, the
race boxes in track.config.json, the sign bases in data/signs.local.json, the lamp heads in data/lights.local.json).

  --svg  vector, no imagery, local metres (default <track>/data/expansion_plan.svg): every piece's curbs, the medians
         (MD#), the pads (J2-J4) with their arm cuts, the two weld openings (W1 / W5) on the loop's outer edge, the
         see-only stubs (S#) with their walls, the numbered aerial width stations, the junctions with their heights
  --png  the same over NAIP 2022 (USGS The National Map ImageServer through tools/aerial/naip.py, TLS verified; the
         raw windows are cached OUTSIDE the repo, default <naip.default_cache()>/sd-expansion): one overview of the
         whole network plus five close-ups (J1 weld, J5 weld, J2 / J3 / J4 pads)

San Diego's NAIP quarter-quads are in UTM zone 11N (EPSG:26911); tools/aerial is written for the Lariat's zone 13, so
this tool points its geo / naip modules at zone 11 in-process (module attributes, the way the 2026-10-12 aerial lens
did) — the repo's defaults are untouched. Zone 11's central meridian is -117 deg, so the windows are north-up here.
NAIP is public domain (USGS / USDA, The National Map: Orthoimagery).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

TRACK_DEFAULT = AIROSO / "tracks" / "san-diego-lake-murray"
PIECE_COL = {"A": (255, 150, 30), "B": (255, 225, 40), "C": (40, 210, 255), "D": (255, 80, 200)}
MEDIAN_COL = {"planted": (60, 200, 70), "terracotta": (200, 90, 50), "nose": (230, 230, 230),
              "painted": (255, 230, 0), "hatched": (255, 255, 120)}
OVERVIEW_PX_M = 1.25
INSET_PX_M = 0.3
INSET_HALF_M = 115.0
WELD_INSET_PX_M = 0.2       # the two welds closer: 160 m square
WELD_INSET_HALF_M = 76.7


def zone11():
    """tools/aerial/{geo,naip} pointed at UTM 11N (San Diego) for this process only"""
    from tools.aerial import geo, naip
    geo.ZONE = 11
    geo.LON0 = math.radians(11 * 6 - 183)
    naip.EPSG = 26911
    return geo, naip


def font(sz, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, sz)
        except OSError:
            continue
    return ImageFont.load_default()


class Plan:
    def __init__(self, track: Path):
        self.track = track
        d = track / "data"
        self.x = json.loads((d / "expansion.north.json").read_text(encoding="utf-8"))
        self.cl = json.loads((d / "centerline.local.json").read_text(encoding="utf-8"))
        self.cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
        sp = d / "signs.local.json"
        self.signs = json.loads(sp.read_text(encoding="utf-8")).get("signs", []) if sp.exists() else []
        lp = d / "lights.local.json"
        self.lamps = json.loads(lp.read_text(encoding="utf-8")).get("lampheads", []) if lp.exists() else []
        o = self.x["frame"]["origin"]
        phi = math.radians(o["lat"])
        self.mlat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
        self.mlon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
        self.o = o

    def lonlat(self, x, z):
        return (self.o["lon"] + x / self.mlon, self.o["lat"] + z / self.mlat)

    # ---- geometry in local (x, z) -------------------------------------------------------------------------
    def piece_curbs(self, pc, clip=True):
        """centre, left and right curbs of a piece — clipped to its cuts (the pad arm cuts, the weld crossing: what
        P3 builds as the piece; the pads and the welds draw the rest)"""
        cols = pc["columns"]
        ix, iz, il, ir, i_s = (cols.index("x"), cols.index("z"), cols.index("left_m"), cols.index("right_m"),
                               cols.index("s"))
        rows = pc["stations"]
        if clip:
            c = pc.get("cuts", {})
            s0 = c.get("start", {}).get("s", -1e9)
            s1 = c.get("end", {}).get("s", 1e9)
            rows = [r for r in rows if s0 <= r[i_s] <= s1]
        P = [(r[ix], r[iz]) for r in rows]
        left, right = [], []
        for i, r in enumerate(rows):
            a, b = P[max(0, i - 1)], P[min(len(P) - 1, i + 1)]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz) or 1.0
            nx, nz = -dz / L, dx / L
            left.append((P[i][0] + nx * r[il], P[i][1] + nz * r[il]))
            right.append((P[i][0] + nx * r[ir], P[i][1] + nz * r[ir]))
        return P, left, right

    def loop_edges(self, v0=None, v1=None):
        P, W = self.cl["points_xyz_m"], self.cl["widths_m"]
        n = len(P)
        v0 = 0 if v0 is None else v0
        v1 = n - 1 if v1 is None else v1
        L, R = [], []
        for v in range(v0, v1 + 1):
            a, b = P[max(0, v - 1)], P[min(n - 1, v + 1)]
            dx, dz = b[0] - a[0], b[2] - a[2]
            Ln = math.hypot(dx, dz) or 1.0
            nx, nz = -dz / Ln, dx / Ln
            L.append((P[v][0] + nx * W[v] / 2, P[v][2] + nz * W[v] / 2))
            R.append((P[v][0] - nx * W[v] / 2, P[v][2] - nz * W[v] / 2))
        return L, R

    def edge_at(self, vf):
        P, W = self.cl["points_xyz_m"], self.cl["widths_m"]
        v = int(math.floor(vf))
        t = vf - v
        L0, _ = self.loop_edges(v, v)
        L1, _ = self.loop_edges(v + 1, v + 1)
        return (L0[0][0] + (L1[0][0] - L0[0][0]) * t, L0[0][1] + (L1[0][1] - L0[0][1]) * t)


# ------------------------------------------------------------------------------------------------ the drawing

class Canvas:
    """draws local (x, z) features onto an image whose pixel <-> UTM11 mapping is known"""

    def __init__(self, plan: Plan, geo, img: Image.Image, E0, N1, px_m, scale_text=1.0):
        self.p, self.geo = plan, geo
        self.img = img.convert("RGBA")
        self.ov = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.ov)
        self.E0, self.N1, self.px = E0, N1, px_m
        self.k = scale_text

    def pix(self, x, z):
        lon, lat = self.p.lonlat(x, z)
        E, N = self.geo.to_utm(lon, lat)
        return ((E - self.E0) / self.px, (self.N1 - N) / self.px)

    def poly(self, pts, fill=None, outline=None, width=1):
        q = [self.pix(*p) for p in pts]
        if len(q) >= 3 and fill:
            self.d.polygon(q, fill=fill)
        if outline:
            self.d.line(q + [q[0]], fill=outline, width=width)

    def line(self, pts, col, width=2):
        q = [self.pix(*p) for p in pts]
        if len(q) >= 2:
            self.d.line(q, fill=col, width=width, joint="curve")

    def label(self, x, z, text, col=(255, 255, 255, 255), size=16, bold=True, box=True, anchor="mm"):
        f = font(int(size * self.k), bold)
        px, py = self.pix(x, z)
        bb = self.d.textbbox((px, py), text, font=f, anchor=anchor)
        if box:
            self.d.rectangle((bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2), fill=(0, 0, 0, 170))
        self.d.text((px, py), text, font=f, fill=col, anchor=anchor)

    def dot(self, x, z, r, col):
        px, py = self.pix(x, z)
        self.d.ellipse((px - r, py - r, px + r, py + r), fill=col, outline=(0, 0, 0, 255))

    def done(self):
        return Image.alpha_composite(self.img, self.ov).convert("RGB")


def draw_features(cv: Canvas, detail: bool):
    p, x = cv.p, cv.p.x
    k = 1.0 if detail else 0.0
    # the existing loop
    L, R = p.loop_edges()
    cv.line(L, (230, 230, 230, 200), 2 if detail else 1)
    cv.line(R, (230, 230, 230, 200), 2 if detail else 1)
    # pieces: translucent pavement, curbs
    for pc in x["pieces"]:
        col = PIECE_COL[pc["id"]]
        P, left, right = p.piece_curbs(pc)
        cv.poly(left + right[::-1], fill=col + (70,))
        cv.line(left, col + (255,), 3 if detail else 2)
        cv.line(right, col + (255,), 3 if detail else 2)
    # medians
    for m in x["medians"]:
        col = MEDIAN_COL.get(m["type"], (255, 255, 255))
        pts = [tuple(q) for q in m["polygon_xz"]]
        cv.poly(pts, fill=col + (200 if m["raised"] else 110,), outline=col + (255,), width=1)
    # pads
    for pad in x["pads"]:
        cv.poly([tuple(q) for q in pad["outline_xz"]], fill=(255, 255, 255, 60), outline=(255, 255, 255, 255),
                width=3 if detail else 2)
        for a in pad["arms"]:
            cv.line([tuple(q) for q in a["cut_line_xz"]], (255, 60, 60, 255) if a["kind"] == "stub" else (255, 255, 255, 255),
                    3 if detail else 2)
    # stubs
    for s in x["stubs"]:
        cv.poly([tuple(q) for q in s["pavement_xz"]], fill=(150, 150, 150, 150), outline=(200, 200, 200, 255))
        cv.line([tuple(q) for q in s["mouth_line_xz"]], (255, 40, 40, 255), 4 if detail else 3)
    # welds: the curb lines and the opening on the loop's outer edge; an apron (a return the ribbon stub cannot
    # weld, P3 authors it) hatched orange
    for w in x["welds"]:
        for ap in w.get("aprons", []):
            cv.poly([tuple(q) for q in ap["polygon_xz"]], fill=(255, 140, 0, 120), outline=(255, 140, 0, 255),
                    width=3 if detail else 2)
        for side in ("left", "right"):
            cv.line([tuple(q) for q in w["edges_xz"][side]], (255, 255, 255, 255), 3 if detail else 2)
        o = w["opening"]
        n = max(2, int((o["vertex_to"] - o["vertex_from"]) * 4))
        cv.line([p.edge_at(o["vertex_from"] + (o["vertex_to"] - o["vertex_from"]) * i / n) for i in range(n + 1)],
                (255, 30, 30, 255), 6 if detail else 4)
        c = w["connector"]
        if detail:
            cv.line([(q[0], q[2]) for q in c["points_xyz_m"]], (40, 255, 255, 230), 2)
    # aerial width stations: a tick across the road + the number
    for st in x["width_stations"]:
        a, b = tuple(st["left_xz"]), tuple(st["right_xz"])
        cv.line([a, b], (255, 255, 255, 255), 2)
        if detail or True:
            dx, dz = a[0] - b[0], a[1] - b[1]
            L_ = math.hypot(dx, dz) or 1.0
            cv.label(a[0] + dx / L_ * 9, a[1] + dz / L_ * 9, str(st["n"]), col=(255, 255, 0, 255),
                     size=15 if detail else 13)


def draw_labels(cv: Canvas, overview: bool):
    p, x = cv.p, cv.p.x
    for pc in x["pieces"]:
        P, left, right = p.piece_curbs(pc)
        i = len(P) // 2
        cv.label(P[i][0], P[i][1], f"{pc['id']}  {pc['road']}  {pc['length_m'] / 1000:.2f} km",
                 col=PIECE_COL[pc["id"]] + (255,), size=22 if overview else 18)
    for j, rec in x["junctions"].items():
        xz = rec["xz"]
        cv.dot(xz[0], xz[1], 6, (255, 255, 255, 255))
        cv.label(xz[0] + 22, xz[1] + 22, f"{j}  {rec['z_3dep_m']:.1f} m", size=22 if overview else 18, anchor="lm")
    for m in x["medians"]:
        q = m["polygon_xz"][len(m["polygon_xz"]) // 4]
        cv.label(q[0], q[1], f"{m['id']} {m['type']}", col=MEDIAN_COL.get(m["type"], (255, 255, 255)) + (255,),
                 size=13 if overview else 15, anchor="lm")
    for s in x["stubs"]:
        q = s["pavement_xz"][2]
        cv.label(q[0], q[1], f"{s['id']} {s['road'].split(' (')[0]}", col=(255, 120, 120, 255), size=13 if overview else 16)
    for w in x["welds"]:
        o = w["opening"]
        e = p.edge_at((o["vertex_from"] + o["vertex_to"]) / 2)
        cv.label(e[0], e[1] - (10 if w["id"] == "W1" else -10),
                 f"{w['id']} opening v{o['vertex_from']:.1f}-v{o['vertex_to']:.1f}", col=(255, 90, 90, 255),
                 size=14 if overview else 17)
        if not overview:
            for ap in w.get("aprons", []):
                q = ap["polygon_xz"][len(ap["polygon_xz"]) // 2]
                cv.label(q[0], q[1], f"{ap['id']} apron (P3) v{ap['loop_edge_vertices'][0]:.1f}-"
                                     f"{ap['loop_edge_vertices'][1]:.1f}", col=(255, 170, 60, 255), size=15, anchor="lm")


def draw_inset_extras(cv: Canvas, which: str):
    """the loop's vertex numbers, race box and pins, signs and lamps near a weld"""
    p, x = cv.p, cv.p.x
    boxes = {int(b["apex"]): b for b in p.cfg["race"]["corridor"]["boxes"]}
    if which in ("J1", "J5"):
        w = next(q for q in x["welds"] if q["junction"] == which)
        b = boxes[w["apex"]]
        lo, hi = int(w["opening"]["vertex_from"]) - 8, int(w["opening"]["vertex_to"]) + 9
        for v in range(lo, hi + 1):
            e = p.edge_at(v)
            cv.dot(e[0], e[1], 3, (255, 255, 255, 255))
            if v % 2 == 0 or v in (b["i"], b["j"]) or v == b["j"] + 1:
                inbox = b["i"] <= v <= b["j"]
                cv.label(e[0], e[1], f"v{v}", col=(120, 255, 120, 255) if inbox else (200, 200, 200, 255), size=12,
                         box=True, anchor="mb")
        for v, tag in ((b["i"], "pin"), (b["j"], "pin")):
            e = p.edge_at(v)
            cv.dot(e[0], e[1], 7, (0, 255, 0, 255))
        P = p.cl["points_xyz_m"]
        a = P[b["apex"]]
        cv.label(a[0], a[2], f"race box v{b['i']}-v{b['j']} (apex {b['apex']})", col=(120, 255, 120, 255), size=15)
        for sgn in p.signs:
            if str(sgn.get("id", "")).split("-")[0] in ("M3", "M4") and sgn.get("base_xz"):
                bx = sgn["base_xz"]
                if math.hypot(bx[0] - w["centre_cross"]["xz"][0], bx[1] - w["centre_cross"]["xz"][1]) < 80:
                    cv.dot(bx[0], bx[1], 6, (255, 255, 0, 255))
                    cv.label(bx[0] + 3, bx[1] + 3, f"sign {sgn['id']}", col=(255, 255, 0, 255), size=13, anchor="lm")
        for i, lh in enumerate(p.lamps):
            if math.hypot(lh[0] - w["centre_cross"]["xz"][0], lh[2] - w["centre_cross"]["xz"][1]) < 60:
                cv.dot(lh[0], lh[2], 5, (255, 170, 0, 255))
                cv.label(lh[0] + 3, lh[2] - 3, f"lamp {i}", col=(255, 170, 0, 255), size=12, anchor="lm")
        for side, r in w["curbs"].items():
            ret = r.get("return") or r.get("ease")
            if ret:
                ev = ret["built_end_vertex"]
                e = p.edge_at(ev)
                cv.label(e[0], e[1], ("R %.0f return" % ret["R"]) if r.get("return") else "eased onto the loop edge",
                         col=(255, 200, 200, 255), size=13, anchor="lt")


# ------------------------------------------------------------------------------------------------ the PNG

def naip_mosaic(geo, naip, cache, E0, N0, E1, N1, px, prefix, fetch=True, tile_m=1800.0):
    """a north-up image of [E0, E1] x [N0, N1] at px m/pixel from cached / fetched NAIP windows"""
    W = int(round((E1 - E0) / px))
    H = int(round((N1 - N0) / px))
    out = Image.new("RGB", (W, H), (30, 30, 30))
    nx = max(1, int(math.ceil((E1 - E0) / tile_m)))
    ny = max(1, int(math.ceil((N1 - N0) / tile_m)))
    tw, th = (E1 - E0) / nx, (N1 - N0) / ny
    meta = []
    for i in range(nx):
        for j in range(ny):
            cE = E0 + tw * (i + 0.5)
            cN = N0 + th * (j + 0.5)
            wid = f"{prefix}_{i}{j}_{px:.2f}"
            m = naip.window(cache, wid, cE, cN, tw / 2 + 2 * px, th / 2 + 2 * px, px, fetch=fetch)
            im = Image.open(Path(m["_cache"]) / m["files"]["rgb"]["path"]).convert("RGB")
            bx0, by0, bx1, by1 = m["bbox_utm13n"]
            ox = int(round((bx0 - E0) / px))
            oy = int(round((N1 - by1) / px))
            out.paste(im, (ox, oy))
            meta.append({"id": wid, "bbox_utm11n": m["bbox_utm13n"], "catalog": [c.get("Name") for c in m.get("catalog", [])
                                                                                 if isinstance(c, dict)]})
    return out, meta


def render_png(plan: Plan, out: Path, cache: Path, fetch: bool):
    geo, naip = zone11()
    x = plan.x
    pts = []
    for pc in x["pieces"]:
        _P, l, r = plan.piece_curbs(pc)
        pts += l + r
    for w in x["welds"]:
        pts += [tuple(q) for side in ("left", "right") for q in w["edges_xz"][side]]
    lls = [plan.lonlat(*q) for q in pts]
    utm = [geo.to_utm(lo, la) for lo, la in lls]
    margin = 220.0
    E0, E1 = min(u[0] for u in utm) - margin, max(u[0] for u in utm) + margin
    N0, N1 = min(u[1] for u in utm) - margin, max(u[1] for u in utm) + margin
    E0, N1 = math.floor(E0), math.ceil(N1)
    base, meta = naip_mosaic(geo, naip, cache, E0, N0, E1, N1, OVERVIEW_PX_M, "sdx_ov", fetch=fetch)
    cv = Canvas(plan, geo, base, E0, N1, OVERVIEW_PX_M, scale_text=1.0)
    draw_features(cv, detail=False)
    draw_labels(cv, overview=True)
    ov = cv.done()
    # insets
    insets = []
    centres = [("J1", "W1 at J1: Waring welded onto the loop's outer edge (College/Navajo box)"),
               ("J5", "W5 at J5: Jackson north welded onto the loop's outer edge (the 0050 box)"),
               ("J2", "J2 pad: Waring / Princess View / Mound"), ("J3", "J3 pad: Princess View / Mission Gorge (33.4 m)"),
               ("J4", "J4 pad: Mission Gorge / Jackson")]
    for j, title in centres:
        if j in ("J1", "J5"):
            w = next(q for q in x["welds"] if q["junction"] == j)
            cx, cz = w["centre_cross"]["xz"]
        else:
            cx, cz = x["junctions"][j]["xz"]
        lo, la = plan.lonlat(cx, cz)
        cE, cN = geo.to_utm(lo, la)
        half, px = (WELD_INSET_HALF_M, WELD_INSET_PX_M) if j in ("J1", "J5") else (INSET_HALF_M, INSET_PX_M)
        e0, e1 = cE - half, cE + half
        n0, n1 = cN - half, cN + half
        e0, n1 = math.floor(e0), math.ceil(n1)
        img, m2 = naip_mosaic(geo, naip, cache, e0, n0, e1, n1, px, f"sdx_{j}", fetch=fetch, tile_m=400.0)
        meta += m2
        c2 = Canvas(plan, geo, img, e0, n1, px, scale_text=1.0)
        draw_features(c2, detail=True)
        draw_labels(c2, overview=False)
        draw_inset_extras(c2, j)
        im = c2.done()
        dr = ImageDraw.Draw(im)
        dr.rectangle((0, 0, im.size[0], 34), fill=(0, 0, 0))
        dr.text((10, 6), title, font=font(20, True), fill=(255, 255, 255))
        scale_bar(dr, im.size, px, 20.0)
        insets.append(im)
    # compose: overview left, insets in two columns right
    iw = insets[0].size[0]
    ih = insets[0].size[1]
    W = ov.size[0] + 2 * iw
    H = max(ov.size[1], 3 * ih) + 210
    sheet = Image.new("RGB", (W, H), (18, 18, 18))
    sheet.paste(ov, (0, 210))
    for k, im in enumerate(insets):
        sheet.paste(im, (ov.size[0] + (k % 2) * iw, 210 + (k // 2) * ih))
    dr = ImageDraw.Draw(sheet)
    dr.text((20, 14), "Lake Murray north network - the numbered plan (ledger 0054, P1)", font=font(40, True), fill=(255, 255, 255))
    dr.text((20, 66), "Kevin: \"college down waring to princess view, princess view to mission gorge, mission gorge to jackson, "
                      "then extend jackson down to mission gorge\" - one network with the loop", font=font(22), fill=(220, 220, 220))
    legend(dr, 20, 104)
    scale_bar(dr, (ov.size[0], ov.size[1] + 210), OVERVIEW_PX_M, 500.0)
    dr.text((W - 1150, H - 30), "NAIP 2022-04-25 (USGS / USDA, The National Map: Orthoimagery, public domain), UTM 11N, "
                                "north up. Plan: tracks/san-diego-lake-murray/data/expansion.north.json",
            font=font(16), fill=(200, 200, 200))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    return meta, sheet.size


def scale_bar(dr, size, px_m, metres):
    L = metres / px_m
    x0, y0 = 30, size[1] - 40
    dr.rectangle((x0 - 6, y0 - 26, x0 + L + 60, y0 + 14), fill=(0, 0, 0))
    dr.line((x0, y0, x0 + L, y0), fill=(255, 255, 255), width=5)
    dr.text((x0 + L + 8, y0 - 10), f"{metres:.0f} m", font=font(16, True), fill=(255, 255, 255))
    dr.text((x0, y0 - 24), "N up", font=font(14), fill=(255, 255, 255))


def legend(dr, x0, y0):
    f = font(17)
    items = [((255, 150, 30), "A Waring"), ((255, 225, 40), "B Princess View"), ((40, 210, 255), "C Mission Gorge"),
             ((255, 80, 200), "D Jackson north"), ((255, 255, 255), "pad outline / arm cut (J2-J4)"),
             ((255, 30, 30), "W1 / W5 opening on the loop edge; S# stub wall"), ((60, 200, 70), "MD planted median"),
             ((200, 90, 50), "MD terracotta median"), ((255, 230, 0), "MD painted / hatched median"),
             ((255, 255, 0), "1-38 aerial width station"), ((255, 140, 0), "AP1 apron: the J1 return P3 authors"),
             ((230, 230, 230), "existing loop")]
    x = x0
    for col, txt in items:
        dr.rectangle((x, y0 + 4, x + 22, y0 + 20), fill=col)
        dr.text((x + 28, y0 + 2), txt, font=f, fill=(230, 230, 230))
        x += 34 + int(dr.textlength(txt, font=f)) + 18
        if x > 2900:
            x = x0
            y0 += 30


# ------------------------------------------------------------------------------------------------ the SVG

def render_svg(plan: Plan, out: Path):
    x = plan.x
    pts = []
    for pc in x["pieces"]:
        _P, l, r = plan.piece_curbs(pc)
        pts += l + r
    minx, maxx = min(p[0] for p in pts) - 150, max(p[0] for p in pts) + 150
    minz, maxz = min(p[1] for p in pts) - 150, max(p[1] for p in pts) + 150
    W, H = maxx - minx, maxz - minz

    def P(q):
        return f"{q[0] - minx:.2f},{maxz - q[1]:.2f}"

    def path(q, close=False):
        return "M" + " L".join(P(p) for p in q) + (" Z" if close else "")

    def rgb(c, a=1.0):
        return f"rgba({c[0]},{c[1]},{c[2]},{a})"
    el = []
    L, R = plan.loop_edges()
    el.append(f'<path d="{path(L)}" fill="none" stroke="#888" stroke-width="1"/>')
    el.append(f'<path d="{path(R)}" fill="none" stroke="#888" stroke-width="1"/>')
    for pc in x["pieces"]:
        col = PIECE_COL[pc["id"]]
        _P, l, r = plan.piece_curbs(pc)
        el.append(f'<path d="{path(l + r[::-1], True)}" fill="{rgb(col, 0.35)}" stroke="{rgb(col)}" stroke-width="1.2"/>')
        mid = _P[len(_P) // 2]
        el.append(f'<text x="{mid[0] - minx:.1f}" y="{maxz - mid[1]:.1f}" class="big" fill="{rgb(col)}">{pc["id"]} '
                  f'{pc["road"]} {pc["length_m"] / 1000:.2f} km</text>')
    for m in x["medians"]:
        col = MEDIAN_COL.get(m["type"], (255, 255, 255))
        el.append(f'<path d="{path([tuple(q) for q in m["polygon_xz"]], True)}" fill="{rgb(col, 0.8 if m["raised"] else 0.45)}" '
                  f'stroke="{rgb(col)}" stroke-width="0.3"><title>{m["id"]} {m["type"]} s {m["s_from"]}-{m["s_to"]} '
                  f'width {m["width_m"]}</title></path>')
        q = m["polygon_xz"][len(m["polygon_xz"]) // 4]
        el.append(f'<text x="{q[0] - minx:.1f}" y="{maxz - q[1]:.1f}" class="sm">{m["id"]}</text>')
    for pad in x["pads"]:
        el.append(f'<path d="{path([tuple(q) for q in pad["outline_xz"]], True)}" fill="rgba(255,255,255,0.5)" '
                  f'stroke="#000" stroke-width="0.6"><title>{pad["id"]} pad, {pad["z_3dep_m"]} m; corners R '
                  f'{"/".join(str(c["R_m"]) for c in pad["corners"])} m</title></path>')
        for a in pad["arms"]:
            el.append(f'<path d="{path([tuple(q) for q in a["cut_line_xz"]])}" stroke="{"#d00" if a["kind"] == "stub" else "#000"}" '
                      f'stroke-width="1"/>')
    for s in x["stubs"]:
        el.append(f'<path d="{path([tuple(q) for q in s["pavement_xz"]], True)}" fill="#bbb" stroke="#666" stroke-width="0.4"/>')
        el.append(f'<path d="{path([tuple(q) for q in s["mouth_line_xz"]])}" stroke="#d00" stroke-width="1.5"/>')
        q = s["pavement_xz"][2]
        el.append(f'<text x="{q[0] - minx:.1f}" y="{maxz - q[1]:.1f}" class="sm" fill="#d00">{s["id"]} {s["road"]}</text>')
    for w in x["welds"]:
        for ap in w.get("aprons", []):
            el.append(f'<path d="{path([tuple(q) for q in ap["polygon_xz"]], True)}" fill="rgba(255,140,0,0.5)" '
                      f'stroke="#c60" stroke-width="0.6"><title>{ap["id"]} apron (P3): {ap["why"]}</title></path>')
        for side in ("left", "right"):
            el.append(f'<path d="{path([tuple(q) for q in w["edges_xz"][side]])}" fill="none" stroke="#000" stroke-width="0.8"/>')
        o = w["opening"]
        n = max(2, int((o["vertex_to"] - o["vertex_from"]) * 4))
        ed = [plan.edge_at(o["vertex_from"] + (o["vertex_to"] - o["vertex_from"]) * i / n) for i in range(n + 1)]
        el.append(f'<path d="{path(ed)}" fill="none" stroke="#e00" stroke-width="2.5"><title>{w["id"]} opening '
                  f'v{o["vertex_from"]}-v{o["vertex_to"]} ({o["length_m"]} m; A5 {o["a5"]})</title></path>')
        e = ed[len(ed) // 2]
        el.append(f'<text x="{e[0] - minx:.1f}" y="{maxz - e[1]:.1f}" class="mid" fill="#e00">{w["id"]} '
                  f'v{o["vertex_from"]:.1f}-v{o["vertex_to"]:.1f}</text>')
        el.append(f'<path d="{path([(q[0], q[2]) for q in w["connector"]["points_xyz_m"]])}" fill="none" stroke="#0aa" '
                  f'stroke-width="0.5" stroke-dasharray="2,2"/>')
    for st in x["width_stations"]:
        a, b = st["left_xz"], st["right_xz"]
        el.append(f'<path d="{path([tuple(a), tuple(b)])}" stroke="#000" stroke-width="0.6"><title>{st["n"]}: {st["label"]} '
                  f'eye {st["eye_width_m"]} m, built {st["built_width_m"]} m</title></path>')
        dx, dz = a[0] - b[0], a[1] - b[1]
        L_ = math.hypot(dx, dz) or 1.0
        el.append(f'<text x="{a[0] + dx / L_ * 8 - minx:.1f}" y="{maxz - (a[1] + dz / L_ * 8):.1f}" class="sm" '
                  f'fill="#a60">{st["n"]}</text>')
    for j, rec in x["junctions"].items():
        q = rec["xz"]
        el.append(f'<circle cx="{q[0] - minx:.1f}" cy="{maxz - q[1]:.1f}" r="3" fill="#000"/>')
        el.append(f'<text x="{q[0] - minx + 12:.1f}" y="{maxz - q[1] - 12:.1f}" class="big">{j} {rec["z_3dep_m"]:.1f} m</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}">\n'
           '<title>Lake Murray north network - the numbered plan (ledger 0054 P1)</title>\n'
           '<style>text{font-family:Arial,sans-serif;font-weight:bold} .big{font-size:24px} .mid{font-size:14px} '
           '.sm{font-size:7px}</style>\n'
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#f4f1ea"/>\n'
           f'<text x="20" y="40" class="big">Lake Murray north network - the numbered plan (ledger 0054 P1); local metres, '
           f'north up; data/expansion.north.json</text>\n' + "\n".join(el) + "\n</svg>\n")
    out.write_text(svg, encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--track", default=str(TRACK_DEFAULT))
    ap.add_argument("--png", required=True)
    ap.add_argument("--svg", default=None)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args(argv)
    track = Path(a.track)
    plan = Plan(track)
    svg = Path(a.svg) if a.svg else track / "data" / "expansion_plan.svg"
    render_svg(plan, svg)
    print(f"[plan-map] wrote {svg}")
    _geo, naip = zone11()
    cache = Path(a.cache) if a.cache else naip.default_cache() / "sd-expansion"
    png = Path(a.png).resolve()
    try:
        png.relative_to(AIROSO.resolve())
        raise SystemExit("[plan-map] --png is inside the repo: the NAIP sheet is a large binary, write it outside")
    except ValueError:
        pass
    meta, size = render_png(plan, png, cache, fetch=not a.no_fetch)
    (png.with_suffix(".windows.json")).write_text(json.dumps({"naip_windows": meta, "cache": str(cache)}, indent=1),
                                                  encoding="utf-8")
    print(f"[plan-map] wrote {png} ({size[0]} x {size[1]} px; {len(meta)} NAIP windows, cache {cache})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

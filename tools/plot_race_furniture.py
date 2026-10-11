"""Top-down pictures of the race-layout furniture over the Lake Murray loop (ledger 0047) — for
someone who thinks in maps: pavement, median islands, the centre K-rail chain (red), the kerb-line
barriers on both curb faces (orange = forward-left, cyan = forward-right), the race kerbs (white),
the three bridge-span gaps, each layout's grid / pit row / timing lines, and the island noses the
chain butts into. One overview + one 180 m window per place that matters (the Alvarado grids, the
hairpin, the Del Cerro 4-way, the three chained corners, the I-8 end of the chain, the lap seam).

Reads data/race_authored.json (tools/author_race_furniture_blend.py: the SEATED ring centres of
every authored object) when it exists, else plans the same geometry in pure Python
(tools/race_furniture.plan_all) so the picture exists before any Blender run; `--planned` forces
the latter. Pillow only (no matplotlib on this box).

    python tools/plot_race_furniture.py <project-dir> [--out DIR] [--planned]
        (default DIR: <project>/data/race_plots/)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import race_furniture as rf  # noqa: E402

COL = {"bg": (34, 40, 34), "grass": (60, 92, 54), "road": (88, 88, 94), "island": (142, 170, 112),
       "chain": (235, 60, 50), "edge_L": (255, 160, 40), "edge_R": (60, 200, 230), "kerb": (255, 255, 255),
       "kerb2": (235, 60, 50), "gap": (255, 230, 80), "nose": (255, 255, 120), "text": (240, 240, 240),
       "shadow": (0, 0, 0), "cl": (130, 130, 140),
       "street": (255, 255, 255), "race_cw": (120, 255, 120), "race_acw": (255, 120, 255)}
CAR_L, CAR_W = 4.5, 1.9
WINDOWS = (("alvarado_grids", 300, "Alvarado: the line (v300), grid A / pits behind (v291 down), grid B (v310 up)"),
           ("hairpin_770", 770, "Alvarado/College hairpin: chain starts v780, inside + outside kerbs"),
           ("del_cerro_1085", 1085, "Del Cerro 4-way: chain nose-to-nose across the mouths (sealed, Q1)"),
           ("college_navajo_1514", 1514, "College/Navajo: chain continuous round the corner, outside kerb"),
           ("navajo_jackson_2319", 2319, "Navajo/Jackson: chain continuous, outside kerb"),
           ("jackson_lmb_3297", 3297, "Jackson/Lake Murray: chain continuous, outside kerb"),
           ("i8_end_4440", 4460, "Chain end v4440 before the I-8 span; edge strips gapped on the span"),
           ("seam_0", 0, "Lap seam 70th/Lake Murray -> Alvarado: inside + outside kerbs, no chain"))


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
    """engine x (E) -> right, z (N) -> up"""

    def __init__(self, x0, z0, x1, z1, px_per_m, pad_px=0, footer_px=0):
        self.x0, self.z0, self.x1, self.z1, self.s = x0, z0, x1, z1, px_per_m
        self.pad, self.footer = pad_px, footer_px
        self.W = int((x1 - x0) * px_per_m) + 2 * pad_px
        self.H = int((z1 - z0) * px_per_m) + 2 * pad_px + footer_px
        self.img = Image.new("RGB", (self.W, self.H), COL["grass"])
        self.d = ImageDraw.Draw(self.img)

    def px(self, p):
        return (int((p[0] - self.x0) * self.s) + self.pad, int((self.z1 - p[1]) * self.s) + self.pad)

    def poly(self, pts, fill):
        self.d.polygon([self.px(p) for p in pts], fill=fill)

    def line(self, pts, fill, width=1):
        if len(pts) >= 2:
            self.d.line([self.px(p) for p in pts], fill=fill, width=width)

    def dot(self, p, r, fill, outline=None):
        x, y = self.px(p)
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline)

    def text(self, xy, s, size=13, bold=False, fill=None, anchor="la"):
        f = font(size, bold)
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            self.d.text((xy[0] + dx, xy[1] + dy), s, font=f, fill=COL["shadow"], anchor=anchor)
        self.d.text(xy, s, font=f, fill=fill or COL["text"], anchor=anchor)

    def save(self, path):
        self.img.save(path, optimize=True)


def _load(proj, planned):
    proj = Path(proj)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    pts, widths = rf.load_centerline(proj)
    m = rf.unique_count(pts)
    island_w = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))["island_w_by_vertex"]
    bands = rf.load_bands(proj)
    if bands is None:
        raise SystemExit("[plot-race] no data/barrier_bands.json (tools/barrier_bands.py)")
    authored = None
    rep = data / "race_authored.json"
    if rep.exists() and not planned:
        authored = json.loads(rep.read_text(encoding="utf-8"))
    curves = {}
    if authored:
        for name, cs in authored["ring_centres"].items():
            curves[name] = [(c[0], c[2]) for c in cs]
        source = f"race_authored.json ({authored['totals']['objects']} objects, seated on the built deck)"
    else:
        _, _, _, plans, _ = rf.plan_all(proj, bands, (bands.get("params") or {}).get("edge_mode", "road"))
        for p in plans:
            name = rf.object_name(p)
            if p["kind"] in ("chain", "edge"):
                out = []
                for r in p["rings"]:
                    lx, lz = rf.left_normal(r["tx"], r["tz"])
                    out.append((r["cx"] + lx * r["lat"], r["cz"] + lz * r["lat"]))
            else:
                sgn = 1.0 if p["side"] == "L" else -1.0
                out = []
                for s in p["stations"]:
                    lx, lz = rf.left_normal(s["tx"], s["tz"])
                    mid = s["lip"] + sgn * rf.KERB_W / 2.0
                    out.append((s["cx"] + lx * mid, s["cz"] + lz * mid))
            curves[name] = out
        source = f"PLANNED in pure Python ({len(plans)} objects; no Blender run yet)"
    dummies = {}
    for lo in cfg.get("layouts", []):
        p = data / f"dummies_{lo['id']}.json"
        if p.exists():
            dummies[lo["id"]] = json.loads(p.read_text(encoding="utf-8"))
    return pts, widths, m, island_w, bands, curves, dummies, authored, source


def _edge_pts(pts, widths, m, k, sgn):
    tx, tz = rf.tangent(pts, k, m)
    lx, lz = rf.left_normal(tx, tz)
    h = widths[k] / 2.0 * sgn
    return (pts[k][0] + lx * h, pts[k][2] + lz * h)


def _draw_base(cv, pts, widths, m, island_w, bands, ks):
    """pavement quads, islands, centreline and bridge-gap marks for the vertex list ks"""
    ei = bands["edge_inset_by_vertex"]
    for a, b in zip(ks, ks[1:]):
        cv.poly([_edge_pts(pts, widths, m, a, 1), _edge_pts(pts, widths, m, b, 1),
                 _edge_pts(pts, widths, m, b, -1), _edge_pts(pts, widths, m, a, -1)], COL["road"])
    for a, b in zip(ks, ks[1:]):
        if island_w[a] > 0 and island_w[b] > 0:
            quad = []
            for k, sg in ((a, 1), (b, 1), (b, -1), (a, -1)):
                tx, tz = rf.tangent(pts, k, m)
                lx, lz = rf.left_normal(tx, tz)
                h = island_w[k] / 2.0 * sg
                quad.append((pts[k][0] + lx * h, pts[k][2] + lz * h))
            cv.poly(quad, COL["island"])
    for a, b in zip(ks, ks[1:]):
        if ei[a] == 0 and ei[b] == 0:          # inside a declared bridge span: no edge strip
            cv.line([_edge_pts(pts, widths, m, a, 1), _edge_pts(pts, widths, m, b, 1)], COL["gap"], 3)
            cv.line([_edge_pts(pts, widths, m, a, -1), _edge_pts(pts, widths, m, b, -1)], COL["gap"], 3)
    cv.line([(pts[k][0], pts[k][2]) for k in ks], COL["cl"], 1)


def _draw_furniture(cv, curves, w_chain, w_edge, w_kerb):
    for name, cs in curves.items():
        if "_kbar_" in name:
            cv.line(cs, COL["chain"], w_chain)
        elif "_edge_L_" in name:
            cv.line(cs, COL["edge_L"], w_edge)
        elif "_edge_R_" in name:
            cv.line(cs, COL["edge_R"], w_edge)
        elif name.upper().startswith("1KERB_RACE"):
            # red/white dashes, like the texture
            for i, (a, b) in enumerate(zip(cs, cs[1:])):
                cv.line([a, b], COL["kerb"] if (i // 3) % 2 == 0 else COL["kerb2"], w_kerb)


def _draw_dummies(cv, pts, m, dummies, scale_ok):
    for lid, d in dummies.items():
        col = COL.get(lid, (200, 200, 200))
        pos = rf.dummies_positions(d)
        vtx = d.get("_vertex", {})
        for name, p in pos.items():
            x, z = p[0], p[2]
            if name.startswith("AC_TIME"):
                continue
            k = int(vtx.get(name, rf.nearest_vertex(pts, m, x, z))) % m
            tx, tz = rf.tangent(pts, k, m)
            if d.get("_direction") == "reverse":
                tx, tz = -tx, -tz
            lx, lz = rf.left_normal(tx, tz)
            L, W = (CAR_L, CAR_W) if name.startswith("AC_START") else (3.6, 1.6)
            quad = [(x + tx * L / 2 + lx * W / 2, z + tz * L / 2 + lz * W / 2),
                    (x + tx * L / 2 - lx * W / 2, z + tz * L / 2 - lz * W / 2),
                    (x - tx * L / 2 - lx * W / 2, z - tz * L / 2 - lz * W / 2),
                    (x - tx * L / 2 + lx * W / 2, z - tz * L / 2 + lz * W / 2)]
            if scale_ok:
                cv.poly(quad, col if name.startswith("AC_START") else tuple(int(c * 0.6) for c in col))
                cv.line([(x, z), (x + tx * L / 2 + tx * 1.5, z + tz * L / 2 + tz * 1.5)], col, 2)   # nose tick
            else:
                cv.dot((x, z), 3, col)
        for gi in range(3):
            l, r = pos.get(f"AC_TIME_{gi}_L"), pos.get(f"AC_TIME_{gi}_R")
            if l and r:
                cv.line([(l[0], l[2]), (r[0], r[2])], col, 3 if scale_ok else 2)
                if scale_ok:
                    cv.text(cv.px((l[0], l[2])), f"T{gi} {lid}", 12, True, col)


def _legend(cv, x, y, source, totals):
    rows = [("chain", "centre K-rail chain (1WALL_race_kbar_*)"), ("edge_L", "kerb-line barrier, forward-left curb"),
            ("edge_R", "kerb-line barrier, forward-right curb"), ("kerb", "race kerb (1KERB_race_*)"),
            ("gap", "declared bridge span: no edge strip"), ("island", "median island"),
            ("street", "street grid / line"), ("race_cw", "race_cw grid / line"), ("race_acw", "race_acw grid / line")]
    for i, (key, label) in enumerate(rows):
        yy = y + i * 18
        cv.d.rectangle((x, yy + 3, x + 22, yy + 13), fill=COL[key])
        cv.text((x + 30, yy), label, 13)
    yy = y + len(rows) * 18 + 6
    cv.text((x, yy), f"source: {source}", 12)
    if totals:
        cv.text((x, yy + 18), f"chain {totals['chain_length_m']:.0f} m = {totals['chain_segments_4m']} x 4.04 m modules in "
                               f"{totals['chain_objects']} objects ({totals['chain_rings']} rings); edge strips {totals['edge_length_m']:.0f} m "
                               f"in {totals['edge_objects']} objects; kerbs {totals['kerb_length_m']:.0f} m in {totals['kerb_objects']} objects", 12)
        cv.text((x, yy + 36), f"{totals['positions']:,} positions in {totals['objects']} objects; seated {totals['seated_hit']} hit / "
                               f"{totals['seated_near']} near / {totals['seated_interpolated']} interpolated; deck vs data max "
                               f"{totals['deck_vs_data_max_m']} m; other deck above {totals['other_deck_above_rings']} rings", 12)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    planned = "--planned" in argv
    out = None
    if "--out" in argv:
        i = argv.index("--out"); out = Path(argv[i + 1]); del argv[i:i + 2]
    argv = [a for a in argv if a != "--planned"]
    proj = Path(argv[0]).resolve()
    out = out or (proj / "data" / "race_plots")
    out.mkdir(parents=True, exist_ok=True)
    pts, widths, m, island_w, bands, curves, dummies, authored, source = _load(proj, planned)
    totals = authored["totals"] if authored else None
    noses = (bands.get("summary") or {}).get("nose_vertices", [])

    # overview
    xs, zs = [p[0] for p in pts], [p[2] for p in pts]
    x0, x1, z0, z1 = min(xs) - 60, max(xs) + 60, min(zs) - 60, max(zs) + 60
    s = min(1700.0 / (x1 - x0), 1400.0 / (z1 - z0))
    cv = Canvas(x0, z0, x1, z1, s, pad_px=10, footer_px=230)
    ks = list(range(m)) + [0]
    _draw_base(cv, pts, widths, m, island_w, bands, ks)
    _draw_furniture(cv, curves, 3, 2, 3)
    for k in noses:
        cv.dot((pts[k][0], pts[k][2]), 4, COL["nose"], (0, 0, 0))
    _draw_dummies(cv, pts, m, dummies, False)
    for k, label in ((300, "LINE v300"), (770, "hairpin v770"), (1085, "Del Cerro 4-way"), (1514, "College/Navajo"),
                     (2319, "Navajo/Jackson"), (3297, "Jackson/LMB"), (4440, "chain end v4440"), (0, "seam v0")):
        x, y = cv.px((pts[k][0], pts[k][2]))
        cv.text((x, y), label, 13, True, anchor=("ra" if x > cv.W - 160 else "la"))
    cv.text((14, 8), "Lake Murray race-layout furniture (ledger 0047) — top-down, engine frame x=E right, z=N up", 18, True)
    _legend(cv, 14, cv.H - 220, source, totals)
    cv.save(out / "overview.png")
    print(f"[plot-race] overview -> {out / 'overview.png'} ({cv.W}x{cv.H})")

    # windows
    for tag, k0, caption in WINDOWS:
        cx, cz = pts[k0][0], pts[k0][2]
        win, pxm = 180.0, 6.0
        cv = Canvas(cx - win / 2, cz - win / 2, cx + win / 2, cz + win / 2, pxm, pad_px=0, footer_px=60)
        ks = [k % m for k in range(k0 - 90, k0 + 91)]
        _draw_base(cv, pts, widths, m, island_w, bands, ks)
        _draw_furniture(cv, curves, 5, 4, 5)
        for k in noses:
            if abs(pts[k][0] - cx) < win and abs(pts[k][2] - cz) < win:
                cv.dot((pts[k][0], pts[k][2]), 6, COL["nose"], (0, 0, 0))
                cv.text(cv.px((pts[k][0], pts[k][2])), f"nose v{k}", 12, True, COL["nose"])
        _draw_dummies(cv, pts, m, dummies, True)
        for k in range(k0 - 90, k0 + 91, 15):
            kk = k % m
            cv.text(cv.px((pts[kk][0], pts[kk][2])), f"v{kk}", 11, False, COL["cl"])
        cv.text((8, cv.H - 54), caption, 14, True)
        cv.text((8, cv.H - 30), f"{win:.0f} m window, {pxm:.0f} px/m; forward travel = increasing vertex index (clockwise); "
                                f"orange = forward-left curb strip, cyan = forward-right", 12)
        cv.save(out / f"{tag}.png")
        print(f"[plot-race] {tag} -> {out / (tag + '.png')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

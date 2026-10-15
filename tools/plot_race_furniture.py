"""Top-down pictures of the race-layout furniture over the Lake Murray loop (ledgers 0047 + 0049) — for someone
who thinks in maps. ONE FOLDER PER RACE LAYOUT, `data/race_plots/<layout id>/`, each showing what THAT version
loads: pavement, median islands, the race lane (green: where the car may go), both curb barriers (orange =
forward-left curb, cyan = forward-right curb — common to both race versions), THIS version's closure wall (red:
the barrier that shuts off the other direction), the race kerbs (red / white), the closure's pins (where each
wall end is buried in the far curb barrier), the island noses, and the grid / pit row / timing lines.

Per layout: overview.png, the five corners the race turns at (corner_<apex>.png), the Del Cerro 4-way
(del_cerro_1085.png), the I-8 end of the closure (i8_end_4454.png), every island nose (nose_<v>.png) and every
closure pin (pin_<v>.png).

Reads data/race_authored.json (tools/author_race_furniture_blend.py: the SEATED ring centres of every authored
object) when it exists, else plans the same geometry in pure Python (tools/race_furniture.plan_all) so the
pictures exist before any Blender run; `--planned` forces the latter. Pillow only (no matplotlib on this box).

    python tools/plot_race_furniture.py <project-dir> [--out DIR] [--planned]
        (default DIR: <project>/data/race_plots/)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import race_furniture as rf  # noqa: E402

COL = {"grass": (60, 92, 54), "road": (88, 88, 94), "island": (142, 170, 112), "lane": (90, 230, 120, 70),
       "close": (235, 50, 45), "edge_L": (255, 160, 40), "edge_R": (60, 200, 230), "kerb": (255, 255, 255),
       "kerb2": (235, 60, 50), "nose": (255, 255, 120), "pin": (255, 60, 255), "text": (240, 240, 240),
       "shadow": (0, 0, 0), "cl": (130, 130, 140), "grid": (120, 255, 120), "pit": (80, 170, 80), "time": (255, 255, 255)}
CAR_L, CAR_W = 4.5, 1.9
CORNERS = ((0, "seam: Lake Murray Blvd -> Alvarado (the I-8 interchange corner)"),
           (770, "hairpin: Alvarado -> College"),
           (1514, "College -> Navajo"),
           (2319, "Navajo -> Jackson"),
           (3297, "Jackson -> Lake Murray Blvd"))
# the retired ledger-0047 picture names, removed from the top of the output folder (the per-layout folders replace them)
OLD_FILES = ("overview.png", "alvarado_grids.png", "hairpin_770.png", "del_cerro_1085.png", "college_navajo_1514.png",
             "navajo_jackson_2319.png", "jackson_lmb_3297.png", "i8_end_4440.png", "seam_0.png")


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
        self.overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        self.od = ImageDraw.Draw(self.overlay)

    def px(self, p):
        return (int((p[0] - self.x0) * self.s) + self.pad, int((self.z1 - p[1]) * self.s) + self.pad)

    def poly(self, pts, fill):
        self.d.polygon([self.px(p) for p in pts], fill=fill)

    def tint(self, pts, fill):
        self.od.polygon([self.px(p) for p in pts], fill=fill)

    def flush(self):
        """composite the translucent layer (the lane) under everything drawn after this"""
        self.img = Image.alpha_composite(self.img.convert("RGBA"), self.overlay).convert("RGB")
        self.d = ImageDraw.Draw(self.img)
        self.overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        self.od = ImageDraw.Draw(self.overlay)

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


def _load(proj, planned, lap=None):
    """one lap group (ledger 0054): the mainline (lap None, as before) or a lap's line / declaration / authored set"""
    proj = Path(proj)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    pts, widths = rf.load_centerline(proj, lap)
    m = rf.unique_count(pts)
    island_w = rf.load_island_w(proj, lap)
    bands = rf.load_bands(proj, lap)
    if bands is None:
        raise SystemExit(f"[plot-race] no data/{rf._race_lap().bands_file(lap)} (tools/barrier_bands.py)")
    authored = None
    rep = data / rf._race_lap().authored_file(lap)
    if rep.exists() and not planned:
        authored = json.loads(rep.read_text(encoding="utf-8"))
    curves = {}
    if authored:
        for name, cs in authored["ring_centres"].items():
            curves[name] = [(c[0], c[2]) for c in cs]
        source = f"race_authored.json ({authored['totals']['objects']} objects, seated on the built deck)"
    else:
        _, _, _, plans, _ = rf.plan_all(proj, bands, (bands.get("params") or {}).get("edge_mode", "road"), lap=lap)
        for p in plans:
            name = rf.object_name(p)
            if p["kind"] in ("edge", "close"):
                curves[name] = [rf._strip_xz(r) for r in p["rings"]]
            else:
                sgn = 1.0 if p["side"] == "L" else -1.0
                curves[name] = [rf.kerb_mid_xz(s, sgn) for s in p["stations"]]
        source = f"PLANNED in pure Python ({len(plans)} objects; no Blender run yet)"
    dummies = {}
    for lo in cfg.get("layouts", []):
        p = data / f"dummies_{lo['id']}.json"
        if p.exists():
            dummies[lo["id"]] = json.loads(p.read_text(encoding="utf-8"))
    return cfg, pts, widths, m, island_w, bands, curves, dummies, authored, source


def island_noses(island_w, m):
    """the first and last vertex of every median island run (island_w > 0) — where each nose tip stands"""
    out = []
    k = 0
    while k < m:
        if island_w[k] <= 0:
            k += 1
            continue
        j = k
        while j + 1 < m and island_w[j + 1] > 0:
            j += 1
        out += [k, j]
        k = j + 1
    return sorted(set(out))


def _off(pts, m, k, lat):
    tx, tz = rf.tangent(pts, k, m)
    lx, lz = rf.left_normal(tx, tz)
    return (pts[k][0] + lx * lat, pts[k][2] + lz * lat)


def _draw_base(cv, pts, widths, m, island_w, ks, lane=None):
    """pavement quads, the layout's lane (translucent green), islands and the centreline for the vertex list ks"""
    for a, b in zip(ks, ks[1:]):
        cv.poly([_off(pts, m, a, widths[a] / 2), _off(pts, m, b, widths[b] / 2),
                 _off(pts, m, b, -widths[b] / 2), _off(pts, m, a, -widths[a] / 2)], COL["road"])
    for a, b in zip(ks, ks[1:]):
        if island_w[a] > 0 and island_w[b] > 0:
            cv.poly([_off(pts, m, a, island_w[a] / 2), _off(pts, m, b, island_w[b] / 2),
                     _off(pts, m, b, -island_w[b] / 2), _off(pts, m, a, -island_w[a] / 2)], COL["island"])
    if lane:
        for a, b in zip(ks, ks[1:]):
            if a < len(lane) and b < len(lane) and lane[a] and lane[b]:
                cv.tint([_off(pts, m, a, lane[a][0]), _off(pts, m, b, lane[b][0]),
                         _off(pts, m, b, lane[b][1]), _off(pts, m, a, lane[a][1])], COL["lane"])
        cv.flush()
    cv.line([(pts[k][0], pts[k][2]) for k in ks], COL["cl"], 1)


def _draw_furniture(cv, curves, token, w_close, w_edge, w_kerb):
    for name, cs in curves.items():
        role = rf.race_role(name)
        if role == "edge":
            cv.line(cs, COL["edge_L"] if "_edge_L_" in name else COL["edge_R"], w_edge)
        elif role == "kerb":
            for i, (a, b) in enumerate(zip(cs, cs[1:])):          # red/white dashes, like the texture
                cv.line([a, b], COL["kerb"] if (i // 3) % 2 == 0 else COL["kerb2"], w_kerb)
    for name, cs in curves.items():
        if rf.race_role(name) == "close" and rf.race_owner(name) == token:
            cv.line(cs, COL["close"], w_close)


def _draw_dummies(cv, pts, m, d, scale_ok):
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
        col = COL["grid"] if name.startswith("AC_START") else COL["pit"]
        if scale_ok:
            cv.poly(quad, col)
            cv.line([(x, z), (x + tx * (L / 2 + 1.5), z + tz * (L / 2 + 1.5))], col, 2)   # nose tick
        else:
            cv.dot((x, z), 3, col)
    for gi in range(3):
        a, b = pos.get(f"AC_TIME_{gi}_L"), pos.get(f"AC_TIME_{gi}_R")
        if a and b:
            cv.line([(a[0], a[2]), (b[0], b[2])], COL["time"], 3 if scale_ok else 2)
            if scale_ok:
                cv.text(cv.px((a[0], a[2])), "start/finish line" if gi == 0 else f"sector line {gi}", 12, True, COL["time"])


def _legend(cv, x, y, lid, source, totals, lay):
    rows = [("lane", f"the {lid} race lane: where the car can go"), ("close", f"{lid}'s closure wall (shuts off the other direction)"),
            ("edge_L", "curb barrier, forward-left curb (both race versions)"),
            ("edge_R", "curb barrier, forward-right curb (both race versions)"), ("kerb", "race kerb (both race versions)"),
            ("pin", "closure end buried in the far curb barrier"), ("island", "median island"), ("nose", "island nose"),
            ("grid", "starting grid / pit boxes")]
    for i, (key, label) in enumerate(rows):
        yy = y + i * 18
        cv.d.rectangle((x, yy + 3, x + 22, yy + 13), fill=COL[key][:3])
        cv.text((x + 30, yy), label, 13)
    yy = y + len(rows) * 18 + 6
    cv.text((x, yy), f"source: {source}", 12)
    if lay:
        cv.text((x, yy + 18), f"{lid} closure: {lay.get('length_m', 0):.0f} m of wall in {lay.get('objects')} objects "
                              f"({lay.get('rings')} rings, {lay.get('positions', 0):,} positions)", 12)
    if totals and "edge_length_m" in totals:
        cv.text((x, yy + 36), f"common: curb barriers {totals['edge_length_m']:.0f} m in {totals.get('edge_objects')} objects "
                              f"(closed loops, bridges included); kerbs {totals.get('kerb_length_m', 0):.0f} m in "
                              f"{totals.get('kerb_objects')} objects", 12)


def _window(cv_args, pts, widths, m, island_w, lane, k0, half_v):
    cv = Canvas(*cv_args)
    ks = [k % m for k in range(k0 - half_v, k0 + half_v + 1)]
    _draw_base(cv, pts, widths, m, island_w, ks, lane)
    return cv, ks


def _plot_layout(out, lid, lo, cfg, pts, widths, m, island_w, bands, curves, dummies, authored, source, lap=None):
    c = rf.corridors(bands).get(lid) or {}
    token = rf.closure_token(bands, lid)
    lane = c.get("lane_by_vertex")
    y = c.get("closure_y_by_vertex") or []
    pins = sorted({int(v) % m for i, j, _r in rf.closure_runs(bands, lid, m) for v in (i, j)})
    noses = island_noses(island_w, m)
    out.mkdir(parents=True, exist_ok=True)
    lay = (authored or {}).get("layouts", {}).get(lid) if authored else None
    direction = "clockwise (increasing vertex)" if lo.get("direction", "forward") == "forward" else "anticlockwise (decreasing vertex)"
    written = []

    def pin_marks(cv, r):
        for v in pins:
            if y and v < len(y) and y[v] is not None:
                cv.dot(_off(pts, m, v, float(y[v])), r, COL["pin"], (0, 0, 0))

    # overview
    xs, zs = [p[0] for p in pts], [p[2] for p in pts]
    x0, x1, z0, z1 = min(xs) - 60, max(xs) + 60, min(zs) - 60, max(zs) + 60
    s = min(1700.0 / (x1 - x0), 1400.0 / (z1 - z0))
    cv = Canvas(x0, z0, x1, z1, s, pad_px=10, footer_px=260)
    ks = list(range(m)) + [0]
    _draw_base(cv, pts, widths, m, island_w, ks, lane)
    _draw_furniture(cv, curves, token, 3, 2, 3)
    for k in noses:
        cv.dot((pts[k][0], pts[k][2]), 4, COL["nose"], (0, 0, 0))
    pin_marks(cv, 5)
    if lid in dummies:
        _draw_dummies(cv, pts, m, dummies[lid], False)
    marks = ((300, "start/finish v300"), (770, "hairpin v770"), (1085, "Del Cerro 4-way"), (1514, "College/Navajo"),
             (2319, "Navajo/Jackson"), (3297, "Jackson/LMB"), (4454, "I-8 bridge v4454"), (0, "seam v0")) if not lap else \
        tuple((int(c["apex"]), f"corner v{c['apex']}") for c in bands.get("corners") or []) + ((0, f"lap {lap} v0"),)
    for k, label in marks:
        if k >= m:
            continue
        x, yy = cv.px((pts[k][0], pts[k][2]))
        cv.text((x, yy), label, 13, True, anchor=("ra" if x > cv.W - 160 else "la"))
    cv.text((14, 8), f"Lake Murray — {lo.get('name', lid)} ({lid}, {direction}): the race lane and its walls "
                     f"(ledger 0049) — top-down, north up", 18, True)
    _legend(cv, 14, cv.H - 250, lid, source, (authored or {}).get("totals"), lay)
    cv.save(out / "overview.png")
    written.append("overview.png")

    def window(tag, k0, caption, win=180.0, pxm=6.0, extra=None):
        cx, cz = pts[k0 % m][0], pts[k0 % m][2]
        half_v = int(win / 2.5) + 10
        cv, ks_ = _window((cx - win / 2, cz - win / 2, cx + win / 2, cz + win / 2, pxm, 0, 64),
                          pts, widths, m, island_w, lane, k0, half_v)
        _draw_furniture(cv, curves, token, 5, 4, 5)
        for k in noses:
            if abs(pts[k][0] - cx) < win and abs(pts[k][2] - cz) < win:
                cv.dot((pts[k][0], pts[k][2]), 6, COL["nose"], (0, 0, 0))
                cv.text(cv.px((pts[k][0], pts[k][2])), f"nose v{k}", 12, True, COL["nose"])
        for v in pins:
            if abs(pts[v][0] - cx) < win and abs(pts[v][2] - cz) < win and v < len(y) and y[v] is not None:
                p = _off(pts, m, v, float(y[v]))
                cv.dot(p, 7, COL["pin"], (0, 0, 0))
                cv.text(cv.px(p), f"pin v{v}", 12, True, COL["pin"])
        if lid in dummies:
            _draw_dummies(cv, pts, m, dummies[lid], True)
        step = max(3, int(win / 12 / 3))
        for k in range(k0 - half_v, k0 + half_v + 1, step):
            kk = k % m
            cv.text(cv.px((pts[kk][0], pts[kk][2])), f"v{kk}", 11, False, COL["cl"])
        cv.text((8, cv.H - 60), caption, 13 if win < 120 else 14, True)
        cv.text((8, cv.H - 40), f"{lid}, {direction}. Green = the car's lane; red = this version's closure wall; "
                                f"orange / cyan = the curb barriers.", 11)
        cv.text((8, cv.H - 22), (extra + "; " if extra else "") + f"{win:.0f} m window, north up", 11)
        cv.save(out / f"{tag}.png")
        written.append(f"{tag}.png")

    if lap:
        # a LAP (ledger 0054): its own detected corners (barrier_bands.<lap>.json) — the mainline's named windows
        # (Del Cerro, the I-8 end) are mainline vertex numbers
        for c_ in bands.get("corners") or []:
            window(f"corner_{c_['apex']}", int(c_["apex"]), f"Lap {lap} corner v{c_['apex']} (D {c_.get('D_deg')} deg)")
    else:
        for apex, name in CORNERS:
            window(f"corner_{apex}", apex, f"Corner v{apex} — {name}: the whole intersection is open between the curb barriers")
        window("del_cerro_1085", 1085, "Del Cerro 4-way: not a turn — the closure runs across it nose to nose, both side "
                                       "streets stay sealed")
        window("i8_end_4454", 4454, "The I-8 bridge: the closure ends on the bridge's far curb barrier; the bridge and "
                                    "Alvarado are the whole street", win=220.0, pxm=5.0)
    for k in noses:
        window(f"nose_{k}", k, f"Island nose v{k}: the closure passes the tip on the race side — the nose is behind the wall",
               win=70.0, pxm=11.0)
    for v in pins:
        yy = y[v] if v < len(y) else None
        window(f"pin_{v}", v, f"Closure pin v{v}: the wall end is buried in the far curb barrier (no gap, no free end)",
               win=90.0, pxm=9.0, extra=None if yy is None else f"closure centre {float(yy):+.2f} m left of the centreline "
                                                                  f"(forward frame) at v{v}")
    return written


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
    for f in OLD_FILES:
        if (out / f).is_file():
            (out / f).unlink()
    LAP = rf._race_lap()
    cfg0 = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    if not [lo for lo in cfg0.get("layouts", []) if lo.get("race_furniture")]:
        raise SystemExit("[plot-race] no race layout in track.config.json")
    for lap in LAP.groups(cfg0):
        _plot_group(proj, out, planned, lap)
    return 0


def _plot_group(proj, out, planned, lap):
    cfg, pts, widths, m, island_w, bands, curves, dummies, authored, source = _load(proj, planned, lap)
    race = [lo for lo in cfg.get("layouts", []) if lo.get("race_furniture") and (lo.get("lap") or None) == lap]
    for lo in race:
        lid = str(lo["id"])
        if lid not in rf.corridors(bands):
            raise SystemExit(f"[plot-race] no corridors.{lid} in {rf._race_lap().bands_file(lap)} — re-run "
                             f"tools/barrier_bands.py (v2)")
        written = _plot_layout(out / lid, lid, lo, cfg, pts, widths, m, island_w, bands, curves, dummies, authored, source,
                               lap=lap)
        where = (f"{len(CORNERS)} corners, Del Cerro, I-8 end" if not lap else
                 f"lap {lap}: {sum(1 for w in written if w.startswith('corner_'))} corners")
        print(f"[plot-race] {lid}: {len(written)} pictures -> {out / lid} (overview, {where}, "
              f"{sum(1 for w in written if w.startswith('nose_'))} noses, {sum(1 for w in written if w.startswith('pin_'))} pins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

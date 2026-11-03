"""Streetlight posts for an ENGINE-DRAFT track (ledger 0070 D1; Kevin 2026-11-03 for Sand Creek: "same lamps as lake
murray"). Writes data/lights.local.json, the post plan tools/author_lamps_blend.py stands the real lamp model on.

Why this exists. On Lake Murray the plan is written by the v021 assembler (scripts-v021/blender/build_loop_blend.py
build_streetlights for the loop, scripts-v021/geometry/streetlights.py for the north pieces). An engine-draft track
(source.type osm / kml -> build_mesh -> the underlay) has no assembler, so no lamp plan, so `lamps` had nothing to
stand. This is the same plan, ported, reading what an engine draft has: the lap (data/centerline.local.json), the
built road / wall / ground surfaces of the draft (data/track.obj, build_mesh's output: 1ROAD* = every road, the grid
streets included; 1WALL* = every wall; 1GRASS* = the ground), the deck spans (data/bridge.spans.auto.json) and, when a
track has them, the junction pads' outlines (data/pads.plan.json).

THE RULES (ported; every [invented] number is in fleet/GATES-CHANGELOG.md "engine-draft lamps"):
  * the loop's walk (build_streetlights): a station every SPACING_M (55 m) from START_M, alternating sides, the post
    SIDE_OFF_M past the pavement edge, the head ARM_M (1.8 m) road-ward of it at HEAD_OVER_GROUND_M (8.8 m) over the
    draft ground under the post — exactly the record author_lamps_blend.py's base rule reads back (road-ward = head ->
    nearest centreline vertex; the head lies on the segment from the base to that vertex, so the author finds the same
    base);
  * no two posts within MIN_GAP_M (25 m);
  * no post where the road stands more than CUT_WALL_M (6 m) over the ground under it (build_streetlights' cut-wall
    rule), and none beside a deck span (+-BRIDGE_PAD_M);
  * the pole's footprint (the axis + a ring of the LED model's mast radius + author_lamps_blend.ROAD_SETBACK_M, read in
    FOOTPRINT_DIRS directions) is on no road surface — the lap, its shoulder sheet, any grid street (streetlights.py's
    "clear of EVERY other pavement", read on the built surfaces as the author's own self-check reads them);
  * the pole stands >= WALL_CLEAR_M (0.5 m, the integration brief; author_lamps_blend.WALL_CLEAR_M) + its mast radius
    from every wall in plan, and >= PAD_CLEAR_M from a junction pad's outline (streetlights.py);
  * a blocked station slides along the road (SLIDE_M in SLIDE_STEP_M steps), then tries the other side, then is
    skipped with its reasons recorded — never silently (streetlights.py).

Opt-in per track: track.config.json scenery.streetlights.planner == "engine_draft". Absent: nothing is read or written
(Lake Murray's lights.local.json is its assembler's and is never touched here).

    python tools/plan_streetlights.py <project-dir> [--plot <png>]

Pure python, no bpy; tests/tools/test_plan_streetlights.py.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]

SPACING_M = 55.0          # build_streetlights spacing (the loop's draft)
START_M = SPACING_M       # the loop's walk starts one spacing in
MIN_GAP_M = 25.0          # build_streetlights: no two posts closer than this
ARM_M = 1.8               # build_streetlights arm; author_lamps_blend.ARM_M
HEAD_OVER_GROUND_M = 8.8  # build_streetlights head rule; author_lamps_blend.HEAD_OVER_GROUND_M
CUT_WALL_M = 6.0          # build_streetlights: road more than this over the ground under the post = a cut wall / a deck
SIDE_OFF_M = 3.6          # [invented] post axis past the pavement edge: build_mesh's 2.5 m verge sheet (1ROAD_shoulder)
#                           + the footprint ring (0.124 + 0.46) + 0.5 m to spare
SLIDE_M = 12.0            # streetlights.py SLIDE_M [invented there]
SLIDE_STEP_M = 2.0        # streetlights.py SLIDE_STEP_M [invented there]
WALL_CLEAR_M = 0.5        # author_lamps_blend.WALL_CLEAR_M: the pole >= 0.5 m clear of a barrier
PAD_CLEAR_M = 3.0         # streetlights.py PAD_CLEAR_M [invented there]
BRIDGE_PAD_M = 10.0       # [invented] no post within this of a deck span's ends (draft vs finished stations differ <= 5 m)
ROAD_SETBACK_M = 0.46     # author_lamps_blend.ROAD_SETBACK_M
MAST_RADIUS_M = 0.1241    # assets/models/streetlight_led.json mast_radius_m (read from the file when present)
FOOTPRINT_DIRS = 16       # author_lamps_blend.FOOTPRINT_DIRS
CELL_M = 4.0              # the triangle hash's cell
CORRIDOR_M = 40.0         # only the draft's surfaces within this of the lap are read


# ----------------------------------------------------------------------------------------------- surfaces
class Surfaces:
    """the draft's built surfaces in plan: road / wall / ground triangles of data/track.obj (x E, y up, z N), hashed on
    CELL_M cells. ``road_at(x, z)`` = is a road triangle under (x, z); ``ground_y(x, z)`` = the highest ground (1GRASS*)
    under it; ``wall_dist(x, z, r)`` = plan distance to the nearest wall triangle within r (inf beyond)."""

    def __init__(self, tris_by_kind: dict):
        self.cells = {k: {} for k in ("road", "wall", "ground")}
        self.tris = {k: [] for k in ("road", "wall", "ground")}
        for kind, tris in tris_by_kind.items():
            for t in tris:
                k = len(self.tris[kind])
                self.tris[kind].append(t)
                xs = [p[0] for p in t]
                zs = [p[2] for p in t]
                for ci in range(int(math.floor(min(xs) / CELL_M)), int(math.floor(max(xs) / CELL_M)) + 1):
                    for cj in range(int(math.floor(min(zs) / CELL_M)), int(math.floor(max(zs) / CELL_M)) + 1):
                        self.cells[kind].setdefault((ci, cj), []).append(k)

    def _near(self, kind, x, z, r=0.0):
        seen = set()
        for ci in range(int(math.floor((x - r) / CELL_M)), int(math.floor((x + r) / CELL_M)) + 1):
            for cj in range(int(math.floor((z - r) / CELL_M)), int(math.floor((z + r) / CELL_M)) + 1):
                for k in self.cells[kind].get((ci, cj), ()):
                    if k not in seen:
                        seen.add(k)
                        yield self.tris[kind][k]

    @staticmethod
    def _bary(t, x, z):
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(d) < 1e-12:
            return None
        w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
        w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
        w2 = 1.0 - w0 - w1
        if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
            return None
        return w0 * ay + w1 * by + w2 * cy

    def road_at(self, x, z):
        return any(self._bary(t, x, z) is not None for t in self._near("road", x, z))

    def road_y(self, x, z):
        ys = [y for y in (self._bary(t, x, z) for t in self._near("road", x, z)) if y is not None]
        return max(ys) if ys else None

    def ground_y(self, x, z):
        ys = [y for y in (self._bary(t, x, z) for t in self._near("ground", x, z)) if y is not None]
        return max(ys) if ys else None

    def wall_dist(self, x, z, r):
        best = float("inf")
        for t in self._near("wall", x, z, r):
            if self._bary(t, x, z) is not None:
                return 0.0
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                best = min(best, _seg_dist(x, z, a[0], a[2], b[0], b[2]))
        return best


def _seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 <= 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - ax - dx * t, pz - az - dz * t)


def kind_of(group: str) -> str | None:
    g = group.upper()
    if g.startswith("1ROAD"):
        return "road"
    if g.startswith("1WALL"):
        return "wall"
    if g.startswith("1GRASS"):
        return "ground"
    return None


def read_obj(path: Path, keep_xz=None) -> dict:
    """the road / wall / ground triangles of an OBJ (``g``/``o`` group names; faces fanned), optionally only those whose
    plan bounding box touches a 10 m cell for which ``keep_xz(x, z)`` is true"""
    verts, out, kind = [], {"road": [], "wall": [], "ground": []}, None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            c = ln[:2]
            if c == "v ":
                p = ln.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif c in ("g ", "o "):
                kind = kind_of(ln[2:].strip())
            elif c == "f " and kind is not None:
                idx = [int(tok.split("/")[0]) for tok in ln.split()[1:]]
                pts = [verts[i - 1] if i > 0 else verts[i] for i in idx]
                if keep_xz is not None and not any(keep_xz(p[0], p[2]) for p in pts):
                    xs = [p[0] for p in pts]
                    zs = [p[2] for p in pts]
                    if max(xs) - min(xs) < 10.0 and max(zs) - min(zs) < 10.0:
                        continue          # a small face with no corner in the corridor
                    if not any(keep_xz(x + 0.5, z + 0.5)
                               for x in range(int(math.floor(min(xs) / 10.0)) * 10, int(max(xs)) + 10, 10)
                               for z in range(int(math.floor(min(zs) / 10.0)) * 10, int(max(zs)) + 10, 10)):
                        continue
                for k in range(1, len(pts) - 1):
                    out[kind].append((pts[0], pts[k], pts[k + 1]))
    return out


# ----------------------------------------------------------------------------------------------- the lap
class Lap:
    def __init__(self, pts, widths):
        self.pts = [tuple(p) for p in pts]
        self.w = [float(w) for w in widths]
        self.cum = [0.0]
        for i in range(1, len(self.pts)):
            self.cum.append(self.cum[-1] + math.hypot(self.pts[i][0] - self.pts[i - 1][0],
                                                      self.pts[i][2] - self.pts[i - 1][2]))
        self.length = self.cum[-1]
        self._h = {}
        for k, p in enumerate(self.pts):
            self._h.setdefault((int(p[0] // 30.0), int(p[2] // 30.0)), []).append(k)

    def at(self, s):
        """(x, y, z), left normal (nx, nz), width at station s"""
        i = max(0, min(len(self.pts) - 2, bisect.bisect_right(self.cum, s) - 1))
        L = self.cum[i + 1] - self.cum[i]
        t = 0.0 if L <= 1e-9 else (s - self.cum[i]) / L
        a, b = self.pts[i], self.pts[i + 1]
        p = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
        ia, ib = max(0, i - 1), min(len(self.pts) - 1, i + 2)
        tx, tz = self.pts[ib][0] - self.pts[ia][0], self.pts[ib][2] - self.pts[ia][2]
        Lt = math.hypot(tx, tz) or 1.0
        w = self.w[i] + (self.w[i + 1] - self.w[i]) * t
        return p, (-tz / Lt, tx / Lt), w

    def nearest_vertex(self, x, z):
        """author_lamps_blend's road-ward rule reads the nearest centreline VERTEX"""
        cx, cz = int(x // 30.0), int(z // 30.0)
        best = None
        for r in range(0, 40):
            for i in range(cx - r, cx + r + 1):
                for j in range(cz - r, cz + r + 1):
                    if max(abs(i - cx), abs(j - cz)) != r:
                        continue
                    for k in self._h.get((i, j), ()):
                        d = (self.pts[k][0] - x) ** 2 + (self.pts[k][2] - z) ** 2
                        if best is None or d < best[0]:
                            best = (d, k)
            if best is not None and math.sqrt(best[0]) < r * 30.0:
                break
        return best[1]

    def corridor(self, r, cell=10.0):
        """a test (x, z) -> True within about r of the lap (10 m cells, dilated): which surfaces are worth reading"""
        n = int(math.ceil(r / cell))
        cells = set()
        for p in self.pts:
            ci, cj = int(p[0] // cell), int(p[2] // cell)
            for i in range(ci - n, ci + n + 1):
                for j in range(cj - n, cj + n + 1):
                    cells.add((i, j))
        return lambda x, z: (int(x // cell), int(z // cell)) in cells


def _in_poly(poly, x, z):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            inside = not inside
    return inside


def _poly_dist(poly, x, z):
    return min(_seg_dist(x, z, poly[i][0], poly[i][1], poly[(i + 1) % len(poly)][0], poly[(i + 1) % len(poly)][1])
               for i in range(len(poly)))


# ----------------------------------------------------------------------------------------------- the plan
def plan(lap: Lap, surf: Surfaces, *, spans=(), pads=(), rules=None):
    """The posts along the lap. ``spans`` = [(s0, s1)] deck stations; ``pads`` = [(id, outline_xz)]. Returns
    {"lamps": [...], "skipped": [...], "rules": {...}} — each lamp: head [x, y, z], base_xz, roadward_xz, vertex (the
    nearest centreline vertex, which the author's road-ward rule reads), station_m, side, ground_y, road_y."""
    R = dict(spacing_m=SPACING_M, min_gap_m=MIN_GAP_M, side_off_m=SIDE_OFF_M, arm_m=ARM_M,
             head_over_ground_m=HEAD_OVER_GROUND_M, cut_wall_m=CUT_WALL_M, slide_m=SLIDE_M, slide_step_m=SLIDE_STEP_M,
             wall_clear_m=WALL_CLEAR_M, pad_clear_m=PAD_CLEAR_M, bridge_pad_m=BRIDGE_PAD_M,
             footprint_radius_m=round(MAST_RADIUS_M + ROAD_SETBACK_M, 4), mast_radius_m=MAST_RADIUS_M)
    R.update(rules or {})
    ring = R["footprint_radius_m"]
    placed, lamps, skipped = [], [], []

    def candidate(s, side):
        p, (nx, nz), w = lap.at(s)
        off = w / 2.0 + R["side_off_m"]
        bx, bz = p[0] + nx * side * off, p[2] + nz * side * off
        return bx, bz, p[1]

    def why_blocked(s, side, bx, bz, road_y):
        why = []
        for a, b in spans:
            if a - R["bridge_pad_m"] <= s <= b + R["bridge_pad_m"]:
                return ["deck"]
        for px, pz in placed:
            if (px - bx) ** 2 + (pz - bz) ** 2 < R["min_gap_m"] ** 2:
                why.append("gap")
                break
        foot = [(bx, bz)] + [(bx + ring * math.cos(2 * math.pi * k / FOOTPRINT_DIRS),
                              bz + ring * math.sin(2 * math.pi * k / FOOTPRINT_DIRS)) for k in range(FOOTPRINT_DIRS)]
        if any(surf.road_at(x, z) for x, z in foot):
            why.append("road")
        g = surf.ground_y(bx, bz)
        if g is None:
            why.append("no_ground")
        elif road_y - g > R["cut_wall_m"]:
            why.append("cut_wall")
        if surf.wall_dist(bx, bz, R["wall_clear_m"] + R["mast_radius_m"] + 1.0) < R["wall_clear_m"] + R["mast_radius_m"]:
            why.append("wall")
        for pid, poly in pads:
            if _in_poly(poly, bx, bz) or _poly_dist(poly, bx, bz) < R["pad_clear_m"]:
                why.append(f"pad:{pid}")
        return why

    def place(s, side, bx, bz):
        k = lap.nearest_vertex(bx, bz)
        c = lap.pts[k]
        dx, dz = c[0] - bx, c[2] - bz
        L = math.hypot(dx, dz) or 1e-9
        rx, rz = dx / L, dz / L
        g = surf.ground_y(bx, bz)
        hx, hz = bx + rx * R["arm_m"], bz + rz * R["arm_m"]
        lamps.append({"head": [round(hx, 3), round(g + R["head_over_ground_m"], 3), round(hz, 3)],
                      "base_xz": [round(bx, 3), round(bz, 3)], "roadward_xz": [round(rx, 5), round(rz, 5)],
                      "vertex": k, "station_m": round(s, 1), "side": "L" if side > 0 else "R",
                      "ground_y": round(g, 3), "road_y": round(c[1], 3)})
        placed.append((bx, bz))

    s, side = START_M, 1
    while s < lap.length - R["min_gap_m"]:
        done, reasons = None, []
        for sd in (side, -side):
            for k in range(0, int(R["slide_m"] / R["slide_step_m"]) + 1):
                for du in ((0.0,) if k == 0 else (k * R["slide_step_m"], -k * R["slide_step_m"])):
                    ss = s + du
                    if ss <= 0.0 or ss >= lap.length:
                        continue
                    bx, bz, ry = candidate(ss, sd)
                    why = why_blocked(ss, sd, bx, bz, ry)
                    if not why:
                        done = (ss, sd, bx, bz)
                        break
                    reasons.append(why)
                    if why == ["deck"]:
                        break
                if done or (reasons and reasons[-1] == ["deck"]):
                    break
            if done or (reasons and reasons[-1] == ["deck"]):
                break
        if done:
            place(*done)
            side = -done[1]
        else:
            skipped.append({"station_m": round(s, 1), "side": "L" if side > 0 else "R",
                            "why": sorted({r for w in reasons for r in w})})
            side = -side
        s += R["spacing_m"]
    return {"lamps": lamps, "skipped": skipped, "rules": R}


# ----------------------------------------------------------------------------------------------- I/O
def _mast_radius():
    p = AIROSO / "assets" / "models" / "streetlight_led.json"
    try:
        return float(json.loads(p.read_text(encoding="utf-8"))["mast_radius_m"])
    except (OSError, KeyError, ValueError):
        return MAST_RADIUS_M


def load(project: Path):
    data = project / "data"
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    lap = Lap(cl["points_xyz_m"], cl["widths_m"])
    obj = data / "track.obj"
    if not obj.exists():
        raise SystemExit(f"[lamps_plan] FATAL: {obj} missing — the plan reads the draft's built surfaces (run the mesh "
                         f"step first)")
    tris = read_obj(obj, keep_xz=lap.corridor(CORRIDOR_M + max(lap.w) / 2.0))
    surf = Surfaces(tris)
    spans = []
    bsp = data / "bridge.spans.auto.json"
    if bsp.exists():
        spans = [tuple(map(float, s)) for s in json.loads(bsp.read_text(encoding="utf-8"))]
    pads = []
    pp = data / "pads.plan.json"
    if pp.exists():
        for pad in json.loads(pp.read_text(encoding="utf-8")).get("pads", []):
            out = (pad.get("design") or {}).get("outline_xz") or pad.get("outline_xz")
            if out:
                pads.append((str(pad.get("id")), [tuple(q) for q in out]))
    return lap, surf, spans, pads, {k: len(v) for k, v in tris.items()}


def write(project: Path, res: dict, counts: dict, sl_cfg: dict) -> Path:
    out = {"_doc": "tools/plan_streetlights.py (ledger 0070 D1): the engine draft's lamp posts. lampheads = the draft "
                   "heads (local x E, y up, z N; the arm tip ARM_M road-ward of the post, HEAD_OVER_GROUND_M over the "
                   "draft ground) that tools/author_lamps_blend.py stands scenery.streetlights.model on; lamps = the same "
                   "posts with their base, road-ward unit, station and side; skipped = every station with no post, and why.",
           "planner": "tools/plan_streetlights.py", "model": sl_cfg.get("model"),
           "lampheads": [l["head"] for l in res["lamps"]], "lamps": res["lamps"], "skipped": res["skipped"],
           "rules": res["rules"], "surfaces_read": counts}
    p = project / "data" / "lights.local.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return p


def run(project, plot=None):
    project = Path(project)
    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
    sl = (cfg.get("scenery") or {}).get("streetlights") or {}
    if str(sl.get("planner", "")) != "engine_draft":
        print("[lamps_plan] scenery.streetlights.planner is not \"engine_draft\": nothing planned (an assembler track "
              "writes its own data/lights.local.json)")
        return None
    rules = {k: float(sl[k]) for k in ("spacing_m", "min_gap_m", "side_off_m") if k in sl}
    global MAST_RADIUS_M
    MAST_RADIUS_M = _mast_radius()
    lap, surf, spans, pads, counts = load(project)
    res = plan(lap, surf, spans=spans, pads=pads, rules=rules)
    p = write(project, res, counts, sl)
    why = {}
    for sk in res["skipped"]:
        for w in sk["why"]:
            why[w] = why.get(w, 0) + 1
    print(f"[lamps_plan] {len(res['lamps'])} posts on {lap.length:.0f} m (every {res['rules']['spacing_m']:g} m, "
          f"alternating sides, {res['rules']['side_off_m']:g} m past the pavement edge); {len(res['skipped'])} stations "
          f"skipped {dict(sorted(why.items()))}; surfaces read {counts} -> {p}")
    if plot:
        plot_plan(project, res, lap, plot)
    return res


def plot_plan(project, res, lap, png):
    """top-down: the lap's pavement, the posts (base dot + arm to the head), the skipped stations (x)"""
    from PIL import Image, ImageDraw
    xs = [p[0] for p in lap.pts]
    zs = [p[2] for p in lap.pts]
    pad = 40.0
    x0, x1, z0, z1 = min(xs) - pad, max(xs) + pad, min(zs) - pad, max(zs) + pad
    sc = 2400.0 / (x1 - x0)
    W, H = int((x1 - x0) * sc), int((z1 - z0) * sc)
    im = Image.new("RGB", (W, H), (245, 245, 240))
    d = ImageDraw.Draw(im)

    def P(x, z):
        return ((x - x0) * sc, (z1 - z) * sc)
    left, right = [], []
    for s in range(0, int(lap.length), 3):
        p, (nx, nz), w = lap.at(s)
        left.append(P(p[0] + nx * w / 2, p[2] + nz * w / 2))
        right.append(P(p[0] - nx * w / 2, p[2] - nz * w / 2))
    d.polygon(left + right[::-1], fill=(150, 150, 150))
    for l in res["lamps"]:
        bx, bz = l["base_xz"]
        hx, _hy, hz = l["head"]
        d.line([P(bx, bz), P(hx, hz)], fill=(200, 120, 0), width=2)
        x, z = P(bx, bz)
        d.ellipse([x - 4, z - 4, x + 4, z + 4], fill=(230, 160, 0), outline=(0, 0, 0))
    for sk in res["skipped"]:
        p, (nx, nz), w = lap.at(sk["station_m"])
        x, z = P(p[0], p[2])
        d.line([x - 5, z - 5, x + 5, z + 5], fill=(200, 0, 0), width=2)
        d.line([x - 5, z + 5, x + 5, z - 5], fill=(200, 0, 0), width=2)
    d.text((10, 10), f"{len(res['lamps'])} posts (orange: base + arm to the head), {len(res['skipped'])} skipped "
                     f"stations (red x); tools/plan_streetlights.py", fill=(0, 0, 0))
    im.save(png)
    print(f"[lamps_plan] plot -> {png}")


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    plot = None
    if "--plot" in a:
        i = a.index("--plot")
        plot = a[i + 1]
        del a[i:i + 2]
    if len(a) != 1:
        raise SystemExit("usage: python tools/plan_streetlights.py <project-dir> [--plot <png>]")
    run(a[0], plot)


if __name__ == "__main__":
    main()

"""verify_fold_fans — ledger 0050's gate: every LEVELLED mainline fold pinch, read on every layout's BUILT gate OBJ.

THE DEFECT (Kevin, from the seat, v0.17.1: "the small steps are a problem at jackson/navajo"). The road is a 24 m
ribbon swung round a 7.4 m corner at Navajo -> Jackson, so its inside edge folds back over itself and the weld pinches
it to one point X. The legs meeting at X came from road ~19 m apart on a 2.7 % climb (108.81 / 109.31 m); X took the
higher, the low leg's last row stayed 6 cm away, and the triangle between them stood at 901 %: a lip across the whole
inside half of the road, 13 cm 3 m from the centre line, 47 cm at the kerb. drive_test filed the street's 0.24 m of it
as an exempt "apron step"; the race layouts counted it (severe 31 / 28) and it shipped as "the next owner's".
tools/mouth_weld.unfold_line now puts X at the MIDPOINT of its legs and eases each leg's last FOLD_LEVEL_ROWS rows to
it. This gate proves that on the artifact (L5), around every pinch the weld levelled (data/mouth_welds.json
folds.MAINLINE.levelled; a file from before 0050 has none, and the pinches are then re-found on the ROAD edge rebuilt
from the gate centreline, so the v0.17.1 build can be judged — and fails):

  scope   per pinch, centreline rows k - B - PAD .. l + 1 + B + PAD (B = the weld's level_rows, PAD = WINDOW_PAD_ROWS);
          per layout in track.config.json layouts[] (street: data/track.obj; a race layout: data/track.<id>.obj);
          the DRIVEN lane — street: +-(w/2 - 0.5) less the median island (+-(island/2 + 0.4), data/median_bands.json,
          the way drive_test keeps the inner wheel off the island face); race: barrier_bands.json
          corridors.<id>.lane_by_vertex. The real median-island curb (0.20 m, street, rows 2266-2295 at Navajo) is not
          driven surface, and it is not a step here for THAT reason: it is outside the lane (the 0050 review's
          BLOCKER 2 — scoped by the lane, never by exempting a curb that stands in one).
  surface the top physics surface (1ROAD / 1KERB / 1GRASS) under each sample, exact (point in triangle).
  paths   every PATH_DO_M across the lane, each cut at its own self-intersection (mouth_weld.unfold_line, level off:
          the line a wheel can actually take round the inside of a corner tighter than its offset), every PATH_DS_M.
  FAIL on (1) FINE: a rise over 0.10 m beyond the previous metre's grade >= FINE_STEP_M, unless a 1KERB_race kerb is on
          one side and the rise is <= KERB_LIP_M (the authored kerb); (2) DT: a 1 m second difference > DT_MAX_M unless
          the metre touches such a kerb; (3) two 1ROAD vertices within JUMP_PLAN_M in plan whose heights differ by
          >= FINE_STEP_M + TRI_SLOPE_MAX x their distance (a sheet edge / riser, direction-free); (4) 1GRASS on top of
          the lane more than GRASS_OVER_M over the pavement beneath it, in rows k - B .. l + 1 + B (the saddle history:
          grass 0.04-0.22 m through the race lane's inside edge; the prep pins grass 0.02 m under the deck at its
          vertices, so a big facet can graze the deck by millimetres between them — counted and reported, not a step); (5) a 1ROAD triangle of plan area >= TRI_AREA_MIN sloping more than
          TRI_SLOPE_MAX; (6) the built X not within APEX_TOL_M of the midpoint of its legs (the proof the leveller ran);
          (7) race layouts: a 1WALL cell (0.5 m, base = the 3x3 minimum — the 0050 review's aggregation) within
          WALL_RADIUS_M of X whose base + 0.05 m bury is outside +-WALL_BAND_M of no_route's reference (its projected
          centre line + 0.10).

    python tools/verify_fold_fans.py <project> [--layout <id> ...] [--json <out>]

Writes data/verify_fold_fans.json; exit 1 on FAIL, 2 on an input error. Pure Python (the ship chain's interpreter has
no numpy). Thresholds: fleet/GATES-CHANGELOG.md (2026-10-13, ledger 0050), every invented one marked there.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mouth_weld as mw  # noqa: E402  (pure geometry)
import no_route as nr  # noqa: E402  (its centre-line reference, read-only)

PATH_DO_M = 0.25         # [invented] wheel paths across the lane
PATH_DS_M = 0.05         # [invented] samples along a path
FINE_STEP_M = 0.02       # the diagnosis' step a tyre hits
FINE_WIN_M = 0.10        # [invented] the rise is measured over this
KERB_LIP_M = 0.05 + 0.005  # the authored race kerb (0.05 m) + 5 mm sampling [invented]
DT_MAX_M = 0.06          # drive_test STEP_SEVERE_M, reused
WINDOW_PAD_ROWS = 4      # [invented] rows surveyed past each leg's eased window
JUMP_PLAN_M = 0.10       # [invented] road vertices this close in plan are one place
GRASS_OVER_M = 0.02      # [invented] = FINE_STEP_M: grass standing this far over the pavement beneath is a step in the lane
TRI_AREA_MIN = 0.01      # [invented] m^2 of plan area
TRI_SLOPE_MAX = 0.25     # [invented] the installed riser was 9.01
APEX_TOL_M = 0.01        # [invented]
WALL_RADIUS_M = 25.0     # [invented]
WALL_BAND_M = mw.FOLD_HALF_JUMP_MAX_M   # 0.28: no_route's [0.20, 0.90] band, a 1.20 m K-rail buried 0.05, less 0.02
WALL_CELL_M = 0.5        # the 0050 review's walls_base aggregation
HASH_M = 1.0


class InputError(Exception):
    pass


def _load(p: Path):
    if not p.exists():
        raise InputError(f"{p} does not exist")
    return json.loads(p.read_text(encoding="utf-8"))


def gate_obj(data: Path, lid: str, race: bool) -> Path:
    return data / (f"track.{lid}.obj" if race else "track.obj")


def read_obj_region(path: Path, boxes):
    """([(a, b, c, group index)], group names) for every face whose plan bounding box meets any (x0, z0, x1, z1)"""
    vx = []
    tris, groups = [], []
    cur = -1
    with path.open(encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            k = ln[:2]
            if k == "v ":
                p = ln.split()
                vx.append((float(p[1]), float(p[2]), float(p[3])))
            elif k == "f ":
                p = ln.split()
                ids = [int(q.partition("/")[0]) - 1 for q in p[1:]]
                pts = [vx[i] for i in ids]
                fx0, fx1 = min(q[0] for q in pts), max(q[0] for q in pts)
                fz0, fz1 = min(q[2] for q in pts), max(q[2] for q in pts)
                if not any(fx0 <= x1 and fx1 >= x0 and fz0 <= z1 and fz1 >= z0 for x0, z0, x1, z1 in boxes):
                    continue
                for t in range(1, len(ids) - 1):
                    tris.append((pts[0], pts[t], pts[t + 1], cur))
            elif k == "o " or k == "g ":
                groups.append(ln[2:].strip())
                cur = len(groups) - 1
    return tris, groups


class Surface:
    """the top of a set of triangles at a plan point (exact barycentric), with the owner group"""

    def __init__(self, tris):
        self.tris = tris
        self.cells = {}
        for i, (a, b, c, _g) in enumerate(tris):
            x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
            z0, z1 = min(a[2], b[2], c[2]), max(a[2], b[2], c[2])
            for cx in range(int(math.floor(x0 / HASH_M)), int(math.floor(x1 / HASH_M)) + 1):
                for cz in range(int(math.floor(z0 / HASH_M)), int(math.floor(z1 / HASH_M)) + 1):
                    self.cells.setdefault((cx, cz), []).append(i)

    def top(self, x, z):
        best, own = None, -1
        for i in self.cells.get((int(math.floor(x / HASH_M)), int(math.floor(z / HASH_M))), ()):
            a, b, c, g = self.tris[i]
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            w2 = 1.0 - w0 - w1
            if w0 < -1e-7 or w1 < -1e-7 or w2 < -1e-7:
                continue
            y = w0 * a[1] + w1 * b[1] + w2 * c[1]
            if best is None or y > best:
                best, own = y, g
        return best, own


# ----------------------------------------------------------------------------------------------- pinches
def normals(P, closed):
    n = len(P) - 1 if closed else len(P)
    out = []
    for i in range(n):
        a = P[(i - 1) % n] if closed or i > 0 else P[i]
        b = P[(i + 1) % n] if closed or i < n - 1 else P[i]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1e-9
        out.append((-tz / L, tx / L))                 # LEFT normal (ribbon.road_ribbon / barrier_bands)
    return out


def pinches_from(welds, P, W, closed):
    """([{k, l, X, y_k, y_l, lane, source}], B) — the weld's own record when it has one, else re-found on the ROAD edge
    rebuilt from the gate centreline (heights = centre + the 0.10 m deck lift; pre-0050 weld files)"""
    folds = ((welds or {}).get("folds") or {}).get("MAINLINE") or {}
    rec = [q for q in folds.get("levelled") or [] if isinstance(q, dict) and (q.get("line") or [None])[0] == "road"]
    if rec:
        return [{"k": int(q["k"]), "l": int(q["l"]), "X": tuple(q["X"]), "y_k": float(q["y_k"]), "y_l": float(q["y_l"]),
                 "lane": int(q["line"][1]), "source": "mouth_welds.json levelled"} for q in rec], \
            int(folds.get("level_rows") or mw.FOLD_LEVEL_ROWS)
    cuts = [c for c in folds.get("cuts") or [] if c and c[0] == "road"]
    n = len(P) - 1 if closed else len(P)
    N = normals(P, closed)
    out = []
    for lane in sorted({int(c[1]) for c in cuts}):
        sgn = 1.0 if lane == 0 else -1.0
        E = [(P[i][0] + sgn * N[i][0] * W[i] / 2.0, P[i][1] + 0.10, P[i][2] + sgn * N[i][1] * W[i] / 2.0) for i in range(n)]
        C = [(P[i][0], P[i][1] + 0.10, P[i][2]) for i in range(n)]
        rep = []
        mw.unfold_line(E, C, closed, strict=False, level=True, half_jump_max=None, report=rep)
        want = [(int(c[-2]) % n, int(c[-1]) % n) for c in cuts if int(c[1]) == lane]
        cyc = lambda a, b: min(abs(a - b), n - abs(a - b))
        for q in rep:
            if any(cyc(w[0], q["k"] % n) <= 2 and cyc(w[1], q["l"] % n) <= 2 for w in want):
                out.append({"k": q["k"], "l": q["l"], "X": tuple(q["X"]), "y_k": q["y_k"], "y_l": q["y_l"], "lane": lane,
                            "source": "re-found on the gate centreline (no levelled record: a pre-0050 weld)"})
    return out, mw.FOLD_LEVEL_ROWS


def _interp(ss, sl, vals):
    out, j = [], 0
    for s in ss:
        while j < len(sl) - 2 and sl[j + 1] < s:
            j += 1
        a, b = sl[j], sl[j + 1]
        f = 0.0 if b <= a else (s - a) / (b - a)
        out.append(vals[j] + (vals[j + 1] - vals[j]) * f)
    return out


# ----------------------------------------------------------------------------------------------- the survey
def survey_pinch(pin, B, P, W, N, closed, lane_of, surf, paved, tris, names, island, race, cl_line):
    n = len(P) - 1 if closed else len(P)
    k, l = pin["k"], pin["l"]
    rows = [r % n for r in range(k - B - WINDOW_PAD_ROWS, l + 2 + B + WINDOW_PAD_ROWS) if closed or 0 <= r < n]
    # (4)'s rows: the ones the leveller moves (weight > 0: k-B+1..k, the fan k+1..l, l+1..l+B) — grass the levelling
    # could expose; grass beyond them is drive_test's soft-top count (held to the baseline), not this gate's
    eased = {r % n for r in range(k - B + 1, l + 1 + B) if closed or 0 <= r < n}
    upper = [nm.upper() for nm in names]
    kind = lambda g: "" if g < 0 else ("road" if upper[g].startswith("1ROAD") else
                                       "rkerb" if upper[g].startswith("1KERB_RACE") else
                                       "grass" if upper[g].startswith("1GRASS") else
                                       "kerb" if upper[g].startswith("1KERB") else "other")
    nm = lambda g: names[g] if g >= 0 else "-"
    fails = []
    info = {"rows": [rows[0], rows[-1]], "paths": 0, "paths_with_step": 0, "kerb_lip_max_m": 0.0,
            "fine_max_m": 0.0, "dt_max_m": 0.0, "grass_on_top": 0, "grass_over_max_m": 0.0}
    C = [tuple(P[r]) for r in rows]
    lanes = [lane_of(r) for r in rows]
    lo_all = min(a for a, _b in lanes)
    hi_all = max(b for _a, b in lanes)
    k1, k10 = int(round(1.0 / PATH_DS_M)), int(round(FINE_WIN_M / PATH_DS_M))
    worst = []
    o = math.ceil(lo_all / PATH_DO_M) * PATH_DO_M
    while o <= hi_all + 1e-9:
        E = [(P[r][0] + N[r][0] * o, P[r][1], P[r][2] + N[r][1] * o) for r in rows]
        E2, _done, _left = mw.unfold_line(E, C, False, window=40, strict=False, level=False)
        pts, keep, rr = [], [], []
        for idx, e in enumerate(E2):
            if pts and math.hypot(e[0] - pts[-1][0], e[2] - pts[-1][2]) < 1e-6:
                continue
            a, b = lanes[idx]
            ok = a - 1e-6 <= o <= b + 1e-6
            r = rows[idx]
            if not race and island(r) > 0 and abs(o) < island(r) / 2.0 + 0.4:
                ok = False
            pts.append(e); keep.append(1.0 if ok else 0.0); rr.append(r)
        if len(pts) < 3:
            o += PATH_DO_M
            continue
        sl = [0.0]
        for i in range(1, len(pts)):
            sl.append(sl[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
        ss = [i * PATH_DS_M for i in range(int(sl[-1] / PATH_DS_M) + 1)]
        px = _interp(ss, sl, [p[0] for p in pts])
        pz = _interp(ss, sl, [p[2] for p in pts])
        kin = [v > 0.999 for v in _interp(ss, sl, keep)]
        rowi, j = [], 0
        for s in ss:
            while j < len(sl) - 2 and sl[j + 1] <= s:
                j += 1
            rowi.append(rr[j])
        h, ow = [], []
        for x, z in zip(px, pz):
            y, g = surf.top(x, z)
            h.append(y); ow.append(g)
        ok = [h[i] is not None and kin[i] for i in range(len(h))]
        kd = [kind(g) for g in ow]
        info["paths"] += 1
        for i in range(len(h)):
            if ok[i] and kd[i] == "grass" and rowi[i] in eased:
                info["grass_on_top"] += 1
                ry, _rg = paved.top(px[i], pz[i])
                over = (h[i] - ry) if ry is not None else 9.99
                info["grass_over_max_m"] = max(info["grass_over_max_m"], over)
                if over > GRASS_OVER_M:
                    worst.append((over, "GRASS", px[i], pz[i], o, rowi[i], nm(ow[i]), ""))
        hit = False
        for i in range(k1, len(h) - k10):
            if not (ok[i - k1] and ok[i] and ok[i + k10]):
                continue
            st = (h[i + k10] - h[i]) - (h[i] - h[i - k1]) * FINE_WIN_M
            if abs(st) < FINE_STEP_M:
                continue
            if "rkerb" in (kd[i], kd[i + k10]):
                info["kerb_lip_max_m"] = max(info["kerb_lip_max_m"], abs(st))
                if abs(st) <= KERB_LIP_M:
                    continue
            info["fine_max_m"] = max(info["fine_max_m"], abs(st))
            worst.append((abs(st), "FINE", px[i], pz[i], o, rowi[i], nm(ow[i]), nm(ow[i + k10])))
            hit = True
        for i in range(k1, len(h) - k1):
            if not (ok[i - k1] and ok[i] and ok[i + k1]):
                continue
            if "rkerb" in kd[i - k1:i + k1 + 1]:
                continue                     # the metre touches an authored race kerb (its 0.05 m lip)
            v = abs((h[i + k1] - h[i]) - (h[i] - h[i - k1]))
            info["dt_max_m"] = max(info["dt_max_m"], v)
            if v > DT_MAX_M:
                worst.append((v, "DT", px[i], pz[i], o, rowi[i], nm(ow[i]), ""))
                hit = True
        info["paths_with_step"] += hit
        o += PATH_DO_M
    feats = {}
    for w in worst:
        key = (w[1], int(w[2] // 1.0), int(w[3] // 1.0))
        if key not in feats or w[0] > feats[key][0]:
            feats[key] = w
    code = {"FINE": "1", "DT": "2", "GRASS": "4"}
    shown = sorted(feats.values(), key=lambda q: (q[1] != "GRASS", -q[0]))
    for w in shown[:12]:
        what = f"grass {w[0]:.3f} m over the pavement in the lane" if w[1] == "GRASS" else f"{w[1]} {w[0]:.3f} m"
        fails.append(f"({code[w[1]]}) {what} at ({w[2]:.2f}, {w[3]:.2f}), offset {w[4]:+.2f}, row {w[5]} "
                     f"({w[6]}{' -> ' + w[7] if w[7] else ''})")
    if len(shown) > 12:
        fails.append(f"... and {len(shown) - 12} more step / grass features")
    # window geometry for (3) / (5): road triangles whose centroid's nearest row (of the window +- 12) is in the window
    near_rows = [r % n for r in range(k - B - WINDOW_PAD_ROWS - 12, l + 14 + B + WINDOW_PAD_ROWS) if closed or 0 <= r < n]
    wr = set(rows)

    def in_window(x, z):
        best = None
        for r in near_rows:
            d = (P[r][0] - x) ** 2 + (P[r][2] - z) ** 2
            if best is None or d < best[0]:
                best = (d, r)
        return best[1] in wr and math.sqrt(best[0]) <= W[best[1]] / 2.0 + 2.0
    road_tris = [t for t in tris if t[3] >= 0 and upper[t[3]].startswith("1ROAD")
                 and in_window((t[0][0] + t[1][0] + t[2][0]) / 3.0, (t[0][2] + t[1][2] + t[2][2]) / 3.0)]
    # (3) road vertices one place in plan, two heights
    grid = {}
    for t in road_tris:
        for p in t[:3]:
            grid.setdefault((int(math.floor(p[0] / JUMP_PLAN_M)), int(math.floor(p[2] / JUMP_PLAN_M))), set()).add(p)
    jumps = []
    for (cx, cz), ps in grid.items():
        cand = set()
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                cand |= grid.get((cx + dx, cz + dz), set())
        for p in ps:
            for q in cand:
                d = math.hypot(p[0] - q[0], p[2] - q[2])
                if d <= JUMP_PLAN_M and abs(p[1] - q[1]) >= FINE_STEP_M + TRI_SLOPE_MAX * d:
                    jumps.append((abs(p[1] - q[1]), d, p, q))
    info["road_jumps"] = len(jumps) // 2
    if jumps:
        j_ = max(jumps)
        fails.append(f"(3) two road vertices {j_[1]:.3f} m apart in plan stand {j_[0]:.3f} m apart in height at "
                     f"({j_[2][0]:.2f}, {j_[2][2]:.2f}): {j_[2][1]:.3f} / {j_[3][1]:.3f} ({len(jumps) // 2} pairs)")
    # (5) steep road triangles
    steep = []
    for a, b, c, g in road_tris:
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx_, ny_, nz_ = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        area = 0.5 * abs(ny_)
        if area < TRI_AREA_MIN:
            continue
        slope = math.hypot(nx_, nz_) / abs(ny_)
        if slope > TRI_SLOPE_MAX:
            steep.append((slope, area, (round(a[0], 2), round(a[1], 3), round(a[2], 2)), names[g]))
    info["steep_road_tris"] = len(steep)
    for s_, a_, p_, nmg in sorted(steep, reverse=True)[:5]:
        fails.append(f"(5) {nmg} triangle at {p_} slopes {s_:.0%} over {a_:.3f} m2 of plan")
    # (6) the pinch at its midpoint: every road vertex within 0.02 m of X in plan
    X = pin["X"]
    mid = 0.5 * (pin["y_k"] + pin["y_l"])
    ys = [p[1] for t in road_tris for p in t[:3] if math.hypot(p[0] - X[0], p[2] - X[2]) <= 0.02]
    if not ys:
        fails.append(f"(6) no road vertex at the pinch X ({X[0]:.3f}, {X[2]:.3f})")
    else:
        dev = max(abs(y - mid) for y in ys)
        info["apex"] = {"X": [round(X[0], 3), round(X[2], 3)], "built_y": [round(min(ys), 4), round(max(ys), 4)],
                        "legs": [round(pin["y_k"], 4), round(pin["y_l"], 4)], "midpoint": round(mid, 4),
                        "max_dev_m": round(dev, 4)}
        if dev > APEX_TOL_M:
            fails.append(f"(6) the pinch X ({X[0]:.2f}, {X[2]:.2f}) is built at {min(ys):.3f}..{max(ys):.3f}, not the "
                         f"midpoint {mid:.3f} of its legs {pin['y_k']:.3f} / {pin['y_l']:.3f} (off {dev:.3f} m)")
    # (7) the race walls near X inside no_route's band
    if race:
        cells = {}
        for a, b, c, g in tris:
            if g < 0 or not upper[g].startswith("1WALL"):
                continue
            if min(math.hypot(p[0] - X[0], p[2] - X[2]) for p in (a, b, c)) > WALL_RADIUS_M:
                continue
            for p in (a, b, c):
                key = (int(math.floor(p[0] / WALL_CELL_M)), int(math.floor(p[2] / WALL_CELL_M)))
                cells[key] = min(cells.get(key, 1e9), p[1])
        worst_w, bad_w = None, 0
        for (i, j) in cells:
            base = min(cells.get((i + a, j + b), 1e9) for a in (-1, 0, 1) for b in (-1, 0, 1))
            x, z = (i + 0.5) * WALL_CELL_M, (j + 0.5) * WALL_CELL_M
            pr = cl_line.project(x, z)
            if pr is None:
                continue
            delta = base + 0.05 - (pr[3] + 0.10)
            if worst_w is None or abs(delta) > abs(worst_w[0]):
                worst_w = (delta, x, z)
            if abs(delta) > WALL_BAND_M:
                bad_w += 1
        info["wall_cells"] = len(cells)
        info["wall_worst_delta_m"] = round(worst_w[0], 4) if worst_w else None
        if bad_w:
            fails.append(f"(7) {bad_w} race-wall cells within {WALL_RADIUS_M:.0f} m of X stand outside no_route's band "
                         f"(+-{WALL_BAND_M}); worst {worst_w[0]:+.3f} m at ({worst_w[1]:.1f}, {worst_w[2]:.1f})")
    for key in ("kerb_lip_max_m", "fine_max_m", "dt_max_m", "grass_over_max_m"):
        info[key] = round(info[key], 4)
    return fails, info


def _lap_lane(data: Path, lap: str, lid: str, n: int):
    """(lane_of(row, W), covered rows) for a race layout on a LAP (ledger 0054): mainline row r -> the lap vertex
    standing on it (data/lap.<lap>.json source_by_vertex) and that layout's lane there
    (data/barrier_bands.<lap>.json), turned into the MAINLINE's forward-left frame when the lap runs the row
    backwards; a row the lap does not cover gets the full road (it is never surveyed: covered decides)"""
    rec = _load(data / f"lap.{lap}.json")
    bp = data / f"barrier_bands.{lap}.json"
    lbv = ((((json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {}).get("corridors") or {}).get(lid) or {})
           .get("lane_by_vertex"))
    if not lbv:
        raise InputError(f"barrier_bands.{lap}.json has no corridors.{lid}.lane_by_vertex")
    src = rec["source_by_vertex"]
    m = len(src) - 1
    at = {}
    for k in range(m):
        sv, nx = src[k], src[(k + 1) % m]
        if sv[0] != "MAINLINE":
            continue
        r = int(sv[1]) % n
        fwd = nx[0] == "MAINLINE" and int(nx[1]) % n == (r + 1) % n
        bwd = nx[0] == "MAINLINE" and int(nx[1]) % n == (r - 1) % n
        at.setdefault(r, (k, 1.0 if fwd or not bwd else -1.0))

    def lane_of(r, W):
        hit = at.get(r % n)
        if hit is None:
            return (-(W[r] / 2.0 - 0.5), W[r] / 2.0 - 0.5)
        k, sgn = hit
        lo, hi = float(lbv[k][0]), float(lbv[k][1])
        return (lo, hi) if sgn > 0 else (-hi, -lo)
    return lane_of, set(at)


# ----------------------------------------------------------------------------------------------- main
def run(project: Path, layouts=None, out: Path | None = None) -> dict:
    data = project / "data"
    cfg = _load(project / "track.config.json")
    welds = _load(data / "mouth_welds.json")
    gc = _load(data / "gate_centerline.json")
    P = [tuple(p) for p in gc["points_xyz_m"]]
    W = [float(w) for w in gc["widths_m"]]
    closed = len(P) > 2 and abs(P[0][0] - P[-1][0]) < 1e-6 and abs(P[0][2] - P[-1][2]) < 1e-6
    n = len(P) - 1 if closed else len(P)
    rows_rec = ((welds.get("folds") or {}).get("MAINLINE") or {}).get("rows")
    if rows_rec is not None and int(rows_rec) != n:
        raise InputError(f"mouth_welds.json indexes {rows_rec} mainline rows; data/gate_centerline.json has {n}")
    N = normals(P, closed)
    pins, B = pinches_from(welds, P, W, closed)
    mb = data / "median_bands.json"
    iw = (json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex") or []) if mb.exists() else []
    island = lambda r: float(iw[r]) if r < len(iw) else 0.0
    bp = data / "barrier_bands.json"
    bands = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {}
    cl = _load(data / "centerline.local.json")
    cpts = [tuple(p) for p in cl["points_xyz_m"]]
    if len(cpts) > 2 and abs(cpts[0][0] - cpts[-1][0]) < 1e-6 and abs(cpts[0][2] - cpts[-1][2]) < 1e-6:
        cpts = cpts[:-1]
    cl_line = nr.Line(cpts)
    lays = []
    for lo in cfg.get("layouts") or [{"id": "street"}]:
        lid = str(lo.get("id"))
        if layouts and lid not in layouts:
            continue
        race = bool(lo.get("race_furniture"))
        p = gate_obj(data, lid, race)
        if not p.exists():
            raise InputError(f"layout {lid}: no gate OBJ {p.name} (the gates write it)")
        lays.append((lid, race, p, lo.get("lap") or None))
    rep = {"pinches": [{k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items()} for p in pins],
           "level_rows": B, "layouts": {}, "fails": []}
    if not pins:
        rep["note"] = "no levelled mainline pinch (no swallowtail fold): nothing to judge"
    else:
        boxes = []
        for pin in pins:
            rs = [r % n for r in range(pin["k"] - B - WINDOW_PAD_ROWS - 12, pin["l"] + 14 + B + WINDOW_PAD_ROWS)]
            xs = [P[r][0] for r in rs]
            zs = [P[r][2] for r in rs]
            pad = max(W[r] for r in rs) / 2.0 + WALL_RADIUS_M + 2.0
            boxes.append((min(xs) - pad, min(zs) - pad, max(xs) + pad, max(zs) + pad))
        for lid, race, path, lap in lays:
            if lap:
                # ledger 0054: a race layout on a LAP — the pinches are MAINLINE rows; the ones its lap does not run
                # over stand behind its walls (not its lane), the others take the lap's lane mapped back to the row
                lane_lap, covered = _lap_lane(data, lap, lid, n)
                todo = [pin for pin in pins if all((r % n) in covered for r in range(pin["k"] - B, pin["l"] + 2 + B))]
                rep["layouts"][lid] = [{"k": pin["k"] % n, "l": pin["l"] % n, "lane": pin["lane"], "fails": [],
                                        "skipped": f"not on lap {lap} (behind its walls)"} for pin in pins if pin not in todo]
            else:
                todo = pins
            tris, names = read_obj_region(path, boxes)
            upper = [g.upper() for g in names]
            phys = [t for t in tris if t[3] >= 0 and upper[t[3]].startswith(("1ROAD", "1KERB", "1GRASS"))]
            surf = Surface(phys)
            paved = Surface([t for t in phys if upper[t[3]].startswith(("1ROAD", "1KERB"))])
            if race and lap:
                lane_of = lambda r, ll=lane_lap: ll(r, W)
            elif race:
                lbv = (((bands.get("corridors") or {}).get(lid) or {}).get("lane_by_vertex"))
                if not lbv:
                    raise InputError(f"barrier_bands.json has no corridors.{lid}.lane_by_vertex")
                lane_of = lambda r, lbv=lbv: (float(lbv[r][0]), float(lbv[r][1]))
            else:
                lane_of = lambda r: (-(W[r] / 2.0 - 0.5), W[r] / 2.0 - 0.5)
            res = rep["layouts"].get(lid, []) if lap else []
            for pin in todo:
                f, info = survey_pinch(pin, B, P, W, N, closed, lane_of, surf, paved, tris, names, island, race, cl_line)
                res.append({"k": pin["k"] % n, "l": pin["l"] % n, "lane": pin["lane"], "fails": f, **info})
                rep["fails"] += [f"{lid} pinch {pin['k'] % n}..{(pin['l'] + 1) % n}: {x}" for x in f]
            rep["layouts"][lid] = res
    rep["fail"] = bool(rep["fails"])
    rep["thresholds"] = {"fine_step_m": FINE_STEP_M, "kerb_lip_m": KERB_LIP_M, "dt_max_m": DT_MAX_M, "grass_over_m": GRASS_OVER_M,
                         "jump_plan_m": JUMP_PLAN_M, "tri_slope_max": TRI_SLOPE_MAX, "tri_area_min": TRI_AREA_MIN,
                         "apex_tol_m": APEX_TOL_M, "wall_band_m": WALL_BAND_M, "wall_radius_m": WALL_RADIUS_M,
                         "window_pad_rows": WINDOW_PAD_ROWS, "path_do_m": PATH_DO_M, "path_ds_m": PATH_DS_M}
    (out or data / "verify_fold_fans.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    proj = Path(argv[0])
    lays, out = [], None
    i = 1
    while i < len(argv):
        if argv[i] == "--layout" and i + 1 < len(argv):
            lays.append(argv[i + 1]); i += 2
        elif argv[i] == "--json" and i + 1 < len(argv):
            out = Path(argv[i + 1]); i += 2
        else:
            print(f"[fold-fans] unknown argument {argv[i]}")
            return 2
    try:
        rep = run(proj, lays or None, out)
    except InputError as e:
        print(f"[fold-fans] INPUT ERROR: {e}")
        return 2
    for p in rep.get("pinches", []):
        print(f"[fold-fans] pinch rows {p['k']}..{p['l'] + 1} (ROAD lane {p['lane']}): legs {p['y_k']:.3f} / "
              f"{p['y_l']:.3f}, midpoint {0.5 * (p['y_k'] + p['y_l']):.3f} — {p['source']}")
    for lid, res in rep.get("layouts", {}).items():
        for r in res:
            if r.get("skipped"):        # a lap layout's pinch behind its walls carries no survey (ledger 0054)
                print(f"[fold-fans] {lid:9s} pinch {r['k']}..{(r['l'] + 1)}: skipped — {r['skipped']}")
                continue
            ap = r.get("apex") or {}
            print(f"[fold-fans] {lid:9s} rows {r['rows'][0]}..{r['rows'][1]}: {r['paths']} paths, {r['paths_with_step']} "
                  f"with a step; fine max {r['fine_max_m']:.3f}, DT max {r['dt_max_m']:.3f}, race-kerb lip max "
                  f"{r['kerb_lip_max_m']:.3f}, grass-on-top {r['grass_on_top']} (max {r['grass_over_max_m']:.3f} over), road jumps {r['road_jumps']}, steep road "
                  f"tris {r['steep_road_tris']}, X built {ap.get('built_y')} vs midpoint {ap.get('midpoint')}"
                  + (f", walls worst {r['wall_worst_delta_m']:+.3f} m over {r['wall_cells']} cells"
                     if r.get("wall_worst_delta_m") is not None else ""))
    for f in rep.get("fails", []):
        print(f"[fold-fans] FAIL {f}")
    print(f"[fold-fans] {'FAIL' if rep['fail'] else 'PASS'}: {len(rep.get('pinches', []))} levelled pinch(es) x "
          f"{len(rep.get('layouts', {}))} layout(s)" + (f" — {rep['note']}" if rep.get("note") else ""))
    return 1 if rep["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())

"""A switchback as its graded platform measures: the turn's centre arc, radius and width from the 1 m DEM (ledger 0078
round 9).

The Rangely stages' switchbacks are mapped as a kink (three or four 116-150 deg OSM vertices over ~30 m on a ~7 m
radius); a road swept along that folds its inside edge. The real switchback is a graded platform you can read in 3DEP's
1 m bare-earth DEM: tools/road_seek.py measures, at every station, how far the graded surface runs either side of the
road's centre before a face (cut, fill or ditch) ends it (bench_m, per side, BENCH_MAX_M = unmeasured). Round the turn,
those two edges trace the platform's outside and inside: each is fitted with a circle (least squares, Kasa), and the
road's centre arc is the circle between them: radius = the mean of the two, width = their difference, centre = theirs.

Per turn (every run of stations whose heading changes more than TURN_DEG within +-TURN_HALF_M), on the line
road_seek moved onto the road:
    {id, st_m (apex), turn_deg, radius_m (the centre arc), width_m, r_outside_m, r_inside_m, centre_xz,
     points_outside, points_inside, rms_outside_m, rms_inside_m, measured (both edges fitted)}
written to the port's data/switchbacks.json; tools/lm_engine_intake.py fits the measured ones as corner arcs
(lm_intake.corner_arcs: "data/switchbacks.json", scripts/geometry/corner_arcs.fit_corners). Nothing is declared by
hand: a turn whose edges the DEM does not bound is reported unmeasured and left as mapped.

    python tools/switchback_measure.py <port-track-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

TURN_DEG = 90.0          # [invented] a switchback: more than this of heading change ...
TURN_HALF_M = 15.0       # ... within this either side of a station
EDGE_HALF_M = 25.0       # [invented] the platform's edges are read this far either side of the apex
MIN_POINTS = 5           # a circle needs at least this many edge points
BENCH_MAX_M = 15.0       # tools/road_seek.py's: an edge at this is unmeasured


def _kasa(pts):
    """least-squares circle through [(x, z)]: (cx, cz, r, rms)"""
    n = len(pts)
    sx = sum(p[0] for p in pts) / n
    sz = sum(p[1] for p in pts) / n
    u = [p[0] - sx for p in pts]
    v = [p[1] - sz for p in pts]
    suu = sum(a * a for a in u); svv = sum(b * b for b in v); suv = sum(a * b for a, b in zip(u, v))
    suuu = sum(a ** 3 for a in u); svvv = sum(b ** 3 for b in v)
    suvv = sum(a * b * b for a, b in zip(u, v)); svuu = sum(b * a * a for a, b in zip(u, v))
    det = suu * svv - suv * suv
    if abs(det) < 1e-9:
        return None
    rhs1 = 0.5 * (suuu + suvv)
    rhs2 = 0.5 * (svvv + svuu)
    uc = (rhs1 * svv - rhs2 * suv) / det
    vc = (suu * rhs2 - suv * rhs1) / det
    cx, cz = uc + sx, vc + sz
    r = math.sqrt(uc * uc + vc * vc + (suu + svv) / n)
    rms = math.sqrt(sum((math.hypot(p[0] - cx, p[1] - cz) - r) ** 2 for p in pts) / n)
    return cx, cz, r, rms


class LidarGround:
    """a tools/lidar_turns.py grid: the mean class-2 height of each 0.5 m cell, local frame"""

    def __init__(self, f):
        import numpy as np
        d = np.load(f)
        self.g, self.x0, self.z0, self.c = d["ground"], float(d["x0"]), float(d["z0"]), float(d["cell_m"])
        self.st_m = float(d["st_m"])
        self.n = self.g.shape[0]

    def covers(self, x, z):
        return self.x0 <= x < self.x0 + self.n * self.c and self.z0 <= z < self.z0 + self.n * self.c

    def at(self, x, z):
        """the mean of the cells with ground nearest (x, z): the 3 x 3 block, else the 5 x 5 (~3.8 class-2 points a
        square metre leave a third of the 0.5 m cells empty; a bench read stops at an empty one)"""
        import numpy as np
        i, j = int((x - self.x0) / self.c), int((z - self.z0) / self.c)
        if not (0 <= i < self.n and 0 <= j < self.n):
            return None
        for r in (0, 1, 2):
            blk = self.g[max(0, j - r):j + r + 1, max(0, i - r):i + r + 1]
            ok = np.isfinite(blk)
            if ok.any():
                return float(blk[ok].mean())
        return None


def bench_on(G, q, nx, nz):
    """road_seek's bench, read on lidar ground: the road's plane fitted BENCH_CORE_M either side of the centre q, how far
    the ground stays within BENCH_TOL_M of it each way, an end measured only where it is a face (FACE_DROP_M off within
    FACE_RUN_M); [-left, right] with BENCH_MAX_M for an unmeasured side"""
    import road_seek as rs
    ts, hs = [], []
    t = -rs.BENCH_CORE_M
    while t <= rs.BENCH_CORE_M + 1e-9:
        v = G.at(q[0] + nx * t, q[1] + nz * t)
        if v is not None:
            ts.append(t); hs.append(v)
        t += 0.5
    if len(ts) < 3:
        return [-BENCH_MAX_M, BENCH_MAX_M]
    a, b, _r = rs._fit(ts, hs)
    ext = []
    for sgn in (-1.0, 1.0):
        e = 0.0
        while e < rs.BENCH_MAX_M:
            v = G.at(q[0] + nx * sgn * (e + 0.5), q[1] + nz * sgn * (e + 0.5))
            if v is None or abs(v - (a + b * sgn * (e + 0.5))) >= rs.BENCH_TOL_M:
                break
            e += 0.5
        tq = sgn * (e + rs.FACE_RUN_M)
        v = G.at(q[0] + nx * tq, q[1] + nz * tq)
        if e >= rs.BENCH_MAX_M or v is None or abs(v - (a + b * tq)) < rs.FACE_DROP_M:
            e = BENCH_MAX_M
        ext.append(e)
    return [-ext[0], ext[1]]


def measure(P, seek, lidar=()):
    import road_seek
    Q, _relaxed = road_seek.moved_line(P, seek)
    n = len(Q)
    st = [0.0]
    for a, b in zip(Q, Q[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))

    def idx_at(s):
        lo, hi = 0, n - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if st[mid] < s:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def heading(i, j):
        return math.atan2(Q[j][2] - Q[i][2], Q[j][0] - Q[i][0])

    turn = [0.0] * n
    for i in range(n):
        a, b = idx_at(st[i] - TURN_HALF_M), idx_at(st[i] + TURN_HALF_M)
        if a < 1 or b > n - 2:
            continue
        t = heading(b, b + 1) - heading(a - 1, a)
        turn[i] = (t + math.pi) % (2 * math.pi) - math.pi
    out = []
    i = 0
    while i < n:
        if abs(turn[i]) * 180 / math.pi <= TURN_DEG:
            i += 1
            continue
        j = i
        while j < n and abs(turn[j]) * 180 / math.pi > TURN_DEG:
            j += 1
        apex = max(range(i, j), key=lambda k: abs(turn[k]))
        sgn = 1.0 if turn[apex] > 0 else -1.0           # + = turning left (the inside is the left)
        ins, outs = [], []
        src_lidar = False
        for k in range(idx_at(st[apex] - EDGE_HALF_M), idx_at(st[apex] + EDGE_HALF_M) + 1):
            a, b = Q[max(k - 1, 0)], Q[min(k + 1, n - 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            G = next((g for g in lidar if g.covers(Q[k][0], Q[k][2])), None)
            if G is not None:                                   # the turn's lidar ground (tools/lidar_turns.py) first
                lo, hi = bench_on(G, (Q[k][0], Q[k][2]), nx, nz)
                src_lidar = True
            else:
                lo, hi = seek[k].get("bench_m") or [-BENCH_MAX_M, BENCH_MAX_M]
            for t_, side in ((lo, -1.0), (hi, 1.0)):
                if abs(t_) >= BENCH_MAX_M - 1e-6:
                    continue
                pt = (Q[k][0] + nx * t_, Q[k][2] + nz * t_)
                (ins if side == sgn else outs).append(pt)
        rec = {"id": f"S{len(out) + 1}", "st_m": round(st[apex], 1), "turn_deg": round(abs(turn[apex]) * 180 / math.pi, 1),
               "points_outside": len(outs), "points_inside": len(ins), "measured": False,
               "ground": "3DEP lidar class 2 (tools/lidar_turns.py)" if src_lidar else "3DEP 1 m DEM (road_seek bench)"}
        fo = _kasa(outs) if len(outs) >= MIN_POINTS else None
        fi = _kasa(ins) if len(ins) >= MIN_POINTS else None
        if fo:
            rec.update({"r_outside_m": round(fo[2], 2), "rms_outside_m": round(fo[3], 2)})
        if fi:
            rec.update({"r_inside_m": round(fi[2], 2), "rms_inside_m": round(fi[3], 2)})
        if fo and fi and math.hypot(fo[0] - fi[0], fo[1] - fi[1]) < 0.5 * fo[2] and fo[2] > fi[2]:
            rec.update({"measured": True, "radius_m": round((fo[2] + fi[2]) / 2.0, 2),
                        "width_m": round(fo[2] - fi[2], 2),
                        "centre_xz": [round((fo[0] + fi[0]) / 2.0, 2), round((fo[1] + fi[1]) / 2.0, 2)]})
        elif fo:
            rec["why"] = "the inside edge is not bounded by a face in the DEM (or the circles disagree)"
        else:
            rec["why"] = "the outside edge is not bounded by a face in the DEM"
        out.append(rec)
        i = j
    return out


def main(argv=None):
    port = Path((argv or sys.argv[1:])[0])
    cfg = json.loads((port / "track.config.json").read_text(encoding="utf-8"))
    src = AIROSO / "tracks" / cfg["lm_intake"]["source_track"]
    local = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    seek = json.loads((port / "data" / "road_seek.json").read_text(encoding="utf-8"))["stations"]
    P = [tuple(p) for p in local["points_xyz_m"]]
    lidar = [LidarGround(f) for f in sorted((port / "data" / "lidar").glob("*.npz"))] \
        if (port / "data" / "lidar").is_dir() else []
    corners = measure(P, seek, lidar)
    rec = {"_doc": "tools/switchback_measure.py (ledger 0078 round 9): each switchback's graded platform from the 1 m DEM "
                   "(road_seek's bench edges round the turn, a circle fitted to each; the road's centre arc between them)",
           "params": {"TURN_DEG": TURN_DEG, "TURN_HALF_M": TURN_HALF_M, "EDGE_HALF_M": EDGE_HALF_M, "MIN_POINTS": MIN_POINTS},
           "corners": corners}
    (port / "data" / "switchbacks.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    for c in corners:
        print(f"[switchbacks] {c['id']} s {c['st_m']:.0f} turn {c['turn_deg']:.0f} deg: " + (
            f"R {c['radius_m']} m, width {c['width_m']} m (outside R {c['r_outside_m']} rms {c['rms_outside_m']}, "
            f"inside R {c['r_inside_m']} rms {c['rms_inside_m']})" if c["measured"] else f"unmeasured: {c.get('why')} "
            f"(outside R {c.get('r_outside_m')}, inside R {c.get('r_inside_m')})"))


if __name__ == "__main__":
    main()

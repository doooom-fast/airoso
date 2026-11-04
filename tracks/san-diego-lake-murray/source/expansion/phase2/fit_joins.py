"""Refit the north lap's J2 / J3 / J4 join curves inside the BUILT junction pads (ledger 0054 Phase 2, 2026-11-04).

The PC's step 3 (judge_joins_built.py on v4's built road) failed J2 / J3 / J4 on severe steps: the planned race lane's inside
face stood on the pads' curb returns. The joins were cubic curves off the approach tangents with handles a third of the
chord (accounting lines), and they cut every inside corner. This refits each one so that the lap's own curb lines, the
race strips standing on them and so the whole race lane, lie on the pad's real pavement on BOTH sides:

  pavement   data/pads.built.json outline_xz (the pad deck as built: its curb runs are swept outward from this line,
             tools/junction_pad.py) united with the two pieces' own road ribbons beyond the join ends (the lap's vertices,
             +-w/2: what the ribbon is built from). The built outline is 0.1-1.75 m tighter at the inside
             corners than expansion.north.json's planned outline_xz (it carries the stubs' and corners' as-built
             radii); the PC measured the curb on the built road exactly where this outline stands (J2 v324 10.18 m).
  the lap    each join keeps its end points (the two piece ends, race_lap.JOIN_END_TOL_M) and its end tangents (the pieces'
             own: no kink), and its POINT COUNT (every declared vertex number of the lap after it is unchanged). Its
             widths stay race_lap's (the two piece widths lerped by arc fraction); its heights are the old reference's
             profile by arc fraction (never a road datum).
  the curve  a cubic (handle lengths h1, h2 x chord) plus a lateral bump t^2 (1-t)^2 (c0 + c1 t + c2 t^2) along its own
             normal (zero offset and slope at both ends): 5 parameters.
  the fit    every interior point and every midpoint between consecutive points (the strips and the lane are lerped
             between vertices): the strip's OUTER face (|lat| = w/2 - 0.15, tools/race_furniture: centre w/2 - 0.485,
             half base 0.335) stands >= STRIP_KEEP_M inside the pavement on both sides (>= 0 at the two points beside the
             ends, which the pieces' own ends place) (a hard constraint, as a steep
             penalty), and the centreline's smallest plan radius (+-6 m stencil, barrier_bands' corner measure) is as
             large as that allows. Differential evolution (seed 1) then Nelder-Mead polish.
  shape      the centreline radius stays >= max width / 2 + R_FLOOR_PAD_M (the inside curb line never folds) and the
             join no more than LEN_MAX longer than the old one (no swing-out loop): both as penalties.
  refusal    exit 1 when a join's best fit leaves any strip face more than FIT_TOL_M short of its keep (the lane
             cannot stay on the asphalt without leaving it on the outside), or breaks the radius floor or the length
             bound: nothing is written.

    .venv/bin/python tracks/san-diego-lake-murray/source/expansion/phase2/fit_joins.py [--write]

Prints per join: old / new strip-face margins (min over both sides), lane margins (the judge's samples: 0.5 m inside the lane
face, |lat| = w/2 - 1.32), the radius, the length. --write rewrites source/expansion/race.north.joins.json (with the fit
record). Needs numpy, scipy, shapely (the repo's .venv). Deterministic on one platform; the joins file is the record.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution, minimize
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from scripts.geometry import race_lap  # noqa: E402

JOINS = PROJECT / "source" / "expansion" / "race.north.joins.json"
STRIP_OUTER_M = 0.15        # the strip's outer face stands this far inside the lap's curb line (0.485 - 0.335)
LANE_KEEP_M = 1.32          # the judge's outermost sample: 0.82 lane inset + EDGE_KEEP_M 0.5
STRIP_KEEP_M = 0.0          # the strip's outer face stands ON the built pavement (the judge's lane samples are then >= 1.17 m in)
FIT_TOL_M = 0.02
R_FLOOR_PAD_M = 0.5         # [invented] the centreline radius never below w/2 + this: the inside curb line never folds
LEN_MAX = 1.25              # [invented] the refit never runs more than 25 % longer than the old join (no swing-out loop)
RIBBON_VERTS = 14           # the pieces' own road this many vertices (~40 m) beyond each join end
STENCIL_M = 6.0
FIT_JOINS = ("J2", "J3", "J4")


def pavement(pid: str, ribbons=()):
    """the pad deck as built (pads.built.json outline_xz) united with the route pieces' own road ribbons beyond it"""
    built = json.loads((PROJECT / "data" / "pads.built.json").read_text(encoding="utf-8"))
    pb = next(p for p in built["pads"] if p["id"] == pid)
    return unary_union([Polygon(pb["outline_xz"]).buffer(0)] + list(ribbons))


def ribbon(P, Wd, ks, end_tangent):
    """the road ribbon (curb line to curb line, +-w/2) over the lap's piece vertices ks, as quads; the vertex at the
    join end takes the piece's own end tangent (its join neighbour is what is being refitted)"""
    quads = []
    rows = []
    for k in ks:
        if k == end_tangent[0]:
            tx, tz = end_tangent[1]
        else:
            tx, tz = P[k + 1][0] - P[k - 1][0], P[k + 1][2] - P[k - 1][2]
            L = math.hypot(tx, tz)
            tx, tz = tx / L, tz / L
        h = Wd[k] / 2.0
        rows.append(((P[k][0] - tz * h, P[k][2] + tx * h), (P[k][0] + tz * h, P[k][2] - tx * h)))
    for (a, b), (c, d) in zip(rows, rows[1:]):
        quads.append(Polygon([a, b, d, c]).buffer(0))
    return quads


def _bez(P0, P1, P2, P3, t):
    t = t[:, None]
    return ((1 - t) ** 3) * P0 + 3 * ((1 - t) ** 2) * t * P1 + 3 * (1 - t) * t * t * P2 + t ** 3 * P3


def curve(A, B, tA, tB, x, chord, n=400):
    t = np.linspace(0, 1, n)
    C = _bez(A, A + x[0] * chord * tA, B - x[1] * chord * tB, B, t)
    d = np.gradient(C, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    bump = (t ** 2) * ((1 - t) ** 2) * (x[2] + x[3] * t + x[4] * t * t)
    return C + bump[:, None] * nrm


def resample(C, npts):
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
    u = np.linspace(0, s[-1], npts)
    return np.stack([np.interp(u, s, C[:, 0]), np.interp(u, s, C[:, 1])], axis=1), float(s[-1])


def radius_min(Q):
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))])
    best = 1e9
    for i in range(1, len(Q) - 1):
        a = max(0, min(int(np.searchsorted(s, s[i] - STENCIL_M)), i - 1))
        b = min(len(Q) - 1, max(int(np.searchsorted(s, s[i] + STENCIL_M)), i + 1))
        p, q, r = Q[a], Q[i], Q[b]
        cr = abs((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))
        if cr > 1e-9:
            best = min(best, np.linalg.norm(q - p) * np.linalg.norm(r - q) * np.linalg.norm(p - r) / (2 * cr))
    return float(best)


def margins(Q, w, pav, before, after):
    """[strip L, strip R, lane L, lane R] per interior point: the signed distance inside the pavement (+ inside) of the
    offsets at the point and at the midpoint to the next one (the worse of the two)"""
    full = np.concatenate([before, Q, after])
    d = np.gradient(full, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    k0 = len(before)

    def off(i, s, sg):
        return full[k0 + i] + sg * (w[i] / 2 - s) * nrm[k0 + i]
    out = []
    for i in range(1, len(Q) - 1):
        row = []
        for s in (STRIP_OUTER_M, LANE_KEEP_M):
            for sg in (1, -1):
                v = 1e9
                cands = [off(i, s, sg)]
                cands += [0.5 * (off(i, s, sg) + off(j, s, sg)) for j in (i - 1, i + 1) if 0 < j < len(Q) - 1]
                for p in cands:
                    pt = Point(p[0], p[1])
                    dd = pav.boundary.distance(pt)
                    v = min(v, dd if pav.contains(pt) else -dd)
                row.append(v)
        out.append(row)
    return np.array(out)


def lap_context():
    decl = json.loads((HERE / "race.north.declaration.json").read_text(encoding="utf-8"))
    cfg = {"race": {"laps": {"north": decl["laps"]["north"]}}, "layouts": []}
    return race_lap.stitch(PROJECT, cfg, "north")


def fit_one(lap, jdef):
    P, Wd, SRC = lap["points_xyz_m"], lap["widths_m"], lap["source_by_vertex"]
    jid, old = jdef["id"], jdef["points_xyz_m"]
    ji = next(i for i, j in enumerate(lap["joins"]) if j.get("declared") == jid)
    ks = [k for k, s in enumerate(SRC) if s[0] == "join" and s[1] == ji]
    kA, kB = ks[0] - 1, ks[-1] + 1
    xz = lambda k: np.array([P[k][0], P[k][2]])  # noqa: E731
    A, B = xz(kA), xz(kB)
    tA = A - xz(kA - 1)
    tA /= np.linalg.norm(tA)
    tB = xz(kB + 1) - B
    tB /= np.linalg.norm(tB)
    before = np.array([xz(k) for k in range(kA - 3, kA)])
    after = np.array([xz(k) for k in range(kB + 1, kB + 4)])
    wa, wb = Wd[kA], Wd[kB]
    npts = len(old)
    chord = float(np.linalg.norm(B - A))
    rib = ribbon(P, Wd, range(kA - RIBBON_VERTS, kA + 1), (kA, tuple(tA))) + \
        ribbon(P, Wd, range(kB, kB + RIBBON_VERTS + 1), (kB, tuple(tB)))
    pav = pavement(jid, rib)
    w = wa + (wb - wa) * np.linspace(0, 1, npts)

    def build(x):
        return resample(curve(A, B, tA, tB, x, chord), npts)

    # the interior points beside the two ends stand where the pieces' own ends put them: their strips need only be ON the
    # pavement (0.0); every other point keeps STRIP_KEEP_M
    keep = np.full(npts - 2, STRIP_KEEP_M)
    keep[0] = keep[-1] = 0.0

    r_floor = float(max(w)) / 2.0 + R_FLOOR_PAD_M
    old_len = float(np.sum(np.linalg.norm(np.diff(np.array([[p[0], p[2]] for p in old]), axis=0), axis=1)))

    def score(x):
        Q, L = build(x)
        M = margins(Q, w, pav, before, after)
        viol = np.clip(keep[:, None] - M[:, :2], 0, None)      # every strip face where it must be (hard)
        R = radius_min(np.concatenate([before, Q, after]))
        pen = 1e6 * float((viol ** 2).sum())
        pen += 1e3 * max(0.0, r_floor - R) ** 2 + 1e2 * max(0.0, L - LEN_MAX * old_len) ** 2
        # then the gentlest radius
        return -min(R, 60.0) / 10.0 + pen + 1e-7 * float(np.dot(x[2:], x[2:]))

    def judge(Q):
        M = margins(Q, w, pav, before, after)
        i, j = divmod(int(np.argmin(M[:, :2])), 2)
        return {"strip_min_m": round(float(M[:, :2].min()), 3), "strip_min_at": [i + 1, "LR"[j]],
                "strip_short_m": round(float(np.clip(keep[:, None] - M[:, :2], 0, None).max()), 3),
                "lane_min_m": round(float(M[:, 2:].min()), 3),
                "radius_min_m": round(radius_min(np.concatenate([before, Q, after])), 1),
                "length_m": round(float(np.sum(np.linalg.norm(np.diff(Q, axis=0), axis=1))), 2)}
    oldQ = np.array([[p[0], p[2]] for p in old])
    de = differential_evolution(score, [(0.1, 1.2), (0.1, 1.2), (-200, 200), (-300, 300), (-200, 200)], seed=1,
                                maxiter=300, popsize=30, tol=1e-7, polish=False)
    best = minimize(score, de.x, method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-5, "fatol": 1e-7})
    x = best.x if best.fun <= de.fun else de.x
    Q, L = build(x)
    # heights: the old reference's profile by arc fraction
    so = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(oldQ, axis=0), axis=1))])
    sn = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))])
    ys = np.interp(sn / sn[-1], so / so[-1], [p[1] for p in old])
    pts = [[round(float(old[0][0]), 4), round(float(old[0][1]), 4), round(float(old[0][2]), 4)]]
    pts += [[round(float(q[0]), 4), round(float(y), 4), round(float(q[1]), 4)] for q, y in zip(Q[1:-1], ys[1:-1])]
    pts += [[round(float(old[-1][0]), 4), round(float(old[-1][1]), 4), round(float(old[-1][2]), 4)]]
    return {"id": jid, "from": jdef["from"], "to": jdef["to"], "points_xyz_m": pts,
            "fit": {"params": [round(float(v), 4) for v in x], "radius_floor_m": round(r_floor, 2),
                    "length_max_m": round(LEN_MAX * old_len, 2), "old": judge(oldQ), "new": judge(Q)}}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    doc = json.loads(JOINS.read_text(encoding="utf-8"))
    lap = lap_context()
    out, bad = [], []
    for jdef in doc["joins"]:
        if jdef["id"] not in FIT_JOINS or ("--only" in argv and jdef["id"] != argv[argv.index("--only") + 1]):
            out.append(jdef)
            continue
        r = fit_one(lap, jdef)
        o, n = r["fit"]["old"], r["fit"]["new"]
        print(f"{r['id']}: strip face {o['strip_min_m']:+.2f} -> {n['strip_min_m']:+.2f} m, lane (judge's samples) "
              f"{o['lane_min_m']:+.2f} -> {n['lane_min_m']:+.2f} m, radius {o['radius_min_m']} -> {n['radius_min_m']} m, "
              f"length {o['length_m']} -> {n['length_m']} m (short of its keep by {n['strip_short_m']} m; strip min at point {n['strip_min_at']} of {len(r['points_xyz_m'])})")
        if n["strip_short_m"] > FIT_TOL_M or n["radius_min_m"] < r["fit"]["radius_floor_m"] - 0.1 \
                or n["length_m"] > r["fit"]["length_max_m"] + 0.1:
            bad.append(r["id"])
        out.append(r)
    if bad:
        print(f"REFUSED: {bad} — no curve keeps both strips on the built pavement; nothing written")
        return 1
    if "--write" in argv:
        doc["joins"] = out
        doc["_doc"] = ("Held Phase 2 race-reference joins J2-J4 (ledger 0054), not road geometry and never an AI spline. "
                       "REFIT 2026-11-04 by source/expansion/phase2/fit_joins.py: each curve keeps its end points, end "
                       "tangents and point count, and is fitted so that the lap's race strips (and so its whole race lane) "
                       "stand on the BUILT pads' pavement on both sides (data/pads.built.json outline_xz + the route arms), "
                       "with the largest smallest radius that allows; `fit` records the old and new margins. Heights are the "
                       "old reference's profile by arc fraction, NOT a road datum. The built road is judged by "
                       "judge_joins_built.py on the PC (ledger 0054 Phase 2 step 3). J1 / J5 are not declared here: straight "
                       "joins inside the mainline's own junction boxes.")
        JOINS.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print("wrote", JOINS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

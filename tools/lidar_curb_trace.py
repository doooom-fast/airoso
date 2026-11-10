"""A CONTINUOUS LIDAR CURB-LINE TRACE along a divided road (ledger 0079 round Q, Sand Creek; opt-in, no build step).

Kevin, 2026-11-03: "I just want real"; "Real junctions". Round J's per-station tracer (tools/naip_edge.py) found
Quebec's raised median but not its outer edges: one cross-section at a time, a NAIP brightness run plus a curb step
picks driveways, aprons, the slip lane and the other carriageway as readily as the curb. Round J's lead: trace the
lidar's own curb line ALONG the road (a continuous step line, not per station), with NAIP only as the check.

What this does, for a road OSM draws as two one-way pieces A and B (Quebec: grid_primary_6 / 7):
  * THE STRAIGHTENED RASTER. The midline between A and B (merge_forks' stations: equal fractions of each piece from
    their shared end), every ROW_M along; across it, lateral -HALF_M .. +HALF_M every BIN_M (+ = toward B). Each cell is
    the median class-2 lidar ground within +-ALONG_M along and +-1 bin across (3 returns or more), and the NAIP 2023 gray
    in the track frame (tools/naip_edge.Naip).
  * THE STEP MAP. D(s, l) = the mean ground over (l, l + STEP_WIN_M] minus over [l - STEP_WIN_M, l), each row the mean
    of SMOOTH_ROWS rows. A curb face is a ridge of |D| (0.10-0.20 m) that runs along the road.
  * FOUR LINES, each by dynamic programming over every row (Viterbi: the path through the row's candidate bins with the
    largest summed step, less MOVE_COST per bin moved, at most MAX_MOVE bins a row): outer_left (A's outer edge),
    median_left (the median's A-side face: rises toward +l), median_right (its B-side face: falls toward +l),
    outer_right (B's outer edge). Each searches a window about A's / B's OSM ribbon (WINDOWS, metres off the ribbon
    edge). An outer line takes a step of either sign (`kind` curb: the ground rises outward, capped at OUTER_CAP_M;
    drop: an embankment's edge or the back of a walk, capped lower at DROP_CAP_M so a curb comes first), the innermost
    preferred (INWARD_COST).
  * PER ROW: `curb` = the step at the line is STEP_M or more (tools/naip_edge.STEP_M, round J); `naip` = NAIP agrees:
    the road side (NAIP_IN_M) reads the row's own road (its band: the median gray over both OSM ribbons, +- half the
    width of naip_edge.ROAD_BAND, so concrete pavement counts as well as asphalt) and the gray leaves that band for
    NAIP_LEAVE_M within NAIP_EDGE_M of the line (concrete, planting, verge; paint is narrower), or NAIP reads a
    concrete line at the line (brighter than the road side by NAIP_BRIGHT within NAIP_NEAR_M: a curb top / gutter).
  * SEGMENTS: runs of `curb` rows joined across gaps up to GAP_M (a driveway cut, a car on the gutter), less every
    stretch where NAIP disagrees for more than NAIP_GAP_M, kept when MIN_SEG_M or longer. Only a kept segment's rows
    are `ok`; every other row is reported, not used.

  * APPLY (`apply_plan`): what a re-centre would take, per piece: a carriageway's two edges where both are `ok`, bridged
    straight across gaps up to BRIDGE_M, stretches of MIN_APPLY_M or longer, eased back to OSM over TAPER_M, with the
    height shift the lidar reads between the new centre and OSM's line. Nothing in the build reads it yet (round Q:
    Quebec's median is 1.75-2 m wide over most of its length, under the two ribbons' edge strips; see ledger 0079).
  * ONE CARRIAGEWAY (--a = --b): the midline is the piece itself, its two outer edges only (48th's legs at Quebec).

Output (JSON): the midline and its normals, OSM's ribbon offsets, each line's lateral / step / `curb` / `naip` / `ok` per
row, the kept segments, each line's edge points in the track frame (x, z) per row, and `apply`. Numbers marked
[invented] are in fleet/GATES-CHANGELOG.md (round Q). Lidar tiles missing from the cache are listed, never fetched.

    python3 tools/lidar_curb_trace.py --connectors <connectors json> --a grid_primary_6 --b grid_primary_7 \
        --tiles <dir of tile_i_j.npz> --naip <naip jpg> --origin <centerline.local.json> --out <json>
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO / "tools"))

ROW_M = 0.5          # [invented] raster rows along the midline
BIN_M = 0.25         # [invented] raster bins across
HALF_M = 30.0        # [invented] lateral reach either side of the midline
ALONG_M = 0.75       # [invented] a cell's returns within this along (the lidar is ~4 class-2 returns / m2 here)
STEP_WIN_M = 1.0     # = tools/naip_edge.STEP_WIN_M (round J [invented]): a curb face 0.10-0.20 m, its gutter pan 0.6 m
SMOOTH_ROWS = 5      # [invented] the step map is the mean of 5 rows (+-1 m along)
MOVE_COST = 0.01     # [invented] metres of step a line gives up per bin it moves across between rows
MAX_MOVE = 2         # [invented] bins a line may move between rows (0.5 m per 0.5 m along)
GAP_M = 8.0          # [invented] a gap in the curb this long or shorter is a driveway cut: the segment runs on
MIN_SEG_M = 20.0     # [invented] a segment shorter than this is not a trace
BRIDGE_M = 30.0      # [invented] measured stretches this close are joined (edges straight between the checked ends)
MIN_APPLY_M = 40.0   # [invented] a carriageway is re-centred only over a stretch this long or longer
TAPER_M = 20.0       # [invented] past a stretch's end the edges ease back to OSM's ribbon over this
DY_ALONG_M = 2.5     # [invented] the height shift (lidar at the new centre - at OSM's) is the median over +-this along
NAIP_GAP_M = 15.0    # [invented] NAIP may disagree this long inside a segment (a tree's shadow, a parked car)
BAND_ALONG_M = 10.0  # [invented] the road band's centre is the median over this either side along
NAIP_IN_M = (1.0, 2.5)   # [invented] the road side's point is this window's middle inward of the line (past the gutter pan)
NAIP_EDGE_M = (-1.0, 2.5)  # [invented] NAIP must leave the road band this far from the line (- inside, + outside)
NAIP_LEAVE_M = 1.0   # [invented] ... for this long across (= naip_edge.RUN_M: paint is narrower)
NAIP_NEAR_M = 0.75   # [invented] or NAIP is brighter within this of the line ...
NAIP_BRIGHT = 12.0   # [invented] ... by this many gray levels over the road side (concrete curb / gutter vs asphalt)
OUTER_CAP_M = 0.08   # [invented] an outer line's step counts up to this (= STEP_M: every curb alike; a berm no more)
DROP_CAP_M = 0.06    # [invented] a fall outward (an embankment's edge, the back of a walk) counts up to this: a curb first
INWARD_COST = 0.0005 # [invented] metres of step an outer line gives up per bin outward of its window's road end
# windows: (ribbon, its edge sign, near, far) -> laterals from the OSM ribbon edge, metres, + = away from the ribbon centre
WINDOWS = {                # [invented] how far off OSM's ribbon edge each line is searched
    "outer_left": ("A", -1, -3.0, 9.0, -1),
    "median_left": ("A", +1, -5.0, 9.0, +1),
    "median_right": ("B", -1, -5.0, 9.0, -1),
    "outer_right": ("B", +1, -2.5, 11.0, +1),
}


def _plen(p):
    return sum(math.hypot(p[i][0] - p[i - 1][0], p[i][2] - p[i - 1][2]) for i in range(1, len(p)))


def _at(p, s):
    acc = 0.0
    for i in range(1, len(p)):
        L = math.hypot(p[i][0] - p[i - 1][0], p[i][2] - p[i - 1][2])
        if L > 0 and acc + L >= s:
            t = (s - acc) / L
            return tuple(p[i - 1][k] + (p[i][k] - p[i - 1][k]) * t for k in range(3))
        acc += L
    return tuple(p[-1])


def midline(pa, pb):
    """merge_forks' midline: pb turned to start at the end nearest pa's start; stations every ROW_M of the mean length.
    Returns (S, mid xyz, unit tangents (x, z), normals (-tz, tx)) as numpy arrays."""
    import numpy as np
    d0 = math.hypot(pa[0][0] - pb[0][0], pa[0][2] - pb[0][2])
    d1 = math.hypot(pa[0][0] - pb[-1][0], pa[0][2] - pb[-1][2])
    pb = pb if d0 <= d1 else pb[::-1]
    La, Lb = _plen(pa), _plen(pb)
    Lm = (La + Lb) / 2.0
    S = np.arange(0.0, Lm, ROW_M)
    mid = np.array([[(_at(pa, s / Lm * La)[k] + _at(pb, s / Lm * Lb)[k]) / 2.0 for k in range(3)] for s in S])
    tang = np.zeros((len(S), 2))
    w = int(round(5.0 / ROW_M))
    for i in range(len(S)):
        v = mid[min(len(S) - 1, i + w), [0, 2]] - mid[max(0, i - w), [0, 2]]
        tang[i] = v / np.linalg.norm(v)
    nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
    if np.dot(np.array([pb[len(pb) // 2][0], pb[len(pb) // 2][2]]) - mid[len(S) // 2, [0, 2]], nrm[len(S) // 2]) < 0:
        nrm = -nrm                                      # + = toward B
    return S, mid, tang, nrm, pb


def offsets(poly, mid, nrm):
    """the lateral of a polyline's nearest point to each midline station"""
    import numpy as np
    P = np.array([[q[0], q[2]] for q in poly])
    dense = []
    for i in range(1, len(P)):
        n = max(1, int(np.linalg.norm(P[i] - P[i - 1]) / 0.25))
        dense.extend(P[i - 1] + (P[i] - P[i - 1]) * t for t in np.arange(n) / n)
    dense.append(P[-1])
    Dn = np.array(dense)
    out = []
    for i in range(len(mid)):
        k = int(np.argmin(((Dn - mid[i, [0, 2]]) ** 2).sum(1)))
        out.append(float(np.dot(Dn[k] - mid[i, [0, 2]], nrm[i])))
    return np.array(out)


def load_ground(tiles_dir, x0, x1, z0, z1):
    """class-2 returns (E, N, Z) from tools/lidar_connector_profile.py's tile cache (tile_i_j.npz, 100 m); the missing
    tiles are listed, never fetched"""
    import numpy as np
    E, N, Z, missing = [], [], [], []
    for i in range(int(math.floor(x0 / 100)), int(math.floor(x1 / 100)) + 1):
        for j in range(int(math.floor(z0 / 100)), int(math.floor(z1 / 100)) + 1):
            f = os.path.join(tiles_dir, f"tile_{i}_{j}.npz")
            if not os.path.exists(f):
                missing.append([i, j])
                continue
            d = np.load(f)
            m = d["C"] == 2
            E.append(d["E"][m]); N.append(d["N"][m]); Z.append(d["Z"][m])
    if not E:
        raise SystemExit("lidar_curb_trace: no lidar tile covers the road")
    return np.concatenate(E), np.concatenate(N), np.concatenate(Z), missing


def raster(S, mid, tang, nrm, E, N, Z):
    import numpy as np
    from scipy.spatial import cKDTree
    L = np.arange(-HALF_M, HALF_M + 1e-9, BIN_M)
    H = np.full((len(S), len(L)), np.nan)
    tree = cKDTree(np.stack([E, N], 1))
    for i in range(len(S)):
        c = mid[i, [0, 2]]
        idx = tree.query_ball_point(c, HALF_M + 2.0)
        if not idx:
            continue
        P = np.stack([E[idx], N[idx]], 1) - c
        lat, al = P @ nrm[i], P @ tang[i]
        m = np.abs(al) <= ALONG_M
        k = np.round((lat[m] + HALF_M) / BIN_M).astype(int)
        hz = Z[idx][m]
        ok = (k >= 0) & (k < len(L))
        k, hz = k[ok], hz[ok]
        o = np.argsort(k)
        k, hz = k[o], hz[o]
        bd = np.searchsorted(k, np.arange(len(L) + 1))
        for b in range(len(L)):
            lo, hi = bd[max(0, b - 1)], bd[min(len(L), b + 2)]
            if hi - lo >= 3:
                H[i, b] = np.median(hz[lo:hi])
    return L, H


def step_map(H):
    import numpy as np
    from scipy.ndimage import uniform_filter1d
    w = int(round(STEP_WIN_M / BIN_M))
    Hf = np.where(np.isfinite(H), H, 0.0)
    Wt = np.isfinite(H).astype(float)
    Hs = uniform_filter1d(Hf, SMOOTH_ROWS, axis=0, mode="nearest")
    Ws = uniform_filter1d(Wt, SMOOTH_ROWS, axis=0, mode="nearest")
    ch = np.concatenate([np.zeros((H.shape[0], 1)), np.cumsum(Hs, 1)], 1)
    cw = np.concatenate([np.zeros((H.shape[0], 1)), np.cumsum(Ws, 1)], 1)
    D = np.full(H.shape, np.nan)
    for b in range(w, H.shape[1] - w):
        hr, wr = ch[:, b + 1 + w] - ch[:, b + 1], cw[:, b + 1 + w] - cw[:, b + 1]
        hl, wl = ch[:, b] - ch[:, b - w], cw[:, b] - cw[:, b - w]
        ok = (wr > w * 0.5) & (wl > w * 0.5)
        D[ok, b] = hr[ok] / wr[ok] - hl[ok] / wl[ok]
    return D


def viterbi(score, lo, hi):
    """score (rows x bins, >= 0); lo / hi the window's first / last bin per row. The best path's bin per row."""
    import numpy as np
    n, nb = score.shape
    NEG = -1e9
    acc = np.full(nb, NEG)
    acc[lo[0]:hi[0] + 1] = score[0, lo[0]:hi[0] + 1]
    back = np.zeros((n, nb), dtype=np.int32)
    moves = np.arange(-MAX_MOVE, MAX_MOVE + 1)
    for i in range(1, n):
        best = np.full(nb, NEG)
        arg = np.zeros(nb, dtype=np.int32)
        for mv in moves:
            src = np.roll(acc, mv) - MOVE_COST * abs(mv)
            if mv > 0:
                src[:mv] = NEG
            elif mv < 0:
                src[mv:] = NEG
            better = src > best
            best[better] = src[better]
            arg[better] = (np.arange(nb) - mv)[better]
        win = np.full(nb, NEG)
        win[lo[i]:hi[i] + 1] = 0.0
        acc = best + score[i] + win
        back[i] = arg
    path = np.zeros(n, dtype=np.int32)
    path[-1] = int(np.argmax(acc))
    for i in range(n - 1, 0, -1):
        path[i - 1] = back[i, path[i]]
    return path


def road_band(G, L, offA, offB, hwA, hwB):
    """per row, the road's own NAIP band: the median gray over both OSM ribbons, then the median of that over
    +-BAND_ALONG_M along (a car, a shadow), +- half naip_edge.ROAD_BAND's width"""
    import numpy as np
    from naip_edge import ROAD_BAND
    half = 0.5 * (ROAD_BAND[1] - ROAD_BAND[0])
    c = np.array([np.median(G[i][(np.abs(L - offA[i]) <= hwA) | (np.abs(L - offB[i]) <= hwB)]) for i in range(len(G))])
    w = int(round(BAND_ALONG_M / ROW_M))
    cs = np.array([np.median(c[max(0, i - w):i + w + 1]) for i in range(len(c))])
    return np.stack([cs - half, cs + half], 1)


def naip_agrees(G, L, li, side, band):
    """the road side (NAIP_IN_M's middle, inward of the line) reads the road (the row's band) and the gray leaves the
    band for NAIP_LEAVE_M or more somewhere from NAIP_EDGE_M[0] inside the line to NAIP_EDGE_M[1] outside it; or the
    line is a concrete line in NAIP (NAIP_BRIGHT over the road side within NAIP_NEAR_M)"""
    import numpy as np
    lo, hi = float(band[0]), float(band[1])
    road = [g for l, g in zip(L, G) if NAIP_IN_M[0] <= (li - l) * side <= NAIP_IN_M[1]]
    if not road or not (lo <= float(np.median(road)) <= hi):
        return False
    step = float(L[1] - L[0])
    need = int(round(NAIP_LEAVE_M / step))
    run = 0
    for l, g in sorted(zip(L, G), key=lambda t: (t[0] - li) * side):
        off = (l - li) * side
        if off < NAIP_EDGE_M[0]:
            continue
        if off > NAIP_EDGE_M[1] + NAIP_LEAVE_M:
            break
        run = run + 1 if not (lo <= g <= hi) else 0
        if run >= need and off - (need - 1) * step <= NAIP_EDGE_M[1]:
            return True
    # a narrow raised median's two curbs are two bright lines, its top as gray as the road
    near = [g for l, g in zip(L, G) if abs(l - li) <= NAIP_NEAR_M]
    return bool(near and max(near) - float(np.median(road)) >= NAIP_BRIGHT)


def _runs(flags, gap):
    """maximal runs of True rows, joined across False gaps of `gap` rows or fewer: [(i0, i1)]"""
    n, runs, i = len(flags), [], 0
    while i < n:
        if not flags[i]:
            i += 1
            continue
        j, last = i, i
        while j < n and (flags[j] or j - last <= gap):
            if flags[j]:
                last = j
            j += 1
        runs.append((i, last))
        i = last + 1
    return runs


def segments(curb, naip):
    """the lidar's curb runs (gaps <= GAP_M joined) with every stretch where NAIP disagrees for more than NAIP_GAP_M cut
    out, kept when MIN_SEG_M or longer: [(i0, i1, curb share, naip share)], and the ok mask"""
    n = len(curb)
    lidar = [False] * n
    for i0, i1 in _runs(curb, int(round(GAP_M / ROW_M))):
        for q in range(i0, i1 + 1):
            lidar[q] = True
    nai_ok = [False] * n
    for i0, i1 in _runs(naip, int(round(NAIP_GAP_M / ROW_M))):
        for q in range(i0, i1 + 1):
            nai_ok[q] = True
    both = [a and b for a, b in zip(lidar, nai_ok)]
    keep, ok = [], [False] * n
    for i0, i1 in _runs(both, 0):
        if (i1 - i0) * ROW_M < MIN_SEG_M:
            continue
        cs = sum(curb[i0:i1 + 1]) / (i1 - i0 + 1)
        ns = sum(naip[i0:i1 + 1]) / (i1 - i0 + 1)
        keep.append((i0, i1, round(cs, 3), round(ns, 3)))
        for q in range(i0, i1 + 1):
            ok[q] = True
    return keep, ok


def run(conns, a, b, tiles_dir, naip):
    import numpy as np
    by = {c["name"]: c for c in conns}
    A, B = by[a], by[b]
    pa = [tuple(q) for q in A["points_xyz_m"]]
    pb = [tuple(q) for q in B["points_xyz_m"]]
    S, mid, tang, nrm, pb = midline(pa, pb)
    offA, offB = offsets(pa, mid, nrm), offsets(pb, mid, nrm)
    if a == b:
        offA = offB = np.zeros(len(S))
    hwA, hwB = 0.5 * float(np.median(A["widths_m"])), 0.5 * float(np.median(B["widths_m"]))
    E, N, Z, missing = load_ground(tiles_dir, mid[:, 0].min() - HALF_M - 5, mid[:, 0].max() + HALF_M + 5,
                                   mid[:, 2].min() - HALF_M - 5, mid[:, 2].max() + HALF_M + 5)
    L, H = raster(S, mid, tang, nrm, E, N, Z)
    D = step_map(H)
    XX = mid[:, 0][:, None] + nrm[:, 0][:, None] * L[None, :]
    ZZ = mid[:, 2][:, None] + nrm[:, 1][:, None] * L[None, :]
    G = np.mean([naip.gray(XX + tang[:, 0][:, None] * q, ZZ + tang[:, 1][:, None] * q) for q in (-0.25, 0.0, 0.25)],
                axis=0)
    rec = {"pieces": [a, b], "row_m": ROW_M, "bin_m": BIN_M, "length_m": round(float(S[-1]) + ROW_M, 1),
           "tiles_missing": missing, "midline_xz": [[round(float(p[0]), 3), round(float(p[2]), 3)] for p in mid],
           "osm_offsets": {"A": [round(float(v), 2) for v in offA], "B": [round(float(v), 2) for v in offB]},
           "lines": {}, "curb": {}, "naip": {}, "ok": {}, "step_m": {}, "segments": {}, "edges_xz": {}}
    nb = len(L)
    band = road_band(G, L, offA, offB, hwA, hwB)
    rec["naip_band"] = [[round(float(a_), 1), round(float(b_), 1)] for a_, b_ in band[::20]]
    single = a == b
    for name, (rib, esign, near, far, sign) in WINDOWS.items():
        if single and name.startswith("median"):
            continue                                    # one carriageway: its two outer edges only
        off, hw = (offA, hwA) if rib == "A" else (offB, hwB)
        edge = off + esign * hw
        lo_l = edge + esign * near
        hi_l = edge + esign * far
        lo_l, hi_l = np.minimum(lo_l, hi_l), np.maximum(lo_l, hi_l)
        lo = np.clip(np.round((lo_l + HALF_M) / BIN_M).astype(int), 0, nb - 1)
        hi = np.clip(np.round((hi_l + HALF_M) / BIN_M).astype(int), 0, nb - 1)
        if name.startswith("outer"):
            # an outer edge is a curb (the ground rises outward) or an embankment's edge (it falls): either sign,
            # capped so a taller berm or wall further out does not outbid the curb, and the innermost preferred
            Dn = np.nan_to_num(D, nan=0.0) * sign             # + = the ground rises outward (a curb)
            sc = np.where(Dn >= 0, np.minimum(Dn, OUTER_CAP_M), np.minimum(-Dn, DROP_CAP_M))
            inner = lo if esign > 0 else hi                  # the window's end nearest the road
            sc = sc - INWARD_COST * np.abs(np.arange(nb)[None, :] - inner[:, None])
        else:
            sc = np.clip(np.nan_to_num(sign * D, nan=0.0), 0.0, 0.3)
        path = viterbi(sc, lo, hi)
        li = L[path]
        raw = np.array([D[i, path[i]] if np.isfinite(D[i, path[i]]) else np.nan for i in range(len(S))])
        st = np.abs(raw) if name.startswith("outer") else sign * raw
        curb = [bool(np.isfinite(v) and v >= _STEP_M()) for v in st]
        kind = ["curb" if (np.isfinite(r) and r * sign > 0) else "drop" for r in raw]
        nai = [naip_agrees(G[i], L, li[i], sign, band[i]) for i in range(len(S))]
        keep, ok = segments(curb, nai)
        rec["lines"][name] = [round(float(v), 2) for v in li]
        rec["step_m"][name] = [None if not np.isfinite(v) else round(float(v), 3) for v in st]
        rec["curb"][name] = curb
        rec.setdefault("kind", {})[name] = kind if name.startswith("outer") else None
        rec["naip"][name] = nai
        rec["ok"][name] = ok
        rec["segments"][name] = [{"s": [round(float(S[i0]), 1), round(float(S[i1]), 1)], "curb_share": c,
                                  "naip_share": q} for i0, i1, c, q in keep]
        rec["edges_xz"][name] = [[round(float(mid[i, 0] + nrm[i, 0] * li[i]), 3),
                                  round(float(mid[i, 2] + nrm[i, 1] * li[i]), 3)] for i in range(len(S))]
    rec["normals"] = [[round(float(v[0]), 4), round(float(v[1]), 4)] for v in nrm]
    rec["apply"] = apply_plan(rec, L, H, hwA, hwB, single)
    return rec, (S, L, H, D, G)


def _ground_at(L, Hrow, lat):
    """the lidar ground at a lateral: the median of the raster cells within +-1 m (None where empty)"""
    import numpy as np
    v = Hrow[np.abs(L - lat) <= 1.0]
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else None


def apply_plan(rec, L, H, hwA, hwB, single):
    """what tools/trim_connectors.measured_edges applies, per piece and row: the carriageway's two edges (laterals off
    the midline) where both are `ok`; across a gap of BRIDGE_M or less between two such stretches the edges run
    straight from one checked end to the other (the unchecked trace is not used); a stretch shorter than MIN_APPLY_M
    is dropped; past each end the edges ease linearly back to OSM's ribbon over TAPER_M. `dy`: the lidar ground at the
    new centre minus at OSM's (the piece's heights were read at OSM's line). null = OSM, as it was."""
    import numpy as np
    n = len(rec["midline_xz"])
    gap = int(round(BRIDGE_M / ROW_M))
    taper = int(round(TAPER_M / ROW_M))
    plans = {}
    pairs = {"A": ("outer_left", "outer_right" if single else "median_left")}
    if not single:
        pairs["B"] = ("median_right", "outer_right")
    for rib, (lo_n, hi_n) in pairs.items():
        off = np.array(rec["osm_offsets"][rib])
        hw = hwA if rib == "A" else hwB
        lo_l, hi_l = np.array(rec["lines"][lo_n]), np.array(rec["lines"][hi_n])
        both = [x and y for x, y in zip(rec["ok"][lo_n], rec["ok"][hi_n])]
        lo_e, hi_e = np.full(n, np.nan), np.full(n, np.nan)
        runs = _runs(both, gap)
        kept = []
        for i0, i1 in runs:
            if (i1 - i0) * ROW_M < MIN_APPLY_M:
                continue
            kept.append((i0, i1))
            for i in range(i0, i1 + 1):
                if both[i]:
                    lo_e[i], hi_e[i] = lo_l[i], hi_l[i]
            idx = [i for i in range(i0, i1 + 1) if both[i]]
            for i in range(i0, i1 + 1):                 # bridge: straight between the checked ends
                if not both[i]:
                    p = max(k for k in idx if k < i)
                    q = min(k for k in idx if k > i)
                    t = (i - p) / (q - p)
                    lo_e[i] = lo_l[p] + (lo_l[q] - lo_l[p]) * t
                    hi_e[i] = hi_l[p] + (hi_l[q] - hi_l[p]) * t
        meas = np.isfinite(lo_e)
        out_lo, out_hi = lo_e.copy(), hi_e.copy()
        for i in range(n):                              # the ease back to OSM past each kept end
            if meas[i]:
                continue
            best = None
            for i0, i1 in kept:
                for end in (i0, i1):
                    d = abs(i - end)
                    if d <= taper and (best is None or d < best[0]):
                        best = (d, end)
            if best is None:
                continue
            w = 1.0 - best[0] / float(taper)
            e = best[1]
            out_lo[i] = w * lo_e[e] + (1 - w) * (off[i] - hw)
            out_hi[i] = w * hi_e[e] + (1 - w) * (off[i] + hw)
        dy = []
        for i in range(n):
            if not np.isfinite(out_lo[i]):
                dy.append(None)
                continue
            g1, g0 = _ground_at(L, H[i], 0.5 * (out_lo[i] + out_hi[i])), _ground_at(L, H[i], off[i])
            dy.append(None if g1 is None or g0 is None else g1 - g0)
        dya = np.array([np.nan if v is None else v for v in dy])
        w = int(round(DY_ALONG_M / ROW_M))
        dys = [None if not np.isfinite(out_lo[i]) else
               (round(float(np.nanmedian(dya[max(0, i - w):i + w + 1])), 3)
                if np.isfinite(dya[max(0, i - w):i + w + 1]).any() else 0.0) for i in range(n)]
        plans[rec["pieces"][0] if rib == "A" else rec["pieces"][1]] = {
            "edges": [None if not np.isfinite(out_lo[i]) else [round(float(out_lo[i]), 2), round(float(out_hi[i]), 2)]
                      for i in range(n)],
            "measured": [bool(v) for v in meas], "dy": dys,
            "stretches_s": [[round(i0 * ROW_M, 1), round(i1 * ROW_M, 1)] for i0, i1 in kept],
            "measured_m": round(float(meas.sum()) * ROW_M, 1), "length_m": round(n * ROW_M, 1)}
    return plans


def _STEP_M():
    from naip_edge import STEP_M
    return STEP_M


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--connectors", required=True)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--naip", required=True)
    ap.add_argument("--origin", required=True, help="a centerline.local.json (its origin)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--raster", help="also save the raster / step map (npz)")
    a = ap.parse_args(argv)
    import numpy as np
    from naip_edge import Naip
    conns = json.loads(Path(a.connectors).read_text(encoding="utf-8"))["connectors"]
    origin = json.loads(Path(a.origin).read_text(encoding="utf-8"))["origin"]
    rec, (S, L, H, D, G) = run(conns, a.a, a.b, a.tiles, Naip(origin, image=a.naip))
    rec["_doc"] = (__doc__.split("\n\n")[0] + " Inputs: connectors " + Path(a.connectors).name + ", lidar CO_DRCOG_2_2020 "
                   "class 2 (tools/lidar_connector_profile.py's tile cache), NAIP 2023 (tracks/sand-creek/source/"
                   "naip_2023_sc_z18.jpg) in the track frame.")
    Path(a.out).write_text(json.dumps(rec), encoding="utf-8")
    if a.raster:
        np.savez(a.raster, S=S, L=L, H=H, D=D, G=G)
    for piece, pl in rec["apply"].items():
        print(f"[curb-trace] apply {piece}: {pl['measured_m']} of {pl['length_m']} m measured, stretches s "
              f"{pl['stretches_s']}; the rest OSM")
    for name, segs in rec["segments"].items():
        tot = sum(sg["s"][1] - sg["s"][0] for sg in segs)
        print(f"[curb-trace] {name}: {len(segs)} segment(s), {tot:.0f} of {rec['length_m']} m ok: "
              + ", ".join(f"s {sg['s'][0]:.0f}-{sg['s'][1]:.0f} (curb {sg['curb_share']:.2f}, naip {sg['naip_share']:.2f})"
                          for sg in segs))
    if rec["tiles_missing"]:
        print(f"[curb-trace] lidar tiles not cached (not fetched): {rec['tiles_missing']}")


if __name__ == "__main__":
    main()

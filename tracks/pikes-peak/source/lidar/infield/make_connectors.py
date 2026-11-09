"""PPIR's infield roads as the engine's side streets (ledger 0085 Phase B): data for lm_intake.connectors_file.

    python make_connectors.py <project with the intake's data/centerline.local.json> <infield_dem.npz> <out json>

From ../../road-course/route_from_maps.naip.json (both published maps' route, every coordinate a measured piece
centre line, the measured lot band, or a straight join between them; Kevin 2026-11-08: the lot's NE side straight):
  - rc_infield: RC-D from LEAD_M before it leaves the oval's line to LEAD_M after it rejoins (both ends on the oval's
    deck, so tools/trim_connectors.py cuts them at the deck's edge and blends them onto it): NE lane, top hairpin,
    diag, the lot (band + the 64.3 m straight), bottom road, west road, sweeper. A host (route.connector_hosts).
  - if_link: IF-K's own piece, bottom road's west end -> S-curve -> C road east -> diag's start, LEAD_M into
    rc_infield at each end (cut there by trim's pass 2).
Widths: each point takes the nearest measured piece's own width per metre (within NEAR_M), the lot band its measured
p50 (9.16 m; per-section widths are not on disk), joins and the oval run the neighbours' (linear). Heights: the 1 m
lidar DEM (infield_ground.py), a SMOOTH_M running mean along (the DEM's ~2 cm noise), in the build's y.
Points resampled every STEP_M. Frame: ENU local metres (x = E, y = up, z = N), the engine's connector frame.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RC = HERE.parents[1] / "road-course"
STEP_M = 2.0          # [invented] the connectors' point spacing (Sand Creek's grid: 3 m)
LEAD_M = 14.0         # [invented] how far each end runs into its host: past the host's centre, never past its far edge
NEAR_M = 3.0          # [invented] a point takes a piece's width within this of its centre line
SMOOTH_M = 9.0        # [invented] the heights' running mean along
LOT_W = 9.16          # the lot band's measured p50 width (route_from_maps lot_band.width_m)
MEDIAN_M = 15.0       # [invented] a running median of the widths along: the older pieces' inferred dusty edges dip to
                      # 4 m for a few metres (s_curve 4.0-11.6, p50 7.8); a lane does not
END_M = 30.0          # [invented] within this of an end on the host, the flare is the mouth's (tools/mouth_returns), not
END_W = 13.0          # the road's: the NE lane's measured diverge mouth reads 22.3 m; capped at its own 12.2 m + 0.8
EASE_M = 25.0         # [invented] the run either side of where RC-D crosses the deck's edge that is redrawn as one
                      # cubic off the two directions (the oval's, the lane's): the route's straight join from the oval's
                      # mid line to the measured lane's first point crossed the edge at 82 deg (NE) / 57 deg (NW), a kink
                      # no driver takes; the pavement there is continuous (the apron, the diverge's mouth: inside_edge
                      # junction runs s 945-995, 1308-1377), so the driven line eases across it
R_MIN = 12.0          # [invented, from the measured pieces] the tightest centre-line radius kept: the pieces' tightest
                      # traced edge is 7.6 m (diag_s left), a 12 m road's centre ~13.6 m. Tighter spots are the route's
                      # straight joins between pieces (35-100 deg in 4 m) and the lot band's noisy west end
MAX_MOVE = 3.0        # [invented] the relaxation never moves a point further than this from the route (a quarter of a road)
CAP_W = 14.5          # [invented] where a piece's measured width runs out across a junction (hairpin top 20.3 m, west road
                      # 18.9 m: the side roads' mouths, not this road), the widest piece's own p50 (bottom 14.0) + 0.5
FLOOR_FRAC = 0.85     # [invented] no point narrower than 85 % of its piece's p50 (the S-curve's weak, dusty edges)


def resample(P, step):
    P = np.asarray(P, float)
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    t = np.linspace(0, s[-1], max(2, int(round(s[-1] / step)) + 1))
    return np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], t


def lateral_off(P, line):
    """unsigned distance of each P to the closed polyline `line`"""
    A = line; B = np.roll(line, -1, 0); AB = B - A; L2 = np.maximum((AB * AB).sum(1), 1e-12)
    out = []
    for q in P:
        t = np.clip(((q - A) * AB).sum(1) / L2, 0, 1)
        out.append(np.min(np.hypot(*(A + AB * t[:, None] - q).T)))
    return np.array(out)


def dem_sampler(npz):
    d = np.load(npz)
    dem, e0, n0, c = d["dem"], float(d["e0"]), float(d["n0"]), float(d["cell_m"])
    ny, nx = dem.shape

    def f(E, N):
        fx = (np.asarray(E) - e0) / c - 0.5; fy = (np.asarray(N) - n0) / c - 0.5
        x0 = np.clip(np.floor(fx).astype(int), 0, nx - 2); y0 = np.clip(np.floor(fy).astype(int), 0, ny - 2)
        tx = np.clip(fx - x0, 0, 1); ty = np.clip(fy - y0, 0, 1)
        return (dem[y0, x0] * (1 - tx) * (1 - ty) + dem[y0, x0 + 1] * tx * (1 - ty)
                + dem[y0 + 1, x0] * (1 - tx) * ty + dem[y0 + 1, x0 + 1] * tx * ty)
    return f


def radius(P, w=3, closed=False):
    if closed:
        A = np.roll(P, w, 0); B = np.roll(P, -w, 0)
    else:
        A = np.r_[np.repeat(P[:1], w, 0), P[:-w]]; B = np.r_[P[w:], np.repeat(P[-1:], w, 0)]
    a = np.hypot(*(P - A).T); b = np.hypot(*(B - P).T); c = np.hypot(*(B - A).T)
    cross = np.abs((P - A)[:, 0] * (B - A)[:, 1] - (P - A)[:, 1] * (B - A)[:, 0])
    with np.errstate(divide="ignore", invalid="ignore"):
        R = a * b * c / np.maximum(2 * cross, 1e-12)
    R[~np.isfinite(R)] = 1e9
    if not closed:
        R[:w] = R[-w:] = 1e9
    return R


def relax(R0, closed=False, iters=3000, grow=4):
    """Points on a radius under R_MIN (and GROW either side) move half-way to their neighbours' mean, pass after pass,
    never more than MAX_MOVE from the route: the joins' kinks ease, the measured pieces' own corners stay."""
    S = R0.copy()
    n = len(S)
    ker = np.ones(2 * grow + 1)
    for _ in range(iters):
        bad = radius(S, closed=closed) < R_MIN
        if not bad.any():
            break
        if closed:
            k = np.convolve(np.r_[bad[-grow:], bad, bad[:grow]].astype(float), ker, "valid") > 0
            lap = 0.5 * (np.roll(S, 1, 0) + np.roll(S, -1, 0)) - S
        else:
            k = np.convolve(bad.astype(float), ker, "same") > 0
            lap = np.zeros_like(S); lap[1:-1] = 0.5 * (S[:-2] + S[2:]) - S[1:-1]
        S[k] += 0.5 * lap[k]
        dev = S - R0; m = np.hypot(*dev.T); o = m > MAX_MOVE
        S[o] = R0[o] + dev[o] * (MAX_MOVE / m[o])[:, None]
    rad = radius(S, closed=closed); mv = np.hypot(*(S - R0).T)
    return S, {"min_radius_m": round(float(rad.min()), 1), "points_under_r_min": int((rad < R_MIN).sum()),
               "max_move_m": round(float(mv.max()), 2), "p95_move_m": round(float(np.percentile(mv, 95)), 2), "n": n}


def hermite(R, a, b):
    """R[a..b] redrawn as a cubic Hermite from R[a] to R[b] on their own directions (1 m points), magnitude = chord."""
    P0, P1 = R[a], R[b]
    T0 = R[a + 1] - R[a - 1]; T0 = T0 / np.linalg.norm(T0)
    T1 = R[b + 1] - R[b - 1]; T1 = T1 / np.linalg.norm(T1)
    ch = np.linalg.norm(P1 - P0)
    u = np.linspace(0, 1, b - a + 1)[:, None]
    h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
    return h00 * P0 + h10 * ch * T0 + h01 * P1 + h11 * ch * T1


def widths_for(C, pieces, names, lot_mask):
    w = np.full(len(C), np.nan)
    floor = np.zeros(len(C))
    for nm in names:
        pc = np.array(pieces[nm]["centre_en_m"]); pw = np.array(pieces[nm]["width_m_per_metre"], float)
        for i, q in enumerate(C):
            d = np.hypot(*(pc - q).T); j = int(np.argmin(d))
            if d[j] <= NEAR_M and (np.isnan(w[i]) or d[j] < 1.0):
                w[i] = pw[min(j, len(pw) - 1)]
                floor[i] = FLOOR_FRAC * float(pieces[nm]["width_m"]["p50"])
    w[lot_mask & np.isnan(w)] = LOT_W
    ok = np.isfinite(w)
    idx = np.arange(len(w))
    w[~ok] = np.interp(idx[~ok], idx[ok], w[ok])
    k = max(1, int(round(MEDIAN_M / STEP_M)) // 2)
    w = np.array([np.median(w[max(0, i - k):i + k + 1]) for i in range(len(w))])
    w = np.clip(np.maximum(w, floor), None, CAP_W)
    n_end = int(round(END_M / STEP_M))
    w[:n_end] = np.minimum(w[:n_end], END_W)
    w[-n_end:] = np.minimum(w[-n_end:], END_W)
    return w


def main(proj, dem_npz, out):
    loc = json.loads((Path(proj) / "data/centerline.local.json").read_text(encoding="utf-8"))
    line = np.array(loc["points_xyz_m"])[:, [0, 2]]
    lw = np.array(loc["widths_m"])
    routes = json.loads((RC / "route_from_maps.naip.json").read_text(encoding="utf-8"))
    pieces = json.loads((RC / "infield_pieces.naip.json").read_text(encoding="utf-8"))["pieces"]
    lot = np.array(routes["lot_band"]["centre_en_m"])
    dem = dem_sampler(dem_npz)
    half_max = float(lw.max()) / 2.0
    res = []
    # rc_infield: RC-D's run off the oval (laterals past the deck's widest half-width + 1 m), LEAD_M either side
    R = np.array(routes["routes"]["RC-D"]["centre_en_m"])
    off = lateral_off(R, line)
    out_idx = np.flatnonzero(off > half_max + 1.0)
    i0, i1 = int(out_idx.min()), int(out_idx.max())
    R = R.copy()
    e = int(EASE_M)
    for a, b in ((i0 - e, i0 + e), (i1 - e, i1 + e)):
        R[a:b + 1] = hermite(R, a, b)
    R, rep = relax(R)
    print(f"[connectors] RC-D relaxed: {rep}")
    i0, i1 = max(0, i0 - int(LEAD_M)), min(len(R) - 1, i1 + int(LEAD_M))
    C, t = resample(R[i0:i1 + 1], STEP_M)
    lot_mask = np.array([np.min(np.hypot(*(lot - q).T)) <= 4.0 for q in C])
    # the 64.3 m straight join before the band also takes the band's width
    rcd_names = ["ne_lane", "hairpin_w", "diag_n", "diag_s", "bottom", "west_n", "arc_nw"]
    w = widths_for(C, pieces, rcd_names, lot_mask)
    res.append(("rc_infield", C, w, f"RC-D route_from_maps idx {i0}..{i1}"))
    # if_link: IF-K from LEAD_M before the S-curve (bottom's west end) to LEAD_M into diag_n (wrapping its start)
    K, rep = relax(np.array(routes["routes"]["IF-K"]["centre_en_m"]), closed=True)
    print(f"[connectors] IF-K relaxed: {rep} (its tight spots left are the junction turns at both ends of if_link)")
    parts = routes["routes"]["IF-K"]["part_m"]; joins = [j["gap_m"] for j in routes["routes"]["IF-K"]["joins"]]
    names = list(parts)
    acc = 0.0; start_s = None
    for k, nm in enumerate(names):
        if nm == "s_curve":
            start_s = acc
        acc += parts[nm] + (joins[k] if k < len(joins) else 0.0)
    j0 = int(round(start_s - LEAD_M))
    seg = np.vstack([K[j0:], K[:int(LEAD_M) + 1]])
    C2, _ = resample(seg, STEP_M)
    w2 = widths_for(C2, pieces, ["s_curve", "c_road", "bottom", "diag_n"], np.zeros(len(C2), bool))
    res.append(("if_link", C2, w2, f"IF-K route_from_maps idx {j0}..end + 0..{int(LEAD_M)}"))
    conns = []
    for name, C_, w_, src in res:
        y = dem(C_[:, 0], C_[:, 1])
        k = max(1, int(round(SMOOTH_M / STEP_M)) // 2)
        ys = np.array([y[max(0, i - k):i + k + 1].mean() for i in range(len(y))])
        conns.append({"name": name, "kind": "connector",
                      "points_xyz_m": [[round(float(x), 3), round(float(yy), 4), round(float(z), 3)] for (x, z), yy in zip(C_, ys)],
                      "widths_m": [round(float(v), 3) for v in w_], "joined": [],
                      "source": f"tracks/pikes-peak/source/road-course/route_from_maps.naip.json ({src}); heights: "
                                f"infield_ground.py's lidar DEM, {SMOOTH_M:.0f} m mean"})
        L = float(np.sum(np.hypot(*np.diff(C_, axis=0).T)))
        print(f"[connectors] {name}: {len(C_)} points, {L:.1f} m, widths {w_.min():.2f}..{w_.max():.2f} m "
              f"(p50 {np.median(w_):.2f}), heights {ys.min():+.2f}..{ys.max():+.2f} m; ends "
              f"{lateral_off(C_[[0, -1]], line).round(2).tolist()} m off the oval's line ({src})")
    Path(out).write_text(json.dumps({"connectors": conns}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:4])

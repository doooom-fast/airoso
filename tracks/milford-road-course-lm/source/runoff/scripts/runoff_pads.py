"""Milford's paved run-off, aprons and side lanes outlined as bespoke pads (ledger 0092; the 2026-11-18 scenery audit's item 3).

The audit (Milford 0.1.12 vs High Plains 0.1.7) measured ~16,900 m2 of pavement within 30 m of the lane edge drawn as turf:
class D of the measured class map (source/vegetation/grass_classes.png, 2 m cells: "no grass, pavement or gravel the build
carries as ground") plus bright grey concrete the D rule misses (NAIP 2022 mean over GREY_MEAN, grey). Here every such blob of
at least MIN_M2 beside the lap (outside the ride pad, which is its own pad) whose NAIP colour is grey (pavement, not the
gravel / dry ground D also holds) is outlined in the road's own frame, per STEP_M of station: the blob's offset range from the
lane edge on its side, as a strip pad (tools/author_bespoke_blend.py "strip_lonlat": inner / outer, one quad per pair). A blob
that reaches within ADJ_M of the lane edge starts at the edge strip's outer lip (LIP_M), so the run-off meets the built
pavement as the photograph shows it does. Nevada's route (ledger 0081): the config seats the pads on the prepped ground as
1RUNOFF (scenery.bespoke.pads_seat "ground", pads_surface "1RUNOFF").

    python runoff_pads.py [--write] [--line <a centerline.local.json>]

Reads the committed class map, NAIP 2022 (source/road_wear/naip_2022_mrc.jpg, the same bbox), data/centerline.local.json (or
--line: the intake's line of a workshop, e.g. a dry run's, before the build commits it) and the config's ride pad. The lane edge
is the one the assembler builds (ledger 0091): that line through the route's own smoothing (scripts-v021 geometry/smooth.py,
route.smooth_*), +- widths_m / 2. With lm_intake.line_precomp the intake's line is not the built one (Milford 0.1.13: 0.21 m
p50, 4.25 m at most off it; 0.1.12's 0.12 / 1.68 m), and outlining on it put a pad 0.92 m onto the lane at s 355 and folded
7 quads. A quad that still folds (the inside of a tight bend at a large offset: the offset curve turns back) loses the row
that turns it back, until none does (the blob's "rows_dropped"). The record carries the line's md5. Writes ../runoff_pads.json (every blob: area, D / grey share, stations, offsets, NAIP colour, kept or why
not, the fold check); with --write, the config's scenery.bespoke.pads = the ride pad (kept first: PADAPRON_0) + one strip pad
per kept blob (the file is re-dumped indent 2, as it is committed, so nothing else in it moves). Deterministic: re-run it after
the line or the widths move.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

T = Path(__file__).resolve().parents[3]
REPO = T.parents[1]
sys.path.insert(0, str(REPO))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402  (the draft's own lon/lat -> metres)

MIN_M2 = 150.0      # [invented] the smallest blob outlined (the audit listed D blobs from 212 m2, grey from 168 m2)
REACH_M = 40.0      # the audit's reach for D blobs (D_blobs.json: "within 40 m")
GREY_REACH_M = 30.0  # the audit's reach for the grey concrete (grey_not_D_blobs.json: "within 30 m")
GREY_MEAN = 165.0   # the audit's rule: NAIP mean over 165 ...
GREY_SPREAD = 24.0  # [invented] ... and grey: max - min channel under this
PAVED_B_OVER_R = 0.88  # [invented] a kept blob's NAIP p50 blue / red: the lanes read 174 / 188 = 0.93, the ride pad 0.99, the
#                        mown turf 118 / 157 = 0.75; D blobs at 0.72-0.80 are bare ground or gravel, not pavement (kept out)
STEP_M = 4.0        # [invented] the strip's station step (the pad's own 4 m cell, tools/author_bespoke_blend.py PAD_CELL_M)
HALF_PX_M = 1.0     # half a class-map cell: a blob's pixels reach this past their centres
LIP_M = 1.9         # measured: the edge strip's outer lip, lane edge + 1.73-1.84 m (p99 of the 0.1.5 gate OBJ's 1KERB
#                     vertices per 250 m of station, 0.1.12's line) + 0.1 m [invented], so no pad cell lands on the strip
ADJ_M = 3.0         # [invented] a blob whose pixels come within this of the lane edge is run-off at the edge


def load_line(cfg, path=None):
    """the lane the assembler builds: the intake's line through the route's own smoothing, its widths (ledger 0091)"""
    import hashlib
    import importlib.util
    lp = Path(path) if path else T / "data" / "centerline.local.json"
    raw = lp.read_bytes()
    cl = json.loads(raw.decode("utf-8"))
    sp = importlib.util.spec_from_file_location(
        "_lm_smooth", REPO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py")
    sm = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(sm)
    route = cfg.get("route") or {}
    pts = sm.smooth_centerline([tuple(p) for p in cl["points_xyz_m"]], sigma_pts=float(route.get("smooth_sigma_pts", 2.0)),
                               passes=int(route.get("smooth_passes", 2)), sigma_y_pts=0.0)
    load_line.md5 = hashlib.md5(raw).hexdigest()
    P = np.array(pts, float)[:, [0, 2]]
    half = np.array(cl["widths_m"], float) / 2.0
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    return cl["origin"], P, half, s


def edge_query(P, half, s, qx, qz, chunk=256):
    """per query point: distance to the lane edge (+ outside), station, side (+1 left of travel), as make_treefx RoadField"""
    ax, az, bx, bz = P[:-1, 0], P[:-1, 1], P[1:, 0], P[1:, 1]
    dx, dz = bx - ax, bz - az
    L2 = np.where(dx * dx + dz * dz == 0, 1.0, dx * dx + dz * dz)
    out = np.empty((len(qx), 3))
    for k in range(0, len(qx), chunk):
        x, z = qx[k:k + chunk, None], qz[k:k + chunk, None]
        t = np.clip(((x - ax) * dx + (z - az) * dz) / L2, 0, 1)
        d = np.hypot(x - ax - t * dx, z - az - t * dz) - (half[:-1] * (1 - t) + half[1:] * t)
        j = np.argmin(d, axis=1)
        r = np.arange(len(j))
        out[k:k + chunk, 0] = d[r, j]
        out[k:k + chunk, 1] = s[j] + t[r, j] * np.sqrt(L2[j])
        out[k:k + chunk, 2] = np.sign(dx[j] * (z[:, 0] - az[j]) - dz[j] * (x[:, 0] - ax[j]))
    return out


def point_in(poly, x, z):
    c = np.zeros(np.shape(x), bool)
    for k in range(len(poly)):
        (x1, z1), (x2, z2) = poly[k - 1], poly[k]
        hit = ((z1 > z) != (z2 > z)) & (x < x1 + (z - z1) * (x2 - x1) / ((z2 - z1) if z2 != z1 else 1e-12))
        c ^= hit
    return c


def label8(mask):
    """8-connected components of a boolean raster -> (labels, n)"""
    lab = np.zeros(mask.shape, int)
    n = 0
    H, W = mask.shape
    for j0, i0 in zip(*np.nonzero(mask)):
        if lab[j0, i0]:
            continue
        n += 1
        lab[j0, i0] = n
        st = [(j0, i0)]
        while st:
            j, i = st.pop()
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    a, b = j + dj, i + di
                    if 0 <= a < H and 0 <= b < W and mask[a, b] and not lab[a, b]:
                        lab[a, b] = n
                        st.append((a, b))
    return lab, n


def frame_at(P, half, s, q):
    """centreline point, left normal and half width at station q"""
    q = q % s[-1]
    i = int(np.clip(np.searchsorted(s, q) - 1, 0, len(s) - 2))
    t = (q - s[i]) / max(s[i + 1] - s[i], 1e-9)
    c = P[i] * (1 - t) + P[i + 1] * t
    tg = P[i + 1] - P[i]
    tg = tg / (np.hypot(*tg) or 1.0)
    return c, np.array([-tg[1], tg[0]]), half[i] * (1 - t) + half[i + 1] * t


def outline(rows, P, half, s, side):
    inner, outer = [], []
    for q0, d_lo, d_hi in rows:
        c, nrm, hw = frame_at(P, half, s, q0)
        inner.append(tuple(c + nrm * side * (hw + d_lo)))
        outer.append(tuple(c + nrm * side * (hw + d_hi)))
    return inner, outer


def _quad_sign(inner, outer, i):
    quad = [inner[i], inner[i + 1], outer[i + 1], outer[i]]
    cr = [(quad[(a + 1) % 4][0] - quad[a][0]) * (quad[(a + 2) % 4][1] - quad[(a + 1) % 4][1])
          - (quad[(a + 1) % 4][1] - quad[a][1]) * (quad[(a + 2) % 4][0] - quad[(a + 1) % 4][0]) for a in range(4)]
    return 1 if all(v > 0 for v in cr) else -1 if all(v < 0 for v in cr) else 0


def _major_sign(inner, outer):
    sg = [_quad_sign(inner, outer, i) for i in range(len(inner) - 1)]
    return 1 if sg.count(1) >= sg.count(-1) else -1


def folds_of(inner, outer):
    """quads that are not convex, plus 1 when the quads do not all keep one winding"""
    sgn = []
    for i in range(len(inner) - 1):
        quad = [inner[i], inner[i + 1], outer[i + 1], outer[i]]
        cr = [(quad[(a + 1) % 4][0] - quad[a][0]) * (quad[(a + 2) % 4][1] - quad[(a + 1) % 4][1])
              - (quad[(a + 1) % 4][1] - quad[a][1]) * (quad[(a + 2) % 4][0] - quad[(a + 1) % 4][0]) for a in range(4)]
        sgn.append(1 if all(v > 0 for v in cr) else -1 if all(v < 0 for v in cr) else 0)
    return sum(1 for v in sgn if v == 0) + (0 if len(set(v for v in sgn if v)) <= 1 else 1)


def area_of(inner, outer):
    ring = list(inner) + list(outer)[::-1]
    return abs(sum(ring[k - 1][0] * ring[k][1] - ring[k][0] * ring[k - 1][1] for k in range(len(ring)))) / 2


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cfg_p = T / "track.config.json"
    cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    bes = cfg["scenery"]["bespoke"]
    gz = bes["grassfx_zones"]
    line_p = argv[argv.index("--line") + 1] if "--line" in argv else None
    origin, P, half, s = load_line(cfg, line_p)
    lap = float(s[-1])
    m_lon, m_lat = _meters_per_degree(origin["lat"])
    W_, S_, E_, N_ = gz["bbox_lonlat"]
    G = np.asarray(Image.open(T / gz["image"]).convert("RGB")).astype(int)
    H, W = G.shape[:2]
    lon = W_ + (np.arange(W) + 0.5) / W * (E_ - W_)
    lat = N_ - (np.arange(H) + 0.5) / H * (N_ - S_)
    X, Z = np.meshgrid((lon - origin["lon"]) * m_lon, (lat - origin["lat"]) * m_lat)
    px_m2 = abs((E_ - W_) / W * m_lon * (N_ - S_) / H * m_lat)
    r, g, b = G[..., 0], G[..., 1], G[..., 2]
    is_D = (r < 40) & (g < 40) & (b > 170)
    is_C = (r < 40) & (g > 90) & (g < 150) & (b < 40)
    # NAIP 2022 over the same bbox: each class cell's mean colour
    aer = cfg["road_wear"]["aerial"]
    if aer["bbox_lonlat"] != gz["bbox_lonlat"]:
        raise SystemExit("runoff_pads: the NAIP and the class map must share one bbox")
    Nm = np.asarray(Image.open(T / aer["image"]).convert("RGB")).astype(float)
    nh, nw = Nm.shape[:2]
    ri = (np.arange(H + 1) * nh / H).astype(int)
    ci = (np.arange(W + 1) * nw / W).astype(int)
    cs = np.pad(Nm, ((1, 0), (1, 0), (0, 0))).cumsum(0).cumsum(1)
    tot = cs[ri[1:]][:, ci[1:]] - cs[ri[:-1]][:, ci[1:]] - cs[ri[1:]][:, ci[:-1]] + cs[ri[:-1]][:, ci[:-1]]
    cnt = ((ri[1:] - ri[:-1])[:, None] * (ci[1:] - ci[:-1])[None, :])[..., None]
    naip = tot / np.maximum(cnt, 1)
    cx, cz = X.ravel(), Z.ravel()
    lo = (cx > P[:, 0].min() - 80) & (cx < P[:, 0].max() + 80) & (cz > P[:, 1].min() - 80) & (cz < P[:, 1].max() + 80)
    Dd = np.full(H * W, np.inf)
    Ss = np.full(H * W, np.nan)
    Sd = np.zeros(H * W)
    q = edge_query(P, half, s, cx[lo], cz[lo])
    Dd[lo], Ss[lo], Sd[lo] = q[:, 0], q[:, 1], q[:, 2]
    Dd, Ss, Sd = Dd.reshape(H, W), Ss.reshape(H, W), Sd.reshape(H, W)
    ride = next(p for p in bes["pads"] if p["key"] == "ride_pad")
    rq = [((a - origin["lon"]) * m_lon, (c - origin["lat"]) * m_lat) for a, c in ride["quad_lonlat"]]
    in_ride = point_in(rq, X, Z)
    mean = naip.mean(-1)
    spread = naip.max(-1) - naip.min(-1)
    m_D = is_D & (Dd >= 0) & (Dd < REACH_M) & ~in_ride
    m_G = ~is_D & ~is_C & (mean > GREY_MEAN) & (spread < GREY_SPREAD) & (Dd >= LIP_M - HALF_PX_M) & (Dd < GREY_REACH_M) & ~in_ride
    lab, n = label8(m_D | m_G)
    blobs = []
    for k in range(1, n + 1):
        m = lab == k
        area = float(m.sum() * px_m2)
        if area < MIN_M2:
            continue
        side = 1 if Sd[m].sum() >= 0 else -1
        mm = m & (Sd == side)
        st, dd = Ss[mm], Dd[mm]
        if st.max() - st.min() > lap / 2:            # across the line's seam (s 0)
            st = np.where(st < lap / 2, st + lap, st)
        b0 = math.floor(st.min() / STEP_M) * STEP_M
        b1 = math.ceil(st.max() / STEP_M) * STEP_M
        rows = []
        for q0 in np.arange(b0, b1 + 1e-6, STEP_M):
            sel = (st >= q0 - STEP_M / 2) & (st < q0 + STEP_M / 2)
            if not sel.any():
                continue
            d_lo, d_hi = float(dd[sel].min()) - HALF_PX_M, float(dd[sel].max()) + HALF_PX_M
            if d_lo < ADJ_M:
                d_lo = LIP_M
            rows.append((float(q0), d_lo, max(d_hi, d_lo + STEP_M / 2)))
        if len(rows) < 2:                             # a blob inside one bin: one quad its own length
            q_mid, d_lo, d_hi = rows[0] if rows else (float(st.mean()), LIP_M, LIP_M + STEP_M)
            rows = [(q_mid - STEP_M / 2, d_lo, d_hi), (q_mid + STEP_M / 2, d_lo, d_hi)]
        else:                                         # the ends at the blob's own first / last pixel
            rows[0] = (max(rows[0][0], float(st.min()) - HALF_PX_M), rows[0][1], rows[0][2])
            rows[-1] = (min(rows[-1][0], float(st.max()) + HALF_PX_M), rows[-1][1], rows[-1][2])
        inner, outer = outline(rows, P, half, s, side)
        dropped = 0
        while folds_of(inner, outer) and len(rows) > 2:  # a quad the offset curve turns back in: drop its turning row
            k_ = next(i for i in range(len(inner) - 1) if _quad_sign(inner, outer, i) != _major_sign(inner, outer))
            del rows[k_ + 1 if k_ + 1 < len(rows) - 1 else k_]
            inner, outer = outline(rows, P, half, s, side)
            dropped += 1
        rgb = np.median(naip[m], 0)
        b_over_r = float(rgb[2] / max(rgb[0], 1.0))
        s_mid = float(np.median(st)) % lap
        blobs.append({
            "key": f"runoff_{'L' if side > 0 else 'R'}{int(round(s_mid)):04d}",
            "side": "L" if side > 0 else "R", "s_median": round(s_mid, 1),
            "s_range": [round(rows[0][0] % lap, 1), round(rows[-1][0] % lap, 1)],
            "area_m2": round(area), "D_m2": round(float((m & m_D).sum() * px_m2)), "grey_m2": round(float((m & m_G).sum() * px_m2)),
            "off_edge_m": [round(float(dd.min()), 1), round(float(dd.max()), 1)],
            "within_30m_m2": round(float((m & (Dd < 30)).sum() * px_m2)), "within_9m_m2": round(float((m & (Dd < 9)).sum() * px_m2)),
            "naip_rgb_p50": [int(v) for v in rgb], "naip_b_over_r": round(b_over_r, 3),
            "kept": b_over_r >= PAVED_B_OVER_R,
            "why": "pavement (NAIP grey)" if b_over_r >= PAVED_B_OVER_R else
                   f"NAIP blue / red {b_over_r:.2f} under {PAVED_B_OVER_R}: bare ground or gravel, not pavement",
            "outline_m2": round(area_of(inner, outer)), "quads": len(inner) - 1, "folds": folds_of(inner, outer),
            **({"rows_dropped": dropped} if dropped else {}),
            "inner_xz": [[round(x, 2), round(z, 2)] for x, z in inner],
            "outer_xz": [[round(x, 2), round(z, 2)] for x, z in outer]})
    blobs.sort(key=lambda b_: (b_["s_median"], b_["side"]))
    kept = [b_ for b_ in blobs if b_["kept"]]
    # overlap check between kept strips on one side (the quads' mid points against the other's ring)
    overlaps = []
    for a in range(len(kept)):
        for c in range(a + 1, len(kept)):
            A, B = kept[a], kept[c]
            if A["side"] != B["side"]:
                continue
            ringB = B["inner_xz"] + B["outer_xz"][::-1]
            mids = np.array([((p[0] + q_[0]) / 2, (p[1] + q_[1]) / 2) for p, q_ in zip(A["inner_xz"], A["outer_xz"])])
            hit = int(point_in(ringB, mids[:, 0], mids[:, 1]).sum())
            if hit:
                overlaps.append([A["key"], B["key"], hit])
    road = (Dd < -0.5) & (Dd > -3.0)
    ref = {"road_lanes_rgb_p50": [int(v) for v in np.median(naip[road], 0)],
           "ride_pad_rgb_p50": [int(v) for v in np.median(naip[in_ride], 0)],
           "turf_base_3_30m_rgb_p50": [int(v) for v in np.median(naip[~is_D & ~is_C & (Dd >= 3) & (Dd < 30) & (r > 230)], 0)]}
    m30 = (m_D | m_G) & (Dd < 30)
    rec = {"_doc": __doc__.split("\n\n")[0] + " Written by source/runoff/scripts/runoff_pads.py.",
           "params": {"MIN_M2": MIN_M2, "REACH_M": REACH_M, "GREY_REACH_M": GREY_REACH_M, "GREY_MEAN": GREY_MEAN,
                      "GREY_SPREAD": GREY_SPREAD, "PAVED_B_OVER_R": PAVED_B_OVER_R, "STEP_M": STEP_M, "LIP_M": LIP_M,
                      "ADJ_M": ADJ_M},
           "within_30m_m2": {"D": round(float((m_D & (Dd < 30)).sum() * px_m2)), "grey": round(float((m_G & (Dd < 30)).sum() * px_m2)),
                             "all": round(float(m30.sum() * px_m2)),
                             "in_kept_blobs": sum(b_["within_30m_m2"] for b_ in kept),
                             "in_blobs_left_out": sum(b_["within_30m_m2"] for b_ in blobs if not b_["kept"])},
           "line": {"md5": load_line.md5, "frame": "the intake's data/centerline.local.json through the route's own smoothing "
                                                  "(the assembler's line), +- widths_m / 2"},
           "kept": len(kept), "left_out": len(blobs) - len(kept), "overlaps": overlaps,
           "reference_colours": ref, "blobs": blobs}
    (T / "source" / "runoff" / "runoff_pads.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(f"[runoff] {len(blobs)} blobs of >= {MIN_M2:.0f} m2, {len(kept)} kept as pavement; within 30 m {rec['within_30m_m2']}; "
          f"folds {sum(b_['folds'] for b_ in kept)}; overlaps {overlaps}; colours {ref}")
    for b_ in blobs:
        print(f"  {'+' if b_['kept'] else '-'} {b_['key']}: {b_['area_m2']} m2 (D {b_['D_m2']}, grey {b_['grey_m2']}), s {b_['s_range']}, "
              f"{b_['off_edge_m']} m off, NAIP {b_['naip_rgb_p50']} b/r {b_['naip_b_over_r']}, {b_['quads']} quads, "
              f"outline {b_['outline_m2']} m2, folds {b_['folds']}")
    if "--write" in argv:
        def ll(p):
            return [round(origin["lon"] + p[0] / m_lon, 8), round(origin["lat"] + p[1] / m_lat, 8)]
        bes["pads"] = [ride] + [{"key": b_["key"], "strip_lonlat": {"inner": [ll(p) for p in b_["inner_xz"]],
                                                                    "outer": [ll(p) for p in b_["outer_xz"]]},
                                 "_source": f"ledger 0092: {b_['area_m2']} m2 of paved ground (class D {b_['D_m2']}, NAIP grey "
                                            f"{b_['grey_m2']}) beside s {b_['s_range'][0]:.0f}-{b_['s_range'][1]:.0f} "
                                            f"{b_['side']}, outlined by source/runoff/scripts/runoff_pads.py"}
                                for b_ in kept]
        cfg_p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[runoff] wrote {len(bes['pads'])} pads into {cfg_p.name} scenery.bespoke.pads (the ride pad first)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

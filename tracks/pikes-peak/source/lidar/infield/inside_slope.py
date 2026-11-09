"""The oval's unbuilt inside pavement (built lane's left edge -> the NAIP inside edge) read off the 2018 lidar
(ledger 0085 owed: "the apron's slope, then the inside edge can be built").

    python inside_slope.py <workshop> <infield.npz> <out.json>

Per 3 m station of the BUILT line (<workshop>/data/finished_centerline.json, the deck pikes-peak-lm 0.1.0 shipped),
class-2 ground points within +-ALONG_M along and across the left (inside, CCW lap) normal:
  - lane:    lateral -LANE_M..+LANE_M, a least-squares line: the deck's own cross-slope (checks this read against
             crossfall.json, the G10's survey of the same 2018 returns) and its height against the built deck;
  - inside:  lateral half_w+GAP_M .. edge-GAP_M (edge = inside_edge.naip.json's measured edge, its own frame,
             nearest by position), a line: the apron's slope, and the step where it meets the lane plane at half_w;
  - knee:    one continuous two-segment line over -LANE_M .. edge-GAP_M, its knee searched every 0.25 m: where the
             bank's plane really ends (it need not be the built edge);
  - beyond:  edge+1 .. edge+BEYOND_M: the infield ground's fall away from the pavement.
Slopes in % of lateral, + = inside (left) higher, as crossfall.json. Only the fit; nothing here changes a build.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
RC = HERE.parents[1] / "road-course"
ELEV0 = 1634.84            # the port's origin elev_m (centerline.local.json), the build's y = 0
STEP_M = 3.0               # the camber survey's station step
ALONG_M = 1.5              # [invented] +-1.5 m along: ~3 m x band width at ~1.9 ground pts/m2
LANE_M = 6.5               # the camber survey's half-width
GAP_M = 0.3                # [invented] clear of the built edge and the measured edge
BEYOND_M = 12.0            # [invented]
MIN_PTS = 10               # [invented]


def line_fit(x, z):
    if len(x) < MIN_PTS or np.ptp(x) < 2.0:
        return None
    A = np.c_[np.ones_like(x), x]
    keep = np.ones(len(x), bool)
    for _ in range(3):                    # trimmed: drop > 3 sd (cars, cones, a kerb lip) twice
        c, *_ = np.linalg.lstsq(A[keep], z[keep], rcond=None)
        r = z - A @ c
        sd = np.std(r[keep])
        nk = np.abs(r) <= max(3 * sd, 0.03)
        if (nk == keep).all():
            break
        keep = nk
    c, *_ = np.linalg.lstsq(A[keep], z[keep], rcond=None)
    sd = float(np.std(z[keep] - A[keep] @ c))
    return {"a": float(c[0]), "b": float(c[1]), "sd": sd, "n": int(keep.sum())}


def knee_fit(x, z, lo, hi):
    """z = a + b x + c max(0, x - k): continuous, knee k in [lo, hi] every 0.25 m; best by residual sd."""
    if len(x) < 2 * MIN_PTS:
        return None
    best = None
    for k in np.arange(lo, hi + 1e-9, 0.25):
        if (x > k).sum() < MIN_PTS // 2 or (x <= k).sum() < MIN_PTS:
            continue
        A = np.c_[np.ones_like(x), x, np.maximum(0, x - k)]
        c, *_ = np.linalg.lstsq(A, z, rcond=None)
        sd = float(np.std(z - A @ c))
        if best is None or sd < best["sd"]:
            best = {"knee_m": float(k), "b_in": float(c[1]), "b_out": float(c[1] + c[2]), "sd": sd,
                    "c": [float(c[0]), float(c[1]), float(c[2])]}
    return best


def main(ws, npz, out):
    ws = Path(ws)
    fc = json.loads((ws / "data/finished_centerline.json").read_text(encoding="utf-8"))
    P = np.array(fc["points_xyz_m"]); W = np.array(fc["widths_m"])
    # finished_centerline.json is in the kn5 frame (x, y, -z of the local ENU) after the PC prep, in build_mesh's mesh
    # frame (z = north) straight after a draft, as its "frame" names (tools/lidar_crossfall.line_points)
    sz = 1.0 if str(fc.get("frame") or "").startswith("mesh") else -1.0
    xy = np.c_[P[:, 0], sz * P[:, 2]]
    area = 0.5 * np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1])
    seg = np.hypot(*np.diff(np.vstack([xy, xy[:1]]), axis=0).T)
    s = np.r_[0, np.cumsum(seg)]; lap = s[-1]
    st = np.arange(0, lap, STEP_M)
    ex = np.interp(st, s, np.r_[xy[:, 0], xy[0, 0]]); ez = np.interp(st, s, np.r_[xy[:, 1], xy[0, 1]])
    ey = np.interp(st, s, np.r_[P[:, 1], P[0, 1]]); hw = np.interp(st, s, np.r_[W, W[0]]) / 2
    C = np.c_[ex, ez]
    T = np.roll(C, -1, 0) - np.roll(C, 1, 0); T /= np.linalg.norm(T, axis=1)[:, None]
    L = np.c_[-T[:, 1], T[:, 0]]                         # left normal: inside on a CCW lap
    d = np.load(npz)
    g = d["cls"] == 2
    G = np.c_[d["e"][g], d["n"][g]]; Gz = d["z"][g]
    tree = cKDTree(G)
    ie = json.loads((RC / "inside_edge.naip.json").read_text(encoding="utf-8"))["rows"]
    EP = np.array([r["edge_en_m"] for r in ie]); elab = np.array([r["label"] for r in ie])
    etree = cKDTree(EP)
    rows = []
    for k in range(len(st)):
        # the measured edge in THIS frame: edge points within 1 m along, median lateral
        cand = etree.query_ball_point(C[k], 40.0)
        edge = None; edge_label = None
        if cand:
            dv = EP[cand] - C[k]
            lat = dv @ L[k]; al = dv @ T[k]
            m = (np.abs(al) <= 1.0) & (lat > 0)
            if m.any():
                edge = float(np.median(lat[m]))
                labs = elab[np.array(cand)[m]]
                edge_label = "seen" if (labs == "seen").mean() >= 0.5 else str(labs[0])
        idx = tree.query_ball_point(C[k], (edge or 30.0) + BEYOND_M + 2.0)
        row = {"s": round(float(st[k]), 1), "half_w_m": round(float(hw[k]), 2),
               "xz": [round(float(C[k, 0]), 3), round(float(C[k, 1]), 3)],
               "left": [round(float(L[k, 0]), 5), round(float(L[k, 1]), 5)], "built_y": round(float(ey[k]), 4),
               "edge_m": None if edge is None else round(edge, 2), "edge_label": edge_label}
        if idx:
            dv = G[idx] - C[k]; lat = dv @ L[k]; al = dv @ T[k]; z = Gz[idx] - ELEV0
            near = np.abs(al) <= ALONG_M
            lat, z = lat[near], z[near]
            lane = line_fit(lat[np.abs(lat) <= LANE_M], z[np.abs(lat) <= LANE_M])
            if lane:
                row["lane"] = {"slope_pct": round(100 * lane["b"], 2), "sd_m": round(lane["sd"], 3), "n": lane["n"],
                               "z0_minus_built_m": round(lane["a"] - float(ey[k]), 3),
                               "a": round(lane["a"], 4), "b": round(lane["b"], 5)}
            if edge is not None and edge > hw[k] + 2 * GAP_M + 1.0:
                m = (lat >= hw[k] + GAP_M) & (lat <= edge - GAP_M)
                ins = line_fit(lat[m], z[m])
                if ins:
                    row["inside"] = {"slope_pct": round(100 * ins["b"], 2), "sd_m": round(ins["sd"], 3), "n": ins["n"],
                                     "width_m": round(edge - hw[k], 2)}
                    if lane:
                        zl = lane["a"] + lane["b"] * hw[k]; zi = ins["a"] + ins["b"] * hw[k]
                        row["inside"]["step_at_built_edge_m"] = round(zi - zl, 3)
                        zle = lane["a"] + lane["b"] * edge; zie = ins["a"] + ins["b"] * edge
                        row["inside"]["below_lane_plane_at_edge_m"] = round(zle - zie, 3)
                m2 = (lat >= -LANE_M) & (lat <= edge - GAP_M)
                kn = knee_fit(lat[m2], z[m2], hw[k] - 3.0, edge - 1.0)
                if kn:
                    row["knee"] = {"at_m": kn["knee_m"], "from_built_edge_m": round(kn["knee_m"] - hw[k], 2),
                                   "slope_in_pct": round(100 * kn["b_in"], 2), "slope_out_pct": round(100 * kn["b_out"], 2),
                                   "sd_m": round(kn["sd"], 3)}
                m3 = (lat >= edge + 1.0) & (lat <= edge + BEYOND_M)
                bey = line_fit(lat[m3], z[m3])
                if bey:
                    row["beyond"] = {"slope_pct": round(100 * bey["b"], 2), "sd_m": round(bey["sd"], 3), "n": bey["n"]}
                    if ins:
                        row["beyond"]["step_at_edge_m"] = round((bey["a"] + bey["b"] * (edge + 1.0))
                                                                - (ins["a"] + ins["b"] * edge), 3)
                    if kn:
                        c0, c1, c2 = kn["c"]
                        z_edge = c0 + c1 * edge + c2 * max(0.0, edge - kn["knee_m"])
                        # the ground 1 m past the edge (the edge strip's grade width) above the knee model's apron at the edge
                        row["beyond"]["lip_step_m"] = round((bey["a"] + bey["b"] * (edge + 1.0)) - z_edge, 3)
        rows.append(row)

    def q(vals, p):
        v = np.array([x for x in vals if x is not None], float)
        return None if not len(v) else round(float(np.percentile(v, p)), 3)

    def summ(sel):
        rr = [r for r in rows if sel(r["s"])]
        g = lambda key, f: [r.get(key, {}).get(f) for r in rr]  # noqa: E731
        return {"stations": len(rr),
                "with_inside_fit": sum("inside" in r for r in rr),
                "lane_slope_pct_p50": q(g("lane", "slope_pct"), 50),
                "lane_z_minus_built_m": {"p10": q(g("lane", "z0_minus_built_m"), 10), "p50": q(g("lane", "z0_minus_built_m"), 50),
                                         "p90": q(g("lane", "z0_minus_built_m"), 90)},
                "inside_width_m_p50": q(g("inside", "width_m"), 50),
                "inside_slope_pct": {"p10": q(g("inside", "slope_pct"), 10), "p50": q(g("inside", "slope_pct"), 50),
                                     "p90": q(g("inside", "slope_pct"), 90)},
                "inside_sd_m_p50": q(g("inside", "sd_m"), 50),
                "step_at_built_edge_m": {"p10": q(g("inside", "step_at_built_edge_m"), 10),
                                         "p50": q(g("inside", "step_at_built_edge_m"), 50),
                                         "p90": q(g("inside", "step_at_built_edge_m"), 90)},
                "knee_from_built_edge_m": {"p10": q(g("knee", "from_built_edge_m"), 10), "p50": q(g("knee", "from_built_edge_m"), 50),
                                           "p90": q(g("knee", "from_built_edge_m"), 90)},
                "knee_slope_out_pct_p50": q(g("knee", "slope_out_pct"), 50),
                "beyond_slope_pct_p50": q(g("beyond", "slope_pct"), 50),
                "beyond_step_at_edge_m_p50": q(g("beyond", "step_at_edge_m"), 50)}
    sections = {"front stretch (s 1497-198)": lambda x: x >= 1497 or x < 198,
                "turns 1-2 (s 198-730)": lambda x: 198 <= x < 730,
                "back stretch (s 730-960)": lambda x: 730 <= x < 960,
                "turns 3-4 (s 960-1497)": lambda x: 960 <= x < 1497,
                "NE diverge (s 947-1037)": lambda x: 947 <= x < 1037,
                "NW merge (s 1310-1380)": lambda x: 1310 <= x < 1380}
    res = {"_doc": __doc__.strip().splitlines()[0], "workshop": str(ws), "lidar": str(npz),
           "lap_m": round(float(lap), 1), "ccw": bool(area > 0), "stations": len(rows),
           "params": {"STEP_M": STEP_M, "ALONG_M": ALONG_M, "LANE_M": LANE_M, "GAP_M": GAP_M, "BEYOND_M": BEYOND_M,
                      "MIN_PTS": MIN_PTS, "ELEV0": ELEV0},
           "sections": {k: summ(v) for k, v in sections.items()}, "rows": rows}
    Path(out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])

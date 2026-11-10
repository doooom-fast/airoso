"""A barrier reader on the cached lidar: a continuity rule, calibrated on the median barrier before it is used outside
(ledger 0080 2a round 6, the SD freeway port; Kevin 2026-11-05: "I just want real").

Neither dataset classes a barrier: the 2014 QL2 EPT and the 2024 D24 tiles put what stands at a shoulder's edge in class 1
(unclassified), with parked vehicles, sign posts and shrubs (round 5's census, `r5/outer_cov.py`). A concrete barrier is
told from those by what it is: a LINE. At every carriageway vertex, on each side, the non-ground returns (not class 2, 7,
17, 18) standing H_LO-H_HI over the pavement's own class-2 height are binned across the edge (BIN_M); the densest bin
(>= N_MIN returns, within ALONG_M of the vertex) is that station's reading (its offset from the built edge and its height,
the bin's p90). A BARRIER is a run of consecutive stations whose readings hold their offset (DOFF_M) and height (DH_M)
station to station for at least RUN_MIN_M: a vehicle is a few metres, a shrub's height wanders.

The median is the calibration: `median_barrier.json`'s runs (NAIP's barrier, round 2-5; the line's stations) are the
truth on the line's and WB's inner sides. The reader is scored there first (precision and recall over the stations the
lidar covers), and its outer-side runs are reported, NOT built, until that score is read. Every threshold here is
invented (fleet/GATES-CHANGELOG.md 2026-11-05 round 6). Reads only the caches; fetches nothing.

    <lidar venv>/python tools/barrier_lidar.py <network-draft dir> --ept-cache <dir> [--laz <dir>] --out <file.json>
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

AIROSO = Path(__file__).resolve().parents[1]
ALONG_M = 2.5        # [invented] returns within this of the vertex, along the carriageway (the 5 m station spacing / 2)
LAT_IN_M = 0.5       # [invented] the search starts this far inside the built edge ...
LAT_OUT_M = 3.0      # [invented] ... and ends this far past it
PAVE_M = 2.0         # [invented] the pavement's class-2 height: returns this far inside the edge
H_LO, H_HI = 0.3, 1.3  # [invented] a return this high over the pavement can be a barrier's (Type 60 stands 0.914 m;
                       # the cache reads the median's at 0.25-0.75 m: returns on its sloped faces)
BIN_M = 0.25         # [invented] the across-edge bin
N_MIN = 2            # [invented] a reading needs this many returns in its bin (the 2014 QL2 cache: ~0.6 per bin)
DOFF_M = 0.5         # [invented] station to station, a barrier's offset holds within this ...
DH_M = 0.3           # [invented] ... and its height within this
RUN_MIN_M = 10.0     # [invented] a barrier is at least this long (3 stations)
# Chosen by a 16-way sweep (H_LO 0.3/0.5, N_MIN 2/3, DOFF_M 0.5/0.75, RUN_MIN_M 10/20) on the line's level median, IN
# SAMPLE (the same truth it is scored on): precision 0.92-1.0 throughout, recall 0.16-0.52; this row 0.93 / 0.51.
SKIP = (2, 7, 17, 18)
STEP_MIN_M = 0.3     # median_ground_blend's / median_barrier_blend's retaining threshold, reused


def load_returns(ept_cache, laz_dir, origin, corr_xz):
    import laspy
    from pyproj import Transformer
    from scipy.spatial import cKDTree
    sys.path.insert(0, str(AIROSO))
    from scripts.geometry.projection import _meters_per_degree
    lon0, lat0, e0 = origin["lon"], origin["lat"], origin["elev_m"]
    mx, my = _meters_per_degree(lat0)
    tree = cKDTree(corr_xz)
    out = []

    def keep(lo, la, z, c):
        x = (lo - lon0) * mx
        zz = (la - lat0) * my
        d, _ = tree.query(np.c_[x, zz], distance_upper_bound=30.0)
        k = np.isfinite(d)
        if k.any():
            out.append(np.c_[x[k], zz[k], z[k] - e0, c[k]])
    if ept_cache:
        inv = Transformer.from_crs(3857, 4326, always_xy=True)
        for f in sorted(glob.glob(str(Path(ept_cache) / "*-*-*-*.laz"))):
            las = laspy.read(f)
            lo, la = inv.transform(np.asarray(las.x), np.asarray(las.y))
            keep(lo, la, np.asarray(las.z), np.asarray(las.classification))
    files = 0
    if laz_dir:
        for f in sorted(Path(laz_dir).glob("*.laz")):
            files += 1
            with laspy.open(f) as fh:
                crs = fh.header.parse_crs()
                h = crs.sub_crs_list[0] if crs.is_compound else crs
                tr = Transformer.from_crs(h, 4326, always_xy=True)
                for ch in fh.chunk_iterator(2_000_000):
                    lo, la = tr.transform(np.asarray(ch.x), np.asarray(ch.y))
                    keep(lo, la, np.asarray(ch.z), np.asarray(ch.classification))
    return (np.concatenate(out) if out else np.zeros((0, 4))), files


def readings(G, gt, P, Wd, sign):
    """Per vertex: None (no return), 'none' (returns, no barrier-like bin) or (offset past the edge, height)."""
    xz = P[:, [0, 2]]
    t = np.zeros_like(xz)
    t[1:-1] = xz[2:] - xz[:-2]
    t[0] = xz[1] - xz[0]
    t[-1] = xz[-1] - xz[-2]
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.stack([-t[:, 1], t[:, 0]], 1) * sign
    res = []
    for i in range(len(P)):
        e = Wd[i] / 2.0
        idx = gt.query_ball_point(xz[i] + n[i] * e, max(ALONG_M, PAVE_M, LAT_OUT_M) + 0.5)
        if not idx:
            res.append(None)
            continue
        q = G[idx]
        v = q[:, :2] - xz[i]
        al, lat = v @ t[i], v @ n[i] - e
        m = np.abs(al) <= ALONG_M
        q, lat = q[m], lat[m]
        pv = q[(q[:, 3] == 2) & (lat <= 0.0) & (lat >= -PAVE_M)]
        if not len(pv):
            res.append(None)
            continue
        zp = float(np.median(pv[:, 2]))
        ng = ~np.isin(q[:, 3], SKIP) & (lat >= -LAT_IN_M) & (lat <= LAT_OUT_M)
        h = q[:, 2] - zp
        c = ng & (h >= H_LO) & (h <= H_HI)
        if c.sum() < N_MIN:
            res.append("none")
            continue
        b = np.floor((lat[c] + LAT_IN_M) / BIN_M).astype(int)
        cnt = np.bincount(b)
        k = int(np.argmax(cnt))
        if cnt[k] < N_MIN:
            res.append("none")
            continue
        sel = (b >= k - 1) & (b <= k + 1)
        res.append((round(-LAT_IN_M + (k + 0.5) * BIN_M, 2), round(float(np.percentile(h[c][sel], 90)), 2)))
    return res


def runs(rd, s):
    """Runs of consecutive readings holding offset and height, at least RUN_MIN_M long: [(i0, i1)]."""
    out, a = [], None
    for i in range(len(rd) + 1):
        ok = i < len(rd) and isinstance(rd[i], tuple)
        if ok and a is not None and (abs(rd[i][0] - rd[i - 1][0]) > DOFF_M or abs(rd[i][1] - rd[i - 1][1]) > DH_M):
            if s[i - 1] - s[a] >= RUN_MIN_M:
                out.append((a, i - 1))
            a = i
            continue
        if ok and a is None:
            a = i
        elif not ok and a is not None:
            if s[i - 1] - s[a] >= RUN_MIN_M:
                out.append((a, i - 1))
            a = None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--ept-cache")
    ap.add_argument("--laz")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = Path(a.draft)
    org = json.loads((D / "network.local.json").read_text(encoding="utf-8"))["origin"]
    L = json.loads((D / "centerline.measured.local.json").read_text(encoding="utf-8"))
    C = json.loads((D / "connectors.measured.local.json").read_text(encoding="utf-8"))["connectors"][0]
    bar = json.loads((D / "median_barrier.json").read_text(encoding="utf-8"))
    pair = json.loads((D / "median_ground.lidar.json").read_text(encoding="utf-8"))["pairs"][C["name"]]["rows"]
    lines = {"line": (np.array(L["points_xyz_m"], float), np.array(L["widths_m"], float)),
             C["name"]: (np.array(C["points_xyz_m"], float), np.array(C["widths_m"], float))}
    corr = np.concatenate([p[:, [0, 2]] for p, _w in lines.values()])
    G, nlaz = load_returns(a.ept_cache, a.laz, org, corr)
    from scipy.spatial import cKDTree
    gt = cKDTree(G[:, :2])
    # truth on the median, in the line's stations: a barrier run covers the station
    sL = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(lines["line"][0][:, [0, 2]], axis=0).T))])
    in_run = lambda s_: any(r["stations_m"][0] <= s_ <= r["stations_m"][1] for r in bar["runs"])
    truth_line = [in_run(float(x)) for x in sL]
    # scored where the two pavements are LEVEL (built heights within STEP_MIN_M, median_ground_blend's): across a step
    # the barrier is the high side's retaining face, read from the low pavement as a 1-4.8 m wall, not a barrier (an
    # outer barrier stands on its own pavement's level)
    paired_line = {r["i"]: r["partner_vertex"] for r in pair if abs(r["built_y"][0] - r["built_y"][1]) <= STEP_MIN_M}
    truth_wb = {}
    for i, pv in paired_line.items():
        truth_wb[pv] = truth_wb.get(pv, False) or truth_line[i]
    rep = {"tool": "tools/barrier_lidar.py", "ledger": "0080 2a round 6",
           "lidar": {"returns": int(len(G)), "d24_tiles": nlaz,
                     "classes": {int(c): int((G[:, 3] == c).sum()) for c in np.unique(G[:, 3])}},
           "params": {"ALONG_M": ALONG_M, "LAT_IN_M": LAT_IN_M, "LAT_OUT_M": LAT_OUT_M, "PAVE_M": PAVE_M,
                      "H_LO": H_LO, "H_HI": H_HI, "BIN_M": BIN_M, "N_MIN": N_MIN, "DOFF_M": DOFF_M, "DH_M": DH_M,
                      "RUN_MIN_M": RUN_MIN_M},
           "_invented": "every params value: fleet/GATES-CHANGELOG.md 2026-11-05 round 6", "calibration": {}, "outer": {}}
    for nm, (P, Wd) in lines.items():
        s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P[:, [0, 2]], axis=0).T))])
        for side, sign in (("inner", 1.0), ("outer", -1.0)):
            rd = readings(G, gt, P, Wd, sign)
            rr = runs(rd, s)
            det = np.zeros(len(P), bool)
            for i0, i1 in rr:
                det[i0:i1 + 1] = True
            cov = np.array([r is not None for r in rd])
            if side == "inner":
                if nm == "line":
                    sc = np.array([i in paired_line for i in range(len(P))])
                    tr = np.array(truth_line)
                else:
                    sc = np.array([i in truth_wb for i in range(len(P))])
                    tr = np.array([truth_wb.get(i, False) for i in range(len(P))])
                m = sc & cov
                tp, fp, fn = int((det & tr & m).sum()), int((det & ~tr & m).sum()), int((~det & tr & m).sum())
                rep["calibration"][nm] = {
                    "paired_stations": int(sc.sum()), "covered": int(m.sum()), "truth_barrier_covered": int((tr & m).sum()),
                    "detected": int((det & m).sum()), "tp": tp, "fp": fp, "fn": fn,
                    "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                    "recall": round(tp / (tp + fn), 3) if tp + fn else None,
                    # the base rate: on the level median nearly every covered station has a barrier, so precision says
                    # little; the stations WITHOUT one are what an outer shoulder mostly is
                    "no_barrier_covered": int((~tr & m).sum()),
                    "false_positive_rate": round(fp / int((~tr & m).sum()), 3) if (~tr & m).sum() else None,
                    "false_positive_s": [round(float(s[i]), 1) for i in np.where(det & ~tr & m)[0]][:40]}
            else:
                rep["outer"][nm] = {"vertices": len(P), "covered": int(cov.sum()), "runs": len(rr),
                                    "run_m": round(float(sum(s[i1] - s[i0] for i0, i1 in rr)), 1),
                                    "stations": int(det.sum()),
                                    "runs_s": [[round(float(s[i0]), 1), round(float(s[i1]), 1),
                                                float(np.median([rd[k][0] for k in range(i0, i1 + 1)])),
                                                float(np.median([rd[k][1] for k in range(i0, i1 + 1)]))] for i0, i1 in rr]}
    Path(a.out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({"calibration": {k: {q: v[q] for q in v if q != "false_positive_s"} for k, v in rep["calibration"].items()},
                      "outer": {k: {q: v[q] for q in v if q != "runs_s"} for k, v in rep["outer"].items()}}))


if __name__ == "__main__":
    main()

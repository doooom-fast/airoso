"""Fetch the nodes plan.json lists into DL/ept-data/, read them, keep the returns within BUF_M of the lane edge, in the
port's local frame (E, N metres about centerline.local.json's origin; Z = the EPT's own height, m), and write OUT.npz
(e, n, z, cls, rn, nr) plus a count summary. Run with -I.

    python -I ept_fetch.py <centerline.local.json> <DL dir> <OUT.npz>
"""
import io, json, math, sys, urllib.request
from pathlib import Path

import laspy
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree

cl_path, DL, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
plan = json.loads((DL / "plan.json").read_text())
BASE = plan["ept"].rsplit("/", 1)[0]
BUF = plan["buffer_m_past_edge"]


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


loc = json.loads(cl_path.read_text()); o = loc["origin"]
P = np.array(loc["points_xyz_m"]); W = np.array(loc["widths_m"])
E, N, HW = [], [], []
for i in range(len(P) - 1):
    a, b = P[i], P[i + 1]; L = math.hypot(b[0] - a[0], b[2] - a[2]); n = max(1, int(L / 1.0))
    for t in np.arange(n) / n:
        E.append(a[0] + (b[0] - a[0]) * t); N.append(a[2] + (b[2] - a[2]) * t); HW.append((W[i] + (W[i + 1] - W[i]) * t) / 2)
E, N, HW = map(np.array, (E, N, HW))
tree = cKDTree(np.c_[E, N])
m_lon, m_lat = mpd(o["lat"])
to_ll = Transformer.from_crs(3857, 4326, always_xy=True)

got_bytes = 0
chunks = []
read_pts = 0
classes_all = {}
(DL / "ept-data").mkdir(exist_ok=True)
for q, (key, npts, size) in enumerate(plan["nodes"]):
    f = DL / "ept-data" / f"{key}.laz"
    if not f.exists() or f.stat().st_size != size:
        for k in range(5):
            try:
                with urllib.request.urlopen(f"{BASE}/ept-data/{key}.laz", timeout=180) as r:
                    data = r.read()
                break
            except Exception as e:  # noqa
                import time; time.sleep(3 * (k + 1))
        f.write_bytes(data); got_bytes += len(data)
    las = laspy.read(str(f))
    read_pts += len(las.points)
    lon, lat = to_ll.transform(np.asarray(las.x), np.asarray(las.y))
    e = (lon - o["lon"]) * m_lon; n = (lat - o["lat"]) * m_lat
    d, j = tree.query(np.c_[e, n], distance_upper_bound=200.0)
    ok = np.isfinite(d)
    keep = np.zeros(len(e), bool)
    keep[ok] = d[ok] <= HW[j[ok]] + BUF
    cls = np.asarray(las.classification)
    for c, cnt in zip(*np.unique(cls[keep], return_counts=True)):
        classes_all[int(c)] = classes_all.get(int(c), 0) + int(cnt)
    chunks.append(np.c_[e[keep], n[keep], np.asarray(las.z)[keep], cls[keep],
                        np.asarray(las.return_number)[keep], np.asarray(las.number_of_returns)[keep], np.asarray(las.intensity)[keep], np.asarray(las.gps_time)[keep]])
    if q % 10 == 0:
        print(f"node {q + 1}/{len(plan['nodes'])} {key}: {len(las.points):,} read, {int(keep.sum()):,} kept", flush=True)
A = np.concatenate(chunks)
np.savez_compressed(OUT, e=A[:, 0].astype(np.float32), n=A[:, 1].astype(np.float32), z=A[:, 2].astype(np.float32),
                    cls=A[:, 3].astype(np.uint8), rn=A[:, 4].astype(np.uint8), nr=A[:, 5].astype(np.uint8), inten=A[:, 6].astype(np.uint16), t=A[:, 7])
tot_disk = sum((DL / "ept-data" / f"{k}.laz").stat().st_size for k, _, _ in plan["nodes"])
summ = {"nodes": len(plan["nodes"]), "laz_bytes_on_disk": tot_disk, "laz_bytes_fetched_this_run": got_bytes,
        "metadata_bytes": plan["metadata_bytes"], "points_read": read_pts, "points_kept_within_buffer": int(len(A)),
        "buffer_m_past_edge": BUF, "classes_kept": classes_all, "z_range": [float(A[:, 2].min()), float(A[:, 2].max())]}
print(json.dumps(summ, indent=1))
(OUT.with_suffix(".summary.json")).write_text(json.dumps(summ, indent=1))

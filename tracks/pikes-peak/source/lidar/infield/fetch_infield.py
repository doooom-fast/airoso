"""Fetch the 2018 USGS 3DEP lidar over PPIR's infield and the oval's inside half (ledger 0085 owed item 2), every class.

Kevin 2026-11-08 (PC session, asked here): picked "Pikes Peak road course", whose option said the 2018 lidar for the
oval's inside and infield would be downloaded first (estimated 30-80 MB). This is that download and nothing else.

    python fetch_infield.py --plan            # walk the EPT hierarchy only: nodes, points, estimated bytes; no point data
    python fetch_infield.py --out DIR         # download the nodes' LAZ to DIR/ept-data (cached), write DIR/infield.npz

The box is the road course's extent (RC-D in ../../road-course/route_from_maps.naip.json, E -224..240, N -292..260 m
about the port's origin) plus PAD_M on every side, so the wall and the ground outside it are in too. Points are kept
in the box only; E/N are the port's local metres (x = E, z = N in the build), z is the EPT's own height (NAVD88 m).
Stops before downloading if the plan exceeds CAP_MB (twice the high estimate): that is a new size to ask Kevin about.
Needs numpy, laspy[lazrs], pyproj (D:/k10-scratch/lidar-venv on the PC).
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
from scripts.tls import https_context  # noqa: E402

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_Eastern_ElPaso_2018/ept.json"
BOX_E = (-224.0, 240.0)       # RC-D's extent (measured line), m
BOX_N = (-292.0, 260.0)
PAD_M = 60.0                  # [invented] past the wall and its berm; the course's own pieces are all inside RC-D's box
CAP_MB = 160.0                # twice the 80 MB high estimate given to Kevin
BYTES_PER_POINT = 9.0         # [invented] LAZ 1.4 pdrf 6-7 typically 7-11 B/pt; only for the plan's estimate


def mpd(lat0):
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


def origin():
    loc = json.loads((REPO / "tracks/pikes-peak/data/centerline.local.json").read_text(encoding="utf-8"))
    return loc["origin"]["lon"], loc["origin"]["lat"]


def get(url, tries=4):
    for t in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if t == tries - 1:
                raise
            print(f"  retry {t + 1} {url}: {e}", flush=True)
            time.sleep(2 + 3 * t)


def box_merc():
    from pyproj import Transformer
    lon0, lat0 = origin()
    m_lon, m_lat = mpd(lat0)
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    e = [BOX_E[0] - PAD_M, BOX_E[1] + PAD_M]
    n = [BOX_N[0] - PAD_M, BOX_N[1] + PAD_M]
    xs, ys = [], []
    for ee in e:
        for nn in n:
            x, y = to_merc.transform(lon0 + ee / m_lon, lat0 + nn / m_lat)
            xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def plan():
    ept = json.loads(get(EPT))
    if ept["srs"].get("horizontal") != "3857":
        raise SystemExit(f"{EPT} is not EPSG:3857")
    base = EPT.rsplit("/", 1)[0]
    b = ept["bounds"]
    bx0, by0, bx1, by1 = box_merc()
    hier_files = {}

    def hier(key):
        if key not in hier_files:
            hier_files[key] = json.loads(get(f"{base}/ept-hierarchy/{key}.json"))
        return hier_files[key]
    nodes = []

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        if h[k] == -1:
            h = hier(k)
        sz = (b[3] - b[0]) / 2 ** d
        x0, y0 = b[0] + x * sz, b[1] + y * sz
        if x0 > bx1 or x0 + sz < bx0 or y0 > by1 or y0 + sz < by0:
            return
        if h[k] > 0:
            nodes.append((k, int(h[k]), sz))
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, hier("0-0-0-0"))
    pts = sum(n[1] for n in nodes)
    return ept, base, nodes, pts, (bx0, by0, bx1, by1), len(hier_files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    ept, base, nodes, pts, bm, nh = plan()
    est = pts * BYTES_PER_POINT / 1e6
    depths = sorted({int(k.split("-")[0]) for k, _, _ in nodes})
    print(f"[fetch_infield] {EPT}")
    print(f"[fetch_infield] box E {BOX_E[0] - PAD_M:.0f}..{BOX_E[1] + PAD_M:.0f} N {BOX_N[0] - PAD_M:.0f}..{BOX_N[1] + PAD_M:.0f} m"
          f" (merc {bm[0]:.1f},{bm[1]:.1f} .. {bm[2]:.1f},{bm[3]:.1f}); hierarchy files read {nh}")
    print(f"[fetch_infield] {len(nodes)} nodes at depths {depths[0]}-{depths[-1]}, {pts:,} points in them, "
          f"~{est:.0f} MB at {BYTES_PER_POINT} B/pt [estimate]")
    for k, c, sz in sorted(nodes, key=lambda n: -n[1])[:6]:
        print(f"    {k}: {c:,} pts, node {sz:.0f} m")
    if a.plan or not a.out:
        return
    if est > CAP_MB:
        raise SystemExit(f"[fetch_infield] plan ~{est:.0f} MB > cap {CAP_MB:.0f} MB: ask Kevin before downloading")
    import numpy as np
    import laspy
    from pyproj import Transformer
    out = Path(a.out); (out / "ept-data").mkdir(parents=True, exist_ok=True)
    lon0, lat0 = origin(); m_lon, m_lat = mpd(lat0)
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    got = 0; keep = {f: [] for f in ("e", "n", "z", "cls", "inten", "ret", "nret")}
    t0 = time.time()
    for q, (k, c, sz) in enumerate(nodes):
        f = out / "ept-data" / f"{k}.laz"
        if not f.exists():
            raw = get(f"{base}/ept-data/{k}.laz")
            f.write_bytes(raw)
            if got + len(raw) > CAP_MB * 1e6:
                raise SystemExit(f"[fetch_infield] downloaded {(got + len(raw)) / 1e6:.0f} MB > cap: stopped")
        got += f.stat().st_size
        las = laspy.read(io.BytesIO(f.read_bytes()))
        x = np.asarray(las.x); y = np.asarray(las.y)
        m = (x >= bm[0]) & (x <= bm[2]) & (y >= bm[1]) & (y <= bm[3])
        if m.any():
            lon, lat = to_ll.transform(x[m], y[m])
            keep["e"].append((lon - lon0) * m_lon); keep["n"].append((lat - lat0) * m_lat)
            keep["z"].append(np.asarray(las.z)[m]); keep["cls"].append(np.asarray(las.classification)[m])
            keep["inten"].append(np.asarray(las.intensity)[m])
            keep["ret"].append(np.asarray(las.return_number)[m]); keep["nret"].append(np.asarray(las.number_of_returns)[m])
        if q % 10 == 0 or q == len(nodes) - 1:
            print(f"  node {q + 1}/{len(nodes)} {k}: {got / 1e6:.1f} MB so far, {time.time() - t0:.0f} s", flush=True)
    arr = {k: np.concatenate(v) for k, v in keep.items()}
    np.savez_compressed(out / "infield.npz", e=arr["e"].astype(np.float64), n=arr["n"].astype(np.float64),
                        z=arr["z"].astype(np.float64), cls=arr["cls"].astype(np.uint8), inten=arr["inten"].astype(np.uint16),
                        ret=arr["ret"].astype(np.uint8), nret=arr["nret"].astype(np.uint8))
    cls, cnt = np.unique(arr["cls"], return_counts=True)
    area = (BOX_E[1] - BOX_E[0] + 2 * PAD_M) * (BOX_N[1] - BOX_N[0] + 2 * PAD_M)
    summ = {"ept": EPT, "box_local_m": {"e": [BOX_E[0] - PAD_M, BOX_E[1] + PAD_M], "n": [BOX_N[0] - PAD_M, BOX_N[1] + PAD_M]},
            "nodes": len(nodes), "downloaded_bytes": got, "points_in_box": int(len(arr["z"])),
            "density_pts_m2": round(len(arr["z"]) / area, 2),
            "classes": {int(c): int(n) for c, n in zip(cls, cnt)},
            "ground_density_pts_m2": round(float((arr["cls"] == 2).sum()) / area, 2)}
    (out / "infield.summary.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()

"""The ground at a stage's turns from 3DEP lidar: a 0.5 m class-2 grid per turn (ledger 0078 round 11; run on the PC).

tools/switchback_measure.py reads a switchback's graded platform from 3DEP's 1 m DEM. Two turns' inside edges the DEM
does not bound with a face (Dragon Tail switchback 3, s ~7,453; Under the Dragon's Douglas Creek switchback, s
~2,482-2,500). USGS's lidar covers both stages (CO_NWCO_1_2020's EPT). This script reads that point cloud's ground
class (2) within HALF_M of each named turn's apex and writes, per turn, the port's data/lidar/<track>_<id>.npz: the
mean class-2 height of every 0.5 m cell (NaN where no ground point fell), in the port's local frame (x east, z north,
metres about centerline.local.json's origin; row 0 = south), with the grid's origin and the point count.
tools/switchback_measure.py then measures those turns' bench edges on it instead of the DEM.

Needs laspy (with a LAZ backend: lazrs or laszip), pyproj and numpy: the PC's environment (it reads LAZ for the
Lariat's pads, tools/draft_pad_outline.py). The Mac has no LAZ reader and installs nothing.

    python tools/lidar_turns.py tracks/<port> --turns S5,S4 [--ept <ept.json url>] [--half 60]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import urllib.request
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_NWCO_1_2020/ept.json"
HALF_M = 60.0
CELL_M = 0.5


def _get(url):
    from scripts.tls import https_context
    for k in range(6):
        try:
            with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
                return r.read()
        except Exception:                                   # noqa: BLE001
            import time
            time.sleep(4 * (k + 1))
    raise SystemExit(f"[lidar_turns] refused: {url}")


def ground_points(ept_url, origin, cx, cz, half):
    """class-2 (E, N, Z) in the box, local metres (the EPT octree walked to every node over the box)"""
    import laspy
    import numpy as np
    from pyproj import Transformer
    from scripts.geometry.projection import _meters_per_degree
    m_lon, m_lat = _meters_per_degree(float(origin["lat"]))
    ept = json.loads(_get(ept_url))
    base = ept_url.rsplit("/", 1)[0]
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    x0, y0 = to_merc.transform(origin["lon"] + (cx - half) / m_lon, origin["lat"] + (cz - half) / m_lat)
    x1, y1 = to_merc.transform(origin["lon"] + (cx + half) / m_lon, origin["lat"] + (cz + half) / m_lat)
    b = ept["bounds"]
    hier = {}

    def h_of(key):
        if key not in hier:
            hier[key] = json.loads(_get(f"{base}/ept-hierarchy/{key}.json"))
        return hier[key]
    keys = []

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        if h[k] == -1:
            h = h_of(k)
        sz = (b[3] - b[0]) / 2 ** d
        bx, by = b[0] + x * sz, b[1] + y * sz
        if bx > x1 or bx + sz < x0 or by > y1 or by + sz < y0:
            return
        if h[k] > 0:
            keys.append(k)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, h_of("0-0-0-0"))
    E, N, Z = [], [], []
    for k in keys:
        las = laspy.read(io.BytesIO(_get(f"{base}/ept-data/{k}.laz")))
        m = (np.asarray(las.classification) == 2) & (las.x >= x0) & (las.x <= x1) & (las.y >= y0) & (las.y <= y1)
        if not m.any():
            continue
        lon, lat = to_ll.transform(np.asarray(las.x)[m], np.asarray(las.y)[m])
        E.append((lon - origin["lon"]) * m_lon)
        N.append((lat - origin["lat"]) * m_lat)
        Z.append(np.asarray(las.z)[m])
    return (np.concatenate(E), np.concatenate(N), np.concatenate(Z)) if E else (None, None, None)


def main(argv=None):
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("--turns", required=True)
    ap.add_argument("--ept", default=EPT)
    ap.add_argument("--half", type=float, default=HALF_M)
    a = ap.parse_args(argv)
    port = Path(a.port)
    cfg = json.loads((port / "track.config.json").read_text(encoding="utf-8"))
    src = AIROSO / "tracks" / cfg["lm_intake"]["source_track"]
    local = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    swb = {c["id"]: c for c in json.loads((port / "data" / "switchbacks.json").read_text(encoding="utf-8"))["corners"]}
    P = local["points_xyz_m"]
    st = [0.0]
    for p, q in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(q[0] - p[0], q[2] - p[2]))
    out_dir = port / "data" / "lidar"
    out_dir.mkdir(parents=True, exist_ok=True)
    for tid in a.turns.split(","):
        c = swb[tid]
        i = min(range(len(P)), key=lambda k: abs(st[k] - c["st_m"]))
        cx, cz = P[i][0], P[i][2]
        E, N, Z = ground_points(a.ept, local["origin"], cx, cz, a.half)
        if E is None:
            print(f"[lidar_turns] {tid}: no class-2 points in the box")
            continue
        n = int(round(2 * a.half / CELL_M))
        gx0, gz0 = cx - a.half, cz - a.half
        ix = np.clip(((E - gx0) / CELL_M).astype(int), 0, n - 1)
        iz = np.clip(((N - gz0) / CELL_M).astype(int), 0, n - 1)
        s = np.zeros((n, n)); c_ = np.zeros((n, n))
        np.add.at(s, (iz, ix), Z - float(local["origin"]["elev_m"]))
        np.add.at(c_, (iz, ix), 1)
        grid = np.where(c_ > 0, s / np.maximum(c_, 1), np.nan).astype(np.float32)
        f = out_dir / f"{cfg['lm_intake']['source_track']}_{tid}.npz"
        np.savez_compressed(f, ground=grid, x0=gx0, z0=gz0, cell_m=CELL_M, elev0=float(local["origin"]["elev_m"]),
                            points=len(Z), ept=a.ept, st_m=c["st_m"])
        print(f"[lidar_turns] {tid} s {c['st_m']:.0f}: {len(Z):,} class-2 points -> {f} ({n}x{n} cells of {CELL_M} m, "
              f"{int(np.isfinite(grid).sum()):,} with ground; {f.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

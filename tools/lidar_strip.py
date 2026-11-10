"""Every lidar return along a stretch of a circuit's lane edge, gridded by station and offset (ledger 0081 round 2; PC).

NAIP at 0.3 m cannot decide two things on the circuits: Grand Junction's faint light blocks along the right edge near
s ~200 and ~1,000 (faded kerbs, or not), and what a run-off past an edge is made of (gravel or ground) where that decides a
build. 3DEP's point clouds carry an INTENSITY per return (paint and fresh gravel return brighter than asphalt and dirt) and
a class (2 = ground). This reads every return within the box of each named span from the dataset's public EPT and grids
it on the live track's own line (data/gate_centerline.json: station s along it, offset o metres OUTWARD past the named
lane edge, - = over the lane), CELL_M cells, o from O_LO_M to O_HI_M. Per span it writes
<track>/source/lidar/strip/<SIDE><s0>-<s1>.npz: n (returns per cell), i_mean / i_p90 (intensity), z_mean, ground_share
(class 2 / all), plus s / o axes, the EPT and the point count; and prints per 0.5 m offset column the median intensity,
so a kerb reads as a bright band at the lane edge that alternates along s, and a gravel trap as a bright band past it.
It measures nothing by itself: the npz is the record, read beside the aerial.

Needs laspy with lazrs (or laszip), pyproj and numpy: the PC's environment (tools/lidar_turns.py's). The Mac has no LAZ
reader; this has not been run.

    python tools/lidar_strip.py tracks/grand-junction --spans R:170-230,R:970-1030 \
        --ept https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_CO_MesaCo_QL2_2015_LAS_2017/ept.json
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
sys.path.insert(0, str(AIROSO / "tools"))

CELL_M = 0.5          # QL2 is 2-8 returns / m2: a 0.5 m cell holds ~0.5-2
O_LO_M, O_HI_M = -4.0, 16.0   # the band read: 4 m over the lane (a kerb inside the edge) to 16 m past it (a run-off)
PAD_M = 2.0           # the box round the span reaches this far past its ends


def line_frame(tdir):
    line = json.loads((tdir / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
    P, W = line["points_xyz_m"], line["widths_m"]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return P, W, st


def station_offset(x, z, P, W, st, side, s_lo, s_hi):
    """(s, o) of a local point on the line between s_lo and s_hi: s along it, o outward past the side's lane edge"""
    best = None
    j0 = max(0, bisect.bisect_left(st, s_lo) - 1)
    j1 = min(len(P) - 1, bisect.bisect_right(st, s_hi) + 1)
    for j in range(j0, j1):
        ax, az, bx, bz = P[j][0], P[j][2], P[j + 1][0], P[j + 1][2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        d2 = (x - ax - dx * t) ** 2 + (z - az - dz * t) ** 2
        if best is None or d2 < best[0]:
            L = math.sqrt(L2)
            lat = ((x - ax) * -dz + (z - az) * dx) / L      # + = left of travel
            best = (d2, st[j] + t * L, side * lat - (W[j] + (W[j + 1] - W[j]) * t) / 2)
    return best[1], best[2]


def returns(ept_url, origin, box):
    """every return in the local box (x0, z0, x1, z1): local E, N, Z, intensity, class (the EPT octree walked as
    tools/lidar_turns.py walks it)"""
    import laspy
    import numpy as np
    from pyproj import Transformer
    from scripts.geometry.projection import _meters_per_degree
    from lidar_turns import _get
    m_lon, m_lat = _meters_per_degree(float(origin["lat"]))
    ept = json.loads(_get(ept_url))
    base = ept_url.rsplit("/", 1)[0]
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    x0, y0 = to_merc.transform(origin["lon"] + box[0] / m_lon, origin["lat"] + box[1] / m_lat)
    x1, y1 = to_merc.transform(origin["lon"] + box[2] / m_lon, origin["lat"] + box[3] / m_lat)
    b = ept["bounds"]
    hier, keys = {}, []

    def h_of(key):
        if key not in hier:
            hier[key] = json.loads(_get(f"{base}/ept-hierarchy/{key}.json"))
        return hier[key]

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
    out = [[], [], [], [], []]
    for k in keys:
        las = laspy.read(io.BytesIO(_get(f"{base}/ept-data/{k}.laz")))
        m = (las.x >= x0) & (las.x <= x1) & (las.y >= y0) & (las.y <= y1)
        if not m.any():
            continue
        lon, lat = to_ll.transform(np.asarray(las.x)[m], np.asarray(las.y)[m])
        out[0].append((lon - origin["lon"]) * m_lon)
        out[1].append((lat - origin["lat"]) * m_lat)
        out[2].append(np.asarray(las.z)[m])
        out[3].append(np.asarray(las.intensity)[m])
        out[4].append(np.asarray(las.classification)[m])
    return [np.concatenate(v) for v in out] if out[0] else None


def main(argv=None):
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("track")
    ap.add_argument("--spans", required=True, help="L:s0-s1,R:s0-s1 (stations on the track's data/gate_centerline.json)")
    ap.add_argument("--ept", required=True)
    a = ap.parse_args(argv)
    tdir = Path(a.track)
    origin = json.loads((tdir / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    P, W, st = line_frame(tdir)
    outdir = tdir / "source" / "lidar" / "strip"
    outdir.mkdir(parents=True, exist_ok=True)
    for spec in a.spans.split(","):
        sd, rng = spec.split(":")
        side = 1 if sd.upper().startswith("L") else -1
        s0, s1 = (float(v) for v in rng.split("-"))
        xs, zs = [], []
        s = s0 - PAD_M
        while s <= s1 + PAD_M:
            j = min(len(P) - 2, max(0, bisect.bisect_right(st, s) - 1))
            for o in (O_LO_M, O_HI_M):
                for jj in (j, j + 1):
                    xs.append(P[jj][0]); zs.append(P[jj][2])
            s += 1.0
        R = O_HI_M + max(W) / 2 + PAD_M
        box = (min(xs) - R, min(zs) - R, max(xs) + R, max(zs) + R)
        got = returns(a.ept, origin, box)
        if got is None:
            print(f"[lidar_strip] {spec}: no returns in the box")
            continue
        E, N, Z, I, C = got
        ns, no = int((s1 - s0) / CELL_M) + 1, int((O_HI_M - O_LO_M) / CELL_M) + 1
        n = np.zeros((ns, no)); isum = np.zeros((ns, no)); zsum = np.zeros((ns, no)); g = np.zeros((ns, no))
        cells = {}
        for x, z, h, i, c in zip(E, N, Z, I, C):
            s_, o_ = station_offset(x, z, P, W, st, side, s0 - PAD_M, s1 + PAD_M)
            if not (s0 <= s_ <= s1 and O_LO_M <= o_ <= O_HI_M):
                continue
            r, q = int((s_ - s0) / CELL_M), int((o_ - O_LO_M) / CELL_M)
            n[r, q] += 1; isum[r, q] += i; zsum[r, q] += h; g[r, q] += (c == 2)
            cells.setdefault((r, q), []).append(i)
        with np.errstate(invalid="ignore", divide="ignore"):
            i_mean, z_mean, gshare = isum / n, zsum / n, g / n
        i_p90 = np.full((ns, no), np.nan)
        for (r, q), v in cells.items():
            i_p90[r, q] = float(np.percentile(v, 90))
        f = outdir / f"{sd.upper()}{s0:.0f}-{s1:.0f}.npz"
        np.savez_compressed(f, n=n, i_mean=i_mean, i_p90=i_p90, z_mean=z_mean, ground_share=gshare,
                            s=s0 + CELL_M * np.arange(ns), o=O_LO_M + CELL_M * np.arange(no), ept=a.ept,
                            points=int(n.sum()))
        col = np.nanmedian(i_mean, axis=0)
        print(f"[lidar_strip] {spec}: {int(n.sum())} returns in the band, {int((n > 0).sum())} / {n.size} cells, "
              f"{f.stat().st_size / 1e6:.2f} MB -> {f}")
        print("[lidar_strip]   median intensity by offset: " +
              " ".join(f"{O_LO_M + CELL_M * q:+.1f}:{v:.0f}" for q, v in enumerate(col) if not np.isnan(v)))


if __name__ == "__main__":
    main()

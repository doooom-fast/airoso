"""Measure a side street's real road surface height off USGS 3DEP source lidar, point by point (ledger 0079 round H).

Kevin, 2026-11-03: "I just want real". The free roam's streets take their heights from the source track's 3DEP grid (40 m,
read at 20 m): it cannot hold an embankment, a ramp or a bridge. Measured on Sand Creek (round H):
  - grid_tertiary_5 crosses Sand Creek on a 60 m bridge (lidar class 17 at 22.2 m); the grid dropped the street 5 m into
    the creek bed, and its mouth on the lap read a 3.9 %/m grade change (verify_mouths APPROACH);
  - grid_primary_84 / grid_primary_78 climb onto a bridge over the interstate (class 17 at 29.3 m); the grid held them up
    to 4.25 m low, with a 2.8 m step at their own mouth (8.6 %/m).

Method, for each named connector of the source track's data/connectors.local.json, at each of its points: the median
height of the ground (class 2) and bridge deck (class 17) returns within RADIUS_M of the point. A point with fewer than
MIN_RETURNS keeps the 3DEP height moved by the lidar - 3DEP offset interpolated between its measured neighbours (none
on the Sand Creek streets measured). Heights in the track's local frame (z - origin.elev_m), the frame the 3DEP heights
are in. Nothing is smoothed here: the assembler smooths every connector's heights as it always has.

Writes <out> (default <project>/source/connector_profiles.lidar.json): {connector: {"y": [...], "xz": [[x, z]...],
"returns": [...], "bridge_returns": [...]}}; tools/lm_engine_intake.py applies it (lm_intake.connector_profiles), checking
every point's plan position. Fetching needs numpy, laspy[lazrs], pyproj (the Mac: a venv with them; the PC's environment).

    python tools/lidar_connector_profile.py <project-dir> <connector>[,<connector>...] [--ept URL] [--out PATH]
                                            [--cache DIR]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

EPT_DEFAULT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json"
RADIUS_M = 1.0        # [invented] returns within this of the street point (3-6 returns/m2 here: 10-25 per point)
MIN_RETURNS = 3       # [invented] fewer than this is no reading
TILE_M = 100.0        # fetch tiles (a fetch window is the tile + 5 m)
CLASSES = (2, 17)     # ground, bridge deck


def _get(url):
    from scripts.tls import https_context
    with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
        return r.read()


class Ept:
    def __init__(self, url, origin, cache: Path):
        self.url, self.base = url, url.rsplit("/", 1)[0]
        self.o = origin
        self.m_lon, self.m_lat = _meters_per_degree(origin["lat"])
        self.cache = cache
        self.meta = None
        self.hier = {}

    def tile(self, i, j):
        import numpy as np
        p = self.cache / f"tile_{i}_{j}.npz"
        if p.exists():
            d = np.load(p)
            return d["E"], d["N"], d["Z"], d["C"]
        import laspy
        from pyproj import Transformer
        if self.meta is None:
            self.meta = json.loads(_get(self.url))
            if self.meta["srs"].get("horizontal") != "3857":
                raise SystemExit(f"lidar_connector_profile: {self.url} is not EPSG:3857")
        b = self.meta["bounds"]
        to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
        to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
        e0, n0 = i * TILE_M - 5.0, j * TILE_M - 5.0
        e1, n1 = e0 + TILE_M + 10.0, n0 + TILE_M + 10.0
        x0, y0 = to_merc.transform(self.o["lon"] + e0 / self.m_lon, self.o["lat"] + n0 / self.m_lat)
        x1, y1 = to_merc.transform(self.o["lon"] + e1 / self.m_lon, self.o["lat"] + n1 / self.m_lat)

        def h_of(k):
            if k not in self.hier:
                self.hier[k] = json.loads(_get(f"{self.base}/ept-hierarchy/{k}.json"))
            return self.hier[k]
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
        acc = [[], [], [], []]
        for k in keys:
            las = laspy.read(io.BytesIO(_get(f"{self.base}/ept-data/{k}.laz")))
            cl = np.asarray(las.classification)
            m = np.isin(cl, CLASSES) & (las.x >= x0) & (las.x <= x1) & (las.y >= y0) & (las.y <= y1)
            if not m.any():
                continue
            lon, lat = to_ll.transform(np.asarray(las.x)[m], np.asarray(las.y)[m])
            acc[0].append((lon - self.o["lon"]) * self.m_lon)
            acc[1].append((lat - self.o["lat"]) * self.m_lat)
            acc[2].append(np.asarray(las.z)[m] - float(self.o["elev_m"]))
            acc[3].append(cl[m])
        E, N, Z, C = (np.concatenate(a) if a else np.zeros(0) for a in acc)
        self.cache.mkdir(parents=True, exist_ok=True)
        np.savez(p, E=E, N=N, Z=Z, C=C)
        return E, N, Z, C


def profile(ept: Ept, pts):
    """[(y or None, returns, bridge returns)] at each (x, y, z) point"""
    import numpy as np
    need = sorted({(int(math.floor(p[0] / TILE_M)), int(math.floor(p[2] / TILE_M))) for p in pts})
    tiles = {t: ept.tile(*t) for t in need}
    out = []
    for p in pts:
        E, N, Z, C = tiles[(int(math.floor(p[0] / TILE_M)), int(math.floor(p[2] / TILE_M)))]
        m = (E - p[0]) ** 2 + (N - p[2]) ** 2 <= RADIUS_M * RADIUS_M
        n = int(m.sum())
        out.append((round(float(np.median(Z[m])), 3) if n >= MIN_RETURNS else None, n, int((C[m] == 17).sum())))
    return out


def fill(pts, meas):
    """y per point: the measured one, or the 3DEP height moved by the offset interpolated between measured neighbours"""
    k = [i for i, m in enumerate(meas) if m[0] is not None]
    if not k:
        raise SystemExit("lidar_connector_profile: no point of the street has a lidar reading")
    ys = []
    for i, p in enumerate(pts):
        if meas[i][0] is not None:
            ys.append(meas[i][0])
            continue
        a = max((j for j in k if j < i), default=None)
        b = min((j for j in k if j > i), default=None)
        da = meas[a][0] - pts[a][1] if a is not None else None
        db = meas[b][0] - pts[b][1] if b is not None else None
        if da is None or db is None:
            off = da if db is None else db
        else:
            off = da + (db - da) * (i - a) / (b - a)
        ys.append(round(p[1] + off, 3))
    return ys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("connectors")
    ap.add_argument("--ept", default=EPT_DEFAULT)
    ap.add_argument("--out")
    ap.add_argument("--cache")
    a = ap.parse_args(argv)
    proj = Path(a.project).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    src = proj.parent / str((cfg.get("lm_intake") or {}).get("source_track") or proj.name)
    conns = {c["name"]: c for c in json.loads((src / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]}
    origin = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    cache = Path(a.cache) if a.cache else Path(tempfile.mkdtemp(prefix="lidar_conn_"))
    ept = Ept(a.ept, origin, cache)
    out_p = Path(a.out) if a.out else proj / "source" / "connector_profiles.lidar.json"
    doc = json.loads(out_p.read_text(encoding="utf-8")) if out_p.exists() else {}
    res = doc.get("connectors", {})
    for name in a.connectors.split(","):
        if name not in conns:
            raise SystemExit(f"lidar_connector_profile: {name} is not a connector of {src}")
        pts = conns[name]["points_xyz_m"]
        meas = profile(ept, pts)
        ys = fill(pts, meas)
        d = [y - p[1] for y, p in zip(ys, pts)]
        res[name] = {"xz": [[round(p[0], 3), round(p[2], 3)] for p in pts], "y": ys,
                     "returns": [m[1] for m in meas], "bridge_returns": [m[2] for m in meas]}
        print(f"[lidar_profile] {name}: {len(pts)} points, {sum(m[0] is not None for m in meas)} measured, "
              f"{sum(m[2] > 0 for m in meas)} on a bridge deck; lidar - 3DEP {min(d):+.2f} .. {max(d):+.2f} m")
    out_p.write_text(json.dumps({
        "_doc": "tools/lidar_connector_profile.py (ledger 0079 round H): each street's road surface height at each of the "
                "source track's connector points, the median of the lidar ground (class 2) and bridge deck (class 17) "
                f"returns within {RADIUS_M} m [invented radius] (min {MIN_RETURNS} returns), local frame (z - origin.elev_m); "
                "applied by tools/lm_engine_intake.py (lm_intake.connector_profiles)",
        "ept": a.ept, "radius_m": RADIUS_M, "min_returns": MIN_RETURNS, "connectors": res}, indent=None), encoding="utf-8")
    print(f"[lidar_profile] -> {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

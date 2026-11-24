"""THE REAL LIGHT POLES ALONG COLORADO BLVD, OFF THE 2020 LIDAR AT ITS FULL CLASS RANGE (Sand Creek round 0.2.13; data
only, nothing reads it).

Kevin: "I just want real". NAIP 2023 (0.46 m/px) shows a pole only as its shadow, so the lamps 0.2.11 built on Colorado
(data/lights.local.json, alternating at u +-11.05) are not checked against a real pole. This reads USGS CO_DRCOG_2_2020
itself, every class (the PC's tile cache keeps only 2 and 17), over the lap's Colorado stations s 0-415 (the lap's s:
plan metres along data/centerline.local.json from v0) and u -30..+30 (+u = left of the lap's travel, its west side here),
in the lap's frame (tools/lidar_connector_profile's: ENU metres about centerline.local.json's origin, WGS84 series;
heights = las z - origin.elev_m).

Every chosen constant is marked [invented] (or [sampling]). The method:
  * THE POINTS: every EPT node whose box comes within CORR_M of the lap's line over s S_RANGE (+-PAD_S), read whole
    from local copies of earlier fetches (--mirror) or fetched (--dl, md5-indexed); each point kept with its class,
    return number / count and intensity when it lies within CORR_M of the line in that s range.
  * THE GROUND: the class-2 returns' median per DTM_M cell, holes filled from the nearest read cell; a point's height
    over ground (HAG) is its height minus its cell's ground.
  * THE OBJECTS: every non-ground return (any class but 2 ground, 7 low noise, 9 water, 17 bridge deck, 18 high noise)
    HAG_MIN or more over the ground, joined in plan when within LINK_M: one object per connected group.
  * EACH OBJECT'S SHAPE: its top (highest return, HAG), the plan spread of its returns (principal axes: length and
    width), the share of its returns that are not the pulse's last (a canopy lets pulses through; a steel pole does not),
    its SHAFT (returns HAG_MIN .. top - TOP_BAND_M: under a cobra head only the pole itself) and its TOP BAND (top -
    TOP_BAND_M .. top: the head and arm).
  * KINDS (rules, all [invented]):
      wire    long and thin in plan (length WIRE_LEN_M or more, width WIRE_W_M or less), over WIRE_HAG_M: an overhead
              line, or a chain of them;
      tree    wide (plan width TREE_W_M or more) and dense (TREE_N or more returns), or a canopy (non-last share
              TREE_NONLAST or more over TREE_W_M / 2);
      pole    narrow (width POLE_W_M or less, every return within POLE_REACH_M of the base in plan) and tall (top HAG
              POLE_TOP_M[0] .. POLE_TOP_M[1]), not a tree:
                light pole      a shaft (SHAFT_MIN returns or more under the top band, spanning SHAFT_SPAN_M or
                                more), top under UTIL_TOP_M and no wire ending within WIRE_NEAR_M of its top;
                line pole       a shaft, and a top UTIL_TOP_M or more or a wire ending at its top (named: which);
                head / arm only no shaft: a narrow elevated object with nothing under it (a light's head and arm, a
                                sign's or a billboard's top); no arm direction is claimed;
      other   the rest (buildings, signs, signal mast arms, vehicles, walls), counted, not listed.
  * A POLE'S BASE: the plan median of its shaft returns; with no shaft, the end of its top band farther from the road
    (where a cobra head's pole would stand: an assumption, so marked). Its arm: base to the top band's farthest
    return, when ARM_MIN_M or longer; toward the road when it points from the base toward ROAD_U (the road between its
    measured outer curbs, roads_lidar_g10/lap_colorado_quebec.lidar.json on its own branch: u -5.25 .. +20.1).
  * CONFIDENCE: high = a shaft and a top band, no tree or wire within CLEAR_M; medium = a shaft; low = no shaft.
  * THE WINDOW'S EVIDENCE: the count of non-ground returns 3 .. 10 m or more over the ground inside s S_RANGE, |u| <=
    U_HALF, and the window's returns per m2: a pole's head and arm at 6-11 m read 12-80 returns where one stands
    (the objects found just west of the window), so an empty count is a measurement, not a gap.

THE LAMPS: data/lights.local.json lamp_bases_xz, the six on this stretch (s 0-415, |u| < 30): each to the nearest real
pole (light or line) in plan, its distance, or "no pole within LAMP_NEAR_M".

    python -I colorado_poles_g10.py fetch   --repo R --dl DIR [--mirror DIR ...] [--plan plan.json]
    python -I colorado_poles_g10.py measure --repo R --dl DIR [--mirror DIR ...] --out JSON
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EPT_URL = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json"
EPT_BASE = EPT_URL.rsplit("/", 1)[0]

S_RANGE = (0.0, 415.0)   # the task's stations: the lap's s on Colorado
U_HALF = 30.0            # the task's lateral reach
CORR_M = 50.0            # [invented] points kept within this of the lap's line: U_HALF, and the pole line standing
                         # just past it on the west (u +35, found in a first pass at 36 m), listed apart
PAD_S = 10.0             # [invented] ... and this far past each end of S_RANGE
DTM_M = 1.0              # [sampling] the ground grid
HAG_MIN = 2.0            # [invented] an object's return stands this far over the ground or more (a car is lower)
LINK_M = 1.2             # [invented] two returns this close in plan are one object
TOP_BAND_M = 2.0         # [invented] the head and arm: returns within this of the object's top
WIRE_LEN_M = 12.0        # [invented]
WIRE_W_M = 0.6           # [invented] (the plan width's standard deviation)
WIRE_HAG_M = 4.0         # [invented]
TREE_W_M = 0.9           # [invented] (plan width's standard deviation, metres)
TREE_N = 25              # [invented]
TREE_NONLAST = 0.3       # [invented]
POLE_W_M = 0.6           # [invented] (plan width's standard deviation)
POLE_REACH_M = 5.0       # [invented] a cobra head's arm is 1.8-4.6 m; 0.2.11 builds 3.66
POLE_TOP_M = (6.0, 18.0) # [invented] a pole's top over the ground
UTIL_TOP_M = 13.0        # [invented] a street light stands 9-12 m (0.2.11: 11.8 m mounting); a line pole taller
WIRE_NEAR_M = 2.5        # [invented] a wire ends at a pole's top: its nearest return this close in plan, within
                         # TOP_BAND_M + 2 m of the top's height
SHAFT_MIN = 2            # [invented]
SHAFT_SPAN_M = 2.0       # [invented]
ARM_MIN_M = 0.75         # [invented]
CLEAR_M = 3.0            # [invented]
ROAD_U = (-5.25, 20.1)   # measured: Colorado's outer curbs (lap_colorado_quebec.lidar.json, divided stations' medians)
LAMP_NEAR_M = 15.0       # the task's
SKIP_CLASSES = (2, 7, 9, 17, 18)


# ------------------------------------------------------------------------------------------------ EPT, local first


class Mirror:
    """each EPT file from the first local copy holding it (--dl, then each --mirror); otherwise fetched over HTTPS
    (TLS verified), its length checked, saved under --dl and indexed (dl/index.json: bytes, md5)"""

    def __init__(self, mirrors, dl: Path):
        self.dirs = [Path(m) for m in mirrors or []]
        self.dl = dl
        dl.mkdir(parents=True, exist_ok=True)
        self.index_p = dl / "index.json"
        self.index = json.loads(self.index_p.read_text()) if self.index_p.exists() else {"files": {}}
        self.fetched = 0

    def rel(self, url):
        if not url.startswith(EPT_BASE + "/"):
            raise SystemExit(f"refused (not the CO_DRCOG_2_2020 EPT): {url}")
        r = url[len(EPT_BASE) + 1:]
        if ".." in r or r.startswith("/"):
            raise SystemExit(f"refused path: {r}")
        return r

    def local(self, url):
        r = self.rel(url)
        for d in [self.dl] + self.dirs:
            if (d / r).exists():
                return d / r
        return None

    def get(self, url, offline=False):
        p = self.local(url)
        if p is not None:
            return p.read_bytes()
        if offline:
            raise SystemExit(f"offline: {self.rel(url)} is in no local copy")
        import ssl
        ctx = ssl.create_default_context()
        last = None
        for k in range(6):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "airoso-lidar/1.0"})
                with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
                    body = resp.read()
                    cl = resp.headers.get("Content-Length")
                if cl is not None and int(cl) != len(body):
                    raise IOError(f"short body {len(body)} of {cl}")
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError, IOError) as e:
                last = e
                time.sleep(min(60.0, 2.0 * 2 ** k))
        else:
            raise SystemExit(f"gave up on {self.rel(url)}: {last}")
        r = self.rel(url)
        p = self.dl / r
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        self.index["files"][r] = {"bytes": len(body), "md5": hashlib.md5(body).hexdigest()}
        self.index_p.write_text(json.dumps(self.index, indent=1, sort_keys=True))
        self.fetched += 1
        return body

    def head(self, url):
        import ssl
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "airoso-lidar/1.0"})
        with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
            return int(resp.headers["Content-Length"])


def mpd(lat0):
    """(m per deg lon, m per deg lat): scripts.geometry.projection._meters_per_degree, the same WGS84 series"""
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


# ------------------------------------------------------------------------------------------------------- the lap


class Lap:
    """the lap's line (x, z) by plan length s (closed), densified for nearest-point (s, u) lookups"""

    def __init__(self, repo: Path):
        import numpy as np
        cl = json.loads((repo / "tracks/sand-creek-lm/data/centerline.local.json").read_text())
        self.origin = cl["origin"]
        P = np.asarray(cl["points_xyz_m"], float)
        self.P = P
        self.xz = P[:, [0, 2]]
        self.s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(self.xz, axis=0).T))])
        self.L = float(self.s[-1])

    def at(self, s):
        import numpy as np
        s = np.mod(np.asarray(s, float), self.L)
        return np.stack([np.interp(s, self.s, self.xz[:, 0]), np.interp(s, self.s, self.xz[:, 1])], -1)

    def frame(self, s, h=5.0):
        import numpy as np
        c = self.at(s)
        t = self.at(np.asarray(s) + h) - self.at(np.asarray(s) - h)
        t = t / np.linalg.norm(t, axis=-1, keepdims=True)
        return c, t, np.stack([-t[..., 1], t[..., 0]], -1)

    def dense(self, s0, s1, step=0.25):
        import numpy as np
        S = np.arange(s0, s1 + 1e-9, step)
        c, t, n = self.frame(S)
        return S, c, t, n

    def su(self, x, z, dense):
        """(s, u) of plan points against the dense line (nearest dense point; u along its normal)"""
        import numpy as np
        from scipy.spatial import cKDTree
        S, c, t, n = dense
        d, k = cKDTree(c).query(np.stack([x, z], 1))
        dx, dz = x - c[k, 0], z - c[k, 1]
        return S[k] + dx * t[k, 0] + dz * t[k, 1], dx * n[k, 0] + dz * n[k, 1], d


def corridor_keys(mirror: Mirror, lap: Lap, offline=False):
    """every EPT node (key, points) whose box comes within CORR_M (+1 m) of the lap's line over S_RANGE +- PAD_S:
    tools/ept_plan's walk (the Sand Creek fetch of 2026-11-22), on this corridor"""
    import numpy as np
    from pyproj import Transformer
    o = lap.origin
    m_lon, m_lat = mpd(o["lat"])
    _, c, _, _ = lap.dense(S_RANGE[0] - PAD_S, S_RANGE[1] + PAD_S, 1.0)
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    mx, my = to_merc.transform(o["lon"] + c[:, 0] / m_lon, o["lat"] + c[:, 1] / m_lat)
    mx, my = np.asarray(mx), np.asarray(my)
    reach = (CORR_M + 1.0) / math.cos(math.radians(o["lat"]))     # mercator metres per ground metre
    meta = json.loads(mirror.get(EPT_URL, offline))
    if meta["srs"].get("horizontal") != "3857":
        raise SystemExit("not EPSG:3857")
    b = meta["bounds"]
    hier = {}

    def h_of(k):
        if k not in hier:
            hier[k] = json.loads(mirror.get(f"{EPT_BASE}/ept-hierarchy/{k}.json", offline))
        return hier[k]
    keys = []

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        sz = (b[3] - b[0]) / 2 ** d
        x0, y0 = b[0] + x * sz, b[1] + y * sz
        dx = np.maximum(np.maximum(x0 - mx, 0), mx - (x0 + sz))
        dy = np.maximum(np.maximum(y0 - my, 0), my - (y0 + sz))
        if not np.any(np.hypot(dx, dy) <= reach):
            return
        if h[k] == -1:
            h = h_of(k)
        if h[k] > 0:
            keys.append((k, int(h[k])))
        for ddx in (0, 1):
            for ddy in (0, 1):
                for ddz in (0, 1):
                    walk(d + 1, 2 * x + ddx, 2 * y + ddy, 2 * z + ddz, h)
    walk(0, 0, 0, 0, h_of("0-0-0-0"))
    return keys


def cmd_fetch(a):
    repo = Path(a.repo).resolve()
    lap = Lap(repo)
    mirror = Mirror(a.mirror, Path(a.dl))
    keys = corridor_keys(mirror, lap)
    miss = [(k, n) for k, n in keys if mirror.local(f"{EPT_BASE}/ept-data/{k}.laz") is None]
    print(f"[poles] corridor: {len(keys)} nodes ({sum(n for _, n in keys):,} points), {len(keys) - len(miss)} local, "
          f"{len(miss)} to fetch; hierarchy files fetched {mirror.fetched}", flush=True)
    if a.plan:
        sizes = {k: mirror.head(f"{EPT_BASE}/ept-data/{k}.laz") for k, _ in miss}
        Path(a.plan).write_text(json.dumps({"nodes": len(keys), "local": len(keys) - len(miss), "to_fetch": sizes,
                                            "bytes_to_fetch": sum(sizes.values())}, indent=1))
        print(f"[poles] to fetch: {len(sizes)} nodes, {sum(sizes.values()):,} bytes", flush=True)
        return 0
    for k, _ in miss:
        mirror.get(f"{EPT_BASE}/ept-data/{k}.laz")
    laz = {r: v for r, v in mirror.index["files"].items() if r.endswith(".laz")}
    print(f"[poles] fetched {len(laz)} nodes, {sum(v['bytes'] for v in laz.values()):,} bytes (dl/index.json)",
          flush=True)
    return 0


# ---------------------------------------------------------------------------------------------------- the points


def read_points(mirror: Mirror, lap: Lap, keys):
    """every return within CORR_M of the lap's line over S_RANGE +- PAD_S, node by node (memory stays small)"""
    import laspy
    import numpy as np
    from pyproj import Transformer
    o = lap.origin
    m_lon, m_lat = mpd(o["lat"])
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    dense = lap.dense(S_RANGE[0] - PAD_S - 40.0, S_RANGE[1] + PAD_S + 40.0)
    acc = {k: [] for k in ("E", "N", "Z", "C", "I", "RN", "NR", "s", "u")}
    for k, _ in sorted(keys, key=lambda t: [int(v) for v in t[0].split("-")]):
        las = laspy.read(io.BytesIO(mirror.get(f"{EPT_BASE}/ept-data/{k}.laz", offline=True)))
        lon, lat = to_ll.transform(np.asarray(las.x), np.asarray(las.y))
        E = (np.asarray(lon) - o["lon"]) * m_lon
        N = (np.asarray(lat) - o["lat"]) * m_lat
        s, u, d = lap.su(E, N, dense)
        m = (np.abs(u) <= CORR_M) & (s >= S_RANGE[0] - PAD_S) & (s <= S_RANGE[1] + PAD_S) & (d <= CORR_M + 1.0)
        if not m.any():
            continue
        acc["E"].append(E[m]); acc["N"].append(N[m]); acc["Z"].append(np.asarray(las.z)[m] - float(o["elev_m"]))
        acc["C"].append(np.asarray(las.classification)[m].astype(np.uint8))
        acc["I"].append(np.asarray(las.intensity)[m].astype(np.float32))
        acc["RN"].append(np.asarray(las.return_number)[m].astype(np.uint8))
        acc["NR"].append(np.asarray(las.number_of_returns)[m].astype(np.uint8))
        acc["s"].append(s[m]); acc["u"].append(u[m])
    return {k: np.concatenate(v) for k, v in acc.items()}


def ground_model(Pt):
    """the class-2 median per DTM_M cell, holes filled from the nearest read cell: (grid origin, cell, G)"""
    import numpy as np
    from scipy import ndimage
    g = Pt["C"] == 2
    x0, z0 = float(Pt["E"].min()) - 1.0, float(Pt["N"].min()) - 1.0
    nx = int((Pt["E"].max() - x0) / DTM_M) + 2
    nz = int((Pt["N"].max() - z0) / DTM_M) + 2
    ix = ((Pt["E"][g] - x0) / DTM_M).astype(int)
    iz = ((Pt["N"][g] - z0) / DTM_M).astype(int)
    key = iz * nx + ix
    o = np.argsort(key)
    key, zz = key[o], Pt["Z"][g][o]
    G = np.full(nx * nz, np.nan)
    u, st = np.unique(key, return_index=True)
    bounds = list(st) + [len(key)]
    for j, kk in enumerate(u):
        G[kk] = np.median(zz[bounds[j]:bounds[j + 1]])
    G = G.reshape(nz, nx)
    holes = ~np.isfinite(G)
    if holes.any():
        _, (iz2, ix2) = ndimage.distance_transform_edt(holes, return_indices=True)
        G = G[iz2, ix2]
    return x0, z0, G


def ground_at(model, x, z):
    import numpy as np
    x0, z0, G = model
    ix = np.clip(((np.asarray(x) - x0) / DTM_M).astype(int), 0, G.shape[1] - 1)
    iz = np.clip(((np.asarray(z) - z0) / DTM_M).astype(int), 0, G.shape[0] - 1)
    return G[iz, ix]


# --------------------------------------------------------------------------------------------------- the objects


def objects(Pt, model):
    """non-ground returns HAG_MIN or more over the ground, joined in plan within LINK_M"""
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    hag = Pt["Z"] - ground_at(model, Pt["E"], Pt["N"])
    m = (~np.isin(Pt["C"], SKIP_CLASSES)) & (hag >= HAG_MIN)
    idx = np.nonzero(m)[0]
    xy = np.stack([Pt["E"][idx], Pt["N"][idx]], 1)
    pairs = cKDTree(xy).query_pairs(LINK_M, output_type="ndarray")
    A = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(idx), len(idx)))
    ncomp, lab = connected_components(A, directed=False)
    return idx, hag, lab, ncomp


def shape(Pt, hag, ids):
    import numpy as np
    x, z, h = Pt["E"][ids], Pt["N"][ids], hag[ids]
    xy = np.stack([x, z], 1)
    c = xy.mean(0)
    if len(ids) >= 3:
        w, V = np.linalg.eigh(np.cov((xy - c).T))
        major, minor = V[:, 1], V[:, 0]
        sd_major, sd_minor = float(math.sqrt(max(w[1], 0))), float(math.sqrt(max(w[0], 0)))
        proj = (xy - c) @ major
        length = float(proj.max() - proj.min())
    else:
        major = np.array([1.0, 0.0]); sd_major = sd_minor = 0.0; length = float(np.ptp(x) if len(ids) > 1 else 0.0)
    top = float(h.max())
    nonlast = float(np.mean(Pt["RN"][ids] < Pt["NR"][ids]))
    return {"n": int(len(ids)), "top_hag": top, "top_y": float(Pt["Z"][ids].max()), "sd_major": sd_major,
            "sd_minor": sd_minor, "length": length, "major": major, "centre": c, "nonlast": nonlast}


def toward_road_sign(u):
    """+1: the road lies toward +u from here; -1: toward -u; 0: inside the road (the median)"""
    if u < ROAD_U[0]:
        return +1
    if u > ROAD_U[1]:
        return -1
    return 0


def cmd_measure(a):
    import numpy as np
    from pyproj import Transformer
    from scipy.spatial import cKDTree
    repo = Path(a.repo).resolve()
    lap = Lap(repo)
    mirror = Mirror(a.mirror, Path(a.dl))
    keys = corridor_keys(mirror, lap, offline=True)
    Pt = read_points(mirror, lap, keys)
    cls, cnt = np.unique(Pt["C"], return_counts=True)
    print(f"[poles] {len(keys)} nodes, {len(Pt['E']):,} returns kept; classes "
          f"{dict(zip(cls.tolist(), cnt.tolist()))}", flush=True)
    model = ground_model(Pt)
    idx, hag, lab, ncomp = objects(Pt, model)
    o = lap.origin
    m_lon, m_lat = mpd(o["lat"])
    dense = lap.dense(S_RANGE[0] - PAD_S - 40.0, S_RANGE[1] + PAD_S + 40.0)
    groups = {}
    for i, L in zip(idx, lab):
        groups.setdefault(int(L), []).append(int(i))
    shapes = {L: shape(Pt, hag, np.asarray(ids)) for L, ids in groups.items()}
    kind = {}
    for L, sh in shapes.items():
        if sh["length"] >= WIRE_LEN_M and sh["sd_minor"] <= WIRE_W_M and sh["top_hag"] >= WIRE_HAG_M:
            kind[L] = "wire"
        elif (sh["sd_minor"] >= TREE_W_M and sh["n"] >= TREE_N) or (sh["nonlast"] >= TREE_NONLAST
                                                                     and sh["sd_minor"] >= TREE_W_M / 2):
            kind[L] = "tree"
        elif sh["sd_minor"] <= POLE_W_M and POLE_TOP_M[0] <= sh["top_hag"] <= POLE_TOP_M[1]:
            kind[L] = "pole?"
        else:
            kind[L] = "other"
    # wire returns, for "a wire ends at this pole's top"
    wire_ids = np.asarray([i for L, ids in groups.items() if kind[L] == "wire" for i in ids], int)
    wtree = cKDTree(np.stack([Pt["E"][wire_ids], Pt["N"][wire_ids]], 1)) if len(wire_ids) else None
    # tree / wire returns, for the clearance
    busy_ids = np.asarray([i for L, ids in groups.items() if kind[L] in ("tree", "wire") for i in ids], int)
    btree = cKDTree(np.stack([Pt["E"][busy_ids], Pt["N"][busy_ids]], 1)) if len(busy_ids) else None
    to_ll = (o, m_lon, m_lat)
    poles = []
    for L, sh in shapes.items():
        if kind[L] != "pole?":
            continue
        ids = np.asarray(groups[L])
        x, z, h = Pt["E"][ids], Pt["N"][ids], hag[ids]
        top = sh["top_hag"]
        shaft = h <= top - TOP_BAND_M
        band = ~shaft
        su_all = lap.su(x, z, dense)
        if shaft.sum() >= SHAFT_MIN:
            bx, bz = float(np.median(x[shaft])), float(np.median(z[shaft]))
            base_from = "shaft"
        else:
            # the top band's two ends along its long axis: the pole is the end farther from the road's middle
            c = sh["centre"]; ax = sh["major"]
            pr = (np.stack([x[band], z[band]], 1) - c) @ ax
            ends = [c + ax * pr.min(), c + ax * pr.max()]
            eu = [float(lap.su(np.array([e[0]]), np.array([e[1]]), dense)[1][0]) for e in ends]
            mid = 0.5 * (ROAD_U[0] + ROAD_U[1])
            j = int(np.argmax([abs(v - mid) for v in eu]))
            bx, bz = float(ends[j][0]), float(ends[j][1])
            base_from = "top band's end farther from the road (no shaft return)"
        reach = float(np.max(np.hypot(x - bx, z - bz)))
        if reach > POLE_REACH_M:
            kind[L] = "other"
            continue
        s_b, u_b, _ = lap.su(np.array([bx]), np.array([bz]), dense)
        s_b, u_b = float(s_b[0]), float(u_b[0])
        gy = float(ground_at(model, bx, bz))
        # the arm: base to the top band's farthest return
        bx_t, bz_t = x[band], z[band]
        dd = np.hypot(bx_t - bx, bz_t - bz)
        arm = None
        if len(dd) and dd.max() >= ARM_MIN_M:
            j = int(np.argmax(dd))
            v = np.array([bx_t[j] - bx, bz_t[j] - bz])
            # its u component, from the lap's frame at the base
            _, tt, nn = lap.frame(np.array([s_b]))
            du = float(v @ nn[0])
            sgn = toward_road_sign(u_b)
            az = (math.degrees(math.atan2(v[0], v[1])) + 360.0) % 360.0
            both = bool(((np.stack([bx_t - bx, bz_t - bz], 1) @ nn[0]) > ARM_MIN_M).any()
                        and ((np.stack([bx_t - bx, bz_t - bz], 1) @ nn[0]) < -ARM_MIN_M).any())
            arm = {"length_m": round(float(dd.max()), 2), "azimuth_deg": round(az, 1),
                   "u_component_m": round(du, 2), "points": "+u (west)" if du > 0 else "-u (east)",
                   "toward_road": (None if sgn == 0 else bool(du * sgn > 0)),
                   "both_sides": both}
        # a wire ending at the top
        wire_end = None
        if wtree is not None:
            tops = np.nonzero(band)[0]
            dw, kw = wtree.query(np.stack([x[tops], z[tops]], 1))
            near = dw <= WIRE_NEAR_M
            if near.any():
                wi = wire_ids[kw[near]]
                ok = np.abs(hag[wi] - top) <= TOP_BAND_M + 2.0
                if ok.any():
                    wl = int(lab[np.searchsorted(idx, wi[ok][0])])
                    wsh = shapes[wl]
                    waz = (math.degrees(math.atan2(wsh["major"][0], wsh["major"][1])) + 360.0) % 180.0
                    wire_end = {"wire_length_m": round(wsh["length"], 1), "wire_axis_deg": round(waz, 1),
                                "wire_top_hag_m": round(wsh["top_hag"], 2), "wire_returns": wsh["n"]}
        clear = None
        if btree is not None:
            dcl, _ = btree.query([bx, bz])
            clear = round(float(dcl), 2)
        line = top >= UTIL_TOP_M or wire_end is not None
        shaft_ok = shaft.sum() >= SHAFT_MIN and float(np.ptp(h[shaft])) >= SHAFT_SPAN_M
        if not shaft_ok:
            # nothing under the top band: a head and arm, a sign's or a billboard's top; which end is a pole (if any)
            # is not measured, so no arm direction is claimed
            ksub = "head / arm only, no shaft"
            ax = sh["major"]
            _, tt, nn = lap.frame(np.array([s_b]))
            across = abs(float(ax @ nn[0])) >= 0.7
            arm = {"length_m": round(sh["length"], 2),
                   "axis_azimuth_deg": round((math.degrees(math.atan2(ax[0], ax[1])) + 360.0) % 180.0, 1),
                   "axis": "across the road (u)" if across else "along the road (s)", "toward_road": None,
                   "note": "no shaft returns: which end stands on a pole is not measured"}
        else:
            ksub = "line pole" if line else "light pole"
        why_line = []
        if top >= UTIL_TOP_M:
            why_line.append(f"taller: top {top:.1f} m over the ground (>= {UTIL_TOP_M})")
        if wire_end is not None:
            why_line.append(f"a wire ends at its top ({wire_end['wire_length_m']} m long, axis "
                            f"{wire_end['wire_axis_deg']} deg)")
        has_top = band.sum() >= 2
        isolated = clear is None or clear >= CLEAR_M
        if shaft_ok and has_top and isolated:
            conf = "high"
        elif shaft_ok:
            conf = "medium"
        else:
            conf = "low"
        reason = (f"{int(shaft.sum())} shaft returns spanning {float(np.ptp(h[shaft])) if shaft.any() else 0:.1f} m, "
                  f"{int(band.sum())} in the top band, footprint sd {sh['sd_minor']:.2f} m, nearest tree / wire "
                  f"{'none' if clear is None else f'{clear} m'}, non-last share {sh['nonlast']:.2f}")
        lon = o["lon"] + bx / m_lon
        lat = o["lat"] + bz / m_lat
        poles.append({"kind": ksub, "line_pole_because": why_line or None,
                      "base_xz": [round(bx, 2), round(bz, 2)], "base_lonlat": [round(lon, 7), round(lat, 7)],
                      "base_from": base_from, "s": round(s_b, 1), "u": round(u_b, 2),
                      "ground_y": round(gy, 2), "top_y": round(sh["top_y"], 2), "top_over_ground_m": round(top, 2),
                      "returns": sh["n"], "shaft_returns": int(shaft.sum()), "top_band_returns": int(band.sum()),
                      "returns_over_ground_m": [round(float(h.min()), 2), round(float(h.max()), 2)],
                      "footprint": {"plan_sd_minor_m": round(sh["sd_minor"], 2),
                                    "plan_sd_major_m": round(sh["sd_major"], 2),
                                    "reach_from_base_m": round(reach, 2),
                                    "shaft_spread_m": (round(float(np.max(np.hypot(x[shaft] - bx, z[shaft] - bz))), 2)
                                                       if shaft.any() else None)},
                      "arm": arm, "wire_at_top": wire_end, "nearest_tree_or_wire_m": clear,
                      "confidence": conf, "confidence_reason": reason})
    inside = [p for p in poles if S_RANGE[0] <= p["s"] <= S_RANGE[1] and abs(p["u"]) <= U_HALF]
    inside.sort(key=lambda p: p["s"])
    for k, p in enumerate(inside):
        p["id"] = f"P{k + 1:02d}"
    outside = [p for p in poles if S_RANGE[0] - PAD_S <= p["s"] <= S_RANGE[1] + PAD_S and p not in inside
               and abs(p["u"]) <= CORR_M - 2.0]
    outside.sort(key=lambda p: p["s"])
    for k, p in enumerate(outside):
        p["id"] = f"Q{k + 1:02d}"
    tall = []
    for L, sh in shapes.items():
        s_c, u_c, _ = lap.su(np.array([sh["centre"][0]]), np.array([sh["centre"][1]]), dense)
        if sh["top_hag"] >= 5.0 and abs(float(u_c[0])) <= CORR_M - 2.0:
            tall.append({"kind": kind[L], "s": round(float(s_c[0]), 1), "u": round(float(u_c[0]), 1),
                         "returns": sh["n"], "top_over_ground_m": round(sh["top_hag"], 2),
                         "plan_sd_minor_m": round(sh["sd_minor"], 2), "plan_length_m": round(sh["length"], 1),
                         "non_last_share": round(sh["nonlast"], 2)})
    tall.sort(key=lambda r: r["s"])
    # the lamps 0.2.11 built here
    lights = json.loads((repo / "tracks/sand-creek-lm/data/lights.local.json").read_text())
    lamps = []
    LB = np.asarray(lights["lamp_bases_xz"], float)
    s_l, u_l, _ = lap.su(LB[:, 0], LB[:, 1], dense)
    allp = inside + outside
    pp = np.asarray([p["base_xz"] for p in allp], float) if allp else np.zeros((0, 2))
    for i in range(len(LB)):
        if not (S_RANGE[0] <= s_l[i] <= S_RANGE[1] and abs(u_l[i]) <= U_HALF):
            continue
        rec = {"lamp": i, "base_xz": [float(LB[i, 0]), float(LB[i, 1])], "s": round(float(s_l[i]), 1),
               "u": round(float(u_l[i]), 2)}
        if len(pp):
            d = np.hypot(pp[:, 0] - LB[i, 0], pp[:, 1] - LB[i, 1])
            j = int(np.argmin(d))
            rec["nearest_pole"] = allp[j]["id"]
            rec["nearest_pole_kind"] = allp[j]["kind"]
            rec["distance_m"] = round(float(d[j]), 2)
            rec["delta_s_m"] = round(allp[j]["s"] - rec["s"], 1)
            rec["delta_u_m"] = round(allp[j]["u"] - rec["u"], 2)
            rec["verdict"] = (f"{allp[j]['kind']} {allp[j]['id']} at {d[j]:.1f} m" if d[j] <= LAMP_NEAR_M
                              else f"no pole within {LAMP_NEAR_M:.0f} m")
        else:
            rec["verdict"] = f"no pole within {LAMP_NEAR_M:.0f} m"
        lamps.append(rec)
    win = ((Pt["s"] >= S_RANGE[0]) & (Pt["s"] <= S_RANGE[1]) & (np.abs(Pt["u"]) <= U_HALF)
           & ~np.isin(Pt["C"], SKIP_CLASSES))
    hag_all = Pt["Z"] - ground_at(model, Pt["E"], Pt["N"])
    window_high = {f"{t}m": int((win & (hag_all >= t)).sum()) for t in (3, 4, 5, 6, 7, 8, 10)}
    area = (S_RANGE[1] - S_RANGE[0]) * 2 * U_HALF
    inwin = (Pt["s"] >= S_RANGE[0]) & (Pt["s"] <= S_RANGE[1]) & (np.abs(Pt["u"]) <= U_HALF)
    density = round(float(inwin.sum()) / area, 2)
    counts = {}
    for L, kd in kind.items():
        counts[kd] = counts.get(kd, 0) + 1
    out = {
        "_doc": ("Colorado Blvd's real poles off the 2020 lidar, every class (roads_lidar_g10/colorado_poles_g10.py; "
                 "its docstring gives the method and every [invented] constant). poles: each column standing alone "
                 "(kind light pole | line pole), base in the lap's frame (x, z) and lon / lat, s / u in the lap's "
                 "Colorado frame (s: plan metres along centerline.local.json from v0; +u = left of travel, west), "
                 "ground_y and top_y (the lap's y = las z - origin.elev_m), footprint, arm (azimuth clockwise from "
                 "north; toward_road: from the base toward the road between its outer curbs; null in the median), "
                 "confidence and why. lamps: the lamps data/lights.local.json builds here, each to its nearest pole."),
        "lidar": "USGS CO_DRCOG_2_2020 (" + EPT_URL + "), every class",
        "window": {"s": list(S_RANGE), "u": [-U_HALF, U_HALF], "kept_corridor_m": CORR_M, "pad_s_m": PAD_S},
        "nodes_read": len(keys), "returns_kept": int(len(Pt["E"])),
        "classes_kept": {int(c): int(n) for c, n in zip(cls, cnt)},
        "objects": {"total": ncomp, "by_kind": counts},
        "window_returns_per_m2": density,
        "window_non_ground_returns_at_or_over": window_high,
        "constants": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, tuple))},
        "poles": inside, "poles_outside_window": outside, "objects_5m_or_taller": tall, "lamps": lamps}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"[poles] objects {ncomp}: {counts}; poles in the window {len(inside)} "
          f"({sum(p['kind'] == 'light pole' for p in inside)} light, {sum(p['kind'] == 'line pole' for p in inside)} "
          f"line); outside {len(outside)}; window high returns {window_high}, {density}/m2; lamps {len(lamps)}",
          flush=True)
    for p in inside + outside:
        print(f"  {p['id']} {p['kind']:10s} s {p['s']:6.1f} u {p['u']:+6.2f} top {p['top_over_ground_m']:5.2f} "
              f"n {p['returns']:3d} shaft {p['shaft_returns']:2d} arm "
              f"{'-' if not p['arm'] else (str(p['arm']['length_m']) + ' ' + str(p['arm'].get('points', p['arm'].get('axis'))))} "
              f"{p['confidence']} clear {p['nearest_tree_or_wire_m']}", flush=True)
    for r in lamps:
        print(f"  lamp {r['lamp']} s {r['s']} u {r['u']}: {r['verdict']} (nearest {r.get('nearest_pole')} "
              f"{r.get('distance_m')} m)", flush=True)
    for r in tall:
        print(f"  tall {r}", flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("fetch", "measure"):
        p = sub.add_parser(nm)
        p.add_argument("--repo", required=True)
        p.add_argument("--dl", required=True)
        p.add_argument("--mirror", action="append")
        if nm == "fetch":
            p.add_argument("--plan")
        else:
            p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return cmd_fetch(a) if a.cmd == "fetch" else cmd_measure(a)


if __name__ == "__main__":
    sys.exit(main())

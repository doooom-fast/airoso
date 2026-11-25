"""SAND CREEK'S REAL ROADS OFF THE 2020 LIDAR, for round 2 and after (ledgers 0079 / 0098; data only, nothing reads it).

Kevin: "I just want real". Measured numbers only; every chosen constant is marked [invented] (or [sampling] where it
only sets how often a thing is read). Three items:

  1. COLORADO BLVD (lap v3205 -> v140, wrapping past v0) and the lap's QUEBEC ST (v1940 -> v2080), every STATION_M of the
     lap's s (plan length along centerline.local.json's points, from v0), in the lap's frame (+u = left of travel):
     every curb face across the whole road (outer curbs, both faces of a raised median) with its step, the median's top
     and width, the two carriageways' widths, the built edges (+-widths_m / 2) and real minus built for each face.
  2. THE NORTHFIELD QUEBEC ARMS (grid_primary_78 / grid_primary_84#0#0 of data/connectors.local.json, the stretch 0098
     names for its raised median, quebec_median: from the nose at the sandcreek_quebec pad to where the arms meet): the
     same, along each arm's TRUE lon / lat line (a drawn grid point x, z is read at x * KX, z * KZ,
     tools/grid_reach.frame_scale), every STATION_M of it (+u = left of the arm's travel, toward the median); and per
     ROW of each drawn piece: the drawn point, its true counterpart, the offset, and the faces and the median's top
     carried into that piece's own (drawn) frame.
  3. THE QUEBEC ST BRIDGE OVER SAND CREEK: the class-17 deck along the lap every 1 m at the lap's centre line and its
     two wheel paths (scripts/geometry/drive_test.WHEEL_HALF_TRACK), the class-2 ground on the approaches, the lap's
     built height (centerline.local.json y) and built minus real.

THE LIDAR. USGS CO_DRCOG_2_2020 through tools/lidar_connector_profile.py: its frame (E, N metres about the lap's origin,
scripts.geometry.projection's WGS84 series; Z = las z - origin.elev_m, the lap's y), its tile_i_j.npz cache (100 m tiles
+ 5 m, classes 2 and 17) and its Ept.tile reader. `tiles` builds the tiles a cache lacks with that reader, its HTTP get
pointed first at local copies of EPT nodes fetched earlier (--mirror), then at the public EPT; a node it fetches is saved
under --dl with its md5 (dl/index.json).

THE CROSS-SECTION (items 1 and 2), along a reference line (the lap; each arm's true line):
  * tools/lidar_curb_trace.py's raster: rows every ROW_M along; across, bins every 0.25 m; each cell the median class-2
    ground within +-0.75 m along and +-1 bin across (3 returns or more); rows then averaged 5 at a time (+-1 m);
  * THE KINK MAP: at each bin a straight line through the bins KINK_BINS off each side, both read at the bin: K = the
    +u line minus the -u line. A curb face (vertical or sloped up to ~1.5 m) is a ridge of |K|; a steady crossfall or a
    fill's slope reads K ~ 0, which a difference of means (lidar_curb_trace's step map) does not. A step counts only
    with both side lines graded under GENTLE (a fill's slope carried back to its top edge would read as one);
  * FOUR FACES, each a Viterbi line (lidar_curb_trace.viterbi) through every row, searched outward in order:
    right_edge (a curb: the ground steps up toward -u; or, with no curb, a fall: the grade outward drops), the first
    face left of the line (the median's near face, or the left edge), the median's far face (the ground steps down
    toward +u onto SMOOTH_M of carriageway: rms under ROUGH_M, grade under 8 %), the far carriageway's left edge. A
    line's score is capped (CAP_M, DROP_CAP_M) so a taller wall further out does not outbid a curb, the innermost
    preferred (INWARD_K); each row is then moved to its own strongest bin within REFINE_BINS;
  * PER STATION, from the raw class-2 returns within +-STATION_M / 2 along: at each face a straight line through the
    returns FOOT_M off each side, both read at the face; the step is their difference (a narrow median's top: its
    returns' median). Kinds: an outer edge is `curb` (steps up outward by STEP_M or more), `drop` (steps down outward
    by STEP_M or more), `fall` (no step; the outward grade drops by FALL_GRADE or more: a road on a fill) or `none`; a
    median face is `curb` or `none`. A `none` face's u is where the line ran, not a measurement: no width uses it;
  * DIVIDED: both median faces `curb`, the far one onto a carriageway, MEDIAN_MIN_M apart or more, the two
    carriageways' lines at the faces within ROAD_DY_M. Otherwise the first face left of the line is the left edge
    and the station is one carriageway (its far-face and far-edge candidates are kept, marked so).

    python -I roads_lidar_g10.py tiles   --repo R --cache DIR --tiles 17_-6,18_-6 [--mirror DIR ...] --dl DIR [--plan]
    python -I roads_lidar_g10.py measure --repo R --cache DIR --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# The repo's TLS rule (scripts/tls.py, tests/net/test_https_everywhere.py): every fetch uses scripts.tls.https_context().
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.tls import https_context  # noqa: E402

EPT_URL = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json"
EPT_BASE = EPT_URL.rsplit("/", 1)[0]

STATION_M = 2.5          # [sampling] the task's station spacing along the lap's s
ROW_M = 0.5              # = tools/lidar_curb_trace.ROW_M [invented there]: raster rows along
BRIDGE_STEP_M = 1.0      # [sampling] the bridge profile's spacing along the lap
CAP_M = 0.08             # = lidar_curb_trace.OUTER_CAP_M [invented]: a face's score counts its step up to this
STEP_M = 0.08            # = tools/naip_edge.STEP_M (round J [invented]): a curb face's step, at least
FOOT_M = (0.75, 2.00)    # [invented] a face's step: a straight line through the returns this far off each side,
                         # past a sloped face's foot and top, both carried back to the face
SMOOTH_M = 4.0           # [invented] a carriageway past median_far: this much smooth ground
ROUGH_M = 0.03           # [invented] ... smooth = the 0.25 m bins' rms about their own straight line under this
ROAD_DY_M = 0.6          # [invented] divided: the two carriageways' lines, read at the median's faces, within this
MEDIAN_MIN_M = 0.5       # [invented] a median is at least this wide face to face
TOP_IN_M = 0.30          # [invented] the median's top: ground from this far inside each face
BRIDGE_R_M = 1.0         # = tools/lidar_connector_profile.RADIUS_M [invented there]
BRIDGE_MIN = 3           # = lidar_connector_profile.MIN_RETURNS [invented there]
APPROACH_M = 40.0        # [invented] the bridge's approaches: this far either side of the deck's class-17 ends


# ------------------------------------------------------------------------------------------------- repo + the lidar


def repo_paths(repo: Path):
    for p in (str(repo), str(repo / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)


class Mirror:
    """lidar_connector_profile._get, local first: each EPT file is read from the first --mirror (or --dl) holding it;
    otherwise fetched over HTTPS (TLS verified), its length checked, saved under dl and indexed (md5, bytes)."""

    def __init__(self, mirrors, dl: Path, offline: bool):
        self.dirs = [Path(m) for m in mirrors]
        self.dl = dl
        self.offline = offline
        self.index_p = dl / "index.json"
        self.index = json.loads(self.index_p.read_text()) if self.index_p.exists() else {"files": {}}
        self.local_hits = 0
        self.fetched = 0

    def rel(self, url):
        if not url.startswith(EPT_BASE + "/"):
            raise SystemExit(f"refused (not the CO_DRCOG_2_2020 EPT): {url}")
        r = url[len(EPT_BASE) + 1:]
        if ".." in r or r.startswith("/"):
            raise SystemExit(f"refused path: {r}")
        return r

    def has(self, url):
        r = self.rel(url)
        return any((d / r).exists() for d in [self.dl] + self.dirs)

    def get(self, url):
        r = self.rel(url)
        for d in [self.dl] + self.dirs:
            p = d / r
            if p.exists():
                self.local_hits += 1
                return p.read_bytes()
        if self.offline:
            raise SystemExit(f"offline: {r} is in no mirror")
        import ssl
        last = None
        for k in range(6):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "airoso-lidar/1.0"})
                with urllib.request.urlopen(req, timeout=180, context=https_context()) as resp:
                    body = resp.read()
                    cl = resp.headers.get("Content-Length")
                if cl is not None and int(cl) != len(body):
                    raise IOError(f"short body {len(body)} of {cl}")
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError, IOError) as e:
                last = e
                time.sleep(min(60.0, 2.0 * 2 ** k))
        else:
            raise SystemExit(f"gave up on {r}: {last}")
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
        with urllib.request.urlopen(req, timeout=60, context=https_context()) as resp:
            return int(resp.headers["Content-Length"])


def tile_keys(mirror: Mirror, origin, i, j):
    """the EPT node keys lidar_connector_profile.Ept.tile reads for tile (i, j): its own walk, its own window"""
    import lidar_connector_profile as lcp
    from pyproj import Transformer
    meta = json.loads(mirror.get(EPT_URL))
    b = meta["bounds"]
    m_lon, m_lat = lcp._meters_per_degree(origin["lat"])
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    e0, n0 = i * lcp.TILE_M - 5.0, j * lcp.TILE_M - 5.0
    e1, n1 = e0 + lcp.TILE_M + 10.0, n0 + lcp.TILE_M + 10.0
    x0, y0 = to_merc.transform(origin["lon"] + e0 / m_lon, origin["lat"] + n0 / m_lat)
    x1, y1 = to_merc.transform(origin["lon"] + e1 / m_lon, origin["lat"] + n1 / m_lat)
    hier = {}

    def h_of(k):
        if k not in hier:
            hier[k] = json.loads(mirror.get(f"{EPT_BASE}/ept-hierarchy/{k}.json"))
        return hier[k]
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
            keys.append((k, h[k]))
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, h_of("0-0-0-0"))
    return keys


def cmd_tiles(a):
    repo = Path(a.repo).resolve()
    repo_paths(repo)
    import lidar_connector_profile as lcp
    origin = json.loads((repo / "tracks/sand-creek-lm/data/centerline.local.json").read_text())["origin"]
    dl = Path(a.dl)
    dl.mkdir(parents=True, exist_ok=True)
    mirror = Mirror(a.mirror or [], dl, offline=False)
    cache = Path(a.cache)
    tiles = [tuple(int(v) for v in t.split("_")) for t in a.tiles.split(",")]
    if a.plan:
        rep, tot_new, n_new = {}, 0, 0
        for i, j in tiles:
            if (cache / f"tile_{i}_{j}.npz").exists():
                rep[f"{i}_{j}"] = "in the cache"
                continue
            keys = tile_keys(mirror, origin, i, j)
            new = [(k, n) for k, n in keys if not mirror.has(f"{EPT_BASE}/ept-data/{k}.laz")]
            sizes = {k: mirror.head(f"{EPT_BASE}/ept-data/{k}.laz") for k, _ in new}
            rep[f"{i}_{j}"] = {"nodes": len(keys), "points": sum(n for _, n in keys), "local": len(keys) - len(new),
                               "to_fetch": len(new), "to_fetch_points": sum(n for _, n in new),
                               "to_fetch_bytes": sum(sizes.values()), "fetch_keys": sorted(sizes)}
            print(f"[plan] tile {i}_{j}: {len(keys)} nodes, {len(keys) - len(new)} local, {len(new)} to fetch, "
                  f"{sum(sizes.values()) / 1e6:.2f} MB", flush=True)
            for k in sizes:
                if k not in rep.get("_union", {}):
                    rep.setdefault("_union", {})[k] = sizes[k]
        u = rep.get("_union", {})
        tot_new, n_new = sum(u.values()), len(u)
        rep["_total"] = {"nodes_to_fetch": n_new, "bytes_to_fetch": tot_new,
                         "hierarchy_fetched": mirror.fetched, "hierarchy_bytes": sum(
                             v["bytes"] for v in mirror.index["files"].values())}
        Path(a.plan).write_text(json.dumps(rep, indent=1))
        print(f"[plan] union: {n_new} nodes to fetch, {tot_new / 1e6:.2f} MB; hierarchy files fetched "
              f"{mirror.fetched}", flush=True)
        return 0
    lcp._get = mirror.get                         # the reader's own walk and cut, local copies first
    ept = lcp.Ept(EPT_URL, origin, cache)
    for i, j in tiles:
        p = cache / f"tile_{i}_{j}.npz"
        if p.exists():
            print(f"[tiles] {i}_{j}: in the cache", flush=True)
            continue
        f0 = mirror.fetched
        E, N, Z, C = ept.tile(i, j)
        print(f"[tiles] {i}_{j}: {len(E)} returns ({int((C == 2).sum())} ground, {int((C == 17).sum())} deck); "
              f"{mirror.fetched - f0} files fetched", flush=True)
    print(f"[tiles] local reads {mirror.local_hits}, fetched {mirror.fetched}", flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tiles")
    t.add_argument("--repo", required=True)
    t.add_argument("--cache", required=True)
    t.add_argument("--tiles", required=True)
    t.add_argument("--mirror", action="append")
    t.add_argument("--dl", required=True)
    t.add_argument("--plan")
    m = sub.add_parser("measure")
    m.add_argument("--repo", required=True)
    m.add_argument("--cache", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--only")
    a = ap.parse_args(argv)
    if a.cmd == "tiles":
        return cmd_tiles(a)
    return cmd_measure(a)


# ------------------------------------------------------------------------------------------- the lidar, by tile


class Lidar:
    """class-2 / class-17 returns of the tiles a job needs, through lidar_connector_profile.Ept.tile on the cache (a
    tile the cache lacks is refused here: `tiles` builds it). Each tile keeps its own 100 m square only, so the 5 m
    margins two tiles share are read once."""

    def __init__(self, cache: Path, origin):
        import lidar_connector_profile as lcp

        def refuse(url):
            raise SystemExit(f"measure reads the cache only; not in it: {url}")
        lcp._get = refuse
        self.ept = lcp.Ept(EPT_URL, origin, cache)
        self.cache = cache
        self.got = {}

    def points(self, tiles):
        import numpy as np
        acc = [[], [], [], []]
        for i, j in sorted(tiles):
            if (i, j) not in self.got:
                if not (self.cache / f"tile_{i}_{j}.npz").exists():
                    raise SystemExit(f"tile {i}_{j} is not in the cache: run `tiles` first")
                E, N, Z, C = self.ept.tile(i, j)
                m = (np.floor(E / 100.0) == i) & (np.floor(N / 100.0) == j)
                self.got[(i, j)] = (E[m], N[m], Z[m], C[m])
            for k in range(4):
                acc[k].append(self.got[(i, j)][k])
        return [np.concatenate(v) for v in acc]


def tiles_of(cs, ns, half, pad=3.0):
    """the 100 m tiles every cross-section (centre c, normal n, +-half, +-pad along) touches"""
    T = set()
    for c, n in zip(cs, ns):
        t = (n[1], -n[0])
        for u in [-half - pad + k * 2.0 for k in range(int((2 * half + 2 * pad) / 2.0) + 2)]:
            for al in (-pad, 0.0, pad):
                x, z = c[0] + n[0] * u + t[0] * al, c[1] + n[1] * u + t[1] * al
                T.add((int(math.floor(x / 100.0)), int(math.floor(z / 100.0))))
    return T


# ------------------------------------------------------------------------------------------------ a reference line


class Line:
    """a polyline (x, z) in the lidar / lap frame, by plan length s; closed = the lap (s wraps)"""

    def __init__(self, xz, closed=False):
        import numpy as np
        self.xz = np.asarray(xz, float)
        d = np.hypot(*np.diff(self.xz, axis=0).T)
        self.s = np.concatenate([[0.0], np.cumsum(d)])
        self.L = float(self.s[-1])
        self.closed = closed

    def _ss(self, s):
        import numpy as np
        s = np.asarray(s, float)
        return np.mod(s, self.L) if self.closed else np.clip(s, 0.0, self.L)

    def at(self, s):
        """the point at s; an open line is carried on straight past its ends (its first / last segment's heading)"""
        import numpy as np
        s = np.asarray(s, float)
        ss = self._ss(s)
        p = np.stack([np.interp(ss, self.s, self.xz[:, 0]), np.interp(ss, self.s, self.xz[:, 1])], -1)
        if not self.closed:
            t0 = self.xz[1] - self.xz[0]; t0 = t0 / np.linalg.norm(t0)
            t1 = self.xz[-1] - self.xz[-2]; t1 = t1 / np.linalg.norm(t1)
            p = p + np.minimum(s, 0.0)[..., None] * t0 + np.maximum(s - self.L, 0.0)[..., None] * t1
        return p

    def value(self, s, v):
        import numpy as np
        return np.interp(self._ss(s), self.s, np.asarray(v, float))

    def frame(self, s, h=5.0):
        """(centre, unit tangent, unit normal +u = left of travel): the tangent is the chord over +-h (= lidar_curb_trace's
        midline, 5 m)"""
        import numpy as np
        s = np.asarray(s, float)
        c = self.at(s)
        a, b = self.at(s - h), self.at(s + h)
        t = b - a
        t = t / np.linalg.norm(t, axis=-1, keepdims=True)
        n = np.stack([-t[..., 1], t[..., 0]], -1)
        return c, t, n


# ---------------------------------------------------------------------------------------- the cross-section engine

# the four faces' windows, metres of u (+ = left of the reference line's travel) [invented, per stretch: each wide
# enough for the road the ledgers' NAIP readings describe there (0079 rounds J / Q / R item 4), searched innermost first]
WIN_LAP_COLORADO = {"edge_min": 1.5, "right_max": 16.0, "left_max": 28.0, "median_max": 16.0, "cw_min": 4.0,
                    "cw_max": 18.0, "half": 32.0}
WIN_LAP_QUEBEC = {"edge_min": 1.5, "right_max": 16.0, "left_max": 38.0, "median_max": 16.0, "cw_min": 4.0,
                  "cw_max": 18.0, "half": 42.0}
WIN_ARM = {"edge_min": 1.5, "right_max": 16.0, "left_max": 18.0, "median_max": 10.0, "cw_min": 6.0,
           "cw_max": 22.0, "half": 36.0}
DROP_CAP_M = 0.06        # = lidar_curb_trace.DROP_CAP_M [invented]: a fall outward (no curb) scores up to this
INWARD_K = 0.0002        # [invented] metres of score per bin outward of a window's inner end (lidar_curb_trace's
                         # INWARD_COST, smaller: these windows are up to 36 m, round Q's were ~12 m)
KINK_BINS = (3, 8)       # [invented] the kink map: a straight line through the bins 3..8 off each side (0.75-2.0 m
                         # = FOOT_M; a raster cell spans +-1 bin), both read at the bin itself
FALL_GRADE = 0.10        # [invented] an outer edge with no curb: the ground's grade outward drops by this or more
FALL_SCALE_M = 0.5       # [invented] a fall's score is its grade change times this (0.12 -> 0.06 = DROP_CAP_M)
REFINE_BINS = 3          # [invented] a line's row is moved to its strongest bin within this many (0.75 m)
NOISE_M = 0.03           # [invented] every line's score less this: a line prefers a real face to the ground's ripple
GENTLE = 0.10            # [invented] a step is a curb only with its road side's line graded under this and its outer
                         # side's not falling outward faster (a fill's slope carried back to its top edge reads as a
                         # false step; a lawn rising behind a curb does not); a median face, a drop: both sides under it


def _sm_rows(H, k=5):
    """a nan-aware mean of k rows (lidar_curb_trace.SMOOTH_ROWS: +-1 m along)"""
    import numpy as np
    from scipy.ndimage import uniform_filter1d
    f = np.isfinite(H)
    a = uniform_filter1d(np.where(f, H, 0.0), k, axis=0, mode="nearest")
    w = uniform_filter1d(f.astype(float), k, axis=0, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(w > 0.3, a / w, np.nan)


def kink_map(H, bin_m):
    """per (row, bin): a straight line through the bins KINK_BINS off each side, each read at the bin: (K = the +u
    line's value minus the -u line's, the -u side's grade, the +u side's grade; dz per metre of +u). A curb face is a
    ridge of |K|; a steady crossfall or a slope reads K ~ 0 (unlike a difference of means)."""
    import numpy as np
    R, B = H.shape
    f = np.isfinite(H)
    y = np.where(f, H, 0.0)
    i = np.arange(B, dtype=float)[None, :]

    def cs(a):
        return np.concatenate([np.zeros((R, 1)), np.cumsum(a, 1)], 1)
    Cf, Cy, Ci, Cii, Cyi = cs(f.astype(float)), cs(y), cs(f * i), cs(f * i * i), cs(y * i)
    o0, o1 = KINK_BINS
    need = 0.6 * (o1 - o0 + 1)
    out = {}
    for side, (p, q) in (("lo", (-o1, -o0)), ("hi", (o0, o1))):
        b = np.arange(B)
        a0 = np.clip(b + p, 0, B); a1 = np.clip(b + q + 1, 0, B)
        n = Cf[:, a1] - Cf[:, a0]
        Sy = Cy[:, a1] - Cy[:, a0]
        Si = Ci[:, a1] - Ci[:, a0]
        Sii = Cii[:, a1] - Cii[:, a0]
        Syi = Cyi[:, a1] - Cyi[:, a0]
        bb = b[None, :].astype(float)
        Sx = Si - bb * n                                 # x = (i - b) in bins
        Sxx = Sii - 2 * bb * Si + bb * bb * n
        Sxy = Syi - bb * Sy
        with np.errstate(invalid="ignore", divide="ignore"):
            den = n * Sxx - Sx * Sx
            slope = (n * Sxy - Sx * Sy) / den
            icp = (Sy - slope * Sx) / n
        okk = (n >= need) & (np.abs(den) > 1e-9)
        out[side] = (np.where(okk, icp, np.nan), np.where(okk, slope / bin_m, np.nan))
    K = out["hi"][0] - out["lo"][0]
    return K, out["lo"][1], out["hi"][1]


def road_after(H, bin_m):
    """(rows, bins) bool: the SMOOTH_M of ground starting FOOT_M[0] past each bin is a carriageway: 75 % of its bins read,
    their rms about their own straight line under ROUGH_M, the line's slope under 8 % [invented]"""
    import numpy as np
    n = int(round(SMOOTH_M / bin_m))
    R, B = H.shape
    ok = np.zeros((R, B), bool)
    x = np.arange(n) * bin_m
    o = KINK_BINS[0]
    for b in range(B - n - o):
        Y = H[:, b + o:b + o + n]
        f = np.isfinite(Y)
        cnt = f.sum(1)
        Yz = np.where(f, Y, 0.0)
        Sx = (f * x).sum(1); Sy = Yz.sum(1); Sxx = (f * x * x).sum(1); Sxy = (Yz * x).sum(1); Syy = (Yz * Yz).sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            vx = Sxx - Sx * Sx / cnt
            slope = (Sxy - Sx * Sy / cnt) / vx
            res = (Syy - Sy * Sy / cnt) - slope * (Sxy - Sx * Sy / cnt)
            rms = np.sqrt(np.maximum(res, 0.0) / cnt)
        ok[:, b] = (cnt >= 0.75 * n) & (rms <= ROUGH_M) & (np.abs(slope) <= 0.08)
    return ok


def trace_faces(line: Line, S, E, N, Z, win):
    """lidar_curb_trace's raster along `line` at rows S, its rows smoothed (+-1 m), the kink map, and the four faces'
    Viterbi lines (lidar_curb_trace.viterbi), searched outward in order (module doc)"""
    import numpy as np
    import lidar_curb_trace as lct
    half = win["half"]
    lct.HALF_M = half
    c, t, n = line.frame(S)
    mid = np.stack([c[:, 0], np.zeros(len(S)), c[:, 1]], 1)
    L, H = lct.raster(S, mid, t, n, E, N, Z)
    bin_m = lct.BIN_M
    Hs = _sm_rows(H)
    K, g_lo, g_hi = kink_map(Hs, bin_m)
    nb = len(L)

    def ub(u):
        return int(np.clip(round((u + half) / bin_m), 0, nb - 1))

    def nbins(m):
        return int(round(m / bin_m))
    with np.errstate(invalid="ignore"):
        both = (np.abs(g_lo) <= GENTLE) & (np.abs(g_hi) <= GENTLE)
        curb_ok = {+1: (np.abs(g_lo) <= GENTLE) & (g_hi >= -GENTLE), -1: (np.abs(g_hi) <= GENTLE) & (-g_lo >= -GENTLE)}
    K0 = np.nan_to_num(K, nan=0.0)
    Kz = K0 * both
    idx = np.arange(nb)[None, :]

    def outer(side, cap=True):
        """an outer edge: a curb (the ground steps up outward, capped CAP_M) or, with no curb, a fall (the outward
        grade drops, FALL_SCALE_M x the drop, capped DROP_CAP_M): lidar_curb_trace's outer line, read off kinks"""
        rise = K0 * side * curb_ok[side]
        g_beyond = np.nan_to_num(g_hi if side > 0 else -g_lo, nan=0.0)
        g_in = np.nan_to_num(g_lo if side > 0 else -g_hi, nan=0.0)
        fall = np.clip(-(g_beyond - g_in) * FALL_SCALE_M, 0.0, DROP_CAP_M)
        return np.maximum(np.clip(rise, 0.0, CAP_M if cap else None), fall)

    def run(sc, lo, hi, inner, raw):
        """the Viterbi line, then each row moved to its own strongest bin within REFINE_BINS (the cap makes every
        curb alike for the line; the face is where the kink peaks)"""
        lo = np.clip(lo, 0, nb - 1); hi = np.clip(hi, 0, nb - 1); hi = np.maximum(hi, lo)
        sc = sc - NOISE_M - INWARD_K * np.abs(idx - inner[:, None])
        p = lct.viterbi(sc, lo, hi)
        out = p.copy()
        for i in range(len(p)):
            a0, a1 = max(lo[i], p[i] - REFINE_BINS), min(hi[i], p[i] + REFINE_BINS)
            if a1 >= a0:
                out[i] = a0 + int(np.argmax(raw[i, a0:a1 + 1]))
        return out
    R = len(S)
    full = np.ones(R, int)
    lo, hi = full * ub(-win["right_max"]), full * ub(-win["edge_min"])
    p_right = run(outer(-1), lo, hi, hi, outer(-1, cap=False))
    lo, hi = full * ub(win["edge_min"]), full * ub(win["left_max"])
    p_near = run(outer(+1), lo, hi, lo, outer(+1, cap=False))
    ra = road_after(H, bin_m)
    lo, hi = p_near + nbins(MEDIAN_MIN_M), p_near + nbins(win["median_max"])
    p_far = run(np.clip(-Kz, 0.0, CAP_M) * ra, lo, hi, np.clip(lo, 0, nb - 1), np.clip(-Kz, 0.0, None) * ra)
    lo, hi = p_far + nbins(win["cw_min"]), p_far + nbins(win["cw_max"])
    p_left = run(outer(+1), lo, hi, np.clip(lo, 0, nb - 1), outer(+1, cap=False))
    return {"L": L, "H": H, "D": K, "road_after": ra, "c": c, "t": t, "n": n,
            "u": {"right": L[p_right], "near": L[p_near], "far": L[p_far], "left": L[p_left]},
            "ra_far": ra[np.arange(R), np.clip(p_far, 0, nb - 1)]}


def _med(z, m):
    import numpy as np
    return (float(np.median(z[m])), int(m.sum())) if m.sum() >= 3 else (None, int(m.sum()))


def _fit(u, z, m, at, flat=False):
    """a straight line through the returns m (z on u), read at u = at: (value, grade, returns); under 4 returns or
    0.5 m of spread, or `flat` (a narrow median's top), their median with no grade (3 returns or more); else None"""
    import numpy as np
    k = int(m.sum())
    if flat or k < 4 or float(np.ptp(u[m])) < 0.5:
        return (float(np.median(z[m])), None, k) if k >= 3 else (None, None, k)
    A = np.stack([u[m] - at, np.ones(k)], 1)
    sol, *_ = np.linalg.lstsq(A, z[m], rcond=None)
    return float(sol[1]), float(sol[0]), k


def section_at(c, t, n, E, N, Z, faces_u, along):
    """the raw class-2 returns within +-along of the cross-section; at each face a straight line through the returns
    FOOT_M off each side, both read at the face: the step toward +u (the +u line minus the -u line) and each side's
    grade"""
    import numpy as np
    d = np.stack([E - c[0], N - c[1]], 1)
    a = d @ t
    m0 = np.abs(a) <= along
    u = d[m0] @ n
    z = Z[m0]
    out = {}
    nr, fr = faces_u.get("near"), faces_u.get("far")
    for k, uf in faces_u.items():
        lo_a, lo_b, hi_a, hi_b = uf - FOOT_M[1], uf - FOOT_M[0], uf + FOOT_M[0], uf + FOOT_M[1]
        flat_lo = flat_hi = False
        if nr is not None and fr is not None and fr > nr and k in ("near", "far"):
            # the median side of a median face stays on the median's top: TOP_IN_M .. FOOT_M[1] in from the face,
            # short of the other face by TOP_IN_M; narrower than 1 m, the top's median (no grade)
            w = fr - nr
            a = min(FOOT_M[0], 0.3 * w)
            if k == "near":
                hi_a, hi_b = uf + a, min(uf + FOOT_M[1], fr - a)
                flat_hi = hi_b - hi_a < 1.0
            else:
                lo_a, lo_b = max(uf - FOOT_M[1], nr + a), uf - a
                flat_lo = lo_b - lo_a < 1.0
        lo = _fit(u, z, (u >= lo_a) & (u <= lo_b), uf, flat_lo)
        hi = _fit(u, z, (u >= hi_a) & (u <= hi_b), uf, flat_hi)
        rise = None if lo[0] is None or hi[0] is None else hi[0] - lo[0]
        out[k] = {"u": float(uf), "z_minus": lo[0], "z_plus": hi[0], "g_minus": lo[1], "g_plus": hi[1],
                  "rise_plus": rise, "n": [lo[2], hi[2]]}
    return out, u, z


def classify(sec, u, z, ra_far, median_known=False):
    """one station: each face's kind and step, divided or not, the median's top and width, the carriageways.
    kinds: an outer edge is `curb` (steps up outward by STEP_M or more), `drop` (steps down outward by STEP_M or more),
    `fall` (no step; the outward grade drops by FALL_GRADE or more: the road's edge on a fill), or `none`; a median
    face is `curb` (the step onto the median, STEP_M or more) or `none`"""
    def r3(v):
        return None if v is None else round(float(v), 3)
    f = {}
    for k, outward in (("right", -1), ("near", +1), ("far", None), ("left", +1)):
        s = sec[k]
        rp = s["rise_plus"]
        if outward is None:                              # the median's far face: a step down toward +u
            step = None if rp is None else -rp
            gentle = all(g is None or abs(g) <= GENTLE for g in (s["g_minus"], s["g_plus"]))
            kind = "curb" if step is not None and step >= STEP_M and gentle else "none"
            g_in = g_out = None
        else:
            step = None if rp is None else outward * rp
            if outward > 0:
                g_in, g_out = s["g_minus"], s["g_plus"]
            else:
                g_in = None if s["g_plus"] is None else -s["g_plus"]
                g_out = None if s["g_minus"] is None else -s["g_minus"]
            kind = "none"
            road_ok = g_in is None or abs(g_in) <= GENTLE
            curb_ok = road_ok and (g_out is None or g_out >= -GENTLE)
            drop_ok = road_ok and (g_out is None or abs(g_out) <= GENTLE)
            if step is not None and step >= STEP_M and curb_ok:
                kind = "curb"
            elif step is not None and step <= -STEP_M and drop_ok:
                kind = "drop"
            elif g_in is not None and g_out is not None and g_out - g_in <= -FALL_GRADE:
                kind = "fall"
                step = None                              # a grade break: its two lines' offset is no step
        f[k] = {"u_m": round(s["u"], 2), "kind": kind, "step_m": r3(step),
                "y_minus_side": r3(s["z_minus"]), "y_plus_side": r3(s["z_plus"]),
                "grade_inward_side": r3(g_in), "grade_outward_side": r3(g_out), "returns": s["n"]}
        if outward is None:
            f[k].pop("grade_inward_side"); f[k].pop("grade_outward_side")
    near, far = f["near"], f["far"]
    gut_near = sec["near"]["z_minus"]                    # the near carriageway's line, read at the near face
    gut_far = sec["far"]["z_plus"]                       # the far carriageway's line, read at the far face
    divided = bool(near["kind"] == "curb" and far["kind"] == "curb" and bool(ra_far)
                   and far["u_m"] - near["u_m"] >= MEDIAN_MIN_M and gut_near is not None and gut_far is not None
                   and abs(gut_far - gut_near) <= ROAD_DY_M)
    rec = {"divided": divided}
    if divided:
        lo, hi = near["u_m"] + TOP_IN_M, far["u_m"] - TOP_IN_M
        if hi - lo < 0.25:
            mid_ = 0.5 * (near["u_m"] + far["u_m"])
            lo, hi = mid_ - 0.125, mid_ + 0.125
        top, tn = _med(z, (u >= lo) & (u <= hi))
        rec["median"] = {"near_face_u_m": near["u_m"], "far_face_u_m": far["u_m"],
                         "width_m": round(far["u_m"] - near["u_m"], 2), "top_y": r3(top), "top_returns": tn,
                         "top_over_near_side_m": r3(None if top is None else top - gut_near),
                         "top_over_far_side_m": r3(None if top is None else top - gut_far)}
        f["median_near"], f["median_far"], f["left_edge"] = near, far, f["left"]
    elif median_known:
        # the arms: OSM draws the street as two carriageways either side of a median, so the faces keep their names
        # (each with its own kind); the median's top and width only where both faces read as curbs
        f["median_near"], f["median_far"], f["left_edge"] = near, far, f["left"]
    else:
        f["left_edge"] = near
        rec["not_divided_candidates"] = {"median_far": far, "far_left_edge": f["left"]}
    f["right_edge"] = f["right"]
    for k in ("right", "near", "far", "left"):
        f.pop(k)
    rec["faces"] = f
    re_, le = f["right_edge"], f["left_edge"]
    rec["carriageways"] = {}
    if divided or median_known:
        if re_["kind"] != "none" and f["median_near"]["kind"] != "none":
            rec["carriageways"]["near_m"] = round(f["median_near"]["u_m"] - re_["u_m"], 2)
        if le["kind"] != "none" and f["median_far"]["kind"] != "none":
            rec["carriageways"]["far_m"] = round(le["u_m"] - f["median_far"]["u_m"], 2)
    elif re_["kind"] != "none" and le["kind"] != "none":
        rec["carriageways"]["one_m"] = round(le["u_m"] - re_["u_m"], 2)
    rec["real_width_m"] = (round(le["u_m"] - re_["u_m"], 2) if re_["kind"] != "none" and le["kind"] != "none"
                           else None)
    return rec


def stations_record(line, tr, S_rows, s_st, E, N, Z, built_w, built_label, s_label, median_known=False):
    """per station (rows of S_rows nearest each s_st): the faces from the raw returns, real minus built"""
    import numpy as np
    out = []
    for s in s_st:
        i = int(np.argmin(np.abs(S_rows - s)))
        c, t, n = tr["c"][i], tr["t"][i], tr["n"][i]
        fu = {k: float(v[i]) for k, v in tr["u"].items()}
        sec, u, z = section_at(c, t, n, E, N, Z, fu, STATION_M / 2.0)
        rec = classify(sec, u, z, tr["ra_far"][i], median_known)
        w = float(built_w(s))
        rec = {s_label: round(float(s), 2), "xz": [round(float(c[0]), 3), round(float(c[1]), 3)],
               "normal_xz": [round(float(n[0]), 4), round(float(n[1]), 4)], **rec}
        rec[built_label] = {"width_m": round(w, 3), "left_u_m": round(w / 2, 3), "right_u_m": round(-w / 2, 3)}
        for k, fc in rec["faces"].items():
            edge = -w / 2 if fc["u_m"] < 0 else w / 2
            fc["real_minus_built_m"] = round(fc["u_m"] - edge, 2)
        if rec["real_width_m"] is not None:
            rec["real_minus_built_width_m"] = round(rec["real_width_m"] - w, 2)
        out.append(rec)
    return out


def _stats(v):
    import numpy as np
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"median": round(float(np.median(v)), 2), "min": round(float(min(v)), 2), "max": round(float(max(v)), 2),
            "n": len(v)}


def per_50(stations, s_label, run_label, built_label):
    import numpy as np
    out = []
    if not stations:
        return out
    r0 = stations[0][run_label]
    nb = int(math.ceil((stations[-1][run_label] - r0 + 1e-6) / 50.0)) or 1
    for k in range(nb):
        g = [r for r in stations if r0 + 50 * k <= r[run_label] < r0 + 50 * (k + 1)]
        if not g:
            continue
        dv = [r for r in g if r["divided"]]
        rec = {"run_m": [round(r0 + 50 * k, 1), round(r0 + 50 * (k + 1), 1)],
               s_label: [g[0][s_label], g[-1][s_label]], "stations": len(g), "divided_stations": len(dv),
               "real_width_m": _stats([r["real_width_m"] for r in g]),
               "real_width_divided_m": _stats([r["real_width_m"] for r in dv]),
               "built_width_m": _stats([r[built_label]["width_m"] for r in g]),
               "real_minus_built_width_m": _stats([r.get("real_minus_built_width_m") for r in g]),
               "median_width_m": _stats([r["median"]["width_m"] for r in dv]),
               "median_top_over_near_side_m": _stats([r["median"]["top_over_near_side_m"] for r in dv]),
               "median_top_over_far_side_m": _stats([r["median"]["top_over_far_side_m"] for r in dv]),
               "carriageway_near_m": _stats([r["carriageways"].get("near_m") for r in g]),
               "carriageway_far_m": _stats([r["carriageways"].get("far_m") for r in g]),
               "faces": {}}
        for nm in ("right_edge", "median_near", "median_far", "left_edge"):
            fs = [r["faces"][nm] for r in g if nm in r["faces"]]
            if not fs:
                continue
            rec["faces"][nm] = {"u_m": _stats([f["u_m"] for f in fs if f["kind"] != "none"]),
                                "step_m": _stats([f["step_m"] for f in fs if f["kind"] != "none"]),
                                "kinds": {kd: sum(f["kind"] == kd for f in fs) for kd in ("curb", "drop", "none")},
                                "real_minus_built_m": _stats([f["real_minus_built_m"] for f in fs
                                                              if f["kind"] != "none"])}
        out.append(rec)
    return out


def qa_image(tr, path, title_rows=None):
    """a QA picture of the step map with the four lines (not a product)"""
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return
    D = np.nan_to_num(tr["D"], nan=0.0)
    v = np.clip(D / 0.15, -1, 1)
    img = np.zeros(D.shape + (3,), np.uint8)
    img[..., 0] = (np.clip(v, 0, 1) * 255).astype(np.uint8)
    img[..., 2] = (np.clip(-v, 0, 1) * 255).astype(np.uint8)
    img[..., 1] = (np.isfinite(tr["H"]) * 40).astype(np.uint8)
    L = tr["L"]
    cols = {"right": (255, 255, 0), "near": (0, 255, 0), "far": (0, 255, 255), "left": (255, 255, 255)}
    for k, col in cols.items():
        b = np.clip(np.round((tr["u"][k] - L[0]) / (L[1] - L[0])).astype(int), 0, len(L) - 1)
        img[np.arange(len(b)), b] = col
    z0 = int(np.argmin(np.abs(L)))
    img[:, z0] = (128, 128, 128)
    Image.fromarray(img[::-1]).resize((img.shape[1] * 2, img.shape[0])).save(path)


# --------------------------------------------------------------------------------------------- item 1: the lap


def item_lap(repo, lidar, outdir):
    import numpy as np
    cl = json.loads((repo / "tracks/sand-creek-lm/data/centerline.local.json").read_text())
    P = np.asarray(cl["points_xyz_m"], float)
    W = np.asarray(cl["widths_m"], float)
    assert np.allclose(P[0], P[-1]), "the lap is closed"
    lap = Line(P[:, [0, 2]], closed=True)
    sv = lap.s
    res = {"_doc": None, "frame": "the lap's: ENU local metres about centerline.local.json's origin (X east, Z north); "
           "heights = las z - origin.elev_m, the lap's y; +u = left of the lap's travel", "stretches": {}}
    for name, va, vb, win in (("colorado", 3205, 140, WIN_LAP_COLORADO), ("quebec", 1940, 2080, WIN_LAP_QUEBEC)):
        sa = float(sv[va])
        sb = float(sv[vb]) + (lap.L if vb < va else 0.0)
        s0 = math.ceil(sa / STATION_M) * STATION_M
        S = np.arange(s0 - 10.0, sb + 10.0 + 1e-9, ROW_M)          # 10 m past each end: the step map's rows settle
        st = np.arange(s0, sb + 1e-9, STATION_M)
        c, t, n = lap.frame(S)
        tiles = tiles_of(c, n, win["half"])
        E, N, Z, C = lidar.points(tiles)
        g = C == 2
        tr = trace_faces(lap, S, E[g], N[g], Z[g], win)
        qa_image(tr, outdir / f"qa_{name}.png")

        def bw(s):
            return float(lap.value(s, W))
        recs = stations_record(lap, tr, S, st, E[g], N[g], Z[g], bw, "built", "s_lap")
        for r, s in zip(recs, st):
            r["s_lap"] = round(float(s % lap.L), 2)
            r["run_m"] = round(float(s - s0), 2)
            k = int(np.searchsorted(sv, s % lap.L, side="right") - 1)
            r["v"] = k
        res["stretches"][name] = {
            "lap_vertices": [va, vb], "s_lap": [round(sa % lap.L, 2), round(sb % lap.L, 2)],
            "length_m": round(sb - sa, 1), "stations": len(recs), "tiles": sorted([list(x) for x in tiles]),
            "windows_m": win, "per_50m": per_50(recs, "s_lap", "run_m", "built"), "stations_list": recs}
        print(f"[lap] {name}: {len(recs)} stations, divided {sum(r['divided'] for r in recs)}", flush=True)
    return res


# ------------------------------------------------------------------------------------------ item 2: the arms


def item_arms(repo, lidar, outdir):
    import numpy as np
    import grid_reach
    cl = json.loads((repo / "tracks/sand-creek-lm/data/centerline.local.json").read_text())
    origin = cl["origin"]
    KX, KZ = grid_reach.frame_scale(origin)
    conns = {c["name"]: c for c in json.loads((repo / "tracks/sand-creek-lm/data/connectors.local.json")
                                              .read_text())["connectors"]}
    res = {"frame_scale": {"KX": KX, "KZ": KZ, "rule": "tools/grid_reach.frame_scale: a drawn (grid-frame) x, z times "
                           "KX, KZ is the lidar / lap frame's point at the same lon / lat"}, "pieces": {}}
    for name in ("grid_primary_78", "grid_primary_84#0#0"):
        Pd = np.asarray(conns[name]["points_xyz_m"], float)
        Wd = np.asarray(conns[name]["widths_m"], float)
        Pt = Pd[:, [0, 2]] * np.array([KX, KZ])
        true = Line(Pt)
        drawn = Line(Pd[:, [0, 2]])
        S = np.arange(-10.0, true.L + 10.0 + 1e-9, ROW_M)
        st = np.arange(0.0, true.L + 1e-9, STATION_M)
        c, t, n = true.frame(S)
        tiles = tiles_of(c, n, WIN_ARM["half"])
        E, N, Z, C = lidar.points(tiles)
        g = C == 2
        tr = trace_faces(true, S, E[g], N[g], Z[g], WIN_ARM)
        qa_image(tr, outdir / f"qa_{name.replace('#', '_')}.png")

        def bw(s):
            return float(true.value(s, Wd))
        recs = stations_record(true, tr, S, st, E[g], N[g], Z[g], bw, "built", "s_true", median_known=True)
        rows = []
        for k in range(len(Pd)):
            sk = float(true.s[k])
            # the faces' lines at this row's own s (interpolated between raster rows), the cross-section at the row
            ck, tk, nk = true.frame(np.array([sk]))
            ck, tk, nk = ck[0], tk[0], nk[0]
            fu = {kk: float(np.interp(sk, S, v)) for kk, v in tr["u"].items()}
            ra = bool(tr["ra_far"][int(np.argmin(np.abs(S - sk)))])
            sec, u, z = section_at(ck, tk, nk, E[g], N[g], Z[g], fu, STATION_M / 2.0)
            r = classify(sec, u, z, ra, median_known=True)
            _, td, nd = drawn.frame(np.array([float(drawn.s[k])]))
            td, nd = td[0], nd[0]
            off = Pt[k] - Pd[k, [0, 2]]

            def to_drawn(uu):
                """the face u (true frame, about the true point) carried into the drawn frame: the true face point
                divided by (KX, KZ), its lateral off the drawn point along the drawn normal"""
                p = (ck + nk * uu) / np.array([KX, KZ])
                return round(float(np.dot(p - Pd[k, [0, 2]], nd)), 2)

            def as_lidar(uu):
                """the same face against the drawn point read as a lidar point (no frame change)"""
                p = ck + nk * uu
                return round(float(np.dot(p - Pd[k, [0, 2]], nd)), 2)
            for fc in r["faces"].values():
                fc["u_drawn_m"] = to_drawn(fc["u_m"])
                fc["u_vs_drawn_point_as_lidar_m"] = as_lidar(fc["u_m"])
                edge = -Wd[k] / 2 if fc["u_m"] < 0 else Wd[k] / 2
                fc["real_minus_built_m"] = round(fc["u_m"] - edge, 2)
            if r.get("median"):
                md = r["median"]
                md["near_face_u_drawn_m"] = to_drawn(md["near_face_u_m"])
                md["far_face_u_drawn_m"] = to_drawn(md["far_face_u_m"])
                md["top_minus_drawn_y_m"] = None if md["top_y"] is None else round(md["top_y"] - float(Pd[k, 1]), 3)
            rows.append({"row": k, "drawn_xz": [round(float(Pd[k, 0]), 3), round(float(Pd[k, 2]), 3)],
                         "drawn_y": round(float(Pd[k, 1]), 3), "true_xz": [round(float(Pt[k, 0]), 3),
                                                                          round(float(Pt[k, 1]), 3)],
                         "offset_true_minus_drawn": {
                             "dx_m": round(float(off[0]), 3), "dz_m": round(float(off[1]), 3),
                             "dist_m": round(float(np.hypot(*off)), 3),
                             "along_m": round(float(np.dot(off, td)), 3), "u_m": round(float(np.dot(off, nd)), 3)},
                         "s_true": round(sk, 2), "normal_true_xz": [round(float(nk[0]), 4), round(float(nk[1]), 4)],
                         "built": {"width_m": float(Wd[k]), "left_u_m": float(Wd[k]) / 2,
                                   "right_u_m": -float(Wd[k]) / 2}, **r})
        res["pieces"][name] = {"rows": len(Pd), "true_length_m": round(true.L, 2), "drawn_length_m": round(drawn.L, 2),
                               "tiles": sorted([list(x) for x in tiles]), "windows_m": WIN_ARM,
                               "per_50m": per_50(recs, "s_true", "s_true", "built"), "stations_list": recs,
                               "rows_list": rows}
        print(f"[arms] {name}: {len(recs)} stations ({sum(r['divided'] for r in recs)} divided), {len(rows)} rows "
              f"({sum(r['divided'] for r in rows)} divided)", flush=True)
    return res


# ------------------------------------------------------------------------------------------ item 3: the bridge


def item_bridge(repo, lidar, outdir):
    import numpy as np
    from scripts.geometry.drive_test import WHEEL_HALF_TRACK
    cl = json.loads((repo / "tracks/sand-creek-lm/data/centerline.local.json").read_text())
    P = np.asarray(cl["points_xyz_m"], float)
    lap = Line(P[:, [0, 2]], closed=True)
    sv = lap.s
    # search the deck along the lap's centre from v1930 to v2000 (ledger 0098: the bridge at the pad's S end)
    s_a, s_b = float(sv[1930]), float(sv[2000])
    S = np.arange(math.floor(s_a), math.ceil(s_b) + 1e-9, BRIDGE_STEP_M)
    c, t, n = lap.frame(S)
    tiles = tiles_of(c, n, 4.0)
    E, N, Z, C = lidar.points(tiles)
    from scipy.spatial import cKDTree
    t2 = cKDTree(np.stack([E[C == 2], N[C == 2]], 1)); Z2 = Z[C == 2]
    t17 = cKDTree(np.stack([E[C == 17], N[C == 17]], 1)); Z17 = Z[C == 17]
    E17, N17 = E[C == 17], N[C == 17]

    def read(p):
        i2 = t2.query_ball_point(p, BRIDGE_R_M)
        i17 = t17.query_ball_point(p, BRIDGE_R_M)
        g = (round(float(np.median(Z2[i2])), 3) if len(i2) >= BRIDGE_MIN else None, len(i2))
        d = (round(float(np.median(Z17[i17])), 3) if len(i17) >= BRIDGE_MIN else None, len(i17))
        plane = None
        if len(i17) >= 6:
            A = np.stack([E17[i17] - p[0], N17[i17] - p[1], np.ones(len(i17))], 1)
            sol, *_ = np.linalg.lstsq(A, Z17[i17], rcond=None)
            r = Z17[i17] - A @ sol
            k = np.abs(r) <= max(0.05, 2.5 * float(np.std(r)))
            if k.sum() >= 6:
                sol, *_ = np.linalg.lstsq(A[k], Z17[i17][k], rcond=None)
            plane = round(float(sol[2]), 3)
        return g, d, plane
    first = [read(c[i]) for i in range(len(S))]
    on = [f[1][0] is not None for f in first]
    if not any(on):
        raise SystemExit("bridge: no class-17 deck on the lap's centre line")
    i0 = on.index(True)
    i1 = len(on) - 1 - on[::-1].index(True)
    d0, d1 = float(S[i0]), float(S[i1])
    S = np.arange(math.floor(d0 - APPROACH_M), math.ceil(d1 + APPROACH_M) + 1e-9, BRIDGE_STEP_M)
    c, t, n = lap.frame(S)
    tiles2 = tiles_of(c, n, 4.0)
    if not tiles2 <= tiles:
        E, N, Z, C = lidar.points(tiles | tiles2)
        t2 = cKDTree(np.stack([E[C == 2], N[C == 2]], 1)); Z2 = Z[C == 2]
        t17 = cKDTree(np.stack([E[C == 17], N[C == 17]], 1)); Z17 = Z[C == 17]
        E17, N17 = E[C == 17], N[C == 17]
    by = lap.value(S, P[:, 1])
    rows = []
    for i, s in enumerate(S):
        rec = {"s_lap": round(float(s % lap.L), 2), "v": int(np.searchsorted(sv, s % lap.L, side="right") - 1),
               "built_y": round(float(by[i]), 3), "on_deck_centre": bool(d0 <= s <= d1), "paths": {}}
        for nm, uu in (("right_wheel", -WHEEL_HALF_TRACK), ("centre", 0.0), ("left_wheel", WHEEL_HALF_TRACK)):
            p = c[i] + n[i] * uu
            g, d, plane = read(p)
            real, src = (d[0], "class17") if d[0] is not None else ((g[0], "class2") if g[0] is not None else (None, None))
            rec["paths"][nm] = {"u_m": uu, "xz": [round(float(p[0]), 3), round(float(p[1]), 3)],
                                "class17_y": d[0], "class17_returns": d[1], "class17_plane_y": plane,
                                "class2_y": g[0], "class2_returns": g[1], "real_y": real, "real_from": src,
                                "built_minus_real_m": None if real is None else round(float(by[i]) - real, 3)}
        rows.append(rec)
    # the pad's S row (data/pads.built.json, sandcreek_quebec rows[1]): the deck under each of its points
    pads = json.loads((repo / "tracks/sand-creek-lm/data/pads.built.json").read_text())
    plist = pads if isinstance(pads, list) else pads.get("pads", list(pads.values()))
    pad = next(p for p in plist if isinstance(p, dict) and p.get("id") == "sandcreek_quebec")
    tp = {(int(math.floor(x / 100.0)), int(math.floor(z / 100.0))) for row in pad["rows"] for x, z, _ in row}
    if not tp <= (tiles | tiles2):
        E, N, Z, C = lidar.points(tiles | tiles2 | tp)
        t2 = cKDTree(np.stack([E[C == 2], N[C == 2]], 1)); Z2 = Z[C == 2]
        t17 = cKDTree(np.stack([E[C == 17], N[C == 17]], 1)); Z17 = Z[C == 17]
        E17, N17 = E[C == 17], N[C == 17]
    pad_rows = []
    for ri, row in enumerate(pad["rows"]):
        pts = []
        for x, z, y in row:
            g, d, plane = read(np.array([x, z]))
            real = d[0] if d[0] is not None else g[0]
            pts.append({"xz": [x, z], "built_y": y, "class17_y": d[0], "class17_returns": d[1], "class2_y": g[0],
                        "class2_returns": g[1], "built_minus_real_m": None if real is None else round(y - real, 3),
                        "real_from": "class17" if d[0] is not None else ("class2" if g[0] is not None else None)})
        pad_rows.append({"row": ri, "points": pts})
    dk = [r for r in rows if r["on_deck_centre"]]
    summ = {}
    for nm in ("right_wheel", "centre", "left_wheel"):
        v = [r["paths"][nm]["class17_y"] for r in dk if r["paths"][nm]["class17_y"] is not None]
        bmr = [r["paths"][nm]["built_minus_real_m"] for r in dk if r["paths"][nm]["real_from"] == "class17"]
        summ[nm] = {"deck_y": _stats(v), "built_minus_deck_m": _stats(bmr)}
    print(f"[bridge] deck on the lap's centre s {d0 % lap.L:.1f} .. {d1 % lap.L:.1f} ({d1 - d0:.0f} m); "
          f"{len(rows)} rows", flush=True)
    return {"deck_on_centre_s_lap": [round(d0 % lap.L, 2), round(d1 % lap.L, 2)], "deck_length_m": round(d1 - d0, 1),
            "approach_m": APPROACH_M, "wheel_half_track_m": WHEEL_HALF_TRACK, "radius_m": BRIDGE_R_M,
            "min_returns": BRIDGE_MIN, "tiles": sorted([list(x) for x in (tiles | tiles2)]), "summary_on_deck": summ,
            "rows": rows, "pad_sandcreek_quebec_rows": pad_rows}


def cmd_measure(a):
    repo = Path(a.repo).resolve()
    repo_paths(repo)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    origin = json.loads((repo / "tracks/sand-creek-lm/data/centerline.local.json").read_text())["origin"]
    lidar = Lidar(Path(a.cache), origin)
    only = set((a.only or "lap,arms,bridge").split(","))
    common = {"lidar": "USGS CO_DRCOG_2_2020 (" + EPT_URL + "), classes 2 (ground) and 17 (bridge deck), through "
              "tools/lidar_connector_profile.py's tile cache and reader", "script": "roads_lidar_g10.py",
              "constants": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, tuple))}}
    face_doc = ("faces: right_edge, median_near, median_far, left_edge (a station that is not divided has "
                "right_edge and left_edge, its far-face candidates under not_divided_candidates), each {u_m: + = left "
                "of travel, kind: curb | drop | fall | none (outer edges; a median face is curb | none), step_m (curb / "
                "drop: up / down outward; a median face: onto the median), y_minus_side / y_plus_side (the two side "
                "lines read at the face, heights in the lap's y), grade_inward_side / grade_outward_side, returns, "
                "real_minus_built_m (u minus the built edge on that side)}. A `none` face's u is where the trace ran, "
                "not a measurement. median: {near_face_u_m, far_face_u_m, width_m (face to face), top_y, "
                "top_over_near_side_m / top_over_far_side_m}; carriageways: near_m / far_m (divided) or one_m; "
                "real_width_m: outer edge to outer edge (both measured); per_50m: median / min / max / n.")
    if "lap" in only:
        r = item_lap(repo, lidar, out)
        r["_doc"] = ("Item 1 (ledgers 0079 round R item 4, 0098): Colorado Blvd (lap v3205 -> v140) and the lap's "
                     "Quebec St (v1940 -> v2080) off the 2020 lidar, every 2.5 m of the lap's s (s_lap: plan metres "
                     "along centerline.local.json from v0; run_m: from the stretch's first station; v: the lap vertex "
                     "at or before it). built: the lap's widths_m, centred (left_u_m = +w/2, right_u_m = -w/2). "
                     + face_doc + " Method and every [invented] constant: roads_lidar_g10.py.")
        (out / "lap_colorado_quebec.lidar.json").write_text(json.dumps({**common, **r}, indent=None))
    if "arms" in only:
        r = item_arms(repo, lidar, out)
        r["_doc"] = ("Item 2 (ledger 0098 'quebec_median': the median between the Northfield Quebec arms): "
                     "grid_primary_78 and grid_primary_84#0#0 of tracks/sand-creek-lm/data/connectors.local.json "
                     "(drawn in the grid's sphere frame), each read along its TRUE line (each drawn x, z times KX, KZ). "
                     "+u = left of the arm's travel (78 runs from the I-70 end to the sandcreek_quebec pad, 84#0#0 "
                     "from the pad north): the median is on the left of both. stations_list: every 2.5 m of the true "
                     "line (s_true). rows_list: per drawn row: drawn_xz / drawn_y (the built point), true_xz, "
                     "offset_true_minus_drawn (dx, dz, dist; along / u in the drawn piece's frame), the station read "
                     "at the row, and for every face u_drawn_m (the face's true-frame point divided by KX, KZ, its "
                     "lateral off the drawn point along the drawn normal: where to build it on the drawn line) and "
                     "u_vs_drawn_point_as_lidar_m (the same face against the drawn point read as a lidar point: the "
                     "4.6 m frame gap included); median.top_minus_drawn_y_m: the real top minus the drawn row's y. "
                     "built: the drawn widths_m, centred. " + face_doc)
        (out / "quebec_arms_median.lidar.json").write_text(json.dumps({**common, **r}, indent=None))
    if "bridge" in only:
        r = item_bridge(repo, lidar, out)
        r["_doc"] = ("Item 3 (ledger 0098 'the lap's height on the Quebec St bridge over Sand Creek'): along the lap "
                     "every 1 m (s_lap) from APPROACH_M before the class-17 deck's first reading on the lap's centre "
                     "line to APPROACH_M past its last, at the centre line and both wheel paths (u = -+ "
                     "drive_test.WHEEL_HALF_TRACK). Each path: the median of the class-17 returns within 1.0 m "
                     "(3 or more; lidar_connector_profile's rule) and a plane through them (6 or more), the class-2 "
                     "median likewise; real_y = the deck where read, else the ground; built_y = centerline.local.json "
                     "y (the centre line's, used for all three paths); built_minus_real_m. pad_sandcreek_quebec_rows: "
                     "data/pads.built.json's rows of the pad (row 1 = its S row on the deck), each point's deck / "
                     "ground under it and built minus real.")
        (out / "quebec_bridge_deck.lidar.json").write_text(json.dumps({**common, **r}, indent=None))
    return 0


if __name__ == "__main__":
    sys.exit(main())

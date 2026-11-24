"""High Plains round 5 (ledger 0097, "Still to do (round 5)"): what NAIP could not settle, read off the 2018 lidar.

    python -I hp_r5_lidar.py plan    <repo> <DL dir> [--reuse <earlier DL dir>]   # ept.json, hierarchy, HEADs: the nodes + bytes
    python -I hp_r5_lidar.py fetch   <DL dir>                                       # the planned nodes not already on disk
    python -I hp_r5_lidar.py extract <repo> <DL dir> <points.npz> [--reuse <dir>]   # every return in the spots, track frame
    python -I hp_r5_lidar.py measure <repo> <points.npz> <out dir>                  # the three items' JSON

The lidar: USGS 3DEP CO_Eastern_B3_2018 (public domain), its EPT on the USGS lidar bucket (EPSG:3857 XY, NAVD88 Z), the
same dataset and octree round 3's roofs read (hp_paddock_ept.py). plan / fetch reach the network; extract and measure do
not. A node an earlier download already holds (same key, same bytes) is read from there, not fetched again.

THE FRAME. Every return goes 3857 -> lon / lat (pyproj) -> the track frame the author uses (scripts.geometry.projection.
_meters_per_degree about data/centerline.local.json's origin: x = E, z = N metres), exactly as round 4's scripts and
tools/lidar_strip.py map lon / lat. The lines read against: the West lap as built (data/centerline.local.json, its widths)
and the north loop's own line (source/full/connectors.full.json, its widths; "own s" is that line's arc length, the s of
round 4's kerbs and stripes; "row s" is north_loop.json's rows', OSM's, every 2 m, the s of round 4's carried rows).

THE SPOTS (each a box in the track frame, SPOT_PAD_M round the pieces of line it holds):
  fork       the north loop own s 0-45 and the West lap s 2,670-2,770 (the fork's mouth, R row s 0-19)
  merge      the north loop own s 940-995 and the West lap s 2,800-2,890 (the merge: both corners, the T13 kerb, R row
             s 988-1001 and L row s 996-1001)
  l254       the north loop own s 230-285 (L row s 254-260)
  stripe372  the north loop own s 355-420 (round 4's blue / yellow stripe L own s 372-401)
  stripe648  the north loop own s 630-700 (round 4's blue / yellow stripe L own s 648-682)

What measure reads, and how, is in measure()'s own docstring and the README beside this file.
"""
from __future__ import annotations

import json
import math
import sys
import time
import urllib.request
from pathlib import Path

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_Eastern_B3_2018/ept.json"
BASE = EPT.rsplit("/", 1)[0]
UA = {"User-Agent": "airoso-fetch/1.0"}
T = Path("tracks/high-plains-lm")
SPOT_PAD_M = 22.0      # [invented] the box reaches this far past the line pieces (a lane half-width + 16 m of verge)
SPOTS = {               # name: ([(line, s0, s1)], what it is for)
    "fork": ([("north", 0.0, 45.0), ("west", 2670.0, 2770.0)], "the fork's mouth (R row s 0-19)"),
    "merge": ([("north", 940.0, 995.2), ("west", 2800.0, 2890.0)], "the merge: the east fillet behind the T13 kerb, R row s 988-1001, L row s 996-1001"),
    "l254": ([("north", 230.0, 285.0)], "L row s 254-260"),
    "stripe372": ([("north", 355.0, 420.0)], "the blue / yellow stripe L own s 372-401"),
    "stripe648": ([("north", 630.0, 700.0)], "the blue / yellow stripe L own s 648-682"),
}
NOISE = (7, 18)


# ---------------------------------------------------------------------------------------------------------------- frame
def mpd(repo: Path, lat0: float):
    sys.path.insert(0, str(repo))
    from scripts.geometry.projection import _meters_per_degree
    return _meters_per_degree(lat0)


class Line:
    """a polyline in the track frame (x = E, z = N) with widths: arc length, frames, projection"""

    def __init__(self, pts_xyz, widths):
        import numpy as np
        P = np.asarray(pts_xyz, dtype=float)
        self.x, self.y, self.z = P[:, 0], P[:, 1], P[:, 2]
        self.w = np.asarray(widths, dtype=float)
        self.s = np.r_[0.0, np.cumsum(np.hypot(np.diff(self.x), np.diff(self.z)))]

    def at(self, s):
        """(x, z, tx, tz, half-width) at arc length s (arrays)"""
        import numpy as np
        s = np.asarray(s, dtype=float)
        j = np.clip(np.searchsorted(self.s, s, side="right") - 1, 0, len(self.s) - 2)
        L = self.s[j + 1] - self.s[j]
        f = np.clip((s - self.s[j]) / np.where(L > 0, L, 1.0), -1.0, 2.0)
        x = self.x[j] + (self.x[j + 1] - self.x[j]) * f
        z = self.z[j] + (self.z[j + 1] - self.z[j]) * f
        # the tangent over +-2 m (a smooth frame across the polyline's vertices)
        a, b = np.clip(s - 2.0, 0, self.s[-1]), np.clip(s + 2.0, 0, self.s[-1])
        xa, za = np.interp(a, self.s, self.x), np.interp(a, self.s, self.z)
        xb, zb = np.interp(b, self.s, self.x), np.interp(b, self.s, self.z)
        tx, tz = xb - xa, zb - za
        n = np.hypot(tx, tz)
        return x, z, tx / n, tz / n, np.interp(s, self.s, self.w) / 2.0

    def project(self, X, Z, s_lo=None, s_hi=None):
        """(s, lateral + = left of travel) of points, nearest segment within [s_lo, s_hi]"""
        import numpy as np
        X = np.asarray(X, dtype=float); Z = np.asarray(Z, dtype=float)
        j0 = 0 if s_lo is None else max(0, int(np.searchsorted(self.s, s_lo)) - 2)
        j1 = len(self.s) - 1 if s_hi is None else min(len(self.s) - 1, int(np.searchsorted(self.s, s_hi)) + 2)
        best_d = np.full(X.shape, np.inf); best_s = np.zeros(X.shape); best_l = np.zeros(X.shape)
        for j in range(j0, j1):
            ax, az, bx, bz = self.x[j], self.z[j], self.x[j + 1], self.z[j + 1]
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            if L2 <= 0:
                continue
            t = np.clip(((X - ax) * dx + (Z - az) * dz) / L2, 0.0, 1.0)
            d = (X - ax - dx * t) ** 2 + (Z - az - dz * t) ** 2
            m = d < best_d
            L = math.sqrt(L2)
            best_d[m] = d[m]
            best_s[m] = self.s[j] + t[m] * L
            best_l[m] = (((X - ax) * -dz + (Z - az) * dx) / L)[m]
        return best_s, best_l


def lines(repo: Path):
    P = repo / T
    west = json.loads((P / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    north = json.loads((P / "source" / "full" / "connectors.full.json").read_text(encoding="utf-8"))["connectors"][0]
    return west["origin"], {"west": Line(west["points_xyz_m"], west["widths_m"]),
                            "north": Line(north["points_xyz_m"], north["widths_m"])}


def spot_boxes(repo: Path):
    """{spot: (x0, z0, x1, z1)} in the track frame"""
    import numpy as np
    _o, L = lines(repo)
    out = {}
    for name, (pieces, _why) in SPOTS.items():
        xs, zs = [], []
        for ln, s0, s1 in pieces:
            s = np.arange(s0, min(s1, L[ln].s[-1]) + 1e-9, 1.0)
            x, z, *_r = L[ln].at(s)
            xs += list(x); zs += list(z)
        out[name] = (min(xs) - SPOT_PAD_M, min(zs) - SPOT_PAD_M, max(xs) + SPOT_PAD_M, max(zs) + SPOT_PAD_M)
    return out


# ---------------------------------------------------------------------------------------------------- plan / fetch / read
def _get(url, method="GET"):
    # the repo's TLS rule (scripts/tls.py, tests/net/test_https_everywhere.py): one verifying context for every fetch. Added
    # on the Mac when the directory was brought into the repo (ledger 0097 round 5); the G10's own run had urllib's default
    sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
    from scripts.tls import https_context
    for k in range(5):
        try:
            req = urllib.request.Request(url, headers=UA, method=method)
            with urllib.request.urlopen(req, timeout=120, context=https_context()) as r:
                return r.read() if method == "GET" else int(r.headers.get("Content-Length", 0))
        except Exception:                       # noqa: BLE001 (backoff on any transport error, then give up)
            if k == 4:
                raise
            time.sleep(2 ** k)


def boxes_3857(repo: Path):
    from pyproj import Transformer
    origin, _L = lines(repo)
    m_lon, m_lat = mpd(repo, float(origin["lat"]))
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    out = {}
    for name, (x0, z0, x1, z1) in spot_boxes(repo).items():
        xs, ys = to_merc.transform([origin["lon"] + x / m_lon for x in (x0, x1, x0, x1)],
                                   [origin["lat"] + z / m_lat for z in (z0, z0, z1, z1)])
        out[name] = (min(xs), min(ys), max(xs), max(ys))
    return out


def plan(repo: Path, dl: Path, reuse: Path | None):
    boxes = boxes_3857(repo)
    dl.mkdir(parents=True, exist_ok=True)
    ept = json.loads(_get(EPT))
    (dl / "ept.json").write_text(json.dumps(ept))
    b = ept["bounds"]
    hier = {}

    def h_of(key):
        if key not in hier:
            f = (reuse / "ept-hierarchy" / f"{key}.json") if reuse else None
            if f is not None and f.exists():
                hier[key] = json.loads(f.read_text())
            else:
                hier[key] = json.loads(_get(f"{BASE}/ept-hierarchy/{key}.json"))
                (dl / "ept-hierarchy").mkdir(exist_ok=True)
                (dl / "ept-hierarchy" / f"{key}.json").write_text(json.dumps(hier[key]))
        return hier[key]
    keys = []

    def walk(d, x, y, z, h):
        kk = f"{d}-{x}-{y}-{z}"
        if kk not in h:
            return
        if h[kk] == -1:
            h = h_of(kk)
        sz = (b[3] - b[0]) / 2 ** d
        nx0, ny0 = b[0] + x * sz, b[1] + y * sz
        if not any(nx0 <= q[2] and nx0 + sz >= q[0] and ny0 <= q[3] and ny0 + sz >= q[1] for q in boxes.values()):
            return
        if h[kk] > 0:
            keys.append((kk, h[kk]))
        for a in (0, 1):
            for c in (0, 1):
                for e in (0, 1):
                    walk(d + 1, 2 * x + a, 2 * y + c, 2 * z + e, h)
    walk(0, 0, 0, 0, h_of("0-0-0-0"))
    nodes = []
    for kk, n in keys:
        sz = _get(f"{BASE}/ept-data/{kk}.laz", "HEAD")
        old = (reuse / "ept-data" / f"{kk}.laz") if reuse else None
        nodes.append({"key": kk, "points": n, "bytes": sz,
                      "reuse": bool(old is not None and old.exists() and old.stat().st_size == sz)})
    new = [q for q in nodes if not q["reuse"]]
    rec = {"ept": EPT, "boxes_3857": boxes, "spot_pad_m": SPOT_PAD_M, "reuse_dir": str(reuse) if reuse else None,
           "nodes": nodes, "laz_bytes_all": sum(q["bytes"] for q in nodes),
           "laz_bytes_to_fetch": sum(q["bytes"] for q in new), "nodes_to_fetch": len(new)}
    (dl / "plan.json").write_text(json.dumps(rec, indent=1))
    print(f"[plan] {len(nodes)} nodes, {sum(q['points'] for q in nodes):,} points, {rec['laz_bytes_all']:,} B laz; "
          f"{len(nodes) - len(new)} already on disk; to fetch {len(new)} nodes, {rec['laz_bytes_to_fetch']:,} B")


def fetch(dl: Path):
    p = json.loads((dl / "plan.json").read_text())
    (dl / "ept-data").mkdir(exist_ok=True)
    got = 0
    for q in p["nodes"]:
        if q["reuse"]:
            continue
        out = dl / "ept-data" / f"{q['key']}.laz"
        if out.exists() and out.stat().st_size == q["bytes"]:
            continue
        data = _get(f"{BASE}/ept-data/{q['key']}.laz")
        if len(data) != q["bytes"]:
            raise SystemExit(f"[fetch] {q['key']}: {len(data)} B, the plan said {q['bytes']}")
        out.write_bytes(data)
        got += len(data)
    print(f"[fetch] {p['nodes_to_fetch']} nodes in {dl / 'ept-data'} ({got:,} B fetched now)")


def extract(repo: Path, dl: Path, out: Path, reuse: Path | None):
    """every return (noise classes dropped) inside a spot's box, in the track frame: x E, z N, h NAVD88 m, i intensity,
    c class, rn / nr return number / count, ps the flight line (PointSourceId), spot the spot's index (SPOTS' order)"""
    import laspy
    import numpy as np
    from pyproj import Transformer
    origin, _L = lines(repo)
    m_lon, m_lat = mpd(repo, float(origin["lat"]))
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    p = json.loads((dl / "plan.json").read_text())
    names = list(SPOTS)
    boxes = spot_boxes(repo)
    cols = {k: [] for k in ("x", "z", "h", "i", "c", "rn", "nr", "ps", "spot")}
    n_read = 0
    for q in p["nodes"]:
        f = (reuse if q["reuse"] else dl) / "ept-data" / f"{q['key']}.laz"
        with laspy.open(f) as fh:
            for ch in fh.chunk_iterator(200_000):
                n_read += len(ch)
                lon, lat = to_ll.transform(np.asarray(ch.x), np.asarray(ch.y))
                x = (lon - origin["lon"]) * m_lon
                z = (lat - origin["lat"]) * m_lat
                cl = np.asarray(ch.classification)
                for k, nm in enumerate(names):
                    x0, z0, x1, z1 = boxes[nm]
                    m = (x >= x0) & (x <= x1) & (z >= z0) & (z <= z1) & ~np.isin(cl, NOISE)
                    if not m.any():
                        continue
                    cols["x"].append(x[m]); cols["z"].append(z[m]); cols["h"].append(np.asarray(ch.z)[m])
                    cols["i"].append(np.asarray(ch.intensity)[m]); cols["c"].append(cl[m])
                    cols["rn"].append(np.asarray(ch.return_number)[m]); cols["nr"].append(np.asarray(ch.number_of_returns)[m])
                    cols["ps"].append(np.asarray(ch.point_source_id)[m]); cols["spot"].append(np.full(int(m.sum()), k))
    arr = {k: np.concatenate(v) for k, v in cols.items()}
    np.savez_compressed(out, **arr, spots=np.array(names), boxes=np.array([boxes[n] for n in names]),
                        origin=np.array([origin["lon"], origin["lat"], origin["elev_m"]]))
    print(f"[extract] {n_read:,} returns read, {len(arr['x']):,} kept -> {out}")
    for k, nm in enumerate(names):
        m = arr["spot"] == k
        x0, z0, x1, z1 = boxes[nm]
        A = (x1 - x0) * (z1 - z0)
        print(f"[extract]   {nm}: {int(m.sum()):,} returns over {A:,.0f} m2 ({m.sum() / A:.2f} /m2), class 2 "
              f"{int((arr['c'][m] == 2).sum()):,}, flight lines {sorted(set(arr['ps'][m].tolist()))}")


# -------------------------------------------------------------------------------------------------------------- readers
W_M = 1.2            # [invented] the step reader's window each side of a candidate edge (QL2 here: ~2 returns / m2)
ALONG_M = 1.5        # [invented] a station along a line reads the returns within this of it, along
GRID_M = 0.05        # the candidate edges' spacing
SCORE_MIN = 1.6      # [invented] of 2.0 (the dark share inside + the bright share outside): a reading below is not kept
N_MIN = 3            # [invented] returns on each side of a candidate edge
T_SENS = (0.8, 1.25)  # [invented] every reading is repeated at these multiples of its threshold; the spread is reported
HALF_ARC_M = 0.75    # [invented] a polar ray reads the returns within this of it, across
ARC_MID = 0.7        # [invented] (tools/mouth_radii.py's) the middle share of a candidate arc that is scored
R_GRID = (5.0, 60.0, 0.25)   # [invented] the corner radii tried (mouth_radii's ran to 20 m; the east corner's best sat there)
STRIPE_MIN_M = 0.5   # [invented] a stripe's core: its first bright return stands this far inside the edge line either side
TAPER_MIN_M = 0.2    # [invented] ... and its tapered ends run on while it stands this far inside
BOBSLED, LADDER = 132189631, 289314483
FORK, TURN, MERGE = 1454637759, 1454637958, 1454637805


def step_edge(u, dark, lo, hi, w=W_M):
    """the dark -> bright step along u (the dark side at smaller u): (edge, score, n dark side, n bright side, gap) or
    None. score = the dark share over [e - w, e) + the bright share over [e, e + w), on a GRID_M lattice of e in [lo, hi];
    the edge is the middle of the innermost plateau of the best score (the plateau spans the gap between the last dark
    and the first bright return there: its width is reported as gap)"""
    import numpy as np
    best, run = -1.0, []
    for e in np.arange(lo, hi + 1e-9, GRID_M):
        a = (u >= e - w) & (u < e)
        b = (u >= e) & (u < e + w)
        if a.sum() < N_MIN or b.sum() < N_MIN:
            continue
        sc = float(dark[a].mean() + (~dark[b]).mean())
        if sc > best + 1e-9:
            best, run = sc, [e]
        elif abs(sc - best) <= 1e-9 and run and abs(e - run[-1] - GRID_M) < 1e-6:
            run.append(e)
    if not run:
        return None
    e = float((run[0] + run[-1]) / 2.0)
    a = (u >= e - w) & (u < e)
    b = (u >= e) & (u < e + w)
    return {"edge": round(e, 2), "score": round(best, 2), "n_in": int(a.sum()), "n_out": int(b.sum()),
            "gap": round(float(run[-1] - run[0]), 2)}


def lonlat(E, N, origin, mlon, mlat):
    return [round(origin["lon"] + float(E) / mlon, 8), round(origin["lat"] + float(N) / mlat, 8)]


def osm_line(repo: Path, origin, mlon, mlat):
    """the north loop's OSM line, as measure_north.py builds it (the rows' line: north_loop.json's left_m / right_m are
    metres off it): every 1 m of row s, tangents over +-5 m. Returns (s, x, z, tx, tz)"""
    import numpy as np
    osm = json.loads((repo / T / "source" / "full" / "osm_full_course.json").read_text(encoding="utf-8"))
    ways = {e["id"]: e for e in osm["elements"]}

    def piece(wid, a, b):
        e = ways[wid]
        i, j = e["nodes"].index(a), e["nodes"].index(b)
        return [(g["lon"], g["lat"]) for g in e["geometry"][i:j + 1]]
    ll = piece(BOBSLED, FORK, TURN) + piece(LADDER, TURN, MERGE)[1:]
    xy = np.array([((lo - origin["lon"]) * mlon, (la - origin["lat"]) * mlat) for lo, la in ll])
    st = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    s = np.arange(0, st[-1] + 1e-9, 1.0)
    x = np.interp(s, st, xy[:, 0]); z = np.interp(s, st, xy[:, 1])
    k = 5
    tx = np.array([x[min(i + k, len(s) - 1)] - x[max(i - k, 0)] for i in range(len(s))])
    tz = np.array([z[min(i + k, len(s) - 1)] - z[max(i - k, 0)] for i in range(len(s))])
    L_ = np.hypot(tx, tz)
    return s, x, z, tx / L_, tz / L_


class Strip:
    """one side of one line over one spot: every return's (s, o), o metres OUTWARD past the built lane edge"""

    def __init__(self, pts, line: Line, side: int, s0: float, s1: float):
        import numpy as np
        self.line, self.side = line, side
        s, lat = line.project(pts["x"], pts["z"], s0 - 10.0, s1 + 10.0)
        hw = np.interp(s, line.s, line.w) / 2.0
        self.s, self.o, self.i = s, side * lat - hw, pts["i"]
        self.h = pts["h"]

    def threshold(self, s0, s1):
        """sqrt(asphalt x what borders it): the median intensity 1.5-4.5 m inside the edge (the lane) and 0.3-1.5 m past it"""
        import numpy as np
        m = (self.s >= s0) & (self.s <= s1)
        a = float(np.median(self.i[m & (self.o > -4.5) & (self.o < -1.5)]))
        b = float(np.median(self.i[m & (self.o > 0.3) & (self.o < 1.5)]))
        return math.sqrt(a * b), a, b

    def read(self, s_at, lo, hi, T, along=ALONG_M):
        import numpy as np
        m = (np.abs(self.s - s_at) <= along) & (self.o >= lo - W_M) & (self.o <= hi + W_M)
        u, I = self.o[m], self.i[m]
        r = step_edge(u, I < T, lo, hi)
        if r is None:
            return None
        sens = [step_edge(u, I < T * f, lo, hi) for f in T_SENS]
        r["t_sens_m"] = round(max(abs(q["edge"] - r["edge"]) if q else 99.0 for q in sens), 2)
        return r

    def point(self, s_at, o):
        """(E, N) of the point o past the lane edge at s"""
        x, z, tx, tz, hw = self.line.at(s_at)
        lat = self.side * (hw + o)
        return float(x + (-tz) * lat), float(z + tx * lat)


def polar_read(pts, O, th0, th1, dth, T, r_lo, r_hi):
    """rays from O (in the grass wedge of a corner): on each, the step from the grass (bright, nearer O) to the asphalt
    (dark, farther): [(theta deg, r, reading)]"""
    import numpy as np
    dx, dz = pts["x"] - O[0], pts["z"] - O[1]
    rr = np.hypot(dx, dz)
    ang = np.degrees(np.arctan2(dz, dx)) % 360.0
    out = []
    for th in np.arange(th0, th1 + 1e-9, dth):
        da = (ang - th % 360.0 + 180.0) % 360.0 - 180.0
        m = (np.abs(np.radians(da)) * rr <= HALF_ARC_M) & (rr >= r_lo - W_M) & (rr <= r_hi + W_M)
        u = -rr[m]                                   # the step reader wants the dark side at smaller u
        I = pts["i"][m]
        r = step_edge(u, I < T, -r_hi, -r_lo)
        if r is None:
            continue
        sens = [step_edge(u, I < T * f, -r_hi, -r_lo) for f in T_SENS]
        r["t_sens_m"] = round(max(abs(q["edge"] - r["edge"]) if q else 99.0 for q in sens), 2)
        r["edge"] = -r["edge"]
        out.append((float(th), r["edge"], r))
    return out


def fit_line(P):
    """total least squares: (centroid, unit direction, rms)"""
    import numpy as np
    c = P.mean(axis=0)
    _u, sv, vt = np.linalg.svd(P - c)
    d = vt[0]
    n = np.array([-d[1], d[0]])
    return c, d, float(np.sqrt(np.mean(((P - c) @ n) ** 2)))


def fit_circle(P):
    """geometric least squares (Kasa start, Gauss-Newton): (centre, R, rms)"""
    import numpy as np
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    sol, *_ = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)
    c = sol[:2]
    R = math.sqrt(sol[2] + c @ c)
    for _k in range(30):
        d = P - c
        r = np.hypot(d[:, 0], d[:, 1])
        J = np.c_[-d[:, 0] / r, -d[:, 1] / r, -np.ones(len(P))]
        res = r - R
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        c = c + step[:2]; R = R + step[2]
        if np.abs(step).max() < 1e-6:
            break
    d = P - c
    return c, float(R), float(np.sqrt(np.mean((np.hypot(d[:, 0], d[:, 1]) - R) ** 2)))


def corner_from_legs(c1, d1, c2, d2, toward1, toward2):
    """the crossing K' of two leg lines and the wedge: a (along leg 1, the way toward1 points), b (along leg 2), phi"""
    import numpy as np
    a = d1 if d1 @ toward1 > 0 else -d1
    b = d2 if d2 @ toward2 > 0 else -d2
    A = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]])
    t = np.linalg.solve(A, c2 - c1)
    K = c1 + d1 * t[0]
    phi = math.acos(max(-1.0, min(1.0, float(a @ b))))
    return K, a, b, phi


def tangent_radius(Q, K, a, b, phi):
    """mouth_returns' circle (tangent to both legs, in the wedge) that best fits the outline points Q: for every R of
    R_GRID, the median |distance to the circle| of the Q inside the arc's middle ARC_MID; the best R, its score, the
    score curve's prominence (the median score over the grid / the best's) and the circle"""
    import numpy as np
    bis = (a + b) / np.linalg.norm(a + b)
    rows = []
    for R in np.arange(R_GRID[0], R_GRID[1] + 1e-9, R_GRID[2]):
        O = K + bis * (R / math.sin(phi / 2.0))
        t = R / math.tan(phi / 2.0)
        Ta, Tb = K + a * t, K + b * t
        a0 = math.atan2(Ta[1] - O[1], Ta[0] - O[0]); a1 = math.atan2(Tb[1] - O[1], Tb[0] - O[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        aq = np.arctan2(Q[:, 1] - O[1], Q[:, 0] - O[0])
        f = ((aq - a0 + math.pi) % (2 * math.pi) - math.pi) / da
        m = (f >= 0.5 - ARC_MID / 2) & (f <= 0.5 + ARC_MID / 2)
        if m.sum() < 5:
            rows.append((R, np.inf, int(m.sum()), O, Ta, Tb, da))
            continue
        dist = np.abs(np.hypot(Q[m, 0] - O[0], Q[m, 1] - O[1]) - R)
        rows.append((R, float(np.median(dist)), int(m.sum()), O, Ta, Tb, da))
    k = int(np.argmin([r_[1] for r_ in rows]))
    sc = np.array([r_[1] for r_ in rows])
    fin = np.isfinite(sc)
    R, best, n, O, Ta, Tb, da = rows[k]
    return {"R": float(R), "median_dev_m": round(best, 3), "n_points": n,
            "prominence": round(float(np.median(sc[fin]) / max(best, 1e-6)), 2),
            "at_grid_end": bool(k == 0 or k == len(rows) - 1), "O": O, "Ta": Ta, "Tb": Tb,
            "arc_m": round(abs(da) * R, 2), "curve": [(round(r_[0], 2), round(r_[1], 3)) for r_ in rows if np.isfinite(r_[1])]}


# -------------------------------------------------------------------------------------------------------------- measure
class Ctx:
    def __init__(self, repo: Path, npz: Path):
        import numpy as np
        self.repo = repo
        d = np.load(npz, allow_pickle=False)
        self.d = d
        self.names = [str(n) for n in d["spots"]]
        self.origin, self.L = lines(repo)
        self.mlon, self.mlat = mpd(repo, float(self.origin["lat"]))
        P = repo / T
        self.rows = json.loads((P / "source" / "full" / "north_loop.json").read_text(encoding="utf-8"))["rows"]
        self.kerbs = json.loads((P / "source" / "edges" / "kerbs.lm.json").read_text(encoding="utf-8"))["kerbs"]
        self.osm = osm_line(repo, self.origin, self.mlon, self.mlat)

    def pts(self, nm):
        m = self.d["spot"] == self.names.index(nm)
        return {"x": self.d["x"][m], "z": self.d["z"][m], "h": self.d["h"][m], "i": self.d["i"][m].astype(float),
                "c": self.d["c"][m]}

    def ll(self, E, N):
        return lonlat(E, N, self.origin, self.mlon, self.mlat)

    def own_s(self, row_s):
        """the north loop's own s (connectors.full.json) of a north_loop.json row (row s, OSM's, every 2 m)"""
        i = min(int(math.floor(row_s / 2.0 + 0.5)), len(self.L["north"].s) - 1)   # the last row (1001) is the last point
        return float(self.L["north"].s[i])

    def off_osm(self, row_s, E, N, side):
        """metres off OSM's line at row s, outward on the side (+1 left, -1 right): north_loop.json's left_m / right_m"""
        s, x, z, tx, tz = self.osm
        i = min(int(round(row_s)), len(s) - 1)
        return round(float(side * ((E - x[i]) * -tz[i] + (N - z[i]) * tx[i])), 2)

    def row(self, row_s):
        return next(r for r in self.rows if abs(r["s"] - row_s) < 0.01)


def _edge_rec(cx, st, s_at, r, row_s=None, side=None):
    E, N = st.point(s_at, r["edge"])
    rec = {"o_past_built_edge_m": r["edge"], "E": round(E, 2), "N": round(N, 2), "lonlat": cx.ll(E, N),
           "score": r["score"], "returns_in_out": [r["n_in"], r["n_out"]], "gap_m": r["gap"], "t_sens_m": r["t_sens_m"],
           "kept": bool(r["score"] >= SCORE_MIN and r["t_sens_m"] <= 0.5)}
    if row_s is not None:
        rec["off_osm_m"] = cx.off_osm(row_s, E, N, side)
    return rec


def read_north_rows(cx, spot, side, row_lo, row_hi, lo=-3.0, hi=3.0):
    """every north_loop.json row in [row_lo, row_hi] on one side: the lidar's asphalt edge (_edge_rec) beside the NAIP
    row's own value (off OSM's line)"""
    import numpy as np
    north = cx.L["north"]
    s0, s1 = cx.own_s(row_lo), cx.own_s(row_hi)
    st = Strip(cx.pts(spot), north, side, s0, s1)
    Tt, a, b = st.threshold(s0, s1)
    out = []
    for rs in np.arange(row_lo, row_hi + 1e-9, 2.0):
        so = cx.own_s(rs)
        r = st.read(so, lo, hi, Tt)
        rw = cx.row(rs)
        naip = rw["left_m" if side > 0 else "right_m"]
        rec = {"row_s": float(rs), "own_s": round(so, 2), "naip_off_osm_m": naip, "naip_width": rw["width"]}
        if r is not None:
            rec.update(_edge_rec(cx, st, so, r, rs, side))
        out.append(rec)
    return out, {"T": round(Tt), "asphalt_median": round(a), "beside_median": round(b)}


def in_kerb_or_stripe(cx, side, own_s, stripes):
    for k in cx.kerbs:
        if k.get("line") and (k["side"] == "left") == (side > 0) and k["s0"] - 3 <= own_s <= k["s1"] + 3:
            return True
    return any(sd == side and a - 3 <= own_s <= b + 3 for sd, a, b in stripes)


def registration(cx, stripes):
    """the lidar's asphalt edge against NAIP's on every row both read in the spots (kerb runs and the stripes left out:
    there NAIP's edge is the paint's outer side, the lidar's the asphalt's): d = lidar - NAIP, metres outward off OSM's
    line. Fitted d = c + (dE, dN) . n_out (n_out the row's outward normal): c the readers' bias (the lidar's first bright
    return against NAIP's edge: the white edge line is paint, and NAIP's edge is the line's outer side or the asphalt's
    end), (dE, dN) the lidar's shift against the photo"""
    import numpy as np
    spans = {"fork": (22.0, 44.0), "l254": (232.0, 284.0), "stripe372": (356.0, 420.0), "stripe648": (632.0, 700.0),
             "merge": (944.0, 984.0)}
    s_, x_, z_, tx_, tz_ = cx.osm
    out, D, NO, tag = {}, [], [], []
    for nm, (a, b) in spans.items():
        for side, sd in ((1, "left"), (-1, "right")):
            recs, thr = read_north_rows(cx, nm, side, a, b)
            for r in recs:
                if not (r.get("kept") and r["naip_off_osm_m"] is not None and r["naip_width"].startswith("measured")
                        and not in_kerb_or_stripe(cx, side, r["own_s"], stripes)):
                    continue
                i = int(round(r["row_s"]))
                D.append(r["off_osm_m"] - r["naip_off_osm_m"])
                NO.append((side * -tz_[i], side * tx_[i]))
                tag.append(f"{nm}_{sd}")
    D, NO, tag = np.array(D), np.array(NO), np.array(tag)
    A = np.c_[np.ones(len(D)), NO]
    sol, *_ = np.linalg.lstsq(A, D, rcond=None)
    res = D - A @ sol
    for t in sorted(set(tag)):
        m = tag == t
        out[t] = {"rows": int(m.sum()), "lidar_minus_naip_median_m": round(float(np.median(D[m])), 2),
                  "after_fit_median_m": round(float(np.median(res[m])), 2)}
    out["fit"] = {"rows": len(D), "c_m": round(float(sol[0]), 2), "shift_E_N_m": [round(float(sol[1]), 2), round(float(sol[2]), 2)],
                  "residual_p10_p50_p90_m": [round(float(v), 2) for v in np.percentile(res, [10, 50, 90])],
                  "residual_within_0.3_m": round(float(np.mean(np.abs(res) <= 0.3)), 2),
                  "raw_p10_p50_p90_m": [round(float(v), 2) for v in np.percentile(D, [10, 50, 90])]}
    return out


def stripe_read(cx, spot, eye, side=1, step=0.5, along=1.0):
    """one flat stripe on the north loop's edge (round 4's eye span): every `step` of own s, the first bright return
    outward (the inner edge of the first paint: the white edge line, or the stripe), +-along. The reference is the median
    of the stations 5-25 m outside the eye span, either side (the edge line there). The stripe's CORE is the longest run of
    stations whose first bright return stands STRIPE_MIN_M or more inside the reference (gaps up to 2 m bridged); its
    TAPERED ends run on while it stands TAPER_MIN_M or more inside"""
    import numpy as np
    north = cx.L["north"]
    a, b = eye[0] - 30.0, eye[1] + 30.0
    st = Strip(cx.pts(spot), north, side, a, b)
    Tt, A, B = st.threshold(a, b)
    S = np.arange(a, b + 1e-9, step)
    R = [st.read(s, -3.0, 2.0, Tt, along=along) for s in S]
    e = np.array([r["edge"] if r and r["score"] >= SCORE_MIN else np.nan for r in R])
    before = (S >= eye[0] - 25) & (S <= eye[0] - 5)
    after = (S >= eye[1] + 5) & (S <= eye[1] + 25)
    ref = float(np.nanmedian(e[before | after]))

    def run_of(depth):
        inside = np.nan_to_num(e, nan=99.0) <= ref - depth
        runs, k = [], 0
        while k < len(S):
            if inside[k]:
                j_ = k
                while j_ + 1 < len(S) and (inside[j_ + 1] or inside[j_ + 2:j_ + 1 + int(round(2.0 / step))].any()):
                    j_ += 1
                runs.append((k, j_)); k = j_ + 1
            else:
                k += 1
        k0, k1 = max(runs, key=lambda r_: S[r_[1]] - S[r_[0]])
        return float(S[k0]), float(S[k1])
    s0, s1 = run_of(STRIPE_MIN_M)
    t0, t1 = run_of(TAPER_MIN_M)
    core = (S >= s0 + 2.0) & (S <= s1 - 2.0) & np.isfinite(e)
    inm = float(np.median(e[core]))
    x_, z_, tx_, tz_, _hw = north.at((s0 + s1) / 2.0)
    m_s = (st.s >= s0 + 2) & (st.s <= s1 - 2)
    m_o = ((st.s >= eye[0] - 25) & (st.s <= eye[0] - 5)) | ((st.s >= eye[1] + 5) & (st.s <= eye[1] + 25))
    band = m_s & (st.o >= inm + 0.1) & (st.o <= ref - 0.1)

    def q(v):
        return [int(x) for x in np.percentile(v, [25, 50, 75])] if len(v) else None
    stations = [{"own_s": round(float(s), 1), "first_bright_o_m": (None if r is None else r["edge"]),
                 "score": (None if r is None else r["score"]), "t_sens_m": (None if r is None else r["t_sens_m"]),
                 "gap_m": (None if r is None else r["gap"]), "returns_in_out": (None if r is None else [r["n_in"], r["n_out"]])}
                for s, r in zip(S, R)]
    return {"T": round(Tt), "asphalt_median": round(A), "beside_median": round(B), "ref": ref,
            "ref_before_after": [round(float(np.nanmedian(e[before])), 2), round(float(np.nanmedian(e[after])), 2)],
            "core": (s0, s1), "tapered": (t0, t1), "in_o": inm,
            "in_o_p10_p90": [round(float(v), 2) for v in np.percentile(e[core], [10, 90])], "core_stations": int(core.sum()),
            "n_out": (float(side * -tz_), float(side * tx_)),
            "intensity": {"stripe_band": q(st.i[band]), "same_band_outside_the_stripe": q(st.i[m_o & (st.o >= inm + 0.1) & (st.o <= ref - 0.1)]),
                          "beside_the_stripe_0.5_3_m_past_the_built_edge": q(st.i[m_s & (st.o >= 0.5) & (st.o <= 3.0)]),
                          "the_lane_1.5_4.5_m_inside": q(st.i[m_s & (st.o >= -4.5) & (st.o <= -1.5)])},
            "returns_in_band": int(band.sum()), "stations": stations}


def mouth_frames(cx):
    """tools/mouth_radii.py's corner frames on the repo's built data (data/mouths.json, connectors.local.json,
    centerline.local.json: the install build's), keyed as round 4's mouth_radii.naip.json"""
    sys.path.insert(0, str(cx.repo / "tools"))
    import mouth_radii
    D = cx.repo / T / "data"
    mouths = json.loads((D / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    conns = json.loads((D / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    local = json.loads((D / "centerline.local.json").read_text(encoding="utf-8"))
    out = {}
    for mo in mouths:
        cfs, err = mouth_radii.corner_frames(mo, conns, local)
        if cfs is None:
            raise SystemExit(f"[corner] {mo['piece']}: {err}")
        for cf in cfs:
            out[f"{mo['piece']}|{mo['end']}|{cf['e']:+d}"] = cf
    return out


def leg_points(P, line, side, s_lo, s_hi, K, dmin, dmax):
    """a leg's lidar edge: strip reads every 1 m on a built line's side, kept where the edge point lies dmin-dmax from K"""
    import numpy as np
    st = Strip(P, line, side, s_lo, s_hi)
    Tt, A, B = st.threshold(s_lo, s_hi)
    pts = []
    for s in np.arange(s_lo, s_hi + 1e-9, 1.0):
        r = st.read(s, -3.0, 3.0, Tt)
        if r and r["score"] >= SCORE_MIN:
            E, N = st.point(s, r["edge"])
            if dmin <= math.hypot(E - K[0], N - K[1]) <= dmax:
                pts.append((float(s), E, N, r["edge"]))
    return np.array(pts), Tt


def corner(cx, P, K, leg1, leg2, R0):
    """one corner of the merge, read from the lidar alone: each leg's real edge (leg_points) fitted as a straight line,
    K' their crossing, then rays from the corner circle's centre read the asphalt's edge (grass -> asphalt), and R is the
    circle tangent to both legs that fits those points best (tangent_radius; the rays re-read about each new centre, four
    times). Reported beside it: the free circle through the outline between the tangent points, and the outline's own
    radius every 2 m (a circle through 10 m of it)"""
    import numpy as np
    p1, T1 = leg_points(P, cx.L[leg1[0]], leg1[1], leg1[2], leg1[3], K, leg1[4], leg1[5])
    p2, T2 = leg_points(P, cx.L[leg2[0]], leg2[1], leg2[2], leg2[3], K, leg2[4], leg2[5])
    c1, d1, rms1 = fit_line(p1[:, 1:3])
    c2, d2, rms2 = fit_line(p2[:, 1:3])
    Kp, a, b, phi = corner_from_legs(c1, d1, c2, d2, c1 - np.array(K), c2 - np.array(K))
    Tc = math.sqrt(T1 * T2)
    bis = (a + b) / np.linalg.norm(a + b)
    R = R0
    for _it in range(4):
        O = Kp + bis * (R / math.sin(phi / 2.0))
        tt = R / math.tan(phi / 2.0)
        Ta, Tb = Kp + a * tt, Kp + b * tt
        ta = math.degrees(math.atan2(Ta[1] - O[1], Ta[0] - O[0]))
        da = (math.degrees(math.atan2(Tb[1] - O[1], Tb[0] - O[0])) - ta + 180.0) % 360.0 - 180.0
        th0, th1 = (ta, ta + da) if da > 0 else (ta + da, ta)
        rays = polar_read(P, O, th0 - 20.0, th1 + 20.0, 1.0, Tc, max(2.0, 0.5 * R), R + 8.0)
        Q = np.array([(O[0] + r * math.cos(math.radians(th)), O[1] + r * math.sin(math.radians(th)))
                      for th, r, rec in rays if rec["score"] >= SCORE_MIN])
        tr = tangent_radius(Q, Kp, a, b, phi)
        R = tr["R"]
    O, Ta, Tb = tr["O"], tr["Ta"], tr["Tb"]
    a0 = math.atan2(Ta[1] - O[1], Ta[0] - O[0]); a1 = math.atan2(Tb[1] - O[1], Tb[0] - O[0])
    dd = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    outline = []
    for th, r, rec in rays:
        E, N = O[0] + r * math.cos(math.radians(th)), O[1] + r * math.sin(math.radians(th))
        fa = (((math.radians(th) - a0 + math.pi) % (2 * math.pi)) - math.pi) / dd
        outline.append({"theta_deg": round(th % 360.0, 1), "r_m": round(r, 2), "E": round(E, 2), "N": round(N, 2),
                        "lonlat": cx.ll(E, N), "arc_fraction": round(fa, 3), "score": rec["score"], "gap_m": rec["gap"],
                        "returns_in_out": [rec["n_in"], rec["n_out"]], "t_sens_m": rec["t_sens_m"],
                        "kept": bool(rec["score"] >= SCORE_MIN and rec["t_sens_m"] <= 0.5)})
    arc = np.array([(o["E"], o["N"]) for o in outline if o["kept"] and 0.0 <= o["arc_fraction"] <= 1.0])
    cfree, Rfree, rmsf = fit_circle(arc)
    # the outline's own radius along it: a circle through every 10 m of the kept points, every 2 m (+ = centred on O's side)
    Qk = np.array([(o["E"], o["N"]) for o in outline if o["kept"]])
    dl = np.r_[0, np.cumsum(np.hypot(*np.diff(Qk, axis=0).T))]
    prof = []
    for c in np.arange(5.0, dl[-1] - 5.0 + 1e-9, 2.0):
        m = np.abs(dl - c) <= 5.0
        if m.sum() >= 6:
            cc, Rl, rl = fit_circle(Qk[m])
            sg = 1.0 if (cc - Qk[m].mean(0)) @ (O - Qk[m].mean(0)) > 0 else -1.0
            prof.append({"along_m": round(float(c), 1), "E": round(float(np.interp(c, dl, Qk[:, 0])), 2),
                         "N": round(float(np.interp(c, dl, Qk[:, 1])), 2), "R_m": round(sg * Rl, 1), "rms_m": round(rl, 3)})
    legs = {}
    for nm, p_, rms_, T_, lg in (("leg1", p1, rms1, T1, leg1), ("leg2", p2, rms2, T2, leg2)):
        legs[nm] = {"line": lg[0], "side": "left" if lg[1] > 0 else "right", "stations": len(p_), "s": [p_[0, 0], p_[-1, 0]],
                    "o_past_built_edge_median_m": round(float(np.median(p_[:, 3])), 2), "straight_fit_rms_m": round(rms_, 3),
                    "T": round(T_)}
    return {"legs": legs, "Kreal": [round(float(v), 2) for v in Kp], "a": [round(float(v), 4) for v in a],
            "b": [round(float(v), 4) for v in b], "phi_deg": round(math.degrees(phi), 2), "T": round(Tc),
            "tangent": tr, "free": {"centre": [round(float(v), 2) for v in cfree], "R_m": round(Rfree, 2),
                                    "rms_m": round(rmsf, 3), "points": int(len(arc))},
            "profile": prof, "outline": outline}


def kerb_band(P, O, outline, lo_frac=0.0, hi_frac=1.0):
    """the very bright returns (over the grass's own p99 4-8 m behind: the kerb's white blocks) behind the asphalt's edge
    along the arc, per 0.25 m of depth behind the edge"""
    import numpy as np
    sel = [o for o in outline if o["kept"] and lo_frac <= o["arc_fraction"] <= hi_frac]
    th = np.array([o["theta_deg"] for o in sel]); rr = np.array([o["r_m"] for o in sel])
    order = np.argsort(th); th, rr = th[order], rr[order]
    dx, dz = P["x"] - O[0], P["z"] - O[1]
    ang = np.degrees(np.arctan2(dz, dx)) % 360.0
    m = (ang >= th.min()) & (ang <= th.max())
    depth = np.interp(ang[m], th, rr) - np.hypot(dx[m], dz[m])     # metres behind the asphalt's edge (toward the grass)
    I = P["i"][m]
    T_hi = float(np.percentile(I[(depth >= 4) & (depth <= 8)], 99))
    rows = []
    for lo in np.arange(-0.5, 4.0 - 1e-9, 0.25):
        mm = (depth >= lo) & (depth < lo + 0.25)
        rows.append({"depth_m": [round(float(lo), 2), round(float(lo + 0.25), 2)], "returns": int(mm.sum()),
                     "over_T_hi": int((I[mm] >= T_hi).sum()), "median_I": (int(np.median(I[mm])) if mm.any() else None)})
    hit = [r_ for r_ in rows if r_["over_T_hi"] > 0 and r_["depth_m"][0] >= 0]
    return {"T_hi": round(T_hi), "theta_deg": [round(float(th.min()), 1), round(float(th.max()), 1)],
            "deepest_bright_m": (hit[-1]["depth_m"][1] if hit else None),
            "shallowest_bright_m": (hit[0]["depth_m"][0] if hit else None), "bins": rows}


def ray_read(P, p0, d, lo, hi, T_):
    """along one ray from p0 (unit direction d): the first dark -> bright step, u metres from p0"""
    import numpy as np
    X = np.c_[P["x"], P["z"]] - np.asarray(p0)
    u = X @ d
    w = np.abs(X @ np.array([-d[1], d[0]]))
    m = (w <= HALF_ARC_M) & (u >= lo - W_M) & (u <= hi + W_M)
    r = step_edge(u[m], P["i"][m] < T_, lo, hi)
    if r is None:
        return None
    sens = [step_edge(u[m], P["i"][m] < T_ * f, lo, hi) for f in T_SENS]
    r["t_sens_m"] = round(max(abs(q_["edge"] - r["edge"]) if q_ else 99.0 for q_ in sens), 2)
    return r


def measure(repo: Path, npz: Path, outdir: Path):
    import numpy as np
    outdir.mkdir(parents=True, exist_ok=True)
    cx = Ctx(repo, npz)
    north, west = cx.L["north"], cx.L["west"]
    res = {}
    # ---- item 2 first: its spans keep the registration off the paint
    stripes = {nm: stripe_read(cx, nm, eye) for nm, eye in (("stripe372", (372.0, 401.0)), ("stripe648", (648.0, 682.0)))}
    for nm, r in stripes.items():
        print(f"[stripe] {nm}: core {r['core']}, tapered {r['tapered']}, in_o {r['in_o']:.2f} {r['in_o_p10_p90']}, ref "
              f"{r['ref']:.2f} {r['ref_before_after']}, T {r['T']}: {r['intensity']}")
    reg = registration(cx, [(1, *r["tapered"]) for r in stripes.values()])
    c_bias, (sE, sN) = reg["fit"]["c_m"], reg["fit"]["shift_E_N_m"]
    print(f"[registration] {reg['fit']}")

    def shift_out(no):
        return sE * no[0] + sN * no[1]

    # ---- item 1 (and the west corner, for item 3's R rows 988-1001)
    P = cx.pts("merge")
    frames = mouth_frames(cx)
    Ke = frames["full_north#0#0|end|+1"]["K"]; Kw = frames["full_north#0#0|end|-1"]["K"]
    sKe = float(frames["full_north#0#0|end|+1"]["sK"])
    east = corner(cx, P, Ke, ("west", 1, sKe, sKe + 40.0, 14.0, 32.0), ("north", 1, 920.0, 990.0, 18.0, 32.0), 20.0)
    westc = corner(cx, P, Kw, ("west", 1, sKe - 45.0, sKe - 5.0, 10.0, 28.0), ("north", -1, 920.0, 990.0, 10.0, 28.0), 10.0)
    east["kerb_band"] = kerb_band(P, east["tangent"]["O"], east["outline"])
    east["leg_windows"] = []
    for dw, dn_ in (((10.0, 26.0), (14.0, 28.0)), ((14.0, 32.0), (18.0, 32.0)), ((18.0, 36.0), (22.0, 36.0)), ((12.0, 40.0), (16.0, 40.0))):
        cv = corner(cx, P, Ke, ("west", 1, sKe, sKe + 45.0, *dw), ("north", 1, 915.0, 990.0, *dn_), 20.0)
        east["leg_windows"].append({"west_lap_leg_m_from_K": list(dw), "ladder_leg_m_from_K": list(dn_), "R_m": cv["tangent"]["R"],
                                    "median_dev_m": cv["tangent"]["median_dev_m"], "phi_deg": cv["phi_deg"],
                                    "free_R_m": cv["free"]["R_m"], "free_rms_m": cv["free"]["rms_m"]})
        print(f"[east legs] {east['leg_windows'][-1]}")
    westc["leg_windows"] = []
    for dw, dn_ in (((8.0, 22.0), (8.0, 22.0)), ((14.0, 34.0), (14.0, 34.0))):
        cv = corner(cx, P, Kw, ("west", 1, sKe - 50.0, sKe - 5.0, *dw), ("north", -1, 915.0, 990.0, *dn_), 10.0)
        westc["leg_windows"].append({"west_lap_leg_m_from_K": list(dw), "ladder_leg_m_from_K": list(dn_), "R_m": cv["tangent"]["R"],
                                     "median_dev_m": cv["tangent"]["median_dev_m"], "phi_deg": cv["phi_deg"],
                                     "free_R_m": cv["free"]["R_m"], "free_rms_m": cv["free"]["rms_m"]})
        print(f"[west legs] {westc['leg_windows'][-1]}")
    for nm, c in (("east", east), ("west", westc)):
        tr = c["tangent"]
        print(f"[corner {nm}] legs {c['legs']} K' {c['Kreal']} phi {c['phi_deg']} T {c['T']} -> R {tr['R']} (dev {tr['median_dev_m']}, "
              f"n {tr['n_points']}, prom {tr['prominence']}, end {tr['at_grid_end']}, arc {tr['arc_m']}); free {c['free']}")
        print(f"[corner {nm}] profile " + " ".join(f"{q_['along_m']}:{q_['R_m']}" for q_ in c["profile"]))
    print(f"[kerb band] {east['kerb_band']['T_hi']} deepest {east['kerb_band']['deepest_bright_m']} shallowest "
          f"{east['kerb_band']['shallowest_bright_m']}: " + " ".join(f"{b_['depth_m'][0]}:{b_['over_T_hi']}/{b_['returns']}" for b_ in east["kerb_band"]["bins"]))
    # the same corners read in mouth_radii's BUILT frame (the frame route.mouth_returns builds in), for the record
    built = {}
    for key, cf in frames.items():
        X = np.c_[P["x"], P["z"]] - np.array(cf["K"])
        dn, ua = X @ np.array(cf["n"]), X @ np.array(cf["a"])
        A_ = float(np.median(P["i"][(dn < -2.0) & (dn > -6.0) & (ua > 12) & (ua < 30)]))
        G_ = float(np.median(P["i"][(dn > 3.0) & (dn < 8.0) & (ua > 12) & (ua < 30)]))
        built[key] = corner_read_built(cx, P, cf, math.sqrt(A_ * G_), 14.0)
        print(f"[built frame] {key}: {built[key]['summary']}")

    # ---- item 3
    l254, thr254 = read_north_rows(cx, "l254", 1, 240.0, 272.0)
    for r in l254:
        if "off_osm_m" in r:
            no = (lambda t: (float(-t[3]), float(t[2])))(north.at(r["own_s"]))
            r["off_osm_naip_def_m"] = round(r["off_osm_m"] - c_bias - shift_out(no), 2)
    Pf = cx.pts("fork")
    stf = Strip(Pf, north, -1, 0.0, 50.0)
    Tf, Af, Bf = stf.threshold(22.0, 45.0)
    fork = []
    for rs in np.arange(0.0, 44.0 + 1e-9, 2.0):
        so = cx.own_s(rs)
        r = stf.read(so, -3.0, 16.0, Tf)
        rec = {"row_s": float(rs), "own_s": round(so, 2)}
        if r is not None:
            rec.update(_edge_rec(cx, stf, so, r, rs, -1))
            sw, lw = west.project(np.array([rec["E"]]), np.array([rec["N"]]), 2650.0, 2800.0)
            hw = float(np.interp(sw[0], west.s, west.w) / 2.0)
            rec["west_s"] = round(float(sw[0]), 1)
            rec["past_west_right_edge_m"] = round(float(-lw[0] - hw), 2)
            rec["past_west_left_edge_m"] = round(float(lw[0] - hw), 2)
        fork.append(rec)
    stw = Strip(Pf, west, 1, 2690.0, 2775.0)
    Tw, Aw, Bw = stw.threshold(2745.0, 2770.0)
    fork_west = []
    for s_ in np.arange(2700.0, 2770.0 + 1e-9, 1.0):
        r = stw.read(s_, -3.0, 16.0, Tw)
        if r is not None:
            q_ = _edge_rec(cx, stw, s_, r)
            q_["west_s"] = float(s_)
            fork_west.append(q_)
    gn = next(r for r in fork if r.get("kept") and r["row_s"] >= 20 and abs(r["o_past_built_edge_m"]) <= 1.5)
    gw = next(q_ for q_ in fork_west if q_["west_s"] >= 2730 and q_["kept"] and abs(q_["o_past_built_edge_m"]) <= 1.0)
    Og = np.array([(gn["E"] + gw["E"]) / 2.0, (gn["N"] + gw["N"]) / 2.0 + 8.0])
    Tg = math.sqrt(Tf * Tw)
    nose = []
    for th, r, rec in polar_read(Pf, Og, 180.0, 360.0, 2.0, Tg, 2.0, 25.0):
        E, N = Og[0] + r * math.cos(math.radians(th)), Og[1] + r * math.sin(math.radians(th))
        nose.append({"theta_deg": th, "r_m": round(r, 2), "E": round(E, 2), "N": round(N, 2), "lonlat": cx.ll(E, N),
                     "score": rec["score"], "t_sens_m": rec["t_sens_m"], "kept": bool(rec["score"] >= SCORE_MIN and rec["t_sens_m"] <= 0.5)})
    kept_n = [q_ for q_ in nose if q_["kept"]]
    apex = min(kept_n, key=lambda q_: q_["N"])
    sa, la = north.project(np.array([apex["E"]]), np.array([apex["N"]]), 0.0, 60.0)
    apex["north_own_s"], apex["north_lat_m"] = round(float(sa[0]), 2), round(float(la[0]), 2)
    sw_, lw_ = west.project(np.array([apex["E"]]), np.array([apex["N"]]), 2680.0, 2780.0)
    apex["west_s"], apex["west_lat_m"] = round(float(sw_[0]), 2), round(float(lw_[0]), 2)
    print(f"[gore] centre {Og.round(2)} T {Tg:.0f}: apex {apex}")
    merge_rows = []
    for side, lo_row, hi_row in ((-1, 986.0, 1001.0), (1, 994.0, 1001.0)):
        for rs in list(np.arange(lo_row, hi_row - 1e-9, 2.0)) + [hi_row]:
            so = cx.own_s(rs)
            x_, z_, tx_, tz_, hw_ = north.at(so)
            d = np.array([float(side * -tz_), float(side * tx_)])
            T_ = math.sqrt(east["legs"]["leg1"]["T"] * westc["legs"]["leg2"]["T"])
            r = ray_read(P, (float(x_), float(z_)), d, 2.0, 30.0, T_)
            rec = {"side": "left" if side > 0 else "right", "row_s": float(rs), "own_s": round(so, 2),
                   "built_half_width_m": round(float(hw_), 2)}
            if r is not None:
                E, N = float(x_ + d[0] * r["edge"]), float(z_ + d[1] * r["edge"])
                sw, lw = west.project(np.array([E]), np.array([N]), 2780.0, 2900.0)
                hw = float(np.interp(sw[0], west.s, west.w) / 2.0)
                dist = {}
                for nm, c in (("east corner", east), ("west corner", westc)):
                    Qo = np.array([(o["E"], o["N"]) for o in c["outline"] if o["kept"]])
                    dist[nm] = round(float(np.min(np.hypot(Qo[:, 0] - E, Qo[:, 1] - N))), 2)
                rec.update({"edge_from_line_m": r["edge"], "o_past_built_edge_m": round(r["edge"] - hw_, 2), "E": round(E, 2),
                            "N": round(N, 2), "lonlat": cx.ll(E, N), "score": r["score"], "gap_m": r["gap"],
                            "t_sens_m": r["t_sens_m"], "returns_in_out": [r["n_in"], r["n_out"]],
                            "kept": bool(r["score"] >= SCORE_MIN and r["t_sens_m"] <= 0.5),
                            "off_osm_m": cx.off_osm(rs, E, N, side), "west_s": round(float(sw[0]), 1),
                            "west_lat_m": round(float(lw[0]), 2), "west_half_width_m": round(hw, 2),
                            "nearest_outline_m": dist})
                rec["off_osm_shift_only_m"] = round(rec["off_osm_m"] - shift_out(d), 2)
            merge_rows.append(rec)
            print(f"[merge rows] {rec}")
    res.update({"stripes": stripes, "reg": reg, "east": east, "west": westc, "built": built, "l254": l254, "thr254": thr254,
                "fork": fork, "fork_T": (Tf, Af, Bf), "fork_west": fork_west, "fork_west_T": (Tw, Aw, Bw),
                "gore": {"centre": Og, "T": Tg, "apex": apex, "outline": nose},
                "merge_rows": merge_rows})
    write_outputs(cx, res, outdir)


def corner_read_built(cx, P, cf, T_c, R0, edge_u=(12.0, 30.0), edge_off=(-3.0, 8.0)):
    """tools/mouth_radii.py's measurement in its BUILT corner frame (K, a, b, phi of the install build's data), the
    lidar's returns in place of NAIP's gray: each leg's real edge offset (median of 1 m step reads EDGE_U from K), K', and
    the tangent circle fitted to the lidar's asphalt edge read by rays about its centre (four passes)"""
    import numpy as np
    K = np.array(cf["K"], dtype=float)
    a, n, b, nb = (np.array(cf[k], dtype=float) for k in ("a", "n", "b", "nb"))
    phi = math.radians(cf["phi"])
    X = np.c_[P["x"], P["z"]] - K
    dark = P["i"] < T_c
    legs = {}
    for nm, along, out in (("host", a, n), ("street", b, nb)):
        ua, dn = X @ along, X @ out
        rd = []
        for u in np.arange(edge_u[0], edge_u[1] + 1e-9, 1.0):
            m = (np.abs(ua - u) <= ALONG_M) & (dn >= edge_off[0] - W_M) & (dn <= edge_off[1] + W_M)
            r = step_edge(dn[m], dark[m], *edge_off)
            if r and r["score"] >= SCORE_MIN:
                rd.append(r["edge"])
        legs[nm] = {"offset_m": round(float(np.median(rd)), 2), "stations": len(rd),
                    "p10_p90_m": [round(float(v), 2) for v in np.percentile(rd, [10, 90])]}
    P1, P2 = K + n * legs["host"]["offset_m"], K + nb * legs["street"]["offset_m"]
    t = np.linalg.solve(np.array([[a[0], -b[0]], [a[1], -b[1]]]), P2 - P1)
    Kp = P1 + a * t[0]
    bis = (a + b) / np.linalg.norm(a + b)
    R = R0
    for _it in range(4):
        O = Kp + bis * (R / math.sin(phi / 2.0))
        tt = R / math.tan(phi / 2.0)
        Ta, Tb = Kp + a * tt, Kp + b * tt
        ta = math.degrees(math.atan2(Ta[1] - O[1], Ta[0] - O[0]))
        da = (math.degrees(math.atan2(Tb[1] - O[1], Tb[0] - O[0])) - ta + 180.0) % 360.0 - 180.0
        th0, th1 = (ta, ta + da) if da > 0 else (ta + da, ta)
        rays = polar_read(P, O, th0 - 15.0, th1 + 15.0, 1.0, T_c, max(2.0, 0.5 * R), R + 8.0)
        Q = np.array([(O[0] + r * math.cos(math.radians(th)), O[1] + r * math.sin(math.radians(th)))
                      for th, r, rec in rays if rec["score"] >= SCORE_MIN])
        tr = tangent_radius(Q, Kp, a, b, phi)
        R = tr["R"]
    return {"K": [round(float(v), 2) for v in K], "phi_deg": round(cf["phi"], 2), "legs": legs,
            "Kreal": [round(float(v), 2) for v in Kp], "T": round(T_c),
            "summary": {"R_m": tr["R"], "median_dev_m": tr["median_dev_m"], "points": tr["n_points"],
                        "prominence": tr["prominence"], "at_grid_end": tr["at_grid_end"], "arc_m": tr["arc_m"]}}


def _jd(o):
    import numpy as np
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    raise TypeError(type(o))


def _r(v, k=2):
    return [round(float(x), k) for x in v]


def write_outputs(cx, res, outdir):
    import numpy as np
    reg = res["reg"]
    c_bias, (sE, sN) = reg["fit"]["c_m"], reg["fit"]["shift_E_N_m"]
    src = {"lidar": "USGS 3DEP CO_Eastern_B3_2018 lidar (public domain), its EPT: " + EPT,
           "returns": "every class but noise (7, 18); one flight line over all five spots: " + str(sorted(set(cx.d["ps"].tolist()))),
           "returns_per_m2": {nm: round(float((cx.d["spot"] == k).sum() / ((b_[2] - b_[0]) * (b_[3] - b_[1]))), 2)
                              for k, (nm, b_) in enumerate(zip(cx.names, cx.d["boxes"]))},
           "frame": "the track frame: E, N metres about data/centerline.local.json's origin, lon / lat through "
                    "scripts.geometry.projection._meters_per_degree (round 4's mapping); 3857 -> lon / lat by pyproj",
           "lines": "the West lap as built (data/centerline.local.json + widths); the north loop's own line "
                    "(source/full/connectors.full.json + widths: 'own s', the s of round 4's kerbs and stripes); OSM's line "
                    "as measure_north.py builds it ('row s', north_loop.json's rows, whose left_m / right_m are metres off it)",
           "script": "hp_r5_lidar.py beside this file (plan / fetch / extract / measure)"}
    params = {k: globals()[k] for k in ("W_M", "ALONG_M", "GRID_M", "SCORE_MIN", "N_MIN", "T_SENS", "HALF_ARC_M", "ARC_MID",
                                        "R_GRID", "STRIPE_MIN_M", "TAPER_MIN_M", "SPOT_PAD_M")}
    params["_doc"] = "every one [invented] reader tuning; the returns are the measurement"
    reg_doc = {"_doc": "the lidar's asphalt edge against NAIP's own on every north-loop row both read in the five spots (the "
                       "north loop's kerb runs and the two stripes left out): d = lidar - NAIP, metres outward off OSM's line, "
                       "fitted d = c + (shift_E, shift_N) . n_out. c is the readers' difference: the lidar's first bright "
                       "return is the INNER side of the first paint (the white edge line is paint, retro-reflective at the "
                       "scanner's 1064 nm), NAIP's edge is the line's outer side + the photo's line-to-edge offset (round 4: "
                       "0.3 m left, 0.4 m right). The shift is the 2018 lidar against the 2023 photo.", **reg}

    def ll_pt(p):
        return {"E": round(float(p[0]), 2), "N": round(float(p[1]), 2), "lonlat": cx.ll(p[0], p[1])}

    # -------------------------------------------------------------------------------------------- item 1: the east fillet
    e = res["east"]; tr = e["tangent"]; kb = e["kerb_band"]
    bright = []
    for b_ in kb["bins"]:
        if b_["depth_m"][0] >= 0:
            bright += [b_["depth_m"][0] + 0.125] * b_["over_T_hi"]
    bright = np.array(bright)
    prof_arc = [q for q in e["profile"] if q["R_m"] > 0]
    arc_ids = [o for o in e["outline"] if o["kept"] and 0 <= o["arc_fraction"] <= 1]
    kb_p50, kb_p90, kb_max = (round(float(np.percentile(bright, 50)), 2), round(float(np.percentile(bright, 90)), 2),
                              round(float(bright.max()), 2))
    item1 = {
        "_doc": "ledger 0097 round 5, owed item 1: the paved fillet behind the T13 kerb, the merge's EAST corner "
                "(round 4's full_north#0#0|end|+1: tools/mouth_radii.py's best NAIP arc ran to its 20 m grid's end). Read "
                "off the 2018 lidar's INTENSITY: asphalt returns ~700-1,300, the grass and the kerb's paint 4,500-9,000 "
                "(one flight line). The outline is the asphalt's edge read by rays every 1 deg from the fitted circle's "
                "centre (grass -> asphalt); the kerb's white blocks are the brightest returns just behind it.",
        "source": src, "params": params,
        "measured": {
            "asphalt_edge_radius_m": tr["R"],
            "asphalt_edge_radius_how": "the circle tangent to both legs' lidar edges (each a straight fit) that best fits the "
                                       "outline's middle ARC_MID (tools/mouth_radii.py's model, R every 0.25 m from 5 to 60 m)",
            "fit": {"median_dev_m": tr["median_dev_m"], "points": tr["n_points"], "prominence": tr["prominence"],
                    "at_grid_end": tr["at_grid_end"], "arc_m": tr["arc_m"], "centre": ll_pt(tr["O"]),
                    "tangent_on_west_lap_edge": ll_pt(tr["Ta"]), "tangent_on_ladder_edge": ll_pt(tr["Tb"]),
                    "score_by_R": [c_ for c_ in tr["curve"] if abs(c_[0] - round(c_[0])) < 1e-9]},
            "free_circle": {**e["free"], "_doc": "no tangency imposed: the outline's points between the tangent points"},
            "leg_windows": {"_doc": "the same fit with each leg read over other distances from the built K: the radius's "
                                    "sensitivity to where the legs are taken (the corner eases in and out)",
                            "rows": e["leg_windows"],
                            "R_min_max_m": [min(q["R_m"] for q in e["leg_windows"]), max(q["R_m"] for q in e["leg_windows"])]},
            "radius_along_the_outline": {"_doc": "a circle through every 10 m of the outline, every 2 m along it from Ladder's "
                                                 "edge round to the West lap's (+ = the corner's own sense; huge or - = straight "
                                                 "or turning back)", "rows": e["profile"],
                                         "tightest_m": min(q["R_m"] for q in prof_arc)},
            "legs": e["legs"], "Kreal": e["Kreal"], "phi_deg": e["phi_deg"], "threshold_T": e["T"],
            "kerb_white_blocks": {"_doc": "returns brighter than T_hi (the grass's own p99, 4-8 m behind the edge) by depth "
                                          "behind the asphalt's edge along the arc: the kerb's white blocks. The kerb is "
                                          "the paved surface's edge (round 2's rule), so the paved outline is the asphalt "
                                          "outline moved this far into the grass",
                                  "T_hi": kb["T_hi"], "returns_over_T_hi": int(len(bright)),
                                  "depth_p50_p90_max_m": [kb_p50, kb_p90, kb_max], "bins": kb["bins"]},
            "paved_outline": {"offset_behind_asphalt_edge_m": kb_p90,
                              "radius_m": round(tr["R"] - kb_p90, 2),
                              "_doc": "DERIVED from the two measurements above: the asphalt edge's circle less the white "
                                      "blocks' p90 depth (a concentric arc; the kerb's NAIP widths, kerbs.lm.json T13 runs: "
                                      "1.88 / 2.10 m)"},
        },
        "outline": e["outline"],
        "against": {
            "round4_naip": {"radius_m": 20.0, "measured": False, "why": "fit at the grid's end (20.0 m)",
                            "_doc": "source/edges/mouth_radii.naip.json: the arc wanted more than the grid held"},
            "mouth_radii_built_frame_with_the_lidar": {**res["built"]["full_north#0#0|end|+1"],
                "_doc": "the same lidar returns in tools/mouth_radii.py's BUILT frame (the install build's corner: K, a, b, "
                        "phi 120.1 deg): its street line is the built Ladder edge 6-18 m from the cut, which the real edge "
                        "leaves as it sweeps round (leg offsets spread p10-p90 shown), so no circle tangent to it fits "
                        "the outline well (median dev above): read for the record, not the answer"},
            "naip_2023": "by eye on the 0.3 m crop (scratch overlay, not committed): the outline lies along the inner side "
                         "of the blue / white T13 kerb round the whole corner, the kerb behind it, grass behind the kerb",
        },
        "registration": {"shift_E_N_m": [sE, sN], "_doc": "the lidar against the 2023 photo (carried_edges.json "
                                                          "registration): subtract it to put a point in the photo's frame"},
    }

    # --------------------------------------------------------------------------------------------- item 2: the stripes
    stripes_out = {}
    for nm, eye in (("stripe372", (372.0, 401.0)), ("stripe648", (648.0, 682.0))):
        r = res["stripes"][nm]
        sh = sE * r["n_out"][0] + sN * r["n_out"][1]
        stripes_out[nm] = {
            "line": "full_north#0#0", "side": "left", "colour_round4": "blue_yellow", "profile": "paint",
            "round4_eye_s": list(eye),
            "s0_s1": list(r["core"]), "s0_s1_tapered": list(r["tapered"]),
            "s_ends_pm_m": 1.0,
            "in_m": round(r["in_o"], 2), "in_m_p10_p90": r["in_o_p10_p90"],
            "in_m_photo_frame": round(r["in_o"] - sh, 2),
            "out_m": None,
            "out_m_why": "not measured: the paint (intensity p25/p50/p75 in stripe_band) and what lies past it read alike "
                         "(beside_the_stripe); the lidar cannot place the stripe's outer side",
            "inside_the_edge_line_m": round(r["in_o"] - r["ref"], 2),
            "width_to_the_asphalt_end_m": round(r["ref"] - c_bias - r["in_o"], 2),
            "width_how": "DERIVED: the stripe's inner side to the asphalt's end, where the asphalt's end is the edge line's "
                         "inner side either side less the registration's c (the lidar's first bright against NAIP's edge); "
                         "true if the paint runs to the asphalt's end, as the 2023 photo shows",
            "out_m_if_to_the_asphalt_end": round(r["ref"] - c_bias, 2),
            "out_m_if_to_the_asphalt_end_photo_frame": round(r["ref"] - c_bias - sh, 2),
            "edge_line_either_side_o_m": round(r["ref"], 2), "edge_line_before_after_o_m": r["ref_before_after"],
            "edge_line_either_side_photo_frame_o_m": round(r["ref"] - sh, 2),
            "intensity_p25_p50_p75": r["intensity"], "returns_in_band": r["returns_in_band"],
            "threshold_T": r["T"], "core_stations": r["core_stations"],
            "stations": r["stations"]}
    item2 = {
        "_doc": "ledger 0097 round 5, owed item 2: the north loop's two blue / yellow stripes, which NAIP's z18 photo "
                "cannot resolve, read off the 2018 lidar's INTENSITY. Every 0.5 m of the north loop's own s (+-1 m along): "
                "the first bright return outward from the lane (the inner side of the first paint). Either side of a "
                "stripe that is the white edge line; along the stripe it stands ~0.8 m further in: the stripe's inner "
                "side. o / in_m are metres past the north loop's built lane edge (source/full/connectors.full.json's "
                "widths, kerbs.lm.json's convention, - = inside); the _photo_frame values take off the lidar's measured "
                "shift against the 2023 photo (carried_edges.json registration). s0_s1 is the stripe's core "
                "(STRIPE_MIN_M inside the edge line), s0_s1_tapered its ends (TAPER_MIN_M inside), each +-1 m (the "
                "stations' window). The lidar is 2018; round 4's eye spans are the 2023 photo's.",
        "source": src, "params": params, "stripes": stripes_out}

    # ------------------------------------------------------------------------------------------ item 3: carried edges
    def pick(r, keys):
        return {k: r[k] for k in keys if k in r}
    l254 = []
    for r in res["l254"]:
        l254.append(pick(r, ("row_s", "own_s", "naip_width", "naip_off_osm_m", "o_past_built_edge_m", "off_osm_m",
                             "off_osm_naip_def_m", "E", "N", "lonlat", "score", "gap_m", "t_sens_m", "returns_in_out", "kept")))
    nb = [r for r in res["l254"] if r.get("kept") and r["naip_off_osm_m"] is not None]
    l254_check = [round(r["off_osm_naip_def_m"] - r["naip_off_osm_m"], 2) for r in nb]
    fork_rows = []
    for r in res["fork"]:
        q = pick(r, ("row_s", "own_s", "o_past_built_edge_m", "off_osm_m", "E", "N", "lonlat", "score", "gap_m",
                     "t_sens_m", "returns_in_out", "kept", "west_s", "past_west_right_edge_m", "past_west_left_edge_m"))
        south = q["own_s"] < res["gore"]["apex"]["north_own_s"]
        if q.get("kept") and q["o_past_built_edge_m"] > 3.0 and abs(q.get("past_west_right_edge_m", 99)) <= 1.5:
            q["reads"] = "the West lap's far (right) edge: no edge of the north loop's own, the pavement runs on"
        elif south:
            q["reads"] = ("south of the gore's apex: one pavement, no edge of the north loop's own" +
                          ("" if q.get("kept") else " (no clean step)") +
                          (" (the step found lies inside the paving, at the junction's lighter surface)"
                           if q.get("kept") and q["o_past_built_edge_m"] <= 3.0 else ""))
        elif q.get("kept") and abs(q["o_past_built_edge_m"]) <= 1.5:
            q["reads"] = "the north loop's own right edge (the gore's grass)"
        else:
            q["reads"] = "no clean step (the gore's rounded nose)"
        fork_rows.append(q)
    gore_n = next(q for q in fork_rows if q["reads"].startswith("the north loop's own") and q["row_s"] >= 20)
    gore_w = next(q for q in res["fork_west"] if q["west_s"] >= 2730 and q["kept"] and abs(q["o_past_built_edge_m"]) <= 1.0)

    merge_rows = []
    for r in res["merge_rows"]:
        q = dict(r)
        near = q.get("nearest_outline_m", {})
        if q.get("kept") and near.get("east corner", 99) <= 1.0:
            q["reads"] = "the east corner's asphalt edge (merge_east_fillet.json outline; the T13 kerb's inner side)"
            q["kerb_outer_side_o_past_built_edge_m"] = round(q["o_past_built_edge_m"] + kb_p90, 2)
            q["kerb_outer_side_off_osm_photo_frame_m"] = round(q["off_osm_shift_only_m"] + kb_p90, 2)
        elif q.get("kept") and near.get("west corner", 99) <= 1.0:
            q["reads"] = "the west corner's asphalt edge (the bellmouth)"
        elif q["side"] == "right":
            q["reads"] = ("no edge of the north loop's own on this row's normal: the right side here is the mouth, the "
                          "West lap's pavement; the normal crosses it to the West lap's far side (the step found, see "
                          "west_lat_m). The side's real edge is the west corner's outline (merge.west_corner)")
        else:
            q["reads"] = "no clean step"
        merge_rows.append(q)
    w = res["west"]; wt = w["tangent"]
    item3 = {
        "_doc": "ledger 0097 round 5, owed item 3: the north loop's 42 m of carried edges (north_loop.json's rows: R row s "
                "0-19, the fork's mouth; R 988-1001 and L 996-1001, the merge's mouth; L 254-260), the asphalt's edge read "
                "off the 2018 lidar's INTENSITY. off_osm_m is the rows' own convention (metres outward off OSM's line at "
                "the row's s); off_osm_naip_def_m takes off the registration below (c and the shift), giving what NAIP's "
                "reader would have read: the value a carried row would take. o_past_built_edge_m is past the north loop's "
                "built lane edge (source/full/connectors.full.json).",
        "source": src, "params": params,
        "registration": reg_doc,
        "l254_260": {"_doc": "L rows 240-272, the carried 254-260 inside them; NAIP's rows beside them read on the same "
                             "faint edge line (round 4's second read)",
                     "threshold": res["thr254"], "rows": l254,
                     "naip_rows_beside_minus_lidar_naip_def_m": {"rows": len(l254_check),
                                                                 "median": round(float(np.median(l254_check)), 2),
                                                                 "p10_p90": _r(np.percentile(l254_check, [10, 90]))},
                     "beyond": "past the asphalt a grey strip (intensity ~2,200-2,900, between asphalt ~800 and the prairie "
                               "~5,300) runs 3-3.5 m before the prairie: round 4's 'verge greying into the prairie'; not "
                               "asphalt by the lidar"},
        "fork_r0_19": {"_doc": "R rows 0-44: the first dark -> bright step past the north loop's built right edge, out to 16 "
                               "m. Rows 0-12: the step is the West lap's far edge (the fork is one pavement: the north loop "
                               "has no right edge of its own there); 14-22: no clean step (the junction's lighter paving "
                               "and the gore's tip); from row 24 the gore's grass: the north loop's own right edge",
                       "threshold": _r(res["fork_T"], 0), "rows": fork_rows,
                       "gore_nose": {"_doc": "the grass between the two roads, read by rays every 2 deg from a point inside it "
                                             "(grass -> asphalt): its southern apex is where the north loop's own right edge "
                                             "begins; south of it the fork is one pavement",
                                     "apex": res["gore"]["apex"], "outline": res["gore"]["outline"],
                                     "threshold_T": round(res["gore"]["T"]),
                                     "north_loop_first_clean_edge": pick(gore_n, ("row_s", "own_s", "o_past_built_edge_m", "E", "N", "lonlat")),
                                     "west_lap_first_clean_left_edge": pick(gore_w, ("west_s", "o_past_built_edge_m", "E", "N", "lonlat"))},
                       "west_lap_left_edge": [pick(q, ("west_s", "o_past_built_edge_m", "E", "N", "score", "t_sens_m", "kept"))
                                              for q in res["fork_west"]]},
        "merge": {"_doc": "R rows 986-1001 and L rows 994-1001: along each row's normal from the north loop's own line, the "
                          "first dark -> bright step 2-30 m out, and which outline it lies on",
                  "rows": merge_rows,
                  "west_corner": {"_doc": "the merge's WEST corner (the bellmouth round 4 built at NAIP's R 14.0 m), read as "
                                          "the east corner is (merge_east_fillet.json)",
                                  "asphalt_edge_radius_m": wt["R"],
                                  "fit": {"median_dev_m": wt["median_dev_m"], "points": wt["n_points"],
                                          "prominence": wt["prominence"], "at_grid_end": wt["at_grid_end"],
                                          "arc_m": wt["arc_m"], "centre": ll_pt(wt["O"]),
                                          "tangent_on_west_lap_edge": ll_pt(wt["Ta"]), "tangent_on_ladder_edge": ll_pt(wt["Tb"])},
                                  "free_circle": w["free"], "legs": w["legs"], "Kreal": w["Kreal"], "phi_deg": w["phi_deg"],
                                  "leg_windows": w["leg_windows"],
                                  "radius_along_the_outline": w["profile"],
                                  "mouth_radii_built_frame_with_the_lidar": res["built"]["full_north#0#0|end|-1"],
                                  "round4_naip_radius_m": 14.0,
                                  "outline": w["outline"]}},
    }
    for nm, obj in (("merge_east_fillet.json", item1), ("north_stripes.json", item2), ("carried_edges.json", item3)):
        (outdir / nm).write_text(json.dumps(obj, indent=1, default=_jd) + "\n", encoding="utf-8")
        print(f"[out] {outdir / nm}: {(outdir / nm).stat().st_size:,} B")
    print(f"[item1] R {tr['R']} (dev {tr['median_dev_m']}), free {e['free']['R_m']}, tightest {item1['measured']['radius_along_the_outline']['tightest_m']}, "
          f"kerb blocks depth p50/p90/max {kb_p50}/{kb_p90}/{kb_max}, paved R {item1['measured']['paved_outline']['radius_m']}")
    for nm, r in stripes_out.items():
        print(f"[item2] {nm}: s {r['s0_s1']} tapered {r['s0_s1_tapered']} in_m {r['in_m']} (photo {r['in_m_photo_frame']}), edge line {r['edge_line_either_side_o_m']}")
    print(f"[item3] l254 check {item3['l254_260']['naip_rows_beside_minus_lidar_naip_def_m']}; gore apex {res['gore']['apex']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    rz = Path(a[a.index("--reuse") + 1]) if "--reuse" in a else None
    if a[0] == "plan":
        plan(Path(a[1]).resolve(), Path(a[2]), rz)
    elif a[0] == "fetch":
        fetch(Path(a[1]))
    elif a[0] == "extract":
        extract(Path(a[1]).resolve(), Path(a[2]), Path(a[3]), rz)
    elif a[0] == "measure":
        measure(Path(a[1]).resolve(), Path(a[2]), Path(a[3]))
    else:
        raise SystemExit(__doc__)

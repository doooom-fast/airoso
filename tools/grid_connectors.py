"""Fill out a free roam's street grid from the real OSM streets around the lap (ledger 0063, Kevin 2026-11-01: "fill out the
grid around sand creek for its free roam version"). Real roads only (L1): every piece is an OSM way out of the track's own
cached data/osm.ways.json, nothing routed, nothing invented; pieces that run on the lap are cut away.

    python tools/grid_connectors.py <project-dir>

Reads track.config.json route.grid:
    classes        {highway class: width m} the classes to take; widths are [invented] (the cache carries no lanes)
    min_piece_m    a piece shorter than this is dropped (a stub of a way that mostly runs on the lap)
    on_lap_pad_m   a point within the lap's half width + this is on the lap
    parallel_m     a piece whose median distance from the lap is under this is the lap's other carriageway: dropped
    terrain_inset_m  the terrain grid must reach this far past a piece (heightfield.meta.json bbox_swne)
    exclude        piece names left out, each with its reason in the config (a piece the kn5 gate shows cutting a graded bank)

Ways meeting end to end are joined first, so an OSM way split at a tag change is one road. Each piece keeps one on-lap point at
each end so it reaches the lap's pavement; build_mesh levels that end onto the lap. Heights are USGS 3DEP along the piece's own
line, despiked, smoothed and grade-capped (tools/route_connectors.py), cached in data/grid.3dep.json. Where two pieces meet
they are eased to one height over GRID_EASE_M, so a crossing has no step.

Writes data/connectors.local.json (build_mesh ribbons each as 1ROAD_<name>) and data/grid.report.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))
sys.path.insert(0, str(AIROSO / "tools"))
from route_connectors import _despike_smooth_cap, _mpd, _resample  # noqa: E402

RESAMPLE_M = 3.0
JOIN_KEY = 1e-6        # way ends within ~0.1 m are one node
MEET_R_M = 2.5         # [invented] two pieces closer than this at a point meet there
GRID_EASE_M = 18.0     # [invented] the reach of the ease to a shared height either side of a meeting


def _key(p):
    return (round(p[0] / JOIN_KEY), round(p[1] / JOIN_KEY))


def join_ways(ways):
    """[(class, [(lon, lat), ...])]: ways meeting end to end at a node only they share become one line, the wider class kept"""
    rank = {c: i for i, c in enumerate(("primary", "secondary", "tertiary", "unclassified", "residential"))}
    ways = [(c, list(g)) for c, g in ways]
    while True:
        ends = {}
        for i, (_c, g) in enumerate(ways):
            ends.setdefault(_key(g[0]), []).append(i)
            ends.setdefault(_key(g[-1]), []).append(i)
        for ids in ends.values():
            if len(ids) == 2 and ids[0] != ids[1]:
                a, b = ids
                ca, ga = ways[a]
                cb, gb = ways[b]
                if _key(ga[-1]) == _key(gb[0]):
                    g = ga + gb[1:]
                elif _key(ga[-1]) == _key(gb[-1]):
                    g = ga + gb[::-1][1:]
                elif _key(ga[0]) == _key(gb[-1]):
                    g = gb + ga[1:]
                else:
                    g = gb[::-1] + ga[1:]
                ways[a] = (min(ca, cb, key=lambda c: rank.get(c, 9)), g)
                del ways[b]
                break
        else:
            return ways


class Hash:
    """nearest point lookup on a 30 m grid"""

    def __init__(self, pts, cell=30.0):
        self.cell = cell
        self.g = {}
        for k, p in enumerate(pts):
            self.g.setdefault((int(p[0] // cell), int(p[1] // cell)), []).append(k)
        self.pts = pts

    def near(self, x, z, reach=1):
        c = (int(x // self.cell), int(z // self.cell))
        best, bk = float("inf"), None
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                for k in self.g.get((c[0] + dx, c[1] + dz), ()):
                    d = math.hypot(self.pts[k][0] - x, self.pts[k][1] - z)
                    if d < best:
                        best, bk = d, k
        return best, bk


def pieces_off_lap(line, lap, lap_half, pad):
    """contiguous runs of a resampled line that are off the lap, one on-lap point kept at each end"""
    on = []
    for x, z in line:
        d, k = lap.near(x, z)
        on.append(k is not None and d <= lap_half[k] + pad)
    out, i, n = [], 0, len(line)
    while i < n:
        if on[i]:
            i += 1
            continue
        j = i
        while j < n and not on[j]:
            j += 1
        out.append(line[max(0, i - 1):min(n, j + 1)])
        i = j
    return out


def _length(run):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(run, run[1:]))


def ease_meetings(conns):
    """two pieces that meet share one height there: each eased to the mean over GRID_EASE_M (mutates points_xyz_m's y)"""
    flat = []
    for ci, c in enumerate(conns):
        for pi, p in enumerate(c["points_xyz_m"]):
            flat.append((p[0], p[2], ci, pi))
    h = Hash([(f[0], f[1]) for f in flat], cell=MEET_R_M * 2)
    meets = {}
    for f in flat:
        cell = (int(f[0] // h.cell), int(f[1] // h.cell))
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in h.g.get((cell[0] + dx, cell[1] + dz), ()):
                    o = flat[k]
                    if o[2] <= f[2]:
                        continue
                    d = math.hypot(o[0] - f[0], o[1] - f[1])
                    key = (f[2], o[2], round(f[0] / 12.0), round(f[1] / 12.0))
                    if d <= MEET_R_M and (key not in meets or d < meets[key][0]):
                        meets[key] = (d, f[2], f[3], o[2], o[3])
    edits = {}
    for _d, a, i, b, j in meets.values():
        t = (conns[a]["points_xyz_m"][i][1] + conns[b]["points_xyz_m"][j][1]) / 2.0
        edits.setdefault(a, []).append((i, t))
        edits.setdefault(b, []).append((j, t))
    for ci, rows in edits.items():
        pts = conns[ci]["points_xyz_m"]
        ys = [p[1] for p in pts]
        reach = GRID_EASE_M / RESAMPLE_M
        dy = [0.0] * len(pts)
        wt = [0.0] * len(pts)
        for i0, t in rows:
            for k in range(max(0, int(i0 - reach)), min(len(pts), int(i0 + reach) + 1)):
                u = 1.0 - abs(k - i0) / reach
                w = u * u * (3.0 - 2.0 * u)
                if w > wt[k]:           # the nearest meeting wins a shared stretch
                    wt[k], dy[k] = w, (t - ys[i0]) * w
        for k, p in enumerate(pts):
            p[1] = round(ys[k] + dy[k], 3)
    return len(meets)


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("route") or {}).get("grid")
    if not spec:
        print("[grid] no route.grid declared: nothing to do")
        return
    classes = spec["classes"]
    pad = float(spec.get("on_lap_pad_m", 6.0))
    min_piece = float(spec.get("min_piece_m", 40.0))
    parallel = float(spec.get("parallel_m", 25.0))
    inset = float(spec.get("terrain_inset_m", 60.0))
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    o = local["origin"]
    lon0, lat0, elev0 = o["lon"], o["lat"], o["elev_m"]
    m_lon, m_lat = _mpd(lat0)
    main = [(p[0], p[2]) for p in local["points_xyz_m"]]
    lap = Hash(main)
    lap_half = [w / 2.0 for w in local["widths_m"]]
    s_, w_, n_, e_ = json.loads((data / "heightfield.meta.json").read_text(encoding="utf-8"))["bbox_swne"]
    xmin, xmax = (w_ - lon0) * m_lon + inset, (e_ - lon0) * m_lon - inset
    zmin, zmax = (s_ - lat0) * m_lat + inset, (n_ - lat0) * m_lat - inset
    inside = lambda x, z: xmin <= x <= xmax and zmin <= z <= zmax   # noqa: E731

    raw = json.loads((data / "osm.ways.json").read_text(encoding="utf-8"))
    ways = [(w["highway"], [tuple(q) for q in w["geom"]]) for w in raw if w.get("highway") in classes and len(w.get("geom") or []) >= 2]
    joined = join_ways(ways)

    runs, dropped = [], {"short": 0, "parallel": 0, "outside": 0}
    for cls, g in joined:
        line = _resample([((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in g], RESAMPLE_M)
        k, n = 0, len(line)
        # the terrain only reaches so far: a way leaving the grid is cut at its edge
        while k < n:
            if not inside(*line[k]):
                k += 1
                continue
            j = k
            while j < n and inside(*line[j]):
                j += 1
            for run in pieces_off_lap(line[k:j], lap, lap_half, pad):
                if _length(run) < min_piece:
                    dropped["short"] += 1
                    continue
                ds = sorted(lap.near(x, z, reach=2)[0] for x, z in run)
                if ds[len(ds) // 2] < parallel:
                    dropped["parallel"] += 1
                    continue
                runs.append((cls, run))
            k = j
        if not any(inside(*p) for p in line):
            dropped["outside"] += 1

    # 3DEP along every piece, cached: the source data is public and the pipeline re-runs offline (L2)
    from scripts.elevation import usgs_3dep
    cache_p = data / "grid.3dep.json"
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    lonlat_of = lambda x, z: (round(lon0 + x / m_lon, 7), round(lat0 + z / m_lat, 7))   # noqa: E731
    want = sorted({lonlat_of(x, z) for _c, run in runs for x, z in run})
    missing = [p for p in want if f"{p[0]},{p[1]}" not in cache]
    if missing:
        print(f"[grid] 3DEP: {len(missing)} of {len(want)} points to fetch")
        for p, v in zip(missing, usgs_3dep.sample_points(missing)):
            cache[f"{p[0]},{p[1]}"] = v
        cache_p.write_text(json.dumps(cache), encoding="utf-8")

    conns, per_class = [], {}
    exclude = set(spec.get("exclude") or [])
    for k, (cls, run) in enumerate(sorted(runs, key=lambda r: (-_length(r[1]), r[0]))):
        if f"grid_{cls}_{k}" in exclude:
            continue
        zs = [cache[f"{p[0]},{p[1]}"] - elev0 for p in (lonlat_of(x, z) for x, z in run)]
        ys = _despike_smooth_cap(zs, RESAMPLE_M)
        conns.append({"name": f"grid_{cls}_{k}", "kind": "connector",
                      "points_xyz_m": [[round(x, 3), round(y, 3), round(z, 3)] for (x, z), y in zip(run, ys)],
                      "widths_m": [float(classes[cls])] * len(run)})
        r = per_class.setdefault(cls, {"pieces": 0, "km": 0.0})
        r["pieces"] += 1
        r["km"] = round(r["km"] + _length(run) / 1000.0, 2)
    meetings = ease_meetings(conns)

    base = {"connectors": []}
    (data / "connectors.local.json").write_text(json.dumps({**base, "connectors": conns}), encoding="utf-8")
    rep = {"_doc": "tools/grid_connectors.py: the free roam's street grid, real OSM ways only (L1)", "ways_taken": len(ways),
           "joined_lines": len(joined), "per_class": per_class, "pieces": len(conns),
           "km": round(sum(r["km"] for r in per_class.values()), 2), "dropped": dropped, "meetings_eased": meetings}
    (data / "grid.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[grid] {len(conns)} pieces, {rep['km']} km, {meetings} meetings eased, per class {per_class}, dropped {dropped}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/grid_connectors.py <project-dir>")
    build(sys.argv[1])

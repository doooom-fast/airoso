"""THE GRID'S MAP-EDGE CUT, REACHED: a free-roam street that stops where OSM's road goes on is walked on along OSM's own
way to the road it meets (ledger 0098; ledger 0086 "Disconnected roads located": Kevin 2026-11-13, "San creek has many
disconnected roads but drives well otherwise").

The cause (ledger 0086, checked against the code): tools/grid_connectors.py clips every OSM way TERRAIN_INSET_M inside
the SOURCE track's 3DEP grid (heightfield.meta.json bbox_swne), and Sand Creek's source grid ends at lat 39.798823
(local z 1313.9 in the grid's frame). The port's own grid (lm_intake.heightfield "port") reaches 39.801706, but the grid
was never re-run on it: re-running would rename every piece (grid_connectors names pieces by length rank) and every
re-resampled point would need a 3DEP point fetch and a new lidar profile (lm_intake.connector_profiles checks each point's
plan position). So the clip is not moved; the pieces it cut are REACHED, additively, and no existing point moves:

  * a piece END named in track.config.json route.grid.reach is walked along the OSM way it lies on (data/osm.ways.json of
    the source track, the classes route.grid.classes takes, projected exactly as grid_connectors projects them), way to
    way through OSM's nodes (the straightest continuation, or toward the record's `via` points where a road forks),
    resampled every RESAMPLE_M as grid_connectors resamples, until the record's `stop`:
      {"x_max" | "x_min" | "z_max" | "z_min": v}   the walk is cut where it crosses that line (the grid's own extent)
      {"on": "MAINLINE" | <piece>}                 the first point on that road (grid_connectors' own on-lap rule: within
                                                   its half width + route.grid.on_lap_pad_m), kept, as grid_connectors
                                                   keeps one on-lap point at each end; trim_connectors cuts it there
  * heights: the source lidar where it reads the point (tools/lidar_connector_profile.profile, its radius, its minimum
    returns and its --surface rule, on a tile cache; a missing tile is never fetched, it is no reading), else the port's
    3DEP grid (data/heightfield.npy, bilinear) moved by the lidar - 3DEP offset interpolated between measured neighbours
    (lidar_connector_profile.fill, its rule). The first EASE_M are eased onto the piece's own end height (smoothstep,
    trim_connectors' BLEND_M), so the joint has no step. Each point records its source.
  * THE FRAME. The grid's points are in grid_connectors' frame (tools/route_connectors._mpd, a sphere); the lidar tiles are
    in scripts.geometry.projection's (the ellipsoid; the lap's frame too). A grid point is read in the lidar at the SAME
    lon / lat (x * KX, z * KZ, recorded), so the heights are the street's own. [The 99 streets of
    source/connector_profiles.lidar.round_i.json were read at the grid's x / z taken as lidar x / z: 0.25 % of x toward
    the origin, 0.15 % of z away from it, so 4.7 m / 2.0 m off the street at the grid's east / north edge; ledger 0098
    measures what that moved.]

Writes the record lm_intake applies (lm_intake.grid_reach, tools/lm_engine_intake.apply_grid_reach): per reached end the
existing end's plan position (checked there, 1 cm) and the height the joint was eased onto (from_y: if the piece's end
height has changed since, e.g. a later lidar profile, lm_intake moves the new points by the difference faded over ease_m,
the same smoothstep, so the joint never steps), the new points in order away from it, their widths (the piece's end
width: grid_connectors' class width, [invented] as every grid width) and their height sources. numpy only.

    python tools/grid_reach.py <port-project-dir> --tiles <dir of tile_i_j.npz> [--out <json>]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
for _p in (str(AIROSO), str(AIROSO / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from route_connectors import _mpd, _resample  # noqa: E402

RESAMPLE_M = 3.0       # = tools/grid_connectors.RESAMPLE_M
SNAP_M = 1.5           # [invented] a piece end lies on an OSM way when within this of it
NODE_M = 0.05          # two way vertices this close are one OSM node (grid_connectors joins at ~0.1 m)
TURN_MAX_DEG = 60.0    # [invented] past a node, a way turning more than this from the walk is not its continuation
HEADING_M = 8.0        # = trim_connectors.HEADING_M: a way's direction at a node, read this far along it
VIA_NEAR_M = 6.0       # [invented] a via point is passed when the walk comes this close
VIA_LOOK_M = 150.0     # [invented] at a fork, each branch is read this far for its closest approach to the via point
MAX_WALK_M = 4000.0    # [invented] no walk is longer
EASE_M = 30.0          # = trim_connectors.BLEND_M
DENSE_M = 0.5          # [sampling] the stop rules read the walk every this


def _key(x, z):
    return (round(x / NODE_M), round(z / NODE_M))


def load_ways(osm_ways, classes, origin):
    """OSM ways of the grid's classes as polylines in the GRID's frame (grid_connectors' own projection)"""
    m_lon, m_lat = _mpd(origin["lat"])
    out = []
    for w in osm_ways:
        if w.get("highway") in classes and len(w.get("geom") or []) >= 2:
            out.append((w["highway"], [((lo - origin["lon"]) * m_lon, (la - origin["lat"]) * m_lat) for lo, la in w["geom"]]))
    return out


def _seg_proj(px, pz, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (pz - a[1]) * dz) / L2))
    return math.hypot(px - (a[0] + t * dx), pz - (a[1] + t * dz)), t


def _unit(dx, dz):
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L


def _ahead(V, i, s, look=HEADING_M):
    """the walk's points along way V from vertex i in direction s, up to `look` m (vertex i excluded)"""
    out, acc, prev, j = [], 0.0, V[i], i + s
    while 0 <= j < len(V):
        acc += math.hypot(V[j][0] - prev[0], V[j][1] - prev[1])
        out.append(V[j])
        prev = V[j]
        if acc >= look:
            break
        j += s
    return out


def _choose(cands, heading, via):
    """the candidate (way, vertex, step, heading, ahead polyline from the node) the walk takes: toward the next via point
    if any (the branch's closest approach to it over VIA_LOOK_M), else the straightest within TURN_MAX_DEG"""
    if not cands:
        return None
    if via:
        vx, vz = via[0]
        return min(cands, key=lambda c: min(_seg_proj(vx, vz, a, b)[0] for a, b in zip(c[4], c[4][1:])))
    best, bt = None, None
    for c in cands:
        h = c[3]
        t = math.degrees(math.acos(max(-1.0, min(1.0, h[0] * heading[0] + h[1] * heading[1]))))
        if t <= TURN_MAX_DEG and (bt is None or t < bt):
            best, bt = c, t
    return best


def walk(ways, start, heading, via=()):
    """the polyline OSM's ways draw from `start` (a piece end, on a way) onward, `heading` the piece's outward direction.
    Returns (points from start, [notes])."""
    via = [tuple(v) for v in via]
    nodes = {}
    for wi, (_c, V) in enumerate(ways):
        for vi, p in enumerate(V):
            nodes.setdefault(_key(*p), []).append((wi, vi))
    # the first way: every segment within SNAP_M of the start, both directions
    cands = []
    for wi, (_c, V) in enumerate(ways):
        for i in range(len(V) - 1):
            d, t = _seg_proj(start[0], start[1], V[i], V[i + 1])
            if d > SNAP_M:
                continue
            for s in (1, -1):
                nxt = i + 1 if s == 1 else i
                if t >= 1.0 and s == 1:
                    nxt = i + 2
                if t <= 0.0 and s == -1:
                    nxt = i - 1
                if not 0 <= nxt < len(V):
                    continue
                h = _unit(V[nxt][0] - start[0], V[nxt][1] - start[1])
                ahead = [tuple(start), V[nxt]] + _ahead(V, nxt, s, VIA_LOOK_M)
                cands.append((wi, nxt, s, h, ahead))
    c = _choose(cands, heading, via)
    if c is None:
        return [start], ["no OSM way within %.1f m of the end, or none goes on" % SNAP_M]
    pts, notes = [tuple(start)], []
    wi, vi, s = c[0], c[1], c[2]
    acc = 0.0
    while acc < MAX_WALK_M:
        V = ways[wi][1]
        while 0 <= vi < len(V):
            p = V[vi]
            if math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-6:
                acc += math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1])
                pts.append(p)
                if via and math.hypot(p[0] - via[0][0], p[1] - via[0][1]) <= VIA_NEAR_M:
                    notes.append(f"via ({via[0][0]:.1f}, {via[0][1]:.1f}) passed")
                    via.pop(0)
            vi += s
        # the way's end node: its continuation
        end = pts[-1]
        hd = _unit(end[0] - pts[-2][0], end[1] - pts[-2][1]) if len(pts) >= 2 else heading
        cands = []
        for wj, vj in nodes.get(_key(*end), []):
            if wj == wi:
                continue
            Vj = ways[wj][1]
            for s2 in (1, -1):
                if not 0 <= vj + s2 < len(Vj):
                    continue
                ah = _ahead(Vj, vj, s2)
                cands.append((wj, vj + s2, s2, _unit(ah[-1][0] - end[0], ah[-1][1] - end[1]),
                              [end] + _ahead(Vj, vj, s2, VIA_LOOK_M)))
        c = _choose(cands, hd, via)
        if c is None:
            notes.append(f"OSM's road ends at ({end[0]:.1f}, {end[1]:.1f})")
            break
        wi, vi, s = c[0], c[1], c[2]
    return pts, notes


def cut_at_stop(pts, stop, lines, pad):
    """the walk up to its stop rule (module doc): (points, how it stopped) or (None, why not)"""
    dense = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(math.ceil(L / DENSE_M)))
        dense += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
    if "on" in stop:
        P, W = lines[stop["on"]]
        for k, q in enumerate(dense[1:], 1):
            best = min((_seg_proj(q[0], q[1], (P[i][0], P[i][2]), (P[i + 1][0], P[i + 1][2]))[0] - W[i] / 2.0)
                       for i in range(len(P) - 1))
            if best <= pad:
                return dense[:k + 1], f"on {stop['on']} {best + pad:.1f} m from its centre line"
        return None, f"never on {stop['on']}"
    (key, v), = [(k, float(x)) for k, x in stop.items() if k in ("x_max", "x_min", "z_max", "z_min")]
    ax = 0 if key[0] == "x" else 1
    sign = 1.0 if key.endswith("max") else -1.0
    for k, (a, b) in enumerate(zip(dense, dense[1:])):
        if sign * (b[ax] - v) >= 0.0:
            t = (v - a[ax]) / ((b[ax] - a[ax]) or 1.0)
            return dense[:k + 1] + [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)], f"{key} {v}"
    return None, f"never crosses {key} {v}"


class TileCache:
    """tools/lidar_connector_profile.Ept's tile(), read-only: a missing tile is empty (no reading), never fetched"""

    def __init__(self, tiles: Path):
        self.dir = Path(tiles)
        self.missing = set()

    def tile(self, i, j):
        import numpy as np
        p = self.dir / f"tile_{i}_{j}.npz"
        if not p.exists():
            self.missing.add((i, j))
            z = np.zeros(0)
            return z, z, z, np.zeros(0, np.uint8)
        d = np.load(p)
        return d["E"], d["N"], d["Z"], d["C"]


def heightfield_at(proj: Path, origin):
    """the port's 3DEP grid, bilinear at a grid-frame (x, z), local frame (elev - origin.elev_m)"""
    import numpy as np
    H = np.load(proj / "data" / "heightfield.npy")
    meta = json.loads((proj / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
    s_, w_, n_, e_ = meta["bbox_swne"]
    ny, nx = H.shape
    m_lon, m_lat = _mpd(origin["lat"])

    def at(x, z):
        lon, lat = origin["lon"] + x / m_lon, origin["lat"] + z / m_lat
        fx = (lon - w_) / (e_ - w_) * (nx - 1)
        fy = (n_ - lat) / (n_ - s_) * (ny - 1)                  # row 0 = north
        if not (0 <= fx <= nx - 1 and 0 <= fy <= ny - 1):
            raise SystemExit(f"[grid_reach] ({x:.1f}, {z:.1f}) lies outside the port's 3DEP grid")
        i0, j0 = min(int(fx), nx - 2), min(int(fy), ny - 2)
        tx, ty = fx - i0, fy - j0
        h = (H[j0, i0] * (1 - tx) * (1 - ty) + H[j0, i0 + 1] * tx * (1 - ty)
             + H[j0 + 1, i0] * (1 - tx) * ty + H[j0 + 1, i0 + 1] * tx * ty)
        return float(h) - float(origin["elev_m"])
    return at


def frame_scale(origin):
    """(KX, KZ): a grid-frame x / z times these is the lidar / lap frame's at the same lon / lat"""
    from scripts.geometry.projection import _meters_per_degree
    gs, ge = _mpd(origin["lat"]), _meters_per_degree(origin["lat"])
    return ge[0] / gs[0], ge[1] / gs[1]


def heights(pts_xz, tiles: TileCache, hf, origin):
    """(y per point, source per point, bridge returns per point): module doc"""
    import lidar_connector_profile as lcp
    kx, kz = frame_scale(origin)
    lid = [(x * kx, 0.0, z * kz) for x, z in pts_xz]
    meas = lcp.profile(tiles, lid, surface=True)
    base = [(x, hf(x, z), z) for x, z in pts_xz]
    if not any(m[0] is not None for m in meas):
        return [b[1] for b in base], ["3dep"] * len(base), [0] * len(base)
    ys = lcp.fill(base, meas)
    return ys, ["lidar" if m[0] is not None else "3dep+offset" for m in meas], [m[2] for m in meas]


def smoothstep(x):
    x = 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)
    return x * x * (3.0 - 2.0 * x)


def reach(proj: Path, tiles_dir: Path):
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    grid = (cfg.get("route") or {}).get("grid") or {}
    spec = grid.get("reach") or []
    if not spec:
        raise SystemExit("[grid_reach] track.config.json route.grid.reach names no piece end")
    src = AIROSO / "tracks" / str((cfg.get("lm_intake") or {})["source_track"])
    conns = json.loads((src / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    prof_p = (cfg.get("lm_intake") or {}).get("connector_profiles")
    prof = json.loads((proj / prof_p).read_text(encoding="utf-8"))["connectors"] if prof_p else {}
    for c in conns:                                       # the heights lm_intake hands on (its profiles applied)
        pr = prof.get(c["name"])
        if pr is not None:
            for p, y in zip(c["points_xyz_m"], pr["y"]):
                p[1] = float(y)
    by = {c["name"]: c for c in conns}
    local = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    origin = local["origin"]
    lines = {"MAINLINE": (local["points_xyz_m"], local["widths_m"])}
    lines.update({n: (c["points_xyz_m"], c["widths_m"]) for n, c in by.items()})
    ways = load_ways(json.loads((src / "data" / "osm.ways.json").read_text(encoding="utf-8")), grid["classes"], origin)
    pad = float(grid.get("on_lap_pad_m", 6.0))
    tiles = TileCache(tiles_dir)
    hf = heightfield_at(proj, origin)
    kx, kz = frame_scale(origin)
    out = []
    for r in spec:
        name, end = r["piece"], r["end"]
        if name not in by or end not in ("start", "end"):
            raise SystemExit(f"[grid_reach] {name} {end}: no such piece end in the source's connectors")
        P = [list(p) for p in by[name]["points_xyz_m"]]
        W = list(by[name]["widths_m"])
        seq = P if end == "end" else P[::-1]                 # walking away from the end: seq[-1] is the end
        e, e2 = seq[-1], seq[-2]
        hdg = _unit(e[0] - e2[0], e[2] - e2[2])
        path, notes = walk(ways, (e[0], e[2]), hdg, r.get("via") or ())
        cut, how = cut_at_stop(path, r["stop"], lines, pad)
        if cut is None:
            raise SystemExit(f"[grid_reach] {name} {end}: {how} ({'; '.join(notes)})")
        new = _resample(cut, RESAMPLE_M)[1:]
        if math.hypot(new[-1][0] - cut[-1][0], new[-1][1] - cut[-1][1]) > 1e-6:
            new.append(cut[-1])
        ys, srcs, brs = heights([(e[0], e[2])] + new, tiles, hf, origin)
        y_end, ys, srcs, brs = ys[0], ys[1:], srcs[1:], brs[1:]
        acc, prev = 0.0, (e[0], e[2])
        dy0 = e[1] - y_end                                    # the joint: onto the piece's own end height
        for k, q in enumerate(new):
            acc += math.hypot(q[0] - prev[0], q[1] - prev[1])
            prev = q
            ys[k] = round(ys[k] + dy0 * smoothstep(1.0 - acc / EASE_M), 3)
        pts = [[round(q[0], 3), y, round(q[1], 3)] for q, y in zip(new, ys)]
        jumps = [abs(b - a) for a, b in zip([e[1]] + ys, ys)]
        rec = {"piece": name, "end": end, "from_xz": [round(e[0], 3), round(e[2], 3)], "from_y": round(e[1], 3),
               "ease_m": EASE_M, "points_xyz_m": pts,
               "widths_m": [float(W[-1] if end == "end" else W[0])] * len(pts), "height_source": srcs,
               "bridge_returns": brs, "length_m": round(acc, 1), "stopped": how, "walk": notes,
               "lidar_share": round(sum(s == "lidar" for s in srcs) / len(srcs), 3),
               "max_neighbour_jump_m": round(max(jumps), 3), "why": r.get("why", "")}
        out.append(rec)
        lines[name] = ((P + pts) if end == "end" else (pts[::-1] + P),
                       (W + rec["widths_m"]) if end == "end" else (rec["widths_m"] + W))
        by[name]["points_xyz_m"], by[name]["widths_m"] = lines[name]
        print(f"[grid_reach] {name} ({end}): +{len(pts)} points, {acc:.1f} m along OSM, {how}; heights: "
              f"{sum(s == 'lidar' for s in srcs)} lidar, {sum(s != 'lidar' for s in srcs)} 3DEP + offset; "
              f"largest neighbour step {rec['max_neighbour_jump_m']} m; joint eased {dy0:+.2f} m")
    return {"_doc": "tools/grid_reach.py (ledger 0098): the grid's map-edge cut reached, additively; applied by "
                    "tools/lm_engine_intake.py (lm_intake.grid_reach). Each record: an existing piece end (from_xz, the "
                    "grid's frame), the points walked on along OSM's way away from it, their widths (the piece's) and "
                    "their height sources (lidar = tools/lidar_connector_profile.profile --surface at the same lon / lat; "
                    "3dep+offset = the port's 3DEP grid moved by the interpolated lidar - 3DEP offset)",
            "frame": {"grid": "tools/route_connectors._mpd (sphere)", "lidar": "scripts.geometry.projection",
                      "kx": round(kx, 7), "kz": round(kz, 7)},
            "tiles_missing": sorted([list(t) for t in tiles.missing]), "reach": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--tiles", required=True, help="the lidar tile cache (tile_<i>_<j>.npz, as lidar_connector_profile "
                                                   "writes); nothing is fetched")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    proj = Path(a.project).resolve()
    rec = reach(proj, Path(a.tiles))
    out = Path(a.out) if a.out else proj / "source" / "grid_reach.json"
    out.write_text(json.dumps(rec, indent=None), encoding="utf-8")
    print(f"[grid_reach] {len(rec['reach'])} end(s) -> {out}; tiles not in the cache: {len(rec['tiles_missing'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Denver Grand Prix: the lap's draft line, its profile, its widths and the 3DEP grid, written as the files a source
track's data stages leave for tools/lm_engine_intake.py (data/centerline.geojson, data/centerline.local.json,
data/heightfield.npy + .meta.json). Ledger 0096, "0.1.0 (Drive 1)".

Why a script and not scripts/build.sh's gps / elev / project / widths stages: the lap is already resolved on the
committed OSM extract (source/lap_route.py -> data/lap_line.plan.json, the OSM nodes in driving order), its profile is
already measured (data/lap_profile.3dep.json, USGS 3DEP 1 m cells every 2 m on OSM's lines), and the regional 3DEP
tiles are on the Mac. Nothing here fetches anything. The engine's own functions do the work: scripts.gps.fillet
(the polygon rounded into a curve), scripts.gps.centerline (fold removal, the 3 m resample), scripts.geometry.projection
(lon/lat -> local ENU), scripts.elevation.heightfield (the median despike + light mean; no grade cap).

What is measured and what is not (every [invented] item is also in the ledger):
  - the line: OSM's street centrelines as of 2026-11-23T01:12:49Z (source/osm.json); its corners are rounded by
    route.fillet (round_nodes: inside OSM's own segments; declared corners: the radius in the config) [construction];
  - the heights: 3DEP 1 m bare earth along OSM's line (data/lap_profile.3dep.json), despiked (33 m median) and lightly
    meaned (9 m), keyed to this line by the OSM station of each point's foot on OSM's line; three spans replaced by a
    straight line between measured ends, each declared in track.config.json draft_line.straight_spans:
    Stout under the Convention Center (no ground return for 304 m; 3DEP is interpolated there) [invented],
    the 15th St pit (a 5 m DEM artefact) [invented], and the two creek bridges, held straight from abutment to
    abutment until the class-17 deck profile replaces them [invented];
  - the widths: draft_line.widths. "osm_lanes" = the OSM way's lanes tag x lane_m [invented] (provisional, NEVER
    shipped); "measured" = the file it names (the widths survey);
  - the ground grid: USGS 3DEP 1/3 arc-second tiles (about 10 m cells) on the Mac, sampled bilinearly on a 40 m
    lattice (the elevation stage's spacing) over the lap + draft_line.grid_margin_m.

    python tracks/denver-grand-prix/source/draft/draft_line.py --dem-dir DIR   (or DGP_DEM_DIR=DIR)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACK = HERE.parents[1]
AIROSO = TRACK.parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

from scripts.gps import centerline as cl_mod  # noqa: E402
from scripts.gps.fillet import fillet_ring, insert_point  # noqa: E402
from scripts.geometry.projection import project_to_local, _meters_per_degree  # noqa: E402
from scripts.elevation import heightfield as hf  # noqa: E402

DEM_DIR_ENV = "DGP_DEM_DIR"   # the folder holding the USGS_13_*.tif tiles (source/survey/DATA.md); never in git


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _foot_station(pts_xy, st, q):
    """station along a polyline (pts_xy, cumulative st) of the foot of q, and its distance"""
    best = (float("inf"), 0.0)
    for i in range(len(pts_xy) - 1):
        ax, ay = pts_xy[i]; bx, by = pts_xy[i + 1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / L2))
        px, py = ax + t * dx, ay + t * dy
        d = math.hypot(q[0] - px, q[1] - py)
        if d < best[0]:
            best = (d, st[i] + t * math.sqrt(L2))
    return best[1], best[0]


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if xs[m] <= x:
            lo = m
        else:
            hi = m
    t = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] * (1 - t) + ys[hi] * t


def _smooth_open(vals, half):
    n = len(vals)
    return [sum(vals[max(0, i - half):min(n, i + half + 1)]) / (min(n, i + half + 1) - max(0, i - half)) for i in range(n)]


def build(dem_dir: Path) -> dict:
    cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
    dl = cfg["draft_line"]
    route = cfg.get("route") or {}
    lap = json.loads((TRACK / "data" / "lap_line.plan.json").read_text(encoding="utf-8"))["nodes"]
    prof = json.loads((TRACK / "data" / "lap_profile.3dep.json").read_text(encoding="utf-8"))
    osm = json.loads((TRACK / "source" / "osm.json").read_text(encoding="utf-8"))
    ways = {w["id"]: w for w in osm["ways"]}

    ring = [(float(n["lon"]), float(n["lat"])) for n in lap]
    if math.dist(ring[0], ring[-1]) > 1e-9:
        raise SystemExit("[draft_line] lap_line.plan.json does not close on its first node")
    # 1. the polygon rounded into a curve (the engine's fillet), station 0 exactly at route.start_at
    fil = route.get("fillet") or {}
    ring, frep = fillet_ring(ring, corners=fil.get("corners") or (), round_nodes=bool(fil.get("round_nodes", True)),
                             arc_step_m=float(fil.get("arc_step_m", 1.0)), simplify_m=float(fil.get("simplify_m", 0.0)))
    body = ring[:-1]
    body, k, off = insert_point(body + [body[0]], route["start_at"])
    body = body[:-1]
    ring = body[k:] + body[:k] + [body[k]]
    ring = cl_mod.remove_folds(ring)
    if math.dist(ring[0], ring[-1]) > 1e-12:
        ring.append(ring[0])
    ring = cl_mod.resample(ring, cl_mod.RESAMPLE_SPACING_M)
    if math.dist(ring[0], ring[-1]) > 1e-12:
        ring[-1] = ring[0]
    n = len(ring)

    # 2. the OSM station of each point (its foot on OSM's own line, the profile's frame)
    m_lon, m_lat = _meters_per_degree(float(route["start_at"][0]))
    lon0, lat0 = float(route["start_at"][1]), float(route["start_at"][0])
    P = prof["points"]
    oxy = [((p["lon"] - lon0) * m_lon, (p["lat"] - lat0) * m_lat) for p in P]
    ost = [float(p["s"]) for p in P]
    oz = [float(p["z"]) for p in P]
    lap_len = float(prof["lap_length_m"])
    # close the profile on itself (its last sample is short of the seam)
    oxy.append(oxy[0]); ost.append(lap_len); oz.append(oz[0])
    import numpy as np
    A = np.array(oxy[:-1]); B = np.array(oxy[1:]); S0 = np.array(ost[:-1])
    D = B - A; L2 = np.maximum((D * D).sum(1), 1e-12)
    s_osm, foot_d = [], []
    prev = None
    for i, (lo, la) in enumerate(ring):
        q = np.array(((lo - lon0) * m_lon, (la - lat0) * m_lat))
        t = np.clip(((q - A) * D).sum(1) / L2, 0.0, 1.0)
        F = A + D * t[:, None]
        d = np.hypot(*(F - q).T)
        sc = S0 + t * np.sqrt(L2)
        if prev is not None:
            # continuity: never jump to the lap's other side (Kalamath and Santa Fe run 13 m apart)
            dd = np.abs((sc - prev + lap_len / 2) % lap_len - lap_len / 2)
            d = np.where(dd <= 60.0, d, np.inf)
        j = int(np.argmin(d))
        s_, d_ = float(sc[j]), float(d[j])
        s_osm.append(s_); foot_d.append(d_)
        prev = s_
    # 3. the profile: the straight spans laid on the RAW 2 m samples first (so no artefact is smeared past its ends),
    #    then the median despike + light mean (no cap), read at each station
    zr = oz[:]
    spans_rep = []
    wst = None
    if (TRACK / "source" / "widths" / "widths.json").exists():
        wst = json.loads((TRACK / "source" / "widths" / "widths.json").read_text(encoding="utf-8"))["stations"]

    def s_from_widths(sw):
        """a widths.json station (its own frame, 6,646.5 m) -> this profile's station, through the station's lon/lat"""
        ws = [float(r["s"]) for r in wst]
        j = max(0, min(len(ws) - 2, next((q for q in range(len(ws)) if ws[q] >= sw), len(ws) - 1) - 1))
        t = 0.0 if ws[j + 1] == ws[j] else (sw - ws[j]) / (ws[j + 1] - ws[j])
        lo = wst[j]["line_lonlat"][0] * (1 - t) + wst[j + 1]["line_lonlat"][0] * t
        la = wst[j]["line_lonlat"][1] * (1 - t) + wst[j + 1]["line_lonlat"][1] * t
        q = np.array(((lo - lon0) * m_lon, (la - lat0) * m_lat))
        tt = np.clip(((q - A) * D).sum(1) / L2, 0.0, 1.0)
        dd = np.hypot(*((A + D * tt[:, None]) - q).T)
        k = int(np.argmin(dd))
        return float(S0[k] + tt[k] * np.sqrt(L2[k]))

    for sp in dl.get("straight_spans") or []:
        if sp.get("frame") == "widths":
            a, b = s_from_widths(float(sp["from_s"])), s_from_widths(float(sp["to_s"]))
        else:
            a, b = float(sp["from_s"]), float(sp["to_s"])
        za = float(sp["z_from"]) if "z_from" in sp else _interp(ost, oz, a)
        zb = float(sp["z_to"]) if "z_to" in sp else _interp(ost, oz, b)
        if "z_level" in sp:
            za = zb = float(sp["z_level"])
        changed = 0
        for j, s_ in enumerate(ost):
            if a <= s_ <= b:
                zr[j] = za + (zb - za) * (s_ - a) / (b - a)
                changed += 1
        spans_rep.append({"name": sp["name"], "frame": sp.get("frame", "profile"), "given_s": [sp["from_s"], sp["to_s"]],
                          "profile_s": [round(a, 2), round(b, 2)], "z_from": round(za, 3), "z_to": round(zb, 3),
                          "samples_replaced": changed, "why": sp.get("why", "")})
    zs = hf.smooth_profile(zr[:-1], spacing_m=float(prof["step_m"]), median_m=hf.MEDIAN_WINDOW_M,
                           mean_m=float(dl.get("mean_window_m", 9.0)), passes=1)
    zs = zs + [zs[0]]
    z = [_interp(ost, zs, s) for s in s_osm]

    # 4. widths
    wcfg = dl["widths"]
    if wcfg["mode"] == "osm_lanes":
        lane_m = float(wcfg["lane_m"])
        node_s = []
        # the way that reaches each OSM node, at that node's OSM station
        nxy = [((nd["lon"] - lon0) * m_lon, (nd["lat"] - lat0) * m_lat) for nd in lap]
        nst = [0.0]
        for a_, b_ in zip(nxy, nxy[1:]):
            nst.append(nst[-1] + math.hypot(b_[0] - a_[0], b_[1] - a_[1]))
        scale = lap_len / nst[-1]
        lanes_by_way = {}
        for nd in lap:
            t = ways[nd["way"]]["tags"]
            ln = t.get("lanes")
            lanes_by_way[nd["way"]] = int(ln) if ln and str(ln).isdigit() else None
        over = {int(k): int(v) for k, v in (wcfg.get("lanes_untagged") or {}).items()}
        lanes_node = []
        for nd in lap:
            ln = lanes_by_way[nd["way"]]
            if ln is None:
                ln = over.get(nd["way"], int(wcfg.get("lanes_default", 2)))
            lanes_node.append(ln)
        # node i's way runs from node i-1 to node i
        w_raw = []
        for s in s_osm:
            s_ = s / scale
            j = next((q for q in range(1, len(nst)) if nst[q] >= s_), len(nst) - 1)
            w_raw.append(lanes_node[j] * lane_m)
        half = max(1, round(float(wcfg.get("smooth_m", 30.0)) / cl_mod.RESAMPLE_SPACING_M / 2))
        widths = [round(w, 2) for w in _smooth_open(w_raw, half)]
        widths[-1] = widths[0]
        wsrc = {"mode": "osm_lanes", "lane_m": lane_m, "status": "[invented] provisional, never shipped"}
    elif wcfg["mode"] == "measured":
        widths = None          # computed after the projection (section 5): the edges are absolute positions
        wsrc = {"mode": "measured", "file": "source/widths/widths.json",
                "md5": _md5(TRACK / "source" / "widths" / "widths.json")}
    else:
        raise SystemExit(f"[draft_line] draft_line.widths.mode {wcfg['mode']!r}")

    # 5. project about the configured origin (the start line), Y about origin.elev_m
    org = cfg["origin"]
    local = project_to_local(ring, z, (float(org["lon"]), float(org["lat"])), float(org["elev_m"]))
    shift_rep = None
    if widths is None:
        local, ring, widths, shift_rep = measured_edges(local, ring, s_osm, wst, cfg, frep, org)
    data = TRACK / "data"
    gj = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "geometry": {"type": "LineString", "coordinates": [[round(a, 8), round(b, 8)] for a, b in ring]},
        "properties": {"name": "centerline", "kind": "full", "closed": True, "length_m": round(sum(
            math.dist(local[i][0::2], local[i + 1][0::2]) for i in range(n - 1)), 1), "point_count": n,
            "widths_m": widths, "source": "tracks/denver-grand-prix/source/draft/draft_line.py"}}]}
    (data / "centerline.geojson").write_text(json.dumps(gj), encoding="utf-8")
    out = {
        "frame": "ENU local meters (X=east, Y=up, Z=north)",
        "origin": {"lon": float(org["lon"]), "lat": float(org["lat"]), "elev_m": float(org["elev_m"])},
        "true_north_rotation_deg": 0.0,
        "point_count": n,
        "points_xyz_m": [[round(x, 3), round(y, 3), round(zz, 3)] for x, y, zz in local],
        "widths_m": widths,
        "s_osm_m": [round(s, 2) for s in s_osm],
        "_doc": "tracks/denver-grand-prix/source/draft/draft_line.py; s_osm_m = each point's station on OSM's own line "
                "(data/lap_profile.3dep.json's frame), the key every measured survey row uses",
    }
    (data / "centerline.local.json").write_text(json.dumps(out), encoding="utf-8")

    # 6. the 3DEP grid (1/3 arc-second tiles on the Mac), 40 m lattice, row 0 = north
    import numpy as np
    import rasterio
    margin = float(dl.get("grid_margin_m", 470.0))
    spacing = float(dl.get("grid_spacing_m", 40.0))
    lons = [p[0] for p in ring]; lats = [p[1] for p in ring]
    midlat = (min(lats) + max(lats)) / 2
    mlat = margin / 111_000.0
    mlon = margin / (111_000.0 * math.cos(math.radians(midlat)))
    s_, w_, n_, e_ = min(lats) - mlat, min(lons) - mlon, max(lats) + mlat, max(lons) + mlon
    gy = spacing / 111_000.0
    gx = spacing / (111_000.0 * math.cos(math.radians(midlat)))
    nx = int(round((e_ - w_) / gx)) + 1
    ny = int(round((n_ - s_) / gy)) + 1
    grid = np.full((ny, nx), np.nan)
    tiles = sorted(Path(dem_dir).glob("USGS_13_*.tif"))
    used = []
    for tp in tiles:
        with rasterio.open(tp) as ds:
            b = ds.bounds
            if b.right < w_ or b.left > e_ or b.top < s_ or b.bottom > n_:
                continue
            used.append({"file": tp.name, "bytes": tp.stat().st_size})
            band = ds.read(1, masked=True)
            for j in range(ny):
                la = n_ - j * gy
                for i in range(nx):
                    lo = w_ + i * gx
                    if not (b.left <= lo < b.right and b.bottom < la <= b.top):
                        continue
                    fr, fc = ds.index(lo, la, op=float)
                    fr -= 0.5; fc -= 0.5
                    r0, c0 = int(math.floor(fr)), int(math.floor(fc))
                    tr, tc = fr - r0, fc - c0
                    v = band[r0:r0 + 2, c0:c0 + 2]
                    if v.shape != (2, 2) or np.ma.is_masked(v):
                        continue
                    v = v.filled(np.nan)
                    grid[j, i] = (v[0, 0] * (1 - tc) * (1 - tr) + v[0, 1] * tc * (1 - tr)
                                  + v[1, 0] * (1 - tc) * tr + v[1, 1] * tc * tr)
    if np.isnan(grid).any():
        raise SystemExit(f"[draft_line] {int(np.isnan(grid).sum())} grid samples have no DEM under them")
    hf.write_npy(data / "heightfield.npy", grid.tolist())
    meta = {"bbox_swne": [round(s_, 6), round(w_, 6), round(n_, 6), round(e_, 6)], "nx": nx, "ny": ny,
            "spacing_m": spacing, "margin_m": margin, "row0": "north",
            "_provenance": {"tool": "tracks/denver-grand-prix/source/draft/draft_line.py", "dem": "USGS 3DEP 1/3 arc-second "
                            "(about 10 m cells), bilinear", "tiles": used}}
    (data / "heightfield.meta.json").write_text(json.dumps(meta), encoding="utf-8")

    rep = {
        "line": {"points": n, "length_m": gj["features"][0]["properties"]["length_m"], "osm_lap_m": lap_len,
                 "start_at_offset_m": round(off, 3), "foot_distance_m_max": round(max(foot_d), 2),
                 "fillet": {"corners": frep.get("corners"), "nodes_rounded": frep.get("nodes_rounded"),
                            "length_in_m": frep.get("length_in_m"), "length_out_m": frep.get("length_out_m")}},
        "profile": {"source": "data/lap_profile.3dep.json", "md5": _md5(TRACK / "data" / "lap_profile.3dep.json"),
                    "median_m": hf.MEDIAN_WINDOW_M, "mean_m": float(dl.get("mean_window_m", 9.0)),
                    "straight_spans": spans_rep, "z_min": round(min(z), 3), "z_max": round(max(z), 3)},
        "widths": {**wsrc, "min": min(widths), "max": max(widths), **({"edges": shift_rep} if shift_rep else {})},
        "grid": {"nx": nx, "ny": ny, "spacing_m": spacing, "margin_m": margin, "z_min": round(float(np.nanmin(grid)), 2),
                 "z_max": round(float(np.nanmax(grid)), 2)},
        "md5": {f: _md5(data / f) for f in ("centerline.geojson", "centerline.local.json", "heightfield.npy",
                                            "heightfield.meta.json")},
    }
    (data / "draft_line.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def measured_edges(local, ring, s_osm, wst, cfg, frep, org):
    """The measured kerb-to-kerb edges (source/widths/widths.json, the edge of record per side, absolute lon/lat) on this
    line: each point's left / right offset along its own normal, the line moved to the middle of its two edges and the
    width set to their distance. Three constructions, each reported: (1) inside each declared corner's arc (tangent +
    pad) the centre offset and width run linearly between the zone's ends [construction: the corner's own curb return is
    not measured]; (2) where the lap's two directions share one paved street (Kalamath / Santa Fe south of Colfax), an edge
    that reaches past the middle of the two lap lines is cut there [invented divider position, checked against paint.json's
    yellow pieces]; (3) a light running mean on the offset and width (draft_line.widths.smooth_m)."""
    import numpy as np
    from scripts.geometry.projection import _meters_per_degree as _mpd
    dl = cfg["draft_line"]; wcfg = dl["widths"]
    lon0, lat0 = float(org["lon"]), float(org["lat"])
    ml, mt = _mpd(lat0)
    n = len(local)
    P = np.array([[p[0], p[2]] for p in local])
    # tangents (closed lap)
    T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    T[0] = P[1] - P[-2]; T[-1] = T[0]
    T /= np.maximum(np.hypot(*T.T), 1e-9)[:, None]
    NL = np.stack([-T[:, 1], T[:, 0]], axis=1)            # driver's left of travel (E, N)
    # the stations' line and edges in this frame
    W = wst
    SL = np.array([[(r["line_lonlat"][0] - lon0) * ml, (r["line_lonlat"][1] - lat0) * mt] for r in W])
    EL = np.array([[(r["left"]["lonlat"][0] - lon0) * ml, (r["left"]["lonlat"][1] - lat0) * mt] for r in W])
    ER = np.array([[(r["right"]["lonlat"][0] - lon0) * ml, (r["right"]["lonlat"][1] - lat0) * mt] for r in W])
    gl = [r["left"]["grade"] for r in W]; gr = [r["right"]["grade"] for r in W]
    # declared fills (draft_line.widths.edge_fills): a span whose edge readings are known bad is filled linearly, both
    # edges, between the stations at its ends (along each station's own normal)
    fill_rep = []
    for fl in wcfg.get("edge_fills") or []:
        a_, b_ = float(fl["from_s"]), float(fl["to_s"])
        ka = min(range(len(W)), key=lambda q: abs(float(W[q]["s"]) - a_))
        kb = min(range(len(W)), key=lambda q: abs(float(W[q]["s"]) - b_))
        oa = (float(W[ka]["left"]["offset"]), float(W[ka]["right"]["offset"]))
        ob = (float(W[kb]["left"]["offset"]), float(W[kb]["right"]["offset"]))
        for k in range(ka + 1, kb):
            f_ = (float(W[k]["s"]) - float(W[ka]["s"])) / (float(W[kb]["s"]) - float(W[ka]["s"]))
            t_ = SL[(k + 1) % len(W)] - SL[k - 1]; t_ = t_ / max(np.hypot(*t_), 1e-9)
            nl_ = np.array([-t_[1], t_[0]])
            EL[k] = SL[k] + nl_ * (oa[0] * (1 - f_) + ob[0] * f_)
            ER[k] = SL[k] - nl_ * (oa[1] * (1 - f_) + ob[1] * f_)
            gl[k] = gr[k] = "inferred"
        fill_rep.append({"from_s": float(W[ka]["s"]), "to_s": float(W[kb]["s"]), "stations": kb - ka - 1, "ends": [oa, ob]})
    # declared overrides (draft_line.widths.edge_overrides): an edge of record contradicted by measured paint is held at
    # least min_offset_m from the station's line (along the station's own left normal)
    ov_rep = []
    for ov in wcfg.get("edge_overrides") or []:
        a_, b_ = float(ov["from_s"]), float(ov["to_s"])
        side = ov["side"]; mn = float(ov["min_offset_m"]); hit = 0
        for k, r in enumerate(W):
            sk = float(r["s"])
            inside = (a_ <= sk <= b_) if a_ <= b_ else (sk >= a_ or sk <= b_)
            if not inside or float(r[side]["offset"]) >= mn:
                continue
            t_ = SL[(k + 1) % len(W)] - SL[k - 1]; t_ = t_ / max(np.hypot(*t_), 1e-9)
            nl_ = np.array([-t_[1], t_[0]])
            if side == "left":
                EL[k] = SL[k] + nl_ * mn
            else:
                ER[k] = SL[k] - nl_ * mn
            hit += 1
        ov_rep.append({"side": side, "from_s": a_, "to_s": b_, "min_offset_m": mn, "stations_moved": hit})
    ws_ = np.array([float(r["s"]) for r in W]); wlen = float(ws_[-1] + 2.5)
    # match each point to a station by position, with continuity (the lap's other side is never a candidate)
    left = np.zeros(n); right = np.zeros(n); kidx = np.zeros(n, dtype=int)
    prev = None
    for i in range(n):
        d = np.hypot(*(SL - P[i]).T)
        if prev is not None:
            dd = np.abs((ws_ - prev + wlen / 2) % wlen - wlen / 2)
            d = np.where(dd <= 40.0, d, np.inf)
        k = int(np.argmin(d)); kidx[i] = k; prev = ws_[k]
        # the two stations either side, weighted by the foot along the line
        k2 = (k + 1) % len(W) if np.dot(P[i] - SL[k], T[i]) >= 0 else (k - 1) % len(W)
        a, b = SL[k], SL[k2]
        ab = b - a; L2 = float(np.dot(ab, ab))
        t = 0.0 if L2 < 1e-9 else float(np.clip(np.dot(P[i] - a, ab) / L2, 0, 1))
        el = EL[k] * (1 - t) + EL[k2] * t; er = ER[k] * (1 - t) + ER[k2] * t
        left[i] = float(np.dot(el - P[i], NL[i])); right[i] = float(-np.dot(er - P[i], NL[i]))
    # (1) corner zones: linear between the zone's ends
    corners = [c for c in (cfg["route"].get("fillet") or {}).get("corners") or []]
    frc = {c["name"]: c for c in (frep.get("corners") or [])}
    pad = float(wcfg.get("corner_pad_m", 6.0))
    so = np.array(s_osm)
    zones = []
    for c in corners:
        s_apex = float(c["s_osm"]); tm = float(frc.get(c["name"], {}).get("tangent_m", c["radius_m"]))
        a_, b_ = s_apex - tm - pad, s_apex + tm + pad
        idx = np.where((so >= a_) & (so <= b_))[0]
        if len(idx) < 2:
            continue
        i0, i1 = int(idx.min()) - 1, int(idx.max()) + 1
        for i in range(i0 + 1, i1):
            f = (i - i0) / (i1 - i0)
            left[i] = left[i0] * (1 - f) + left[i1] * f
            right[i] = right[i0] * (1 - f) + right[i1] * f
        zones.append({"name": c["name"], "points": [i0, i1], "s_osm": [round(a_, 1), round(b_, 1)]})
    # (3) light running means (closed) on the centre offset and the width
    def run(v, m):
        h = max(1, int(round(m / 3.0 / 2)))
        vv = np.concatenate([v[-1 - h:-1], v[:-1], v[:h]])
        k_ = np.ones(2 * h + 1) / (2 * h + 1)
        out = np.convolve(vv, k_, mode="valid")
        return np.append(out, out[0])
    c_off = run((left - right) / 2.0, float(wcfg.get("centre_smooth_m", 15.0)))
    wid = run(left + right, float(wcfg.get("smooth_m", 9.0)))
    eL = c_off + wid / 2.0; eR = wid / 2.0 - c_off          # each edge's offset from this point (after the means)
    # (2) the lap's own other direction beside it (after the means, so the cut is exact): an edge never reaches past
    #     the middle between the two lap lines, less divider_clear_m [invented] so neither ribbon's edge strip or K-rail
    #     stands on the other's pavement
    clr = float(wcfg.get("divider_clear_m", 0.25))
    st = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))]); lap = st[-1]
    caps = []
    for i in range(n - 1):
        dd = np.abs((st - st[i] + lap / 2) % lap - lap / 2)
        far = np.where(dd > 150.0)[0]
        if not len(far):
            continue
        dist = np.hypot(*(P[far] - P[i]).T)
        j = far[int(np.argmin(dist))]; dmin = float(dist.min())
        if dmin > 60.0:
            continue
        side = float(np.dot(P[j] - P[i], NL[i]))
        lim = dmin / 2.0 - clr
        if side > 0 and eL[i] > lim:
            caps.append((i, "left", round(float(eL[i]), 2), round(lim, 2))); eL[i] = lim
        elif side < 0 and eR[i] > lim:
            caps.append((i, "right", round(float(eR[i]), 2), round(lim, 2))); eR[i] = lim
    eL[-1] = eL[0]; eR[-1] = eR[0]
    c_off = (eL - eR) / 2.0
    wid = eL + eR
    Q = P + NL * c_off[:, None]
    # (4) one street, one height: where the lap's two directions run within shared_height_m [invented] of each other
    #     (Kalamath and Santa Fe south of Colfax), each point's height is blended toward the mean of its own and the
    #     nearest far point's (weight 1 within shared_height_m - 10 m, 0 at shared_height_m), so the ground between the
    #     two ribbons is pinned to one deck height and never stands over the lower one (drive_test street, r9: grass on
    #     top at s 4,442 where Santa Fe sat 0.11 m under Kalamath). The real crossfall across the street is not measured
    Y = np.array([p[1] for p in local], dtype=float)
    Yn = Y.copy()
    sh = float(wcfg.get("shared_height_m", 30.0))
    blended = 0
    for i in range(n - 1):
        dd = np.abs((st - st[i] + lap / 2) % lap - lap / 2)
        far = np.where(dd > 150.0)[0]
        if not len(far):
            continue
        dist = np.hypot(*(P[far] - P[i]).T)
        j = far[int(np.argmin(dist))]; dmin = float(dist.min())
        wgt = float(np.clip((sh - dmin) / 10.0, 0.0, 1.0))
        if wgt > 0:
            Yn[i] = Y[i] + wgt * ((Y[i] + Y[j]) / 2.0 - Y[i])
            blended += 1
    Yn[-1] = Yn[0]
    local = [(p[0], float(Yn[i]), p[2]) for i, p in enumerate(local)]
    new_local = [[float(Q[i, 0]), local[i][1], float(Q[i, 1])] for i in range(n)]
    new_local[-1] = list(new_local[0])
    new_ring = [(lon0 + x / ml, lat0 + zz / mt) for x, _, zz in new_local]
    widths = [round(float(w), 2) for w in wid]
    widths[-1] = widths[0]
    grades = {"measured": 0, "detected": 0, "inferred": 0}
    for k in kidx[:-1]:
        grades[gl[k]] = grades.get(gl[k], 0) + 1; grades[gr[k]] = grades.get(gr[k], 0) + 1
    rep = {"shared_height_points": blended, "edge_fills": fill_rep, "edge_overrides": ov_rep, "centre_shift_m": {"min": round(float(c_off.min()), 2), "max": round(float(c_off.max()), 2)},
           "corner_zones": zones, "divider_caps": {"count": len(caps), "first": caps[:3], "last": caps[-3:],
                                                  "points": sorted({c[0] for c in caps})[:1] + sorted({c[0] for c in caps})[-1:]},
           "edge_grades_at_points": grades,
           "invented": ["corner zones: offset and width linear across each declared corner (curb returns not measured)",
                        "divider caps: the middle between the lap's two lines where they share one paved street"]}
    return [tuple(p) for p in new_local], new_ring, widths, rep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem-dir", default=__import__("os").environ.get(DEM_DIR_ENV), help="the 3DEP 1/3 arc-second tiles (or $DGP_DEM_DIR)")
    a = ap.parse_args()
    if not a.dem_dir:
        ap.error("--dem-dir (or $DGP_DEM_DIR): the folder of USGS_13_n40w105.tif / USGS_13_n40w106.tif")
    rep = build(Path(a.dem_dir))
    print(json.dumps({k: rep[k] for k in ("line", "profile", "widths", "grid")}, indent=1)[:6000])


if __name__ == "__main__":
    main()

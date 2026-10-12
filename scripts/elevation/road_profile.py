"""The road's own elevation profile, smoothed by STATION, with declared decks held straight (Lariat V3, ledger 0048).

``scripts/elevation/heightfield.py`` samples 3DEP at every centreline vertex (``z_raw_m``) and smooths it with
windows counted in VERTICES, sized for a 3 m line (``CENTERLINE_SPACING_M``): a 33 m median, a 9 m mean and a
grade cap of ``max_grade_pct`` x 3 m per vertex. The Lariat's paint centreline is 1 m on the climb and 3 m
elsewhere, so on the climb those windows shrink to 11 m and 3 m and the cap loosens to 3x its grade. This stage
re-smooths the SAME raw samples with the same contract, measured in metres along the road:

  1. declared decks (``bridges.declared`` in track.config.json) are held STRAIGHT between their abutments in
     the raw profile first, so a bare-earth trench under a deck never enters a filter (L3 "bridges dip");
  2. a median de-spike over ``MEDIAN_WINDOW_M`` (heightfield's 33 m, or ``road_profile.despike_window_m``);
  3. one light mean over 9 m (heightfield's own);
  4. the grade limiter that only CUTS (heightfield's snap_to_ground), with the cap applied per REAL segment
     length (L3: "grade-cap by real segment distance").

On a uniformly 3 m line this is heightfield.snap_to_ground exactly (tests/elevation/test_road_profile.py), so it
changes nothing but the windows' units. Closed laps fold the duplicate closing vertex out and wrap station
distances (L13). Where the raw samples come from: heightfield samples the centreline vertices themselves, i.e.
the painted centre of the road (``tools/paint_centreline.py``), never a point beside it (L3b: a lateral sample
beside a 6 m road reads the cut or the fill).

Declared decks (``bridges.declared[]``): ``footprint_ways`` = OSM ways (from ``data/osm.cache.json``) the deck
passes OVER (the 19th St lid over the US-6 tunnel, ways 533503591 + 533679737). The deck is the stretch of the lap
inside the union of their footprints (each way's centreline buffered by half its pavement width, from
``scripts.gps.widths_from_osm.pavement_width`` with the track's width profile), plus ``abutment_m`` each side.
Its stations are written in both frames: the geojson's (from its v0) and the local one
(``scripts.geometry.projection``'s ``route.start_at`` rotation, emulated here exactly as projection rotates).

Writes (data/):
  centerline.elevation.json   z_smooth_m replaced (heightfield's own kept as z_smooth_heightfield_m); z_raw_m is
                              untouched (the 3DEP samples); z_held_m = the raw profile with the decks held;
                              ``road_profile`` = the method, windows and stats
  bridge.spans.json           the declared decks (both frames, footprint crossings, dip removed), the lap's own
                              OSM bridge ways (none expected), the dropped suspects from the config
With ``--write`` it also records the decks as ``capture.bridges`` [{center_m, len_m}] (local stations) in
track.config.json, the engine's declared-span key (scripts.capture.evidence.bridge_spans: drive_test's
replication and obstruction exemptions, kn5_ground_check's railing feet).

    python -m scripts.elevation.road_profile <project-dir> [--write]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from scripts.elevation.heightfield import MEDIAN_WINDOW_M
from scripts.geometry.projection import _meters_per_degree, centroid

MEAN_WINDOW_M = 9.0          # heightfield.snap_to_ground's one light mean (round(9 / spacing) vertices)
DECK_DENSIFY_M = 0.25        # lap sub-steps when intersecting a deck footprint (measurement resolution only)
GRADE_WINDOW_M = 20.0        # the stats' "steepest 20 m" (the dossier's / A7's figure), not a threshold


# --- stations --------------------------------------------------------------------------------------------------

def plan_xy(lonlat, origin=None):
    """(east, north) metres about ``origin`` (default: the line's centroid), projection's series."""
    lon0, lat0 = origin if origin is not None else centroid(lonlat)
    mlon, mlat = _meters_per_degree(lat0)
    return [((a - lon0) * mlon, (b - lat0) * mlat) for a, b in lonlat]


def stations(xy):
    st = [0.0]
    for i in range(1, len(xy)):
        st.append(st[-1] + math.hypot(xy[i][0] - xy[i - 1][0], xy[i][1] - xy[i - 1][1]))
    return st


def is_closed(points, tol=1e-9) -> bool:
    """L13 rule 1: derive, never assume."""
    return len(points) > 2 and all(abs(a - b) <= tol for a, b in zip(points[0], points[-1]))


# --- station-window filters (L13: the closing duplicate folded out, distances wrapped) ------------------------

def _window_iter(st, lap, half_m, closed):
    """For each unique vertex i: the indices j with |st_j - st_i| <= half_m, distances wrapped by ``lap`` on a
    closed lap (``st`` = the unique vertices' stations, the closing duplicate already folded out)."""
    n = len(st)
    eps = 1e-9
    for i in range(n):
        idx = [i]
        j = i
        while True:                                    # forward
            j2 = j + 1
            if j2 >= n:
                if not closed:
                    break
                j2 -= n
            d = st[j2] - st[i]
            if d < 0:
                d += lap
            if d > half_m + eps or j2 == i or len(idx) >= n:
                break
            idx.append(j2)
            j = j2
        j = i
        while True:                                    # backward
            j2 = j - 1
            if j2 < 0:
                if not closed:
                    break
                j2 += n
            d = st[i] - st[j2]
            if d < 0:
                d += lap
            if d > half_m + eps or j2 == i or j2 in idx:
                break
            idx.append(j2)
            j = j2
        yield idx


def length_weights(st, lap, closed):
    """Each vertex's share of the road: half of each adjacent segment (wrapped on a closed lap). Where the spacing
    changes (the Lariat's 1 m climb meets its 3 m roads) a window holds more vertices on the dense side; counting
    vertices would pull a median or a mean toward that side (measured: a 0.70 m lift and a false -12.3 % at the
    1 m / 3 m change at local st 11,588). Weighting by length removes the bias; on uniform spacing every weight is
    equal and both filters are the plain ones (heightfield's)."""
    n = len(st)
    if n == 1:
        return [1.0]
    seg = [st[i + 1] - st[i] for i in range(n - 1)]
    close = (lap - st[-1] + st[0]) if closed else 0.0
    w = []
    for i in range(n):
        left = seg[i - 1] if i > 0 else close
        right = seg[i] if i < n - 1 else close
        if not closed and i == 0:
            left = right
        if not closed and i == n - 1:
            right = left
        w.append((left + right) / 2.0)
    return w


def station_median(z, st, lap, window_m, closed, weights=None):
    """Length-weighted median over +-window/2 of road: the first value (ascending) whose cumulative weight passes
    half the window's. On uniform spacing that is ``sorted(window)[len // 2]``, heightfield's pick (the middle of
    an odd window, the upper middle of an even one at a clamped open end)."""
    wts = weights if weights is not None else length_weights(st, lap, closed)
    out = []
    for idx in _window_iter(st, lap, window_m / 2.0, closed):
        pairs = sorted((z[k], wts[k]) for k in idx)
        half = sum(w for _, w in pairs) / 2.0
        acc = 0.0
        val = pairs[-1][0]
        for v, w in pairs:
            acc += w
            if acc > half * (1.0 + 1e-12):
                val = v
                break
        out.append(val)
    return out


def station_mean(z, st, lap, window_m, closed, weights=None):
    """Length-weighted mean over +-window/2 of road."""
    wts = weights if weights is not None else length_weights(st, lap, closed)
    out = []
    for idx in _window_iter(st, lap, window_m / 2.0, closed):
        sw = sum(wts[k] for k in idx)
        out.append(sum(z[k] * wts[k] for k in idx) / sw)
    return out


def snap_to_ground_stations(z, st_full, *, grade_cap_pct, median_m=MEDIAN_WINDOW_M, mean_m=MEAN_WINDOW_M,
                            closed=True):
    """heightfield.snap_to_ground with its windows in METRES along the road and the grade cap per real segment.

    ``z`` and ``st_full`` are per vertex of the line as stored (a closed lap repeats its first vertex last; it is
    folded out here, filtered, and restored identical to the first — L13). Result is at-or-below the despiked
    ground everywhere (the limiter only cuts)."""
    n = len(z)
    if n == 0:
        return []
    dup = closed and n > 2 and abs(z[0] - z[-1]) < 1e-9
    zz = list(z[:-1]) if dup else list(z)
    st = list(st_full[:-1]) if dup else list(st_full)
    m = len(zz)
    lap = st_full[-1]                      # with the duplicate folded out, the closing segment is last -> v0
    seg = [st[i + 1] - st[i] for i in range(m - 1)]
    seg_close = (lap - st[-1]) if closed else 0.0
    out = station_median(zz, st, lap, median_m, closed)
    out = station_mean(out, st, lap, mean_m, closed)
    cap = grade_cap_pct / 100.0
    for _ in range(2):                     # closed loop: two wraps converge the clamp (heightfield's)
        for i in range(1, m):
            out[i] = min(out[i], out[i - 1] + cap * seg[i - 1])
        for i in range(m - 2, -1, -1):
            out[i] = min(out[i], out[i + 1] + cap * seg[i])
        if closed:
            out[0] = min(out[0], out[-1] + cap * seg_close)
    if dup:
        out.append(out[0])
    return out


# --- declared decks --------------------------------------------------------------------------------------------

def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _seg_cross(p0, p1, q0, q1):
    """(t along p, u along q) of the crossing of segments p0p1 and q0q1, or None."""
    rx, ry = p1[0] - p0[0], p1[1] - p0[1]
    sx, sy = q1[0] - q0[0], q1[1] - q0[1]
    den = rx * sy - ry * sx
    if abs(den) < 1e-12:
        return None
    qpx, qpy = q0[0] - p0[0], q0[1] - p0[1]
    t = (qpx * sy - qpy * sx) / den
    u = (qpx * ry - qpy * rx) / den
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return t, u
    return None


def deck_span(xy, st, footprints, *, abutment_m, closed):
    """The lap's stretch over a deck's footprint: ``footprints`` = [(polyline_xy, half_width_m), ...].

    Every lap segment near a footprint is walked at ``DECK_DENSIFY_M``; the stations inside any footprint give
    [first, last], then ``abutment_m`` each side. Returns a dict (a_m, b_m, inside_m, crossings) or None when the
    lap never enters the footprint. Refuses (ValueError) a deck that would cross the seam of a closed lap: the
    span convention [a, b] with a < b cannot hold it, and no declared deck needs it (L13)."""
    inside = []
    crossings = []
    n = len(xy)
    for poly, half in footprints:
        for k in range(len(poly) - 1):
            q0, q1 = poly[k], poly[k + 1]
            reach = half + 10.0
            for i in range(n - 1):
                p0, p1 = xy[i], xy[i + 1]
                if min(_seg_dist(p0, q0, q1), _seg_dist(p1, q0, q1)) > reach + math.dist(p0, p1):
                    continue
                L = st[i + 1] - st[i]
                steps = max(1, int(math.ceil(L / DECK_DENSIFY_M)))
                for s in range(steps + 1):
                    t = s / steps
                    p = (p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1]))
                    if _seg_dist(p, q0, q1) <= half:
                        inside.append(st[i] + t * L)
                c = _seg_cross(p0, p1, q0, q1)
                if c:
                    t, _u = c
                    hl = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                    hq = math.atan2(q1[1] - q0[1], q1[0] - q0[0])
                    ang = abs((math.degrees(hl - hq) + 90.0) % 180.0 - 90.0)
                    crossings.append({"lap_st_m": round(st[i] + t * L, 2), "angle_deg": round(ang, 1)})
    if not inside:
        return None
    a, b = min(inside), max(inside)
    lap = st[-1]
    a2, b2 = a - abutment_m, b + abutment_m
    if closed and (a2 < 0.0 or b2 > lap):
        raise ValueError(f"declared deck [{a2:.1f}, {b2:.1f}] crosses the seam of a closed lap (lap {lap:.1f} m)")
    return {"a_m": max(0.0, a2), "b_m": min(lap, b2), "footprint_a_m": a, "footprint_b_m": b,
            "inside_m": round(b - a, 2), "crossings": sorted(crossings, key=lambda c: c["lap_st_m"])}


def interp(st, z, s):
    import bisect
    k = bisect.bisect_left(st, s)
    if k <= 0:
        return z[0]
    if k >= len(st):
        return z[-1]
    t = (s - st[k - 1]) / max(1e-12, st[k] - st[k - 1])
    return z[k - 1] + t * (z[k] - z[k - 1])


def hold_straight(z, st, a, b):
    """The raw profile with [a, b] replaced by the straight line between its heights at a and b (a deck carries its
    road straight from abutment to abutment: no dip into what it spans). Returns (z_new, stats)."""
    za, zb = interp(st, z, a), interp(st, z, b)
    out = list(z)
    dips = []
    for i, s in enumerate(st):
        if a <= s <= b:
            line = za + (zb - za) * (s - a) / max(1e-9, b - a)
            dips.append(line - z[i])
            out[i] = line
    return out, {"z_a_m": round(za, 2), "z_b_m": round(zb, 2), "grade_pct": round(100 * (zb - za) / max(1e-9, b - a), 2),
                 "max_dip_removed_m": round(max(dips), 2) if dips else 0.0,
                 "max_hump_removed_m": round(-min(dips), 2) if dips else 0.0, "vertices": len(dips)}


# --- the local frame (projection.build's route.start_at rotation, emulated exactly) -------------------------

def projection_rotation(lonlat, cfg) -> int:
    """The number of unique vertices projection.build rotates the ring by (0 when it does not rotate)."""
    route = cfg.get("route") or {}
    sa = route.get("start_at")
    closed = len(lonlat) > 2 and tuple(lonlat[0]) == tuple(lonlat[-1])
    if route.get("reverse"):
        raise ValueError("route.reverse: not supported by this stage (the Lariat runs its line as stored)")
    if not sa or not cfg.get("loop", True):
        return 0
    ring = lonlat[:-1] if closed else lonlat
    mlon, mlat = _meters_per_degree(float(sa[0]))
    return min(range(len(ring)), key=lambda i: ((ring[i][0] - float(sa[1])) * mlon) ** 2
               + ((ring[i][1] - float(sa[0])) * mlat) ** 2)


def to_local_station(s_geo, st_geo, k, closed):
    """A geojson-frame station -> the local frame (v0 = geojson vertex k)."""
    if k == 0:
        return s_geo
    lap = st_geo[-1]
    s = s_geo - st_geo[k]
    if closed:
        s %= lap
    return s


# --- stats -----------------------------------------------------------------------------------------------------

def grade_stats(st, z, window_m=GRADE_WINDOW_M):
    """Steepest climb / descent over any ``window_m`` of road (interpolated), and the per-segment extremes."""
    best_up, best_dn, at_up, at_dn = -1e9, 1e9, 0.0, 0.0
    s = 0.0
    lap = st[-1]
    while s + window_m <= lap:
        g = 100.0 * (interp(st, z, s + window_m) - interp(st, z, s)) / window_m
        if g > best_up:
            best_up, at_up = g, s
        if g < best_dn:
            best_dn, at_dn = g, s
        s += 1.0
    return {"steepest_up_pct": round(best_up, 2), "at_up_m": round(at_up, 1),
            "steepest_down_pct": round(best_dn, 2), "at_down_m": round(at_dn, 1)}


def _ways_by_id(proj: Path):
    snap = json.loads((proj / "data" / "osm.cache.json").read_text(encoding="utf-8"))
    els = (snap.get("payload") or snap).get("elements", [])
    return {e["id"]: e for e in els if e.get("type") == "way" and e.get("geometry")}


def lap_bridge_ways(ways, xy, origin, near_m=6.0, frac=0.7):
    """OSM bridge=yes ways (not motorway) the lap itself rides: >= ``frac`` of the way's nodes within ``near_m`` of
    the lap. Reported, never auto-declared (a deck is declared from evidence, V3-PLAN P2 step 5)."""
    out = []
    for w in ways.values():
        t = w.get("tags") or {}
        if t.get("bridge") in (None, "no") or (t.get("highway") or "").startswith("motorway"):
            continue
        g = plan_xy([(p["lon"], p["lat"]) for p in w["geometry"]], origin)
        near = 0
        for p in g:
            if min(math.dist(p, q) for q in xy[::3]) <= near_m + 3.0:
                near += 1
        if near >= frac * len(g):
            out.append({"way": w["id"], "name": t.get("name"), "ref": t.get("ref"), "highway": t.get("highway")})
    return out


# --- the stage -------------------------------------------------------------------------------------------------

def build(project_dir, *, write=False, log=print) -> dict:
    proj = Path(project_dir)
    data = proj / "data"
    cfg_p = proj / "track.config.json"
    cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    gj = json.loads((data / "centerline.geojson").read_text(encoding="utf-8"))
    full = next(f for f in gj["features"] if (f.get("properties") or {}).get("kind") == "full")
    lonlat = [(float(a), float(b)) for a, b in full["geometry"]["coordinates"]]
    ej_p = data / "centerline.elevation.json"
    ej = json.loads(ej_p.read_text(encoding="utf-8"))
    z_raw = [float(v) for v in ej["z_raw_m"]]
    if len(z_raw) != len(lonlat):
        raise SystemExit(f"[road_profile] centerline.elevation.json has {len(z_raw)} samples for {len(lonlat)} vertices"
                         " (re-run scripts.elevation.heightfield on this line)")
    closed = is_closed(lonlat) and bool(full["properties"].get("closed", cfg.get("loop", True)))
    origin = centroid(lonlat)
    xy = plan_xy(lonlat, origin)
    st = stations(xy)
    rp = cfg.get("road_profile") or {}
    cap = float(rp.get("max_grade_pct", 9.0))
    med_m = float(rp.get("despike_window_m", MEDIAN_WINDOW_M))
    k = projection_rotation(lonlat, cfg)

    # 1. declared decks, held straight in the RAW profile before any filter sees the trench
    bcfg = cfg.get("bridges") or {}
    profile = (cfg.get("route") or {}).get("width_profile", "urban")
    from scripts.gps.widths_from_osm import pavement_width
    ways = None
    decks = []
    z_held = list(z_raw)
    for d in bcfg.get("declared") or []:
        if ways is None:
            ways = _ways_by_id(proj)
        fps = []
        for wid in d["footprint_ways"]:
            w = ways.get(int(wid))
            if w is None:
                raise SystemExit(f"[road_profile] deck {d['id']}: footprint way {wid} is not in data/osm.cache.json")
            t = w.get("tags") or {}
            way = {"highway": t.get("highway"), "lanes": t.get("lanes"), "width": t.get("width")}
            fps.append((plan_xy([(p["lon"], p["lat"]) for p in w["geometry"]], origin),
                        pavement_width(way, profile) / 2.0))
        span = deck_span(xy, st, fps, abutment_m=float(d.get("abutment_m", 8.0)), closed=closed)
        if span is None:
            raise SystemExit(f"[road_profile] deck {d['id']}: the lap never crosses its footprint ways {d['footprint_ways']}")
        z_held, hs = hold_straight(z_held, st, span["a_m"], span["b_m"])
        la, lb = (to_local_station(span["a_m"], st, k, closed), to_local_station(span["b_m"], st, k, closed))
        if lb < la:
            raise SystemExit(f"[road_profile] deck {d['id']} straddles the local seam ({la:.1f} -> {lb:.1f})")
        decks.append({"id": d["id"], "kind": d.get("kind", "deck"), "footprint_ways": d["footprint_ways"],
                      "footprint_half_widths_m": [round(h, 2) for _, h in fps],
                      "abutment_m": float(d.get("abutment_m", 8.0)),
                      "geojson_m": [round(span["a_m"], 1), round(span["b_m"], 1)],
                      "local_m": [round(la, 1), round(lb, 1)],
                      "center_m": round((la + lb) / 2.0, 1), "len_m": round(lb - la, 1),
                      "over_footprint_m": span["inside_m"], "crossings_geojson": span["crossings"], "hold": hs})
        log(f"[road_profile] deck {d['id']}: local st {la:.1f}-{lb:.1f} ({lb - la:.1f} m, {span['inside_m']:.1f} m over"
            f" the footprint), held straight at {hs['grade_pct']:+.2f} % (the raw profile moved by at most "
            f"{max(hs['max_dip_removed_m'], hs['max_hump_removed_m']):.2f} m: dip {hs['max_dip_removed_m']:.2f}, hump "
            f"{hs['max_hump_removed_m']:.2f})")

    # 2-4. the station-window smoothing
    z_s = snap_to_ground_stations(z_held, st, grade_cap_pct=cap, median_m=med_m, mean_m=MEAN_WINDOW_M,
                                  closed=closed)
    dev = sorted(abs(a - b) for a, b in zip(z_s, z_raw))
    in_deck = [any(dd["geojson_m"][0] <= s <= dd["geojson_m"][1] for dd in decks) for s in st]
    dev_off = sorted(abs(a - b) for a, b, f in zip(z_s, z_raw, in_deck) if not f)
    seg = [st[i] - st[i - 1] for i in range(1, len(st))]
    seg_grades = [abs(z_s[i] - z_s[i - 1]) / max(1e-6, seg[i - 1]) * 100 for i in range(1, len(z_s))]
    climb = sum(max(0.0, z_s[i] - z_s[i - 1]) for i in range(1, len(z_s)))
    g_raw, g_s = grade_stats(st, z_raw), grade_stats(st, z_s)
    capped = sum(1 for i in range(1, len(z_s)) if abs(z_s[i] - z_s[i - 1]) >= cap / 100.0 * seg[i - 1] - 1e-9)
    hf = ej.get("z_smooth_heightfield_m") or ej.get("z_smooth_m")
    stats = {"min_m": round(min(z_s), 1), "max_m": round(max(z_s), 1), "range_m": round(max(z_s) - min(z_s), 1),
             "total_climb_m": round(climb, 1), "max_segment_grade_pct": round(max(seg_grades), 1),
             "mean_grade_pct": round(sum(seg_grades) / len(seg_grades), 2), "lap_m": round(st[-1], 1),
             "steepest_20m_smoothed": g_s, "steepest_20m_raw": g_raw,
             "grade_cap_pct": cap, "segments_at_cap": capped,
             "smoothed_vs_raw_m": {"median": round(dev[len(dev) // 2], 3), "p95": round(dev[19 * len(dev) // 20], 3),
                                   "max": round(dev[-1], 3)},
             "smoothed_vs_raw_off_decks_m": {"median": round(dev_off[len(dev_off) // 2], 3),
                                             "p95": round(dev_off[19 * len(dev_off) // 20], 3),
                                             "max": round(dev_off[-1], 3)},
             "heightfield_vs_this_m": ({"p95": round(sorted(abs(a - b) for a, b in zip(hf, z_s))[19 * len(z_s) // 20], 3),
                                        "max": round(max(abs(a - b) for a, b in zip(hf, z_s)), 3)} if hf else None)}
    ej.setdefault("z_smooth_heightfield_m", ej.get("z_smooth_m"))
    ej["z_smooth_m"] = [round(v, 2) for v in z_s]
    ej["z_held_m"] = [round(v, 2) for v in z_held]
    # the raw 3DEP samples in the LOCAL index space too (projection rotates the ring by k): z_raw_m is per geojson
    # vertex, centerline.local.json per local vertex; a gate pairing the two by index would compare points k apart
    if closed and k:
        m_u = len(z_raw) - 1
        zl = [z_raw[(i + k) % m_u] for i in range(m_u)]
        ej["z_raw_local_m"] = [round(v, 2) for v in zl + [zl[0]]]
    else:
        ej["z_raw_local_m"] = [round(v, 2) for v in z_raw]
    ej["stats"] = {**(ej.get("stats") or {}), **{k2: stats[k2] for k2 in
                   ("min_m", "max_m", "range_m", "total_climb_m", "mean_grade_pct", "lap_m")},
                   "max_grade_pct": stats["max_segment_grade_pct"]}
    ej["road_profile"] = {
        "tool": "scripts/elevation/road_profile.py",
        "_doc": "z_smooth_m re-derived from z_raw_m with windows in METRES along the road (heightfield's are in "
                "vertices, sized for 3 m spacing); declared decks held straight first (z_held_m); grade cap per real "
                "segment. heightfield's own profile is z_smooth_heightfield_m.",
        "median_window_m": med_m, "mean_window_m": MEAN_WINDOW_M, "grade_cap_pct": cap, "closed": closed,
        "local_rotation_vertices": k, "decks": [dd["id"] for dd in decks], "stats": stats}
    ej_p.write_text(json.dumps(ej), encoding="utf-8")

    # bridge spans record: declared decks, the lap's own OSM bridge ways (reported), the dropped suspects
    if ways is None and (data / "osm.cache.json").exists():
        ways = _ways_by_id(proj)
    lap_bridges = lap_bridge_ways(ways, xy, origin) if ways else []
    rec = {"frame": {"geojson": "stations from data/centerline.geojson v0", "local": "centerline.local.json stations "
                     "(route.start_at rotation by %d vertices, as scripts.geometry.projection rotates)" % k,
                     "lap_m": round(st[-1], 2), "closed": closed},
           "declared": decks, "lap_osm_bridge_ways": lap_bridges,
           "dropped": bcfg.get("dropped") or [],
           "l13_seam": "every declared span lies inside (0, lap): none ends on the closing vertex"}
    (data / "bridge.spans.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    if lap_bridges:
        log(f"[road_profile] NOTE the lap rides {len(lap_bridges)} OSM bridge way(s) not declared: "
            f"{[b['way'] for b in lap_bridges]} (reported in data/bridge.spans.json, never auto-declared)")
    if write and bcfg.get("declared") is not None:
        cap_blk = cfg.setdefault("capture", {})
        cap_blk["bridges"] = [{"id": dd["id"], "center_m": dd["center_m"], "len_m": dd["len_m"]} for dd in decks]
        cap_blk["_bridges_doc"] = ("Written by scripts/elevation/road_profile.py --write from bridges.declared "
                                   "(local stations; data/bridge.spans.json has the footprint, the frames and the hold). "
                                   "The engine's declared-span key: drive_test's replication / obstruction exemptions "
                                   "and kn5_ground_check's railing feet read it. Do not edit by hand.")
        cfg_p.write_text(json.dumps(cfg, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
        log(f"[road_profile] track.config.json capture.bridges <- {cap_blk['bridges']}")
    log(f"[road_profile] {len(z_s)} vertices, lap {st[-1]:.1f} m, {stats['min_m']}-{stats['max_m']} m, climb "
        f"{stats['total_climb_m']} m; steepest 20 m {g_s['steepest_up_pct']:+.1f} % / {g_s['steepest_down_pct']:+.1f} % "
        f"(raw {g_raw['steepest_up_pct']:+.1f} / {g_raw['steepest_down_pct']:+.1f}); |smoothed - raw| off decks p95 "
        f"{stats['smoothed_vs_raw_off_decks_m']['p95']} m, max {stats['smoothed_vs_raw_off_decks_m']['max']} m; "
        f"{capped} segment(s) at the {cap:g} % cap")
    return {"stats": stats, "decks": decks, "lap_bridge_ways": lap_bridges}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.elevation.road_profile")
    ap.add_argument("project_dir")
    ap.add_argument("--write", action="store_true", help="record the declared decks as capture.bridges in the config")
    a = ap.parse_args(argv)
    build(a.project_dir, write=a.write)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""``paint_traces.json``: the traced paint of every window, in the OSM / engine frames, with a confidence per
point. It is what ``tools/paint_centreline.py`` follows and ``tools/verify_centreline_paint.py`` judges.

Per window (a hairpin's corner window, a width station, a junction arm):
- ``yellow``: the double-yellow centre line, one point per profile that found it, from the perpendicular
  trace (``source`` "profile") and, at a measured hairpin, from the polar rays over the core ("core_ray");
- ``edge_left`` / ``edge_right``: the white edge lines, left / right of travel in the Full (forward,
  increasing-station) direction;
- ``reference``: the paint centre as one continuous polyline: the trace reference moved onto the medium+
  yellow offsets (median +-3 m, gaps interpolated, +-2 m moving average), every 0.5 m, each point flagged
  ``supported`` when a medium+ yellow point lies within ``SUPPORT_M`` of it; unsupported points bridge a gap
  (shadow, a parked car) or are still the OSM-derived reference;
- ``core`` (hairpins): the yellow-line circle and the painted edge-line pair (one centre, two radii), with
  the core's two ends as points, so a consumer can follow the arc in its own frame.

Every point is given as ``xz_m``: the engine plan frame, local ENU metres (x east, z north) about
``frame.origin_lonlat`` = scripts.geometry.projection.centroid of the lap centreline, with
projection._meters_per_degree's series, so lon = lon0 + x / m_lon, lat = lat0 + z / m_lat exactly (the
imagery point was first moved into the OSM / WGS84 frame by the measured OSM-minus-imagery offset). With it:
``lap_st_m`` (metres from v0 of that lap centreline in the same plan frame: geojson stations, not the
config's local frame) and ``heading_deg`` (direction of Full travel, degrees counter-clockwise from east).

Confidence per point (thresholds all **[invented]**, 2026-10-11, none a gate by itself; the paint gate
judges only medium+ points):
- profile points: a **run** is consecutive 0.5 m profiles that found the line; **consistent** = within
  ``CONSISTENT_M`` 0.3 m of the median of its +-``CONSISTENT_K`` 8 neighbours (+-4 m, >= 3 of them
  present; a short second line 1.4 m off the paint, as at W00150, is not); **strong** = yellow
  prominence >= ``PROM_REL`` 0.5 x the median prominence of the window's own detections (a parked car's edge
  at C4 reads 12-16 where the window's paint reads 36-48); **parallel** = the line's offset from the trace
  reference changes by at most ``DRIFT_MAX`` 0.15 m per metre over +-``DRIFT_K`` 8 profiles (4 m) of its run
  (paint runs along the road; a run that crosses it diagonally, as at W06900 in shadow, is soil or a car).
  high = run >= ``RUN_HIGH`` 8 profiles, consistent, strong, parallel, prominence >= ``PROM_HIGH`` 15 and
  both edge lines found on that profile with lanes ``LANE_M`` 2.4-5.0 m; medium = run >= ``RUN_MEDIUM`` 4,
  consistent, strong and parallel; low = anything else. At a hairpin whose yellow circle is good, a profile point inside the
  core's polar sector more than max(0.3 m, 2.5 rms) off that circle is low (the circle is the better
  witness there). Edge lines: run, consistency and, for high, the yellow on that profile and the lane in
  range. A width station the measurement itself judged unusable (fewer than 10 profiles of either width,
  tools/aerial/widths.py) contributes low points only: W06900 (72 % shadow, 5 edge-line profiles) traced a
  run of "yellow" that crosses the road.
- core-ray points: inliers of the corner's robust circle for that line (within max(0.3 m, 2.5 rms));
  high when that circle is "good" (>= 45 % of the core rays, rms <= 0.35 m), else medium; outliers low.
- ``SUPPORT_M`` 0.35 m: a reference point is supported by a medium+ yellow point this close [invented].
"""
from __future__ import annotations

import hashlib
import math
import statistics as stt
from pathlib import Path

from . import geo, profile as pf

CONSISTENT_M = 0.3
CONSISTENT_K = 8
USABLE_MIN_PROFILES = 10
RUN_HIGH = 8
RUN_MEDIUM = 4
PROM_HIGH = 15.0
PROM_REL = 0.5
DRIFT_MAX = 0.15
DRIFT_K = 8
STEP_M = 0.5
LANE_M = (2.4, 5.0)
SUPPORT_M = 0.35
CORE_FLOOR_M = 0.3
CORE_K = 2.5


class Frames:
    """imagery (UTM 13N NAD83) -> OSM lon/lat -> engine plan xz, and lap stations on the OSM line."""

    def __init__(self, ctx):
        self.V = ctx.V
        ll = ctx.L.ll
        n = len(ll)
        self.lon0 = sum(p[0] for p in ll) / n
        self.lat0 = sum(p[1] for p in ll) / n
        self.mlon, self.mlat = geo.meters_per_degree(self.lat0)
        self.plan = [self.ll_to_xz(lo, la) for lo, la in ll]
        self.st = [0.0]
        for i in range(1, n):
            self.st.append(self.st[-1] + geo.dist(self.plan[i], self.plan[i - 1]))

    def img_to_ll(self, E, N):
        return geo.from_utm(E + self.V[0], N + self.V[1])

    def ll_to_xz(self, lon, lat):
        return ((lon - self.lon0) * self.mlon, (lat - self.lat0) * self.mlat)

    def img_to_xz(self, E, N):
        return self.ll_to_xz(*self.img_to_ll(E, N))

    def heading(self, p_img, t_img):
        a = self.img_to_xz(*p_img)
        b = self.img_to_xz(p_img[0] + t_img[0], p_img[1] + t_img[1])
        return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))

    def station(self, xz, s_lo, s_hi):
        """Lap station of the nearest point of the OSM line between stations s_lo and s_hi."""
        i0 = max(0, _bisect(self.st, s_lo) - 1)
        i1 = min(len(self.plan) - 1, _bisect(self.st, s_hi) + 1)
        best = None
        for i in range(i0, i1):
            a, b = self.plan[i], self.plan[i + 1]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            if L2 == 0:
                continue
            t = max(0.0, min(1.0, ((xz[0] - a[0]) * dx + (xz[1] - a[1]) * dy) / L2))
            d = math.hypot(a[0] + t * dx - xz[0], a[1] + t * dy - xz[1])
            if best is None or d < best[0]:
                best = (d, self.st[i] + t * (self.st[i + 1] - self.st[i]))
        return best[1] if best else None


def _bisect(a, x):
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _runs(vals):
    n = len(vals)
    run = [0] * n
    i = 0
    while i < n:
        if vals[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < n and vals[j + 1] is not None:
            j += 1
        for k in range(i, j + 1):
            run[k] = j - i + 1
        i = j + 1
    return run


def _parallel(vals, i, run_start, run_end):
    """Offset drift (m per m) over +-DRIFT_K profiles of i, clipped to its run, within DRIFT_MAX."""
    j0, j1 = max(run_start, i - DRIFT_K), min(run_end, i + DRIFT_K)
    if j1 - j0 < 4:
        return True
    return abs(vals[j1] - vals[j0]) / ((j1 - j0) * STEP_M) <= DRIFT_MAX


def _run_bounds(vals):
    n = len(vals)
    lo, hi = [None] * n, [None] * n
    i = 0
    while i < n:
        if vals[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < n and vals[j + 1] is not None:
            j += 1
        for k in range(i, j + 1):
            lo[k], hi[k] = i, j
        i = j + 1
    return lo, hi


def _consistent(vals, i, half=CONSISTENT_K):
    nb = [vals[j] for j in range(max(0, i - half), min(len(vals), i + half + 1)) if j != i and vals[j] is not None]
    return len(nb) >= 3 and abs(vals[i] - stt.median(nb)) <= CONSISTENT_M


def profile_confidence(yel, prom, lo, hi, off_core=None):
    """Per-profile confidence of the yellow, right (lo) and left (hi) edge lines (lists aligned on profiles).
    ``off_core[i]`` true = that profile's yellow sits inside a good core circle's sector but off the circle."""
    n = len(yel)
    ry, rl, rh = _runs(yel), _runs(lo), _runs(hi)
    cy, cl, ch = [None] * n, [None] * n, [None] * n
    proms = [prom[i] for i in range(n) if yel[i] is not None and prom[i] is not None]
    floor = PROM_REL * stt.median(proms) if proms else 0.0
    bounds = {"y": _run_bounds(yel), "lo": _run_bounds(lo), "hi": _run_bounds(hi)}
    for i in range(n):
        lanes_ok = (yel[i] is not None and lo[i] is not None and hi[i] is not None
                    and LANE_M[0] <= yel[i] - lo[i] <= LANE_M[1] and LANE_M[0] <= hi[i] - yel[i] <= LANE_M[1])
        if yel[i] is not None:
            cons = _consistent(yel, i)
            strong = (prom[i] or 0) >= floor
            par = _parallel(yel, i, bounds["y"][0][i], bounds["y"][1][i])
            if off_core is not None and off_core[i]:
                cy[i] = "low"
            elif ry[i] >= RUN_HIGH and cons and strong and par and (prom[i] or 0) >= PROM_HIGH and lanes_ok:
                cy[i] = "high"
            elif ry[i] >= RUN_MEDIUM and cons and strong and par:
                cy[i] = "medium"
            else:
                cy[i] = "low"
        for vals, runs, out, sgn, key in ((lo, rl, cl, -1, "lo"), (hi, rh, ch, 1, "hi")):
            if vals[i] is None:
                continue
            cons = _consistent(vals, i) and _parallel(vals, i, bounds[key][0][i], bounds[key][1][i])
            lane_ok = yel[i] is not None and LANE_M[0] <= (vals[i] - yel[i]) * sgn <= LANE_M[1]
            if runs[i] >= RUN_HIGH and cons and lane_ok:
                out[i] = "high"
            elif runs[i] >= RUN_MEDIUM and cons:
                out[i] = "medium"
            else:
                out[i] = "low"
    return cy, cl, ch


def _empty_line():
    return {"xz_m": [], "lap_st_m": [], "heading_deg": [], "confidence": [], "source": []}


def _add(line, fr, p_img, t_img, conf, src, st_window):
    lon, lat = fr.img_to_ll(*p_img)
    xz = fr.ll_to_xz(lon, lat)
    line["xz_m"].append([round(xz[0], 2), round(xz[1], 2)])
    s = fr.station(xz, *st_window)
    line["lap_st_m"].append(None if s is None else round(s, 1))
    line["heading_deg"].append(round(fr.heading(p_img, t_img), 1))
    line["confidence"].append(conf)
    line["source"].append(src)


def _off_core(rows, core):
    """Per profile: its yellow lies inside the core's polar sector of a good yellow circle but off it."""
    if not core:
        return None
    res, fits = core["res"], core["fits"]
    f = fits.get("yel")
    if not f or not res["good"].get("yel"):
        return None
    sgn = 1 if res["direction"] == "left" else -1
    a0, a1 = [math.radians(x) for x in res["core_polar_deg"]]
    sweep = (a1 - a0) * sgn % (2 * math.pi)
    lim = max(CORE_FLOOR_M, CORE_K * f["rms"])
    out = []
    for r in rows:
        if r["yellow"] is None:
            out.append(False)
            continue
        p = pf.pt_at(r, r["yellow"])
        a = math.atan2(p[1] - f["cy"], p[0] - f["cx"])
        inside = (a - a0) * sgn % (2 * math.pi) <= sweep
        out.append(bool(inside and abs(math.hypot(p[0] - f["cx"], p[1] - f["cy"]) - f["R"]) > lim))
    return out


def _profile_rows(rows, s_offset, fr, win_rec, st_pad=30.0, core=None):
    """rows: [{s, p, n, t, yellow, prom, fog_lo, fog_hi}] in travel order (imagery frame)."""
    yel = [r["yellow"] for r in rows]
    prom = [r.get("prom") for r in rows]
    lo = [r.get("fog_lo") for r in rows]
    hi = [r.get("fog_hi") for r in rows]
    cy, cl, ch = profile_confidence(yel, prom, lo, hi, _off_core(rows, core))
    for i, r in enumerate(rows):
        s_est = r["s"] + s_offset
        win = (s_est - st_pad, s_est + st_pad)
        for key, conf, line in (("yellow", cy, "yellow"), ("fog_lo", cl, "edge_right"), ("fog_hi", ch, "edge_left")):
            v = r.get(key)
            if v is None:
                continue
            _add(win_rec[line], fr, pf.pt_at(r, v), r["t"], conf[i], "profile", win)
    return cy


def _reference(rows, conf, ref_poly):
    """The paint centre polyline: ref moved onto the medium+ yellow offsets (median +-3 m, gaps
    interpolated, +-2 m moving average). None without medium+ yellow."""
    keep = [{"s": r["s"], "p": r["p"], "n": r["n"],
             "r": {"yellow": r["yellow"] if (r["yellow"] is not None and conf[i] in ("high", "medium")) else None}}
            for i, r in enumerate(rows)]
    if not any(k["r"]["yellow"] is not None for k in keep):
        return None
    poly, nk = pf.refine_from_yellow(ref_poly, keep)
    return poly


def _add_reference(win_rec, fr, poly, s_offset, st_pad=30.0):
    pts = poly.resample(0.5).p
    ref = {"xz_m": [], "lap_st_m": [], "supported": []}
    yl = win_rec["yellow"]
    good = [tuple(xz) for xz, c in zip(yl["xz_m"], yl["confidence"]) if c in ("high", "medium")]
    sts = [s for s, c in zip(yl["lap_st_m"], yl["confidence"]) if c in ("high", "medium") and s is not None]
    s_lo, s_hi = (min(sts) - st_pad, max(sts) + st_pad) if sts else (s_offset - st_pad, s_offset + poly.L + st_pad)
    for k, p in enumerate(pts):
        lon, lat = fr.img_to_ll(*p)
        xz = fr.ll_to_xz(lon, lat)
        ref["xz_m"].append([round(xz[0], 2), round(xz[1], 2)])
        s = fr.station(xz, s_lo, s_hi)
        ref["lap_st_m"].append(None if s is None else round(s, 1))
        ref["supported"].append(any(math.hypot(xz[0] - g[0], xz[1] - g[1]) <= SUPPORT_M for g in good))
    win_rec["reference"] = ref


def _rows_from_recs(recs, pkey="r"):
    out = []
    for r in recs:
        rr = r.get(pkey) or {}
        out.append({"s": r["s"], "p": r["p"], "n": r["n"], "t": r["t"], "yellow": rr.get("yellow"),
                    "prom": rr.get("yellow_prom"), "fog_lo": rr.get("fog_lo"), "fog_hi": rr.get("fog_hi")})
    return out


def _rows_from_ref(ref_pts, rows):
    ref = pf.Poly(ref_pts)
    out = []
    for r in rows:
        s = r["s"]
        p = ref.pos(s)
        t = ref.tan(s)
        out.append({"s": s, "p": p, "n": pf.left_normal(t), "t": t, "yellow": r.get("yellow"), "prom": r.get("yellow_prom"),
                    "fog_lo": r.get("fog_lo"), "fog_hi": r.get("fog_hi")})
    return out, ref


def _core(win_rec, fr, cid, core, span, st_pad=60.0):
    res, fits, rays = core["res"], core["fits"], core["rays"]
    sgn = 1 if res["direction"] == "left" else -1
    win = (span[0] - st_pad, span[1] + st_pad)
    for key, fk, line in (("yellow", "yel", "yellow"), ("fog_lo", "fog_in", None), ("fog_hi", "fog_out", None)):
        f = fits.get(fk)
        good = bool(res["good"].get(fk))
        if line is None:  # polar lo = towards the centre: inner = right of travel on a left turn
            line = ("edge_left" if key == "fog_lo" else "edge_right") if sgn > 0 else ("edge_right" if key == "fog_lo" else "edge_left")
        for ray in rays:
            v = ray["r"].get(key)
            if v is None:
                continue
            p = (ray["p"][0] + ray["n"][0] * v, ray["p"][1] + ray["n"][1] * v)
            n = ray["n"]
            t = (-n[1] * sgn, n[0] * sgn)
            if f is not None:
                inlier = abs(math.hypot(p[0] - f["cx"], p[1] - f["cy"]) - f["R"]) <= max(CORE_FLOOR_M, CORE_K * f["rms"])
                conf = ("high" if good else "medium") if inlier else "low"
            else:
                conf = "low"
            _add(win_rec[line], fr, p, t, conf, "core_ray", win)

    def circ(f, good):
        if not f:
            return None
        lon, lat = fr.img_to_ll(f["cx"], f["cy"])
        xz = fr.ll_to_xz(lon, lat)
        return {"centre_xz_m": [round(xz[0], 2), round(xz[1], 2)], "centre_lonlat": [round(lon, 8), round(lat, 8)],
                "R_m": round(f["R"], 3), "rms_m": round(f["rms"], 3), "n": f["n"], "good": bool(good)}
    a0, a1 = [math.radians(x) for x in res["core_polar_deg"]]
    yf = fits.get("yel")
    ends = []
    if yf:
        for a in (a0, a1):
            p = (yf["cx"] + yf["R"] * math.cos(a), yf["cy"] + yf["R"] * math.sin(a))
            lon, lat = fr.img_to_ll(*p)
            xz = fr.ll_to_xz(lon, lat)
            ends.append({"xz_m": [round(xz[0], 2), round(xz[1], 2)]})
    win_rec["core"] = {
        "direction": res["direction"], "turn_deg": res["turn_deg"], "arc_deg": res["core_arc_deg"],
        "yellow_circle": circ(yf, res["good"].get("yel")),
        "edge_line_inner_circle": circ(fits.get("fog_in"), res["good"].get("fog_in")),
        "edge_line_outer_circle": circ(fits.get("fog_out"), res["good"].get("fog_out")),
        "core_ends_on_yellow_circle": ends,
        "_doc": "core = headings 20-80 % of the turn; core_ends_on_yellow_circle are the arc's first and last point in travel order",
    }


def build(ctx, corner_traces, cores, width_res, junctions, corner_conf):
    fr = Frames(ctx)
    windows = []
    for cid, tr in corner_traces.items():
        W, ref, recs, s_lo, span = tr
        rec = {"id": cid, "kind": "corner", "window": cid, "corner_confidence": corner_conf.get(cid, "none"),
               "yellow": _empty_line(), "edge_left": _empty_line(), "edge_right": _empty_line()}
        rows = _rows_from_recs(recs)
        conf = _profile_rows(rows, s_lo, fr, rec, core=cores.get(cid))
        if cid in cores:
            _core(rec, fr, cid, cores[cid], span)
        poly = _reference(rows, conf, ref)
        if poly is not None:
            _add_reference(rec, fr, poly, s_lo)
        rec["lap_st_m"] = _span(rec)
        windows.append(rec)
    for wid in sorted(width_res, key=lambda k: int(k[1:])):
        w = width_res[wid]
        st = w["res"]["station_m"]
        rows, ref = _rows_from_ref(w["ref"], w["rows"])
        s_off = st - 22.0
        rec = {"id": wid, "kind": "width_station", "window": wid, "station_m": st,
               "yellow": _empty_line(), "edge_left": _empty_line(), "edge_right": _empty_line()}
        usable = any((w["res"].get(k) or {}).get("n", 0) >= USABLE_MIN_PROFILES for k in ("edge_line_width", "pavement_width"))
        rec["usable"] = usable
        conf = _profile_rows(rows, s_off, fr, rec)
        if not usable:
            for key in ("yellow", "edge_left", "edge_right"):
                rec[key]["confidence"] = ["low"] * len(rec[key]["confidence"])
            conf = ["low" if c else c for c in conf]
        poly = _reference(rows, conf, ref)
        if poly is not None:
            _add_reference(rec, fr, poly, s_off)
        rec["lap_st_m"] = _span(rec)
        windows.append(rec)
    for cid, jd in junctions.items():
        for arm in ("in", "out"):
            a = jd["arms"][arm]
            rows, ref = _rows_from_ref(a["ref"], a["rows"])
            s_off = min(a["s_range_lap"]) - 3.0
            rec = {"id": f"{cid}_{arm}", "kind": "junction_arm", "window": cid, "corner": cid, "arm": arm,
                   "yellow": _empty_line(), "edge_left": _empty_line(), "edge_right": _empty_line()}
            conf = _profile_rows(rows, s_off, fr, rec)
            poly = _reference(rows, conf, ref)
            if poly is not None:
                _add_reference(rec, fr, poly, s_off)
            rec["lap_st_m"] = _span(rec)
            windows.append(rec)
    counts = {}
    for w in windows:
        for c in w["yellow"]["confidence"]:
            counts[c] = counts.get(c, 0) + 1
    lap_md5 = hashlib.md5(Path(ctx.lap_path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return {
        "schema": "airoso paint traces v1",
        "written_by": "tools/aerial_measure.py (tools/aerial/traces.py)",
        "_doc": __doc__.strip(),
        "imagery": "USDA NAIP Colorado 2019 (public domain), measured in NAD83 / UTM 13N; see aerial_measurements.json",
        "registration": {"osm_minus_imagery_EN_m": list(ctx.V),
                         "_doc": "every point here is the imagery point moved by this offset, so it lines up with OSM and the centreline"},
        "frame": {
            "xz_m": ("local ENU metres, x east, z north, about origin_lonlat (scripts.geometry.projection.centroid of the lap "
                     "centreline; centerline.local.json's own origin differs by < 1 mm): lon = lon0 + x / m_lon, lat = lat0 + "
                     "z / m_lat with scripts.geometry.projection._meters_per_degree(lat0) = m_per_deg"),
            "origin_lonlat": [fr.lon0, fr.lat0],
            "m_per_deg": [fr.mlon, fr.mlat],
            "lap_st_m": "metres from v0 of the lap centreline in the xz frame (geojson stations; the config's local frame adds the start_at offset)",
            "heading_deg": "direction of Full (forward) travel, degrees counter-clockwise from east, xz frame",
            "lap_centerline": str(Path(ctx.lap_path).relative_to(ctx.project)).replace("\\", "/"),
            "lap_centerline_md5": lap_md5,
        },
        "confidence_counts_yellow": counts,
        "windows": windows,
    }


def _span(rec):
    s = [x for x in rec["yellow"]["lap_st_m"] if x is not None]
    return [round(min(s), 1), round(max(s), 1)] if s else None


def dumps(obj) -> str:
    """JSON with every data array (a list of numbers, strings, booleans or small lists) on one line."""
    import json
    nl = "\n"

    def is_data(v):
        return isinstance(v, list) and all(not isinstance(x, (dict, list)) or
                                           (isinstance(x, list) and all(not isinstance(y, (dict, list)) for y in x)) for x in v)

    def enc(v, ind):
        pad = " " * ind
        if isinstance(v, dict):
            if not v:
                return "{}"
            items = [f'{pad} {json.dumps(k, ensure_ascii=False)}: {enc(x, ind + 1)}' for k, x in v.items()]
            return "{" + nl + ("," + nl).join(items) + nl + pad + "}"
        if isinstance(v, list) and not is_data(v):
            items = [pad + " " + enc(x, ind + 1) for x in v]
            return "[" + nl + ("," + nl).join(items) + nl + pad + "]"
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return enc(obj, 0) + nl

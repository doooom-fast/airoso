"""Measured road widths over the OSM width profile, in the LOCAL frame (Lariat V3, ledger 0048, P2 step 1).

Runs after ``scripts.gps.widths_from_osm`` (the ``route.width_profile`` table, e.g. ``mountain``). That stage
leaves three things this one undoes or replaces, opt-in per track (nothing else calls this module):

  * **frame**: it computes widths per vertex of ``data/centerline.geojson`` and writes them 1:1 into
    ``centerline.local.json`` when the counts match, but projection rotated the local ring to ``route.start_at``
    (k vertices; 2 on the Lariat's paint line), so every width sits k vertices off. Here the OSM widths are
    rotated into the local frame (k is derived by matching the two point sets, never assumed);
  * **invented widenings**: its junction flares, hard-corner flares (>= 14 m) and the automatic 10 m floor on
    every fold over 110 degrees. None is a measurement; on the Lariat the fold floor widens every hairpin, which
    plan A2 keeps off for Drive 1. The OSM base (``widths_base_m``, before any flare) is used, and the flares it
    would have laid are listed in the record for P3b (the mouths are authored, JUNCTIONS.md);
  * **published and measured widths**: ``width_overrides`` (local stations, the dossier's) and the aerial pass
    (``route.measured_widths``: ``data/aerial/aerial_measurements.json``: width stations, hairpin legs, hairpin
    apexes) override the OSM table: measured > published > OSM.

The rule, per top-level ``width_overrides`` stretch (one not nested inside another):
  - with measured points inside it: the width at each vertex is the linear interpolation of those points by
    station, held flat from the first / last point to the stretch's ends (touching stretches that are both
    measured interpolate as one, so a hairpin measured either side of their boundary tapers through it);
  - else with a published ``width_m``: that width;
  - else the OSM width.
A measured point is the painted travelled way, edge-line centre to edge-line centre, plus one stripe width
(``STRIPE_W_M`` 0.10 m, MUTCD's 4 in normal line: centre-to-centre + one stripe = outer edge to outer edge);
where a stretch is a town street with no edge lines (``town_segments``) the curb-to-curb pavement width is used.
Aerial stations are on ``data/centerline.osm.geojson`` (from its v0); they reach the paint line through its
per-vertex ``osm_station_m``, then the local frame through the same rotation.
Then width changes are rate-limited round the closed lap (``scripts.geometry.projection.slew_limit_widths``'s
0.25 m of width per metre, applied cyclically: L13, the seam is adjacent to itself).

Writes ``centerline.local.json`` ``widths_m`` (and ``widths_base_m`` = the same: no flares, sidewalks follow the
road), ``widths_osm_m`` (the OSM table in the local frame), ``widths_frame`` = "local"; and
``data/widths.measured.json`` (every point used or refused, per-stretch min / median / max, the flares not laid).

    python -m scripts.gps.measured_widths <project-dir>
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from scripts.geometry.projection import _meters_per_degree

STRIPE_W_M = 0.10            # [std: MUTCD 3A.05, a normal line is 4-6 in wide; 4 in = 0.10 m]
SLEW_RATE = 0.25             # m of width per m of road: projection.slew_limit_widths's existing rate
FRAME_TOL_M = 0.05           # local and geojson points must coincide after the rotation (a frame check, not a gate)


def _xy(lonlat, lon0, lat0):
    mlon, mlat = _meters_per_degree(lat0)
    return [((a - lon0) * mlon, (b - lat0) * mlat) for a, b in lonlat]


def _stations(xy):
    st = [0.0]
    for i in range(1, len(xy)):
        st.append(st[-1] + math.hypot(xy[i][0] - xy[i - 1][0], xy[i][1] - xy[i - 1][1]))
    return st


def local_rotation(geo_xy, local_xz, tol=FRAME_TOL_M) -> int:
    """k such that local[i] == geojson[(i + k) mod m] (m unique vertices of the closed ring). Raises when the two
    point sets are not the same ring rotated."""
    m = len(geo_xy) - 1
    if len(local_xz) != len(geo_xy):
        raise ValueError(f"local has {len(local_xz)} points, the geojson {len(geo_xy)}: not the same line")
    p0 = local_xz[0]
    k = min(range(m), key=lambda j: (geo_xy[j][0] - p0[0]) ** 2 + (geo_xy[j][1] - p0[1]) ** 2)
    worst = max(math.dist(local_xz[i], geo_xy[(i + k) % m]) for i in range(m))
    if worst > tol:
        raise ValueError(f"local is not the geojson ring rotated by {k} (worst {worst:.3f} m)")
    return k


def rotate_ring(vals, k):
    """Per-vertex values of a closed ring (last == first) rotated so index 0 is old index k."""
    m = len(vals) - 1
    out = [vals[(i + k) % m] for i in range(m)]
    return out + [out[0]]


def cyclic_slew(widths, st, rate=SLEW_RATE, closed=True):
    """projection.slew_limit_widths, but round a closed lap: the seam is adjacent to itself (L13). Only lowers."""
    n = len(widths)
    m = n - 1 if closed else n
    w = list(widths[:m])
    seg = [st[i + 1] - st[i] for i in range(m - 1)] + ([st[-1] - st[m - 1]] if closed else [])
    for _ in range(4):
        for i in range(m - 1 + (1 if closed else 0)):
            j = (i + 1) % m
            lim = w[i] + rate * seg[i]
            if w[j] > lim:
                w[j] = lim
        for i in range(m - 2 + (1 if closed else 0), -1, -1):
            j = (i + 1) % m
            lim = w[j] + rate * seg[i]
            if w[i] > lim:
                w[i] = lim
    return w + ([w[0]] if closed else [])


def osm_to_geo_station(s_osm, osm_st, geo_st):
    """A station on the OSM source line -> the paint line's geojson station (through osm_station_m)."""
    import bisect
    k = bisect.bisect_right(osm_st, s_osm)
    if k <= 0:
        return geo_st[0]
    if k >= len(osm_st):
        return geo_st[-1]
    a, b = osm_st[k - 1], osm_st[k]
    t = 0.0 if b <= a else (s_osm - a) / (b - a)
    return geo_st[k - 1] + t * (geo_st[k] - geo_st[k - 1])


def geo_to_local_station(s_geo, geo_st, k):
    lap = geo_st[-1]
    return (s_geo - geo_st[k]) % lap if k else s_geo


def measured_points(aerial: dict, to_local, town_segments=("Golden",)):
    """Every width the aerial pass measured, as (local_station, width_m, source, id, note); refused ones too."""
    used, refused = [], []
    w = aerial.get("widths") or {}
    for s in w.get("stations") or []:
        e, p = s.get("edge_line_width_m"), s.get("pavement_width_m")
        seg = s.get("segment") or ""
        rid = f"W{float(s['station_m']):.0f}"
        if not s.get("usable"):
            refused.append({"id": rid, "why": "not usable: " + (s.get("note") or "tree shadow")})
            continue
        if e and e.get("median"):
            used.append((to_local(float(s["station_m"])), e["median"] + STRIPE_W_M, "edge_lines", rid, s.get("note")))
        elif p and p.get("median") and any(seg.startswith(t) for t in town_segments):
            used.append((to_local(float(s["station_m"])), p["median"], "pavement_town", rid,
                         s.get("note") or "town street: curb to curb"))
        else:
            refused.append({"id": rid, "why": "no edge lines and not a town street (pavement width is an upper "
                                              "bound there: " + (s.get("note") or "") + ")"})
    for cid, legs in (w.get("hairpin_legs") or {}).items():
        for side, leg in legs.items():
            a, b = leg["lap_st_range"]
            used.append((to_local((a + b) / 2.0), leg["edge_line_width_median"] + STRIPE_W_M, "hairpin_leg",
                         f"{cid}.{side}", None))
    apex_st = {c["id"]: c.get("apex_lap_st_m") for c in aerial.get("corners") or []}
    for cid, ap in (w.get("corner_apexes") or {}).items():
        el = (ap.get("edge_line_width") or {}).get("median")
        if el and apex_st.get(cid) is not None:
            note = None
            if ap.get("lane_inner") and ap.get("lane_outer"):
                note = f"lanes inner {ap['lane_inner']['median']} / outer {ap['lane_outer']['median']} m"
            used.append((to_local(float(apex_st[cid])), el + STRIPE_W_M, "hairpin_apex", f"{cid}.apex", note))
        else:
            refused.append({"id": f"{cid}.apex", "why": "no apex station or edge-line width"})
    return sorted(used), refused


def top_level_stretches(overrides):
    st = [o for o in overrides or [] if isinstance(o.get("st_m"), list) and len(o["st_m"]) == 2]
    out = []
    for o in st:
        a, b = o["st_m"]
        nested = any(p is not o and p["st_m"][0] <= a and b <= p["st_m"][1] and (p["st_m"][1] - p["st_m"][0]) > (b - a)
                     for p in st)
        if not nested:
            out.append(o)
    return sorted(out, key=lambda o: o["st_m"][0])


def _interp_points(pts, s):
    if s <= pts[0][0]:
        return pts[0][1]
    if s >= pts[-1][0]:
        return pts[-1][1]
    for (s0, w0), (s1, w1) in zip(pts, pts[1:]):
        if s0 <= s <= s1:
            return w0 + (w1 - w0) * (s - s0) / max(1e-9, s1 - s0)
    return pts[-1][1]


def build(project_dir, log=print) -> dict:
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    gj = json.loads((data / "centerline.geojson").read_text(encoding="utf-8"))
    full = next(f for f in gj["features"] if (f.get("properties") or {}).get("kind") == "full")
    lonlat = [(float(a), float(b)) for a, b in full["geometry"]["coordinates"]]
    props = full.get("properties") or {}
    lp = data / "centerline.local.json"
    local = json.loads(lp.read_text(encoding="utf-8"))
    o = local["origin"]
    geo_xy = _xy(lonlat, o["lon"], o["lat"])
    loc_xz = [(p[0], p[2]) for p in local["points_xyz_m"]]
    if lonlat[0] != lonlat[-1]:
        raise SystemExit("[measured_widths] the centreline is not a closed lap (this stage is for loops)")
    k = local_rotation(geo_xy, loc_xz)
    geo_st = _stations(geo_xy)
    st = _stations(loc_xz)
    if "widths_base_m" not in local:
        raise SystemExit("[measured_widths] centerline.local.json has no widths_base_m: run scripts.gps.widths_from_osm first")
    if local.get("widths_frame") == "local":
        raise SystemExit("[measured_widths] centerline.local.json widths are already this stage's (re-run "
                         "projection + widths_from_osm first; this stage reads widths_from_osm's geojson-indexed output)")
    osm_flared = rotate_ring(local["widths_m"], k)
    osm = rotate_ring(local["widths_base_m"], k)

    osm_st = props.get("osm_station_m")
    if not osm_st or len(osm_st) != len(lonlat):
        raise SystemExit("[measured_widths] the centreline carries no per-vertex osm_station_m (not the paint line?)")
    mw = (cfg.get("route") or {}).get("measured_widths") or {}
    aerial_p = proj / mw.get("aerial", "data/aerial/aerial_measurements.json")
    aerial = json.loads(aerial_p.read_text(encoding="utf-8"))

    def to_local(s_osm):
        return geo_to_local_station(osm_to_geo_station(s_osm, osm_st, geo_st), geo_st, k)

    pts, refused = measured_points(aerial, to_local, tuple(mw.get("town_segments") or ("Golden",)))
    lap = st[-1]
    stretches = top_level_stretches(cfg.get("width_overrides"))
    widths = list(osm)
    src = ["osm"] * len(widths)
    summary = []
    # touching stretches that are both measured are ONE interpolation domain: a hairpin measured either side of a
    # stretch boundary (C2's apex at the Golden / Lariat Trail line) tapers through it instead of stepping
    measured_spans = []
    for o2 in stretches:
        a, b = (float(v) for v in o2["st_m"])
        if any(a <= s <= b for s, *_ in pts):
            if measured_spans and abs(measured_spans[-1][1] - a) < 1e-6:
                measured_spans[-1][1] = b
            else:
                measured_spans.append([a, b])

    def domain(a, b):
        for d0, d1 in measured_spans:
            if d0 <= a and b <= d1:
                return d0, d1
        return a, b

    for o2 in stretches:
        a, b = (float(v) for v in o2["st_m"])
        inside = [(s, w) for s, w, *_ in pts if a <= s <= b]
        if inside:
            how = "measured"
            d0, d1 = domain(a, b)
            dom = [(s, w) for s, w, *_ in pts if d0 <= s <= d1]
            for i, s in enumerate(st):
                if a <= s <= b:
                    widths[i], src[i] = _interp_points(dom, s), "measured"
        elif o2.get("width_m"):
            how = "published"
            for i, s in enumerate(st):
                if a <= s <= b:
                    widths[i], src[i] = float(o2["width_m"]), "published"
        else:
            how = "osm"
        summary.append({"road": o2.get("road"), "st_m": [a, b], "source": how, "points": len(inside)})
    outside = [p[3] for p in pts if not any(float(o2["st_m"][0]) <= p[0] <= float(o2["st_m"][1]) for o2 in stretches)]
    widths[-1] = widths[0]
    final = cyclic_slew(widths, st, SLEW_RATE, closed=True)
    final = [round(v, 2) for v in final]
    for row in summary:
        a, b = row["st_m"]
        ws = [w for w, s in zip(final, st) if a <= s <= b]
        if ws:
            row.update({"min_m": min(ws), "median_m": round(statistics.median(ws), 2), "max_m": max(ws)})
    slewed = sum(1 for a2, b2 in zip(widths, final) if abs(a2 - b2) > 0.005)
    flares = []
    i = 0
    while i < len(osm):
        if osm_flared[i] > osm[i] + 0.01:
            j = i
            while j + 1 < len(osm) and osm_flared[j + 1] > osm[j + 1] + 0.01:
                j += 1
            flares.append({"local_m": [round(st[i], 1), round(st[j], 1)],
                           "max_width_m": round(max(osm_flared[i:j + 1]), 2)})
            i = j + 1
        else:
            i += 1

    local["widths_osm_m"] = [round(v, 2) for v in osm]
    local["widths_m"] = final
    local["widths_base_m"] = list(final)
    local["default_width_m"] = round(sum(final) / len(final), 2)
    local["widths_frame"] = "local"
    local["widths_source"] = "scripts/gps/measured_widths.py (data/widths.measured.json)"
    lp.write_text(json.dumps(local), encoding="utf-8")
    rec = {"tool": "scripts/gps/measured_widths.py", "frame": "local stations (centerline.local.json, v0 = route.start_at)",
           "local_rotation_vertices": k, "lap_m": round(lap, 2), "stripe_w_m": STRIPE_W_M, "slew_rate": SLEW_RATE,
           "precedence": "measured (aerial NAIP 2019) > published (width_overrides.width_m) > OSM (route.width_profile)",
           "aerial": str(aerial_p.relative_to(proj)).replace("\\", "/"),
           "points": [{"local_m": round(s, 1), "width_m": round(w, 2), "source": so, "id": i2,
                       **({"note": n} if n else {})} for s, w, so, i2, n in pts],
           "points_outside_any_stretch": outside, "refused": refused, "stretches": summary,
           "vertices_by_source": {s: src.count(s) for s in sorted(set(src))},
           "vertices_slew_limited": slewed,
           "osm_flares_not_laid": {"_doc": "widths_from_osm's junction flares, hard-corner flares and 10 m fold floors "
                                           "(not measurements; mouths are authored in P3b, A2 keeps hairpin widening off)",
                                   "runs": flares},
           "summary": {"min_m": min(final), "median_m": round(statistics.median(final), 2), "max_m": max(final)}}
    (data / "widths.measured.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    log(f"[measured_widths] frame: widths_from_osm's widths were {k} vertices off the local ring; rotated")
    log(f"[measured_widths] {len(pts)} measured points used ({len(refused)} refused); vertices by source "
        f"{rec['vertices_by_source']}; {slewed} slew-limited; {len(flares)} OSM flare runs not laid")
    for row in summary:
        log(f"  {row['st_m'][0]:>7.0f}-{row['st_m'][1]:<7.0f} {row['source']:9s} {row.get('min_m', '-')}-"
            f"{row.get('max_m', '-')} m (median {row.get('median_m', '-')})  {row['road']}")
    log(f"[measured_widths] lap widths {rec['summary']['min_m']}-{rec['summary']['max_m']} m, median "
        f"{rec['summary']['median_m']} m -> centerline.local.json, data/widths.measured.json")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.gps.measured_widths")
    ap.add_argument("project_dir")
    a = ap.parse_args(argv)
    build(a.project_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

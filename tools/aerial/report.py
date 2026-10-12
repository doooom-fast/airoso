"""Assemble ``aerial_measurements.json``: per-corner records (the radius decision and its confidence), the
widths, the bridge crossings, the registration and the windows, with the spec's authored text carried
verbatim.

The radius decision for a hairpin (thresholds all **[invented]** for the aerial pass, 2026-10-11, none a
gate; listed in the JSON's ``methods.thresholds_invented``):
- a concentric pair is "good" when both sides are traced on >= 40 % of the core rays
  (``PAIR_MIN_COVERAGE``) with rms <= 0.35 m (``PAIR_MAX_RMS_M``); the yellow circle when traced on >= 45 %
  with rms <= 0.35 m;
- radius = the pavement-edge pair's mean when it is good and within 1.0 m (``PAVEMENT_VS_PAINTED_MAX_M``)
  of the painted estimates, else the painted edge-line pair's mean, else the yellow circle, else the ridge
  search;
- confidence: high when >= 2 independent estimates spread <= 0.75 m (``HIGH_CONF_SPREAD_M``), medium <=
  1.5 m (``MEDIUM_CONF_SPREAD_M``) or one estimate (supported by a partial one within 0.6 m, or not), low
  otherwise and always for the ridge search; uncertainty = half the spread + 0.2 m (min 0.3) high,
  + 0.3 m medium, 0.8 m for one unsupported estimate, 1.0 m low [invented];
- a partial estimate supports when traced on >= 25 % with rms <= 0.35 m [invented];
- junctions: uncertainty = half the R band within 0.15 m of the best residual + 0.3 m (min 0.5) + 0.5 m,
  confidence medium [invented].
"""
from __future__ import annotations

import math
import statistics as stt
import time

from . import circles, geo

PAIR_MIN_COVERAGE = 0.4
PAIR_MAX_RMS_M = 0.35
PAVEMENT_VS_PAINTED_MAX_M = 1.0
HIGH_CONF_SPREAD_M = 0.75
MEDIUM_CONF_SPREAD_M = 1.5

THRESHOLDS = {"asphalt_match_z": 3.0, "edge_run_m": 0.45, "edge_search_beyond_line_m": 8.0, "shadow_mean_rgb": 45,
              "pair_min_core_coverage": PAIR_MIN_COVERAGE, "pair_max_rms_m": PAIR_MAX_RMS_M,
              "pavement_vs_painted_max_m": PAVEMENT_VS_PAINTED_MAX_M, "high_conf_spread_m": HIGH_CONF_SPREAD_M,
              "medium_conf_spread_m": MEDIUM_CONF_SPREAD_M}

RIDGE_NOTE = ("grid search for the circle that maximises yellow-paint ridge strength over the core; biased where "
              "yellowish dry soil borders the pavement, so it is a check, not an estimate, except where the apex is shadowed")


def r2(x, nd=2):
    return None if x is None else round(x, nd)


def to_wgs(ctx, E, N):
    lon, lat = geo.from_utm(E + ctx.V[0], N + ctx.V[1])
    return [round(lon, 7), round(lat, 7)]


def osm_offsets(ctx, points):
    """Distance from imagery-frame points to the OSM lap line moved into the imagery frame."""
    V = ctx.V
    lapimg = [(p[0] - V[0], p[1] - V[1]) for p in ctx.L.utm]
    out = []
    for P in points:
        best = None
        for i in range(len(lapimg) - 1):
            a, b = lapimg[i], lapimg[i + 1]
            if abs(a[0] - P[0]) > 60 or abs(a[1] - P[1]) > 60:
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            if L2 == 0:
                continue
            t = max(0, min(1, ((P[0] - a[0]) * dx + (P[1] - a[1]) * dy) / L2))
            d = math.hypot(a[0] + t * dx - P[0], a[1] + t * dy - P[1])
            best = d if best is None or d < best else best
        if best is not None:
            out.append(best)
    return out


def hairpin(ctx, cid, d, ridge):
    """One hairpin's record + its overlay label and final circle. ``d`` = corners.measure's result."""
    text = ctx.spec["text"]
    res, fits, feats, rays = d["res"], d["fits"], d["feats"], d["rays"]
    nr = len(rays)
    seedc = d["c"]
    pave = circles.concentric(feats["in"], feats["out"], seedc)
    lines = circles.concentric(feats["fog_in"], feats["fog_out"], seedc)
    yel = fits.get("yel")

    def pair_rec(f, kin, kout):
        if not f:
            return None
        cin = f["n_in"] / nr
        cout = f["n_out"] / nr
        ok = cin >= PAIR_MIN_COVERAGE and cout >= PAIR_MIN_COVERAGE and f["rms_in"] <= PAIR_MAX_RMS_M and f["rms_out"] <= PAIR_MAX_RMS_M
        why = None
        if not ok:
            bits = []
            if cin < PAIR_MIN_COVERAGE:
                bits.append("inner %s traced on %d%% of the core rays" % (kin, round(100 * cin)))
            if cout < PAIR_MIN_COVERAGE:
                bits.append("outer %s traced on %d%% of the core rays" % (kout, round(100 * cout)))
            if f["rms_in"] > PAIR_MAX_RMS_M:
                bits.append("inner rms %.2f m" % f["rms_in"])
            if f["rms_out"] > PAIR_MAX_RMS_M:
                bits.append("outer rms %.2f m" % f["rms_out"])
            why = "; ".join(bits)
        return {"R_inner": r2(f["R_in"]), "R_outer": r2(f["R_out"]), "R_mean": r2(f["R_mean"]),
                "rms_inner_m": r2(f["rms_in"], 3), "rms_outer_m": r2(f["rms_out"], 3),
                "coverage_inner": r2(cin), "coverage_outer": r2(cout),
                "centre_utm13n_nad83": [r2(f["cx"]), r2(f["cy"])], "good": ok, "why_not_good": why}
    pr = pair_rec(pave, "pavement edge", "pavement edge")
    lr = pair_rec(lines, "edge line", "edge line")
    yr = None
    if yel:
        cov = yel["n"] / nr
        yr = {"R": r2(yel["R"]), "rms_m": r2(yel["rms"], 3), "coverage": r2(cov), "arc_deg": r2(yel["span_deg"], 1),
              "centre_utm13n_nad83": [r2(yel["cx"]), r2(yel["cy"])], "good": bool(cov >= 0.45 and yel["rms"] <= 0.35)}
    rid = None
    if ridge is not None:
        rid = {"R": r2(ridge["R"]), "sunlit_fraction": r2(ridge["sunlit_frac"]),
               "centre_utm13n_nad83": [r2(ridge["centre"][0]), r2(ridge["centre"][1])], "note": RIDGE_NOTE}
    painted = [x for x in ((lr or {}).get("R_mean") if (lr or {}).get("good") else None,
                           (yr or {}).get("R") if (yr or {}).get("good") else None) if x is not None]
    pm = stt.median(painted) if painted else None
    chosen = method = centre = None
    notes = []
    if pr and pr["good"] and (pm is None or abs(pr["R_mean"] - pm) <= PAVEMENT_VS_PAINTED_MAX_M):
        chosen, method, centre = pr["R_mean"], "pavement edges: one centre, two radii (concentric fit), mean of inner and outer", pr["centre_utm13n_nad83"]
    elif lr and lr["good"]:
        chosen, method, centre = lr["R_mean"], "painted edge lines: one centre, two radii (concentric fit), mean of inner and outer", lr["centre_utm13n_nad83"]
        if pr and pr["good"]:
            notes.append("pavement-edge pair fits (mean %.2f m) but sits %.1f m off the painted estimates: the outer pavement edge "
                         "here includes an apron or pull-off, so the painted edges stand in for the edges" % (pr["R_mean"], pr["R_mean"] - pm))
    elif yr and yr["good"]:
        chosen, method, centre = yr["R"], "yellow centre line circle (edge pairs not usable)", yr["centre_utm13n_nad83"]
    elif rid:
        chosen, method, centre = rid["R"], "yellow-paint ridge search (apex mostly in shadow)", rid["centre_utm13n_nad83"]
    fam = []
    if method and method.startswith("pavement"):
        fam = [pr["R_mean"]]
    fam += [x for x in ((lr or {}).get("R_mean") if (lr or {}).get("good") else None,
                        (yr or {}).get("R") if (yr or {}).get("good") else None) if x is not None]
    partial = [x["R_mean"] if "R_mean" in x else x["R"] for x in (lr, yr)
               if x and not x["good"] and min(x.get("coverage_inner", x.get("coverage", 0)), x.get("coverage_outer", 1)) >= 0.25
               and max(x.get("rms_inner_m", x.get("rms_m", 9)), x.get("rms_outer_m", 0)) <= 0.35]
    spread = (max(fam) - min(fam)) if len(fam) >= 2 else None
    supported = [p for p in partial if chosen is not None and abs(p - chosen) <= 0.6]
    if chosen is None:
        conf, unc = "none", None
    elif len(fam) >= 2 and spread <= HIGH_CONF_SPREAD_M:
        conf, unc = "high", max(0.3, round(spread / 2 + 0.2, 1))
    elif len(fam) >= 2 and spread <= MEDIUM_CONF_SPREAD_M:
        conf, unc = "medium", round(spread / 2 + 0.3, 1)
    elif len(fam) == 1 and supported:
        conf, unc = "medium", max(0.5, round(abs(supported[0] - chosen) / 2 + 0.3, 1))
    elif len(fam) == 1:
        conf, unc = "medium", 0.8
    else:
        conf, unc = "low", 1.0
    if method and method.startswith("yellow-paint ridge"):
        conf, unc = "low", 1.0
        notes.append("the apex is in tree shadow (only ~1/3 of the core arc sunlit); the radius comes from the circle that best "
                     "follows the sunlit yellow paint, and the partial edge-line pair (mean %.2f m) agrees within %.1f m"
                     % ((lr or {}).get("R_mean") or float("nan"), abs(((lr or {}).get("R_mean") or chosen) - chosen)))
    if pr and pr["good"] and method and not method.startswith("pavement"):
        pass
    elif pr and not pr["good"]:
        notes.append("pavement-edge pair: %s (aprons, pull-offs, gravel margins and tree shadow make the pavement edge "
                     "irregular at this hairpin; the painted edge lines are circular to ~0.1-0.2 m)" % pr["why_not_good"])
    offs = osm_offsets(ctx, feats["yel"]) if feats["yel"] else []
    prof = [(p["lap_st"], p["R_10m"]) for p in res["radius_profile_yellow"] if p["R_10m"] is not None and abs(p["R_10m"]) < 200]
    if offs and max(offs) > 1.5:
        ph = text["corner_osm_offset_phrase"]
        notes.append(text["corner_osm_offset_note"].format(median=stt.median(offs), max=max(offs), phrase=ph.get(cid, ph["_default"])))
    shape = (text.get("corner_shape_notes") or {}).get(cid)
    if shape:
        notes.append(shape.format(osm_max=max(offs) if offs else float("nan")))
    fc = ctx.plan[cid]
    rec = {
        "id": cid, "name": ctx.names.get(cid), "dossier": text["corners"][cid]["dossier"],
        "apex_lap_st_m": fc["apex_st_m"], "turn_deg_aerial": res["turn_deg"], "direction": res["direction"],
        "radius_m": r2(chosen), "radius_method": method, "uncertainty_m": unc, "confidence": conf,
        "centre": None if not centre else {"utm13n_nad83": centre, "lonlat_wgs84": to_wgs(ctx, *centre)},
        "core": {"definition": "headings 20-80 % of the turn between the traced entry and exit legs (tools/fit_hairpins.py's core)",
                 "polar_deg_from_east": res["core_polar_deg"], "arc_deg": res["core_arc_deg"], "rays": nr},
        "estimates": {"pavement_edges": pr, "painted_edge_lines": lr, "yellow_centre_line": yr, "yellow_ridge_search": rid},
        "estimates_spread_m": r2(spread), "supporting_partial_estimates": [r2(x) for x in partial],
        "apex_cross_section": {"pavement_width": res["width_core"], "edge_line_width": res["edge_line_width_core"],
                               "lane_inner": res["lane_inner_core"], "lane_outer": res["lane_outer_core"]},
        "osm_vs_paint_core": {"median_m": r2(stt.median(offs)) if offs else None, "max_m": r2(max(offs)) if offs else None,
                              "note": "distance from the traced yellow line to the OSM lap line after removing the %.1f m datum shift"
                                      % math.hypot(*ctx.V)},
        "fitter_osm": {"radius_measured_m": fc["measured"].get("radius_m"), "radius_fit_m": fc.get("radius_fit_m"), "status": fc.get("status")},
        "radius_profile_yellow_10m": prof,
        "notes": notes,
    }
    lab = ["%s %s  st %.0f  turn %.0f deg %s" % (cid, ctx.names.get(cid, ""), fc["apex_st_m"], abs(res["turn_deg"]), res["direction"]),
           "radius %s m +-%s (%s)  %s" % (rec["radius_m"], unc, conf, (method or "").split(":")[0]),
           "cyan/blue: inner/outer pavement edge (grey: rejected)   white: painted edge lines",
           "yellow: centre line   red: OSM lap line + nodes (datum-shifted)   magenta: result   wedge: core"]
    final = {"cx": centre[0], "cy": centre[1], "R": chosen} if centre else None
    rec["overlay"] = "overlays/%s.png" % cid
    return rec, lab, final


def junction(ctx, cid, jd):
    text = ctx.spec["text"]
    o = jd["out"]
    fc = ctx.plan[cid]
    scan = o["scan"]
    best = min(s[1] for s in scan)
    band = [s[0] for s in scan if s[1] <= best + 0.15]
    fcheck = o.get("free_circle_check") or {}
    unc = max(0.5, round((max(band) - min(band)) / 2 + 0.3, 1))
    free_note = None
    if fcheck.get("R") is not None:
        free_note = ("an unconstrained circle through the same core points gives R %.2f m with its centre %.1f m away; over a ~%d "
                     "deg arc with %s that fit is poorly conditioned, so the tangent-constrained value is kept"
                     % (fcheck["R"], fcheck.get("centre_gap_m", float("nan")), round(0.6 * abs(o["inside_edge_lines_angle_deg"])),
                        text["junction_free_fit_phrase"][cid]))
    rec = {
        "id": cid, "name": ctx.names.get(cid), "dossier": text["corners"][cid]["dossier"],
        "apex_lap_st_m": fc["apex_st_m"], "turn_deg_osm": fc["measured"]["turn_deg"],
        "inside_edge_lines_angle_deg": o["inside_edge_lines_angle_deg"],
        "radius_m": o.get("R_centreline"), "uncertainty_m": round(unc + 0.5, 1), "confidence": "medium",
        "radius_method": ("junction: the lap turns through an intersection, so no painted arc exists. Inside kerb-return fillet "
                          "fitted as an arc tangent to both arms' inside pavement edges (line-arc-line, one parameter), then the "
                          "lap-centreline arc concentric with it: R = R_fillet + mean inside half-width (arm centre line to inside "
                          "pavement edge)"),
        "R_fillet_inside_m": o["R_fillet"], "fillet_fit_scan_band_m": [min(band), max(band)],
        "fillet_free_circle_check": fcheck,
        "inside_half_width_m": o.get("d_half_inside_m"),
        "centre": {"utm13n_nad83": o["fillet_centre_utm"], "lonlat_wgs84": to_wgs(ctx, *o["fillet_centre_utm"])},
        "arms": o.get("arms"),
        "notes": [free_note] if free_note else [],
    }
    rec["notes"].append(text["junction_notes"][cid].format(ribbon_R=o["R_fillet"] + 3.35))
    rec["radius_if_ribbon_6p7m_inside_edge_on_fillet_m"] = round(o["R_fillet"] + 3.35, 2)
    lab = ["%s %s  st %.0f  turn %.0f deg (OSM)" % (cid, ctx.names.get(cid, ""), fc["apex_st_m"], abs(fc["measured"]["turn_deg"])),
           "inside kerb return R %.1f m;  lap centreline R %.1f m +-%.1f (medium)" % (o["R_fillet"], o.get("R_centreline", float("nan")), rec["uncertainty_m"]),
           "cyan: inside pavement edges + fitted kerb-return arc   blue: outside edges",
           "yellow: arm centre lines   red: OSM lap line (datum-shifted)   magenta: lap-centreline arc"]
    rec["overlay"] = "overlays/%s.png" % cid
    return rec, lab


def unmeasured(ctx, cid):
    t = ctx.spec["text"]["unmeasured"][cid]
    return {"id": cid, "name": ctx.names.get(cid), "dossier": ctx.spec["text"]["corners"][cid]["dossier"],
            "apex_lap_st_m": ctx.plan[cid]["apex_st_m"],
            "radius_m": None, "confidence": "none", "uncertainty_m": None,
            "radius_method": t["radius_method"], "notes": list(t["notes"]), "overlay": None}


def predicted_datum_shift(lat, lon, h, t):
    """ITRF2008 (~WGS84 G1762) minus NAD83(2011), metres E, N, at (lat, lon, h) and epoch t: the NGS
    14-parameter transformation (Pearson & Snay 2013), as the aerial pass computed it."""
    a = 6378137.0
    f = 1 / 298.257222101
    e2 = f * (2 - f)

    def ecef(lat, lon, h):
        la, lo = math.radians(lat), math.radians(lon)
        N = a / math.sqrt(1 - e2 * math.sin(la) ** 2)
        return ((N + h) * math.cos(la) * math.cos(lo), (N + h) * math.cos(la) * math.sin(lo), (N * (1 - e2) + h) * math.sin(la))

    def geod(X, Y, Z):
        lon = math.atan2(Y, X)
        p = math.hypot(X, Y)
        lat = math.atan2(Z, p * (1 - e2))
        for _ in range(10):
            N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
            h = p / math.cos(lat) - N
            lat = math.atan2(Z, p * (1 - e2 * N / (N + h)))
        return math.degrees(lat), math.degrees(lon), h

    def itrf08_to_nad83(X, Y, Z, t):
        dt = t - 1997.0
        mas = math.pi / 180 / 3600 / 1000
        Tx = 0.99343 + 0.00079 * dt
        Ty = -1.90331 - 0.00060 * dt
        Tz = -0.52655 - 0.00134 * dt
        ex = (25.91467 + 0.06667 * dt) * mas
        ey = (9.42645 - 0.75744 * dt) * mas
        ez = (11.59935 - 0.05133 * dt) * mas
        s = (1.71504 - 0.10201 * dt) * 1e-9
        Xn = Tx + (1 + s) * X + ez * Y - ey * Z
        Yn = Ty - ez * X + (1 + s) * Y + ex * Z
        Zn = Tz + ey * X - ex * Y + (1 + s) * Z
        return Xn, Yn, Zn
    X, Y, Z = ecef(lat, lon, h)
    la2, lo2, h2 = geod(*itrf08_to_nad83(X, Y, Z, t))
    dN = (la2 - lat) * 111000.0
    dE = (lo2 - lon) * 111000.0 * math.cos(math.radians(lat))
    return -dE, -dN


def assemble(ctx, windows_meta, reg, corners, edge_stats, width_res, legs, xosm, xres, corr, overlays):
    """The whole aerial_measurements.json as an ordered dict (``windows_meta`` in cache-file order)."""
    text = ctx.spec["text"]
    V = ctx.V

    def wgs(E, N):
        lon, lat = geo.from_utm(E + V[0], N + V[1])
        return [round(lon, 7), round(lat, 7)]
    purpose = {w["id"]: w["purpose"] for w in ctx.spec["windows"]}
    windows = []
    rasters = {}
    for m in windows_meta:
        wid = m["id"]
        xmin, ymin, xmax, ymax = m["bbox_utm13n"]
        for c in m["catalog"]:
            if c.get("Name"):
                rasters[c["Name"]] = {k: c.get(k) for k in ("Name", "Year", "State", "resolution_value", "projection_zone", "datum", "vendor")}
                rasters[c["Name"]]["acquisition_date_utc"] = (time.strftime("%Y-%m-%d", time.gmtime(c["acquisition_date"] / 1000))
                                                              if c.get("acquisition_date") else None)
        windows.append({"id": wid, "purpose": purpose[wid], "bbox_utm13n_nad83": m["bbox_utm13n"],
                        "bbox_lonlat_nad83": [round(v, 7) for v in geo.from_utm(xmin, ymin)] + [round(v, 7) for v in geo.from_utm(xmax, ymax)],
                        "size_px": m["size"], "px_m": m["px_m"], "rasters": [c.get("Name") for c in m["catalog"] if c.get("Name")],
                        "fetched_utc": m["fetched_utc"],
                        "request_rgb": m["files"]["rgb"]["url"], "bytes_rgb": m["files"]["rgb"]["bytes"], "bytes_cir": m["files"]["cir"]["bytes"]})
    g = reg["global"]
    dc = ctx.spec["datum_check"]
    pe, pn = predicted_datum_shift(dc["lat"], dc["lon"], dc["h_m"], dc["epoch"])
    s_text = text["source"]
    source = {
        "imagery": s_text["imagery"], "service": s_text["service"], "year_note": s_text["year_note"],
        "rasters": sorted(rasters.values(), key=lambda r: r["Name"]),
        "licence": s_text["licence"], "request": s_text["request"],
        "cache": ("raw windows (PNG + per-window JSON with bbox, URL, raster names) are in the window cache only: %s; "
                  "nothing raw is in the repo" % str(ctx.cache).replace("\\", "/")),
        "tls": s_text["tls"], "georeferencing": s_text["georeferencing"],
        "registration_vs_osm": {
            "method": text["registration_method"],
            "osm_minus_imagery_EN_m": g["v_osm_minus_paint_EN_m"], "magnitude_m": g["magnitude_m"],
            "bearing_deg": g["bearing_deg"], "points": g["n_points"], "windows": g["n_windows"],
            "residual_rms_m": g["resid_rms_m"], "residual_p90_abs_m": g["resid_p90_abs_m"],
            "explained_by_datum": text["registration_explained_by_datum"].format(
                pred_e=pe, pred_n=pn, pred_mag=math.hypot(pe, pn), epoch=dc["epoch"],
                meas_e=g["v_osm_minus_paint_EN_m"][0], meas_n=g["v_osm_minus_paint_EN_m"][1], rms=g["resid_rms_m"]),
            "per_window_median_cross_offset_m": {k: v.get("median_cross_offset_m") for k, v in reg["per_window"].items() if v.get("n", 0) >= 6},
            "how_coordinates_here_are_given": text["registration_how_coordinates"],
        },
        "local_frame_note": text["local_frame_note"],
    }
    corner_list = []
    for cid in [c["id"] for c in ctx.spec["corner_plan"]["corners"]]:
        r = dict(corners[cid])
        if cid in edge_stats:
            r["edge_appearance_core"] = edge_stats[cid]
        corner_list.append(r)
    segs = ctx.spec["segments"]
    notes_by_st = text["station_notes"]
    stations = []
    for k in sorted(width_res, key=lambda s: int(s[1:])):
        w = width_res[k]
        st = w["station_m"]
        seg = segs[0]["name"] if st < segs[0]["below_m"] else (segs[1]["name"] if st <= segs[1]["up_to_m"] else segs[2]["name"])
        usable = (w.get("edge_line_width") is not None and w["edge_line_width"]["n"] >= 10) or \
                 (w.get("pavement_width") is not None and w["pavement_width"]["n"] >= 10)
        note = None
        if w["shadow_frac"] >= 0.6 and not usable:
            note = "tree shadow over the road; not measurable"
        elif w["shadow_frac"] >= 0.5:
            note = "partly in tree shadow; fewer profiles"
        if str(int(st)) in notes_by_st:
            note = notes_by_st[str(int(st))]
        stations.append({"station_m": st, "segment": seg, "lonlat_wgs84": wgs(*w["utm"]), "window": k,
                         "edge_line_width_m": w.get("edge_line_width"), "pavement_width_m": w.get("pavement_width"),
                         "lane_right_m": w.get("lane_right_of_travel"), "lane_left_m": w.get("lane_left_of_travel"),
                         "beyond_edge_line_right_m": w.get("beyond_edge_line_right"), "beyond_edge_line_left_m": w.get("beyond_edge_line_left"),
                         "profiles": w["profiles"], "shadow_fraction": w["shadow_frac"], "usable": usable, "note": note})

    def agg(sel, key):
        v = [s[key]["median"] for s in stations
             if sel(s) and s.get(key) and s[key]["n"] >= 10 and s["note"] is None
             or (sel(s) and s.get(key) and s[key]["n"] >= 10 and s["note"] and "partly" in s["note"])]
        v = sorted(v)
        return None if not v else {"median_of_stations": round(stt.median(v), 2), "min": v[0], "max": v[-1], "stations": len(v)}
    cr = ctx.spec["summary_ranges"]

    def climb(s):
        return cr["climb_m"][0] <= s["station_m"] <= cr["climb_m"][1]

    def para(s):
        return s["station_m"] >= cr["paradise_from_m"]
    legv = sorted(x["edge_line_width_median"] for c in legs.values() for x in c.values())
    widths = {
        "method": text["widths"]["method"],
        "two_widths_why": text["widths"]["two_widths_why"],
        "summary": {
            "lariat_climb_edge_lines": agg(climb, "edge_line_width_m"),
            "lariat_climb_pavement": agg(climb, "pavement_width_m"),
            "lariat_hairpin_legs_edge_lines": {"median": round(stt.median(legv), 2), "min": legv[0], "max": legv[-1], "legs": len(legv)},
            "paradise_rd_edge_lines": agg(para, "edge_line_width_m"),
            "paradise_rd_pavement": agg(para, "pavement_width_m"),
            "versus_dossier": text["widths_versus_dossier"],
        },
        "stations": stations,
        "hairpin_legs": legs,
        "corner_apexes": {cid: corners[cid].get("apex_cross_section") for cid in ctx.spec["hairpins"]},
        "junction_arms": {cid: corners[cid].get("arms") for cid in ctx.spec["junctions"]},
    }
    c470 = {
        "how": text["c470_how"],
        "osm_source": text["c470_osm_source"],
        "osm_crossings": xosm,
        "crossings": [xres[x["id"]] for x in ctx.spec["crossings"]],
        "lap_corridor_paved_width_m_near_deck": corr,
        "per_crossing_notes": text["c470_per_crossing_notes"],
    }
    out = {
        "schema": text["schema"],
        "ledger": text["ledger"],
        "source": source,
        "methods": {
            "hairpins_C1_C10": text["methods"]["hairpins_C1_C10"],
            "junctions_C12_C13": text["methods"]["junctions_C12_C13"],
            "thresholds_invented": dict(THRESHOLDS, _doc=text["thresholds_doc"]),
        },
        "windows": windows,
        "corners": corner_list,
        "corner_summary": [{"id": c["id"], "name": c.get("name"), "radius_m": c.get("radius_m"), "uncertainty_m": c.get("uncertainty_m"),
                            "confidence": c.get("confidence"), "method": (c.get("radius_method") or "").split(":")[0],
                            "turn_deg_aerial": c.get("turn_deg_aerial"), "osm_fitter_radius_m": (c.get("fitter_osm") or {}).get("radius_fit_m")}
                           for c in corner_list],
        "widths": widths,
        "edges": text["edges"],
        "c470": c470,
        "files": {"overlays": sorted(overlays), "overlay_dir": "overlays/", "provenance": "PROVENANCE.md"},
    }
    return out

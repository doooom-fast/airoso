"""Phase 3: the 3DEP profiles, the width table and the station frame, from this run's downloads and readings.

  profile_3dep.west.json  every 25 m along each clockwise leg (the shape of routes__profile_3dep.json)
  measure.west.json       5 m node-to-node profiles of both carriageways and the midline, junction heights, max
                          grades on a 20 m chord (tools/author_expansion.max_grade) and over 50 / 100 m windows, the
                          plan's height and grade facts beside them (the shape of revise__measure.json)
  mouth_grades.json       each mouth's own way: height at the node, grade over its first 15 m and 40 m
  widths_eye.west.csv     the eye table (the columns of aerial__widths_eye.csv, plus this run's re-read columns)
  stations.west.json      the midline skeleton every 2.5 m with y_3dep, the curb offsets and the median from the
                          re-read (linear between readings, flat beyond the first / last): the frame
                          tools/aerial_paint_north.py measures the paint in; NOT Step 1's expansion.west.json

    python -I p3x_profiles.py <airoso> <legs-dir> <3dep-dir> <crops.json> <eye_reread.json> <out-dir>
"""
import csv
import io
import json
import math
import sys
from pathlib import Path

NAMES = {"E": "P3-WAR", "F": "P3-ZION", "G": "P3-MG"}
A4 = {  # EXPANSION-PHASE3-PLAN rev 2 A4: curb to curb (m) at station s, read by eye 2026-10-14 (NAIP 2022-04-25)
    "E": [(150, 28.0), (300, 29.5), (450, 29.7), (600, 22.0)],
    "F": [(150 * k, w) for k, w in zip(range(1, 11), (12.0, 12.0, 13.5, 11.5, 12.0, 13.0, 11.5, 11.2, 15.1, 14.8))],
    "G": [(150 * k, w) for k, w in zip(range(1, 16), (32.1, 31.0, 27.5, 26.3, 27.3, 30.5, 27.0, 29.0, 31.3, 27.5,
                                                       32.7, 30.1, 31.9, 33.5, 33.7))],
}
PLAN = {  # EXPANSION-PHASE3-PLAN rev 2 A6 / V2 and DOSSIER-EXPANSION-WEST 3: the facts the profiles are checked against
    "J2_m": 103.9, "waring_crest_m": 106.6, "waring_crest_s": 400, "J6_m": 99.7, "J7_m": 33.8,
    "mg_sag_m": 28.7, "mg_sag_s": [300, 400], "J3_m": 33.4, "zion_max_grade_pct": {"50m": 10.1, "100m": 9.8, "20m": 10.2},
    "zion_steep_s": [570, 660], "waring_max_grade_pct": [3.2, 3.4], "mg_max_grade_pct": [4.1, 4.2]}


def window_grade(s, z, w):
    best = (0.0, None)
    j = 0
    for i in range(len(s)):
        while j < len(s) and s[j] - s[i] < w - 1e-6:
            j += 1
        if j >= len(s):
            break
        g = (z[j] - z[i]) / (s[j] - s[i])
        if abs(g) > abs(best[0]):
            best = (g, (s[i] + s[j]) / 2)
    return [round(100 * best[0], 1), None if best[1] is None else round(best[1], 1)]


def main():
    airoso, legs_d, dep_d, crops_p, eye_p, out = (Path(a) for a in sys.argv[1:7])
    sys.path.insert(0, str(airoso / "tools"))
    import author_expansion as ae
    out.mkdir(parents=True, exist_ok=True)
    pts = json.loads((dep_d / "points.json").read_text())["points"]
    smp = json.loads((dep_d / "samples.json").read_text())
    vals = smp["values"]
    an = json.loads((legs_d / "routes_analysis.west.json").read_text())
    sk = json.loads((legs_d / "skeleton.west.json").read_text())
    mo = json.loads((legs_d / "mouths.west.raw.json").read_text())
    crops = {c["key"]: c for c in json.loads(crops_p.read_text())["stations"]}
    eye = {r["key"]: r for r in json.loads(eye_p.read_text())["rows"]}
    elev0 = sk["frame"]["origin"]["elev_m"]
    series = {}
    for p, v in zip(pts, vals):
        series.setdefault(p[0], []).append((p[1], v, p[4], p[5]))
    if any(v is None for v in vals):
        raise SystemExit("3DEP gave no value at some points")

    # ------------------------------------------------------------------ measure
    prof = {}
    for lid in "EFG":
        for sense in ("cw", "acw", "mid"):
            sr = series[f"{lid}.{sense}"]
            s = [a[0] for a in sr]
            z = [a[1] for a in sr]
            imax, imin = max(range(len(z)), key=lambda i: z[i]), min(range(len(z)), key=lambda i: z[i])
            g20 = ae.max_grade(s, z, 20.0)
            f100 = [k for k in range(len(s)) if s[k] <= 100.0]
            l100 = [k for k in range(len(s)) if s[k] >= s[-1] - 100.0]
            prof[f"{NAMES[lid]}.{sense}"] = {
                "length_m": round(s[-1], 1), "z_start": round(z[0], 2), "z_end": round(z[-1], 2),
                "z_max": [round(z[imax], 2), s[imax], [round(sr[imax][2], 6), round(sr[imax][3], 6)]],
                "z_min": [round(z[imin], 2), s[imin], [round(sr[imin][2], 6), round(sr[imin][3], 6)]],
                "max_grade_20m_chord_pct": [round(100 * g20[0], 1), None if g20[1] is None else round(g20[1], 1)],
                "max_grade_50m_pct": window_grade(s, z, 50.0), "max_grade_100m_pct": window_grade(s, z, 100.0),
                "max_grade_first100_pct": window_grade([s[k] for k in f100], [z[k] for k in f100], 20.0)[0],
                "max_grade_last100_pct": window_grade([s[k] for k in l100], [z[k] for k in l100], 20.0)[0],
                "first5": [round(v, 2) for v in z[:5]], "last5": [round(v, 2) for v in z[-5:]],
                "profile_5m": [[a[0], round(a[1], 2)] for a in sr]}
    jn = {}
    for tag, sr in series.items():
        if tag.startswith("node."):
            _n, j, which = tag.split(".")
            jn.setdefault(j, {})[which] = round(sr[0][1], 2)
    mid = {lid: prof[f"{NAMES[lid]}.mid"] for lid in "EFG"}

    def at_s(pr, lo, hi, fn):
        rows = [r for r in pr["profile_5m"] if lo <= r[0] <= hi]
        return fn(rows, key=lambda r: r[1]) if rows else None
    crest = at_s(mid["E"], 0, mid["E"]["length_m"], max)
    sag = at_s(mid["G"], 100, 800, min)
    zion = prof["P3-ZION.cw"]
    zion_win = [r for r in zion["profile_5m"] if 500 <= r[0] <= 720]
    checks = {
        "J2": {"plan_m": PLAN["J2_m"], "3dep_cw_node_m": jn["J2"]["cw"], "3dep_acw_node_m": jn["J2"]["acw"]},
        "J6": {"plan_m": PLAN["J6_m"], "3dep_cw_node_m": jn["J6"]["cw"], "3dep_acw_node_m": jn["J6"]["acw"]},
        "J7": {"plan_m": PLAN["J7_m"], "3dep_cw_node_m": jn["J7"]["cw"], "3dep_acw_node_m": jn["J7"]["acw"]},
        "J3": {"plan_m": PLAN["J3_m"], "3dep_cw_node_m": jn["J3"]["cw"], "3dep_acw_node_m": jn["J3"]["acw"]},
        "waring_crest": {"plan_m_s": [PLAN["waring_crest_m"], PLAN["waring_crest_s"]], "midline_m_s": [crest[1], crest[0]]},
        "mission_gorge_sag": {"plan_m_s": [PLAN["mg_sag_m"], PLAN["mg_sag_s"]], "midline_m_s": [sag[1], sag[0]],
                              "searched_s": [100, 800]},
        "zion_max_grade": {"plan_pct": PLAN["zion_max_grade_pct"], "plan_s": PLAN["zion_steep_s"],
                           "cw_20m_chord": zion["max_grade_20m_chord_pct"], "cw_50m": zion["max_grade_50m_pct"],
                           "cw_100m": zion["max_grade_100m_pct"],
                           "cw_s500_720_5m": zion_win},
        "waring_max_grade": {"plan_pct": PLAN["waring_max_grade_pct"],
                             "cw_20m": prof["P3-WAR.cw"]["max_grade_20m_chord_pct"],
                             "acw_20m": prof["P3-WAR.acw"]["max_grade_20m_chord_pct"],
                             "cw_100m": prof["P3-WAR.cw"]["max_grade_100m_pct"]},
        "mg_max_grade": {"plan_pct": PLAN["mg_max_grade_pct"], "cw_20m": prof["P3-MG.cw"]["max_grade_20m_chord_pct"],
                         "acw_20m": prof["P3-MG.acw"]["max_grade_20m_chord_pct"],
                         "cw_100m": prof["P3-MG.cw"]["max_grade_100m_pct"]},
        "grade_cap_11pct_binds": any(abs(p["max_grade_20m_chord_pct"][0]) > 11.0 for p in prof.values())}
    measure = {"_doc": "USGS 3DEP 1 m bare earth along the Phase 3 legs, every 5 m (p3x_3dep.py points, p3x_profiles.py); "
                       "stations s = metres along each line from its own start (cw / mid: the clockwise station; acw: "
                       "from the anticlockwise start). z = metres NAVD88.",
               "source": smp["source"], "fetched_utc": smp["fetched_utc"], "requests": smp["requests"],
               "bytes": smp["bytes"], "profiles": prof, "junction_3dep_m": jn, "checks_vs_plan": checks}
    (out / "measure.west.json").write_text(json.dumps(measure, indent=1))

    # ------------------------------------------------------------------ profile every 25 m (cw), Phase 2's shape
    p25 = {}
    for lid in "EFG":
        pr = prof[f"{NAMES[lid]}.cw"]
        rows = [r for r in pr["profile_5m"] if abs(r[0] / 25.0 - round(r[0] / 25.0)) < 1e-6] + [pr["profile_5m"][-1]]
        rows = [[r[0], round(r[1], 1)] for r in rows]
        s = [r[0] for r in pr["profile_5m"]]
        z = [r[1] for r in pr["profile_5m"]]
        g100 = window_grade(s, z, 100.0)
        p25[NAMES[lid]] = {"road": next(l["road"] for l in an["cw"] if l["leg"] == lid), "sense": "cw",
                           "z_start": round(z[0], 1), "z_end": round(z[-1], 1), "z_min": round(min(z), 1),
                           "z_max": round(max(z), 1), "net_grade_pct": round(100 * (z[-1] - z[0]) / s[-1], 2),
                           "steepest_100m_pct": g100[0], "steepest_at_m": g100[1], "profile": rows}
    (out / "profile_3dep.west.json").write_text(json.dumps(p25, indent=1))

    # ------------------------------------------------------------------ mouth grades
    mg = {}
    for lid, recs in mo["mouths"].items():
        for k, r in enumerate(recs):
            sr = series.get(f"mouth.{lid}.{k}")
            if not sr:
                continue
            z0 = sr[0][1]
            g15 = next(((a[1] - z0) / a[0] for a in sr if abs(a[0] - 15.0) < 1e-6), None)
            g40 = (sr[-1][1] - z0) / sr[-1][0] if sr[-1][0] > 0 else None
            mg[f"{lid}.{k}"] = {"z_node_m": round(z0, 2), "grade_15m_pct": None if g15 is None else round(100 * g15, 1),
                                "grade_to_m": sr[-1][0], "grade_far_pct": None if g40 is None else round(100 * g40, 1),
                                "profile": [[a[0], round(a[1], 2)] for a in sr]}
    (out / "mouth_grades.json").write_text(json.dumps(mg, indent=1))

    # ------------------------------------------------------------------ the eye table
    cols = ["label", "lat", "lon", "eye_curb_to_curb_m", "eye_conf_m", "median_m", "median_kind", "cw_left_m",
            "cw_right_m", "auto_total_m", "lo_p", "hi_p", "note", "s_cw_m", "eye_source", "a4_m", "reread_total_m",
            "reread_left_m", "reread_right_m", "reread_median_hi_m", "reread_median_lo_m", "reread_conf_m"]
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(cols)
    readings = {}
    for key, c in crops.items():
        e = eye.get(key)
        if not e:
            continue
        lid = key[0] if key[0] in "EFG" else None
        a4 = None
        if lid and "_st" in key:
            st = int(key.split("_st")[1])
            a4 = dict(A4[lid]).get(st)
        L, R, med = e["L"], e["R"], e["med"]
        tot = round(L - R, 1) if (L is not None and R is not None) else None
        mw = round(med[0] - med[1], 1) if med else 0.0
        if med and L is not None and R is not None:
            cl_, cr_ = round(L - med[0], 1), round(med[1] - R, 1)
        else:
            cl_, cr_ = None, None
        main_w = a4 if a4 is not None else tot
        src = ("A4 (EXPANSION-PHASE3-PLAN rev 2, eye 2026-10-14); median, split and reread_* this run" if a4 is not None
               else "this run's re-read" if tot is not None else "not readable")
        conf = 1.5 if a4 is not None else e["conf"]
        lab = c["label"].replace(" WIDE", "")
        wr.writerow([lab, c["lat"], c["lon"], main_w, conf, mw if med else 0.0, e["kind"], cl_ if cl_ is not None else "",
                     cr_ if cr_ is not None else "", c["auto_total_m"], c["auto_right_m"], c["auto_left_m"], e["note"],
                     c["s"], src, a4 if a4 is not None else "", tot if tot is not None else "",
                     L if L is not None else "", R if R is not None else "", med[0] if med else "",
                     med[1] if med else "", e["conf"]])
        if lid and ("_st" in key or key.endswith("_p1arm")) and L is not None and R is not None:
            readings.setdefault(lid, []).append({"s": c["s"], "L": L, "R": R, "med": med, "kind": e["kind"],
                                                 "label": lab})
    (out / "widths_eye.west.csv").write_text(buf.getvalue())

    # ------------------------------------------------------------------ the station frame (paint) with y_3dep
    pieces = []
    for lid, pc in sk["pieces"].items():
        rd = sorted(readings[lid], key=lambda r: r["s"])
        msr = series[f"{lid}.mid"]
        ms = [a[0] for a in msr]
        mz = [a[1] for a in msr]

        def interp(sv, key):
            if sv <= rd[0]["s"]:
                return rd[0][key]
            if sv >= rd[-1]["s"]:
                return rd[-1][key]
            for a, b in zip(rd, rd[1:]):
                if a["s"] <= sv <= b["s"]:
                    t = (sv - a["s"]) / ((b["s"] - a["s"]) or 1.0)
                    return a[key] + (b[key] - a[key]) * t

        for r in rd:
            r["mh"] = r["med"][0] if r["med"] else 0.0
            r["ml"] = r["med"][1] if r["med"] else 0.0
        rows = []
        for st in pc["stations"]:
            s, x, z, sep = st[0], st[1], st[2], st[3]
            k = max(0, min(len(ms) - 2, int(s // 5.0)))
            t = (s - ms[k]) / ((ms[k + 1] - ms[k]) or 1.0)
            zz = mz[k] + (mz[k + 1] - mz[k]) * max(0.0, min(1.0, t))
            near = min(rd, key=lambda r: abs(r["s"] - s))
            mh, ml = interp(s, "mh"), interp(s, "ml")
            mt = ae.median_type(near["kind"]) if near["med"] else ("line" if lid == "F" else "none")
            mw = round(mh - ml, 2) if near["med"] else 0.0
            rows.append([s, x, z, round(zz - elev0, 3), round(interp(s, "L"), 3), round(interp(s, "R"), 3), mw,
                         round((mh + ml) / 2, 3) if near["med"] else 0.0, mt, sep, near["label"]])
        pieces.append({"id": NAMES[lid], "name": NAMES[lid].lower(), "road": next(l["road"] for l in an["cw"]
                                                                               if l["leg"] == lid),
                       "from": an["meta"]["legs"][lid]["from"], "to": an["meta"]["legs"][lid]["to"],
                       "length_m": pc["length_m"], "spacing_m": 2.5, "n": len(rows),
                       "cuts": {"start": {"s": 0.0, "kind": "node"}, "end": {"s": pc["length_m"], "kind": "node"}},
                       "columns": ["s", "x", "z", "y_3dep", "left_m", "right_m", "median_w_m", "median_off_m",
                                   "median_type", "osm_sep_m", "width_from"],
                       "stations": rows})
    doc = {"version": 1, "_doc": "The Phase 3 station frame: the midline skeleton every 2.5 m (author_expansion "
                                 "build_midline + gauss_smooth on the fresh OSM legs), y_3dep = 3DEP midline height - "
                                 "origin.elev_m, the curb offsets and median from this run's eye re-read (linear between "
                                 "readings). It is the frame aerial__paint_west.json is measured in. NOT Step 1's "
                                 "expansion.west.json: no pads, no stubs, no welds, no smoothing of the profile.",
           "frame": sk["frame"], "stations_frame": "s = metres along the clockwise OSM leg from its start junction node; "
                                                   "offsets + = left of the clockwise direction", "pieces": pieces}
    (out / "stations.west.json").write_text(json.dumps(doc, indent=0))
    print(json.dumps(checks, indent=0)[:3000])


if __name__ == "__main__":
    main()

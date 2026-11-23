"""Phase 3 pipeline lens: the mouth geometry (the shape of source/expansion/pipeline__mouth_geometry.json).

At J2 and J3 (Phase 1's pads, built and installed): the arm conversions. Phase 1 closed Waring south-west (S2, at J2)
and Mission Gorge west (S3, at J3) with a 15 m stub and a K-rail; Phase 3's pieces start / end there. Read here
against the repo's own Phase 1 records (data/expansion.north.json pads and stubs, data/pads.built.json, data/
lights.local.json): where the new midline crosses the arm's straight cut, its angle to the arm's axis and its offset
from the cut's middle, the widths (Phase 1's declared arm, this run's re-read and A4's nearest station), the heights
(the pad's 3DEP datum against this run's 3DEP at the cut), the built barrier's distance, and the installed lamps
nearest the new piece's first 100 m.

At J6 and J7 (new corners): every arm, from the fresh OSM (bearing, class, lanes, one-way), this run's arm re-read,
the angles between consecutive arms, the signals within 40 m and the 3DEP node heights. The curb-return radii are not
measured here (owed).

    python -I p3x_mouthgeo.py <airoso> <legs-dir> <prof-dir> <osm.expansion.json> <out.json>
"""
import csv
import json
import math
import sys
from pathlib import Path

NAMES = {"E": "P3-WAR", "F": "P3-ZION", "G": "P3-MG"}
CONV = [("J2", "S2", "E", "start"), ("J3", "S3", "G", "end")]


def main():
    airoso, legs_d, prof_d, osm_p, out_p = (Path(a) for a in sys.argv[1:6])
    sys.path.insert(0, str(airoso / "tools"))
    import author_expansion as ae
    T = airoso / "tracks/san-diego-lake-murray/data"
    X = json.loads((T / "expansion.north.json").read_text())
    PB = json.loads((T / "pads.built.json").read_text())
    LL = json.loads((T / "lights.local.json").read_text())
    st = json.loads((prof_d / "stations.west.json").read_text())
    ms = json.loads((prof_d / "measure.west.json").read_text())
    an = json.loads((legs_d / "routes_analysis.west.json").read_text())
    mo = json.loads((legs_d / "mouths.west.raw.json").read_text())
    eye = list(csv.DictReader((prof_d / "widths_eye.west.csv").open()))
    osm = json.loads(osm_p.read_text())
    ntags = {int(k): v for k, v in osm.get("node_tags", {}).items()}
    nodes = {int(k): v for k, v in osm["nodes"].items()}
    fr = ae.Frame(X["frame"]["origin"])
    elev0 = X["frame"]["origin"]["elev_m"]
    pieces = {p["id"]: p for p in st["pieces"]}
    pads = {p["id"]: p for p in X["pads"]}
    built = {p["id"]: p for p in PB["pads"]}
    stubs = {s["id"]: s for s in X["stubs"]}
    lamps = LL.get("lamp_bases_xz") or []
    out = {"_doc": __doc__.split("\n\n")[0], "origin": X["frame"]["origin"],
           "phase1_records": {"expansion.north.json": X.get("written_utc"), "pads.built.json": "repo at the branch base"},
           "conversions": [], "new_junctions": {}}
    for j, sid, lid, end in CONV:
        pid = NAMES[lid]
        pc = pieces[pid]
        cols = pc["columns"]
        rows = [dict(zip(cols, r)) for r in pc["stations"]]
        P = [(r["x"], r["z"]) for r in rows]
        arm = next(a for a in pads[j]["arms"] if a.get("stub") == sid)
        cut = arm["cut_line_xz"]
        rec ={"junction": j, "stub": sid, "piece": pid, "piece_end": end, "arm": {k: arm[k] for k in arm
                                                                                  if k != "cut_line_xz"},
               "cut_line_xz": cut, "stub_pavement_xz": stubs[sid]["pavement_xz"], "stub_length_m": stubs[sid]["length_m"],
               "stub_width_src": stubs[sid]["src"]}
        d, s_hit, lat, seg = ae.project(((cut[0][0] + cut[1][0]) / 2, (cut[0][1] + cut[1][1]) / 2), P)
        a, b = P[max(0, seg)], P[min(len(P) - 1, seg + 1)]
        hd = (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360
        if end == "end":
            hd = (hd + 180) % 360                       # the piece's direction out of the pad
        ang = ((hd - arm["bearing_out_deg"] + 180) % 360) - 180
        r0 = min(rows, key=lambda r: abs(r["s"] - s_hit))
        z3 = next((p for p in [ms["profiles"][f"{pid}.mid"]["profile_5m"]]), None)
        zc = min(z3, key=lambda q: abs(q[0] - s_hit))
        bp = next((s for s in built[j].get("stubs", []) if s.get("stub") == sid), None)
        bar = bp["barrier"]["path_xz"] if bp else None
        bar_mid = bar[len(bar) // 2] if bar else None
        near_l = sorted(((math.dist(q, P[k]), i, rows[k]["s"]) for i, q in enumerate(lamps)
                         for k in range(0, len(P), 4)
                         if (rows[k]["s"] <= 100.0 if end == "start" else rows[k]["s"] >= pc["length_m"] - 100.0)),
                        key=lambda t: t[0])
        seen, nl = set(), []
        for dd, i, s in near_l:
            if i in seen:
                continue
            seen.add(i)
            nl.append({"lamp": i, "base_xz": lamps[i], "d_m": round(dd, 1), "nearest_s": s})
            if len(nl) == 3:
                break
        e_s = [r for r in eye if r["label"].startswith(pid + " st")]
        a4_near = min(e_s, key=lambda r: abs(float(r["s_cw_m"]) - s_hit))
        p1 = next((r for r in eye if r["label"].startswith(f"{j} arm") and f"{sid} re-read" in r["label"]), None)
        rec.update({
            "midline_s_at_cut_mid_m": round(s_hit, 2), "midline_off_cut_mid_m": round(d, 2),
            "piece_heading_out_of_pad_deg": round(hd, 1), "angle_vs_arm_axis_deg": round(ang, 1),
            "widths_m": {"phase1_declared": arm["width_m"],
                         "reread_at_phase1_point": (None if not p1 or not p1["reread_total_m"]
                                                    else float(p1["reread_total_m"])),
                         "reread_at_phase1_point_note": p1["note"] if p1 else None,
                         "frame_at_cut_m": round(r0["left_m"] - r0["right_m"], 2),
                         "frame_at_cut_from": f"the station frame at the cut: this run's re-read '{r0['width_from']}' "
                                              f"(held flat from the reading nearest the cut, not read at the cut)",
                         "a4_nearest": {"label": a4_near["label"], "a4_m": float(a4_near["a4_m"]),
                                        "metres_from_cut": round(abs(float(a4_near["s_cw_m"]) - s_hit), 1)}},
            "heights_m": {"pad_z_3dep": pads[j]["z_3dep_m"], "pad_y_3dep": pads[j]["y_3dep_m"],
                          "midline_3dep_at_cut": zc[1], "midline_3dep_minus_pad": round(zc[1] - pads[j]["z_3dep_m"], 2)},
            "built_barrier": None if not bar else {"object": bp["barrier"]["object"], "style": bp["barrier"]["style"],
                                                    "mid_xz": bar_mid,
                                                    "d_from_cut_mid_m": round(math.dist(bar_mid, ((cut[0][0] + cut[1][0]) / 2,
                                                                                                  (cut[0][1] + cut[1][1]) / 2)), 2)},
            "nearest_installed_lamps_first_100m": nl})
        out["conversions"].append(rec)
    # ---------------------------------------------------------------- the new corners
    phase3_ways = set()
    for lg in an["cw"] + an["acw"]:
        phase3_ways |= {w["id"] for w in lg["ways"]}
    sig = [n for n, t in ntags.items() if t.get("highway") == "traffic_signals"]
    for j in ("J6", "J7"):
        cwn, acwn = an["meta"]["junction_nodes_cw_acw"][j]
        pj = fr.xz(*nodes[cwn][:2])
        arms, seen = [], set()
        for lid, recs in mo["mouths"].items():
            for r in recs:
                if r["junction"] != j or r["kind"] != "junction_arm":
                    continue
                key = (r["way"], r["node"], r["next_node"])
                if key in seen:
                    continue
                seen.add(key)
                arms.append({"way": r["way"], "name": r["name"], "highway": r["highway"], "oneway": r["oneway"],
                             "flow": r["flow"], "lanes": r["lanes"], "maxspeed": r["maxspeed"], "node": r["node"],
                             "bearing_deg": r["bearing_deg"], "phase3_route": r["way"] in phase3_ways})
        arms.sort(key=lambda a: a["bearing_deg"])
        eye_arms = [{"label": r["label"], "reread_total_m": r["reread_total_m"], "median_m": r["median_m"],
                     "median_kind": r["median_kind"], "conf_m": r["reread_conf_m"], "note": r["note"]}
                    for r in eye if r["label"].startswith(f"{j} arm")]
        between = []
        for a, b in zip(arms, arms[1:] + arms[:1]):
            between.append({"from_way": a["way"], "to_way": b["way"],
                            "clockwise_angle_deg": round((b["bearing_deg"] - a["bearing_deg"]) % 360, 1)})
        out["new_junctions"][j] = {
            "nodes_cw_acw": [cwn, acwn], "node_lonlat": nodes[cwn][:2], "node_xz": [round(pj[0], 3), round(pj[1], 3)],
            "z_3dep_m": ms["junction_3dep_m"][j], "arms": arms, "angles_between_arms": between, "eye_arms": eye_arms,
            "signals_within_40m": sorted(n for n in sig if math.dist(fr.xz(*nodes[n][:2]), pj) <= 40.0),
            "turns": [t for t in an["junctions"] if t["junction"] == j],
            "curb_return_radii": "owed: not measured (NAIP 0.6 m; Step 1 reads them)"}
    out_p.write_text(json.dumps(out, indent=1))
    for c in out["conversions"]:
        print(c["junction"], c["stub"], "s", c["midline_s_at_cut_mid_m"], "off", c["midline_off_cut_mid_m"], "angle",
              c["angle_vs_arm_axis_deg"], "widths", json.dumps(c["widths_m"]), "dz", c["heights_m"]["midline_3dep_minus_pad"],
              "barrier", c["built_barrier"] and c["built_barrier"]["d_from_cut_mid_m"])
    for j, v in out["new_junctions"].items():
        print(j, [(a["name"], a["bearing_deg"], a["phase3_route"]) for a in v["arms"]], v["signals_within_40m"])


if __name__ == "__main__":
    main()

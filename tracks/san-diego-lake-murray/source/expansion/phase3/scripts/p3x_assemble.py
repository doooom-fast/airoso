"""Assemble the Phase 3 data folder (tracks/san-diego-lake-murray/source/expansion/phase3/) from this run's outputs:
the Phase 2 kinds of file under Phase 2's names, the fresh downloads, last night's reused terrain fetches, the eye
panels, the scripts of record, and provenance.json (what, from, bytes, sha256 per file).

    python -I p3x_assemble.py <job-dir> <round2-job-dir> <out-dir>
"""
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

NAMES = {"E": "P3-WAR", "F": "P3-ZION", "G": "P3-MG"}


try:   # a local helper (not committed) names the home paths and host names to keep out of the folder
    from local_sanitize import FORBID, sanitize
except ImportError:
    FORBID = ()

    def sanitize(text, job, r2):
        return text.replace(str(r2), "<round-2 job>").replace(str(job), "<this job>")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    job, r2, out = (Path(a) for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    L, P, D = job / "out" / "legs", job / "out" / "prof", job / "dl"
    prov = {}

    def put(name, data=None, src=None, what="", frm=""):
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if src is not None:
            shutil.copyfile(src, p)
        elif isinstance(data, (dict, list)):
            p.write_text(json.dumps(data, indent=1) + "\n")
        else:
            p.write_text(data)
        prov[name] = {"what": what, "from": frm, "bytes": p.stat().st_size, "sha256": sha(p)}

    # ---------------------------------------------------------------- routes
    an = json.loads((L / "routes_analysis.west.json").read_text())
    for lg in an["cw"] + an["acw"]:
        lg["leg"] = NAMES[lg["leg"]]
    an["meta"]["legs"] = {NAMES[k]: v for k, v in an["meta"]["legs"].items()}
    dedup = {}
    for lid, xs in an["median_crossings"].items():
        seen, keep = set(), []
        for x in xs:
            if x["way"] in seen:
                continue
            seen.add(x["way"])
            keep.append(x)
        dedup[NAMES[lid]] = keep
    an["median_crossings"] = dedup
    an["summary"] = {k.replace("E_", "P3-WAR_").replace("F_", "P3-ZION_").replace("G_", "P3-MG_"): v
                     for k, v in an["summary"].items()}
    an["summary"]["plan_rev2_cw_acw_m"] = {NAMES[k]: v for k, v in an["summary"]["plan_rev2_cw_acw_m"].items()}
    an["_doc"] = ("Phase 3 routes lens on fresh OSM (scripts/p3x_legs.py): the legs in both directions (cw = the "
                  "plan's clockwise J2 -> J6 -> J7 -> J3, acw = back; Phase 2's file calls them fwd / rev), way lists, "
                  "one-way-aware paths, controls on the path, the turns at J2 / J6 / J7 / J3 over 20 m chords, the "
                  "median crossings. Lengths are in data/centerline.local.json's local frame (the build's frame); the "
                  "plan's lengths run ~0.2 % shorter (another metric), as Phase 2's routes lens against "
                  "data/expansion.north.json.")
    put("routes__routes_analysis.json", an, what="legs, ways, controls, junction turns, median crossings",
        frm="scripts/p3x_legs.py on osm.expansion.json (this folder)")
    gj = json.loads((L / "legs.west.geojson").read_text())
    for f in gj["features"]:
        f["properties"]["leg"] = NAMES[f["properties"]["leg"]]
    put("routes__legs.geojson", json.dumps(gj) + "\n", what="the six legs (3 roads x cw / acw) as GeoJSON, WGS84",
        frm="scripts/p3x_legs.py")
    mo = json.loads((L / "mouths.west.raw.json").read_text())
    mg = json.loads((P / "mouth_grades.json").read_text())
    p3ways = {w["id"] for lg in an["cw"] + an["acw"] for w in lg["ways"]}
    mouths, census = {}, {}
    for lid, recs in mo["mouths"].items():
        pid = NAMES[lid]
        rows = []
        c = {"public": 0, "service": 0, "service_private": 0, "link": 0, "junction_arm_closed": 0,
             "junction_arm_phase3_route": 0, "junction_arm_phase1": 0}
        for k, r in enumerate(recs):
            g = mg.get(f"{lid}.{k}", {})
            r = dict(r)
            r.update({"z_node_m": g.get("z_node_m"), "grade_15m_pct": g.get("grade_15m_pct"),
                      "grade_far_pct": g.get("grade_far_pct"), "grade_far_to_m": g.get("grade_to_m")})
            kind = r["kind"]
            if kind == "junction_arm":
                if r["way"] in p3ways:
                    tr = "phase3_route"
                    c["junction_arm_phase3_route"] += 1
                elif r["junction"] in ("J2", "J3"):
                    tr = "phase1_arm (stays as Phase 1 built it)"
                    c["junction_arm_phase1"] += 1
                else:
                    tr = "junction_arm_stub (plan A1)"
                    c["junction_arm_closed"] += 1
            elif kind == "public":
                tr = "stub (plan A2)"
                c["public"] += 1
            elif kind == "service":
                tr = "curb_cut (plan A2)"
                c["service"] += 1
                if (r.get("access") or "") in ("private", "no"):
                    c["service_private"] += 1
            elif kind == "link":
                tr = "junction_arm_stub (plan A1: the J6 free-right slip)"
                c["link"] += 1
            else:
                tr = "unclassified"
            r["treatment_by_plan"] = tr
            r["station_cw_m"] = r.pop("station_cw_m")
            rows.append(r)
        mouths[pid] = rows
        census[pid] = c
    tot = {k: sum(c[k] for c in census.values()) for k in census["P3-WAR"]}
    plan_c = {"public_side_streets": 30, "junction_arms": 5, "service_curb_cuts": 45, "median_openings": 5,
              "by_road": {"P3-WAR": {"public": 2, "service": 0}, "P3-ZION": {"public": 22, "service": 12},
                          "P3-MG": {"public": 6, "service": 33}}}
    jarm_ways = sorted({(r["junction"], r["name"], r["way"]) for rs in mouths.values() for r in rs
                        if r["treatment_by_plan"].startswith("junction_arm_stub")}, key=str)
    mdoc = {"_doc": "Every side street, driveway and junction-arm mouth along the Phase 3 legs (scripts/p3x_legs.py on the "
                    "fresh OSM), one record per branch leaving either carriageway; station_cw_m on the clockwise leg, "
                    "side L / R of the clockwise direction, leaves_toward / bearing_deg over the branch's first 15 m, "
                    "flow in / out for one-way branches; z_node_m and the grades = 3DEP along the branch's own way "
                    "(scripts/p3x_3dep.py, p3x_profiles.py). treatment_by_plan = EXPANSION-PHASE3-PLAN A1 / A2 applied "
                    "to the OSM class: this is NOT tools/stub_roads.py's declaration (the PC runs `declare`).",
            "mouths": mouths, "median_crossings": dedup, "lengths": an["summary"],
            "census": {"by_road": census, "total": tot, "plan_rev2": plan_c,
                       "junction_arm_stub_ways": [list(x) for x in jarm_ways],
                       "median_crossing_ways": {k: [[x["station_cw_m"], x["way"], x["name"], x["highway"]] for x in v]
                                                for k, v in dedup.items()}}}
    put("routes__mouths.json", mdoc, what="side mouths, junction arms, median crossings, the census against the plan",
        frm="scripts/p3x_legs.py + p3x_3dep.py + p3x_profiles.py")
    put("routes__osm_diff.json", src=L / "osm_diff.west.json",
        what="the fresh OSM against data/osm.expansion.json (2026-10-14) on the six legs and every way within 60 m",
        frm="scripts/p3x_legs.py")
    put("routes__stations.west.json", src=P / "stations.west.json",
        what="the station frame (midline every 2.5 m, y_3dep, re-read curb offsets and medians): the frame the paint "
             "was measured in; NOT Step 1's expansion.west.json", frm="scripts/p3x_legs.py + p3x_profiles.py")
    put("routes__profile_3dep.json", src=P / "profile_3dep.west.json", what="3DEP 1 m every 25 m along each cw leg",
        frm="scripts/p3x_3dep.py + p3x_profiles.py")
    put("revise__measure.json", src=P / "measure.west.json",
        what="3DEP 1 m every 5 m: both carriageways and the midline, junction heights, max grades, the plan's checks",
        frm="scripts/p3x_3dep.py + p3x_profiles.py")
    put("pipeline__mouth_geometry.json", src=job / "out" / "mouth_geometry.west.json",
        what="the J2 / J3 arm conversions against Phase 1's records; the J6 / J7 arms",
        frm="scripts/p3x_mouthgeo.py")
    # ---------------------------------------------------------------- lamps and signals
    ls = json.loads((D / "lamps" / "osm_lamps_signals.json").read_text())
    st = json.loads((P / "stations.west.json").read_text())
    sys.path.insert(0, str(job / "code" / "airoso" / "tools"))
    import author_expansion as ae
    fr = ae.Frame(st["frame"]["origin"])
    lines = {pc["id"]: [(r[1], r[2]) for r in pc["stations"]] for pc in st["pieces"]}
    for el in ls["traffic_signals"] + ls["street_lamps"]:
        p = fr.xz(el["lon"], el["lat"])
        best = None
        for pid, Pl in lines.items():
            d, s, lat, _i = ae.project(p, Pl)
            if best is None or d < best[0]:
                best = (d, pid, s, lat)
        el["near_phase3"] = ({"piece": best[1], "station_cw_m": round(best[2], 1), "offset_m": round(best[3], 1),
                              "d_m": round(best[0], 1)} if best[0] <= 60.0 else None)
    ls["_doc"] = ("OSM highway=street_lamp and highway=traffic_signals nodes around the Phase 3 roads (scripts/"
                  "p3x_fetch_osm.py, the guarded Overpass client); near_phase3 = the nearest piece, its station and "
                  "the offset (+ = left of cw) where within 60 m of the station frame's midline.")
    ls["counts"] = {"street_lamps": len(ls["street_lamps"]), "traffic_signals": len(ls["traffic_signals"]),
                    "signals_within_60m": sum(1 for e in ls["traffic_signals"] if e["near_phase3"])}
    put("pipeline__osm_lamps_signals.json", ls, what="OSM street lamps (none mapped here) and traffic signals",
        frm="scripts/p3x_fetch_osm.py lamps (download) + p3x_assemble.py (near_phase3)")
    # ---------------------------------------------------------------- aerial
    put("aerial__widths_eye.csv", src=P / "widths_eye.west.csv",
        what="curb to curb at the A4 stations and the junction arms: A4's eye width of record where it exists, this "
             "run's re-read (median, split, reread_*) everywhere; the automatic pavement read beside it",
        frm="EXPANSION-PHASE3-PLAN rev 2 A4 + scripts/eye_reread.json (p3x_crops.py panels) + p3x_profiles.py")
    cr = json.loads((job / "out" / "crops4" / "crops.json").read_text())
    er = json.loads((job / "scripts" / "eye_reread.json").read_text())
    put("aerial__widths_reread.json", {"_doc": er["_doc"], "panels": cr["params"], "stations": cr["stations"],
                                       "rows": er["rows"]},
        what="this run's eye re-read with the panel geometry of every station", frm="scripts/p3x_crops.py + eye_reread.json")
    put("aerial__veg_bins.json", src=job / "out" / "veg" / "veg_bins.west.json",
        what="per piece / 250 m / side: [other, canopy, water, scrub] NAIP CIR samples of the 10-40 m band",
        frm="scripts/p3x_veg.py bins (thresholds from aerial__veg_bins.calibration.json)")
    cal = json.loads((job / "out" / "veg" / "calibration.json").read_text())
    put("aerial__veg_bins.calibration.json", cal,
        what="the [invented] NDVI / brightness thresholds, picked on the Phase 2 legs against Phase 2's own bins",
        frm="scripts/p3x_veg.py calibrate")
    pp = job / "out" / "paint_track" / "source" / "expansion" / "aerial__paint_north.json"
    if pp.exists():
        put("aerial__paint_west.json", src=pp,
            what="the centre paint measured off NAIP every 2.5 m (tools/aerial_paint_north.py, unchanged, run on "
                 "routes__stations.west.json; its intermediate_sha256_12 is that file's)",
            frm="tools/aerial_paint_north.py via scripts/p3x_paint.py")
    # ---------------------------------------------------------------- downloads kept in the folder
    put("osm.expansion.json", src=D / "osm" / "osm.expansion.json",
        what="fresh OSM roads + service ways, the exact box and query of data/osm.expansion.json",
        frm="tools/fetch_osm.py --service via scripts/p3x_fetch_osm.py (download)")
    put("buildings.expansion.cache.json", src=D / "buildings" / "buildings.expansion.cache.json",
        what="fresh OSM building footprints, the box of data/buildings.expansion.cache.json (reaches -117.115)",
        frm="tools/fetch_buildings_cache.py via scripts/p3x_fetch_osm.py (download)")
    put("buildings.expansion.cache.json.provenance.json",
        src=D / "buildings" / "buildings.expansion.cache.json.provenance.json",
        what="the buildings fetch's own provenance (server, OSM timestamp, compare with the 2026-10-14 cache)",
        frm="tools/fetch_buildings_cache.py")
    # ---------------------------------------------------------------- terrain reused from the round-2 job
    T = {"terrain/heightfield.88.npy": r2 / "dl_3dep_grid" / "heightfield.npy",
         "terrain/heightfield.88.meta.json": r2 / "dl_3dep_grid" / "heightfield.meta.json",
         "terrain/heightfield.88.grow.proof.json": r2 / "dl_3dep_grid" / "heightfield.grow.proof.json",
         "terrain/p3_tier_samples.json.gz": r2 / "dl_3dep_tiers" / "p3_tier_samples.json.gz",
         "terrain/plan_p3_fetch.report.json": r2 / "p3" / "out" / "plan_p3_fetch.json",
         "terrain/plan_p3_count.report.json": r2 / "p3" / "out" / "plan_p3_count.json",
         "terrain/plan_baseline26.report.json": r2 / "p3" / "out" / "plan_baseline26.json",
         "terrain/remap.proof.json": r2 / "p3" / "out" / "remap.proof.json",
         "terrain/tier_plan_input.expansion.west.planned.json": r2 / "inputs" / "expansion.west.planned.json"}
    for name, src in T.items():
        frm = "round-2 job scripts p3_grow.py / p3_plan.py / p3_remap.py / p3_west.py (scripts/round2/)"
        if src.suffix == ".json":
            raw = src.read_text()
            clean = sanitize(raw, job, r2)
            put(name, clean, what="reused from the 2026-11-22/23 round-2 data job (Step 0.5 / 0.6)",
                frm=frm + ("; home paths and host name replaced, original sha256 " + sha(src) if clean != raw else ""))
        else:
            put(name, src=src, what="reused from the 2026-11-22/23 round-2 data job (Step 0.5 / 0.6)", frm=frm)
    # ---------------------------------------------------------------- the eye panels (evidence for the re-read)
    from PIL import Image
    cdir, wdir = job / "out" / "crops4", job / "out" / "crops_wide"
    keys = [c["key"] for c in cr["stations"]]
    wide = {"J6_arm_041", "J7_arm_189", "J7_arm_013"}
    groups = {"P3-WAR": [k for k in keys if k.startswith("E_")], "P3-ZION": [k for k in keys if k.startswith("F_")],
              "P3-MG": [k for k in keys if k.startswith("G_")],
              "arms": [k for k in keys if "_arm_" in k]}
    for gname, ks in groups.items():
        for part in range(0, len(ks), 4):
            ims = [Image.open((wdir / f"{k}_wide.png") if k in wide else (cdir / f"{k}.png")).convert("RGB")
                   for k in ks[part:part + 4]]
            cw_ = max(i.width for i in ims)
            ch_ = max(i.height for i in ims)
            sheet = Image.new("RGB", (2 * cw_ + 10, 2 * ch_ + 10), (255, 255, 255))
            for q, im in enumerate(ims):
                sheet.paste(im, ((q % 2) * (cw_ + 10), (q // 2) * (ch_ + 10)))
            name = f"aerial__eye_panels/{gname}_{part // 4 + 1}.jpg"
            (out / "aerial__eye_panels").mkdir(exist_ok=True)
            sheet.save(out / name, quality=85)
            prov[name] = {"what": "eye-reading panels: " + ", ".join(ks[part:part + 4]),
                          "from": "scripts/p3x_crops.py (NAIP 2022-04-25 0.6 m; 0.1 m a pixel drawn, 1 m ticks)",
                          "bytes": (out / name).stat().st_size, "sha256": sha(out / name)}
    # ---------------------------------------------------------------- scripts of record
    for f in sorted((job / "scripts").glob("p3x_*.py")) + [job / "scripts" / "eye_reread.json",
                                                           job / "scripts" / "p3_net_r2.py"]:
        raw = f.read_text()
        clean = sanitize(raw, job, r2)
        put(f"scripts/{f.name}", clean, what="this run's script / reading of record" +
            (" (round-2 p3_net.py, imported by p3x_3dep.py)" if f.name == "p3_net_r2.py" else ""),
            frm="this run" + ("; host name replaced, original sha256 " + sha(f) if clean != raw else ""))
    for f in ("p3_net.py", "p3_plan.py", "p3_grow.py", "p3_remap.py", "p3_west.py", "p3_config.py", "p3_naip.py"):
        raw = (r2 / "scripts" / f).read_text()
        clean = sanitize(raw, job, r2)
        put(f"scripts/round2/{f}", clean, what="the round-2 job's script behind terrain/ and the NAIP tiles this run read",
            frm="round-2 job" + ("; host name / home paths replaced, original sha256 " + sha(r2 / "scripts" / f)
                                 if clean != raw else ""))
    (out / "provenance.json").write_text(json.dumps({"_doc": "every file in this folder: what it is, what made it, its "
                                                             "bytes and sha256 (README.md has the story)",
                                                     "files": prov}, indent=1) + "\n")
    bad = []
    for name in prov:
        p = out / name
        if p.suffix in (".json", ".py", ".csv", ".geojson", ".md", ".txt"):
            t = p.read_text(errors="replace")
            bad += [(name, w) for w in FORBID if w in t]
    print("forbidden tokens:", bad or "none")
    print(len(prov), "files;", sum(v["bytes"] for v in prov.values()), "bytes")
    print(json.dumps(census), json.dumps(tot))


if __name__ == "__main__":
    main()

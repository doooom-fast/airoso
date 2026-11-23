"""Milford round 2 (ledger 0102): the config edits, applied on top of round 1's track.config.json (0.1.14), each one named.

    python -I tracks/milford-road-course-lm/source/round2/edit_config_0102.py tracks/milford-road-course-lm/track.config.json

1. GM's 2.9 mi loop (Kevin 2026-11-22, calls page: "Build the 2.9 mi loop"): lm_intake.source_data "data_gm"
   (tracks/milford-road-course/source/trace/gm_loop/README.md), its measured surface and its edge evidence.
2. The station-keyed entries re-read on the GM line, by position (an old station's point -> the nearest point of the GM
   intake line): before the splice unchanged, after it -174.6..-175.5 m; the agree span s 1,228-1,237 lay on the dropped
   2022 loop (13.7-16.1 m off the GM line) and goes.
3. Off the lap with the 2022 loop: T3 (t3_s1000_apron_back, 62.6-77.5 m off the new lane edge), run-off pads R0998
   (37.6-71.0 m off), L1175 and L0883 (now under the new lane, up to 5.4 / 6.6 m inside it; L0883 was the inner branch's
   own concrete, drawn as a pad while it was not on the lap).
4. The banked inner turn's measured cross-section (route.densify.section).
5. The shoulder (Kevin 2026-11-22, calls page: "Reshape the shoulder"): terrain.shoulder_grade.
"""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
raw = p.read_text(encoding="utf-8")
d = json.loads(raw)
if d.get("version") != "0.1.14":
    raise SystemExit(f"expected round 1's 0.1.14, found {d.get('version')}")
d["version"] = "0.1.15"
d["_version_doc"] = ("0.1.15 (ledger 0102, Milford round 2; Kevin's answers of 2026-11-22): GM's 2.9 mi loop (the inner "
                     "hairpin in place of the 2022 loop), the banked inner turn's measured cross-section, the shoulder graded "
                     "on the lidar. " + d.get("_version_doc", ""))
li = d["lm_intake"]

# 1. the GM loop
li["source_data"] = "data_gm"
li["_source_data_doc"] = (
    "ledger 0102 (Milford round 2; Kevin 2026-11-22: \"Build the 2.9 mi loop\"): GM's loop, OSM's older ways (72577419 + "
    "72577413, 2010), in place of ours, which rode 1030539760 (2022), the 534 m southern hairpin loop, where GM's takes "
    "72577413's 370 m inner turn (a concrete branch). tracks/milford-road-course/data_gm/ = the committed line with that "
    "piece replaced (splice_gm_loop.py: every other station bit for bit; the new piece off NAIP 2022 + the 2025 Oakland "
    "ortho; lap 4,900.7 -> 4,726.0 m on the source line). README: tracks/milford-road-course/source/trace/gm_loop/")
li["measured_surface"]["file"] = "source/surface/road_surface_gm.fit.json"
li["_measured_surface_doc"] = (li.get("_measured_surface_doc", "") + " | ledger 0102: the G10's read of the GM line "
                               "(board asset 7da6810244a541615b95aced5f6e5290), fitted the same way")
li["edge_fit"]["evidence"] = "source/edges/edge_evidence_gm.json"
for e in li["edge_retrace"]:
    e["evidence"] = "source/edges/edge_evidence_gm.json"

# 2. the station-keyed spans on the GM line
li["edge_retrace"][0]["spans"] = [[4355.5, 150.0]]
li["edge_retrace"][1]["spans"] = [[431.2, 458.8], [2380.8, 2424.6], [2462.9, 2499.6], [3292.5, 3321.0],
                                  [3734.4, 3744.3], [3938.6, 3969.7], [4049.3, 4074.1]]
li["edge_retrace"][1]["rails"] = [r for r in li["edge_retrace"][1]["rails"] if r != "t3_s1000_apron_back"]
li["_edge_retrace_0102_doc"] = (
    "ledger 0102: the spans re-read on the GM line by position (0.1.13's intake line -> the GM intake line): 4,530 -> "
    "4,355.5; 431 / 459 -> 431.2 / 458.8; 2,556-2,600 -> 2,380.8-2,424.6; 2,638-2,675 -> 2,462.9-2,499.6; 3,468-3,496 -> "
    "3,292.5-3,321.0; 3,909-3,919 -> 3,734.4-3,744.3; 4,113-4,144 -> 3,938.6-3,969.7; 4,224-4,249 -> 4,049.3-4,074.1 (each "
    "within 1.01 m of its old point); 1,228-1,237 lay on the dropped 2022 loop and is gone, with T3 from the rails")

# 3. off the lap
b = d["scenery"]["bespoke"]
b["rails"] = [r for r in b["rails"] if r["key"] != "t3_s1000_apron_back"]
b["pads"] = [q for q in b["pads"] if q["key"] not in ("runoff_R0998", "runoff_L1175", "runoff_L0883")]
b["_off_lap_0102_doc"] = (
    "ledger 0102: off the lap with the 2022 loop: T3 (t3_s1000_apron_back, 62.6-77.5 m off the GM lane edge), run-off pads "
    "R0998 (37.6-71.0 m off), L1175 and L0883 (under the new lane, up to 5.4 / 6.6 m inside it; L0883 was the inner "
    "branch's concrete, drawn as a pad while it was off the lap)")

# 4. the banked inner turn
d["route"]["densify"]["section"] = {
    "file": "source/surface/road_section_gm.json", "spans": [[870.0, 1030.0]], "col_m": 1.0, "taper_m": 15.0,
    "objects": ["CURB", "MARKINGS", "YLINE"],
    "_doc": ("ledger 0102: GM's inner turn is a banked turn whose cross-section curves (the G10's read and the 1 m grid, "
             "all on pavement in the 2025 ortho: s 920 +3.50 m at u = -8, 45-55 % at the outer edge, the inside 10-15 %); "
             "the fit's plane misses it by over 1 m at both edges. The rows over the spans (the section product's own s, "
             "the GM line) take its measured profile: columns every col_m [invented], taper_m [invented]")}

# 5. the shoulder
d["terrain"]["shoulder_grade"] = {
    "npz": "source/lidar/milford_lidar_1m.npz", "lidar_shift_m": [-0.375, 0.938],
    "from_m": 2.0, "full_m": 15.0, "to_m": 20.0, "fall_max": 0.1667, "rise_max": 0.5, "max_fill_m": 1.0,
    "keep_patches": ["culvert_4349_w"],
    "_doc": ("ledger 0102 (Kevin 2026-11-22: \"Reshape the shoulder\"): 0.1.13's 32 far ledges are, every 3 m, 1,491 "
             "drops on ~1.2 km of edge, 1,382 where the lidar is flatter (the built ground a median 0.58 m under it: the "
             "prep's shelf / feather meeting the corridor ramp's draft TERRAIN). tools/shoulder_grade_blend.py grades the "
             "ground 2-15 m off the drivable edge outward on the lidar (registered: lidar_shift_m, the measured surface's), "
             "falling no faster than fall_max (1V:6H, AASHTO's preferred foreslope [invented here]) nor rising faster than "
             "rise_max (1V:2H [invented]), no fill deeper than max_fill_m (1 m [invented]: a deeper real drop stays real), "
             "the culvert's headwall patch kept; blended back to the prepped ground by to_m")}

out = json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")
p.write_text(out, encoding="utf-8", newline="\n")
print(f"[0102] {p}: 0.1.14 -> 0.1.15; rails {len(b['rails'])}, pads {len(b['pads'])}")

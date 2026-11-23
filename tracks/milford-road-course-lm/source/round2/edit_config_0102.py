"""Milford round 2 (ledger 0102): the config edits, applied on top of round 1's track.config.json (0.1.14), each one named.

    python -I tracks/milford-road-course-lm/source/round2/edit_config_0102.py tracks/milford-road-course-lm/track.config.json

1. GM's 2.9 mi loop (Kevin 2026-11-22, calls page: "Build the 2.9 mi loop"): lm_intake.source_data "data_gm"
   (tracks/milford-road-course/source/trace/gm_loop/README.md), its measured surface and its edge evidence.
2. The station-keyed entries re-read on the GM line, by position (an old station's point -> the nearest point of the GM
   intake line): before the splice unchanged, after it -174.6..-175.5 m; the agree span s 1,228-1,237 lay on the dropped
   2022 loop (13.7-16.1 m off the GM line) and goes.
3. Off the lap with the 2022 loop: T3 (t3_s1000_apron_back, 62.6-77.5 m off the new lane edge). The run-off pads are
   re-outlined on the GM line by their own tool afterwards (source/runoff/scripts/runoff_pads.py --write: "re-run it after
   the line or the widths move"), not edited here.
4. The banked inner turn's measured cross-section (route.densify.section), and the ground under it cut by the road's folds
   (route.seat_edges_section); drive_test's daylight probe hung from the road's own edge height on that bank
   (drive_test.daylight_edge_ref, the second rehearsal's 69 readings).
5. The shoulder (Kevin 2026-11-22, calls page: "Reshape the shoulder"): terrain.shoulder_grade.

    python -I tracks/milford-road-course-lm/source/round2/edit_config_0102.py --docs tracks/milford-road-course-lm/track.config.json

--docs (after the re-plans; source/round2/apply_0102.sh runs every step in order): the numbers the GM lap's re-plans measured,
written into the docs of the keys round 1 (0.1.14, ledger 0100) and round 2 both touch: race_start (the painted line's station,
the grid and the pits on the GM lap's swept line, tools/circuit_dummies_blend.py's own plan), the pads, the trunk colliders,
the verge trees.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DOCS = "--docs" in sys.argv
p = Path([a for a in sys.argv[1:] if not a.startswith("--")][0])
raw = p.read_text(encoding="utf-8")
d = json.loads(raw)


def docs():
    """ledger 0102 --docs: the GM lap's re-planned numbers into the docs of the keys rounds 1 and 2 both touch"""
    sys.path.insert(0, str(ROOT))
    from scripts.geometry import circuit_start as cs
    mf = p.parent
    loc = json.loads((mf / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pl = cs.plan(d["race_start"], loc)
    if pl["problems"]:
        raise SystemExit(f"[0102] race_start on the GM lap: {pl['problems']}")
    st = sorted(v["station_m"] for k, v in pl["nodes"].items() if k.startswith("AC_START_"))
    pt = sorted(v["station_m"] for k, v in pl["nodes"].items() if k.startswith("AC_PIT_"))
    d["race_start"]["_gm_loop_0102_doc"] = (
        f"ledger 0102: the line, grid and pits are declared by the MEASURED paint (lon / lat) and patterns, so the build re-reads "
        f"them on its own lap. On the GM lap's swept line (source/round2/predict_lines_0102.py; lap {pl['lap_m']:.2f} m) the "
        f"painted line projects to s {pl['line_station_m']:.2f} (0.1.14: s 4,639.86 on 4,898.25 m), the grid's {len(st)} slots "
        f"s {st[0]:.2f}-{st[-1]:.2f}, the pits' {len(pt)} s {pt[0]:.2f}-{pt[-1]:.2f}, AC_TIME_1 / _2 at s "
        f"{pl['sectors_m'][0]:.2f} / {pl['sectors_m'][1]:.2f}: all on the front straight, the splice (s ~768-1,045) far off")
    rec = json.loads((mf / "source" / "runoff" / "runoff_pads.json").read_text(encoding="utf-8"))
    kept = [x["key"] for x in rec["blobs"] if x["kept"]]
    keys = [q["key"] for q in d["scenery"]["bespoke"]["pads"]]
    if keys != ["ride_pad"] + kept:
        raise SystemExit("[0102] the config's pads are not runoff_pads.py's: run it with --write first")
    d["scenery"]["bespoke"]["_pads_0102_doc"] = (
        f"ledger 0102: the strip pads re-outlined on the GM intake line by source/runoff/scripts/runoff_pads.py --write (its "
        f"own rule, unchanged: re-run after the line moves): {len(kept)} (0.1.14: 19). Keys name side + station, so the 12 "
        f"after the splice carry the GM line's stations (L1530 -> L1355 ... L4775 -> L4601), each re-sampled on its 4 m rows "
        f"from the lane edge + LIP_M; L0883 (the inner branch's concrete, now the lane), R0998 and L1175 (the 2022 loop) go; "
        f"R0880 and R1008 are new: the 2022 loop's grey pavement beside the GM inner turn (NAIP blue / red 0.937 / 0.931, "
        f"748 / 1,296 m2). pads_shade smooth and pads_shade_crease_deg 10 (ledger 0100) are this block's keys, so every pad, "
        f"the new two included, keeps them")
    tr = json.loads((mf / "source" / "vegetation" / "trunks.json").read_text(encoding="utf-8"))
    tk = d["scenery"]["bespoke"]["trunks"]
    tk["_gm_loop_0102_doc"] = (
        f"ledger 0102: re-selected on the GM lap's swept line by veg_trunks_reach.py (unchanged rule): the reach stays "
        f"{tr['reach_m']:.0f} m (g4_infield_esses' median standoff 19.07 m), {len(tr['points'])} colliders (0.1.14's file: 261 "
        f"on 0.1.13's line)")
    vv = json.loads((mf / "source" / "vegetation" / "naip_verge.json").read_text(encoding="utf-8"))
    d["scenery"]["treefx"]["planted"]["_verge_0102_doc"] = (
        f"ledger 0102: the verge trees re-planted on the GM lap's swept line by veg_naip_verge.py (unchanged rules): "
        f"{len(vv['trees'])} (0.1.14: 883), left out {vv['left_out']}; keys are KEY0 + rank, so the trees after a new one take "
        f"new keys (TreeFX's model and angle draw)")


if DOCS:
    if d.get("version") != "0.1.15":
        raise SystemExit(f"--docs: expected 0.1.15, found {d.get('version')}")
    docs()
    out = json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")
    p.write_text(out, encoding="utf-8", newline="\n")
    print(f"[0102] {p}: the GM lap's numbers in the docs")
    sys.exit(0)
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
b["_off_lap_0102_doc"] = (
    "ledger 0102: off the lap with the 2022 loop: T3 (t3_s1000_apron_back, 62.6-77.5 m off the GM lane edge; round 1's 0.2 m "
    "move of its start, ledger 0100 item 1, goes with it)")

# 4. the banked inner turn
d["route"]["densify"]["section"] = {
    "file": "source/surface/road_section_gm.json", "spans": [[870.0, 1030.0]], "col_m": 1.0, "taper_m": 15.0,
    "objects": ["CURB", "MARKINGS", "YLINE"],
    "_doc": ("ledger 0102: GM's inner turn is a banked turn whose cross-section curves (the G10's read and the 1 m grid, "
             "all on pavement in the 2025 ortho: s 920 +3.50 m at u = -8, 45-55 % at the outer edge, the inside 10-15 %); "
             "the fit's plane misses it by over 1 m at both edges. The rows over the spans (the section product's own s, "
             "the GM line) take its measured profile: columns every col_m [invented], taper_m [invented]")}
# 4b. the ground under that bowl (0.1.15's first rehearsal, milford_0115_reh: drive_test's soft_top at s 947; 61 lane points
#     of grass up to 2.1 cm over the road on s 925-962, faces across the columns' folds)
d["route"]["seat_edges_section"] = True
d["route"]["_seat_edges_section_doc"] = (
    "ledger 0102: the first rehearsal of 0.1.15 (milford_0115_reh, 2026-11-23) read the grass OVER the lane on the bowl: "
    "every TERRAIN vertex under it at the deck - 0.020 (the prep's pin), but a grass face is flat and the road folds at each "
    "of densify's ~1 m columns (s 953: -47 / -41 / -22 / -7 % at u -2.9 / -1.9 / -0.9), so 0.85 m faces across 16-19 % folds "
    "stood up to 2.1 cm over it (61 points, s 925-962). tools/seat_edges_blend.py (tools/seat_edges_section.py) cuts every "
    "face under the road on the section's stretch by the road's own fold under it to <= 1 cm of chord (seat_edges' CHORD "
    "rule, half the prep's 2 cm clearance); nothing moves; self-checked")
# 4c. drive_test's daylight probe on that bank (0.1.15's second rehearsal, milford_0115b_reh: 69 daylight gaps, s 912-980,
#     left, every one with kerb or grass 0.03 m under to 0.30 m over the road's own edge; the rehearsal before read the same 69)
d.setdefault("drive_test", {})["daylight_edge_ref"] = True
d["drive_test"]["_daylight_edge_ref_doc"] = (
    "ledger 0102: the second rehearsal of 0.1.15 (milford_0115b_reh, 2026-11-23) read 69 daylight gaps, every one at s "
    "912-980 on the left, 0.8 m past the edge of the bowl's banked outer side. None is a hole: the built left edge stands "
    "2.59-3.68 m over the centre deck (the measured bank, section 4) and the kerb or grass there 0.03 m under to 0.30 m over "
    "that edge, above the probe's window (7.5 m under to 2.5 m over the centre deck). scripts/geometry/drive_test.py hangs the "
    "same window from the road's own height at each edge (the highest 1ROAD face 0.15 m inside it [invented]): 69 -> 0, no "
    "new gap in 9,448 probes; on 0.1.14 0 -> 0 in 9,798. It moves where the probe looks, not its limit (0)")

# 5a. the committed 1 m grid's registration to the road's frame (the measured surface's: frame = lidar + shift), read by
#     tools/lidar_ground_patch.py and tools/shoulder_grade_blend.py; the culvert's patch polygon was drawn on the
#     unshifted lidar (its headwall's line), so it moves with it. The corridor patch is the lap's box: unchanged
SHIFT = [-0.375, 0.938]
t = d["terrain"]
t["lidar_shift_m"] = SHIFT
t["_lidar_shift_doc"] = ("ledger 0102: the committed grid sits (-0.375, +0.938) m off the frame the road is built in "
                         "(tools/measured_surface.py's registration_lidar_shift_m; with it the grid meets the G10's paths "
                         "to p50 1.9 / p90 7.3 cm, without 6.9 / 25.9). Across the corridor's 9-45 m band it moves the "
                         "ground p50 0.05 / p90 0.14 / p99 0.29 m, the culvert's headwall up to 2.2 m. culvert_4349_w's "
                         "polygon, drawn on the unshifted lidar, moved by the same")
for q in t["lidar_patches"]:
    if q["id"] == "culvert_4349_w":
        q["polygon"] = [[round(x + SHIFT[0], 3), round(z + SHIFT[1], 3)] for x, z in q["polygon"]]

# 5. the shoulder
d["terrain"]["shoulder_grade"] = {
    "npz": "source/lidar/milford_lidar_1m.npz",
    "from_m": 2.0, "full_m": 15.0, "to_m": 20.0, "fall_max": 0.1667, "rise_max": 0.5, "max_fill_m": 1.0,
    "keep_patches": ["culvert_4349_w"],
    "_doc": ("ledger 0102 (Kevin 2026-11-22: \"Reshape the shoulder\"): 0.1.13's 32 far ledges are, every 3 m, 1,491 "
             "drops on ~1.2 km of edge, 1,382 where the lidar is flatter (the built ground a median 0.58 m under it: the "
             "prep's shelf / feather meeting the corridor ramp's draft TERRAIN). tools/shoulder_grade_blend.py grades the "
             "ground 2-15 m off the drivable edge outward on the lidar (registered: terrain.lidar_shift_m), "
             "falling no faster than fall_max (1V:6H, AASHTO's preferred foreslope [invented here]) nor rising faster than "
             "rise_max (1V:2H [invented]), no fill deeper than max_fill_m (1 m [invented]: a deeper real drop stays real), "
             "the culvert's headwall patch kept; blended back to the prepped ground by to_m")}

# (the road wear's line needs nothing: road_wear.lines names a recorded source/road_wear/fast_lane.full.ai that has never
#  existed, so every build has drawn the bake's own model line, minimum curvature inside the built edges, and the GM
#  loop's comes with the built road)

out = json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")
p.write_text(out, encoding="utf-8", newline="\n")
print(f"[0102] {p}: 0.1.14 -> 0.1.15; rails {len(b['rails'])} (the pads: runoff_pads.py --write next)")

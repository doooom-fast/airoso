"""Milford round 3 (ledger 0103): the config edit, applied on top of round 2's track.config.json (0.1.15).

    python -I tracks/milford-road-course-lm/source/round3/edit_config_0103.py tracks/milford-road-course-lm/track.config.json

1. The side lines' bulges, the whole lap (Kevin 2026-11-24: "Not vertical waves, horizontal at the edges" / "Long smooth
   curves get weird blooms" / "Look at the side lines", to the Mac; then, here: "Look for primarily bulges during
   otherwise smooth curves and straights" / "Dreaded slop, a human would never do it"): lm_intake.width_design
   (tools/edge_design.py), every width bulge the measured edge does not carry taken out, the bowl held.
2. The report's block (tools/edge_bulges.py): its measured edges and the bowl it counts apart.
(3e79e619's lm_intake.width_hold on the two longest curves is superseded by 1 and no longer named: width_design takes
those two bulges out with the rest.)
"""
import json
import sys
from pathlib import Path

p = Path([a for a in sys.argv[1:] if not a.startswith("--")][0])
raw = p.read_text(encoding="utf-8")
d = json.loads(raw)
if d.get("version") != "0.1.15":
    raise SystemExit(f"expected round 2's 0.1.15, found {d.get('version')}")
d["version"] = "0.1.16"
d["_version_doc"] = ("0.1.16 (ledger 0103, Milford round 3; Kevin 2026-11-24: \"Long smooth curves get weird blooms\"): every "
                     "bulge in the width that the measured edge does not carry taken out, the whole lap (ledger 0103). " + d.get("_version_doc", ""))
li = d["lm_intake"]

HELD = [[750.0, 1045.0]]      # the banked turn: route.densify.section's spans + taper (s 855-1,045) and the G10's s 750-1,015
LIDAR = "source/surface/road_profile_lidar_g10/milford_edges_curves.lidar.g10.json"
EVID = "source/edges/edge_evidence_gm.json"

# 1. the width laid out as a person would, the whole lap
li.pop("width_hold", None)
li["width_design"] = {
    "evidence": EVID, "lidar_edges": LIDAR, "held": HELD,
    "_doc": (
        "ledger 0103 (Kevin 2026-11-24: \"Not vertical waves, horizontal at the edges\" / \"Long smooth curves get weird "
        "blooms\" / \"Look at the side lines\" / \"Look for primarily bulges during otherwise smooth curves and straights\" "
        "/ \"Dreaded slop, a human would never do it because it's more work, both irl and digitally\"): on 0.1.15 every "
        "bloom is the road edge, the paint and the edge strip swelling together on both sides by the width's own swell (the "
        "ribbon is +-w/2 about the line), carried from data_gm's widths (the 0.6.0 tracer's NAIP-mask scans). "
        "tools/edge_design.py lays the width out (every swell and pinch narrower than 200 m taken out, steps and tapers "
        "kept [invented]), judges each excursion of >= 10 cm over 15-200 m [invented] against the measured width (the "
        "G10's 2017-lidar edges on its six stretches, edge_evidence_gm.json's 5 m bins elsewhere: real when it makes the "
        "same excursion, >= half the built one and >= 2 standard errors [invented]) and replaces every one it does not "
        "carry by a cubic taper on the layout's slope, rounded over 10 m [invented]. Held: the banked turn (held, s "
        "750-1,045) and every edge_retrace span and taper (re-traced to the measured edge after this). At intake: 10 "
        "bulges taken out (2.12 -> 0.21 /km the measured edge does not carry; the one left, s 1,342-1,420, 0.15 m), 6 "
        "real kept, the edges moved max 0.78 m, 1,360 of 6,304 points; the line not moved. On the swept line "
        "(tools/edge_bulges.py --line, the retraced stretches and the bowl counted apart): width bulges ours 11 -> 2 "
        "(2.33 -> 0.42 /km), left edge 9 -> 4, right 5 -> 1. Without the key the intake writes main's line byte for byte")}

# 2. the report's block
d["edge_bulges"] = {
    "evidence": EVID, "lidar_edges": LIDAR, "skip": HELD,
    "_doc": ("ledger 0103: tools/edge_bulges.py's measured edges (the G10's lidar read where it covers, the evidence "
             "elsewhere) and the stretch it counts apart (the banked turn, built from its own section); the edge_retrace "
             "spans and tapers are counted apart by the tool itself")}

out = json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")
p.write_text(out, encoding="utf-8", newline="\n")
print(f"[0103] {p}: 0.1.15 -> 0.1.16; width_design (held {HELD}) + edge_bulges")

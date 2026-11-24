"""Milford round 3 (ledger 0103): the config edit, applied on top of round 2's track.config.json (0.1.15).

    python -I tracks/milford-road-course-lm/source/round3/edit_config_0103.py tracks/milford-road-course-lm/track.config.json

1. The side lines' blooms on the lap's two longest smooth curves (Kevin 2026-11-24, to the Mac: "Not vertical waves,
   horizontal at the edges" / "Long smooth curves get weird blooms" / "Look at the side lines"): lm_intake.width_hold on
   the GM line's s 1,114-1,270 and 1,557-1,857 (tools/width_hold.py).
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
d["_version_doc"] = ("0.1.16 (ledger 0103, Milford round 3; Kevin 2026-11-24: \"Long smooth curves get weird blooms\"): the "
                     "trace's width held straight on the lap's two longest smooth curves, where it swelled and the measured "
                     "edges do not. " + d.get("_version_doc", ""))
li = d["lm_intake"]

# 1. the width held on the two long curves
li["width_hold"] = {
    "spans": [[1114.0, 1270.0], [1557.0, 1857.0]],
    "evidence": "source/edges/edge_evidence_gm.json",
    "blend_m": 15.0,
    "_doc": (
        "ledger 0103 (Kevin 2026-11-24, to the Mac: \"Not vertical waves, horizontal at the edges\" / \"Long smooth curves "
        "get weird blooms\" / \"Look at the side lines\"): on 0.1.15's track.obj every bloom on a long smooth curve is the "
        "road edge, the paint and the edge strip swelling together on both sides by the width's own swell (the ribbon is "
        "+-w/2 about the line), carried bit for bit from data_gm's widths (the 0.6.0 tracer's NAIP-mask scans); edge_fit "
        "cuts 1-2 row spikes and width_smooth's 10 m Gaussian cannot reach a 50-150 m swell. On these two spans (R 92 / "
        "93 m, the lap's two longest smooth curves) the trace swells 0.9-1.4 m while the measured edges hold their width: "
        "edge_evidence_gm.json's two sides (5 m bins) and the G10's re-read of the 2017 lidar's intensity step "
        "(milford_edges_curves.lidar.g10.json, branch claude/mf-road-profile-lidar-20261124 19018b12: real 10.4-10.8 / "
        "10.6-10.7 m, steady; 0.1.15 built +0.63 / +0.76 m median over it). tools/width_hold.py holds each span to the "
        "straight fit through the measured width (bins further than 2.5 MADs + 2 cm dropped [invented]), blended over "
        "blend_m [invented]: 10.49-10.80 and 10.88-11.12 m; built minus measured width median 0.437 -> 0.018 and 0.302 "
        "-> 0.042 m, RMS about it 0.518 -> 0.379 and 0.628 -> 0.342 m; the bloom +0.60 / +0.57 m a side -> 0; the edges "
        "move p50 0.23 / 0.12, max 0.69 / 0.60 m. A span it fits worse than the trace, or measured on < 60 % of its bins, "
        "is refused. The line is not moved. Owed, not here: s 580-660 (a third swell, built +0.96 m over a steady 10.5-11.0 "
        "m, but the trace before it is too wide as well, so a hold there pinches both lines ~0.5 m in 15 m at s 565-580); "
        "the banked turn (s 750-1,015: built 1.2-1.8 m UNDER the real at s 875-940, the 16 m cap)")}

out = json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")
p.write_text(out, encoding="utf-8", newline="\n")
print(f"[0103] {p}: 0.1.15 -> 0.1.16; width_hold spans {li['width_hold']['spans']}")

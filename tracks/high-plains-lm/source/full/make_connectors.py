"""The Full layout's north loop as the port's own connector (ledger 0097 round 3; Kevin 2026-11-22: "Yes, add the Full
layout"): north_loop.json (measure_north.py: To Hell On A Bobsled + Ladder To Heaven, fork to merge, its line, widths and
heights) in the shape lm_intake.connectors_file carries (tools/lm_engine_intake.py -> data/connectors.local.json).

    python -I make_connectors.py        (stdlib only; writes connectors.full.json beside itself)

  points / widths   north_loop.json's own, unchanged (measured where the photos read both edges; "carried" elsewhere: the
                    measured median 11.2 m, marked per row in north_loop.json and [invented] in the config's doc)
  paint             the mainline's own edge lines (route.lane_dividers false, divided_double false: scripts-v021
                    ribbon.lane_markings draws solid white edge lines EDGE_INSET_M inside each edge, LINE_W_M wide, and no
                    centre line), written as the authored-paint shape (ribbon.paint_markings) so the assembler draws no
                    yellow centre line on a circuit (a plain connector gets lane_markings(center_yellow=True))
Nothing else is decided here: the cuts (the FORK pad's box edge, the West lap's edge at the merge) and the merge's weld are the
chain's (tools/trim_connectors.py, tools/weld_mouths_blend.py), the lap race.laps.full's (scripts/geometry/race_lap.py).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDGE_INSET_M = 0.55      # scripts-v021 ribbon.lane_markings edge_inset (the mainline's edge lines)
LINE_W_M = 0.12          # scripts-v021 ribbon.lane_markings line_w


def build(nl: dict) -> dict:
    c = nl["connectors"][0]
    w = [float(v) for v in c["widths_m"]]
    rows = nl.get("rows") or []
    kinds = [r.get("width") for r in rows] if len(rows) == len(w) else []
    conn = {"name": c["name"], "kind": "connector", "points_xyz_m": c["points_xyz_m"], "widths_m": w, "joined": [],
            "paint": {"lines": [{"color": "white", "w": LINE_W_M, "off": [round(v / 2 - EDGE_INSET_M, 3) for v in w]},
                                {"color": "white", "w": LINE_W_M, "off": [round(-(v / 2 - EDGE_INSET_M), 3) for v in w]}]},
            "source": c["source"] + "; paint: the mainline's edge lines (make_connectors.py)"}
    if kinds:
        conn["width_kind"] = kinds
    return {"_doc": "ledger 0097 round 3: the Full layout's north loop (To Hell On A Bobsled + Ladder To Heaven) as the port's "
                    "own connector, read by lm_intake.connectors_file (make_connectors.py from north_loop.json)",
            "summary": nl.get("summary"), "connectors": [conn]}


if __name__ == "__main__":
    nl = json.loads((HERE / "north_loop.json").read_text(encoding="utf-8"))
    out = build(nl)
    (HERE / "connectors.full.json").write_text(json.dumps(out, indent=0) + "\n", encoding="utf-8")
    s = out["summary"] or {}
    print(f"[full] {out['connectors'][0]['name']}: {len(out['connectors'][0]['points_xyz_m'])} points, "
          f"{s.get('length_m')} m, measured {s.get('measured_m')} m / carried {s.get('carried_m')} m")

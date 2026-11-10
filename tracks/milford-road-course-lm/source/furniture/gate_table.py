"""gate_table.py <ws-a> <ws-b> ...: the gate rows of each workshop side by side (ledger 0082)"""
import json, os, re, sys
WS = sys.argv[1:]
def J(ws, f):
    p = os.path.join(ws, "data", f)
    return json.load(open(p)) if os.path.exists(p) else {}
DT = ["soft_top_in_lane", "severe_steps", "kinks_per_km", "vertex_bumps", "fold_bumps", "obstruction_stations", "floating_furniture",
      "undrivable_corners", "daylight_gaps", "off_pavement_stations", "apron_steps", "barrier_stations", "barrier_missing"]
rows = []
for k in DT:
    rows.append(("drive_test " + k, [J(w, "drive_test.full.json").get(k) for w in WS]))
for w in WS:
    pass
def excursions(w):
    d = J(w, "drive_test.full.json")
    return d.get("excursion_drops", d.get("excursion_drops_gated")), d.get("far_flare_ledges", d.get("flare_ledges"))
rows.append(("drive_test excursion drops / far ledges", [excursions(w) for w in WS]))
AU = ["A_supports_in_road", "B_terrain_poke", "C_junction_crossings", "D_wall_on_road", "E_wall_floating", "worst_float_m",
      "F_curb_not_flush", "I_sidewalk_isolating", "K_kerb_in_carriageway", "J_terrain_span", "wall_verts"]
for k in AU:
    rows.append(("audit " + k, [J(w, "audit.json").get(k) for w in WS]))
for w in WS:
    pass
rows.append(("kn5_ground_check", [J(w, "kn5_ground_check.full.json") for w in WS]))
rows.append(("house_seat", [{k: v for k, v in J(w, "house_seat_check.json").items() if not isinstance(v, (list, dict))} for w in WS]))
er = [J(w, "edge_report.json") for w in WS]
rows.append(("edge_report at_1m", [e.get("summary", e).get("at_1m") if isinstance(e.get("summary", e), dict) else None for e in er]))
for name, vals in rows:
    print(f"{name:45s} " + " | ".join(str(v) for v in vals))
for w in WS:
    log = open(w + ".log").read()
    print(os.path.basename(w), [l for l in log.splitlines() if l.startswith(("✓", "✗", "SHIP", "exit", "GATES"))])
    for f in sorted(os.listdir(os.path.join(w, "build"))):
        if f.endswith(".kn5"):
            print("   ", f, os.path.getsize(os.path.join(w, "build", f)), "B")

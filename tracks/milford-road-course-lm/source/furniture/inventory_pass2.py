"""Furniture pass 2 (ledger 0082): add each item's lidar reading to inventory.json ("lidar_2017"), from
source/lidar/sumitems.json and f1.json. Idempotent.   python inventory_pass2.py <airoso>"""
import json
import sys
from pathlib import Path

A = Path(sys.argv[1]) / "tracks/milford-road-course-lm/source"
inv = json.loads((A / "furniture/inventory.json").read_text(encoding="utf-8"))
cnt = json.loads((A / "lidar/sumitems.json").read_text(encoding="utf-8"))
f1 = json.loads((A / "lidar/f1.json").read_text(encoding="utf-8"))["summary"]
pieces = json.loads((A / "lidar/f1_entries.json").read_text(encoding="utf-8"))
FLIGHT = "3DEP USGS_LPC_MI_31Co_Oakland_2016_LAS_2019, flown 2017-05-03 (source/lidar/)"
VERDICT = {
    "G1": "no rail: nothing stood on this line in May 2017 (the rail postdates the flight); height NOT measurable, stays [invented]",
    "G2": "as G1", "G3": "as G1", "G4": "as G1",
    "G5": "a scatter of ~10 low returns (0.2-0.9 m) in a 7 m stretch at one end, a shrub's shape, not a 34 m rail: NOT confirmed, not built",
    "G6": "nothing: NOT confirmed, not built",
    "T1": "no tyre stack (it would read as a ~1 m band of returns): nothing stood here in May 2017; identity neither confirmed nor dropped by it (NAIP 2022 still shows the black bar); height stays [invented]",
    "T2": "as T1", "T3": "as T1",
    "T4": "nothing: NOT confirmed, not built",
    "T5": "outside the 45 m read", "T6": "outside the 45 m read (no returns on it)",
    "U1": "the headwall reads 0.6-1.6 m returns (0.56 / m); the deck it belongs to is not modelled: not built",
}
for it in inv["items"]:
    i = it["id"]
    if i == "F1":
        it["lidar_2017"] = {
            "source": FLIGHT, "measured_length_m": f1["fitted_length_m"], "returns_per_m": f1["per_m"],
            "top_m": f1["top_m"], "plan_sd_m": f1["plan_offset_sd_m_of_top_returns"],
            "top_single_pulse_frac": f1["top_returns_single_pulse_frac"],
            "pieces": [{"along_m": p["a"], "height_m": p["height_m"], "bins": p["bins"]} for p in pieces],
            "naip_tone_on_the_line": "R 204-212 G 203-213 B 183-199 (light grey), its shadow 2-4 m WNW (f1_naip.py)",
            "verdict": "a thin, opaque, level-topped screen 3.2-4.1 m over the ground, light grey: a screen wall or screened fence, NOT a hedge; built (kind screen) where the read measured it",
        }
        it["identity_confidence"] = "high (structure); wall vs screened fence unresolved"
        continue
    if i in ("S1", "S2", "P1"):
        it["lidar_2017"] = {"source": FLIGHT, "verdict": "outside the approved 45 m read: height stays [invented]"}
        continue
    v = VERDICT[i]
    v = VERDICT[v[3:]] if v.startswith("as ") else v
    c = cnt.get(i)
    it["lidar_2017"] = {"source": FLIGHT, "per_m_within_1m_on_vs_control": c if isinstance(c, dict) else None, "verdict": v}
(A / "furniture/inventory.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False), encoding="utf-8")
print("inventory.json: lidar_2017 on", len(inv["items"]), "items")

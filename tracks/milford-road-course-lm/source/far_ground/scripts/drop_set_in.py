"""Ledger 0082 'Far ground (0.1.11)': a pass-4 far block the author refuses ON THE REAL GROUND leaves furniture/pass4/blocks.json
for blocks_dropped.json, with its reason and the measurement. On 0.1.11's far ground (the 2017 lidar's) mpg_nw_complex_0, the
lowest roof of the NW complex (roof 25.91 m, wall 5.11 m over its median lidar ground), has ground returns 25.44-25.56 m 5-6 m
east of its east wall (e -560.5, n 437-439: outside every footprint) and 19.6-20.0 m along its north wall: it is set into its
slope, its south-east end at grade with its roof. tools/author_bespoke_blend.py refuses a measured roof standing less than
half its wall over the highest built ground under its rim (0.19 m in run 1 of b0111); that rule is not loosened. Standing a
building set into its slope is Del Mar's set-in form (ledger 0083 pass 4b), not on this branch: owed.

    python drop_set_in.py            (idempotent; edits ../../furniture/pass4/blocks.json + blocks_dropped.json)
"""
import json
from pathlib import Path

P4 = Path(__file__).resolve().parents[2] / "furniture" / "pass4"
DROP = {"mpg_nw_complex_0": "set into its slope on the real ground (0.1.11): the lidar's ground 25.44-25.56 m 5-6 m east of its "
                            "east wall, its roof 25.91 m; the author refuses a roof under half its wall over its rim's highest ground"}
blocks = json.loads((P4 / "blocks.json").read_text(encoding="utf-8"))
dropped = json.loads((P4 / "blocks_dropped.json").read_text(encoding="utf-8"))
tiers = json.loads((P4 / "tiers_p4.json").read_text(encoding="utf-8"))
keep = []
for b in blocks:
    if b["key"] not in DROP:
        keep.append(b)
        continue
    t = next(t for t in tiers if t["footprint_lonlat"] == b["footprint_lonlat"])
    dropped.append({"src": t["src"], "tier": t["tier"], "area_m2": t["area_m2"], "fill": t["fill"], "why": "set into its slope",
                    "key": b["key"], "_why": DROP[b["key"]]})
    print(f"dropped {b['key']}")
(P4 / "blocks.json").write_text(json.dumps(keep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(P4 / "blocks_dropped.json").write_text(json.dumps(dropped, indent=1) + "\n")

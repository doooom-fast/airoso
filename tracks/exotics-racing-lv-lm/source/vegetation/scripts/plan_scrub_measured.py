"""Nevada Nights 0.1.5 (ledger 0089): the NAIP clumps (scrub.naip.json: positions and crowns) at their LIDAR heights
(scrub.lidar.json, lidar/clump_heights.py). A clump is planted when its measured top stands more than K_SD times its own
ground's scatter above that ground (it stands up, with about 95 % confidence); the others have no height the lidar can
tell from the ground and are left out, counted. Writes source/vegetation/scrub.measured.json: [lon, lat, 0, h_m, crown_m, key].

    python tracks/exotics-racing-lv-lm/source/vegetation/scripts/plan_scrub_measured.py
"""
import json
from pathlib import Path

K_SD = 2.0   # a two-sided 95 % bar on the ground plane's own scatter; not tuned

here = Path(__file__).resolve().parents[1]
naip = {p[5]: p for p in json.loads((here / "scrub.naip.json").read_text(encoding="utf-8"))["points"]}
lid = json.loads((here / "scrub.lidar.json").read_text(encoding="utf-8"))["clumps"]
pts, low = [], []
for r in sorted(lid, key=lambda r: r["key"]):
    p = naip[r["key"]]
    if r["top_m"] > K_SD * r["ring_sd_m"]:
        pts.append([p[0], p[1], 0, r["top_m"], p[4], r["key"]])
    else:
        low.append(r["key"])
hs = sorted(p[3] for p in pts)
doc = {"_source": ("Positions and crowns: scrub.naip.json (NAIP 2019 + 2022). Heights: scrub.lidar.json (3DEP NV_ClarkCo_2_B22, "
                   "2022-07-28), the second-highest return over the clump's own ground plane, MEASURED. Planted when that top "
                   "clears %.0f x the ground's scatter; %d of %d do. The rest (%s) have no height the lidar separates from the "
                   "ground: not planted." % (K_SD, len(pts), len(lid), low)),
       "heights_m": {"min": hs[0], "median": hs[len(hs) // 2], "max": hs[-1]} if hs else {},
       "cols": 1, "rows": 1, "points": pts}
(here / "scrub.measured.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
print(f"[scrub] {len(pts)} of {len(lid)} clumps stand clear of their ground; heights {hs[0] if hs else '-'}..{hs[-1] if hs else '-'} m")

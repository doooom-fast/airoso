"""Ledger 0084 stills: pick the three spots off the 0.1.7 line and write the cameras both builds are shot with.

    python pick_spots.py <0.1.7 workshop> <spots.json>

front_straight  the S/F straight: the line's first station (the timing line), raced north
fast_curve      the tightest station where the model carries >= 150 km/h
apex            the tightest corner on the lap (its apex: the line hugs the inside edge, rubber at its peak, the edge strip
                beside it clipped)
Each spot: `low` the eye 1.1 m over the line 24 m before the spot, looking at the road 6 m past it; `top` 28 m straight over
the spot (a hair behind it, so the view's up is the direction of travel).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from scripts.aerial import road_wear as rw  # noqa: E402

proj, out = Path(sys.argv[1]), Path(sys.argv[2])
L = json.loads((proj / "data" / "road_wear.line.full.json").read_text(encoding="utf-8"))
P = np.array(L["points"])
spec = json.loads((proj / "data" / "road_wear.json").read_text(encoding="utf-8"))["spec"]
v, _al, _ag = rw.speed_profile(P, 2.0, spec["wear"], True)
k = np.abs(rw.curvature(P, True))
n = len(P)
fast = np.where(v * 3.6 >= 150.0)[0]
i_fast = int(fast[np.argmax(k[fast])])
i_apex = int(np.argmax(k))
spots = []
for tag, i in (("front_straight", 12), ("fast_curve", i_fast), ("apex", i_apex)):
    b = P[(i - 12) % n]; c = P[i]; f = P[(i + 3) % n]
    spots.append({"tag": f"{tag}_low", "eye": [b[0], b[1], b[2] + 1.1], "look": [f[0], f[1], f[2]], "fov": 60.0,
                  "station": i, "v_kmh": round(float(v[i]) * 3.6, 1), "radius_m": round(1 / max(1e-9, float(k[i])), 1)})
    t = P[(i + 1) % n] - P[(i - 1) % n]; t = t / (np.linalg.norm(t[:2]) or 1)
    spots.append({"tag": f"{tag}_top", "eye": [c[0] - t[0] * 0.05, c[1] - t[1] * 0.05, c[2] + 28.0],
                  "look": [c[0], c[1], c[2]], "fov": 60.0, "station": i})
for s in spots:
    s["eye"] = [round(float(x), 3) for x in s["eye"]]; s["look"] = [round(float(x), 3) for x in s["look"]]
out.write_text(json.dumps(spots, indent=1), encoding="utf-8")
for s in spots:
    print(s["tag"], s.get("station"), s.get("v_kmh", ""), s.get("radius_m", ""))

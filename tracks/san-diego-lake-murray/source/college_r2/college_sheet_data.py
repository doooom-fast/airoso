"""Twelve stations of College's split stretch as plain JSON for the picture (run with Blender's python after college_sections.py)."""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
L = json.loads((HERE / "college_xsec.lidar.g10.json").read_text(encoding="utf-8"))
B = np.load(HERE / "college_built_y.npy")
V = L["stations"]["v"]; out = []
for v in (1180, 1200, 1220, 1240, 1260, 1280, 1320, 1340, 1380, 1400, 1420, 1460):
    i = V.index(v)
    out.append({"v": v, "s_m": L["stations"]["s_m"][i], "y_line": L["stations"]["y_line"][i],
                "measured": [None if (h is None or (f & 17)) else round(h - 100.8, 3) for h, f in zip(L["h_navd88_m"][i], L["flags"][i])],
                "built": [None if np.isnan(b) else round(float(b), 3) for b in B[i]]})
(HERE / "college_sheet_data.json").write_text(json.dumps({"offsets_m": L["offsets_m"], "stations": out}), encoding="utf-8")
print("ok", len(out))

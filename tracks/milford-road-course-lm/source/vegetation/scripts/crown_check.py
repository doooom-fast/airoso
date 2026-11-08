"""Ledger 0082 vegetation pass, the PC's measured model sizes: per planted tree, its measured height and crown against what
TreeFX draws. size = h / HEIGHT; a uniform size alone draws the crown WIDTH x size; the width multiplier (planted.native_w_m)
brings it back to the measured crown. Reports both, and the trees whose width multiplier lies far from 1 (the model squeezed
or stretched sideways): the bands are for reporting only, nothing is clamped.

    python crown_check.py <worktree> <workshop> <out.json>
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np

W, WS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
tmp = OUT.parent / "plan_w"
shutil.rmtree(tmp, ignore_errors=True)
tmp.mkdir()
for d in ("data", "source"):
    os.symlink(WS / d, tmp / d)
shutil.copy(W / "tracks/milford-road-course-lm/track.config.json", tmp / "track.config.json")
sys.path.insert(0, str(W))
sys.path.insert(0, str(W / "tools"))
s = importlib.util.spec_from_file_location("mt", W / "tools/make_treefx.py")
mt = importlib.util.module_from_spec(s)
s.loader.exec_module(mt)
with contextlib.redirect_stdout(io.StringIO()):
    p = mt.plan(tmp)
cfg = json.loads((tmp / "track.config.json").read_text(encoding="utf-8"))["scenery"]["treefx"]["planted"]
NH = {k: v for k, v in cfg["native_h_m"].items() if not k.startswith("_")}
NW = {k: v for k, v in cfg["native_w_m"].items() if not k.startswith("_")}
pts = json.loads((W / "tracks/milford-road-course-lm/source/vegetation/trees.lm.json").read_text(encoding="utf-8"))["points"]
R = re.compile(r"tree: (\S+); pos=([-0-9.]+), ([-0-9.]+), ([-0-9.]+); angle = \d+; size = ([0-9.]+); width = ([0-9.]+)")
rows = [R.match(ln) for ln in p["lines"] if ln.startswith("tree:")]
assert all(rows) and len(rows) == len(pts), (len(rows), len(pts))
# lines follow the points' order (one zone, none rejected: the v1 log's 10419 of 10419)
model = [m.group(1) for m in rows]
size = np.array([float(m.group(5)) for m in rows])
width = np.array([float(m.group(6)) for m in rows])
h = np.array([q[3] for q in pts])
c = np.array([q[4] for q in pts])
nh = np.array([NH[m] for m in model])
nw = np.array([NW[m] for m in model])
drawn_h = size * nh
uniform_c = size * nw
drawn_c = size * nw * width
pct = lambda a: [round(float(x), 2) for x in np.percentile(a, [1, 10, 50, 90, 99])]
rep = {
    "trees": len(rows), "models": {m: model.count(m) for m in sorted(set(model))},
    "size_p1_p10_p50_p90_p99": pct(size),
    "height_error_m_max": round(float(np.abs(drawn_h - h).max()), 3),
    "crown_error_m_max_with_width": round(float(np.abs(drawn_c - c).max()), 3),
    "uniform_crown_over_measured_p1_p10_p50_p90_p99": pct(uniform_c / c),
    "uniform_crown_m_p50": round(float(np.median(uniform_c)), 1), "measured_crown_m_p50": round(float(np.median(c)), 1),
    "uniform_within_25pct": int((np.abs(uniform_c / c - 1) <= 0.25).sum()),
    "width_mult_p1_p10_p50_p90_p99": pct(width),
    "width_mult_bands": {"<0.25": int((width < 0.25).sum()), "0.25-0.5": int(((width >= 0.25) & (width < 0.5)).sum()),
                         "0.5-2": int(((width >= 0.5) & (width <= 2)).sum()), ">2": int((width > 2).sum())},
    "crown_over_height_p1_p50_p99": [round(float(x), 2) for x in np.percentile(c / h, [1, 50, 99])],
}
extreme = np.where((width < 0.25) | (width > 2.0))[0]
rep["extreme"] = [{"lon": pts[i][0], "lat": pts[i][1], "model": model[i], "h_m": h[i], "crown_m": c[i], "size": size[i],
                   "width": width[i]} for i in extreme[np.argsort(width[extreme])]]
OUT.write_text(json.dumps(rep, indent=1))
print(json.dumps({k: v for k, v in rep.items() if k != "extreme"}, indent=1))
print("extreme (width < 0.25 or > 2):", len(rep["extreme"]), rep["extreme"][:5])

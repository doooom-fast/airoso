"""Ledger 0092, items 5-6: GrassFX looks within 30 m of the lane edge, two readings compared (the scenery audit's
ground_classes.py metrics, on the class map's 2 m cells in the draft's own frame): look boundary, class = look, the ride
pad's and the run-off pads' looks.

python grassfx_metrics.py <track dir> <grassfx.aerial.json before> <grassfx.aerial.json after>"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

T = Path(sys.argv[1])
sys.path.insert(0, str(T.parents[1]))
sys.path.insert(0, str(T / "source" / "runoff" / "scripts"))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402
import runoff_pads as rp  # noqa: E402

cfg = json.loads((T / "track.config.json").read_text())
gz = cfg["scenery"]["bespoke"]["grassfx_zones"]
origin, P, half, s = rp.load_line()
m_lon, m_lat = _meters_per_degree(origin["lat"])
W_, S_, E_, N_ = gz["bbox_lonlat"]
G = np.asarray(Image.open(T / gz["image"]).convert("RGB")).astype(int)
H, W = G.shape[:2]
lon = W_ + (np.arange(W) + 0.5) / W * (E_ - W_)
lat = N_ - (np.arange(H) + 0.5) / H * (N_ - S_)
X, Z = np.meshgrid((lon - origin["lon"]) * m_lon, (lat - origin["lat"]) * m_lat)
r, g, b = G[..., 0], G[..., 1], G[..., 2]
cls = np.full((H, W), "?", "<U4")
cls[(r < 40) & (g > 90) & (g < 150) & (b < 40)] = "C"
cls[(r > 170) & (g > 170) & (b < 40)] = "B"
cls[(r < 40) & (g < 40) & (b > 170)] = "D"
cls[(r > 230) & (g > 230) & (b > 230)] = "base"
q = rp.edge_query(P, half, s, X.ravel(), Z.ravel())
D = q[:, 0].reshape(H, W)
rec = json.loads((T / "source" / "runoff" / "runoff_pads.json").read_text())
padm = np.zeros((H, W), bool)
for bl in rec["blobs"]:
    if bl["kept"]:
        padm |= rp.point_in([tuple(p) for p in bl["inner_xz"] + bl["outer_xz"][::-1]], X, Z)
ride = next(p for p in cfg["scenery"]["bespoke"]["pads"] if p["key"] == "ride_pad")
ridem = rp.point_in([((a - origin["lon"]) * m_lon, (c - origin["lat"]) * m_lat) for a, c in ride["quad_lonlat"]], X, Z)


def look_of(path):
    adj = json.loads(Path(path).read_text())["adjustments"]
    look = np.full((H, W), "base", "<U4")
    for a in adj[::-1]:
        cx, cy, cz = a["rect"]["center"]
        sx, sz = a["rect"]["size"]
        m = (np.abs(X - cx) <= sx / 2) & (np.abs(Z - (-cz)) <= sz / 2)
        look[m] = a["map"]
    return adj, look


near = (D >= 0) & (D < 30)
out = {}
for tag, path in (("before", sys.argv[2]), ("after", sys.argv[3])):
    adj, look = look_of(path)
    res = {"rects": len(adj), "by_map": {k: sum(1 for a in adj if a["map"] == k) for k in "BCD"}}
    chg_x = (look[:, 1:] != look[:, :-1]) & near[:, 1:]
    chg_z = (look[1:, :] != look[:-1, :]) & near[1:, :]
    res["look_boundary_m_within_30m"] = int((chg_x.sum() + chg_z.sum()) * 2)
    # boundaries outside the pads (a boundary under a 1RUNOFF pad is hidden by the occluder)
    vis_x = chg_x & ~padm[:, 1:] & ~padm[:, :-1]
    vis_z = chg_z & ~padm[1:, :] & ~padm[:-1, :]
    res["look_boundary_m_within_30m_off_pads"] = int((vis_x.sum() + vis_z.sum()) * 2)
    pair = {}
    for A_, B_, mm in ((look[:, 1:], look[:, :-1], chg_x), (look[1:, :], look[:-1, :], chg_z)):
        for u, v in zip(A_[mm], B_[mm]):
            k = "/".join(sorted((u, v)))
            pair[k] = pair.get(k, 0) + 2
    res["pairs_m"] = dict(sorted(pair.items(), key=lambda t: -t[1])[:6])
    agree = {}
    for k in ("C", "B", "D", "base"):
        m = near & (cls == k) & ~padm & ~ridem
        agree[k] = round(100.0 * float((look[m] == k).sum()) / max(1, int(m.sum())), 1)
    res["class_eq_look_pct_0_30m_off_pads"] = agree
    res["ride_pad_cells_look_pct"] = {k: round(100.0 * float((look[ridem] == k).sum()) / max(1, int(ridem.sum())), 1)
                                      for k in ("base", "B", "C", "D")}
    res["under_runoff_pads_look_pct"] = {k: round(100.0 * float((look[padm] == k).sum()) / max(1, int(padm.sum())), 1)
                                         for k in ("base", "B", "C", "D")}
    out[tag] = res
cchg = ((cls[:, 1:] != cls[:, :-1]) & near[:, 1:]).sum() + ((cls[1:, :] != cls[:-1, :]) & near[1:, :]).sum()
out["class_boundary_m_within_30m"] = int(cchg * 2)
print(json.dumps(out, indent=1))

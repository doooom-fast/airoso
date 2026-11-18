"""Ledger 0092, item 1: a loop.blend's TERRAIN minus the 2017 lidar on the scenery audit's 1 m cells (ground returns, 1GRASS
in the audit's 0.1.5 owner raster), by band off the lane edge; the 25 m side-stretches; s 4,325-4,375 and s 1,000-1,225.

blender -b <loop.blend> --python terrain_resid_blend.py -- <out.json>
    env NPZ (default this track's source/lidar/milford_lidar_1m.npz), AUD = the scenery audit's out/ (lidar1m_dedge /
    _station / _side, v015_ground_owner1m .npy)"""
import os, sys, json
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out = sys.argv[sys.argv.index("--") + 1]
AUD = os.environ.get("AUD") or "/Volumes/Sundowning/codex/mac/milford-hp-audit-20261118/scenery/out/"
AUD = AUD.rstrip("/") + "/"
z = np.load(os.environ.get("NPZ") or Path(__file__).resolve().parents[2] / "lidar" / "milford_lidar_1m.npz")
L = np.where(z["ground_z_cm_over_z0"] != -1, float(z["z0_m"]) + z["ground_z_cm_over_z0"] / 100 - 316.26, np.nan)
gn = z["ground_n"]
D = np.load(AUD + "lidar1m_dedge.npy"); S = np.load(AUD + "lidar1m_station.npy"); SD = np.load(AUD + "lidar1m_side.npy")
owner = np.load(AUD + "v015_ground_owner1m.npy")
ob = bpy.data.objects["TERRAIN"]
me = ob.data
bvh = BVHTree.FromPolygons([v.co[:] for v in me.vertices], [p.vertices[:] for p in me.polygons])
e0, n0 = int(z["e0"]), int(z["n0"])
jj, ii = np.where((D >= 0) & (D < 45) & (owner == 1) & (gn > 0))
B = np.full(L.shape, np.nan)
for j, i in zip(jj, ii):
    h = bvh.ray_cast(Vector((e0 + i + 0.5, n0 + j + 0.5, 500.0)), Vector((0, 0, -1)), 1000.0)
    if h[0] is not None:
        B[j, i] = h[0].z
R = B - L
res = {"verts": len(me.vertices), "faces": len(me.polygons), "bands": {}}
for b0, b1 in [(0, 3), (3, 9), (9, 12), (12, 20), (20, 30), (30, 45)]:
    m = (D >= b0) & (D < b1) & np.isfinite(R)
    r = np.abs(R[m])
    res["bands"][f"{b0}-{b1}"] = {"cells": int(m.sum()), "abs_p50": round(float(np.median(r)), 3), "abs_p95": round(float(np.percentile(r, 95)), 3),
                                  "over_1m_pct": round(100 * float((r > 1).mean()), 1)}
rows = []
for s0 in range(0, 4900, 25):
    for sd in (1, -1):
        m = np.isfinite(R) & (D >= 3) & (D < 20) & (S >= s0) & (S < s0 + 25) & (SD == sd)
        if m.sum() >= 30:
            rows.append(float(np.percentile(np.abs(R[m]), 90)))
res["stretches_25m_3_20m_p90_over_0.5"] = [sum(v > 0.5 for v in rows), len(rows)]
m = np.isfinite(R) & (S >= 4325) & (S < 4375) & (D < 45)
res["max_abs_s4325_4375"] = round(float(np.abs(R[m]).max()), 2)
m = np.isfinite(R) & (S >= 1000) & (S < 1225) & (D >= 9) & (D < 30)
res["s1000_1225_9_30m_abs_p50_p95"] = [round(float(np.median(np.abs(R[m]))), 2), round(float(np.percentile(np.abs(R[m]), 95)), 2)]
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res))

"""The skid pad's paved outline (ledger 0085, furniture pass 1, 0.2.1): the lot the road course runs round the long way,
its interior the big concrete circle and the asphalt to its south-east, unbuilt ground until now.

THE OUTLINE: junction_pads.py's pavement rule (NAIP 2023 grey x the 2018 lidar's asphalt-dark intensity, or a red / white
kerb) on its GRID_M grid over a box round the lot, the infield road's own ribbon taken out (its centre line +- half its
width + the route.edge strip, CURB_M: the road and its edge strip are the road's), the component holding the circle's
centre traced, smoothed and resampled with draft_pads' helpers (draft_pad_outline's numbers). The pad is that outline:
tools/author_bespoke_blend.py pads (a strip from its centre to the outline), its cells over the road left out.

    python tracks/pikes-peak/source/lidar/infield/skid_pad.py <workshop project> --naip <crop png> \
        --lidar D:/k10-scratch/pp_lidar/infield.npz --centre E,N --out <prefix>

Writes <prefix>.json {"outline_en", "outline_lonlat", "centre_en", "area_m2", ...} and <prefix>.png.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from junction_pads import Crop, fill_small_holes, SAT_MAX, VEG_SAT, HOLE_MAX_M2  # noqa: E402,F401

AIROSO = HERE.parents[4]
sys.path.insert(0, str(AIROSO))
from tools import draft_pads as dp  # noqa: E402
from tools import draft_pad_outline as dpo  # noqa: E402

HALF_M = 95.0         # [invented] the box round the lot's centre the read covers (the lot is ~150 x 75 m)
CURB_M = 1.3          # route.edge's strip: curb_face_w 0.1 + sidewalk_w 0.2 + grade_w 1.0 (track.config.json)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--naip", required=True)
    ap.add_argument("--lidar", required=True)
    ap.add_argument("--centre", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    crop = Crop(Path(a.naip), loc["origin"])
    cE, cN = (float(v) for v in a.centre.split(","))
    G = dpo.GRID_M
    n = int(round(2 * HALF_M / G))
    xs = cE - HALF_M + (np.arange(n) + 0.5) * G
    ys = cN + HALF_M - (np.arange(n) + 0.5) * G
    gx, gy = np.meshgrid(xs, ys)
    L = np.load(a.lidar)
    g = L["cls"] == 2
    E, N, I = L["e"][g], L["n"][g], L["inten"][g].astype(float)
    win = (np.abs(E - cE) < HALF_M + 3) & (np.abs(N - cN) < HALF_M + 3)
    E, N, I = E[win], N[win], I[win]
    tree = cKDTree(np.c_[E, N])
    # the threshold: the infield road's own points against the vegetation (junction_pads' rule, the road for the lane)
    road_pts = np.vstack([np.array([[q[0], q[2]] for q in c["points_xyz_m"]]) for c in conns])
    dd, _ = cKDTree(road_pts).query(np.c_[E, N])
    veg = crop.sat[crop.ij(E, N)] > VEG_SAT
    on, off = float(np.median(I[dd < 2.0])), float(np.median(I[veg]))
    thr = (on + off) / 2.0
    idx = tree.query_ball_point(np.c_[gx.ravel(), gy.ravel()], dpo.MEAN_R_M)
    val = np.array([I[q].mean() if len(q) else np.nan for q in idx]).reshape(n, n)
    mask = (crop.grey(gx, gy) & (np.isnan(val) | (val < thr))) | crop.kerb(gx, gy)
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    mask = fill_small_holes(mask, G, HOLE_MAX_M2)
    # the road's own: every connector's ribbon and edge strip
    road = np.zeros_like(mask)
    for c in conns:
        P = [(q[0], q[2]) for q in c["points_xyz_m"]]
        W = c["widths_m"]
        for k in range(len(P) - 1):
            road |= dp.segment_band(P[k], P[k + 1], gx, gy, W[k] / 2.0 + CURB_M)
    keep = mask & ~road
    lab, _ = ndimage.label(keep)
    ci, cj = int((cN + HALF_M - cN) / G), int((cE - (cE - HALF_M)) / G)
    if not lab[ci, cj]:
        raise SystemExit("skid_pad: the centre is not on pavement off the road")
    region = lab == lab[ci, cj]
    if region[0].any() or region[-1].any() or region[:, 0].any() or region[:, -1].any():
        raise SystemExit("skid_pad: the region reaches the box's edge (it leaks past the lot)")
    ring = dp.trace_boundary(region.tolist(), xs.tolist(), ys.tolist())
    ring = dp.smooth_ring(ring, dpo.SMOOTH_M)
    ring = dp.resample_ring(ring, dpo.STEP_M * 2)
    area = abs(sum(ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1] for i in range(len(ring)))) / 2.0
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    # star-shaped from its centroid (the pad is a fan from it): every outline point visible from the centre
    blocked = 0
    for x, y in ring[::4]:
        for t in np.linspace(0.05, 0.95, 19):
            px_, py_ = cx + (x - cx) * t, cy + (y - cy) * t
            i_, j_ = int((cN + HALF_M - py_) / G), int((px_ - (cE - HALF_M)) / G)
            if not region[i_, j_]:
                blocked += 1
                break
    lon0, lat0 = float(loc["origin"]["lon"]), float(loc["origin"]["lat"])
    m_lat, m_lon = crop.m_lat, crop.m_lon
    rec = {"_doc": __doc__.split("\n\n")[0], "centre_en": [round(cx, 2), round(cy, 2)],
           "outline_en": [[round(x, 3), round(y, 3)] for x, y in ring],
           "outline_lonlat": [[round(lon0 + x / m_lon, 8), round(lat0 + y / m_lat, 8)] for x, y in ring],
           "centre_lonlat": [round(lon0 + cx / m_lon, 8), round(lat0 + cy / m_lat, 8)],
           "area_m2": round(area, 1), "rays_blocked_of_sampled": [blocked, len(ring[::4])],
           "source": {"naip": crop.item, "lidar": "CO_Eastern_ElPaso_2018 class-2 intensity (infield.npz)",
                      "intensity_road_median": round(on), "intensity_vegetation_median": round(off), "threshold": round(thr),
                      "road_cut": f"every connector's ribbon + {CURB_M} m strip", "method": "tracks/pikes-peak/source/lidar/infield/skid_pad.py"}}
    Path(a.out + ".json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    jj, ii = crop.ij(gx, gy)
    rgb = crop.rgb[jj, ii] * 0.55
    rgb[region] = rgb[region] * 0.5 + 110
    rgb[road] = rgb[road] * 0.7 + np.array([0, 60, 120])
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    r_ = [((x - (cE - HALF_M)) / G, ((cN + HALF_M) - y) / G) for x, y in ring]
    d.line(r_ + [r_[0]], fill=(255, 230, 0), width=2)
    img.save(a.out + ".png")
    print(f"[skid-pad] {len(ring)} outline points, {area:.0f} m2, centre ({cx:.1f}, {cy:.1f}); intensity road {on:.0f} / "
          f"vegetation {off:.0f} -> {thr:.0f}; rays from the centre blocked: {blocked} of {len(ring[::4])} -> {a.out}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

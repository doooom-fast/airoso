"""(the setup of naip_read.py) High Plains NAIP 2023 0.3 m read for ledger 0084 (Mac, no build): registration, shadows / paint, and whether the
rubber shows on the model line, on the centreline's own corridor (an estimate of the built road: centreline +- half width)."""
import json, sys, math
from pathlib import Path
import numpy as np
from PIL import Image
A = Path(sys.argv[1]); sys.path.insert(0, str(A))
from scripts.aerial import road_wear as rw
T = A / "tracks/high-plains-lm"
cfg = json.loads((T / "track.config.json").read_text())
spec = rw.spec_from_config(cfg)
d = json.loads((T / "data/centerline.local.json").read_text()); o = d["origin"]
p = np.array(d["points_xyz_m"]); W = np.array(d["widths_m"])
C = rw.closed_polyline(np.c_[p[:, 0], p[:, 2], p[:, 1]])
img = np.asarray(Image.open(T / spec["aerial"]["image"]).convert("RGB")).astype(np.float32) / 255
aer = rw.Aerial(img, spec["aerial"]["bbox_lonlat"], (o["lon"], o["lat"]))
tex = 0.2
C2, W2, L = rw.resample(C, 1.0, True, W[:len(C), None])
n = rw.left_normals(C2)
g = rw.Grid.around(C2[:, 0].min(), C2[:, 1].min(), C2[:, 0].max(), C2[:, 1].max(), tex, 4.0, 12.0)
# road mask: cells within half width of the centreline (KD-free: rasterise quads between stations)
tris = []
for i in range(len(C2)):
    j = (i + 1) % len(C2)
    a0 = C2[i, :2] + n[i] * W2[i, 0] / 2; a1 = C2[i, :2] - n[i] * W2[i, 0] / 2
    b0 = C2[j, :2] + n[j] * W2[j, 0] / 2; b1 = C2[j, :2] - n[j] * W2[j, 0] / 2
    tris += [(a0, a1, b1), (a0, b1, b0)]
road = rw.rasterize(g, np.array(tris))
reg = rw.register(aer, g, road)
aer.dx, aer.dy = reg["dx_m"], reg["dy_m"]
tone, ts = rw.tone_field(aer, g, road, spec["tone"])
print("registration", reg); print("tone", ts)
# luminance stats on the road
X, Y = g.centres(0, 0, g.nx, g.ny)
rgb = aer.sample(X, Y); lum = rw.luminance(rgb)
lr = lum[road & np.isfinite(lum)]; med = np.median(lr)
br = (rgb[..., 2] / np.maximum(rgb[..., 0], 1e-3))[road & np.isfinite(lum)]
q = np.percentile(lr / med, [0.5, 1, 5, 50, 95, 99, 99.5])
print("road lum / median p0.5,1,5,50,95,99,99.5", np.round(q, 3), "b/r lit median", round(float(np.median(br)), 3),
      "dark tail (<0.72) %", round(100 * float(np.mean(lr / med < 0.72)), 2), "its b/r", round(float(np.median(br[lr / med < 0.72])) if np.any(lr / med < 0.72) else 0, 3),
      "paint (>1.45) %", round(100 * float(np.mean(lr / med > 1.45)), 2))
# the model line inside the corridor
w = spec["wear"]
a = rw.min_curvature(C2, n, -(W2[:, 0] / 2 - w["margin_m"]), W2[:, 0] / 2 - w["margin_m"], True)
Pl = np.column_stack([C2[:, :2] + a[:, None] * n, C2[:, 2]])
P2, _, _ = rw.resample(Pl, 2.0, True)
I, sp = rw.rubber_intensity(P2, 2.0, w, True)
print("model line", sp, "lateral offset p5/p50/p95", np.round(np.percentile(a, [5, 50, 95]), 2))
def profile(P, I, sel):
    nn = rw.left_normals(P, True); us = np.arange(-4.0, 4.01, 0.25)
    out = []
    for i in np.where(sel)[0][::2]:
        xs = P[i, 0] + nn[i, 0] * us; ys = P[i, 1] + nn[i, 1] * us
        s = rw.luminance(aer.sample(xs, ys)); ii, jj = g.index(xs, ys)
        ok = (ii >= 0) & (jj >= 0) & (ii < g.nx) & (jj < g.ny)
        on = np.zeros(len(us), bool); on[ok] = road[jj[ok], ii[ok]]
        if not on.all() or not np.isfinite(s).all():
            continue
        out.append(s / np.median(s))
    return us, np.array(out)
for name, P, Ii in (("model line", P2, I), ("centreline", *rw.resample(C2, 2.0, True)[:1], None)):
    if Ii is None:
        Ii = rw.rubber_intensity(P, 2.0, w, True)[0]
    us, pr = profile(P, Ii, Ii >= 0.7)
    if len(pr):
        m = pr.mean(axis=0); core = m[np.abs(us) <= 0.75].mean(); ref = m[(np.abs(us) >= 3) & (np.abs(us) <= 4)].mean()
        print(name, "stations", len(pr), "band |u|<=0.75 vs 3-4 m out:", round(100 * (1 - core / ref), 2), "% darker",
              "profile", np.round(m[::4], 3).tolist())
    else:
        print(name, "no full cross-sections inside the corridor (the road is 12 m: +-4 m off the line leaves it)")


# --- photo mode (Kevin 2026-11-10 "Use the photo's rubber"), simulated on this corridor: the bake's measurement on the
# photo (road_wear.photo_rubber) against the gate's on the shipped atlas (road_wear_check.measure_photo), the shipped atlas
# being m0 x tone in 8 bits with no drawn band; then the kerb profile's peak
sys.path.insert(0, str(A / "tools"))
import road_wear_check as rwc
ph = dict(rw.PHOTO)
lit_mask = rw.tone_field(aer, g, road, spec["tone"], return_lit=True)[2]
ri = max(1, int(round(ph["interior_m"] / tex)))
interior = road & (rw.box_mean(road.astype(np.float64), np.ones(road.shape), ri) >= 1.0 - 1e-9)
usable = interior & lit_mask
def tone_at(x, y):
    i, j = g.index(x, y); ok = (i >= 0) & (j >= 0) & (i < g.nx) & (j < g.ny)
    out = np.full(np.shape(x), np.nan); ok2 = ok.copy(); ok2[ok] = usable[j[ok], i[ok]]; out[ok2] = tone[j[ok2], i[ok2]]
    return out
Cc, _, _ = rw.resample(C2, 2.0, True); nCc = rw.left_normals(Cc, True)
w = spec["wear"]
a_ = rw.min_curvature(C2, n, -(W2[:, 0] / 2 - w["margin_m"]), W2[:, 0] / 2 - w["margin_m"], True)
Pl = np.column_stack([C2[:, :2] + a_[:, None] * n, C2[:, 2]]); P2, _, _ = rw.resample(Pl, 2.0, True)
decl = rw.photo_rubber(tone_at, P2, Cc, nCc, True, ph)
print("bake (photo):", {k: decl[k] for k in ("depth", "peak", "centroid_m", "stations", "samples")})
print("  D(u):", list(zip(decl["u"], decl["D"])))
m0 = min(1.0, 1.0 / float(np.percentile(tone[road], spec["tone"]["headroom_pct"])))
ship = np.round(np.clip(m0 * tone, 0, 1) * 255) / 255.0
ref_l = ts["lit_median_lum"]; apx = 0.3
def value_at(x, y):
    i, j = g.index(np.array([x, x + 1.5, x - 1.5, x, x]), np.array([y, y, y, y + 1.5, y - 1.5]))
    if (i < 0).any() or (j < 0).any() or (i >= g.nx).any() or (j >= g.ny).any() or not road[j, i].all():
        return None
    for dx in (-apx, 0.0, apx):
        for dy in (-apx, 0.0, apx):
            c = aer.sample(np.array([x + dx]), np.array([y + dy]))[0]
            if not np.isfinite(c).all():
                return None
            l = float(rw.luminance(c)); br = float(c[2] / max(c[0], 1e-3))
            if (l < spec["tone"]["shadow_lum"] * ref_l and br > spec["tone"]["shadow_blue"]) or l > spec["tone"]["paint_lum"] * ref_l:
                return None
    return float(ship[j[0], i[0]])
got = rwc.measure_photo(np.round(P2, 3).tolist(), np.round(Cc[:, :2], 3).tolist(), np.round(nCc, 6).tolist(), True, value_at, ph)
G = rwc.GATE
ok = (got["stations"] >= 10 and decl["depth"] >= G["photo_min_depth"] and abs(got["depth"] - decl["depth"]) <= G["photo_depth_tol"]
      and abs(got["centroid_m"] - decl["centroid_m"]) <= G["photo_centroid_tol_m"])
print("gate (shipped):", {k: got[k] for k in ("depth", "centroid_m", "stations", "samples")})
print(f"photo_rubber row: depth {got['depth']} vs {decl['depth']} (tol {G['photo_depth_tol']}), centroid {got['centroid_m']:+.3f} vs "
      f"{decl['centroid_m']:+.3f} (tol {G['photo_centroid_tol_m']}), min depth {G['photo_min_depth']} -> {'PASS' if ok else 'FAIL'}")
# the drawn rubber row is not run in photo mode; the same atlas judged by it would ask for a drawn band (want 0 -> no pass)
print("kerbs: levels 16, top level = the measured peak", decl["peak"], "step", round(decl["peak"] / 15, 5))

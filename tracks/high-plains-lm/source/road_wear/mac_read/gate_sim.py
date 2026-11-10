"""High Plains NAIP 2023 0.3 m read for ledger 0084 (Mac, no build): registration, shadows / paint, and whether the
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


# --- the gate's rubber row, simulated on this corridor: shipped = tone x (1 - A x shape), sampled like road_wear_check
cover_half = W2[:, 0] / 2 + 1.5        # + the edge strip [estimate]
line = {"P": P2, "I": I, "closed": True, "layer_m": 10.0}
reach = 0.5 * w["track_m"] + 4 * w["spread_m"]
nn = rw.left_normals(P2, True)
dCl, iCl = None, None
def tone_at(x, y):
    ii, jj = g.index(x, y); return tone[np.clip(jj, 0, g.ny - 1), np.clip(ii, 0, g.nx - 1)]
# coverage test: distance to the centreline <= cover_half at the nearest centreline station
from numpy.linalg import norm
def covered(x, y):
    d = np.hypot(C2[:, 0][None] - x[:, None], C2[:, 1][None] - y[:, None]); k = d.argmin(1)
    return d[np.arange(len(x)), k] <= cover_half[k]
ks = np.arange(-16, 17); u = ks * 0.25
for A in (0.0, 0.10, 0.22):
    w2 = dict(w); w2["amplitude"] = 1.0
    prof = []; rub = []
    for i in range(0, len(P2), 5):
        if I[i] < 0.7: continue
        x = P2[i, 0] + nn[i, 0] * u; y = P2[i, 1] + nn[i, 1] * u
        if not covered(x, y).all(): continue
        sh = rw.wear_at(x, y, P2[i, 2], line, w2, reach)
        v = tone_at(x, y) * (1 - A * sh)
        ref = np.median(v[np.abs(ks) >= 12])
        prof.append(1 - v / ref); rub.append(I[i])
    prof = np.array(prof); m = prof.mean(0)
    core = np.maximum(0, m[np.abs(ks) <= 10]); kk = ks[np.abs(ks) <= 10]
    cen = (kk * 0.25 * core).sum() / core.sum()
    depth = m[np.abs(ks) <= 3].mean()
    tp = lambda q: rw.tyre_profile(np.asarray(q, float), w["track_m"], w["spread_m"])
    want = A * np.mean(rub) * (tp(u[np.abs(ks) <= 3]).mean() - tp(3.5))
    print(f"A {A}: stations {len(prof)} centroid {cen:+.3f} m depth {depth:.4f} want {want:.4f} ratio {depth / want if want else float('nan'):.2f}")

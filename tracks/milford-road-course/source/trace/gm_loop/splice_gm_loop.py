"""GM's 2.9 mi loop (ledger 0102, Milford round 2; Kevin 2026-11-22 on the calls page: "Build the 2.9 mi loop"): the
committed line with the 2022 hairpin loop (OSM 1030539760, first mapped 2022-02-11) replaced by OSM 72577413's own inner
turn (2010), written as a second data folder of this track (data_gm/, read by the port through lm_intake.source_data).

Every station outside the splice keeps its committed position, width and raw 3DEP sample EXACTLY; only the new piece is
new: its centre and paved width off Oakland County's 2025 ortho (7.62 cm; trace_inner.py off NAIP 2022, then
ortho_width.py re-centred on the whole pavement: the inner branch is concrete with an asphalt edge), its raw height
native 3DEP from data/corridor.elev.json (every 6 m along, 5 m across, +-60 m of the committed line; inverse distance
over the 4 nearest, as tools/lm_engine_intake.py's corner arcs read it). The profile and the projection are the stages'
own code (scripts.elevation.heightfield.profile_along at this track's 32 % cap; scripts.geometry.projection
.project_to_local at the committed origin), each first checked to reproduce the committed files.

    python -I splice_gm_loop.py <repo> <inner_ortho.json> <out dir> [fix_a=337] [fix_b=518]
"""
import json
import math
import shutil
import statistics
import sys
from pathlib import Path

REPO, ORTHO, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
FIX_A = int(sys.argv[4]) if len(sys.argv) > 4 else 337
FIX_B = int(sys.argv[5]) if len(sys.argv) > 5 else 518
sys.path.insert(0, str(REPO))
from scripts.elevation import heightfield as hf            # noqa: E402
from scripts.geometry.projection import project_to_local   # noqa: E402
from scripts.gps.centerline import haversine               # noqa: E402

TRK = REPO / "tracks" / "milford-road-course"
D = TRK / "data"
STEP_M = 3.0                  # the committed line's spacing (from_track's resample)
W_CLAMP = (9.0, 16.0)         # to_fixes.py's clamp
W_VALID = (7.0, 18.0)         # finalize.py: measured where it reads as one carriageway, else the median
W_MED_K = 10                  # finalize.py's running median, stations either side (2 m stations)
TAPER_M = 15.0                # [invented] the new piece's widths taper onto the kept neighbours' over this

cfg = json.loads((TRK / "track.config.json").read_text(encoding="utf-8"))
gj = json.loads((D / "centerline.geojson").read_text(encoding="utf-8"))
ej = json.loads((D / "centerline.elevation.json").read_text(encoding="utf-8"))
lj = json.loads((D / "centerline.local.json").read_text(encoding="utf-8"))
fixes = json.loads((TRK / "source" / "mrc_fixes.json").read_text(encoding="utf-8"))
full = next(f for f in gj["features"] if f["properties"].get("kind") == "full")
coords = [tuple(c) for c in full["geometry"]["coordinates"]]
gw = [float(w) for w in full["properties"]["widths_m"]]
z_raw = [float(z) for z in ej["z_raw_m"]]
lw = [float(w) for w in lj["widths_m"]]
n0 = len(coords)
assert len(gw) == len(z_raw) == len(lw) == n0 and coords[0] == coords[-1], "the committed files disagree"
origin = (float(lj["origin"]["lon"]), float(lj["origin"]["lat"]))
elev0 = float(lj["origin"]["elev_m"])
cap = float((cfg.get("road_profile") or {}).get("max_grade_pct", 9.0))
med = float((cfg.get("road_profile") or {}).get("despike_window_m", hf.MEDIAN_WINDOW_M))


def profile(zr, cc):
    seg = [haversine(cc[i - 1], cc[i]) for i in range(1, len(cc))]
    z, _ = hf.profile_along(zr, seg, grade_cap_pct=cap, median_m=med, closed=True, close_seg_m=None)
    return z, seg


# --- controls: the stages' code reproduces the committed files ---------------------------------------------------------
z0s, _ = profile(z_raw, coords)
dev_prof = max(abs(a - b) for a, b in zip(z0s, ej["z_smooth_m"]))
loc0 = project_to_local(coords, z0s, origin, elev0)
dev_proj = max(max(abs(a - b) for a, b in zip(p, q)) for p, q in zip(loc0, lj["points_xyz_m"]))
print(f"[gm-loop] controls: profile reproduces z_smooth to {dev_prof:.4f} m, projection the points to {dev_proj:.4f} m")
assert dev_prof <= 0.0101 and dev_proj <= 0.0101, "the stages do not reproduce the committed line"
assert gw == lw, "geojson and local widths differ"

# --- the splice ---------------------------------------------------------------------------------------------------------
phi = math.radians(origin[1])
MLON = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
MLAT = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)


def m(lon, lat):
    return ((lon - origin[0]) * MLON, (lat - origin[1]) * MLAT)


def ll(x, y):
    return (origin[0] + x / MLON, origin[1] + y / MLAT)


def nearest(lon, lat, lo, hi):
    p = m(lon, lat)
    return min(range(lo, hi), key=lambda i: math.dist(m(*coords[i]), p))


fa, fb = fixes[FIX_A], fixes[FIX_B]
a = nearest(fa["lon"], fa["lat"], 0, n0 - 1)
b = nearest(fb["lon"], fb["lat"], a + 1, n0 - 1)
oj = json.loads(ORTHO.read_text(encoding="utf-8"))
tr = [m(*q) for q in oj["lonlat"]]
pa, pb = m(*coords[a]), m(*coords[b])
# the joins: the trace's first / last metres were not re-centred (they meet our fixes) and leave the kept line at a kink
# (3 m turns -16 / +30 / +15 deg on the first try); the piece within BLEND_M of each end is a cubic Hermite from the kept
# line's own heading to the trace's heading BLEND_M in
BLEND_M = 30.0                # [invented] past the ortho re-centring's first 12 m (held on the trace), whose seam jogged


def unit(v):
    L_ = math.hypot(*v) or 1.0
    return (v[0] / L_, v[1] / L_)


def arc_index(P, dist):
    acc = 0.0
    for i in range(1, len(P)):
        acc += math.dist(P[i - 1], P[i])
        if acc >= dist:
            return i
    return len(P) - 1


def hermite(p0, t0, p1, t1, n):
    c = math.dist(p0, p1)
    out = []
    for k in range(1, n):
        u = k / n
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        out.append((h00 * p0[0] + h10 * c * t0[0] + h01 * p1[0] + h11 * c * t1[0],
                    h00 * p0[1] + h10 * c * t0[1] + h01 * p1[1] + h11 * c * t1[1]))
    return out


ia_ = arc_index(tr, BLEND_M)
ib_ = len(tr) - 1 - arc_index(tr[::-1], BLEND_M)
ta = unit((pa[0] - m(*coords[a - 1])[0], pa[1] - m(*coords[a - 1])[1]))
tb = unit((m(*coords[b + 1])[0] - pb[0], m(*coords[b + 1])[1] - pb[1]))
t_ia = unit((tr[ia_ + 1][0] - tr[ia_ - 1][0], tr[ia_ + 1][1] - tr[ia_ - 1][1]))
t_ib = unit((tr[ib_ + 1][0] - tr[ib_ - 1][0], tr[ib_ + 1][1] - tr[ib_ - 1][1]))
poly = ([pa] + hermite(pa, ta, tr[ia_], t_ia, 12) + tr[ia_:ib_ + 1] + hermite(tr[ib_], t_ib, pb, tb, 12) + [pb])
cum = [0.0]
for p, q in zip(poly, poly[1:]):
    cum.append(cum[-1] + math.dist(p, q))
L = cum[-1]
nseg = max(2, round(L / STEP_M))


def at(s):
    k = max(1, min(len(cum) - 1, next((i for i, c in enumerate(cum) if c >= s), len(cum) - 1)))
    f = (s - cum[k - 1]) / max(1e-9, cum[k] - cum[k - 1])
    return (poly[k - 1][0] + f * (poly[k][0] - poly[k - 1][0]), poly[k - 1][1] + f * (poly[k][1] - poly[k - 1][1]))


new_m = [at(L * k / nseg) for k in range(1, nseg)]
# a light smoothing of the new piece (the ortho re-centring leaves 3 m turns of 12-17 deg at single stations; the intake's
# line_precomp, 2 P - S(P), would sharpen them): SMOOTH_PASSES binomial [1 2 1] passes with the joins fixed, sigma ~1.4
# stations (4.2 m) [invented], pulling the inner turn's ~20 m radius inside by ~sigma^2 / 2R = 0.45 m
SMOOTH_PASSES = 4
for _ in range(SMOOTH_PASSES):
    ext = [pa] + new_m + [pb]
    new_m = [((ext[k - 1][0] + 2 * ext[k][0] + ext[k + 1][0]) / 4, (ext[k - 1][1] + 2 * ext[k][1] + ext[k + 1][1]) / 4)
             for k in range(1, len(ext) - 1)]
new_ll = [ll(*p) for p in new_m]

# widths: the ortho's pavement widths (2 m stations along its own line), finalize.py's rules, to_fixes.py's clamp
raw = oj["pavement_width_m"]
good = [w for w in raw if w and W_VALID[0] <= w <= W_VALID[1]]
wmed = statistics.median(good)
wv = [w if (w and W_VALID[0] <= w <= W_VALID[1]) else wmed for w in raw]
wv = [sorted(wv[max(0, i - W_MED_K):i + W_MED_K + 1])[len(wv[max(0, i - W_MED_K):i + W_MED_K + 1]) // 2]
      for i in range(len(wv))]
wv = [min(W_CLAMP[1], max(W_CLAMP[0], w)) for w in wv]
tcum = [0.0]
for p, q in zip(tr, tr[1:]):
    tcum.append(tcum[-1] + math.dist(p, q))
new_w = []
for k, p in enumerate(new_m, start=1):
    s = L * k / nseg
    f = s / L
    st = f * tcum[-1]
    j = max(1, min(len(tcum) - 1, next((i for i, c in enumerate(tcum) if c >= st), len(tcum) - 1)))
    g = (st - tcum[j - 1]) / max(1e-9, tcum[j] - tcum[j - 1])
    w = wv[j - 1] + g * (wv[j] - wv[j - 1])
    if s < TAPER_M:
        w = gw[a] + (w - gw[a]) * s / TAPER_M
    elif L - s < TAPER_M:
        w = gw[b] + (w - gw[b]) * (L - s) / TAPER_M
    new_w.append(round(w, 2))

# raw heights: native 3DEP off the committed corridor (inverse distance over the 4 nearest)
corr = json.loads((D / "corridor.elev.json").read_text(encoding="utf-8"))
lat0c = corr["stations_lonlat"][0][1]
mlon_c, mlat_c = 111_320.0 * math.cos(math.radians(lat0c)), 110_540.0
SP = corr["stations_lonlat"]
buck = {}
for i2, (slon, slat) in enumerate(SP):
    a2, b2 = SP[max(i2 - 1, 0)], SP[min(i2 + 1, len(SP) - 1)]
    tx_, tz_ = (b2[0] - a2[0]) * mlon_c, (b2[1] - a2[1]) * mlat_c
    L_ = math.hypot(tx_, tz_) or 1.0
    nx_, nz_ = -tz_ / L_, tx_ / L_
    for off, zz in zip(corr["offsets"], corr["z"][i2]):
        if zz is None:
            continue
        qx, qz = m(slon + nx_ * off / mlon_c, slat + nz_ * off / mlat_c)
        buck.setdefault((int(qx // 10), int(qz // 10)), []).append((qx, qz, float(zz)))


def g3dep(x, z):
    near = []
    for gx in range(int(x // 10) - 1, int(x // 10) + 2):
        for gz in range(int(z // 10) - 1, int(z // 10) + 2):
            near += buck.get((gx, gz), ())
    near.sort(key=lambda q: (q[0] - x) ** 2 + (q[1] - z) ** 2)
    near = near[:4]
    if not near:
        raise SystemExit(f"[gm-loop] no corridor 3DEP near ({x:.1f}, {z:.1f})")
    w = [1.0 / max(1e-6, (q[0] - x) ** 2 + (q[1] - z) ** 2) for q in near]
    return sum(wi * q[2] for wi, q in zip(w, near)) / sum(w), math.sqrt((near[0][0] - x) ** 2 + (near[0][1] - z) ** 2)


gz = [g3dep(*p) for p in new_m]
new_z = [round(v, 2) for v, _ in gz]
near_max = max(d for _, d in gz)
# the control for the corridor read: at the kept stations next to the splice, the committed sample vs the corridor's
ctrl = [abs(g3dep(*m(*coords[i]))[0] - z_raw[i]) for i in list(range(max(0, a - 20), a + 1)) + list(range(b, b + 21))]

C = coords[:a + 1] + new_ll + coords[b:]
W = gw[:a + 1] + new_w + gw[b:]
ZR = z_raw[:a + 1] + new_z + z_raw[b:]
zs, seg = profile(ZR, C)
loc = project_to_local(C, zs, origin, elev0)
dist = [0.0]
for d in seg:
    dist.append(dist[-1] + d)
grades = [abs(zs[i] - zs[i - 1]) / max(1e-6, seg[i - 1]) * 100 for i in range(1, len(C))]
climb = sum(max(0.0, zs[i] - zs[i - 1]) for i in range(1, len(zs)))
stats = {"min_m": round(min(zs), 1), "max_m": round(max(zs), 1), "range_m": round(max(zs) - min(zs), 1),
         "total_climb_m": round(climb, 1), "max_grade_pct": round(max(grades), 1),
         "mean_grade_pct": round(sum(grades) / len(grades), 2), "lap_m": round(dist[-1], 1)}

OUT.mkdir(parents=True, exist_ok=True)
g2 = json.loads(json.dumps(gj))
f2 = next(f for f in g2["features"] if f["properties"].get("kind") == "full")
f2["geometry"]["coordinates"] = [list(c) for c in C]
f2["properties"].update({"widths_m": W, "point_count": len(C), "length_m": round(dist[-1], 1),
                         "default_width_m": round(statistics.median(W), 2)})
(OUT / "centerline.geojson").write_text(json.dumps(g2), encoding="utf-8")
e2 = dict(ej)
e2.update({"point_count": len(C), "distance_m": [round(x, 1) for x in dist], "z_raw_m": ZR,
           "z_smooth_m": [round(v, 2) for v in zs], "stats": stats})
(OUT / "centerline.elevation.json").write_text(json.dumps(e2), encoding="utf-8")
xs, ys_, zz_ = [p[0] for p in loc], [p[1] for p in loc], [p[2] for p in loc]
l2 = {"frame": lj["frame"], "origin": lj["origin"], "true_north_rotation_deg": lj.get("true_north_rotation_deg", 0.0),
      "extent_x_m": round(max(xs) - min(xs), 1), "extent_z_m": round(max(zz_) - min(zz_), 1),
      "height_m": round(max(ys_) - min(ys_), 1), "point_count": len(loc),
      "points_xyz_m": [[round(x, 2), round(y, 2), round(z, 2)] for x, y, z in loc], "widths_m": W}
(OUT / "centerline.local.json").write_text(json.dumps(l2), encoding="utf-8")
for f in ("heightfield.npy", "heightfield.meta.json", "corridor.elev.json"):
    shutil.copyfile(D / f, OUT / f)
rep = {"_doc": __doc__.split("\n\n")[0], "splice": {"fix_a": FIX_A, "fix_b": FIX_B, "geojson_a": a, "geojson_b": b,
       "dropped_points": b - a - 1, "dropped_m": round(sum(haversine(coords[i - 1], coords[i]) for i in range(a + 1, b + 1)), 1),
       "new_points": len(new_ll), "new_m": round(L, 1), "join_blend_m": BLEND_M,
       "smooth_passes": SMOOTH_PASSES},
       "lap_m": {"was": round(sum(haversine(coords[i - 1], coords[i]) for i in range(1, n0)), 1), "now": round(dist[-1], 1)},
       "widths_new_m": {"min": min(new_w), "p50": statistics.median(new_w), "max": max(new_w),
                        "ortho_valid_median": round(wmed, 2)},
       "z_raw_new": {"min": min(new_z), "max": max(new_z), "nearest_sample_max_m": round(near_max, 2),
                     "control_kept_vs_corridor_m": {"p50": round(statistics.median(ctrl), 3), "max": round(max(ctrl), 3)}},
       "controls": {"profile_dev_m": round(dev_prof, 4), "projection_dev_m": round(dev_proj, 4)},
       "stats": stats}
(OUT / "splice.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
print(f"[gm-loop] {json.dumps({k: rep[k] for k in ('splice', 'lap_m', 'widths_new_m', 'z_raw_new')})}")

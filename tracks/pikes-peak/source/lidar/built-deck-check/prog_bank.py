"""Progressive banking from the lidar fits already on disk (no new lidar read).

Two plane fits of the SAME 2018 ground returns exist per station:
  - crossfall.lidar.json: the camber survey, one plane over the line's centre +-6.5 m (13 m), class 2;
  - wall_right.json road_slope_pct: lidar_wall.py's plane over a 3 m band from 7.5 to 4.5 m inside the right lane edge of
    the source line (half-width 7.5 m): i.e. 0 .. +3 m right (outside) of the centre line, class 2, trimmed.
If the bank steepened toward the wall the outer band would read steeper than the 13 m plane.
Also: the 13 m plane's residual sd bounds any curvature across it.
"""
import json, math, sys
import numpy as np

W = str(__import__("pathlib").Path(__file__).resolve().parents[5]) + "/" + "tracks/pikes-peak/"
cf = json.load(open(W + "source/lidar/camber-survey/crossfall.json"))
fits = json.load(open(W + "source/lidar/camber-survey/crossfall.lidar.json"))["fits"]
wall = json.load(open(W + "source/lidar/wall-survey/wall_right.json"))
fin = json.load(open(W + "data/finished_centerline.json"))
loc = json.load(open(W + "data/centerline.local.json"))


def stations(pts, step=3.0):
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    out, s, j = [], 0.0, 0
    while s < st[-1] - 1e-6:
        while j < len(st) - 2 and st[j + 1] < s:
            j += 1
        t = (s - st[j]) / ((st[j + 1] - st[j]) or 1e-9)
        a, b = pts[j], pts[j + 1]
        out.append((a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t))
        s += step
    return np.array(out)

fpts = fin.get("points_xyz_m") or fin.get("points")
print("finished keys", list(fin.keys())[:8], len(fpts))
A = stations([[p[0], p[1], -p[2]] for p in fpts])          # survey stations (finished line, kn5 frame)
B = stations(loc["points_xyz_m"])   # wall stations (local ENU)
print(len(A), len(B), len(cf["station_m"]), len(wall["stations"]))
# frames: finished is kn5 frame (mirror false) == ENU? check nearest distances
from scipy.spatial import cKDTree
d, i = cKDTree(B).query(A)
print("survey->wall station match: median %.2f m, max %.2f m" % (np.median(d), d.max()))
full = np.array([f[0][0] if f[0] else np.nan for f in fits])
sdv = np.array([f[0][1] if f[0] else np.nan for f in fits])
band = np.array([wall["stations"][k].get("road_slope_pct", np.nan) if wall["stations"][k].get("road_slope_pct") is not None else np.nan for k in i])
ok = np.isfinite(full) & np.isfinite(band) & (d < 2.0)
diff = np.abs(band[ok]) - np.abs(full[ok])   # + = outer band steeper
print("stations compared", ok.sum())
print("outer band (0..+3 m) |slope| minus 13 m plane |slope|, %%-pts: mean %.2f median %.2f p10 %.2f p90 %.2f" % (
    diff.mean(), np.median(diff), np.percentile(diff, 10), np.percentile(diff, 90)))
s = np.array(cf["station_m"])[ok]
secs = [(0, 215, "front stretch/dogleg"), (215, 265, "T1-2 ramp in"), (265, 680, "T1-2 plateau"), (680, 730, "T2 exit"),
        (730, 960, "back stretch"), (960, 1010, "T3 ramp in"), (1010, 1450, "T3-4 plateau"), (1450, 1500, "T4 exit"),
        (1500, 1666, "front dogleg")]
rows = []
for a, b, n in secs:
    m = (s >= a) & (s < b)
    rows.append((n, a, b, int(m.sum()), float(np.mean(np.abs(full[ok][m]))), float(np.mean(np.abs(band[ok][m]))), float(np.mean(diff[m]))))
    print("%-22s s %4d-%4d n=%3d  13m plane %.2f %%  outer band %.2f %%  diff %+.2f" % rows[-1][0:1] + rows[-1][1:] if False else
          "%-22s s %4d-%4d n=%3d  13m plane %.2f %%  outer band %.2f %%  diff %+.2f" % rows[-1])
# curvature bound from the residual sd: z = b x + a x^2 over x in [-L, L]; rms of (x^2 - L^2/3) = L^2 * sqrt(4/45)
L = 6.5
sd_med = np.nanmedian(sdv)
a_max = sd_med / (L * L * math.sqrt(4 / 45))
print("13 m plane residual sd median %.4f m (p90 %.4f); if ALL of it were curvature, slope change across 13 m <= %.2f %%-pts"
      % (sd_med, np.nanpercentile(sdv, 90), 100 * 2 * a_max * 2 * L))
json.dump({"rows": rows, "stations": int(ok.sum()), "diff_mean": float(diff.mean()), "diff_median": float(np.median(diff)),
           "diff_p10": float(np.percentile(diff, 10)), "diff_p90": float(np.percentile(diff, 90)),
           "sd_median_m": float(sd_med), "slope_change_bound_pct": float(100 * 2 * a_max * 2 * L)},
          open(str(__import__("pathlib").Path(__file__).resolve().parent) + "/" + "prog_bank.json", "w"), indent=1)

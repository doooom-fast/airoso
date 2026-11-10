"""Part 1: the BUILT deck's cross-slope against the 2018 lidar survey, station by station.

    python bank_check.py <workshop> [<label>]

Reads <ws>/data/track.obj (the road kn5's own gate OBJ), the survey (tracks/pikes-peak/source/lidar/camber-survey:
crossfall.json tilt_pct = filled/smoothed/rate-limited, crossfall.lidar.json raw plane fits) keyed by POSITION
(crossfall.lm.json points_xz: the survey stations in the engine frame), and 0077's plateau windows
(tracks/pikes-peak/track.config.json road_profile.cambers) for comparison.
Per station: the built deck's least-squares plane over the survey's own band (centre +-6.5 m, 0.5 m steps), and the
inner / outer halves separately; the outside (right) edge vs inside (left) edge.
"""
import json, math, sys
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent) + "/")
from objdeck import load_obj, Surface

REPO = str(__import__("pathlib").Path(__file__).resolve().parents[5]) + "/"
ws = sys.argv[1]; label = sys.argv[2] if len(sys.argv) > 2 else ws.rstrip("/").split("/")[-1]
cf = json.load(open(REPO + "tracks/pikes-peak/source/lidar/camber-survey/crossfall.json"))
fits = json.load(open(REPO + "tracks/pikes-peak/source/lidar/camber-survey/crossfall.lidar.json"))["fits"]
pos = json.load(open(REPO + "tracks/pikes-peak-lm/data/crossfall.lm.json"))["points_xz"]
V, F = load_obj(ws + "/data/track.obj", lambda n: n is not None and n.startswith("1ROAD"))
road = Surface(V, np.concatenate(list(F.values())))
S = np.array(cf["station_m"]); tilt = np.array(cf["tilt_pct"]); raw = np.array([f[0][0] if f[0] else np.nan for f in fits])
P = np.array(pos)
n = len(P)
T = np.roll(P, -1, 0) - np.roll(P, 1, 0); T /= np.linalg.norm(T, axis=1)[:, None]
L = np.c_[-T[:, 1], T[:, 0]]      # left normal in (x=E, z=N)
offs = np.arange(-6.5, 6.51, 0.5)  # + = left
built, inner, outer, cover = [], [], [], []
for k in range(n):
    xs = P[k, 0] + offs * L[k, 0]; zs = P[k, 1] + offs * L[k, 1]
    hs = np.array([road.h(x, z) for x, z in zip(xs, zs)])
    ok = np.isfinite(hs); cover.append(ok.mean())
    def fit(m):
        m = m & ok
        if m.sum() < 4:
            return np.nan
        return 100 * np.polyfit(offs[m], hs[m], 1)[0]
    built.append(fit(np.ones_like(ok))); inner.append(fit(offs >= 0)); outer.append(fit(offs <= 0))
built = np.array(built); inner = np.array(inner); outer = np.array(outer)
# 0077's windows
cfg = json.load(open(REPO + "tracks/pikes-peak/track.config.json"))
camb = (cfg.get("road_profile") or {}).get("cambers") or []


sys.path.insert(0, REPO)
from scripts.geometry.profile import build_profile
_, bank_at, _act = build_profile(cfg.get("road_profile"))


def win(s):
    return 100 * math.tan(bank_at(s))
w77 = np.array([win(s) for s in S]) if camb else None
ok = np.isfinite(built)
e_tilt = built - tilt; e_raw = built - raw


def stats(e, m):
    e = e[m & np.isfinite(e)]
    return {"mean": round(float(e.mean()), 3), "rms": round(float(np.sqrt((e ** 2).mean())), 3), "worst": round(float(e[np.argmax(np.abs(e))]), 3)}
worst_k = int(np.nanargmax(np.abs(e_raw)))
rep = {"label": label, "stations": int(ok.sum()), "coverage_min": round(float(min(cover)), 3),
       "built_vs_survey_tilt_pct": stats(e_tilt, ok), "built_vs_raw_lidar_pct": stats(e_raw, ok),
       "worst_vs_raw": {"s": float(S[worst_k]), "built": round(float(built[worst_k]), 2), "raw": round(float(raw[worst_k]), 2)},
       "survey_noise": {"raw_minus_tilt_rms": round(float(np.sqrt(np.nanmean((raw - tilt) ** 2))), 3),
                        "raw_station_to_station_sd": round(float(np.nanstd(np.diff(raw)) / math.sqrt(2)), 3)},
       "outside_edge_up": int(np.sum(built[ok] < 0)), "inner_minus_outer_half_pct": stats(inner - outer, ok)}
secs = [(0, 215, "front stretch / dogleg"), (215, 265, "T1 ramp-in"), (265, 680, "T1-2 plateau"), (680, 730, "T2 exit"),
        (730, 960, "back stretch"), (960, 1010, "T3 ramp-in"), (1010, 1450, "T3-4 plateau"), (1450, 1500, "T4 exit"),
        (1500, 1666, "front dogleg")]
rep["sections"] = []
for a, b, nm in secs:
    m = (S >= a) & (S < b) & ok
    row = {"section": nm, "s": [a, b], "lidar_raw_pct": round(float(np.nanmean(raw[m])), 2), "built_pct": round(float(np.mean(built[m])), 2),
           "built_deg": round(math.degrees(math.atan(abs(np.mean(built[m])) / 100)), 2)}
    if w77 is not None:
        row["0077_windows_pct"] = round(float(np.mean(w77[m])), 2)
    rep["sections"].append(row)
# ramps: where |tilt| crosses 15 % and 9 % (lidar vs built)


def crossings(v, thr):
    a = np.abs(v) >= thr
    return [float(S[i + 1]) for i in range(len(a) - 1) if a[i] != a[i + 1]]
rep["ramps"] = {f"{thr}%": {"lidar": crossings(raw, thr), "built": crossings(built, thr)} for thr in (9.0, 15.0)}
if w77 is not None:
    rep["0077_windows_vs_raw_lidar_pct"] = stats(w77 - raw, np.isfinite(raw))
json.dump({"report": rep, "per_station": {"s": S.tolist(), "built": [None if not np.isfinite(b) else round(float(b), 3) for b in built],
           "raw": raw.tolist(), "tilt": tilt.tolist(), "inner": [None if not np.isfinite(b) else round(float(b), 3) for b in inner],
           "outer": [None if not np.isfinite(b) else round(float(b), 3) for b in outer]}},
          open(str(__import__("pathlib").Path(__file__).resolve().parent) + "/" + f"bank_check.{label}.json", "w"), indent=1)
print(json.dumps(rep, indent=1))

"""College Ave "realism+": the DESIGN cross-section per centreline vertex, from the measured edges and heights
(ledger 0055 "Bounded proof" step 3 input; stage A = this file and a standalone proof scene, nothing in the build).

    <blender python> college_design.py        (after college_edges.py)

Per station v ZONE0..ZONE1, four control points across the road, west to east:
    SBo  southbound outer edge      SBi  southbound inner edge (the island's west side)
    NBi  northbound inner edge      NBo  northbound outer edge
Where the island exists (the main read, ISLAND0..ISLAND1) SBi and NBi are the measured island edges; outside it they
are one point (the crown) at the built road's centre, so the same four points describe one slab.
  edges    measured (college_edges.json); a station whose edge sits more than OUTLIER_M off the 31-station median, and
           every edge at the stations in UNMEASURED, is dropped and bridged from its neighbours (flag "bridged");
           then a moving average over EDGE_AVG stations.
  heights  the lidar's median within HEIGHT_HALF_M of a point half a metre inside each edge, then a moving average
           over HEIGHT_AVG stations (the survey is of the real pavement: light smoothing only).
  ends     over BLEND_ST stations at each end the section is blended into the road as built, so the design meets
           the untouched road in position and height.
Writes college_design.json (offsets, heights, world x / z of every control point, flags, and the checks: long grade,
crossfall, bank slope) for the proof scene and the picture."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ZONE0, ZONE1 = 1130, 1480          # [chosen] where northbound over southbound falls under 0.3 m at both ends
ISLAND0, ISLAND1 = 1172, 1444      # the main island as read (college_edges.json)
UNMEASURED = range(1297, 1301)     # under the trees (the Mac: "treat v1297-1300 as unmeasured; bridge them")
OUTLIER_M = 2.0                    # [invented]
EDGE_AVG = 11                      # stations, about 33 m [invented]
HEIGHT_AVG = 5                     # stations, about 15 m [invented]
HEIGHT_HALF_M = 1.0                # [invented]
BLEND_ST = 10                      # stations, about 30 m [invented]
NOSE_ST = 3                        # stations over which the island's width runs out at each nose [invented]

L = json.loads((HERE / "college_xsec.lidar.g10.json").read_text(encoding="utf-8"))
E = {r["v"]: r for r in json.loads((HERE / "college_edges.json").read_text(encoding="utf-8"))["stations"]}
off = np.array(L["offsets_m"])
st = L["stations"]
V = np.array(st["v"])
H = np.array([[np.nan if v is None else v for v in row] for row in L["h_navd88_m"]], float) - 100.8
H[(np.array(L["flags"], int) & 17) > 0] = np.nan
B = np.load(HERE / "college_built_y.npy")
row_of = {int(v): i for i, v in enumerate(V)}
vs = np.arange(ZONE0, ZONE1 + 1)
n = len(vs)
KEYS = ("sb_outer_m", "sb_inner_m", "nb_inner_m", "nb_outer_m")


def run_median(a, w):
    out = np.full(len(a), np.nan)
    h = w // 2
    for k in range(len(a)):
        x = a[max(0, k - h):k + h + 1]
        x = x[~np.isnan(x)]
        if len(x) >= 3:
            out[k] = np.median(x)
    return out


def mov_avg(a, w):
    out = a.copy()
    h = w // 2
    for k in range(len(a)):
        out[k] = np.mean(a[max(0, k - h):k + h + 1])
    return out


def bridge(a):
    ok = ~np.isnan(a)
    return np.interp(np.arange(len(a)), np.where(ok)[0], a[ok]) if ok.any() else a


built_w = np.array([E[v]["built_to_m"] if v in E and E[v]["built_to_m"] is not None else np.nan for v in vs])
built_e = np.array([E[v]["built_from_m"] if v in E and E[v]["built_from_m"] is not None else np.nan for v in vs])
built_c = 0.5 * (built_w + built_e)
island = (vs >= ISLAND0) & (vs <= ISLAND1)
raw = {}
bridged = {}
for key in KEYS:
    a = np.array([E[v].get(key, np.nan) if v in E else np.nan for v in vs], float)
    a[~island] = np.nan
    a[np.isin(vs, list(UNMEASURED))] = np.nan
    med = run_median(a, 31)
    a[np.abs(a - med) > OUTLIER_M] = np.nan
    raw[key] = a.copy()
    a2 = a.copy()
    if key == "sb_outer_m":
        a2[~island] = built_w[~island]
    elif key == "nb_outer_m":
        a2[~island] = built_e[~island]
    else:
        a2[~island] = built_c[~island]
    bridged[key] = np.isnan(a2)
    raw[key + "_filled"] = bridge(a2)
edge = {k: mov_avg(raw[k + "_filled"], EDGE_AVG) for k in KEYS}
# the island's width runs out to nothing at each nose
wmid = edge["sb_inner_m"] - edge["nb_inner_m"]
k0 = int(np.where(island)[0][0])
k1 = int(np.where(island)[0][-1])
mid = 0.5 * (edge["sb_inner_m"] + edge["nb_inner_m"])
for k in range(n):
    f = 1.0
    if k < k0 or k > k1:
        f = 0.0
    elif k - k0 < NOSE_ST:
        f = (k - k0 + 1) / (NOSE_ST + 1)
    elif k1 - k < NOSE_ST:
        f = (k1 - k + 1) / (NOSE_ST + 1)
    half = max(0.0, 0.5 * wmid[k]) * f
    edge["sb_inner_m"][k] = mid[k] + half
    edge["nb_inner_m"][k] = mid[k] - half
has_island = (edge["sb_inner_m"] - edge["nb_inner_m"]) > 0.05

INSIDE = {"sb_outer_m": -0.5, "sb_inner_m": +0.5, "nb_inner_m": -0.5, "nb_outer_m": +0.5}


def height(v, o):
    i = row_of[int(v)]
    m = np.abs(off - o) <= HEIGHT_HALF_M
    x = H[i, m]
    x = x[~np.isnan(x)]
    return float(np.median(x)) if len(x) else np.nan


ymeas = {}
for key in KEYS:
    a = np.array([height(v, edge[key][k] + INSIDE[key]) for k, v in enumerate(vs)])
    ymeas[key] = mov_avg(bridge(a), HEIGHT_AVG)


def built_at(v, o):
    i = row_of[int(v)]
    j = int(np.argmin(np.abs(off - o)))
    for d in range(0, 6):
        for jj in (j - d, j + d):
            if 0 <= jj < len(off) and not np.isnan(B[i, jj]):
                return float(B[i, jj])
    return np.nan


# blend into the road as built at both ends
wgt = np.ones(n)
for k in range(n):
    wgt[k] = min(1.0, (k + 1) / (BLEND_ST + 1), (n - k) / (BLEND_ST + 1))
y = {}
for key in KEYS:
    yb = np.array([built_at(v, edge[key][k] + INSIDE[key]) for k, v in enumerate(vs)])
    yb = bridge(yb)
    y[key] = wgt * ymeas[key] + (1 - wgt) * yb
    y[key + "_built"] = yb

X = np.array(st["x"])
Z = np.array(st["z"])
NX = np.array(st["nx"])
NZ = np.array(st["nz"])
S = np.array(st["s_m"])
rows = []
for k, v in enumerate(vs):
    i = row_of[int(v)]
    r = {"v": int(v), "s_m": float(S[i]), "island": bool(has_island[k]), "blend": round(float(wgt[k]), 3)}
    for key in KEYS:
        name = key[:-2]
        o = float(edge[key][k])
        r[name] = {"offset_m": round(o, 2), "y": round(float(y[key][k]), 3), "y_built": round(float(y[key + "_built"][k]), 3),
                   "x": round(float(X[i] + o * NX[i]), 3), "z": round(float(Z[i] + o * NZ[i]), 3),
                   "bridged": bool(bridged[key][k])}
    rows.append(r)

# --- checks ------------------------------------------------------------------------------------------------------------
ds = np.diff([r["s_m"] for r in rows])


def grade(a):
    return np.abs(np.diff(a) / ds) * 100.0


nb_c = 0.5 * (y["nb_inner_m"] + y["nb_outer_m"])
sb_c = 0.5 * (y["sb_inner_m"] + y["sb_outer_m"])
nb_w = edge["nb_inner_m"] - edge["nb_outer_m"]
sb_w = edge["sb_outer_m"] - edge["sb_inner_m"]
nb_x = (y["nb_outer_m"] - y["nb_inner_m"]) / np.maximum(0.1, nb_w) * 100.0      # + = rises toward the outside (east)
sb_x = (y["sb_outer_m"] - y["sb_inner_m"]) / np.maximum(0.1, sb_w) * 100.0      # + = rises toward the outside (west)
step = y["nb_inner_m"] - y["sb_inner_m"]
wm = edge["sb_inner_m"] - edge["nb_inner_m"]
bank = np.where(has_island, step / np.maximum(0.5, wm) * 100.0, np.nan)
chk = {
    "stations": n, "island_stations": int(has_island.sum()),
    "bridged_edge_points": {k[:-2]: int(bridged[k].sum()) for k in KEYS},
    "long_grade_pct": {"northbound_max": round(float(grade(nb_c).max()), 2), "southbound_max": round(float(grade(sb_c).max()), 2),
                       "built_centre_max": round(float(grade(0.5 * (y["sb_inner_m_built"] + y["nb_inner_m_built"])).max()), 2)},
    "crossfall_pct": {"northbound_min": round(float(nb_x.min()), 2), "northbound_max": round(float(nb_x.max()), 2),
                      "southbound_min": round(float(sb_x.min()), 2), "southbound_max": round(float(sb_x.max()), 2)},
    "width_m": {"northbound_median": round(float(np.median(nb_w[has_island])), 2), "southbound_median": round(float(np.median(sb_w[has_island])), 2),
                "island_max": round(float(wm.max()), 2)},
    "northbound_over_southbound_m": {"max": round(float(step.max()), 2), "at_v": int(vs[int(step.argmax())])},
    "bank_slope_pct": {"max": round(float(np.nanmax(bank)), 1), "at_v": int(vs[int(np.nanargmax(bank))]),
                       "median": round(float(np.nanmedian(bank)), 1)},
    "design_minus_built_m": {"northbound_outer_max": round(float((y["nb_outer_m"] - y["nb_outer_m_built"]).max()), 2),
                             "southbound_outer_max_abs": round(float(np.abs(y["sb_outer_m"] - y["sb_outer_m_built"]).max()), 2),
                             "at_zone_ends": [round(float(y[k][0] - y[k + "_built"][0]), 3) for k in KEYS] +
                                             [round(float(y[k][-1] - y[k + "_built"][-1]), 3) for k in KEYS]},
}
(HERE / "college_design.json").write_text(json.dumps({
    "what": "College Ave realism+: the design cross-section per centreline vertex (stage A; nothing in the build uses it yet)",
    "frame": "offset + = left of travel = west on College northbound; x east, z north; y = NAVD88 - 100.8",
    "params": {"ZONE": [ZONE0, ZONE1], "ISLAND": [ISLAND0, ISLAND1], "UNMEASURED": [UNMEASURED.start, UNMEASURED.stop - 1],
               "OUTLIER_M": OUTLIER_M, "EDGE_AVG": EDGE_AVG, "HEIGHT_AVG": HEIGHT_AVG, "HEIGHT_HALF_M": HEIGHT_HALF_M,
               "BLEND_ST": BLEND_ST, "NOSE_ST": NOSE_ST, "_doc": "ZONE is [chosen], UNMEASURED is the Mac's call, the rest [invented]"},
    "checks": chk, "stations": rows}, indent=1), encoding="utf-8")
print(json.dumps(chk, indent=1))

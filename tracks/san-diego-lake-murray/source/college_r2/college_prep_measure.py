"""Measure what the prep made of College's ground, on the OBJ college_prep_look_blend.py wrote (no Blender).

    <python with numpy> college_prep_measure.py <obj> [--out <json>]

Everything is sampled straight down: the highest 1GRASS, 1ROAD and 1KERB surface at a plan point.
  bank      the bank's top against the authored plane between its two curb tops (released ground: should be untouched)
  roads     ground against each road's surface (should lie 0.02 m under it everywhere: pinned)
  forks     ground against the fork's pavement inside the old island's footprint (pinned under)
  east      the ground behind the east walk against the road's east edge, and the walk's lip against the ground beside it
  islands   the two College islands that stay: grass or asphalt between the curbs
Frames: engine x east, y up, z north; offsets from the BUILT line, + = west."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OBJ = Path(sys.argv[1])
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
R, F = S["rows"], S["frame"]
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
NOSE, TAIL = R["v"][0], R["v"][-1]
K = {v: k for k, v in enumerate(R["v"])}
FK = {v: k for k, v in enumerate(R["fork_v"])}
O = R["offsets_m"]
FV0 = F["from_v"]
LIFT, CURB_H, DECK_INSET = 0.10, 0.18, 0.22

verts, tris, kind = [], {"1GRASS": [], "1ROAD": [], "1KERB": []}, None
with open(OBJ, "r", encoding="utf-8") as fh:
    for line in fh:
        c = line[:2]
        if c == "v ":
            p = line.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif c == "o ":
            kind = next((k for k in tris if line[2:].strip().upper().startswith(k)), None)
        elif c == "f " and kind:
            ids = [int(t) - 1 for t in line.split()[1:]]
            for k in range(1, len(ids) - 1):
                tris[kind].append((ids[0], ids[k], ids[k + 1]))
V = np.array(verts)
T = {k: np.array(v, dtype=np.int64) for k, v in tris.items()}
BOX = {}
for k, t in T.items():
    x, z = V[t][:, :, 0], V[t][:, :, 2]
    BOX[k] = (x.min(axis=1), x.max(axis=1), z.min(axis=1), z.max(axis=1))
print(f"[measure] {len(V)} vertices; triangles: " + ", ".join(f"{k} {len(t)}" for k, t in T.items()))


def tops(kind_, x, z):
    """every surface height of that kind at (x, z), highest first"""
    x0, x1, z0, z1 = BOX[kind_]
    out = []
    for i in np.nonzero((x0 <= x) & (x1 >= x) & (z0 <= z) & (z1 >= z))[0]:
        a, b, c = V[T[kind_][i]]
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        if l1 >= -1e-9 and l2 >= -1e-9 and 1.0 - l1 - l2 >= -1e-9:
            out.append(l1 * a[1] + l2 * b[1] + (1.0 - l1 - l2) * c[1])
    return sorted(out, reverse=True)


def top(kind_, x, z):
    t = tops(kind_, x, z)
    return t[0] if t else None


def plan(v, off):
    i = v - FV0
    return F["x"][i] + F["nx"][i] * off, F["z"][i] + F["nz"][i] * off


def stat(vals):
    a = np.array([x for x in vals if x is not None])
    if not len(a):
        return None
    return {"n": int(len(a)), "min": round(float(a.min()), 3), "median": round(float(np.median(a)), 3), "max": round(float(a.max()), 3)}


rep = {}
# --- the bank's top against the authored plane ----------------------------------------------------------------------------
dif, missing, worst = [], 0, []
for v in range(NOSE + 3, TAIL - 2):
    k = K[v]
    oe, ow = O["nb_west"][k] + DECK_INSET, O["sb_east"][k] - DECK_INSET
    ye, yw = R["nb_west"][k][1] + CURB_H + 0.005, R["sb_east"][k][1] + CURB_H + 0.005
    if ow - oe < 0.4:
        continue
    for t in (0.15, 0.3, 0.5, 0.7, 0.85):
        o = oe + (ow - oe) * t
        g = top("1GRASS", *plan(v, o))
        if g is None:
            missing += 1
            continue
        d = g - (ye + (yw - ye) * t)
        dif.append(d)
        worst.append((abs(d), v, round(o, 2), round(d, 3)))
worst.sort(reverse=True)
rep["bank_top_minus_authored_m"] = dict(stat(dif) or {}, no_ground_at=missing,
                                        within_2cm=int(sum(1 for d in dif if abs(d) <= 0.02)),
                                        largest=[(v, o, d) for _a, v, o, d in worst[:6]])
# --- ground against each road -------------------------------------------------------------------------------------------------
for nm, keys in (("southbound", ("sb_west", "sb_line", "sb_east")), ("northbound", ("nb_west", "nb_line", "nb_east"))):
    dif, over, none = [], [], 0
    for v in range(NOSE + 1, TAIL):
        k = K[v]
        a, b = O[keys[0]][k], O[keys[2]][k]
        for t in (0.04, 0.12, 0.2, 0.35, 0.5, 0.65, 0.8, 0.88, 0.96):
            o = a + (b - a) * t
            x, z = plan(v, o)
            r = top("1ROAD", x, z)
            if r is None:
                none += 1
                continue
            g = top("1GRASS", x, z)
            if g is None:
                continue
            dif.append(g - r)
            if g > r - 0.005:
                over.append((v, round(o, 2), round(g - r, 3)))
    rep[f"ground_minus_{nm}_road_m"] = dict(stat(dif) or {}, ground_within_5mm_or_over=len(over),
                                            over_by_more_than_1cm=sum(1 for *_x, d in over if d > 0.01),
                                            largest=sorted(over, key=lambda q: -q[2])[:5], no_road_at=none)
# --- the forks: ground against the pavement inside the old island's footprint ----------------------------------------------
dif, over = [], []
for v in list(range(A0 + 2, NOSE - 1)) + list(range(TAIL + 2, A1 - 1)):
    for o in (-3.0, -1.5, 0.0, 1.5, 3.0):
        x, z = plan(v, o)
        r, g = top("1ROAD", x, z), top("1GRASS", x, z)
        if r is None or g is None:
            continue
        dif.append(g - r)
        if g > r - 0.005:
            over.append((v, o, round(g - r, 3)))
rep["fork_ground_minus_pavement_m"] = dict(stat(dif) or {}, ground_within_5mm_or_over=len(over), first=over[:5])
# --- the east side ------------------------------------------------------------------------------------------------------------
EDGE = {}
for v in range(A0 + 1, A1):
    EDGE[v] = R["nb_east"][K[v]][1] if v in K else R["fork_y"][FK[v]][2]
by_d = {}
lip_float = []
for v in range(A0 + 4, A1 - 3, 2):
    hw = F["half_w"][v - FV0]
    for d in (0.5, 1.5, 2.5, 3.3, 4.5, 6.0, 8.0, 12.0):
        g = top("1GRASS", *plan(v, -hw - d))
        if g is not None:
            by_d.setdefault(d, []).append(g - EDGE[v])
    kl = tops("1KERB", *plan(v, -hw - 3.0))            # the walk's back grade just inside its lip
    g = top("1GRASS", *plan(v, -hw - 3.3))
    if kl and g is not None:
        lip_float.append((kl[-1] - g, v))
rep["east_ground_minus_road_edge_m_by_distance_past_the_edge"] = {str(d): stat(x) for d, x in sorted(by_d.items())}
lf = sorted(lip_float, reverse=True)
rep["east_walk_lip_over_the_ground_beside_it_m"] = dict(stat([x for x, _v in lip_float]) or {},
                                                        over_0p10=int(sum(1 for x, _v in lip_float if x > 0.10)),
                                                        largest=[(v, round(x, 3)) for x, v in lf[:6]])
# --- the two College islands that stay ----------------------------------------------------------------------------------------
isl = {}
for nm, rows in (("south, to v1116", range(1098, 1114)), ("north, v1476-1487", range(1479, 1485))):
    dif = []
    for v in rows:
        x, z = plan(v, 0.0)
        r, g = top("1ROAD", x, z), top("1GRASS", x, z)
        if r is not None and g is not None:
            dif.append(g - r)
    isl[nm] = dict(stat(dif) or {}, rows_with_grass_over_the_road=int(sum(1 for d in dif if d >= 0.05)))
rep["islands_that_stay_grass_minus_road_m"] = isl
# --- the bank's curbs ------------------------------------------------------------------------------------------------------------
ck = {"southbound_side": [], "northbound_side": []}
for v in range(NOSE + 3, TAIL - 2, 3):
    k = K[v]
    kw = top("1KERB", *plan(v, O["sb_east"][k] - 0.09))
    ke = top("1KERB", *plan(v, O["nb_west"][k] + 0.09))
    if kw is not None:
        ck["southbound_side"].append(kw - R["sb_east"][k][1])
    if ke is not None:
        ck["northbound_side"].append(ke - R["nb_west"][k][1])
rep["bank_curb_top_over_its_road_edge_m"] = {k: stat(v) for k, v in ck.items()}
print(json.dumps(rep, indent=1))
if OUT:
    OUT.write_text(json.dumps({"what": "College after the prep (college_prep_measure.py)", "obj": str(OBJ), "report": rep}, indent=1), encoding="utf-8")

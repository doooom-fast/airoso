"""Ledger 0054 P2 measures on the BUILT gate OBJs (Blender's python: mathutils KD / BVH). Run:

  blender --background --python-exit-code 1 --python measure_ground.py -- <v018 track.obj> <rehearsal track.obj>
          <rehearsal project> <airoso worktree> <out.json>

1. UNCHANGED LOOP GROUND: every v0.18.0 1GRASS vertex within 150 m of a v0.18.0 1ROAD vertex, against the rehearsal's
   ground surface (1GRASS + GRASS_FAR, ray straight down) - and every rehearsal 1GRASS vertex within 150 m of a road
   against v0.18.0's: |dy| <= 0.05 m, except where the plan names exceptions (beside the two weld mouths). Each
   departure is reported with its distance to the planned north pavement and to J1 / J5.
2. TIER SEAMS: open edges of the rehearsal's terrain (1GRASS + GRASS_FAR, welded at 1 mm), excluding the domain's outer
   border; split by distance to the nearest road vertex (<= 30 m: the road seams the seat cuts, as v0.18.0 has them)
   and the rest (a tier seam): must be 0. The same count on v0.18.0's.
3. LOW CLAUSE: every terrain vertex against 3DEP at its own position (the lattice cache: point samples at lattice and
   break-line keys; elsewhere the 2.5 m base lattice, bilinear, flagged): more than 2 m below = a failure, split by
   pavement distance (the graded near-road band <= 36 m vs beyond); the same on v0.18.0.
4. MESHES: positions per 1GRASS / GRASS_FAR tile.
"""
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import kdtree
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
OLD_OBJ, NEW_OBJ, PROJ, AIR, OUT = (Path(a) for a in argv[:5])


def read_obj(path):
    """{object name: (V local idx -> global), F as global index triples}, all vertices"""
    V = []
    objs = {}
    cur = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            c = ln[:2]
            if c == "v ":
                p = ln.split()
                V.append((float(p[1]), float(p[2]), float(p[3])))
            elif c == "f ":
                p = ln.split()[1:]
                idx = [int(q.split("/")[0]) for q in p]
                idx = [i - 1 if i > 0 else len(V) + i for i in idx]
                for k in range(1, len(idx) - 1):
                    objs[cur].append((idx[0], idx[k], idx[k + 1]))
            elif c == "o " or c == "g ":
                cur = ln.split(None, 1)[1].strip()
                objs.setdefault(cur, [])
    return np.array(V, dtype=np.float64), objs


def pick(objs, prefixes):
    out = []
    for n, F in objs.items():
        if n.upper().startswith(prefixes):
            out += F
    return out


def tile_counts(objs):
    out = {}
    for n, F in objs.items():
        if n.upper().startswith(("1GRASS", "GRASS_FAR")):
            out[n] = len({v for t in F for v in t})
    return out


print("[p2] reading OBJs", flush=True)
Vo, Oo = read_obj(OLD_OBJ)
Vn, On = read_obj(NEW_OBJ)
res = {"tiles_v018": tile_counts(Oo), "tiles_rehearsal": tile_counts(On)}


def road_kd(V, objs):
    rv = sorted({v for t in pick(objs, ("1ROAD",)) for v in t})
    kd = kdtree.KDTree(len(rv))
    for k, v in enumerate(rv):
        kd.insert((V[v][0], V[v][2], 0.0), k)
    kd.balance()
    return kd


def ground_bvh(V, objs, prefixes=("1GRASS", "GRASS_FAR")):
    F = pick(objs, prefixes)
    used = sorted({v for t in F for v in t})
    m = {v: k for k, v in enumerate(used)}
    verts = [(V[v][0], V[v][2], V[v][1]) for v in used]
    return BVHTree.FromPolygons(verts, [(m[a], m[b], m[c]) for a, b, c in F]), F


kdo, kdn = road_kd(Vo, Oo), road_kd(Vn, On)
bo, Fo = ground_bvh(Vo, Oo)
bn, Fn = ground_bvh(Vn, On)

# planned north pavement (local = engine frame x E, z N) and the two weld nodes
X = json.loads((PROJ / "data" / "expansion.north.json").read_text(encoding="utf-8"))
pp = []
for pc in X["pieces"]:
    col = {c: k for k, c in enumerate(pc["columns"])}
    for r in pc["stations"]:
        pp.append((r[col["x"]], r[col["z"]], max(abs(r[col["left_m"]]), abs(r[col["right_m"]]))))
kdp = kdtree.KDTree(len(pp))
for k, (x, z, _h) in enumerate(pp):
    kdp.insert((x, z, 0.0), k)
kdp.balance()
J = {j: X["junctions"][j]["xz"] for j in ("J1", "J5")}


def plan_d(x, z):
    _c, k, d = kdp.find((x, z, 0.0))
    return d - pp[k][2]


def hit(b, x, z, y):
    loc, _n, _i, _d = b.ray_cast((x, z, y + 60.0), (0.0, 0.0, -1.0))
    return None if loc is None else loc[2]


def nearest_surface(b, x, z, y):
    """the other ground's height at (x, z) nearest y: rays from 1 m above and 1 m below (a terrain that folds over
    itself - a bank under a deck - has two heights at one xz), else from 60 m above"""
    best = None
    for oz, dz in ((1.0, -1.0), (-1.0, 1.0)):
        loc, _n, _i, _d = b.ray_cast((x, z, y + oz), (0.0, 0.0, dz), 2.0)
        if loc is not None and (best is None or abs(loc[2] - y) < abs(best - y)):
            best = loc[2]
    return best if best is not None else hit(b, x, z, y)


def by_xz(V, F):
    d = {}
    for v in sorted({v for t in F for v in t}):
        d.setdefault((round(V[v][0] * 1000), round(V[v][2] * 1000)), []).append(V[v][1])
    return d


def compare(V, F, kd_road, other_bvh, label, other_xz):
    vs = sorted({v for t in F for v in t})
    n = 0
    dys = []
    bad = []
    miss = 0
    same_vertex = 0
    for v in vs:
        x, y, z = V[v]
        _c, _k, dr = kd_road.find((x, z, 0.0))
        if dr > 150.0:
            continue
        n += 1
        ys = other_xz.get((round(x * 1000), round(z * 1000)))
        if ys:
            same_vertex += 1
            h = min(ys, key=lambda q: abs(q - y))
        else:
            h = nearest_surface(other_bvh, x, z, y)
        if h is None:
            miss += 1
            continue
        dy = h - y
        dys.append(abs(dy))
        if abs(dy) > 0.05:
            jd = {j: round(math.hypot(x - J[j][0], z - J[j][1]), 1) for j in J if J[j]}
            bad.append([round(x, 2), round(z, 2), round(y, 3), round(dy, 3), round(dr, 1), round(plan_d(x, z), 1), jd])
    dys.sort()
    return {"vertices_within_150m_of_a_road": n, "no_surface_under": miss, "matched_a_vertex_at_the_same_xz": same_vertex,
            "abs_dy_p50": dys[len(dys) // 2] if dys else None, "abs_dy_p99": dys[int(0.99 * len(dys))] if dys else None,
            "abs_dy_max": dys[-1] if dys else None, "over_0.05": len(bad),
            "over_0.05_rows": {"columns": ["x", "z", "y", "dy", "road_d", "planned_pavement_d", "to_J"], "rows": bad}}


print("[p2] loop ground: v0.18.0 vertices vs the rehearsal", flush=True)
xz_o, xz_n = by_xz(Vo, Fo), by_xz(Vn, Fn)
res["ground_v018_vs_rehearsal"] = compare(Vo, pick(Oo, ("1GRASS",)), kdo, bn, "v018", xz_n)
print("[p2] loop ground: rehearsal vertices vs v0.18.0", flush=True)
res["ground_rehearsal_vs_v018"] = compare(Vn, pick(On, ("1GRASS",)), kdn, bo, "new", xz_o)
for k in ("ground_v018_vs_rehearsal", "ground_rehearsal_vs_v018"):
    r = res[k]
    rows = r["over_0.05_rows"]["rows"]
    # the plan's exceptions: beside the two weld mouths, where the nearest road changes (within 150 m of the planned
    # north pavement AND within 300 m of J1 / J5)
    exc = [q for q in rows if q[5] <= 150.0 and min(q[6].values()) <= 300.0]
    r["over_0.05_beside_the_weld_mouths"] = len(exc)
    r["over_0.05_elsewhere"] = len(rows) - len(exc)
    r["max_abs_dy_elsewhere"] = max([abs(q[3]) for q in rows if q not in exc], default=0.0)
    r["max_abs_dy_beside_mouths"] = max([abs(q[3]) for q in exc], default=0.0)
    r["max_planned_pavement_d_of_a_departure"] = max([q[5] for q in rows], default=None)
    print(k, {kk: r[kk] for kk in r if kk != "over_0.05_rows"}, flush=True)


# --- 2. open edges ---
def open_edges(V, F, kd_road):
    key = {}
    vid = []
    for v in range(len(V)):
        pass
    used = sorted({v for t in F for v in t})
    q = {}
    for v in used:
        k = (round(V[v][0] * 1000), round(V[v][1] * 1000), round(V[v][2] * 1000))
        q[v] = key.setdefault(k, len(key))
    cnt = {}
    for a, b, c in F:
        A, B, C = q[a], q[b], q[c]
        for e in ((A, B), (B, C), (C, A)):
            e2 = (min(e), max(e))
            cnt[e2] = cnt.get(e2, 0) + 1
    pos = {}
    for v in used:
        pos[q[v]] = V[v]
    xs = [p[0] for p in pos.values()]
    zs = [p[2] for p in pos.values()]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    border = near_road = tier = 0
    tier_rows = []
    over2 = sum(1 for c in cnt.values() if c > 2)
    for (a, b), c in cnt.items():
        if c != 1:
            continue
        pa, pb = pos[a], pos[b]
        on_b = ((abs(pa[0] - x0) < 0.01 and abs(pb[0] - x0) < 0.01) or (abs(pa[0] - x1) < 0.01 and abs(pb[0] - x1) < 0.01)
                or (abs(pa[2] - z0) < 0.01 and abs(pb[2] - z0) < 0.01) or (abs(pa[2] - z1) < 0.01 and abs(pb[2] - z1) < 0.01))
        if on_b:
            border += 1
            continue
        mx, mz = (pa[0] + pb[0]) / 2, (pa[2] + pb[2]) / 2
        _c, _k, dr = kd_road.find((mx, mz, 0.0))
        if dr <= 30.0:
            near_road += 1
        else:
            tier += 1
            if len(tier_rows) < 200:
                tier_rows.append([round(mx, 2), round(mz, 2), round(dr, 1)])
    return {"open_edges_outer_border": border, "open_edges_within_30m_of_a_road": near_road,
            "open_edges_elsewhere_tier_seams": tier, "edges_used_more_than_twice": over2, "rows": tier_rows}


print("[p2] open edges", flush=True)
res["open_edges_rehearsal"] = open_edges(Vn, Fn, kdn)
res["open_edges_v018"] = open_edges(Vo, Fo, kdo)
print({k: {kk: v for kk, v in res[k].items() if kk != "rows"} for k in ("open_edges_rehearsal", "open_edges_v018")}, flush=True)

# --- 3. low clause ---
T = json.loads(gzip.decompress((PROJ / "data" / "terrain.tiers.json.gz").read_bytes()))
x0f, z0f, ux, uz = T["frame"]
C = json.loads(gzip.decompress((PROJ / "data" / "terrain.samples.json.gz").read_bytes()))
H = {(i, j): c / 100.0 for i, j, c in zip(C["I"], C["J"], C["h_cm"])}
FD = C.get("fine") or {}
HF = {(i, j): c / 100.0 for i, j, c in zip(FD.get("I", []), FD.get("J", []), FD.get("h_cm", []))}
elev0 = 100.8
cfgo = json.loads((PROJ / "data" / "centerline.local.json").read_text())["origin"]
elev0 = float(cfgo["elev_m"])


def dep_at(x, z):
    fi, fj = (x - x0f) / ux, (z - z0f) / uz
    ri, rj = round(fi), round(fj)
    if abs(fi - ri) < 1e-3 and abs(fj - rj) < 1e-3 and (ri, rj) in H:
        return H[(ri, rj)], "point"
    f5i, f5j = fi * 5, fj * 5
    r5i, r5j = round(f5i), round(f5j)
    if abs(f5i - r5i) < 5e-3 and abs(f5j - r5j) < 5e-3 and (r5i, r5j) in HF:
        return HF[(r5i, r5j)], "fine_point"
    i0, j0 = math.floor(fi), math.floor(fj)
    tx, ty = fi - i0, fj - j0
    try:
        a, b, c, d = H[(i0, j0)], H[(i0 + 1, j0)], H[(i0, j0 + 1)], H[(i0 + 1, j0 + 1)]
    except KeyError:
        return None, "none"
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty, "bilinear_2.5m"


def low(V, F, kd_road, label):
    vs = sorted({v for t in F for v in t})
    kinds = {}
    rows = {"near_road_band": [], "beyond": []}
    worst = {"near_road_band": 0.0, "beyond": 0.0}
    nb = {"near_road_band": 0, "beyond": 0}
    ymin = 1e9
    for v in vs:
        x, y, z = V[v]
        ymin = min(ymin, y + elev0)
        h, kind = dep_at(x, z)
        kinds[kind] = kinds.get(kind, 0) + 1
        if h is None:
            continue
        under = h - (y + elev0)
        _c, _k, dr = kd_road.find((x, z, 0.0))
        band = "near_road_band" if dr <= 36.0 else "beyond"
        nb[band] += 1
        worst[band] = max(worst[band], under)
        if under > 2.0 and len(rows[band]) < 400:
            rows[band].append([round(x, 2), round(z, 2), round(y + elev0, 2), round(h, 2), round(under, 2), round(dr, 1),
                               kind])
    return {"vertices": len(vs), "by_3dep_kind": kinds, "min_abs_m": round(ymin, 2),
            "checked": nb, "worst_under_3dep_m": {k: round(w, 3) for k, w in worst.items()},
            "more_than_2m_under": {k: len(r) for k, r in rows.items()},
            "more_than_3m_under": {k: sum(1 for q in r if q[4] > 3.0) for k, r in rows.items()},
            "rows": {"columns": ["x", "z", "y_abs", "3dep", "under", "road_d", "kind"], **rows}}


def far_dev(V, objs):
    """V7 'far cells within 1 m of 3DEP': every GRASS_FAR vertex on a lattice / break key against its own 3DEP point"""
    vs = sorted({v for t in pick(objs, ("GRASS_FAR",)) for v in t})
    dev = []
    for v in vs:
        x, y, z = V[v]
        h, kind = dep_at(x, z)
        if kind in ("point", "fine_point"):
            dev.append(abs(h - (y + elev0)))
    dev.sort()
    return {"far_vertices": len(vs), "on_a_sampled_key": len(dev), "abs_dev_p50": dev[len(dev) // 2] if dev else None,
            "abs_dev_p99": dev[int(0.99 * len(dev))] if dev else None, "abs_dev_max": dev[-1] if dev else None,
            "over_1m": sum(1 for d in dev if d > 1.0)}


res["far_vs_3dep_rehearsal"] = far_dev(Vn, On)
print("far_vs_3dep", res["far_vs_3dep_rehearsal"], flush=True)
print("[p2] low clause", flush=True)
res["low_rehearsal"] = low(Vn, Fn, kdn, "new")
print("low_rehearsal", {k: v for k, v in res["low_rehearsal"].items() if k != "rows"}, flush=True)
res["low_v018"] = low(Vo, Fo, kdo, "v018")
print("low_v018", {k: v for k, v in res["low_v018"].items() if k != "rows"}, flush=True)
OUT.write_text(json.dumps(res, indent=1))
print("[p2] wrote", OUT)

"""Ledger 0054 P2 step 5: 0046 criterion 3's low clause, restated, measured on a BUILT gate OBJ (L5).

The plan's wording: "no terrain vertex more than 2 m below the 3DEP value at its own position". Every terrain vertex
(1GRASS* + GRASS_FAR*) against 3DEP at its position from the rehearsal's lattice cache (data/terrain.samples.json.gz:
3DEP 1 m point samples, TLS-fetched): a lattice or break-line key takes its own point; any other vertex (seated,
refined, subdivided near a road) the 2.5 m base lattice around it, bilinear (flagged). A finest-level vertex is BUILT
from the anti-aliasing tent of the 2.5 m samples around it (0046 fix round 2): its tent value is reported beside the
point. Each vertex more than 1 m under is classified by its pavement distance (terrain_sample's own: centreline
distance less the half-width, the planning roads): inside the graded near-road band (keep_surface_m + keep_feather_m
= 36 m, 0046 criterion 7: a road cut graded to the road by design) or beyond.

    python low_clause.py <airoso> <project> <gate obj> <out.json>
"""
import gzip
import json
import math
import sys
from pathlib import Path

AIR, PROJ, OBJ, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(AIR))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

cfg = json.loads((PROJ / "track.config.json").read_text(encoding="utf-8"))
opt = cfg["terrain"]["tier_options"]
BAND = float(opt["keep_surface_m"]) + float(opt["keep_feather_m"])
T = json.loads(gzip.decompress((PROJ / "data" / "terrain.tiers.json.gz").read_bytes()))
x0, z0, ux, uz = T["frame"]
C = json.loads(gzip.decompress((PROJ / "data" / "terrain.samples.json.gz").read_bytes()))
H = {(i, j): c / 100.0 for i, j, c in zip(C["I"], C["J"], C["h_cm"])}
FD = C.get("fine") or {}
HF = {(i, j): c / 100.0 for i, j, c in zip(FD.get("I", []), FD.get("J", []), FD.get("h_cm", []))}
local = json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))
elev0 = float(local["origin"]["elev_m"])
lines, _o, _f = ts.road_inputs(PROJ)
pave = ts._Pave(lines, bool(cfg.get("loop", True)))


def dep(x, z):
    fi, fj = (x - x0) / ux, (z - z0) / uz
    ri, rj = round(fi), round(fj)
    if abs(fi - ri) < 1e-3 and abs(fj - rj) < 1e-3 and (ri, rj) in H:
        tent = None
        try:
            tent = tt.aa_value(H, (ri, rj))
        except KeyError:
            pass
        return H[(ri, rj)], tent, "point"
    f5i, f5j = fi * tt.BREAK_FINE, fj * tt.BREAK_FINE
    if abs(f5i - round(f5i)) < 5e-3 and abs(f5j - round(f5j)) < 5e-3 and (round(f5i), round(f5j)) in HF:
        return HF[(round(f5i), round(f5j))], None, "fine_point"
    i0, j0 = math.floor(fi), math.floor(fj)
    tx, ty = fi - i0, fj - j0
    try:
        a, b, c, d = H[(i0, j0)], H[(i0 + 1, j0)], H[(i0, j0 + 1)], H[(i0 + 1, j0 + 1)]
    except KeyError:
        return None, None, "none"
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty, None, "bilinear_2.5m"


verts = []
groups_on = False
V = []
used = set()
cur_terrain = False
with open(OBJ, "r", encoding="utf-8", errors="replace") as f:
    for ln in f:
        c = ln[:2]
        if c == "v ":
            p = ln.split()
            V.append((float(p[1]), float(p[2]), float(p[3])))
        elif c == "o " or c == "g ":
            cur_terrain = ln[2:].strip().upper().startswith(("1GRASS", "GRASS_FAR"))
        elif c == "f " and cur_terrain:
            for t in ln.split()[1:]:
                i = int(t.split("/")[0])
                used.add(i - 1 if i > 0 else len(V) + i)
rows = []
kinds = {}
ymin = 1e9
for v in sorted(used):
    x, y, z = V[v]
    ya = y + elev0
    ymin = min(ymin, ya)
    h, tent, kind = dep(x, z)
    kinds[kind] = kinds.get(kind, 0) + 1
    if h is None:
        continue
    under = h - ya
    under_t = None if tent is None else tent - ya
    if under > 1.0:
        d = pave.dist(x, z, reach=120.0)
        rows.append([round(x, 2), round(z, 2), round(ya, 2), round(h, 2), round(under, 3),
                     None if under_t is None else round(under_t, 3), round(d, 1), kind])


# a vertex with no sample at its own position (bilinear) and more than 1 m under: fresh 3DEP AT it (TLS), the clause's
# own reference (L5) - the bilinear estimate is replaced, both kept
from scripts.elevation import usgs_3dep  # noqa: E402
m_lon, m_lat = tt.meters_per_degree(local["origin"]["lat"])
need = [r for r in rows if r[7] == "bilinear_2.5m"]
fresh = []
for a in range(0, len(need), 450):
    fresh += usgs_3dep._sample_batch([(local["origin"]["lon"] + r[0] / m_lon, local["origin"]["lat"] + r[1] / m_lat)
                                      for r in need[a:a + 450]], retries=4)
for r, h in zip(need, fresh):
    if h is not None:
        r.append({"bilinear": r[3], "fresh_3dep": round(float(h), 2)})
        r[3] = round(float(h), 2)
        r[4] = round(float(h) - r[2], 3)
        r[7] = "fresh_point"
rows = [r for r in rows if r[4] > 1.0 or r[7] != "fresh_point"]


def summ(sel):
    return {"over_2m_point": sum(1 for r in sel if r[4] > 2.0),
            "over_2m_point_and_tent": sum(1 for r in sel if r[4] > 2.0 and (r[5] is None or r[5] > 2.0)),
            "over_2m_point_and_tent_beyond_40m": sum(1 for r in sel if r[4] > 2.0 and (r[5] is None or r[5] > 2.0)
                                                     and r[6] > 40.0),
            "over_3m_point": sum(1 for r in sel if r[4] > 3.0),
            "worst_point_m": max([r[4] for r in sel], default=0.0),
            "worst_tent_m": max([r[5] for r in sel if r[5] is not None], default=0.0)}


# terrain.ground_release zones (0046 v0.18.0 integration): their ground is 3DEP held under an earth batter from the
# pavement, out to reach_m 40 m - near-road ground graded by design, like criterion 7's band
GR = PROJ / "data" / "ground_release.json"
rel = set()
rc = 2.0
if GR.exists():
    g = json.loads(GR.read_text(encoding="utf-8"))
    rc = float(g["cell_m"])
    rel = set(zip(g["I"], g["J"]))


def released(x, z):
    i, j = x / rc, z / rc
    return all((a, b) in rel for a in (math.floor(i), math.ceil(i)) for b in (math.floor(j), math.ceil(j)))


for r in rows:
    r.append("released" if released(r[0], r[1]) else "")
clause_i = [r for r in rows if r[6] > BAND and not released(r[0], r[1])
            and min(r[4], r[5] if r[5] is not None else r[4]) > 2.0]
band = [r for r in rows if r[6] <= BAND]
beyond = [r for r in rows if r[6] > BAND]
below100 = [r for r in rows if r[2] < 100.0]
rep = {"obj": str(OBJ), "terrain_vertices": len(used), "by_3dep_kind": kinds, "min_abs_m": round(ymin, 2),
       "band_m": BAND, "near_road_band": summ(band), "beyond_band": summ(beyond), "below_100m_abs": summ(below100),
       "beyond_band_rows": sorted(beyond, key=lambda r: -r[4])[:50],
       "near_band_worst": sorted(band, key=lambda r: -r[4])[:20],
       "fresh_points": len(need),
       "clause_i": {"what": "beyond the near-road band (36 m of a built pavement) and outside the ground_release zones: "
                            "more than 2 m under the 3DEP value the vertex is built from (its point sample; a finest-level "
                            "vertex's anti-aliasing tent)", "offenders": len(clause_i), "rows": clause_i[:20]},
       "clause_ii_below_100m_or_far": {"what": "0046 fix round 3, kept: below 100 m abs, more than 3 m under the 3DEP point",
                                       "offenders": sum(1 for r in rows if r[2] < 100.0 and r[4] > 3.0)},
       "clause_iii_floor_m": 15.52, "clause_iii_pass": ymin >= 15.52,
       "columns": ["x", "z", "y_abs", "3dep_point", "under_point", "under_tent", "pavement_d", "kind"]}
OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
print("[low]", json.dumps({k: v for k, v in rep.items() if k not in ("beyond_band_rows", "near_band_worst")})[:1800])

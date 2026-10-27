"""Replay the assembler's buildings pass (scripts-v021/blender/build_loop_blend.build_buildings) outside Blender, on the
scratch project's own inputs, to list the old band / new band counts and the per-type split. bpy is stubbed; heights are
irrelevant to the selection (terr = 0)."""
import importlib.util, json, math, sys, types
from collections import Counter
from pathlib import Path

W = Path(sys.argv[1]); PROJ = Path(sys.argv[2])
sys.modules["bpy"] = types.ModuleType("bpy")
sys.modules["bmesh"] = types.ModuleType("bmesh")
sys.path.insert(0, str(W / "tracks" / "san-diego-lake-murray"))     # `scripts` = scripts-v021 (the V021 shim's effect)
spec = importlib.util.spec_from_file_location("scripts", W / "tracks/san-diego-lake-murray/scripts-v021/__init__.py",
                                              submodule_search_locations=[str(W / "tracks/san-diego-lake-murray/scripts-v021")])
m = importlib.util.module_from_spec(spec); sys.modules["scripts"] = m; spec.loader.exec_module(m)
spec = importlib.util.spec_from_file_location("blb", W / "tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.py")
blb = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(blb)
except Exception as e:
    print("import note:", type(e).__name__, str(e)[:200])
cl = json.load(open(PROJ / "data/centerline.local.json", encoding="utf-8"))
cfg = json.load(open(PROJ / "track.config.json", encoding="utf-8"))
centerline = [tuple(p) for p in cl["points_xyz_m"]]; widths = cl["widths_m"]
lon0, lat0 = cl.get("origin_lon") or cl.get("lon0"), cl.get("origin_lat") or cl.get("lat0")
if lon0 is None:
    o = cl.get("origin") or {}
    lon0, lat0 = o.get("lon"), o.get("lat")
print("origin", lon0, lat0, "keys", [k for k in cl.keys()][:12])
conns = json.load(open(PROJ / "data/connectors.local.json", encoding="utf-8"))["connectors"]
pieces = [(c["name"], [tuple(p) for p in c["points_xyz_m"]], list(c["widths_m"])) for c in conns if len(c["points_xyz_m"]) >= 2]
pads = json.load(open(PROJ / "data/pads.plan.json", encoding="utf-8"))
old = json.load(open(PROJ / "data/buildings.cache.json", encoding="utf-8"))
new = json.load(open(PROJ / "data/buildings.expansion.cache.json", encoding="utf-8"))

# instrument: record the candidates by wrapping _extrude_footprint
rec = []
blb._extrude_footprint = lambda mesh, foot, base, h: rec.append((foot, base, h))
blb.build_buildings(centerline, widths, None, old, lon0, lat0, terr=lambda x, z: 0.0, new_cache=new, pieces=pieces, pads=pads)
print("extruded", len(rec))
# which band is each in? (re-derive: old band = within 120 m of the mainline)
B = 60.0
from collections import defaultdict
rb = defaultdict(list)
for i in range(0, len(centerline), 2):
    x, _y, z = centerline[i]; rb[(int(x // B), int(z // B))].append((x, z))
def d_main(x, z):
    bx, bz = int(x // B), int(z // B); best = 1e18
    for dx in (-2, -1, 0, 1, 2):
        for dz in (-2, -1, 0, 1, 2):
            for (rx, rz) in rb.get((bx + dx, bz + dz), ()):
                best = min(best, (x - rx) ** 2 + (z - rz) ** 2)
    return math.sqrt(best)
north = [p for p in pieces if p[0].startswith("north_")]
def d_north(x, z):
    best = 1e18
    for _n, pts, _w in north:
        for q in pts[::2]:
            best = min(best, (x - q[0]) ** 2 + (z - q[2]) ** 2)
    return math.sqrt(best)
bands = Counter(); verts = Counter()
for foot, base, h in rec:
    cx = sum(p[0] for p in foot) / len(foot); cz = sum(p[1] for p in foot) / len(foot)
    band = "old" if d_main(cx, cz) <= 120 else ("new_north" if d_north(cx, cz) <= 125 else "new_other")
    bands[band] += 1
    verts[band] += 2 * len(foot) + len(foot)      # walls (2n) + roof ring (n), as _extrude_footprint
print("bands", dict(bands), "approx verts", dict(verts))

"""Ledger 0054 P0 step 6 proofs for scripts-v021 heightfield.py grid_grow + terrain_tiers frame pin.

usage: python p0_heightfield_proof.py <airoso-worktree> <scratch-dir> <heightfield_head.py> <remap-proof.json>

A  grid_grow ABSENT: the new heightfield.py, fed the installed grid's own 3DEP values, writes the installed
   heightfield.npy + heightfield.meta.json byte for byte (same dims, same rounding, same writer).
B  grid_grow ABSENT: HEAD's heightfield.py and the new one, fed a sampler that is a function of each point's exact
   float bits, write byte-identical outputs (elevation json, npy, meta, svg): the sample positions are bit-identical.
C  grid_grow 37/37/26/0: every old node is re-sampled at its bit-identical position (old block == installed npy);
   24,883 nodes; 1,000 random old nodes keep their consumer-projected position to 1e-9 deg; the pinned frame on the
   grown meta == the remap tool's new frame; the pin with offsets 0 on the installed meta == today's frame, bitwise.
D  coverage: every kept near-road cell (20 m, within 18 m of the pavement) of the north route lies inside the grown grid.
"""
import importlib.util
import json
import math
import random
import shutil
import struct
import sys
from pathlib import Path

AIR = Path(sys.argv[1]); SCR = Path(sys.argv[2]); HEAD = Path(sys.argv[3]); REMAP = Path(sys.argv[4])
V021 = AIR / "tracks" / "san-diego-lake-murray" / "scripts-v021"
TRACK = AIR / "tracks" / "san-diego-lake-murray"
s = importlib.util.spec_from_file_location("scripts", V021 / "__init__.py", submodule_search_locations=[str(V021)])
m = importlib.util.module_from_spec(s); sys.modules["scripts"] = m; s.loader.exec_module(m)
from scripts.elevation import heightfield as hf_new, usgs_3dep  # noqa: E402
hs = importlib.util.spec_from_file_location("hf_head", HEAD); hf_head = importlib.util.module_from_spec(hs); hs.loader.exec_module(hf_head)
# airoso's engine terrain_tiers by file path (pure stdlib, stands alone)
ts_ = importlib.util.spec_from_file_location("tt_air", AIR / "scripts" / "geometry" / "terrain_tiers.py")
tt = importlib.util.module_from_spec(ts_); ts_.loader.exec_module(tt)

meta0 = json.loads((TRACK / "data" / "heightfield.meta.json").read_text())
npy0 = (TRACK / "data" / "heightfield.npy").read_bytes()
NX0, NY0 = meta0["nx"], meta0["ny"]
hdr = 128 if npy0[8:10] else None
hlen = struct.unpack("<H", npy0[8:10])[0]
vals0 = list(struct.unpack("<%dd" % (NX0 * NY0), npy0[10 + hlen:]))
cfg0 = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
cfg0["terrain"].pop("grid_grow", None)
out = {}


def project(name, cfg):
    p = SCR / name
    if p.exists():
        shutil.rmtree(p)
    (p / "data").mkdir(parents=True)
    shutil.copy(TRACK / "data" / "centerline.geojson", p / "data" / "centerline.geojson")
    (p / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return p


def bits(lon, lat):
    h = 0
    for b in struct.pack("<dd", lon, lat):
        h = (h * 131 + b) % 1000003
    return 100.0 + h / 1000.0


captured = {}


def sampler_installed(points, **k):
    if len(points) == NX0 * NY0:
        captured["grid_points"] = list(points)
        return list(vals0)
    return [bits(lo, la) for lo, la in points]


# --- A ---
usgs_3dep.sample_points = sampler_installed
pa = project("A", cfg0)
hf_new.build(pa)
a_npy = (pa / "data" / "heightfield.npy").read_bytes() == npy0
a_meta = (pa / "data" / "heightfield.meta.json").read_bytes() == (TRACK / "data" / "heightfield.meta.json").read_bytes()
out["A_grid_grow_absent_reproduces_installed"] = {"npy_byte_identical": a_npy, "meta_byte_identical": a_meta,
                                                   "nx": NX0, "ny": NY0}

# --- B ---
usgs_3dep.sample_points = lambda pts, **k: [bits(lo, la) for lo, la in pts]
pb1, pb2 = project("B_head", cfg0), project("B_new", cfg0)
hf_head.build(pb1)
hf_new.build(pb2)
same = {}
for f in ("centerline.elevation.json", "heightfield.npy", "heightfield.meta.json", "elevation_profile.svg"):
    same[f] = (pb1 / "data" / f).read_bytes() == (pb2 / "data" / f).read_bytes()
out["B_head_vs_new_bit_positions"] = same

# --- C ---
grow = {"rows_n": 37, "rows_s": 37, "cols_w": 26, "cols_e": 0}
cfgg = json.loads(json.dumps(cfg0)); cfgg["terrain"]["grid_grow"] = grow
lookup = {pt: v for pt, v in zip(captured["grid_points"], vals0)}
SENT = -9999.0
usgs_3dep.sample_points = lambda pts, **k: ([lookup.get(p, SENT) for p in pts] if len(pts) > 20000
                                            else [bits(lo, la) for lo, la in pts])
pc = project("C", cfgg)
hf_new.build(pc)
mg = json.loads((pc / "data" / "heightfield.meta.json").read_text())
raw = (pc / "data" / "heightfield.npy").read_bytes()
hl = struct.unpack("<H", raw[8:10])[0]
NX, NY = mg["nx"], mg["ny"]
vg = struct.unpack("<%dd" % (NX * NY), raw[10 + hl:])
old_block_ok, sentinel_in_old, sentinel_new = True, 0, 0
for j in range(NY):
    for i in range(NX):
        v = vg[j * NX + i]
        oj, oi = j - 37, i - 26
        if 0 <= oj < NY0 and 0 <= oi < NX0:
            if v != vals0[oj * NX0 + oi]:
                old_block_ok = False
            if v == SENT:
                sentinel_in_old += 1
        elif v == SENT:
            sentinel_new += 1


def proj_node(meta, j, i, lon0=0.0):
    s_, w_, n_, e_ = meta["bbox_swne"]
    sp = meta["spacing_m"]
    mid = (s_ + n_) / 2
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(mid)))
    return w_ + i * gx, n_ - j * gy


rng = random.Random(54)
worst = 0.0
for _ in range(1000):
    j, i = rng.randrange(NY0), rng.randrange(NX0)
    a, b = proj_node(meta0, j, i), proj_node(mg, j + 37, i + 26)
    worst = max(worst, abs(a[0] - b[0]), abs(a[1] - b[1]))
worst_all = 0.0
for j in range(NY0):
    for i in range(NX0):
        a, b = proj_node(meta0, j, i), proj_node(mg, j + 37, i + 26)
        worst_all = max(worst_all, abs(a[0] - b[0]), abs(a[1] - b[1]))
# frames
local = json.loads((TRACK / "data" / "centerline.local.json").read_text())
origin = local["origin"]
spec = tt.TierSpec(cfg0["terrain"], origin, False)
up = 2
f_today = tt.Frame.heightfield(meta0, origin, up, spec.levels, spec.base_m)
pin0 = {"bbox_swne": meta0["bbox_swne"], "spacing_m": 40.0, "rows_n": 0, "cols_w": 0}
f_pin0 = tt.Frame.heightfield(meta0, origin, up, spec.levels, spec.base_m, pin=pin0)
pin = dict(pin0, rows_n=37, cols_w=26)
f_grown = tt.Frame.heightfield(mg, origin, up, spec.levels, spec.base_m, pin=pin)
remap = json.loads(REMAP.read_text())
f_grown_unpinned = tt.Frame.heightfield(mg, origin, up, spec.levels, spec.base_m)
out["C_grid_grow_37_37_26"] = {
    "meta": {k: mg[k] for k in ("bbox_swne", "nx", "ny", "grid_grow", "base_bbox_swne")},
    "nodes": NX * NY, "old_block_equals_installed_npy": old_block_ok, "old_nodes_missing_their_position": sentinel_in_old,
    "new_nodes_to_fetch": sentinel_new,
    "random_1000_old_nodes_max_projected_diff_deg": worst, "all_old_nodes_max_projected_diff_deg": worst_all,
    "frame_today": f_today.to_json(), "frame_pin_offsets0_installed_meta": f_pin0.to_json(),
    "pin0_equals_today_bitwise": f_today.to_json() == f_pin0.to_json(),
    "frame_grown_pinned": f_grown.to_json(), "remap_new_frame": remap["new_frame"],
    "pinned_grown_equals_remap_frame": f_grown.to_json() == remap["new_frame"],
    "frame_grown_unpinned_minus_pinned_m": [a - b for a, b in zip(f_grown_unpinned.to_json(), f_grown.to_json())],
}

# --- D: coverage of the kept near-road cells of the north route ---
routes = json.loads((AIR / "data" / "routes.json").read_text())
north = routes["north"]
HALF = {"Waring Road": 27.5 / 2, "Princess View Drive": 28.0 / 2, "Mission Gorge Road": 33.0 / 2,
        "Jackson Drive": 26.0 / 2, "College Avenue": 15.0}
osm = json.loads((TRACK / "data" / "osm.expansion.json").read_text())
wname = {}
for w in osm["ways"]:
    for a_, b_ in zip(w["nodes"], w["nodes"][1:]):
        wname[frozenset((a_, b_))] = w["tags"].get("name")
lines = []
for nodes in (north["nodes"], north["rev"]["nodes"]):
    for a_, b_ in zip(nodes, nodes[1:]):
        nm = wname.get(frozenset((a_, b_)))
        pa_ = spec.to_local(*osm["nodes"][str(a_)]); pb_ = spec.to_local(*osm["nodes"][str(b_)])
        hw = HALF.get(nm, 16.5)
        lines.append(([(pa_[0], 0.0, pa_[1]), (pb_[0], 0.0, pb_[1])], [2 * hw, 2 * hw]))
pts = tt.densify(lines, 2.0)
kc = 8  # base units per 20 m keep cell (upsample 2: per = 8)
cx, cz = kc * f_grown.ux, kc * f_grown.uz
cells = tt.mark_cells(pts, 18.0, cx, cz, f_grown.x0, f_grown.z0)
# the grown grid's extent in the local frame (row 0 north): x in [x0, x0 + (NX-1)*40m], z in [z0 - (NY-1)*40m, z0]
gx_m, gz_m = 2 * cx, 2 * cz
xmin, xmax = f_grown.x0, f_grown.x0 + (NX - 1) * gx_m
zmax, zmin = f_grown.z0, f_grown.z0 - (NY - 1) * gz_m
outside = []
mx = {"north_margin_m": 1e9, "south_margin_m": 1e9, "west_margin_m": 1e9, "east_margin_m": 1e9}
for (i, j) in cells:
    xa, xb = f_grown.x0 + i * cx, f_grown.x0 + (i + 1) * cx
    za, zb = f_grown.z0 + j * cz, f_grown.z0 + (j + 1) * cz
    mx["north_margin_m"] = min(mx["north_margin_m"], zmax - zb)
    mx["south_margin_m"] = min(mx["south_margin_m"], za - zmin)
    mx["west_margin_m"] = min(mx["west_margin_m"], xa - xmin)
    mx["east_margin_m"] = min(mx["east_margin_m"], xmax - xb)
    if xa < xmin - 1e-6 or xb > xmax + 1e-6 or za < zmin - 1e-6 or zb > zmax + 1e-6:
        outside.append([i, j])
lat_n = spec.to_lonlat(0.0, max(f_grown.z0 + (j + 1) * cz for _i, j in cells))[1]
lon_w = spec.to_lonlat(min(f_grown.x0 + i * cx for i, _j in cells), 0.0)[0]
out["D_north_route_kept_cells"] = {"kept_cells": len(cells), "outside_grown_grid": len(outside),
                                   "margins_m": {k: round(v, 1) for k, v in mx.items()},
                                   "furthest_north_lat": lat_n, "furthest_west_lon": lon_w,
                                   "half_widths_m": HALF, "within_m": 18.0, "keep_cell_m": 20.0}
ok = (a_npy and a_meta and all(same.values()) and old_block_ok and sentinel_in_old == 0 and worst <= 1e-9
      and worst_all <= 1e-9 and out["C_grid_grow_37_37_26"]["pin0_equals_today_bitwise"]
      and out["C_grid_grow_37_37_26"]["pinned_grown_equals_remap_frame"] and not outside and NX * NY == 24883)
out["PASS"] = ok
(SCR / "p0_heightfield_proof.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))

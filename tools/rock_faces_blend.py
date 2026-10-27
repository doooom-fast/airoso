"""The road cuts' rock faces — ledger 0054 P4 (buildings + rock): the steep faces of the north network's cut walls split
out of the physical ground tiles of the PREPPED scene and skinned as the sandstone / conglomerate they are cut into, with
the ground's own physics kept.

IN PLAIN TERMS. A road cut into a hillside leaves a wall of bare rock beside the sidewalk, up to the rounded top where the
hill's own slope takes over. v0.19.0 built those walls at their real height (ledger 0054 P3 repair round 1: the auto
cuts) but painted them green, like the grass they stand in. This step looks at the finished ground beside every declared
cut, takes every ground triangle inside the cut's band that stands steeper than a slope grass could hold, and moves those
triangles into their own meshes named 1GRASS_ROCK_<tile>, so they wear the rock texture (scripts/ac/pbr.py row
"1GRASS_ROCK", before "1GRASS"). Nothing moves: every vertex stays exactly where the chain put it; the split only decides
which mesh a triangle belongs to, and the two meshes share their boundary vertices by position, so there is no crack.

WHY THE PREFIX 1GRASS_ROCK (and not 1ROCK, ROCKCUT, 1WALL). The faces keep the digit prefix so AC still collides with them
(a car that leaves the road still hits the ground, not a hole) and keep the GRASS key so surfaces.ini is unchanged (KEY=GRASS
binds every mesh whose name starts 1GRASS: same friction, same dirt, same sound as the verge they were cut from); every gate
that reads ground by the 1GRASS prefix (drive_test, audit_mesh, verify_kn5's face-up rule, kn5_ground_check, house_seat_check,
rib_check) reads them exactly as before. Only two readers tell them apart: pbr binds the rock row by the longer prefix, and
ext_config leaves them out of GrassFX's GRASS_MESHES (no grass blades on a rock wall). ROCKCUT (no digit) would have no
physics; 1WALL would make every wall gate read a 500 m rock face as a barrier.

WHERE THE SPLIT RUNS. After the kn5 prep and the thinning (the ground is final: the prep's contact band, the halving, the
thinning have all happened) and before the split into road / race scenes. It reads the SAME declaration the ground release
built the walls from (data/ground_release.auto_cuts.json: each zone's piece, stations, side, cut reach and top rounding) and
the intermediate's piece stations (data/expansion.north.json: x, z, curb offsets) for the band: from the declared side's
curb line out to cut_reach_m + round_m + BAND_PAD_M. Inside a band a triangle is rock when it stands at SLOPE_MIN or steeper
(metres of rise per metre of run; 0.7 = 35 deg, the angle of repose of loose earth: steeper than that in this ground is cut
rock, not a grassed bank — the real faces climb 1.1-1.6 m per metre, EXPANSION-PLAN D3 / auto_cuts face_p90_m_per_m). The
split lands at the toe (the first batter row off the sidewalk's apron, where the ground turns from flat to the batter) and at
the top rounding (where round_m eases the batter onto the hill's own slope, under SLOPE_MIN again) by that one rule; then a
clean-up so the boundary reads as one line and not a lace: a rock patch smaller than MIN_PATCH_M2 goes back to grass, a grass
hole inside the rock smaller than MAX_HOLE_M2 (the lattice's bench rows across a wall) becomes rock. A zone whose measured
real rise over the road is under MIN_RISE_M (3 m, ledger 0054's own "real wall" bar) is a bank and gets no rock however steep
a facet of it is. Every number is in fleet/GATES-CHANGELOG.md (2026-10-26 P4 buildings).

THE TOE. The sidewalk's outer apron (the CURB profile's last 1.2 m, graded 0.2 m down and buried under the ground) runs on
under the foot of the cut, so the first batter row stands OVER buried pavement: that is the real toe, and it is rock. What
is never rock is ground UNDER a pavement sheet (a face with a corner that has 1ROAD / 1KERB above it: the ground pinned under
the walk, the curtain behind a curb) — such a face stays grass whatever its slope.

SELF-CHECKS (exit 1 = the blend is not saved): no rock face has a vertex under a pavement sheet; the tiles' faces before ==
the tiles' faces after + the rock faces (no triangle made or lost); every vertex of every rock mesh is a vertex of the tile
it came from (no vertex moved); every rock mesh under the AC vertex cap. Report: data/rock_faces.json (per zone: faces, area, rise; the totals; the thin
triangles at the toe counted before the split, for ledger 0054 P3 "Left").

    blender --background --python-exit-code 1 --python tools/rock_faces_blend.py -- <prepped.blend> --project <proj>

No declaration (no data/ground_release.auto_cuts.json, or terrain.rock_faces.enabled false) = nothing happens, the blend is
left alone, exit 0. The texture: track.config.json texture_overrides["1GRASS_ROCK"] (Lake Murray's own sandstone tile,
tracks/san-diego-lake-murray/textures/sandstone_cut_*.jpg); the stock row's stone_tan.png when a track has none.
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
from scripts.ac import pbr  # noqa: E402

TERRAIN = "1GRASS"            # the prep's physical ground tiles (1GRASS_<n>)
ROCK = "1GRASS_ROCK"          # the rock meshes (1GRASS_ROCK_<n>, one per source tile)
PAVEMENT = ("1ROAD", "1KERB")
SLOPE_MIN = 0.70              # [invented] rise per run at which cut ground is rock, not grass (35 deg; earth rests at 30-35)
BAND_PAD_M = 6.0              # [invented] the band reaches this far past cut_reach_m + round_m (the rounding's own spread)
MIN_RISE_M = 3.0              # [std: ledger 0054 P2 / repair round 1 "a real wall 3 m or taller"] a zone whose measured real
                              # rise over the road is under this is a bank, not a wall: no rock in it however steep a facet
MIN_PATCH_M2 = 40.0           # [invented] a rock patch smaller than this (a few facets) goes back to grass (rehearsal 5 at 12:
                              # 17-35 m2 outcrop speckles on Mission Gorge's south bank, mg_apartments still)
MAX_HOLE_M2 = 60.0            # [invented] a grass hole inside the rock smaller than this becomes rock (rehearsal 5 at 20: the
                              # lattice's 1 m bench rows, 10-20 m long, left as grass stripes across the Jackson walls)
UV_TILE = 4.0                 # metres per texture tile, as the prep's planar UV (build_kn5_loop.UV_TILE)
VERT_CAP = 65535
THIN_ALT_M = 0.25             # [reported] a triangle whose shortest altitude is under this ...
THIN_LONG_M = 1.5             # ... with an edge longer than this is a sliver (ledger 0054 P3 "thin lighter triangles")


def _args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    blend = Path(a[0])
    proj = Path(a[a.index("--project") + 1]) if "--project" in a else blend.parents[1]
    return blend, proj


def _point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def zone_bands(proj, R, exp):
    """[(zone name, polygon [(x, y) plan, Blender frame], side)] from the auto-cut zones and the piece stations"""
    pieces = {p["id"]: p for p in exp["pieces"]}
    bands = []
    for z in R["zones"]:
        if not z.get("auto") or not z.get("cut_reach_m"):
            continue
        if float((z.get("measured") or {}).get("max_rise_m", 0.0)) < MIN_RISE_M:
            continue                                   # a bank under MIN_RISE_M: never rock
        p = pieces[z["piece"]]
        cols = p["columns"]
        ix, iz, il, ir, i_s = cols.index("x"), cols.index("z"), cols.index("left_m"), cols.index("right_m"), cols.index("s")
        rows = [r for r in p["stations"] if z["piece_s_m"][0] - 1e-6 <= r[i_s] <= z["piece_s_m"][1] + 1e-6]
        if len(rows) < 2:
            continue
        reach = float(z["cut_reach_m"]) + float(z.get("round_m") or 0.0) + BAND_PAD_M
        for side in z["sides"]:
            inner, outer = [], []
            for k, r in enumerate(rows):
                a, b = rows[max(0, k - 1)], rows[min(len(rows) - 1, k + 1)]
                tx, tz = b[ix] - a[ix], b[iz] - a[iz]
                L = math.hypot(tx, tz) or 1.0
                lx, lz = -tz / L, tx / L                  # unit LEFT of the forward direction (x east, z north)
                off = r[il] if side == "left" else r[ir]  # the curb: left_m +, right_m - (left of forward)
                sgn = 1.0 if side == "left" else -1.0
                inner.append((r[ix] + lx * off, r[iz] + lz * off))
                outer.append((r[ix] + lx * (off + sgn * reach), r[iz] + lz * (off + sgn * reach)))
            bands.append((z["name"], inner + outer[::-1], side))
    return bands


def _flat_bvh(prefixes):
    vs, fs = [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith(prefixes):
            continue
        base = len(vs)
        mw = ob.matrix_world
        vs += [tuple(mw @ v.co) for v in ob.data.vertices]
        fs += [tuple(base + i for i in p.vertices) for p in ob.data.polygons]
    if not fs:
        return None, None
    return BVHTree.FromPolygons(vs, fs), BVHTree.FromPolygons([(v[0], v[1], 0.0) for v in vs], fs)


def _components(face_keys, adjacency):
    """connected components of a set of face keys over an edge adjacency {face key: set(face key)}"""
    seen, comps = set(), []
    for f in face_keys:
        if f in seen:
            continue
        stack, comp = [f], []
        seen.add(f)
        while stack:
            g = stack.pop()
            comp.append(g)
            for h in adjacency.get(g, ()):
                if h in face_keys and h not in seen:
                    seen.add(h)
                    stack.append(h)
        comps.append(comp)
    return comps


def main():
    t0 = time.time()
    blend, proj = _args()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rc = ((cfg.get("terrain") or {}).get("rock_faces") or {})
    cuts = proj / "data" / "ground_release.auto_cuts.json"
    expp = proj / "data" / "expansion.north.json"
    if rc.get("enabled") is False or not cuts.exists() or not expp.exists():
        print("[rock] no auto cuts declared (data/ground_release.auto_cuts.json / expansion.north.json) or "
              "terrain.rock_faces.enabled false — nothing to do")
        return
    slope_min = float(rc.get("slope_min_m_per_m", SLOPE_MIN))
    R = json.loads(cuts.read_text(encoding="utf-8"))
    exp = json.loads(expp.read_text(encoding="utf-8"))
    bands = zone_bands(proj, R, exp)
    if not bands:
        print("[rock] no cut zone with a reach — nothing to do")
        return
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    if any(o.name.upper().startswith(ROCK) for o in bpy.data.objects):
        raise SystemExit("[rock] the scene already carries 1GRASS_ROCK meshes — this step runs once, on the prepped scene")
    tiles = sorted((o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(TERRAIN)),
                   key=lambda o: o.name)
    if not tiles:
        print("[rock] no 1GRASS tile — nothing to do")
        return
    for ob in tiles:
        if any(abs(a - b) > 1e-9 for a, b in zip(ob.matrix_world.to_translation(), (0, 0, 0))) or \
                any(abs(a - b) > 1e-9 for a, b in zip(ob.matrix_world.to_scale(), (1, 1, 1))):
            raise SystemExit(f"[rock] {ob.name} carries a transform — the prep leaves terrain tiles at identity")
    pav, _pav_flat = _flat_bvh(PAVEMENT)
    if pav is None:
        raise SystemExit("[rock] no pavement in the scene")
    # band bounding boxes, for a quick reject
    bb = [(nm, poly, side, min(p[0] for p in poly), max(p[0] for p in poly), min(p[1] for p in poly), max(p[1] for p in poly))
          for nm, poly, side in bands]

    def band_of(x, y):
        for nm, poly, side, x0, x1, y0, y1 in bb:
            if x0 <= x <= x1 and y0 <= y <= y1 and _point_in_poly(x, y, poly):
                return nm
        return None

    # 1. every tile face in a band: slope, area, thinness; adjacency across tiles by vertex position
    faces = {}                        # (tile index, face index) -> dict
    edge_faces = defaultdict(list)    # (rounded a, rounded b) -> [face keys]
    n_thin_before = 0
    n_under = 0                       # steep faces left as grass: a corner under a pavement sheet
    faces_before = {}
    for ti, ob in enumerate(tiles):
        me = ob.data
        faces_before[ob.name] = len(me.polygons)
        vs = me.vertices
        for p in me.polygons:
            c = p.center
            zn = band_of(c.x, c.y)
            if zn is None:
                continue
            nrm = p.normal
            horiz = math.hypot(nrm.x, nrm.y)
            slope = horiz / abs(nrm.z) if abs(nrm.z) > 1e-9 else float("inf")
            co = [vs[i].co for i in p.vertices]
            e = [(co[i] - co[(i + 1) % len(co)]).length for i in range(len(co))]
            area = p.area
            alt = 2.0 * area / max(e) if max(e) > 1e-9 else 0.0
            thin = len(co) == 3 and alt < THIN_ALT_M and max(e) > THIN_LONG_M
            n_thin_before += thin
            key = (ti, p.index)
            under = slope >= slope_min and any(
                pav.ray_cast(Vector((v.x, v.y, v.z + 60.0)), Vector((0, 0, -1)), 59.99)[0] is not None for v in co)
            n_under += under
            faces[key] = {"zone": zn, "slope": slope, "area": area, "rock": slope >= slope_min and not under, "thin": thin,
                          "rise": max(v.z for v in co) - min(v.z for v in co), "c": (c.x, c.y)}
            rk = [(round(v.x, 3), round(v.y, 3), round(v.z, 3)) for v in co]
            for i in range(len(rk)):
                a_, b_ = rk[i], rk[(i + 1) % len(rk)]
                edge_faces[(a_, b_) if a_ < b_ else (b_, a_)].append(key)
    adjacency = defaultdict(set)
    for fl in edge_faces.values():
        for a_ in fl:
            for b_ in fl:
                if a_ != b_:
                    adjacency[a_].add(b_)
    rock = {k for k, f in faces.items() if f["rock"]}
    n_raw = len(rock)
    # 2. clean-up: small rock patches back to grass; small grass holes inside the rock become rock
    dropped = 0
    for comp in _components(rock, adjacency):
        if sum(faces[k]["area"] for k in comp) < MIN_PATCH_M2:
            rock -= set(comp)
            dropped += len(comp)
    grass = {k for k in faces if k not in rock}
    filled = 0
    for comp in _components(grass, adjacency):
        area = sum(faces[k]["area"] for k in comp)
        if area >= MAX_HOLE_M2:
            continue
        # enclosed: every neighbour outside the component is rock, and no face of it lies on the band's edge (a face
        # with a neighbour outside the band set is on the edge) — only then it is a hole in the wall
        enclosed = True
        for k in comp:
            nbrs = adjacency.get(k, ())
            if len(nbrs) < 3 and faces[k]["area"] > 0.0:
                enclosed = False      # a band-edge or mesh-edge face
                break
            if any(h not in rock and h not in comp for h in nbrs):
                enclosed = False
                break
        if enclosed:
            rock |= set(comp)
            filled += len(comp)
    # 3. self-check on the chosen faces (the hole fill may have added one): nothing under a pavement sheet
    bad_under = []
    for ti, ob in enumerate(tiles):
        vs = ob.data.vertices
        for k in (k for k in rock if k[0] == ti):
            p = ob.data.polygons[k[1]]
            for i in p.vertices:
                v = vs[i].co
                if pav.ray_cast(Vector((v.x, v.y, v.z + 60.0)), Vector((0, 0, -1)), 59.99)[0] is not None:
                    bad_under.append((ob.name, k[1], round(v.x, 1), round(v.y, 1)))
                    break
    if bad_under:
        raise SystemExit(f"[rock] REFUSED: {len(bad_under)} rock face(s) with a vertex under a pavement sheet — "
                         f"e.g. {bad_under[:5]}")
    # 4. split: one 1GRASS_ROCK_<n> per source tile, the faces' vertices by position (the tile keeps its own)
    overrides = pbr.load_overrides(proj)
    per_zone = defaultdict(lambda: {"faces": 0, "area_m2": 0.0, "rise_max_m": 0.0, "slope_min": 9e9, "slope_max": 0.0})
    made = []
    for ti, ob in enumerate(tiles):
        mine = sorted(k[1] for k in rock if k[0] == ti)
        if not mine:
            continue
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        sel = [bm.faces[i] for i in mine]
        # the new mesh: the selected faces' corners, winding kept (the prep already turned every ground face up)
        vmap, verts, polys, uvs = {}, [], [], []
        for f in sel:
            idx = []
            for v in f.verts:
                k_ = v.index
                if k_ not in vmap:
                    vmap[k_] = len(verts)
                    verts.append(tuple(v.co))
                idx.append(vmap[k_])
            polys.append(idx)
            # UV: a wall projection per face — u along the wall's own horizontal strike, v up the face (a planar
            # top-down projection would stretch the tile 1.5-3x on a face this steep)
            nrm = f.normal
            h = math.hypot(nrm.x, nrm.y)
            if h < 0.2:
                uvs.append([(v.co.x / UV_TILE, v.co.y / UV_TILE) for v in f.verts])
            else:
                tx, ty = -nrm.y / h, nrm.x / h
                uvs.append([((v.co.x * tx + v.co.y * ty) / UV_TILE, v.co.z / UV_TILE) for v in f.verts])
            fz = faces[(ti, f.index)]
            rec = per_zone[fz["zone"]]
            rec["faces"] += 1
            rec["area_m2"] += fz["area"]
            rec["rise_max_m"] = max(rec["rise_max_m"], fz["rise"])
            rec["slope_min"] = min(rec["slope_min"], fz["slope"])
            rec["slope_max"] = max(rec["slope_max"], fz["slope"])
        name = f"{ROCK}_{ob.name.split('_')[-1]}"
        nme = bpy.data.meshes.new(name)
        nme.from_pydata(verts, [], polys)
        nme.update()
        uv = nme.uv_layers.new(name="UVMap")
        li = 0
        for pi, poly in enumerate(nme.polygons):
            for q in range(len(poly.vertices)):
                uv.data[li].uv = uvs[pi][q]
                li += 1
        for poly in nme.polygons:
            poly.use_smooth = True
        nob = bpy.data.objects.new(name, nme)
        for col in ob.users_collection:
            col.objects.link(nob)
        nob.matrix_world = ob.matrix_world.copy()
        pbr.setup_material(bpy, nob, overrides=overrides)
        # the tile loses them (faces and the vertices only they used)
        bmesh.ops.delete(bm, geom=sel, context="FACES")
        bm.to_mesh(me)
        bm.free()
        me.update()
        if len(nme.vertices) > VERT_CAP:
            raise SystemExit(f"[rock] {name} {len(nme.vertices)} vertices over the AC cap {VERT_CAP}")
        made.append((name, ob.name, len(nme.vertices), len(nme.polygons)))
    if not made:
        print(f"[rock] {len(faces)} faces in {len(bands)} band(s), none at {slope_min} m/m or steeper — nothing split")
        return
    # 5. conservation: tiles before == tiles after + rock
    for name, src, nv, nf in made:
        after = len(bpy.data.objects[src].data.polygons)
        if after + nf != faces_before[src]:
            raise SystemExit(f"[rock] {src}: {faces_before[src]} faces before, {after} + {nf} rock after — a face was made or lost")
    res = pbr.resolve(ROCK + "_0", overrides)
    rep = {"_doc": "tools/rock_faces_blend.py (ledger 0054 P4 buildings + rock): the cut faces split out of the ground tiles",
           "params": {"slope_min_m_per_m": slope_min, "band_pad_m": BAND_PAD_M, "min_rise_m": MIN_RISE_M, "min_patch_m2": MIN_PATCH_M2,
                      "max_hole_m2": MAX_HOLE_M2, "uv_tile_m": UV_TILE},
           "texture": {"key": res["key"], "diffuse": str(res["diffuse"]), "normal": str(res["normal"]),
                       "overridden": res["overridden"]},
           "bands": len(bands), "faces_in_bands": len(faces), "steep_under_pavement_left_grass": n_under, "rock_raw": n_raw, "patches_dropped": dropped,
           "holes_filled": filled, "rock_faces": len(rock), "rock_area_m2": round(sum(faces[k]["area"] for k in rock), 1),
           "thin_triangles_in_bands_before_split": n_thin_before,
           "meshes": [{"name": n, "from": s, "vertices": v, "faces": f} for n, s, v, f in made],
           "zones": {z: {"faces": r["faces"], "area_m2": round(r["area_m2"], 1), "rise_max_m": round(r["rise_max_m"], 2),
                         "slope_min": round(r["slope_min"], 2), "slope_max": round(min(r["slope_max"], 99.0), 2)}
                     for z, r in sorted(per_zone.items())}}
    (proj / "data" / "rock_faces.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    # the kn5 writer reads every texture from the packed image data (the prep and the freeway drape pack theirs the same
    # way): an unpacked rock image leaves the writer with "Image not packed" and no kn5
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"[rock] pack_all warning: {e}")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    print(f"[rock] {len(rock)} faces / {rep['rock_area_m2']} m2 of cut face at {slope_min} m/m or steeper in {len(per_zone)} of "
          f"{len(bands)} bands -> {len(made)} mesh(es) {', '.join(n for n, *_ in made)} ({sum(v for _, _, v, _ in made)} "
          f"vertices); {n_raw} raw ({n_under} steep faces under a pavement left grass), {dropped} in small patches back to grass, {filled} hole faces filled; thin toe "
          f"triangles in the bands {n_thin_before}; texture {res['diffuse'].name if res['diffuse'] else None}"
          f"{' (override)' if res['overridden'] else ''}; saved {blend.name} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()

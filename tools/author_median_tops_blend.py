"""Give every raised median's grass top its own object, so it stays grass (ledger 0055, "Known defect": every Lake Murray
median showed the road's asphalt between its curbs; Kevin's finish list, the Mac 2026-11-23: option (a)).

    blender --background --python-exit-code 1 --python tools/author_median_tops_blend.py -- <project>
            [--blend <loop.blend>] [--save-as <copy.blend>] [--only <line>:<first row>]

WHY. tools/author_median_blend.py joins each island's top deck into TERRAIN, 0.185 m over the slab the island stands on.
The prep (engine-july scripts/ac/build_kn5_loop.py, _conform_and_reseat) sets EVERY 1GRASS vertex that has pavement
straight above or below it to the deck less 0.02 m, released ground or not, and clamps any grass over the lowest road
or kerb sheet. An island stands on pavement, so its whole top went 0.02 m under the road: 2,486 of 2,486 rows measured
on the 0.20.3 build. The prep of record is not changed. What the prep takes as ground is a NAME: an object whose name
starts with 1GRASS. So the top leaves TERRAIN for an object the prep does not pin.

WHAT. Opt-in, track.config.json route.median_tops {"object": "<name>"}; key absent = no-op, the blend not saved.
Every loose strip of TERRAIN that stands DECK_OVER_M over a road surface on every vertex (the median tool's deck: found
by what it is, not by an index) is moved, face for face and vertex for vertex, into the named object, its faces wound
UP (the prep flips 1ROAD / 1GRASS / 1KERB up, not this one). Nothing else in TERRAIN moves. A loose strip with no road
under it (College's bank between its two roads) is real ground and stays.

THE NAME. In AC the physical surface of a mesh IS its name: the digits, then a surfaces.ini KEY (1GRASS -> GRASS). The
same name picks the mesh's material row in the engine's table (scripts/ac/pbr.py TEXTURES). A top that kept the GRASS
key would be named 1GRASS... and be pinned. The engine's table has one other physical turf row, 1LAWN (KEY=LAWN), so
the object is 1LAWN_<something>; scripts/ac/track_folder.py writes this track's LAWN block with GRASS's own values
(opt-in surfaces.lawn_as_grass), so a car on an island is on grass, exactly.

Self-checks (exit 1, NOT saved): every vertex of a moved strip stands DECK_OVER_M +- DECK_TOL_M over the road; no strip
is part deck, part not; every island row at least MIN_ROW_W_M wide (data/median_bands.json) has a moved face under at
least two of three points: its centre and two points inside the deck as built (a quarter of the band's width, or half
the deck's own half width where the island tapers to its nose); a row with the top at only two of them, and an island
the scene holds no deck for at all, are written into the report, not hidden; TERRAIN loses exactly the moved faces and vertices; every moved face faces up.
Writes data/median_tops.json. Idempotent: a scene whose object already carries the property `median_tops` is left alone.
--only <line>:<first row> moves ONE island (the scratch test before all of them): MAINLINE:1540."""
import json
import math
import sys
from pathlib import Path

DECK_OVER_M = 0.185       # tools/author_median_blend.py: CURB_H 0.18 + 0.005
DECK_TOL_M = 0.06         # [invented] the deck against the road's own triangles: measured 0.141 to 0.228 m on Lake Murray
#                           (7 vertices of 4 strips stand more than 0.03 off, where the road's cross-section turns under them)
MIN_ROW_W_M = 1.2         # a row narrower than this is a nose's taper (source/college_r2/median_tops_check.py's)
LOOSE_MAX_VERTS = 6000    # [invented] a loose part of TERRAIN larger than this is ground, never a median's deck
NOSE_VERTS, NOSE_HALF_M, DECK_INSET_M = 3, 0.25, 0.22   # tools/author_median_blend.py: an island's last three rows taper
END_IN_M = 0.3            # [invented] an island's end row is measured this far inside it (the row itself is the deck's edge)


def deck_half(w, k, n):
    """the BUILT deck's half width at row k of an island of n rows whose band is w wide there (the median tool's rule)"""
    half = 0.5 * w
    for si in (k, n - 1 - k):
        if si < NOSE_VERTS:
            half = min(half, NOSE_HALF_M + (0.5 * w - NOSE_HALF_M) * si / NOSE_VERTS)
    return max(0.05, half - DECK_INSET_M)


def die(msg):
    print("[median-tops] FATAL " + msg)
    raise SystemExit(1)


def spec(cfg):
    s = (cfg.get("route") or {}).get("median_tops")
    if not s:
        return None
    name = str(s.get("object") or "")
    if not name.upper().startswith("1LAWN"):
        die(f"route.median_tops.object {name!r}: the name is the surface and the material (1LAWN...: see this file's header)")
    return {"object": name}


def islands(proj):
    """[{line, first, last, rows: [(x, z, nx, nz, w)]}] off data/centerline.local.json + data/median_bands.json"""
    data = Path(proj) / "data"
    P = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    mb = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))
    lines = [("MAINLINE", P, mb["island_w_by_vertex"])]
    for ci in mb.get("connector_islands") or []:
        lines.append((ci["name"], ci["points_xyz_m"], ci["island_w_by_point"]))
    out = []
    for name, pts, iw in lines:
        m, k = len(pts), 0
        while k < m:
            if iw[k] <= 0:
                k += 1
                continue
            j = k
            while j < m and iw[j] > 0:
                j += 1
            rows = []
            for r in range(k, j):
                a, b = pts[max(0, r - 1)], pts[min(m - 1, r + 1)]
                tx, tz = b[0] - a[0], b[2] - a[2]
                L = math.hypot(tx, tz) or 1.0
                rows.append((pts[r][0], pts[r][2], -tz / L, tx / L, float(iw[r])))
            out.append({"line": name, "first": k, "last": j - 1, "rows": rows})
            k = j
    return out


def main():
    import bmesh
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        die("usage: ... -- <project> [--blend <loop.blend>] [--save-as <copy>] [--only <line>:<first row>]")
    proj = Path(argv[0])
    opt = {k: argv[argv.index(k) + 1] for k in ("--blend", "--save-as", "--only") if k in argv}
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    sp = spec(cfg)
    if sp is None:
        print("[median-tops] route.median_tops not declared: nothing to do, the blend not opened")
        return
    blend = Path(opt.get("--blend") or proj / "loop.blend")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    have = bpy.data.objects.get(sp["object"])
    if have is not None and have.get("median_tops"):
        print(f"[median-tops] {sp['object']} already carries the tops ({have['median_tops']}): nothing to do, nothing saved")
        return
    if have is not None:
        die(f"an object {sp['object']} is in the scene and is not this tool's")
    terrain = bpy.data.objects.get("TERRAIN")
    if terrain is None or terrain.type != "MESH":
        die("no TERRAIN mesh in the scene")
    isl = islands(proj)
    only = None
    if "--only" in opt:
        ln, first = opt["--only"].rsplit(":", 1)
        only = next((i for i, s in enumerate(isl) if s["line"] == ln and s["first"] == int(first)), None)
        if only is None:
            die(f"--only {opt['--only']}: no island starts there; islands: {[(s['line'], s['first'], s['last']) for s in isl]}")

    # the road's surfaces, world space (Blender x east, y north, z up; the data's z is Blender's y)
    rv, rf = [], []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and (ob.name == "ROAD" or ob.name.upper().startswith("1ROAD")):
            base, mw = len(rv), ob.matrix_world
            rv += [mw @ v.co for v in ob.data.vertices]
            rf += [[base + i for i in p.vertices] for p in ob.data.polygons]
    if not rf:
        die("no ROAD surface in the scene")
    road = BVHTree.FromPolygons(rv, rf)
    down = Vector((0.0, 0.0, -1.0))

    def over_road(co):
        hit = road.ray_cast(Vector((co.x, co.y, co.z + 0.5)), down, 3.0)
        return None if hit[0] is None else co.z - hit[0].z

    bm = bmesh.new()
    bm.from_mesh(terrain.data)
    bm.verts.ensure_lookup_table()
    mw = terrain.matrix_world
    n_v0, n_f0 = len(bm.verts), len(bm.faces)
    # loose parts of TERRAIN
    seen = [False] * n_v0
    strips, mixed = [], []
    for v0 in bm.verts:
        if seen[v0.index]:
            continue
        comp, stack = [], [v0]
        seen[v0.index] = True
        big = False
        while stack:
            v = stack.pop()
            comp.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if not seen[o.index]:
                    seen[o.index] = True
                    stack.append(o)
        if len(comp) > LOOSE_MAX_VERTS:
            continue
        d = [over_road(mw @ v.co) for v in comp]
        ok = [x is not None and abs(x - DECK_OVER_M) <= DECK_TOL_M for x in d]
        if all(ok):
            strips.append((comp, d))
        elif any(ok) and sum(ok) > 0.5 * len(ok):
            mixed.append((len(comp), sum(ok), [round(x, 3) if x is not None else None for x, k in zip(d, ok) if not k][:6],
                          [round(c, 1) for c in (mw @ comp[0].co)]))
    if mixed:
        die(f"{len(mixed)} loose strips of TERRAIN are mostly a median's deck but not on every vertex "
            f"(vertices, on the deck, the others' heights over the road, where): {mixed[:5]}")
    if not strips:
        die("no median deck found in TERRAIN (a loose strip standing %.3f m over the road)" % DECK_OVER_M)

    # each strip's island: the island whose rows its vertices stand nearest
    def island_of(comp):
        c = mw @ comp[len(comp) // 2].co
        best = None
        for i, s in enumerate(isl):
            for (x, z, _nx, _nz, w) in s["rows"]:
                dd = math.hypot(c.x - x, c.y - z)
                if dd <= 0.5 * w + 1.5 and (best is None or dd < best[0]):
                    best = (dd, i)
        return None if best is None else best[1]

    take = []
    per = {}
    unowned = 0
    for comp, d in strips:
        i = island_of(comp)
        if i is None:
            unowned += 1
            continue
        if only is not None and i != only:
            continue
        take.append((comp, d, i))
        per.setdefault(i, {"strips": 0, "vertices": 0, "faces": 0})
        per[i]["strips"] += 1
        per[i]["vertices"] += len(comp)
    if unowned:
        die(f"{unowned} deck strips stand on no island of data/median_bands.json")
    if not take:
        die("no deck strip for the island asked")

    # the new mesh: the strips' own vertices and faces, world space, wound up
    verts, faces, moved_faces, moved_verts = [], [], [], []
    d_all = []
    for comp, d, i in take:
        idx = {}
        for v in comp:
            idx[v.index] = len(verts)
            verts.append(tuple(mw @ v.co))
            moved_verts.append(v)
        d_all += d
        fs = {f for v in comp for f in v.link_faces}
        for f in fs:
            if any(v.index not in idx for v in f.verts):
                die("a deck face shares a vertex with another part of TERRAIN")
            loop = [idx[v.index] for v in f.verts]
            a, b, c = (Vector(verts[k]) for k in loop[:3])
            if (b - a).cross(c - a).z < 0.0:
                loop.reverse()
            faces.append(loop)
            moved_faces.append(f)
            per[i]["faces"] += 1
    me = bpy.data.meshes.new(sp["object"])
    me.from_pydata(verts, [], faces)
    me.update()
    if any(p.normal.z <= 0.0 for p in me.polygons):
        die("a moved face does not face up")
    me.uv_layers.new(name="UVMap")
    ob = bpy.data.objects.new(sp["object"], me)
    for col in terrain.users_collection:
        col.objects.link(ob)
    bmesh.ops.delete(bm, geom=moved_verts, context="VERTS")
    if len(bm.verts) != n_v0 - len(verts) or len(bm.faces) != n_f0 - len(faces):
        die(f"TERRAIN lost {n_v0 - len(bm.verts)} vertices and {n_f0 - len(bm.faces)} faces, the tops are {len(verts)} and {len(faces)}")
    bm.to_mesh(terrain.data)
    bm.free()
    terrain.data.update()

    # every island row wide enough has the top under its centre and quarter points
    top = BVHTree.FromPolygons([Vector(v) for v in verts], faces)
    rows_checked = rows_bare = rows_one_side = 0
    bare, one_side = [], []
    no_deck = [i for i in range(len(isl)) if i not in per and (only is None or i == only)]
    for i, s in enumerate(isl):
        if (only is not None and i != only) or i in no_deck:
            continue
        for r, (x, z, nx, nz, w) in enumerate(s["rows"]):
            if w < MIN_ROW_W_M:
                continue
            rows_checked += 1
            q = min(0.25 * w, 0.5 * deck_half(w, r, len(s["rows"])))
            # an island's first and last row IS the deck's end edge: measured END_IN_M inside the island along its line
            n_rows = len(s["rows"])
            sx, sz = 0.0, 0.0
            if n_rows > 1 and r in (0, n_rows - 1):
                ox, oz = s["rows"][1 if r == 0 else n_rows - 2][:2]
                L = math.hypot(ox - x, oz - z) or 1.0
                sx, sz = (ox - x) / L * END_IN_M, (oz - z) / L * END_IN_M
            miss = []
            for o in (0.0, q, -q):
                px, py = x + sx + nx * o, z + sz + nz * o
                rz = road.ray_cast(Vector((px, py, 1.0e4)), down)[0]
                tz = top.ray_cast(Vector((px, py, 1.0e4)), down)[0]
                if tz is None or (rz is not None and tz.z - rz.z < 0.05):
                    miss.append(round(o, 2))
            # the row's verdict is the measure's own (source/college_r2/median_tops_check.py): two of its three points
            if len(miss) >= 2:
                rows_bare += 1
                bare.append((s["line"], s["first"] + r, miss))
            elif miss:
                rows_one_side += 1
                one_side.append({"line": s["line"], "row": s["first"] + r, "no_top_at_offset_m": miss[0], "band_w_m": round(w, 2)})
    if rows_bare:
        die(f"{rows_bare} of {rows_checked} island rows have no top over the road at two of their three points: {bare[:10]}")
    rep = {"_doc": "tools/author_median_tops_blend.py (ledger 0055): the medians' grass tops moved out of TERRAIN into their own "
                   "object, which the prep does not pin under the road",
           "object": sp["object"], "only": opt.get("--only"),
           "islands": [{"line": isl[i]["line"], "rows": [isl[i]["first"], isl[i]["last"]], **per[i]} for i in sorted(per)],
           "strips": len(take), "vertices": len(verts), "faces": len(faces),
           "deck_over_the_road_m": {"min": round(min(d_all), 4), "max": round(max(d_all), 4)},
           "rows_checked": rows_checked, "rows_with_no_top": 0,
           "rows_with_the_top_at_two_of_three_points": one_side,
           "_rows_two_of_three_doc": "the built island is narrower than its band in data/median_bands.json on one side there; the "
                                     "row still reads grass by the measure's own rule (two of three points)",
           "islands_with_no_deck_in_the_scene": [{"line": isl[i]["line"], "rows": [isl[i]["first"], isl[i]["last"]],
                                                  "length_rows": isl[i]["last"] - isl[i]["first"] + 1} for i in no_deck],
           "_no_deck_doc": "the scene holds no grass top for these islands (nothing stands 0.185 m over the road between their "
                           "rows), so there is nothing to move: they show the road between their curbs, as before",
           "terrain": {"vertices": [n_v0, n_v0 - len(verts)], "faces": [n_f0, n_f0 - len(faces)]},
           "loose_strips_left_in_terrain_with_no_road_under_them": "left as ground (College's bank top)"}
    ob["median_tops"] = json.dumps({k: rep[k] for k in ("strips", "vertices", "faces", "only")})
    (proj / "data" / "median_tops.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("[median-tops] " + json.dumps({k: v for k, v in rep.items() if k != "_doc"}))
    if "--save-as" in opt:
        bpy.ops.wm.save_as_mainfile(filepath=opt["--save-as"], copy=True)
        print(f"[median-tops] saved a copy: {opt['--save-as']}")
    else:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print(f"[median-tops] saved {blend}")


if __name__ == "__main__":
    main()

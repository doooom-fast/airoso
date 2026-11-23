"""Give every raised median's top its own object, so it stays what it is: grass, or a paved top (ledger 0055, "Known
defect": every Lake Murray median showed the road's asphalt between its curbs; Kevin's finish list, the Mac 2026-11-23:
option (a); ledger 0099 round 3, 2026-11-23: Mission Gorge Rd's two islands are terracotta pavers, not grass).

    blender --background --python-exit-code 1 --python tools/author_median_tops_blend.py -- <project>
            [--blend <loop.blend>] [--save-as <copy.blend>] [--only <line>:<first row>]

WHY. tools/author_median_blend.py joins each island's top deck into TERRAIN, 0.185 m over the slab the island stands on.
The prep (engine-july scripts/ac/build_kn5_loop.py, _conform_and_reseat) sets EVERY 1GRASS vertex that has pavement
straight above or below it to the deck less 0.02 m, released ground or not, and clamps any grass over the lowest road
or kerb sheet. An island stands on pavement, so its whole top went 0.02 m under the road: 2,486 of 2,486 rows measured
on the 0.20.3 build. The prep of record is not changed. What the prep takes as ground is a NAME: an object whose name
starts with 1GRASS. So the top leaves TERRAIN for an object the prep does not pin.

WHAT. Opt-in, track.config.json route.median_tops {"object": "<name>"[, "paver": {"object": "<name>", "islands":
[{"line": "<line>", "rows": [<first>, <last>]}]}]}; key absent = no-op, the blend not opened.
Every loose strip of TERRAIN that stands DECK_OVER_M over a road surface on every vertex (the median tool's deck: found
by what it is, not by an index) is moved, face for face and vertex for vertex, into the object of its island, its faces
wound UP (the prep flips 1ROAD / 1GRASS / 1KERB up, not 1LAWN). Nothing else in TERRAIN moves. A loose strip with no
road under it (College's bank between its two roads) is real ground and stays.

THE NAME. In AC the physical surface of a mesh IS its name: the digits, then a surfaces.ini KEY (1GRASS -> GRASS). The
same name picks the mesh's material row in the engine's table (scripts/ac/pbr.py TEXTURES). A top that kept the GRASS
key would be named 1GRASS... and be pinned. The engine's table has one other physical turf row, 1LAWN (KEY=LAWN), so
the grass tops' object is 1LAWN_<something>; scripts/ac/track_folder.py writes this track's LAWN block with GRASS's own
values (opt-in surfaces.lawn_as_grass), so a car on a grass island is on grass, exactly.

THE PAVED TOPS (ledger 0099 round 3). An island the config lists under "paver" (by its line and its first and last
row, exactly as data/median_bands.json builds it: a listed island that is not built is fatal) has a hard top: its
object is 1KERB_PAVER_<something>. KEY=KERB is the surface every street curb and sidewalk of the track already has
(friction, the kerb sound and the wheel rumble with it): no value is invented for it. Its material row is 1KERB_PAVER,
above the red racing kerb's row (scripts/ac/pbr.py), and the track tones the paver with its own texture override. The
prep does not move a 1KERB vertex (it pins 1GRASS under 1ROAD and nothing else), and it seats props on 1KERB as on the
ground, so what stands on a paved island stands on its top.

Self-checks (exit 1, NOT saved): every vertex of a moved strip stands DECK_OVER_M +- DECK_TOL_M over the road; no strip
is part deck, part not; every island row at least MIN_ROW_W_M wide (data/median_bands.json) has a moved face under at
least two of three points: its centre and two points inside the deck as built (a quarter of the band's width, or half
the deck's own half width where the island tapers to its nose); a row with the top at only two of them, and an island
the scene holds no deck for at all, are written into the report, not hidden; TERRAIN loses exactly the moved faces and vertices; every moved face faces up.
Writes data/median_tops.json. Idempotent, and it CONVERGES: a top still in TERRAIN is moved out; a top already in one
of the two objects but declared for the other (a scene built before its island was declared paved) is moved across; a
scene in which every top already lies in its own object is left alone and not saved.
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
MIN_ISLAND_ROWS = 6       # tools/author_median_blend.py _segments (`if j - i >= 6`): a shorter run of the band is not built as
#                           an island at all (no curb, no deck: its two three-row noses need six rows). Lake Murray has one,
#                           Mission Gorge v54-57: paint only in the scene


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


PAVER_PREFIX = "1KERB_PAVER"   # scripts/ac/pbr.py: its own material row above 1KERB; the surfaces.ini key stays KERB


def spec(cfg):
    s = (cfg.get("route") or {}).get("median_tops")
    if not s:
        return None
    name = str(s.get("object") or "")
    if not name.upper().startswith("1LAWN"):
        die(f"route.median_tops.object {name!r}: the name is the surface and the material (1LAWN...: see this file's header)")
    out = {"object": name}
    pv = s.get("paver")
    if pv:
        pname = str(pv.get("object") or "")
        if not pname.upper().startswith(PAVER_PREFIX):
            die(f"route.median_tops.paver.object {pname!r}: a paved top is named {PAVER_PREFIX}... (KEY=KERB, its own material row)")
        listed = []
        for it in pv.get("islands") or []:
            rows = it.get("rows") or []
            if not it.get("line") or len(rows) != 2:
                die(f"route.median_tops.paver.islands: {it!r} is not {{line, rows: [first, last]}}")
            listed.append((str(it["line"]), int(rows[0]), int(rows[1])))
        if not listed:
            die("route.median_tops.paver names no island")
        if len(set(listed)) != len(listed):
            die("route.median_tops.paver.islands lists an island twice")
        out["paver"] = {"object": pname, "islands": listed}
    return out


def surfaces(sp, isl):
    """{island index: "paver"} for the islands the config lists as paved (every other island is grass); a listed island
    that data/median_bands.json does not build, row for row, is fatal"""
    built = {(s["line"], s["first"], s["last"]): i for i, s in enumerate(isl)}
    out = {}
    for key in (sp.get("paver") or {}).get("islands", []):
        if key not in built:
            die(f"route.median_tops.paver.islands: {key[0]} rows {key[1]}-{key[2]} is not an island of data/median_bands.json; "
                f"that line's islands: {[(f, l) for (ln, f, l) in built if ln == key[0]]}")
        out[built[key]] = "paver"
    return out


def islands(proj, short=False):
    """[{line, first, last, rows: [(x, z, nx, nz, w)]}] off data/centerline.local.json + data/median_bands.json: the runs
    of the band the median tool builds as islands (MIN_ISLAND_ROWS or more); short=True: the runs it does not"""
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
            if (j - k >= MIN_ISLAND_ROWS) != short:
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
    isl = islands(proj)
    paved = surfaces(sp, isl)
    names = {"grass": sp["object"]}
    if sp.get("paver"):
        names["paver"] = sp["paver"]["object"]

    def kind_of(i):
        return paved.get(i, "grass")

    blend = Path(opt.get("--blend") or proj / "loop.blend")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    have = {}
    for kind, name in names.items():
        ob = bpy.data.objects.get(name)
        if ob is not None:
            if not ob.get("median_tops"):
                die(f"an object {name} is in the scene and is not this tool's")
            have[kind] = ob
    terrain = bpy.data.objects.get("TERRAIN")
    if terrain is None or terrain.type != "MESH":
        die("no TERRAIN mesh in the scene")
    only = None
    if "--only" in opt:
        if have:
            die("--only is the scratch test on a scene this tool has not been over; this scene already holds "
                + ", ".join(sorted(o.name for o in have.values())))
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

    def island_of(c):
        best = None
        for i, s in enumerate(isl):
            for (x, z, _nx, _nz, w) in s["rows"]:
                dd = math.hypot(c.x - x, c.y - z)
                if dd <= 0.5 * w + 1.5 and (best is None or dd < best[0]):
                    best = (dd, i)
        return None if best is None else best[1]

    # 1. the decks still in TERRAIN: every one of them on a scene this tool has not been over, none on one it has
    bm = bmesh.new()
    bm.from_mesh(terrain.data)
    bm.verts.ensure_lookup_table()
    mw = terrain.matrix_world
    n_v0, n_f0 = len(bm.verts), len(bm.faces)
    seen = [False] * n_v0
    strips, mixed = [], []
    for v0 in bm.verts:
        if seen[v0.index]:
            continue
        comp, stack = [], [v0]
        seen[v0.index] = True
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
    if strips and have:
        die(f"{len(strips)} deck strips are still in TERRAIN and the scene already holds {sorted(o.name for o in have.values())}: "
            f"a scene half moved is not one this tool makes")
    if not strips and not have:
        die("no median deck found in TERRAIN (a loose strip standing %.3f m over the road)" % DECK_OVER_M)

    # every top as one record, wherever it lies now: its island, where it lies (src), its vertices (world) and faces
    tops = []
    unowned = 0
    for comp, d in strips:
        i = island_of(mw @ comp[len(comp) // 2].co)
        if i is None:
            unowned += 1
            continue
        if only is not None and i != only:
            continue
        idx = {v.index: k for k, v in enumerate(comp)}
        faces = []
        for f in {f for v in comp for f in v.link_faces}:
            if any(v.index not in idx for v in f.verts):
                die("a deck face shares a vertex with another part of TERRAIN")
            faces.append((f.index, [idx[v.index] for v in f.verts]))
        faces.sort()
        tops.append({"island": i, "src": "TERRAIN", "verts": [mw @ v.co for v in comp], "faces": [t[1] for t in faces],
                     "d": d, "bm_verts": comp})
    if unowned:
        die(f"{unowned} deck strips stand on no island of data/median_bands.json")
    for kind, ob in have.items():
        me, mwo = ob.data, ob.matrix_world
        parent = list(range(len(me.vertices)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for pl in me.polygons:
            vs = list(pl.vertices)
            for k in vs[1:]:
                ra, rb = find(vs[0]), find(k)
                if ra != rb:
                    parent[rb] = ra
        groups, pf = {}, {}
        for vi in range(len(me.vertices)):
            groups.setdefault(find(vi), []).append(vi)
        for pl in me.polygons:
            pf.setdefault(find(pl.vertices[0]), []).append(list(pl.vertices))
        for root in sorted(groups):
            vis = groups[root]
            idx = {vi: k for k, vi in enumerate(vis)}
            verts = [mwo @ me.vertices[vi].co for vi in vis]
            i = island_of(verts[len(verts) // 2])
            if i is None:
                die(f"a part of {ob.name} ({len(vis)} vertices near {[round(c, 1) for c in verts[0]]}) stands on no island of "
                    f"data/median_bands.json")
            tops.append({"island": i, "src": kind, "verts": verts, "faces": [[idx[vi] for vi in f] for f in pf.get(root, [])],
                         "d": [over_road(c) for c in verts], "bm_verts": None})
    if not tops:
        die("no deck strip for the island asked")

    move = [t for t in tops if t["src"] != kind_of(t["island"])]
    if not move:
        bm.free()
        held = {k: sum(1 for t in tops if t["src"] == k) for k in names}
        print("[median-tops] every top already lies in its own object ("
              + ", ".join(f"{names[k]}: {held[k]}" for k in names) + "): nothing to do, nothing saved")
        return
    # a top that moves is checked as a deck where it stands now, whichever object it leaves
    for t in move:
        bad = [x for x in t["d"] if x is None or abs(x - DECK_OVER_M) > DECK_TOL_M]
        if bad:
            s_ = isl[t["island"]]
            die(f"a top of island {s_['line']} {s_['first']}-{s_['last']} in {t['src']} is not a deck any more "
                f"({len(bad)} of {len(t['d'])} vertices off {DECK_OVER_M} m over the road, e.g. {bad[:3]})")
    no_paver = [i for i in paved if not any(t["island"] == i for t in tops) and (only is None or i == only)]
    if no_paver:
        die("listed as paved, with no top in the scene: " + str([(isl[i]["line"], isl[i]["first"], isl[i]["last"]) for i in no_paver]))

    # 2. each object's mesh, built from its islands' tops in island order (world space, wound up)
    per, built = {}, {}
    for kind in names:
        mine = sorted((t for t in tops if kind_of(t["island"]) == kind),
                      key=lambda t: (t["island"], round(min(c.x for c in t["verts"]), 4), round(min(c.y for c in t["verts"]), 4)))
        verts, faces = [], []
        for t in mine:
            base = len(verts)
            verts += [tuple(c) for c in t["verts"]]
            for loop in t["faces"]:
                loop = [base + k for k in loop]
                a, b, c = (Vector(verts[k]) for k in loop[:3])
                if (b - a).cross(c - a).z < 0.0:
                    loop.reverse()
                faces.append(loop)
            e = per.setdefault(t["island"], {"surface": kind, "strips": 0, "vertices": 0, "faces": 0})
            e["strips"] += 1
            e["vertices"] += len(t["verts"])
            e["faces"] += len(t["faces"])
        built[kind] = (verts, faces, len(mine))
    identity = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)
    for kind, (verts, faces, n_strips) in built.items():
        ob = have.get(kind)
        if not faces:
            if ob is not None:                       # no island wears this top any more: its object goes
                old = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                bpy.data.meshes.remove(old)
            continue
        me = bpy.data.meshes.new(names[kind])
        me.from_pydata(verts, [], faces)
        me.update()
        if any(pl.normal.z <= 0.0 for pl in me.polygons):
            die("a moved face does not face up")
        me.uv_layers.new(name="UVMap")
        if ob is None:
            ob = bpy.data.objects.new(names[kind], me)
            for col in terrain.users_collection:
                col.objects.link(ob)
        else:
            if tuple(round(x, 9) for row in ob.matrix_world for x in row) != identity:
                die(f"{ob.name} carries a transform: its mesh cannot be rebuilt in world space")
            old = ob.data
            ob.data = me
            bpy.data.meshes.remove(old)
        ob["median_tops"] = json.dumps({"strips": n_strips, "vertices": len(verts), "faces": len(faces), "only": opt.get("--only")})
    out_v = [v for t in tops if t["src"] == "TERRAIN" for v in t["bm_verts"]]
    out_f = sum(len(t["faces"]) for t in tops if t["src"] == "TERRAIN")
    if out_v:
        bmesh.ops.delete(bm, geom=out_v, context="VERTS")
        if len(bm.verts) != n_v0 - len(out_v) or len(bm.faces) != n_f0 - out_f:
            die(f"TERRAIN lost {n_v0 - len(bm.verts)} vertices and {n_f0 - len(bm.faces)} faces, the tops are {len(out_v)} and {out_f}")
        bm.to_mesh(terrain.data)
        terrain.data.update()
    bm.free()

    # every island row wide enough has a top under its centre and quarter points
    all_v, all_f = [], []
    for verts, faces, _n in built.values():
        base = len(all_v)
        all_v += [Vector(v) for v in verts]
        all_f += [[base + k for k in f] for f in faces]
    top = BVHTree.FromPolygons(all_v, all_f)
    d_all = [x for t in tops for x in t["d"] if x is not None]
    rows_checked = rows_bare = 0
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
                one_side.append({"line": s["line"], "row": s["first"] + r, "no_top_at_offset_m": miss[0], "band_w_m": round(w, 2)})
    if rows_bare:
        die(f"{rows_bare} of {rows_checked} island rows have no top over the road at two of their three points: {bare[:10]}")
    tot = {k: sum(e[k] for e in per.values()) for k in ("strips", "vertices", "faces")}
    by_kind = {kind: {"object": names[kind], "islands": sum(1 for e in per.values() if e["surface"] == kind),
                      **{k: sum(e[k] for e in per.values() if e["surface"] == kind) for k in ("strips", "vertices", "faces")}}
               for kind in names}
    rep = {"_doc": "tools/author_median_tops_blend.py (ledgers 0055, 0099 round 3): the medians' tops moved out of TERRAIN into their "
                   "own objects, which the prep does not pin under the road: grass tops (1LAWN...) and paved tops (1KERB_PAVER...)",
           "object": sp["object"], "only": opt.get("--only"),
           "islands": [{"line": isl[i]["line"], "rows": [isl[i]["first"], isl[i]["last"]], **per[i]} for i in sorted(per)],
           **tot, "grass": by_kind["grass"], "paver": by_kind.get("paver"),
           "moved_this_run": {"out_of_terrain": sum(1 for t in move if t["src"] == "TERRAIN"),
                              "from_one_top_object_to_the_other": sum(1 for t in move if t["src"] != "TERRAIN")},
           "deck_over_the_road_m": {"min": round(min(d_all), 4), "max": round(max(d_all), 4)},
           "rows_checked": rows_checked, "rows_with_no_top": 0,
           "rows_with_the_top_at_two_of_three_points": one_side,
           "_rows_two_of_three_doc": "the built island is narrower than its band in data/median_bands.json on one side there; the "
                                     "row still reads as topped by the measure's own rule (two of three points)",
           "islands_with_no_deck_in_the_scene": [{"line": isl[i]["line"], "rows": [isl[i]["first"], isl[i]["last"]],
                                                  "length_rows": isl[i]["last"] - isl[i]["first"] + 1} for i in no_deck],
           "_no_deck_doc": "the scene holds no top for these islands (nothing stands 0.185 m over the road between their "
                           "rows), so there is nothing to move: they show the road between their curbs, as before",
           "band_runs_too_short_to_be_islands": [{"line": s["line"], "rows": [s["first"], s["last"]]} for s in islands(proj, short=True)],
           "_short_runs_doc": "runs of the median band under %d rows: tools/author_median_blend.py builds no island for them (no "
                              "curb, no top), so they are no part of this step" % MIN_ISLAND_ROWS,
           "terrain": {"vertices": [n_v0, n_v0 - len(out_v)], "faces": [n_f0, n_f0 - out_f]},
           "loose_strips_left_in_terrain_with_no_road_under_them": "left as ground (College's bank top)"}
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

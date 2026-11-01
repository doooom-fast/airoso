"""Loop front-end: prep a Blender-FIRST project's loop.blend for AC and save blender/<slug>.blend.

This is the San Diego (k10-san-diego) build philosophy, ported as an alternate front-end: the
project's ``loop.blend`` is the source of truth (Kevin shapes it in Blender), and this pass CONSUMES
it — renames the working meshes to AC surface conventions, gives them tiling UVs + PBR materials,
welds/holes-fills the grass, drops the AC_START/PIT/TIME/HOTLAP dummies computed from the real
centreline, packs textures, and saves ``blender/<slug>.blend``. ``export_kn5_addon`` then binds
shaders + exports the real kn5 (see scripts/build_loop.sh for the full pipeline).

THIS IS A DIFFERENT PROGRAM from scripts/ac/build_kn5.py (the OBJ-import pipeline). The two must
never be merged: this one edits an existing hand-authored scene; that one assembles a scene from
generated, audited OBJs. (docs: k10-colorado ENGINE-MIGRATION.md — "build_kn5.py is two programs".)

    blender --background --python scripts/ac/build_kn5_loop.py -- <project-dir>

The project dir is EXTERNAL to this repo (a consumer repo like k10-san-diego passes its own
project path); everything engine-side resolves against this file's location, never the project's.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# engine repo root — for `from scripts.ac import pbr` / `from scripts.geometry import dummies`
# regardless of where Blender was launched from or where the project dir lives.
_REPO = Path(__file__).resolve().parents[2]

# working mesh name (in loop.blend) -> AC-convention name. `1` prefix = physical surface keyed to
# surfaces.ini (ROAD/KERB/GRASS); 1WALL = physical collision barrier (guardrail).
AC_NAME = {
    "ROAD": "1ROAD_road",
    "KERB": "1KERB_kerb",
    # The street curb+sidewalk ships as the working mesh "CURB". Remap it to a 1KERB_ physical
    # surface so (a) it's collidable — the car can't fall through the road-edge/grass gap it
    # bridges — and (b) it gets the face-up flip below. Without this it stayed "CURB":
    # non-physical AND textureless=black.
    "CURB": "1KERB_sidewalk",
    "TERRAIN": "1GRASS",
    "GUARDRAIL": "1WALL_guard",
}
UV_TILE = 4.0  # metres per texture tile (top-down planar projection)

# AC/ksEditor hard per-mesh vertex cap (16-bit indices). Meshes are split under SPLIT_CAP; anything
# STILL over VERT_CAP after split+weld is FATAL — AC silently drops over-cap meshes, and a dropped
# PHYSICAL mesh means the car falls through (the invisible-forest / fall-through bug class).
VERT_CAP = 65535
SPLIT_CAP = 60000
# TERRAIN meshes tile by BALANCED BISECTION (ledger 0046): the tiered terrain is fine along the roads and coarse
# far out, so equal-width bands put most of the vertices into whichever band holds the most road (the western
# one already held ~60k of the cap before the tiers); a recursive median split lands every tile under SPLIT_CAP
# whatever the density. GRASS_FAR is the visual-only far ring (no digit prefix: no physics, no gates, no GrassFX).
TERRAIN_TILES = ("1GRASS", "GRASS_FAR")

# freeway groups whose winding must not matter: after the loop's local->Blender reflection their
# faces would point inward, so double-side them (append reversed faces) — a barrier/structure must
# render AND collide from both sides. Drivable surfaces are handled by the face-up flip pass.
DOUBLE_SIDE = ("1WALL", "HWYSTRUCT")

# --- terrain contact conform (the CO road-grounding pattern, loop-path edition) -------------------
# The hand-authored TERRAIN follows the DEM; the hand-shaped ROAD does not follow it back — on the
# western hills the deck ended up 1.8–6.7 m over the grass DIRECTLY beneath it (203+ red samples on
# the kn5 ground gate). Construction pins the world to the road: under the pavement footprint the
# terrain is PINNED to deck−GROUND_CLEAR (up or down), a FEATHER band blends back to natural ground,
# and the corridor is SUBDIVIDED first so coarse terrain triangles can hug the deck instead of
# chording (the adaptive-fine-grid move). Declared bridge spans (the real I-8 crossings) are spared:
# there the pin may only push DOWN — a bridge keeps its trench.
GROUND_CLEAR = 0.02        # m below the deck (the ground gate's ceiling is 0.05)
BAND_M = 3.0               # full-contact shelf past the pavement edge (CO grade_embankment's band)
FEATHER_M = 6.0            # smoothstep blend band beyond the shelf
CORRIDOR_EDGE_M = 4.5      # subdivide terrain edges near the road down to about this length
LAYER_WIN = 30.0           # deck sampling window (no stacked loop legs, but stay safe)
BRIDGE_MATCH_M = 14.0      # centerline pt within this of an OSM bridge way = on the span
BRIDGE_PAD_M = 8.0         # widen each detected span a touch onto the abutments
# --- house / building seat (ledger 0046 fix round 3) -------------------------------------------------------------
# The draft sits each OSM footprint on the ground it can see (its centroid, less HOUSE_SINK_M) and this prep then
# reshapes that ground (conform, pin, feather, the tiered terrain's kept-cell refinement), so a house that rode one
# corner's delta could end up half under a hill whose ground moved under its other corners. Buildings are
# therefore seated on the FINAL ground under their own footprint, after every pass that moves it.
HOUSE_SINK_M = 0.4         # the draft's own sink: build_loop_blend.build_buildings sits a footprint at ground - 0.4
HOUSE_FOOT_M = 0.15        # [invented] the foundation reaches this far below the lowest ground under the footprint
HOUSE_EDGE_STEP_M = 1.5    # [invented] ground is read at the corners, the centroid and every ~1.5 m along each wall
HOUSE_SHOW = 0.5           # [invented] at least this share of a building's height stands above the highest ground under its walls


def _mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def detect_bridge_spans(pts_xyz, origin_lonlat, bridge_ways, *, mirror_x=False,
                        match_m=BRIDGE_MATCH_M, pad_m=BRIDGE_PAD_M):
    """Station ranges [(a_m, b_m), ...] where the loop rides an OSM-declared bridge (its own deck —
    motorway/motorway_link ways are excluded so a freeway bridge crossing OVER the loop can't mark a
    phantom span on the road below). Pure function (no bpy) so it is unit-testable.

    pts_xyz: local (E, up, N) centerline; bridge_ways: [{'hw': ..., 'geom': [[lon, lat], ...]}, ...]."""
    lon0, lat0 = origin_lonlat
    m_lon, m_lat = _mpd(lat0)
    sx = -1.0 if mirror_x else 1.0
    segs = []
    for w in bridge_ways or []:
        if (w.get("hw") or "") in ("motorway", "motorway_link"):
            continue                      # the freeway's own bridges, not the loop's deck
        g = [(sx * (lon - lon0) * m_lon, (lat - lat0) * m_lat) for lon, lat in w.get("geom", [])]
        segs += [(g[i][0], g[i][1], g[i + 1][0], g[i + 1][1]) for i in range(len(g) - 1)]
    if not segs:
        return []

    def near_bridge(x, z):
        for ax, az, bx, bz in segs:
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
            px, pz = ax + t * dx, az + t * dz
            if (x - px) ** 2 + (z - pz) ** 2 <= match_m * match_m:
                return True
        return False

    spans = []
    st = 0.0
    open_a = None
    prev = pts_xyz[0]
    for i, p in enumerate(pts_xyz):
        if i:
            st += math.hypot(p[0] - prev[0], p[2] - prev[2])
            prev = p
        if near_bridge(p[0], p[2]):
            if open_a is None:
                open_a = st
            open_b = st
        elif open_a is not None:
            spans.append((max(0.0, open_a - pad_m), open_b + pad_m))
            open_a = None
    if open_a is not None:
        spans.append((max(0.0, open_a - pad_m), open_b + pad_m))
    return spans


def declare_bridge_spans(proj: Path) -> list[tuple[float, float]]:
    """Detect the loop's real bridge spans and DECLARE them the way every other project does — write
    data/bridge.spans.auto.json + data/finished_centerline.json so the kn5 ground gate applies its
    standard declared-span exemption (a deck over the I-8 trench is SUPPOSED to ride high over the
    grass; that is not a float). finished_centerline is written in the KN5 frame (x, y, -z of the
    local frame): the Blender-first path has no OBJ stage, so the shipped-binary frame IS the
    reference frame the gate samples in. Returns the spans (local stations, metres)."""
    local = json.loads((proj / "data" / "centerline.local.json").read_text())
    pts = [tuple(p) for p in local["points_xyz_m"]]
    widths = local.get("widths_m") or [7.0] * len(pts)
    cfg = json.loads((proj / "track.config.json").read_text())
    bridges_p = proj / "data" / "bridges.cache.json"
    ways = json.loads(bridges_p.read_text()) if bridges_p.exists() else []
    o = local.get("origin") or {}
    spans = []
    if ways and "lon" in o:
        spans = detect_bridge_spans(pts, (o["lon"], o["lat"]), ways,
                                    mirror_x=bool(cfg.get("mirror_x", False)))
    (proj / "data" / "bridge.spans.auto.json").write_text(
        json.dumps([[round(a, 1), round(b, 1)] for a, b in spans]), encoding="utf-8")
    (proj / "data" / "finished_centerline.json").write_text(json.dumps({
        "points_xyz_m": [[round(x, 3), round(y, 3), round(-z, 3)] for x, y, z in pts],
        "widths_m": widths}), encoding="utf-8")
    print(f"[build_kn5_loop] declared {len(spans)} bridge span(s): "
          f"{[(round(a), round(b)) for a, b in spans]}")
    return spans


def _project_dir(argv):
    if "--" not in argv:
        raise SystemExit("usage: blender --background --python build_kn5_loop.py -- <project-dir>")
    rest = argv[argv.index("--") + 1:]
    if not rest:
        raise SystemExit("missing <project-dir>")
    return Path(rest[0]).resolve()


def assert_under_cap(name: str, nverts: int) -> None:
    """Loop-path over-cap guard (the OBJ program's guard lives in build_kn5.py step 2b; this path
    needs its own). FATAL, not a warning: AC silently drops over-cap meshes from render AND
    collision, so a warned-and-shipped over-cap 1ROAD/1GRASS is a guaranteed fall-through."""
    if nverts > VERT_CAP:
        raise SystemExit(f"[build_kn5_loop] FATAL: '{name}' has {nverts} positions (> {VERT_CAP}) "
                         f"even after the split pass — AC silently drops over-cap meshes. "
                         f"Raise the split factor or slim the source mesh. Refusing to export.")


def balanced_face_tiles(centers, face_verts, cap=SPLIT_CAP):
    """Pure (no bpy): face-index groups, each touching at most ``cap`` unique vertices, by recursive
    MEDIAN bisection of the face centres along the group's longer horizontal extent (palm.chunk_mesh's
    rule). Deterministic: ties broken by the other axis, then the face index."""
    out = []

    def nverts(fs):
        return len({v for f in fs for v in face_verts[f]})

    def rec(fs):
        if len(fs) < 2 or nverts(fs) <= cap:
            out.append(fs)
            return
        xs = [centers[f][0] for f in fs]
        ys = [centers[f][1] for f in fs]
        ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
        order = sorted(fs, key=lambda f: (centers[f][ax], centers[f][1 - ax], f))
        h = len(order) // 2
        rec(order[:h])
        rec(order[h:])

    rec(list(range(len(face_verts))))
    return out


def _export_vertex_keys(me):
    """Per polygon of ``me`` TRIANGULATED as the kn5 writer triangulates it, the writer's vertex keys of its corners.
    The writer that runs (blender-assetto-corsa-tools exporter/node_writer.py _split_object_by_materials) takes
    obj.to_mesh(), bmesh.ops.triangulate(faces=all) with its defaults, calc_loop_triangles, calc_tangents, and emits one
    kn5 vertex per unique (position, loop normal, uv, tangent) of a triangle corner, compared as exact floats; past 2**16
    it splits the mesh into meshes of ONE name, which AC drops from collision. A flat-shaded box beam whose quads are a
    hair off planar is two normals per quad corner after the triangulation: the median barriers' 1WALL_guard, 15,136
    Blender vertices and 48,200 corner keys untriangulated, was 65,251 kn5 positions on the v0.19.0 repair round 1 build
    and 67,447 (two meshes of one name, verify_kn5 "DUPLICATE physical mesh '1WALL_guard' x2") after repair round 2 gave
    two more north islands their barrier (ledger 0054). Returns (keys per triangle, the triangulated temporary mesh's
    polygon centres)."""
    import bmesh
    import bpy

    tmp = bpy.data.meshes.new("__writer_count")
    try:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(tmp)
        bm.free()
        tmp.calc_loop_triangles()
        try:
            tmp.calc_tangents()
            tang = True
        except Exception:
            tang = False
        uvl = tmp.uv_layers.active
        loops, verts = tmp.loops, tmp.vertices
        keys = []
        for tri in tmp.loop_triangles:
            ks = []
            for li in tri.loops:
                lp = loops[li]
                ks.append((tuple(verts[lp.vertex_index].co), tuple(lp.normal),
                           tuple(uvl.data[li].uv) if uvl is not None else None,
                           tuple(lp.tangent) if tang else None))
            keys.append(ks)
        centres = [(tuple(p.center)[0], tuple(p.center)[1]) for p in tmp.polygons]
        return keys, centres
    finally:
        bpy.data.meshes.remove(tmp)


def export_vertex_count(face_keys):
    """Pure (no bpy): the number of kn5 vertices the writer emits for these per-polygon corner keys."""
    return len({k for ks in face_keys for k in ks})


def _split_for_writer(ob, cap=SPLIT_CAP):
    """Split a mesh whose WRITER vertex count (_export_vertex_keys) is over VERT_CAP into uniquely-named tiles
    (base_0, base_1, ...) of at most ``cap`` writer vertices each (balanced_face_tiles over the corner keys). The mesh is
    first triangulated exactly as the writer would (so its own triangulation is then a no-op and the count is the
    writer's); each tile keeps its triangles' uvs, smooth flags and materials. Runs after the per-mesh pass (UVs, flips,
    shading final). Returns the tile objects ([] when the mesh fits)."""
    import bmesh
    import bpy

    me = ob.data
    # the writer emits at most one vertex per TRIANGLE corner (a quad is 6, not 4): fewer than the cap fit for certain
    if sum(3 * (len(p.vertices) - 2) for p in me.polygons) <= VERT_CAP:
        return []
    keys, _c = _export_vertex_keys(me)
    n = export_vertex_count(keys)
    if n <= VERT_CAP:
        return []
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    me.update()
    keys, centres = _export_vertex_keys(me)                 # a no-op triangulation now: the same triangles, in order
    if len(keys) != len(me.polygons):
        raise SystemExit(f"[build_kn5_loop] FATAL: {ob.name}: {len(keys)} writer triangles vs {len(me.polygons)} "
                         f"polygons after the triangulation")
    polys = list(me.polygons)
    groups = balanced_face_tiles(centres, keys, cap)
    uvl = me.uv_layers.active
    base = ob.name
    tiles = []
    for k, g in enumerate(groups):
        used, nv, nf, smooth, mats, fuv = {}, [], [], [], [], []
        for fi in g:
            poly = polys[fi]
            idx = []
            for vi in poly.vertices:
                if vi not in used:
                    used[vi] = len(nv)
                    nv.append(tuple(me.vertices[vi].co))
                idx.append(used[vi])
            nf.append(idx)
            smooth.append(poly.use_smooth)
            mats.append(poly.material_index)
            if uvl is not None:
                fuv.append([tuple(uvl.data[li].uv) for li in poly.loop_indices])
        nm = bpy.data.meshes.new(f"{base}_{k}")
        nm.from_pydata(nv, [], nf)
        nm.update()
        for m in me.materials:
            nm.materials.append(m)
        for poly, sm, mi in zip(nm.polygons, smooth, mats):
            poly.use_smooth = sm
            poly.material_index = mi
        if uvl is not None:
            nuv = nm.uv_layers.new(name=uvl.name)
            for poly, uvs in zip(nm.polygons, fuv):
                for li, u in zip(poly.loop_indices, uvs):
                    nuv.data[li].uv = u
        nm.update()
        nob = bpy.data.objects.new(f"{base}_{k}", nm)
        bpy.context.scene.collection.objects.link(nob)
        tiles.append(nob)
    print(f"[build_kn5_loop] split {base} for the kn5 writer ({len(me.vertices)} Blender vertices, {n} writer "
          f"vertices > {VERT_CAP}) -> {len(tiles)} tiles under {cap}")
    bpy.data.objects.remove(ob, do_unlink=True)
    return tiles


def t_junctions(co, boundary_edges, tol=0.001, cell=5.0):
    """Pure (no bpy): [(edge_index, vert_index, t)] for every vertex lying on the INTERIOR of a boundary edge
    (within ``tol`` in 3D, 0 < t < 1 along it) — a T-junction. ``co`` = [(x, y, z)], ``boundary_edges`` =
    [(a, b)] vertex-index pairs; only vertices that are themselves on a boundary edge are candidates, and only
    when the T is real: one of the vertex's own boundary edges runs ALONG the long edge (to its end or to another
    vertex on it). A vertex that merely sits on the line of an edge across a hole (the cleared fold fans, a mouth)
    is not a T and is left alone."""
    nbr = {}
    for a, b in boundary_edges:
        nbr.setdefault(a, set()).add(b)
        nbr.setdefault(b, set()).add(a)
    raw = _t_candidates(co, boundary_edges, tol, cell)
    on_edge = {}
    for ei, v, _t in raw:
        on_edge.setdefault(ei, set()).add(v)
    out = []
    for ei, v, t in raw:
        a, b = boundary_edges[ei]
        ok = on_edge[ei] | {a, b}
        if any(w in ok for w in nbr.get(v, ())):
            out.append((ei, v, t))
    return out


def _t_candidates(co, boundary_edges, tol, cell):
    bverts = sorted({v for e in boundary_edges for v in e})
    buck = {}
    for v in bverts:
        buck.setdefault((int(co[v][0] // cell), int(co[v][1] // cell)), []).append(v)
    out = []
    for ei, (a, b) in enumerate(boundary_edges):
        A, B = co[a], co[b]
        d = (B[0] - A[0], B[1] - A[1], B[2] - A[2])
        L2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
        if L2 < 4 * tol * tol:
            continue
        seen = set()
        for i in range(int(min(A[0], B[0]) // cell) - 1, int(max(A[0], B[0]) // cell) + 2):
            for j in range(int(min(A[1], B[1]) // cell) - 1, int(max(A[1], B[1]) // cell) + 2):
                for v in buck.get((i, j), ()):
                    if v in (a, b) or v in seen:
                        continue
                    seen.add(v)
                    P = co[v]
                    t = ((P[0] - A[0]) * d[0] + (P[1] - A[1]) * d[1] + (P[2] - A[2]) * d[2]) / L2
                    if t <= 1e-6 or t >= 1.0 - 1e-6:
                        continue
                    q = (A[0] + d[0] * t - P[0], A[1] + d[1] * t - P[1], A[2] + d[2] * t - P[2])
                    if q[0] * q[0] + q[1] * q[1] + q[2] * q[2] <= tol * tol:
                        out.append((ei, v, t))
    return out


def _weld_t_junctions(bm, tol=0.001):
    """Close every T-junction in a terrain bmesh WITHOUT moving the surface: a face whose boundary edge carries
    other vertices is replaced by a fan from its centroid through all of them (every fan triangle lies in the old
    face's plane). Ledger 0046: a tiered terrain keeps the graded grid's own triangles under and beside the roads
    (so the seat and this prep reshape exactly the ground they always reshaped) and its finer neighbours leave
    their nodes ON those kept edges; this runs after the conform, when nothing else will move them. Returns the
    number of faces re-fanned (0 on a terrain without T-junctions: nothing touched)."""
    import bmesh  # noqa: F401
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bedges = [e for e in bm.edges if len(e.link_faces) == 1]
    if not bedges:
        return 0
    vobj = list(bm.verts)
    co = [(v.co.x, v.co.y, v.co.z) for v in vobj]
    hits = t_junctions(co, [(e.verts[0].index, e.verts[1].index) for e in bedges], tol)
    if not hits:
        return 0
    by_face = {}
    for ei, vi, t in hits:
        e = bedges[ei]
        by_face.setdefault(e.link_faces[0], []).append((e, vi, t))
    dead_edges = []
    for f, lst in by_face.items():
        ring = []
        for loop in f.loops:
            ring.append(loop.vert)
            on = [(t if e.verts[0] == loop.vert else 1.0 - t, vobj[vi]) for e, vi, t in lst if e == loop.edge]
            ring += [v for _t, v in sorted(on, key=lambda p: p[0])]
            if on:
                dead_edges.append(loop.edge)
        n = len(f.verts)
        c = bm.verts.new((sum(v.co.x for v in f.verts) / n, sum(v.co.y for v in f.verts) / n,
                          sum(v.co.z for v in f.verts) / n))
        mat, smooth = f.material_index, f.smooth
        bm.faces.remove(f)
        for k in range(len(ring)):
            nf = bm.faces.new((c, ring[k], ring[(k + 1) % len(ring)]))
            nf.material_index, nf.smooth = mat, smooth
    for e in dead_edges:
        if e.is_valid and not e.link_faces:
            bm.edges.remove(e)
    return len(by_face)


def _collinear_middle(pts, tol=1e-3, end=1e-3):
    """ledger 0054 P3 repair round 1 (airoso tools/terrain_mend.collinear_middle, the same rule): the index of the one
    of three plan points lying on the segment between the other two (within tol of the line, strictly inside), or None"""
    for k in range(3):
        a, m, b = pts[(k + 1) % 3], pts[k], pts[(k + 2) % 3]
        ex, ey = b[0] - a[0], b[1] - a[1]
        L = math.hypot(ex, ey)
        if L < 10 * tol:
            continue
        t = ((m[0] - a[0]) * ex + (m[1] - a[1]) * ey) / (L * L)
        d = abs((m[0] - a[0]) * ey - (m[1] - a[1]) * ex) / L
        if end < t < 1.0 - end and d <= tol and min(t, 1.0 - t) * L > tol:
            return k
    return None


def _mend_vertical_slivers(bm, rounds=6):
    """ledger 0054 P3 repair round 1 (airoso tools/terrain_mend.mend_vertical_slivers, the same mend): the corridor
    subdivision leaves a T-vertex m on a coarser face's straight edge a-b, and the BEAUTY triangulation after it may cut
    the ear (a, m, b) — no plan area; the pin / feather then moves m off the line and the ear stands up as a one-sided
    vertical fin over a crack (sky through the ground from half the directions; 262 such faces within 80 m of Lake
    Murray's north roads after the author stage had mended its own). Here, BEFORE anything moves (the surface is still
    the old faces' planes), the edge a-b is rotated inside the quad it makes with the face across it — no vertex moves or
    is added — or the ear deleted on the open edge. Returns the number mended."""
    import bmesh
    n = 0
    for _r in range(rounds):
        rot, dele, used = [], [], set()
        for f in bm.faces:
            if len(f.verts) != 3:
                continue
            vs = list(f.verts)
            k = _collinear_middle([(v.co.x, v.co.y) for v in vs])
            if k is None:
                continue
            m = vs[k]
            e = next((e for e in f.edges if m not in e.verts), None)
            if e is None:
                continue
            others = [g for g in e.link_faces if g is not f]
            if not others:
                if f not in used:
                    used.add(f)
                    dele.append((f, e))
                continue
            if len(others) == 1 and len(others[0].verts) == 3 and f not in used and others[0] not in used:
                used.update((f, others[0]))
                rot.append(e)
        if not rot and not dele:
            break
        if rot:
            n += len(bmesh.ops.rotate_edges(bm, edges=rot, use_ccw=False).get("edges") or [])
        if dele:
            bmesh.ops.delete(bm, geom=[f for f, _e in dele], context="FACES_ONLY")
            loose = [e for _f, e in dele if e.is_valid and not e.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="EDGES")
            n += len(dele)
    return n


def xsplit_interp(u, v, sw, se, ne, nw, c):
    """Pure (no bpy): the value at (u, v) in [0, 1]^2 of a cell split in four around its centre — linear on the
    S (sw, se, c), E (se, ne, c), N (ne, nw, c) or W (nw, sw, c) triangle holding the point. The same surface the
    tiered lattice's x-split cells mesh (airoso scripts/geometry/terrain_tiers.xsplit_interp, ledger 0046)."""
    if v <= u and v <= 1.0 - u:
        return (1.0 - u - v) * sw + (u - v) * se + 2.0 * v * c
    if u >= v and u >= 1.0 - v:
        return (u - v) * se + (u + v - 1.0) * ne + 2.0 * (1.0 - u) * c
    if v >= u and v >= 1.0 - u:
        return (u + v - 1.0) * ne + (v - u) * nw + 2.0 * (1.0 - v) * c
    return (v - u) * nw + (1.0 - u - v) * sw + 2.0 * u * c


def house_seat(g_level, g_low, g_high=None, height=None, sink=HOUSE_SINK_M, foot=HOUSE_FOOT_M, show=HOUSE_SHOW):
    """Pure (no bpy): where a building stands on the final ground. Returns ``(floor, base)``: ``floor`` is where its
    walls' visible height starts — the mean ground under the footprint less ``sink`` (the draft's rule, now read on
    the ground that ships), raised where needed so that at least ``show`` of its ``height`` stands above the highest
    ground under its walls (a footprint straddling a cut edge is not buried on its uphill side); ``base`` is the bottom
    of its foundation — never above ``floor`` and never above the lowest ground under its walls less ``foot``, so on a
    slope the downhill wall reaches down into the ground instead of hanging in the air, and on level ground
    ``base == floor`` (the house is exactly the draft's)."""
    floor = g_level - sink
    if g_high is not None and height is not None:
        floor = max(floor, g_high - (1.0 - show) * height)
    return floor, min(floor, g_low - foot)


def footprint_samples(ring, step=HOUSE_EDGE_STEP_M):
    """Pure: the points a footprint's ground is read at — ``(level_pts, low_pts)``. ``ring`` is the base ring in order
    [(x, y), ...]. The level is the mean of the corners and the centroid (the draft's centroid read, made robust to
    one odd corner); the low point walks the walls only (the corners and every ~``step`` between them, so a dip
    between two corners counts) — the ground the walls stand on, not a hollow under the floor."""
    n = len(ring)
    cx = sum(p[0] for p in ring) / n
    cy = sum(p[1] for p in ring) / n
    level = list(ring) + [(cx, cy)]
    low = list(ring)
    for k in range(n):
        (ax, ay), (bx, by) = ring[k], ring[(k + 1) % n]
        m = int(math.hypot(bx - ax, by - ay) // step)
        for j in range(1, m + 1):
            t = j / (m + 1)
            low.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    return level, low


def keep_weight(d, keep_m, feather_m):
    """Pure: weight of the kept (graded) surface at pavement distance ``d`` — 1 within ``keep_m``, smoothstep to 0 at
    ``keep_m + feather_m`` (the tiered assembler's own feather, terrain_tiers.keep_weight)."""
    if d <= keep_m:
        return 1.0
    if feather_m <= 0.0 or d >= keep_m + feather_m:
        return 0.0
    t = (d - keep_m) / feather_m
    return 1.0 - t * t * (3.0 - 2.0 * t)


class RefineField:
    """Pure (no bpy): the kept-cell refinement data (data/terrain.refine.json.gz, written by the tiered assembler):
    which 20 m cells were kept, and on their x-split sub-lattice the clamped 3DEP height ``D`` and the pavement
    distance ``d``. Blender (x, y) = local (x = E, z = N)."""

    def __init__(self, R):
        self.x0, self.z0, self.ux, self.uz = R["frame"]
        self.kr, self.cr = int(R["keep_r"]), int(R["cell_r"])
        self.kept = {tuple(c) for c in R["kept_cells"]}
        self.cells = {tuple(c) for c in R["cells"]}
        self.D = {(i, j): v for i, j, v in zip(R["I"], R["J"], R["D"])}
        self.d = {(i, j): v for i, j, v in zip(R["I"], R["J"], R["d"])}
        self.keep_m, self.feather_m = float(R["keep_m"]), float(R["keep_feather_m"])
        # the feather LENGTH per node (ledger 0046 fix round 4, keep_batter: an earth batter's run of the gap between the
        # graded ground and the data, computed by the assembler at each node); absent = the fixed keep_feather_m
        self.L = {(i, j): v for i, j, v in zip(R["I"], R["J"], R["L"])} if "L" in R else None
        self.edge_m, self.move_m, self.face_m = float(R["edge_m"]), float(R["move_beyond_m"]), float(R["min_face_d_m"])

    def in_kept(self, x, y):
        return (math.floor((x - self.x0) / self.ux / self.kr), math.floor((y - self.z0) / self.uz / self.kr)) in self.kept

    def at(self, x, y, tab, eps=1e-4):
        """``tab`` (self.D / self.d) interpolated at (x, y); None outside every refine sub-cell. A point on a sub-cell
        edge (float32 coordinates) is looked up in whichever listed neighbour holds it: the corner values are shared,
        so the edge reads the same from both sides."""
        fi, fj = (x - self.x0) / self.ux / self.cr, (y - self.z0) / self.uz / self.cr
        ci, cj = math.floor(fi), math.floor(fj)
        u, v = fi - ci, fj - cj
        for di in ((0, -1) if u < eps else ((0, 1) if u > 1 - eps else (0,))):
            for dj in ((0, -1) if v < eps else ((0, 1) if v > 1 - eps else (0,))):
                k = (ci + di, cj + dj)
                if k not in self.cells:
                    continue
                uu, vv = min(1.0, max(0.0, u - di)), min(1.0, max(0.0, v - dj))
                r, h = self.cr, self.cr // 2
                bx, bz = k[0] * r, k[1] * r
                return xsplit_interp(uu, vv, tab[(bx, bz)], tab[(bx + r, bz)], tab[(bx + r, bz + r)], tab[(bx, bz + r)],
                                     tab[(bx + h, bz + h)])
        return None

    def target(self, x, y, z, d_built=None):
        """the refined height of a kept-cell vertex now at height ``z``: None (unchanged) within move_beyond_m of a
        pavement or off the data, else the data feathered toward ``z`` exactly as the lattice beside the kept cell is.
        ``d_built``: the distance to the BUILT pavement, when known — the nearer of the two is the one that counts"""
        d = self.at(x, y, self.d)
        if d is not None and d_built is not None:
            d = min(d, d_built)
        if d is None or d <= self.move_m:
            return None
        D = self.at(x, y, self.D)
        f = self.at(x, y, self.L) if self.L is not None else self.feather_m
        return D + keep_weight(d, self.keep_m, f) * (z - D)


class ReleaseZones:
    """Pure (no bpy): the near-road ground the author stage released to the bare earth (ledger 0046, v0.18.0
    integration fix round: tools/ground_release.py plans data/ground_release.json, tools/ground_release_blend.py applies
    it to TERRAIN). The same membership rule as tools/ground_release.Zones: the nearest centreline vertex (within
    LOCATE_M), the point's station on its tangent and its signed lateral offset (+ = left of travel); in a zone when the
    station is inside [a, b] and the offset on one of its sides lies between half-width - inner_m and half-width +
    reach_m (a span zone from the centreline out: the ground under the deck too). This prep leaves that ground alone: no contact feather, no kept-cell refinement (it pins under the
    pavement as before). Absent file = no zone = nothing changes (every other track)."""
    LOCATE_M = 80.0
    CELL = 20.0

    def __init__(self, pts, widths, zones, inner_m=0.5):
        n = len(pts)
        self.P = [(p[0], p[2]) for p in pts]
        self.W = list(widths)
        closed = n > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
        self.s = [0.0]
        for a, b in zip(self.P, self.P[1:]):
            self.s.append(self.s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.T = []
        for i in range(n):
            a = self.P[n - 2] if (closed and i == 0) else self.P[max(0, i - 1)]
            b = self.P[1] if (closed and i == n - 1) else self.P[min(n - 1, i + 1)]
            L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            self.T.append(((b[0] - a[0]) / L, (b[1] - a[1]) / L))
        self.inner = float(inner_m)
        self.zones = [(float(z["s_m"][0]), float(z["s_m"][1]), [int(v) for v in z["sides"]], float(z["reach_m"]),
                       z.get("kind") == "span") for z in zones]
        self.grid = {}
        for i, (x, z) in enumerate(self.P):
            if any(a - self.LOCATE_M <= self.s[i] <= b + self.LOCATE_M for a, b, _sd, _r, _k in self.zones):
                self.grid.setdefault((int(x // self.CELL), int(z // self.CELL)), []).append(i)

    def contains(self, x, z):
        ci, cj = int(x // self.CELL), int(z // self.CELL)
        r = int(math.ceil(self.LOCATE_M / self.CELL))
        best = None
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                for i in self.grid.get((ci + di, cj + dj), ()):
                    d2 = (self.P[i][0] - x) ** 2 + (self.P[i][1] - z) ** 2
                    if best is None or d2 < best[0]:
                        best = (d2, i)
        if best is None or best[0] > self.LOCATE_M * self.LOCATE_M:
            return False
        i = best[1]
        tx, tz = self.T[i]
        dx, dz = x - self.P[i][0], z - self.P[i][1]
        s, lat = self.s[i] + dx * tx + dz * tz, -dx * tz + dz * tx
        hw = self.W[i] / 2.0
        for a, b, sides, reach, span in self.zones:
            inner = -1e-9 if span else hw - self.inner          # a span zone holds the ground under the deck too
            if a <= s <= b and any(inner <= sd * lat <= hw + reach for sd in sides):
                return True
        return False


class _UnionZones:
    """ledger 0054 P3: the mainline's zones and each connector line's (a zone carrying line_xz / line_w) together"""

    def __init__(self, parts):
        self.parts = parts

    def contains(self, x, z):
        return any(p.contains(x, z) for p in self.parts)


def _release_zones(proj):
    """ReleaseZones from data/ground_release.json + data/centerline.local.json, or None (no file: nothing released).
    A zone resolved on a connector line (ledger 0054 P3: line_xz / line_w in its record, tools/ground_release.py) is
    judged on that line; with none, exactly the mainline's ReleaseZones as before."""
    p = proj / "data" / "ground_release.json"
    if not p.exists():
        return None
    R = json.loads(p.read_text(encoding="utf-8"))
    if not R.get("zones"):
        return None
    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    main = [z for z in R["zones"] if not z.get("line_xz")]
    lines = {}
    for z in R["zones"]:
        if z.get("line_xz"):
            lines.setdefault(z["line"], []).append(z)
    inner = float(R.get("inner_m", 0.5))
    mz = ReleaseZones([tuple(q) for q in local["points_xyz_m"]], local.get("widths_m") or [7.0] * len(
        local["points_xyz_m"]), main, inner_m=inner)
    if not lines:
        return mz
    parts = [mz] + [ReleaseZones([(x, 0.0, zz) for x, zz in zs[0]["line_xz"]], zs[0]["line_w"], zs, inner_m=inner)
                    for zs in lines.values()]
    return _UnionZones(parts)


def _clip_ears(f):
    """triangulate a convex (coplanar) n-gon by ear clipping: of the ears that are not flat in plan (a run of collinear
    vertices — edge midpoints — must never become a zero-area triangle), the one with the SHORTEST new diagonal first
    (the midpoint-to-midpoint cut a tri pattern makes). Returns the number of triangles cut off."""
    import bmesh
    n_cut = 0
    while f is not None and f.is_valid and len(f.verts) > 3:
        vs = [l.vert for l in f.loops]
        n = len(vs)
        best = None
        amax = 0.0
        ears = []
        for i in range(n):
            a, b, c = vs[i - 1].co, vs[i].co, vs[(i + 1) % n].co
            ar = abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y))
            amax = max(amax, ar)
            ears.append((ar, (a - c).length, i))
        for ar, diag, i in ears:
            if ar > 1e-3 * amax and (best is None or diag < best[0]):
                best = (diag, i)
        if best is None:
            break
        i = best[1]
        nf, _l = bmesh.utils.face_split(f, vs[i - 1], vs[(i + 1) % n])
        n_cut += 1
        f = nf if len(nf.verts) > 3 else (f if len(f.verts) > 3 else None)
    return n_cut


def _refine_kept_terrain(proj, bm, near2d=None, skip=None):
    """Ledger 0046 fix round — the kept cells' outer half, AFTER every pass that reshapes near-road ground. A tiered
    terrain keeps the graded grid's own 20 m cells within ~18 m of a pavement so the seat and this prep reshape exactly
    the ground they always reshaped; but those cells reach ~46 m out, and past this prep's reach they stayed 20 m
    graded facets (criterion 5's long triangles 15-35 m from a road, the I-8 terrace walls beside Alvarado smoothed
    away). Two moves, opt-in by data/terrain.refine.json.gz (absent on every other track: nothing touched):

      1. COPLANAR refinement: every edge longer than edge_m of a kept-cell face that reaches past move_beyond_m (or
         whose centre is past min_face_d_m) is halved until none is — on the 20 m grid the halving lands on the 5 m
         x-split sub-lattice; nothing moves, so the surface the gates read is unchanged.
      2. DATA past move_beyond_m: each kept-cell vertex there takes the 3DEP sub-lattice (under the L3 clamp) feathered
         toward its graded height exactly as the tiered lattice beside the cell is (keep_m / keep_feather_m), so the
         field is one surface across the kept edge. Within move_beyond_m nothing moves.
    Returns a report dict, or None when the track has no refinement data."""
    import gzip
    import bmesh
    p = proj / "data" / "terrain.refine.json.gz"
    if not p.exists():
        return None
    F = RefineField(json.loads(gzip.decompress(p.read_bytes()).decode("utf-8")))
    # coincident vertices first (within 1 mm: the same point, so nothing moves): where this prep's corridor subdivision
    # put a midpoint exactly on a finer neighbour's node, the two stay separate vertices until the 5 cm weld after the
    # split — and a move of the kept one alone would open a crack under a vertical fin
    n_merged = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.001)
    n_merged -= len(bm.verts)

    def cand(f):
        c = f.calc_center_median()
        if not F.in_kept(c.x, c.y):
            return False
        if abs(f.normal.z) < 0.05:
            # a (near-)vertical or zero-area face — a step the graded surface already had: every piece of it would
            # be vertical too, so halving it only multiplies it (round on round). Left as it is.
            return False
        dc = F.at(c.x, c.y, F.d)
        if dc is not None and dc >= F.face_m:
            return True
        for v in f.verts:
            dv = F.at(v.co.x, v.co.y, F.d)
            if dv is not None and dv > F.move_m:
                return True
        return False

    n_split = n_poke = 0
    for _round in range(8):
        todo = set()
        for f in bm.faces:
            if cand(f):
                for e in f.edges:
                    if e.calc_length() > F.edge_m:
                        todo.add(e)
        if not todo:
            break
        # one cut edge -> tri_1edge (the midpoint joined to the opposite corner), three -> tri_3edge (four triangles).
        # bmesh has no pattern for two: it leaves a pentagon with two straight-angle vertices, and a generic
        # triangulation of that can be a zero-area cap — invisible while coplanar, but the data move below would stand
        # it up as a vertical fin over a crack. Those are clipped ear by ear (_clip_ears): no new vertex, never a
        # zero-area triangle.
        bmesh.ops.subdivide_edges(bm, edges=list(todo), cuts=1, use_single_edge=True)
        for f in [f for f in bm.faces if len(f.verts) > 3]:
            n_poke += _clip_ears(f)
        n_split += len(todo)
    # a halving can land exactly on a finer neighbour's node that was never welded to the kept edge (a T-junction the
    # prep's own subdivision hid): merge what now coincides, then weld what is still a T — so every node ON a kept
    # cell's edge belongs to a kept face and moves with it (a node left behind would open a crack under a fin)
    n_v = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.001)
    n_merged += n_v - len(bm.verts)
    n_tj = _weld_t_junctions(bm)
    kept_v = set()
    for f in bm.faces:
        c = f.calc_center_median()
        if F.in_kept(c.x, c.y):
            kept_v.update(f.verts)
    n_move, dmax = 0, 0.0
    moved = set()
    z0 = {}
    tgt = {}
    n_skip = 0
    for v in kept_v:
        if skip is not None and skip(v.co.x, v.co.y):
            n_skip += 1          # released to the bare earth by the author stage (ground_release): left alone
            continue
        # the pavement distance is the data's (centreline - half width) or the BUILT road's, whichever is nearer: a
        # mouth weld or a flare widens the pavement past its centreline width, and nothing within move_beyond_m of
        # what was built may move (criterion 7)
        d_built = near2d(v.co.x, v.co.y)[0] if near2d is not None else None
        t = F.target(v.co.x, v.co.y, v.co.z, d_built)
        if t is not None and abs(t - v.co.z) > 1e-6:
            tgt[v] = t
    # a ZERO-AREA face (three points on one straight line, flat in plan and in 3D: the triangulation before this pass
    # can leave one where a quad had a point on its edge) has no surface; moving one of its points and not the others
    # would stand it up as a vertical fin. Its moved points are held where they are (ledger 0046 fix round 4: the
    # height-dependent BEAUTY split met the batter feather's new heights at one such face) — repeated until none is
    # left; the FATAL check below still guards everything else.
    def _flat(pts):
        a, b, c = pts[:3]
        return abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) < 2e-4

    n_held = 0
    for _r in range(16):
        held = set()
        for f in {f for v in tgt for f in v.link_faces}:
            pts = [v.co.copy() for v in f.verts]
            if not _flat(pts) or f.calc_area() > 1e-3:
                continue
            post = [v.co.copy() for v in f.verts]
            for k, v in enumerate(f.verts):
                if v in tgt:
                    post[k].z = tgt[v]
            if ((post[1] - post[0]).cross(post[2] - post[0])).length > 2e-3:
                held.update(v for v in f.verts if v in tgt)
        if not held:
            break
        for v in held:
            del tgt[v]
        n_held += len(held)
    for v, t in tgt.items():
        dmax = max(dmax, abs(t - v.co.z))
        z0[v] = v.co.z
        v.co.z = t
        n_move += 1
        moved.add(v)
    # a face flat in plan with a moved vertex that is not flat in 3D now stands vertical (a fin over a crack): counted,
    # and those that were already vertical before the move (the graded surface's own steps) counted apart
    fins = fins_pre = 0
    for f in {f for v in moved for f in v.link_faces}:
        a, b, c = [v.co for v in f.verts][:3]
        if abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) < 2e-4 and f.calc_area() > 1e-3:
            zs = [(v, z0.get(v, v.co.z)) for v in f.verts]
            pa = [v.co.copy() for v in f.verts]
            for k, (v, z) in enumerate(zs):
                pa[k].z = z
            if ((pa[1] - pa[0]).cross(pa[2] - pa[0])).length > 2e-3:
                fins_pre += 1
            else:
                fins += 1
    if fins:
        raise SystemExit(f"[build_kn5_loop] FATAL: the kept-cell refinement stood {fins} plan-flat faces up as vertical "
                         f"fins (a moved vertex beside an unmoved one at the same point: a crack). Refusing to export.")
    return {"merged": n_merged, "t_junctions": n_tj, "edges_split": n_split, "ears_clipped": n_poke,
            "kept_vertices": len(kept_v), "moved": n_move, "max_move_m": round(dmax, 2), "fins": fins,
            "held_on_zero_area_faces": n_held, "released_left_alone": n_skip,
            "vertical_before": fins_pre}


def _split_large(ob, cap=SPLIT_CAP):
    """Split a mesh over AC's 65,535-vertex cap into UNIQUELY-named spatial tiles (base_0, base_1,
    ...). The exporter otherwise auto-splits into DUPLICATE-named meshes, and AC drops dup-named
    PHYSICAL meshes from collision -> the car falls through (a 46 km freeway terrain is ~268k
    verts). Terrain (TERRAIN_TILES) is tiled by balanced bisection; every other mesh keeps the
    equal-width bands along the longest axis; pbr/surfaces still key off the shared name prefix
    (1GRASS_0 -> GRASS)."""
    import bpy

    me = ob.data
    if len(me.vertices) <= cap:
        return
    co = [(v.co.x, v.co.y, v.co.z) for v in me.vertices]
    if ob.name.upper().startswith(TERRAIN_TILES):
        polys = list(me.polygons)
        groups = balanced_face_tiles([(p.center[0], p.center[1]) for p in polys],
                                     [tuple(p.vertices) for p in polys], cap)
        bands = [[polys[i] for i in g] for g in groups]
        K = len(bands)
    else:
        K = len(me.vertices) // cap + 1
        ax = 0 if (max(c[0] for c in co) - min(c[0] for c in co)) >= \
                 (max(c[1] for c in co) - min(c[1] for c in co)) else 1
        lo = min(c[ax] for c in co); span = (max(c[ax] for c in co) - lo) or 1.0
        bands = [[] for _ in range(K)]
        for p in me.polygons:
            bands[min(K - 1, int((p.center[ax] - lo) / span * K))].append(p)
    base = ob.name
    mat = me.materials[0] if me.materials else None
    # carry authored per-vertex UVs across the split (palm cards etc. are single UV per vertex) —
    # without this the tiles have NO UVs and an alpha-cutout texture samples (0,0) and vanishes.
    vert_uv = None
    if me.uv_layers.active:
        uvl = me.uv_layers.active
        vert_uv = [(0.0, 0.0)] * len(me.vertices)
        for loop in me.loops:
            vert_uv[loop.vertex_index] = tuple(uvl.data[loop.index].uv)
    for k, polys in enumerate(bands):
        if not polys:
            continue
        used, nv, nf, orig = {}, [], [], []
        for poly in polys:
            idx = []
            for vi in poly.vertices:
                if vi not in used:
                    used[vi] = len(nv); nv.append(co[vi]); orig.append(vi)
                idx.append(used[vi])
            nf.append(idx)
        nm = bpy.data.meshes.new(f"{base}_{k}")
        nm.from_pydata(nv, [], nf); nm.update()
        if vert_uv is not None:
            nuv = nm.uv_layers.new(name="UVMap")
            for loop in nm.loops:
                nuv.data[loop.index].uv = vert_uv[orig[loop.vertex_index]]
        if mat:
            nm.materials.append(mat)
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(f"{base}_{k}", nm))
    how = "balanced bisection" if base.upper().startswith(TERRAIN_TILES) else "equal-width bands"
    print(f"[build_kn5_loop] split {base} ({len(me.vertices)} verts) -> {K} tiles under {cap} ({how})")
    bpy.data.objects.remove(ob, do_unlink=True)


def planar_uv(me):
    """Top-down planar UVs (u=x/tile, v=y/tile) — tiles asphalt/grass/kerb consistently at world
    scale."""
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / UV_TILE, co.y / UV_TILE)


def _add_obj_meshes(obj_path):
    """Import a merged OBJ (e.g. a freeway network already translated to the loop frame) using the
    SAME local->Blender remap as the loop authoring — (x,y,z)->(x,z,y) with reversed winding — so
    it lands in the loop's frame and the existing rename/flip/material pass handles it. Keeps AC
    group names + authored UVs."""
    import bpy

    verts = []; uvs = []; groups = []; cur = None
    for ln in obj_path.read_text().splitlines():
        s = ln.split()
        if not s:
            continue
        if s[0] == "v":
            verts.append((float(s[1]), float(s[2]), float(s[3])))
        elif s[0] == "vt":
            uvs.append((float(s[1]), float(s[2])))
        elif s[0] == "o":
            cur = (ln[2:].strip(), []); groups.append(cur)
        elif s[0] == "f" and cur is not None:
            face = []
            for tok in s[1:]:
                p = tok.split("/")
                face.append((int(p[0]) - 1, int(p[1]) - 1 if len(p) > 1 and p[1] else None))
            cur[1].append(face)
    n = 0
    for name, faces in groups:
        if not faces:
            continue
        has_uv = all(t is not None for fc in faces for _, t in fc)
        idx = {}; bverts = []; buvs = []; bfaces = []
        for fc in faces:
            bf = []
            for vi, ti in fc:
                if vi not in idx:
                    idx[vi] = len(bverts)
                    x, y, z = verts[vi]; bverts.append((x, z, y))     # local (E,up,N) -> Blender (E,N,up)
                    buvs.append(uvs[ti] if (has_uv and ti is not None) else (0.0, 0.0))
                bf.append(idx[vi])
            bfaces.append(tuple(reversed(bf)))                        # reverse winding (cancels the reflection)
        if name.upper().startswith(DOUBLE_SIDE):
            bfaces += [tuple(reversed(f)) for f in bfaces]            # render + collide from both sides
        me = bpy.data.meshes.new(name); me.from_pydata(bverts, [], bfaces); me.validate(); me.update()
        if has_uv:
            uvl = me.uv_layers.new(name="UVMap")
            for loop in me.loops:
                uvl.data[loop.index].uv = buvs[loop.vertex_index]
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(name, me))
        n += 1
    print(f"[build_kn5_loop] merged {n} groups ({len(verts)} verts) from {obj_path.name}")
    return n


def _conform_and_reseat(proj: Path, spans):
    """Terrain contact conform for the Blender-first loop + prop re-seat, run INSIDE the open scene
    (after the AC renames, before the split pass). Three moves, all engine-owned so every future
    rebuild stays fixed (no hand surgery baked into loop.blend):

      1. SUBDIVIDE the terrain corridor: coarse DEM triangles cannot hug a hand-shaped deck — edges
         near the road are split to ~CORRIDOR_EDGE_M so the pin has vertices to work with
         (the adaptive-fine-grid move).
      2. PIN under the footprint: every 1GRASS vert under 1ROAD pavement is SET to deck−GROUND_CLEAR
         (up or down — contact, not a clamp), with a smoothstep FEATHER band blending back to natural
         ground past the edge. Under a DECLARED bridge span the pin may only push DOWN: the I-8
         trench stays a trench and the deck keeps riding it.
      3. RE-SEAT props on the moved ground: trees are seated absolutely (their floats predate this
         pass); palms/scrub/buildings/lights ride the terrain DELTA so today's good seats stay good.
    """
    import bpy
    from mathutils import kdtree
    from mathutils.bvhtree import BVHTree

    def _world_tris(name_pred):
        tris = []
        for ob in bpy.data.objects:
            if ob.type != "MESH" or not name_pred(ob.name.upper()):
                continue
            mw = ob.matrix_world
            me = ob.data
            vs = [mw @ v.co for v in me.vertices]
            for p in me.polygons:
                idx = list(p.vertices)
                for k in range(1, len(idx) - 1):
                    tris.append(((vs[idx[0]].x, vs[idx[0]].y, vs[idx[0]].z),
                                 (vs[idx[k]].x, vs[idx[k]].y, vs[idx[k]].z),
                                 (vs[idx[k + 1]].x, vs[idx[k + 1]].y, vs[idx[k + 1]].z)))
        return tris

    def _bvh(tris):
        return BVHTree.FromPolygons([v for t in tris for v in t],
                                    [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))]) if tris else None

    def _surf_z(bvh, x, y, zref=None, win=LAYER_WIN):
        """Highest surface z at (x, y) via a downward ray from far above (Blender z = up)."""
        if bvh is None:
            return None
        hit = bvh.ray_cast((x, y, 4000.0), (0.0, 0.0, -1.0))
        if hit[0] is None:
            return None
        z = hit[0].z
        if zref is not None and abs(z - zref) > win:
            return None
        return z

    # 0. BURY-CULL: drivable faces (road/kerb) sandwiched >=0.3 m UNDER other pavement are junction
    #    apron slop that slid beneath the main deck when the junctions were shaped — dead geometry
    #    no wheel can reach. Left in, they poison every "lowest drivable sheet" lens: the poke gate
    #    reads contact-pinned grass as floating grass ABOVE the buried sliver, and clamping the
    #    grass down to the sliver instead re-opens metre-deep holes under the driven road. Cull the
    #    fully-buried faces (all verts covered) before anything measures against them.
    import bmesh
    _pre_bvh = _bvh(_world_tris(lambda n: n.startswith(("1ROAD", "1KERB")) and not n.endswith("_FW")))
    n_cull = 0
    if _pre_bvh is not None:
        for ob in [o for o in bpy.data.objects if o.type == "MESH"
                   and o.name.upper().startswith(("1ROAD", "1KERB"))
                   and not o.name.upper().endswith("_FW")]:
            me = ob.data
            bm = bmesh.new(); bm.from_mesh(me)
            drop = []
            for f in bm.faces:
                buried = True
                for v in f.verts:
                    hit = _pre_bvh.ray_cast((v.co.x, v.co.y, v.co.z + 0.3), (0.0, 0.0, 1.0), 20.0)
                    if hit[0] is None:
                        buried = False
                        break
                if buried:
                    drop.append(f)
            if drop:
                n_cull += len(drop)
                bmesh.ops.delete(bm, geom=drop, context="FACES")
                bm.to_mesh(me); me.update()
            bm.free()
    if n_cull:
        print(f"[build_kn5_loop] bury-cull: {n_cull} drivable faces removed from under other pavement")

    road_tris = _world_tris(lambda n: n.startswith("1ROAD"))
    road_bvh = _bvh(road_tris)
    if road_bvh is None:
        print("[build_kn5_loop] conform skipped: no 1ROAD mesh")
        return
    # drivable = road + kerb/sidewalk: the anti-poke pass below must use the same surface set the
    # verify poke lens measures against (grass over a LOW sidewalk apron is a poke too).
    driv_bvh = _bvh(_world_tris(lambda n: n.startswith(("1ROAD", "1KERB"))))

    # HORIZONTAL road-vert KD-tree for the feather + subdivision predicate. Distance must be 2D: on
    # a bench cut the ground beside the road is legitimately metres LOW, so a 3D nearest-distance
    # reads 6+ m and never feathers exactly the band the contact pin exists for (the CO lesson —
    # "real ground under the outer half of a bench-cut road is legitimately metres low").
    _rverts = sorted({(round(v[0], 4), round(v[1], 4), round(v[2], 4)) for t in road_tris for v in t})
    road_kd = kdtree.KDTree(len(_rverts))
    for _i, (_x, _y, _z) in enumerate(_rverts):
        road_kd.insert((_x, _y, 0.0), _i)
    road_kd.balance()

    def _near2d(x, y):
        co, idx, d = road_kd.find((x, y, 0.0))
        return (d, _rverts[idx][2]) if co is not None else (None, None)

    def _lowest_surf(bvh, x, y, zref, win=20.0):
        """LOWEST drivable surface at (x, y) within ±win of zref — multi-hit downward ray walk
        (the verify poke lens takes the lowest sheet; on a crowned/sloped section the highest one
        is the wrong reference)."""
        z0 = zref + win
        best = None
        for _ in range(6):
            hit = bvh.ray_cast((x, y, z0), (0.0, 0.0, -1.0), z0 - (zref - win))
            if hit[0] is None:
                break
            best = hit[0].z
            z0 = hit[0].z - 0.02
        return best

    # span mask: centerline stations inside a declared span -> XY discs (deck may only push DOWN)
    span_pts = []
    try:
        local = json.loads((proj / "data" / "centerline.local.json").read_text())
        pts = local["points_xyz_m"]
        wid = local.get("widths_m") or [7.0] * len(pts)
        st = 0.0
        for i, p in enumerate(pts):
            if i:
                st += math.hypot(p[0] - pts[i - 1][0], p[2] - pts[i - 1][2])
            if any(a <= st <= b for a, b in spans):
                span_pts.append((p[0], p[2], wid[i] / 2.0 + 12.0))   # Blender XY = (E, N)
    except Exception as e:  # noqa: BLE001
        print(f"[build_kn5_loop] span mask skipped: {e}")

    def on_span(x, y):
        return any((x - sx) ** 2 + (y - sy) ** 2 <= r * r for sx, sy, r in span_pts)

    # released ground (ledger 0046 v0.18.0 integration fix round): the author stage set it to the bare earth inside the
    # declared zones (tools/ground_release_blend.py); the contact feather and the kept-cell refinement leave it alone
    rel = _release_zones(proj)
    n_rel_zone = 0

    terrain = [ob for ob in bpy.data.objects
               if ob.type == "MESH" and ob.name.upper().startswith("1GRASS")]
    old_grass_bvh = _bvh(_world_tris(lambda n: n.startswith("1GRASS")))   # pre-pin ground, for deltas

    import bmesh
    n_pin = n_feather = n_sub = 0
    for ob in terrain:
        me = ob.data
        bm = bmesh.new(); bm.from_mesh(me)
        # 1. corridor subdivision (repeat: each round halves qualifying edges)
        for _round in range(4):
            todo = []
            for e in bm.edges:
                if e.calc_length() <= CORRIDOR_EDGE_M:
                    continue
                mx = (e.verts[0].co + e.verts[1].co) / 2
                d2d, _rz = _near2d(mx.x, mx.y)
                if d2d is not None and d2d <= FEATHER_M + 10.0:
                    todo.append(e)
            if not todo:
                break
            bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1)
            n_sub += len(todo)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        n_mend = _mend_vertical_slivers(bm)
        if n_mend:
            print(f"[build_kn5_loop] vertical slivers: {n_mend} T-vertex ears of the corridor subdivision mended")
        # 2. pin + feather (all distances HORIZONTAL — bench-cut ground is legitimately metres low)
        for v in bm.verts:
            x, y, z = v.co.x, v.co.y, v.co.z
            d2d, rz = _near2d(x, y)
            if d2d is None or d2d > FEATHER_M + 10.0:
                continue
            deck = _surf_z(road_bvh, x, y, zref=z)
            if deck is not None:                       # under the pavement footprint
                tgt = deck - GROUND_CLEAR
                if on_span(x, y):
                    if z > tgt:
                        v.co.z = tgt; n_pin += 1       # bridge span: contact may only push DOWN
                else:
                    v.co.z = tgt; n_pin += 1
            else:                                      # contact band + feather past the edge
                if rel is not None and rel.contains(x, y):
                    n_rel_zone += 1
                    continue
                # full-contact BAND (CO's "gentle shelf"): every triangle covering pavement has all
                # verts within ~2.6 m of the edge, so holding the first 3 m at contact height makes
                # the surface under the deck edge gate-proof; then smoothstep back to natural.
                if d2d <= BAND_M:
                    w = 1.0
                elif d2d < BAND_M + FEATHER_M:
                    w = 1.0 - (d2d - BAND_M) / FEATHER_M
                    w = w * w * (3 - 2 * w)
                else:
                    continue
                # target = deck at the CLOSEST FOOTPRINT POINT (BVH), not the nearest road VERT's
                # height — on a 7% grade the vert-snap target was ±0.3 off between stations and
                # printed that error into the contact band (the 0.05–0.35 residual tail).
                near3 = road_bvh.find_nearest((x, y, z))
                tgt = (near3[0].z if near3[0] is not None else rz) - GROUND_CLEAR
                nz = tgt * w + z * (1.0 - w)
                if on_span(x, y) and nz > z:
                    continue
                v.co.z = nz; n_feather += 1
        # 2c. ANTI-POKE vs the LOWEST drivable sheet (road + kerb): the pin/feather reference the
        # nearest/highest deck — on crowned or sloping sections, and over the sidewalk's outer
        # apron, that left grass 0.15–1.2 m over the LOWER surface the verify lens measures
        # against (217 pokes). One-sided: only pushes DOWN, so spans/trenches are untouched.
        # (Blanket clamp is safe now that the bury-cull removed the sandwiched apron slivers.)
        n_anti = 0
        for v in bm.verts:
            low = _lowest_surf(driv_bvh, v.co.x, v.co.y, v.co.z)
            if low is not None and v.co.z > low - GROUND_CLEAR:
                v.co.z = low - GROUND_CLEAR; n_anti += 1
        if n_anti:
            print(f"[build_kn5_loop] anti-poke: {n_anti} verts clamped under the lowest drivable sheet")
        # 2d. T-junctions (a tiered terrain's finer cells beside its kept grid cells, ledger 0046): re-fan the
        # kept face through the nodes on its edge — after every pass that moves ground, so nothing moves
        n_tj = _weld_t_junctions(bm)
        if n_tj:
            print(f"[build_kn5_loop] T-junctions: {n_tj} terrain faces re-fanned through the nodes on their edges")
        # 2e. the kept cells' outer half (ledger 0046 fix round): refined, and the data past the near-road band — after
        # every pass above, before the re-seat below (so the props ride this delta too)
        rf = _refine_kept_terrain(proj, bm, _near2d, skip=(rel.contains if rel is not None else None))
        if rf is not None:
            print(f"[build_kn5_loop] kept-cell refinement: {rf}")
        bm.to_mesh(me); bm.free(); me.update()
    print(f"[build_kn5_loop] terrain conform: {n_sub} corridor edges split, "
          f"{n_pin} verts pinned to deck-{GROUND_CLEAR}, {n_feather} feathered"
          + (f", {n_rel_zone} released verts left unfeathered" if rel is not None else ""))

    # 3. prop re-seat on the moved ground
    ground_bvh = _bvh(_world_tris(lambda n: n.startswith(("1GRASS", "1ROAD", "1KERB"))))

    def _islands(ob):
        """Connected vert islands of a mesh object (index lists), via union-find over edges."""
        me = ob.data
        parent = list(range(len(me.vertices)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for e in me.edges:
            a, b = find(e.vertices[0]), find(e.vertices[1])
            if a != b:
                parent[a] = b
        groups: dict[int, list[int]] = {}
        for i in range(len(me.vertices)):
            groups.setdefault(find(i), []).append(i)
        return list(groups.values())

    def _shift(ob, isl, dz):
        me = ob.data
        for i in isl:
            me.vertices[i].co.z += dz

    trunk_dz = []                                    # (x, y, dz) for canopy matching
    n_trees = n_rel = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith("TREETRUNK"):
            continue
        me = ob.data
        for isl in _islands(ob):
            fi = min(isl, key=lambda i: me.vertices[i].co.z)
            f = ob.matrix_world @ me.vertices[fi].co
            g = _surf_z(ground_bvh, f.x, f.y, zref=None)
            if g is None:
                continue
            dz = g - f.z
            cx = sum(me.vertices[i].co.x for i in isl) / len(isl)
            cy = sum(me.vertices[i].co.y for i in isl) / len(isl)
            if abs(dz) > 0.03:
                _shift(ob, isl, dz); n_trees += 1
            trunk_dz.append((cx, cy, dz if abs(dz) > 0.03 else 0.0))
        me.update()
    for ob in bpy.data.objects:                      # canopies follow their trunk
        if ob.type != "MESH" or not ob.name.upper().startswith("TREECANOPY"):
            continue
        me = ob.data
        for isl in _islands(ob):
            cx = sum(me.vertices[i].co.x for i in isl) / len(isl)
            cy = sum(me.vertices[i].co.y for i in isl) / len(isl)
            best = None
            for tx, ty, dz in trunk_dz:
                d2 = (cx - tx) ** 2 + (cy - ty) ** 2
                if best is None or d2 < best[0]:
                    best = (d2, dz)
            if best is not None and best[0] < 16.0 and abs(best[1]) > 0.0:
                _shift(ob, isl, best[1])
        me.update()
    # houses / buildings: seated on the FINAL ground under their own footprint (house_seat; ledger 0046 fix round 3)
    n_seat = n_found = 0
    max_found = 0.0
    seated = set()
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith(("BUILDING", "HOUSE")):
            continue
        if not ob.matrix_world.is_identity:
            continue                                  # not the draft's own mesh: left to the delta ride below
        me = ob.data
        for isl in _islands(ob):
            zmin = min(me.vertices[i].co.z for i in isl)
            base = [i for i in isl if me.vertices[i].co.z < zmin + 0.05]
            top = [i for i in isl if me.vertices[i].co.z >= zmin + 0.05]
            if len(base) < 3 or not top:
                continue
            ring = [(me.vertices[i].co.x, me.vertices[i].co.y) for i in sorted(base)]   # the draft's ring order
            level_pts, low_pts = footprint_samples(ring)
            gl = [_surf_z(ground_bvh, x, y, zref=zmin, win=40.0) for x, y in level_pts]
            gw = [_surf_z(ground_bvh, x, y, zref=zmin, win=40.0) for x, y in low_pts]
            gl = [g for g in gl if g is not None]
            gw = [g for g in gw if g is not None]
            if len(gl) < 3:
                continue
            ztop = max(me.vertices[i].co.z for i in top)
            floor, bottom = house_seat(sum(gl) / len(gl), min(gw) if gw else min(gl),
                                       max(gw + gl), ztop - zmin)
            dz = floor - zmin
            for i in top:
                me.vertices[i].co.z += dz
            for i in base:
                me.vertices[i].co.z = bottom
            n_seat += 1
            if floor - bottom > 0.005:
                n_found += 1
                max_found = max(max_found, floor - bottom)
            seated.add((ob.name, min(isl)))
        me.update()
    print(f"[build_kn5_loop] house seat: {n_seat} buildings seated on the final ground under their footprints, "
          f"{n_found} with a foundation reaching down a slope (deepest {max_found:.2f} m)")
    # palms / scrub (and any building not seated above) ride the terrain delta (their seats were green). NOT the
    # LIGHTS lens markers (v0.18.0, the runtime lens): each sits at its LIGHTPOST's luminaire (tools/author_lamps_blend.py),
    # and the post never rides, so a lens moved by the ground change under the arm left its own lamp head (LIGHT_123 on
    # Lake Murray Blvd's I-8 deck rose 1.22 m, 0.68 m over its plate) and the head shadowed its own pool at night
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith(
                ("PALMTRUNK", "PALMFROND", "SCRUB", "BUILDING", "HOUSE")):
            continue
        me = ob.data
        for isl in _islands(ob):
            if (ob.name, min(isl)) in seated:
                continue
            fi = min(isl, key=lambda i: me.vertices[i].co.z)
            f = ob.matrix_world @ me.vertices[fi].co
            zo = _surf_z(old_grass_bvh, f.x, f.y, zref=f.z, win=40.0)
            zn = _surf_z(ground_bvh, f.x, f.y, zref=f.z, win=40.0)
            if zo is None or zn is None:
                continue
            dz = zn - zo
            if abs(dz) > 0.02:
                _shift(ob, isl, dz); n_rel += 1
        me.update()
    print(f"[build_kn5_loop] re-seat: {n_trees} trees seated on the conformed ground, "
          f"{n_rel} props rode the terrain delta")


def main():
    import bpy

    proj = _project_dir(sys.argv)
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    cfg = json.loads((proj / "track.config.json").read_text())
    slug = cfg["slug"]
    (proj / "blender").mkdir(exist_ok=True)
    (proj / "build").mkdir(exist_ok=True)

    # 1. open the working scene
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))

    # 1b. merge pre-built network OBJs (translated to the loop frame, e.g. by a merge_freeway step)
    #     into ONE kn5. Skipped when the project has none.
    for mobj in sorted(list((proj / "data").glob("track_*.obj")) + list((proj / "data").glob("env_*.obj"))):
        _add_obj_meshes(mobj)

    # 2. drop non-exported helpers (markers/cameras), rename meshes to AC convention
    for ob in list(bpy.data.objects):
        if ob.type != "MESH":
            bpy.data.objects.remove(ob, do_unlink=True); continue
        ob.name = AC_NAME.get(ob.name, ob.name)

    # 2b. terrain contact conform: declare the real bridge spans, pin the terrain to the deck under
    #     the footprint (subdividing the corridor first), spare the declared spans, and re-seat the
    #     props on the moved ground. Engine-owned so every future rebuild stays fixed.
    spans = declare_bridge_spans(proj)
    _conform_and_reseat(proj, spans)

    # split any mesh over the AC per-mesh vertex cap into uniquely-named tiles (big tracks: freeway terrain)
    for ob in list(o for o in bpy.data.objects if o.type == "MESH"):
        _split_large(ob)

    import bmesh
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        me = ob.data
        # props / billboards carry authored UVs — don't flatten (freeway BUSHES/CHAINLINK too)
        # ...and the race furniture (ledger 0047) + the phase-5 stub barriers (1WALL_STUB, ledger 0054): the strips carry
        # u = arc / 4.04 m along the
        # vertical faces and the kerbs v = arc / 1 m — a top-down projection would smear them
        if not ob.name.upper().startswith(("PALM", "TREE", "SCRUB", "BUSHES", "CHAINLINK", "ROADTEXT",
                                           "1WALL_RACE", "1KERB_RACE", "BRIDGESTRUCT", "1WALL_STUB",
                                           "BUILDING_FABRIC", "1WALL_FABRIC", "PROPCONE", "BUILDING_TILTUP", "BUILDING_METAL",
                                           "BUILDING_STUCCO", "BUILDING_SIDING", "ROOFTOP", "1WALL_TILTUP", "1WALL_TECPRO",
                                           "1WALL_KRAILBW", "GUARDRAIL", "PADAPRON", "BUILDING_DRYSTONE", "FARBLOCK")):
            planar_uv(me)
        bm = bmesh.new(); bm.from_mesh(me)
        # ledger 0061: the bespoke shells are authored and never welded (ledger 0024's inside-out shells)
        if not ob.name.upper().startswith(("BUILDING_FABRIC", "PROPCONE", "BUILDING_TILTUP", "BUILDING_METAL", "BUILDING_STUCCO",
                                           "BUILDING_SIDING", "ROOFTOP", "GUARDRAIL", "BUILDING_DRYSTONE", "FARBLOCK")):
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        if ob.name.upper().startswith("1GRASS"):
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.05)   # terrain must be watertight
            try:
                bmesh.ops.holes_fill(bm, edges=bm.edges, sides=16)
            except Exception as e:
                print(f"[build_kn5_loop] holes_fill skipped: {e}")
        # DRIVABLE surfaces must face UP or AC has no top collision and the car falls through. The
        # local->Blender axis remap (x,y,z)->(x,z,y) is a reflection that flipped every face down.
        # Fix DETERMINISTICALLY: reverse only the faces whose normal points down (normal.z<0). This
        # is NOT recalc_face_normals (which guesses "outward" from shape and picks DOWN on big
        # terrain); for a near-horizontal drivable surface "up" is unambiguous, so this can't guess
        # wrong or split the mesh. ...plus flat painted markings (MARKINGS/YLINE) — decals that
        # must face up to be seen from the car.
        if ob.name.upper().startswith(("1ROAD", "1GRASS", "1KERB", "MARKINGS", "YLINE", "GRASS_FAR")):
            bm.normal_update()
            down = [f for f in bm.faces if f.normal.z < 0]
            if down:
                bmesh.ops.reverse_faces(bm, faces=down)
            print(f"[build_kn5_loop] {ob.name}: flipped {len(down)}/{len(bm.faces)} faces up")
        bm.to_mesh(me); bm.free(); me.update()
        if len(me.loops) > VERT_CAP:         # smooth-shade big meshes so render-verts fit the 16-bit cap
            for poly in me.polygons:
                poly.use_smooth = True
            me.update()
        # loop-path over-cap guard: FATAL (the OBJ program guards in build_kn5.py; this path is its
        # own program and needs its own gate — a WARNING here shipped over-cap meshes before).
        assert_under_cap(ob.name, len(me.vertices))
        # ...and the count the kn5 WRITER emits (ledger 0054 P3 repair round 2): a mesh past it is tiled under unique
        # names here, never left to the writer's split into meshes of one name
        for t in _split_for_writer(ob):
            assert_under_cap(t.name, export_vertex_count(_export_vertex_keys(t.data)[0]))
    tiles = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.upper().startswith(TERRAIN_TILES):
            k = "1GRASS" if o.name.upper().startswith("1GRASS") else "GRASS_FAR"
            tiles.setdefault(k, []).append(len(o.data.vertices))
    print("[build_kn5_loop] terrain tiles: " + ", ".join(
        f"{k} x{len(v)} (max {max(v)} v, total {sum(v)} v)" for k, v in sorted(tiles.items())))

    # 3. AC dummies from the real centreline (local frame x=E,y=up,z=N -> Blender x=E,y=N,z=up = (x,z,y))
    #    MULTI-LAYOUT (ledger 0047; fleet/LAWS.md L8 as amended): with more than one layouts[] entry
    #    the road kn5 carries NO AC_* nodes — every layout's grid / pits / timing gates ride in its
    #    own nodes-only spawn kn5 (tools/layout_dummies.py -> data/dummies_<id>.json ->
    #    scripts/ac/build_spawn_kn5.py), so no empties are created here and data/dummies.json is
    #    written EMPTY. The exporter writes every object it finds, so nothing can bake what is not
    #    there; verify_kn5 (a) fails a multi-layout road kn5 that carries a spawn node.
    FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")
    dummies_out = {}
    _layouts = cfg.get("layouts", []) or []
    if len(_layouts) > 1:
        print(f"[build_kn5_loop] multi-layout ({len(_layouts)} layouts): spawns ride in per-layout kn5s — "
              f"no AC_* empties in the road scene, data/dummies.json = {{}}")
    else:
        from scripts.geometry import dummies as dmod
        local = json.loads((proj / "data" / "centerline.local.json").read_text())
        cl = [tuple(p) for p in local["points_xyz_m"]]
        widths = local["widths_m"]
        n_pits = 8
        placed = dmod.place_dummies(cl, widths, n_sectors=3, n_pits=n_pits)
        # start facing = travel direction pts[0]->pts[1], as a yaw about Blender Z(up)
        tx, ty = cl[1][0] - cl[0][0], cl[1][2] - cl[0][2]          # Blender (E, N)
        start_yaw = math.atan2(tx, ty)
        for name, (x, y, z) in placed.items():
            e = bpy.data.objects.new(name, None)
            e.empty_display_type = "ARROWS"; e.empty_display_size = 4.0
            e.location = (x, z, y)                                  # local (E,up,N) -> Blender (E,N,up)
            if any(name.startswith(p) for p in FACING):
                e.rotation_euler = (0.0, 0.0, start_yaw)
            bpy.context.scene.collection.objects.link(e)
            dummies_out[name] = [round(x, 3), round(y, 3), round(z, 3)]
    (proj / "data" / "dummies.json").write_text(json.dumps(dummies_out, indent=1))

    # 4. PBR materials (prefix -> texture set); export_kn5_addon re-derives shader from the same
    #    prefix. Reconciled to the ENGINE pbr: config/capture texture_overrides apply here AND at
    #    export (load_overrides), so a loop project can e.g. swap 1GRASS dry dirt for green turf
    #    via track.config.json without renaming meshes.
    from scripts.ac import pbr
    overrides = pbr.load_overrides(proj)
    if overrides:
        print(f"[build_kn5_loop] texture overrides: {sorted(overrides)}")
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        pbr.setup_material(bpy, ob, overrides=overrides)

    # 5. pack textures + save the AC-ready .blend for the export pass
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"[build_kn5_loop] pack_all warning: {e}")
    out = proj / "blender" / f"{slug}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    meshes = [o.name for o in bpy.data.objects if o.type == "MESH"]
    print(f"[build_kn5_loop] prepped {meshes}  + {len(dummies_out)} dummies -> {out}")


if __name__ == "__main__":
    main()

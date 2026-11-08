"""Stand the bespoke dressing a track declares (track.config.json scenery.bespoke) into loop.blend's AUTH_bespoke.

.claude/skills/bespoke-assets section 4. Every position is DECLARED in the config and placed here, never typed here, so a
re-run reproduces it; the seat is read off the BUILT ground of this scene (1GRASS / 1ROAD / 1KERB, Blender frame x = E,
y = N, z = up). The collection is emptied first, so the tool is idempotent, and the engine's GEN_* is never touched.

  buildings   {"key", "footprint_lonlat": [4 corners, any winding], "roof": "flat", "wall_h_m"}
              {"key", "footprint_lonlat": [...], "roof": "gable", "eave_h_m", "ridge_h_m"}: ridge along the long side
              -> BUILDING_FABRIC_<key> (the shell, visual, its UVs tiled by real metres, 5 m bay)
              -> 1WALL_FABRIC_<key>    (four collidable faces COLLIDER_INSET_M inside the shell, so a car stops at the
                                        wall and never drives through a tent; never seen)
              Seat, the prep's house_seat rule that tools/house_seat_check.py gates: the bottom ring BOTTOM_UNDER_M under
              the lowest ground under the walls, the heights measured from the MEAN ground, raised where the footprint
              straddles more relief than half the wall so that half of it stands above the highest ground.
  cones       {"stations": [{"corner", "role", "s", "side"}]} (tools/plan_cones.py): assets/models/traffic_cone.obj on
              the surface just beyond the track's edge (main road, kerb) on that side, CONE_OFF_EDGE_M clear of it: verge,
              shoulder or corner run-off
              -> PROPCONE_<k> (visual only, one mesh per CONES_PER_MESH cones)
  scrub       {"polygon_lonlat", "count", "seed", "creosote_share", "size_m": [lo, hi]}: crossed double-sided cards on
              a seeded scatter inside the polygon, seated on the ground -> SCRUBCARD_<k>. The atlas is the 2 x 2
              assets/textures/desert_scrub_atlas.png (creosote on top, bursage below)
  blocks      [{"file": "source/bespoke/buildings.json", "auto": true, "replace": ["HOUSE", "BUILDING"]}] or inline {"key", "footprint_lonlat", "wall_h_m", "skin",
              "roof", "form", "ridge_h_m", "off_terrain"}: "form" (tools/plan_buildings.py) = flat | flat_parapet (a PARAPET_M lip
              round the roof) | hip | gable (the ridge along the long axis of the footprint's oriented box, ridge_h_m over the
              level; a ring that fills less than RECT_FILL of its box is roofed flat instead) | posts (ledger 0083 pass 3, opt-in
              by a planned row only: an open-sided roof, canopy_on_posts, one welded island BUILDING_METAL_CANOPY_<k>, no walls,
              no collider, refused within COLLIDER_REACH_M of the lap) | shed (ledger 0083 pass 4, by a planned row only: one
              measured plane, "plane" {"ref_lonlat", "h_m", "gx", "gy"}; the walls rise to it, the roof is the ring on it).
              Planned-row keys of pass 4, each absent = as before: "parapet_m" (a measured parapet, in place of PARAPET_M),
              "ridge_axis": "short" (a gable's measured ridge across the box), "roof": "NAIP" + "roof_uv" (the measured
              colour's cell of the plan's palette: ROOFTOP_NAIP_<k>, bound by the track's texture_overrides ROOF key); "off_terrain" = a far backdrop past the built ground: it stands at the nearest ground's
              height with OFF_TERRAIN_SKIRT_M more wall below -> FARBLOCK_<SKIN>_<k>, no collider: never a GrassFX occluder (the
              TDR lesson in scripts/ac/ext_config.py) and never read by the seat gate. "replace": the scene's own meshes of these exact
              names (the v021 assembler's HOUSE / BUILDING boxes on Lake Murray) are removed first, so the pipeline's stand alone. Any ring, flat roof, walls batched by skin -> BUILDING_TILTUP_<k> / BUILDING_METAL_<k> /
              BUILDING_FABRICB_<k> (joined only within one building: tools/house_seat_check.py re-joins by position),
              ROOFTOP_<WHITE|TAN|DARK>_<k>, 1WALL_TILTUP_<k> (the collider). "auto" = a planned file: a footprint the
              checks refuse is dropped and counted, more than AUTO_DROP_MAX of them is a failure; one past the physical 1GRASS
              stands as a far block within FAR_REACH_M of the lap and is dropped beyond it. Hand-measured entries refuse.
  pads        [{"key", "quad_lonlat": [4 corners in order]}]: a visual sheet draped PAD_LIFT_M over the ground on a PAD_CELL_M
              grid, cells over a road left out -> PADAPRON_<k>
  cards       [{"file", "prefix": "TREECARD", "clear_m"}]: {"cols", "rows", "points": [[lon, lat, cell, h, w], ...]}; crossed
              double-sided cards on the ground, anything within clear_m of pavement or a wall dropped and counted -> <prefix>_<k>
  (blocks group key) "collider_tri_m": the longest ground-polygon edge a collider may stand over (default COLLIDER_TRI_M, 8 m)
  (blocks group key) "rim_step_m": the rim walk that finds a block's ground (default BLOCK_RIM_STEP_M, 1 m; Lake Murray v4's 7,600
              blocks were stood at 2.0 m, the walk before ledger 0063, and its config keeps that: ledger 0065)
  guardrail   {"from": "1WALL_PARA"}: a W-beam rail and posts along the draft's guard lips (RAIL_* below), road side. The
              lips keep their shape and are renamed 1WALL_GHOST_*, a transparent skin: the collider the gates judged stays
  prep_seats  true where the prep that follows is engine-july's (Lake Murray): it re-seats every BUILDING* island itself, so a
              block is authored at the prep's floor; false (the chain) = the block carries its own foundation
  names       {"ground": [...], "far": [...], "paved": [...], "track_edge": [...], "cone_ground": [...], "walls": [...]}: the scene's
              mesh-name prefixes where they are not the chain's (Lake Murray at the author stage: TERRAIN, GRASS_FAR, ROAD, CURB;
              the prep renames them to 1GRASS / 1ROAD / 1KERB later). Defaults = the chain's names below
  rails       [{"key", "kind": "tecpro" | "krail", "polyline_lonlat", "auto", "height_m"}]: collidable module lines seated on
              the ground -> 1WALL_TECPRO_<k> / 1WALL_KRAILBW_<k>; "auto" leaves a module out when it would stand on a road,
              instead of refusing; "height_m" (optional): a measured height over the ground, in place of the kind's

SELF-CHECKS, exit 1 and loop.blend NOT saved: a building's footprint (ring + interior) and every scrub foot off every road
and kerb; every cone foot off the main road; a building at least BUILDING_CLEAR_M from the road and any wall; ground under every read; no AC_* touched.
One line per object with the numbers it checked (L12).

Runs inside Blender, in the chain's author phase (tools/ship_track.sh author_bespoke):

    blender --background --python-exit-code 1 --python tools/author_bespoke_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import random
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402  (the draft's own lon/lat -> metres)

COLLECTION = "AUTH_bespoke"
OWN_PREFIXES = ("BUILDING_FABRIC", "1WALL_FABRIC", "PROPCONE", "SCRUBCARD", "BUILDING_TILTUP", "BUILDING_METAL", "ROOFTOP",
                "1WALL_TILTUP", "PADAPRON", "TREECARD", "PRAIRIECARD", "GUARDRAIL", "1WALL_TECPRO", "1WALL_KRAILBW", "BUILDING_DRYSTONE", "FARBLOCK")
GROUND = ("1GRASS",)
GROUND_FAR = ("1GRASS", "GRASS_FAR")
PAVED = ("1ROAD", "1RUNOFF", "1KERB")
TRACK_EDGE = ("1ROAD_MAIN", "1KERB")   # a cone marks this edge; the shoulder and the corners' run-off beyond it are its ground
CONE_GROUND = ("1GRASS", "1RUNOFF", "1ROAD_SHOULDER", "1KERB")
WALLS = ("1WALL", "BARRIER")
BOTTOM_UNDER_M = 0.15          # tools/house_seat_check.py: a seated bottom sits 0.15-0.40 m under the lowest ground
MAX_RELIEF_M = 2.5             # [invented] more relief than this under a footprint is a building on a cut edge: refused
BUILDING_CLEAR_M = 3.0         # [invented] a wall this close to a road or barrier would stand in the run-off
COLLIDER_INSET_M = 0.03        # [invented] inside the shell, so the collider never z-fights it
FABRIC_BAY_M = 5.0             # tools/make_bespoke_assets.py FABRIC_BAY_M: one tile
CONE_OFF_EDGE_M = 0.6          # [invented] a marker just off the paved edge
EDGE_SCAN_M = 30.0             # a cone looks this far out from the centreline for the paved edge
CONES_PER_MESH = 32
PREP_SEATS = False             # scenery.bespoke.prep_seats: the prep that follows re-seats BUILDING* islands (engine-july's does)
SCRUB_ROAD_CLEAR_M = 4.0       # [invented] the imagery's clumps stand well off any pavement
CARDS_PER_MESH = 64
OFF_TERRAIN_SKIRT_M = 4.0      # [invented] a far backdrop's wall carries on this far below the nearest ground
BLOCK_RIM_STEP_M = 1.0         # [invented] the rim sampled for a block's lowest ground: 2.0 m stepped over a 0.27 m dip in the fine ground beside a street (ledger 0063)
COLLIDER_STEP_M = 3.0          # [invented] the collider's skirt follows the ground at this spacing (see the collider rule in blocks)
FAR_REACH_M = 450.0            # [invented] a far block past this from the lap is dropped: unseen from the car, weight in the kn5
COLLIDER_TRI_M = 8.0           # [invented] a collider stands only over ground triangles finer than this (see bvh / down_edge)
COLLIDER_REACH_M = 60.0        # [invented] Sand Creek still read floating at 100 m; the corridor's fine terrain reaches at least this far off the lap
AUTO_DROP_MAX = 0.35           # [invented] a planned file losing more than this share to the checks is a wrong plan, not noise
AUTO_RELIEF_SHARE = 0.8        # [invented] a planned building may straddle relief up to this share of its wall
BLOCK_BATCH_VERTS = 12000      # [invented] under either prep's tile cap (airoso 50,000; engine-july's is smaller), so no building is ever cut in two
TILE_BAY = {"TILTUP": 8.0, "METAL": 0.914, "FABRICB": 5.0, "DRYSTONE": 2.0, "STUCCO": 3.0, "SIDING": 3.0}    # tools/make_bespoke_assets.py: one tile along a wall, in metres
ROOF_TILE_M = {"SHINGLE": 2.0}  # tools/make_bespoke_assets.py; every other roof tile reads at ROOF_TILE_DEFAULT_M
ROOF_TILE_DEFAULT_M = 12.0     # [invented] a flat roof's membrane tile on the roof
PARAPET_M = 0.7                # [invented] a flat commercial roof's parapet, as a lip above the roof
# engine-july's prep (Lake Murray's) has a house seat: every BUILDING* island is re-seated with its floor at the mean ground less
# HOUSE_SINK_M, raised so HOUSE_SHOW of its height clears the highest ground, its base ring pushed to HOUSE_FOOT_M under the lowest
# ground. airoso's prep (the chain's) has none. The block's visible walls start at that floor on both; where the prep seats
# (scenery.bespoke.prep_seats true) the block is authored AT the floor so the prep moves its walls by nothing and the roof, another
# object the prep never touches, stays on them; where it does not, the walls carry on down to the foundation themselves
PREP_SINK_M, PREP_SHOW, PREP_FOOT_M = 0.4, 0.5, 0.15
SET_IN_SUFFIX = "_SETIN"       # ledger 0083 pass 4b: a set-in deck's walls, BUILDING_<SKIN>_SETIN_<k> (pbr binds BUILDING_<SKIN>)
SET_IN_LIFT_M = 1.0            # their object transform (the same world positions): the prep's house seat leaves them be
ELEV0 = 0.0                    # the origin's NAVD88 height (centerline.local.json), set in main
RECT_FILL = 0.82               # [invented] a ring filling less of its oriented box than this is not a rectangle: flat roof
PAD_CELL_M = 4.0               # [invented] a cell of a draped pad
PAD_LIFT_M = 0.06              # [invented] above the ground, under any kerb
# W-beam: AASHTO M 180 section 312 mm tall and 83 mm deep, posts every 1.905 m (both as DOSSIER (Lariat) section 8 and
# tools/make_bespoke_assets.py cite them); the rail's top rides the lip's top, 0.70 m over its foot, against the 0.79 m of
# a modern rail. The cross-section's intermediate points are [invented] by eye
RAIL_H = (0.0, 0.040, 0.078, 0.156, 0.234, 0.272, 0.312)
RAIL_D = (0.020, 0.060, 0.083, 0.030, 0.083, 0.060, 0.020)
RAIL_POST_M = 1.905
RAIL_PANEL_M = 3.81
RAIL_GAP_M = 6.0               # [invented] lips further apart than this are two runs
RAIL_LIP_H = 0.70              # the draft's lip, read off Milford's 1WALL_PARA_stone
# Tec-Pro: 1.2 m tall, 1.5 m long, 0.8 m deep modules [invented: public photos only, no published drawing was read]
RAIL_KINDS = {"tecpro": ("1WALL_TECPRO", 1.2, 1.5, 0.8),
              # High Plains' painted barriers: a Caltrans-type K-rail is 0.81 m tall, 0.6 m at the foot, 3 m a section
              # (cited from memory, not re-read); the paint alternates every section on NAIP 2023
              "krail": ("1WALL_KRAILBW", 0.81, 3.0, 0.6)}


EDGE_OF = {}                   # id(BVH) -> the longest edge of each polygon, in metres (for the collider's fine-ground rule)


def bvh(prefixes):
    """(BVH, owner name per polygon) over every mesh whose name starts with a prefix, world space"""
    verts, polys, owner, edges = [], [], [], []
    for o in bpy.data.objects:
        u = o.name.upper()
        if o.type != "MESH" or not u.startswith(prefixes) or u.startswith(OWN_PREFIXES):
            continue
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ Vector(v.co) for v in o.data.vertices]
        for p in o.data.polygons:
            ids = [off + i for i in p.vertices]
            polys.append(ids)
            owner.append(u)
            edges.append(max((verts[a] - verts[b]).length for a, b in zip(ids, ids[1:] + ids[:1])))
    tree = BVHTree.FromPolygons(verts, polys) if polys else None
    if tree is not None:
        EDGE_OF[id(tree)] = edges
    return tree, owner


def down_edge(tree, x, y):
    """the longest edge of the polygon under (x, y) in a BVH, or None when nothing is under it"""
    if tree is None:
        return None
    hit = tree.ray_cast(Vector((x, y, 3000.0)), Vector((0.0, 0.0, -1.0)), 6000.0)
    return None if hit[0] is None else EDGE_OF[id(tree)][hit[2]]


def collider_ground_ok(edges, limit):
    """a collider may stand when every sampled ground polygon under its ring exists and has no edge longer than ``limit`` m.
    ``edges`` is down_edge() per sample (None = no ground). ``limit`` is COLLIDER_TRI_M unless the block group declares
    ``collider_tri_m`` (High Plains: its 1GRASS_ring seating fans put 12 m-long slivers under two posts, ledger 0072)"""
    return all(e is not None and e <= limit for e in edges)


def down(tree, x, y):
    """the highest surface of a BVH under (x, y): height or None"""
    if tree is None:
        return None
    hit = tree.ray_cast(Vector((x, y, 3000.0)), Vector((0.0, 0.0, -1.0)), 6000.0)
    return None if hit[0] is None else float(hit[0].z)


def lonlat_to_xy(origin):
    m_lon, m_lat = _meters_per_degree(origin["lat"])

    def f(p):
        return (p[0] - origin["lon"]) * m_lon, (p[1] - origin["lat"]) * m_lat
    return f


def ensure_collection():
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    for ob in list(col.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    return col


def make_mesh(col, name, verts, faces, uvs, smooth_groups=None):
    """``faces`` = vertex-index tuples, ``uvs`` = one uv per corner of each face; flat unless a face's group says smooth"""
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces, shade_flat=True)
    layer = me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, uvs):
        for k, li in enumerate(poly.loop_indices):
            layer.data[li].uv = uv[k]
    if smooth_groups is not None:
        owners = {}
        for poly, g in zip(me.polygons, smooth_groups):
            poly.use_smooth = g != 0
            for ek in poly.edge_keys:
                owners.setdefault(ek, []).append(g)
        sharp = {ek for ek, gs in owners.items() if len(gs) != 2 or gs[0] != gs[1] or gs[0] == 0}
        for e in me.edges:
            e.use_edge_sharp = tuple(sorted(e.vertices)) in sharp
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def inward_ring(ring):
    """counter-clockwise seen from above, so the walls built along it face outward"""
    a = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))
    return list(ring) if a > 0 else list(reversed(ring))


def footprint_points(ring, step=1.5):
    """the ring walked every ``step`` m, plus an interior grid: what the footprint stands on"""
    pts = []
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        n = max(1, int(math.dist(a, b) / step))
        pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    interior = []
    u = (ring[1][0] - ring[0][0], ring[1][1] - ring[0][1])
    v = (ring[3][0] - ring[0][0], ring[3][1] - ring[0][1])
    for i in range(1, 8):
        for j in range(1, 8):
            interior.append((ring[0][0] + u[0] * i / 8 + v[0] * j / 8, ring[0][1] + u[1] * i / 8 + v[1] * j / 8))
    return pts, interior


def wall_quad(verts, faces, uvs, a, b, z0, z1, arc):
    """a wall from a to b, outward on the right of a -> b seen from above (counter-clockwise ring); u by real metres"""
    off = len(verts)
    verts += [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
    faces.append((off, off + 1, off + 2, off + 3))
    w = math.dist(a, b)
    h = z1 - z0
    uvs.append(((arc / FABRIC_BAY_M, 0.0), ((arc + w) / FABRIC_BAY_M, 0.0), ((arc + w) / FABRIC_BAY_M, h / FABRIC_BAY_M),
                (arc / FABRIC_BAY_M, h / FABRIC_BAY_M)))
    return arc + w


def building(col, b, to_xy, ground, paved, walls, bad):
    key = b["key"]
    ring = inward_ring([to_xy(p) for p in b["footprint_lonlat"]])
    rim, inner = footprint_points(ring)
    gs = [down(ground, x, y) for x, y in rim]
    if any(g is None for g in gs):
        bad.append(f"building {key}: no ground under part of its walls")
        return None
    on_paved = [(round(x, 2), round(y, 2)) for x, y in rim + inner
                if (down(paved, x, y) is not None and down(paved, x, y) >= (down(ground, x, y) or -1e9) - 0.05)]
    if on_paved:
        bad.append(f"building {key}: footprint on a road or kerb at {len(on_paved)} points, e.g. {on_paved[:3]}")
    lo, hi, mean = min(gs), max(gs), sum(gs) / len(gs)
    if hi - lo > MAX_RELIEF_M:
        bad.append(f"building {key}: {hi - lo:.2f} m of relief under the footprint (> {MAX_RELIEF_M} m)")
    clear = float("inf")
    for tree, label in ((paved, "road"), (walls, "wall")):
        if tree is None:
            continue
        for x, y in rim:
            hit = tree.find_nearest(Vector((x, y, mean + 1.0)), 60.0)
            if hit[0] is not None:
                clear = min(clear, float(hit[3]))
    if clear < BUILDING_CLEAR_M:
        bad.append(f"building {key}: {clear:.2f} m from a road or wall (< {BUILDING_CLEAR_M} m)")
    bottom = lo - BOTTOM_UNDER_M
    wall_h = float(b["eave_h_m"] if b["roof"] == "gable" else b["wall_h_m"])
    level = max(mean, hi - wall_h / 2.0)                     # house_seat's "show"
    eave = level + wall_h
    verts, faces, uvs = [], [], []
    arc = 0.0
    n = len(ring)
    sides = [math.dist(ring[i], ring[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        arc = wall_quad(verts, faces, uvs, ring[i], ring[(i + 1) % n], bottom, eave, arc)
    if b["roof"] == "flat":
        off = len(verts)
        verts += [(x, y, eave) for x, y in ring]
        faces.append(tuple(range(off, off + n)))
        ox, oy = ring[0]
        ux, uy = (ring[1][0] - ox) / sides[0], (ring[1][1] - oy) / sides[0]
        uvs.append(tuple((((x - ox) * ux + (y - oy) * uy) / FABRIC_BAY_M, (-(x - ox) * uy + (y - oy) * ux) / FABRIC_BAY_M)
                         for x, y in ring))
        roof_note = f"flat, walls {wall_h:.2f} m"
    else:
        ridge_z = level + float(b["ridge_h_m"])
        # the ridge runs along the long sides, joining the midpoints of the two short (gable) ends
        s0 = 0 if sides[0] < sides[1] else 1
        a0, a1 = ring[s0], ring[(s0 + 1) % 4]              # one gable end, a0 -> a1 on the ring
        c0, c1 = ring[(s0 + 2) % 4], ring[(s0 + 3) % 4]    # the other
        m0 = ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2)
        m1 = ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2)
        span = math.dist(a0, a1) / 2
        slope = math.hypot(span, ridge_z - eave)
        length = math.dist(m0, m1)
        for p, q in ((a0, a1), (c0, c1)):                  # the gable triangles
            mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            off = len(verts)
            verts += [(p[0], p[1], eave), (q[0], q[1], eave), (mid[0], mid[1], ridge_z)]
            faces.append((off, off + 1, off + 2))
            uvs.append(((0.0, 0.0), (2 * span / FABRIC_BAY_M, 0.0), (span / FABRIC_BAY_M, (ridge_z - eave) / FABRIC_BAY_M)))
        for p, q, r0, r1 in ((a1, c0, m0, m1), (c1, a0, m1, m0)):      # the two roof slopes, eave p -> q, ridge over them
            off = len(verts)
            verts += [(p[0], p[1], eave), (q[0], q[1], eave), (r1[0], r1[1], ridge_z), (r0[0], r0[1], ridge_z)]
            faces.append((off, off + 1, off + 2, off + 3))
            uvs.append(((0.0, 0.0), (length / FABRIC_BAY_M, 0.0), (length / FABRIC_BAY_M, slope / FABRIC_BAY_M),
                        (0.0, slope / FABRIC_BAY_M)))
        roof_note = (f"gable, eave {wall_h:.2f} m, ridge {ridge_z - level:.2f} m, pitch "
                     f"{math.degrees(math.atan2(ridge_z - eave, span)):.1f} deg")
    make_mesh(col, f"BUILDING_FABRIC_{key}", verts, faces, uvs)
    # the collider: the walls again, inset, to the eave
    cx = sum(p[0] for p in ring) / n
    cy = sum(p[1] for p in ring) / n
    inset = []
    for x, y in ring:
        d = math.hypot(cx - x, cy - y)
        inset.append((x + (cx - x) / d * COLLIDER_INSET_M, y + (cy - y) / d * COLLIDER_INSET_M))
    verts, faces, uvs = [], [], []
    arc = 0.0
    for i in range(n):
        arc = wall_quad(verts, faces, uvs, inset[i], inset[(i + 1) % n], bottom, eave, arc)
    make_mesh(col, f"1WALL_FABRIC_{key}", verts, faces, uvs)
    print(f"[bespoke] building {key}: {sides[0]:.1f} x {sides[1]:.1f} m, {roof_note}; ground {lo:.2f}..{hi:.2f} (mean {mean:.2f}), level {level:.2f}, "
          f"bottom {bottom:.2f}, {clear:.1f} m clear of road and wall")
    return {"key": key, "sides_m": [round(s, 2) for s in sides], "ground": [round(lo, 3), round(hi, 3)],
            "bottom": round(bottom, 3), "eave": round(eave, 3), "clear_m": round(clear, 2)}


def load_obj(path):
    """vertices + faces (indices, per-corner uv, smoothing group), OBJ frame +y up"""
    verts, uvt, faces = [], [], []
    group = 0
    for ln in open(path, encoding="utf-8"):
        p = ln.split()
        if not p:
            continue
        if p[0] == "v":
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif p[0] == "vt":
            uvt.append((float(p[1]), float(p[2])))
        elif p[0] == "s":
            group = 0 if p[1] in ("off", "0") else int(p[1])
        elif p[0] == "f":
            ix, uv = [], []
            for q in p[1:]:
                a = q.split("/")
                ix.append(int(a[0]) - 1)
                uv.append(uvt[int(a[1]) - 1])
            faces.append((ix, uv, group))
    return verts, faces


def centreline(proj, with_network=False):
    d = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in d["points_xyz_m"]]
    if with_network and (proj / "data" / "expansion.north.json").exists():      # Lake Murray's north pieces: part of the lap for reach
        n = json.loads((proj / "data" / "expansion.north.json").read_text(encoding="utf-8"))
        for piece in n.get("pieces", []):
            pts += [(r[1], r[3] if isinstance(r[3], (int, float)) else 0.0, r[2]) for r in piece["stations"]]
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return pts, s, s[-1] + math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2])


def at_station(pts, s, total, q):
    """(x, y) and the unit tangent (Blender frame) at arc ``q`` of the closed lap"""
    q %= total
    lo, hi = 0, len(s) - 1
    while lo < hi:
        m = (lo + hi + 1) // 2
        if s[m] <= q:
            lo = m
        else:
            hi = m - 1
    a, b = pts[lo], pts[(lo + 1) % len(pts)]
    seg = math.hypot(b[0] - a[0], b[2] - a[2]) or 1e-9
    t = (q - s[lo]) / seg
    return (a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t), ((b[0] - a[0]) / seg, (b[2] - a[2]) / seg)


def cones(col, spec, proj, bad):
    model = json.loads((AIROSO / "assets" / "models" / "traffic_cone.json").read_text(encoding="utf-8"))
    mv, mf = load_obj(AIROSO / "assets" / "models" / model["file"])
    pts, s, total = centreline(proj)
    foot_r = float(model["footprint_radius_m"])
    track = bvh(TRACK_EDGE)[0]
    main = bvh(("1ROAD_MAIN",))[0]
    seat = bvh(CONE_GROUND)[0]
    all_v, all_f, all_uv, all_g, rows, batches = [], [], [], [], [], 0

    def flush():
        nonlocal all_v, all_f, all_uv, all_g, batches
        if all_v:
            make_mesh(col, f"PROPCONE_{batches}", all_v, all_f, all_uv, all_g)
            batches += 1
            all_v, all_f, all_uv, all_g = [], [], [], []
    for k, st in enumerate(spec["stations"]):
        (cx, cy), (tx, ty) = at_station(pts, s, total, float(st["s"]))
        nx, ny = (-ty, tx) if st["side"] == "L" else (ty, -tx)        # outward from the centreline on that side
        edge = None
        d = 0.0
        while d < EDGE_SCAN_M:
            d += 0.1
            if down(track, cx + nx * d, cy + ny * d) is None:
                edge = d
                break
        if edge is None:
            bad.append(f"cone {k} (corner {st['corner']} {st['role']}): no track edge within {EDGE_SCAN_M} m of s {st['s']}")
            continue
        off = edge + CONE_OFF_EDGE_M + foot_r
        x, y = cx + nx * off, cy + ny * off
        g = down(seat, x, y)
        if g is None or down(main, x, y) is not None:
            bad.append(f"cone {k} (corner {st['corner']} {st['role']}): its foot at ({x:.1f}, {y:.1f}) is on the main road or on nothing")
            continue
        yaw = math.atan2(ty, tx)
        c, sn = math.cos(yaw), math.sin(yaw)
        base = len(all_v)
        for vx, vy, vz in mv:
            all_v.append((x + vx * c - vz * sn, y + vx * sn + vz * c, g + vy))       # OBJ (x, y up, z) -> (E, N, up)
        for ix, uv, grp in mf:                                                        # reversed: the remap is a reflection
            all_f.append(tuple(base + i for i in reversed(ix)))
            all_uv.append(tuple(reversed(uv)))
            all_g.append(grp)
        rows.append({"k": k, "corner": st["corner"], "role": st["role"], "s": st["s"], "side": st["side"],
                     "xy": [round(x, 2), round(y, 2)], "ground": round(g, 3), "edge_m": round(edge, 2)})
        print(f"[bespoke] cone {k:2d} corner {st['corner']} {st['role']:5s} s {st['s']:7.1f} {st['side']}: track edge {edge:5.2f} m "
              f"from the centreline, foot ({x:7.1f}, {y:7.1f}) seated at {g:.2f}")
        if len(rows) % CONES_PER_MESH == 0:
            flush()
    flush()
    return rows


def point_in_polygon(poly, x, y):
    inside = False
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def scrub(col, spec, to_xy, ground, paved, walls, bad):
    poly = [to_xy(p) for p in spec["polygon_lonlat"]]
    rng = random.Random(int(spec["seed"]))
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    lo, hi = spec["size_m"]
    share = float(spec.get("creosote_share", 0.7))
    verts, faces, uvs, n_mesh, placed, tries = [], [], [], 0, [], 0
    want = int(spec["count"])

    def flush():
        nonlocal verts, faces, uvs, n_mesh
        if verts:
            make_mesh(col, f"SCRUBCARD_{n_mesh}", verts, faces, uvs)
            n_mesh += 1
            verts, faces, uvs = [], [], []
    while len(placed) < want and tries < want * 200:
        tries += 1
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        if not point_in_polygon(poly, x, y):
            continue
        g = down(ground, x, y)
        if g is None:
            continue
        near_paved = paved.find_nearest(Vector((x, y, g)), SCRUB_ROAD_CLEAR_M) if paved is not None else (None,)
        near_wall = walls.find_nearest(Vector((x, y, g)), SCRUB_ROAD_CLEAR_M) if walls is not None else (None,)
        if near_paved[0] is not None or near_wall[0] is not None:
            continue
        creosote = rng.random() < share
        col_ = rng.randrange(2)
        row = 0 if creosote else 1                  # the atlas's top row is creosote; v counts from its bottom edge
        u0, u1 = col_ * 0.5, (col_ + 1) * 0.5
        v0, v1 = (0.5, 1.0) if row == 0 else (0.0, 0.5)
        h = rng.uniform(lo, hi) if creosote else rng.uniform(lo, hi) * 0.5
        half = h * 0.5
        yaw = rng.uniform(0, math.pi)
        for a in (yaw, yaw + math.pi / 2):          # two crossed planes, each double-sided
            dx, dy = math.cos(a) * half, math.sin(a) * half
            base = len(verts)
            verts += [(x - dx, y - dy, g - 0.03), (x + dx, y + dy, g - 0.03), (x + dx, y + dy, g + h), (x - dx, y - dy, g + h)]
            faces.append((base, base + 1, base + 2, base + 3))
            uvs.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
            base = len(verts)
            verts += [(x + dx, y + dy, g - 0.03), (x - dx, y - dy, g - 0.03), (x - dx, y - dy, g + h), (x + dx, y + dy, g + h)]
            faces.append((base, base + 1, base + 2, base + 3))
            uvs.append(((u1, v0), (u0, v0), (u0, v1), (u1, v1)))
        placed.append({"xy": [round(x, 2), round(y, 2)], "h_m": round(h, 2), "kind": "creosote" if creosote else "bursage",
                       "ground": round(g, 3)})
        if len(placed) % CARDS_PER_MESH == 0:
            flush()
    flush()
    if len(placed) < want:
        bad.append(f"scrub: placed {len(placed)} of {want} clumps inside the polygon in {tries} tries")
    n_c = sum(1 for p in placed if p["kind"] == "creosote")
    print(f"[bespoke] scrub: {len(placed)} clumps ({n_c} creosote, {len(placed) - n_c} bursage), heights "
          f"{min(p['h_m'] for p in placed) if placed else 0}..{max(p['h_m'] for p in placed) if placed else 0} m, every foot on the "
          f"ground and >= {SCRUB_ROAD_CLEAR_M} m from pavement and walls, {n_mesh} mesh(es)")
    return placed


class Batcher:
    """one mesh per BLOCK_BATCH_VERTS, a building never cut in two; make_mesh on flush"""

    def __init__(self, col, prefix):
        self.col, self.prefix, self.k = col, prefix, 0
        self.v, self.f, self.uv = [], [], []

    def room(self, n):
        if self.v and len(self.v) + n > BLOCK_BATCH_VERTS:
            self.flush()

    def add(self, verts, faces, uvs):
        off = len(self.v)
        self.v += verts
        self.f += [tuple(off + i for i in f) for f in faces]
        self.uv += uvs

    def flush(self):
        if self.v:
            make_mesh(self.col, f"{self.prefix}_{self.k}", self.v, self.f, self.uv)
            self.k += 1
            self.v, self.f, self.uv = [], [], []


CANOPY_SLAB_M = 0.3            # [invented] an open-sided roof's slab: its top is the measured roof, its soffit this under it
CANOPY_POST_W = 0.3            # [invented] a canopy post's square section
CANOPY_POST_M = 6.0            # [invented] posts at every ring corner and at most this far apart along an edge


def canopy_on_posts(ring, bottom, top, slab=CANOPY_SLAB_M, post_w=CANOPY_POST_W, step=CANOPY_POST_M):
    """Pure: the "posts" form (ledger 0083 pass 3): an open-sided roof (a pavilion, a fuel canopy). ``ring`` counter-clockwise
    seen from above; the slab is the ring extruded from ``top - slab`` to ``top``; a square post stands at every ring corner
    and every ``step`` along each edge, from ``bottom`` to the soffit, inside the ring. Each post's outer top corner IS a
    slab vertex (shared index), so posts and slab are ONE island: the prep re-seats it by its feet (the lowest vertices)
    and tools/house_seat_check.py judges it by them. Returns (verts, faces, uvs, n_posts); no walls, no collider."""
    pts = []
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        n = max(1, math.ceil(math.dist(a, b) / step))
        pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    m = len(pts)
    soffit = top - slab
    verts = [(x, y, soffit) for x, y in pts] + [(x, y, top) for x, y in pts]
    faces, uvs = [], []
    for i in range(m):                                         # the slab's edge band
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
        uvs.append(((0.0, 0.0), (1.0, 0.0), (1.0, slab), (0.0, slab)))
    faces.append(tuple(range(m, 2 * m)))                        # top, facing up (ccw)
    uvs.append(tuple((x / 4.0, y / 4.0) for x, y in pts))
    faces.append(tuple(range(m - 1, -1, -1)))                   # soffit, facing down
    uvs.append(tuple((pts[i][0] / 4.0, pts[i][1] / 4.0) for i in range(m - 1, -1, -1)))
    for i in range(m):
        a, b = pts[i], pts[(i + 1) % m]
        L = math.dist(a, b) or 1.0
        e1 = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        e2 = (-e1[1], e1[0])                                    # inward for a counter-clockwise ring
        q = [a, (a[0] + e1[0] * post_w, a[1] + e1[1] * post_w),
             (a[0] + (e1[0] + e2[0]) * post_w, a[1] + (e1[1] + e2[1]) * post_w), (a[0] + e2[0] * post_w, a[1] + e2[1] * post_w)]
        o = len(verts)
        verts += [(x, y, bottom) for x, y in q] + [(x, y, soffit) for x, y in q[1:]]
        tops = [i, o + 4, o + 5, o + 6]                         # the outer top corner is the slab's own vertex i
        for k in range(4):
            kk = (k + 1) % 4
            faces.append((o + k, o + kk, tops[kk], tops[k]))
            uvs.append(((0.0, 0.0), (post_w, 0.0), (post_w, top - bottom), (0.0, top - bottom)))
    return verts, faces, uvs, m


def ring_points(ring, step=2.0):
    """a ring of any shape walked every ``step`` m + a grid of interior points"""
    pts = []
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        n = max(1, int(math.dist(a, b) / step))
        pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    grid = [(min(xs) + (max(xs) - min(xs)) * i / 7, min(ys) + (max(ys) - min(ys)) * j / 7) for i in range(1, 7) for j in range(1, 7)]
    return pts, [q for q in grid if point_in_polygon(ring, q[0], q[1])]


def blocks(col, spec, proj, to_xy, ground, near_ground, paved, walls, bad):
    """the batched flat-roofed buildings; see the header. Refusals: hand-measured entries fail the run, planned ones drop"""
    from mathutils.geometry import tessellate_polygon
    walls_by, roofs_by, rows, dropped = {}, {}, [], []
    lap = centreline(proj, with_network=True)[0]
    beyond = 0
    collider = Batcher(col, "1WALL_TILTUP")
    for group in spec:
        auto = bool(group.get("auto"))
        for name in group.get("replace", []):
            gone = [o for o in bpy.data.objects if o.type == "MESH" and (o.name == name or o.name.startswith(name + "."))]
            for o in gone:
                bpy.data.objects.remove(o, do_unlink=True)
            if gone:
                print(f"[bespoke] replaced the scene's {name} ({len(gone)} object(s)) with the pipeline's blocks")
        items = json.loads((proj / group["file"]).read_text(encoding="utf-8")) if group.get("file") else [group]
        kept0, drop0 = len(rows), len(dropped)
        for b in items:
            key, why = b["key"], None
            ring = inward_ring([to_xy(p) for p in b["footprint_lonlat"]])
            rim, inner = ring_points(ring, float(group.get("rim_step_m", BLOCK_RIM_STEP_M)))
            gs = [down(ground, x, y) for x, y in rim]
            wall_h = float(b["wall_h_m"])
            near = [down(near_ground, x, y) for x, y in ring]
            off = bool(b.get("off_terrain")) or (auto and (any(g is None for g in gs) or any(g is None for g in near)))
            if off and auto:
                # a planned footprint past the physical ground is a far block only within FAR_REACH_M of the lap: beyond that it
                # is never seen from the car and only weighs the kn5 (Lake Murray's 18,002 boxes made a 181 MB road kn5)
                reach = min(math.hypot(x - q[0], y - q[2]) for x, y in ring[:: max(1, len(ring) // 4)] for q in lap[::6])
                if reach > FAR_REACH_M:
                    dropped.append(f"block {key}: {reach:.0f} m from the lap, past FAR_REACH_M")
                    beyond += 1
                    continue
            if off:
                seen = [g for g in gs if g is not None]
                if seen:                                   # part of it is on the built ground: that part sets the seat
                    lo, hi, mean = min(seen), max(seen), sum(seen) / len(seen)
                else:
                    cx0, cy0 = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
                    hit = ground.find_nearest(Vector((cx0, cy0, 0.0)), 5000.0)
                    if hit[0] is None:
                        why = "no ground anywhere near it"
                    else:
                        lo = hi = mean = float(hit[0].z)
                        lo -= OFF_TERRAIN_SKIRT_M
            elif any(g is None for g in gs):
                why = "no ground under part of its walls"
            else:
                lo, hi, mean = min(gs), max(gs), sum(gs) / len(gs)
                # a shed's (ledger 0083 pass 4) walls rise from its low eave to its high one: its mean wall is the share's measure
                wall_m = (wall_h + float(b.get("ridge_h_m", wall_h))) / 2 if b.get("form") == "shed" else wall_h
                limit = max(MAX_RELIEF_M, wall_m * AUTO_RELIEF_SHARE) if auto else MAX_RELIEF_M
                if hi - lo > limit and not b.get("set_in"):   # a set-in deck (pass 4b) stands in the relief it was measured in
                    why = f"{hi - lo:.1f} m of relief under it"
                elif any(down(paved, x, y) is not None for x, y in rim + inner):
                    why = "on a road or kerb"
                else:
                    clear = float("inf")
                    for tree in (paved, walls):
                        for x, y in rim[:: max(1, len(rim) // 24)]:
                            hit = tree.find_nearest(Vector((x, y, mean + 1.0)), 30.0) if tree is not None else (None,)
                            if hit[0] is not None:
                                clear = min(clear, float(hit[3]))
                    if clear < BUILDING_CLEAR_M:
                        why = f"{clear:.1f} m from a road or wall"
            if why:
                (dropped if auto else bad).append(f"block {key}: {why}")
                continue
            skin = str(b.get("skin", "tiltup")).upper()
            bay = TILE_BAY[skin]
            form = str(b.get("form", "flat"))
            par_m = float(b.get("parapet_m", PARAPET_M))      # a planned row's MEASURED parapet (ledger 0083 pass 4), else PARAPET_M
            total_h = wall_h + (max(0.0, float(b.get("ridge_h_m", wall_h)) - wall_h) if form in ("hip", "gable", "shed") else (par_m if form == "flat_parapet" else 0.0))
            floor = max(mean - PREP_SINK_M, hi - (1.0 - PREP_SHOW) * total_h)         # the prep's floor, see PREP_SINK_M
            if off:
                bottom, eave = lo - BOTTOM_UNDER_M, lo - BOTTOM_UNDER_M + wall_h
            elif PREP_SEATS:
                bottom, eave = floor, floor + wall_h
            else:
                bottom, eave = min(floor, lo - PREP_FOOT_M), floor + wall_h
            set_in = b.get("set_in") if not off else None
            if set_in:
                # set into the slope (ledger 0083 pass 4b, a planned row's "set_in"): every height of the row is over its MEASURED
                # low ground, at that ground's own height (NAVD88 less the origin's); the walls run down to the real ground on
                # every side (PREP_FOOT_M under the lowest under its walls), so the uphill side stands in the hill as built
                floor = float(set_in["ground_navd88"]) - ELEV0
                bottom, eave = min(floor, lo) - PREP_FOOT_M, floor + wall_h
            n = len(ring)
            if form == "posts":
                # an open-sided roof on posts (ledger 0083 pass 3), opt-in: only a planned row whose form names it
                # (tools/plan_buildings.py's plan key canopy_posts, a MEASURED roof only). One welded island per canopy,
                # ribbed metal; no walls, no collider (a canopy within COLLIDER_REACH_M of the lap is refused instead)
                reach = min(math.hypot(x - q[0], y - q[2]) for x, y in ring[:: max(1, n // 4)] for q in lap[::4])
                if reach <= COLLIDER_REACH_M or off:
                    (dropped if auto else bad).append(f"block {key}: a canopy on posts {reach:.0f} m from the lap"
                                                      f"{' (off the ground)' if off else ''}: no post collider yet")
                    continue
                cv, cf, cu, n_posts = canopy_on_posts(ring, bottom, eave)
                cb = walls_by.setdefault(("CANOPY", off), Batcher(col, "BUILDING_METAL_CANOPY"))
                cb.room(len(cv))
                cb.add(cv, cf, cu)
                rows.append({"key": key, "skin": "METAL", "roof": "METAL", "form": f"posts ({n_posts}), slab {CANOPY_SLAB_M} m",
                             "wall_h_m": wall_h, "ground": [round(lo, 2), round(hi, 2)], "bottom": round(bottom, 2),
                             "eave": round(eave, 2), "off_terrain": off, "collider": False})
                continue
            cx_, cy_ = sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
            if set_in:
                batch = walls_by.setdefault((skin, "set_in"), Batcher(col, f"BUILDING_{skin}{SET_IN_SUFFIX}"))
            else:
                batch = walls_by.setdefault((skin, off), Batcher(col, f"FARBLOCK_{skin}" if off else f"BUILDING_{skin}"))
            batch.room(5 * n)
            bay_h0 = (floor - bottom) if not off else 0.0        # the wall tile starts at the floor: the foundation shows the tile below it
            tops = [eave] * n
            if form == "shed":
                # one measured plane (ledger 0083 pass 4, a planned row's "plane"): the walls rise to it at every ring vertex and
                # the roof IS the ring at those heights. h_m over the level at ref_lonlat, gx / gy per metre east / north
                pl = b["plane"]
                rx, ry = to_xy(pl["ref_lonlat"])
                base_z = eave - wall_h
                tops = [base_z + float(pl["h_m"]) + float(pl["gx"]) * (x - rx) + float(pl["gy"]) * (y - ry) for x, y in ring]
                tops = [max(t, base_z + 0.3) for t in tops]
            batch_v = [(x, y, bottom) for x, y in ring] + [(x, y, t) for (x, y), t in zip(ring, tops)]
            faces, uvs, arc = [], [], 0.0
            h = eave - bottom
            for i in range(n):
                j = (i + 1) % n
                w = math.dist(ring[i], ring[j])
                faces.append((i, j, n + j, n + i))
                hi_, hj_ = tops[i] - bottom, tops[j] - bottom
                uvs.append(((arc / bay, -bay_h0 / bay), ((arc + w) / bay, -bay_h0 / bay), ((arc + w) / bay, (hj_ - bay_h0) / bay), (arc / bay, (hi_ - bay_h0) / bay)))
                arc += w
            if form == "flat_parapet":
                # the parapet carries on from the eave ring's OWN vertices (one island: the prep re-seats a building by island),
                # PARAPET_M up, a cap 0.25 m wide, and back down inside
                inset = []
                for x, y in ring:
                    d = math.hypot(cx_ - x, cy_ - y) or 1.0
                    inset.append((x + (cx_ - x) / d * 0.25, y + (cy_ - y) / d * 0.25))
                top_o = len(batch_v)
                batch_v += [(x, y, eave + par_m) for x, y in ring]
                top_i = len(batch_v)
                batch_v += [(x, y, eave + par_m) for x, y in inset]
                bot_i = len(batch_v)
                batch_v += [(x, y, eave) for x, y in inset]
                arc = 0.0
                for i in range(n):
                    j = (i + 1) % n
                    w = math.dist(ring[i], ring[j])
                    faces += [(n + i, n + j, top_o + j, top_o + i), (top_o + i, top_o + j, top_i + j, top_i + i), (top_i + i, top_i + j, bot_i + j, bot_i + i)]
                    uvs += [((arc / bay, (h - bay_h0) / bay), ((arc + w) / bay, (h - bay_h0) / bay), ((arc + w) / bay, (h - bay_h0 + par_m) / bay), (arc / bay, (h - bay_h0 + par_m) / bay))] * 3
                    arc += w
            batch.add(batch_v, faces, uvs)
            rclass = str(b.get("roof", "white")).upper()
            rb = roofs_by.setdefault(rclass, Batcher(col, f"ROOFTOP_{rclass}"))
            rtile = ROOF_TILE_M.get(rclass, ROOF_TILE_DEFAULT_M)
            obb = oriented_box(ring)
            if obb is not None and b.get("ridge_axis") == "short":
                # a gable whose MEASURED ridge runs across the footprint (ledger 0083 pass 4): the box turned a quarter, the
                # same right-handed turn oriented_box makes, so the windings still face up and out
                obb = dict(obb, u=obb["v"], v=(-obb["u"][0], -obb["u"][1]), hw=obb["hh"], hh=obb["hw"])
            if form in ("hip", "gable") and obb is not None and obb["fill"] >= RECT_FILL:
                ridge_z = max(eave + 0.3, bottom + float(b.get("ridge_h_m", wall_h + 1.0)))
                rv, rf, ruv = pitched_roof(obb, eave, ridge_z, form, rtile)
                rb.room(len(rv))
                if rclass == "NAIP":
                    ruv = [tuple(naip_uv(b["roof_uv"], ring, (p[0], p[1])) for p in (rv[i] for i in f)) for f in rf]
                rb.add(rv, rf, ruv)
                roof_note = f"{form} ridge {ridge_z - (eave - wall_h):.1f} m" + (" across" if b.get("ridge_axis") == "short" else "")
            else:
                rb.room(n)
                tris = tessellate_polygon([[Vector((x, y, 0.0)) for x, y in ring]])
                ruv = [(x / rtile, y / rtile) for x, y in ring]
                if rclass == "NAIP":
                    ruv = [naip_uv(b["roof_uv"], ring, p) for p in ring]
                top_z = tops if form == "shed" else [eave] * n
                rb.add([(x, y, z) for (x, y), z in zip(ring, top_z)], [tuple(t) for t in tris], [tuple(ruv[i] for i in t) for t in tris])
                roof_note = "flat"
                if form == "flat_parapet":
                    roof_note = f"flat, parapet {par_m} m"
                elif form == "shed":
                    roof_note = f"shed {min(tops) - (eave - wall_h):.1f}..{max(tops) - (eave - wall_h):.1f} m"
            # a collider only within COLLIDER_REACH_M of the lap, on fine ground: drive_test culls ground triangles by centroid around a
            # wall's cell, so past the corridor's fine terrain a coarse triangle under a wall is culled and the wall reads floating 99.
            # Past that reach no lap is near it, so it is left see-through
            reach = min(math.hypot(x - q[0], y - q[2]) for x, y in ring[:: max(1, n // 4)] for q in lap[::4])
            footed = False
            if not off and reach <= COLLIDER_REACH_M:
                cx, cy = sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
                inset = []
                for x, y in ring:
                    d = math.hypot(cx - x, cy - y) or 1.0
                    inset.append((x + (cx - x) / d * COLLIDER_INSET_M, y + (cy - y) / d * COLLIDER_INSET_M))
                # drive_test reads every wall column (0.6 m cells) against the ground triangles whose centroid cell lies near the
                # wall: over a coarse triangle (Lake Murray's slope beside College, osm_buildings3: 31 columns "floating 99") it
                # finds nothing, so the collider stands only where ground finer than COLLIDER_TRI_M lies under EVERY 0.6 m of its
                # ring: pavement under a ring (a mouth fill, a stub) is not that ground
                footed = collider_ground_ok([down_edge(near_ground, x, y) for x, y in ring_points(inset, 0.6)[0]],
                                            float(group.get("collider_tri_m", COLLIDER_TRI_M)))
                # and its foot follows the ground: the gate takes each wall vertex's LOWEST point and looks for ground within 2.5 m
                # of it, so one flat foot at the footprint's lowest ground reads "floating 99" at the high corner of a sloped lot
                # (Lake Murray's two Mission Gorge columns stood 2.9 m under the grass, ledger 0062). A skirt walked every
                # COLLIDER_STEP_M, each vertex BOTTOM_UNDER_M under its own ground, is seated at every vertex the gate reads; the
                # prep never seats a 1WALL, so this is the collider's own foot
                skirt = ring_points(inset, COLLIDER_STEP_M)[0]
                feet = [down(near_ground, x, y) for x, y in skirt]
                footed = footed and all(g is not None for g in feet)
            if footed:
                m = len(skirt)
                collider.room(2 * m)
                collider.add([(x, y, g - BOTTOM_UNDER_M) for (x, y), g in zip(skirt, feet)] + [(x, y, eave) for x, y in skirt],
                             [(i, (i + 1) % m, m + (i + 1) % m, m + i) for i in range(m)],
                             [((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))] * m)
            rows.append({"key": key, "skin": skin, "roof": rclass, "form": roof_note, "wall_h_m": wall_h, "ground": [round(lo, 2), round(hi, 2)],
                         "bottom": round(bottom, 2), "eave": round(eave, 2), "off_terrain": off, "collider": footed})
            if set_in:
                rows[-1]["set_in"] = {"ground_navd88": float(set_in["ground_navd88"]), "floor": round(floor, 3),
                                      "deck_top": round(max(tops), 3), "deck_low": round(min(tops), 3),
                                      "ring_xy": [[round(x, 3), round(y, 3)] for x, y in ring]}
            if not auto:
                print(f"[bespoke] block {key}: {skin}, walls {wall_h:.1f} m, {roof_note}, ground {lo:.2f}..{hi:.2f}, bottom {bottom:.2f}, eave {eave:.2f}")
        n_kept, n_drop = len(rows) - kept0, len(dropped) - drop0
        if auto:
            print(f"[bespoke] {group['file']}: {n_kept} buildings stood, {n_drop} dropped ({beyond} of them past {FAR_REACH_M:.0f} m of the lap)")
            for_cause = [d for d in dropped[drop0:] if "FAR_REACH_M" not in d]
            for r in for_cause[:12]:
                print(f"[bespoke]   dropped {r}")
            tally = {}
            for d in for_cause:
                why_ = re.sub(r"[0-9.]+ m", "N m", d.split(": ", 1)[1])
                tally[why_] = tally.get(why_, 0) + 1
            if tally:
                print("[bespoke]   drop reasons: " + ", ".join(f"{n} {w}" for w, n in sorted(tally.items(), key=lambda t: -t[1])))
            n_drop -= beyond
            beyond = 0
            if n_kept + n_drop and n_drop / (n_kept + n_drop) > AUTO_DROP_MAX:
                bad.append(f"{group['file']}: {n_drop} of {n_kept + n_drop} planned buildings refused (> {AUTO_DROP_MAX:.0%})")
    for b in list(walls_by.values()) + list(roofs_by.values()) + [collider]:
        b.flush()
    # a set-in deck's walls (ledger 0083 pass 4b) are not re-seated by the prep: engine-july's house seat (build_kn5_loop)
    # seats only a BUILDING mesh at the identity transform ("not the draft's own mesh: left to the delta ride") and would
    # lift a deck set into a hill until half of it stood over its uphill ground. The same world positions, carried by an
    # object lift of SET_IN_LIFT_M, keep the measured placement; the delta ride moves it only by the prep's own ground
    # change under it (none past the corridor the prep reshapes)
    for ob in list(col.objects):
        if ob.type == "MESH" and SET_IN_SUFFIX in ob.name:
            for v in ob.data.vertices:
                v.co.z -= SET_IN_LIFT_M
            ob.location.z += SET_IN_LIFT_M
            ob.data.update()
    return rows


def oriented_box(ring):
    """the minimum-area box round a ring (an edge direction is a box direction): centre, unit axes, half-sizes, the ring's fill"""
    n = len(ring)
    area = abs(sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))) / 2
    best = None
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey)
        if ln < 1e-6:
            continue
        ux, uy = ex / ln, ey / ln
        vx, vy = -uy, ux
        us = [p[0] * ux + p[1] * uy for p in ring]
        vs = [p[0] * vx + p[1] * vy for p in ring]
        w, h = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * h < best[0]:
            cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (w * h, (cu * ux + cv * vx, cu * uy + cv * vy), (ux, uy), (vx, vy), w / 2, h / 2)
    if best is None or best[0] < 1e-6:
        return None
    _, c, u, v, hw, hh = best
    if hw < hh:                      # u along the long side
        u, v, hw, hh = v, (-u[0], -u[1]), hh, hw
    return {"c": c, "u": u, "v": v, "hw": hw, "hh": hh, "fill": area / (4 * hw * hh)}


def naip_uv(rect, ring, p):
    """Pure: a roof vertex's UV in its MEASURED colour's palette cell (ledger 0083 pass 4, tools/plan_buildings.py roof_palette):
    the footprint's box mapped onto the cell's inner rect [u0, v0, u1, v1], so the roof reads one solid colour and its UVs
    still span a real area (no degenerate tangents)"""
    xs, ys = [q[0] for q in ring], [q[1] for q in ring]
    w, h = (max(xs) - min(xs)) or 1.0, (max(ys) - min(ys)) or 1.0
    s, t = min(1.0, max(0.0, (p[0] - min(xs)) / w)), min(1.0, max(0.0, (p[1] - min(ys)) / h))
    return (rect[0] + (rect[2] - rect[0]) * s, rect[1] + (rect[3] - rect[1]) * t)


def pitched_roof(obb, eave, ridge_z, form, tile):
    """a hip roof (the ridge pulled in from each end by the half width) or a gable (two slopes, two triangular ends) on the box"""
    c, u, v, hw, hh = obb["c"], obb["u"], obb["v"], obb["hw"], obb["hh"]
    P = lambda a, b, z: (c[0] + u[0] * a + v[0] * b, c[1] + u[1] * a + v[1] * b, z)
    corners = [P(-hw, -hh, eave), P(hw, -hh, eave), P(hw, hh, eave), P(-hw, hh, eave)]
    slope = math.hypot(hh, ridge_z - eave)
    if form == "hip":
        r0, r1 = P(-(hw - hh), 0.0, ridge_z), P(hw - hh, 0.0, ridge_z)
        if hw - hh < 0.3:                      # a square plan: a pyramid
            r0 = r1 = P(0.0, 0.0, ridge_z)
        verts = corners + [r0, r1]
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
        uvs = [((0.0, 0.0), (2 * hw / tile, 0.0), ((hw - hh + hw) / tile, slope / tile), (hh / tile, slope / tile)),
               ((0.0, 0.0), (2 * hw / tile, 0.0), ((hw - hh + hw) / tile, slope / tile), (hh / tile, slope / tile)),
               ((0.0, 0.0), (2 * hh / tile, 0.0), (hh / tile, slope / tile)),
               ((0.0, 0.0), (2 * hh / tile, 0.0), (hh / tile, slope / tile))]
    else:
        r0, r1 = P(-hw, 0.0, ridge_z), P(hw, 0.0, ridge_z)
        verts = corners + [r0, r1]
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
        uvs = [((0.0, 0.0), (2 * hw / tile, 0.0), (2 * hw / tile, slope / tile), (0.0, slope / tile)),
               ((0.0, 0.0), (2 * hw / tile, 0.0), (2 * hw / tile, slope / tile), (0.0, slope / tile)),
               ((0.0, 0.0), (2 * hh / tile, 0.0), (hh / tile, (ridge_z - eave) / tile)),
               ((0.0, 0.0), (2 * hh / tile, 0.0), (hh / tile, (ridge_z - eave) / tile))]
    # outward: the ring is counter-clockwise seen from above; the box axes follow it, so these windings face up and out
    return verts, faces, uvs


def pads(col, spec, to_xy, ground, paved, bad):
    rows = []
    for k, p in enumerate(spec):
        # a pad is one quad ("quad_lonlat"), or a STRIP ("strip_lonlat": {"inner": [...], "outer": [...]}, equal lengths:
        # the quads between consecutive pairs, one mesh; ledger 0078 round 5, Nevada's measured run-off)
        if "strip_lonlat" in p:
            inn = [to_xy(c) for c in p["strip_lonlat"]["inner"]]
            out = [to_xy(c) for c in p["strip_lonlat"]["outer"]]
            if len(inn) != len(out) or len(inn) < 2:
                bad.append(f"pad {p['key']}: strip_lonlat inner / outer must be equal and >= 2 long")
                continue
            quads = [[inn[i], inn[i + 1], out[i + 1], out[i]] for i in range(len(inn) - 1)]
        else:
            quads = [[to_xy(c) for c in p["quad_lonlat"]]]
        verts, faces, uvs, skipped = [], [], [], 0
        for q in quads:
            nu = max(1, int(math.dist(q[0], q[1]) / PAD_CELL_M))
            nv = max(1, int(math.dist(q[1], q[2]) / PAD_CELL_M))
            idx = {}

            def vert(i, j):
                if (i, j) not in idx:
                    u, v = i / nu, j / nv
                    x = (q[0][0] * (1 - u) + q[1][0] * u) * (1 - v) + (q[3][0] * (1 - u) + q[2][0] * u) * v
                    y = (q[0][1] * (1 - u) + q[1][1] * u) * (1 - v) + (q[3][1] * (1 - u) + q[2][1] * u) * v
                    g = down(ground, x, y)
                    if g is None:
                        return None
                    idx[(i, j)] = len(verts)
                    verts.append((x, y, g + PAD_LIFT_M))
                return idx[(i, j)]
            for i in range(nu):
                for j in range(nv):
                    ids = [vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)]
                    if None in ids:
                        skipped += 1
                        continue
                    c = [verts[a] for a in ids]
                    mx, my = sum(a[0] for a in c) / 4, sum(a[1] for a in c) / 4
                    if any(down(paved, x, y) is not None for x, y in [(mx, my)] + [(a[0], a[1]) for a in c]):
                        skipped += 1
                        continue
                    area = sum(c[a][0] * c[(a + 1) % 4][1] - c[(a + 1) % 4][0] * c[a][1] for a in range(4))
                    ord_ = ids if area > 0 else ids[::-1]
                    faces.append(tuple(ord_))
                    uvs.append(tuple((verts[a][0] / 8.0, verts[a][1] / 8.0) for a in ord_))
        if not faces:
            bad.append(f"pad {p['key']}: no cell stood")
            continue
        make_mesh(col, f"PADAPRON_{k}", verts, faces, uvs)
        rows.append({"key": p["key"], "cells": len(faces), "left_out": skipped})
        print(f"[bespoke] pad {p['key']}: {len(faces)} cells, {skipped} left out (over a road or off the ground)")
    return rows


def cards(col, spec, proj, to_xy, ground, paved, walls, bad, pad_quads=()):
    rows = []
    for group in spec:
        d = json.loads((proj / group["file"]).read_text(encoding="utf-8"))
        cols, nrows = int(d["cols"]), int(d["rows"])
        clear = float(group.get("clear_m", 4.0))
        batch = Batcher(col, group["prefix"])
        kept = gone = 0
        for lon, lat, cell, h, w in d["points"]:
            x, y = to_xy((lon, lat))
            g = down(ground, x, y)
            if g is None or any(point_in_polygon(q, x, y) for q in pad_quads):
                gone += 1
                continue
            near = [t.find_nearest(Vector((x, y, g)), clear) if t is not None else (None,) for t in (paved, walls)]
            if near[0][0] is not None or near[1][0] is not None:
                gone += 1
                continue
            cl, rw = cell % cols, cell // cols
            u0, u1 = cl / cols, (cl + 1) / cols
            v1 = 1.0 - rw / nrows
            v0 = v1 - 1.0 / nrows
            yaw = (lon * 1e5 + lat * 1e5) % math.pi        # from the position, so a re-run reproduces it
            batch.room(16)
            verts, faces, uvs = [], [], []
            for a in (yaw, yaw + math.pi / 2):
                dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
                base = len(verts)
                verts += [(x - dx, y - dy, g - 0.05), (x + dx, y + dy, g - 0.05), (x + dx, y + dy, g + h), (x - dx, y - dy, g + h)]
                faces.append((base, base + 1, base + 2, base + 3))
                uvs.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
                base = len(verts)
                verts += [(x + dx, y + dy, g - 0.05), (x - dx, y - dy, g - 0.05), (x - dx, y - dy, g + h), (x + dx, y + dy, g + h)]
                faces.append((base, base + 1, base + 2, base + 3))
                uvs.append(((u1, v0), (u0, v0), (u0, v1), (u1, v1)))
            batch.add(verts, faces, uvs)
            kept += 1
        batch.flush()
        rows.append({"file": group["file"], "prefix": group["prefix"], "stood": kept, "dropped": gone})
        print(f"[bespoke] {group['prefix']} ({group['file']}): {kept} stood, {gone} dropped (no ground, or within {clear} m of pavement or a wall)")
    return rows


def guardrail(col, spec, proj, bad):
    """the rail along the draft's guard lips: the lip's own top and foot, its road side; the lip becomes the unseen collider"""
    src = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith((spec["from"], "1WALL_GHOST"))]
    if not src:
        bad.append(f"guardrail: no {spec['from']}* to follow")
        return {}
    cl = centreline(proj)[0]
    road = [(p[0], p[2]) for p in cl]
    stations = []                # (x, y, top z, foot z) per lip end, in mesh order
    for o in src:
        mw = o.matrix_world
        me = o.data
        tops = [p for p in me.polygons if p.normal.z > 0.9]        # two triangles per lip, in the mesh's order along the run
        for p in tops[::2]:
            c = sum((mw @ me.vertices[i].co for i in p.vertices), Vector((0, 0, 0))) / len(p.vertices)
            stations.append((c.x, c.y, c.z, c.z - RAIL_LIP_H))
    runs, cur = [], []
    for st in stations:
        if cur and math.dist(st[:2], cur[-1][:2]) > RAIL_GAP_M:
            runs.append(cur)
            cur = []
        cur.append(st)
    if cur:
        runs.append(cur)
    batch = Batcher(col, "GUARDRAIL")
    total, n_post = 0.0, 0
    for run in runs:
        if len(run) < 2:
            continue
        mid = run[len(run) // 2]
        rx, ry = min(road, key=lambda q: (q[0] - mid[0]) ** 2 + (q[1] - mid[1]) ** 2)
        a, b = run[0], run[-1]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1.0
        side = 1.0 if (-ty / ln) * (rx - mid[0]) + (tx / ln) * (ry - mid[1]) > 0 else -1.0     # +left of travel faces the road
        arc = 0.0
        next_post = 0.0
        for s0, s1 in zip(run, run[1:]):
            dx, dy = s1[0] - s0[0], s1[1] - s0[1]
            seg = math.hypot(dx, dy) or 1e-6
            nx, ny = -dy / seg * side, dx / seg * side
            verts, faces, uvs = [], [], []
            for k in range(len(RAIL_H) - 1):
                base = len(verts)
                for st_, u in ((s0, arc), (s1, arc + seg)):
                    for j in (k, k + 1):
                        z = st_[2] - 0.312 + RAIL_H[j]
                        verts.append((st_[0] + nx * (0.3 + RAIL_D[j]), st_[1] + ny * (0.3 + RAIL_D[j]), z))
                v = lambda j: 0.06 + 0.88 * RAIL_H[j] / 0.312
                u0, u1 = arc / RAIL_PANEL_M, (arc + seg) / RAIL_PANEL_M
                q = (base, base + 2, base + 3, base + 1)
                quv = ((u0, v(k)), (u1, v(k)), (u1, v(k + 1)), (u0, v(k + 1)))
                area_sign = side
                if area_sign > 0:
                    faces += [q, q[::-1]]
                    uvs += [quv, quv[::-1]]
                else:
                    faces += [q[::-1], q]
                    uvs += [quv[::-1], quv]
            while next_post <= arc + seg:
                t = (next_post - arc) / seg
                px, py = s0[0] + dx * t, s0[1] + dy * t
                top = s0[2] + (s1[2] - s0[2]) * t - 0.03
                foot = s0[3] + (s1[3] - s0[3]) * t - 0.15
                base = len(verts)
                hx, hy = dx / seg * 0.075, dy / seg * 0.075
                ox, oy = nx * 0.3, ny * 0.3
                wx, wy = nx * 0.05, ny * 0.05
                ring = [(px + ox + hx + wx, py + oy + hy + wy), (px + ox - hx + wx, py + oy - hy + wy),
                        (px + ox - hx - wx, py + oy - hy - wy), (px + ox + hx - wx, py + oy + hy - wy)]
                area = sum(ring[i][0] * ring[(i + 1) % 4][1] - ring[(i + 1) % 4][0] * ring[i][1] for i in range(4))
                if area < 0:
                    ring.reverse()
                for i in range(4):
                    p, r = ring[i], ring[(i + 1) % 4]
                    b0 = len(verts)
                    verts += [(p[0], p[1], foot), (r[0], r[1], foot), (r[0], r[1], top), (p[0], p[1], top)]
                    faces.append((b0, b0 + 1, b0 + 2, b0 + 3))
                    uvs.append(((0.5, 0.2), (0.6, 0.2), (0.6, 0.8), (0.5, 0.8)))
                next_post += RAIL_POST_M
                n_post += 1
            batch.room(len(verts))
            batch.add(verts, faces, uvs)
            arc += seg
        total += arc
    batch.flush()
    for o in src:
        if not o.name.startswith("1WALL_GHOST"):
            o.name = "1WALL_GHOST_" + o.name
            for m in o.data.materials:
                if m is not None:
                    m.name = "1WALL_GHOST_" + m.name
    print(f"[bespoke] guardrail: {len(runs)} runs, {total:.0f} m of rail, {n_post} posts, along {sum(1 for _ in stations)} lips; "
          f"the lips stay as the collider, renamed 1WALL_GHOST_*")
    return {"runs": len(runs), "rail_m": round(total, 1), "posts": n_post}


def rails(col, spec, to_xy, ground, paved, bad):
    rows = []
    for k, r in enumerate(spec):
        line = [to_xy(p) for p in r["polyline_lonlat"]]
        prefix, hgt, mod, dep = RAIL_KINDS[r["kind"]]
        hgt = float(r.get("height_m", hgt))      # a measured height (ledger 0078: Pikes Peak's wall off the lidar)
        verts, faces, uvs = [], [], []
        arc_total, modules, left_out = 0.0, 0, 0
        for a, b in zip(line, line[1:]):
            seg = math.dist(a, b)
            ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
            nx, ny = -uy, ux
            cnt = int(seg // mod)
            for m in range(cnt):
                x0, y0 = a[0] + ux * m * mod, a[1] + uy * m * mod
                x1, y1 = x0 + ux * (mod - 0.02), y0 + uy * (mod - 0.02)
                ring = [(x0 - nx * dep / 2, y0 - ny * dep / 2), (x1 - nx * dep / 2, y1 - ny * dep / 2),
                        (x1 + nx * dep / 2, y1 + ny * dep / 2), (x0 + nx * dep / 2, y0 + ny * dep / 2)]
                ring = inward_ring(ring)
                gs = [down(ground, x, y) for x, y in ring]
                if any(g is None for g in gs) or any(down(paved, x, y) is not None for x, y in ring):
                    if r.get("auto"):
                        left_out += 1
                    else:
                        bad.append(f"rail {r['key']}: module {modules} at ({x0:.1f}, {y0:.1f}) is on a road or off the ground")
                    continue
                bot, top = min(gs) - BOTTOM_UNDER_M, max(gs) + hgt
                cell = modules % 2
                u0, u1 = cell * 0.5, cell * 0.5 + 0.5
                base = len(verts)
                verts += [(x, y, bot) for x, y in ring] + [(x, y, top) for x, y in ring]
                for i in range(4):
                    j = (i + 1) % 4
                    faces.append((base + i, base + j, base + 4 + j, base + 4 + i))
                    uvs.append(((u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)))
                faces.append((base + 4, base + 5, base + 6, base + 7))
                uvs.append(((u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)))
                modules += 1
            arc_total += seg
        if verts:
            make_mesh(col, f"{prefix}_{k}", verts, faces, uvs)
        rows.append({"key": r["key"], "kind": r["kind"], "modules": modules, "left_out": left_out, "length_m": round(arc_total, 1)})
        print(f"[bespoke] rail {r['key']}: {modules} {r['kind']} modules over {arc_total:.0f} m, {left_out} left out")
    return rows


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("scenery") or {}).get("bespoke")
    if not spec:
        print("[bespoke] no scenery.bespoke declared: nothing to stand")
        return
    origin = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    to_xy = lonlat_to_xy(origin)
    global GROUND, GROUND_FAR, PAVED, TRACK_EDGE, CONE_GROUND, WALLS, PREP_SEATS, ELEV0
    PREP_SEATS = bool(spec.get("prep_seats", False))
    ELEV0 = float(origin.get("elev_m", 0.0))
    names = spec.get("names") or {}
    GROUND = tuple(names.get("ground", GROUND))
    GROUND_FAR = tuple(names.get("far", GROUND_FAR)) + GROUND
    PAVED = tuple(names.get("paved", PAVED))
    TRACK_EDGE = tuple(names.get("track_edge", TRACK_EDGE))
    CONE_GROUND = tuple(names.get("cone_ground", CONE_GROUND))
    WALLS = tuple(names.get("walls", WALLS))
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ac_before = sorted(o.name for o in bpy.data.objects if o.name.startswith("AC_"))
    col = ensure_collection()
    ground = bvh(GROUND)[0]
    paved = bvh(PAVED)[0]
    walls = bvh(WALLS)[0]
    print(f"[bespoke] scene names: ground {GROUND}, far {GROUND_FAR}, paved {PAVED}, walls {WALLS}; "
          f"ground {'found' if ground else 'NOT FOUND'}, paved {'found' if paved else 'NOT FOUND'}")
    bad, report = [], {}
    report["buildings"] = [r for r in (building(col, b, to_xy, ground, paved, walls, bad) for b in spec.get("buildings", [])) if r]
    if spec.get("cones"):
        report["cones"] = cones(col, spec["cones"], proj, bad)
    if spec.get("scrub"):
        report["scrub"] = scrub(col, spec["scrub"], to_xy, ground, paved, walls, bad)
    far = bvh(GROUND_FAR)[0]
    if spec.get("rails"):
        report["rails"] = rails(col, spec["rails"], to_xy, ground, paved, bad)
    if spec.get("blocks"):
        report["blocks"] = blocks(col, spec["blocks"], proj, to_xy, far, ground, paved, walls, bad)
    if spec.get("pads"):
        report["pads"] = pads(col, spec["pads"], to_xy, far, paved, bad)
    if spec.get("cards"):
        quads = [[to_xy(c) for c in p["quad_lonlat"]] for p in spec.get("pads", []) if "quad_lonlat" in p]
        for p in spec.get("pads", []):                 # a strip pad's quads (ledger 0078 round 5)
            if "strip_lonlat" in p:
                si, so = p["strip_lonlat"]["inner"], p["strip_lonlat"]["outer"]
                quads += [[to_xy(si[i]), to_xy(si[i + 1]), to_xy(so[i + 1]), to_xy(so[i])] for i in range(len(si) - 1)]
        report["cards"] = cards(col, spec["cards"], proj, to_xy, far, paved, walls, bad, quads)
    if spec.get("guardrail"):
        report["guardrail"] = guardrail(col, spec["guardrail"], proj, bad)
    if sorted(o.name for o in bpy.data.objects if o.name.startswith("AC_")) != ac_before:
        bad.append("an AC_* node changed")
    if bad:
        raise SystemExit("[bespoke] self-check FAILED (loop.blend not saved): " + "; ".join(bad))
    (proj / "data" / "bespoke.report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    # the set-in decks (ledger 0083 pass 4b) declared for tools/house_seat_check.py, which judges each against its own
    # measured deck instead of its uphill ground; no set-in deck = no file (and a stale one removed)
    si = [{"key": r["key"], **r["set_in"]} for r in report.get("blocks", []) if r.get("set_in")]
    sp = proj / "data" / "house_seat.set_in.json"
    if si:
        sp.write_text(json.dumps({"_doc": "ledger 0083 pass 4b: decks set into their slope by tools/author_bespoke_blend.py "
                                          "(rows with set_in); Blender frame (x east, y north, z up)", "decks": si}, indent=1),
                      encoding="utf-8")
    elif sp.exists():
        sp.unlink()
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[bespoke] saved loop.blend: {len(col.objects)} objects in {COLLECTION}; {len(report['buildings'])} buildings, "
          f"{len(report.get('blocks', []))} blocks, {len(report.get('cones', []))} cones, {len(report.get('scrub', []))} scrub clumps")


if __name__ == "__main__":
    main()

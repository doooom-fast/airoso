"""BVH helpers over loop.blend's built surfaces, shared by tools/author_signs_blend.py (places on
the built mesh) and tools/verify_signs.py --blend (measures the result independently). bpy only
— importable inside Blender 4.2, nowhere else.

The top-surface test: a point is PAVEMENT when the highest ROAD/1ROAD hit under it is at or above
the highest CURB/SIDEWALK/TERRAIN hit (- 2 cm); everything else is off-road. That is what the car
sees, and it is the only edge definition these tools trust (LAWS L5: never the data that placed it).

    load_bvhs()                -> (road_bvh, ground_bvh, road_names, ground_names)
    on_road(road, ground, x, z) -> bool, engine-frame (x = E, z = N)
    polar_clearance(road, ground, x, z, deg=5, step=0.25, reach=6.0)
        -> (metres to the nearest pavement in ANY direction, bearing deg) — a 5-degree polar scan
           at 0.25 m steps, bisected to ~1 cm on the first on-road sample; (reach, None) when
           nothing within reach
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

GROUND = ("CURB", "SIDEWALK", "TERRAIN", "1KERB", "1GRASS")
ROAD = ("ROAD", "1ROAD")
RAY_TOP = 4000.0
POLAR_DEG, POLAR_STEP, POLAR_REACH = 5, 0.25, 6.0


def world_tris(ob):
    mw = ob.matrix_world
    vs = [tuple(mw @ v.co) for v in ob.data.vertices]
    tris = []
    for poly in ob.data.polygons:
        idx = poly.vertices
        for k in range(1, len(idx) - 1):
            tris.append((vs[idx[0]], vs[idx[k]], vs[idx[k + 1]]))
    return tris


def bvh_of(tris):
    if not tris:
        return None
    return BVHTree.FromPolygons([v for t in tris for v in t], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))])


def load_bvhs(skip_prefixes=()):
    """ROAD vs GROUND BVHs over every mesh object of the open file (skip_prefixes: names to ignore,
    e.g. the SIGN* meshes themselves)"""
    ground_tris, road_tris, ground_names, road_names = [], [], [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        up = ob.name.upper()
        if skip_prefixes and up.startswith(tuple(skip_prefixes)):
            continue
        if up.startswith(ROAD):
            road_tris += world_tris(ob)
            road_names.append(ob.name)
        elif up.startswith(GROUND):
            ground_tris += world_tris(ob)
            ground_names.append(ob.name)
    return bvh_of(road_tris), bvh_of(ground_tris), road_names, ground_names


def top_hit(bvh, x, z):
    """highest surface height (engine y) under the engine-frame point (x, z); None if nothing"""
    if bvh is None:
        return None
    hit = bvh.ray_cast(Vector((x, z, RAY_TOP)), Vector((0.0, 0.0, -1.0)))
    return None if hit[0] is None else hit[0].z


def on_road(road, ground, x, z):
    """the top surface under (x, z) is pavement (a curb/walk hit above the road wins)"""
    r = top_hit(road, x, z)
    if r is None:
        return False
    g = top_hit(ground, x, z)
    return g is None or r >= g - 0.02


def polar_clearance(road, ground, x, z, deg=POLAR_DEG, step=POLAR_STEP, reach=POLAR_REACH):
    """metres from (x, z) to the nearest built pavement in any direction (see module doc)"""
    best = (reach, None)
    for a in range(0, 360, deg):
        th = math.radians(a)
        cx, sz = math.cos(th), math.sin(th)
        d = step
        # one sample PAST the running minimum: pavement first seen at d lies in (d - step, d], so
        # a direction is only cleared once its sample beyond best has been taken
        while d < best[0] + step:
            if on_road(road, ground, x + cx * d, z + sz * d):
                lo, hi = d - step, d
                for _ in range(10):
                    mid = (lo + hi) / 2
                    if on_road(road, ground, x + cx * mid, z + sz * mid):
                        hi = mid
                    else:
                        lo = mid
                if hi < best[0]:
                    best = (hi, a)
                break
            d += step
    return best

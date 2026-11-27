"""The raised median island's own shape, as one rule (pure: no bpy, no numpy).

tools/author_median_blend.py (the draft step that authors every island into loop.blend) and
tools/author_median_rebuild_blend.py (the author step that re-authors ONE island in a scene whose draft is never run
again; ledger 0099 round 3, item 1b) both build an island from these functions, so the rule exists once. Lifted out of
author_median_blend.py on 2026-11-23 line for line: tests/tools/test_median_island_rule.py runs the draft tool against
a stand-in bpy and holds what it hands to Blender to the checksums taken before the lift.

An island is a run of at least MIN_ISLAND_VERTS points of a line (the mainline, or a divided connector's island points)
whose band width is over 0. Per point k of the run [i, j): a curb ring of six vertices across the island, a deck pair
inside it, and on a run of BARRIER_MIN_M or more a box beam along the middle with a post every POST_EVERY_M. The island
tapers to NOSE_HALF over its first and last NOSE_VERTS points. Local frame x = east, y = up, z = north; every vertex
is returned in Blender's frame (x, z, y): `B`.

OFFSET ISLANDS (opt-in; data/median_bands.json `island_off_by_vertex` on the mainline, + = forward-left metres, the
same sign as a lap's island_off_by_vertex): an island whose centre stands off the line it is indexed on (Denver's
Colfax median, DOTI 100% design Aug 2024: 7.32 m off the north kerb, not in the street's middle). Every shape function
takes `off` (that list) and `ys` (the road's height under each centre, from the scene) as keyword arguments; both
absent = the centre is the line point itself, exactly as before, byte for byte."""
from __future__ import annotations

import math

LIFT = 0.10          # road ribbon rides +0.10 above the local y (build_loop_blend's lift)
CURB_H = 0.18
LIP_IN = 0.15        # curb top inward batter
DECK_INSET = 0.22
NOSE_HALF = 0.25     # island end tapers to this half-width
NOSE_VERTS = 3
MIN_ISLAND_VERTS = 6
BARRIER_MIN_M = 120.0
POST_EVERY_M = 8.0
BEAM = ((-0.12, 0.45), (-0.12, 0.75), (0.12, 0.75), (0.12, 0.45))        # the box beam's section: (lateral, over the curb top)
POST = ((-0.06, -0.06), (0.06, -0.06), (0.06, 0.06), (-0.06, 0.06))      # a post's plan corners; it stands POST_H tall
POST_H = 0.45


def B(p):
    """local (x, y_up, z_north) -> blender (x, z_north, y_up)"""
    return (p[0], p[2], p[1])


def tangent(pts, k):
    a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
    dx, dz = b[0] - a[0], b[2] - a[2]
    d = math.hypot(dx, dz) or 1.0
    return dx / d, dz / d


def segments(island_w):
    """[(i, j)]: the runs of points with a band, at least MIN_ISLAND_VERTS long (a shorter run is not built)"""
    segs, i, n = [], 0, len(island_w)
    while i < n:
        if island_w[i] <= 0:
            i += 1
            continue
        j = i
        while j < n and island_w[j] > 0:
            j += 1
        if j - i >= MIN_ISLAND_VERTS:
            segs.append((i, j))
        i = j
    return segs


def seg_length(pts, i, j):
    return sum(math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][2] - pts[k][2]) for k in range(i, j - 1))


def centre(pts, k, off=None, ys=None):
    """(x, y, z) of the island's centre at point k: the line point, moved off[k] along the line's left normal and set
    at ys[k] when either is given (OFFSET ISLANDS above); the line point itself otherwise"""
    p = pts[k]
    if off is None and ys is None:
        return p[0], p[1], p[2]
    o = float(off[k]) if off is not None else 0.0
    tx, tz = tangent(pts, k)
    return p[0] - tz * o, (float(ys[k]) if ys is not None else p[1]), p[2] + tx * o


def half_width(iw, i, j, k):
    """the island's half width at point k of the run [i, j): half the band, tapered to NOSE_HALF at both ends"""
    si, n = k - i, j - i
    half = iw[k] / 2.0
    if si < NOSE_VERTS:
        half = NOSE_HALF + (half - NOSE_HALF) * si / NOSE_VERTS
    if (n - 1 - si) < NOSE_VERTS:
        half = NOSE_HALF + (half - NOSE_HALF) * (n - 1 - si) / NOSE_VERTS
    return half


def ring(pts, iw, i, j, k, off=None, ys=None):
    """(the curb ring's six vertices: Lbase LtopO LtopI RtopI RtopO Rbase, the deck's two) at point k of the run [i, j)"""
    half = half_width(iw, i, j, k)
    tx, tz = tangent(pts, k)
    lx, lz = -tz, tx
    cx, cy, cz = centre(pts, k, off, ys)
    cy = cy + LIFT

    def P(off, dy):
        return B((cx + lx * off, cy + dy, cz + lz * off))

    curb = [P(-half, -0.02), P(-half + 0.04, CURB_H), P(-half + LIP_IN, CURB_H),
            P(half - LIP_IN, CURB_H), P(half - 0.04, CURB_H), P(half, -0.02)]
    di = max(0.05, half - DECK_INSET)
    return curb, [P(-di, CURB_H + 0.005), P(di, CURB_H + 0.005)]


def curb_span_faces(a):
    """the four quads between the ring whose first vertex is a and the next (bands 0-1 sideL, 1-2 lipL, 3-4 lipR, 4-5 sideR)"""
    b = a + 6
    return [(a + p, a + q, b + q, b + p) for (p, q) in ((0, 1), (1, 2), (3, 4), (4, 5))]


def curb_start_cap(a):
    return [(a + 0, a + 1, a + 2, a + 3), (a + 0, a + 3, a + 4, a + 5)]


def curb_end_cap(z):
    return [(z + 3, z + 2, z + 1, z + 0), (z + 5, z + 4, z + 3, z + 0)]


def deck_face(d):
    """the quad between the deck pair whose first vertex is d and the next"""
    return (d, d + 1, d + 3, d + 2)


def beam_points(i, j):
    """the points a run's beam and posts stand on: all but its two noses"""
    return list(range(i + NOSE_VERTS, j - NOSE_VERTS))


def beam_ring(pts, k, off=None, ys=None):
    tx, tz = tangent(pts, k)
    lx, lz = -tz, tx
    cx, cy, cz = centre(pts, k, off, ys)
    yb = cy + LIFT + CURB_H
    return [B((cx + lx * off, yb + dy, cz + lz * off)) for off, dy in BEAM]


def beam_span_faces(a):
    b = a + 4
    return [(a + p, a + q, b + q, b + p) for (p, q) in ((0, 1), (1, 2), (2, 3), (3, 0))]


def post_points(pts, bks):
    """the points of bks a post stands on: one every POST_EVERY_M along the road, counted from the beam's first point"""
    out, dist = [], 0.0
    for k in bks:
        dist += math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
        if dist < POST_EVERY_M:
            continue
        dist = 0.0
        out.append(k)
    return out


def post(pts, k, off=None, ys=None):
    """(eight vertices, the faces on them counted from 0) of the post at point k"""
    cx, cy, cz = centre(pts, k, off, ys)
    yb = cy + LIFT + CURB_H
    verts = []
    for (ox, oz) in POST:
        verts.append(B((cx + ox, yb, cz + oz)))
        verts.append(B((cx + ox, yb + POST_H, cz + oz)))
    return verts, [(p, q, q + 1, p + 1) for (p, q) in ((0, 2), (2, 4), (4, 6), (6, 0))]

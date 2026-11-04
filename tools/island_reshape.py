"""One raised island's curb and deck vertices exactly as tools/author_median_blend.py lays them — PURE (no bpy), so a
corrected island can be re-shaped in an authored loop.blend vertex for vertex (ledger 0054 Phase 2 step 4,
tools/reshape_island_blend.py).

author_median_blend.py builds every island from (its polyline points, its widths) alone: per station a 6-vertex curb ring
(Lbase, LtopO, LtopI, RtopI, RtopO, Rbase) across the island polyline's local normal, and two deck vertices; the 0.25 m nose
taper over the first / last three stations; runs of >= 6 stations. Those formulas are restated here — and the reshape tool
REFUSES unless every vertex this module computes from the OLD island data is found in the blend at that position: a drift
between the two copies cannot reshape anything silently. Only positions change: the same island runs (same nonzero
pattern) give the same vertex count and order, so every face and every other vertex of the blend stays as it is.

Frames: island points are engine (x = E, y = up, z = N); the blend is (x, z_north, y_up) — B().
"""
from __future__ import annotations

import math

LIFT = 0.10          # author_median_blend.LIFT
CURB_H = 0.18        # author_median_blend.CURB_H
LIP_IN = 0.15        # author_median_blend.LIP_IN
DECK_INSET = 0.22    # author_median_blend.DECK_INSET
NOSE_HALF = 0.25     # author_median_blend.NOSE_HALF
NOSE_VERTS = 3       # author_median_blend.NOSE_VERTS
MIN_RUN = 6          # author_median_blend._segments


def B(p):
    return (p[0], p[2], p[1])


def _tangent(pts, k):
    a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
    dx, dz = b[0] - a[0], b[2] - a[2]
    d = math.hypot(dx, dz) or 1.0
    return dx / d, dz / d


def segments(island_w):
    segs, i, n = [], 0, len(island_w)
    while i < n:
        if island_w[i] <= 0:
            i += 1
            continue
        j = i
        while j < n and island_w[j] > 0:
            j += 1
        if j - i >= MIN_RUN:
            segs.append((i, j))
        i = j
    return segs


def island_vertices(pts, iw):
    """{(segment i, j): {"curb": {k: [6 blend-frame points]}, "deck": {k: [2 blend-frame points]}}}"""
    out = {}
    for i, j in segments(iw):
        ks = list(range(i, j))
        curb, deck = {}, {}
        for si, k in enumerate(ks):
            half = iw[k] / 2.0
            if si < NOSE_VERTS:
                half = NOSE_HALF + (half - NOSE_HALF) * si / NOSE_VERTS
            if (len(ks) - 1 - si) < NOSE_VERTS:
                half = NOSE_HALF + (half - NOSE_HALF) * (len(ks) - 1 - si) / NOSE_VERTS
            tx, tz = _tangent(pts, k)
            lx, lz = -tz, tx
            cx, cy, cz = pts[k][0], pts[k][1] + LIFT, pts[k][2]

            def P(off, dy):
                return B((cx + lx * off, cy + dy, cz + lz * off))
            curb[k] = [P(-half, -0.02), P(-half + 0.04, CURB_H), P(-half + LIP_IN, CURB_H),
                       P(half - LIP_IN, CURB_H), P(half - 0.04, CURB_H), P(half, -0.02)]
            di = max(0.05, half - DECK_INSET)
            deck[k] = [P(-di, CURB_H + 0.005), P(di, CURB_H + 0.005)]
        out[(i, j)] = {"curb": curb, "deck": deck}
    return out


def moves(old_pts, old_iw, new_pts, new_iw, tol=1e-9, move_deck=True):
    """[(object, old blend point, new blend point)] for every island vertex that moves; ValueError when the two islands'
    runs differ (the topology would change: re-author instead).

    ``move_deck=False`` (tools/reshape_island_blend.py's default since ledger 0054 Phase 2 step 2f) moves the CURB only and
    leaves the deck (TERRAIN, -> 1GRASS) exactly as authored. The deck is ground UNDER the road slab: the prep pins every
    deck vertex to the road - 0.02 (measured on v4's prepped Princess View: 28 of 28), so the island's visible top is the
    slab, whatever the deck's width. But the deck is terrain the prep READS. Moving it carries deck edges across the
    prep's CORRIDOR_EDGE_M (4 more corridor splits on Princess View) and moves deck face centres across the 1GRASS tile
    cuts, which are median bisections of every face centre. Either way every later cut moves, and the per-tile thinning
    re-meshes ground kilometres away (the 0.20.2 road kn5: 16 of 20 tiles)."""
    so, sn = segments(old_iw), segments(new_iw)
    if so != sn:
        raise ValueError(f"the island runs differ ({so} -> {sn}): its vertex count would change — re-author it instead")
    vo, vn = island_vertices(old_pts, old_iw), island_vertices(new_pts, new_iw)
    out = []
    for seg in so:
        for part, obj in (("curb", "CURB"), ("deck", "TERRAIN")):
            if part == "deck" and not move_deck:
                continue
            for k, ring in vo[seg][part].items():
                for a, b in zip(ring, vn[seg][part][k]):
                    if max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])) > tol:
                        out.append((obj, a, b, k))
    return out


def all_vertices(pts, iw):
    """[(object, blend point, station)] of the whole island (the presence check)"""
    out = []
    for seg, d in island_vertices(pts, iw).items():
        for part, obj in (("curb", "CURB"), ("deck", "TERRAIN")):
            for k, ring in d[part].items():
                out += [(obj, p, k) for p in ring]
    return out

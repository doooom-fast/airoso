"""A ground triangle clipped to a convex pad cell in plan, keeping the triangle's own plane (ledger 0081 round 2).

tools/seat_pads_blend.py lays each bespoke pad on the prepped ground: every ground triangle under a pad cell, cut to the
cell's outline (Sutherland-Hodgman against the cell's edges in x / y), each cut vertex's height on the triangle's plane.
So the pad keeps its measured outline and lies on the ground's own surface. Pure Python, tested without Blender.
"""
from __future__ import annotations


def _side(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def ccw(poly):
    s = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    return poly if s > 0 else poly[::-1]


def clip(tri, cell):
    """tri: three (x, y, z); cell: a convex polygon [(x, y), ...]. The part of tri inside cell, as (x, y, z) points in
    order (z linear along each cut edge, so on tri's plane); [] when they do not overlap."""
    out = [tuple(p) for p in tri]
    c = ccw([tuple(p[:2]) for p in cell])
    for i in range(len(c)):
        a, b = c[i], c[(i + 1) % len(c)]
        src, out = out, []
        if not src:
            break
        for j in range(len(src)):
            p, q = src[j], src[(j + 1) % len(src)]
            sp, sq = _side(a, b, p), _side(a, b, q)
            if sp >= 0:
                out.append(p)
            if (sp >= 0) != (sq >= 0):
                t = sp / (sp - sq)
                out.append(tuple(p[k] + (q[k] - p[k]) * t for k in range(3)))
    return out


def area2(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


FOLD_MAX_M = 0.01   # [invented] (ledger 0092 round 2) the most a rebuilt pad vertex is raised onto a fold of the ground


def lift_over_folds(verts, top, lift, tol=1e-3, cap=FOLD_MAX_M):
    """tools/seat_pads_blend.py's rebuilt pad vertices, raised where the prepped ground has a fold: two ground triangles
    over one (x, y) at heights mm apart (Milford 0.1.13's apron_9: the pad vertex on one, the other 1.8 mm higher, so the
    self-check read ground 58.2 mm under the pad, not 60). ``top(x, y, z)`` is the highest ground the self-check's own ray
    finds there (None: none). A vertex is raised ONLY where that self-check would fail (ground more than ``tol`` over
    z - lift), and only by up to ``cap``: the vertex then stands ``lift`` over the higher piece. A pad that passed before is
    unchanged, vertex for vertex; ground more than ``cap`` over is left as it is, so the self-check still stops the build.
    Returns (verts, raised, worst_raise_m)."""
    out, raised, worst = [], 0, 0.0
    for x, y, z in verts:
        g = top(x, y, z)
        if g is not None and g > z - lift + tol and g + lift - z <= cap:
            worst = max(worst, g + lift - z)
            z = g + lift
            raised += 1
        out.append((x, y, z))
    return out, raised, worst

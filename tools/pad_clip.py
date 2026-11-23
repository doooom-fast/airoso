"""A ground triangle clipped to a convex pad cell in plan, keeping the triangle's own plane (ledger 0081 round 2).

tools/seat_pads_blend.py lays each bespoke pad on the prepped ground: every ground triangle under a pad cell, cut to the
cell's outline (Sutherland-Hodgman against the cell's edges in x / y), each cut vertex's height on the triangle's plane.
So the pad keeps its measured outline and lies on the ground's own surface. Pure Python, tested without Blender.
"""
from __future__ import annotations

import math


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


def area_normals(verts, faces):
    """(ledger 0100 item 6, opt-in pads_shade "smooth") one unit normal per vertex: the AREA-weighted mean of the normals of
    the faces meeting there (sum of each face's cross product, which is twice its area along its normal). Blender's own
    smooth normals weight by corner ANGLE, so a clipping sliver (a ground fold's 1-2 mm2 triangle standing 60-90 deg) with a
    near-180 deg corner tipped its vertex 47-75 deg on Milford 0.1.5's ride pad; by area it weighs nothing. A vertex no face
    reaches (none in a rebuilt pad) gets straight up. faces: vertex-index tuples, counter-clockwise from above."""
    acc = [[0.0, 0.0, 0.0] for _ in verts]
    for f in faces:
        p0 = verts[f[0]]
        for k in range(1, len(f) - 1):
            p1, p2 = verts[f[k]], verts[f[k + 1]]
            ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
            vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
            cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            for i in (f[0], f[k], f[k + 1]):
                a = acc[i]
                a[0] += cx
                a[1] += cy
                a[2] += cz
    out = []
    for a in acc:
        n = (a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) ** 0.5
        out.append((0.0, 0.0, 1.0) if n == 0 else (a[0] / n, a[1] / n, a[2] / n))
    return out


def crease_normals(verts, faces, crease_deg):
    """(ledger 0100 round 1b, opt-in scenery.bespoke.pads_shade_crease_deg) one normal per face CORNER: at each vertex the faces
    meeting there are grouped so that every two faces in a group have normals within ``crease_deg`` of each other, and a
    group's corners share the AREA-weighted mean of its faces' normals (pad_clip.area_normals' weighting). Faces further
    apart than that keep apart: the corner is split, so a shared normal never averages across a crease of the ground (the PC's
    0.1.14 pads, shared at every vertex, read up to 117 deg off a face on apron_16). Mean of unit normals pairwise within
    crease_deg: it stands within crease_deg of each (about half of it where the group is balanced). Faces are taken largest
    first, each into the first group it fits (deterministic); a zero-area face takes its vertex's first group and weighs
    nothing. crease_deg >= 180 is area_normals exactly. Returns a list (per face) of tuples (per corner) of unit normals."""
    cos_c = math.cos(math.radians(min(float(crease_deg), 180.0)))
    fn, fa = [], []
    for f in faces:
        sx = sy = sz = 0.0
        p0 = verts[f[0]]
        for k in range(1, len(f) - 1):
            p1, p2 = verts[f[k]], verts[f[k + 1]]
            ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
            vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
            sx += uy * vz - uz * vy
            sy += uz * vx - ux * vz
            sz += ux * vy - uy * vx
        n = math.sqrt(sx * sx + sy * sy + sz * sz)
        fa.append(n)
        fn.append((sx / n, sy / n, sz / n) if n > 0 else None)
    at = [[] for _ in verts]
    for i, f in enumerate(faces):
        for v in f:
            at[v].append(i)
    group_n = {}                                  # (vertex, face) -> the group's normal
    for v, inc in enumerate(at):
        groups = []                               # [members, (sx, sy, sz)]
        for i in sorted(inc, key=lambda i: (-fa[i], i)):
            if fn[i] is None:
                continue
            for g in groups:
                if all(fn[i][0] * fn[j][0] + fn[i][1] * fn[j][1] + fn[i][2] * fn[j][2] >= cos_c for j in g[0]):
                    g[0].append(i)
                    g[1] = (g[1][0] + fa[i] * fn[i][0], g[1][1] + fa[i] * fn[i][1], g[1][2] + fa[i] * fn[i][2])
                    break
            else:
                groups.append([[i], (fa[i] * fn[i][0], fa[i] * fn[i][1], fa[i] * fn[i][2])])
        for members, s in groups:
            n = math.sqrt(s[0] * s[0] + s[1] * s[1] + s[2] * s[2])
            u = (s[0] / n, s[1] / n, s[2] / n) if n > 0 else (0.0, 0.0, 1.0)
            for i in members:
                group_n[(v, i)] = u
        first = group_n.get((v, groups[0][0][0])) if groups else (0.0, 0.0, 1.0)
        for i in inc:
            if fn[i] is None:
                group_n[(v, i)] = first
    return [tuple(group_n[(v, i)] for v in f) for i, f in enumerate(faces)]

"""Mend the terrain's VERTICAL SLIVERS: triangles flat in plan whose three corners lie on one straight line with a
T-vertex between the other two (ledger 0054 P3 repair round 1, the view lens's see-through slit on Jackson north's cut,
D s ~1375, 24 m past the curb).

HOW ONE IS MADE. The seat (tools/seat_terrain_blend.py: the verge finer than the road) and the ground release halve
terrain edges; a coarser face beside a halved edge keeps the new vertex m on its straight edge a-b as an n-gon corner.
Blender's BEAUTY triangulation of that n-gon may cut the ear (a, m, b): a triangle with no plan area. While m sits on
the line a-b it is invisible; once any pass moves m off it (the seat seats the verge, the release takes 3DEP) the face
across a-b still runs straight from a to b, the faces on the other side run through m, and the ear stands up as a
vertical fin filling the crack between them — one-sided, so from half the directions AC culls it and the sky shows
through (the 0.125 m T-junction mismatch of the slit; 1,972 such faces within 80 m of the north roads, held v0.18.1 had
3 there, the whole OBJ 2,700 against 730).

THE MEND (no vertex moves, none is added): the edge a-b is rotated inside the quad (a, m, b, c) that the sliver and the
face across a-b make, so the surface runs a -> m -> b on both sides — (a, m, c) and (m, b, c); a sliver on the mesh's
open edge (nothing across a-b) is deleted (its two short edges become the open edge through m). Repeated until none is
left or MAX_ROUNDS.

The geometry test is pure (collinear_middle) so the suite runs it without Blender; mend_vertical_slivers takes a bmesh.
"""
from __future__ import annotations

import math

LINE_TOL_M = 1e-3     # [invented] a corner this close (in plan) to the line through the other two lies ON it
END_FRAC = 1e-3       # ...strictly between them: its projection beyond this share of the edge from either end
MAX_ROUNDS = 6        # [invented] rotation rounds (a rotated quad's neighbour can be a sliver of its own)


def collinear_middle(pts):
    """pts: three (x, y) plan points. The index of the one lying on the segment between the other two (within
    LINE_TOL_M of the line, strictly inside it), or None (a real triangle, or two corners on one plan point — a seat
    curtain's vertical edge, which is not this defect)"""
    for k in range(3):
        a, m, b = pts[(k + 1) % 3], pts[k], pts[(k + 2) % 3]
        ex, ey = b[0] - a[0], b[1] - a[1]
        L = math.hypot(ex, ey)
        if L < 10 * LINE_TOL_M:
            continue
        t = ((m[0] - a[0]) * ex + (m[1] - a[1]) * ey) / (L * L)
        d = abs((m[0] - a[0]) * ey - (m[1] - a[1]) * ex) / L
        if END_FRAC < t < 1.0 - END_FRAC and d <= LINE_TOL_M and min(t, 1.0 - t) * L > LINE_TOL_M:
            return k
    return None


def mend_vertical_slivers(bm, faces=None):
    """rotate (or, on the open edge, delete) every vertical sliver among `faces` (default: every triangle of bm);
    returns {"rotated": n, "deleted": n, "left": n}. Batched: one rotate_edges / delete call per round over edges that
    share no face (a bmesh operator walks the whole mesh, so one call per sliver would take minutes on the terrain)"""
    import bmesh
    rot = dele = 0
    todo = None if faces is None else {f for f in faces if f.is_valid}
    for _round in range(MAX_ROUNDS):
        cand = [f for f in (bm.faces if todo is None else todo) if f.is_valid and len(f.verts) == 3]
        rot_e, del_f, del_e, used, again = [], [], [], set(), set()
        for f in cand:
            vs = list(f.verts)
            k = collinear_middle([(v.co.x, v.co.y) for v in vs])
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
                    del_f.append(f)
                    del_e.append(e)
                continue
            if len(others) != 1 or len(others[0].verts) != 3:
                continue
            if f in used or others[0] in used:
                again.add(f)              # its neighbour is rotated this round: next round
                continue
            used.update((f, others[0]))
            rot_e.append(e)
        if not rot_e and not del_f:
            break
        touched = set(again)
        if rot_e:
            res = bmesh.ops.rotate_edges(bm, edges=rot_e, use_ccw=False)
            got = res.get("edges") or []
            rot += len(got)
            for ne in got:
                for g in ne.link_faces:
                    touched.add(g)
                    for v in g.verts:
                        touched.update(v.link_faces)
        if del_f:
            for f in del_f:
                for v in f.verts:
                    touched.update(g for g in v.link_faces if g is not f)
            bmesh.ops.delete(bm, geom=del_f, context="FACES_ONLY")
            loose = [e for e in del_e if e.is_valid and not e.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="EDGES")
            dele += len(del_f)
        todo = {g for g in touched if g.is_valid}
        if not todo:
            break
    # the few a rotation refuses (the new edge m-c already exists: the face across a-b is part of a fan through m):
    # rebuilt by hand — the face across a-b re-made as the quad with m inserted on its edge a-b, cut at m-c, the sliver
    # deleted
    rebuilt = 0
    for _pass in range(3):              # a fan of several T-vertices on one line: one per pass
        n_before = rebuilt
        for f in [f for f in bm.faces if len(f.verts) == 3]:
            if not f.is_valid:
                continue
            vs = list(f.verts)
            k = collinear_middle([(v.co.x, v.co.y) for v in vs])
            if k is None:
                continue
            m = vs[k]
            e = next((e for e in f.edges if m not in e.verts), None)
            others = [g for g in e.link_faces if g is not f] if e is not None else []
            if len(others) != 1 or len(others[0].verts) != 3:
                continue
            g = others[0]
            loop = [l.vert for l in g.loops]
            if m in loop:                 # the two faces share all three corners (back to back): not this defect
                continue
            a, b = e.verts
            i = next(j for j in range(3) if {loop[j], loop[(j + 1) % 3]} == {a, b})
            quad = loop[:i + 1] + [m] + loop[i + 1:]
            c = next(v for v in loop if v not in (a, b))
            mat, smooth = g.material_index, g.smooth
            if bm.faces.get(quad) is not None:
                continue
            bmesh.ops.delete(bm, geom=[f, g], context="FACES_ONLY")
            nf = bm.faces.new(quad)
            nf.material_index, nf.smooth = mat, smooth
            bmesh.utils.face_split(nf, m, c)
            if e.is_valid and not e.link_faces:
                bmesh.ops.delete(bm, geom=[e], context="EDGES")
            rebuilt += 1
        if rebuilt == n_before:
            break
    left = sum(1 for f in bm.faces if len(f.verts) == 3
               and collinear_middle([(v.co.x, v.co.y) for v in f.verts]) is not None)
    return {"rotated": rot, "deleted": dele, "rebuilt": rebuilt, "left": left}

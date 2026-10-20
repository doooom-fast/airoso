"""Error-bounded thinning of a built terrain triangulation — ledger 0054 P3 repair round 3 (the road kn5's size).

WHY. The north roads' refinements (the seat's halving under every welded approach and the host lanes, the release
zones' 2.5 / 1 m facets, the prep's corridor subdivision and the kept-cell refinement) left the physical ground with
far more vertices than its surface needs: on the r2run2 build 1GRASS was 941,699 vertices (55 % of a 122.6 MB road kn5;
v0.18.1 355k), and 268k of the 555k within 20 m of a pavement were coplanar with their neighbours to 2 mm. Each pass
halves edges so the NEXT pass has vertices to move; most of the vertices it made were never moved.

WHAT (pure Python, no bpy — tools/thin_terrain_blend.py feeds it each 1GRASS tile of the prepped scene). Greedy
HALF-EDGE COLLAPSE: a vertex v is merged into one of its neighbours u — no vertex ever moves and none is ever made, so
every vertex that ships is one the chain placed (3DEP / the graded or released ground, LAWS L2 / L3: no reshaping) —
only where the new surface stays within the vertex's own vertical tolerance of the ORIGINAL surface, everywhere:

  * the deviation is measured EXACTLY over the collapse's star: the new and old surfaces are both linear on the overlay
    of the two triangulations, so their difference peaks at the overlay's vertices — v itself and every crossing of an
    old spoke (v-w) with a new edge (u-w) — and those are all evaluated;
  * deviations ACCUMULATE: every triangle carries the interval [lo, hi] of (its surface - the original surface) over
    its area; a collapse's new triangles carry [min lo + min D, max hi + max D] over the star, and a collapse is taken
    only while that interval sits inside [-tol_dn, +tol_up] of the strictest vertex in the star;
  * never a fold: every new triangle keeps the star's orientation in plan, is no thinner than ASPECT of its longest
    edge, no steeper than the steepest triangle it replaces, has no edge longer than the caller's cap; the link condition holds (no non-manifold edge); a boundary or non-manifold vertex (a tile seam, the
    far ring's seam, a hole) and every vertex of a near-vertical triangle stays;
  * the caller may forbid any new triangle (``forbid``) and lock any vertex (``locked``).

Cheapest collapse first (a heap; a vertex is re-evaluated whenever its star changes).

    python tools/terrain_thin.py worker <in.json> <out.json>     (one tile; tools/thin_terrain_blend.py runs these)
"""
from __future__ import annotations

import heapq
import json
import math
import sys

ASPECT = 0.02        # [invented] a new triangle's plan area x 2 is at least this x its longest edge squared (height >= 2 %
#                      of its base: ~1.1 deg) — no needles
NZ_LOCK = 0.25       # [invented] every vertex of a triangle whose normal's vertical component is under this (a riser, a
#                      sliver standing up) stays where the chain put it
NZ_SLACK = 0.02      # [invented] a new triangle may be at most this much steeper (normal z) than the steepest it replaces
MIN_AREA2 = 1e-6     # [invented] plan area x 2 (m2) under which a new triangle is degenerate
BARY_EPS = 1e-9
NZ_FINE = 0.84       # [invented] a triangle with its normal's vertical component under this is steeper than 0.65 m per
#                      metre — near tools/rib_check.py's riser slope (JOG_SLOPE 0.7): a star with one keeps fine triangles
HALF_CELL_EX = 0.25  # [invented] tools/rib_check.py's cross-grain measure reports folds from 0.5 m (AMPS), gates them from
#                      1 m (FOLD_M): a new plain cell may lean this little across the grain at most


def _ring(v, T, vt):
    """the closed, ordered ring of v's neighbours (each star triangle (v, a, b) as the directed edge a -> b), or None
    when v is on a boundary or non-manifold"""
    nxt = {}
    for t in vt[v]:
        a, b, c = T[t]
        if a == v:
            q, r = b, c
        elif b == v:
            q, r = c, a
        else:
            q, r = a, b
        if q in nxt:
            return None
        nxt[q] = r
    if len(nxt) < 3:
        return None
    start = next(iter(nxt))
    ring = [start]
    cur = nxt[start]
    while cur != start:
        if cur not in nxt or len(ring) >= len(nxt):
            return None
        ring.append(cur)
        cur = nxt[cur]
    return ring if len(ring) == len(nxt) else None


def thin(X, Y, Z, tris, tol_up, tol_dn, max_edge, locked, forbid=None, aspect=ASPECT, nz_lock=NZ_LOCK, fine_cap=None,
         keys=None):
    """Thin the triangulation (X, Y, Z: vertex coordinates, Z up; ``tris``: index triples) in place of a copy.
    ``tol_up`` / ``tol_dn`` [m] per vertex: how far the surface may ever rise / fall over the triangles around it (each
    triangle keeps the strictest tolerance of every vertex it has covered);
    ``max_edge`` [m] per vertex: the longest new edge a star holding it may get; ``locked`` per vertex; ``forbid(a, b,
    c)`` -> True refuses a new triangle. ``fine_cap`` [m] per vertex (0 = none): where a star holding it has a triangle,
    old or new, steeper than NZ_FINE, no new edge is longer than this (a riser stays in fine triangles). ``keys``: per
    vertex its lattice node (I, J) or None — a new triangle that is half of a plain lattice cell is refused when its
    diagonal joins the two corners that differ more in height than the cell's other two by HALF_CELL_EX (a cross-grain
    fold). Returns (alive vertex flags, the new triangle list, a stats dict)."""
    n = len(X)
    T = [list(t) for t in tris]
    nt = len(T)
    alive_t = [True] * nt
    lo = [0.0] * nt
    hi = [0.0] * nt
    vt = [[] for _ in range(n)]
    lock = list(locked)
    sgn_votes = 0
    nz_t = [1.0] * nt
    # every triangle carries the strictest tolerance of every vertex it has ever covered (a removed vertex's point lies
    # in some triangle for good: a later collapse over it may not loosen what that point was allowed)
    tu_t = [0.0] * nt
    td_t = [0.0] * nt
    for i, (a, b, c) in enumerate(T):
        vt[a].append(i); vt[b].append(i); vt[c].append(i)
        tu_t[i] = min(tol_up[a], tol_up[b], tol_up[c])
        td_t[i] = min(tol_dn[a], tol_dn[b], tol_dn[c])
        ax, ay, az = X[b] - X[a], Y[b] - Y[a], Z[b] - Z[a]
        bx, by, bz = X[c] - X[a], Y[c] - Y[a], Z[c] - Z[a]
        cz = ax * by - ay * bx
        cx = ay * bz - az * by
        cy = az * bx - ax * bz
        L = math.sqrt(cx * cx + cy * cy + cz * cz)
        nz_t[i] = abs(cz) / L if L > 0 else 0.0
        sgn_votes += 1 if cz > 0 else -1
    sgn = 1.0 if sgn_votes >= 0 else -1.0
    n_lock_steep = n_lock_flip = 0
    for i, (a, b, c) in enumerate(T):
        cz = (X[b] - X[a]) * (Y[c] - Y[a]) - (Y[b] - Y[a]) * (X[c] - X[a])
        if nz_t[i] < nz_lock:
            for w in (a, b, c):
                if not lock[w]:
                    lock[w] = True; n_lock_steep += 1
        elif cz * sgn <= MIN_AREA2:
            for w in (a, b, c):
                if not lock[w]:
                    lock[w] = True; n_lock_flip += 1
    dead = [False] * n
    ver = [0] * n
    node = {}
    if keys is not None:
        for i, k in enumerate(keys):
            if k is not None:
                node.setdefault(tuple(k), i)

    def cross_grain(u, a, b):
        ka, kb, kc = keys[u], keys[a], keys[b]
        if ka is None or kb is None or kc is None:
            return False
        for p_, q_, o_ in ((u, a, b), (a, b, u), (b, u, a)):
            kp, kq, ko = keys[p_], keys[q_], keys[o_]
            dI, dJ = abs(kp[0] - kq[0]), abs(kp[1] - kq[1])
            if dI and dI == dJ and ko[0] in (kp[0], kq[0]) and ko[1] in (kp[1], kq[1]) and tuple(ko) not in (tuple(kp), tuple(kq)):
                w4 = node.get((kp[0] + kq[0] - ko[0], kp[1] + kq[1] - ko[1]))
                if w4 is None or dead[w4]:
                    return False
                return abs(Z[p_] - Z[q_]) - abs(Z[o_] - Z[w4]) > HALF_CELL_EX
        return False

    def evaluate(v):
        if lock[v] or dead[v]:
            return None
        R = _ring(v, T, vt)
        if R is None:
            return None
        m = len(R)
        tu = min(tu_t[t] for t in vt[v]); td = min(td_t[t] for t in vt[v]); cap = max_edge[v]
        fc = fine_cap[v] if fine_cap is not None else 0.0
        for w in R:
            if max_edge[w] < cap: cap = max_edge[w]
            if fine_cap is not None and fine_cap[w] > 0.0 and (fc <= 0.0 or fine_cap[w] < fc): fc = fine_cap[w]
        if tu <= 0.0 and td <= 0.0:
            return None
        Lo = min(lo[t] for t in vt[v]); Hi = max(hi[t] for t in vt[v])
        if Lo < -td or Hi > tu:
            return None
        xv, yv, zv = X[v], Y[v], Z[v]
        cap2 = cap * cap
        nz_old = min(nz_t[t] for t in vt[v])
        nzmin = nz_old - NZ_SLACK
        fc2 = fc * fc if fc > 0.0 else None
        steep_old = fc2 is not None and nz_old < NZ_FINE
        best = None
        for k in range(m):
            u = R[k]
            xu, yu, zu = X[u], Y[u], Z[u]
            ok = True
            new = []
            for i in range(m):
                a = R[i]; b = R[(i + 1) % m]
                if a == u or b == u:
                    continue
                ax, ay, az = X[a] - xu, Y[a] - yu, Z[a] - zu
                bx, by, bz = X[b] - xu, Y[b] - yu, Z[b] - zu
                A2 = ax * by - ay * bx
                if A2 * sgn <= MIN_AREA2:
                    ok = False; break
                la = ax * ax + ay * ay; lb = bx * bx + by * by
                lab = (bx - ax) ** 2 + (by - ay) ** 2
                if la > cap2 or lb > cap2:
                    ok = False; break
                if abs(A2) < aspect * max(la, lb, lab):
                    ok = False; break
                cx = ay * bz - az * by; cy = az * bx - ax * bz
                nzn = abs(A2) / math.sqrt(cx * cx + cy * cy + A2 * A2)
                if nzn < nzmin:
                    ok = False; break
                if fc2 is not None and (steep_old or nzn < NZ_FINE) and (la > fc2 or lb > fc2):
                    ok = False; break
                if keys is not None and cross_grain(u, a, b):
                    ok = False; break
                if forbid is not None and forbid(u, a, b):
                    ok = False; break
                new.append((a, b, A2))
            if not ok or not new:
                continue
            # link condition: u and v share exactly the two ring neighbours of u
            nb_u = set()
            for t in vt[u]:
                nb_u.update(T[t])
            shared = nb_u.intersection(R)
            shared.discard(u)
            if shared != {R[k - 1], R[(k + 1) % m]}:
                continue
            # the deviation at v
            Dv = None
            for a, b, A2 in new:
                wa = ((xv - xu) * (Y[b] - yu) - (yv - yu) * (X[b] - xu)) / A2
                wb = ((X[a] - xu) * (yv - yu) - (Y[a] - yu) * (xv - xu)) / A2
                wu = 1.0 - wa - wb
                if wa >= -BARY_EPS and wb >= -BARY_EPS and wu >= -BARY_EPS:
                    Dv = wu * zu + wa * Z[a] + wb * Z[b] - zv
                    break
            if Dv is None:
                continue
            Dmin = min(0.0, Dv); Dmax = max(0.0, Dv)
            if Lo + Dmin < -td or Hi + Dmax > tu:
                continue
            # every crossing of an old spoke v-w_i with a new edge u-w_j
            for j in range(m):
                if j == k or j == (k - 1) % m or j == (k + 1) % m:
                    continue
                wj = R[j]
                ex, ey, ez = X[wj] - xu, Y[wj] - yu, Z[wj] - zu
                for i in range(m):
                    if i == k or i == j:
                        continue
                    wi = R[i]
                    sx, sy = X[wi] - xv, Y[wi] - yv
                    den = sx * ey - sy * ex
                    if abs(den) < 1e-12:
                        continue
                    qx, qy = xu - xv, yu - yv
                    t = (qx * ey - qy * ex) / den
                    s = (qx * sy - qy * sx) / den
                    if 1e-9 < t < 1.0 - 1e-9 and 1e-9 < s < 1.0 - 1e-9:
                        D = (zu + s * ez) - (zv + t * (Z[wi] - zv))
                        if D < Dmin: Dmin = D
                        elif D > Dmax: Dmax = D
            nlo, nhi = Lo + Dmin, Hi + Dmax
            if nlo < -td or nhi > tu:
                continue
            cost = max(Dmax, -Dmin)
            if best is None or cost < best[0]:
                best = (cost, u, nlo, nhi, tu, td)
        return best

    heap = []
    for v in range(n):
        r = evaluate(v)
        if r is not None:
            heap.append((r[0], v, ver[v], r[1], r[2], r[3], r[4], r[5]))
    heapq.heapify(heap)
    n_coll = 0
    while heap:
        cost, v, vv, u, nlo, nhi, ntu, ntd = heapq.heappop(heap)
        if dead[v] or vv != ver[v] or dead[u]:
            continue
        # collapse v -> u
        touched = set()
        for t in list(vt[v]):
            tri = T[t]
            if u in tri:
                alive_t[t] = False
                for w in tri:
                    if w != v:
                        vt[w].remove(t)
                        touched.add(w)
            else:
                tri[tri.index(v)] = u
                lo[t] = nlo; hi[t] = nhi
                tu_t[t] = ntu; td_t[t] = ntd
                a, b, c = tri
                ax, ay, az = X[b] - X[a], Y[b] - Y[a], Z[b] - Z[a]
                bx, by, bz = X[c] - X[a], Y[c] - Y[a], Z[c] - Z[a]
                cz = ax * by - ay * bx; cx = ay * bz - az * by; cy = az * bx - ax * bz
                L = math.sqrt(cx * cx + cy * cy + cz * cz)
                nz_t[t] = abs(cz) / L if L > 0 else 0.0
                vt[u].append(t)
                touched.update(tri)
        vt[v] = []
        dead[v] = True
        n_coll += 1
        for w in touched:
            if w == v or dead[w]:
                continue
            ver[w] += 1
            r = evaluate(w)
            if r is not None:
                heapq.heappush(heap, (r[0], w, ver[w], r[1], r[2], r[3], r[4], r[5]))
    out = [tuple(T[t]) for t in range(nt) if alive_t[t]]
    dev_lo = min((lo[t] for t in range(nt) if alive_t[t]), default=0.0)
    dev_hi = max((hi[t] for t in range(nt) if alive_t[t]), default=0.0)
    return ([not d for d in dead], out,
            {"vertices": n, "removed": n_coll, "triangles": [nt, len(out)], "locked_steep": n_lock_steep,
             "locked_flat_or_flipped": n_lock_flip, "deviation_bound_m": [round(dev_lo, 4), round(dev_hi, 4)]})


def surface_at(X, Y, Z, tris, px, py, cell=10.0):
    """Pure helper for the self-check: a function (x, y) -> [z of every triangle over the point]"""
    grid = {}
    for i, (a, b, c) in enumerate(tris):
        x0 = min(X[a], X[b], X[c]); x1 = max(X[a], X[b], X[c])
        y0 = min(Y[a], Y[b], Y[c]); y1 = max(Y[a], Y[b], Y[c])
        for gi in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
            for gj in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                grid.setdefault((gi, gj), []).append(i)

    def at(x, y):
        out = []
        for i in grid.get((int(math.floor(x / cell)), int(math.floor(y / cell))), ()):
            a, b, c = tris[i]
            d = (Y[b] - Y[c]) * (X[a] - X[c]) + (X[c] - X[b]) * (Y[a] - Y[c])
            if abs(d) < 1e-12:
                continue
            wa = ((Y[b] - Y[c]) * (x - X[c]) + (X[c] - X[b]) * (y - Y[c])) / d
            wb = ((Y[c] - Y[a]) * (x - X[c]) + (X[a] - X[c]) * (y - Y[c])) / d
            wc = 1.0 - wa - wb
            if wa >= -1e-7 and wb >= -1e-7 and wc >= -1e-7:
                out.append(wa * Z[a] + wb * Z[b] + wc * Z[c])
        return out
    return at


def _worker(inp, outp):
    d = json.loads(open(inp, encoding="utf-8").read())
    keys = d.get("lattice")
    alive, tris, st = thin(d["X"], d["Y"], d["Z"], d["tris"], d["tol_up"], d["tol_dn"], d["max_edge"], d["locked"],
                           fine_cap=d.get("fine_cap"), keys=[tuple(k) if k is not None else None for k in keys]
                           if keys is not None else None)
    open(outp, "w", encoding="utf-8").write(json.dumps({"alive": alive, "tris": tris, "stats": st}))


def is_half_cell(ka, kb, kc):
    """True when three lattice nodes are half of a plain square lattice cell (two of them on its diagonal, the third
    sharing one coordinate with each) — the triangle tools/rib_check.py's cross-grain measure reads"""
    for p, q, o in ((ka, kb, kc), (kb, kc, ka), (kc, ka, kb)):
        dI, dJ = abs(p[0] - q[0]), abs(p[1] - q[1])
        if dI and dI == dJ and o[0] in (p[0], q[0]) and o[1] in (p[1], q[1]) and tuple(o) not in (tuple(p), tuple(q)):
            return True
    return False


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "worker":
        _worker(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)

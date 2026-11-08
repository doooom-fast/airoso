"""A route line (a registered published map's, a sketch's) -> a guide through the measured pavement.

The route line only SELECTS which pavement; the guide only ORIENTS the cross-sections (edges.py measures). The guide is
the least-cost pixel path between waypoints taken every WAYPOINT_M along the route line, over a cost that falls toward
the pavement's middle (pieces.py's medial cost: 1 / (0.5 + clearance)^1.5, clearance capped at CAP_M; off the mask
allowed but dear, OFF_COST) and rises with the distance from the route line (x (1 + (d / corridor_m)^2)), so on a road
the guide runs down the road's middle whichever side of it the map was drawn, and on open pavement (a lot) it follows
the route line. Smoothed SMOOTH_M (sigma), resampled 0.5 m.

``mask: "between_lines"`` (a circuit painted on a lot): the free space is the pavement less its painted lines, so the
middle is the middle between the lines.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from . import geom

WAYPOINT_M = 25.0
CAP_M = 12.0
OFF_COST = 3.0
SMOOTH_M = 3.0
MARGIN_M = 30.0


def free_mask(ch, pave_mask, kind="pave"):
    if kind == "between_lines":
        b = ch["edge_band"] if "edge_band" in ch else ch["line"]
        return ~ndimage.binary_dilation(b > 0.5, iterations=1)
    return pave_mask


def _graph(cost):
    H, W = cost.shape
    idx = np.arange(H * W).reshape(H, W)
    rows, cols, vals = [], [], []
    c = cost.ravel()
    for dy, dx in [(0, 1), (1, 0), (1, 1), (1, -1)]:
        ys, ye = slice(0, H - dy), slice(dy, H)
        if dx >= 0:
            xs, xe = slice(0, W - dx), slice(dx, W)
        else:
            xs, xe = slice(-dx, W), slice(0, W + dx)
        a = idx[ys, xs].ravel()
        b = idx[ye, xe].ravel()
        w = 0.5 * (c[a] + c[b]) * (1.4142 if dx and dy else 1.0)
        rows += [a, b]
        cols += [b, a]
        vals += [w, w]
    return csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(H * W, H * W))


def guide(ortho, free, line_en, closed: bool, corridor_m: float = 8.0, waypoint_m: float = WAYPOINT_M):
    """The guide (ENU, 0.5 m) for a route line (ENU). Returns (guide, info)."""
    gsd = float(np.mean(ortho.gsd))
    Lr = geom.resample(np.asarray(line_en, float), 1.0, closed=closed)
    px, py = ortho.en_to_px(Lr[:, 0], Lr[:, 1])
    nwp = max(3, int(round((geom.closed_len(Lr) if closed else geom.cumlen(Lr)[-1]) / waypoint_m)))
    wi = np.linspace(0, len(Lr) - (0 if closed else 1), nwp + (0 if closed else 1), endpoint=not closed).astype(int) % len(Lr)
    pairs = list(zip(wi, np.r_[wi[1:], wi[:1]])) if closed else list(zip(wi[:-1], wi[1:]))
    margin = MARGIN_M / gsd
    cap = CAP_M / gsd
    path_px = []
    for a, b in pairs:
        seg = np.arange(a, b + 1) if b >= a else np.r_[np.arange(a, len(Lr)), np.arange(0, b + 1)]
        x0 = int(max(0, np.floor(px[seg].min() - margin)))
        x1 = int(min(ortho.W - 1, np.ceil(px[seg].max() + margin)))
        y0 = int(max(0, np.floor(py[seg].min() - margin)))
        y1 = int(min(ortho.H - 1, np.ceil(py[seg].max() + margin)))
        sub = free[y0:y1 + 1, x0:x1 + 1]
        dt = ndimage.distance_transform_edt(sub)
        base = np.where(sub, 1.0 / (0.5 + np.minimum(dt, cap)) ** 1.5, OFF_COST)
        lm = np.ones(sub.shape, bool)
        sx = np.clip(np.rint(px[seg] - x0).astype(int), 0, sub.shape[1] - 1)
        sy = np.clip(np.rint(py[seg] - y0).astype(int), 0, sub.shape[0] - 1)
        lm[sy, sx] = False
        dl = ndimage.distance_transform_edt(lm) * gsd
        cost = base * (1 + (dl / corridor_m) ** 2)
        G = _graph(cost)
        W_ = sub.shape[1]

        def snap(i):
            x, y = int(round(px[i] - x0)), int(round(py[i] - y0))
            r = max(2, int(round(4.0 / gsd)))
            ya, yb, xa, xb = max(0, y - r), min(sub.shape[0], y + r + 1), max(0, x - r), min(sub.shape[1], x + r + 1)
            win = cost[ya:yb, xa:xb]
            j = np.unravel_index(np.argmin(win), win.shape)
            return (ya + j[0]) * W_ + (xa + j[1])
        sa, sb = snap(a), snap(b)
        _, pred = dijkstra(G, indices=sa, return_predecessors=True)
        q = [sb]
        while q[-1] != sa:
            p = pred[q[-1]]
            if p < 0:
                raise SystemExit("[aerial-engine] no path between two route waypoints (the window is cut off)")
            q.append(p)
        q = np.array(q[::-1])
        pp = np.c_[q % W_ + x0, q // W_ + y0].astype(float)
        path_px.append(pp if not path_px else pp[1:])
    pp = np.vstack(path_px)
    e, n = ortho.px_to_en(pp[:, 0], pp[:, 1])
    P = geom.resample(np.c_[e, n], 0.25, closed=closed)
    P = geom.smooth(P, SMOOTH_M, 0.25, closed=closed)
    P = geom.resample(P, 0.5, closed=closed)
    tree_d = _dist_to(P, Lr)
    info = {"waypoints": int(len(wi)), "corridor_m": corridor_m,
            "guide_to_route_line_m": geom.pct(tree_d, 2),
            "length_m": round(float(geom.closed_len(P) if closed else geom.cumlen(P)[-1]), 1)}
    return P, info


def _dist_to(P, Q):
    from scipy.spatial import cKDTree
    return cKDTree(Q).query(P)[0]


def medial_points(ortho, free, box_en=None, min_clear_m=1.5):
    """The free mask's distance-transform ridge (3 x 3 local maxima with clearance >= min_clear_m), as ENU points: a
    reference for re-fitting a schematic line that strays off the pavement."""
    gsd = float(np.mean(ortho.gsd))
    dt = ndimage.distance_transform_edt(free)
    ridge = (dt >= ndimage.maximum_filter(dt, size=3)) & (dt >= min_clear_m / gsd) & free
    y, x = np.nonzero(ridge)
    e, n = ortho.px_to_en(x.astype(float), y.astype(float))
    pts = np.c_[e, n]
    if box_en is not None:
        (e0, n0), (e1, n1) = box_en
        pts = pts[(pts[:, 0] >= e0) & (pts[:, 0] <= e1) & (pts[:, 1] >= n0) & (pts[:, 1] <= n1)]
    return pts

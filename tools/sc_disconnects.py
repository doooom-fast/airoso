"""DIAGNOSTIC (not a gate), READ-ONLY: every place in Sand Creek where roads that should meet don't, on the BUILT road.

    python -I tools/sc_disconnects.py --project <dir> --obj <track.obj> --osm <osm.widths.cache.json> --out <dir>
                                [--cell 0.10] [--win 22] [--limit N]

Kevin, 2026-11-13, on Sand Creek 0.2.8: "San creek has many disconnected roads but drives well otherwise".
Every gate that looks at junctions (verify_mouths, verify_mouth_corners, mouth_survey) walks data/mouths.json only: a
place where two roads should meet but trim never cut a mouth is never looked at. This walks three lists of PLACES:

  MOUTH  every record of data/mouths.json (trim's cuts): the piece and its host must be one drivable sheet.
  END    every piece end of data/connectors.local.json that is NOT a mouth: a dead end. Classed against OpenStreetMap
         (the committed Overpass cache, nodes + names): OSM_JUNCTION (a real junction, degree >= 3, within END_JUNCTION_M
         of the end: the street should meet something here), OSM_CONTINUES (OSM's road runs on past the end), OSM_DEAD_END
         (OSM's way ends here too: real), SERVICE (it goes on only as a service road), and MAP_EDGE when it sits on the
         grid's clip box (tools/grid_connectors.py clips at the source heightfield's bbox minus terrain_inset_m).
  OSMJ   every OSM junction (degree >= 3 among public classes) inside the built grid that is not within MOUTH_NEAR_M of
         a mouth and not on a pad: two or more built roads there with no mouth (an unwelded crossing), or one built road
         and an OSM cross street that was never built.

and measures each one on the gate OBJ's triangles (L5: what ships), in a window raster (CELL m) of the topmost
drivable sheet (1ROAD*, 1KERB*) and the topmost ground (1GRASS*):

  CONNECTED  seeds on each road that should meet (on its centre line, SEED_M out from the place): one 8-connected
             drivable component, or not. Not: GAP_M = the shortest horizontal distance between the two components.
  STEP       inside JOIN_R_M of the place, between 4-neighbour drivable cells: the largest |dz| (a lip or a cut end
             standing over the next sheet), its position and its run length over STEP_M. Steps over LEVEL_M are level
             changes (a deck over a road), listed apart.
  EDGE       inside JOIN_R_M, every drivable cell beside a non-drivable one: drivable z - ground z beside it.
             HANG = the slab standing over grass (> 0, "floats"); WALL = grass standing over the drivable edge (< 0).
             Split by the drivable class at the edge: ROAD (a pavement edge with no strip: a bare slab edge) or KERB
             (the edge strip's lip).
  PATHS      straight wheel lines through the place (MOUTH: the piece's centre and both wheel lines from 5 m on the
             host to 12 m up the piece; END: the piece's centre line from 12 m back to END_PROBE_M past its end;
             OSMJ: each built road's centre line +-12 m): holes (no drivable sheet) and the largest rise over 0.10 m.

Names: the OSM `name` of the nearest named public way (within NAME_REACH_M), as tools/name_blades.py reads them.
Known items (ledger 0086 owed list, route.verify_mouth_corners_allowed, route.mouth_returns_skip) are tagged, not hidden.

Report bands, not gates. STEP_M 0.05 = scripts/ac/kn5_ground_check.ROAD_GAP_M [measured: the contact ceiling the
house uses]; FINE_M 0.10 = tools/mouth_survey.FINE_M (0050's fine step) [sampling]; LEVEL_M 1.0, GAP_REPORT_M 0.2,
END_JUNCTION_M 15, MOUTH_NEAR_M 20, SEED_M, JOIN_R_M, END_PROBE_M, the window and the cell [invented: sampling
geometry, chosen before any reading]. numpy only (the PC's Python has no scipy; G10: no Blender, no shapely). Writes <out>/disconnects.json
and <out>/disconnects.txt (ranked).
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
import time
from pathlib import Path

import warnings

import numpy as np


# ---- numpy-only stand-ins for the two scipy.ndimage calls this check used (the PC's Python has no scipy) ----
def label8(D):
    """8-connected component labels of a 2-D bool grid, numbered 1..n in raster order of each component's first cell
    (the numbering scipy.ndimage.label gives). Row runs + union-find over runs."""
    D = np.asarray(D, bool)
    n0 = D.shape[0]
    rs, ra, rb, rows = [], [], [], []
    for i in range(n0):
        d = np.diff(np.concatenate(([0], D[i].astype(np.int8), [0])))
        st, en = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        rows.append((len(ra), len(ra) + len(st)))
        rs.extend([i] * len(st)); ra.extend(st.tolist()); rb.extend(en.tolist())
    parent = list(range(len(ra)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(1, n0):
        p0, p1 = rows[i - 1]
        c0, c1 = rows[i]
        j = p0
        for k in range(c0, c1):
            a, b = ra[k], rb[k]
            while j < p1 and rb[j] < a:      # previous-row run ends left of a-1: no contact
                j += 1
            jj = j
            while jj < p1 and ra[jj] <= b:   # previous-row run starts at or before b (8-neighbour contact)
                x, y = find(k), find(jj)
                if x != y:
                    parent[max(x, y)] = min(x, y)
                jj += 1
    lab = np.zeros(D.shape, np.int32)
    num = {}
    for k in range(len(ra)):
        r = find(k)
        if r not in num:
            num[r] = len(num) + 1
        lab[rs[k], ra[k]:rb[k]] = num[r]
    return lab, len(num)


def _edge_cells(M):
    """Cells of M with at least one 8-neighbour outside M (grid border counts as outside), raster order."""
    P = np.pad(M, 1, constant_values=False)
    inner = M.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                inner &= P[1 + di:1 + di + M.shape[0], 1 + dj:1 + dj + M.shape[1]]
    return np.nonzero(M & ~inner)


def nearest_pair(A, Bm, chunk=4_000_000):
    """The B cell nearest to A (first in raster order on ties, as np.argmin over an EDT gives) and its nearest A cell,
    with the distance in cells. The nearest pair between two cell sets always lies on both sets' edges, so only edge
    cells are compared. Tie between equally near A cells: the first in raster order (scipy's EDT may pick another one
    at the same distance; gap_m is the same either way)."""
    ai, aj = _edge_cells(A)
    bi, bj = _edge_cells(Bm)
    best_d2 = np.empty(len(bi), np.int64); best_a = np.empty(len(bi), np.int64)
    step = max(1, chunk // max(len(ai), 1))
    for s0 in range(0, len(bi), step):
        d2 = (bi[s0:s0 + step, None] - ai[None, :]).astype(np.int64) ** 2 + (bj[s0:s0 + step, None] - aj[None, :]).astype(np.int64) ** 2
        best_a[s0:s0 + step] = d2.argmin(1)
        best_d2[s0:s0 + step] = d2[np.arange(d2.shape[0]), best_a[s0:s0 + step]]
    k = int(np.argmin(best_d2))
    return (int(bi[k]), int(bj[k])), (int(ai[best_a[k]]), int(aj[best_a[k]])), float(np.sqrt(best_d2[k]))

STEP_M = 0.05          # [measured] kn5_ground_check.ROAD_GAP_M
FINE_M = 0.10          # [sampling] mouth_survey.FINE_M
LEVEL_M = 1.0          # [invented] a jump this big between neighbouring cells is a deck over a road, not a lip
GAP_REPORT_M = 0.2     # [invented] two cells at 0.10 m
END_JUNCTION_M = 15.0  # [invented]
MOUTH_NEAR_M = 20.0    # [invented]
NAME_REACH_M = 15.0    # tools/name_blades.nearest_name's reach
SEED_M = 8.0           # [invented] seeds this far out from the place along each road
JOIN_R_M = 12.0        # [invented] the join zone judged around a place
END_PROBE_M = 12.0     # [invented] how far past a dead end the path looks
BOX_TOL_M = 6.0        # [invented] an end this close to the grid's outer extent is on the clip box
PUBLIC = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
          "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}
NAMED = PUBLIC - {"motorway", "motorway_link"}
CLS = {"ROAD": 1, "PAD": 2, "KERB": 3, "GRASS": 4}


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- the gate OBJ, numpy
def load_obj(path):
    """vertices (N,3) float64; triangles (M,3) int32 (0-based); class per triangle (int8, CLS). Other objects skipped."""
    t0 = time.time()
    vx, fa, fb, fc, fk = [], [], [], [], []
    cur = 0
    nv = 0
    with open(path, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            c2 = line[:2]
            if c2 == "v ":
                vx.append(line[2:])
                nv += 1
            elif c2 == "o " or c2 == "g ":
                nm = line[2:].strip().upper()
                cur = (CLS["PAD"] if nm.startswith("1ROAD_PAD") else CLS["ROAD"] if nm.startswith("1ROAD")
                       else CLS["KERB"] if nm.startswith("1KERB") else CLS["GRASS"] if nm.startswith("1GRASS") else 0)
            elif c2 == "f " and cur:
                idx = [int(t.split("/")[0]) for t in line.split()[1:]]
                idx = [i - 1 if i > 0 else nv + i for i in idx]
                for k in range(1, len(idx) - 1):
                    fa.append(idx[0]); fb.append(idx[k]); fc.append(idx[k + 1]); fk.append(cur)
    V = np.array([tuple(map(float, s.split()[:3])) for s in vx], dtype=np.float64)
    del vx
    T = np.stack([np.array(fa, np.int32), np.array(fb, np.int32), np.array(fc, np.int32)], 1)
    K = np.array(fk, np.int8)
    log(f"[obj] {path}: {len(V):,} verts, {len(T):,} tris kept "
        f"({', '.join(f'{k} {int((K == v).sum()):,}' for k, v in CLS.items())}) in {time.time() - t0:.0f} s")
    return V, T, K


class Mesh:
    def __init__(self, V, T, K):
        self.V, self.T, self.K = V, T, K
        P = V[T]                                    # (M,3,3)
        self.xmin, self.xmax = P[:, :, 0].min(1), P[:, :, 0].max(1)
        self.zmin, self.zmax = P[:, :, 2].min(1), P[:, :, 2].max(1)
        del P

    def window(self, x0, z0, x1, z1):
        return np.nonzero((self.xmax >= x0) & (self.xmin <= x1) & (self.zmax >= z0) & (self.zmin <= z1))[0]


def raster(mesh, cx, cz, half, cell):
    """topmost drivable z / class and topmost ground z on a (n, n) grid of cell centres around (cx, cz)."""
    n = int(round(2 * half / cell))
    x0, z0 = cx - half, cz - half
    top = np.full(n * n, -np.inf)
    cls = np.zeros(n * n, np.int8)
    low = np.full(n * n, np.inf)                    # lowest drivable sheet (deck-over-deck / overlap)
    gnd = np.full(n * n, -np.inf)
    sel = mesh.window(x0, z0, x0 + n * cell, z0 + n * cell)
    if not len(sel):
        return n, x0, z0, top.reshape(n, n), cls.reshape(n, n), gnd.reshape(n, n), low.reshape(n, n)
    P = mesh.V[mesh.T[sel]]
    Kc = mesh.K[sel]
    i0 = np.clip(np.floor((P[:, :, 0].min(1) - x0) / cell - 0.5).astype(int) + 1, 0, n)
    i1 = np.clip(np.floor((P[:, :, 0].max(1) - x0) / cell - 0.5).astype(int), -1, n - 1)
    j0 = np.clip(np.floor((P[:, :, 2].min(1) - z0) / cell - 0.5).astype(int) + 1, 0, n)
    j1 = np.clip(np.floor((P[:, :, 2].max(1) - z0) / cell - 0.5).astype(int), -1, n - 1)
    ni = np.maximum(i1 - i0 + 1, 0)
    nj = np.maximum(j1 - j0 + 1, 0)
    cnt = ni * nj
    keep = cnt > 0
    order = np.nonzero(keep)[0]
    CH = 1_500_000                                  # candidate cells per chunk (memory)
    cum = np.cumsum(cnt[order])
    start = 0
    while start < len(order):
        base = cum[start - 1] if start else 0
        stop = int(np.searchsorted(cum, base + CH, side="right"))
        stop = max(stop, start + 1)
        ids = order[start:stop]
        c = cnt[ids]
        rep = np.repeat(np.arange(len(ids)), c)
        off = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)
        tj = ids[rep]
        ii = i0[tj] + off // nj[tj]
        jj = j0[tj] + off % nj[tj]
        px = x0 + (ii + 0.5) * cell
        pz = z0 + (jj + 0.5) * cell
        a, b, cc = P[tj, 0], P[tj, 1], P[tj, 2]
        d = (b[:, 2] - cc[:, 2]) * (a[:, 0] - cc[:, 0]) + (cc[:, 0] - b[:, 0]) * (a[:, 2] - cc[:, 2])
        ok = np.abs(d) > 1e-12
        d = np.where(ok, d, 1.0)
        l1 = ((b[:, 2] - cc[:, 2]) * (px - cc[:, 0]) + (cc[:, 0] - b[:, 0]) * (pz - cc[:, 2])) / d
        l2 = ((cc[:, 2] - a[:, 2]) * (px - cc[:, 0]) + (a[:, 0] - cc[:, 0]) * (pz - cc[:, 2])) / d
        l3 = 1.0 - l1 - l2
        inside = ok & (l1 >= -1e-7) & (l2 >= -1e-7) & (l3 >= -1e-7)
        y = l1 * a[:, 1] + l2 * b[:, 1] + l3 * cc[:, 1]
        flat = ii * n + jj
        k = Kc[tj]
        drv = inside & (k != CLS["GRASS"])
        g = inside & (k == CLS["GRASS"])
        if drv.any():
            f_, y_, k_ = flat[drv], y[drv], k[drv]
            o = np.lexsort((y_, f_))                # by cell, then height: the last per cell is the top
            f_, y_, k_ = f_[o], y_[o], k_[o]
            last = np.r_[f_[1:] != f_[:-1], True]
            first = np.r_[True, f_[1:] != f_[:-1]]
            upd = y_[last] > top[f_[last]]
            top[f_[last][upd]] = y_[last][upd]
            cls[f_[last][upd]] = k_[last][upd]
            np.minimum.at(low, f_[first], y_[first])
        if g.any():
            np.maximum.at(gnd, flat[g], y[g])
        start = stop
    return n, x0, z0, top.reshape(n, n), cls.reshape(n, n), gnd.reshape(n, n), low.reshape(n, n)


# ---------------------------------------------------------------- lines and OSM
class Line:
    def __init__(self, name, pts, widths):
        P = np.asarray(pts, float)
        self.name, self.P, self.W = name, P, np.asarray(widths, float)
        d = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2]))
        self.s = np.r_[0.0, np.cumsum(d)]

    def dist(self, x, z):
        A, B = self.P[:-1][:, [0, 2]], self.P[1:][:, [0, 2]]
        dd = B - A
        L2 = np.maximum((dd ** 2).sum(1), 1e-12)
        t = np.clip(((np.array([x, z]) - A) * dd).sum(1) / L2, 0, 1)
        Q = A + dd * t[:, None]
        D = np.hypot(Q[:, 0] - x, Q[:, 1] - z)
        i = int(D.argmin())
        return float(D[i]), i, float(self.s[i] + t[i] * math.sqrt(L2[i])), float(self.W[i])

    def at(self, s):
        s = min(max(s, 0.0), self.s[-1])
        i = int(np.searchsorted(self.s, s, side="right") - 1)
        i = min(i, len(self.s) - 2)
        t = (s - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-9)
        p = self.P[i] + (self.P[i + 1] - self.P[i]) * t
        tx, tz = self.P[i + 1][0] - self.P[i][0], self.P[i + 1][2] - self.P[i][2]
        L = math.hypot(tx, tz) or 1.0
        return float(p[0]), float(p[2]), tx / L, tz / L, float(self.W[i])


def osm_index(path, lon0, lat0):
    o = json.loads(Path(path).read_text(encoding="utf-8"))
    els = (o.get("payload") or o).get("elements", [])
    phi = math.radians(lat0)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    deg = collections.Counter()
    nxz, nnames, nclass = {}, collections.defaultdict(set), collections.defaultdict(set)
    segs, named = [], []
    for e in els:
        tg = e.get("tags") or {}
        hw = tg.get("highway")
        if e.get("type") != "way" or not e.get("geometry"):
            continue
        g = [((q["lon"] - lon0) * m_lon, (q["lat"] - lat0) * m_lat) for q in e["geometry"]]
        for a, b in zip(g, g[1:]):
            segs.append((a[0], a[1], b[0], b[1], hw or "", tg.get("name", "")))
        if hw not in PUBLIC:
            continue
        ns = e.get("nodes") or []
        for k, nd in enumerate(ns):
            deg[nd] += 1 if k in (0, len(ns) - 1) else 2
            nxz[nd] = g[k]
            nnames[nd].add(tg.get("name") or f"(unnamed {hw})")
            nclass[nd].add(hw)
        if tg.get("name") and hw in NAMED:
            named.append((tg["name"], np.array(g)))
    S = np.array([s[:4] for s in segs]) if segs else np.zeros((0, 4))
    meta = [s[4:] for s in segs]
    return dict(deg=deg, nxz=nxz, nnames=nnames, nclass=nclass, segs=S, segmeta=meta, named=named,
                m_lon=m_lon, m_lat=m_lat, lon0=lon0, lat0=lat0)


def seg_dist(S, x, z):
    A, B = S[:, :2], S[:, 2:]
    dd = B - A
    L2 = np.maximum((dd ** 2).sum(1), 1e-12)
    t = np.clip(((np.array([x, z]) - A) * dd).sum(1) / L2, 0, 1)
    Q = A + dd * t[:, None]
    return np.hypot(Q[:, 0] - x, Q[:, 1] - z)


def name_at(osm, x, z):
    best = None
    for nm, g in osm["named"]:
        if len(g) < 2:
            continue
        d = seg_dist(np.c_[g[:-1], g[1:]], x, z).min()
        if d <= NAME_REACH_M and (best is None or d < best[0]):
            best = (d, nm)
    return best[1] if best else None


def name_of_line(osm, line, s_from, s_to):
    votes = collections.Counter()
    for s in np.linspace(s_from, s_to, 5):
        x, z, *_ = line.at(s)
        nm = name_at(osm, x, z)
        if nm:
            votes[nm] += 1
    return votes.most_common(1)[0][0] if votes else None


def lonlat(osm, x, z):
    return [round(osm["lon0"] + x / osm["m_lon"], 6), round(osm["lat0"] + z / osm["m_lat"], 6)]


# ---------------------------------------------------------------- one place, measured
def measure(mesh, cx, cz, seeds, paths, cell, half):
    n, x0, z0, top, cls, gnd, low = raster(mesh, cx, cz, half, cell)
    D = np.isfinite(top)
    lab, nlab = label8(D)

    def ij(x, z):
        i, j = int((x - x0) / cell), int((z - z0) / cell)
        return (i, j) if 0 <= i < n and 0 <= j < n else None

    # CONNECTED: the seeds' components
    sl = []
    for nm, x, z in seeds:
        c = ij(x, z)
        lb = 0
        if c is not None:
            # the seed's cell, else the nearest drivable cell within 1.5 m (a seed on a hole, a centre line off the deck)
            r = int(1.5 / cell)
            i, j = c
            w = lab[max(i - r, 0):i + r + 1, max(j - r, 0):j + r + 1]
            if lab[i, j]:
                lb = int(lab[i, j])
            elif (w > 0).any():
                ii, jj = np.nonzero(w > 0)
                k = int(np.argmin((ii - min(r, i)) ** 2 + (jj - min(r, j)) ** 2))
                lb = int(w[ii[k], jj[k]])
        sl.append((nm, lb))
    comps = sorted({lb for _n, lb in sl if lb})
    out = {"seeds": [{"road": nm, "component": lb} for nm, lb in sl], "components": len(comps)}
    missing = [nm for nm, lb in sl if not lb]
    if missing:
        out["seed_without_pavement"] = missing
    if len(comps) >= 2:
        # the shortest horizontal gap between the first seed's component and each other one
        A = lab == comps[0]
        gaps = []
        for cb in comps[1:]:
            Bm = lab == cb
            (bi, bj), (gi, gj), dcell = nearest_pair(A, Bm)
            g = dcell * cell
            gaps.append({"gap_m": round(g, 2), "between": [R(x0 + (gi + .5) * cell), R(z0 + (gj + .5) * cell), R(x0 + (bi + .5) * cell), R(z0 + (bj + .5) * cell)],
                         "dz_m": round(float(top[bi, bj] - top[gi, gj]), 3)})
        out["gaps"] = gaps
    # zone
    ii, jj = np.mgrid[0:n, 0:n]
    zone = np.hypot(x0 + (ii + .5) * cell - cx, z0 + (jj + .5) * cell - cz) <= JOIN_R_M
    # STEP between 4-neighbour drivable cells
    best = {"max_m": 0.0}
    steps, levels = [], []
    run = 0
    for ax in (0, 1):
        a = top[:-1, :] if ax == 0 else top[:, :-1]
        b = top[1:, :] if ax == 0 else top[:, 1:]
        zz = (zone[:-1, :] & zone[1:, :]) if ax == 0 else (zone[:, :-1] & zone[:, 1:])
        ok = np.isfinite(a) & np.isfinite(b) & zz
        dz = np.where(ok, np.abs(a - b), 0.0)
        lv = dz > LEVEL_M
        st = (dz > STEP_M) & ~lv
        run += int(st.sum())
        if lv.any():
            levels.append(float(dz[lv].max()))
        if st.any():
            k = np.argmax(np.where(st, dz, 0))
            i, j = np.unravel_index(k, dz.shape)
            if dz[i, j] > best["max_m"]:
                ca = cls[i, j]
                cb = cls[i + 1, j] if ax == 0 else cls[i, j + 1]
                best = {"max_m": round(float(dz[i, j]), 3), "at": [R(x0 + (i + .5) * cell), R(z0 + (j + .5) * cell)],
                        "classes": sorted({_cname(ca), _cname(cb)})}
    best["run_m_over"] = round(run * cell, 1)
    out["step"] = best
    if levels:
        out["level_change_m"] = round(max(levels), 2)
    # EDGE: drivable cells beside non-drivable ones, against the ground beside them
    E = {}
    for name, code in (("ROAD", (1, 2)), ("KERB", (3,))):
        hang, wall, hl, wl, hat, wat = 0.0, 0.0, 0, 0, None, None
        isc = np.isin(cls, code) & D & zone
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            src = isc[max(-di, 0):n - max(di, 0), max(-dj, 0):n - max(dj, 0)]
            nb_d = D[max(di, 0):n - max(-di, 0), max(dj, 0):n - max(-dj, 0)]
            nb_g = gnd[max(di, 0):n - max(-di, 0), max(dj, 0):n - max(-dj, 0)]
            ts = top[max(-di, 0):n - max(di, 0), max(-dj, 0):n - max(dj, 0)]
            m = src & ~nb_d & np.isfinite(nb_g)
            if not m.any():
                continue
            dz = np.where(m, ts - nb_g, np.nan)
            h = np.nanmax(dz) if np.isfinite(np.nanmax(dz)) else 0.0
            w = -np.nanmin(dz) if np.isfinite(np.nanmin(dz)) else 0.0
            hl += int((dz > STEP_M).sum())
            wl += int((dz < -STEP_M).sum())
            if h > hang:
                hang = float(h)
                k = np.nanargmax(dz)
                i, j = np.unravel_index(k, dz.shape)
                hat = [R(x0 + (i + max(-di, 0) + .5) * cell), R(z0 + (j + max(-dj, 0) + .5) * cell)]
            if w > wall:
                wall = float(w)
                k = np.nanargmin(dz)
                i, j = np.unravel_index(k, dz.shape)
                wat = [R(x0 + (i + max(-di, 0) + .5) * cell), R(z0 + (j + max(-dj, 0) + .5) * cell)]
        E[name] = {"hang_max_m": round(hang, 3), "hang_at": hat, "hang_run_m": round(hl * cell, 1),
                   "wall_max_m": round(wall, 3), "wall_at": wat, "wall_run_m": round(wl * cell, 1)}
    out["edge"] = E
    # bare: ground with no drivable sheet inside the zone where a path says pavement should be (the paths do this)
    P = []
    for pname, pts in paths:
        ys, hole, hole_max, rise, rise_at = [], 0.0, 0.0, 0.0, None
        cur = 0.0
        prev = None
        step = 0.05
        for (x, z) in pts:
            c = ij(x, z)
            y = top[c] if c is not None and np.isfinite(top[c]) else None
            if y is None:
                cur += step
                hole_max = max(hole_max, cur)
                hole += step
            else:
                cur = 0.0
                if prev is not None and abs(y - prev[0]) <= LEVEL_M:
                    d = abs(y - prev[0])
                    if d > rise:
                        rise, rise_at = float(d), [R(x), R(z)]
                prev = (y,)
        g_end = None
        P.append({"path": pname, "hole_m": round(hole, 2), "longest_hole_m": round(hole_max, 2),
                  "max_jump_m": round(rise, 3), "jump_at": rise_at})
    out["paths"] = P
    return out


def R(v, k=2):
    return round(float(v), k)


def _cname(c):
    return {1: "ROAD", 2: "PAD", 3: "KERB", 4: "GRASS"}.get(int(c), "-")


def line_pts(x, z, tx, tz, u0, u1, lat=0.0, step=0.05):
    nx, nz = -tz, tx
    us = np.arange(u0, u1 + 1e-9, step)
    return [(x + tx * u + nx * lat, z + tz * u + nz * lat) for u in us]


# ---------------------------------------------------------------- the places
def main(argv=None):
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--obj", default=None)
    ap.add_argument("--osm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cell", type=float, default=0.10)
    ap.add_argument("--win", type=float, default=22.0)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    data = proj / "data"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    route = cfg.get("route") or {}
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pads = json.loads((data / "pads.built.json").read_text(encoding="utf-8")).get("pads", []) if (data / "pads.built.json").exists() else []
    O = local["origin"]
    osm = osm_index(a.osm, float(O["lon"]), float(O["lat"]))
    lines = {"MAINLINE": Line("MAINLINE", local["points_xyz_m"], local["widths_m"])}
    for c in conns:
        lines[c["name"]] = Line(c["name"], c["points_xyz_m"], c["widths_m"])
    known = {}
    for r in route.get("verify_mouth_corners_allowed") or []:
        known[(r["piece"], r["end"])] = "verify_mouth_corners_allowed: " + r.get("why", "")[:160]
    for r in route.get("mouth_returns_skip") or []:
        known[(r["piece"], r["end"])] = "mouth_returns_skip: " + r.get("why", "")[:160]
    allx = np.concatenate([L.P[:, 0] for n_, L in lines.items() if n_ != "MAINLINE"])
    allz = np.concatenate([L.P[:, 2] for n_, L in lines.items() if n_ != "MAINLINE"])
    box = (allx.min(), allx.max(), allz.min(), allz.max())
    padpolys = [(p["id"], np.asarray(p["outline_en"], float)) for p in pads if p.get("outline_en")]

    def in_pad(x, z):
        for pid, Pp in padpolys:
            c = False
            for i in range(len(Pp)):
                p1, p2 = Pp[i], Pp[(i + 1) % len(Pp)]
                if (p1[1] > z) != (p2[1] > z) and x < (p2[0] - p1[0]) * (z - p1[1]) / (p2[1] - p1[1]) + p1[0]:
                    c = not c
            if c:
                return pid
        return None

    def roads_near(x, z, extra=4.0, skip=()):
        r = []
        for nm, L in lines.items():
            if nm in skip:
                continue
            d, i, s, w = L.dist(x, z)
            if d <= w / 2.0 + extra:
                r.append((nm, s, d))
        return r

    places = []
    mend = set()
    for mo in mouths:
        mend.add((mo["piece"], mo["end"]))
        cx, _cy, cz = mo["cut_xyz"]
        P = lines[mo["piece"]]
        H = lines.get(mo["host"])
        u = 1.0 if mo["end"] == "start" else -1.0
        s_end = 0.0 if mo["end"] == "start" else P.s[-1]
        x, z, tx, tz, w = P.at(s_end + u * 0.5)
        tx, tz = tx * u, tz * u                     # pointing up the piece, away from the host
        sx, sz, *_ = P.at(s_end + u * SEED_M)
        seeds = [(mo["piece"], sx, sz)]
        if H is not None:
            _d, _i, hs, hw = H.dist(cx, cz)
            hx, hz, htx, htz, _w = H.at(hs)
            seeds.append((mo["host"], hx, hz))
        paths = [(f"piece l={lat:+.1f}", line_pts(cx, cz, tx, tz, -5.0, 12.0, lat)) for lat in (0.0, w / 2 - 0.9, -(w / 2 - 0.9))]
        places.append(dict(kind="MOUTH", id=f"{mo['piece']}({mo['end']})->{mo['host']}", x=cx, z=cz, piece=mo["piece"],
                           end=mo["end"], host=mo["host"], seeds=seeds, paths=paths,
                           known=known.get((mo["piece"], mo["end"]))))
    # END: piece ends with no mouth
    J = [nd for nd, dg in osm["deg"].items() if dg >= 3]
    JXY = np.array([osm["nxz"][nd] for nd in J]) if J else np.zeros((0, 2))
    for c in conns:
        L = lines[c["name"]]
        for end in ("start", "end"):
            if (c["name"], end) in mend:
                continue
            u = 1.0 if end == "start" else -1.0
            s_end = 0.0 if end == "start" else L.s[-1]
            ex, ez, tx, tz, w = L.at(s_end)
            _x, _z, tx, tz, _w = L.at(s_end + u * 2.0)
            tx, tz = -tx * u, -tz * u                # pointing OUT past the end
            on_box = min(abs(ex - box[0]), abs(ex - box[1]), abs(ez - box[2]), abs(ez - box[3])) <= BOX_TOL_M
            dj = np.hypot(JXY[:, 0] - ex, JXY[:, 1] - ez) if len(JXY) else np.array([1e9])
            k = int(dj.argmin())
            jn = J[k] if len(J) else None
            probe = (ex + tx * 15.0, ez + tz * 15.0)
            sd = seg_dist(osm["segs"], *probe) if len(osm["segs"]) else np.array([1e9])
            kk = int(sd.argmin())
            cont_hw, cont_nm = osm["segmeta"][kk]
            if dj[k] <= END_JUNCTION_M:
                ocls = "OSM_JUNCTION"
            elif sd[kk] <= 6.0 and cont_hw in PUBLIC:
                ocls = "OSM_CONTINUES"
            elif sd[kk] <= 6.0:
                ocls = "SERVICE" if cont_hw == "service" else f"OSM_{cont_hw or 'other'}"
            else:
                ocls = "OSM_DEAD_END"
            other = roads_near(ex + tx * 3.0, ez + tz * 3.0, extra=25.0, skip=(c["name"],))
            other.sort(key=lambda r: r[2])
            seeds = [(c["name"], *L.at(s_end + u * SEED_M)[:2])]
            if other and other[0][2] <= 30.0:
                o = lines[other[0][0]]
                ox, oz, *_ = o.at(other[0][1])
                seeds.append((other[0][0], ox, oz))
            paths = [("centre", line_pts(ex, ez, tx, tz, -12.0, END_PROBE_M))]
            places.append(dict(kind="END", id=f"{c['name']}({end})", x=ex, z=ez, piece=c["name"], end=end,
                               osm_class=ocls, on_clip_box=bool(on_box), nearest_osm_junction_m=round(float(dj[k]), 1),
                               osm_junction_names=sorted(osm["nnames"][jn]) if jn else [],
                               osm_beyond=[cont_hw, cont_nm, round(float(sd[kk]), 1)],
                               nearest_built=[(r[0], round(r[2], 1)) for r in other[:2]], seeds=seeds, paths=paths,
                               known=known.get((c["name"], end))))
    # OSMJ: OSM junctions with no mouth near
    cuts = np.array([[m["cut_xyz"][0], m["cut_xyz"][2]] for m in mouths])
    for nd in J:
        x, z = osm["nxz"][nd]
        if not (box[0] + 10 < x < box[1] - 10 and box[2] + 10 < z < box[3] - 10):
            continue
        if np.hypot(cuts[:, 0] - x, cuts[:, 1] - z).min() <= MOUTH_NEAR_M or in_pad(x, z):
            continue
        if osm["nclass"][nd] <= {"motorway", "motorway_link"}:
            continue
        nr = roads_near(x, z)
        if not nr:
            continue
        seeds, paths = [], []
        for nm, s, _d in nr:
            L = lines[nm]
            for sg in (-1.0, 1.0):
                sx, sz, *_ = L.at(s + sg * SEED_M)
                seeds.append((f"{nm}{'+' if sg > 0 else '-'}", sx, sz))
            px, pz, tx, tz, _w = L.at(s)
            paths.append((f"{nm} centre", line_pts(px, pz, tx, tz, -12.0, 12.0)))
        places.append(dict(kind="OSMJ", id=f"osm node {nd}", x=x, z=z, osm_names=sorted(osm["nnames"][nd]),
                           osm_classes=sorted(osm["nclass"][nd]), built=[r[0] for r in nr], seeds=seeds, paths=paths,
                           known=None))
    log(f"[places] {sum(p['kind'] == 'MOUTH' for p in places)} mouths, {sum(p['kind'] == 'END' for p in places)} ends, "
        f"{sum(p['kind'] == 'OSMJ' for p in places)} OSM junctions with no mouth; grid box x {box[0]:.0f}..{box[1]:.0f} "
        f"z {box[2]:.0f}..{box[3]:.0f}")
    if a.limit:
        places = places[:a.limit]
    obj = Path(a.obj) if a.obj else data / "track.obj"
    mesh = Mesh(*load_obj(obj))
    t0 = time.time()
    rows = []
    for k, p in enumerate(places):
        far = max([math.hypot(sx - p["x"], sz - p["z"]) for _n, sx, sz in p["seeds"]] or [0.0])
        half = min(max(a.win, far + 4.0), 60.0)     # every seed inside the window
        m = measure(mesh, p["x"], p["z"], p["seeds"], p["paths"], a.cell, half)
        m["window_half_m"] = half
        r = {kk: v for kk, v in p.items() if kk not in ("seeds", "paths")}
        r["x"], r["z"] = R(p["x"]), R(p["z"])
        r["lonlat"] = lonlat(osm, p["x"], p["z"])
        if p["kind"] == "MOUTH":
            Lp = lines[p["piece"]]
            r["names"] = [name_of_line(osm, Lp, 5, 40) if p["end"] == "start" else name_of_line(osm, Lp, Lp.s[-1] - 40, Lp.s[-1] - 5)]
            H = lines.get(p["host"])
            if H is not None:
                hs = H.dist(p["x"], p["z"])[2]
                hn = [name_of_line(osm, H, hs + sg * 15, hs + sg * 35) for sg in (-1, 1)]
                r["names"].append(next((h for h in hn if h and h != r["names"][0]), hn[0] or hn[1]))
        elif p["kind"] == "END":
            L = lines[p["piece"]]
            r["names"] = [name_of_line(osm, L, 5, 40) if p["end"] == "start" else name_of_line(osm, L, L.s[-1] - 40, L.s[-1] - 5)]
        else:
            r["names"] = p["osm_names"]
        r.update(m)
        rows.append(r)
        if (k + 1) % 25 == 0:
            log(f"[measure] {k + 1}/{len(places)} places, {time.time() - t0:.0f} s")
    report(rows, out, obj)
    return 0


def severity(r):
    gap = max([g["gap_m"] for g in r.get("gaps", [])] or [0.0])
    step = r["step"].get("max_m", 0.0)
    hang = max(r["edge"]["ROAD"]["hang_max_m"], r["edge"]["KERB"]["hang_max_m"])
    wall = max(r["edge"]["ROAD"]["wall_max_m"], r["edge"]["KERB"]["wall_max_m"])
    hole = max([p["longest_hole_m"] for p in r["paths"] if not p["path"].startswith("centre")] or [0.0])
    return gap, step, hang, wall, hole


def report(rows, out, obj):
    (out / "disconnects.json").write_text(json.dumps({"obj": str(obj), "places": rows}, indent=1), encoding="utf-8")
    L = [f"sc_disconnects on {obj}: {len(rows)} places (MOUTH / END / OSMJ). Numbers measured on the OBJ; bands: step "
         f"{STEP_M} m [measured: kn5_ground_check.ROAD_GAP_M], the rest sampling geometry [invented].", ""]
    # 1: not one drivable sheet
    dis = [r for r in rows if r.get("gaps") or r.get("seed_without_pavement")]
    dis.sort(key=lambda r: -max([g["gap_m"] for g in r.get("gaps", [])] or [99.0 if r.get("seed_without_pavement") else 0]))
    L.append(f"== 1. NOT CONNECTED (the roads that should meet are separate drivable sheets): {len(dis)}")
    for r in dis:
        L.append(_line(r, "gap " + ", ".join(f"{g['gap_m']} m (dz {g['dz_m']})" for g in r.get("gaps", []))
                       + (f" no pavement at seed {r['seed_without_pavement']}" if r.get("seed_without_pavement") else "")))
    # 2: dead ends where OSM says the street meets something
    de = [r for r in rows if r["kind"] == "END" and r["osm_class"] in ("OSM_JUNCTION", "OSM_CONTINUES")]
    de.sort(key=lambda r: r["nearest_osm_junction_m"])
    L += ["", f"== 2. DEAD ENDS where OpenStreetMap has a junction / the road going on: {len(de)}"]
    for r in de:
        L.append(_line(r, f"{r['osm_class']}{' (on the grid clip box)' if r['on_clip_box'] else ''}: OSM junction "
                          f"{r['nearest_osm_junction_m']} m away {r['osm_junction_names']}; nearest built {r['nearest_built']}"))
    # 3: OSM junctions with no mouth
    oj = [r for r in rows if r["kind"] == "OSMJ"]
    L += ["", f"== 3. OSM JUNCTIONS with no mouth (built roads there: one = the cross street was not built): {len(oj)}"]
    for r in sorted(oj, key=lambda r: (len(r["built"]), r["osm_names"])):
        L.append(_line(r, f"built {r['built']}"))
    # 4: steps / hangs / walls, ranked, everywhere
    L += ["", "== 4. STEPS (4-neighbour drivable cells, |dz| > 0.05 m) inside 12 m of a place, worst first"]
    st = [r for r in rows if r["step"].get("max_m", 0) > STEP_M]
    for r in sorted(st, key=lambda r: -r["step"]["max_m"]):
        L.append(_line(r, f"step {r['step']['max_m']} m at {r['step']['at']} {r['step']['classes']}, "
                          f"{r['step']['run_m_over']} m of cell edges over 0.05"))
    L += ["", "== 5. ROAD SLAB EDGE over grass (no strip beside the pavement: HANG > 0.05 m), worst first"]
    hg = [r for r in rows if r["edge"]["ROAD"]["hang_max_m"] > STEP_M]
    for r in sorted(hg, key=lambda r: -r["edge"]["ROAD"]["hang_max_m"]):
        e = r["edge"]["ROAD"]
        L.append(_line(r, f"hang {e['hang_max_m']} m at {e['hang_at']}, {e['hang_run_m']} m of edge over 0.05"))
    L += ["", "== 6. GROUND standing over a drivable edge (WALL > 0.05 m), worst first"]
    wl = [r for r in rows if max(r["edge"]["ROAD"]["wall_max_m"], r["edge"]["KERB"]["wall_max_m"]) > STEP_M]
    for r in sorted(wl, key=lambda r: -max(r["edge"]["ROAD"]["wall_max_m"], r["edge"]["KERB"]["wall_max_m"])):
        e, k = r["edge"]["ROAD"], r["edge"]["KERB"]
        L.append(_line(r, f"wall ROAD {e['wall_max_m']} m ({e['wall_run_m']} m), KERB lip {k['wall_max_m']} m ({k['wall_run_m']} m)"))
    L += ["", "== 7. HOLES on the wheel lines through a mouth / junction (no drivable sheet), worst first"]
    ho = [(max([p["longest_hole_m"] for p in r["paths"] if not p["path"].startswith("centre") or r["kind"] != "END"] or [0]), r)
          for r in rows]
    for h, r in sorted([t for t in ho if t[0] > GAP_REPORT_M], key=lambda t: -t[0]):
        L.append(_line(r, f"longest hole {h} m"))
    (out / "disconnects.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    log("\n".join(L[:12]))
    log(f"[out] {out / 'disconnects.json'}, {out / 'disconnects.txt'}")


def _line(r, what):
    nm = " / ".join(n for n in (r.get("names") or []) if n) or "(no OSM name)"
    kn = f"  [known: {r['known'][:70]}]" if r.get("known") else ""
    return f"  {r['kind']:5s} {r['id']:44s} {nm[:60]:60s} x {r['x']:9.1f} z {r['z']:8.1f} {r['lonlat']}: {what}{kn}"


if __name__ == "__main__":
    sys.exit(main())

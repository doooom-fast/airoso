"""ENGINE-DRAFT PADS, the pure half (stdlib only; tests/tools/test_draft_pads.py runs it in plain Python): the geometry
both tools/draft_pad_outline.py (the measurement) and tools/author_draft_pads_blend.py (the Blender author) share.

A pad is docs/JUNCTIONS.md §2.0 topology B on an ENGINE DRAFT: the lap is both main arms, cut at two of its own rows
(``cuts``), and one deck fills the junction between them out to its MEASURED outline -- the lidar or aerial pavement edge,
never a chosen radius (ledger 0048 P3b; Kevin's rule: measured, not invented). Lake Murray's tools/junction_pad.py is the
same idea on that network's connector pieces and cannot take a lap arm; this module is the engine-draft path, one for every
track (the Lariat's mouths, Sand Creek's corners, Lake Murray v5's I-8 seam).

Frames: the track's local metres, E east and N north (centerline.local.json's x and z), heights in its local y. The
Blender scene is the same frame with z up (underlay.py).
"""
from __future__ import annotations

import math

CUT_HALF_M = 30.0          # [invented] a lap cut's barrier runs this far either side of the lap
ON_CUT_M = 0.6             # an outline point this close to a cut line after smoothing is put back exactly on it (the cells beside a 0.3 m barrier band sit ~0.43 m off it)
PLANE_MIN_POINTS = 8       # fewer ground points under a deck node: no plane there (None)
PLANE_TRIM_M = 0.10        # [invented] one refit without points this far off the first plane (a curb, a car)


def meters_per_degree(lat0: float) -> tuple[float, float]:
    """(m per deg lon, m per deg lat): scripts.geometry.projection._meters_per_degree, the same WGS84 series."""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


def declarations(cfg: dict) -> list[dict]:
    """route.draft_pads, validated: [] when none is declared."""
    pads = ((cfg.get("route") or {}).get("draft_pads")) or []
    seen = set()
    for d in pads:
        pid = d.get("id")
        if not pid or pid in seen:
            raise SystemExit(f"route.draft_pads: a pad without an id, or {pid!r} twice")
        seen.add(pid)
        cuts = d.get("cuts")
        if not (isinstance(cuts, list) and len(cuts) == 2 and all(isinstance(c, int) for c in cuts)):
            raise SystemExit(f"route.draft_pads {pid}: cuts must be [in vertex, out vertex]")
        if not isinstance(d.get("node"), int) or not cuts[0] < d["node"] < cuts[1]:
            raise SystemExit(f"route.draft_pads {pid}: node must be a vertex strictly between its two cuts")
        for s in d.get("sealed") or []:
            if not (len(s) == 2 and all(len(p) == 2 for p in s)):
                raise SystemExit(f"route.draft_pads {pid}: a sealed cut is [[E, N], [E, N]]")
    return pads


def declaration(cfg: dict, pid: str) -> dict:
    for d in declarations(cfg):
        if d["id"] == pid:
            return d
    raise SystemExit(f"route.draft_pads declares no pad {pid!r}")


def lap_cut(points_xyz, k: int, node: int) -> dict:
    """The lap's transverse cut at vertex k: the line through it along its normal, the KEPT side the node's side (the
    pad's). {"p": (E, N), "n": unit vector into the kept side, "a", "b": the drawn ends, "vertex": k}"""
    m = len(points_xyz)
    pa, pk, pb = points_xyz[max(k - 1, 0)], points_xyz[k], points_xyz[min(k + 1, m - 1)]
    tx, tz = pb[0] - pa[0], pb[2] - pa[2]
    L = math.hypot(tx, tz) or 1.0
    tx, tz = tx / L, tz / L
    s = 1.0 if node > k else -1.0                     # into the pad: forward from the in cut, backward from the out cut
    p = (pk[0], pk[2])
    nx, nz = -tz, tx                                   # the cut line runs along the normal
    return {"p": p, "n": (s * tx, s * tz), "vertex": k,
            "a": (p[0] - nx * CUT_HALF_M, p[1] - nz * CUT_HALF_M), "b": (p[0] + nx * CUT_HALF_M, p[1] + nz * CUT_HALF_M)}


def sealed_cut(seg, node_en) -> dict:
    """A declared straight cut across a leg the lap does not drive; the kept side is the node's."""
    (ax, ay), (bx, by) = seg
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    if (node_en[0] - ax) * nx + (node_en[1] - ay) * ny < 0:
        nx, ny = -nx, -ny
    return {"p": (ax, ay), "n": (nx, ny), "a": (ax, ay), "b": (bx, by)}


def segment_band(a, b, gx, gy, w: float):
    """the points within ``w`` of the segment a-b, elementwise (numpy arrays or floats)"""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy or 1e-12
    t = ((gx - ax) * dx + (gy - ay) * dy) / L2
    t = t * (t > 0)
    t = t - (t - 1.0) * (t > 1.0)
    qx, qy = ax + t * dx, ay + t * dy
    return (gx - qx) ** 2 + (gy - qy) ** 2 <= w * w


def in_ring_grid(ring, gx, gy):
    """even-odd point-in-polygon, elementwise over numpy arrays (or floats)"""
    inside = (gx * 0) != 0
    for i in range(len(ring)):
        x0, y0 = ring[i - 1]
        x1, y1 = ring[i]
        if y0 == y1:
            continue
        cond = ((y0 > gy) != (y1 > gy)) & (gx < x0 + (gy - y0) * (x1 - x0) / (y1 - y0))
        inside = inside ^ cond
    return inside


def side(c: dict, x: float, y: float) -> float:
    """signed distance of (x, y) to a cut line, + on its kept side"""
    return (x - c["p"][0]) * c["n"][0] + (y - c["p"][1]) * c["n"][1]


def half_plane_mask(c: dict, gx, gy):
    """the kept side of a cut, elementwise (works on numpy arrays and on plain floats alike)"""
    return (gx - c["p"][0]) * c["n"][0] + (gy - c["p"][1]) * c["n"][1] >= 0.0


def trace_boundary(region, xs, ys) -> list[tuple[float, float]]:
    """The outer boundary of a 4-connected True region on a grid (region[row][col], row 0 = ys[0]), traced cell centre to
    cell centre (Moore neighbour tracing, Jacob's stop), counter-clockwise in E/N."""
    R, C = len(region), len(region[0])

    def on(r, c):
        return 0 <= r < R and 0 <= c < C and region[r][c]
    start = next(((r, c) for r in range(R) for c in range(C) if region[r][c]), None)
    if start is None:
        return []
    # the 8 neighbours clockwise from west (row increases downward = south)
    nb = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    ring = [start]
    cur, back = start, 0                      # entered the start cell from its west
    first_step = None
    for _ in range(4 * R * C):
        found = None
        for t in range(8):
            d = (back + 1 + t) % 8
            r2, c2 = cur[0] + nb[d][0], cur[1] + nb[d][1]
            if on(r2, c2):
                found = (r2, c2, d)
                break
        if found is None:
            break                             # an isolated single cell
        nxt = (found[0], found[1])
        step = (cur, nxt)
        if first_step is None:
            first_step = step
        elif step == first_step:
            break
        back = (found[2] + 4) % 8             # the neighbour we came from, seen from the new cell
        cur = nxt
        ring.append(cur)
    if len(ring) > 1 and ring[-1] == ring[0]:
        ring.pop()
    pts = [(xs[c], ys[r]) for r, c in ring]
    if ring_area(pts) < 0:
        pts.reverse()
    return pts


def ring_area(ring) -> float:
    """signed shoelace area (+ = counter-clockwise in E/N)"""
    a = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i - 1]
        x1, y1 = ring[i]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def _stations(ring):
    st = [0.0]
    for i in range(1, len(ring)):
        st.append(st[-1] + math.dist(ring[i - 1], ring[i]))
    return st, st[-1] + math.dist(ring[-1], ring[0])


def smooth_ring(ring, sigma_m: float, keep_on=(), pin=(), pin_m: float = 2.5) -> list[tuple[float, float]]:
    """Gaussian smoothing along a closed ring's arc length (the traced cell staircase out); a point that ends within ON_CUT_M
    of a cut SEGMENT is put back exactly on its line, so a cut edge stays straight. Points within pin_m of a ``pin`` cut
    (the lap's own cuts) are not smoothed: the smoothing would round the corner where the lap's edge meets its cut inward
    and leave the lane unpaved beside the seam (C18 0.17.2, v14197-14199).""" 
    if not ring:
        return []
    st, L = _stations(ring)
    n = len(ring)
    out = []
    reach = 3.0 * sigma_m
    for i in range(n):
        if any(segment_band(c["a"], c["b"], ring[i][0], ring[i][1], pin_m) for c in pin):
            out.append(snap(ring[i], keep_on))           # a lap cut's corner keeps its traced place (no rounding inward)
            continue
        sw = sx = sy = 0.0
        for j in range(n):
            d = abs(st[j] - st[i])
            d = min(d, L - d)
            if d > reach:
                continue
            w = math.exp(-0.5 * (d / sigma_m) ** 2)
            sw += w
            sx += w * ring[j][0]
            sy += w * ring[j][1]
        out.append(snap((sx / sw, sy / sw), keep_on))
    return out


def snap(p, cuts):
    """a point within ON_CUT_M of a cut SEGMENT put exactly on its line"""
    for c in cuts:
        s = side(c, *p)
        if abs(s) <= ON_CUT_M and segment_band(c["a"], c["b"], p[0], p[1], ON_CUT_M + 0.5):
            p = (p[0] - s * c["n"][0], p[1] - s * c["n"][1])
    return p


def resample_ring(ring, step_m: float) -> list[tuple[float, float]]:
    """equal arc-length points every ~step_m round a closed ring"""
    st, L = _stations(ring)
    k = max(3, int(round(L / step_m)))
    pts = ring + ring[:1]
    st = st + [L]
    out, j = [], 0
    for q in range(k):
        s = q * L / k
        while j + 1 < len(st) - 1 and st[j + 1] <= s:
            j += 1
        t = (s - st[j]) / max(1e-12, st[j + 1] - st[j])
        out.append((pts[j][0] + t * (pts[j + 1][0] - pts[j][0]), pts[j][1] + t * (pts[j + 1][1] - pts[j][1])))
    return out


def plane_height(pts) -> float | None:
    """The height at (0, 0) of the least-squares plane z = a + b dx + c dy through [(dx, dy, z), ...], refit once without
    points over PLANE_TRIM_M off it; None under PLANE_MIN_POINTS points."""
    def fit(P):
        if len(P) < PLANE_MIN_POINTS:
            return None
        n = len(P)
        sx = sum(p[0] for p in P); sy = sum(p[1] for p in P); sz = sum(p[2] for p in P)
        sxx = sum(p[0] * p[0] for p in P); syy = sum(p[1] * p[1] for p in P); sxy = sum(p[0] * p[1] for p in P)
        sxz = sum(p[0] * p[2] for p in P); syz = sum(p[1] * p[2] for p in P)
        A = [[n, sx, sy], [sx, sxx, sxy], [sy, sxy, syy]]
        B = [sz, sxz, syz]
        return _solve3(A, B)
    sol = fit(pts)
    if sol is None:
        return None
    a, b, c = sol
    kept = [p for p in pts if abs(p[2] - (a + b * p[0] + c * p[1])) <= PLANE_TRIM_M]
    sol2 = fit(kept)
    return (sol2 or sol)[0]


def _solve3(A, B):
    """Cramer's rule, None when singular"""
    def det(M):
        return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    D = det(A)
    if abs(D) < 1e-12:
        return None
    out = []
    for i in range(3):
        M = [row[:] for row in A]
        for r in range(3):
            M[r][i] = B[r]
        out.append(det(M) / D)
    return out


def deck_at(deck: dict, e: float, n: float) -> float | None:
    """The measured deck height at (e, n): bilinear on the pad file's grid, over the nodes that carry a height."""
    fx = (e - deck["e0"]) / deck["cell_m"]
    fy = (n - deck["n0"]) / deck["cell_m"]
    i0, j0 = int(math.floor(fx)), int(math.floor(fy))
    acc = wsum = 0.0
    for dj in (0, 1):
        for di in (0, 1):
            i, j = i0 + di, j0 + dj
            if not (0 <= i < deck["nx"] and 0 <= j < deck["ny"]):
                continue
            v = deck["y"][j][i]
            if v is None:
                continue
            w = (1 - abs(fx - i)) * (1 - abs(fy - j))
            acc += w * v
            wsum += w
    return acc / wsum if wsum > 1e-9 else None


def deck_near(deck: dict, e: float, n: float, reach_m: float = 3.0) -> float | None:
    """deck_at, else the nearest grid node that carries a height within reach_m (the asphalt's edge, where the ground
    points thin out), else None"""
    g = deck_at(deck, e, n)
    if g is not None:
        return g
    c = deck["cell_m"]
    i0, j0 = int(round((e - deck["e0"]) / c)), int(round((n - deck["n0"]) / c))
    r = int(math.ceil(reach_m / c))
    best, bv = None, None
    for dj in range(-r, r + 1):
        for di in range(-r, r + 1):
            i, j = i0 + di, j0 + dj
            if 0 <= i < deck["nx"] and 0 <= j < deck["ny"] and deck["y"][j][i] is not None:
                d = di * di + dj * dj
                if best is None or d < best:
                    best, bv = d, deck["y"][j][i]
    return bv if best is not None and math.sqrt(best) * c <= reach_m else None


FILL_REACH_M = (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0)   # the hole fill's growing search radii (the plane fit's own 2 m in the middle)
FILL_MIN_NODES = 12        # [invented] measured deck nodes a hole's plane needs (a 3 x 4 patch of the 0.5 m grid)


def deck_filled(deck: dict, ring, datum_m: float = 0.0, smooth_m: float | None = None) -> tuple[dict, dict]:
    """THE MEASURED DECK WITH ITS HOLES FILLED FROM ITSELF (ledger 0079 round D, opt-in ``lm_pads.deck``). The PC's deck
    is a plane per 0.5 m node over the ROAD-intensity class-2 points within 2 m (tools/draft_pad_outline.py); where
    crosswalk paint, a concrete gutter pan or a parked car leaves fewer than PLANE_MIN_POINTS such points the node is
    None. Inside the measured outline (``ring``, the lidar's own asphalt) a None node read through to the lap's removed
    ribbon in 0.2.1's try (tools/lm_pads_blend.py deck_z): 0.10-0.33 m off the lidar around it, the severe steps at
    50th/Ash, 50th/Dahlia and 48th/Colorado. Here each such node takes the least-squares plane through the measured
    nodes around it (the nearest FILL_REACH_M radius holding FILL_MIN_NODES): the lidar's own surface carried across
    the gap, slope and crown kept. Nodes outside the ring stay as measured (None stays None). ``datum_m`` is added to
    every node (the assembler's ROAD stands 0.10 m over its sampled ground: scripts-v021 build_loop_blend.py
    ``y + 0.10``, so a deck in the lap's datum stands the same 0.10 m over the lidar). Returns (deck, report)."""
    nx, ny, c = deck["nx"], deck["ny"], deck["cell_m"]
    Y = deck["y"]
    meas = [(i, j) for j in range(ny) for i in range(nx) if Y[j][i] is not None]
    cell = 4.0
    grid = {}
    for i, j in meas:
        grid.setdefault((int(i * c // cell), int(j * c // cell)), []).append((i, j))
    out = [[None if v is None else v + datum_m for v in row] for row in Y]
    filled = unfilled = 0
    reach_used = []
    for j in range(ny):
        for i in range(nx):
            if Y[j][i] is not None:
                continue
            e, n = deck["e0"] + i * c, deck["n0"] + j * c
            if not point_in_ring(e, n, ring):
                continue
            got = None
            for R in FILL_REACH_M:
                r = int(math.ceil(R / cell))
                gi, gj = int(i * c // cell), int(j * c // cell)
                pts = []
                for di in range(-r, r + 1):
                    for dj in range(-r, r + 1):
                        for a, b in grid.get((gi + di, gj + dj), ()):
                            dx, dy = (a - i) * c, (b - j) * c
                            if dx * dx + dy * dy <= R * R:
                                pts.append((dx, dy, Y[b][a]))
                if len(pts) >= FILL_MIN_NODES:
                    got = plane_height(pts)
                    if got is not None:
                        reach_used.append(R)
                        break
            if got is None:
                unfilled += 1
                continue
            out[j][i] = got + datum_m
            filled += 1
    moved = []
    if smooth_m:
        # THE LIDAR'S NOISE OUT (``smooth_m``, a Gaussian sigma): each node inside the ring becomes the Gaussian-weighted
        # mean of the ring's nodes within 3 sigma (inside only: the verge's fall and a curb face never pull the deck).
        # The 2 m plane per node jitters 1-6 cm from its neighbour where its trimmed point set changes (a slope change
        # over 3 % per metre: 0.2.1's try read 3.3 kinks /km on four pads against the lap's 0.41); the real asphalt is a
        # surface, so the move is recorded (p95 / max) against the survey's own vertical accuracy
        inside = [[point_in_ring(deck["e0"] + i * c, deck["n0"] + j * c, ring) and out[j][i] is not None
                   for i in range(nx)] for j in range(ny)]
        r = int(math.ceil(3.0 * smooth_m / c))
        w = {(di, dj): math.exp(-((di * c) ** 2 + (dj * c) ** 2) / (2.0 * smooth_m * smooth_m))
             for di in range(-r, r + 1) for dj in range(-r, r + 1)}
        sm = [row[:] for row in out]
        for j in range(ny):
            for i in range(nx):
                if not inside[j][i]:
                    continue
                num = den = 0.0
                for (di, dj), wt in w.items():
                    a, b = i + di, j + dj
                    if 0 <= a < nx and 0 <= b < ny and inside[b][a]:
                        num += wt * out[b][a]
                        den += wt
                sm[j][i] = num / den
                moved.append(abs(sm[j][i] - out[j][i]))
        out = sm
    new = dict(deck)
    new["y"] = out
    rep = {"filled": filled, "unfilled": unfilled, "datum_m": datum_m,
           "reach_max_m": max(reach_used) if reach_used else None}
    if moved:
        moved.sort()
        rep["smooth_m"] = smooth_m
        rep["smooth_moved_m"] = {"p50": round(moved[len(moved) // 2], 4), "p95": round(moved[int(0.95 * (len(moved) - 1))], 4),
                                 "max": round(moved[-1], 4), "nodes": len(moved)}
    return new, rep


def offset_ring(ring, d: float) -> list[list[float]]:
    """a counter-clockwise ring moved d outward at every vertex (along the mean of its two edges' outward normals)"""
    n = len(ring)
    out = []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = ring[i - 1], ring[i], ring[(i + 1) % n]
        nx, ny = 0.0, 0.0
        for (ax, ay), (bx, by) in (((x0, y0), (x1, y1)), ((x1, y1), (x2, y2))):
            L = math.hypot(bx - ax, by - ay) or 1.0
            nx += (by - ay) / L
            ny += -(bx - ax) / L
        L = math.hypot(nx, ny) or 1.0
        out.append([round(x1 + d * nx / L, 3), round(y1 + d * ny / L, 3)])
    return out


def point_in_ring(x: float, y: float, ring) -> bool:
    """even-odd point in polygon"""
    inside = False
    for i in range(len(ring)):
        x0, y0 = ring[i - 1]
        x1, y1 = ring[i]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


SEAM_FADE_M = 12.0          # [invented] a seam's departure from the measured ground fades over this far into the deck


SEAM_STEP_M = 0.25          # the seam's departure is sampled this often along the row
SEAM_MAX_SLOPE = 0.035      # [invented] a seam fade never climbs faster than this (drive_test's severe step is 6 cm in 1 m)


def seam_profile(rows, deck_fn, fade_m: float = SEAM_FADE_M, max_slope: float = SEAM_MAX_SLOPE):
    """Per cut: the ribbon row's own cross-section (its vertices, ordered along the row, linear between them -- the
    engine's cols=1 ribbon is straight across) and its departure from the measured ground at each vertex. Returns the
    list the deck height reads (``seam_offset``). ``rows`` = [(cut dict with p / n, [(x, y, z), ...]), ...];
    ``deck_fn(x, y)`` the measured ground or None."""
    out = []
    for c, row in rows:
        ux, uy = -c["n"][1], c["n"][0]
        verts = sorted(row, key=lambda v: (v[0] - c["p"][0]) * ux + (v[1] - c["p"][1]) * uy)
        # sampled every SEAM_STEP_M along the row, the row's own height linear between its vertices: the departure is
        # the straight ribbon row minus the measured (crowned) ground AT EACH POINT, so the deck is the row exactly
        # (0.17.2 run d: the edge departures interpolated across a crowned road left 0.12 m at the lane's middle)
        ts, rs = [], []
        pts = []
        for (x0, y0, z0), (x1, y1, z1) in zip(verts, verts[1:]):
            n = max(1, int(math.ceil(math.dist((x0, y0), (x1, y1)) / SEAM_STEP_M)))
            pts += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, z0 + (z1 - z0) * i / n) for i in range(n)]
        pts.append(verts[-1])
        for x, y, z in pts:
            g = deck_fn(x, y)
            ts.append((x - c["p"][0]) * ux + (y - c["p"][1]) * uy)
            rs.append(z - g if g is not None else 0.0)
        out.append({"c": c, "u": (ux, uy), "t": ts, "r": rs, "fade": fade_m})
    # the fade is as long as the departure needs (a raised cosine's steepest slope is r * pi / (2 * fade)), up to 45 % of
    # the way to the other cut: C18's out-cut stands 0.835 m over the real road (the engine line climbing to the lid)
    if len(out) == 2:
        span = math.dist(out[0]["c"]["p"], out[1]["c"]["p"])
        for s_ in out:
            need = max(abs(r) for r in s_["r"]) * math.pi / (2.0 * max_slope)
            s_["fade"] = max(fade_m, min(need, 0.45 * span))
    return out


def seam_offset(prof, x: float, y: float) -> float:
    """The deck's departure from the measured ground at (x, y): each cut's row departure (linear along the row, held
    past its ends) faded by a raised cosine with the distance into the pad from the row line -- exact on the row (the
    weld), the measured ground FADE_M in. A crown the straight ribbon row lacks (0.17.2: 0.13-0.15 m at the seams)
    and an engine line off the real road (C18's out-cut, 0.39 m) both come in over the fade, never as a step."""
    off = 0.0
    for s_ in prof:
        c = s_["c"]
        d = side(c, x, y)
        t = (x - c["p"][0]) * s_["u"][0] + (y - c["p"][1]) * s_["u"][1]
        ts, rs = s_["t"], s_["r"]
        if s_.get("near_row") and not ts[0] <= t <= ts[-1]:
            # a pad declared seam "row" (ledger 0078 round 13, a switchback): beyond the row's own ends the fade runs from
            # the row itself, not from its infinite line; a hairpin's other leg lies behind the in-cut's line, and took
            # that row's whole departure there (Douglas Creek: +0.2 m beside the out-cut's row)
            d = math.hypot(d, t - min(max(t, ts[0]), ts[-1]))
        if d >= s_["fade"]:
            continue
        w = 1.0 if d <= 0.0 else 0.5 * (1.0 + math.cos(math.pi * d / s_["fade"]))
        if t <= ts[0]:
            r = rs[0]
        elif t >= ts[-1]:
            r = rs[-1]
        else:
            k = max(i for i in range(len(ts) - 1) if ts[i] <= t)
            f = (t - ts[k]) / max(1e-9, ts[k + 1] - ts[k])
            r = rs[k] + f * (rs[k + 1] - rs[k])
        off += w * r
    return off


def seam_offset_multi(prof, x: float, y: float) -> float:
    """seam_offset for MORE than the lap's two rows (opt-in, lm_pads.arms "streets", ledger 0079 0.2.3: the street arms'
    end rows are seams too). Each row's raised-cosine weight w_i as in seam_offset; a profile marked "lateral" (an arm:
    its row line is short and the pad runs on past its ends) also fades past the row's ends over the same length. The
    rows share the departure where their fades overlap: W x sum(a_i r_i) / sum(a_i), W = 1 - prod(1 - w_j),
    a_i = w_i prod_{j != i}(1 - w_j) -- exact on every row (w_i = 1 silences the others), w r where one fade alone
    reaches, and seam_offset's sum wherever the fades do not overlap."""
    ws, rs = [], []
    for s_ in prof:
        c = s_["c"]
        d = side(c, x, y)
        if d >= s_["fade"]:
            continue
        w = 1.0 if d <= 0.0 else 0.5 * (1.0 + math.cos(math.pi * d / s_["fade"]))
        t = (x - c["p"][0]) * s_["u"][0] + (y - c["p"][1]) * s_["u"][1]
        ts, rr = s_["t"], s_["r"]
        if s_.get("lateral"):
            past = max(ts[0] - t, t - ts[-1], 0.0)
            if past >= s_["fade"]:
                continue
            w *= 0.5 * (1.0 + math.cos(math.pi * past / s_["fade"]))
        if t <= ts[0]:
            r = rr[0]
        elif t >= ts[-1]:
            r = rr[-1]
        else:
            k = max(i for i in range(len(ts) - 1) if ts[i] <= t)
            f = (t - ts[k]) / max(1e-9, ts[k + 1] - ts[k])
            r = rr[k] + f * (rr[k + 1] - rr[k])
        if w > 0.0:
            ws.append(w)
            rs.append(r)
    if not ws:
        return 0.0
    full = [r for w, r in zip(ws, rs) if w >= 1.0]
    if len(full) > 1:
        return sum(full) / len(full)
    a = []
    for i in range(len(ws)):
        p = ws[i]
        for j in range(len(ws)):
            if j != i:
                p *= 1.0 - ws[j]
        a.append(p)
    W = 1.0
    for w in ws:
        W *= 1.0 - w
    W = 1.0 - W
    S = sum(a)
    return W * sum(ai * r for ai, r in zip(a, rs)) / S if S > 0 else 0.0


def seam_blend(x: float, y: float, seams, power: float = 2.0) -> float:
    """The deck's departure from the measured ground at (x, y): the seams' own departures [(x, y, residual), ...]
    inverse-distance weighted -- exact on a seam vertex, smooth between, so the deck welds to the ribbon rows and
    follows the lidar ground inside."""
    num = den = 0.0
    for sx, sy, r in seams:
        d2 = (x - sx) ** 2 + (y - sy) ** 2
        if d2 < 1e-12:
            return r
        w = 1.0 / d2 ** (power / 2.0)
        num += w * r
        den += w
    return num / den if den else 0.0


# ---- the lap arm (ledger 0078 round 7: moved here from 0.17.2's author_draft_pads_blend.py, pure, so the Lake Murray
# engine's tools/lm_pads_blend.py and any other author share one splice) ------------------------------------------------

def row_cut(row, node_en, reach=CUT_HALF_M):
    """the ribbon row's own line as a cut: through its two end vertices, kept side the node's, drawn +-reach"""
    (ax, ay), (bx, by) = (row[0][0], row[0][1]), (row[-1][0], row[-1][1])
    c = sealed_cut(((ax, ay), (bx, by)), node_en)
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    c["a"], c["b"] = (mx - ux * reach, my - uy * reach), (mx + ux * reach, my + uy * reach)
    return c


def _project(c, q):
    s_ = side(c, *q)
    return (q[0] - s_ * c["n"][0], q[1] - s_ * c["n"][1])


def splice_rows(ring, cuts_rows):
    """the measured ring with each cut's run along its MEASURED line replaced by the ribbon's ROW: the asphalt's two
    crossings projected onto the row's own line, the row's vertices between them, and any outline point left on the
    lap's side of the row line near it dropped (on a curve the two lines differ by a few degrees: that wedge was
    0.17.2's sliver / hole at every seam)"""
    out = list(ring)
    for c, cr, row in cuts_rows:
        on = [i for i, q in enumerate(out) if abs(side(c, *q)) <= 0.05
              and segment_band(c["a"], c["b"], q[0], q[1], 0.5)]
        if not on:
            raise SystemExit(f"[pads] cut at v{c['vertex']}: the outline never runs along it (measure again)")
        on_set, runs, seen = set(on), [], set()
        for i in on:
            if i in seen:
                continue
            j = i
            while (j - 1) % len(out) in on_set and (j - 1) % len(out) not in seen and (j - 1) % len(out) != i:
                j = (j - 1) % len(out)
            run = []
            k = j
            while k in on_set and k not in seen:
                run.append(k)
                seen.add(k)
                k = (k + 1) % len(out)
            runs.append(run)
        run = max(runs, key=len)
        a, b = _project(cr, out[run[0]]), _project(cr, out[run[-1]])
        # the row's order from the outline on either side of the run (the point before it to the point after it): a
        # short run (the asphalt narrower than the ribbon: C18's 5 m ramp) cannot be trusted for the direction
        pp, pn = out[(run[0] - 1) % len(out)], out[(run[-1] + 1) % len(out)]
        ux, uy = pn[0] - pp[0], pn[1] - pp[1]
        rv = sorted(row, key=lambda v: (v[0] - pp[0]) * ux + (v[1] - pp[1]) * uy)
        if (a[0] - pp[0]) * ux + (a[1] - pp[1]) * uy > (b[0] - pp[0]) * ux + (b[1] - pp[1]) * uy:
            a, b = b, a
        # the row's own vertices always stay (they are the weld); a projected crossing within 5 cm of a row end is the
        # row end itself
        rowpts = [(v[0], v[1]) for v in rv]
        clean = list(rowpts)
        rl = math.dist(rowpts[0], rowpts[-1]) or 1e-9
        ux, uy = (rowpts[-1][0] - rowpts[0][0]) / rl, (rowpts[-1][1] - rowpts[0][1]) / rl
        ta = (a[0] - rowpts[0][0]) * ux + (a[1] - rowpts[0][1]) * uy
        tb = (b[0] - rowpts[0][0]) * ux + (b[1] - rowpts[0][1]) * uy
        # a crossing beyond the row's end (the asphalt wider than the ribbon there) stays; one INSIDE the row's span
        # (the asphalt narrower than the ribbon: C14's out-cut) is dropped, or the outline would double back along the
        # row (a zero-width spike the triangulation drops together with the row's end vertex)
        if ta < -0.05:
            clean.insert(0, a)
        if tb > rl + 0.05:
            clean.append(b)
        s_, e_ = run[0], run[-1]
        if s_ <= e_:
            out = out[:s_] + clean + out[e_ + 1:]
            new_idx = set(range(s_, s_ + len(clean)))
        else:
            out = clean + out[e_ + 1:s_]
            new_idx = set(range(len(clean)))
        out = [q for i, q in enumerate(out) if i in new_idx or not (
            side(cr, *q) < -0.02 and segment_band(cr["a"], cr["b"], q[0], q[1], 6.0))]
    protect = {(round(v[0], 6), round(v[1], 6)) for _, _, row in cuts_rows for v in row}
    return untie(out, protect)


def _seg_x(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def untie(ring, protect=frozenset(), max_rounds=200):
    """a simple polygon: wherever two non-adjacent edges cross, the smaller loop between them is cut out at the
    crossing (a spur the smoothing folded back, or the seam wedge); delaunay_2d_cdt's 'inside' on a crossed ring
    leaves holes in the deck (0.17.2: C15 at 16,565 m, C18 at 24,279 m)"""
    r = list(ring)
    for _ in range(max_rounds):
        n = len(r)
        hit = None
        for i in range(n):
            a1, a2 = r[i], r[(i + 1) % n]
            for j in range(i + 2, n):
                if (j + 1) % n == i:
                    continue
                x = _seg_x(a1, a2, r[j], r[(j + 1) % n])
                if x is not None:
                    hit = (i, j, x)
                    break
            if hit:
                break
        if not hit:
            return r
        i, j, x = hit
        loop_a = r[i + 1:j + 1]                               # cut this way round: the inside run goes
        loop_b = r[j + 1:] + r[:i + 1]                        # or the other way round
        hits_a = sum((round(q[0], 6), round(q[1], 6)) in protect for q in loop_a)
        hits_b = sum((round(q[0], 6), round(q[1], 6)) in protect for q in loop_b)
        if (hits_a, len(loop_a)) <= (hits_b, len(loop_b)):
            if hits_a:
                raise SystemExit("[pads] the outline crosses itself through a seam row: measure again")
            r = r[:i + 1] + [x] + r[j + 1:]
        else:
            if hits_b:
                raise SystemExit("[pads] the outline crosses itself through a seam row: measure again")
            r = [x] + r[i + 1:j + 1]
    raise SystemExit("[pads] the outline would not untie into a simple polygon")

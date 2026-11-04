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
        if d >= s_["fade"]:
            continue
        w = 1.0 if d <= 0.0 else 0.5 * (1.0 + math.cos(math.pi * d / s_["fade"]))
        t = (x - c["p"][0]) * s_["u"][0] + (y - c["p"][1]) * s_["u"][1]
        ts, rs = s_["t"], s_["r"]
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

"""Build the road ribbon (1ROAD) and the grass heightfield mesh (GRASS).

The ribbon is swept along the projected centerline using per-vertex width; the grass mesh is the
triangulated terrain grid. All inputs are local ENU metres (X-east, Y-up, Z-north). Meshes are
returned as ``{"vertices": [(x,y,z)...], "tris": [(a,b,c)...]}`` with 0-based triangle indices.
"""

from __future__ import annotations

import math

from scripts.geometry import nodedbg

Vertex = tuple[float, float, float]


def _uniq_n(pts: list[Vertex], closed: bool) -> int:
    """Number of UNIQUE vertices: a closed centerline repeats its first point as its last, and
    every wrap-around index below must skip that duplicate. With the raw length, vertex 0's
    backward neighbour is pts[-1] — which IS vertex 0 — so the centered difference collapses to a
    one-sided one and the cross-section at the seam is swept off a half tangent. Measured on Lake
    Murray: a 0.78 m step at station 13476 of a 13478 m lap, right on the start/finish line, plus
    both remaining ground-on-top hits at that same point. Same defect class as the elevation seam
    (heightfield.snap_to_ground), one mesh stage later."""
    n = len(pts)
    if closed and n > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6:
        return n - 1
    return n


def _horiz_tangent(pts: list[Vertex], i: int, closed: bool) -> tuple[float, float]:
    """Unit tangent in the horizontal X-Z plane at vertex i (centered difference)."""
    n = _uniq_n(pts, closed)
    a = pts[(i - 1) % n] if closed else pts[max(0, i - 1)]
    b = pts[(i + 1) % n] if closed else pts[min(len(pts) - 1, i + 1)]
    dx, dz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L



def _signed_curvature(pts: list[Vertex], i: int, closed: bool) -> float:
    """Signed horizontal curvature (1/m) at vertex i; +ve = turning left. Used to stop cross-sections
    PLEATING: when a lateral offset exceeds the local curve radius, consecutive sections sweep
    backwards over each other and the ribbon lays multiple road layers at one (x,z) — five stacked
    decks inside the Lariat's flared hogback curve read as 0.3-0.6 m random steps."""
    n = _uniq_n(pts, closed)
    a = pts[(i - 1) % n] if closed else pts[max(0, i - 1)]
    b = pts[i]
    c = pts[(i + 1) % n] if closed else pts[min(len(pts) - 1, i + 1)]
    v1x, v1z = b[0] - a[0], b[2] - a[2]
    v2x, v2z = c[0] - b[0], c[2] - b[2]
    l1, l2 = math.hypot(v1x, v1z), math.hypot(v2x, v2z)
    if l1 < 1e-9 or l2 < 1e-9:
        return 0.0
    cross = v1x * v2z - v1z * v2x
    dot = v1x * v2x + v1z * v2z
    ang = math.atan2(cross, dot)
    return ang / ((l1 + l2) / 2.0)


def _cap_offset(off: float, k: float, frac: float = 0.9) -> float:
    """Cap a LEFT-positive lateral offset so it never reaches the inside curve centre."""
    if k > 1e-6 and off > 0:          # turning left: left side is inside
        return min(off, frac / k)
    if k < -1e-6 and off < 0:         # turning right: right side is inside
        return max(off, -frac / -k)
    return off


def road_ribbon(centerline_m: list[Vertex], widths_m: list[float], *, tile_m: float = 4.0,
                bank_at=None, cols: int = 1) -> dict:
    """Sweep a drivable ribbon (1ROAD) along the centerline, offsetting ±width/2 per vertex.

    Also emits per-vertex UVs (parallel to vertices) in metres/``tile_m``: U across the width
    (±half/tile), V along the lap (cumulative arc/tile) — so a seamless asphalt tiles correctly down
    the road and a detail/markings layer can key off the same coordinates.

    ``bank_at`` (station_m -> roll radians) rolls the cross-section: a vertex at lateral offset ``o``
    (left +ve) is lifted by ``o*tan(bank)`` so the road banks as one plane (see ``profile.py``).

    ``cols`` splits each cross-section into that many lateral columns. With the default 1 a row is a
    single edge-to-edge quad, and where the bank changes between rows (a camber ramp) that quad
    twists: its diagonal sags by half the edge lift difference, about 10 cm on a 17 m road ramping
    6 deg over 20 m at 3 m rows (Exotics Racing T2, 2026-10-28). The sag falls as 1/cols. 1 is
    byte-identical to the old ribbon."""
    pts = centerline_m
    n = len(pts)
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    m = n - 1 if closed else n  # unique cross-sections (drop the duplicate closing vertex)
    verts: list[Vertex] = []
    uvs: list[tuple[float, float]] = []
    arc = 0.0
    for i in range(m):
        if i > 0:
            arc += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
        x, y, z = pts[i]
        tx, tz = _horiz_tangent(pts, i, closed)
        nx, nz = -tz, tx  # left normal (tangent rotated +90° in X-Z)
        half = widths_m[i] / 2.0
        k = _signed_curvature(pts, i, closed)
        half_l = _cap_offset(half, k)
        half_r = -_cap_offset(-half, k)
        tb = math.tan(bank_at(arc)) if bank_at else 0.0
        if cols <= 1:
            verts.append((x + nx * half_l, y + half_l * tb, z + nz * half_l))  # left  -> 2i  (outside/raised)
            verts.append((x - nx * half_r, y - half_r * tb, z - nz * half_r))  # right -> 2i+1
            uvs.append((half_l / tile_m, arc / tile_m))        # left
            uvs.append((-half_r / tile_m, arc / tile_m))       # right
        else:
            for c in range(cols + 1):                          # left edge (c=0) -> right edge (c=cols)
                o = half_l - (half_l + half_r) * c / cols
                verts.append((x + nx * o, y + o * tb, z + nz * o))
                uvs.append((o / tile_m, arc / tile_m))
    tris: list[tuple[int, int, int]] = []
    last = m if closed else m - 1
    if cols <= 1:
        for i in range(last):
            j = (i + 1) % m
            l0, r0, l1, r1 = 2 * i, 2 * i + 1, 2 * j, 2 * j + 1
            tris.append((l0, r0, r1))
            tris.append((l0, r1, l1))
    else:
        k = cols + 1
        for i in range(last):
            j = (i + 1) % m
            for c in range(cols):
                l0, r0, l1, r1 = k * i + c, k * i + c + 1, k * j + c, k * j + c + 1
                tris.append((l0, r0, r1))
                tris.append((l0, r1, l1))
    return {"vertices": verts, "uvs": uvs, "tris": tris}


def road_shoulder(centerline_m: list[Vertex], widths_m: list[float], *, lift: float = 0.1,
                  verge_w: float = 2.5, tile_m: float = 4.0, bank_at=None, ground_drop: float = 0.0,
                  ground=None, ratio: float = 2.0, max_w: float = 60.0,
                  fill_apron: bool = False, bank_hold: bool = False) -> dict:
    """A graded **verge + embankment** that ramps each road edge down (fill) or up (cut) to the REAL
    ground, so the road reads like a real shouldered/embanked road instead of a ribbon floating on a
    hard edge. Three points out from the lane edge: inner lip (road edge, ``lift`` proud) → a short
    ``verge_w`` band just below it (the gentle drivable band) → a GROUND-MEET point DRAPED onto
    ``ground(x,z)`` at a ``ratio``:1 slope, so the outer edge sits flush on the terrain however far
    below/above the road it is (no floating ribbon edge, no cliff). Without ``ground`` it falls back to
    the old two-point verge at ``road_edge − ground_drop``. Physical (``1GRASS_*`` in build_mesh)."""
    pts = centerline_m
    n = len(pts)
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    m = n - 1 if closed else n
    verts: list[Vertex] = []
    uvs: list[tuple[float, float]] = []
    tris: list[tuple[int, int, int]] = []
    P = 4 if ground is not None else 2   # 4th point = the BURIED HEM (sheet edge sealed into dirt)
    sections: dict = {1.0: [], -1.0: []}   # per-station construction metadata (selector output)
    for side in (1.0, -1.0):
        rows: list[int] = []
        arc = 0.0
        for i in range(m):
            if i > 0:
                arc += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
            x, y, z = pts[i]
            tx, tz = _horiz_tangent(pts, i, closed)
            nx, nz = -tz * side, tx * side  # outward normal on this side
            k = _signed_curvature(pts, i, closed)
            half = widths_m[i] / 2.0
            def _cap(o):                       # offsets are along +n*side; convert to left-signed
                return abs(_cap_offset(o * side, k))
            tb = math.tan(bank_at(arc)) if bank_at else 0.0
            r = len(verts)
            inner_y = y + lift + side * half * tb
            verts.append((x + nx * _cap(half), inner_y, z + nz * _cap(half)))                 # inner lip (road edge)
            uvs.append((0.0, arc / tile_m))
            if ground is not None:
                verge_y = y + side * (half + verge_w) * tb - ground_drop          # gentle band just off the edge
                verts.append((x + nx * _cap(half + verge_w), verge_y, z + nz * _cap(half + verge_w)))
                uvs.append((0.5, arc / tile_m))
                gy0 = ground(x + nx * _cap(half + verge_w), z + nz * _cap(half + verge_w))
                # BENCH EARTHWORKS (Kevin: "we cut roads INTO mountains, out of the ridges — not
                # stuck on the outside"): the transition is ASYMMETRIC like real construction.
                # CUT (ground above the bench): a steep 0.75:1 excavated face climbing into the
                # hill. FILL (ground below): the gentle ratio:1 embankment descending to natural.
                _cutting = gy0 > verge_y
                _drop = abs(verge_y - gy0)
                # CONSTRUCTION SELECTOR (docs/ROAD-CONSTRUCTION.md four-condition rule): pick the
                # cheapest condition that closes the gap. CUT: steep 0.75:1 excavated face into the
                # hill. FILL: gentle ratio:1 while small (urban lawns); >1.5 m steepens to 0.75:1.
                # WALL: fill drop > 4 m exceeds what earth can carry — a dry-stone RETAINING WALL
                # at 1:6 batter (near-vertical, the 1913 Lariat pattern; build_mesh skins it in
                # RETWALL stone). Bridges are already handled upstream by the bridge detector.
                _wall = (not _cutting) and _drop > 4.0
                # FILL GRADE vs THE GATE (ledger 0025): the drive gate budgets 24% max grade in
                # its excursion band, but "gentle ratio:1" at the default 2.0 is a 50% face — the
                # builder violated its own gate on every embankment toe (nine constant 0.16 m
                # steps at the rim line on imi). Shallow fills now grade at 4.5:1 (22%): a 0.4 m
                # toe widens by ~1 m and the whole face passes inside the band.
                _steep_fill = (not _cutting) and _drop > 1.2 and not fill_apron
                _slope_r = (1.0 / 6.0) if _wall else (0.75 if (_cutting or _steep_fill) else max(4.5, ratio))
                # THE COMPLETE SELECTOR/GATE AGREEMENT (ledger 0025, 27 builds of evidence):
                # shallow fill (<1.2 m) grades GENTLE at 4.5:1 (22%) — legal inside the drive
                # gate's 24% band, narrow enough not to pleat corners (always-4.5 swept 10 m+
                # sheets across the 302.5 corner and built sawtooth hills). Deep fill (>=1.2 m)
                # stays 0.75:1 but earns a stone PARAPET (warrant lowered to match), and the
                # gate exempts guarded drops. >4 m keeps the retaining wall.
                # ``fill_apron`` (tarmac tracks, 0025 closing): the deep-fill "steep + parapet
                # + exemption" design never once functioned end-to-end — the metadata parapets
                # built 0 verts at every warrant tried, and the exemption was dead code until
                # 0027. On a PAVED track the gate is also right to demand an apron (its own
                # doctrine: "run-off there is a flat apron, so any drop really is a ledge") —
                # Pueblo's 12 residual gated drops were all this band's fill faces, starting on
                # the shoulder's own quads where no lip can legally stand. So on tarmac the
                # whole 0-4 m fill range grades at 4.5:1 (22%); cuts stay 0.75:1 (the always-4.5
                # pleating came from grading a CUT corner), >4 m keeps the retaining wall, and
                # unpaved tracks keep their steep rally-stage character exactly as the gate
                # keeps its relaxed unpaved thresholds.
                extra = min(max_w, max(verge_w if not _wall else 0.6, _drop * _slope_r))
                o = _cap(half + verge_w + extra)
                _my = ground(x + nx * o, z + nz * o)
                # THE FACE GRADE IS MEASURED AT THE MEET, NOT AT THE SIZING SAMPLE (0025
                # closing): ``_drop`` reads ground at the verge, but the sheet lands at
                # verge+extra — where natural ground can sit far lower. Pueblo's staircases
                # were 30-50% faces built exactly this way: extra floored at verge_w while
                # the terrain kept falling beyond the sample, so no _slope_r value changed
                # the mesh by a byte. On fill, re-size against the drop where the sheet
                # actually lands until the face respects the selected slope — terrain
                # gentler than the face converges in a few rounds; max_w caps runaways.
                if not _cutting and not _wall:
                    for _ in range(6):
                        _mdrop = verge_y - _my
                        if _mdrop <= 0 or extra >= max_w or _mdrop * _slope_r <= extra + 0.05:
                            break
                        extra = min(max_w, _mdrop * _slope_r)
                        o = _cap(half + verge_w + extra)
                        _my = ground(x + nx * o, z + nz * o)
                verts.append((x + nx * o, _my, z + nz * o))   # ground meet (draped)
                uvs.append((1.0, arc / tile_m))
                sections[1.0 if side > 0 else -1.0].append({
                    "i": i, "cutting": _cutting, "drop": round(_drop, 2), "wall": _wall,
                    "verge": (x + nx * _cap(half + verge_w), verge_y, z + nz * _cap(half + verge_w)),
                    "meet": verts[-1], "n": (nx, nz), "arc": arc})
                # BURIED HEM: one more metre out and 0.8 m INTO the dirt — the sheet's edge ends
                # inside the terrain, not balanced on an interpolated line, so no grid-resolution
                # or interp mismatch can ever open daylight under the lip.
                oh = _cap(half + verge_w + extra + 1.0)
                verts.append((x + nx * oh, ground(x + nx * oh, z + nz * oh) - 0.8, z + nz * oh))
                uvs.append((1.0, arc / tile_m))
            else:
                # bank_hold: the verge stays at the banked EDGE's height instead of carrying the bank
                # plane on past it (natural ground: the lidar's real verge flattens off the bowl's edge)
                _vo = half if bank_hold else half + verge_w
                verts.append((x + nx * (half + verge_w), y + side * _vo * tb - ground_drop, z + nz * (half + verge_w)))
                uvs.append((1.0, arc / tile_m))
            rows.append(r)
        last = m if closed else m - 1
        for k in range(last):
            p = rows[k]
            q = rows[(k + 1) % m]
            for u in range(P - 1):
                tris.append((p + u, p + u + 1, q + u + 1))
                tris.append((p + u, q + u + 1, q + u))
    return {"vertices": verts, "uvs": uvs, "tris": tris, "sections": sections}


def curb_sidewalk(centerline_m: list[Vertex], widths_m: list[float], *, lift: float = 0.1,
                  curb_h: float = 0.15, curb_face_w: float = 0.08, sidewalk_w: float = 1.5,
                  grade_w: float = 1.0, grass_clearance: float = 0.25, tile_m: float = 2.0,
                  bank_at=None, ground=None, ratio: float = 2.0, max_grade_w: float = 60.0,
                  roll_flags=None) -> dict:
    """A continuous urban edge swept along BOTH road sides as ONE strip so road, curb, sidewalk and
    grass share seam vertices and nothing can hover. Per side, the cross-section is five profile points
    out from the lane edge:
      0  lane edge    — identical to the road-ribbon edge (road height, ``lift`` proud) → road↔curb meets
      1  curb top     — raised ``curb_h`` over a slight ``curb_face_w`` batter (mountable, not a wall)
      2  sidewalk back— flat walkway ``sidewalk_w`` wide at curb-top height
      3  slope start  — a short ``grade_w`` verge dropping just below the sidewalk (the gentle band)
      4  GROUND MEET  — an EMBANKMENT point DRAPED onto the actual grass surface: it marches outward at a
                        ``ratio``:1 fill/cut slope until it reaches ``ground(x,z)`` (the graded terrain),
                        so the edge sits flush on the ground however far below the road it is — no float,
                        no shadow-casting gap, at road resolution (independent of the coarse grass grid).
    Without ``ground`` it falls back to the old fixed ``road_edge − grass_clearance`` lip. Physical
    (``1KERB_sidewalk``). UVs: U across the profile, V along the road (m/``tile_m``)."""
    pts = centerline_m
    n = len(pts)
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    m = n - 1 if closed else n
    fixed = [(0.0, lift), (curb_face_w, lift + curb_h),
             (curb_face_w + sidewalk_w, lift + curb_h),
             (curb_face_w + sidewalk_w + grade_w, -grass_clearance)]   # points 0..3 (relative to banked edge)
    sidewalk_off = curb_face_w + sidewalk_w + grade_w
    P = 6 if ground is not None else 5   # 6th point = buried hem
    verts: list[Vertex] = []
    uvs: list[tuple[float, float]] = []
    tris: list[tuple[int, int, int]] = []
    for side in (1.0, -1.0):
        rows: list[int] = []
        arc = 0.0
        for i in range(m):
            if i > 0:
                arc += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
            x, y, z = pts[i]
            tx, tz = _horiz_tangent(pts, i, closed)
            nx, nz = -tz * side, tx * side  # outward normal on this side
            k = _signed_curvature(pts, i, closed)
            half = widths_m[i] / 2.0
            def _cap(o):                       # offsets are along +n*side; convert to left-signed
                return abs(_cap_offset(o * side, k))
            edge_bank = side * half * (math.tan(bank_at(arc)) if bank_at else 0.0)
            base_y = y + edge_bank
            r = len(verts)
            # ROLLED CURB through junction flares (roll_flags[i]): where the flared roadway
            # crosses the sidewalk line, the curb rolls to a 2-4 cm apron lip (Commerce City
            # driveway spec) instead of standing as a 15 cm wall inside the mouth.
            _roll = bool(roll_flags[i]) if roll_flags is not None else False
            for off, h in fixed:
                o = half + off
                hh = (min(h, 0.03) if h >= 0 else h) if _roll else h
                verts.append((x + nx * o, base_y + hh, z + nz * o))
                uvs.append((off / sidewalk_off, arc / tile_m))
            # point 4: drape onto the ground at a fill/cut slope
            verge_y = base_y - grass_clearance             # height at the slope-start point (3)
            if ground is not None:
                gy0 = ground(x + nx * (half + sidewalk_off + grade_w), z + nz * (half + sidewalk_off + grade_w))
                extra = max(grade_w, abs(verge_y - gy0) * ratio)
                extra = min(extra, max_grade_w)
                o4 = half + sidewalk_off + extra
                g4 = ground(x + nx * o4, z + nz * o4)
                verts.append((x + nx * o4, g4, z + nz * o4))
                # BURIED HEM (same as road_shoulder): seal the sheet edge into the dirt
                o5 = _cap(half + sidewalk_off + grade_w + 1.0) if callable(globals().get('_cap')) else o4 + 1.0
                o5 = o4 + 1.0
                verts.append((x + nx * o5, ground(x + nx * o5, z + nz * o5) - 0.8, z + nz * o5))
                uvs.append((1.0, arc / tile_m))
                uvs.append(((sidewalk_off + extra) / sidewalk_off, arc / tile_m))
            else:
                o4 = half + sidewalk_off + grade_w
                verts.append((x + nx * o4, verge_y, z + nz * o4))
                uvs.append(((sidewalk_off + grade_w) / sidewalk_off, arc / tile_m))
            rows.append(r)
        last = m if closed else m - 1
        for k in range(last):
            a = rows[k]
            b = rows[(k + 1) % m]
            for p in range(P - 1):                      # curb face, sidewalk top, verge, embankment
                tris.append((a + p, a + p + 1, b + p + 1))
                tris.append((a + p, b + p + 1, b + p))
    return {"vertices": verts, "uvs": uvs, "tris": tris}


def _road_surface_samples(centerline_m: list[Vertex], widths_m: list[float] | None, bank_at=None):
    """Centre + both edge points per station, each tagged with its lap index. Grading to these — not
    just the centreline — makes the terrain meet the road at its real edges; with ``bank_at`` the edge
    samples carry the banked height (left = +o*tan, right = -o*tan) so the grass meets a cambered edge."""
    n = len(centerline_m)
    closed = abs(centerline_m[0][0] - centerline_m[-1][0]) < 1e-6 and abs(centerline_m[0][2] - centerline_m[-1][2]) < 1e-6
    out: list[tuple[float, float, float, int]] = []
    arc = 0.0
    for i, (x, y, z) in enumerate(centerline_m):
        if i > 0:
            arc += math.hypot(x - centerline_m[i - 1][0], z - centerline_m[i - 1][2])
        out.append((x, y, z, i))
        if widths_m:
            tx, tz = _horiz_tangent(centerline_m, i, closed)
            nx, nz = -tz, tx
            h = widths_m[i] / 2.0
            tb = math.tan(bank_at(arc)) if bank_at else 0.0
            out.append((x + nx * h, y + h * tb, z + nz * h, i))   # left edge (raised when bank>0)
            out.append((x - nx * h, y - h * tb, z - nz * h, i))   # right edge
    return out, n


def conform_terrain_to_road(grid_xyz: list[list[Vertex]], centerline_m: list[Vertex],
                            widths_m: list[float] | None = None,
                            *, corridor: float = 12.0, blend: float = 12.0, bank_at=None,
                            target: str = "nearest", extra_roads=None, clearance: float = 0.0) -> None:
    """Grade the terrain so it MEETS the road at the edge (no cliff to fall off, no bulge to poke up).
    Each grid node within ``corridor`` m of the road surface (centre + both edges) is pulled to a road
    elevation; the cut then blends back to natural terrain over ``blend`` m. Mutates in place.

    ``target="nearest"`` (default) grades to the NEAREST road sample, so the grass sits right at the
    local road height and you can run off road->grass smoothly. ``target="min"`` grades to the lowest
    road sample within the corridor — only correct for a grade-SEPARATED route (one part passing under
    another), and on a normal single-loop street it carves the grass metres below the local road,
    leaving the shoulder floating on a cliff the car falls off (the "drive off the grass and collapse"
    bug). The Sand Creek loop is a simple closed loop (no self-crossing), so nearest is right.

    For the meeting to hold at every road point, ``corridor`` must exceed the terrain grid's
    half-diagonal — so the grid must be FINE (see ``upsample_grid``)."""
    from collections import defaultdict
    reach = corridor + blend
    corr2 = corridor * corridor
    samples, _ = _road_surface_samples(centerline_m, widths_m, bank_at)
    for ec, ew in (extra_roads or []):       # connector/interior roads: grass meets them too (flat, no bank)
        samples = samples + _road_surface_samples(ec, ew, None)[0]
    buckets: dict[tuple[int, int], list[tuple[float, float, float]]] = defaultdict(list)
    for x, y, z, _i in samples:
        buckets[(int(x // reach), int(z // reach))].append((x, y, z))
    for row in grid_xyz:
        for k in range(len(row)):
            gx, gy, gz = row[k]
            ci, cj = int(gx // reach), int(gz // reach)
            best_d2, near_y, corr_min = 1e18, None, None
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for cx, cy, cz in buckets.get((ci + di, cj + dj), ()):
                        if abs(cy - gy) > 20.0:   # different leg of a stacked switchback, not "the" road
                            continue
                        d2 = (gx - cx) ** 2 + (gz - cz) ** 2
                        if d2 < best_d2:
                            best_d2, near_y = d2, cy
                        if d2 <= corr2 and (corr_min is None or cy < corr_min):
                            corr_min = cy
            if near_y is None:
                continue
            tgt = (corr_min if corr_min is not None else near_y) if target == "min" else near_y
            tgt -= clearance      # sink the graded grass a touch BELOW the road so the coarse grass grid
            #                       can't bulge a triangle up through the road (poke-through) on steep
            #                       sections like the corkscrew. The shoulder ramps to this same level.
            d = math.sqrt(best_d2)
            if d <= corridor:
                row[k] = (gx, tgt, gz)
            elif d <= reach:
                t = (d - corridor) / blend
                row[k] = (gx, tgt * (1 - t) + gy * t, gz)


def grade_embankment(grid_xyz: list[list[Vertex]], centerline_m: list[Vertex],
                     widths_m: list[float] | None = None, *, band: float = 4.0, ratio: float = 2.0,
                     clearance: float = 0.0, bank_at=None, extra_roads=None,
                     bridge_of=None) -> float:
    """Build the terrain UP from the real ground to the road — an EMBANKMENT (fill) where the road sits
    above bare earth, a CUT where it sits below — instead of pulling the whole corridor UP to a flat
    plateau (the old ``conform_terrain_to_road``, which buried valleys under a 10 m mesa the car floats on).

    For each grid node, referenced to the nearest road-surface sample (centre + both banked edges):
      • within ``band`` m of the road  → held at ``road_edge - clearance`` (a gentle, drivable shelf that
        the shoulder/kerb meets flush — the "hybrid" gentle band),
      • beyond ``band``                → ramps toward the node's OWN bare-earth height at a ``ratio``:1
        slope (2:1 ≈ 27°). Fill descends from the shelf down to real ground; cut rises up to it. Once it
        reaches natural ground it STAYS there — so the real valley/hillside is preserved, and running off
        is a slope to the real ground, not a fall off a tabletop edge.

    Mutates ``grid_xyz`` in place (Y only) and RETURNS the effective ``band`` — widened below when the
    grid is too coarse to represent the one asked for. clamp_terrain_below_road needs that same number
    to reproduce this fill profile as its layer window, and recomputing it there would let the two
    drift apart. ``bridge_of(station_m) -> bool`` (optional) marks stations the
    road crosses on a BRIDGE: fill is suppressed there (the terrain keeps its natural creek/valley height
    so the deck can span it). On a near-flat racetrack the fills are tiny, so this reads as the "smooth
    gradations to the ground" a purpose-built circuit wants — same code path, no special-casing."""
    from collections import defaultdict
    slope = 1.0 / max(ratio, 1e-3)
    samples, _ = _road_surface_samples(centerline_m, widths_m, bank_at)
    # tag each sample with its lap station so bridge spans can suppress fill under a deck
    stationed = []
    arc = 0.0
    prev = None
    # recompute per-sample station: samples come grouped (centre,left,right) per centerline vertex; use the
    # centerline arc at that vertex. Rebuild arc alongside _road_surface_samples' vertex order.
    cl_arc = [0.0]
    for i in range(1, len(centerline_m)):
        cl_arc.append(cl_arc[-1] + math.hypot(centerline_m[i][0] - centerline_m[i - 1][0],
                                              centerline_m[i][2] - centerline_m[i - 1][2]))
    for (sx, sy, sz, si) in samples:
        stationed.append((sx, sy, sz, cl_arc[si] if si < len(cl_arc) else 0.0))
    for ec, ew in (extra_roads or []):        # connectors: graded too, no bridge, no station
        for (sx, sy, sz, _si) in _road_surface_samples(ec, ew, None)[0]:
            stationed.append((sx, sy, sz, -1.0))
    # BAND MUST BE REPRESENTABLE BY THE GRID. The shelf only exists where a grid NODE lands on it:
    # nodes carry the height, triangles interpolate between them. A band narrower than the grid's
    # half-diagonal is a shelf no node ever samples, so every node anchoring a road-spanning triangle
    # has already ramped down at ``ratio``:1 — and the terrain sags under the deck by roughly
    # (spacing/2 - band)/ratio. That is L3b one level up: a shelf can only exist if it is WIDER than
    # the cell that has to represent it. Measured on Dragon Tail (40 m 3DEP -> 10 m cells, band 2.5):
    # median 0.48 m, p95 1.51 m, max 4.12 m of air under the road, 98.6% of samples off the ground.
    # Raising the floor, never lowering a caller's request: a track that asks for a wide bench keeps it.
    _dx = abs(grid_xyz[0][1][0] - grid_xyz[0][0][0]) if len(grid_xyz[0]) > 1 else 0.0
    _dz = abs(grid_xyz[1][0][2] - grid_xyz[0][0][2]) if len(grid_xyz) > 1 else 0.0
    _need = 0.5 * math.hypot(_dx, _dz) + 1.0   # half-diagonal + margin: the ring of nodes flanking the road
    if _need > band:
        print(f"[grade_embankment] band {band:.1f} m < grid half-diagonal {_need - 1.0:.1f} m "
              f"({_dx:.1f}x{_dz:.1f} m cells) -> widening to {_need:.1f} m so the shelf is representable")
        band = _need
    reach = band + 60.0                        # search radius: band + a tall fill's run (30 m fill @2:1 = 60 m)
    cell = 24.0
    BRIDGE_CLEAR = 14.0                         # keep terrain NATURAL within this of a bridge-span road point
    buckets: dict[tuple[int, int], list] = defaultdict(list)
    bridge_buckets: dict[tuple[int, int], list] = defaultdict(list)
    for sx, sy, sz, sstn in stationed:
        buckets[(int(sx // cell), int(sz // cell))].append((sx, sy, sz))
        if bridge_of is not None and sstn >= 0 and bridge_of(sstn):
            bridge_buckets[(int(sx // cell), int(sz // cell))].append((sx, sz))
    R = int(reach // cell) + 1
    br2 = BRIDGE_CLEAR * BRIDGE_CLEAR
    for row in grid_xyz:
        _dbgrow = nodedbg.ENABLED and isinstance(row, nodedbg.WatchRow)
        for k in range(len(row)):
            gx, gy, gz = row[k]                # gy = natural bare earth
            ci, cj = int(gx // cell), int(gz // cell)
            best_d2, ref_y = 1e18, None
            on_bridge = False
            for di in range(-R, R + 1):
                for dj in range(-R, R + 1):
                    for sx, sy, sz in buckets.get((ci + di, cj + dj), ()):
                        # LAYER WINDOW: a sample far above/below this node's NATURAL ground is a
                        # different leg of a stacked switchback. Grading to it erects a fill wall
                        # beside the lower leg or carves a canyon beside the upper one.
                        if abs(sy - gy) > 20.0:
                            continue
                        d2 = (gx - sx) ** 2 + (gz - sz) ** 2
                        if d2 < best_d2:
                            best_d2, ref_y = d2, sy
                    if not on_bridge:
                        for bx, bz in bridge_buckets.get((ci + di, cj + dj), ()):
                            if (gx - bx) ** 2 + (gz - bz) ** 2 <= br2:
                                on_bridge = True
                                break
            if ref_y is None:
                continue
            shelf = ref_y - clearance
            d = math.sqrt(best_d2)
            over = max(0.0, d - band)
            if shelf >= gy:                     # FILL — descend from the shelf to real ground
                if on_bridge:
                    continue                    # leave the natural creek/valley open so the deck spans it
                tgt = max(gy, shelf - slope * over)
            else:                               # CUT — a steep excavated face rising into the ridge
                tgt = min(gy, shelf + over / 0.75)
            if _dbgrow and k == nodedbg.COL:
                nodedbg.note(f"  grade: natural {gy:.3f} -> {tgt:.3f}; nearest road sample y "
                             f"{ref_y:.3f} at {d:.2f} m (band {band:.2f}, over {over:.2f}, "
                             f"{'FILL' if shelf >= gy else 'CUT'}, on_bridge {on_bridge})")
            row[k] = (gx, tgt, gz)
    return band


def clamp_terrain_below_road(grid_xyz: list[list[Vertex]], road_verts: list[Vertex],
                             *, reach: float = 11.0, clear: float = 0.25, cell: float = 12.0,
                             grid_spacing: float | None = None,
                             foot_m: float | None = None, recover: float = 0.0,
                             fill_ratio: float | None = None, band: float = 0.0,
                             layer_ref: list[list[float]] | None = None) -> None:
    """One-sided ANTI-POKE against the ACTUAL built road surface. For every terrain grid node within
    ``reach`` m of a road vertex, if the node sits above ``road_y - clear`` push it DOWN to that level so
    no grass triangle pokes up through the drivable ribbon. Never RAISES a node (natural dips survive).

    Why against the built road verts (not the centerline): on a BANKED turn the inner edge rides metres
    below the centre, so a centreline-based clamp leaves the inner edge poking; the real banked edge verts
    are the true surface. Run AFTER road_ribbon (post-bank, post-lift) and conform, BEFORE grass_terrain.
    Mutates ``grid_xyz`` in place. Mirror-agnostic: road_verts and grid_xyz must be in the SAME frame."""
    from collections import defaultdict
    # reach must cover the terrain grid's cell DIAGONAL past the road edge, or the first un-clamped
    # node up-slope bridges its triangle back over the pavement (195 wheel-path ground-throughs on
    # the Lariat at reach=11 vs 13.4 m cells — the drive test sees the faces, not the vertices).
    if grid_spacing is not None:
        # 2.2x: at bridge-deck ends the fill-grading exemption leaves natural-high nodes close by;
        # 1.5x let one coarse triangle bridge over the deck (grass mid-lane at SC station 6032).
        reach = max(reach, grid_spacing * 2.2 + 0.5)
    cell = max(cell, reach)
    buckets: dict[tuple[int, int], list[Vertex]] = defaultdict(list)
    for x, y, z in road_verts:
        buckets[(int(x // cell), int(z // cell))].append((x, y, z))
    r2 = reach * reach
    # LAYER WINDOW: at a switchback stack two road legs share the same XZ column. Clamping a node
    # under the LOWEST nearby road vert drags the grass beside the UPPER leg a hundred metres down —
    # the upper road then rides a canyon of air ("road 10 feet over the ground", the rainbow-road
    # layers Kevin drove through). A road vert far below the node's own height belongs to a DIFFERENT
    # leg: never conform across more than LAYER_DY of vertical separation.
    LAYER_DY = 20.0
    # ...but a FLAT 20 m only separates legs that are more than 20 m apart. L4 already says the layer
    # gap is scale-dependent ("~20 m generally; ~4 m for a shoulder against its own deck"), and a
    # DIVIDED STREET is the case where the general figure has nothing to bite on: Del Cerro Boulevard
    # carries its two carriageways 13-20 m apart horizontally and only 2.0-4.7 m apart vertically, so
    # the lower one sits well inside 20 m of the upper one's embankment and shaves it flat. Measured
    # on Lake Murray: grade_embankment builds the shelf at 47.840, this pass drops it to 43.600 one
    # line later, and nothing downstream can lift it because the node is 0.18 m OUTSIDE the upper
    # carriageway's pavement (so the contact pin, which needs a road triangle overhead, skips it).
    # Result: p95 4.051 m of air under 1ROAD_del_cerro_blvd's outer edge — ledger 0019.
    #
    # The window that actually separates them is the FILL FACE, not a constant. grade_embankment
    # builds terrain up from a road at ``fill_ratio``:1 through a flush ``band``; so the highest this
    # node could legitimately stand while still belonging to THIS road vert is (d - band) / ratio
    # above its deck. A node higher than that is standing on someone else's embankment — a different
    # layer — and this vert has no business pulling it down. Near the pavement the window closes to
    # ~clear (anti-poke intact, which is the whole point of the pass); it only opens out where the
    # ground is legitimately climbing away. Callers that pass no fill_ratio keep the flat LAYER_DY.
    _fill_slope = (1.0 / max(fill_ratio, 1e-3)) if fill_ratio else None
    # ...measured against ``layer_ref`` — the height the GRADING pass gave this node — not against
    # whatever it currently holds. This pass runs more than once, and after the first call has
    # lowered a node the window sees it sitting near the lower road and waves the second call
    # through: measured at Lake Murray station ~ -1640,-128, call #1 correctly rejected the mainline
    # (dy -3.443 against a 3.325 m window) and call #2 then shaved the same node to it anyway
    # (dy -0.795, nothing rejected). Which road OWNS a node is decided once, by the grading; later
    # anti-poke passes may lower it but must not re-decide its layer.
    # DISTANCE-GRADED, not a flat shave: clamping every node within reach to road_y - clear carved
    # a reach-wide (15 m on a 10 m grid) sunken APRON along the whole lap — the dark moat between
    # road edge and natural grass in Kevin's night photo. Full clamp beside the pavement, then the
    # allowed height RECOVERS with distance at a natural slope: near nodes still pin the triangles
    # down (anti-poke intact), the terrain rejoins its real height instead of a shaved terrace.
    # foot_m/recover=None,0 -> classic flat shave (used for the tight under-shoulder clamp).
    # The ROAD-corridor call passes foot_m past the shoulder's reach so the moat ends where the
    # drape ends, and terrain recovery can NEVER rise into the wheel path (drive test at the Sand
    # Creek bridge approach caught a 0.43 m step when recovery started inside the verge band).
    FOOT_M = foot_m if foot_m is not None else reach + 1.0
    RECOVER = recover
    _GRID_SP = grid_spacing or 0.0
    for _rj, row in enumerate(grid_xyz):
        _dbgrow = nodedbg.ENABLED and isinstance(row, nodedbg.WatchRow)
        _lrow = layer_ref[_rj] if layer_ref is not None else None
        for k in range(len(row)):
            gx, gy, gz = row[k]
            ref = _lrow[k] if _lrow is not None else gy
            ci, cj = int(gx // cell), int(gz // cell)
            lim = None
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for rx, ry, rz in buckets.get((ci + di, cj + dj), ()):
                        d2 = (gx - rx) ** 2 + (gz - rz) ** 2
                        if d2 > r2 or gy - ry > LAYER_DY:
                            continue
                        d = d2 ** 0.5
                        if _fill_slope is not None and \
                                ref - ry > clear + max(0.0, d - band) * _fill_slope:
                            continue        # standing on a HIGHER road's fill face — different layer
                        t = ry - clear + max(0.0, d - FOOT_M) * RECOVER
                        if lim is None or t < lim:
                            lim = t
            # THE GRADING IS NOT OVERRULED BY MORE THAN ONE CELL OF FILL. The window above asks
            # "could this node belong to that road", and at a grade separation BOTH roads answer
            # yes: the node measured at Lake Murray -1643,-126 sits 1.4 m from the connector it was
            # graded to and 10.9 m from the mainline 3.7 m below, and a 2:1 cone from the mainline
            # reaches 3.95 m at 10.9 m — so the far road squeaks in and wins the minimum. Distance
            # is the discriminator the window cannot see, and grade_embankment already applied it
            # (it grades to the NEAREST road). This pass exists to catch the BUILT ribbon sitting
            # lower than the SAMPLED surface the grading used — banking, lift, discretisation —
            # which is a cell-scale correction, not a 3 m one. Bound it at exactly that.
            if _fill_slope is not None and lim is not None and _GRID_SP:
                lim = max(lim, ref - (clear + _GRID_SP * _fill_slope))
            if _dbgrow and k == nodedbg.COL:
                # name the vertex that won the minimum — "which road shaved this node?"
                _cands = []
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        for rx, ry, rz in buckets.get((ci + di, cj + dj), ()):
                            d2 = (gx - rx) ** 2 + (gz - rz) ** 2
                            if d2 > r2 or gy - ry > LAYER_DY:
                                continue
                            d = d2 ** 0.5
                            _off = (_fill_slope is not None and
                                    ref - ry > clear + max(0.0, d - band) * _fill_slope)
                            _cands.append((ry - clear + max(0.0, d - FOOT_M) * RECOVER, d, ry, _off))
                _cands.sort()
                _acc = [c for c in _cands if not c[3]]
                nodedbg.note(f"  clamp: node y {gy:.3f}, reach {reach:.2f} m, LAYER_DY {LAYER_DY}, "
                             f"fill window {'off' if _fill_slope is None else f'1:{1/_fill_slope:.0f} past {band:.2f} m'}, "
                             f"{len(_cands)} road verts in range, {len(_cands) - len(_acc)} rejected")
                for _lim, _d, _ry, _off in _cands[:3]:
                    nodedbg.note(f"    limit {_lim:8.3f}  from a road vert at y {_ry:8.3f}, "
                                 f"{_d:6.2f} m away (dy {_ry - gy:+.3f})"
                                 f"{'  [REJECTED: different layer]' if _off else ''}")
                if _acc:
                    _wl, _wd, _wy, _ = _acc[0]
                    nodedbg.note(f"    WINNER  limit {_wl:8.3f}  road vert y {_wy:8.3f}, "
                                 f"{_wd:6.2f} m away (dy {_wy - gy:+.3f})")
                else:
                    nodedbg.note("    WINNER  none — every candidate was a different layer")
            if lim is not None and gy > lim:
                row[k] = (gx, lim, gz)


def upsample_grid(grid: list[list[float]], meta: dict, factor: int) -> tuple[list[list[float]], dict]:
    """Bilinearly upsample the raw DEM height grid by an integer factor (finer spacing). Free (no
    re-sampling) and lossless on gentle terrain — a fine grid lets ``conform_terrain_to_road`` hug the
    road with a small corridor and little float, instead of fighting 40 m facets. Returns (grid, meta)
    with nx/ny/spacing_m updated; the lon/lat bbox is unchanged so projection stays identical."""
    if factor <= 1:
        return grid, meta
    ny, nx = len(grid), len(grid[0])
    big_y, big_x = (ny - 1) * factor + 1, (nx - 1) * factor + 1
    out = [[0.0] * big_x for _ in range(big_y)]
    for jj in range(big_y):
        fy = jj / factor
        j0 = min(ny - 1, int(fy)); j1 = min(ny - 1, j0 + 1); ty = fy - j0
        for ii in range(big_x):
            fx = ii / factor
            i0 = min(nx - 1, int(fx)); i1 = min(nx - 1, i0 + 1); tx = fx - i0
            a = grid[j0][i0] * (1 - tx) + grid[j0][i1] * tx
            b = grid[j1][i0] * (1 - tx) + grid[j1][i1] * tx
            out[jj][ii] = a * (1 - ty) + b * ty
    meta2 = dict(meta)
    meta2["nx"], meta2["ny"], meta2["spacing_m"] = big_x, big_y, meta["spacing_m"] / factor
    return out, meta2


def grass_terrain(grid_xyz: list[list[Vertex]], *, tile_m: float = 6.0, skirt_m: float = 500.0,
                  refine_quads: set | None = None, refine_factor: int = 1, height_at=None) -> dict:
    """Triangulate the projected terrain grid (ny rows × nx cols of (x,y,z)) into the GRASS mesh.
    UVs are world-planar (x/tile, z/tile) so the grass texture tiles seamlessly over any terrain.

    A flat **skirt** (``skirt_m`` m) is extruded outward from every grid border at the border height,
    so the physical ground extends far past the loop — run wide onto the grass and you stay on a
    surface instead of dropping off the edge of the world.

    CORRIDOR REFINEMENT (``refine_quads``: a set of (i,j) quad corners to subdivide ``refine_factor``
    ways per axis; ``height_at(x, z, base_y) -> y`` supplies each new node's height).

    The road contact problem is that a cell can only follow a cut it is SMALLER than (L3b), but the
    corridor is ~1% of the grid's area — on Dragon Tail, 1.01 km² of a 94 km² grid. Refining
    UNIFORMLY to 2 m costs 23.4 M verts and is unbuildable; refining only the quads the pavement
    touches costs ~0.2 M and buys the identical contact. The coarse raster is left completely
    untouched — same nx/ny, same spacing, same vertex indices, same ``ground.local.json`` — because
    four other modules (audit check G, scenery seating, both network builders) re-read it as a
    regular raster. Only the emitted TRIANGLES change.

    T-junctions are the trap: subdividing a quad leaves hanging nodes on the edges it shares with
    un-refined neighbours, and an un-stitched hanging node is daylight beside the pavement (the
    failure class of ledger 0004). So every quad bordering the refined region is fan-triangulated
    from its centroid through those hanging nodes — no cracks, no constraint on the region's shape."""
    ny = len(grid_xyz)
    nx = len(grid_xyz[0])
    verts = [grid_xyz[j][i] for j in range(ny) for i in range(nx)]
    uvs = [(grid_xyz[j][i][0] / tile_m, grid_xyz[j][i][2] / tile_m) for j in range(ny) for i in range(nx)]
    tris: list[tuple[int, int, int]] = []

    N = max(1, int(refine_factor))
    RQ = refine_quads if (refine_quads and N > 1) else set()
    # sub-lattice index: coarse node (i,j) is (i*N, j*N), so coarse verts keep their existing ids
    _sub: dict[tuple[int, int], int] = {}

    def _node(I: int, J: int) -> int:
        """Vertex id at sub-lattice (I,J), creating it (and its height) on first use."""
        if I % N == 0 and J % N == 0:
            return (J // N) * nx + (I // N)
        k = (I, J)
        got = _sub.get(k)
        if got is not None:
            return got
        i0, si = divmod(I, N)
        j0, sj = divmod(J, N)
        i1, j1 = min(nx - 1, i0 + 1), min(ny - 1, j0 + 1)
        tx, tz = si / N, sj / N
        p00, p10 = grid_xyz[j0][i0], grid_xyz[j0][i1]
        p01, p11 = grid_xyz[j1][i0], grid_xyz[j1][i1]
        x = (p00[0] * (1 - tx) + p10[0] * tx) * (1 - tz) + (p01[0] * (1 - tx) + p11[0] * tx) * tz
        z = (p00[2] * (1 - tx) + p10[2] * tx) * (1 - tz) + (p01[2] * (1 - tx) + p11[2] * tx) * tz
        y = (p00[1] * (1 - tx) + p10[1] * tx) * (1 - tz) + (p01[1] * (1 - tx) + p11[1] * tx) * tz
        if height_at is not None:
            y = height_at(x, z, y)
        got = len(verts)
        verts.append((x, y, z))
        uvs.append((x / tile_m, z / tile_m))
        _sub[k] = got
        return got

    for j in range(ny - 1):
        for i in range(nx - 1):
            if (i, j) in RQ:
                for sj in range(N):                       # fine sub-quads, all nodes shared by key
                    for si in range(N):
                        a = _node(i * N + si,     j * N + sj)
                        b = _node(i * N + si + 1, j * N + sj)
                        c = _node(i * N + si + 1, j * N + sj + 1)
                        d = _node(i * N + si,     j * N + sj + 1)
                        tris.append((a, b, c))
                        tris.append((a, c, d))
                continue
            # un-refined: does any neighbour refine, leaving hanging nodes on our shared edge?
            nb = (RQ and ((i, j - 1) in RQ or (i + 1, j) in RQ or (i, j + 1) in RQ or (i - 1, j) in RQ))
            if not nb:
                a, b, c, d = j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i
                tris.append((a, b, c))
                tris.append((a, c, d))
                continue
            ring: list[int] = []                          # perimeter a->b->c->d, hanging nodes inserted
            for (di0, dj0), (di1, dj1), side in (((0, 0), (1, 0), (i, j - 1)),
                                                 ((1, 0), (1, 1), (i + 1, j)),
                                                 ((1, 1), (0, 1), (i, j + 1)),
                                                 ((0, 1), (0, 0), (i - 1, j))):
                ring.append(_node((i + di0) * N, (j + dj0) * N))
                if side in RQ:
                    for s in range(1, N):
                        t = s / N
                        ring.append(_node(int(round(((i + di0) * (1 - t) + (i + di1) * t) * N)),
                                          int(round(((j + dj0) * (1 - t) + (j + dj1) * t) * N))))
            cx = sum(verts[r][0] for r in ring) / len(ring)
            cz = sum(verts[r][2] for r in ring) / len(ring)
            cy = sum(verts[r][1] for r in ring) / len(ring)
            if height_at is not None:
                cy = height_at(cx, cz, cy)
            ci = len(verts)
            verts.append((cx, cy, cz))
            uvs.append((cx / tile_m, cz / tile_m))
            for k in range(len(ring)):
                tris.append((ci, ring[k], ring[(k + 1) % len(ring)]))

    if skirt_m > 0.0:
        # WATERTIGHT skirt: walk the grid's border as a closed perimeter loop and reference the grid's
        # ACTUAL border vertex indices (gi). Each skirt quad's inner edge IS a real grid edge, so it
        # shares with the grid face — no coincident copies, no reliance on welding, no open seam (the
        # old copy-and-weld approach left ~780 holes the car fell through).
        # OUTWARD IS DERIVED, NOT ASSUMED. These offsets used to hardcode +x for the i=nx-1 edge
        # and -x for i=0, which is only correct while x increases with i. Every k10-colorado track
        # sets mirror_x, so x DECREASES with i and both x skirts extruded 500 m straight ACROSS the
        # grid instead of away from it. Measured on Aspen: the west border at x=-255.4 had its skirt
        # partner at x=+244.6 (exactly -255.4 + 500), and the east border at 307.0 had one at
        # -193.0 — a 500 m plane laid over the interior. Where the border sits higher than the road
        # (a mountain site: +18.59 vs a deck at 4.17) that plane passes OVER the pavement, which is
        # Aspen's 1,037 "ground on top mid-lane" hits. Flat sites hid it because the skirt drops to
        # a low floor and never rises above their deck.
        _sx = 1.0 if grid_xyz[0][nx - 1][0] >= grid_xyz[0][0][0] else -1.0   # does x grow with i?
        _sz = 1.0 if grid_xyz[ny - 1][0][2] >= grid_xyz[0][0][2] else -1.0   # does z grow with j?
        _ox, _oz = skirt_m * _sx, skirt_m * _sz
        perim: list[tuple[int, float, float]] = []  # (grid_index, outward_dx, outward_dz)
        for i in range(nx):                 perim.append((i, 0.0, -_oz))                  # j=0    edge
        for j in range(1, ny):              perim.append((j * nx + nx - 1, _ox, 0.0))      # i=nx-1 edge
        for i in range(nx - 2, -1, -1):     perim.append(((ny - 1) * nx + i, 0.0, _oz))    # j=ny-1 edge
        for j in range(ny - 2, 0, -1):      perim.append((j * nx, -_ox, 0.0))              # i=0    edge
        # Drop the far edge to one flat LOW level (below all terrain) instead of extruding each border
        # FLAT at its own height — otherwise a high DEM border (here up to +35 m vs a ~17 m track) makes
        # a 500 m grass plane hanging in the sky. The skirt now ramps gently down-and-out to a floor you
        # never reach, so there's a catch-surface off the world without any floating planes.
        low_y = min(v[1] for v in verts) - 5.0
        outer_idx = []
        for gi, dx, dz in perim:
            x, _y, z = verts[gi]
            outer_idx.append(len(verts))
            verts.append((x + dx, low_y, z + dz))
            uvs.append(((x + dx) / tile_m, (z + dz) / tile_m))
        P = len(perim)
        for k in range(P):
            gi0, gi1 = perim[k][0], perim[(k + 1) % P][0]      # consecutive grid border verts (a real edge)
            oi0, oi1 = outer_idx[k], outer_idx[(k + 1) % P]
            tris.append((gi0, oi0, oi1))
            tris.append((gi0, oi1, gi1))
    return {"vertices": verts, "uvs": uvs, "tris": tris}


def crosswalk(centerline_m: list[Vertex], widths_m: list[float], *, at_idx: int = 0,
              depth_m: float = 3.6, bar_w: float = 0.55, gap_w: float = 0.55, margin_m: float = 0.5,
              lift: float = 0.0, bank_at=None) -> dict:
    """A high-visibility **continental crosswalk** across the road at centerline index ``at_idx`` (the
    start/finish on Colorado Blvd). Longitudinal white bars — parallel to travel, arranged across the
    full width — straddling the line. Flat white (visual-only, MARKINGS material). ``bank_at`` rolls it
    with the road. UV-free (solid colour)."""
    pts = centerline_m
    n = len(pts)
    i = max(0, min(n - 1, at_idx))
    x, y, z = pts[i]
    tx, tz = _horiz_tangent(pts, i, abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6)
    nx, nz = -tz, tx                      # left normal (across the road)
    # global station at this index (for bank lookup)
    arc = 0.0
    for k in range(1, i + 1):
        arc += math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
    tb = math.tan(bank_at(arc)) if bank_at else 0.0
    half = widths_m[i] / 2.0 - margin_m
    d = depth_m / 2.0
    verts: list[Vertex] = []
    tris: list[tuple[int, int, int]] = []
    u = -half
    step = bar_w + gap_w
    while u <= half - 1e-6:
        u1 = min(u + bar_w, half)
        for (uu, dd) in ((u, -d), (u1, -d), (u1, d), (u, d)):   # bar corners (across × along)
            px = x + nx * uu + tx * dd
            pz = z + nz * uu + tz * dd
            verts.append((px, y + lift + uu * tb, pz))
        b = len(verts) - 4
        tris.append((b, b + 1, b + 2))
        tris.append((b, b + 2, b + 3))
        u += step
    return {"vertices": verts, "tris": tris}


def road_markings(centerline_m: list[Vertex], widths_m: list[float], *, line_w: float = 0.14,
                  edge_inset: float = 0.4, lift: float = 0.0, dash_on: float = 3.0,
                  dash_gap: float = 4.5, tile_m: float = 1.0, bank_at=None) -> dict:
    """Thin white lane lines along the road: solid edge lines (inset from the kerb) + a dashed centre.
    Visual-only (no ``1`` prefix). Sits ``lift`` above the road — build_mesh raises it with the ribbon.
    ``bank_at`` rolls each line with the cambered road (offset*tan(bank) added to Y)."""
    pts = centerline_m
    n = len(pts)
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    m = n - 1 if closed else n
    stations = []
    arc = 0.0
    for i in range(m):
        if i > 0:
            arc += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
        x, y, z = pts[i]
        tx, tz = _horiz_tangent(pts, i, closed)
        stations.append((x, y, z, -tz, tx, widths_m[i] / 2.0, arc))  # x,y,z, leftnormal nx,nz, half, arc
    verts: list[Vertex] = []
    uvs: list[tuple[float, float]] = []
    tris: list[tuple[int, int, int]] = []

    def add_line(offset_of, dashed):
        for i in range(m):
            j = (i + 1) % m
            if not closed and j == 0:
                break
            s0, s1 = stations[i], stations[j]
            if dashed and (s0[6] % (dash_on + dash_gap)) > dash_on:
                continue
            b = len(verts)
            for s in (s0, s1):
                x, y, z, nx, nz, half, a = s
                o = offset_of(s)
                tb = math.tan(bank_at(a)) if bank_at else 0.0
                for sign in (-1, 1):
                    off = o + sign * line_w / 2
                    verts.append((x + nx * off, y + lift + off * tb, z + nz * off))
                    uvs.append(((sign + 1) / 2, a / tile_m))
            tris.append((b, b + 1, b + 3))
            tris.append((b, b + 3, b + 2))

    add_line(lambda s: 0.0, True)                    # centre line, dashed
    add_line(lambda s: s[5] - edge_inset, False)     # left edge, solid
    add_line(lambda s: -(s[5] - edge_inset), False)  # right edge, solid
    return {"vertices": verts, "uvs": uvs, "tris": tris}


# Ported from k10-san-diego (Lake Murray look): double-yellow centre + white edge lines +
# dashed dividers, lane count derived per-station from real width.
def lane_markings(centerline_m: list[Vertex], widths_m: list[float], *, line_w: float = 0.12,
                  edge_inset: float = 0.55, lane_w: float = 3.65, lift: float = 0.0,
                  dash_on: float = 3.0, dash_gap: float = 9.0, max_lanes_side: int = 6,
                  center_yellow: bool = True, tile_m: float = 1.0, bank_at=None) -> dict:
    """Realistic painted lane lines for a real street: a solid double-yellow centreline, dashed white
    lane dividers (one per lane boundary each side, spaced ``lane_w``), and solid white edge lines inset
    from the kerb. Lane count is derived per-station from the road width, so wide arterials and
    intersection turn-pockets get more lanes and narrow blocks fewer — dividers self-clip where they'd
    fall outside the paved width. Returns ``{"white": mesh, "yellow": mesh}`` (both VISUAL-only — no ``1``
    prefix); the caller lifts them a hair above the road. Quads are double-sided so a flat decal never
    backface-culls. ``bank_at`` rolls every line with the cambered road."""
    pts = centerline_m
    n = len(pts)
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    m = n - 1 if closed else n
    stations = []
    arc = 0.0
    for i in range(m):
        if i > 0:
            arc += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
        x, y, z = pts[i]
        tx, tz = _horiz_tangent(pts, i, closed)
        stations.append((x, y, z, -tz, tx, widths_m[i] / 2.0, arc))  # x,y,z, leftnormal, half, arc
    white = {"vertices": [], "uvs": [], "tris": []}
    yellow = {"vertices": [], "uvs": [], "tris": []}

    def strip(mesh, offset_of, dashed, clip=False, w=line_w):
        V, U, T = mesh["vertices"], mesh["uvs"], mesh["tris"]
        for i in range(m):
            j = (i + 1) % m
            if not closed and j == 0:
                break
            s0, s1 = stations[i], stations[j]
            o0, o1 = offset_of(s0[5]), offset_of(s1[5])
            if clip and (abs(o0) + w / 2 > s0[5] - edge_inset or abs(o1) + w / 2 > s1[5] - edge_inset):
                continue                                   # divider would spill past the paved edge → skip
            if dashed and (s0[6] % (dash_on + dash_gap)) > dash_on:
                continue
            b = len(V)
            for s, o in ((s0, o0), (s1, o1)):
                x, y, z, nx, nz, half, a = s
                tb = math.tan(bank_at(a)) if bank_at else 0.0
                for sign in (-1, 1):
                    off = o + sign * w / 2
                    V.append((x + nx * off, y + lift + off * tb, z + nz * off))
                    U.append(((sign + 1) / 2, a / tile_m))
            T.append((b, b + 1, b + 3)); T.append((b, b + 3, b + 2))     # forced face-up in build_kn5

    if center_yellow:                                           # two-way street: solid double-yellow centre
        strip(yellow, lambda half: +0.09, False)                # (a one-way freeway carriageway has none)
        strip(yellow, lambda half: -0.09, False)
    strip(white, lambda half: half - edge_inset, False)         # solid white edge lines
    strip(white, lambda half: -(half - edge_inset), False)
    for k in range(1, max_lanes_side + 1):                       # dashed white lane dividers, both sides
        strip(white, (lambda kk: (lambda half: kk * lane_w))(k), True, clip=True)
        strip(white, (lambda kk: (lambda half: -kk * lane_w))(k), True, clip=True)
    return {"white": white, "yellow": yellow}



"""PHASE 5 stub geometry — the PURE half (no bpy) of tools/author_stubs_blend.py, shared with tools/verify_stubs.py
and the tests. Engine frame throughout: x east, y up, z north; a "row" is the curb strip's 4 profile points
(p0 lane edge, p1 curb top, p2 sidewalk back, p3 grass meet — ribbon.curb_sidewalk).

CURB RETURN (docs/JUNCTIONS.md R5 / R9 / R10, 2.2 rt_macau: "each curb strip wraps a corner-return arc and terminates
at the main-road edge"). At each corner of a stub mouth:
  K   the corner: the stub's road edge line (straight, read off its rows past the weld's re-spread) meets the host's
      road edge line;
  A   the host curb row where gap_mouths' sidewalk gap ENDS on that side (mouth_weld.gap_window — the same window, so the
      return starts exactly on the last host curb row that keeps its faces);
  tH  = |K A|, the tangent length; phi the ground wedge's angle at K between K->A and the stub edge outward;
  R   = tH tan(phi / 2): the circle tangent to the host edge AT A and to the stub edge at B = K + tH (stub outward);
  J   the first stub curb row at or past B — the stub's own curb faces before it are removed (the return replaces them).
The return strip runs A (the host row, copied exactly) -> the arc at <= RETURN_STEP_M stations -> B -> J (the stub row,
copied exactly): the curb wraps the corner and is continuous from the host's strip into the stub's. Every profile
point keeps its offset from the lane edge toward the circle's centre (linear from A's offsets to J's along the path),
compressed so the outermost stays inside COMPRESS_R x R (a tight acute corner never folds the back of walk through
the centre). The CORNER PAVEMENT (the wedge between K, the host edge, the arc and the stub edge) is a fan from K,
merged into the road: single coverage (it never overlaps the host or the stub pavement — its two straight sides lie
ON their edges).

THE COMPRESSION IS CONTINUOUS (2026-10-18, the phase-5 verifier's acute-corner V-notch at Lambda c1 58 deg / Margerum
c1 66 deg). Compressing only the arc stations left two jumps: the host's gap-end row A kept its full walk (on the
mainline 1.88 m + 1.2 m of verge — past the circle's centre when R is 1.7 m), so the quad from A to the first arc
station twisted through the centre, and the last arc station B stepped straight back out to the stub's full walk at
the first tail row. Now (only where the walk must be compressed, `walk_scale` < 1): row A itself is compressed (the
caller moves the host's own row A to it and eases the host rows behind it back to full over HOST_RAMP_M,
`host_ramp`), the arc as before, and the tail B -> J eases the compression back to 1 (smoothstep over the tail; the
caller takes J at least STUB_RAMP_M past B). With nothing to compress every row is what it was.

THE RETURN'S GRASS MEET (2026-10-18, the verifier's sawtooth grass behind the returns). The loop's strips end their
verge 0.20 m under the road (curb_sidewalk grass_clearance) and the kn5 prep lays the ground beside every road at deck
- 0.02 and then clamps it 0.02 under the lowest drivable sheet: the verge's foot is buried, and the two rules meet
along it. On a straight strip that meeting is one long facet; round a return, on the fine ground of a welded approach,
it alternated cell by cell (0.2-0.6 m teeth). So the return's interior stations put their grass meet where the prep
lays the ground (MEET_H_M under the lane edge), easing to the host's / stub's own over MEET_RAMP_M at each end: the
verge lands on the ground instead of under it, and the prep's two rules agree within 0.02 m across it.

BARRIER: Kevin's concrete_barrier_4m.obj jersey profile (tools/race_furniture.HALF_PROFILE, 1.20 m, 0.67 m base) swept
ACROSS the stub at its declared distance from the mouth line, from the right grass meet over the right sidewalk, the
curb, the carriageway, the left curb and sidewalk to the left grass meet — rings at every profile point of the stub's
own curb row there and every <= BARRIER_RING_M between, each base seated on the LOWEST of the surfaces under its
footprint (front, centre, back) less BARRIER_BURY_M. The texture tiles at the module pitch (u = arc / 4.04 m).
MODULE JOINTS (2026-10-18, the verifier: "across the carriageway the K-rail renders as one continuous slab"): a swept
strip has no joint in its shape, and the texture alone does not read from the seat. Kevin's module is chamfered at
each end (the obj: the face insets 0.020 m at the base and the top drops 1.202 -> 1.106 m over its last 0.020 m), so
two modules butted make a V-groove. Every MODULE_PITCH_M along the barrier, laid out symmetric about its middle (whole
modules in the middle, the two end ones cut to the grass meets), the strip carries that groove: a ring of the end
profile (JOINT_HALF_PROFILE) between two full rings JOINT_HALF_M either side; the faces between meet at 45-78 deg, so
the race-furniture sharp-edge rule shades each joint as a crease. u is measured from the first joint so the texture's
module repeat lines up with the grooves.

Numbers marked [INVENTED] are in fleet/GATES-CHANGELOG.md (2026-10-14, phase 5).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import race_furniture as rf  # noqa: E402

RETURN_STEP_M = 0.3        # JUNCTIONS R5/R10: corner returns at ~0.2-0.3 m stations (macau 0.18 m median)
COMPRESS_R = 0.85          # [INVENTED] the outermost profile point stays inside this x R of the arc
HOST_RAMP_M = 3.0          # [INVENTED] a compressed return's host walk eases back to full over this (behind row A)
STUB_RAMP_M = 3.0          # [INVENTED] ... and its stub walk over at least this (the tail B -> J)
BARRIER_RING_M = 0.25      # [INVENTED] ring spacing across the stub (the curb step is ringed exactly)
BARRIER_BURY_M = 0.02      # [INVENTED] the base sunk this far under the lowest surface under its footprint
BARRIER_H = rf.BARRIER_H
BARRIER_HALF_BASE = rf.HALF_PROFILE[0][0]
MODULE_PITCH_M = rf.MODULE_PITCH_M
JOINT_HALF_M = 0.02        # measured: concrete_barrier_4m.obj chamfers its last 0.020 m at each end
# measured: the obj's end face (z = -4.000), (lateral, height) bottom -> top, the race_furniture.HALF_PROFILE points'
# own places on it (the base corner kept on the ground so the joint ring seats like its neighbours)
JOINT_HALF_PROFILE = ((0.315, 0.00), (0.311, 0.113), (0.147, 0.375), (0.117, 0.466), (0.073, 1.106))
JOINT_CLEAR_M = 0.30       # [INVENTED] no joint within this of the barrier's two ends (a cut module stays a module)
JOINT_KEY_CLEAR_M = 0.06   # [INVENTED] a joint this close to a profile-point ring (the curb step) slides off it
END_INSET_M = 0.02         # [INVENTED] the barrier's end rings stand this far inside the grass meets (on the strip)
MEET_H_M = -0.02           # the return's grass meet under its lane edge: the kn5 prep's GROUND_CLEAR (engine-july
#                            build_kn5_loop: every ground vertex within 3 m of a road is laid at deck - 0.02)
MEET_RAMP_M = 1.5          # [INVENTED] ... reached this far along the return from either end (A, J keep their own)
PHI_MIN_DEG, PHI_MAX_DEG = 20.0, 160.0


class GeomError(RuntimeError):
    pass


def sub(a, b):
    return (a[0] - b[0], a[2] - b[2])


def unit2(dx, dz):
    L = math.hypot(dx, dz)
    if L < 1e-12:
        raise GeomError("zero-length direction")
    return dx / L, dz / L


def dist2(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def line_seg_intersect(p, d, a, b):
    """the infinite line p + s d (plan) vs the segment a-b: (x, z, s, t) or None"""
    e = (b[0] - a[0], b[2] - a[2])
    den = cross2(d, e)
    if abs(den) < 1e-12:
        return None
    w = (a[0] - p[0], a[2] - p[2])
    s = cross2(w, e) / den
    t = cross2(w, d) / den
    if -1e-9 <= t <= 1.0 + 1e-9:
        return p[0] + d[0] * s, p[2] + d[1] * s, s, t
    return None


def corner(K, A0, b_dir):
    """the return's circle: (tH, phi, R, O, a_dir, B) for corner K, host gap-end lane edge A0 and the stub edge's
    outward unit b_dir (plan). Raises GeomError when the wedge is degenerate."""
    a_dir = unit2(A0[0] - K[0], A0[2] - K[2])
    tH = dist2(K, A0)
    c = max(-1.0, min(1.0, a_dir[0] * b_dir[0] + a_dir[1] * b_dir[1]))
    phi = math.acos(c)
    if not (math.radians(PHI_MIN_DEG) <= phi <= math.radians(PHI_MAX_DEG)):
        raise GeomError(f"corner wedge {math.degrees(phi):.1f} deg outside {PHI_MIN_DEG}-{PHI_MAX_DEG}")
    R = tH * math.tan(phi / 2.0)
    bis = unit2(a_dir[0] + b_dir[0], a_dir[1] + b_dir[1])
    h = R / math.sin(phi / 2.0)
    O = (K[0] + bis[0] * h, K[2] + bis[1] * h)
    B = (K[0] + b_dir[0] * tH, K[2] + b_dir[1] * tH)
    return tH, phi, R, O, a_dir, B


def arc_points(A, B, O, step=RETURN_STEP_M):
    """plan points from A to B on the circle about O (the short way), A and B included"""
    a0 = math.atan2(A[1] - O[1], A[0] - O[0])
    a1 = math.atan2(B[1] - O[1], B[0] - O[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    R = math.hypot(A[0] - O[0], A[1] - O[1])
    n = max(2, int(math.ceil(abs(da) * R / step)))
    return [(O[0] + R * math.cos(a0 + da * k / n), O[1] + R * math.sin(a0 + da * k / n)) for k in range(n + 1)], abs(da) * R


def _offsets(row):
    """per profile point: (plan offset from p0, height over p0)"""
    return [dist2(row[p], row[0]) for p in range(4)], [row[p][1] - row[0][1] for p in range(4)]


def walk_scale(A_row, J_row, K, b_dir):
    """the factor the return's walk + verge (every offset past the curb top) is scaled by about the curb top so the
    outermost profile point stays inside COMPRESS_R x R of the arc: 1.0 when it already does. Raises GeomError when
    the radius leaves no room for a walk at all."""
    _tH, _phi, R, _O, _a, _B = corner(K, A_row[0], b_dir)
    oA, _ = _offsets(A_row)
    oJ, _ = _offsets(J_row)
    o_max = max(oA[3], oJ[3])
    o_top = oA[1]
    room = COMPRESS_R * R - o_top
    if room <= 0.1:
        raise GeomError(f"return radius {R:.2f} m leaves no room for a walk behind the curb")
    return min(1.0, room / (o_max - o_top)) if o_max > o_top else 1.0


def compress_row(row, s):
    """a straight-edge curb row (p0..p3 on one plan line) with every profile point past the curb top pulled toward
    it: offset o -> o_top + (o - o_top) * s, along the row's own line; heights kept. s = 1 returns the row itself."""
    if s >= 1.0:
        return tuple(tuple(p) for p in row)
    p0 = row[0]
    n = unit2(row[3][0] - p0[0], row[3][2] - p0[2])
    o_top = dist2(row[1], p0)
    out = [tuple(row[0]), tuple(row[1])]
    for p in (2, 3):
        o = dist2(row[p], p0)
        o2 = o_top + (o - o_top) * s if o > o_top else o
        out.append((p0[0] + n[0] * o2, row[p][1], p0[2] + n[1] * o2))
    return tuple(out)


def host_ramp(host_rows, s, ramp_m=HOST_RAMP_M):
    """the host's curb rows from the gap-end row A (host_rows[0]) AWAY from the mouth: [(k, compressed row)] for A (at
    s) and every row within ramp_m of it, eased back to full (smoothstep of the distance along the host's lane edge),
    so the host's walk tapers into a compressed return instead of stepping. Empty when s = 1."""
    if s >= 1.0:
        return []
    out = []
    acc = 0.0
    for k, row in enumerate(host_rows):
        if k > 0:
            acc += dist2(row[0], host_rows[k - 1][0])
            if acc >= ramp_m:
                break
        t = acc / ramp_m
        out.append((k, compress_row(row, s + (1.0 - s) * (t * t * (3.0 - 2.0 * t)))))
    return out


def return_stations(A_row, J_row, K, b_dir, step=RETURN_STEP_M, y0_of=None):
    """the curb return as station rows (4 engine points each), A_row first and J_row last, plus the corner record.
    A_row / J_row: the host gap-end curb row and the stub's first kept curb row. y0_of(x, z): the lane edge's height
    at a station (tools/author_stubs_blend.py blends the host deck and the stub's edge by distance to each, so the
    corner pavement meets both at their own heights); default linear from A to J along the path.
    The last row is J_row exactly. The first is A_row exactly when the walk needs no compression (walk_scale 1);
    otherwise it is A_row compressed (`compress_row`, rec["A_row"]) — the caller moves the host's own row A there and
    eases the host behind it (`host_ramp`) — and the tail B -> J eases the compression back to 1 (module doc)."""
    A0 = A_row[0]
    tH, phi, R, O, a_dir, B = corner(K, A0, b_dir)
    arc, arc_len = arc_points((A0[0], A0[2]), B, O, step)
    J0 = J_row[0]
    tail = math.hypot(J0[0] - B[0], J0[2] - B[1])
    if (J0[0] - B[0]) * b_dir[0] + (J0[2] - B[1]) * b_dir[1] < -0.05:
        raise GeomError(f"the stub's first kept curb row stands {tail:.2f} m BEFORE the return's end B")
    path = list(arc[1:])                                # arc stations past A (B included)
    nt = int(math.ceil(tail / step)) if tail > 1e-3 else 0
    for k in range(1, nt):
        f = k / nt
        path.append((B[0] + (J0[0] - B[0]) * f, B[1] + (J0[2] - B[1]) * f))
    total = arc_len + tail
    oA, hA = _offsets(A_row)
    oJ, hJ = _offsets(J_row)
    scale = walk_scale(A_row, J_row, K, b_dir)
    A_out = compress_row(A_row, scale)
    rows = [A_out]
    acc = 0.0
    prev = (A0[0], A0[2])
    for k, (x, z) in enumerate(path):
        acc += math.hypot(x - prev[0], z - prev[1])
        prev = (x, z)
        f = min(1.0, acc / total) if total > 0 else 1.0
        on_arc = k < len(arc) - 1
        if on_arc:
            nx, nz = unit2(O[0] - x, O[1] - z)          # outward = toward the circle centre (away from the pavement)
            s = scale
        else:
            nx, nz = unit2(J_row[3][0] - J0[0], J_row[3][2] - J0[2])
            t = min(1.0, max(0.0, (acc - arc_len) / tail)) if tail > 1e-9 else 1.0
            s = scale + (1.0 - scale) * (t * t * (3.0 - 2.0 * t))      # the tail eases back to the stub's own walk
        y0 = A0[1] + (J0[1] - A0[1]) * f if y0_of is None else y0_of(x, z)
        row = []
        for p in range(4):
            o = oA[p] + (oJ[p] - oA[p]) * f
            if p >= 2 and s < 1.0:
                o = oA[1] + (o - oA[1]) * s if o > oA[1] else o
            h = hA[p] + (hJ[p] - hA[p]) * f
            if p == 3:                                   # the grass meet rises to the ground the prep lays there
                wm = min(acc, total - acc) / MEET_RAMP_M if MEET_RAMP_M > 0 else 1.0
                wm = 1.0 if wm >= 1.0 else max(0.0, wm) ** 2 * (3.0 - 2.0 * max(0.0, wm))
                h = h + (MEET_H_M - h) * wm
            row.append((x + nx * o, y0 + h, z + nz * o))
        rows.append(tuple(row))
    rows.append(tuple(tuple(p) for p in J_row))
    rec = {"K": [round(K[0], 3), round(K[2], 3)], "A": [round(A0[0], 3), round(A0[2], 3)],
           "B": [round(B[0], 3), round(B[1], 3)], "J": [round(J0[0], 3), round(J0[2], 3)],
           "O": [round(O[0], 3), round(O[1], 3)], "tangent_m": round(tH, 3), "phi_deg": round(math.degrees(phi), 2),
           "radius_m": round(R, 3), "arc_len_m": round(arc_len, 3), "stations": len(rows), "compress": round(scale, 3),
           "n_arc_rows": len(arc), "tail_m": round(tail, 3)}
    if scale < 1.0:
        rec["A_row"] = [list(p) for p in A_out]
    return rows, rec


def strip_faces(n_rows, base=0, P=4):
    """quads between consecutive 4-point rows laid out row-major: [(a, b, c, d)]"""
    out = []
    for r in range(n_rows - 1):
        a, b = base + r * P, base + (r + 1) * P
        for p in range(P - 1):
            out.append((a + p, a + p + 1, b + p + 1, b + p))
    return out


def corner_pavement(K, Ky, rows, n_arc_rows):
    """the corner pavement fan: K plus every station's lane edge from A up to the last ARC station B (rows[:n_arc_rows];
    past B the return runs straight along the stub edge and the stub's own road is the pavement). Returns (verts,
    tris) with tris facing up."""
    edge = [r[0] for r in rows[:n_arc_rows]]
    verts = [(K[0], Ky, K[2])] + [tuple(p) for p in edge]
    tris = []
    for i in range(1, len(verts) - 1):
        t = (0, i, i + 1)
        tris.append(up_facing(verts, t))
    return verts, tris


def up_facing(verts, t):
    a, b, c = verts[t[0]], verts[t[1]], verts[t[2]]
    ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    return t if ny >= 0 else (t[0], t[2], t[1])


def point_in_poly(x, z, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / ((zj - zi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def tri_height(x, z, a, b, c):
    """the height of triangle abc at (x, z) when the point is inside it in plan, else None"""
    d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if abs(d) < 1e-12:
        return None
    l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
    l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
    l3 = 1.0 - l1 - l2
    if min(l1, l2, l3) < -1e-7:
        return None
    return l1 * a[1] + l2 * b[1] + l3 * c[1]


# ------------------------------------------------------------------------------------------------ barrier

def joint_stations(total_m, keys_m, pitch=MODULE_PITCH_M):
    """the module joints along a barrier of length total_m (module doc): every pitch, symmetric about the middle,
    none within JOINT_CLEAR_M of either end; a joint within JOINT_KEY_CLEAR_M of a profile-point ring (keys_m, their
    arc positions) slides off it to the far side. Returns the joint centres (arc m), ascending."""
    n_full = int(math.floor(total_m / pitch))
    s0 = (total_m - n_full * pitch) / 2.0
    out = []
    gap = JOINT_KEY_CLEAR_M + JOINT_HALF_M
    for k in range(n_full + 1):
        s = s0 + k * pitch
        for _ in range(4):                     # a curb's face and top rings stand 0.08 m apart: slide past the pair
            hit = next((kk for kk in keys_m if abs(s - kk) < gap - 1e-9), None)
            if hit is None:
                break
            s = hit + (1.0 if s >= hit else -1.0) * gap
        if any(abs(s - kk) < gap - 1e-9 for kk in keys_m):
            continue
        if JOINT_CLEAR_M <= s <= total_m - JOINT_CLEAR_M:
            out.append(s)
    return out


def barrier_path(right_row, left_row, ring_m=BARRIER_RING_M, joints=True):
    """plan stations across the stub, right grass meet -> left grass meet: every profile point of both curb rows
    (right p3 p2 p1 p0, left p0 p1 p2 p3) plus <= ring_m between, and (joints) a module joint every MODULE_PITCH_M:
    three stations JOINT_HALF_M apart ('jside', 'joint', 'jside'), the 'mid' stations within 1.5 x JOINT_HALF_M of it
    dropped. right_row / left_row: (p0..p3) engine points of the stub's curb at the barrier. Returns [(x, z, kind)]
    with kind in {'p0'..'p3', 'mid', 'jside', 'joint'}."""
    key = [(right_row[3], "p3"), (right_row[2], "p2"), (right_row[1], "p1"), (right_row[0], "p0"),
           (left_row[0], "p0"), (left_row[1], "p1"), (left_row[2], "p2"), (left_row[3], "p3")]
    out = []
    for (a, ka), (b, kb) in zip(key, key[1:]):
        if not out:
            out.append((a[0], a[2], ka))
        L = dist2(a, b)
        n = max(1, int(math.ceil(L / ring_m)))
        for k in range(1, n):
            f = k / n
            out.append((a[0] + (b[0] - a[0]) * f, a[2] + (b[2] - a[2]) * f, "mid"))
        out.append((b[0], b[2], kb))
    # the two end rings stand END_INSET_M inside the grass meets: a ring exactly on a curb strip's outer boundary edge
    # reads no surface under it (a ray down an edge shared by no second face misses; 2026-10-18, Saint Therese Way on
    # the v0.18.1 road)
    for i, j in ((0, 1), (len(out) - 1, len(out) - 2)):
        x, z, k = out[i]
        L = math.hypot(out[j][0] - x, out[j][1] - z)
        f = min(0.5, END_INSET_M / L) if L > 1e-9 else 0.0
        out[i] = (x + (out[j][0] - x) * f, z + (out[j][1] - z) * f, k)
    if not joints:
        return out
    arcs = [0.0]
    for p, q in zip(out, out[1:]):
        arcs.append(arcs[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
    js = joint_stations(arcs[-1], [a for a, p in zip(arcs, out) if p[2] != "mid"])

    def at(s):
        i = max(0, min(len(out) - 2, next((k for k in range(len(arcs) - 1) if arcs[k + 1] >= s), len(arcs) - 2)))
        f = (s - arcs[i]) / max(1e-12, arcs[i + 1] - arcs[i])
        return (out[i][0] + (out[i + 1][0] - out[i][0]) * f, out[i][1] + (out[i + 1][1] - out[i][1]) * f)
    ins = []
    for s in js:
        for ds, kind in ((-JOINT_HALF_M, "jside"), (0.0, "joint"), (JOINT_HALF_M, "jside")):
            x, z = at(s + ds)
            ins.append((s + ds, (x, z, kind)))
    kept = [(a, p) for a, p in zip(arcs, out)
            if p[2] != "mid" or all(abs(a - s) > 1.5 * JOINT_HALF_M for s in js)]
    return [p for _a, p in sorted(kept + ins, key=lambda t: t[0])]


def _ring(half):
    """a closed strip ring (race_furniture.ring_profile's order) from a half profile ((lat, h) bottom -> top)"""
    return [(-lat, h) for lat, h in half] + [(lat, h) for lat, h in reversed(half)]


def barrier_rings(path, base_of, bury=BARRIER_BURY_M, height=BARRIER_H):
    """ring records for race_furniture.strip_mesh. base_of(x, z, ax, az) -> (lowest surface under the footprint,
    [samples]) where (ax, az) is the profile axis (along the stub). A 'joint' station's ring is Kevin's module END
    profile (JOINT_HALF_PROFILE: the V-groove between two modules); u (ring "arc") is measured from the first joint so
    the texture's module repeat lands on the grooves. Returns (rings, seat rows)."""
    rings, seat = [], []
    arc = 0.0
    n = len(path)
    for i, (x, z, kind) in enumerate(path):
        a = path[max(0, i - 1)]
        b = path[min(n - 1, i + 1)]
        tx, tz = unit2(b[0] - a[0], b[1] - a[1])
        if i > 0:
            arc += math.hypot(x - path[i - 1][0], z - path[i - 1][1])
        ax, az = rf.left_normal(tx, tz)
        low, samples = base_of(x, z, ax, az)
        if low is None:
            raise GeomError(f"no stub surface under the barrier ring at ({x:.2f}, {z:.2f})")
        y = low - bury
        ring = {"cx": x, "cz": z, "y": y, "tx": tx, "tz": tz, "lat": 0.0, "ls": 1.0, "h": height, "arc": arc}
        if kind == "joint":
            ring["prof"] = _ring(tuple((lat, h * height / BARRIER_H) for lat, h in JOINT_HALF_PROFILE))
        rings.append(ring)
        seat.append({"x": round(x, 3), "z": round(z, 3), "kind": kind, "base": round(y, 4),
                     "surface": [None if s is None else round(s, 4) for s in samples]})
    u0 = next((r["arc"] for r, p in zip(rings, path) if p[2] == "joint"), 0.0)
    for r in rings:
        r["arc"] -= u0
    return rings, seat


def barrier_mesh(rings):
    """(verts, faces, uvs) engine frame, outward normals (race_furniture.strip_mesh, both ends capped)"""
    return rf.strip_mesh(rings, True, True)


def footprint_samples(x, z, ax, az, half=BARRIER_HALF_BASE):
    """the plan points a ring's base stands on: back toe, centre, front toe (along the profile axis)"""
    return [(x - ax * half, z - az * half), (x, z), (x + ax * half, z + az * half)]

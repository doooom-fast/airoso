"""Race-layout furniture for the Lake Murray loop — the PURE geometry (no bpy), ledger 0047.

Three kinds of furniture, every one a swept strip authored in the ENGINE frame (x = E, y = up,
z = N) and emitted into Blender by `tools/author_race_furniture_blend.py` with the (x, z, y) remap
and REVERSED winding (LAWS L6: the remap is a reflection):

  centre K-rail chain   `1WALL_race_kbar_<street>_<k>`   Kevin's concrete_barrier_4m.obj silhouette
                                                        swept along `barrier_bands.json` centre runs,
                                                        nose-to-nose with the median islands, continuous
                                                        round the three interior corners, tapered free ends
  kerb-line barriers    `1WALL_race_edge_<L|R>_<street>_<k>`  the same strip on BOTH curb faces, every
                                                        street incl. Alvarado, gapped only inside the
                                                        declared bridge spans (the authored rails are the
                                                        barrier there), straight across every mouth
  race kerbs            `1KERB_race_<apexvertex>_<in|out>`  a 1.0 m x 0.05 m flat rumble strip ON the
                                                        pavement inboard of the edge strip at the five
                                                        corners the sign detector finds (|D| >= 45 deg)

Why strips and not 2,100+ instanced modules: ~130k positions in ~30 objects (each <= MAX_RINGS_PER_OBJECT
rings, render verts well under the exporter's 65,535 split) versus ~2.2 M positions; every
reference measured (SRP, nohesi, Macau, rt_california) ships strips/sheets. The texture tiles at the
module pitch (u = arc / 4.04 m) so the joints still read every 4.04 m.

SHADING (2026-10-11 weld pass): every object is SMOOTH-shaded with hard edges only on real creases —
`sharp_edges` (faces meeting at more than SHARP_DEG = 30 deg: the jersey base corner 90, base/slope 33,
top lip 86, the end caps 90; the slope/upper break is two 17 / 12 deg steps and stays smooth) plus the
kerb outline (`kerb_outline_edges`: ramp/top and top/outer). The exporter (exporter.kn5, AppData
blender-assetto-corsa-tools) welds face corners sharing position + normal + UV + tangent, and the UVs are
per VERTEX (u = arc / pitch along, v across: no seam anywhere), so a smooth-shaded strip ships ~16
render verts per 20-triangle ring interval (~0.8 per triangle) where the flat-shaded one shipped 3.0.
`render_vertex_count` predicts it without Blender.

RING DENSITY (same pass): the plan rings sit on the centreline vertices (~3 m apart), which on the
outside lip of a 10 m corner stretched to 7 m with the strip chording the arc by up to 0.27 m. Every
strip is densified (`densify_rings`) so consecutive rings are <= RING_SPACING_MAX_M apart and the
polyline stays within CHORD_MAX_M of the declared offset curve `offset_xz` (centre lerp + normalised
lerp of the vertex tangents x lerp of the declared lateral) — the inserted rings stand ON that curve.

FOLDS (2026-10-11): at an inside lip tighter than the strip's offset (the five right-handers' inside lips) the
offset curve folds back on itself. The strip and the inside race kerb are TRIMMED to the curb's own corner
(_trim_folds: one mitred corner ring where the offset curve crosses itself, or where its legs extended meet)
instead of dropping the backward rings and chording back across the fold — that left six inside-out strip spans,
a hook of wall standing 1-3.5 m inside three exit carriageways and seven inverted kerb spans. The corners are
what tools/barrier_bands.py declares (`edge_corners`, edge_fold_corners here), so the gates stand on them.

Everything here is testable without Blender: the Blender tool only supplies the deck height per ring
(a BVH ray onto ROAD/CURB) and turns the (verts, faces, uvs) into mesh objects. The corner detector is
tools/place_signs.py's, imported READ-ONLY (that file belongs to the signs workflow).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO / "tools") not in sys.path:
    sys.path.insert(0, str(AIROSO / "tools"))

# ---------------------------------------------------------------------------------------------
# constants — the spec (ledger 0047 FINAL SPEC) in one place
RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")   # upper-case prefix test; the export split keys on these
LIFT = 0.10              # the road ribbon rides +0.10 over centerline y (build_loop_blend.py:654)
BURY_M = 0.05            # strip base sunk this far into the deck (drive_test floating 0.8 m / audit E read 'grounded')
MODULE_PITCH_M = 4.04    # concrete_barrier_4m.obj is 4.04 m long: the texture tiles at that pitch
BARRIER_H = 1.20         # Kevin's module is 1.202 m tall (Q5 offers 0.81-1.07 real K-rail: ONE constant)
# measured half-profile of assets/models/concrete_barrier_4m.obj (249 v): (lateral, height) bottom->top.
# The 1.16/1.20 top chamfer is collapsed into one point so a ring is 10 vertices (10 quads/station).
HALF_PROFILE = ((0.335, 0.00), (0.335, 0.12), (0.164, 0.38), (0.137, 0.47), (0.080, 1.20))
BARRIER_HALF_W = HALF_PROFILE[0][0]
NOSE_HALF = 0.25         # tools/author_median_blend.py NOSE_HALF — the island nose the chain butts into
NOSE_H = 0.30            # chain height at the shared nose vertex (island curb top is 0.18 above the deck)
NOSE_TAPER_RINGS = 3     # the nose ring + the two before it taper 0.335 -> 0.25 / 1.20 -> 0.30
FREE_END_H = 0.30        # free ends (v780 / v4440 / bridge-span gaps): 3-ring height taper 1.20 -> 0.30
FREE_TAPER_RINGS = 3
MAX_RINGS_PER_OBJECT = 800   # 10 positions/ring -> <= 8,000 positions/object; smooth render verts ~16/ring
#                              (12,800 + caps); even fully flat (60/ring) 48,000 + caps < 65,535
RING_SPACING_MAX_M = 3.5     # densify_rings: consecutive rings along a strip at most this far apart (xz)
CHORD_MAX_M = 0.10           # densify_rings: the strip polyline within this of the declared offset curve
DENSIFY_SAMPLES = 16         # samples of the offset curve per sub-interval when measuring the chord error
DENSIFY_MAX_SPLIT = 64       # an interval is cut into at most this many pieces
# fold TRIM (2026-10-11, replaces the one-sided drop): an inside lip tighter than the strip's offset folds
# the offset curve into a swallowtail; the strip is trimmed to the curb's own corner (_trim_folds)
FOLD_SEARCH_RINGS = 12       # vertex rings searched either side of a backward cluster for the crossing legs (~36 m)
FOLD_SEARCH_STATIONS = 120   # the same reach for the 0.3 m kerb stations (~36 m)
FOLD_MERGE_M = 6.0           # backward steps closer than this (along the run's arc) are ONE fold: the 0.3 m kerb stations
#                              saw-tooth back at every ~3 m polyline vertex of a folding lip (two vertex spacings)
FOLD_STRETCH_MIN = 0.5       # an `extend` leg step moves >= this fraction of its centreline step (not curling into the cusp)
FOLD_EXTEND_MAX_M = 8.0      # an `extend` join runs at most this far past either leg's last ring (SD's seam corner: 7.0)
MITRE_MAX = 2.0              # corner ring lateral scale cap 1/cos(psi/2) (2.0 at psi 120 deg; SD's corners 67-93: 1.20-1.45)
MITRE_CLEAR_M = 0.25         # a leg ring stays >= half_w * tan(psi/2) + this from the corner (clear of the reflex mitre tip)
SHARP_DEG = 30.0             # a hard edge where two faces meet at more than this (a real crease)
EDGE_INSET_M = 0.82      # road mode: the strip's road-side face at half_w - 0.82 (curb-side face at half_w - 0.15)
EDGE_WALK_CENTRE_M = 0.445   # walk mode: strip centre at half_w + 0.445 on the sidewalk top (road-side face half_w + 0.11)
KERB_W = 1.0
KERB_H = 0.05            # flat low kerb: below audit K's KERB_STAND_M 0.10 and drive_test's severe step 6 cm
KERB_RAMP_W = 0.10       # rideable lane-side ramp
KERB_CLEAR_M = 0.05      # kerb outer edge 0.05 m clear of the edge strip's road-side face
KERB_STEP_M = 0.3
KERB_TILE_M = 1.0        # kerb_diffuse.png stripes: one tile per metre along
KERB_TAPER_STATIONS = 3
KERB_DEFL_MIN_DEG = 45.0
KERB_EXT_MIN_M, KERB_EXT_MAX_M = 10.0, 30.0   # outside kerb symmetric extension E = clamp(2 R_apex, 10, 30)
CAR_HALF_W = 0.95        # spawn clearance: a 1.9 m car
SPAWN_MARGIN_M = 0.30    # HARD floor (2026-10-11; was a soft note): a car on a grid/pit slot stands >= this off any
#                          strip face — 0.08 m (the 1.4 m stagger) left no room for a spawn wobble or a wider car
COLLIDER_BELOW_M, COLLIDER_ABOVE_M = 0.30, 2.50   # optional invisible sheet (Q11, OFF by default)
STREETS = (("alvarado", 0, 759), ("college", 760, 1514), ("navajo", 1515, 2320),
           ("jackson", 2321, 3297), ("lakemurray", 3298, 4498))
# the spec's centre runs, closed vertex intervals ending ON the island nose vertices (used only when
# data/barrier_bands.json is absent and --standin-bands is given)
SPEC_CENTRE_RUNS = ((780, 846), (1073, 1096), (1258, 1374), (1487, 1540), (1739, 2183), (2297, 4440))
SPEC_CHAIN_LEN_M = 8525.0
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")


# ---------------------------------------------------------------------------------------------
# centreline helpers
def load_centerline(proj):
    local = json.loads((Path(proj) / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in local["points_xyz_m"]]
    widths = [float(w) for w in local["widths_m"]]
    return pts, widths


def unique_count(pts):
    """vertices before the repeated closure vertex (v4498 == v0 on SD)"""
    n = len(pts)
    if n > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6:
        return n - 1
    return n


def stations(pts):
    st = [0.0]
    for i in range(1, len(pts)):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return st


def tangent(pts, k, m):
    """unit tangent at vertex k from pts[k-1] -> pts[k+1] on the closed ring of m unique vertices"""
    a, b = pts[(k - 1) % m], pts[(k + 1) % m]
    dx, dz = b[0] - a[0], b[2] - a[2]
    d = math.hypot(dx, dz) or 1.0
    return dx / d, dz / d


def left_normal(tx, tz):
    """left of forward travel (x = E, z = N); right = the negative"""
    return -tz, tx


def street_slug(name):
    """'Lake Murray Boulevard' -> 'lakemurray': a mesh-name-safe token (no spaces, no suffix word)"""
    drop = ("road", "avenue", "drive", "boulevard", "blvd", "rd", "ave", "dr")
    words = [w for w in name.lower().replace("-", " ").split() if w not in drop]
    return "".join(ch for ch in "".join(words) if ch.isalnum()) or "loop"


def street_table(bands=None):
    """[(slug, i, j)]: the declaration's `streets` table when the bands carry one (tools/barrier_bands.py
    puts the boundaries at the corner apexes), else the spec's measured table — so an object's street
    token and split point come from the same file the gates read"""
    rows = (bands or {}).get("streets") or []
    if rows:
        return [(street_slug(r["street"]), int(r["vertex_from"]), int(r["vertex_to"])) for r in rows]
    return list(STREETS)


def street_of(k, table=None):
    for name, i, j in (table or STREETS):
        if i <= k <= j:
            return name
    return "loop"


def is_race_name(name):
    return name.upper().startswith(RACE_PREFIXES)


def yaw_blender(tx, tz, direction="forward"):
    """Blender rotation_euler.z for a facing dummy: the exporter's (x, z, -y) conversion makes
    atan2(tx, -tz) the kn5-frame travel heading (measured: deepforest +1.00, today's SD -0.91)"""
    yaw = math.atan2(tx, -tz)
    return yaw + math.pi if direction == "reverse" else yaw


# ---------------------------------------------------------------------------------------------
# the profile and the sweep
def ring_profile(lat_scale=1.0, height=BARRIER_H):
    """closed 10-vertex ring in the cross-section plane: (lat, h), lat > 0 = LEFT of travel.
    Order: right base -> up the right face -> across the top -> down the left face -> (bottom edge
    closes back to the right base). Scaled proportionally for the nose taper."""
    hs = height / BARRIER_H
    right = [(-lat * lat_scale, h * hs) for lat, h in HALF_PROFILE]
    left = [(lat * lat_scale, h * hs) for lat, h in reversed(HALF_PROFILE)]
    return right + left


def ring_perimeter_v(ring):
    """v coordinate (0..1) around the ring by cumulative perimeter"""
    cum = [0.0]
    for i in range(1, len(ring)):
        cum.append(cum[-1] + math.hypot(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]))
    L = cum[-1] or 1.0
    return [c / L for c in cum]


def taper(idx, n, start_kind, end_kind):
    """(lat_scale, height) of ring idx in a run of n rings; ends are 'nose' or 'free'"""
    ls, h = 1.0, BARRIER_H
    for d, kind in ((idx, start_kind), (n - 1 - idx, end_kind)):
        if kind == "nose" and d < NOSE_TAPER_RINGS:
            f = d / NOSE_TAPER_RINGS
            ls = min(ls, NOSE_HALF / BARRIER_HALF_W + (1.0 - NOSE_HALF / BARRIER_HALF_W) * f)
            h = min(h, NOSE_H + (BARRIER_H - NOSE_H) * f)
        elif kind == "free" and d < FREE_TAPER_RINGS:
            f = d / FREE_TAPER_RINGS
            h = min(h, FREE_END_H + (BARRIER_H - FREE_END_H) * f)
    return ls, h


def strip_mesh(rings, cap_start, cap_end, u_scale=MODULE_PITCH_M):
    """A closed swept solid from ring records. Each ring: dict(cx, cz, y, tx, tz, lat, ls, h, arc).
    Returns (verts, faces, uvs) in the ENGINE frame with OUTWARD normals under the right-hand rule
    (the Blender tool remaps + reverses). u = arc / u_scale, v = perimeter fraction."""
    verts, faces, uvs = [], [], []
    P = len(ring_profile())
    rows = []
    for r in rings:
        prof = ring_profile(r["ls"], r["h"])
        vv = ring_perimeter_v(prof)
        lx, lz = left_normal(r["tx"], r["tz"])
        base = len(verts)
        u = r["arc"] / u_scale
        for (lat, h), v in zip(prof, vv):
            off = r["lat"] + lat
            verts.append((r["cx"] + lx * off, r["y"] + h, r["cz"] + lz * off))
            uvs.append((u, v))
        rows.append(base)
    for a, b in zip(rows[:-1], rows[1:]):
        for i in range(P):
            j = (i + 1) % P
            faces.append((a + i, a + j, b + j, b + i))
    # end caps: zig-zag between the two mirrored sides (the jersey profile has a shallow concave kink
    # at the toe, so a fan from one vertex could overlap; the ladder never does). The ring order
    # (right base -> up -> over the top -> down the left) is CLOCKWISE seen from +t, so the plain
    # ladder faces -t: right for the START cap, reversed for the END cap (tests/tools/test_race_furniture
    # pins it: every directed edge matched once, volume > 0).
    def ladder(base, reverse):
        tris = []
        lo, hi = 0, P - 1
        while hi - lo > 1:
            tris.append((base + lo, base + hi, base + lo + 1))
            lo += 1
            if hi - lo > 1:
                tris.append((base + lo, base + hi, base + hi - 1))
                hi -= 1
        return [tuple(reversed(t)) for t in tris] if reverse else tris
    if cap_start and rows:
        faces += ladder(rows[0], reverse=False)    # faces -t
    if cap_end and rows:
        faces += ladder(rows[-1], reverse=True)    # faces +t
    return verts, faces, uvs


def kerb_mesh(stations_, side, u_scale=KERB_TILE_M):
    """Open rumble-strip profile per station: lane lip (0, 0) -> ramp top (0.10, h) -> outer top
    (1.0, h) -> outer base (1.0, 0), offsets OUTWARD from the lane lip. Each station: dict(cx, cz, y,
    tx, tz, lip (lateral of the lane lip, signed +left), h, arc). u across the profile, v = arc / 1 m.
    A trimmed fold's corner station carries `ls` (the mitre scale 1/cos(psi/2)): its profile is
    stretched about the kerb's mid-line so both edges meet their legs' edges as a mitre."""
    verts, faces, uvs = [], [], []
    prof = ((0.0, 0.0), (KERB_RAMP_W, 1.0), (KERB_W, 1.0), (KERB_W, 0.0))
    us = (0.0, 0.1, 0.9, 1.0)
    rows = []
    for s in stations_:
        lx, lz = left_normal(s["tx"], s["tz"])
        base = len(verts)
        for (o, hf), u in zip(prof, us):
            if "ls" in s:
                off = s["lip"] + side * KERB_W / 2.0 + side * (o - KERB_W / 2.0) * s["ls"]
            else:
                off = s["lip"] + side * o
            verts.append((s["cx"] + lx * off, s["y"] + hf * s["h"], s["cz"] + lz * off))
            uvs.append((u, s["arc"] / u_scale))
        rows.append(base)
    for a, b in zip(rows[:-1], rows[1:]):
        for i in range(3):
            q = (a + i, a + i + 1, b + i + 1, b + i)
            faces.append(q if side > 0 else (q[0], q[3], q[2], q[1]))
    return verts, faces, uvs


def to_blender(verts, faces):
    """engine (x, y_up, z_north) -> Blender (x, z_north, y_up) is a reflection: reverse every face"""
    return [(x, z, y) for (x, y, z) in verts], [tuple(reversed(f)) for f in faces]


def signed_volume(verts, faces):
    """divergence-theorem volume of a closed triangulated/quad mesh: > 0 when normals point outward"""
    vol = 0.0
    for f in faces:
        for k in range(1, len(f) - 1):
            a, b, c = verts[f[0]], verts[f[k]], verts[f[k + 1]]
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                    + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return vol


def face_normal(verts, f):
    a, b, c = verts[f[0]], verts[f[1]], verts[f[2]]
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])


# ---------------------------------------------------------------------------------------------
# shading: smooth everywhere, hard only on real creases (what the exporter's weld needs)
def newell_normal(verts, f):
    """unit polygon normal by Newell's method (Blender's own for a non-planar quad); (0,0,0) if degenerate"""
    nx = ny = nz = 0.0
    for i in range(len(f)):
        a, b = verts[f[i]], verts[f[(i + 1) % len(f)]]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    L = math.sqrt(nx * nx + ny * ny + nz * nz)
    return (nx / L, ny / L, nz / L) if L > 0 else (0.0, 0.0, 0.0)


def edge_faces(faces):
    """{(a, b) with a < b: [face indices using that edge]}"""
    out = {}
    for fi, f in enumerate(faces):
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            out.setdefault((a, b) if a < b else (b, a), []).append(fi)
    return out


def sharp_edges(verts, faces, max_deg=SHARP_DEG):
    """the manifold edges whose two faces meet at more than max_deg (the Blender 4.2
    Mesh.set_sharp_from_angle rule, pure): sorted [(a, b), a < b]. Boundary edges (one face) need no
    mark — the fan ends there anyway. Frame-independent (a reflection with reversed winding keeps every
    dihedral)."""
    cos_max = math.cos(math.radians(max_deg))
    normals = [newell_normal(verts, f) for f in faces]
    out = []
    for e, fs in edge_faces(faces).items():
        if len(fs) != 2:
            continue
        n0, n1 = normals[fs[0]], normals[fs[1]]
        if n0[0] * n1[0] + n0[1] * n1[1] + n0[2] * n1[2] < cos_max:
            out.append(e)
    return sorted(out)


def kerb_outline_edges(n_stations):
    """the race kerb's hard outline: along every station interval the ramp/top edge (profile vertex 1)
    and the top/outer edge (profile vertex 2) — the flat top reads as a flat plate. kerb_mesh lays 4
    vertices per station (lip, ramp top, outer top, outer base)."""
    out = []
    for q in range(n_stations - 1):
        a, b = 4 * q, 4 * (q + 1)
        out += [(a + 1, b + 1), (a + 2, b + 2)]
    return out


def render_vertex_count(n_verts, faces, sharp):
    """what the exporter emits for a smooth-shaded mesh with per-vertex UVs: one vertex per (position,
    smooth fan) — the faces round a vertex joined across its non-sharp manifold edges. (A flat-shaded
    triangulated mesh is 3 per triangle.)"""
    sharp = {(a, b) if a < b else (b, a) for a, b in sharp}
    ef = edge_faces(faces)
    by_vertex = [[] for _ in range(n_verts)]
    for fi, f in enumerate(faces):
        for v in f:
            by_vertex[v].append(fi)
    total = 0
    for v, fs in enumerate(by_vertex):
        if not fs:
            continue
        parent = {fi: fi for fi in fs}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for fi in fs:
            f = faces[fi]
            i = f.index(v)
            for w in (f[i - 1], f[(i + 1) % len(f)]):
                e = (v, w) if v < w else (w, v)
                fe = ef.get(e, [])
                if len(fe) == 2 and e not in sharp:          # both faces hold v, so both are in `parent`
                    a, b = find(fe[0]), find(fe[1])
                    if a != b:
                        parent[a] = b
        total += len({find(fi) for fi in fs})
    return total


def triangle_count(faces):
    return sum(len(f) - 2 for f in faces)


# ---------------------------------------------------------------------------------------------
# bands: the declaration the gates read (written by tools/barrier_bands.py — the data agent's file)
def load_bands(proj):
    p = Path(proj) / "data" / "barrier_bands.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def intervals(flags, m, wrap=True):
    """maximal [i, j] intervals (inclusive, on the ring of m vertices) where flags[k] is truthy;
    a run crossing the seam is returned as one interval with j < i"""
    on = [bool(flags[k]) for k in range(m)]
    if all(on):
        return [(0, m - 1)]
    if not any(on):
        return []
    start = next(k for k in range(m) if not on[k]) if wrap else 0
    out, cur = [], None
    for q in range(m):
        k = (start + q) % m if wrap else q
        if on[k]:
            if cur is None:
                cur = [k, k]
            else:
                cur[1] = k
        elif cur is not None:
            out.append(tuple(cur))
            cur = None
    if cur is not None:
        out.append(tuple(cur))
    return out


def walk(i, j, m):
    """vertex indices from i to j inclusive, wrapping past the seam when j < i"""
    if j >= i:
        return list(range(i, j + 1))
    return list(range(i, m)) + list(range(0, j + 1))


def standin_bands(pts, widths, island_w, mouths, spans, race_cfg=None, corners=None):
    """A STAND-IN for data/barrier_bands.json built from the spec's vertex runs (centre chain), the
    declared bridge spans (edge gaps) and the detector's corners (kerbs). Used only when the data
    agent's file is absent and the caller passes --standin-bands; flagged `_standin: true`."""
    race_cfg = race_cfg or {}
    n = len(pts)
    m = unique_count(pts)
    st = stations(pts)
    runs_c = [tuple(r) for r in race_cfg.get("centre_runs") or SPEC_CENTRE_RUNS]
    centre_w = [0.0] * n
    bw = float(race_cfg.get("barrier_width_m", 2 * BARRIER_HALF_W))
    for i, j in runs_c:
        for k in walk(i, j, m):
            centre_w[k] = bw
    inset = float(race_cfg.get("edge_inset_m", EDGE_INSET_M))
    edge_inset = [inset] * n
    for s0, s1 in spans:
        for k in range(n):
            if s0 <= st[k] <= s1:
                edge_inset[k] = 0.0
    centre_w[n - 1] = centre_w[0]
    edge_inset[n - 1] = edge_inset[0]
    runs = [{"kind": "centre", "i": i, "j": j, "street": street_of(i)} for i, j in runs_c]
    for side in ("L", "R"):
        for i, j in intervals(edge_inset, m):
            runs.append({"kind": f"edge_{side}", "i": i, "j": j, "street": street_of(i)})
    closed = []
    for mo in mouths:
        if mo.get("host") != "MAINLINE":
            continue
        k = int(mo["host_vertex"])
        side = int(mo["side"])
        nv = int(math.ceil((float(mo["connector_width_m"]) / 2.0 + 3.0) / 3.0))
        poly = []
        for q in (k - nv, k, k + nv):
            q %= m
            tx, tz = tangent(pts, q, m)
            lx, lz = left_normal(tx, tz)
            lat = side * (widths[q] / 2.0 - inset + BARRIER_HALF_W)
            poly.append([round(pts[q][0] + lx * lat, 3), round(pts[q][2] + lz * lat, 3)])
        closed.append({"connector": mo.get("connector"), "host_vertex": k, "side": side, "xz": poly})
    chain_len = sum(st[j] - st[i] if j >= i else st[m] - st[i] + st[j] for i, j in runs_c)
    out = {
        "_standin": True,
        "_doc": "STAND-IN written by tools/race_furniture.standin_bands from the spec's vertex runs — "
                "replace with tools/barrier_bands.py's measured file before any ship run",
        "centre_w_by_vertex": centre_w,
        "edge_inset_by_vertex": edge_inset,
        "runs": runs,
        "closed_mouths": closed,
        "kerbs": [{"apex": kb["apex_vertex"], "side": kb["side"], "i": kb["i"], "j": kb["j"], "kind": kb["kind"]}
                  for c in (corners or []) for kb in c["kerbs"]],
        "params": {"edge_mode": race_cfg.get("edge_mode", "road"), "edge_inset_m": inset,
                   "barrier_width_m": bw, "barrier_height_m": float(race_cfg.get("barrier_height_m", BARRIER_H)),
                   "module_pitch_m": MODULE_PITCH_M, "chain_length_m": round(chain_len, 1),
                   "bridge_spans_m": [list(s) for s in spans]},
    }
    return out


def check_bands(bands, pts, island_w):
    """the band writer's self-gates, re-run on whatever file we were handed; returns a list of problems"""
    n = len(pts)
    m = unique_count(pts)
    cw = bands["centre_w_by_vertex"]
    probs = []
    if len(cw) != n:
        return [f"centre_w_by_vertex has {len(cw)} entries, centerline {n}"]
    runs_c = [(r["i"], r["j"]) for r in bands.get("runs", []) if r["kind"] == "centre"] or \
             intervals(cw, m)
    ends = {i for i, _ in runs_c} | {j for _, j in runs_c}
    on_island = [k for k in range(m) if cw[k] > 0 and island_w[k] > 0 and k not in ends]
    if on_island:
        probs.append(f"{len(on_island)} centre verts on an island beyond the nose (first {on_island[:5]})")
    on_alv = [k for k in range(0, 780) if cw[k] > 0]
    if on_alv:
        probs.append(f"{len(on_alv)} centre verts on Alvarado/the hairpin flare v0-779 (first {on_alv[:5]})")
    st = stations(pts)
    chain_len = sum(st[j] - st[i] if j >= i else st[m] - st[i] + st[j] for i, j in runs_c)
    if abs(chain_len - SPEC_CHAIN_LEN_M) > 60.0:
        probs.append(f"chain length {chain_len:.0f} m vs spec {SPEC_CHAIN_LEN_M:.0f} +- 60")
    return probs


# ---------------------------------------------------------------------------------------------
# ring plans: WHERE every ring goes (the Blender tool adds y and emits the mesh)
def _plan_run(pts, widths, m, st, ks, lat_fn, start_kind, end_kind, height, kind, street, side, run):
    rings = []
    arc = 0.0
    prev = None
    for idx, k in enumerate(ks):
        if prev is not None:
            arc += math.hypot(pts[k][0] - pts[prev][0], pts[k][2] - pts[prev][2])
        prev = k
        tx, tz = tangent(pts, k, m)
        ls, h = taper(idx, len(ks), start_kind, end_kind)
        rings.append({"k": k, "u": 0.0, "s": st[k], "cx": pts[k][0], "cz": pts[k][2], "y_hint": pts[k][1] + LIFT,
                      "tx": tx, "tz": tz, "lat": lat_fn(k), "ls": ls, "h": h * (height / BARRIER_H),
                      "arc": arc})
    return {"kind": kind, "street": street, "side": side, "run": list(run), "rings": rings,
            "start_kind": start_kind, "end_kind": end_kind}


def split_plan(plan, max_rings=MAX_RINGS_PER_OBJECT):
    """split one run into objects of <= max_rings rings; neighbours SHARE their boundary ring (zero
    gap, no cap); only the run's true ends get a cap"""
    rings = plan["rings"]
    if len(rings) <= max_rings:
        return [dict(plan, cap_start=True, cap_end=True, part=0)]
    n_parts = math.ceil((len(rings) - 1) / (max_rings - 1))
    step = math.ceil((len(rings) - 1) / n_parts)
    parts = []
    a = 0
    p = 0
    while a < len(rings) - 1:
        b = min(len(rings) - 1, a + step)
        parts.append(dict(plan, rings=rings[a:b + 1], cap_start=(a == 0), cap_end=(b == len(rings) - 1), part=p))
        a = b
        p += 1
    return parts


# ---------------------------------------------------------------------------------------------
# ring density: the strip polyline vs the declared offset curve
def offset_xz(a, b, u):
    """the declared offset curve between two VERTEX rings a (vertex k) and b (vertex k+1): the centre
    lerped along the centreline segment, the left normal of the normalised lerp of the two vertex
    tangents, the lerp of the two declared laterals. u = 0 / 1 return a's / b's own strip centre exactly,
    so every ring the plan already had lies on it."""
    cx = a["cx"] + (b["cx"] - a["cx"]) * u
    cz = a["cz"] + (b["cz"] - a["cz"]) * u
    tx = a["tx"] + (b["tx"] - a["tx"]) * u
    tz = a["tz"] + (b["tz"] - a["tz"]) * u
    L = math.hypot(tx, tz) or 1.0
    lx, lz = left_normal(tx / L, tz / L)
    lat = a["lat"] + (b["lat"] - a["lat"]) * u
    return cx + lx * lat, cz + lz * lat


def seg_dist(p, a, b):
    """xz distance from p to the segment a-b"""
    ax, az = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + az * az
    t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * az) / L2))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * az)


def chord_error(a, b, u0=0.0, u1=1.0, samples=DENSIFY_SAMPLES):
    """max distance of the offset curve between u0 and u1 from the straight chord the strip draws there"""
    p0, p1 = offset_xz(a, b, u0), offset_xz(a, b, u1)
    return max([seg_dist(offset_xz(a, b, u0 + (u1 - u0) * i / samples), p0, p1) for i in range(1, samples)] or [0.0])


def _runs_forward(a, b, steps=64):
    """the offset curve advances along the travel tangent everywhere between a and b (an inside lip
    tighter than its offset runs backwards — that span stays the fold-drop chord)"""
    prev = offset_xz(a, b, 0.0)
    for i in range(1, steps + 1):
        u = i / steps
        cur = offset_xz(a, b, u)
        tx = a["tx"] + (b["tx"] - a["tx"]) * u
        tz = a["tz"] + (b["tz"] - a["tz"]) * u
        if (cur[0] - prev[0]) * tx + (cur[1] - prev[1]) * tz <= 0.0:
            return False
        prev = cur
    return True


def interp_ring(a, b, u):
    """a ring ON the offset curve at fraction u of the vertex interval a -> b: centre, tangent, lateral,
    taper, deck hint and texture arc interpolated (u = arc / pitch stays continuous); k stays a's vertex"""
    r = {key: val for key, val in a.items() if key != "y"}
    for key in ("cx", "cz", "y_hint", "lat", "ls", "h", "arc"):
        r[key] = a[key] + (b[key] - a[key]) * u
    tx, tz = a["tx"] + (b["tx"] - a["tx"]) * u, a["tz"] + (b["tz"] - a["tz"]) * u
    L = math.hypot(tx, tz) or 1.0
    r["tx"], r["tz"] = tx / L, tz / L
    r["s"] = a["s"] + u * math.hypot(b["cx"] - a["cx"], b["cz"] - a["cz"])
    r["u"] = u
    r["inserted"] = True
    return r


def _strip_xz(r):
    lx, lz = left_normal(r["tx"], r["tz"])
    return r["cx"] + lx * r["lat"], r["cz"] + lz * r["lat"]


def fill_ring(a, b, f):
    """a ring ON THE STRAIGHT CHORD a -> b at fraction f — the chord IS the strip there (a trimmed fold's
    leg running into its mitred corner ring, or a vertex pair whose offset curve runs backwards): the
    position lerped, the profile SQUARE TO THE CHORD (the leg is a prism that meets the corner's mitre
    plane flat — the old lerp of the two end tangents twisted it by up to psi / 2), the corner ring's
    mitre scale never inherited (a fill ring next to a corner keeps its leg's width), everything else
    lerped"""
    r = {key: val for key, val in a.items() if key not in ("y", "corner", "corner_turn_deg")}
    pa, pb = _strip_xz(a), _strip_xz(b)
    px, pz = pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f
    tx, tz = pb[0] - pa[0], pb[1] - pa[1]
    if math.hypot(tx, tz) < 1e-9:
        tx, tz = a["tx"] + (b["tx"] - a["tx"]) * f, a["tz"] + (b["tz"] - a["tz"]) * f
    L = math.hypot(tx, tz) or 1.0
    r["tx"], r["tz"] = tx / L, tz / L
    for key in ("y_hint", "lat", "h", "arc", "s"):
        r[key] = a[key] + (b[key] - a[key]) * f
    if a.get("corner") and not b.get("corner"):
        r["ls"] = b["ls"]
    elif b.get("corner") and not a.get("corner"):
        r["ls"] = a["ls"]
    else:
        r["ls"] = a["ls"] + (b["ls"] - a["ls"]) * f
    lx, lz = left_normal(r["tx"], r["tz"])
    r["cx"], r["cz"] = px - lx * r["lat"], pz - lz * r["lat"]      # so that cx + left * lat is the chord point
    r["u"] = None
    r["inserted"] = r["fold_fill"] = True
    return r


def densify_rings(rings, m, max_spacing=RING_SPACING_MAX_M, max_chord=CHORD_MAX_M):
    """Insert rings between every pair of consecutive VERTEX rings (k, k+1) until each piece is
    <= max_spacing long and within max_chord of the offset curve (uniform cuts in u, the fewest that
    pass). A pair that is not adjacent on the centreline (a fold-drop chord) or whose curve runs
    backwards has no curve to follow: it is only cut into <= max_spacing pieces ON its straight chord
    (`fill_ring`). Each ring gets `seg_chord_m`: the chord error of the span to the next ring (None
    after the last ring and along a fold chord). Returns (rings, n_inserted)."""
    if len(rings) < 2:
        return rings, 0
    out = []
    n_ins = 0

    def fold_fill(a, b):
        pa, pb = _strip_xz(a), _strip_xz(b)
        n = max(1, math.ceil(math.hypot(pb[0] - pa[0], pb[1] - pa[1]) / max_spacing))
        a["seg_chord_m"] = None
        added = []
        for i in range(1, n):
            r = fill_ring(a, b, i / n)
            r["seg_chord_m"] = None
            added.append(r)
        return added
    for a, b in zip(rings, rings[1:]):
        out.append(a)
        if (b["k"] - a["k"]) % m != 1 or a.get("u", 0.0) != 0.0 or b.get("u", 0.0) != 0.0:
            add = fold_fill(a, b)
            out += add
            n_ins += len(add)
            continue

        def ok(n):
            for i in range(n):
                u0, u1 = i / n, (i + 1) / n
                p0, p1 = offset_xz(a, b, u0), offset_xz(a, b, u1)
                if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) > max_spacing or chord_error(a, b, u0, u1) > max_chord:
                    return False
            return True
        n = 1
        while n < DENSIFY_MAX_SPLIT and not ok(n):
            n += 1
        if n > 1 and not _runs_forward(a, b):
            add = fold_fill(a, b)
            out += add
            n_ins += len(add)
            continue
        a["seg_chord_m"] = round(chord_error(a, b, 0.0, 1.0 / n), 4)
        for i in range(1, n):
            r = interp_ring(a, b, i / n)
            r["seg_chord_m"] = round(chord_error(a, b, i / n, (i + 1) / n), 4)
            out.append(r)
            n_ins += 1
    rings[-1]["seg_chord_m"] = None
    out.append(rings[-1])
    return out, n_ins


def ring_stats(rings):
    """(max consecutive xz spacing of the strip centres, max seg_chord_m, fold/unmeasured spans) of a
    planned ring list"""
    sp = 0.0
    for a, b in zip(rings, rings[1:]):
        pa, pb = _strip_xz(a), _strip_xz(b)
        sp = max(sp, math.hypot(pb[0] - pa[0], pb[1] - pa[1]))
    chords = [r.get("seg_chord_m") for r in rings[:-1]]
    return sp, max([c for c in chords if c is not None] or [0.0]), sum(1 for c in chords if c is None)


def _count_inserted(parts):
    """part['densified'] = the rings densify_rings inserted in this part (a part's first ring is the
    previous part's last, so it is not counted twice)"""
    for part in parts:
        part["densified"] = sum(1 for r in part["rings"][1:] if r.get("inserted"))
    return parts


def chain_plans(pts, widths, island_w, bands, height=BARRIER_H):
    m = unique_count(pts)
    st = stations(pts)
    cw = bands["centre_w_by_vertex"]
    runs = [(r["i"], r["j"]) for r in bands.get("runs", []) if r["kind"] == "centre"] or intervals(cw, m)
    table = street_table(bands)
    plans = []
    for i, j in runs:
        ks = walk(i, j, m)
        sk = "nose" if island_w[i] > 0 else "free"
        ek = "nose" if island_w[j] > 0 else "free"
        plan = _plan_run(pts, widths, m, st, ks, lambda k: 0.0, sk, ek, height, "chain", street_of(i, table), "C", (i, j))
        # lat 0: the offset curve IS the centreline chord, so this only ever splits a > 3.5 m vertex gap
        plan["rings"], _ = densify_rings(plan["rings"], m)
        plans += _count_inserted(split_plan(plan))
    return plans


def edge_lateral(half_w, inset, mode):
    """lateral (unsigned) of the strip CENTRE for a road half-width"""
    if mode == "walk":
        return half_w + EDGE_WALK_CENTRE_M
    return half_w - inset + BARRIER_HALF_W


def edge_plans(pts, widths, bands, mode="road", height=BARRIER_H):
    """both curb faces: one swept run per edge interval (the gaps are the declared bridge spans, free
    tapered ends), every inside-lip fold TRIMMED on the WHOLE run first (trim_folded_rings: one mitred
    corner ring where the offset curve's legs meet — the curb's own corner), then cut at street
    boundaries (the boundary ring shared: zero gap, no cap) so every object is named for its street.
    The declaration wins: when data/barrier_bands.json carries `edge_corners` (tools/barrier_bands.py,
    the same computation) every trimmed corner must be one it declares, and every declared corner must
    be trimmed — else SystemExit (re-run the band writer)."""
    m = unique_count(pts)
    st = stations(pts)
    ei = bands["edge_inset_by_vertex"]
    table = street_table(bands)
    plans = []
    found = []
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        for i, j in intervals(ei, m):
            ks = walk(i, j, m)
            whole = _plan_run(pts, widths, m, st, ks,
                              lambda k, s=sgn: s * edge_lateral(widths[k] / 2.0, ei[k] or EDGE_INSET_M, mode),
                              "free", "free", height, "edge", street_of(ks[0], table), side, (i, j))
            rings, skipped, corners = trim_folded_rings(whole["rings"])
            found += [dict(c, side=side) for c in corners]
            assigned = set()
            rings, _ = densify_rings(rings, m)      # AFTER the trim: the two corner spans stay straight chords
            pieces, cur = [], [rings[0]]
            for r in rings[1:]:
                cur.append(r)
                if street_of(r["k"], table) != street_of(cur[0]["k"], table) and r is not rings[-1]:
                    pieces.append(cur)
                    cur = [r]
            pieces.append(cur)
            for pi, pr in enumerate(pieces):
                sk = "free" if pi == 0 else "join"
                ek = "free" if pi == len(pieces) - 1 else "join"
                plan = dict(whole, rings=pr, street=street_of(pr[0]["k"], table), run=(pr[0]["k"], pr[-1]["k"]),
                            start_kind=sk, end_kind=ek)
                for part in _count_inserted(split_plan(plan)):
                    part["cap_start"] = part["cap_start"] and sk == "free"
                    part["cap_end"] = part["cap_end"] and ek == "free"
                    # each trimmed corner is reported ONCE, by the object that holds its corner ring
                    mine = [ci for ci, c in enumerate(corners) if ci not in assigned and any(
                        r.get("corner") and math.dist(_strip_xz(r), c["xz"]) <= 2e-3 for r in part["rings"])]
                    assigned.update(mine)
                    part["fold_corners"] = [dict(corners[ci], side=side) for ci in mine]
                    part["fold_skipped"] = sum(corners[ci]["n_removed"] for ci in mine)
                    plans.append(part)
            if len(assigned) != len(corners) or sum(c["n_removed"] for c in corners) != skipped:
                raise SystemExit(f"[race] edge {side} run v{i}-v{j}: {len(corners)} trimmed corners, {len(assigned)} found "
                                 f"in the swept objects — the corner rings went missing between trim and split")
    match_declared_corners(bands, found)
    return plans


# ---------------------------------------------------------------------------------------------
# corners -> race kerbs (tools/place_signs.py's detector, read-only)
def detect_kerb_corners(pts, widths, bands, min_defl=KERB_DEFL_MIN_DEG):
    import place_signs as ps   # noqa: E402  (the signs workflow's file; imported, never edited)
    rb = ps.Ribbon("MAINLINE", pts, widths, True)
    cw = bands["centre_w_by_vertex"]
    out = []
    for c in ps.detect_corners(rb):
        if abs(c["D_deg"]) < min_defl:
            continue
        apex_v = rb.vertex(c["apex"])
        inside = "L" if c["sign"] > 0 else "R"
        outside = "R" if inside == "L" else "L"
        E = max(KERB_EXT_MIN_M, min(KERB_EXT_MAX_M, 2.0 * c["R_apex_m"]))
        pc, pt = c["PC"], c["PT"]
        arc = (pt - pc) % rb.n
        kerbs = [{"apex_vertex": apex_v, "apex_station": c["apex"], "side": outside, "kind": "out",
                  "s0": (pc - E) % rb.L, "s1": (pc + arc + E) % rb.L,
                  "i": rb.vertex(int(round(pc - E))), "j": rb.vertex(int(round(pc + arc + E)))}]
        chained = cw[apex_v] > 0
        if not chained:
            kerbs.append({"apex_vertex": apex_v, "apex_station": c["apex"], "side": inside, "kind": "in",
                          "s0": float(pc), "s1": float((pc + arc) % rb.L),
                          "i": rb.vertex(pc), "j": rb.vertex(pt)})
        out.append({"apex_vertex": apex_v, "apex_station": c["apex"], "sign": c["sign"], "R_apex_m": round(c["R_apex_m"], 1),
                    "D_deg": round(c["D_deg"], 1), "PC": pc, "PT": pt, "arc_m": arc, "E_m": round(E, 1),
                    "chained": chained, "kerbs": kerbs})
    return rb, out


def apply_declared_kerbs(rb, corners, bands):
    """The declaration wins: where data/barrier_bands.json carries a `kerbs` run for the same
    (apex, side) — tools/barrier_bands.py's [PC-E, PT+E] / [PC, PT], already clipped for bridge
    clearance (the seam corner's outside kerb starts at v4492, after the I-8 span, not v4484) — its
    i/j replace the detector's own so the authored kerb IS the declared band (the median_zone
    precedent). Kinds 'outside'/'inside' map to 'out'/'in'. Stations come from the ribbon's own
    cumulative length (rb.cum[k]), the frame the detector's PC/PT live in. Returns the declared runs
    nothing in the detector's corner table matched (an author-time warning; verify_race's gate)."""
    KIND = {"outside": "out", "inside": "in", "out": "out", "in": "in"}
    declared = {(int(kb["apex"]), str(kb["side"]).upper()): kb for kb in (bands.get("kerbs") or [])}
    matched = set()
    n = len(rb.raw)
    for c in corners:
        for kb in c["kerbs"]:
            d = declared.get((c["apex_vertex"], kb["side"]))
            if d is None:
                continue
            i, j = int(d["i"]) % n, int(d["j"]) % n
            kb.update({"i": i, "j": j, "s0": float(rb.cum[i]), "s1": float(rb.cum[j]),
                       "kind": KIND.get(str(d.get("kind", kb["kind"])).lower(), kb["kind"]), "declared": True})
            matched.add((c["apex_vertex"], kb["side"]))
    return [d for key, d in declared.items() if key not in matched]


def kerb_plans(rb, corners, bands, mode="road"):
    """0.3 m stations along each kerb run: lane lip at half_w - inset - KERB_CLEAR - KERB_W (road
    mode) or half_w - 0.05 - KERB_W (walk mode); height tapers over the first/last 3 stations"""
    cw_ei = bands["edge_inset_by_vertex"]
    plans = []
    for c in corners:
        for kb in c["kerbs"]:
            s0, s1 = kb["s0"], kb["s1"]
            length = (s1 - s0) % rb.L
            n_st = max(2, int(length / KERB_STEP_M) + 1)
            sgn = 1.0 if kb["side"] == "L" else -1.0
            sts = []
            for q in range(n_st):
                s = (s0 + q * KERB_STEP_M) % rb.L if q < n_st - 1 else s1
                x, z, y, w, vf = rb._interp(s)
                xa, za = rb._interp((s - 1.0) % rb.L)[:2]
                xb, zb = rb._interp((s + 1.0) % rb.L)[:2]
                tx, tz = xb - xa, zb - za
                L = math.hypot(tx, tz) or 1.0
                k = int(round(vf)) % len(rb.raw)
                inset = cw_ei[k] or EDGE_INSET_M
                half = w / 2.0
                outer = half - inset - KERB_CLEAR_M if mode == "road" else half - 0.05
                d = min(q, n_st - 1 - q)
                h = max(0.005, KERB_H * min(1.0, (d + 0.5) / KERB_TAPER_STATIONS))
                sts.append({"s": s, "k": k, "cx": x, "cz": z, "y_hint": y + LIFT, "tx": tx / L, "tz": tz / L,
                            "lip": sgn * (outer - KERB_W), "h": h, "arc": q * KERB_STEP_M})
            sts, skipped, kcorners = trim_folded_stations(sts, sgn)
            plans.append({"kind": "kerb", "apex": kb["apex_vertex"], "side": kb["side"], "sub": kb["kind"],
                          "run": [kb["i"], kb["j"]], "stations": sts, "length_m": round(length, 1),
                          "fold_skipped": skipped, "fold_corners": kcorners})
    return plans


def _seg_cross(p1, p2, p3, p4):
    """(t, s) where the line p1 + t (p2 - p1) meets the line p3 + s (p4 - p3); None if parallel"""
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    s = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    return t, s


def _unit2(dx, dz):
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L


def _mitre(din, dout):
    """(bisector tangent, cos(psi / 2), signed turn psi) of a corner from leg direction din to dout"""
    tx, tz = _unit2(din[0] + dout[0], din[1] + dout[1])
    cos_half = max(1e-6, tx * din[0] + tz * din[1])
    psi = math.atan2(din[0] * dout[1] - din[1] * dout[0], din[0] * dout[0] + din[1] * dout[1])
    return (tx, tz), cos_half, psi


def corner_ring(a, nxt, X, din, dout, t):
    """the mitred strip ring AT a trimmed fold's corner X: profile on the bisector of the two leg directions,
    lateral scale 1/cos(psi/2) (capped at MITRE_MAX) so each face of the strip meets its partner on the other
    leg as a mitre — the curb-side face lands in the curb's own corner, the road-side face is the corner the
    driver sees. Deck hint / lateral / height lerped a -> nxt at t (X's fraction along a's segment); u None so
    densify_rings treats both corner spans as straight chords. Returns (ring, |psi|)."""
    (tx, tz), cos_half, psi = _mitre(din, dout)
    r = {key: val for key, val in a.items() if key != "y"}
    for key in ("y_hint", "lat", "h"):
        r[key] = a[key] + (nxt[key] - a[key]) * t
    r["tx"], r["tz"] = tx, tz
    lx, lz = left_normal(tx, tz)
    r["cx"], r["cz"] = X[0] - lx * r["lat"], X[1] - lz * r["lat"]     # so that _strip_xz(r) == X
    r["ls"] = min(MITRE_MAX, a["ls"] / cos_half)
    r["u"] = None
    r["inserted"] = r["corner"] = True
    r["corner_turn_deg"] = round(math.degrees(psi), 1)
    return r, abs(psi)


def corner_station(a, nxt, X, din, dout, t, sgn):
    """the kerb form of corner_ring: the station's mid-line (lip + sgn KERB_W / 2) at X, profile on the
    bisector, `ls` = the mitre scale kerb_mesh stretches the profile by about that mid-line"""
    (tx, tz), cos_half, psi = _mitre(din, dout)
    r = {key: val for key, val in a.items() if key != "y"}
    for key in ("y_hint", "lip", "h"):
        r[key] = a[key] + (nxt[key] - a[key]) * t
    r["tx"], r["tz"] = tx, tz
    lx, lz = left_normal(tx, tz)
    mid = r["lip"] + sgn * KERB_W / 2.0
    r["cx"], r["cz"] = X[0] - lx * mid, X[1] - lz * mid
    r["ls"] = min(MITRE_MAX, 1.0 / cos_half)
    r["corner"] = True
    r["corner_turn_deg"] = round(math.degrees(psi), 1)
    return r, abs(psi)


def _trim_folds(recs, pos, place, half, search, what):
    """Offset-curve LOOP REMOVAL on the polyline pos(recs) of ONE run (strip rings or kerb stations) —
    ledger 0047, 2026-10-11; replaces the one-sided drop (drop_folded_rings / drop_folded_stations), whose
    test kept the 'ear' rings v768 / v1512 / v2317 / v3295 and chorded BACKWARDS across the fold: six
    inside-out strip spans on the R side, seven on the inside kerbs, and a hook of wall standing 1-3.5 m
    inside the exit carriageway at College/Navajo, Navajo/Jackson and Jackson/Lake Murray.

    Where an inside lip is tighter than the offset (|lat| > R: the hairpin v770, College/Navajo v1514,
    Navajo/Jackson v2319, Jackson/Lake Murray v3297, the seam v0) the offset curve runs forward through a
    self-intersection X to a cusp, BACKWARDS to a second cusp, and forward through X again (a swallowtail);
    the ROAD ribbon's own inside edge folds the same way. The pavement's real inside boundary — the curb —
    is the TRIMMED curve: the in-leg up to X, then the out-leg, a sharp corner. So the furniture does the same:
      1. a backward step: record i behind record i-1 along EITHER record's tangent (the two-sided test);
         backward steps within FOLD_MERGE_M of each other (along the run) are one fold;
      2. each cluster of backward steps is cut between the in-leg segment (a, a+1) and the out-leg segment
         (b, b+1) that CROSS, the pair removing the fewest records (kind 'loop'); where the legs never cross
         — the lip flares while it folds (v3297) or the width steps (the seam v0: a Z-fold) — the last
         in-leg step and the first out-leg step that are not curling into a cusp (polyline step >=
         FOLD_STRETCH_MIN x the centreline step) are extended to meet, each <= FOLD_EXTEND_MAX_M (kind 'extend');
      3. ONE mitred corner record (`place`) stands AT X; a leg record nearer X than the reflex mitre tip
         (half x tan(psi / 2) + MITRE_CLEAR_M along its leg) is dropped too, so no span turns inside-out;
      4. arcs after X are rebased so the texture (u = arc / pitch) stays continuous along the trimmed run.
    No trim found (no crossing, no extension within reach) or a leg too short to clear the mitre is a
    SystemExit: that corner is authored by hand. Returns (records, n_dropped, corners); a corner record is
    what tools/barrier_bands.py declares as `edge_corners` (edge_fold_corners)."""
    n = len(recs)
    if n < 3:
        return recs, 0, []
    P = [pos(r) for r in recs]

    def backward(i):
        dx, dz = P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]
        return (dx * recs[i - 1]["tx"] + dz * recs[i - 1]["tz"] < 0.0) or (dx * recs[i]["tx"] + dz * recs[i]["tz"] < 0.0)

    def leg_ok(i):          # the step i -> i+1 is a real leg, not the curl into a cusp
        cs = math.hypot(recs[i + 1]["cx"] - recs[i]["cx"], recs[i + 1]["cz"] - recs[i]["cz"]) or 1e-9
        ss = math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1])
        return ss / cs >= FOLD_STRETCH_MIN and not backward(i + 1)

    clusters = []
    for i in range(1, n):
        if backward(i):
            if clusters and recs[i]["arc"] - recs[clusters[-1][1]]["arc"] <= FOLD_MERGE_M:
                clusters[-1][1] = i
            else:
                clusters.append([i, i])
    cuts = []
    for f0, f1 in clusters:
        best = None
        for a in range(f0 - 1, max(-1, f0 - 1 - search), -1):         # in-leg segment (a, a+1), a < f0
            for b in range(f1, min(n - 1, f1 + search)):               # out-leg segment (b, b+1), b >= f1
                r = _seg_cross(P[a], P[a + 1], P[b], P[b + 1])
                if r and 0.0 <= r[0] <= 1.0 and 0.0 <= r[1] <= 1.0 and (best is None or b - a < best[1] - best[0]):
                    X = (P[a][0] + r[0] * (P[a + 1][0] - P[a][0]), P[a][1] + r[0] * (P[a + 1][1] - P[a][1]))
                    best = (a, b, X, _unit2(P[a + 1][0] - P[a][0], P[a + 1][1] - P[a][1]),
                            _unit2(P[b + 1][0] - P[b][0], P[b + 1][1] - P[b][1]), r[0], "loop", 0.0)
        if best is None:
            for a in range(f0 - 1, max(0, f0 - 1 - search), -1):      # in-leg step (a-1, a)
                if not leg_ok(a - 1):
                    continue
                for b in range(f1, min(n - 1, f1 + search)):          # out-leg step (b, b+1)
                    if not leg_ok(b):
                        continue
                    din = _unit2(P[a][0] - P[a - 1][0], P[a][1] - P[a - 1][1])
                    dout = _unit2(P[b + 1][0] - P[b][0], P[b + 1][1] - P[b][1])
                    r = _seg_cross(P[a], (P[a][0] + din[0], P[a][1] + din[1]), (P[b][0] - dout[0], P[b][1] - dout[1]), P[b])
                    if not r or not (0.0 <= r[0] <= FOLD_EXTEND_MAX_M and 0.0 <= 1.0 - r[1] <= FOLD_EXTEND_MAX_M):
                        continue
                    ext = r[0] + 1.0 - r[1]
                    if best is None or (b - a, ext) < (best[1] + 1 - best[0], best[7]):
                        X = (P[a][0] + din[0] * r[0], P[a][1] + din[1] * r[0])
                        best = (a, b - 1, X, din, dout, 0.0, "extend", ext)
        if best is None:
            raise SystemExit(f"[race] {what} fold at v{recs[f0]['k']}..v{recs[f1]['k']}: no trim (no crossing, no "
                             f"extension within {FOLD_EXTEND_MAX_M} m) — author this corner by hand")
        if cuts and best[0] < cuts[-1][1] + 1:
            raise SystemExit(f"[race] {what} folds at v{recs[cuts[-1][0]]['k']} and v{recs[f0]['k']} overlap — "
                             f"author this corner by hand")
        cuts.append(best)
    out, dropped, corners = [], 0, []
    i = ci = 0
    shift = 0.0
    while i < n:
        if ci < len(cuts) and i == cuts[ci][0] + 1:
            a, b, X, din, dout, t, kind, ext = cuts[ci]
            cr, psi = place(recs[a], recs[a + 1], X, din, dout, t)
            reach = half * math.tan(min(psi, math.radians(150.0)) / 2.0) + MITRE_CLEAR_M
            removed = []
            while len(out) > 1:
                q = pos(out[-1])
                if (X[0] - q[0]) * din[0] + (X[1] - q[1]) * din[1] >= reach:
                    break
                removed.append(out.pop()["k"])
            q = pos(out[-1])
            if (X[0] - q[0]) * din[0] + (X[1] - q[1]) * din[1] < reach:
                raise SystemExit(f"[race] {what} fold corner at ({X[0]:.2f}, {X[1]:.2f}): the in-leg is shorter than the "
                                 f"mitre ({reach:.2f} m) — author this corner by hand")
            cr["arc"] = out[-1]["arc"] + math.hypot(X[0] - q[0], X[1] - q[1])
            cr["k"], cr["s"] = out[-1]["k"], out[-1]["s"]     # the corner belongs to the last kept leg record's vertex
            out.append(cr)
            j = b + 1
            while j < n - 1:
                q = pos(recs[j])
                if (q[0] - X[0]) * dout[0] + (q[1] - X[1]) * dout[1] >= reach:
                    break
                j += 1
            q = pos(recs[j])
            if (q[0] - X[0]) * dout[0] + (q[1] - X[1]) * dout[1] < reach:
                raise SystemExit(f"[race] {what} fold corner at ({X[0]:.2f}, {X[1]:.2f}): the out-leg is shorter than the "
                                 f"mitre ({reach:.2f} m) — author this corner by hand")
            removed += [recs[q_]["k"] for q_ in range(a + 1, j)]
            dropped += len(removed)
            shift = cr["arc"] + math.hypot(q[0] - X[0], q[1] - X[1]) - recs[j]["arc"]
            corners.append({"kind": kind, "xz": [round(X[0], 3), round(X[1], 3)], "turn_deg": cr["corner_turn_deg"],
                            "mitre": round(cr["ls"], 3), "in_vertex": out[-2]["k"], "out_vertex": recs[j]["k"],
                            "removed": sorted(set(removed)), "n_removed": len(removed),
                            "extension_m": round(ext, 2)})
            i = j
            ci += 1
            continue
        out.append(dict(recs[i], arc=recs[i]["arc"] + shift) if shift else recs[i])
        i += 1
    return out, dropped, corners


def trim_folded_rings(rings, search=FOLD_SEARCH_RINGS):
    """_trim_folds on a kerb-line strip's vertex rings (the strip centre polyline, a mitred corner_ring at
    each corner). The chain (lat 0) never folds. Returns (rings, n_dropped, corners)."""
    return _trim_folds(rings, _strip_xz, corner_ring, BARRIER_HALF_W, search, "edge")


def trim_folded_stations(sts, sgn, search=FOLD_SEARCH_STATIONS):
    """_trim_folds on a race kerb's 0.3 m stations (the kerb's mid-line, a mitred corner_station at each
    corner): the inside kerbs at the hairpin and the seam fold exactly like the strip they run beside.
    Returns (stations, n_dropped, corners)."""
    def place(a, nxt, X, din, dout, t):
        return corner_station(a, nxt, X, din, dout, t, sgn)
    return _trim_folds(sts, lambda s: kerb_mid_xz(s, sgn), place, KERB_W / 2.0, search, "kerb")


def kerb_mid_xz(s, sgn):
    """the kerb's mid-line point of a station (lip + sgn KERB_W / 2) — the polyline the trim works on"""
    lx, lz = left_normal(s["tx"], s["tz"])
    mid = s["lip"] + sgn * KERB_W / 2.0
    return s["cx"] + lx * mid, s["cz"] + lz * mid


def inside_out_spans(recs, pos, half):
    """[(span index, column offset)] of the spans between consecutive records (strip rings or kerb stations)
    where a profile column moves BACKWARD along the span's mean tangent — the swept solid / kerb sheet there
    is inside-out. Columns at the profile's two extreme offsets +-half x ls about pos(rec) along its left
    normal (the test is affine in the offset, so the extremes bound every column). [] = no inverted span."""
    bad = []
    for i in range(len(recs) - 1):
        a, b = recs[i], recs[i + 1]
        tm = (a["tx"] + b["tx"], a["tz"] + b["tz"])
        pa, pb = pos(a), pos(b)
        la, lb = left_normal(a["tx"], a["tz"]), left_normal(b["tx"], b["tz"])
        sa, sb = half * a.get("ls", 1.0), half * b.get("ls", 1.0)
        for o in (-1.0, 1.0):
            dx = (pb[0] + lb[0] * o * sb) - (pa[0] + la[0] * o * sa)
            dz = (pb[1] + lb[1] * o * sb) - (pa[1] + la[1] * o * sa)
            if dx * tm[0] + dz * tm[1] <= 0.0:
                bad.append((i, o))
                break
    return bad


def match_declared_corners(bands, found, tol=0.05):
    """The declaration wins (the median_zone precedent): when data/barrier_bands.json carries `edge_corners`
    (tools/barrier_bands.py — edge_fold_corners, the same computation) every corner the sweep trims must be a
    declared one (same side, same removed vertices, X within tol) and every declared corner must be trimmed;
    else SystemExit (re-run the band writer: the declaration IS the authored line). A bands file written
    before 2026-10-11 has no key: nothing to match here — verify_race D then fails every vertex the trim
    leaves without a ring, because nothing declares it."""
    if "edge_corners" not in bands:
        return
    declared = list(bands.get("edge_corners") or [])

    def same(c, d):
        return (str(c.get("side")) == str(d.get("side")) and sorted(c["removed"]) == sorted(d["removed"])
                and math.dist(c["xz"], d["xz"]) <= tol)
    extra = [c for c in found if not any(same(c, d) for d in declared)]
    unbuilt = [d for d in declared if not any(same(c, d) for c in found)]
    if extra or unbuilt:
        raise SystemExit(f"[race] the trimmed edge corners differ from barrier_bands.json edge_corners: "
                         f"{len(extra)} trimmed but not declared {[(c['side'], c['in_vertex'], c['out_vertex']) for c in extra]}, "
                         f"{len(unbuilt)} declared but not trimmed {[(d['side'], d['in_vertex'], d['out_vertex']) for d in unbuilt]} "
                         f"— re-run tools/barrier_bands.py")


def edge_fold_corners(pts, widths, edge_inset, mode="road", height=BARRIER_H):
    """the kerb-line strips' trimmed inside corners on both sides — what tools/barrier_bands.py declares as
    `edge_corners`: the SAME _plan_run + trim_folded_rings that edge_plans authors, so the declaration IS the
    authored line. Each record: side, kind (loop | extend), xz (the corner X, engine frame), turn_deg, mitre,
    in_vertex / out_vertex (the leg rings either side), removed (the vertices with no ring on that side: the
    declared band runs in_vertex -> xz -> out_vertex across them), n_removed, extension_m."""
    m = unique_count(pts)
    st = stations(pts)
    out = []
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        for i, j in intervals(edge_inset, m):
            run = _plan_run(pts, widths, m, st, walk(i, j, m),
                            lambda k, s=sgn: s * edge_lateral(widths[k] / 2.0, edge_inset[k] or EDGE_INSET_M, mode),
                            "free", "free", height, "edge", "", side, (i, j))
            out += [dict(c, side=side) for c in trim_folded_rings(run["rings"])[2]]
    return out


# ---------------------------------------------------------------------------------------------
# names
def object_name(plan):
    if plan["kind"] == "chain":
        return f"1WALL_race_kbar_{plan['street']}_{plan['run'][0]}_{plan['part']}"
    if plan["kind"] == "edge":
        return f"1WALL_race_edge_{plan['side']}_{plan['street']}_{plan['run'][0]}_{plan['part']}"
    if plan["kind"] == "kerb":
        return f"1KERB_race_{plan['apex']}_{plan['sub']}"
    if plan["kind"] == "collider":
        return f"1WALL_racecol_{plan['part']}"
    raise ValueError(plan["kind"])


# ---------------------------------------------------------------------------------------------
# spawn clearance (grid / pit exclusions): nothing of a layout's grid or pit row may stand in a strip
def nearest_vertex(pts, m, x, z, cells=None):
    best, bi = float("inf"), 0
    for k in range(m):
        d = (pts[k][0] - x) ** 2 + (pts[k][2] - z) ** 2
        if d < best:
            best, bi = d, k
    return bi


def spawn_clearance_table(pts, widths, bands, dummies, mode="road"):
    """One record per FACING dummy (grid / pit / hotlap; AC_TIME_* skipped): the nearest vertex, the
    signed lateral (+ = left of the FORWARD centreline), the edge-strip face it faces, and the car's
    clearance to that face and (where a chain stands) to the centre chain. Pure; verify_race and the
    author tool both read it."""
    m = unique_count(pts)
    cw, ei = bands["centre_w_by_vertex"], bands["edge_inset_by_vertex"]
    out = []
    for name, p in dummies.items():
        if name.startswith("_") or not any(name.startswith(f) for f in FACING):
            continue
        x, y, z = p
        k = nearest_vertex(pts, m, x, z)
        tx, tz = tangent(pts, k, m)
        lx, lz = left_normal(tx, tz)
        lat = (x - pts[k][0]) * lx + (z - pts[k][2]) * lz
        half = widths[k] / 2.0
        face = (half - (ei[k] or EDGE_INSET_M)) if mode == "road" else half + 0.11
        rec = {"name": name, "vertex": k, "lat_m": round(lat, 3), "edge_face_m": round(face, 3),
               "clear_edge_m": round(face - (abs(lat) + CAR_HALF_W), 3), "clear_centre_m": None}
        if cw[k] > 0:
            rec["clear_centre_m"] = round(abs(lat) - CAR_HALF_W - cw[k] / 2.0, 3)
        out.append(rec)
    return out


def spawn_clearance(pts, widths, bands, dummies, mode="road"):
    """(hard, notes): hard = a car on this spawn overlaps a strip OR stands closer than SPAWN_MARGIN_M
    (0.30 m) to a strip face — never ship (HARD since 2026-10-11; a 0.08 m clearance used to be a note);
    notes = the minimum clearance found, one line (reported, never gated)"""
    hard, notes = [], []
    worst = None
    for r in spawn_clearance_table(pts, widths, bands, dummies, mode):
        name, k, lat, face = r["name"], r["vertex"], r["lat_m"], r["edge_face_m"]
        clear = r["clear_edge_m"]
        if clear < 0:
            hard.append(f"{name} at v{k} lat {lat:+.2f}: car edge {abs(lat) + CAR_HALF_W:.2f} m overlaps the edge-strip face {face:.2f} m")
        elif clear < SPAWN_MARGIN_M:
            hard.append(f"{name} at v{k} lat {lat:+.2f}: only {clear:.2f} m clear of the edge-strip face ({face:.2f} m) "
                        f"< {SPAWN_MARGIN_M:.2f} m")
        if worst is None or clear < worst[0]:
            worst = (clear, f"{name} v{k} (edge-strip face {face:.2f} m)")
        cc = r["clear_centre_m"]
        if cc is not None:
            if cc < 0:
                hard.append(f"{name} at v{k} lat {lat:+.2f}: overlaps the centre chain")
            elif cc < SPAWN_MARGIN_M:
                hard.append(f"{name} at v{k} lat {lat:+.2f}: only {cc:.2f} m clear of the centre chain < {SPAWN_MARGIN_M:.2f} m")
            if cc < worst[0]:
                worst = (cc, f"{name} v{k} (centre chain)")
    if worst is not None:
        notes.append(f"minimum spawn clearance {worst[0]:.2f} m at {worst[1]} (hard floor {SPAWN_MARGIN_M:.2f} m)")
    return hard, notes


# ---------------------------------------------------------------------------------------------
# dry-run dummies (the spec's grids) — tools/layout_dummies.py is the real producer (another agent)
def synth_dummies(pts, widths, layout, n_pits=8):
    """FULL dummy set for one layout in the engine frame + the underscore keys the spec names.
    Grid: pole at grid_vertex, +offset right of THIS layout's travel; AC_START_g at pole - 5.5 g m in
    two staggered columns (lane centre +- layout_dummies.GRID_STAGGER_M); pits single file at the lane centre 45 + 7 (p+1) m
    behind; AC_TIME_0 at line_vertex across the full width; sectors at sector_vertices."""
    from layout_dummies import GRID_STAGGER_M as stagger   # the producer's constant, never restated
    m = unique_count(pts)
    st = stations(pts)
    rev = layout.get("direction") == "reverse"
    sgn = -1.0 if rev else 1.0           # vertex index step along travel
    s = layout["start"]
    out, yaw, vtx, rot = {}, {}, {}, {}

    def at(k, right_m, lift=LIFT + 0.30):
        k %= m
        tx, tz = tangent(pts, k, m)
        if rev:
            tx, tz = -tx, -tz
        rx, rz = tz, -tx                 # right of travel
        p = pts[k]
        return [round(p[0] + rx * right_m, 3), round(p[1] + lift, 3), round(p[2] + rz * right_m, 3)], (tx, tz)

    def behind_vertex(k0, metres):
        """the vertex `metres` behind k0 in the direction of travel"""
        target = st[k0] - sgn * metres
        best, bk = float("inf"), k0
        for k in range(m):
            d = abs(st[k] - target)
            if d < best:
                best, bk = d, k
        return bk

    def facing(name, k, right_m):
        p, (tx, tz) = at(k, right_m)
        out[name] = p
        yaw[name] = round(math.degrees(math.atan2(tx, -tz)), 3)
        vtx[name] = k % m
        rot[name] = right_m

    off = float(s["offset_right_m"])
    g0 = int(s["grid_vertex"])
    facing("AC_START_0", g0, off)
    facing("AC_HOTLAP_START_0", g0, off)
    for g in range(1, n_pits):
        k = behind_vertex(g0, 5.5 * g)
        facing(f"AC_START_{g}", k, off + (stagger if g % 2 else -stagger))
    for p in range(n_pits):
        k = behind_vertex(g0, 45.0 + 7.0 * (p + 1))
        facing(f"AC_PIT_{p}", k, off)
    line = int(s["line_vertex"])
    gates = [line] + [int(v) for v in s.get("sector_vertices", [])]
    for gi, k in enumerate(gates):
        half = widths[k % m] / 2.0 - 0.3
        pl, _ = at(k, -half, LIFT)       # left of travel
        pr, _ = at(k, +half, LIFT)
        out[f"AC_TIME_{gi}_L"] = pl
        out[f"AC_TIME_{gi}_R"] = pr
        vtx[f"AC_TIME_{gi}_L"] = vtx[f"AC_TIME_{gi}_R"] = k % m
    out["_layout"] = layout["id"]
    out["_direction"] = layout.get("direction", "forward")
    out["_synthesised"] = True
    out["_doc"] = ("SYNTHESISED for a dry run by tools/race_furniture.synth_dummies from layouts[].start — "
                   "tools/layout_dummies.py is the producer of record; underscore keys are not dummies")
    out["_yaw_deg"] = yaw
    out["_vertex"] = vtx
    out["_right_of_travel_m"] = rot
    return out


def dummies_positions(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------------------------
def plan_all(proj, bands, mode="road", height=BARRIER_H, kerbs=True):
    """everything the Blender tool needs, plus the corner table for the report"""
    pts, widths = load_centerline(proj)
    mb = json.loads((Path(proj) / "data" / "median_bands.json").read_text(encoding="utf-8"))
    island_w = mb["island_w_by_vertex"]
    if len(island_w) != len(pts):
        raise SystemExit(f"[race] median_bands {len(island_w)} vs centerline {len(pts)} vertices")
    plans = chain_plans(pts, widths, island_w, bands, height) + edge_plans(pts, widths, bands, mode, height)
    corners = []
    if kerbs:
        rb, corners = detect_kerb_corners(pts, widths, bands)
        for d in apply_declared_kerbs(rb, corners, bands):
            print(f"[race] WARNING declared kerb apex v{d.get('apex')} {d.get('side')} {d.get('kind')} "
                  f"matches no detected corner — not authored")
        plans += kerb_plans(rb, corners, bands, mode)
    return pts, widths, island_w, plans, corners


if __name__ == "__main__":
    # CLI: write a stand-in bands file / synthesised dummies into a (scratch) project and print the plan
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--standin-bands", action="store_true", help="write data/barrier_bands.json (stand-in) if absent")
    ap.add_argument("--synth-dummies", action="store_true", help="write data/dummies_<id>.json (synthesised) if absent")
    ap.add_argument("--edge-mode", default=None, choices=["road", "walk"])
    a = ap.parse_args()
    proj = Path(a.project)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    race_cfg = cfg.get("race", {}) or {}
    pts, widths = load_centerline(proj)
    mode = a.edge_mode or race_cfg.get("edge_mode", "road")
    bands = load_bands(proj)
    if bands is None and a.standin_bands:
        mb = json.loads((proj / "data" / "median_bands.json").read_text(encoding="utf-8"))
        mouths = json.loads((proj / "data" / "mouths.json").read_text(encoding="utf-8")).get("mouths", [])
        spans = json.loads((proj / "data" / "bridge.spans.auto.json").read_text(encoding="utf-8"))
        tmp = standin_bands(pts, widths, mb["island_w_by_vertex"], mouths, spans, dict(race_cfg, edge_mode=mode))
        _, corners = detect_kerb_corners(pts, widths, tmp)
        bands = standin_bands(pts, widths, mb["island_w_by_vertex"], mouths, spans, dict(race_cfg, edge_mode=mode), corners)
        (proj / "data" / "barrier_bands.json").write_text(json.dumps(bands), encoding="utf-8")
        print(f"[race] wrote STAND-IN data/barrier_bands.json: chain {bands['params']['chain_length_m']} m, "
              f"{len(bands['runs'])} runs, {len(bands['closed_mouths'])} closed mouths, {len(bands['kerbs'])} kerbs")
    if a.synth_dummies:
        for lo in cfg.get("layouts", []):
            p = proj / "data" / f"dummies_{lo['id']}.json"
            if p.exists() or not lo.get("start"):
                continue
            p.write_text(json.dumps(synth_dummies(pts, widths, lo), indent=1), encoding="utf-8")
            print(f"[race] wrote SYNTHESISED {p.name} ({lo.get('direction', 'forward')})")
    if bands is not None:
        mb = json.loads((proj / "data" / "median_bands.json").read_text(encoding="utf-8"))
        for pr in check_bands(bands, pts, mb["island_w_by_vertex"]):
            print(f"[race] bands: {pr}")
        _, _, _, plans, corners = plan_all(proj, bands, mode)
        for c in corners:
            print(f"[race] corner apex v{c['apex_vertex']} R {c['R_apex_m']} m D {c['D_deg']} deg "
                  f"{'chained' if c['chained'] else 'open'} -> {[k['side'] + '/' + k['kind'] for k in c['kerbs']]}")
        print(f"[race] {len(plans)} objects planned: "
              f"{sum(1 for p in plans if p['kind'] == 'chain')} chain, {sum(1 for p in plans if p['kind'] == 'edge')} edge, "
              f"{sum(1 for p in plans if p['kind'] == 'kerb')} kerb")

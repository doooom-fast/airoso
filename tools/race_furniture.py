"""Race-layout furniture for the Lake Murray loop — the PURE geometry (no bpy), ledgers 0047 + 0049.

Ledger 0049 (Kevin 2026-10-11, the race-corridor spec): "racetrack versions of these, we need full
intersections available for turning. And the entire other lane blocked off from access" — an
Alvarado-wide lane per direction. Three kinds of furniture, every one a swept strip authored in the
ENGINE frame (x = E, y = up, z = N) and emitted into Blender by `tools/author_race_furniture_blend.py`
with the (x, z, y) remap and REVERSED winding (LAWS L6: the remap is a reflection):

  kerb-line barriers    `1WALL_race_edge_<L|R>_<street>_<k>_<part>`   COMMON (both race layouts): Kevin's
                                                        concrete_barrier_4m.obj silhouette swept on BOTH curb
                                                        faces as ONE CLOSED LOOP per side — bridges included
                                                        (C1: edge_gaps none), straight across every mouth, cut
                                                        at street boundaries on shared rings: no free end, no cap
  closures              `1WALL_race_close_<token>_<street>_<k>_<part>`  PER DIRECTION: the same strip on
                                                        barrier_bands.json `corridors.<layout>.closure_y_by_vertex`
                                                        (the far boundary 11.36 m from the race-side strip,
                                                        along the island's race-side curb nose tip to nose tip),
                                                        both ends PINNED full height on the far curb strip at a
                                                        box / whole-street edge (the end cap buried in it)
  race kerbs            `1KERB_race_<apexvertex>_<in|out>`  COMMON: a 1.0 m x 0.05 m flat rumble strip ON the
                                                        pavement inboard of the edge strip at the five corners
                                                        the sign detector finds (|D| >= 45 deg), in AND out,
                                                        clipped where either direction's closure stands on it;
                                                        a kerb the declaration drops or pulls back
                                                        (race.kerbs.trims: off a ribbon fold) follows it

A layout that names a LAP (layouts[].lap, ledger 0054 — scripts/geometry/race_lap.py) has its own common set on its
own line: `1WALL_race_edge_lap<lap>_<L|R>_...` and `1KERB_race_lap<lap>_<apex>_<in|out>` in the collection
RACE_LAP_<LAP>, routed to <slug>_race_<lap>.kn5 (race_lap here reads the token back). The mainline's names are
unchanged: a mainline strip's first field is its side (L / R), a kerb's its apex vertex — never "lap...".

The retired ledger-0047 centre chain (`1WALL_race_kbar_*`, `centre_w_by_vertex`, `centre_runs`) is refused:
a declaration that still carries it is a v1 file (check_bands). The owner token rides in a closure's NAME
(race_owner) because the prep re-links objects to the scene root — the export split, check_race_kn5 and
verify_kn5 route on it: common -> <slug>_race.kn5, token t -> <slug>_closure_<layout>.kn5.

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
import re
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
NOSE_HALF = 0.25         # tools/author_median_blend.py NOSE_HALF — the authored island nose half-width (MEASURED)
NOSE_VERTS = 3           # ... tapered over this many vertices at each island end (author_median_blend NOSE_VERTS)
FREE_END_H = 0.30        # a FREE end (only a gapped, pre-0049 declaration has one — verify_race J fails it):
FREE_TAPER_RINGS = 3     #   3-ring height taper 1.20 -> 0.30. Joins and closure pins stay full height.
# ledger 0049 names: the kind / owner rides in the name (upper-case prefix tests)
EDGE_TAG = "1WALL_RACE_EDGE_"
CLOSE_TAG = "1WALL_RACE_CLOSE_"   # + <token>_ : the per-direction closure, routed to <slug>_closure_<layout>.kn5
KBAR_TAG = "1WALL_RACE_KBAR_"     # the RETIRED centre chain (ledger 0047): its presence anywhere FAILS
KERB_TAG = "1KERB_RACE_"
TOKEN_RE = re.compile(r"^[a-z0-9]+$")   # a closure owner token ("cw" / "acw"): no underscore, it ends the name field
COMMON_COLLECTION = "RACE"        # the common furniture's Blender collection; closures: RACE_CLOSE_<TOKEN>
LAP_FIELD = "lap"                 # ledger 0054: a lap's common furniture names carry lap<token> as their first field
KERB_CLOSURE_CLEAR_M = 0.05       # a race kerb's footprint stands >= this off EVERY race layout's closure footprint
#                                   (INVENTED, spec 0049 §6: the clip rule) — else the kerb is cut back
LOOP_START_WINDOW = 10            # a closed curb-strip loop starts at the straightest vertex of the lap (least
#                                   heading change over +-this many vertices): a fold never straddles its two ends
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
KERB_TILE_M = 1.0        # kerb_diffuse.png stripes: one tile per metre along (the wear=None path, unchanged)
# ledger 0053 — the worn race-kerb ATLAS (tools/make_kerb_texture.py paints it, kerb_atlas_face_uvs wraps it).
# kerb_race_worn_{diffuse,normal}.jpg: KERB_ATLAS_COLUMNS columns of KERB_ATLAS_COL_PX px = tyre-rubber level
# 0..3 (identical paint, chips and joints; level c's rubber a superset of level c-1's), each padded
# KERB_ATLAS_PAD_PX px per side against mip bleed; along v KERB_ATLAS_V_M metres of kerb at KERB_ATLAS_PX_M px/m,
# KERB_BLOCK_M red / white blocks with a grime joint at every block end. All [invented] (GATES-CHANGELOG 0053).
KERB_ATLAS_COLUMNS = 4
KERB_ATLAS_COL_PX = 256
KERB_ATLAS_PAD_PX = 8
KERB_ATLAS_V_M = 8.0
KERB_ATLAS_PX_M = 256
KERB_BLOCK_M = 1.0
# the 5 cm OUTER face (the kerb's back, facing away from the lane) always wraps column 0: no column carries rubber
# past 60 % of the profile (the outer face is 95..100 %), so the pixels are the same in every column, and the face's
# two row vertices never split at a column seam — a seam costs 4 render vertices (lip, ramp top x 2, top's outer
# edge), not 6, which keeps Lake Murray's kerbs inside the diagnosis's pre-registered KERB <= 7,300 render vertices
# (ledger 0053 V2; tests/tools/test_kerb_wear.py).
KERB_OUTER_FACE_COLUMN = 0
KERB_SEAM_RENDER_VERTS = 4
# wear placement (kerb_wear): both race directions drive every kerb (barrier_bands: whole/box at every kerb vertex)
KERB_WEAR_IN_LATE = 0.6          # inside kerb: each direction's late apex at PC + 0.6 arc (increasing) / PT - 0.6 arc
KERB_WEAR_IN_SIGMA_MIN_M = 5.0   # ... lobe sigma max(5 m, 0.15 arc)
KERB_WEAR_IN_SIGMA_FRAC = 0.15
KERB_WEAR_IN_FLOOR = 0.15        # ... everywhere else on an inside kerb: light wear
KERB_WEAR_OUT_D_FRAC = 0.2       # outside kerb: each direction's track-out at PT + 0.2 E (increasing) / PC - 0.2 E
KERB_WEAR_OUT_SIGMA_M = 6.0
KERB_WEAR_OUT_FLOOR = 0.10
KERB_JOINT_SNAP_MAX_M = 0.25     # a whole metre becomes a joint station only if a station lies within this of it
KERB_TAPER_STATIONS = 3
KERB_DEFL_MIN_DEG = 45.0
KERB_EXT_MIN_M, KERB_EXT_MAX_M = 10.0, 30.0   # outside kerb symmetric extension E = clamp(2 R_apex, 10, 30)
CAR_HALF_W = 0.95        # spawn clearance: a 1.9 m car
SPAWN_MARGIN_M = 0.30    # HARD floor (2026-10-11; was a soft note): a car on a grid/pit slot stands >= this off any
#                          strip face — 0.08 m (the 1.4 m stagger) left no room for a spawn wobble or a wider car
COLLIDER_BELOW_M, COLLIDER_ABOVE_M = 0.30, 2.50   # optional invisible sheet (Q11, OFF by default)
STREETS = (("alvarado", 0, 759), ("college", 760, 1514), ("navajo", 1515, 2320),
           ("jackson", 2321, 3297), ("lakemurray", 3298, 4498))
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")


# ---------------------------------------------------------------------------------------------
# centreline helpers
def load_centerline(proj, lap=None):
    """the mainline (data/centerline.local.json), or with `lap` the stitched lap line data/lap.<lap>.json"""
    if lap:
        local = _race_lap().load(proj, lap)
    else:
        local = json.loads((Path(proj) / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in local["points_xyz_m"]]
    widths = [float(w) for w in local["widths_m"]]
    return pts, widths


def load_island_w(proj, lap=None):
    """median_bands island_w_by_vertex (mainline), or the lap file's island_w_by_vertex"""
    if lap:
        return [float(w) for w in _race_lap().load(proj, lap)["island_w_by_vertex"]]
    mb = json.loads((Path(proj) / "data" / "median_bands.json").read_text(encoding="utf-8"))
    return mb["island_w_by_vertex"]


_RACE_LAP = []


def _race_lap():
    """scripts/geometry/race_lap.py (pure), loaded by file once — this module also runs inside Blender"""
    if not _RACE_LAP:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_race_lap_rf", AIROSO / "scripts" / "geometry" / "race_lap.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _RACE_LAP.append(mod)
    return _RACE_LAP[0]


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


def race_role(name):
    """what a RACE object is, from its name alone: 'close' (a per-direction closure), 'edge' (a common curb
    strip), 'kerb' (a common race kerb), 'kbar' (the RETIRED ledger-0047 centre chain — a FAIL wherever it
    shows up), 'other' (another RACE-prefixed name); None for a non-race name"""
    u = str(name).upper()
    for tag, role in ((CLOSE_TAG, "close"), (EDGE_TAG, "edge"), (KERB_TAG, "kerb"), (KBAR_TAG, "kbar")):
        if u.startswith(tag):
            return role
    return "other" if u.startswith(RACE_PREFIXES) else None


def race_owner(name):
    """the owner token of a closure `1WALL_race_close_<token>_<street>_<k>_<part>` (lower case), else None — the
    common furniture (curb strips, kerbs) belongs to every race layout"""
    if not str(name).upper().startswith(CLOSE_TAG):
        return None
    tok = str(name)[len(CLOSE_TAG):].split("_", 1)[0].lower()
    return tok or None


def closure_collection(token):
    """the Blender collection a layout's closure objects are authored into (Kevin toggles a direction there)"""
    return f"{COMMON_COLLECTION}_CLOSE_{str(token).upper()}"


def lap_collection(lap):
    """the Blender collection a LAP's common furniture (its curb strips + kerbs) is authored into; None = RACE"""
    return COMMON_COLLECTION if not lap else f"{COMMON_COLLECTION}_LAP_{str(lap).upper()}"


def race_lap(name):
    """the lap token of a lap's common furniture (`1WALL_race_edge_lap<tok>_...`, `1KERB_race_lap<tok>_...`), else
    None — the mainline's strips start with their side (L / R), its kerbs with their apex vertex"""
    u = str(name).upper()
    for tag in (EDGE_TAG, KERB_TAG):
        if u.startswith(tag):
            field = str(name)[len(tag):].split("_", 1)[0]
            if field.lower().startswith(LAP_FIELD) and TOKEN_RE.match(field[len(LAP_FIELD):].lower() or "-"):
                return field[len(LAP_FIELD):].lower()
            return None
    return None


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
    closes back to the right base). Scaled proportionally for a free end's height taper."""
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
    """(lat_scale, height) of ring idx in a run of n rings. Only a 'free' end tapers (a gapped, pre-0049
    declaration); 'join' (a ring shared with the neighbouring object) and 'pin' (a closure end buried in the far
    curb strip, ledger 0049) stay full width and full height. The ledger-0047 nose taper is retired."""
    ls, h = 1.0, BARRIER_H
    for d, kind in ((idx, start_kind), (n - 1 - idx, end_kind)):
        if kind == "free" and d < FREE_TAPER_RINGS:
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


def render_vertex_count(n_verts, faces, sharp, face_uvs=None):
    """what the exporter emits for a smooth-shaded mesh with per-vertex UVs: one vertex per (position,
    smooth fan) — the faces round a vertex joined across its non-sharp manifold edges. (A flat-shaded
    triangulated mesh is 3 per triangle.) With `face_uvs` (per face, per corner — ledger 0053's kerb atlas) two
    faces are joined at a vertex only where they also carry the same UV there: a column seam splits the row."""
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
                    if face_uvs is not None and (face_uvs[fe[0]][faces[fe[0]].index(v)]
                                                 != face_uvs[fe[1]][faces[fe[1]].index(v)]):
                        continue
                    a, b = find(fe[0]), find(fe[1])
                    if a != b:
                        parent[a] = b
        total += len({find(fi) for fi in fs})
    return total


def triangle_count(faces):
    return sum(len(f) - 2 for f in faces)


# ---------------------------------------------------------------------------------------------
# ledger 0053: the worn race-kerb atlas — WHERE the tyre rubber goes and how the kerb is wrapped onto it (pure).
# Kevin 2026-10-12, from the seat: "i'd like the race curbs to be tire-worn/textured". The geometry is untouched:
# kerb_mesh is called exactly as before; only the per-face-corner UVs below are new.
#
# Handedness: a kn5 vertex carries a tangent but no bitangent sign, so AC assumes ONE wrap handedness. The prep's
# planar_uv (u = x, v = y in Blender, the road / grass / sidewalk wrap) is right-handed seen from above in the
# Blender frame; kerb_mesh's L and R kerbs were mirror images of each other. KERB_V_SIGN runs v along the kerb so
# BOTH sides match the planar wrap (tests pin it in the Blender frame) — the normal map's joints then read as
# grooves on every kerb, the way the asphalt's cracks already read.
KERB_V_SIGN = {"L": -1.0, "R": 1.0}


def kerb_profile_u():
    """u across the kerb profile by real surface length — lane lip 0 -> ramp top -> outer top -> outer base 1
    (ramp hypot(0.10, 0.05) + top 0.90 + outer face 0.05 = 1.062 m); kerb_mesh's 4 profile vertices"""
    seg = (math.hypot(KERB_RAMP_W, KERB_H), KERB_W - KERB_RAMP_W, KERB_H)
    tot = sum(seg)
    return (0.0, seg[0] / tot, (seg[0] + seg[1]) / tot, 1.0)


def kerb_atlas_u(level, u_prof):
    """atlas u of profile coordinate u_prof (0..1) in rubber column `level`, inside the column's pad"""
    width = KERB_ATLAS_COLUMNS * KERB_ATLAS_COL_PX
    inner = KERB_ATLAS_COL_PX - 2 * KERB_ATLAS_PAD_PX
    return (int(level) * KERB_ATLAS_COL_PX + KERB_ATLAS_PAD_PX + u_prof * inner) / width


def kerb_arcs(sts, sgn):
    """cumulative plan length (m) along the kerb's OWN mid-line from its first station: the real length the 1 m
    blocks are laid on (a station's `arc` is the centreline's — on the hairpin the inside kerb is far shorter)"""
    out = [0.0]
    for a, b in zip(sts, sts[1:]):
        out.append(out[-1] + math.dist(kerb_mid_xz(a, sgn), kerb_mid_xz(b, sgn)))
    return out


def _signed_gap(a, b, lap):
    """a - b along a closed lap of length `lap` (the shorter way round, L13); plain difference when lap is 0"""
    if not lap:
        return a - b
    d = (a - b) % lap
    return d - lap if d > lap / 2.0 else d


def kerb_wear_centres(plan, corner):
    """(lobe centres in ribbon metres, sigma m, floor) of a kerb's rubber — [invented], GATES-CHANGELOG 0053.
    Both race directions drive every kerb (race_cw increasing, race_acw decreasing): an INSIDE kerb is worn at each
    direction's late apex (PC + 0.6 arc, PT - 0.6 arc), an OUTSIDE kerb where each direction runs out wide on exit
    (PT + 0.2 E, PC - 0.2 E). The AI drafts cannot say where tyres run: they stay >= 1.04 m off every edge."""
    pc, pt = float(corner["PC"]), float(corner["PT"])
    lap = float(plan.get("lap_m") or 0.0)
    arc = (pt - pc) % lap if lap else pt - pc
    if plan["sub"] == "in":
        sig = max(KERB_WEAR_IN_SIGMA_MIN_M, KERB_WEAR_IN_SIGMA_FRAC * arc)
        return (pc + KERB_WEAR_IN_LATE * arc, pt - KERB_WEAR_IN_LATE * arc), sig, KERB_WEAR_IN_FLOOR
    d = KERB_WEAR_OUT_D_FRAC * float(corner["E_m"])
    return (pt + d, pc - d), KERB_WEAR_OUT_SIGMA_M, KERB_WEAR_OUT_FLOOR


def kerb_wear(plan, corner):
    """Per-span rubber level of one (seated or planned) kerb, and the v the atlas is wrapped with.

    raw level per station = min(3, int(4 w)), w = max(floor, Gaussian lobes at kerb_wear_centres). The column may
    only change AT a block joint: the station nearest each whole metre of the kerb's own mid-line length is a JOINT
    station, and v is warped piecewise-linearly so every joint station lands exactly on a whole metre (a block end in
    the atlas, inside its grime line) — blocks stay 1 m to within half a station spacing. Each block takes the
    highest raw level of its stations. Returns {levels: per span, v_m: per station, joints: [station idx],
    seams, m_by_level, heavy_spans_m_from_apex, arcs_m}."""
    sts = plan["stations"]
    sgn = 1.0 if plan["side"] == "L" else -1.0
    lap = float(plan.get("lap_m") or 0.0)
    centres, sig, floor = kerb_wear_centres(plan, corner)
    raw = []
    for s in sts:
        w = max([floor] + [math.exp(-0.5 * (_signed_gap(s["s"], c, lap) / sig) ** 2) for c in centres])
        raw.append(min(KERB_ATLAS_COLUMNS - 1, int(KERB_ATLAS_COLUMNS * w)))
    a = kerb_arcs(sts, sgn)
    n = len(sts)
    joints, metres = [], []
    for j in range(0, int(math.floor(a[-1] / KERB_BLOCK_M + 0.5)) + 1):
        q = min(range(n), key=lambda i: abs(a[i] - j * KERB_BLOCK_M))
        if (joints and q <= joints[-1]) or abs(a[q] - j * KERB_BLOCK_M) > KERB_JOINT_SNAP_MAX_M:
            continue                      # no station near this whole metre (a trimmed fold's long span): no joint here
        joints.append(q)
        metres.append(j * KERB_BLOCK_M)
    v_m = [0.0] * n
    for k, q in enumerate(joints):
        q1 = joints[k + 1] if k + 1 < len(joints) else n
        for i in range(q, q1):
            if k + 1 < len(joints):
                f = (a[i] - a[q]) / max(1e-9, a[q1] - a[q])
                v_m[i] = metres[k] + f * (metres[k + 1] - metres[k])
            else:
                v_m[i] = metres[k] + (a[i] - a[q])
    for i in range(joints[0]):            # never: station 0 is nearest metre 0
        v_m[i] = a[i] - a[joints[0]] + metres[0]
    levels = [0] * max(0, n - 1)
    for k, q in enumerate(joints):
        q1 = joints[k + 1] if k + 1 < len(joints) else n - 1
        if q1 <= q:
            continue
        lv = max(raw[q:q1])
        for i in range(q, q1):
            levels[i] = lv
    seams = sum(1 for i in range(1, len(levels)) if levels[i] != levels[i - 1])
    m_by = [0.0] * KERB_ATLAS_COLUMNS
    for i, lv in enumerate(levels):
        m_by[lv] += a[i + 1] - a[i]
    apex = float(plan.get("apex_station", corner.get("apex_station", 0.0)))
    heavy, run = [], None
    top = KERB_ATLAS_COLUMNS - 1
    for i, lv in enumerate(levels + [None]):
        if lv == top and run is None:
            run = i
        elif lv != top and run is not None:
            heavy.append([round(_signed_gap(sts[run]["s"], apex, lap), 1), round(_signed_gap(sts[i]["s"], apex, lap), 1)])
            run = None
    return {"levels": levels, "v_m": v_m, "joints": joints, "raw": raw, "seams": seams,
            "m_by_level": [round(x, 1) for x in m_by], "heavy_spans_m_from_apex": heavy, "arcs_m": a}


def kerb_atlas_face_uvs(n_stations, side, wear):
    """per-face, per-corner UVs for kerb_mesh(stations, side)'s faces (same order, same corner order): u in the
    span's rubber column (kerb_profile_u across, inside the pad), v = KERB_V_SIGN[side] x warped metres / 8 m —
    continuous along the whole kerb; a column change splits only the joint station's row, and only its ramp and top
    faces' corners: the outer face (i = 2) always wraps KERB_OUTER_FACE_COLUMN (the same pixels in every column)"""
    pu = kerb_profile_u()
    vs = KERB_V_SIGN["L" if side > 0 else "R"]
    out = []
    for q in range(n_stations - 1):
        lv = wear["levels"][q]
        a, b = 4 * q, 4 * (q + 1)
        for i in range(3):
            col = KERB_OUTER_FACE_COLUMN if i == 2 else lv
            f = (a + i, a + i + 1, b + i + 1, b + i)
            if side <= 0:
                f = (f[0], f[3], f[2], f[1])
            out.append([(kerb_atlas_u(col, pu[v % 4]), vs * wear["v_m"][v // 4] / KERB_ATLAS_V_M) for v in f])
    return out


def uv_handedness(verts, face, uvs):
    """+1 / -1: the sign of (T x B) . N for one face (first three corners) — T, B the directions of increasing u,
    v on the surface, N the winding normal. Same sign on every face = one wrap handedness."""
    p0, p1, p2 = (verts[i] for i in face[:3])
    (u0, v0), (u1, v1), (u2, v2) = uvs[0], uvs[1], uvs[2]
    e1 = [p1[k] - p0[k] for k in range(3)]
    e2 = [p2[k] - p0[k] for k in range(3)]
    du1, dv1, du2, dv2 = u1 - u0, v1 - v0, u2 - u0, v2 - v0
    det = du1 * dv2 - du2 * dv1
    if abs(det) < 1e-15:
        return 0
    T = [(e1[k] * dv2 - e2[k] * dv1) / det for k in range(3)]
    B = [(e2[k] * du1 - e1[k] * du2) / det for k in range(3)]
    N = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
    C = [T[1] * B[2] - T[2] * B[1], T[2] * B[0] - T[0] * B[2], T[0] * B[1] - T[1] * B[0]]
    d = sum(C[k] * N[k] for k in range(3))
    return 1 if d > 0 else -1 if d < 0 else 0


# ---------------------------------------------------------------------------------------------
# bands: the declaration the gates read (written by tools/barrier_bands.py — the data agent's file)
def load_bands(proj, lap=None):
    """data/barrier_bands.json (the mainline), or with `lap` data/barrier_bands.<lap>.json — None when absent"""
    p = Path(proj) / "data" / ("barrier_bands.json" if not lap else f"barrier_bands.{lap}.json")
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


def corridors(bands):
    """{layout id: corridor} — barrier_bands.json v2 `corridors` (ledger 0049), {} for a v1 file"""
    return (bands or {}).get("corridors") or {}


def closure_token(bands, layout_id):
    """the owner token a race layout's closure objects carry in their names ("cw" / "acw"): DECLARED by
    barrier_bands.json corridors.<id>.token (from track.config.json layouts[].closure_token)"""
    c = corridors(bands).get(layout_id) or {}
    return str(c.get("token") or "").lower()


def token_layouts(bands):
    """{token: layout id} of every declared closure (check_bands refuses a duplicate or malformed token)"""
    return {closure_token(bands, lid): lid for lid in corridors(bands) if closure_token(bands, lid)}


def check_bands(bands, pts, island_w=None):
    """what the furniture needs from a declaration before it plans anything (the band writer's own self-gates
    are tools/barrier_bands.py's); returns a list of problems. A ledger-0047 (v1) file — a centre chain
    declared, no `corridors` — is refused: the chain is retired, each direction has its own closure."""
    m = unique_count(pts)
    probs = []
    if any(float(w or 0.0) > 0.0 for w in (bands.get("centre_w_by_vertex") or [])):
        probs.append("centre_w_by_vertex declares the ledger-0047 centre chain — retired by ledger 0049 (one closure "
                     "per direction); re-run tools/barrier_bands.py (v2)")
    if any(str(r.get("kind")) == "centre" for r in (bands.get("runs") or [])):
        probs.append("runs[] declares a centre run — retired by ledger 0049")
    ei = bands.get("edge_inset_by_vertex") or []
    if len(ei) < m:
        probs.append(f"edge_inset_by_vertex has {len(ei)} entries, the centreline {m} unique vertices")
    cors = corridors(bands)
    if not cors:
        probs.append("no corridors.<layout id> in barrier_bands.json — a ledger-0047 (v1) declaration; re-run "
                     "tools/barrier_bands.py (v2)")
    seen = {}
    for lid, c in sorted(cors.items()):
        tok = str(c.get("token") or "")
        if not TOKEN_RE.match(tok):
            probs.append(f"corridors.{lid}.token {tok!r} is not a lower-case [a-z0-9]+ name token")
        elif tok in seen:
            probs.append(f"corridors.{lid}.token {tok!r} is also {seen[tok]}'s — each layout owns its closure")
        seen[tok] = lid
        y = c.get("closure_y_by_vertex")
        if not isinstance(y, list) or len(y) < m:
            probs.append(f"corridors.{lid}.closure_y_by_vertex has {len(y) if isinstance(y, list) else 'no'} entries, "
                         f"the centreline {m}")
        if not c.get("runs"):
            probs.append(f"corridors.{lid}: no closure runs declared")
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


def edge_lateral(half_w, inset, mode):
    """lateral (unsigned) of the strip CENTRE for a road half-width"""
    if mode == "walk":
        return half_w + EDGE_WALK_CENTRE_M
    return half_w - inset + BARRIER_HALF_W


def loop_start(pts, m, window=LOOP_START_WINDOW, lat_fns=()):
    """the vertex a CLOSED curb-strip loop is swept from: the straightest point of the lap (the least heading change
    between the tangents `window` vertices either side; ties -> the lowest index) among the vertices more than
    FOLD_SEARCH_RINGS + 2 vertices from any backward step of the strip offsets `lat_fns` (each k -> signed lateral)
    — so no fold, and no fold's crossing search, ever straddles the loop's two ends (with no safe vertex: the one
    farthest from every backward step). The swept loop is rotated to its first street boundary afterwards
    (_rotate_loop), so the start never names an object. loop_start(pts, m) alone is the straightest vertex."""
    T = [tangent(pts, k, m) for k in range(m)]
    turn = []
    for k in range(m):
        a, b = T[(k - window) % m], T[(k + window) % m]
        turn.append(abs(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])))
    marked = set()
    for lat in lat_fns:
        P = []
        for k in range(m):
            lx, lz = left_normal(*T[k])
            P.append((pts[k][0] + lx * lat(k), pts[k][2] + lz * lat(k)))
        for k in range(m):
            a = (k - 1) % m
            dx, dz = P[k][0] - P[a][0], P[k][1] - P[a][1]
            if dx * T[a][0] + dz * T[a][1] < 0.0 or dx * T[k][0] + dz * T[k][1] < 0.0:
                marked |= {a, k}
    dist = [m] * m
    if marked:
        for k in marked:                       # ring index distance to the nearest backward step (two sweeps)
            dist[k] = 0
        for _ in range(2):
            for k in range(m):
                dist[k] = min(dist[k], dist[(k - 1) % m] + 1)
            for k in range(m - 1, -1, -1):
                dist[k] = min(dist[k], dist[(k + 1) % m] + 1)
    safe = [k for k in range(m) if dist[k] > FOLD_SEARCH_RINGS + 2]
    if not safe:
        return max(range(m), key=lambda k: (dist[k], -turn[k], -k))
    best, bk = None, safe[0]
    for k in safe:
        if best is None or turn[k] < best - 1e-12:
            best, bk = turn[k], k
    return bk


def _edge_runs(pts, widths, ei, mode="road", height=BARRIER_H, table=None):
    """[(side, whole-run plan, closed)] — the kerb-line strips as declared: where `edge_inset_by_vertex` is set on
    EVERY vertex (ledger 0049 C1: edge_gaps none) each side is ONE closed loop swept from loop_start() round to
    the same vertex again (the last ring repeats the first, both 'join'); a gapped (pre-0049) declaration gives one
    run per interval with free ends. edge_plans (the authored line) and edge_fold_corners (what
    tools/barrier_bands.py declares) both sweep these, so the trimmed corners agree by construction."""
    m = unique_count(pts)
    st = stations(pts)
    ivs = intervals(ei, m)
    closed = ivs == [(0, m - 1)]
    out = []
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        def lat(k, s=sgn):
            return s * edge_lateral(widths[k] / 2.0, ei[k] or EDGE_INSET_M, mode)
        if closed:
            s0 = loop_start(pts, m, lat_fns=[lambda k, s=s_: s * edge_lateral(widths[k] / 2.0, ei[k] or EDGE_INSET_M, mode)
                                             for s_ in (1.0, -1.0)])
            ks = walk(s0, (s0 - 1) % m, m) + [s0]
            out.append((side, _plan_run(pts, widths, m, st, ks, lat, "join", "join", height, "edge",
                                        street_of(s0, table), side, (s0, s0)), True))
        else:
            for i, j in ivs:
                out.append((side, _plan_run(pts, widths, m, st, walk(i, j, m), lat, "free", "free", height, "edge",
                                            street_of(i, table), side, (i, j)), False))
    return out


def _rotate_loop(rings, table):
    """a CLOSED strip loop (its last ring stands where its first does) rotated to start at its first street boundary,
    so every swept object is one street's; the arcs are rebased so the texture u runs on from the new start"""
    body = rings[:-1]
    idx = next((i for i in range(1, len(body)) if street_of(body[i]["k"], table) != street_of(body[i - 1]["k"], table)), 0)
    if idx == 0:
        return rings
    a_first, a_new, total = rings[0]["arc"], body[idx]["arc"], rings[-1]["arc"] - rings[0]["arc"]
    out = [dict(r, arc=r["arc"] - a_new) for r in body[idx:]]
    out += [dict(r, arc=r["arc"] - a_first + total - (a_new - a_first)) for r in body[:idx]]
    out.append(dict(body[idx], arc=total))
    return out


def _cut_streets(rings, table):
    """cut a ring list at every street change: the boundary ring is shared by both pieces (zero gap, no cap)"""
    pieces, cur = [], [rings[0]]
    for r in rings[1:]:
        cur.append(r)
        if street_of(r["k"], table) != street_of(cur[0]["k"], table) and r is not rings[-1]:
            pieces.append(cur)
            cur = [r]
    pieces.append(cur)
    return pieces


def edge_plans(pts, widths, bands, mode="road", height=BARRIER_H):
    """both curb faces — COMMON to every race layout (ledger 0049): each side one CLOSED loop (bridges included, C1),
    every inside-lip fold TRIMMED on the whole loop first (trim_folded_rings: one mitred corner ring where the offset
    curve's legs meet — the curb's own corner), densified, rotated to a street boundary and cut at street boundaries
    on shared rings (every end a `join`, no cap, no free end) so every object is named for its street. The
    declaration wins: when data/barrier_bands.json carries `edge_corners` (tools/barrier_bands.py, the same
    computation — edge_fold_corners) every trimmed corner must be one it declares, and every declared corner must
    be trimmed — else SystemExit (re-run the band writer)."""
    m = unique_count(pts)
    ei = bands["edge_inset_by_vertex"]
    table = street_table(bands)
    plans = []
    found = []
    for side, whole, closed in _edge_runs(pts, widths, ei, mode, height, table):
        i, j = whole["run"]
        rings, skipped, corners = trim_folded_rings(whole["rings"])
        found += [dict(c, side=side) for c in corners]
        assigned = set()
        rings, _ = densify_rings(rings, m)      # AFTER the trim: the two corner spans stay straight chords
        if closed:
            rings = _rotate_loop(rings, table)
        pieces = _cut_streets(rings, table)
        for pi, pr in enumerate(pieces):
            sk = "join" if (closed or pi > 0) else "free"
            ek = "join" if (closed or pi < len(pieces) - 1) else "free"
            plan = dict(whole, rings=pr, street=street_of(pr[0]["k"], table), run=(pr[0]["k"], pr[-1]["k"]),
                        start_kind=sk, end_kind=ek, closed_loop=closed)
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


def closure_runs(bands, layout_id, m):
    """[(i, j, run record)] — the layout's declared closure runs in FORWARD vertex order (increasing index; a run
    declared in its layout's travel order, i > j for race_acw, is turned round): the walk i -> j on which
    closure_y_by_vertex is declared at every vertex, pins included. A run with a null inside it is a SystemExit."""
    c = corridors(bands).get(layout_id) or {}
    y = c.get("closure_y_by_vertex") or []
    out = []
    for r in c.get("runs") or []:
        i, j = int(r["i"]) % m, int(r["j"]) % m
        fw, bw = walk(i, j, m), walk(j, i, m)
        ok_f = all(k < len(y) and y[k] is not None for k in fw)
        ok_b = all(k < len(y) and y[k] is not None for k in bw)
        if ok_f and (not ok_b or len(fw) <= len(bw)):
            out.append((i, j, r))
        elif ok_b:
            out.append((j, i, r))
        else:
            raise SystemExit(f"[race] corridors.{layout_id} run v{r['i']}-v{r['j']}: closure_y_by_vertex is null inside "
                             f"it in both directions — the declaration is broken (re-run tools/barrier_bands.py)")
    return out


def closure_side(bands, layout_id):
    """'L' / 'R': the side of the layout's lane its closure bounds, in the FORWARD frame (race_cw travels forward
    with its race side on the right: closure 'L'; race_acw the mirror) — corridors.<id>.closure_side when declared"""
    c = corridors(bands).get(layout_id) or {}
    s = str(c.get("closure_side") or "").upper()
    if s in ("L", "R"):
        return s
    return "R" if str(c.get("direction", "forward")) == "reverse" else "L"


def closure_plans(pts, widths, bands, layout_id, height=BARRIER_H):
    """ONE race layout's closure (ledger 0049): one swept run per declared closure run on
    `corridors.<layout_id>.closure_y_by_vertex` (the CENTRE lateral, + = forward-left, lerped between vertices —
    the declared curve verify_race C' measures against), both ends 'pin': full height and width, the end cap
    kept and BURIED in the far curb strip (the pin ring is centred on that strip's line). A closure that folds
    (trim_folded_rings finds a corner) is a SystemExit — the declaration's line is tighter than its own offset.
    Densified (<= RING_SPACING_MAX_M, chord <= CHORD_MAX_M on the declared curve), split at
    MAX_RINGS_PER_OBJECT rings on shared boundary rings. Plans carry token / layout / pins."""
    m = unique_count(pts)
    st = stations(pts)
    c = corridors(bands).get(layout_id)
    if c is None:
        raise SystemExit(f"[race] no corridors.{layout_id} in barrier_bands.json — re-run tools/barrier_bands.py (v2)")
    tok = closure_token(bands, layout_id)
    if not TOKEN_RE.match(tok):
        raise SystemExit(f"[race] corridors.{layout_id}.token {tok!r} is not a lower-case [a-z0-9]+ name token")
    y = c["closure_y_by_vertex"]
    table = street_table(bands)
    side = closure_side(bands, layout_id)
    far = "edge_L" if side == "L" else "edge_R"
    plans = []
    for i, j, rec in closure_runs(bands, layout_id, m):
        ks = walk(i, j, m)
        whole = _plan_run(pts, widths, m, st, ks, lambda k: float(y[k]), "pin", "pin", height, "close",
                          street_of(i, table), side, (i, j))
        rings, dropped, corners = trim_folded_rings(whole["rings"])
        if corners or dropped:
            raise SystemExit(f"[race] closure {layout_id} v{i}-v{j} folds at {[(cn['in_vertex'], cn['out_vertex']) for cn in corners]} "
                             f"— the declared line is tighter than its own offset there; re-solve the corridor")
        rings, _ = densify_rings(rings, m)
        decl_ends = {int(e.get("vertex", -1)) % m: e for e in (rec.get("ends") or []) if isinstance(e, dict)}
        pins = []
        for v in (i, j):
            e = decl_ends.get(v, {})
            pins.append({"vertex": v, "y": round(float(y[v]), 4), "joins": str(e.get("joins") or far)})
        whole.update(rings=rings, token=tok, layout=layout_id, pins=pins, closed_loop=False,
                     run_length_m=round(rings[-1]["arc"] - rings[0]["arc"], 1))
        for part in _count_inserted(split_plan(whole)):
            part["fold_corners"], part["fold_skipped"] = [], 0
            plans.append(part)
    return plans


# ---------------------------------------------------------------------------------------------
# corners -> race kerbs (tools/place_signs.py's detector, read-only)
def detect_kerb_corners(pts, widths, bands, min_defl=KERB_DEFL_MIN_DEG):
    import place_signs as ps   # noqa: E402  (the signs workflow's file; imported, never edited)
    rb = ps.Ribbon("MAINLINE", pts, widths, True)
    cw = bands.get("centre_w_by_vertex") or []        # all 0 / absent since ledger 0049: every corner gets its inside kerb
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
        chained = apex_v < len(cw) and float(cw[apex_v] or 0.0) > 0.0
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
    nothing in the detector's corner table matched (an author-time warning; verify_race's gate).

    A kerb the declaration DROPS (`kerbs_dropped`, from track.config.json race.kerbs.trims — ledger 0049 fix
    round: an inside kerb on a ribbon fold sits under the other road sheet) is removed from its corner here, so
    nothing is swept there; the declared set and the authored set stay equal (verify_race E)."""
    KIND = {"outside": "out", "inside": "in", "out": "out", "in": "in"}
    declared = {(int(kb["apex"]), str(kb["side"]).upper()): kb for kb in (bands.get("kerbs") or [])}
    dropped = {(int(d["apex"]), str(d["side"]).upper()) for d in (bands.get("kerbs_dropped") or [])}
    matched = set()
    n = len(rb.raw)
    for c in corners:
        if dropped:
            c["kerbs"] = [kb for kb in c["kerbs"] if (c["apex_vertex"], kb["side"]) not in dropped]
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
                          "fold_skipped": skipped, "fold_corners": kcorners, "declared": bool(kb.get("declared")),
                          "apex_station": float(kb.get("apex_station", c.get("apex_station", 0.0))), "lap_m": rb.L})
    return plans


def seg_seg_dist(p1, p2, q1, q2):
    """xz distance between the segments p1-p2 and q1-q2 (0 where they cross)"""
    r = _seg_cross(p1, p2, q1, q2)
    if r and 0.0 <= r[0] <= 1.0 and 0.0 <= r[1] <= 1.0:
        return 0.0
    return min(seg_dist(p1, q1, q2), seg_dist(p2, q1, q2), seg_dist(q1, p1, p2), seg_dist(q2, p1, p2))


class SegIndex:
    """a cell hash of footprint segments (p, q, half, tag): `near(a, b, reach)` yields every segment whose cell
    box overlaps the box of a-b grown by reach"""

    def __init__(self, segs, cell=4.0):
        self.segs, self.cell, self.cells = segs, cell, {}
        for si, (p, q, half, _tag) in enumerate(segs):
            for key in self._keys(p, q, half):
                self.cells.setdefault(key, []).append(si)

    def _keys(self, p, q, grow):
        c = self.cell
        x0, x1 = int(math.floor((min(p[0], q[0]) - grow) / c)), int(math.floor((max(p[0], q[0]) + grow) / c))
        z0, z1 = int(math.floor((min(p[1], q[1]) - grow) / c)), int(math.floor((max(p[1], q[1]) + grow) / c))
        return [(i, j) for i in range(x0, x1 + 1) for j in range(z0, z1 + 1)]

    def near(self, a, b, reach):
        seen = set()
        for key in self._keys(a, b, reach):
            for si in self.cells.get(key, ()):
                if si not in seen:
                    seen.add(si)
                    yield self.segs[si]


def closure_footprints(cplans):
    """[(p, q, half, layout)] — every planned closure's centre polyline as segments, half = the K-rail half base x
    the ring's lateral scale (1 on a closure)"""
    segs = []
    for p in cplans:
        rs = p["rings"]
        for a, b in zip(rs, rs[1:]):
            segs.append((_strip_xz(a), _strip_xz(b), BARRIER_HALF_W * max(a.get("ls", 1.0), b.get("ls", 1.0)),
                         p.get("layout")))
    return segs


def kerb_station_footprint(s, sgn):
    """the kerb's cross-section at a station in plan: lane lip -> outer edge (about the mid-line x ls at a mitre)"""
    lx, lz = left_normal(s["tx"], s["tz"])
    mid = s["lip"] + sgn * KERB_W / 2.0
    h = KERB_W / 2.0 * s.get("ls", 1.0)
    return (s["cx"] + lx * (mid - h), s["cz"] + lz * (mid - h)), (s["cx"] + lx * (mid + h), s["cz"] + lz * (mid + h))


def _kerb_heights(sts):
    """re-taper a (clipped) kerb's height over its first / last KERB_TAPER_STATIONS stations — kerb_plans' rule"""
    n = len(sts)
    out = []
    for q, s in enumerate(sts):
        d = min(q, n - 1 - q)
        out.append(dict(s, h=max(0.005, KERB_H * min(1.0, (d + 0.5) / KERB_TAPER_STATIONS))))
    return out


def clip_kerbs(kplans, cplans, clear=KERB_CLOSURE_CLEAR_M):
    """Ledger 0049 §6 clip rule, in place: every race kerb is cut to the longest contiguous run of its stations that
    contains the apex and whose footprint stands >= `clear` off EVERY race layout's closure footprint (the kerbs are
    common; a kerb under either direction's wall is cut for both). The cut ends re-taper. Each plan gets
    `clip = {stations_removed: [start, end], by: [layouts], clear_m, min_clear_m}`. A kerb whose APEX station is
    under a closure is a SystemExit: the declaration put a closure on a corner (boxes exist to prevent it)."""
    segs = closure_footprints(cplans)
    index = SegIndex(segs)
    reach = BARRIER_HALF_W * MITRE_MAX + clear + 0.5
    for kp in kplans:
        sgn = 1.0 if kp["side"] == "L" else -1.0
        sts = kp["stations"]
        okay, mins, by = [], [], set()
        for s in sts:
            a, b = kerb_station_footprint(s, sgn)
            worst = float("inf")
            for p, q, half, lid in index.near(a, b, reach):
                d = seg_seg_dist(a, b, p, q) - half
                if d < clear:
                    by.add(lid)
                worst = min(worst, d)
            okay.append(worst >= clear)
            mins.append(worst)
        L = kp.get("lap_m") or 0.0
        ap = kp.get("apex_station")

        def gap(s_):
            d = abs(s_ - ap)
            return min(d, L - d) if L else d
        ai = min(range(len(sts)), key=lambda q: gap(sts[q]["s"])) if ap is not None else len(sts) // 2
        if not okay[ai]:
            raise SystemExit(f"[race] kerb {object_name(kp)}: its apex station stands {mins[ai]:.2f} m off a closure "
                             f"(< {clear} m) — a closure on a corner; the corridor's boxes must hold the corner")
        lo = ai
        while lo > 0 and okay[lo - 1]:
            lo -= 1
        hi = ai
        while hi < len(sts) - 1 and okay[hi + 1]:
            hi += 1
        removed = [lo, len(sts) - 1 - hi]
        if lo or hi < len(sts) - 1:
            kp["stations"] = _kerb_heights(sts[lo:hi + 1])
        kept = mins[lo:hi + 1]
        kp["clip"] = {"stations_removed": removed, "by": sorted(str(x) for x in by), "clear_m": clear,
                      "min_clear_m": (round(min(kept), 3) if kept and min(kept) < float("inf") else None)}
    return kplans


def kerb_closure_clips(pts, widths, bands, mode="road", height=BARRIER_H):
    """What tools/barrier_bands.py (v2) declares as the kerbs' clipped i/j — the SAME plan + clip the author sweeps
    (the edge_fold_corners precedent: the declaration IS the authored line). For every declared kerb: the
    vertices whose stations bound its kept stations, rounded INWARD (i = the first vertex at or after the first kept
    station, j = the last at or before the last), plus the stations the clip removed and the layouts it removed
    them for. [{apex, side, kind, i, j, stations_removed, by, clear_m, min_clear_m}]"""
    rb, corners = detect_kerb_corners(pts, widths, bands)
    apply_declared_kerbs(rb, corners, bands)
    kps = kerb_plans(rb, corners, bands, mode)
    cps = [p for lid in sorted(corridors(bands)) for p in closure_plans(pts, widths, bands, lid, height)]
    clip_kerbs(kps, cps)
    m = len(rb.raw)
    out = []
    for kp in kps:
        s_a, s_b = kp["stations"][0]["s"], kp["stations"][-1]["s"]
        span = (s_b - s_a) % rb.L
        ks = walk(int(kp["run"][0]) % m, int(kp["run"][1]) % m, m)
        inside = [k for k in ks if ((rb.cum[k] - s_a) % rb.L) <= span + 1e-6]
        i, j = (inside[0], inside[-1]) if inside else (kp["run"][0], kp["run"][1])
        out.append({"apex": kp["apex"], "side": kp["side"], "kind": {"out": "outside", "in": "inside"}.get(kp["sub"], kp["sub"]),
                    "i": i, "j": j} | {k: v for k, v in kp["clip"].items()})
    return out


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
    each corner). A closure never folds (closure_plans refuses one). Returns (rings, n_dropped, corners)."""
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
    `edge_corners`: the SAME _edge_runs (one closed loop per side when every vertex is declared — ledger 0049 C1)
    + trim_folded_rings that edge_plans authors, so the declaration IS the authored line. Sorted by (side,
    in_vertex). Each record: side, kind (loop | extend), xz (the corner X, engine frame), turn_deg, mitre,
    in_vertex / out_vertex (the leg rings either side), removed (the vertices with no ring on that side: the
    declared band runs in_vertex -> xz -> out_vertex across them), n_removed, extension_m."""
    out = []
    for side, run, _closed in _edge_runs(pts, widths, edge_inset, mode, height):
        out += [dict(c, side=side) for c in trim_folded_rings(run["rings"])[2]]
    return sorted(out, key=lambda c: (c["side"], int(c["in_vertex"])))


# ---------------------------------------------------------------------------------------------
# names
def object_name(plan):
    lap = f"{LAP_FIELD}{plan['lap']}_" if plan.get("lap") else ""      # ledger 0054: a lap's common set
    if plan["kind"] == "edge":
        return f"1WALL_race_edge_{lap}{plan['side']}_{plan['street']}_{plan['run'][0]}_{plan['part']}"
    if plan["kind"] == "close":
        return f"1WALL_race_close_{plan['token']}_{plan['street']}_{plan['run'][0]}_{plan['part']}"
    if plan["kind"] == "kerb":
        return f"1KERB_race_{lap}{plan['apex']}_{plan['sub']}"
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


def spawn_clearance_table(pts, widths, bands, dummies, mode="road", layout_id=None):
    """One record per FACING dummy (grid / pit / hotlap; AC_TIME_* skipped): the nearest vertex, the
    signed lateral (+ = left of the FORWARD centreline), the edge-strip face it faces and the car's
    clearance to it; with `layout_id` and a declared corridor (ledger 0049) also `clear_lane_m`, the car's
    clearance to the nearer face of that layout's lane (corridors.<id>.lane_by_vertex, forward frame [lo, hi] —
    the curb-strip faces in WHOLE / BOX zones, the closure face where one stands). Pure; verify_race and the
    author tool both read it."""
    m = unique_count(pts)
    ei = bands["edge_inset_by_vertex"]
    lane = (corridors(bands).get(layout_id) or {}).get("lane_by_vertex") if layout_id else None
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
               "clear_edge_m": round(face - (abs(lat) + CAR_HALF_W), 3), "clear_lane_m": None, "lane_m": None}
        if lane and k < len(lane) and lane[k]:
            lo, hi = float(lane[k][0]), float(lane[k][1])
            rec["lane_m"] = [round(lo, 3), round(hi, 3)]
            rec["clear_lane_m"] = round(min(lat - CAR_HALF_W - lo, hi - (lat + CAR_HALF_W)), 3)
        out.append(rec)
    return out


def spawn_clearance(pts, widths, bands, dummies, mode="road", layout_id=None):
    """(hard, notes): hard = a car on this spawn overlaps a strip / its lane face OR stands closer than
    SPAWN_MARGIN_M (0.30 m) to one — never ship (HARD since 2026-10-11); notes = the minimum clearance found, one
    line (reported, never gated)"""
    hard, notes = [], []
    worst = None
    for r in spawn_clearance_table(pts, widths, bands, dummies, mode, layout_id):
        name, k, lat, face = r["name"], r["vertex"], r["lat_m"], r["edge_face_m"]
        clear = r["clear_edge_m"]
        if clear < 0:
            hard.append(f"{name} at v{k} lat {lat:+.2f}: car edge {abs(lat) + CAR_HALF_W:.2f} m overlaps the edge-strip face {face:.2f} m")
        elif clear < SPAWN_MARGIN_M:
            hard.append(f"{name} at v{k} lat {lat:+.2f}: only {clear:.2f} m clear of the edge-strip face ({face:.2f} m) "
                        f"< {SPAWN_MARGIN_M:.2f} m")
        if worst is None or clear < worst[0]:
            worst = (clear, f"{name} v{k} (edge-strip face {face:.2f} m)")
        cl = r["clear_lane_m"]
        if cl is not None:
            if cl < 0:
                hard.append(f"{name} at v{k} lat {lat:+.2f}: the car stands outside its lane {r['lane_m']} (a closure or strip face)")
            elif cl < SPAWN_MARGIN_M:
                hard.append(f"{name} at v{k} lat {lat:+.2f}: only {cl:.2f} m clear of its lane face {r['lane_m']} < {SPAWN_MARGIN_M:.2f} m")
            if cl < worst[0]:
                worst = (cl, f"{name} v{k} (lane face {r['lane_m']})")
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
def strip_length(rings):
    """the swept strip's own plan length (its centre polyline; `arc` measures the centreline instead)"""
    return sum(math.dist(_strip_xz(a), _strip_xz(b)) for a, b in zip(rings, rings[1:]))


def plan_all(proj, bands, mode="road", height=BARRIER_H, kerbs=True, lap=None):
    """everything the Blender tool needs, plus the corner table for the report: the COMMON furniture (both curb
    strips as closed loops, the race kerbs clipped against every closure) then every race layout's closure
    (corridors.<id>, sorted by id). A declaration check_bands refuses (a v1 file) is a SystemExit. With `lap` the
    line is data/lap.<lap>.json, `bands` that lap's declaration, and the common plans carry the lap token (their
    names: object_name)."""
    pts, widths = load_centerline(proj, lap)
    island_w = load_island_w(proj, lap)
    if len(island_w) != len(pts):
        raise SystemExit(f"[race] median_bands {len(island_w)} vs centerline {len(pts)} vertices")
    probs = check_bands(bands, pts)
    if probs:
        raise SystemExit("[race] barrier_bands.json refused: " + " | ".join(probs))
    plans = edge_plans(pts, widths, bands, mode, height)
    closures = [p for lid in sorted(corridors(bands)) for p in closure_plans(pts, widths, bands, lid, height)]
    corners = []
    if kerbs:
        rb, corners = detect_kerb_corners(pts, widths, bands)
        for d in apply_declared_kerbs(rb, corners, bands):
            print(f"[race] WARNING declared kerb apex v{d.get('apex')} {d.get('side')} {d.get('kind')} "
                  f"matches no detected corner — not authored")
        plans += clip_kerbs(kerb_plans(rb, corners, bands, mode), closures)
    if lap:
        for p in plans:
            p["lap"] = lap
    return pts, widths, island_w, plans + closures, corners


if __name__ == "__main__":
    # CLI: synthesised dummies into a (scratch) project, and the pure plan's census
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--synth-dummies", action="store_true", help="write data/dummies_<id>.json (synthesised) if absent")
    ap.add_argument("--edge-mode", default=None, choices=["road", "walk"])
    a = ap.parse_args()
    proj = Path(a.project)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    race_cfg = cfg.get("race", {}) or {}
    pts, widths = load_centerline(proj)
    mode = a.edge_mode or race_cfg.get("edge_mode", "road")
    bands = load_bands(proj)
    if a.synth_dummies:
        for lo in cfg.get("layouts", []):
            p = proj / "data" / f"dummies_{lo['id']}.json"
            if p.exists() or not lo.get("start"):
                continue
            p.write_text(json.dumps(synth_dummies(pts, widths, lo), indent=1), encoding="utf-8")
            print(f"[race] wrote SYNTHESISED {p.name} ({lo.get('direction', 'forward')})")
    if bands is None:
        raise SystemExit("[race] no data/barrier_bands.json — run tools/barrier_bands.py first")
    _, _, _, plans, corners = plan_all(proj, bands, (bands.get("params") or {}).get("edge_mode", mode))
    for c in corners:
        print(f"[race] corner apex v{c['apex_vertex']} R {c['R_apex_m']} m D {c['D_deg']} deg "
              f"-> {[k['side'] + '/' + k['kind'] for k in c['kerbs']]}")
    for kind in ("edge", "kerb", "close"):
        ps = [p for p in plans if p["kind"] == kind]
        print(f"[race] {kind}: {len(ps)} objects " + ", ".join(sorted({p.get('token') or 'common' for p in ps})))
    for p in plans:
        if p["kind"] == "kerb" and p.get("clip", {}).get("stations_removed") != [0, 0]:
            print(f"[race] kerb {object_name(p)} clipped {p['clip']}")

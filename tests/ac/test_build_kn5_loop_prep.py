"""The three Lariat preconditions in airoso's loop prep (scripts/ac/build_kn5_loop.py; V3-PLAN P1, ledger 0048).

1. **Frame.** ``_corridor_hash`` (the 0020 corridor discipline: kerb faces carved out of carriageways, trunks and
   canopies cleared from the driving envelope) was built from ``data/finished_centerline.json``, which the prep
   itself writes in the KN5 frame (north negated), and queried with Blender coordinates (east, north, up). Every
   mainline sample sat at the mirror image of the road across the origin's east-west line: the cull ran in the
   wrong places, and the real road had no corridor (connectors, read from connectors.local.json in the local
   frame, were right). The first test fails on the old function.
2. **Tiling.** Meshes over the cap are split by balanced halving into pieces of <= 50,000 positions (AC's hard
   cap is 65,535); equal-width bands overflow where switchbacks bunch the faces into one band.
3. **Stacked legs (L4), station matching only.** Every point the prep seats carries the arc station of its road
   leg and seats only against road triangles of that leg's own stretch (``LegIndex``); no vertical window.

Pure Python (no Blender): the prep's bpy passes call exactly these functions.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from scripts.ac import build_kn5_loop as bk

LON0, LAT0 = -105.22, 39.74


def _project(pts, widths=8.0, connectors=None):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "data" / "centerline.local.json").write_text(json.dumps({
        "origin": {"lon": LON0, "lat": LAT0},
        "points_xyz_m": [list(p) for p in pts],
        "widths_m": [widths] * len(pts)}), encoding="utf-8")
    if connectors is not None:
        (d / "data" / "connectors.local.json").write_text(json.dumps({"connectors": connectors}), encoding="utf-8")
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False, "loop": False}), encoding="utf-8")
    bk.declare_bridge_spans(d)          # writes data/finished_centerline.json in the KN5 frame, as the prep does
    return d


# --- 1. the frame bug ----------------------------------------------------------------------------------------
def test_corridor_hash_is_queried_in_the_frame_it_is_built_in():
    """A straight road from north 100 m to north 300 m (local frame: x = east, y = up, z = north). The prep queries
    the corridor with Blender coordinates (east, north, up), so (0, 200, 10) is ON the road and (0, -200, 10), its
    mirror across the origin, is nowhere near it. The old hash answered the other way round."""
    pts = [(0.0, 10.0, 100.0 + 2.0 * i) for i in range(101)]
    proj = _project(pts)
    fc = json.loads((proj / "data" / "finished_centerline.json").read_text())
    assert fc["points_xyz_m"][50][2] == -200.0, "the prep writes finished_centerline in the KN5 frame (north negated)"
    corr = bk._corridor_hash(proj)
    d_on, deck_on = corr(0.0, 200.0, 10.0)
    assert d_on < -3.5 and math.isclose(deck_on, 10.0), (d_on, deck_on)        # inside: 4 m half-width
    d_mirror, _ = corr(0.0, -200.0, 10.0)
    assert d_mirror > 50.0, d_mirror                                            # the mirror image is open ground
    d_edge, _ = corr(5.0, 200.0, 10.0)
    assert math.isclose(d_edge, 1.0, abs_tol=1e-6), d_edge                      # 1 m outside the 4 m half-width


def test_corridor_hash_mainline_and_connectors_share_one_frame():
    """Connectors come from connectors.local.json (local frame); the mainline must land in the same frame, so a
    connector teeing into the mainline meets it (before the fix the mainline sat mirrored, 2 x 200 m away)."""
    pts = [(0.0, 5.0, 100.0 + 2.0 * i) for i in range(101)]
    con = {"points_xyz_m": [[4.0 + 2.0 * i, 5.0, 200.0] for i in range(30)], "widths_m": [6.0] * 30}
    proj = _project(pts, connectors=[con])
    corr = bk._corridor_hash(proj)
    d_main, _ = corr(1.0, 200.0, 5.0)                 # on the mainline, 1 m east of its centre
    assert d_main < -2.5, d_main
    d_con, _ = corr(40.0, 200.0, 5.0)                 # on the connector
    assert d_con < -2.5, d_con


# --- 2. balanced-halving tiles -------------------------------------------------------------------------------
def _grid(nx, ny, x0=0.0, y0=0.0, step=1.0):
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            verts.append((x0 + i * step, y0 + j * step, 0.0))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return verts, faces


def _check_tiles(verts, faces, tiles, cap):
    seen = sorted(f for t in tiles for f in t)
    assert seen == list(range(len(faces))), "every face in exactly one tile"
    for t in tiles:
        pos = {v for f in t for v in faces[f]}
        assert 0 < len(pos) <= cap, len(pos)


def test_balanced_tiles_stay_under_the_cap_where_equal_bands_overflow():
    """A long thin strip (the lap) plus a dense knot at one end (switchbacks bunched into a few hundred metres):
    equal-width bands along the long axis put the whole knot in one band, over the cap. Balanced halving does not."""
    cap = 2000
    strip_v, strip_f = _grid(3000, 1)                       # 6,002 positions over 3 km
    knot_v, knot_f = _grid(60, 60, x0=10.0, y0=5.0, step=0.1)   # 3,721 positions in 6 m x 6 m
    verts = strip_v + knot_v
    faces = strip_f + [tuple(v + len(strip_v) for v in f) for f in knot_f]
    centres = [tuple(sum(verts[v][k] for v in f) / len(f) for k in range(3)) for f in faces]
    # today's equal bands: K = n // cap + 1 bands over the longest axis
    K = len(verts) // cap + 1
    lo = min(c[0] for c in centres); span = max(c[0] for c in centres) - lo
    bands = [[] for _ in range(K)]
    for i, c in enumerate(centres):
        bands[min(K - 1, int((c[0] - lo) / span * K))].append(i)
    worst_band = max(len({v for f in b for v in faces[f]}) for b in bands)
    assert worst_band > cap, worst_band                     # the old split overflows here
    tiles = bk.balanced_tiles(centres, faces, cap)
    _check_tiles(verts, faces, tiles, cap)
    assert len(tiles) <= 2 * (len(verts) // cap + 1), len(tiles)   # balanced: no confetti


def test_balanced_tiles_small_mesh_is_one_piece_and_the_order_is_stable():
    verts, faces = _grid(10, 10)
    centres = [tuple(sum(verts[v][k] for v in f) / len(f) for k in range(3)) for f in faces]
    assert bk.balanced_tiles(centres, faces, 1000) == [list(range(len(faces)))]
    a = bk.balanced_tiles(centres, faces, 30)
    assert a == bk.balanced_tiles(centres, faces, 30)
    _check_tiles(verts, faces, a, 30)


def test_piece_cap_is_50k_under_acs_65535():
    assert bk.PIECE_CAP == 50_000 and bk.PIECE_CAP < bk.VERT_CAP == 65_535


# --- 3. stacked legs: station matching -------------------------------------------------------------------------
def _switchback(gap_plan=20.5, rise=0.10, R=None):
    """Two legs joined by a hairpin: leg A runs north along x = 0 climbing, a 180 deg turn of radius gap/2, leg B
    runs back south along x = gap one level up. Local frame (east, up, north), 1 m points."""
    R = R or gap_plan / 2.0
    pts, st = [], 0.0
    for i in range(201):                                   # leg A: north 0 -> 200
        pts.append((0.0, rise * st, float(i))); st += 1.0
    n_arc = int(math.pi * R)
    for k in range(1, n_arc + 1):                         # the hairpin, centre (R, 200)
        a = math.pi - math.pi * k / n_arc
        p = (R + R * math.cos(a), 0.0, 200.0 + R * math.sin(a))
        st += math.dist((pts[-1][0], pts[-1][2]), (p[0], p[2]))
        pts.append((p[0], rise * st, p[2]))
    for i in range(1, 201):                               # leg B: south 200 -> 0
        st += 1.0
        pts.append((2 * R, rise * st, 200.0 - i))
    return pts


def test_leg_index_gives_each_point_its_own_legs_station():
    pts = _switchback()
    legs = bk.LegIndex([("main", pts, False)])
    la = legs.locate(1.0, 50.0)                          # beside leg A, 1 m east of it
    lb = legs.locate(19.5, 50.0)                         # beside leg B, 1 m west of it, 18.5 m east of A
    assert la[0] == lb[0] == "main"
    assert abs(la[1] - 50.0) < 1.0, la
    assert lb[1] > 350.0, lb                             # leg B's own station, ~ 200 + pi*10.25 + 150
    assert not legs.same_leg(la, lb)
    assert legs.same_leg(la, legs.locate(0.0, 60.0))
    # the two legs stand 35 m apart vertically here: rise 0.1 x the ~350 m of road between them. A vertical
    # window would have to be under that gap and over the ground's own relief; station matching needs neither
    z_a, z_b = 0.1 * la[1], 0.1 * lb[1]
    assert z_b - z_a > 30.0


def test_seating_picks_the_hit_of_the_points_own_leg_not_the_highest():
    """Where the ray finds two road sheets (an overpass, or a stacked leg overhanging a cut), the prep seats on the
    one whose station matches the point's leg; with no match it seats on nothing (never on the other leg)."""
    pts = _switchback()
    legs = bk.LegIndex([("main", pts, False)])
    own = legs.locate(0.5, 100.0)
    other = legs.locate(20.0, 100.0)
    hits = [(40.0, other), (10.0, own)]                  # highest first, as a downward ray walk returns them
    assert bk.pick_same_leg(hits, own, legs) == 10.0
    assert bk.pick_same_leg(hits[:1], own, legs) is None
    assert bk.pick_same_leg([], own, legs) is None


def test_station_window_is_cyclic_on_a_closed_lap():
    ring = [(100.0 * math.cos(2 * math.pi * k / 628), 0.0, 100.0 * math.sin(2 * math.pi * k / 628)) for k in range(628)]
    ring.append(ring[0])
    legs = bk.LegIndex([("main", ring, True)])
    a = legs.locate(100.0, -1.0)                          # just before the seam (station ~ 627)
    b = legs.locate(100.0, 1.0)                           # just after it (station ~ 1)
    assert a[1] > 600.0 and b[1] < 5.0, (a, b)
    assert legs.same_leg(a, b), "the seam is one stretch of road (L13)"



def test_seam_chunks_hold_every_same_leg_station_when_the_last_chunk_is_short():
    """A lap whose length is not a multiple of STATION_WIN_M ends in a short chunk, so near the seam a point's
    40 m window reaches two chunks back across it (verify finding, 2026-10-11: on a 1,010 m lap a point at
    station 5 is same-leg with station 985, chunk 24, which the old (25, 0, 1) neighbour set missed)."""
    r = 1010.0 / (2 * math.pi)
    ring = [(r * math.cos(2 * math.pi * k / 2020), 0.0, r * math.sin(2 * math.pi * k / 2020)) for k in range(2020)]
    legs = bk.LegIndex([("main", ring, True)])
    L, w = legs.length["main"], legs.win
    assert L % w > 1.0, (L, w)                            # the last chunk really is short
    missed = []
    sa = 0.0
    while sa < L:
        held = set(legs.neighbour_keys(legs.chunk_key(("main", sa))))
        for d in range(-int(w), int(w) + 1):
            sb = (sa + d) % L
            if legs.same_leg(("main", sa), ("main", sb)) and legs.chunk_key(("main", sb)) not in held:
                missed.append((round(sa, 1), round(sb, 1)))
        sa += 1.0
    assert not missed, missed[:10]

def test_connectors_are_their_own_legs():
    pts = [(0.0, 0.0, float(i)) for i in range(301)]
    con = [(1.0 + i, 0.0, 150.0) for i in range(40)]
    legs = bk.LegIndex([("main", pts, False), ("c0", con, False)])
    assert legs.locate(20.0, 150.5)[0] == "c0"
    assert legs.locate(0.5, 100.0)[0] == "main"
    assert not legs.same_leg(legs.locate(20.0, 150.5), legs.locate(0.5, 150.0))


def test_the_prep_seats_by_station_not_by_a_vertical_window():
    """The bpy pass uses the station matching above for the deck under the footprint and the contact band; the
    old LAYER_WIN vertical window is gone from the seating."""
    src = Path(bk.__file__).read_text(encoding="utf-8")
    assert "LAYER_WIN" not in src, "the vertical deck window is retired"
    conform = src[src.index("def _conform_and_reseat"):src.index("def _corridor_hash")]
    assert "pick_same_leg(hits, vleg, legs)" in conform and "vleg = legs.locate(x, y)" in conform
    assert "deck = _deck_same_leg(x, y, vleg)" in conform and "near3 = _near_same_leg(x, y, z, vleg)" in conform
    assert "road_bvh.find_nearest" not in conform, "the contact band seats on its own leg, not the nearest in 3D"


def test_the_corridor_carve_leaves_race_kerbs_alone():
    """0020's Rule 1 carves street kerbs / sidewalks out of carriageways; a race kerb rides the lane edge by design
    (Lake Murray v5: the carve emptied two race kerbs and the race kn5 failed to export)."""
    assert bk.corridor_carves_kerb("1KERB_sidewalk") and bk.corridor_carves_kerb("1KERB_kerb_3")
    assert not bk.corridor_carves_kerb("1KERB_race_766_in") and not bk.corridor_carves_kerb("1KERB_RACE_LAP2_1_out")
    assert not bk.corridor_carves_kerb("1ROAD_main") and not bk.corridor_carves_kerb("TREETRUNK_0")
    src = Path(bk.__file__).read_text(encoding="utf-8")
    assert "if corridor_carves_kerb(ob.name):" in src, "the bpy pass asks the rule, not its own prefix test"

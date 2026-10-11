"""tools/race_furniture.py — the pure geometry behind the race-layout furniture (ledger 0047): the
swept jersey strip (closed ring, outward normals, the (x, z, y) remap + reversed winding keeping
them outward, u = arc / 4.04 m), the kerb profile, the run splitter (<= MAX_RINGS_PER_OBJECT rings,
shared boundary ring, caps only at true ends), the seam-wrapping intervals, the names, the facing
formula and the declaration's street table / kerb runs. Plain ``test_*`` functions for
tests/run_tests.py (no pytest, no bpy). The last test runs the whole plan on the REAL Lake Murray
declaration when the repo carries it, so a change to either side shows up here before Blender.

The closed-solid test caught the strip's end caps wound inside-out on 2026-10-11 (the ring order is
clockwise seen from +t, so the plain ladder faces -t and belongs on the START cap) — keep it.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import race_furniture as rf  # noqa: E402

TRACK = ROOT / "tracks" / "san-diego-lake-murray"


def _straight_rings(n, step=3.0, lat=0.0, start="free", end="free", y=0.0):
    rings = []
    for k in range(n):
        ls, h = rf.taper(k, n, start, end)
        rings.append({"k": k, "s": k * step, "cx": k * step, "cz": 0.0, "y": y, "y_hint": y + rf.LIFT,
                      "tx": 1.0, "tz": 0.0, "lat": lat, "ls": ls, "h": h, "arc": k * step})
    return rings


def _edges(faces):
    """directed edges of every face (polygons of any size)"""
    out = []
    for f in faces:
        for i in range(len(f)):
            out.append((f[i], f[(i + 1) % len(f)]))
    return out


def test_ring_profile_is_a_closed_symmetric_ten_vertex_ring():
    ring = rf.ring_profile()
    assert len(ring) == 10
    assert ring[0] == (-rf.BARRIER_HALF_W, 0.0) and ring[-1] == (rf.BARRIER_HALF_W, 0.0)
    for (la, ha), (lb, hb) in zip(ring[:5], reversed(ring[5:])):
        assert abs(la + lb) < 1e-9 and abs(ha - hb) < 1e-9
    assert max(h for _, h in ring) == rf.BARRIER_H
    nose = rf.ring_profile(rf.NOSE_HALF / rf.BARRIER_HALF_W, rf.NOSE_H)
    assert abs(nose[0][0] + rf.NOSE_HALF) < 1e-9 and abs(max(h for _, h in nose) - rf.NOSE_H) < 1e-9


def test_strip_is_a_closed_solid_with_outward_normals_in_both_frames():
    rings = _straight_rings(12)
    verts, faces, uvs = rf.strip_mesh(rings, True, True)
    assert len(verts) == 12 * 10 and len(uvs) == len(verts)
    # closed manifold: every directed edge is matched by its reverse exactly once (caps included)
    es = _edges(faces)
    s = set(es)
    assert len(s) == len(es), "duplicate directed edge"
    for a, b in es:
        assert (b, a) in s, f"open edge {a}->{b}"
    vol = rf.signed_volume(verts, faces)
    assert vol > 0, vol
    # faces 0..9 are the first row's quads between ring vertex i and i+1: 4 = the top, 5 = the upper
    # left wall, 9 = the bottom. Left of +x travel is +z (north). Engine frame.
    nt, nl, nb = (rf.face_normal(verts, faces[i]) for i in (4, 5, 9))
    assert nt[1] > 0 and abs(nt[2]) < 1e-9, nt
    assert nl[2] > 0 and nl[2] > abs(nl[1]), nl
    assert nb[1] < 0, nb
    # the caps face -t and +t
    n_start = rf.face_normal(verts, faces[11 * 10])
    n_end = rf.face_normal(verts, faces[-1])
    assert n_start[0] < 0 and n_end[0] > 0, (n_start, n_end)
    # the reflection to Blender reverses the winding so the volume (hence every normal) stays outward
    bverts, bfaces = rf.to_blender(verts, faces)
    assert rf.signed_volume(bverts, bfaces) > 0
    assert bverts[0] == (verts[0][0], verts[0][2], verts[0][1])
    bt = rf.face_normal(bverts, bfaces[4])
    assert bt[2] > 0, bt          # top faces +Z (up) in Blender


def test_strip_uv_u_is_arc_over_module_pitch_and_monotone():
    rings = _straight_rings(8)
    _, _, uvs = rf.strip_mesh(rings, False, False)
    us = [uvs[r * 10][0] for r in range(8)]
    for r in range(8):
        assert abs(us[r] - r * 3.0 / rf.MODULE_PITCH_M) < 1e-9
    assert all(b > a for a, b in zip(us, us[1:]))
    vs = [uvs[i][1] for i in range(10)]
    assert vs[0] == 0.0 and abs(vs[-1] - 1.0) < 1e-9 and all(b >= a for a, b in zip(vs, vs[1:]))


def test_taper_kinds():
    assert rf.taper(5, 20, "free", "free") == (1.0, rf.BARRIER_H)
    ls, h = rf.taper(0, 20, "nose", "free")
    assert abs(ls - rf.NOSE_HALF / rf.BARRIER_HALF_W) < 1e-9 and abs(h - rf.NOSE_H) < 1e-9
    ls, h = rf.taper(19, 20, "free", "free")
    assert ls == 1.0 and abs(h - rf.FREE_END_H) < 1e-9
    ls, h = rf.taper(19, 20, "free", "join")
    assert (ls, h) == (1.0, rf.BARRIER_H)          # a join shares its ring with the next part: no taper


def test_split_plan_shares_boundary_rings_and_caps_only_true_ends():
    plan = {"kind": "chain", "street": "navajo", "side": "C", "run": (0, 1999), "rings": _straight_rings(2000),
            "start_kind": "free", "end_kind": "nose"}
    parts = rf.split_plan(plan)
    assert len(parts) >= 3
    assert all(len(p["rings"]) <= rf.MAX_RINGS_PER_OBJECT for p in parts)
    assert sum(len(p["rings"]) for p in parts) - (len(parts) - 1) == 2000
    for a, b in zip(parts, parts[1:]):
        assert a["rings"][-1] is b["rings"][0]
    assert [p["cap_start"] for p in parts] == [True] + [False] * (len(parts) - 1)
    assert [p["cap_end"] for p in parts] == [False] * (len(parts) - 1) + [True]
    assert [p["part"] for p in parts] == list(range(len(parts)))
    assert rf.split_plan({"rings": _straight_rings(5)})[0]["cap_start"] is True


def test_intervals_wrap_the_seam_and_walk_follows():
    flags = [1] * 5 + [0] * 10 + [1] * 5         # one run crossing the seam
    assert rf.intervals(flags, 20) == [(15, 4)]
    assert rf.walk(15, 4, 20) == [15, 16, 17, 18, 19, 0, 1, 2, 3, 4]
    assert rf.intervals([0] * 20, 20) == []
    assert rf.intervals([1] * 20, 20) == [(0, 19)]
    assert rf.intervals([0, 1, 1, 0, 1, 0], 6) == [(1, 2), (4, 4)]


def test_names_and_prefix_filter():
    assert rf.is_race_name("1WALL_race_kbar_college_780_0") and rf.is_race_name("1kerb_RACE_770_in")
    assert rf.is_race_name("1WALL_racecol_0")
    assert not rf.is_race_name("1WALL_guard") and not rf.is_race_name("1KERB_sidewalk") and not rf.is_race_name("ROAD")
    assert rf.object_name({"kind": "chain", "street": "navajo", "run": (2297, 4440), "part": 2}) == "1WALL_race_kbar_navajo_2297_2"
    assert rf.object_name({"kind": "edge", "side": "L", "street": "alvarado", "run": (0, 608), "part": 0}) == "1WALL_race_edge_L_alvarado_0_0"
    assert rf.object_name({"kind": "kerb", "apex": 770, "sub": "in"}) == "1KERB_race_770_in"
    assert rf.object_name({"kind": "collider", "part": 3}) == "1WALL_racecol_3"
    for n in ("1WALL_race_edge_L_alvarado_0_0", "1KERB_race_0_out"):
        assert " " not in n and n.upper().startswith(rf.RACE_PREFIXES)


def test_street_table_prefers_the_declaration_and_slugs_names():
    assert rf.street_slug("Lake Murray Boulevard") == "lakemurray"
    assert rf.street_slug("College Avenue") == "college" and rf.street_slug("Jackson Drive") == "jackson"
    bands = {"streets": [{"street": "Alvarado Road", "vertex_from": 0, "vertex_to": 769},
                         {"street": "College Avenue", "vertex_from": 770, "vertex_to": 1513}]}
    t = rf.street_table(bands)
    assert t == [("alvarado", 0, 769), ("college", 770, 1513)]
    assert rf.street_of(769, t) == "alvarado" and rf.street_of(770, t) == "college"
    assert rf.street_table({}) == list(rf.STREETS) and rf.street_of(1000) == "college"


def test_yaw_formula_is_the_measured_reflection_and_reverse_adds_pi():
    for tx, tz in ((1.0, 0.0), (0.0, 1.0), (-0.6, 0.8), (0.3, -0.95)):
        f = rf.yaw_blender(tx, tz, "forward")
        assert abs(f - math.atan2(tx, -tz)) < 1e-12
        r = rf.yaw_blender(tx, tz, "reverse")
        assert abs(abs(r - f) - math.pi) < 1e-12
    # the old formula atan2(tx, tz) is off by 180 deg on a north-south road (College), by ~0 on east-west (Alvarado)
    assert abs(abs(rf.yaw_blender(0.0, 1.0) - math.atan2(0.0, 1.0)) - math.pi) < 1e-12
    assert abs(rf.yaw_blender(1.0, 0.0) - math.atan2(1.0, 0.0)) < 1e-12


def test_edge_lateral_modes():
    assert abs(rf.edge_lateral(8.5, 0.82, "road") - (8.5 - 0.82 + 0.335)) < 1e-12     # face at half_w - 0.82
    assert abs(rf.edge_lateral(6.5, 0.0, "walk") - (6.5 + rf.EDGE_WALK_CENTRE_M)) < 1e-12


def test_kerb_mesh_faces_up_with_the_declared_profile():
    sts = []
    for q in range(6):
        sts.append({"s": q * 0.3, "k": q, "cx": q * 0.3, "cz": 0.0, "y": 0.0, "y_hint": 0.1, "tx": 1.0, "tz": 0.0,
                    "lip": 4.63, "h": rf.KERB_H, "arc": q * 0.3})
    verts, faces, uvs = rf.kerb_mesh(sts, 1.0)
    assert len(verts) == 24 and len(faces) == 15
    lip, ramp, outer_top, outer_base = verts[0], verts[1], verts[2], verts[3]
    assert abs(lip[2] - 4.63) < 1e-9 and abs(outer_base[2] - 5.63) < 1e-9       # 1.0 m wide, outward = +z (left)
    assert lip[1] == 0.0 and abs(ramp[1] - rf.KERB_H) < 1e-9 and abs(outer_top[1] - rf.KERB_H) < 1e-9
    assert abs(ramp[2] - lip[2] - rf.KERB_RAMP_W) < 1e-9
    for f in faces:
        assert rf.face_normal(verts, f)[1] >= -1e-9                    # nothing faces down (engine frame)
    assert rf.face_normal(verts, faces[1])[1] > 0                      # the flat top faces up
    bverts, bfaces = rf.to_blender(verts, faces)
    assert rf.face_normal(bverts, bfaces[1])[2] > 0                    # ... and +Z in Blender
    assert uvs[0] == (0.0, 0.0) and abs(uvs[4][1] - 0.3 / rf.KERB_TILE_M) < 1e-9
    # the right-hand kerb mirrors: outward = -z, still face-up
    vr, fr, _ = rf.kerb_mesh(sts, -1.0)
    assert abs(vr[3][2] - (4.63 - 1.0)) < 1e-9 and rf.face_normal(vr, fr[1])[1] > 0


def test_spawn_clearance_is_hard_below_the_margin():
    """HARD below SPAWN_MARGIN_M (0.30 m) since 2026-10-11 — the 1.4 m stagger's 0.08 m used to be a note"""
    pts = [(float(k) * 3.0, 0.0, 0.0) for k in range(10)] + [(0.0, 0.0, 0.0)]
    widths = [13.0] * 11
    bands = {"centre_w_by_vertex": [0.0] * 11, "edge_inset_by_vertex": [0.82] * 11}
    assert rf.SPAWN_MARGIN_M == 0.30
    # +3.25 right of +x travel = z -3.25 (right = (tz, -tx)); car edge 4.2 m vs the face at 5.68 m: 1.48 clear
    hard, notes = rf.spawn_clearance(pts, widths, bands, {"AC_START_0": [9.0, 0.4, -3.25], "_yaw_deg": {}})
    assert hard == [] and len(notes) == 1 and "1.48 m" in notes[0], notes
    hard, notes = rf.spawn_clearance(pts, widths, bands, {"AC_START_1": [9.0, 0.4, -4.9]})
    assert hard and "overlaps" in hard[0]
    # 0.13 m clear: was a note, is now a hard fail
    hard, notes = rf.spawn_clearance(pts, widths, bands, {"AC_PIT_0": [9.0, 0.4, -4.6]})
    assert hard and "0.13 m clear" in hard[0], hard
    # the old outer column (lane centre 3.25 + 1.4 = 4.65): 0.08 m -> hard; the new one (+ 1.0 = 4.25): 0.48 m
    hard, _ = rf.spawn_clearance(pts, widths, bands, {"AC_START_1": [9.0, 0.4, -4.65]})
    assert hard and "0.08 m clear" in hard[0], hard
    hard, notes = rf.spawn_clearance(pts, widths, bands, {"AC_START_1": [9.0, 0.4, -4.25]})
    assert hard == [] and "0.48 m" in notes[0], notes
    # just either side of the floor
    assert rf.spawn_clearance(pts, widths, bands, {"AC_START_3": [9.0, 0.4, -4.40]})[0] == []      # 0.33 m
    assert rf.spawn_clearance(pts, widths, bands, {"AC_START_3": [9.0, 0.4, -4.46]})[0] != []      # 0.27 m
    chained = dict(bands, centre_w_by_vertex=[0.67] * 11)
    hard, _ = rf.spawn_clearance(pts, widths, chained, {"AC_START_0": [9.0, 0.4, -0.8]})
    assert hard and "centre chain" in hard[0]
    hard, _ = rf.spawn_clearance(pts, widths, chained, {"AC_START_0": [9.0, 0.4, -1.455]})    # 0.17 m off the chain
    assert hard and "centre chain" in hard[0] and "0.17 m clear" in hard[0], hard
    rows = rf.spawn_clearance_table(pts, widths, chained, {"AC_START_0": [9.0, 0.4, -3.25], "AC_TIME_0_L": [9.0, 0.4, 6.0]})
    assert [r["name"] for r in rows] == ["AC_START_0"]                     # timing planes are not slots
    assert abs(rows[0]["clear_edge_m"] - 1.48) < 1e-6 and abs(rows[0]["clear_centre_m"] - 1.965) < 1e-6


def test_synth_dummies_use_the_producers_stagger():
    import layout_dummies as ld
    assert ld.GRID_STAGGER_M == 1.0
    pts = [(float(k) * 3.0, 0.0, 0.0) for k in range(60)] + [(0.0, 0.0, 0.0)]
    lo = {"id": "x", "start": {"line_vertex": 50, "grid_vertex": 45, "offset_right_m": 3.25, "sector_vertices": [10, 20]}}
    d = rf.synth_dummies(pts, [13.0] * 61, lo)
    assert d["_right_of_travel_m"]["AC_START_1"] == 4.25 and d["_right_of_travel_m"]["AC_START_2"] == 2.25


def test_apply_declared_kerbs_overrides_matching_runs_only():
    class RB:
        raw = [None] * 100
        cum = [float(3 * k) for k in range(100)]
    corners = [{"apex_vertex": 50, "kerbs": [{"side": "L", "kind": "out", "i": 40, "j": 60, "s0": 120.0, "s1": 180.0},
                                              {"side": "R", "kind": "in", "i": 45, "j": 55, "s0": 135.0, "s1": 165.0}]}]
    bands = {"kerbs": [{"apex": 50, "side": "L", "kind": "outside", "i": 42, "j": 58},
                       {"apex": 90, "side": "L", "kind": "outside", "i": 85, "j": 95}]}
    unmatched = rf.apply_declared_kerbs(RB(), corners, bands)
    out, inn = corners[0]["kerbs"]
    assert (out["i"], out["j"], out["s0"], out["s1"], out["kind"], out.get("declared")) == (42, 58, 126.0, 174.0, "out", True)
    assert (inn["i"], inn["j"], inn["kind"]) == (45, 55, "in") and not inn.get("declared")
    assert [d["apex"] for d in unmatched] == [90]


def test_real_lake_murray_declaration_plans_cleanly():
    """the whole pure plan on the repo's own declaration (skipped when the track data is absent)"""
    data = TRACK / "data"
    if not all((data / f).exists() for f in ("centerline.local.json", "median_bands.json", "barrier_bands.json")):
        print("  (no Lake Murray data in this checkout — skipped)")
        return
    pts, widths = rf.load_centerline(TRACK)
    m = rf.unique_count(pts)
    island_w = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))["island_w_by_vertex"]
    bands = rf.load_bands(TRACK)
    assert rf.check_bands(bands, pts, island_w) == []
    _, _, _, plans, corners = rf.plan_all(TRACK, bands)
    names = [rf.object_name(p) for p in plans]
    assert len(names) == len(set(names)), "duplicate object names"
    for n in names:
        assert " " not in n and n.upper().startswith(rf.RACE_PREFIXES), n
    chain = [p for p in plans if p["kind"] == "chain"]
    edge = [p for p in plans if p["kind"] == "edge"]
    kerb = [p for p in plans if p["kind"] == "kerb"]
    assert all(len(p["rings"]) <= rf.MAX_RINGS_PER_OBJECT for p in chain + edge)
    assert len(chain) == 8 and len(edge) >= 16 and len(kerb) == 7, (len(chain), len(edge), len(kerb))
    # chain: never on an island beyond the shared nose, never on Alvarado / the hairpin flare, ends taper
    noses = set(bands["summary"]["nose_vertices"]) if "summary" in bands else set()
    for p in chain:
        ks = [r["k"] for r in p["rings"]]
        assert not any(k < 780 for k in ks)
        inner = ks[(1 if p["cap_start"] else 0):(len(ks) - 1 if p["cap_end"] else len(ks))]
        assert not any(island_w[k] > 0 for k in inner), p["run"]
        i, j = p["run"]
        assert (island_w[i] > 0) == (p["start_kind"] == "nose") and (island_w[j] > 0) == (p["end_kind"] == "nose")
        if noses:
            assert (i in noses) == (p["start_kind"] == "nose") and (j in noses) == (p["end_kind"] == "nose")
    chain_len = sum(p["rings"][-1]["arc"] - p["rings"][0]["arc"] for p in chain)   # parts share boundary rings
    assert abs(chain_len - 8525.0) < 60.0, chain_len
    # edge strips: both sides, absent only inside the three declared bridge spans, at half_w - 0.82 + 0.335
    ei = bands["edge_inset_by_vertex"]
    covered = {(p["side"], r["k"]) for p in edge for r in p["rings"]}
    assert not any(ei[k] == 0 for (_, k) in covered)
    # the only flagged vertices without a ring are the folded inside-apex rings the sweep drops
    # (drop_folded_rings): all on the R side (the five corners are right-handers), within 15 vertices
    # of a corner apex, and exactly as many as the plans report
    missing = [(side, k) for k in range(m) for side in ("L", "R") if ei[k] > 0 and (side, k) not in covered]
    dropped = sum(p.get("fold_skipped", 0) for p in edge if p["part"] == 0)
    assert 0 < dropped < 60 and len(missing) == dropped, (len(missing), dropped, missing[:8])
    assert all(side == "R" for side, _ in missing), missing
    assert all(min((k - a) % m, (a - k) % m) <= 15 for _, k in missing for a in [min((0, 770, 1514, 2319, 3297), key=lambda a: min((k - a) % m, (a - k) % m))]), missing
    for p in edge:
        for r in p["rings"][:3]:
            assert abs(abs(r["lat"]) - (widths[r["k"]] / 2.0 - 0.82 + rf.BARRIER_HALF_W)) < 1e-9
    gaps = [(g["i"], g["j"]) for g in bands.get("edge_gaps", [])]
    assert len(gaps) == 3
    for i, j in gaps:
        assert not any(ei[k] > 0 for k in range(i, j + 1))
    # kerbs: the declaration's seven runs, every one matched, the seam corner's outside kerb past the I-8 span
    kb = {(p["apex"], p["side"]): p for p in kerb}
    assert set(kb) == {(0, "L"), (0, "R"), (770, "L"), (770, "R"), (1514, "L"), (2319, "L"), (3297, "L")}
    assert all(k.get("declared") for c in corners for k in c["kerbs"])
    assert kb[(0, "L")]["run"][0] == 4492 and kb[(0, "L")]["sub"] == "out" and kb[(0, "R")]["sub"] == "in"
    assert all(len(p["stations"]) >= 2 and all(0.0 < s["h"] <= rf.KERB_H for s in p["stations"]) for p in kerb)
    print(f"  real plan: {len(chain)} chain / {len(edge)} edge / {len(kerb)} kerb objects, chain {chain_len:.0f} m")

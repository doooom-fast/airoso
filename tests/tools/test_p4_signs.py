"""Ledger 0054 P4 step 1 + 6 — SIGNS and MAP (EXPANSION-PLAN A7 / A8 / A12): the pure-Python pieces.

* tools/race_furniture.py: a race layout's own W1-6 plates (SIGN*_<token>_<k>) are race objects of role 'sign' owned
  by that token; the road kn5's SIGNPLATE_<k> never match.
* tools/check_race_kn5.py / scripts/ac/verify_kn5.py: a closure kn5 may carry ITS layout's plates (and their solid
  textures); the common kn5 and another layout's closure may not.
* tools/place_signs.py: the pad decks as pavement polygons and the drive lines as disc-only ribbons in the field; the
  through-road rule (a ray down another road is no shared plate); a per_layout corner's LAYOUT PLATE behind the race
  layout's sealing wall, its id <corner>-<dir>@<layout>, its skip records per layout.
* tools/verify_signs.py: parse_id strips the layout; (m) layout coverage; (i) spacing only between posts one layout
  loads together.
* tools/expansion_lines.py: stitch strings pieces through a pad on a cubic, widths eased.
* tools/make_map.py: layouts[].map "lap" draws that layout's lap alone (map + outline), the root and the rest the network.
* the chain: the signs step after the race furniture in tools/ship_sd.sh, tracks/san-diego-lake-murray/ship.json
  and tools/ship_track.sh, with one header.
Plain ``test_*`` functions for tests/run_tests.py (no pytest, no bpy).
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import check_race_kn5 as ck  # noqa: E402
import expansion_lines as el  # noqa: E402
import make_map as mm  # noqa: E402
import place_signs as ps  # noqa: E402
import race_furniture as rf  # noqa: E402
import verify_signs as vs  # noqa: E402

WALL_TEX = ("concrete_barrier_diffuse.png", "concrete_barrier_normal.png")
CLOSE_CW = ["1WALL_race_close_cw_college_777_0", "1WALL_race_close_cw_navajo_1521_0"]
SIGNS_CW = ["SIGNPLATE_cw_0", "SIGNARROW_cw_0", "SIGNPOST_cw_0"]


def _parse(names, textures):
    return {"file_bytes": 9_000_000, "nodes": ["BlenderFile"], "textures": [{"name": t} for t in textures],
            "meshes": [{"name": n, "verts": 100, "tris": 120} for n in names]}


# --- the names -------------------------------------------------------------------------------------------------------
def test_layout_sign_names_are_race_objects_owned_by_their_token():
    assert rf.layout_sign_owner("SIGNPLATE_cw_0") == "cw" and rf.layout_sign_owner("SIGNPOST_ACW_12") == "acw"
    assert rf.layout_sign_owner("SIGNPLATE_cw_0_mat") == "cw" and rf.layout_sign_owner("SIGNARROW_cw_1_mat.001") == "cw"
    assert rf.layout_sign_owner("SIGNPLATE_0") is None and rf.layout_sign_owner("SIGNPLATE_0_mat") is None
    assert rf.layout_sign_owner("1WALL_race_close_cw_x_1_0") is None and rf.layout_sign_owner("LIGHTPOST_cw_0") is None
    assert rf.race_role("SIGNPLATE_cw_0") == "sign" and rf.race_owner("SIGNPLATE_cw_0") == "cw"
    assert rf.race_role("SIGNPLATE_0") is None and rf.race_owner("SIGNPLATE_0") is None
    assert rf.race_role("1WALL_race_close_cw_x_1_0") == "close" and rf.race_owner("1WALL_race_close_cw_x_1_0") == "cw"
    assert not rf.is_race_name("SIGNPLATE_cw_0") and rf.is_layout_sign_name("SIGNPLATE_cw_0")
    assert ck.layout_sign_owner("SIGNPOST_cw_3") == "cw" and ck.layout_sign_owner("SIGNPOST_3") is None


# --- the kn5 guards --------------------------------------------------------------------------------------------------
def test_check_race_kn5_closure_carries_its_own_plates_only():
    allowed = ck.race_texture_set()
    sign_tex = ck.sign_texture_set()
    assert sign_tex and sign_tex.isdisjoint(allowed)            # the SIGN rows' solid textures, from pbr.py's table
    r = ck.check(_parse(CLOSE_CW + SIGNS_CW, WALL_TEX + tuple(sorted(sign_tex))), allowed, role="closure", owner="cw")
    assert r["ok"] and r["summary"]["sign_plates"] == 3 and r["summary"]["closures"] == 2, r
    # another layout's plates in this closure
    r = ck.check(_parse(CLOSE_CW + ["SIGNPLATE_acw_0"], WALL_TEX + tuple(sorted(sign_tex))), allowed, role="closure", owner="cw")
    assert not r["ok"] and any("not 'cw''s closure" in f for f in r["fails"]), r["fails"]
    # the road kn5's plates (no token) are a leak anywhere
    r = ck.check(_parse(CLOSE_CW + ["SIGNPLATE_0"], WALL_TEX), allowed, role="closure", owner="cw")
    assert not r["ok"] and any("non-race meshes" in f for f in r["fails"]), r["fails"]
    # plates never ride in the COMMON kn5, and their textures are not the race set there
    common = ["1WALL_race_edge_L_alvarado_0_0", "1KERB_race_770_in"]
    r = ck.check(_parse(common + SIGNS_CW, ("kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg") + WALL_TEX + tuple(sorted(sign_tex))),
                 allowed, role="common", expect_kerbs=1)
    assert not r["ok"] and any("per-layout sign plates in the COMMON" in f for f in r["fails"]) \
        and any("textures outside the race set" in f for f in r["fails"]), r["fails"]
    # a closure with no plates still refuses the sign textures (nothing of it needs them)
    r = ck.check(_parse(CLOSE_CW, WALL_TEX + tuple(sorted(sign_tex))), allowed, role="closure", owner="cw")
    assert not r["ok"] and any("textures outside the race set" in f for f in r["fails"]), r["fails"]


def test_verify_kn5_closure_kn5_accepts_its_own_plates():
    spec = importlib.util.spec_from_file_location("vk_layouts", ROOT / "tests" / "ac" / "test_verify_kn5_layouts.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = m._synthetic()
    assert m.verify(d) == []
    # the cw closure kn5 with cw's own plates + their materials: clean
    ms, mats = m._closure_meshes("cw", extra=["SIGNPLATE_cw_0", "SIGNPOST_cw_0"])
    m.write_kn5(d / "build" / "t_closure_race_cw.kn5", ms, [], mats + ["SIGNPLATE_cw_0_mat", "SIGNPOST_cw_0_mat"])
    assert m.verify(d) == [], m.verify(d)
    # the other layout's plates: refused
    ms, mats = m._closure_meshes("cw", extra=["SIGNPLATE_acw_0"])
    m.write_kn5(d / "build" / "t_closure_race_cw.kn5", ms, [], mats + ["SIGNPLATE_acw_0_mat"])
    fails = m.verify(d)
    assert m._has(fails, "CLOSURE kn5 't_closure_race_cw.kn5' (race_cw)", "SIGNPLATE_acw_0"), fails
    # the road kn5's plates (no token): a leak
    ms, mats = m._closure_meshes("cw", extra=["SIGNPLATE_0"])
    m.write_kn5(d / "build" / "t_closure_race_cw.kn5", ms, [], mats + ["SIGNPLATE_0_mat"])
    assert m._has(m.verify(d), "non-race mesh", "SIGNPLATE_0")


# --- the field: pad decks, disc-only lines, the through-road rule ----------------------------------------------------
def _ribbon(name, pts, w=10.0, closed=False):
    return ps.Ribbon(name, pts, [w] * len(pts), closed)


def test_field_pad_polygons_are_pavement_and_drive_lines_are_discs_only():
    main = _ribbon("MAINLINE", [(float(i), 0.0, 0.0) for i in range(0, 101, 2)])
    f = ps.PavementField([main])
    f.add_polygon("pad J2", [(200.0, -20.0), (240.0, -20.0), (240.0, 20.0), (200.0, 20.0)])
    f.add_line("expansion_fwd", [(300.0, 0.0, 0.0), (300.0, 0.0, 100.0)], [8.0, 8.0])
    assert f.query(220.0, 0.0)[0] < 0 and f.query(220.0, 0.0)[1] == "pad J2"          # on the deck
    assert abs(f.query(245.0, 0.0)[0] - 5.0) < 1e-9                                    # 5 m off its east edge
    assert f.query(220.0, 0.0, only=("MAINLINE",))[0] > 0                             # a layout plate's field: the mainline alone
    q = f.query(300.0, 50.0)
    assert q[1] == "pad J2" and q[0] > 60.0                                            # the line is never pavement (the pad, 60 m off, is the nearest)
    assert f.gate_margin(300.0, 50.0) < 0 and f.gate_margin(300.0, 50.0, ("MAINLINE",)) > 100.0   # but it is a gated disc
    assert ps.disc_names_for("MAINLINE", ("MAINLINE", "expansion_fwd")) is None
    assert ps.disc_names_for("north", ("MAINLINE", "expansion_fwd")) == ("MAINLINE", "expansion_fwd")
    assert ps.gate_label(None) == "all" and ps.gate_label(("MAINLINE", "expansion_fwd")) == "MAINLINE+expansion_fwd"
    assert ps.point_in_polygon(1.0, 1.0, [(0, 0), (2, 0), (2, 2), (0, 2)]) and not ps.point_in_polygon(3.0, 1.0, [(0, 0), (2, 0), (2, 2), (0, 2)])


def _square_loop(side=200.0, R=10.0, step=2.0):
    """a closed CLOCKWISE square, R 10 m rounded corners (tests/tools/test_place_signs.py's)"""
    pts = []
    x, z, h = 0.0, 0.0, 0.0
    for _ in range(4):
        hx, hz = math.cos(math.radians(h)), math.sin(math.radians(h))
        L = side - 2 * R
        n = int(round(L / step))
        for k in range(n):
            pts.append((x + hx * k * step, 0.0, z + hz * k * step))
        x, z = x + hx * L, z + hz * L
        rx, rz = hz, -hx
        ccx, ccz = x + rx * R, z + rz * R
        a0 = math.atan2(z - ccz, x - ccx)
        for k in range(10):
            a = a0 - (math.pi / 2) * k / 10
            pts.append((ccx + R * math.cos(a), 0.0, ccz + R * math.sin(a)))
        a = a0 - math.pi / 2
        x, z = ccx + R * math.cos(a), ccz + R * math.sin(a)
        h -= 90.0
    pts.append(pts[0])
    return pts


def _proj_with_through_road(tmp, per_layout=True, bands=True):
    """the square loop (clockwise) + a 32 m wide side street 'straight_on' running EAST from the first corner at
    (200, 0) — like Waring at J1: its start (190, 12.5) is 15 m+ from the corner's apex (no mouth-flare skip) and its
    pavement covers the approach's heading, so for the forward approach (eastbound along z = 0) straight on IS that
    road; three layouts as Lake Murray has"""
    d = Path(tmp)
    (d / "data").mkdir(parents=True, exist_ok=True)
    pts = _square_loop()
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": [10.0] * len(pts)}))
    side = [[190.0 + 2.0 * k, 0.0, 12.5] for k in range(0, 45)]   # x 190 .. 278, z 12.5 +- 16: over the ray at z -2.5
    (d / "data" / "connectors.local.json").write_text(json.dumps({"connectors": [{"name": "straight_on", "kind": "connector", "points_xyz_m": side, "widths_m": [32.0] * len(side)}]}))
    (d / "data" / "mouths.json").write_text(json.dumps({"mouths": []}))
    layouts = [{"id": "street", "direction": "forward", "race_furniture": False},
               {"id": "race_cw", "direction": "forward", "race_furniture": True, "closure_token": "cw"},
               {"id": "race_acw", "direction": "reverse", "race_furniture": True, "closure_token": "acw"}]
    (d / "track.config.json").write_text(json.dumps({"slug": "zz_no_such_track_p4", "layouts": layouts}))
    if bands:
        (d / "data" / "barrier_bands.json").write_text(json.dumps({"params": {"edge_centre_from_lip_m": -0.485, "barrier_half_m": 0.335}}))
    v1 = min(range(len(pts)), key=lambda i: math.dist((pts[i][0], pts[i][2]), (190.0, -3.0)))
    corners = {"M1": {"ribbon": "MAINLINE", "vertex": v1, "plate": "W1-6", "expect_arrow": "right",
                      **({"per_layout": True} if per_layout else {})}}
    return d, pts, corners


def test_through_road_skips_the_shared_plate_and_a_per_layout_corner_gets_race_plates():
    quiet = lambda *a: None
    d, pts, corners = _proj_with_through_road(tempfile.mkdtemp())
    cfg = dict(ps.DEFAULTS, include_connectors=False, both_directions_mainline=True)
    out, ctx = ps.place_all(d, cfg, corners, log=quiet)
    ids = [s["id"] for s in out["signs"]]
    skips = {s["id"]: s for s in out["skipped"]}
    # the forward approach at M1 runs straight on down the side street (M3 at J1: College into Waring): no shared
    # plate, the rule's own reason — the ray never leaves pavement
    assert "M1-fwd" not in ids and "M1-fwd" in skips, (ids, list(skips))
    assert any(r.startswith("ray never leaves pavement") for r in skips["M1-fwd"]["reasons"]), skips["M1-fwd"]
    assert all(any(rx.match(r) for rx in vs.RULE_SKIP_RES) for r in skips["M1-fwd"]["reasons"])
    # the reverse approach (northbound) runs ACROSS the wide street for 32 m before leaving pavement (M3-rev at J1,
    # Navajo across the Waring opening): a through road, the rule's own reason
    assert "M1-rev" not in ids and "M1-rev" in skips, (ids, list(skips))
    assert any(r.startswith("ray runs") and "straight_on" in r and "(a through road)" in r for r in skips["M1-rev"]["reasons"]), skips["M1-rev"]
    assert all(any(rx.match(r) for rx in vs.RULE_SKIP_RES) for r in skips["M1-rev"]["reasons"])
    # each race layout drives one approach and got no shared plate: its own plate, behind its sealing wall, judged on
    # the mainline's field alone (every side street is sealed in a race layout)
    assert "M1-fwd@race_cw" in ids and "M1-rev@race_acw" in ids and "M1-fwd@race_acw" not in ids and "M1-rev@race_cw" not in ids, ids
    lp = next(s for s in out["signs"] if s["id"] == "M1-fwd@race_cw")
    assert lp["layout"] == "race_cw" and lp["direction"] == "fwd" and lp["arrow"] == "right"
    assert abs(lp["wall"]["behind_lip_m"] - (-0.485 + 0.335 + cfg["lateral_offset_m"])) < 1e-9 and lp["wall"]["token"] == "cw"
    assert abs(lp["checks"]["edge_clear_m"] - lp["wall"]["behind_lip_m"]) < 0.05        # 1.48 m past the loop's lip
    assert lp["checks"]["edge_clear_all_m"] < 0                                          # ...which is the side street's deck
    assert lp["checks"]["gate_ribbons"] == "MAINLINE" and lp["checks"]["gate_margin_gated_m"] >= 0
    la = next(s for s in out["signs"] if s["id"] == "M1-rev@race_acw")
    assert la["layout"] == "race_acw" and la["direction"] == "rev" and la["arrow"] == "left" and la["wall"]["token"] == "acw"
    assert ps.split_layout_id("M1-fwd@race_cw") == ("M1-fwd", "race_cw") and ps.split_layout_id("M1-fwd") == ("M1-fwd", None)
    assert out["counts"]["layout_plates"] == 2 and sorted(out["layout_plates"]) == ["M1-fwd@race_cw", "M1-rev@race_acw"]
    # merge_pairs never pairs a layout plate; a layout record is a MAINLINE plate for the direction counts
    assert ps.merge_pairs(out["signs"]) == out["signs"]
    assert ps.direction_counts(out)["fwd"] == 4 and ps.direction_counts(out)["rev"] == 4
    # the verifier: ids parse, (k) covered, (l) named corner kept, (m) every layout loads a plate or the rule's skip
    assert vs.parse_id("M1-fwd@race_cw") == ("M1", "fwd", False) and vs.split_layout("M1-fwd@race_cw") == ("M1-fwd", "race_cw")
    driven = vs.driven_directions(d)
    assert vs.direction_coverage(out, driven, entries=corners)[0] == []
    assert vs.named_coverage(out, driven, corners)[0] == []
    mf, mrows = vs.layout_coverage(out, driven, corners)
    assert mf == [], mf
    assert any(r.startswith("(m) layout street") and "M1 skipped" in r for r in mrows), mrows
    assert any(r.startswith("(m) layout race_cw") and "M1-fwd@race_cw" in r for r in mrows), mrows
    assert any(r.startswith("(m) layout race_acw") and "M1-rev@race_acw" in r for r in mrows), mrows
    # without per_layout the same corner is only skipped — and (l) says the named corner lost its forward plate
    out0, _ = ps.place_all(d, cfg, {"M1": dict(corners["M1"], per_layout=False)}, log=quiet)
    assert not any("@" in s["id"] for s in out0["signs"]) and out0["counts"]["layout_plates"] == 0
    assert vs.layout_coverage(out0, driven, corners)[0] == []          # the rule's skip covers every layout...
    assert any("M1" in f for f in vs.named_coverage(out0, driven, {"M1": dict(corners["M1"], per_layout=False)})[0])  # ...but Kevin named it
    # no race declaration: the layout plate is skipped with a reason the verifier counts as the rule's own
    d2, _, c2 = _proj_with_through_road(tempfile.mkdtemp(), bands=False)
    out2, _ = ps.place_all(d2, cfg, c2, log=quiet)
    sk2 = next(s for s in out2["skipped"] if s["id"] == "M1-fwd@race_cw")
    assert sk2["layout"] == "race_cw" and all(any(rx.match(r) for rx in vs.RULE_SKIP_RES) for r in sk2["reasons"]), sk2
    assert vs.layout_coverage(out2, driven, c2)[0] == []
    # the pieces of the stitched north ribbon are never a through road for it (own_names); any other ribbon is
    main = next(rb for rb in ctx.ribbons if rb.name == "MAINLINE")
    assert ctx.own_names(main) == {"MAINLINE"}


def test_a_ray_down_another_road_is_a_through_road():
    """M3-rev at J1: Navajo westbound runs 16 m across the Waring opening before leaving pavement — the rule's own
    skip (THROUGH_ROAD_M), so the arrow never points away from a road a Free Roam driver may take; a pad deck, a
    declared stub and the north ribbon's own pieces never count"""
    import types
    main = _ribbon("MAINLINE", [(float(i), 0.0, 0.0) for i in range(0, 101, 2)])
    # a 10 m wide street crossing the ray's path obliquely just past the mainline's end: ~14 m of its pavement on the ray
    cross = _ribbon("side", [(100.0 + 4.0 * k, 0.0, -8.0 + 2.0 * k) for k in range(0, 9)])
    stub = _ribbon("STUB_x", [(140.0 + 2.0 * k, 0.0, 0.0) for k in range(0, 12)])
    ctx = types.SimpleNamespace(field=ps.PavementField([main, cross, stub]), own_names=lambda rb: {rb.name})
    ctx.field.add_polygon("pad J9", [(170.0, -10.0), (200.0, -10.0), (200.0, 10.0), (170.0, 10.0)])
    m = ps.march(ctx, main, (90.0, 0.0), (1.0, 0.0), 1.33)
    assert m is not None and m["through"].get("side", 0.0) >= ps.THROUGH_ROAD_M, m
    assert "STUB_x" not in m["through"] and not any(k.startswith("pad ") for k in m["through"]), m["through"]
    # the MAINLINE alone (a layout plate's field): nothing is a through road, the ray leaves at the mainline's end
    m2 = ps.march(ctx, main, (90.0, 0.0), (1.0, 0.0), 1.48, only=("MAINLINE",))
    assert m2["through"] == {} and 10.0 <= m2["s_C"] <= 16.0 and m2.get("S") is not None     # past the mainline's end (+ its round cap)
    assert abs(m2["s_S"] - m2["s_C"] - 1.48) < 0.3
    # with the street as the ribbon's own (the north ribbon's pieces) it is not a through road either
    ctx.own_names = lambda rb: {rb.name, "side"}
    assert ps.march(ctx, main, (90.0, 0.0), (1.0, 0.0), 1.33)["through"] == {}
    assert ps.THROUGH_ROAD_M == 8.0 and ps.SIDE_STEP_MAX_M == 2.5 and ps.WALL_CLEAR_M == 0.5


def test_per_layout_is_validated_at_load():
    for bad, msg in (({"M1": {"ribbon": "MAINLINE", "vertex": 0, "per_layout": "yes"}}, "true|false"),
                     ({"X": {"ribbon": "medium#2+0#0#0", "vertex": 0, "per_layout": True}}, "only a MAINLINE corner"),
                     ({"M1": {"ribbon": "MAINLINE", "vertex": 0, "per_layout": True, "skip": True, "reason": "r"}}, "per_layout and skip")):
        try:
            ps.validate_overrides({}, bad)
        except ps.SignsConfigError as e:
            assert msg in str(e), str(e)
        else:
            raise AssertionError(msg)
    ps.validate_overrides({}, {"M1": {"ribbon": "MAINLINE", "vertex": 0, "per_layout": True}})
    assert "per_layout" in ps.CORNER_KEYS


def test_layout_coverage_and_spacing_rules():
    rec = lambda cid, d, lay=None: {"id": cid, "ribbon": "MAINLINE", "direction": d, "layout": lay, "base_xz": [0.0, 0.0],
                                    "corner": {"second_arrow": False}}
    driven = {"fwd": ["street", "race_cw"], "rev": ["race_acw"]}
    # a plate for race_cw only + the shared rule skip: street covered by the skip, race_acw by its own plate
    d = {"signs": [rec("M3-fwd@race_cw", "fwd", "race_cw"), rec("M3-rev@race_acw", "rev", "race_acw")],
         "skipped": [{"id": "M3-fwd", "ribbon": "MAINLINE", "reasons": ["ray never leaves pavement within 80 m (through leg / junction)"]}]}
    f, rows = vs.layout_coverage(d, driven, None)
    assert f == [] and any("(m) layout street: M3 skipped" in r for r in rows), (f, rows)
    # no shared skip: street has nothing, and the fail names the other layout's plate
    d2 = {"signs": d["signs"], "skipped": []}
    f2, _ = vs.layout_coverage(d2, driven, None)
    assert len(f2) == 1 and "layout street (fwd)" in f2[0] and "M3-fwd@race_cw" in f2[0], f2
    # a skip that is a placement failure is not coverage
    d3 = {"signs": d["signs"], "skipped": [{"id": "M3-fwd", "ribbon": "MAINLINE", "reasons": ["sign base is ON pavement (edge clearance -1.00)"]}]}
    f3, _ = vs.layout_coverage(d3, driven, None)
    assert len(f3) == 1 and "not the rule's own" in f3[0], f3
    # a layout's own skip covers that layout alone
    d4 = {"signs": [rec("M3-rev@race_acw", "rev", "race_acw")],
          "skipped": [{"id": "M3-fwd@race_cw", "ribbon": "MAINLINE", "layout": "race_cw", "reasons": ["R_apex 42.0 > 30 m"]}]}
    f4, _ = vs.layout_coverage(d4, driven, None)
    assert len(f4) == 1 and "layout street (fwd)" in f4[0], f4
    # (i) spacing: two layouts' own plates may share a spot; a shared plate and a layout plate may not
    assert vs.split_layout("M3-fwd") == ("M3-fwd", None)


def test_stitch_strings_pieces_through_a_pad_on_a_cubic():
    a = [(0.0, 0.0, float(z)) for z in range(0, 31, 3)]                 # north along z to (0, 30)
    b = [(float(x), 0.0, 60.0) for x in range(30, 61, 3)]              # east along x from (30, 60)
    P, W, parts = el.stitch([("A", a, [20.0] * len(a)), ("B", b, [30.0] * len(b))])
    assert parts[:len(a)] == ["A"] * len(a) and parts[-len(b):] == ["B"] * len(b)
    n_pad = parts.count("pad")
    assert n_pad >= 3 and len(P) == len(a) + len(b) + n_pad
    pad = P[len(a):len(a) + n_pad]
    assert all(0.0 < q[0] < 30.0 and 30.0 < q[2] < 60.0 for q in pad), pad       # the turn stays between the arms
    assert all(20.0 < w < 30.0 for w in W[len(a):len(a) + n_pad])                # widths eased between theirs
    assert el.NORTH_RIBBON == "north" and ps.RIBBON_PREFIX["north"] == "N"
    assert el.compute_lines(tempfile.mkdtemp()) is None and el.centre_ribbon(tempfile.mkdtemp()) is None   # no north route: nothing
    assert el.pad_polygons(tempfile.mkdtemp()) == [] and el.pad_stub_reach_m(tempfile.mkdtemp()) == 0.0


# --- the map ---------------------------------------------------------------------------------------------------------
def _map_project(tmp, race_map="lap"):
    d = Path(tmp)
    (d / "data").mkdir(parents=True, exist_ok=True)
    layouts = [{"id": "street", "direction": "forward"},
               {"id": "race_cw", "direction": "forward", "race_furniture": True, **({"map": race_map} if race_map else {})}]
    (d / "track.config.json").write_text(json.dumps({"slug": "sq", "layouts": layouts}))
    sq = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [100.0, 0.0, 100.0], [0.0, 0.0, 100.0], [0.0, 0.0, 0.0]]
    (d / "data" / "finished_centerline.json").write_text(json.dumps({"points_xyz_m": sq}))
    (d / "data" / "connectors.local.json").write_text(json.dumps({"connectors": [{"name": "north_x", "points_xyz_m": [[50.0, 0.0, 100.0], [50.0, 0.0, 400.0]], "widths_m": [10.0, 10.0]}]}))
    out = d / "build" / "sq"
    for lid in ("street", "race_cw"):
        (out / "ui" / lid).mkdir(parents=True, exist_ok=True)
        (out / f"models_{lid}.ini").write_text("x")
    return d, out


def _ini(p):
    return {ln.split("=")[0]: float(ln.split("=")[1]) for ln in p.read_text().splitlines() if "=" in ln and ln.split("=")[0] in ("SCALE_FACTOR", "X_OFFSET", "Z_OFFSET")}


def test_make_map_draws_a_lap_layout_alone_and_the_network_elsewhere():
    d, out = _map_project(tempfile.mkdtemp())
    written = mm.build(d)
    assert sorted(p.name for p in written) == ["race_cw", "sq", "street"]
    root, street, race = (_ini(out / "data" / "map.ini"), _ini(out / "street" / "data" / "map.ini"), _ini(out / "race_cw" / "data" / "map.ini"))
    assert root == street                                   # the root and Free Roam: the whole network
    assert race["SCALE_FACTOR"] < street["SCALE_FACTOR"]    # the lap alone fills the canvas: fewer metres per pixel
    # the network spans z -400 .. 100 in the kn5 frame (the connector mirrored), the lap 100 m
    assert abs(street["SCALE_FACTOR"] - 500.0 / (mm.W - 2 * mm.MARGIN)) < 1e-6 and abs(race["SCALE_FACTOR"] - 100.0 / (mm.W - 2 * mm.MARGIN)) < 1e-6
    for lid in ("street", "race_cw"):
        assert (out / "ui" / lid / "outline.png").exists() and (out / lid / "map.png").exists()
    assert (out / "ui" / "street" / "outline.png").read_bytes() != (out / "ui" / "race_cw" / "outline.png").read_bytes()
    # no key = the network everywhere (byte-identical maps, as before P4)
    d2, out2 = _map_project(tempfile.mkdtemp(), race_map=None)
    mm.build(d2)
    assert (out2 / "race_cw" / "map.png").read_bytes() == (out2 / "street" / "map.png").read_bytes()
    assert mm.layout_scopes({"layouts": [{"id": "a"}, {"id": "b", "map": "lap"}]}) == {"a": "network", "b": "lap"}
    try:
        mm.layout_scopes({"layouts": [{"id": "a", "map": "everything"}]})
    except ValueError as e:
        assert "everything" in str(e)
    else:
        raise AssertionError("an unknown map scope must be refused")
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert mm.layout_scopes(cfg) == {"street": "network", "race_cw": "lap", "race_acw": "lap"}


# --- the chain -------------------------------------------------------------------------------------------------------
def test_signs_step_runs_after_the_race_furniture_in_every_chain():
    sd = (ROOT / "tools" / "ship_sd.sh").read_text(encoding="utf-8")
    tr = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    spec = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "ship.json").read_text(encoding="utf-8"))
    header = 'step "author: W1-6 large-arrow signs at every tight corner (SIGNPLATE + SIGNARROW + SIGNPOST; the race layouts\' own plates into RACE_CLOSE_<TOKEN>)"'
    assert sd.count("tools/author_signs_blend.py") == 1 and sd.count(header) == 1
    i_sign = sd.index("tools/author_signs_blend.py")
    # ledger 0054 Phase 2 step 2g: after the furniture, BEFORE verify_race (its scenery check G reads this run's
    # data/signs.local.json — after it, a re-used workshop judged the last run's plates)
    assert sd.index("tools/author_race_furniture_blend.py") < i_sign < sd.index("tools/verify_race.py") \
        < sd.index("tools/plot_race_furniture.py") < sd.index("scripts/ac/build_kn5_loop.py")
    assert i_sign > sd.index('if [ "$SKIP_BLEND" = 0 ]; then') and sd.index("tools/verify_signs.py") > i_sign and sd.index("tools/plot_signs.py") > i_sign
    au = spec["steps"]["author"]
    assert "signs" not in spec["steps"]["draft"] and au[-3:] == ["race_author", "signs", "race_verify"]
    assert '*" race_verify "*" signs "*)' in tr                  # the chain refuses the old order
    assert "author_signs() {" in tr and "draft_signs() {" not in tr and tr.count(header) == 1
    # the map step says what a lap layout gets
    assert 'map = lap gets its lap alone' in sd and 'map = lap gets its lap alone' in tr
    # signs.json: M3 / M4 are per_layout, not skipped; J2 / J3 / J4 name the north ribbon
    sj = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "signs.json").read_text(encoding="utf-8"))["corners"]
    for cid in ("M3", "M4"):
        assert sj[cid].get("per_layout") is True and not sj[cid].get("skip")
    for cid in ("J2", "J3", "J4"):
        assert sj[cid]["ribbon"] == "north" and sj[cid]["expect_arrow"] == "right"

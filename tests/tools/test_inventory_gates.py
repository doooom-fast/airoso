"""The surveyed inventory, paint from it, and the three inventory gates (Denver Grand Prix PLAN 4b items 10, 11;
ledger 0096): tools/inventory.py, tools/inventory_gate.py, the prep's paint rule.

Fixtures: the survey pilot's own files (tracks/denver-grand-prix/source/survey/pilot: 385 m of Colfax, 308 paint
marks, the posts read at Colfax / Sherman). The "built track" is a kn5 written by scripts/ac/kn5_write.py from
meshes laid where the inventory says (tools/paint_shapes.drape on a flat road, posts as boxes), then spoiled one way
per test; every gate reads that kn5 FILE (LAWS L5), never the meshes it was written from.

Plain ``test_*`` for tests/run_tests.py.
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import inventory as INV  # noqa: E402
import inventory_gate as IG  # noqa: E402
import paint_shapes  # noqa: E402

from tests.geometry.test_drive_test import _write_obj  # noqa: E402

from scripts.ac import build_kn5_loop as bk  # noqa: E402
from scripts.ac.kn5_write import build as write_kn5  # noqa: E402
from scripts.ac.verify_kn5 import _parse_full  # noqa: E402

PILOT = ROOT / "tracks" / "denver-grand-prix" / "source" / "survey" / "pilot"
PAINT = json.loads((PILOT / "paint.json").read_text(encoding="utf-8"))
POLES = json.loads((PILOT / "poles.json").read_text(encoding="utf-8"))
ORIGIN = {"lon": PAINT["georeference"]["origin_lonlat"][0], "lat": PAINT["georeference"]["origin_lonlat"][1]}
SNAPSHOT_PREP = (ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac"
                 / "build_kn5_loop.py")


# --- the world -------------------------------------------------------------------------------------------------
def _kn5(p):
    """local (east, up, north) -> the kn5 frame the chain ships (east, up, -north)"""
    return (p[0], p[1], -p[2])


def _box(v, t, x0, x1, y0, y1, n0, n1):
    b = len(v)
    for y in (y0, y1):
        for n in (n0, n1):
            for x in (x0, x1):
                v.append(_kn5((x, y, n)))
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        a, b2, c, d = (b + k for k in q)
        t.extend([(a, b2, c), (a, c, d)])


def _mesh(v, t):
    return {"vertices": v, "tris": t, "uvs": [(0.0, 0.0)] * len(v)}


def _paint_groups(inv, spoil=None):
    """the inventory's built-grade items draped on a flat road at y = 0, as the author step drapes them"""
    out = {}
    for it in inv.built():
        strokes = it.strokes if spoil is None else spoil(it)
        if not strokes:
            continue
        colour = strokes[0].get("color", it.colour)
        verts, faces, _made, _clipped = paint_shapes.drape([{**s, "color": colour} for s in strokes],
                                                           lambda x, z: 0.0, 0.5, 0.015, clip=True)
        m = out.setdefault(colour, ([], []))
        b = len(m[0])
        m[0].extend(_kn5((x, y, z)) for x, z, y in verts)           # the drape's (x, north, up)
        for q in faces:
            a, b2, c, d = (b + i for i in q)
            m[1].extend([(a, b2, c), (a, c, d)])
    return [(INV.INVENTORY_PAINT[c] + "000", _mesh(*m)) for c, m in out.items()]


def _post(x, n, h=7.0, arm_deg=None, arm_m=8.0):
    """a mast (a 0.3 m box, h tall) and, with a bearing, an arm from its top reaching arm_m that way, as ten short
    boxes: two shells that only touch"""
    v, t = [], []
    _box(v, t, x - 0.15, x + 0.15, 0.0, h, n - 0.15, n + 0.15)
    if arm_deg is not None:
        e, nn = math.sin(math.radians(arm_deg)), math.cos(math.radians(arm_deg))
        for k in range(10):
            cx, cn = x + e * arm_m * (k + 0.5) / 10.0, n + nn * arm_m * (k + 0.5) / 10.0
            r = arm_m / 20.0 + 0.02
            _box(v, t, cx - max(abs(e) * r, 0.08), cx + max(abs(e) * r, 0.08), h - 0.4, h - 0.2,
                 cn - max(abs(nn) * r, 0.08), cn + max(abs(nn) * r, 0.08))
    return v, t


def _plate(x, n, facing_deg, w=0.75, h=0.75, y0=2.1):
    """one sign plate (two triangles) whose FRONT looks along the compass bearing. Front is decided where AC decides
    it, in the kn5 frame: the triangle's own cross product there (the rule verify_kn5 counts a road's up-faces by)."""
    e, nn = math.sin(math.radians(facing_deg)), math.cos(math.radians(facing_deg))
    te, tn = nn, -e                                              # along the plate, in plan
    c = [(x - te * w / 2, y0, n - tn * w / 2), (x + te * w / 2, y0, n + tn * w / 2),
         (x + te * w / 2, y0 + h, n + tn * w / 2), (x - te * w / 2, y0 + h, n - tn * w / 2)]
    k = [_kn5(p) for p in c]
    tris = [(0, 1, 2), (0, 2, 3)]
    a, b, cc = k[0], k[1], k[2]
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = cc[0] - a[0], cc[1] - a[1], cc[2] - a[2]
    front_e, front_n = uy * vz - uz * vy, -(ux * vy - uy * vx)   # kn5 normal (x, ., z) -> plan (east, north = -z)
    if front_e * e + front_n * nn < 0:
        tris = [(0, 2, 1), (0, 3, 2)]
    return k, tris


def _join(parts):
    v, t = [], []
    for pv, pt in parts:
        b = len(v)
        v.extend(pv)
        t.extend((a + b, b2 + b, c + b) for a, b2, c in pt)
    return _mesh(v, t)


LAP = [(float(x), 0.0, 0.0) for x in range(240, -131, -5)]      # Colfax, east to west, as the car faces
JUNCTIONS = {"junctions": [{"id": "Colfax / Sherman", "xz": [0.0, 0.0]}]}


def _project(inventory_cfg, groups, files=None, lap=LAP, junctions=JUNCTIONS) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "source").mkdir()
    for name, doc in (files or {}).items():
        (d / "source" / name).write_text(json.dumps(doc), encoding="utf-8")
    inv = copy.deepcopy(inventory_cfg)
    if junctions is not None:
        (d / "source" / "junctions.json").write_text(json.dumps(junctions), encoding="utf-8")
        inv["junctions"] = "source/junctions.json"
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False, "inventory": inv}))
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in lap], "widths_m": [16.0] * len(lap), "origin": ORIGIN}))
    _write_obj(d / "data" / "track.obj", groups or [("1ROAD_main", _mesh([(0, 0, 0), (1, 0, 0), (0, 0, 1)], [(0, 1, 2)]))])
    with contextlib.redirect_stdout(io.StringIO()):
        write_kn5(d)
    return d


def _gate(d, **kw):
    return IG.check(d, **kw)


PAINT_CFG = {"paint": {"file": "source/paint.json", "gate": True, "build_grades": ["measured"]}}


def _paint_inv(doc=PAINT, ccfg=None):
    return INV.read(doc, "paint", ORIGIN, PAINT_CFG["paint"] if ccfg is None else ccfg)


# --- the pilot's schema, as read ---------------------------------------------------------------------------------
def test_the_pilot_paint_file_reads_as_it_reports_itself():
    inv = INV.read(PAINT, "paint", ORIGIN)
    assert len(inv.items) == 308 == sum(PAINT["counts"].values())
    g = inv.grade_shares()
    assert (g["measured"], g["detected"], g["tagged"]) == (PAINT["grades"]["measured"], PAINT["grades"]["detected"], 0)
    assert abs(g["measured_share"] - 125 / 308) < 1e-3
    # the frame: every mark lies in the box the pilot says it photographed (metres about its origin), within 2 m
    x0, z0, x1, z1 = PAINT["source_image"]["frame_box_m_x0_y0_x1_y1"]
    pts = [p for it in inv.items for p in it.points()]
    assert x0 - 2 <= min(p[0] for p in pts) and max(p[0] for p in pts) <= x1 + 2
    assert z0 - 2 <= min(p[1] for p in pts) and max(p[1] for p in pts) <= z1 + 2
    # only an untyped symbol cannot be built as read
    assert {it.raw["class"] for it in inv.items if not it.built} == {"symbol"}
    assert sum(1 for it in inv.items if not it.built) == PAINT["counts"]["symbol"] == 55


def test_each_paint_class_becomes_its_own_stripes():
    inv = INV.read(PAINT, "paint", ORIGIN)
    by = {}
    for it in inv.items:
        by.setdefault((it.raw["class"], it.raw.get("pattern")), it)
    cw = by[("crosswalk", None)]
    assert len(cw.strokes) == cw.raw["bars"] and all(s["w"] == cw.raw["bar_width_m"] for s in cw.strokes)
    assert abs(INV.polyline_length(cw.strokes[0]["pts"]) - cw.raw["bar_length_m"]) < 0.25
    br = by[("line", "broken")]
    assert len(br.strokes) == br.raw["dashes"] and "double_gap_m" not in br.strokes[0]
    dy = by[("line", "double solid")]
    (st,) = dy.strokes
    w = dy.raw["width_m"]
    assert abs(st["w"] - w / 3) < 1e-9 and abs(st["double_gap_m"] - w / 3) < 1e-9       # two lines inside what was read
    (a, wa), (b, wb) = INV.stripe_axes(st)
    assert abs(math.dist(a[0], b[0]) - 2 * w / 3) < 1e-6 and wa == wb
    # a fragment the reader kept as a centre, a length and a bearing is the same mark end to end
    one = next(it for it in inv.items if len(it.raw.get("line_lonlat") or []) == 1)
    (st,) = one.strokes
    assert abs(INV.polyline_length(st["pts"]) - one.raw["length_m"]) < 1e-6
    e, n = st["pts"][1][0] - st["pts"][0][0], st["pts"][1][1] - st["pts"][0][1]
    assert INV.angle_diff(INV.bearing_deg(e, n), one.raw["bearing_deg"]) < 1e-6


def test_the_pilot_posts_read_by_class_and_the_unread_are_not_items():
    sig = INV.read(POLES, "signals", ORIGIN)
    lam = INV.read(POLES, "lamps", ORIGIN)
    assert sorted(it.type for it in sig.items) == ["mast_arm", "mast_arm", "mast_arm", "pedestal_or_post"]
    assert sorted(it.facing_deg for it in sig.items if it.facing_deg is not None) == [0.0, 180.0]
    assert [it.type for it in lam.items].count("pedestrian_globe") == 3
    assert all(it.grade == "measured" for it in sig.items + lam.items)
    # the shadow reader's unread candidates and the ones rejected by eye are in the file and are not inventory items
    assert sig.not_items["grade 'rejected by eye'"] == 9 and sig.not_items["a post with no class read"] > 180
    # the pilot's signs.json holds junction records with no post position: nothing to build, nothing to compare
    signs = INV.read(json.loads((PILOT / "signs.json").read_text()), "signs", ORIGIN)
    assert signs.items == [] and signs.not_items == {"a junction record with no position": 4}


def test_type_names_and_tolerances():
    assert INV.type_prefix({}, "signals", "mast_arm") == "SIGNAL_MAST_ARM"
    assert INV.type_prefix({}, "signs", "R1-1") == "SIGNFACE_R1_1"
    assert INV.type_prefix({"types": {"led_cobra": "LIGHTPOST"}}, "lamps", "led_cobra") == "LIGHTPOST"
    assert INV.tolerances({}, "paint")["measured"] == 0.30 and INV.tolerances({}, "lamps")["tagged"] == 15.0
    assert INV.tolerances({"tolerance_m": {"measured": 0.2}}, "paint") == {"measured": 0.2, "detected": 0.6, "tagged": 3.0}
    try:
        INV.build_grades({"build_grades": ["invented"]})
    except INV.InventoryError:
        pass
    else:
        raise AssertionError("an invented grade was accepted")


# --- opt-in ------------------------------------------------------------------------------------------------------
def test_a_track_with_no_inventory_is_not_judged_and_no_kn5_is_opened():
    d = Path(tempfile.mkdtemp())
    (d / "track.config.json").write_text(json.dumps({"slug": "t"}))          # no build/, no data/: nothing may be read
    assert IG.check(d) == {"fail": False, "opted_in": False, "classes": {}}
    with contextlib.redirect_stdout(io.StringIO()) as out:
        assert IG.main([str(d)]) == 0
    assert "not opted in" in out.getvalue()
    # a file with no "gate": true authors from the inventory and gates nothing
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "inventory": {"paint": {"file": "x.json"}}}))
    assert IG.check(d)["opted_in"] is False


def test_inventory_and_covered_road_stay_opt_in_outside_denver():
    """The Denver rollout must leave the existing tracks' chain untouched."""
    tracks = ROOT / "tracks"
    denver = tracks / "denver-grand-prix"
    for cfg in sorted(tracks.glob("*/track.config.json")):
        c = json.loads(cfg.read_text(encoding="utf-8"))
        if cfg.parent == denver:
            continue
        assert "inventory" not in c, cfg
        assert not ((c.get("capture") or {}).get("covered_spans")), cfg
    for spec in sorted(tracks.glob("*/ship.json")):
        steps = json.loads(spec.read_text(encoding="utf-8")).get("steps") or {}
        if spec.parent == denver:
            continue
        assert "paint_inventory" not in (steps.get("author") or []) and "inventory" not in (steps.get("gate") or []), spec


def test_denver_wires_any_declared_inventory_and_covered_road_to_the_shipping_gates():
    denver = ROOT / "tracks" / "denver-grand-prix"
    cfg_path = denver / "track.config.json"
    if not cfg_path.is_file():
        return
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    spec = json.loads((denver / "ship.json").read_text(encoding="utf-8"))
    gates = set(spec["steps"]["gate"])
    if INV.gated_classes(cfg):
        assert "inventory" in gates
    if (cfg.get("capture") or {}).get("covered_spans"):
        assert {"drive_test_street", "kn5_ground"} <= gates


def test_a_mirrored_or_yawed_track_is_refused():
    d = _project(PAINT_CFG, _paint_groups(_paint_inv()), {"paint.json": PAINT})
    cfg = json.loads((d / "track.config.json").read_text())
    (d / "track.config.json").write_text(json.dumps({**cfg, "true_north_rotation_deg": 180}))
    try:
        IG.check(d)
    except INV.InventoryError as e:
        assert "frame" in str(e)
    else:
        raise AssertionError("a yawed track was judged")
    assert IG.main([str(d)]) == 2


# --- paint ---------------------------------------------------------------------------------------------------
def test_paint_built_from_the_inventory_passes_all_three_gates_and_states_the_shares():
    d = _project(PAINT_CFG, _paint_groups(_paint_inv()), {"paint.json": PAINT})
    res = _gate(d)
    r = res["classes"]["paint"]
    assert res["fail"] is False and res["kn5"] == ["t.kn5"], json.dumps(r)[:600]
    assert r["present"]["judged"] == 125 and r["present"]["missing"] == 0
    assert r["nothing_extra"]["extra_area_m2"] == 0.0
    assert r["covered"]["uncovered_m"] == 0 and r["covered"]["uncovered_junctions"] == []
    assert (r["grades"]["measured"], r["grades"]["detected"], r["grades"]["tagged"]) == (125, 183, 0)
    assert r["held_out"]["its shape was not read (an untyped symbol)"] == 55
    with contextlib.redirect_stdout(io.StringIO()) as out:
        assert IG.main([str(d), "--json", str(d / "data" / "inventory_gate.json")]) == 0
    assert "measured 125 (40.6 %)" in out.getvalue() and "detected 183 (59.4 %)" in out.getvalue()
    assert json.loads((d / "data" / "inventory_gate.json").read_text())["fail"] is False


def test_present_names_the_item_that_was_not_painted():
    inv = _paint_inv()
    gone = next(it.id for it in inv.built() if it.raw["class"] == "crosswalk")
    d = _project(PAINT_CFG, _paint_groups(inv, lambda it: [] if it.id == gone else it.strokes), {"paint.json": PAINT})
    r = _gate(d)["classes"]["paint"]
    assert r["present"]["fail"] is True and [m["id"] for m in r["present"]["missing_rows"]] == [gone]
    assert r["nothing_extra"]["fail"] is False
    assert IG.main([str(d)]) == 1


def test_present_holds_measured_paint_to_its_tolerance():
    """every mark moved 0.2 m north still passes (measured: 0.30 m); moved 1.0 m, the lines that run east-west are
    no longer where they were read, and the paint now lying beside them is extra"""
    def moved(dn):
        return lambda it: [{**s, "pts": [(x, z + dn) for x, z in s["pts"]]} for s in it.strokes]
    inv = _paint_inv()
    near = _gate(_project(PAINT_CFG, _paint_groups(inv, moved(0.2)), {"paint.json": PAINT}))["classes"]["paint"]
    assert near["present"]["fail"] is False and near["nothing_extra"]["fail"] is False
    far = _gate(_project(PAINT_CFG, _paint_groups(inv, moved(1.0)), {"paint.json": PAINT}))["classes"]["paint"]
    assert far["present"]["fail"] is True and far["present"]["missing"] > 20
    assert far["nothing_extra"]["fail"] is True


def test_the_wrong_colour_is_the_wrong_type():
    inv = _paint_inv()
    yellow = next(it.id for it in inv.built() if it.colour == "yellow" and it.raw.get("pattern") == "double solid")
    d = _project(PAINT_CFG, _paint_groups(inv, lambda it: [{**s, "color": "white"} for s in it.strokes]
                                          if it.id == yellow else it.strokes), {"paint.json": PAINT})
    r = _gate(d)["classes"]["paint"]
    assert [(w["id"], w["built_as"]) for w in r["present"]["wrong_type_rows"]] == [(yellow, "white")]
    assert r["nothing_extra"]["fail"] is True                 # and the white paint lying there is on no white item


def test_a_broken_line_built_solid_is_extra_paint():
    inv = _paint_inv()
    broken = max((it for it in inv.built() if it.raw.get("pattern") == "broken"),
                 key=lambda it: it.raw["gap_m"] * (it.raw["dashes"] - 1))          # a lane line: 3 m dashes, 9 m gaps

    def solid(it):
        if it.id != broken.id:
            return it.strokes
        ends = [q for st in it.strokes for q in st["pts"]]           # the dashes are not stored in order along the line
        a, b = max(((p, q) for p in ends for q in ends), key=lambda pq: math.dist(*pq))
        return [{"pts": [a, b], "w": it.strokes[0]["w"]}]
    r = _gate(_project(PAINT_CFG, _paint_groups(inv, solid), {"paint.json": PAINT}))["classes"]["paint"]
    assert r["nothing_extra"]["fail"] is True and r["nothing_extra"]["extra_area_m2"] > 5.0


def test_paint_by_width_is_extra_and_a_declared_addition_is_not():
    """the assembler's own lines beside the inventory's: an edge line the survey did not read"""
    v, t = [], []
    _box(v, t, -120.0, 230.0, 0.014, 0.015, 30.0, 30.12)             # a 350 m white line by rule, north of the road
    groups = _paint_groups(_paint_inv()) + [("MARKINGS", _mesh(v, t))]
    r = _gate(_project(PAINT_CFG, groups, {"paint.json": PAINT}))["classes"]["paint"]
    assert r["present"]["fail"] is False and r["nothing_extra"]["fail"] is True
    assert r["nothing_extra"]["rows"][0]["mesh"] == "MARKINGS" and r["nothing_extra"]["extra_area_m2"] > 40.0
    # the same line under a name the track declares as an addition (a start line, a grid): not looked at
    groups = _paint_groups(_paint_inv()) + [("MARKINGS_paint_grid", _mesh(v, t))]
    cfg = {"paint": {**PAINT_CFG["paint"], "keep_prefixes": ["MARKINGS_paint_grid"]}}
    assert _gate(_project(cfg, groups, {"paint.json": PAINT}))["classes"]["paint"]["nothing_extra"]["fail"] is False


def test_an_untyped_symbol_in_a_built_grade_cannot_pass():
    cfg = {"paint": {"file": "source/paint.json", "gate": True}}                 # every grade built
    inv = _paint_inv(ccfg=cfg["paint"])
    assert len(INV.unbuildable(inv, INV.GRADES)) == 55
    r = _gate(_project(cfg, _paint_groups(inv), {"paint.json": PAINT}))["classes"]["paint"]
    assert r["present"]["fail"] is True and r["present"]["unbuildable"] == 55 and r["present"]["missing"] == 0


def test_covered_silence_is_not_a_pass_and_a_declared_none_is():
    """the lap run 150 m past the photographed box: no record there, so not covered, until the survey says none"""
    lap = [(float(x), 0.0, 0.0) for x in range(240, -281, -5)]
    groups = _paint_groups(_paint_inv())
    r = _gate(_project(PAINT_CFG, groups, {"paint.json": PAINT}, lap=lap))["classes"]["paint"]
    assert r["covered"]["fail"] is True and r["present"]["fail"] is False
    ((a, b),) = r["covered"]["uncovered_stretches"]
    assert 370 < a < 400 and b == 520.0 and r["covered"]["uncovered_m"] == b - a + 1
    doc = {**PAINT, "items": PAINT["items"] + [{"none": True, "lap_m": [a, b]}]}
    r = _gate(_project(PAINT_CFG, groups, {"paint.json": doc}, lap=lap))["classes"]["paint"]
    assert r["covered"]["fail"] is False and r["covered"]["none_stretches"] == 1 and r["none_records"] == 1
    # "none" over a stretch the same file holds marks in is a contradiction, not a cover
    doc = {**PAINT, "items": PAINT["items"] + [{"none": True, "lap_m": [100.0, 520.0]}]}
    r = _gate(_project(PAINT_CFG, groups, {"paint.json": doc}, lap=lap))["classes"]["paint"]
    assert r["covered"]["fail"] is True and len(r["covered"]["contradictions"]) > 10


def test_covered_asks_every_junction():
    groups = _paint_groups(_paint_inv())
    files = {"paint.json": PAINT}
    two = {"junctions": JUNCTIONS["junctions"] + [{"id": "Colfax / Elsewhere", "xz": [0.0, 400.0]}]}
    r = _gate(_project(PAINT_CFG, groups, files, junctions=two))["classes"]["paint"]
    assert r["covered"]["fail"] is True and r["covered"]["uncovered_junctions"] == ["Colfax / Elsewhere"]
    doc = {**PAINT, "none": [{"junction": "Colfax / Elsewhere"}]}
    r = _gate(_project(PAINT_CFG, groups, {"paint.json": doc}, junctions=two))["classes"]["paint"]
    assert r["covered"]["fail"] is False and r["covered"]["none_junctions"] == 1
    # a track that declares no junction list has not shown its junctions are covered
    r = _gate(_project(PAINT_CFG, groups, files, junctions=None))["classes"]["paint"]
    assert r["covered"]["fail"] is True and r["covered"]["junctions"] is None


def test_a_closed_lap_counts_its_seam_once():
    """LAWS L13: closed is derived from the repeated first point, and a none stretch may wrap through the seam"""
    sq = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0), (0.0, 0.0)]
    lap = INV.Lap(sq)
    assert lap.closed and lap.length == 400.0 and not INV.Lap(sq[:-1]).closed
    assert lap.in_span(395.0, [380.0, 20.0]) and lap.in_span(5.0, [380.0, 20.0]) and not lap.in_span(200.0, [380.0, 20.0])
    inv = INV.Inventory("lamps")
    inv.nones.append({"lap_m": [380.0, 20.0]})
    cov = INV.coverage(inv, lap, [], reach_m=10.0)
    assert cov["uncovered_stretches"] == [[21.0, 379.0]] and cov["uncovered_m"] == 359.0


# --- posts: signals and lamps off the pilot, signs off a file written here ------------------------------------------
POST_CFG = {"signals": {"file": "source/poles.json", "gate": True}, "lamps": {"file": "source/poles.json", "gate": True}}


def _post_groups(spoil=None):
    """every pilot signal and lamp as a post where it was read, one mesh per type (so one mesh holds several posts)"""
    by = {}
    for cls in ("signals", "lamps"):
        for it in INV.read(POLES, cls, ORIGIN).items:
            row = {"cls": cls, "id": it.id, "name": INV.type_prefix({}, cls, it.type) + "_0", "x": it.xz[0], "n": it.xz[1],
                   "arm": it.facing_deg, "h": 7.0 if cls == "signals" else 4.0}
            row = row if spoil is None else spoil(row)
            if row is not None:
                by.setdefault(row["name"], []).append(_post(row["x"], row["n"], row["h"], row["arm"]))
    return [(name, _join(parts)) for name, parts in by.items()]


def _posts(spoil=None, extra=()):
    d = _project(POST_CFG, _post_groups(spoil) + list(extra), {"poles.json": POLES})
    return _gate(d)["classes"]


def test_posts_built_where_they_were_read_are_present_and_nothing_is_extra():
    r = _posts()
    for cls, n in (("signals", 4), ("lamps", 4)):
        assert r[cls]["present"]["fail"] is False and r[cls]["present"]["judged"] == n, r[cls]["present"]
        assert r[cls]["built"]["objects"] == n and r[cls]["nothing_extra"]["fail"] is False
        assert r[cls]["grades"]["measured_share"] == 1.0
    # the two masts whose arm the pilot read are judged for facing; the others say they were not
    assert r["signals"]["present"]["facing_not_given"] == 2 and r["lamps"]["present"]["facing_not_given"] == 4
    # four posts at one junction do not cover 370 m of lap: every stretch out of their reach is listed
    assert r["signals"]["covered"]["fail"] is True and r["signals"]["covered"]["uncovered_m"] > 200


def test_a_mast_and_its_arm_are_one_object():
    v, t = _post(0.0, 0.0, 7.0, 90.0, arm_m=10.0)
    (one,) = IG.shapes([("SIGNAL_MAST_ARM_0", [(p[0], p[1], -p[2]) for p in v], [i for tri in t for i in tri])])
    assert math.dist(one.foot(), (0.0, 0.0)) < 0.01 and abs(one.height() - 7.0) < 1e-6
    assert INV.angle_diff(one.arm_bearing(), 90.0) < 1.0
    # two posts 3 m apart stay two
    a, b = _post(0.0, 0.0), _post(3.0, 0.0)
    m = _join([a, b])
    assert len(IG.shapes([("LIGHTPOST_X", [(p[0], p[1], -p[2]) for p in m["vertices"]],
                           [i for tri in m["tris"] for i in tri])])) == 2


def test_present_fails_a_missing_post_a_moved_post_a_wrong_type_and_an_arm_the_wrong_way():
    armed = next(it.id for it in INV.read(POLES, "signals", ORIGIN).items if it.facing_deg == 180.0)
    r = _posts(lambda row: None if row["id"] == armed else row)["signals"]
    assert [m["id"] for m in r["present"]["missing_rows"]] == [armed] and r["nothing_extra"]["fail"] is False
    # 0.4 m off: inside the measured tolerance (0.5 m); 0.8 m off: the post is missing AND the one built is extra
    r = _posts(lambda row: {**row, "x": row["x"] + 0.4} if row["id"] == armed else row)["signals"]
    assert r["present"]["fail"] is False and r["present"]["worst_off_m"] == 0.4
    r = _posts(lambda row: {**row, "x": row["x"] + 0.8} if row["id"] == armed else row)["signals"]
    assert r["present"]["missing"] == 1 and r["nothing_extra"]["extra"] == 1
    r = _posts(lambda row: {**row, "name": "SIGNAL_PEDESTAL_0"} if row["id"] == armed else row)["signals"]
    assert [(w["id"], w["wanted_prefix"]) for w in r["present"]["wrong_type_rows"]] == [(armed, "SIGNAL_MAST_ARM")]
    r = _posts(lambda row: {**row, "arm": 270.0} if row["id"] == armed else row)["signals"]
    (w,) = r["present"]["wrong_facing_rows"]
    assert w["id"] == armed and w["wanted_deg"] == 180.0 and abs(w["built_deg"] - 270.0) < 1.0
    r = _posts(lambda row: {**row, "arm": 190.0} if row["id"] == armed else row)["signals"]       # 10 degrees: inside 15
    assert r["present"]["fail"] is False
    r = _posts(lambda row: {**row, "arm": None} if row["id"] == armed else row)["signals"]        # no arm built at all
    assert r["present"]["wrong_facing"] == 1 and r["present"]["wrong_facing_rows"][0]["built_deg"] is None


def test_nothing_extra_fails_a_post_by_rule():
    """a lamp every 55 m is what the chain plants today (tools/plan_streetlights.py): none of them is in the survey"""
    rule = [("LIGHTPOST", _join([_post(float(x), 12.0, 9.0, 180.0, 3.6) for x in range(-110, 221, 55)]))]
    r = _posts(extra=rule)["lamps"]
    assert r["present"]["fail"] is False and r["nothing_extra"]["fail"] is True and r["nothing_extra"]["extra"] == 7
    assert r["nothing_extra"]["rows"][0]["meshes"] == ["LIGHTPOST"]


def test_a_declared_none_covers_what_the_posts_do_not_reach():
    first = _posts()["lamps"]["covered"]
    doc = {**POLES, "none": [{"lap_m": s} for s in first["uncovered_stretches"]]}
    d = _project(POST_CFG, _post_groups(), {"poles.json": doc})
    r = _gate(d)["classes"]
    assert r["lamps"]["covered"]["fail"] is False and r["lamps"]["fail"] is False
    assert r["signals"]["covered"]["fail"] is True          # the same nones do not reach as far for signals (40 m, not 50)


SIGNS = {"items": [
    {"id": "g1", "type": "R1-1", "grade": "measured", "lonlat": None, "facing_deg": 90.0, "junction": "Colfax / Sherman"},
    {"id": "g2", "type": "R6-1R", "grade": "detected", "lonlat": None, "facing_deg": 180.0},
    {"id": "g3", "type": "R2-1", "grade": "tagged", "lonlat": None}]}
SIGN_XZ = {"g1": (8.0, 9.0), "g2": (-30.0, -11.0), "g3": (60.0, 10.0)}
SIGN_CFG = {"signs": {"file": "source/signs.json", "gate": True}}


def _signs_doc():
    m_lon, m_lat = paint_shapes.meters_per_degree(ORIGIN["lat"])
    doc = copy.deepcopy(SIGNS)
    for it in doc["items"]:
        x, n = SIGN_XZ[it["id"]]
        it["lonlat"] = [ORIGIN["lon"] + x / m_lon, ORIGIN["lat"] + n / m_lat]
    return doc


def _sign_groups(spoil=None):
    out = []
    for it in SIGNS["items"]:
        row = {"id": it["id"], "name": INV.type_prefix({}, "signs", it["type"]), "x": SIGN_XZ[it["id"]][0],
               "n": SIGN_XZ[it["id"]][1], "facing": it.get("facing_deg", 0.0)}
        row = row if spoil is None else spoil(row)
        if row is not None:
            k, tris = _plate(row["x"], row["n"], row["facing"])
            out.append((row["name"], _mesh(k, tris)))
    return out


def _signs(spoil=None, extra=()):
    return _gate(_project(SIGN_CFG, _sign_groups(spoil) + list(extra), {"signs.json": _signs_doc()}))["classes"]["signs"]


def test_sign_plates_are_read_by_name_place_and_the_way_the_face_looks():
    r = _signs()
    assert r["present"]["fail"] is False and r["present"]["judged"] == 3 and r["present"]["facing_not_given"] == 1
    assert r["nothing_extra"]["fail"] is False and r["built"]["objects"] == 3
    assert (r["grades"]["measured"], r["grades"]["detected"], r["grades"]["tagged"]) == (1, 1, 1)
    # the plate turned to look the other way
    r = _signs(lambda row: {**row, "facing": 270.0} if row["id"] == "g1" else row)
    (w,) = r["present"]["wrong_facing_rows"]
    assert w["id"] == "g1" and abs(w["built_deg"] - 270.0) < 0.5 and w["off_deg"] == 180.0
    # the wrong plate on the right post
    r = _signs(lambda row: {**row, "name": "SIGNFACE_W1_6"} if row["id"] == "g1" else row)
    assert r["present"]["wrong_type"] == 1
    # each grade its own tolerance: a detected sign 2 m off passes (3 m), a measured one does not (0.5 m)
    assert _signs(lambda row: {**row, "x": row["x"] + 2.0} if row["id"] == "g2" else row)["present"]["fail"] is False
    assert _signs(lambda row: {**row, "x": row["x"] + 2.0} if row["id"] == "g1" else row)["present"]["missing"] == 1


def test_a_sign_placed_by_rule_is_extra():
    """the W1-6 arrow plates the chain stands at tight corners today (SIGNPLATE): not in the survey, so extra"""
    k, tris = _plate(100.0, 9.0, 270.0, w=1.2, h=0.6)
    r = _signs(extra=[("SIGNPLATE_w16", _mesh(k, tris))])
    assert r["present"]["fail"] is False and r["nothing_extra"]["extra"] == 1


def test_the_face_convention_is_the_kn5s_own_winding():
    """a plate's front is its triangles' cross product in the kn5 frame, the rule verify_kn5 counts a road's up-faces
    by. Written through the real writer and read back from the file: a level triangle that verify_kn5 calls UP is the
    one whose front, by tools/inventory_gate's rule, points up."""
    up = _mesh([_kn5(p) for p in ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))], [(0, 1, 2)])
    d = _project(SIGN_CFG, [("1ROAD_probe", up)] + _sign_groups(), {"signs.json": _signs_doc()})
    _nodes, meshes, _mats = _parse_full(d / "build" / "t.kn5")
    probe = next(m for m in meshes if m["name"] == "1ROAD_probe")
    (name, P, idx), = [m for m in IG.read_kn5([d / "build" / "t.kn5"]) if m[0] == "1ROAD_probe"]
    a, b, c = (P[i] for i in idx[:3])
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    front_up = -(uz * vx - ux * vz)                     # the gate's rule: minus the local-frame cross product
    assert (probe["up"], probe["dn"]) in ((1, 0), (0, 1))
    assert (front_up > 0) == (probe["up"] == 1)


# --- the prep's paint rule (both preps: airoso's, and the engine-july copy an lm-v4 track runs) ---------------------
def _snapshot_prep():
    spec = importlib.util.spec_from_file_location("_engine_july_prep", SNAPSHOT_PREP)
    mod = importlib.util.module_from_spec(spec)
    was, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = was
    return mod


class _Objects(list):
    def __getitem__(self, k):
        return next(o for o in self if o.name == k) if isinstance(k, str) else list.__getitem__(self, k)

    def remove(self, ob, do_unlink=False):
        list.remove(self, ob)


class _Bpy:
    def __init__(self, names):
        class _O:
            def __init__(s, n):
                s.name, s.type = n, "MESH"
        self.data = type("D", (), {})()
        self.data.objects = _Objects(_O(n) for n in names)


SCENE = ["1ROAD_road", "1KERB_sidewalk", "1GRASS", "MARKINGS", "YLINE", "MARKINGS_paint_fork", "YLINE_I8_0", "ROADTEXT",
         "MARKINGS_inv_000", "YLINE_inv_000", "MARKINGS_paint_grid", "SIGNPLATE", "LIGHTPOST"]


def test_the_prep_leaves_every_scene_alone_when_the_track_names_no_paint_inventory():
    for prep in (bk, _snapshot_prep()):
        for cfg in ({"slug": "t"}, {"slug": "t", "inventory": {}}, {"slug": "t", "inventory": {"lamps": {"file": "l.json"}}},
                    {"slug": "t", "inventory": {"paint": {"gate": True}}}):
            assert prep.paint_inventory_of(cfg) is None
            # an object that raises on any touch: the function must return before it looks at the scene
            assert prep.drop_bywidth_paint(None, cfg) == []


def test_the_prep_drops_every_paint_mesh_the_inventory_did_not_author():
    for prep in (bk, _snapshot_prep()):
        cfg = {"slug": "t", "inventory": {"paint": {"file": "source/survey/paint.json",
                                                    "keep_prefixes": ["MARKINGS_paint_grid"]}}}
        b = _Bpy(SCENE)
        gone = prep.drop_bywidth_paint(b, cfg)
        assert sorted(gone) == ["MARKINGS", "MARKINGS_paint_fork", "ROADTEXT", "YLINE", "YLINE_I8_0"]
        assert [o.name for o in b.data.objects] == ["1ROAD_road", "1KERB_sidewalk", "1GRASS", "MARKINGS_inv_000",
                                                    "YLINE_inv_000", "MARKINGS_paint_grid", "SIGNPLATE", "LIGHTPOST"]
        # the inventory declared and its paint not in the scene: the author step did not run, nothing is prepped
        try:
            prep.drop_bywidth_paint(_Bpy(["1ROAD_road", "MARKINGS", "YLINE"]), cfg)
        except SystemExit as e:
            assert "author_paint_inventory_blend.py" in str(e)
        else:
            raise AssertionError(f"{prep.__name__}: prepped a scene with no inventory paint")


def test_the_author_step_and_the_prep_agree_on_what_is_paint_by_width():
    src = (ROOT / "tools" / "author_paint_inventory_blend.py").read_text(encoding="utf-8")
    assert "PAINT_CLASS = INV.MESH_PREFIXES[\"paint\"]" in src
    assert INV.MESH_PREFIXES["paint"] == bk.PAINT_CLASS == _snapshot_prep().PAINT_CLASS
    assert tuple(p.upper().rstrip("_") for p in INV.INVENTORY_PAINT.values()) == bk.INVENTORY_PAINT
    assert bk.is_bywidth_paint("YLINE_tile3") and not bk.is_bywidth_paint("YLINE_inv_002")
    assert not bk.is_bywidth_paint("1ROAD_road") and not bk.is_bywidth_paint("SIGNPLATE")

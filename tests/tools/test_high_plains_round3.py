"""High Plains round 3 (ledger 0097, 0.1.11): the Full layout as a second layout, and the opt-in engine pieces it needs.

Kevin, 2026-11-22: "Yes, add the Full layout". The north loop (To Hell On A Bobsled + Ladder To Heaven) is the port's own
connector; the fork is a measured pad (lm_pads, deck fill "membrane"), the merge a welded mouth; race.laps.full stitches the
lap; race_start.layouts gives each layout its own spawn kn5 from the one painted line. Every engine change is opt-in and no
other track declares any of it.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from scripts.geometry import circuit_start as cs  # noqa: E402
from scripts.ac import verify_kn5 as vk  # noqa: E402
import trim_connectors as tc  # noqa: E402

HP = ROOT / "tracks" / "high-plains-lm"
FULL = HP / "source" / "full"


def _cfg():
    return json.loads((HP / "track.config.json").read_text(encoding="utf-8"))


def _configs():
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):
        yield p.parent.name, json.loads(p.read_text(encoding="utf-8"))


# --- the config -------------------------------------------------------------------------------------------------------
def test_two_layouts_on_one_road_the_west_renamed_the_full_on_its_lap():
    c = _cfg()
    assert c["version"] in ("0.1.11", "0.1.12")               # round 4 (0.1.12) keeps both layouts
    w, f = c["layouts"]
    assert (w["id"], w["name"], w.get("lap"), w["ai"]) == ("west", "High Plains Raceway — West", None, "ai/west")
    assert (f["id"], f["name"], f["lap"], f["ai"]) == ("full_course", "High Plains Raceway — Full", "full", "ai/full_course")
    assert all(lo["kind"] == "race" and lo["race_furniture"] is False for lo in (w, f))
    assert (w["map"], f["map"]) == ("lap", "race_lap")
    assert "full" not in [lo["id"] for lo in c["layouts"]]       # track_folder drops a 'full' layout's name from the menu
    assert c["race_start"]["layouts"] == ["west", "full_course"]
    assert [ln["layout"] for ln in c["road_wear"]["lines"]] == ["west"]


def test_the_full_lap_is_the_west_lap_with_the_north_loop_between_its_two_junctions():
    c = _cfg()
    pieces = c["race"]["laps"]["full"]["pieces"]
    assert [p["line"] for p in pieces] == ["MAINLINE", "full_north#0#0", "MAINLINE"]
    a, b, m = pieces
    assert a["from"] == 0 and 896 < a["to"] < 907              # High Plains Drifter, inside the FORK pad (cuts 896 / 922)
    assert b["from"] == 0 and "via" in b and "via" in m
    assert 940 < m["from"] < 960 and m["to"] == 1072            # back on at the Prairie Corkscrew, round to the last vertex
    for via in (b["via"], m["via"]):
        assert all(len(q) == 3 and 10.0 <= q[2] <= 14.5 for q in via)
        assert all(math.dist(p[:2], q[:2]) < 3.0 for p, q in zip(via, via[1:]))


def test_the_north_loop_is_the_ports_connector_and_the_fork_a_pad():
    c = _cfg()
    assert c["lm_intake"]["connectors_file"] == "source/full/connectors.full.json"
    pads = c["lm_pads"]
    assert [p["id"] for p in pads["pads"]] == ["FORK"] and pads["arms"] == "streets"
    assert pads["deck"]["fill"] == "membrane" and pads["close_arms"] is False
    fork = pads["pads"][0]
    assert fork["cuts"] == [896, 922] and fork["node"] == 907
    assert fork["arms"][0]["connector"] == "full_north"
    assert c["route"]["street_junctions"]["pad_arms"] is True
    assert c["route"]["trim_host_bank"] is True and c["route"]["weld_exact_deck"] == ["full_north"]
    rec = json.loads((HP / "source" / "pads" / "FORK.json").read_text(encoding="utf-8"))
    assert rec["cuts"] == fork["cuts"] and rec["node"] == fork["node"]
    assert rec["source"]["kind"] == "naip" and 1300.0 < rec["area_m2"] < 1500.0
    assert all(v is None for row in rec["deck"]["y"] for v in row)      # nothing measures the deck: fill membrane


def test_ship_json_runs_the_connector_the_pad_the_lap_and_the_spawns():
    s = json.loads((HP / "ship.json").read_text(encoding="utf-8"))
    d, a, sh, g = (s["steps"][k] for k in ("draft", "author", "ship", "gate"))
    assert d[:4] == ["lm_intake", "build_loop_blend", "trim_connectors", "rebuild_loop_blend"]
    assert d.index("weld_mouths") < d.index("lm_pads") < d.index("strip_seam") < d.index("gap_mouths") < d.index("kerbs")
    assert a[0] == "race_laps" and sh[sh.index("export_road") + 1] == "spawn_kn5"
    assert {"verify_mouths", "verify_pads"} <= set(g)
    assert "source/full/connectors.full.json" in s["sync_in"]["required"]
    assert "source/pads/*.json" in s["sync_in"]["globs"]
    for f in ("data/lap.full.json", "data/dummies_{id}.json", "data/pads.built.json", "data/verify_pads.json"):
        assert f in s["sync_out"]["files"]


def test_the_heightfield_reaches_the_north_loop():
    m = json.loads((HP / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
    assert m["bbox_swne"] == [39.732566, -103.906618, 39.74124, -103.888297] and (m["nx"], m["ny"]) == (40, 25)
    nl = json.loads((FULL / "north_loop.json").read_text(encoding="utf-8"))
    o = json.loads((HP / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["origin"]
    top = max(p[2] for p in nl["connectors"][0]["points_xyz_m"])
    m_lat = cs.meters_per_degree(o["lat"])[1]
    assert o["lat"] + (top + 150.0) / m_lat <= m["bbox_swne"][2] + 1e-4    # the north loop's top + the stage's 150 m margin


# --- the measurements -------------------------------------------------------------------------------------------------
def test_the_hairpin_is_measured_off_the_north_tiles_and_nothing_up_there_is_carried():
    nl = json.loads((FULL / "north_loop.json").read_text(encoding="utf-8"))
    rows = nl["rows"]
    north = [r for r in rows if r["photo"] == "naip_z18_north"]
    assert len(north) >= 150 and all(r["width"] == "measured" for r in north)
    top = [r for r in rows if 380.0 <= r["s"] <= 690.0]
    assert all(r["width"] == "measured" for r in top)
    assert nl["summary"]["measured_m"] >= 800 and nl["summary"]["carried_m"] <= 200
    g = json.loads((FULL / "naip_2023_hp_north_z18.georef.json").read_text(encoding="utf-8"))
    assert (g["z"], g["x0"], g["y0"], g["w"], g["h"]) == (18, 55414, 99488, 512, 512)


def test_the_connector_file_is_the_measured_loop_painted_like_the_mainline():
    sys.path.insert(0, str(FULL))
    import make_connectors as mc
    nl = json.loads((FULL / "north_loop.json").read_text(encoding="utf-8"))
    built = mc.build(nl)
    on_disk = json.loads((FULL / "connectors.full.json").read_text(encoding="utf-8"))
    assert built == on_disk                                          # regenerated, not hand-edited
    c, = on_disk["connectors"]
    pts = c["points_xyz_m"]
    assert len(pts) == len(c["widths_m"]) == len(c["paint"]["lines"][0]["off"]) == 502
    assert all(ln["color"] == "white" for ln in c["paint"]["lines"])   # no yellow centre line on a circuit
    turn = []
    for a, b, q in zip(pts, pts[1:], pts[2:]):
        h0, h1 = math.atan2(b[0] - a[0], b[2] - a[2]), math.atan2(q[0] - b[0], q[2] - b[2])
        turn.append(abs(math.degrees((h1 - h0 + math.pi) % (2 * math.pi) - math.pi)))
    assert max(turn) < 6.0                                           # OSM's node polygon smoothed (it turned 23 deg at a node)


def test_the_t13_kerb_is_retraced_onto_its_paint_by_round_twos_rule():
    lm = json.loads((HP / "source" / "edges" / "kerbs.lm.json").read_text(encoding="utf-8"))
    run = next(k for k in lm["kerbs"] if (k["side"], k["s0"]) == ("left", 2843.0))
    assert "round 3" in run["_retrace"] and run["edge_lonlat_was"] != run["edge_lonlat"]
    m_lon, m_lat = cs.meters_per_degree(39.736)
    moved = [math.hypot((p[0] - q[0]) * m_lon, (p[1] - q[1]) * m_lat) for p, q in zip(run["edge_lonlat"], run["edge_lonlat_was"])]
    assert 2.3 < moved[0] < 2.8 and 0.8 < moved[1] < 1.3 and all(m < 0.01 for m in moved[2:5])
    r2673 = next(k for k in lm["kerbs"] if (k["side"], k["s0"]) == ("right", 2673.0))
    assert "round 2" in r2673["_retrace"]                            # round 2's own re-trace kept


def test_three_paddock_roofs_take_the_2018_lidar_forms_the_shed_is_owed():
    rows = {r["key"]: r for r in json.loads((HP / "source" / "bespoke" / "buildings.race.json").read_text(encoding="utf-8"))}
    a = rows["osm289311820"]
    assert (a["form"], a["wall_h_m"]) == ("flat", 4.28) and "ridge_h_m" not in a
    b = rows["osm289311821"]
    assert (b["form"], b["canopy_roof"], b["ridge_h_m"]) == ("posts", "gable", 3.72) and abs(b["wall_h_m"] + 0.15 - 2.62) < 1e-6
    c = rows["osm289311823"]
    assert (c["form"], c["wall_h_m"], c["ridge_h_m"], c["ridge_axis"]) == ("gable", 2.48, 4.74, "short")
    for r in (a, b, c):
        assert r["_h"].startswith("measured: the 2018 lidar") and r["_h_2023"]
    d = rows["traced_white_w_of_osm289311820"]                       # the lidar's shed: built since round 4 (atlas_shed)
    assert d["form"] == "shed" and d["atlas_shed"] is True and "round 4" in d["_lidar_2018"] and "gable" in d["_form_2023"]
    for k in ("traced_container_row", "traced_grey_roof_e_of_containers", "traced_pit_entry_canopy", "osm289311824"):
        assert not rows[k]["_h"].startswith("measured:")             # the 2018 lidar cannot read them: kept as they were


# --- the shared tools (opt-in) ----------------------------------------------------------------------------------------
def _oval(r=60.0, straight=300.0, step=2.0):
    pts = []
    x = 0.0
    while x < straight:
        pts.append((x, 0.0, 0.0)); x += step
    n = int(math.pi * r / step)
    for k in range(n):
        a = -math.pi / 2 + math.pi * k / n
        pts.append((straight + r * math.cos(a), 0.0, r + r * math.sin(a)))
    x = straight
    while x > 0:
        pts.append((x, 0.0, 2 * r)); x -= step
    for k in range(n):
        a = math.pi / 2 + math.pi * k / n
        pts.append((r * math.cos(a), 0.0, r + r * math.sin(a)))
    pts.append(pts[0])
    return {"origin": {"lon": 0.0, "lat": 0.0}, "points_xyz_m": [list(p) for p in pts], "widths_m": [12.0] * len(pts)}


RS = {"line": {"station_m": 150.0},
      "grid": {"pattern": {"first_m": -7.0, "step_m": -4.55, "lateral_m": [-2.8, 2.4], "slots": 6}},
      "pits": {"pattern": {"first_m": 8.0, "step_m": 4.55, "lateral_m": [-2.8, 2.4], "slots": 6}}}


def test_race_start_layouts_must_name_every_layout_once_and_forward():
    los = [{"id": "west"}, {"id": "full_course", "lap": "full"}]
    assert cs.layout_ids({}, los) == (None, [])
    assert cs.layout_ids({"layouts": ["west", "full_course"]}, los) == (["west", "full_course"], [])
    assert cs.layout_ids({"layouts": ["west"]}, los)[1]
    assert cs.layout_ids({"layouts": ["west", "west"]}, los)[1]
    assert cs.layout_ids({"layouts": ["west", "full_course"]}, [{"id": "west"}, {"id": "full_course", "direction": "reverse"}])[1]
    assert cs.layout_ids({"layouts": ["west", "full_course"], "sectors": {"stations_m": [1, 2]}}, los)[1]


def test_spawn_set_is_layout_dummies_schema_and_passes_the_race_start_judge():
    local = _oval()
    pl = cs.plan(RS, local)
    assert pl["problems"] == []
    d = cs.spawn_set(pl, local, {n: 0.4 for n in pl["nodes"]}, "west", None)
    assert d["_layout"] == "west" and d["_direction"] == "forward" and d["_race_start"] is True and "_lap" not in d
    names = {k for k in d if not k.startswith("_")}
    assert names == set(pl["nodes"]) and len([n for n in names if n.startswith("AC_START_")]) == 6
    assert set(d["_yaw_deg"]) == {n for n in names if n.startswith(cs.FACING)}
    assert all(d[n][1] == 0.4 for n in names)
    assert d["_line"]["pole_behind_line_m"] == pytest.approx(7.0, abs=0.01)
    # the spawn kn5's nodes as verify_kn5 reads them: kn5 (x, y, -z), local +Z of the yaw (sin, 0, cos) in kn5
    nodes3 = []
    for n in names:
        x, y, z = d[n]
        yaw = math.radians(d["_yaw_deg"].get(n, 0.0))
        nodes3.append((n, (x, y, -z), (math.sin(yaw), 0.0, math.cos(yaw))))
    fails, lines = vk.race_start_checks(RS, local, nodes3)
    assert fails == [], fails
    assert any("heading" in ln and "+1.00" in ln for ln in lines)
    lap = cs.spawn_set(pl, local, {n: 0.4 for n in pl["nodes"]}, "full_course", "full")
    assert lap["_lap"] == "full"


def _painted(n):
    return {"name": "p", "kind": "connector", "points_xyz_m": [[float(i), 0.0, 0.0] for i in range(n)],
            "widths_m": [10.0] * n, "paint": {"lines": [{"color": "white", "off": [4.0 + 0.01 * i for i in range(n)]}]}}


def test_trim_carries_line_paint_sliced_and_nothing_else():
    c = _painted(10)
    assert tc.carries_paint(c)
    assert tc.sliced_paint(c["paint"], [3, 3, 4, 5])["lines"][0]["off"] == [4.03, 4.03, 4.04, 4.05]
    assert not tc.carries_paint(dict(c, paint={"lines": c["paint"]["lines"], "strokes": [{"a": [0, 1], "b": [1, 1]}]}))
    assert not tc.carries_paint(dict(c, paint={"lines": [{"off": [1.0] * 9}]}))     # offsets not one per point
    assert not tc.carries_paint({k: v for k, v in c.items() if k != "paint"})


def test_cut_at_pads_keeps_the_paint_on_the_piece_it_cuts():
    c = _painted(40)                                                   # x 0..39 along z = 0
    pad = {"id": "P", "box": [[-5.0, -10.0], [10.5, -10.0], [10.5, 10.0], [-5.0, 10.0]]}
    out, arms = tc.cut_at_pads([c], [pad])
    piece, = out
    assert len(arms) == 1 and arms[0]["pad"] == "P"
    off = piece["paint"]["lines"][0]["off"]
    assert len(off) == len(piece["points_xyz_m"])
    assert piece["points_xyz_m"][0][0] == pytest.approx(10.5) and off[0] == pytest.approx(4.11)   # the crossing: point 11's (as its width)
    assert off[1:] == [round(4.0 + 0.01 * i, 2) for i in range(11, 40)]


def test_make_map_draws_a_layouts_own_lap_when_it_says_map_lap(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import make_map as mm
    lap = _oval()
    main = [[p[0], 0.0, -p[2]] for p in lap["points_xyz_m"]]          # finished_centerline is in the kn5 frame
    wide = [[p[0] * 2.0, p[1], p[2] * 2.0] for p in lap["points_xyz_m"]]   # a lap twice the mainline's size
    (tmp_path / "data").mkdir()
    cfg = {"slug": "t", "layouts": [{"id": "a", "map": "lap"}, {"id": "b", "lap": "x", "map": "race_lap"}, {"id": "c"},
                                    {"id": "d", "lap": "x", "map": "lap"}]}
    (tmp_path / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "data" / "finished_centerline.json").write_text(json.dumps({"points_xyz_m": main}), encoding="utf-8")
    (tmp_path / "data" / "lap.x.json").write_text(json.dumps({"points_xyz_m": wide}), encoding="utf-8")
    b = tmp_path / "build" / "t"
    b.mkdir(parents=True)
    for lid in "abcd":
        (b / f"models_{lid}.ini").write_text("", encoding="utf-8")
    mm.build(tmp_path)

    def scale(d):
        return float(next(ln for ln in (d / "data" / "map.ini").read_text().splitlines() if ln.startswith("SCALE_FACTOR"))
                     .split("=")[1])
    assert scale(b / "b") == pytest.approx(2.0 * scale(b / "a"), rel=0.05)   # its own lap, drawn to its own extent
    assert scale(b / "c") == pytest.approx(scale(b / "a"), rel=1e-6)        # network = the mainline here (no connector)
    assert scale(b / "d") == pytest.approx(scale(b / "a"), rel=1e-6)        # "lap" on a lap layout: the mainline, as before
    with pytest.raises(ValueError):
        mm.layout_scopes({"layouts": [{"id": "e", "map": "race_lap"}]})


def test_no_other_track_declares_any_round3_key():
    for t, c in _configs():
        if t == "high-plains-lm":
            continue
        assert "layouts" not in (c.get("race_start") or {}), t
        assert ((c.get("lm_pads") or {}).get("deck") or {}).get("fill") != "membrane", t
        for lo in c.get("layouts") or []:
            assert lo.get("map") != "race_lap", t
        for name in ((c.get("lm_intake") or {}).get("connectors_file") or "",):
            if "/" in name:
                conns = json.loads((ROOT / "tracks" / t / name).read_text(encoding="utf-8"))["connectors"]
                assert not any(tc.carries_paint(x) for x in conns), t


def test_the_engine_pieces_are_written_down_where_they_run():
    src = (ROOT / "tools" / "lm_pads_blend.py").read_text(encoding="utf-8")
    assert 'deck_cfg.get("fill") == "membrane"' in src and "def membrane_fill" in src
    weld = (ROOT / "tools" / "weld_mouths_blend.py").read_text(encoding="utf-8")
    assert "if r.size == 0 and mesh_block.size == 0:" in weld
    cd = (ROOT / "tools" / "circuit_dummies_blend.py").read_text(encoding="utf-8")
    assert "def per_layout(" in cd and "cs.layout_ids(" in cd
    vsrc = (ROOT / "scripts" / "ac" / "verify_kn5.py").read_text(encoding="utf-8")
    assert "_verify_race_start_spawn(" in vsrc

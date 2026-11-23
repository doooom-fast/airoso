"""Ledger 0093: High Plains' race furniture (the line, the grid, the pit lane's paint and sheet, the paddock's buildings,
K-rails and posts), every piece opt-in by a track.config.json key; the chain hooks; nothing else changes."""
from __future__ import annotations

import ast
import json
import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import paint_shapes as ps  # noqa: E402
from scripts.ac import verify_kn5 as vk  # noqa: E402
from scripts.geometry import circuit_start as cs  # noqa: E402

HP = ROOT / "tracks" / "high-plains-lm"
SH = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
CHANGED = ("scripts/geometry/circuit_start.py", "tools/circuit_dummies_blend.py", "tools/paint_shapes.py",
           "tools/author_paint_blend.py", "scripts/ac/verify_kn5.py")


def _cfg(track="high-plains-lm"):
    return json.loads((ROOT / "tracks" / track / "track.config.json").read_text(encoding="utf-8"))


def _local():
    return json.loads((HP / "data" / "centerline.local.json").read_text(encoding="utf-8"))


def _fn(name):
    m = re.search(rf"^{name}\(\) \{{\n(.*?)^\}}\n", SH, re.S | re.M)
    assert m, name
    return m.group(1)


def test_changed_files_parse_as_python_3_11():
    for rel in CHANGED:
        ast.parse((ROOT / rel).read_text(encoding="utf-8"), feature_version=(3, 11))


def test_the_chain_runs_the_declared_start_only_where_the_config_declares_one():
    prep = _fn("prep_prep")
    i = prep.index("tools/circuit_dummies_blend.py")
    assert prep.index("scripts/ac/build_kn5_loop.py") < i < prep.index("tools/road_wear_blend.py")
    assert "get('race_start')" in prep[prep.rindex("if [", 0, i):i]
    assert 'rm -f "$PROJ/data/circuit_dummies.json"' in prep
    # the paint: the draft pass on ROAD, the author pass on the bespoke surfaces after author_bespoke rebuilt them
    assert "author_paint_blend.py\" -- \"$PROJ\" --stage draft" in _fn("draft_paint")
    assert "author_paint_blend.py\" -- \"$PROJ\" --stage author" in _fn("author_paint")
    for t in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if t.parent.name != "high-plains-lm":
            assert "race_start" not in json.loads(t.read_text(encoding="utf-8")), t.parent.name


def test_high_plains_ship_json_paints_twice_and_syncs_the_ports_own_files():
    spec = json.loads((HP / "ship.json").read_text(encoding="utf-8"))
    d, a = spec["steps"]["draft"], spec["steps"]["author"]
    assert d[-1] == "paint" and d.index("kerbs") < d.index("paint")
    assert a == ["bespoke", "paint"]
    cfg = _cfg()
    files = [b["file"] for b in cfg["scenery"]["bespoke"]["blocks"]]
    assert files == ["source/bespoke/buildings.race.json", "source/bespoke/posts.race.json"]
    for f in files:
        assert f in spec["sync_in"]["required"] and (HP / f).exists()
        assert not (ROOT / "tracks" / "high-plains" / f).exists()          # the intake keeps the port's own file


def test_the_old_engine_track_and_lake_murray_keep_their_furniture():
    hp = _cfg("high-plains")
    assert [b["file"] for b in hp["scenery"]["bespoke"]["blocks"]] == ["source/bespoke/buildings.json", "source/bespoke/posts.json"]
    assert "race_start" not in hp and not (hp.get("route") or {}).get("paint")
    sd = ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json"
    if sd.exists():
        c = json.loads(sd.read_text(encoding="utf-8"))
        assert "race_start" not in c and not any(it.get("surface") for it in (c.get("route") or {}).get("paint") or [])
    mf = ROOT / "tracks" / "milford-road-course-lm" / "track.config.json"
    if mf.exists():                                                     # Milford's S/F is Kevin's call (ledger 0093)
        c = json.loads(mf.read_text(encoding="utf-8"))
        assert "race_start" not in c and not (c.get("route") or {}).get("paint")


def test_high_plains_paint_expands_onto_measured_places():
    cfg, local = _cfg(), _local()
    items = {it["id"]: it for it in cfg["route"]["paint"]}
    assert set(items) == {"sf_line", "grid_marks", "pit_lane_line", "pit_lane_end", "pit_in_gore", "pit_out_gore"}
    line = cs.Line(local["points_xyz_m"], local["widths_m"])
    for pid, it in items.items():
        assert ("surface" in it) == pid.startswith("pit_"), pid           # the pit lane's on PADAPRON, the rest on ROAD
        lines = ps.expand(it, local["origin"], local["points_xyz_m"])
        assert lines and all(len(ln["pts"]) >= 2 for ln in lines), pid
        assert len({ln.get("color") for ln in lines}) == 1, pid
    sf = ps.expand(items["sf_line"], local["origin"], local["points_xyz_m"])[0]["pts"]
    (s0, l0), (s1, l1) = (line.project(*p) for p in sf)
    assert abs(s0 - 12.15) < 0.3 and abs(s1 - 12.15) < 0.3 and l0 < -5.5 and l1 > 5.5
    assert max(abs(l0), abs(l1)) + 0.0 < line.width(12.15) / 2.0      # on the built ROAD, end to end
    dots = ps.expand(items["grid_marks"], local["origin"], local["points_xyz_m"])
    assert len(dots) == 50 and all(abs(math.dist(*d["pts"]) - 0.3) < 1e-6 for d in dots)
    for d in dots:
        s, lat = line.project(*d["pts"][0])
        assert abs(lat) < line.width(s) / 2.0 - 0.5                     # every mark on the racing surface
    yl = ps.expand(items["pit_lane_line"], local["origin"], local["points_xyz_m"])[0]["pts"]
    for p in yl:
        s, lat = line.project(*p)
        assert 19.5 < lat < 22.5, (s, lat)                                # 4-5 m off the paddock K-rail (+25.5)


def test_hatches_stay_inside_their_gores():
    cfg, local = _cfg(), _local()
    for it in cfg["route"]["paint"]:
        if not it["id"].endswith("gore"):
            continue
        h = it["lines"][0]["hatch"]
        poly = [ps.to_xz(local["origin"], q) for q in h["polygon_lonlat"]]
        lines = ps.expand(it, local["origin"], local["points_xyz_m"])
        assert lines[-1]["pts"][0] == lines[-1]["pts"][-1]                # the outline closes
        stripes = lines[:-1]
        assert len(stripes) >= 8, it["id"]
        for ln in stripes:
            mx = (ln["pts"][0][0] + ln["pts"][1][0]) / 2.0
            mz = (ln["pts"][0][1] + ln["pts"][1][1]) / 2.0
            c = False
            j = len(poly) - 1
            for i in range(len(poly)):
                (xi, zi), (xj, zj) = poly[i], poly[j]
                if (zi > mz) != (zj > mz) and mx < (xj - xi) * (mz - zi) / (zj - zi) + xi:
                    c = not c
                j = i
            assert c, it["id"]


def test_sand_creeks_paint_expands_to_itself():
    sc = ROOT / "tracks" / "sand-creek-lm" / "track.config.json"
    if not sc.exists():
        pytest.skip("sand-creek-lm is outside this checkout")
    for it in (json.loads(sc.read_text(encoding="utf-8")).get("route") or {}).get("paint") or []:
        assert not ps.needs_line(it) and "surface" not in it
        assert [ln["pts"] for ln in ps.expand(it)] == [[(float(p[0]), float(p[1])) for p in ln["pts"]] for ln in it["lines"]]


def test_pit_lane_sheet_meets_the_paddock_sheet_and_keeps_the_old_names():
    bes = _cfg()["scenery"]["bespoke"]
    pads = bes["pads"]
    assert pads[0]["key"] == "paddock" and "quad_lonlat" in pads[0]       # PADAPRON_0 is still the paddock
    strip = next(p for p in pads if p["key"] == "pitlane")["strip_lonlat"]
    assert len(strip["inner"]) == len(strip["outer"]) >= 30
    posts = [p for p in pads if p["key"].endswith("_pad")]
    assert len(posts) == 9 and all(len(p["quad_lonlat"]) == 4 for p in posts)
    rails = [r["key"] for r in bes["rails"]]
    assert rails[:8] == ["infield_t", "pit_wall_naip_rest", "pit_paddock_naip_rest", "paddock_east_naip_rest",
                         "pit_wall_lidar", "pit_paddock_lidar", "paddock_east_lidar", "back_straight_lidar"]
    new = {r["key"]: r for r in bes["rails"][8:]}
    assert new["pit_wall_west"]["height_m"] == 1.03 and new["pit_paddock_west"]["height_m"] == 0.59
    assert new["pit_wall_nose"]["kind"] == "tyres"
    rows = [r for k, r in new.items() if k.startswith("paddock_row_")]
    assert len(rows) == 13 and all(r["kind"] == "krail" and "height_m" not in r for r in rows)   # 0.81 m [invented]
    assert not {"paddock_row_3", "paddock_row_8"} & set(new)   # 2026-11-22: the kerb paint, not K-rails (ledger 0097 round 2)
    # the west pit wall ends where the lidar's begins, the paddock rail likewise
    by = {r["key"]: r for r in bes["rails"]}
    assert by["pit_wall_west"]["polyline_lonlat"][-1] == by["pit_wall_lidar"]["polyline_lonlat"][0]
    assert by["pit_paddock_west"]["polyline_lonlat"][-1] == by["pit_paddock_lidar"]["polyline_lonlat"][0]


def test_paddock_buildings_drop_the_duplicate_and_name_a_source_per_height():
    rows = json.loads((HP / "source" / "bespoke" / "buildings.race.json").read_text(encoding="utf-8"))
    keys = [r["key"] for r in rows]
    assert "osm289317403" not in keys                                     # the same roof as post1
    assert {"traced_white_w_of_osm289311820", "traced_pit_entry_canopy", "traced_container_row"} <= set(keys)
    by = {r["key"]: r for r in rows}
    assert by["osm289314487"]["roof"] == "white"                          # bright on the 0.3 m crop, not dark
    for r in rows:
        assert any(w in r["_h"] for w in ("shadow estimate", "official", "[invented]", "measured: the 2018 lidar")), r["key"]
        if r["form"] == "gable":
            assert r["ridge_h_m"] > r["wall_h_m"] >= 2.1, r["key"]
    posts = json.loads((HP / "source" / "bespoke" / "posts.race.json").read_text(encoding="utf-8"))
    src = json.loads((ROOT / "tracks" / "high-plains" / "source" / "bespoke" / "posts.json").read_text(encoding="utf-8"))
    assert [p["key"] for p in posts] == [p["key"] for p in src]
    moved = [p["key"] for p, q in zip(posts, src) if p["footprint_lonlat"] != q["footprint_lonlat"]]
    assert moved == ["post0", "post1", "post2", "post3", "post4", "post6", "post8", "post9"]


def _nodes(pl, flip=()):
    """kn5-frame nodes as verify_kn5._parse_full returns them, from a plan (z mirrored; local +Z from the yaw)"""
    out = []
    for n, v in pl["nodes"].items():
        if "yaw_deg" in v:
            a = math.radians(v["yaw_deg"] + (180.0 if n in flip else 0.0))
            zax = (math.sin(a), 0.0, math.cos(a))
        else:
            zax = (0.0, 0.0, 1.0)
        out.append((n, (v["x"], v["y"], -v["z"]), zax))
    return out


def test_verify_kn5_judges_a_declared_start_with_its_own_thresholds():
    cfg, local = _cfg(), _local()
    pl = cs.plan(cfg["race_start"], local)
    fails, lines = vk.race_start_checks(cfg["race_start"], local, _nodes(pl))
    assert fails == [] and any("heading" in ln for ln in lines)
    fails, _ = vk.race_start_checks(cfg["race_start"], local, _nodes(pl, flip={"AC_START_3"}))
    assert any(f.startswith("HEADING 'AC_START_3'") for f in fails)
    moved = [(n, ((p[0] + 6.0, p[1], p[2]) if n.startswith("AC_TIME_0") else p), z) for n, p, z in _nodes(pl)]
    fails, _ = vk.race_start_checks(cfg["race_start"], local, moved)
    assert any(f.startswith("LINE") for f in fails)
    short = [t for t in _nodes(pl) if t[0] != "AC_PIT_24"]
    fails, _ = vk.race_start_checks(cfg["race_start"], local, short)
    assert any("lacks" in f for f in fails)

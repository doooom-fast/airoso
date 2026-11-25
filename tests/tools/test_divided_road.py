"""Ledger 0098 0.2.13 (Sand Creek, North Colorado Blvd at its real width; the Mac's decisions 2026-11-24 / 25): the lap on
its measured carriageway (tools/divided_road.py -> lm_intake.carriageway), the far carriageway as its own side piece
(lm_intake.side_pieces, open_ends for tools/trim_connectors.py), the raised median as route.islands, and the 12 DRAPP 2022
poles in place of the six spaced lamps (scenery.streetlights.measured -> tools/streetlight_relocate.measured_plan). Every key
opt-in; Sand Creek alone names them. Pure Python: no Blender, no numpy."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SC = ROOT / "tracks" / "sand-creek-lm"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import divided_road as dr  # noqa: E402
import lm_engine_intake as li  # noqa: E402
import streetlight_relocate as SR  # noqa: E402
import trim_connectors as tc  # noqa: E402


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


CFG = _j(SC / "track.config.json")
CW = _j(SC / "source" / "carriageway_colorado.lidar.json")
FAR = _j(SC / "source" / "side_pieces_colorado.lidar.json")
ISL = _j(SC / "source" / "islands_colorado.lidar.json")
LAMPS = _j(SC / "source" / "lamps_colorado.drapp.json")


# ------------------------------------------------------------------ the tool's rules on stand-ins
def _station(s, faces, divided=True):
    return {"s_lap": s, "xz": [0.0, s], "normal_xz": [-1.0, 0.0], "divided": divided,
            "faces": {k: {"u_m": u, "kind": kind, "y_minus_side": 0.0, "y_plus_side": 0.14 if k == "median_near" else 0.0}
                      for k, (u, kind) in faces.items()}}


def test_series_reads_curbs_only_and_fills_short_gaps():
    st = [_station(float(s), {"right_edge": (-5.0, "curb")}) for s in range(0, 50, 5)]
    st[4]["faces"]["right_edge"]["kind"] = "fall"          # a falling edge is not the curb
    st[5]["faces"]["right_edge"]["kind"] = "none"
    ser = dr.series(st, "right_edge")
    assert set(ser) == {float(s) for s in range(0, 50, 5)}     # the two unread rows filled between measured ones
    assert all(abs(v + 5.0) < 1e-9 for v in ser.values())


def test_weight_is_a_raised_cosine_outside_the_span():
    assert dr.weight(100.0, [50.0, 150.0]) == 1.0
    assert dr.weight(25.0, [50.0, 150.0], 25.0) == 0.0
    assert abs(dr.weight(37.5, [50.0, 150.0], 25.0) - 0.5) < 1e-9


def test_unwrapped_reads_one_way_over_v0():
    st = [{"s_lap": s} for s in (9600.0, 9630.0, 1.0, 30.0)]
    assert [x["s_lap"] for x in dr.unwrapped(st, 9640.0)] == [-40.0, -10.0, 1.0, 30.0]


def test_islands_have_gaps_where_no_raised_median_reads():
    st = []
    for s in range(0, 100, 5):
        faces = {"median_near": (5.75, "curb"), "median_far": (10.0, "curb")}
        st.append(_station(float(s), faces if not (40 <= s <= 55) else {}))
    runs = dr.island_runs(st, [0.0, 100.0])
    assert [(st[r[0]]["s_lap"], st[r[-1]]["s_lap"]) for r in runs] == [(0.0, 35.0), (60.0, 95.0)]


# ------------------------------------------------------------------ the intake's two steps
def test_apply_carriageway_moves_and_refuses_another_line(tmp_path):
    rec = {"rows": [{"k": 1, "line_xz": [0.0, 10.0], "width_was_m": 16.5, "new_xz": [0.25, 10.0], "width_m": 11.0}]}
    (tmp_path / "cw.json").write_text(json.dumps(rec), encoding="utf-8")
    pts = [(0.0, 1.0, 0.0), (0.0, 1.0, 10.0), (0.0, 1.0, 20.0)]
    p2, w2, rep = li.apply_carriageway(tmp_path, "cw.json", pts, [16.5, 16.5, 16.5])
    assert p2[1] == [0.25, 1.0, 10.0] and w2 == [16.5, 11.0, 16.5] and rep["rows"] == 1
    with pytest.raises(SystemExit):
        li.apply_carriageway(tmp_path, "cw.json", [(0.0, 1.0, 0.0), (0.3, 1.0, 10.0), (0.0, 1.0, 20.0)], [16.5] * 3)
    with pytest.raises(SystemExit):
        li.apply_carriageway(tmp_path, "cw.json", pts, [16.5, 18.0, 16.5])


def test_add_side_pieces_appends_keeps_open_ends_and_refuses_a_duplicate(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "connectors.local.json").write_text(json.dumps({"connectors": [
        {"name": "grid_primary_1", "kind": "connector", "points_xyz_m": [[0, 0, 0], [1, 0, 0]], "widths_m": [9.5, 9.5]}]}),
        encoding="utf-8")
    (tmp_path / "side.json").write_text(json.dumps(FAR), encoding="utf-8")
    assert li.add_side_pieces(tmp_path, "side.json", tmp_path / "data") == ["grid_primary_colorado_sb"]
    got = _j(tmp_path / "data" / "connectors.local.json")["connectors"]
    assert [c["name"] for c in got] == ["grid_primary_1", "grid_primary_colorado_sb"] and got[1]["open_ends"] is True
    with pytest.raises(SystemExit):
        li.add_side_pieces(tmp_path, "side.json", tmp_path / "data")


def test_trim_never_stretches_an_open_ended_piece_onto_its_host():
    host = [(0.0, 0.0, float(z)) for z in range(-50, 151, 5)]
    hw = [11.0] * len(host)
    # a piece beside the host 14 m to its left, its ends within REACH_M of it (as Colorado's far carriageway)
    piece = {"name": "grid_primary_colorado_sb", "kind": "connector", "open_ends": True,
             "points_xyz_m": [[-14.0, 0.0, float(z)] for z in range(0, 101, 5)], "widths_m": [10.0] * 21}
    out = tc._trim_against([dict(piece)], [("MAINLINE", host, hw)], [])
    assert out[0]["points_xyz_m"] == piece["points_xyz_m"]
    plain = dict(piece)
    plain.pop("open_ends")
    out2 = tc._trim_against([plain], [("MAINLINE", host, hw)], [])
    assert out2[0]["points_xyz_m"] != piece["points_xyz_m"]       # without the flag both ends are reached (and cut)


# ------------------------------------------------------------------ the measured posts
def _plan(heads, posts, road=lambda x, z: False, zone=(0.0, 100.0)):
    spec = {"file": "f", "zone": zone, "posts": posts, "max_move_m": 0.75, "step_m": 0.05}
    cl = [(0.0, 0.0, float(z)) for z in range(0, 301)]

    def nearest(x, z):
        return min(cl, key=lambda p: (p[0] - x) ** 2 + (p[2] - z) ** 2)
    return SR.measured_plan(heads, lambda i, h: SR.base_of(h, nearest, 1.8), lambda x, z: z, spec, nearest, 1.8, road,
                            lambda x, z: 0.0, 8.8)


def test_measured_posts_replace_the_zone_and_keep_the_rest_in_order():
    heads = [[9.0, 8.8, 55.0], [-9.0, 8.8, 110.0], [9.0, 8.8, 165.0]]
    posts = [{"id": "q2", "base": (-12.0, 60.0), "out": (-1.0, 0.0)}, {"id": "q1", "base": (12.0, 20.0), "out": (1.0, 0.0)}]
    new, rec = _plan(heads, posts)
    assert [r["i"] for r in rec["replaced"]] == [0] and rec["inserted_at"] == 0
    assert [r["id"] for r in rec["posts"]] == ["q1", "q2"] and len(new) == 4 and new[2:] == heads[1:]
    hx, hy, hz = new[0]
    assert abs(hx - 10.2) < 1e-6 and abs(hz - 20.0) < 1e-6 and hy == 8.8      # the arm 1.8 m road-ward, 8.8 m up


def test_a_measured_post_steps_out_at_most_its_limit_or_stays_for_drop_on_road():
    def road(x, z):
        return x < 5.6          # the pavement (+ footprint) reaches 5.6 m out
    posts = [{"id": "near", "base": (5.2, 50.0), "out": (1.0, 0.0)}, {"id": "far_in", "base": (4.0, 70.0), "out": (1.0, 0.0)}]
    _new, rec = _plan([], posts, road)
    by = {r["id"]: r for r in rec["posts"]}
    assert by["near"]["status"] == "moved" and abs(by["near"]["moved_m"] - 0.4) < 1e-9
    assert by["far_in"]["status"] == "on_road" and by["far_in"]["base_xz"] == [4.0, 70.0]


def test_measured_spec_validates(tmp_path):
    cfg = {"scenery": {"streetlights": {"measured": {"file": "source/lamps_colorado.drapp.json"}}}}
    spec = SR.measured_spec(cfg, lambda rel: _j(SC / rel))
    assert len(spec["posts"]) == 12 and spec["zone"] == (0.0, 412.0) and spec["max_move_m"] == 0.75
    assert SR.measured_spec({}, lambda rel: {}) is None
    with pytest.raises(ValueError):
        SR.measured_spec({"scenery": {"streetlights": {"measured": {"file": "../x.json"}}}}, lambda rel: {})


# ------------------------------------------------------------------ Sand Creek's records
def test_sand_creek_names_the_0213_keys_and_no_other_track_does():
    li_ = CFG["lm_intake"]
    assert li_["carriageway"] == "source/carriageway_colorado.lidar.json"
    assert li_["side_pieces"] == "source/side_pieces_colorado.lidar.json"
    assert CFG["scenery"]["streetlights"]["measured"] == {"file": "source/lamps_colorado.drapp.json"}
    assert CFG["version"] == "0.2.13"
    ship = _j(SC / "ship.json")
    for f in ("source/carriageway_colorado.lidar.json", "source/side_pieces_colorado.lidar.json",
              "source/lamps_colorado.drapp.json"):
        assert f in ship["sync_in"]["optional"] and (SC / f).is_file()
    assert ship["sync_out"]["required"] == []           # Kevin: "Keep only builds apart" (loop.blend a record)
    for cfg_p in (ROOT / "tracks").glob("*/track.config.json"):
        if cfg_p.parent.name == "sand-creek-lm":
            continue
        c = _j(cfg_p)
        assert not any(k in (c.get("lm_intake") or {}) for k in ("carriageway", "side_pieces")), cfg_p
        assert "measured" not in ((c.get("scenery") or {}).get("streetlights") or {}), cfg_p


def test_the_lap_moves_only_on_colorado_and_the_pads_keep_their_rows():
    rows = CW["rows"]
    ks = [r["k"] for r in rows]
    assert ks == list(range(14, 125))
    for pad in CFG["lm_pads"]["pads"]:
        if pad["id"] in ("colorado_50th", "48th_colorado"):
            assert not set(ks) & set(range(pad["cuts"][0], pad["cuts"][1] + 1)), pad["id"]
    src = _j(ROOT / "tracks" / "sand-creek" / "data" / "centerline.local.json")
    for r in rows:                                    # the record names the source's own line (no earlier step moves it)
        p = src["points_xyz_m"][r["k"]]
        assert math.hypot(p[0] - r["line_xz"][0], p[2] - r["line_xz"][1]) < 0.01
    on = [r for r in rows if r["left_u_m"] is not None and r["weight"].get("left") == 1.0]
    w = [r["width_m"] for r in on]
    assert 10.7 < min(w) and max(w) < 12.8            # the near carriageway (16.5 m before): 10.76-12.77 m
    rep = CW["report"]["built_edge_off_target_across_m"]
    assert rep["right"]["max"] < 0.15 and rep["left"]["max"] < 0.15


def test_the_far_piece_and_the_islands_meet_their_pavements():
    con = FAR["connectors"][0]
    assert con["name"] == "grid_primary_colorado_sb" and con["open_ends"] is True
    assert 10.0 <= min(con["widths_m"]) and max(con["widths_m"]) < 13.5
    G = _j(SC / "source" / "roads_lidar_g10" / "lap_colorado_quebec.lidar.json")["stretches"]["colorado"]["stations_list"]
    st = dr.unwrapped(G, 9639.1745)
    mn, mf = dr.series(st, "median_near"), dr.series(st, "median_far")
    isl = {i["id"]: i for i in CFG["route"]["islands"] if i["id"].startswith("colorado_median_")}
    assert sorted(isl) == ["colorado_median_0", "colorado_median_1", "colorado_median_2"]
    far_s = [r["s_lap"] for r in FAR["stations"]]
    for i in isl.values():
        assert all(0.1 < r < 0.2 for r in i["rise_m"]), i["rise_m"]            # the lidar's 0.11-0.17 m curb steps
        s0, s1 = ISL["islands"][int(i["id"][-1])]["s_built_m"]
        assert min(far_s) < s0 and s1 < max(far_s)                              # edge B always over the far piece
    # the gaps the Mac named: the railway (s ~258-268) and the turn bay (s ~295-328)
    spans = sorted(tuple(x["s_built_m"]) for x in ISL["islands"])
    assert spans[0][1] < 258 and 268 < spans[1][0] and spans[1][1] < 295 and 328 < spans[2][0]
    # each island edge stands 0.25 m onto its pavement: A inside the lap's median face, B past the far face
    s = 200.83
    st_ = next(x for x in st if abs(x["s_lap"] - s) < 0.01)
    row = next(r for r in isl["colorado_median_0"]["rows"]
               if abs(r[1] - (st_["xz"][1] + st_["normal_xz"][1] * (dr.at(mn, s) - 0.25))) < 0.01)
    ua = (row[0] - st_["xz"][0]) * st_["normal_xz"][0] + (row[1] - st_["xz"][1]) * st_["normal_xz"][1]
    ub = (row[2] - st_["xz"][0]) * st_["normal_xz"][0] + (row[3] - st_["xz"][1]) * st_["normal_xz"][1]
    assert abs(ua - (dr.at(mn, s) - 0.25)) < 0.01 and abs(ub - (dr.at(mf, s) + 0.25)) < 0.01


def test_the_lamps_are_the_twelve_read_poles_with_their_credit():
    ids = [p["id"] for p in LAMPS["posts"]]
    assert sorted(ids) == sorted(["a", "b", "w2", "g", "f", "i", "h", "k", "j", "n", "p", "o"])
    assert LAMPS["credit"].startswith("DRAPP 2022, DRCOG") and LAMPS["zone_s_built_m"] == [0.0, 412.0]
    poles = {p["id"]: p for p in _j(SC / "source" / "roads_lidar_g10" / "colorado_poles.ortho.json")["poles"]}
    for p in LAMPS["posts"]:
        assert poles[p["id"]]["read"] is True and p["base_xz"] == poles[p["id"]]["base_xz"]
        out = p["out_xz"]
        assert abs(math.hypot(*out) - 1.0) < 1e-3
        # east of the lap (u < 0) steps east (+x), west steps west, the median twin toward the median's middle (east)
        assert (out[0] > 0) == (p["u_m"] < 0 or p["side"] == "median")
    assert sum(1 for p in LAMPS["posts"] if p["side"] == "median") == 1

"""scripts.geometry.network_reference — a road network's ONE reference line, from the draft's own built edges.

The ship phase (prep, write_ai_line, make_map, verify_kn5, drive_test) walks one line; a network draft has none. The
config declares a real mainline (network.reference_line) and the step resolves it from network.geojson +
data/network.edges.local.json (the lines build_network_mesh swept). These pin: every point of the line is a vertex of a
built edge, joined only at a shared node (never across a gap); a declared ref chain that is not contiguous is refused;
the explicit edge_ids path is checked the same way; the travel direction is the OSM ways' (classify travel_dir) and is
cross-checked against the opposite carriageway's side; the files are in the frames their readers expect (local ENU
unmirrored, "mesh" for the prep), loop false, the grid at the start and AC_TIME_0 at the finish (L11).
Synthetic network: a divided freeway "I 8" running east (south carriageway, eastbound) and west (north carriageway,
z = +30 m), three edges each, plus an on-ramp — all plain test functions (tests/run_tests.py).
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from scripts.geometry import network_reference as nr

STEP = 5.0
LIFT = 0.12


def _line(x0, x1, z, y0=10.0, grade=0.01):
    n = int(round(abs(x1 - x0) / STEP))
    sgn = 1.0 if x1 > x0 else -1.0
    return [[x0 + sgn * STEP * i, y0 + grade * (x0 + sgn * STEP * i), z] for i in range(n + 1)]   # one profile


def _edge(eid, pts_travel, *, name="I 8", ramp=False, store_reversed=False, width=16.0, travel=None):
    """A built edge whose TRAVEL order is ``pts_travel``; stored (geojson order) reversed when store_reversed."""
    stored = pts_travel[::-1] if store_reversed else pts_travel
    td = (-1 if store_reversed else 1) if travel is None else travel
    rec = {"id": eid, "name": name, "road_class": "motorway", "is_ramp": ramp, "lanes": 4, "width_m": width,
           "travel_dir": td, "n_geojson": len(stored), "trimmed": False,
           "surface_xyz_m": [[x, y + LIFT, z] for x, y, z in stored],
           "at_grade_xyz_m": [list(p) for p in stored], "widths_m": [width] * len(stored)}
    feat = {"type": "Feature", "properties": {"id": eid, "name": name, "road_class": "motorway", "is_ramp": ramp,
                                              "length_m": round(sum(math.dist((a[0], a[2]), (b[0], b[2]))
                                                                    for a, b in zip(stored, stored[1:])), 1),
                                              "travel_dir": td, "width_m": width},
            "geometry": {"type": "LineString", "coordinates": [[-117.0 + p[0] / 93000.0, 32.77 + p[2] / 111000.0]
                                                               for p in stored]}}
    return rec, feat


def _network(drop=(), rename=None, flip_travel=False, z0=0.0):
    """EB: edges 1, 2, 3 along z = 0 west -> east (2 stored reversed); WB: 4, 5, 6 along z = +30 east -> west;
    ramp 7 joins EB at x = 300 from the south."""
    rename = rename or {}
    eb = [_line(0, 300, z0), _line(300, 600, z0), _line(600, 900, z0)]
    wb = [_line(900, 600, z0 + 30.0), _line(600, 300, z0 + 30.0), _line(300, 0, z0 + 30.0)]
    specs = [(1, eb[0], False), (2, eb[1], True), (3, eb[2], False),
             (4, wb[0], False), (5, wb[1], True), (6, wb[2], False)]
    recs, feats = [], []
    for eid, pts, rev in specs:
        if eid in drop:
            continue
        if flip_travel:   # the data says every carriageway is driven the other way (contradicts right-hand traffic)
            r, f = _edge(eid, pts[::-1], name=rename.get(eid, "I 8"), store_reversed=not rev)
        else:
            r, f = _edge(eid, pts, name=rename.get(eid, "I 8"), store_reversed=rev)
        recs.append(r)
        feats.append(f)
    ramp = [[280.0 + 2 * i, 12.8, z0 - 60.0 + 6 * i] for i in range(11)]       # ends ON the EB node at (300, 0)
    r, f = _edge(7, ramp, name=None, ramp=True, width=8.5)
    recs.append(r)
    feats.append(f)
    fc = {"type": "FeatureCollection", "properties": {"edge_count": len(feats)}, "features": feats}
    erec = {"frame": "mesh local metres", "origin": {"lon": -117.0, "lat": 32.77, "elev_m": 100.0},
            "mirror_x": False, "road_lift_m": LIFT, "edges": recs}
    return fc, erec


def _refused(fn) -> str:
    try:
        fn()
    except nr.RefusedError as e:
        return e.reason
    raise AssertionError("expected a refusal")


def test_the_line_is_real_edge_vertices_only_in_driving_order():
    fc, erec = _network()
    r = nr.resolve({"ref": "I 8", "direction": "eastbound"}, fc, erec, snap_grid_m=7.0)
    assert r["chain"] == [1, 2, 3], r["chain"]
    built = {tuple(p) for e in erec["edges"] for p in e["surface_xyz_m"]}
    grade = {tuple(p) for e in erec["edges"] for p in e["at_grade_xyz_m"]}
    assert all(tuple(p) in built for p in r["surface"]), "a line point that is no built vertex"
    assert all(tuple(p) in grade for p in r["grade"])
    # driving order west -> east, no jump longer than a vertex step, the shared node written once
    xs = [p[0] for p in r["surface"]]
    assert xs == sorted(xs) and len(set(xs)) == len(xs)
    assert max(math.dist(a, b) for a, b in zip(r["surface"], r["surface"][1:])) <= STEP + 0.1
    assert [j["gap_m"] for j in r["joints"]] == [0.0, 0.0]
    assert len(r["surface"]) == len(r["grade"]) == len(r["widths"]) == len(r["source_by_vertex"]) == 181
    # edge 2 is stored reversed: its source vertices count DOWN in geojson order
    src2 = [v for e, v in r["source_by_vertex"] if e == 2]
    assert src2 == sorted(src2, reverse=True) and src2[0] == 59 and src2[-1] == 0   # its vertex 60 = edge 1's last
    assert r["judged_km"] == 0.9
    # the opposite carriageway is on the LEFT of eastbound travel (right-hand traffic) at every sample
    assert r["side_check"]["samples"] > 0 and r["side_check"]["right"] == 0
    # every other built edge is named unjudged, with the reason
    why = {u["id"]: u["why"] for u in r["unjudged"]}
    assert set(why) == {4, 5, 6, 7}
    assert why[7].startswith("ramp") and all(why[k] == "the other carriageway" for k in (4, 5, 6))


def test_westbound_takes_the_other_carriageway():
    fc, erec = _network()
    r = nr.resolve({"ref": "I 8", "direction": "westbound"}, fc, erec)
    assert r["chain"] == [4, 5, 6]
    assert r["surface"][0][0] == 900.0 and r["surface"][-1][0] == 0.0
    assert r["side_check"]["right"] == 0 and r["side_check"]["left"] > 0


def test_a_ref_chain_that_is_not_contiguous_is_refused():
    fc, erec = _network(drop=(2,))
    why = _refused(lambda: nr.resolve({"ref": "I 8", "direction": "eastbound"}, fc, erec))
    assert "not contiguous" in why and "piece" in why, why


def test_a_mislabelled_piece_is_refused_unless_a_bridge_is_allowed_and_then_named():
    fc, erec = _network(rename={2: "CA 163"})
    why = _refused(lambda: nr.resolve({"ref": "I 8", "direction": "eastbound"}, fc, erec))
    assert "not contiguous" in why
    r = nr.resolve({"ref": "I 8", "direction": "eastbound", "bridge_max_edges": 1}, fc, erec)
    assert r["chain"] == [1, 2, 3] and [b["id"] for b in r["bridged"]] == [2]
    assert r["bridged"][0]["name"] == "CA 163"


def test_explicit_edge_ids_are_checked_the_same_way():
    fc, erec = _network()
    r = nr.resolve({"edge_ids": [1, 2, 3], "direction": "eastbound"}, fc, erec)
    assert r["chain"] == [1, 2, 3]
    assert "not contiguous" in _refused(lambda: nr.resolve({"edge_ids": [1, 3]}, fc, erec))
    assert "not contiguous" in _refused(lambda: nr.resolve({"edge_ids": [3, 2, 1]}, fc, erec))   # against travel
    assert "does not have" in _refused(lambda: nr.resolve({"edge_ids": [1, 99]}, fc, erec))
    # a declared direction the list does not drive is refused too
    assert "off eastbound" in _refused(lambda: nr.resolve({"edge_ids": [4, 5, 6], "direction": "eastbound"}, fc, erec))


def test_no_u_turn_through_a_shared_end_node():
    """With a join tolerance wide enough to fuse WB's end (0, 30) and EB's start (0, 0) into one node, the two
    carriageways are 'contiguous' — and the joint turns 180 deg: never a continuation, so never one line."""
    fc, erec = _network()
    why = _refused(lambda: nr.resolve({"edge_ids": [4, 5, 6, 1, 2, 3], "join_tol_m": 40.0}, fc, erec))
    assert "turns" in why and "6 -> 1" in why, why
    r = nr.resolve({"ref": "I 8", "direction": "eastbound", "join_tol_m": 40.0}, fc, erec)
    assert r["chain"] == [1, 2, 3], r["chain"]


def test_undecided_travel_and_contradicted_side_are_refused():
    fc, erec = _network()
    for e in erec["edges"]:
        e["travel_dir"] = 0
    assert "undecided" in _refused(lambda: nr.resolve({"ref": "I 8", "direction": "eastbound"}, fc, erec))
    fc, erec = _network(flip_travel=True)        # the north carriageway "drives east": its partner on its RIGHT
    assert "RIGHT" in _refused(lambda: nr.resolve({"ref": "I 8", "direction": "eastbound"}, fc, erec))


def _project(tmp: Path, decl=None, *, loop=False, layouts=1):
    fc, erec = _network()
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    (tmp / "data" / "network.geojson").write_text(json.dumps(fc))
    (tmp / "data" / "network.edges.local.json").write_text(json.dumps(erec))
    cfg = {"slug": "net_t", "loop": loop, "mirror_x": False, "true_north_rotation_deg": 0.0,
           "network": {"snap_grid_m": 7.0, "reference_line": decl if decl is not None else
                       {"ref": "I 8", "direction": "eastbound"}},
           "layouts": [{"id": f"l{k}", "name": "Free Roam"} for k in range(layouts)]}
    (tmp / "track.config.json").write_text(json.dumps(cfg))
    return fc, erec


def test_build_writes_the_frames_loop_false_and_the_l11_grid():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fc, erec = _project(tmp)
        (tmp / "data" / "gate_centerline.json").write_text("{}")          # an earlier kn5's line: must go
        rep = nr.build(tmp)
        assert not (tmp / "data" / "gate_centerline.json").exists()
        loc = json.loads((tmp / "data" / "centerline.local.json").read_text())
        assert loc["loop"] is False and loc["frame"].startswith("ENU local meters")
        assert loc["origin"] == erec["origin"]
        assert loc["points_xyz_m"][0] == [0.0, 10.0, 0.0] and loc["points_xyz_m"][-1] == [900.0, 19.0, 0.0]
        assert set(loc["widths_m"]) == {16.0} and loc["point_count"] == len(loc["points_xyz_m"]) == 181
        fin = json.loads((tmp / "data" / "finished_centerline.json").read_text())
        assert fin["frame"].startswith("mesh") and "network reference line" in fin["frame"]
        assert all(abs(f[1] - g[1] - LIFT) < 1e-6 for f, g in zip(fin["points_xyz_m"], loc["points_xyz_m"]))
        assert json.loads((tmp / "data" / "bridge.spans.auto.json").read_text()) == []
        d = json.loads((tmp / "data" / "dummies.json").read_text())
        # L11: the grid at the START, AC_TIME_0 at the FINISH, splits 1, 2 in driving order (x grows eastbound)
        assert d["AC_START_0"][0] < 60.0 and d["AC_HOTLAP_START_0"] == d["AC_START_0"]
        t = {k: (d[f"AC_TIME_{k}_L"][0] + d[f"AC_TIME_{k}_R"][0]) / 2 for k in (0, 1, 2)}
        assert d["AC_START_0"][0] < t[1] < t[2] < t[0] and t[0] > 870.0
        assert all(d[f"AC_PIT_{p}"][0] > d["AC_START_0"][0] for p in range(4))
        k0 = min(range(len(fin["points_xyz_m"])), key=lambda k: abs(fin["points_xyz_m"][k][0] - d["AC_START_0"][0]))
        assert abs(d["AC_START_0"][1] - (fin["points_xyz_m"][k0][1] + nr.SPAWN_CLEAR_M)) < 1e-6   # off the pavement
        r = json.loads((tmp / "data" / "network.reference.json").read_text())
        assert r["line"]["edges"] == [1, 2, 3] and r["line"]["loop"] is False
        assert r["unjudged_edges"] == 4 and {u["id"] for u in r["unjudged"]} == {4, 5, 6, 7}
        assert rep["judged_km"] == 0.9


def test_a_refusal_leaves_no_line_behind():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _project(tmp)
        nr.build(tmp)
        assert (tmp / "data" / "finished_centerline.json").exists()
        cfg = json.loads((tmp / "track.config.json").read_text())
        cfg["network"]["reference_line"] = {"edge_ids": [1, 3]}
        (tmp / "track.config.json").write_text(json.dumps(cfg))
        _refused(lambda: nr.build(tmp))
        for f in ("centerline.local.json", "finished_centerline.json", "network.reference.json"):
            assert not (tmp / "data" / f).exists(), f


def test_build_refuses_a_loop_or_several_layouts_or_no_declaration():
    for kw, word in (({"loop": True}, "L11"), ({"layouts": 2}, "layout")):
        with tempfile.TemporaryDirectory() as td:
            _project(Path(td), **kw)
            assert word in _refused(lambda: nr.build(Path(td)))
    with tempfile.TemporaryDirectory() as td:
        _project(Path(td), decl={})
        assert "declares no network.reference_line" in _refused(lambda: nr.build(Path(td)))

"""tools/verify_stacked_legs.py — the Lariat's Drive-1 stacked-leg check (L4; V3-PLAN P5, ledger 0048), on synthetic
built laps whose truth is known.

The fixture is a closed 850 m lap shaped like one long switchback: leg A runs north along x = 0 at height 0, a
25 m connector climbs 10 m, leg B runs back south along x = 25 at height 10, and a 25 m connector drops back. A lap
point on leg A at z has a partner on leg B (< 40 m in plan, > 150 m along the lap) for 46.9 < z < 353.1: that
stretch is stacked, the ends are not.
- ground / edge / sign / closure vertices beside their own leg at their own leg's height pass; one beside leg A
  at leg B's height fails (each class), and the report names its own and the other station;
- a vertex outside the stacked stretch is never judged, whatever its height;
- a stacked lap point with no built road under it fails (it cannot be judged);
- --line-only reports the pairs, the nearest pair (25 m) and the vertical gap (10 m) and never passes;
- a lap that crosses over itself (a figure of eight on a bridge) reports the crossing and skips the vertices in
  its footprint instead of judging them against a leg that is not beside them;
- class matching puts a 1WALL_closure in closure, not edge; a track can override the classes.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import verify_stacked_legs as vsl  # noqa: E402
from scripts.geometry import ribbon  # noqa: E402

W = 6.0


def _dense(corners, step=1.0):
    out = []
    for (x0, y0, z0), (x1, y1, z1) in zip(corners, corners[1:]):
        L = ((x1 - x0) ** 2 + (z1 - z0) ** 2) ** 0.5
        n = max(1, int(round(L / step)))
        for k in range(n):
            t = k / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t))
    out.append(tuple(corners[-1]))
    return out


SWITCHBACK = [(0, 0, 0), (0, 0, 400), (25, 10, 400), (25, 10, 0), (0, 0, 0)]
FIGURE8 = [(0, 0, 0), (0, 0, 300), (150, 3.5, 300), (150, 7, 150), (-150, 7, 150), (-150, 3.5, 0), (0, 0, 0)]


def _write_obj(path: Path, groups) -> None:
    lines, base = [], 1
    for name, mesh in groups:
        lines.append(f"o {name}")
        for x, y, z in mesh["vertices"]:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for a, b, c in mesh["tris"]:
            lines.append(f"f {base+a} {base+b} {base+c}")
        base += len(mesh["vertices"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _road(corners, hole=None):
    """the ribbon leg by leg (a ribbon round a 90 deg corner folds; each straight is its own strip)"""
    verts, tris = [], []
    for a, b in zip(corners, corners[1:]):
        r = ribbon.road_ribbon(_dense([a, b]), [W] * len(_dense([a, b])))
        o = len(verts)
        verts += r["vertices"]
        for t in r["tris"]:
            if hole:
                zc = sum(r["vertices"][k][2] for k in t) / 3.0
                xc = sum(r["vertices"][k][0] for k in t) / 3.0
                if hole[0] < zc < hole[1] and abs(xc) < W:
                    continue
            tris.append((t[0] + o, t[1] + o, t[2] + o))
    return {"vertices": verts, "tris": tris}


def _dots(points):
    """a tiny triangle at each (x, y, z): its three vertices sit within 0.1 m of the point, at the point's height"""
    verts, tris = [], []
    for x, y, z in points:
        o = len(verts)
        verts += [(x, y, z), (x + 0.1, y, z), (x, y, z + 0.1)]
        tris.append((o, o + 1, o + 2))
    return {"vertices": verts, "tris": tris}


def _project(corners, groups, cfg_extra=None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = {"slug": "t", "loop": True}
    cfg.update(cfg_extra or {})
    (d / "track.config.json").write_text(json.dumps(cfg))
    cl = _dense(corners, 3.0)
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": [W] * len(cl)}))
    _write_obj(d / "data" / "track.obj", groups)
    return d


GOOD = [(5, 0.5, 200), (20, 9.5, 200), (-10, -3, 150), (35, 13, 250), (11.5, 4.5, 100)]


def test_vertices_beside_their_own_leg_pass():
    d = _project(SWITCHBACK, [("1ROAD_main", _road(SWITCHBACK)), ("1GRASS_between", _dots(GOOD)),
                              ("1WALL_stone", _dots([(3.5, 0.6, 180)])), ("SIGN_arrow", _dots([(28.5, 11, 220)]))])
    r = vsl.run(d)
    assert r["fail"] is False, r
    assert r["failures"] == 0 and r["tested"]["ground"] == 3 * len(GOOD)
    assert r["tested"]["edge"] == 3 and r["tested"]["sign"] == 3
    assert r["crossings"] == [] and r["stacked_points_without_road"] == 0
    assert r["nearest_plan_m"] == 25.0 and r["vertical_gap_m"]["min"] > 9.9 and r["vertical_gap_m"]["max"] < 10.1


def test_a_vertex_seated_to_the_other_leg_fails_in_every_class():
    for name, cls in (("1GRASS_fill", "ground"), ("1WALL_rail", "edge"), ("AUTH_sign_C4", "sign"),
                      ("1WALL_closure_race", "closure"), ("GEN_terrain_t3", "ground"), ("AUTH_cut_C5", "ground")):
        d = _project(SWITCHBACK, [("1ROAD_main", _road(SWITCHBACK)), ("1GRASS_between", _dots(GOOD)),
                                  (name, _dots([(5, 9.0, 200)]))])   # beside leg A (5 m), at leg B's height
        r = vsl.run(d)
        assert r["fail"] and r["failures"] == 3 and r["failures_by_class"] == {cls: 3}, (name, r["failures_by_class"])
        w = r["worst"][0]
        assert w["group"] == name and w["class"] == cls
        assert abs(w["own_station_m"] - 200) < 1.5, w                 # leg A at z = 200
        assert abs(w["other_station_m"] - (400 + 25 + 200)) < 1.5, w  # leg B at z = 200
        assert w["dy_own_m"] > w["dy_other_m"]


def test_a_vertex_outside_the_stacked_stretch_is_not_judged():
    # z = 20: across to leg B is 2 * 20 + 25 = 65 m along the lap (< 150): not a pair, whatever its height
    d = _project(SWITCHBACK, [("1ROAD_main", _road(SWITCHBACK)), ("1GRASS_end", _dots([(5, 9.0, 20)]))])
    r = vsl.run(d)
    assert r["fail"] is False and r["tested_total"] == 0, r


def test_a_stacked_point_with_no_road_under_it_fails():
    d = _project(SWITCHBACK, [("1ROAD_main", _road(SWITCHBACK, hole=(190, 210))), ("1GRASS_between", _dots(GOOD))])
    r = vsl.run(d)
    assert r["fail"] and r["failures"] == 0 and r["stacked_points_without_road"] >= 15, r


def test_line_only_measures_and_never_passes():
    d = _project(SWITCHBACK, [("1ROAD_main", _road(SWITCHBACK))])
    r = vsl.run(d, line_only=True)
    assert r["fail"] is None and r["pairs"] > 0 and r["nearest_plan_m"] == 25.0
    assert r["vertical_gap_m"]["min"] > 9.9 and r["vertical_gap_m"]["max"] < 10.1
    # the stacked stretch on leg A: z + 25 + z' > 150 with |z' - z| < sqrt(40^2 - 25^2) = 31.2, so 46.9 < z < 353.1
    runs = r["stacked_runs"]
    assert any(abs(a - 47) <= 1.5 and abs(b - 353) <= 1.5 for a, b in runs), runs
    assert vsl.main([str(d), "--line-only"]) == 0
    assert (d / "data" / "stacked_legs.line.json").exists()


def test_a_crossing_is_reported_and_its_footprint_skipped():
    groups = [("1ROAD_main", _road(FIGURE8)),
              ("1GRASS_under", _dots([(4, 0.2, 165), (-4, 0.3, 135)])),       # beside the lower road at the bridge
              ("1GRASS_far", _dots([(5, 0.4, 260)]))]                         # leg 1, not at any pair
    d = _project(FIGURE8, groups)
    r = vsl.run(d)
    assert len(r["crossings"]) == 1, r["crossings"]
    a, b = r["crossings"][0]
    assert abs(a - 150) < 2 and abs(b - 750) < 2
    assert r["crossing_skipped"] == 6 and r["failures"] == 0 and r["fail"] is False, r


def test_classes_closure_first_and_overridable():
    c = vsl.DEFAULT_CLASSES
    assert vsl.classify("1WALL_CLOSURE_race_cw", c) == "closure"
    assert vsl.classify("1WALL_stone_C4", c) == "edge"
    assert vsl.classify("1ROAD_main", c) is None and vsl.classify("TREES_pine", c) is None
    d = _project(SWITCHBACK, [("1ROAD_main", _road(SWITCHBACK)), ("ROCKS_scree", _dots([(5, 9.0, 200)]))],
                 {"gates": {"stacked_legs": {"classes": {"ground": ["ROCKS"]}}}})
    r = vsl.run(d)
    assert r["fail"] and r["failures_by_class"] == {"ground": 3}


def test_input_errors_exit_2():
    d = _project(SWITCHBACK, [("1GRASS_only", _dots(GOOD))])             # no road at all
    assert vsl.main([str(d)]) == 2
    (d / "data" / "track.obj").unlink()
    assert vsl.main([str(d)]) == 2

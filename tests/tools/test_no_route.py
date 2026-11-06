"""tools/no_route.py — the containment flood fill (ledger 0049), on synthetic L-shaped corridors.

A 16 m road runs 100 m north, turns right on a 30 m radius and runs 100 m east. race_cw (forward) drives the
right-hand side: its lane is the right curb strip face (-7.18 m) to its closure's face (closure centre 1 m left
of the centreline); race_acw (reverse) is the mirror. Walls are written as closed prisms into an OBJ (BUILT
mode) or taken from the declared polylines (PLANNED mode). Pins:

  * sealed passes (planned and built, both directions; the reverse layout works);
  * a 1.5 m door in the race-side strip FAILS at the right vertex and side, classed off_road, escaping to the
    open map; a 0.8 m crack passes (gaps under 1.0 m close);
  * a beam-only closure (0.63-0.93 m above the deck, the island beam's band) FAILS — it is not a wall;
  * an unpinned closure end FAILS (the car drives round it into the closed-off lane: class opposite);
  * a wall across the lane is "corridor blocked at v...";
  * a seed standing in a wall is an input error (SystemExit);
  * a reached forbidden probe FAILS;
  * a version-1 declaration is read with its own semantics (chain face), and a chain free end leaks.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import no_route as nr  # noqa: E402

W = 16.0
FACE = W / 2 - 0.82          # 7.18: the curb strip's road face
EDGE = W / 2 - 0.485         # 7.515: the curb strip's centre
CLOSE = 1.0                  # race_cw's closure centre, 1 m LEFT of the centreline
BH = 0.335
DECK = nr.DECK_LIFT_M         # the deck rides 0.10 over the centreline y


def _centreline(step=2.0, R=30.0):
    pts = []
    z = 0.0
    while z < 100.0 - 1e-9:
        pts.append((0.0, 0.0, z)); z += step
    n_arc = max(2, int(round(R * math.pi / 2 / step)))
    for q in range(n_arc):
        th = math.pi - (math.pi / 2) * q / n_arc
        pts.append((R + R * math.cos(th), 0.0, 100.0 + R * math.sin(th)))
    x = R
    while x <= R + 100.0 + 1e-9:
        pts.append((x, 0.0, 100.0 + R)); x += step
    return pts


PTS = _centreline()
N = len(PTS)


def _normal(k):
    a, b = PTS[max(0, k - 1)], PTS[min(N - 1, k + 1)]
    tx, tz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(tx, tz) or 1.0
    return -tz / L, tx / L


def _at(k, y):
    nx, nz = _normal(k)
    return PTS[k][0] + nx * y, PTS[k][2] + nz * y


def _corridor(lid, closure=(0, N - 1), probes=()):
    """a v2 corridor record: closure on [i, j] (else full width)"""
    sgn = 1.0 if lid == "race_cw" else -1.0
    y, lane, zone = [], [], []
    for k in range(N):
        if closure[0] <= k <= closure[1]:
            c = sgn * CLOSE
            y.append(c)
            lane.append([-FACE, c - BH] if lid == "race_cw" else [c + BH, FACE])
            zone.append("closure")
        else:
            y.append(None)
            lane.append([-FACE, FACE])
            zone.append("whole")
    return {"token": "cw" if lid == "race_cw" else "acw", "direction": "forward" if lid == "race_cw" else "reverse",
            "closure_y_by_vertex": y, "lane_by_vertex": lane, "zone_by_vertex": zone,
            "no_route": {"forbidden_probes": [dict(p) for p in probes]}}


def _bands(closure=(0, N - 1), probes=()):
    return {"version": 2, "params": {"barrier_half_m": BH, "edge_centre_from_lip_m": -0.485, "edge_inset_m": 0.82},
            "edge_strip_by_vertex": [1] * N, "edge_corners": [], "closed_mouths": [],
            "corridors": {lid: _corridor(lid, closure, probes) for lid in ("race_cw", "race_acw")}}


def _prism(name, poly, half=BH, y0=0.05, y1=1.25):
    """a closed wall prism along an xz polyline: (name, verts, tris)"""
    v, t = [], []
    m = len(poly)
    for i, (x, z) in enumerate(poly):
        a, b = poly[max(0, i - 1)], poly[min(m - 1, i + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L * half, tx / L * half
        v += [(x + nx, y0, z + nz), (x - nx, y0, z - nz), (x - nx, y1, z - nz), (x + nx, y1, z + nz)]
    for r in range(m - 1):
        a = 4 * r
        for q in range(4):
            q1 = (q + 1) % 4
            t += [(a + q, a + q1, a + 4 + q1), (a + q, a + 4 + q1, a + 4 + q)]
    last = 4 * (m - 1)
    t += [(0, 1, 2), (0, 2, 3), (last, last + 2, last + 1), (last, last + 3, last + 2)]
    return name, v, t


def _write_obj(path, objs):
    lines, base = [], 1
    for name, v, t in objs:
        lines.append(f"o {name}")
        lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in v]
        lines += [f"f {a + base} {b + base} {c + base}" for a, b, c in t]
        base += len(v)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _band(y, k0=0, k1=N - 1):
    return [_at(k, y) for k in range(k0, k1 + 1)]


def _cut(poly, k, f0, f1):
    """the polyline with the stretch between fractions f0..f1 of its segment k removed: two pieces"""
    a, b = poly[k], poly[k + 1]
    p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
    p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
    return poly[:k + 1] + [p0], [p1] + poly[k + 1:]


def _project(lid="race_cw", *, walls=None, bands=None, seed=None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    layouts = [{"id": "race_cw", "kind": "race", "direction": "forward", "race_furniture": True,
                "closure_token": "cw", "start": {"grid_vertex": 10, "offset_right_m": 3.0}},
               {"id": "race_acw", "kind": "race", "direction": "reverse", "race_furniture": True,
                "closure_token": "acw", "start": {"grid_vertex": N - 11, "offset_right_m": 3.0}}]
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False, "layouts": layouts}))
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in PTS],
                                                                  "widths_m": [W] * N}))
    (d / "data" / "barrier_bands.json").write_text(json.dumps(bands or _bands()))
    for l_ in ("race_cw", "race_acw"):
        k = 10 if l_ == "race_cw" else N - 11
        y = -3.0 if l_ == "race_cw" else 3.0
        sx, sz = seed if (seed and l_ == lid) else _at(k, y)
        px, pz = _at(k + (-4 if l_ == "race_cw" else 4), y)
        (d / "data" / f"dummies_{l_}.json").write_text(json.dumps({"AC_START_0": [sx, 0.1, sz], "AC_PIT_0": [px, 0.1, pz]}))
    if walls is not None:
        _write_obj(d / "data" / f"track.{lid}.obj", walls)
    return d


def _sealed_walls(lid="race_cw", closure_poly=None, edge_r=None):
    sgn = 1.0 if lid == "race_cw" else -1.0
    objs = [_prism("1WALL_race_edge_L", _band(EDGE)), _prism("1WALL_race_edge_R", _band(-EDGE))]
    if edge_r is not None:
        objs = [objs[0]] + [_prism(f"1WALL_race_edge_R_{i}", p) for i, p in enumerate(edge_r)]
    objs.append(_prism(f"1WALL_race_close_{'cw' if lid == 'race_cw' else 'acw'}", closure_poly or _band(sgn * CLOSE)))
    return objs


def test_a_sealed_corridor_passes_planned_and_built_both_directions():
    for lid in ("race_cw", "race_acw"):
        d = _project(lid, walls=_sealed_walls(lid))
        rp = nr.run(d, lid, planned=True, verbose=False)
        assert rp["fail"] is False and rp["leak_cells"] == 0 and rp["blocked"] == [], (lid, rp["fails"])
        rb = nr.run(d, lid, verbose=False)
        assert rb["fail"] is False and rb["leak_cells"] == 0 and rb["blocked"] == [], (lid, rb["fails"])
        assert rb["obj"] == f"track.{lid}.obj" and rb["wall_cells"] > 0 and rb["spawns_unreached"] == []
        assert (d / "data" / f"no_route.{lid}.json").exists() and (d / "data" / f"no_route.{lid}.planned.json").exists()


def test_a_one_and_a_half_metre_door_fails_at_its_vertex_and_side_and_escapes():
    k = 30
    a, b = _cut(_band(-EDGE), k, 0.125, 0.875)                  # 2 m segment, 1.5 m removed
    d = _project(walls=_sealed_walls(edge_r=[a, b]))
    r = nr.run(d, "race_cw", verbose=False)
    assert r["fail"] and r["leak_cells"] > 0
    doors = [x for x in r["doors"] if x["v0"] - 2 <= k <= x["v1"] + 2]
    assert doors and doors[0]["side"] == "R" and doors[0]["class"] == "off_road", r["doors"]
    assert doors[0]["escapes"] is True and r["escaped"] is True
    assert 0.5 <= doors[0]["gap_m"] <= 4.0, doors[0]


def test_a_crack_under_a_metre_closes():
    a, b = _cut(_band(-EDGE), 30, 0.3, 0.7)                     # 0.8 m
    d = _project(walls=_sealed_walls(edge_r=[a, b]))
    r = nr.run(d, "race_cw", verbose=False)
    assert r["fail"] is False and r["leak_cells"] == 0, r["fails"]


def test_a_beam_only_closure_is_not_a_wall():
    objs = [_prism("1WALL_race_edge_L", _band(EDGE)), _prism("1WALL_race_edge_R", _band(-EDGE)),
            _prism("1WALL_guard", _band(CLOSE), half=0.12, y0=0.73, y1=1.03)]     # 0.63-0.93 above the deck
    d = _project(walls=objs)
    r = nr.run(d, "race_cw", verbose=False)
    assert r["fail"] and r["leak_cells"] > 0
    assert any(x["class"] == "opposite" for x in r["doors"]), r["doors"]
    # the same beam WITH posts reaching the deck band every ~9 m is still only dots, not a seal
    posts = [_prism(f"1WALL_guard_post{i}", [_at(k, CLOSE), _at(k + 1, CLOSE)], half=0.06, y0=0.30, y1=0.73)
             for i, k in enumerate(range(5, N - 5, 5))]
    d2 = _project(walls=objs + posts)
    assert nr.run(d2, "race_cw", verbose=False)["fail"]


def test_an_unpinned_closure_end_fails():
    bands = _bands(closure=(20, N - 21))
    objs = [_prism("1WALL_race_edge_L", _band(EDGE)), _prism("1WALL_race_edge_R", _band(-EDGE)),
            _prism("1WALL_race_close_cw", _band(CLOSE, 20, N - 21))]     # stops 1 m off the centreline: free ends
    d = _project(walls=objs, bands=bands)
    r = nr.run(d, "race_cw", verbose=False)
    assert r["fail"] and r["leak_cells"] > 0
    assert any(x["class"] == "opposite" and x["side"] == "L" for x in r["doors"]), r["doors"]
    rp = nr.run(d, "race_cw", planned=True, verbose=False)          # the declaration itself has the hole
    assert rp["fail"] and rp["leak_cells"] > 0


def test_a_wall_across_the_lane_blocks_the_lap():
    objs = _sealed_walls() + [_prism("1WALL_stray", [_at(40, -EDGE), _at(40, CLOSE)])]
    d = _project(walls=objs)
    r = nr.run(d, "race_cw", verbose=False)
    assert r["fail"] and r["leak_cells"] == 0
    assert r["blocked"] and r["blocked"][0][0] <= 41 and r["blocked"][-1][1] == N - 2, r["blocked"]   # the open line's end vertex is not checked
    assert any("corridor blocked at v" in f for f in r["fails"])


def test_a_seed_in_a_wall_is_an_input_error():
    d = _project(walls=_sealed_walls(), seed=_at(10, -EDGE))
    try:
        nr.run(d, "race_cw", verbose=False)
    except SystemExit as e:
        assert "seed" in str(e) and "wall" in str(e)
    else:
        raise AssertionError("a seed in a wall was filled from")


def test_a_reached_forbidden_probe_fails():
    bands = _bands(probes=[{"vertex": 50, "y": -3.0, "why": "pocket"},        # in the lane: reached
                           {"vertex": 60, "y": 4.0, "why": "pocket"}])        # behind the closure: not
    d = _project(walls=_sealed_walls(), bands=bands)
    r = nr.run(d, "race_cw", verbose=False)
    assert r["fail"] and r["leak_cells"] == 0
    assert r["forbidden_reached"] == [{"vertex": 50, "y": -3.0, "why": "pocket"}]


def test_a_version_1_declaration_uses_the_chain_face_and_a_free_end_leaks():
    v1 = {"version": 1, "params": {"barrier_half_m": BH, "edge_centre_from_lip_m": -0.485, "edge_inset_m": 0.82},
          "centre_w_by_vertex": [2 * BH] * N, "edge_strip_by_vertex": [1] * N, "edge_inset_by_vertex": [0.82] * N,
          "edge_corners": [], "closed_mouths": []}
    objs = [_prism("1WALL_race_edge_L", _band(EDGE)), _prism("1WALL_race_edge_R", _band(-EDGE)),
            _prism("1WALL_race_kbar", _band(0.0))]
    d = _project(walls=objs, bands=v1)
    (d / "data" / "track.race_cw.obj").rename(d / "data" / "track.race.obj")
    r = nr.run(d, "race_cw", verbose=False)
    assert r["declaration"].startswith("v1") and r["obj"] == "track.race.obj"
    assert r["fail"] is False, r["fails"]
    # the chain stops short of the end with a free end (the 0047 v780 / v4440 class)
    v1["centre_w_by_vertex"] = [2 * BH if k <= N - 20 else 0.0 for k in range(N)]
    objs[2] = _prism("1WALL_race_kbar", _band(0.0, 0, N - 20))
    d2 = _project(walls=objs, bands=v1)
    (d2 / "data" / "track.race_cw.obj").rename(d2 / "data" / "track.race.obj")
    r2 = nr.run(d2, "race_cw", verbose=False)
    assert r2["fail"] and any(x["class"] == "opposite" for x in r2["doors"]), r2["doors"]


def test_cli_exit_codes():
    d = _project(walls=_sealed_walls())
    assert nr.main([str(d), "--layout", "race_cw", "--planned"]) == 0
    a, b = _cut(_band(-EDGE), 30, 0.125, 0.875)
    d2 = _project(walls=_sealed_walls(edge_r=[a, b]))
    assert nr.main([str(d2), "--layout", "race_cw"]) == 1
    d3 = _project(walls=_sealed_walls(), seed=_at(10, -EDGE))
    assert nr.main([str(d3), "--layout", "race_cw"]) == 2


def _deck(name, y_lo, y_hi, h, k0=0, k1=N - 1):
    """a flat 1ROAD strip between laterals y_lo..y_hi at height h: (name, verts, tris)"""
    v, t = [], []
    for k in range(k0, k1 + 1):
        (xa, za), (xb, zb) = _at(k, y_lo), _at(k, y_hi)
        v += [(xa, h, za), (xb, h, zb)]
    for r in range(k1 - k0):
        a = 2 * r
        t += [(a, a + 1, a + 3), (a, a + 3, a + 2)]
    return name, v, t


def test_a_wall_on_a_pad_below_the_line_is_measured_from_the_pad():
    """ledger 0054 step 2e (MEASUREMENT-BUG FIX): a closure stretch standing on a pad 0.24 m below the line's deck
    reads [-0.24, +0.73] in the centreline frame — short of the 0.90 band top, a door. Measured from the pad it
    stands on it spans [0, 0.97] and seals. Without the pad in the OBJ it is still a door (no deck, centreline)."""
    pad_h = DECK - 0.24
    k0, k1 = 40, 60
    close = [_prism("1WALL_race_close_cw_a", _band(CLOSE, 0, k0)),
             _prism("1WALL_race_close_cw_pad", _band(CLOSE, k0, k1), y0=pad_h, y1=pad_h + 0.97),
             _prism("1WALL_race_close_cw_b", _band(CLOSE, k1, N - 1))]
    edges = [_prism("1WALL_race_edge_L", _band(EDGE)), _prism("1WALL_race_edge_R", _band(-EDGE))]
    bare = nr.run(_project(walls=edges + close), "race_cw", verbose=False)
    assert bare["fail"] and any(x["class"] == "opposite" for x in bare["doors"]), bare["doors"]
    assert bare["local_deck_cells"] == 0
    padded = edges + close + [_deck("1ROAD_pad", CLOSE - 2.0, CLOSE + 2.0, pad_h, k0 - 2, k1 + 2)]
    r = nr.run(_project(walls=padded), "race_cw", verbose=False)
    assert r["fail"] is False and r["leak_cells"] == 0, r["fails"]
    assert r["local_deck_cells"] > 0
    # step 2g: what sealed them — the wall on the pad, its deck 0.24 m under the line's, standing 0..0.97 m over it
    w = {x["object"]: x for x in r["local_deck_walls"]}
    pad = w["1WALL_race_close_cw_pad"]
    assert pad["cells"] > 0 and abs(pad["deck_minus_line_m"][0] + 0.24) < 1e-3 and abs(pad["deck_minus_line_m"][1] + 0.24) < 1e-3
    assert abs(pad["base_m"]) < 1e-3 and abs(pad["top_m"] - 0.97) < 1e-3 and k0 - 2 <= pad["vertices"][0] <= pad["vertices"][1] <= k1 + 2
    assert sum(x["cells"] for x in r["local_deck_walls"]) >= r["local_deck_cells"]
    # ...but a wall on ANOTHER road's deck (3 m under the line: the I-8 under a bridge) is not this line's wall: only
    # decks within DECK_REACH_M (0.70 = the band's own height) of the line's deck count
    low = DECK - 3.0
    far = [_prism("1WALL_race_close_cw_a", _band(CLOSE, 0, k0)),
           _prism("1WALL_freeway", _band(CLOSE, k0, k1), y0=low, y1=low + 0.97),
           _prism("1WALL_race_close_cw_b", _band(CLOSE, k1, N - 1)),
           _deck("1ROAD_freeway", CLOSE - 2.0, CLOSE + 2.0, low, k0 - 2, k1 + 2)]
    rf = nr.run(_project(walls=edges + far), "race_cw", verbose=False)
    assert rf["fail"] and rf["local_deck_cells"] == 0 and "local_deck_walls" not in rf


def test_walls_on_the_lines_own_deck_are_unchanged_by_the_deck_frame():
    """the second frame only ADDS: walls standing on a 1ROAD deck at the line's own height give the same cells"""
    walls = _sealed_walls()
    r0 = nr.run(_project(walls=walls), "race_cw", verbose=False)
    r1 = nr.run(_project(walls=walls + [_deck("1ROAD_main", -W / 2, W / 2, DECK)]), "race_cw", verbose=False)
    for key in ("wall_cells", "wall_tris_in_band", "reached_m2", "allowed_m2", "leak_cells", "door_clusters", "fail"):
        assert r0[key] == r1[key], key
    assert r1["local_deck_cells"] == 0

"""Ledger 0100: Milford to finished, round 1 (Kevin's answers of 2026-11-22). Every number here is re-derived from the
committed files: the 0.1.13 build's swept line (data/centerline.local.json, the PC's), the config, the vegetation files.

  1. T3's traced start 0.2 m off the lane: module 0 stands (the proxy reproduces the PC's own 0.214 m / 0.18 m over).
  2. The painted line as the start / finish: race_start on the measured lon/lat, the grid and pits as patterns, all forward.
  3. GrassFX at 6 m cells everywhere.
  4. The trunk colliders' reach derived from the barrier lines (20 m), trunks.json reproduced.
  5. mpg_nw_complex_0 stood with the set-in form (tools/author_bespoke_blend.far_roof_refusal, opt-in by row).
  6. The run-off pads shaded smooth with area-weighted normals (tools/pad_clip.area_normals, opt-in pads_shade).
stdlib + numpy only: bpy is stubbed where a Blender tool is imported.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MF = ROOT / "tracks" / "milford-road-course-lm"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from scripts.geometry import circuit_start as cs  # noqa: E402
import pad_clip as pc  # noqa: E402
import paint_shapes as ps  # noqa: E402

PAINT_LONLAT = (-83.667339, 42.568319)       # the furniture audit 2026-11-18, section 4.2


def _cfg():
    return json.loads((MF / "track.config.json").read_text(encoding="utf-8"))


def _local():
    return json.loads((MF / "data" / "centerline.local.json").read_text(encoding="utf-8"))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _author():
    for name in ("bpy", "mathutils", "mathutils.bvhtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = object
    sys.modules["mathutils.bvhtree"].BVHTree = object
    return _load(ROOT / "tools" / "author_bespoke_blend.py", "author_bespoke_blend_0100")


# --- 1. T3 --------------------------------------------------------------------------------------------------------------------

def _t3_modules(poly, dep=1.5, mod=0.62):
    """tools/author_bespoke_blend.rails' tyre modules, restated: 0.62 m modules from each segment's start, depth centred"""
    out = []
    for a, b in zip(poly, poly[1:]):
        seg = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
        nx, ny = -uy, ux
        for m in range(int(seg // mod)):
            x0, y0 = a[0] + ux * m * mod, a[1] + uy * m * mod
            x1, y1 = x0 + ux * (mod - 0.02), y0 + uy * (mod - 0.02)
            out.append([(x0 - nx * dep / 2, y0 - ny * dep / 2), (x1 - nx * dep / 2, y1 - ny * dep / 2),
                        (x1 + nx * dep / 2, y1 + ny * dep / 2), (x0 + nx * dep / 2, y0 + ny * dep / 2)])
    return out


def _outside_lane(line, ring):
    """each corner's distance outside the built lane edge (+ off the road), on the swept line +- half its width"""
    out = []
    for x, z in ring:
        s, la = line.project(x, z)
        out.append(abs(la) - line.width(s) / 2.0)
    return out


def test_t3_module_0_stands_after_the_move_and_the_proxy_reproduces_the_pc():
    loc, cfg = _local(), _cfg()
    line = cs.Line(loc["points_xyz_m"], loc["widths_m"])
    t3 = [r for r in cfg["scenery"]["bespoke"]["rails"] if r["key"] == "t3_s1000_apron_back"][0]
    assert t3["stand_on"] == ["CURB", "1KERB"] and t3["seat"] == "surface" and t3["depth_m"] == 1.5
    poly = [cs.lonlat_to_xz(loc["origin"], *p) for p in t3["polyline_lonlat"]]
    old = [cs.lonlat_to_xz(loc["origin"], -83.6662312, 42.5690387)] + poly[1:]
    assert 0.1995 <= math.dist(old[0], poly[0]) <= 0.2005
    m_old, m_new = _t3_modules(old), _t3_modules(poly)
    assert len(m_old) == len(m_new) == 51
    # the PC's 0.1.13 build (ledger 0091 rehearsals 2 / 3): module 0 0.18 m over the lane, module 1's corner 0.214 m off it
    assert abs(min(_outside_lane(line, m_old[0])) + 0.184) < 0.002
    assert abs(min(_outside_lane(line, m_old[1])) - 0.214) < 0.002
    new0 = min(_outside_lane(line, m_new[0]))
    assert 0.008 <= new0 <= 0.014                         # 0.011 m: module 0 off the lane, on the edge strip
    assert all(min(_outside_lane(line, r)) > new0 for r in m_new[1:])
    # drive_test's obstruction disc reaches w/2 - 0.1 m from the centre: the module stays outside it
    s0, _la = line.project(*m_new[0][0])
    assert min(_outside_lane(line, m_new[0])) > -0.1


# --- 2. the start / finish ----------------------------------------------------------------------------------------------------

def test_race_start_on_the_painted_line_all_forward():
    cfg, loc = _cfg(), _local()
    rs = cfg["race_start"]
    assert rs["line"]["lonlat"] == list(PAINT_LONLAT)
    pl = cs.plan(rs, loc)
    assert pl["problems"] == []
    assert abs(pl["line_station_m"] - 4639.86) < 0.05
    nodes = pl["nodes"]
    starts = sorted(n for n in nodes if n.startswith("AC_START_"))
    pits = sorted(n for n in nodes if n.startswith("AC_PIT_"))
    assert len(starts) == len(pits) == 20 and "AC_HOTLAP_START_0" in nodes
    line = cs.Line(loc["points_xyz_m"], loc["widths_m"])
    assert abs(line.ahead(nodes["AC_START_0"]["station_m"], pl["line_station_m"]) - 7.4) < 1e-6
    assert nodes["AC_START_0"]["lateral_m"] == -2.25                        # the right column (east) first
    # the whole grid inside the measured straight: within 2 deg of the line's own heading, 101.0 m behind it
    h0 = math.degrees(math.atan2(*line.tangent(pl["line_station_m"])))
    for n in starts:
        s = nodes[n]["station_m"]
        assert line.ahead(s, pl["line_station_m"]) <= 101.0
        assert abs(math.degrees(math.atan2(*line.tangent(s))) - h0) <= 2.0
    # every facing node faces the travel (engine-july's reflected yaw read about -1 on this north-south straight)
    dots = [cs.kn5_heading_dot(math.radians(v["yaw_deg"]), *v["travel"]) for v in nodes.values() if "travel" in v]
    assert len(dots) == 41 and min(dots) > 0.999


def test_the_painted_line_is_drawn_where_it_was_measured():
    cfg, loc = _cfg(), _local()
    items = cfg["route"]["paint"]
    assert [it["id"] for it in items] == ["sf_line"] and "surface" not in items[0]
    lines = ps.expand(items[0], loc["origin"], loc["points_xyz_m"])
    assert len(lines) == 1 and lines[0]["w"] == 1.0 and lines[0]["color"] == "white"
    (ax, az), (bx, bz) = lines[0]["pts"]
    assert abs(math.hypot(bx - ax, bz - az) - 10.5) < 0.01
    cx, cz = cs.lonlat_to_xz(loc["origin"], *PAINT_LONLAT)
    assert math.hypot((ax + bx) / 2 - cx, (az + bz) / 2 - cz) < 0.01
    line = cs.Line(loc["points_xyz_m"], loc["widths_m"])
    s, _la = line.project(cx, cz)
    tx, tz = line.tangent(s)
    assert abs(((bx - ax) * tx + (bz - az) * tz) / 10.5) < 1e-3           # square to the lap
    lat = sorted(line.project(x, z)[1] for x, z in lines[0]["pts"])
    assert abs(lat[0] + 4.88) < 0.02 and abs(lat[1] - 5.62) < 0.02        # the audit's -4.9 .. +5.6 m
    ship = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    d = ship["steps"]["draft"]
    assert d.index("kerbs") < d.index("paint") < d.index("ground_patch") and "paint" not in ship["steps"]["author"]


# --- 3. GrassFX ---------------------------------------------------------------------------------------------------------------

def test_grass_reads_every_cell_at_6_m():
    gz = _cfg()["scenery"]["bespoke"]["grassfx_zones"]
    assert gz["cell_m"] == 6 and "near" not in gz and gz["max_rects"] is None
    assert gz["pad_looks"] and gz["fade_by_map"] == {"B": 12} and gz["frame"] == "projection"


# --- 4. the collider reach ----------------------------------------------------------------------------------------------------

def test_trunk_reach_is_derived_from_the_barrier_lines_and_trunks_json_reproduces():
    pytest.importorskip("numpy")
    vtr = _load(MF / "source" / "vegetation" / "scripts" / "veg_trunks_reach.py", "veg_trunks_reach_0100")
    res = vtr.plan(MF)
    st = res["standoffs"]
    assert set(st) == {"g1_nw_corner_outside", "g2_front_straight_east", "g3_front_straight_west", "g4_infield_esses",
                       "t1_nw_hairpin_exit", "t2_esses_east_leg", "t3_s1000_apron_back"}      # no screen: site fences
    assert max(st, key=lambda k: st[k][1]) == "g4_infield_esses" and abs(st["g4_infield_esses"][1] - 19.07) < 0.01
    assert res["reach_m"] == 20.0
    tr = json.loads((MF / "source" / "vegetation" / "trunks.json").read_text(encoding="utf-8"))
    assert tr["reach_m"] == 20.0 and tr["points"] == res["trunks"] and len(tr["points"]) == 174
    assert min(p[3] for p in tr["points"]) >= 3.0                          # none within the corridor margin
    veg_plan = (MF / "source" / "vegetation" / "scripts" / "veg_plan.py").read_text(encoding="utf-8")
    assert "COLLIDER_REACH_M = 20.0" in veg_plan
    assert "20 m" in _cfg()["scenery"]["bespoke"]["trunks"]["_source"]


# --- 5. the set-in far block --------------------------------------------------------------------------------------------------

def test_far_roof_refusal_set_in_reads_the_downhill_face_and_nothing_else_moves():
    m = _author()
    # mpg_nw_complex_0 on 0.1.11's real ground: roof 25.91, highest built ground 25.72 (b0111 run 1), lowest 19.79, wall 5.11
    why = m.far_roof_refusal(25.91, 19.79, 25.72, 5.11)
    assert why == "its measured roof 25.91 stands 0.19 m over the highest ground under it (< half its 5.11 m wall)"
    assert m.far_roof_refusal(25.91, 19.79, 25.72, 5.11, set_in=True) is None
    assert m.far_roof_refusal(25.91, 19.79, 26.43, 5.11, set_in=True) is None   # its south-east corner cell, over the roof
    assert "downhill" in m.far_roof_refusal(21.0, 19.79, 25.72, 5.11, set_in=True)  # still refused: under half its wall
    assert m.far_roof_refusal(40.13, 33.0, 34.0, 6.3) is None                     # a far block that stood stands
    # opt-in by row: only Milford's mpg_nw_complex_0 is a far block carrying set_in, in every track's block files
    found = []
    for t in sorted((ROOT / "tracks").glob("*/track.config.json")):
        groups = ((json.loads(t.read_text(encoding="utf-8")).get("scenery") or {}).get("bespoke") or {}).get("blocks") or []
        for g in groups:
            f = t.parent / g["file"] if g.get("file") else None
            items = json.loads(f.read_text(encoding="utf-8")) if f and f.exists() else [g]
            found += [(t.parent.name, b["key"]) for b in items if isinstance(b, dict) and b.get("set_in") and b.get("off_terrain")]
    assert found == [("milford-road-course-lm", "mpg_nw_complex_0")]


# --- 6. the pads' shared corners ----------------------------------------------------------------------------------------------

def test_area_normals_ignore_a_sliver_and_match_a_plane():
    # a level 4 x 4 m square in two triangles, plus a 1 mm2 sliver standing vertical on its edge (a ground fold's cut)
    v = [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (4.0, 4.0, 0.0), (0.0, 4.0, 0.0), (2.0, 0.0, 0.0), (2.0, 0.0, 0.001)]
    f = [(0, 4, 2), (4, 1, 2), (0, 2, 3), (0, 4, 5)]
    n = pc.area_normals(v, f)
    assert all(abs(q[2] - 1.0) < 1e-3 for q in n[:5])                      # the sliver weighs nothing at the shared corners
    tilt = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.2)]
    (nx, ny, nz), = {pc.area_normals(tilt, [(0, 1, 2)])[i] for i in range(3)}
    assert abs(math.degrees(math.acos(nz)) - math.degrees(math.atan(0.1))) < 1e-9 and nx == 0.0
    assert pc.area_normals([(0.0, 0.0, 0.0)], []) == [(0.0, 0.0, 1.0)]


def test_pads_shade_is_opt_in_and_milford_only():
    src = (ROOT / "tools" / "seat_pads_blend.py").read_text(encoding="utf-8")
    assert 'smooth = bes.get("pads_shade") == "smooth"' in src and "shade_flat=not smooth" in src
    assert "normals_split_custom_set_from_vertices(pc.area_normals(" in src
    named = [t.parent.name for t in sorted((ROOT / "tracks").glob("*/track.config.json"))
             if '"pads_shade"' in t.read_text(encoding="utf-8")]
    assert named == ["milford-road-course-lm"]
    assert _cfg()["scenery"]["bespoke"]["pads_shade"] == "smooth"

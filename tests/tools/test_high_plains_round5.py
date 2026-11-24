"""High Plains round 5 (ledger 0097, 0.1.13): what NAIP left owed, read off the 2018 lidar's intensity (the G10,
tracks/high-plains-lm/source/edges/r5_lidar_g10/): the merge's east fillet behind the T13 kerb and its west corner, the north
loop's two blue / yellow stripes, and the 42 m of carried edges.

Every number the build gains is the lidar's or the 2023 photo's, or is marked [invented] where it is written down; the one
engine change (road_markings.gap_mouths_street_lines) is opt-in by a High Plains key and no other track declares it.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
HP = ROOT / "tracks" / "high-plains-lm"
FULL = HP / "source" / "full"
EDGES = HP / "source" / "edges"
G10 = EDGES / "r5_lidar_g10"
LINE = "full_north#0#0"
EAST, WEST = f"{LINE}|end|+1", f"{LINE}|end|-1"


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _cfg():
    return _j(HP / "track.config.json")


def _mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


# --- opt-in -----------------------------------------------------------------------------------------------------------
def test_version_and_no_other_track_declares_the_round5_key():
    assert _cfg()["version"] == "0.1.13"
    assert _cfg()["road_markings"]["gap_mouths_street_lines"] is True
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if p.parent.name == "high-plains-lm":
            continue
        assert not (_j(p).get("road_markings") or {}).get("gap_mouths_street_lines"), p.parent.name


def test_the_street_line_gap_runs_only_on_the_key():
    src = (ROOT / "tools" / "gap_mouths_blend.py").read_text(encoding="utf-8")
    assert 'if (cfg.get("road_markings") or {}).get("gap_mouths_street_lines") and ret_paint:' in src
    assert src.count("gap_street_paint(") == 2                       # its definition and that one call
    assert "def gap_street_paint(proj, ret_paint):" in src


def test_the_ground_seam_is_sand_creeks_existing_opt_in():
    s = _cfg()["strip_seam"]
    assert (s["scope"], s["connectors"]) == ("local", True)
    sc = _j(ROOT / "tracks" / "sand-creek-lm" / "track.config.json")["strip_seam"]
    assert (sc["scope"], sc["connectors"]) == ("local", True)         # the same keys, already shipped there (ledger 0086)
    assert "teeth" in s["_doc"]


# --- the G10's data, brought in as it is ------------------------------------------------------------------------------
def test_the_lidar_readings_are_the_g10s_files():
    for f in ("README.md", "merge_east_fillet.json", "north_stripes.json", "carried_edges.json", "hp_r5_lidar.py", "measure.log"):
        assert (G10 / f).exists(), f
    east = _j(G10 / "merge_east_fillet.json")["measured"]
    assert east["asphalt_edge_radius_m"] == 23.0 and east["fit"]["median_dev_m"] == 0.128 and not east["fit"]["at_grid_end"]
    assert east["leg_windows"]["R_min_max_m"] == [21.25, 23.0] and east["radius_along_the_outline"]["tightest_m"] == 13.8
    reg = _j(G10 / "carried_edges.json")["registration"]["fit"]
    assert reg["rows"] == 168 and reg["c_m"] == -0.49 and reg["shift_E_N_m"] == [-0.24, -0.04]


# --- items 1 and 4: the merge's two corners ----------------------------------------------------------------------------
def test_both_corners_are_the_lidars_tangent_fits():
    r = _cfg()["route"]
    assert r["mouth_returns"] == ["full_north"] and r["mouth_returns_measured_only"] is True
    assert r["mouth_radii_file"] == "source/edges/mouth_radii.r5.json"
    assert r["mouth_radii_file"] in _j(HP / "ship.json")["sync_in"]["required"]
    radii = _j(HP / r["mouth_radii_file"])["corners"]
    east, west = radii[EAST], radii[WEST]
    m = _j(G10 / "merge_east_fillet.json")["measured"]
    wc = _j(G10 / "carried_edges.json")["merge"]["west_corner"]
    assert (east["radius_m"], east["measured"], east["src"]) == (m["asphalt_edge_radius_m"], True, "lidar_2018")
    assert (west["radius_m"], west["measured"], west["src"]) == (wc["asphalt_edge_radius_m"], True, "lidar_2018")
    assert (east["radius_m"], west["radius_m"]) == (23.0, 6.75)
    assert east["host"] == west["host"] == "MAINLINE"
    assert "takes no outline" in east["outline"]                     # why the tangent fit, not the traced outline
    naip = _j(EDGES / "mouth_radii.naip.json")["corners"]            # round 4's record, kept
    assert naip[WEST]["radius_m"] == 14.0 and naip[EAST]["measured"] is False


def test_the_west_corner_is_settled_by_the_2023_photo():
    w = _j(EDGES / "west_corner_r5.json")
    rays = w["rays"]
    assert rays["n"] == rays["read"] == 23
    p6, p14 = rays["photo_minus_6_75_p10_p50_p90_m"], rays["photo_minus_14_0_p10_p50_p90_m"]
    assert abs(p6[1]) < 1.0 and p14[2] < -3.0                         # on the lidar's arc; every ray well inside round 4's
    reg = w["regions"]
    lane = reg["the West lap's lane"]["groundness_p10_p50_p90"][1]
    prairie = reg["the prairie 1.5-5 m past the 14.0 m arc"]["groundness_p10_p50_p90"][1]
    band = reg["between the 6.75 and 14.0 m arcs"]["groundness_p10_p50_p90"][1]
    assert abs(w["threshold_groundness"] - (lane + prairie) / 2) < 0.01
    assert band > w["threshold_groundness"]                           # between the arcs the photo reads ground
    assert w["R14_round4_built"]["R"] == 14.0 and "rebuild" in w["verdict"]


# --- item 2: the stripes ----------------------------------------------------------------------------------------------
def test_the_stripes_are_paint_runs_on_the_lidars_inner_side():
    K = _j(EDGES / "kerbs.lm.json")["kerbs"]
    st = [k for k in K if k.get("line") == LINE and k["profile"] == "paint"]
    assert len(st) == 2 and K[-2:] == st                              # after the lap's 20 and the north loop's 6 kerbs
    S = _j(G10 / "north_stripes.json")["stripes"]
    by = {round(k["s0"]): k for k in st}
    a, b = by[372], by[648]
    assert (a["in_m"], b["in_m"]) == (S["stripe372"]["in_m_photo_frame"], S["stripe648"]["in_m_photo_frame"]) == (-1.37, -1.6)
    for k in st:
        assert k["side"] == "left" and k["colour"] == "blue_yellow" and k["out_m"] == 0.0 and "out_m_invented" in k
    # the ends: the lidar's where the 2023 photo gives none, else the photo's
    assert (a["s0"], a["ends"]["s0"]) == (S["stripe372"]["s0_s1"][0], "lidar_2018") == (372.0, "lidar_2018")
    assert (a["s1"], a["ends"]["s1"]) == (400.0, "naip_2023_z18")
    assert (b["s0"], b["ends"]["s0"], b["s1"], b["ends"]["s1"]) == (648.0, "naip_2023_z18", 681.0, "naip_2023_z18")
    for k in st:     # each photo end is where the band's brightness steps in the recorded profile
        for e in ("s0", "s1"):
            if k["ends"][e] != "naip_2023_z18":
                continue
            prof = {float(s): v for s, v in k["ends"]["photo_profile_2023"][e].items()}
            inside = [v[0] for s, v in prof.items() if (s > k[e] + 0.75 if e == "s0" else s < k[e] - 0.75)]
            outside = [v[0] for s, v in prof.items() if (s < k[e] - 0.75 if e == "s0" else s > k[e] + 0.75)]
            p90_in = [v[1] for s, v in prof.items() if (s > k[e] if e == "s0" else s < k[e])]
            p90_out = [v[1] for s, v in prof.items() if (s < k[e] if e == "s0" else s > k[e])]
            assert np.median(inside) > np.median(outside) or np.median(p90_in) > np.median(p90_out) + 10, (k["s0"], e)


def test_the_stripes_edge_is_the_north_loops_built_lane_edge():
    conn = _j(FULL / "connectors.full.json")["connectors"][0]
    o = _j(HP / "data" / "centerline.local.json")["origin"]
    m_lon, m_lat = _mpd(o["lat"])
    P = np.array(conn["points_xyz_m"], float)
    W = np.array(conn["widths_m"], float)
    st = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2])))]
    s = np.arange(300.0, 720.0, 0.05)
    x, z, hw = np.interp(s, st, P[:, 0]), np.interp(s, st, P[:, 2]), np.interp(s, st, W) / 2
    tx, tz = np.gradient(x), np.gradient(z)
    L = np.hypot(tx, tz)
    ex, ez = x - tz / L * hw, z + tx / L * hw
    for k in (k for k in _j(EDGES / "kerbs.lm.json")["kerbs"] if k.get("line") == LINE and k["profile"] == "paint"):
        for lon, lat in k["edge_lonlat"]:
            px, pz = (lon - o["lon"]) * m_lon, (lat - o["lat"]) * m_lat
            assert np.min(np.hypot(ex - px, ez - pz)) < 0.05


def test_trace_north_kerbs_keeps_the_stripes():
    src = (EDGES / "trace_north_kerbs.py").read_text(encoding="utf-8")
    assert 'r.get("line") != LINE or r.get("profile") == "paint"' in src and 'K["kerbs"] += stripes' in src


# --- item 3: the carried edges ----------------------------------------------------------------------------------------
def test_the_carried_edges_are_read_or_have_no_edge():
    nl = _j(FULL / "north_loop.json")
    sm = nl["summary"]
    assert (sm["carried_m"], sm["no_edge_m"], sm["measured_m"]) == (0, 34, 968)
    rows = {r["s"]: r for r in nl["rows"]}
    lid = {r["row_s"]: r for r in _j(G10 / "carried_edges.json")["l254_260"]["rows"]}
    for s in (254.0, 256.0, 258.0, 260.0):        # seated on the lidar (NAIP's definition: less c and the shift)
        assert rows[s]["width"] == "measured_lidar" and rows[s]["photo"] == "lidar_2018"
        assert rows[s]["left_m"] == lid[s]["off_osm_naip_def_m"]
    ne = [r for r in nl["rows"] if r["width"] == "no_edge"]
    assert ne and all(r["no_edge"] == ["right"] and (r["s"] <= 19.0 or r["s"] >= 988.0) for r in ne)
    assert {r["s"] for r in ne} == {s for s in rows if s <= 19.0 or s >= 988.0}
    outl = {r["s"]: r["lidar_left_m"] for r in nl["rows"] if "lidar_left_m" in r}
    merge = {r["row_s"]: r["off_osm_shift_only_m"] for r in _j(G10 / "carried_edges.json")["merge"]["rows"]
             if r["side"] == "left" and r["row_s"] >= 996}
    assert outl == {s: round(v, 2) for s, v in merge.items()}         # the east corner's outline, kept as a record
    apex = _j(G10 / "carried_edges.json")["fork_r0_19"]["gore_nose"]["apex"]
    assert 19.0 < apex["north_own_s"] < 20.0                         # the gore's grass begins past the no-edge rows


def test_measure_north_and_make_connectors_reproduce_the_committed_files():
    z18 = ROOT / "tracks" / "high-plains" / "source" / "naip_2023_hp_z18.png"
    if z18.stat().st_size < 4096:
        pytest.skip("the z18 photo is an LFS pointer here (git lfs pull reads it)")
    sys.path.insert(0, str(FULL))
    import measure_north as mn
    import make_connectors as mc
    conn, rows, summ = mn.measure(ROOT)
    nl = _j(FULL / "north_loop.json")
    assert rows == nl["rows"] and conn == nl["connectors"][0]
    assert json.loads(json.dumps(summ)) == nl["summary"]
    assert mc.build(nl) == _j(FULL / "connectors.full.json")


def test_the_ledger_carries_round5_and_its_runbook():
    text = (ROOT / "fleet" / "feedback" / "0097-high-plains-to-finished.md").read_text(encoding="utf-8")
    assert "## Round 5 (0.1.13" in text and "### Runbook 0097-5 (PC)" in text and "Still to do (round 6)" in text

"""High Plains round 4 (ledger 0097, 0.1.12): the north loop's kerbs, its carried edges read again, road wear's aerial over the
north loop, the merge's measured bellmouth, the traced white building's measured shed.

Every number the build gains is read off a photo or the 2018 lidar; every engine change is opt-in by a High Plains key and no
other track declares any of it.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import circuit_facades as cf  # noqa: E402

HP = ROOT / "tracks" / "high-plains-lm"
FULL = HP / "source" / "full"
EDGES = HP / "source" / "edges"
LINE = "full_north#0#0"


def _cfg():
    return json.loads((HP / "track.config.json").read_text(encoding="utf-8"))


def _ship():
    return json.loads((HP / "ship.json").read_text(encoding="utf-8"))


def _kerbs():
    return json.loads((EDGES / "kerbs.lm.json").read_text(encoding="utf-8"))["kerbs"]


def _mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


# --- opt-in ------------------------------------------------------------------------------------------------------------
def test_version_and_no_other_track_declares_any_round4_key():
    assert _cfg()["version"] == "0.1.12"
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):
        t = p.parent.name
        if t == "high-plains-lm":
            continue
        c = json.loads(p.read_text(encoding="utf-8"))
        assert not (c.get("route") or {}).get("mouth_returns_measured_only"), t
        rel = (c.get("route") or {}).get("kerbs_file")
        if rel and (p.parent / rel).exists():
            assert not any(r.get("line") for r in json.loads((p.parent / rel).read_text(encoding="utf-8"))["kerbs"]), t
    for f in sorted((ROOT / "tracks").glob("*/source/bespoke/*.json")):
        if f.parent.parent.parent.name == "high-plains-lm":
            continue
        rows = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(rows, list):
            assert not any(isinstance(r, dict) and r.get("atlas_shed") for r in rows), f


def test_the_engine_pieces_are_written_down_where_they_run():
    ak = (ROOT / "tools" / "author_kerbs_blend.py").read_text(encoding="utf-8")
    assert 'cur[0] = run.get("line") or "MAINLINE"' in ak and "not a line of this build" in ak
    ab = (ROOT / "tools" / "author_bespoke_blend.py").read_text(encoding="utf-8")
    assert 'atlas_shed = bool(atlas and form == "shed" and b.get("atlas_shed") and not set_in)' in ab
    assert 'if atlas and ((form == "shed" and not atlas_shed) or form == "posts" or set_in):' in ab   # refused as before
    mrb = (ROOT / "tools" / "mouth_returns_blend.py").read_text(encoding="utf-8")
    assert 'measured_only = bool((cfg.get("route") or {}).get("mouth_returns_measured_only"))' in mrb
    assert 'if measured_only and src != "measured":' in mrb


# --- item 3: road wear's aerial ---------------------------------------------------------------------------------------
def test_road_wear_reads_the_mosaic_whose_bottom_rows_are_the_crop():
    from PIL import Image
    a = _cfg()["road_wear"]["aerial"]
    rec = json.loads((HP / "source" / "road_wear" / "naip_2023_hp_mosaic.json").read_text(encoding="utf-8"))
    W, N, E, S = rec["corners"]
    assert a["image"] == "source/road_wear/naip_2023_hp_mosaic.png" and a["bbox_lonlat"] == [W, S, E, N]
    assert a["image"] in _ship()["sync_in"]["required"]
    crop_meta = json.loads((HP / "source" / "road_wear" / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    cw, cn, ce, cs = crop_meta["corners"]
    assert (W, E, S) == (cw, ce, cs) and N > cn
    M = np.asarray(Image.open(HP / a["image"]).convert("RGB"))
    C = np.asarray(Image.open(HP / "source" / "road_wear" / "naip_2023_030_hp.png").convert("RGB"))
    k0, k1 = rec["crop_rows"]
    assert M.shape == (rec["h"], rec["w"], 3) and k1 == M.shape[0] and np.array_equal(M[k0:k1], C)   # the crop unchanged
    assert abs((N - S) / M.shape[0] - (cn - cs) / C.shape[0]) < 1e-12                                # on its own lattice
    assert rec["registration"]["z18_shift_m"] == [0.0, 0.0] and rec["registration"]["ncc_best"] > 0.85
    # every point of the north loop reads a photo pixel, none the black outside the corridor
    o = json.loads((HP / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    m_lon, m_lat = _mpd(o["lat"])
    conn = json.loads((FULL / "connectors.full.json").read_text(encoding="utf-8"))["connectors"][0]
    for p in conn["points_xyz_m"]:
        lon, lat = o["lon"] + p[0] / m_lon, o["lat"] + p[2] / m_lat
        i, j = int((lon - W) / (E - W) * M.shape[1]), int((N - lat) / (N - S) * M.shape[0])
        assert M[j, i].sum() > 0, p


# --- item 4: the white building's shed ---------------------------------------------------------------------------------
def _ring_xy(row, o):
    m_lon, m_lat = _mpd(o["lat"])
    return [((lo - o["lon"]) * m_lon, (la - o["lat"]) * m_lat) for lo, la in row["footprint_lonlat"]]


def test_the_white_building_is_the_2018_lidars_one_plane():
    rows = {r["key"]: r for r in json.loads((HP / "source" / "bespoke" / "buildings.race.json").read_text(encoding="utf-8"))}
    d = rows["traced_white_w_of_osm289311820"]
    assert (d["form"], d["atlas_shed"], d["wall_h_m"], d["ridge_h_m"]) == ("shed", True, 2.92, 3.79)
    pl = d["plane"]
    assert (pl["h_m"], pl["gx"], pl["gy"]) == (3.35, 0.0285, 0.0864) and pl["ref_lonlat"] == [-103.8946219, 39.7354656]
    assert d["_h"].startswith("measured: the 2018 lidar") and "gable" in d["_form_2023"]
    o = json.loads((HP / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    m_lon, m_lat = _mpd(o["lat"])
    rx, ry = (pl["ref_lonlat"][0] - o["lon"]) * m_lon, (pl["ref_lonlat"][1] - o["lat"]) * m_lat
    tops = [pl["h_m"] + pl["gx"] * (x - rx) + pl["gy"] * (y - ry) for x, y in _ring_xy(d, o)]
    assert abs(min(tops) - d["wall_h_m"]) < 0.05 and abs(max(tops) - d["ridge_h_m"]) < 0.05   # the lidar's low / high corner
    others = [r for k, r in rows.items() if k != "traced_white_w_of_osm289311820"]
    assert not any(r.get("atlas_shed") for r in others)


def test_facade_walls_carry_every_bay_up_to_the_plane():
    ring = [(0.0, 0.0), (11.0, 0.0), (11.0, 7.0), (0.0, 7.0)]
    tops = [3.0 + 0.1 * y for _x, y in ring]                       # rising 0.7 m to the north
    plain = cf.facade_walls(ring, "garage", 0.0, 0.0, 3.0, (0.0, -1.0))
    v, f, uv, info = cf.facade_walls(ring, "garage", 0.0, 0.0, min(tops), (0.0, -1.0), shed_tops=tops)
    n0 = len(plain[0])
    assert v[:n0] == plain[0] and f[:len(plain[1])] == plain[1]   # the walls up to the low eave as without the plane
    # 3 + 2 + 3 + 2 bays; the south wall's 3 stand at the low eave (no face above them), the others rise to the plane
    assert info["bays"] == 10 and info["shed_faces"] == 7
    assert abs(max(p[2] for p in v) - max(tops)) < 1e-9 and min(p[2] for p in v) == 0.0
    for p in v[n0:]:                                               # every raised vertex lies on the plane, on the ring's edge
        assert abs(p[2] - (3.0 + 0.1 * p[1])) < 1e-9
    assert len(f) == len(uv) and all(len(a) == len(b) for a, b in zip(f, uv))
    assert cf.facade_walls(ring, "garage", 0.0, 0.0, 3.0, (0.0, -1.0), shed_tops=None) == plain      # absent = as before


# --- item 1: the north loop's kerbs -----------------------------------------------------------------------------------
def test_the_north_loops_kerbs_are_measured_runs_on_its_own_rows():
    K = _kerbs()
    lap, north = [k for k in K if not k.get("line")], [k for k in K if k.get("line")]
    assert len(lap) == 20 and len(north) == 6 and K[:20] == lap      # the lap's 20 first, unchanged in order
    assert all(k["line"] == LINE and k["colour"] == "blue_white" and k["profile"] == "kerb" for k in north)
    for k in north:
        r = k["reader"]
        assert r["block_amp_median"] >= 8.0 and r["followed"] is True     # kerb_offsets' MIN_AMP; --follow 1
        assert k["in_m"] < k["out_m"] and 1.2 <= k["out_m"] - k["in_m"] <= 2.1
        assert abs(k["in_m"] - k["colour_read"]["in_m"]) <= 0.5 and abs(k["out_m"] - k["colour_read"]["out_m"]) <= 0.5
        assert len(k["edge_lonlat"]) >= 2 and 0.0 <= k["s0"] < k["s1"] <= 1001.0
    spans = sorted((k["side"], round(k["s0"]), round(k["s1"])) for k in north)
    assert spans == [("left", 170, 216), ("left", 733, 761), ("left", 983, 990), ("right", 57, 98), ("right", 308, 335),
                     ("right", 546, 638)]
    assert _cfg()["route"]["kerbs_file"] == "source/edges/kerbs.lm.json"


def test_t13s_piece_on_ladder_ends_where_the_wests_t13_run_begins():
    sys.path.insert(0, str(EDGES))
    import trace_north_kerbs as tn
    import kerb_offsets as ko
    tn.ko = ko
    conn = json.loads((FULL / "connectors.full.json").read_text(encoding="utf-8"))["connectors"][0]
    origin = json.loads((HP / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    K = json.loads((EDGES / "kerbs.lm.json").read_text(encoding="utf-8"))
    end = tn.t13_end(conn, K, origin)
    t13 = next(k for k in K["kerbs"] if k.get("line") and k["side"] == "left" and k["s0"] > 900)
    assert t13["s1"] == end and 985.0 < end < 995.0
    assert "L:982.8-{t13}:blue_white:eye" in tn.SPANS


# --- item 5: the carried edges, read again -----------------------------------------------------------------------------
def test_the_carried_rows_are_read_again_and_what_is_left_is_the_mouths():
    sys.path.insert(0, str(FULL))
    import measure_north as mn
    nl = json.loads((FULL / "north_loop.json").read_text(encoding="utf-8"))
    sm = nl["summary"]
    assert sm["second_read"]["measured_m"] == 150 and sm["carried_m"] == 42 and sm["measured_m"] == 960
    for side, d in sm["second_read"]["per_side"].items():
        for photo, (off, n) in d["line_to_edge_m"].items():
            assert 0.2 <= off <= 0.5 and n >= 50, (side, photo)
    second = [r for r in nl["rows"] if r["width"] == "measured_second_read"]
    assert second and all(any(a <= r["s"] <= b for _sd, a, b, *_ in mn.SECOND_READ) for r in second)
    carried = [r["s"] for r in nl["rows"] if r["width"] == "carried"]
    mouths = [(a, b) for _sd, a, b, _w in mn.NOT_READ]
    left = [s for s in carried if not any(a <= s <= b for a, b in mouths)]
    assert left and all(254.0 <= s <= 260.0 for s in left)           # the one stretch no second reading survived
    lo, hi = sm["width_measured_m"][0], sm["width_measured_m"][-1]
    assert all(lo - 0.6 <= r["width_m"] <= hi + 0.6 for r in nl["rows"])
    assert {r["width"] for r in nl["rows"]} == {"measured", "measured_second_read", "carried"}


# --- item 2: the merge ------------------------------------------------------------------------------------------------
def test_the_merges_bellmouth_is_a_measured_return_and_the_kerb_corner_is_not_invented():
    c = _cfg()
    r = c["route"]
    assert r["mouth_returns"] == ["full_north"] and r["mouth_returns_measured_only"] is True
    assert r["verify_mouth_corners"] is True and c["road_markings"]["gap_mouths"] is True
    radii = json.loads((HP / r["mouth_radii_file"]).read_text(encoding="utf-8"))["corners"]
    west, east = radii[f"{LINE}|end|-1"], radii[f"{LINE}|end|+1"]
    assert west["measured"] is True and west["radius_m"] == 14.0 and west["contrast"] >= 12.0 and west["prominence"] >= 1.4
    assert east["measured"] is False and "grid's end" in east["why"]
    s = _ship()
    d = s["steps"]["draft"]
    assert d.index("lm_pads") < d.index("mouth_returns") < d.index("strip_seam") < d.index("gap_mouths") < d.index("kerbs")
    g = s["steps"]["gate"]
    assert g.index("verify_mouths") < g.index("verify_mouth_corners")
    assert r["mouth_radii_file"] in s["sync_in"]["required"]


def test_the_gates_changelog_names_the_round():
    text = (ROOT / "fleet" / "GATES-CHANGELOG.md").read_text(encoding="utf-8")
    assert "ledger 0097 round 4" in text and "verify_mouth_corners" in text

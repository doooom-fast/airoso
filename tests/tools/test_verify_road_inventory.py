"""tools/verify_road_inventory.py — the Lariat's Drive-1 road inventory (V3-PLAN P5, ledger 0048), on synthetic
built OBJs whose truth is known:

- forbidden meshes: HIGHWAY* / HWYSTRUCT* / MOUNTAINS* fail, with or without a physics prefix; a clean road passes;
- pavement off the route fails; the same slab inside a declared exemption polygon passes (lon/lat or OBJ frame); an
  exemption with no polygon exempts nothing; a name_and_footprint exemption exempts only its own object's group;
  the margin is half-width + 2 m (a slab 1.5 m past the edge passes, 2.5 m fails);
- the pavement is the lap: a 10 m hole in a 200 m road fails, a 1 m hole passes (1 %);
- a malformed exemption file is an input error (exit 2), and the kn5 route (--kn5) reads the same answer.
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
import verify_road_inventory as vri  # noqa: E402
from scripts.geometry import ribbon  # noqa: E402
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

W = 7.0
LON0, LAT0 = -105.2, 39.7


def _write_obj(path: Path, groups) -> None:
    lines, base = [], 1
    for name, mesh in groups:
        lines.append(f"o {name}")
        for x, y, z in mesh["vertices"]:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for _ in mesh["vertices"]:
            lines.append("vt 0 0")
        for a, b, c in mesh["tris"]:
            lines.append(f"f {base+a}/{base+a} {base+b}/{base+b} {base+c}/{base+c}")
        base += len(mesh["vertices"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _slab(x0, x1, z0, z1, y=0.0):
    return {"vertices": [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], "tris": [(0, 1, 2), (0, 2, 3)]}


def _road(z0=-100.0, z1=100.0, hole=None):
    cl = [(0.0, 0.0, float(z)) for z in range(int(z0), int(z1) + 1)]
    r = ribbon.road_ribbon(cl, [W] * len(cl))
    if hole:
        a, b = hole
        keep = []
        for t in r["tris"]:
            zc = sum(r["vertices"][k][2] for k in t) / 3.0
            if not (a < zc < b):
                keep.append(t)
        r = {"vertices": r["vertices"], "tris": keep}
    return r


def _project(groups, exemptions=None, layouts=None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = {"slug": "t", "mirror_x": False}
    if layouts:
        cfg["layouts"] = layouts
    (d / "track.config.json").write_text(json.dumps(cfg))
    cl = [[0.0, 0.0, float(z)] for z in range(-100, 101, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": cl, "widths_m": [W] * len(cl), "origin": {"lon": LON0, "lat": LAT0, "elev_m": 0.0}}))
    _write_obj(d / "data" / "track.obj", groups)
    if exemptions is not None:
        (d / "pavement_exemptions.json").write_text(json.dumps(exemptions))
    return d


def test_clean_road_passes_and_the_lap_is_paved():
    r = vri.run(_project([("1ROAD_main", _road()), ("1GRASS", _slab(-40, 40, -110, 110, -0.05))]))
    assert r["fail"] is False, r
    assert r["forbidden_meshes"] == 0 and r["off_route_tris"] == 0 and r["pavement_tris"] > 0
    assert r["lap"]["None"]["pass"] and r["lap"]["None"]["ratio"] == 1.0 and r["lap"]["None"]["paved_m"] == 200.0


def test_forbidden_meshes_fail_with_or_without_a_physics_prefix():
    for bad in ("HIGHWAY_c470", "HWYSTRUCT_bridge", "MOUNTAINS", "1ROAD_HIGHWAY_i70", "mountains_far"):
        r = vri.run(_project([("1ROAD_main", _road()), (bad, _slab(500, 600, 0, 50, 30))]))
        assert r["fail"] and r["forbidden_meshes"] == 1 and r["forbidden_names"] == [bad], (bad, r)
    for fine in ("1ROAD_main_highway_view", "AUTH_overpass_c470_us6", "GRASS_mountain"):
        r = vri.run(_project([("1ROAD_main", _road()), (fine, _slab(500, 600, 0, 50, 30))]))
        assert r["forbidden_meshes"] == 0, (fine, r["forbidden_names"])


def test_pavement_off_the_route_fails_and_the_margin_is_half_width_plus_2m():
    edge = W / 2
    near = vri.run(_project([("1ROAD_main", _road()), ("1ROAD_apron", _slab(edge, edge + 1.5, 0, 10))]))
    assert near["fail"] is False and near["off_route_tris"] == 0, near
    far = vri.run(_project([("1ROAD_main", _road()), ("1ROAD_apron", _slab(edge, edge + 2.5, 0, 10))]))
    assert far["fail"] and far["off_route_tris"] == 2 and far["off_route_by_group"] == {"1ROAD_apron": 2}
    worst = far["worst_off_route"][0]
    assert abs(worst["beyond_m"] - 0.5) < 1e-6 and 0 <= worst["nearest_station_m"] <= 200


def _lot_exemption(poly_key, poly, obj="AUTH_lot_test", match="footprint", eid="lot"):
    return {"pavement_prefixes": ["1ROAD", "AUTH_OVERPASS"],
            "exemptions": [{"id": eid, "object": obj, "match": match, poly_key: poly}]}


def test_an_exemption_polygon_covers_declared_pavement_in_either_frame():
    groups = [("1ROAD_main", _road()), ("1ROAD_lot", _slab(20, 40, 0, 20))]
    bare = vri.run(_project(groups))
    assert bare["fail"] and bare["off_route_tris"] == 2
    xz = vri.run(_project(groups, _lot_exemption("polygon_xz", [[18, -2], [42, -2], [42, 22], [18, 22]])))
    assert xz["fail"] is False and xz["exemptions_used"] == {"lot": 2}, xz
    mlon, mlat = _meters_per_degree(LAT0)
    ll = [[LON0 + x / mlon, LAT0 + z / mlat] for x, z in ((18, -2), (42, -2), (42, 22), (18, 22))]
    lonlat = vri.run(_project(groups, _lot_exemption("polygon_lonlat", ll)))
    assert lonlat["fail"] is False and lonlat["exemptions_used"] == {"lot": 2}, lonlat
    # a polygon that covers only part of the slab exempts only what it covers: the rest still fails
    half = vri.run(_project(groups, _lot_exemption("polygon_xz", [[18, -2], [30, -2], [30, 22], [18, 22]])))
    assert half["fail"] and half["off_route_tris"] == 2


def test_an_unmeasured_or_inactive_exemption_exempts_nothing():
    groups = [("1ROAD_main", _road()), ("1ROAD_lot", _slab(20, 40, 0, 20))]
    ex = {"exemptions": [{"id": "lot", "object": "AUTH_lot", "polygon_lonlat": []},
                         {"id": "d2b", "object": "AUTH_route_d2b", "active": False,
                          "polygon_xz": [[18, -2], [42, -2], [42, 22], [18, 22]]}]}
    r = vri.run(_project(groups, ex))
    assert r["fail"] and r["off_route_tris"] == 2
    assert r["exemptions_unmeasured"] == ["lot"] and r["exemptions_inactive"] == ["d2b"]


def test_name_and_footprint_exempts_only_the_named_object():
    poly = [[18, -2], [42, -2], [42, 22], [18, 22]]
    ex = _lot_exemption("polygon_xz", poly, obj="AUTH_overpass_c470_us6", match="name_and_footprint", eid="deck")
    named = vri.run(_project([("1ROAD_main", _road()), ("AUTH_overpass_c470_us6_deck", _slab(20, 40, 0, 20, 6))], ex))
    assert named["fail"] is False and named["exemptions_used"] == {"deck": 2}, named
    other = vri.run(_project([("1ROAD_main", _road()), ("1ROAD_carpark", _slab(20, 40, 0, 20))], ex))
    assert other["fail"] and other["off_route_tris"] == 2
    # the deck is pavement only because the file says so: without the prefix it is not judged at all
    ex2 = dict(ex, pavement_prefixes=["1ROAD"])
    unjudged = vri.run(_project([("1ROAD_main", _road()), ("AUTH_overpass_x", _slab(20, 40, 0, 20, 6))], ex2))
    assert unjudged["fail"] is False and unjudged["pavement_groups"] == 1


def test_the_pavement_is_the_lap_within_one_percent():
    big = vri.run(_project([("1ROAD_main", _road(hole=(40.0, 50.0)))]))
    assert big["fail"] and not big["lap"]["None"]["pass"]
    assert 0.94 < big["lap"]["None"]["ratio"] < 0.97 and big["lap"]["None"]["unpaved_runs"]
    small = vri.run(_project([("1ROAD_main", _road(hole=(40.0, 41.0)))]))
    assert small["lap"]["None"]["pass"] and small["fail"] is False, small["lap"]
    # every declared layout is walked (a layout's own centerline file when it names one)
    lo = [{"id": "street_full", "direction": "forward"}, {"id": "street_reverse", "direction": "reverse"}]
    r = vri.run(_project([("1ROAD_main", _road())], layouts=lo))
    assert set(r["lap"]) == {"street_full", "street_reverse"} and all(v["pass"] for v in r["lap"].values())


def test_a_bad_exemption_file_is_an_input_error():
    groups = [("1ROAD_main", _road())]
    for ex in ({"exemptions": [{"id": "x", "object": "pad_C1", "polygon_xz": []}]},          # not AUTH_*
               {"exemptions": [{"id": "x", "object": "AUTH_a"}, {"id": "x", "object": "AUTH_b"}]},  # duplicate id
               {"exemptions": [{"id": "x", "object": "AUTH_a", "match": "nearby"}]}):
        d = _project(groups, ex)
        try:
            vri.run(d)
        except vri.InputError:
            pass
        else:
            raise AssertionError(f"accepted {ex}")
        assert vri.main([str(d)]) == 2
    nothing = Path(tempfile.mkdtemp())
    (nothing / "track.config.json").write_text("{}")
    assert vri.main([str(nothing)]) == 2                      # no OBJ: never a pass


def test_the_cli_reads_a_kn5_like_the_obj():
    from scripts.ac.kn5_write import build
    # symmetric about z = 0, so the gate OBJ's z mirror (kn5 -> engine frame) lands the road on itself
    d = _project([("1ROAD_main", _road()), ("HIGHWAY_c470", _slab(500, 600, -20, 20, 30))])
    kn5 = build(d)
    out = d / "data" / "inv.json"
    assert vri.main([str(d), "--kn5", str(kn5), "--out", str(out)]) == 1
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["forbidden_names"] == ["HIGHWAY_c470"] and r["off_route_tris"] == 0 and r["lap"]["None"]["pass"]
    assert ".kn5" in r["obj"]


def test_the_lariat_exemption_file_loads_and_declares_the_plans_list():
    p = ROOT / "tracks" / "lookout-lariat" / "pavement_exemptions.json"
    ex = vri.load_exemptions(p, None)
    d = json.loads(p.read_text(encoding="utf-8"))
    ids = [e["id"] for e in d["exemptions"]]
    for need in ("c1_pad", "mouth_c12", "mouth_c14", "mouth_c15", "mouth_c16", "mouth_c18", "side_road_stubs",
                 "windy_saddle_lot", "overlook_1", "lid", "c470_deck_colfax", "c470_deck_us6", "d2_slab_exit259",
                 "d2_slab_colfax", "d2_slab_us6_offramp", "d2_slab_nineteenth", "d2b_reverse_route"):
        assert need in ids, need
    assert all(e["object"].startswith("AUTH_") for e in d["exemptions"])
    assert ex["inactive"] == ["d2b_reverse_route"]                       # Kevin chose D2 (a)
    assert ex["polys"] == [] and len(ex["unmeasured"]) == len(ids) - 1   # nothing authored yet: nothing exempt
    assert {e["match"] for e in d["exemptions"] if e["id"].startswith("c470")} == {"name_and_footprint"}

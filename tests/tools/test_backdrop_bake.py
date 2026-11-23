"""Ledger 0096, the shared Front Range backdrop: tools/backdrop_bake.py (the bake) and tools/backdrop_peak_gate.py (its
gate), on an analytic surface, so every expected number here comes from a formula and not from the bake. numpy only."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


bb = _load("backdrop_bake")
pg = _load("backdrop_peak_gate")

O = (-104.9853, 39.7401)          # an origin at Denver's latitude
E0 = 1600.0
K = 0.13
SITE = "synthetic start"


def _at(bearing_deg, dist_m):
    a = math.radians(bearing_deg)
    return dist_m * math.sin(a), dist_m * math.cos(a)


HILL = _at(270.0, 19000.0)        # 300 m hill behind the ridge: hidden from the road
PEAK = _at(265.0, 35000.0)        # 2,600 m peak far behind it: seen over the ridge


def surface(x, z):
    """A plain, a 600 m ridge ringing the origin 15 km out, a hill hidden behind it, a far peak over it."""
    d = np.hypot(x, z)
    return (E0 + 600.0 * np.exp(-((d - 15000.0) / 1500.0) ** 2)
            + 300.0 * np.exp(-(np.hypot(x - HILL[0], z - HILL[1]) / 800.0) ** 2)
            + 2600.0 * np.exp(-(np.hypot(x - PEAK[0], z - PEAK[1]) / 2000.0) ** 2))


class Synth:
    def elev(self, lon, lat):
        shape = np.shape(lon)
        x, z = bb.to_local(O[0], O[1], np.ravel(lon), np.ravel(lat))
        return surface(x, z).reshape(shape)


PARAMS = {"arc_deg": [240.0, 300.0], "near_m": 3000.0, "far_m": 40000.0, "pixel_rad": 0.004, "min_cell_m": 40.0,
          "radial_factor": 2.0, "viewshed_eye_m": 2.0, "viewshed_margin_deg": 0.05, "viewshed_margin_cells": 1,
          "viewpoint_spacing_m": 100.0, "blocker_min_m": 2000.0, "max_verts_per_object": 700}
ROAD = [(O[0], O[1]), (O[0] + 0.002, O[1]), (O[0] + 0.002, O[1] + 0.002)]
_BAKED = {}


def baked():
    if not _BAKED:
        _BAKED.update(bb.bake(PARAMS, O, ROAD, Synth(), E0))
    return _BAKED


def _all(res):
    V = np.concatenate([o["v"] for o in res["objects"]]); N = np.concatenate([o["vn"] for o in res["objects"]])
    return V, N


def _horizon():
    """What the study would say of the two summits, from the formulas alone."""
    out = {}
    for name, (px, pz), vis in (("Far Peak", PEAK, True), ("Hidden Hill", HILL, False)):
        d = math.hypot(px, pz); top = float(surface(np.array([px]), np.array([pz]))[0])
        lon, lat = bb.geod_direct(O[0], O[1], math.degrees(math.atan2(px, pz)) % 360, d)
        alt = math.degrees(math.atan2(top - (E0 + 1.2) - d * d * (1 - K) / (2 * 6371000.0), d))
        out[name] = {"bearing_deg": math.degrees(math.atan2(px, pz)) % 360, "distance_km": d / 1000, "summit_dem_m": top,
                     "summit_lon_lat": [float(lon), float(lat)], "nominal_lon_lat": [float(lon), float(lat)], "altitude_deg": alt, "visible": vis,
                     "clearance_deg": 1.0 if vis else -1.0}
    return {"site_ground_m": {SITE: E0}, "peaks": {SITE: out}, "sites": {}, "summit_box_half_deg": [0.008, 0.006]}


def _write(res, d, name="t_backdrop.obj"):
    p = Path(d) / name
    bb.write_obj(p, res["objects"])
    return p


def test_geodesy_matches_vincentys_published_line_and_round_trips():
    # Flinders Peak -> Buninyong (Geoscience Australia's worked example, GRS80; WGS84 differs by under a millimetre)
    lat1 = -(37 + 57 / 60 + 3.72030 / 3600); lon1 = 144 + 25 / 60 + 29.52440 / 3600
    lat2 = -(37 + 39 / 60 + 10.15610 / 3600); lon2 = 143 + 55 / 60 + 35.38390 / 3600
    az, s = bb.geod_inverse(lon1, lat1, lon2, lat2)
    assert abs(s[0] - 54972.271) < 0.01
    assert abs(az[0] - (306 + 52 / 60 + 5.37 / 3600)) < 1e-5
    lo, la = bb.geod_direct(lon1, lat1, az[0], s[0])
    assert abs(float(lo) - lon2) < 1e-8 and abs(float(la) - lat2) < 1e-8
    az2, s2 = bb.geod_inverse(O[0], O[1], *bb.geod_direct(O[0], O[1], np.array([182.9, 253.5, 317.1]), np.array([100200.0, 58800.0, 78500.0])))
    assert np.allclose(az2, [182.9, 253.5, 317.1], atol=1e-7) and np.allclose(s2, [100200.0, 58800.0, 78500.0], atol=1e-3)


def test_lattice_cell_grows_with_distance_and_bands_share_their_edges():
    p = dict(bb.DEFAULTS)
    rings, n0 = bb.lattice(p)
    step = math.radians(155.0) / n0
    assert abs(60000 * step - 60.0) < 0.5                           # one pixel at 60 km is about 60 m
    assert rings[0]["r"] == p["near_m"] and abs(rings[-1]["r"] - p["far_m"]) < 1e-6
    for r in rings:
        cell = r["r"] * step * 2 ** r["k"]
        assert p["min_cell_m"] * 0.99 <= cell < max(2 * p["min_cell_m"], p["far_m"] * step) * 1.01, (r, cell)
    for a, b in zip(rings, rings[1:]):
        assert b["r"] > a["r"] and b["n"] in (a["n"], 2 * a["n"])
        assert (b["r"] - a["r"]) / (a["r"] * step * 2 ** a["k"]) < p["radial_factor"] * 1.01


def test_stitched_lattice_has_no_crack():
    rings, _ = bb.lattice(PARAMS)
    assert len({r["k"] for r in rings}) >= 2                        # the fixture crosses a band edge
    T, off = bb.triangles(rings)
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); e.sort(axis=1)
    u, c = np.unique(e, axis=0, return_counts=True)
    assert c.max() == 2
    ring_of = np.searchsorted(off, u[c == 1], side="right") - 1
    col = u[c == 1] - off[ring_of]
    n = np.array([r["n"] for r in rings])[ring_of]
    edge = (ring_of == 0) | (ring_of == len(rings) - 1) | (col == 0) | (col == n)
    assert edge.all()                                               # every open edge lies on the lattice's own rim
    assert len(np.unique(T)) == off[-1]                             # every vertex is used, the fine ring's odd ones too


def test_bake_is_visual_only_wound_up_and_capped():
    res = baked()
    assert res["meta"]["triangles"] > 500
    for o in res["objects"]:
        assert o["name"].startswith("BACKDROP_FR_") and not o["name"][0].isdigit()
        assert len(o["v"]) <= PARAMS["max_verts_per_object"]
        a, b, c = (o["v"][o["tris"][:, i]] for i in range(3))
        ny = (b[:, 2] - a[:, 2]) * (c[:, 0] - a[:, 0]) - (b[:, 0] - a[:, 0]) * (c[:, 2] - a[:, 2])
        assert (ny > 0).all()
    V, _ = _all(res)
    brg = np.degrees(np.arctan2(V[:, 0], V[:, 2])) % 360
    d = np.hypot(V[:, 0], V[:, 2])
    assert brg.min() >= 240 - 1e-6 and brg.max() <= 300 + 1e-6 and d.min() >= 3000 - 1e-3 and d.max() <= 40000 + 1e-3


def test_height_is_the_surface_minus_curvature_from_the_origin():
    V, _ = _all(baked())
    d = np.hypot(V[:, 0], V[:, 2])
    want = surface(V[:, 0], V[:, 2]) - E0 - d * d * (1 - K) / (2 * 6371000.0)
    assert np.abs(V[:, 1] - want).max() < 0.02                      # the surface untouched: no smoothing, no scale
    far = d > 39000
    assert far.any() and (d[far] ** 2 * (1 - K) / (2 * 6371000.0) > 100).all()


def test_normals_are_the_real_surfaces():
    V, N = _all(baked())
    assert np.allclose(np.linalg.norm(N, axis=1), 1.0, atol=1e-6) and (N[:, 1] > 0).all()
    h = 1.0
    gx = (surface(V[:, 0] + h, V[:, 2]) - surface(V[:, 0] - h, V[:, 2])) / (2 * h)
    gz = (surface(V[:, 0], V[:, 2] + h) - surface(V[:, 0], V[:, 2] - h)) / (2 * h)
    want = np.stack([-gx, np.ones_like(gx), -gz], 1); want /= np.linalg.norm(want, axis=1)[:, None]
    ang = np.degrees(np.arccos(np.clip((N * want).sum(1), -1, 1)))
    assert np.median(ang) < 0.5 and ang.max() < 6.0                 # central differences over a cell, on a smooth surface


def test_only_what_the_road_sees_is_kept():
    res = baked(); V, _ = _all(res)
    assert res["meta"]["triangles"] < 0.75 * len(bb.triangles(bb.lattice(PARAMS)[0])[0])
    assert (np.hypot(V[:, 0] - HILL[0], V[:, 2] - HILL[1]) < 500).sum() == 0          # the hill behind the ridge is gone
    assert (np.hypot(V[:, 0] - PEAK[0], V[:, 2] - PEAK[1]) < 300).sum() > 0           # the far summit is there
    d = np.hypot(V[:, 0], V[:, 2])
    assert ((d > 14000) & (d < 15000)).sum() > 0                                      # the ridge's near face
    assert ((d > 5000) & (d < 9000)).sum() > 0                                        # the plain in front of it


def test_gate_passes_on_the_bake_and_reads_the_summit_from_the_mesh():
    with tempfile.TemporaryDirectory() as d:
        obj = _write(baked(), d)
        res = pg.gate(obj, _horizon(), SITE, O, E0, O, K, PARAMS["arc_deg"])
    rows = {r["peak"]: r for r in res["peaks"]}
    assert res["ok"], res
    assert rows["Far Peak"]["in_mesh"] and abs(rows["Far Peak"]["d_bearing_deg"]) < 0.1 and abs(rows["Far Peak"]["d_altitude_deg"]) < 0.02
    assert rows["Hidden Hill"]["in_mesh"] is False and rows["Hidden Hill"]["ok"]


def test_summits_are_kept_at_the_surfaces_own_high_point():
    spike = _at(271.3, 8111.0)                                      # a sharp 150 m summit on the plain, off the lattice

    def spiky(x, z):
        return surface(x, z) + 150.0 * np.exp(-(np.hypot(x - spike[0], z - spike[1]) / 60.0) ** 2)

    class Spiky:
        def elev(self, lon, lat):
            x, z = bb.to_local(O[0], O[1], np.ravel(lon), np.ravel(lat))
            return spiky(x, z).reshape(np.shape(lon))
    top = float(spiky(np.array([spike[0]]), np.array([spike[1]]))[0])
    got = {}
    for keep in (True, False):
        res = bb.bake(dict(PARAMS, keep_summits=keep, viewshed_eye_m=30.0), O, ROAD, Spiky(), E0)
        V = np.concatenate([o["v"] for o in res["objects"]])
        d = np.hypot(V[:, 0] - spike[0], V[:, 2] - spike[1]); near = d < 400
        j = np.flatnonzero(near)[np.argmax(V[near, 1])]
        dj = math.hypot(V[j, 0], V[j, 2])
        got[keep] = (float(d[j]), float(V[j, 1] + E0 + dj * dj * (1 - K) / (2 * 6371000.0)), res["meta"]["summits_kept"])
        want = spiky(V[:, 0], V[:, 2]) - E0 - (V[:, 0] ** 2 + V[:, 2] ** 2) * (1 - K) / (2 * 6371000.0)
        assert np.abs(V[:, 1] - want).max() < 0.02                  # every vertex, moved or not, is on the surface
    assert got[True][0] < 8.0 and top - got[True][1] < 3.0 and got[True][2] >= 1
    assert top - got[False][1] > 10.0 and got[False][2] == 0        # the plain lattice steps over it


def test_gate_takes_a_mesas_whole_top_as_its_bearing():
    res = baked()
    flat = {"objects": []}                                          # shave the far peak flat 40 m under its summit
    cap = float(surface(np.array([PEAK[0]]), np.array([PEAK[1]]))[0]) - 40.0
    for o in res["objects"]:
        v = o["v"].copy(); d = np.hypot(v[:, 0], v[:, 2])
        realh = v[:, 1] + E0 + d * d * (1 - K) / (2 * 6371000.0)
        v[:, 1] -= np.maximum(realh - cap, 0.0)
        flat["objects"].append(dict(o, v=v))
    h = _horizon(); pk = h["peaks"][SITE]["Far Peak"]
    pk["altitude_deg"] -= math.degrees(40.0 / 35000.0); pk["bearing_deg"] += 0.25      # the study's "summit": a cell somewhere on the top
    with tempfile.TemporaryDirectory() as d:
        r = pg.gate(_write(flat, d), h, SITE, O, E0, O, K, PARAMS["arc_deg"])
        pk["bearing_deg"] += 2.0                                                        # but not one off the mesa
        r2 = pg.gate(_write(flat, d), h, SITE, O, E0, O, K, PARAMS["arc_deg"])
    row = next(q for q in r["peaks"] if q["peak"] == "Far Peak")
    assert r["ok"] and row["mesh_top_bearing_span_deg"][1] - row["mesh_top_bearing_span_deg"][0] > 0.3
    assert not r2["ok"]


def _moved(fn):
    res = baked()
    return {"objects": [dict(o, v=fn(o["v"])) for o in res["objects"]]}


def test_gate_fails_a_mesh_turned_a_third_of_a_degree():
    t = math.radians(0.3)

    def turn(v):
        w = v.copy(); w[:, 0] = v[:, 0] * math.cos(t) + v[:, 2] * math.sin(t); w[:, 2] = -v[:, 0] * math.sin(t) + v[:, 2] * math.cos(t)
        return w
    with tempfile.TemporaryDirectory() as d:
        res = pg.gate(_write(_moved(turn), d), _horizon(), SITE, O, E0, O, K, PARAMS["arc_deg"])
    assert not res["ok"] and res["failed"] == ["Far Peak"]
    assert abs(abs(next(r for r in res["peaks"] if r["peak"] == "Far Peak")["d_bearing_deg"]) - 0.3) < 0.1


def test_gate_fails_a_mesh_without_the_curvature_drop_and_one_stretched_tall():
    def flat_earth(v):
        w = v.copy(); w[:, 1] = v[:, 1] + (v[:, 0] ** 2 + v[:, 2] ** 2) * (1 - K) / (2 * 6371000.0)
        return w

    def tall(v):
        w = v.copy(); w[:, 1] = v[:, 1] * 1.1
        return w
    with tempfile.TemporaryDirectory() as d:
        a = pg.gate(_write(_moved(flat_earth), d, "a.obj"), _horizon(), SITE, O, E0, O, K, PARAMS["arc_deg"])
        b = pg.gate(_write(_moved(tall), d, "b.obj"), _horizon(), SITE, O, E0, O, K, PARAMS["arc_deg"])
    assert not a["ok"] and next(r for r in a["peaks"] if r["peak"] == "Far Peak")["d_altitude_deg"] > 0.1
    assert not b["ok"] and next(r for r in b["peaks"] if r["peak"] == "Far Peak")["d_altitude_deg"] > 0.1


def test_gate_fails_a_missing_visible_peak_and_a_digit_prefixed_name():
    res = baked()
    cut = {"objects": []}
    for o in res["objects"]:
        keep = np.hypot(o["v"][:, 0] - PEAK[0], o["v"][:, 2] - PEAK[1]) > 1500
        t = o["tris"][keep[o["tris"]].all(1)]
        cut["objects"].append(dict(o, tris=t, v=np.where(keep[:, None], o["v"], 0.0)))      # dropped vertices parked at the origin
    named = {"objects": [dict(o, name="1" + o["name"]) for o in res["objects"]]}
    with tempfile.TemporaryDirectory() as d:
        a = pg.gate(_write(cut, d, "a.obj"), _horizon(), SITE, O, E0, O, K, PARAMS["arc_deg"])
        b = pg.gate(_write(named, d, "b.obj"), _horizon(), SITE, O, E0, O, K, PARAMS["arc_deg"])
    assert not a["ok"] and a["failed"] == ["Far Peak"]
    assert not b["ok"] and b["digit_prefixed_objects"]


def test_gate_skyline_follows_the_ridge():
    h = _horizon()
    ridge_alt = math.degrees(math.atan2(600.0 - 1.2 - 15000.0 ** 2 * (1 - K) / (2 * 6371000.0), 15000.0))
    h["sites"][SITE] = [[b, ridge_alt, 15000, 2200] for b in (245.0, 250.0, 280.0, 290.0)]     # bearings clear of the far peak
    with tempfile.TemporaryDirectory() as d:
        res = pg.gate(_write(baked(), d), h, SITE, O, E0, O, K, PARAMS["arc_deg"])
    s = res["skyline_reported_not_gated"]
    assert s["bearings_compared"] == 4 and s["over_tolerance"] == 0 and abs(s["worst"]["diff_deg"]) < 0.03


def test_cli_bakes_from_a_config_and_the_gate_exits_nonzero_on_failure():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); ref = root / "tracks" / "_reference" / "front-range"; ref.mkdir(parents=True)
        (root / "road.json").write_text(json.dumps({"nodes": [{"lon": q[0], "lat": q[1]} for q in ROAD]}))
        hz = _horizon()
        (root / "horizon.json").write_text(json.dumps(hz))
        cfg = {"params": PARAMS, "tracks": {"t": {"slug": "t", "origin_lon_lat": list(O), "origin_elev_m": E0, "road_line": "road.json",
                                                   "gate": {"horizon": "horizon.json", "site": SITE, "start_line_lon_lat": list(O)}}}}
        (ref / "bake.config.json").write_text(json.dumps(cfg))
        obj = _write(baked(), d)
        assert pg.main([str(obj), str(ref / "bake.config.json"), "t", "--report", str(root / "r.json")]) == 0
        assert json.loads((root / "r.json").read_text())["ok"] is True
        hz["peaks"][SITE]["Far Peak"]["altitude_deg"] += 0.2
        (root / "horizon.json").write_text(json.dumps(hz))
        assert pg.main([str(obj), str(ref / "bake.config.json"), "t"]) == 1
        assert bb.load_road(root / "road.json") == ROAD

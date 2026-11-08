"""The aerial reading stage (scripts/aerial/engine, ledger 0088) on synthetic images with known answers.

Each test draws the thing it measures (a road with a kerb, a dark driven band on a lot, a schematic map, a run of kerb
blocks, a displaced image) at a known place and checks the stage finds it there, within the image's own resolution.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.aerial.engine import band as bandm
from scripts.aerial.engine import channels as chn
from scripts.aerial.engine import edges as edg
from scripts.aerial.engine import geom, kerbs, maps, register, route
from scripts.aerial.engine.ortho import Ortho, utm_inverse

GSD = 0.3
LAT0 = 38.59
LON0 = -104.676


def _ortho(rgb, gsd=GSD):
    """A corners-georeferenced image whose ENU origin is its centre."""
    H, W = rgb.shape[:2]
    from scripts.aerial.engine.ortho import mpd
    mlon, mlat = mpd(LAT0)
    w_ = LON0 - W * gsd / 2 / mlon
    e_ = LON0 + W * gsd / 2 / mlon
    n_ = LAT0 + H * gsd / 2 / mlat
    s_ = LAT0 - H * gsd / 2 / mlat
    return Ortho(np.asarray(rgb, np.float32), Ortho._georef(Path("x.png"), {"corners": [w_, n_, e_, s_], "w": W, "h": H}, W, H)[0],
                 {"kind": "corners", "crs": "EPSG:4326"}, (LON0, LAT0))


def _road_image(W=600, H=600, radius=60.0, half=6.0, kerb_side=1, kerb_w=1.0):
    """A ring road (centre radius ``radius`` m about the image centre, half width ``half``) of grey asphalt on grass,
    with red / white kerb blocks (1 m each) just inside the asphalt on the ``kerb_side`` (+1 outer, -1 inner)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    e = (xx - (W - 1) / 2) * GSD
    n = -(yy - (H - 1) / 2) * GSD
    r = np.hypot(e, n)
    th = np.arctan2(n, e)
    img = np.zeros((H, W, 3), np.float32)
    img[:] = (70, 110, 50)                      # grass
    road = np.abs(r - radius) <= half
    img[road] = (95, 95, 92)                    # asphalt
    # the kerb: the last kerb_w metres of the asphalt on that side, blocks alternating every 1 m of arc
    k0 = radius + kerb_side * half
    kb = road & (np.abs(r - (k0 - kerb_side * kerb_w / 2)) <= kerb_w / 2)
    blk = (np.floor(th * radius / 1.0) % 2) == 0
    img[kb & blk] = (200, 40, 40)
    img[kb & ~blk] = (235, 235, 235)
    return np.clip(img, 0, 255)


def test_ortho_corners_round_trip_and_gsd():
    o = _ortho(np.zeros((200, 300, 3)))
    x, y = np.array([0.0, 150.0, 299.0]), np.array([0.0, 99.5, 199.0])
    e, n = o.px_to_en(x, y)
    bx, by = o.en_to_px(e, n)
    assert np.allclose(bx, x, atol=1e-6) and np.allclose(by, y, atol=1e-6)
    assert abs(o.gsd[0] - GSD) < 1e-6 and abs(o.gsd[1] - GSD) < 1e-6
    assert o.fit_px < 1e-6


def test_ortho_shift_moves_true_coordinates():
    o = _ortho(np.zeros((100, 100, 3)))
    e0, n0 = o.px_to_en(50.0, 50.0)
    o.set_shift([0.4, -0.2])
    e1, n1 = o.px_to_en(50.0, 50.0)
    assert abs((e0 - e1) - 0.4) < 1e-9 and abs((n0 - n1) + 0.2) < 1e-9
    x, y = o.en_to_px(e1, n1)
    assert abs(x - 50) < 1e-6 and abs(y - 50) < 1e-6


def test_fixture_crop_measures_pikes_peaks_diag_road():
    """A real NAIP 2023 window (tests/fixtures/aerial_engine): the diag road between its kerbs and its grass edges,
    12.0-12.8 m wide by ledger 0085's measurement, found from a straight route line through it."""
    fx = Path(__file__).resolve().parents[1] / "fixtures" / "aerial_engine" / "ppir_diag_2023_030.png"
    o = Ortho.load(fx)
    ch = chn.compute(o.rgb, float(np.mean(o.gsd)))
    pave = chn.pavement_mask(ch["pave"])
    a = np.array(o.px_to_en(np.array([75.0, 205.0]), np.array([65.0, 235.0]))).T
    line = np.c_[np.linspace(a[0, 0], a[1, 0], 60), np.linspace(a[0, 1], a[1, 1], 60)]
    G, _ = route.guide(o, pave, line, False, 8.0)
    m = edg.measure_strip(edg.Ctx(o, ch, opts={"reach_m": 20.0}), G, closed=False)
    assert not m["failed"]
    s = edg.summarise(m)
    w = float(np.median(s["W"]))
    assert 11.6 <= w <= 13.0, w
    for side in ("left", "right"):
        assert s["report"][side]["residual_m"]["p50"] < 0.25, s["report"][side]["residual_m"]


def test_utm_inverse_on_the_central_meridian():
    lon, lat = utm_inverse(np.array([500000.0]), np.array([4271000.0]), 13)
    assert abs(lon[0] + 105.0) < 1e-9
    # 4,271 km of northing on GRS80 at k0 0.9996 is ~38.58 deg
    assert 38.5 < lat[0] < 38.7
    try:
        from pyproj import Transformer
    except Exception:
        return
    t = Transformer.from_crs("EPSG:26913", "EPSG:4326", always_xy=True)
    for E, N in ((512345.0, 4271234.0), (487000.0, 4400000.0)):
        a = utm_inverse(np.array([E]), np.array([N]), 13)
        b = t.transform(E, N)
        assert abs(a[0][0] - b[0]) < 1e-8 and abs(a[1][0] - b[1]) < 1e-8


def test_ortho_reads_a_geotiff_crs():
    from PIL import TiffImagePlugin
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.tif"
        ifd = TiffImagePlugin.ImageFileDirectory_v2()
        ifd[33550] = (0.6, 0.6, 0.0)
        ifd[33922] = (0.0, 0.0, 0.0, 512000.0, 4272000.0, 0.0)
        ifd.tagtype[34735] = 3
        ifd[34735] = (1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, 26913)
        Image.fromarray(np.zeros((50, 80, 3), np.uint8)).save(p, tiffinfo=ifd)
        o = Ortho.load(p)
        assert o.desc["crs"] == "EPSG:26913"
        lon, lat = o.px_to_lonlat(np.array([-0.5]), np.array([-0.5]))      # the tiepoint is the corner
        lon_e, lat_e = utm_inverse(np.array([512000.0]), np.array([4272000.0]), 13)
        assert abs(lon[0] - lon_e[0]) < 1e-8 and abs(lat[0] - lat_e[0]) < 1e-8
        assert abs(o.gsd[0] - 0.6) < 0.005


def test_edges_find_a_ring_road_and_its_kerb_inner_face():
    rgb = _road_image()
    o = _ortho(rgb)
    ch = chn.compute(o.rgb, GSD)
    ctx = edg.Ctx(o, ch, opts={"reach_m": 15.0})
    th = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    G = np.c_[(60.0 + 1.5) * np.cos(th), (60.0 + 1.5) * np.sin(th)]      # a guide 1.5 m off the middle, CCW
    m = edg.measure_strip(ctx, G, closed=True)
    assert not m["failed"]
    s = edg.summarise(m)
    rad = np.hypot(*s["C"].T)
    # the asphalt runs 54..66 m; the outer 1 m is kerb paint, so the asphalt EDGE (the kerb's inner face) is at 65 m:
    # centre 59.5, width 11
    assert abs(np.median(rad) - 59.5) < 0.15, np.median(rad)
    assert abs(np.median(s["W"]) - 11.0) < 0.3, np.median(s["W"])
    kinds = s["report"]["right"]["edge_evidence"]          # CCW about the centre: the outer edge is on the right
    assert kinds.get("kerb", 0) > 0.5 * sum(kinds.values()), kinds
    assert s["report"]["left"]["residual_m"]["p50"] < 0.15


def test_lidar_edge_overrides_an_image_edge_only_where_it_is_the_boundary():
    rgb = _road_image(kerb_side=1, kerb_w=0.0)
    o = _ortho(rgb)
    ch = chn.compute(o.rgb, GSD)
    th = np.linspace(0, 2 * np.pi, 600, endpoint=False)
    wall = np.c_[66.4 * np.cos(th), 66.4 * np.sin(th)]
    ctx = edg.Ctx(o, ch, [np.vstack([wall, wall[:1]])], {"reach_m": 15.0})
    G = np.c_[60.0 * np.cos(th), 60.0 * np.sin(th)]
    s = edg.summarise(edg.measure_strip(ctx, G, closed=True))
    assert s["report"]["right"]["edge_evidence"].get("lidar", 0) > 0
    # the outer edge is the lidar's 66.4 m (the image's asphalt stops at 66.0, within LIDAR_TOL_M): centre 60.2, width 12.4
    assert abs(np.median(np.hypot(*s["C"].T)) - 60.2) < 0.15
    assert abs(np.median(s["W"]) - 12.4) < 0.3


def test_band_finds_the_dark_driven_band_on_open_pavement():
    H = W = 400
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    e = (xx - (W - 1) / 2) * GSD
    rgb = np.zeros((H, W, 3), np.float32)
    rgb[:] = (170, 170, 168)                        # a light lot
    inband = np.abs(e - 2.0) <= 4.5                 # a 9 m dark band centred 2 m east of the line
    rgb[inband] = (120, 120, 118)
    o = _ortho(rgb)
    ch = chn.compute(o.rgb, GSD)
    ctx = edg.Ctx(o, ch)
    line = np.c_[np.zeros(80), np.linspace(-40, 40, 80)]          # due north, so the band is on its RIGHT
    b = bandm.measure(ctx, line)
    mid = slice(10, -10)
    off = b["centre_off"][mid]
    assert abs(np.median(off) + 2.0) < 0.2, np.median(off)        # left-normal offsets: east = -
    assert abs(np.nanmedian(b["width"][mid]) - 9.0) < 0.4
    assert b["seen"][mid].mean() > 0.9


def _oval(n=400, a=150.0, b=90.0):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.c_[a * np.cos(t), b * np.sin(t) + 0.15 * a * np.sin(t) ** 3]      # not symmetric about the long axis


def test_similarity_fit_recovers_a_map_and_its_handedness():
    ref = geom.resample(_oval(), 0.5, closed=True)
    # the "map": ENU -> map px by scale 0.5 px/m, rotated 30 deg, y down (an unmirrored drawing), translated
    th = math.radians(30)
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    A = (ref @ R.T) * 2.0
    A[:, 1] *= -1
    A += [400, 300]
    sols = maps.fit_similarity(A[::3], ref)
    z = sols[0]
    assert z["det"] < 0, "an unmirrored map is det -1 (y down onto N up)"
    assert z["rms"] < 0.2 and abs(z["scale_m_per_px"] - 0.5) < 0.005
    # a mirrored copy of the same map fits only with the other handedness
    Am = A.copy()
    Am[:, 0] = 800 - Am[:, 0]
    zm = maps.fit_similarity(Am[::3], ref)[0]
    assert zm["det"] > 0 and zm["rms"] < 0.2


def test_course_loop_drops_the_ink_marked_not_course():
    H, W = 300, 400
    yy, xx = np.mgrid[0:H, 0:W]
    ring = (np.abs(np.hypot((xx - 200) / 150, (yy - 150) / 100) - 1) < 0.04)
    chord = (np.abs(yy - 70) <= 3) & (xx >= 110) & (xx <= 290)       # a "pit lane": a chord across the top
    course = ring | chord
    try:
        maps.course_loop({"course": course}, {"spur_px": 6})
        raised = False
    except SystemExit:
        raised = True
    assert raised, "a loop with a parallel chord is not one loop: the stage must ask, not choose"
    px, info = maps.course_loop({"course": course}, {"spur_px": 6, "exclude_px": [[200, 70]]})
    assert info["dropped_px"]
    r = np.hypot((px[:, 0] - 200) / 150, (px[:, 1] - 150) / 100)
    assert np.abs(r - 1).max() < 0.1


def test_block_reader_places_kerb_paint_across_the_edge():
    # a straight lane edge running east; blocks 1 m long from 0.2 m inside to 1.4 m outside the edge, on its left
    H, W = 200, 400
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    e = (xx - (W - 1) / 2) * GSD
    n = -(yy - (H - 1) / 2) * GSD
    rgb = np.zeros((H, W, 3), np.float32)
    rgb[:] = (100, 100, 100)
    hw = 5.0
    paint = (n >= hw - 0.2) & (n <= hw + 1.4) & (np.abs(e) < 25)
    blk = (np.floor(e / 1.0) % 2) == 0
    rgb[paint & blk] = (230, 230, 230)
    rgb[paint & ~blk] = (180, 60, 60)
    o = _ortho(rgb)
    P = np.c_[np.linspace(-50, 50, 101), np.zeros(101)]
    line = kerbs.Line(o, P, np.full(101, 2 * hw))
    m = kerbs.measure(line, 1, 35.0, 65.0)         # s from the line's start at e = -50: the paint spans s 25..75
    assert m is not None
    assert abs(m["in_m"] + 0.2) < 0.15 and abs(m["out_m"] - 1.4) < 0.15, m
    assert abs(m["s0"] - 25) < 3 and abs(m["s1"] - 75) < 3, m
    cands = kerbs.scan(line, 1)
    assert any(a < 40 and b > 60 for a, b in cands), cands


def test_registration_recovers_a_known_displacement():
    t = np.linspace(0, 2 * np.pi, 300, endpoint=False)
    outward = np.c_[np.cos(t), np.sin(t)]
    shift = np.array([0.30, -0.45])
    rng = np.random.default_rng(1)
    off = 0.05 + outward @ shift + rng.normal(0, 0.05, len(t))
    r = register.fit_shift(off, outward, 0.3)
    assert abs(r["shift_en_m"][0] - 0.30) < 0.03 and abs(r["shift_en_m"][1] + 0.45) < 0.03
    assert r["apply"]
    r2 = register.fit_shift(0.05 + outward @ np.array([0.05, 0.05]), outward, 0.3)
    assert not r2["apply"], "under a pixel: reported, not applied"


def test_guide_runs_down_the_road_whichever_side_the_route_line_is_drawn():
    rgb = _road_image(kerb_w=0.0)
    o = _ortho(rgb)
    ch = chn.compute(o.rgb, GSD)
    pave = chn.pavement_mask(ch["pave"])
    th = np.linspace(0, 2 * np.pi, 300, endpoint=False)
    line = np.c_[63.5 * np.cos(th), 63.5 * np.sin(th)]           # drawn 3.5 m off the middle
    G, info = route.guide(o, pave, line, True, 8.0)
    rad = np.hypot(*G.T)
    assert abs(np.median(rad) - 60.0) < 0.6, np.median(rad)


def test_stage_runs_end_to_end_on_a_synthetic_track():
    """A map image, a ring road, a config: the stage writes a layout on the road with its lap length."""
    from scripts.aerial.engine.run import Stage
    rgb = _road_image(kerb_w=0.0).astype(np.uint8)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        Image.fromarray(rgb).save(d / "ortho.png")
        o = _ortho(rgb)
        lon, lat = o.px_to_lonlat(np.array([-0.5, rgb.shape[1] - 0.5]), np.array([-0.5, rgb.shape[0] - 0.5]))
        (d / "ortho.json").write_text(json.dumps({"corners": [lon[0], lat[0], lon[1], lat[1]],
                                                  "w": rgb.shape[1], "h": rgb.shape[0]}))
        # the map: the same ring drawn red on white at 2 px per metre, rotated 20 degrees; a grey outline round it
        M = np.full((400, 400, 3), 255, np.uint8)
        yy, xx = np.mgrid[0:400, 0:400]
        r = np.hypot(xx - 200, yy - 200)
        M[np.abs(r - 120) <= 6] = (230, 20, 20)
        M[(np.abs(r - 133) <= 7)] = (150, 150, 150)
        Image.fromarray(M).save(d / "map.png")
        cfg = {"name": "synthetic", "image": "ortho.png", "edges": {"reach_m": 15.0},
               "maps": {"m": {"file": "map.png", "register_to": "pavement", "direction": "ccw",
                              "ink": {"course": {"any": [{"rgb_min": [200, 0, 0], "rgb_max": [255, 60, 60]}]},
                                      "other": {"any": [{"rgb_min": [140, 140, 140], "rgb_max": [160, 160, 160]}]}}}},
               "layouts": [{"id": "lap", "route": {"maps": ["m"]}, "direction": "ccw", "published_length_m": [377.0],
                            "kerbs": False}]}
        rep = Stage(cfg, d, d / "out").run(do_stills=False)
        lay = rep["layouts"][0]
        assert abs(lay["lap_m"] - 2 * math.pi * 60.0) < 3.0, lay["lap_m"]
        assert abs(lay["width_m"]["p50"] - 12.0) < 0.5
        gj = json.loads((d / "out" / "lap.centerline.geojson").read_text())
        assert gj["features"][0]["properties"]["closed"] is True
        assert (d / "out" / "lap.source.json").exists()

"""Ledger 0057 (Kevin 2026-10-14: "my cars with clutches would roll back from stoplights there"): road_datum profile
windows (tools/deck_datum.py) re-base a short stretch of the frozen pre-median profile on fresh 3DEP at both carriageway
centres, holding every deck span inside straight; the assembler (scripts-v021) smooths those windows with their own
sigma and leaves every other vertex exactly as before."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import deck_datum as dd  # noqa: E402

SRC = ROOT / "tracks" / "san-diego-lake-murray"


def _smooth():
    spec = importlib.util.spec_from_file_location("_v021_smooth_0057", SRC / "scripts-v021" / "geometry" / "smooth.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _ring(n=400, r=200.0):
    """a closed circle ~3.14 m per vertex, v0 == v[-1] (the closing duplicate)"""
    pts = [[r * math.cos(2 * math.pi * k / n), 0.0, r * math.sin(2 * math.pi * k / n)] for k in range(n)]
    return pts + [list(pts[0])]


# --- pure halves ---------------------------------------------------------------------------------------------
def test_unwrap_window_runs_through_the_seam():
    assert dd.unwrap_window([100.0, 300.0], 1000.0) == (100.0, 300.0)
    assert dd.unwrap_window([900.0, 50.0], 1000.0) == (900.0, 1050.0)          # start past end: through the seam
    assert dd.unwrapped(950.0, 900.0, 1050.0, 1000.0) == 950.0
    assert dd.unwrapped(20.0, 900.0, 1050.0, 1000.0) == 1020.0
    assert dd.unwrapped(500.0, 900.0, 1050.0, 1000.0) is None


def test_profile_target_holds_a_span_straight_and_keeps_a_short_grade():
    ts = [float(t) for t in range(0, 201)]
    # a 6 % climb to a crest at 100 then -6 %, a 30 m span 140-170 over a trench 8 m down
    raw = [(6.0 - 0.06 * abs(t - 100)) - (8.0 if 141 <= t <= 169 else 0.0) for t in ts]
    tgt, held = dd.profile_target(ts, raw, [(140.0, 170.0)], 3.0)
    (ya, yb), = held
    assert abs(ya - (6.0 - 0.06 * 38.5)) < 0.01 and abs(yb - (6.0 - 0.06 * 71.5)) < 0.01    # never across an abutment
    assert min(y for t, y in zip(ts, tgt) if 140 <= t <= 170) > yb - 0.05                   # no trench under the deck
    g = (tgt[80] - tgt[50]) / 30.0
    assert abs(g - 0.06) < 0.002                                                              # a 30 m grade kept
    assert tgt[100] > 6.0 - 0.15                                                              # the crest only rounded


def test_window_spans_refuses_a_deck_cut_by_the_window_edge():
    decks = [{"name": "a", "deck_m": [120.0, 160.0]}, {"name": "b", "deck_m": [980.0, 995.0]}]
    assert dd.window_spans(decks, 900.0, 1050.0, 1000.0) == [(980.0, 995.0, "b")]
    assert dd.window_spans(decks, 100.0, 200.0, 1000.0) == [(120.0, 160.0, "a")]
    try:
        dd.window_spans(decks, 140.0, 300.0, 1000.0)
    except SystemExit as e:
        assert "cuts deck a" in str(e)
    else:
        raise AssertionError("a profile window cutting a deck span must be refused")


# --- the run: a window through the seam on a closed ring, offline from the cache ---------------------------------
def _project(profiles, decks=()):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    pts = _ring()
    raw = {"origin": {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}, "points_xyz_m": pts, "widths_m": [12.0] * len(pts)}
    (d / "data" / dd.SRC_NAME).write_text(json.dumps(raw))
    (d / "track.config.json").write_text(json.dumps({"road_datum": {"decks": list(decks), "profiles": profiles}}))
    st = dd.stations(pts)
    keys = {}
    for p in profiles:
        w0, w1 = dd.unwrap_window(p["window_m"], st[-1])
        ts = dd.profile_samples(w0, w1)
        for a, b in dd.carriageway_centres(pts, st, raw["widths_m"], ts):
            for x, z in (a, b):
                ang = math.atan2(z, x)
                # the real road: a 3 m hump centred on v0 (angle 0), the left carriageway 0.2 m over the right
                keys[f"{x:.2f},{z:.2f}"] = 100.0 + 3.0 * math.exp(-(ang * 200.0 / 40.0) ** 2) + (
                    0.1 if (x * x + z * z) < 200.0 ** 2 else -0.1)
    (d / "data" / "deck_datum.samples.json").write_text(json.dumps({"_provenance": {"fetches": []}, "points": keys}))
    return d, pts, st


def test_profile_through_the_seam_moves_both_sides_keeps_v0_closed_and_leaves_the_rest_alone():
    d, pts, st = _project([{"name": "seam", "window_m": [1100.0, 150.0], "blend_m": 30.0}])
    r1 = dd.run(d, offline=True)
    out = json.loads((d / "data" / dd.SRC_NAME).read_text())["points_xyz_m"]
    ys = [p[1] for p in out]
    L = st[-1]
    assert ys[-1] == ys[0]                                            # the closing duplicate is v0 (L13)
    assert abs(ys[0] - 3.0) < 0.15                                    # the hump's top, at both carriageway centres' mean
    for s, y in zip(st, ys):
        if 180.0 < s < 1080.0:
            assert y == 0.0                                           # outside the window: untouched
    before = [y for s, y in zip(st, ys) if L - 60 < s < L - 1]
    after = [y for s, y in zip(st, ys) if 1 < s < 60]
    assert max(before) > 1.0 and max(after) > 1.0                     # both sides of the seam re-based
    rec = r1["profiles"][0]
    assert rec["unwrapped_m"][1] > L and rec["vertices_moved"] > 0
    r2 = dd.run(d, offline=True)                                      # idempotent: the md5 of what it wrote
    assert r2["output_md5"] == r1["output_md5"]


def test_a_deck_inside_a_profile_is_held_by_the_profile_not_its_own_window():
    decks = [{"name": "span", "deck_m": [40.0, 60.0], "window_m": [25.0, 75.0]}]
    d, pts, st = _project([{"name": "p", "window_m": [1150.0, 140.0], "blend_m": 30.0}], decks)
    r = dd.run(d, offline=True)
    assert r["decks"][0]["re_derived_by_profile"] == "p" and "moves" not in r["decks"][0]
    held = r["profiles"][0]["spans_held"]
    assert held and held[0]["deck"] == "span"
    ys = [p[1] for p in json.loads((d / "data" / dd.SRC_NAME).read_text())["points_xyz_m"]]
    on = [(s, y) for s, y in zip(st, ys) if 46 <= s <= 54]
    g = [(y1 - y0) / (s1 - s0) for (s0, y0), (s1, y1) in zip(on, on[1:])]
    assert max(g) - min(g) < 0.01                                     # straight across the span's middle


def test_offline_profile_refuses_an_uncached_sample():
    d, _pts, _st = _project([{"name": "seam", "window_m": [1100.0, 150.0]}])
    (d / "data" / "deck_datum.samples.json").write_text(json.dumps({"_provenance": {"fetches": []}, "points": {}}))
    try:
        dd.run(d, offline=True)
    except SystemExit as e:
        assert "not cached" in str(e)
    else:
        raise AssertionError("a profile with uncached 3DEP must refuse --offline (L2: no silent fill)")


# --- the assembler's per-window sigma ------------------------------------------------------------------------------
def test_assembler_window_sigma_is_opt_in_and_exact_outside_the_windows():
    sm = _smooth()
    pts = _ring()
    n = len(pts)
    # a sharp 2 m crest at v10 and a second one far away at v200
    for k in range(n):
        j = k % (n - 1)
        pts[k][1] = max(0.0, 2.0 - 0.15 * min(abs(j - 10), n - 1 - abs(j - 10))) + max(0.0, 2.0 - 0.15 * abs(j - 200))
    pts = [tuple(p) for p in pts]
    st = dd.stations(pts)
    L = st[-1]
    plain = sm.smooth_centerline(pts, sigma_pts=0, passes=0, sigma_y_pts=5.0)
    assert sm.smooth_centerline(pts, sigma_pts=0, passes=0, sigma_y_pts=5.0, y_sigma_windows=None) == plain
    w = sm.window_weights(st[:-1], L, [(L - 60.0, L + 90.0, 30.0)])       # through the seam (L13)
    assert w[0] == 1.0 and w[5] == 1.0 and w[n - 5] == 1.0 and w[100] == 0.0 and 0.0 < w[n - 1 - 15] < 1.0
    out = sm.smooth_centerline(pts, sigma_pts=0, passes=0, sigma_y_pts=5.0, y_sigma_windows=[(1.5, w)])
    assert out[-1] == out[0] and len(out) == n
    for i in range(n - 1):
        if w[i] == 0.0:
            assert out[i][1] == plain[i][1]                               # byte-identical outside every window
    assert out[10][1] > plain[10][1] + 0.3                                # the window keeps its crest
    assert abs(out[200][1] - plain[200][1]) == 0.0                        # the far crest: sigma 5, as before
    try:
        sm.smooth_centerline(pts, sigma_pts=0, passes=0, sigma_y_pts=5.0, y_sigma_windows=[(1.5, w[:-1])])
    except ValueError:
        pass
    else:
        raise AssertionError("weights must be one per unique vertex")


def test_build_loop_blend_passes_the_windows_only_when_declared():
    src = (SRC / "scripts-v021" / "blender" / "build_loop_blend.py").read_text(encoding="utf-8")
    assert "y_windows = _profile_sigma_windows(cfg, data, raw_centerline)" in src
    assert '**({"y_sigma_windows": y_windows} if y_windows else {})' in src
    assert 'data / "centerline.raw.local.json.pre-median"' in src


# --- Lake Murray's declaration ---------------------------------------------------------------------------------------
def test_lake_murray_declares_both_windows_and_the_lmb_decks():
    cfg = json.loads((SRC / "track.config.json").read_text(encoding="utf-8"))
    rd = cfg["road_datum"]
    assert [d["name"] for d in rd["decks"]] == ["college_ave_over_i8", "lmb_over_i8", "lmb_over_alvarado_creek"]
    prof = {p["name"]: p for p in rd["profiles"]}
    a, b = prof["college_alvarado_junction"], prof["seventieth_alvarado"]
    assert a["window_m"][1] < rd["decks"][0]["window_m"][0]              # short of the College deck window
    assert b["window_m"][0] > b["window_m"][1]                            # through the lap seam
    assert a["assembler_sigma_y_pts"] == 1.0 and b["assembler_sigma_y_pts"] == 1.5     # rehearsed (ledger 0057)
    assert a["hold_straight_m"] == [[2289.0, 2323.0]] and not b.get("hold_straight_m")
    pre = json.loads((SRC / "data" / dd.SRC_NAME).read_text(encoding="utf-8"))["points_xyz_m"]
    L = dd.stations(pre)[-1]
    spans = dd.window_spans(rd["decks"], *dd.unwrap_window(b["window_m"], L), L)
    assert [n for _a, _b, n in spans] == ["lmb_over_i8", "lmb_over_alvarado_creek"]
    assert dd.window_spans(rd["decks"], *dd.unwrap_window(a["window_m"], L), L) == []
    assert route_sigma_unchanged(cfg)


def route_sigma_unchanged(cfg):
    return cfg["route"]["smooth_sigma_y_pts"] == 5.0                      # ledger 0042's loop-wide sigma stays


def test_lake_murray_profiles_run_offline_from_the_committed_cache_and_restore_the_grades():
    """the committed data/deck_datum.samples.json carries every 3DEP sample both windows read (L2), and the datum puts
    the College -> Alvarado signal approach and Alvarado's pitch from 70th back near the real grades"""
    import shutil
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    shutil.copy(SRC / "track.config.json", d / "track.config.json")
    for f in (dd.SRC_NAME, "deck_datum.samples.json"):
        shutil.copy(SRC / "data" / f, d / "data" / f)
    dd.run(d, offline=True)
    pts = json.loads((d / "data" / dd.SRC_NAME).read_text())["points_xyz_m"]
    st = dd.stations(pts)
    ys = [p[1] for p in pts]
    L = st[-1]

    def y(t):
        return _lin(st, ys, t % L)
    # College southbound into the signal (pre-median s 2356 -> 2326; local s 2343 -> 2313): real +5.9 %
    assert (y(2326.0) - y(2356.0)) / 30.0 > 0.055
    # the hairpin's fold fan (2289-2323) held straight: no hump inside the box
    box = [(s, yy) for s, yy in zip(st, ys) if 2290.0 <= s <= 2322.0]
    gb = [(y1 - y0) / (s1 - s0) for (s0, y0), (s1, y1) in zip(box, box[1:])]
    assert max(gb) - min(gb) < 0.002
    # Alvarado westbound s 17 -> 117 from 70th: real -7.7 %
    assert (y(L + 117.0) - y(L + 17.0)) / 100.0 < -0.074
    # the 70th junction back at the real pavement (125.1 m), not 0.7 m under it
    assert abs(y(0.0) + 100.8 - 125.1) < 0.15


def test_a_hold_span_holds_a_junction_box_straight_and_must_sit_inside_the_window():
    d, pts, st = _project([{"name": "p", "window_m": [1150.0, 140.0], "blend_m": 30.0,
                            "hold_straight_m": [[1240.0, 20.0]]}])
    r = dd.run(d, offline=True)
    assert [h["deck"] for h in r["profiles"][0]["spans_held"]] == ["hold:p#0"]
    ys = [p[1] for p in json.loads((d / "data" / dd.SRC_NAME).read_text())["points_xyz_m"]]
    L = st[-1]
    on = sorted(((s if s > 600 else s + L), y) for s, y in zip(st[:-1], ys[:-1]) if s > L - 15 or s < 12)
    g = [(y1 - y0) / (s1 - s0) for (s0, y0), (s1, y1) in zip(on, on[1:])]
    assert max(g) - min(g) < 0.01                  # straight across the seam, where the hump's crest was
    assert max(y for _s, y in on) <= max(on[0][1], on[-1][1]) + 1e-6 < 2.95   # the hump's top is not in the box
    bad = [{"name": "p", "window_m": [1150.0, 140.0], "blend_m": 30.0, "hold_straight_m": [[1160.0, 20.0]]}]
    (d / "track.config.json").write_text(json.dumps({"road_datum": {"decks": [], "profiles": bad}}))
    (d / "data" / "deck_datum.json").unlink()
    try:
        dd.run(d, offline=True)
    except SystemExit as e:
        assert "hold_straight_m" in str(e)
    else:
        raise AssertionError("a hold inside the window's blend must be refused")


def _lin(st, ys, t):
    for i in range(len(st) - 1):
        if st[i] <= t <= st[i + 1]:
            u = (t - st[i]) / ((st[i + 1] - st[i]) or 1e-9)
            return ys[i] + (ys[i + 1] - ys[i]) * u
    return ys[-1]

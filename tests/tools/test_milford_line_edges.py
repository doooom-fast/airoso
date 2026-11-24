"""Ledger 0091 (the Milford geometry audit's line and edge fixes, 2026-11-18). All opt-in; only Milford's port names them.

- lm_intake.line_precomp (Gap 1 / Fix B): x, z <- 2 P - S(P), S the route's own smooth, so the assembler's S(2 P - S(P))
  lands on P to second order (a bend is no longer built inside itself); Y, the count and the closure are kept.
- tools/edge_retrace.py mode "agree" (Gap 2 / Fix A): an edge moves in OR out to the mean of NAIP and the lidar where the
  two agree within edge_fit.AGREE_M, and nowhere they do not; never onto a rail; nothing outside the spans and the fade.
  The default mode ("widen", 0.1.12's front straight) is unchanged.
- lm_intake.edge_retrace as a list of records (each with an optional shift_precomp) and lm_intake.width_smooth_m (Gap 3 /
  Fix C: a Gaussian on the widths, held where a widen record acts).
"""

from __future__ import annotations

import importlib.util
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


er = _load("edge_retrace", ROOT / "tools" / "edge_retrace.py")
sm = _load("_v021_smooth", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py")
MF = "milford-road-course-lm"


def _loop(n=800, r=200.0, y=0.0):
    """a closed circle, travel counter-clockwise (left = inside), last == first"""
    pts = [(r * math.cos(2 * math.pi * k / n), y + 0.01 * k, r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return pts + [pts[0]]


def _edge_points(pts, rows, off, src):
    """evidence points at lateral offset off (+ left) on the given rows, three per row"""
    out = []
    n = len(pts) - 1
    for i in rows:
        a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz)
        nx, nz = -tz / L, tx / L
        for _ in range(3):
            out.append([pts[i][0] + nx * off, pts[i][2] + nz * off, src, 30.0])
    return out


def _both(pts, rows, off_naip, off_lidar=None):
    return (_edge_points(pts, rows, off_naip, "naip")
            + _edge_points(pts, rows, off_naip if off_lidar is None else off_lidar, "lidar"))


def _radius_err(P, r):
    return max(abs(math.hypot(p[0], p[2]) - r) for p in P)


# ------------------------------------------------------------------------------------------------ Fix B: line_precomp
def test_precomp_lands_the_assembler_on_the_intake_line():
    import lm_engine_intake as L
    r = 40.0
    n = int(round(2 * math.pi * r / 1.5))
    pts = _loop(n=n, r=r)
    built_plain = sm.smooth_centerline(pts, sigma_pts=5.0, passes=2, sigma_y_pts=0.0)
    pre, rep = L.precomp_line(pts, True, sm, sigma_pts=5.0, passes=2)
    built_pre = sm.smooth_centerline(pre, sigma_pts=5.0, passes=2, sigma_y_pts=0.0)
    e0, e1 = _radius_err(built_plain, r), _radius_err(built_pre, r)
    assert e0 > 1.0, e0                                   # ~sigma^2 / 2R: the bend built inside itself
    assert e1 < 0.1 * e0, (e0, e1)                        # second order once pre-compensated
    assert len(pre) == len(pts) and pre[-1] == pre[0]
    assert all(abs(p[1] - q[1]) < 1e-12 for p, q in zip(pts, pre))    # Y kept, per index
    assert rep["moved_m"]["max"] > 1.0 and rep["lap_m"][1] > rep["lap_m"][0]


def test_precomp_leaves_a_straight_where_it_is():
    import lm_engine_intake as L
    pts = [(0.0, 0.1 * k, 1.5 * k) for k in range(100)]  # open and straight: nothing moves sideways
    pre, rep = L.precomp_line(pts, False, sm, sigma_pts=5.0, passes=2)
    assert max(abs(p[0]) for p in pre) < 1e-9
    # beyond the kernel's reach of the ends (2 passes x 15 points; there the open smooth clamps its kernel and only slides
    # points along the line) nothing moves at all; the end points are pinned, Y is kept
    assert max(abs(a[2] - b[2]) for a, b in zip(pts[30:-30], pre[30:-30])) < 1e-9
    assert pre[0] == pts[0] and pre[-1] == pts[-1] and [p[1] for p in pre] == [p[1] for p in pts]


# ------------------------------------------------------------------------------------------------ Fix A: mode agree
def test_agree_moves_each_edge_in_or_out_where_both_sensors_agree():
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [16.0] * len(pts)
    ev = _both(pts, range(n), 9.0) + _both(pts, range(n), -6.5)    # left 1.0 m out, right 1.5 m in, both sensors
    span = [[300.0, 500.0]]
    new, shift, rep = er.retrace(pts, w, True, ev, span, [], taper_m=30.0, mode="agree")
    mid = min(range(n), key=lambda i: abs(st[i] - 400.0))
    far = min(range(n), key=lambda i: abs(st[i] - 900.0))
    left, right = new[mid] / 2 + shift[mid], new[mid] / 2 - shift[mid]
    assert abs(left - 9.0) < 0.05 and abs(right - 6.5) < 0.05, (left, right)
    assert abs(new[far] - 16.0) < 1e-6 and abs(shift[far]) < 1e-9      # outside the span and its fade: nothing
    assert new[-1] == new[0] and shift[-1] == shift[0]
    assert rep["mode"] == "agree" and rep["src"] == "naip+lidar"
    # the same evidence in the default mode: the right edge never moves in
    new_w, shift_w, rep_w = er.retrace(pts, w, True, ev, span, [], taper_m=30.0)
    assert abs((new_w[mid] / 2 - shift_w[mid]) - 8.0) < 1e-3 and "mode" not in rep_w


def test_agree_does_not_move_where_the_sensors_disagree():
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [16.0] * len(pts)
    ev = _both(pts, range(n), 9.5, 8.5) + _both(pts, range(n), -7.0)   # left: 1.0 m apart (> AGREE_M); right agree
    new, shift, rep = er.retrace(pts, w, True, ev, [[300.0, 500.0]], [], taper_m=30.0, mode="agree")
    mid = min(range(n), key=lambda i: abs(st[i] - 400.0))
    left, right = new[mid] / 2 + shift[mid], new[mid] / 2 - shift[mid]
    assert abs(left - 8.0) < 1e-3, left
    assert abs(right - 7.0) < 0.05, right


def test_agree_keeps_the_rail_clamp():
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [16.0] * len(pts)
    ev = _both(pts, range(n), 10.0) + _both(pts, range(n), -8.0)
    rail = [((200.0 - 9.0) * math.cos(t), (200.0 - 9.0) * math.sin(t))
            for t in [2 * math.pi * (350.0 + k) / lap for k in range(0, 101, 5)]]
    new, shift, rep = er.retrace(pts, w, True, ev, [[300.0, 500.0]], [{"key": "r", "xz": rail}], clear_m=0.10,
                                 taper_m=30.0, mode="agree")
    for s in (360.0, 400.0, 440.0):
        i = min(range(n), key=lambda k: abs(st[k] - s))
        assert new[i] / 2 + shift[i] <= 9.0 - 0.10 + 0.005, (s, new[i] / 2 + shift[i])
    assert rep["rails"][0]["side"] == "left"


def test_widen_is_unchanged_by_the_new_options():
    pts = _loop()
    n = len(pts) - 1
    w = [16.0] * len(pts)
    ev = _edge_points(pts, range(n), 9.5, "naip") + _edge_points(pts, range(n), -8.0, "naip")
    a = er.retrace(pts, w, True, ev, [[300.0, 500.0]], [], taper_m=30.0)
    b = er.retrace(pts, w, True, ev, [[300.0, 500.0]], [], taper_m=30.0, mode="widen", smooth_m=er.SMOOTH_M,
                   erode_m=er.ERODE_M, gap_m=er.GAP_M)
    assert a[0] == b[0] and a[1] == b[1] and json.dumps(a[2]) == json.dumps(b[2])
    assert "mode" not in a[2]
    try:
        er.retrace(pts, w, True, ev, [[300.0, 500.0]], [], mode="both")
    except SystemExit as e:
        assert "mode" in str(e)
    else:
        raise AssertionError("an unknown mode must stop the intake")


# ------------------------------------------------------------------------------------------------ Fix C: width_smooth_m
def test_width_smoothing_damps_the_breathing_and_holds_a_widen_span():
    import lm_engine_intake as L
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [12.0 + 2.0 * (int(s // 20.0) % 2) for s in st] + [12.0]      # 12 / 14 m every 20 m (a 40 m wave)
    w[-1] = w[0]
    held = [([[300.0, 500.0]], 30.0)]
    new, rep = L.smooth_widths(pts, w, True, 10.0, held)
    far = [i for i in range(n) if 700.0 <= st[i] <= 1100.0]
    amp0 = max(w[i] for i in far) - min(w[i] for i in far)
    amp1 = max(new[i] for i in far) - min(new[i] for i in far)
    assert amp1 < 0.4 * amp0, (amp0, amp1)                 # a sigma 10 m Gaussian passes ~0.29 of a 40 m wave
    inside = [i for i in range(n) if 300.0 <= st[i] <= 500.0]
    assert all(new[i] == w[i] for i in inside)             # a widen record's own widths stay
    assert new[-1] == new[0] and rep["rows_held_by_widen_retrace"] == len(inside)
    try:
        L.smooth_widths(pts, w, True, 0.0, [])
    except SystemExit as e:
        assert "width_smooth_m" in str(e)
    else:
        raise AssertionError("a sigma of 0 must stop the intake")


# ------------------------------------------------------------------------------------------------ the Milford port
def _sync_in(port: str, ws: Path):
    """ship.json's sync_in, as tools/ship_track.sh does it, into an EMPTY workshop (tests/tools/test_lm_engine_port.py's)"""
    spec = json.loads((ROOT / "tracks" / port / "ship.json").read_text(encoding="utf-8"))
    src = ROOT / "tracks" / port
    sin = spec.get("sync_in") or {}
    for rel in sin.get("required", []) + [r for r in sin.get("optional", []) if (src / r).exists()]:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes((src / rel).read_bytes())


def _built(ws: Path):
    """the assembler's line: its own smooth of the intake's data/centerline.local.json (build_loop_blend)"""
    cfg = json.loads((ws / "track.config.json").read_text(encoding="utf-8"))
    route = cfg["route"]
    loc = json.loads((ws / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in loc["points_xyz_m"]]
    return pts, sm.smooth_centerline(pts, sigma_pts=float(route["smooth_sigma_pts"]), passes=int(route["smooth_passes"]),
                                     sigma_y_pts=float(route["smooth_sigma_y_pts"]))


def test_milford_intake_runs_the_0091_options_and_the_assembler_builds_the_intake_line():
    import lm_engine_intake as L
    ws = Path(tempfile.mkdtemp(prefix="mf0091_"))
    ws2 = Path(tempfile.mkdtemp(prefix="mf0091_off_"))
    try:
        _sync_in(MF, ws)
        rep = L.intake(ws)
        cfg = json.loads((ws / "track.config.json").read_text(encoding="utf-8"))
        assert rep["line_precomp"]["moved_m"]["max"] > 1.0
        assert rep["width_smooth"]["rows_held_by_widen_retrace"] > 0
        assert [r.get("mode", "widen") for r in rep["edge_retrace"]] == ["widen", "agree"]
        runs = json.loads((ws / "data" / "edge_retrace.json").read_text(encoding="utf-8"))["runs"]
        assert len(runs) == 2 and all(r.get("shift_precomp") for r in runs)
        # the agree record's rail clamp lists every rail the bespoke dressing builds
        keys = {r["key"] for r in cfg["scenery"]["bespoke"]["rails"]}
        assert set(cfg["lm_intake"]["edge_retrace"][1]["rails"]) == keys
        assert {r["key"] for r in runs[1]["rails"]} == keys
        # the same line without the pre-compensation (and without the retrace's shifts, which both runs then lack)
        _sync_in(MF, ws2)
        c2 = json.loads((ws2 / "track.config.json").read_text(encoding="utf-8"))
        for k in ("line_precomp", "edge_retrace", "width_smooth_m"):
            c2["lm_intake"].pop(k)
        (ws2 / "track.config.json").write_text(json.dumps(c2), encoding="utf-8")
        L.intake(ws2)
        c1 = json.loads((ws / "track.config.json").read_text(encoding="utf-8"))
        c1["lm_intake"].pop("edge_retrace")
        c1["lm_intake"].pop("width_smooth_m")
        (ws / "track.config.json").write_text(json.dumps(c1), encoding="utf-8")
        L.intake(ws)
        trace, built_plain = _built(ws2)
        _pre, built_pre = _built(ws)
        d0 = sorted(math.hypot(a[0] - b[0], a[2] - b[2]) for a, b in zip(trace, built_plain))
        d1 = sorted(math.hypot(a[0] - b[0], a[2] - b[2]) for a, b in zip(trace, built_pre))
        assert len(d0) == len(d1)
        assert d1[-1] < 0.5 * d0[-1] and d1[int(0.9 * len(d1))] < 0.5 * d0[int(0.9 * len(d0))], (d0[-1], d1[-1])
    finally:
        shutil.rmtree(ws, ignore_errors=True)
        shutil.rmtree(ws2, ignore_errors=True)


def test_milford_config_keeps_the_smoothing_in_metres():
    c = json.loads((ROOT / "tracks" / MF / "track.config.json").read_text(encoding="utf-8"))
    li, route = c["lm_intake"], c["route"]
    assert li["line_precomp"] is True
    # route.smooth_sigma_pts x lm_intake.resample_m: 7.5 m, the audit's modelled sigma 5 pts at 1.5 m
    assert abs(float(route["smooth_sigma_pts"]) * float(li["resample_m"]) - 7.5) < 1e-9
    front, flares = li["edge_retrace"]
    # the GM line (ledger 0102: 0.1.14's 4,530 re-read by position on it)
    assert front.get("mode", "widen") == "widen" and front["spans"] == [[4355.5, 150.0]]
    assert flares["mode"] == "agree" and float(flares.get("taper_m", 60.0)) == 60.0
    assert "smooth_m" not in flares                       # the agree record keeps the tool's 8 m smoothing


def test_the_0091_options_are_milfords_alone():
    cfgs = {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "tracks").glob("*/track.config.json")}

    def names(key):
        return sorted(t for t, c in cfgs.items() if (c.get("lm_intake") or {}).get(key))
    assert names("line_precomp") == [MF]
    assert names("width_smooth_m") == [MF]
    agree = sorted(t for t, c in cfgs.items()
                   if any(isinstance(r, dict) and r.get("mode") == "agree"
                          for r in (lambda e: e if isinstance(e, list) else [e])((c.get("lm_intake") or {}).get("edge_retrace") or {})))
    assert agree == [MF]
    assert "lm_intake" not in cfgs.get("san-diego-lake-murray", {})      # Lake Murray runs no intake
    text = (ROOT / "tools" / "lm_engine_intake.py").read_text(encoding="utf-8")
    assert 'li.get("line_precomp")' in text and 'li.get("width_smooth_m")' in text


# ------------------------------------------------------------------------------------------------ 0092's ground, on this line
def test_the_corridor_reads_the_lane_edge_the_assembler_builds(tmp_path):
    """tools/lidar_ground_patch.py: a corridor patch's in0_m is read off the assembler's line (the route's smooth of the
    intake's line), not the intake's line itself, which lm_intake.line_precomp sets outside every bend"""
    np = __import__("pytest").importorskip("numpy")
    import lidar_ground_patch as lgp
    import lm_engine_intake as L
    r = 60.0
    n = int(round(2 * math.pi * r / 1.5))
    trace = _loop(n=n, r=r)
    line_pts, _rep = L.precomp_line(trace, True, sm, sigma_pts=5.0, passes=2)    # the intake's line, as Milford's
    proj = tmp_path / "p"
    (proj / "data").mkdir(parents=True)
    (proj / "source").mkdir()
    g = np.full((240, 240), 500, np.int16)                    # flat ground, 240 x 240 m about the circle
    np.savez(proj / "source" / "grid.npz", e0=np.int64(-120), n0=np.int64(-120), cell=np.float64(1.0), nx=np.int64(240),
             ny=np.int64(240), z0_m=np.float64(100.0), ground_z_cm_over_z0=g)
    line = {"origin": {"lon": 0.0, "lat": 0.0, "elev_m": 100.0}, "points_xyz_m": [list(p) for p in line_pts],
            "widths_m": [12.0] * len(line_pts)}
    (proj / "data" / "centerline.local.json").write_text(json.dumps(line), encoding="utf-8")
    cor = {"in0_m": 9.0, "in1_m": 16.0, "full_m": 35.0, "zero_m": 45.0}
    (proj / "track.config.json").write_text(json.dumps({
        "route": {"smooth_sigma_pts": 5.0, "smooth_passes": 2},
        "terrain": {"lidar_patches_npz": "source/grid.npz", "lidar_patches_file": "data/patches.json",
                    "lidar_patches": [{"id": "corridor", "polygon": [[-100, -100], [100, -100], [100, 100], [-100, 100]],
                                       "corridor": cor}]}}), encoding="utf-8")
    assert lgp.main([str(proj)]) == 0
    c = json.loads((proj / "data" / "patches.json").read_text())["patches"]["corridor"]
    w = np.array(c["w"]).reshape(c["nz"], c["nx"])
    gx, gz = np.meshgrid(c["x0"] + np.arange(c["nx"]), c["z0"] + np.arange(c["nz"]))
    built = lgp.assembler_line(line, {"smooth_sigma_pts": 5.0, "smooth_passes": 2})
    d_built = lgp.lane_edge_distance(built, gx[w > 0], gz[w > 0])
    d_intake = lgp.lane_edge_distance(line, gx[w > 0], gz[w > 0])
    assert d_built.min() >= 9.0 - 1e-6, d_built.min()        # nothing weighted inside the 9 m drive_test reach
    assert d_intake.min() < 8.6                               # (off the intake's own line it would have been ~1 m short)


def test_the_run_off_pads_are_outlined_off_this_line():
    """source/runoff/runoff_pads.json was made off this config's intake line (ledger 0091 re-ran it): none folds, and every
    kept pad that meets the lane edge starts at the edge strip's lip of the line the assembler builds"""
    rec = json.loads((ROOT / "tracks" / MF / "source" / "runoff" / "runoff_pads.json").read_text(encoding="utf-8"))
    kept = [b for b in rec["blobs"] if b["kept"]]
    assert rec["line"]["frame"].startswith("the intake's data/centerline.local.json through the route's own smoothing")
    # GM's loop (ledger 0102): 18 off its line (0.1.14's lap: 19)
    assert len(kept) == 18 and rec["left_out"] == 5 and all(b["folds"] == 0 for b in kept)
    assert sum(b.get("rows_dropped", 0) for b in rec["blobs"]) <= 2

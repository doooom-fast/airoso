"""tools/width_hold.py, lm_intake.width_hold (ledger 0103; Kevin 2026-11-24: "Long smooth curves get weird blooms" /
"Look at the side lines"): a width swell the measured edges do not carry is held to a straight fit; one they do carry is
refused; the blend is a raised cosine; no key, no work."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import width_hold as wh  # noqa: E402

R = 90.0          # a long left-hand arc, 300 m of it, points every 0.75 m
STEP = 0.75


def _arc(n=401):
    return [(R * math.sin(i * STEP / R), 0.0, R - R * math.cos(i * STEP / R)) for i in range(n)]


def _swell(s, a=120.0, b=200.0, h=1.2):
    """a cosine bump of height h over [a, b] (the trace's bloom)"""
    if a <= s <= b:
        return h * 0.5 * (1 - math.cos(2 * math.pi * (s - a) / (b - a)))
    return 0.0


def _evidence(pts, s, width_of):
    """measured edge points, 3 a side every 0.75 m, at +-width/2 off the arc (no noise)"""
    out = []
    for k in range(1, len(pts) - 1):
        tx, tz = pts[k + 1][0] - pts[k - 1][0], pts[k + 1][2] - pts[k - 1][2]
        tn = math.hypot(tx, tz)
        nx, nz = -tz / tn, tx / tn
        half = width_of(s[k]) / 2
        for sd in (1, -1):
            for j in range(3):
                out.append([pts[k][0] + sd * (half + 0.01 * j) * nx, pts[k][2] + sd * (half + 0.01 * j) * nz, "naip", 30])
    return out


def test_a_swell_the_measured_edge_does_not_carry_is_held_to_the_measured_width():
    pts = _arc(); s = wh.arc(pts)
    trace = [11.0 + _swell(v) for v in s]
    ev = _evidence(pts, s, lambda v: 11.0)                       # the pavement keeps 11 m
    out, rep = wh.hold(pts, trace, False, [[60.0, 260.0]], 15.0, ev)
    inside = [out[k] for k in range(len(s)) if 60 <= s[k] <= 260]
    assert max(inside) - min(inside) < 0.05 and abs(sum(inside) / len(inside) - 11.0) < 0.05
    sp = rep["spans"][0]
    bm = sp["built_minus_measured_width_m"]
    assert bm["after"]["rms_about_it"] < bm["before"]["rms_about_it"] and abs(bm["after"]["median"]) < 0.05
    assert sp["edge_moved_m"]["max"] > 0.5                       # the 1.2 m swell, half a side
    # outside the span + blend nothing moves
    assert all(out[k] == trace[k] for k in range(len(s)) if s[k] < 60 - 15 or s[k] > 260 + 15)


def test_a_swell_the_measured_edge_carries_too_is_refused():
    pts = _arc(); s = wh.arc(pts)
    trace = [11.0 + _swell(v) for v in s]
    ev = _evidence(pts, s, lambda v: 11.0 + _swell(v))          # the pavement really widens
    try:
        wh.hold(pts, trace, False, [[60.0, 260.0]], 15.0, ev)
    except SystemExit as e:
        assert "WORSE" in str(e)
    else:
        raise AssertionError("a real widening was held")


def test_too_few_measured_bins_refuse_and_spans_are_checked():
    pts = _arc(); s = wh.arc(pts)
    trace = [11.0 + _swell(v) for v in s]
    for spans, msg in (([[60.0, 260.0]], "bins measured"), ([[260.0, 60.0]], "0 <= a < b"), ([[60.0, 1e6]], "0 <= a < b")):
        try:
            wh.hold(pts, trace, False, spans, 15.0, [])
        except SystemExit as e:
            assert msg in str(e), str(e)
        else:
            raise AssertionError(spans)


def test_the_blend_is_a_raised_cosine_and_the_fit_drops_outlying_bins():
    assert wh.weight(100.0, 100.0, 200.0, 15.0) == 1.0 and wh.weight(85.0, 100.0, 200.0, 15.0) == 0.0
    assert abs(wh.weight(92.5, 100.0, 200.0, 15.0) - 0.5) < 1e-12 and abs(wh.weight(207.5, 100.0, 200.0, 15.0) - 0.5) < 1e-12
    # 40 measured bins on a 0.2 %/m ramp, a +-3 cm scatter, three bins 1-2 m off (a junction's apron read as road)
    t = [2.5 + 5.0 * i for i in range(40)]
    w = [10.0 + 0.002 * x + 0.03 * (-1) ** i for i, x in enumerate(t)]
    for i, d in ((7, 1.5), (8, 2.0), (30, -1.0)):
        w[i] += d
    a, b = wh.robust_line(t, w)
    assert abs(a - 10.0) < 0.02 and abs(b - 0.002) < 0.0002


def test_width_hold_is_opt_in_and_the_intake_runs_it_only_with_the_key():
    text = (ROOT / "tools" / "lm_engine_intake.py").read_text(encoding="utf-8")
    assert 'wh_cfg = li.get("width_hold")' in text and "    if wh_cfg:\n" in text
    assert '**({"width_hold": width_hold_rep} if width_hold_rep else {}),' in text
    # it runs after width_smooth and before edge_retrace
    assert text.index('wsm = li.get("width_smooth_m")') < text.index('wh_cfg = li.get("width_hold")') \
        < text.index('er_cfg = li.get("edge_retrace")')
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        li = json.loads(cfgp.read_text(encoding="utf-8")).get("lm_intake") or {}
        if "width_hold" in li:
            assert cfgp.parent.name == "milford-road-course-lm", cfgp


def test_milford_holds_its_two_long_curves_and_its_committed_line_carries_the_hold():
    mf = ROOT / "tracks" / "milford-road-course-lm"
    cfg = json.loads((mf / "track.config.json").read_text(encoding="utf-8"))
    wcfg = cfg["lm_intake"]["width_hold"]
    assert cfg["version"] == "0.1.16"
    assert wcfg["spans"] == [[1114.0, 1270.0], [1557.0, 1857.0]] and wcfg["blend_m"] == 15.0
    assert wcfg["evidence"] == "source/edges/edge_evidence_gm.json"
    src = (mf / "source" / "round3" / "edit_config_0103.py").read_text(encoding="utf-8")
    assert 'li["width_hold"] = {' in src and wcfg["_doc"] in src.replace('\\"', '"').replace('"\n        "', "")
    # the committed swept line (predict_lines_0102.py: the build's own bytes) is straight in width across each span
    loc = json.loads((mf / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts, w = loc["points_xyz_m"], loc["widths_m"]
    s = wh.arc(pts)
    for a, b in wcfg["spans"]:
        rows = [k for k in range(len(s)) if a + 2 <= s[k] <= b - 2]
        fa, fb = wh._lsq([s[k] for k in rows], [w[k] for k in rows])
        assert max(abs(w[k] - (fa + fb * s[k])) for k in rows) < 0.01, (a, b)

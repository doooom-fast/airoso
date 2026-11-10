"""tools/edge_fit.py + tools/edge_smoothness.py (ledger 0087): the lane edges re-fitted with outliers cut, and the built edges
measured and gated.

edge_fit: a 1-2 row spike the evidence does not support is cut (and logged); a sustained width change stays; a spike the
evidence supports stays. edge_smoothness: a clean straight ribbon passes the gate, the same ribbon with one notched row
fails it. Both are opt-in: only Milford's config names lm_intake.edge_fit, only its ship.json names the gate.
"""

from __future__ import annotations

import importlib.util
import json
import math
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ef = _load("edge_fit")
es = _load("edge_smoothness")


def _line(n=300, step=1.5):
    """an open straight line due north, x = 0"""
    return [(0.0, 0.0, i * step) for i in range(n)]


def test_a_spike_is_cut_and_logged():
    pts = _line()
    w = [10.0] * len(pts)
    w[150] = 11.0                                   # one row 0.5 m proud a side
    new, rep = ef.fit_widths(pts, w, False, [], mode="judge", half=15.0)
    assert abs(new[150] - 10.0) < 0.02, new[150]
    assert all(abs(x - 10.0) < 0.02 for x in new)
    rej = [r for r in rep["rejections"] if r["rejected"]]
    assert {r["row"] for r in rej} == {150} and {r["reason"] for r in rej} == {"spike"}
    assert {r["side"] for r in rej} == {"left", "right"}


def test_a_sustained_change_stays():
    pts = _line()
    w = [10.0] * 100 + [10.0 + 0.2 * k for k in range(1, 11)] + [12.0] * 190   # a 15 m ramp to a 285 m plateau
    new, rep = ef.fit_widths(pts, w, False, [], mode="judge", half=15.0)
    assert abs(new[200] - 12.0) < 0.02 and abs(new[50] - 10.0) < 0.02
    assert not [r for r in rep["rejections"] if r["rejected"]]


def test_a_spike_the_evidence_supports_stays():
    pts = _line()
    w = [10.0] * len(pts)
    w[150] = w[151] = 11.0
    # the evidence reads the left edge at 5.5 m (the spike's), along rows 148-153
    ev = [[-5.5, (148 + k * 0.5) * 1.5, "lidar", 9000] for k in range(12)]
    new, rep = ef.fit_widths(pts, w, False, ev, mode="judge", half=15.0)
    kept = [r for r in rep["rejections"] if r["side"] == "left" and not r["rejected"]]
    cut = [r for r in rep["rejections"] if r["side"] == "right" and r["rejected"]]
    assert kept and {r["reason"] for r in kept} == {"kept_spike_supported"}
    assert cut and {r["reason"] for r in cut} == {"spike"}


def _ribbon_obj(path: Path, notch_row=None, n=200, step=1.0, hw=5.0):
    V, F = [], []
    for i in range(n):
        h = hw + (0.15 if i == notch_row else 0.0)
        V += [(-h, 0.0, i * step), (0.0, 0.0, i * step), (h, 0.0, i * step)]
    for i in range(n - 1):
        l0, c0, r0 = 3 * i + 1, 3 * i + 2, 3 * i + 3        # 1-based
        l1, c1, r1 = l0 + 3, c0 + 3, r0 + 3
        F += [(l0, c0, c1), (l0, c1, l1), (c0, r0, r1), (c0, r1, c1)]
    lines = ["g 1ROAD_road"] + [f"v {x} {y} {z}" for x, y, z in V] + [f"f {a} {b} {c}" for a, b, c in F]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _gate(notch_row):
    with tempfile.TemporaryDirectory() as t:
        p = Path(t)
        (p / "data").mkdir()
        _ribbon_obj(p / "data" / "track.obj", notch_row)
        (p / "data" / "gate_centerline.json").write_text(json.dumps(
            {"points_xyz_m": [[0.0, 0.0, i * 1.0] for i in range(200)], "widths_m": [10.0] * 200}), encoding="utf-8")
        return es.main([str(p), "--gate-default", "--quiet", "--json", str(p / "out.json")]), \
            json.loads((p / "out.json").read_text(encoding="utf-8"))


def test_a_clean_ribbon_passes_the_gate():
    rc, rep = _gate(None)
    assert rc == 0 and rep["gate"]["verdict"] == "PASS"
    assert rep["lane_edge"]["left"]["d2_m"]["max"] < 1e-3


def test_a_notched_ribbon_fails_the_gate():
    rc, rep = _gate(100)
    assert rc == 1 and rep["gate"]["verdict"] == "FAIL"
    assert rep["ragged_runs"]["lane_edge"] >= 2              # both sides
    assert math.isclose(rep["lane_edge"]["left"]["d2_m"]["max"], 0.30, abs_tol=0.02)


def test_both_are_opt_in():
    """only Milford's port names lm_intake.edge_fit / the edge_smoothness gate (ledger 0087); Lake Murray runs no intake"""
    fit = sorted(p.parent.name for p in (ROOT / "tracks").glob("*/track.config.json")
                 if ((json.loads(p.read_text(encoding="utf-8")).get("lm_intake") or {}).get("edge_fit")))
    assert fit == ["milford-road-course-lm"]
    gate = sorted(p.parent.name for p in (ROOT / "tracks").glob("*/ship.json")
                  if "edge_smoothness" in json.loads(p.read_text(encoding="utf-8"))["steps"].get("gate", []))
    assert gate == ["milford-road-course-lm"]
    text = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    assert "gate_edge_smoothness() {" in text and "python tools/edge_smoothness.py \"$PROJ\" --gate-default" in text

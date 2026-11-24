"""tools/edge_design.py (lm_intake.width_design) and tools/edge_bulges.py (ledger 0103; Kevin 2026-11-24: "Look for
primarily bulges during otherwise smooth curves and straights" / "Dreaded slop, a human would never do it"): the layout
takes out what goes out and comes back, keeps steps and tapers; a bulge the measured edge carries is real; the design
takes out only the others, nothing else moves; the intake runs it only with the key."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import edge_design as ED  # noqa: E402

MF = ROOT / "tracks" / "milford-road-course-lm"


def _bump(s, a, b, h):
    return h * 0.5 * (1 - math.cos(2 * math.pi * (s - a) / (b - a))) if a <= s <= b else 0.0


def _road(n=4700):
    """an 11 m road: a 1.2 m swell (120 m), a 0.5 m swell (190 m), a 0.6 m pinch (60 m), a real +3 m step, a real taper"""
    s = [float(i) for i in range(n)]
    y = [11.0 + _bump(t, 1500, 1620, 1.2) + _bump(t, 600, 790, 0.5) - _bump(t, 3500, 3560, 0.6)
         + (3.0 if t > 2000 else 0.0) - min(max((t - 3000) / 60.0, 0.0), 1.0) * 3.0 for t in s]
    return s, y


def test_the_layout_takes_out_what_comes_back_and_keeps_steps_and_tapers():
    s, y = _road()
    lay = ED.layout(y, True)
    assert abs(lay[1560] - 11.0) < 1e-9 and abs(lay[700] - 11.0) < 1e-9 and abs(lay[3530] - 11.0) < 1e-9
    assert all(abs(lay[k] - y[k]) < 1e-9 for k in list(range(1900, 2100)) + list(range(2950, 3100)))   # step, taper
    ex = ED.excursions(y, lay)
    got = sorted((e["dir"], round(e["amp_m"], 2)) for e in ex)
    assert got == [(-1, 0.6), (1, 0.5), (1, 1.2)], got
    d = ED.designed(y, [(e["i0"], e["i1"]) for e in ex], lay)
    assert max(abs(d[k] - 11.0) for k in range(1490, 1630)) < 0.035                  # the feet are under EPS_M
    assert all(d[k] == y[k] for k in range(1900, 2100))


def _line(n=4700):
    """a closed lap of a circle (R ~748 m), points every 1 m, z north"""
    R = n / (2 * math.pi)
    return [(R * math.cos(2 * math.pi * i / n), 0.0, R * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _evidence(pts, width_of, every=2):
    """measured edge points, 3 a side every `every` m at +-width/2 (no noise)"""
    out = []
    n = len(pts)
    for k in range(0, n, every):
        a, b = pts[k - 1], pts[(k + 1) % n]
        tx, tz = b[0] - a[0], b[2] - a[2]
        tn = math.hypot(tx, tz)
        nx, nz = -tz / tn, tx / tn
        for sd in (1, -1):
            for j in range(3):
                h = width_of(float(k)) / 2 + 0.01 * j
                out.append([pts[k][0] + sd * h * nx, pts[k][2] + sd * h * nz, "naip", 30])
    return out


def test_the_design_takes_out_only_what_the_measured_edge_does_not_carry():
    pts = _line()
    w = [11.0 + _bump(t, 1500, 1620, 1.2) + _bump(t, 3000, 3100, 0.8) for t in range(len(pts))]
    # the measured road keeps 11 m at s 1,500-1,620 (ours) and really widens at s 3,000-3,100 (real)
    ev = _evidence(pts, lambda t: 11.0 + _bump(t, 3000, 3100, 0.8))
    out, rep = ED.design_width(pts, w, True, ev, None, held=[[2500.0, 2600.0]])
    assert rep["before"]["ours"] == 1 and rep["before"]["real"] == 1 and rep["after"]["ours"] == 0
    assert max(abs(out[k] - 11.0) for k in range(1495, 1625)) < 0.04
    assert all(abs(out[k] - w[k]) < 1e-12 for k in range(2950, 3150))                 # the real one kept
    assert all(out[k] == w[k] for k in range(0, 1450))                                # nothing else moves, to the bit
    # a held span is never touched, even with a bulge in it
    w2 = [11.0 + _bump(t, 2510, 2590, 1.0) for t in range(len(pts))]
    out2, rep2 = ED.design_width(pts, w2, True, _evidence(pts, lambda t: 11.0), None, held=[[2500.0, 2600.0]])
    assert out2 == w2 and rep2["before"]["ours"] == 0 and any(b["held"] for b in rep2["bulges"])


def test_a_bulge_nobody_measured_is_kept_and_reported():
    pts = _line()
    w = [11.0 + _bump(t, 1500, 1620, 1.2) for t in range(len(pts))]
    out, rep = ED.design_width(pts, w, True, [], None)
    assert out == w and rep["before"]["unmeasured"] == 1 and rep["taken_out"] == []


def test_the_lidar_edges_judge_where_they_cover():
    pts = _line()
    w = [11.0 + _bump(t, 1500, 1620, 1.2) for t in range(len(pts))]
    lid = {"spans": [{"s": [1400.0, 1700.0]}],
           "stations": [{"s": float(t), "left": {"u_m": 5.5}, "right": {"u_m": -5.5}} for t in range(1400, 1701)]}
    # the evidence (outside the lidar's span ignored there) says the bulge is real; the lidar, where it covers, says not
    ev = _evidence(pts, lambda t: 11.0 + _bump(t, 1500, 1620, 1.2))
    out, rep = ED.design_width(pts, w, True, ev, lid)
    assert rep["before"]["ours"] == 1 and max(abs(out[k] - 11.0) for k in range(1495, 1625)) < 0.04


def test_width_design_is_opt_in_runs_after_width_hold_and_before_the_retrace():
    text = (ROOT / "tools" / "lm_engine_intake.py").read_text(encoding="utf-8")
    assert 'wd_cfg = li.get("width_design")' in text and "    if wd_cfg:\n" in text
    assert '**({"width_design": width_design_rep} if width_design_rep else {}),' in text
    assert text.index('wh_cfg = li.get("width_hold")') < text.index('wd_cfg = li.get("width_design")') \
        < text.index('er_cfg = li.get("edge_retrace")')
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        li = json.loads(cfgp.read_text(encoding="utf-8")).get("lm_intake") or {}
        if "width_design" in li:
            assert cfgp.parent.name == "milford-road-course-lm", cfgp


def test_milford_names_it_its_script_writes_it_and_its_committed_line_carries_it():
    cfg = json.loads((MF / "track.config.json").read_text(encoding="utf-8"))
    wd = cfg["lm_intake"]["width_design"]
    assert cfg["version"] == "0.1.16" and "width_hold" not in cfg["lm_intake"]
    assert wd["held"] == [[750.0, 1045.0]] and wd["evidence"] == "source/edges/edge_evidence_gm.json"
    assert (MF / wd["lidar_edges"]).exists() and cfg["edge_bulges"]["skip"] == wd["held"]
    spec = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    assert wd["lidar_edges"] in spec["sync_in"]["required"] and "data/width_design.json" in spec["sync_out"]["files"]
    src = (MF / "source" / "round3" / "edit_config_0103.py").read_text(encoding="utf-8")
    assert 'li["width_design"] = {' in src and 'li.pop("width_hold", None)' in src
    # the committed swept line (predict_lines_0102.py: the build's own bytes) has no bulge the measured edge does not
    # carry left outside the held stretches but the one the design's own re-scan logs (s 1,342-1,420, 0.15 m)
    loc = json.loads((MF / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    ev = json.loads((MF / wd["evidence"]).read_text(encoding="utf-8"))["points"]
    lid = json.loads((MF / wd["lidar_edges"]).read_text(encoding="utf-8"))
    held = list(wd["held"])
    for r_ in cfg["lm_intake"]["edge_retrace"]:
        held += [[a - r_.get("taper_m", 60.0), b + r_.get("taper_m", 60.0)] for a, b in r_["spans"]]
    _, rep = ED.design_width(loc["points_xyz_m"], loc["widths_m"], True, ev, lid, held)
    assert rep["before"]["ours"] <= 2, [b for b in rep["bulges"] if b["verdict"] == "ours" and not b["held"]]


def test_edge_bulges_reports_a_line(tmp_path=None):
    tmp = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    pts = _line()
    w = [11.0 + _bump(t, 1500, 1620, 1.2) + _bump(t, 3000, 3100, 0.8) for t in range(len(pts))]
    (tmp / "source").mkdir(parents=True, exist_ok=True)
    (tmp / "source" / "ev.json").write_text(json.dumps({"points": _evidence(pts, lambda t: 11.0 + _bump(t, 3000, 3100, 0.8))}))
    (tmp / "track.config.json").write_text(json.dumps({"loop": True, "edge_bulges": {"evidence": "source/ev.json"}}))
    (tmp / "line.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": w}))
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "edge_bulges.py"), str(tmp), "--line", str(tmp / "line.json"),
                        "--out", str(tmp / "rep.json")], capture_output=True, text=True)
    if r.returncode != 0 and "numpy" in (r.stderr or ""):
        return                                                  # the report needs numpy; the PC's system python has none
    assert r.returncode == 0, r.stderr
    rep = json.loads((tmp / "rep.json").read_text())
    assert rep["series"]["width"]["count"] == {"ours": 1, "real": 1, "unmeasured": 0}

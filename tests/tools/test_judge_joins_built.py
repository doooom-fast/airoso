"""judge_joins_built.py (ledger 0054 Phase 2): a lane band that moves through a join is re-seated, not read as a step;
a real step is still one. Synthetic lap, lane and road; the frame check is the repo's and is stubbed here."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tracks" / "san-diego-lake-murray" / "source" / "expansion" / "phase2"))
import judge_joins_built as J  # noqa: E402

SLOPE = 0.03                       # 3 % grade along x: 0.015 m per 0.5 m sample (no bump), 0.33 m over 11 m (a "step" if compared)


def _write_obj(path, slab_from_x=None, slab_h=0.15):
    """1ROAD_road: a grid x 0..60, z -6..6 at y = SLOPE * x; with slab_from_x, a 1KERB slab slab_h above it from that x on"""
    lines, n = [], 0

    def quad_grid(name, x0, x1, lift):
        nonlocal n
        lines.append(f"o {name}")
        base = n
        xs, zs = list(range(x0, x1 + 1)), list(range(-6, 7))
        for x in xs:
            for z in zs:
                lines.append(f"v {x} {SLOPE * x + lift} {z}")
                n += 1
        w = len(zs)
        for i in range(len(xs) - 1):
            for j in range(w - 1):
                a = base + i * w + j + 1
                b, c, d = a + w, a + w + 1, a + 1
                lines.append(f"f {a} {b} {c}")
                lines.append(f"f {a} {c} {d}")
    quad_grid("1ROAD_road", 0, 60, 0.0)
    if slab_from_x is not None:
        quad_grid("1KERB_slab", slab_from_x, 60, slab_h)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plan(tmp, shift):
    """a straight lap along +x, vertices 20..40 one join; with shift, the lane band leaves the lane's left half for v25..35"""
    d = tmp / "plan" / "data"
    d.mkdir(parents=True)
    pts = [[float(k), SLOPE * k, 0.0] for k in range(61)]
    src = [["join", 0] if 20 <= k <= 40 else ["road", 0] for k in range(61)]
    lanes = [[1.0, 4.0] if (shift and 25 <= k <= 35) else [-4.0, 4.0] for k in range(61)]
    (d / "lap.north.json").write_text(json.dumps({"points_xyz_m": pts, "joins": [{}], "source_by_vertex": src}))
    (d / "barrier_bands.north.json").write_text(json.dumps({"corridors": {"north_cw": {"lane_by_vertex": lanes}}}))
    (tmp / "gate.json").write_text("{}")
    return tmp / "plan"


def _judge(tmp, obj, plan, monkeypatch):
    monkeypatch.setattr(J, "frame_check", lambda p: (0.0, None))
    out = tmp / "out.json"
    J.main(["--obj", str(obj), "--gate-centerline", str(tmp / "gate.json"), "--plan", str(plan), "--json", str(out)])
    return json.loads(out.read_text())["rows"][0]["layouts"]["north_cw"]


def test_a_lane_band_that_moves_through_a_join_is_not_a_step(tmp_path, monkeypatch):
    obj = tmp_path / "road.obj"
    _write_obj(obj)
    plan = _plan(tmp_path, shift=True)
    assert _judge(tmp_path, obj, plan, monkeypatch)["severe_steps"] == 0
    monkeypatch.setattr(J, "RESEAT_M", 1e9)                 # without the re-seat: the stale 11 m compare reads as a step
    assert _judge(tmp_path, obj, plan, monkeypatch)["severe_steps"] > 0


def test_a_real_step_is_still_a_step(tmp_path, monkeypatch):
    obj = tmp_path / "road.obj"
    _write_obj(obj, slab_from_x=30)                          # a 0.15 m curb across the lane at x = 30
    plan = _plan(tmp_path, shift=False)
    v = _judge(tmp_path, obj, plan, monkeypatch)
    assert v["severe_steps"] > 0 and v["fail"]

"""tools/bench_pad.py (ledger 0078 round 13): a switchback platform traced as a pad from its lidar ground, and the lane the
intake reads on it (lm_intake.pad_widths)."""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import bench_pad as bp  # noqa: E402
import draft_pads as dp  # noqa: E402

UTD = ROOT / "tracks" / "rally-under-the-dragon-gravel-lm"


def _hillside(tmp_path):
    """a graded bench climbing 2 % along x between a fill face 4 m right of the line (z < -4, falling 0.6 per m) and a cut
    face 5 m left (z > 5, rising 0.8 per m), as tools/lidar_turns.py writes it: 0.5 m cells, a third of them empty"""
    c, n = 0.5, 240
    x0, z0 = -10.0, -60.0
    g = np.full((n, n), np.nan, dtype=np.float32)
    rng = np.random.default_rng(1)
    for j in range(n):
        for i in range(n):
            if rng.random() < 0.33:
                continue
            x, z = x0 + (i + 0.5) * c, z0 + (j + 0.5) * c
            h = 0.02 * x
            if z > 5.0:
                h += 0.8 * (z - 5.0)
            elif z < -4.0:
                h -= 0.6 * (-4.0 - z)
            g[j, i] = h
    f = tmp_path / "grid_S1.npz"
    np.savez(f, ground=g, x0=x0, z0=z0, cell_m=c, points=12345, ept="test", st_m=0.0, elev0=0.0)
    return bp.Lidar([f])


def test_the_platform_is_traced_between_its_faces_and_its_deck_is_the_ground(tmp_path):
    G = _hillside(tmp_path)
    P = [(3.0 * i, 0.06 * i, 0.0) for i in range(30)]
    W = [7.0] * len(P)
    ring, deck, lap, srcs = bp.measure(P, W, G, None, 5, 25, 15)
    assert set(srcs) == {"lidar face"}
    for x in lap:
        lo, hi = x["edge_m"]
        assert lo == pytest.approx(-4.0, abs=0.6) and hi == pytest.approx(5.0, abs=0.6), x
    # the outline: the bench (9 m) between the two cut lines (60 m), closed along them
    assert abs(dp.ring_area(ring)) == pytest.approx(9.0 * 60.0, rel=0.06)
    on_cut = [p for p in ring if abs(p[0] - 15.0) < 1e-6 or abs(p[0] - 75.0) < 1e-6]
    assert len(on_cut) >= 4
    # the deck: the bench's own plane
    for j in range(0, deck["ny"], 5):
        for i in range(0, deck["nx"], 5):
            v = deck["y"][j][i]
            x, z = deck["e0"] + i * deck["cell_m"], deck["n0"] + j * deck["cell_m"]
            if v is not None and -3.0 < z < 4.0:
                assert v == pytest.approx(0.02 * x, abs=0.02), (x, z, v)


def test_the_douglas_creek_record_is_complete_and_its_lane_stays_on_it():
    rec = json.loads((UTD / "source" / "pads" / "DC.json").read_text(encoding="utf-8"))
    cfg = json.loads((UTD / "track.config.json").read_text(encoding="utf-8"))
    decl = cfg["lm_pads"]["pads"][0]
    assert (rec["id"], rec["cuts"], rec["node"]) == (decl["id"], decl["cuts"], decl["node"])
    assert [x["k"] for x in rec["lap"]] == list(range(rec["cuts"][0], rec["cuts"][1] + 1))
    assert all(x["edge_m"][0] < 0 < x["edge_m"][1] and "raw_xz" in x for x in rec["lap"])
    assert dp.ring_area(rec["outline_en"]) > 0 and len(rec["deck"]["y"]) == rec["deck"]["ny"]
    assert "source/pads/DC.json" in json.loads((UTD / "ship.json").read_text(encoding="utf-8"))["sync_in"]["required"]


def test_the_intake_lays_the_lane_on_the_measured_platform_and_refuses_another_line(tmp_path):
    proj = tmp_path / "utd"
    (proj / "data").mkdir(parents=True)
    (proj / "source" / "pads").mkdir(parents=True)
    shutil.copyfile(UTD / "track.config.json", proj / "track.config.json")
    for f in ("road_seek.json", "switchbacks.json"):
        shutil.copyfile(UTD / "data" / f, proj / "data" / f)
    shutil.copyfile(UTD / "source" / "pads" / "DC.json", proj / "source" / "pads" / "DC.json")
    from tools import lm_engine_intake as li
    rep = li.intake(proj)
    pw = rep["pad_widths"][0]
    rec = json.loads((UTD / "source" / "pads" / "DC.json").read_text(encoding="utf-8"))
    line = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    W, P = line["widths_m"], line["points_xyz_m"]
    k0, k1 = rec["cuts"]
    for x in rec["lap"][1:-1]:
        assert W[x["k"]] <= 2.0 * min(-x["edge_m"][0], x["edge_m"][1]) + 1e-3          # never wider than measured
    for k in range(k0, k1 - 1):              # (the out-cut row is the ribbon's own, the weld: it may stand wider)
        ds = math.hypot(P[k + 1][0] - P[k][0], P[k + 1][2] - P[k][2])
        assert W[k + 1] - W[k] <= 2 * 0.1 * ds + 1e-2                                 # never steps up faster than the taper
    assert pw["cuts"] == [k0, k1]
    # a record measured on another line is refused
    bad = json.loads(json.dumps(rec))
    bad["lap"][3]["raw_xz"][0] += 0.5
    (proj / "source" / "pads" / "DC.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SystemExit, match="measured on another line"):
        li.intake(proj)


def test_a_switchback_seam_fades_from_its_row_not_its_line():
    """a hairpin: the out leg lies behind the in-cut row's infinite line; with seam "row" that row's departure does not
    reach it (lm_pads.pads[].seam; Douglas Creek's 0.2 m step at the out-cut, round 13)"""
    row = [(-3.0, 0.0, 1.0), (0.0, 0.0, 1.0), (3.0, 0.0, 1.0)]          # the in-cut row across x, the pad to +y
    cut = dp.row_cut(row, (0.0, 10.0))
    prof = dp.seam_profile([(cut, row)], lambda x, y: 0.8)               # the row stands 0.2 m over the measured ground
    behind_far = (20.0, -2.0)                                             # the other leg: behind the line, past the row's end
    assert dp.seam_offset(prof, *behind_far) == pytest.approx(0.2)       # the line's rule: the whole departure
    for s_ in prof:
        s_["near_row"] = True
    assert dp.seam_offset(prof, *behind_far) == pytest.approx(0.0, abs=1e-6)
    assert dp.seam_offset(prof, 0.0, 0.0) == pytest.approx(0.2)          # on the row: the weld, unchanged
    assert dp.seam_offset(prof, 1.0, 3.0) == pytest.approx(0.2 * 0.5 * (1 + math.cos(math.pi * 3.0 / prof[0]["fade"])))

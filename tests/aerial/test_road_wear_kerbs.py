"""Ledger 0084, High Plains 0.1.7: the race kerbs' levelled paint (scripts/aerial/road_wear.kerb_*) and the gate's own
reading of the line's rubber (tools/road_wear_check.make_darkness) against the bake's (road_wear.wear_at)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import numpy as np
    from scripts.aerial import road_wear as rw
except ImportError:                      # the PC's plain interpreter: the bake runs inside Blender, which bundles numpy
    np = None

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

if np is not None:
    import road_wear_check as rwc

    def test_kerb_spec_is_opt_in_and_a_power_of_two():
        assert rw.kerb_spec({}) is None and rw.kerb_spec({"kerbs": None}) is None
        k = rw.kerb_spec({"kerbs": {"_doc": "x"}})
        assert k == {"prefix": "1KERB_CIRCUIT_", "levels": 16}
        assert rw.kerb_spec({"kerbs": {"prefix": "1kerb_x_", "levels": 8}})["prefix"] == "1KERB_X_"
        for bad in (1, 12):
            try:
                rw.kerb_spec({"kerbs": {"levels": bad}})
            except ValueError:
                continue
            raise AssertionError(f"levels {bad} accepted")

    def test_no_kerbs_key_leaves_the_spec_as_milfords():
        """Milford's spec (no kerbs key) gains no key: its data/road_wear.json is unchanged by this pass."""
        s = rw.spec_from_config({"road_wear": {"surfaces": ["1ROAD"]}})
        assert "kerbs" not in s

    def test_levelled_paint_copy_zero_is_the_paint():
        rng = np.random.default_rng(3)
        base = rng.integers(0, 256, size=(8, 16, 3), dtype=np.uint8)
        step = rw.kerb_step(0.22, 16)
        at = rw.kerb_wear_atlas(base, 16, step)
        assert at.shape == (8, 256, 3)
        assert np.array_equal(at[:, :16], base)
        last = at[:, 15 * 16:]
        assert np.all(np.abs(last.astype(int) - np.round(base * (1 - 0.22)).astype(int)) <= 0)
        assert abs(step * 15 - 0.22) < 1e-12

    def test_levels_and_u():
        step = rw.kerb_step(0.22, 16)
        d = np.array([0.0, step * 0.49, step * 0.51, 0.22, 0.5])
        lv = rw.kerb_levels(d, step, 16)
        assert lv.tolist() == [0, 0, 1, 15, 15]
        u = rw.kerb_u(np.array([0.05, 0.45, 0.95]), np.array([0, 3, 15]), 16)
        assert np.allclose(u, [0.05 / 16, 3.45 / 16, 15.95 / 16])
        assert np.all(np.floor(u * 16) == [0, 3, 15])

    def test_gate_darkness_reads_the_bakes_rubber():
        """The gate's restated wear (pure python, the line json's rounding) gives each kerb face the level the bake gave it:
        a 200 m lap with a corner, faces scattered within 5 m of the line."""
        t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
        P = np.column_stack([60 * np.cos(t), 35 * np.sin(t), 2.0 + 0.5 * np.sin(2 * t)])
        w = dict(rw.DEFAULTS["wear"])
        I, _sp = rw.rubber_intensity(P, 2.0, w, True)
        line = {"P": P, "I": I, "closed": True, "layer_m": 10.0}
        reach = 0.5 * w["track_m"] + 4 * w["spread_m"]
        rng = np.random.default_rng(7)
        k = rng.integers(0, len(P), 600)
        n = rw.left_normals(P, True)
        off = rng.uniform(-5, 5, len(k))
        X = P[k, 0] + n[k, 0] * off; Y = P[k, 1] + n[k, 1] * off
        D = rw.wear_at(X, Y, 2.0, line, w, reach).astype(np.float64)
        step = rw.kerb_step(w["amplitude"], 16)
        lv = rw.kerb_levels(D, step, 16)
        dark = rwc.make_darkness([(np.round(P, 3).tolist(), np.round(I, 4).tolist())], True, w, 10.0, w["amplitude"])
        err = [abs(dark(x, y, 2.0) / step - L) for x, y, L in zip(X, Y, lv)]
        assert max(err) <= rwc.GATE["kerb_level_tol"]
        assert lv.max() >= 10 and (lv == 0).any()

    def test_gate_pip():
        sq = [[0, 0], [2, 0], [2, 1], [0, 1]]
        assert rwc._pip(1.0, 0.5, sq) and not rwc._pip(2.5, 0.5, sq) and not rwc._pip(1.0, -0.1, sq)

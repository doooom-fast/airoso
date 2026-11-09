"""scripts/aerial/road_wear.py (ledger 0084): the pieces the bake is built from. numpy only (skipped without it)."""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

try:
    import numpy as np
    from scripts.aerial import road_wear as rw
except ImportError:                      # the PC's plain interpreter: the bake runs inside Blender, which bundles numpy
    np = None

if np is not None:

    def test_no_key_no_spec():
        """Lake Murray names no road_wear key: the spec is None and nothing downstream runs."""
        assert rw.spec_from_config({}) is None
        assert rw.spec_from_config({"road_wear": {"enabled": False}}) is None
        s = rw.spec_from_config({"road_wear": {"surfaces": ["1road"], "wear": {"amplitude": 0.1}}})
        assert s["surfaces"] == ["1ROAD"] and s["wear"]["amplitude"] == 0.1 and s["wear"]["track_m"] == 1.6

    def test_png_round_trip_keeps_rgb_under_zero_alpha():
        img = np.zeros((8, 16, 4), dtype=np.uint8)
        img[..., 0] = np.arange(16)[None, :] * 15
        img[..., 1] = np.arange(8)[:, None] * 30
        img[..., 2] = 77
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.png"
            rw.write_png(p, img)
            back = rw.read_png_rgba(p)
        assert back.shape == img.shape and np.array_equal(back, img)

    def test_min_curvature_cuts_a_corner_inside_its_corridor():
        """A 90-degree corner of a 12 m road: the line uses the width (outside - inside - outside) and never leaves it."""
        corners = [(0.0, 0.0), (200.0, 0.0), (200.0, 200.0), (0.0, 200.0)]   # a 200 m square lap, sharp corners
        P = []
        for k in range(4):
            a0 = np.array(corners[k]); a1 = np.array(corners[(k + 1) % 4])
            for t in np.arange(0, 1, 0.01):
                P.append(a0 + (a1 - a0) * t)
        P = np.array(P)
        C, _e, lap = rw.resample(np.column_stack([P, np.zeros(len(P))]), 2.0, True)
        n = rw.left_normals(C)
        lo = np.full(len(C), -5.0); hi = np.full(len(C), 5.0)
        a = rw.min_curvature(C, n, lo, hi, iters=20000)
        assert a.min() >= -5.0 - 1e-9 and a.max() <= 5.0 + 1e-9
        line = C[:, :2] + a[:, None] * n
        k0 = float(np.sum(rw._lap2(C[:, :2], True) ** 2)); k1 = float(np.sum(rw._lap2(line, True) ** 2))
        assert k1 < 0.5 * k0
        # the outside edge on the straights' middle, five metres further in at the corner (the lap turns left: + is in)
        assert a.min() < -4.9 and float(a[0] - a[len(a) // 8]) > 4.0

    def test_tyre_profile_peaks_and_falls():
        u = np.linspace(-4, 4, 801)
        f = rw.tyre_profile(u, 1.6, 0.55)
        assert abs(f.max() - 1.0) < 0.02 and f[0] < 0.01 and f[-1] < 0.01
        assert abs(u[np.argmax(f)]) <= 0.8 + 1e-9

    def test_atlas_uvs_keep_the_detail_grid_and_never_repeat():
        """Faces in different cells land in different tiles; the detail UV (uv x multiplier) is x / 4, y / 4 mod 1."""
        spec = rw.spec_from_config({"road_wear": {}}) or rw.spec_from_config({"road_wear": {"enabled": True}})
        rng = np.random.default_rng(3)
        cen = rng.uniform(-300, 300, size=(400, 2))
        plan = rw.plan_atlas(cen, np.zeros(400), 6.3, spec)
        assert plan["margin_m"] % spec["detail_tile_m"] == 0 and plan["cell_m"] % spec["detail_tile_m"] == 0
        keys = rw.cell_keys(cen, np.zeros(400), plan, spec)
        slots = rw.tile_slots(keys, plan)
        assert len(set(slots.values())) == len(set(keys))
        mult = rw.detail_multiplier(plan, spec)
        for k, (x, y) in zip(keys[:50], cen[:50]):
            for dx, dy in ((0, 0), (5.9, -6.2), (-6.0, 6.0)):
                u, v = rw.uv_of(np.array([x + dx]), np.array([y + dy]), k, slots[k], plan, spec["texel_m"])
                assert 0 <= u[0] <= 1 and 0 <= v[0] <= 1
                pu = (u[0] * mult - (x + dx) / 4.0) % 1.0; pv = (v[0] * mult - (y + dy) / 4.0) % 1.0
                assert min(pu, 1 - pu) < 1e-6 and min(pv, 1 - pv) < 1e-6

    def test_tone_fills_shadow_from_lit_asphalt():
        """A shadow band (dark, blue) inside a lit road reads as the lit asphalt round it, not as a dark stripe."""
        h, w = 200, 200
        img = np.full((h, w, 3), 120, dtype=np.uint8)
        img[90:110, :, :] = (40, 45, 60)                     # a blue-ish shadow across the road
        aer = rw.Aerial(img, (-0.001, -0.001, 0.001, 0.001), (0.0, 0.0))
        grid = rw.Grid.around(-50, -50, 50, 50, 0.5, 4.0, 0.0)
        road = np.ones((grid.ny, grid.nx), dtype=bool)
        tone, st = rw.tone_field(aer, grid, road, rw.DEFAULTS["tone"])
        assert st["shadow_pct"] > 5
        assert abs(float(np.median(tone)) - 1.0) < 1e-3 and float(tone.min()) > 0.95

    def test_wear_sits_on_the_line():
        P = np.column_stack([np.arange(-50, 50, 2.0), np.zeros(50), np.zeros(50)])
        line = {"P": P, "I": np.ones(50), "closed": False}
        w = dict(rw.DEFAULTS["wear"])
        X, Y = np.meshgrid(np.zeros(1), np.linspace(-4, 4, 81))
        D = rw.wear_at(X, Y, None, line, w, 4.0)[:, 0]
        ys = np.linspace(-4, 4, 81)
        assert abs(float(np.sum(ys * D) / np.sum(D))) < 0.01
        assert abs(float(D.max()) - w["amplitude"]) < 0.01 and D[0] < 0.01 * w["amplitude"]

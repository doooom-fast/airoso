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

    # --- the paint repeats (Pueblo / Aspen, PC 2026-11-10: "1KERB_circuit_0: u 0.000..2.111 outside the paint texture") --
    def _run(us, rows=6):
        """A kerb run as tools/author_kerbs_blend.py lays one without a kerb.atlas cell: one section per row, u = the
        section's offsets / the painted width (here 0 .. 2.1: the faces [0.4, 1.3] and [1.3, 2.1] straddle 1.0 and 2.0),
        v = arc / 2 m. Returns per-loop (u, v), each loop's face, the face count (quads, loops in Blender's order)."""
        P = len(us)
        U = []; F = []
        for i in range(rows - 1):
            for p in range(P - 1):
                f = len(F); F.append(f)
                for (r, q) in ((i, p), (i, p + 1), (i + 1, p + 1), (i + 1, p)):
                    U.append((us[q], r * 1.5 / 2.0, f))
        U = np.array(U)
        return U[:, :2], U[:, 2].astype(np.int64), len(F)

    def test_repeating_paint_unwraps_each_face_and_keeps_every_texel():
        """Every point of every face reads the same paint texel as the stock exporter's wrap did (frac(u)), from its
        level's copy, darkened by that level; faces straddling 1.0 and 2.0 included; no face is split (the loops, and so
        the positions, are the input's)."""
        us = [0.0, 0.4, 1.3, 2.1]
        uv, fl, nf = _run(us)
        L = 16; step = rw.kerb_step(0.22, L)
        loc, shift = rw.kerb_unwrap(uv[:, 0], fl, nf)
        assert sorted(set(shift.tolist())) == [0.0, 1.0]                  # [0, .4] and [.4, 1.3] by 0; [1.3, 2.1] by 1
        assert loc.min() >= 0.0 and abs(loc.max() - 1.3) < 1e-12              # [0.4, 1.3] is the widest
        R = rw.kerb_repeats(float(loc.max()), L)
        assert R == 2
        rng = np.random.default_rng(11)
        Wp, Hp = 64, 256                                                  # kerb_redwhite.png's size
        paint = rng.integers(0, 256, size=(Hp, Wp, 3), dtype=np.uint8)
        at = rw.kerb_wear_atlas(paint, L, step, R)
        assert at.shape == (Hp, Wp * R * L, 3)
        lev = rng.integers(0, L, nf)                                      # any level per face
        u2 = rw.kerb_u(np.clip(loc, 0.0, float(R)), lev[fl], L, R).astype(np.float32).astype(np.float64)   # as stored
        assert len(u2) == len(uv) and np.array_equal(uv[:, 1], _run(us)[0][:, 1])   # v untouched, no loop added
        checked = 0
        for f in range(nf):
            ls = np.nonzero(fl == f)[0]
            ua, ub = uv[ls, 0].min(), uv[ls, 0].max()
            sa, sb = u2[ls][np.argmin(uv[ls, 0])], u2[ls][np.argmax(uv[ls, 0])]
            assert np.floor(sa * L) == np.floor(sb * L) == lev[f]          # every corner inside its level's copy
            # every texel centre the face covers: the wrap read column c of the paint; the shipped u (linear across
            # the face, as the GPU interpolates it) reads the same column of copy lev[f]
            for n in range(int(np.floor(ua)), int(np.ceil(ub))):
                for c in range(Wp):
                    u = n + (c + 0.5) / Wp
                    if not (ua <= u <= ub):
                        continue
                    t = (u - ua) / (ub - ua)
                    x = int(np.floor((sa + t * (sb - sa)) * at.shape[1]))
                    assert x // (Wp * R) == lev[f] and x % Wp == c, (f, u, x)
                    want = np.clip(np.round(paint[:, c].astype(np.float64) * (1 - lev[f] * step)), 0, 255)
                    assert np.array_equal(at[:, x], want.astype(np.uint8))
                    checked += 1
        assert checked > 3 * Wp

    def test_paint_inside_one_repeat_is_high_plains_byte_for_byte():
        """High Plains 0.1.7's cells (u 0.05 .. 0.95): unwrapped by exactly 0, one tile per copy, so its UVs and atlas
        are the arithmetic it shipped with, bit for bit."""
        rng = np.random.default_rng(5)
        u = rng.uniform(0.05, 0.95, 400); fl = np.repeat(np.arange(100), 4)
        loc, shift = rw.kerb_unwrap(u, fl, 100)
        assert not shift.any() and np.array_equal(loc.view(np.int64), u.view(np.int64))
        L = 16; step = rw.kerb_step(0.15771, L)
        assert rw.kerb_repeats(float(loc.max()), L) == 1 and rw.kerb_repeats(0.95, L) == 1
        lev = rng.integers(0, L, 100)[fl]
        old_u = (lev.astype(np.float64) + np.clip(u, 0.0, 1.0)) / L          # 0.1.7's kerb_u(clip(u, 0, 1), lev, L)
        assert np.array_equal(rw.kerb_u(np.clip(loc, 0.0, 1.0), lev, L, 1).view(np.int64), old_u.view(np.int64))
        base = rng.integers(0, 256, size=(256, 128, 3), dtype=np.uint8)
        old_at = np.empty((256, 128 * L, 3), dtype=np.uint8)
        for k in range(L):
            old_at[:, k * 128:(k + 1) * 128] = np.clip(np.round(base.astype(np.float64) * (1.0 - k * step)), 0, 255)
        assert np.array_equal(rw.kerb_wear_atlas(base, L, step, 1), old_at)

    def test_repeats_keep_the_copy_edge_off_the_next_copy():
        """A face reaching the copy's right edge (u 1.0 exactly) takes the next power of two: its corner would otherwise
        be stored as copy k + 1's first column (floor(u x levels) = k + 1)."""
        assert rw.kerb_repeats(1.0, 16) == 2 and rw.kerb_repeats(1.111, 16) == 2 and rw.kerb_repeats(2.0, 16) == 4
        assert rw.kerb_repeats(0.0, 16) == 1
        u = np.array([0.0, 1.0]); lev = np.array([15, 15])
        s = rw.kerb_u(u, lev, 16, rw.kerb_repeats(1.0, 16)).astype(np.float32)
        assert np.all(np.floor(s.astype(np.float64) * 16) == 15)

    def test_gate_kerb_paint_reads_the_repeated_copies():
        """kerb_paint judges an atlas of 16 copies x 2 tiles exactly: as built PASS, one texel of copy 3's second tile
        off by 2 FAIL."""
        import io
        import json
        import tempfile
        from PIL import Image
        rng = np.random.default_rng(2)
        paint = rng.integers(0, 256, size=(32, 16, 3), dtype=np.uint8)
        L = 16; step = rw.kerb_step(0.22, L); R = 2
        at = rw.kerb_wear_atlas(paint, L, step, R)
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            (proj / "textures").mkdir()
            Image.fromarray(paint).save(proj / "textures" / "kerb_redwhite.png")

            def rows_for(atlas):
                b = io.BytesIO(); Image.fromarray(atlas).save(b, format="PNG")
                kd = {"levels": L, "step": step, "amplitude": 0.22, "repeats": R, "materials": [], "faces": {},
                      "paint": {"kerb_redwhite.png": {"atlas": "a.png", "source": "kerb_redwhite.png"}}}
                decl = {"materials": {}, "spec": {"layer_m": 10.0}}
                return rwc.kerb_rows(proj, {"loop": True}, decl, kd, [], {"textures": {"a.png": b.getvalue()},
                                                                         "meshes": []}, [], dict(rw.DEFAULTS["wear"]))
            assert rows_for(at)["kerb_paint"]["pass"]
            bad = at.copy(); bad[0, 3 * 16 * R + 16 + 5, 0] ^= 2
            assert not rows_for(bad)["kerb_paint"]["pass"]
            assert not rows_for(at[:, : 16 * L])["kerb_paint"]["pass"]        # one tile per copy is not what was declared
            json.dumps(rows_for(at))

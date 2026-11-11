"""Ledger 0084, High Plains 0.1.7 (Kevin 2026-11-10: "Use the photo's rubber"): road_wear.rubber "photo" — the photo's
darkening across the line measured against its mirror (road_wear.photo_rubber), the gate's restatement
(road_wear_check.measure_photo), and the measured profile laid on kerb faces (photo_darkness_at / make_photo_darkness)."""
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

    def _lap():
        t = np.linspace(0, 2 * np.pi, 600, endpoint=False)
        C = np.column_stack([200 * np.cos(t), 120 * np.sin(t), np.zeros(len(t))])
        C, _e, _L = rw.resample(C, 2.0, True)
        n = rw.left_normals(C, True)
        th = np.arctan2(C[:, 1] / 120, C[:, 0] / 200)
        a = 3.0 * np.sin(2 * th)                              # the line swings 3 m either side of the centre
        P = np.column_stack([C[:, :2] + a[:, None] * n, C[:, 2]])
        return C, n, a, P

    def _tone_fn(C, n, P, depth=0.15, sigma=0.6, shift=0.0, crown=0.03):
        """tone: 1, a dark band of ``depth`` (Gaussian, sigma) on the line moved ``shift`` m left, and a crown symmetric
        about the centreline (which the mirror must take out)."""
        Pd, _e, _L = rw.resample(P, 0.25, True)
        nd = rw.left_normals(Pd, True)
        Pd = Pd[:, :2] + shift * nd

        def tone_at(x, y):
            X = np.ravel(x); Y = np.ravel(y)
            out = np.empty(len(X))
            for s0 in range(0, len(X), 512):
                q = np.stack([X[s0:s0 + 512], Y[s0:s0 + 512]], axis=1)
                d = np.sqrt(np.min(np.sum((q[:, None, :] - Pd[None]) ** 2, axis=2), axis=1))
                k = rw.nearest_station(q, C)
                lat = np.sum((q - C[k, :2]) * n[k], axis=1)
                out[s0:s0 + 512] = (1 - depth * np.exp(-d * d / (2 * sigma * sigma))) * (1 - crown * (1 - (lat / 6) ** 2))
            return out.reshape(np.shape(x))
        return tone_at

    def test_photo_mode_is_opt_in():
        s = rw.spec_from_config({"road_wear": {"surfaces": ["1ROAD"]}})
        assert "rubber" not in s and "photo" not in s          # Milford's spec: drawn, unchanged
        s = rw.spec_from_config({"road_wear": {"rubber": "photo"}})
        assert s["rubber"] == "photo"

    def test_mirror_measures_the_band_and_cancels_the_crown():
        C, n, _a, P = _lap()
        prof = rw.photo_rubber(_tone_fn(C, n, P), P, C, n, True)
        # the band alone, pooled over |u| <= 0.75 m: 1 - mean(1 - 0.15 g(u))
        u = np.array(prof["u"]); band = np.abs(u) <= 0.75
        want = 0.15 * float(np.mean(np.exp(-u[band] ** 2 / (2 * 0.36))))
        assert abs(prof["depth"] - want) < 0.006, (prof["depth"], want)
        assert abs(prof["centroid_m"]) < 0.05 and prof["stations"] > 100
        assert abs(prof["peak"] - 0.15) < 0.01
        shifted = rw.photo_rubber(_tone_fn(C, n, P, shift=0.5), P, C, n, True)
        assert 0.35 < shifted["centroid_m"] < 0.65            # a band left of the line reads left (+)

    def test_no_band_reads_no_rubber():
        C, n, _a, P = _lap()
        prof = rw.photo_rubber(_tone_fn(C, n, P, depth=0.0), P, C, n, True)
        assert abs(prof["depth"]) < 0.003 and prof["depth"] < rwc.GATE["photo_min_depth"]

    def test_gate_restatement_equals_the_bake():
        C, n, _a, P = _lap()
        tone_at = _tone_fn(C, n, P)
        prof = rw.photo_rubber(tone_at, P, C, n, True)
        got = rwc.measure_photo(P.tolist(), C[:, :2].tolist(), n.tolist(), True,
                                lambda x, y: float(tone_at(np.array([x]), np.array([y]))[0]), rw.PHOTO)
        assert got["stations"] == prof["stations"]
        assert abs(got["depth"] - prof["depth"]) < 1e-6 and abs(got["centroid_m"] - prof["centroid_m"]) < 1e-4

    def test_profile_on_kerb_faces_is_signed_and_matches_the_gate():
        C, n, _a, P = _lap()
        prof = {"u": [-1.0, 0.0, 1.0, 2.0], "D": [0.0, 0.10, 0.12, 0.02]}
        line = {"P": P, "closed": True, "layer_m": 10.0}
        nl = rw.left_normals(P, True)
        i = 40
        X = P[i, 0] + nl[i, 0] * np.array([0.0, 1.0, -0.5, 1.5, 3.0]); Y = P[i, 1] + nl[i, 1] * np.array([0.0, 1.0, -0.5, 1.5, 3.0])
        D = rw.photo_darkness_at(X, Y, 0.0, line, prof)
        assert np.allclose(D, [0.10, 0.12, 0.05, 0.07, 0.0], atol=2e-3), D
        dark = rwc.make_photo_darkness([(P.tolist(), [1.0] * len(P))], True, [prof], 10.0)
        assert np.allclose([dark(x, y, 0.0) for x, y in zip(X, Y)], D, atol=1e-9)

    def test_kerb_levels_take_the_measured_peak():
        step = rw.kerb_step(0.142, 16)
        assert rw.kerb_levels(np.array([0.142, 0.0, 0.142 * 8 / 15, 0.142 * 7.4 / 15]), step, 16).tolist() == [15, 0, 8, 7]


# --- road_wear.rubber "none" (Kevin 2026-11-10 "Tone only, no rubber"; Pueblo, Aspen, Grand Junction, Pikes Peak) --------
if np is not None:
    _AER = {"image": "x.png", "bbox_lonlat": [0, 0, 1, 1]}

    def test_rubber_mode_checks():
        assert rw.rubber_mode({}) == ("drawn", None)                       # Milford: unchanged
        assert rw.rubber_mode({"rubber": "photo", "aerial": _AER}) == ("photo", None)
        assert rw.rubber_mode({"rubber": "none", "aerial": _AER}) == ("none", None)
        assert rw.rubber_mode({"rubber": "photo"})[1]                      # photo / none need the aerial
        assert rw.rubber_mode({"rubber": "none"})[1]
        assert rw.rubber_mode({"rubber": "tone"})[1]                       # a typo is refused, not read as drawn
        err = rw.rubber_mode({"rubber": "none", "aerial": _AER, "kerbs": {"prefix": "1KERB_CIRCUIT_", "levels": 16}})[1]
        assert err and "kerbs" in err                                      # nothing to level the kerbs by
        assert rw.rubber_mode({"rubber": "photo", "aerial": _AER,          # High Plains 0.1.7: photo + kerbs, as before
                               "kerbs": {"prefix": "1KERB_CIRCUIT_", "levels": 16}}) == ("photo", None)

    def _measure(C, n, P, tone_at):
        return rwc.measure_photo(P.tolist(), C[:, :2].tolist(), n.tolist(), True,
                                 lambda x, y: float(tone_at(np.array([x]), np.array([y]))[0]), rw.PHOTO)

    def test_none_passes_the_photo_as_it_is_and_fails_a_drawn_band():
        C, n, _a, P = _lap()
        photo = _tone_fn(C, n, P, depth=0.0)                               # Grand Junction: no rubber in the photo
        dp = rw.photo_rubber(photo, P, C, n, True)
        assert dp["depth"] < rwc.GATE["photo_min_depth"]
        same = _measure(C, n, P, photo)                                    # the shipped atlas = the photo's tone
        assert rwc.photo_line_pass("none", same, dp)
        assert not rwc.photo_line_pass("photo", same, dp)                  # photo mode still needs the photo's rubber
        drawn = _tone_fn(C, n, P, depth=0.15)                              # a Milford-sized band drawn on top of it
        got = _measure(C, n, P, drawn)
        assert got["depth"] - dp["depth"] > rwc.GATE["photo_depth_tol"]
        assert not rwc.photo_line_pass("none", got, dp)

    def test_photo_verdict_unchanged():
        C, n, _a, P = _lap()
        photo = _tone_fn(C, n, P)                                          # High Plains: the photo shows its rubber
        dp = rw.photo_rubber(photo, P, C, n, True)
        got = _measure(C, n, P, photo)
        old = (got["stations"] >= 10 and dp["depth"] >= rwc.GATE["photo_min_depth"] and
               abs(got["depth"] - dp["depth"]) <= rwc.GATE["photo_depth_tol"] and
               abs(got["centroid_m"] - dp["centroid_m"]) <= rwc.GATE["photo_centroid_tol_m"])
        assert old and rwc.photo_line_pass("photo", got, dp) == old
        moved = dict(got, centroid_m=got["centroid_m"] + 0.3)
        assert not rwc.photo_line_pass("photo", moved, dp)                 # the centroid still judges photo mode
        assert rwc.photo_line_pass("none", moved, dp)                      # and not none (no rubber: noise)
        assert not rwc.photo_line_pass("drawn", got, dp)


# --- the gate measures on the bake's own cells (photo_mask; Grand Junction 0.1.4, 2026-11-11) ---------------------------
if np is not None:
    _TONE = {"shadow_lum": 0.72, "shadow_blue": 1.06, "paint_lum": 1.45, "fill_m": 3.0, "clip": [0.7, 1.3],
             "headroom_pct": 99.5}
    _PLAN = {"cell_m": 64.0, "margin_m": 4.0}
    _REG = {"dx_m": 0.75, "dy_m": 0.25}

    def _mask_scene(seed=3):
        """An oval road of varying width, its triangles, and a 0.3 m photo with paint and bluish shadow blobs on it."""
        from PIL import Image
        rng = np.random.default_rng(seed)
        t = np.linspace(0, 2 * np.pi, 240, endpoint=False)
        C = np.column_stack([70 * np.cos(t), 45 * np.sin(t), np.zeros(len(t))])
        n = rw.left_normals(C, True)
        hw = 5.0 + 1.5 * np.sin(3 * t)
        L = C[:, :2] + hw[:, None] * n; R = C[:, :2] - hw[:, None] * n
        tris = []
        for k in range(len(C)):
            k2 = (k + 1) % len(C)
            tris.append((tuple(L[k]), tuple(R[k]), tuple(R[k2])))
            tris.append((tuple(L[k]), tuple(R[k2]), tuple(L[k2])))
        lon0, lat0 = -108.55, 39.06
        m_lon, m_lat = rw.meters_per_degree(lat0)
        bbox = (lon0 - 90 / m_lon, lat0 - 65 / m_lat, lon0 + 90 / m_lon, lat0 + 65 / m_lat)
        w, h = 600, 434
        img = np.clip(120 + rng.normal(0, 6, (h, w, 3)), 0, 255)
        yy, xx = np.mgrid[0:h, 0:w]
        for _ in range(60):                                  # paint (bright) and shadow (dark, blue) blobs on the road
            k = rng.integers(len(C)); off = rng.uniform(-6, 6)
            px = (C[k, 0] + off * n[k, 0] + 90) / 0.3; py = (65 - (C[k, 1] + off * n[k, 1])) / (130 / h)
            r = rng.uniform(1.5, 5)
            m = (xx - px) ** 2 + (yy - py) ** 2 < r * r
            img[m] = (235, 235, 230) if rng.random() < 0.5 else (45, 50, 75)
        img = img.astype(np.uint8)
        return C, n, tris, img, Image.fromarray(img), bbox, (lon0, lat0)

    def _bake_mask(tris, img, bbox, origin, tex=0.25, interior_m=1.5):
        T = np.array(tris)
        cen = T.mean(axis=1)
        ci = np.floor(cen[:, 0] / _PLAN["cell_m"]).astype(int); cj = np.floor(cen[:, 1] / _PLAN["cell_m"]).astype(int)
        C_, M_ = _PLAN["cell_m"], _PLAN["margin_m"]
        x0, y0 = ci.min() * C_ - M_, cj.min() * C_ - M_
        grid = rw.Grid(x0, y0, int(round(((ci.max() + 1) * C_ + M_ - x0) / tex)),
                       int(round(((cj.max() + 1) * C_ + M_ - y0) / tex)), tex)
        aer = rw.Aerial(img, bbox, origin); aer.dx, aer.dy = _REG["dx_m"], _REG["dy_m"]
        road = rw.rasterize(grid, T)
        tone, _st, lit = rw.tone_field(aer, grid, road, _TONE, return_lit=True)
        ri = max(1, int(round(interior_m / tex)))
        interior = road & (rw.box_mean(road.astype(np.float64), np.ones(road.shape), ri) >= 1.0 - 1e-9)
        return grid, road, lit, interior & lit, tone

    def test_photo_mask_is_the_bakes():
        C, n, tris, img, pim, bbox, origin = _mask_scene()
        grid, road, lit, ub, _tone = _bake_mask(tris, img, bbox, origin)
        assert (road & ~lit).sum() > 500 and (lit & ~ub).sum() > 500       # paint, shadow and the interior all bite
        rgb_at = rwc.aerial_rgb_at(pim.load(), pim.size, bbox, origin, _REG)
        g = rwc.bake_grid([(t_, None) for t_ in tris], _PLAN, 0.25)
        assert g == (grid.x0, grid.y0, grid.nx, grid.ny)
        usable, ms = rwc.photo_mask(tris, g, 0.25, rgb_at, _TONE, rgb_at.px_m, 1.5)
        assert ms["road_cells"] == int(road.sum())
        js, is_ = np.nonzero(road)
        off = sum(1 for j, i in zip(js[::2].tolist(), is_[::2].tolist()) if usable(i, j) != bool(ub[j, i]))
        assert off <= 0.001 * len(js[::2]), off                              # float32 rounding at a threshold only

    def test_gate_measures_the_bakes_samples():
        C, n, tris, img, pim, bbox, origin = _mask_scene()
        grid, road, lit, ub, tone = _bake_mask(tris, img, bbox, origin)
        Cc, _e, _L = rw.resample(C, 2.0, True)
        nCc = rw.left_normals(Cc, True)
        th = np.arctan2(Cc[:, 1] / 45, Cc[:, 0] / 70)
        P = np.column_stack([Cc[:, :2] + (3.0 * np.sin(2 * th))[:, None] * nCc, Cc[:, 2]])

        def tone_at(x, y):                                                  # the bake's (tools/road_wear_blend.py)
            i, j = grid.index(x, y)
            ok = (i >= 0) & (j >= 0) & (i < grid.nx) & (j < grid.ny)
            out = np.full(np.shape(x), np.nan)
            ok2 = ok.copy(); ok2[ok] = ub[j[ok], i[ok]]
            out[ok2] = tone[j[ok2], i[ok2]]
            return out
        dp = rw.photo_rubber(tone_at, P, Cc, nCc, True, rw.PHOTO)
        rgb_at = rwc.aerial_rgb_at(pim.load(), pim.size, bbox, origin, _REG)
        g = rwc.bake_grid([(t_, None) for t_ in tris], _PLAN, 0.25)
        usable, _ms = rwc.photo_mask(tris, g, 0.25, rgb_at, _TONE, rgb_at.px_m, 1.5)

        def value_at(x, y):                                                 # the gate's, on the same tone
            i = int(np.floor((x - g[0]) / 0.25)); j = int(np.floor((y - g[1]) / 0.25))
            return float(tone[j, i]) if usable(i, j) else None
        got = rwc.measure_photo(P.tolist(), Cc[:, :2].tolist(), nCc.tolist(), True, value_at, rw.PHOTO)
        assert got["stations"] == dp["stations"]
        assert abs(got["samples"] - dp["samples"]) <= 0.002 * dp["samples"], (got["samples"], dp["samples"])
        assert abs(got["depth"] - dp["depth"]) < 1e-3, (got["depth"], dp["depth"])

"""Ledger 0095 (Kevin 2026-11-19: "Yes, pilot the owned asphalt with the high-pass"): the road detail's high-pass
(scripts/aerial/road_wear.detail_highpass / highpass_cuts, used by tools/road_wear_blend.py step 5b) and the pilot's
bindings on Milford and High Plains (texture_overrides 1ROAD = the owned asphalt_dense pair, road_wear.detail_highpass_m).

numpy only; the real tile's check needs Pillow and is skipped without it.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from scripts.aerial import road_wear as rw

ROOT = Path(__file__).resolve().parents[2]
PILOT = {"milford-road-course-lm", "high-plains-lm"}
PAIR = ["assets/textures/asphalt_dense_diffuse.jpg", "assets/textures/asphalt_dense_normal.jpg"]


def _wave(n: int, tile_m: float, wl_m: float) -> np.ndarray:
    """a sinusoid along x of wavelength wl_m (a whole number of periods across the tile), 3 channels, about 0.4"""
    x = (np.arange(n) + 0.5) * tile_m / n
    row = 0.4 + 0.1 * np.sin(2 * math.pi * x / wl_m)
    return np.repeat(np.tile(row, (n, 1))[..., None], 3, axis=2)


def _amp(a: np.ndarray) -> float:
    return float(a[..., 0].std() * math.sqrt(2))


def test_the_cut_is_half_power_at_its_wavelength_and_the_mean_is_kept():
    n, tile = 256, 4.0
    for wl, want in ((0.5, 0.5), (4.0, 1 - math.exp(-math.log(2) * (0.5 / 4.0) ** 2)), (0.0625, 1.0)):
        a = _wave(n, tile, wl)
        out = rw.detail_highpass(a, tile, 0.5)
        assert out.dtype == np.float32 and out.shape == a.shape
        assert abs(float(out.mean()) - float(a.mean())) < 1e-6           # the mean (DC) kept: m0 still holds
        assert abs(_amp(out) / _amp(a) - want) < 2e-3, (wl, _amp(out) / _amp(a), want)


def test_the_tile_still_wraps_and_a_flat_tile_is_unchanged():
    n, tile = 128, 4.0
    a = _wave(n, tile, 1.0) + _wave(n, tile, 0.25) - 0.4
    out = rw.detail_highpass(a, tile, 0.5)
    # the filter works on the tile's own period: the seam step equals an interior step's size
    seam = np.abs(out[:, 0] - out[:, -1]).max()
    inner = np.abs(np.diff(out, axis=1)).max()
    assert seam <= inner + 1e-6
    flat = np.full((n, n, 3), 0.37, dtype=np.float32)
    assert np.allclose(rw.detail_highpass(flat, tile, 0.5), flat, atol=1e-6)


def test_cuts_are_opt_in_and_checked():
    base = rw.spec_from_config({"road_wear": {"surfaces": ["1ROAD", "1KERB_SIDEWALK"]}})
    assert "detail_highpass_m" not in rw.DEFAULTS and rw.highpass_cuts(base) == {}
    s = rw.spec_from_config({"road_wear": {"surfaces": ["1ROAD", "1KERB_SIDEWALK"],
                                           "detail_highpass_m": {"1road": 0.5, "_doc": "x"}}})
    assert rw.highpass_cuts(s) == {"1ROAD": 0.5}
    for bad in ({"1RUNOFF": 0.5}, {"1ROAD": 0.0}, {"1ROAD": -1}, {"1ROAD": 2.5}, 0.5):
        s = rw.spec_from_config({"road_wear": {"detail_highpass_m": bad}})
        with pytest.raises(ValueError):
            rw.highpass_cuts(s)


def test_only_the_pilot_tracks_opt_in_and_they_bind_the_owned_pair():
    seen = set()
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        cfg = json.loads(cfgp.read_text(encoding="utf-8"))
        slug = cfgp.parent.name
        ov = (cfg.get("texture_overrides") or {}).get("1ROAD") or {}
        hp = (cfg.get("road_wear") or {}).get("detail_highpass_m")
        if slug not in PILOT:
            assert hp is None, slug                                       # every other track unchanged
            if slug == "san-diego-lake-murray":
                # ledger 0099 (Kevin 2026-11-22, owned asphalt "On every track now"): Lake Murray binds the pair with no
                # road_wear key, so no high-pass; its ship.json brings the pair (tests/tools/test_lake_murray_0099.py)
                assert "road_wear" not in cfg and [ov["diffuse"], ov["normal"]] == PAIR, slug
                ship = json.loads((cfgp.parent / "ship.json").read_text(encoding="utf-8"))
                assert set(PAIR) <= set(ship["sync_in"]["assets"]), slug
                continue
            assert "asphalt_dense" not in json.dumps(ov), slug
            continue
        seen.add(slug)
        assert hp == {"1ROAD": 0.5}, slug
        assert [ov["diffuse"], ov["normal"]] == PAIR, slug
        assert all((ROOT / f).is_file() for f in PAIR)
        assert rw.highpass_cuts(rw.spec_from_config(cfg)) == {"1ROAD": 0.5}
        ship = json.loads((cfgp.parent / "ship.json").read_text(encoding="utf-8"))
        assert set(PAIR) <= set(ship["sync_in"]["assets"]), slug         # the PC's workshop gets the pair
    assert seen == PILOT, seen                                            # sparse checkouts may lack other tracks, not these


def test_the_owned_tile_keeps_its_close_look():
    """measured 2026-11-19 (Mac, Pillow decode, as Blender's Non-Color load): asphalt_dense_diffuse std/mean 27.90 ->
    27.87 % with the 0.5 m cut, the mean unchanged, and its clip over m0 (Milford 0.85588, High Plains 0.76923, their
    last bakes) 0.068 / 0.408 % (the cracked tile's 0.444 / 1.27 % in those bakes)"""
    Image = pytest.importorskip("PIL.Image")
    d = np.asarray(Image.open(ROOT / PAIR[0]).convert("RGB"), dtype=np.float32) / 255.0
    out = rw.detail_highpass(d, 4.0, 0.5)
    assert abs(float(out.mean()) - float(d.mean())) < 1e-5
    sd0, sd1 = float(d.std() / d.mean()), float(out.std() / out.mean())
    assert 0.0 < sd0 - sd1 < 0.001                                        # the band removed is a sliver of the variance
    assert float((out / 0.85588 > 1).mean()) < 0.001 and float((out / 0.76923 > 1).mean()) < 0.005

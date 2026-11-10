"""tools/kerb_offsets.py: a kerb's paint edges read from its alternating blocks alone, colour not used (ledger 0081 round 3)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import kerb_offsets as ko  # noqa: E402


def _window(o_in, o_out, blur_m=0.3, rows=25, period=2.0, contrast=60.0, seed=1):
    """luminance rows along s x columns across the edge: blocks between o_in .. o_out, blurred across like an aerial"""
    offs = np.arange(ko.O_LO_M, ko.O_HI_M + 1e-9, ko.DO_M)
    s = np.arange(rows) * ko.DS_M
    cover = ((offs >= o_in) & (offs <= o_out)).astype(float)
    k = np.exp(-0.5 * (np.arange(-20, 21) * ko.DO_M / blur_m) ** 2)
    cover = np.convolve(cover, k / k.sum(), mode="same")
    blocks = np.where(np.sin(2 * np.pi * s / period) >= 0, 1.0, -1.0) * contrast / 2
    base = np.where(offs < 0, 90.0, 150.0)                 # asphalt inside the edge, pale dirt outside: no alternation
    rng = np.random.default_rng(seed)
    return base[None, :] + cover[None, :] * blocks[:, None] + rng.normal(0, 3, (rows, len(offs))), offs


def test_the_half_maximum_of_the_blurred_blocks_is_the_paint_edge():
    G, offs = _window(-0.8, 0.6)
    r = ko.station(G, offs)
    assert r is not None
    assert abs(r[0] + 0.8) < 0.1 and abs(r[1] - 0.6) < 0.1
    assert r[2] > ko.MIN_AMP


def test_a_plain_edge_with_no_blocks_reads_no_kerb():
    G, offs = _window(-0.8, 0.6, contrast=0.0)
    r = ko.station(G, offs)
    assert r is None or r[2] < ko.MIN_AMP


def test_crossings_interpolate_and_refuse_a_band_off_the_grid():
    offs = np.arange(0.0, 1.01, 0.1)
    k = np.array([0, 0, 0.2, 0.6, 1.0, 1.0, 0.6, 0.2, 0, 0, 0], dtype=float)
    o_in, o_out, lo, hi = ko.crossings(k, offs)
    assert abs(o_in - 0.275) < 1e-9 and abs(o_out - 0.625) < 1e-9
    assert ko.crossings(np.ones(11), offs) is None


def test_every_tuning_number_is_named_for_the_changelog():
    for name in ("DS_M", "DO_M", "WIN_M", "PERIOD_M", "HALF", "MIN_AMP", "EXT_WIN_M", "EXT_FRAC", "GAP_M", "GROW_M"):
        assert hasattr(ko, name)

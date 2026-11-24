"""Ledger 0099 round 3, item 3: scripts/aerial/road_wear.flat_alpha, the weight of a flat tone on a named stretch of road
(opt-in road_wear.tone.flat; Lake Murray's Mission Gorge Rd where it is built off the real road). numpy, as the module."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.aerial import road_wear as rw  # noqa: E402


def test_the_weight_is_one_on_the_carriageway_eased_at_the_two_ends_and_zero_off_it():
    P = np.array([[x, 0.0] for x in np.arange(0.0, 100.1, 4.0)])
    half = np.full(len(P), 5.0)
    X, Y = np.meshgrid(np.array([-3.0, 0.0, 12.5, 25.0, 50.0, 75.0, 87.5, 100.0, 104.0]), np.array([0.0, 4.9, 5.1, -4.9]))
    a = rw.flat_alpha(X, Y, P, half, 25.0)
    assert a.shape == X.shape and a.dtype == np.float32
    on = [0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 0.5, 0.0, 0.0]
    assert np.allclose(a[0], on) and np.allclose(a[1], on) and np.allclose(a[3], on)
    assert not a[2].any()                                                # 5.1 m off a 5 m half width
    assert np.allclose(rw.flat_alpha(X, Y, P, half, 0.0)[0], [1, 1, 1, 1, 1, 1, 1, 1, 1])   # no ease: the stretch whole, round ends
    assert (rw.FLAT_SKIRT_M, rw.FLAT_EASE_M) == (2.0, 25.0)


def test_the_half_width_is_drawn_along_a_segment_and_a_bend_belongs_to_its_nearest_one():
    P = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])
    half = np.array([1.0, 3.0, 3.0])
    a = rw.flat_alpha(np.array([[5.0, 5.0, 10.9, 12.5, 14.0]]), np.array([[1.9, 2.1, 5.0, 5.0, 5.0]]), P, half, 0.0)
    assert a.tolist() == [[1.0, 0.0, 1.0, 1.0, 0.0]]                     # 2 m wide half way along the first segment
    # far points cost nothing and stay zero; a tone field set from it is the lit ratio there and the photo's elsewhere
    X, Y = np.meshgrid(np.linspace(-200.0, 200.0, 81), np.linspace(-200.0, 200.0, 81))
    al = rw.flat_alpha(X, Y, P, half, 0.0)
    assert al.sum() > 0 and not al[(np.abs(X) > 20) | (np.abs(Y) > 20)].any()
    tone = np.full(X.shape, 0.8, dtype=np.float32)
    tone[...] = 1.0 + (tone - 1.0) * (1.0 - al)
    assert np.allclose(tone[al == 1.0], 1.0) and np.allclose(tone[al == 0.0], 0.8)

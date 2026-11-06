"""tools/naip_carriageways.py (ledger 0080 2b round 2): where there is no image there is no reading. A carriageway pair
whose median NAIP never imaged (a crop not cached under NAIP_OFFLINE, an item's nodata) reads "unread", never the
paved-median fallback's "barrier at the midline" (2b round 1: 2,343 of I 5 NB's stations read so off no image)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import naip_carriageways as C  # noqa: E402

PAVE = (100.0, 100.0, 100.0, 100.0)     # NDVI 0, unsaturated, mean 100: pavement under the reader's own classes


class _Fake:
    """A mosaic whose pixel at (x, z) is ``fn(x, z)`` (R, G, B, NIR) or NaN (no image)."""

    def __init__(self, fn):
        self.fn = fn

    def sample(self, xs, zs):
        return np.asarray([self.fn(x, z) for x, z in zip(xs, zs)], np.float32).reshape(-1, 4)


def _pair(gap=20.0, length=60.0, width=12.0):
    """Two carriageways running east (+x), the partner ``gap`` m to the left (north, +z)."""
    xs = np.arange(0.0, length + 1e-6, 2.0)
    a = [[float(x), 0.0, 0.0] for x in xs]
    b = [[float(x), 0.0, gap] for x in xs]
    w = [width] * len(xs)
    return {"a": (a, w, "b"), "b": (b, w, "a")}


def _left_kinds(mosaic):
    rows, _lines = C.read_sections(mosaic, _pair())
    return {r[4][0] for r in rows["a"]}


def test_no_image_between_the_pair_is_unread_not_a_midline_barrier():
    assert _left_kinds(_Fake(lambda x, z: (np.nan,) * 4)) == {"unread"}


def test_a_hole_in_the_image_inside_the_median_is_unread():
    def fn(x, z):
        return (np.nan,) * 4 if 9.0 <= z <= 11.0 else PAVE
    assert _left_kinds(_Fake(fn)) == {"unread"}


def test_an_imaged_paved_median_still_puts_its_barrier_at_the_midline():
    rows, _lines = C.read_sections(_Fake(lambda x, z: PAVE), _pair())
    kinds = {r[4][0] for r in rows["a"]}
    assert kinds == {"barrier at the midline"}
    assert {r[4][2] for r in rows["a"]} == {10.0}             # midway between the two lines, 20 m apart


def test_an_imaged_paved_median_with_a_bright_top_reads_the_barrier_seen():
    def fn(x, z):
        return (200.0, 200.0, 200.0, 200.0) if 10.4 <= z <= 11.0 else PAVE
    rows, _lines = C.read_sections(_Fake(fn), _pair())
    assert {r[4][0] for r in rows["a"]} == {"barrier seen"}
    assert all(10.4 <= r[4][2] <= 11.0 for r in rows["a"])   # the top read, not the midline

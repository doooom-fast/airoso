"""scripts/elevation/heightfield.profile_along — the profile on a line that is not the gps stage's uniform 3 m.

snap_to_ground converts its metre windows and its grade cap into points through ``spacing_m``, and build()
always passed CENTERLINE_SPACING_M (3.0). On the Lariat's paint centreline (1 m over the climb and Paradise
Rd, 3 m elsewhere) that made the 16 % cap 48 % per metre and the 33 m median 11 m wide (ledger 0048
"Started", 2026-11-01). profile_along runs the same smoother on a ~1 m station grid when a line carries
short segments, and leaves every uniform 3 m line byte-identical. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import math
import random

from scripts.elevation.heightfield import profile_along, snap_to_ground


def _rolling(n, amp=6.0, seed=1):
    rnd = random.Random(seed)
    base = [1800.0 + amp * math.sin(i / 60.0) + 2.0 * math.sin(i / 7.0) + rnd.uniform(-0.15, 0.15) for i in range(n)]
    base[-1] = base[0]
    return base


def test_uniform_3m_line_is_byte_identical_to_the_old_call():
    z = _rolling(600)
    seg = [3.0] * (len(z) - 1)
    out, info = profile_along(z, seg, grade_cap_pct=9.0, closed=True)
    assert info["by_station"] is False and info["short_segments"] == 0
    assert out == snap_to_ground(z, spacing_m=3.0, grade_cap_pct=9.0, closed=True)
    # the gps stage's real spacing jitter (2.1-4.4 m at corners and seams) stays on the old path too
    seg2 = [3.0 if i % 40 else 2.3 for i in range(len(z) - 1)]
    out2, info2 = profile_along(z, seg2, grade_cap_pct=9.0, closed=True)
    assert info2["by_station"] is False
    assert out2 == snap_to_ground(z, spacing_m=3.0, grade_cap_pct=9.0, closed=True)


def _mixed_line(cap_pct):
    """3 m points for 300 m, then 1 m points for 600 m carrying four one-metre cliffs of 1.0 m (a DEM wall at a
    cut edge: a 100 % grade over one metre that a 16 % cap must turn into a ramp), then 3 m points back to the
    start (closed). A step survives any median; only the mean's width and the cap's per-metre value decide what
    reaches the road."""
    pts, seg = [], []
    z0 = 1800.0
    for i in range(100):
        pts.append(z0 + 0.5 * math.sin(i / 10.0)); seg.append(3.0)
    lift = 0.0
    for i in range(600):
        if i in (120, 260, 400, 540):
            lift += 1.0
        pts.append(z0 + 0.5 * math.sin((300 + i) / 30.0) + lift); seg.append(1.0)
    for i in range(100):
        pts.append(z0 + 0.5 * math.sin((900 + 3 * i) / 30.0) + lift * (1 - i / 100.0)); seg.append(3.0)
    pts.append(pts[0])
    return pts, seg


def test_mixed_line_runs_by_station_and_caps_per_metre():
    z, seg = _mixed_line(16.0)
    out, info = profile_along(z, seg, grade_cap_pct=16.0, closed=True)
    assert info["by_station"] is True and info["short_segments"] == 600
    assert abs(info["spacing_m"] - 1.0) < 0.01 and info["grid_points"] == round(sum(seg)) + 1
    assert len(out) == len(z) and out[0] == out[-1]
    worst = max(abs(out[i + 1] - out[i]) / seg[i] * 100 for i in range(len(seg)))
    assert worst <= 16.0 + 0.5, f"a {worst:.1f} % per-metre step survived the 16 % cap"
    # read as 3 m points, the same cliffs reach the road at over 25 % per metre (a 9 m mean that is 3 points
    # wide, a cap of 0.48 m per point)
    old = snap_to_ground(z, spacing_m=3.0, grade_cap_pct=16.0, closed=True)
    worst_old = max(abs(old[i + 1] - old[i]) / seg[i] * 100 for i in range(len(seg)))
    assert worst_old > 25.0, worst_old
    # and the line stays on the ground: the mean rounds the top of a cliff, the cap only cuts (snap_to_ground)
    assert max(a - b for a, b in zip(out, z)) < 0.6


def test_closed_ring_without_the_repeated_vertex_keeps_its_last_vertex():
    # a 1 m ring of 900 vertices, heights a gentle wave, NOT closed by a duplicate vertex: the last vertex is its own
    # point 1 m before vertex 0 (close_seg_m = 1.0), never overwritten with vertex 0's height
    n = 900
    z = [1800.0 + 3.0 * math.sin(2 * math.pi * i / n) for i in range(n)]
    seg = [1.0] * (n - 1)
    out, info = profile_along(z, seg, grade_cap_pct=16.0, closed=True, close_seg_m=1.0)
    assert info["by_station"] is True and info["grid_points"] == n + 1 and len(out) == n
    assert abs(out[-1] - z[-1]) < 0.05 and abs(out[0] - z[0]) < 0.05
    assert abs(z[-1] - z[0]) > 0.015 and abs(out[-1] - out[0]) > 0.01, "the last vertex is not vertex 0"
    # the same ring WITH the repeated vertex: the duplicate is folded out and restored equal (L13)
    z2 = z + [z[0]]
    out2, info2 = profile_along(z2, seg + [1.0], grade_cap_pct=16.0, closed=True)
    assert len(out2) == n + 1 and out2[-1] == out2[0] and info2["grid_points"] == n + 1


def test_open_mixed_line_keeps_its_ends():
    z, seg = _mixed_line(16.0)
    z = z[:-1]; seg = seg[:-1]
    z = [v + 0.1 * i for i, v in enumerate(z)]          # a climbing stage, ends at different heights
    out, info = profile_along(z, seg, grade_cap_pct=18.0, closed=False)
    assert info["by_station"] is True and len(out) == len(z)
    assert abs(out[0] - z[0]) < 2.0 and abs(out[-1] - z[-1]) < 2.0

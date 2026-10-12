"""L13 for the bridge-span detectors (Lariat V3, ledger 0048, V3-PLAN P2 step 5): a span may not end on the closing
vertex of a closed lap unless it continues from vertex 0.

- scripts/geometry/build_mesh.py ``_bridge_detector`` (the height detector that minted the July Lariat's 525 m
  [24,278-24,803] span): with ``seam_rule`` (opt-in, ``bridges.l13_seam_rule``) a run reaching the closing vertex
  while vertex 0 is low is dropped, one that continues from vertex 0 is kept; WITHOUT it the output is exactly what
  it was (every other track);
- scripts/ac/build_kn5_loop.py ``detect_bridge_spans`` (the prep's OSM-way detector, which no shipping track preps
  with yet): spans and pads wrap at the seam and stay inside [0, lap]; open roads are unchanged.
"""
from __future__ import annotations

from scripts.ac.build_kn5_loop import _mpd, detect_bridge_spans
from scripts.geometry.build_mesh import _bridge_detector, seam_rule_spans


def _ring(n=200, step=5.0):
    """a closed square lap, n unique vertices + the closing duplicate"""
    side = n // 4
    pts = []
    for k in range(4):
        for i in range(side):
            t = i * step
            L = side * step
            x, z = [(t, 0.0), (L, t), (L - t, L), (0.0, L - t)][k]
            pts.append((x, 0.0, z))
    pts.append(pts[0])
    return pts


def _ground_with_high_run(pts, lo, hi, lift=6.0):
    """raw ground stations + heights: the road (y = 0) rides `lift` above the ground on vertices [lo, hi)"""
    import math
    st = [0.0]
    for i in range(1, len(pts)):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    gy = [(-lift if lo <= i < hi else 0.0) for i in range(len(pts))]
    return st, gy


def test_without_the_opt_in_the_seam_span_is_kept_as_before():
    pts = _ring()
    n = len(pts)
    st, gy = _ground_with_high_run(pts, n - 30, n)          # the run reaches the closing vertex; v0 is low
    gy[0] = 0.0
    _bridge_detector(pts, [[(0, 0, 0)]], raw_ground=(st, gy))
    assert _bridge_detector.last_spans == [(st[n - 30], st[n - 1])]


def test_the_seam_rule_drops_a_run_that_ends_on_the_closing_vertex_alone():
    pts = _ring()
    n = len(pts)
    st, gy = _ground_with_high_run(pts, n - 30, n)
    gy[0] = 0.0
    bridge_of = _bridge_detector(pts, [[(0, 0, 0)]], raw_ground=(st, gy), seam_rule=True)
    assert _bridge_detector.last_spans == []
    assert bridge_of(st[n - 10]) is False


def test_the_seam_rule_keeps_a_span_that_continues_from_vertex_0():
    pts = _ring()
    n = len(pts)
    st, gy = _ground_with_high_run(pts, n - 30, n)
    for i in range(0, 20):
        gy[i] = -6.0                                        # high on both sides of the seam: one real span
    _bridge_detector(pts, [[(0, 0, 0)]], raw_ground=(st, gy), seam_rule=True)
    spans = _bridge_detector.last_spans
    assert (st[n - 30], st[n - 1]) in spans and spans[0][0] == 0.0
    kept, dropped = seam_rule_spans(spans, st, [True] * n, closed=True)
    assert dropped == [] and kept == spans


def test_the_seam_rule_leaves_open_roads_and_mid_lap_spans_alone():
    st = [5.0 * i for i in range(50)]
    spans = [(100.0, 150.0), (200.0, st[-1])]
    assert seam_rule_spans(spans, st, [False] * 50, closed=False) == (spans, [])
    assert seam_rule_spans([(100.0, 150.0)], st, [False] * 50, closed=True) == ([(100.0, 150.0)], [])


def _bridge_way(origin, x0, z0, x1, z1):
    m_lon, m_lat = _mpd(origin[1])
    return {"hw": "primary", "geom": [[origin[0] + x0 / m_lon, origin[1] + z0 / m_lat],
                                       [origin[0] + x1 / m_lon, origin[1] + z1 / m_lat]]}


def test_the_prep_detector_wraps_spans_and_pads_at_the_seam():
    import math
    pts = _ring()
    lap = sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]) for i in range(1, len(pts)))
    origin = (-105.2, 39.7)
    # a bridge way along the lap's first and last 20 m (it straddles vertex 0)
    way = _bridge_way(origin, -20.0, 0.0, 20.0, 0.0)
    way2 = _bridge_way(origin, 0.0, 20.0, 0.0, -1.0)
    spans = detect_bridge_spans(pts, origin, [way, way2], match_m=1.0, pad_m=8.0, seam_rule=True)
    assert all(0.0 <= a <= b <= lap + 1e-9 for a, b in spans), spans
    ends_at_close = [s for s in spans if abs(s[1] - lap) < 1e-6]
    starts_at_0 = [s for s in spans if s[0] == 0.0]
    assert ends_at_close and starts_at_0, spans               # the seam span continues from vertex 0 (L13)
    assert abs(starts_at_0[0][1] - (20.0 + 8.0)) < 5.0 + 1e-6
    assert abs(ends_at_close[0][0] - (lap - 20.0 - 8.0)) < 5.0 + 1e-6


def test_the_prep_detector_seam_wrap_is_opt_in():
    # without bridges.l13_seam_rule a closed lap's spans are exactly the pre-2026-10-12 ones: the seam span is NOT
    # continued from vertex 0 and the last pad may run past the lap (every other track byte-identical)
    import math
    pts = _ring()
    lap = sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]) for i in range(1, len(pts)))
    origin = (-105.2, 39.7)
    way = _bridge_way(origin, -20.0, 0.0, 20.0, 0.0)
    way2 = _bridge_way(origin, 0.0, 20.0, 0.0, -1.0)
    old = detect_bridge_spans(pts, origin, [way, way2], match_m=1.0, pad_m=8.0)
    new = detect_bridge_spans(pts, origin, [way, way2], match_m=1.0, pad_m=8.0, seam_rule=True)
    assert old != new, (old, new)
    assert old[0][0] == 0.0 and old[-1][1] > lap, old            # the legacy shape: pad past the lap, no wrap


def test_the_prep_detector_is_unchanged_on_an_open_road():
    pts = [(5.0 * i, 0.0, 0.0) for i in range(60)]
    origin = (-105.2, 39.7)
    way = _bridge_way(origin, 100.0, 0.0, 150.0, 0.0)
    assert detect_bridge_spans(pts, origin, [way], match_m=1.0, pad_m=8.0) == [(92.0, 158.0)]
    tail = _bridge_way(origin, 260.0, 0.0, 300.0, 0.0)          # reaching the open end: the pad runs past it
    assert detect_bridge_spans(pts, origin, [tail], match_m=1.0, pad_m=8.0) == [(252.0, 295.0 + 8.0)]

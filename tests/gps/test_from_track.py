"""Build a centerline from a recorded GPS drive — scripts/gps/from_track.

Synthesises a small square loop of GPS fixes (the dashcam/redtiger_gps JSON format), runs the
drive->centerline builder into a temp project, and asserts a pipeline-shaped centerline.geojson comes
out (closed, resampled, width-tagged). Plain tempfile + asserts for tests/run_tests.py.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.gps import from_track as ft


def _square_track(path: Path, n_per_side: int = 40, size: float = 0.004, lat0: float = 39.78, lon0: float = -104.94):
    """~square loop (approx 1.3 km/side at this latitude) sampled densely, with timestamps."""
    corners = [(lat0, lon0), (lat0 + size, lon0), (lat0 + size, lon0 + size), (lat0, lon0 + size)]
    fixes, sec = [], 0
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        for k in range(n_per_side):
            t = k / n_per_side
            fixes.append({"t": f"2026-04-06T18:{40 + sec // 60:02d}:{sec % 60:02d}",
                          "lat": a[0] + (b[0] - a[0]) * t, "lon": a[1] + (b[1] - a[1]) * t})
            sec += 1
    path.write_text(json.dumps(fixes))


def test_builds_closed_centerline_from_drive():
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        trk = proj / "track.json"
        _square_track(trk)
        out, stats = ft.build_from_track(proj, [str(trk)], loop=True, width_m=8.0)
        assert out.exists()
        gj = json.loads(out.read_text())
        feats = gj["features"]
        cl = next(f for f in feats if f["properties"].get("kind") == "full")
        assert cl["properties"]["closed"] is True
        coords = cl["geometry"]["coordinates"]
        assert len(coords) > 100                                  # resampled to ~3 m over a ~5 km loop
        assert coords[0][0] < 0 and coords[0][1] > 0              # [lon,lat] order: lon negative (W), lat positive (N)
        assert all(w == 8.0 for w in cl["properties"]["widths_m"])
        assert 1.2 < stats["length_km"] < 2.0                     # ~444 m + ~341 m sides, square perimeter
        assert (proj / "data" / "centerline_preview.svg").exists()


def test_measured_widths_ride_on_their_stations():
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        trk = proj / "track.json"
        _square_track(trk)
        fixes = json.loads(trk.read_text())
        for i, f in enumerate(fixes):
            f["w"] = 16.0 if i < 40 else 10.0                    # first side measured wide (a front straight)
        trk.write_text(json.dumps(fixes))
        out, _ = ft.build_from_track(proj, [str(trk)], loop=True, width_m=8.0)
        cl = json.loads(out.read_text())["features"][0]["properties"]
        w = cl["widths_m"]
        assert set(w) == {16.0, 10.0}                             # --width ignored once every fix is measured
        assert w[5] == 16.0 and w[len(w) // 2] == 10.0
        assert 0.2 < w.count(16.0) / len(w) < 0.3                 # one side of four
        assert cl["default_width_m"] == 10.0                      # the median measured width


def test_resample_spacing_is_even():
    import math
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        trk = proj / "t.json"
        _square_track(trk)
        out, _ = ft.build_from_track(proj, [str(trk)], loop=True)
        coords = json.loads(out.read_text())["features"][0]["geometry"]["coordinates"]
        # consecutive spacings should hover around the 3 m resample target (allow corners/closing slack)
        ds = []
        for i in range(1, min(len(coords), 200)):
            (lo1, la1), (lo2, la2) = coords[i - 1], coords[i]
            ds.append(math.hypot((lo2 - lo1) * 85000, (la2 - la1) * 111000))
        ds = [x for x in ds if x > 0]
        assert 2.0 < (sum(ds) / len(ds)) < 4.5


def test_the_smoother_wraps_on_a_loop_and_zero_is_none():
    """ledger 0060 (High Plains, 2026-10-29): the 5-fix average meant for 1 Hz GPS jitter cut an OSM node list's corners by
    26.8 m and, un-wrapped, parted a closed ring's ends by 466 m. On a loop the window wraps (the ends stay together, a
    repeated closing vertex is kept, not averaged twice); window 0 returns the fixes untouched."""
    sq = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0), (0.0, 2.0), (0.0, 1.0), (0.0, 0.0)]
    assert ft._smooth(sq, 0) == sq and ft._smooth(sq, 1, loop=True) == sq
    open_ends = ft._smooth(sq, 5)                       # the old behaviour: the two ends drift apart
    assert open_ends[0] != open_ends[-1]
    wrapped = ft._smooth(sq, 5, loop=True)
    assert wrapped[0] == wrapped[-1] and len(wrapped) == len(sq), "a closed ring stays closed"
    # every wrapped point averages its two neighbours on each side around the ring: the corner (2, 0) pulls in
    # to the mean of (0,0) (1,0) (2,0) (2,1) (2,2)
    assert abs(wrapped[2][0] - 1.4) < 1e-9 and abs(wrapped[2][1] - 0.6) < 1e-9
    # the end vertex is averaged with its ring neighbours, exactly as any interior vertex is:
    # (0,2) (0,1) (0,0) (1,0) (2,0)
    assert abs(wrapped[0][0] - 0.6) < 1e-9 and abs(wrapped[0][1] - 0.6) < 1e-9


def test_smooth_window_zero_puts_the_line_on_the_fixes():
    """a node list (smooth_window 0) resamples the source polygon itself: every output point lies ON one of its
    segments (the resample lands between vertices, so the test is point-to-segment); window 5 leaves the polygon"""
    def to_segment(p, a, b):
        ax, ay = a; bx, by = b; px, py = p
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        s = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
        return ((px - (ax + s * dx)) ** 2 + (py - (ay + s * dy)) ** 2) ** 0.5

    with tempfile.TemporaryDirectory() as td:
        d = Path(td); (d / "data").mkdir()
        fixes = d / "fixes.json"; _square_track(fixes, n_per_side=3)
        src = [(f["lon"], f["lat"]) for f in json.loads(fixes.read_text())]
        segs = list(zip(src, src[1:] + src[:1]))
        out, stats = ft.build_from_track(d, [str(fixes)], loop=True, width_m=9.0, smooth_window=0)
        ring = json.loads(out.read_text())["features"][0]["geometry"]["coordinates"]
        off = max(min(to_segment(p, a, b) for a, b in segs) for p in ring)
        assert off < 1e-9, off                                   # on the polygon, in degrees
        assert stats["closed"]                                   # (the fixture's last fix is a step short of its first: a real gap, closed by loop=True)
        out5, _stats5 = ft.build_from_track(d, [str(fixes)], loop=True, width_m=9.0, smooth_window=5)
        ring5 = json.loads(out5.read_text())["features"][0]["geometry"]["coordinates"]
        off5 = max(min(to_segment(p, a, b) for a, b in segs) for p in ring5)
        assert off5 > 1e-5, off5                                 # the average cuts the corners (> ~1 m here)

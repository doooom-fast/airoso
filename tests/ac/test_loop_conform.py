"""Regression tests for the loop terrain-conform front-end (build_kn5_loop): declared bridge spans.

The bpy passes (corridor subdivision, contact pin, prop re-seat) run only inside Blender; the
pure-python span detection + declaration they depend on is tested here — it is what keeps the I-8
trench a trench (pin may only push DOWN on a span) and what hands the kn5 ground gate its standard
declared-span exemption for the loop's real bridges."""

import contextlib
import io
import json
import math
import tempfile
from pathlib import Path

from scripts.ac.build_kn5_loop import _mpd, declare_bridge_spans, detect_bridge_spans

LON0, LAT0 = -117.04, 32.78


def _ll(x, z):
    m_lon, m_lat = _mpd(LAT0)
    return (LON0 + x / m_lon, LAT0 + z / m_lat)


def _straight_centerline(n=200, step=4.0):
    return [(0.0, 10.0, i * step) for i in range(n)]


def test_detect_bridge_spans_finds_crossing():
    pts = _straight_centerline()
    ways = [{"hw": "secondary", "geom": [_ll(-30.0, 100.0), _ll(30.0, 100.0)]}]
    spans = detect_bridge_spans(pts, (LON0, LAT0), ways)
    assert len(spans) == 1
    a, b = spans[0]
    assert a < 100.0 < b, f"span {spans[0]} must cover station 100"
    assert b - a < 80.0, "span must stay local to the crossing"


def test_detect_bridge_spans_ignores_freeway_bridges():
    """A motorway bridge crossing OVER the loop must not mark a phantom span on the road below."""
    pts = _straight_centerline()
    ways = [{"hw": "motorway", "geom": [_ll(-30.0, 300.0), _ll(30.0, 300.0)]},
            {"hw": "motorway_link", "geom": [_ll(-30.0, 500.0), _ll(30.0, 500.0)]}]
    assert detect_bridge_spans(pts, (LON0, LAT0), ways) == []


def test_detect_bridge_spans_mirror_x():
    pts = [(-x, y, z) for x, y, z in _straight_centerline()]   # mirrored frame (x flipped)
    ways = [{"hw": "primary", "geom": [_ll(-30.0, 100.0), _ll(30.0, 100.0)]}]
    spans = detect_bridge_spans(pts, (LON0, LAT0), ways, mirror_x=True)
    assert len(spans) == 1 and spans[0][0] < 100.0 < spans[0][1]


def test_declare_bridge_spans_writes_gate_files():
    """declare_bridge_spans must emit the two files kn5_ground_check's declared-span exemption
    reads — bridge.spans.auto.json (station ranges) and finished_centerline.json in the KN5 frame
    (z negated: the Blender-first path ships (x, y, -z) of the local frame)."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "data").mkdir()
        pts = _straight_centerline()
        (proj / "data" / "centerline.local.json").write_text(json.dumps({
            "origin": {"lon": LON0, "lat": LAT0},
            "points_xyz_m": [list(p) for p in pts],
            "widths_m": [9.0] * len(pts)}))
        (proj / "data" / "bridges.cache.json").write_text(json.dumps(
            [{"hw": "secondary", "geom": [list(_ll(-30.0, 100.0)), list(_ll(30.0, 100.0))]}]))
        (proj / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
        spans = declare_bridge_spans(proj)
        assert len(spans) == 1
        auto = json.loads((proj / "data" / "bridge.spans.auto.json").read_text())
        assert len(auto) == 1 and auto[0][0] < 100.0 < auto[0][1]
        fc = json.loads((proj / "data" / "finished_centerline.json").read_text())
        assert len(fc["points_xyz_m"]) == len(pts)
        assert fc["widths_m"][0] == 9.0
        # KN5 frame: z negated vs the local frame
        assert math.isclose(fc["points_xyz_m"][50][2], -pts[50][2], abs_tol=1e-6)


def test_declare_bridge_spans_no_bridges_is_clean():
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "data").mkdir()
        pts = _straight_centerline(n=20)
        (proj / "data" / "centerline.local.json").write_text(json.dumps({
            "origin": {"lon": LON0, "lat": LAT0},
            "points_xyz_m": [list(p) for p in pts],
            "widths_m": [7.0] * len(pts)}))
        (proj / "track.config.json").write_text(json.dumps({"slug": "t"}))
        assert declare_bridge_spans(proj) == []
        assert json.loads((proj / "data" / "bridge.spans.auto.json").read_text()) == []
        fc = json.loads((proj / "data" / "finished_centerline.json").read_text())
        assert fc["frame"].startswith("kn5") and "centerline.local.json" in fc["source"], "the raw line, marked as such"


# --- the gate line is the ENGINE's swept line when there is one (ledger 0060, Sand Creek's bridges) ------------------

def _engine_draft(proj: Path, raw_pts, *, spans=((96.0, 204.0),)):
    """What build_mesh leaves in data/ beside the raw centerline: its swept line (frame "mesh …", the declared deck
    LEVELLED 4 m above the raw profile through the span, a corner rounded 1.5 m east), its auto spans, and the
    underlay's report (the engine-draft marker)."""
    (proj / "data" / "centerline.local.json").write_text(json.dumps({
        "origin": {"lon": LON0, "lat": LAT0},
        "points_xyz_m": [list(p) for p in raw_pts],
        "widths_m": [9.0] * len(raw_pts)}))
    swept = []
    for x, y, z in raw_pts:
        yy = y + 4.0 if 100.0 <= z <= 200.0 else y          # the levelled deck over the creek
        xx = x + 1.5 if 400.0 <= z <= 440.0 else x           # a rounded corner
        swept.append([round(xx, 2), round(yy, 2), round(z, 2)])
    (proj / "data" / "finished_centerline.json").write_text(json.dumps({
        "frame": "mesh (mirrored) local metres — same frame as track.obj",
        "points_xyz_m": swept, "widths_m": [9.5] * len(swept)}))
    (proj / "data" / "bridge.spans.auto.json").write_text(json.dumps([[a, b] for a, b in spans]))
    (proj / "data" / "underlay.report.json").write_text("{}")
    (proj / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    return swept


def test_declare_bridge_spans_keeps_the_engines_swept_line_and_spans():
    """An engine draft's finished_centerline is the line the road was swept along (build_mesh: corner-rounded,
    smoothed, bridge decks levelled). The prep used to overwrite it with the raw centerline.local.json line: drive_test
    then walked a line that dived into the creek under every levelled deck and lost the deck out of its 2.5 m window
    (Sand Creek 2026-10-29: 127 severe steps of up to 1.75 m, all on the three spans). Now: the engine's line goes to
    the KN5 frame (z negated), its widths and its auto spans are kept, and the OSM-way scan does not run."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "data").mkdir()
        raw = _straight_centerline()
        swept = _engine_draft(proj, raw)
        # an OSM crossing at station 300 that the builder did NOT leave open: must not become an exemption
        (proj / "data" / "bridges.cache.json").write_text(json.dumps(
            [{"hw": "secondary", "geom": [list(_ll(-30.0, 300.0)), list(_ll(30.0, 300.0))]}]))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            spans = declare_bridge_spans(proj)
        assert spans == [(96.0, 204.0)], spans
        assert json.loads((proj / "data" / "bridge.spans.auto.json").read_text()) == [[96.0, 204.0]]
        fc = json.loads((proj / "data" / "finished_centerline.json").read_text())
        assert fc["frame"].startswith("kn5") and "build_mesh" in fc["source"]
        assert len(fc["points_xyz_m"]) == len(raw) and fc["widths_m"][0] == 9.5
        i_deck = next(i for i, p in enumerate(raw) if p[2] == 148.0)
        i_corner = next(i for i, p in enumerate(raw) if p[2] == 420.0)
        assert math.isclose(fc["points_xyz_m"][i_deck][1], raw[i_deck][1] + 4.0), "the levelled deck, not the raw dip"
        assert math.isclose(fc["points_xyz_m"][i_deck][2], -swept[i_deck][2]), "KN5 frame: z negated"
        assert math.isclose(fc["points_xyz_m"][i_corner][0], raw[i_corner][0] + 1.5), "the rounded corner, not the raw one"
        assert "the engine's swept line" in out.getvalue()


def test_declare_bridge_spans_keeps_its_own_line_on_a_rerun_from_the_prep():
    """`--from prep` re-runs the prep on the workshop's last output, where finished_centerline is already this prep's
    KN5-frame copy of the engine's line: it stays (the raw line must not creep back in on a re-run)."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "data").mkdir()
        raw = _straight_centerline()
        _engine_draft(proj, raw)
        declare_bridge_spans(proj)
        first = (proj / "data" / "finished_centerline.json").read_text()
        spans = declare_bridge_spans(proj)
        assert spans == [(96.0, 204.0)]
        assert (proj / "data" / "finished_centerline.json").read_text() == first


def test_declare_bridge_spans_says_when_the_engines_line_is_gone():
    """A finished_centerline with no frame beside an engine draft is an earlier (pre-fix) prep's raw copy — the
    engine's line is lost until the draft is rebuilt. The prep says so and walks the raw line, as before."""
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "data").mkdir()
        raw = _straight_centerline()
        _engine_draft(proj, raw)
        (proj / "data" / "finished_centerline.json").write_text(json.dumps({
            "points_xyz_m": [[x, y, -z] for x, y, z in raw], "widths_m": [9.0] * len(raw)}))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            spans = declare_bridge_spans(proj)
        assert spans == []
        out = buf.getvalue()
        assert "WARNING" in out and "engine's swept line is gone" in out
        fc = json.loads((proj / "data" / "finished_centerline.json").read_text())
        assert "centerline.local.json" in fc["source"]
        assert math.isclose(fc["points_xyz_m"][30][1], raw[30][1]), "the raw profile (nothing better exists)"

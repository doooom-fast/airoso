"""tools/route_oneway_check.py — does a layout's lap drive against the arrows of a one-way OSM way?

The Lariat's July route drove ~105 m the wrong way at the 19th St ramp terminal and 84 m at I-70 exit 259
(ledger 0048, dossier 2d) and no gate could see it. These pin the matcher (a segment matches the way it
runs ALONG, so a divided road's other carriageway never steals it, and a junction corner is a gap, not a
run), the one-way semantics (yes / -1 / roundabout / reversible / two-way), the per-layout verdict (Full
declares nothing, Reverse declares its stretches, stale or unknown declarations fail, race layouts are
skipped), the seam merge on a closed lap, and the real Lariat: V3 passes, the July line fails on exactly
its two defects. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import route_oneway_check as roc  # noqa: E402

LAT0, LON0 = 39.70, -105.20
MLON, MLAT = roc.meters_per_degree(LAT0)
LARIAT = ROOT / "tracks" / "lookout-lariat"


def ll(x, y):
    """local metres (x = east, y = north) -> (lon, lat)"""
    return (LON0 + x / MLON, LAT0 + y / MLAT)


def way(wid, pts_xy, **tags):
    return {"type": "way", "id": wid, "tags": tags,
            "geometry": [{"lon": ll(x, y)[0], "lat": ll(x, y)[1]} for x, y in pts_xy]}


def densify(pts_xy, step=3.0):
    out = [pts_xy[0]]
    for (ax, ay), (bx, by) in zip(pts_xy, pts_xy[1:]):
        n = max(1, int(math.ceil(math.dist((ax, ay), (bx, by)) / step)))
        out += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(1, n + 1)]
    return out


def project(tmp, line_xy, elements, config):
    p = Path(tmp)
    (p / "data").mkdir(parents=True, exist_ok=True)
    coords = [list(ll(x, y)) for x, y in line_xy]
    (p / "data" / "centerline.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"kind": "full"},
         "geometry": {"type": "LineString", "coordinates": coords}}]}), encoding="utf-8")
    (p / "data" / "osm.cache.json").write_text(json.dumps({"query_fingerprint": "test", "fetched_utc": "x",
                                                           "payload": {"elements": elements}}), encoding="utf-8")
    (p / "track.config.json").write_text(json.dumps(config), encoding="utf-8")
    return p


FWD = {"id": "street_full", "kind": "street", "direction": "forward"}
REV = {"id": "street_reverse", "kind": "street", "direction": "reverse"}


def layout(report, lid):
    return next(lo for lo in report["layouts"] if lo["id"] == lid)


def test_with_the_arrows_passes():
    with tempfile.TemporaryDirectory() as t:
        p = project(t, densify([(0, 0), (200, 0)]), [way(1, [(0, 0), (200, 0)], highway="primary", oneway="yes")],
                    {"layouts": [FWD]})
        rep = roc.run_check(p)
        lo = layout(rep, "street_full")
        assert rep["verdict"] == "PASS" and lo["against_total_m"] == 0
        assert len(lo["with_arrows_runs"]) == 1 and abs(lo["with_arrows_runs"][0]["length_m"] - 200) < 0.5
        assert rep["unmatched_m"] == 0


def test_against_the_arrows_fails_and_names_the_run():
    with tempfile.TemporaryDirectory() as t:
        p = project(t, densify([(200, 0), (0, 0)]), [way(7, [(0, 0), (200, 0)], highway="primary", oneway="yes")],
                    {"layouts": [FWD]})
        rep = roc.run_check(p)
        lo = layout(rep, "street_full")
        assert rep["verdict"] == "FAIL" and lo["verdict"] == "FAIL"
        (run,) = lo["against_runs"]
        assert run["way"] == 7 and abs(run["length_m"] - 200) < 0.5
        assert run["st_from_m"] == 0.0 and abs(run["st_to_m"] - 200) < 0.5
        assert any("AGAINST oneway way 7" in f for f in rep["fails"])


def test_oneway_minus_one_is_against_node_order():
    with tempfile.TemporaryDirectory() as t:
        els = [way(3, [(0, 0), (150, 0)], highway="secondary", oneway="-1")]
        rep = roc.run_check(project(t, densify([(0, 0), (150, 0)]), els, {"layouts": [FWD]}))
        assert layout(rep, "street_full")["against_runs"][0]["way"] == 3
        rep2 = roc.run_check(project(t, densify([(150, 0), (0, 0)]), els, {"layouts": [FWD]}))
        assert rep2["verdict"] == "PASS"


def test_two_way_reversible_and_roundabout_semantics():
    assert roc.oneway_sense({"oneway": "yes"}) == 1
    assert roc.oneway_sense({"oneway": "true"}) == 1
    assert roc.oneway_sense({"oneway": "-1"}) == -1
    assert roc.oneway_sense({"oneway": "no"}) == 0
    assert roc.oneway_sense({}) == 0
    assert roc.oneway_sense({"junction": "roundabout"}) == 1
    assert roc.oneway_sense({"junction": "roundabout", "oneway": "no"}) == 0
    assert roc.oneway_sense({"oneway": "reversible"}) is None
    with tempfile.TemporaryDirectory() as t:
        els = [way(4, [(0, 0), (100, 0)], highway="residential"),
               way(5, [(100, 0), (200, 0)], highway="primary", oneway="reversible")]
        rep = roc.run_check(project(t, densify([(200, 0), (0, 0)]), els, {"layouts": [FWD]}))
        lo = layout(rep, "street_full")
        assert rep["verdict"] == "PASS" and lo["against_total_m"] == 0
        assert [r["way"] for r in lo["unjudged_runs"]] == [5]


def test_divided_pair_matches_its_own_carriageway():
    # A (eastbound) at y = 0 and B (westbound) 8 m north, as on US-6: the line on A, heading east, is
    # legal; snapped to the nearer-but-wrong B it would read as a wrong-way run.
    els = [way(10, [(0, 0), (300, 0)], highway="trunk", oneway="yes"),
           way(11, [(300, 8), (0, 8)], highway="trunk", oneway="yes")]
    with tempfile.TemporaryDirectory() as t:
        rep = roc.run_check(project(t, densify([(0, 0), (300, 0)]), els, {"layouts": [FWD]}))
        lo = layout(rep, "street_full")
        assert rep["verdict"] == "PASS" and {r["way"] for r in lo["with_arrows_runs"]} == {10}
        rep2 = roc.run_check(project(t, densify([(0, 8), (300, 8)]), els, {"layouts": [FWD]}))
        assert [r["way"] for r in layout(rep2, "street_full")["against_runs"]] == [11]


def test_junction_shared_by_the_other_side_is_not_a_wrong_way_run():
    # Exit 259's shape: the lap comes east on X and turns onto Y (north-east-bound); Z, the south-west-
    # bound other side, ends at the same node and diverges from Y at 30 deg. The corner segments must
    # match Y (or nothing), never Z.
    a = 30 * math.pi / 180
    els = [way(20, [(-120, 0), (0, 0)], highway="primary"),
           way(21, [(0, 0), (100 * math.cos(math.pi / 4), 100 * math.sin(math.pi / 4))], highway="secondary", oneway="yes"),
           way(22, [(100 * math.cos(math.pi / 4 + a), 100 * math.sin(math.pi / 4 + a)), (0, 0)],
               highway="secondary", oneway="yes")]
    line = densify([(-120, 0), (0, 0), (100 * math.cos(math.pi / 4), 100 * math.sin(math.pi / 4))])
    with tempfile.TemporaryDirectory() as t:
        rep = roc.run_check(project(t, line, els, {"layouts": [FWD]}))
        lo = layout(rep, "street_full")
        assert rep["verdict"] == "PASS" and lo["against_total_m"] == 0
        assert 22 not in {e["way"] for e in rep["ways_driven_forward"]}


def test_junction_corner_cutting_both_ways_is_a_gap_not_a_run():
    # a vertex-cutting chord across a right-angle corner: its ends sit 3.5 m from the far way
    els = [way(30, [(-100, 0), (0, 0)], highway="primary", oneway="yes"),
           way(31, [(0, 0), (0, 100)], highway="primary", oneway="yes")]
    line = densify([(-100, 0), (-3.5, 0)]) + densify([(0, 3.5), (0, 100)])
    with tempfile.TemporaryDirectory() as t:
        rep = roc.run_check(project(t, line, els, {"layouts": [FWD]}))
        assert rep["verdict"] == "PASS"
        assert len(rep["unmatched_runs"]) == 1 and rep["unmatched_m"] < 5.0


def test_reverse_declared_stretches_pass_and_undeclared_or_stale_fail():
    els = [way(40, [(0, 0), (200, 0)], highway="trunk", oneway="yes"),
           way(41, [(200, 0), (400, 0)], highway="secondary")]
    line = densify([(0, 0), (400, 0)])
    base = {"divided": {"stretches": [{"id": "s1", "ways": [40]}, {"id": "ghost", "ways": [99]}]}}
    with tempfile.TemporaryDirectory() as t:
        ok = roc.run_check(project(t, line, els, {**base, "layouts": [FWD, {**REV, "against_oneway": ["s1"]}]}))
        rv = layout(ok, "street_reverse")
        assert ok["verdict"] == "PASS" and rv["against_by_stretch_m"] == {"s1": 200.0}
        undeclared = roc.run_check(project(t, line, els, {**base, "layouts": [REV]}))
        assert undeclared["verdict"] == "FAIL" and layout(undeclared, "street_reverse")["undeclared_against_m"] == 200.0
        stale = roc.run_check(project(t, line, els, {**base, "layouts": [{**REV, "against_oneway": ["s1", "ghost"]}]}))
        assert stale["verdict"] == "FAIL" and any("stale declaration" in f for f in stale["fails"])
        unknown = roc.run_check(project(t, line, els, {**base, "layouts": [{**REV, "against_oneway": ["s1", "nope"]}]}))
        assert any("not declared in divided.stretches" in f for f in unknown["fails"])


def test_race_layouts_are_not_checked():
    els = [way(50, [(0, 0), (200, 0)], highway="trunk", oneway="yes")]
    with tempfile.TemporaryDirectory() as t:
        rep = roc.run_check(project(t, densify([(0, 0), (200, 0)]), els,
                                    {"layouts": [{"id": "race_cw", "kind": "race", "direction": "reverse"}]}))
        lo = layout(rep, "race_cw")
        assert rep["verdict"] == "PASS" and lo["verdict"] == "SKIP" and lo["checked"] is False


def test_closed_lap_merges_the_run_across_the_seam():
    # a 100 m square of one-ways, legal anticlockwise; the line starts mid-way along the first side
    sq = [(0, 0), (100, 0), (100, 100), (0, 100)]
    els = [way(60 + k, [sq[k], sq[(k + 1) % 4]], highway="primary", oneway="yes") for k in range(4)]
    line = densify([(50, 0), (100, 0), (100, 100), (0, 100), (0, 0), (50, 0)])
    with tempfile.TemporaryDirectory() as t:
        rep = roc.run_check(project(t, line, els, {"layouts": [FWD, REV]}))
        assert layout(rep, "street_full")["verdict"] == "PASS"
        rv = layout(rep, "street_reverse")
        assert len(rv["against_runs"]) == 4                       # one run per side, the seam merged
        first = next(r for r in rv["against_runs"] if r["way"] == 60)
        assert abs(first["length_m"] - 100) < 0.5


def test_cli_writes_the_report_and_sets_the_exit_code():
    with tempfile.TemporaryDirectory() as t:
        p = project(t, densify([(200, 0), (0, 0)]), [way(70, [(0, 0), (200, 0)], highway="primary", oneway="yes")],
                    {"layouts": [FWD]})
        out = Path(t) / "r.json"
        assert roc.main([str(p), "--out", str(out)]) == 1
        rep = json.loads(out.read_text(encoding="utf-8"))
        assert rep["verdict"] == "FAIL" and "frame" in rep and rep["params"] == {"snap_m": 3.0, "min_cos": 0.7}
        p2 = project(t, densify([(0, 0), (200, 0)]), [way(70, [(0, 0), (200, 0)], highway="primary", oneway="yes")],
                     {"layouts": [FWD]})
        assert roc.main([str(p2), "--out", str(out)]) == 0
        assert roc.main([]) == 2 and roc.main([str(p2), "--bogus"]) == 2


def test_lariat_v3_passes_and_the_july_line_fails_on_its_two_defects():
    """The real thing, offline: the V3 centreline + its own snapshot pass every street layout; the
    recovered July centreline fails Full on exactly exit 259 (42005706) and the 19th St eastbound side
    (1283267905 + 533500102), and nothing else."""
    if not (LARIAT / "data" / "centerline.geojson").exists():
        return                                                   # data/ is local (not committed)
    rep = roc.run_check(LARIAT)
    assert rep["verdict"] == "PASS"
    full = layout(rep, "street_full")
    rev = layout(rep, "street_reverse")
    assert full["against_total_m"] == 0
    assert set(rev["against_by_stretch_m"]) == {"exit259", "colfax", "us6_offramp", "nineteenth"}
    assert rev["undeclared_against_m"] == 0
    driven = {e["way"] for e in rep["ways_driven_forward"]}
    assert {119006778, 533503210, 1283267904, 1106864351, 533504135} <= driven
    assert not driven & {42005706, 533503214, 533500102, 1283267905}
    july = LARIAT / "data" / "source-july"
    if (july / "centerline.geojson").exists() and (july / "osm.widths.cache.json").exists():
        jr = roc.run_check(LARIAT, centerline=july / "centerline.geojson", snapshot=july / "osm.widths.cache.json",
                           only=["street_full"])
        bad = {r["way"]: r["length_m"] for r in layout(jr, "street_full")["against_runs"]}
        assert set(bad) == {42005706, 1283267905, 533500102}
        assert abs(bad[42005706] - 84) < 2 and abs(bad[1283267905] + bad[533500102] - 105) < 3

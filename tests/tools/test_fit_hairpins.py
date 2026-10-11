"""tools/fit_hairpins.py: replace a faceted hairpin with a clothoid-arc-clothoid and gate it.

Lookout Lariat V3 plan A2 / P2 step 2 (ledger 0048, dossier section 4). The OSM hairpin ways have a node every
4-5 m turning 17-27 deg, so the 3 m centreline steps up to 25 deg point to point at the base hairpin. These
pin the curve maths (a clothoid against its series, an arc in closed form, the Newton solve recovering a
known curve), the circle fit, the gate (facets fail, a fitted arc passes, a curvature jump fails the
adjacent-step rule), and the whole tool on synthetic OSM-like lines whose true geometry is known: it must
find the true curve under the facets (left and right hand, 180 and 200 deg, two stacked hairpins), honour the
per-corner radius override, leave a kink pending until it has a radius, refuse a stale corner list, a fit
across the lap seam and an --out-dir inside the track's data, and keep every untouched vertex byte-for-byte.
Plus the real Lariat base hairpin (C1) on the current centreline. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import fit_hairpins as fh  # noqa: E402

LAT0, LON0 = 39.70, -105.20
MLON, MLAT = fh._meters_per_degree(LAT0)
LARIAT = ROOT / "tracks" / "lookout-lariat"


# --------------------------------------------------------------------------------------------------
# synthetic geometry, built independently of the tool
# --------------------------------------------------------------------------------------------------
def trace(pieces, start=(0.0, 0.0), th=0.0, h=0.01):
    """Dense reference path through curvature pieces [(length, k_start, k_end), ...] (curvature linear
    within a piece), integrated with tiny midpoint steps."""
    x, y = start
    pts = [(x, y)]
    for L, k0, k1 in pieces:
        n = max(1, int(round(L / h)))
        d = L / n
        for i in range(n):
            k = k0 + (k1 - k0) * (i + 0.5) / n
            mid = th + 0.5 * k * d
            x += d * math.cos(mid)
            y += d * math.sin(mid)
            th += k * d
            pts.append((x, y))
    return pts


def resample(poly, step):
    """Points every ``step`` metres along a polyline, plus its last point."""
    out = [poly[0]]
    need = step
    acc = 0.0
    for a, b in zip(poly, poly[1:]):
        seg = math.dist(a, b)
        while acc + seg >= need - 1e-12:
            t = (need - acc) / seg
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
            need += step
        acc += seg
    if math.dist(out[-1], poly[-1]) > 1e-6:
        out.append(poly[-1])
    return out


def osm_like(true_pts, node_m=4.5, jitter=0.08):
    """What OSM + the route stage make of a true road: nodes every ``node_m`` metres, the ones on the
    curve with a few cm of deterministic mapping jitter (a straight OSM leg is an exact line between
    its end nodes), then the 3 m resample the centreline stage does."""
    nodes = resample(true_pts, node_m)
    out = []
    for i, p in enumerate(nodes):
        if 0 < i < len(nodes) - 1:
            a, b = nodes[i - 1], nodes[i + 1]
            if abs(fh._wrap(fh.heading(p, b) - fh.heading(a, p))) > math.radians(0.5):
                L = math.dist(a, b)
                nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
                off = jitter * math.sin(1.7 * i + 0.3)
                p = (p[0] + off * nx, p[1] + off * ny)
        out.append(p)
    return resample(out, 3.0)


def hairpin_pieces(R=12.0, turn_deg=180.0, Ls=10.0, leg=80.0, sign=1):
    k = sign / R
    Lc = math.radians(turn_deg) * R - Ls
    return [(leg, 0.0, 0.0), (Ls, 0.0, k), (Lc, k, k), (Ls, k, 0.0), (leg, 0.0, 0.0)], leg + Ls + Lc / 2


def write_project(tmp: Path, pts_xy, corners, **block):
    proj = tmp / "proj"
    (proj / "data").mkdir(parents=True)
    coords = [[LON0 + x / MLON, LAT0 + y / MLAT] for x, y in pts_xy]
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "name": "centerline", "kind": "full", "closed": False, "default_width_m": 6.7,
        "widths_m": [6.7] * len(coords), "length_m": 0.0, "point_count": len(coords)},
        "geometry": {"type": "LineString", "coordinates": coords}}]}
    (proj / "data" / "centerline.geojson").write_text(json.dumps(gj), encoding="utf-8")
    cfg = {"name": "synthetic", "hairpin_fit": dict(block, corners=corners)}
    (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return proj


def local(coords):
    return [((c[0] - LON0) * MLON, (c[1] - LAT0) * MLAT) for c in coords]


def run_synthetic(pieces, corners, tmp, **block):
    true = trace(pieces)
    line = osm_like(true)
    proj = write_project(tmp, line, corners, **block)
    src_bytes = (proj / "data" / "centerline.geojson").read_bytes()
    out = tmp / "out"
    rep = fh.run(proj, out, detect_deg=None)
    assert (proj / "data" / "centerline.geojson").read_bytes() == src_bytes  # the source is never touched
    assert sorted(x.name for x in (proj / "data").iterdir()) == ["centerline.geojson"]
    fitted = json.loads((out / "centerline.fitted.geojson").read_text(encoding="utf-8"))
    return rep, true, line, proj, out, fitted["features"][0]


def max_dist_to(pts, poly):
    return max(fh.dist_to_polyline(p, poly) for p in pts)


# --------------------------------------------------------------------------------------------------
# curve maths
# --------------------------------------------------------------------------------------------------
def test_clothoid_matches_its_series():
    L, R = 10.0, 50.0  # a clothoid from straight to 1/R over L: x, y by the standard series
    x, y, th = fh.piece_at(0.0, 0.0, 0.0, L, 0.0, 1.0 / R, L)
    xs = L - L ** 3 / (40 * R ** 2) + L ** 5 / (3456 * R ** 4) - L ** 7 / (599040 * R ** 6)
    ys = L ** 2 / (6 * R) - L ** 4 / (336 * R ** 3) + L ** 6 / (42240 * R ** 5) - L ** 8 / (9676800 * R ** 7)
    assert abs(x - xs) < 1e-12 and abs(y - ys) < 1e-12, (x, xs, y, ys)
    assert abs(th - L / (2 * R)) < 1e-12


def test_arc_piece_is_a_circle():
    R, L = 12.0, 30.0
    x, y, th = fh.piece_at(0.0, 0.0, 0.0, L, 1.0 / R, 1.0 / R, L)
    assert abs(math.hypot(x, y - R) - R) < 1e-12  # on the circle centred (0, R)
    assert abs(th - L / R) < 1e-12
    # the same arc as a (degenerate) clothoid through the quadrature path agrees
    x2, y2, _ = fh.piece_at(0.0, 0.0, 0.0, L, 1.0 / R, 1.0 / R + 1e-14, L)
    assert math.hypot(x - x2, y - y2) < 1e-9


def test_curve_turn_spacing_and_reference_agree():
    c = fh.Curve(0.0, 0.0, 0.3, -1, 12.0, 8.0, 20.0, 12.0)
    x, y, th = c.end()
    assert abs(th - (0.3 - (4.0 + 20.0 + 6.0) / 12.0)) < 1e-12
    ref = trace([(8.0, 0.0, -1 / 12.0), (20.0, -1 / 12.0, -1 / 12.0), (12.0, -1 / 12.0, 0.0)], th=0.3,
                h=0.002)[-1]
    assert math.hypot(x - ref[0], y - ref[1]) < 1e-4
    pts, ds = c.sample(1.0)
    assert ds <= 1.0 and len(pts) == math.ceil(40.0 / 1.0) - 1
    full = [(0.0, 0.0)] + pts + [(x, y)]
    gaps = [math.dist(a, b) for a, b in zip(full, full[1:])]
    assert max(gaps) - min(gaps) < 1e-3  # chords of an even arc-length spacing


def test_solve_transitions_recovers_a_known_curve():
    true = fh.Curve(5.0, -2.0, 1.1, 1, 12.0, 8.0, 20.0, 12.0)
    x, y, th = true.end()
    delta = th - 1.1
    sol = fh.solve_transitions((5.0, -2.0), 1.1, (x, y), delta, 12.0)
    assert sol is not None
    L1, Lc, L2 = sol
    assert abs(L1 - 8.0) < 1e-4 and abs(Lc - 20.0) < 1e-4 and abs(L2 - 12.0) < 1e-4, sol
    # an end point no arc of that radius can reach is refused, not forced
    assert fh.solve_transitions((0.0, 0.0), 0.0, (0.0, 60.0), math.pi, 12.0) is None


def test_circle_fit_exact_and_noisy():
    cx, cy, R = 3.0, -4.0, 12.5
    pts = [(cx + R * math.cos(t), cy + R * math.sin(t)) for t in [0.1 * i for i in range(20)]]
    fx, fy, fR, rms = fh.circle_fit(pts)
    assert abs(fx - cx) < 1e-8 and abs(fy - cy) < 1e-8 and abs(fR - R) < 1e-8 and rms < 1e-8
    noisy = [(x + 0.05 * math.sin(7 * i), y + 0.05 * math.cos(5 * i)) for i, (x, y) in enumerate(pts)]
    assert abs(fh.circle_fit(noisy)[2] - R) < 0.3


# --------------------------------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------------------------------
def test_gate_fails_facets_and_passes_a_fitted_arc():
    R = 12.0
    arc = [(R * math.sin(s / R), R - R * math.cos(s / R)) for s in [0.5 * i for i in range(60)]]
    assert fh.gate(arc, 1, len(arc) - 2, R, 1.0, 1.5)["pass"]
    # an R 12 m arc sampled every 3 m with every other point pushed 0.5 m out: facets
    facets = [(R * math.sin(s / R), R - R * math.cos(s / R)) for s in [3.0 * i for i in range(12)]]
    facets = [(x * (1.04 if i % 2 else 1.0), y) for i, (x, y) in enumerate(facets)]
    g = fh.gate(facets, 1, len(facets) - 2, R, 1.0, 1.5)
    assert not g["pass"] and any(f["rule"] == "adjacent" for f in g["fails"])
    # straight into the arc with no transition: each step is within the arc's own limit, but the
    # jump from 0 to the arc's step trips the adjacent-step rule
    jump = [(-5.0 + i, 0.0) for i in range(5)] + arc[2::2]
    g = fh.gate(jump, 1, len(jump) - 2, R, 1.0, 1.5)
    assert not g["pass"]
    assert all(f["rule"] == "adjacent" for f in g["fails"])


# --------------------------------------------------------------------------------------------------
# the tool on synthetic OSM-like lines whose true geometry is known
# --------------------------------------------------------------------------------------------------
def _assert_good_fit(r, R_true):
    assert r["status"] == "PASS" and r["gate"] == "PASS", r.get("why")
    assert abs(r["measured"]["radius_m"] - R_true) / R_true < 0.10, r["measured"]
    assert abs(r["radius_fit_m"] - R_true) / R_true < 0.15, r["radius_fit_m"]
    assert r["before"]["max_step_deg"] >= 8.0 and r["before"]["gate_fails"] > 0  # the input is faceted
    a = r["after"]
    assert a["spacing_m"] <= 1.0
    assert a["max_step_deg"] <= a["step_limit_deg"] and a["max_adjacent_diff_deg"] <= 1.5
    assert r["lateral_move_m"]["max"] <= 0.6


def _on_true_road(feat, cid, true, tol=0.5):
    """The spliced span of corner ``cid`` sits on the TRUE road, not just near the facets."""
    a, b = next(c["v"] for c in feat["properties"]["hairpin_fit"]["corners"] if c["id"] == cid)
    P = local(feat["geometry"]["coordinates"])
    d = max_dist_to(P[a:b + 1], true)
    assert d < tol, (cid, d)


def test_left_hairpin_recovers_the_true_curve():
    pieces, apex_st = hairpin_pieces(R=12.0, turn_deg=180.0, sign=1)
    with tempfile.TemporaryDirectory() as td:
        rep, true, line, proj, out, feat = run_synthetic(pieces, [{"id": "H1", "st_m": apex_st}], Path(td))
        r = rep["corners"][0]
        _assert_good_fit(r, 12.0)
        assert r["turn_deg"] > 170.0
        _on_true_road(feat, "H1", true)
        a, b = feat["properties"]["hairpin_fit"]["corners"][0]["v"]
        # every vertex outside the span is the source vertex, byte-for-byte, in order
        src = json.loads((proj / "data" / "centerline.geojson").read_text())["features"][0]
        cs, cf = src["geometry"]["coordinates"], feat["geometry"]["coordinates"]
        A, B = r["span"]["v"]  # the fit replaces source vertices A..B with new points a..b
        assert a == A and cf[:A] == cs[:A] and cf[b + 1:] == cs[B + 1:]
        slide_a, slide_b = r["span"]["slide_m"]
        assert (cf[a] == cs[A]) == (slide_a == 0.0) and (cf[b] == cs[B]) == (slide_b == 0.0)
        assert slide_a <= 0.0 <= slide_b
        props = feat["properties"]
        assert props["point_count"] == len(cf) == len(props["widths_m"])
        assert rep["status"] == "PASS" and (out / "H1.svg").exists()


def test_right_hand_and_over_180_hairpins():
    with tempfile.TemporaryDirectory() as td:
        pieces, apex_st = hairpin_pieces(R=13.0, turn_deg=200.0, sign=-1, leg=50.0)
        rep, true, line, proj, out, feat = run_synthetic(pieces, [{"id": "H1", "st_m": apex_st}], Path(td))
        r = rep["corners"][0]
        _assert_good_fit(r, 13.0)
        assert r["turn_deg"] < -190.0
        _on_true_road(feat, "H1", true)


def test_stacked_hairpins_get_their_own_spans():
    k = 1 / 12.0
    Lc = math.pi * 12.0 - 10.0
    pieces = [(60.0, 0, 0), (10.0, 0, k), (Lc, k, k), (10.0, k, 0), (45.0, 0, 0),
              (10.0, 0, -k), (Lc, -k, -k), (10.0, -k, 0), (60.0, 0, 0)]
    first = 60.0 + 10.0 + Lc / 2
    second = 60.0 + 20.0 + Lc + 45.0 + 10.0 + Lc / 2
    with tempfile.TemporaryDirectory() as td:
        rep, true, line, proj, out, feat = run_synthetic(
            pieces, [{"id": "H2", "st_m": second}, {"id": "H1", "st_m": first}], Path(td))
        r1, r2 = rep["corners"]  # reported in driving order
        assert (r1["id"], r2["id"]) == ("H1", "H2")
        _assert_good_fit(r1, 12.0)
        _assert_good_fit(r2, 12.0)
        assert r1["turn_deg"] > 0 > r2["turn_deg"]
        assert r1["span"]["v"][1] < r2["span"]["v"][0]  # never share a vertex
        assert rep["index_shift"]["entries"][0]["from_v"] == r1["span"]["v"][1]
        _on_true_road(feat, "H1", true)
        _on_true_road(feat, "H2", true)


def test_radius_override_is_used():
    pieces, apex_st = hairpin_pieces(R=12.0, turn_deg=180.0)
    with tempfile.TemporaryDirectory() as td:
        rep, *_ = run_synthetic(pieces, [{"id": "H1", "st_m": apex_st, "radius_m": 11.0}], Path(td))
        r = rep["corners"][0]
        assert r["radius_fit_m"] == 11.0 and r["radius_kind"] == "override"
        assert r["radius_source"].startswith("config")
        assert r["after"]["max_turn_rate_deg_per_m"] == round(fh.DEG / 11.0, 2)
        assert r["gate"] == "PASS"
        # a radius too wide for the gap between the legs has no curve at all: FAIL, never forced
        rep, *_ = run_synthetic(pieces, [{"id": "H1", "st_m": apex_st, "radius_m": 14.0}], Path(td) / "w")
        r = rep["corners"][0]
        assert r["status"] == "FAIL" and "no anchor pair" in r["why"] and not r["spliced"]


def test_kink_stays_pending_until_it_has_a_radius():
    # a T-junction-like corner: one node turns 90 deg
    corner = [(float(x), 0.0) for x in range(0, 101)] + [(100.0, float(y)) for y in range(1, 101)]
    line = resample(corner, 3.0)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = write_project(tmp, line, [{"id": "K1", "st_m": 100.0}])
        rep = fh.run(proj, tmp / "out", detect_deg=None)
        r = rep["corners"][0]
        assert r["status"] == "PENDING" and rep["status"] == "PENDING"
        assert r["measured"]["kind"] == "kink" and r["measured"]["biggest_share"] > 0.5
        assert fh.main([str(proj), "--out-dir", str(tmp / "out2"), "--detect-deg", "0"]) == 3
        # with a radius it is fitted, and the lateral-move ceiling says how far a fillet leaves the
        # OSM line through a junction node
        rep = fh.run(proj, tmp / "out3", radius_cli={"K1": 10.0}, detect_deg=None)
        r = rep["corners"][0]
        assert r["radius_fit_m"] == 10.0 and r["gate"] == "PASS"
        assert r["lateral_move_m"]["max"] > 1.5 and r["status"] == "FAIL" and not r["spliced"]
        fitted = json.loads((tmp / "out3" / "centerline.fitted.geojson").read_text())
        assert fitted["features"][0]["properties"]["point_count"] == len(line)  # a FAIL is never spliced
        assert fh.main([str(proj), "--out-dir", str(tmp / "out4"), "--radius", "K1=10",
                        "--detect-deg", "0"]) == 1


def test_refusals():
    pieces, apex_st = hairpin_pieces(R=12.0, turn_deg=180.0)
    line = osm_like(trace(pieces))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj = write_project(tmp, line, [{"id": "H1", "st_m": apex_st}])
        for bad in (proj / "data", proj / "data" / "sub"):  # never into the track's data
            try:
                fh.run(proj, bad, detect_deg=None)
                raise AssertionError("wrote into data/")
            except SystemExit as e:
                assert "refusing" in str(e)
        assert fh.main([str(proj), "--out-dir", str(proj / "data")]) == 2
        # a declared corner where the line runs straight: the corner list is stale
        proj2 = write_project(tmp / "b", line, [{"id": "H1", "st_m": 20.0}])
        try:
            fh.run(proj2, tmp / "out", detect_deg=None)
            raise AssertionError("stale corner accepted")
        except SystemExit as e:
            assert "no longer matches" in str(e)
        # a corner whose reach crosses the start of the line (the lap seam, L13)
        short = trace([(15.0, 0, 0)] + hairpin_pieces(R=12.0, leg=60.0)[0][1:])
        proj3 = write_project(tmp / "c", osm_like(short), [{"id": "H1", "st_m": 15.0 + 10.0 + 13.7}])
        try:
            fh.run(proj3, tmp / "out", detect_deg=None)
            raise AssertionError("seam crossing accepted")
        except SystemExit as e:
            assert "seam" in str(e)


def test_lariat_base_hairpin():
    """The real C1 on the current V3 centreline: 25 deg facets in, a smooth R ~12 m curve out."""
    with tempfile.TemporaryDirectory() as td:
        rep = fh.run(LARIAT, Path(td), only=["C1"], detect_deg=None)
        (r,) = rep["corners"]
        assert r["id"] == "C1" and r["status"] == "PASS"
        assert r["before"]["max_step_deg"] >= 24.0  # dossier 4: the base hairpin's 25 deg step
        assert 11.0 <= r["radius_fit_m"] <= 14.0
        assert r["after"]["max_step_deg"] <= r["after"]["step_limit_deg"] <= 6.0
        assert r["after"]["max_adjacent_diff_deg"] <= 1.5 and r["after"]["spacing_m"] <= 1.0
        assert r["lateral_move_m"]["max"] <= 1.5
        assert 245.0 <= r["span"]["st_m"][0] < r["apex_st_m"] < r["span"]["st_m"][1] <= 310.0

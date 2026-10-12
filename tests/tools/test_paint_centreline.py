"""tools/paint_centreline.py: the OSM line moved onto the traced paint, curvature-continuous on the climb.

Lookout Lariat V3 (ledger 0048, P2). A synthetic lap whose true road is known: a stadium (straights 300 m,
semicircles R 40 m) with a right-angle junction kink on the far side. Its "OSM" line is the true road at 3 m
with two OSM-like errors on the climb (the first half): 1.8 m sideways on a stretch of straight, and the
first semicircle faceted with 6 m chords 2 m inside the paint, as OSM cuts the Lariat's C4. The paint traces
are the true road in two windows (one with a good yellow circle over the hairpin's core) and, outside the
climb, a window on each arm of the junction. Pinned: the result follows the paint within the gate's 0.75 m
and passes all four checks of tools/verify_centreline_paint.py; untouched OSM vertices are byte-for-byte; the
junction node stays a node; the seam is closed exactly and smooth (L13); widths and osm_station_m are carried;
a fresh gps output becomes the source file and a replaced paint line is kept for the remap. Plus the real
Lariat: the committed centreline is exactly what the tool makes from the committed inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import paint_centreline as pc  # noqa: E402
import verify_centreline_paint as vp  # noqa: E402
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

LAT0, LON0 = 39.70, -105.20
MLON, MLAT = _meters_per_degree(LAT0)
R = 40.0
L = 300.0
LARIAT = ROOT / "tracks" / "lookout-lariat"


def ll(p):
    return [LON0 + p[0] / MLON, LAT0 + p[1] / MLAT]


def true_road(step=0.25):
    """The painted road: east along y = 0 from x = 0, the left semicircle about (L, R), west along y = 2R to
    x = 60, a right-angle junction to the south... (a kink: the lap turns 90 deg left at (60, 2R)), south to
    y = R ... and home: the closing semicircle about (0, R) is replaced by straights through a junction node."""
    pts = []

    def seg(a, b):
        n = max(1, int(math.dist(a, b) / step))
        for k in range(n):
            pts.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))

    def arc(c, a0, a1):
        n = max(2, int(abs(a1 - a0) * R / step))
        for k in range(n):
            a = a0 + (a1 - a0) * k / n
            pts.append((c[0] + R * math.cos(a), c[1] + R * math.sin(a)))
    seg((0.0, 0.0), (L, 0.0))
    arc((L, R), -math.pi / 2, math.pi / 2)
    seg((L, 2 * R), (-60.0, 2 * R))       # west, past x = 0
    seg((-60.0, 2 * R), (-60.0, 0.0))     # the junction node at (-60, 2R): a 90 deg left kink
    seg((-60.0, 0.0), (0.0, 0.0))         # home: another 90 deg left at (-60, 0)
    return pts


def resample(poly, step, closed=True):
    pts = poly + ([poly[0]] if closed else [])
    st = [0.0]
    for i in range(1, len(pts)):
        st.append(st[-1] + math.dist(pts[i - 1], pts[i]))
    out = []
    n = int(st[-1] / step)
    j = 0
    for k in range(n):
        s = k * st[-1] / n
        while st[j + 1] < s:
            j += 1
        t = (s - st[j]) / (st[j + 1] - st[j])
        out.append((pts[j][0] + t * (pts[j + 1][0] - pts[j][0]), pts[j][1] + t * (pts[j + 1][1] - pts[j][1])))
    return out


def osm_like():
    """The true road at 3 m, 1.8 m north on x 100-220 (30 m ramps), and the first semicircle as 6 m chords
    2 m inside. Corners of the junction kept as single nodes."""
    base = resample(true_road(), 3.0)
    out = []
    for x, y in base:
        if y < 1.0 and 70 <= x <= 250:
            w = min(1.0, max(0.0, (x - 70) / 30.0), max(0.0, (250 - x) / 30.0))
            y = y + 1.8 * w * w * (3 - 2 * w)
        if x > L:  # on the first semicircle: pull 2 m inside, snapped onto 6 m chords below
            a = math.atan2(y - R, x - L)
            x, y = L + (R - 2.0) * math.cos(a), R + (R - 2.0) * math.sin(a)
        out.append((x, y))
    # facet the semicircle: keep every second vertex there
    fac = [p for i, p in enumerate(out) if not (p[0] > L + 0.5 and i % 2)]
    # the two junction corners as exact nodes
    for node in ((-60.0, 2 * R), (-60.0, 0.0)):
        k = min(range(len(fac)), key=lambda i: math.dist(fac[i], node))
        fac[k] = node
    return fac


def write_project(tmp: Path, osm_pts, widths=None, climb=None):
    proj = tmp / "proj"
    (proj / "data" / "aerial").mkdir(parents=True)
    coords = [ll(p) for p in osm_pts] + [ll(osm_pts[0])]
    widths = widths or [6.7] * len(coords)
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "name": "centerline", "kind": "full", "closed": True, "widths_m": widths, "point_count": len(coords)},
        "geometry": {"type": "LineString", "coordinates": coords}}]}
    (proj / "data" / "centerline.geojson").write_text(json.dumps(gj), encoding="utf-8")
    cfg = {"name": "t", "slug": "t", "loop": True, "hairpin_fit": {"climb_st_m": climb or [0, 470]}}
    (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return proj


def traces(osm_pts):
    """paint_traces.json for the true road: windows W1 (straight, x 60-260), C1 (the semicircle +- 25 m legs,
    with its good yellow circle) and the junction arms J_in (y = 2R, x -45..-15) / J_out (x = -60, y 65..35),
    in a frame whose origin is the OSM line's centroid (as tools/aerial_measure.py writes it)."""
    import fit_hairpins as fh
    lon_lat = [ll(p) for p in osm_pts] + [ll(osm_pts[0])]
    lon0, lat0 = fh.centroid([tuple(c) for c in lon_lat])
    mlon, mlat = _meters_per_degree(lat0)
    ox, oy = (lon0 - LON0) * MLON, (lat0 - LAT0) * MLAT
    P = [((a - lon0) * mlon, (b - lat0) * mlat) for a, b in lon_lat]
    st = fh.stations(P)

    def xz(p):
        lon, lat = ll(p)
        return [round((lon - lon0) * mlon, 3), round((lat - lat0) * mlat, 3)]

    def station(p):
        q = xz(p)
        return round(min(((math.dist(q, P[i]), st[i]) for i in range(len(P))))[1], 1)
    road = true_road(0.5)

    def window(wid, kind, sel, core=None):
        pts = [p for p in road if sel(p)]
        hd = []
        for i, p in enumerate(pts):
            a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
            hd.append(round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), 1))
        w = {"id": wid, "kind": kind, "window": wid,
             "yellow": {"xz_m": [xz(p) for p in pts], "lap_st_m": [station(p) for p in pts], "heading_deg": hd,
                        "confidence": ["high"] * len(pts), "source": ["profile"] * len(pts)},
             "edge_left": {"xz_m": [], "lap_st_m": [], "heading_deg": [], "confidence": [], "source": []},
             "edge_right": {"xz_m": [], "lap_st_m": [], "heading_deg": [], "confidence": [], "source": []},
             "reference": {"xz_m": [xz(p) for p in pts], "lap_st_m": [station(p) for p in pts], "supported": [True] * len(pts)}}
        if core:
            w["core"] = core
        return w
    a0, a1 = -math.pi / 2 + 0.2 * math.pi, -math.pi / 2 + 0.8 * math.pi
    core = {"direction": "left", "turn_deg": 180.0, "arc_deg": 108.0,
            "yellow_circle": {"centre_xz_m": xz((L, R)), "R_m": R, "rms_m": 0.05, "n": 200, "good": True},
            "core_ends_on_yellow_circle": [{"xz_m": xz((L + R * math.cos(a0), R + R * math.sin(a0)))},
                                           {"xz_m": xz((L + R * math.cos(a1), R + R * math.sin(a1)))}]}
    ws = [window("W1", "width_station", lambda p: p[1] < 1 and 60 <= p[0] <= 260),
          window("C1", "corner", lambda p: (p[0] >= L - 25 and (p[1] < 1 or p[1] > 2 * R - 1)) or p[0] >= L, core),
          window("J_in", "junction_arm", lambda p: p[1] > 2 * R - 1 and -45 <= p[0] <= -15),
          window("J_out", "junction_arm", lambda p: abs(p[0] + 60) < 0.01 and 35 <= p[1] <= 65)]
    return {"frame": {"origin_lonlat": [lon0, lat0], "m_per_deg": [mlon, mlat]},
            "registration": {"osm_minus_imagery_EN_m": [0.0, 0.0]}, "windows": ws, "_origin_offset": [ox, oy]}


def built(tmp, widths=None):
    osm = osm_like()
    proj = write_project(tmp, osm, widths)
    tr = traces(osm)
    (proj / "data" / "aerial" / "paint_traces.json").write_text(json.dumps(tr), encoding="utf-8")
    rep = pc.run(proj, log=lambda *a: None)
    gj = json.loads((proj / "data" / "centerline.geojson").read_text(encoding="utf-8"))
    return proj, osm, tr, rep, gj


def test_follows_the_paint_and_passes_the_gate():
    with tempfile.TemporaryDirectory() as td:
        proj, osm, tr, rep, gj = built(Path(td))
        line = vp.Line.from_geojson(gj)
        res = vp.gate(line, tr, [0, 470], loop=True)
        assert res["pass"], {k: res[k]["pass"] for k in ("a_paint", "b_curvature", "c_topology", "d_closure")}
        assert res["a_paint"]["max_m"] <= 0.3
        # the OSM line misses the same paint by its injected errors
        osm_line = vp.Line.from_geojson(json.loads((proj / "data" / "centerline.osm.geojson").read_text(encoding="utf-8")))
        o = vp.gate(osm_line, tr, [0, 470], loop=True)
        assert not o["a_paint"]["pass"] and o["a_paint"]["max_m"] > 1.7
        per = {w["window"]: w for w in rep["windows"]}
        assert per["W1"]["osm_max_m"] > 1.7 and per["W1"]["new_max_m"] <= 0.3
        assert per["C1"]["osm_max_m"] > 1.9 and per["C1"]["new_max_m"] <= 0.3
        # the hairpin's tightest radius on the new line is the painted one, not OSM's 38 m chords
        rr = line.min_radius_near(line.frame_xy_from_traces(tr, *tr["windows"][1]["core"]["yellow_circle"]["centre_xz_m"]), R + 6)
        assert abs(rr - R) < 2.0, rr
        assert rep["regions"][0]["name"] == "climb" and rep["regions"][0]["spacing_m"][0] >= 0.95


def test_osm_kept_outside_the_moved_stretches_and_the_junction_node_kept():
    # with gaps longer than GAP_INTERP_M the offsets taper to zero and the middle of a gap is OSM, byte for
    # byte (on this short lap every gap is shorter than the real 400 m, so the test shortens it)
    keep = pc.GAP_INTERP_M
    pc.GAP_INTERP_M = 200.0
    try:
        with tempfile.TemporaryDirectory() as td:
            _osm_kept(Path(td))
    finally:
        pc.GAP_INTERP_M = keep


def _osm_kept(td):
    if True:
        proj, osm, tr, rep, gj = built(td)
        f = gj["features"][0]
        coords = f["geometry"]["coordinates"]
        src = json.loads((proj / "data" / "centerline.osm.geojson").read_text(encoding="utf-8"))["features"][0]["geometry"]["coordinates"]
        srcset = {tuple(c) for c in src}
        # the far straight between x = 200 and 100 (nothing moved it): every OSM vertex there copied exactly
        far = [c for c in src if abs((c[1] - LAT0) * MLAT - 2 * R) < 0.01 and 100 <= (c[0] - LON0) * MLON <= 150]
        assert far and all(tuple(c) in {tuple(x) for x in coords} for c in far)
        # the junction node at (-60, 2R) is pinned (outside the climb) and still turns ~90 deg at one point
        line = vp.Line.from_geojson(gj)
        S = line.steps()
        node = min(range(line.n), key=lambda i: math.dist(line.lonlat[i], tuple(ll((-60.0, 2 * R)))))
        assert abs(S[node]) * 180 / math.pi > 60
        assert rep["regions"][-1]["pinned_kinks_osm_st_m"]
        assert len(srcset) > 0


def test_closure_widths_and_stations():
    with tempfile.TemporaryDirectory() as td:
        osm = osm_like()
        n = len(osm) + 1
        widths = [6.7 + (1.3 if 2 * R - 1 < y and 0 < x < 100 else 0.0) for x, y in osm] + [6.7]
        proj, osm, tr, rep, gj = built(Path(td), widths)
        f = gj["features"][0]
        coords, props = f["geometry"]["coordinates"], f["properties"]
        assert coords[0] == coords[-1] and props["closed"]
        assert props["point_count"] == len(coords) == len(props["widths_m"]) == len(props["osm_station_m"])
        s = props["osm_station_m"]
        assert all(b >= a for a, b in zip(s, s[1:])) and abs(s[-1] - s[0] - rep["length_m"]) < 50
        # the 8.0 m stretch is carried by station
        line = vp.Line.from_geojson(gj)
        wide = [w for (lo, la), w in zip(line.lonlat, props["widths_m"]) if 10 < (lo - LON0) * MLON < 90 and abs((la - LAT0) * MLAT - 2 * R) < 0.5]
        assert len(wide) > 50 and all(abs(w - 8.0) < 1e-6 for w in wide)
        assert all(6.7 - 1e-9 <= w <= 8.0 + 1e-9 for w in props["widths_m"])
        assert n == len(json.loads((proj / "data" / "centerline.osm.geojson").read_text(encoding="utf-8"))["features"][0]["geometry"]["coordinates"])
        meta = props["paint_centreline"]
        assert meta["osm_source"] == "data/centerline.osm.geojson" and meta["climb_st_m"] == [0, 470]


def test_source_file_handling_and_previous_line():
    with tempfile.TemporaryDirectory() as td:
        proj, osm, tr, rep, gj = built(Path(td))
        data = proj / "data"
        first = (data / "centerline.geojson").read_bytes()
        # same inputs again: the same bytes, nothing kept as previous
        pc.run(proj, log=lambda *a: None)
        assert (data / "centerline.geojson").read_bytes() == first
        assert not (data / "centerline.previous.geojson").exists()
        # changed traces: the replaced paint line is kept for the config remap
        tr2 = json.loads((data / "aerial" / "paint_traces.json").read_text(encoding="utf-8"))
        tr2["windows"] = tr2["windows"][1:]
        (data / "aerial" / "paint_traces.json").write_text(json.dumps(tr2), encoding="utf-8")
        pc.run(proj, log=lambda *a: None)
        assert (data / "centerline.previous.geojson").read_bytes() == first
        # a fresh gps run (a plain OSM file at data/centerline.geojson) becomes the source
        osm2 = [(x, y + (0.01 if x < 10 else 0.0)) for x, y in osm]
        fresh = write_project(Path(td) / "b", osm2)
        (fresh / "data" / "aerial" / "paint_traces.json").write_text(json.dumps(traces(osm2)), encoding="utf-8")
        raw = (fresh / "data" / "centerline.geojson").read_bytes()
        pc.run(fresh, log=lambda *a: None)
        assert (fresh / "data" / "centerline.osm.geojson").read_bytes() == raw
        assert "paint_centreline" in json.loads((fresh / "data" / "centerline.geojson").read_text(encoding="utf-8"))["features"][0]["properties"]
        # usage errors
        assert pc.main([str(Path(td) / "missing")]) == 2


def test_smoother_keeps_tolerance_and_pins():
    # a zig-zag of +-0.4 m on a straight: smoothed within its 0.5 m tolerance, pinned ends untouched
    Q = [(float(i), 0.4 * (1 if i % 2 else -1)) for i in range(60)]
    pinned = [i < 3 or i > 56 for i in range(60)]
    X, d, its = pc.smooth(Q, pinned, [0.5] * 60)
    assert all(abs(x) <= 0.5 * 1.02 + 1e-9 for x in d)
    # pinned = weight 1e8: held to a few mm even against this pathological zig-zag (sub-micron on smooth line)
    assert all(math.dist(X[i], Q[i]) < 0.005 for i in range(60) if pinned[i])
    import fit_hairpins as fh
    before = fh.signed_steps(Q)
    after = fh.signed_steps(X)
    jolt_b = max(abs(before[i] - before[i - 1]) for i in range(10, 50))
    jolt_a = max(abs(after[i] - after[i - 1]) for i in range(10, 50))
    assert jolt_a < jolt_b / 5  # the tolerance holds the line near its input, so the jolts only shrink...
    X1, d1, _ = pc.smooth(Q, pinned, [1.0] * 60)
    a1 = fh.signed_steps(X1)
    assert max(abs(a1[i] - a1[i - 1]) for i in range(10, 50)) * pc.DEG < 3.0  # ...and with room they are gone
    # the banded solver against a dense solve
    import random
    rnd = random.Random(3)
    n = 12
    diag = [10 + rnd.random() for _ in range(n)]
    off = [[rnd.random() * 0.5 for _ in range(n)] for _ in range(3)]
    rhs = [rnd.random() for _ in range(n)]
    x = pc.banded_cholesky_solve(diag, off, rhs)
    for i in range(n):
        row = diag[i] * x[i]
        for k in range(3):
            if i + k + 1 < n:
                row += off[k][i] * x[i + k + 1]
            if i - k - 1 >= 0:
                row += off[k][i - k - 1] * x[i - k - 1]
        assert abs(row - rhs[i]) < 1e-9


def test_real_lariat_is_reproducible():
    """The committed data/centerline.geojson is exactly what the tool makes from the committed OSM line and
    paint traces (byte for byte), and its report says so."""
    osm = LARIAT / "data" / "centerline.osm.geojson"
    tp = LARIAT / "data" / "aerial" / "paint_traces.json"
    cl = LARIAT / "data" / "centerline.geojson"
    if not (osm.exists() and tp.exists() and cl.exists()):
        return
    cfg = json.loads((LARIAT / "track.config.json").read_text(encoding="utf-8"))
    gj, info = pc.build(osm, json.loads(tp.read_text(encoding="utf-8")), cfg["hairpin_fit"]["climb_st_m"], log=lambda *a: None)
    committed = json.loads(cl.read_text(encoding="utf-8"))
    f, g = gj["features"][0], committed["features"][0]
    assert f["geometry"]["coordinates"] == g["geometry"]["coordinates"]
    assert f["properties"]["osm_station_m"] == g["properties"]["osm_station_m"]
    assert f["properties"]["widths_m"] == g["properties"]["widths_m"]
    meta = g["properties"]["paint_centreline"]
    assert meta["osm_source_md5"] == pc.text_md5(osm) == hashlib.md5(osm.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert meta["traces_md5"] == pc.text_md5(tp)

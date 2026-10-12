"""tools/aerial_measure.py + tools/aerial/: the aerial measurement, ported from the aerial pass's scratch scripts.

Lookout Lariat V3 (ledger 0048). Pins the pieces on synthetic data whose truth is known: UTM 13N on GRS80
(round trip, the central meridian), the robust and concentric circle fits (recovering an edge-line pair through
outliers), a synthetic road profile (yellow centre line, white edge lines, asphalt to grass: the paint and the
pavement edge found where they are), the paint confidence rules (a long consistent run high, a parked car's weak
edge, a short line and a run crossing the road low), and the NAIP fetch (every request through a verifying TLS
context; a cached window reused without the network). Plus the committed outputs: paint_traces.json's shape,
and, when a NAIP window cache is at ``$AIROSO_NAIP_CACHE``, a corner re-measured exactly as committed.
"""

from __future__ import annotations

import io
import json
import math
import os
import ssl
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
from aerial import circles, geo, naip, profile as pf, traces  # noqa: E402

LARIAT = ROOT / "tracks" / "lookout-lariat"


def test_utm_round_trip_and_central_meridian():
    E, N = geo.to_utm(-105.0, 39.7)
    assert abs(E - 500000.0) < 1e-6 and 4390000 < N < 4400000
    for lon, lat in ((-105.2446422, 39.7487629), (-104.1, 38.2), (-107.9, 41.0)):
        E, N = geo.to_utm(lon, lat)
        lo2, la2 = geo.from_utm(E, N)
        assert abs(lo2 - lon) < 1e-9 and abs(la2 - lat) < 1e-9
    # 100 m east on the grid is 100 m on the ground within the zone's scale (0.9996 at the meridian)
    a = geo.to_utm(-105.0, 39.7)
    m_lon, _ = geo.meters_per_degree(39.7)
    b = geo.to_utm(-105.0 + 100.0 / m_lon, 39.7)
    assert abs((b[0] - a[0]) - 99.96) < 0.01


def test_circle_fits_recover_an_edge_line_pair():
    c = (480000.0, 4398000.0)
    inner = [(c[0] + 7.0 * math.cos(a / 50), c[1] + 7.0 * math.sin(a / 50)) for a in range(0, 100)]
    outer = [(c[0] + 14.0 * math.cos(a / 50), c[1] + 14.0 * math.sin(a / 50)) for a in range(0, 100)]
    # noise and an apron: 8 outer points 2.5 m outside
    inner = [(x + 0.03 * math.sin(i), y - 0.03 * math.cos(i)) for i, (x, y) in enumerate(inner)]
    outer = [(x + (2.5 * math.cos(i / 50) if 40 <= i < 48 else 0.0), y + (2.5 * math.sin(i / 50) if 40 <= i < 48 else 0.0))
             for i, (x, y) in enumerate(outer)]
    f = circles.concentric(inner, outer, (c[0] + 1.0, c[1] - 1.0))
    assert abs(f["R_in"] - 7.0) < 0.02 and abs(f["R_out"] - 14.0) < 0.02 and abs(f["R_mean"] - 10.5) < 0.02
    assert math.dist((f["cx"], f["cy"]), c) < 0.02 and f["n_out"] == 92  # the apron trimmed
    r = circles.robust_circle(outer)
    assert abs(r["R"] - 14.0) < 0.02 and r["n"] == 92 and 100 < r["span_deg"] < 120
    assert circles.robust_circle(outer[:5]) is None
    ln = circles.robust_line([(x, 2.0 * x + 1.0) for x in range(20)] + [(5.0, 40.0)])
    assert abs(ln["d"][1] / ln["d"][0] - 2.0) < 1e-6 and ln["n"] == 20


class FakeWin:
    """A road running north in imagery-frame metres: grass, pavement edge at x = +-4.2, white edge lines at
    +-3.2 (0.15 m wide), the double-yellow centre line at x = 0.1, asphalt between."""

    def sample(self, E, N):
        x = E
        if abs(x) > 4.2:
            return [70.0, 95.0, 50.0, 160.0]          # grass: NIR high
        if abs(abs(x) - 3.2) < 0.12:
            return [215.0, 215.0, 212.0, 150.0]       # white paint
        if abs(x - 0.1) < 0.1:
            return [205.0, 180.0, 60.0, 120.0]        # yellow paint
        return [105.0 + 3 * math.sin(N), 104.0, 102.0, 72.0]  # asphalt: NDVI ~ -0.19


def test_paint_and_pavement_edge_on_a_synthetic_profile():
    W = FakeWin()
    pr = pf.sample_profile(W, (0.0, 0.0), (1.0, 0.0), half=10.0)
    y, prom = pf.find_yellow(pr)
    assert abs(y - 0.1) < 0.08 and prom > 20
    lo, _ = pf.find_fog(pr, y, -1)
    hi, _ = pf.find_fog(pr, y, 1)
    assert abs(lo + 3.2) < 0.1 and abs(hi - 3.2) < 0.1
    model = pf.Model(pf.lane_samples(pr, y) * 3)
    e_lo, q_lo, out_lo = pf.find_edge(pr, model, lo - 0.45, -1)
    e_hi, q_hi, out_hi = pf.find_edge(pr, model, hi + 0.45, 1)
    assert q_lo == q_hi == "ok" and abs(e_lo + 4.2) < 0.2 and abs(e_hi - 4.2) < 0.2
    assert out_hi["ndvi"] > 0.2
    # a whole trace along the road: the reference ends up on the yellow line
    ref = pf.Poly([(0.0, -20.0), (0.0, 20.0)])
    recs = pf.trace2(W, ref, 0, ref.L, None)
    ref2, nk = pf.refine_from_yellow(ref, recs)
    assert nk == len(recs) and all(abs(p[0] - 0.1) < 0.05 for p in ref2.p[5:-5])


def test_paint_confidence_rules():
    n = 30
    yel = [0.02 * math.sin(i) for i in range(n)]
    prom = [40.0] * n
    lo = [-3.2] * n
    hi = [3.2] * n
    cy, cl, ch = traces.profile_confidence(yel, prom, lo, hi)
    assert set(cy) == {"high"} and set(cl) == {"high"} and set(ch) == {"high"}
    # a parked car's edge: a run with prominence well under the window's own paint is low
    weak = list(prom)
    for i in range(10, 16):
        weak[i] = 13.0
    cy, _, _ = traces.profile_confidence(yel, weak, lo, hi)
    assert all(cy[i] == "low" for i in range(10, 16)) and cy[5] == "high"
    # no edge lines (Golden's street): medium at best
    cy, _, _ = traces.profile_confidence(yel, prom, [None] * n, [None] * n)
    assert set(cy) == {"medium"}
    # a short second line 1.4 m off inside a long run: low (consistency over +-4 m)
    odd = list(yel)
    for i in (14, 15, 16):
        odd[i] = 1.4
    cy, _, _ = traces.profile_confidence(odd, prom, lo, hi)
    assert all(cy[i] == "low" for i in (14, 15, 16))
    # a run that crosses the road (0.3 m sideways per metre): low however consistent
    drift = [0.15 * i for i in range(n)]
    cy, _, _ = traces.profile_confidence(drift, prom, [d - 3.2 for d in drift], [d + 3.2 for d in drift])
    assert all(c == "low" for c in cy[8:-8])
    # isolated detections (runs of 2) are low
    iso = [0.0 if i % 3 else None for i in range(n)]
    cy, _, _ = traces.profile_confidence(iso, prom, lo, hi)
    assert set(c for c in cy if c) == {"low"}


def _png_bytes(w, h, rgb):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), rgb).save(buf, format="PNG")
    return buf.getvalue()


def test_naip_fetch_is_tls_verified_and_cached():
    calls = []

    class Resp:
        def __init__(self, data, ctype):
            self.data, self.headers = data, {"Content-Type": ctype}

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake(req, context=None, timeout=None):
        url = req.full_url
        calls.append((url, context))
        if "/query?" in url:
            return Resp(json.dumps({"features": [{"attributes": {"Name": "m_test", "Year": 2019}}]}).encode(), "application/json")
        return Resp(_png_bytes(40, 40, (100, 100, 100)), "image/png")
    real = naip.urllib.request.urlopen
    naip.urllib.request.urlopen = fake
    try:
        with tempfile.TemporaryDirectory() as td:
            m = naip.window(Path(td), "T1", 480000.0, 4398000.0, 6.0)
            assert m["size"] == [40, 40] and m["bbox_utm13n"] == [479994.0, 4397994.0, 480006.0, 4398006.0]
            assert len(calls) == 3 and m["catalog"][0]["Name"] == "m_test"
            for url, ctx in calls:
                assert url.startswith("https://imagery.nationalmap.gov/")
                assert ctx is None or (ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname)
            assert "bandIds=0%2C1%2C2" in calls[0][0] and "bandIds=3%2C0%2C1" in calls[1][0]
            assert "bboxSR=26913" in calls[0][0] and "imageSR=26913" in calls[0][0]
            # cached: no network at all, and the pixels read back
            calls.clear()
            m2 = naip.window(Path(td), "T1", 480000.0, 4398000.0, 6.0, fetch=False)
            assert not calls and m2["files"]["rgb"]["path"] == "T1_rgb.png"
            W = naip.Win(m2)
            assert W.sample(480000.0, 4398000.0)[:3] == [100.0, 100.0, 100.0]
            # a different bbox without fetching is refused
            try:
                naip.window(Path(td), "T1", 480001.0, 4398000.0, 6.0, fetch=False)
                raise AssertionError("fetched without permission")
            except SystemExit as e:
                assert "not in the cache" in str(e)
    finally:
        naip.urllib.request.urlopen = real


def test_committed_paint_traces_shape():
    p = LARIAT / "data" / "aerial" / "paint_traces.json"
    if not p.exists():
        return
    t = json.loads(p.read_text(encoding="utf-8"))
    assert t["frame"]["lap_centerline"] == "data/centerline.osm.geojson" and len(t["frame"]["m_per_deg"]) == 2
    assert t["registration"]["osm_minus_imagery_EN_m"] == [-1.2, 0.56]
    ids = {w["id"] for w in t["windows"]}
    assert {"C1", "C4", "C10", "C11", "W03250", "C12_in", "C13_out"} <= ids
    for w in t["windows"]:
        for key in ("yellow", "edge_left", "edge_right"):
            ln = w[key]
            n = len(ln["xz_m"])
            assert all(len(ln[k]) == n for k in ("lap_st_m", "heading_deg", "confidence", "source"))
            assert set(ln["confidence"]) <= {"high", "medium", "low"}
        if w.get("reference"):
            assert len(w["reference"]["supported"]) == len(w["reference"]["xz_m"])
    assert sum(t["confidence_counts_yellow"].get(k, 0) for k in ("high", "medium")) > 5000
    w9 = next(w for w in t["windows"] if w["id"] == "W06900")
    assert w9["usable"] is False and set(w9["yellow"]["confidence"]) <= {"low"}
    assert next(w for w in t["windows"] if w["id"] == "C4")["core"]["yellow_circle"]["good"]


def test_reproduces_the_committed_corner_when_the_window_cache_is_here():
    """Opt-in (the raw NAIP windows are never in the repo): with AIROSO_NAIP_CACHE pointing at a cache that
    holds C1's window, C1 is re-measured and must equal the committed record."""
    cache = os.environ.get("AIROSO_NAIP_CACHE")
    if not cache or not (Path(cache) / "C1.json").exists():
        return
    from aerial import corners, report
    from aerial.context import Ctx
    ctx = Ctx(LARIAT, cache, fetch=False)
    am = json.loads((LARIAT / "data" / "aerial" / "aerial_measurements.json").read_text(encoding="utf-8"))
    ctx.V = tuple(am["source"]["registration_vs_osm"]["osm_minus_imagery_EN_m"])
    tr = corners.trace_corner(ctx, "C1")
    core = corners.measure(ctx, "C1", tr)
    ridge = corners.ridge_for(ctx, "C1", core)
    rec, lab, final = report.hairpin(ctx, "C1", core, ridge)
    committed = next(c for c in am["corners"] if c["id"] == "C1")
    for k in ("radius_m", "radius_method", "uncertainty_m", "confidence", "centre", "estimates", "apex_cross_section",
              "osm_vs_paint_core", "radius_profile_yellow_10m", "notes"):
        assert json.loads(json.dumps(rec[k])) == committed[k], k

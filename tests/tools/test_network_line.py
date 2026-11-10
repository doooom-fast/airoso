"""tools/network_line.py (ledger 0080): a network draft's reference line becomes an LM port's line with its OWN 3DEP,
uncapped, and its lon / lat read from the draft's network.geojson (no inverse projection)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))


def _draft(tmp: Path) -> Path:
    d = tmp / "draft" / "data"
    d.mkdir(parents=True)
    # two edges, 5 m apart, a 10 % climb in the raw 3DEP the draft capped to 5 %
    e0 = [(i * 5.0, 0.0) for i in range(11)]          # 0..50 m
    e1 = [(50.0 + i * 5.0, 0.0) for i in range(11)]   # 50..100 m
    raw0 = [10.0 + 0.5 * i for i in range(11)]
    raw1 = [15.0 + 0.5 * i for i in range(11)]
    pts, sbv, ys = [], [], []
    for k, (x, z) in enumerate(e0):
        pts.append([x, 0.25 * k - 0.0, z]); sbv.append([0, k])
    for k, (x, z) in enumerate(e1[1:], start=1):
        pts.append([x, 2.5 + 0.25 * k, z]); sbv.append([1, k])
    origin = {"lon": -117.0, "lat": 32.0, "elev_m": 10.0}
    (d / "centerline.local.json").write_text(json.dumps({"origin": origin, "points_xyz_m": pts,
                                                          "widths_m": [16.0] * len(pts), "source_by_vertex": sbv}))
    (d / "network.elevation.json").write_text(json.dumps([{"id": 0, "z_raw_m": raw0}, {"id": 1, "z_raw_m": raw1}]))
    feats = [{"type": "Feature", "properties": {"id": i},
              "geometry": {"type": "LineString", "coordinates": [[-117.0 + 1e-5 * (i * 10 + k), 32.0] for k in range(11)]}}
             for i in (0, 1)]
    (d / "network.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    (d / "network.reference.json").write_text("{}")
    (d / "heightfield.npy").write_bytes(b"x")
    (d / "heightfield.meta.json").write_text("{}")
    return d.parent


def test_the_line_takes_its_raw_3dep_uncapped_and_the_draft_lon_lat():
    import network_line as N
    tmp = Path(tempfile.mkdtemp(prefix="netline_"))
    try:
        rep = N.build(_draft(tmp), tmp / "out")
        loc = json.loads((tmp / "out" / "centerline.local.json").read_text())
        ys = [p[1] for p in loc["points_xyz_m"]]
        # the raw climb is 10 %: away from the ends' smoothing the line keeps it (the draft's 5 % does not bind)
        assert abs((ys[12] - ys[8]) / 20.0 - 0.10) < 1e-6
        assert rep["max_grade_10m_pct"]["measured_uncapped"] > rep["max_grade_10m_pct"]["draft_capped"]
        assert loc["loop"] is False and len(ys) == 21
        gj = json.loads((tmp / "out" / "centerline.geojson").read_text())
        c = gj["features"][0]["geometry"]["coordinates"]
        assert len(c) == 21 and abs(c[11][0] - (-117.0 + 1e-5 * 11)) < 1e-9     # edge 1, vertex 1
        assert gj["features"][0]["properties"]["length_m"] == 100.0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

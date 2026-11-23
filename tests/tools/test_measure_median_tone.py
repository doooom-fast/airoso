"""tools/measure_median_tone.py: the island colour off a NAIP z18 mosaic, and the terracotta_paver pair it was written
for. Pins the frame maths to tools/naip_edge.py's Naip.px, the inset / canopy / shadow masks on a synthetic mosaic,
and the committed pair as downloaded (CC0 record, power of two, the md5s the licence note records).
Plain ``test_*`` functions with tempfile.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import measure_median_tone as mt  # noqa: E402
import naip_edge  # noqa: E402

ORIGIN = {"lon": -117.04666413020487, "lat": 32.78835571285328, "elev_m": 100.8}
ASPHALT, TERRACOTTA, GREEN, DARK = (120, 122, 118), (150, 128, 116), (60, 80, 60), (70, 66, 62)


def _mosaic(d: Path):
    """A 768 px z18 mosaic whose middle tile holds the origin: asphalt with a 24 x 5 m terracotta island round the
    origin, one green crown and one dark (shadow) blob on the island."""
    tx = (ORIGIN["lon"] + 180.0) / 360.0 * 2 ** 18
    lat = math.radians(ORIGIN["lat"])
    ty = (1.0 - math.log(math.tan(lat) + 1.0 / math.cos(lat)) / math.pi) / 2.0 * 2 ** 18
    g = {"z": 18, "x0": int(tx) - 1, "y0": int(ty) - 1, "w": 768, "h": 768}
    (d / "m.georef.json").write_text(json.dumps(g), encoding="utf-8")
    mos = mt.Mosaic.__new__(mt.Mosaic)
    mos.z, mos.x0, mos.y0 = 18, g["x0"], g["y0"]
    mos.lat0, mos.lon0 = ORIGIN["lat"], ORIGIN["lon"]
    mos.m_lon, mos.m_lat = mt._meters_per_degree(mos.lat0)
    a = np.zeros((768, 768, 3), np.uint8)
    a[:] = ASPHALT
    ring = [(-12.0, -2.5), (12.0, -2.5), (12.0, 2.5), (-12.0, 2.5)]
    U, V = np.meshgrid(np.arange(768) + 0.5, np.arange(768) + 0.5)
    # pixel centres back to metres, by inverting px() along each axis (north-up, no rotation)
    u0, v0 = mos.px(0.0, 0.0)
    du, _ = mos.px(1.0, 0.0)
    _, dv = mos.px(0.0, 1.0)
    xm, zm = (U - u0) / (du - u0), (V - v0) / (dv - v0)
    a[(np.abs(xm) <= 12.6) & (np.abs(zm) <= 3.1)] = TERRACOTTA
    green = (np.hypot(xm - 6.0, zm) <= 1.2)
    dark = (np.hypot(xm + 6.0, zm) <= 1.2)
    a[green], a[dark] = GREEN, DARK
    Image.fromarray(a).save(d / "m.png")
    med = {"id": "MDX", "piece": "C", "type": "terracotta", "s_from": 0.0, "s_to": 24.0, "width_m": [5.0, 5.0],
           "polygon_xz": [list(p) for p in ring]}
    return d / "m.png", d / "m.georef.json", med, int(green.sum()), int(dark.sum())


def test_px_is_naip_edges_frame():
    with tempfile.TemporaryDirectory() as t:
        img, geo, _, _, _ = _mosaic(Path(t))
        mos = mt.Mosaic(img, geo, ORIGIN)
        ne = naip_edge.Naip.__new__(naip_edge.Naip)
        ne.z, ne.x0, ne.y0 = mos.z, mos.x0, mos.y0
        ne.lat0, ne.lon0 = ORIGIN["lat"], ORIGIN["lon"]
        ne.m_lon, ne.m_lat = naip_edge._mpd(ne.lat0)
        E, N = np.array([-3010.7, 0.0, 512.3]), np.array([2048.5, 0.0, -77.1])
        for a, b in zip(mos.px(E, N), ne.px(E, N)):
            assert np.allclose(a, b, atol=1e-9)


def test_masks_keep_only_the_lit_terracotta():
    with tempfile.TemporaryDirectory() as t:
        img, geo, med, n_green, n_dark = _mosaic(Path(t))
        r = mt.measure_island(mt.Mosaic(img, geo, ORIGIN), med)
        assert r["px_in_inset"] < r["px_in_ring"]                          # the 0.5 m inset drops the curb row
        assert r["px_canopy"] >= n_green and r["px_shadow"] >= n_dark       # each blob taken, grown by a pixel
        assert r["px_kept"] + r["px_canopy"] + r["px_shadow"] == r["px_in_inset"]
        for q in ("mean", "median", "p10", "p90"):
            assert r["kept"][q] == [float(v) for v in TERRACOTTA], (q, r["kept"][q])   # no asphalt, crown or shadow


def test_terracotta_paver_pair_is_recorded_as_downloaded():
    lic = json.loads((ROOT / "assets" / "licenses.json").read_text(encoding="utf-8"))
    rows = [a for a in lic["bundled_assets"] if "terracotta_paver_diffuse.jpg" in a.get("files", [])]
    assert len(rows) == 1
    row = rows[0]
    assert row["license"] == "CC0-1.0" and row["url"] == "https://ambientcg.com/view?id=PavingStones135"
    for f in row["files"]:
        p = ROOT / "assets" / "textures" / f
        im = Image.open(p)
        assert im.size == (2048, 2048) and im.mode == "RGB"
        assert hashlib.md5(p.read_bytes()).hexdigest() in row["_note"], f     # byte for byte as served
    assert "terracotta_paver" in (ROOT / "assets" / "textures" / "SOURCES.txt").read_text(encoding="utf-8")

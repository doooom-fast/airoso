"""The engine edits of ledger 0048 "P2 fixed" (2026-10-12) are opt-in per track, and do what they say.

- scripts/geometry/projection.py writes centerline.local.json at 2 decimals unless ``projection.decimals`` says
  otherwise (the Lariat: 3; cm heights on 1 m spacing quantise grades to +-1 %-point = drive_test kinks);
- scripts/elevation/road_profile.py's station filters weigh each sample by the part of its cell inside the window:
  identical on uniform spacing (heightfield), and smooth where 1 m spacing meets 3 m (the -16 % cap segment between
  -4 % ones that drove severe steps across all six wheel paths at local st 11,577.8);
- scripts/ac/build_kn5_loop.py's terrain conform reads ``prep.terrain_conform`` and defaults to its constants
  (band 3.0 m, feather 6.0 m, subdivide on), so every other track preps exactly as before.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.elevation import road_profile as rp
from scripts.geometry import projection

ROOT = Path(__file__).resolve().parents[2]


def _proj(decimals=None):
    p = Path(tempfile.mkdtemp())
    (p / "data").mkdir()
    cfg = {"name": "t", "slug": "t", "loop": False, "default_width_m": 7.0, "true_north_rotation_deg": 0.0,
           "location": {"lat": 39.7, "lon": -105.2, "timezone": "America/Denver"}, "source": {"type": "osm"},
           "origin": "centroid", "surfaces": {"road": "1ROAD"}, "layouts": [], "lighting": {}}
    if decimals is not None:
        cfg["projection"] = {"decimals": decimals}
    (p / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    coords = [[-105.2 + i * 1e-5, 39.7] for i in range(50)]
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"kind": "full", "widths_m": [7.0] * 50},
                                                     "geometry": {"type": "LineString", "coordinates": coords}}]}
    (p / "data" / "centerline.geojson").write_text(json.dumps(gj), encoding="utf-8")
    (p / "data" / "centerline.elevation.json").write_text(json.dumps({"z_smooth_m": [1800.0 + 0.0123 * i for i in range(50)]}),
                                                          encoding="utf-8")
    return p


def test_projection_decimals_are_opt_in():
    a = _proj()
    projection.build(a)
    pa = json.loads((a / "data" / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    assert all(round(v, 2) == v for p in pa for v in p)                     # cm, as every other track
    b = _proj(3)
    projection.build(b)
    pb = json.loads((b / "data" / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    assert any(round(p[1], 2) != p[1] for p in pb) and all(round(v, 3) == v for p in pb for v in p)


def test_mixed_spacing_profile_has_no_cap_staircase():
    # an 8 % ramp sampled at 1 m then 3 m: every segment of the filtered profile stays within 1.5 %-points of 8 %
    # (the centre-counted windows of the integrated build: 7.8 %-points off; the overlap-weighted ones: 0.89)
    st = [float(i) for i in range(0, 200)] + [200.0 + 3.0 * i for i in range(0, 70)]
    z = [0.08 * s for s in st]
    out = rp.snap_to_ground_stations(z, st, grade_cap_pct=16.0, closed=False)
    g = [(out[i + 1] - out[i]) / (st[i + 1] - st[i]) * 100.0 for i in range(len(st) - 1) if 40.0 <= st[i] <= 360.0]
    assert max(abs(x - 8.0) for x in g) < 1.5, max(abs(x - 8.0) for x in g)
    # and a 9 % descent with 1 m 3DEP noise, sampled 1 m then 3 m (the lower-Paradise case): no segment at the cap
    # (the integrated build's filters: 16.0 %, at the cap; these: 9.87 %)
    import math
    st2 = [float(i) for i in range(0, 120)] + [120.0 + 3.0 * i for i in range(0, 40)]
    z2 = [-0.09 * s + 0.04 * math.sin(s * 1.7) for s in st2]
    out2 = rp.snap_to_ground_stations(z2, st2, grade_cap_pct=16.0, closed=False)
    g2 = [abs(out2[i + 1] - out2[i]) / (st2[i + 1] - st2[i]) * 100.0 for i in range(len(st2) - 1)]
    assert max(g2) < 12.0, max(g2)


def test_prep_terrain_conform_is_per_track_with_the_old_constants_as_defaults():
    src = (ROOT / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")
    for frag in ('band_m = float(_tc.get("band_m", BAND_M))', 'feather_m = float(_tc.get("feather_m", FEATHER_M))',
                 'subdivide = bool(_tc.get("subdivide", True))', "for _round in range(4 if subdivide else 0):",
                 "if d_own <= band_m:", "elif d_own < band_m + feather_m:"):
        assert frag in src, frag
    assert "BAND_M = 3.0" in src and "FEATHER_M = 6.0" in src
    # only the Lariat sets it
    users = [p.parent.name for p in (ROOT / "tracks").glob("*/track.config.json")
             if "terrain_conform" in (json.loads(p.read_text(encoding="utf-8")).get("prep") or {})]
    assert users == ["lookout-lariat"], users

"""scripts-v021/blender/build_loop_blend.build_buildings — the pure part of the buildings pass (ledger 0054 P4 integration
fix round): footprints projected with the roads' own WGS84 series, and no footprint corner on the built walk. bpy is
stubbed; heights do not matter to the choice (terr = 0); _extrude_footprint is replaced by a recorder."""
from __future__ import annotations

import importlib.util
import math
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACK = ROOT / "tracks" / "san-diego-lake-murray"


def _load():
    sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    sys.modules.setdefault("bmesh", types.ModuleType("bmesh"))
    if "scripts" not in sys.modules or not getattr(sys.modules["scripts"], "__file__", "").startswith(str(TRACK)):
        spec = importlib.util.spec_from_file_location("scripts", TRACK / "scripts-v021" / "__init__.py",
                                                      submodule_search_locations=[str(TRACK / "scripts-v021")])
        m = importlib.util.module_from_spec(spec)
        saved = sys.modules.get("scripts")
        sys.modules["scripts"] = m
        spec.loader.exec_module(m)
    else:
        saved = None
    spec = importlib.util.spec_from_file_location("blb_under_test", TRACK / "scripts-v021" / "blender" / "build_loop_blend.py")
    blb = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(blb)
    except Exception:
        pass            # the module's tail reads the project at import; the functions above it are bound
    if saved is not None:
        sys.modules["scripts"] = saved
    return blb


def test_footprints_use_the_roads_own_projection():
    blb = _load()
    spec = importlib.util.spec_from_file_location("proj_v021", TRACK / "scripts-v021" / "geometry" / "projection.py")
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    for lat in (32.79, 39.5):
        assert blb._meters_per_degree(lat) == pm._meters_per_degree(lat)
    m_lon, m_lat = blb._meters_per_degree(32.788)
    assert 110895 < m_lat < 110905 and 93670 < m_lon < 93690           # not 110574 / 93575 (0.3 % / 0.1 % short)


def _run(blb, cache, lat0=32.788, lon0=-117.0467, half_w=5.0):
    m_lon, m_lat = blb._meters_per_degree(lat0)
    rec = []
    blb._extrude_footprint = lambda mesh, foot, base, h: rec.append(foot)
    # a straight road along x at z = 0, 10 m wide (half 5 m), 400 m long
    centerline = [(float(x), 0.0, 0.0) for x in range(0, 401, 5)]
    widths = [2 * half_w] * len(centerline)

    def geom(x0, z0, w, d):
        return [(lon0 + x / m_lon, lat0 + z / m_lat) for x, z in ((x0, z0), (x0 + w, z0), (x0 + w, z0 + d), (x0, z0 + d), (x0, z0))]
    cache = [{"building": "house", "geom": geom(*g)} for g in cache]
    blb.build_buildings(centerline, widths, None, cache, lon0, lat0, terr=lambda x, z: 0.0)
    return rec


def test_no_footprint_corner_on_the_built_walk():
    blb = _load()
    clear = blb.BUILDING_CORNER_CLEAR_M
    assert 3.0 <= clear <= 3.2                                      # the curb profile's width: 0.08 + 1.8 + 1.2
    rec = _run(blb, [
        (100.0, 5.0 + 2.0, 12.0, 10.0),      # nearest corner 2 m off the pavement edge: ON the walk -> dropped
        (150.0, 5.0 + 4.0, 12.0, 10.0),      # nearest corner 4 m off, centroid 9 m off (>= 5 m): kept
        (200.0, 5.0 + 1.0, 30.0, 10.0),      # a 30 m house: centroid 6 m off would pass the old rule, its corner 1 m: dropped
        (244.0, 5.0 + 3.5, 12.0, 2.5),       # corner 3.5 m clear but centroid 4.75 m off: the crowding rule still drops it
    ])
    xs = sorted(round(min(p[0] for p in f)) for f in rec)
    assert xs == [150], xs
    rec2 = _run(blb, [(100.0, 5.0 + 2.0, 12.0, 10.0)], half_w=2.0)   # a narrower road: the same corner is 5 m clear
    assert len(rec2) == 1

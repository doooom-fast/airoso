"""A synthetic underlay project (no network, no Blender): a closed 'switchback' loop whose two long legs run 25 m
apart on the map and up to ~12 m apart in height, so every refs pass has something to find; a small 40 m
heightfield; a config carrying the Lariat's switches (road_profile.verge_m, drive1_variants, hairpin_fit.corners,
race.corridor.boxes, terrain.stacked_legs). Shared by test_underlay_draft.py and tests/tools/test_underlay_blend.py
(not a test module itself: the runner only loads test_*.py)."""

from __future__ import annotations

import json
import math
from pathlib import Path

LON0, LAT0, ELEV0 = -105.2, 39.73, 1800.0


def loop_points(spacing=2.0, leg=400.0, gap=25.0):
    """anticlockwise: east along z=0, a semicircle up to z=gap, west along z=gap, a semicircle back. Climbs 0 -> 6 m
    over the first leg and 6 -> 12 m round the east turn, descends 12 -> 6 m over the second leg (6 m above the
    first, 25 m away on the map: a stacked pair at every station) and 6 -> 0 m round the west turn."""
    r = gap / 2.0
    pts = []
    n = int(leg / spacing)
    for k in range(n):                                       # leg 1, east, climbing 0 -> 6
        x = -leg / 2 + k * spacing
        pts.append((x, 6.0 * k / n, 0.0))
    m = int(math.pi * r / spacing)
    for k in range(m):                                       # east turn
        a = -math.pi / 2 + math.pi * k / m
        pts.append((leg / 2 + r * math.cos(a), 6.0 + 6.0 * k / m, r + r * math.sin(a)))
    for k in range(n):                                       # leg 2, west, descending 12 -> 6 (6 m over leg 1)
        x = leg / 2 - k * spacing
        pts.append((x, 12.0 - 6.0 * k / n, gap))
    for k in range(m):                                       # west turn
        a = math.pi / 2 + math.pi * k / m
        pts.append((-leg / 2 + r * math.cos(a), 6.0 - 6.0 * k / m, r + r * math.sin(a)))
    pts.append(pts[0])                                       # closed: last == first
    return [(round(x, 4), round(y, 4), round(z, 4)) for x, y, z in pts]


def write_project(root: Path, *, verge_m=0.4, crossfall=None, with_heightfield=True) -> Path:
    from scripts.elevation.heightfield import write_npy
    proj = Path(root)
    (proj / "data").mkdir(parents=True, exist_ok=True)
    pts = loop_points()
    widths = [6.5] * len(pts)
    (proj / "data" / "centerline.local.json").write_text(json.dumps({
        "frame": "ENU local meters (X=east, Y=up, Z=north)",
        "origin": {"lon": LON0, "lat": LAT0, "elev_m": ELEV0},
        "points_xyz_m": [list(p) for p in pts], "widths_m": widths}), encoding="utf-8")
    n = len(pts) - 1
    cfg = {
        "slug": "synthetic_underlay", "loop": True, "mirror_x": False,
        "road_profile": {"verge_m": verge_m, "crossfall": {"status": "estimated", "banking": False}},
        "drive1_variants": {"a_real_edge": {"road_profile.verge_m": 0.4, "install_folder": "x_v3"},
                            "b_verge": {"road_profile.verge_m": 1.25, "install_folder": "x_v3_verge"}},
        "hairpin_fit": {"corners": [{"id": "C1", "name": "east turn", "st_m": 420.0, "radius_m": 12.5},
                                    {"id": "C2", "name": "west turn", "st_m": 860.0, "radius_m": 12.5}]},
        "race": {"corridor": {"boxes": [{"corner": "C9", "name": "a box", "apex": 100, "i": 90, "j": 110}]}},
        "terrain": {"stacked_legs": {"pair_max_plan_m": 40, "pair_min_along_m": 150}},
        "layouts": [{"id": "street_full"}],
    }
    (proj / "track.config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    if crossfall is not None:
        (proj / "data" / "crossfall.json").write_text(json.dumps(crossfall), encoding="utf-8")
    if with_heightfield:
        sp = 40.0
        mlat = 111_000.0
        mlon = 111_000.0 * math.cos(math.radians(LAT0))
        half = 400.0
        s, w = LAT0 - half / mlat, LON0 - half / mlon
        nlat, elon = LAT0 + half / mlat, LON0 + half / mlon
        gy, gx = sp / mlat, sp / mlon
        ny, nx = int((nlat - s) / gy) + 1, int((elon - w) / gx) + 1
        # a hillside rising 0.4 m per metre north (row 0 = north): the first leg (north 0) rides a fill, the
        # second (north 25, 6-12 m) is cut into the slope at its west end, so both the pin and the edge clamp bite
        grid = [[ELEV0 - 1.0 + 0.4 * (half - j * sp) + 0.01 * i for i in range(nx)] for j in range(ny)]
        write_npy(proj / "data" / "heightfield.npy", grid)
        (proj / "data" / "heightfield.meta.json").write_text(json.dumps(
            {"bbox_swne": [s, w, nlat, elon], "nx": nx, "ny": ny, "spacing_m": sp, "margin_m": 150.0,
             "row0": "north"}), encoding="utf-8")
    assert n > 0
    return proj

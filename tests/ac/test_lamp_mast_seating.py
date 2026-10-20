"""kn5_ground_check's lamp seating: a mast arm is not a foot, however far it reaches (ledger 0054 P3 repair round 3).

The seating lens found FEET as the lowest vertex of every 1.5 m column with no lower column within ~3.5 m — so a
2026-10 LED standard (a 3.66 m arm, the lens 4.04 m from the pole, two arms back to back) left its outer arm columns,
11 m up, as feet with nothing in their 4 m support window: 38.4 % of Lake Murray's lampposts read "no-ground" and the
gate failed on a mesh whose every pole stands in the earth. Mast buckets now take their feet per object (the chain of
occupied columns): long-armed lamps on the ground PASS, the same lamps lifted 1.5 m off it still FAIL.
Plain ``test_*`` for tests/run_tests.py.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.geometry.test_drive_test import _grass_plane, _write_obj

from scripts.ac.kn5_ground_check import MAST_BUCKETS, check
from scripts.ac.kn5_write import build
from scripts.geometry import ribbon

N_M = 200


def _lamps(xs_zs, foot_y, arm=4.3, top=11.0):
    """a pole (a thin box from foot_y to top) with two arms reaching +-arm in x at the top, per (x, z)"""
    verts, tris = [], []

    def box(x0, x1, y0, y1, z0, z1):
        b = len(verts)
        for y in (y0, y1):
            for z in (z0, z1):
                for x in (x0, x1):
                    verts.append((x, y, z))
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            a, b2, c, d = (b + k for k in q)
            tris.extend([(a, b2, c), (a, c, d)])

    for x, z in xs_zs:
        box(x - 0.12, x + 0.12, foot_y, top, z - 0.12, z + 0.12)
        for k in range(1, 10):                         # arm segments every ~0.5 m, both ways
            for s in (1, -1):
                a0, a1 = s * arm * (k - 1) / 9.0, s * arm * k / 9.0
                box(x + min(a0, a1), x + max(a0, a1), top - 0.3, top, z - 0.05, z + 0.05)
    return {"vertices": verts, "tris": tris, "uvs": [(0.0, 0.0)] * len(verts)}


def _project(foot_y):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, 5)]
    widths = [8.0] * len(cl)
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    spots = [(10.0, 20.0 + 8.0 * k) for k in range(20)]
    _write_obj(d / "data" / "track.obj", [("1ROAD_main", ribbon.road_ribbon(cl, widths)), ("1GRASS", _grass_plane()),
                                          ("LIGHTPOST_0", _lamps(spots, foot_y))])
    return d


def test_long_armed_lamps_standing_in_the_earth_read_seated():
    d = _project(foot_y=-2.5)                         # the LED standard's own 2.5 m footing under the datum
    build(d)
    st = {}
    r = __import__("scripts.ac.kn5_ground_check", fromlist=["check"]).check(d, stats=st)
    lp = st["seating"]["lampposts"]
    assert lp["objects"] == 20 and lp["no_ground_pct"] == 0.0, lp
    assert not any("lampposts" in why for why in r["reasons"]), r["reasons"]


def test_the_same_lamps_hovering_still_fail():
    d = _project(foot_y=1.5)                          # every pole 1.5 m over the grass plane
    build(d)
    r = check(d)
    assert r["fail"] is True and any("lampposts" in why for why in r["reasons"]), r["reasons"]


def test_mast_buckets_are_the_masts():
    assert MAST_BUCKETS == ("LIGHTPOST", "GANTRY")

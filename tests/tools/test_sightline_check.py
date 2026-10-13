"""tools/sightline_check.py (ledger 0046 criterion 2) — read-only on a gate OBJ: a cone 'summit' 1.6 km off a road
reads its true elevation angle and passes; a ridge standing in front of it fails the 'nothing nearer stands
higher' test; a bearing ray reports where the built ground runs out; the far ring counts as terrain, the road
gives the eye height."""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import sightline_check as sc  # noqa: E402


def _grid(groups_out, name, x0, x1, z0, z1, step, h):
    vs, fs = [], []
    nx, nz = int(round((x1 - x0) / step)), int(round((z1 - z0) / step))
    for j in range(nz + 1):
        for i in range(nx + 1):
            x, z = x0 + i * step, z0 + j * step
            vs.append((x, h(x, z), z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            fs += [(a, a + 1, a + nx + 2), (a, a + nx + 2, a + nx + 1)]
    groups_out.append((name, vs, fs))


def _obj(groups):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    lines, base = [], 1
    for name, vs, fs in groups:
        lines.append(f"o {name}")
        lines += [f"v {x:.3f} {y:.3f} {z:.3f}" for x, y, z in vs]
        lines += [f"f {a + base} {b + base} {c + base}" for a, b, c in fs]
        base += len(vs)
    (d / "data" / "track.obj").write_text("\n".join(lines) + "\n")
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], "widths_m": [10, 10],
         "origin": {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}}))
    return d


def _peak(x, z, top=270.0, cx=0.0, cz=1650.0, r=900.0):
    return max(0.0, top * (1.0 - math.hypot(x - cx, z - cz) / r))


def test_summit_angle_and_the_blocker():
    g = []
    _grid(g, "1ROAD_road", -20, 20, -20, 20, 10, lambda x, z: 0.0)
    _grid(g, "1GRASS_0", -100, 100, -100, 300, 20, lambda x, z: -0.5)
    _grid(g, "GRASS_FAR_0", -1000, 1000, 300, 2600, 25, _peak)        # the mountain is in the far ring
    d = _obj(g)
    rays = [{"name": "crest", "from": (0.0, 0.0), "to": (0.0, 1650.0), "min_deg": 9.0}]
    rep, bad = sc.run(d, rays)
    real = math.degrees(math.atan2(270.0 - 1.2, 1650.0))
    assert bad == 0 and abs(rep[0]["target_deg"] - real) < 0.05 and rep[0]["eye_abs_m"] == 101.2, rep[0]
    assert rep[0]["max_intermediate_deg"] < rep[0]["target_deg"]
    # a 60 m ridge 200 m out (11 deg) stands in front: the summit no longer clears every intermediate angle
    g2 = list(g)
    _grid(g2, "1GRASS_1", -50, 50, 180, 220, 10, lambda x, z: 60.0 if abs(z - 200) < 15 else 0.0)
    rep2, bad2 = sc.run(_obj(g2), [dict(rays[0])])
    assert bad2 == 1 and rep2[0]["max_intermediate_deg"] > rep2[0]["target_deg"] and rep2[0]["pass"] is False
    # a station the world hides the summit from (v1640, ledger 0046 2026-10-13): "hidden" passes only when the build
    # hides it too — the ridge in front passes, the open view fails
    rep3, bad3 = sc.run(_obj(g2), [dict(rays[0], hidden=True)])
    assert bad3 == 0 and rep3[0]["pass"] and rep3[0]["expect"] == "hidden"
    rep4, bad4 = sc.run(d, [dict(rays[0], hidden=True)])
    assert bad4 == 1 and rep4[0]["pass"] is False


def test_bearing_reports_where_the_ground_ends_and_ignores_other_groups():
    g = []
    _grid(g, "1ROAD_road", -20, 20, -20, 20, 10, lambda x, z: 0.0)
    _grid(g, "GRASS_FAR_0", -200, 200, -3000, 0, 50, lambda x, z: -10.0)
    _grid(g, "HOUSE", -200, 200, -5000, -3000, 50, lambda x, z: 30.0)  # not terrain: never read as ground
    rep, bad = sc.run(_obj(g), [{"name": "south", "from": (0.0, 0.0), "bearing": 180.0, "range": 5000.0}])
    assert bad == 0
    r = rep[0]
    assert 2990.0 <= r["built_to_m"] <= 3000.0 and 3000.0 <= r["first_gap_m"] <= 3010.0, r
    assert r["max_ground_abs_m"] == 90.0


def test_the_target_is_the_summit_top_and_the_nominal_point_is_reported():
    """ledger 0046 fix round: the nominal (1380, 2700) is ~14 m off the real top. The ray is aimed at the highest built
    vertex within the summit cone (criterion 1's 60 m); the shoulder inside the cone is reported, not judged, and the
    nominal point's own angle is printed beside the verdict"""
    g = []
    _grid(g, "1ROAD_road", -20, 20, -20, 20, 10, lambda x, z: 0.0)
    _grid(g, "GRASS_FAR_0", -1000, 1000, 300, 2600, 25, lambda x, z: _peak(x, z, cx=25.0, cz=1675.0))
    rep, bad = sc.run(_obj(g), [{"name": "crest", "from": (0.0, 0.0), "to": (0.0, 1650.0), "min_deg": 9.0}])
    r = rep[0]
    assert bad == 0 and r["pass"] and r["nominal"] == [0.0, 1650.0], r
    assert abs(r["top_abs_m"] - 370.0) < 1e-6 and abs(r["target_dist_m"] - math.hypot(25.0, 1675.0)) < 0.1
    assert r["nominal_deg"] < r["target_deg"], "the nominal point sits on the flank, below the top"
    assert r["max_shoulder_deg"] is not None and r["max_intermediate_deg"] < r["target_deg"]

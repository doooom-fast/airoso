"""Ledger 0069: a one-quad ribbon row twists on a curve that descends, banked or not.

Milford's s 1,000 left-hander: the inside edge's rows bunch towards the turning centre while every row still drops the
centreline's full fall, so the quad's diagonal splits a near-vertical sliver off the inside and its drop crosses the wheel
paths as a step (drive_test: 26 severe steps, up to 22 cm, all at the centre pair). Lateral columns put a vertex row on the
centreline and the step goes. build_mesh used to honour road_profile.ribbon_cols on a banked road only."""
import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.geometry import ribbon  # noqa: E402

spec = importlib.util.spec_from_file_location("_bm_0069", ROOT / "scripts" / "geometry" / "build_mesh.py")
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)

# a 120 deg left-hander of centreline radius 12 m, 3 m rows, 15 % descent, 20 m wide (the inside edge 2 m off the centre),
# unbanked, with 30 m straights either side
R, ROW, GRADE, WIDTH = 12.0, 3.0, 0.15, 20.0


def _corner():
    pts, s = [], 0.0
    for i in range(10):                              # straight in, heading +z
        pts.append((R, -GRADE * s, -30.0 + ROW * i)); s += ROW
    n_arc = int(round(math.radians(120.0) * R / ROW))
    for j in range(n_arc + 1):                       # arc about the origin, turning left (counter-clockwise from above)
        a = (ROW / R) * j
        pts.append((R * math.cos(a), -GRADE * s, R * math.sin(a))); s += ROW
    hx, hz = -math.sin((ROW / R) * n_arc), math.cos((ROW / R) * n_arc)
    x0, _, z0 = pts[-1]
    for k in range(1, 11):                           # straight out
        pts.append((x0 + hx * ROW * k, -GRADE * s, z0 + hz * ROW * k)); s += ROW
    return pts


def _height_at(rib, x, z):
    v = rib["vertices"]
    best = None
    for a, b, c in rib["tris"]:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = v[a], v[b], v[c]
        d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(d) < 1e-12:
            continue
        l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
        l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
        l3 = 1.0 - l1 - l2
        if min(l1, l2, l3) >= -1e-9:
            y = l1 * ay + l2 * by + l3 * cy
            best = y if best is None else max(best, y)
    assert best is not None, f"no triangle under ({x}, {z})"
    return best


def _worst_centre_step(rib):
    """drive_test's severe-step measure on the wheel pair either side of the centreline, over the arc at 1 m: the second
    difference of the surface height along a constant-radius path"""
    worst = 0.0
    for off in (-0.75, 0.75):
        r = R - off                                   # left (+) is the inside of a left-hander
        hs = []
        for m in range(int(math.radians(110.0) * R)):
            a = math.radians(5.0) + m / R
            hs.append(_height_at(rib, r * math.cos(a), r * math.sin(a)))
        for i in range(2, len(hs)):
            worst = max(worst, abs((hs[i] - hs[i - 1]) - (hs[i - 1] - hs[i - 2])))
    return worst


def test_one_quad_row_steps_on_a_graded_corner_and_columns_remove_it():
    cl = _corner()
    w = [WIDTH] * len(cl)
    one = ribbon.road_ribbon(cl, w)
    four = ribbon.road_ribbon(cl, w, cols=4)
    s1, s4 = _worst_centre_step(one), _worst_centre_step(four)
    assert s1 > 0.06                       # the defect: a severe step (drive_test's 6 cm) across the centre pair (~22 cm)
    # with a column line on the centreline the severe step goes; ~2.7 cm is left on this extreme corner (2 m inside
    # radius) from the columns' own smaller twist
    assert s4 < 0.06 and s4 < 0.2 * s1


def test_ribbon_cols_is_honoured_without_banking():
    assert bm.ribbon_cols(None) == 1
    assert bm.ribbon_cols({}) == 1
    assert bm.ribbon_cols({"dips": [], "cambers": []}) == 1
    assert bm.ribbon_cols({"ribbon_cols": 4}) == 4
    assert bm.ribbon_cols({"ribbon_cols": 8, "cambers": [{"bank_deg": -10.0}]}) == 8
    assert bm.ribbon_cols({"ribbon_cols": 0}) == 1


def test_every_track_that_declared_ribbon_cols_before_is_banked():
    """The rule changed from 'banked only' to 'wherever declared'. That is byte-identical for the fleet only while every
    track that declared the key before 0069 is banked: such a track built columns already."""
    import json
    from scripts.geometry import profile
    for cfg_path in sorted((ROOT / "tracks").glob("*/track.config.json")):
        rp = json.loads(cfg_path.read_text(encoding="utf-8")).get("road_profile") or {}
        if "ribbon_cols" not in rp or cfg_path.parent.name == "milford-road-course":
            continue
        _dip, _bank, active = profile.build_profile(rp)
        assert active, f"{cfg_path.parent.name} declares ribbon_cols on an unbanked road: its ribbon changes under 0069"

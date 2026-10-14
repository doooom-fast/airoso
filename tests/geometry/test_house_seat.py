"""Ledger 0046 fix round 3: buildings are seated on the FINAL ground under their own footprint (engine-july prep,
snapshot of record) — the visual lens found houses that stood upright in v0.17.1 half under a hill, because the
draft sat them on one centroid read and the prep then reshaped the ground and moved them by one corner's delta."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py"


def _bkl():
    sp = importlib.util.spec_from_file_location("_bkl_house_seat", SNAP)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def test_level_ground_keeps_the_drafts_seat():
    b = _bkl()
    floor, base = b.house_seat(100.0, 100.0)
    assert floor == base == 100.0 - b.HOUSE_SINK_M == 99.6          # the draft's own rule: ground - 0.4


def test_a_slope_reaches_down_instead_of_floating():
    b = _bkl()
    # 12 m house across a 20 % slope: corners at 98.8 and 101.2, mean 100
    floor, base = b.house_seat(100.0, 98.8)
    assert floor == 99.6                                               # visible height starts at the mean less 0.4
    assert base == 98.8 - b.HOUSE_FOOT_M                               # the downhill wall goes into the ground
    assert base < floor


def test_the_sunken_house_case_is_lifted_to_its_ground():
    """the visual lens's (-249, 1461): ground ~90.1 under the footprint, base had been lowered to 87.42 by one
    corner's delta — seated on its own ground the house stands with 0.4 m in the ground, not half its height"""
    b = _bkl()
    floor, base = b.house_seat(90.12, 89.9)
    assert abs(floor - 89.72) < 1e-9 and floor - 87.42 > 2.0
    assert (90.12 - floor) / 5.5 < 0.1                                 # buried fraction by the lens's own measure


def test_footprint_samples_read_corners_centroid_and_walls():
    b = _bkl()
    ring = [(0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0)]
    level, low = b.footprint_samples(ring)
    assert level[:4] == ring and level[4] == (6.0, 4.0) and len(level) == 5
    assert low[:4] == ring and (6.0, 4.0) not in low        # the walls' ground, not a hollow under the floor
    walls = low[4:]
    # 12 m walls -> 8 interior points each (spacing 12/9 <= 1.5 m), 8 m walls -> 5
    assert len(walls) == 8 + 5 + 8 + 5
    assert all(0.0 <= x <= 12.0 and 0.0 <= y <= 8.0 for x, y in walls)
    assert all(x in (0.0, 12.0) or y in (0.0, 8.0) for x, y in walls)  # on the walls, not inside


def test_a_footprint_straddling_a_cut_edge_shows_half_its_height_uphill():
    """the build's (1369, -908): 7.4 m of ground under one 5.5 m house at the I-8 cut's south rim — seated at its mean
    ground its uphill wall was swallowed; at least half its height now stands above the highest ground under it"""
    b = _bkl()
    floor, base = b.house_seat(65.4, 63.6, 71.0, 5.5)
    assert floor == 71.0 - 0.5 * 5.5 and floor > 65.4 - 0.4
    assert base == 63.6 - b.HOUSE_FOOT_M                                # its downhill foundation still reaches down
    floor2, _ = b.house_seat(100.0, 98.8, 101.2, 5.5)                   # an ordinary slope: the mean rule stands
    assert floor2 == 99.6


def test_house_seat_check_flags_floating_sunken_and_buried():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import house_seat_check as hc
    import tempfile
    # one 10 x 10 m box on a 1 m-step ground plane at y = 0, its bottom at `b`, roof at `b + 5`
    def obj(b, ground_tilt=0.0):
        v = [(-20, 0, -20), (20, 40 * ground_tilt, -20), (20, 40 * ground_tilt, 20), (-20, 0, 20)]
        v = [(x, y, z) for x, y, z in v]
        f = ["o 1GRASS_0", "f 1 2 3", "f 1 3 4", "o HOUSE"]
        box = [(0, b, 0), (10, b, 0), (10, b, 10), (0, b, 10), (0, b + 5, 0), (10, b + 5, 0), (10, b + 5, 10), (0, b + 5, 10)]
        lines = [f"v {x} {y} {z}" for x, y, z in v + box]
        o = 4
        for k in range(4):
            a, c = o + 1 + k, o + 1 + (k + 1) % 4
            d, e = o + 5 + (k + 1) % 4, o + 5 + k
            f += [f"f {a} {d} {c}", f"f {a} {e} {d}"]
        f += [f"f {o+5} {o+7} {o+6}", f"f {o+5} {o+8} {o+7}"]
        return "\n".join(lines + f) + "\n"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.obj"
        for b, tilt, want in ((-0.3, 0.0, "PASS"), (0.6, 0.0, "floating"), (-1.6, 0.0, "sunken"), (-0.2, 0.15, "buried")):
            p.write_text(obj(b, tilt))
            rep, rows = hc.run(Path(d), p)
            assert rep["buildings"] == 1, rep
            if want == "PASS":
                assert rep["verdict"] == "PASS", rep
            else:
                assert rep["verdict"] == "FAIL" and rep[want] == 1, (want, rep)

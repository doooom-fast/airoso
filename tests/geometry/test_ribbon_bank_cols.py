"""road_ribbon ``cols``: a camber ramp must not sag the deck between rows (Exotics Racing T2, 2026-10-28)."""

import math

from scripts.geometry import ribbon
from scripts.geometry.profile import build_profile

# a straight 120 m road, 3 m rows (the pipeline's spacing), 17 m wide, banking 0 -> 6.3 deg over 20 m
CL = [(0.0, 0.0, 3.0 * i) for i in range(41)]
W = [17.0] * len(CL)
_, BANK_AT, _ = build_profile({"cambers": [{"name": "t", "start_m": 30, "len_m": 80, "bank_deg": 6.3, "ramp_m": 20}]})


def _height_at(rib, x, z):
    """Height of the ribbon surface at (x, z): barycentric on the triangle that contains it."""
    v = rib["vertices"]
    for a, b, c in rib["tris"]:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = v[a], v[b], v[c]
        d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(d) < 1e-12:
            continue
        l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
        l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
        l3 = 1.0 - l1 - l2
        if min(l1, l2, l3) >= -1e-9:
            return l1 * ay + l2 * by + l3 * cy
    raise AssertionError(f"no triangle under ({x}, {z})")


def _worst_centre_sag(rib):
    # the ideal deck at lateral x (left = -x here) and station z is y = -x*tan(bank(z)); mid-row samples
    # off every column line expose the diagonal sag of a twisted quad
    worst = 0.0
    for z in range(30, 110, 3):
        for x in (-6.1, -2.3, 0.75, 3.7, 7.3):
            ideal = -x * math.tan(BANK_AT(z + 1.5))
            worst = max(worst, abs(_height_at(rib, x, z + 1.5) - ideal))
    return worst


def test_single_column_twist_sags_and_cols_remove_it():
    one = ribbon.road_ribbon(CL, W, bank_at=BANK_AT)
    eight = ribbon.road_ribbon(CL, W, bank_at=BANK_AT, cols=8)
    s1, s8 = _worst_centre_sag(one), _worst_centre_sag(eight)
    assert s1 > 0.05                                 # the defect: ~10 cm of sag mid-ramp
    # split eight ways the twist sag goes; what is left (~1.6 cm at the 7.3 m edge sample) is the
    # ramp's own curvature between 3 m rows, which no column count changes
    assert s8 < 0.2 * s1


def test_cols_keeps_the_edges_and_the_bank():
    one = ribbon.road_ribbon(CL, W, bank_at=BANK_AT)
    eight = ribbon.road_ribbon(CL, W, bank_at=BANK_AT, cols=8)
    k = 9
    assert len(eight["vertices"]) == k * (len(one["vertices"]) // 2) == len(eight["uvs"])
    for i in range(len(CL)):
        assert eight["vertices"][k * i] == one["vertices"][2 * i]              # left edge
        assert eight["vertices"][k * i + 8] == one["vertices"][2 * i + 1]      # right edge
        mid = eight["vertices"][k * i + 4]
        assert abs(mid[1]) < 1e-9 and abs(mid[0]) < 1e-9                       # centre on the axis
    tb = math.tan(math.radians(6.3))
    assert abs(eight["vertices"][k * 30][1] - 8.5 * tb) < 1e-9                  # full bank, left edge up


def test_default_is_the_two_edge_ribbon():
    a = ribbon.road_ribbon(CL, W, bank_at=BANK_AT)
    b = ribbon.road_ribbon(CL, W, bank_at=BANK_AT, cols=1)
    assert a == b and len(a["vertices"]) == 2 * len(CL) and len(a["tris"]) == 2 * (len(CL) - 1)

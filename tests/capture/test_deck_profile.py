"""The measured bridge-deck profile (capture.bridges[].profile_m, ledger 0068): opt-in per bridge, laid on the
finished line in evidence.apply_deck_profiles from build_mesh.finished_centerline, its stations metres from the
bridge's start (center_m - len_m / 2).

Pinned: a config without a profile changes nothing (byte-identical, on the evidence functions and on
finished_centerline itself); a profile is followed exactly inside its stations, in absolute heights; the road eases
back with no step at either end and is untouched past the ramp; a closed lap wraps (L13); a bad profile is refused.
Plain ``test_*`` functions, stdlib only, for tests/run_tests.py.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.capture import evidence  # noqa: E402

ELEV0 = 1500.0


def _line(length=400.0, step=2.0, y=lambda s: 0.0):
    """Straight line along +X, station == x; local y from ``y(station)``."""
    n = int(round(length / step))
    return [(i * step, y(i * step), 0.0) for i in range(n + 1)]


def _cfg(bridges):
    return {"capture": {"bridges": bridges}}


def test_no_profile_is_no_change():
    pts = _line(y=lambda s: 0.01 * s)
    for cfg in ({}, {"capture": {}}, _cfg([]), _cfg([{"name": "a", "center_m": 200, "len_m": 100}])):
        decks = evidence.deck_profiles(cfg)
        assert decks == []
        out = evidence.apply_deck_profiles(pts, decks, origin_elev_m=ELEV0)
        assert out == [tuple(p) for p in pts]


def test_profile_is_followed_inside_its_stations_in_absolute_heights():
    pts = _line(y=lambda s: 0.0)
    prof = [[0.0, ELEV0 + 0.10], [50.0, ELEV0 + 0.50], [100.0, ELEV0 + 0.20]]       # from the start, 150 m
    decks = evidence.deck_profiles(_cfg([{"name": "d", "center_m": 200, "len_m": 100, "profile_m": prof}]))
    assert decks[0]["ramp_m"] == evidence.DECK_PROFILE_RAMP_M
    out = evidence.apply_deck_profiles(pts, decks, origin_elev_m=ELEV0)
    by_s = {p[0]: p[1] for p in out}
    assert abs(by_s[150.0] - 0.10) < 1e-9 and abs(by_s[200.0] - 0.50) < 1e-9 and abs(by_s[250.0] - 0.20) < 1e-9
    assert abs(by_s[176.0] - (0.10 + 0.40 * 26 / 50)) < 1e-9          # linear between profile points
    assert all(a[0] == b[0] and a[2] == b[2] for a, b in zip(pts, out))   # Y only


def test_ends_ease_back_without_a_step_and_stop_at_the_ramp():
    base = lambda s: 0.02 * (s - 200.0)          # a 2 % grade under the deck
    pts = _line(step=1.0, y=base)
    prof = [[0.0, ELEV0 + base(150.0) + 0.3], [100.0, ELEV0 + base(250.0) + 0.2]]
    decks = evidence.deck_profiles(_cfg([{"name": "d", "center_m": 200, "len_m": 100, "profile_m": prof,
                                          "profile_ramp_m": 20}]))
    out = evidence.apply_deck_profiles(pts, decks, origin_elev_m=ELEV0)
    y = [p[1] for p in out]
    steps = [abs(y[i + 1] - y[i] - 0.02) for i in range(len(y) - 1)]
    assert max(steps) < 0.03, max(steps)                       # no step anywhere, 1 m stations
    for i, p in enumerate(out):
        if p[0] <= 130.0 or p[0] >= 270.0:
            assert p[1] == pts[i][1]                           # untouched past the ramp
    assert abs(y[140] - base(140.0) - 0.15) < 1e-9            # half the lift, half way down the west ramp


def test_closed_lap_wraps_the_seam():
    # a 400 m square lap whose profile ends 5 m before the seam: the ease must continue past vertex 0 and the
    # closing duplicate must get exactly what vertex 0 gets
    side, step = 100.0, 1.0
    pts = []
    for k in range(4):
        for i in range(int(side / step)):
            t = i * step
            pts.append([(t, 0.0, 0.0), (side, 0.0, t), (side - t, 0.0, side), (0.0, 0.0, side - t)][k])
    pts.append(pts[0])
    prof = [[0.0, ELEV0], [95.0, ELEV0 + 0.4]]          # 300-395 m
    decks = evidence.deck_profiles(_cfg([{"name": "seam", "center_m": 347.5, "len_m": 95, "profile_m": prof,
                                          "profile_ramp_m": 20}]))
    out = evidence.apply_deck_profiles(pts, decks, origin_elev_m=ELEV0)
    assert out[0][1] == out[-1][1]
    expect0 = 0.4 * 0.5 * (1 + math.cos(math.pi * 5.0 / 20.0))
    assert abs(out[0][1] - expect0) < 1e-9, out[0][1]
    assert out[10][1] > 0.0 and out[30][1] == 0.0


def test_bad_profiles_are_refused():
    for prof in ([[100, 1.0]], [[100, 1.0], [100, 2.0]], [[200, 1.0], [100, 2.0]]):
        try:
            evidence.deck_profiles(_cfg([{"name": "x", "center_m": 200, "len_m": 50, "profile_m": prof}]))
        except ValueError:
            continue
        raise AssertionError(f"accepted {prof}")
    try:
        evidence.deck_profiles(_cfg([{"name": "no span", "profile_m": [[0, 1.0], [10, 1.0]]}]))
    except ValueError:
        pass
    else:
        raise AssertionError("a profile with no span to measure from was accepted")


def test_profile_is_keyed_to_the_bridges_start():
    # the same deck re-keyed after a line change: moving center_m moves every profile point with it
    prof = [[-4, ELEV0 + 0.1], [0, ELEV0 + 0.2], [118, ELEV0 + 0.3]]
    a = evidence.deck_profiles(_cfg([{"name": "d", "center_m": 2463, "len_m": 118, "profile_m": prof}]))[0]
    b = evidence.deck_profiles(_cfg([{"name": "d", "center_m": 2449, "len_m": 118, "profile_m": prof}]))[0]
    assert a["start_m"] == 2404.0 and a["profile"][0] == (2400.0, ELEV0 + 0.1) and a["profile"][-1] == (2522.0, ELEV0 + 0.3)
    assert [round(s - t, 9) for (s, _), (t, _) in zip(a["profile"], b["profile"])] == [14.0] * 3
    assert [h for _, h in a["profile"]] == [h for _, h in b["profile"]]


def test_finished_centerline_unchanged_without_a_profile_and_needs_the_datum_with_one():
    from scripts.geometry.build_mesh import finished_centerline
    raw = [(float(i * 3.0), 0.01 * i, 2.0 * math.sin(i / 15.0)) for i in range(120)]
    cfg = {"capture": {"bridges": [{"name": "b", "center_m": 150, "len_m": 60}]}}
    a = finished_centerline(list(raw), json.loads(json.dumps(cfg)), mirror_x=False)[0]
    b = finished_centerline(list(raw), json.loads(json.dumps(cfg)), mirror_x=False, origin_elev_m=ELEV0)[0]
    assert a == b                                            # no profile: the datum is never read
    cfg["capture"]["bridges"][0]["profile_m"] = [[0, ELEV0 + 2.0], [60, ELEV0 + 2.0]]     # 120-180 m
    try:
        finished_centerline(list(raw), cfg, mirror_x=False)
    except ValueError:
        pass
    else:
        raise AssertionError("a profile without origin_elev_m must be refused, not laid at the wrong datum")
    c = finished_centerline(list(raw), cfg, mirror_x=False, origin_elev_m=ELEV0)[0]
    st = [0.0]
    for i in range(1, len(c)):
        st.append(st[-1] + math.hypot(c[i][0] - c[i - 1][0], c[i][2] - c[i - 1][2]))
    inside = [c[i][1] for i in range(len(c)) if 120 <= st[i] <= 180]
    assert inside and all(abs(v - 2.0) < 1e-9 for v in inside)

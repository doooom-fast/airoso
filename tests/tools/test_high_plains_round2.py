"""High Plains 0.1.10, ledger 0097 round 2 (Kevin 2026-11-22: "Rebuild at the measured widths", the owned concrete "On every
track now", the grey roof "as a low shed [invented height]", the pit-exit merge paving, the R s 2,673 stripe).

- tools/edge_retrace.py mode "measured" (opt-in): ONE sensor, each edge in OR out to its reading; the line moves by half the
  difference, the width is left + right; nothing outside the spans; the other two modes keep their own behaviour.
- The port's measured evidence is in the line's frame and the config reads it through that mode alone.
- The port's kerbs file is the source's but for R s 2,673's edge points (moved outward, in_m / out_m kept).
- The grey roof is a traced shed with an [invented] height; the pit-exit strip is a pad of equal sides outside the paddock
  sheet; the concrete row binds the owned pair, which ship.json syncs; rows 3 / 8 are documented, not moved.
- Every one of these keys is High Plains' own.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HP = ROOT / "tracks" / "high-plains-lm"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


er = _load("edge_retrace")


def _cfg(track="high-plains-lm"):
    return json.loads((ROOT / "tracks" / track / "track.config.json").read_text(encoding="utf-8"))


def _loop(n=800, r=200.0):
    pts = [(r * math.cos(2 * math.pi * k / n), 0.0, r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return pts + [pts[0]]


def _edge_points(pts, rows, off, src="naip"):
    out = []
    n = len(pts) - 1
    for i in rows:
        a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz)
        nx, nz = -tz / L, tx / L
        for _ in range(3):
            out.append([pts[i][0] + nx * off, pts[i][2] + nz * off, src, 30.0])
    return out


def test_measured_mode_moves_each_edge_in_or_out_on_one_sensor():
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [12.0] * len(pts)
    # NAIP reads the left edge IN at 5.0 m and the right edge OUT at 6.5 m all round; a lidar point that would disagree is
    # ignored (one sensor)
    ev = _edge_points(pts, range(n), 5.0) + _edge_points(pts, range(n), -6.5)
    ev += _edge_points(pts, range(0, n, 7), 7.5, src="lidar")
    new, shift, rep = er.retrace(pts, w, True, ev, [[0.0, lap]], [], mode="measured", erode_m=3.0, smooth_m=4.0)
    mid = min(range(n), key=lambda i: abs(st[i] - 400.0))
    assert abs(new[mid] - 11.5) < 0.02, new[mid]               # 5.0 + 6.5
    assert abs(shift[mid] - (5.0 - 6.5) / 2) < 0.02, shift[mid]  # the line moves toward the wider side
    assert rep["mode"] == "measured" and rep["src"] == "naip"
    assert new[-1] == new[0]
    # mode widen on the same evidence never moves the left edge in
    new_w, shift_w, _ = er.retrace(pts, w, True, ev, [[0.0, lap]], [], erode_m=3.0, smooth_m=4.0)
    assert new_w[mid] / 2 + shift_w[mid] >= 6.0 - 1e-6


def test_measured_mode_leaves_rows_outside_its_spans():
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [12.0] * len(pts)
    ev = _edge_points(pts, range(n), 5.0) + _edge_points(pts, range(n), -5.0)
    new, shift, _ = er.retrace(pts, w, True, ev, [[300.0, 500.0]], [], mode="measured", taper_m=30.0)
    far = min(range(n), key=lambda i: abs(st[i] - 900.0))
    mid = min(range(n), key=lambda i: abs(st[i] - 400.0))
    assert abs(new[far] - 12.0) < 1e-6 and abs(shift[far]) < 1e-6
    assert abs(new[mid] - 10.0) < 0.02


def test_unknown_mode_is_refused():
    try:
        er.retrace(_loop(), [12.0] * 801, True, [], [[0.0, 10.0]], [], mode="median")
    except SystemExit as e:
        assert "mode" in str(e)
    else:
        raise AssertionError("an unknown retrace mode must stop the intake")


def test_high_plains_reads_its_measured_edge_through_mode_measured():
    c = _cfg()
    rec, = c["lm_intake"]["edge_retrace"]
    assert rec["mode"] == "measured" and rec["src"] == "naip" and rec["shift_precomp"] is True
    assert rec["spans"] == [[0.0, 3205.0]]
    assert "paddock_row_3" not in rec["rails"] and "paddock_row_8" not in rec["rails"]   # the kerbs' paint, not rails
    rails = {r["key"] for r in c["scenery"]["bespoke"]["rails"]}
    assert set(rec["rails"]) <= rails
    ev = json.loads((HP / rec["evidence"]).read_text(encoding="utf-8"))
    raw = json.loads((HP / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))
    assert abs(ev["origin"]["lon"] - raw["origin"]["lon"]) < 1e-12 and abs(ev["origin"]["lat"] - raw["origin"]["lat"]) < 1e-12
    assert len(ev["points"]) > 4000 and {p[2] for p in ev["points"]} == {"naip"}
    assert {m["side"] for m in ev["mouths"]} == {"left", "right"}
    ship = json.loads((HP / "ship.json").read_text(encoding="utf-8"))
    assert rec["evidence"] in ship["sync_in"]["required"]
    # the readings: every station a 1 m step, the straights' paved width 10.7-11.6 m (ledger 0059: the edge lines' centres
    # 10.5 m apart), the front straight 11.8-12.7 m
    wm = json.loads((HP / "source" / "edges" / "widths_measured.json").read_text(encoding="utf-8"))
    rows = wm["rows"]
    w = lambda a, b: sorted(r["width_m"] for r in rows if a <= r["s"] <= b and r["width_m"] is not None)
    med = lambda v: v[len(v) // 2]
    assert 10.7 <= med(w(820, 1180)) <= 11.6
    assert 11.8 <= med(w(20, 170)) <= 12.7


def test_kerbs_lm_is_the_source_but_for_the_r2673_stripe():
    src = json.loads((ROOT / "tracks" / "high-plains" / "source" / "edges" / "kerbs.json").read_text(encoding="utf-8"))
    lm = json.loads((HP / "source" / "edges" / "kerbs.lm.json").read_text(encoding="utf-8"))
    # round 4 appended the north loop's runs ("line": full_north#0#0, test_high_plains_round4.py); the lap's 20 come first
    lm = dict(lm, kerbs=[k for k in lm["kerbs"] if not k.get("line")])
    c = _cfg()
    assert c["route"]["kerbs_file"] == "source/edges/kerbs.lm.json"
    assert not (ROOT / "tracks" / "high-plains" / "source" / "edges" / "kerbs.lm.json").exists()   # the port's own (synced in)
    assert "source/edges/kerbs.lm.json" in json.loads((HP / "ship.json").read_text(encoding="utf-8"))["sync_in"]["required"]
    assert len(src["kerbs"]) == len(lm["kerbs"]) == 20
    changed = [i for i, (a, b) in enumerate(zip(src["kerbs"], lm["kerbs"])) if a != b]
    # round 3 re-traced the T13 kerb (L s 2,843) by the same rule (test_high_plains_round3.py); nothing else moved
    assert sorted((src["kerbs"][i]["side"], src["kerbs"][i]["s0"]) for i in changed) == [("left", 2843.0), ("right", 2673.0)]
    for i in changed:
        a, b = src["kerbs"][i], lm["kerbs"][i]
        assert {k: v for k, v in a.items() if k != "edge_lonlat"} == {k: v for k, v in b.items()
                                                                       if k not in ("edge_lonlat", "edge_lonlat_was", "_retrace")}
    assert b["edge_lonlat_was"] == a["edge_lonlat"] and len(b["edge_lonlat"]) == len(a["edge_lonlat"])
    m_lon = 111412.84 * math.cos(math.radians(39.735))
    m_lat = 111132.954 - 559.822 * math.cos(math.radians(2 * 39.735))
    moved = [math.hypot((p[0] - q[0]) * m_lon, (p[1] - q[1]) * m_lat) for p, q in zip(a["edge_lonlat"], b["edge_lonlat"])]
    assert 1.8 <= moved[0] <= 2.8 and all(m < 0.01 for m in moved[5:]), moved   # the first points onto the paint, the rest kept


def test_grey_roof_is_a_traced_shed_of_invented_height():
    rows = json.loads((HP / "source" / "bespoke" / "buildings.race.json").read_text(encoding="utf-8"))
    roof = next(r for r in rows if r["key"] == "traced_grey_roof_e_of_containers")
    assert roof["class"] == "shed" and roof["form"] == "flat"
    assert roof["_h"].startswith("[invented]")
    assert len(roof["footprint_lonlat"]) == 4
    keys = [r["key"] for r in rows]
    assert keys.index("traced_grey_roof_e_of_containers") == keys.index("traced_container_row") + 1


def test_pit_exit_strip_is_outside_the_paddock_sheet():
    pads = _cfg()["scenery"]["bespoke"]["pads"]
    assert [p["key"] for p in pads][-1] == "pit_exit"          # appended: the old PADAPRON_<k> keep their numbers
    pe = pads[-1]["strip_lonlat"]
    assert len(pe["inner"]) == len(pe["outer"]) >= 40
    quad = next(p for p in pads if p["key"] == "paddock")["quad_lonlat"]

    def inside(q, x, y):
        c = False
        for i in range(len(q)):
            x1, y1 = q[i]; x2, y2 = q[(i + 1) % len(q)]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c
    assert not any(inside(quad, *p) for p in pe["inner"] + pe["outer"])


def test_owned_concrete_on_the_edge_strip_and_synced():
    c = _cfg()
    ov = c["texture_overrides"]["1KERB_SIDEWALK"]
    assert ov["diffuse"] == "assets/textures/concrete_plain_diffuse.jpg"
    assert ov["normal"] == "assets/textures/concrete_plain_normal.jpg"
    assets = json.loads((HP / "ship.json").read_text(encoding="utf-8"))["sync_in"]["assets"]
    for f in (ov["diffuse"], ov["normal"]):
        assert f in assets and (ROOT / f).exists()


def test_rows_3_and_8_are_removed_as_kerb_paint():
    """ledger 0097 round 2: the two rows' blue sections are the kerb paint, not K-rails; standing them would invent barriers,
    so the Mac removed them (Kevin 2026-11-22: decide on my own, 'I just want real'); the config says why"""
    bes = _cfg()["scenery"]["bespoke"]
    keys = {r["key"] for r in bes["rails"]}
    assert not {"paddock_row_3", "paddock_row_8"} & keys
    assert "kerb paint" in bes["_rows_3_8_doc"]


def test_version_and_every_round2_key_is_high_plains_own():
    c = _cfg()
    assert c["version"] in ("0.1.10", "0.1.11", "0.1.12")    # rounds 3 and 4 (0.1.11, 0.1.12) keep every round-2 key
    concrete_users = {"milford-road-course-lm", "sand-creek-lm", "san-diego-lake-murray", "denver-grand-prix"}
    for t, cfg in ((p.parent.name, json.loads(p.read_text(encoding="utf-8")))
                   for p in (ROOT / "tracks").glob("*/track.config.json")):
        if t == "high-plains-lm":
            continue
        for r in (cfg.get("lm_intake") or {}).get("edge_retrace") or []:
            assert r.get("mode") != "measured", t
        assert (cfg.get("route") or {}).get("kerbs_file") != "source/edges/kerbs.lm.json", t
        ov = ((cfg.get("texture_overrides") or {}).get("1KERB_SIDEWALK") or {}).get("diffuse", "")
        assert "concrete_plain" not in ov or t in concrete_users, t


def test_full_layouts_extra_pieces_are_measured_data():
    """item 2's data half: Bobsled + Ladder from the fork to the merge, in the engine's connector shape; both ends on the West
    lap's line; the widths measured where both sides read and CARRIED (marked) elsewhere. Round 3 builds it (the carried rows
    now take their edges between the nearest measured rows, and source/full/connectors.full.json is what the config reads)"""
    d = json.loads((HP / "source" / "full" / "north_loop.json").read_text(encoding="utf-8"))
    c, = d["connectors"]
    assert c["name"] == "full_north" and c["kind"] == "connector"
    assert len(c["points_xyz_m"]) == len(c["widths_m"]) == d["summary"]["points"]
    assert 990.0 <= d["summary"]["length_m"] <= 1010.0                 # OSM: 568.3 + 432.8 m
    assert all(10.0 <= w <= 15.0 for w in c["widths_m"])
    # round 4 (test_high_plains_round4.py) read the carried verge rows a second time: "measured_second_read"
    assert {r["width"] for r in d["rows"]} == {"measured", "measured_second_read", "carried"}
    lo, hi = d["summary"]["width_measured_m"][0], d["summary"]["width_measured_m"][-1]
    assert all(lo - 0.6 <= r["width_m"] <= hi + 0.6 for r in d["rows"] if r["width"] == "carried")
    lap = json.loads((HP / "data" / "gate_centerline.json").read_text(encoding="utf-8"))["points_xyz_m"]
    for end in (c["points_xyz_m"][0], c["points_xyz_m"][-1]):
        near = min(math.hypot(end[0] - p[0], end[2] - p[2]) for p in lap)
        assert near < 6.0, near                                         # the fork and the merge lie on the West lap
    assert _cfg()["lm_intake"]["connectors_file"] == "source/full/connectors.full.json"

"""tools/stub_roads.py — the phase-5 stub declaration and draft (ledger 0054, 2026-10-14), plus the two opt-in hooks
it needs in tools/trim_connectors.py.

A straight host 20 m wide along +x on a +4 % grade, and a synthetic OSM around it: a residential street crossing it
(two branches, L and R, 2 lanes), a service driveway (curb cut), a motorway ramp (skipped), a way running along the
host (a carriageway: skipped), and a side street already built as a connector (skipped). The draft: with no
declaration nothing is touched (bytes compared); with one, each stub is appended AFTER every existing connector (the
assembler's vertex blocks keep their ranges), its height profile starts on the host centreline at the cut on the
host's own grade along it and reaches the 3DEP grade through a vertical curve no steeper than RAMP_DG_PER_M; the trim
records its mouth, keeps the profile (blend_m 0) and never extends its dead end back to the host.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import stub_roads as sr  # noqa: E402
import trim_connectors as tc  # noqa: E402

ORIGIN = {"lon": -117.05, "lat": 32.79, "elev_m": 100.0}
GRADE = 0.04
HALF = 10.0


def _ll(x, z):
    return list(sr.to_lonlat(x, z, ORIGIN))


def _project(tmp, with_built=True):
    proj = Path(tmp)
    (proj / "data").mkdir(parents=True, exist_ok=True)
    pts = [[-150.0 + 3.0 * i, GRADE * (-150.0 + 3.0 * i), 0.0] for i in range(101)]
    (proj / "data" / "centerline.local.json").write_text(json.dumps(
        {"origin": ORIGIN, "points_xyz_m": pts, "widths_m": [2 * HALF] * len(pts)}), encoding="utf-8")
    conns = [{"name": "other", "kind": "connector",
              "points_xyz_m": [[100.0, 4.0, 5.0 + 3.0 * k] for k in range(30)], "widths_m": [10.0] * 30}]
    doc = json.dumps({"connectors": conns})
    (proj / "data" / "connectors.local.json").write_text(doc, encoding="utf-8")
    (proj / "data" / "connectors.local.json.pre-trim").write_text(doc, encoding="utf-8")
    (proj / "track.config.json").write_text(json.dumps({"slug": "t", "route": {}}), encoding="utf-8")
    nodes = {}
    ways = []

    def node(nid, x, z):
        nodes[str(nid)] = _ll(x, z)
        return nid
    host_nodes = [node(1000 + i, -150.0 + 10.0 * i, 0.3) for i in range(31)]
    ways.append({"id": 1, "nodes": host_nodes, "tags": {"highway": "primary", "name": "Host Road"}})
    # a crossing residential street at x = 0 (the junction node is the host's node 1015 at x = 0)
    ways.append({"id": 2, "nodes": [node(2001, 0.0, -60.0), node(2002, 0.0, -30.0), 1015, node(2003, 0.0, 30.0),
                                    node(2004, 0.0, 60.0)],
                 "tags": {"highway": "residential", "name": "Cross Street", "lanes": "2"}})
    ways.append({"id": 3, "nodes": [1010, node(3001, -50.0, 40.0)], "tags": {"highway": "service"}})
    ways.append({"id": 4, "nodes": [1005, node(4001, -100.0, -40.0)], "tags": {"highway": "motorway_link"}})
    ways.append({"id": 5, "nodes": [1020, node(5001, 90.0, 13.0), node(5002, 130.0, 26.0)],
                 "tags": {"highway": "residential", "name": "Slip"}})
    ways.append({"id": 6, "nodes": [1025, node(6001, 100.0, 30.0), node(6002, 100.0, 90.0)],
                 "tags": {"highway": "residential", "name": "Built Avenue"}})
    (proj / "osm.json").write_text(json.dumps({"nodes": nodes, "ways": ways}), encoding="utf-8")
    return proj


def _dem(slope_along=0.07):
    """a fake 3DEP: absolute elevation rising `slope_along` per metre of |z| (away from the host), on the host's own
    grade along x"""
    def sample(lonlat):
        out = []
        for lon, lat in lonlat:
            x, z = sr.to_local(lon, lat, ORIGIN)
            out.append(ORIGIN["elev_m"] + GRADE * x + slope_along * abs(z) + 0.3)
        return out
    return sample


def test_declare_finds_every_branch_and_sorts_its_treatment():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        doc = sr.declare(proj, proj / "osm.json")
        by = {(e["way"], e["side"]): e for e in doc["stubs"]}
        assert by[(2, 1)]["treatment"] == "stub" and by[(2, -1)]["treatment"] == "stub"
        assert by[(2, 1)]["width_m"] == round(2 * sr.LANE_W_M + 2 * sr.GUTTER_W_M, 2)
        assert "lanes=2" in by[(2, 1)]["width_source"]
        assert abs(by[(2, 1)]["angle_deg"] - 90.0) < 1.0
        assert by[(2, 1)]["host_street"] == "Host Road"
        cut = next(e for e in doc["stubs"] if e["way"] == 3)
        assert cut["treatment"] == "curb_cut" and cut["width_m"] == sr.SERVICE_WIDTH_M
        ramp = next(e for e in doc["stubs"] if e["way"] == 4)
        assert ramp["treatment"] == "skip" and "phase 4" in ramp["skip_reason"]
        # a way running along the host is never a stub: a host way when most of it is on the host, else skipped as
        # a carriageway / slip lane
        assert all(e["treatment"] == "skip" and "carriageway" in e["skip_reason"] for e in doc["stubs"] if e["way"] == 5)
        lone = sr.Line([[0.0, 0.0, 0.0], [300.0, 0.0, 0.0]], [20.0, 20.0])
        cut = sr.find_cut(lone, [(100.0, 0.0), (140.0, 13.0), (180.0, 26.0)])
        assert cut is not None and math.degrees(math.atan2(abs(cut[4]), abs(cut[3]))) < sr.PARALLEL_DEG
        built = next(e for e in doc["stubs"] if e["way"] == 6)
        assert built["treatment"] == "skip" and "already built" in built["skip_reason"]
        assert sr.validate_declaration(doc) == []


def test_only_and_merge_keep_the_hand_edits():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        doc = sr.declare(proj, proj / "osm.json")
        sid = next(e["id"] for e in doc["stubs"] if e["way"] == 2 and e["side"] == 1)
        only = sr.declare(proj, proj / "osm.json", only={sid})
        act = [e["id"] for e in only["stubs"] if e["treatment"] != "skip"]
        assert act == [sid]
        for e in doc["stubs"]:
            if e["id"] == sid:
                e["width_m"] = 11.5
                e["hand"] = ["width_m"]
        old = Path(tmp) / "old.json"
        old.write_text(json.dumps(doc), encoding="utf-8")
        again = sr.declare(proj, proj / "osm.json", merge=old)
        assert next(e for e in again["stubs"] if e["id"] == sid)["width_m"] == 11.5


def test_validation_refuses_what_the_chain_cannot_build():
    bad = {"stubs": [
        {"id": "a", "treatment": "stub", "length_m": 5.0, "width_m": 10.0, "barrier": "krail", "branch_lonlat": [[0, 0], [1, 1]]},
        {"id": "b", "treatment": "stub", "length_m": 15.0, "width_m": 10.0, "barrier": "type3", "branch_lonlat": [[0, 0], [1, 1]]},
        {"id": "c", "treatment": "skip"},
        {"id": "c", "treatment": "weird"}]}
    f = " | ".join(sr.validate_declaration(bad))
    assert "length_m 5.0" in f and "type3 is a PREVIEW" in f and "skip without a skip_reason" in f
    assert "duplicate id c" in f and "treatment 'weird'" in f


def test_no_declaration_touches_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        before = {p.name: p.read_bytes() for p in (proj / "data").iterdir()}
        assert sr.apply(proj) == 0
        after = {p.name: p.read_bytes() for p in (proj / "data").iterdir()}
        assert before == after


def test_apply_appends_the_stub_on_the_hosts_grade_into_the_3dep_grade():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        doc = sr.declare(proj, proj / "osm.json")
        for e in doc["stubs"]:
            if not (e["way"] == 2 and e["side"] == 1):
                e["treatment"], e["skip_reason"] = "skip", "test"
        (proj / "data" / "stubs.json").write_text(json.dumps(doc), encoding="utf-8")
        before = json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
        assert sr.apply(proj, sampler=_dem(0.07)) == 0
        for name in ("connectors.local.json", "connectors.local.json.pre-trim"):
            cs = json.loads((proj / "data" / name).read_text(encoding="utf-8"))["connectors"]
            assert cs[:len(before)] == before                        # every existing block untouched, in order
            assert [c["name"] for c in cs[len(before):]] == ["STUB_cross_street_2_L"]
        stub = cs[-1]
        assert stub["blend_m"] == 0.0 and stub["stub"]["id"] == "cross_street_2_L"
        plan = json.loads((proj / "data" / "stubs.plan.json").read_text(encoding="utf-8"))["stubs"][0]
        assert abs(plan["grade_3dep"] - 0.07) < 1e-3
        assert abs(plan["grade_host_along"]) < 1e-3                  # the host's grade has no component along a 90 deg stub
        # heights: on the host centreline at the cut, then the vertical curve, then the real grade
        P = stub["points_xyz_m"]
        cx, cz = plan["cut_xz"]
        u = [math.hypot(p[0] - cx, p[2] - cz) * (1 if p[2] > cz else -1) for p in P]
        hy = plan["host_y"]
        T = plan["vcurve_m"]
        assert abs(T - 1.5 * 0.07 / sr.RAMP_DG_PER_M) < 1e-2
        for uu, p in zip(u, P):
            assert abs(p[1] - sr.draft_y(uu, hy, 0.0, 0.07, T)) < 2e-3   # g0 = 0: the draft IS the finished profile
        far = [(uu, p[1]) for uu, p in zip(u, P) if uu > T + 1.0]
        g = (far[-1][1] - far[0][1]) / (far[-1][0] - far[0][0])
        assert abs(g - 0.07) < 1e-3
        # the barrier + tail: the last point is TAIL_M past the barrier, the barrier length_m past the mouth line
        assert abs(u[-1] - (plan["u_barrier_from_cut_m"] + sr.TAIL_M)) < 1e-3
        assert abs(plan["u_barrier_from_cut_m"] - plan["u_mouth_from_cut_m"] - sr.STUB_LENGTH_M) < 1e-6
        # a second apply is idempotent (the stub replaced, not doubled)
        assert sr.apply(proj, sampler=_dem(0.07)) == 0
        cs2 = json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
        assert [c["name"] for c in cs2] == [c["name"] for c in cs]


def test_ramp_never_changes_grade_faster_than_the_limit():
    for g0, g in ((0.0, 0.11), (0.05, -0.08), (-0.02, 0.0)):
        T = sr.ramp_length(g, g0)
        prev = None
        for k in range(0, int(T * 100) + 200):
            u = k / 100.0
            grade = (sr.profile_y(u + 1e-4, 0.0, g0, g, T) - sr.profile_y(u, 0.0, g0, g, T)) / 1e-4
            if prev is not None:
                assert abs(grade - prev) / 0.01 <= sr.RAMP_DG_PER_M * 1.01
            prev = grade
        assert abs(prev - g) < 1e-3


def test_a_stub_on_a_connector_host_from_an_expansion_mouths_leg():
    """phase 1's hookup: the host is a connector piece (an expansion road), the ways come from one leg of a mouths
    file; trim cuts the stub against that piece and records the mouth on it (pieces renamed <host>#k included)"""
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        north = {"name": "north_w", "kind": "connector",
                 "points_xyz_m": [[-150.0 + 3.0 * i, 2.0, 200.0] for i in range(101)], "widths_m": [16.0] * 101}
        for name in ("connectors.local.json", "connectors.local.json.pre-trim"):
            p = proj / "data" / name
            doc = json.loads(p.read_text(encoding="utf-8"))
            doc["connectors"].append(north)
            p.write_text(json.dumps(doc), encoding="utf-8")
        osm = json.loads((proj / "osm.json").read_text(encoding="utf-8"))
        hn = []
        for i in range(31):
            nid = 7000 + i
            osm["nodes"][str(nid)] = _ll(-150.0 + 10.0 * i, 200.0)
            hn.append(nid)
        osm["ways"].append({"id": 70, "nodes": hn, "tags": {"highway": "secondary", "name": "North Road"}})
        for nid, z in ((7101, 140.0), (7102, 260.0)):
            osm["nodes"][str(nid)] = _ll(30.0, z)
        osm["ways"].append({"id": 71, "nodes": [7101, 7018, 7102], "tags": {"highway": "residential", "name": "Glen"}})
        osm["ways"].append({"id": 72, "nodes": [7006, 7103], "tags": {"highway": "residential", "name": "Unlisted"}})
        osm["nodes"]["7103"] = _ll(-90.0, 250.0)
        (proj / "osm.json").write_text(json.dumps(osm), encoding="utf-8")
        mouths = Path(tmp) / "routes__mouths.json"
        mouths.write_text(json.dumps({"mouths": {"W": [{"way": 71, "node": 7018}]}}), encoding="utf-8")
        doc = sr.declare(proj, proj / "osm.json", "north_w", mouths_path=mouths, legs={"north_w": "W"})
        assert {e["way"] for e in doc["stubs"]} == {71}
        assert {e["side"] for e in doc["stubs"]} == {1, -1} and all(e["host"] == "north_w" for e in doc["stubs"])
        assert all(e["host_street"] == "North Road" for e in doc["stubs"])
        (proj / "data" / "stubs.json").write_text(json.dumps(doc), encoding="utf-8")
        assert sr.apply(proj, sampler=_dem(0.0)) == 0
        tc.build(proj)
        ms = [m for m in json.loads((proj / "data" / "mouths.json").read_text(encoding="utf-8"))["mouths"]
              if str(m["connector"]).startswith("STUB_glen_71")]
        assert len(ms) == 2 and all(m["host"] == "north_w" and m["end"] == "start" and m["piece"] for m in ms)


def test_draft_plus_the_welds_warp_is_the_finished_profile():
    """on a skewed stub off a graded host the weld lays the host's grade along the stub in (g0 u x its blend weight);
    the draft leaves exactly that out, so draft + warp == the finished profile (host grade at the mouth, 3DEP beyond)"""
    hy, g0, g = 5.0, 0.0387, 0.0404
    T = sr.ramp_length(g, g0)
    for k in range(0, 200):
        u = k * 0.1
        assert abs(sr.draft_y(u, hy, g0, g, T) + sr.weld_warp(u, g0) - sr.profile_y(u, hy, g0, g, T)) < 1e-12
    eps = 1e-5
    assert abs((sr.profile_y(eps, hy, g0, g, T) - sr.profile_y(0.0, hy, g0, g, T)) / eps - g0) < 1e-4


def test_trim_records_the_stub_mouth_keeps_its_profile_and_never_extends_its_dead_end():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        doc = sr.declare(proj, proj / "osm.json")
        for e in doc["stubs"]:
            if not (e["way"] == 2 and e["side"] == 1):
                e["treatment"], e["skip_reason"] = "skip", "test"
        (proj / "data" / "stubs.json").write_text(json.dumps(doc), encoding="utf-8")
        sr.apply(proj, sampler=_dem(0.07))
        pre = json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"][-1]
        tc.build(proj)
        cs = json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
        piece = next(c for c in cs if c["name"].startswith("STUB_cross_street_2_L"))
        mo = next(m for m in json.loads((proj / "data" / "mouths.json").read_text(encoding="utf-8"))["mouths"]
                  if m["connector"] == "STUB_cross_street_2_L")
        assert mo["piece"] == piece["name"] and mo["end"] == "start" and mo["side"] == 1
        assert piece["stub"]["id"] == "cross_street_2_L"
        # every point past the cut keeps its declared height (no 30 m blend), the far end stays where it was declared
        kept = {(round(p[0], 3), round(p[2], 3)): p[1] for p in pre["points_xyz_m"]}
        for p in piece["points_xyz_m"][1:]:
            assert abs(kept[(round(p[0], 3), round(p[2], 3))] - p[1]) < 1e-9
        assert piece["points_xyz_m"][-1] == pre["points_xyz_m"][-1]
        assert abs(piece["points_xyz_m"][0][1] - pre["points_xyz_m"][1][1]) < 0.05   # the cut lands on the profile


def test_a_side_street_whose_last_nodes_lie_inside_the_host_is_not_a_host_way():
    """ledger 0054 P3 repair round 1 (the view lens: "Glenroy St's mouths are not declared"): Glenroy St's south-west
    leg reaches Princess View on a short way with 3 of its 5 nodes inside the 22 m road, and was taken for a host
    carriageway (no entry at all). A host way must also run ALONG the host where it is on it"""
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        osm = json.loads((proj / "osm.json").read_text(encoding="utf-8"))

        def node(nid, x, z):
            osm["nodes"][str(nid)] = _ll(x, z)
            return nid
        # 5 nodes, the last three within HALF + HOST_REACH_M of the host, crossing it at 90 deg at x = 50
        osm["ways"].append({"id": 7, "nodes": [node(7001, 50.0, -60.0), node(7002, 50.0, -30.0), node(7003, 50.0, -9.0),
                                               node(7004, 50.0, -5.0), 1020],
                            "tags": {"highway": "residential", "name": "Short Leg"}})
        (proj / "osm.json").write_text(json.dumps(osm), encoding="utf-8")
        doc = sr.declare(proj, proj / "osm.json")
        legs = [e for e in doc["stubs"] if e["way"] == 7]
        assert legs and legs[0]["treatment"] == "stub" and legs[0]["side"] == -1, legs
        # the host itself is still the host (no entry for way 1)
        assert not [e for e in doc["stubs"] if e["way"] == 1]

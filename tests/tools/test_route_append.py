"""tools/route_append.py — append one route to data/routes.json, never regenerate (ledger 0054 P0 step 4).

- the existing routes stay byte-identical (the old file minus its closing brace is a prefix of the new one);
- a route that is already there is refused (append only);
- each leg is routed over ITS ways only, one-way tags respected, and must equal the spec's path_nodes;
- the committed data: `north` re-derives from the committed spec + OSM snapshot, and full / medium / short are the
  bytes they were before the append (md5 of the v0.18.0 file, 4a9e66f);
- tools/route_tracks.py refuses to overwrite routes.json.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACK = ROOT / "tracks" / "san-diego-lake-murray"
ROUTES_MD5_BEFORE = "10d266659533c2458224579b36eeaf1e"     # data/routes.json at 4a9e66f (v0.18.0 installed)


def _tool():
    spec = importlib.util.spec_from_file_location("_tool_route_append", ROOT / "tools" / "route_append.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _osm():
    # a little ladder: 1-2-3 on way 10 (two-way), 3-4 on way 11 (one-way 3->4), 4-5 on way 12 (one-way -1: 5->4),
    # and a parallel 1-6-3 on way 13 (two-way, longer)
    nodes = {1: (0.0, 0.0), 2: (0.001, 0.0), 3: (0.002, 0.0), 4: (0.003, 0.0), 5: (0.004, 0.0), 6: (0.001, 0.002)}
    ways = [{"id": 10, "nodes": [1, 2, 3], "tags": {"name": "A"}},
            {"id": 11, "nodes": [3, 4], "tags": {"name": "B", "oneway": "yes"}},
            {"id": 12, "nodes": [4, 5], "tags": {"name": "C", "oneway": "-1"}},
            {"id": 13, "nodes": [1, 6, 3], "tags": {"name": "A"}}]
    return {"nodes": {str(k): list(v) for k, v in nodes.items()}, "ways": ways, "source": "test",
            "osm_base": "2026-10-14T00:00:00Z", "fetched_utc": "2026-10-14T00:00:01Z"}


def _routes_file(d: Path) -> Path:
    p = d / "routes.json"
    p.write_text(json.dumps({"full": {"nodes": [1, 2], "coords": [[0.0, 0.0], [0.001, 0.0]], "km": 0.11},
                             "short": {"nodes": [2, 3], "coords": [[0.001, 0.0], [0.002, 0.0]], "km": 0.11}}),
                 encoding="utf-8")
    return p


def _spec(**over):
    s = {"name": "north", "junctions": {"fwd": {"J1": 1, "J2": 4}},
         "directions": {"fwd": {"legs": [{"leg": "A", "road": "A", "start_node": 1, "end_node": 3, "ways": [10],
                                          "path_nodes": [1, 2, 3]},
                                         {"leg": "B", "road": "B", "start_node": 3, "end_node": 4, "ways": [11]}]},
                        "rev": {"legs": [{"leg": "A", "road": "A", "start_node": 3, "end_node": 1, "ways": [13]}]}}}
    s.update(over)
    return s


def test_append_keeps_every_existing_byte_and_adds_the_route():
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        p = _routes_file(Path(t))
        before = p.read_bytes()
        rep = mod.append(p, _spec(), Path("osm.json"), _osm())
        assert not rep["fails"], rep["fails"]
        after = p.read_bytes()
        assert after[:len(before) - 1] == before[:-1] and len(after) > len(before)
        d = json.loads(after)
        assert list(d) == ["full", "short", "north"]
        n = d["north"]
        assert n["nodes"] == [1, 2, 3, 4] and n["coords"][0] == [0.0, 0.0] and n["km"] > 0
        assert n["rev"]["nodes"] == [3, 6, 1] and [L["road"] for L in n["legs"]["fwd"]] == ["A", "B"]
        assert n["junctions"] == {"fwd": {"J1": 1, "J2": 4}} and n["provenance"]["drive_order"] == "fwd"


def test_append_only_an_existing_name_is_refused():
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        p = _routes_file(Path(t))
        before = p.read_bytes()
        try:
            mod.append(p, _spec(name="full"), Path("osm.json"), _osm())
            raise AssertionError("an existing route was replaced")
        except SystemExit as e:
            assert "append only" in str(e.code)
        assert p.read_bytes() == before


def test_one_way_tags_are_respected_and_a_wrong_way_leg_fails():
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        p = _routes_file(Path(t))
        before = p.read_bytes()
        # 4 -> 3 on way 11 (one-way 3 -> 4) has no legal path; 4 -> 5 on way 12 (oneway=-1: only 5 -> 4) neither
        for leg in ({"start_node": 4, "end_node": 3, "ways": [11]}, {"start_node": 4, "end_node": 5, "ways": [12]}):
            sp = {"name": "x", "directions": {"fwd": {"legs": [dict(leg, leg="B", road="B")]}}}
            rep = mod.append(p, sp, Path("osm.json"), _osm())
            assert rep["fails"] and "no one-way-respecting path" in rep["fails"][0], rep
            assert p.read_bytes() == before
        # 5 -> 4 on way 12 is legal
        rep = mod.append(p, {"name": "y", "directions": {"fwd": {"legs": [
            {"leg": "C", "road": "C", "start_node": 5, "end_node": 4, "ways": [12]}]}}}, Path("osm.json"), _osm(),
            check=True)
        assert not rep["fails"]
        # a path that a router might produce but runs against a one-way edge is caught by the edge check
        snap = mod.Snapshot(_osm())
        assert snap.against_oneway([4, 3]) and not snap.against_oneway([3, 4]) and snap.against_oneway([4, 5])


def test_a_routed_path_that_differs_from_the_spec_stops_the_append():
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        p = _routes_file(Path(t))
        sp = _spec()
        sp["directions"]["fwd"]["legs"][0]["path_nodes"] = [1, 6, 3]      # the spec says the long way
        rep = mod.append(p, sp, Path("osm.json"), _osm())
        assert any("differs from the spec's path_nodes" in f for f in rep["fails"]), rep["fails"]
        sp = _spec()
        sp["directions"]["fwd"]["legs"][0]["ways"] = [10, 13]              # a spec way the path never uses
        rep = mod.append(p, sp, Path("osm.json"), _osm())
        assert any("never used" in f for f in rep["fails"]), rep["fails"]


def test_committed_routes_full_medium_short_are_the_v018_bytes_and_north_rederives():
    raw = (ROOT / "data" / "routes.json").read_bytes()
    d = json.loads(raw)
    assert list(d) == ["full", "medium", "short", "north"]
    old = {k: d[k] for k in ("full", "medium", "short")}
    old_bytes = json.dumps(old).encode("utf-8")
    assert hashlib.md5(old_bytes).hexdigest() == ROUTES_MD5_BEFORE
    assert raw[:len(old_bytes) - 1] == old_bytes[:-1]
    # north re-derives from the committed spec + snapshot (check mode on a copy holding the three old routes)
    mod = _tool()
    spec = json.loads((TRACK / "data" / "route.north.spec.json").read_text(encoding="utf-8"))
    osm = json.loads((TRACK / "data" / "osm.expansion.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "routes.json"
        p.write_bytes(old_bytes)
        spec["_spec_path"] = "tracks/san-diego-lake-murray/data/route.north.spec.json"
        rep = mod.append(p, spec, Path("tracks/san-diego-lake-murray/data/osm.expansion.json"), osm, check=True)
        assert not rep["fails"], rep["fails"]
        n = d["north"]
        snap = mod.Snapshot(osm)
        for sense in ("fwd", "rev"):
            nodes = n["nodes"] if sense == "fwd" else n["rev"]["nodes"]
            built = [x for L in spec["directions"][sense]["legs"] for x in L["path_nodes"]]
            dedup = [built[0]] + [x for a, x in zip(built, built[1:]) if not (x == a)]
            assert nodes == dedup, sense
            assert not snap.against_oneway(nodes), sense
        # J1 -> J5 clockwise, and J1 / J5 are the loop's own corners (College/Waring, Navajo/Jackson)
        assert n["junctions"]["fwd"]["J1"] in n["nodes"] and n["nodes"][-1] == n["junctions"]["fwd"]["J5"]
        assert [L["road"] for L in n["legs"]["fwd"]] == ["College Avenue", "Waring Road", "Princess View Drive",
                                                        "Mission Gorge Road", "Jackson Drive"]
        assert 6.3 <= n["km"] <= 6.45 and 6.3 <= n["rev"]["km"] <= 6.45


def test_route_tracks_refuses_to_overwrite_routes_json():
    src = (ROOT / "tools" / "route_tracks.py").read_text(encoding="utf-8")
    assert "--overwrite" in src and "append-only" in src
    # run it for real against the committed data: it must stop before writing (the result differs: north is there)
    before = (ROOT / "data" / "routes.json").read_bytes()
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "route_tracks.py")], cwd=str(ROOT),
                       capture_output=True, text=True, timeout=300)
    assert r.returncode != 0 and "append-only" in (r.stderr + r.stdout), (r.returncode, r.stderr[-500:])
    assert (ROOT / "data" / "routes.json").read_bytes() == before

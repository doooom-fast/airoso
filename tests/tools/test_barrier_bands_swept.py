"""tools/barrier_bands.py race.swept_mouths (ledger 0054 P1, opt-in) — the weld mouths of the north network on the
loop's outer edge, declared where they really open it (the piece's swept road edges, and the loop sidewalk gap
gap_mouths cuts), their policy per vertex (EXPANSION-PLAN A7's split).

On the track's own v0.18.0 data plus the authored weld stubs (data/expansion.north.json) cut by trim_connectors:
  * as rehearsed (welds[].connector): W1 (J1 Waring, Waring's straight curbs) opens v1514-v1520.4 and its sidewalk
    gap runs v1509-v1523, past race_cw's box-end pin v1521: in race_cw (far side) v...-1521 is sealed_far_strip and
    v1522-1523 behind_closure (the A7 split); in race_acw (race side) one sealed_race_strip row. W5 (J5) opens
    v2313.5-v2320.9 inside box 2311-2328; its sidewalk gap starts at v2310, the closure vertex before the box pin;
  * with W1's full flare (welds[].connector_full, the R 30 return the P3 apron carries) the far-side split runs to
    ~v1525: the machinery holds the wider opening too, not only the rehearsed stub;
  * probes cross each opening at 3 m and 10 m past the edge, one past v1521 in both layouts;
  * every self-gate passes and the PLANNED no-route fill holds both layouts (0 leaks, no probe reached);
  * the existing three mouths' rows and probes are exactly those of the same build without the key, and a split
    row declared with the wrong policy fails self-gate 7.
Plain ``test_*`` for tests/run_tests.py (one planned build, ~30 s).
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import barrier_bands as bb  # noqa: E402

TRACK = ROOT / "tracks" / "san-diego-lake-murray"
KERB_DROPS = [{"apex": 1514, "kind": "outside", "drop": True, "why": "test: inside the W1 opening"},
              {"apex": 2319, "kind": "outside", "drop": True, "why": "test: inside the W5 opening"}]


def _load(stem):
    spec = importlib.util.spec_from_file_location(f"_t_{stem}", ROOT / "tools" / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _project(full: bool = False) -> Path:
    """the v0.18.0 track data + the two weld stubs (full: W1's whole opening), trimmed at the loop edge"""
    rc = _load("route_connectors")
    trim = _load("trim_connectors")
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    for f in ("centerline.local.json", "median_bands.json", "bridge.spans.auto.json"):
        shutil.copyfile(TRACK / "data" / f, d / "data" / f)
    base = json.loads((TRACK / "data" / "connectors.local.json.pre-trim").read_text(encoding="utf-8"))
    local = json.loads((TRACK / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    with contextlib.redirect_stdout(io.StringIO()):
        stubs = rc._authored_take("north", TRACK / "data" / "expansion.north.json", ["W1", "W5"], local)
    if full:
        doc = json.loads((TRACK / "data" / "expansion.north.json").read_text(encoding="utf-8"))
        cf = next(w for w in doc["welds"] if w["id"] == "W1")["connector_full"]
        y = rc._despike_smooth_cap([q[1] for q in cf["points_xyz_m"]], rc.RESAMPLE_M)
        stubs[0] = {"name": cf["name"], "kind": "connector", "widths_m": list(cf["widths_m"]),
                    "points_xyz_m": [[q[0], round(yy, 3), q[2]] for q, yy in zip(cf["points_xyz_m"], y)]}
    base["connectors"] = list(base["connectors"]) + stubs
    (d / "data" / "connectors.local.json").write_text(json.dumps(base), encoding="utf-8")
    cfg = json.loads((TRACK / ".p1-rehearsal.bak" / "track.config.json").read_text(encoding="utf-8")) \
        if (TRACK / ".p1-rehearsal.bak").exists() else json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()):
        trim.build(d)
    return d


def _cfg(proj: Path, swept: bool) -> Path:
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    cfg["race"]["kerbs"]["trims"] = [t for t in cfg["race"]["kerbs"]["trims"]
                                     if not (t.get("kind") == "outside" and t.get("apex") in (1514, 2319))] + KERB_DROPS
    if swept:
        cfg["race"]["swept_mouths"] = ["north_"]
    else:
        cfg["race"].pop("swept_mouths", None)
    p = proj / ("cfg_swept.json" if swept else "cfg_plain.json")
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


_C = {}


def _decl():
    if not _C:
        proj = _project()
        pf = _project(full=True)
        with contextlib.redirect_stdout(io.StringIO()):
            _C["swept"] = bb.build(proj, config_path=_cfg(proj, True), planned_no_route=True, write=False)
            _C["plain"] = bb.build(proj, config_path=_cfg(proj, False), planned_no_route=False, write=False)
            _C["full"] = bb.build(pf, config_path=_cfg(pf, True), planned_no_route=False, write=False)
    return _C


def _rows(decl, lid, conn):
    return [r for r in decl["corridors"][lid]["mouths"] if r["connector"].startswith(conn)]


def test_the_swept_declaration_passes_every_self_gate_and_the_planned_fill():
    d = _decl()["swept"]
    assert d["fails"] == [], d["fails"]
    for lid in ("race_cw", "race_acw"):
        pr = d["corridors"][lid]["no_route"]["planned"]
        assert pr["fail"] is False and pr["leak_m2"] == 0 and not pr["forbidden_reached"] and not pr["blocked"], (lid, pr)


def test_w1_splits_at_race_cws_pin_and_is_one_race_strip_row_in_race_acw():
    d = _decl()["swept"]
    sw = next(m for m in d["closed_mouths"] if m["connector"] == "north_J1_waring")["swept"]
    assert 1513 <= sw["edge_vertex_from"] <= 1515.5 and 1519.5 <= sw["edge_vertex_to"] <= 1521.5, sw
    assert sw["vertex_to"] >= 1522, sw                                    # the sidewalk gap runs past the pin
    cw = _rows(d, "race_cw", "north_J1_waring")
    assert [r["policy"] for r in cw] == ["sealed_far_strip", "behind_closure"], cw
    assert cw[0]["vertex_to"] == 1521 and cw[1]["vertex_from"] == 1522, cw
    assert all(r["split"]["of"] == 2 for r in cw)
    acw = _rows(d, "race_acw", "north_J1_waring")
    assert [r["policy"] for r in acw] == ["sealed_race_strip"] and acw[0]["vertex_to"] >= 1522, acw


def test_w1_full_flare_splits_the_same_way_to_its_sidewalk_gap():
    d = _decl()["full"]
    assert d["fails"] == [], d["fails"]
    sw = next(m for m in d["closed_mouths"] if m["connector"] == "north_J1_waring")["swept"]
    # trimmed at its centre crossing, the full flare's NE edge runs on straight to ~v1523 (the same limit the weld
    # meets); its sidewalk gap reaches ~v1525: the declaration follows the geometry the chain would build
    assert 1522.5 <= sw["edge_vertex_to"] <= 1530 and sw["vertex_to"] >= 1525, sw
    cw = _rows(d, "race_cw", "north_J1_waring")
    assert [r["policy"] for r in cw] == ["sealed_far_strip", "behind_closure"], cw
    assert cw[0]["vertex_to"] == 1521 and cw[1]["vertex_to"] >= 1525, cw


def test_w5_opens_inside_its_box_in_both_layouts():
    d = _decl()["swept"]
    sw = next(m for m in d["closed_mouths"] if m["connector"] == "north_J5_jackson_north")["swept"]
    assert 2311 <= sw["edge_vertex_from"] and sw["edge_vertex_to"] <= 2323, sw
    acw = _rows(d, "race_acw", "north_J5_jackson_north")
    assert [x["policy"] for x in acw] == ["sealed_race_strip"], acw
    cw = _rows(d, "race_cw", "north_J5_jackson_north")
    far = [x for x in cw if x["policy"] == "sealed_far_strip"]
    assert len(far) == 1 and far[0]["vertex_from"] <= 2312 and far[0]["vertex_to"] <= 2328, cw
    for x in cw:                                        # anything outside the box is behind race_cw's closure
        if x["policy"] != "sealed_far_strip":
            assert x["policy"] == "behind_closure" and x["vertex_to"] < 2311, cw


def test_probes_cross_the_openings_past_v1521_in_both_layouts():
    d = _decl()["swept"]
    for lid in ("race_cw", "race_acw"):
        pr = [p for p in d["corridors"][lid]["no_route"]["forbidden_probes"] if "north_J1_waring" in p["why"]]
        past = [p for p in pr if p["vertex"] > 1521]
        assert past and {round(abs(p["y"]) - 15.0) for p in past} >= {3, 10}, (lid, pr)
        assert any("north_J5_jackson_north" in p["why"] for p in d["corridors"][lid]["no_route"]["forbidden_probes"])


def test_the_key_changes_only_the_swept_mouths():
    s, p = _decl()["swept"], _decl()["plain"]
    for lid in ("race_cw", "race_acw"):
        old = [r for r in p["corridors"][lid]["mouths"] if not r["connector"].startswith("north_")]
        new = [r for r in s["corridors"][lid]["mouths"] if not r["connector"].startswith("north_")]
        assert old == new and len(old) >= 3
        po = [q for q in p["corridors"][lid]["no_route"]["forbidden_probes"] if "north_" not in q["why"]]
        ps = [q for q in s["corridors"][lid]["no_route"]["forbidden_probes"] if "swept mouth" not in q["why"]
              and "north_" not in q["why"]]
        assert po == ps
    assert not any("swept" in m for m in p["closed_mouths"])


def test_a_split_row_with_the_wrong_policy_fails_self_gate_7():
    out = _decl()["swept"]
    bad = copy.deepcopy({k: v for k, v in out.items() if k != "_ctx"})
    for r in bad["corridors"]["race_cw"]["mouths"]:
        if r["connector"] == "north_J1_waring" and r["policy"] == "behind_closure":
            r["policy"] = "sealed_far_strip"
    fails = bb.validate(bad, out["_ctx"])
    assert any("north_J1_waring" in f and "needs behind_closure" in f for f in fails), fails

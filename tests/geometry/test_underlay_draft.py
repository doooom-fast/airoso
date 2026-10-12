"""scripts/geometry/underlay_draft.py — the data half of scripts/blender/underlay.py (V3-PLAN P2 step 3), no Blender.

The cross sections are the engine ribbon's (parity with ribbon.road_ribbon), carry the crown / crossfall from data,
the verge is the D4 switch and sits flush and level on the pavement edge, every drivable face is wound up, the refs
find the stacked legs, and nothing the underlay emits is a highway, a mountain or a lamp. Opt-in: no other pipeline
module reaches it, so every other track's output is byte-identical (nothing existing was edited).
"""
from __future__ import annotations

import importlib.util
import json
import math
import tempfile
from pathlib import Path

from scripts.geometry import ribbon
from scripts.geometry import underlay_draft as ud

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("underlay_fixture", Path(__file__).with_name("underlay_fixture.py"))
fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fx)


def _proj(**kw):
    return fx.write_project(Path(tempfile.mkdtemp()) / "proj", **kw)


def _refused(fn, needle):
    try:
        fn()
    except SystemExit as e:
        assert needle in str(e.code), (needle, e.code)
        return
    raise AssertionError(f"not refused: {needle}")


def test_edges_are_the_engine_ribbon_when_flat():
    """crown 0, no tilt: the left/right edges are ribbon.road_ribbon's vertices exactly (same tangent, same fold
    guard), so GEN_road is 'the engine ribbon', with a centre row added for the crown."""
    pts = fx.loop_points()
    w = [6.5] * len(pts)
    n = len(pts)
    secs, closed = ud.sections(pts, w, [0.0] * n, [0.0] * n, 0.0)
    rib = ribbon.road_ribbon(pts, w)
    assert closed and len(secs) * 2 == len(rib["vertices"])
    for i, sec in enumerate(secs):
        for got, want in ((sec[0], rib["vertices"][2 * i]), (sec[2], rib["vertices"][2 * i + 1])):
            assert all(abs(a - b) < 1e-9 for a, b in zip(got, want)), (i, got, want)
    # a tilt is the ribbon's bank_at exactly
    b = 0.03
    secs, _ = ud.sections(pts, w, [b] * n, [0.0] * n, 0.0)
    rib = ribbon.road_ribbon(pts, w, bank_at=lambda s: b)
    for i in (0, 57, 300):
        assert abs(secs[i][0][1] - rib["vertices"][2 * i][1]) < 1e-9
        assert abs(secs[i][2][1] - rib["vertices"][2 * i + 1][1]) < 1e-9


def test_crown_is_the_construction_standard_without_crossfall_data():
    p = _proj()
    d = ud.build(p, with_terrain=False)
    assert "2 % crown everywhere" in d["report"]["road"]["crossfall"]
    inp = ud.load_inputs(p)
    cf = ud.crossfall_plan(inp)
    secs, _ = ud.sections(inp["pts"], inp["widths"], cf["bank"], cf["crown"], 0.4)
    left, centre, right = secs[10][0], secs[10][1], secs[10][2]
    assert abs((centre[1] - left[1]) - 0.02 * 3.25) < 1e-9 and abs((centre[1] - right[1]) - 0.02 * 3.25) < 1e-9


def test_crossfall_file_tilts_and_crowns_only_the_flat_stations():
    cf = {"station_m": [0.0, 300.0, 301.0, 2000.0], "bank_rad": [0.0, 0.0, 0.04, 0.04]}
    p = _proj(crossfall=cf)
    inp = ud.load_inputs(p)
    plan = ud.crossfall_plan(inp)
    st = ud.arcs(inp["pts"])
    i_flat = next(i for i, s in enumerate(st) if s > 100)
    i_tilt = next(i for i, s in enumerate(st) if s > 500)
    assert plan["bank"][i_flat] == 0.0 and abs(plan["crown"][i_flat] - 0.02) < 1e-12
    assert abs(plan["bank"][i_tilt] - 0.04) < 1e-12 and plan["crown"][i_tilt] == 0.0
    secs, _ = ud.sections(inp["pts"], inp["widths"], plan["bank"], plan["crown"], 0.0)
    l, c, r = secs[i_tilt][:3]
    assert abs((l[1] - c[1]) - 3.25 * math.tan(0.04)) < 1e-9 and abs((c[1] - r[1]) - 3.25 * math.tan(0.04)) < 1e-9
    # mirror_x flips the sign, as build_mesh does
    cfg = json.loads((p / "track.config.json").read_text())
    cfg["mirror_x"] = True
    (p / "track.config.json").write_text(json.dumps(cfg))
    assert abs(ud.crossfall_plan(ud.load_inputs(p))["bank"][i_tilt] + 0.04) < 1e-12
    # an explicit crown_pct list wins
    cf["crown_pct"] = [1.5, 1.5, 0.0, 0.0]
    (p / "data" / "crossfall.json").write_text(json.dumps(cf))
    assert abs(ud.crossfall_plan(ud.load_inputs(p))["crown"][i_flat] - 0.015) < 1e-12
    cf["crown_pct"] = [1.5]
    (p / "data" / "crossfall.json").write_text(json.dumps(cf))
    _refused(lambda: ud.crossfall_plan(ud.load_inputs(p)), "crown_pct must be a list parallel")


def test_verge_is_the_d4_switch_flush_and_level():
    for variant, want, mode in ((None, 0.4, "D4 A"), ("a_real_edge", 0.4, "D4 A"), ("b_verge", 1.25, "D4 B")):
        d = ud.build(_proj(), variant, with_terrain=False)
        assert d["verge"]["width_m"] == want and d["verge"]["mode"].startswith(mode), (variant, d["verge"])
        road = d["meshes"]["road"][ud.ROAD_NAME]["vertices"]
        verge = d["meshes"]["verge"][ud.VERGE_NAME]["vertices"]
        m = len(road) // 3
        for i in (5, 50, 150):                          # straight leg 1: inner = road edge, outer = edge + verge, level
            for side, col in ((0, 0), (1, 2)):
                inner, outer = verge[side * 2 * m + 2 * i], verge[side * 2 * m + 2 * i + 1]
                assert inner == road[3 * i + col], (variant, i, side)
                assert abs(math.hypot(outer[0] - inner[0], outer[1] - inner[1]) - want) < 1e-6
                assert outer[2] == inner[2]               # level: no lip, no fall
    # the config is never written by a variant
    p = _proj()
    before = (p / "track.config.json").read_bytes()
    ud.build(p, "b_verge", with_terrain=False)
    assert (p / "track.config.json").read_bytes() == before
    _refused(lambda: ud.build(p, "c_nope", with_terrain=False), "not in track.config.json drive1_variants")
    _refused(lambda: ud.build(_proj(verge_m=0.8), with_terrain=False), "neither D4 A")
    _refused(lambda: ud.build(_proj(verge_m=6.4), with_terrain=False), "is not a verge")
    assert ud.build(_proj(verge_m=0), with_terrain=False)["meshes"].get("verge") is None


def test_every_drivable_face_is_wound_up_and_none_degenerate():
    d = ud.build(_proj(verge_m=1.25))
    for role, name in (("road", ud.ROAD_NAME), ("verge", ud.VERGE_NAME), ("terrain", ud.TERRAIN_NAME)):
        mesh = d["meshes"][role][name]
        v = mesh["vertices"]
        assert mesh["faces"], role
        for a, b, c in mesh["faces"]:
            assert ud._tri_nz(v[a], v[b], v[c]) > 0, (role, a, b, c)
    # face_up fixes a down-wound triangle and drops a zero-area one
    v = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (2, 0, 0)]
    assert ud.face_up(v, [(0, 2, 1), (0, 1, 3)]) == [(0, 1, 2)]


def test_terrain_is_the_engine_heightfield_placeholder():
    p = _proj()
    d = ud.build(p)
    t = d["report"]["terrain"]
    assert t["placeholder"] is True and "P3a" in t["replaced_by"] and t["cell_m"] == 20.0
    meta = json.loads((p / "data" / "heightfield.meta.json").read_text())
    nx, ny = (meta["nx"] - 1) * 2 + 1, (meta["ny"] - 1) * 2 + 1
    assert t["grid"] == [nx, ny]
    rf = t["refine"]
    assert rf["factor"] == 8 and rf["sub_cell_m"] == 2.5 and rf["quads"] > 0 and rf["pinned"] > 0
    terr = d["meshes"]["terrain"][ud.TERRAIN_NAME]["vertices"]
    # far from the road the elevation is the survey's (the engine path with no pavement), untouched
    raw = ud.terrain_mesh(ud.load_inputs(p), [])["vertices"]
    road = d["meshes"]["road"][ud.ROAD_NAME]["vertices"]
    far = [k for k, v in enumerate(terr[:nx * ny]) if min(abs(v[1] - r[1]) + abs(v[0] - r[0]) for r in road[::30]) > 60]
    assert len(far) > 100 and all(terr[k] == raw[k] for k in far)
    assert t["refine"]["edge_clamped"] > 0 and t["refine"]["coarse_repinned"] > 0     # the hillside bites both ways
    # no ground above the pavement anywhere: at every road / verge face centre, the highest terrain surface over
    # that point sits at least GROUND_CLEAR_M (to rounding) under the pavement
    tmesh = d["meshes"]["terrain"][ud.TERRAIN_NAME]
    th = ud._Pavement([tmesh])

    def highest_terrain(x, n):
        hi = None
        for k in th.hash.get((int(x // th.CELL), int(n // th.CELL)), ()):
            a, b, c = th.tris[k]
            dd = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(dd) < 1e-12:
                continue
            w0 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (n - c[1])) / dd
            w1 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (n - c[1])) / dd
            if w0 >= -1e-9 and w1 >= -1e-9 and 1 - w0 - w1 >= -1e-9:
                z = w0 * a[2] + w1 * b[2] + (1 - w0 - w1) * c[2]
                hi = z if hi is None else max(hi, z)
        return hi
    checked = 0
    for role, name in (("road", ud.ROAD_NAME), ("verge", ud.VERGE_NAME)):
        m = d["meshes"][role][name]
        v = m["vertices"]
        for f in m["faces"][::3]:
            cx, cy, cz = (sum(v[i][k] for i in f) / 3 for k in range(3))
            hi = highest_terrain(cx, cy)
            assert hi is not None and hi <= cz - ud.GROUND_CLEAR_M + 0.01, (role, cx, cy, cz, hi)
            checked += 1
    assert checked > 1000
    (p / "data" / "heightfield.npy").unlink()
    _refused(lambda: ud.build(p), "heightfield.npy")


def test_refs_find_the_stacked_legs_corners_and_boxes():
    d = ud.build(_proj(), with_terrain=False)
    r = d["refs"]
    assert r["closed"] and abs(r["lap_m"] - 878.5) < 1.0
    assert [s["name"] for s in r["stations"]][:3] == ["REF_st_00000", "REF_st_00100", "REF_st_00200"]
    assert [c["id"] for c in r["corners"]] == ["C1", "C2", "C9"]
    assert r["corners"][0]["radius_m"] == 12.5 and r["corners"][2]["source"] == "race.corridor.boxes"
    box = r["boxes"][0]
    assert box["name"] == "REF_race_box_C9" and len(box["ring"]) == 2 * 21
    pairs = r["pairs"]
    assert len(pairs) > 100
    st = ud.arcs(fx.loop_points())
    lap = st[-1]
    for i, j, plan, dy in pairs:
        along = abs(st[i] - st[j])
        assert min(along, lap - along) > 150 and plan < 40
    assert 24.9 < min(p[2] for p in pairs) < 25.2 and 5.5 < max(abs(p[3]) for p in pairs) < 6.5


def test_nothing_but_the_lap_road_and_ground():
    d = ud.build(_proj())
    names = [n for role in d["meshes"].values() for n in role]
    assert names == [ud.ROAD_NAME, ud.VERGE_NAME, ud.TERRAIN_NAME]
    assert set(d["meshes"]) == {"road", "verge", "terrain"}            # no buildings role in Drive 1
    for bad in ("HIGHWAY_i70", "HWYSTRUCT_c470", "MOUNTAINS", "LAMP_post", "LIGHTS", "AUTH_road", "BUILDING_x"):
        _refused(lambda b=bad: ud.check_names([b]), "refusing to emit")
    ud.check_names(["1ROAD_road", "1RUNOFF_verge", "1GRASS_terrain_placeholder", "REF_centreline"])


def test_deterministic():
    p = _proj()
    a, b = ud.build(p), ud.build(p)
    for role in a["meshes"]:
        for name in a["meshes"][role]:
            assert ud.mesh_digest(a["meshes"][role][name]) == ud.mesh_digest(b["meshes"][role][name])
    assert a["report"] == b["report"]


def test_opt_in_only_the_underlay_reaches_it():
    """Engine changes are opt-in per track: nothing existing imports the new module, and only the Lariat's ship.json
    names the underlay step, so every other track's output is byte-identical (no existing engine file was edited)."""
    users = [p.relative_to(ROOT).as_posix() for p in (ROOT / "scripts").rglob("*.py")
             if "underlay_draft" in p.read_text(encoding="utf-8", errors="replace")
             and p.name != "underlay_draft.py"]
    assert users == ["scripts/blender/underlay.py"], users
    steps = {}
    for sj in (ROOT / "tracks").glob("*/ship.json"):
        spec = json.loads(sj.read_text(encoding="utf-8"))
        steps[sj.parent.name] = "underlay" in sum(spec.get("steps", {}).values(), [])
    assert [t for t, on in steps.items() if on] == ["lookout-lariat"], steps

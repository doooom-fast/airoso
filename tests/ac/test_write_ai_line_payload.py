"""Ledger 0052 — the race AI lines aimed at the K-rail, braked for bends that were not there, and carried five
payload fields in a meaning no reference line uses. Pinned here:

* a project WITHOUT ``track.config.json`` ``ai`` (or a layout not in ``ai.layouts``) writes every file
  byte-identical to the writer before ledger 0052 (golden md5s of the two end-to-end fixtures of
  test_ai_corridor / test_write_ai_line_layouts, computed with HEAD 5ccf20b's writer);
* with the opt-in, on a synthetic BUILT gate OBJ (walls standing on the corridor faces, a tilted road): the
  payload carries AC's meaning (segment length, direction +-1 from the LOCAL turn, the built normal, the camber
  measured toward the bend = -direction x asin(normal . right), the plain 3-point radius, a 0/0 header), the
  line keeps wall_clear off the built walls, has no spurious speed dips, its sides never reach past a built wall,
  every box keeps >= 0.85 x the arc the v0.17.1 rule lays there, and tools/verify_ai_line.py passes it (with the
  legacy line as --baseline) while it fails the legacy line;
* the gate's V1 accepts what AC's own lines carry (the recorder's seam point, a spacing gap) and refuses the
  plain-asin camber sign, a one-point length error and a direction window wider than the local turn; V6 refuses
  a corner tightened below 0.85 x the baseline's;
* the pieces: the banded solver, fair_line (takes a wiggle out, never crosses a bound), the gate OBJ reader
  (wall footprints, layer filter, rays, the road surface), load_ai_opts' refusals, the stale-OBJ guard.

Plain ``test_*`` for tests/run_tests.py (no pytest fixtures).
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

from scripts.ac import ai_built as ab
from scripts.ac import write_ai_line as w

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import verify_ai_line as gate  # noqa: E402


def _load(p: Path):
    spec = importlib.util.spec_from_file_location(p.stem + "_0052", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CORR = _load(ROOT / "tests" / "ac" / "test_ai_corridor.py")
LAY = _load(ROOT / "tests" / "ac" / "test_write_ai_line_layouts.py")

# every file the writer emitted for the two fixtures before ledger 0052 (HEAD 5ccf20b, this PC — Windows).
# The bytes are platform-specific in two ways, so each platform keeps its own table: text files (.csv, ai_draft.json)
# carry the platform's newline, and the v2 corridor fixture's trig lands a last-ulp apart between the MS UCRT libm
# and glibc, which moves the packed .ai floats and the json's float repr. The v1 .ai files agree everywhere.
GOLDEN = {
    "v2/race_cw/ai_draft.json": "be69544c02104d3bfb6ea0cfd8dde33b",
    "v2/race_cw/fast_lane.ai": "f24910802d817769a88cbeb59b578062",
    "v2/race_cw/pit_lane.ai": "f24910802d817769a88cbeb59b578062",
    "v2/race_cw/side_l.csv": "4ff85732e8ba85189f86f1e859f37cc1",
    "v2/race_cw/side_r.csv": "3b15544b0874a1827199e3cc4bc17fe8",
    "v2/race_acw/ai_draft.json": "5c470065bc7c953a2e9c7cd5b94c42d7",
    "v2/race_acw/fast_lane.ai": "29799876619f2f655b9d4a42ef163d8e",
    "v2/race_acw/pit_lane.ai": "29799876619f2f655b9d4a42ef163d8e",
    "v2/race_acw/side_l.csv": "edddf418b8acfa62ef8c05515f28a931",
    "v2/race_acw/side_r.csv": "63ecb0f557648bde7d1938e968f22a21",
    "v1/race_cw/ai_draft.json": "27c3c4ae1d52586a6286996d3e98faa6",
    "v1/race_cw/fast_lane.ai": "971869bafbdd52fff5637286c54d32a3",
    "v1/race_cw/pit_lane.ai": "971869bafbdd52fff5637286c54d32a3",
    "v1/race_cw/side_l.csv": "257be9271e395661f2d79202941e7e82",
    "v1/race_cw/side_r.csv": "270817d5f64ecaeabff20b26a461cf08",
    "v1/race_acw/ai_draft.json": "933e43c6cf2642a343b32c4b104c3196",
    "v1/race_acw/fast_lane.ai": "3ee36ca9bc3cc78dd42269c2780bc75e",
    "v1/race_acw/pit_lane.ai": "3ee36ca9bc3cc78dd42269c2780bc75e",
    "v1/race_acw/side_l.csv": "52daf852b04f0e889f3cfaddb08dc3c5",
    "v1/race_acw/side_r.csv": "e3319ec61b3b13888f5dc1ac7fccedd0",
    "v1/street/ai_draft.json": "f63933c9ea6240d881e6983120d16ed1",
    "v1/street/fast_lane.ai": "d873fa99c8a76f427445da87adfadc06",
    "v1/street/pit_lane.ai": "d873fa99c8a76f427445da87adfadc06",
    "v1/street/side_l.csv": "ada964b587dc5b4ab0066d7889cf2002",
    "v1/street/side_r.csv": "48886d0eec618d419aaa21738da49393",
}

# the same files from the same writer on Linux/glibc (recorded 2026-10-28, identical under CPython 3.11 and 3.13)
GOLDEN_LINUX = {
    "v2/race_cw/ai_draft.json": "b21e9fd0ecefb28f516adfba39bf60b9",
    "v2/race_cw/fast_lane.ai": "6d46075f9ca5bb56300cc71b8c6faf6a",
    "v2/race_cw/pit_lane.ai": "6d46075f9ca5bb56300cc71b8c6faf6a",
    "v2/race_cw/side_l.csv": "cf4917858fdfc2a6cd01e31e640be346",
    "v2/race_cw/side_r.csv": "6761a632b9d4ce96b8a2778b7635c0a7",
    "v2/race_acw/ai_draft.json": "62f1362ca739f1be63577c2e9b55cb3a",
    "v2/race_acw/fast_lane.ai": "46c968981e0de38e7ac6ff6d3277e09c",
    "v2/race_acw/pit_lane.ai": "46c968981e0de38e7ac6ff6d3277e09c",
    "v2/race_acw/side_l.csv": "d495532e14b9d4f0556543583f59ef01",
    "v2/race_acw/side_r.csv": "38425ee948e863886e1cf34f9614da32",
    "v1/race_cw/ai_draft.json": "98c7b37762bf736a4fd755f1e46fd859",
    "v1/race_cw/fast_lane.ai": "971869bafbdd52fff5637286c54d32a3",
    "v1/race_cw/pit_lane.ai": "971869bafbdd52fff5637286c54d32a3",
    "v1/race_cw/side_l.csv": "f79e2c82325bf3179dbfe2353665e1b3",
    "v1/race_cw/side_r.csv": "da983567a95831671ee9f437b10a5882",
    "v1/race_acw/ai_draft.json": "ec294ce6d7ca076a29f6c0729fc8dd70",
    "v1/race_acw/fast_lane.ai": "3ee36ca9bc3cc78dd42269c2780bc75e",
    "v1/race_acw/pit_lane.ai": "3ee36ca9bc3cc78dd42269c2780bc75e",
    "v1/race_acw/side_l.csv": "f5c0a3f0f19e273824e8bbc9b473d76b",
    "v1/race_acw/side_r.csv": "dcd442de36a875a2978b44b486cd4e36",
    "v1/street/ai_draft.json": "4f6ef44114afc4316a72eeacf06b771b",
    "v1/street/fast_lane.ai": "d873fa99c8a76f427445da87adfadc06",
    "v1/street/pit_lane.ai": "d873fa99c8a76f427445da87adfadc06",
    "v1/street/side_l.csv": "d8dcb9962e01eedc066c748f31d35578",
    "v1/street/side_r.csv": "8956d391fc2ddaa038b54a7d4711471d",
}


def _golden() -> dict | None:
    """this platform's recorded bytes, or None where none were recorded (macOS: libm differs again)"""
    return {"win32": GOLDEN, "linux": GOLDEN_LINUX}.get(sys.platform)

OPTS = {"_note": "ledger 0052", "layouts": ["race_cw", "race_acw"], "payload": "kunos", "wall_clear_m": 2.5,
        "fair": True, "surface": "gate_obj"}
TILT = (0.006, 0.003)               # the synthetic road: y = 0.006 x + 0.003 z (engine frame; within 2 m of the
                                    # centreline's y = 0 everywhere on the 400 m square — ai_built.SURFACE_BAND_M 3)


def _quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


def _md5s(ai_dir: Path, prefix: str) -> dict:
    return {f"{prefix}/{f.name}": hashlib.md5(f.read_bytes()).hexdigest() for f in sorted(ai_dir.iterdir())}


def _set_ai(d: Path, block: dict | None) -> None:
    p = d / "track.config.json"
    cfg = json.loads(p.read_text())
    if block is None:
        cfg.pop("ai", None)
    else:
        cfg["ai"] = block
    p.write_text(json.dumps(cfg))


def _gate_obj(d: Path, layout: str, *, walls: bool = True) -> Path:
    """data/track.<layout>.obj for the rounded-square race fixture: a tilted 1ROAD plane under everything and a
    1 m-high 1WALL standing on each of the layout's two corridor faces (engine frame, like kn5_to_gate_obj)."""
    bands = json.loads((d / "data" / "barrier_bands.json").read_text())
    fin = json.loads((d / "data" / "finished_centerline.json").read_text())["points_xyz_m"][:-1]
    lane = [tuple(r) for r in bands["corridors"][layout]["lane_by_vertex"]]
    faces = w.CorridorFaces(fin, lane, closed=True)
    ys = lambda x, z: TILT[0] * x + TILT[1] * z      # noqa: E731
    out = ["# gate OBJ extracted from sq.kn5 (kn5->engine frame, z mirrored, winding reversed)", "o 1ROAD_road"]
    E = 400.0
    for x, z in ((-E, -E), (E, -E), (E, E), (-E, E)):
        out.append(f"v {x} {ys(x, z)} {z}")
    out += ["f 1 3 2", "f 1 4 3"]
    nv = 4
    if walls:
        for name in ("hi", "lo"):
            line = faces.polyline(name)
            out.append(f"o 1WALL_race_{name}")
            for k in range(len(line)):
                (ax, az), (bx, bz) = line[k], line[(k + 1) % len(line)]
                ya, yb = ys(ax, az), ys(bx, bz)
                out += [f"v {ax} {ya - 0.2} {az}", f"v {bx} {yb - 0.2} {bz}", f"v {bx} {yb + 1.0} {bz}", f"v {ax} {ya + 1.0} {az}"]
                out += [f"f {nv + 1} {nv + 2} {nv + 3}", f"f {nv + 1} {nv + 3} {nv + 4}"]
                nv += 4
    p = d / "data" / f"track.{layout}.obj"
    p.write_text("\n".join(out) + "\n")
    return p


# --- today's bytes without the opt-in -----------------------------------------------------------------------

def test_without_the_ai_block_every_file_is_todays_bytes():
    golden = _golden()
    if golden is None:
        print(f"  (no golden bytes recorded for {sys.platform} — byte check skipped)")
        return
    with tempfile.TemporaryDirectory() as td:
        got = {}
        d = CORR._v2_project(Path(td) / "v2")
        for lid in ("race_cw", "race_acw"):
            _quiet(w.main, [str(d), "--layout", lid])
            got.update(_md5s(d / "ai" / lid, f"v2/{lid}"))
        d1 = LAY._project(Path(td) / "v1", layouts=LAY._LAYOUTS)
        for lid in ("race_cw", "race_acw", "street"):
            _quiet(w.main, [str(d1), "--layout", lid])
            got.update(_md5s(d1 / "ai" / lid, f"v1/{lid}"))
        assert got == golden, sorted(k for k in golden if got.get(k) != golden[k])
        # an ai block that lists only the race layouts leaves the street layout's files byte-identical
        _set_ai(d1, dict(OPTS, layouts=["race_cw", "race_acw"]))
        _quiet(w.main, [str(d1), "--layout", "street"])
        assert _md5s(d1 / "ai" / "street", "v1/street") == {k: v for k, v in golden.items() if k.startswith("v1/street/")}


# --- the opt-in, end to end on a synthetic BUILT world ---------------------------------------------------------

def _opt_in_project(td: Path) -> Path:
    d = CORR._v2_project(td / "opt")
    _set_ai(d, OPTS)
    for lid in ("race_cw", "race_acw"):
        _gate_obj(d, lid)
    return d


def test_opt_in_payload_carries_acs_meaning():
    with tempfile.TemporaryDirectory() as td:
        d = _opt_in_project(Path(td))
        for lid in ("race_cw", "race_acw"):
            _quiet(w.main, [str(d), "--layout", lid])
            ai = ab.read_ai(d / "ai" / lid / "fast_lane.ai")
            P, n = ai["pos"], ai["n"]
            assert (ai["lap_ms"], ai["sample_count"], ai["has_grid"]) == (0, 0, 0), ai["lap_ms"]
            # length = the 3D segment from the previous point (point 0: the seam segment), never the lap distance
            for i in range(n):
                assert abs(ai["length"][i] - math.dist(P[i], P[i - 1])) < 2e-3, (i, ai["length"][i])
            assert max(ai["length"]) < 2.0 and ai["point_length"][-1] > 1000.0      # the point record stays cumulative
            # direction +-1 everywhere; = -sign(the LOCAL heading change, +-1 point) wherever it turns > 0.5 deg
            assert all(x in (-1.0, 1.0) for x in ai["direction"])
            tk = gate.window_sum(gate.turns(P), 1)
            bend = [i for i in range(n) if abs(tk[i]) > math.radians(0.5)]
            agree = sum(1 for i in bend if ai["direction"][i] == -math.copysign(1.0, tk[i]))
            assert bend and agree == len(bend), (agree, len(bend))         # computed from the float32 points
            # radius = the plain 3-point circumradius of the points as written
            for i in range(0, n, 7):
                r = w._circumradius(P[i - 1], P[i], P[(i + 1) % n])
                assert abs(math.log(ai["radius"][i]) - math.log(r)) < 1e-6, (i, ai["radius"][i], r)
            # seated on the built road, its normal and camber: the plane's own tilt (kn5 frame: z negated)
            L = math.sqrt(1.0 + TILT[0] ** 2 + TILT[1] ** 2)
            nk = (-TILT[0] / L, 1.0 / L, TILT[1] / L)
            for i in range(0, n, 11):
                x, y, z = P[i]
                assert abs(y - (TILT[0] * x + TILT[1] * -z)) < 1e-3, (i, y)
                assert all(abs(a - b) < 1e-5 for a, b in zip((ai["nx"][i], ai["ny"][i], ai["nz"][i]), nk))
                fx, fz = ai["fx"][i], ai["fz"][i]
                tilt = math.asin((nk[0] * -fz + nk[2] * fx) / math.hypot(fx, fz))
                # AC's sign rule: the tilt measured toward the bend (every reference line, 0.95-1.00 of tilted points)
                assert abs(ai["camber"][i] - -ai["direction"][i] * tilt) < 1e-4, (i, ai["camber"][i], tilt)
            rep = json.loads((d / "ai" / lid / "ai_draft.json").read_text())
            assert rep["ai_0052"]["opts"]["payload"] == "kunos" and rep["ai_0052"]["built"]["road_tris"] == 2
            assert rep["geometry"]["seated"]["off_road"] == 0 and "GENERATED DRAFT" in rep["status"]


def test_opt_in_line_keeps_off_the_built_walls_and_passes_the_gate_the_legacy_line_fails():
    with tempfile.TemporaryDirectory() as td:
        d = _opt_in_project(Path(td))
        lid = "race_cw"
        objp = d / "data" / f"track.{lid}.obj"
        ob = ab.read_gate_obj(objp)
        walls, road = ab.WallIndex(ob.wall_segs), ab.RoadSurface(ob)
        th = gate.thresholds(d)
        # the legacy line (no ai block) aims at the comfort 1.5 m: under the gate's 2.0 m, and its payload fails V1
        _set_ai(d, None)
        _quiet(w.main, [str(d), "--layout", lid])
        base = Path(td) / "legacy_fast_lane.ai"
        base.write_bytes((d / "ai" / lid / "fast_lane.ai").read_bytes())
        legacy = gate.measure(ab.read_ai(base), walls=walls, road=road, th=th)
        fails = gate.judge(legacy, th)
        assert legacy["v2"]["min_m"] < 2.0 and any(f.startswith("V1 length") for f in fails), (legacy["v2"], fails)
        assert _quiet(gate.main, [str(d), "--layout", lid]) == 1
        # opted in: wall_clear off the built walls, no spurious dips, sides inside the walls — PASS
        _set_ai(d, OPTS)
        _quiet(w.main, [str(d), "--layout", lid])
        m = gate.measure(ab.read_ai(d / "ai" / lid / "fast_lane.ai"), walls=walls, road=road, th=th)
        assert m["v2"]["min_m"] >= 2.5 - 0.05, m["v2"]
        assert m["v3"]["dip_pts"] == 0 and m["v4"]["overreach_pts"] == 0, (m["v3"], m["v4"])
        assert gate.judge(m, th) == [], gate.judge(m, th)
        assert _quiet(gate.main, [str(d), "--layout", lid, "--baseline", str(base)]) == 0
        rep = json.loads((d / "data" / f"ai_verify.{lid}.json").read_text())
        assert rep["ok"] and rep["measured"]["v1"]["direction_agree"] == 1.0
        # the fixture's road tilts <= 0.0067 rad (under the gate's 0.01 "tilted" bar): the flat-road rule judges it
        assert rep["measured"]["v1"]["camber_med_abs_err_rad"] < 1e-4, rep["measured"]["v1"]
        v6 = rep["measured"]["v6"]
        assert len(v6["corners"]) == 4 and v6["min_ratio"] >= 0.85, v6       # the fixture's four corners
        draft = json.loads((d / "ai" / lid / "ai_draft.json").read_text())
        assert draft["corridor"]["check"]["ok"] and all("radius_m" in a for a in draft["geometry"]["box_arcs"])
        assert draft["geometry"]["fairing"]["refused_after"] == 0
        # the box rule as written: every box's car-scale minimum >= 0.85 x the arc the v0.17.1 rule lays there
        for a in draft["geometry"]["box_arcs"]:
            assert a["line_radius_min_m"] >= 0.85 * a["radius_v0171_rule_m"], a
        # with the "tilted" bar under this road's tilt, the ratio rule: AC's sign gives 1.0 ...
        th_t = dict(th, camber_tilt_min_rad=0.004)
        good = ab.read_ai(d / "ai" / lid / "fast_lane.ai")
        mg = gate.measure(good, walls=walls, road=road, th=th_t)
        assert mg["v1"]["camber_tilted_points"] > 0 and 0.99 <= mg["v1"]["camber_ratio_med"] <= 1.01, mg["v1"]
        assert not any(f.startswith("V1") for f in gate.judge(mg, th_t))
        # ... and the plain-asin camber sign (no reference line uses it) fails V1 on the same built road
        bad = ab.read_ai(d / "ai" / lid / "fast_lane.ai")
        bad["camber"] = [-bad["direction"][i] * c for i, c in enumerate(bad["camber"])]
        assert any(f.startswith("V1 camber") for f in gate.judge(gate.measure(bad, walls=walls, road=road, th=th_t), th_t))


def test_opt_in_refuses_a_missing_or_stale_gate_obj():
    with tempfile.TemporaryDirectory() as td:
        d = _opt_in_project(Path(td))
        objp = d / "data" / "track.race_cw.obj"
        (d / "build").mkdir()
        kn5 = d / "build" / "sq.kn5"
        kn5.write_bytes(b"x")
        old = time.time() - 100.0
        os.utime(objp, (old, old))
        assert w.stale_gate_obj(objp, d / "build") == ["sq.kn5"]
        try:
            _quiet(w.main, [str(d), "--layout", "race_cw"])
        except SystemExit as e:
            assert "older than" in str(e.code), e.code
        else:
            raise AssertionError("a gate OBJ older than the kn5 it names must refuse")
        os.utime(objp, None)
        assert w.stale_gate_obj(objp, d / "build") == []
        objp.unlink()
        try:
            _quiet(w.main, [str(d), "--layout", "race_cw"])
        except SystemExit as e:
            assert "missing" in str(e.code), e.code
        else:
            raise AssertionError("ai.surface gate_obj without the OBJ must refuse")


def test_opt_in_refuses_a_box_tighter_than_the_declared_rule():
    # the 0052 box rule (each box >= 0.85 x the arc the v0.17.1 rule lays there) is enforced on the line AS WRITTEN:
    # demand more than the fixture's boxes can keep (0.995 x, while 2.5 m off the walls) and the writer refuses
    with tempfile.TemporaryDirectory() as td:
        d = _opt_in_project(Path(td))
        keep = w.BOX_RULE_KEEP
        try:
            w.BOX_RULE_KEEP = 0.995
            try:
                _quiet(w.main, [str(d), "--layout", "race_cw"])
            except SystemExit as e:
                assert "box corner is tighter" in str(e.code), e.code
            else:
                raise AssertionError("a box under the declared rule must refuse")
        finally:
            w.BOX_RULE_KEEP = keep
        _quiet(w.main, [str(d), "--layout", "race_cw"])             # at 0.85 the same world writes
        draft = json.loads((d / "ai" / "race_cw" / "ai_draft.json").read_text())
        assert all(a["line_radius_min_m"] >= 0.85 * a["radius_v0171_rule_m"] for a in draft["geometry"]["box_arcs"])


def test_load_ai_opts_scopes_and_refusals():
    assert w.load_ai_opts({}, "race_cw") is None
    assert w.load_ai_opts({"ai": OPTS}, "street") is None
    o = w.load_ai_opts({"ai": OPTS}, "race_cw")
    assert o["payload"] == "kunos" and "layouts" not in o and "_note" not in o
    assert w.load_ai_opts({"ai": {"fair": True}}, "anything") == {"fair": True}     # no layouts: every line
    for bad in ({"fiar": True}, {"payload": "ks"}, {"surface": "declared"}):
        try:
            w.load_ai_opts({"ai": bad}, "race_cw")
        except SystemExit:
            pass
        else:
            raise AssertionError(f"{bad} must refuse")


# --- the pieces --------------------------------------------------------------------------------------------

def test_band_solve_matches_a_dense_solve():
    m = 23
    A = [[0.0] * 4 for _ in range(m)]
    for i in range(m):
        A[i][0] = 10.0 + (i % 5)
        for d in range(1, 4):
            if i + d < m:
                A[i][d] = 1.0 / (d + 1 + (i % 3))
    b = [math.sin(i) for i in range(m)]
    x = w._band_solve(A, b)
    Ax = w._band_matvec(A, x)
    assert max(abs(a - c) for a, c in zip(Ax, b)) < 1e-9


def test_fair_line_takes_out_a_wiggle_and_never_crosses_a_bound():
    n = 400
    P = [[i * 1.5, 0.0, 0.15 * math.sin(i * 2.0 * math.pi / 8.0)] for i in range(n)]    # a 12 m wiggle on a straight
    Q, rep = w.fair_line(P, False, lambda i, x, z: True, alpha=0.0)
    amp_in = max(abs(p[2]) for p in P[50:350])
    amp_out = max(abs(q[2]) for q in Q[50:350])
    assert amp_out < 0.1 * amp_in, (amp_in, amp_out)
    # a bound (every input point satisfies it, as the writer's do): between 150 and 250 no point may move more than
    # 2 cm toward -z — the crests stay up there, and nothing ships past the bound
    ok = lambda i, x, z: not (150 <= i <= 250) or z >= P[i][2] - 0.02 - 1e-9      # noqa: E731
    Q2, rep2 = w.fair_line(P, False, ok, alpha=0.0)
    assert all(ok(i, q[0], q[2]) for i, q in enumerate(Q2)) and rep2["refused_after"] == 0, rep2
    assert max(q[2] for q in Q2[150:251]) > 0.12 and max(abs(q[2]) for q in Q2[300:350]) < 0.1 * amp_in
    # a curvature pull straightens a long gentle S inside wide bounds
    S = [[i * 1.5, 0.0, 1.0 * math.sin(i * 2.0 * math.pi / 40.0)] for i in range(n)]      # a 60 m S, R ~ 23 m
    S2, _ = w.fair_line(S, False, lambda i, x, z: True, alpha=1e-2)
    assert max(abs(q[2]) for q in S2[100:300]) < 0.5 * max(abs(p[2]) for p in S[100:300])


def test_gate_obj_reader_walls_rays_and_surface():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.obj"
        # a road square tilted 0.1 along x, a wall along z = 5 (y 0..1), and a second wall 10 m up (another layer)
        p.write_text("\n".join([
            "# gate OBJ extracted from a.kn5", "o 1ROAD_r",
            "v -10 -1 -10", "v 10 1 -10", "v 10 1 10", "v -10 -1 10", "f 1 3 2", "f 1 4 3",
            "o 1WALL_w", "v -10 0 5", "v 10 0 5", "v 10 1 5", "v -10 1 5", "f 5 6 7", "f 5 7 8",
            "o 1WALL_up", "v -10 10 2", "v 10 10 2", "v 10 11 2", "v -10 11 2", "f 9 10 11", "f 9 11 12",
            "o SCENERY", "v 0 0 0", "v 1 0 0", "v 0 0 1", "f 13 14 15"]) + "\n")
        ob = ab.read_gate_obj(p)
        assert ob.header.startswith("gate OBJ") and len(ob.road_tris) == 2
        walls = ab.WallIndex(ob.wall_segs)
        d, k = walls.nearest(0.0, 0.0, 0.0)
        assert abs(d - 5.0) < 1e-9, d                     # the wall on this layer, not the one 10 m up at z = 2
        assert abs(walls.nearest(0.0, 10.0, 0.0)[0] - 2.0) < 1e-9
        assert abs(walls.ray(0.0, 0.0, 0.0, 0.0, 1.0, 20.0) - 5.0) < 1e-9
        assert walls.ray(0.0, 0.0, 0.0, 0.0, -1.0, 20.0) == float("inf")
        assert walls.ray(0.0, 0.0, 0.0, 0.0, 1.0, 4.0) == float("inf")
        y, nrm = ab.RoadSurface(ob).sample(5.0, 0.0, 0.0)
        assert abs(y - 0.5) < 1e-9 and nrm[1] > 0.99 and abs(nrm[0] + 0.1 / math.sqrt(1.01)) < 1e-9
        assert ab.RoadSurface(ob).sample(50.0, 0.0, 0.0) is None


def test_gate_counts_sides_past_a_wall_on_a_perpendicular_ray():
    # a straight line along +x (engine frame) beside the wall at z = 5 (to its LEFT: right of travel is -z)
    n = 60
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.obj"
        p.write_text("\n".join(["o 1WALL_w", "v -100 0 5", "v 100 0 5", "v 100 1 5", "v -100 1 5", "f 1 2 3", "f 1 3 4"]) + "\n")
        walls = ab.WallIndex(ab.read_gate_obj(p).wall_segs)
    pos = [(i * 1.5, 0.0, 0.0) for i in range(n)]          # kn5 frame = engine with z negated: z = 0 either way
    ai = {"pos": pos, "lap_ms": 0, "sample_count": 0, "has_grid": 0, "length": [1.5] * n, "direction": [1.0] * n,
          "radius": [10000.0] * n, "camber": [0.0] * n, "nx": [0.0] * n, "ny": [1.0] * n, "nz": [0.0] * n,
          "fx": [1.0] * n, "fy": [0.0] * n, "fz": [0.0] * n, "side_left": [4.0] * n, "side_right": [4.0] * n}
    m = gate.measure(ai, walls=walls, road=None, th=dict(gate.DEFAULTS))
    assert m["v4"]["overreach_pts"] == 0 and abs(m["v2"]["min_m"] - 5.0) < 1e-9
    ai["side_left"] = [6.0] * n
    m = gate.measure(ai, walls=walls, road=None, th=dict(gate.DEFAULTS))
    assert m["v4"]["overreach_pts"] == n and m["v4"]["per_side"]["left"] == n and abs(m["v4"]["worst_m"] - 1.0) < 1e-6


def _rounded_square(half: float, r: float, ds: float = 1.5) -> list[tuple[float, float, float]]:
    """A closed rounded square (kn5 frame, y = 0): straights of 2 (half - r) joined by quarter arcs of radius r,
    anticlockwise in (x, z), sampled every ~ds metres along it."""
    c = half - r
    legs = []                                                  # (length, point_at(t in 0..length))
    for k, (cx, cz) in enumerate(((c, c), (-c, c), (-c, -c), (c, -c))):
        a0 = k * math.pi / 2
        sx, sz = cx + r * math.cos(a0) , cz + r * math.sin(a0)
        dx, dz = -math.sin(a0), math.cos(a0)                   # the straight runs along the arc's start tangent ...
        legs.append((2 * c, lambda t, sx=sx, sz=sz, dx=dx, dz=dz: (sx - dx * 2 * c + dx * t, sz - dz * 2 * c + dz * t)))
        legs.append((r * math.pi / 2, lambda t, cx=cx, cz=cz, a0=a0: (cx + r * math.cos(a0 + t / r),
                                                                      cz + r * math.sin(a0 + t / r))))
    total = sum(L for L, _ in legs)
    m = int(round(total / ds))
    pts = []
    for j in range(m):
        s_ = total * j / m
        for L, f in legs:
            if s_ <= L:
                x, z = f(s_)
                break
            s_ -= L
        pts.append((x, 0.0, z))
    return pts


def _line_dict(pos) -> dict:
    """A decoded line carrying AC's payload for points ``pos`` (flat road): what read_ai returns."""
    n = len(pos)
    seg = [math.dist(pos[i], pos[i - 1]) for i in range(n)]
    tk = gate.window_sum(gate.turns(pos), 1)
    d, last = [], 1.0
    for i in range(n):
        if abs(tk[i]) > math.radians(0.5):
            last = -math.copysign(1.0, tk[i])
        d.append(last)
    fx = [pos[(i + 1) % n][0] - pos[i - 1][0] for i in range(n)]
    fz = [pos[(i + 1) % n][2] - pos[i - 1][2] for i in range(n)]
    return {"pos": pos, "lap_ms": 0, "sample_count": 0, "has_grid": 0, "length": seg, "direction": d,
            "radius": [gate._circum_xz(pos[i - 1], pos[i], pos[(i + 1) % n]) for i in range(n)],
            "camber": [0.0] * n, "nx": [0.0] * n, "ny": [1.0] * n, "nz": [0.0] * n, "fx": fx, "fy": [0.0] * n,
            "fz": fz, "side_left": [3.0] * n, "side_right": [3.0] * n}


def test_gate_v1_reads_acs_own_conventions():
    th = dict(gate.DEFAULTS)
    ai = _line_dict(_rounded_square(100.0, 40.0))
    n = len(ai["pos"])

    def v1_fails(a):
        return [f for f in gate.judge(gate.measure(a, walls=None, road=None, th=th), th) if f.startswith("V1")
                and "not judged" not in f]
    assert v1_fails(ai) == [], v1_fails(ai)
    # what AC's recorder leaves at the seam (every Kunos line: ~5 x the spacing and direction 0.1 on the last point)
    # and a spacing gap whose length field matches it (every Kunos line, near point 25): still AC's meaning
    k = dict(ai, length=ai["length"][:-1] + [7.5], direction=ai["direction"][:-1] + [0.1])
    assert v1_fails(k) == [], v1_fails(k)
    pos = ai["pos"][:25] + ai["pos"][28:]                      # a 4-segment gap
    g = _line_dict(pos)
    assert v1_fails(g) == [] and gate.measure(g, walls=None, road=None, th=th)["v1"]["spacing_gaps_over_3x"] == 1
    # one point's length 0.5 m off its own segment: refused (the median alone never saw it)
    L = list(ai["length"])
    L[n // 2] += 0.5
    assert any("off their own segment" in f for f in v1_fails(dict(ai, length=L)))
    # direction toward the wrong side: refused
    wrong = [-1.0 * x for x in ai["direction"]]
    assert any(f.startswith("V1 direction agrees") for f in v1_fails(dict(ai, direction=wrong)))
    # AC's WINDOW family (ks_silverstone/international and 33 third-party lines on this PC): length = the last 5
    # segments, radius through the points +-5, a direction ramp over the 10 points at each end, the normal up
    P = ai["pos"]
    seg = ai["length"]
    ramp = list(ai["direction"])
    for j in range(10):
        ramp[j] *= j / 10.0
        ramp[n - 1 - j] *= j / 10.0
    win = dict(ai, length=[sum(seg[i - j] for j in range(5)) for i in range(n)], direction=ramp,
               radius=[gate._circum_xz(P[(i - 5) % n], P[i], P[(i + 5) % n]) for i in range(n)])
    mw = gate.measure(win, walls=None, road=None, th=th)
    assert mw["v1"]["family"] == "window" and v1_fails(win) == [], v1_fails(win)
    # a cumulative length (the v0.17.1 drafts) matches neither family and is judged, and refused, as a segment line
    cum = [sum(seg[1:i + 1]) for i in range(n)]
    mc = gate.measure(dict(ai, length=cum), walls=None, road=None, th=th)
    assert mc["v1"]["family"] == "segment" and any(f.startswith("V1 length is not") for f in v1_fails(dict(ai, length=cum)))


def test_gate_v6_refuses_a_corner_tightened_below_the_baseline():
    th = dict(gate.DEFAULTS)
    base = _line_dict(_rounded_square(100.0, 40.0))
    near = _line_dict(_rounded_square(100.0, 36.0))           # 0.9 x: kept
    tight = _line_dict(_rounded_square(100.0, 30.0))          # 0.75 x: refused
    v6 = gate.corners_vs_baseline(near, base, th)
    assert len(v6["corners"]) == 4 and 0.85 <= v6["min_ratio"] < 0.95, v6
    m = gate.measure(near, walls=None, road=None, th=th)
    m["v6"] = v6
    assert not any(f.startswith("V6") for f in gate.judge(m, th))
    m = gate.measure(tight, walls=None, road=None, th=th)
    m["v6"] = gate.corners_vs_baseline(tight, base, th)
    assert sum(1 for f in gate.judge(m, th) if f.startswith("V6")) == 4, gate.judge(m, th)

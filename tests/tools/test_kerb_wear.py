"""tools/race_furniture.py — ledger 0053's worn race-kerb wrap (pure): WHERE the tyre rubber goes on each race kerb
(kerb_wear) and how the kerb is wrapped onto the 4-column atlas (kerb_atlas_face_uvs), with the geometry untouched.

Kevin, 2026-10-12, from the seat: "i'd like the race curbs to be tire-worn/textured". Pinned here, decided before
the fix (fleet/feedback/0053, Verification 1):
  (a) kerb_mesh's output is byte-identical to before (the wear only adds UVs beside it);
  (b) on every Lake Murray kerb: v continuous along the kerb, every face corner's u inside its column's pad, every
      column change on a joint station whose v is a whole metre, one wrap handedness on all eight kerbs — the same as
      the prep's planar road wrap in the Blender frame (a kn5 tangent carries no handedness sign);
  (c) the rubber where tyres run: every outside kerb worn on BOTH exits and never within 5 m of its apex, the hairpin
      and seam inside kerbs carrying >= 10 m (centreline) of the heaviest level, <= 60 seams in all; the exporter's
      render vertices rise by at most 6 per seam.
Plain ``test_*`` functions for tests/run_tests.py (no pytest, no bpy).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import race_furniture as rf  # noqa: E402

TRACK = ROOT / "tracks" / "san-diego-lake-murray"


def _arc_stations(n=30, radius=12.0, lip=4.63, corner_at=15):
    out = []
    for q in range(n):
        a = q * 0.3 / radius
        s = {"s": q * 0.3, "k": q, "cx": radius * math.sin(a), "cz": radius * (1 - math.cos(a)), "y": 0.01 * q,
             "y_hint": 0.1, "tx": math.cos(a), "tz": math.sin(a), "lip": lip, "h": rf.KERB_H, "arc": q * 0.3}
        if q == corner_at:
            s["ls"] = 1.2
        out.append(s)
    return out


def _md5_mesh(out):
    def r(x):
        return round(x, 9) if isinstance(x, float) else tuple(r(y) for y in x) if isinstance(x, (tuple, list)) else x
    return hashlib.md5(repr(r(out)).encode()).hexdigest()


def test_kerb_mesh_is_unchanged_by_the_wear():
    """(a) the geometry and its legacy per-vertex UVs: md5 of kerb_mesh on a curved, mitred kerb, both sides —
    recorded from HEAD 5ccf20b (git show HEAD:tools/race_furniture.py, identical output)"""
    assert rf.KERB_TILE_M == 1.0 and rf.KERB_W == 1.0 and rf.KERB_H == 0.05 and rf.KERB_RAMP_W == 0.10
    got = {side: _md5_mesh(rf.kerb_mesh(_arc_stations(), side)) for side in (1.0, -1.0)}
    assert got == {1.0: "ad5e48af2192cbbe9d09650f18e6887f", -1.0: "b88da1604df792566cb187cfc57a51e6"}, got


def _check_wrap(plan, wear, face_uvs, n):
    """(b) on one kerb: v continuous, u in its column's pad, column changes only at whole-metre joints"""
    cols, pad = rf.KERB_ATLAS_COLUMNS, rf.KERB_ATLAS_PAD_PX / (rf.KERB_ATLAS_COLUMNS * rf.KERB_ATLAS_COL_PX)
    side = 1.0 if plan["side"] == "L" else -1.0
    vs = rf.KERB_V_SIGN[plan["side"]]
    v_m = wear["v_m"]
    assert len(face_uvs) == 3 * (n - 1) and len(wear["levels"]) == n - 1
    v_at = {}
    for q in range(n - 1):
        lv = wear["levels"][q]
        assert 0 <= lv < cols
        for corner_uvs, f in zip(face_uvs[3 * q:3 * q + 3], rf.kerb_mesh(plan["stations"], side)[1][3 * q:3 * q + 3]):
            for (u, v), vi in zip(corner_uvs, f):
                assert lv / cols + pad - 1e-12 <= u <= (lv + 1) / cols - pad + 1e-12, (u, lv)
                st = vi // 4
                assert abs(v - vs * v_m[st] / rf.KERB_ATLAS_V_M) < 1e-12
                v_at.setdefault(st, set()).add(round(v, 12))
    assert all(len(vs_) == 1 for vs_ in v_at.values()), "a station row with two v values: a jump along the kerb"
    for i in range(1, n):                         # v strictly increasing along the kerb (warped metres)
        assert v_m[i] > v_m[i - 1]
    joints = set(wear["joints"])
    for q in range(1, n - 1):
        if wear["levels"][q] != wear["levels"][q - 1]:
            assert q in joints, (rf.object_name(plan), q)
            assert abs(v_m[q] - round(v_m[q])) < 1e-9, v_m[q]          # ON a block end of the atlas
    a = wear["arcs_m"]
    assert max(abs(v_m[i] - a[i]) for i in range(n)) <= rf.KERB_JOINT_SNAP_MAX_M + 1e-9   # blocks stay ~1 m


def _handedness_blender(plan, face_uvs):
    side = 1.0 if plan["side"] == "L" else -1.0
    v, f, _ = rf.kerb_mesh(plan["stations"], side)
    bv, bf = rf.to_blender(v, f)
    return {rf.uv_handedness(bv, face, list(reversed(face_uvs[i]))) for i, face in enumerate(bf)}


def test_synthetic_kerbs_wrap_with_one_handedness_and_seams_only_at_joints():
    """an L outside kerb and an R inside kerb on a 12 m arc: the wrap rules, and the handedness of the prep's
    planar road wrap (u = x, v = y seen from above, Blender frame) on BOTH — the L / R mirror image is gone"""
    planar = rf.uv_handedness([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], (0, 1, 2, 3), [(0, 0), (1, 0), (1, 1)])
    assert planar == 1
    for side, sub, lip in (("L", "out", 4.63), ("R", "in", -4.63)):
        sts = _arc_stations(n=120, lip=lip, corner_at=-1)
        plan = {"stations": sts, "side": side, "sub": sub, "lap_m": 0.0, "apex_station": 18.0}
        corner = {"PC": 8.0, "PT": 28.0, "E_m": 10.0, "apex_station": 18.0}
        wear = rf.kerb_wear(plan, corner)
        fu = rf.kerb_atlas_face_uvs(len(sts), 1.0 if side == "L" else -1.0, wear)
        _check_wrap(plan, wear, fu, len(sts))
        assert _handedness_blender(plan, fu) == {planar}, side
        assert wear["seams"] >= 1
    # the legacy per-vertex UVs WERE mirrored (the defect the sign fixes): L and R disagree
    legacy = set()
    for side in (1.0, -1.0):
        v, f, uv = rf.kerb_mesh(_arc_stations(lip=4.63 * side, corner_at=-1), side)
        legacy |= {rf.uv_handedness(v, face, [uv[i] for i in face]) for face in f}
    assert legacy == {1, -1}


def test_wear_levels_and_render_vertex_split():
    """the level rule ([invented], GATES-CHANGELOG 0053) on a symmetric outside kerb: floor away from the lobes,
    the heaviest column at both track-outs, a superset climb in between; a seam costs at most 6 render verts"""
    sts = _arc_stations(n=200, lip=4.63, corner_at=-1)
    plan = {"stations": sts, "side": "L", "sub": "out", "lap_m": 0.0, "apex_station": 30.0}
    corner = {"PC": 20.0, "PT": 40.0, "E_m": 20.0, "apex_station": 30.0}
    (c1, c2), sig, floor = rf.kerb_wear_centres(plan, corner)
    assert (c1, c2, sig, floor) == (44.0, 16.0, 6.0, 0.10)
    wear = rf.kerb_wear(plan, corner)
    lv = wear["levels"]
    top = rf.KERB_ATLAS_COLUMNS - 1
    near = [lv[i] for i in range(len(lv)) if abs(sts[i]["s"] - 30.0) <= 5.0]
    assert near and max(near) < top                                   # nothing heavy through the apex
    heavy = wear["heavy_spans_m_from_apex"]
    assert any(b < -5 for a, b in heavy) and any(a > 5 for a, b in heavy), heavy   # both exits
    v, f, _ = rf.kerb_mesh(sts, 1.0)
    fu = rf.kerb_atlas_face_uvs(len(sts), 1.0, wear)
    sharp = sorted(set(rf.sharp_edges(v, f)) | set(rf.kerb_outline_edges(len(sts))))
    base = rf.render_vertex_count(len(v), f, sharp)
    assert base == 6 * len(sts)
    assert rf.render_vertex_count(len(v), f, sharp, fu) == base + 6 * wear["seams"]


def _sd_plans():
    data = TRACK / "data"
    if not all((data / f).exists() for f in ("centerline.local.json", "median_bands.json", "barrier_bands.json")):
        return None
    bands = json.loads((data / "barrier_bands.json").read_text(encoding="utf-8"))
    if not rf.corridors(bands):
        return None
    with contextlib.redirect_stdout(io.StringIO()):
        _, _, _, plans, corners = rf.plan_all(TRACK, bands)
    for p in plans:
        for s in p.get("stations") or []:
            s.setdefault("y", s["y_hint"])
    return [p for p in plans if p["kind"] == "kerb"], {c["apex_vertex"]: c for c in corners}


def test_real_lake_murray_kerbs_are_worn_where_tyres_run():
    """(b) + (c) on the eight declared Lake Murray kerbs (skipped without the repo's v2 data)"""
    got = _sd_plans()
    if got is None:
        print("  (no Lake Murray v2 data in this checkout — skipped)")
        return
    kerbs, corner_of = got
    assert len(kerbs) == 8, len(kerbs)
    seams, rv0, rv1, hands = 0, 0, 0, set()
    for p in kerbs:
        name = rf.object_name(p)
        c = corner_of[p["apex"]]
        side = 1.0 if p["side"] == "L" else -1.0
        wear = rf.kerb_wear(p, c)
        fu = rf.kerb_atlas_face_uvs(len(p["stations"]), side, wear)
        _check_wrap(p, wear, fu, len(p["stations"]))
        hands |= _handedness_blender(p, fu)
        seams += wear["seams"]
        v, f, _ = rf.kerb_mesh(p["stations"], side)
        sharp = sorted(set(rf.sharp_edges(v, f)) | set(rf.kerb_outline_edges(len(p["stations"]))))
        a, b = rf.render_vertex_count(len(v), f, sharp), rf.render_vertex_count(len(v), f, sharp, fu)
        assert b - a <= 6 * wear["seams"], (name, a, b, wear["seams"])
        rv0, rv1 = rv0 + a, rv1 + b
        heavy = wear["heavy_spans_m_from_apex"]
        if p["sub"] == "out":
            assert any(e < 0 for s_, e in heavy) and any(s_ > 0 for s_, e in heavy), (name, heavy)   # both exits
            assert all(e < -5 or s_ > 5 for s_, e in heavy), (name, heavy)                          # not the apex
        if name in ("1KERB_race_770_in", "1KERB_race_0_in"):
            assert sum(e - s_ for s_, e in heavy) >= 10.0, (name, heavy)       # centreline metres of the heaviest level
    assert hands == {1}, hands
    assert seams <= 60, seams
    assert rv0 == 7050, rv0                      # the installed v0.17.1 race kn5's KERB verts (inspect_kn5)
    assert rv1 <= rv0 + 6 * seams, (rv1, seams)
    print(f"  Lake Murray kerbs: {seams} column seams, render verts {rv0} -> {rv1}")

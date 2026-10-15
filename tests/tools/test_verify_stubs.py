"""tools/verify_stubs.py — the phase-5 stub gate (ledger 0054, 2026-10-14), on a synthetic BUILT road.

test_verify_mouths' welded mouth (a straight host 20 m wide on a -5 % grade, a 16 m connector meeting it at 76 deg,
welded by mouth_weld.weld_end) dressed as a STUB the way tools/author_stubs_blend.py dresses one, with the pure
geometry it uses (tools/stub_geom.py): both corner returns from the host's gap-end rows to the stub's first kept curb
rows (the stub's curb before them removed), the corner pavement fans, and the K-rail across the stub 15 m past the
mouth line, seated on the lowest surface under its footprint. That passes every check; then one defect at a time:
a gap in the barrier, the barrier lifted off the road, a wall standing in the stub's carriageway, a return missing,
the barrier object missing.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import mouth_weld as mw  # noqa: E402
import stub_geom as sg  # noqa: E402
import verify_stubs as vs  # noqa: E402

_spec = importlib.util.spec_from_file_location("_tvm", Path(__file__).resolve().parent / "test_verify_mouths.py")
TVM = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TVM)

L_STUB = 15.0


def _quad(tris, a, b, c, d):
    tris.extend([(a, b, c), (a, c, d)])


def _write_obj(path, groups):
    out, k = [], 0
    for g, tris in groups.items():
        out.append(f"o {g}")
        for t in tris:
            for v in t:
                out.append("v %.5f %.5f %.5f" % v)
            out.append(f"f {k + 1} {k + 2} {k + 3}")
            k += 3
    Path(path).write_text("\n".join(out) + "\n", encoding="ascii")


def _host_curb_pt(j, s, p):
    x = TVM.HX[j]
    off, h = TVM.CURB_H[p]
    return (x, TVM.hy(x) + h, s * (TVM.HALF_H + off))


def build(tmp, gap_in_barrier=False, lift=0.0, wall_in_lane=False, drop_return=None, no_barrier=False):
    proj = Path(tmp)
    (proj / "data").mkdir(parents=True, exist_ok=True)
    lines, centre = TVM.conn_lines()
    new = TVM.weld(lines)
    n = len(new[("road", 0)])
    groups = {"1ROAD_road": [], "1KERB_sidewalk": [], "1GRASS_0": []}
    hr = TVM.host_rows()
    for j in range(len(hr) - 1):
        for a, b in ((0, 1), (1, 2)):
            _quad(groups["1ROAD_road"], hr[j][a], hr[j][b], hr[j + 1][b], hr[j + 1][a])
    hpts = [r[1] for r in hr]
    seg = next(i for i in range(len(TVM.HX) - 1) if TVM.HX[i] <= 0.0 <= TVM.HX[i + 1])
    window = mw.gap_window(hpts, len(hpts), False, seg, 0.0, 2 * TVM.HALF_C, TVM.ANG)
    for s in (1, -1):
        for j in range(len(hr) - 1):
            if s == 1 and j in window and j + 1 in window:
                continue
            for p in range(3):
                _quad(groups["1KERB_sidewalk"], _host_curb_pt(j, s, p), _host_curb_pt(j, s, p + 1),
                      _host_curb_pt(j + 1, s, p + 1), _host_curb_pt(j + 1, s, p))
    rows = [tuple(new[("road", k)][j] for k in range(3)) for j in range(n)]
    for j in range(n - 1):
        for a, b in ((0, 1), (1, 2)):
            _quad(groups["1ROAD_road"], rows[j][a], rows[j][b], rows[j + 1][b], rows[j + 1][a])
    # the returns (author_stubs_blend's corner loop, pure)
    cen = [r[1] for r in rows]
    arcs = mw.arc_lengths(cen)
    j1 = next(j for j, a in enumerate(arcs) if a >= 8.0)
    j2 = next(j for j, a in enumerate(arcs) if a >= 12.0)
    ends = (min(window), max(window))
    corners = []
    first_kept = {}
    for e, lane in ((1, 0), (-1, 2)):
        E1, E2 = rows[j1][lane], rows[j2][lane]
        bdir = sg.unit2(E2[0] - E1[0], E2[2] - E1[2])
        hit = sg.line_seg_intersect(E1, (-bdir[0], -bdir[1]), (-90.0, 0.0, TVM.HALF_H), (90.0, 0.0, TVM.HALF_H))
        K = (hit[0], TVM.hy(hit[0]), hit[1])
        best = None
        for kend in ends:
            A_row = tuple(_host_curb_pt(kend, 1, p) for p in range(4))
            ln = sg.rf.left_normal(*bdir)
            lat = ((A_row[0][0] - E1[0]) * ln[0] + (A_row[0][2] - E1[2]) * ln[1]) * e
            if best is None or lat > best[0]:
                best = (lat, A_row)
        A_row = best[1]
        tH = sg.dist2(K, A_row[0])
        J = next(r for r in range(n) if (new[("curb", e, 0)][r][0] - K[0]) * bdir[0]
                 + (new[("curb", e, 0)][r][2] - K[2]) * bdir[1] >= tH + 0.05)
        J_row = tuple(new[("curb", e, p)][J] for p in range(4))
        st, rec = sg.return_stations(A_row, J_row, K, bdir)
        rec["edge"] = e
        corners.append(rec)
        first_kept[e] = J
        if drop_return == e:
            continue
        for r0, r1 in zip(st, st[1:]):
            for p in range(3):
                _quad(groups["1KERB_sidewalk"], r0[p], r0[p + 1], r1[p + 1], r1[p])
        pv, pt = sg.corner_pavement(K, K[1], st, rec["n_arc_rows"])
        groups["1ROAD_road"].extend(tuple(pv[i] for i in t) for t in pt)
    for s in (1, -1):
        for p in range(3):
            A, B = new[("curb", s, p)], new[("curb", s, p + 1)]
            for j in range(first_kept[s], n - 1):
                _quad(groups["1KERB_sidewalk"], A[j], B[j], B[j + 1], A[j + 1])
    for x in range(-80, 80, 10):
        for z in range(-60, 100, 10):
            _quad(groups["1GRASS_0"], (x, TVM.hy(x) - 1.5, z), (x + 10, TVM.hy(x + 10) - 1.5, z),
                  (x + 10, TVM.hy(x + 10) - 1.5, z + 10), (x, TVM.hy(x) - 1.5, z + 10))
    # the barrier, L_STUB past the mouth line, seated on the built surfaces
    u_mouth = mw.OVERLAP_M / math.sin(math.radians(TVM.ANG))
    u_bar = u_mouth + L_STUB
    j = max(i for i, a in enumerate(arcs) if a <= u_bar)
    f = (u_bar - arcs[j]) / (arcs[j + 1] - arcs[j])

    def lerp_row(s):
        return tuple(tuple(new[("curb", s, p)][j][k] * (1 - f) + new[("curb", s, p)][j + 1][k] * f for k in range(3))
                     for p in range(4))
    field = vs.Field({"ROAD": groups["1ROAD_road"], "KERB": groups["1KERB_sidewalk"], "GRASS": [], "STUB": [],
                      "WALL": [], "OTHER": []})

    def base_of(x, z, ax, az):
        smp = []
        for px, pz in sg.footprint_samples(x, z, ax, az):
            h = field.heights(px, pz)
            smp.append(max(h["ROAD"] + h["KERB"], default=None))
        got = [v for v in smp if v is not None]
        return (min(got) if got else None), smp
    path = sg.barrier_path(lerp_row(-1), lerp_row(1))
    rings, seat = sg.barrier_rings(path, base_of)
    if gap_in_barrier:
        mid = len(rings) // 2
        parts = [rings[:mid - 4], rings[mid + 4:]]
    else:
        parts = [rings]
    if not no_barrier:
        groups["1WALL_STUB_t"] = []
        for part in parts:
            verts, faces, _uvs = sg.barrier_mesh(part)
            for fc in faces:
                vv = [(verts[i][0], verts[i][1] + lift, verts[i][2]) for i in fc]
                for k in range(1, len(vv) - 1):
                    groups["1WALL_STUB_t"].append((vv[0], vv[k], vv[k + 1]))
    if wall_in_lane:
        (cx, cz), (tx, tz), (nx, nz), _w = TVM.vm.Path2(TVM.vm.smooth_xz([tuple(q) for q in centre]),
                                                       [2 * TVM.HALF_C] * len(centre)).frame(8.0)
        y = TVM.hy(0.0) + 3.0                     # a 0.5 m post box standing in the lane (its top face has area)
        q = [(cx + sx * 0.25, y, cz + sz * 0.25) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        groups["1WALL_lamp"] = [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
    _write_obj(proj / "data" / "track.obj", groups)
    (proj / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in hpts],
                                                                      "widths_m": [2 * TVM.HALF_H] * len(hpts)}))
    (proj / "data" / "connectors.local.json").write_text(json.dumps({"connectors": [
        {"name": "c#0", "points_xyz_m": [list(p) for p in centre], "widths_m": [2 * TVM.HALF_C] * len(centre)}]}))
    (proj / "data" / "mouths.json").write_text(json.dumps({"mouths": [{
        "connector": "c", "host": "MAINLINE", "host_vertex": seg, "side": 1, "connector_width_m": 2 * TVM.HALF_C,
        "cut_xyz": list(centre[0]), "host_seg": seg, "host_t": 0.0, "angle_deg": TVM.ANG, "host_grade": TVM.GRADE,
        "piece": "c#0", "end": "start"}]}))
    (proj / "data" / "stubs.plan.json").write_text(json.dumps({"stubs": [{
        "id": "t", "connector": "c", "host": "MAINLINE", "u_mouth_from_cut_m": u_mouth, "u_barrier_from_cut_m": u_bar,
        "cut_xz": [centre[0][0], centre[0][2]]}], "curb_cuts": []}))
    (proj / "data" / "stubs.built.json").write_text(json.dumps({"stubs": [{
        "id": "t", "corners": corners, "barrier": {"path_xz": [[r["x"], r["z"]] for r in seat], "half_base_m": 0.335}}]}))
    (proj / "track.config.json").write_text(json.dumps({"slug": "t"}))
    return proj


def _run(**kw):
    with tempfile.TemporaryDirectory() as tmp:
        proj = build(tmp, **kw)
        r = vs.verify(proj)
        return r["stubs"][0], r


def test_a_dressed_stub_passes_every_check():
    s, r = _run()
    assert not r["fail"], s["fails"]
    assert s["S4"]["short"] == 0 and s["S4"]["samples"] > 300
    assert s["S5"]["max_float_m"] <= 0.0 and s["S5"]["max_sink_m"] <= vs.SEAT_SINK_M
    assert s["S6"]["min_off_host_edge_m"] > 10.0
    assert len(s["S7"]) == 2 and all(not c["fails"] for c in s["S7"])
    assert s["S3"]["holes"] == 0 and s["S3"]["obstructions"] == 0


def test_a_gap_in_the_barrier_fails_the_span():
    s, _r = _run(gap_in_barrier=True)
    assert s["S4"]["short"] > 0 and any(f.startswith("S4") for f in s["fails"])


def test_a_hovering_barrier_fails_the_seat():
    s, _r = _run(lift=0.12)
    assert any(f.startswith("S5") and "hovers" in f for f in s["fails"])


def test_a_wall_in_the_stub_fails_drivable():
    s, _r = _run(wall_in_lane=True)
    assert s["S3"]["obstructions"] > 0 and any(f.startswith("S3") for f in s["fails"])


def test_a_missing_return_fails():
    s, _r = _run(drop_return=-1)
    bad = [c for c in s["S7"] if c["fails"]]
    assert len(bad) == 1 and bad[0]["edge"] == -1


def test_a_missing_barrier_fails_presence():
    s, _r = _run(no_barrier=True)
    assert s["fail"] and any(f.startswith("S1") for f in s["fails"])


def test_no_plan_is_no_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "data").mkdir()
        assert vs.verify(Path(tmp)) is None
        assert vs.main([tmp]) == 0
        assert not (Path(tmp) / "data" / "verify_stubs.json").exists()

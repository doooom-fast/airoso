"""tools/stub_geom.py — the phase-5 stub's pure geometry (ledger 0054, 2026-10-14): the curb return round each mouth
corner, the corner pavement fan, and the K-rail barrier across the stub.

A right-angle corner (wedge 90 deg, tangent 3 m) is a true quarter circle of R 3 m whose first row IS the host's
gap-end row and whose last row IS the stub's first kept curb row (exact copies: the curb is continuous), every station
on the arc within RETURN_STEP_M, the walk never folding through the circle's centre; a 60-deg wedge compresses the
walk; the corner pavement covers exactly the wedge minus the circle's quadrant, facing up; the barrier path rings
every profile point from grass meet to grass meet at <= BARRIER_RING_M and the swept K-rail is a closed solid seated
on the lowest surface under its footprint less the bury.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import race_furniture as rf  # noqa: E402
import stub_geom as sg  # noqa: E402

PROF_H = ((0.0, 0.0), (0.08, 0.14), (1.88, 0.14), (3.08, -0.20))   # host curb profile (walk 1.8 m)
PROF_C = ((0.0, 0.0), (0.08, 0.14), (1.58, 0.14), (2.78, -0.20))   # connector curb profile (walk 1.5 m)


def _row(x, z, y, nx, nz, prof):
    return tuple((x + nx * o, y + h, z + nz * o) for o, h in prof)


def _right_angle(tH=3.0, wedge_deg=90.0, y=10.0):
    """host edge along +x at z = 0 (host pavement at z < 0, ground at z > 0); the corner K at the origin; the stub's
    edge leaves K at `wedge_deg` from the host edge's +x, its pavement on the -x side of that edge"""
    K = (0.0, y, 0.0)
    A_row = _row(tH, 0.0, y, 0.0, 1.0, PROF_H)                     # host gap-end row: outward = +z
    a = math.radians(wedge_deg)
    b_dir = (math.cos(a), math.sin(a))
    J = tH + 0.6
    jx, jz = b_dir[0] * J, b_dir[1] * J
    out = (b_dir[1], -b_dir[0])                                    # away from the stub's pavement
    J_row = _row(jx, jz, y + 0.02, out[0], out[1], PROF_C)
    return K, A_row, J_row, b_dir


def test_right_angle_return_is_a_quarter_circle_welded_to_both_strips():
    # R 4 m: the host's 3.08 m walk + verge fits inside COMPRESS_R x R, so nothing is compressed
    K, A_row, J_row, b_dir = _right_angle(tH=4.0)
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir)
    assert abs(rec["radius_m"] - 4.0) < 1e-6 and abs(rec["phi_deg"] - 90.0) < 1e-6
    assert rec["compress"] == 1.0 and "A_row" not in rec
    assert rows[0] == A_row and rows[-1] == J_row                   # exact copies: the curb is continuous
    O = rec["O"]
    assert abs(O[0] - 4.0) < 1e-6 and abs(O[1] - 4.0) < 1e-6
    n_arc = rec["n_arc_rows"]
    for r in rows[1:n_arc]:
        assert abs(math.hypot(r[0][0] - O[0], r[0][2] - O[1]) - 4.0) < 1e-6   # the lane edge ON the circle
        assert math.hypot(r[3][0] - O[0], r[3][2] - O[1]) > 0.0              # the walk stays on this side of O
    for a, b in zip(rows, rows[1:]):
        assert math.hypot(b[0][0] - a[0][0], b[0][2] - a[0][2]) <= sg.RETURN_STEP_M + 1e-6
    # every station's walk stands 0.14 m over its lane edge (interpolated between the two strips)
    for r in rows:
        assert abs((r[1][1] - r[0][1]) - 0.14) < 1e-6
    assert rec["compress"] <= 1.0


def test_acute_wedge_compresses_the_walk_inside_the_circle():
    K, A_row, J_row, b_dir = _right_angle(tH=3.0, wedge_deg=60.0)
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir)
    R = rec["radius_m"]
    assert abs(R - 3.0 * math.tan(math.radians(30.0))) < 1e-3
    assert rec["compress"] < 1.0
    O = rec["O"]
    for r in rows[1:rec["n_arc_rows"]]:
        d0 = math.hypot(r[0][0] - O[0], r[0][2] - O[1])
        d3 = math.hypot(r[3][0] - O[0], r[3][2] - O[1])
        assert d0 - d3 <= sg.COMPRESS_R * R + 1e-6                 # never through the centre


def test_degenerate_wedges_are_refused():
    K, A_row, J_row, b_dir = _right_angle(wedge_deg=175.0)
    try:
        sg.return_stations(A_row, J_row, K, b_dir)
    except sg.GeomError:
        return
    raise AssertionError("a 175 deg wedge was accepted")


def test_corner_pavement_fills_the_wedge_minus_the_quadrant_facing_up():
    K, A_row, J_row, b_dir = _right_angle(tH=3.0)
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir, step=0.05)
    verts, tris = sg.corner_pavement(K, K[1], rows, rec["n_arc_rows"])
    area = 0.0
    for t in tris:
        a, b, c = (verts[i] for i in t)
        ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        assert ny >= 0                                              # up (engine frame)
        area += ny / 2.0
    R = 3.0
    assert abs(area - (R * R - math.pi * R * R / 4.0)) < 0.01, area


def test_barrier_path_rings_every_profile_point_grass_to_grass():
    right = _row(0.0, -5.0, 10.0, 0.0, -1.0, PROF_C)
    left = _row(0.0, 5.0, 10.0, 0.0, 1.0, PROF_C)
    path = sg.barrier_path(right, left)
    # the end rings END_INSET_M inside the grass meets (on the strip, never on its boundary edge)
    assert abs(math.hypot(path[0][0] - right[3][0], path[0][1] - right[3][2]) - sg.END_INSET_M) < 1e-9
    assert abs(math.hypot(path[-1][0] - left[3][0], path[-1][1] - left[3][2]) - sg.END_INSET_M) < 1e-9
    for p in list(right[:3]) + list(left[:3]):
        assert any(abs(q[0] - p[0]) < 1e-9 and abs(q[1] - p[2]) < 1e-9 for q in path)
    for a, b in zip(path, path[1:]):
        assert math.hypot(b[0] - a[0], b[1] - a[1]) <= sg.BARRIER_RING_M + 1e-9


def test_barrier_is_a_closed_jersey_solid_seated_on_the_lowest_surface():
    right = _row(0.0, -5.0, 10.0, 0.0, -1.0, PROF_C)
    left = _row(0.0, 5.0, 10.0, 0.0, 1.0, PROF_C)
    path = sg.barrier_path(right, left)

    def base_of(x, z, ax, az):
        s = [10.0 + 0.05 * px for px, _pz in sg.footprint_samples(x, z, ax, az)]   # a 5 % grade along the stub
        return min(s), s
    rings, seat = sg.barrier_rings(path, base_of)
    for r, s in zip(rings, seat):
        assert abs(r["y"] - (min(s["surface"]) - sg.BARRIER_BURY_M)) < 1e-3
        assert r["h"] == sg.BARRIER_H
    verts, faces, uvs = sg.barrier_mesh(rings)
    assert rf.signed_volume(verts, faces) > 0
    edges = {}
    for f in faces:
        for i in range(len(f)):
            e = (f[i], f[(i + 1) % len(f)])
            edges[e] = edges.get(e, 0) + 1
    assert all(edges.get((b, a), 0) == 1 for (a, b) in edges), "not a closed manifold"
    span = max(v[2] for v in verts) - min(v[2] for v in verts)
    assert span >= 10.0 + 2 * (2.78 - sg.END_INSET_M) - 1e-6       # grass meet to grass meet


def _crosses(a, b, c, d):
    """the plan segments ab and cd cross (proper intersection)"""
    def o(p, q, r):
        return (q[0] - p[0]) * (r[2] - p[2]) - (q[2] - p[2]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < -1e-12 and o(c, d, a) * o(c, d, b) < -1e-12


def _host_rows(tH, n=6, step=2.5, y=10.0):
    """the host's curb rows from the gap end A (x = tH) away from the mouth (+x)"""
    return [_row(tH + k * step, 0.0, y, 0.0, 1.0, PROF_H) for k in range(n)]


def test_compressed_return_is_continuous_from_the_host_through_the_arc_into_the_stub():
    """2026-10-18 (the phase-5 verifier's V-notch at the 58 / 66 deg corners): the host's gap-end row keeps its full
    3.08 m walk + verge, past the centre of an R 1.7 m return, and the old return compressed only its arc stations —
    the quad A -> first arc station twisted through the centre and the walk stepped back out at B. Now A is compressed
    (the host rows behind it ease back over HOST_RAMP_M), the arc as before, the tail eases back to the stub's own walk:
    no two consecutive cross-section lines cross, and the back of walk / grass meet never leave the curb faster than 45 deg"""
    tH = 3.12
    K, A_row, J_row0, b_dir = _right_angle(tH=tH, wedge_deg=58.0)
    s = sg.walk_scale(A_row, J_row0, K, b_dir)
    assert s < 1.0
    # J at least STUB_RAMP_M past B (the author's rule), then the stub's own row there
    jj = tH + 0.05 + sg.STUB_RAMP_M
    out = (b_dir[1], -b_dir[0])
    J_row = _row(b_dir[0] * jj, b_dir[1] * jj, 10.02, out[0], out[1], PROF_C)
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir)
    assert rec["compress"] < 1.0 and rows[-1] == J_row
    ramp = sg.host_ramp(_host_rows(tH), sg.walk_scale(A_row, J_row, K, b_dir))   # rec["compress"] is rounded
    assert ramp and ramp[0][0] == 0
    assert all(sg.dist2(rows[0][p], ramp[0][1][p]) < 1e-12 for p in range(4))     # the host's row A IS the return's
    assert rows[0][0] == A_row[0] and rows[0][1] == A_row[1]                       # lane edge and curb top unmoved
    # the host strip eases back to full over HOST_RAMP_M and never steps
    hr = [r for _k, r in ramp] + [_host_rows(tH)[len(ramp)]]
    for a, b in zip(hr, hr[1:]):
        assert sg.dist2(a[3], a[0]) <= sg.dist2(b[3], b[0]) + 1e-9
    assert len(ramp) * 2.5 >= sg.HOST_RAMP_M - 1e-9
    seq = list(reversed(hr)) + rows[1:]
    for a, b in zip(seq, seq[1:]):
        assert not _crosses(a[0], a[3], b[0], b[3]), "two consecutive cross-sections cross: the strip folds"
    for a, b in zip(seq, seq[1:]):
        for p in (2, 3):                     # the back of walk / grass meet never diverge faster than 45 deg in plan
            da = sg.dist2(a[p], a[0])
            db = sg.dist2(b[p], b[0])
            assert abs(da - db) <= 1.0 * sg.dist2(a[0], b[0]) + 1e-9, (p, da, db)
    O = rec["O"]
    R = rec["radius_m"]
    for r in rows[:rec["n_arc_rows"]]:
        assert math.hypot(r[3][0] - O[0], r[3][2] - O[1]) >= (1.0 - sg.COMPRESS_R) * R - 1e-3   # rec rounds R


def test_barrier_has_a_module_joint_every_pitch_symmetric_about_its_middle():
    """2026-10-18 (the verifier: "across the carriageway the K-rail renders as one continuous slab, with no 4 m module
    joints"): every MODULE_PITCH_M a V-groove ring of Kevin's module's end profile between two full rings, the layout
    symmetric about the barrier's middle, none on a curb step, the faces round it shaded as creases"""
    right = _row(0.0, -5.0, 10.0, 0.0, -1.0, PROF_C)
    left = _row(0.0, 5.0, 10.0, 0.0, 1.0, PROF_C)
    path = sg.barrier_path(right, left)
    arcs = [0.0]
    for a, b in zip(path, path[1:]):
        arcs.append(arcs[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    js = [a for a, p in zip(arcs, path) if p[2] == "joint"]
    total = arcs[-1]
    assert abs(total - (10.0 + 2 * (2.78 - sg.END_INSET_M))) < 1e-6
    assert len(js) == 4, js                                       # 15.52 m: 3 whole modules + two 1.70 m ends
    for a, b in zip(js, js[1:]):
        assert abs((b - a) - sg.MODULE_PITCH_M) < 1e-6
    assert abs((js[0] + js[-1]) / 2.0 - total / 2.0) < 1e-6      # symmetric about the middle
    keys = [a for a, p in zip(arcs, path) if p[2].startswith("p")]
    for j in js:
        assert min(abs(j - k) for k in keys) >= sg.JOINT_KEY_CLEAR_M
        side = [a for a, p in zip(arcs, path) if p[2] == "jside" and abs(a - j) < 0.05]
        assert sorted(round(a - j, 6) for a in side) == [-sg.JOINT_HALF_M, sg.JOINT_HALF_M]
    for a, b in zip(path, path[1:]):
        assert math.hypot(b[0] - a[0], b[1] - a[1]) <= sg.BARRIER_RING_M + 1e-9

    def base_of(x, z, ax, az):
        s = [10.0 for _p in sg.footprint_samples(x, z, ax, az)]
        return min(s), s
    rings, seat = sg.barrier_rings(path, base_of)
    jr = [r for r, p in zip(rings, path) if p[2] == "joint"]
    assert len(jr) == len(js) and all("prof" in r for r in jr)
    assert abs(jr[0]["arc"]) < 1e-9                               # u = 0 on the first groove
    top = max(h for _l, h in jr[0]["prof"])
    base = max(abs(l) for l, h in jr[0]["prof"] if h == 0.0)
    assert abs(top - 1.106) < 1e-9 and abs(base - 0.315) < 1e-9  # the module's measured end face
    verts, faces, uvs = sg.barrier_mesh(rings)
    assert rf.signed_volume(verts, faces) > 0
    edges = {}
    for f in faces:
        for i in range(len(f)):
            e = (f[i], f[(i + 1) % len(f)])
            edges[e] = edges.get(e, 0) + 1
    assert all(edges.get((b, a), 0) == 1 for (a, b) in edges), "not a closed manifold"
    sharp = set(rf.sharp_edges(verts, faces))
    P = len(rf.ring_profile())
    for k, p in enumerate(path):
        if p[2] != "joint":
            continue
        # the groove reads: the faces either side meet as creases along the joint ring (its flanks and its top)
        along = [e for e in sharp if e[0] // P == k and e[1] // P == k]
        assert len(along) >= 4, len(along)


def test_a_joint_never_lands_on_a_curb_step():
    """the curb's face and top rings stand 0.08 m apart: a joint that would fall on either slides past the pair"""
    keys = [2.0, 2.08]
    for s in (1.98, 2.0, 2.04, 2.08, 2.1):
        js = sg.joint_stations(2 * s, keys, pitch=100.0)       # one joint, at s
        assert js, s
        assert min(abs(js[0] - k) for k in keys) >= sg.JOINT_KEY_CLEAR_M + sg.JOINT_HALF_M - 1e-9, (s, js)


def test_the_returns_grass_meet_lands_where_the_prep_lays_the_ground():
    """2026-10-18 (the verifier's sawtooth grass behind the returns): the interior stations' grass meet stands
    MEET_H_M under their lane edge (the kn5 prep's deck - 0.02), easing from the host's / stub's own 0.20 m under over
    MEET_RAMP_M at each end; the walk is untouched, the end rows are the strips' own"""
    K, A_row, J_row, b_dir = _right_angle(tH=4.0)
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir)
    assert rows[0] == A_row and rows[-1] == J_row
    acc, prev, seen_mid = 0.0, rows[0][0], False
    total = rec["arc_len_m"] + rec["tail_m"]
    for r in rows[1:-1]:
        acc += sg.dist2(r[0], prev)
        prev = r[0]
        h3 = r[3][1] - r[0][1]
        assert sg.MEET_H_M - 1e-9 >= -0.20 - 1e-9
        assert -0.20 - 1e-6 <= h3 <= sg.MEET_H_M + 1e-6, h3
        if min(acc, total - acc) >= sg.MEET_RAMP_M:
            assert abs(h3 - sg.MEET_H_M) < 1e-9
            seen_mid = True
        assert abs((r[1][1] - r[0][1]) - 0.14) < 1e-6 and abs((r[2][1] - r[0][1]) - 0.14) < 1e-6
    assert seen_mid

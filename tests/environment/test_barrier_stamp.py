"""Ledger 0071 (0070 C1): the wall props the engine stamps are wound ONCE and OUTWARD, so the underlay's
Mesh.validate() has nothing to delete and nothing renders inside out.

The frame: the engine's local (x = E, y = up, z = N). The underlay remaps (x, y, z) -> (x, z, y), a reflection, and
re-winds every face to cancel it, so a face whose local cross product (b - a) x (c - a) points outward in the local
frame points outward in Blender too. Every check below is on that local cross product.

- Kevin's 4 m concrete module (props.load_module / instance_barriers / place_module): each face once per placement,
  its normal the rigid image of the module's authored ``vn`` on BOTH sides of a run and on the rim-arc path, every
  face pointing away from the barrier's centre line except the few the authored module itself turns toward it (the
  fork-lift pockets and the end slot: geometry, not winding); UV seams kept; concave end faces triangulated inside
  their outline.
- the chain-link fence sheet (props.append_sheet): both sides, on separate vertices.
- the stone lips and #17 parapets (build_mesh.stone_lip_box / stone_parapet_run) and the swept jersey
  (kerbs.warning_barriers): outward on either side of the road.

Plain ``test_*`` functions, stdlib only.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.environment import props  # noqa: E402
from scripts.geometry import build_mesh as BM, kerbs  # noqa: E402

MODULE = ROOT / "assets" / "models" / "concrete_barrier_4m.obj"


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def _normal(vs, t):
    a, b, c = vs[t[0]], vs[t[1]], vs[t[2]]
    return _cross(_sub(b, a), _sub(c, a))


def _centre(vs, t):
    return tuple(sum(vs[i][k] for i in t) / 3.0 for k in range(3))


def _authored():
    """Per loaded triangle (file order, len(polygon) - 2 per polygon): the polygon's authored vn; and the module's
    height and length range (its centre line is x = 0 at mid-height, along z)."""
    vs, vns, out = [], [], []
    for ln in open(MODULE):
        s = ln.split()
        if not s:
            continue
        if s[0] == "v":
            vs.append(tuple(map(float, s[1:4])))
        elif s[0] == "vn":
            vns.append(tuple(map(float, s[1:4])))
        elif s[0] == "f":
            n = vns[int(s[1].split("/")[2]) - 1]
            out += [n] * (len(s) - 3)
    h = max(v[1] for v in vs)
    return out, h, min(v[2] for v in vs), max(v[2] for v in vs)


def _away_from_centre_line(c, n, h, z0, z1):
    """> 0 when a face at c with normal n (module frame, unit) points away from the module's centre line: lateral
    and vertical offset from (x = 0, y = h / 2) for side / top / bottom faces, the module's middle for end faces."""
    ln = math.sqrt(_dot(n, n)) or 1.0
    n = (n[0] / ln, n[1] / ln, n[2] / ln)
    if abs(n[2]) > 0.7:
        return n[2] * (c[2] - (z0 + z1) / 2.0)
    return n[0] * c[0] + n[1] * (c[1] - h / 2.0)


def _to_module(p, origin, x_axis, z_axis):
    """Inverse of place_module's map (x_axis, z_axis orthonormal horizontal)."""
    d = _sub(p, origin)
    return (d[0] * x_axis[0] + d[2] * x_axis[1], d[1], d[0] * z_axis[0] + d[2] * z_axis[1])


def _vec_to_module(v, x_axis, z_axis):
    return (v[0] * x_axis[0] + v[2] * x_axis[1], v[1], v[0] * z_axis[0] + v[2] * z_axis[1])


def test_the_module_loads_with_its_seams_and_every_triangle_faces_its_authored_normal():
    m = props.load_module(MODULE, keep_seams=True)
    assert len(m["vertices"]) == 439 and len(m["uvs"]) == 439, len(m["vertices"])
    assert len({(v, uv) for v, uv in zip(m["vertices"], m["uvs"])}) == 439, "one vertex per (position, uv) pair"
    vn, _, _, _ = _authored()
    assert len(m["tris"]) == len(vn) == 493
    bad = [k for k, t in enumerate(m["tris"]) if _dot(_normal(m["vertices"], t), vn[k]) < -1e-12]
    assert not bad, f"{len(bad)} triangles face against their polygon (a fan over a concave end face does this)"
    # the collapsed loader still exists for the props that want it (build_env's trees, lamps, fence panels)
    assert len(props.load_module(MODULE)["vertices"]) == 249


def test_triangulate_keeps_convex_fans_and_clips_a_concave_polygon_inside_its_outline():
    quad = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    assert props.triangulate(quad) == [(0, 1, 2), (0, 2, 3)], "convex faces load exactly as before"
    # an L (area 3, counter-clockwise about +z) starting at a convex corner whose fan crosses the notch
    ell = [(0, 1, 0), (1, 1, 0), (1, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)]
    fan_bad = [k for k in range(1, 5) if _normal(ell, (0, k, k + 1))[2] < 0]
    assert fan_bad, "the fan over this L folds over (else the test proves nothing)"
    tris = props.triangulate(ell)
    assert len(tris) == 4
    area = 0.0
    for t in tris:
        n = _normal(ell, t)
        assert n[2] > 0.0, (t, n)                    # wound like the polygon (+z)
        area += n[2] / 2.0
    assert abs(area - 3.0) < 1e-9, area             # covers the L exactly once


def _stamp_run(side):
    cl = [(float(i), 0.0, 0.0) for i in range(14)]  # straight along +x: tangent (1, 0), outward n = (0, side)
    m = props.load_module(MODULE, keep_seams=True)
    out = props.instance_barriers(cl, [8.0] * len(cl), [{"start_idx": 1, "end_idx": 13, "side": side}], m)
    return m, out, (0.0, side), (1.0, 0.0)


def _check_placed(m, out, blocks):
    """blocks: [(origin, x_axis, z_axis)] in vertex-block order. Returns faces checked."""
    vn, h, z0, z1 = _authored()
    nv, nt = len(m["vertices"]), len(m["tris"])
    assert len(out["vertices"]) == nv * len(blocks) and len(out["uvs"]) == len(out["vertices"])
    assert len(out["tris"]) == nt * len(blocks), "each face written once per placement, not twice"
    assert len({tuple(sorted(t)) for t in out["tris"]}) == len(out["tris"]), "no face shares a vertex set with another"
    # how far each authored triangle points away from the centre line. A few point toward it (24 of 493: the
    # fork-lift pockets under the base and the end slot, the inside of a notch): geometry, not winding.
    away = {k: _away_from_centre_line(_centre(m["vertices"], t), _normal(m["vertices"], t), h, z0, z1)
            for k, t in enumerate(m["tris"]) if _dot(_normal(m["vertices"], t), _normal(m["vertices"], t)) > 1e-14}
    toward = [k for k, v in away.items() if v <= 0.0]
    assert 0 < len(toward) <= 30 and len(away) >= 490, (len(toward), len(away))
    for b, (origin, xa, za) in enumerate(blocks):
        assert abs(_dot((xa[0], 0, xa[1]), (za[0], 0, za[1]))) < 1e-9
        for k in range(nt):
            t = out["tris"][b * nt + k]
            assert all(b * nv <= i < (b + 1) * nv for i in t)
            n = _normal(out["vertices"], t)
            if k not in away:
                continue                                       # the module's zero-area slivers
            nm = _vec_to_module(n, xa, za)
            assert _dot(nm, vn[k]) > 0.0, (b, k, nm, vn[k])    # the rigid image of the authored normal
            c = _to_module(_centre(out["vertices"], t), origin, xa, za)
            # away from the centre line exactly as the authored face is: every face but the notches' insides
            assert abs(_away_from_centre_line(c, nm, h, z0, z1) - away[k]) < 1e-6, (b, k)
    return len(blocks) * nt


def test_a_stamped_run_is_wound_once_and_outward_on_both_sides():
    for side in (1.0, -1.0):
        m, out, xa, za = _stamp_run(side)
        n_mod = len(out["vertices"]) // len(m["vertices"])
        assert n_mod == 3, n_mod
        # instance_barriers' placement: origin = station + n * (w/2 + 1.6), y = -base_sink; stations 1, 5, 9
        blocks = [((float(i), -0.05, side * 5.6), xa, za) for i in (1, 5, 9)]
        _check_placed(m, out, blocks)


def test_the_rim_arc_placement_is_wound_outward_at_any_angle():
    m = props.load_module(MODULE, keep_seams=True)
    out = {"vertices": [], "uvs": [], "tris": []}
    blocks = []
    for k in range(8):
        a = k * math.pi / 4 + 0.1
        o = (9.6 * math.cos(a), 0.3, 9.6 * math.sin(a))
        xa, za = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))     # build_mesh's rim arc: a rotation
        props.place_module(out, m, o, xa, za)
        blocks.append((o, xa, za))
    # ...and a reflected basis, the +1 side's handedness, at the same angles
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        o = (30.0 + 5 * math.cos(a), 0.0, 5 * math.sin(a))
        xa, za = (-math.sin(a), math.cos(a)), (math.cos(a), math.sin(a))
        props.place_module(out, m, o, xa, za)
        blocks.append((o, xa, za))
    _check_placed(m, out, blocks)


def test_the_fence_sheet_is_two_sided_on_separate_vertices():
    out = {"vertices": [], "uvs": [], "tris": []}
    quad = [(0.0, 0.0, 0.0), (3.0, 0.0, 0.0), (3.0, 1.8, 0.0), (0.0, 1.8, 0.0)]
    props.append_sheet(out, quad, [(0, 0), (1, 0), (1, 1), (0, 1)], [(0, 1, 2), (0, 2, 3)])
    assert len(out["vertices"]) == 8 and len(out["uvs"]) == 8 and len(out["tris"]) == 4
    assert len({tuple(sorted(t)) for t in out["tris"]}) == 4, "validate() would delete a shared-vertex back face"
    zs = sorted(_normal(out["vertices"], t)[2] for t in out["tris"])
    assert zs[0] < 0 and zs[1] < 0 and zs[2] > 0 and zs[3] > 0, zs


def _bend(side):
    """stations on a 40 m bend with the side's outward normal"""
    rows = []
    for k in range(12):
        th = k / 40.0
        x, z = 40 * math.sin(th), 40 * (1 - math.cos(th))
        tx, tz = math.cos(th), math.sin(th)
        rows.append(((x, 0.0, z), (tx, tz), (-tz * side, tx * side)))
    return rows


def test_stone_lips_are_wound_outward_on_both_sides_and_tile_along_the_run():
    for side in (1.0, -1.0):
        mesh = {"vertices": [], "uvs": [], "tris": []}
        cents = []
        for (x, y, z), (tx, tz), (nx, nz) in _bend(side)[1::4]:
            s = (x + nx * 5.5 - tx * 1.5, y, z + nz * 5.5 - tz * 1.5)
            e = (x + nx * 5.5 + tx * 1.5, y, z + nz * 5.5 + tz * 1.5)
            BM.stone_lip_box(mesh, s, e, (nx * 0.6, nz * 0.6))
            cents.append((x + nx * 5.8, 0.35, z + nz * 5.8))
        assert len(mesh["vertices"]) == 12 * len(cents) and len(mesh["uvs"]) == len(mesh["vertices"])
        assert len(mesh["tris"]) == 8 * len(cents)
        for j, t in enumerate(mesh["tris"]):
            c = _centre(mesh["vertices"], t)
            assert _dot(_normal(mesh["vertices"], t), _sub(c, cents[j // 8])) > 0.0, (side, j)
        tops = [t for t in mesh["tris"] if abs(_normal(mesh["vertices"], t)[1]) > 0.5 and _centre(mesh["vertices"], t)[1] > 0.5]
        assert len(tops) == 2 * len(cents) and all(_normal(mesh["vertices"], t)[1] > 0 for t in tops)
        # UVs: u along the run on every face, v up the sides / across the top — never one texel column
        for t in mesh["tris"]:
            us = {round(mesh["uvs"][i][0], 6) for i in t}
            assert len(us) > 1, "a face whose u never changes is a smear"


def test_the_parapet_run_is_wound_outward_on_both_sides():
    for side in (1.0, -1.0):
        rows = [((x + nx * 7.5, 0.0, z + nz * 7.5), (nx, nz), float(k)) for k, ((x, _, z), _, (nx, nz))
                in enumerate(_bend(side))]
        mesh = {"vertices": [], "uvs": [], "tris": []}
        BM.stone_parapet_run(mesh, rows)
        segs = [((a[0] + c[0]) / 2, 0.175, (a[2] + c[2]) / 2) for (a, _, _), (c, _, _) in zip(rows, rows[1:])]
        assert len(mesh["tris"]) == 6 * len(segs) + 4
        for t in mesh["tris"]:
            c = _centre(mesh["vertices"], t)
            seg = min(segs, key=lambda q: (q[0] - c[0]) ** 2 + (q[2] - c[2]) ** 2)
            assert _dot(_normal(mesh["vertices"], t), _sub(c, seg)) > 0.0, (side, t)


def test_the_swept_jersey_is_wound_outward():
    cl = [(-200.0 + 3.0 * k, 0.0, -200.0) for k in range(20)]
    c0 = cl[-1]
    cl += [(c0[0] + 15 * math.sin(k * math.pi / 14), 0.0, c0[2] + 15 * (1 - math.cos(k * math.pi / 14))) for k in range(1, 8)]
    c1 = cl[-1]
    cl += [(c1[0], 0.0, c1[2] + 3.0 * k) for k in range(1, 20)]
    mesh, spots = kerbs.warning_barriers(cl, [8.0] * len(cl))
    assert spots and mesh["tris"]
    tops = [t for t in mesh["tris"] if abs(_normal(mesh["vertices"], t)[1]) > 0.9 * math.sqrt(_dot(_normal(mesh["vertices"], t), _normal(mesh["vertices"], t)))]
    assert tops and all(_normal(mesh["vertices"], t)[1] > 0 for t in tops), "the K-rail's top faces point up"
    # side faces: away from the row's own centroid (one 8-point jersey profile per row)
    P = 8
    vs = mesh["vertices"]
    for t in mesh["tris"]:
        row = min(t) // P
        rc = tuple(sum(vs[row * P + j][k] for j in range(P)) / P for k in range(3))
        n = _normal(vs, t)
        c = _centre(vs, t)
        off = (c[0] - rc[0], c[1] - rc[1], c[2] - rc[2])
        nxt = tuple(vs[min(row * P + P, len(vs) - P)][k] - vs[row * P][k] for k in range(3))
        L = math.hypot(nxt[0], nxt[2]) or 1.0
        tx, tz = nxt[0] / L, nxt[2] / L
        a = off[0] * tx + off[2] * tz
        off = (off[0] - a * tx, off[1], off[2] - a * tz)
        assert _dot(n, off) > 0.0, t

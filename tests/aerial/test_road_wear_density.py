"""Ledger 0084, Pikes Peak 0.2.2 (PC 2026-11-10): the road_wear gate's density row on sliver triangles.

Two of 28,656 triangles failed density, both slivers on the oval's apron pads (1ROAD_pad_NE 0.0020 m2, edges 1.01 / 5.06 /
6.07 m, read 0.86 % off; 1ROAD_pad_NW 0.0189 m2, 0.51 %). The bake maps every face exactly (u = east / (atlas_px x texel_m)
+ its tile's offset); what moved them is float32: the UV Jacobian of a triangle 0.66 mm tall amplifies the kn5's float32
rounding by its length / height. tools/road_wear_check.density_row judges each triangle by the measure float32 resolves on
it. Pure python (the gate's own interpreter on the PC has no numpy)."""
from __future__ import annotations

import math
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import road_wear_check as rwc  # noqa: E402

A, TEX = 4096, 0.25                     # Pikes Peak 0.2.2's atlas and texel
PITCH, CELL, MARGIN = 192, 32.0, 8.0    # a tile as scripts/aerial/road_wear.plan_atlas lays one at 0.25 m


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def bake(P, col=10, row=12, cell=(1, 6), scale=(1.0, 1.0), off=None):
    """The bake's UVs (road_wear.uv_of) for ground points P, as the kn5 stores them: float32, v negated (the add-on
    writes (u, -v)). ``scale`` / ``off`` mis-map on purpose."""
    wx, wy = cell[0] * CELL - MARGIN, cell[1] * CELL - MARGIN
    out = []
    for i, (x, y) in enumerate(P):
        u = (col * PITCH + scale[0] * (x - wx) / TEX) / A
        v = (row * PITCH + scale[1] * (y - wy) / TEX) / A
        if off is not None and i == off[0]:
            u += off[1] / A; v += off[2] / A
        out.append((f32(u), f32(-v)))
    return tuple(out)


def sliver(cx, cy, L=6.07, a=1.0097, area=0.001988, ang=0.3):
    """1ROAD_pad_NE tri 4006's shape: a 6.07 m base, the apex 1.01 m along it at the height that gives 0.0020 m2."""
    h = 2 * area / L
    dx, dy = math.cos(ang), math.sin(ang)
    P0 = (cx - dx * L / 2, cy - dy * L / 2); P2 = (cx + dx * L / 2, cy + dy * L / 2)
    t = math.sqrt(a * a - h * h)
    P1 = (P0[0] + dx * t - dy * h, P0[1] + dy * t + dx * h)
    return tuple((f32(p[0]), f32(p[1])) for p in (P0, P1, P2))


def tri(cx, cy, s=2.0, ang=0.0):
    """A well-shaped road triangle (a 2 m right isosceles), as the ribbon is made of."""
    c, d = math.cos(ang), math.sin(ang)
    pts = [(0.0, 0.0), (s, 0.0), (0.0, s)]
    return tuple((f32(cx + c * x - d * y), f32(cy + d * x + c * y)) for x, y in pts)


def old_row(tris):
    """The density row as it stood at 06d782f (the Jacobian on every triangle with |det| >= 1e-6): (off, worst)."""
    s0 = 1 / (A * TEX); off = 0; worst = 0.0
    for (P0, P1, P2), (U0, U1, U2) in tris:
        ex, ey = P1[0] - P0[0], P1[1] - P0[1]; fx, fy = P2[0] - P0[0], P2[1] - P0[1]
        det = ex * fy - ey * fx
        if abs(det) < 1e-6:
            continue
        du1, dv1 = U1[0] - U0[0], U1[1] - U0[1]; du2, dv2 = U2[0] - U0[0], U2[1] - U0[1]
        j11 = (du1 * fy - du2 * ey) / det; j12 = (du2 * ex - du1 * fx) / det
        j21 = (dv1 * fy - dv2 * ey) / det; j22 = (dv2 * ex - dv1 * fx) / det
        sA = j11 ** 2 + j12 ** 2 + j21 ** 2 + j22 ** 2; dt = abs(j11 * j22 - j12 * j21)
        r = math.sqrt(max(0.0, sA * sA / 4 - dt * dt)); s1 = math.sqrt(sA / 2 + r); s2 = math.sqrt(max(0.0, sA / 2 - r))
        d = max(abs(s1 / s0 - 1), abs(s2 / s0 - 1)); sh = (s1 - s2) / s0
        worst = max(worst, d)
        off += d > rwc.GATE["density_tol"] or sh > rwc.GATE["shear_tol"]
    return off, worst


def road(n=40, seed=3):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        P = tri(40 + rng.uniform(0, 20), 190 + rng.uniform(0, 20), ang=rng.uniform(0, 6.28))
        out.append((P, bake(P)))
    return out


def test_float32_alone_fails_the_old_row_on_the_pads_sliver():
    """The mechanism: NE-shaped slivers around (46.4, 198.5), mapped exactly and stored as float32, fail the Jacobian
    row by rounding alone (it is the measurement, not the bake)."""
    rng = random.Random(1)
    fails = 0
    for _ in range(50):
        P = sliver(46.44 + rng.uniform(-3, 3), 198.46 + rng.uniform(-3, 3), ang=rng.uniform(0, math.pi))
        fails += old_row([(P, bake(P))])[0]
    assert fails >= 40


def test_correctly_mapped_slivers_pass_on_their_edges():
    rng = random.Random(1)
    tris = road()
    for _ in range(50):
        P = sliver(46.44 + rng.uniform(-3, 3), 198.46 + rng.uniform(-3, 3), ang=rng.uniform(0, math.pi))
        tris.append((P, bake(P)))
    P = sliver(-208.3, 170.43, L=14.767, a=5.8443, area=0.018891, ang=1.1)       # 1ROAD_pad_NW tri 3672's shape
    tris.append((P, bake(P, col=3, row=7, cell=(-7, 5))))
    r = rwc.density_row(tris, A, TEX)
    assert r["pass"], r
    assert r["jacobian_judged"] == 40 and r["edge_judged"] == 51 and r["unjudged"] == 0
    assert r["v_sign"] == -1.0 and r["worst_edge_err"] < 1e-4


def test_mis_mapped_sliver_fails():
    """A sliver really mis-mapped fails: stretched 1 % along the ground's east (its long edge lies 17 degrees off east),
    or with one corner's UV from a texel away."""
    P = sliver(46.44, 198.46)
    for bad in (bake(P, scale=(1.01, 1.0)), bake(P, scale=(1.01, 1.01)), bake(P, off=(1, 1.0, 0.0)),
                bake(P, off=(2, 0.0, 3.0))):
        r = rwc.density_row(road() + [(P, bad)], A, TEX)
        assert not r["pass"] and r["edge_off"] == 1 and r["jacobian_off"] == 0, r
        assert r["edge_offenders"][0]["area_m2"] < 0.003


def test_mis_mapped_road_triangle_fails_on_the_jacobian_as_before():
    """A well-shaped triangle is judged by the Jacobian exactly as before: 0.6 % too many texels fails, 0.4 % passes,
    a 1 % anisotropic stretch fails; the old row and the new agree on every one."""
    for scale, ok in (((1.006, 1.006), False), ((1.004, 1.004), True), ((1.01, 1.0), False), ((1.0, 1.0), True),
                      ((0.994, 1.0), False)):
        P = tri(52.0, 201.0, ang=0.7)
        tris = road() + [(P, bake(P, scale=scale))]
        r = rwc.density_row(tris, A, TEX)
        assert r["pass"] is ok and (old_row(tris)[0] == 0) is ok, (scale, r)
        assert r["jacobian_judged"] == 41 and r["edge_judged"] == 0


def test_the_jacobian_verdict_is_unchanged_on_resolvable_triangles():
    """Every triangle float32 resolves gets the old row's verdict, at the old tolerance: 400 random well-shaped
    triangles, mis-scaled around density_tol."""
    rng = random.Random(9)
    for _ in range(400):
        s = rng.uniform(0.4, 3.0)
        P = tri(rng.uniform(-300, 300), rng.uniform(-300, 300), s=s, ang=rng.uniform(0, 6.28))
        sc = (1 + rng.uniform(-0.008, 0.008), 1 + rng.uniform(-0.008, 0.008))
        U = bake(P, col=rng.randrange(20), row=rng.randrange(20), cell=(int(P[0][0] // CELL), int(P[0][1] // CELL)),
                 scale=sc)
        r = rwc.density_row([(P, U)], A, TEX)
        assert r["jacobian_judged"] == 1
        assert (r["off"] == 0) == (old_row([(P, U)])[0] == 0)


def test_a_triangle_float32_cannot_see_is_counted_not_hidden():
    """A 1 cm triangle (no edge float32 resolves at 0.5 %) is listed as unjudged; a zero-area one (the old row skipped
    |det| < 1e-6 without a word) is judged by its edges."""
    tiny = tri(47.0, 199.0, s=0.01)
    flat = ((f32(47.0), f32(199.0)), (f32(49.0), f32(199.0)), (f32(51.0), f32(199.0)))
    r = rwc.density_row(road() + [(tiny, bake(tiny)), (flat, bake(flat))], A, TEX)
    assert r["pass"] and r["unjudged"] == 1 and r["edge_judged"] == 1
    assert r["unjudged_list"][0]["edges_m"][0] == 0.01
    r = rwc.density_row(road() + [(flat, bake(flat, scale=(1.02, 1.0)))], A, TEX)
    assert not r["pass"] and r["edge_off"] == 1


def test_ulp32():
    assert rwc._ulp32(1.0) == 2.0 ** -23 and rwc._ulp32(0.5) == 2.0 ** -24 and rwc._ulp32(-200.0) == 2.0 ** -16
    assert rwc._ulp32(0.0) > 0

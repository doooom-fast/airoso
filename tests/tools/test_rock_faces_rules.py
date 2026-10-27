"""tools/rock_faces_rules.py — the rock / grass boundary over a cut band's lattice (ledger 0054 P4 integration fix round:
the sawtooth toe and the grass tongues). A strip lattice: rows of squares, each split into two triangles (lower-left
'a', upper-right 'b'); edge adjacency built by shared vertices, as rock_faces_blend builds it by vertex position."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import rock_faces_rules as rr  # noqa: E402


def lattice(nx, ny):
    """faces keyed (i, j, 'a'|'b'); square (i, j) has corners (i,j) (i+1,j) (i,j+1) (i+1,j+1); 'a' = (i,j)(i+1,j)(i,j+1),
    'b' = (i+1,j)(i+1,j+1)(i,j+1). Returns (keys, adjacency, area)"""
    edges = {}
    keys = []
    for i in range(nx):
        for j in range(ny):
            tri = {"a": [(i, j), (i + 1, j), (i, j + 1)], "b": [(i + 1, j), (i + 1, j + 1), (i, j + 1)]}
            for t, vs in tri.items():
                k = (i, j, t)
                keys.append(k)
                for e in range(3):
                    a, b = vs[e], vs[(e + 1) % 3]
                    edges.setdefault((a, b) if a < b else (b, a), []).append(k)
    adj = {k: set() for k in keys}
    for fl in edges.values():
        for a in fl:
            for b in fl:
                if a != b:
                    adj[a].add(b)
    return keys, adj, {k: 0.5 for k in keys}


def test_a_straight_row_boundary_is_stable_and_has_no_teeth():
    keys, adj, _ = lattice(10, 4)
    rock = {k for k in keys if k[1] >= 2}                       # rows 2-3 rock, rows 0-1 grass: a straight boundary
    assert rr.teeth(rock, keys, adj) == (0, 0)
    out, st = rr.smooth_boundary(rock, keys, adj)
    assert out == rock and st["filled"] == 0 and st["eroded"] == 0


def test_grass_teeth_into_the_rock_are_filled_and_rock_teeth_into_the_grass_eroded():
    keys, adj, _ = lattice(10, 4)
    rock = {k for k in keys if k[1] >= 2}
    # a grass tooth: one triangle of row 2 left grass (its two row-mates are rock, its base on row 1 is grass)
    rock.discard((4, 2, "a"))
    # a rock tooth: one triangle of row 1 made rock (its base on row 2 is rock, two sides on grass)
    rock.add((7, 1, "b"))
    g, r = rr.teeth(rock, keys, adj)
    assert g == 1 and r == 1
    out, st = rr.smooth_boundary(rock, keys, adj)
    assert (4, 2, "a") in out and (7, 1, "b") not in out
    assert out == {k for k in keys if k[1] >= 2}
    assert st["teeth_after"] == (0, 0)


def test_a_blocked_face_never_becomes_rock():
    keys, adj, _ = lattice(10, 4)
    rock = {k for k in keys if k[1] >= 2}
    rock.discard((4, 2, "a"))
    out, _ = rr.smooth_boundary(rock, keys, adj, blocked=lambda k: k == (4, 2, "a"))
    assert (4, 2, "a") not in out


def test_a_bench_tongue_across_the_wall_fills_but_a_wide_bank_does_not():
    keys, adj, area = lattice(12, 6)
    rock = {k for k in keys if k[1] >= 1}
    # a one-row grass tongue across the wall at row 3, columns 2-7, open to the hill on its left end (column 2's left
    # neighbour is grass too? no: make it rock-bounded on three sides and open on the lattice edge by using columns 0-5)
    tongue = {(i, 3, t) for i in range(0, 6) for t in "ab"}
    rock -= tongue
    out, nf, nc = rr.fill_tongues(rock, keys, adj, area, max_area_m2=60.0)
    assert nf == len(tongue) and nc == 1 and tongue <= out
    # the same shape with the band's own top rows grass (a wide bank, 60 m2 or more) is not a tongue
    rock2 = {k for k in keys if 1 <= k[1] <= 2}
    out2, nf2, _ = rr.fill_tongues(rock2, keys, adj, area, max_area_m2=60.0)
    assert nf2 == 0 and out2 == rock2


def test_a_tongue_holding_a_blocked_face_is_left_whole():
    keys, adj, area = lattice(12, 6)
    rock = {k for k in keys if k[1] >= 1}
    tongue = {(i, 3, t) for i in range(0, 6) for t in "ab"}
    rock -= tongue
    out, nf, nc = rr.fill_tongues(rock, keys, adj, area, blocked=lambda k: k == (2, 3, "a"), max_area_m2=60.0)
    assert nf == 0 and nc == 0 and out == rock


def test_tongue_rule_needs_most_of_the_boundary_against_rock():
    keys, adj, area = lattice(12, 6)
    # a small grass pocket at the band's corner: two of its sides are the lattice edge (open), little of it is against rock
    rock = {k for k in keys if not (k[0] <= 1 and k[1] <= 1)}
    pocket = {k for k in keys if k not in rock}
    out, nf, _ = rr.fill_tongues(rock, keys, adj, area, max_area_m2=60.0, rock_frac=0.9)
    assert nf == 0 and pocket <= set(keys) - out

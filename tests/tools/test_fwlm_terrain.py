"""tools/fwlm_terrain.py (ledger 0080 2b round 1): the vectorised band clamp is the assembler's, byte for byte; the
tiered mesh keeps the fine cells exactly as grass_terrain triangulates them and opens no crack."""
import ast
import json
import math
import random
import struct
import sys
from collections import Counter
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import fwlm_terrain as ft  # noqa: E402

ASM = ROOT / "tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.py"
RIB = ROOT / "tracks/san-diego-lake-murray/scripts-v021/geometry/ribbon.py"


def _from(path, names, extra=None):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    keep = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {"json": json, "math": math, "struct": struct, **(extra or {})}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(path), "exec"), ns)
    return ns


def _grid(ny, nx, sp=13.75, seed=1):
    rnd = random.Random(seed)
    return [[(-400.0 + i * sp, rnd.uniform(-40, 60), 300.0 - j * sp) for i in range(nx)] for j in range(ny)]


def _road(seed=2, n=120):
    rnd = random.Random(seed)
    return [(-300.0 + k * 4.0, rnd.uniform(-5, 20), 100.0 + 30 * math.sin(k / 15.0)) for k in range(n)]


@pytest.mark.parametrize("seed", [1, 7])
def test_band_clamp_np_is_the_assemblers_byte_for_byte(seed):
    ref = _from(ASM, {"band_clamp"})["band_clamp"]
    road = _road(seed) + [(2000.0, 3.0, -2500.0)]          # a far road point: the ring search goes wide
    a = _grid(45, 61, seed=seed)
    b = [list(r) for r in a]
    ref(a, road, 22.0)
    n = ft.band_clamp_np(b, road, 22.0)
    assert n > 0
    assert a == b                                           # every float equal


def test_tiered_fine_cells_are_grass_terrains_and_watertight():
    grass = _from(RIB, {"grass_terrain"}, {"Vertex": tuple})["grass_terrain"]
    g = _grid(4 * 12 + 1, 4 * 16 + 1, seed=3)
    pts = [(-200.0 + k * 5.0, 0.0, 150.0) for k in range(30)]
    roads = [(pts, [12.0] * len(pts))]
    mesh, rep = ft.tiered_terrain(g, roads, fine_m=20.0, step=4)
    full = grass(g)
    assert 0 < rep["fine_cells"] < rep["native_cells"] and rep["fan_cells"] > 0
    assert rep["vertices"] < len(full["vertices"])
    # every fine cell's triangles, as grass_terrain makes them (by position)
    key = lambda m, t: tuple(m["vertices"][k] for k in t)   # noqa: E731
    full_t = {key(full, t) for t in full["tris"]}
    F = ft.fine_cells(g, roads, 20.0, 4)
    nx = len(g[0])
    for J, I in zip(*np.nonzero(F)):
        for jj in range(4 * J, 4 * J + 4):
            for ii in range(4 * I, 4 * I + 4):
                assert (g[jj][ii], g[jj][ii + 1], g[jj + 1][ii + 1]) in full_t
    # watertight: inside the skirt every edge has exactly two faces; the skirt's outer ring is the only open loop
    ec = Counter()
    for a, b, c in mesh["tris"]:
        for e in ((a, b), (b, c), (c, a)):
            ec[tuple(sorted(e))] += 1
    assert max(ec.values()) == 2
    open_edges = [e for e, n in ec.items() if n == 1]
    low = min(v[1] for v in mesh["vertices"])
    assert all(mesh["vertices"][e[0]][1] == low and mesh["vertices"][e[1]][1] == low for e in open_edges)
    # one winding: no edge is used twice in the same direction
    de = Counter()
    for a, b, c in mesh["tris"]:
        for e in ((a, b), (b, c), (c, a)):
            de[e] += 1
    assert max(de.values()) == 1
    assert nx == 65


def test_tiered_refuses_a_grid_that_is_not_whole_native_cells():
    with pytest.raises(SystemExit):
        ft.tiered_terrain(_grid(10, 10), [([(0.0, 0.0, 0.0), (5.0, 0.0, 0.0)], [10.0, 10.0])], fine_m=20.0, step=4)

"""tools/terrain_thin.py — the error-bounded half-edge collapse that thins the road kn5's physical ground (ledger 0054 P3
repair round 3). Pure Python: the thinned surface is checked against the original EVERYWHERE (a dense raster, not
only at the removed vertices), so the overlay bound the module claims is held to the letter."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import terrain_thin as TT  # noqa: E402


def _grid(n, h, step=1.0, jitter=0.0, seed=1):
    rnd = random.Random(seed)
    X, Y, Z = [], [], []
    for j in range(n):
        for i in range(n):
            x = i * step + (rnd.uniform(-jitter, jitter) if 0 < i < n - 1 else 0.0)
            y = j * step + (rnd.uniform(-jitter, jitter) if 0 < j < n - 1 else 0.0)
            X.append(x); Y.append(y); Z.append(h(x, y))
    tris = []
    for j in range(n - 1):
        for i in range(n - 1):
            a, b, c, d = j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i
            tris += [(a, b, c), (a, c, d)] if (i + j) % 2 == 0 else [(a, b, d), (b, c, d)]
    return X, Y, Z, tris


def _max_dev(X, Y, Z, tris0, tris1, n, step):
    at0 = TT.surface_at(X, Y, Z, tris0, None, None, cell=2.0)
    at1 = TT.surface_at(X, Y, Z, tris1, None, None, cell=2.0)
    lo = hi = 0.0
    k = 37
    span = (n - 1) * step
    for a in range(k + 1):
        for b in range(k + 1):
            x, y = 1e-3 + (span - 2e-3) * a / k, 1e-3 + (span - 2e-3) * b / k
            z0, z1 = at0(x, y), at1(x, y)
            assert z0 and z1, (x, y)
            d = z1[0] - z0[0]
            lo, hi = min(lo, d), max(hi, d)
    return lo, hi


def _run(h, tol, n=17, jitter=0.0, lock_border=True):
    X, Y, Z, tris = _grid(n, h, jitter=jitter)
    N = len(X)
    locked = [lock_border and (i % n in (0, n - 1) or i // n in (0, n - 1)) for i in range(N)]
    alive, out, st = TT.thin(X, Y, Z, tris, [tol] * N, [tol] * N, [50.0] * N, locked)
    return X, Y, Z, tris, alive, out, st, n


def test_a_plane_thins_to_its_border_and_does_not_move():
    X, Y, Z, tris, alive, out, st, n = _run(lambda x, y: 0.3 * x - 0.1 * y + 5.0, 1e-6)
    assert st["removed"] > 0.8 * (n - 2) ** 2          # nearly every interior vertex goes
    lo, hi = _max_dev(X, Y, Z, tris, out, n, 1.0)
    assert -1e-6 <= lo and hi <= 1e-6
    for i in range(len(X)):
        if i % n in (0, n - 1) or i // n in (0, n - 1):
            assert alive[i]                              # a locked vertex stays


def test_a_curved_surface_stays_inside_its_tolerance_everywhere_not_only_at_the_vertices():
    for tol, jit in ((0.02, 0.0), (0.05, 0.2), (0.005, 0.3)):
        X, Y, Z, tris, alive, out, st, n = _run(lambda x, y: 0.02 * (x - 8) ** 2 + 0.3 * math.sin(y / 3.0), tol,
                                                jitter=jit)
        lo, hi = _max_dev(X, Y, Z, tris, out, n, 1.0)
        assert -tol - 1e-9 <= lo and hi <= tol + 1e-9, (tol, lo, hi)
        assert st["deviation_bound_m"][0] >= -tol - 1e-9 and st["deviation_bound_m"][1] <= tol + 1e-9
        assert 0 < st["removed"] < (n - 2) ** 2


def test_a_ridge_is_never_planed():
    """a sharp real ridge (a 1 m crest across the tile) keeps its crest within the tolerance"""
    X, Y, Z, tris, alive, out, st, n = _run(lambda x, y: max(0.0, 1.0 - abs(x - 8.0)), 0.02)
    lo, hi = _max_dev(X, Y, Z, tris, out, n, 1.0)
    assert lo >= -0.02 - 1e-9 and hi <= 0.02 + 1e-9
    crest = [i for i in range(len(X)) if abs(X[i] - 8.0) < 1e-9 and 0 < i // n < n - 1]
    at = TT.surface_at(X, Y, Z, out, None, None)
    for i in crest:
        assert abs(at(X[i], Y[i])[0] - 1.0) <= 0.02 + 1e-9


def test_zero_tolerance_changes_nothing_and_a_steep_face_is_locked():
    X, Y, Z, tris, alive, out, st, n = _run(lambda x, y: 0.01 * x * y, 0.0)
    assert st["removed"] == 0 and sorted(map(tuple, map(sorted, out))) == sorted(map(tuple, map(sorted, tris)))
    # a riser (normal z under NZ_LOCK) keeps every vertex it touches
    X, Y, Z, tris = _grid(9, lambda x, y: 0.0)
    for i in range(len(X)):
        if X[i] >= 4.0:
            Z[i] = 10.0                                  # a 10 m wall over the x = 3..4 column of cells
    N = len(X)
    locked = [i % 9 in (0, 8) or i // 9 in (0, 8) for i in range(N)]
    alive, out, st = TT.thin(X, Y, Z, tris, [0.01] * N, [0.01] * N, [50.0] * N, locked)
    for i in range(N):
        if abs(X[i] - 3.0) < 1e-9 or abs(X[i] - 4.0) < 1e-9:
            assert alive[i]
    assert st["locked_steep"] > 0


def test_no_new_half_cell_and_no_fold():
    X, Y, Z, tris = _grid(9, lambda x, y: 0.0)
    N = len(X)
    keys = [(round(X[i]), round(Y[i])) for i in range(N)]
    locked = [i % 9 in (0, 8) or i // 9 in (0, 8) for i in range(N)]
    forbid = lambda a, b, c: TT.is_half_cell(keys[a], keys[b], keys[c])
    alive, out, st = TT.thin(X, Y, Z, tris, [0.01] * N, [0.01] * N, [50.0] * N, locked, forbid=forbid)
    old = {tuple(sorted(t)) for t in tris}
    for a, b, c in out:
        if tuple(sorted((a, b, c))) not in old:
            assert not TT.is_half_cell(keys[a], keys[b], keys[c])
        assert (X[b] - X[a]) * (Y[c] - Y[a]) - (Y[b] - Y[a]) * (X[c] - X[a]) > 0.0
    assert TT.is_half_cell((0, 0), (2, 2), (0, 2)) and not TT.is_half_cell((0, 0), (2, 1), (0, 1))


def test_the_blend_driver_keeps_rib_check_inputs_and_is_wired_after_the_prep():
    src = (ROOT / "tools" / "thin_terrain_blend.py").read_text(encoding="utf-8")
    for k in ("NEAR_ROAD_M = 22.0", "TOL_M = 0.03", "TOL_NEAR_M = 0.005", "UNDER_UP_M = 0.005", "UNDER_DOWN_M = 0.015",
              "FAR_TOL_M = 0.10", "FAR_TOL_OUT_M = 0.15", "FINE_CAP_M = 7.5", "JOG_ZONE_M = 12.0", "CELL_LOCK_M = 18.0",
              "ON_LATTICE = 0.01", 'NODES_FILE = "terrain_thin.nodes.json.gz"', 'TERRAIN = ("1GRASS", "GRASS_FAR")'):
        assert k in src, k
    assert "THIN_DEV" not in src                                         # no look-only knob ships
    rib = (ROOT / "tools" / "rib_check.py").read_text(encoding="utf-8")
    assert "ON_LATTICE = 0.01" in rib and "NEAR_M = 20.0" in rib and "JOG_CELL_MAX_M = 7.6" in rib and "JOG_SLOPE = 0.7" in rib
    assert 'THINNED = "terrain_thin.nodes.json.gz"' in rib
    assert TT.NZ_FINE >= 1.0 / math.sqrt(1.0 + 0.7 ** 2)                 # a riser-steep face is always "steep" here
    ship = (ROOT / "tools" / "ship_sd.sh").read_text(encoding="utf-8")
    i = ship.index('--python "$ENG/scripts/ac/build_kn5_loop.py"')
    r = ship.index('rm -f "$PROJ/data/terrain_thin.json" "$PROJ/data/terrain_thin.nodes.json.gz"')
    j = ship.index('--python "$AIROSO/tools/thin_terrain_blend.py" -- "$PROJ/blender/$SLUG.blend" --project "$PROJ"')
    f = ship.index('--python "$AIROSO/tools/author_freeway_blend.py"')
    k = ship.index('--python "$AIROSO/tools/split_exports_blend.py"')
    assert i < r < j < f < k
    assert "terrain_thin.json" in ship[ship.index('step "sync outputs workshop -> airoso"' + chr(10)):]


def test_rib_check_reads_the_thinned_lattice_off_the_built_surface():
    import gzip
    import json
    import tempfile
    import rib_check as RC
    d = Path(tempfile.mkdtemp()); (d / "data").mkdir()
    frame = [0.0, 0.0, 2.5, 2.5]
    # a 20 x 20 m plane y = 0.1 x + 0.2 z, two triangles; the lattice node (2, 3) and a line vertex at I = 1.5, J = 4
    verts = [(0.0, 0.0, 0.0), (20.0, 2.0, 0.0), (20.0, 6.0, 20.0), (0.0, 4.0, 20.0)]
    tris = [(0, 1, 2), (0, 2, 3)]
    (d / "data" / RC.THINNED).write_bytes(gzip.compress(json.dumps(
        {"frame": frame, "removed": [[5.0, 7.5], [3.75, 10.0], [0.0, 0.0]]}).encode("utf-8")))
    H = {(0, 0): 0.0}
    on = {}
    n, l = RC.thinned_lattice(d, verts, tris, frame, H, on)
    assert (n, l) == (1, 1)
    assert abs(H[(2, 3)] - (0.1 * 5.0 + 0.2 * 7.5)) < 1e-9 and H[(0, 0)] == 0.0      # a kept node is never re-read
    assert on == {(0, 4): [1.5]}
    # no file: nothing changes; another frame: refused
    assert RC.thinned_lattice(Path(tempfile.mkdtemp()), verts, tris, frame, {}, {}) == (0, 0)
    try:
        RC.thinned_lattice(d, verts, tris, [1.0, 0.0, 2.5, 2.5], {}, {})
        raise AssertionError("another frame was read")
    except SystemExit:
        pass

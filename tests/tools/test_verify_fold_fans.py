"""tools/verify_fold_fans.py (ledger 0050) on a synthetic project: a 24 m road swept round a 7.4 m right-hander on a
climb, its inside edge pinched by tools/mouth_weld.unfold_line. The levelled fan passes; the 2026-10-11 rule's riser,
grass standing in the lane, a pinch off its midpoint, a race wall lifted to the high apex and a kerb lip past the
authored 0.05 m fail; the authored race kerb lip and a wall inside the band pass; exit 0 / 1 / 2."""
from __future__ import annotations

import json
import math
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import mouth_weld as mw  # noqa: E402
import verify_fold_fans as vf  # noqa: E402

HALF = 12.0


def _centre(R=7.4, grade=0.018, spacing=2.0, n_arc=12, n_leg=30, y0=100.0):
    pts = [(-spacing * (n_leg - i), 0.0) for i in range(n_leg)] + [(0.0, 0.0)]
    tot = math.radians(110.0)
    for k in range(1, n_arc + 1):
        a = tot * k / n_arc
        pts.append((R * math.sin(a), -R + R * math.cos(a)))
    hx, hz = math.cos(-tot), math.sin(-tot)
    ex, ez = pts[-1]
    pts += [(ex + hx * spacing * i, ez + hz * spacing * i) for i in range(1, n_leg + 1)]
    out, s = [], 0.0
    for i, (x, z) in enumerate(pts):
        if i:
            s += math.hypot(x - pts[i - 1][0], z - pts[i - 1][1])
        out.append((x, y0 + grade * s, z))
    return out


def _edge(C, off):
    out = []
    for i in range(len(C)):
        a, b = C[max(0, i - 1)], C[min(len(C) - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz)
        out.append((C[i][0] - tz / L * off, C[i][1] + 0.10, C[i][2] + tx / L * off))
    return out


def _project(level=True, grass_over=None, race=False, wall_delta=None, kerb_lip=None, x_shift=0.0):
    """-> project dir. The OBJ is the ribbon (L, C, R per row) with R unfolded, plus optional planted defects."""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    C = _centre()
    n = len(C)
    Cl = [(p[0], p[1] + 0.10, p[2]) for p in C]
    L = _edge(C, HALF)
    R = _edge(C, -HALF)
    rep = []
    R2, done, _ = mw.unfold_line(R, Cl, False, strict=True, level=level, report=rep)
    sw = [q for q in done if q[2] is not None]
    assert len(sw) == 1
    k, l, X = sw[0]
    y_k = (rep[0]["y_k"] if rep else None)
    if not rep:                                   # the old rule: recompute the legs for the record
        r2 = []
        mw.unfold_line(R, Cl, False, strict=True, level=True, report=r2)
        y_k, y_l = r2[0]["y_k"], r2[0]["y_l"]
    else:
        y_l = rep[0]["y_l"]
    V, F, groups = [], [], []

    def group(name):
        groups.append((name, []))
        return groups[-1][1]

    def add(p):
        V.append(p)
        return len(V)
    road = group("1ROAD_road")
    for r in range(n - 1):
        l0, c0, r0 = add(L[r]), add(Cl[r]), add(R2[r])
        l1, c1, r1 = add(L[r + 1]), add(Cl[r + 1]), add(R2[r + 1])
        road += [(c0, l0, l1), (c0, l1, c1), (c0, r0, r1), (c0, r1, c1)]
    if grass_over is not None:                    # a grass facet standing in the lane on an eased row
        g = group("1GRASS_0")
        r = k - 2
        a = (Cl[r][0], Cl[r][1] + grass_over, Cl[r][2])
        b = (Cl[r + 1][0], Cl[r + 1][1] + grass_over, Cl[r + 1][2])
        e = ((Cl[r][0] + R2[r][0]) / 2, (Cl[r][1] + R2[r][1]) / 2 + grass_over, (Cl[r][2] + R2[r][2]) / 2)
        g.append((add(a), add(e), add(b)))
    if kerb_lip is not None:                      # a flat race kerb pad on the outside of the bend, kerb_lip high
        kg = group("1KERB_race_test_out")
        r0_, r1_ = k + 3, k + 6
        def at(r, f):
            return (Cl[r][0] + (L[r][0] - Cl[r][0]) * f, Cl[r][1] + kerb_lip, Cl[r][2] + (L[r][2] - Cl[r][2]) * f)
        for r in range(r0_, r1_):
            a, b, c, e = add(at(r, 0.5)), add(at(r, 0.9)), add(at(r + 1, 0.9)), add(at(r + 1, 0.5))
            kg += [(a, b, c), (a, c, e)]
    if wall_delta is not None:                    # a 1.2 m K-rail segment by X, its base wall_delta off the reference
        wg = group("1WALL_RACE_test")
        cx, cz = X[0] - 1.0, X[2]
        base = Cl[k][1] + wall_delta - 0.05
        for (x0, z0, x1, z1) in ((cx - 1, cz, cx + 1, cz), (cx, cz - 1, cx, cz + 1)):
            a, b = add((x0, base, z0)), add((x1, base, z1))
            c, e = add((x1, base + 1.2, z1)), add((x0, base + 1.2, z0))
            wg += [(a, b, c), (a, c, e)]
    obj = "".join(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n" for p in V)
    for name, fs in groups:
        obj += f"o {name}\n" + "".join(f"f {a} {b} {c}\n" for a, b, c in fs)
    lays = [{"id": "street", "direction": "forward"}]
    if race:
        lays = [{"id": "race_cw", "direction": "forward", "race_furniture": True}]
        (d / "data" / "barrier_bands.json").write_text(json.dumps(
            {"corridors": {"race_cw": {"lane_by_vertex": [[-HALF + 0.75, HALF - 0.75]] * n}}}))
    (d / "data" / ("track.race_cw.obj" if race else "track.obj")).write_text(obj)
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "layouts": lays}))
    (d / "data" / "gate_centerline.json").write_text(json.dumps({"points_xyz_m": C, "widths_m": [2 * HALF] * n}))
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": C, "widths_m": [2 * HALF] * n}))
    Xr = (X[0] + x_shift, X[1], X[2])
    welds = {"folds": {"MAINLINE": {"cuts": [["road", 2, k, l]], "rows": n, "level_rows": mw.FOLD_LEVEL_ROWS,
                                    "levelled": [{"line": ["road", 2], "k": k, "l": l, "X": list(Xr),
                                                  "y_k": y_k, "y_l": y_l}]}}}
    (d / "data" / "mouth_welds.json").write_text(json.dumps(welds))
    return d


def _fails(d):
    rep = vf.run(d)
    return rep["fails"], rep


def test_the_levelled_fan_passes_and_the_old_riser_fails():
    f, rep = _fails(_project(level=True))
    assert f == [], f
    r = rep["layouts"]["street"][0]
    assert r["paths"] > 50 and r["apex"]["max_dev_m"] <= vf.APEX_TOL_M and r["steep_road_tris"] == 0
    f, _ = _fails(_project(level=False))
    kinds = {m for x in f for m in re.findall(r": (\(\d\))", x)}
    assert {"(5)", "(6)"} <= kinds and ("(1)" in kinds or "(2)" in kinds or "(3)" in kinds), f


def test_grass_in_the_lane_fails_past_2_cm_only():
    f, _ = _fails(_project(grass_over=0.05))
    assert any("(4)" in x for x in f), f
    f, rep = _fails(_project(grass_over=0.01))
    assert not any("(4)" in x for x in f), f
    assert rep["layouts"]["street"][0]["grass_on_top"] > 0


def test_a_pinch_off_its_midpoint_fails():
    # the record says the legs meet at X, but the built X stands at the other rule's height
    d = _project(level=False)
    f, _ = _fails(d)
    assert any("(6)" in x and "not the midpoint" in x for x in f), f


def test_race_walls_inside_and_outside_no_routes_band():
    f, rep = _fails(_project(race=True, wall_delta=0.25))
    assert not any("(7)" in x for x in f), f
    assert abs(rep["layouts"]["race_cw"][0]["wall_worst_delta_m"]) <= vf.WALL_BAND_M
    f, _ = _fails(_project(race=True, wall_delta=0.5))
    assert any("(7)" in x for x in f), f


def test_the_authored_race_kerb_lip_passes_a_taller_one_fails():
    f, rep = _fails(_project(race=True, kerb_lip=0.045))
    assert f == [], f
    assert 0.03 < rep["layouts"]["race_cw"][0]["kerb_lip_max_m"] <= vf.KERB_LIP_M
    f, _ = _fails(_project(race=True, kerb_lip=0.08))
    assert any("(1)" in x or "(2)" in x for x in f), f


def test_exit_codes():
    assert vf.main([str(_project())]) == 0
    assert vf.main([str(_project(level=False))]) == 1
    d = _project()
    (d / "data" / "mouth_welds.json").unlink()
    assert vf.main([str(d)]) == 2
    assert vf.main([]) == 2

"""The I-8 deck guardrails stand on the curb, not on the pavement (v0.18.0, the gates lens): audit_mesh D read every
panel vertex placed ON the carriageway's edge line as a wall standing on the road. build_loop_blend.py imports bpy, so
the function is lifted out of its source with ast and run on a straight deck. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

from scripts.geometry import audit_mesh as A
from scripts.geometry import ribbon

SRC = Path(__file__).resolve().parents[2] / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "blender" / \
    "build_loop_blend.py"


def _guardrails():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "build_guardrails")
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "GUARDRAIL_SET_M" for t in n.targets))]
    assert len(keep) == 2, "build_guardrails / GUARDRAIL_SET_M not found"
    ns = {"math": math, "_i8_nearest": lambda i8, x, z: (abs(z - 50.0), None)}   # the I-8 crosses at z = 50
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SRC), "exec"), ns)
    return ns


def test_deck_rails_stand_outside_the_pavement_so_audit_d_reads_none():
    ns = _guardrails()
    assert 0.1 <= ns["GUARDRAIL_SET_M"] <= 0.3
    cl = [(0.0, 5.0, float(z)) for z in range(0, 101, 3)]
    widths = [21.0] * len(cl)
    rails = ns["build_guardrails"](cl, widths, i8=[(0.0, 0.0)])
    assert rails["vertices"], "no rail over the crossing"
    # every panel vertex is set_m outside the 10.5 m half-width, on both sides
    lat = sorted({round(abs(x), 3) for x, _y, _z in rails["vertices"]})
    assert lat == [round(10.5 + ns["GUARDRAIL_SET_M"], 3)], lat
    # audit_mesh's own D test (a wall vertex within 1.2 m of a road triangle under it) finds none
    road = ribbon.road_ribbon(cl, widths)
    tris = [tuple(road["vertices"][i] for i in t) for t in road["tris"]]
    th = A._tri_hash(tris, 8.0)
    on_road = [v for v in rails["vertices"] if A._surf_at(th, 8.0, v[0], v[2], v[1], dy_max=1.2) is not None]
    assert on_road == [], on_road[:4]
    # ...where the old placement (set_m = 0, on the edge line) put every one of them on the road
    old = ns["build_guardrails"](cl, widths, i8=[(0.0, 0.0)], set_m=0.0)
    assert all(A._surf_at(th, 8.0, v[0], v[2], v[1], dy_max=1.2) is not None for v in old["vertices"])

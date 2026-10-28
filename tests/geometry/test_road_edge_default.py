"""Every road-edge config must reach a shoulder: the edge chain in build_mesh.build ends in a default.

The natural_ground port (6f1c734) rewrote the chain's `else:` as `elif natural_ground:`, so a track
with neither a sidewalk nor natural ground (every constructed circuit: Pueblo, Aspen, High Plains,
Milford) hit `edge_group` unbound and build_mesh died. A full mesh build is too slow for the suite,
so this reads the source: the `if edge_cfg.get("profile") == "sidewalk"` chain must end in an
`else`, and that `else` must build the constructed shoulder (draped onto grass_surf).
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "scripts" / "geometry" / "build_mesh.py"


def _edge_chain() -> ast.If:
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and "sidewalk" in ast.unparse(node.test) and "edge_cfg" in ast.unparse(node.test):
            return node
    raise AssertionError("road-edge chain (edge_cfg profile == 'sidewalk') not found in build_mesh.py")


def test_edge_chain_ends_in_a_default():
    node = _edge_chain()
    while len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
        node = node.orelse[0]
    assert node.orelse, "road-edge chain has no else: a constructed track leaves edge_group unbound"
    assigned = {t.id for s in ast.walk(ast.Module(body=node.orelse, type_ignores=[]))
                if isinstance(s, ast.Assign) for el in s.targets
                for t in (el.elts if isinstance(el, ast.Tuple) else [el]) if isinstance(t, ast.Name)}
    assert "edge_group" in assigned


def test_constructed_shoulder_drapes_onto_the_ground():
    node = _edge_chain()
    while len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
        node = node.orelse[0]
    calls = [c for c in ast.walk(ast.Module(body=node.orelse, type_ignores=[]))
             if isinstance(c, ast.Call) and ast.unparse(c.func).endswith("road_shoulder")]
    kws = [{k.arg for k in c.keywords} for c in calls]
    assert any({"ground", "fill_apron"} <= k for k in kws), \
        "no road_shoulder(ground=..., fill_apron=...) in the default branch: the constructed corridor is gone"

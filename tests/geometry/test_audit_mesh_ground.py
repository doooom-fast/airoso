"""scripts/geometry/audit_mesh.py MESH-GROUND mode (opt-in: track.config.json gates.audit.mesh_ground; 2026-10-12).

A Blender-first track writes no ground.local.json raster and no environment.obj, so classes G and H were skipped
(null) and a null read as 0 downstream. With the opt-in, H nominates and confirms on the BUILT grass mesh and G reads
the built OBJ's prop groups; without it the audit is exactly as before (null).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.geometry import audit_mesh


def _obj(path: Path, groups):
    lines, off = [], 1
    for name, verts, faces in groups:
        lines.append(f"o {name}")
        lines += [f"v {x} {y} {z}" for x, y, z in verts]
        lines += ["f " + " ".join(str(off + i) for i in f) for f in faces]
        off += len(verts)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _strip(x0, x1, z0, z1, y0, y1, step=2.0):
    """a quad strip from z0 (height y0) to z1 (height y1) along x"""
    verts, faces = [], []
    n = int((x1 - x0) / step)
    for i in range(n + 1):
        x = x0 + i * step
        verts += [(x, y0, z0), (x, y1, z1)]
    for i in range(n):
        a = 2 * i
        faces += [(a, a + 2, a + 3), (a, a + 3, a + 1)]
    return verts, faces


def _project(cut_m, opt_in, props=False):
    p = Path(tempfile.mkdtemp())
    (p / "data").mkdir()
    cfg = {"slug": "toy", "gates": {"audit": {"mesh_ground": True}} if opt_in else {}}
    (p / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    pts = [[float(x), 0.0, 0.0] for x in range(0, 101)]
    (p / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [6.0] * len(pts)}),
                                                     encoding="utf-8")
    road = _strip(0, 100, -3.0, 3.0, 0.0, 0.0)
    under = _strip(-2, 102, -3.0, 3.0, -0.02, -0.02)
    cutl = _strip(-2, 102, 3.0, 6.0, -0.02, cut_m)          # one side rises to cut_m 3 m past the edge
    cutr = _strip(-2, 102, -6.0, -3.0, -1.0, -0.02)
    groups = [("1ROAD_road", *road), ("1GRASS_under", *under), ("1GRASS_l", *cutl), ("1GRASS_r", *cutr)]
    if props:
        groups.append(("TREETRUNK_a", [(50.0, 3.0, -20.0), (50.5, 3.0, -20.0), (50.0, 8.0, -20.0)], [(0, 1, 2)]))
        groups.append(("1GRASS_far", *_strip(40, 60, -25.0, -15.0, 0.0, 0.0)))
    _obj(p / "data" / "track.obj", groups)
    return p


def test_without_the_opt_in_g_and_h_stay_skipped():
    r = audit_mesh.audit(_project(1.5, opt_in=False))
    assert r["H_ground_above_deck"] is None and r["G_prop_floating"] is None


def test_mesh_ground_computes_h_on_the_built_grass():
    r = audit_mesh.audit(_project(1.5, opt_in=True))          # 2 m past the edge the bank is 1.0 m over the deck
    assert r["H_ground_above_deck"] > 0 and r["worst_ground_cut_m"] > 0.5, r
    r = audit_mesh.audit(_project(0.05, opt_in=True))         # a bank that stays within 0.10 m: clean
    assert r["H_ground_above_deck"] == 0, r
    assert r["G_prop_floating"] == 0                          # no prop group in the build: nothing can float


def test_mesh_ground_g_reads_the_built_props():
    r = audit_mesh.audit(_project(0.05, opt_in=True, props=True))   # a trunk foot 3 m over the grass
    assert r["G_prop_floating"] > 0, r                         # its 0.8 m columns, as the raster path counts them

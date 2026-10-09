"""Remove the procedural vegetation from loop.blend once TreeFX replaces it.

After tools/export_scatter_blend.py has recorded every position, the cross-quad palms, blob
trees and scrub (PALMFROND_*, PALMTRUNK_*, TREECANOPY, TREETRUNK, SCRUB — ~500k verts of the
kn5) are deleted; CSP TreeFX draws the real models at those positions (tools/make_treefx.py).
Streetlights (LIGHTS) stay until the lamp-model pass.

    blender --background --python tools/strip_scenery_blend.py -- <project-dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

STRIP = ("PALMFROND", "PALMTRUNK", "TREECANOPY", "TREETRUNK", "SCRUB")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    gone = []
    for ob in list(bpy.data.objects):
        if ob.type == "MESH" and ob.name.upper().startswith(STRIP):
            gone.append(f"{ob.name}({len(ob.data.vertices)}v)")
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[strip] removed {len(gone)} procedural scenery mesh(es): {', '.join(gone)}")


main()

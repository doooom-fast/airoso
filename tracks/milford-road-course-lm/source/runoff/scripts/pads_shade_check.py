"""Ledger 0100 item 6: what scenery.bespoke.pads_shade "smooth" changes in a seated pad, measured in Blender on a prepped scene.

    python pads_shade_check.py <prepped.blend> <scratch dir> [<out.json>]

Copies the blend twice into <scratch dir>/{flat,smooth}/, writes a track.config.json beside each (the blend's project's
pads seated on the ground as 1RUNOFF; the second with pads_shade "smooth"), runs tools/seat_pads_blend.py on both, then reads
every 1RUNOFF_apron_* back the way the vendored kn5 writer does (vendor/io_import_accsv/kn5/node_writer.py: one vertex per
position + loop normal + UV + loop tangent, after calc_tangents) and compares: triangles, vertices, writer vertices, positions,
UVs, and each corner's shading normal against its flat face normal (degrees; by corner and by area). The Mac's run (2026-11-22,
Blender 5.1.2) on the 0.1.5 workshop's prepped scene (its one pad, the ride pad) is records/pads_shade_v015_ride_pad.json.
Needs AIROSO_BLENDER (default: the macOS Blender.app) and a track.config.json at <prepped.blend>/../../ (the workshop's).
"""
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[5]
BL = os.environ.get("AIROSO_BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
READ = r'''
import bpy, sys, json
out = sys.argv[sys.argv.index("--") + 1]
res = {}
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.name.startswith("1RUNOFF_apron_"):
        continue
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles(); me.calc_tangents()
    uv = me.uv_layers.active
    seen, rows = set(), []
    for t in me.loop_triangles:
        for li in t.loops:
            l = me.loops[li]
            seen.add((tuple(me.vertices[l.vertex_index].co), tuple(l.normal), tuple(uv.data[li].uv), tuple(l.tangent)))
        a, b, c = (me.vertices[me.loops[li].vertex_index].co for li in t.loops)
        rows.append({"area": ((b - a).cross(c - a)).length / 2, "fn": tuple(t.normal),
                     "ln": [tuple(me.loops[li].normal) for li in t.loops],
                     "co": [tuple(me.vertices[me.loops[li].vertex_index].co) for li in t.loops],
                     "uv": [tuple(uv.data[li].uv) for li in t.loops]})
    res[ob.name] = {"tris": len(me.loop_triangles), "verts": len(me.vertices), "writer_verts": len(seen), "rows": rows}
json.dump(res, open(out, "w"))
'''


def run(blend, scratch):
    proj0 = blend.parents[1]
    cfg = json.loads((proj0 / "track.config.json").read_text(encoding="utf-8"))
    b = cfg["scenery"]["bespoke"]
    b["pads_seat"], b["pads_surface"] = "ground", "1RUNOFF"
    reads = {}
    for mode in ("flat", "smooth"):
        d = scratch / mode
        (d / "data").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(blend, d / "prepped.blend")
        if mode == "smooth":
            b["pads_shade"] = "smooth"
        (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        subprocess.run([BL, "--background", "--python-exit-code", "1", "--python", str(REPO / "tools" / "seat_pads_blend.py"),
                        "--", str(d / "prepped.blend"), "--project", str(d)], check=True, capture_output=True)
        (scratch / "read.py").write_text(READ, encoding="utf-8")
        subprocess.run([BL, "--background", str(d / "prepped.blend"), "--python", str(scratch / "read.py"), "--",
                        str(d / "read.json")], check=True, capture_output=True)
        reads[mode] = json.loads((d / "read.json").read_text())
    return reads


def compare(f, s):
    ang, w = [], []
    worst_real = 0.0
    for a, b in zip(f["rows"], s["rows"]):
        fn = np.array(a["fn"])
        for ln in b["ln"]:
            d = math.degrees(math.acos(float(np.clip(np.dot(fn, ln) / np.linalg.norm(ln), -1, 1))))
            ang.append(d)
            w.append(a["area"] / 3)
            if a["area"] > 1e-3:
                worst_real = max(worst_real, d)
    ang, w = np.array(ang), np.array(w)
    o = np.argsort(ang)
    cw = np.cumsum(w[o]) / w.sum()
    by_area = {q: round(float(ang[o][min(len(o) - 1, np.searchsorted(cw, q / 100))]), 3) for q in (50, 95, 99)}
    return {"tris": f["tris"], "verts": f["verts"], "writer_verts_flat": f["writer_verts"], "writer_verts_smooth": s["writer_verts"],
            "positions_identical": all(a["co"] == b["co"] for a, b in zip(f["rows"], s["rows"])),
            "uvs_identical": all(a["uv"] == b["uv"] for a, b in zip(f["rows"], s["rows"])),
            "normal_change_deg_by_corner": {q: round(float(np.percentile(ang, q)), 3) for q in (50, 95, 99)},
            "normal_change_deg_by_area": by_area,
            "normal_change_deg_max_on_faces_over_10cm2": round(worst_real, 2),
            "area_share_over_2deg_pct": round(100 * float(w[ang > 2].sum() / w.sum()), 4),
            "bytes_at_44B_per_writer_vertex": {"flat": 44 * f["writer_verts"], "smooth": 44 * s["writer_verts"]}}


def main():
    blend, scratch = Path(sys.argv[1]), Path(sys.argv[2])
    reads = run(blend, scratch)
    out = {"_doc": "ledger 0100 item 6: tools/seat_pads_blend.py flat vs pads_shade smooth on one prepped scene "
                   "(source/runoff/scripts/pads_shade_check.py)", "blend": blend.name,
           "pads": {k: compare(reads["flat"][k], reads["smooth"][k]) for k in sorted(reads["flat"])}}
    txt = json.dumps(out, indent=1)
    print(txt)
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

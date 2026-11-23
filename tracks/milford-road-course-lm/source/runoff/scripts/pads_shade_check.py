"""Ledger 0100 item 6 / round 1b: what scenery.bespoke.pads_shade does to the seated pads, measured in Blender on a prepped scene.

    python pads_shade_check.py <prepped.blend> <scratch dir> [--config <track.config.json>] [--modes flat,smooth,crease10]
                               [--json <out.json>]

<prepped.blend>: a scene after engine-july's prep (and the far-ground prep), BEFORE seat_pads (its PADAPRON_* still the author's).
The config defaults to <prepped.blend>/../../track.config.json (a workshop's). Each mode copies the blend into <scratch>/<mode>/,
writes the config beside it with the pads seated on the ground as 1RUNOFF and:
  flat       no pads_shade (0.1.13);
  smooth     pads_shade "smooth", one area-weighted normal per vertex (0.1.14);
  creaseN    pads_shade "smooth" + pads_shade_crease_deg N (round 1b);
runs tools/seat_pads_blend.py, then reads every 1RUNOFF_apron_* back the way the vendored kn5 writer does
(vendor/io_import_accsv/kn5/node_writer.py: one vertex per position + loop normal + UV + loop tangent, after calc_tangents)
and measures what source/runoff/scripts/pads_kn5_check.py measures on a built kn5: triangles, writer vertices, and each
corner's normal against its own face's normal (degrees; by area p50 / p95 / p99, the largest on a face over 10 cm2, the area
share over 2 deg). Records:
  records/pads_shade_v015_ride_pad.json   the 0.1.5 workshop's prepped scene, its one pad (item 6, flat vs smooth)
  records/pads_shade_0113_20pads.json     0.1.13's synced-out loop.blend through engine-july's prep: the 20 pads (round 1b)
Needs AIROSO_BLENDER (default: the macOS Blender.app).
"""
import argparse
import json
import os
import shutil
import subprocess
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
    seen, area, fn, ln = set(), [], [], []
    for t in me.loop_triangles:
        for li in t.loops:
            l = me.loops[li]
            seen.add((tuple(me.vertices[l.vertex_index].co), tuple(l.normal), tuple(uv.data[li].uv), tuple(l.tangent)))
        a, b, c = (me.vertices[me.loops[li].vertex_index].co for li in t.loops)
        cr = (b - a).cross(c - a)
        area.append(cr.length / 2)
        fn.append(tuple(cr.normalized()) if cr.length > 0 else (0.0, 0.0, 1.0))
        ln.append([tuple(me.loops[li].normal) for li in t.loops])
    res[ob.name] = {"tris": len(me.loop_triangles), "verts": len(me.vertices), "writer_verts": len(seen),
                    "area": area, "fn": fn, "ln": ln}
json.dump(res, open(out, "w"))
'''


def mode_cfg(cfg, mode):
    c = json.loads(json.dumps(cfg))
    b = c["scenery"]["bespoke"]
    b["pads_seat"], b["pads_surface"] = "ground", "1RUNOFF"
    for k in ("pads_shade", "pads_shade_crease_deg"):
        b.pop(k, None)
    if mode == "smooth" or mode.startswith("crease"):
        b["pads_shade"] = "smooth"
    if mode.startswith("crease"):
        b["pads_shade_crease_deg"] = float(mode[len("crease"):])
    return c


def stats(m):
    area = np.asarray(m["area"], float)
    fn = np.asarray(m["fn"], float)
    ln = np.asarray(m["ln"], float)
    ln = ln / np.maximum(np.linalg.norm(ln, axis=2, keepdims=True), 1e-12)
    ang = np.degrees(np.arccos(np.clip(np.einsum("tj,tkj->tk", fn, ln), -1, 1)))
    w = np.repeat(area / 3, 3)
    flat = ang.ravel()
    o = np.argsort(flat)
    cw = np.cumsum(w[o]) / max(w.sum(), 1e-12)
    big = area > 1e-3
    return {"tris": m["tris"], "verts": m["verts"], "writer_verts": m["writer_verts"],
            "deg_by_area": {q: round(float(flat[o][min(len(o) - 1, np.searchsorted(cw, q / 100))]), 3) for q in (50, 95, 99)},
            "max_deg_on_faces_over_10cm2": round(float(ang[big].max()) if big.any() else 0.0, 2),
            "area_share_over_2deg_pct": round(100 * float(w[flat > 2].sum() / max(w.sum(), 1e-12)), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("scratch")
    ap.add_argument("--config")
    ap.add_argument("--modes", default="flat,smooth")
    ap.add_argument("--json")
    a = ap.parse_args()
    blend, scratch = Path(a.blend), Path(a.scratch)
    cfg = json.loads(Path(a.config or blend.parents[1] / "track.config.json").read_text(encoding="utf-8"))
    out = {"_doc": "ledger 0100: tools/seat_pads_blend.py's pads by pads_shade mode on one prepped scene, read as the kn5 writer "
                   "keeps them (source/runoff/scripts/pads_shade_check.py)", "blend": blend.name, "modes": {}}
    for mode in a.modes.split(","):
        d = scratch / mode
        (d / "data").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(blend, d / "prepped.blend")
        (d / "track.config.json").write_text(json.dumps(mode_cfg(cfg, mode)), encoding="utf-8")
        r = subprocess.run([BL, "--background", "--python-exit-code", "1", "--python", str(REPO / "tools" / "seat_pads_blend.py"),
                            "--", str(d / "prepped.blend"), "--project", str(d)], capture_output=True, text=True)
        log = [ln for ln in r.stdout.splitlines() if ln.startswith("[seat-pads]")]
        if r.returncode:
            raise SystemExit(f"{mode}: seat_pads failed\n" + "\n".join(log) + r.stderr[-2000:])
        (scratch / "read.py").write_text(READ, encoding="utf-8")
        subprocess.run([BL, "--background", str(d / "prepped.blend"), "--python", str(scratch / "read.py"), "--",
                        str(d / "read.json")], check=True, capture_output=True)
        rd = json.loads((d / "read.json").read_text())
        pads = {k: stats(rd[k]) for k in sorted(rd, key=lambda n: int(n.rsplit("_", 1)[1]))}
        wv = sum(p["writer_verts"] for p in pads.values())
        out["modes"][mode] = {"writer_verts": wv, "tris": sum(p["tris"] for p in pads.values()),
                              "bytes_vertices_44B": 44 * wv, "seat_pads_log": log, "pads": pads}
        print(f"[pads-shade] {mode}: {len(pads)} pads, {wv} writer vertices for {out['modes'][mode]['tris']} triangles; worst p95 "
              f"{max(p['deg_by_area'][95] for p in pads.values()):.3f} deg, worst max "
              f"{max(p['max_deg_on_faces_over_10cm2'] for p in pads.values()):.2f} deg")
    txt = json.dumps(out, indent=1)
    if a.json:
        Path(a.json).write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

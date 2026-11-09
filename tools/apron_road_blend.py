"""The mainline's measured APRON as its own drivable road object (ledger 0085, Pikes Peak; opt-in route.edge_apron_file).

The assembler sweeps the apron as the edge strip's sidewalk on one side (scripts-v021 ribbon.curb_sidewalk apron:
4.2-14.9 m wide, falling -2.9..-8.5 %, its lip on the measured ground). In CURB it would ship as 1KERB_sidewalk, and
engine-july's prep (build_kn5_loop._conform_and_reseat) pins the ground under 1ROAD only: past the LANE edge it holds a
3 m band at the lane edge's height and feathers it to the natural ground over 6 m more. With a 6 m apron falling 0.4 m,
that band and feather stand over the apron's low outer lip (up to ~0.2 m, the anti-poke only pushes ground DOWN under a
drivable sheet). As a 1ROAD object the apron is part of the footprint: the ground under it is pinned to it, and the band
starts at its lip, which stands on the measured ground. The aerial shows it paved (a lighter band with its painted line
all round the inside), so ROAD physics is the real surface; it keeps CURB's material (the concrete look).

This step moves the declared side's CURB faces of the MAINLINE (tools/mouth_weld.mesh_layout: CURB is per line two side
blocks, rows x 4 profile points) into a new object 1ROAD_apron with copies of their vertices, UVs and materials, and
deletes the faces from CURB (FACES_ONLY: CURB keeps every vertex, so every later step that reads its layout by index still
can). Connectors' strips are not touched.

Self-checks (exit 1, loop.blend not saved): CURB is not the assembler's layout; the apron file's side is not "left" or
"right"; fewer faces moved than the side's rows. No route.edge_apron_file = no-op (Lake Murray and every other track).
Run after strip_seam (its seam reads the strip's lip off CURB's layout) and BEFORE gap_mouths (which deletes with its
orphaned vertices: CURB is no longer the layout after it); the mouths' windows (gap_mouths' own rule) stay in CURB for it.

    blender --background --python-exit-code 1 --python tools/apron_road_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402

NAME = "1ROAD_apron"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rel = (cfg.get("route") or {}).get("edge_apron_file")
    if not rel:
        print("[apron-road] no route.edge_apron_file: nothing to do")
        return
    ap = json.loads((proj / rel).read_text(encoding="utf-8"))
    if ap.get("side") not in ("left", "right"):
        raise SystemExit(f"[apron-road] FATAL: {rel} side {ap.get('side')!r}; not saved")
    side = 1 if ap["side"] == "left" else -1
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8"))["connectors"] if cp.exists() else []
    lay = mw.mesh_layout([tuple(p) for p in local["points_xyz_m"]], conns)
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb = bpy.data.objects.get("CURB")
    if curb is None:
        raise SystemExit("[apron-road] FATAL: no CURB in loop.blend; not saved")
    if len(curb.data.vertices) != lay["_curb_total"]:
        raise SystemExit(f"[apron-road] FATAL: CURB has {len(curb.data.vertices)} vertices, the assembler's layout "
                         f"{lay['_curb_total']}; not saved")
    rows = lay["MAINLINE"]["rows"]
    lo = mw.curb_index(lay, "MAINLINE", 0, side, 0)
    hi = mw.curb_index(lay, "MAINLINE", rows - 1, side, mw.CURB_P - 1)
    bm = bmesh.new()
    bm.from_mesh(curb.data)
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    # the mouths' windows stay in CURB for tools/gap_mouths_blend.py (it runs AFTER this step and deletes them, the
    # apron opening where a road leaves: its own rule, mouth_weld.gap_window on mouths.json's cut station, a face goes
    # when both its stations are in the window). gap_mouths deletes with context FACES (its orphaned vertices go too),
    # so this step must come first: after it CURB is no longer the assembler's layout
    skip = set()
    mp = data / "mouths.json"
    pts_m = local["points_xyz_m"]
    closed_m = mw.is_closed(pts_m)
    for mo in (json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else []):
        if mo.get("host") != "MAINLINE" or int(mo.get("side", 0)) != side:
            continue
        if "host_seg" in mo:
            skip.update(mw.gap_window(pts_m, rows, closed_m, int(mo["host_seg"]), float(mo["host_t"]),
                                      float(mo["connector_width_m"]), float(mo.get("angle_deg") or 90.0)))
        else:
            raise SystemExit(f"[apron-road] FATAL: mouth {mo.get('piece')} has no host_seg (an older mouths.json); not saved")
    base = mw.curb_index(lay, "MAINLINE", 0, side, 0)

    def in_gap(f):
        return {(v.index - base) // mw.CURB_P for v in f.verts} <= skip
    take = [f for f in bm.faces if all(lo <= v.index <= hi for v in f.verts) and not in_gap(f)]
    n_gap = sum(1 for f in bm.faces if all(lo <= v.index <= hi for v in f.verts) and in_gap(f))
    if len(take) + n_gap < rows:
        raise SystemExit(f"[apron-road] FATAL: {len(take) + n_gap} faces on the apron side for {rows} rows; not saved")
    # the new object: its own vertices (a copy), faces, UVs and material slots
    nb = bmesh.new()
    nuv = nb.loops.layers.uv.new("UVMap")
    vmap = {}
    for f in take:
        for v in f.verts:
            if v.index not in vmap:
                vmap[v.index] = nb.verts.new(v.co)
    for f in take:
        nf = nb.faces.new([vmap[v.index] for v in f.verts])
        nf.material_index = f.material_index
        nf.smooth = f.smooth
        if uv is not None:
            for la, lb in zip(f.loops, nf.loops):
                lb[nuv].uv = la[uv].uv
    me = bpy.data.meshes.new(NAME)
    nb.to_mesh(me)
    nb.free()
    for m in curb.data.materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(NAME, me)
    for c in curb.users_collection:
        c.objects.link(ob)
    ob.matrix_world = curb.matrix_world.copy()
    n_take = len(take)
    bmesh.ops.delete(bm, geom=take, context="FACES_ONLY")
    bm.to_mesh(curb.data)
    bm.free()
    curb.data.update()
    if len(curb.data.vertices) != lay["_curb_total"]:
        raise SystemExit("[apron-road] FATAL: CURB lost vertices; not saved")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[apron-road] {ap['side']} apron: {n_take} CURB faces ({rows} rows) -> {NAME} ({len(vmap)} vertices, CURB's "
          f"material); {n_gap} faces in {len(skip)} mouth-window rows left for gap_mouths; CURB keeps all "
          f"{lay['_curb_total']} vertices; saved loop.blend")


main()

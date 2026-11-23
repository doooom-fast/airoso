"""The edge strip (CURB) of a long lap cut into pieces under AC's vertex cap BEFORE the prep (ledger 0078 round 6).

engine-july's prep (build_kn5_loop._split_large) cuts every non-terrain mesh over 60,000 vertices into equal-width bands
along its longest axis. A 24.9 km mountain lap's strip (the Lariat: 14,444 rows x 2 sides x 4 profile points = 115,552
vertices) is not spread evenly along any axis, so one band kept 76,510 and the prep refused it ("AC silently drops
over-cap meshes"). This step cuts the strip along the LINE instead: each piece a contiguous run of rows (both sides),
at most PIECE_VERTS vertices, named with the AC name the prep would give it (1KERB_sidewalk_lm<k>: the prep's rename
leaves an AC name as it is, pbr binds the 1KERB_SIDEWALK row, the physics stay KERB). Nothing moves. A strip under the
cap is left alone (the prep does what it always did). Opt-in: a track lists the draft step `split_strip` last.

BALANCED (opt-in track.config.json `route.split_strip_balanced` true; ledger 0098, Sand Creek 0.2.9): a strip that also
carries the side streets' strips has no single row layout, so its faces are tiled by recursive MEDIAN bisection of their
centres along the group's longer horizontal extent (the prep's own balanced_face_tiles rule for the terrain) until every
piece holds at most PIECE_VERTS vertices; the same names, the same checks. Sand Creek 0.2.9's strip (E 56th's 2.5 km and
13 new mouths' returns) left one of the prep's equal-width bands at 67,258 vertices, and the prep refused it.

    blender --background --python-exit-code 1 --python tools/split_strip_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402

CAP = 60000          # engine-july's SPLIT_CAP: a mesh under it is never cut
PIECE_VERTS = 50000  # [invented] each piece's ceiling, under the cap with room for the prep's face-up pass
NAME = "1KERB_sidewalk_lm"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8"))["connectors"] if cp.exists() else []
    lay = mw.mesh_layout([tuple(p) for p in local["points_xyz_m"]], conns)
    rows = lay["MAINLINE"]["rows"]
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("CURB")
    if ob is None:
        print("[split-strip] no CURB: nothing to do")
        return
    n = len(ob.data.vertices)
    if n <= CAP:
        print(f"[split-strip] CURB has {n} vertices (<= {CAP}): left to the prep")
        return
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    if (cfg.get("route") or {}).get("split_strip_balanced") is True:
        return balanced(ob, n)
    if conns:
        raise SystemExit("[split-strip] FATAL: connectors in CURB (the row layout below is the mainline's alone)")
    if n != lay["_curb_total"]:
        raise SystemExit(f"[split-strip] FATAL: CURB has {n} verts, the assembler's layout says {lay['_curb_total']}")
    # the row of every CURB vertex (both sides' blocks), so each face goes to the piece of its lowest row
    row_of = [0] * n
    for side in (1, -1):
        for r in range(rows):
            for p in range(mw.CURB_P):
                row_of[mw.curb_index(lay, "MAINLINE", r, side, p)] = r
    k = math.ceil(n / PIECE_VERTS)
    per = math.ceil(rows / k)
    me = ob.data
    pieces = []
    for i in range(k):
        lo, hi = i * per, min(rows, (i + 1) * per)
        bm = bmesh.new(); bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        kill = [f for f in bm.faces if not (lo <= min(row_of[v.index] for v in f.verts) < hi)]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        nm = bpy.data.meshes.new(f"{NAME}{i}")
        bm.to_mesh(nm); bm.free()
        for m in me.materials:
            nm.materials.append(m)
        o2 = bpy.data.objects.new(f"{NAME}{i}", nm)
        for c in ob.users_collection:
            c.objects.link(o2)
        o2.matrix_world = ob.matrix_world.copy()
        pieces.append((o2.name, len(nm.vertices), lo, hi))
    if any(v > CAP for _, v, _, _ in pieces):
        raise SystemExit(f"[split-strip] FATAL: a piece over the cap: {pieces}; loop.blend not saved")
    if sum(len(bpy.data.objects[nm].data.polygons) for nm, *_ in pieces) != len(me.polygons):
        raise SystemExit("[split-strip] FATAL: the pieces do not hold every strip face once; loop.blend not saved")
    bpy.data.objects.remove(ob, do_unlink=True)
    print(f"[split-strip] CURB ({n} vertices, {rows} rows) cut along the line into {len(pieces)} pieces: "
          + ", ".join(f"{nm} rows {lo}-{hi - 1} ({v} v)" for nm, v, lo, hi in pieces) + "; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


def balanced_groups(centres, face_verts, cap):
    """face-index groups, each touching at most ``cap`` unique vertices: recursive median bisection of the face centres
    along the group's longer horizontal extent (ties by the other axis, then the index). Pure python"""
    out = []

    def nverts(fs):
        return len({v for f in fs for v in face_verts[f]})

    def rec(fs):
        if len(fs) < 2 or nverts(fs) <= cap:
            out.append(fs)
            return
        xs = [centres[f][0] for f in fs]
        zs = [centres[f][1] for f in fs]
        ax = 0 if (max(xs) - min(xs)) >= (max(zs) - min(zs)) else 1
        o = sorted(fs, key=lambda f: (centres[f][ax], centres[f][1 - ax], f))
        h = len(o) // 2
        rec(o[:h])
        rec(o[h:])
    rec(list(range(len(face_verts))))
    return out


def balanced(ob, n):
    me = ob.data
    groups = balanced_groups([(p.center[0], p.center[1]) for p in me.polygons], [tuple(p.vertices) for p in me.polygons],
                             PIECE_VERTS)
    gid = [0] * len(me.polygons)
    for k, g in enumerate(groups):
        for f in g:
            gid[f] = k
    pieces = []
    for k in range(len(groups)):
        bm = bmesh.new(); bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        kill = [f for f in bm.faces if gid[f.index] != k]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        nm = bpy.data.meshes.new(f"{NAME}{k}")
        bm.to_mesh(nm); bm.free()
        for m in me.materials:
            nm.materials.append(m)
        o2 = bpy.data.objects.new(f"{NAME}{k}", nm)
        for c in ob.users_collection:
            c.objects.link(o2)
        o2.matrix_world = ob.matrix_world.copy()
        pieces.append((o2.name, len(nm.vertices), len(nm.polygons)))
    if any(v > CAP for _, v, _ in pieces):
        raise SystemExit(f"[split-strip] FATAL: a piece over the cap: {pieces}; loop.blend not saved")
    if sum(f for *_, f in pieces) != len(me.polygons):
        raise SystemExit("[split-strip] FATAL: the pieces do not hold every strip face once; loop.blend not saved")
    nf = len(me.polygons)
    bpy.data.objects.remove(ob, do_unlink=True)
    print(f"[split-strip] CURB ({n} vertices, {nf} faces, side streets' strips with it) tiled by median bisection into "
          f"{len(pieces)} pieces: " + ", ".join(f"{nm} ({v} v)" for nm, v, _ in pieces) + "; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(PROJ / "loop.blend"))


PROJ = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else None
main()

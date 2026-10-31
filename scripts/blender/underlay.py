"""The data underlay: the engine's draft geometry into an editable loop.blend (fleet/REALISM.md §4;
tracks/lookout-lariat/V3-PLAN.md P2 step 3 — the generalisation of San Diego's build_loop_blend.py).

WHAT IT DOES. ``data/track.obj`` — what ``scripts.geometry.build_mesh`` drafts from the real centreline,
real widths and real 3DEP elevation: the road ribbon (``1ROAD_*``), the verge or sidewalk, the kerbs
(``1KERB_*``), the walls the engine stands where the data says a drop or a blind corner is (``1WALL_*``,
``BARRIER_*``, ``RETWALL_*``, ``ROCKCUT_*``), the painted markings (``YLINE``, ``ROADTEXT``, ``MARKINGS``) and the
ground tiles (``1GRASS_*``) — becomes mesh objects in ``loop.blend``, one per OBJ group, under the ``GEN_*``
collections of the collection contract. A road NETWORK's draft (``scripts.geometry.build_network_mesh``: the
same AC prefixes, tiled — ``1ROAD_part*``, ``1WALL_part*``, ``1RUNOFF_median*``, ``1GRASS_<i>_<j>`` tiles + ``1GRASS_skirt`` + ``1GRASS_verge*``, ``HWYSTRUCT_via*``,
``MARKINGS_part*``) writes the same ``data/track.obj`` and needs nothing else here; it has no single centreline,
so ``GEN_refs`` stays empty for it:

    GEN_road      1ROAD_* 1RUNOFF_*           GEN_kerb   1KERB_*
    GEN_terrain   1GRASS_* / GRASS*           GEN_wall   1WALL_* BARRIER_* RETWALL_* ROCKCUT_*
    GEN_misc      everything else the OBJ carries (markings, text)
    GEN_refs      the centreline as a poly curve + a station marker every 500 m + REF_start (never exported:
                  the prep drops every non-mesh object)

The objects keep their OBJ group names: the prep (``scripts/ac/build_kn5_loop.py``) keys everything on those
AC prefixes (1ROAD / 1KERB / 1GRASS: the terrain conform, the carriageway carve, the face-up flip, the
materials), passes unknown names through its rename map unchanged, and splits anything over the 16-bit cap.
The frame is the prep's own OBJ import (``_add_obj_meshes``): local (E, up, N) -> Blender (E, N, up) as
(x, y, z) -> (x, z, y), faces re-wound to cancel the reflection, UVs kept.

THE COLLECTION CONTRACT (REALISM §4): on a re-run every ``GEN_*`` collection is emptied and rebuilt; nothing
named ``AUTH_*`` — and nothing outside a ``GEN_*`` collection — is ever touched, and the scene is never reset.
Promoting an object to an ``AUTH_*`` collection is the author saying "this is mine now".

RECORD: ``data/underlay.report.json`` — the OBJ's md5, every group with its collection and counts, the
authored objects that were left alone, the Blender version. ``--plan`` prints the plan without Blender.

    blender --background --python-exit-code 1 --python scripts/blender/underlay.py -- <project-dir>
    python -m scripts.blender.underlay <project-dir> --plan          # no Blender: what WOULD be built
"""
from __future__ import annotations

import hashlib
import json
import sys
from itertools import pairwise
from pathlib import Path

GEN_PREFIX = "GEN_"
AUTH_PREFIX = "AUTH_"
COLLECTIONS = ("GEN_road", "GEN_kerb", "GEN_terrain", "GEN_wall", "GEN_misc", "GEN_refs")
REF_STATION_M = 500.0
REPORT = "underlay.report.json"
# the prep's DOUBLE_SIDE rule (build_kn5_loop.py): barriers render and collide from both sides. The
# underlay does NOT duplicate faces — the prep does, at prep time, on the same names — so a GEN_ object is
# exactly one copy of the engine's geometry and an author edits one sheet, not two.


# --- pure helpers (no bpy) -------------------------------------------------------------------------------------

def collection_for(group_name: str) -> str:
    """Which GEN_ collection an OBJ group belongs in, by its AC prefix (case-insensitive)."""
    n = group_name.upper()
    if n.startswith(("1ROAD", "1RUNOFF")):          # the drivable surfaces: pavement and the paved run-off
        return "GEN_road"
    if n.startswith("1KERB"):
        return "GEN_kerb"
    if n.startswith(("1GRASS", "GRASS")):
        return "GEN_terrain"
    if n.startswith(("1WALL", "BARRIER", "RETWALL", "ROCKCUT")):
        return "GEN_wall"
    return "GEN_misc"


def to_blender(v):
    """local (E, up, N) -> Blender (E, N, up): the prep's own remap, (x, y, z) -> (x, z, y)."""
    x, y, z = v
    return (x, z, y)


def parse_obj(path: Path):
    """(verts, uvs, groups) — groups: [(name, [[(vi, ti|None), ...], ...])], indices 0-based. The same reading
    as build_kn5_loop._add_obj_meshes: 'o' starts a group, 'f' tokens are v or v/vt (normals ignored)."""
    verts, uvs, groups = [], [], []
    cur = None
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.split()
        if not s:
            continue
        if s[0] == "v":
            verts.append((float(s[1]), float(s[2]), float(s[3])))
        elif s[0] == "vt":
            uvs.append((float(s[1]), float(s[2])))
        elif s[0] == "o":
            cur = (ln[2:].strip(), [])
            groups.append(cur)
        elif s[0] == "f" and cur is not None:
            face = []
            for tok in s[1:]:
                p = tok.split("/")
                face.append((int(p[0]) - 1, int(p[1]) - 1 if len(p) > 1 and p[1] else None))
            cur[1].append(face)
    return verts, uvs, groups


def group_to_mesh(verts, uvs, faces):
    """One OBJ group -> (blender_verts, blender_faces, blender_uvs_per_vert, has_uv): vertices re-indexed to the
    group, remapped into Blender's frame, every face re-wound (the remap is a reflection)."""
    has_uv = all(t is not None for fc in faces for _, t in fc)
    idx, bverts, buvs, bfaces = {}, [], [], []
    for fc in faces:
        bf = []
        for vi, ti in fc:
            if vi not in idx:
                idx[vi] = len(bverts)
                bverts.append(to_blender(verts[vi]))
                buvs.append(uvs[ti] if (has_uv and ti is not None) else (0.0, 0.0))
            bf.append(idx[vi])
        bfaces.append(tuple(reversed(bf)))
    return bverts, bfaces, buvs, has_uv


def md5_of(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def plan(proj: Path) -> dict:
    """What the underlay would build for this project, from its data alone (no Blender). Raises SystemExit
    with the reason when the project is not ready (no track.obj: run scripts.geometry.build_mesh first)."""
    proj = Path(proj)
    cfg_p = proj / "track.config.json"
    if not cfg_p.is_file():
        raise SystemExit(f"[underlay] {proj}: no track.config.json")
    cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    obj = proj / "data" / "track.obj"
    if not obj.is_file():
        raise SystemExit(f"[underlay] {obj} is missing — the underlay is the engine's draft; run the draft's mesh "
                         f"step first (python -m scripts.geometry.build_mesh {proj}; a road network: "
                         f"scripts.geometry.build_network_mesh)")
    verts, _uvs, groups = parse_obj(obj)
    rows = []
    for name, faces in groups:
        if not faces:
            continue
        used = {vi for fc in faces for vi, _ in fc}
        rows.append({"name": name, "collection": collection_for(name), "verts": len(used), "faces": len(faces)})
    if not rows:
        raise SystemExit(f"[underlay] {obj} has no faces")
    cl = proj / "data" / "centerline.local.json"
    refs = None
    if cl.is_file():
        local = json.loads(cl.read_text(encoding="utf-8"))
        pts = local.get("points_xyz_m") or []
        refs = {"points": len(pts), "stations": int(_arc_length(pts) // REF_STATION_M) + 1 if len(pts) > 1 else 0,
                "closed": bool(cfg.get("loop", True))}
    return {"project": str(proj), "slug": cfg.get("slug"), "source_obj": "data/track.obj", "obj_md5": md5_of(obj),
            "obj_verts": len(verts), "groups": rows, "collections": sorted({r["collection"] for r in rows}),
            "refs": refs, "frame": "local (E,up,N) -> Blender (E,N,up) as (x,y,z)->(x,z,y), faces re-wound"}


def _arc_length(pts) -> float:
    s = 0.0
    for a, b in pairwise(pts):
        s += ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2) ** 0.5
    return s


def _station_points(pts, every_m: float):
    """[(station_m, (x, y, z))] every ``every_m`` along the local-frame polyline, plus the start."""
    out = [(0.0, tuple(pts[0]))]
    acc, nxt = 0.0, every_m
    for a, b in pairwise(pts):
        seg = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2) ** 0.5
        while seg > 0 and acc + seg >= nxt:
            t = (nxt - acc) / seg
            out.append((nxt, tuple(a[i] + t * (b[i] - a[i]) for i in range(3))))
            nxt += every_m
        acc += seg
    return out


# --- the Blender side ------------------------------------------------------------------------------------------

def _project_dir(argv) -> tuple[Path, bool]:
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    plan_only = "--plan" in args
    args = [a for a in args if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: blender --background --python-exit-code 1 --python scripts/blender/underlay.py -- "
                         "<project-dir>   |   python -m scripts.blender.underlay <project-dir> --plan")
    return Path(args[0]).resolve(), plan_only


def _purge_gen(bpy) -> tuple[list[str], list[str]]:
    """Empty and remove every GEN_* collection (objects + orphaned mesh/curve data). Returns (removed object
    names, the AUTH_* object names that were left alone)."""
    removed = []
    for col in [c for c in bpy.data.collections if c.name.startswith(GEN_PREFIX)]:
        for ob in list(col.all_objects):
            data = ob.data
            removed.append(ob.name)
            bpy.data.objects.remove(ob, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)
        for child in list(col.children):
            col.children.unlink(child)
        bpy.data.collections.remove(col)
    auth = sorted(ob.name for ob in bpy.data.objects
                  if any(c.name.startswith(AUTH_PREFIX) for c in ob.users_collection))
    return removed, auth


def _collection(bpy, name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    if col.name not in {c.name for c in bpy.context.scene.collection.children}:
        bpy.context.scene.collection.children.link(col)
    return col


def _add_group(bpy, col, name, bverts, bfaces, buvs, has_uv):
    me = bpy.data.meshes.new(name)
    me.from_pydata(bverts, [], bfaces)
    me.validate()
    me.update()
    if has_uv:
        uvl = me.uv_layers.new(name="UVMap")
        for loop in me.loops:
            uvl.data[loop.index].uv = buvs[loop.vertex_index]
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def _add_refs(bpy, col, proj: Path, closed: bool) -> int:
    cl = proj / "data" / "centerline.local.json"
    if not cl.is_file():
        return 0
    pts = json.loads(cl.read_text(encoding="utf-8")).get("points_xyz_m") or []
    if len(pts) < 2:
        return 0
    cu = bpy.data.curves.new("REF_centreline", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts):
        x, y, z = to_blender(v)
        p.co = (x, y, z, 1.0)
    sp.use_cyclic_u = closed
    col.objects.link(bpy.data.objects.new("REF_centreline", cu))
    n = 1
    for st, v in _station_points(pts, REF_STATION_M):
        e = bpy.data.objects.new("REF_start" if st == 0.0 else f"REF_station_{int(st):05d}", None)
        e.empty_display_type = "ARROWS" if st == 0.0 else "PLAIN_AXES"
        e.empty_display_size = 6.0 if st == 0.0 else 3.0
        e.location = to_blender(v)
        col.objects.link(e)
        n += 1
    return n


def build(proj: Path) -> dict:
    import bpy  # provided by Blender, or the bpy module

    p = plan(proj)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    blend = proj / "loop.blend"
    if blend.is_file():
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        existed = True
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        existed = False
    removed, auth = _purge_gen(bpy)
    verts, uvs, groups = parse_obj(proj / "data" / "track.obj")
    cols = {name: _collection(bpy, name) for name in COLLECTIONS}
    built = []
    for name, faces in groups:
        if not faces:
            continue
        bverts, bfaces, buvs, has_uv = group_to_mesh(verts, uvs, faces)
        ob = _add_group(bpy, cols[collection_for(name)], name, bverts, bfaces, buvs, has_uv)
        built.append({"name": ob.name, "collection": collection_for(name), "verts": len(ob.data.vertices),
                      "faces": len(ob.data.polygons), "uv": has_uv})
    n_refs = _add_refs(bpy, cols["GEN_refs"], proj, bool(cfg.get("loop", True)))
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report = {"written": "loop.blend", "existed": existed, "blender": bpy.app.version_string,
              "source_obj": p["source_obj"], "obj_md5": p["obj_md5"], "frame": p["frame"],
              "groups": built, "refs": n_refs, "gen_removed": removed, "auth_untouched": auth,
              "collections": list(COLLECTIONS)}
    (proj / "data" / REPORT).write_text(json.dumps(report, indent=1), encoding="utf-8")
    by_col = {}
    for b in built:
        by_col[b["collection"]] = by_col.get(b["collection"], 0) + 1
    print(f"[underlay] {'refreshed' if existed else 'created'} {blend}: {len(built)} GEN objects "
          f"({', '.join(f'{k} {v}' for k, v in sorted(by_col.items()))}) + {n_refs} refs; "
          f"{len(removed)} old GEN objects replaced; {len(auth)} AUTH_* objects untouched")
    print(f"[underlay] source data/track.obj md5 {p['obj_md5']} -> data/{REPORT}")
    return report


def main(argv=None) -> int:
    proj, plan_only = _project_dir(list(sys.argv if argv is None else argv))
    if plan_only:
        p = plan(proj)
        print(json.dumps(p, indent=1))
        return 0
    build(proj)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

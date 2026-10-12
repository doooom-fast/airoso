"""The underlay: build or refresh a track's data underlay inside ``<project>/loop.blend`` (fleet/REALISM.md §4;
V3-PLAN P2 step 3; the generalisation of San Diego's quarantined build_loop_blend.py).

    blender --background --python-exit-code 1 --python scripts/blender/underlay.py -- <project-dir>
            [--variant <drive1_variants id>] [--out <file.blend>]

THE COLLECTION CONTRACT (REALISM §4), enforced here:
  * The underlay writes ONLY into its own collections: GEN_road, GEN_verge, GEN_terrain, GEN_refs
    (scripts/geometry/underlay_draft.COLLECTIONS). GEN_buildings is a hook, not built (Drive 1 is road + ground).
  * It NEVER resets the scene: an existing loop.blend is opened and edited in place. Only when there is no
    loop.blend yet does it start from an empty file (there is nothing to reset).
  * It never touches anything AUTH_*: an object named AUTH_*, or linked into any AUTH_* collection, is never
    deleted, re-linked, re-parented, renamed, moved or edited, and neither is its data. A fingerprint of every such
    object (and every AUTH_* collection) is taken before the run and compared before saving: any difference
    refuses the save (exit 1).
  * Idempotent: a re-run replaces only its own GEN objects. An object it owns is updated IN PLACE (same object,
    same name, new mesh/curve data; the old datablock is removed once nothing uses it), so nothing parented to it
    moves and no ".001" duplicates appear. Its own objects that this run no longer emits are removed. A name the
    underlay needs that is held by something it does not own is a refusal, never a rename.
  * Promotion: an AUTH object carrying ``underlay_role`` = road / verge / terrain (Kevin or Claude took that layer
    over) supersedes the role: the underlay stops drafting it and removes its own stale copy.

Objects carry ``underlay_role`` and ``underlay_gen`` custom properties; meshes also ``underlay_digest``. Mesh
geometry arrives in Blender's frame (x = E, y = N, z = up), drivable faces wound face-up. The report goes to
``<project>/data/underlay.json`` (with --out, ``<out stem>.underlay.json`` beside that file); every printed line
starts with ``[underlay]`` (tools/ship_track.sh greps them).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.geometry import underlay_draft as ud  # noqa: E402

AUTH = "AUTH_"
COLOURS = {"road": (0.09, 0.09, 0.10, 1.0), "verge": (0.47, 0.42, 0.33, 1.0), "terrain": (0.42, 0.38, 0.29, 1.0)}


def log(msg: str) -> None:
    print(f"[underlay] {msg}", flush=True)


def _args(argv):
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    out = {"proj": None, "variant": None, "out": None}
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("--variant", "--out"):
            if i + 1 >= len(rest):
                raise ud.UnderlayError(f"{a} needs a value")
            out[a[2:]] = rest[i + 1]
            i += 2
        elif a.startswith("--"):
            raise ud.UnderlayError(f"unknown flag {a}")
        elif out["proj"] is None:
            out["proj"] = a
            i += 1
        else:
            raise ud.UnderlayError(f"one project per run (got {out['proj']} and {a})")
    if not out["proj"]:
        raise ud.UnderlayError("usage: blender --background --python-exit-code 1 --python scripts/blender/underlay.py "
                               "-- <project-dir> [--variant <id>] [--out <file.blend>]")
    return out


# --- ownership --------------------------------------------------------------------------------------------------

def is_protected(ob) -> bool:
    return ob.name.startswith(AUTH) or any(c.name.startswith(AUTH) for c in ob.users_collection)


def owned_names() -> set:
    """names of every object the underlay owns: inside one of its collections (at any depth), not protected"""
    names = set()
    for cname in ud.COLLECTIONS.values():
        coll = bpy.data.collections.get(cname)
        if coll is None:
            continue
        for ob in coll.all_objects:
            if not is_protected(ob):
                names.add(ob.name)
    return names


def foreign_descendants(ob, owned: set) -> list:
    return [c.name for c in ob.children_recursive if c.name not in owned]


# --- the AUTH fingerprint -------------------------------------------------------------------------------------------

def _f(vals) -> bytes:
    return repr([round(float(v), 9) for v in vals]).encode()


def _ob_fingerprint(ob) -> str:
    h = hashlib.sha256()
    h.update(f"{ob.name}|{ob.type}|{ob.parent.name if ob.parent else ''}|{ob.parent_type}|".encode())
    h.update(_f([v for row in ob.matrix_world for v in row]))
    h.update(_f([v for row in ob.matrix_local for v in row]))
    h.update(_f([v for row in ob.matrix_parent_inverse for v in row]))
    h.update(repr(sorted(c.name for c in ob.users_collection)).encode())
    h.update(repr(sorted((k, repr(ob[k])) for k in ob.keys())).encode())
    h.update(repr((ob.hide_viewport, ob.hide_render, ob.hide_get() if ob.name in bpy.context.view_layer.objects else None,
                   ob.display_type, [(m.name, m.type) for m in ob.modifiers])).encode())
    d = ob.data
    if d is not None:
        h.update(f"data:{d.name}|{type(d).__name__}|".encode())
        mats = getattr(d, "materials", None)
        if mats is not None:
            h.update(repr([m.name if m else None for m in mats]).encode())
        if ob.type == "MESH":
            co = [0.0] * (len(d.vertices) * 3)
            d.vertices.foreach_get("co", co)
            h.update(_f(co))
            vi = [0] * len(d.loops)
            d.loops.foreach_get("vertex_index", vi)
            h.update(repr(vi).encode())
            ls = [0] * len(d.polygons)
            d.polygons.foreach_get("loop_start", ls)
            h.update(repr(ls).encode())
            for layer in d.uv_layers:
                uv = [0.0] * (len(d.loops) * 2)
                layer.data.foreach_get("uv", uv)
                h.update(layer.name.encode() + _f(uv))
        elif ob.type == "CURVE":
            for sp in d.splines:
                pts = [0.0] * (len(sp.points) * 4)
                sp.points.foreach_get("co", pts)
                h.update(_f(pts))
    return h.hexdigest()


def auth_fingerprint() -> dict:
    fp = {}
    for ob in bpy.data.objects:
        if is_protected(ob):
            fp["object:" + ob.name] = _ob_fingerprint(ob)
    for c in bpy.data.collections:
        if c.name.startswith(AUTH):
            fp["collection:" + c.name] = hashlib.sha256(repr((
                sorted(o.name for o in c.objects), sorted(ch.name for ch in c.children),
                c.hide_render, c.hide_viewport)).encode()).hexdigest()
    return fp


# --- writing ------------------------------------------------------------------------------------------------------

def collection(name: str):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    return coll


def material(role: str):
    name = f"GEN_{role}_mat"
    mat = bpy.data.materials.get(name)
    if mat is None:                     # never edits an existing one: an AUTH object may share it
        mat = bpy.data.materials.new(name)
        mat.use_nodes = False
        mat.diffuse_color = COLOURS[role]
    return mat


def new_mesh(name: str, mesh: dict):
    me = bpy.data.meshes.new(name + "__new")
    me.from_pydata(mesh["vertices"], [], mesh["faces"])
    me.validate()
    me.update()
    return me


def new_curve(name: str, polylines, cyclic):
    cu = bpy.data.curves.new(name + "__new", "CURVE")
    cu.dimensions = "3D"
    for pl, cyc in zip(polylines, cyclic):
        sp = cu.splines.new("POLY")
        sp.points.add(len(pl) - 1)
        flat = []
        for p in pl:
            flat += [p[0], p[1], p[2], 1.0]
        sp.points.foreach_set("co", flat)
        sp.use_cyclic_u = bool(cyc)
    return cu


SKIP = object()


class Writer:
    def __init__(self):
        self.owned = owned_names()
        self.emitted: list = []
        self.created = self.updated = 0

    def _claim(self, name: str, kind: str, role: str):
        """the existing object to update, None to create, or SKIP; refuses a foreign holder of the name (a reference
        held by authored work is skipped instead: it is a marker, not a layer)"""
        ob = bpy.data.objects.get(name)
        if ob is None:
            return None
        if ob.name not in self.owned:
            where = sorted(c.name for c in ob.users_collection) or ["(no collection)"]
            if is_protected(ob) and role == "refs":
                log(f"{name}: held by authored work (in {where}), left alone, not redrawn")
                return SKIP
            if is_protected(ob):
                raise ud.UnderlayError(
                    f"'{name}' is authored work (in {where}) and the underlay never drafts over AUTH_*. Give it the "
                    f"custom property underlay_role = the layer it replaces (road / verge / terrain) to supersede that "
                    f"GEN layer, or rename it. Nothing was saved.")
            raise ud.UnderlayError(
                f"'{name}' exists in loop.blend but the underlay does not own it (in {where}). Rename it AUTH_* "
                f"(or link it into an AUTH_* collection) to keep it as authored work, or move it into a GEN_* "
                f"collection to let the underlay replace it. Nothing was saved.")
        want = "EMPTY" if kind == "EMPTY" else kind
        if ob.type != want:
            fd = foreign_descendants(ob, self.owned)
            if fd:
                raise ud.UnderlayError(f"'{name}' changed type ({ob.type} -> {want}) but {fd} are parented to it")
            bpy.data.objects.remove(ob, do_unlink=True)
            return None
        return ob

    def _finish(self, ob, coll, role: str, props: dict, data_old=None):
        if coll.name not in [c.name for c in ob.users_collection]:
            coll.objects.link(ob)
        for k in list(ob.keys()):
            if k.startswith("underlay_"):
                del ob[k]
        ob["underlay_role"] = role
        ob["underlay_gen"] = 1
        for k, v in props.items():
            if v is not None:
                ob[k] = v
        if data_old is not None and data_old.users == 0:
            if isinstance(data_old, bpy.types.Mesh):
                bpy.data.meshes.remove(data_old)
            elif isinstance(data_old, bpy.types.Curve):
                bpy.data.curves.remove(data_old)
        self.emitted.append(ob.name)

    def _identity(self, ob):
        """GEN objects live at the identity transform, unless something it does not own is parented to it (then
        its transform is left exactly as found, so that child does not move)."""
        if not foreign_descendants(ob, self.owned):
            ob.matrix_world = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))

    def mesh(self, name, mesh, coll, role, props):
        me = new_mesh(name, mesh)
        me.materials.append(material(role))
        ob = self._claim(name, "MESH", role)
        old = None
        if ob is None:
            ob = bpy.data.objects.new(name, me)
            self.created += 1
        else:
            old = ob.data
            ob.data = me
            self.updated += 1
            self._identity(ob)
        self._finish(ob, coll, role, props, old)
        me.name = name                                    # free once the old datablock is gone
        return ob

    def curve(self, name, polylines, cyclic, coll, role, props):
        ob = self._claim(name, "CURVE", role)
        if ob is SKIP:
            return None
        cu = new_curve(name, polylines, cyclic)
        old = None
        if ob is None:
            ob = bpy.data.objects.new(name, cu)
            self.created += 1
        else:
            old = ob.data
            ob.data = cu
            self.updated += 1
            self._identity(ob)
        ob.hide_render = True
        self._finish(ob, coll, role, props, old)
        cu.name = name
        return ob

    def empty(self, name, location, coll, role, props, *, display="PLAIN_AXES", size=2.0):
        ob = self._claim(name, "EMPTY", role)
        if ob is SKIP:
            return None
        if ob is None:
            ob = bpy.data.objects.new(name, None)
            self.created += 1
        else:
            self.updated += 1
        if not foreign_descendants(ob, self.owned):
            ob.parent = None
            ob.location = location
            ob.rotation_euler = (0.0, 0.0, 0.0)
            ob.scale = (1.0, 1.0, 1.0)
        ob.empty_display_type = display
        ob.empty_display_size = size
        ob.hide_render = True
        self._finish(ob, coll, role, props)
        return ob

    def sweep(self, roles) -> list:
        """remove this underlay's own objects (in the given roles' collections) that this run did not emit"""
        keep = set(self.emitted)
        removed = []
        for role in roles:
            coll = bpy.data.collections.get(ud.COLLECTIONS[role])
            if coll is None:
                continue
            for ob in list(coll.all_objects):
                if ob.name in keep or ob.name not in self.owned:
                    continue
                fd = foreign_descendants(ob, self.owned)
                if fd:
                    log(f"kept stale {ob.name}: {fd} are parented to it (not the underlay's to move)")
                    continue
                data, nm = ob.data, ob.name
                bpy.data.objects.remove(ob, do_unlink=True)
                if data is not None and data.users == 0:
                    if isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
                    elif isinstance(data, bpy.types.Curve):
                        bpy.data.curves.remove(data)
                removed.append(nm)
        if removed:
            log(f"removed {len(removed)} stale GEN object(s): {removed[:8]}{' ...' if len(removed) > 8 else ''}")
        return removed


def superseded_roles() -> dict:
    out = {}
    for ob in bpy.data.objects:
        role = ob.get("underlay_role")
        if role in ("road", "verge", "terrain") and is_protected(ob):
            out.setdefault(role, []).append(ob.name)
    return out


# --- main ---------------------------------------------------------------------------------------------------------

def main() -> None:
    a = _args(sys.argv)
    proj = Path(a["proj"]).resolve()
    out = Path(a["out"]).resolve() if a["out"] else proj / "loop.blend"
    draft = ud.build(proj, a["variant"])          # every refusal about the data happens before the blend is opened
    rep = draft["report"]

    if out.is_file():
        bpy.ops.wm.open_mainfile(filepath=str(out))
        log(f"opened {out} (edited in place: no scene reset)")
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        log(f"no {out.name} yet: starting an empty file")
    before = auth_fingerprint()
    log(f"AUTH_* fingerprinted: {sum(1 for k in before if k.startswith('object:'))} objects, "
        f"{sum(1 for k in before if k.startswith('collection:'))} collections")

    sup = superseded_roles()
    w = Writer()
    roles_done = []
    for role in ("road", "verge", "terrain"):
        if role in sup:
            log(f"{ud.COLLECTIONS[role]}: superseded by authored {sup[role]} — not drafted; its stale GEN copy is removed")
            roles_done.append(role)
            continue
        if role not in draft["meshes"]:
            continue
        coll = collection(ud.COLLECTIONS[role])
        for name, mesh in draft["meshes"][role].items():
            props = {"underlay_digest": ud.mesh_digest(mesh)}
            if role == "terrain" and (rep.get("terrain") or {}).get("placeholder", True):
                props["underlay_placeholder"] = "P3a tiered terrain replaces this (engine heightfield; pinned under the pavement, raw survey elsewhere)"
            elif role == "terrain":
                props["underlay_terrain"] = ("cutfill: the real edge (scripts/geometry/terrain_cutfill.py); P3a's tiers "
                                             "replace the far ground")
            if role == "verge":
                props["underlay_verge_m"] = draft["verge"]["width_m"]
                props["underlay_verge_mode"] = draft["verge"]["mode"]
            ob = w.mesh(name, mesh, coll, role, props)
            log(f"{coll.name}/{ob.name}: {len(mesh['vertices'])} verts, {len(mesh['faces'])} faces")
        roles_done.append(role)

    r = draft["refs"]
    coll = collection(ud.COLLECTIONS["refs"])
    w.curve("REF_centreline", [r["centreline"]], [r["closed"]], coll, "refs", {"underlay_lap_m": r["lap_m"]})
    for s in r["stations"]:
        w.empty(s["name"], s["location"], coll, "refs", {"underlay_station_m": s["station_m"], "underlay_index": s["i"]})
    for c in r["corners"]:
        w.empty(c["name"], c["location"], coll, "refs",
                {"underlay_station_m": c["station_m"], "underlay_index": c["i"], "underlay_radius_m": c["radius_m"],
                 "underlay_label": c["label"], "underlay_source": c["source"]}, display="SPHERE", size=4.0)
    for b in r["boxes"]:
        w.curve(b["name"], [b["ring"]], [True], coll, "refs",
                {"underlay_corner": b["corner"], "underlay_label": b["label"], "underlay_i": b["i"],
                 "underlay_j": b["j"], "underlay_apex": b["apex"],
                 "underlay_note": "PROVISIONAL: race.corridor.boxes i..j +/- (half width + margin); P3b's mouths decide"})
    pl = r["pair_lines"] or [[r["centreline"][0], r["centreline"][0]]]
    w.curve("REF_stacked_legs", pl, [False] * len(pl), coll, "refs",
            {"underlay_pairs": len(r["pairs"]), "underlay_rule": json.dumps(r["pair_rule"])})
    roles_done.append("refs")
    w.sweep(roles_done)

    # the contract, checked on the data before anything is written to disk
    after = auth_fingerprint()
    if after != before:
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        raise ud.UnderlayError(f"AUTH_* changed during the run ({changed[:8]}); NOT saved")
    gen_names = [o.name for cname in ud.COLLECTIONS.values() if bpy.data.collections.get(cname)
                 for o in bpy.data.collections[cname].all_objects if not is_protected(o)]
    ud.check_names(gen_names)
    dups = [n for n in gen_names if "." in n and n.rsplit(".", 1)[1].isdigit()]
    if dups:
        raise ud.UnderlayError(f"duplicate-suffixed GEN objects {dups[:8]}; NOT saved")

    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    rep["blend"] = str(out)
    rep["objects"] = {"created": w.created, "updated": w.updated, "gen": len(gen_names),
                      "auth_untouched": sum(1 for k in before if k.startswith("object:"))}
    rep["superseded"] = sup
    if a["out"]:                      # a rehearsal into another file: its report sits beside it, not in the project
        rep_p = out.with_name(out.stem + ".underlay.json")
    else:
        (proj / "data").mkdir(exist_ok=True)
        rep_p = proj / "data" / "underlay.json"
    rep_p.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    log(f"road: {rep['road']['verts']} verts, widths {rep['road']['width_m']}; crossfall: {rep['road']['crossfall']}")
    log(f"verge: {rep['verge']['mode']}")
    if rep.get("terrain") and not rep["terrain"].get("placeholder", True):
        t = rep["terrain"]
        log(f"terrain CUTFILL (the real edge): {t['grid'][0]}x{t['grid'][1]} @ {t['cell_m']} m, {t['refined_quads']} quads "
            f"refined x{t['refine_factor']}, {t['grid_tris_removed_under_strip']} grid triangles cut back under the edge "
            f"strip ({t['edge_verts']} verts, {t['sparse_stations']} sections, {t['rows_clipped']} clipped at a stacked "
            f"midline or a hairpin centre); sections {t['section_counts']}; {t['verts']} verts in all")
    elif rep.get("terrain"):
        t = rep["terrain"]
        rf_ = t["refine"]
        log(f"terrain PLACEHOLDER: {t['grid'][0]}x{t['grid'][1]} @ {t['cell_m']} m, corridor {rf_['quads']} quads at "
            f"{rf_['sub_cell_m']} m ({rf_['pinned']} nodes pinned under the pavement, {rf_['edge_clamped']} held under its "
            f"edge), skirt {t['skirt_m']} m, "
            f"{t['verts']} verts (replaced by {t['replaced_by']})")
    rf = rep["refs"]
    log(f"refs: {rf['stations']} stations, corners {rf['corners']}, race boxes {rf['race_boxes']}, "
        f"{rf['stacked_pairs']} stacked-leg pairs (plan min {rf['stacked_plan_m_min']} m, |dy| {rf['stacked_dy_abs_m']})")
    log(f"objects: {w.created} created, {w.updated} updated in place; {rep['objects']['auth_untouched']} AUTH_* "
        f"objects untouched (fingerprint equal)")
    log(f"wrote {out}")


if __name__ == "__main__":             # Blender's --python runs the file as __main__; importing it runs nothing
    try:
        main()
    except SystemExit as e:           # a refusal: say it on an [underlay] line, then fail the Blender run
        if e.code not in (None, 0):   # (--python-exit-code 1 turns the raised error into exit 1)
            msg = e.code if isinstance(e.code, str) else f"[underlay] exit {e.code}"
            print(msg, flush=True)
            raise RuntimeError(msg) from None

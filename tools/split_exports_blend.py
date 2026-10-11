"""Split one authored/prepped blend into the kinds of export scene the race layouts need (ledgers 0047 + 0049,
L8 as amended: ONE shared road kn5 + ONE common race-furniture kn5 + ONE closure kn5 PER race layout + ONE
nodes-only spawn kn5 per layout). NEVER saves over the input.

    blender --background --python-exit-code 1 --python tools/split_exports_blend.py -- <blend>
        --project <project-dir> [--out-dir <dir>] [--layouts a,b,c] [--synth-dummies]

Writes, into --out-dir (default: the input blend's folder):
  loop_main.blend              everything EXCEPT the race furniture and every AC_* object   -> <slug>.kn5
  loop_race.blend              the COMMON race furniture ONLY: the curb strips (1WALL_race_edge_*) and the race
                               kerbs (1KERB_race_*) — every RACE object that is not a closure   -> <slug>_race.kn5
  loop_closure_<id>.blend      per race layout: ITS closure ONLY (1WALL_race_close_<token>_*, the token
                               barrier_bands.json corridors.<id>.token declares)              -> <slug>_closure_<id>.kn5
  loop_spawn_<id>.blend        AC_* empties from data/dummies_<id>.json for each layouts[] id (nothing else)
  split_manifest.json          what went where (objects, meshes, positions, materials, AC nodes per output)
                               + problems (exit 1 on any)

The manifest records a PROBLEM (exit 1) for: a closure whose name token no corridor declares; a retired
centre-chain object (1WALL_race_kbar_*); an empty closure blend; a closure object in loop_race.blend (or another
layout's closure in a closure blend); (race u closures) != every RACE object of the input; a material in a race
or closure scene no kept object uses, or a non-RACE material there; AC_* nodes in any furniture scene.

Why objects are REMOVED rather than deselected or moved between collections: the exporter that runs
(exporter.kn5 — the AppData blender-assetto-corsa-tools 1.0.7) walks blend_data.objects, ignores the
selection, and embeds every material with users > 0; a mesh datablock keeps its material 'used'
after the object is gone, hence meshes.remove + orphans_purge. The race filter is membership of the
RACE / RACE_CLOSE_* collections OR the name prefix — the prep (_split_large) re-links tiles to the scene root, so a
collection alone cannot be trusted after the prep; the prefix alone cannot be trusted before it. Which kn5 a race
object goes to is decided by its NAME alone (race_furniture.race_owner): the token is authoritative.

Empties: Blender (x, z, y) of the engine-frame dummy, rotation_euler.z from the dummies file's
`_yaw_deg[name]` (tools/layout_dummies.py) or, when absent, atan2(tx, -tz) (+pi for a reverse
layout) at the nearest centreline vertex — the measured facing correction (ledger 0047).
true_north_rotation_deg is 0.0 on SD and the loop prep never rotates the scene, so no yaw
composition is applied (build_spawn_kn5.py's rotation is the OBJ-path convention, not the loop's).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO / "tools"))
import race_furniture as rf  # noqa: E402

AC_PREFIX = "AC_"


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = {"blend": None, "project": None, "out_dir": None, "layouts": None, "synth": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--project":
            out["project"] = argv[i + 1]; i += 2
        elif a == "--out-dir":
            out["out_dir"] = argv[i + 1]; i += 2
        elif a == "--layouts":
            out["layouts"] = argv[i + 1].split(","); i += 2
        elif a == "--synth-dummies":
            out["synth"] = True; i += 1
        elif out["blend"] is None:
            out["blend"] = a; i += 1
        else:
            raise SystemExit(f"[split] unknown argument {a}")
    if out["blend"] is None or out["project"] is None:
        raise SystemExit(__doc__)
    return out


def closure_blend_name(layout_id):
    """loop_closure_<id>.blend — exported as <slug>_closure_<id>.kn5 (tools/ship_sd.sh)"""
    return f"loop_closure_{layout_id}.blend"


def _members(col):
    out = set(ob.name for ob in col.objects)
    for c in col.children:
        out |= _members(c)
    return out


def _classify():
    """(race, ac): every RACE object of the open scene (RACE / RACE_CLOSE_* members or a RACE-prefixed name) and
    every AC_* object"""
    race = set()
    for col in bpy.data.collections:
        if col.name == rf.COMMON_COLLECTION or col.name.startswith(rf.COMMON_COLLECTION + "_CLOSE_"):
            race |= _members(col)
    race |= {ob.name for ob in bpy.data.objects if rf.is_race_name(ob.name)}
    ac = {ob.name for ob in bpy.data.objects if ob.name.startswith(AC_PREFIX)}
    return race, ac


def _remove(names):
    for name in sorted(names):
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        me = ob.data if ob.type == "MESH" else None
        bpy.data.objects.remove(ob, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    while bpy.data.orphans_purge(do_recursive=True):
        pass


def _census():
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    used = {s.material.name for o in meshes for s in o.material_slots if s.material is not None}
    return {"objects": len(bpy.data.objects), "meshes": len(meshes),
            "positions": sum(len(o.data.vertices) for o in meshes),
            "max_positions": max([len(o.data.vertices) for o in meshes] or [0]),
            "materials": sorted(m.name for m in bpy.data.materials),
            "orphan_materials": sorted(m.name for m in bpy.data.materials if m.name not in used),
            "ac_nodes": sorted(o.name for o in bpy.data.objects if o.name.startswith(AC_PREFIX)),
            "race_objects": sorted(o.name for o in bpy.data.objects if rf.is_race_name(o.name)),
            "closure_objects": sorted(o.name for o in bpy.data.objects if rf.race_role(o.name) == "close"),
            "names": sorted(o.name for o in bpy.data.objects)}


def _save(path):
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=False)


def _furniture_problems(tag, c, problems):
    """a race / closure scene: RACE objects + RACE materials only, every material used, no AC_* node, < 60k positions"""
    bad = [m for m in c["materials"] if not rf.is_race_name(m)]
    if bad or c["ac_nodes"] or len(c["race_objects"]) != c["objects"]:
        problems.append(f"{tag}: non-race materials {bad} ac={c['ac_nodes']} objects={c['objects']} race={len(c['race_objects'])}")
    if c["orphan_materials"]:
        problems.append(f"{tag}: materials no kept object uses {c['orphan_materials'][:6]} (the exporter would embed them)")
    if c["max_positions"] >= 60000:
        problems.append(f"{tag}: an object has {c['max_positions']} positions")


def main():
    a = _args()
    blend = Path(a["blend"]).resolve()
    proj = Path(a["project"]).resolve()
    out_dir = Path(a["out_dir"]).resolve() if a["out_dir"] else blend.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    layouts = [lo for lo in cfg.get("layouts", []) if (a["layouts"] is None or lo["id"] in a["layouts"])]
    race_ids = [str(lo["id"]) for lo in layouts if lo.get("race_furniture")]
    bands = rf.load_bands(proj) or {}
    manifest = {"input": str(blend), "outputs": {}, "problems": []}
    problems = manifest["problems"]
    # the declared owner token of every race layout's closure (barrier_bands.json v2 corridors; the config's
    # layouts[].closure_token must agree)
    tokens = {}
    for lo in layouts:
        if not lo.get("race_furniture"):
            continue
        lid = str(lo["id"])
        tok = rf.closure_token(bands, lid)
        ct = str(lo.get("closure_token") or "").lower()
        if not tok:
            problems.append(f"layout {lid}: no corridors.{lid}.token declared in barrier_bands.json — its closure cannot be routed")
            continue
        if ct and ct != tok:
            problems.append(f"layout {lid}: closure_token {ct!r} in the config != {tok!r} declared")
        tokens[lid] = tok
    tok_to_lid = {t: lid for lid, t in tokens.items()}
    manifest["tokens"] = tokens
    outputs = {"main": out_dir / "loop_main.blend", "race": out_dir / "loop_race.blend"}
    for lid in tokens:
        outputs[f"closure_{lid}"] = out_dir / closure_blend_name(lid)
    for lo in layouts:
        outputs[f"spawn_{lo['id']}"] = out_dir / f"loop_spawn_{lo['id']}.blend"
    for p in outputs.values():
        if p.resolve() == blend:
            raise SystemExit(f"[split] output {p} is the input — refusing")

    # --- the input's RACE census: routes, retired / undeclared names ----------------------------
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    race, ac = _classify()
    manifest["input_census"] = _census()
    kbar = sorted(n for n in race if rf.race_role(n) == "kbar")
    if kbar:
        problems.append(f"input: {len(kbar)} retired centre-chain objects (1WALL_race_kbar_*, ledger 0049): {kbar[:4]}")
    closures_in = {n for n in race if rf.race_role(n) == "close"}
    undeclared = sorted(n for n in closures_in if rf.race_owner(n) not in tok_to_lid)
    if undeclared:
        problems.append(f"input: {len(undeclared)} closure objects whose token no race layout declares "
                        f"(declared {sorted(tok_to_lid)}): {undeclared[:4]}")
    common_in = race - closures_in
    if not race:
        problems.append("input: no race furniture (run author_race_furniture_blend first)")
    manifest["routes"] = {"common": len(common_in), **{lid: sum(1 for n in closures_in if rf.race_owner(n) == t)
                                                       for lid, t in tokens.items()}}

    # --- main: everything except race furniture + AC_* ----------------------------------------
    _remove(race | ac)
    c = _census()
    bad = [m for m in c["materials"] if rf.is_race_name(m)]
    if c["ac_nodes"] or c["race_objects"] or bad:
        problems.append(f"main: ac={c['ac_nodes']} race={c['race_objects']} race_mats={bad}")
    _save(outputs["main"])
    manifest["outputs"]["loop_main.blend"] = c
    print(f"[split] main: {c['meshes']} meshes / {c['positions']} positions / {len(c['materials'])} materials / "
          f"{len(c['ac_nodes'])} AC nodes / {len(c['race_objects'])} race objects -> {outputs['main'].name}")

    # --- race: the COMMON furniture only (curb strips + kerbs; no closure) -----------------------
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    race, ac = _classify()
    keep = {n for n in race if rf.race_role(n) != "close"}
    _remove({ob.name for ob in bpy.data.objects} - keep)
    c = _census()
    _furniture_problems("race", c, problems)
    if c["closure_objects"]:
        problems.append(f"race: {len(c['closure_objects'])} closure objects in loop_race.blend {c['closure_objects'][:4]}")
    if not any(rf.race_role(n) == "edge" for n in c["race_objects"]):
        problems.append("race: no curb strip (1WALL_race_edge_*) in loop_race.blend")
    _save(outputs["race"])
    manifest["outputs"]["loop_race.blend"] = c
    kept_all = set(c["race_objects"])
    print(f"[split] race (common): {c['meshes']} meshes / {c['positions']} positions (max {c['max_positions']}) / "
          f"{len(c['materials'])} materials / {len(c['ac_nodes'])} AC nodes -> {outputs['race'].name}")

    # --- closure per race layout: ITS closure only ------------------------------------------------
    for lid, tok in tokens.items():
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        race, ac = _classify()
        keep = {n for n in race if rf.race_role(n) == "close" and rf.race_owner(n) == tok}
        _remove({ob.name for ob in bpy.data.objects} - keep)
        c = _census()
        tag = f"closure_{lid}"
        _furniture_problems(tag, c, problems)
        if not c["meshes"]:
            problems.append(f"{tag}: EMPTY — no 1WALL_race_close_{tok}_* object in the input")
        alien = [n for n in c["race_objects"] if rf.race_owner(n) != tok]
        if alien:
            problems.append(f"{tag}: objects that are not {lid}'s closure {alien[:4]}")
        _save(outputs[tag])
        manifest["outputs"][closure_blend_name(lid)] = c
        kept_all |= set(c["race_objects"])
        print(f"[split] closure {lid} (token {tok}): {c['meshes']} meshes / {c['positions']} positions "
              f"(max {c['max_positions']}) / {len(c['materials'])} materials / {len(c['ac_nodes'])} AC nodes -> "
              f"{outputs[tag].name}")
    input_race = set(manifest["input_census"]["race_objects"])
    if kept_all != input_race:
        problems.append(f"race u closures != every RACE object of the input: missing {sorted(input_race - kept_all)[:4]}, "
                        f"extra {sorted(kept_all - input_race)[:4]}")

    # --- spawn per layout: AC_* empties only ------------------------------------------------------
    pts, widths = rf.load_centerline(proj)
    m = rf.unique_count(pts)
    for lo in layouts:
        lid = lo["id"]
        dp = proj / "data" / f"dummies_{lid}.json"
        if not dp.exists():
            if a["synth"] and lo.get("start"):
                dp.write_text(json.dumps(rf.synth_dummies(pts, widths, lo), indent=1), encoding="utf-8")
                print(f"[split] WARNING: synthesised {dp.name} for the dry run")
            else:
                problems.append(f"spawn_{lid}: no {dp.name}")
                print(f"[split] spawn {lid}: no {dp.name} — skipped")
                continue
        d = json.loads(dp.read_text(encoding="utf-8"))
        yaws = d.get("_yaw_deg", {})
        direction = lo.get("direction", d.get("_direction", "forward"))
        bpy.ops.wm.read_homefile(use_empty=True)
        n = 0
        for name, p in rf.dummies_positions(d).items():
            x, y, z = p
            e = bpy.data.objects.new(name, None)
            e.empty_display_type = "ARROWS"
            e.empty_display_size = 3.0
            e.location = (x, z, y)                           # engine (E, up, N) -> Blender (E, N, up)
            if any(name.startswith(f) for f in rf.FACING):
                if name in yaws:
                    yaw = math.radians(float(yaws[name]))
                else:
                    k = rf.nearest_vertex(pts, m, x, z)
                    tx, tz = rf.tangent(pts, k, m)
                    yaw = rf.yaw_blender(tx, tz, direction)
                e.rotation_euler = (0.0, 0.0, yaw)
            bpy.context.scene.collection.objects.link(e)
            n += 1
        c = _census()
        if c["meshes"] or c["objects"] != n or not c["ac_nodes"]:
            problems.append(f"spawn_{lid}: meshes={c['meshes']} objects={c['objects']} nodes={n}")
        _save(outputs[f"spawn_{lid}"])
        c["synthesised"] = bool(d.get("_synthesised"))
        manifest["outputs"][f"loop_spawn_{lid}.blend"] = c
        print(f"[split] spawn {lid} ({direction}): {n} AC_* empties, 0 meshes -> loop_spawn_{lid}.blend"
              f"{' (SYNTHESISED dummies)' if c['synthesised'] else ''}")

    (out_dir / "split_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    for p in problems:
        print(f"[split] PROBLEM: {p}")
    print(f"[split] manifest -> {out_dir / 'split_manifest.json'}; input untouched: {blend}")
    if problems:
        raise SystemExit(1)


main()

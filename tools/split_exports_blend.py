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
  loop_race_<lap>.blend        per LAP a race layout names (ledger 0054, scripts/geometry/race_lap.py): that lap's
                               common set ONLY (1WALL_race_edge_lap<lap>_*, 1KERB_race_lap<lap>_*)  -> <slug>_race_<lap>.kn5
                               (loop_race.blend then holds the MAINLINE's common set alone; it is written only when a
                               race layout drives the mainline — always, while no layout names a lap)
  loop_street.blend            (ledger 0055, when race.chicanes declares a street-only island; ledger 0063, when a track
                               has both race and street layouts) the STREET-ONLY objects: names carrying
                               race_chicane.STREET_TAG (the median island over a chicane's span, tools/
                               author_median_blend.py) and the road's centre paint (YLINE*, not the I-8's) — never in
                               loop_main.blend -> <slug>_street.kn5, loaded by every non-race layout only
  loop_spawn_<id>.blend        AC_* empties from data/dummies_<id>.json for each layouts[] id (nothing else)
  split_manifest.json          what went where (objects, meshes, positions, materials, AC nodes per output)
                               + problems (exit 1 on any)

A SINGLE-layout track (one layouts[] entry; the four of ledger 0060 — Exotics, Milford, High Plains, Sand Creek's
first pass) has no spawn scenes: the prep bakes AC_START / AC_PIT / AC_TIME / AC_HOTLAP into the road scene
(scripts/ac/build_kn5_loop.py, data/dummies.json) and verify_kn5's single-layout branch judges them in <slug>.kn5,
so loop_main.blend KEEPS every AC_* object and a road scene without one is the PROBLEM. The race scenes exist only
when a layout declares race_furniture: a track with none has no common set to find and no curb strip to demand
(the Exotics run of 2026-10-29 stopped here on all three counts). The multi-layout rule above is unchanged.

The manifest records a PROBLEM (exit 1) for: a closure whose name token no corridor declares; a retired
centre-chain object (1WALL_race_kbar_*); an empty closure blend; a closure object in loop_race.blend (or another
layout's closure in a closure blend); (race u closures) != every RACE object of the input; a material in a race
or closure scene no kept object uses, or a non-RACE material there; AC_* nodes in any furniture scene; a
multi-layout road scene that kept an AC_* node, a single-layout one that has none.

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


def _race_chicane():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_race_chicane_split", AIROSO / "scripts" / "geometry" / "race_chicane.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RC = _race_chicane()


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


def lap_blend_name(lap):
    """loop_race_<lap>.blend — a lap's common set, exported as <slug>_race_<lap>.kn5 (tools/ship_sd.sh)"""
    return f"loop_race_{lap}.blend"


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
        if (col.name == rf.COMMON_COLLECTION or col.name.startswith(rf.COMMON_COLLECTION + "_CLOSE_")
                or col.name.startswith(rf.COMMON_COLLECTION + "_LAP_")):
            race |= _members(col)
    race |= {ob.name for ob in bpy.data.objects if _is_race_object(ob.name)}
    ac = {ob.name for ob in bpy.data.objects if ob.name.startswith(AC_PREFIX)}
    return race, ac


def _is_race_object(name):
    """a RACE-prefixed name, or a per-layout sign plate (ledger 0054 P4: SIGN*_<token>_<k>, routed with its closure)"""
    return rf.is_race_name(name) or rf.is_layout_sign_name(name)


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
            "race_objects": sorted(o.name for o in bpy.data.objects if _is_race_object(o.name)),
            "closure_objects": sorted(o.name for o in bpy.data.objects if rf.race_role(o.name) == "close"),
            "sign_objects": sorted(o.name for o in bpy.data.objects if rf.race_role(o.name) == "sign"),
            "names": sorted(o.name for o in bpy.data.objects)}


def _save(path):
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=False)


def _furniture_problems(tag, c, problems):
    """a race / closure scene: RACE objects + RACE materials only (a closure scene: its layout's sign plates and their
    materials too, ledger 0054 P4), every material used, no AC_* node, < 60k positions"""
    bad = [m for m in c["materials"] if not (rf.is_race_name(m) or rf.is_layout_sign_name(m))]
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
    # the prep's and verify_kn5's rule, on the CONFIG's layouts (never the --layouts selection): more than one entry =
    # a spawn-free road scene + one spawn scene per layout; one entry = the AC_* ride in the road scene
    multi = len([lo for lo in (cfg.get("layouts") or []) if isinstance(lo, dict) and lo.get("id")]) > 1
    LAP = rf._race_lap()
    # ledger 0054: the lap groups — the mainline's declaration (barrier_bands.json) and one per lap a race layout
    # names (barrier_bands.<lap>.json); with no lap declared, the mainline's alone. No race layout = no common set.
    laps = LAP.lap_ids(cfg)
    has_main = bool(race_ids) and None in LAP.groups(cfg)
    bands_of = {None: rf.load_bands(proj) or {}}
    for lap in laps:
        bands_of[lap] = rf.load_bands(proj, lap) or {}
    lap_of = {str(lo["id"]): LAP.lap_of(lo) for lo in layouts}
    manifest = {"input": str(blend), "outputs": {}, "problems": []}
    problems = manifest["problems"]
    # the declared owner token of every race layout's closure (barrier_bands.json v2 corridors; the config's
    # layouts[].closure_token must agree)
    tokens = {}
    for lo in layouts:
        if not lo.get("race_furniture"):
            continue
        lid = str(lo["id"])
        tok = rf.closure_token(bands_of[lap_of[lid]], lid)
        ct = str(lo.get("closure_token") or "").lower()
        if not tok:
            problems.append(f"layout {lid}: no corridors.{lid}.token declared in {LAP.bands_file(lap_of[lid])} — its "
                            f"closure cannot be routed")
            continue
        if ct and ct != tok:
            problems.append(f"layout {lid}: closure_token {ct!r} in the config != {tok!r} declared")
        tokens[lid] = tok
    tok_to_lid = {t: lid for lid, t in tokens.items()}
    manifest["tokens"] = tokens
    outputs = {"main": out_dir / "loop_main.blend"}
    if has_main:
        outputs["race"] = out_dir / "loop_race.blend"
    for lap in laps:
        outputs[f"race_{lap}"] = out_dir / lap_blend_name(lap)
    for lid in tokens:
        outputs[f"closure_{lid}"] = out_dir / closure_blend_name(lid)
    if multi:
        for lo in layouts:
            outputs[f"spawn_{lo['id']}"] = out_dir / f"loop_spawn_{lo['id']}.blend"
    want_street = RC.has_street_kn5(cfg)
    if want_street:
        outputs["street"] = out_dir / "loop_street.blend"
    stale_street = out_dir / "loop_street.blend"
    if not want_street and stale_street.exists():
        stale_street.unlink()                       # a retired chicane's street set never rides along
    # a scene this run does not write never rides along either: a race set after the race layouts went, a spawn set
    # after a track became single-layout
    if not has_main and (out_dir / "loop_race.blend").exists():
        (out_dir / "loop_race.blend").unlink()
    if not multi:
        for stale in out_dir.glob("loop_spawn_*.blend"):
            stale.unlink()
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
    if race_ids and not race:
        problems.append(f"input: layouts {race_ids} declare race_furniture but the scene has none (run author_race_furniture_blend first)")
    if race and not race_ids:
        problems.append(f"input: {len(race)} RACE objects but no layout declares race_furniture: {sorted(race)[:4]}")
    stray_lap = sorted(n for n in common_in if rf.race_lap(n) is not None and rf.race_lap(n) not in laps)
    if stray_lap:
        problems.append(f"input: {len(stray_lap)} lap common objects whose lap no layout names (laps {laps}): {stray_lap[:4]}")
    manifest["routes"] = {"common": len([n for n in common_in if rf.race_lap(n) is None]),
                          **{f"common_{lap}": sum(1 for n in common_in if rf.race_lap(n) == lap) for lap in laps},
                          **{lid: sum(1 for n in closures_in if rf.race_owner(n) == t) for lid, t in tokens.items()}}

    street_in = {ob.name for ob in bpy.data.objects if RC.is_street_only_name(ob.name)}
    manifest["routes"]["street"] = len(street_in)
    if street_in & race:
        problems.append(f"input: objects both race and street-only {sorted(street_in & race)[:4]}")
    if want_street and not street_in:
        problems.append("input: a street-only set is declared (race.chicanes street_only_island, or race and street layouts "
                        "with a painted centre line) but no street-only object exists (tools/author_median_blend.py, YLINE*)")
    # a track with one kind of layout keeps its YLINE in the road kn5: only a tagged object with no span is a stray
    if not want_street:
        street_in = {n for n in street_in if not RC.is_centre_paint_name(n)}
        if street_in:
            problems.append(f"input: {len(street_in)} street-only objects but no street-only span is declared {sorted(street_in)[:4]}")

    # --- main: everything except race furniture + the street-only set; + AC_* when every layout has its own spawn
    #     scene (multi-layout), the AC_* kept when the prep baked them in (single layout) -----------------------
    _remove(race | (ac if multi else set()) | street_in)
    c = _census()
    bad = [m for m in c["materials"] if rf.is_race_name(m)]
    if (multi and c["ac_nodes"]) or c["race_objects"] or bad:
        problems.append(f"main: ac={c['ac_nodes']} race={c['race_objects']} race_mats={bad}")
    if not multi and not c["ac_nodes"]:
        problems.append("main: single layout but no AC_* node in the prepped scene — the prep bakes AC_START / AC_PIT / "
                        "AC_TIME / AC_HOTLAP there (scripts/ac/build_kn5_loop.py, data/dummies.json); the road kn5 would have no grid")
    if want_street and any(RC.is_street_only_name(nm) for nm in c["names"]):
        problems.append("main: a street-only object in loop_main.blend")
    _save(outputs["main"])
    manifest["outputs"]["loop_main.blend"] = c
    print(f"[split] main: {c['meshes']} meshes / {c['positions']} positions / {len(c['materials'])} materials / "
          f"{len(c['ac_nodes'])} AC nodes / {len(c['race_objects'])} race objects -> {outputs['main'].name}")

    # --- race: the COMMON furniture only (curb strips + kerbs; no closure) -----------------------
    # one common blend per group: the mainline's (loop_race.blend) and each lap's (loop_race_<lap>.blend) — which
    # one an object goes to is its NAME's lap field (race_furniture.race_lap; None = the mainline)
    kept_all = set()
    for lap in ([None] if has_main else []) + laps:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        race, ac = _classify()
        keep = {n for n in race if rf.race_role(n) not in ("close", "sign") and rf.race_lap(n) == lap}
        _remove({ob.name for ob in bpy.data.objects} - keep)
        c = _census()
        tag, key, bname = ("race", "race", "loop_race.blend") if lap is None else \
            (f"race_{lap}", f"race_{lap}", lap_blend_name(lap))
        _furniture_problems(tag, c, problems)
        if c["closure_objects"]:
            problems.append(f"{tag}: {len(c['closure_objects'])} closure objects in {bname} {c['closure_objects'][:4]}")
        if c["sign_objects"]:
            problems.append(f"{tag}: {len(c['sign_objects'])} per-layout sign plates in {bname} {c['sign_objects'][:4]} (they ride with their closure)")
        if not any(rf.race_role(n) == "edge" for n in c["race_objects"]):
            problems.append(f"{tag}: no curb strip (1WALL_race_edge_*) in {bname}")
        alien = [n for n in c["race_objects"] if rf.race_lap(n) != lap]
        if alien:
            problems.append(f"{tag}: objects of another group's common set {alien[:4]}")
        _save(outputs[key])
        manifest["outputs"][bname] = c
        kept_all |= set(c["race_objects"])
        print(f"[split] {tag} (common{'' if lap is None else ', lap ' + lap}): {c['meshes']} meshes / {c['positions']} "
              f"positions (max {c['max_positions']}) / {len(c['materials'])} materials / {len(c['ac_nodes'])} AC nodes -> "
              f"{outputs[key].name}")

    # --- closure per race layout: ITS closure only ------------------------------------------------
    for lid, tok in tokens.items():
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        race, ac = _classify()
        # ITS closure walls and ITS sign plates (ledger 0054 P4: SIGN*_<token>_<k>, a per_layout corner's plates)
        keep = {n for n in race if rf.race_role(n) in ("close", "sign") and rf.race_owner(n) == tok}
        _remove({ob.name for ob in bpy.data.objects} - keep)
        c = _census()
        tag = f"closure_{lid}"
        _furniture_problems(tag, c, problems)
        if not c["closure_objects"]:
            problems.append(f"{tag}: EMPTY — no 1WALL_race_close_{tok}_* object in the input")
        alien = [n for n in c["race_objects"] if rf.race_owner(n) != tok]
        if alien:
            problems.append(f"{tag}: objects that are not {lid}'s closure {alien[:4]}")
        _save(outputs[tag])
        manifest["outputs"][closure_blend_name(lid)] = c
        kept_all |= set(c["race_objects"])
        print(f"[split] closure {lid} (token {tok}): {c['meshes']} meshes / {c['positions']} positions "
              f"(max {c['max_positions']}) / {len(c['materials'])} materials / {len(c['ac_nodes'])} AC nodes"
              f"{(' / ' + str(len(c['sign_objects'])) + ' sign plates') if c['sign_objects'] else ''} -> "
              f"{outputs[tag].name}")
    # --- street: the street-only set (ledger 0055) ------------------------------------------------
    if want_street:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        keep = {ob.name for ob in bpy.data.objects if RC.is_street_only_name(ob.name)}
        _remove({ob.name for ob in bpy.data.objects} - keep)
        c = _census()
        if not c["meshes"]:
            problems.append("street: EMPTY — no street-only object in the input")
        alien = [nm for nm in c["names"] if not RC.is_street_only_name(nm)]
        if alien or c["ac_nodes"] or c["race_objects"]:
            problems.append(f"street: objects that are not street-only {alien[:4]} ac={c['ac_nodes']} race={c['race_objects']}")
        if c["orphan_materials"]:
            problems.append(f"street: materials no kept object uses {c['orphan_materials'][:6]}")
        if c["max_positions"] >= 60000:
            problems.append(f"street: an object has {c['max_positions']} positions")
        _save(outputs["street"])
        manifest["outputs"]["loop_street.blend"] = c
        print(f"[split] street (street-only island, ledger 0055): {c['meshes']} meshes / {c['positions']} positions / "
              f"{len(c['materials'])} materials / {len(c['ac_nodes'])} AC nodes -> {outputs['street'].name}")

    input_race = set(manifest["input_census"]["race_objects"])
    if kept_all != input_race:
        problems.append(f"race u closures != every RACE object of the input: missing {sorted(input_race - kept_all)[:4]}, "
                        f"extra {sorted(kept_all - input_race)[:4]}")

    # --- spawn per layout: AC_* empties only (multi-layout; a single layout's ride in loop_main.blend) -----------
    if not multi:
        print(f"[split] spawn: single layout — the {len(ac)} AC_* object(s) stay in loop_main.blend (the prep's "
              f"data/dummies.json); no spawn scene")
    pts_main, widths_main = rf.load_centerline(proj) if multi else (None, None)
    for lo in (layouts if multi else []):
        lid = lo["id"]
        pts, widths = (pts_main, widths_main) if not lap_of.get(str(lid)) else rf.load_centerline(proj, lap_of[str(lid)])
        m = rf.unique_count(pts)
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

"""Export a tiny nodes-only SPAWN kn5 per layout — the grid, pits and timing gates of THAT layout.

Multi-layout tracks keep the shared road kn5 free of AC_* spawn/timing nodes and load a small
per-layout kn5 beside it (models_<layout>.ini MODEL_n) that holds only that layout's dummies:
every reverse-capable reference measured (deepforest, Oregon Raceway Park, rt_california_highway,
Pacific Coast Hwy) ships this shape, and it is what fleet/LAWS.md L8 means by "layouts add kn5s,
never rebuild the road" (ledger 0047). AC reads AC_START/AC_PIT/AC_TIME/AC_HOTLAP from every
loaded kn5, so each layout gets its own start, grid, pit row and clock.

Dummies come from data/dummies_<layout>.json, one file per ``layouts[]`` id:

* NEW SHAPE (tools/layout_dummies.py, 2026-10-10): positions in the ENGINE frame (x=E, y=up, z=N —
  the frame dummies.json and the loop prep share) plus underscore metadata every consumer skips:
  ``_yaw_deg`` {name: Blender rotation_euler.z in degrees, already the reflected heading
  atan2(tx, −tz) (+180 for a reverse layout)}, ``_layout``, ``_direction``, ``_vertex``,
  ``_right_of_travel_m``. Placed exactly as the loop prep places its empties (build_kn5_loop step
  3): Blender (x, z, y), yaw about Blender Z = ``_yaw_deg`` + true_north_rotation_deg for the
  FACING names, AC_TIME_* unrotated. The AppData exporter's (x, z, −y) conversion then lands the
  node at kn5 (x, y, −z) with local +Z along the recorded travel — the facing measured at +1.00 on
  deepforest (ledger 0047; the old atan2(tx, tz) read −0.91 on the installed SD build).
* LEGACY SHAPE (build_network_mesh, per layouts[].spawn — no ``_yaw_deg``): kept byte-for-byte —
  Blender (x, −z, y) and the true-north yaw only, as before.

The persistence *.ini from the main export is purged first so the add-on's read_settings returns
{} and node_writer._write_base_node writes every empty as a plain node: a textureless nodes-only
kn5 (rt_california's 65 KB 100.kn5). Run AFTER export_kn5_addon's passes (which need their ini).
Stale build/<slug>__<x>.kn5 files for ids no longer in layouts[] are deleted so verify_kn5's
"exactly one spawn kn5 per layout id" check sees the declared set only.

    "$BLENDER" --background --python-exit-code 1 --python scripts/ac/build_spawn_kn5.py -- <track-dir>
"""

import json
import math
import sys
import tempfile
import zipfile
from pathlib import Path

import addon_utils
import bpy


def _track_dir(argv):
    if "--" not in argv:
        raise SystemExit("usage: blender --background --python build_spawn_kn5.py -- <track-dir>")
    rest = argv[argv.index("--") + 1:]
    if not rest:
        raise SystemExit("missing <track-dir> after '--'")
    return Path(rest[0]).resolve()


project = _track_dir(sys.argv)
# --obj-frame: the road kn5 came from build.sh's OBJ path (scripts/ac/build_kn5.py), not the loop prep
OBJ_FRAME = "--obj-frame" in sys.argv[sys.argv.index("--") + 1:]
repo = Path(__file__).resolve().parents[2]
cfg = json.loads((project / "track.config.json").read_text())
slug = cfg["slug"]
sx = -1.0 if cfg.get("mirror_x", False) else 1.0
data = project / "data"
build = project / "build"
build.mkdir(parents=True, exist_ok=True)
yaw_deg = float(cfg.get("true_north_rotation_deg", 0.0))
yr = math.radians(yaw_deg)
yc, ys = math.cos(yr), math.sin(yr)

# install + enable the AC add-on once (zipped on the fly from the vendored copy)
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_src = repo / "vendor" / "io_import_accsv"
if not (addon_src / "__init__.py").exists():
    raise SystemExit(f"vendored AC add-on missing at {addon_src}")
_zip = Path(tempfile.gettempdir()) / "_ac_addon_vendored.zip"
with zipfile.ZipFile(_zip, "w", zipfile.ZIP_DEFLATED) as z:
    for f in addon_src.rglob("*"):
        if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts:
            z.write(f, Path("io_import_accsv") / f.relative_to(addon_src))
bpy.ops.preferences.addon_install(filepath=str(_zip), overwrite=True)
for mod in addon_utils.modules():
    if any(k in mod.__name__.lower() for k in ("assetto", "corsa", "accsv")):
        try:
            bpy.ops.preferences.addon_enable(module=mod.__name__)
        except Exception as e:
            print("enable err", e)


def _find_export_op():
    if hasattr(bpy.ops, "exporter") and hasattr(bpy.ops.exporter, "kn5"):
        return "exporter.kn5", bpy.ops.exporter.kn5
    for modname in dir(bpy.ops):
        mod = getattr(bpy.ops, modname)
        for opname in dir(mod):
            if "kn5" in opname.lower() or "assetto" in opname.lower():
                return f"{modname}.{opname}", getattr(mod, opname)
    return None, None


op_name, op = _find_export_op()
print(f"[spawn_kn5] exporter: {op_name}")
# Clear any leftover persistence .ini from the main export — the add-on embeds every texture it lists,
# which would bloat a dummies-only spawn kn5 by ~25 MB of unused textures.
for old in build.glob("*.ini"):
    old.unlink()
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")
layouts = [lo for lo in cfg.get("layouts", []) if isinstance(lo, dict) and lo.get("id")]
ids = [lo["id"] for lo in layouts]
print(f"[spawn_kn5] yaw={yaw_deg} layouts={ids}")
# stale spawn kn5s of retired layout ids: verify_kn5 requires exactly one __<id>.kn5 per declared id
for old in build.glob(f"{slug}__*.kn5"):
    _lid = old.name[len(slug) + 2:-len(".kn5")]
    if _lid not in ids:
        old.unlink()
        print(f"[spawn_kn5] removed stale {old.name} (layout {_lid!r} no longer declared)")
failed = []
for lo in layouts:
    lid = lo["id"]
    dpath = data / f"dummies_{lid}.json"
    if not dpath.exists():
        print(f"[spawn_kn5] no dummies_{lid}.json — skip ({lid} keeps whatever spawns the road kn5 bakes)")
        continue
    # clear the scene WITHOUT read_factory_settings (which resets prefs -> disables the add-on -> the
    # kn5 operator disappears). Just remove all objects between layouts.
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    raw = json.loads(dpath.read_text())
    meta = {k: v for k, v in raw.items() if k.startswith("_")}
    dummies = {k: v for k, v in raw.items() if not k.startswith("_")}
    new_shape = "_yaw_deg" in raw
    yaws = meta.get("_yaw_deg") or {}
    if new_shape and str(meta.get("_layout", lid)) != lid:
        raise SystemExit(f"[spawn_kn5] dummies_{lid}.json says _layout={meta.get('_layout')!r}")
    # dummies-only scene: the exporter writes each AC_* empty as a base node (node_writer._write_object
    # -> _write_base_node). A mesh here would hit _split_object_by_materials and fail without materials;
    # empties do not, so no root mesh is needed.
    for name, (x, y, z) in dummies.items():
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 3.0
        facing = any(name.startswith(p) for p in FACING)
        if new_shape and OBJ_FRAME:
            # build.sh's OBJ path: the road kn5 is the MESH frame (engine x mirrored by mirror_x) imported as
            # Blender (x, -z, y) and yawed by true north about Blender Z (build_kn5 step 3b) — the node goes
            # exactly there. Its facing is this layout's engine travel (recovered from _yaw_deg =
            # atan2(ux, -uz)) carried through the same map into the kn5 frame (exporter (x, z, -y)), and the
            # Blender yaw psi gives kn5 local +Z = (sin psi, 0, cos psi). Adding true north to _yaw_deg, as
            # the loop branch below does, faced Sand Creek's grid backwards (mirror_x + 180 deg).
            xm = sx * x
            e.location = (xm * yc + z * ys, xm * ys - z * yc, y)
            if facing:
                if name not in yaws:
                    raise SystemExit(f"[spawn_kn5] dummies_{lid}.json: no _yaw_deg for facing node {name}")
                p0 = math.radians(float(yaws[name]))
                ux, uz = math.sin(p0), -math.cos(p0)
                kx, kz = sx * ux * yc + uz * ys, -sx * ux * ys + uz * yc
                e.rotation_euler = (0.0, 0.0, math.atan2(kx, kz))
        elif new_shape:
            # ENGINE (E, up, N) -> Blender (E, N, up) = (x, z, y), yawed by true north about Blender Z
            # (the loop prep's placement); the exporter's (x, z, -y) then gives kn5 (x, y, -z).
            e.location = (x * yc - z * ys, x * ys + z * yc, y)
            if facing:
                if name not in yaws:
                    raise SystemExit(f"[spawn_kn5] dummies_{lid}.json: no _yaw_deg for facing node {name}")
                e.rotation_euler = (0.0, 0.0, math.radians(float(yaws[name])) + yr)
        else:
            e.location = (x * yc + z * ys, x * ys - z * yc, y)   # legacy: same yaw as build_kn5's dummies
            if facing:
                e.rotation_euler = (0.0, 0.0, yr)
        bpy.context.scene.collection.objects.link(e)
    out = build / f"{slug}__{lid}.kn5"
    try:
        out.unlink()
    except OSError:
        pass
    for ob in bpy.data.objects:
        ob.select_set(True)
    if op is None:
        raise SystemExit("[spawn_kn5] no kn5 export operator found — add-on not enabled")
    try:
        op("EXEC_DEFAULT", filepath=str(out))
    except Exception as ex:
        import traceback
        print(f"[spawn_kn5] export EXCEPTION {lid}: {ex}")
        traceback.print_exc()
    exists = out.exists()
    size = out.stat().st_size if exists else 0
    print(f"[spawn_kn5] {lid}: kn5={exists} size={size} dummies={len(dummies)} "
          f"shape={('engine+yaw, obj frame' if OBJ_FRAME else 'engine+yaw') if new_shape else 'legacy'} direction={meta.get('_direction', '?')}")
    # nodes-only: no textures, no materials — a spawn kn5 over 1 MB has swallowed the main export's
    # material table (ini not purged) or a mesh, and verify_kn5 would reject it anyway
    if not exists or size == 0:
        failed.append(f"{lid}: no kn5 written")
    elif size > 1_000_000:
        failed.append(f"{lid}: {size} B is not a nodes-only kn5")
if failed:
    raise SystemExit("[spawn_kn5] FAILED: " + "; ".join(failed))

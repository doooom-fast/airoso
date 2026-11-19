"""A circuit's declared start, grid, pits and sectors on the PREPPED scene (ledger 0093; opt-in: track.config.json race_start).

engine-july's prep (Lake Murray v4's engine, frozen) lays a single-layout lap's AC_* empties by rule: the grid on the
straightest 260 m, AC_TIME_0 30 m ahead of it, eight pits every 10 m on the racing surface, one AC_START, every facing node
yawed from pts[0] -> pts[1] with atan2(tx, tz) (High Plains: the grid on the south straight, s 1080, its kn5 +Z reading
-0.97 against the travel). This step, inside the prep (tools/ship_track.sh prep_prep, only for a config that declares
race_start: every other track never runs it), removes that set and places the DECLARED one (scripts/geometry/
circuit_start.py: the measured line, the grid slots, the pits, the sectors), each facing node yawed from the line's own
tangent at its station, then rewrites data/dummies.json (the shape track_folder / write_ai_line / verify_kn5 read) and
writes data/circuit_dummies.json (what was placed, where, and what it replaced).

Heights: every START / PIT / HOTLAP at the BUILT road's top under the car's centre + DROP_IN_M, every timing pair at the
road's top under the line's centre + TIME_LIFT_M (the prepped 1ROAD* meshes, a ray down; race_start.road_prefixes
overrides the prefixes).

Self-check, exit 1 and the blend NOT saved: any problem circuit_start.plan reports (off the road's width, overlapping
cars, the grid out of order, AC_TIME_0 not 0-35 m ahead of the pole, sectors out of order); a car corner or centre with
no ROAD under it; a multi-layout track (its spawns ride in per-layout kn5s: tools/layout_dummies.py); a facing node whose
exported kn5 +Z would read under cos(HEADING_MIN_DEG) against its travel (scripts/ac/verify_kn5 (c)); a placed empty that
reads back off its planned position.

    blender --background --python-exit-code 1 --python tools/circuit_dummies_blend.py -- <prepped.blend> --project <dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.geometry import circuit_start as cs  # noqa: E402

ROAD_PREFIXES = ("1ROAD",)
HEADING_MIN_DEG = 30.0       # scripts/ac/verify_kn5.HEADING_MIN_DEG (read, never moved here)


def road_bvh(prefixes):
    verts, polys = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.upper().startswith(prefixes):
            continue
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ Vector(v.co) for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys) if polys else None


def top(tree, x, z):
    """the built road's top under engine (x, z) — Blender (X, Y) = engine (x, z) — or None"""
    hit = tree.ray_cast(Vector((x, z, 3000.0)), Vector((0.0, 0.0, -1.0)), 6000.0)
    return None if hit[0] is None else float(hit[0].z)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend = Path(argv[0])
    proj = Path(argv[argv.index("--project") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rs = cfg.get("race_start")
    if not rs:
        print("[circuit-dummies] no race_start declared: nothing to do")
        return
    if len(cfg.get("layouts") or []) > 1:
        raise SystemExit("[circuit-dummies] FATAL: a multi-layout track's spawns ride in per-layout kn5s "
                         "(tools/layout_dummies.py), not in the road scene")
    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pl = cs.plan(rs, local)
    problems = list(pl["problems"])
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    prefixes = tuple(str(p).upper() for p in (rs.get("road_prefixes") or ROAD_PREFIXES))
    tree = road_bvh(prefixes)
    if tree is None:
        raise SystemExit(f"[circuit-dummies] FATAL: no {list(prefixes)} mesh in the prepped scene")
    line = cs.Line(local["points_xyz_m"], local["widths_m"])
    placed = {}
    for name, v in sorted(pl["nodes"].items()):
        if name.startswith(cs.FACING):
            yc = top(tree, v["x"], v["z"])
            miss = [f"({x:.1f}, {z:.1f})" for x, z in cs.car_corners(v) if top(tree, x, z) is None]
            if yc is None or miss:
                where = ["its centre"] if yc is None else []
                where += ["corners " + ", ".join(miss)] if miss else []
                problems.append(f"{name} at s {v['station_m']:.1f}, lateral {v['lateral_m']:+.2f}: no ROAD under "
                                + " and ".join(where))
                continue
            y = yc + cs.DROP_IN_M
        else:
            cx, _cy, cz = line.point(v["station_m"])
            yc = top(tree, cx, cz)
            if yc is None:
                problems.append(f"{name}: no ROAD under the timing line's centre at s {v['station_m']:.1f}")
                continue
            y = yc + cs.TIME_LIFT_M
        placed[name] = (v["x"], y, v["z"])
    cos_min = math.cos(math.radians(HEADING_MIN_DEG))
    for name, v in pl["nodes"].items():
        if name.startswith(cs.FACING):
            d = cs.kn5_heading_dot(math.radians(v["yaw_deg"]), *v["travel"])
            if d < cos_min:
                problems.append(f"{name}: kn5 +Z . travel {d:+.2f} < {cos_min:.2f}")
    old = {o.name: o for o in bpy.data.objects if o.name.startswith("AC_")}
    old_start = None
    if "AC_START_0" in old:
        o = old["AC_START_0"]
        s_old, _la = line.project(float(o.location.x), float(o.location.y))
        old_start = {"station_m": round(s_old, 1), "yaw_deg": round(math.degrees(o.rotation_euler.z), 1),
                     "kn5_heading_dot": round(cs.kn5_heading_dot(o.rotation_euler.z, *line.tangent(s_old)), 3)}
    if problems:
        raise SystemExit("[circuit-dummies] FATAL (blend not saved): " + "; ".join(problems))
    for o in old.values():
        bpy.data.objects.remove(o, do_unlink=True)
    out, rows = {}, {}
    for name in sorted(placed):
        x, y, z = placed[name]
        v = pl["nodes"][name]
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 4.0
        e.location = (x, z, y)                                   # engine (E, up, N) -> Blender (E, N, up)
        if name.startswith(cs.FACING):
            e.rotation_euler = (0.0, 0.0, math.radians(v["yaw_deg"]))
        bpy.context.scene.collection.objects.link(e)
        out[name] = [round(x, 3), round(y, 3), round(z, 3)]
        rows[name] = {"station_m": round(v["station_m"], 2), "lateral_m": round(v["lateral_m"], 2)}
        if "yaw_deg" in v:
            rows[name]["yaw_deg"] = round(v["yaw_deg"], 2)
            rows[name]["kn5_heading_dot"] = round(cs.kn5_heading_dot(math.radians(v["yaw_deg"]), *v["travel"]), 4)
    for name, (x, y, z) in placed.items():                      # read back: every empty where it was planned
        o = bpy.data.objects[name]
        if math.dist((o.location.x, o.location.y, o.location.z), (x, z, y)) > 1e-3:
            raise SystemExit(f"[circuit-dummies] FATAL: {name} reads back off its planned position; blend not saved")
    (proj / "data" / "dummies.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    n_start = sum(1 for n in out if n.startswith("AC_START_"))
    n_pit = sum(1 for n in out if n.startswith("AC_PIT_"))
    rep = {"_doc": "tools/circuit_dummies_blend.py (ledger 0093): the declared race_start placed on the prepped scene, "
                   "in place of the prep's rule set; stations / laterals on data/centerline.local.json (+ = left of travel)",
           "line_station_m": round(pl["line_station_m"], 2), "sectors_m": [round(s, 2) for s in pl["sectors_m"]],
           "lap_m": round(pl["lap_m"], 2), "grid_slots": n_start, "pits": n_pit, "replaced": sorted(old),
           "replaced_start": old_start, "nodes": rows}
    (proj / "data" / "circuit_dummies.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    worst = min(r["kn5_heading_dot"] for r in rows.values() if "kn5_heading_dot" in r)
    print(f"[circuit-dummies] {len(old)} prep dummies replaced by {len(out)}: the line at s {pl['line_station_m']:.1f}, "
          f"{n_start} grid slots, {n_pit} pits, sectors at s {', '.join(f'{s:.0f}' for s in pl['sectors_m'])}; "
          f"kn5 heading min {worst:+.3f} (the prep's AC_START_0 read "
          f"{old_start['kn5_heading_dot'] if old_start else 'n/a'}); data/dummies.json, data/circuit_dummies.json; "
          f"saved {blend.name}")


main()

"""Move the spawn to the issue being verified — per-issue start positions.

Kevin (2026-08-20): "write starting positions for each issue you fix so that you can start
right where the issue is." Runs INSIDE Blender, AFTER the engine prep (build_kn5_loop, which
creates the AC_* dummy empties at the lap seam) and BEFORE the kn5 export:

    blender --background --python tools/set_start_blend.py -- <project-dir>

Reads <project>/start_positions.json (registry; `active` picks the position) and
data/centerline.local.json. Moves AC_START_0 + AC_HOTLAP_START_0 to the position and lines the
AC_PIT_n row up behind it in the same lane; keeps data/dummies.json in sync. The empties live in
the PREPPED blend (project/blender/<slug>.blend), Blender frame (E, N, up), yaw about +Z from
the driving direction — same conventions as build_kn5_loop.py:655-675.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

LIFT = 0.10
DROP_IN = 0.30
PIT_SPACING_M = 7.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    reg = json.loads((proj / "start_positions.json").read_text(encoding="utf-8"))
    key = reg["active"]
    pos = reg["positions"][key]
    k, off = int(pos["vertex"]), float(pos["offset_right_m"])
    if k == 0 and off == 0.0:
        print(f"[set-start] active '{key}' is the default seam placement — nothing to move")
        return

    slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"]
    blend = proj / "blender" / f"{slug}.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))

    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = local["points_xyz_m"]
    n = len(pts)

    def place(kk, off_r):
        kk = max(1, min(n - 2, kk))
        c = pts[kk]
        a, b = pts[kk - 1], pts[kk + 1]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz) or 1.0
        tx, tz = dx / L, dz / L          # driving direction in (E, N)
        rx, rz = tz, -tx                 # right-hand side of travel
        x = c[0] + rx * off_r
        z = c[2] + rz * off_r
        y = c[1] + LIFT + DROP_IN
        return (x, z, y), math.atan2(tx, tz), (tx, tz)

    dummies_path = proj / "data" / "dummies.json"
    dummies = json.loads(dummies_path.read_text(encoding="utf-8")) if dummies_path.exists() else {}

    moved = 0
    (bx, bz, by), yaw, (tx, tz) = place(k, off)
    for name in ("AC_START_0", "AC_HOTLAP_START_0"):
        e = bpy.data.objects.get(name)
        if e is None:
            print(f"[set-start] WARNING: {name} not found")
            continue
        e.location = (bx, bz, by)        # Blender (E, N, up)
        e.rotation_euler = (0.0, 0.0, yaw)
        dummies[name] = [round(bx, 3), round(by, 3), round(bz, 3)]
        moved += 1
    # pit row: behind the start, same lane, one car-length-ish apart
    p = 0
    while True:
        e = bpy.data.objects.get(f"AC_PIT_{p}")
        if e is None:
            break
        back = (p + 1) * PIT_SPACING_M
        kk = k - int(round(back / 3.0))
        (px, pz, py), pyaw, _ = place(kk, off)
        e.location = (px, pz, py)
        e.rotation_euler = (0.0, 0.0, pyaw)
        dummies[f"AC_PIT_{p}"] = [round(px, 3), round(py, 3), round(pz, 3)]
        p += 1
    dummies_path.write_text(json.dumps(dummies, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    print(f"[set-start] '{key}': start at vert {k} offset {off} m right, yaw {math.degrees(yaw):.0f} deg; "
          f"moved {moved} start dummies + {p} pits; saved {blend.name}")


main()

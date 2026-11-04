"""A point-to-point stage's start, splits and finish on the PREPPED scene (ledger 0078 round 8).

engine-july's prep (Lake Murray v4's engine) places the AC dummies for a LAP: the grid on the straightest window
anywhere on the line, the start / finish 30 m ahead of it, the splits wrapping round (its scripts/geometry/dummies.py
place_dummies, loop=True). A rally stage is driven once, end to end: the Rangely gravel stages on that engine put
their grid 59 % of the way along Dragon Tail, facing the wrong way for the declared run (the AI step refused it: "grid
faces REVERSE but the line is declared FORWARD"). airoso's own dummies module has the stage's branch (loop=False:
the grid 45 m into the road, AC_TIME_0 the finish 15 m short of its end, the splits between, never wrapping), the
placement airoso's engine draft gave the installed stages.

This step, inside the prep (only for a track whose config says `loop` false: Lake Murray and every circuit never run
it), removes the prep's AC_* empties from the prepped scene and places airoso's point-to-point set from the same
line the prep read (data/centerline.local.json), facing the run at the start, and rewrites data/dummies.json. A
multi-layout track (spawns in per-layout kn5s) is refused: no stage has one.

    blender --background --python-exit-code 1 --python tools/stage_dummies_blend.py -- <prepped.blend> --project <dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.geometry import dummies as dmod  # noqa: E402

FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")
N_PITS = 4                 # the installed stages' own set (airoso's build_mesh draft: AC_PIT_0..3, AC_START_0..3)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend = Path(argv[0])
    proj = Path(argv[argv.index("--project") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    if cfg.get("loop", True) is not False:
        print("[stage-dummies] the track is a loop: nothing to do")
        return
    if len(cfg.get("layouts") or []) > 1:
        raise SystemExit("[stage-dummies] FATAL: a multi-layout stage (spawns in per-layout kn5s) is not handled here")
    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    cl = [tuple(p) for p in local["points_xyz_m"]]
    widths = local["widths_m"]
    placed = dmod.place_dummies(cl, widths, n_sectors=3, n_pits=N_PITS, loop=False)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    old = [o for o in bpy.data.objects if o.name.startswith("AC_")]
    for o in old:
        bpy.data.objects.remove(o, do_unlink=True)
    # the run's direction at the start: the line's tangent at AC_START_0, as a yaw about Blender Z (the prep's own
    # convention: atan2(east, north) of the travel direction)
    sx, _sy, sz = placed["AC_START_0"]
    i = min(range(len(cl)), key=lambda k: (cl[k][0] - sx) ** 2 + (cl[k][2] - sz) ** 2)
    a, b = cl[max(i - 1, 0)], cl[min(i + 1, len(cl) - 1)]
    yaw = math.atan2(b[0] - a[0], b[2] - a[2])
    out = {}
    for name, (x, y, z) in sorted(placed.items()):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 4.0
        e.location = (x, z, y)                                 # local (E, up, N) -> Blender (E, N, up)
        if name.startswith(FACING):
            e.rotation_euler = (0.0, 0.0, yaw)
        bpy.context.scene.collection.objects.link(e)
        out[name] = [round(x, 3), round(y, 3), round(z, 3)]
    (proj / "data" / "dummies.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    st = [0.0]
    for p, q in zip(cl, cl[1:]):
        st.append(st[-1] + math.hypot(q[0] - p[0], q[2] - p[2]))
    print(f"[stage-dummies] point-to-point: {len(old)} lap dummies replaced by {len(out)} (the grid at "
          f"{st[i]:.0f} m of {st[-1]:.0f} m, the finish {st[-1] - 15:.0f} m); data/dummies.json; saved {blend.name}")


main()

"""Lake Murray v4's assembler (scripts-v021/blender/build_loop_blend.py, UNCHANGED) with the SD freeway port's two
opt-in terrain pieces (ledger 0080 2b round 1; tools/fwlm_terrain.py):

  - its band_clamp replaced by fwlm_terrain.band_clamp_np (byte-identical, vectorised: the whole network box's
    1.44 M-vertex grid never finished in pure Python);
  - with track.config.json lm_intake.terrain_tiers {"fine_m": .., "step": ..}, ribbon.grass_terrain replaced by
    fwlm_terrain.tiered_terrain on the roads the assembler conformed the ground to (its own call's arguments).
    Absent = grass_terrain itself: the assembler's mesh, unchanged.

Everything else is the assembler's own main(), run from its own file (its source is executed as is, minus the last
line's bare ``main()`` call, which this wrapper makes after the two patches). ship.json draft step
``build_loop_blend_tiered`` (tools/ship_track.sh); Lake Murray's ship.json names ``build_loop_blend`` and never runs it.

  <blender> --background --python-expr "$V021_SHIM" --python tools/fwlm_tiered_assembler_blend.py -- <project>
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fwlm_terrain  # noqa: E402  (tools/, by path: inside Blender `scripts` is scripts-v021)

V021 = Path(sys.modules["scripts"].__path__[0])          # V021_SHIM registered it
ASM = V021 / "blender" / "build_loop_blend.py"
src = ASM.read_text(encoding="utf-8")
tail = src.rstrip()
if not tail.endswith("\nmain()"):
    raise SystemExit(f"[fwlm-tiers] {ASM} no longer ends in a bare main() call: the wrapper cannot run it unchanged")
proj = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
tiers = (cfg.get("lm_intake") or {}).get("terrain_tiers")

ns = {"__name__": "__fwlm_assembler__", "__file__": str(ASM)}
exec(compile(tail[: -len("main()")], str(ASM), "exec"), ns)
from scripts.geometry import ribbon  # noqa: E402  (scripts-v021's, the module the assembler uses)

_roads = []
_conform = ribbon.conform_terrain_to_road


def conform_capture(grid_xyz, centerline_m, widths_m=None, **kw):
    _roads[:] = [(list(centerline_m), list(widths_m))] + [(list(p), list(w)) for p, w in (kw.get("extra_roads") or [])]
    return _conform(grid_xyz, centerline_m, widths_m, **kw)


def band_clamp_fast(grid_xyz, road_pts, band):
    t = time.time()
    n = fwlm_terrain.band_clamp_np(grid_xyz, road_pts, band)
    print(f"[fwlm-tiers] band clamp (vectorised, byte-identical): {n} vertices clamped, {time.time() - t:.1f} s")


_grass = ribbon.grass_terrain


def grass_tiered(grid_xyz, **kw):
    if not tiers:
        return _grass(grid_xyz, **kw)
    if not _roads:
        raise SystemExit("[fwlm-tiers] grass_terrain called before the conform: no roads to tier the ground on")
    t = time.time()
    mesh, rep = fwlm_terrain.tiered_terrain(grid_xyz, _roads, fine_m=float(tiers["fine_m"]), step=int(tiers["step"]), **kw)
    rep["seconds"] = round(time.time() - t, 1)
    (proj / "data" / "terrain.fwlm_tiers.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[fwlm-tiers] tiered terrain: {rep}")
    return mesh


ribbon.conform_terrain_to_road = conform_capture
ribbon.grass_terrain = grass_tiered
ns["band_clamp"] = band_clamp_fast
if not tiers:
    (proj / "data" / "terrain.fwlm_tiers.json").unlink(missing_ok=True)
ns["main"]()

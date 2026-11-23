"""Light the second head of every two-arm street lamp (ledger 0099; Kevin 2026-11-22: "Yes, light both heads").

The twin-arm LED lamp (scenery.streetlights.model "led_cobra", arms 2; ledger 0056, tools/author_lamps_blend.py) carries two
luminaires back to back, but the draft gives it ONE lens: LIGHTS_0, at the road-ward head only. scripts/ac/ext_config.py
clusters the exported LIGHTS* vertices into one CSP [LIGHT_N] per lens and lights the LIGHTS*_mat lenses at night, so the
back head has stood dark on every build since v0.18.1.

This author step (opt-in: track.config.json scenery.streetlights.light_both_heads true; absent = nothing runs, no blend is
saved) gives every two-arm lamp its back lens: each LIGHTS_0 lens, turned half a turn about its own pole's axis, into one
new mesh LIGHTS_back. The twin model is symmetric (assets/models/streetlight_led_post_twin.obj: every vertex above 11 m
has its mirror at -x; the lens, assets/models/streetlight_led_lens.obj, is symmetric across its own z = 0), so the turned
lens lies exactly where the back luminaire's lens is: 4.0376 m behind the pole, at the front lens's height. No vertex of
any other object moves; LIGHTS_0 is untouched.

Pole axes are the lamps as built (data/lights.local.json lamp_bases_xz, written by the draft's lamp author; one per lens in
provenance.lens_xyz, the same order). Each LIGHTS_0 face is paired with its lamp by its centroid (within MATCH_M of a
recorded lens), so a lens the record does not know refuses the step.

Self-checks (exit 1, loop.blend NOT saved):
  * every LIGHTS_0 face pairs with exactly one recorded lens, and every lens has its face;
  * every front lens stands ARM_TOL_M of spec lens_centre_m[0] from its pole (the model's 4.0376 m);
  * no two lenses (front and back, all lamps) closer than LENS_APART_M horizontally: ext_config's LAMP_LINK_M, the
    distance under which two lenses would merge into ONE light.

Writes data/lights.heads.json (the back lenses in the local frame, lens_xyz's order; tools/check_lights_ini.py then expects
two [LIGHT_N] per two-arm lamp, each at its own lens) and saves loop.blend. Idempotent: an earlier LIGHTS_back is removed
first. With the key absent or false a stale data/lights.heads.json is removed and the blend is not opened for writing.

    blender --background --python-exit-code 1 --python tools/author_lamp_heads_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
MODELS = AIROSO / "assets" / "models"
OBJECT = "LIGHTS_back"
FRONT = "LIGHTS_0"
MATCH_M = 0.01          # a LIGHTS_0 face's centroid within this of its recorded lens (lens_xyz is rounded to 1 mm)
ARM_TOL_M = 0.005       # the recorded lens vs the model's road-ward offset (measured on Lake Murray: 4.0366-4.0386 m)
LENS_APART_M = 2.0      # scripts/ac/ext_config.py LAMP_LINK_M: two lenses closer than this become one light
CLOSEST_CELL_M = 12.0   # the report names the closest two lenses when they are under this apart (a search radius, not a gate)
REPORT = "lights.heads.json"


def wanted(cfg: dict) -> bool:
    """the opt-in: scenery.streetlights.light_both_heads is true"""
    return ((cfg.get("scenery") or {}).get("streetlights") or {}).get("light_both_heads") is True


def refuse_unless_twin(cfg: dict, lights: dict) -> None:
    """both heads needs the twin-arm LED lamp the draft built (config and record agree)"""
    sl = (cfg.get("scenery") or {}).get("streetlights") or {}
    prov = lights.get("provenance") or {}
    if sl.get("model") != "led_cobra" or int(sl.get("arms", 2)) != 2:
        raise SystemExit("[heads] scenery.streetlights.light_both_heads needs model 'led_cobra' with arms 2 "
                         f"(the config says {sl.get('model')!r}, arms {sl.get('arms', 2)})")
    if prov.get("model") != "led_cobra" or int(prov.get("arms") or 0) != 2:
        raise SystemExit("[heads] data/lights.local.json provenance is not the twin-arm LED lamp "
                         f"(model {prov.get('model')!r}, arms {prov.get('arms')}): re-draft the lamps first")


def back_of(lens, base):
    """a front lens point (local x, y, z) turned half a turn about the vertical pole axis at base (x, z)"""
    return [2.0 * base[0] - lens[0], lens[1], 2.0 * base[1] - lens[2]]


def back_lenses(lens_xyz, bases_xz):
    """the back head's lens centre per lamp, local frame, lens_xyz's order"""
    if len(lens_xyz) != len(bases_xz):
        raise SystemExit(f"[heads] lights.local.json: {len(lens_xyz)} lenses but {len(bases_xz)} lamp bases")
    return [[round(v, 3) for v in back_of(l, b)] for l, b in zip(lens_xyz, bases_xz)]


def arm_offsets(lens_xyz, bases_xz):
    """each front lens's horizontal distance from its pole"""
    return [math.hypot(l[0] - b[0], l[2] - b[1]) for l, b in zip(lens_xyz, bases_xz)]


def closest_pair(points_xz, cell=CLOSEST_CELL_M):
    """(distance, i, j) of the two closest points (horizontal) when they are under ``cell`` apart, grid-bucketed; else
    (inf, -1, -1): every pair is at least ``cell`` apart, far past the link distance"""
    grid: dict[tuple[int, int], list[int]] = {}
    for i, (x, z) in enumerate(points_xz):
        grid.setdefault((int(math.floor(x / cell)), int(math.floor(z / cell))), []).append(i)
    best = (math.inf, -1, -1)
    for (cx, cz), ids in grid.items():
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in grid.get((cx + dx, cz + dz), ()):
                    for i in ids:
                        if i < j:
                            d = math.hypot(points_xz[i][0] - points_xz[j][0], points_xz[i][1] - points_xz[j][1])
                            if d < best[0] and d < cell:
                                best = (d, i, j)
    return best


def plan(cfg: dict, lights: dict, spec: dict) -> dict:
    """the pure half: the back lenses and every check that needs no Blender (raises SystemExit on a refusal)"""
    refuse_unless_twin(cfg, lights)
    lens = (lights.get("provenance") or {}).get("lens_xyz") or []
    bases = lights.get("lamp_bases_xz") or []
    if not lens:
        raise SystemExit("[heads] data/lights.local.json has no provenance.lens_xyz")
    arm = float(spec["lens_centre_m"][0])
    offs = arm_offsets(lens, bases)
    bad = [i for i, o in enumerate(offs) if abs(o - arm) > ARM_TOL_M]
    if bad:
        raise SystemExit(f"[heads] {len(bad)} lamps' lens is not {arm} m from its pole (+-{ARM_TOL_M}), e.g. lamp "
                         f"{bad[0]} at {offs[bad[0]]:.4f} m: the record and the model disagree")
    back = back_lenses(lens, bases)
    pts = [(p[0], p[2]) for p in lens] + [(p[0], p[2]) for p in back]
    d, i, j = closest_pair(pts)
    if d < LENS_APART_M:
        raise SystemExit(f"[heads] two lenses {d:.3f} m apart (< {LENS_APART_M} m, ext_config's link): points {i} and {j} "
                         f"(index >= {len(lens)} = a back lens) would merge into one light")
    return {"_doc": "ledger 0099 (Kevin 2026-11-22: \"Yes, light both heads\"): tools/author_lamp_heads_blend.py. The back "
                    "head's lens of every two-arm lamp, local frame (x east, y up, z north), in "
                    "lights.local.json provenance.lens_xyz's order; mesh " + OBJECT + ". tools/check_lights_ini.py "
                    "expects one [LIGHT_N] at every front and every back lens",
            "object": OBJECT, "lamps": len(lens), "lenses": 2 * len(lens),
            "arm_m": {"model": arm, "min": round(min(offs), 4), "max": round(max(offs), 4)},
            "closest_lenses_m": round(d, 3) if math.isfinite(d) else None, "link_m": LENS_APART_M,
            "back_lens_xyz": back}


def _remove_old(bpy):
    for ob in [o for o in bpy.data.objects if o.name == OBJECT or o.name.startswith(OBJECT + ".")]:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)


def author(bpy, proj: Path, rep: dict, lights: dict) -> int:
    """LIGHTS_back = LIGHTS_0's faces, each turned about its own lamp's pole; returns the faces written"""
    front = bpy.data.objects.get(FRONT)
    if front is None or front.type != "MESH":
        raise SystemExit(f"[heads] no {FRONT} mesh in loop.blend: the draft's lamp author writes it")
    lens = lights["provenance"]["lens_xyz"]
    bases = lights["lamp_bases_xz"]
    cells: dict[tuple[int, int], list[int]] = {}
    for k, l in enumerate(lens):                        # local (x, y, z) -> Blender (x, z, y)
        cells.setdefault((int(math.floor(l[0])), int(math.floor(l[2]))), []).append(k)
    _remove_old(bpy)
    me = front.data.copy()
    me.name = OBJECT
    mw = front.matrix_world
    owner, taken = [], {}
    for poly in me.polygons:
        c = [sum((mw @ me.vertices[v].co)[a] for v in poly.vertices) / len(poly.vertices) for a in range(3)]
        hits = [k for dx in (-1, 0, 1) for dz in (-1, 0, 1)
                for k in cells.get((int(math.floor(c[0])) + dx, int(math.floor(c[1])) + dz), ())
                if abs(lens[k][0] - c[0]) <= MATCH_M and abs(lens[k][2] - c[1]) <= MATCH_M
                and abs(lens[k][1] - c[2]) <= MATCH_M]
        if len(hits) != 1:
            raise SystemExit(f"[heads] {FRONT} face {poly.index} at ({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f}) pairs with "
                             f"{len(hits)} recorded lenses (want exactly 1)")
        k = hits[0]
        if k in taken:
            raise SystemExit(f"[heads] {FRONT} faces {taken[k]} and {poly.index} both stand at lamp {k}'s lens")
        taken[k] = poly.index
        owner.append((poly, k))
    if len(taken) != len(lens):
        missing = [k for k in range(len(lens)) if k not in taken]
        raise SystemExit(f"[heads] {len(missing)} recorded lenses have no {FRONT} face, e.g. lamp {missing[0]}")
    moved = set()
    inv = mw.inverted()
    from mathutils import Vector
    for poly, k in owner:
        bx, bz = bases[k]                               # the pole axis in Blender (x, y)
        for v in poly.vertices:
            if v in moved:
                raise SystemExit(f"[heads] {FRONT} vertex {v} is shared by two lenses")
            w = mw @ me.vertices[v].co
            me.vertices[v].co = inv @ Vector((2.0 * bx - w.x, 2.0 * bz - w.y, w.z))
            moved.add(v)
    me.update()
    ob = bpy.data.objects.new(OBJECT, me)
    ob.matrix_world = mw.copy()
    for col in front.users_collection:
        col.objects.link(ob)
    # read back: every turned face's centroid at its recorded back lens
    back = rep["back_lens_xyz"]
    worst = 0.0
    for poly, k in owner:
        p = ob.data.polygons[poly.index]
        c = [sum((ob.matrix_world @ ob.data.vertices[v].co)[a] for v in p.vertices) / len(p.vertices) for a in range(3)]
        worst = max(worst, abs(c[0] - back[k][0]), abs(c[1] - back[k][2]), abs(c[2] - back[k][1]))
    if worst > MATCH_M:
        raise SystemExit(f"[heads] a back lens stands {worst:.4f} m from where the record puts it (> {MATCH_M})")
    rep["read_back_worst_m"] = round(worst, 5)
    return len(owner)


def main(argv=None) -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if argv is None and "--" in sys.argv else (argv or [])
    if len(argv) != 1:
        raise SystemExit("usage: blender --background --python tools/author_lamp_heads_blend.py -- <project-dir>")
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    out = proj / "data" / REPORT
    if ((cfg.get("scenery") or {}).get("streetlights") or {}).get("both_heads_by") == "lamps":
        # ledger 0098's path (Sand Creek): the draft's lamps step lit both heads itself (heads_lit 2); this step would light
        # the back head a second time. The same key was written twice in two rounds (2026-11-22); round 2 of Sand Creek
        # moves it onto this step and both_heads_by goes
        raise SystemExit("[heads] scenery.streetlights.both_heads_by \"lamps\": tools/author_lamps_blend.py lit both heads "
                         "already; lamp_heads would light the back head twice (take lamp_heads out of ship.json, or drop "
                         "both_heads_by)")
    if not wanted(cfg):
        if out.exists():
            out.unlink()
        print("[heads] scenery.streetlights.light_both_heads is not set: nothing to do (one lens per lamp, as before)")
        return 0
    import bpy
    lights = json.loads((proj / "data" / "lights.local.json").read_text(encoding="utf-8"))
    spec = json.loads((MODELS / "streetlight_led.json").read_text(encoding="utf-8"))
    rep = plan(cfg, lights, spec)
    blend = proj / "loop.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    n = author(bpy, proj, rep, lights)
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"[heads] {n} back lenses -> {OBJECT} ({len(rep['back_lens_xyz'])} lamps, {rep['lenses']} lenses; arm "
          f"{rep['arm_m']['min']}-{rep['arm_m']['max']} m; closest two lenses {rep['closest_lenses_m']} m apart, link "
          f"{LENS_APART_M} m; read back worst {rep['read_back_worst_m']} m); wrote data/{REPORT}; saved {blend}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

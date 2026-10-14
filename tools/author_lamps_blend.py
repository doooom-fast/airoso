"""Rebuild every streetlight from a lamp MODEL chosen in track.config.json (0040 pass 2; ledger 0056).

The draft's build_streetlights sweeps a 9 m box post + arm + head box into ONE merged LIGHTS mesh
and records every lamp HEAD position in data/lights.local.json (local frame; head = arm tip,
1.8 m road-ward of the post, 0.1 m below the 9 m top). This script removes that mesh and stands a
real lamp at every post, from the model `scenery.streetlights.model` names (one key = a rollback):

  "led_cobra" (ledger 0056, Kevin 2026-10-14: "make lighter lamp model" / "more modern" / "Taller too")
      the modern San Diego arterial light from tools/make_streetlight_led.py (CC0): a 35 ft (10.67 m)
      tapered steel pole, 12 ft (3.66 m) mast arm(s), LED cobra head(s) with a flat lens at the 38'-9"
      (11.81 m) Caltrans ES-6A mounting height — ~1/11 of the 2026-10 lamp's render points (371 vs 4,045).
        pole + arm(s) + luminaire(s) -> LIGHTPOST_<k>  (LAMPS_PER_MESH lamps per mesh, contiguous along the loop)
        flat LED lens (road-ward head)  -> LIGHTS_0     (pbr LIGHTS: the CSP night emissive; ext_config clusters
                                                         ONE [LIGHT_N] per lens, 0.15 m under it)
      `scenery.streetlights.arms` 2 (default: back-to-back heads, the configuration every 2026-10 lamp has) or 1.
      Faces carry the model's smoothing groups: smooth faces, every edge between two groups (or beside a flat
      face) marked sharp — round pole, crisp luminaire. The model's UVs are kept as the UVMap.
  "street_lamp_2026_10" (the default when the key is absent — other tracks, and the rollback)
      Kevin's decimated Street_Lamp, assets/models/lamp_post.obj (2,060 v, 9 m, scaled to POST_H) + a 2 cm
      marker triangle at its road-ward head as the LIGHTS mesh — byte-for-byte the v0.18.0 path.

PLACEMENT (both models): the post base stands where it always has, ARM_M behind the recorded head away from the
road (road-ward = head -> nearest centreline point), so verify_race G, place_signs and the drive gates see the same
masts. The LED model's road datum is the head height minus HEAD_ABOVE_ROAD_M (ledger 0043 measured the 2026-10 light
6.94 m over the nearest road vertex; that light sat 2.004 m under the recorded head), so its lens stands
MOUNTING_HEIGHT over the road. The lens moves by a CONSTANT offset in each lamp's own frame from the 2026-10 lens —
written to data/lights.local.json "provenance" (with every lens position), so ext_config's [LIGHT_N] move by exactly
that offset and nothing else.

RELOCATIONS (v0.18.1 integration, verifier-found): `scenery.streetlights.relocate` moves a NAMED post, nothing else.
Each entry names the post by its base as the draft placed it (`from_base_xz`, local x/z, matched within MATCH_TOL_M —
exactly one post, or exit 1) and gives the new base (`to_base_xz`, at most MAX_MOVE_M away) and how the lamp is seated
(`seat`: "ground" = the road datum on the authored ground under the new base, the draft's own rule — head 8.8 m over the
ground under the post; "keep" = the head height the draft gave it). The recorded head moves with the base (same arm, the
road-ward direction re-read at the new spot), and data/lights.local.json `lampheads` is rewritten, so every reader
downstream (place_signs, verify_race G, ext_config's [LIGHT_N] through the lens) sees the moved post. Self-checks per
moved lamp, exit 1 (loop.blend NOT saved): the base is not over a road surface, the pole stands at least WALL_CLEAR_M
from every wall / guardrail, and its foot (POLE_BURY_M under the datum) is in the ground — never hanging in the air.

The local->Blender remap (x, z, y) is a reflection (LAWS L6), so face winding is reversed on import to keep the
models' outward normals.

Runs INSIDE Blender after strip_scenery_blend, before the kn5 prep:

    blender --background --python tools/author_lamps_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

AIROSO = Path(__file__).resolve().parents[1]
MODELS = AIROSO / "assets" / "models"
ARM_M = 1.8
POST_H = 11.5   # Kevin 2026-10-09: "lights need to be taller" — arterial cobra-head height (was 9.0); street_lamp_2026_10 only
CAP = 60000
LEGACY = "street_lamp_2026_10"
LED = "led_cobra"
HEAD_ABOVE_ROAD_M = 8.944     # recorded head - road (ledger 0043: light 6.94 m over the road = head - 2.004 m)
LAMPS_PER_MESH = 16           # LED LIGHTPOST batch: ~16 lamps (~0.9 km of loop) per mesh, so AC culls by stretch
LIGHT_DROP_M = 0.15           # scripts/ac/ext_config.py writes POSITION = lens centroid - 0.15 m
# relocations (v0.18.1): see the module doc and GATES-CHANGELOG 2026-10-14 v0.18.1
HEAD_OVER_GROUND_M = 8.8      # build_loop_blend.build_streetlights: head = ground under the post + 9.0 m post - 0.2 m
MATCH_TOL_M = 1.0             # [invented] a relocation names its post within this of the draft's base
MAX_MOVE_M = 15.0             # [invented] a relocation is a nudge to the right spot, not a new lamp
WALL_CLEAR_M = 0.5            # the integration brief: the pole >= 0.5 m clear of a barrier
WALL_PREFIXES = ("1WALL", "GUARDRAIL", "WALL")
ROAD_PREFIXES = ("ROAD", "1ROAD")
GROUND_PREFIXES = ("TERRAIN", "CURB", "SIDEWALK", "1KERB", "1GRASS", "GRASS", "ROAD", "1ROAD", "BRIDGESTRUCT")


def load_obj(path):
    verts, faces = [], []
    for ln in open(path, encoding="utf-8", errors="ignore"):
        if ln.startswith("v "):
            p = ln.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif ln.startswith("f "):
            ix = [int(q.split("/")[0]) - 1 for q in ln.split()[1:]]
            for k in range(1, len(ix) - 1):
                faces.append((ix[0], ix[k], ix[k + 1]))
    return verts, faces


def load_obj_full(path):
    """vertices + n-gon faces with their per-corner UVs and OBJ smoothing group (0 = `s off`, flat)"""
    verts, uvs, faces = [], [], []
    group = 0
    for ln in open(path, encoding="utf-8", errors="ignore"):
        p = ln.split()
        if not p:
            continue
        if p[0] == "v":
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif p[0] == "vt":
            uvs.append((float(p[1]), float(p[2])))
        elif p[0] == "s":
            group = 0 if p[1] in ("off", "0") else int(p[1])
        elif p[0] == "f":
            ix, uv = [], []
            for q in p[1:]:
                a = q.split("/")
                ix.append(int(a[0]) - 1)
                uv.append(uvs[int(a[1]) - 1] if len(a) > 1 and a[1] else (0.0, 0.0))
            faces.append((ix, uv, group))
    return verts, faces


def B(p):
    return (p[0], p[2], p[1])


def _mk(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _mk_shaded(name, verts, faces):
    """``faces`` = [(indices, uvs, group)]: smooth faces in a group, flat in group 0, every edge between two groups
    (or beside a flat face, or open) sharp; the per-corner UVs become the UVMap"""
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [f[0] for f in faces], shade_flat=False)
    groups = [f[2] for f in faces]
    for poly, g in zip(me.polygons, groups):
        poly.use_smooth = g != 0
    uvl = me.uv_layers.new(name="UVMap")
    for poly, (_, uv, _) in zip(me.polygons, faces):
        for k, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uv[k]
    owners = {}
    for poly, g in zip(me.polygons, groups):
        for ek in poly.edge_keys:
            owners.setdefault(ek, []).append(g)
    sharp = {ek for ek, gs in owners.items() if len(gs) != 2 or gs[0] != gs[1] or gs[0] == 0}
    for e in me.edges:
        e.use_edge_sharp = tuple(sorted(e.vertices)) in sharp
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def lamp_config(proj: Path) -> tuple[str, int]:
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    sl = ((cfg.get("scenery") or {}).get("streetlights") or {})
    model = str(sl.get("model", LEGACY))
    arms = int(sl.get("arms", 2))
    if model not in (LEGACY, LED):
        raise SystemExit(f"[lamps] scenery.streetlights.model must be {LED!r} or {LEGACY!r}, got {model!r}")
    if arms not in (1, 2):
        raise SystemExit(f"[lamps] scenery.streetlights.arms must be 1 or 2, got {arms}")
    return model, arms


def led_spec() -> dict:
    return json.loads((MODELS / "streetlight_led.json").read_text(encoding="utf-8"))


def legacy_lens_frame() -> tuple[float, float]:
    """the 2026-10 lamp's LIGHTS marker centroid in its lamp frame: (road-ward from the base, height over the head)"""
    post_v, _ = load_obj(MODELS / "lamp_post.obj")
    scale = POST_H / max(v[1] for v in post_v)
    fixture = (1.25, 7.7, 0.0)
    return fixture[0] * scale, 0.1 - POST_H + fixture[1] * scale - 0.3 + 0.02 / 3


def led_lens_offset(spec: dict) -> dict:
    """the LED lens centroid minus the 2026-10 lens centroid, per lamp in its own frame (road-ward, up)"""
    r_old, up_old = legacy_lens_frame()
    lx, ly, _ = spec["lens_centre_m"]
    return {"road_ward_m": round(lx - r_old, 4), "up_m": round(ly - HEAD_ABOVE_ROAD_M - up_old, 4)}


def _centreline_cells(cl):
    cells = {}
    for i, p in enumerate(cl):
        cells.setdefault((int(p[0] // 30), int(p[2] // 30)), []).append(i)

    def nearest_cl(x, z):
        best, bi = float("inf"), 0
        cx, cz = int(x // 30), int(z // 30)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in cells.get((cx + dx, cz + dz), ()):
                    d = (cl[i][0] - x) ** 2 + (cl[i][2] - z) ** 2
                    if d < best:
                        best, bi = d, i
        return cl[bi]
    return nearest_cl


def author_legacy(heads, nearest_cl):
    post_v, post_f = load_obj(MODELS / "lamp_post.obj")
    lens_v, lens_f = load_obj(MODELS / "lamp_lens.obj")
    top_y = max(v[1] for v in post_v)
    # lamp_post.obj is a symmetric double-arm luminaire (heads at x = ±1.58 m, y 7-8.5 m); the lens
    # goes at the ROAD-WARD head, not the centroid (which sits over the pole)
    fixture = (1.25, 7.7, 0.0)
    scale = POST_H / top_y

    postV, postF, lensV, lensF = [], [], [], []
    batches = {"LIGHTPOST": [], "LIGHTS": []}

    def flush(kind, V, F):
        if V:
            batches[kind].append((list(V), list(F)))
            V.clear()
            F.clear()

    n = 0
    for (hx, hy, hz) in heads:
        c = nearest_cl(hx, hz)
        dx, dz = c[0] - hx, c[2] - hz
        L = math.hypot(dx, dz) or 1e-9
        rx, rz = dx / L, dz / L                 # road-ward
        tx, tz = -rz, rx                        # along the road
        bx, bz = hx - rx * ARM_M, hz - rz * ARM_M
        by = hy + 0.1 - POST_H
        def place(v):
            mx, my, mz = v[0] * scale, v[1] * scale, v[2] * scale
            return B((bx + rx * mx + tx * mz, by + my, bz + rz * mx + tz * mz))
        if len(postV) + len(post_v) > CAP:
            flush("LIGHTPOST", postV, postF)
        off = len(postV)
        postV += [place(v) for v in post_v]
        postF += [(off + c_, off + b_, off + a_) for (a_, b_, c_) in post_f]     # reversed: reflection
        fx = bx + rx * fixture[0] * scale + tx * fixture[2] * scale
        fz = bz + rz * fixture[0] * scale + tz * fixture[2] * scale
        fy = by + fixture[1] * scale - 0.3
        # NO lens blob: the 0.5 m emissive lens read as "the glowing ball" (Kevin, 2026-10-08).
        # A 2 cm marker triangle at the fixture is invisible in game but still clusters one
        # [LIGHT_N] per lamp from the LIGHTS mesh (the engine's own fallback, build_env.py:1265).
        if len(lensV) + 3 > CAP:
            flush("LIGHTS", lensV, lensF)
        off = len(lensV)
        lensV += [B((fx, fy, fz)), B((fx + 0.02, fy, fz)), B((fx, fy + 0.02, fz))]
        lensF += [(off, off + 1, off + 2)]
        n += 1
    flush("LIGHTPOST", postV, postF)
    flush("LIGHTS", lensV, lensF)
    for kind, lst in batches.items():
        for k, (V, F) in enumerate(lst):
            _mk(f"{kind}_{k}", V, F)
    return n, batches, f"model {len(post_v)}v + lens {len(lens_v)}v each, fixture h {fixture[1] * scale:.2f} m", None


def author_led(heads, nearest_cl, arms):
    spec = led_spec()
    post_v, post_f = load_obj_full(MODELS / spec["files"]["post_twin" if arms == 2 else "post_single"])
    lens_v, lens_f = load_obj_full(MODELS / spec["files"]["lens"])
    lx, ly, lz = spec["lens_centre_m"]
    rev = lambda faces, off: [([off + i for i in reversed(ix)], list(reversed(uv)), g) for ix, uv, g in faces]

    posts, cur_v, cur_f, lensV, lensF, lenses = [], [], [], [], [], []
    n = 0
    for (hx, hy, hz) in heads:
        c = nearest_cl(hx, hz)
        dx, dz = c[0] - hx, c[2] - hz
        L = math.hypot(dx, dz) or 1e-9
        rx, rz = dx / L, dz / L                 # road-ward
        tx, tz = -rz, rx                        # along the road
        bx, bz = hx - rx * ARM_M, hz - rz * ARM_M
        yd = hy - HEAD_ABOVE_ROAD_M             # the road datum under this lamp
        def place(v):
            return B((bx + rx * v[0] + tx * v[2], yd + v[1], bz + rz * v[0] + tz * v[2]))
        if n and n % LAMPS_PER_MESH == 0:
            posts.append((cur_v, cur_f))
            cur_v, cur_f = [], []
        off = len(cur_v)
        cur_v += [place(v) for v in post_v]
        cur_f += rev(post_f, off)                # reversed: reflection
        off = len(lensV)
        lensV += [place(v) for v in lens_v]
        lensF += rev(lens_f, off)
        lenses.append([round(bx + rx * lx + tx * lz, 3), round(yd + ly, 3), round(bz + rz * lx + tz * lz, 3)])
        n += 1
    if cur_v:
        posts.append((cur_v, cur_f))
    for k, (V, F) in enumerate(posts):
        _mk_shaded(f"LIGHTPOST_{k}", V, F)
    _mk_shaded("LIGHTS_0", lensV, lensF)
    batches = {"LIGHTPOST": posts, "LIGHTS": [(lensV, lensF)]}
    prov = {
        "model": LED, "arms": arms, "generator": "tools/make_streetlight_led.py (assets/models/streetlight_led*.obj, CC0)",
        "mounting_height_m": spec["mounting_height_m"], "arm_length_m": spec["arm_length_m"],
        "pole_height_m": spec["pole_height_m"],
        "road_datum": f"head y - {HEAD_ABOVE_ROAD_M} m (ledger 0043: the 2026-10 light stood 6.94 m over the nearest road "
                      "vertex, 2.004 m under the recorded head)",
        "lens_offset_m": led_lens_offset(spec),
        "lens_offset_frame": "per lamp: road_ward = head -> nearest centreline point (horizontal), up = +y; from the "
                             "2026-10 lamp's LIGHTS marker centroid (street_lamp_2026_10) to this lens centroid. "
                             f"ext_config [LIGHT_N] POSITION = lens centroid - {LIGHT_DROP_M} m y, so each light moves by "
                             "the same offset",
        "lens_xyz": lenses,
    }
    note = (f"model {len(post_v)}v ({arms} arm{'s' if arms == 2 else ''}) + lens {len(lens_v)}v each, lens "
            f"{spec['mounting_height_m']:.2f} m over the road datum, {spec['lens_centre_m'][0]:.2f} m road-ward of the pole")
    return n, batches, note, prov


def _bvh(prefixes, exclude=()):
    """one BVH over every mesh whose name starts with a prefix (world space, Blender frame); None when there is none"""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    verts, polys = [], []
    for o in bpy.data.objects:
        u = o.name.upper()
        if o.type != "MESH" or not u.startswith(prefixes) or (exclude and u.startswith(exclude)):
            continue
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ Vector(v.co) for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys) if polys else None


def _top(bvh, x, z):
    """the highest surface of ``bvh`` under local (x, z): its height (local y), or None"""
    from mathutils import Vector
    if bvh is None:
        return None
    hit = bvh.ray_cast(Vector((x, z, 2000.0)), Vector((0.0, 0.0, -1.0)), 5000.0)
    return None if hit[0] is None else float(hit[0].z)


def relocate(heads, nearest_cl, cfg, model):
    """apply scenery.streetlights.relocate to ``heads`` in place (module doc, RELOCATIONS); returns the provenance rows.
    SystemExit on a bad entry or a failed self-check — before anything is saved"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import streetlight_relocate as SR
    try:
        rows = SR.plan(heads, nearest_cl, SR.entries(cfg), ARM_M, MATCH_TOL_M, MAX_MOVE_M)
    except ValueError as e:
        raise SystemExit(f"[lamps] relocate: {e}")
    if not rows:
        return []
    from mathutils import Vector
    ground = _bvh(GROUND_PREFIXES, exclude=("GRASS_FAR",))
    earth = _bvh(("TERRAIN", "1GRASS", "GRASS"), exclude=("GRASS_FAR",))
    road = _bvh(ROAD_PREFIXES)
    walls = _bvh(WALL_PREFIXES)
    if model == LED:
        spec = led_spec()
        bury, pole_h, mast_r = float(spec.get("pole_bury_m", 2.5)), float(spec["pole_height_m"]), float(spec["mast_radius_m"])
    else:
        bury, pole_h, mast_r = 0.0, POST_H, 0.585
    bad = []
    for r in rows:
        i = r["lamp"]
        bx, bz = r["new_base"]
        hx, hz = r["head_xz"]
        g = _top(ground, bx, bz)
        if g is None:
            bad.append(f"{r['name']}: no ground under the new base ({bx}, {bz})")
            continue
        hy = (g + HEAD_OVER_GROUND_M) if r["seat"] == "ground" else float(heads[i][1])
        yd = (hy - HEAD_ABOVE_ROAD_M) if model == LED else (hy + 0.1 - POST_H)
        foot = yd - bury
        rd = _top(road, bx, bz)
        if rd is not None and abs(rd - g) < 0.3:
            bad.append(f"{r['name']}: the new base ({bx}, {bz}) is on a road surface")
        e = _top(earth, bx, bz)
        if e is None or e < foot + 0.05:
            bad.append(f"{r['name']}: the pole foot ({foot:.2f}) is not in the earth (earth {e if e is None else round(e, 2)})"
                       " — it would hang in the air")
        clear = float("inf")
        if walls is not None:
            for k in range(0, 23):
                y = foot + (yd + pole_h - foot) * k / 22.0
                hit = walls.find_nearest(Vector((bx, bz, y)), 10.0)
                if hit[0] is not None:
                    clear = min(clear, float(hit[3]) - mast_r)
        if clear < WALL_CLEAR_M:
            bad.append(f"{r['name']}: the pole stands {clear:.2f} m from a wall / guardrail (< {WALL_CLEAR_M} m)")
        old = list(heads[i])
        heads[i] = [round(hx, 3), round(hy, 3), round(hz, 3)]
        r.update({"old_head": old, "new_head": heads[i], "ground_y": round(g, 3), "earth_y": None if e is None else round(e, 3),
                  "foot_y": round(foot, 3), "wall_clear_m": None if clear == float("inf") else round(clear, 3)})
        r.pop("head_xz", None)
        print(f"[lamps] relocate {r['name']}: lamp {i} base ({r['old_base'][0]}, {r['old_base'][1]}) -> ({bx}, {bz}) "
              f"{r['move_m']} m, seat {r['seat']}: head y {old[1]} -> {heads[i][1]}, ground {g:.2f}, foot {foot:.2f}, "
              f"wall clear {r['wall_clear_m']}")
    if bad:
        raise SystemExit("[lamps] relocate self-check FAILED (loop.blend not saved): " + "; ".join(bad))
    return rows


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    model, arms = lamp_config(proj)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    lights_p = data / "lights.local.json"
    lights = json.loads(lights_p.read_text(encoding="utf-8"))
    heads = lights["lampheads"]
    if "lampheads_draft" in lights:
        heads[:] = [list(h) for h in lights["lampheads_draft"]]   # idempotent: relocations start from the draft's posts
    cl = [tuple(p) for p in json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]]
    nearest_cl = _centreline_cells(cl)

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    old = bpy.data.objects.get("LIGHTS")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    for ob in [o for o in bpy.data.objects if o.name.upper().startswith(("LIGHTPOST_", "LIGHTS_"))]:
        bpy.data.objects.remove(ob, do_unlink=True)          # idempotent: a re-run never stacks two lamp sets

    draft = [list(h) for h in heads]
    moved = relocate(heads, nearest_cl, cfg, model)
    if moved:
        lights["lampheads_draft"] = draft
        lights["relocated"] = moved
    else:
        lights.pop("lampheads_draft", None)
        lights.pop("relocated", None)

    if model == LED:
        n, batches, note, prov = author_led(heads, nearest_cl, arms)
    else:
        n, batches, note, prov = author_legacy(heads, nearest_cl)
    if prov is not None:
        lights["provenance"] = prov
    else:
        lights.pop("provenance", None)
    lights_p.write_text(json.dumps(lights), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[lamps] {n} lamps from lights.local.json -> {len(batches['LIGHTPOST'])} LIGHTPOST + "
          f"{len(batches['LIGHTS'])} LIGHTS mesh(es) [{model}] ({note}); procedural LIGHTS removed; saved loop.blend")
    if prov is not None:
        print(f"[lamps] lens offset vs {LEGACY}: {prov['lens_offset_m']} (recorded in data/lights.local.json provenance)")


if __name__ == "__main__":
    main()

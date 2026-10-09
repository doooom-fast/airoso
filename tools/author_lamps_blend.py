"""Replace the procedural box streetlights with Kevin's own lamp model (0040 pass 2).

The draft's build_streetlights sweeps a 9 m box post + arm + head box into ONE merged LIGHTS mesh
and records every lamp HEAD position in data/lights.local.json (local frame; head = arm tip,
1.8 m road-ward of the post, 0.1 m below the 9 m top). This script rebuilds each lamp from
assets/models/lamp_post.obj (Kevin's decimated Street_Lamp, 2,060 v, 9 m, +x road-ward) and
assets/models/lamp_lens.obj (994 v) exactly the way the engine's own build_env does it:

  mast + luminaire  -> LIGHTPOST_<k>  (pbr prefix LIGHTPOST: solid dark metal — planar UVs harmless)
  lens at the fixture -> LIGHTS_<k>   (pbr prefix LIGHTS: warm solid lens, CSP night emissive;
                                       ext_config clusters [LIGHT_N] from LIGHTS verts, so one lens =
                                       one light at head height, no frame math)

Instances are batched under the 65,535-vert cap. The local->Blender remap (x, z, y) is a
reflection (LAWS L6), so face winding is reversed on import to keep the model's outward normals.

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
ARM_M = 1.8
POST_H = 11.5   # Kevin 2026-10-09: "lights need to be taller" — arterial cobra-head height (was 9.0)
CAP = 60000


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


def B(p):
    return (p[0], p[2], p[1])


def _mk(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    heads = json.loads((data / "lights.local.json").read_text(encoding="utf-8"))["lampheads"]
    cl = [tuple(p) for p in json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]]
    post_v, post_f = load_obj(AIROSO / "assets" / "models" / "lamp_post.obj")
    lens_v, lens_f = load_obj(AIROSO / "assets" / "models" / "lamp_lens.obj")
    top_y = max(v[1] for v in post_v)
    # lamp_post.obj is a symmetric double-arm luminaire (heads at x = ±1.58 m, y 7-8.5 m); the lens
    # goes at the ROAD-WARD head, not the centroid (which sits over the pole)
    fixture = (1.25, 7.7, 0.0)
    scale = POST_H / top_y

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    old = bpy.data.objects.get("LIGHTS")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

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
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[lamps] {n} lamps from lights.local.json -> {len(batches['LIGHTPOST'])} LIGHTPOST + "
          f"{len(batches['LIGHTS'])} LIGHTS mesh(es) (model {len(post_v)}v + lens {len(lens_v)}v each, "
          f"fixture h {fixture[1] * scale:.2f} m); procedural LIGHTS removed; saved loop.blend")


main()

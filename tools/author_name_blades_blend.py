"""Stand the street-name blades (MUTCD D3-1) that tools/name_blades.py planned, on Lake Murray's sign post (ledger 0079
round K; Kevin 2026-11-05: arrow signs and street-name signs, "Both").

track.config.json signs_name_blades.file (opt-in; absent = no-op) names the committed plan: per post the lap vertex, the
side, how far along the lap from the mouth (along_m) and outside the lane edge (setback_m), the two names and the side
street's direction. Here, on the BUILT loop.blend:

  base     P[v] + t along_m + n (side) (w/2 + setback_m) on this build's centreline (engine frame x = E, z = N; Blender
           (x, z) = (E, N)); a base on pavement (tools/signs_mesh.on_road), within place_signs.WALL_CLEAR_M of any
           1WALL face, within LAMP_CLEAR_M of a lamp mast or with less than PAVE_CLEAR_M to built pavement slides on
           AWAY from the mouth along the lap in SLIDE_STEP_M steps up to SLIDE_MAX_M, else the post is skipped and named.
  height   MUTCD 2009 2A.18 para 05: the bottom of the sign 7 ft (2.134 m) above the near edge of the traveled way (the
           lane edge's built height) — and never less above the ground under the post.
  blades   the lower blade names the side street, its face parallel to that street; the upper names the lap, parallel to
           the lap (2D.43 para 20); 12 in high (Table 2D-1, D3-1 conventional "Varies x 12"), the atlas row's length,
           BLADE_T_M thick [authored], BLADE_GAP_M apart [authored], centred on the post.
  post     place_signs' post: POST_W square, sunk POST_SINK, POST_OVER_TOP over the top blade.
  meshes   SIGNPOST_nameblade<k> (pbr SIGNPOST: the grey solid) and SIGNS_nameblade<k>a / b (pbr SIGNS, texture_overrides
           SIGNS = the committed atlas); the blades' UVs in their own active layer BLADE_UV, which the prep's planar pass
           (written into "UVMap") never touches (tools/author_kerbs_blend.py's way). No name matches race_furniture.SIGN_RE,
           so nothing is routed as a per-layout plate; the posts ship in the road kn5 every layout loads.
Writes data/name_blades.built.json. Idempotent (its own names removed first). Exit 1 (not saved) when no post stands.

    blender --background --python-exit-code 1 --python tools/author_name_blades_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import place_signs as ps  # noqa: E402
import signs_mesh as sm  # noqa: E402

FT = 0.3048
IN = 0.0254
MOUNT_BOTTOM_M = 7.0 * FT      # MUTCD 2009 2A.18 para 05 (business / commercial / residential): 7 ft
BLADE_T_M = 0.02               # [authored] blade thickness (a real blade is ~2 mm aluminium; 2 cm reads at distance)
BLADE_GAP_M = 0.03             # [authored] between the two blades
SLIDE_STEP_M, SLIDE_MAX_M = 0.25, 6.0   # [authored] the slide away from the mouth, as place_signs' step / its 6 m cap
LAMP_CLEAR_M = 3.0             # place_signs' lamp rule (a lamp inside 3.0 m of a sign)
PAVE_CLEAR_M = 1.0             # verify_signs' connector gate minimum: a post stands >= this from built pavement
POST_PREFIX, BLADE_PREFIX = "SIGNPOST_nameblade", "SIGNS_nameblade"
BLADE_UV = "BladeUV"


def box(name, centre, along, up_h, length, thick, uv_front):
    """a blade: `length` along the unit plan vector `along` (x, y Blender), `up_h` (z0, z1), `thick` across; the front and
    back faces carry the atlas cell uv_front = (u0, u1, v0, v1) (the back mirrored so it reads from behind), the four
    edges the cell's green margin"""
    ax, ay = along
    nx, ny = -ay, ax
    cx, cy = centre
    z0, z1 = up_h
    h, t = length / 2.0, thick / 2.0
    u0, u1, v0, v1 = uv_front
    um, vm = u1 + 0.004, (v0 + v1) / 2.0           # just right of the cell: green

    def P(s, q, z):
        return (cx + ax * s + nx * q, cy + ay * s + ny * q, z)
    faces = [  # (4 corners), (4 uvs)  — front at +n, back at -n
        ([P(-h, t, z0), P(h, t, z0), P(h, t, z1), P(-h, t, z1)], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]),
        ([P(h, -t, z0), P(-h, -t, z0), P(-h, -t, z1), P(h, -t, z1)], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]),
        ([P(-h, -t, z0), P(-h, t, z0), P(-h, t, z1), P(-h, -t, z1)], [(um, vm)] * 4),
        ([P(h, t, z0), P(h, -t, z0), P(h, -t, z1), P(h, t, z1)], [(um, vm)] * 4),
        ([P(-h, -t, z1), P(-h, t, z1), P(h, t, z1), P(h, -t, z1)], [(um, vm)] * 4),
        ([P(-h, t, z0), P(-h, -t, z0), P(h, -t, z0), P(h, t, z0)], [(um, vm)] * 4),
    ]
    verts, fl, uvs = [], [], []
    for corners, uv in faces:
        b = len(verts)
        verts += corners
        uvs += uv
        fl.append((b, b + 1, b + 2, b + 3))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], fl)
    me.validate()
    layer = me.uv_layers.new(name=BLADE_UV)
    for poly in me.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    _outward(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _outward(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def post(name, cx, cy, z0, z1, w):
    h = w / 2.0
    vs = [(cx + sx * h, cy + sy * h, z) for z in (z0, z1) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    fs = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.validate()
    _outward(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    proj = Path(sys.argv[sys.argv.index("--") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    nb_cfg = cfg.get("signs_name_blades") or {}
    if not nb_cfg.get("file"):
        print("[name-blades] no signs_name_blades.file: nothing to do")
        return
    plan = json.loads((proj / nb_cfg["file"]).read_text(encoding="utf-8"))
    rows = plan["atlas"]["rows"]
    cl = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    P = [tuple(p) for p in cl["points_xyz_m"]]
    W = [float(w) for w in cl["widths_m"]]
    m = len(P) - 1
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    for ob in [o for o in bpy.data.objects if o.name.startswith((POST_PREFIX, BLADE_PREFIX))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    road, ground, _rn, _gn = sm.load_bvhs(skip_prefixes=("SIGN",))
    walls = sm.load_wall_bvhs()["all"]
    lamps = sm.bvh_of([t for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("LIGHTPOST")
                       for t in sm.world_tris(o)])
    built, skipped = [], []
    for k, p in enumerate(plan["posts"]):
        v = int(p["vertex"])
        a, b = P[(v - 1) % m], P[(v + 1) % m]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        tx, tz = tx / L, tz / L
        nx, nz = -tz, tx                                    # left normal, engine frame
        sgn = 1.0 if p["side"] == "L" else -1.0
        lat = W[v] / 2.0 + float(p["setback_m"])
        edge = (P[v][0] + nx * sgn * W[v] / 2.0, P[v][2] + nz * sgn * W[v] / 2.0)
        away = 1.0 if p["along_m"] >= 0 else -1.0
        spot, why = None, None
        s = 0.0
        while s <= SLIDE_MAX_M + 1e-9:
            al = float(p["along_m"]) + away * s
            x, z = P[v][0] + tx * al + nx * sgn * lat, P[v][2] + tz * al + nz * sgn * lat
            g = sm.top_hit(ground, x, z)
            yy = g if g is not None else P[v][1]
            if sm.on_road(road, ground, x, z):
                why = "on pavement"
            elif sm.nearest_dist(walls, x, yy + 1.0, z) < ps.WALL_CLEAR_M:
                why = "beside a wall"
            elif sm.nearest_dist(lamps, x, yy + 1.0, z) < LAMP_CLEAR_M:
                why = "beside a lamp"
            elif sm.polar_clearance(road, ground, x, z)[0] < PAVE_CLEAR_M:
                why = f"within {PAVE_CLEAR_M} m of pavement"
            else:
                spot = (x, z, g, al, s)
                break
            s += SLIDE_STEP_M
        if spot is None:
            skipped.append({"id": p["id"], "why": f"no clear base within {SLIDE_MAX_M} m of the plan ({why})"})
            continue
        x, z, g, al, slid = spot
        r_edge = sm.top_hit(road, edge[0], edge[1])
        e_y = r_edge if r_edge is not None else P[v][1]
        g_y = g if g is not None else e_y
        bottom = max(e_y, g_y) + MOUNT_BOTTOM_M
        bh = plan["mutcd"]["blade_h_in"] * IN
        names = [("a", p["cross_name"], p["cross_dir_xz"]), ("b", p["lap_name"], (tx, tz))]
        z_lo = bottom
        for suf, nm, d in names:
            row = rows[nm]
            Lb = row["length_in"] * IN
            dl = math.hypot(d[0], d[1]) or 1.0
            box(f"{BLADE_PREFIX}{k}{suf}", (x, z), (d[0] / dl, d[1] / dl), (z_lo, z_lo + bh), Lb, BLADE_T_M,
                (row["u"][0], row["u"][1], row["v"][0], row["v"][1]))
            z_lo += bh + BLADE_GAP_M
        top = z_lo - BLADE_GAP_M + ps.POST_OVER_TOP
        post(f"{POST_PREFIX}{k}", x, z, g_y - ps.POST_SINK, top, ps.POST_W)
        built.append({"id": p["id"], "k": k, "vertex": v, "side": p["side"], "xz": [round(x, 2), round(z, 2)],
                      "along_m": round(al, 2), "slid_m": round(slid, 2), "ground_y": round(g_y, 3),
                      "edge_y": round(e_y, 3), "blade_bottom_y": round(bottom, 3), "names": [p["cross_name"], p["lap_name"]]})
    (proj / "data" / "name_blades.built.json").write_text(json.dumps(
        {"source": nb_cfg["file"], "posts": built, "skipped": skipped}, indent=1), encoding="utf-8")
    if not built:
        raise SystemExit("[name-blades] FATAL: no post stands (data/name_blades.built.json)")
    print(f"[name-blades] {len(built)} posts, {2 * len(built)} blades stood ({sum(1 for b in built if b['slid_m'] > 0)} "
          f"slid, max {max(b['slid_m'] for b in built)} m); {len(skipped)} skipped; saved loop.blend")
    for s_ in skipped:
        print(f"[name-blades]   skipped {s_['id']}: {s_['why']}")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()

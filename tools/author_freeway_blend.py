"""Drape the I-8's own pavement, lane lines and median barrier on the FINAL ground (ledger 0046, v0.18.0 integration fix
round; the plan and the WHY are in tools/freeway_i8.py, which writes data/freeway_i8.json).

Runs INSIDE Blender on the PREPPED scene (<project>/blender/<slug>.blend, after build_kn5_loop and before
split_exports_blend), because the prep still reshapes the ground (the corridor pin, the kept-cell refinement): draped
any earlier, the pavement would float or sink where it moved. It adds, all VISUAL ONLY (no digit prefix: no physics,
no gate scans them, the drive_test obstacle band is 0.25-1.8 m over a LANE of the loop, which nothing here is near):
  HIGHWAY_I8_NEAR_<k> / HIGHWAY_I8_FAR_<k>  the carriageways (pbr row HIGHWAY: cracked asphalt), lift_m over the ground,
        NEAR inside the 1ROAD extent (a GrassFX occluder: scripts/ac/ext_config.py), FAR beyond it (plain scenery);
  MARKINGS_I8_<k> / YLINE_I8_<k>            dashed lane lines and white outer / yellow median edge lines, NEAR only
        (a line 1-2 km out is under a pixel; MARKINGS is a GrassFX occluder prefix and must stay near-field);
  BARRIER_I8_<k>                            the concrete median barrier (pbr row BARRIER), a Jersey profile on the ground.
Materials are bound exactly as the prep binds them (engine-july's pbr.setup_material by name prefix + the project's
overrides); UVs are the prep's planar 4 m projection; textures are packed and the scene saved in place.

Self-checks (exit 1, scene NOT saved): every pavement vertex has ground under it (stations without are left out before
meshing); no pavement point (vertices, edge midpoints, centroids) under the ground + 0.03 m after the lift; nothing
within 1 m under a 1ROAD surface of the loop (the loop's decks pass OVER the freeway, never on it); every mesh under
the 65,535-vertex cap. Writes data/freeway_i8.report.json.

    blender --background --python-exit-code 1 --python tools/author_freeway_blend.py -- <project-dir> --eng <engine-july>
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

UV_TILE = 4.0           # build_kn5_loop.UV_TILE
VERT_CAP = 60000        # build_kn5_loop.SPLIT_CAP
MIN_CLEAR = 0.03        # [invented] after the lift, no pavement point within this of the ground
RAISE_MAX = 0.5         # [invented] the most the lift check may raise a pavement vertex; a face it cannot clear is left out
DECK_CLEAR = 2.0        # [invented] a station with a loop deck (1ROAD / 1KERB) less than this over its pavement is left out
LINE_LIFT = 0.02        # [invented] lines over the pavement
BAR_BASE, BAR_TOP, BAR_H, BAR_SINK = 0.60, 0.20, 0.81, 0.30


def _bvh(objs):
    vs, fs = [], []
    for ob in objs:
        base = len(vs)
        mw = ob.matrix_world
        vs += [tuple(mw @ v.co) for v in ob.data.vertices]
        fs += [tuple(base + i for i in p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(vs, fs) if fs else None


class Mesh:
    def __init__(self):
        self.v, self.f = [], []

    def add(self, p):
        self.v.append(p)
        return len(self.v) - 1


def _ob(name, M):
    used = sorted({i for f in M.f for i in f})
    if len(used) != len(M.v):                     # faces left out on a slope leave loose vertices: compact
        remap = {o: n for n, o in enumerate(used)}
        M.v = [M.v[o] for o in used]
        M.f = [tuple(remap[i] for i in f) for f in M.f]
    me = bpy.data.meshes.new(name)
    me.from_pydata(M.v, [], M.f)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / UV_TILE, co.y / UV_TILE)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    down = [f for f in bm.faces if f.normal.z < 0 and abs(f.normal.z) > 0.2]
    if down and not name.startswith("BARRIER"):
        bmesh.ops.reverse_faces(bm, faces=down)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    eng = Path(argv[argv.index("--eng") + 1]) if "--eng" in argv else None
    data = proj / "data"
    fp = data / "freeway_i8.json"
    if not fp.exists():
        print("[freeway] no data/freeway_i8.json (scenery.freeway off) — nothing to do")
        return
    if eng is None:
        raise SystemExit("[freeway] --eng <engine-july> is required (materials bind through its pbr)")
    F = json.loads(fp.read_text(encoding="utf-8"))
    P = F["params"]
    lift, lw = float(P["lift_m"]), float(P["line_w_m"])
    dash, period = float(P["dash_m"]), float(P["dash_period_m"])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    blend = proj / "blender" / f"{cfg['slug']}.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    for ob in list(bpy.data.objects):
        if ob.name.upper().startswith(("HIGHWAY_I8", "MARKINGS_I8", "YLINE_I8", "BARRIER_I8")):
            bpy.data.objects.remove(ob, do_unlink=True)
    terr = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(("1GRASS", "GRASS_FAR"))]
    roads = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1ROAD")]
    decks = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(("1ROAD", "1KERB"))]
    ground = _bvh(terr)
    roadb = _bvh(decks)
    if ground is None or roadb is None:
        raise SystemExit("[freeway] the prepped scene has no 1GRASS/GRASS_FAR ground or no 1ROAD")
    rv = [o.matrix_world @ v.co for o in roads for v in o.data.vertices]
    box = (min(v.x for v in rv), max(v.x for v in rv), min(v.y for v in rv), max(v.y for v in rv))

    def near(x, y):
        return box[0] <= x <= box[1] and box[2] <= y <= box[3]

    def gz(x, y):
        h = ground.ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)), 6000.0)
        return h[0].z if h[0] is not None else None

    pave = {"NEAR": [Mesh()], "FAR": [Mesh()]}
    lines = {"MARKINGS": [Mesh()], "YLINE": [Mesh()]}
    n_sta = n_skip = n_deck = 0
    strips = 0
    built = []
    for ch in F["chains"]:
        runs, cur = [], []
        for st in ch + [None]:
            ok = st is not None
            if ok:
                offs = sorted({-st["wr"], st["wl"], *st["edge"], *st["dash"]})
                offs = [o for o in offs if -st["wr"] - 1e-6 <= o <= st["wl"] + 1e-6]
                nx, ny = -st["tz"], st["tx"]
                cs = [(st["x"] + nx * o, st["z"] + ny * o) for o in offs]
                hs = [gz(x, y) for x, y in cs]
                if any(h is None for h in hs):
                    ok = False
                    n_skip += 1
                elif any(roadb.ray_cast(Vector((x, y, h + lift - 0.05)), Vector((0, 0, 1)), DECK_CLEAR)[0] is not None
                         for (x, y), h in zip(cs, hs)):
                    # under a loop deck's abutment the ground is pinned to the deck (the bridge's own earth): the
                    # freeway passes there under the BRIDGESTRUCT abutment wall, not over the embankment top
                    ok = False
                    n_deck += 1
            if ok and cur and (len(offs) != len(cur[-1]["offs"]) or near(st["x"], st["z"]) != cur[-1]["near"]
                               or st["lanes"] != cur[-1]["st"]["lanes"]):
                runs.append(cur)
                cur = []
            if not ok:
                if cur:
                    runs.append(cur)
                cur = []
                continue
            n_sta += 1
            cur.append({"st": st, "offs": offs, "cs": cs, "hs": hs, "near": near(st["x"], st["z"])})
        for run in runs:
            if len(run) < 2:
                continue
            strips += 1
            kind = "NEAR" if run[0]["near"] else "FAR"
            M = pave[kind][-1]
            if len(M.v) + len(run) * len(run[0]["offs"]) > VERT_CAP:
                pave[kind].append(Mesh())
                M = pave[kind][-1]
            rows = []
            for r in run:
                rows.append([M.add([x, y, h + lift]) for (x, y), h in zip(r["cs"], r["hs"])])
            for ra, rb in zip(rows, rows[1:]):
                for k in range(len(ra) - 1):
                    M.f.append((ra[k], ra[k + 1], rb[k + 1], rb[k]))
            built.append((kind, M, run, rows))
    # the lift is checked, not assumed: every pavement point (vertices, edge midpoints, centroids) stands MIN_CLEAR over
    # the ground; a face that does not is raised (its vertices) by the shortfall, round after round
    def short(M, f):
        """how far face f's lowest test point (vertices, edge midpoints, centroid) is under ground + MIN_CLEAR"""
        ps = [Vector(M.v[i]) for i in f]
        tests = ps + [(ps[i] + ps[(i + 1) % len(ps)]) / 2 for i in range(len(ps))] + [sum(ps, Vector()) / len(ps)]
        need = 0.0
        for t in tests:
            g = gz(t.x, t.y)
            if g is not None and t.z < g + MIN_CLEAR + 1e-4:
                need = max(need, g + MIN_CLEAR + 0.005 - t.z)
        return need

    n_raised = 0
    cum = {}
    for _round in range(6):
        bump = {}
        for kind, Ms in pave.items():
            for M in Ms:
                for f in M.f:
                    need = short(M, f)
                    if need > 0:
                        for i in f:
                            k = (id(M), i)
                            room = RAISE_MAX - cum.get(k, 0.0)
                            if room > 1e-6:
                                bump[k] = max(bump.get(k, 0.0), min(need, room))
        if not bump:
            break
        for kind, Ms in pave.items():
            for M in Ms:
                for (mid, i), dz in bump.items():
                    if mid == id(M):
                        M.v[i][2] += dz
        for k, dz in bump.items():
            cum[k] = cum.get(k, 0.0) + dz
        n_raised = len(cum)
    # a face the capped raise could not lift clear (the ground climbing an abutment or a cut wall under it) is left out:
    # the pavement stops there, it never stands up into the slope
    n_dropped = 0
    dropped = {}
    for kind, Ms in pave.items():
        for M in Ms:
            keep, gone = [], set()
            for f in M.f:
                if short(M, f) > 0:
                    gone.update(f)
                else:
                    keep.append(f)
            n_dropped += len(M.f) - len(keep)
            M.f = keep
            dropped[id(M)] = gone
    # lines on the (checked) pavement: dashed lane lines; solid edge lines (white outside, yellow on the median side)
    for kind, M, run, rows in built:
        if kind != "NEAR":
            continue
        st0 = run[0]["st"]
        for li, o in enumerate(run[0]["offs"]):
            is_dash = any(abs(o - d) < 1e-6 for d in st0["dash"])
            is_edge = any(abs(o - e) < 1e-6 for e in st0["edge"])
            if not (is_dash or is_edge):
                continue
            med = is_edge and (o > 0) == (st0["median_side"] > 0)
            key = "YLINE" if med else "MARKINGS"
            if len(lines[key][-1].v) > VERT_CAP - 4 * len(run):
                lines[key].append(Mesh())
            L = lines[key][-1]
            acc = 0.0
            gone = dropped.get(id(M), set())
            for ra, rb in zip(rows, rows[1:]):
                if ra[li] in gone or rb[li] in gone:
                    continue
                pa, pb = M.v[ra[li]], M.v[rb[li]]
                ax, ay, bx, by = pa[0], pa[1], pb[0], pb[1]
                seg = math.hypot(bx - ax, by - ay) or 1e-9
                t0, t1 = acc, acc + seg
                acc = t1
                if is_dash:
                    k = math.floor(t0 / period)
                    a = max(t0, k * period)
                    b = min(t1, k * period + dash)
                    if b <= a:
                        continue
                    u0, u1 = (a - t0) / seg, (b - t0) / seg
                else:
                    u0, u1 = 0.0, 1.0
                ha, hb = pa[2] + LINE_LIFT, pb[2] + LINE_LIFT
                nx, ny = -(by - ay) / seg, (bx - ax) / seg
                p0 = (ax + (bx - ax) * u0, ay + (by - ay) * u0, ha + (hb - ha) * u0)
                p1 = (ax + (bx - ax) * u1, ay + (by - ay) * u1, ha + (hb - ha) * u1)
                q = [L.add((p0[0] - nx * lw / 2, p0[1] - ny * lw / 2, p0[2])),
                     L.add((p0[0] + nx * lw / 2, p0[1] + ny * lw / 2, p0[2])),
                     L.add((p1[0] + nx * lw / 2, p1[1] + ny * lw / 2, p1[2])),
                     L.add((p1[0] - nx * lw / 2, p1[1] - ny * lw / 2, p1[2]))]
                L.f.append(tuple(q))
    # the median barrier
    bars = [Mesh()]
    prof = [(-BAR_BASE / 2, -BAR_SINK), (-BAR_BASE / 2, 0.0), (-BAR_TOP / 2, BAR_H), (BAR_TOP / 2, BAR_H),
            (BAR_BASE / 2, 0.0), (BAR_BASE / 2, -BAR_SINK)]
    n_bar = 0
    for line in F["barrier"]:
        rings = []
        for k, (x, y) in enumerate(line):
            a = line[max(0, k - 1)]
            b = line[min(len(line) - 1, k + 1)]
            L2 = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            nx, ny = -(b[1] - a[1]) / L2, (b[0] - a[0]) / L2
            h = gz(x, y)
            if h is None or roadb.ray_cast(Vector((x, y, h + lift - 0.05)), Vector((0, 0, 1)), DECK_CLEAR + BAR_H)[0]                     is not None:
                rings.append(None)
                continue
            M = bars[-1]
            rings.append([M.add((x + nx * o, y + ny * o, h + lift + dz)) for o, dz in prof])
        M = bars[-1]
        for ra, rb in zip(rings, rings[1:]):
            if ra is None or rb is None:
                continue
            for k in range(len(prof) - 1):
                M.f.append((ra[k], ra[k + 1], rb[k + 1], rb[k]))
            n_bar += 1
        if len(M.v) > VERT_CAP - 5000:
            bars.append(Mesh())
    # self-checks on the pavement: still under the ground after the raise rounds, or under the loop's decks
    low, under_road = 0, []
    for kind, Ms in pave.items():
        for M in Ms:
            used = sorted({i for f in M.f for i in f})
            for i in used:
                v = M.v[i]
                g = gz(v[0], v[1])
                if g is not None and v[2] < g + MIN_CLEAR:
                    low += 1
                h = roadb.ray_cast(Vector((v[0], v[1], v[2] - 0.05)), Vector((0, 0, 1)), 1.0)
                if h[0] is not None:
                    under_road.append((round(v[0], 1), round(v[1], 1)))
    if low or under_road:
        raise SystemExit(f"[freeway] FATAL: {low} pavement vertices within {MIN_CLEAR} m of the ground (or under it); "
                         f"{len(under_road)} vertices under a 1ROAD deck within 1 m {under_road[:4]} — scene NOT saved")
    spec = importlib.util.spec_from_file_location("_eng_pbr_freeway", eng / "scripts" / "ac" / "pbr.py")
    pbr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pbr)
    overrides = pbr.load_overrides(proj)
    made = {}
    for prefix, Ms in (("HIGHWAY_I8_NEAR", pave["NEAR"]), ("HIGHWAY_I8_FAR", pave["FAR"]),
                       ("MARKINGS_I8", lines["MARKINGS"]), ("YLINE_I8", lines["YLINE"]), ("BARRIER_I8", bars)):
        k = 0
        for M in Ms:
            if not M.f:
                continue
            if len(M.v) > 65535:
                raise SystemExit(f"[freeway] FATAL: {prefix}_{k} has {len(M.v)} vertices (> 65,535)")
            ob = _ob(f"{prefix}_{k}", M)
            pbr.setup_material(bpy, ob, overrides=overrides)
            made[ob.name] = len(M.v)
            k += 1
    try:
        bpy.ops.file.pack_all()
    except Exception as e:  # noqa: BLE001
        print(f"[freeway] pack_all warning: {e}")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    rep = {"_doc": "tools/author_freeway_blend.py (ledger 0046 v0.18.0 integration fix round)", "stations": n_sta,
           "stations_off_the_ground": n_skip, "stations_under_a_deck_abutment": n_deck, "strips": strips, "vertices_raised_over_the_ground": n_raised, "faces_left_out_on_a_slope": n_dropped, "barrier_segments": n_bar, "objects": made,
           "road_extent_xy": [round(b, 1) for b in box], "lift_m": lift}
    (data / "freeway_i8.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[freeway] I-8: {n_sta} stations draped ({n_skip} off the ground, {n_deck} under a deck abutment left out) "
          f"in {strips} strips, barrier "
          f"{n_bar} segments; objects {made}; saved {blend.name}")


main()

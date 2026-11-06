"""The median barrier where two freeway carriageways share one paved width (ledger 0080 phase 2a, the SD freeway port).

tools/naip_carriageways.py measured I 8's two carriageways off NAIP 2022: where the pavement runs unbroken from one
carriageway into the other, the section is one paved width with a concrete median barrier, and each carriageway's
inner edge was put at the barrier's face (its base half-width from the barrier's centre line). This step stands the
barrier there, as a solid: Caltrans Concrete Barrier Type 60 (Standard Plans A76A), its numbers in
median_barrier.json (0.914 m high, 0.610 m base, 9.1 deg faces, 0.317 m top).

Each side's foot sits on that side's BUILT pavement: ROAD (the assembler's merged line + connectors) is ray-cast
straight down FOOT_PROBE_M out from the centre line on each side. The top is BARRIER_H above the higher foot; where the
two pavements differ in height (the Morena interchange: WB above the line, both levelled there, neither measured)
the low side's face runs down to the low pavement — a retaining face, reported, not a Type 60 (the A76 family's unequal-
grade variants are not read here). The body is buried BURY_M below the lower foot so no ground shows under it.

Before the barrier is written, every TERRAIN face reaching within SEAM_BAND_M of a barrier run is cut to edges of at
most SEAM_EDGE_M (bmesh grid fill, as tools/seat_edges_blend.py cuts): a 13.75 m ground facet pinned to both pavements
otherwise stands over the lower one's lane (ws10). No vertex moves here; the prep's pin places the new ones.

The mesh is 1WALL_MEDIAN (engine-july's 1WALL: collidable, double-sided, concrete_barrier texture), written into
loop.blend. Opt-in by ship.json draft step `median_barrier`; Lake Murray never names it. Reads the run file named by
track.config.json lm_intake.median_barrier_file in the source data folder.

    blender --background --python tools/median_barrier_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]
FOOT_PROBE_M = (0.6, 1.2, 2.0)   # [invented] how far out from the centre line each side's pavement is sought (first hit)
BURY_M = 0.3                     # [invented] the body's bottom below the lower foot
MAX_DIFF_M = 6.0                 # [invented] a foot more than this below the other is not this carriageway's: dropped
SEAM_BAND_M = 1.0                # [invented] a TERRAIN face reaching within this of the barrier line is cut ...
SEAM_EDGE_M = 2.0                # [invented] ... to edges of at most this, so no ground triangle spans from under one
#                                  carriageway to under the other (ws10: 13.75 m facets pinned to both pavements stood over
#                                  the lower one's lane, WB soft top at s 4,650-4,800 and 5,450-5,600 with 0.2-0.5 m between
#                                  them); the prep's pin then places every new vertex. Nothing is moved here.
SKIRT_M = 40.0                   # seat_edges' rule: a face longer than this is the grid's far skirt, never near a road
# ledger 0080 2a round 5 (owed item 3, WB s 7,052): beside a DECK the barrier stood on nothing. Each carriageway's inner
# edge stands BARRIER_CLEAR (0.3 m) off the barrier's foot (naip_carriageways), and off a deck the prep's contact pin
# raises the ground in that slot to the pavement; on a deck nothing does (the ground is the real ground under the bridge:
# 10 m down under WB's Morena deck), so between WB's deck edge and the barrier's face drive_test fell 1.61 m, unguarded
# (the face stood past its probe). A barrier on a bridge stands on the deck: under every LEVEL section (feet within the
# 0.3 m retaining threshold; across a step audit_mesh F reads the slab as a curb not flush) whose foot is on a
# declared deck (the line's lm_intake bridges_levelled, a network connector's decks_all) the deck is carried from just
# under that pavement's edge to the barrier's far foot, DECK_EDGE_DY_M under the foot (deck_rails_blend's slab: the same
# mesh, 1KERB_SIDEWALK_DECK).
DECK_EDGE_DY_M = 0.03            # reused: tools/deck_rails_blend.py, the slab's top under the pavement's edge height
DECK_EDGE_IN_M = 0.1             # reused: tools/deck_rails_blend.py, the slab runs this far under the pavement's edge
DECK_EDGE_NAME = "1KERB_SIDEWALK_DECK"


def _decked(proj):
    """[(points (x, z), per-point on-a-deck flags)] for the line and every network connector, as declared."""
    import importlib.util
    data = proj / "data"
    out = []
    raw = json.loads((data / "centerline.raw.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    loc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    decks = json.loads((data / "lm_intake.json").read_text(encoding="utf-8")).get("bridges_levelled") or []
    st = [0.0]
    for a, b in zip(raw, raw[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    out.append(([(q[0], q[2]) for q in loc],
                [any(float(c) - float(ln) / 2.0 <= s <= float(c) + float(ln) / 2.0 for c, ln in decks) for s in st]))
    p = data / "connectors.local.json"
    if p.exists():
        spec = importlib.util.spec_from_file_location(
            "v021_smooth", AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py")
        sm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sm)
        for c in json.loads(p.read_text(encoding="utf-8")).get("connectors") or []:
            if not c.get("network"):
                continue
            cpts = sm.smooth_centerline([tuple(q) for q in c["points_xyz_m"]], sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
            fl = [False] * len(cpts)
            for a, b in c.get("decks_all") or []:
                for k in range(a, min(b, len(fl) - 1) + 1):
                    fl[k] = True
            out.append(([(q[0], q[2]) for q in cpts], fl))
    return out


def _local_to_blend(x, y, z):
    # the assembler's remap (build_loop_blend.make_mesh): local (x = E, y = up, z = N) -> Blender (x, z, y)
    return Vector((x, z, y))


def seam_terrain(runs):
    """Cut every TERRAIN face that reaches within SEAM_BAND_M of a barrier run to edges <= SEAM_EDGE_M (grid fill)."""
    import bmesh
    from mathutils.kdtree import KDTree
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[median-barrier] FATAL: no TERRAIN in loop.blend")
    pts = []
    for run in runs:
        xz = run["xz"]
        for a, b in zip(xz, xz[1:]):
            n = max(1, int(math.dist(a, b) / 0.5))
            pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    kd = KDTree(len(pts))
    for i, (x, z) in enumerate(pts):
        kd.insert((x, z, 0.0), i)
    kd.balance()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n0 = len(bm.verts)
    groups = {}
    for f in bm.faces:
        lng = max(e.calc_length() for e in f.edges)
        if lng > SKIRT_M:
            continue
        c = f.calc_center_median()
        rad = max((v.co.xy - c.xy).length for v in f.verts)
        _co, _i, d = kd.find((c.x, c.y, 0.0))
        if d is None or d > rad + SEAM_BAND_M:
            continue
        cuts = math.ceil(lng / SEAM_EDGE_M) - 1
        if cuts >= 1:
            groups.setdefault(cuts, []).append(f)
    n_cut = 0
    for cuts in sorted(groups, reverse=True):
        fs = [f for f in groups[cuts] if f.is_valid]
        edges = list({e for f in fs for e in f.edges if e.is_valid})
        if edges:
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
            n_cut += len(fs)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return n_cut, n0, len(ob.data.vertices)


def main():
    proj = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    li = cfg.get("lm_intake") or {}
    name = li.get("median_barrier_file")
    if not name:
        print("[median-barrier] no lm_intake.median_barrier_file: nothing written")
        return
    src = AIROSO / "tracks" / li["source_track"] / (li.get("source_data") or "data") / name
    doc = json.loads(src.read_text(encoding="utf-8"))
    bar = doc["barrier"]
    H, B, T = float(bar["height_m"]), float(bar["base_m"]), float(bar["top_m"])
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    if bpy.data.objects.get("1WALL_MEDIAN") is not None:
        raise SystemExit("[median-barrier] FATAL: loop.blend already has 1WALL_MEDIAN")
    road = bpy.data.objects["ROAD"]
    mw = road.matrix_world
    verts_w = [mw @ v.co for v in road.data.vertices]
    bvh = BVHTree.FromPolygons(verts_w, [tuple(p.vertices) for p in road.data.polygons])
    up = Vector((0, 0, 1))

    def foot(x, zl, nx, nz, sg):
        for d in FOOT_PROBE_M:
            px, pz = x + sg * d * nx, zl + sg * d * nz
            o = _local_to_blend(px, 1e4, pz)
            hit = bvh.ray_cast(o, -up, 2e4)
            if hit[0] is not None:
                return hit[0].z
        return None

    from mathutils.kdtree import KDTree
    carr = _decked(proj)
    kds = []
    for pts_, _fl in carr:
        kd_ = KDTree(len(pts_))
        for k, (px, pz) in enumerate(pts_):
            kd_.insert((px, pz, 0.0), k)
        kd_.balance()
        kds.append(kd_)

    def on_deck(px, pz):
        best = None
        for (pts_, fl), kd_ in zip(carr, kds):
            _co, k, d = kd_.find((px, pz, 0.0))
            if k is not None and (best is None or d < best[0]):
                best = (d, fl[k])
        return bool(best and best[1])

    def edge_d(x, zl, nx, nz, sg):
        """The pavement's edge on side sg: the first distance out from the centre line (0.05 m steps) over ROAD."""
        d = 0.0
        while d <= FOOT_PROBE_M[-1] + 1e-6:
            o = _local_to_blend(x + sg * d * nx, 1e4, zl + sg * d * nz)
            if bvh.ray_cast(o, -up, 2e4)[0] is not None:
                return d
            d += 0.05
        return None
    slab_v, slab_f = [], []
    n_slab = 0

    verts, faces = [], []
    rep = []
    n_retain = 0
    for run in doc["runs"]:
        xz = run["xz"]
        if len(xz) < 2:
            continue
        sec = []
        for i, (x, z) in enumerate(xz):
            a = xz[max(0, i - 1)]
            b = xz[min(len(xz) - 1, i + 1)]
            tx, tz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L                     # left of the run's direction
            yl = foot(x, z, nx, nz, 1)
            yr = foot(x, z, nx, nz, -1)
            if yl is None and yr is None:
                sec.append(None)
                continue
            yl = yr if yl is None else yl
            yr = yl if yr is None else yr
            if abs(yl - yr) > MAX_DIFF_M:
                sec.append(None)
                continue
            sec.append((x, z, nx, nz, yl, yr))
        # runs of sections with both feet found
        k = 0
        while k < len(sec):
            if sec[k] is None:
                k += 1
                continue
            j = k
            while j + 1 < len(sec) and sec[j + 1] is not None:
                j += 1
            if j > k:
                base = len(verts)
                for q in range(k, j + 1):
                    x, z, nx, nz, yl, yr = sec[q]
                    top = max(yl, yr) + H
                    bot = min(yl, yr) - BURY_M
                    if abs(yl - yr) > 0.3:
                        n_retain += 1
                    prof = [(B / 2, bot), (B / 2, yl), (T / 2, top), (-T / 2, top), (-B / 2, yr), (-B / 2, bot)]
                    for sg_, yf in ((1, yl), (-1, yr)):     # the deck under the barrier, on a deck side
                        if q == j:
                            continue
                        x2, z2, nx2, nz2, yl2, yr2 = sec[q + 1]
                        # a LEVEL section only (feet within the retaining threshold): across a stepped one the slab's
                        # vertices stand > 0.5 m off the other carriageway's edge, 2 m away, and audit_mesh F reads
                        # them as curbs not flush (ws25: 64)
                        if abs(yl - yr) > 0.3 or abs(yl2 - yr2) > 0.3:
                            continue
                        yf2 = yl2 if sg_ > 0 else yr2
                        e1, e2 = edge_d(x, z, nx, nz, sg_), edge_d(x2, z2, nx2, nz2, sg_)
                        if e1 is None or e2 is None or not on_deck(x + sg_ * e1 * nx, z + sg_ * e1 * nz):
                            continue
                        b0 = len(slab_v)
                        for (xa, za, nxa, nza, ya, ea) in ((x, z, nx, nz, yf, e1), (x2, z2, nx2, nz2, yf2, e2)):
                            for off in (ea + DECK_EDGE_IN_M, -B / 2):
                                slab_v.append(_local_to_blend(xa + sg_ * off * nxa, ya - DECK_EDGE_DY_M,
                                                              za + sg_ * off * nza))
                        slab_f.append((b0, b0 + 1, b0 + 3, b0 + 2) if sg_ > 0 else (b0, b0 + 2, b0 + 3, b0 + 1))  # face up
                        n_slab += 1
                    for off, y in prof:
                        verts.append(_local_to_blend(x + off * nx, y, z + off * nz))
                m = len(prof)
                for q in range(j - k):
                    a0, b0 = base + q * m, base + (q + 1) * m
                    for e in range(m):
                        f = (e + 1) % m
                        faces.append((a0 + e, a0 + f, b0 + f, b0 + e))
                faces.append(tuple(base + e for e in range(m)))
                last = base + (j - k) * m
                faces.append(tuple(last + e for e in reversed(range(m))))
                rep.append({"stations_m": run["stations_m"], "sections": j - k + 1})
            k = j + 1
    if not verts:
        print("[median-barrier] no section found its pavement: nothing written")
        return
    n_cut, t0, t1 = seam_terrain(doc["runs"])
    print(f"[median-barrier] TERRAIN near the barrier cut to <= {SEAM_EDGE_M} m: {n_cut} faces, {t0} -> {t1} verts")
    me = bpy.data.meshes.new("1WALL_MEDIAN")
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    mat = bpy.data.materials.new("1WALL_MEDIAN_mat")
    mat.diffuse_color = (0.72, 0.72, 0.70, 1.0)
    me.materials.append(mat)
    ob = bpy.data.objects.new("1WALL_MEDIAN", me)
    bpy.context.scene.collection.objects.link(ob)
    if slab_f:
        import bmesh
        dob = bpy.data.objects.get(DECK_EDGE_NAME)
        if dob is None:
            sme = bpy.data.meshes.new(DECK_EDGE_NAME)
            sme.from_pydata([tuple(v) for v in slab_v], [], slab_f)
            sme.update()
            smat = bpy.data.materials.new(DECK_EDGE_NAME + "_mat")
            smat.diffuse_color = (0.66, 0.66, 0.64, 1.0)
            sme.materials.append(smat)
            dob = bpy.data.objects.new(DECK_EDGE_NAME, sme)
            bpy.context.scene.collection.objects.link(dob)
        else:
            inv = dob.matrix_world.inverted()
            bm = bmesh.new()
            bm.from_mesh(dob.data)
            vs = [bm.verts.new(inv @ v) for v in slab_v]
            for f in slab_f:
                bm.faces.new([vs[k] for k in f])
            bm.to_mesh(dob.data)
            bm.free()
            dob.data.update()
    print(f"[median-barrier] the deck under the barrier where its foot is on a declared deck: {n_slab} quads "
          f"({DECK_EDGE_NAME}, {DECK_EDGE_DY_M} m under the foot, from {DECK_EDGE_IN_M} m under the pavement's edge "
          f"to the far foot)")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    length = sum(math.dist(r0, r1) for run in doc["runs"] for r0, r1 in zip(run["xz"], run["xz"][1:]))
    out = {"tool": "tools/median_barrier_blend.py", "ledger": "0080 2a", "barrier": bar, "runs": rep,
           "sections_retaining_over_0_3m": n_retain, "vertices": len(verts), "run_length_m": round(length, 1),
           "deck_under_barrier_quads": n_slab}
    (proj / "data" / "median_barrier.built.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[median-barrier] 1WALL_MEDIAN: {len(rep)} run(s), {sum(r['sections'] for r in rep)} sections, "
          f"{len(verts)} vertices; {n_retain} sections with feet > 0.3 m apart (a retaining face)")


if __name__ == "__main__":
    main()

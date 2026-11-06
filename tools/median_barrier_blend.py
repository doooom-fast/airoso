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
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    length = sum(math.dist(r0, r1) for run in doc["runs"] for r0, r1 in zip(run["xz"], run["xz"][1:]))
    out = {"tool": "tools/median_barrier_blend.py", "ledger": "0080 2a", "barrier": bar, "runs": rep,
           "sections_retaining_over_0_3m": n_retain, "vertices": len(verts), "run_length_m": round(length, 1)}
    (proj / "data" / "median_barrier.built.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[median-barrier] 1WALL_MEDIAN: {len(rep)} run(s), {sum(r['sections'] for r in rep)} sections, "
          f"{len(verts)} vertices; {n_retain} sections with feet > 0.3 m apart (a retaining face)")


if __name__ == "__main__":
    main()

"""The road-building section and the stacked-leg hold on the LM engine's terrain, before the prep (ledger 0078 round 7).

PR 32's P3a (scripts/geometry/cutfill.py, ledger 0048): the ground beside the road is the section the road was built to
(the verge at the edge's height, a cut bench and a 0.25:1 rock face where the ground stands above, a fill hinge and a
1.5:1 face where it falls away), and between STACKED legs (the climb's switchbacks, 21 m apart in plan, 6.5-15 m in
height) every ground point is held on its own leg's side of the midpoint height (by the section's margin, 0.3 m),
ownership read exactly as tools/verify_stacked_legs.py reads it. build_mesh grades its grid with it; the v021 assembler
does not, so on the LM engine 101 ground vertices between the Lariat's legs followed the other leg (the gate's L4 red).

This step grades the assembler's TERRAIN with the same CrossSection, on the line the ROAD mesh was swept along (its
mainline centre row: x, deck height, z; widths from its edge rows). engine-july's prep then pins under the road, holds the
first 3 m at the edge, feathers 3-9 m toward the NEAREST road and splits corridor edges to 4.5 m. The pin, band and
feather move a point toward its nearest road's height, which keeps an upper leg's ground above the midpoint and a lower
leg's below; the corridor split would add points interpolated ACROSS the hold, so (as Lake Murray's seat_terrain does
before its prep) the terrain is first split here to the prep's own CORRIDOR_EDGE_M within its reach, and every point,
old and new, is graded: the prep then finds nothing to split. Opt-in: terrain.cross_section.build true and the draft
step `cutfill`; Lake Murray never runs it.

    blender --background --python-exit-code 1 --python tools/cutfill_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import kdtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mouth_weld as mw  # noqa: E402
from scripts.geometry import cutfill  # noqa: E402

CORRIDOR_EDGE_M = 4.5   # engine-july build_kn5_loop.CORRIDOR_EDGE_M: the prep splits corridor edges down to this
REACH_M = 16.0          # engine-july's split reach: FEATHER_M (6) + 10 m from the nearest road vertex
PASSES = 16             # [invented] bisection passes (each halves the longest edges; 13.3 m cells need ~4)
CLEARANCE_M = 0.02      # engine-july's GROUND_CLEAR: the ground under the deck's edge


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    if not cutfill.section_enabled(cfg):
        print("[cutfill] terrain.cross_section.build is not true: nothing to do")
        return
    xs = (cfg.get("terrain") or {}).get("cross_section") or {}
    verge = float(((cfg.get("road_profile") or {}).get("verge_m")) or 0.4)
    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lay = mw.mesh_layout([tuple(p) for p in local["points_xyz_m"]], [])
    rows, closed = lay["MAINLINE"]["rows"], lay["MAINLINE"]["closed"]
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    road, terr = bpy.data.objects.get("ROAD"), bpy.data.objects.get("TERRAIN")
    if road is None or terr is None:
        raise SystemExit("[cutfill] FATAL: no ROAD or TERRAIN in loop.blend")
    RV = road.data.vertices
    line, widths = [], []
    for r in range(rows):
        L = RV[mw.road_index(lay, "MAINLINE", r, 0)].co
        C = RV[mw.road_index(lay, "MAINLINE", r, 1)].co
        R = RV[mw.road_index(lay, "MAINLINE", r, 2)].co
        line.append((C.x, C.z, C.y))                       # cutfill's frame: x east, y up, z north
        widths.append(math.hypot(L.x - R.x, L.y - R.y))
    if closed:
        line.append(line[0]); widths.append(widths[0])
    # the declared decks (capture.bridges, stations on this line): no fill under a deck
    decks = [(float(b["center_m"]) - float(b["len_m"]) / 2, float(b["center_m"]) + float(b["len_m"]) / 2)
             for b in ((cfg.get("capture") or {}).get("bridges") or [])]
    (proj / "data" / "cutfill.line.json").write_text(json.dumps({
        "_doc": "tools/cutfill_blend.py (ledger 0078 round 7): the line the ground was graded on (ROAD's mainline centre "
                "row, cutfill's frame: x east, y up, z north) and its widths; tools/hold_stacked_blend.py re-reads it after "
                "the prep", "line": [[round(c, 4) for c in q] for q in line], "widths": [round(w, 4) for w in widths],
        "decks": decks, "verge_m": verge}), encoding="utf-8")
    cs = cutfill.CrossSection(line, widths, verge_m=verge,
                              fill_bench_m=float(xs.get("fill_bench_m", 0.0) or 0.0),
                              cut_bench_m=float(xs.get("cut_bench_m", 0.0) or 0.0),
                              cut_hv=cutfill.parse_ratio(xs.get("rock_cut_slope"), 0.25),
                              fill_hv=cutfill.parse_ratio(xs.get("fill_slope"), 1.5),
                              clearance=CLEARANCE_M, bank_at=None,
                              bridge_of=(lambda st: any(a <= st <= b for a, b in decks)) if decks else None)
    # the prep's own reach: road vertices in plan
    kd = kdtree.KDTree(len(RV))
    for i, v in enumerate(RV):
        kd.insert((v.co.x, v.co.y, 0.0), i)
    kd.balance()

    def near_road(x, y):
        co, _i, d = kd.find((x, y, 0.0))
        return co is not None and d <= REACH_M

    bm = bmesh.new(); bm.from_mesh(terr.data)
    n0 = len(bm.verts)
    n_split = 0
    # the corridor split to the prep's own CORRIDOR_EDGE_M, by LONGEST-EDGE BISECTION: each long edge halved and both
    # triangles beside it split through the new vertex to their far corner (bmesh.utils, triangles only). Not the prep's
    # subdivide-then-triangulate: repeated until nothing was left for the prep, that left 80,946 duplicate and 110,842
    # zero-area ground faces on the Lariat (round 7, run 3), and once (run 1) 46,335 long diagonals the prep then split,
    # interpolated across the hold (35 L4 reds)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    nat = bm.verts.layers.float.new("cutfill_natural")      # the natural ground, interpolated into every split vertex

    def bisect(need=None):
        """one pass: every corridor edge over CORRIDOR_EDGE_M (3-D, as the prep measures it) [that need() picks],
        longest first"""
        n = 0
        todo = []
        for e in bm.edges:
            if e.calc_length() <= CORRIDOR_EDGE_M:
                continue
            m = (e.verts[0].co + e.verts[1].co) / 2
            if near_road(m.x, m.y) and (need is None or need(e)):
                todo.append(e)
        todo.sort(key=lambda e: -e.calc_length())
        for e in todo:
            if not e.is_valid or e.calc_length() <= CORRIDOR_EDGE_M:
                continue
            tris = [(f, next(v for v in f.verts if v not in e.verts)) for f in e.link_faces if len(f.verts) == 3]
            va, vb = e.verts
            mid_nat = (va[nat] + vb[nat]) / 2.0
            _ne, nv = bmesh.utils.edge_split(e, va, 0.5)
            nv[nat] = mid_nat
            for f, far in tris:
                if f.is_valid and len(f.verts) == 4:
                    bmesh.utils.face_split(f, nv, far)
            n += 1
        return n
    for v in bm.verts:
        v[nat] = v.co.z
    for _pass in range(PASSES):                              # on the natural ground
        k = bisect()
        n_split += k
        if not k:
            break
    moved = 0
    graded = set()

    def grade():
        nonlocal moved
        for v in bm.verts:
            if v in graded:
                continue
            g = cs.height(v.co.x, v.co.y, v[nat], count=True)
            if abs(g - v.co.z) > 1e-6:
                moved += 1
            v.co.z = g
            graded.add(v)
    grade()
    left = sum(1 for e in bm.edges if e.calc_length() > CORRIDOR_EDGE_M
               and near_road(*((e.verts[0].co + e.verts[1].co) / 2).xy))
    bm.verts.layers.float.remove(nat)
    bm.to_mesh(terr.data); bm.free(); terr.data.update()
    print(f"[cutfill] section: verge {verge} m, benches fill {cs.fill_bench} / cut {cs.cut_bench} m; "
          f"{sum(cs.stacked)} stacked lap points; {n_split} corridor edges split to <= {CORRIDOR_EDGE_M} m first, "
          f"{left} longer than that once graded (the prep splits those; tools/hold_stacked_blend.py holds after it) "
          f"(TERRAIN {n0} -> {len(terr.data.vertices)} verts); {moved} ground points moved {dict(cs.stats)}; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()

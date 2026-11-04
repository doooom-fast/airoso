"""Re-shape ONE raised island in an authored loop.blend to corrected median data, vertex for vertex (ledger 0054 Phase 2
step 4, 2026-11-04: Princess View's median, whose right face the automatic aerial reader took from two street trees).

    blender --background --python-exit-code 1 --python tools/reshape_island_blend.py -- <project-dir> \
        --island north_princess_view --old-bands <the median_bands.json the blend was authored from> \
        --out-blend <scratch .blend> [--blend <loop.blend>] [--new-bands <file>] [--report <json>] [--move-deck]

Why not re-run the draft: an LM v4 chain without --skip-blend rebuilds loop.blend and loses its 7,600 bespoke houses, and
tools/author_median_blend.py joins its islands INTO CURB / TERRAIN (re-running it would author every island twice). This
moves only the island's own vertices:

  1. tools/island_reshape.py computes the island's curb rings and deck exactly as author_median_blend lays them, from the
     OLD data and from the NEW data — the same runs, so the same vertex count and order.
  2. Every OLD vertex must be found in the blend (CURB / TERRAIN, within MATCH_TOL_M, one blend vertex each), else exit 1:
     the blend was not authored from that data, and nothing is saved.
  3. Each found CURB vertex moves to its NEW position. Faces, vertex order and every other vertex of the blend stay as they
     are. THE DECK STAYS (ledger 0054 Phase 2 step 2f; --move-deck moves it too, as step 4 did): it is terrain under the
     road slab that the prep pins to the road - 0.02, so the island's visible top does not depend on it. But the prep's
     corridor subdivision and its 1GRASS tile cuts read it, so a moved deck re-tiles and re-thins the ground across the map
     (island_reshape.moves).
  4. The island's two yellow edge lines (connectors.local.json paint, MEDIAN_EDGE_M off each face, in YLINE / MARKINGS)
     follow their face: a paint vertex within PAINT_BAND_M of an OLD edge line, inside the stations that changed, moves
     across the road by that face's change.
  5. The scratch blend is saved to --out-blend (never airoso's tracks/, never the input). The report lists every count and
     the largest move; --report writes it.

Exit 1 = refused (nothing saved). The PC judges the result on the built road (ledger 0054 Phase 2 step 4).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import mathutils

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import island_reshape as ir  # noqa: E402

MATCH_TOL_M = 0.003      # float32 at |x| ~ 3,000 m resolves ~0.25 mm: a blend vertex stands this close to its formula
PAINT_BAND_M = 0.25      # a paint vertex this close (across the road) to an old edge line is that line's
MEDIAN_EDGE_M = 0.30     # tools/expansion_pieces.MEDIAN_EDGE_M


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"project": None, "island": None, "old": None, "new": None, "blend": None, "out": None, "report": None,
         "move_deck": False}
    keys = {"--island": "island", "--old-bands": "old", "--new-bands": "new", "--blend": "blend", "--out-blend": "out",
            "--report": "report"}
    i = 0
    while i < len(argv):
        if argv[i] == "--move-deck":
            a["move_deck"] = True
            i += 1
        elif argv[i] in keys:
            a[keys[argv[i]]] = argv[i + 1]
            i += 2
        elif a["project"] is None:
            a["project"] = argv[i]
            i += 1
        else:
            raise SystemExit(f"[reshape] unknown argument {argv[i]!r}")
    if not a["project"] or not a["island"] or not a["old"] or not a["out"]:
        raise SystemExit("[reshape] usage: -- <project> --island <name> --old-bands <json> --out-blend <blend>")
    return a


def _island(bands_path, name):
    mb = json.loads(Path(bands_path).read_text(encoding="utf-8"))
    ci = next((c for c in mb.get("connector_islands") or [] if c.get("name") == name), None)
    if ci is None:
        raise SystemExit(f"[reshape] {bands_path}: no connector island {name!r}")
    return [tuple(p) for p in ci["points_xyz_m"]], [float(w) for w in ci["island_w_by_point"]]


def main():
    a = _args()
    proj = Path(a["project"]).resolve()
    out = Path(a["out"]).resolve()
    blend = Path(a["blend"] or proj / "loop.blend").resolve()
    if out == blend:
        raise SystemExit("[reshape] --out-blend must be a scratch copy, never the input blend")
    if "tracks" in out.parts and any((p / "fleet").is_dir() for p in out.parents):
        raise SystemExit(f"[reshape] {out} is inside an airoso checkout's tracks/ — a scratch path only")
    old_pts, old_iw = _island(a["old"], a["island"])
    new_pts, new_iw = _island(a["new"] or proj / "data" / "median_bands.json", a["island"])
    try:
        mv = ir.moves(old_pts, old_iw, new_pts, new_iw, move_deck=a["move_deck"])
    except ValueError as e:
        raise SystemExit(f"[reshape] REFUSED: {e}")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    objs = {n: bpy.data.objects.get(n) for n in ("CURB", "TERRAIN")}
    for n, ob in objs.items():
        if ob is None or ob.type != "MESH":
            raise SystemExit(f"[reshape] REFUSED: {blend.name} has no mesh {n}")
        if not ob.matrix_world.is_identity:
            raise SystemExit(f"[reshape] REFUSED: {n} carries a transform — the island's world positions are its data")
    trees = {}
    for n, ob in objs.items():
        kd = mathutils.kdtree.KDTree(len(ob.data.vertices))
        for v in ob.data.vertices:
            kd.insert(v.co, v.index)
        kd.balance()
        trees[n] = kd
    # 2. the presence check: every OLD island vertex, one blend vertex each
    found, missing, worst = {}, [], 0.0
    for obj, p, k in ir.all_vertices(old_pts, old_iw):
        co, idx, dist = trees[obj].find(p)
        if co is None or dist > MATCH_TOL_M:
            missing.append((obj, k, round(dist if dist is not None else -1, 4)))
            continue
        if (obj, idx) in found and found[(obj, idx)] != k:
            missing.append((obj, k, "shared"))
            continue
        found[(obj, idx)] = k
        worst = max(worst, dist)
    n_all = len(ir.all_vertices(old_pts, old_iw))
    print(f"[reshape] {a['island']}: {n_all} island vertices from the OLD data, {n_all - len(missing)} found "
          f"(worst {worst * 1000:.2f} mm)")
    if missing:
        raise SystemExit(f"[reshape] REFUSED: {len(missing)} island vertices not in {blend.name} as the old data lays them "
                         f"(first {missing[:6]}) — the blend was not authored from {a['old']}; nothing saved")
    # 3. the moves
    moved = {"CURB": 0, "TERRAIN": 0}
    big = 0.0
    stations = set()
    for obj, p, q, k in mv:
        co, idx, dist = trees[obj].find(p)
        v = objs[obj].data.vertices[idx]
        big = max(big, math.dist(p, q))
        v.co = mathutils.Vector(q)
        moved[obj] += 1
        stations.add(k)
    # 4. the yellow edge lines (paint), in the connector frame, over the stations that changed
    cp = proj / "data" / "connectors.local.json"
    conn = next((c for c in json.loads(cp.read_text(encoding="utf-8"))["connectors"] if c["name"] == a["island"]), None)
    paint = {}
    if conn is not None and stations:
        P = conn["points_xyz_m"]
        n = len(P)

        def frame(i):
            a_, b_ = P[max(0, i - 1)], P[min(n - 1, i + 1)]
            tx, tz = b_[0] - a_[0], b_[2] - a_[2]
            L = math.hypot(tx, tz) or 1.0
            return tx / L, tz / L, -tz / L, tx / L

        def faces(pts, iw, i):
            _tx, _tz, nx, nz = frame(i)
            c = (pts[i][0] - P[i][0]) * nx + (pts[i][2] - P[i][2]) * nz
            return c + iw[i] / 2.0, c - iw[i] / 2.0
        lo, hi = min(stations), max(stations)
        for name in ("YLINE", "MARKINGS"):
            ob = bpy.data.objects.get(name)
            if ob is None or ob.type != "MESH" or not ob.matrix_world.is_identity:
                continue
            cnt = 0
            for v in ob.data.vertices:
                x, z = v.co.x, v.co.y
                i = min(range(max(0, lo - 1), min(n, hi + 2)), key=lambda q: (P[q][0] - x) ** 2 + (P[q][2] - z) ** 2)
                if not lo <= i <= hi or math.hypot(P[i][0] - x, P[i][2] - z) > 20.0:
                    continue
                tx, tz, nx, nz = frame(i)
                lat = (x - P[i][0]) * nx + (z - P[i][2]) * nz
                (oL, oR), (nL, nR) = faces(old_pts, old_iw, i), faces(new_pts, new_iw, i)
                for old_line, d in ((oL + MEDIAN_EDGE_M, nL - oL), (oR - MEDIAN_EDGE_M, nR - oR)):
                    if abs(lat - old_line) <= PAINT_BAND_M and abs(d) > 1e-6:
                        v.co.x += nx * d
                        v.co.y += nz * d
                        cnt += 1
                        break
            paint[name] = cnt
    for ob in objs.values():
        ob.data.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    rep = {"island": a["island"], "blend_in": str(blend), "blend_out": str(out), "old_bands": a["old"],
           "island_vertices": n_all, "found_worst_mm": round(worst * 1000, 3), "moved": moved,
           "stations_moved": [min(stations), max(stations)] if stations else None, "largest_move_m": round(big, 3),
           "paint_vertices_moved": paint, "deck": "moved" if a["move_deck"] else "kept (v4's, under the slab)"}
    print("[reshape] " + json.dumps(rep))
    if a["report"]:
        Path(a["report"]).write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")


main()

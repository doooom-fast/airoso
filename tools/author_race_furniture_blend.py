"""Author the race-layout furniture into loop.blend — centre K-rail chain, kerb-line barriers,
race kerbs — as `1WALL_race_*` / `1KERB_race_*` mesh objects in a `RACE` collection (ledger 0047).

Runs INSIDE Blender, in the author stage AFTER author_signs_blend (+ verify_signs) and after
tools/barrier_bands.py has written data/barrier_bands.json, BEFORE the kn5 prep:

    blender --background --python-exit-code 1 --python tools/author_race_furniture_blend.py -- <project-dir>
        [--blend <loop.blend>] [--out-blend <file>] [--edge-mode road|walk] [--barrier-height 1.20]
        [--no-kerbs] [--collider] [--standin-bands]

Idempotent: every object whose upper-case name starts with 1WALL_RACE / 1KERB_RACE, and every
member of the RACE collection, is removed first (the author_lamps_blend LIGHTS pattern). Nothing
else in the scene is touched — the hand-edit layers stay. The geometry itself is pure Python in
tools/race_furniture.py; this file only (1) seats every ring on the BUILT deck, (2) remaps to
Blender with reversed winding (LAWS L6) and (3) writes the objects + data/race_authored.json for
tools/verify_race.py and tools/plot_race_furniture.py.

SEATING (measured on the 2026-10-09 loop.blend): a BVH over the MAINLINE rows of ROAD only (the
ribbon lays the mainline's 3-vertex rows first, connectors after — build_loop_blend.py:653/674), the
LOWEST sheet where the ribbon folds on itself (the inside edge of the seam corner v4496-v0 and the
Navajo/Jackson apex), a +-0.4 m probe when the ring centre falls in a fold's uncovered wedge, and
linear interpolation from the run's seated neighbours for the handful that still miss. Every one of
those is counted in race_authored.json; a run with no seated ring at all fails. Where ANOTHER deck
(a connector's) stands more than 0.15 m above the strip base the ring is listed under
`other_deck_above` — that is a junction defect (0033/0046 class) for its owner, not a seating choice.

SHADING (2026-10-11): every strip and kerb is smooth-shaded (Mesh.shade_smooth) with hard edges
(MeshEdge.use_edge_sharp) only where race_furniture.sharp_edges finds faces meeting at > 30 deg (the
jersey base, base/slope and top-lip creases, the end caps) plus the kerb outline — the flat-shaded
strips made the exporter emit one vertex per triangle corner (3.0 per triangle, a 35.6 MB race kn5).
The prep (build_kn5_loop.py) keeps it: its remove_doubles / face-up pass round-trip the sharp and smooth
flags through bmesh, it never double-sides a loop.blend mesh (DOUBLE_SIDE only touches merged
data/track_*.obj groups) and it only ever ADDS smooth shading (above 65,535 loops).

FOLDS (2026-10-11): at the five inside lips tighter than the strip's offset the plan TRIMS the strip and the
inside kerbs to the curb's own corner (race_furniture._trim_folds: one mitred corner ring at the offset curve's
self-intersection, or where its legs extended meet) — what barrier_bands.json declares as `edge_corners`;
race_authored.json records each object's fold_corners, an author-time inside-out count and `ring_frames`
(tangent + lateral scale per ring), from which verify_race I re-checks that no span is inside-out.

Default --out-blend is the input blend (saved in place, like every other author tool). The
hand-edit surface airoso/tracks/<track>/loop.blend is NEVER written by this tool (ship_sd.sh's
sync-back is the only writer); an --out-blend under airoso/tracks is refused.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO / "tools"))
import race_furniture as rf  # noqa: E402

RAY_UP_M = 15.0
RAY_DOWN_M = 4.0           # the lowest-sheet up-cast starts this far under the data height
RAY_LEN_M = 60.0
KERB_SINK_M = 0.01
PROBE_M = 0.4
OTHER_DECK_M = 0.15
INTERP_MAX_FRAC = 0.01     # more than 1 % interpolated rings = something is wrong with the deck


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = {"project": None, "blend": None, "out_blend": None, "edge_mode": None, "height": None,
           "kerbs": True, "collider": False, "standin": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--blend":
            out["blend"] = argv[i + 1]; i += 2
        elif a == "--out-blend":
            out["out_blend"] = argv[i + 1]; i += 2
        elif a == "--edge-mode":
            out["edge_mode"] = argv[i + 1]; i += 2
        elif a == "--barrier-height":
            out["height"] = float(argv[i + 1]); i += 2
        elif a == "--no-kerbs":
            out["kerbs"] = False; i += 1
        elif a == "--collider":
            out["collider"] = True; i += 1
        elif a == "--standin-bands":
            out["standin"] = True; i += 1
        elif out["project"] is None:
            out["project"] = a; i += 1
        else:
            raise SystemExit(f"[race] unknown argument {a}")
    if out["project"] is None:
        raise SystemExit(__doc__)
    return out


def _bvh(name, keep=None):
    """BVH over an object's faces, optionally only those `keep(face)` accepts"""
    ob = bpy.data.objects.get(name)
    if ob is None or ob.type != "MESH":
        return None
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    if keep is not None:
        bm.faces.ensure_lookup_table()
        doomed = [f for f in bm.faces if not keep(f)]
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def _cast(bvh, x, z_north, y0, up):
    loc, _n, _i, _d = bvh.ray_cast(Vector((x, z_north, y0)), Vector((0.0, 0.0, 1.0 if up else -1.0)), RAY_LEN_M)
    return None if loc is None else float(loc.z)


def _seat_lowest(bvh, x, z_north, y_hint):
    """the LOWEST deck sheet near the data height (folded ribbons: bury, never float)"""
    if bvh is None:
        return None
    y = _cast(bvh, x, z_north, y_hint - RAY_DOWN_M, up=True)
    if y is None:
        y = _cast(bvh, x, z_north, y_hint + RAY_UP_M, up=False)
    return y


def _seat_highest(bvh, x, z_north, y_hint):
    if bvh is None:
        return None
    return _cast(bvh, x, z_north, y_hint + RAY_UP_M, up=False)


def _collection(name="RACE"):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    return col


def _members(col):
    out = set(ob.name for ob in col.objects)
    for c in col.children:
        out |= _members(c)
    return out


def _remove_existing():
    col = bpy.data.collections.get("RACE")
    doomed = set(_members(col)) if col else set()
    doomed |= {ob.name for ob in bpy.data.objects if rf.is_race_name(ob.name)}
    n = 0
    for name in sorted(doomed):
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        me = ob.data if ob.type == "MESH" else None
        bpy.data.objects.remove(ob, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
        n += 1
    while bpy.data.orphans_purge(do_recursive=True):
        pass
    return n


def _mk(name, verts, faces, uvs, col, sharp=None):
    """the mesh object, SMOOTH-shaded with `sharp` (vertex-index pairs) as its only hard edges (Blender
    4.2: Mesh.shade_smooth + MeshEdge.use_edge_sharp; no auto-smooth). UVs are per VERTEX — one UV per
    position, no seam — so the exporter's weld (position + normal + UV + tangent) is blocked only where
    an edge is hard. `sharp=None` leaves the mesh flat (the collider sheets)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    if sharp is not None:
        me.shade_smooth()
        key = {(a, b) if a < b else (b, a) for a, b in sharp}
        flags = [tuple(sorted(e.vertices)) in key for e in me.edges]
        me.edges.foreach_set("use_edge_sharp", flags)
        n_smooth = sum(1 for p in me.polygons if p.use_smooth)
        n_sharp = sum(1 for e in me.edges if e.use_edge_sharp)
        if n_smooth != len(me.polygons) or n_sharp != len(key):
            raise SystemExit(f"[race] FATAL {name}: shading not applied ({n_smooth}/{len(me.polygons)} smooth faces, "
                             f"{n_sharp}/{len(key)} hard edges) — validate() changed the topology?")
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob, me


class Seater:
    """seats a list of ring/station records in place: rec['y'] = deck - sink; counts how"""

    def __init__(self, main_bvh, any_bvh, sink):
        self.main, self.any, self.sink = main_bvh, any_bvh, sink
        self.hit = self.near = self.interp = 0
        self.misses, self.devs, self.other = [], [], []

    def seat(self, name, recs, xz_of):
        pending = []
        for idx, r in enumerate(recs):
            x, z = xz_of(r)
            y = _seat_lowest(self.main, x, z, r["y_hint"])
            how = "hit"
            if y is None:
                lx, lz = rf.left_normal(r["tx"], r["tz"])
                for da, dl in ((PROBE_M, 0.0), (-PROBE_M, 0.0), (0.0, PROBE_M), (0.0, -PROBE_M)):
                    y = _seat_lowest(self.main, x + r["tx"] * da + lx * dl, z + r["tz"] * da + lz * dl, r["y_hint"])
                    if y is not None:
                        how = "near"
                        break
            if y is None:
                pending.append(idx)
                r["y"] = None
                continue
            if how == "hit":
                self.hit += 1
            else:
                self.near += 1
            self.devs.append((round(y - r["y_hint"], 3), name, r["k"]))
            top = _seat_highest(self.any, x, z, r["y_hint"])
            if top is not None and top - y > OTHER_DECK_M:
                self.other.append((round(top - y, 3), name, r["k"]))
            r["y"] = y - self.sink
        seated = [i for i in range(len(recs)) if recs[i]["y"] is not None]
        if pending and not seated:
            return False
        for idx in pending:
            lo = max((i for i in seated if i < idx), default=None)
            hi = min((i for i in seated if i > idx), default=None)
            if lo is None:
                recs[idx]["y"] = recs[hi]["y"]
            elif hi is None:
                recs[idx]["y"] = recs[lo]["y"]
            else:
                t = (idx - lo) / (hi - lo)
                recs[idx]["y"] = recs[lo]["y"] * (1 - t) + recs[hi]["y"] * t
            x, z = xz_of(recs[idx])
            self.misses.append((name, recs[idx]["k"], round(x, 1), round(z, 1), round(recs[idx]["y"], 2)))
            self.interp += 1
        return True


def main():
    t0 = time.time()
    a = _args()
    proj = Path(a["project"]).resolve()
    blend = Path(a["blend"]).resolve() if a["blend"] else proj / "loop.blend"
    out_blend = Path(a["out_blend"]).resolve() if a["out_blend"] else blend
    if (AIROSO / "tracks") in out_blend.parents:
        raise SystemExit(f"[race] refusing to write under airoso/tracks ({out_blend}) — ship_sd.sh syncs the hand-edit surface")
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    race_cfg = cfg.get("race", {}) or {}
    mode = a["edge_mode"] or race_cfg.get("edge_mode", "road")
    height = a["height"] or float(race_cfg.get("barrier_height_m", rf.BARRIER_H))
    data = proj / "data"
    pts, widths = rf.load_centerline(proj)
    m = rf.unique_count(pts)
    mb = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))
    island_w = mb["island_w_by_vertex"]

    bands = rf.load_bands(proj)
    standin = False
    if bands is None:
        if not a["standin"]:
            raise SystemExit("[race] no data/barrier_bands.json — run tools/barrier_bands.py first "
                             "(or --standin-bands for a dry run from the spec's vertex runs)")
        mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8")).get("mouths", [])
        spans = json.loads((data / "bridge.spans.auto.json").read_text(encoding="utf-8"))
        tmp = rf.standin_bands(pts, widths, island_w, mouths, spans, dict(race_cfg, edge_mode=mode))
        _, corners0 = rf.detect_kerb_corners(pts, widths, tmp)
        bands = rf.standin_bands(pts, widths, island_w, mouths, spans, dict(race_cfg, edge_mode=mode), corners0)
        (data / "barrier_bands.json").write_text(json.dumps(bands), encoding="utf-8")
        standin = True
        print(f"[race] WARNING: wrote a STAND-IN data/barrier_bands.json (chain {bands['params']['chain_length_m']} m)")
    probs = rf.check_bands(bands, pts, island_w)
    if probs:
        for p in probs:
            print(f"[race] bands FAIL: {p}")
        raise SystemExit(1)
    mode = (bands.get("params") or {}).get("edge_mode", mode)
    plans = rf.chain_plans(pts, widths, island_w, bands, height) + rf.edge_plans(pts, widths, bands, mode, height)
    corners, unmatched_kerbs = [], []
    if a["kerbs"]:
        rb, corners = rf.detect_kerb_corners(pts, widths, bands)
        unmatched_kerbs = rf.apply_declared_kerbs(rb, corners, bands)
        for d in unmatched_kerbs:
            print(f"[race] WARNING declared kerb apex v{d.get('apex')} {d.get('side')} {d.get('kind')} "
                  f"matches no detected corner — not authored")
        plans += rf.kerb_plans(rb, corners, bands, mode)

    bpy.ops.wm.open_mainfile(filepath=str(blend))
    road_name = "ROAD" if bpy.data.objects.get("ROAD") else "1ROAD_road"
    road = bpy.data.objects.get(road_name)
    if road is None:
        raise SystemExit("[race] no ROAD mesh to seat on")
    main_n = 3 * m
    if len(road.data.vertices) < main_n:
        raise SystemExit(f"[race] ROAD has {len(road.data.vertices)} verts < 3 x {m} mainline rows")
    for k in (0, m // 3, 2 * m // 3):   # the ribbon's centre vertex of row k is the centreline vertex
        c = road.data.vertices[3 * k + 1].co
        if abs(c.x - pts[k][0]) > 0.05 or abs(c.y - pts[k][2]) > 0.05:
            raise SystemExit(f"[race] ROAD row {k} centre {tuple(round(v, 2) for v in c)} is not centreline v{k} — ribbon layout changed")
    road_main = _bvh(road_name, keep=lambda f: all(v.index < main_n for v in f.verts))
    road_any = _bvh(road_name)
    curb_name = "CURB" if bpy.data.objects.get("CURB") else "1KERB_sidewalk"
    curb_bvh = _bvh(curb_name) if mode == "walk" else None
    removed = _remove_existing()
    col = _collection("RACE")

    strips = Seater(road_main, road_any, rf.BURY_M)
    walk = Seater(curb_bvh, curb_bvh, rf.BURY_M) if mode == "walk" else strips
    kerbs = Seater(road_main, road_any, KERB_SINK_M)
    objects, centres, frames = [], {}, {}
    tot = {"chain_len": 0.0, "chain_rings": 0, "edge_len": 0.0, "edge_rings": 0, "kerb_len": 0.0,
           "kerb_stations": 0, "positions": 0, "triangles": 0, "render_verts_est": 0, "densified": 0,
           "spacing_max": 0.0, "chord_max": 0.0}
    failed_runs = []
    for plan in plans:
        name = rf.object_name(plan)
        if plan["kind"] in ("chain", "edge"):
            seater = walk if plan["kind"] == "edge" else strips

            def xz(r):
                lx, lz = rf.left_normal(r["tx"], r["tz"])
                return r["cx"] + lx * r["lat"], r["cz"] + lz * r["lat"]
            h0, n0, i0 = seater.hit, seater.near, seater.interp
            if not seater.seat(name, plan["rings"], xz):
                failed_runs.append(name)
                continue
            verts, faces, uvs = rf.strip_mesh(plan["rings"], plan["cap_start"], plan["cap_end"], rf.MODULE_PITCH_M)
            sharp = rf.sharp_edges(verts, faces)
            length = plan["rings"][-1]["arc"] - plan["rings"][0]["arc"]
            key = "chain" if plan["kind"] == "chain" else "edge"
            tot[f"{key}_len"] += length
            tot[f"{key}_rings"] += len(plan["rings"])
            sp, ch, folds = rf.ring_stats(plan["rings"])
            tot["densified"] += plan.get("densified", 0)
            tot["spacing_max"] = max(tot["spacing_max"], sp)
            tot["chord_max"] = max(tot["chord_max"], ch)
            rec = {"name": name, "kind": plan["kind"], "side": plan["side"], "street": plan["street"],
                   "run": plan["run"], "part": plan["part"], "rings": len(plan["rings"]), "length_m": round(length, 1),
                   "segments_4m": round(length / rf.MODULE_PITCH_M, 1),
                   "seated": {"hit": seater.hit - h0, "near": seater.near - n0, "interpolated": seater.interp - i0},
                   "seat_gap_max_m": 0.0, "ends": [plan["start_kind"], plan["end_kind"]],
                   "caps": [plan["cap_start"], plan["cap_end"]], "fold_skipped_run": plan.get("fold_skipped", 0),
                   "densified": plan.get("densified", 0), "spacing_max_m": round(sp, 3), "chord_max_m": round(ch, 4),
                   "fold_spans": folds, "fold_corners": plan.get("fold_corners", []),
                   "inside_out_spans": len(rf.inside_out_spans(plan["rings"], rf._strip_xz, rf.BARRIER_HALF_W))}
            centres[name] = [[round(x, 2), round(r["y"], 2), round(z, 2)] for r in plan["rings"] for (x, z) in (xz(r),)]
            # the ring frames verify_race I rebuilds the profile columns from (tangent + lateral scale)
            frames[name] = [[round(r["tx"], 5), round(r["tz"], 5), round(r.get("ls", 1.0), 4)] for r in plan["rings"]]
        else:
            sgn = 1.0 if plan["side"] == "L" else -1.0

            def xz(s, sgn=sgn):
                lx, lz = rf.left_normal(s["tx"], s["tz"])
                mid = s["lip"] + sgn * rf.KERB_W / 2.0
                return s["cx"] + lx * mid, s["cz"] + lz * mid
            h0, n0, i0 = kerbs.hit, kerbs.near, kerbs.interp
            if not kerbs.seat(name, plan["stations"], xz):
                failed_runs.append(name)
                continue
            verts, faces, uvs = rf.kerb_mesh(plan["stations"], sgn, rf.KERB_TILE_M)
            sharp = sorted(set(rf.sharp_edges(verts, faces)) | set(rf.kerb_outline_edges(len(plan["stations"]))))
            tot["kerb_len"] += plan["length_m"]
            tot["kerb_stations"] += len(plan["stations"])
            rec = {"name": name, "kind": "kerb", "side": plan["side"], "sub": plan["sub"], "apex": plan["apex"],
                   "run": plan["run"], "stations": len(plan["stations"]), "length_m": plan["length_m"],
                   "fold_skipped": plan.get("fold_skipped", 0), "fold_corners": plan.get("fold_corners", []),
                   "inside_out_spans": len(rf.inside_out_spans(plan["stations"], lambda s_, g=sgn: rf.kerb_mid_xz(s_, g),
                                                               rf.KERB_W / 2.0)),
                   "seated": {"hit": kerbs.hit - h0, "near": kerbs.near - n0, "interpolated": kerbs.interp - i0},
                   "seat_gap_max_m": 0.0}
            centres[name] = [[round(x, 2), round(s["y"], 2), round(z, 2)] for s in plan["stations"] for (x, z) in (xz(s),)]
            frames[name] = [[round(s["tx"], 5), round(s["tz"], 5), round(s.get("ls", 1.0), 4)] for s in plan["stations"]]
        bverts, bfaces = rf.to_blender(verts, faces)
        if len(bverts) >= 60000:
            raise SystemExit(f"[race] FATAL {name}: {len(bverts)} positions (>= 60,000) — lower MAX_RINGS_PER_OBJECT")
        ob, me = _mk(name, bverts, bfaces, uvs, col, sharp=sharp)     # the reflection keeps every dihedral
        rv = rf.render_vertex_count(len(verts), faces, sharp)
        tris = rf.triangle_count(faces)
        rec.update({"positions": len(me.vertices), "faces": len(me.polygons), "loops": len(me.loops),
                    "smooth": True, "sharp_edges": len(sharp), "triangles": tris, "render_verts_est": rv})
        if len(me.loops) * 3 // 2 > 65535:     # worst case if the shading were ever lost: 2 flat tris x 3 per quad
            print(f"[race] WARNING {name}: {len(me.loops)} loops — flat-shaded render verts may exceed 65,535")
        tot["positions"] += len(me.vertices)
        tot["triangles"] += tris
        tot["render_verts_est"] += rv
        objects.append(rec)

    # optional invisible collider sheets (Q11 — OFF by default; needs the 1WALL_RACECOL pbr/ALPHATEST row first)
    if a["collider"]:
        part = 0
        for plan in [p for p in plans if p["kind"] in ("chain", "edge") and p["rings"][0].get("y") is not None]:
            verts, faces = [], []
            for r in plan["rings"]:
                lx, lz = rf.left_normal(r["tx"], r["tz"])
                x, z = r["cx"] + lx * r["lat"], r["cz"] + lz * r["lat"]
                base = r["y"] + rf.BURY_M
                verts += [(x, base - rf.COLLIDER_BELOW_M, z), (x, base + rf.COLLIDER_ABOVE_M, z)]
            for q in range(len(plan["rings"]) - 1):
                i = 2 * q
                faces.append((i, i + 1, i + 3, i + 2))
                faces.append((i + 2, i + 3, i + 1, i))      # both sides: collides from either carriageway
            bverts, bfaces = rf.to_blender(verts, faces)
            name = rf.object_name({"kind": "collider", "part": part})
            ob, me = _mk(name, bverts, bfaces, [(0.0, 0.0)] * len(bverts), col)
            objects.append({"name": name, "kind": "collider", "positions": len(me.vertices), "faces": len(me.polygons)})
            part += 1
        print(f"[race] {part} invisible collider sheets authored (1WALL_racecol_*) — pbr row '1WALL_RACECOL' + ALPHATEST owed")

    # grid / pit exclusions: no spawn of a race layout may stand in a strip
    clearance, hard = {}, []
    for lo in cfg.get("layouts", []):
        if not lo.get("race_furniture"):
            continue
        dp = data / f"dummies_{lo['id']}.json"
        if not dp.exists():
            clearance[lo["id"]] = {"unchecked": "no dummies file (tools/layout_dummies.py not run)"}
            print(f"[race] spawn unchecked {lo['id']}: no {dp.name}")
            continue
        d = json.loads(dp.read_text(encoding="utf-8"))
        # HARD below rf.SPAWN_MARGIN_M (0.30 m) since 2026-10-11 — was a note; the per-slot table rides
        # along so verify_race / the ledger can quote every slot's clearance
        h, notes = rf.spawn_clearance(pts, widths, bands, rf.dummies_positions(d), mode)
        slots = rf.spawn_clearance_table(pts, widths, bands, rf.dummies_positions(d), mode)
        clearance[lo["id"]] = {"hard": h, "notes": notes, "synthesised": bool(d.get("_synthesised")),
                               "margin_m": rf.SPAWN_MARGIN_M, "slots": slots,
                               "min_clear_m": min([s["clear_edge_m"] for s in slots] +
                                                  [s["clear_centre_m"] for s in slots if s["clear_centre_m"] is not None],
                                                  default=None)}
        hard += [f"{lo['id']}: {p}" for p in h]
        for p in h:
            print(f"[race] spawn FAIL {lo['id']}: {p}")
        for p in notes:
            print(f"[race] spawn note {lo['id']}: {p}")

    if out_blend != blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    else:
        bpy.ops.wm.save_mainfile(filepath=str(blend))

    all_devs = sorted(strips.devs + kerbs.devs + (walk.devs if walk is not strips else []), key=lambda d: -abs(d[0]))
    all_other = sorted(strips.other + kerbs.other, key=lambda d: -d[0])
    n_rings = tot["chain_rings"] + tot["edge_rings"] + tot["kerb_stations"]
    n_interp = strips.interp + kerbs.interp + (walk.interp if walk is not strips else 0)
    report = {
        "_doc": "written by tools/author_race_furniture_blend.py — per-object counts and seating for "
                "tools/verify_race.py; ring_centres are the authored strip centres (engine frame x=E, y=up, z=N) "
                "for tools/plot_race_furniture.py. seated.hit = BVH deck under the ring centre, near = within "
                "0.4 m (a ribbon fold's uncovered wedge), interpolated = from the run's seated neighbours. "
                "seat_gap_max_m is 0 by construction (base = deck - 0.05); the honest numbers are the seated counts, "
                "deck_vs_data (built deck minus data height + 0.10) and other_deck_above (another ROAD sheet above "
                "the strip base — a junction defect for its owner).",
        "blend": str(out_blend), "standin_bands": standin, "edge_mode": mode, "barrier_height_m": height,
        "removed_existing": removed, "collection": "RACE", "race_prefixes": list(rf.RACE_PREFIXES),
        "max_rings_per_object": rf.MAX_RINGS_PER_OBJECT,
        "shading": {"smooth": True, "sharp_deg": rf.SHARP_DEG, "kerb_outline_hard": True,
                    "triangles": tot["triangles"], "render_verts_est": tot["render_verts_est"],
                    "verts_per_triangle_est": round(tot["render_verts_est"] / max(1, tot["triangles"]), 3)},
        "density": {"ring_spacing_max_target_m": rf.RING_SPACING_MAX_M, "chord_max_target_m": rf.CHORD_MAX_M,
                    "rings_inserted": tot["densified"], "ring_spacing_max_m": round(tot["spacing_max"], 3),
                    "chord_max_m": round(tot["chord_max"], 4)},
        "totals": {"objects": len(objects), "positions": tot["positions"], "rings": n_rings,
                   "chain_length_m": round(tot["chain_len"], 1), "chain_rings": tot["chain_rings"],
                   "chain_segments_4m": round(tot["chain_len"] / rf.MODULE_PITCH_M),
                   "chain_objects": sum(1 for o in objects if o["kind"] == "chain"),
                   "edge_length_m": round(tot["edge_len"], 1), "edge_rings": tot["edge_rings"],
                   "edge_segments_4m": round(tot["edge_len"] / rf.MODULE_PITCH_M),
                   "edge_objects": sum(1 for o in objects if o["kind"] == "edge"),
                   "kerb_length_m": round(tot["kerb_len"], 1), "kerb_stations": tot["kerb_stations"],
                   "kerb_objects": sum(1 for o in objects if o["kind"] == "kerb"),
                   "seated_hit": strips.hit + kerbs.hit + (walk.hit if walk is not strips else 0),
                   "seated_near": strips.near + kerbs.near + (walk.near if walk is not strips else 0),
                   "seated_interpolated": n_interp,
                   "deck_vs_data_max_m": round(abs(all_devs[0][0]), 3) if all_devs else 0.0,
                   "other_deck_above_rings": len(all_other),
                   "other_deck_above_max_m": all_other[0][0] if all_other else 0.0},
        "corners": [{k: v for k, v in c.items() if k != "kerbs"} | {"kerbs": [{"side": kb["side"], "kind": kb["kind"],
                     "i": kb["i"], "j": kb["j"], "declared": bool(kb.get("declared"))} for kb in c["kerbs"]]} for c in corners],
        "kerbs_declared_unmatched": unmatched_kerbs,
        "street_table": rf.street_table(bands),
        "spawn_clearance": clearance,
        "failed_runs": failed_runs,
        "deck_interpolated": strips.misses + kerbs.misses,
        "deck_vs_data_worst": all_devs[:12],
        "other_deck_above": all_other[:24],
        "objects": objects,
        "ring_centres": centres,
        "ring_frames": frames,
        "seconds": round(time.time() - t0, 1),
    }
    (data / "race_authored.json").write_text(json.dumps(report), encoding="utf-8")
    for mname, k, mx, mz, my in report["deck_interpolated"][:20]:
        print(f"[race] interpolated {mname} v{k} at ({mx}, {mz}) -> y {my}")
    for dv, dname, k in all_devs[:5]:
        print(f"[race] deck vs data {dv:+.3f} m at {dname} v{k}")
    for dv, dname, k in all_other[:8]:
        print(f"[race] other deck {dv:+.3f} m above the strip base at {dname} v{k} (junction defect, not a seating choice)")
    t = report["totals"]
    print(f"[race] chain {t['chain_length_m']} m / {t['chain_rings']} rings / {t['chain_segments_4m']} x 4.04 m in "
          f"{t['chain_objects']} objects; edge {t['edge_length_m']} m / {t['edge_rings']} rings in {t['edge_objects']} objects; "
          f"kerbs {t['kerb_length_m']} m / {t['kerb_stations']} stations in {t['kerb_objects']} objects; "
          f"{t['positions']} positions in {t['objects']} objects (RACE collection); seated {t['seated_hit']} hit / "
          f"{t['seated_near']} near / {t['seated_interpolated']} interpolated; deck vs data max {t['deck_vs_data_max_m']} m; "
          f"other deck above {t['other_deck_above_rings']} rings (max {t['other_deck_above_max_m']} m); "
          f"removed {removed} old; saved {out_blend.name} ({report['seconds']} s)")
    n_io = sum(int(o.get("inside_out_spans", 0) or 0) for o in objects)
    for o in objects:
        for c in o.get("fold_corners", []) or []:
            print(f"[race] trimmed fold {o['name']}: {c['kind']} corner at ({c['xz'][0]:.2f}, {c['xz'][1]:.2f}) turn "
                  f"{c['turn_deg']:+.1f} deg, mitre {c['mitre']}, {c.get('n_removed', len(c['removed']))} rings/stations removed")
    print(f"[race] inside-out spans (author-time column test): {n_io}")
    sh, dn = report["shading"], report["density"]
    print(f"[race] shading: smooth, hard edges > {sh['sharp_deg']:.0f} deg + kerb outline; {sh['triangles']} triangles -> "
          f"~{sh['render_verts_est']} render verts ({sh['verts_per_triangle_est']} per triangle; flat-shaded was 3.0)")
    print(f"[race] density: {dn['rings_inserted']} rings inserted; ring spacing max {dn['ring_spacing_max_m']} m "
          f"(target {dn['ring_spacing_max_target_m']}), chord vs the declared curve max {dn['chord_max_m']} m "
          f"(target {dn['chord_max_target_m']})")
    if failed_runs:
        print(f"[race] FAIL: runs with no deck under any ring: {failed_runs}")
        raise SystemExit(1)
    if n_interp > INTERP_MAX_FRAC * n_rings:
        print(f"[race] FAIL: {n_interp} of {n_rings} rings interpolated (> {INTERP_MAX_FRAC:.0%})")
        raise SystemExit(1)
    if hard:
        raise SystemExit(1)


main()

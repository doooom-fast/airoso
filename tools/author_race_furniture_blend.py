"""Author the race-layout furniture into loop.blend (ledgers 0047 + 0049): the COMMON kerb-line strips and race kerbs
in collection `RACE`, and each race layout's CLOSURE in its own collection `RACE_CLOSE_<TOKEN>` (RACE_CLOSE_CW /
RACE_CLOSE_ACW), as `1WALL_race_edge_*` / `1KERB_race_*` / `1WALL_race_close_<token>_*` mesh objects.

Runs INSIDE Blender, in the author stage AFTER author_signs_blend (+ verify_signs) and after
tools/barrier_bands.py has written data/barrier_bands.json (version 2: `corridors.<layout id>`), BEFORE the kn5 prep:

    blender --background --python-exit-code 1 --python tools/author_race_furniture_blend.py -- <project-dir>
        [--blend <loop.blend>] [--out-blend <file>] [--edge-mode road|walk] [--barrier-height 1.20] [--no-kerbs]

What is built (pure geometry in tools/race_furniture.py):
  * both curb strips as ONE CLOSED LOOP per side — across all three bridge spans (ledger 0049 C1), straight across
    every mouth, trimmed to the curb's own corner at the five inside lips, cut at street boundaries on shared
    rings: no free end, no cap anywhere;
  * per race layout, its closure along corridors.<id>.closure_y_by_vertex: the far boundary of its Alvarado-wide
    lane, along the island's race-side curb nose tip to nose tip, both ends PINNED full height on the far curb
    strip at a box / whole-street edge (the cap buried in that strip);
  * the race kerbs at the five corners, in and out (10), clipped where EITHER layout's closure footprint comes
    within 0.05 m (race_furniture.clip_kerbs — the stations removed are recorded per kerb).
The owner token rides in each closure's NAME (the prep re-links every object to the scene root, so the collection
is for Kevin's eye and toggling; the export split routes on the name): RACE -> <slug>_race.kn5, RACE_CLOSE_CW ->
<slug>_closure_race_cw.kn5, RACE_CLOSE_ACW -> <slug>_closure_race_acw.kn5. Every name keeps the 1WALL_RACE /
1KERB_RACE prefix, so scripts/ac/pbr.py binds Kevin's K-rail / kerb textures with no new row.

Idempotent: every object whose upper-case name starts with 1WALL_RACE / 1KERB_RACE, every member of `RACE` and of
any `RACE_CLOSE_*` collection is removed, and those collections with it (the author_lamps_blend LIGHTS pattern).
Nothing else in the scene is touched — the hand-edit layers stay. A ledger-0047 (v1) declaration — the retired
centre chain, no corridors — is refused (race_furniture.check_bands).

SEATING (unchanged, measured on the 2026-10-09 loop.blend): a BVH over the MAINLINE rows of ROAD only (the
ribbon lays the mainline's 3-vertex rows first, connectors after — build_loop_blend.py:653/674), the
LOWEST sheet where the ribbon folds on itself, a +-0.4 m probe when the ring centre falls in a fold's uncovered
wedge, and linear interpolation from the run's seated neighbours for the handful that still miss. Every one of
those is counted in race_authored.json (and, since 0049, separately for the rings inside the declared bridge
spans: `bridge_seating` — verify_race L fails any interpolated ring there); a run with no seated ring at all
fails. Where ANOTHER deck (a connector's) stands more than 0.15 m above the strip base the ring is listed under
`other_deck_above` — a junction defect (0033/0046 class) for its owner, not a seating choice.

SHADING (2026-10-11): every strip and kerb is smooth-shaded (Mesh.shade_smooth) with hard edges
(MeshEdge.use_edge_sharp) only where race_furniture.sharp_edges finds faces meeting at > 30 deg plus the kerb
outline — the flat-shaded strips made the exporter emit one vertex per triangle corner (a 35.6 MB race kn5).

race_authored.json carries, per object: owner (the closure token, None for the common furniture), kind
(edge | close | kerb), collection, run, ends [{kind, vertex, joins, gap_m, h, ls}] (a closure's true ends: kind
`pin`, joins edge_L / edge_R, gap_m = the end ring's centre to the authored far strip's centre polyline), the ring
centres / frames verify_race and plot_race_furniture read, and per layout a census.

Default --out-blend is the input blend (saved in place, like every other author tool). The
hand-edit surface airoso/tracks/<track>/loop.blend is NEVER written by this tool (ship_sd.sh's
sync-back is the only writer); an --out-blend under airoso/tracks is refused.
"""
from __future__ import annotations

import json
import math
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
    out = {"project": None, "blend": None, "out_blend": None, "edge_mode": None, "height": None, "kerbs": True}
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
        elif a in ("--collider", "--standin-bands"):
            raise SystemExit(f"[race] {a} is retired (ledger 0049): the collider sheet (Q11) is not built for the "
                             f"per-direction closures, and the only declaration is tools/barrier_bands.py's v2 file")
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


def _collection(name):
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


def _race_collections():
    return [c for c in bpy.data.collections
            if c.name == rf.COMMON_COLLECTION or c.name.startswith(rf.COMMON_COLLECTION + "_CLOSE_")]


def _remove_existing():
    """every RACE-named object, every member of RACE / RACE_CLOSE_*, then those collections themselves"""
    cols = _race_collections()
    doomed = set()
    for col in cols:
        doomed |= _members(col)
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
    for col in _race_collections():
        bpy.data.collections.remove(col)
    while bpy.data.orphans_purge(do_recursive=True):
        pass
    return n


def _mk(name, verts, faces, uvs, col, sharp=None):
    """the mesh object, SMOOTH-shaded with `sharp` (vertex-index pairs) as its only hard edges (Blender
    4.2: Mesh.shade_smooth + MeshEdge.use_edge_sharp; no auto-smooth). UVs are per VERTEX — one UV per
    position, no seam — so the exporter's weld (position + normal + UV + tangent) is blocked only where
    an edge is hard."""
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
    """seats a list of ring/station records in place: rec['y'] = deck - sink and rec['seat'] = hit | near | interp"""

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
            r["seat"] = how
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
            recs[idx]["seat"] = "interp"
            x, z = xz_of(recs[idx])
            self.misses.append((name, recs[idx]["k"], round(x, 1), round(z, 1), round(recs[idx]["y"], 2)))
            self.interp += 1
        return True


def _poly_dist(p, polys):
    """xz distance from p to the nearest segment of any polyline in polys"""
    best = float("inf")
    for cs in polys:
        for a, b in zip(cs, cs[1:]):
            best = min(best, rf.seg_dist(p, a, b))
    return best


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
    st = rf.stations(pts)

    bands = rf.load_bands(proj)
    if bands is None:
        raise SystemExit("[race] no data/barrier_bands.json — run tools/barrier_bands.py first")
    probs = rf.check_bands(bands, pts)
    if probs:
        for p in probs:
            print(f"[race] bands FAIL: {p}")
        raise SystemExit(1)
    mode = (bands.get("params") or {}).get("edge_mode", mode)
    race_ids = [str(lo["id"]) for lo in cfg.get("layouts", []) if lo.get("race_furniture")]
    declared_ids = sorted(rf.corridors(bands))
    if sorted(race_ids) != declared_ids:
        raise SystemExit(f"[race] race layouts in track.config.json {sorted(race_ids)} != corridors declared in "
                         f"barrier_bands.json {declared_ids} — re-run tools/barrier_bands.py")
    tokens = {lid: rf.closure_token(bands, lid) for lid in race_ids}
    for lo in cfg.get("layouts", []):
        ct = lo.get("closure_token")
        if lo.get("race_furniture") and ct and str(ct).lower() != tokens[str(lo["id"])]:
            raise SystemExit(f"[race] layout {lo['id']}: closure_token {ct!r} in the config != {tokens[str(lo['id'])]!r} "
                             f"declared — re-run tools/barrier_bands.py")

    edge = rf.edge_plans(pts, widths, bands, mode, height)
    closures = {lid: rf.closure_plans(pts, widths, bands, lid, height) for lid in race_ids}
    corners, unmatched_kerbs, kerb = [], [], []
    if a["kerbs"]:
        rb, corners = rf.detect_kerb_corners(pts, widths, bands)
        unmatched_kerbs = rf.apply_declared_kerbs(rb, corners, bands)
        for d in unmatched_kerbs:
            print(f"[race] WARNING declared kerb apex v{d.get('apex')} {d.get('side')} {d.get('kind')} "
                  f"matches no detected corner — not authored")
        kerb = rf.clip_kerbs(rf.kerb_plans(rb, corners, bands, mode), [p for lid in race_ids for p in closures[lid]])
    plans = edge + kerb + [p for lid in race_ids for p in closures[lid]]

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
    col_common = _collection(rf.COMMON_COLLECTION)
    col_close = {lid: _collection(rf.closure_collection(tokens[lid])) for lid in race_ids}

    strips = Seater(road_main, road_any, rf.BURY_M)
    walk = Seater(curb_bvh, curb_bvh, rf.BURY_M) if mode == "walk" else strips
    kerbs = Seater(road_main, road_any, KERB_SINK_M)
    objects, centres, frames = [], {}, {}
    tot = {"edge_len": 0.0, "edge_cl": 0.0, "edge_rings": 0, "kerb_len": 0.0, "kerb_stations": 0, "positions": 0,
           "triangles": 0, "render_verts_est": 0, "densified": 0, "spacing_max": 0.0, "chord_max": 0.0}
    per_layout = {lid: {"token": tokens[lid], "collection": col_close[lid].name, "objects": 0, "rings": 0,
                        "length_m": 0.0, "centreline_m": 0.0, "positions": 0, "triangles": 0, "render_verts_est": 0}
                  for lid in race_ids}
    spans = [tuple(map(float, s)) for s in (bands.get("bridge_spans_m") or [])]
    bridge = {"spans_m": [list(s) for s in spans], "hit": 0, "near": 0, "interpolated": 0,
              "by_span": [{"span_m": list(s), "hit": 0, "near": 0, "interpolated": 0} for s in spans], "by_object": {}}
    plan_of = {}
    failed_runs = []
    for plan in plans:
        name = rf.object_name(plan)
        kind = plan["kind"]
        owner = plan.get("token") if kind == "close" else None
        col = col_close[plan["layout"]] if kind == "close" else col_common
        if kind in ("edge", "close"):
            seater = walk if kind == "edge" else strips

            def xz(r):
                return rf._strip_xz(r)
            h0, n0, i0 = seater.hit, seater.near, seater.interp
            if not seater.seat(name, plan["rings"], xz):
                failed_runs.append(name)
                continue
            verts, faces, uvs = rf.strip_mesh(plan["rings"], plan["cap_start"], plan["cap_end"], rf.MODULE_PITCH_M)
            sharp = rf.sharp_edges(verts, faces)
            cl = plan["rings"][-1]["arc"] - plan["rings"][0]["arc"]
            length = rf.strip_length(plan["rings"])
            sp, ch, folds = rf.ring_stats(plan["rings"])
            tot["densified"] += plan.get("densified", 0)
            tot["spacing_max"] = max(tot["spacing_max"], sp)
            tot["chord_max"] = max(tot["chord_max"], ch)
            if kind == "edge":
                tot["edge_len"] += length
                tot["edge_cl"] += cl
                tot["edge_rings"] += len(plan["rings"])
            else:
                L = per_layout[plan["layout"]]
                L["length_m"] += length
                L["centreline_m"] += cl
                L["rings"] += len(plan["rings"])
            # rings seated inside the declared bridge spans (C1: the strips run over every deck; verify_race L)
            bo = {"hit": 0, "near": 0, "interpolated": 0}
            for r in plan["rings"]:
                for si, (s0, s1) in enumerate(spans):
                    if s0 <= r["s"] <= s1:
                        key = {"hit": "hit", "near": "near", "interp": "interpolated"}[r.get("seat", "hit")]
                        bridge[key] += 1
                        bridge["by_span"][si][key] += 1
                        bo[key] += 1
            if any(bo.values()):
                bridge["by_object"][name] = bo
            rec = {"name": name, "kind": kind, "owner": owner, "layout": plan.get("layout"), "collection": col.name,
                   "side": plan["side"], "street": plan["street"], "run": list(plan["run"]), "part": plan["part"],
                   "rings": len(plan["rings"]), "length_m": round(length, 1), "centreline_m": round(cl, 1),
                   "segments_4m": round(length / rf.MODULE_PITCH_M, 1),
                   "seated": {"hit": seater.hit - h0, "near": seater.near - n0, "interpolated": seater.interp - i0},
                   "seat_gap_max_m": 0.0, "end_kinds": [plan["start_kind"], plan["end_kind"]],
                   "caps": [plan["cap_start"], plan["cap_end"]], "closed_loop": bool(plan.get("closed_loop")),
                   "fold_skipped_run": plan.get("fold_skipped", 0),
                   "densified": plan.get("densified", 0), "spacing_max_m": round(sp, 3), "chord_max_m": round(ch, 4),
                   "fold_spans": folds, "fold_corners": plan.get("fold_corners", []),
                   "inside_out_spans": len(rf.inside_out_spans(plan["rings"], rf._strip_xz, rf.BARRIER_HALF_W))}
            centres[name] = [[round(x, 2), round(r["y"], 2), round(z, 2)] for r in plan["rings"] for (x, z) in (xz(r),)]
            # the ring frames verify_race I rebuilds the profile columns from (tangent + lateral scale)
            frames[name] = [[round(r["tx"], 5), round(r["tz"], 5), round(r.get("ls", 1.0), 4)] for r in plan["rings"]]
        else:
            sgn = 1.0 if plan["side"] == "L" else -1.0

            def xz(s, sgn=sgn):
                return rf.kerb_mid_xz(s, sgn)
            h0, n0, i0 = kerbs.hit, kerbs.near, kerbs.interp
            if not kerbs.seat(name, plan["stations"], xz):
                failed_runs.append(name)
                continue
            verts, faces, uvs = rf.kerb_mesh(plan["stations"], sgn, rf.KERB_TILE_M)
            sharp = sorted(set(rf.sharp_edges(verts, faces)) | set(rf.kerb_outline_edges(len(plan["stations"]))))
            klen = sum(math.dist(xz(p), xz(q)) for p, q in zip(plan["stations"], plan["stations"][1:]))
            tot["kerb_len"] += klen
            tot["kerb_stations"] += len(plan["stations"])
            rec = {"name": name, "kind": "kerb", "owner": None, "layout": None, "collection": col.name,
                   "side": plan["side"], "sub": plan["sub"], "apex": plan["apex"],
                   "run": plan["run"], "built_run": [plan["stations"][0]["k"], plan["stations"][-1]["k"]],
                   "stations": len(plan["stations"]), "length_m": round(klen, 1), "declared_length_m": plan["length_m"],
                   "clip": plan.get("clip"), "declared": bool(plan.get("declared")),
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
        if kind == "close":
            L = per_layout[plan["layout"]]
            L["objects"] += 1
            L["positions"] += len(me.vertices)
            L["triangles"] += tris
            L["render_verts_est"] += rv
        plan_of[name] = plan
        objects.append(rec)

    # ends: every strip end is a JOIN (the neighbour's ring) or a closure PIN (buried in the far curb strip) —
    # measured on the SEATED ring centres; verify_race J re-measures from ring_centres
    strip_recs = [o for o in objects if o["kind"] in ("edge", "close")]
    edge_by_side = {s: [centres[o["name"]] for o in strip_recs if o["kind"] == "edge" and o["side"] == s] for s in ("L", "R")}

    def xz2(c):
        return (c[0], c[2])
    for o in strip_recs:
        plan = plan_of[o["name"]]
        cs = centres[o["name"]]
        ends = []
        for idx, (cap, kind_) in enumerate(zip(o["caps"], o["end_kinds"])):
            ring = plan["rings"][0 if idx == 0 else -1]
            c = cs[0 if idx == 0 else -1]
            e = {"vertex": ring["k"], "h": round(ring["h"], 4), "ls": round(ring.get("ls", 1.0), 4)}
            if o["kind"] == "close" and cap:
                pin = plan["pins"][idx]
                far = pin["joins"]
                e.update(kind="pin", vertex=pin["vertex"], y=pin["y"], joins=far,
                         gap_m=round(_poly_dist(xz2(c), [[xz2(q) for q in p] for p in edge_by_side[far[-1]]]), 3))
            elif cap:
                e.update(kind="free", joins=None, gap_m=None)
            else:
                best = None
                for q in strip_recs:
                    if q is o or q["kind"] != o["kind"] or q["side"] != o["side"] or q.get("owner") != o.get("owner"):
                        continue
                    qc = centres[q["name"]][-1 if idx == 0 else 0]
                    d = math.dist(xz2(c), xz2(qc))
                    if best is None or d < best[0]:
                        best = (d, q["name"])
                e.update(kind="join", joins=best[1] if best else None, gap_m=round(best[0], 3) if best else None)
            ends.append(e)
        o["ends"] = ends

    # grid / pit exclusions: no spawn of a race layout may stand in a strip, or outside its own lane
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
        h, notes = rf.spawn_clearance(pts, widths, bands, rf.dummies_positions(d), mode, layout_id=lo["id"])
        slots = rf.spawn_clearance_table(pts, widths, bands, rf.dummies_positions(d), mode, layout_id=lo["id"])
        clearance[lo["id"]] = {"hard": h, "notes": notes, "synthesised": bool(d.get("_synthesised")),
                               "margin_m": rf.SPAWN_MARGIN_M, "slots": slots,
                               "min_clear_m": min([s["clear_edge_m"] for s in slots] +
                                                  [s["clear_lane_m"] for s in slots if s["clear_lane_m"] is not None],
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
    strip_rings = tot["edge_rings"] + sum(L["rings"] for L in per_layout.values())
    n_rings = strip_rings + tot["kerb_stations"]
    n_interp = strips.interp + kerbs.interp + (walk.interp if walk is not strips else 0)
    for L in per_layout.values():
        L["length_m"], L["centreline_m"] = round(L["length_m"], 1), round(L["centreline_m"], 1)
        L["segments_4m"] = round(L["length_m"] / rf.MODULE_PITCH_M)
    report = {
        "_doc": "written by tools/author_race_furniture_blend.py (ledger 0049) — per-object counts and seating for "
                "tools/verify_race.py; ring_centres are the authored strip / kerb centres (engine frame x=E, y=up, z=N) "
                "for tools/plot_race_furniture.py. owner = the closure token (None = common: curb strips + kerbs). "
                "seated.hit = BVH deck under the ring centre, near = within 0.4 m (a ribbon fold's uncovered wedge), "
                "interpolated = from the run's seated neighbours; bridge_seating counts the rings inside the declared "
                "bridge spans the same way. ends: kind join (the neighbouring object's ring, gap_m apart) or pin (a "
                "closure end: gap_m = its centre to the authored far curb strip's centre polyline, h / ls its profile). "
                "length_m = the strip's own plan length, centreline_m the centreline distance it spans.",
        "blend": str(out_blend), "standin_bands": bool(bands.get("_standin")), "declaration_version": bands.get("version"),
        "edge_mode": mode, "barrier_height_m": height,
        "removed_existing": removed, "collections": {"common": col_common.name, **{lid: c.name for lid, c in col_close.items()}},
        "tokens": tokens, "race_prefixes": list(rf.RACE_PREFIXES), "max_rings_per_object": rf.MAX_RINGS_PER_OBJECT,
        "shading": {"smooth": True, "sharp_deg": rf.SHARP_DEG, "kerb_outline_hard": True,
                    "triangles": tot["triangles"], "render_verts_est": tot["render_verts_est"],
                    "verts_per_triangle_est": round(tot["render_verts_est"] / max(1, tot["triangles"]), 3)},
        "density": {"ring_spacing_max_target_m": rf.RING_SPACING_MAX_M, "chord_max_target_m": rf.CHORD_MAX_M,
                    "rings_inserted": tot["densified"], "ring_spacing_max_m": round(tot["spacing_max"], 3),
                    "chord_max_m": round(tot["chord_max"], 4)},
        "totals": {"objects": len(objects), "positions": tot["positions"], "rings": strip_rings,
                   "edge_length_m": round(tot["edge_len"], 1), "edge_centreline_m": round(tot["edge_cl"], 1),
                   "edge_rings": tot["edge_rings"], "edge_segments_4m": round(tot["edge_len"] / rf.MODULE_PITCH_M),
                   "edge_objects": sum(1 for o in objects if o["kind"] == "edge"),
                   "close_objects": sum(1 for o in objects if o["kind"] == "close"),
                   "close_rings": sum(L["rings"] for L in per_layout.values()),
                   "kerb_length_m": round(tot["kerb_len"], 1), "kerb_stations": tot["kerb_stations"],
                   "kerb_objects": sum(1 for o in objects if o["kind"] == "kerb"),
                   "seated_hit": strips.hit + kerbs.hit + (walk.hit if walk is not strips else 0),
                   "seated_near": strips.near + kerbs.near + (walk.near if walk is not strips else 0),
                   "seated_interpolated": n_interp,
                   "deck_vs_data_max_m": round(abs(all_devs[0][0]), 3) if all_devs else 0.0,
                   "other_deck_above_rings": len(all_other),
                   "other_deck_above_max_m": all_other[0][0] if all_other else 0.0},
        "layouts": per_layout,
        "bridge_seating": bridge,
        "corners": [{k: v for k, v in c.items() if k != "kerbs"} | {"kerbs": [{"side": kb["side"], "kind": kb["kind"],
                     "i": kb["i"], "j": kb["j"], "declared": bool(kb.get("declared"))} for kb in c["kerbs"]]} for c in corners],
        "kerbs_declared_unmatched": unmatched_kerbs,
        "kerb_clips": {o["name"]: o["clip"] for o in objects if o["kind"] == "kerb"},
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
    print(f"[race] COMMON (collection {col_common.name}): curb strips {t['edge_length_m']} m / {t['edge_rings']} rings in "
          f"{t['edge_objects']} objects (closed loops, bridges included); kerbs {t['kerb_length_m']} m / {t['kerb_stations']} "
          f"stations in {t['kerb_objects']} objects")
    for lid, L in per_layout.items():
        print(f"[race] {lid} closure (collection {L['collection']}, token {L['token']}): {L['length_m']} m "
              f"(centreline {L['centreline_m']} m) / {L['rings']} rings / {L['segments_4m']} x 4.04 m in {L['objects']} objects, "
              f"{L['positions']} positions, ~{L['render_verts_est']} render verts")
    pins = [e for o in objects if o["kind"] == "close" for e in o.get("ends", []) if e.get("kind") == "pin"]
    print(f"[race] closure pins: {len(pins)}, gap to the far curb strip max "
          f"{max([e['gap_m'] for e in pins] or [0.0]):.3f} m; free ends: "
          f"{sum(1 for o in objects for e in o.get('ends', []) if e.get('kind') == 'free')}")
    for name, clip in report["kerb_clips"].items():
        if clip and clip.get("stations_removed") != [0, 0]:
            print(f"[race] kerb {name} clipped by {clip['by']}: {clip['stations_removed']} stations (start, end) removed, "
                  f"kept min clearance {clip['min_clear_m']} m")
    print(f"[race] bridge spans: {bridge['hit']} rings hit / {bridge['near']} near / {bridge['interpolated']} interpolated")
    print(f"[race] {t['positions']} positions in {t['objects']} objects; seated {t['seated_hit']} hit / {t['seated_near']} near / "
          f"{t['seated_interpolated']} interpolated; deck vs data max {t['deck_vs_data_max_m']} m; other deck above "
          f"{t['other_deck_above_rings']} rings (max {t['other_deck_above_max_m']} m); removed {removed} old; saved "
          f"{out_blend.name} ({report['seconds']} s)")
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

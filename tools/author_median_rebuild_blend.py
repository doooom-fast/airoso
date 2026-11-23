"""Re-author the raised median islands of ONE line in loop.blend from corrected data (ledger 0099 round 3, items 1b and 2;
Lake Murray).

    blender --background --python-exit-code 1 --python tools/author_median_rebuild_blend.py -- <project>
            --v021 <the track's scripts-v021> [--blend <loop.blend>] [--save-as <copy.blend>]

WHY A SCENE STEP. tools/author_median_blend.py is a DRAFT step: it builds every island at once into CURB / TERRAIN /
GUARDRAIL, and tools/expansion_pieces.py decorate lays a divided piece's paint into MARKINGS / YLINE. Lake Murray's
chain never runs its draft again (it builds from the committed, authored blend), so correcting an island's data alone
changes nothing that ships. This step makes the scene say what the corrected data says, for one island, and nothing
else: Mission Gorge Rd's long island MD13, declared and built unbroken across the real Margerum Avenue / Mission Vista
Drive crossing (source/expansion/mg_median/: the measurement, fix_mg_median.py, its record).

WHAT. Opt-in, track.config.json route.median_rebuild {"line": <a line of data/median_bands.json>, "was_rows": [first,
last] or a list of such pairs (every built island of the line the correction touches: item 2 corrects two),
"record": <the correction's record, project-relative>}; key absent = no-op, the blend not opened.
  1. EACH OLD ISLAND IS FOUND BY WHAT IT IS, AND REFUSED IF IT IS NOT EXACTLY THAT (the Mac, 2026-11-23). The record
     holds the line's data as it stood before the correction. From it the island's own rule (tools/median_island.py)
     gives every vertex the draft built for rows was_rows: the curb ring, the deck, the beam, each post. Each is looked
     for in the scene as ONE loose part of exactly that many vertices, every vertex within TOL_M of where the rule
     puts it: the curb in CURB, the deck in the medians' top object (route.median_tops: the grass object, the paved
     one, or TERRAIN on a scene no tops step has been over), the beam and posts in GUARDRAIL. The paint strips the
     correction changes are found the same way, strip by strip, in MARKINGS / YLINE, by the assembler's own paint
     function on the paint as it stood. Anything missing, extra, or off: fatal, nothing saved. Counts and bounds are
     printed.
  2. They are taken out, and the islands the corrected data holds between the first and the last of those rows are
     built by the same rule into the same objects (a new deck goes where an old one lay; the tops step then gives it the
     object of its island; an island the corrected data makes long enough gets the rule's barrier, one it makes shorter
     than the rule's 120 m loses it). The
     changed paint strips are laid by the assembler's own function. Nothing else in any object moves.
  3. Self-checks (fatal, nothing saved): every object lost exactly the old vertices and gained exactly the new; each
     new part is there as the rule made it; every new deck vertex stands DECK_OVER_M +- DECK_TOL_M over the road (the
     tops step's own numbers); no vertex of a new curb ring stands outside the road's pavement.
Writes data/median_rebuild.json and stamps the scene (property `median_rebuild`: the line, the rows, a checksum of the
data built from). Idempotent: a scene carrying that stamp is left alone and not saved; a stamp of other data is fatal.

The assembler's package (tracks/<track>/scripts-v021) is registered as `scripts` from --v021 unless the caller has
already done so (tools/ship_track.sh's V021_SHIM)."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

TOL_M = 2e-3            # tools/weld_mouths_blend.py LAYOUT_TOL_M: a scene vertex against the rule's own (float32 in the mesh)
DECK_OVER_M = 0.185     # tools/author_median_tops_blend.py: the deck over the road it stands on ...
DECK_TOL_M = 0.06       # ... and how far a deck vertex may be off it
PAINT_LIFT_M = 0.115    # tools/weld_mouths_blend.py: the assembler lays a connector's paint this far over its line
TAG = "[median-rebuild] "


def die(msg):
    print(TAG + "FATAL " + msg)
    raise SystemExit(1)


def _load(name, rel):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MI = _load("_median_island_rebuild", "tools/median_island.py")


def spec(cfg):
    s = (cfg.get("route") or {}).get("median_rebuild")
    if not s:
        return None
    rows = s.get("was_rows") or []
    if rows and not isinstance(rows[0], (list, tuple)):
        rows = [rows]
    if not s.get("line") or not rows or any(len(r) != 2 for r in rows) or not s.get("record"):
        die(f"route.median_rebuild {s!r} is not {{line, was_rows: [first, last] or a list of them, record}}")
    was = sorted((int(a), int(b)) for a, b in rows)
    if any(a > b for a, b in was) or any(was[k][1] >= was[k + 1][0] for k in range(len(was) - 1)):
        die(f"route.median_rebuild.was_rows {rows!r}: the islands overlap or run backwards")
    return {"line": str(s["line"]), "was": was, "record": str(s["record"])}


def old_data(island, record):
    """(points, widths) of the line's island as it stood: the file's, with the record's `before` put back"""
    pts = [list(p) for p in island["points_xyz_m"]]
    iw = [float(w) for w in island["island_w_by_point"]]
    for k, v in (record.get("island") or {}).get("before", {}).items():
        iw[int(k)] = float(v["w"])
        pts[int(k)] = list(v["p"])
    return pts, iw


def old_paint(paint, record):
    lines = [dict(ln, off=list(ln["off"])) for ln in paint.get("lines") or []]
    for li, d in ((record.get("paint") or {}).get("before") or {}).items():
        for i, off in d.items():
            lines[int(li)]["off"][int(i)] = off
    return dict(paint, lines=lines)


def island_parts(pts, iw, a, b):
    """what the rule builds for the islands of the points a..b (inclusive): {"curb": [(verts, faces)], "deck": [...],
    "beam": [...], "posts": [...]}, one entry per loose part, faces counted from 0 within the part"""
    out = {"curb": [], "deck": [], "beam": [], "posts": [], "runs": []}
    for (i, j) in MI.segments(iw):
        if j - 1 < a or i > b:
            continue
        if i < a or j - 1 > b:
            die(f"the island of points {i}-{j - 1} reaches outside {a}-{b}: this step re-authors whole islands inside the rows it is given")
        out["runs"].append([i, j - 1])
        cv, cf, dv, df = [], [], [], []
        for k in range(i, j):
            curb, deck = MI.ring(pts, iw, i, j, k)
            cv += curb
            dv += deck
        for si in range(j - i - 1):
            cf += MI.curb_span_faces(si * 6)
            df.append(MI.deck_face(si * 2))
        cf += MI.curb_start_cap(0) + MI.curb_end_cap((j - i - 1) * 6)
        out["curb"].append((cv, cf))
        out["deck"].append((dv, df))
        if MI.seg_length(pts, i, j) >= MI.BARRIER_MIN_M:
            bks = MI.beam_points(i, j)
            bv, bf = [], []
            for k in bks:
                bv += MI.beam_ring(pts, k)
            for si in range(len(bks) - 1):
                bf += MI.beam_span_faces(si * 4)
            out["beam"].append((bv, bf))
            for k in MI.post_points(pts, bks):
                out["posts"].append(MI.post(pts, k))
    return out


def paint_quads(wr, ws, conn, paint):
    """{"MARKINGS": [quad], "YLINE": [quad]}: each quad its four vertices in Blender's frame, as the assembler lays them
    (blender/build_loop_blend.py through ribbon.connector_markings; tools/weld_mouths_blend.py rebuilds them so)"""
    cpts = ws.smooth_centerline([tuple(p) for p in conn["points_xyz_m"]], sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
    cmk = wr.connector_markings(cpts, list(conn["widths_m"]), conn.get("stub"), paint)
    out = {}
    for name, key in (("MARKINGS", "white"), ("YLINE", "yellow")):
        V, T = cmk[key]["vertices"], cmk[key]["tris"]
        if len(V) % 4 or len(T) * 2 != len(V):
            die(f"the assembler's {key} paint is not one quad of four vertices per strip ({len(V)} vertices, {len(T)} triangles)")
        out[name] = [[(x, z, y + PAINT_LIFT_M) for (x, y, z) in V[q:q + 4]] for q in range(0, len(V), 4)]
    return out


def signature(sp, pts, iw, quads):
    a, b = sp["was"][0][0], sp["was"][-1][1]
    h = hashlib.sha256()
    h.update(json.dumps([sp["line"], sp["was"], [[round(c, 4) for c in p] for p in pts[a:b + 1]], [round(w, 4) for w in iw[a:b + 1]],
                         {n: [[[round(c, 4) for c in v] for v in q] for q in qs] for n, qs in sorted(quads.items())}]).encode("utf-8"))
    return h.hexdigest()[:16]


def main():
    import bmesh
    import bpy
    from mathutils import Vector, kdtree
    from mathutils.bvhtree import BVHTree
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        die("usage: ... -- <project> --v021 <scripts-v021> [--blend <loop.blend>] [--save-as <copy>]")
    proj = Path(argv[0])
    opt = {k: argv[argv.index(k) + 1] for k in ("--blend", "--save-as", "--v021") if k in argv}
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    sp = spec(cfg)
    if sp is None:
        print(TAG + "route.median_rebuild not declared: nothing to do, the blend not opened")
        return
    try:
        from scripts.geometry import ribbon as wr, smooth as ws
        wr.connector_markings
    except (ImportError, AttributeError):
        if "--v021" not in opt:
            die("the assembler's package is not registered as `scripts` and no --v021 <scripts-v021> was given")
        import importlib.util as u
        v021 = Path(opt["--v021"])
        s_ = u.spec_from_file_location("scripts", str(v021 / "__init__.py"), submodule_search_locations=[str(v021)])
        m_ = u.module_from_spec(s_)
        sys.modules["scripts"] = m_
        s_.loader.exec_module(m_)
        from scripts.geometry import ribbon as wr, smooth as ws
    data = proj / "data"
    record = json.loads((proj / sp["record"]).read_text(encoding="utf-8"))
    mb = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))
    island = next((ci for ci in mb.get("connector_islands") or [] if ci["name"] == sp["line"]), None)
    if island is None:
        die(f"data/median_bands.json holds no connector island {sp['line']}")
    conn = next(c for c in json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"] if c["name"] == sp["line"])
    a, b = sp["was"][0][0], sp["was"][-1][1]                 # the rows this step re-authors: from the first old island to the last
    pts_new, iw_new = [list(p) for p in island["points_xyz_m"]], [float(w) for w in island["island_w_by_point"]]
    pts_old, iw_old = old_data(island, record)
    old = {"curb": [], "deck": [], "beam": [], "posts": [], "runs": []}
    for (a_, b_) in sp["was"]:
        if (a_, b_ + 1) not in MI.segments(iw_old):
            die(f"the record's data holds no island of exactly points {a_}-{b_} on {sp['line']} (its islands: {[(i, j - 1) for i, j in MI.segments(iw_old)]})")
        one = island_parts(pts_old, iw_old, a_, b_)
        for k in old:
            old[k] += one[k]
    between = [(i, j - 1) for i, j in MI.segments(iw_old) if a <= i and j - 1 <= b and (i, j - 1) not in sp["was"]]
    if between:
        die(f"the record's data holds islands {between} between the rows given: name every built island the step re-authors")
    new = island_parts(pts_new, iw_new, a, b)
    q_old, q_new = paint_quads(wr, ws, conn, old_paint(conn["paint"], record)), paint_quads(wr, ws, conn, conn["paint"])

    def qkey(q):
        return tuple(round(c, 4) for v in q for c in v)

    k_old, k_new = ({n: {qkey(q) for q in qs[n]} for n in qs} for qs in (q_old, q_new))
    paint_out = {n: [q for q in q_old[n] if qkey(q) not in k_new[n]] for n in q_old}       # the strips the correction changes
    paint_in = {n: [q for q in q_new[n] if qkey(q) not in k_old[n]] for n in q_new}
    sig = signature(sp, pts_new, iw_new, q_new)

    blend = Path(opt.get("--blend") or proj / "loop.blend")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    stamp = scene.get("median_rebuild")
    if stamp:
        st = json.loads(stamp)
        if st.get("signature") == sig and st.get("line") == sp["line"]:
            print(TAG + f"the scene already carries {sp['line']} rows {sp['was']} rebuilt from this data ({sig}): nothing to do, nothing saved")
            return
        die(f"the scene carries a median_rebuild stamp of other data ({st}); this data is {sig}")
    tops = (cfg.get("route") or {}).get("median_tops") or {}
    deck_homes = [n for n in (tops.get("object"), (tops.get("paver") or {}).get("object"), "TERRAIN") if n]

    class Mesh:
        """one object's mesh: its vertices in the world, its loose parts, a KD tree to find a vertex by place"""
        def __init__(self, name):
            self.ob = bpy.data.objects.get(name)
            if self.ob is None or self.ob.type != "MESH":
                die(f"no {name} mesh in the scene")
            me = self.ob.data
            self.mw = self.ob.matrix_world
            self.co = [self.mw @ v.co for v in me.vertices]
            parent = list(range(len(self.co)))

            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            for pl in me.polygons:
                vs = list(pl.vertices)
                for k in vs[1:]:
                    ra, rb = find(vs[0]), find(k)
                    if ra != rb:
                        parent[rb] = ra
            self.root = [find(i) for i in range(len(self.co))]
            self.size = {}
            for r in self.root:
                self.size[r] = self.size.get(r, 0) + 1
            self.kd = kdtree.KDTree(len(self.co))
            for i, c in enumerate(self.co):
                self.kd.insert(c, i)
            self.kd.balance()
            self.n0 = (len(me.vertices), len(me.polygons))
            self.out, self.add = [], []

        def part(self, verts, what):
            """the indices of the ONE loose part that is exactly these vertices, or None"""
            want = [Vector(v) for v in verts]
            cands = {self.root[i] for (_c, i, _d) in self.kd.find_range(want[0], TOL_M)}
            for r in sorted(cands):
                if self.size[r] != len(want):
                    continue
                idx = sorted(i for i in range(len(self.co)) if self.root[i] == r) if len(want) > 64 else \
                    sorted({i for w in want for (_c, i, _d) in self.kd.find_range(w, TOL_M) if self.root[i] == r})
                if len(idx) != len(want):
                    continue
                if max((self.co[i] - w).length for i, w in zip(idx, want)) <= TOL_M:      # the rule's own order
                    return idx
                used, ok = set(), True                                                    # or the same set, in another order
                for w in want:
                    hit = [i for (_c, i, _d) in self.kd.find_range(w, TOL_M) if self.root[i] == r and i not in used]
                    if not hit:
                        ok = False
                        break
                    used.add(hit[0])
                if ok and len(used) == len(want):
                    return sorted(used)
            return None

    def bounds(vs):
        return [[round(min(v[k] for v in vs), 2), round(max(v[k] for v in vs), 2)] for k in range(3)]

    # ---- 1. the old island, found by what it is -------------------------------------------------------------------
    M = {n: Mesh(n) for n in ("CURB", "GUARDRAIL", "MARKINGS", "YLINE")}
    found, miss = {}, []
    found["curb"], found["deck"] = [], []
    for (verts, _f), rows_ in zip(old["curb"], old["runs"]):
        idx = M["CURB"].part(verts, "curb")
        if idx is None:
            miss.append(f"CURB holds no loose part of exactly {len(verts)} vertices on the ring of the old island rows {rows_} "
                        f"(bounds {bounds(verts)})")
        else:
            M["CURB"].out += idx
            found["curb"].append({"rows": rows_, "object": "CURB", "vertices": len(idx), "bounds_xyz": bounds([M["CURB"].co[i] for i in idx])})
    deck_ob = None
    for (verts, _f), rows_ in zip(old["deck"], old["runs"]):
        home = None
        for name in deck_homes:
            if bpy.data.objects.get(name) is None:
                continue
            if name not in M:
                M[name] = Mesh(name)
            idx = M[name].part(verts, "deck")
            if idx is not None:
                home = name
                M[name].out += idx
                found["deck"].append({"rows": rows_, "object": name, "vertices": len(idx), "bounds_xyz": bounds([M[name].co[i] for i in idx])})
                break
        if home is None:
            miss.append(f"none of {deck_homes} holds the deck of the old island rows {rows_} as one loose part of {len(verts)} vertices")
        elif deck_ob not in (None, home):
            miss.append(f"the old islands' decks lie in two objects ({deck_ob}, {home}): the new decks have one home")
        else:
            deck_ob = home
    n_rail = 0
    for what, parts in (("beam", old["beam"]), ("post", old["posts"])):
        for verts, _f in parts:
            idx = M["GUARDRAIL"].part(verts, what)
            if idx is None:
                miss.append(f"GUARDRAIL holds no loose part that is the old island's {what} at {[round(c, 1) for c in verts[0]]}")
            else:
                M["GUARDRAIL"].out += idx
                n_rail += len(idx)
    found["barrier"] = {"object": "GUARDRAIL", "vertices": n_rail, "beams": len(old["beam"]), "posts": len(old["posts"])}
    for name in ("MARKINGS", "YLINE"):
        n = 0
        for q in paint_out[name]:
            idx = M[name].part(q, "paint strip")
            if idx is None:
                miss.append(f"{name} holds no strip at {[round(c, 2) for c in q[0]]} (one the correction changes)")
            else:
                M[name].out += idx
                n += 1
        found[name.lower()] = {"object": name, "strips": n, "of": len(paint_out[name])}
    print(TAG + f"the old islands of {sp['line']} rows {old['runs']}, as the rule and the record give them: curb {[len(v) for v, _f in old['curb']]} v, "
          f"deck {[len(v) for v, _f in old['deck']]} v, beam {sum(len(v) for v, _f in old['beam'])} v, {len(old['posts'])} posts, "
          f"{len(paint_out['MARKINGS'])} + {len(paint_out['YLINE'])} paint strips to change; found: {json.dumps(found)}")
    if miss:
        die(f"the scene does not hold the island exactly as rows {old['runs']} were built ({len(miss)} things): " + "; ".join(miss[:6]))
    for name, m in M.items():
        if len(set(m.out)) != len(m.out):
            die(f"{name}: a vertex was claimed twice")

    # ---- 2. out with the old, in with the new ---------------------------------------------------------------------
    for kind, target in (("curb", "CURB"), ("deck", deck_ob), ("beam", "GUARDRAIL"), ("posts", "GUARDRAIL")):
        M[target].add += [(verts, faces) for verts, faces in new[kind]]
    for name in ("MARKINGS", "YLINE"):
        M[name].add += [(q, [(0, 1, 3), (0, 3, 2)]) for q in paint_in[name]]
    added = {}
    for name, m in M.items():
        if not m.out and not m.add:
            continue
        me = m.ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        gone = [bm.verts[i] for i in m.out]
        ref = next((f for v in gone for f in v.link_faces), None)
        mat, smooth = (ref.material_index, ref.smooth) if ref is not None else (0, False)
        n_f_gone = len({f for v in gone for f in v.link_faces})
        bmesh.ops.delete(bm, geom=gone, context="VERTS")
        inv = m.mw.inverted()
        nv = nf = 0
        for verts, faces in m.add:
            vs = [bm.verts.new(inv @ Vector(c)) for c in verts]
            nv += len(vs)
            for f in faces:
                face = bm.faces.new([vs[k] for k in f])
                face.material_index, face.smooth = mat, smooth
                nf += 1
        bm.to_mesh(me)
        bm.free()
        me.update()
        if (len(me.vertices), len(me.polygons)) != (m.n0[0] - len(m.out) + nv, m.n0[1] - n_f_gone + nf):
            die(f"{name}: {len(me.vertices)} vertices / {len(me.polygons)} faces after the rebuild, expected "
                f"{m.n0[0] - len(m.out) + nv} / {m.n0[1] - n_f_gone + nf}")
        added[name] = {"vertices_out": len(m.out), "faces_out": n_f_gone, "vertices_in": nv, "faces_in": nf,
                       "vertices": [m.n0[0], len(me.vertices)], "faces": [m.n0[1], len(me.polygons)]}

    # ---- 3. self-checks on the scene as it now stands -------------------------------------------------------------
    after = {n: Mesh(n) for n in added}
    for kind, target in (("curb", "CURB"), ("deck", deck_ob), ("beam", "GUARDRAIL"), ("posts", "GUARDRAIL")):
        for verts, _f in new[kind]:
            if after[target].part(verts, kind) is None:
                die(f"{target}: a new {kind} part is not in the scene as the rule made it ({len(verts)} vertices at {[round(c, 1) for c in verts[0]]})")
        for verts, _f in old[kind]:
            if new[kind] and any(len(v2) == len(verts) and max((Vector(p) - Vector(q)).length for p, q in zip(v2, verts)) <= TOL_M for v2, _g in new[kind]):
                continue                                                # a part the new data builds exactly as the old (a post)
            if after[target].part(verts, kind) is not None:
                die(f"{target}: an old {kind} part is still in the scene")
    for name in ("MARKINGS", "YLINE"):
        if name in after:
            for q in paint_in[name]:
                if after[name].part(q, "strip") is None:
                    die(f"{name}: a new paint strip is not in the scene")
    rob = bpy.data.objects["ROAD"]
    rv = [rob.matrix_world @ v.co for v in rob.data.vertices]
    rf = [list(pl.vertices) for pl in rob.data.polygons]
    road = BVHTree.FromPolygons(rv, rf)
    down = Vector((0.0, 0.0, -1.0))

    def over_road(c):
        hit = road.ray_cast(Vector((c[0], c[1], c[2] + 0.5)), down, 3.0)
        return None if hit[0] is None else c[2] - hit[0].z

    deck_d = [over_road(c) for verts, _f in new["deck"] for c in verts]
    if any(x is None or abs(x - DECK_OVER_M) > DECK_TOL_M for x in deck_d):
        bad = [x for x in deck_d if x is None or abs(x - DECK_OVER_M) > DECK_TOL_M]
        die(f"{len(bad)} of {len(deck_d)} new deck vertices do not stand {DECK_OVER_M} +- {DECK_TOL_M} m over the road (e.g. {bad[:4]})")
    base_d = [over_road(verts[k]) for verts, _f in new["curb"] for k in range(0, len(verts), 6)] + \
             [over_road(verts[k + 5]) for verts, _f in new["curb"] for k in range(0, len(verts), 6)]
    if any(x is None for x in base_d):
        die(f"{sum(1 for x in base_d if x is None)} vertices of a new curb's base stand outside the road's pavement")
    old_base = [over_road(verts[k]) for verts, _f in old["curb"] for k in range(0, len(verts), 6)] + \
               [over_road(verts[k + 5]) for verts, _f in old["curb"] for k in range(0, len(verts), 6)]
    old_base = [x for x in old_base if x is not None]
    rep = {"_doc": "tools/author_median_rebuild_blend.py (ledger 0099 round 3, items 1b and 2): the median islands of one line re-authored in the scene "
                   "from corrected data, by the island's own rule (tools/median_island.py) and the assembler's own paint function",
           "line": sp["line"], "was_rows": old["runs"], "now_rows": new["runs"], "record": sp["record"], "signature": sig,
           "the_old_island_as_found": found, "objects": added,
           "new": {"curb_vertices": [len(v) for v, _f in new["curb"]], "deck_vertices": [len(v) for v, _f in new["deck"]],
                   "beam_vertices": [len(v) for v, _f in new["beam"]], "posts": len(new["posts"]),
                   "paint_strips": {n: len(paint_in[n]) for n in paint_in}},
           "old": {"curb_vertices": [len(v) for v, _f in old["curb"]], "deck_vertices": [len(v) for v, _f in old["deck"]],
                   "beam_vertices": [len(v) for v, _f in old["beam"]], "posts": len(old["posts"]),
                   "paint_strips": {n: len(paint_out[n]) for n in paint_out}},
           "deck_over_the_road_m": {"min": round(min(deck_d), 4), "max": round(max(deck_d), 4)},
           "curb_base_over_the_road_m": {"new": [round(min(base_d), 4), round(max(base_d), 4)],
                                         "old": [round(min(old_base), 4), round(max(old_base), 4)],
                                         "_doc": "the rule sets a ring's base 0.02 m under its line's own height; where the road "
                                                 "falls away from that line the base stands over the road by the difference"},
           "deck_object": deck_ob}
    scene["median_rebuild"] = json.dumps({"line": sp["line"], "was_rows": old["runs"], "now_rows": new["runs"], "signature": sig})
    (data / "median_rebuild.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(TAG + json.dumps({k: v for k, v in rep.items() if k != "_doc"}))
    if "--save-as" in opt:
        bpy.ops.wm.save_as_mainfile(filepath=opt["--save-as"], copy=True)
        print(TAG + f"saved a copy: {opt['--save-as']}")
    else:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print(TAG + f"saved {blend}")


if __name__ == "__main__":
    main()

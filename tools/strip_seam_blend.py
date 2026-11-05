"""A ground seam along the edge strip's outer lip, so the strip shows wherever it is built (ledger 0078 round 5).

The v021 edge strip (CURB; a circuit's `route.edge`: the asphalt edge held, then graded down to the grass meet) falls
below the lane edge towards its outer lip. engine-july's prep then seats the ground (build_kn5_loop._conform_and_reseat):
a TERRAIN vertex under a drivable sheet is clamped 0.02 m under it (anti-poke), one past the pavement goes to the 3 m
contact band at the LANE edge's height - 0.02. Wherever a ground triangle has a vertex inside the strip and one on the band
beyond it, it is a straight chord from under the strip up to lane-edge height, and it lies over the strip's lower, outer
part: at 1 m past the edge the strip was the top surface on 60.6 % of High Plains' side-stations with the ground cut to
0.6 m, and 24.4 % once the cut followed the bank (round 4; Nevada 57.2 -> 41.8 %).

This step gives the ground an edge ALONG the strip: one TERRAIN vertex per strip row, INSET_M inside the strip's outer lip
(so the prep's anti-poke finds the strip over it and clamps it under), and the consecutive ones joined by terrain edges
(bmesh connect_vert_pair cuts the faces between them). No ground triangle then spans the lip: inside it every triangle
is under the strip, outside it the band starts. Nothing else is moved; the prep places every new vertex. Opt-in: a track
lists the draft step `strip_seam` after `seat_edges`; Lake Murray never runs it.

Self-check, exit 1 and loop.blend not saved: CURB is not the assembler's layout; more than MAX_MISS_SHARE of the seam
points fall outside the terrain or fail to join.

LOCAL SCOPE (ledger 0078 round 7; config `strip_seam.scope` "local"): every bmesh operator allocates a flag layer over the
WHOLE mesh, so on a 25 km lap's terrain (the Lariat: ~0.9 M vertices, ~29,000 seam points, a poke and a cut each) the
whole-terrain seam does not finish. The local scope does the same pokes and cuts CHUNK_ROWS seam points at a time, on a
small mesh holding only the terrain faces within PAD_M of them, and writes the result back into the terrain's arrays.
The small mesh's outer edges are shared with faces it does not hold, so a chunk that splits one is thrown away and redone
with a wider pad (PAD_M x 2, x 4); one that still splits it counts its seam points as missed. Faces away from the seam
keep their vertices and their material. The scope is the track config's; the four circuit ports of round 6 keep the
whole-terrain seam they shipped with.

    blender --background --python-exit-code 1 --python tools/strip_seam_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402

INSET_M = 0.05          # [invented] the seam this far inside the strip's outer lip: under the strip by construction
CELL_M = 4.0            # face lookup grid
MAX_MISS_SHARE = 0.01   # [invented] seam points that may miss (outside the terrain, a join that fails) before it refuses
JOIN_DEPTH = 3          # [invented] midpoint levels a failed join may try (ledger 0078 round 6: Sand Creek, 366 failed joins)
CHUNK_ROWS = 120        # [invented] local scope: seam points per small mesh
PAD_M = 8.0             # [invented] local scope: terrain faces this far around a chunk's seam points go into its small mesh


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8"))["connectors"] if cp.exists() else []
    lay = mw.mesh_layout([tuple(p) for p in local["points_xyz_m"]], conns)
    rows, closed = lay["MAINLINE"]["rows"], lay["MAINLINE"]["closed"]
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb, terr = bpy.data.objects.get("CURB"), bpy.data.objects.get("TERRAIN")
    if curb is None or terr is None:
        raise SystemExit("[strip-seam] FATAL: no CURB or TERRAIN in loop.blend (run after the assembler, before the prep)")
    if len(curb.data.vertices) != lay["_curb_total"]:
        raise SystemExit(f"[strip-seam] FATAL: CURB has {len(curb.data.vertices)} verts, the assembler's layout says "
                         f"{lay['_curb_total']}")
    CV = curb.data.vertices
    # THE MOUTHS (ledger 0079 round B, Sand Creek's grid streets): where a side street meets the lap, tools/gap_mouths_blend.py
    # deletes the strip across the mouth (mouth_weld.gap_window, the same window here) and the street's own ribbon stands on
    # the ground there: no lip to seam. Those rows are left out (not counted, not seamed). No mouth on the lap = every row
    gapped = {1: set(), -1: set()}
    mp = data / "mouths.json"
    mouths = json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else []
    hpts = [tuple(p) for p in local["points_xyz_m"]]
    for mo in mouths:
        if mo.get("host") != "MAINLINE" or "host_seg" not in mo:
            continue
        gapped[int(mo["side"])].update(mw.gap_window(hpts, rows, closed, int(mo["host_seg"]), float(mo["host_t"]),
                                                     float(mo["connector_width_m"]), float(mo.get("angle_deg") or 90.0)))
    if any(gapped.values()):
        print(f"[strip-seam] {sum(len(v) for v in gapped.values())} lap rows inside side-street mouths left unseamed "
              f"({sum(1 for mo in mouths if mo.get('host') == 'MAINLINE')} mouths on the lap)")
    seams = []
    for side in (1, -1):
        pts = []
        for r in range(rows):
            if r in gapped[side]:
                pts.append(None)
                continue
            o = CV[mw.curb_index(lay, "MAINLINE", r, side, 3)].co
            e = CV[mw.curb_index(lay, "MAINLINE", r, side, 0)].co
            dx, dy = e.x - o.x, e.y - o.y
            L = math.hypot(dx, dy) or 1.0
            pts.append((o.x + dx / L * INSET_M, o.y + dy / L * INSET_M))
        seams.append(pts)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    # THE PADS' OUTLINES (opt-in strip_seam.pads, ledger 0079 round D): the ground seamed along each lm_pads deck's own
    # outline (data/pads.built.json outline_en, every point), so no ground triangle spans the deck's edge. 0.2.2's try:
    # a 0.7 m ground triangle from the contact band outside 48th / Colorado's deck in over its gutter stood 8-10 mm over
    # the deck 0.2 m inside the edge (verify_pads P4). Absent = the lap's strip alone, as before (the Lariat)
    bp = data / "pads.built.json"
    if (cfg.get("strip_seam") or {}).get("pads") and bp.exists():
        rings = [[tuple(q) for q in p["outline_en"]] for p in json.loads(bp.read_text(encoding="utf-8")).get("pads") or []]
        for r_ in rings:
            seams.append(r_ + [r_[0]] if closed is False else r_)
        print(f"[strip-seam] {len(rings)} pad outline(s), {sum(len(r_) for r_ in rings)} points, seamed too")
    if ((cfg.get("strip_seam") or {}).get("scope")) == "local":
        seam_local(proj, terr, seams, closed)
        return

    bm = bmesh.new(); bm.from_mesh(terr.data)
    n0 = len(bm.verts)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    grid = {}

    def put(f):
        xs = [v.co.x for v in f.verts]; ys = [v.co.y for v in f.verts]
        for gx in range(int(min(xs) // CELL_M), int(max(xs) // CELL_M) + 1):
            for gy in range(int(min(ys) // CELL_M), int(max(ys) // CELL_M) + 1):
                grid.setdefault((gx, gy), []).append(f)

    for f in bm.faces:
        put(f)

    def locate(x, y):
        key = (int(x // CELL_M), int(y // CELL_M))
        cell = grid.get(key)
        if cell and len(cell) > 64:                       # drop the faces a poke or a cut replaced (a 25 km lap, the Lariat)
            cell[:] = [f for f in cell if f.is_valid]
        for f in cell or ():
            if not f.is_valid or len(f.verts) != 3:
                continue
            a, b, c = (v.co for v in f.verts)
            d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
            if abs(d) < 1e-12:
                continue
            w0 = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / d
            w1 = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / d
            w2 = 1.0 - w0 - w1
            if min(w0, w1, w2) >= -1e-9:
                return f, w0 * a.z + w1 * b.z + w2 * c.z
        return None, None

    miss = joined = 0
    total = 0
    for pts in seams:
        verts = []
        for q in pts:
            if q is None:                              # a lap row inside a side-street mouth (above): not seamed
                verts.append(None)
                continue
            x, y = q
            total += 1
            f, z = locate(x, y)
            if f is None:
                verts.append(None); miss += 1
                continue
            res = bmesh.ops.poke(bm, faces=[f])
            v = res["verts"][0]
            v.co.x, v.co.y, v.co.z = x, y, z
            for nf in res["faces"]:
                put(nf)
            verts.append(v)
        pairs = list(zip(verts, verts[1:])) + ([(verts[-1], verts[0])] if closed else [])

        def join(a, b, depth=0):
            """join a and b with terrain edges; where bmesh finds no cut between them (a path through a vertex, a
            sliver), seat a seam vertex at the midpoint and join the halves (up to JOIN_DEPTH levels)"""
            if any(b in e.verts for e in a.link_edges):
                return True
            try:
                res = bmesh.ops.connect_vert_pair(bm, verts=[a, b])
            except Exception:                                  # noqa: BLE001
                res = {}
            if res.get("edges"):
                for e in res["edges"]:
                    for nf in e.link_faces:
                        put(nf)
                for v in (a, b):
                    for nf in v.link_faces:
                        put(nf)
                return True
            if depth >= JOIN_DEPTH:
                return False
            mx, my = (a.co.x + b.co.x) / 2.0, (a.co.y + b.co.y) / 2.0
            f, z = locate(mx, my)
            if f is None:
                return False
            res = bmesh.ops.poke(bm, faces=[f])
            m = res["verts"][0]
            m.co.x, m.co.y, m.co.z = mx, my, z
            for nf in res["faces"]:
                put(nf)
            return join(a, m, depth + 1) and join(m, b, depth + 1)

        for a, b in pairs:
            if a is None or b is None:
                continue
            if join(a, b):
                joined += 1
            else:
                miss += 1
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    if miss > MAX_MISS_SHARE * total:
        raise SystemExit(f"[strip-seam] FATAL: {miss} of {total} seam points missed the terrain or failed to join; "
                         f"loop.blend not saved")
    bm.to_mesh(terr.data); bm.free(); terr.data.update()
    print(f"[strip-seam] {total} seam points {INSET_M} m inside the strip's outer lip, {joined} joins, {miss} missed; "
          f"TERRAIN {n0} -> {len(terr.data.vertices)} verts; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


def _knife(a, b, put, knifed, max_steps=400):
    """the straight plan segment a -> b cut into the terrain face by face (local scope's fallback where bmesh's
    connect_vert_pair finds no path: a seam running along the grid, through its vertices). From the current vertex,
    the face whose far side the segment crosses is split there: through a vertex the segment meets, or at a new
    vertex on the crossed edge (its height the edge's own, linear). True when b is reached."""
    from mathutils.geometry import intersect_line_line_2d
    cur = a
    B = b.co.xy
    for _ in range(max_steps):
        if any(b in e.verts for e in cur.link_edges):
            knifed[0] += 1
            return True
        shared = next((f for f in cur.link_faces if b in f.verts), None)
        if shared is not None:
            try:
                f2, _l = bmesh.utils.face_split(shared, cur, b)
            except (ValueError, RuntimeError):
                return False
            put(shared); put(f2)
            knifed[0] += 1
            return True
        C = cur.co.xy
        d_now = (B - C).length
        step = None
        for f in cur.link_faces:
            for e in f.edges:
                if cur in e.verts:
                    continue
                v0, v1 = e.verts
                for w in (v0, v1):                          # the segment through a vertex of this face
                    cw = w.co.xy - C
                    cb = B - C
                    if cw.length < 1e-6 or cw.length >= d_now:
                        continue
                    if abs(cb.x * cw.y - cb.y * cw.x) / d_now <= 1e-4 and cb.dot(cw) > 0:
                        step = ("vert", f, w)
                        break
                if step:
                    break
                hit = intersect_line_line_2d(C, B, v0.co.xy, v1.co.xy)
                if hit is None or (hit - C).length < 1e-6:
                    continue
                if (hit - v0.co.xy).length < 1e-4 or (hit - v1.co.xy).length < 1e-4:
                    continue                                # a vertex hit: the loop above takes it
                step = ("edge", f, e, hit)
                break
            if step:
                break
        if step is None:
            return False
        if step[0] == "vert":
            _k, f, w = step
            if not any(w in e.verts for e in cur.link_edges):
                try:
                    f2, _l = bmesh.utils.face_split(f, cur, w)
                except (ValueError, RuntimeError):
                    return False
                put(f); put(f2)
            cur = w
            continue
        _k, f, e, hit = step
        v0, v1 = e.verts
        L = (v1.co.xy - v0.co.xy).length
        t = (hit - v0.co.xy).length / L if L > 1e-12 else 0.5
        _ne, nv = bmesh.utils.edge_split(e, v0, t)
        try:
            f2, _l = bmesh.utils.face_split(f, cur, nv)
        except (ValueError, RuntimeError):
            return False
        for nf in nv.link_faces:
            put(nf)
        put(f2)
        cur = nv
    return False


def _join_fn(bm, locate, put, knifed=None):
    knifed = knifed if knifed is not None else [0]

    def join(a, b, depth=0):
        """as the whole-terrain join: a direct cut, else (local scope) the segment knifed face by face, else a seam
        vertex at the midpoint and the halves (JOIN_DEPTH)"""
        if any(b in e.verts for e in a.link_edges):
            return True
        try:
            res = bmesh.ops.connect_vert_pair(bm, verts=[a, b])
        except Exception:                                  # noqa: BLE001
            res = {}
        if res.get("edges"):
            for e in res["edges"]:
                for nf in e.link_faces:
                    put(nf)
            for v in (a, b):
                for nf in v.link_faces:
                    put(nf)
            return True
        if _knife(a, b, put, knifed):
            return True
        if depth >= JOIN_DEPTH:
            return False
        mx, my = (a.co.x + b.co.x) / 2.0, (a.co.y + b.co.y) / 2.0
        f, z = locate(mx, my)
        if f is None:
            return False
        res = bmesh.ops.poke(bm, faces=[f])
        m = res["verts"][0]
        m.co.x, m.co.y, m.co.z = mx, my, z
        for nf in res["faces"]:
            put(nf)
        return join(a, m, depth + 1) and join(m, b, depth + 1)
    return join


def _face_grid(bm):
    grid = {}

    def put(f):
        xs = [v.co.x for v in f.verts]; ys = [v.co.y for v in f.verts]
        for gx in range(int(min(xs) // CELL_M), int(max(xs) // CELL_M) + 1):
            for gy in range(int(min(ys) // CELL_M), int(max(ys) // CELL_M) + 1):
                grid.setdefault((gx, gy), []).append(f)

    for f in bm.faces:
        put(f)

    def locate(x, y):
        for f in grid.get((int(x // CELL_M), int(y // CELL_M))) or ():
            if not f.is_valid or len(f.verts) != 3:
                continue
            a, b, c = (v.co for v in f.verts)
            d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
            if abs(d) < 1e-12:
                continue
            w0 = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / d
            w1 = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / d
            w2 = 1.0 - w0 - w1
            if min(w0, w1, w2) >= -1e-9:
                return f, w0 * a.z + w1 * b.z + w2 * c.z
        return None, None
    return put, locate


def _cells(pts, cell=100.0, top=12):
    """where the misses sit: the busiest cell-m squares (lower-left corner) and their counts"""
    c = {}
    for x, y in pts:
        k = (int(x // cell * cell), int(y // cell * cell))
        c[k] = c.get(k, 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])[:top]


def seam_local(proj, terr, seams, closed):
    """the seam CHUNK_ROWS points at a time, each on a small mesh of the terrain faces within PAD_M (module doc)"""
    me = terr.data
    n0 = len(me.vertices)
    co = [tuple(v.co) for v in me.vertices]                       # grows: new seam / cut vertices appended
    faces = [tuple(p.vertices) for p in me.polygons]              # grows: a chunk's faces appended, its old ones dead
    mats = [p.material_index for p in me.polygons]
    smooth = [p.use_smooth for p in me.polygons]
    alive = [True] * len(faces)
    grid = {}
    dup = [0]
    lost_at, failed_at = [], []
    knifed = [0]
    why = {}

    def gput(fi):
        xs = [co[i][0] for i in faces[fi]]; ys = [co[i][1] for i in faces[fi]]
        for gx in range(int(min(xs) // CELL_M), int(max(xs) // CELL_M) + 1):
            for gy in range(int(min(ys) // CELL_M), int(max(ys) // CELL_M) + 1):
                grid.setdefault((gx, gy), []).append(fi)

    for fi in range(len(faces)):
        gput(fi)

    def region(xys, pad):
        out = set()
        for x, y in xys:
            for gx in range(int((x - pad) // CELL_M), int((x + pad) // CELL_M) + 1):
                for gy in range(int((y - pad) // CELL_M), int((y + pad) // CELL_M) + 1):
                    for fi in grid.get((gx, gy)) or ():
                        if alive[fi]:
                            out.add(fi)
        return out

    def run_chunk(pts, gidx, idxs, pairs, pad):
        """one chunk on its small mesh; None when it would split an edge it shares with the rest of the terrain"""
        fids = sorted(region([pts[i] for i in idxs], pad))
        if not fids:
            return None
        bm = bmesh.new()
        vmap = {}
        for fi in fids:
            for gi in faces[fi]:
                if gi not in vmap:
                    vmap[gi] = bm.verts.new(co[gi])
        for fi in fids:
            try:
                f = bm.faces.new([vmap[gi] for gi in faces[fi]])
            except ValueError:                                  # a duplicate of a face already in (same vertices): one
                dup[0] += 1                                     # face over the same ground is kept
                continue
            f.material_index = mats[fi]; f.smooth = smooth[fi]
        gid_of = {v: gi for gi, v in vmap.items()}
        # the small mesh's edges a face OUTSIDE it also holds (a terrain border or a hole's rim, held by nothing else,
        # may be cut: no neighbour is left with a T)
        fset = set(fids)
        outer = []
        for e in bm.edges:
            if len(e.link_faces) != 1:
                continue
            ga, gb = gid_of[e.verts[0]], gid_of[e.verts[1]]
            mx, my = (co[ga][0] + co[gb][0]) / 2.0, (co[ga][1] + co[gb][1]) / 2.0
            if any(alive[fi] and fi not in fset and ga in faces[fi] and gb in faces[fi]
                   for fi in grid.get((int(mx // CELL_M), int(my // CELL_M))) or ()):
                outer.append((ga, gb))
        tri = [f for f in bm.faces if len(f.verts) > 3]
        if tri:
            bmesh.ops.triangulate(bm, faces=tri)
        put, locate = _face_grid(bm)
        join = _join_fn(bm, locate, put, knifed)
        sv = {}
        miss = 0
        for i in idxs:
            if gidx[i] is not None:
                v = vmap.get(gidx[i])
                if v is None:                                   # an earlier chunk's seam vertex outside this pad
                    bm.free()
                    why["seam vertex outside"] = why.get("seam vertex outside", 0) + 1
                    return None
                sv[i] = v
                continue
            x, y = pts[i]
            f, z = locate(x, y)
            if f is None:
                sv[i] = None; miss += 1
                lost_at.append((round(x, 1), round(y, 1)))
                continue
            res = bmesh.ops.poke(bm, faces=[f])
            v = res["verts"][0]
            v.co.x, v.co.y, v.co.z = x, y, z
            for nf in res["faces"]:
                put(nf)
            sv[i] = v
        joined = 0
        for a, b in pairs:
            va, vb = sv.get(a), sv.get(b)
            if va is None or vb is None:
                continue
            if join(va, vb):
                joined += 1
            else:
                miss += 1
                failed_at.append((round(va.co.x, 1), round(va.co.y, 1)))
        tri = [f for f in bm.faces if len(f.verts) > 3]
        if tri:
            bmesh.ops.triangulate(bm, faces=tri)
        # the small mesh's outer edges must come back whole: the faces outside it still hold them
        for ga, gb in outer:
            va, vb = vmap[ga], vmap[gb]
            if not any(vb in e.verts for e in va.link_edges):
                bm.free()
                why["outer edge split"] = why.get("outer edge split", 0) + 1
                return None
        new_gid = {}
        for v in bm.verts:
            gi = gid_of.get(v)
            if gi is None:
                gi = len(co); co.append(tuple(v.co))
            new_gid[v] = gi
        for fi in fids:
            alive[fi] = False
        for f in bm.faces:
            faces.append(tuple(new_gid[v] for v in f.verts)); mats.append(f.material_index); smooth.append(f.smooth)
            alive.append(True)
            gput(len(faces) - 1)
        for i, v in sv.items():
            if v is not None and gidx[i] is None:
                gidx[i] = new_gid[v]
        bm.free()
        return joined, miss

    total = joined = miss = chunks = widened = refused = 0
    for pts in seams:
        n = len(pts)
        total += sum(1 for q in pts if q is not None)
        gidx = [None] * n
        pairs = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if closed else [])
        pairs = [(i, j) for i, j in pairs if pts[i] is not None and pts[j] is not None]   # a mouth's rows: not seamed
        for c0 in range(0, len(pairs), CHUNK_ROWS):
            cp = pairs[c0:c0 + CHUNK_ROWS]
            idxs = sorted({i for p in cp for i in p})
            chunks += 1
            for k, pad in enumerate((PAD_M, 2 * PAD_M, 4 * PAD_M)):
                r = run_chunk(pts, gidx, idxs, cp, pad)
                if r is not None:
                    joined += r[0]; miss += r[1]; widened += k > 0
                    break
            else:
                refused += 1
                miss += sum(1 for i in idxs if gidx[i] is None)
    if miss > MAX_MISS_SHARE * total:
        raise SystemExit(f"[strip-seam] FATAL: {miss} of {total} seam points missed the terrain or failed to join "
                         f"(local scope, {refused} chunks refused {why}; off the terrain {len(lost_at)}, first {lost_at[:4]}; joins failed "
                         f"{len(failed_at)}, first {failed_at[:4]}; by 100 m cell {_cells(failed_at)}); loop.blend not saved")
    keep = [fi for fi in range(len(faces)) if alive[fi]]
    used = sorted({gi for fi in keep for gi in faces[fi]})
    lost = n0 - sum(1 for gi in used if gi < n0)
    if lost:
        raise SystemExit(f"[strip-seam] FATAL: local scope dropped {lost} terrain vertices; loop.blend not saved")
    remap = {gi: k for k, gi in enumerate(used)}
    nm = bpy.data.meshes.new("TERRAIN_seam")
    nm.from_pydata([co[gi] for gi in used], [], [tuple(remap[gi] for gi in faces[fi]) for fi in keep])
    for m in me.materials:
        nm.materials.append(m)
    nm.polygons.foreach_set("material_index", [mats[fi] for fi in keep])
    nm.polygons.foreach_set("use_smooth", [smooth[fi] for fi in keep])
    nm.update()
    old_name = me.name
    terr.data = nm
    bpy.data.meshes.remove(me)
    nm.name = old_name
    print(f"[strip-seam] local scope: {total} seam points {INSET_M} m inside the strip's outer lip in {chunks} chunks of "
          f"<= {CHUNK_ROWS} ({widened} widened, {refused} refused), {joined} joins ({knifed[0]} knifed face by face), {miss} missed; {dup[0]} duplicate "
          f"terrain faces dropped; "
          f"TERRAIN {n0} -> {len(nm.vertices)} verts; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()

"""Through-mouth CORNER RETURNS into loop.blend (ledger 0086; opt-in by track.config.json route.mouth_returns).

The reasons and the pure geometry are tools/mouth_returns.py and tools/stub_geom.py (Lake Murray's stub returns, ledger
0054 Phase 5, whose author stage this follows step for step). Runs INSIDE Blender after lm_pads and BEFORE strip_seam
and gap_mouths (both read data/mouth_returns.json; gap_mouths keys on the assembler's CURB vertex order, so this pass
never deletes or reorders a vertex: it appends after every block and removes faces FACES_ONLY, as the stubs do):

    blender --background --python-exit-code 1 --python tools/mouth_returns_blend.py -- <project>

Per mouth whose piece starts with a declared prefix, per corner (the street's two edges):
  1. K: the street's road edge line (fitted on its rows EDGE_FIT_FROM_M-EDGE_FIT_TO_M out, past the weld's re-spread)
     meets the host's road edge (its ROAD rows on the mouth side). a: along the host's edge away from the street.
  2. R: the corner's measured radius (route.mouth_radii_file, tools/mouth_radii.py), else the median of the measured
     ones on the same host, else of all (logged as such). tH = R / tan(phi / 2), iterated on the host edge's own
     curve; A* the point tH along the host edge from K; A the host's curb row just past A* (it keeps its faces).
  3. THE RETURN STRIP -> CURB (appended): A (the host row, exact) -> A* (A's profile, at A*) -> the arc tangent to the
     host edge at A* and the street edge at B -> J (the street's first curb row past B, exact); the track's own edge
     profile all the way (stub_geom.return_stations(meet_h=None)). The street's curb faces before J go, FACES_ONLY.
  4. THE CORNER PAVEMENT -> ROAD (appended): the fan from K over the arc (stub_geom.corner_pavement), its two straight
     sides ON the host and street edges, its edge heights the host deck and the street edge blended by distance.
  5. GROUND in each corner zone (within tH + ZONE_PAD_M of K, never inside the host's pavement + HOST_KEEP_M): TERRAIN
     edges halved down to TERRAIN_EDGE_M, then every vertex under the fan, the return, the street's kept strip and road,
     the host's strip past A pinned under it (seat_terrain's rule, as the stubs: deck - 0.16 under pavement and the flat
     band, the strip's own surface - 0.02 under its graded part). strip_seam then seams the ground along the return's
     lip (strip_seam.connectors), so no ground triangle spans it, and the prep places every vertex.

Writes data/mouth_returns.json: per mouth the host rows gap_mouths opens on its side (the returns' A rows replace
gap_window's GAP_CORNER_M on a built corner), the paint window (road_markings.gap_mouths), per corner K / A* / B / J,
the radius and where it came from, tangent, wedge, the lip points strip_seam seams, the street rows whose strip faces
went; the corners NOT built and why. Exit 1 (loop.blend NOT saved) when the layout contract breaks or the radii file is
missing; a corner that cannot be built honestly (a wedge outside 20-160 deg, a return longer than its street, a host
strip a pad already cut) is skipped and listed, and verify_mouth_corners judges what that leaves.
Idempotent per assembler run: a second run on the same loop.blend is refused (CURB carries the stamp). With no
route.mouth_returns it removes a stale data/mouth_returns.json and exits 0 without opening loop.blend.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_returns as mr  # noqa: E402
import mouth_weld as mw  # noqa: E402
import stub_geom as sg  # noqa: E402

STAMP = "mouth_returns"
TERRAIN_EDGE_M = 0.75      # as tools/author_stubs_blend.py
ZONE_PAD_M = 3.5           # as tools/author_stubs_blend.py: the strip's 1.8 m + its verge, and the refined ring past it
HOST_KEEP_M = 0.3          # as tools/author_stubs_blend.py: the host's own deck is the prep's to seat
PIN_UNDER_M = 0.16         # seat_terrain: deck - LIFT 0.10 - CLEAR_M 0.06
VERGE_UNDER_M = 0.02
HEAD_MIN_M = 1.0           # [invented] a compressed return's straight head A -> A* is at least this long (a taper, not a step)
HASH_M = 16.0


def B(p):
    return (p[0], p[2], p[1])


def E(v):
    return (v[0], v[2], v[1])


def _box(t):
    return (min(p[0] for p in t), max(p[0] for p in t), min(p[2] for p in t), max(p[2] for p in t))


class Skip(Exception):
    pass


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    prefixes, radii_rel = mr.config(cfg)
    outp = proj / mr.RETURNS_FILE
    if not prefixes:
        if outp.exists():
            outp.unlink()
        print("[returns] no route.mouth_returns — nothing to author")
        return
    radii = mr.load_radii(proj, radii_rel)
    if radii is None:
        raise SystemExit(f"[returns] FATAL: route.mouth_returns declared but {radii_rel} is not in the project (sync it in)")
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    lay = mw.mesh_layout(main_pts, conns)
    hosts = {"MAINLINE": main_pts}
    hosts.update({c["name"]: [tuple(p) for p in c["points_xyz_m"]] for c in conns})
    welds = {(w["piece"], w.get("end")): w for w in
             json.loads((data / "mouth_welds.json").read_text(encoding="utf-8"))["mouths"]}

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    road, curb, terr = (bpy.data.objects.get(n) for n in ("ROAD", "CURB", "TERRAIN"))
    if road is None or curb is None or terr is None:
        raise SystemExit("[returns] FATAL: loop.blend lacks ROAD / CURB / TERRAIN")
    if STAMP in curb.keys():
        raise SystemExit("[returns] FATAL: loop.blend already carries the mouth returns (CURB stamp) — rebuild it first")
    RV = [E(v.co) for v in road.data.vertices]
    CV = [E(v.co) for v in curb.data.vertices]
    # ROAD: the assembler's rows first, untouched; densify_ribbon (a draft step before this one) APPENDS its re-cut
    # columns' vertices after them (bm.verts.new, faces removed FACES_ONLY), so only fewer than the layout is a break
    if len(RV) < lay["_road_total"]:
        raise SystemExit(f"[returns] FATAL: ROAD {len(RV)} verts, fewer than the assembler's layout {lay['_road_total']}")
    if len(CV) != lay["_curb_total"]:
        raise SystemExit(f"[returns] FATAL: CURB {len(CV)} verts, the assembler's layout says {lay['_curb_total']}")
    # (route.strip_under_road, 0.2.7's m7a-m7c: strip faces under another road's pavement removed; measured to move none
    # of its targets, the pad deck edges and grid_primary_7, so dropped for m7d: ledger 0086)
    faced = set()
    for poly in curb.data.polygons:
        faced.update(poly.vertices)

    new_road_v, new_road_f = [], []
    new_curb_v, new_curb_f = [], []
    doomed = []                     # (frozenset of the 8 CURB indices of a street strip quad pair) to remove
    removed = {}                    # (piece, e) -> street rows whose strip faces go (actual row indices)
    zones = []
    out = {"version": 1, "prefixes": prefixes, "radii_file": radii_rel, "mouths": [], "skipped": []}
    n_meas = n_med = 0
    hrows_cache = {}

    skip_named = mr.skip_list(cfg)
    for mo in mouths:
        if not mr.selected(mo, prefixes):
            continue
        piece, end, host = mo["piece"], mo["end"], mo["host"]
        if (piece, end) in skip_named:
            out["skipped"].append({"mouth": f"{piece}({end})->{host}",
                                   "why": f"route.mouth_returns_skip: {skip_named[(piece, end)]}"})
            print(f"[returns] {piece}({end}) -> {host}: NOT built (route.mouth_returns_skip)")
            continue
        if piece not in lay or host not in lay or "host_seg" not in mo:
            out["skipped"].append({"mouth": f"{piece}({end})->{host}", "why": "not in the mesh layout / no host_seg"})
            continue
        pb, hb = lay[piece], lay[host]
        nrows, mh = pb["rows"], hb["rows"]
        hpts = hosts[host]
        closed = mw.is_closed(hpts)
        side = int(mo["side"])
        rid = (lambda r, _n=nrows: r) if end == "start" else (lambda r, _n=nrows: _n - 1 - r)
        rows = [tuple(RV[mw.road_index(lay, piece, rid(r), k)] for k in range(3)) for r in range(nrows)]
        arcs = mw.arc_lengths([r[1] for r in rows])
        if host not in hrows_cache:
            hrows_cache[host] = [tuple(RV[mw.road_index(lay, host, r, k)] for k in range(3)) for r in range(mh)]
        hrows = hrows_cache[host]
        host_lane = 0 if side == 1 else 2
        hedge = [r[host_lane] for r in hrows]
        hdeck = mw.HostDeck(hrows, mw.host_window(hrows, closed, mo["cut_xyz"][0], mo["cut_xyz"][2]))
        harc = mr.host_arcs(hpts, mh, closed)
        lap = harc[mh] if closed else None
        seg0 = int(mo["host_seg"])
        jn = min(seg0 + 1, len(harc) - 1)
        c_arc = harc[seg0] + (harc[jn] - harc[seg0]) * float(mo["host_t"])
        S_def = mw.gap_window(hpts, mh, closed, seg0, float(mo["host_t"]), float(mo["connector_width_m"]),
                              float(mo.get("angle_deg") or 90.0))
        offs_def = [mr.signed_off(harc[q], c_arc, lap) for q in S_def]
        win = {-1: min([o for o in offs_def if o <= 0] or [0.0]), 1: max([o for o in offs_def if o >= 0] or [0.0])}
        paint = {-1: -(float(mo["connector_width_m"]) / 2.0), 1: float(mo["connector_width_m"]) / 2.0}
        w_ = welds.get((piece, end)) or welds.get((piece, None))
        jw = int(w_["rows_respread"]) if w_ else 0
        rec_m = {"piece": piece, "end": end, "host": host, "side": side, "cut_arc_m": round(c_arc, 3), "corners": []}
        sedge_all = {}
        for e in (1, -1):
            lane = 0 if e == 1 else 2
            key = mr.corner_key(piece, end, e)
            try:
                j1 = next((r for r, a in enumerate(arcs) if a >= mr.EDGE_FIT_FROM_M), None)
                if j1 is None:
                    raise Skip("the street is shorter than its edge fit")
                j1 = max(j1, jw)
                j2 = max(r for r, a in enumerate(arcs) if a <= max(arcs[j1] + 1e-6, mr.EDGE_FIT_TO_M))
                if j2 - j1 < mr.EDGE_FIT_ROWS:
                    raise Skip(f"only {j2 - j1} rows to fit the street's edge on")
                E1, E2 = rows[j1][lane], rows[j2][lane]
                bdir = sg.unit2(E2[0] - E1[0], E2[2] - E1[2])
                back = (-bdir[0], -bdir[1])
                Kp, Kq, Kt, best_s = None, None, None, None
                for q in range(seg0 - 40, seg0 + 41):
                    if closed:
                        qq = q % mh
                    elif 0 <= q < mh - 1:
                        qq = q
                    else:
                        continue
                    a_, c_ = hedge[qq], hedge[(qq + 1) % mh]
                    hit = sg.line_seg_intersect(E1, back, a_, c_)
                    if hit is not None and hit[2] >= 0 and (best_s is None or hit[2] < best_s):
                        best_s = hit[2]
                        Kp = (hit[0], a_[1] + (c_[1] - a_[1]) * hit[3], hit[1])
                        Kq, Kt = qq, hit[3]
                if Kp is None:
                    raise Skip("its road edge line never meets the host edge")
                lat = sg.unit2(rows[j1][lane][0] - rows[j1][1][0], rows[j1][lane][2] - rows[j1][1][2])
                a0, a1 = hedge[Kq], hedge[(Kq + 1) % mh]
                dirn = 1 if (a1[0] - a0[0]) * lat[0] + (a1[2] - a0[2]) * lat[1] > 0 else -1
                R, src = mr.radius_for(radii, key, host)
                if R is None:
                    raise Skip("no radius (none measured)")
                # tH so that the circle tangent at A* (chord K -> A*) has radius R, on the host edge's own curve
                cphi = max(-1.0, min(1.0, dirn * ((a1[0] - a0[0]) * bdir[0] + (a1[2] - a0[2]) * bdir[1])
                                     / max(1e-9, math.hypot(a1[0] - a0[0], a1[2] - a0[2]))))
                tH = R / math.tan(max(1e-3, math.acos(cphi)) / 2.0)
                walked = None
                for _it in range(4):
                    walked = mr.walk_polyline(hedge, closed, Kq, Kt, tH, dirn)
                    if walked is None:
                        raise Skip(f"the return (tangent {tH:.1f} m) runs off the host's end")
                    _tH, phi, Rc, _O, _a, _B = sg.corner(Kp, walked[0], bdir)
                    if abs(Rc - R) < 0.01:
                        break
                    tH = tH * R / max(1e-6, Rc)
                Astar, qA, tA = walked
                tH_c, phi, Rc, _O, _a, Bp = sg.corner(Kp, Astar, bdir)
                # A: the host curb row just past A*, away from the mouth
                kA = (qA + 1) % mh if dirn > 0 else qA
                if tA == 0.0 and dirn > 0:
                    kA = qA
                if not closed and not 0 <= kA < mh:
                    raise Skip("the host ends inside the return")

                def crow(name, r, s_):
                    return tuple(CV[mw.curb_index(lay, name, r, s_, p)] for p in range(4))
                A_row = crow(host, kA, side)
                if mw.curb_index(lay, host, kA, side, 0) not in faced:
                    raise Skip(f"the host's strip at row {kA} is already cut (a pad)")
                head = sg.dist2(A_row[0], Astar)
                oA = [sg.dist2(A_row[p], A_row[0]) for p in range(4)]
                hA = [A_row[p][1] - A_row[0][1] for p in range(4)]
                nout = sg.unit2(A_row[3][0] - A_row[0][0], A_row[3][2] - A_row[0][2])
                Astar_row = tuple((Astar[0] + nout[0] * oA[p], Astar[1] + hA[p], Astar[2] + nout[1] * oA[p])
                                  for p in range(4))
                # J: the street's first curb row at or past B
                J = None
                for r in range(nrows):
                    p0 = CV[mw.curb_index(lay, piece, rid(r), e, 0)]
                    if (p0[0] - Kp[0]) * bdir[0] + (p0[2] - Kp[2]) * bdir[1] >= tH_c + 0.05:
                        J = r
                        break
                if J is None or J > nrows - 1 - mr.MIN_TAIL_ROWS:
                    raise Skip(f"the return (tangent {tH_c:.2f} m) runs past the street")
                gone = {rid(r) for r in range(J)}
                if gone & removed.get((piece, e), set()):
                    raise Skip("the street's other end's return already took these rows")
                J_row = crow(piece, rid(J), e)
                scale = sg.walk_scale(Astar_row, J_row, Kp, bdir)
                # a compressed walk (a small radius: the strip's 1.8 m does not fit inside COMPRESS_R x R) tapers along a
                # straight head of at least HEAD_MIN_M: A moves out a host row at a time until it has one
                for _k in range(4):
                    if scale >= 1.0 or head >= HEAD_MIN_M:
                        break
                    kA = kA + dirn
                    if closed:
                        kA %= mh
                    elif not 0 <= kA < mh:
                        raise Skip("the host ends inside a compressed return's head")
                    if mw.curb_index(lay, host, kA, side, 0) not in faced:
                        raise Skip(f"the host's strip at row {kA} is already cut (a pad)")
                    A_row = crow(host, kA, side)
                    head = sg.dist2(A_row[0], Astar)
                if scale < 1.0 and head < HEAD_MIN_M:
                    raise Skip(f"a compressed walk (x{scale:.2f}) with a {head:.2f} m head")
                sedge = [rows[r][lane] for r in range(nrows)]

                def y0_of(x, z, _se=sedge, _hd=hdeck, _side=side):
                    a_ = max(0.0, _hd.edge_gap(x, z, _side, 0.0))
                    best = None
                    for q in range(min(len(_se) - 1, J + 6)):
                        p0, p1 = _se[q], _se[q + 1]
                        dx, dz = p1[0] - p0[0], p1[2] - p0[2]
                        L2 = dx * dx + dz * dz
                        if L2 < 1e-12:
                            continue
                        t = max(0.0, min(1.0, ((x - p0[0]) * dx + (z - p0[2]) * dz) / L2))
                        d = math.hypot(x - (p0[0] + dx * t), z - (p0[2] + dz * t))
                        if best is None or d < best[0]:
                            best = (d, p0[1] + (p1[1] - p0[1]) * t)
                    b_, ys = best
                    yh = _hd.at(x, z)
                    return yh if a_ + b_ < 1e-9 else (b_ * yh + a_ * ys) / (a_ + b_)
                stations, rec = sg.return_stations(Astar_row, J_row, Kp, bdir, y0_of=y0_of, meet_h=None)
            except (Skip, sg.GeomError) as ex:
                out["skipped"].append({"corner": key, "host": host, "why": str(ex)})
                print(f"[returns] {key} -> {host}: NOT built: {ex}")
                continue
            strip = ([A_row] if head > 0.02 else []) + list(stations)
            base = len(CV) + len(new_curb_v)
            for row in strip:
                new_curb_v.extend(row)
            new_curb_f.extend(sg.strip_faces(len(strip), base))
            pv, pt = sg.corner_pavement(Kp, Kp[1], stations, rec["n_arc_rows"])
            rb = len(RV) + len(new_road_v)
            new_road_v.extend(pv)
            new_road_f.extend(tuple(rb + i for i in t) for t in pt)
            for r in range(J):
                doomed.append(frozenset(mw.curb_index(lay, piece, rr, e, p) for rr in (rid(r), rid(r + 1))
                                        for p in range(4)))
            removed.setdefault((piece, e), set()).update(gone)
            if src == "measured":
                n_meas += 1
            else:
                n_med += 1
            # the host's window on this side ends at A (its row keeps its faces outward); the paint at A*
            win[dirn] = mr.signed_off(harc[kA], c_arc, lap)
            arcA = harc[qA] + (harc[min(qA + 1, len(harc) - 1)] - harc[qA]) * tA
            paint[dirn] = mr.signed_off(arcA, c_arc, lap)
            rec.update({"e": e, "key": key, "dir": dirn, "radius_src": src, "radius_m": round(R, 3),
                        "A_row": kA, "head_m": round(head, 3), "J_row_from_mouth": J, "street_rows_removed": J,
                        "Astar": [round(Astar[0], 3), round(Astar[2], 3)],
                        "lip_xz": [[round(r[3][0], 4), round(r[3][2], 4), round(r[0][0], 4), round(r[0][2], 4)]
                                   for r in strip],
                        "new_curb_v": [base, base + 4 * len(strip)]})
            rec_m["corners"].append(rec)
            sedge_all[e] = sedge
            # ground zone
            reach = tH_c + ZONE_PAD_M
            ptris = [(pv[t[0]], pv[t[1]], pv[t[2]]) for t in pt]
            wtris, vtris = [], []

            def band(rows_, _w=wtris, _v=vtris):
                for r0, r1 in zip(rows_, rows_[1:]):
                    dy = min(r0[0][1], r1[0][1])
                    for p in range(3):
                        quad = (r0[p], r0[p + 1], r1[p + 1], r1[p])
                        tl = [(quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])]
                        if p == 2:
                            _v.extend(tl)
                        else:
                            _w.extend((t_, dy) for t_ in tl)

            def within(row, _K=Kp, _r=reach):
                return any(math.hypot(q[0] - _K[0], q[2] - _K[2]) <= _r for q in row)
            band(strip)
            s_rows = [crow(piece, rid(r), e) for r in range(J, nrows)]
            s_rows = s_rows[:next((k for k, rw in enumerate(s_rows) if not within(rw)), len(s_rows)) + 1]
            band(s_rows)
            h_rows = []
            for k in range(0, 24):
                r = kA + dirn * k
                if closed:
                    r %= mh
                elif not 0 <= r < mh:
                    break
                rw = crow(host, r, side)
                h_rows.append(rw)
                if not within(rw):
                    break
            band(h_rows)
            for r0, r1 in zip(rows, rows[1:]):
                if within(r0) or within(r1):
                    ptris += [(r0[0], r0[1], r1[1]), (r0[0], r1[1], r1[0]), (r0[1], r0[2], r1[2]), (r0[1], r1[2], r1[1])]
            zones.append({"pave": ptris, "walk": wtris, "verge": vtris, "centre": (Kp[0], Kp[2]), "reach": reach,
                          "host": hdeck})
        if rec_m["corners"]:
            opened = mr.rows_between(harc, mh, closed, c_arc, win[-1], win[1])
            rec_m["host_rows_opened"] = sorted(opened)
            rec_m["window_off_m"] = [round(win[-1], 3), round(win[1], 3)]
            rec_m["paint_window_off"] = [round(paint[-1], 3), round(paint[1], 3)]
            out["mouths"].append(rec_m)

    # ---- apply: the street strips' faces before J go (FACES_ONLY), the returns and fans appended
    for ob, nv, nf, dl in ((curb, new_curb_v, new_curb_f, doomed), (road, new_road_v, new_road_f, [])):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        if dl:
            idx_all = set().union(*dl)
            gone_f = []
            for f in bm.faces:
                ids = frozenset(v.index for v in f.verts)
                if ids <= idx_all and any(ids <= w for w in dl):
                    gone_f.append(f)
            bmesh.ops.delete(bm, geom=gone_f, context="FACES_ONLY")
            out["street_strip_faces_removed"] = len(gone_f)
        n0 = len(CV) if ob is curb else len(RV)
        if len(bm.verts) != n0:
            raise SystemExit(f"[returns] FATAL: {ob.name} vertex count moved under this pass")
        for p in nv:
            bm.verts.new(B(p))
        bm.verts.ensure_lookup_table()
        for f in nf:
            bm.faces.new([bm.verts[i] for i in f])
        bm.normal_update()
        flip = [f for f in bm.faces if min(v.index for v in f.verts) >= n0 and f.normal.z < 0]
        if flip:
            bmesh.ops.reverse_faces(bm, faces=flip)
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    out["orphan_curb_verts"] = sorted({i for w in doomed for i in w})

    # ---- ground under the corners (zones hashed by HASH_M cells)
    for z_ in zones:
        z_["pave"] = [(t, _box(t)) for t in z_["pave"]]
        z_["verge"] = [(t, _box(t)) for t in z_["verge"]]
        z_["walk"] = [(t, dy, _box(t)) for t, dy in z_["walk"]]
    zh = {}
    for i, z_ in enumerate(zones):
        cx, cz, r = z_["centre"][0], z_["centre"][1], z_["reach"]
        for gx in range(int(math.floor((cx - r) / HASH_M)), int(math.floor((cx + r) / HASH_M)) + 1):
            for gz in range(int(math.floor((cz - r) / HASH_M)), int(math.floor((cz + r) / HASH_M)) + 1):
                zh.setdefault((gx, gz), []).append(i)

    def zones_at(x, z):
        return [zones[i] for i in zh.get((int(math.floor(x / HASH_M)), int(math.floor(z / HASH_M))), ())
                if math.hypot(x - zones[i]["centre"][0], z - zones[i]["centre"][1]) <= zones[i]["reach"]]
    tbm = bmesh.new()
    tbm.from_mesh(terr.data)
    halved = 0
    for _round in range(6):
        todo = []
        for ed in tbm.edges:
            mx = 0.5 * (ed.verts[0].co.x + ed.verts[1].co.x)
            mz = 0.5 * (ed.verts[0].co.y + ed.verts[1].co.y)
            if (int(math.floor(mx / HASH_M)), int(math.floor(mz / HASH_M))) not in zh:
                continue
            if ed.calc_length() <= TERRAIN_EDGE_M:
                continue
            if zones_at(mx, mz):
                todo.append(ed)
        if not todo:
            break
        halved += len(todo)
        bmesh.ops.subdivide_edges(tbm, edges=todo, cuts=1, use_grid_fill=True)
    pinned = 0
    for v in tbm.verts:
        x, z, y = v.co.x, v.co.y, v.co.z
        if (int(math.floor(x / HASH_M)), int(math.floor(z / HASH_M))) not in zh:
            continue
        top = None
        for z_ in zones_at(x, z):
            if z_["host"].inside(x, z, -HOST_KEEP_M):
                continue
            for kind, under in (("pave", PIN_UNDER_M), ("verge", VERGE_UNDER_M)):
                for t, bx in z_[kind]:
                    if not (bx[0] <= x <= bx[1] and bx[2] <= z <= bx[3]):
                        continue
                    h = sg.tri_height(x, z, *t)
                    if h is not None:
                        top = h - under if top is None else min(top, h - under)
            for t, dy, bx in z_["walk"]:
                if bx[0] <= x <= bx[1] and bx[2] <= z <= bx[3] and sg.tri_height(x, z, *t) is not None:
                    top = dy - PIN_UNDER_M if top is None else min(top, dy - PIN_UNDER_M)
        if top is not None and y > top:
            v.co.z = top
            pinned += 1
    tbm.to_mesh(terr.data)
    tbm.free()
    terr.data.update()
    out["terrain"] = {"edges_halved": halved, "verts_pinned": pinned}
    built = sum(len(m["corners"]) for m in out["mouths"])
    out["summary"] = {"mouths": len(out["mouths"]), "corners_built": built, "radius_measured": n_meas,
                      "radius_median": n_med, "corners_skipped": len(out["skipped"])}
    curb[STAMP] = built
    (data / "mouth_returns.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[returns] {built} corner return(s) at {len(out['mouths'])} mouth(s) (radius measured {n_meas}, a median "
          f"{n_med}); {len(out['skipped'])} skipped; {len(new_curb_v) // 4} return stations, {len(new_road_f)} corner "
          f"pavement tris, {out.get('street_strip_faces_removed', 0)} street strip faces removed; ground: {halved} edges "
          f"halved, {pinned} verts pinned; saved loop.blend")


main()

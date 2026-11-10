"""Gap the HOST road's curb+sidewalk strip across every connector mouth — the other half of C2.

tools/trim_connectors.py cuts side streets at the pavement edge of the road they join (the
mainline or a divided trunk) and records each mouth in data/mouths.json. The host's own
`curb_sidewalk` strip still runs unbroken across that mouth (the sweep has no concept of other
roads, ledger 0036), so the side street butts into a raised sidewalk. This removes the strip's
faces across each mouth on the connector's side.

WINDOW (2026-10-11): along the host, centred on the station the CUT projects onto (mouths.json host_seg +
host_t), half-length = connector half-width / sin(junction angle) + CORNER_M — a connector meeting its host at
76.9 deg spans 2.9 % more host than its width (it was sized as if square, in whole 3 m vertices around the
host vertex nearest the first DROPPED point). Measured as arc length on the host, not a vertex count, and the
first station past each end joins the set — a face goes only when both its stations are in it, so the gap used to
stop at the last station INSIDE the window: on the Del Cerro W mouth College's raised sidewalk stood 0.8 m onto the
connector's corner (tools/mouth_weld.gap_window). The SIDE is the approach's (tools/trim_connectors.py since
2026-10-11: medium#2+0#0 at del_cerro_blvd#1 v82 had the wrong sidewalk gapped). A mouth record without host_seg
(an older mouths.json) keeps the old vertex window.

Runs INSIDE Blender, AFTER build_loop_blend + author_median_blend, BEFORE the kn5 prep:

    blender --background --python tools/gap_mouths_blend.py -- <project-dir>

CURB vertex layout (ribbon.curb_sidewalk, scripts-v021/geometry/ribbon.py:139-163, and the
assembler's append order build_loop_blend.py:658/677): the ring strip first — side +1 (left of
travel) stations 0..m-1 as 4 verts each, then side -1 — then one such block per connector IN
connectors.local.json ORDER (m = n-1 when the polyline is closed), then whatever author_median
joined. Every strip face uses verts of one station pair on one side, so host-face identification by
vertex index is exact. The layout is asserted on the ring before anything is touched.
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

CORNER_M = mw.GAP_CORNER_M
P = 4


def _closed(pts):
    return abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]

    # host blocks: name -> (block_start, m, closed, pts)
    blocks = {}
    main_pts = local["points_xyz_m"]
    m0 = len(main_pts) - 1 if _closed(main_pts) else len(main_pts)
    blocks["MAINLINE"] = (0, m0, _closed(main_pts), main_pts)
    start = 2 * m0 * P
    for c in conns:
        pts = c["points_xyz_m"]
        mc = len(pts) - 1 if _closed(pts) else len(pts)
        blocks[c["name"]] = (start, mc, _closed(pts), pts)
        start += 2 * mc * P

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb = bpy.data.objects.get("CURB")
    if curb is None:
        raise SystemExit("[gap-mouths] no CURB object")
    me = curb.data
    if len(me.vertices) < start:
        raise SystemExit(f"[gap-mouths] CURB has {len(me.vertices)} verts < expected blocks {start}")

    def _lat(vi, pts, k):
        v = me.vertices[vi].co
        a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1e-9
        return (-(tz / L) * (v.x - pts[k][0]) + (tx / L) * (v.y - pts[k][2]))
    l0, r0 = _lat(0, main_pts, 0), _lat(m0 * P, main_pts, 0)
    if not (l0 > 0 > r0):
        raise SystemExit(f"[gap-mouths] ring layout assertion failed: side+1 lat {l0:.2f}, side-1 lat {r0:.2f}")

    # ledger 0086 (opt-in, route.mouth_returns): a mouth with corner returns (tools/mouth_returns_blend.py) opens the
    # host's strip exactly to the returns' A rows (data/mouth_returns.json host_rows_opened), not gap_window's
    # GAP_CORNER_M; and the street strip vertices the returns orphaned are deleted once the faces have gone
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    returns = mr.load_returns(proj) if mr.config(cfg)[0] else None
    ret_open = {(m_["piece"], m_["end"]): set(m_["host_rows_opened"]) for m_ in (returns or {}).get("mouths", [])}
    ret_paint = {(m_["piece"], m_["end"]): m_ for m_ in (returns or {}).get("mouths", [])}

    # gap windows per (host, side)
    gaps = {}
    for mo in mouths:
        host = mo["host"]
        if host not in blocks:
            print(f"[gap-mouths] WARNING: mouth host '{host}' not in the CURB block table — skipped")
            continue
        _, mh, closed, hpts = blocks[host]
        s = gaps.setdefault((host, int(mo["side"])), set())
        if (mo.get("piece"), mo.get("end")) in ret_open:
            s.update(ret_open[(mo["piece"], mo["end"])])
            continue
        if "host_seg" not in mo:
            k = int(mo["host_vertex"])
            nv = int(math.ceil((mo["connector_width_m"] / 2.0 + CORNER_M) / 3.0))
            for q in range(k - nv, k + nv + 1):
                s.add(q % mh if closed else max(0, min(mh - 1, q)))
            continue
        for q in mw.gap_window(hpts, mh, closed, int(mo["host_seg"]), float(mo["host_t"]),
                              float(mo["connector_width_m"]), float(mo.get("angle_deg") or 90.0)):
            s.add(q)
    # ledger 0054 P1 fix round (opt-in: data/aprons.json, written by tools/author_aprons_blend.py only when
    # track.config.json route.aprons declares one): a corner apron opens the host's walk from P0's row to the row its
    # return curb meets (E_row) — the host's own curb resumes exactly there, at the return curb's last station
    n_apron = 0
    ap_path = data / "aprons.json"
    if ap_path.exists():
        for ap in json.loads(ap_path.read_text(encoding="utf-8")).get("aprons", []):
            host = ap["host"]
            if host not in blocks:
                raise SystemExit(f"[gap-mouths] apron {ap['id']}: host {host!r} not in the CURB block table")
            _, mh, closed, _hp = blocks[host]
            lo, hi = int(ap["host_rows_opened"][0]), int(ap["host_rows_opened"][1])
            s = gaps.setdefault((host, int(ap["side"])), set())
            for q in range(lo, hi + 1):
                s.add(q % mh if closed else max(0, min(mh - 1, q)))
            n_apron += 1
    print(f"[gap-mouths] {len(mouths)} mouths on {sorted({h for h, _ in gaps})}"
          + (f"; {n_apron} apron(s) open the host's walk to their return curb" if n_apron else ""))

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    orphans = [bm.verts[i] for i in (returns or {}).get("orphan_curb_verts", []) if i < len(bm.verts)]
    doomed = []
    for f in bm.faces:
        idx = [v.index for v in f.verts]
        lo, hi = min(idx), max(idx)
        for (host, side), stations in gaps.items():
            bstart, mh, _, _ = blocks[host]
            side_base = bstart + (0 if side == 1 else mh * P)
            side_end = side_base + mh * P
            if lo >= side_base and hi < side_end:
                st = {((i - side_base) // P) for i in idx}
                if st <= stations:
                    doomed.append(f)
                    break
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    n_orph = 0
    if orphans:
        loose = [v for v in orphans if v.is_valid and not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        n_orph = len(loose)
    bm.to_mesh(me)
    bm.free()
    me.update()
    n_paint = gap_paint(proj, cfg, mouths, blocks, ret_paint) if (cfg.get("road_markings") or {}).get("gap_mouths") else None
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[gap-mouths] deleted {len(doomed)} host curb/sidewalk faces across {len(mouths)} mouths"
          + (f"; {n_orph} street strip vertices the corner returns orphaned deleted" if orphans else "")
          + (f"; {n_paint}" if n_paint is not None else "") + "; saved loop.blend")


PAINT_BAND_M = (-1.2, 0.3)   # [invented] the host's edge line (lane_markings edge_inset 0.55 m, 0.12 m wide) lies in this
#                              band of b (m past the host's pavement edge on the mouth side; - = on the host)
PAINT_PARALLEL = 0.8         # [invented] a face whose long side runs within ~37 deg of the host is the host's line


def gap_paint(proj, cfg, mouths, blocks, ret_paint):
    """road_markings.gap_mouths (ledger 0086, opt-in): the host's white edge line broken at every mouth, as real paint is.
    Kevin's grid streets had it painted across 93 of 113 openings (build_loop_blend.py lane_markings sweeps it along the
    whole host; nothing gapped it). Per mouth: the window along the host is the opening (connector half-width /
    sin(angle) either side of the cut's station), widened to the corner returns' A* where tools/mouth_returns_blend.py
    built them (mouth_returns.paint_window); MARKINGS faces in the edge band whose long side runs with the host are cut
    exactly at the window's two ends (bmesh bisect_plane, those faces only) and the pieces inside deleted. YLINE (the
    centre lines) and the connector's own paint are untouched."""
    ob = bpy.data.objects.get("MARKINGS")
    if ob is None:
        return "no MARKINGS object: no paint gapped"
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    widths = {"MAINLINE": local.get("widths_m")}
    widths.update({c["name"]: c.get("widths_m") for c in conns})
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n_del = n_mouth = 0
    HC = 8.0
    fh = {}
    for f in bm.faces:
        ce = f.calc_center_median()
        fh.setdefault((int(math.floor(ce.x / HC)), int(math.floor(ce.y / HC))), []).append(f)
    arcs = {}
    for mo in mouths:
        host = mo["host"]
        if host not in blocks or "host_seg" not in mo or not widths.get(host):
            continue
        _, mh, closed, hpts = blocks[host]
        hp = [tuple(p) for p in hpts]
        wd = widths[host]
        side = int(mo["side"])
        c, lo, hi = mr.paint_window(mo, hp, closed, ret_paint.get((mo.get("piece"), mo.get("end"))))
        seg0 = int(mo["host_seg"])
        segs = [q for q in range(seg0 - 30, seg0 + 31)]

        def frame(x, z):
            pr = mr.project_polyline(hp, closed, x, z, segs)
            if pr is None:
                return None
            _d, q, t = pr
            n = len(hp)
            a, b = hp[q], hp[(q + 1) % n]
            L = math.hypot(b[0] - a[0], b[2] - a[2]) or 1.0
            tx, tz = (b[0] - a[0]) / L, (b[2] - a[2]) / L
            lat = -tz * (x - a[0] - tx * L * t) + tx * (z - a[2] - tz * L * t)
            arc = arcs.get(host)
            if arc is None:
                arc = arcs[host] = mr.host_arcs(hp, mh, closed)
            s_ = arc[q] + (arc[min(q + 1, len(arc) - 1)] - arc[q]) * t
            w = wd[q] * (1 - t) + wd[min(q + 1, len(wd) - 1)] * t
            return mr.signed_off(s_, c, arc[mh] if closed else None), side * lat - w / 2.0, (tx, tz)
        cx, cz = mo["cut_xyz"][0], mo["cut_xyz"][2]
        reach = max(abs(lo), abs(hi)) + 16.0
        local_f = set()
        for gx in range(int(math.floor((cx - reach) / HC)), int(math.floor((cx + reach) / HC)) + 1):
            for gz in range(int(math.floor((cz - reach) / HC)), int(math.floor((cz + reach) / HC)) + 1):
                local_f.update(f for f in fh.get((gx, gz), ()) if f.is_valid)

        def cand():
            out = []
            for f in local_f:
                if not f.is_valid:
                    continue
                ce = f.calc_center_median()
                fr = frame(ce.x, ce.y)
                if fr is None or not (PAINT_BAND_M[0] <= fr[1] <= PAINT_BAND_M[1]) or not (lo - 4.0 <= fr[0] <= hi + 4.0):
                    continue
                ed = max(f.edges, key=lambda e_: e_.calc_length())
                d = ed.verts[1].co - ed.verts[0].co
                L = math.hypot(d.x, d.y) or 1.0
                if abs(d.x / L * fr[2][0] + d.y / L * fr[2][1]) < PAINT_PARALLEL:
                    continue
                out.append((f, fr))
            return out
        got = cand()
        if not got:
            continue
        for off in (lo, hi):
            # the window's end: the host point at that arc offset, the plane square to the host there
            fr0 = None
            best = None
            for f, fr in got:
                if f.is_valid and (best is None or abs(fr[0] - off) < best):
                    best, fr0 = abs(fr[0] - off), (f, fr)
            if fr0 is None:
                continue
            f, fr = fr0
            ce = f.calc_center_median()
            tx, tz = fr[2]
            co = ce.copy()
            co.x += tx * (off - fr[0])
            co.y += tz * (off - fr[0])
            geom = [g for f_, _ in got if f_.is_valid for g in list(f_.verts) + list(f_.edges) + [f_]]
            geom = list(dict.fromkeys(geom))
            vs = [g for g in geom if isinstance(g, bmesh.types.BMVert)]
            res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=(tx, tz, 0.0), dist=1e-5)
            vs += [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
            for v in vs:
                if v.is_valid:
                    for nf in v.link_faces:
                        if nf not in local_f:
                            local_f.add(nf)
                            ce_ = nf.calc_center_median()
                            fh.setdefault((int(math.floor(ce_.x / HC)), int(math.floor(ce_.y / HC))), []).append(nf)
            got = cand()
        doomed = [f for f, fr in got if lo + 1e-3 < fr[0] < hi - 1e-3]
        if doomed:
            bmesh.ops.delete(bm, geom=doomed, context="FACES")
            n_del += len(doomed)
            n_mouth += 1
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return f"the host's edge line broken at {n_mouth} mouth(s) ({n_del} paint faces inside the openings deleted)"


main()

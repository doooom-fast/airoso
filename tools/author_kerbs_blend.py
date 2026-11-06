"""Racing kerbs from the traced kerb runs, laid on the v021 ribbon's own lane edge (ledger 0078).

route.kerbs_file (a project path; tools/lm_engine_intake.py copies it from the live track: source/edges/kerbs.json, written
from the aerial by tools/aerial_edges.py and checked by eye) lists each kerb run as the lane edge it follows, in lon/lat.
Each run is keyed to THIS build's line (every traced point to its nearest mainline row; the run is the rows between the
first and the last) and swept OUTSIDE the lane edge, its base on the ROAD mesh's own edge vertex of each row (bank, weld and
all), so no kerb stands in the lane and none floats. Cross-section, metres past the edge / over the edge:

    (0, KERB_LIP_M) -> (RAMP_IN_M, h) -> (w, h) -> (w + RAMP_OUT_M, -DROP_M)

A run with "profile": "paint" (ledger 0081: flat edge stripes, e.g. High Plains' blue / yellow) is laid flat at the lip
across w, then the same back fall: no height is seen in an image, so none is built. kerb.atlas (opt-in) maps each run's
colour into its own u-cell of one 1KERB texture.

kerb.placement "measured" (opt-in, ledger 0081 round 2): each run is laid where its paint was MEASURED instead, in_m .. out_m
across the live edge it was measured on, read as an offset from THIS ribbon's lane edge (tools/kerb_section.py; at High
Plains' apexes the port's edge lies 0.5-1.1 m off the live one), so a kerb may lie over the lane: there its base is the ROAD
ribbon's own surface (a ray down within LAYER_M of the edge's height), outside the edge the edge's height as before. The
run is clipped to its measured ends (the live edge's first and last points read on the rows' edge, one row past each end,
lerped), its width is the measured one (no MAX_W_M), and kerb.end_ramp_m (opt-in) ramps the raised top down to the lip
over that length at either end.

the painted width w is the top; the back falls past it (round 4: a 0.6 m fall inside w read as one 0.12 m excursion
drop on Nevada at s 300, the kerb's back between two 0.5 m probes).

h = track.config.json kerb.height_m (the config's, NOT measured: a 1 m DEM cannot read a 5-8 cm kerb); w = the traced paint
width (out_m - in_m), clamped to [MIN_W_M, MAX_W_M]. One mesh per run, 1KERB_circuit_<k>: kerb physics, in the ROAD kn5 (a
1KERB_RACE name is race furniture: split_exports_blend routes it to the race kn5, and a track with no race layout refuses
it). Its UVs (u across, v = arc / STRIPE_M, so the texture's two bands alternate every STRIPE_M / 2 m) are the mesh's only and
active layer, UV_LAYER: engine-july's prep writes its top-down planar UVs into a layer named "UVMap" (created when absent, never
made active), and the kn5 exporter writes the ACTIVE layer, so the stripe survives the prep. The texture is the track's
(texture_overrides["1KERB"]; the ports carry no other 1KERB mesh). Self-check, exit 1 and loop.blend not saved: a run that keys to fewer than 2 rows.

kerb.race_rule (opt-in, ledger 0079 round K; Sand Creek): no traced runs — tools/race_kerbs.py writes RACE_RULE_FILE by rule
(apex + exit at each race corner), each run "edge": "ribbon" (in_m / out_m from this ribbon's own lane edge, no live edge);
kerb.surface "road_and_pads" reads the ROAD ribbon and the junction pads' decks (1ROAD_pad_*) under every offset.

    blender --background --python-exit-code 1 --python tools/author_kerbs_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kerb_section as ks  # noqa: E402
import mouth_weld as mw  # noqa: E402

KERB_LIP_M = 0.003    # [invented] the kerb's inner edge this far over the lane edge: no z-fight, no step a wheel feels
RAMP_IN_M = 0.25      # [invented] the rise from the lane edge to the kerb's top
RAMP_OUT_M = 1.0      # [invented] the fall at the back, past the paint: (h + DROP_M) / 2 per 0.5 m probe, well under
                      # drive_test's 0.12 m excursion step
DROP_M = 0.05         # [invented] the back lands this far under the lane edge (into the edge strip / ground)
MIN_W_M, MAX_W_M = 0.9, 2.0   # [invented] a traced paint width outside these is read as the reader's noise
MIN_PAINT_W_M = 0.45  # [invented] a "paint" run (flat edge stripe, ledger 0081) narrower than this is read as 1-2 px of noise
                      # at NAIP's 0.3 m; its top is the lip, flat: no height is seen in the image, so none is built
STRIPE_M = 2.0        # one white + one colour stripe; racing kerbs are painted in ~1 m blocks
LAYER_M = 2.0         # [invented] measured placement: the ROAD surface is read within this of the lane edge's height (L4)
PREFIX = "1KERB_circuit_"
RACE_RULE_FILE = "data/kerbs.race.json"   # tools/race_kerbs.py's output (kerb.race_rule, ledger 0079 round K)
UV_LAYER = "KerbUV"   # not "UVMap": the prep's planar pass writes that one


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rel = (cfg.get("route") or {}).get("kerbs_file")
    if not rel and ((cfg.get("kerb") or {}).get("race_rule")):
        rel = RACE_RULE_FILE      # kerb.race_rule (opt-in, ledger 0079 round K): the runs tools/race_kerbs.py wrote by rule
    if not rel:
        print("[kerbs] no route.kerbs_file: nothing to do")
        return
    K = json.loads((proj / rel).read_text(encoding="utf-8"))
    h = float((cfg.get("kerb") or {}).get("height_m", 0.08))
    # kerb.atlas (opt-in, ledger 0081): {colour: [u0, u1]}, one texture holding each colour pair side by side, so runs of
    # two paint schemes bind the one 1KERB row (High Plains: blue / white kerbs and blue / yellow edge stripes)
    atlas = {k: tuple(v) for k, v in ((cfg.get("kerb") or {}).get("atlas") or {}).items() if not k.startswith("_")}
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8"))["connectors"] if cp.exists() else []
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    lay = mw.mesh_layout(main_pts, conns)
    rows, closed = lay["MAINLINE"]["rows"], lay["MAINLINE"]["closed"]
    lon0, lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
    m_lon, m_lat = mpd(lat0)
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    road = bpy.data.objects.get("ROAD")
    for ob in [o for o in bpy.data.objects if o.name.startswith((PREFIX, "1KERB_RACE_"))]:
        bpy.data.objects.remove(ob, do_unlink=True)          # idempotent
    V = road.data.vertices

    def row_pts(r):
        L = V[mw.road_index(lay, "MAINLINE", r, 0)].co
        C = V[mw.road_index(lay, "MAINLINE", r, 1)].co
        R = V[mw.road_index(lay, "MAINLINE", r, 2)].co
        return L, C, R                                         # Blender frame: x = E, y = N, z = up

    centres = [row_pts(r)[1] for r in range(rows)]
    # kerb.placement "measured" (opt-in, ledger 0081 round 2): each run at its measured place across THIS ribbon's lane
    # edge (tools/kerb_section.py), its base on the ROAD ribbon's own surface where it lies over the lane
    kcfg = cfg.get("kerb") or {}
    measured = kcfg.get("placement") == "measured"
    end_ramp = float(kcfg.get("end_ramp_m") or 0.0)
    all_road = kcfg.get("surface") == "road_and_pads"
    misses = [0]
    if measured:
        from mathutils import Vector
        from mathutils.bvhtree import BVHTree
        mwr = road.matrix_world
        bvh = BVHTree.FromPolygons([mwr @ v.co for v in V], [tuple(p.vertices) for p in road.data.polygons])
        if all_road:
            # kerb.surface "road_and_pads" (opt-in, ledger 0079 round K): the ROAD ribbon AND every junction pad's deck
            # (1ROAD_pad_*, tools/lm_pads_blend.py: the lap ribbon is cut there and the measured deck stands in), read
            # on every offset of the section, the back fall too (a miss keeps the lane edge's height, as before)
            vs_, fs_ = [], []
            for ob_ in [road] + sorted((o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("1ROAD_pad_")),
                                       key=lambda o: o.name):
                base_ = len(vs_)
                vs_ += [ob_.matrix_world @ v.co for v in ob_.data.vertices]
                fs_ += [tuple(base_ + i for i in p.vertices) for p in ob_.data.polygons]
            bvh = BVHTree.FromPolygons(vs_, fs_)

        def road_z(x, y, z_edge):
            """the ROAD surface's height at (x, y), read within LAYER_M of the lane edge's height (L4: no other layer)"""
            hit = bvh.ray_cast(Vector((x, y, z_edge + LAYER_M)), Vector((0.0, 0.0, -1.0)), 2 * LAYER_M)
            if hit[0] is None:
                misses[0] += 1
                return z_edge
            return hit[0].z

    report = []
    for k, run in enumerate(K.get("kerbs", [])):
        side = 0 if run["side"] == "left" else 2
        idx = []
        for lon, lat in run["edge_lonlat"]:
            x, y = (lon - lon0) * m_lon, (lat - lat0) * m_lat
            idx.append(min(range(rows), key=lambda r: (centres[r].x - x) ** 2 + (centres[r].y - y) ** 2))
        if len(set(idx)) < 2:
            raise SystemExit(f"[kerbs] FATAL: run {k} ({run['side']} s {run['s0']}-{run['s1']}) keys to {len(set(idx))} row(s)")
        a, b = idx[0], idx[-1]
        if closed and (b - a) % rows > rows // 2:
            a, b = b, a
        span = [(a + i) % rows for i in range(((b - a) % rows if closed else b - a) + 1)]
        paint = run.get("profile") == "paint"
        k_in, k_out = float(run.get("in_m", 0.0)), float(run.get("out_m", 1.2))
        if measured:   # the measured width; only the noise floor holds (no MAX_W_M: High Plains' R s 2,892 paint is 2.85 m)
            w = max(MIN_PAINT_W_M if paint else MIN_W_M, k_out - k_in)
        else:
            w = max(MIN_PAINT_W_M if paint else MIN_W_M, min(MAX_W_M, k_out - k_in))
        live = [((lon - lon0) * m_lon, (lat - lat0) * m_lat) for lon, lat in run["edge_lonlat"]]
        u0, u1 = atlas.get(run.get("colour"), (0.0, 1.0))
        verts, faces, uvs, deltas = [], [], [], []
        P = 0
        if measured:
            # one row past each end, then the run clipped to its measured ends (the live edge's first and last points
            # read on these rows' edge): keying ends to the nearest row (~3 m apart) cut up to half a row off each end
            ext = list(span)
            if closed or span[0] > 0:
                ext.insert(0, (span[0] - 1) % rows)
            if closed or span[-1] < rows - 1:
                ext.append((span[-1] + 1) % rows)
            secs, eds = [], []
            for r in ext:
                Lp, Cp, Rp = row_pts(r)
                E = Lp if side == 0 else Rp
                ox, oy = ks.outward_unit((E.x, E.y), (Cp.x, Cp.y))   # outward, across the lane edge
                # a run authored ON the ribbon's own lane edge ("edge": "ribbon", tools/race_kerbs.py) has no live edge
                # to read an offset from: in_m / out_m are offsets from this ribbon's edge itself
                d = 0.0 if run.get("edge") == "ribbon" else ks.edge_delta((E.x, E.y), (ox, oy), live)
                off_in = k_in + d
                sec = []
                for off, dz in ks.section(off_in, off_in + w, h, paint, KERB_LIP_M, RAMP_IN_M, RAMP_OUT_M, DROP_M):
                    x, y = E.x + ox * off, E.y + oy * off
                    base = road_z(x, y, E.z) if (off < 0.0 or all_road) else E.z
                    sec.append((x, y, base, dz, (off - off_in) / w))
                secs.append((sec, d))
                eds.append((E.x, E.y))
            arcs = [0.0]
            for p0, p1 in zip(eds, eds[1:]):
                arcs.append(arcs[-1] + math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
            e0, e1 = ks.arc_of(eds, live[0]), ks.arc_of(eds, live[-1])
            s_a, s_b = min(e0, e1), max(e0, e1)
            arc = s_b - s_a
            P = len(secs[0][0])
            picks = ks.clipped_rows(arcs, s_a, s_b)
            span = picks                                            # the faces below walk these sections
            for i, j, t in picks:
                deltas.append(secs[i][1] + (secs[j][1] - secs[i][1]) * t)
                s_arc = arcs[i] + (arcs[j] - arcs[i]) * t - s_a
                scale = ks.end_scale(s_arc, arc, end_ramp)
                for (xa, ya, ba, dza, fa), (xb, yb, bb, dzb, fb) in zip(secs[i][0], secs[j][0]):
                    dz = dza + (dzb - dza) * t
                    if not paint and dz > KERB_LIP_M:              # the raised top, ramped down at the run's ends
                        dz = max(KERB_LIP_M, dz * scale)
                    verts.append((xa + (xb - xa) * t, ya + (yb - ya) * t, ba + (bb - ba) * t + dz))
                    f = fa + (fb - fa) * t
                    # an atlas cell holds its u inside [u0, u1] (the back fall past w stays in the cell)
                    uvs.append((u0 + (u1 - u0) * min(1.0, f) if atlas else f, s_arc / STRIPE_M))
        else:
            edges, arcs = [], []
            for r in span:
                Lp, Cp, Rp = row_pts(r)
                E = Lp if side == 0 else Rp
                arcs.append(0.0 if not edges else arcs[-1] + math.hypot(E.x - edges[-1][0].x, E.y - edges[-1][0].y))
                edges.append((E, Cp))
            arc = arcs[-1]
            if paint:     # flat paint on the edge (ledger 0081): the lip across the painted width, then the back fall
                prof = [(0.0, KERB_LIP_M), (w, KERB_LIP_M), (w + RAMP_OUT_M, -DROP_M)]
            else:
                prof = [(0.0, KERB_LIP_M), (RAMP_IN_M, h), (w, h), (w + RAMP_OUT_M, -DROP_M)]
            P = len(prof)
            for (E, Cp), s_arc in zip(edges, arcs):
                ox, oy = ks.outward_unit((E.x, E.y), (Cp.x, Cp.y))   # outward, across the lane edge
                for off, dz in prof:
                    verts.append((E.x + ox * off, E.y + oy * off, E.z + dz))
                    # an atlas cell holds its u inside [u0, u1] (the back fall past w stays in the cell); none: as before
                    uvs.append((u0 + (u1 - u0) * min(1.0, off / w) if atlas else off / w, s_arc / STRIPE_M))
        for i in range(len(span) - 1):
            for p in range(P - 1):
                q0, q1 = i * P + p, (i + 1) * P + p
                f = (q0, q0 + 1, q1 + 1, q1) if side == 2 else (q0, q1, q1 + 1, q0 + 1)
                faces.append(f)
        me = bpy.data.meshes.new(f"{PREFIX}{k}")
        me.from_pydata(verts, [], faces)
        me.validate(); me.update()
        uvl = me.uv_layers.new(name=UV_LAYER)
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
        ob = bpy.data.objects.new(f"{PREFIX}{k}", me)
        bpy.context.scene.collection.objects.link(ob)
        rec = {"k": k, "side": run["side"], "rows": len(span), "length_m": round(arc, 1), "width_m": round(w, 2),
               "profile": "paint" if paint else "kerb", "colour": run.get("colour")}
        if measured:
            ds = sorted(deltas)
            rec.update({"s0": run.get("s0"), "s1": run.get("s1"), "in_m": k_in, "out_m": k_out,
                        "edge_delta_m": [round(ds[0], 2), round(ds[len(ds) // 2], 2), round(ds[-1], 2)],
                        "in_vs_ribbon_edge_m": round(k_in + ds[len(ds) // 2], 2),
                        "out_vs_ribbon_edge_m": round(k_in + w + ds[len(ds) // 2], 2)})
        if run.get("rule"):
            rec["rule"] = run["rule"]                              # an authored run's rule (tools/race_kerbs.py)
        report.append(rec)
    (data / "kerbs.built.json").write_text(json.dumps(
        {"height_m": h, "placement": "measured" if measured else "outside", "end_ramp_m": end_ramp if measured else None,
         "road_misses": misses[0], "runs": report}, indent=1), encoding="utf-8")
    where = f"at their measured offsets (ROAD read missed {misses[0]})" if measured else "outside the lane edge"
    print(f"[kerbs] {len(report)} kerb runs, {sum(r['length_m'] for r in report):.0f} m, height {h} m (config), {where}; "
          f"saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()

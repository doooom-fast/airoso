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

the painted width w is the top; the back falls past it (round 4: a 0.6 m fall inside w read as one 0.12 m excursion
drop on Nevada at s 300, the kerb's back between two 0.5 m probes).

h = track.config.json kerb.height_m (the config's, NOT measured: a 1 m DEM cannot read a 5-8 cm kerb); w = the traced paint
width (out_m - in_m), clamped to [MIN_W_M, MAX_W_M]. One mesh per run, 1KERB_circuit_<k>: kerb physics, in the ROAD kn5 (a
1KERB_RACE name is race furniture: split_exports_blend routes it to the race kn5, and a track with no race layout refuses
it). Its UVs (u across, v = arc / STRIPE_M, so the texture's two bands alternate every STRIPE_M / 2 m) are the mesh's only and
active layer, UV_LAYER: engine-july's prep writes its top-down planar UVs into a layer named "UVMap" (created when absent, never
made active), and the kn5 exporter writes the ACTIVE layer, so the stripe survives the prep. The texture is the track's
(texture_overrides["1KERB"]; the ports carry no other 1KERB mesh). Self-check, exit 1 and loop.blend not saved: a run that keys to fewer than 2 rows.

    blender --background --python-exit-code 1 --python tools/author_kerbs_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
PREFIX = "1KERB_circuit_"
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
        w = max(MIN_PAINT_W_M if paint else MIN_W_M,
                min(MAX_W_M, float(run.get("out_m", 1.2)) - float(run.get("in_m", 0.0))))
        if paint:     # flat paint on the edge (ledger 0081): the lip across the painted width, then the same back fall
            prof = [(0.0, KERB_LIP_M), (w, KERB_LIP_M), (w + RAMP_OUT_M, -DROP_M)]
        else:
            prof = [(0.0, KERB_LIP_M), (RAMP_IN_M, h), (w, h), (w + RAMP_OUT_M, -DROP_M)]
        u0, u1 = atlas.get(run.get("colour"), (0.0, 1.0))
        verts, faces, uvs = [], [], []
        arc = 0.0
        prev = None
        for r in span:
            Lp, Cp, Rp = row_pts(r)
            E = Lp if side == 0 else Rp
            dx, dy = E.x - Cp.x, E.y - Cp.y
            n = math.hypot(dx, dy) or 1.0
            ox, oy = dx / n, dy / n                            # outward, across the lane edge
            if prev is not None:
                arc += math.hypot(E.x - prev.x, E.y - prev.y)
            prev = E
            for off, dz in prof:
                verts.append((E.x + ox * off, E.y + oy * off, E.z + dz))
                # an atlas cell holds its u inside [u0, u1] (the back fall past w stays in the cell); none: as before
                uvs.append((u0 + (u1 - u0) * min(1.0, off / w) if atlas else off / w, arc / STRIPE_M))
        P = len(prof)
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
        report.append({"k": k, "side": run["side"], "rows": len(span), "length_m": round(arc, 1), "width_m": round(w, 2),
                       "profile": "paint" if paint else "kerb", "colour": run.get("colour")})
    (data / "kerbs.built.json").write_text(json.dumps({"height_m": h, "runs": report}, indent=1), encoding="utf-8")
    print(f"[kerbs] {len(report)} kerb runs, {sum(r['length_m'] for r in report):.0f} m, height {h} m (config) on the lane "
          f"edge rows; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()

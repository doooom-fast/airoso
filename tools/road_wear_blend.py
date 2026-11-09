"""Road wear where tyres run, and the road's tone off the aerial, baked onto the PREPPED scene (ledger 0084).

    blender --background --python-exit-code 1 --python tools/road_wear_blend.py -- <prepped.blend> --project <proj> --eng <ENGINE>

Opt-in: only a track.config.json with a ``road_wear`` key runs it (scripts/aerial/road_wear.py has the spec, its defaults
and which of them are measured, modelled or invented). No key = nothing happens, the blend is left alone, the stale
data/road_wear.json is removed, exit 0 — Lake Murray (tools/ship_sd.sh never calls this) and every other track are
unchanged.

WHAT IT DOES, in order, on the scene engine-july's prep saved (blender/<slug>.blend, before the split):
1. the surfaces ``road_wear.surfaces`` names (1ROAD always first: its faces are "the road" for the tone and the line);
2. the atlas plan off those faces (cell size, margin = the furthest vertex of any face from its centroid, pitch, the
   power-of-two side): scripts/aerial/road_wear.plan_atlas;
3. the BUILT road rasterised at the texel; the aerial registered to it (the shift at which the photo's asphalt lines up
   with the built road, measured) and its tone read (shadows and paint filled from the lit asphalt);
4. the racing line per layout: a recorded fast_lane.ai named in ``road_wear.lines`` when it exists, else the
   minimum-curvature line inside the built road's edges [model], with the rubber intensity a friction-limited speed model
   gives it [model];
5. the macro atlas baked tile by tile from the world (tone x (1 - wear), x m0), the detail textures (each surface's own
   stock diffuse / m0 and its stock normal), a flat normal — all PNG, power of two;
6. every face's UVs rewritten into its cell's tile (detail on today's 4 m grid and phase: detailUVMultiplier);
7. each surface's material rebuilt with those five images (packed, named as their files, so the add-on embeds exactly
   them) and data/road_wear.json written: the material rows engine-july's export_kn5_addon reads (shader
   ksPerPixelMultiMap_NMDetail, the five slots, the VARs) plus every measured / chosen number;
8. the kn5 WRITER's vertex count re-checked on every surface (engine-july's own _export_vertex_keys); a surface over
   the cap is tiled under unique names by engine-july's own _split_for_writer.

SELF-CHECKS (exit 1 = the blend is not saved): every face of every surface got a tile; no vertex position changed
(hash of every surface's vertices before == after); every surface under the writer cap after the pass; every texture
power of two.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
from scripts.aerial import road_wear as rw  # noqa: E402
from scripts.ac import pbr  # noqa: E402

VERT_CAP = 65535
DETAIL_JPEG_Q = 95         # [invented] the pre-brightened detail's JPEG quality (the stock tile is itself a JPEG)


def _args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    blend = Path(a[0]).resolve()
    proj = Path(a[a.index("--project") + 1]).resolve() if "--project" in a else blend.parents[1]
    eng = Path(a[a.index("--eng") + 1]).resolve() if "--eng" in a else None
    return blend, proj, eng


def _engine_prep(eng: Path | None):
    """engine-july's prep module, loaded by path (its writer-vertex count and writer split are the ones of record)."""
    if eng is None:
        return None
    p = eng / "scripts" / "ac" / "build_kn5_loop.py"
    spec = importlib.util.spec_from_file_location("ej_build_kn5_loop", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _faces(ob):
    """(per-loop world xyz [L x 3], per-loop face index [L], face centroids [F x 3], tris [T x 3 x 3] world)."""
    me = ob.data
    mw = np.array(ob.matrix_world, dtype=np.float64)
    nv = len(me.vertices)
    co = np.empty(nv * 3); me.vertices.foreach_get("co", co); co = co.reshape(nv, 3)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    nl = len(me.loops)
    lv = np.empty(nl, dtype=np.int64); me.loops.foreach_get("vertex_index", lv)
    nf = len(me.polygons)
    ls = np.empty(nf, dtype=np.int64); me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(nf, dtype=np.int64); me.polygons.foreach_get("loop_total", lt)
    # a polygon's loops are contiguous (loop_start .. + loop_total): each loop index -> its face
    face_of_loop = np.empty(nl, dtype=np.int64)
    local = np.arange(int(lt.sum())) - np.repeat(np.cumsum(lt) - lt, lt)
    face_of_loop[np.repeat(ls, lt) + local] = np.repeat(np.arange(nf), lt)
    P = co[lv]
    cen = np.zeros((nf, 3)); np.add.at(cen, face_of_loop, P); cen /= lt[:, None]
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    tv = np.empty(nt * 3, dtype=np.int64); me.loop_triangles.foreach_get("vertices", tv)
    tris = co[tv.reshape(nt, 3)]
    return P, face_of_loop, cen, tris, co


def _hash(arrs) -> str:
    h = hashlib.md5()
    for a in arrs:
        h.update(np.round(np.asarray(a, dtype=np.float64), 6).tobytes())
    return h.hexdigest()


def _image_pixels(path: Path) -> np.ndarray:
    """RGB 0..1 float32, row 0 = TOP, read through Blender (no PIL inside Blender)."""
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
    except Exception:
        pass
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1, :, :3].copy()


def _read_ai_xyz(path: Path) -> np.ndarray:
    """A fast_lane.ai's points (kn5 frame x, y, z) -> Blender (x = E, y = N, height)."""
    import struct
    d = path.read_bytes()
    _ver, n, _lap, _samp = struct.unpack_from("<4i", d, 0)
    pts = np.array([struct.unpack_from("<3f", d, 16 + 20 * i) for i in range(n)], dtype=np.float64)
    return np.column_stack([pts[:, 0], -pts[:, 2], pts[:, 1]])


def _centre(proj: Path, road: np.ndarray, grid: rw.Grid):
    """The line the road was swept along, Blender (x, y, height) + widths: data/finished_centerline.json (the kn5 frame,
    z mirrored on some tracks — the orientation is read off the built road: the one whose points lie on it), else
    data/centerline.local.json (ENU)."""
    fin = proj / "data" / "finished_centerline.json"
    src = fin if fin.exists() else proj / "data" / "centerline.local.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    p = np.array(d["points_xyz_m"], dtype=np.float64)
    W = np.array(d["widths_m"], dtype=np.float64)
    best = None
    for sz in (1.0, -1.0):
        xy = np.column_stack([p[:, 0], sz * p[:, 2]])
        i, j = grid.index(xy[:, 0], xy[:, 1])
        ok = (i >= 0) & (j >= 0) & (i < grid.nx) & (j < grid.ny)
        on = float(road[j[ok], i[ok]].mean()) if ok.any() else 0.0
        if best is None or on > best[0]:
            best = (on, sz)
    P = np.column_stack([p[:, 0], best[1] * p[:, 2], p[:, 1]])
    return P, W, {"file": src.name, "z_sign": best[1], "on_road_frac": round(best[0], 4)}


def main() -> int:
    blend, proj, eng = _args()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    report = proj / "data" / "road_wear.json"
    spec = rw.spec_from_config(cfg)
    if spec is None:
        report.unlink(missing_ok=True)
        print("[road_wear] no road_wear key in track.config.json: nothing to do (the blend is left alone)")
        return 0
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    ej = _engine_prep(eng)
    surfaces = spec["surfaces"]
    objs = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        up = ob.name.upper()
        key = next((s for s in surfaces if up.startswith(s)), None)
        if key is not None:
            objs.setdefault(key, []).append(ob)
    if surfaces[0] not in objs:
        print(f"[road_wear] FATAL: no {surfaces[0]} mesh in {blend.name}")
        return 1
    data = {}
    for key, obl in objs.items():
        for ob in obl:
            data[ob.name] = _faces(ob)
    before = _hash([data[n][4] for n in sorted(data)])
    cen = np.concatenate([d[2] for d in data.values()])
    over = 0.0
    for P, fl, c, _t, _co in data.values():
        over = max(over, float(np.max(np.abs(P[:, :2] - c[fl, :2]))) if len(P) else 0.0)
    plan = rw.plan_atlas(cen[:, :2], cen[:, 2], over, spec)
    tex = spec["texel_m"]; C = plan["cell_m"]; M = plan["margin_m"]; Pp = plan["pitch_px"]
    keys_by = {n: rw.cell_keys(d[2][:, :2], d[2][:, 2], plan, spec) for n, d in data.items()}
    allkeys = sorted({k for ks in keys_by.values() for k in ks})
    slots = rw.tile_slots(allkeys, plan)
    print(f"[road_wear] {sum(len(d[2]) for d in data.values())} faces on {sorted(data)}; furthest vertex {over:.2f} m off its "
          f"centroid; atlas {plan['atlas_px']} px at {tex} m ({plan['cells']} cells of {C:.0f} m + {M:.0f} m margin, "
          f"{plan['atlas_fill_pct']} % of the atlas used)")

    # 3. the grid over every tile window; the built road; the aerial
    ci = np.array([k[0] for k in allkeys]); cj = np.array([k[1] for k in allkeys])
    x0, y0 = ci.min() * C - M, cj.min() * C - M
    grid = rw.Grid(x0, y0, int(round(((ci.max() + 1) * C + M - x0) / tex)), int(round(((cj.max() + 1) * C + M - y0) / tex)), tex)
    road_tris = np.concatenate([data[o.name][3][:, :, :2] for o in objs[surfaces[0]]])
    road = rw.rasterize(grid, road_tris)
    print(f"[road_wear] grid {grid.nx} x {grid.ny} at {tex} m; the built {surfaces[0]} covers {road.sum() * tex * tex:.0f} m2 "
          f"({time.time() - t0:.0f} s)")
    aer_spec = spec.get("aerial")
    stats = {"plan": plan, "furthest_vertex_m": round(over, 3)}
    if aer_spec:
        img = _image_pixels(proj / aer_spec["image"])
        o = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
        aer = rw.Aerial(img, aer_spec["bbox_lonlat"], (o["lon"], o["lat"]))
        reg = rw.register(aer, grid, road)
        aer.dx, aer.dy = reg["dx_m"], reg["dy_m"]
        tone, tstats = rw.tone_field(aer, grid, road, spec["tone"])
        stats["aerial"] = {"image": aer_spec["image"], "registration": reg, **tstats}
        print(f"[road_wear] aerial registered to the built road: shift ({reg['dx_m']:+.2f}, {reg['dy_m']:+.2f}) m, contrast "
              f"{reg['contrast_at_0']:+.4f} -> {reg['contrast_best']:+.4f}; shadow {tstats['shadow_pct']} %, paint "
              f"{tstats['paint_pct']} % of the road; tone p01/p50/p99 {tstats['tone_p01_p50_p99']}")
    else:
        tone = np.ones((grid.ny, grid.nx), dtype=np.float32)
        stats["aerial"] = None
    m0 = 1.0 / float(np.percentile(tone[road], spec["tone"]["headroom_pct"]))
    m0 = min(1.0, m0)

    # 4. the lines
    w = spec["wear"]
    Pc, Wc, cinfo = _centre(proj, road, grid)
    Pc = rw.closed_polyline(Pc) if cfg.get("loop", True) else Pc
    closed = bool(cfg.get("loop", True))
    Wc = Wc[:len(Pc)]
    lines = []
    line_specs = spec.get("lines") or [{"layout": L.get("id", "main")} for L in (cfg.get("layouts") or [{"id": "main"}])]
    for ls in line_specs:
        ai = proj / ls["ai"] if ls.get("ai") else None
        if ai is not None and ai.exists():
            P = _read_ai_xyz(ai)
            P = rw.closed_polyline(P) if closed else P
            P, _e, L = rw.resample(P, 2.0, closed)
            src = f"recorded {ls['ai']}"
        else:
            C2, W2, L = rw.resample(Pc, 2.0, closed, Wc[:, None])
            if ls.get("reverse"):
                C2 = C2[::-1].copy(); W2 = W2[::-1].copy()
            n = rw.left_normals(C2, closed)
            cap = W2[:, 0] / 2 + w["edge_reach_m"]
            el, er = rw.scan_edges(C2, n, road, grid, cap, cap)
            a = rw.min_curvature(C2, n, -(er - w["margin_m"]), el - w["margin_m"], closed)
            P = np.column_stack([C2[:, :2] + a[:, None] * n, C2[:, 2]])
            src = "model: minimum curvature inside the built edges" + (" (recorded line named but missing: "
                                                                      f"{ls['ai']})" if ai is not None else "")
        I, sp = rw.rubber_intensity(P, 2.0, w, closed)
        lines.append({"P": P, "I": I, "closed": closed, "layer_m": spec["layer_m"], "layout": ls.get("layout"),
                      "source": src, "lap_m": round(L, 1), **sp})
        out = proj / "data" / f"road_wear.line.{ls.get('layout', 'main')}.json"
        out.write_text(json.dumps({"layout": ls.get("layout"), "source": src, "frame": "Blender (x = E, y = N, height)",
                                   "spacing_m": 2.0, "points": np.round(P, 3).tolist(), "rubber": np.round(I, 4).tolist(),
                                   **sp}, indent=0), encoding="utf-8", newline="\n")
        print(f"[road_wear] line {ls.get('layout')}: {src}; {L:.0f} m, model lap {sp['lap_s_model']} s "
              f"({sp['v_min_kmh']}-{sp['v_max_kmh']} km/h) -> {out.name}")

    # 5. bake the atlas, tile by tile, from the world
    A = plan["atlas_px"]
    atlas = np.full((A, A, 4), 0, dtype=np.uint8)
    base = int(round(255 * m0))
    atlas[..., :3] = base
    reach = 0.5 * w["track_m"] + 4 * w["spread_m"]
    dmax = 0.0
    for k in allkeys:
        wx, wy = rw.tile_window(k, plan)
        gi0 = int(round((wx - grid.x0) / tex)); gj0 = int(round((wy - grid.y0) / tex))
        T = tone[gj0:gj0 + Pp, gi0:gi0 + Pp]
        X, Y = grid.centres(gi0, gj0, Pp, Pp)
        keep = np.ones_like(T)
        for ln in lines:
            keep *= 1.0 - rw.wear_at(X, Y, k[2] * spec["layer_m"], ln, w, reach)
        dmax = max(dmax, float(1 - keep.min()))
        macro = np.clip(m0 * T * keep, 0.0, 1.0)
        col, row = slots[k]
        atlas[row * Pp:(row + 1) * Pp, col * Pp:(col + 1) * Pp, :3] = np.round(macro * 255)[..., None].astype(np.uint8)
    texdir = proj / "textures" / "road_wear"
    texdir.mkdir(parents=True, exist_ok=True)
    files = {}
    files["macro"] = texdir / "road_wear_macro.png"
    nbytes = rw.write_png(files["macro"], atlas[::-1])          # Blender rows bottom-up -> PNG top-down
    flat = np.zeros((4, 4, 3), dtype=np.uint8); flat[...] = (128, 128, 255)
    files["flat_nm"] = texdir / "road_wear_flat_nm.png"
    rw.write_png(files["flat_nm"], flat)
    print(f"[road_wear] macro atlas {A} x {A}: m0 {m0:.4f}, deepest rubber {100 * dmax:.1f} %, {nbytes} B "
          f"({time.time() - t0:.0f} s)")

    # detail per surface: its own stock texture (or the track's override) / m0
    overrides = pbr.load_overrides(proj)
    mats = {}
    detail_stats = {}
    for key, obl in objs.items():
        res = pbr.resolve(obl[0].name, overrides)
        if res["diffuse"] is None or not Path(res["diffuse"]).exists():
            print(f"[road_wear] FATAL: {key}: no diffuse to keep as the detail ({res['diffuse']})")
            return 1
        d = _image_pixels(Path(res["diffuse"]))
        for s in d.shape[:2]:
            if s & (s - 1):
                print(f"[road_wear] FATAL: {res['diffuse']} is not a power of two ({d.shape[1]} x {d.shape[0]})")
                return 1
        dd = d / m0
        clip = float((dd > 1.0).mean())
        # JPEG, as the stock tile it is made from (0.1.7's first build wrote it as PNG: 9.6 MB for a 2.4 MB JPEG)
        fn = texdir / f"road_wear_detail_{key.lower()}.jpg"
        hh, ww = dd.shape[:2]
        im = bpy.data.images.new(fn.stem, ww, hh, alpha=False)
        px = np.ones((hh, ww, 4), dtype=np.float32)
        px[..., :3] = np.clip(dd, 0, 1)[::-1]                     # top-down -> Blender's bottom-up rows
        im.pixels.foreach_set(px.ravel())
        im.filepath_raw = str(fn)
        im.file_format = "JPEG"
        im.save(filepath=str(fn), quality=DETAIL_JPEG_Q)
        bpy.data.images.remove(im)
        nm = Path(res["normal"]) if res["normal"] is not None and Path(res["normal"]).exists() else files["flat_nm"]
        detail_stats[key] = {"from": str(Path(res["diffuse"]).name), "normal": nm.name, "clipped_pct": round(100 * clip, 3),
                             "size": [d.shape[1], d.shape[0]]}
        mats[key] = {"diffuse": files["macro"], "normal": files["flat_nm"], "detail": fn, "detail_nm": nm}

    # 6. the UVs
    for key, obl in objs.items():
        for ob in obl:
            P, fl, c, _t, _co = data[ob.name]
            ks = keys_by[ob.name]
            me = ob.data
            uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
            me.uv_layers.active = uvl
            fk = np.array([slots[k] for k in ks], dtype=np.float64)          # (col, row) per face
            wxy = np.array([rw.tile_window(k, plan) for k in ks], dtype=np.float64)
            u = (fk[fl, 0] * Pp + (P[:, 0] - wxy[fl, 0]) / tex) / A
            v = (fk[fl, 1] * Pp + (P[:, 1] - wxy[fl, 1]) / tex) / A
            uvl.data.foreach_set("uv", np.column_stack([u, v]).ravel().astype(np.float32))
            me.update()

    # 7. the materials
    mult = rw.detail_multiplier(plan, spec)
    rows = {}
    for key, obl in objs.items():
        m = mats[key]
        imgs = {}
        for slot, f in (("txDiffuse", m["diffuse"]), ("txNormal", m["normal"]), ("txDetail", m["detail"]),
                        ("txNormalDetail", m["detail_nm"])):
            im = bpy.data.images.get(f.name) or bpy.data.images.load(str(f), check_existing=True)
            im.name = f.name
            if slot != "txDiffuse" and slot != "txDetail":
                try:
                    im.colorspace_settings.name = "Non-Color"
                except Exception:
                    pass
            if not im.packed_file:
                im.pack()
            imgs[slot] = im
        seen = set()
        for ob in obl:
            for mat in ob.data.materials:
                if mat is None or mat.name in seen:
                    continue
                seen.add(mat.name)
                nt = mat.node_tree
                for nd in [n for n in nt.nodes if n.type == "TEX_IMAGE" or n.type == "NORMAL_MAP"]:
                    nt.nodes.remove(nd)
                bsdf = nt.nodes.get("Principled BSDF")
                for slot, im in imgs.items():
                    t = nt.nodes.new("ShaderNodeTexImage"); t.image = im; t.label = slot
                    if slot == "txDiffuse" and bsdf is not None:
                        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
                rows[mat.name] = {"shader": "ksPerPixelMultiMap_NMDetail",
                                  "textures": [[s, imgs[s].name, str(f)] for s, f in (("txDiffuse", m["diffuse"]),
                                               ("txNormal", m["normal"]), ("txDetail", m["detail"]),
                                               ("txNormalDetail", m["detail_nm"]))],
                                  "props": {"detailUVMultiplier": mult, "detailNormalBlend": 1.0, "useDetail": 1.0}}
    # 8. the writer's vertex count (engine-july's own), split when over
    caps = {}
    for key, obl in objs.items():
        for ob in list(obl):
            if ej is not None:
                tiles = ej._split_for_writer(ob)
                for t in (tiles or [ob]):
                    n = ej.export_vertex_count(ej._export_vertex_keys(t.data)[0])
                    caps[t.name] = n
                    if n > VERT_CAP:
                        print(f"[road_wear] FATAL: {t.name}: {n} writer vertices > {VERT_CAP}")
                        return 1
            else:
                caps[ob.name] = None
    after_objs = [o for o in bpy.data.objects if o.type == "MESH" and any(o.name.upper().startswith(s) for s in surfaces)]
    after = {}
    for o in after_objs:
        me = o.data; nv = len(me.vertices)
        co = np.empty(nv * 3); me.vertices.foreach_get("co", co)
        after[o.name] = co.reshape(nv, 3) @ np.array(o.matrix_world)[:3, :3].T + np.array(o.matrix_world)[:3, 3]
    same = set(after) == set(data) and _hash([after[n] for n in sorted(after)]) == before
    if not same:
        # a writer split renames: compare the multiset of positions instead
        a1 = np.unique(np.round(np.concatenate([d[4] for d in data.values()]), 5), axis=0)
        a2 = np.unique(np.round(np.concatenate(list(after.values())), 5), axis=0)
        same = a1.shape == a2.shape and bool(np.all(a1 == a2))
    if not same:
        print("[road_wear] FATAL: a vertex moved (positions before != after)")
        return 1
    for f in list(files.values()) + [m["detail"] for m in mats.values()]:
        im = bpy.data.images.get(Path(f).name)
        if im is not None and any(s & (s - 1) for s in im.size):
            print(f"[road_wear] FATAL: {Path(f).name} {tuple(im.size)} is not a power of two")
            return 1
    report.write_text(json.dumps({
        "_doc": "ledger 0084 road wear (tools/road_wear_blend.py): the material rows engine-july's export_kn5_addon binds, "
                "and every number the bake used",
        "materials": rows, "spec": spec, "stats": stats, "m0": round(m0, 5), "detail_uv_multiplier": mult,
        "detail": detail_stats, "deepest_rubber": round(dmax, 4), "centre": cinfo,
        "lines": [{k: v for k, v in ln.items() if k not in ("P", "I")} for ln in lines],
        "writer_vertices": caps, "positions_md5": before, "macro_png_bytes": nbytes,
        "textures": {k: Path(v).name for k, v in files.items()},
    }, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)), encoding="utf-8", newline="\n")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    print(f"[road_wear] {len(rows)} materials -> ksPerPixelMultiMap_NMDetail (detailUVMultiplier {mult:g}); writer vertices "
          f"{caps}; positions unchanged; -> {report.name}, {blend.name} saved ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    rc = main()
    if rc:
        raise SystemExit(rc)

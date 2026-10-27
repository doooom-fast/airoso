"""Build the Lake Murray main loop as EDITABLE Blender meshes — the starting point for live work.

This is deliberately NOT a kn5 exporter. It drops the real-road, real-elevation loop into a .blend so
Kevin (designer) and Claude (operator) can shape it interactively in Blender before any AC export. What it
creates, at REAL sampled elevation (metres, Blender Z-up, +Y = north):

  ROAD    — the drivable ribbon (1ROAD), swept ±width/2 along the centreline, tight to real elevation
  KERB    — corner kerbs, sitting right on the road edge (kept tight to the road, not floating)
  TERRAIN — the grass ground, conformed to the road and clamped to ±terrain_band_m of the nearest road.
            With terrain.tiers declared (ledger 0046; fleet/LAWS.md L3 as amended 2026-10-11: near-road relief
            is clamped, far relief is data) the clamp holds only near a pavement, the ground is the tiered 3DEP
            lattice (fine at the verge), and the far ring past the physical extent is GRASS_FAR (visual only)

Run headless:
  <blender> --background --python scripts/blender/build_loop_blend.py -- project
Then open project/loop.blend in the Blender GUI to work on it live.
"""

import ast
import json
import math
import struct
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender


# --- minimal .npy reader + grid projection (copied so the importer stands alone) ------------------

def read_npy(path):
    with open(path, "rb") as f:
        assert f.read(6) == b"\x93NUMPY"
        f.read(2)
        hlen = struct.unpack("<H", f.read(2))[0]
        header = ast.literal_eval(f.read(hlen).decode())
        ny, nx = header["shape"]
        data = struct.unpack(f"<{ny * nx}d", f.read(8 * ny * nx))
    return [list(data[j * nx:(j + 1) * nx]) for j in range(ny)]


def meters_per_degree(lat0):
    m_lat = 111_132.92 - 559.82 * math.cos(2 * math.radians(lat0))
    m_lon = 111_412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0))
    return m_lon, m_lat


def project_grid(grid, meta, lon0, lat0, elev0):
    s, w, n, e = meta["bbox_swne"]
    nx, ny, sp = meta["nx"], meta["ny"], meta["spacing_m"]
    midlat = (s + n) / 2
    gy = sp / 111_000.0
    gx = sp / (111_000.0 * math.cos(math.radians(midlat)))
    m_lon, m_lat = meters_per_degree(lat0)
    out = []
    for j in range(ny):
        lat = n - j * gy
        out.append([((w + i * gx - lon0) * m_lon, grid[j][i] - elev0, (lat - lat0) * m_lat)
                    for i in range(nx)])
    return out


def carve_road_corridor(grid_xyz, centerline, widths, *, carve=0.2, iters=12):
    """GUARANTEE the terrain never crests over the road. conform+clearance grade grid NODES, but a coarse
    facet spanning a sunk node and a higher one just outside can still cross over the thin ribbon (worst
    at the I-8 bridge cut, where the deck is raised over the freeway embankment). Here we sample the road
    ribbon directly and, wherever the interpolated terrain sits at/above the road, push that grid cell's
    four corners to road-height minus ``carve`` — iterating until no sample pokes. Mutates in place."""
    ny = len(grid_xyz); nx = len(grid_xyz[0])
    x0 = grid_xyz[0][0][0]; z0 = grid_xyz[0][0][2]
    dx = grid_xyz[0][1][0] - x0; dz = z0 - grid_xyz[1][0][2]   # rows run north->south (z decreases with j)

    def cell(tx, tz):
        fi = (tx - x0) / dx; fj = (z0 - tz) / dz
        return max(0, min(nx - 2, int(fi))), max(0, min(ny - 2, int(fj))), fi, fj

    def th(tx, tz):
        i0, j0, fi, fj = cell(tx, tz); ti = fi - i0; tj = fj - j0
        a = grid_xyz[j0][i0][1]; b = grid_xyz[j0][i0 + 1][1]
        c = grid_xyz[j0 + 1][i0][1]; d = grid_xyz[j0 + 1][i0 + 1][1]
        return (a * (1 - ti) + b * ti) * (1 - tj) + (c * (1 - ti) + d * ti) * tj

    def perp(i):
        a = centerline[max(0, i - 1)]; b = centerline[min(len(centerline) - 1, i + 1)]
        ex, ez = b[0] - a[0], b[2] - a[2]; L = math.hypot(ex, ez) or 1.0
        return (-ez / L, ex / L)

    offs = [k / 10 * 1.08 for k in range(-10, 11)]        # across the ribbon + a touch past both edges
    for _ in range(iters):
        changed = False
        for i, (x, y, z) in enumerate(centerline):
            px, pz = perp(i); hw = widths[i] / 2
            for o in offs:
                tx, tz = x + px * o * hw, z + pz * o * hw
                if th(tx, tz) > y - 0.005:
                    i0, j0, _, _ = cell(tx, tz); lim = y - carve
                    for jj in (j0, j0 + 1):
                        for ii in (i0, i0 + 1):
                            g = grid_xyz[jj][ii]
                            if g[1] > lim:
                                grid_xyz[jj][ii] = (g[0], lim, g[2]); changed = True
        if not changed:
            break


def band_clamp(grid_xyz, road_pts, band):
    """Clamp every terrain cell to within ±band of the nearest road point's height (kills fake peaks)."""
    from collections import defaultdict
    B = 130.0
    buck = defaultdict(list)
    for (x, y, z) in road_pts:
        buck[(int(x // B), int(z // B))].append((x, y, z))

    def nearest_y(x, z):
        bx, bz = int(x // B), int(z // B)
        best_y, best_d, r = None, 1e18, 1
        while best_y is None and r < 40:
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if r > 1 and max(abs(dx), abs(dz)) != r:
                        continue
                    for (rx, ry, rz) in buck.get((bx + dx, bz + dz), ()):
                        d = (x - rx) ** 2 + (z - rz) ** 2
                        if d < best_d:
                            best_d, best_y = d, ry
            r += 1
        return best_y

    for j in range(len(grid_xyz)):
        for i in range(len(grid_xyz[0])):
            x, y, z = grid_xyz[j][i]
            ry = nearest_y(x, z)
            if ry is not None:
                grid_xyz[j][i] = (x, max(ry - band, min(ry + band, y)), z)


# --- Blender mesh creation ------------------------------------------------------------------------

def _load_i8(proj, legacy=False):
    """The I-8 floor polyline [(x, y, z)]. ``legacy`` (tiered terrain, ledger 0046): the original 64-point
    polyline kept as i8.legacy.local.json — the near-road trench, guardrails and streetlight skips were built
    on it, and they must not move — while data/i8.local.json is the corridor floor re-fetched over the far
    box (scripts/elevation/terrain_sample.py, a dict carrying its provenance)."""
    d = proj / "data"
    p = d / "i8.legacy.local.json" if legacy and (d / "i8.legacy.local.json").exists() else d / "i8.local.json"
    if not p.exists():
        return []
    v = json.loads(p.read_text())
    return [tuple(x) for x in (v["points_xyz_m"] if isinstance(v, dict) else v)]


# --- tiered terrain (ledger 0046; opt-in: track.config.json terrain.tiers) ------------------------

def _engine_terrain_tiers():
    """airoso's scripts/geometry/terrain_tiers.py, loaded BY PATH: inside Blender `scripts` is this
    track's own package (scripts-v021), so the engine module cannot be imported by name."""
    import importlib.util
    p = Path(__file__).resolve().parents[4] / "scripts" / "geometry" / "terrain_tiers.py"
    if not p.exists():
        raise SystemExit(f"[blend] terrain.tiers declared but the engine module is not at {p} — run this "
                         f"assembler from airoso's tracks/san-diego-lake-murray/scripts-v021 (tools/ship_sd.sh)")
    spec = importlib.util.spec_from_file_location("_airoso_terrain_tiers", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _legacy_surface(grid_xyz):
    """height of the v0.17.1 TERRAIN surface at (x, z): the graded 20 m grid (conform, clamp, carve, trench)
    triangulated EXACTLY as ribbon.grass_terrain does — quad (j,i)/(j,i+1)/(j+1,i+1)/(j+1,i) split on its
    NW->SE diagonal — so a kept vertex lands on the old surface, not on a bilinear patch of it"""
    ny = len(grid_xyz); nx = len(grid_xyz[0])
    x0 = grid_xyz[0][0][0]; z0 = grid_xyz[0][0][2]
    dxg = grid_xyz[0][1][0] - x0; dzg = z0 - grid_xyz[1][0][2]

    def h(x, z):
        fi = (x - x0) / dxg; fj = (z0 - z) / dzg
        if fi < 0 or fj < 0 or fi > nx - 1 or fj > ny - 1:
            return None
        i0 = max(0, min(nx - 2, int(fi))); j0 = max(0, min(ny - 2, int(fj)))
        ti = fi - i0; tj = fj - j0
        a = grid_xyz[j0][i0][1]; b = grid_xyz[j0][i0 + 1][1]
        c = grid_xyz[j0 + 1][i0 + 1][1]; d = grid_xyz[j0 + 1][i0][1]
        if ti >= tj:                                    # triangle (a, b, c)
            return a + (b - a) * ti + (c - b) * tj
        return a + (c - d) * ti + (d - a) * tj           # triangle (a, c, d)
    return h


def build_tiered_terrain(proj, cfg, grid_xyz, road_lines, elev0):
    """The ledger-0046 ground from data/terrain.tiers.json.gz (scripts/elevation/terrain_sample.py): every
    vertex is 3DEP at that vertex; the band clamp holds only near a pavement (L3 as amended 2026-10-11) and
    releases to the raw DEM by clamp_blend_m; within keep_surface_m of a pavement the v0.17.1 graded surface
    is kept (the conform corridor, everything the drive gates were tuned on), feathered into the data over
    keep_feather_m. Returns (TERRAIN mesh = physical, GRASS_FAR mesh = the visual-only far ring, report)."""
    import gzip
    import hashlib
    from mathutils import kdtree
    tt = _engine_terrain_tiers()
    data = proj / "data"
    tp = data / "terrain.tiers.json.gz"
    if not tp.exists():
        raise SystemExit("[blend] terrain.tiers declared but data/terrain.tiers.json.gz is missing — run "
                         "python -m scripts.elevation.terrain_sample <project> first (tools/ship_sd.sh does)")
    T = json.loads(gzip.decompress(tp.read_bytes()).decode("utf-8"))
    # the topology was planned on these exact road inputs: a stale plan would mesh the wrong verges
    raw = data / "centerline.raw.local.json"
    files = [raw if raw.exists() else data / "centerline.local.json"]
    if (data / "connectors.local.json").exists():
        files.append(data / "connectors.local.json")
    if (data / "heightfield.meta.json").exists():
        files.append(data / "heightfield.meta.json")
    # ledger 0054 P2: tier_options.planned_pavement's intermediates planned the tiers + physical ground too (never the
    # kept cells, the clamp or the feather below: those follow the built roads in road_lines)
    for rel in ((cfg.get("terrain") or {}).get("tier_options") or {}).get("planned_pavement", {}).get("files", []):
        files.append(proj / rel)
    now = {f.name: hashlib.md5(f.read_bytes()).hexdigest() for f in files}
    if now != T["inputs_md5"]:
        raise SystemExit(f"[blend] data/terrain.tiers.json.gz was planned on other road inputs ({T['inputs_md5']} "
                         f"vs {now}) — rerun scripts.elevation.terrain_sample")
    tcfg = cfg["terrain"]
    opt = tcfg.get("tier_options") or {}
    band = float(tcfg.get("terrain_band_m", 22.0))
    c_full, c_rel = float(tcfg.get("clamp_corridor_m", 80.0)), float(tcfg.get("clamp_blend_m", 250.0))
    keep_m, keep_f = float(opt.get("keep_surface_m", 0.0)), float(opt.get("keep_feather_m", 0.0))
    # the feather as an earth batter (ledger 0046 fix round 4; opt-in): its length follows how far the graded ground
    # sits off the data, between keep_feather_min_m and keep_feather_m
    batter = float(opt["keep_batter"]) if "keep_batter" in opt else None
    keep_fmin = float(opt.get("keep_feather_min_m", 0.0))
    fx0, fz0, fux, fuz = T["frame"]                     # base-lattice key (I, J) -> (x0 + I*ux, z0 + J*uz)

    # pavement distance + nearest road height: the FINAL lines (smoothed, narrowed) at <= 1 m
    pts, hws, ys = [], [], []
    for li, (lpts, lw) in enumerate(road_lines):
        n = len(lpts)
        segs = list(range(n - 1)) + ([n - 1] if li == 0 and n > 2 else [])     # line 0 = the closed loop
        for k in segs:
            a, b = lpts[k], lpts[(k + 1) % n]
            wa, wb = lw[k] / 2.0, lw[(k + 1) % n] / 2.0
            m = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[2] - a[2]) / 1.0)))
            for s in range(m):
                t = s / m
                pts.append((a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t))
                hws.append(wa + (wb - wa) * t); ys.append(a[1] + (b[1] - a[1]) * t)
    kd = kdtree.KDTree(len(pts))
    for k, (x, z) in enumerate(pts):
        kd.insert((x, z, 0.0), k)
    kd.balance()
    legacy = _legacy_surface(grid_xyz)

    I, J, H, K = T["I"], T["J"], T["h"], T["keep"]
    # the kept cells (the graded grid's own triangles) reach past keep_surface_m wherever a 20 m cell touches the
    # within_m band, up to ~46 m out: feathering by pavement distance alone then leaves the cell's outer edge on the
    # graded surface and the data one 5 m node away (a serrated step where the two disagree, e.g. the cut bank west
    # of seam-alvarado). So the feather ALSO runs keep_feather_m out from the nearest kept node (ledger 0046).
    kept_xz = [(fx0 + i * fux, fz0 + j * fuz) for i, j, kc in zip(I, J, K) if kc]
    kd_keep = None
    RF = T.get("refine")
    # with keep_cells.refine the kept cells themselves take the data past move_beyond_m once the prep has reshaped the
    # near-road ground (build_kn5_loop._refine_kept_terrain): their outer edge is then no longer the graded surface,
    # and the feather is the pavement one alone — the same field on both sides of the kept edge
    if kept_xz and keep_f > 0.0 and RF is None:
        kd_keep = kdtree.KDTree(len(kept_xz))
        for k, (x, z) in enumerate(kept_xz):
            kd_keep.insert((x, z, 0.0), k)
        kd_keep.balance()
    verts = []
    vdist = []                                          # pavement distance per vertex (None = a kept-cell node)
    n_keep = n_feather = n_clamped = n_cell = n_edge = 0
    max_lift = max_cut = 0.0

    def ground(x, z, h):
        """(local y, pavement distance) of a non-kept vertex: 3DEP under the distance-weighted band clamp, then the
        kept graded surface feathered in near the roads"""
        nonlocal n_keep, n_feather, n_clamped, n_edge, max_lift, max_cut
        y = h - elev0
        _co, k, dist = kd.find((x, z, 0.0))
        d = dist - hws[k]
        w = tt.clamp_weight(d, c_full, c_rel)
        if w > 0.0:
            y2 = tt.band_clamp_value(y, ys[k], band, w)
            if abs(y2 - y) > 1e-9:
                n_clamped += 1
                max_lift, max_cut = max(max_lift, y2 - y), max(max_cut, y - y2)
            y = y2
        Lg = None
        if batter is not None and keep_m < d < keep_m + keep_f:
            Lg = legacy(x, z)
            wk = tt.keep_weight(d, keep_m, tt.feather_len((Lg - y) if Lg is not None else keep_f, keep_f, batter,
                                                           keep_fmin))
        else:
            wk = tt.keep_weight(d, keep_m, keep_f)
        if kd_keep is not None and wk < 1.0:
            we = tt.keep_weight(kd_keep.find((x, z, 0.0))[2], 0.0, keep_f)
            if we > wk:
                wk = we
                n_edge += 1
        if wk > 0.0:
            L = legacy(x, z)
            if L is None:
                raise SystemExit(f"[blend] tiered terrain: vertex ({x:.1f}, {z:.1f}) {d:.1f} m from a pavement lies "
                                 f"outside the 40 m grid the kept surface comes from")
            y = y + wk * (L - y)
            if wk >= 1.0:
                n_keep += 1
            else:
                n_feather += 1
        return y, d
    for i, j, h, kc in zip(I, J, H, K):
        x, z = fx0 + i * fux, fz0 + j * fuz
        if kc:
            # a KEPT cell's corner or a node on its edge: the graded grid itself (the seat and the kn5 prep then
            # reshape exactly the ground they always reshaped; a finer neighbour's node lies ON the kept edge)
            L = legacy(x, z)
            if L is None:
                raise SystemExit(f"[blend] tiered terrain: kept vertex ({x:.1f}, {z:.1f}) outside the 40 m grid")
            verts.append((x, L, z))
            vdist.append(None)
            n_cell += 1
            continue
        y, d = ground(x, z, h)
        verts.append((x, y, z))
        vdist.append(d)
    # BREAK LINES (ledger 0046 fix round 4, terrain_sample.build_breaks): vertices ON the edges of plain 5 m cells
    # where a sharp riser crosses them, at fine keys (units of base / break.fine); the same clamp and feather as any
    # vertex. They are never kept-cell nodes and never move a lattice vertex.
    BK = T.get("break")
    n_lat = len(verts)
    Ib, Jb = list(I), list(J)
    if BK:
        q = float(BK["fine"])
        for i5, j5, h in zip(BK["I5"], BK["J5"], BK["h"]):
            x, z = fx0 + i5 / q * fux, fz0 + j5 / q * fuz
            y, d = ground(x, z, h)
            if d <= keep_m:
                raise SystemExit(f"[blend] tiered terrain: break-line vertex ({x:.1f}, {z:.1f}) is {d:.1f} m from a "
                                 f"pavement, inside keep_surface_m {keep_m} (the planning roads moved?)")
            verts.append((x, y, z))
            vdist.append(d)
            Ib.append(i5 / q); Jb.append(j5 / q)
    tris = T["tris"]
    tri3 = [(tris[3 * k], tris[3 * k + 1], tris[3 * k + 2]) for k in range(len(tris) // 3)]
    # DATA DIAGONALS (ledger 0046 fix round 2): every plain square cell is split along the diagonal its data
    # agrees with (terrain_tiers.data_diagonals), past diagonals.beyond_m of a pavement only — the fixed
    # diagonal aliased slanting 3DEP channels and cut benches into parallel ribs. Opt-in; no vertex moves.
    n_diag = 0
    dg = opt.get("diagonals")
    if dg:
        if dg.get("rule", "min_dh") != "min_dh":
            raise SystemExit(f"[blend] terrain.tier_options.diagonals.rule {dg.get('rule')!r}: only 'min_dh'")
        beyond = float(dg.get("beyond_m", 20.0))
        elig = [dd is not None and dd > beyond and n < n_lat for n, dd in enumerate(vdist)]
        tri3, n_diag = tt.data_diagonals(tri3, Ib, Jb, [v[1] for v in verts], elig)
    phys, far = tt.split_mesh(tri3, [bool(p) for p in T["phys"]])
    n_refine = 0
    if RF is not None:
        # the data the prep's kept-cell refinement needs at the kept cells' x-split sub-lattice: D = 3DEP under the
        # same distance-weighted clamp as every lattice vertex, d = pavement distance (the feather's argument)
        prm = RF["params"]
        nD, nd, nL = [], [], []
        for i, j, h in zip(RF["I"], RF["J"], RF["h"]):
            x, z = fx0 + i * fux, fz0 + j * fuz
            y = h - elev0
            _co, k, dist = kd.find((x, z, 0.0))
            d = dist - hws[k]
            w = tt.clamp_weight(d, c_full, c_rel)
            if w > 0.0:
                y = tt.band_clamp_value(y, ys[k], band, w)
            nD.append(round(y, 3)); nd.append(round(d, 3))
            if batter is not None:
                # the feather length at this node, from the graded surface it blends away from (ledger 0046 fix
                # round 4): interpolated by the prep like D and d, so a straight run of vertices stays straight
                Lg = legacy(x, z)
                nL.append(round(tt.feather_len((Lg - y) if Lg is not None else keep_f, keep_f, batter, keep_fmin), 3))
        n_refine = len(nD)
        refine = {"_provenance": {"what": "ledger 0046 kept-cell refinement data for the kn5 prep "
                                          "(build_kn5_loop._refine_kept_terrain): x-split sub-lattice of every kept "
                                          "cell reaching past refine.beyond_m; D = 3DEP (terrain.samples.json.gz) under "
                                          "the L3 clamp, local y; d = pavement distance, m",
                                  "tiers": "terrain.tiers.json.gz"},
                  "frame": T["frame"], "keep_r": RF["keep_r"], "cell_r": RF["cell_r"],
                  "kept_cells": RF["kept_cells"], "cells": RF["cells"],
                  "I": RF["I"], "J": RF["J"], "D": nD, "d": nd,
                  "keep_m": keep_m, "keep_feather_m": keep_f,
                  **({"keep_batter": batter, "keep_feather_min_m": keep_fmin, "L": nL} if batter is not None else {}),
                  "edge_m": float(prm["edge_m"]), "move_beyond_m": float(prm["move_beyond_m"]),
                  "min_face_d_m": float(prm["min_face_d_m"])}
        (data / "terrain.refine.json.gz").write_bytes(
            gzip.compress(json.dumps(refine, separators=(",", ":")).encode("utf-8"), 6, mtime=0))
    else:
        (data / "terrain.refine.json.gz").unlink(missing_ok=True)

    def mesh(sel):
        used, nv, nt = {}, [], []
        for t in sel:
            q = []
            for v in t:
                if v not in used:
                    used[v] = len(nv); nv.append(verts[v])
                q.append(used[v])
            nt.append(tuple(q))
        return {"vertices": nv, "uvs": [(v[0] / 6.0, v[2] / 6.0) for v in nv], "tris": nt}

    terrain, far_mesh = mesh(phys), mesh(far)
    ylo = min(v[1] for v in verts) + elev0
    yhi = max(v[1] for v in verts) + elev0
    rep = {"vertices": len(verts), "physical_v": len(terrain["vertices"]), "far_v": len(far_mesh["vertices"]),
           "kept_cell_vertices": n_cell, "kept_surface": n_keep, "feathered": n_feather,
           "feathered_from_kept_edge": n_edge, "refine_nodes": n_refine, "clamped": n_clamped,
           **({"data_diagonals_flipped": n_diag} if dg else {}),
           **({"break_vertices": len(verts) - n_lat, "break_cells": BK.get("break_cells")} if BK else {}),
           "clamp_max_lift": round(max_lift, 2), "clamp_max_cut": round(max_cut, 2),
           "abs_min": round(ylo, 2), "abs_max": round(yhi, 2)}
    print(f"[blend] tiered terrain: {rep}")
    (data / "terrain.tiers.report.json").write_text(json.dumps(rep, indent=1))
    return terrain, far_mesh, rep


def _surface_sampler(mesh_dict):
    """(x, z) -> height of the highest face of a local-frame mesh under the point (BVH ray, Blender maths)"""
    from mathutils.bvhtree import BVHTree
    vb = [(x, z, y) for (x, y, z) in mesh_dict["vertices"]]
    bvh = BVHTree.FromPolygons(vb, [tuple(t) for t in mesh_dict["tris"]])

    def h(x, z):
        hit = bvh.ray_cast((x, z, 9000.0), (0.0, 0.0, -1.0))
        return hit[0].z if hit[0] is not None else None
    return h


def _i8_nearest(i8, x, z):
    """Nearest distance from (x,z) to the I-8 polyline + the interpolated I-8 floor height there."""
    bd, floor = 1e18, None
    for k in range(len(i8) - 1):
        ax, ay, az = i8[k]; bx, by, bz = i8[k + 1]
        dx, dz = bx - ax, bz - az; L2 = dx * dx + dz * dz
        if L2 == 0:
            continue
        t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        cx, cz = ax + t * dx, az + t * dz
        dd = math.hypot(x - cx, z - cz)
        if dd < bd:
            bd = dd; floor = ay + (by - ay) * t
    return bd, floor


def cut_i8_trench(grid_xyz, i8, *, half_w=16.0, bank=6.0, depth=1.0):
    """Sink the terrain in the I-8 corridor down to the freeway's real grade so the loop bridges span a
    real cut. Within ``half_w`` of the I-8 centreline drop to floor-``depth``; ramp back to the existing
    ground over ``bank``. Runs AFTER carve_road_corridor so the cut wins under the crossing decks. All
    non-crossing loop roads sit >22 m from I-8, so a half_w+bank<=22 m cut never undercuts the frontage."""
    if not i8:
        return
    for j in range(len(grid_xyz)):
        for i in range(len(grid_xyz[0])):
            x, y, z = grid_xyz[j][i]
            bd, floor = _i8_nearest(i8, x, z)
            if floor is None:
                continue
            if bd <= half_w:
                target = floor - depth
            elif bd < half_w + bank:
                tt = (bd - half_w) / bank
                target = (floor - depth) * (1 - tt) + y * tt
            else:
                continue
            if y > target:
                grid_xyz[j][i] = (x, target, z)


def _level_i8_decks(centerline, i8, *, near=30.0, pad=4):
    """Where the loop crosses OVER I-8 (near the I-8 line AND above its floor), replace the road elevation
    across the span with a straight arc-length interpolation between the two approach heights — a real
    bridge DECK, not the sag-to-freeway-floor the bare-earth DEM sampled (College/70th 'flat plane' bug).
    Only the crossings lift (y>floor); a road running alongside I-8 in a low valley is left alone."""
    if not i8:
        return centerline
    over = []
    for x, y, z in centerline:
        bd, floor = _i8_nearest(i8, x, z)
        over.append(floor is not None and bd < near and y > floor + 0.5)
    mask = [any(over[max(0, k - pad):k + pad + 1]) for k in range(len(over))]  # dilate onto the approaches
    pts = [list(p) for p in centerline]
    k = 0
    while k < len(mask):
        if not mask[k]:
            k += 1
            continue
        a = k
        while k + 1 < len(mask) and mask[k + 1]:
            k += 1
        b = k
        lo, hi = max(0, a - 1), min(len(pts) - 1, b + 1)
        ya, yb = pts[lo][1], pts[hi][1]
        dcum = [0.0]
        for j in range(lo + 1, hi + 1):
            dcum.append(dcum[-1] + math.hypot(pts[j][0] - pts[j - 1][0], pts[j][2] - pts[j - 1][2]))
        tot = dcum[-1] or 1.0
        for idx, j in enumerate(range(lo, hi + 1)):
            pts[j][1] = ya + (yb - ya) * (dcum[idx] / tot)
        print(f"[blend] leveled I-8 deck: pts {a}-{b} between {ya:.1f}->{yb:.1f} m")
        k += 1
    return [tuple(p) for p in pts]


GUARDRAIL_SET_M = 0.15   # [invented] v0.18.0: each panel stands this far OUTSIDE the pavement edge, on the curb


def build_guardrails(centerline, widths, i8, *, h=0.95, over=22.0, pad=3, set_m=GUARDRAIL_SET_M):
    """Vertical guardrail panels along BOTH road edges wherever the loop is over the I-8 cut (perp dist to
    I-8 < ``over``). Extends ``pad`` points onto each approach so the rail starts before the gap.

    Each panel stands ``set_m`` outside the pavement's edge (v0.18.0, the gates lens): placed ON the edge line
    (``hw``) every panel vertex lay on the carriageway's own boundary, so audit_mesh D read all 90 of them as a wall
    standing on the road (512 kn5 vertex records in v0.17.1, 514 once College's deck rose to its real height and the
    exporter's exact-normal dedup split two more). A bridge barrier stands on the curb behind the gutter line, not
    on the pavement; 0.15 m puts it on the curb's top, its foot still inside the curb."""
    verts, tris = [], []
    if not i8:
        return {"vertices": verts, "uvs": [], "tris": tris}
    on = [(_i8_nearest(i8, p[0], p[2])[0] < over) for p in centerline]
    # dilate the over-mask by pad so rails run onto the approaches
    mask = [any(on[max(0, k - pad):k + pad + 1]) for k in range(len(on))]
    def perp(i):
        a = centerline[max(0, i - 1)]; b = centerline[min(len(centerline) - 1, i + 1)]
        ex, ez = b[0] - a[0], b[2] - a[2]; L = math.hypot(ex, ez) or 1.0
        return (-ez / L, ex / L)
    runs, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            runs.append((i, j)); i = j + 1
        else:
            i += 1
    for a, b in runs:
        for side in (1, -1):
            base = len(verts)
            for k in range(a, b + 1):
                x, y, z = centerline[k]; px, pz = perp(k); hw = widths[k] / 2
                ex, ez = x + px * side * (hw + set_m), z + pz * side * (hw + set_m)
                verts.append((ex, y, ez))        # bottom (deck level)
                verts.append((ex, y + h, ez))    # top
            for m in range(b - a):
                v = base + m * 2
                # double-sided quad (two tris each winding) so it reads from either side
                tris.append((v, v + 1, v + 3)); tris.append((v, v + 3, v + 2))
                tris.append((v, v + 3, v + 1)); tris.append((v, v + 2, v + 3))
    return {"vertices": verts, "uvs": [], "tris": tris}


def _grid_sampler(grid_xyz):
    ny = len(grid_xyz); nx = len(grid_xyz[0])
    x0 = grid_xyz[0][0][0]; z0 = grid_xyz[0][0][2]
    dxg = grid_xyz[0][1][0] - x0; dzg = z0 - grid_xyz[1][0][2]
    def h(x, z):
        fi = (x - x0) / dxg; fj = (z0 - z) / dzg
        i0 = max(0, min(nx - 2, int(fi))); j0 = max(0, min(ny - 2, int(fj))); ti = fi - i0; tj = fj - j0
        a = grid_xyz[j0][i0][1]; b = grid_xyz[j0][i0 + 1][1]
        c = grid_xyz[j0 + 1][i0][1]; d = grid_xyz[j0 + 1][i0 + 1][1]
        return (a * (1 - ti) + b * ti) * (1 - tj) + (c * (1 - ti) + d * ti) * tj
    return h


def _post_box(verts, tris, x, z, y0, y1, r):
    b = len(verts)
    for (dx, dz) in [(-r, -r), (r, -r), (r, r), (-r, r)]:
        verts.append((x + dx, y0, z + dz))
    for (dx, dz) in [(-r, -r), (r, -r), (r, r), (-r, r)]:
        verts.append((x + dx, y1, z + dz))
    for k in range(4):
        a, c = b + k, b + (k + 1) % 4
        tris.append((a, c, b + 4 + (k + 1) % 4)); tris.append((a, b + 4 + (k + 1) % 4, b + 4 + k))
    tris.append((b + 4, b + 5, b + 6)); tris.append((b + 4, b + 6, b + 7))


def _tube(verts, tris, x0, z0, y0, x1, z1, y1, r):
    dx, dz = x1 - x0, z1 - z0; L = math.hypot(dx, dz) or 1.0; ux, uz = dx / L, dz / L
    px, pz = -uz, ux
    b = len(verts)
    for (sx, sz, sy) in [(x0, z0, y0), (x1, z1, y1)]:
        for (ox, oz, oy) in [(-px * r, -pz * r, -r), (px * r, pz * r, -r), (px * r, pz * r, r), (-px * r, -pz * r, r)]:
            verts.append((sx + ox, sy + oy, sz + oz))
    for k in range(4):
        a, c = b + k, b + (k + 1) % 4
        tris.append((a, c, b + 4 + (k + 1) % 4)); tris.append((a, b + 4 + (k + 1) % 4, b + 4 + k))


def build_streetlights(centerline, widths, i8, grid_xyz, *, spacing=55.0, side_off=2.8,
                       post_h=9.0, arm=1.8, piece_planner=None):
    """Streetlight posts along the loop, COLLISION-AWARE so they never clip other objects:
    - offset outside the kerb (width/2 + side_off) — never in the road;
    - skip the I-8 bridge/cut spans (near_i8 < 26 m) — no posts on a deck or in the trench;
    - min 25 m between posts — no two overlap;
    - base GROUNDED on the sampled terrain (not floating/buried), and rejected where the road sits >6 m
      above the ground (a cut wall) so a post never spawns halfway down the freeway embankment.
    Returns (mesh, lamp_head_positions) with heads in LOCAL frame (x=E, y=up, z=N) for the CSP lights.
    ``piece_planner(placed)`` (ledger 0054 P4 step 2, EXPANSION-PLAN D4): given the mainline's bases, returns the north
    pieces' posts as scripts.geometry.streetlights plans them (its "lamps": head, base_xz, roadward_xz per post) — swept
    here AFTER the mainline's, so the loop's posts keep their numbers (0..n-1) and every reader of lights.local.json
    sees one list. Returns (mesh, heads, that plan or None)."""
    import bisect
    terr = _grid_sampler(grid_xyz)

    def perp(i):
        a = centerline[max(0, i - 1)]; b = centerline[min(len(centerline) - 1, i + 1)]
        ex, ez = b[0] - a[0], b[2] - a[2]; L = math.hypot(ex, ez) or 1.0
        return (-ez / L, ex / L)

    def near_i8(x, z):
        best = 1e18
        for k in range(len(i8) - 1):
            ax, az = i8[k][0], i8[k][2]; bx2, bz2 = i8[k + 1][0], i8[k + 1][2]
            dx, dz = bx2 - ax, bz2 - az; L2 = dx * dx + dz * dz
            if L2 == 0:
                continue
            t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
            best = min(best, math.hypot(x - (ax + t * dx), z - (az + t * dz)))
        return best

    cum = [0.0]
    for i in range(1, len(centerline)):
        cum.append(cum[-1] + math.dist(centerline[i][::2], centerline[i - 1][::2]))
    total = cum[-1]
    verts, tris, heads, placed = [], [], [], []
    s, side = spacing, 1
    while s < total:
        i = min(bisect.bisect_left(cum, s), len(centerline) - 1)
        cx, cy, cz = centerline[i]; hw = widths[i] / 2; px, pz = perp(i)
        if i8 and near_i8(cx, cz) < 26:
            s += spacing; continue
        off = hw + side_off
        bx, bz = cx + px * side * off, cz + pz * side * off
        if any((bx - ox) ** 2 + (bz - oz) ** 2 < 25 ** 2 for ox, oz in placed):
            s += spacing; continue
        base_y = terr(bx, bz)
        if cy - base_y > 6.0:                        # road towers over the ground here (cut wall) — skip
            s += spacing; side = -side; continue
        placed.append((bx, bz))
        top = base_y + post_h
        _post_box(verts, tris, bx, bz, base_y, top, 0.16)          # post
        ix, iz = -px * side, -pz * side                            # arm reaches IN toward the road
        hx, hz = bx + ix * arm, bz + iz * arm
        _post_box(verts, tris, hx, hz, top - 0.25, top, 0.24)      # lamp head
        _tube(verts, tris, bx, bz, top - 0.1, hx, hz, top - 0.1, 0.07)  # arm
        heads.append([round(hx, 3), round(top - 0.2, 3), round(hz, 3)])
        side = -side; s += spacing
    # ledger 0054 P4: the north pieces' posts, as planned (base on the piece's walk, head ARM_M road-ward of it,
    # HEAD_OVER_GROUND_M over the draft ground — the same box post + arm + head as the loop's, so every reader and
    # gate downstream sees one kind of draft lamp; tools/author_lamps_blend.py stands the real model on them). The
    # planner is given the loop's bases, so its MIN_GAP_M rule counts them too
    piece_plan = piece_planner(list(placed)) if piece_planner is not None else None
    for lamp in (piece_plan or {}).get("lamps", []):
        bx, bz = lamp["base_xz"]
        hx, hy, hz = lamp["head"]
        top = hy + 0.2
        _post_box(verts, tris, bx, bz, top - post_h, top, 0.16)   # post (the draft's 9 m box)
        _post_box(verts, tris, hx, hz, top - 0.25, top, 0.24)      # lamp head
        _tube(verts, tris, bx, bz, top - 0.1, hx, hz, top - 0.1, 0.07)  # arm
        heads.append([round(hx, 3), round(hy, 3), round(hz, 3)])
    return {"vertices": verts, "uvs": [], "tris": tris}, heads, piece_plan


def plan_piece_streetlights(proj, cfg, data, centerline, widths, connectors, conn_records, grid_xyz, placed):
    """ledger 0054 P4 step 2 (EXPANSION-PLAN D4): plan the posts of the north pieces (the connectors whose record
    carries `expansion`) with scripts.geometry.streetlights — on the piece's walk, clear of every other pavement
    (the mainline, every other connector and side-street stub, the junction pads' outlines and stub arms, the curb
    cuts), the loop's spacing except where OSM has real street_lamp nodes, nothing in a declared unlit stretch.
    Opt-in by track.config.json scenery.streetlights.expansion.enabled; returns None when off or when no piece is
    built (then the loop's lamps are exactly as before)."""
    from scripts.geometry import streetlights as SL
    sl_cfg = ((cfg.get("scenery") or {}).get("streetlights") or {}).get("expansion") or {}
    pieces = []
    rec_of = {c["name"]: c for c in conn_records}
    inter = {}
    ip = data / "expansion.north.json"
    if ip.exists():
        inter = json.loads(ip.read_text(encoding="utf-8"))
    st_of = {str(p["id"]): p.get("stations") or [] for p in inter.get("pieces", [])}
    for cname, cpts, cw in connectors:
        ex = (rec_of.get(cname) or {}).get("expansion")
        if ex:
            pieces.append({"name": cname, "id": str(ex.get("piece")), "pts": cpts, "widths": cw,
                           "stations": st_of.get(str(ex.get("piece")), [])})
    if not sl_cfg.get("enabled") or not pieces:
        return None
    piece_names = {p["name"] for p in pieces}
    others = [(cname, cpts, cw, "stub" if (rec_of.get(cname) or {}).get("stub") else "connector")
              for cname, cpts, cw in connectors if cname not in piece_names]
    others += [(p["name"], p["pts"], p["widths"], "connector") for p in pieces]   # the other pieces (at the pads)
    pads = [(pd["id"], [tuple(q) for q in pd["outline_xz"]]) for pd in inter.get("pads", []) if pd.get("outline_xz")]
    pads += [(f"{s.get('junction')}:{s['id']}", [tuple(q) for q in s["pavement_xz"]])
             for s in inter.get("stubs", []) if s.get("pavement_xz")]
    stubs, cuts = [], []
    sp = data / "stubs.plan.json"
    if sp.exists():
        plan = json.loads(sp.read_text(encoding="utf-8"))
        stubs = [{"id": s["id"], "host": s.get("host"), "side": s.get("side"), "cut_xz": s.get("cut_xz"),
                  "width_m": s.get("width_m")} for s in plan.get("stubs", [])]
        cuts = [{"id": c["id"], "host": c.get("host"), "side": c.get("side"), "station_m": c.get("station_m"),
                 "half_span_m": c.get("half_span_m"), "flare_m": c.get("flare_m"), "cut_xz": c.get("cut_xz")}
                for c in plan.get("curb_cuts", [])]
    osm_nodes, osm_src = [], None
    of = sl_cfg.get("osm_lamps_file")
    if of:
        op = proj / of
        if op.exists():
            raw = json.loads(op.read_text(encoding="utf-8"))
            local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
            o = local["origin"]
            osm_nodes = SL.project_osm_nodes(raw.get("street_lamps", []), float(o["lon"]), float(o["lat"]))
            osm_src = {"file": of, "osm_base": raw.get("osm_base"), "nodes_in_file": len(osm_nodes)}
        else:
            print(f"[blend] streetlights: osm_lamps_file {of} not in the project — every piece stretch is authored")
    # the loop's posts stand first: the planner keeps MIN_GAP_M from them (mainline sweep replicated for the bases)
    terr = _grid_sampler(grid_xyz)
    out = SL.plan(pieces, mainline=(centerline, widths), others=others, pads=pads, stubs=stubs, curb_cuts=cuts,
                  placed=placed, cfg_expansion=sl_cfg, osm_nodes=osm_nodes, ground=terr)
    out["osm_source"] = osm_src
    out["pieces"] = [{"name": p["name"], "id": p["id"], "n_points": len(p["pts"])} for p in pieces]
    for pid, r in out["per_piece"].items():
        print(f"[blend] streetlights piece {pid} ({r['name']}, {r['length_m']} m): {r['authored']} authored + "
              f"{r['osm']} OSM-grounded, {r['skipped']} skipped, unlit {[(u['s_from'], u['s_to']) for u in r['unlit']]}, "
              f"OSM nodes beside it {len(r['osm_nodes'])}")
    return out


def build_curbs(centerline, widths, *, curb_h=0.14, curb_w=0.15):
    """Continuous concrete street curb along BOTH road edges (replaces the racing corner kerbs): a low
    vertical face at the road edge + a narrow top lip + an outer skirt. Physical 1KERB surface."""
    verts, tris = [], []
    n = len(centerline)
    def perp(i):
        a = centerline[max(0, i - 1)]; b = centerline[min(n - 1, i + 1)]
        ex, ez = b[0] - a[0], b[2] - a[2]; L = math.hypot(ex, ez) or 1.0
        return (-ez / L, ex / L)
    for side in (1, -1):
        base = len(verts)
        for i in range(n):
            x, y, z = centerline[i]; px, pz = perp(i); hw = widths[i] / 2
            ex, ez = x + px * side * hw, z + pz * side * hw
            ox, oz = ex + px * side * curb_w, ez + pz * side * curb_w
            verts.append((ex, y, ez)); verts.append((ex, y + curb_h, ez))
            verts.append((ox, y + curb_h, oz)); verts.append((ox, y - 0.3, oz))   # outer skirt dips BELOW grass so no hover gap shows
        for i in range(n - 1):
            a = base + i * 4; b = base + (i + 1) * 4
            for (p0, p1) in [(0, 1), (1, 2), (2, 3)]:
                tris.append((a + p0, a + p1, b + p1)); tris.append((a + p0, b + p1, b + p0))
    tris += [(t[0], t[2], t[1]) for t in list(tris)]      # double-sided: visible from either side in-game
    return {"vertices": verts, "uvs": [], "tris": tris}


def build_sidewalks(cache, centerline, grid_xyz, lon0, lat0, *, half_w=0.9, lift=0.14, near=24.0):
    """Raised sidewalk slabs along the OSM footway=sidewalk ways that run BESIDE the loop (>50% of the way
    within ``near`` m of the loop centreline — wide enough to clear the now-wide road half-widths).
    Flat top at terrain+lift with a vertical skirt."""
    m_lon = 111320.0 * math.cos(math.radians(lat0)); m_lat = 110574.0
    terr = _grid_sampler(grid_xyz)
    from collections import defaultdict
    B = 40.0; rb = defaultdict(list)
    for i in range(0, len(centerline), 2):
        rb[(int(centerline[i][0] // B), int(centerline[i][2] // B))].append((centerline[i][0], centerline[i][2]))
    def dloop(x, z):
        bx, bz = int(x // B), int(z // B); best = 1e18
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (rx, rz) in rb.get((bx + dx, bz + dz), ()):
                    best = min(best, (x - rx) ** 2 + (z - rz) ** 2)
        return math.sqrt(best)
    verts, tris = [], []
    kept = 0
    for w in cache:
        line = [((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in w["geom"]]
        if len(line) < 2:
            continue
        if sum(1 for (x, z) in line if dloop(x, z) < near) < max(2, len(line) * 0.5):
            continue
        kept += 1
        base = len(verts)
        for k in range(len(line)):
            x, z = line[k]
            a = line[max(0, k - 1)]; b = line[min(len(line) - 1, k + 1)]
            ex, ez = b[0] - a[0], b[1] - a[1]; L = math.hypot(ex, ez) or 1.0
            px, pz = -ez / L, ex / L
            ty = terr(x, z) + lift
            for (sx, sz) in [(x + px * half_w, z + pz * half_w), (x - px * half_w, z - pz * half_w)]:
                verts.append((sx, ty, sz)); verts.append((sx, ty - lift, sz))
        for k in range(len(line) - 1):
            a = base + k * 4; b = base + (k + 1) * 4
            tris.append((a + 0, a + 2, b + 2)); tris.append((a + 0, b + 2, b + 0))
            for e in (0, 2):
                tris.append((a + e, a + e + 1, b + e + 1)); tris.append((a + e, b + e + 1, b + e))
    tris += [(t[0], t[2], t[1]) for t in list(tris)]      # double-sided so the slab top always shows
    return {"vertices": verts, "uvs": [], "tris": tris}, kept


_HOUSE_TYPES = {"house", "detached", "residential", "bungalow", "semidetached_house", "yes", "terrace"}
_H_DEFAULT = {"house": 5.5, "detached": 5.5, "residential": 6.0, "bungalow": 4.0, "terrace": 5.5,
              "garage": 3.0, "apartments": 11.0, "dormitory": 11.0, "retail": 6.5, "commercial": 7.0,
              "supermarket": 8.0, "school": 8.0, "university": 9.5, "hospital": 12.0, "yes": 5.5}


def _bld_height(b):
    if b.get("height"):
        try:
            return float(str(b["height"]).split()[0].replace("m", ""))
        except ValueError:
            pass
    if b.get("levels"):
        try:
            return float(str(b["levels"]).split(";")[0]) * 3.2
        except ValueError:
            pass
    return _H_DEFAULT.get(b.get("building"), 6.0)


def build_buildings(centerline, widths, grid_xyz, cache, lon0, lat0, *, min_area=25.0, cap=None, terr=None):
    """Extrude OSM building footprints near the loop (houses included — building=yes/house cover them).
    Sit each on the sampled terrain, skip any that crowd the road, split HOUSE vs BUILDING for material
    variety. ``cap`` keeps only the N largest near-road footprints (a 46 km urban loop has 60k+). Returns
    {'HOUSE': mesh, 'BUILDING': mesh}. ``terr``: the ground to sit on (default the graded grid; the tiered
    terrain passes its own surface so a house 40-120 m out stands on the ground that ships)."""
    m_lon = 111320.0 * math.cos(math.radians(lat0)); m_lat = 110574.0
    terr = terr or _grid_sampler(grid_xyz)
    # bucket the road for fast nearest (centre pt -> half width)
    from collections import defaultdict
    B = 60.0
    rb = defaultdict(list)
    for i in range(0, len(centerline), 2):
        x, _y, z = centerline[i]; rb[(int(x // B), int(z // B))].append((x, z, widths[i] / 2))
    def near_road(x, z):
        bx, bz = int(x // B), int(z // B); best_d, best_hw = 1e18, 0
        for dx in (-2, -1, 0, 1, 2):
            for dz in (-2, -1, 0, 1, 2):
                for (rx, rz, hw) in rb.get((bx + dx, bz + dz), ()):
                    d = (x - rx) ** 2 + (z - rz) ** 2
                    if d < best_d:
                        best_d, best_hw = d, hw
        return math.sqrt(best_d), best_hw

    meshes = {"HOUSE": {"vertices": [], "uvs": [], "tris": []},
              "BUILDING": {"vertices": [], "uvs": [], "tris": []}}
    cand = []                                             # (area, foot, cx, cz, building)
    for b in cache:
        if b.get("building") == "roof":
            continue
        foot = [((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in b["geom"]]
        if len(foot) >= 2 and foot[0] == foot[-1]:
            foot = foot[:-1]
        if len(foot) < 3:
            continue
        cx = sum(p[0] for p in foot) / len(foot); cz = sum(p[1] for p in foot) / len(foot)
        area = abs(sum(foot[i][0] * foot[(i + 1) % len(foot)][1] - foot[(i + 1) % len(foot)][0] * foot[i][1]
                       for i in range(len(foot)))) / 2
        if area < min_area:
            continue
        d_road, hw = near_road(cx, cz)                    # bucketed nearest — O(1), no per-vertex scan
        if d_road > 120 or d_road < hw + 5:               # roadside context, but not crowding the road
            continue
        cand.append((area, foot, cx, cz, b))
    cand.sort(key=lambda c: -c[0])                        # largest footprints first
    if cap:
        cand = cand[:cap]
    for area, foot, cx, cz, b in cand:
        if _signed_area(foot) < 0:                        # ensure CCW so walls face outward
            foot = foot[::-1]
        grp = "HOUSE" if b.get("building") in _HOUSE_TYPES else "BUILDING"
        _extrude_footprint(meshes[grp], foot, terr(cx, cz) - 0.4, _bld_height(b))
    print(f"[blend] buildings: {len(cand)} extruded near the loop "
          f"(HOUSE {len(meshes['HOUSE']['tris'])//2}, BUILDING {len(meshes['BUILDING']['tris'])//2} quads)")
    return meshes


def _signed_area(foot):
    n = len(foot)
    return sum(foot[i][0] * foot[(i + 1) % n][1] - foot[(i + 1) % n][0] * foot[i][1] for i in range(n)) / 2


def _tri_area2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])


def _pt_in_tri(p, a, b, c):
    d1, d2, d3 = _tri_area2(p, a, b), _tri_area2(p, b, c), _tri_area2(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))   # all same sign = inside


def _triangulate_ccw(foot):
    """Ear-clip a simple CCW polygon (positive signed area) into CCW index triangles. Unlike a fan from
    vertex 0, this stays correct for CONCAVE footprints (L-shapes, courtyards) — their fan roofs otherwise
    produce inverted/see-through triangles."""
    idx = list(range(len(foot)))
    tris = []
    guard = 4 * len(foot) * len(foot) + 10
    while len(idx) > 3 and guard > 0:
        guard -= 1
        L = len(idx)
        for i in range(L):
            ia, ib, ic = idx[(i - 1) % L], idx[i], idx[(i + 1) % L]
            a, b, c = foot[ia], foot[ib], foot[ic]
            if _tri_area2(a, b, c) <= 1e-9:                      # reflex/degenerate (CCW) → not an ear
                continue
            if any(_pt_in_tri(foot[j], a, b, c) for j in idx if j not in (ia, ib, ic)):
                continue
            tris.append((ia, ib, ic)); idx.pop(i); break
        else:
            break                                                # numerical fallback: stop cleanly
    if len(idx) == 3:
        tris.append((idx[0], idx[1], idx[2]))
    return tris


def _extrude_footprint(mesh, foot, base_y, h):
    verts, tris = mesh["vertices"], mesh["tris"]
    n = len(foot); b = len(verts)
    for (x, z) in foot:
        verts.append((x, base_y, z))
    for (x, z) in foot:
        verts.append((x, base_y + h, z))
    # Winding is chosen so that AFTER make_mesh's reflection-cancel (the (x,y,z)->(x,z,y) swap + a
    # per-tri winding reversal), a CCW footprint's walls face OUTWARD and the roof faces UP. Authoring the
    # "natural" (a,c,d)/(0,k,k+1) order instead lands them inward/down — the inside-out-buildings bug.
    for k in range(n):
        a, c = b + k, b + (k + 1) % n
        d, e = b + n + (k + 1) % n, b + n + k
        tris.append((a, d, c)); tris.append((a, e, d))     # outward wall
    for (i, j, k) in _triangulate_ccw(foot):               # concave-safe flat roof, faces up
        tris.append((b + n + i, b + n + k, b + n + j))


def make_mesh(name, mesh_dict, rgba):
    """mesh_dict has 'vertices' [(x,y,z)] in local (x=E, y=up, z=N); remap to Blender Z-up (x, z, y).
    The remap is a reflection (det -1) that flips face orientation, so REVERSE each triangle's winding to
    cancel it — authored orientation is preserved (drivable stays face-up, building walls stay outward)."""
    verts = [(vx, vz, vy) for (vx, vy, vz) in mesh_dict["vertices"]]
    faces = [(t[0], t[2], t[1]) for t in mesh_dict["tris"]]
    if not verts or not faces:
        print(f"[blend] {name}: empty, skipped")
        return None
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    # apply authored per-vertex UVs. Most meshes get re-UV'd (planar) in build_kn5, but palms keep these —
    # without them the frond cards sample the texture at (0,0) (a transparent corner) and vanish.
    uvs = mesh_dict.get("uvs")
    if uvs and len(uvs) == len(verts):
        uvl = me.uv_layers.new(name="UVMap")
        for loop in me.loops:
            uvl.data[loop.index].uv = uvs[loop.vertex_index]
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = False
    mat.diffuse_color = rgba
    me.materials.append(mat)
    print(f"[blend] {name}: {len(verts)} verts, {len(faces)} faces")
    return ob


def _profile_sigma_windows(cfg, data, raw_centerline):
    """Ledger 0057: [(sigma_y_pts, weight per unique vertex)] for every track.config.json road_datum.profiles window
    that carries assembler_sigma_y_pts. Its stations are on the pre-median centreline the windows are declared on
    (index-aligned with centerline.raw.local.json: median_envelope moves x/z, never the vertex count), else on the
    raw line; a window whose start is past its end runs through the lap seam (L13). [] when none is declared."""
    profs = [p for p in ((cfg.get("road_datum") or {}).get("profiles") or []) if p.get("assembler_sigma_y_pts")]
    if not profs:
        return []
    from scripts.geometry import smooth as smoothmod
    pts = raw_centerline
    pre = data / "centerline.raw.local.json.pre-median"
    if pre.exists():
        pp = json.loads(pre.read_text())["points_xyz_m"]
        if len(pp) == len(raw_centerline):
            pts = pp
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    closed = (abs(raw_centerline[0][0] - raw_centerline[-1][0]) < 1e-6
              and abs(raw_centerline[0][2] - raw_centerline[-1][2]) < 1e-6)
    lap = st[-1] if closed else None
    by_sigma = {}
    for p in profs:
        w0, w1 = float(p["window_m"][0]), float(p["window_m"][1])
        if w1 < w0:
            if not closed:
                raise SystemExit(f"road_datum.profiles {p['name']}: a window through the seam needs a closed loop")
            w1 += lap
        # blend default = tools/deck_datum.py PROFILE_BLEND_M
        by_sigma.setdefault(float(p["assembler_sigma_y_pts"]), []).append((w0, w1, float(p.get("blend_m", 30.0))))
    out = []
    for sig, wins in sorted(by_sigma.items()):
        wts = smoothmod.window_weights(st[:-1] if closed else st, lap, wins)
        out.append((sig, wts))
        print(f"[blend] sigma_y {sig:g} pts in {len(wins)} road_datum.profiles window(s) (ledger 0057): "
              f"{sum(1 for w in wts if w > 0)} vertices, {sum(1 for w in wts if w >= 1.0)} at full weight")
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["project"]
    proj = Path(argv[0]).resolve()
    repo = proj.parent
    sys.path.insert(0, str(repo))
    from scripts.geometry import ribbon, kerbs

    cfg = json.loads((proj / "track.config.json").read_text())
    band = float(cfg.get("terrain", {}).get("terrain_band_m", 22.0))
    route = cfg.get("route", {})

    data = proj / "data"
    # Always smooth from a PRISTINE snapshot of the OSM line so rebuilds are idempotent (we never
    # re-smooth an already-smoothed line). The snapshot is written once, on the first build.
    raw_path = data / "centerline.raw.local.json"
    if raw_path.exists():
        local = json.loads(raw_path.read_text())
    else:
        local = json.loads((data / "centerline.local.json").read_text())
        raw_path.write_text(json.dumps(local))
    raw_centerline = [tuple(p) for p in local["points_xyz_m"]]
    widths = local["widths_m"]
    lon0, lat0 = local["origin"]["lon"], local["origin"]["lat"]
    elev0 = local["origin"]["elev_m"]

    # Round the OSM facet-kinks on the curves — horizontal only, elevation preserved — then persist the
    # smoothed line so the mesh, the AC dummies (build_kn5) and the minimap all share ONE geometry.
    from scripts.geometry import smooth as smoothmod
    # Keep the REAL elevation — the loop genuinely grades down to the I-8 overpasses and back up, and that
    # down-and-up is the whole point. sigma_y is LIGHT: it only rounds the sharpest launch-crests (grade
    # reversals that send the car airborne) so the profile is smooth, NOT flat. We do NOT level the bridge
    # decks — the roads ease down and up across them; forcing a flat deck was wrong.
    # Ledger 0057 (opt-in): road_datum.profiles windows (tools/deck_datum.py re-based them on fresh 3DEP) keep their
    # real short grades — smoothed with their own assembler_sigma_y_pts instead of smooth_sigma_y_pts; every vertex
    # outside them is exactly the smooth_sigma_y_pts result. No declared window = the call below, unchanged.
    y_windows = _profile_sigma_windows(cfg, data, raw_centerline)
    centerline = smoothmod.smooth_centerline(
        raw_centerline, sigma_pts=float(route.get("smooth_sigma_pts", 2.0)),
        passes=int(route.get("smooth_passes", 2)),
        sigma_y_pts=float(route.get("smooth_sigma_y_pts", 1.5)),
        **({"y_sigma_windows": y_windows} if y_windows else {}))
    tiers_on = bool((cfg.get("terrain") or {}).get("tiers"))
    i8 = _load_i8(proj, legacy=tiers_on)
    print(f"[blend] smoothed curves: max kink {smoothmod.max_kink_deg(raw_centerline):.1f} -> "
          f"{smoothmod.max_kink_deg(centerline):.1f} deg")

    # --- extra lines: connector streets (the Del Cerro sub-loop) + any split carriageways, each carrying
    #     its OWN real 3DEP elevation (data/connectors.local.json, from scripts.geometry.extra_lines). Swept
    #     as ribbons and MERGED into the main ROAD/CURB/MARKINGS meshes so they share physics + materials.
    #     Their points also feed the terrain conform/clamp/carve so the hill ground meets them (no float). ---
    connectors = []
    stub_of = {}
    paint_of = {}
    conn_records = []           # the records as read (ledger 0054 P4: `expansion` / `stub` keys for the lamp planner)
    conn_path = data / "connectors.local.json"
    if conn_path.exists():
        conn_data = json.loads(conn_path.read_text())
        conn_records = list(conn_data.get("connectors", []))
        for c in conn_data.get("connectors", []):
            cpts = [tuple(p) for p in c["points_xyz_m"]]
            if len(cpts) < 2:
                continue
            cpts = smoothmod.smooth_centerline(cpts, sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
            connectors.append((c["name"], cpts, list(c["widths_m"])))
            if c.get("stub"):
                stub_of[c["name"]] = c["stub"]          # ledger 0054 phase 5: a stub is painted as its street
            if c.get("paint"):
                paint_of[c["name"]] = c["paint"]        # ledger 0054 P3: an authored piece is painted as authored
        print(f"[blend] {len(connectors)} connector line(s): " + ", ".join(n for n, _, _ in connectors))
        # split carriageways: narrow the main loop where it rides a divided road to ONE carriageway, so the
        # double-wide ribbon doesn't overlap the opposing carriageway added beside it (per-direction grade).
        nm = conn_data.get("narrow_main")
        if nm:
            tw = float(nm["width_m"])
            for i in nm["idx"]:
                if 0 <= i < len(widths):
                    widths[i] = min(widths[i], tw)
            print(f"[blend] narrowed {len(nm['idx'])} main-loop verts to single carriageway ({tw:.0f} m)")

    # persist the smoothed centerline + narrowed widths so build_kn5 (dummies) + minimap share this geometry
    local["points_xyz_m"] = [[round(c, 4) for c in p] for p in centerline]
    local["widths_m"] = widths
    (data / "centerline.local.json").write_text(json.dumps(local))

    # --- road + kerbs (tight to real elevation) ---
    road = ribbon.road_ribbon(centerline, widths)
    road["vertices"] = [(x, y + 0.10, z) for (x, y, z) in road["vertices"]]   # ~0.1 m proud of the terrain
    # ONE continuous urban edge per side: road edge -> curb -> raised sidewalk -> graded down to the grass.
    # Gives real sidewalks the WHOLE loop (not just the sparse OSM footways) AND removes the hover — the outer
    # lip lands on the terrain, so road/curb/sidewalk/grass share heights with no floating edge.
    kerb = ribbon.curb_sidewalk(centerline, widths, lift=0.10, curb_h=0.14, curb_face_w=0.08,
                                sidewalk_w=1.8, grade_w=1.2, grass_clearance=0.10)
    marks = ribbon.lane_markings(centerline, widths,   # painted lines: white edges/dashes + (two-way) yellow centre
                                 center_yellow=route.get("divided_double", True))
    for mk in marks.values():
        mk["vertices"] = [(x, y + 0.115, z) for (x, y, z) in mk["vertices"]]  # 1.5 cm above the road top

    # merge each connector's ribbon + curb + markings into the main meshes (shared names -> shared physics)
    def _append(dst, src):
        off = len(dst["vertices"])
        dst["vertices"] += src["vertices"]
        if "uvs" in dst and "uvs" in src and len(src["uvs"]) == len(src["vertices"]):
            dst["uvs"] += src["uvs"]
        dst["tris"] += [(a + off, b + off, c + off) for (a, b, c) in src["tris"]]

    for cname, cpts, cw in connectors:
        crib = ribbon.road_ribbon(cpts, cw)
        crib["vertices"] = [(x, y + 0.10, z) for (x, y, z) in crib["vertices"]]
        _append(road, crib)
        cker = ribbon.curb_sidewalk(cpts, cw, lift=0.10, curb_h=0.14, curb_face_w=0.08,
                                    sidewalk_w=1.5, grade_w=1.2, grass_clearance=0.10)
        _append(kerb, cker)
        cmk = ribbon.connector_markings(cpts, cw, stub_of.get(cname), paint_of.get(cname))   # == lane_markings(.., center_yellow=True) off a stub / authored piece
        for _k in ("white", "yellow"):
            cmk[_k]["vertices"] = [(x, y + 0.115, z) for (x, y, z) in cmk[_k]["vertices"]]
            _append(marks[_k], cmk[_k])

    # --- terrain: upsample the coarse 40 m DEM (finer facets), conform to the road with a small
    #     clearance so near-road ground sits just BELOW the road edge (no coarse facet pokes up through
    #     and buries the ribbon), then clamp to ±band so there are no fake mountains ---
    grid = read_npy(data / "heightfield.npy")
    meta = json.loads((data / "heightfield.meta.json").read_text())
    _grow = meta.get("grid_grow") or {}                                 # ledger 0054: whole cells added N / W
    grid, meta = ribbon.upsample_grid(grid, meta, 2)                      # 40 m -> 20 m facets
    _grow_rc = (2 * int(_grow.get("rows_n", 0)), 2 * int(_grow.get("cols_w", 0)))   # in 20 m rows / cols
    grid_xyz = project_grid(grid, meta, lon0, lat0, elev0)
    # connectors climb the Del Cerro hill (~40 m above the loop) — the terrain MUST conform + clamp to them
    # too, or the hill ground is clamped down to the loop grade and the connector ribbon floats over a void.
    extra_roads = [(cpts, cw) for _n, cpts, cw in connectors]
    ribbon.conform_terrain_to_road(grid_xyz, centerline, widths, corridor=20.0, blend=16.0, clearance=0.08,
                                   extra_roads=extra_roads)
    all_road_pts = list(centerline) + [p for _n, cpts, _w in connectors for p in cpts]
    band_clamp(grid_xyz, all_road_pts, band)
    carve_road_corridor(grid_xyz, centerline, widths, carve=0.2)   # guarantee no ground pokes through
    for _n, cpts, cw in connectors:
        carve_road_corridor(grid_xyz, cpts, cw, carve=0.2)
    cut_i8_trench(grid_xyz, i8)                                     # sink the I-8 corridor into a real cut (i8 loaded above)
    terrain_far, bterr = None, None
    if tiers_on:
        # ledger 0046: the tiered 3DEP lattice; the graded grid above is kept within keep_surface_m of a pavement
        terrain, terrain_far, _trep = build_tiered_terrain(
            proj, cfg, grid_xyz, [(centerline, widths)] + [(cpts, cw) for _n, cpts, cw in connectors], elev0)
        _new_ground, _old_ground = _surface_sampler(terrain), _grid_sampler(grid_xyz)

        def bterr(x, z):
            v = _new_ground(x, z)
            return _old_ground(x, z) if v is None else v
    else:
        terrain = ribbon.grass_terrain(grid_xyz)
    guardrail = build_guardrails(centerline, widths, i8)           # rails where the loop bridges I-8
    # collision-aware posts; ledger 0054 P4 step 2: + the north pieces' posts (scenery.streetlights.expansion)
    lights, lampheads, piece_plan = build_streetlights(
        centerline, widths, i8, grid_xyz,
        piece_planner=lambda placed: plan_piece_streetlights(proj, cfg, data, centerline, widths, connectors,
                                                             conn_records, grid_xyz, placed))
    lights_rec = {"lampheads": lampheads}                          # -> CSP [LIGHT_N]
    if piece_plan is not None:
        # the pieces' posts carry their base and road-ward unit (the author's "head -> nearest MAINLINE point" rule has
        # no meaning on a piece); indexed into lampheads after the loop's posts, which keep their numbers
        n0 = len(lampheads) - len(piece_plan["lamps"])
        for k, lamp in enumerate(piece_plan["lamps"]):
            lamp["i"] = n0 + k
        lights_rec["expansion"] = piece_plan
    (data / "lights.local.json").write_text(json.dumps(lights_rec))
    bcache = data / "buildings.cache.json"
    _scn = cfg.get("scenery", {})
    bmeshes = build_buildings(centerline, widths, grid_xyz, json.loads(bcache.read_text()), lon0, lat0,
                              min_area=float(_scn.get("building_min_area_m2", 25.0)),
                              cap=_scn.get("building_cap"), terr=bterr) \
        if bcache.exists() else {"HOUSE": {"vertices": [], "uvs": [], "tris": []},
                                 "BUILDING": {"vertices": [], "uvs": [], "tris": []}}
    # Continuous sidewalks now come from curb_sidewalk (above); the sparse OSM footways would only z-fight it.
    sidewalks, nsw = {"vertices": [], "uvs": [], "tris": []}, 0

    # --- palms on the verges of named target roads (scenery.palm_roads) ---
    palm_roads = _scn.get("palm_roads", [])
    palms = {"PALMTRUNK": {"vertices": [], "tris": [], "uvs": []},
             "PALMFROND": {"vertices": [], "tris": [], "uvs": []}}
    rlcache = data / "road_lanes.cache.json"
    if palm_roads and rlcache.exists():
        from scripts.geometry import palm as palmmod
        m_lon = 111320.0 * math.cos(math.radians(lat0)); m_lat = 110574.0
        segs = []
        for w in json.loads(rlcache.read_text()):
            if w.get("name") in palm_roads:
                g = [((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in w["geom"]]
                segs += [(g[a][0], g[a][1], g[a + 1][0], g[a + 1][1]) for a in range(len(g) - 1)]

        def on_target(x, z, thr2=25.0 * 25.0):
            best = 1e18
            for ax, az, bx, bz in segs:
                ddx, ddz = bx - ax, bz - az
                L2 = ddx * ddx + ddz * ddz or 1.0
                t = max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
                best = min(best, (x - (ax + t * ddx)) ** 2 + (z - (az + t * ddz)) ** 2)
            return best < thr2

        on_mask = [on_target(p[0], p[2]) for p in centerline]
        palms, npalm = palmmod.scatter(centerline, widths, _grid_sampler(grid_xyz), on_mask,
                                       spacing=float(_scn.get("palm_spacing_m", 28.0)))
        print(f"[blend] {npalm} palms scattered on {palm_roads}")

    # --- off-road neighbourhood scenery: shade trees in the yards + scrub on the hillsides ---
    scen = {"TREETRUNK": {"vertices": [], "tris": [], "uvs": []},
            "TREECANOPY": {"vertices": [], "tris": [], "uvs": []},
            "SCRUB": {"vertices": [], "tris": [], "uvs": []}}
    if _scn.get("scatter_trees") or _scn.get("scatter_scrub"):
        from scripts.geometry import scenery
        scen, ntree, nscrub = scenery.scatter(
            grid_xyz, centerline, widths,
            tree_pct=int(_scn.get("tree_pct", 40)) if _scn.get("scatter_trees") else 0,
            scrub_pct=int(_scn.get("scrub_pct", 26)) if _scn.get("scatter_scrub") else 0,
            index_offset=_grow_rc)     # a grown grid keeps every old node's jitter and pick (ledger 0054 P2)
        print(f"[blend] scenery: {ntree} shade trees + {nscrub} scrub (all placed off-road)")

    # --- fresh scene ---
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_mesh("TERRAIN", terrain, (0.30, 0.42, 0.20, 1.0))
    if terrain_far is not None:
        # the far ring (ledger 0046 E3): no digit prefix -> no physics, never scanned by the gates, never a
        # GrassFX / occluder mesh; the prep binds pbr's textured GRASS_FAR row (dry chaparral), never MOUNTAINS
        make_mesh("GRASS_FAR", terrain_far, (0.42, 0.38, 0.29, 1.0))
    make_mesh("ROAD", road, (0.09, 0.09, 0.10, 1.0))
    make_mesh("MARKINGS", marks["white"], (0.90, 0.90, 0.86, 1.0))   # white edge + dashed lane lines
    make_mesh("YLINE", marks["yellow"], (0.86, 0.68, 0.10, 1.0))     # double-yellow centreline
    make_mesh("CURB", kerb, (0.64, 0.64, 0.66, 1.0))          # concrete grey street curb (visual)
    make_mesh("SIDEWALK", sidewalks, (0.68, 0.68, 0.66, 1.0))
    print(f"[blend] {nsw} sidewalk ways along the loop")
    make_mesh("GUARDRAIL", guardrail, (0.82, 0.82, 0.86, 1.0))
    make_mesh("LIGHTS", lights, (0.28, 0.28, 0.30, 1.0))
    make_mesh("HOUSE", bmeshes["HOUSE"], (0.60, 0.55, 0.48, 1.0))
    make_mesh("BUILDING", bmeshes["BUILDING"], (0.62, 0.62, 0.60, 1.0))
    # Foliage ships PRE-CHUNKED under AC's 65,535-vert cap (palm.chunk_mesh: balanced median
    # bisection). The engine's build_kn5_loop split pass uses equal-width spatial bands, which
    # clustered scatter defeats — one PALMFROND band once hit 82,797 verts, and the engine's
    # over-cap guard is FATAL. Chunk names keep the material prefix (PALMFROND_A -> PALMFROND);
    # letter suffixes can't collide with the engine's numeric _0.. split tiles.
    from scripts.geometry.palm import chunk_mesh
    for base, md, rgba in (
            ("PALMTRUNK", palms["PALMTRUNK"], (0.45, 0.38, 0.28, 1.0)),   # tall Mexican fan palm trunk
            ("PALMFROND", palms["PALMFROND"], (0.24, 0.40, 0.16, 1.0)),   # drooping fan crown (alpha)
            ("TREETRUNK", scen["TREETRUNK"], (0.34, 0.26, 0.18, 1.0)),    # broadleaf shade-tree trunk
            ("TREECANOPY", scen["TREECANOPY"], (0.21, 0.36, 0.16, 1.0)),  # shade canopy (in the yards)
            ("SCRUB", scen["SCRUB"], (0.40, 0.42, 0.25, 1.0))):           # dry chaparral on the hillsides
        chunks = chunk_mesh(md)
        if len(chunks) == 1:
            make_mesh(base, md, rgba)
        else:
            assert len(chunks) <= 26, f"{base}: {len(chunks)} chunks — extend the suffix scheme"
            for ci, cmd in enumerate(chunks):
                make_mesh(f"{base}_{chr(65 + ci)}", cmd, rgba)
            print(f"[blend] {base}: pre-chunked into {len(chunks)} meshes under the 65,535-vert cap")
    print(f"[blend] {len(lampheads)} streetlights placed (collision-checked)"
          + (f" — {len(piece_plan['lamps'])} of them on the north pieces (ledger 0054 P4 D4), "
             f"{len(piece_plan['skipped'])} stations skipped" if piece_plan else ""))

    ys = [p[1] for p in centerline]
    print(f"[blend] loop: {len(centerline)} pts, road elevation {min(ys):.0f}..{max(ys):.0f} m (rel origin {elev0:.0f} m)")
    out = proj / "loop.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"[blend] wrote {out}")


main()

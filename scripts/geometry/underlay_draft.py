"""The data half of the underlay (``scripts/blender/underlay.py``; fleet/REALISM.md §4, V3-PLAN P2 step 3).

Pure stdlib, no ``bpy``: everything the underlay writes into ``<project>/loop.blend`` is computed here, from the
same ``track.config.json`` + ``data/`` the rest of the pipeline reads, so it can be tested without Blender. The
Blender script only turns these dicts into objects inside ``GEN_*`` collections (and never touches ``AUTH_*``).

What it drafts, per role (each role = one ``GEN_<role>`` collection):

  road     ``1ROAD_road``: the engine ribbon on the centreline (``data/centerline.local.json``) at its per-station
           width (``widths_m``, as the widths stage left it — the underlay never invents a width). Same cross
           sections as ``scripts.geometry.ribbon.road_ribbon`` (its tangent, its fold guard ``_cap_offset``),
           plus a centre row so the section can carry a crown. Crossfall comes from data (``data/crossfall.json``:
           ``bank_rad`` = a plane tilt, +left edge up; optional ``crown_pct``); where the file gives no tilt the
           section takes the construction standard's crown, ``road_profile.crossfall.crown_pct`` (default 2 %,
           docs/ROAD-CONSTRUCTION.md "Crown 2%"). Nothing is banked by the underlay (L10 / A6).
  verge    ``1RUNOFF_verge``: the D4 edge strip each side, ``road_profile.verge_m`` wide, flush with the pavement
           edge and laterally level (no lip: Kevin's July "undriveable slop"; level keeps it above the ground the
           prep pins to edge - 0.02 m). D4 A = 0.3-0.5 m gravel (real width, then the real edge); D4 B = 1.0-1.5 m
           firm drivable gravel. ``1RUNOFF`` is the drivable-but-off-track surface every gate already knows.
  terrain  ``1GRASS_terrain_placeholder``: a PLACEHOLDER from the engine's existing terrain path — the 3DEP
           heightfield (``data/heightfield.npy``), ``ribbon.upsample_grid``, ``build_mesh.project_grid``,
           ``ribbon.grass_terrain`` with its corridor refinement and build_mesh's contact pin under the pavement —
           raw survey everywhere else (no cut/fill, no band clamp). P3a's tiered terrain replaces it.
  refs     non-rendering references (curves + empties; the prep drops every non-mesh object): the centreline,
           stations, the corner list, the stacked-leg pairs, the race-turn boxes.

Not drafted, by design: buildings (``GEN_buildings`` is a hook for after Drive 1), connectors / extra roads,
highway or motorway ribbons of any kind (Kevin: "no extra highways"), the environment stage's sine-wave
mountains, lamps. ``FORBIDDEN_PREFIXES`` is checked on every name the underlay emits.

Frames: inputs are local ENU metres (x = E, y = up, z = N); every vertex returned here is already in Blender's
Z-up frame (x = E, y = N, z = up) with drivable faces wound face-up, so the Blender side does no remap.
"""

from __future__ import annotations

import bisect
import copy
import hashlib
import json
import math
from pathlib import Path

from scripts.geometry import ribbon

# role -> collection; the only collections the underlay ever writes or cleans
COLLECTIONS = {"road": "GEN_road", "verge": "GEN_verge", "terrain": "GEN_terrain", "refs": "GEN_refs"}
# GEN_buildings: V3-PLAN P2 step 3 lists it, Drive 1 does not ("the road and the ground, nothing else"). The hook is
# BUILDINGS_HOOK below; when it lands it is one more role here and one more builder, nothing else changes.
BUILDINGS_HOOK = "GEN_buildings"

ROAD_NAME = "1ROAD_road"
VERGE_NAME = "1RUNOFF_verge"
TERRAIN_NAME = "1GRASS_terrain_placeholder"

# names the underlay must never emit (Kevin 2026-10-10 "no extra highways"; L1 / 0046 the sine ridge; no lamps
# before Drive 2). Upper-cased prefix match.
FORBIDDEN_PREFIXES = ("HIGHWAY", "HWYSTRUCT", "MOTORWAY", "MOUNTAINS", "LAMP", "LIGHT", "STREETLIGHT", "BUILDING",
                      "HOUSE", "TREE", "PALM", "SCRUB", "AUTH_")

CROWN_PCT_STD = 2.0          # docs/ROAD-CONSTRUCTION.md: "Crown 2%" [std]
# D4 (V3-PLAN Decisions): A = "0.3-0.5 m gravel" [std: ROAD-CONSTRUCTION "verge 0.3-0.5 m gravel"],
# B = "1-1.5 m firm gravel strip" [std: Kevin's D4 B answer]. Ranges, not thresholds: they name the variant.
D4_A = (0.3, 0.5)
D4_B = (1.0, 1.5)
VERGE_MAX_M = 3.0            # anything wider is not a verge (July's 6.4 m drivable shoulder is what D4 removes)

# refs (display only, never a gate)
STATION_STEP_M = 100.0
STACK_SAMPLE_M = 5.0
BOX_MARGIN_M = 8.0


class UnderlayError(SystemExit):
    """A refusal: printed and exit 1 (Blender runs with --python-exit-code 1)."""

    def __init__(self, msg: str):
        super().__init__(f"[underlay] REFUSED: {msg}")


# --- inputs --------------------------------------------------------------------------------------------------------

def _get_dotted(d: dict, key: str):
    cur = d
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _set_dotted(d: dict, key: str, value) -> None:
    parts = key.split(".")
    cur = d
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def apply_variant(cfg: dict, variant: str | None) -> dict:
    """``drive1_variants[variant]`` applied IN MEMORY (dotted keys; ``install_folder`` is the ship chain's, not the
    underlay's, and is ignored). The config file is never written."""
    if not variant:
        return cfg
    table = cfg.get("drive1_variants") or {}
    if variant not in table or variant.startswith("_"):
        known = sorted(k for k in table if not k.startswith("_"))
        raise UnderlayError(f"variant '{variant}' is not in track.config.json drive1_variants (known: {known})")
    out = copy.deepcopy(cfg)
    for k, v in table[variant].items():
        if k.startswith("_") or k == "install_folder":
            continue
        _set_dotted(out, k, v)
    return out


def load_inputs(proj: Path, variant: str | None = None) -> dict:
    proj = Path(proj)
    cfg_p = proj / "track.config.json"
    loc_p = proj / "data" / "centerline.local.json"
    for p in (cfg_p, loc_p):
        if not p.is_file():
            raise UnderlayError(f"missing {p} (run the draft's data steps first: elev -> project -> widths)")
    cfg = apply_variant(json.loads(cfg_p.read_text(encoding="utf-8")), variant)
    local = json.loads(loc_p.read_text(encoding="utf-8"))
    pts = [tuple(float(c) for c in p) for p in local["points_xyz_m"]]
    widths = [float(w) for w in local["widths_m"]]
    if len(pts) < 3:
        raise UnderlayError(f"{loc_p.name}: {len(pts)} points")
    if len(widths) != len(pts):
        raise UnderlayError(f"{loc_p.name}: {len(widths)} widths for {len(pts)} points")
    if min(widths) <= 0:
        raise UnderlayError(f"{loc_p.name}: a non-positive width ({min(widths)})")
    return {"proj": proj, "cfg": cfg, "local": local, "pts": pts, "widths": widths, "variant": variant}


# --- the cross sections --------------------------------------------------------------------------------------------

def is_closed(pts) -> bool:
    return len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6


def arcs(pts) -> list[float]:
    out = [0.0]
    for i in range(1, len(pts)):
        out.append(out[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return out


def crossfall_plan(inp: dict) -> dict:
    """Per-station (bank_rad, crown_frac) and a label saying where they came from."""
    proj, cfg, pts = inp["proj"], inp["cfg"], inp["pts"]
    cf_cfg = _get_dotted(cfg, "road_profile.crossfall") or {}
    crown_pct = float(cf_cfg.get("crown_pct", CROWN_PCT_STD)) if isinstance(cf_cfg, dict) else CROWN_PCT_STD
    rel = cf_cfg.get("file", "data/crossfall.json") if isinstance(cf_cfg, dict) else "data/crossfall.json"
    path = proj / rel
    st = arcs(pts)
    n = len(pts)
    if not path.is_file():
        return {"bank": [0.0] * n, "crown": [crown_pct / 100.0] * n,
                "label": f"no {rel}: the construction standard, {crown_pct:g} % crown everywhere "
                         f"[std: docs/ROAD-CONSTRUCTION.md], nothing tilted"}
    cf = json.loads(path.read_text(encoding="utf-8"))
    cst = [float(s) for s in cf["station_m"]]
    cbk = [float(b) for b in cf["bank_rad"]]
    ccr = cf.get("crown_pct")
    if len(cst) != len(cbk) or not cst or any(b < a for a, b in zip(cst, cst[1:])):
        raise UnderlayError(f"{rel}: station_m / bank_rad must be equal-length, non-empty, ascending")
    if ccr is not None and (not isinstance(ccr, list) or len(ccr) != len(cst)):
        raise UnderlayError(f"{rel}: crown_pct must be a list parallel to station_m")
    sgn = -1.0 if cfg.get("mirror_x") else 1.0

    def interp(vals, s):
        k = bisect.bisect_left(cst, s)
        if k <= 0:
            return vals[0]
        if k >= len(cst):
            return vals[-1]
        t = (s - cst[k - 1]) / max(1e-9, cst[k] - cst[k - 1])
        return vals[k - 1] + t * (vals[k] - vals[k - 1])

    ccr_f = [float(c) for c in ccr] if ccr is not None else None
    bank, crown = [], []
    for s in st:
        b = sgn * interp(cbk, s)
        bank.append(b)
        if ccr_f is not None:
            crown.append(interp(ccr_f, s) / 100.0)
        else:
            crown.append(crown_pct / 100.0 if abs(b) < 1e-9 else 0.0)
    tilted = sum(1 for b in bank if abs(b) >= 1e-9)
    status = cf_cfg.get("status", "unlabelled") if isinstance(cf_cfg, dict) else "unlabelled"
    return {"bank": bank, "crown": crown,
            "label": f"{rel} ({status}): {tilted}/{n} stations tilted (max {100 * math.tan(max(abs(b) for b in bank)):.1f} %), "
                     f"the rest {'its crown_pct' if ccr is not None else f'{crown_pct:g} % crown'}"}


def sections(pts, widths, bank, crown, verge_m: float):
    """One cross section per unique station, local frame: (left_edge, centre, right_edge, left_verge, right_verge).
    The edges are ``ribbon.road_ribbon``'s exactly when crown == 0 (same tangent, same fold guard); the crown drops
    each edge by crown x its own offset; the verge runs level from the edge out to the capped half + verge_m."""
    closed = is_closed(pts)
    m = len(pts) - 1 if closed else len(pts)
    out = []
    for i in range(m):
        x, y, z = pts[i]
        tx, tz = ribbon._horiz_tangent(pts, i, closed)
        nx, nz = -tz, tx                                     # left normal (ribbon's convention)
        half = widths[i] / 2.0
        k = ribbon._signed_curvature(pts, i, closed)
        hl = ribbon._cap_offset(half, k)
        hr = -ribbon._cap_offset(-half, k)
        tb = math.tan(bank[i])
        c = crown[i]
        yl = y + hl * tb - c * hl
        yr = y - hr * tb - c * hr
        left = (x + nx * hl, yl, z + nz * hl)
        right = (x - nx * hr, yr, z - nz * hr)
        vl = vr = None
        if verge_m > 0:
            ol = ribbon._cap_offset(half + verge_m, k)
            orr = -ribbon._cap_offset(-(half + verge_m), k)
            vl = (x + nx * ol, yl, z + nz * ol)
            vr = (x - nx * orr, yr, z - nz * orr)
        out.append((left, (x, y, z), right, vl, vr))
    return out, closed


# --- meshes (Blender frame, face-up) ------------------------------------------------------------------------------

def to_blender(p):
    """local (E, up, N) -> Blender (E, N, up)"""
    return (p[0], p[2], p[1])


def _tri_nz(a, b, c) -> float:
    """z of the (unnormalised) normal of a Blender-frame triangle"""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def face_up(verts, tris):
    """Wind every triangle so its normal points up (+z, Blender); drop zero-area ones (a capped fold). The
    deterministic version of the prep's normal.z<0 flip, done at the source so 1RUNOFF (which the prep does not
    flip) is right too."""
    out = []
    for a, b, c in tris:
        nz = _tri_nz(verts[a], verts[b], verts[c])
        if abs(nz) < 1e-9:
            continue
        out.append((a, b, c) if nz > 0 else (a, c, b))
    return out


def road_mesh(secs, closed):
    verts, tris = [], []
    for left, centre, right, _vl, _vr in secs:
        verts += [to_blender(left), to_blender(centre), to_blender(right)]
    m = len(secs)
    last = m if closed else m - 1
    for i in range(last):
        j = (i + 1) % m
        l0, c0, r0 = 3 * i, 3 * i + 1, 3 * i + 2
        l1, c1, r1 = 3 * j, 3 * j + 1, 3 * j + 2
        tris += [(l0, c0, c1), (l0, c1, l1), (c0, r0, r1), (c0, r1, c1)]
    return {"vertices": verts, "faces": face_up(verts, tris)}


def verge_mesh(secs, closed):
    verts, tris = [], []
    m = len(secs)
    for side in (0, 2):                                      # left (edge index 0, verge 3), right (2, 4)
        base = len(verts)
        for sec in secs:
            verts += [to_blender(sec[side]), to_blender(sec[3 if side == 0 else 4])]
        last = m if closed else m - 1
        for i in range(last):
            j = (i + 1) % m
            a0, b0, a1, b1 = base + 2 * i, base + 2 * i + 1, base + 2 * j, base + 2 * j + 1
            tris += [(a0, b0, b1), (a0, b1, a1)]
    return {"vertices": verts, "faces": face_up(verts, tris)}


def verge_spec(cfg: dict) -> dict | None:
    v = _get_dotted(cfg, "road_profile.verge_m")
    if v is None:
        return None
    try:
        w = float(v)
    except (TypeError, ValueError):
        raise UnderlayError(f"road_profile.verge_m is not a number: {v!r}")
    if w <= 0:
        return None
    if w > VERGE_MAX_M:
        raise UnderlayError(f"road_profile.verge_m {w:g} m is not a verge (> {VERGE_MAX_M:g} m; D4 removes July's 6.4 m)")
    if D4_A[0] <= w <= D4_A[1]:
        mode = "D4 A: real width, then the real edge (0.3-0.5 m gravel)"
    elif D4_B[0] <= w <= D4_B[1]:
        mode = "D4 B: real pavement + a 1-1.5 m firm drivable gravel strip"
    elif cfg.get("drive1_variants"):
        raise UnderlayError(f"road_profile.verge_m {w:g} m is neither D4 A ({D4_A[0]}-{D4_A[1]} m) nor "
                            f"D4 B ({D4_B[0]}-{D4_B[1]} m), and this track declares drive1_variants")
    else:
        mode = "custom"
    return {"width_m": w, "mode": mode}


# --- terrain placeholder ----------------------------------------------------------------------------------------

GROUND_CLEAR_M = 0.02       # the prep's GROUND_CLEAR (scripts/ac/build_kn5_loop.py): ground sits 2 cm under the deck
PAVE_WINDOW_M = 20.0        # build_mesh._pav_at_point's layer window: pavement more than 20 m off the ground is not "its"
REFINE_CELL_M = 2.5         # corridor sub-cells; V3-PLAN P3a's corridor tier is <= 3 m (L3b: smaller than the road)


class _Pavement:
    """Point queries on the drafted pavement (road + verge triangles, Blender frame): the LOWEST surface directly over
    (x, n) within PAVE_WINDOW_M of a reference height — build_mesh._pav_at_point's rule. Stacked legs never overlap
    on the map (>= 13.8 m edge to edge on the Lariat), so a point under one leg's footprint sees only that leg."""

    CELL = 4.0

    def __init__(self, meshes):
        self.tris = []
        self.hash: dict = {}
        self.vhash: dict = {}
        for mesh in meshes:
            v = mesh["vertices"]
            for p in v:
                self.vhash.setdefault((int(p[0] // self.CELL), int(p[1] // self.CELL)), []).append(p)
            for f in mesh["faces"]:
                a, b, c = v[f[0]], v[f[1]], v[f[2]]
                k = len(self.tris)
                self.tris.append((a, b, c))
                for i in range(int(min(a[0], b[0], c[0]) // self.CELL), int(max(a[0], b[0], c[0]) // self.CELL) + 1):
                    for j in range(int(min(a[1], b[1], c[1]) // self.CELL), int(max(a[1], b[1], c[1]) // self.CELL) + 1):
                        self.hash.setdefault((i, j), []).append(k)

    def at(self, x, n, z_ref):
        lo = None
        for k in self.hash.get((int(x // self.CELL), int(n // self.CELL)), ()):
            a, b, c = self.tris[k]
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (n - c[1])) / d
            w1 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (n - c[1])) / d
            w2 = 1.0 - w0 - w1
            if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                z = w0 * a[2] + w1 * b[2] + w2 * c[2]
                if abs(z - z_ref) <= PAVE_WINDOW_M and (lo is None or z < lo):
                    lo = z
        return lo

    def lowest_near(self, x, n, z_ref, r):
        """the lowest pavement vertex within r (on the map) and PAVE_WINDOW_M (in height) of the point, or None"""
        lo = None
        r2 = r * r
        c = self.CELL
        for i in range(int((x - r) // c), int((x + r) // c) + 1):
            for j in range(int((n - r) // c), int((n + r) // c) + 1):
                for p in self.vhash.get((i, j), ()):
                    if (p[0] - x) ** 2 + (p[1] - n) ** 2 <= r2 and abs(p[2] - z_ref) <= PAVE_WINDOW_M \
                            and (lo is None or p[2] < lo):
                        lo = p[2]
        return lo


def terrain_mesh(inp: dict, pavement_meshes=()) -> dict:
    """GEN_terrain PLACEHOLDER, from the engine's existing terrain path and nothing new: the 3DEP heightfield
    (``data/heightfield.npy``), ``ribbon.upsample_grid``, ``build_mesh.project_grid``, and ``ribbon.grass_terrain``
    with its corridor refinement (ledger 0014: refine only the quads the pavement touches, plus a ring) and
    build_mesh's two-sided contact pin at each refined node (the ground under pavement IS the pavement underside,
    GROUND_CLEAR_M below it, with the sagitta charge for crests); within one sub-cell diagonal of the pavement a node
    is held no higher than the lowest pavement near it (clamp_terrain_below_road's one-sided rule, so no triangle
    can rise over the edge). Everywhere else it is raw survey: no cut/fill, no band clamp, no blend — P3a's tiered
    terrain (cut/fill seated leg by leg) replaces all of it. Measured on the Lariat (2026-10-12, after the airoso
    prep): the raw 20 m grid left ground over 8 % of the road's faces (to 1.1 m) and 28 % of the verge's."""
    from scripts.geometry.build_mesh import project_grid, read_npy   # the engine's own functions
    proj, cfg, local = inp["proj"], inp["cfg"], inp["local"]
    npy, meta_p = proj / "data" / "heightfield.npy", proj / "data" / "heightfield.meta.json"
    for p in (npy, meta_p):
        if not p.is_file():
            raise UnderlayError(f"missing {p} (the elev step: scripts.elevation.heightfield)")
    ucfg = cfg.get("underlay") or {}
    up = int(ucfg.get("terrain_upsample", 2))
    skirt = float(ucfg.get("terrain_skirt_m", 500.0))
    grid = read_npy(npy)
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    grid, meta = ribbon.upsample_grid(grid, meta, up)
    o = local["origin"]
    grid_xyz = project_grid(grid, meta, (float(o["lon"]), float(o["lat"])), float(o["elev_m"]),
                            mirror_x=bool(cfg.get("mirror_x")))
    nxg, nyg = len(grid_xyz[0]), len(grid_xyz)
    cell = float(meta["spacing_m"])
    N = max(1, int(math.ceil(cell / float(ucfg.get("terrain_refine_cell_m", REFINE_CELL_M)))))
    pav = _Pavement(pavement_meshes)
    refine: set = set()
    stats = {"pinned": 0, "edge_clamped": 0, "coarse_repinned": 0}
    if pav.tris and N > 1:
        gx0, gz0 = grid_xyz[0][0][0], grid_xyz[0][0][2]
        gdx = grid_xyz[0][1][0] - gx0
        gdz = grid_xyz[1][0][2] - gz0
        for a, b, c in pav.tris:                         # Blender frame: [0] = E (local x), [1] = N (local z)
            iis = [(v[0] - gx0) / gdx for v in (a, b, c)]
            jjs = [(v[1] - gz0) / gdz for v in (a, b, c)]
            for qi in range(int(math.floor(min(iis))) - 1, int(math.floor(max(iis))) + 2):
                for qj in range(int(math.floor(min(jjs))) - 1, int(math.floor(max(jjs))) + 2):
                    if 0 <= qi < nxg - 1 and 0 <= qj < nyg - 1:
                        refine.add((qi, qj))
        s_n = cell / N
        reach = s_n * math.sqrt(2.0)                     # every triangle touching pavement lies within one sub-cell
        #                                                  diagonal of it: hold those nodes under the pavement too

        def pin(px, pz, base_y):
            lo = pav.at(px, pz, base_y)
            if lo is None:                               # off the pavement: one-sided, raw survey unless it would
                near = pav.lowest_near(px, pz, base_y, reach)   # lift a triangle over the pavement edge
                if near is not None and base_y > near - GROUND_CLEAR_M:
                    stats["edge_clamped"] += 1
                    return near - GROUND_CLEAR_M
                return base_y
            for ex, ez in ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)):   # chord under a crest: the sagitta
                ym = pav.at(px + ex * s_n * 0.5, pz + ez * s_n * 0.5, base_y)
                if ym is None:
                    continue
                yn = pav.at(px + ex * s_n, pz + ez * s_n, base_y)
                need = (2.0 * ym - yn) if yn is not None else ym
                lo = min(lo, need)
            stats["pinned"] += 1
            return lo - GROUND_CLEAR_M

        for qi, qj in sorted(refine):                    # the refined quads' coarse corners anchor them: re-pin
            for ii, jj in ((qi, qj), (qi + 1, qj), (qi, qj + 1), (qi + 1, qj + 1)):
                vx, vy, vz = grid_xyz[jj][ii]
                ny_ = pin(vx, vz, vy)
                if abs(ny_ - vy) > 1e-4:
                    grid_xyz[jj][ii] = (vx, ny_, vz)
                    stats["coarse_repinned"] += 1
        g = ribbon.grass_terrain(grid_xyz, skirt_m=skirt, refine_quads=refine, refine_factor=N, height_at=pin)
    else:
        N = 1
        g = ribbon.grass_terrain(grid_xyz, skirt_m=skirt)
    verts = [to_blender(v) for v in g["vertices"]]
    return {"vertices": verts, "faces": face_up(verts, g["tris"]),
            "cell_m": cell, "nx": meta["nx"], "ny": meta["ny"], "skirt_m": skirt,
            "refine": {"quads": len(refine), "factor": N, "sub_cell_m": round(cell / N, 2), **stats}}


# --- refs ---------------------------------------------------------------------------------------------------------

def _nearest_index(st, s):
    k = bisect.bisect_left(st, s)
    if k <= 0:
        return 0
    if k >= len(st):
        return len(st) - 1
    return k if st[k] - s < s - st[k - 1] else k - 1


def stacked_pairs(pts, *, max_plan_m: float, min_along_m: float, sample_m: float = STACK_SAMPLE_M):
    """Pairs of lap points < max_plan_m apart on the map and > min_along_m apart along the lap (L4's stacked legs):
    for every sample (every ~sample_m), its nearest qualifying partner. Returns [(i, j, plan_d, dy)]."""
    closed = is_closed(pts)
    m = len(pts) - 1 if closed else len(pts)
    st = arcs(pts)
    lap = st[m] if closed else st[-1]
    step = max(1, int(round(sample_m / max(1e-6, lap / max(1, m - 1)))))
    idx = list(range(0, m, step))
    cell = max_plan_m
    grid: dict = {}
    for i in idx:
        grid.setdefault((int(pts[i][0] // cell), int(pts[i][2] // cell)), []).append(i)
    out = []
    r2 = max_plan_m * max_plan_m
    for i in idx:
        xi, yi, zi = pts[i]
        ci, cj = int(xi // cell), int(zi // cell)
        best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for j in grid.get((ci + di, cj + dj), ()):
                    along = abs(st[j] - st[i])
                    if closed:
                        along = min(along, lap - along)
                    if along <= min_along_m:
                        continue
                    d2 = (pts[j][0] - xi) ** 2 + (pts[j][2] - zi) ** 2
                    if d2 < r2 and (best is None or d2 < best[0]):
                        best = (d2, j)
        if best is not None:
            j = best[1]
            out.append((i, j, round(math.sqrt(best[0]), 2), round(pts[j][1] - yi, 2)))
    return out, step


def refs(inp: dict, secs, closed) -> dict:
    cfg, pts, widths = inp["cfg"], inp["pts"], inp["widths"]
    st = arcs(pts)
    m = len(secs)
    lap = st[m] if closed else st[-1]
    ucfg = (cfg.get("underlay") or {}).get("refs") or {}
    step = float(ucfg.get("station_step_m", STATION_STEP_M))
    stm = st[:m]
    stations = []
    s = 0.0
    while s < lap - 1e-6:
        i = _nearest_index(stm, s)
        stations.append({"name": f"REF_st_{int(round(s)):05d}", "i": i, "station_m": round(st[i], 1),
                         "location": to_blender(pts[i])})
        s += step
    corners = []
    seen = set()
    for c in (_get_dotted(cfg, "hairpin_fit.corners") or []):
        if not isinstance(c, dict) or c.get("st_m") is None or c.get("id") in seen:
            continue
        i = _nearest_index(stm, float(c["st_m"]))
        seen.add(c["id"])
        corners.append({"name": f"REF_corner_{c['id']}", "id": c["id"], "i": i, "station_m": round(st[i], 1),
                        "radius_m": c.get("radius_m"), "label": c.get("name", ""), "source": "hairpin_fit.corners",
                        "location": to_blender(pts[i])})
    boxes = []
    for b in (_get_dotted(cfg, "race.corridor.boxes") or []):
        if not isinstance(b, dict) or not all(isinstance(b.get(k), int) for k in ("i", "j", "apex")):
            continue
        i0, j0, ax = b["i"], b["j"], b["apex"]
        if not (0 <= i0 < m and 0 <= j0 < m and 0 <= ax < m):
            raise UnderlayError(f"race.corridor.boxes {b.get('corner')}: i/j/apex outside the centreline (0..{m - 1})")
        if b.get("corner") not in seen:
            seen.add(b.get("corner"))
            corners.append({"name": f"REF_corner_{b['corner']}", "id": b["corner"], "i": ax,
                            "station_m": round(st[ax], 1), "radius_m": None, "label": b.get("name", ""),
                            "source": "race.corridor.boxes", "location": to_blender(pts[ax])})
        margin = float(ucfg.get("box_margin_m", BOX_MARGIN_M))
        span = list(range(i0, j0 + 1)) if j0 >= i0 else list(range(i0, m)) + list(range(0, j0 + 1))
        ring_l, ring_r = [], []
        for k in span:
            x, y, z = pts[k]
            tx, tz = ribbon._horiz_tangent(pts, k, closed)
            nx, nz = -tz, tx
            o = widths[k] / 2.0 + margin
            ring_l.append(to_blender((x + nx * o, y, z + nz * o)))
            ring_r.append(to_blender((x - nx * o, y, z - nz * o)))
        boxes.append({"name": f"REF_race_box_{b.get('corner')}", "corner": b.get("corner"),
                      "label": b.get("name", ""), "i": i0, "j": j0, "apex": ax,
                      "ring": ring_l + list(reversed(ring_r))})
    sl = _get_dotted(cfg, "terrain.stacked_legs") or {}
    max_plan = float(sl.get("pair_max_plan_m", 40.0))
    min_along = float(sl.get("pair_min_along_m", 150.0))
    pairs, pstep = stacked_pairs(pts, max_plan_m=max_plan, min_along_m=min_along)
    pair_lines = [(to_blender(pts[i]), to_blender(pts[j])) for i, j, _d, _dy in pairs]
    return {"centreline": [to_blender(p) for p in pts[:m]] + ([to_blender(pts[0])] if closed else []),
            "closed": closed, "lap_m": round(lap, 1), "stations": stations, "corners": corners, "boxes": boxes,
            "pairs": pairs, "pair_lines": pair_lines,
            "pair_rule": {"max_plan_m": max_plan, "min_along_m": min_along, "sample_every_vertices": pstep}}


# --- the whole draft ----------------------------------------------------------------------------------------------

def mesh_digest(mesh: dict) -> str:
    h = hashlib.sha256()
    for v in mesh["vertices"]:
        h.update(("%.4f,%.4f,%.4f;" % v).encode())
    for f in mesh["faces"]:
        h.update(("%d,%d,%d;" % f).encode())
    return h.hexdigest()[:16]


def check_names(names) -> None:
    bad = [n for n in names if n.upper().startswith(FORBIDDEN_PREFIXES)]
    if bad:
        raise UnderlayError(f"refusing to emit {bad}: no highway/motorway ribbons, mountains, lamps, buildings, "
                            f"trees or AUTH_ names from the underlay")


def build(proj, variant: str | None = None, *, with_terrain: bool = True) -> dict:
    """Everything the Blender side writes, plus a report. Raises UnderlayError on any refusal."""
    inp = load_inputs(Path(proj), variant)
    cfg, pts, widths = inp["cfg"], inp["pts"], inp["widths"]
    cf = crossfall_plan(inp)
    vs = verge_spec(cfg)
    secs, closed = sections(pts, widths, cf["bank"], cf["crown"], vs["width_m"] if vs else 0.0)
    road = road_mesh(secs, closed)
    meshes = {"road": {ROAD_NAME: road}}
    if vs:
        meshes["verge"] = {VERGE_NAME: verge_mesh(secs, closed)}
    terrain = None
    if with_terrain:
        terrain = terrain_mesh(inp, [road] + list(meshes.get("verge", {}).values()))
        meshes["terrain"] = {TERRAIN_NAME: {"vertices": terrain["vertices"], "faces": terrain["faces"]}}
    r = refs(inp, secs, closed)
    names = [n for role in meshes.values() for n in role] + ["REF_centreline", "REF_stacked_legs"] + \
        [s["name"] for s in r["stations"]] + [c["name"] for c in r["corners"]] + [b["name"] for b in r["boxes"]]
    check_names(names)
    ws = sorted(widths)
    pairs = r["pairs"]
    report = {
        "variant": variant,
        "lap_m": r["lap_m"], "stations": len(secs), "closed": closed,
        "road": {"name": ROAD_NAME, "verts": len(road["vertices"]), "faces": len(road["faces"]),
                 "width_m": {"min": ws[0], "median": ws[len(ws) // 2], "max": ws[-1],
                             "over_9m": sum(1 for w in widths if w > 9.0)},
                 "crossfall": cf["label"], "digest": mesh_digest(road)},
        "verge": ({"name": VERGE_NAME, **vs, "verts": len(meshes["verge"][VERGE_NAME]["vertices"]),
                   "digest": mesh_digest(meshes["verge"][VERGE_NAME])} if vs else
                  {"name": None, "mode": "none: road_profile.verge_m absent or 0"}),
        "terrain": ({"name": TERRAIN_NAME, "placeholder": True,
                     "replaced_by": "P3a tiered terrain (scripts/geometry/terrain_tiers.py, ledger 0046)",
                     "source": "data/heightfield.npy (3DEP); pinned under the pavement on a refined corridor "
                               "(grass_terrain + build_mesh's contact pin), raw survey elsewhere",
                     "refine": terrain["refine"],
                     "cell_m": round(terrain["cell_m"], 2), "grid": [terrain["nx"], terrain["ny"]],
                     "skirt_m": terrain["skirt_m"], "verts": len(terrain["vertices"])} if terrain else None),
        "refs": {"stations": len(r["stations"]), "corners": [c["id"] for c in r["corners"]],
                 "race_boxes": [b["corner"] for b in r["boxes"]],
                 "stacked_pairs": len(pairs), "pair_rule": r["pair_rule"],
                 "stacked_plan_m_min": min((p[2] for p in pairs), default=None),
                 "stacked_dy_abs_m": ([min(abs(p[3]) for p in pairs), max(abs(p[3]) for p in pairs)] if pairs else None)},
        "not_built": {"GEN_buildings": "hook only (after Drive 1)",
                      "highways": "never (Kevin: no extra highways)", "lamps": "never in the underlay",
                      "mountains": "never (L1)"},
    }
    return {"meshes": meshes, "refs": r, "report": report, "verge": vs, "crossfall": cf["label"]}

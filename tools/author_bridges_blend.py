"""Give the loop's real overcrossings a bridge body: soffit, fascia, abutment walls and pier bents (ledger 0046 fix
round 4, the visual lens; first drafted in an unverified round-2 attempt parked on branch wip-0046-fixround2-prior).

WHY. Ledger 0046 cut the I-8 trench out of the ground (3DEP floor and walls under both overcrossings). The decks
were authored when there was nothing under them to see: ROAD + CURB are single upward-facing sheets, and AC culls
back faces, so from the cut floor (drivable 1GRASS since 0046) the College Ave and Lake Murray Blvd decks read as
paper-thin ribbons with sky under them — no underside, no edge, nothing holding them up. In v0.17.1 there was no
cut to stand in, so this is newly exposed (verify_visual, ship9 and round 3: col_from_W/E, lmb_from_W/E).

WHAT. For every span where the mainline rides an OSM-declared bridge way (the kn5 prep's own rule:
build_kn5_loop.detect_bridge_spans — a centreline point within 14 m of a non-motorway bridge way, padded 8 m) this
pass reads the AUTHORED deck (ROAD + CURB, BVH) and the ground (TERRAIN) every STEP_M, and where the ground stands
more than OPEN_MIN_M under the deck's underside it builds, in BRIDGESTRUCT_<span> (one mesh per span):
  * the soffit: the deck's own cross-section DECK_T_M lower, edge to edge, facing down;
  * the fascia: both outer edges from just under the deck edge to FASCIA_LIP_M under the soffit, facing out;
  * an abutment wall at each end of every opening, where the clearance first reaches ABUT_MIN_M: soffit down to
    the row's lowest ground (buried BURY_M), facing into the opening;
  * pier bents where the I-8 carriageways (the same OSM ways the I-8 corridor was built from, data/osm.json) cross
    the deck: one at the median, one outside each carriageway's outer shoulder (lanes x 3.7 m / 2 + SHOULDER_M), each
    a cap beam under the soffit on COL_SPACING_M columns down into the ground — never inside a carriageway, never
    within PIER_CLEAR_M of an abutment.
Everything is BELOW the deck surface it hangs from (the drive_test obstruction band is 0.25-1.8 m ABOVE a lane), and
the pass refuses (exit 1, loop.blend not saved) if any structure vertex has a ROAD / CURB surface under it (a road
passing beneath is not a case this pass knows how to build) or stands above the deck over it.

VISUAL ONLY: no digit prefix (no physics, never scanned by the gates — audit_mesh reads 1ROAD/1GRASS/HWYSTRUCT/1WALL/
1KERB, drive_test counts it as an obstacle only between deck + 0.25 and + 1.8 m), not a GrassFX mesh, not an occluder
(ext_config's allow-list does not name it). pbr row BRIDGESTRUCT = the concrete building tile; the prep keeps this
pass's box-mapped UVs (it does not planar-project BRIDGESTRUCT). Regenerable: every run removes BRIDGESTRUCT_* first.

Runs INSIDE Blender, in the author stage after gap_mouths (the deck is final):

    blender --background --python-exit-code 1 --python tools/author_bridges_blend.py -- <project-dir>
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]

STEP_M = 1.5            # station spacing along the span
XS_STEP_M = 0.25        # cross-section march when finding the deck's outer edge
XS_MAX_M = 30.0         # no deck is wider than 2 x this
DECK_WIN_M = 3.0        # a deck hit counts within this of the centreline deck height
COL_STEP_M = 3.0        # soffit column spacing across the deck
DECK_T_M = 1.4          # deck + girder depth: soffit = deck - this
FASCIA_OUT_M = 0.04     # the fascia stands this far outside the deck edge (no coplanar fight with the curb face)
FASCIA_TOP_M = 0.03     # ...and starts this far under the deck edge
FASCIA_LIP_M = 0.25     # ...and ends this far under the soffit (the girder's edge beam)
OPEN_MIN_M = 0.5        # a station is OPEN when the ground at any column is this far under the soffit
BUILD_PAD_M = 6.0       # soffit + fascia run this far past the opening (into the embankment, buried)
ABUT_MIN_M = 1.5        # an abutment wall stands where the clearance first reaches this
BURY_M = 1.0            # walls / columns run this far into the ground
SHOULDER_M = 3.0        # carriageway outer shoulder past its lanes
LANE_M = 3.7
PIER_CLEAR_M = 4.0      # a bent stands at least this far inside an abutment wall
COL_SPACING_M = 7.0     # bent column spacing across the deck
COL_R_M = 0.6           # column radius (octagonal prism)
CAP_D_M = 1.6           # cap beam depth along the road
CAP_H_M = 1.0           # cap beam height under the soffit
EDGE_INSET_M = 1.5      # outermost column centre this far inside the deck edge
UV_M = 4.0              # metres per texture repeat (the prep's UV_TILE)
BRIDGE_MATCH_M = 14.0   # build_kn5_loop.BRIDGE_MATCH_M
BRIDGE_PAD_M = 8.0      # build_kn5_loop.BRIDGE_PAD_M


def _tiers_module():
    p = AIROSO / "scripts" / "geometry" / "terrain_tiers.py"
    spec = importlib.util.spec_from_file_location("_airoso_terrain_tiers_b", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def detect_spans(pts, to_local, ways):
    """build_kn5_loop.detect_bridge_spans, the same rule: [(a_m, b_m)] stations of the loop on a non-motorway bridge"""
    segs = []
    for w in ways or []:
        if (w.get("hw") or "") in ("motorway", "motorway_link"):
            continue
        g = [to_local(lon, lat) for lon, lat in w.get("geom", [])]
        segs += [(g[i][0], g[i][1], g[i + 1][0], g[i + 1][1]) for i in range(len(g) - 1)]
    if not segs:
        return []

    def near(x, z):
        for ax, az, bx, bz in segs:
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
            if (x - ax - t * dx) ** 2 + (z - az - t * dz) ** 2 <= BRIDGE_MATCH_M ** 2:
                return True
        return False

    spans, st, open_a, open_b, prev = [], 0.0, None, None, pts[0]
    for i, p in enumerate(pts):
        if i:
            st += math.hypot(p[0] - prev[0], p[2] - prev[2])
            prev = p
        if near(p[0], p[2]):
            if open_a is None:
                open_a = st
            open_b = st
        elif open_a is not None:
            spans.append((max(0.0, open_a - BRIDGE_PAD_M), open_b + BRIDGE_PAD_M))
            open_a = None
    if open_a is not None:
        spans.append((max(0.0, open_a - BRIDGE_PAD_M), open_b + BRIDGE_PAD_M))
    return spans


def seg_cross(p, q, a, b):
    """parameter t on p->q where it crosses segment a->b (2D), or None"""
    r = (q[0] - p[0], q[1] - p[1])
    s = (b[0] - a[0], b[1] - a[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - p[0]) * s[1] - (a[1] - p[1]) * s[0]) / den
    u = ((a[0] - p[0]) * r[1] - (a[1] - p[1]) * r[0]) / den
    return t if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None


def bent_stations(crossings, lo, hi):
    """pier bent stations along the deck from the carriageway crossings [(station, half_width)] inside the opening
    [lo, hi] (abutment wall stations): the median between two carriageways, and one outside each carriageway's outer
    shoulder; never inside a carriageway, never within PIER_CLEAR_M of an abutment. Pure."""
    cs = sorted(crossings)
    out = []
    if len(cs) >= 2:
        (s1, h1), (s2, h2) = cs[0], cs[-1]
        if s2 - h2 - (s1 + h1) > 2.0 * COL_R_M + 1.0:          # a median wide enough to stand in
            out.append(0.5 * ((s1 + h1) + (s2 - h2)))
        out.append(s1 - h1 - 1.0)
        out.append(s2 + h2 + 1.0)
    elif len(cs) == 1:
        s1, h1 = cs[0]
        out += [s1 - h1 - 1.0, s1 + h1 + 1.0]
    keep = []
    for s in out:
        if lo + PIER_CLEAR_M <= s <= hi - PIER_CLEAR_M:
            if all(not (c - h <= s <= c + h) for c, h in cs):
                keep.append(s)
    return sorted(keep)


class Builder:
    """faces in Blender coordinates, each oriented to a wanted normal, own vertices + box UVs"""

    def __init__(self):
        self.V, self.F, self.UV = [], [], []

    def face(self, pts, want):
        pts = [Vector(p) for p in pts]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if len(pts) == 4:
            n = n + (pts[2] - pts[0]).cross(pts[3] - pts[0])
        if n.length < 1e-9:
            return
        if n.dot(Vector(want)) < 0:
            pts = pts[::-1]
            n = -n
        ax = max(range(3), key=lambda k: abs(n[k]))
        uvs = []
        for p in pts:
            if ax == 2:
                uvs.append((p.x / UV_M, p.y / UV_M))
            elif ax == 0:
                uvs.append((p.y / UV_M, p.z / UV_M))
            else:
                uvs.append((p.x / UV_M, p.z / UV_M))
        base = len(self.V)
        self.V += [tuple(p) for p in pts]
        self.F.append(tuple(range(base, base + len(pts))))
        self.UV.append(uvs)

    def prism(self, centre_xy, r, z0, z1, sides=8):
        cx, cy = centre_xy
        ring = [(cx + r * math.cos(2 * math.pi * k / sides), cy + r * math.sin(2 * math.pi * k / sides))
                for k in range(sides)]
        for k in range(sides):
            a, b = ring[k], ring[(k + 1) % sides]
            mx, my = (a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy
            self.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], (mx, my, 0.0))

    def box(self, c, t, n, half_t, half_n, z0, z1):
        """an oriented box: centre c (x, y), along-road unit t, across-road unit n (Blender xy)"""
        P = {}
        for a in (-1, 1):
            for b in (-1, 1):
                P[(a, b)] = (c[0] + t[0] * a * half_t + n[0] * b * half_n, c[1] + t[1] * a * half_t + n[1] * b * half_n)
        for (a1, b1), (a2, b2), w in (((-1, -1), (-1, 1), (-t[0], -t[1], 0)), ((1, -1), (1, 1), (t[0], t[1], 0)),
                                       ((-1, -1), (1, -1), (-n[0], -n[1], 0)), ((-1, 1), (1, 1), (n[0], n[1], 0))):
            p, q = P[(a1, b1)], P[(a2, b2)]
            self.face([(p[0], p[1], z0), (q[0], q[1], z0), (q[0], q[1], z1), (p[0], p[1], z1)], w)
        ring = [P[(-1, -1)], P[(1, -1)], P[(1, 1)], P[(-1, 1)]]
        self.face([(x, y, z0) for x, y in ring], (0, 0, -1))

    def obj(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.V, [], self.F)
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for poly, uvs in zip(me.polygons, self.UV):
            for li, uv in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = uv
            poly.use_smooth = False
            k += 1
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def _bvh(names):
    V, F = [], []
    for nm in names:
        ob = bpy.data.objects.get(nm)
        if ob is None or ob.type != "MESH":
            continue
        M = ob.matrix_world
        off = len(V)
        V += [M @ v.co for v in ob.data.vertices]
        F += [tuple(off + i for i in p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(V, F) if F else None


def _hits_down(tree, x, y, top, bottom):
    """every surface height under (x, y) between top and bottom (Blender z), highest first"""
    out = []
    z = top
    while z > bottom:
        h = tree.ray_cast(Vector((x, y, z)), Vector((0, 0, -1)), z - bottom)
        if h[0] is None:
            break
        out.append(h[0].z)
        z = h[0].z - 1e-3
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    tt = _tiers_module()
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    origin = cl["origin"]
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    sx = -1.0 if cfg.get("mirror_x") else 1.0
    m_lon, m_lat = tt.meters_per_degree(origin["lat"])

    def to_local(lon, lat):
        return sx * (lon - origin["lon"]) * m_lon, (lat - origin["lat"]) * m_lat

    ways = json.loads((data / "bridges.cache.json").read_text(encoding="utf-8")) \
        if (data / "bridges.cache.json").exists() else []
    # every drivable line that rides a declared bridge: the mainline AND the side lines (the opposing carriageway of a
    # divided road is a connector line beside the loop — College Ave's northbound deck over I-8 is one)
    lines = [("loop", pts)]
    cpath = data / "connectors.local.json"
    if cpath.exists():
        for k, c in enumerate(json.loads(cpath.read_text(encoding="utf-8")).get("connectors", [])):
            if len(c.get("points_xyz_m", [])) >= 2:
                lines.append((str(c.get("name") or c.get("id") or f"connector_{k}"),
                              [tuple(p) for p in c["points_xyz_m"]]))
    jobs = [(lname, P, a, b) for lname, P in lines for a, b in detect_spans(P, to_local, ways)]
    spans = jobs
    # the I-8 carriageways: the OSM ways the corridor was built from (corridor.i8.json provenance)
    carriage = []
    cp = data / "corridor.i8.json"
    if cp.exists():
        prov = json.loads(cp.read_text(encoding="utf-8"))["_provenance"]
        osm_p = AIROSO / prov["osm_cache"]
        ids = set(prov.get("chain_a_way_ids", [])) | set(prov.get("chain_b_way_ids", []))
        osm = json.loads(osm_p.read_text(encoding="utf-8"))
        for w in osm["ways"]:
            if w["id"] in ids:
                tags = w.get("tags") or {}
                try:
                    lanes = int(str(tags.get("lanes", "4")).split(";")[0])
                except ValueError:
                    lanes = 4
                g = [to_local(*osm["nodes"][str(n)]) for n in w["nodes"] if str(n) in osm["nodes"]]
                carriage.append((g, lanes * LANE_M / 2.0 + SHOULDER_M, w["id"]))

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    for ob in list(bpy.data.objects):
        if ob.name.upper().startswith("BRIDGESTRUCT"):
            bpy.data.objects.remove(ob, do_unlink=True)
    deck = _bvh(["ROAD", "CURB"])
    ground = _bvh(["TERRAIN"])
    if deck is None or ground is None:
        raise SystemExit("[bridges] loop.blend has no ROAD/CURB or no TERRAIN")

    st = [0.0]

    def at(s):
        """centre (x, z), centreline y, unit tangent (local x, z) at station s"""
        k = max(0, min(len(st) - 2, next((i for i in range(len(st) - 1) if st[i + 1] >= s), len(st) - 2)))
        L = st[k + 1] - st[k] or 1e-9
        u = (s - st[k]) / L
        a, b = pts[k], pts[k + 1]
        tx, tz = (b[0] - a[0]) / L, (b[2] - a[2]) / L
        return (a[0] + (b[0] - a[0]) * u, a[2] + (b[2] - a[2]) * u), a[1] + (b[1] - a[1]) * u, (tx, tz)

    def deck_at(x, z, yref):
        hs = [h for h in _hits_down(deck, x, z, yref + DECK_WIN_M, yref - DECK_WIN_M)]
        return max(hs) if hs else None

    def ground_at(x, z, below):
        h = ground.ray_cast(Vector((x, z, below)), Vector((0, 0, -1)), 400.0)
        return h[0].z if h[0] is not None else None

    report = {"_doc": "ledger 0046 fix round 4: the bridge body under each overcrossing (tools/author_bridges_blend.py)",
              "spans": []}
    n_obj = 0
    for si, (lname, P, a, b) in enumerate(jobs):
        pts = P                                              # at() reads the job's own line
        st = [0.0]
        for p0, p1 in zip(pts, pts[1:]):
            st.append(st[-1] + math.hypot(p1[0] - p0[0], p1[2] - p0[2]))
        rows = []
        s = a
        while s <= b + 1e-6:
            (cx, cz), cy, (tx, tz) = at(s)
            nx, nz = -tz, tx                                 # left of travel (local x, z)
            y0 = deck_at(cx, cz, cy)
            if y0 is None:
                s += STEP_M
                continue
            edges = []
            for sign in (-1, 1):
                o, last, ylast = 0.0, 0.0, y0
                while o < XS_MAX_M:
                    o += XS_STEP_M
                    yh = deck_at(cx + sign * nx * o, cz + sign * nz * o, ylast)
                    if yh is None:
                        break
                    last, ylast = o, yh
                edges.append((last, ylast))
            (eR, yR), (eL, yL) = edges                      # sign -1 = right, +1 = left
            W = eL + eR
            ncol = max(2, int(math.ceil(W / COL_STEP_M)) + 1)
            cols = []
            for k in range(ncol):
                o = -eR + W * k / (ncol - 1)
                x, z = cx + nx * o, cz + nz * o
                yd = deck_at(x, z, y0) if 0 < k < ncol - 1 else (yR if k == 0 else yL)
                yd = y0 if yd is None else yd
                g = ground_at(x, z, yd - 0.05)
                cols.append((o, x, z, yd, g))
            # a station is OPEN where the ground drops away under ANY part of the deck (a cut slope under one edge
            # and air under the other still shows sky under the deck from the floor): the widest clearance counts
            # (a column with no ground under it reads through the hole the terrain leaves under a road: no evidence)
            clear = max([yd - DECK_T_M - g for _o, _x, _z, yd, g in cols if g is not None] or [0.0])
            gmin = min((g for *_r, g in cols if g is not None), default=y0 - DECK_T_M)
            rows.append({"s": s, "c": (cx, cz), "t": (tx, tz), "n": (nx, nz), "y0": y0, "cols": cols,
                         "clear": clear, "gmin": gmin})
            s += STEP_M
        open_idx = [i for i, r in enumerate(rows) if r["clear"] > OPEN_MIN_M]
        rec = {"line": lname, "span_m": [round(a, 1), round(b, 1)], "stations": len(rows)}
        if not open_idx:
            rec["built"] = False
            rec["why"] = f"the ground stands within {OPEN_MIN_M} m of the deck's underside everywhere (an at-grade span)"
            report["spans"].append(rec)
            print(f"[bridges] {lname} span {a:.0f}-{b:.0f} m: at grade, nothing built")
            continue
        # opening runs (contiguous open stations, gaps of one station bridged)
        runs = []
        for i in open_idx:
            if runs and i - runs[-1][1] <= 2:
                runs[-1][1] = i
            else:
                runs.append([i, i])
        i0 = open_idx[0]
        i1 = open_idx[-1]
        pad = int(math.ceil(BUILD_PAD_M / STEP_M))
        lo, hi = max(0, i0 - pad), min(len(rows) - 1, i1 + pad)
        Bd = Builder()

        def B(x, z, y):
            return (x, z, y)                                 # local (x, y, z) -> Blender (x, z, y)

        # soffit + fascia
        for i in range(lo, hi):
            r0, r1 = rows[i], rows[i + 1]
            if len(r0["cols"]) != len(r1["cols"]):
                # resample r1 to r0's column count by offset fraction
                pass
            n0, n1 = len(r0["cols"]), len(r1["cols"])
            m = max(n0, n1)

            def colpt(r, f):
                cs = r["cols"]
                q = f * (len(cs) - 1)
                k = min(int(q), len(cs) - 2)
                u = q - k
                (o0, x0, z0, y0_, _g0), (o1, x1, z1, y1_, _g1) = cs[k], cs[k + 1]
                return x0 + (x1 - x0) * u, z0 + (z1 - z0) * u, (y0_ + (y1_ - y0_) * u) - DECK_T_M
            for k in range(m - 1):
                f0, f1 = k / (m - 1), (k + 1) / (m - 1)
                p00, p01 = colpt(r0, f0), colpt(r0, f1)
                p10, p11 = colpt(r1, f0), colpt(r1, f1)
                Bd.face([B(*p00), B(*p01), B(*p11), B(*p10)], (0, 0, -1))
            for side in (0, -1):
                sgn = -1.0 if side == 0 else 1.0
                quads = []
                for r in (r0, r1):
                    o, x, z, yd, _g = r["cols"][side]
                    nx, nz = r["n"]
                    xo, zo = x + sgn * nx * FASCIA_OUT_M, z + sgn * nz * FASCIA_OUT_M
                    quads.append(((xo, zo, yd - FASCIA_TOP_M), (xo, zo, yd - DECK_T_M - FASCIA_LIP_M)))
                (t0, b0), (t1, b1) = quads
                nx, nz = r0["n"]
                Bd.face([B(*t0), B(*t1), B(*b1), B(*b0)], (sgn * nx, sgn * nz, 0.0))
                # the fascia's underside lip back to the soffit edge
                o, x, z, yd, _g = r0["cols"][side]
                o1_, x1_, z1_, yd1, _g1 = r1["cols"][side]
                Bd.face([B(x, z, yd - DECK_T_M), B(x1_, z1_, yd1 - DECK_T_M), B(*b1), B(*b0)], (0, 0, -1))
        # abutment walls
        walls = []
        for ra, rb in runs:
            for end, step in ((ra, 1), (rb, -1)):
                i = end
                while 0 <= i < len(rows) and (ra <= i <= rb) and rows[i]["clear"] < ABUT_MIN_M:
                    i += step
                if not (ra <= i <= rb):
                    continue
                r = rows[i]
                face_dir = (r["t"][0] * step, r["t"][1] * step)    # into the opening
                bot = r["gmin"] - BURY_M
                cs = r["cols"]
                for k in range(len(cs) - 1):
                    _o0, x0, z0, y0_, _ = cs[k]
                    _o1, x1, z1, y1_, _ = cs[k + 1]
                    Bd.face([B(x0, z0, y0_ - DECK_T_M), B(x1, z1, y1_ - DECK_T_M), B(x1, z1, bot), B(x0, z0, bot)],
                            (face_dir[0], face_dir[1], 0.0))
                walls.append(round(r["s"], 1))
        # pier bents at the I-8 carriageways
        poly = [(r["c"], r["s"]) for r in rows]
        crossings = []
        for g, half, wid in carriage:
            for (p, sp), (q, sq) in zip(poly, poly[1:]):
                for u, v in zip(g, g[1:]):
                    t = seg_cross(p, q, u, v)
                    if t is not None:
                        crossings.append((sp + (sq - sp) * t, half))
        crossings = sorted(set((round(c, 2), h) for c, h in crossings))
        bents = []
        for ra, rb in runs:
            # the abutment stations bound this run's bents
            lo_s, hi_s = rows[ra]["s"], rows[rb]["s"]
            for w in walls:
                if lo_s - 1e-6 <= w <= hi_s + 1e-6:
                    if w - lo_s < hi_s - w:
                        lo_s = max(lo_s, w)
                    else:
                        hi_s = min(hi_s, w)
            inrun = [(c, h) for c, h in crossings if lo_s - 30.0 <= c <= hi_s + 30.0]
            bents += bent_stations(inrun, lo_s, hi_s)
        for bs in bents:
            r = min(rows, key=lambda rr: abs(rr["s"] - bs))
            (cx, cz), cy, (tx, tz) = at(bs)
            nx, nz = -tz, tx
            cs = r["cols"]
            eR, eL = -cs[0][0], cs[-1][0]
            soff = min(c[3] for c in cs) - DECK_T_M
            top = soff - 0.02
            capb = top - CAP_H_M
            half_n = (eL + eR) / 2.0 - 0.5
            mid_o = (eL - eR) / 2.0
            Bd.box((cx + nx * mid_o, cz + nz * mid_o), (tx, tz), (nx, nz), CAP_D_M / 2.0, half_n, capb, top)
            span_w = eL + eR - 2 * EDGE_INSET_M
            ncol = max(2, int(math.ceil(span_w / COL_SPACING_M)) + 1)
            for k in range(ncol):
                o = -eR + EDGE_INSET_M + span_w * k / (ncol - 1)
                x, z = cx + nx * o, cz + nz * o
                g = ground_at(x, z, capb - 0.01)
                if g is None:
                    continue
                Bd.prism((x, z), COL_R_M, g - BURY_M, capb + 0.05)
        name = f"BRIDGESTRUCT_{si}"
        ob = Bd.obj(name)
        n_obj += 1
        # self-checks: nothing under a road surface, nothing standing on a road below
        bad_above, bad_road = [], []
        for v in ob.data.vertices:
            x, z, y = v.co
            over = deck.ray_cast(Vector((x, z, y + 0.005)), Vector((0, 0, 1)), 6.0)
            if over[0] is None:
                # not under the deck: it must sit below the nearest deck edge it was built from
                pass
            under = deck.ray_cast(Vector((x, z, y - 0.3)), Vector((0, 0, -1)), 80.0)
            if under[0] is not None:
                bad_road.append((round(x, 1), round(z, 1), round(y, 2), round(under[0].z, 2)))
        topmax = max(r["y0"] for r in rows[lo:hi + 1])
        for v in ob.data.vertices:
            if v.co.z > topmax:
                bad_above.append(tuple(round(c, 2) for c in v.co))
        rec.update({"built": True, "object": name, "vertices": len(ob.data.vertices), "faces": len(ob.data.polygons),
                    "opening_m": [round(rows[i0]["s"], 1), round(rows[i1]["s"], 1)],
                    "max_clearance_m": round(max(r["clear"] for r in rows) + DECK_T_M, 2),
                    "abutment_walls_m": walls, "carriageway_crossings_m": [c for c, _h in crossings],
                    "bents_m": [round(x, 1) for x in bents],
                    "road_under_structure": len(bad_road), "above_the_deck": len(bad_above)})
        report["spans"].append(rec)
        print(f"[bridges] {lname} span {a:.0f}-{b:.0f} m: opening {rec['opening_m']}, clearance <= "
              f"{rec['max_clearance_m']} m under the deck, walls at {walls}, carriageways at "
              f"{rec['carriageway_crossings_m']}, bents at {rec['bents_m']} -> {name} ({rec['vertices']} v)")
        if bad_road or bad_above:
            raise SystemExit(f"[bridges] FATAL {name}: {len(bad_road)} structure vertices over a ROAD/CURB surface "
                             f"{bad_road[:4]}, {len(bad_above)} above the deck {bad_above[:4]} — loop.blend NOT saved")
    (data / "bridges.authored.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[bridges] {n_obj} bridge bodies over {len(spans)} declared spans; data/bridges.authored.json; saved loop.blend")


if __name__ == "__main__":
    main()

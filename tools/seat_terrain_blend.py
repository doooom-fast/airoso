"""Seat the terrain under every road at facet-level precision — the verge finer than the road.

Kevin (2026-10-09): "grass cutting through the road ... side street intersections, lots of hovering."
Measured on the built mesh: the Del Cerro hilltop loop had 28 grass-over-road and 37 road-floats up
to 2.58 m; the assembler conforms the 40→20 m terrain GRID NODES to the roads, but a 20 m facet
between nodes cannot follow a steep, curved side street — at a crest it cuts through the deck, in a
dip the road floats over it (docs/PRO-KN5-CONSTRUCTION.md: pro terrain density is a gradient anchored
to the road, the verge finer than the road).

This pass, after build_loop_blend + weld_mouths_blend and BEFORE the island author (the island deck lives in
TERRAIN):
  1. subdivides every TERRAIN face within (half-width + BAND_M) of any connector centreline (edge cuts=1), and
     under the pavement + sidewalk band within FINE_REACH_M of every mouth's cut halves the edges to FINE_EDGE_M
     (the welded approach is a twisted, creased deck; see FINE UNDER THE WELDED APPROACHES in main), and along the
     host's pavement edge at every mouth down to EDGE_FINE_M — the kn5 prep pins the grass vertex by vertex, so the
     grass follows a creased deck only as finely as its vertices stand (budget: the prep tiles 1GRASS into
     equal-width bands and the western one sits near its 65,535 cap — a 0.75 m pass under the mended mainline folds
     put it at 80,362 and the prep refused), and
  1a. (opt-in, ledger 0054 P1 fix round: track.config.json route.weld_exact_deck) under the HOST's lane on the mouth
     side of every exact-deck mouth, over its span + HOST_LANE_PAD_M, halves the edges down to HOST_LANE_FINE_M — see
     HOST LANE UNDER AN EXACT-DECK MOUTH in main; absent the key nothing here changes, and
  1b. removes the terrain from under the inside half of every mainline fold the weld mended (see
     _clear_under_mended_folds: the fan of a climbing corner is no plane a 4.5 m grass facet can lie under),
  2. sets every TERRAIN vertex within the pavement + sidewalk width to deck − LIFT − CLEAR_M (never above
     the deck, never more than a sidewalk grade below it), and blends vertices in the outer band from
     that height back to their own height over the band.

THE DECK IS THE MESH (2026-10-11, side-street mouth fix). The connector rows are read off ROAD (the assembler's
3-per-row layout, tools/mouth_weld.mesh_layout) — the WELDED rows: tools/weld_mouths_blend.py mitres and warps
each connector's end onto its host, so the deck at a mouth corner can stand ±0.6 m off the connector's own
centreline height. Under the connector's pavement the deck is the LOWEST connector ROAD sheet straight above
the vertex (BVH); beside it, the height of the nearest point on that side's ROAD edge row.

THE CUT END IS NOT A DISC (diagnosis 2026-10-11). The nearest-station search clamps to a line's end, so a
connector's cut end used to read as a disc of "connector" (half-width + sidewalk = 14.6 m at Del Cerro) and
every terrain vertex in it — College's own pavement included — was pinned to the connector's height (the
kn5 prep then pinned a grass triangle through College by +0.07..+0.37 m). A connector line no longer seats
any vertex inside its mouth's HOST footprint (data/mouths.json piece/end -> host rows, within MOUTH_REACH_M
of the cut); the host's own seating (the prep's mainline conform, or the host connector's line) owns it.

Runs INSIDE Blender:

    blender --background --python tools/seat_terrain_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402

BAND_M = 8.0        # outer blend band past the sidewalk's grass lip
SIDEWALK_M = 3.1    # curb_face + sidewalk + grade band (build_loop_blend's curb_sidewalk profile)
CLEAR_M = 0.06      # terrain sits this far under the sidewalk's grass lip (road_edge − 0.10)
LIFT = 0.10
MOUTH_REACH_M = 45.0  # a cut end's host footprint is excluded within this of the cut
FINE_EDGE_M = 1.5     # terrain edge length under a welded approach (the prep's own corridor edges are ~4.5 m)
FINE_REACH_M = 38.0   # ... within this of every cut (the weld's 30 m blend + the trunk's half-width)
APPROACH_OFF_M = 3.1  # ... under the connector's pavement and its sidewalk band (pavement alone left grass 0.001-0.003 m
                      # under the road 1 m inside its edge on two approaches)
TIGHT_EDGE_M = 0.75   # ... and under a connector corner of radius < TIGHT_R_FACTOR x half-width within that reach
TIGHT_R_FACTOR = 3.0
FOLD_HOLE_MARGIN_M = 1.0   # terrain kept this far inside a mended fold's trimmed inside edge ...
FOLD_BAND_M = 1.5          # ... and its facets halved within this of that edge ...
FOLD_BAND_EDGE_M = 0.75    # ... down to this
FOLD_PRE_EDGE_M = 2.0      # the fan's own terrain edges halved to this before the clearing (whole faces under it)
FOLD_PRE_PAD_M = 2.0       # ... out to the rows' half-width + this
EDGE_FINE_M = 0.6     # terrain edge length along the host's pavement edge at a mouth ...
EDGE_BAND_M = 1.2     # ... within this either side of that edge ...
EDGE_REACH_M = 20.0   # ... and this of the cut (Del Cerro: half-width / sin(angle) 12.3 m + a corner)
HOST_LANE_FINE_M = 0.75   # [invented] ledger 0054 P1 fix round, opt-in (route.weld_exact_deck): terrain edge length
                          # under the HOST's lane on the mouth side of an exact-deck mouth ...
HOST_LANE_PAD_M = 4.0     # ... over the mouth's span (connector half-width / sin(angle)) + this each way (verify_mouths'
                          # HOST LANE window is span + 3.0 m) ...
HOST_LANE_IN_M = 1.0      # ... from this far across the host centre line to its edge + 0.5 m


class Roads:
    """the connector lines as the MESH has them: per line its rows (L, C, R) in local (x, y, z)"""

    def __init__(self, lines, cell=30.0):
        self.lines = lines                    # [{"name", "rows", "cuts": [(x, z, HostDeck)]}]
        self.cell = cell
        self.cells = {}
        for li, ln in enumerate(lines):
            rows = ln["rows"]
            for i in range(len(rows) - 1):
                for r in (rows[i], rows[i + 1]):
                    c = r[1]
                    self.cells.setdefault((int(c[0] // cell), int(c[2] // cell)), set()).add((li, i))

    def _past_mouth(self, ln, x, z):
        for cx, cz, deck in ln["cuts"]:
            if math.hypot(x - cx, z - cz) <= MOUTH_REACH_M and deck.inside(x, z):
                return True
        return False

    def nearest(self, x, z):
        """(edge distance, line index, segment, side) of the nearest connector line that may seat (x, z), or None"""
        best = None
        cx, cz = int(x // self.cell), int(z // self.cell)
        skip = {}
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (li, i) in self.cells.get((cx + dx, cz + dz), ()):
                    ln = self.lines[li]
                    if li not in skip:
                        skip[li] = bool(ln["cuts"]) and self._past_mouth(ln, x, z)
                    if skip[li]:
                        continue
                    rows = ln["rows"]
                    a, b = rows[i][1], rows[i + 1][1]
                    ddx, ddz = b[0] - a[0], b[2] - a[2]
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[2]) * ddz) / L2))
                    d = math.hypot(x - (a[0] + t * ddx), z - (a[2] + t * ddz))
                    lat = (-ddz * (x - a[0]) + ddx * (z - a[2]))
                    side = 1 if lat >= 0 else -1
                    k = 0 if side == 1 else 2
                    h0 = math.hypot(rows[i][k][0] - a[0], rows[i][k][2] - a[2])
                    h1 = math.hypot(rows[i + 1][k][0] - b[0], rows[i + 1][k][2] - b[2])
                    half = h0 * (1 - t) + h1 * t
                    if best is None or d - half < best[0]:
                        best = (d - half, li, i, side)
        return best

    def edge_height(self, li, i, side, x, z):
        """height of the nearest point on line li's `side` ROAD edge row, near segment i"""
        rows = self.lines[li]["rows"]
        k = 0 if side == 1 else 2
        best = None
        for j in range(max(0, i - 4), min(len(rows) - 1, i + 5)):
            a, b = rows[j][k], rows[j + 1][k]
            ddx, ddz = b[0] - a[0], b[2] - a[2]
            L2 = ddx * ddx + ddz * ddz
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[2]) * ddz) / L2))
            d = math.hypot(x - (a[0] + t * ddx), z - (a[2] + t * ddz))
            if best is None or d < best[0]:
                best = (d, a[1] + (b[1] - a[1]) * t)
        return best[1]


def _clear_under_mended_folds(bm, data, rme, lay, host_rows):
    """NO GRASS UNDER A MENDED FOLD (data/mouth_welds.json folds.MAINLINE, tools/weld_mouths_blend.py). The inside of
    a mainline corner tighter than the half-width is now one fan from the centre rows to the apex, and on a climb its
    two legs meet there up to 0.5 m apart in height (Navajo / Jackson, v2315-2324). The kn5 prep pins every grass
    vertex 0.02 m under the road and leaves the grass a 4.5 m plane between them: over the fan those planes stood
    0.04-0.36 m THROUGH the road along 28 m of race_acw's lane (drive_test soft_top). A denser terrain there broke
    the prep's western grass tile (80,362 > 65,535 positions). So the terrain under the fan's inside half — every face
    whose corners all lie under the mainline ROAD and FOLD_HOLE_MARGIN_M or more inside its trimmed inside edge — is
    removed: nothing is left under the pavement there to come through it, and the road's edge still meets the grass
    (the margin, its facets first halved to FOLD_BAND_EDGE_M within FOLD_BAND_M of that edge). Returns (faces
    removed, edges halved)."""
    wp = data / "mouth_welds.json"
    if not wp.exists():
        return 0, 0
    cuts = [c for c in (json.loads(wp.read_text(encoding="utf-8")).get("folds", {}).get("MAINLINE", {}).get("cuts")
                        or []) if c[0] == "road"]
    if not cuts:
        return 0, 0
    mrows = host_rows["MAINLINE"]
    mm = len(mrows)
    closed = lay["MAINLINE"]["closed"]
    regions = []
    for c in cuts:
        lane, k, l = int(c[1]), int(c[-2]), int(c[-1])
        side = 1 if lane == 0 else -1
        idx = [r % mm for r in range(k - 2, l + 4)] if closed else [r for r in range(max(0, k - 2), min(mm, l + 4))]
        edge = [mrows[r][lane] for r in idx]
        ctr = (sum(e[0] for e in edge) / len(edge), sum(e[2] for e in edge) / len(edge))
        reach = max(math.hypot(mrows[r][1][0] - ctr[0], mrows[r][1][2] - ctr[1]) for r in idx) + 5.0
        regions.append((mw.HostDeck(mrows, idx), side, edge, ctr, reach))
    first = 3 * lay["MAINLINE"]["rows"]
    mpolys = [tuple(p.vertices) for p in rme.polygons if max(p.vertices) < first]
    mbvh = BVHTree.FromPolygons([tuple(v.co) for v in rme.vertices], mpolys)

    def edge_dist(edge, x, z):
        best = float("inf")
        for i in range(len(edge) - 1):
            a, b = edge[i], edge[i + 1]
            dx, dz = b[0] - a[0], b[2] - a[2]
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
            best = min(best, math.hypot(x - (a[0] + t * dx), z - (a[2] + t * dz)))
        return best

    def inside(x, z):
        """(region, distance to its trimmed inside edge) when (x, z) is on the inside half of a mended fold, within
        its rows' half-width + FOLD_PRE_PAD_M of the centre line"""
        for reg in regions:
            deck, side, edge, ctr, reach = reg
            if math.hypot(x - ctr[0], z - ctr[1]) > reach:
                continue
            d, kk, _t, lat = deck.project(x, z)
            if lat * side > 0.3 and d <= deck._half(deck.idx[kk], side) + FOLD_PRE_PAD_M:
                return reg, edge_dist(edge, x, z)
        return None, None

    # the terrain there is still the 20 m grid (the prep refines it later): first halve its edges inside the fan to
    # FOLD_PRE_EDGE_M so whole faces lie under it, and those along the trimmed inside edge to FOLD_BAND_EDGE_M
    n_band = 0
    for _round in range(8):
        todo = []
        for e in bm.edges:
            ln_e = e.calc_length()
            if ln_e <= FOLD_BAND_EDGE_M:
                continue
            mx = 0.5 * (e.verts[0].co.x + e.verts[1].co.x)
            mz = 0.5 * (e.verts[0].co.y + e.verts[1].co.y)
            reg, dist = inside(mx, mz)
            if reg is None:
                # just outside the trimmed edge (the corner's inside) counts too: the facets that meet the road there
                for deck, side, edge, ctr, reach in regions:
                    if math.hypot(mx - ctr[0], mz - ctr[1]) <= reach and edge_dist(edge, mx, mz) <= FOLD_BAND_M:
                        todo.append(e)
                        break
                continue
            if dist <= FOLD_BAND_M or ln_e > FOLD_PRE_EDGE_M:
                todo.append(e)
        if not todo:
            break
        n_band += len(todo)
        bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_grid_fill=True)
    under_cache = {}

    def under_road(v):
        key = v.index
        if key not in under_cache:
            under_cache[key] = mbvh.ray_cast((v.co.x, v.co.y, 10000.0), (0.0, 0.0, -1.0))[0] is not None
        return under_cache[key]
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    doomed = []
    for f in bm.faces:
        ok = True
        for v in f.verts:
            reg, dist = inside(v.co.x, v.co.y)
            if reg is None or dist < FOLD_HOLE_MARGIN_M or not under_road(v):
                ok = False
                break
        if ok:
            doomed.append(f)
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
    return len(doomed), n_band


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8")).get("connectors", []) if cp.exists() else []
    mp = data / "mouths.json"
    mouths = json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else []
    lay = mw.mesh_layout(main_pts, conns)

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    road = bpy.data.objects.get("ROAD")
    if road is None:
        raise SystemExit("[seat] no ROAD object")
    rme = road.data
    if len(rme.vertices) != lay["_road_total"]:
        raise SystemExit(f"[seat] ROAD has {len(rme.vertices)} verts, the assembler's layout says {lay['_road_total']} "
                         "— the row order changed; not seating")
    RV = [(v.co.x, v.co.z, v.co.y) for v in rme.vertices]          # Blender (x, z_north, y_up) -> local

    def rows_of(name):
        b = lay[name]
        return [(RV[b["road"] + 3 * r], RV[b["road"] + 3 * r + 1], RV[b["road"] + 3 * r + 2]) for r in range(b["rows"])]

    host_rows = {"MAINLINE": rows_of("MAINLINE")}
    lines = []
    for c in conns:
        rows = rows_of(c["name"])
        cuts = []
        for mo in mouths:
            if mo.get("piece") != c["name"]:
                continue
            h = mo["host"]
            if h not in host_rows:
                host_rows[h] = rows_of(h)
            hx, _hy, hz = mo["cut_xyz"]
            cuts.append((hx, hz, mw.HostDeck(host_rows[h], mw.host_window(host_rows[h], lay[h]["closed"], hx, hz))))
        if rows[0][1] == rows[-1][1] or lay[c["name"]]["closed"]:
            rows = rows + [rows[0]]                                  # a closed line wraps
        lines.append({"name": c["name"], "rows": rows, "cuts": cuts})
    # CONNECTORS ONLY: the kn5 prep (build_kn5_loop "terrain conform": corridor edges split, verts
    # pinned to deck-0.02) already seats the terrain along the MAINLINE; covering it here too pushed
    # a grass tile to 71,821 verts (> 65,535) and the prep refused to export (2026-10-09)
    roads = Roads(lines)
    # the connector ROAD faces (every vertex past the mainline block) — the deck under the pavement
    first = 3 * lay["MAINLINE"]["rows"]
    polys = [tuple(p.vertices) for p in rme.polygons if min(p.vertices) >= first]
    bvh = BVHTree.FromPolygons([tuple(v.co) for v in rme.vertices], polys)

    def lowest_deck(x, z):
        lo, top = None, 10000.0
        for _ in range(8):
            hit = bvh.ray_cast((x, z, top), (0.0, 0.0, -1.0))
            if hit[0] is None:
                break
            lo = hit[0].z
            top = lo - 1e-4
        return lo

    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[seat] no TERRAIN object")
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # Blender (x, y, z) = local (x, z_north, y_up)
    reach = SIDEWALK_M + BAND_M
    near_faces = []
    for f in bm.faces:
        cx = sum(v.co.x for v in f.verts) / len(f.verts)
        cz = sum(v.co.y for v in f.verts) / len(f.verts)
        r = roads.nearest(cx, cz)
        if r is not None and r[0] < reach + 4.0:
            near_faces.append(f)
    edges = {e for f in near_faces for e in f.edges}
    before = len(bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=1, use_grid_fill=True)
    # FINE UNDER THE WELDED APPROACHES: the kn5 prep pins every grass vertex under a road 0.02 m below it and
    # leaves the grass a plane between them (its corridor edges ~4.5 m); over a warped approach the road creases by
    # 1-3 % of grade from row to row, and a 4.5 m grass facet across such a crease stood up to 0.01 m THROUGH the
    # connector (verify_mouths APPROACH, measured on the built road). Under the pavement + sidewalk band within
    # FINE_REACH_M of every cut, terrain edges are halved down to FINE_EDGE_M, so the prep pins the grass at
    # every 1.5 m and a crease can no longer lift a facet over the deck (the budget: the prep tiles 1GRASS into
    # equal-width bands, and the western one — Del Cerro, College, the medium end — sits ~60k of its 65,535 cap).
    # AND ALONG THE HOST EDGE: within EDGE_BAND_M either side of the host's pavement edge at every mouth the edges go
    # down to EDGE_FINE_M. Outside that edge the prep feathers a grass vertex to the NEAREST road point's height —
    # at a mouth corner that is the connector's corner further up the host's grade (+0.07 m over College beside it
    # on the Del Cerro W mouth) — and a 5 m facet from there into the host's pavement stood 0.01 m over College's deck
    # 0.9 m inside its edge (verify_mouths HOST LANE). Short facets keep that lift outside the lane.
    cuts_xz = [(mo["cut_xyz"][0], mo["cut_xyz"][2]) for mo in mouths if mo.get("piece")]
    edge_cuts = [(cx, cz, deck, int(mo["side"])) for ln in lines for (cx, cz, deck) in ln["cuts"]
                 for mo in mouths if mo.get("piece") == ln["name"]
                 and abs(mo["cut_xyz"][0] - cx) < 1e-6 and abs(mo["cut_xyz"][2] - cz) < 1e-6]
    # ... and finer still (TIGHT_EDGE_M) under a connector corner tighter than TIGHT_R_FACTOR x its half-width: its
    # inside rows fan to nearly a point and crease at every row (medium#2+0's right-angle turn 25-29 m from the
    # Lake Murray Blvd mouth left grass 0.001 m over its inside wheel line at 1.5 m)
    tight = []
    for ln in lines:
        rows = ln["rows"]
        n = len(rows)
        flag = [False] * max(1, n - 1)
        for i in range(1, n - 1):
            a, b, c = rows[i - 1][1], rows[i][1], rows[i + 1][1]
            h1 = math.atan2(b[2] - a[2], b[0] - a[0])
            h2 = math.atan2(c[2] - b[2], c[0] - b[0])
            turn = abs((h2 - h1 + math.pi) % (2 * math.pi) - math.pi)
            seg = 0.5 * (math.hypot(b[0] - a[0], b[2] - a[2]) + math.hypot(c[0] - b[0], c[2] - b[2]))
            half = max(math.hypot(rows[i][0][0] - b[0], rows[i][0][2] - b[2]),
                       math.hypot(rows[i][2][0] - b[0], rows[i][2][2] - b[2]))
            if turn > 1e-6 and seg / turn < TIGHT_R_FACTOR * half:
                for j in range(max(0, i - 3), min(n - 1, i + 4)):
                    flag[j] = True
        tight.append(flag)
    # HOST LANE UNDER AN EXACT-DECK MOUTH (ledger 0054 P1 fix round; opt-in by track.config.json route.weld_exact_deck,
    # connector-name prefixes). The kn5 prep pins every grass vertex under a road 0.02 m below it and leaves the grass a
    # plane between them (its corridor edges ~4.5 m). On the J5 corner (Navajo / Jackson, 0050's levelled fan) the
    # host's own deck creases along its centre line (the inside edge eased up to the pinch, the centre left alone): a
    # 4.5 m grass facet across that valley crease stood within 5 mm of the road, 2 mm over it, at v2311-2313 — 11
    # verify_mouths HOST LANE samples, the same 11 on the installed v0.18.0 road (no gate looked there before a mouth
    # did). Under the host's lane on the mouth's side, over its span + HOST_LANE_PAD_M, the terrain edges are halved to
    # HOST_LANE_FINE_M, so the prep pins the grass every 0.75 m and a 2 % crease lifts a facet ~4 mm, not 2.2 cm.
    exact_px = []
    cfgp = proj / "track.config.json"
    if cfgp.exists():
        exact_px = [str(x) for x in (json.loads(cfgp.read_text(encoding="utf-8")).get("route", {})
                                     .get("weld_exact_deck") or [])]
    lane_wins = []
    for ln in lines:
        for cx, cz, deck in ln["cuts"]:
            mo = next((m_ for m_ in mouths if m_.get("piece") == ln["name"]
                       and abs(m_["cut_xyz"][0] - cx) < 1e-6 and abs(m_["cut_xyz"][2] - cz) < 1e-6), None)
            if mo is None or not any(str(mo["connector"]).startswith(px) for px in exact_px):
                continue
            ang = math.radians(max(1.0, min(90.0, float(mo.get("angle_deg") or 90.0))))
            hw = (float(mo.get("connector_width_m") or 10.0) / 2.0) / max(math.sin(ang), 0.05)
            arc = [0.0]
            for k in range(len(deck.idx) - 1):
                arc.append(arc[-1] + math.hypot(deck.rows[deck.idx[k + 1]][1][0] - deck.rows[deck.idx[k]][1][0],
                                                deck.rows[deck.idx[k + 1]][1][2] - deck.rows[deck.idx[k]][1][2]))
            _d, k0, t0, _o = deck.project(cx, cz)
            s_cut = arc[k0] + (arc[k0 + 1] - arc[k0]) * t0
            lane_wins.append((cx, cz, deck, arc, s_cut, hw + HOST_LANE_PAD_M, int(mo["side"])))

    def in_host_lane(mx, mz):
        for cx, cz, deck, arc, s_cut, reach_s, sd in lane_wins:
            if math.hypot(mx - cx, mz - cz) > reach_s + 30.0:
                continue
            _d, k, t, lat = deck.project(mx, mz)
            s_ = arc[k] + (arc[k + 1] - arc[k]) * t
            if abs(s_ - s_cut) > reach_s:
                continue
            if -HOST_LANE_IN_M <= lat * sd <= deck._half(deck.idx[k], sd) + 0.5:
                return True
        return False

    n_fine = n_lane = 0
    for _round in range(8):
        todo = []
        for e in bm.edges:
            ln_e = e.calc_length()
            if ln_e <= EDGE_FINE_M:
                continue
            mx = 0.5 * (e.verts[0].co.x + e.verts[1].co.x)
            mz = 0.5 * (e.verts[0].co.y + e.verts[1].co.y)
            if lane_wins and ln_e > HOST_LANE_FINE_M and in_host_lane(mx, mz):
                todo.append(e)
                n_lane += 1
                continue
            if not any(math.hypot(mx - cx, mz - cz) <= FINE_REACH_M for cx, cz in cuts_xz):
                continue
            if any(math.hypot(mx - cx, mz - cz) <= EDGE_REACH_M and abs(deck.edge_gap(mx, mz, sd, 0.0)) <= EDGE_BAND_M
                   for cx, cz, deck, sd in edge_cuts):
                todo.append(e)
                continue
            r = roads.nearest(mx, mz)
            if r is None or r[0] > APPROACH_OFF_M:
                continue
            if ln_e > (TIGHT_EDGE_M if tight[r[1]][r[2]] else FINE_EDGE_M):
                todo.append(e)
        if not todo:
            break
        n_fine += len(todo)
        bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_grid_fill=True)
    n_hole, n_band = _clear_under_mended_folds(bm, data, rme, lay, host_rows)
    bm.verts.ensure_lookup_table()
    moved = under = 0
    for v in bm.verts:
        r = roads.nearest(v.co.x, v.co.y)
        if r is None:
            continue
        off, li, seg, side = r
        if off > reach:
            continue
        hit = lowest_deck(v.co.x, v.co.y)
        if hit is not None:
            deck, pin = hit, True
            under += 1
        else:
            deck, pin = roads.edge_height(li, seg, side, v.co.x, v.co.y), off <= SIDEWALK_M
        target = deck - LIFT - CLEAR_M        # the grass lip height: road edge − 0.10 − 0.06
        if pin:
            # under the pavement/sidewalk: pinned just below the lip, never above the deck
            v.co.z = target
            moved += 1
        else:
            t = (off - SIDEWALK_M) / BAND_M     # 0 at the lip → 1 at the outer band edge
            goal = target * (1 - t) + v.co.z * t
            # only pull the terrain DOWN when it would stand over the verge, never push it up hard
            if v.co.z > goal:
                v.co.z = goal
                moved += 1
            elif target - v.co.z > 2.5 * (1 - t):
                v.co.z = goal                   # a deep dip under the verge: lift to the blend
                moved += 1
    bm.to_mesh(me)
    bm.free()
    me.update()
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[seat] TERRAIN: {len(near_faces)} faces near roads subdivided ({before} -> {len(me.vertices)} verts); "
          f"{n_fine} edges halved under the welded approaches + along the host edges; "
          f"{n_hole} terrain faces cleared from under the mended mainline folds ({n_band} edges halved along their "
          f"inside edge); "
          f"{moved} verts seated to the verge ({under} under a connector's ROAD, deck read off the welded mesh); "
          f"{sum(len(ln['cuts']) for ln in lines)} cut end(s) stop at their host's pavement; saved loop.blend")
    if lane_wins:
        print(f"[seat] HOST LANE (route.weld_exact_deck): {n_lane} of those edges halved to {HOST_LANE_FINE_M} m under the "
              f"host's lane at {len(lane_wins)} exact-deck mouth(s)")


main()

"""Deck rails on the line's declared decks, Lake Murray's own I-8 bridge rails (ledger 0080, the SD freeway port).

drive_test's own rule (scripts/geometry/drive_test.py, the declared-span note): "a bridge with no railing is the defect,
not the railing". Lake Murray lays its deck rails in the assembler (scripts-v021 build_loop_blend.build_guardrails:
0.95 m double-sided panels GUARDRAIL_SET_M outside both lane edges wherever the lap is within 22 m of its I-8 polyline,
dilated 3 points onto the approaches). That keys on Lake Murray's data/i8.local.json, which a port has none of (and
which would also cut Lake Murray's I-8 trench). This step calls THE SAME function, unchanged, once per declared deck,
with that deck's own stretch of the line standing in for the I-8 polyline: so the rails run over each deck, 22 m past
its ends plus 3 points, exactly as Lake Murray's run past its I-8 cut. Heights and set are Lake Murray's (0.95 m,
0.15 m), not measured here.

The decks: data/lm_intake.json bridges_levelled ([center_m, len_m] on the draft line, the source's capture.bridges),
put on the assembler's smoothed line by index (v021's smoother keeps the point count; stations from the raw snapshot
data/centerline.raw.local.json, the line the decks were keyed to). The mesh is GUARDRAIL (engine-july's AC_NAME ->
1WALL_guard, double-sided as Lake Murray's), written into loop.blend. No declared deck = nothing written.

Opt-in by ship.json step (`deck_rails`, draft); Lake Murray never names it (its assembler lays its own).

    blender --background --python tools/deck_rails_blend.py -- <project-dir>
"""
from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender

AIROSO = Path(__file__).resolve().parents[1]
ASM = AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "blender" / "build_loop_blend.py"


def _assembler(*names):
    tree = ast.parse(ASM.read_text(encoding="utf-8"))
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    ns = {"json": json, "math": math, "bpy": bpy}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(ASM), "exec"), ns)
    return ns


def _network_connector_decks(data: Path):
    """[(name, smoothed points, widths, decks_all ranges)] of the network connectors (ledger 0080 phase 2); [] without."""
    p = data / "connectors.local.json"
    if not p.exists():
        return []
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "v021_smooth", AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py")
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    out = []
    for c in json.loads(p.read_text(encoding="utf-8")).get("connectors") or []:
        if not c.get("network") or not c.get("decks_all"):
            continue
        cpts = sm.smooth_centerline([tuple(q) for q in c["points_xyz_m"]], sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
        out.append((c["name"], [tuple(q) for q in cpts], list(c["widths_m"]), c["decks_all"]))
    return out


# ledger 0080 2a round 3: a connector deck beside a LOWER carriageway (I 8 WB's deck at WB s 9,050-9,150 stands 1.6-2 m
# over the line's, 2 m away: both read off the lidar) is two parallel bridges with open air between them; the deck rail
# on WB's median side stood on nothing (drive_test floating 10, 0.8-1.5 m). Under a real bridge rail is the deck's edge
# girder: here each such rail column's foot is carried down that girder's face to the lower carriageway's pavement
# (ROAD, ray-cast FASCIA_PROBE_M out past the rail), never deeper than FASCIA_MAX_M. A rail with no lower pavement
# beside it is unchanged; the line's rails are Lake Murray's, unchanged.
FASCIA_PROBE_M = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)   # [invented] how far out past the rail the lower carriageway is sought
FASCIA_MIN_M = 0.3                                # [invented] a pavement less than this under the rail's foot is its own
FASCIA_MAX_M = 3.0                                # [invented] the deepest edge girder face (a box girder ~ span / 18)


class _Fascia:
    def __init__(self):
        from mathutils import Vector
        from mathutils.bvhtree import BVHTree
        road = bpy.data.objects["ROAD"]
        mw = road.matrix_world
        self.V = Vector
        self.bvh = BVHTree.FromPolygons([mw @ v.co for v in road.data.vertices],
                                        [tuple(p.vertices) for p in road.data.polygons])

    def _road_y(self, x, z, below):
        # local (x = E, y = up, z = N) -> Blender (x, z, y): the assembler's make_mesh remap
        hit = self.bvh.ray_cast(self.V((x, z, below)), self.V((0.0, 0.0, -1.0)), 50.0)
        return None if hit[0] is None else hit[0].z

    def lower(self, verts):
        """build_guardrails' panels: pairs (bottom, top) per column, in order along each side's run."""
        n = 0
        for k in range(0, len(verts) - 1, 2):
            bx, by, bz = verts[k]
            # outward = away from the deck's own centre: the column's offset from its run neighbour's normal is not
            # kept by build_guardrails, so probe both ways and take the lower pavement found first (the deck's own
            # pavement is at the foot's height, never FASCIA_MIN_M under it)
            j = k + 2 if k + 2 < len(verts) else k - 2
            if j < 0:
                continue
            tx, tz = verts[j][0] - bx, verts[j][2] - bz
            L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            best = None
            for sg in (1.0, -1.0):
                for d in FASCIA_PROBE_M:
                    y = self._road_y(bx + sg * d * nx, bz + sg * d * nz, by + 0.5)
                    if y is not None:
                        if by - y >= FASCIA_MIN_M and (best is None or y > best):
                            best = y
                        break
            if best is not None:
                verts[k] = (bx, max(best, by - FASCIA_MAX_M), bz)
                n += 1
        return n


# ledger 0080 2a round 4: the deck's edge UNDER and behind each rail. build_guardrails draws a bridge rail as a panel
# GUARDRAIL_SET_M (0.15 m) outside the pavement's edge, "on the curb's top" (Lake Murray's wide sidewalk); the freeway's
# edge strip is 0.1 m (curb_face_w + connector_sidewalk_w), so on every port deck the panel stood 0.05 m past the last
# built surface, over the ground: drive_test read the drop between the pavement and the rail as unguarded (the line's
# deck-station excursions at s 1,201 / 3,154 / 3,304 / 3,454 / 6,604 / 6,754 / 7,202, both sides; WB s 7,052's 3.13 m)
# and a panel over a void as floating (WB deck [1811, 1831], 0.9-1.1 m; the lidar reads that deck 8 m over the ground
# between two parallel bridges). A real bridge rail stands ON the deck, which runs out under it to the barrier's outer
# face. So each rail row gets the deck slab's edge: from DECK_EDGE_IN_M inside the row's own pavement edge out to
# DECK_EDGE_M past the panel, just under the pavement's edge height (1KERB_SIDEWALK_DECK: concrete, collidable). Not laid
# where another carriageway's pavement is under that outer edge, or where the column was carried down a fascia (there the
# deck's edge girder face meets the lower carriageway: round 3).
DECK_EDGE_M = 0.40      # [invented] the deck past the rail panel: a bridge barrier's base (0.3-0.5 m), not measured here
DECK_EDGE_IN_M = 0.10   # [invented] the slab's inner edge tucked under the pavement's edge (no gap at a flare's chord)
DECK_EDGE_DY_M = 0.03   # [invented] the slab's top under the pavement's edge height (never over the pavement)
DECK_EDGE_NAME = "1KERB_SIDEWALK_DECK"


def deck_edges(asm, centerline, widths, wr, stretch, g, road_y, set_m, *, over=22.0, pad=3):
    """The deck-edge slab beside each rail row build_guardrails laid for ``stretch`` (its own run / mask logic, so
    row k here is column k of ``g``). Returns ({vertices, tris}, rows laid, rows skipped)."""
    on = [(asm["_i8_nearest"](stretch, p[0], p[2])[0] < over) for p in centerline]
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
    verts, tris = [], []
    col = 0
    laid = skipped = 0
    gv = g["vertices"]
    for a, b in runs:
        for side in (1, -1):
            rows = []
            for k in range(a, b + 1):
                x, y, z = centerline[k]; px, pz = perp(k)
                foot = gv[2 * col]
                col += 1
                lowered = abs(foot[1] - y) > 1e-6          # carried down a fascia (round 3)
                hin, hout = widths[k] / 2 - DECK_EDGE_IN_M, wr[k] / 2 + set_m + DECK_EDGE_M
                xi, zi = x + px * side * hin, z + pz * side * hin
                xo, zo = x + px * side * hout, z + pz * side * hout
                ey = road_y(x + px * side * (widths[k] / 2 - 0.05), z + pz * side * (widths[k] / 2 - 0.05), y + 1.0)
                ey = (y if ey is None or abs(ey - y) > 0.5 else ey) - DECK_EDGE_DY_M
                other = road_y(xo, zo, ey + 0.5)
                ok = not lowered and (other is None or ey - other > 3.0)
                rows.append((ok, (xi, ey, zi), (xo, ey, zo)))
            for m in range(len(rows) - 1):
                (ok0, i0, o0), (ok1, i1, o1) = rows[m], rows[m + 1]
                if not (ok0 and ok1):
                    skipped += 1
                    continue
                v = len(verts)
                verts += [i0, o0, i1, o1]
                # face up in local (x E, y up, z N) before make_mesh's reflection; the prep turns any down face up
                tris.append((v, v + 1, v + 3)); tris.append((v, v + 3, v + 2))
                laid += 1
    if col * 2 != len(gv):
        raise SystemExit(f"[deck-rails] FATAL: the deck edge read {col} rail columns, build_guardrails laid {len(gv) // 2}")
    return {"vertices": verts, "uvs": [], "tris": tris}, laid, skipped


def main():
    proj = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    data = proj / "data"
    rep = json.loads((data / "lm_intake.json").read_text(encoding="utf-8"))
    decks = rep.get("bridges_levelled") or []
    net = _network_connector_decks(data)
    if not decks and not net:
        print("[deck-rails] no declared deck: nothing written")
        return
    raw = json.loads((data / "centerline.raw.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    loc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cl = [tuple(p) for p in loc["points_xyz_m"]]
    widths = loc["widths_m"]
    if len(raw) != len(cl):
        raise SystemExit(f"[deck-rails] FATAL: the smoothed line has {len(cl)} points, its raw snapshot {len(raw)}")
    st = [0.0]
    for a, b in zip(raw, raw[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    # on a flare (the intake's width_taper widens a step over metres) the pavement edge between two rows is a chord,
    # and a panel set from each row's own half-width crosses it where the next row is wider (drive_test's wheel paths
    # met the panel at s 1,336-1,341 and 3,358-3,364): each row takes the widest of itself and its two neighbours, so
    # the rail stands outside the pavement over the whole flare (at most one row's widening further out)
    wr = [max(widths[max(0, k - 1):k + 2]) for k in range(len(widths))]
    asm = _assembler("_i8_nearest", "build_guardrails", "GUARDRAIL_SET_M", "make_mesh")
    set_m = asm["GUARDRAIL_SET_M"]
    out = {"vertices": [], "uvs": [], "tris": []}
    edge = {"vertices": [], "uvs": [], "tris": []}
    rows = []
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    fascia = _Fascia()

    def add(dst, m):
        off = len(dst["vertices"])
        dst["vertices"] += m["vertices"]
        dst["tris"] += [(p + off, q + off, r + off) for p, q, r in m["tris"]]
    for c, ln in decks:
        a, b = float(c) - float(ln) / 2.0, float(c) + float(ln) / 2.0
        idx = [i for i, s in enumerate(st) if a <= s <= b]
        if len(idx) < 2:
            rows.append({"center_m": c, "len_m": ln, "panels": 0})
            continue
        stretch = [cl[i] for i in idx]
        g = asm["build_guardrails"](cl, wr, stretch)
        add(out, g)
        de, laid, skip = deck_edges(asm, cl, widths, wr, stretch, g, fascia._road_y, set_m)
        add(edge, de)
        rows.append({"center_m": c, "len_m": ln, "panels": len(g["tris"]) // 4, "deck_edge_panels": laid,
                     "deck_edge_skipped": skip})
    # ledger 0080 phase 2: each network connector's decks (tools/network_connectors.py decks_all: measured or levelled),
    # the same call on the connector as the assembler sweeps it (its smoothed points, its widths widest-of-three)
    for name, cpts, cw, ranges in net:
        cwr = [max(cw[max(0, k - 1):k + 2]) for k in range(len(cw))]
        for a, b in ranges:
            stretch = cpts[a:b + 1]
            if len(stretch) < 2:
                continue
            g = asm["build_guardrails"](cpts, cwr, stretch)
            nf = fascia.lower(g["vertices"])
            add(out, g)
            de, laid, skip = deck_edges(asm, cpts, cw, cwr, stretch, g, fascia._road_y, set_m)
            add(edge, de)
            rows.append({"connector": name, "vertices": [a, b], "panels": len(g["tris"]) // 4,
                         "fascia_columns": nf, "deck_edge_panels": laid, "deck_edge_skipped": skip})
    old = bpy.data.objects.get("GUARDRAIL")
    if old is not None:
        raise SystemExit("[deck-rails] FATAL: loop.blend already has a GUARDRAIL (the assembler's I-8 rails): not a port")
    if bpy.data.objects.get(DECK_EDGE_NAME) is not None:
        raise SystemExit(f"[deck-rails] FATAL: loop.blend already has {DECK_EDGE_NAME}")
    asm["make_mesh"]("GUARDRAIL", out, (0.82, 0.82, 0.86, 1.0))
    if edge["tris"]:
        asm["make_mesh"](DECK_EDGE_NAME, edge, (0.66, 0.66, 0.64, 1.0))
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    (data / "deck_rails.json").write_text(json.dumps({"tool": "tools/deck_rails_blend.py", "ledger": "0080",
                                                      "height_m": 0.95, "set_m": set_m,
                                                      "deck_edge": {"mesh": DECK_EDGE_NAME, "past_rail_m": DECK_EDGE_M,
                                                                    "under_edge_m": DECK_EDGE_IN_M,
                                                                    "below_edge_m": DECK_EDGE_DY_M},
                                                      "decks": rows}, indent=1), encoding="utf-8")
    print(f"[deck-rails] {sum(r['panels'] for r in rows)} rail panels on {len(decks)} declared deck(s) "
          f"(Lake Murray's build_guardrails, 0.95 m, set {set_m} m); the deck's edge under them: "
          f"{sum(r.get('deck_edge_panels', 0) for r in rows)} panels laid, "
          f"{sum(r.get('deck_edge_skipped', 0) for r in rows)} skipped (a fascia / another pavement): saved loop.blend")


main()

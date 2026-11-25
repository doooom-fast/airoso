"""THE INVENTORY GATES: the built kn5 against the surveyed inventory (Denver Grand Prix PLAN 4b item 11; ledger 0096).

Kevin, 2026-11-23: "streetlights and road signs that are as accurate as you can make them. Same with road paint ...
Currently track builds don't depend on this." Three gates per class (paint, lamps, signals, signs), each read off the
BUILT kn5 (LAWS L5: never off the scene, the config or the file that placed the thing):

  present        every inventory item of a built grade stands in the kn5 within its grade's tolerance, as the right
                 type, facing the right way
  nothing extra  nothing of that class stands in the kn5 that the inventory does not hold (LAWS L1)
  covered        every metre of the lap and every junction on it has an inventory record or a declared
                 {"none": true}: silence is not a pass

and the report states the share of each grade (measured / detected / tagged): the honest answer to "how accurate".

OPT-IN (Kevin, E1: "Hard gates for Denver, opt-in elsewhere until proven"). A class is gated only where
track.config.json says ``inventory.<class>.gate: true``. With none, this prints that and exits 0, and no chain names
the step. Where it is on it is hard: exit 1 stops the chain, and --force-install does not cover it.

HOW THE KN5 IS READ. Meshes by name prefix (tools/inventory.MESH_PREFIXES, or inventory.<class>.prefixes), in the
chain's frame (kn5 x = east, z = -north; a mirrored or yawed track is refused):

  paint    MARKINGS* is white, YLINE* yellow, ROADTEXT* neither. PRESENT: every 0.5 m along every inventory stripe
           there must be built paint of the item's colour within the grade's tolerance, on 95 % of the item's samples.
           NOTHING EXTRA: every built paint triangle must lie on an inventory stripe of its colour (half the stripe's
           width + the tolerance); the area that does not is summed. A solid line built where the inventory holds a
           broken one fails here: the paint in the gaps is extra. A line's WIDTH is not judged (the pilot over-reads
           thin lines by one to two pixels). inventory.paint.keep_prefixes are declared additions, not looked at.
  posts    lamps (LIGHTPOST*, LAMPHEAD*, LIGHTS*), signals (SIGNAL*), signs (SIGNFACE* and the older sign meshes).
           One item is one object: triangles that share a vertex position, joined to any other such shell that has a
           vertex inside its box (a mast, its arm, its heads). Its POSITION is its foot (a sign: the plate's centre);
           its TYPE is its mesh name (inventory type "mast_arm" -> SIGNAL_MAST_ARM*; inventory.<class>.types maps
           others); it FACES the way its arm reaches from the foot (a sign: the way the plate's face looks; a
           two-sided plate is judged as an axis). An item that gives no facing is counted and not judged.

    python tools/inventory_gate.py <project-dir> [--kn5 <more.kn5> ...] [--class paint ...] [--json <out.json>]

Exit 0 pass or not opted in, 1 a gate failed, 2 the inventory or its declaration could not be read.
Every tolerance is [invented] (tools/inventory.py; fleet/GATES-CHANGELOG.md 2026-11-23).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import inventory as INV  # noqa: E402
import paint_shapes  # noqa: E402

CLUSTER_PAD_M = 0.25       # [invented] a shell with a vertex this near another shell's box is the same object
FOOT_BAND_M = 0.30         # a post's foot: its vertices within this of its lowest
ARM_MIN_M = 0.75           # vertices further than this from the foot's axis are the arm; fewer than 3 = no arm
ARM_OFFSET_MIN_M = 0.30    # an arm whose centre is nearer the axis than this has no direction (two arms back to back)
TWO_SIDED_SHARE = 0.20     # a plate whose net normal is under this share of its area is two-sided
LIST_MAX = 40              # rows of each kind kept in the json


# --- the kn5 --------------------------------------------------------------------------------------------------
def read_kn5(paths) -> list[tuple[str, list, list]]:
    """[(mesh name, [(east, up, north)], [index, ...])] of every mesh of every kn5: local frame, north un-negated"""
    from scripts.ac.kn5_ground_check import _parse_tris
    out = []
    for p in paths:
        for name, P, idx in _parse_tris(Path(p)):
            out.append((name, [(v[0], v[1], -v[2]) for v in P], idx))
    return out


def of_class(meshes, prefixes, keep=()):
    keep = tuple(str(k).upper() for k in keep if str(k))
    return [m for m in meshes if m[0].upper().startswith(prefixes) and not (keep and m[0].upper().startswith(keep))]


# --- paint ----------------------------------------------------------------------------------------------------
def _tri_dist(x, z, a, b, c) -> float:
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(d) > 1e-12:
        w0 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (z - c[1])) / d
        w1 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (z - c[1])) / d
        if w0 >= 0 and w1 >= 0 and 1 - w0 - w1 >= 0:
            return 0.0
    return min(INV.seg_dist(x, z, a, b), INV.seg_dist(x, z, b, c), INV.seg_dist(x, z, c, a))


class TriHash:
    """plan triangles in a grid: the distance from a point to the nearest one"""

    def __init__(self, cell=2.0):
        self.cell = cell
        self.g: dict = {}
        self.n = 0
        self.area = 0.0

    def add(self, a, b, c):
        cell = self.cell
        self.n += 1
        self.area += abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2.0
        for i in range(int(min(a[0], b[0], c[0]) // cell), int(max(a[0], b[0], c[0]) // cell) + 1):
            for j in range(int(min(a[1], b[1], c[1]) // cell), int(max(a[1], b[1], c[1]) // cell) + 1):
                self.g.setdefault((i, j), []).append((a, b, c))

    def within(self, x, z, reach) -> bool:
        cell = self.cell
        r = int(reach // cell) + 1
        ci, cj = int(x // cell), int(z // cell)
        for i in range(ci - r, ci + r + 1):
            for j in range(cj - r, cj + r + 1):
                for a, b, c in self.g.get((i, j), ()):
                    if _tri_dist(x, z, a, b, c) <= reach:
                        return True
        return False


def paint_colour(name: str):
    up = name.upper()
    for colour, pre in INV.PAINT_COLOUR_PREFIX.items():
        if up.startswith(pre):
            return colour
    return None


def gate_paint(inv: INV.Inventory, meshes, ccfg: dict) -> dict:
    tol = INV.tolerances(ccfg, "paint")
    grades = INV.build_grades(ccfg)
    built_paint = {"white": TriHash(), "yellow": TriHash(), None: TriHash()}
    tris = []                                    # (colour, a, b, c, mesh name) in plan
    for name, P, idx in of_class(meshes, INV.mesh_prefixes(ccfg, "paint"), ccfg.get("keep_prefixes") or ()):
        col = paint_colour(name)
        for t in range(0, len(idx) - 2, 3):
            a, b, c = ((P[idx[t + k]][0], P[idx[t + k]][2]) for k in range(3))
            built_paint[col].add(a, b, c)
            tris.append((col, a, b, c, name))
    other = {"white": "yellow", "yellow": "white"}
    # PRESENT
    missing, wrong_type = [], []
    stuck = INV.unbuildable(inv, grades)
    axes = INV.SegHash(4.0)                      # every built-grade stripe axis, for NOTHING EXTRA
    for it in inv.built():
        t = tol[it.grade]
        n = hit = hit_other = 0
        for stroke in it.strokes:
            for pts, w in INV.stripe_axes(stroke):
                for a, b in zip(pts, pts[1:]):
                    axes.add(a, b, (it.colour, w / 2.0 + t))
                for x, z in paint_shapes.resample(pts, INV.PAINT_SAMPLE_M):
                    n += 1
                    if built_paint[it.colour].within(x, z, t):
                        hit += 1
                    elif built_paint[other[it.colour]].within(x, z, t):
                        hit_other += 1
        share = hit / n if n else 0.0
        if share >= INV.PAINT_PRESENT_SHARE:
            continue
        row = {"id": it.id, "grade": it.grade, "type": it.type, "colour": it.colour, "samples": n,
               "found_share": round(share, 3), "tolerance_m": t}
        if n and (hit + hit_other) / n >= INV.PAINT_PRESENT_SHARE:
            wrong_type.append({**row, "built_as": other[it.colour]})
        else:
            missing.append(row)
    # NOTHING EXTRA
    extra_area = 0.0
    cells: dict = {}
    for col, a, b, c, name in tris:
        cx, cz = (a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0
        ok = col is not None and any(d <= reach and tag_col == col
                                     for d, (tag_col, reach) in axes.near(cx, cz, max(tol.values()) + 1.0))
        if ok:
            continue
        ar = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2.0
        extra_area += ar
        k = (int(cx // 5.0), int(cz // 5.0))
        e = cells.setdefault(k, {"x": cx, "z": cz, "area_m2": 0.0, "mesh": name, "colour": col})
        e["area_m2"] += ar
    extras = sorted(cells.values(), key=lambda e: -e["area_m2"])
    built_m = {c: 0.0 for c in INV.PAINT_COLOUR_PREFIX}
    for it in inv.built():
        for stroke in it.strokes:
            for pts, _w in INV.stripe_axes(stroke):
                built_m[it.colour] += INV.polyline_length(pts)
    present_fail = bool(missing or wrong_type or stuck)
    return {
        "tolerance_m": tol, "build_grades": list(grades),
        "built": {"triangles": len(tris), "area_m2": {str(c): round(h.area, 2) for c, h in built_paint.items()}},
        "inventory_stripe_m": {c: round(v, 1) for c, v in built_m.items()},
        "present": {"fail": present_fail, "judged": len(inv.built()), "missing": len(missing),
                    "wrong_type": len(wrong_type), "unbuildable": len(stuck), "facing": "by the stripes' own ends",
                    "missing_rows": missing[:LIST_MAX], "wrong_type_rows": wrong_type[:LIST_MAX],
                    "unbuildable_rows": [{"id": it.id, "grade": it.grade, "why": it.why_not} for it in stuck[:LIST_MAX]]},
        "nothing_extra": {"fail": extra_area > INV.PAINT_EXTRA_AREA_M2, "extra_area_m2": round(extra_area, 3),
                          "limit_m2": INV.PAINT_EXTRA_AREA_M2, "places": len(extras),
                          "rows": [{"x": round(e["x"], 2), "z": round(e["z"], 2), "area_m2": round(e["area_m2"], 3),
                                    "mesh": e["mesh"], "colour": e["colour"]} for e in extras[:LIST_MAX]]},
    }


# --- posts ----------------------------------------------------------------------------------------------------
class Shape:
    """one built object of a post class"""
    __slots__ = ("names", "pts", "tris", "box")

    def __init__(self):
        self.names, self.pts, self.tris = set(), [], []
        self.box = None

    def close(self):
        xs, ys, zs = zip(*self.pts)
        self.box = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    def foot(self):
        y0 = self.box[1]
        low = [p for p in self.pts if p[1] <= y0 + FOOT_BAND_M]
        return sum(p[0] for p in low) / len(low), sum(p[2] for p in low) / len(low)

    def centre(self):
        return sum(p[0] for p in self.pts) / len(self.pts), sum(p[2] for p in self.pts) / len(self.pts)

    def height(self):
        return self.box[4] - self.box[1]

    def arm_bearing(self):
        fx, fz = self.foot()
        far = [p for p in self.pts if math.hypot(p[0] - fx, p[2] - fz) > ARM_MIN_M]
        if len(far) < 3:
            return None
        cx, cz = sum(p[0] for p in far) / len(far) - fx, sum(p[2] for p in far) / len(far) - fz
        if math.hypot(cx, cz) < ARM_OFFSET_MIN_M:
            return None
        return INV.bearing_deg(cx, cz)

    def face_bearing(self):
        """(bearing the plate's face looks, two_sided) from the triangles' own winding; (None, False) = no plan normal.
        The parsed kn5 frame mirrors north, and a mirror turns every triangle's winding over, so the front of a face is
        the kn5-frame normal carried across the mirror: the negative of the cross product taken in this local frame."""
        nx = nz = area = 0.0
        for a, b, c in self.tris:
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            nx -= cx
            nz -= cz
            area += math.sqrt(cx * cx + cy * cy + cz * cz)
        if area <= 1e-12:
            return None, False
        if math.hypot(nx, nz) / area < TWO_SIDED_SHARE:
            # two-sided: the axis the plate stands across, from its largest triangle
            a, b, c = max(self.tris, key=lambda t: _area3(*t))
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx, nz = -(uy * vz - uz * vy), -(ux * vy - uy * vx)
            if math.hypot(nx, nz) < 1e-9:
                return None, True
            return INV.bearing_deg(nx, nz), True
        return INV.bearing_deg(nx, nz), False


def _area3(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return math.sqrt((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2)


def shapes(meshes) -> list[Shape]:
    """the objects a class's meshes hold: shells (triangles sharing a vertex position, 1 mm) joined where one has a
    vertex inside the other's box grown by CLUSTER_PAD_M"""
    key_of: dict = {}
    parent: list[int] = []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    tri_rows = []
    for name, P, idx in meshes:
        ids = []
        for p in P:
            k = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
            if k not in key_of:
                key_of[k] = len(parent)
                parent.append(len(parent))
            ids.append(key_of[k])
        for t in range(0, len(idx) - 2, 3):
            i, j, k = ids[idx[t]], ids[idx[t + 1]], ids[idx[t + 2]]
            union(i, j)
            union(i, k)
            tri_rows.append((i, name, P[idx[t]], P[idx[t + 1]], P[idx[t + 2]]))
    shells: dict = {}
    for i, name, a, b, c in tri_rows:
        s = shells.setdefault(find(i), Shape())
        s.names.add(name)
        s.tris.append((a, b, c))
    pos = {v: k for k, v in key_of.items()}
    for vid, k in pos.items():
        r = find(vid)
        if r in shells:
            shells[r].pts.append(k)
    out = list(shells.values())
    for s in out:
        s.close()
    # join shells: a vertex of one inside the other's grown box
    par = list(range(len(out)))

    def f2(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    grid: dict = {}
    cell = 4.0
    pad = CLUSTER_PAD_M
    for n, s in enumerate(out):
        for i in range(int((s.box[0] - pad) // cell), int((s.box[3] + pad) // cell) + 1):
            for j in range(int((s.box[2] - pad) // cell), int((s.box[5] + pad) // cell) + 1):
                grid.setdefault((i, j), []).append(n)

    def inside(p, box):
        return (box[0] - pad <= p[0] <= box[3] + pad and box[1] - pad <= p[1] <= box[4] + pad
                and box[2] - pad <= p[2] <= box[5] + pad)

    done = set()
    for members in grid.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                a, b = members[x], members[y]
                if (a, b) in done:
                    continue
                done.add((a, b))
                if f2(a) == f2(b):
                    continue
                A, B = out[a], out[b]
                if any(inside(p, B.box) for p in A.pts) or any(inside(p, A.box) for p in B.pts):
                    par[f2(b)] = f2(a)
    merged: dict = {}
    for n, s in enumerate(out):
        m = merged.setdefault(f2(n), Shape())
        m.names |= s.names
        m.pts += s.pts
        m.tris += s.tris
    res = list(merged.values())
    for s in res:
        s.close()
    return res


def gate_posts(cls: str, inv: INV.Inventory, meshes, ccfg: dict) -> dict:
    tol = INV.tolerances(ccfg, cls)
    grades = INV.build_grades(ccfg)
    built = shapes(of_class(meshes, INV.mesh_prefixes(ccfg, cls)))
    is_sign = cls == "signs"
    where = [(s.centre() if is_sign else s.foot()) for s in built]
    items = inv.built()
    stuck = INV.unbuildable(inv, grades)
    pairs = []
    for i, it in enumerate(items):
        want = INV.type_prefix(ccfg, cls, it.type)
        for k, (x, z) in enumerate(where):
            d = math.hypot(x - it.xz[0], z - it.xz[1])
            if d <= tol[it.grade]:
                right = any(n.upper().startswith(want) for n in built[k].names)
                pairs.append((0 if right else 1, d, i, k))
    pairs.sort()
    got_item, got_shape = {}, {}
    for wrong, d, i, k in pairs:
        if i in got_item or k in got_shape:
            continue
        got_item[i] = (k, d, bool(wrong))
        got_shape[k] = i
    missing, wrong_type, wrong_facing = [], [], []
    unjudged = 0
    worst = 0.0
    for i, it in enumerate(items):
        row = {"id": it.id, "grade": it.grade, "type": it.type, "x": round(it.xz[0], 2), "z": round(it.xz[1], 2),
               "tolerance_m": tol[it.grade]}
        if i not in got_item:
            missing.append(row)
            continue
        k, d, wrong = got_item[i]
        worst = max(worst, d)
        row.update({"built": sorted(built[k].names)[:3], "off_m": round(d, 2)})
        if wrong:
            wrong_type.append({**row, "wanted_prefix": INV.type_prefix(ccfg, cls, it.type)})
            continue
        if it.facing_deg is None:
            unjudged += 1
            continue
        if is_sign:
            b, two = built[k].face_bearing()
        else:
            b, two = built[k].arm_bearing(), False
        ftol = INV.FACING_TOL_DEG[it.grade]
        if b is None:
            wrong_facing.append({**row, "wanted_deg": it.facing_deg, "built_deg": None,
                                 "why": "the built object has no direction (no arm, or a level plate)"})
            continue
        diff = INV.angle_diff(b, it.facing_deg)
        if two:
            diff = min(diff, 180.0 - diff)
        if diff > ftol:
            wrong_facing.append({**row, "wanted_deg": it.facing_deg, "built_deg": round(b, 1),
                                 "off_deg": round(diff, 1), "tolerance_deg": ftol, "two_sided": two})
    extra = [{"x": round(where[k][0], 2), "z": round(where[k][1], 2), "meshes": sorted(s.names)[:3],
              "height_m": round(s.height(), 2)} for k, s in enumerate(built) if k not in got_shape]
    return {
        "tolerance_m": tol, "facing_tolerance_deg": INV.FACING_TOL_DEG, "build_grades": list(grades),
        "built": {"objects": len(built)},
        "present": {"fail": bool(missing or wrong_type or wrong_facing or stuck), "judged": len(items),
                    "missing": len(missing), "wrong_type": len(wrong_type), "wrong_facing": len(wrong_facing),
                    "unbuildable": len(stuck), "facing_not_given": unjudged, "worst_off_m": round(worst, 2),
                    "missing_rows": missing[:LIST_MAX], "wrong_type_rows": wrong_type[:LIST_MAX],
                    "wrong_facing_rows": wrong_facing[:LIST_MAX],
                    "unbuildable_rows": [{"id": it.id, "grade": it.grade, "why": it.why_not} for it in stuck[:LIST_MAX]]},
        "nothing_extra": {"fail": bool(extra), "extra": len(extra), "rows": extra[:LIST_MAX]},
    }


# --- the run --------------------------------------------------------------------------------------------------
def check(project_dir, extra_kn5=(), classes=None, meshes=None) -> dict:
    """the verdict for every gated class. ``meshes`` (tests): [(name, [(east, up, north)], indices)] in place of the
    kn5 files. Raises InventoryError on an input that cannot be read."""
    proj = Path(project_dir)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    gated = [c for c in INV.gated_classes(cfg) if classes is None or c in classes]
    out = {"fail": False, "opted_in": bool(gated), "classes": {}}
    if not gated:
        return out
    if cfg.get("mirror_x") or abs(float(cfg.get("true_north_rotation_deg") or 0.0)) > 1e-9:
        raise INV.InventoryError("the inventory gates read the chain's frame (mirror_x false, true_north_rotation_deg 0); "
                                 "this track declares another")
    if meshes is None:
        slug = cfg["slug"]
        kn5 = proj / "build" / f"{slug}.kn5"
        if not kn5.exists():
            kn5 = proj / "build" / slug / f"{slug}.kn5"
        if not kn5.exists():
            raise INV.InventoryError(f"no built kn5 at build/{slug}.kn5")
        paths = [kn5] + [Path(p) for p in extra_kn5 or ()]
        out["kn5"] = [p.name for p in paths]
        meshes = read_kn5(paths)
    origin = INV.origin_of(proj)
    lap = INV.Lap.from_project(proj, (INV.config_of(cfg) or {}).get("line"))
    junctions = INV.load_junctions(proj, cfg, origin)
    for cls in gated:
        ccfg = INV.class_cfg(cfg, cls)
        inv = INV.load_class(proj, cfg, cls, origin)
        r = gate_paint(inv, meshes, ccfg) if cls == "paint" else gate_posts(cls, inv, meshes, ccfg)
        r["covered"] = INV.coverage(inv, lap, junctions, float(ccfg.get("reach_m", INV.REACH_M[cls])),
                                    float(ccfg.get("junction_reach_m", INV.JUNCTION_REACH_M)))
        held = {}
        for it in inv.items:
            if not it.built:
                held[it.why_not] = held.get(it.why_not, 0) + 1
        r.update({"file": ccfg["file"], "grades": inv.grade_shares(), "held_out": held, "not_items": inv.not_items,
                  "none_records": len(inv.nones)})
        r["fail"] = r["present"]["fail"] or r["nothing_extra"]["fail"] or r["covered"]["fail"]
        out["classes"][cls] = r
        out["fail"] = out["fail"] or r["fail"]
    return out


def _pct(v):
    return "n/a" if v is None else f"{100 * v:.1f} %"


def report(res: dict) -> None:
    if not res["opted_in"]:
        print("INVENTORY GATES: not opted in (track.config.json has no inventory.<class>.gate: true); nothing judged")
        return
    print(f"INVENTORY GATES on {' + '.join(res.get('kn5') or ['the meshes given'])}")
    for cls, r in res["classes"].items():
        g, p, x, c = r["grades"], r["present"], r["nothing_extra"], r["covered"]
        print(f"  {cls}: {g['items']} inventory items  measured {g['measured']} ({_pct(g['measured_share'])})  "
              f"detected {g['detected']} ({_pct(g['detected_share'])})  tagged {g['tagged']} ({_pct(g['tagged_share'])})")
        if r["held_out"] or r["not_items"]:
            print(f"    not built by declaration: {r['held_out'] or 'none'}; records that are not items: {r['not_items'] or 'none'}")
        print(f"    present        {'FAIL' if p['fail'] else 'pass'}: {p['judged']} judged, missing {p['missing']}, wrong type "
              f"{p['wrong_type']}, " + (f"wrong facing {p['wrong_facing']} (facing not given: {p['facing_not_given']}), "
                                        if "wrong_facing" in p else "") + f"cannot be built as read {p['unbuildable']}")
        for row in (p["missing_rows"] + p["wrong_type_rows"] + p.get("wrong_facing_rows", []))[:6]:
            print(f"      {json.dumps(row)[:230]}")
        if cls == "paint":
            print(f"    nothing extra  {'FAIL' if x['fail'] else 'pass'}: {x['extra_area_m2']} m2 of built paint in "
                  f"{x['places']} place(s) that no inventory item accounts for (limit {x['limit_m2']} m2)")
        else:
            print(f"    nothing extra  {'FAIL' if x['fail'] else 'pass'}: {x['extra']} built object(s) the inventory does "
                  f"not hold, of {r['built']['objects']} built")
        for row in x["rows"][:6]:
            print(f"      {json.dumps(row)[:230]}")
        print(f"    covered        {'FAIL' if c['fail'] else 'pass'}: {c['uncovered_m']:.0f} m of the {c['lap_m']:.0f} m lap "
              f"with no record within {c['reach_m']:.0f} m and no declared none ({len(c['uncovered_stretches'])} "
              f"stretch(es)); junctions "
              + (c["junction_list"] if c["junctions"] is None else
                 f"{len(c['uncovered_junctions'])} of {c['junctions']} uncovered")
              + f"; contradictions {len(c['contradictions'])}")
        for a, b in c["uncovered_stretches"][:6]:
            print(f"      lap {a:.0f} to {b:.0f} m")
        if c["uncovered_junctions"]:
            print(f"      junctions: {c['uncovered_junctions'][:12]}")
    print(f"  => {'FAIL' if res['fail'] else 'PASS'}")


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    extra, classes, out_json, proj = [], None, None, None
    i = 0
    while i < len(a):
        if a[i] == "--kn5":
            extra.append(a[i + 1]); i += 2
        elif a[i] == "--class":
            classes = (classes or []) + [a[i + 1]]; i += 2
        elif a[i] == "--json":
            out_json = a[i + 1]; i += 2
        else:
            proj = a[i]; i += 1
    if proj is None:
        print(__doc__)
        return 2
    try:
        res = check(proj, extra, classes)
    except INV.InventoryError as e:
        print(f"INVENTORY GATES: cannot be judged: {e}")
        return 2
    report(res)
    if out_json:
        Path(out_json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 1 if res["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())

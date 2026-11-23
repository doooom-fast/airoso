"""The surveyed inventory of a track's paint, streetlights, signals and signs (pure, no bpy; Denver Grand Prix PLAN
4b, ledger 0096). The author step (tools/author_paint_inventory_blend.py) and the gates (tools/inventory_gate.py) both
read an inventory through this module, so "what the inventory says" has one reading. docs/INVENTORY.md is the manual.

OPT-IN. A track with no ``inventory`` key in track.config.json is not touched by anything here:

    "inventory": {
      "junctions": "source/survey/junctions.json",       # {"junctions": [{"id", "lonlat": [lon, lat]}]}
      "paint":   {"file": "source/survey/paint.json", "gate": true, "build_grades": ["measured"]},
      "lamps":   {"file": "source/survey/lamps.json", "gate": true, "types": {"led_cobra": "LIGHTPOST"}},
      "signals": {"file": "source/survey/signals.json", "gate": true},
      "signs":   {"file": "source/survey/signs.json", "gate": true}
    }

``file`` alone makes the chain author from the inventory (paint: tools/author_paint_inventory_blend.py, and the prep
then drops every other paint mesh). ``gate: true`` turns that class's three gates on. Both are off unless written.

FILES. paint.json is the survey pilot's schema as written (tracks/denver-grand-prix/source/survey/pilot/paint.json):
``items[]`` of class line / bar / crosswalk / symbol with lon/lat geometry and a grade. The post classes share one
shape: ``{"items": [{"id", "type", "grade", "lonlat": [lon, lat], "facing_deg"?, "junction"?, "source"?}]}``; the
pilot's poles.json keys (``base_lonlat``, ``arm_bearing_deg``, ``class``, its ``candidates`` / ``by_eye`` lists) are
read too. A surveyed stretch with nothing in it is a record ``{"none": true, "lap_m": [from, to]}`` or
``{"none": true, "junction": "<id>"}`` in the same list (or in a top-level ``"none"`` list).

FRAME. Local metres, x = east, z = north, about data/centerline.local.json's origin: the draft's own conversion
(scripts/geometry/projection._meters_per_degree, restated in tools/paint_shapes.py).

Every tolerance below is [invented] until a survey of a built track calibrates it (fleet/GATES-CHANGELOG.md 2026-11-23).
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paint_shapes  # noqa: E402

CLASSES = ("paint", "lamps", "signals", "signs")
POST_CLASSES = ("lamps", "signals", "signs")
GRADES = ("measured", "detected", "tagged")

# --- [invented] 2026-11-23, every number: PLAN 4b's own words are the only source ("measured: about +-0.5 m",
# "detected: a few metres", "tagged: stood where the standard puts it"); the pilot measured paint at +-0.3 m ----------
TOL_M = {
    "paint":   {"measured": 0.30, "detected": 0.60, "tagged": 3.0},
    "lamps":   {"measured": 0.50, "detected": 3.0, "tagged": 15.0},
    "signals": {"measured": 0.50, "detected": 3.0, "tagged": 15.0},
    "signs":   {"measured": 0.50, "detected": 3.0, "tagged": 15.0},
}
FACING_TOL_DEG = {"measured": 15.0, "detected": 30.0, "tagged": 45.0}
REACH_M = {"paint": 15.0, "lamps": 50.0, "signals": 40.0, "signs": 40.0}   # a lap metre is covered within this of a record
JUNCTION_REACH_M = 30.0        # a junction is covered by a record this near its node
NONE_HALF_WIDTH_M = 25.0       # an item this near the line inside a declared-none stretch contradicts it
PAINT_SAMPLE_M = 0.5           # the present gate reads built paint at this spacing along every inventory stripe
PAINT_PRESENT_SHARE = 0.95     # of an item's samples that must find built paint of its colour
PAINT_EXTRA_AREA_M2 = 0.01     # built paint area no inventory item accounts for, above which nothing-extra fails
DOUBLE_LINE_SPLIT = 1.0 / 3.0  # a "double solid" read w m across both lines is built as two w/3 stripes, w/3 apart

# what the built kn5's meshes are called, per class (upper-case prefixes; track.config.json inventory.<class>.prefixes)
MESH_PREFIXES = {
    "paint":   ("MARKINGS", "YLINE", "ROADTEXT"),
    "lamps":   ("LIGHTPOST", "LAMPHEAD", "LIGHTS"),
    "signals": ("SIGNAL",),
    "signs":   ("SIGNFACE", "SIGNPLATE", "SIGNS", "USSIGN", "EUROSIGN"),
}
# the prefix a typed item's mesh name starts with: <TYPE_PREFIX>_<TYPE>
TYPE_PREFIX = {"lamps": "LIGHTPOST", "signals": "SIGNAL", "signs": "SIGNFACE"}
PAINT_COLOUR_PREFIX = {"white": "MARKINGS", "yellow": "YLINE"}
INVENTORY_PAINT = {"white": "MARKINGS_inv_", "yellow": "YLINE_inv_"}

# the pilot's poles.json classes -> (inventory class, type)
PILOT_POLE_CLASS = (("signal_", "signals"), ("lamp_", "lamps"), ("sign_", "signs"))


class InventoryError(ValueError):
    """the inventory or its declaration cannot be read as written"""


# --- config ---------------------------------------------------------------------------------------------------
def config_of(cfg: dict) -> dict | None:
    inv = cfg.get("inventory")
    return inv if isinstance(inv, dict) and inv else None


def class_cfg(cfg: dict, cls: str) -> dict | None:
    """inventory.<cls> when it names a file, else None"""
    c = (config_of(cfg) or {}).get(cls)
    return c if isinstance(c, dict) and c.get("file") else None


def gated_classes(cfg: dict) -> list[str]:
    return [c for c in CLASSES if (class_cfg(cfg, c) or {}).get("gate") is True]


def tolerances(ccfg: dict, cls: str) -> dict:
    t = dict(TOL_M[cls])
    t.update({k: float(v) for k, v in (ccfg.get("tolerance_m") or {}).items() if k in GRADES})
    return t


def build_grades(ccfg: dict) -> tuple[str, ...]:
    g = ccfg.get("build_grades")
    if g is None:
        return GRADES
    bad = [x for x in g if x not in GRADES]
    if bad:
        raise InventoryError(f"build_grades {bad}: grades are {list(GRADES)}")
    return tuple(g)


def mesh_prefixes(ccfg: dict, cls: str) -> tuple[str, ...]:
    return tuple(str(p).upper() for p in (ccfg.get("prefixes") or MESH_PREFIXES[cls]))


def type_token(t: str) -> str:
    """an inventory type as it appears in a mesh name: upper case, every non-alphanumeric run one underscore"""
    return re.sub(r"[^A-Z0-9]+", "_", str(t).upper()).strip("_")


def type_prefix(ccfg: dict, cls: str, t: str | None) -> str | None:
    """the upper-case prefix a built mesh of this type must start with; None when the item has no type"""
    if not t:
        return None
    m = ccfg.get("types") or {}
    if t in m:
        return str(m[t]).upper()
    return f"{TYPE_PREFIX[cls]}_{type_token(t)}"


# --- geometry -------------------------------------------------------------------------------------------------
def seg_dist(px, pz, a, b) -> float:
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 <= 1e-18 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - (ax + dx * t), pz - (az + dz * t))


def offset_polyline(pts, o: float):
    """the polyline moved ``o`` m to its left (paint_shapes.drape's normal: (-tz, tx) of the neighbours' chord)"""
    out = []
    for k, (x, z) in enumerate(pts):
        a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, tz) or 1e-9
        out.append((x - tz / L * o, z + tx / L * o))
    return out


def polyline_length(pts) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def bearing_deg(dx_east: float, dz_north: float) -> float:
    """compass bearing of a plan vector: 0 = north, 90 = east"""
    return math.degrees(math.atan2(dx_east, dz_north)) % 360.0


def angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


class SegHash:
    """plan segments in a grid: nearest distance from a point to any of them, within a reach"""

    def __init__(self, cell: float = 4.0):
        self.cell = cell
        self.g: dict = {}

    def add(self, a, b, tag):
        c = self.cell
        x0, x1 = sorted((a[0], b[0]))
        z0, z1 = sorted((a[1], b[1]))
        for i in range(int(x0 // c), int(x1 // c) + 1):
            for j in range(int(z0 // c), int(z1 // c) + 1):
                self.g.setdefault((i, j), []).append((a, b, tag))

    def near(self, x, z, reach):
        """[(distance, tag)] for every segment within ``reach`` of (x, z)"""
        c = self.cell
        r = int(reach // c) + 1
        ci, cj = int(x // c), int(z // c)
        out, seen = [], set()
        for i in range(ci - r, ci + r + 1):
            for j in range(cj - r, cj + r + 1):
                for a, b, tag in self.g.get((i, j), ()):
                    k = (a, b, id(tag) if not isinstance(tag, (str, int, tuple)) else tag)
                    if k in seen:
                        continue
                    seen.add(k)
                    d = seg_dist(x, z, a, b)
                    if d <= reach:
                        out.append((d, tag))
        return out


class PointHash:
    def __init__(self, cell: float = 8.0):
        self.cell = cell
        self.g: dict = {}

    def add(self, x, z, tag=None):
        self.g.setdefault((int(x // self.cell), int(z // self.cell)), []).append((x, z, tag))

    def any_within(self, x, z, reach) -> bool:
        c = self.cell
        r = int(reach // c) + 1
        ci, cj = int(x // c), int(z // c)
        r2 = reach * reach
        for i in range(ci - r, ci + r + 1):
            for j in range(cj - r, cj + r + 1):
                for px, pz, _t in self.g.get((i, j), ()):
                    if (px - x) ** 2 + (pz - z) ** 2 <= r2:
                        return True
        return False


# --- the lap --------------------------------------------------------------------------------------------------
class Lap:
    """the line coverage is asked along: plan points (x, z), its stations, closed or open DERIVED (LAWS L13)"""

    def __init__(self, pts_xz):
        self.pts = [(float(p[0]), float(p[1])) for p in pts_xz]
        if len(self.pts) < 2:
            raise InventoryError("the lap line has fewer than 2 points")
        self.closed = len(self.pts) > 3 and math.dist(self.pts[0], self.pts[-1]) < 1e-6
        self.st = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.st.append(self.st[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.st[-1]
        self._h = SegHash(16.0)
        for i, (a, b) in enumerate(zip(self.pts, self.pts[1:])):
            self._h.add(a, b, i)

    @classmethod
    def from_project(cls, proj: Path, rel: str | None = None):
        d = json.loads((Path(proj) / (rel or "data/centerline.local.json")).read_text(encoding="utf-8"))
        return cls([(p[0], p[2]) for p in d["points_xyz_m"]])

    def at(self, s: float):
        s = max(0.0, min(self.length, s))
        lo, hi = 0, len(self.st) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.st[mid] <= s:
                lo = mid
            else:
                hi = mid
        seg = self.st[lo + 1] - self.st[lo]
        t = 0.0 if seg <= 1e-12 else (s - self.st[lo]) / seg
        a, b = self.pts[lo], self.pts[lo + 1]
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t

    def project(self, x: float, z: float, reach: float = 200.0):
        """(station, distance) of the nearest point of the line, or None beyond ``reach``"""
        best = None
        for d, i in self._h.near(x, z, reach):
            if best is None or d < best[0]:
                a, b = self.pts[i], self.pts[i + 1]
                dx, dz = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dz * dz
                t = 0.0 if L2 <= 1e-18 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
                best = (d, self.st[i] + (self.st[i + 1] - self.st[i]) * t)
        return None if best is None else (best[1], best[0])

    def in_span(self, s: float, span) -> bool:
        """is station s inside [a, b]? On a closed lap a > b wraps through the seam (L13: distances wrap too)"""
        a, b = float(span[0]), float(span[1])
        if a <= b:
            return a - 1e-9 <= s <= b + 1e-9
        return self.closed and (s >= a - 1e-9 or s <= b + 1e-9)


# --- reading the files ----------------------------------------------------------------------------------------
class Item:
    __slots__ = ("id", "cls", "type", "grade", "colour", "xz", "strokes", "facing_deg", "junction", "raw", "built",
                 "why_not")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def points(self):
        """plan points that stand for where this item is (coverage, contradictions)"""
        if self.xz is not None:
            return [self.xz]
        out = []
        for s in self.strokes or ():
            out += paint_shapes.resample(s["pts"], 2.0) if len(s["pts"]) > 1 else list(s["pts"])
        return out


class Inventory:
    def __init__(self, cls):
        self.cls = cls
        self.items: list[Item] = []
        self.nones: list[dict] = []        # {"lap_m": [a, b]} | {"junction": id}
        self.not_items: dict = {}          # reason -> count: records the file holds that are not inventory items

    def built(self):
        return [it for it in self.items if it.built]

    def grade_shares(self) -> dict:
        n = len(self.items)
        out = {g: sum(1 for it in self.items if it.grade == g) for g in GRADES}
        return {"items": n, **{g: out[g] for g in GRADES},
                **{g + "_share": (round(out[g] / n, 4) if n else None) for g in GRADES}}


def _xz(origin, q):
    return paint_shapes.to_xz(origin, q)


def paint_strokes(rec: dict, origin: dict) -> list[dict] | None:
    """one pilot-schema paint record -> the stripes it paints, as tools/paint_shapes lines without a colour:
    [{"pts": [(x, z), ...], "w": m, "double_gap_m"?: m}]. None: the record has a position but no shape that can be
    built as read (a symbol whose type was not read)."""
    k = rec.get("class")
    if k == "crosswalk":
        w = float(rec["bar_width_m"])
        return [{"pts": [_xz(origin, p) for p in bar], "w": w} for bar in rec["bars_lonlat"]]
    if k == "bar":
        return [{"pts": [_xz(origin, p) for p in rec["line_lonlat"]], "w": float(rec["width_m"])}]
    if k == "line":
        w = float(rec["width_m"])
        if rec.get("pattern") == "broken":
            return [{"pts": [_xz(origin, p) for p in d], "w": w} for d in rec["dashes_lonlat"]]
        pts = [_xz(origin, p) for p in rec["line_lonlat"]]
        if len(pts) == 1 and rec.get("length_m") and rec.get("bearing_deg") is not None:
            # a fragment the reader kept as its centre, its length and its compass bearing: the same mark, end to end
            h = float(rec["length_m"]) / 2.0
            b = math.radians(float(rec["bearing_deg"]))
            (cx, cz), (ex, ez) = pts[0], (math.sin(b), math.cos(b))
            pts = [(cx - ex * h, cz - ez * h), (cx + ex * h, cz + ez * h)]
        if rec.get("pattern") == "double solid":
            s = w * DOUBLE_LINE_SPLIT
            return [{"pts": pts, "w": s, "double_gap_m": s}]
        return [{"pts": pts, "w": w}]
    return None


def stripe_axes(stroke: dict) -> list[tuple[list, float]]:
    """(centre polyline, width) of every stripe a stroke paints (two for a double line)"""
    return [(offset_polyline(stroke["pts"], (lo + hi) / 2.0), hi - lo) for lo, hi in paint_shapes.stripes(stroke)]


def _none_record(rec: dict):
    if rec.get("none") is not True:
        return None
    if "lap_m" in rec:
        a, b = rec["lap_m"]
        return {"lap_m": [float(a), float(b)]}
    if "junction" in rec:
        return {"junction": str(rec["junction"])}
    raise InventoryError(f'a "none": true record names neither lap_m nor junction: {json.dumps(rec)[:120]}')


def _pilot_pole_class(c: str | None):
    for pre, cls in PILOT_POLE_CLASS:
        if c and c.startswith(pre):
            return cls, c[len(pre):]
    return None, None


def load_class(proj: Path, cfg: dict, cls: str, origin: dict) -> Inventory:
    ccfg = class_cfg(cfg, cls)
    if ccfg is None:
        raise InventoryError(f"track.config.json inventory.{cls} names no file")
    path = Path(proj) / ccfg["file"]
    if not path.exists():
        raise InventoryError(f"inventory.{cls}.file {ccfg['file']} does not exist under {proj}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    return read(doc, cls, origin, ccfg)


def read(doc: dict, cls: str, origin: dict, ccfg: dict | None = None) -> Inventory:
    """an inventory document -> Inventory. ``ccfg`` (inventory.<cls>) picks the grades that are built."""
    ccfg = ccfg or {}
    grades = build_grades(ccfg)
    inv = Inventory(cls)
    recs = list(doc.get("items") or [])
    if cls != "paint":                               # the pilot's poles.json keeps its posts in two lists
        recs += list(doc.get("candidates") or []) + list(doc.get("by_eye") or [])
    for n in doc.get("none") or []:
        inv.nones.append(_none_record({**n, "none": True}))
    seen = set()
    for i, rec in enumerate(recs):
        none = _none_record(rec)
        if none is not None:
            inv.nones.append(none)
            continue
        grade = rec.get("grade")
        if grade not in GRADES:
            inv.not_items[f"grade {grade!r}"] = inv.not_items.get(f"grade {grade!r}", 0) + 1
            continue
        rid = str(rec.get("id") if rec.get("id") is not None else f"{cls}{i:04d}")
        if cls == "paint":
            colour = rec.get("colour")
            strokes = paint_strokes(rec, origin)
            it = Item(id=rid, cls=cls, type=str(rec.get("pattern") or rec.get("class")), grade=grade, colour=colour,
                      raw=rec, strokes=strokes, junction=rec.get("junction"))
            if strokes is None:
                it.xz = _xz(origin, rec["centre_lonlat"]) if rec.get("centre_lonlat") else None
                it.why_not = "its shape was not read (an untyped symbol)"
            elif colour not in PAINT_COLOUR_PREFIX:
                it.why_not = f"colour {colour!r} is not white or yellow"
            elif any(len(s["pts"]) < 2 for s in strokes):
                it.why_not = "a stripe with fewer than 2 points"
        else:
            rcls, rtype = cls, rec.get("type")
            if rtype is None and "class" in rec:             # the pilot's poles.json: class "signal_mast_arm"
                rcls, rtype = _pilot_pole_class(rec.get("class"))
            elif rtype is None and ("base_lonlat" in rec or "lonlat" in rec):
                rcls = None                                  # a post nobody has classed (the shadow reader's "unread")
            if rcls is None:
                inv.not_items["a post with no class read"] = inv.not_items.get("a post with no class read", 0) + 1
                continue
            if rcls != cls:
                continue                                     # another class's post in a shared file: not this gate's
            ll = rec.get("lonlat") or rec.get("base_lonlat")
            if ll is None:
                # a junction-level record with no post position (the pilot's signs.json): it says the class was
                # looked at there, and nothing that can be built or compared
                if rec.get("junction"):
                    inv.not_items["a junction record with no position"] = inv.not_items.get(
                        "a junction record with no position", 0) + 1
                    continue
                raise InventoryError(f"{cls} item {rid}: no lonlat")
            facing = rec.get("facing_deg", rec.get("arm_bearing_deg"))
            it = Item(id=rid, cls=cls, type=rtype, grade=grade, raw=rec, xz=_xz(origin, ll),
                      facing_deg=None if facing is None else float(facing) % 360.0, junction=rec.get("junction"))
            if not rtype:
                it.why_not = "no type"
        if it.id in seen:
            raise InventoryError(f"{cls}: two items share the id {it.id!r}")
        seen.add(it.id)
        if it.why_not is None and it.grade not in grades:
            it.why_not = f"grade {it.grade} is not in build_grades {list(grades)}"
        it.built = it.why_not is None
        inv.items.append(it)
    # the pilot's signs.json: {"junctions": [{"junction", "grade": "tagged", ...}]} with no post positions
    if cls == "signs":
        n = len(doc.get("junctions") or [])
        if n:
            inv.not_items["a junction record with no position"] = inv.not_items.get(
                "a junction record with no position", 0) + n
    return inv


def unbuildable(inv: Inventory, grades) -> list[Item]:
    """items of a built grade that cannot be built as read: a hard stop for the author step and the present gate"""
    return [it for it in inv.items if not it.built and it.grade in grades]


def load_junctions(proj: Path, cfg: dict, origin: dict) -> list[dict] | None:
    """[{"id", "xz"}] from inventory.junctions, or None when the track declares no junction list"""
    rel = (config_of(cfg) or {}).get("junctions")
    if not rel:
        return None
    path = Path(proj) / rel
    if not path.exists():
        raise InventoryError(f"inventory.junctions {rel} does not exist under {proj}")
    out = []
    for j in json.loads(path.read_text(encoding="utf-8")).get("junctions") or []:
        xz = tuple(j["xz"]) if "xz" in j else _xz(origin, j["lonlat"])
        out.append({"id": str(j["id"]), "xz": (float(xz[0]), float(xz[1]))})
    return out


def origin_of(proj: Path) -> dict:
    return json.loads((Path(proj) / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]


# --- covered --------------------------------------------------------------------------------------------------
def coverage(inv: Inventory, lap: Lap, junctions, reach_m: float, junction_reach_m: float = JUNCTION_REACH_M,
             step_m: float = 1.0, none_half_width_m: float = NONE_HALF_WIDTH_M) -> dict:
    """PLAN 4b's third gate for one class. A lap metre is covered when an inventory item of the class lies within
    ``reach_m`` of it, or a declared-none stretch holds it; a junction when an item lies within ``junction_reach_m`` of
    its node (or names it), or a none record names it. An item inside a declared-none stretch contradicts the
    inventory. ``junctions`` None = the track declared no junction list, which is itself not covered."""
    pts = PointHash(max(8.0, reach_m))
    for it in inv.items:
        for x, z in it.points():
            pts.add(x, z, it.id)
    spans = [n["lap_m"] for n in inv.nones if "lap_m" in n]
    none_j = {n["junction"] for n in inv.nones if "junction" in n}
    bad = []                                    # uncovered stretches [from, to]
    n = int(math.floor(lap.length / step_m))
    stations = [k * step_m for k in range(n + 1)]
    if lap.closed and stations and lap.length - stations[-1] < 1e-9:
        stations.pop()                          # L13: the seam is one metre, not two
    run = None
    uncovered = 0
    for s in stations:
        x, z = lap.at(s)
        ok = any(lap.in_span(s, sp) for sp in spans) or pts.any_within(x, z, reach_m)
        if ok:
            if run is not None:
                bad.append(run)
                run = None
        else:
            uncovered += 1
            run = [s, s] if run is None else [run[0], s]
    if run is not None:
        bad.append(run)
    contradictions = []
    for it in inv.items:
        for x, z in it.points()[:1] if it.xz is not None else it.points():
            pr = lap.project(x, z, none_half_width_m)
            if pr is not None and any(lap.in_span(pr[0], sp) for sp in spans):
                contradictions.append({"id": it.id, "lap_m": round(pr[0], 1)})
                break
    junction_rows = []
    if junctions is not None:
        named = {it.junction for it in inv.items if it.junction}
        for j in junctions:
            x, z = j["xz"]
            if j["id"] in none_j:
                if j["id"] in named or pts.any_within(x, z, junction_reach_m):
                    contradictions.append({"id": f"junction {j['id']}", "why": "declared none, and an item stands at it"})
                continue
            if j["id"] not in named and not pts.any_within(x, z, junction_reach_m):
                junction_rows.append(j["id"])
    fail = bool(bad) or bool(junction_rows) or bool(contradictions) or junctions is None
    return {"fail": fail, "lap_m": round(lap.length, 1), "closed": lap.closed, "reach_m": reach_m,
            "uncovered_m": uncovered * step_m, "uncovered_stretches": [[round(a, 1), round(b, 1)] for a, b in bad],
            "junctions": None if junctions is None else len(junctions),
            "junction_list": "not declared (track.config.json inventory.junctions)" if junctions is None else "declared",
            "uncovered_junctions": junction_rows, "none_stretches": len(spans), "none_junctions": len(none_j),
            "contradictions": contradictions}

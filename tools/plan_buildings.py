"""The buildings pipeline's planner: footprints -> class -> height -> form and skins -> the file tools/author_bespoke_blend.py
"blocks" stands (.claude/skills/buildings/SKILL.md).

    python tools/plan_buildings.py <track-dir> <plan.json> [--debug <out.jpg>]

--debug draws the footprints, the sun, every lit reference and every shadow run it measured over the photograph, so the reading can
be laid beside the picture (L12).

Every number in the output names its source (the row's "_h" and "_class"): OSM's own height or building:levels, a shadow MEASURED
on the track's NAIP, or a class default marked [invented]. The footprint is OSM's (Overpass elements, or the buildings-cache schema
tools/fetch_buildings_cache.py writes) or a traced one; nothing is drawn here.

plan.json = {
  "image": "source/naip_2023_hp.jpg", "bbox_lonlat": [w, s, e, n] | "webmerc": {"z", "x0", "y0"},
  "naip_date": "2023-09-28", "utc_offset": "-06:00",             the scene's capture date (its STAC id) and the site's clock
                                                                 that day (this python has no tzdata: an offset, not a zone name)
  "footprints": [{"file": "source/bespoke/osm_buildings.json", "kind": "overpass"},
                 {"file": "data/buildings.traced.json", "kind": "cache"}],
  "out": "source/bespoke/buildings.json",
  "min_area_m2": 25,
  "yes_by_area": [[60, "shed"], [350, "house"], [1500, "commercial"], [1e9, "industrial"]],   an untagged footprint, by size
  "house_skin": "stucco" | "siding",                              the region's houses (DOSSIER section 5)
  "shadow": {"enabled": true, "max_m": 60, "trust_unchecked": false},   off = OSM and defaults only; an unchecked stage (no
                                                                 OSM heights to compare) is used only when trust_unchecked is set
  "sun": {"azimuth_deg": 122, "elevation_deg": 33, "_source": "..."}   optional: a sun read by hand (Nevada's pole shadows)
                                                                 in place of the vote
}

CLASSES, from the OSM building tag first, then by area: house, apartments, commercial, industrial, shed; canopy (building=roof)
is left out. Each class fixes the roof FORM and the SKINS (tools/make_bespoke_assets.py): house = hip roof of shingle on stucco or
siding; apartments = flat with a parapet, stucco; commercial = flat with a parapet, tilt-up; industrial = flat, tilt-up; shed =
low gable, ribbed metal. Flat roofs take the colour class read off the NAIP (white / tan / dark); the parapet and pitch numbers are
[invented] and said so below.

HEIGHTS, in this order per building: OSM height; OSM building:levels x STOREY_M[class]; the shadow on the NAIP; the class default.
The shadow stage: (1) the shadow DIRECTION is voted by every footprint (the darkest of 16 directions just outside its ring, against
the opposite side), (2) the sun's azimuth is the opposite, and scripts/lighting/solar.py gives the time of day on the capture date
that puts the sun there, and its ELEVATION, (3) each building's shadow LENGTH is the run of ground nearer the shadow's own darkness (read
1-2 m out from the sun-away wall) than the lit ground on the sun side, walked from the sun-away edges, median over the edge
samples; height = length x tan(elevation). A run that hits another footprint or the cap, a dark or contrast-less reference
(trees, a lot in shade), too few samples, a wide spread, or a height past the class's cap is not a measurement, and the building
falls back to the next source. NAIP at 0.6 m/px reads a height to about +-0.5 m at a 30-45 deg sun.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

from PIL import Image

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_bespoke_vegetation import geo  # noqa: E402
from scripts.lighting.solar import solar_position  # noqa: E402

TAG_CLASS = {
    "house": "house", "detached": "house", "residential": "house", "semidetached_house": "house", "bungalow": "house",
    "terrace": "house", "cabin": "house", "farm": "house",
    "apartments": "apartments", "dormitory": "apartments",
    "retail": "commercial", "commercial": "commercial", "office": "commercial", "school": "commercial", "church": "commercial",
    "public": "commercial", "civic": "commercial", "hotel": "commercial", "supermarket": "commercial", "hospital": "commercial",
    "kindergarten": "commercial", "university": "commercial", "government": "commercial", "fire_station": "commercial",
    "industrial": "industrial", "warehouse": "industrial", "manufacture": "industrial", "hangar": "industrial", "service": "industrial",
    "shed": "shed", "garage": "shed", "garages": "shed", "carport": "shed", "hut": "shed", "barn": "shed", "storage_tank": "shed",
    "roof": "canopy",
}
# metres per storey: a US house floor at a 9 ft ceiling plus the floor structure (cited from memory, not re-read); other classes
# at the 3.5 m tools/fetch_buildings_cache.py's readers assumed
STOREY_M = {"house": 3.2, "apartments": 3.2, "commercial": 3.8, "industrial": 5.0, "shed": 3.0}
STOREY_MULTI_M = 3.6      # a commercial or industrial building of several storeys: an office or a parking deck, not a stack of
                          # warehouses (Lake Murray's "industrial, 5 levels" stood 25 m tall) [invented]
# class defaults when nothing was measured [invented]: a one-storey house eave, a two-storey apartment block, a one-storey shop,
# a warehouse, a shed
DEFAULT_WALL_M = {"house": 3.0, "apartments": 7.0, "commercial": 4.5, "industrial": 8.0, "shed": 2.8}
# the form each class takes [invented by class]; the hip pitch is 4:12, a common US house pitch (cited from memory)
FORM = {"house": "hip", "apartments": "flat_parapet", "commercial": "flat_parapet", "industrial": "flat", "shed": "gable"}
PITCH = {"hip": 4.0 / 12.0, "gable": 2.0 / 12.0}
MIN_WALL_M = {"house": 2.6, "shed": 2.1}      # [invented] a wall lower than this is not a room
SKIN = {"apartments": "stucco", "commercial": "tiltup", "industrial": "tiltup", "shed": "metal"}
MIN_LIT = 60.0            # [invented] a lit reference darker than this is a tree or a lot in shade: no measurement
MIN_SHADOW_CONTRAST = 12.0  # [invented] the shadow beside the wall must be this much darker than the lit side
CAP_M = {"shed": 6.0, "house": 12.0, "apartments": 35.0, "commercial": 25.0, "industrial": 20.0}   # [invented] past this a shadow
                                                                                                    # is a lot, a tree line, a slope
SUN_MATCH_DEG = 4.0       # [invented] the vote must put the sun somewhere the date allows
MIN_SUN_EL = 30.0         # NAIP is flown at a sun angle of 30 deg or more (the USDA NAIP specification; cited from memory, not
                          # re-read): a vote that needs a lower sun has found the camera's lean on the walls, not shadow
                          # (Sand Creek 2023: dark bands 2-3 m wide on every west wall, which a 17 deg sun could never cast)
CHECK_MIN = 5             # [invented] with this many OSM heights to compare, the stage is checked
CHECK_RANGE = (0.6, 1.6)  # [invented] shadow / OSM median outside this: the stage is wrong on this photograph, off
MIN_CONTRAST = 14.0       # [invented] a footprint whose darkest side is not this much darker than the opposite casts no vote
MIN_SAMPLES = 3
SPREAD_MAX = 0.4          # [invented] p25..p75 of the sample runs over the median: a wider spread is not one shadow


def area_m2(ring):
    lat0 = ring[0][1]
    mx, my = 111320.0 * math.cos(math.radians(lat0)), 111320.0
    pts = [(p[0] * mx, p[1] * my) for p in ring]
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2


def in_ring(ring, x, y):
    inside = False
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def load_footprints(track, sources):
    out = []
    for src in sources:
        rows = json.loads((track / src["file"]).read_text(encoding="utf-8"))
        for k, el in enumerate(rows):
            if src["kind"] == "overpass":
                g = el.get("geometry") or []
                ring = [[n["lon"], n["lat"]] for n in g]
                tags = el.get("tags", {})
                rec = {"key": f"osm{el.get('id', k)}", "tag": tags.get("building"), "levels": tags.get("building:levels"),
                       "height": tags.get("height"), "src": "OSM"}
            else:
                ring = [list(p) for p in el["geom"]]
                rec = {"key": el.get("key") or f"{src['file'].rsplit('/', 1)[-1].split('.')[0]}{k}", "tag": el.get("building"),
                       "levels": el.get("levels"), "height": el.get("height"), "src": el.get("_source", src["file"])}
            if len(ring) > 1 and ring[0] == ring[-1]:
                ring = ring[:-1]
            if len(ring) < 3:
                continue
            rec["ring"] = [[round(p[0], 7), round(p[1], 7)] for p in ring]
            out.append(rec)
    return out


def classify(rec, plan):
    tag = (rec.get("tag") or "yes").lower()
    if tag in TAG_CLASS:
        return TAG_CLASS[tag], f"OSM building={tag}"
    a = rec["area"]
    for below, cls in plan.get("yes_by_area", [[60, "shed"], [350, "house"], [1500, "commercial"], [1e9, "industrial"]]):
        if a < below:
            return cls, f"building={tag}, {a:.0f} m2 -> {cls} by area [invented rule]"
    return "industrial", "by area"


class Photo:
    def __init__(self, track, plan):
        self.img = Image.open(track / plan["image"]).convert("RGB")
        self.px = self.img.load()
        self.w, self.h = self.img.size
        self.to_px = geo(plan, self.w, self.h)
        W, S, E, N = plan.get("bbox_lonlat") or [None] * 4
        if W is None:
            z, x0 = plan["webmerc"]["z"], plan["webmerc"]["x0"]
            lon_c = ((x0 + self.w / 512) / 2 ** z) * 360 - 180
            lat_c = plan.get("lat_hint", 0.0)
            self.lon_c, self.lat_c = lon_c, lat_c
        else:
            self.lon_c, self.lat_c = (W + E) / 2, (S + N) / 2

    def set_centre(self, lon, lat):
        self.lon_c, self.lat_c = lon, lat
        a = self.to_px(lon, lat)
        b = self.to_px(lon + 0.001, lat)
        self.m_per_px = 0.001 * 111320.0 * math.cos(math.radians(lat)) / max(1e-9, b[0] - a[0])

    def bright(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            r, g, b = self.px[int(x), int(y)]
            return (r + g + b) / 3.0
        return None


def ray_to_ring(ring_px, cx, cy, ux, uy):
    """distance from (cx, cy) along (ux, uy) to the ring's edge, or None"""
    best = None
    for i, a in enumerate(ring_px):
        b = ring_px[(i + 1) % len(ring_px)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = ux * ey - uy * ex
        if abs(den) < 1e-9:
            continue
        t = ((a[0] - cx) * ey - (a[1] - cy) * ex) / den
        s = ((a[0] - cx) * uy - (a[1] - cy) * ux) / den
        if t > 0 and 0 <= s <= 1 and (best is None or t < best):
            best = t
    return best


DIR_BINS = 24


def shadow_direction(photo, polys, max_m=60.0):
    """compass azimuth of the shadows, voted by every footprint: of DIR_BINS directions out from its ring, the one the dark
    ground RUNS FARTHEST (the darkest one is not enough: beside a wall several directions are equally dark). The dark threshold is
    each footprint's own, the midpoint of its brightest and darkest near ground; a footprint without that contrast casts no vote"""
    votes = []
    for ring_px in polys:
        cx, cy = sum(p[0] for p in ring_px) / len(ring_px), sum(p[1] for p in ring_px) / len(ring_px)
        near, starts = [], []
        for k in range(DIR_BINS):
            th = math.radians(k * 360.0 / DIR_BINS)
            ux, uy = math.sin(th), -math.cos(th)
            r = ray_to_ring(ring_px, cx, cy, ux, uy)
            if r is None:
                break
            samples = [photo.bright(cx + ux * (r + d / photo.m_per_px), cy + uy * (r + d / photo.m_per_px)) for d in (1.0, 1.5, 2.0)]
            if any(v is None for v in samples):
                break
            near.append(statistics.mean(samples))
            starts.append((cx + ux * r, cy + uy * r, ux, uy))
        if len(near) < DIR_BINS:
            continue
        lo, hi = min(near), max(near)
        if hi - lo < MIN_CONTRAST:
            continue
        thr = (lo + hi) / 2.0
        runs = []
        for k, (sx, sy, ux, uy) in enumerate(starts):
            run, streak, step = 0.0, 0, 0.5
            j = 1
            while j * step * photo.m_per_px <= max_m:
                v = photo.bright(sx + ux * j * step, sy + uy * j * step)
                if v is None:
                    break
                if v < thr:
                    run, streak = j * step, 0
                else:
                    streak += 1
                    if streak >= 3:
                        break
                j += 1
            runs.append(run)
        k = max(range(DIR_BINS), key=lambda i: runs[i])
        if runs[k] * photo.m_per_px >= 1.0:
            votes.append((k, runs[k] * photo.m_per_px))
    if not votes:
        return None, 0
    hist = [0.0] * DIR_BINS
    for k, w in votes:
        hist[k] += w
    k = max(range(DIR_BINS), key=lambda i: hist[i] + 0.5 * hist[(i - 1) % DIR_BINS] + 0.5 * hist[(i + 1) % DIR_BINS])
    sx = sy = 0.0
    for kk, w in votes:
        if min((kk - k) % DIR_BINS, (k - kk) % DIR_BINS) <= 1:
            a = math.radians(kk * 360.0 / DIR_BINS)
            sx += w * math.cos(a)
            sy += w * math.sin(a)
    return math.degrees(math.atan2(sy, sx)) % 360.0, len(votes)


def sun_from_shadow(lat, lon, date, utc_offset, shadow_az):
    """the local time on ``date`` when the sun's azimuth is opposite the shadows, and its elevation then"""
    want = (shadow_az + 180.0) % 360.0
    best = None
    for m in range(5 * 60, 20 * 60, 2):
        when = f"{date}T{m // 60:02d}:{m % 60:02d}:00{utc_offset}"
        az, el = solar_position(lat, lon, when, "UTC")
        if el < MIN_SUN_EL:
            continue
        d = abs((az - want + 180.0) % 360.0 - 180.0)
        if best is None or d < best[0]:
            best = (d, when, az, el)
    return best


def shadow_length_m(photo, ring_px, polys_index, ux, uy, max_m, debug=None):
    """median run of shadow from the sun-away edges, in metres; None when it is not a measurement. ``debug`` (a list) collects
    (kind, x0, y0, x1, y1) segments: 'lit' probes, 'run' measurements, 'blocked' walks"""
    n = len(ring_px)
    step_px = 0.5
    max_px = max_m / photo.m_per_px
    # the lit reference: on the sun side, 2..5 m out
    lit = []
    cx, cy = sum(p[0] for p in ring_px) / n, sum(p[1] for p in ring_px) / n
    r = ray_to_ring(ring_px, cx, cy, -ux, -uy)
    if r is None:
        return None, "no sun side"
    for d in (2.0, 3.0, 4.0, 5.0):
        v = photo.bright(cx - ux * (r + d / photo.m_per_px), cy - uy * (r + d / photo.m_per_px))
        if v is not None:
            lit.append(v)
    if len(lit) < 3:
        return None, "no lit reference"
    lit_b = statistics.median(lit)
    if debug is not None:
        debug.append(("lit", cx - ux * r, cy - uy * r, cx - ux * (r + 5.0 / photo.m_per_px), cy - uy * (r + 5.0 / photo.m_per_px)))
    if lit_b < MIN_LIT:
        return None, f"dark reference {lit_b:.0f}"
    # the shadow's own darkness, 1..2 m out from the sun-away edges
    edges = []
    for i in range(n):
        a, b = ring_px[i], ring_px[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey) or 1e-9
        nx, ny = ey / ln, -ex / ln
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if in_ring(ring_px, mid[0] + nx, mid[1] + ny):
            nx, ny = -nx, -ny
        if nx * ux + ny * uy >= 0.5:
            edges.append((a, ex, ey, nx, ny))
    dark = []
    for a, ex, ey, nx, ny in edges:
        for t_ in (0.3, 0.5, 0.7):
            for d in (1.0, 1.5, 2.0):
                v = photo.bright(a[0] + ex * t_ + ux * d / photo.m_per_px, a[1] + ey * t_ + uy * d / photo.m_per_px)
                if v is not None:
                    dark.append(v)
    if len(dark) < 3:
        return None, "no sun-away edge"
    sref = statistics.median(dark)
    if lit_b - sref < MIN_SHADOW_CONTRAST:
        return 0.0, f"no shadow beside the wall (lit {lit_b:.0f}, beside {sref:.0f})"
    thr = (lit_b + sref) / 2.0
    runs, blocked, capped = [], 0, 0
    for a, ex, ey, nx, ny in edges:
        i = -1
        for t in (0.3, 0.5, 0.7):
            sx, sy = a[0] + ex * t + nx * 0.8, a[1] + ey * t + ny * 0.8
            run, bright_streak, hit = 0.0, 0, False
            k = 1
            while k * step_px <= max_px:
                x, y = sx + ux * k * step_px, sy + uy * k * step_px
                v = photo.bright(x, y)
                if v is None:
                    break
                if polys_index.hit(x, y, ring_px):
                    hit = True
                    break
                if v < thr:
                    run = k * step_px
                    bright_streak = 0
                else:
                    bright_streak += 1
                    if bright_streak >= 3:
                        break
                k += 1
            if hit:
                blocked += 1
                if debug is not None:
                    debug.append(("blocked", sx, sy, sx + ux * k * step_px, sy + uy * k * step_px))
                continue
            if k * step_px > max_px:
                capped += 1
                continue
            if debug is not None:
                debug.append(("run", sx, sy, sx + ux * run, sy + uy * run))
            runs.append(run * photo.m_per_px)
    if len(runs) < MIN_SAMPLES:
        return None, f"{len(runs)} samples, {blocked} blocked, {capped} ran to the cap"
    runs.sort()
    med = runs[len(runs) // 2]
    q1, q3 = runs[len(runs) // 4], runs[(3 * len(runs)) // 4]
    if med < photo.m_per_px:
        return 0.0, f"no shadow ({len(runs)} samples)"
    if (q3 - q1) > max(SPREAD_MAX * med, 2.0 * photo.m_per_px):
        return None, f"spread {q1:.1f}..{q3:.1f} m over {med:.1f}"
    return med, f"{len(runs)} samples, p25 {q1:.1f} p75 {q3:.1f}"


class PolyIndex:
    def __init__(self, polys, cell=40.0):
        self.cell = cell
        self.b = {}
        for p in polys:
            xs, ys = [q[0] for q in p], [q[1] for q in p]
            for i in range(int(min(xs) // cell), int(max(xs) // cell) + 1):
                for j in range(int(min(ys) // cell), int(max(ys) // cell) + 1):
                    self.b.setdefault((i, j), []).append(p)

    def hit(self, x, y, own):
        for p in self.b.get((int(x // self.cell), int(y // self.cell)), ()):
            if p is not own and in_ring(p, x, y):
                return True
        return False


def roof_class(photo, ring_px):
    xs, ys = [p[0] for p in ring_px], [p[1] for p in ring_px]
    rr = gg = bb = n = 0
    for i in range(1, 12):
        for j in range(1, 12):
            x, y = min(xs) + (max(xs) - min(xs)) * i / 12, min(ys) + (max(ys) - min(ys)) * j / 12
            if in_ring(ring_px, x, y) and 0 <= x < photo.w and 0 <= y < photo.h:
                a = photo.px[int(x), int(y)]
                rr += a[0]; gg += a[1]; bb += a[2]; n += 1
    if not n:
        return "tan"
    mean = (rr + gg + bb) / (3 * n)
    warm = (rr - bb) / n
    return "white" if mean > 175 else "dark" if mean < 105 else "tan" if warm > 12 else "white" if mean > 150 else "dark"


def main() -> int:
    track = Path(sys.argv[1])
    plan = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    recs = load_footprints(track, plan["footprints"])
    photo = Photo(track, plan)
    lat_c = statistics.median(r["ring"][0][1] for r in recs)
    lon_c = statistics.median(r["ring"][0][0] for r in recs)
    photo.set_centre(lon_c, lat_c)
    left = {"canopy": 0, "small": 0}
    kept = []
    for r in recs:
        r["area"] = area_m2(r["ring"])
        r["cls"], r["_class"] = classify(r, plan)
        if r["cls"] == "canopy":
            left["canopy"] += 1
            continue
        if r["area"] < plan.get("min_area_m2", 25):
            left["small"] += 1
            continue
        r["px"] = [list(photo.to_px(p[0], p[1])) for p in r["ring"]]
        kept.append(r)
    polys = [r["px"] for r in kept]
    index = PolyIndex(polys)
    sh = plan.get("shadow", {"enabled": True})
    sun = None
    debug = [] if "--debug" in sys.argv else None
    if sh.get("enabled", True) and kept and plan.get("sun"):
        az = (float(plan["sun"]["azimuth_deg"]) + 180.0) % 360.0
        sun = (0.0, "pinned", float(plan["sun"]["azimuth_deg"]), float(plan["sun"]["elevation_deg"]))
        print(f"[buildings] sun pinned by the plan: azimuth {sun[2]:.0f}, elevation {sun[3]:.1f} deg ({plan['sun'].get('_source', '')}); {photo.m_per_px:.2f} m/px")
    elif sh.get("enabled", True) and kept:
        az, nvotes = shadow_direction(photo, polys, float(sh.get("max_m", 60)))
        if az is not None:
            sun = sun_from_shadow(lat_c, lon_c, plan["naip_date"], plan["utc_offset"], az)
            if sun is None or sun[0] > SUN_MATCH_DEG:
                print(f"[buildings] shadows voted azimuth {az:.0f} deg ({nvotes} votes) but no sun of {MIN_SUN_EL:.0f} deg or more on "
                      f"{plan['naip_date']} stands opposite within {SUN_MATCH_DEG:.0f} deg"
                      f"{'' if sun is None else f' (best {sun[0]:.1f})'}: that is the camera's lean, not shadow; OSM and defaults only")
                sun = None
            elif sun is not None:
                print(f"[buildings] shadows run to azimuth {az:.0f} deg ({nvotes} votes) -> sun at {sun[1]}, "
                      f"azimuth {sun[2]:.0f}, elevation {sun[3]:.1f} deg (matched to {sun[0]:.1f} deg); {photo.m_per_px:.2f} m/px")
        else:
            print("[buildings] no shadow direction could be voted: OSM and defaults only")
    ux = uy = 0.0
    if sun:
        th = math.radians(az)
        ux, uy = math.sin(th), -math.cos(th)
        tan_el = math.tan(math.radians(sun[3]))
    out, by_src, checks = [], {}, []
    measured = {}
    if sun:
        for r in kept:
            L, why = shadow_length_m(photo, r["px"], index, ux, uy, float(sh.get("max_m", 60)), debug)
            measured[r["key"]] = (L, why)
            osm_h = None
            try:
                if r.get("height"):
                    osm_h = float(str(r["height"]).split()[0])
                elif r.get("levels"):
                    osm_h = float(r["levels"]) * STOREY_M[r["cls"]]
            except ValueError:
                osm_h = None
            if L and osm_h and L * tan_el <= CAP_M[r["cls"]]:
                checks.append((osm_h, L * tan_el, r["cls"]))
        verdict = "unchecked: no OSM heights to compare"
        trust = bool(sh.get("trust_unchecked", False))
        if len(checks) >= CHECK_MIN:
            ratios = sorted(s / o for o, s, _ in checks if o > 0)
            med = ratios[len(ratios) // 2]
            verdict = f"checked against {len(checks)} OSM heights, shadow / OSM median {med:.2f}"
            if not (CHECK_RANGE[0] <= med <= CHECK_RANGE[1]):
                print(f"[buildings] shadow stage OFF: {verdict}, outside {CHECK_RANGE}: this photograph's dark bands are not this sun's shadows")
                sun = None
        if sun and len(checks) < CHECK_MIN and not trust:
            print(f"[buildings] shadow stage measured but NOT USED: {verdict}; set shadow.trust_unchecked after reading --debug to use it")
            sun = None
        elif sun:
            print(f"[buildings] shadow stage: {verdict}")
    for r in kept:
        cls = r["cls"]
        h = None
        src = None
        try:
            if r.get("height"):
                h, src = float(str(r["height"]).split()[0]), "OSM height"
            elif r.get("levels"):
                lv = float(r["levels"])
                st = STOREY_M[cls] if lv <= 1 or cls in ("house", "apartments", "shed") else STOREY_MULTI_M
                h, src = lv * st, f"OSM building:levels {r['levels']} x {st} m"
        except ValueError:
            h = None
        shadow_h, why = None, None
        if sun:
            L, why = measured[r["key"]]
            if L is not None and L > 0:
                shadow_h = L * tan_el
                if shadow_h > CAP_M[cls]:
                    why = f"shadow {L:.1f} m reads {shadow_h:.0f} m, past the {cls} cap {CAP_M[cls]:.0f} m"
                    shadow_h = None
        if h is None and shadow_h is not None:
            h, src = shadow_h, f"shadow {L:.1f} m on NAIP {plan['naip_date']} at {sun[3]:.0f} deg sun ({why}; {verdict})"
        if h is None:
            h, src = DEFAULT_WALL_M[cls], f"class default [invented]" + (f"; shadow: {why}" if why else "")
        form = FORM[cls]
        row = {"key": r["key"], "footprint_lonlat": r["ring"], "class": cls, "form": form, "wall_h_m": round(h, 1),
               "skin": plan.get("house_skin", "stucco") if cls == "house" else SKIN[cls],
               "roof": "shingle" if cls == "house" else roof_class(photo, r["px"]),
               "_class": r["_class"], "_h": src, "_src": r["src"]}
        if form in ("hip", "gable"):
            # the shadow and OSM give the top: a pitched roof's wall (eave) stands below it by the rise over half the short side
            xs = [p[0] * 111320.0 * math.cos(math.radians(lat_c)) for p in r["ring"]]
            ys = [p[1] * 111320.0 for p in r["ring"]]
            short = min(max(xs) - min(xs), max(ys) - min(ys))
            rise = PITCH[form] * short / 2.0
            wall = max(MIN_WALL_M.get(cls, 2.6), h - rise)
            row["wall_h_m"] = round(wall, 1)
            row["ridge_h_m"] = round(wall + rise, 1)
            row["_form"] = f"{form} at {PITCH[form]:.2f} pitch [invented by class]; wall = top - rise {rise:.1f} m, floored at {MIN_WALL_M.get(cls, 2.6)} m"
        out.append(row)
        by_src.setdefault(src.split(" ")[0] + (" default" if "default" in src else ""), 0)
        by_src[src.split(" ")[0] + (" default" if "default" in src else "")] += 1
    path = track / plan["out"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8", newline="\n")
    if debug is not None:
        from PIL import ImageDraw
        im = photo.img.copy()
        d = ImageDraw.Draw(im)
        for r in kept:
            d.line([tuple(q) for q in r["px"]] + [tuple(r["px"][0])], fill=(0, 255, 255), width=1)
        for kind, x0, y0, x1, y1 in debug:
            d.line((x0, y0, x1, y1), fill={"lit": (255, 255, 0), "run": (255, 0, 0), "blocked": (255, 0, 255)}[kind], width=1)
        if sun:
            cx0, cy0 = im.width / 2, 40
            d.line((cx0, cy0, cx0 + ux * 60, cy0 + uy * 60), fill=(255, 128, 0), width=3)
        xs = [q[0] for r in kept for q in r["px"]]
        ys = [q[1] for r in kept for q in r["px"]]
        box = (max(0, int(min(xs)) - 40), max(0, int(min(ys)) - 40), min(im.width, int(max(xs)) + 40), min(im.height, int(max(ys)) + 40))
        crop = im.crop(box)                      # full resolution: the runs are a few pixels long
        out_dbg = Path(sys.argv[sys.argv.index("--debug") + 1])
        crop.save(out_dbg, quality=90)
        print(f"[buildings] debug drawing -> {out_dbg}")
    classes = {}
    for row in out:
        classes[row["class"]] = classes.get(row["class"], 0) + 1
    print(f"[buildings] {len(out)} footprints -> {plan['out']}; left out {left}; classes {classes}; heights by source {by_src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

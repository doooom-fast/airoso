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
  "tag_class": {"stable": "shed"},                                optional: a building tag the shared TAG_CLASS lacks, classed
                                                                 by the track (never overrides a tag TAG_CLASS knows)
  "shadow": {"enabled": true, "max_m": 60, "trust_unchecked": false},   off = OSM and defaults only; an unchecked stage (no
                                                                 OSM heights to compare) is used only when trust_unchecked is set
  "sun": {"azimuth_deg": 122, "elevation_deg": 33, "_source": "..."}   optional: a sun read by hand (Nevada's pole shadows)
                                                                 in place of the vote
  "canopy_posts": true                                           optional (ledger 0083 pass 3, with "lidar"): a canopy-class
                                                                 footprint (building=roof, a tag_class canopy) the lidar
                                                                 measured stands as the author's "posts" form (canopy_row)
  "lidar": {"file": "source/bespoke/buildings.lidar.json"}       optional (ledger 0083 pass 2): heights MEASURED off 3DEP lidar
                                                                 by tools/lidar_building_heights.py (run on this planner's
                                                                 output WITHOUT this key); a measured footprint takes them over
                                                                 every other source, a "stepped" one stands as its tiers
                                                                 (lidar_rows); absent = as before
  "roof_forms": {"file": "source/bespoke/buildings.roofs.json"}  optional (ledger 0083 pass 4, with "lidar"): each roof's FORM
                                                                 fitted to the points by tools/lidar_roof_forms.py (flat with
                                                                 a measured parapet / gable / hip / shed / its measured
                                                                 parts; a poor fit stands its median, flagged)
                                                                 (roof_form_rows); absent = as before
  "set_in_slope": true                                           optional (ledger 0083 pass 4b, with "roof_forms"): a hillside
                                                                 deck stands set into its slope at its measured heights over
                                                                 its low ground ("set_in" on its rows); absent = as before
  "roof_colour": {"atlas": "source/bespoke/roof_naip_palette.png", "normal": "source/bespoke/roof_flat_normal.png"}
                                                                 optional (ledger 0083 pass 4): each roof's MEASURED colour,
                                                                 the median "image" pixel inside it, as a cell of a palette
                                                                 the author maps its UVs into (roof_palette); absent = as before
}

CLASSES, from the OSM building tag first, then by area: house, apartments, commercial, industrial, shed; canopy (building=roof)
is left out. Each class fixes the roof FORM and the SKINS (tools/make_bespoke_assets.py): house = hip roof of shingle on stucco or
siding; apartments = flat with a parapet, stucco; commercial = flat with a parapet, tilt-up; industrial = flat, tilt-up; shed =
low gable, ribbed metal. Flat roofs take the colour class read off the NAIP (white / tan / dark); the parapet and pitch numbers are
[invented] and said so below.

HEIGHTS, in this order per building: the row's own height (OSM's tag, or Microsoft's ML estimate on a Microsoft footprint);
OSM building:levels x STOREY_M[class]; a later source's height where its footprint stands on this one (dedupe); the shadow on
the NAIP; the class default.
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
    return dedupe(out)


DEDUPE_CELL = 0.0005           # degrees (~50 m): the lon/lat index cell of the footprint-on-footprint test


def dedupe(recs):
    """Sources stand in the plan's order of trust. A footprint whose centroid lies inside an EARLIER source's footprint is
    the same building seen twice (Microsoft's tile over OSM's houses: 1,486 of Lake Murray's 12,035), so it is dropped;
    where the earlier footprint carries no height and no levels, the later one's height is offered to it as
    rec["alt_height"] / rec["alt_src"] (Lake Murray: 1,424 OSM houses gain Microsoft's estimate)."""
    kept, cells, dropped, offered = [], {}, {}, 0
    for rec in recs:
        xs, ys = [p[0] for p in rec["ring"]], [p[1] for p in rec["ring"]]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        host = None
        for k in cells.get((int(cx / DEDUPE_CELL), int(cy / DEDUPE_CELL)), ()):
            if in_ring(kept[k]["ring"], cx, cy):
                host = kept[k]
                break
        if host is not None:
            dropped[rec["src"]] = dropped.get(rec["src"], 0) + 1
            if not host.get("height") and not host.get("levels") and not host.get("alt_height") and rec.get("height"):
                host["alt_height"], host["alt_src"] = rec["height"], rec["src"]
                offered += 1
            continue
        k = len(kept)
        kept.append(rec)
        for i in range(int(min(xs) / DEDUPE_CELL), int(max(xs) / DEDUPE_CELL) + 1):
            for j in range(int(min(ys) / DEDUPE_CELL), int(max(ys) / DEDUPE_CELL) + 1):
                cells.setdefault((i, j), []).append(k)
    for src, n in dropped.items():
        print(f"[buildings] {n} footprints from {src[:70]} stand on an earlier source's footprint: dropped")
    if offered:
        print(f"[buildings] {offered} earlier footprints with no height or levels take the dropped footprint's height")
    return kept


def lidar_rows(row, rec, stepped):
    """the plan's opt-in "lidar" (ledger 0083 pass 2): a footprint MEASURED off the 3DEP point cloud
    (tools/lidar_building_heights.py) takes its roof from it, over every other source (OSM levels are a storey count times an
    assumed storey; the lidar is the roof). A flat roof's wall is the roof points' median over the lidar ground (the deck; the
    parapet stays PARAPET_M [invented] on top); a pitched roof's eave is 2 x p25 - p50 (a gable's heights spread evenly
    over its plan, eave to ridge: p25 = eave + rise / 4, p50 = eave + rise / 2), held between p05 and p50, its ridge their
    p95. The low tail is not the eave: p05 read a lean-to's 1.3 m on a 3.5 m shed (0.2.1's first try) and p10 1.0 m on a
    28 m2 one (0.2.2's), both house_seat's buried. A building named in the file's "stepped" stands as its
    tiers instead (flat roofs, one row per tier, keys <key>_t<i>). One whose first returns
    are mostly ground ("no_roof") is dropped: nothing stands there in the lidar. Not measured = the row as before. Returns the
    rows to write."""
    if rec and rec.get("status") == "no_roof":
        return []                      # the lidar sees bare ground inside the walls: no building stands there today
    if not rec or rec.get("status") != "measured":
        if rec:
            row["_lidar"] = rec.get("status")
        return [row]
    p = rec["h_pct"]
    tag = (f"lidar {rec['roof_src']} n={rec['n_roof']} over ground {rec['ground_m']:.2f} m "
           f"(n={rec['ground_n']}, ring {rec['ground_ring_m'][0]:.0f}-{rec['ground_ring_m'][1]:.0f} m)"
           + (f", {rec['cover']:.0%} of the footprint on the tiles" if rec.get("cover", 1.0) < 0.95 else ""))
    was = row["_h"] + f" -> wall {row['wall_h_m']}" + (f", ridge {row['ridge_h_m']}" if "ridge_h_m" in row else "")
    if len(rec.get("levels", [])) > 1:
        row["_levels"] = rec["levels"]
    if stepped:
        out = []
        for i, t in enumerate(stepped["tiers"]):
            r = {k: v for k, v in row.items() if k not in ("ridge_h_m", "_form")}
            r.update(key=f"{row['key']}_t{i}", footprint_lonlat=t["footprint_lonlat"], form="flat", wall_h_m=round(t["h_p50"], 1),
                     _h=f"lidar stepped form, tier {i} (band {t['band_m'][0]}..{t['band_m'][1]} m across the short axis): roof p50 "
                        f"{t['h_p50']} m (p10 {t['h_p10']}, p90 {t['h_p90']}, n={t['n_roof']}); {tag}",
                     _h_was=was, _form="flat: a tier of the measured stepped form")
            out.append(r)
        return out
    if row["form"] in ("hip", "gable"):
        wall = min(max(2.0 * p["p25"] - p["p50"], p["p05"]), p["p50"])
        ridge = max(p["p95"], wall + 0.3)
        row["wall_h_m"], row["ridge_h_m"] = round(wall, 1), round(ridge, 1)
        row["_h"] = f"{tag}: eave 2 x p25 - p50 = {wall:.2f} m (p05 {p['p05']}, p25 {p['p25']}, p50 {p['p50']}), ridge p95 {p['p95']} m"
        row["_form"] = f"{row['form']} [invented by class]; eave and ridge measured (lidar)"
    else:
        row["wall_h_m"] = round(p["p50"], 1)
        row["_h"] = f"{tag}: roof p50 {p['p50']} m (p10 {p['p10']}, p90 {p['p90']}, p98 {p['p98']})"
    row["_h_was"] = was
    return [row]


def roof_form_rows(row, rec, rf, stepped, set_in=False):
    """the plan's opt-in "roof_forms" (ledger 0083 pass 4, with "lidar"): the roof's FORM fitted to the lidar points
    (tools/lidar_roof_forms.py) in place of the class's. ``row`` is the class row before the lidar, ``rec`` its
    buildings.lidar.json record, ``rf`` its buildings.roofs.json record. flat: the median (as lidar_rows) with the MEASURED
    parapet (none under the fit's MIN_PARAPET_M; the class's [invented] one where the edge band was too thin to read);
    gable / hip: eave and ridge off the fitted planes, the ridge along the box's long or short axis; shed: one plane
    ("plane": its height at a reference point and its gradient east / north); parts: the measured levels (or the stepped
    slope) as rows <key>_p<i>, each flat or shed; poor: the measured median, flat, flagged; a hillside deck (lidar no_roof
    under a sloping ring) stands as its fit over the ring's low ground. No rf, or a form of None: lidar_rows as before."""
    hill = (rf or {}).get("hillside")
    if not rf or rf.get("form") is None or (rec and rec.get("status") != "measured" and not hill):
        return lidar_rows(row, rec, stepped)
    if hill:
        r = dict(row)
        r["_h_was"] = row["_h"] + f" -> wall {row['wall_h_m']}"
        tag = (f"lidar {rec['roof_src']} n={rec['n_roof']}: a hillside deck, heights over the ring's low ground "
               f"(p10 {hill['ground_p10_p90_navd88'][0]:.2f} m NAVD88, the median {hill['ground_median_navd88']:.2f}; "
               f"+{hill['shift_m']:.2f} m)")
        r.pop("ridge_h_m", None)
        if set_in:
            # the plan's opt-in set_in_slope (ledger 0083 pass 4b): the deck stands at its MEASURED height over the ring's low
            # ground, at that ground's own NAVD88 height, set into the slope (tools/author_bespoke_blend.py: walls down to the
            # real ground on every side, no relief refusal, not re-seated by the prep; tools/house_seat_check.py judges it
            # against this deck, not against its uphill ground). Every part carries it (the parts copy the row)
            r["set_in"] = {"ground_navd88": hill["ground_p10_p90_navd88"][0],
                           "_doc": "the ring's p10 lidar ground (its downhill face): every height of this row is over it"}
    else:
        r = lidar_rows(row, rec, None)[0]
        tag = r["_h"]
    form = rf["form"]
    fit_note = f"lidar roof fit {form}, residual {rf['rms_m']:.2f} m (tools/lidar_roof_forms.py)"
    r.pop("ridge_h_m", None)
    r.pop("ridge_axis", None)
    if form == "parts":
        out = []
        for i, p in enumerate(rf["parts"]):
            q = {k: v for k, v in r.items() if k not in ("_form",)}
            pf = p.get("form", "flat")
            q.update(key=f"{row['key']}_p{i}", footprint_lonlat=p["footprint_lonlat"],
                     _h=f"{fit_note}; part {i} of {len(rf['parts'])} ({rf.get('_how', '')}): {pf}, residual {p['rms_m']} m, "
                        f"n={p['n']}; {tag}")
            q.pop("parapet_m", None)
            if pf == "shed":
                q.update(form="shed", wall_h_m=round(p["low_m"], 1), ridge_h_m=round(p["high_m"], 1),
                         plane={"ref_lonlat": p["ref_lonlat"], "h_m": p["h_m"], "gx": p["gx"], "gy": p["gy"]},
                         _form=f"shed: a measured plane of the building, {p['low_m']}..{p['high_m']} m")
            elif pf in ("gable_long", "gable_short", "hip"):
                q.update(form="hip" if pf == "hip" else "gable", wall_h_m=round(p["eave_m"], 1), ridge_h_m=round(p["ridge_m"], 1),
                         _form=f"{pf}: a measured pitched part of the building, eave {p['eave_m']} m, ridge {p['ridge_m']} m")
                if pf != "hip":
                    q["ridge_axis"] = "short" if pf == "gable_short" else "long"
            else:
                q.update(form="flat", wall_h_m=round(p["h_m"], 1), _form="flat: one measured part of the building")
                if p.get("parapet_m"):
                    q.update(form="flat_parapet", parapet_m=round(p["parapet_m"], 2),
                             _form=f"flat with a measured parapet {p['parapet_m']:.2f} m: one part of the building")
            out.append(q)
        return out
    f = rf.get("fits", {})
    if form in ("flat", "poor"):
        if form == "poor":
            r["wall_h_m"] = round(rf["median_m"], 1)
            r["form"] = "flat"
            r["_fit"] = f"poor: the best fit ({rf.get('_poor')}) left {rf['rms_m']:.2f} m; the measured median stands, flat"
            r["_form"] = "flat: the measured median (a poor fit, flagged)"
        else:
            if hill:
                r["wall_h_m"] = round(rf["median_m"], 1)
            par = rf.get("parapet_m")
            if par is None:
                r["_form"] = f"{r['form']} [invented by class]: too few edge points to read a parapet"
            elif par > 0:
                r["form"], r["parapet_m"] = "flat_parapet", round(par, 2)
                r["_form"] = f"flat with a parapet {par:.2f} m (measured: the edge band's p75 over the roof's median)"
            else:
                r["form"] = "flat"
                r["_form"] = "flat: no parapet in the edge band (measured)"
        r["_h"] = f"{fit_note}; {tag}"
        return [r]
    if form in ("gable_long", "gable_short", "hip"):
        g = f[form]
        r.update(form="hip" if form == "hip" else "gable", wall_h_m=round(g["eave_m"], 1), ridge_h_m=round(g["ridge_m"], 1),
                 _form=f"{'hip' if form == 'hip' else 'gable'} (measured: the fitted planes; pitch {g['pitch']:.3f})")
        if form != "hip":
            r["ridge_axis"] = "short" if form == "gable_short" else "long"
        r["_h"] = f"{fit_note}: eave {g['eave_m']} m, ridge {g['ridge_m']} m; {tag}"
        return [r]
    g = f["shed"]                                   # shed
    r.update(form="shed", wall_h_m=round(g["low_m"], 1), ridge_h_m=round(g["high_m"], 1),
             plane={"ref_lonlat": g["ref_lonlat"], "h_m": g["h_c_m"], "gx": g["gx"], "gy": g["gy"]},
             _form=f"shed (measured: one fitted plane, {g['low_m']}..{g['high_m']} m)", _h=f"{fit_note}; {tag}")
    return [r]


ROOF_CELL_PX = 32              # the roof palette: one solid cell per measured colour (mip 5 still holds a cell's own pixel)
ROOF_ATLAS_PX = 1024           # a power of two (fleet/LAWS.md L7): 1,024 cells
ROOF_EDGE_PX = 2.0             # [invented] the NAIP pixels this near a footprint's edge are the eave's shadow or the wall's


def roof_colour(photo, ring_px):
    """the median NAIP colour of the pixels inside a footprint, ROOF_EDGE_PX clear of its edge: (r, g, b) or None when the
    footprint is not wholly on the photograph"""
    xs, ys = [p[0] for p in ring_px], [p[1] for p in ring_px]
    if min(xs) < 0 or min(ys) < 0 or max(xs) >= photo.w or max(ys) >= photo.h:
        return None
    n = len(ring_px)
    vals = []
    for py in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
        for px in range(int(math.floor(min(xs))), int(math.ceil(max(xs))) + 1):
            x, y = px + 0.5, py + 0.5
            if not in_ring(ring_px, x, y):
                continue
            near = False
            for i in range(n):
                (ax, ay), (bx, by) = ring_px[i], ring_px[(i + 1) % n]
                ex, ey = bx - ax, by - ay
                L2 = ex * ex + ey * ey
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * ex + (y - ay) * ey) / L2))
                if math.hypot(x - ax - t * ex, y - ay - t * ey) < ROOF_EDGE_PX:
                    near = True
                    break
            if not near and 0 <= px < photo.w and 0 <= py < photo.h:
                vals.append(photo.px[px, py])
    if len(vals) < 4:
        return None
    return tuple(int(statistics.median(v[c] for v in vals)) for c in range(3))


def roof_palette(rows, photo, spec, track):
    """the plan's opt-in "roof_colour" (ledger 0083 pass 4): every row's roof takes its MEASURED colour, the median NAIP pixel
    inside its footprint, as one solid cell of a palette atlas (spec["atlas"], ROOF_ATLAS_PX square) the author maps that
    roof's UVs into ("roof": "NAIP", "roof_uv": the cell's inner quarter); a footprint not wholly on the photograph keeps its
    class stand-in, said so. Also writes spec["normal"], a flat normal map (the ROOF material's normal slot). Returns counts."""
    from PIL import Image
    cells, n_on, n_off = {}, 0, 0
    per = ROOF_ATLAS_PX // ROOF_CELL_PX
    for row in rows:
        ring_px = [photo.to_px(p[0], p[1]) for p in row["footprint_lonlat"]]
        rgb = roof_colour(photo, ring_px)
        if rgb is None:
            row["_roof"] = f"{row.get('roof')}: off the NAIP ({photo_label(spec)}), the class stand-in [invented]"
            n_off += 1
            continue
        if rgb not in cells:
            if len(cells) >= per * per:
                raise SystemExit(f"[buildings] roof palette full ({per * per} colours)")
            cells[rgb] = len(cells)
        k = cells[rgb]
        i, j = k % per, k // per
        q = ROOF_CELL_PX / ROOF_ATLAS_PX
        row["_roof"] = f"measured: the median NAIP colour inside the footprint, rgb {list(rgb)} ({photo_label(spec)}); was {row.get('roof')}"
        row["roof"] = "NAIP"
        row["roof_rgb"] = list(rgb)
        # the cell's inner quarter (a filtered sample never reaches the next cell); v counts from the image's bottom (Blender)
        u0, v0 = (i + 0.375) * q, 1.0 - (j + 0.625) * q
        row["roof_uv"] = [round(u0, 6), round(v0, 6), round(u0 + 0.25 * q, 6), round(v0 + 0.25 * q, 6)]
        n_on += 1
    img = Image.new("RGB", (ROOF_ATLAS_PX, ROOF_ATLAS_PX), (128, 128, 128))
    for rgb, k in cells.items():
        i, j = k % per, k // per
        img.paste(rgb, (i * ROOF_CELL_PX, j * ROOF_CELL_PX, (i + 1) * ROOF_CELL_PX, (j + 1) * ROOF_CELL_PX))
    (track / spec["atlas"]).parent.mkdir(parents=True, exist_ok=True)
    img.save(track / spec["atlas"], optimize=True)
    Image.new("RGB", (64, 64), (128, 128, 255)).save(track / spec["normal"], optimize=True)
    return {"measured": n_on, "off_the_photograph": n_off, "colours": len(cells)}


def photo_label(spec):
    return spec.get("_photo", "the plan's photograph")


def canopy_row(r, rec):
    """the plan's opt-in canopy_posts (ledger 0083 pass 3): an open-sided roof (building=roof / =pavilion, the canopy class)
    stands as tools/author_bespoke_blend.py's "posts" form, its slab's top at the lidar roof's median over the ground.
    MEASURED only: no lidar roof, no row (the canopy stays left out, as before)."""
    if not rec or rec.get("status") != "measured":
        return None
    p = rec["h_pct"]
    return {"key": r["key"], "footprint_lonlat": r["ring"], "class": "canopy", "form": "posts", "wall_h_m": round(p["p50"], 1),
            "skin": "metal", "roof": "metal", "_class": r["_class"],
            "_h": (f"lidar {rec['roof_src']} n={rec['n_roof']} over ground {rec['ground_m']:.2f} m: roof p50 {p['p50']} m "
                   f"(p10 {p['p10']}, p90 {p['p90']})"),
            "_form": "posts: an open-sided roof, slab and posts [invented sizes]; the slab's top measured (lidar)", "_src": r["src"]}


def height_label(src):
    """where a footprint row's own height came from, for the row's _h"""
    if src == "OSM":
        return "OSM height"
    if str(src).startswith("Microsoft"):
        return f"Microsoft height ({src[:110]})"
    return f"height from {src[:110]}"


HOUSE_MAX_H_M = 7.5            # [invented] an untagged footprint with a known height under this (two storeys' ridge) and under
HOUSE_MAX_AREA_M2 = 1000.0     # this area is a big house, not the commercial block its area alone would make it (Lake Murray's
                               # Microsoft footprints: 1,170 of 10,324 read commercial / industrial by area at a median 4.8 m tall)


def classify(rec, plan):
    tag = (rec.get("tag") or "yes").lower()
    # the plan's own tag -> class rows (opt-in, per track; absent = TAG_CLASS alone, as before): a tag the shared table does
    # not know, read by the track's photograph (Del Mar, ledger 0083: building=stable is a barn row, =grandstand a block)
    own = {str(k).lower(): v for k, v in (plan.get("tag_class") or {}).items() if not str(k).startswith("_")}
    if tag in own and tag not in TAG_CLASS:
        if own[tag] not in STOREY_M and own[tag] != "canopy":
            raise SystemExit(f"[buildings] plan tag_class {tag!r} -> {own[tag]!r}: not a class ({sorted(STOREY_M)} or canopy)")
        return own[tag], f"OSM building={tag} -> {own[tag]} by the plan's tag_class"
    if tag in TAG_CLASS:
        return TAG_CLASS[tag], f"OSM building={tag}"
    a = rec["area"]
    known = rec.get("height") or rec.get("alt_height")
    try:
        known = float(str(known).split()[0]) if known else None
    except ValueError:
        known = None
    by_area = "industrial"
    for below, cls in plan.get("yes_by_area", [[60, "shed"], [350, "house"], [1500, "commercial"], [1e9, "industrial"]]):
        if a < below:
            by_area = cls
            break
    if by_area in ("commercial", "industrial") and known is not None and a < HOUSE_MAX_AREA_M2 and known <= HOUSE_MAX_H_M:
        return "house", f"building={tag}, {a:.0f} m2 but {known:.1f} m tall -> house by height, not {by_area} by area [invented rule]"
    return by_area, f"building={tag}, {a:.0f} m2 -> {by_area} by area [invented rule]"


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
    kept, canopies = [], []
    for r in recs:
        r["area"] = area_m2(r["ring"])
        r["cls"], r["_class"] = classify(r, plan)
        if r["cls"] == "canopy":
            if plan.get("canopy_posts") and plan.get("lidar"):
                canopies.append(r)              # opt-in (ledger 0083 pass 3): stood on posts where the lidar measured it
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
    lidar = None
    if plan.get("lidar"):                       # opt-in (ledger 0083 pass 2); absent = as before
        lidar = json.loads((track / plan["lidar"]["file"]).read_text(encoding="utf-8"))
    roofs = None
    if plan.get("roof_forms") and lidar is not None:   # opt-in (ledger 0083 pass 4); absent = as before
        roofs = json.loads((track / plan["roof_forms"]["file"]).read_text(encoding="utf-8"))
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
        verdict = "unchecked: no known heights to compare"
        trust = bool(sh.get("trust_unchecked", False))
        if len(checks) >= CHECK_MIN:
            ratios = sorted(s / o for o, s, _ in checks if o > 0)
            med = ratios[len(ratios) // 2]
            verdict = f"checked against {len(checks)} known heights (OSM tags and levels, Microsoft estimates), shadow / known median {med:.2f}"
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
                h, src = float(str(r["height"]).split()[0]), height_label(r["src"])
            elif r.get("levels"):
                lv = float(r["levels"])
                st = STOREY_M[cls] if lv <= 1 or cls in ("house", "apartments", "shed") else STOREY_MULTI_M
                h, src = lv * st, f"OSM building:levels {r['levels']} x {st} m"
            elif r.get("alt_height"):
                h, src = float(r["alt_height"]), height_label(r["alt_src"]) + ", its footprint standing on this one"
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
        if lidar is not None:
            rec = lidar["buildings"].get(r["key"])
            if roofs is not None:               # opt-in (ledger 0083 pass 4): the roof's form fitted to the points
                new = roof_form_rows(row, rec, roofs["buildings"].get(r["key"]), lidar.get("stepped", {}).get(r["key"]),
                                     bool(plan.get("set_in_slope")))
            else:
                new = lidar_rows(row, rec, lidar.get("stepped", {}).get(r["key"]))
            out.extend(new)
            if (rec and rec.get("status") == "measured") or (new and roofs is not None and rec and rec.get("status") == "no_roof"):
                src = "lidar"
            elif not new:
                left["no_roof_in_lidar"] = left.get("no_roof_in_lidar", 0) + 1
                continue
        else:
            out.append(row)
        by_src.setdefault(src.split(" ")[0] + (" default" if "default" in src else ""), 0)
        by_src[src.split(" ")[0] + (" default" if "default" in src else "")] += 1
    for r in canopies:
        row = canopy_row(r, (lidar or {}).get("buildings", {}).get(r["key"]))
        if row:
            out.append(row)
            left["canopy"] -= 1
            left["canopy_on_posts"] = left.get("canopy_on_posts", 0) + 1
    if plan.get("roof_colour"):                 # opt-in (ledger 0083 pass 4); absent = as before
        print(f"[buildings] roof colours: {roof_palette(out, photo, plan['roof_colour'], track)}")
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

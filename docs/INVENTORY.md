# The surveyed inventory: paint, streetlights, signals, signs

*2026-11-23, ledger [0096](../fleet/feedback/0096-denver-grand-prix-and-the-front-range-backdrop.md), Denver Grand Prix
PLAN §4b. Kevin: "streetlights and road signs that are as accurate as you can make them. Same with road paint, we do a
terrible job currently. Currently track builds don't depend on this."*

A track that opts in is painted and furnished from a survey, and the built kn5 is held to that survey by three gates per
class. **Opt-in per track, off everywhere by default** (Kevin, E1: hard for Denver, opt-in elsewhere until proven). No
installed track declares any of this, and a test keeps it that way until one is written on purpose
(`tests/tools/test_inventory_gates.py`).

Every tolerance on this page is **[invented]**: PLAN §4b's own words and the pilot's ±0.3 m are the only sources. They
are in `fleet/GATES-CHANGELOG.md` (2026-11-23) and are replaced when a built track has been surveyed.

## 1. Turning it on

```json
"inventory": {
  "junctions": "source/survey/junctions.json",
  "paint":   {"file": "source/survey/paint.json",   "gate": true, "build_grades": ["measured"],
              "keep_prefixes": ["MARKINGS_paint_grid"]},
  "lamps":   {"file": "source/survey/lamps.json",   "gate": true},
  "signals": {"file": "source/survey/signals.json", "gate": true},
  "signs":   {"file": "source/survey/signs.json",   "gate": true}
}
```

| Key | What it does |
|---|---|
| `inventory.<class>.file` | the class's inventory, relative to the project folder. For paint this alone makes the chain paint from it (§3). The files must be in the workshop: list them in `ship.json` `sync_in` |
| `inventory.<class>.gate` | `true` turns that class's three gates on. Absent or false: not judged |
| `build_grades` | the grades that are built and held to *present*. Default all three. The pilot: "paint is ready to run on the lap as it is, with the detected grade kept apart" is `["measured"]` |
| `keep_prefixes` (paint) | mesh-name prefixes of declared additions: paint the survey does not hold and the track adds on purpose (a race layout's start line and grid, E4). Not removed, not judged |
| `tolerance_m`, `reach_m`, `junction_reach_m` | per-class overrides of §5's numbers |
| `prefixes`, `types` | per-class overrides of §4's mesh names |
| `surfaces` (paint) | the mesh-name prefixes the paint is draped on. Default `ROAD`, `1ROAD`: the ribbon and every junction pad |
| `inventory.junctions` | `{"junctions": [{"id", "lonlat": [lon, lat]}]}`: the junctions *covered* asks about. Not declared = not covered |
| `inventory.line` | the line *covered* walks. Default `data/centerline.local.json` |

In `ship.json`: the author step `paint_inventory` (after every step that lays road or paint: the weld, the pads,
`paint`) and the gate step `inventory`.

## 2. The files

**Frame.** Lon / lat (WGS84), turned into local metres about `data/centerline.local.json`'s origin with the draft's
own conversion. **Grades:** `measured`, `detected`, `tagged`. A record with any other grade (the pilot's
`rejected by eye`) is in the file and is not an item. Never `invented`.

**`paint.json`** is the survey pilot's schema as written
(`tracks/denver-grand-prix/source/survey/pilot/paint.json`). What each record paints:

| `class` | Read as |
|---|---|
| `line`, `pattern` `solid` / `single dash or fragment` | one stripe along `line_lonlat`, `width_m` wide. A fragment kept as one point, a `length_m` and a `bearing_deg` is the same mark end to end |
| `line`, `pattern` `broken` | one stripe per entry of `dashes_lonlat` |
| `line`, `pattern` `double solid` | two stripes inside `width_m` (the reader's width across both): each a third of it, a third apart |
| `bar` | one stripe along `line_lonlat`, `width_m` wide |
| `crosswalk` | one stripe per entry of `bars_lonlat`, `bar_width_m` wide |
| `symbol` | **cannot be built as read**: the pilot found a blob and did not read its type. In a built grade it stops the author step and fails *present*; held out by `build_grades`, it is counted |

White is built as `MARKINGS_inv_*`, yellow as `YLINE_inv_*`. A line's width is built as read and **not judged** (the
pilot over-reads thin lines by one to two pixels).

**`lamps.json`, `signals.json`, `signs.json`:**

```json
{"items": [
  {"id": "L0412", "type": "pedestrian_globe", "grade": "measured", "lonlat": [-104.98501, 39.74012],
   "facing_deg": 180, "junction": "Colfax / Sherman", "source": "DRCOG 2022, by eye"},
  {"none": true, "lap_m": [1650, 1994]},
  {"none": true, "junction": "Speer / Stout"}
]}
```

`facing_deg` is a compass bearing: the way a lamp's or a mast's arm reaches from its foot, the way a sign's face looks.
An item without it is built, counted as "facing not given" and not judged for facing. The pilot's `poles.json` is read
as it stands (`base_lonlat`, `arm_bearing_deg`, `class` `signal_mast_arm` → class signals, type `mast_arm`, its
`candidates` and `by_eye` lists); a post nobody classed is not an item.

**A surveyed stretch with nothing in it** is a record: `{"none": true, "lap_m": [from, to]}` (stations along the line;
on a closed lap `from > to` runs through the seam) or `{"none": true, "junction": "<id>"}`, in `items` or in a top-level
`"none"` list. An item standing inside a declared-none stretch is a contradiction and fails *covered*.

## 3. Paint from the inventory, and nothing by width

With `inventory.paint.file` written:

1. **`tools/author_paint_inventory_blend.py`** (author step `paint_inventory`) removes every paint object the inventory
   did not author (`MARKINGS*`, `YLINE*`, `ROADTEXT*`, minus `keep_prefixes`), then drapes every item of a built grade
   on the built road, the lap's ribbon and every junction pad alike, 15 mm over it, where the road is. It writes
   `AUTH_paint_inventory` and `data/paint_inventory.json` (what was painted, what was held out, every item with length
   that found no road under it). Nothing is inferred between marks.
2. **The prep** (`drop_bywidth_paint`, in airoso's `scripts/ac/build_kn5_loop.py` and in the engine-july copy an
   `lm-v4` track runs) removes by-width paint again just before the export, so paint a later step laid cannot ship, and
   stops if the inventory's paint is not in the scene.

A track that also has race and street layouts and wants the yellow paint in both (E4) sets
`road_markings.center_yellow: false`: otherwise `tools/split_exports_blend.py` moves every `YLINE*` into the
street-only kn5 (ledger 0063), the inventory's included.

Not handled: a road stacked over another road (the drape reads the top one).

## 4. How the built kn5 is read

By mesh name, in the chain's frame (a mirrored or yawed track is refused).

| Class | Meshes | One item is | Position | Type | Facing |
|---|---|---|---|---|---|
| paint | `MARKINGS*` white, `YLINE*` yellow, `ROADTEXT*` neither | its stripes | where the triangles are | colour | by the stripes' own ends |
| lamps | `LIGHTPOST*`, `LAMPHEAD*`, `LIGHTS*` | one post with its arm, head and lens | the foot | `LIGHTPOST_<TYPE>` | the way the arm reaches |
| signals | `SIGNAL*` | one mast or pedestal with its arm and heads | the foot | `SIGNAL_<TYPE>` | the way the arm reaches |
| signs | `SIGNFACE*`, and the older `SIGNPLATE*`, `SIGNS*`, `USSIGN*`, `EUROSIGN*` | one plate | the plate's centre | `SIGNFACE_<CODE>` | the way the face looks |

- **`<TYPE>`** is the item's `type`, upper case, every non-alphanumeric run one underscore: `mast_arm` →
  `SIGNAL_MAST_ARM`, `R1-1` → `SIGNFACE_R1_1`. `inventory.<class>.types` maps a type to another prefix.
- **One object** is every triangle that shares a vertex position with another, joined to any other such shell that has
  a vertex inside its box (grown 0.25 m): a mast, its arm, its heads. Two posts 3 m apart stay two.
- **A sign's face** is its triangles' winding as the kn5 holds it. A plate with a front and a back is judged as an axis.
- The older sign meshes are in the signs class so that a sign placed by rule (today's W1-6 arrow plates) is *extra*
  on a track whose signs are surveyed.

**Sign plates and UVs (PLAN §4b item 8).** A mesh whose name starts with `SIGNFACE` keeps the UVs it was authored
with through the prep and is not welded, in both preps. Every other name is treated as before; `SIGNPLATE` is still
projected, so today's plates do not change. The `pbr.TEXTURES` rows bind the bundled MUTCD faces by code in both
engines. Use the code from `assets/models/sign_faces.json`, normalized as above. For example, use `SIGNFACE_R2_1_30`
for the 30 mph plate. Object suffixes can follow an underscore or dot. Faces ship as alpha-tested `ksPerPixel`.
Use `SIGNBACK` for the opaque grey back. The exporter stops if an authored `SIGNFACE` material has no readable diffuse.
For lm-v4, stage the bundled artwork under the engine copy's `assets/textures/` before exporting.

## 5. The three gates (`tools/inventory_gate.py`, gate step `inventory`)

Each reads the built kn5 set a layout loads (LAWS L5). Exit 1 stops the chain; `--force-install` does not cover it.
`data/inventory_gate.<layout>.json` holds every row.

| Gate | Passes when | Numbers [invented] |
|---|---|---|
| **present** | every item of a built grade is in the kn5 within its grade's tolerance, the right type, facing the right way | paint: measured 0.30 m, detected 0.60, tagged 3.0; found on 95 % of samples taken every 0.5 m along each stripe. Posts and signs: 0.5 / 3 / 15 m. Facing: 15° / 30° / 45° |
| **nothing extra** | nothing of the class is in the kn5 that the inventory does not hold | paint: 0.01 m² of built paint lying on no inventory stripe of its colour. Posts and signs: 0 objects |
| **covered** | every metre of the line and every junction has an inventory record or a declared none | a record within 15 m (paint), 50 m (lamps), 40 m (signals, signs) of the metre; within 30 m of a junction's node |

The report states the share of each grade per class: measured, detected, tagged. On the pilot's paint: 125 measured
(40.6 %), 183 detected (59.4 %), 0 tagged.

What a failure says, from the tests: a solid line built where the inventory holds a broken one is *extra* (the paint in
the gaps); the wrong colour is *wrong type*; a post 0.8 m from a measured item is *missing* and the one built is
*extra*; a post every 55 m by rule is 7 *extra* on the pilot's 385 m.

## 6. What this does not do

- Read a survey. The lidar pole reader (PLAN §4b item 9) is not built: the pilot showed the lidar does not see posts.
- Author lamps, signals or signs from the inventory. Paint is authored here; the post classes are gated, and their
  authoring from the inventory is owed (today's `tools/plan_streetlights.py` and `tools/place_signs.py` place by rule).
- Judge a line's width, a lamp's height, or what a sign's face shows.
- Cover the race furniture's own paint, which the track declares with `keep_prefixes`.

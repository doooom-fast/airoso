---
id: 0046
title: "More terrain near the roads, the I-8 trench and adjacent causeway cut out" — and see Cowles Mountain from Navajo
status: in-progress — built and rehearsed 2026-10-12, fix round after two refuting verifiers (every gate identical to v0.17.1); criteria 1-7 measured below; awaiting the engine-july mirror, the install and Kevin's seat (criterion 8)
scope: tracks/san-diego-lake-murray (proof, street_port); engine scripts/elevation/heightfield.py HF_MARGIN_M + scripts/geometry/ribbon.py grass_terrain skirt + terrain tiering (every track, opt-in; Lookout Lariat next consumer); fleet/LAWS.md L3 "Fake mountains" (standard)
layer: standard + engine + project
train: -
---

## Status

**Built and rehearsed, not installed** (2026-10-12, airoso branch `worktree-wf_b291cd05-e2e-1`). Full
`ship_sd.sh --no-install` rehearsals on a scratch copy of the workshop: every gate verdict file is identical to
v0.17.1's field for field (street + race_cw + race_acw drive_test, audit, no_route planned and built, verify_mouths,
verify_race, verify_signs). Two independent verifiers then refuted the first rehearsed build (criterion 5's long facets
15–35 m from the roads, 19 I-8 sections, the I-8 not reading from the seat, a grey far ring); the fix round refined the
kept near-road cells past 20 m onto the 3DEP sub-lattice, inside the prep, after everything that shapes the near-road
ground — gates still identical — and gave the far ring a chaparral texture. Results are under **Results (2026-10-12)**
at the end: 1, 5, 6 and 7 pass; 2 passes from the crest and v2240, and from v1640 the world itself hides Cowles behind a
nearer hill; 3 passes but for "no vertex below 100 m", whose premise the landmark box contradicts (the San Diego River
gorge is 20–100 m in 3DEP); 4 passes on 162 of 171 sections, the 9 being sections on a pavement's own verge (criterion 7
holds that ground) or features narrower than a 5 m cell. The L3 amendment is in `fleet/LAWS.md` (Kevin approved it as
D6(i) of the Lariat plan). Criterion 8, Kevin's seat, is what closes this — frame rate first (`1GRASS` is now ~670k
triangles in 8 tiles). Before the install: mirror the two engine-july files (`engine-july-snapshot/PENDING-MIRROR.md5`)
and merge the branch. Not in here: I-8 as drivable pavement or as a visual ribbon (Kevin: extra highways "look like wavy
ribbons"), scrub on the new ground (0040), the summit antenna farm (authored prop). Filed three times concurrently
(0046/0046/0047); merged here, nothing dropped.

## Symptom (Kevin, seat, 2026-10-10, installed `san_diego_lake_murray_v3`)

> "more terrain near the roads, and the I-8 trench and adjacent causeway cut out"

> "I want to see cowles mountain at least  and maybe more of the i8 corridor when I'm up on Navajo"

One mechanism, three things from the seat: **(A)** past the sidewalk the ground is a few big flat
triangles per yard; **(B)** the freeway beside Alvarado is a shallow dish, not a cut, east of the Lake
Murray Blvd overcrossing it is not there at all, and no causeway exists; **(C)** from the top of Navajo
there is no mountain to the north-east and no Del Cerro hilltop with houses to the south — a flat
plateau ending in nothing, whose highest point is 8 m above the road. ELI15: the ground is one sheet of
triangles over a height map; it stops 150 m past the loop, is pressed to within 22 m of the nearest
road, is simplified into huge triangles far out, and bends down to a floor past the edge.

## Evidence

Built numbers: the gate OBJ of the installed V3 (`k10-sd-v021/project/data/track.obj`, `kn5_to_gate_obj`
from the 2026-10-09 kn5 — L5). Real numbers: fresh USGS 3DEP `getSamples` (`scripts/elevation/usgs_3dep.py`),
never the heightfield that placed the terrain. Frame: `centerline.local.json` origin lon −117.046664
lat 32.788356, elev0 100.8 m, true north 0.0, x east / z north, metres; heights absolute (y + 100.8).

**The grid.** `data/heightfield.meta.json`: `bbox_swne [32.771983, −117.069563, 32.805287, −117.017103]`,
123 × 93 nodes, **`spacing_m 40.0`, `margin_m 150.0`** — 11,439 3DEP samples, 4.91 × 3.69 km (18.1 km²),
local x −2143..2766, z −1810..1872 (a second projection read x −2137..2759, z −1817..1879; rounding),
151/151/147/149 m W/E/S/N past the loop bbox (x −1991..2615, z −1663..1723). The 20 m facets add no
data: `ribbon.upsample_grid(grid, meta, 2)` at `build_loop_blend.py:690`, bilinear, 45,325 nodes. Both
constants are module globals: `tracks/san-diego-lake-murray/scripts-v021/elevation/heightfield.py:27-28`
(`HF_SPACING_M = 40.0`, `HF_MARGIN_M = 150.0`; `:98-115` `build_heightfield` samples loop bbox + margin
and nothing else; `:192` the only call); the live engine `scripts/elevation/heightfield.py:50-51` is
identical for every track (networks: `network_elev.py:27` `GRID_MARGIN_M = 220.0`).

**Where Cowles is** — three independent 3DEP probes, 2026-10-10, agreeing to 40 m / 1.1 m:

| probe | summit | local (x, z) |
|---|---|---|
| **primary:** 480-pt 100 m lattice (32.798–32.816 / −117.045–−117.020), then 13 × 13 at 20 m | **483.2 m, 32.81277 N 117.03192 W** (USGS 1,593 ft = 485.5; a 20 m lattice can miss the top by a few m) | **(1380, 2700)** |
| 21 × 21 window at 50 m | 483.7 m, 32.8127 / −117.03184 | (1389, 2700) |
| 235 m search grid, 50 m refine | 482.6 m, 32.8130 / −117.0320 | (1368, 2736) |

(1380, 2700) is used below. Two published coordinates are *not* the summit: the brief's 32.8008/−117.0314
reads 180 m (grid node 178 — the south flank); Wikipedia's 32.8172/−117.0297 reads 300 m (north ridge).
North along lon −117.0325: 240 m at lat 32.805 → 312 at 32.8075 → 371 at 32.810 → 467 at 32.8125 — the
mountain starts climbing ~300 m north of Navajo.

**From where Kevin stands.** "Up on Navajo" = the north leg, centreline 1872–2621 (z > 1300), 163–212 m;
the crest at the Jackson corner is idx 2325 / (62, 1713), 210.1 m (3DEP agrees); the loop's highest
point is (160, 1564), 212.5 m. To the summit, eye 1.2 m:

| station | abs | distance | bearing | summit elevation |
|---|---|---|---|---|
| idx 2325 crest (62, 1713); v2319 | 210 m | 1,653 / 1,648 m | 053° | **+9.35°** / 9.4° — 121-pt 3DEP profile dips to 167 m at 450 m (the lake arm), climbs from 902 m without a break; highest intervening sample +9.37° at 1,638 m is the summit's own shoulder |
| crest (160, 1564); v2385 | 212.5 m | 1,683 / 1,666 m | 046° / 047° | 9.1° (270 m rise) / 9.2° |
| v2240 (`0033-navajo-jackson`) | 200 m | 1,882 m | 054° | 8.5° (282 m rise) |
| v1640 (`0037-navajo-north`) | 137 m | 3,588 m | 059° | 5.5° |

A 483 m peak 1.6–1.9 km off at 8–9° is a dominant skyline object. **Built**, same bearing from the crest:
`1GRASS` 211.7 m at 100 m, then 212 → 189 m flat to 1,100 m, then no surface (the decimated skirt is the
last thing). Highest built angle toward Cowles **+0.27°** — the road's own verge.

**What the grid holds of Cowles, and what the build did with it.** The summit is **820–860 m past the
grid's north edge** (z 1872–1879, itself 165–315 m north of the crest by station) and ~330 m past the
500 m skirt's outer edge. Raw 3DEP along x = 1428 rises 178 → 184 → 193 → 209 → 237 m from z 1400 to
1800; the north-edge row peaks at **256.5 m** (x 1187–1194): the flank enters at ~29 % and is cut off.
Grid max anywhere 258.3 m — the Del Cerro hilltop inside the loop, (−418, −200). Then:

1. **`band_clamp`** (`scripts-v021/blender/build_loop_blend.py:104-133`; docstring `:9-10` "so the raw
   DEM's Cowles-area peaks can't tower over a neighbourhood loop with none", repeated in `track.config.json`
   `terrain._doc`; `terrain.terrain_band_m 22.0` at `:590`; called `:698-699` after the conform with every
   mainline + connector point) clamps **every** node to nearest-road-y ± 22, no distance limit (bucket
   search to r < 40 × 130 m). At (1187, 1872) the nearest road point (746, 1343) is 187 m → ceiling
   **209 m**; at the summit, had the grid reached it, 217 m by that search (≤ ~235 m by any north-leg
   road). On the raw grid: **2,644 / 11,439 nodes moved (23.1 %)** — 1,754 down, max **94.6 m** (Del Cerro
   258.3 → 163.7, nearest road 790 m); 890 up, max **78.4 m** (NW corner (−2145, 1638) 57.1 → 135.5,
   nearest road 861 m); north-edge row 256.5 → 219.7; 6,300 nodes (55.1 %) are > 300 m from any road,
   1,334 cut down. The real Del Cerro hillside climbs 36 m above Navajo within 300 m; held to road + 22.
2. **`tools/slim_far_terrain_blend.py`** (`FAR_M 220`, `RATIO 0.35`, COLLAPSE decimate by vertex group;
   `ship_sd.sh:56-57`) takes every TERRAIN vertex > 220 m from a mainline/connector point to 35 % —
   b8c2dbd 50,356 → 20,405 verts after two FATAL refusals at 67–72k ("'1GRASS_0' has 67114 positions").
   Its docstring: "the hills nobody drives are meshed at the same 20 m as the verges" — Kevin's hills.
3. **The skirt**: `scripts-v021/geometry/ribbon.py:265-315` `grass_terrain(skirt_m=500)` (engine
   `scripts/geometry/ribbon.py` ~`:667-800`) extrudes the border 500 m out and **down** to `low_y =
   min(terrain) − 5`, "a floor you never reach". Built floor **69.0 m abs** (local −31.8; one read said 64);
   `1GRASS` spans x −2647..3255, z −2302..2399. Where the world rises 270 m the build drops to 69: a pit
   414 m below the summit, in every direction.

As built (`1GRASS_0` 55,572 v + `1GRASS_1` 22,376 v; `audit.json grass_verts 77948`; `inspect_kn5` GRASS
2 meshes, 18.8 m grid):

| region | DEM | built `1GRASS` |
|---|---|---|
| whole grid max | 258.3 m | **220.0 m at (465, 1638)** beside Navajo's crest — Del Cerro shaved 38 m |
| NE corner x > 1000 z > 1500 | 256.5 m | 200.6 m — Cowles' foot shaved 56 m; north-edge row (z 1840–1900) 191–203 vs raw 209–256 |
| x > 600 z > 1700 | — | **zero vertices** |
| south strip z < −1500 | 171.5 m | 146.4 m — the I-8 south wall shaved 25 m |
| Del Cerro top (−418, −200) / south sightline | 258.3 / 246 m | 163.7 / 167.6 m |
| facet longest edge ≤ 15 m from a road | | median 5.6 m, p90 10.3 m |
| 15–60 m | | median 5.6, **p90 28.3 m** (the 20 m grid's diagonal) |
| 60–220 m | | median 28.3 m |
| 220–500 m | | **median 346, p90 777 m** |
| > 500 m | | **median 1,331, p90 2,996 m** |

**The I-8 half.** `data/i8.local.json`: 64 points, x −2021..2693, z −1809..−993, abs 98–167 m, all inside
the grid (clipped to the loop bbox). **No script writes it** — grep across k10-sd-v021, airoso,
k10-track-agents finds only the reader `_load_i8` at `build_loop_blend.py:137`; provenance unrecorded
(L1 corollary). The OSM cache `airoso/data/osm.json` has 44 `highway=motorway ref="I 8"` ways (4
bridge-tagged), x −3840..4734, z −1941..−813: 1.7 km past the grid's west edge, 2.0 km past its east.
Alvarado = verts 0–697 (x +6 → −1884, z −1662 → −1120), 33–110 m from the I-8 centreline, abs 101–124 m;
College Ave crosses at 828–920, Lake Murray Blvd at 4424–4498 (the seam). Raw-grid cut depth (ground
±50 m perpendicular minus floor) vs built (min y within 12 m of the section):

| I-8 station (x) | where | raw 40 m grid | as built |
|---|---|---|---|
| −1482..−1004 | beside Alvarado | north rim +7–8 m, south ≈ floor (half-cut into the north slope) | south −60..0 m at 6.1–6.9; north +15→+60 m 12.7→17.0: the wall is **one 20 m facet** |
| −158..+65 | Lake Murray Blvd crossing | 1–3 m | flat 14.9–17.5: no trench |
| +209..+349 | ~250 m east of the crossing | floor ≥ ground both sides (−0.7/+0.3 m: fill, at 40 m noise level) | flat 20–21: no fill |
| +1101..+1448 | east of 70th St | **7–9.5 m, the deepest cut** | **no vertex within 12 m of any section point** |

30 of the 64 points are > 220 m from any loop road, so `slim_far` collapsed the deepest real cut into the
far facets — "cut out", literally. `cut_i8_trench` (`:158-180`, called `:702`; `half_w 16`, `bank 6`,
`depth 1.0`) sinks nodes within 16 m of the polyline to floor − 1 with a 6 m bank — a 32 m ditch,
sub-cell on a 20 m grid, so its walls are grid facets — and only lowers (`if y > target`): **no code path
can raise an embankment**, so the causeway cannot exist whichever section Kevin means. `_level_i8_decks`
keeps the two overcrossings. The 40 m grid cannot say which section is on fill; a 2 m 3DEP cross-section
pass will (L12: he has driven it — let the data find where, not whether). 3DEP transect due south from
the crest along lon −117.045 (100 m steps): lake 161.8 m z −39..−1138; **trench 121–125 m z −1438..−1738;
far bank 155–163 m z −1838..−1938**; ~145 m plateau to z −3000; 123–146 m to z −5300 (Mission Valley).
The grid's south edge (z −1810/−1817) is **inside the trench**: the south bank is 20–120 m past the edge
and the skirt ramps down instead; the trench ends at the map edge east and west.

**What is actually visible from Navajo.** 3DEP line-of-sight from five Navajo stations (125, 149, 168,
180, 210 m) to nine I-8 points, 24 samples each: **0 / 45 visible** — the pavement is behind the Del
Cerro hill from everywhere on Navajo Road, in reality. South profile from the crest (bearing 192°,
nearest I-8 point 3,053 m, floor 112.1 m), real: 170 m at 1.46 km, **246 m at 1.94 km (Del Cerro, +1.0°
above the eye)**, 112 m at I-8 (−1.8°), 137–142 m for 0.3–1.8 km beyond (the valley's south wall).
Built: hilltop 167.6 m, a 165–200 m plateau to 2.4 km, trench 111.9 m (matches the polyline), far wall
130–140 m to 4.05 km, then void (edge 3.61 km + skirt). What Kevin misses to the south is the *corridor
as landscape* — the hill in front (clamped), the valley wall and skyline beyond (past the edge) — not
the lanes. (L12: if he remembers the freeway from Navajo, check the Jackson / Lake Murray Blvd descents.)

**The cap and the compensation chain.** `engine-july/scripts/ac/build_kn5_loop.py:41` maps the one
`TERRAIN` object to `1GRASS` (physics + GrassFX + tiling); `:49-50` `VERT_CAP 65535`, `SPLIT_CAP 60000`;
`_split_large` (`:176-224`) cuts `K = n // 60000 + 1` equal-width bands along the longest axis;
`assert_under_cap` (`:166`) is FATAL on positions. Three passes fight over one uniform budget: the prep's
corridor subdivision (`CORRIDOR_EDGE_M 4.5`, `BAND_M 3`, `FEATHER_M 6`, mainline only),
`tools/seat_terrain_blend.py` (connectors only — the mainline too "pushed a grass tile to 71,821 verts"),
and `slim_far` paying for them. Four passes already do the near-road job the clamp was invented for:
`ribbon.conform_terrain_to_road` (corridor 20 m, blend 16 m, `:694`), `carve_road_corridor` (`:700-701`),
the prep's `_conform_and_reseat` pin (`build_kn5_loop.py:298`, `:613`), `seat_terrain_blend`.

**Consumers of the tile names.** `scripts/ac/ext_config.py:59` lists every `1GRASS*`/`1LAWN*` group as
GrassFX `GRASS_MESHES`; `:95-97` builds the occlusion field over every listed mesh at session load; `:60-75`
the occluder allow-list, `:62-64` names "the far-field MOUNTAINS backdrop" as the thing never to enrol
(the v0.12.1–0.12.6 TDR whole-PC freeze). Gates key on `1GRASS`: `audit_mesh.py:181`, `drive_test.py:63`,
`kn5_ground_check.py:26`. `tools/make_treefx.py:32` hardcodes `SURFACE_MATERIALS = "1GRASS_0_mat,
1GRASS_1_mat, 1ROAD_road_mat"`; its fill (`FILL_BANDS` `:51-55`, `:178-193`) walks `heightfield.npy` only
to 200 m from a road, so a larger grid does not flood trees — but the Cowles flank has no chaparral zone
(0040's open "scrub density on the Cowles side"). `scripts/ac/pbr.py:88` `MOUNTAINS` is `(None, None, …)`
and `setup_material` (`:202`) adds an image node only when a diffuse exists — per L7 it renders black.

**Precedent and references.** `scripts/geometry/build_mesh.py:815-834` `terrain_cell_m` /
`terrain_vertex_budget` (uniform upsample ≤ ×32, opt-in, "everything else keeps … its exact current
output"), `:1965-1968` `corridor_refine_factor` — already two-tier in the OBJ path; the Blender-first SD
chain uses the v021 assembler with only the ×2 upsample. `docs/PRO-KN5-CONSTRUCTION.md` §3: pro density
"~0.7 m at the verge → 1 m at 30 m → 3.4 m at 100 m → 12–17 m beyond 300 m … our uniform grid is our
single biggest structural difference"; §1: a far backdrop ships as its own visual-only kn5 (`[MODEL_1]`
in `models.ini`; SRP's Kanto skyline 3 meshes / 15k tris). The engine's fake horizon
(`scripts/environment/build_env.py:1312-1333`, `build_network_env.py:390-415` `scenery.mountains`) draws
hazy sine-wave ridges west of Colorado tracks; no SD config uses it (grep: only SD carries
`terrain_band_m`, nothing carries `"mountains"`) — for Cowles, 1.7 km off and 9° up, a sine ridge is L1's
"never invent" broken. Masters, measured 2026-10-10 (`scripts/modkit/extract_kn5.py` + `fast_lane.ai`,
REALISM §3 shelf) — both ship the real hills as a coarse, separate, visual-only terrain:

| reference | road extent | separate terrain kn5 | reach past the road |
|---|---|---|---|
| `mulholland_v1` | x −6988..5135, z −1321..204 | `la_terrain_background.kn5`: 35 meshes, 466,903 v, x −15463..15991, z −12670..12171, y to 1000 m | **8–12 km**, ~13k verts/mesh |
| `pacific_coast_hwy` | x −6412..6803, z −7547..7347 | `terrain.kn5`: 43 meshes, 934,769 v, x −7789..7147, z −7926..8297, y to 982 m | 0.4–1.4 km land side (`ocean.kn5` the rest), ~22k verts/mesh |

## Diagnosis

One grid policy, three symptoms, in causal order: **extent** (primary — `HF_MARGIN_M 150`; nothing Kevin
asked for was ever sampled: Cowles 820–860 m past the north edge, the I-8 south bank 20–120 m past the
south edge, the trench ending at both side edges) → **clamp** (`band_clamp` ±22 m everywhere; would
defeat a bigger grid alone: Del Cerro −38 m, Cowles' foot −56 m, the summit → ~217–235 m) →
**decimation** (`slim_far` 35 % beyond 220 m so one uniform sheet fits two sub-65k tiles — the cap, not
the view, decides how much world there is) → **skirt** (500 m ramp to 69 m: "missing" becomes "wrong").
So **(C)** the flank the grid holds is clamped, collapsed into 350–3,000 m facets, and the world tops
out at 220 m; **(B)** a 16 m / 6 m cut is narrower than the 20 m cells it is cut into (a one-cell dish),
`slim_far` ate it east of Lake Murray Blvd, and a lower-only cutter on a cross-section-less polyline
cannot make a causeway; **(A)** ~5 m refinement stops at pavement + 9 m, then the 20 m grid (28 m
diagonals) against a pro gradient still at 1 m at 30 m.

**L3 is part of the cause.** Its "Fake mountains" bullet — *"A raw DEM carries real peaks that tower
over a neighbourhood loop (Cowles ~500 m over Lake Murray). Clamp terrain to within a band of the
nearest road height (`terrain.terrain_band_m`, 22 m in SD)"* — names the real mountain as the example
of a fake one. The failure that bought it was real (v0.9.1 `b4e5555` "slope-limit the grass so DEM
mountains stop being collidable walls"; v0.9.3 `50dc934` "no more Cowles 'mountain' the road climbs";
`heightfield.py:157-162` "the neighbourhood came out as a mountain the road climbs") but it was a coarse
grid aliasing relief *into the corridor* plus a road-datum defect, which L3's first sentence, bullet 3
(the 70th St 57 % cliff) and ledger 0002 own. The remedy generalised "near the road" to "anywhere in the
grid" and patched the ground for a defect in the road. Cowles is 4.7 km of real mountain Kevin wants to
see from his father's street (L12). Amend L3 first, then the code.

## Fix

**Standard — amend L3 "Fake mountains" (needs Kevin's sign-off; laws are his):** *near-road relief is
clamped, far relief is data.* The band applies only inside the road's own tier / conform corridor and
releases with distance (proposals: ±band within ~60 m = corridor 20 + blend 16 + one cell, or
`clamp_corridor_m` ≈ 100 m; blend to the raw DEM by `clamp_blend_m` ≈ 250 m or the medium tier's edge
~500 m); beyond, 3DEP uncapped. Cowles becomes the example of relief that must *survive*; the road-datum
failure stays, attributed to 0002; strike the sentence in `track.config.json` `terrain._doc`. Extent
becomes a dossier decision (`LOCATION-DOSSIER.md:48` §6 "backdrop and skyline"), not a constant.

**Engine (`scripts/`), opt-in per track so every other track keeps its exact current output:**

- **E1 Tiered sampling + far ring.** `HF_MARGIN_M` → `terrain.margin_m` (default 150); `terrain.extent`
  (per-side margins or bbox); `terrain.tiers` e.g. `[{within_m: 60, cell_m: 5}, {within_m: 500, cell_m:
  20}, {cell_m: 40}]`; `terrain.far_extent_m` / `far_spacing_m`, cached as `data/heightfield.far.npy` +
  meta (L2); `terrain.include` named polygons with their own cell (`cowles_mountain` 20 m, `i8_corridor`
  10 m, ±150 m about the OSM `ref="I 8"` centreline). Sample 3DEP at each tier's spacing directly
  (`usgs_3dep.sample_points`, 450 pts/request), no bilinear upsample; triangulate the multi-resolution
  set (quadtree with stitched T-junctions, or Delaunay); place by real lon/lat through the mirror-aware
  projector (the Aspen skirt mirror bug, `ribbon.py:772-781`). Budgets: 5/20/40 + both polygons ≈ **131k
  verts / 3 tiles** (fine 2.05 km² 82k, medium 9.8 km² 24k, coarse + 1.3 km north extension 6k, Cowles
  2.0 × 1.6 km 8k, I-8 11k; today 77.5k / 2); 4 m fine → 177k / 3; 10 m medium → 218k / 4. Ring alone:
  3,000 m at 80–100 m ≈ 11–17k verts, ~25 requests (Mulholland's ~13k/mesh is the target); 8 × 8 km @
  40 m = 40,401 (one mesh, 90 requests); @ 60 m = 17,956.
- **E2 Distance-weighted band clamp** — the L3 amendment in code; conform / carve / seat unchanged in the
  fine tier. For SD, land it where it runs: 0047 found `ship_sd`'s draft stage executes the `k10-sd-v021`
  copy of `build_loop_blend.py:104` (the airoso `scripts-v021/` snapshot `diff`-identical; CLAUDE.md calls
  the airoso copy the tooling of record — confirm which runs before patching). Another downstream Blender
  pass would be compensation number five: fix the source (Kevin's call, given the fork's "don't extend").
- **E3 Tiling by tier, far ring visual-only.** Balanced bisection (`palm.chunk_mesh`'s median split, not
  equal-width bands — the PALMFROND 82,797 failure). Fine + medium tiles stay `1GRASS_n`; far tiles carry
  **no digit prefix** (`GRASS_FAR_n` / `TERRAIN_FAR`): no physics, never scanned by the three gates,
  skipped by `ext_config`'s `startswith(("1GRASS","1LAWN"))` — **no GrassFX field over Cowles, no TDR
  growth**; `_split_large` tiles it, `verify_kn5` enforces 65,535. Material: a **textured** far-ground key
  (dry-chaparral `1GRASS` set — scrub, not turf), never the texture-less `MOUNTAINS` slot. Optional: a
  separate backdrop kn5 as `[MODEL_1]`, keeping the base kn5 and gates byte-identical (`kn5_ground_check`
  told about it). Skirt: the near border sits on the DEM and the 500 m ramp goes — (a) no skirt, far ring
  visual-only (150 m of physical verge exceeds any excursion; `drive_test` checks drops *from the road*),
  recommended and what both masters do; or (b) physical `1GRASS_far`, paying gate time plus an audit J
  exemption (0011) in `GATES-CHANGELOG`. **Delete `tools/slim_far_terrain_blend.py`** and its
  `ship_sd.sh:56-57` step; lift `seat_terrain_blend.py`'s connectors-only restriction (measure the prep's
  position count first). Never `scenery.mountains` — Cowles must be 3DEP (Colorado removal: follow-up).
- **E4 Cut/fill corridors.** Generalise `cut_i8_trench` into `terrain.corridors`: centreline from the OSM
  motorway ways (provenance recorded, L1), floor from 3DEP every 10 m, **2 m 3DEP cross-sections every
  25 m** so walls *and* fills come from the data, raising as well as lowering, in the corridor's 10 m
  cells; `_level_i8_decks` keeps the two overcrossings. Kevin's call: a visual-only I-8 pavement ribbon
  along the floor so "more of the corridor" reads as a freeway.

**Project (`tracks/san-diego-lake-murray`):** `terrain.extent` north to z ≈ +3,300 (lat ≈ 32.818, ~600 m
past the summit for its north shoulder) or `far_extent_m` 3000 (summit cone inside a 1.5 km margin, plus
the San Carlos mesa, the full I-8 south bank, Mission Valley's lip); the dossier's landmark box — summit
+ ~1 km (north ≥ 32.822), the valley wall south of I-8 (south ≤ 32.755), the Cowles ridge east (−117.00),
the river gorge west (−117.085), ~8 × 7.5 km; east/west to the OSM I-8 extent (x −3,840..4,734) only if
Kevin wants the corridor beyond the loop. Both `include` polygons, `clamp_corridor_m` / `clamp_blend_m`,
`_doc` rewritten; re-run `scripts.elevation.heightfield` (≈ 22k coarse + ≈ 95k fine samples, ~260
requests). **Re-fetch `data/i8.local.json`** over the far bbox from the cached OSM ways (data layer,
provenance recorded) so the cut carries to the ring's edge. The far ring is a **`GEN_` object in
`loop.blend`** (REALISM §4): regenerable, beside authored layers, never through them — TERRAIN is
regenerated by `ship_sd`'s draft stage and the median island deck is authored *onto* it afterwards by
`author_median_blend`, so the order holds. `tools/far_terrain_blend.py` (the 0040/0041 pattern, after
`seat_terrain_blend`) only if the engine side is not ready. `make_treefx.py` reads tile names from the
OBJ; Cowles chaparral (sage/yucca/agave, no palms) is 0040's species-zone pass; the dossier gets both
landmarks. **Cost:** one 3DEP re-sample; +~53k verts (kn5 +~3 MB) for full tiering or one far mesh ≤ 65k
for the ring; 3–4 tiles; gate runtime up with vertex count; GrassFX / TreeFX lists regenerated; one
material, one `models.ini` line if separate. Gates unchanged.

## Scope

- **Proof:** `san-diego-lake-murray` — all three symptoms, the only Blender-first chain; the Navajo crest
  (idx 2325) looking NE and S, `seam-alvarado` for the cut.
- **Second proof:** `lookout-lariat` (0048 rebuild) — canyon shelves need real relief past 150 m, the Front
  Range is real and currently a sine-wave; where E2's release meets stacked legs (L4: a far shelf must
  not grab the wrong leg's height); its enablement is a line in 0048. Also gains: Pikes Peak, the Dragon
  Tail stages (0014's long thin strip). The band clamp itself is SD-only (`scripts-v021` fork).
- **Regression (must not change):** Colorado circuits declaring `terrain_cell_m` (IMI, Aspen, GJ, PPIR,
  Pueblo) with no `terrain.tiers` / `far_extent_m` → byte-identical heightfield, `1GRASS` and gate numbers;
  the flat circuits (High Plains, Second Creek, Sand Creek) likewise; with the ring set, nothing visible
  moves on a flat track; rally ground-on-top counts (0006 / 0014) unchanged. Kinds: all, by opt-in;
  `street_port` and `rally_stage` will want it.

## Verification (decided now, before the fix)

On the gate OBJ / kn5 (L5) against independent 3DEP, before anything is installed:

1. **Cowles is there:** max terrain y within 60 m (XZ) of (1380, 2700) ≥ **470 m abs** (3DEP 483.2 less
   one coarse cell's rounding). Today: no vertex there; world max 220 m; nearest ground the skirt at 69 m.
2. **Cowles is visible:** `tools/sightline_check.py` (new, read-only on `track.obj`) marches the built
   terrain from (62, 1713) + 1.2 m eye toward the summit at 10 m steps; the profile reaches **≥ 9.0°** at
   ~1,650 m (real 9.35°, built today 0.27°) and the summit's angle exceeds every intermediate one;
   repeated from v2240 (8.5°) and v1640 (5.5°).
3. **South, and the far ring exists:** on bearing 192° a built surface to **≥ 5 km** (no `None`); the Del
   Cerro hilltop (−418, −200) ≥ **250 m** (real 258.3); the valley wall at 3.4–4.9 km 130–145 m; the I-8
   south-bank max in z −1838..−1938 at x ≈ 160 is 150–170 m (3DEP 155–163; today 146 then the ramp);
   terrain faces at z ≤ −2500 and x ≤ −4000 / x ≥ 4500; **no terrain vertex below 100 m abs** anywhere
   (the pit is gone; the real low is the trench ~121 m / Mission Valley ~123 m).
4. **I-8 cut and fill:** cross-sections every 50 m along the OSM I-8 centreline through the built
   terrain: floor within ±1.0 m of 3DEP; rim-to-floor at ±60 m within ±2.0 m of the 2 m 3DEP section;
   every section has vertices within 12 m (today none east of x 1100); any fill section 3DEP confirms
   stands above its flanking ground by the 3DEP amount ±2 m.
5. **Near the roads:** facet longest edge 15–60 m from any road p90 ≤ **7 m** (today 28.3); 60–500 m
   p90 ≤ 28.3 m (today 346–777 m beyond 220 m).
6. **The far ring is the data:** every far cell within 1 m of 3DEP (nothing between may clamp it); no far
   triangle has a horizontal edge longer than two of its own cells (0011's rule, measured, not gated).
7. **Cap, gates, regression unchanged:** `1GRASS` vertices within 150 m of any road `|Δy| ≤ 0.05 m` vs
   the 2026-10-09 build; `drive_test` kinks 4.97/km, soft_top_in_lane 82, severe 0, obstruction 0,
   replication p95 0.42; `audit_mesh` B 0, J 0, F 15, K 154, I 145, worst_terrain_span 0.0; `verify_kn5`
   every mesh ≤ 65,535 positions, tile count reported, no far mesh with a `1` prefix; `ext_config.ini`
   GrassFX `GRASS_MESHES` lists only `1GRASS_n`, occluder list unchanged; lights (0043) untouched; the
   Colorado / rally regression set above byte-identical.
8. **Kevin's seat (the only verdict that closes it):** start `0033-navajo-jackson` (v2340) / the crest,
   facing NE — Cowles fills the view above the rooflines, bearing ~046–054°, 8–9° up, its real shape,
   rising as the road does; facing S — the Del Cerro hilltop with its houses above the eye line, valley
   and hills on the horizon behind it, no void; start `seam-alvarado` — the cut with its north wall and
   two overcrossings, the causeway where he knows it is, the trench running out of sight both ways; frame
   rate no worse than v3 (far tier visual-only, one draw call, no GrassFX on it; `LIGHTPOST_*` already at
   the cap); night drive unchanged; chaparral, no palms, once 0040's zone lands. A fixed camera station at
   the crest, bearing 046°, joins the flythrough set (REALISM §4 `views.py`) for every later build.

## Results (2026-10-12) — measured on the built gate OBJ against fresh 3DEP (L5), before any install

**What was built.** The ground is one multi-resolution lattice. USGS 3DEP is sampled **at every vertex**
(`scripts/elevation/terrain_sample.py`, cached with its provenance in `data/terrain.samples.json.gz`: 335,112
samples; the I-8 corridor in `data/corridor.i8.json`: 893 floor samples every 10 m and 358 cross-sections of 81
points at 2 m). The cells are 5 m within 60 m of a pavement, 20 m to 500 m and 40 m beyond. The I-8 corridor (±80 m
about the median of the two OSM carriageway chains) is 5 m and the Cowles cone is 20 m. The extent is the dossier's
landmark box, 32.755–32.822 N by 117.0895–116.998 W (8.6 × 7.4 km). Under and beside the roads, the graded v0.17.1
grid's own 20 m cells within 18 m of a pavement are kept triangle for triangle, so the seat and the kn5 prep reshape
the same ground they always did. **Then** (fix round, after the verifiers) the prep refines those kept cells: every
edge over 5.5 m of a kept face reaching past 20 m is halved (coplanar — the halving lands on the 5 m x-split
sub-lattice), and every kept vertex more than 20 m from the pavement (the data's or the built road's, whichever is
nearer) takes the 3DEP sub-lattice feathered from the graded height over 16 m, exactly as the lattice beside it does.
Within 20 m of a pavement nothing moved. The band clamp follows L3 as amended: in full within 80 m of a pavement,
released by 250 m, 3DEP beyond. Ground within 250 m of a road is physical `1GRASS`; the rest is `GRASS_FAR`: visual
only, never gated, GrassFX-listed or an occluder, and now textured as grey-olive chaparral over tan soil
(`tracks/san-diego-lake-murray/textures/`; it was pbr's stock grey gravel). `slim_far_terrain_blend.py` and the 500 m
skirt are gone. No I-8 pavement. Every number marked invented is in `fleet/GATES-CHANGELOG.md` (2026-10-11, tiered
terrain, and its 2026-10-12 fix round).

Measured on the final full rehearsal (ship9: `ship_sd.sh --no-install`, full chain, scratch workshop, ENG = the
scratch engine-july; gate OBJ md5 6b8ee0caede11064c846a5843997091a) with two independent sets of code: the
implementer's (`tools/sightline_check.py`, measure scripts) and the truth verifier's own (its OBJ parser, its own
OSM-median I-8 centreline and 171 stations, 18,377 fresh 3DEP points fetched 2026-10-12 with TLS on).

| # | criterion | v0.17.1 | now | verdict |
|---|---|---|---|---|
| 1 | max terrain within 60 m of the summit (1380, 2700) ≥ 470 m | no vertex (world max 220.0 m) | **484.34 m**; surface at the nominal point 482.5 m (3DEP 482.56); fresh 3DEP's top is 484.08 m at (1390, 2710), ~14 m off the nominal | PASS |
| 2 | crest (62, 1713) → summit ≥ 9.0°, summit above every intermediate | 1.10°, no surface past 210 m | aimed at the built top (484.34 m, inside the 60 m cone): the summit as seen **9.345°** (the top 9.318°, the nominal point 9.35°); highest step outside the cone 9.24°. 3DEP: 9.375° against 9.127° | PASS, reading "the summit" as its cone (the ledger's own Evidence calls the profile's last samples "the summit's own shoulder"). Read against the single nominal point, every intermediate including the shoulder, it fails in the build (9.350 vs 9.358 at 1,640 m) **and in 3DEP** (9.355 vs 9.375 at 1,630 m) |
| 2 | v2240 → summit (real 8.5°) | 2.54°, no surface past 460 m | **8.487°** (top 8.481°); outside the cone 8.35°. 3DEP 8.512° against 8.31° | PASS (same reading; the strict point reading fails in 3DEP too: 8.500 vs 8.512) |
| 2 | v1640 → summit (real 5.5°) | 6.41°, no surface past 2,350 m | summit **5.49°**, but a hill 340 m off stands at 6.60° | FAIL as written — **and in the world**: fresh 3DEP has that hill at **7.23° at 350 m**, the summit at 5.49°. Cowles is hidden from v1640. The built hill is 3–4.6 m below 3DEP there (85–121 m from a road: the L3 clamp's release band), so the build hides it a little less than the world does |
| 3 | bearing 192° from the crest: a built surface to ≥ 5 km | void past 4.05 km | surface to the far box's edge at **5,550 m**, 0 holes in a 25 m probe lattice over the whole box (101,871 rays); built vs 3DEP at 1,460 / 1,940 / 3,000 / 4,000 / 5,000 m: 171.4/169.9, 243.9/244.5, 113.0/112.9, 138.8/138.9, 141.8/141.5 m | PASS |
| 3 | Del Cerro hilltop (−418, −200) ≥ 250 m | 168.4 m | **258.11 m** (3DEP 258.15) | PASS |
| 3 | valley wall 3.4–4.9 km out, 130–145 m | void | **133.15–142.36 m** (3DEP 132.37–142.59) | PASS |
| 3 | I-8 south bank max (z −1838..−1938, x 160 ± 30), 150–170 m | no vertex (the skirt ramp) | **165.62 m** (3DEP 165.64) | PASS |
| 3 | faces at z ≤ −2500, x ≤ −4000, x ≥ 4500 | 0 / 0 / 0 | 13,054 / 374 / 1,501 faces (6,696 / 188 / 886 vertices) | PASS |
| 3 | no terrain vertex below 100 m abs | 107 (the skirt floor at 69 m) | **21,272** below 100 m (2,586 physical), all west of x −539; the lowest 19.67 m at (−2627, 2717), where 3DEP reads 19.67 m | FAIL as written — the clause's premise is false. It assumed the real low was ~121 m (trench / Mission Valley); the landmark box this ledger asked for reaches the San Diego River gorge, 20–100 m in 3DEP. 985 of these vertices (the 400 lowest + random) against fresh 3DEP: median 0.003 m, p95 0.005 m; the 18 off by > 1 m are graded ground beside College Ave / I-8 (x −1891..−1745, up to 6.6 m) and one at (−1543, 1358). No pit: the skirt is gone. Kept as data (L1, L3 as amended) |
| 4 | I-8 sections every 50 m: floor ±1 m, rims at ±60 m ±2 m of the 2 m 3DEP section, vertices within 12 m, fills stand up | 132 of 179 sections had no vertex within 12 m | **162 of 171** (the truth lens's centreline; 152 before the fix round). Floor error median 0.034 m, p95 0.37 m (was 1.23). Every section has vertices within 12 m. All six 3DEP-confirmed fills (s 7100–7900, rises 2.3–6.4 m) are built within 0.58 m. On the implementer's corridor (179 sections): 0 floors off by > 1 m, 7 rims off by > 2 m, the s 8250 fill 5.05 m against 5.11 | FAIL on 9. **7** sit on or beside a pavement, where criterion 7 holds the ground to v0.17.1: s 1700's centre is under the College Ave deck (the v0.17.1 approach grass at the deck, 109.0 m, over a 104.0 m floor); s 1800–1950's north rims are 1–10 m from Alvarado's pavement; s 3700 is on Lake Murray Blvd; s 3750's south rim is 20 m from it. **2** are away from roads: s 750 (3DEP steps 4 m within 2 m) and s 7250 (a 2–4 m-wide median hump; the vertex on it matches 3DEP to 0.01 m) — features narrower than the 5 m cells. Neither kind is a build defect; the first is criterion 4 against criterion 7, the second the cell size |
| 5 | facet longest edge 15–60 m from a road, p90 ≤ 7 m | 28.6 m | **5.27 m** (median 5.0; 0.07 % over 7 m), measured to `1ROAD` and to all pavement alike (was 9.02 / 5.68) | PASS |
| 5 | 60–500 m, p90 ≤ 28.3 m | 28.9 m (60–220); 921 m (220–500) | **20.2 m** (60–500); 20.5 m (220–500) | PASS |
| 6 | far ring within 1 m of 3DEP | — | 3,000 random far vertices against fresh 3DEP: max **0.005 m** | PASS (between vertices, linear over 40 m cells: p95 1.5 m, max 17.8 m on the steepest slopes) |
| 6 | no far horizontal edge longer than two of its own cells | — | longest 56.65 m (a 40 m cell's diagonal; two cells = 80 m) | PASS |
| 7 | gates unchanged | street soft-top 42 / severe 0 / kinks 3.86 /km / bumps 0.15 /km / excursions 100 / floating 391 / obstruction 0 / daylight 0, replication p95 0.42; audit D 512 K 20 I 20 F 13 (565); race_cw / race_acw severe 31 / 28, audit 53 each, no_route PASS, barrier_missing 0 | **identical, field for field** (only `grass_verts` 87,278 → 335,165 and no_route timing differ); verify_mouths PASS × 4 with identical numbers; verify_kn5 + `--inis` OK; verify_signs PASS; check_race_kn5 OK | PASS |
| 7 | `1GRASS` within 20 m of a road vs v0.17.1 | — | 118,319 vertices, 3D distance to the v0.17.1 surface **0.000 m** (max). A vertical ray reads 42 of them > 0.05 m, all within 3 m of the College Ave bridge over I-8, where two grass layers stack (v0.17.1's own) | PASS |
| 7 | the tiles | `1GRASS` × 2 | `1GRASS` × 8 (max 42,411 v), `GRASS_FAR` × 2 (max 53,414 v); no far mesh with a digit prefix; `GRASS_MESHES` = `1GRASS_0..7` only; `OCCLUDING_MESHES` unchanged; all 244 `[LIGHT_*]` sections and `trees.txt` byte-identical | PASS |

**The budget, honestly.** The ledger estimated ~131k terrain vertices and +~3 MB of kn5. Built: physical `1GRASS`
**335,165** vertices (8 tiles, ~670k triangles) + `GRASS_FAR` 106,557 (2 tiles), against 87,278 in v0.17.1. The road
kn5 went **92.5 → 112.6 MB (+20.1 MB)**. Where it goes: the 5 m tier (x-split: criterion 5's 7 m is under a plain 5 m
cell's 7.1 m diagonal, so every 5 m cell carries a centre vertex) within 60 m of every pavement, the 5 m I-8 corridor,
the prep's own corridor subdivision near the road (as it always did), and the fix round's refinement of the kept cells'
outer half (+~98k: the same density as the 5 m tier around them). The masters ship more terrain: Mulholland's
`la_terrain_background.kn5` is 466,903 vertices in 35 meshes, PCH's `terrain.kn5` 934,769 in 43, at 13–22k per mesh;
ours are 42k per physical tile. **GrassFX at session load.** The v0.12.x freeze came from a far backdrop enrolled as an
occluder; that cannot happen here (`GRASS_FAR` is in no list; the occluders are unchanged). `GRASS_MESHES` grows from 2
meshes / 171k triangles to 8 / ~670k over a smaller bounding volume (the skirt is gone). There is no in-game
frame-time measurement on this machine: criterion 8's "frame rate no worse" is Kevin's, and it is the first thing to
check from the seat.

**What the stills show** (Workbench, backface culling on as in AC, each mesh coloured by its kn5 texture's mean; before
= the v0.17.1 gate OBJ, after = ship9's): from the crest facing 046° Cowles stands on the skyline with its shoulder
ridges where v0.17.1 had a flat green floor; facing 192° the houses across the street fill the frame in both builds
(Del Cerro is 1.2–1.4° above the eye behind them; the valley wall is below the eye and behind Del Cerro, as in the
world). From `seam-alvarado` the I-8 is 108 m north behind the verge in both builds — in the world too — so the cut is
shown from the College Ave and Lake Murray Blvd decks (3 m up, over the rail) and from 120 m above: past 20 m of the
roads the corridor's walls and the far cuts are now the 3DEP's, and it reads as a valley; with no I-8 pavement (Kevin's
call) the two overcrossings stand over grass. Remaining, measured and not fixed here: the material seam where green
`1GRASS` meets the chaparral far ring 250 m out (now close in tone: mean 68/92/40 against 93/93/66, was 139/132/122);
Alvarado Creek near College aliased by the 5 m cells into a saw-toothed ditch; the far box's own edge on the horizon
facing 225–000° (smaller than v0.17.1's void); 7 non-manifold edges in `1GRASS`, the same 7 v0.17.1 has, within the
near-road ground criterion 7 holds.

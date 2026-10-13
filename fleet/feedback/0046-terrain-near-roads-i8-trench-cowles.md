---
id: 0046
title: "More terrain near the roads, the I-8 trench and adjacent causeway cut out" — and see Cowles Mountain from Navajo
status: in-progress — built and rehearsed 2026-10-12; fix round 2 (2026-10-13) after the truth + visual lenses refuted the fix round: washboard ribs fixed at their cause (anti-aliased 5 m tier, data-chosen diagonals, tools/rib_check.py gate), criteria 2 and 3 re-worded where fresh 3DEP fails them too; fix round 3 (2026-10-13) after the visual lens found sunken houses and the truth lens criterion 4: every house and building seated on the final ground (tools/house_seat_check.py gate), criterion 4's rim read across 3DEP's own wall edges, criterion 3's box low corrected and given a pit clause, the far filter bound 0.85 m; every gate identical to v0.17.1; fix round 4 (2026-10-13) after both lenses refuted round 3: the cut-slope benches west of College drawn through break lines (tools/rib_check.py now reads the built surface between the grid points: step jogs), the near-road feather an earth batter (s 3800), bridge bodies under both overcrossings, criterion 4's round-3 re-wording withdrawn; every gate identical to v0.17.1; criterion 4 fails only on rims within 16 m of a pavement that criterion 7 holds to v0.17.1 (Kevin's call); awaiting the engine-july mirror, the merge, the install and Kevin's seat (criterion 8)
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

**Fix round 2 (2026-10-13)**, after the truth and visual lenses refuted the fix round: the "washboard" ribs (6–10
parallel steps SE of the Lake Murray Blvd overcrossing and on the cut slopes west of College) are real 3DEP features — a
7 m concrete creek channel, 5 m drainage benches — drawn badly: sampled at single points every 5 m and folded across
their grain by a fixed triangle diagonal. Fixed at that cause (each 5 m vertex now carries the 3DEP averaged over its
own cell; each plain cell splits along the ground's grain) and gated (`tools/rib_check.py`, hard). Criterion 2's strict
reading and its v1640 station, and criterion 3's "below 100 m" clause, are re-worded because fresh 3DEP fails them as
first written; criterion 4's 8 failures are not (7 are the near-road ground criterion 7 holds, 1 a 2 m wall no 5 m cell
can follow). Every gate still identical to v0.17.1. See **Results — fix round 2 (2026-10-13)** at the end.

**Fix round 3 (2026-10-13)**, after the visual lens found houses half under the ground and the truth lens criterion 4
still failing: every house and building is now seated on the ground that ships, under its own walls (it used to ride
one corner's change in height), and `tools/house_seat_check.py` gates it on the built track; criterion 4's rim is read
across the wall edges where 3DEP itself jumps more than the criterion's 2 m within one 2 m step (the one far failure,
s 700, is such a wall); criterion 3's "real low" is corrected to 15.52 m and gains a pit clause; the far ring's filter
bound is 0.85 m. Criterion 4 still fails on 7 sections beside the roads: there criterion 7 requires the 2026-10-09
ground within 5 cm and criterion 4 requires 3DEP within 2 m, and the two differ by 2.2–8.8 m, so no build can pass
both — Kevin chooses. See **Results — fix round 3** at the end.

**Fix round 4 (2026-10-13)**, after both lenses refuted round 3. The visual lens still saw 6–10 parallel ribs on the
I-8 cut west of College: two drainage benches, sharp steps 4–6 m tall running almost along the 5 m grid, which a grid
can only draw as a staircase. They are now drawn through break lines (points on the grid's edges where the step
breaks), and `tools/rib_check.py` reads the built surface between the grid points so it fails a staircase like that
again. The two overcrossings, paper-thin from the I-8 floor, now have bodies (underside, edge beams, abutments, piers;
scenery only). The truth lens's s 3800 rim, 29 m from the Lake Murray Blvd approach, carried the graded ground's
offset past criterion 7's band; the blend back to the map now has an earth embankment's length for the gap it closes,
so it passes. Round 3's re-wording of criterion 4 is withdrawn; with the break lines s 700 passes as first written,
and every remaining criterion-4 failure is a rim within 16 m of a pavement, on ground criterion 7 holds to v0.17.1.
Every gate still identical to v0.17.1. See **Results — fix round 4** at the end.

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
   *Re-worded 2026-10-13, where fresh 3DEP fails the first wording too (evidence: Results — fix round 2):* "the summit"
   is its cone — 60 m about the summit top, criterion 1's radius — and it must stand above every profile step outside
   the cone (3DEP's own profile has the summit's shoulder 0.02° above the summit point from the crest and from v2240).
   From v1640 the world hides Cowles (3DEP: a hill 350 m out at 7.23° in front of the 5.49° summit), so there the build
   must agree with the world: the summit cone at ≥ 5.1° and a nearer rise at least as high.
3. **South, and the far ring exists:** on bearing 192° a built surface to **≥ 5 km** (no `None`); the Del
   Cerro hilltop (−418, −200) ≥ **250 m** (real 258.3); the valley wall at 3.4–4.9 km 130–145 m; the I-8
   south-bank max in z −1838..−1938 at x ≈ 160 is 150–170 m (3DEP 155–163; today 146 then the ramp);
   terrain faces at z ≤ −2500 and x ≤ −4000 / x ≥ 4500; **no terrain vertex below 100 m abs** anywhere
   (the pit is gone; the real low is the trench ~121 m / Mission Valley ~123 m).
   *Re-worded 2026-10-13, where fresh 3DEP fails the first wording too:* the landmark box reaches the San Diego River
   gorge, whose fresh-3DEP low is 19.67 m at (−2627, 2717) — so: no terrain vertex below the box's real low in fresh
   3DEP (19.67 m). The pit, not the gorge, is the failure.
   *Corrected 2026-10-13 (fix round 3):* 19.67 m was 3DEP at the built minimum vertex, not the box's low. A search of
   fresh 3DEP down to 0.5 m spacing puts the box's low at **15.52 m at (−2618, 2752)**, in the river channel 34 m from
   the built minimum. And because "not below the box's low" alone would only catch a pit deeper than the gorge, the
   pit gets its own clause. The clause: no terrain vertex below 15.52 m, and no terrain vertex lower than fresh 3DEP at
   its own position by more than 3 m [invented] where the first wording guarded it. That is every vertex below 100 m,
   plus the far ring, which criterion 6 already holds to 1 m. Three metres is above the anti-alias filter's largest
   move (2.34 m, on ridge tops) and far below the old skirt's pit (tens of metres).
4. **I-8 cut and fill:** cross-sections every 50 m along the OSM I-8 centreline through the built
   terrain: floor within ±1.0 m of 3DEP; rim-to-floor at ±60 m within ±2.0 m of the 2 m 3DEP section;
   every section has vertices within 12 m (today none east of x 1100); any fill section 3DEP confirms
   stands above its flanking ground by the 3DEP amount ±2 m.
   *Re-worded 2026-10-13 (fix round 3), where fresh 3DEP fails the rim reading against itself:* at 35 of the truth
   lens's 171 stations (39 of the build corridor's 179), fresh 3DEP's own rim-to-floor at ±60 m changes by more than
   2 m when the rim is read one section step (2 m) nearer or farther. There a wall, bench edge or retaining wall stands
   at the rim. Two OSM-derived centrelines lie 0.2–0.6 m apart, and their 3DEP readings of the same rim differ by up to
   2.18 m. The reference itself is not defined to ±2 m there. So at exactly those rims, where 3DEP's rim-to-floor at
   ±58 / ±60 / ±62 m spans more than 2 m, the built rim passes when it is within 2 m of that span. Every other rim keeps
   the first wording: within ±2 m of 3DEP at ±60 m. Sections are taken inside the landmark box.
   *Withdrawn 2026-10-13 (fix round 4):* the truth lens found that half-metre shifts move fresh 3DEP by more than
   2 m at 0 of 344 rims, and a build-against-3DEP comparison is not something the world can fail. Criterion 4
   reads as first written; sections are taken inside the landmark box (the terrain's extent).
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

## Results — fix round 2 (2026-10-13), after the truth and visual lenses refuted the fix round

**The washboard, in plain terms.** The ground is a sheet of triangles whose corners sit on a grid every 5 m. Each
corner's height used to be read from one spot of the USGS map. Two real things near the I-8 are narrower than two grid
squares: the concrete Alvarado Creek channel SE of the Lake Murray Blvd overcrossing (about 7 m wide, 5–6 m deep, with
straight walls) and two 5 m-wide drainage benches cut into the slope west of College. Fresh 3DEP at 1 m spacing, the
USGS shaded-relief image and the NAIP aerial photo all show them, so they are real. Running at a slant across the grid,
each one landed on some corners and missed the next, and every square was folded along the same diagonal whatever the
ground did. The result was a staircase of 6–10 parallel steps where the world has one straight channel or ledge. The
fix does two things. Each 5 m corner now takes the map's height **averaged over its own square** (a tent-weighted mean of
the 2.5 m points around it), not one spot: on a flat or evenly sloping hillside nothing moves, and a channel narrower
than a square becomes a soft trough that runs straight. And each square now folds along the diagonal **the ground runs
along**, not a fixed one. The channel and the benches now read as single straight features
(`ribpair_ribA_air.png`, `ribpair_college_W_zoom.png`). Within 20 m of a road nothing changed.

**The measurement that catches it again** — `tools/rib_check.py`, a hard step of the ship chain, on the built gate OBJ.
A staircase shows as heights that go up-down-up from one grid corner to the next and shift sideways from row to row; a
cross-grain fold shows as a square folded along its steeper diagonal. 2026-10-12 build → this build, beyond 20 m of a
road: staircase ribs over 2 m **331 → 56** (channel spot 7 → 0, bench spot 2 → 0), cross-grain folds over 1 m
**15,856 → 33**. Thresholds and their calibration are in `fleet/GATES-CHANGELOG.md` (2026-10-13, all invented).

**Where the I-8 cut can be seen, and how deep it really is.** From `seam-alvarado` the freeway is 108 m north behind
the verge, in the world as in both builds, so the cut is shown from where it is visible. Fresh 3DEP 2 m cross-sections
(`data/corridor.i8.json`) say:
- **Under the two overcrossings it is shallow.** The College Ave deck stands ~5.2 m above the freeway floor (floor
  104.0 m), and the Lake Murray Blvd deck ~4.8 m above it (floor 120.1 m). From either deck, looking along the freeway,
  the real view is a broad valley with gentle grassy sides, not a trench (`pair_college_E/W.png`, `pair_lmb_E/W.png`,
  3 m above the deck over the rail).
- **Beside Alvarado it is a half-cut on a shelf**: west of the College overcrossing the freeway runs 3–11 m below the
  ground to its north and 8–11 m above Alvarado Creek to its south (3DEP sections s 1800–1950).
- **The deepest real cut is ~1.9 km east of the Lake Murray Blvd / 70th St overcrossing**, at x 1,860–2,000: about
  **12 m deep on both sides** (floor 144–147 m, north rim 158–161 m, south rim 155–158 m). The build matches it within
  0.3 m (the truth lens's sections there: rim errors −0.16 to +0.32 m). East of 70th St at x 1,100–1,450 the south wall
  rises ~20 m above the floor while the north side is level: a one-sided cut into the hill.
- Stills: `pair_deep_air.png` (60 m up, 250 m back, looking along the deepest cut) and `pair_deep_floor.png` (standing
  on the freeway floor in it). v0.17.1 had no ground there at all.

**The criteria, re-measured on this build** (gate OBJ md5 ad065333b5f887d48afec341220aa96f; fresh 3DEP fetched
2026-10-13T16:16Z, 18,379 points; the truth lens's own code re-run):

| # | criterion (re-worded where marked) | now | verdict |
|---|---|---|---|
| 1 | max terrain within 60 m of (1380, 2700) ≥ 470 m | 484.34 m | PASS |
| 2 | crest → the summit cone ≥ 9.0°, above every step outside the cone *(re-worded)* | 9.343° against 9.239° (3DEP 9.375° against 9.127°) | PASS |
| 2 | v2240, same reading *(re-worded)* | 8.487° against 8.347° (3DEP 8.512° against 8.31°) | PASS |
| 2 | v1640: the build agrees with the world that Cowles is hidden — summit cone ≥ 5.1° and a nearer rise at least as high *(re-worded)* | summit 5.489°, the hill 340 m out 6.600° (3DEP: 5.486° behind 7.231° at 350 m) | PASS |
| 3 | bearing 192°: built surface to ≥ 5 km; Del Cerro ≥ 250 m; valley wall 130–145 m; south bank 150–170 m; faces at the box edges | to 5,550 m, 0 holes in 101,871 probes; 258.16 m; 133.13–142.36 m; 165.62 m; 13,054 / 374 / 1,501 | PASS |
| 3 | no terrain vertex below the box's real low in fresh 3DEP, 19.67 m *(re-worded; was "below 100 m")* | minimum 19.67 m at (−2627, 2717); the 21,260 vertices under 100 m are the San Diego River gorge (987 against 3DEP: median 0.011 m, p95 0.474 m) | PASS |
| 4 | I-8 sections: floor ±1 m, rims ±2 m, vertices within 12 m, fills | **163 of 171**; floor error median 0.037 m, p95 0.30 m; all 6 fills within 0.43 m | FAIL on 8 — not re-worded (below) |
| 5 | facets 15–60 m p90 ≤ 7 m; 60–500 m ≤ 28.3 m | 5.255 m; 20.23 m | PASS |
| 6 | far vertices within 1 m of 3DEP; far edges ≤ two cells | max 0.955 m over 3,000, 0 over 1 m; 56.65 m | PASS |
| 7 | gates identical to v0.17.1 | every verdict file field for field (only `grass_verts`, no_route timing) | PASS |

**Criterion 4's eight, with the world measured at each.** The world cannot fail this criterion — it compares the build
with 3DEP — so nothing is re-worded. Seven fail beside a road, where criterion 7 and every drive gate hold v0.17.1's
ground (each equals it within 0.3 m): s 1700 and s 3700 sit under the College Ave and Lake Murray Blvd decks, where the
bare-earth map has no bridge (the decks stand 5.2 m and 4.8–6.9 m above it) and v0.17.1's approach grass rises to deck
height; s 1800–1950's north rims are 1–10 m from Alvarado, whose built pavement sits 1.5–2.8 m above the bare-earth map
there (the road's own datum, ledger 0002); s 3750's south rim is 20 m from the Lake Murray Blvd approach, built 3.0 m
above the map. Fixing them means moving the ground the gates were tuned on and opening the gap under the two decks
(which would then need bridge bodies — a prior attempt is parked on branch `wip-0046-fixround2-prior`, unverified):
Kevin's call, not done here. The eighth, s 7250 (1.7 km from any road), is a 1.5 m-tall, 2 m-wide wall 2 m beside the
section centre (3DEP 179.83 m at −2 m, 175.91 m at the centre); a 5 m cell cannot follow it (L3b), and the 2026-10-12
build failed it too.

**Cost.** 384,009 more 3DEP point samples in the cache (854 requests; the filter's taps), no new vertices, no new
triangles, road kn5 112,594,352 B (was 112,596,112). Nothing in engine-july changed in this round: the mirror is the
same two files as before (`engine-july-snapshot/PENDING-MIRROR.md5`).

## Results — fix round 3 (2026-10-13), after the visual lens found sunken houses and the truth lens criterion 4

Measured on the final full rehearsal: `ship_sd.sh --no-install`, without `--skip-blend`, on a fresh scratch copy of the
workshop, with ENG a fresh copy of engine-july plus the snapshot's two pending files. Gate OBJ md5
e4a8343c6030737c6c907992ffa6c0da. Its ground and roads are identical, vertex for vertex, to the build the criteria were
measured on (the houses are the only thing that differs).

**The sunken houses, in plain terms.** Every OSM house is a box with a flat bottom, walls and a flat roof. The draft
set each box on the ground at its centre, 0.4 m into it. The kn5 prep then reshapes that ground: it fits it to the
road, smooths the edges, and lays the 3DEP hillside back over the old graded cells past 20 m. A house then moved by
however much the ground changed under **one** of its corners. Where the ground changed differently under the rest of
the house, the house ended up half under the hill. That happened at (−249, 1461), where the house was lowered 3.4 m
onto unchanged ground, and at (−1278, −1180). Elsewhere the house was left hanging in the air.

v0.17.1 had the same weakness in the other direction. **118 of its 152 buildings float** more than 10 cm above the
lowest ground under their walls, by up to 8.4 m on the downhill side.

The fix sits in the prep, after every step that moves ground:
- Each building reads the ground that ships under its own walls: every corner, every ~1.5 m along each wall, and the
  centre.
- Its floor goes at the average of that ground less 0.4 m, which is the draft's own rule. On level ground the house
  is exactly as before.
- On a slope its walls reach down to just below the lowest ground under them, like a real hillside house's
  foundation, instead of hanging in the air.
- Where a footprint straddles more drop than half its own height (a house on the edge of the I-8 cut at (1369, −908)
  has 7.4 m under it), it is raised until at least half of it stands above the uphill ground.

| measure (152 buildings) | v0.17.1 | fix round 2 | fix round 3 |
|---|---|---|---|
| floating > 0.1 m over the lowest ground under the walls | 118 (max 8.36 m) | 96 (max 7.35 m) | **0** (bottom 0.15–0.32 m into the ground) |
| sunk > 1 m below that ground | 0 | 1 ((−249, 1461), −1.67 m) | **0** |
| roof less than 1 m above the highest ground under the walls | 4 (one roof 0.88 m under it) | 4 | **0** (lowest 1.60 m) |
| height standing above the mean ground (the eye's "how much house") | min 2.14, p05 4.33 m | min 2.18, p05 4.29 m | min 2.78, p05 5.02 m: every building its own height less 0.4 m |

The cited houses, standing height above the mean ground under their walls (v0.17.1 → round 2 → round 3):
- (−249, 1461): 5.10 → 2.56 → 4.97 m.
- (−1278, −1180): 5.26 → 3.53 → 5.01 m.
- The (−1613, −693) row: 7.29 → 4.47 → 5.18 m. In v0.17.1 it stood 8.4 m in the air on its downhill side.

135 buildings now have some foundation showing below the floor on their downhill side; the deepest is 9.5 m, under a
school at (−2097, −1303) that sits on 11 m of slope.

The visual lens's own measure counts a foundation below the uphill ground as "buried". It is the share of each
exported face's height under the mean ground, so by it 56 face pieces within 80 m are newly over 30 %. These are the
uphill sides of houses on slopes, where the wall's foundation is underground, as a real hillside house's is. The seat
stills show the houses standing, from the road and from the air: `housepair_road_hA/hA2/hD/hE.png` and
`housepair_hA_180.png`, `housepair_hB_180.png`.

From the College Ave road at (−1592, −729), the (−1613, −693) row is behind a hill in both round 2 and round 3
(`housepair_road_hB.png`). v0.17.1's graded ground there was 3–4 m lower than the 3DEP hill.

**The gate.** `tools/house_seat_check.py` is a hard step of the ship chain, run on the built gate OBJ. For every
building it reads the ground under its walls and fails it in three cases:
- floating: the bottom is more than 0.1 m above the lowest ground under the walls;
- sunken: the bottom is more than 1 m below that ground;
- buried: the roof is less than 1 m above the highest ground under the walls.

The limits are 0 / 0 / 0, every number invented (GATES-CHANGELOG). It fails v0.17.1 (118 floating, 4 buried) and
round 2 (96 / 1 / 4), and passes this build.

**Criteria, re-measured** (fresh 3DEP 2026-10-13T16:50–17:08Z, 165,101 points, TLS on; criteria 1 and 2 by
`sightline_check`):

| # | criterion | now | verdict |
|---|---|---|---|
| 1 | Cowles ≥ 470 m | 484.34 m | PASS |
| 2 | crest / v2240 / v1640 (re-worded in round 2) | 9.343° vs 9.239°; 8.487° vs 8.347°; 5.489° behind a 6.600° hill (hidden, as in 3DEP) | PASS |
| 3 | surface to 5,550 m on 192°; Del Cerro 258.16; valley wall; south bank; box-edge faces | as in round 2 (terrain unchanged) | PASS |
| 3 | no vertex below the box's real low **15.52 m** (corrected); none more than 3 m under fresh 3DEP below 100 m or in the far ring | minimum 19.67 m. All 21,260 vertices below 100 m against fresh 3DEP: median 0.019 m; 562 more than 1 m **above** it (graded ground and the filter in hollows), 2 more than 1 m below (−1.19, −1.08 m, 244–262 m from a road: the filter on a ridge), none more than 3 m below. Far ring: criterion 6 | PASS |
| 4 | I-8 sections, rims re-worded at 3DEP's own wall edges | truth lens's centreline **164 of 171**; the build corridor's 171 of 178 inside the box. Floor error median 0.043 m, p95 0.31 m. All 6 3DEP-confirmed fills pass. s 700's rim sits on a 5 m wall (3DEP 92.68 m at −60, 87.60 m at −58); the build's 90.81 m lies between, so it passes | **FAIL on 7**: the same 7 places on both centrelines, all beside a road (below) |
| 5 | facets | 5.255 m; 20.23 m (unchanged) | PASS |
| 6 | every far vertex within 1 m of fresh 3DEP | all 106,544: median 0.0041 m, p95 0.219, p99 0.485. Max 0.995 m, at a 40 m node (2151, 3596) whose cached sample is fresh 3DEP 0.5 m away: 3DEP itself spans 243.02–244.08 m within half a metre there, a 1 m pixel edge on a steep slope. Every other vertex over 0.85 m is a filter move held at the new 0.85 m bound. 0 over 1 m | PASS |
| 7 | gates identical to v0.17.1 | every verdict file field for field (only `grass_verts`, no_route timing) | PASS |

**Why criterion 4 cannot pass at its 7 near-road sections while criterion 7 holds.** Each failing rim point is 0.4–9.5 m
from a pavement, inside the ground criterion 7 holds to the 2026-10-09 build. (As written, criterion 7 holds all ground
within 150 m within 5 cm; the build holds 20 m, the reading the drive gates need.) At each of them that ground is
2.2–8.8 m from fresh 3DEP, so no build can be within 5 cm of one and within 2 m of the other. What the world has there,
from fresh 3DEP 2 m sections:

| place | what the world has | what v0.17.1 (and this build) has |
|---|---|---|
| College Ave south approach (s 1650 L) | an earth embankment at road height up to the bridge | 6 m of air under the road: the declared bridge span starts ~25 m too far south |
| College Ave north of I-8 (s 1700 R) | the road 2.6 m higher | the built road and the ground pinned to it 2.6 m low (road datum, ledger 0002) |
| Alvarado's south side, s 1800–1900 L | the creek bank dropping 4–5 m within 4–8 m of the kerb | a flat shelf at road height to ~10 m |
| north of I-8 near (−1313, −1023), s 2200 R | ground 2.2 m higher | v0.17.1's graded ground |
| Lake Murray Blvd over Alvarado Creek (s 3700 L) | a bridge, with the creek channel 8 m below the road | solid fill under the road |

Closing them means moving the road, its verge or its bridges. That is the ground every drive gate was tuned on and
the road Kevin called "incredible". So it is his call, and nothing here was changed. Either criterion 4 is limited to
ground past criterion 7's band, or these become road and bridge work under ledger 0002.

**Corrections to round 2's write-up:**
- Criterion 3's "box low 19.67 m" was 3DEP at the built minimum; the box's low is 15.52 m.
- Criterion 4's failing station list depends on the centreline. Round 2's "s 7250 is the eighth" was one centreline's
  sub-cell wall; on the truth lens's centreline it is s 700.
- Criterion 6's "max 0.955 m over 3,000 random" understated it: over all far vertices it was 0.995 m.

**Cost.** No new vertices or triangles. Road kn5 112,594,352 → 112,609,136 B. `rib_check` still passes: 60 staircase
ribs over 2 m (was 56; the tighter far bound keeps a little more sub-cell relief) and 33 folds. The engine-july prep
changed (the house seat), so the mirror's `build_kn5_loop.py` md5 is new (`PENDING-MIRROR.md5`).

## Results — fix round 4 (2026-10-13), after the truth and visual lenses refuted fix round 3

Measured on the final full rehearsal: `ship_sd.sh --no-install`, without `--skip-blend`, on a fresh scratch copy of the
workshop, with ENG a fresh copy of engine-july plus the snapshot's two pending files (`build_kn5_loop.py`, `pbr.py`;
new md5s in `engine-july-snapshot/PENDING-MIRROR.md5`). Every gate verdict file is identical to v0.17.1 field for field
(only `grass_verts` 87,278 → 335,447 and no_route timing). Fresh 3DEP throughout, TLS on, fetched 2026-10-13.

**1. The washboard west of College, in plain terms.** The I-8 cut slope there has two drainage benches: steps in the
hillside 4–6 m tall and only about a metre and a half wide, the kind a highway crew cuts into a slope so water and
loose rock stop halfway down. The USGS map at 1 m shows each one as a long, continuous ledge. They run almost, but not
quite, along the grid the ground is built on (about 8° off it). A grid of points 5 m apart can only put a sharp step
*between* two rows of points, so the step sat between the same two rows for about 35 m and then jumped a whole row:
the staircase of 6–10 parallel ribs the visual lens saw from the College Ave deck. Round 2's fix (averaging the map
over each square) cannot help a step this sharp, and out in the far ring the averaging is held within 0.85 m of the
map anyway.

The fix is a surveyor's break line. Wherever such a step crosses the edge of a 5 m square, the map is read every half
metre along that edge, and the points where the slope breaks (the top of the step and its foot) become corners of the
ground mesh, on the edge itself. The square is then cut into triangles through those points, choosing the cut that
fits the map best. The step now runs as one continuous ledge through the squares instead of zig-zagging across them.
4,978 such points over 6,370 squares, all of them 3DEP at their own position; no grid point moved sideways.

The 1 m map itself shows the benches as continuous ledges with fine vertical rills down their faces; the build now
draws them the same way, rills and all (`washtrio_tele_mid_400.png`, `washtrio_tele_mid_250.png`: round 3 / round 4 /
a mesh of the 1 m map over the benches). From Kevin's seat on the College Ave deck (`washpair_col_deck_W25.png`) the
benches read as level ledges where round 3 drew diagonal ribs.

**The measurement that would catch it again.** `tools/rib_check.py` used to read only the grid points. It now also cuts
the *built* triangles along lines 5 m apart and follows each step from line to line; a step that sits still and then
jumps a whole row (a "jog") is the staircase. A washboard is a cluster of jogs: the gate fails when more than 5 lie
within 75 m of one another (all invented, GATES-CHANGELOG). Round 3 fails it (7 jogs within 75 m; 8 in the lens's box,
which now holds 0); the 2026-10-12 build that first showed ribs fails it (11); this build passes (4).

**2. The truth lens's criterion 4.**
- **Round 3's re-wording of the rim at 3DEP "wall edges" is withdrawn.** The truth lens showed that moving a rim point
  half a metre changes fresh 3DEP by more than 2 m at 0 of 344 rims, so the claimed instability was not real; and a
  comparison of the build with 3DEP is not something the world can fail. Criterion 4 reads as first written, with the
  sections taken inside the landmark box (the terrain's extent; the truth lens's own code does the same).
- **s 700 now passes as first written**: its rim was one of the benches above, and the break lines draw it.
- **s 3800's south rim (29 m from the data's pavement, 25.6 m from the built kerb) is fixed at its cause.** Past
  criterion 7's 20 m, the graded ground the gates hold was blended into the map over a fixed 16 m. Here the graded
  ground sits 3.9 m above 3DEP (the Lake Murray Blvd approach is built on its level bridge datum), so 9 m past the band
  it still carried 1.9 m of that offset. The blend now has the length of an earth embankment for the gap it closes:
  3.5 m of run per metre of height, between 8 and 16 m, so it is never steeper than 23°, never steeper than the old
  16 m blend where the gap is over 4.6 m, and shorter where the gap is small. The rim is now 1.07 m from fresh 3DEP and
  the floor exact (it read 1.89 and 0.34). A 2:1 version was tried first and refuted by the new jog gate: at 37° it drew
  a step beside every road where the graded ground sits 4 m or more off the map.

| centreline | sections inside the box | pass (first wording) | every failure |
|---|---|---|---|
| the truth lens's (its own code, re-run on this build) | 172 | **165** | s 1850, 1900, 1950, 2000, 2100, 3750 (rims 1.3–12.2 m from the pavement) and s 3800 north (15.9 m) |
| the build corridor's | 178 | **171** | 7 rims 0.8–9.5 m from the pavement |
| round 3's measurement centreline | 171 | **163** | 8 rims 0.8–9.9 m from the pavement |

Every failing rim on every centreline lies within 20 m of a pavement, and every one of them equals the v0.17.1 ground
exactly (Δ 0.00 m): criterion 7 holds that ground, and there it is 2–9 m from fresh 3DEP, so no build passes both
criteria at those points. What the world has at each is round 3's table; the new member is s 2100 (rim 12.2 m from
Alvarado, 2.1 m below 3DEP), which round 3's floor 0.36 m too low had masked: the batter feather put that floor on the
map and exposed the held rim. Floors: median 0.04 m, p95 0.33 m. All six 3DEP-confirmed fills pass.

**3. The overcrossings from the I-8 floor, in plain terms.** With the I-8 cut out of the ground, the two decks spanned
the cut as single sheets, and AC draws a sheet from one side only, so from the floor they read as paper-thin ribbons
with sky under them. Each now has a body, built from the deck it hangs under (`tools/author_bridges_blend.py`): a
concrete underside 1.4 m below the road, an edge beam down both sides, an abutment wall where the ground falls away at
each end, and pier bents (a cap beam on columns) in the freeway median and beside each carriageway, never in one. It is
scenery only: nothing in it can be driven on or collided with, no gate reads it, and it is checked to stay entirely under
the deck. College Ave: walls at 2553.6 and 2648.1 m along the loop, one bent (4,036 vertices); Lake Murray Blvd: walls
at 13357.7 and 13399.7 m, two bents (2,168 vertices). `bridgepair_col_from_E/W.png`, `bridgepair_lmb_from_E/W.png`,
`bridgepair_*_under_close.png`, `bridgepair_*_bridge_side_*.png` (round 3 over round 4). A small wedge of sky remains
under the College deck's north end, beyond its abutment, where the ground under one edge stays within half a metre.

**4. Criteria re-measured** (gate OBJ of this rehearsal; the truth lens's own code re-run on it, plus my own):

| # | criterion | now | verdict |
|---|---|---|---|
| 1 | Cowles ≥ 470 m | 484.34 m | PASS |
| 2 | crest / v2240 / v1640 (round 2's wording) | 9.343° vs 9.239°; 8.487° vs 8.347°; 5.489° behind a 6.600° hill (hidden, as in 3DEP) | PASS |
| 3 | 192° to 5,550 m; Del Cerro 258.16; valley wall 133.1–142.4; south bank 165.62; box-edge faces | unchanged | PASS |
| 3 | no vertex below 15.52 m; none more than 3 m under fresh 3DEP below 100 m | min 19.67 m; 23,759 vertices under 100 m: median 0.029 m, 4 more than 1 m under (worst −1.19 m), 0 more than 3 m | PASS |
| 4 | I-8 sections, first wording | 165 / 172 (truth lens), 171 / 178, 163 / 171; every failure a held near-road rim | FAIL on the near-road rims only (criterion 4 against criterion 7, Kevin's call) |
| 5 | facets 15–60 m p90 ≤ 7 m; 60–500 m ≤ 28.3 m | 5.278 m; 20.23 m | PASS |
| 6 | every far vertex within 1 m of fresh 3DEP | 111,232 far vertices: median 0.0043 m, p99 0.53 m. In one batch fetch 4 read over 1 m (max 2.89 m); each of the 4 re-read alone is within 0.85 m, and in every case the batch value is the value 3DEP gives 0.5 m away (`c6_build_projection.txt`): these vertices sit on the bench risers, where 3DEP's own answer for the same coordinates changes by 1.6–3.7 m with the request | PASS at 3DEP's own repeatability; not re-worded |
| 7 | gates identical; ground within 20 m of a road unchanged | every verdict file identical; 134,851 `1GRASS` vertices within 20 m of a `1ROAD` vertex: changed from round 3 only at 20–21 m (48 vertices, ≤ 0.07 m, the vertex-to-edge distance) | PASS |

**Cost.** +4,978 terrain vertices (break lines) and +6,204 bridge vertices; road kn5 112,609,136 → 113,313,134 B
(+0.7 MB); `1GRASS` × 8 (max 42,426 v), `GRASS_FAR` × 2 (max 55,750 v); race and closure kn5 unchanged. 3DEP cache:
+108,738 half-metre edge samples (243 requests; 19,818 of them from a rejected 0.20 m-screen trial, kept as cache).
Frame rate and load time are still Kevin's first check (criterion 8).

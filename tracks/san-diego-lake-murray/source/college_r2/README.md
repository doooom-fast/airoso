# College Ave "realism+": the real road against the built one (round 2, step 1)

Kevin (ledger 0055): "can you split them up and do something fun? i would prefer realism+". This folder is proof step 2
of that ledger: the real carriageways' heights, registered in the engine frame, beside the road as built. No geometry
is authored here and nothing in the shared config changes.

## What is here

| File | What |
|---|---|
| `college_xsec.lidar.g10.json` | measured: USGS CA_SanDiegoCo_D24 (2024) lidar, class 2, at every centreline vertex v800-1560, offsets -30..+30 m every 0.5 m (read by the G10, nothing downloaded on the PC; `job1_report.g10.json` has the tiles and md5s) |
| `j1_waring.lidar.g10.json` | measured: the J1 crossroads on a 1 m grid, Waring sections s 0-200 m, the crossroads plane |
| `college_sections.py` | reads the lidar and the 0.20.2 gate OBJ, writes `college_sections.json` (benches, the built extent, built minus measured per station) |
| `college_sheet_data.py`, `college_sheet.py` | the picture `college_sections.png` (twelve stations) |
| `college_edges.py` | the four pavement edges and their heights per station (`college_edges.json`), drawn on the strip (`college_edges.png`) |
| `college_strip.py`, `college_strip_labels.py` | the picture `college_strip.png`: the road straightened, the 2022 aerial over the surveyed heights, the built edges drawn on both (needs the NAIP crops in `tools/naip_carriageways.py`'s cache, Lake Murray frame) |

Run: `<blender python> college_sections.py <workshop>/data/track.obj`, then `college_sheet_data.py` (same python),
then `python college_sheet.py` (Pillow). Offsets: + = left of travel = west on College northbound. Heights: engine
y = NAVD88 - 100.8.

## What it shows

- **The real road is split level from about v1180 to v1440** (3,537 to 4,314 m along the lap). The northbound
  carriageway (east) rides a bench above the southbound (west):

  | v | 1180 | 1200 | 1220 | 1240 | 1260 | 1280 | 1320 | 1340 | 1400 | 1420 | 1440 | 1460 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | northbound over southbound, m | 1.3 | 2.2 | 3.1 | 5.4 | 5.8 | 5.3 | 5.5 | 5.1 | 1.2 | 1.9 | 1.0 | 0 |

  The G10's own check against the older research agrees (+2.51 / 5.59 / 5.91 / 5.33 / 5.02 / 1.85 m at v1216 / 1243 /
  1258 / 1290 / 1342 / 1396).
- **Where the benches sit** (v1240-1340): southbound about +4 to +14 m, northbound about -15 to -6 m, each 8 to 10 m
  wide; the bank between them is about 9 m wide and rises up to 6 m.
- **The build is one slab**, -14 to +16 m, at the southbound grade. Its northbound half sits **up to 6.1 m below** the
  real northbound carriageway (built minus measured: -6.1 m at v1260), cut into the hillside the real road rides on.
- **In plan** (`college_strip.png`, v1240-1340): southbound pavement about W 14 to W 5 m, a planted island on the bank
  about W 5 to E 6 m, northbound pavement about E 6 to E 15 m. The built slab's outer edges (14 to 16 m each side) sit
  close to the real outer pavement edges; what is wrong is the northbound half's height and the middle, where the
  build paves the bank. [read by eye off the picture]
- **Per station** (`college_edges.json`, `college_edges.png`; v1200-1420, 221 stations with all four edges): northbound
  pavement median 10.0 m wide, southbound 10.0 m; the middle (bank and planting) median 10.5 m,
  p90 12.0 m; northbound over southbound up to 6.19 m. The main island reads from v1172 to v1444;
  shorter reads at v1104-1116, v1476-1507.
  The real outer edges sit a median 0.5 m (east) and 2.0 m (west) from the built slab's edges. Single stations misread
  under trees (the middle reads up to 17.0 m at v1297); the 9-station median does not remove every one, so the edges are
  an input to check against the picture, not yet a centreline.
- At v880 the built road is 7 m above the class-2 ground: a bridge deck, as built.
- `[invented]` in the reading: a bench = at least 6 m of measured ground with cross slope under 8 % (taken over 1.5 m).

## J1

The crossroads plane off the same lidar (r 25 m): 6.08 % falling to bearing 277°, toward Waring, rms 0.13 m (the G10's
read; `j1_waring.lidar.g10.json`). Kevin: "Tilt it now", as one change with the College work.

## The design (stage A, `college_design.py` -> `college_design.json`, `college_design.png`)

Four control points across the road at every vertex v1130-1480: southbound outer and inner, northbound inner and
outer; the inner two are the island's edges where it exists (v1172-1444) and one crown point elsewhere. Edges are the
measured ones with misreads dropped and bridged (v1297-1300 under the trees are bridged, as the Mac asked; the flags
are in the file), then averaged over about 33 m; heights are the lidar's, averaged over about 15 m; the last 30 m at
each end blend into the road as built (design minus built at the zone ends: under 5 cm).

Checks: northbound over southbound up to 6.17 m (v1255); steepest long grade northbound 9.5 %, southbound 9.3 %
(as built 8.7 %); crossfall within about 5 %; the bank's slope median 45 %, up to 53 %; northbound pavement median
10.1 m, southbound 9.9 m, the island up to 12.4 m wide.

Bridged edge points of 351 stations: southbound outer 110 (trees and shadow on the west side), southbound inner 21,
northbound inner 49, northbound outer 54. The outer edges wander by a metre or so with the read; **the plan for
authoring is to keep the built outer edges** (0.5 m east and 2.0 m west of the measured ones, median) and rebuild the
middle and the northbound height, so walks, houses and ground outside the road stay put.

## Stages

- **A (here, no build): done.** Measured sections, edges, the design, and the standalone proof scene with before / after stills.
- **B:** author the split into a scratch copy of `lm_phase2/project` (never the build session's workshops): both
  carriageways, the bank and the island, the two transitions, J1's tilt as one change; then every consumer the ledger
  lists (ground seating, paint, curbs, lamps, barriers, the race layouts' corridor on College, AI lines).
- **C:** a full `ship_track` rehearsal through the Mac's queue; installs only as Kevin's standing word allows.

**The race on College: each direction on its own carriageway** (the Mac, 2026-11-22, from the race corridor's standing
rule). Speedway (clockwise, northbound here) runs the upper northbound road; Speedway Reverse runs the lower southbound
road. The rule is the race layouts' own description (ledger 0049 section 9: "an Alvarado-wide lane on your own side of
every road"), which ledger 0054 cites for the median noses ("The median noses: decided (the K-rail at the nose, "your
own side of every road")"). Those words are the layout description Kevin's layouts were built to, not a sentence he
typed. He was also asked on the PC the same evening (own road each way, or both on the lower road) and had not
answered when this was written; his answer wins.

## The proof scene (`college_proof_blend.py`, `college_proof_sheet.py` -> `college_proof.jpg`)

Before = the gate OBJ of 0.20.2. After = the design's two carriageways on the lidar's 1 m ground inside a 40 m
corridor, the build outside it. Three cameras, the same in both: northbound at v1215, southbound at v1410, and from
the south-west 85 m up. The 1 m grid agrees with the design on the line (median +0.012 m where there is no island).
A shape study only: no paint, lamps, trees, curbs or closed seams; the stills and the .blend stay in
`D:/k10-scratch/lm_r2_college/proof`.

## Stage B: what the authored scene holds on College (read off `loop.blend` of 0.20.2, read-only)

The scratch copy is `D:/k10-scratch/lm_r2_college/project` (a copy of `lm_phase2/project`; `inspect_college.py` and
`inspect_columns.py` beside it print this). Offsets are from the lap line, + = west.

| Object | On College (v1130-1480) | What the split does to it |
|---|---|---|
| `ROAD` | **three columns** per station: the two edges (12.5 to 16.3 m out) and the line, all at the line's height + 0.10: one flat slab | new columns at the island's two edges; the northbound half takes the measured heights; no pavement between the island's edges |
| `CURB` | walks outside each edge (curb, 1.8 m walk, outer drop), and the 7 m raised island at +-3.5 m where it is part of the street | the east walk rises with the northbound road; the island's curbs move to the measured island edges |
| `1KERB_sidewalk_streetonly_median`, `1WALL_guard_streetonly_median`, `GUARDRAIL` | the island and a rail on the line; "streetonly" pieces exist in Free Roam only, because the Speedways cross here today | replaced by the planted bank; the crossover goes |
| `MARKINGS`, `YLINE` | lane lines at +-3.7 / 7.4 / 11 m, edge lines, a yellow line on the lap line | repainted per carriageway on the new surfaces |
| `TERRAIN` | dense (about 60 vertices across +-45 m at each station); east of the road it is cut down to the slab (the hill stands 6.7 m over the line 30 m east at v1260) | the bank between the roads and the hill east of the northbound road go to the surveyed ground |
| `LIGHTPOST_3`, `LIGHTPOST_4`, `LIGHTS_0` | lamps about 21 to 22 m out on both sides | the east ones stand on the raised ground |
| `1WALL_race_edge_*_college_*`, `RACE_CLOSE_*`, race kerbs | the Speedways' corridor walls and closures (collections `RACE`, `RACE_CLOSE_CW / ACW`) | rebuilt for one carriageway per direction |
| `AUTH_bespoke` buildings | houses 20 to 36 m out on both sides | untouched; their seats on the east side need a check against the raised ground |

Not read yet, and needed before authoring: which tool makes each of these (the assembler's GEN layer or a later author
step), what `ship_track --skip-blend` re-runs on an authored scene, how `median_bands.json` / `barrier_bands.json` and
the gates' centreline use the lap line (it will lie in the planted bank), and whether round 1's empty-workshop rebuild
(the Mac's `claude/lm-finish-20261122`) changes where a new author step should sit.

## Next (ledger 0055, "Bounded proof" steps 3 to 7)

Author both carriageways, the bank and both transitions together as one connected system, on a scratch copy; prove
connected pavement through College / Navajo / Waring in both directions on the built proof; only then integrate.

## The split as data (step 1, `college_split_data.py` -> `college_split.data.json`, `college_split.png`)

The two roads as lap data, no Blender: the mainline moved onto the southbound road, the northbound road as the piece
`college_nb`, the Speedway lap `college` with its two declared joins. `python college_split_data.py <project> [--write]`;
`python college_split_plot.py` draws the picture. The numbers and what was learned are in `STEP-DESIGN.md`, "Step 1 done".

## The ribbons in the scene (step 2, `college_split_blend.py`, `college_split_stills_blend.py` -> `college_split_step2.jpg`)

`blender --background <loop.blend> --python-exit-code 1 --python college_split_blend.py -- [--save-as <copy>]` edits ROAD
from `college_split.data.json` and checks itself (no save on a failure). Scratch scene only so far; `STEP-DESIGN.md`,
"Step 2 done", has the result and what changed in the plan (the forks are plain road, not pads).

## The middle (step 3, `college_middle_blend.py` -> `college_split_step3.jpg`)

Run on a scene that carries step 2: `blender --background <loop.blend> --python-exit-code 1 --python college_middle_blend.py -- [--save-as <copy>]`.
Takes the old island, its top, barrier, street-only pieces and paint out and builds the bank, the barrier, the raised
east walk and the paint. `STEP-DESIGN.md`, "Step 3 done", has the numbers. `college_split_stills_blend.py` takes a third
argument naming the objects to show.

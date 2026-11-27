# Colfax today: the lap's Colfax leg after the bus-lane rebuild

2026-11-27. Research and a per-block spec only: **no geometry, no config.** Kevin, 2026-11-25: "Colfax today yes"
(build Colfax as it is now). The lap survey read the 2022 aerial, which shows the street before the rebuild; this
file says what the street is now, from what is public, and what none of it fixes.

**In one line:** the rebuild covers only **Broadway to Logan** on the lap (431 m of the 1,389 m Colfax leg). The city's
100% design drawing covers every block of it. **Between Broadway and Lincoln the bus lanes are at the kerb, not in the
centre.** They move to the centre between Lincoln and Sherman and are centre-running, with a raised median between
them, from Sherman east. West of Broadway nothing changed and the 2022 survey stands.

## Sources, newest first

| # | Source | Date | What it fixes | Grade |
|---|---|---|---|---|
| S1 | OSM, `source/osm.json` | data as of 2026-11-23 | every Colfax way from Broadway (x −214 m) east: `lanes=2`, `bus:lanes=designated\|yes`, `access:lanes=no\|yes`, one-way pairs. West of Broadway: no bus tags, lanes 2–5 as before | tagged; coarse (one tag set for all four blocks) |
| S2 | City of Denver, East Colfax BRT project page, "Bus-Only Lane Operations (BOLO)" | read 2026-11-27 | **the lanes are in use:** "Beginning Sunday, September 27, 2026, the two center lanes of East Colfax Avenue from Broadway to Colorado Blvd will be bus-only lanes ... passenger vehicles will travel along Colfax Avenue exclusively in the outer traffic lanes." Also: "The curb median being installed between the Eastbound (EB) and Westbound (WB) BRT lanes will prevent vehicles from making left turns at non-signalized intersections"; "left turns will be restricted to signalized intersections" | published statement |
| S3 | City of Denver DOTI / Parsons, **"E Colfax Ave BRT Proposed Improvements, 100% Design, August 2024", Denver Roll 1 of 4** (N Broadway to Emerson St), marked "Preliminary, not for construction"; its base photograph is dated Nov 2020 | 2024-08 | the layout of every block: bus-only lanes, lane lines, turn pockets, medians, stop bars, crosswalks, signals, bike crossings, kerb changes, trees, proposed lights; two dimensioned typical sections | design drawing, read by eye off the plan; dimensions from its own labels |
| S4 | The lap survey (draft PR 66), DRCOG aerial 2022 | 2022 | the street **before** the rebuild, measured | measured, superseded Broadway to Logan |

S3: <https://www.denvergov.org/files/assets/public/v/3/doti/images/projects/colfax-brt/roll-plot-100percent-denver-1.pdf>
(6.4 MB, not committed). S2: the project page at denvergov.org, "Colfax-BRT". Crops of S3 are in `stills/`, made by
`roll_plot_crops.py`; credit: City and County of Denver, Department of Transportation and Infrastructure.

**Kevin's rule, "newest you have for everything", applied:** S1 and S2 are newest and say the bus lanes exist and are in
use; neither gives a layout. S3 is the newest source that gives one. So: **existence and use from S1 / S2, layout from
S3**, and where S1 and S3 disagree it is said in the block.

## What S3's two typical sections say (feet as labelled; metres beside)

| Section | Where | North to south | Total |
|---|---|---|---|
| **A-A, "roadway typical section"** | cut between Sherman and Grant (about station 108+70) | sidewalk 18 (5.49) · travel lane 12 (3.66) · bus only 12 (3.66) · **median 6 (1.83)** · bus only 12 (3.66) · travel lane 11 (3.35) · turn lane 11 (3.35) · sidewalk 18 (5.49) | **100 ft right of way (30.48 m); 64 ft kerb to kerb (19.51 m)** |
| B-B, "WB nearside station platform" | at the Pennsylvania station, one block east of the lap | sidewalk 11.5 · travel lane 12 · 1.5 · station platform 10 · bus only 12 · bus only 12 · travel lane 11 · sidewalk 10 | 80 ft right of way |

The section linework itself does not render in the PDF; the labels and their order do. A-A sums to its stated 100 ft.

## Block by block, in the lap's direction (westbound, Logan to Broadway)

Lengths are between street labels on S3's stationing (about ±5 m); OSM's node spacing agrees within 4 m.

| Block (lap direction) | Length | Westbound side, kerb to centre (the lap's side) | Centre | Eastbound side | Junction at the block's west end |
|---|---|---|---|---|---|
| **Logan → Grant** (`stills/blk_4_grant_logan.jpg`) | 108 m | one general lane at the kerb; a **left-turn pocket** opens beside the busway for the last third before Grant, behind a hatched taper | two bus-only lanes, S-curving slightly south going west; a **median** line between them the whole block | one general lane; a left-turn pocket at the Logan end | Grant: signal; crosswalks all four sides; a kerb extension on the north-east corner |
| **Grant → Sherman** (`blk_3_sherman_grant.jpg`), holds the grid | 108 m | **one general lane, 12 ft, at the kerb** (hatched taper at the Grant end) | two bus-only lanes, 12 ft each, **6 ft median** between (section A-A) | one general lane 11 ft and a **right-turn lane** 11 ft for the block's east part; a kerb extension at the south-east corner of Grant | Sherman: signal; crosswalks both sides; **two green bike crossings** across Colfax; the start/finish crosswalk is here |
| **Sherman → Lincoln** (`blk_2_lincoln_sherman.jpg`) | 113 m | two general lanes; the westbound bus path leaves the centre and reaches the **north kerb** by Lincoln (drawn as a dotted line, then a red-barred bay with left-turn arrows at the Lincoln stop bar) | a median for the east two thirds, ending in a painted taper; no centre busway by Lincoln | two general lanes shifting south-east (lane-shift arrows); the eastbound bus lane runs from the **south kerb** at Lincoln toward the centre at Sherman | Lincoln: signal; crosswalks |
| **Lincoln → Broadway** (`blk_1_broadway_lincoln.jpg`) | 104 m | **bus-only lane at the north kerb**; two general lanes; a left-turn pocket for the west half | a centre line; a short island at each end | a left-turn pocket for the east half; two general lanes; **bus-only lane at the south kerb** | Broadway: signal; crosswalks. Stops here are labelled "WB BRT STOP (Standard Curb)" and "EB BRT STOP (Standard Curb)": **kerbside stops, no centre platform** |

**No station platform stands on the lap.** The Civic Center / Broadway station is the two kerbside stops above. The first
centre platforms are at Pennsylvania, east of Logan.

## What this changes for the track (facts, not decisions)

- **The grid block.** Between Grant and Sherman the lap's westbound side is 24 ft (7.32 m) of pavement between the north
  kerb and a raised median: one general lane and one bus lane. The whole street is 64 ft (19.51 m) kerb to kerb with the
  6 ft median in it.
- **Turn 12 (Logan onto Colfax westbound)** crosses the eastbound lanes and both bus lanes; the median is open at
  signalised junctions (S2), and Logan is one.
- **The start/finish crosswalk at Sherman** gains two green bike crossings beside it in the design.
- **Where S1 and S3 disagree:** OSM tags Broadway to Lincoln the same as the centre-running blocks (two lanes each way,
  the inner one for buses). S3 draws three lanes each way there with the bus lane at the kerb. OSM is newer but one tag
  set was spread over all four blocks; S2's "two center lanes ... from Broadway" is a corridor summary. **Taken: S3's
  kerbside layout, flagged as the one block where a newer source hints otherwise.**
- **15th St** (also on the lap) is where the same service runs kerbside in bus lanes that already existed (S2: "side-running
  transit lanes along 15th and 17th Streets"). Nothing is rebuilt there; the 2022 survey stands.

## What no public source fixes

1. **As built against the design.** S3 is a 2024 design marked not for construction. S2 confirms the centre lanes and the
   kerb median exist and are in use; it confirms no dimension and no block's lane lines.
2. **Whether the bus lanes are red.** S3's legend uses red as its symbol for "bus-only lane (24 hrs)". The colour of the
   pavement is not stated anywhere I could read. "BUS ONLY" legends are drawn in each lane.
3. **The median's height and section** beyond S2's word "curb median" and A-A's 6 ft.
4. **Lane widths outside section A-A.** Every count in the table is read by eye off the plan; only A-A's are dimensioned.
5. **Signal heads, sign faces, the new lamp posts' positions on the ground** (S3 marks proposed lights and trees as symbols).
6. **Any photograph after the rebuild.** DRCOG's 2024 aerial is refused; NAIP ends at 2023-09. The Denverite article of
   2026-09-28 on riding the new lanes refuses this session (403).

A photograph from Kevin's own drive, or one dated street-level frame per block, would close 1, 2 and 3.

## Unchanged, for the record

West of Broadway to Speer (958 m of the leg): OSM carries no bus-lane tags, the project page puts the service on 15th
and 17th Streets there, and S3 stops at Broadway. The lap survey's 2022 reading is the layout.

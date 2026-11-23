# Survey pilot — Colfax, Logan to Lincoln (PLAN §4b)

2026-11-23. 385 m of Colfax (the start line and the hill), four signalled junctions, the pavement plus about 30 m each
side. **A pilot of the method and the file schema; the whole lap has not been run.** No geometry.

Files here: `paint.json`, `poles.json`, `signs.json`, `census_by_eye.json`, `stills/`, `build_pilot.py` (how they were
made). Readers, one level up: `paint_read.py`, `strokes_read.py`, `drapp_mosaic.py`, `ept_box.py`. Rasters and points are
not in git: the pilot fetched 41 MB of one 2022 tile (`S1E100b`) by HTTP range and 16 lidar nodes (134,151 returns).

## What was measured

| Class | Source | Read | Grades | Second reading (L5) |
|---|---|---|---|---|
| **Paint** | DRCOG 2022 3-inch aerial, through the aerial engine's `Ortho` and `channels` | 308 marks: 19 crosswalk pieces (106 bars), 33 broken lines (884 m), 16 solid white lines (152 m), 8 double-yellow runs (156 m), 49 bars (stop bars and lone crosswalk bars), 183 small marks | **125 measured, 183 detected** (fragments, lone dashes, symbols: real marks half hidden by vehicles, turn guide dashes, arrows, and clutter; not told apart) | **the 2020 lidar's intensity**, a different sensor and year: of the 125 measured, 98 confirmed, 11 contradicted, 16 had too few returns to say |
| **Posts** (lamps, masts, sign posts) | the same aerial, by their shadows | 204 candidates on the stretch | all **detected**; at the one junction checked by eye, 6 are posts and 9 are not | **none exists.** At Colfax / Sherman, read by eye: 10 posts; the reader found 6 (recall 0.60, precision 0.40), and 1 of the 3 signal masts |
| **Signals** | OSM for which junctions; the aerial for the masts | all four junctions are tagged signals. Masts read (by eye) at Sherman only: 3 mast arms and 1 short post | measured by eye at Sherman; tagged at Lincoln, Grant, Logan | none |
| **Signs** | OSM only | per junction: signals, the cross street's one-way and limit as tagged | all **tagged**; no post position, no face | none |

**Paint numbers** (measured items, median and 16–84 %): broken white lines dash 3.02 m, gap 8.85 m, read width 0.22 m;
solid white 0.29 m; double yellow 0.39 m across both lines; crosswalk bars 3.17 × 0.67 m at 1.53 m spacing; stop bars
0.62 m wide. **Thin-line widths are over-read by one to two pixels (7.6 cm each): a 0.10–0.15 m line reads 0.2 m.**
Lengths, spacings and positions do not have that problem.

## Position accuracy, and how it was checked

- **Aerial against lidar:** the lidar's ground returns were moved over the aerial's paint in 0.15 m steps; the brightest
  returns land on the paint at a shift of **0.30 m west, 0.00 m north** (whole stretch), 0.15 m / 0.15 m for the west
  half and 0.30 m / 0.30 m for the east half. So the two agree to about **0.3 m**, with no scale or rotation error over
  385 m. The tiles' CRS was inferred (State Plane Colorado Central, US ft): this is the test of it, and it passes.
- On the paint as read, lidar returns average 2.9 in log-intensity over the asphalt beside it (1,707 returns on paint).
- Defensible claim for a measured paint item: **±0.3 m absolute, about 0.1 m relative to its neighbours.** No shift was
  applied.
- Recall, by eye at Sherman: 36 of 40 crosswalk bars read (the 4 missed lie under a mast's shadow and a vehicle); the
  stop bars on both Colfax approaches and on Sherman, both double-yellow runs and the lane dashes read. A crosswalk
  split by a hidden bar comes out as two pieces (19 pieces here for about 16 crosswalks).
- One crosswalk (`p0016`, the Capitol driveway's, 8 bars) is contradicted by the lidar on 6 of 6 bars. The aerial shows it
  plainly. Read as **painted after May 2020**, not as an error; flagged in the file.

## What could not be read

- **Under vehicles: 14.4 % of the roadway** on this stretch at the moment of the photograph; in building shadow 1.4 %.
  Paint there is absent from the file, not "none". A second flight year (2020 or 2018, both free) would see under
  different vehicles.
- **Symbols are not typed.** Arrows, bike and bus marks are found as blobs (55 here) with a position and size only.
- **The road's edge under bare trees** is ragged (branch shadows have asphalt's colour), so a few marks on lawns are in
  the "detected" grade. Kerbs are not in the inventory at all: they were only used to reject marks.
- **Posts: the lidar cannot find them.** Of eight posts checked directly (four signal masts, four lamps), **seven have no return
  more than 2 m above the ground** in the 2020 point cloud (4.0 returns per m² here); one lamp has three. The first
  reader written for this (`../poles_read.py`, thin vertical clusters) found none of the junction's posts and is kept
  only as the record of that. PLAN §4b's "a pole is a thin vertical cluster in the
  lidar" does not hold for this dataset.
- **Post heights are not written.** A shadow's length gives a height only with the sun's elevation, and two building
  shadows against lidar roof heights give 58° (clean: 47 columns, 0.08 m scatter) and 47° (vehicles in the shadow). The
  day and hour of the 2022 flight would settle it; DRCOG's metadata host is refused from here.
- **What a post carries** (lamp type, signal heads, a sign and its face) is not readable from the air.

## Change since the photographs

- **2022 → NAIP 2023-09-25, by eye at 0.3 m: no change** on this stretch (same crosswalks, double yellow, the island at
  Lincoln, the left-turn lane at Grant).
- **OSM today tags every Colfax way here `lanes=2`, `bus:lanes=designated|yes`.** Neither photograph shows a bus lane:
  both show two general lanes each way and a centre turn lane. **So Colfax has been rebuilt since September 2023 and
  no free photograph shows it as it is now** (DRCOG 2024 is listed but refused; the NAIP catalog ends at 2023). Both are
  recorded; nothing is picked. D8 says build what the survey last saw finished, which is the 2022 state in `paint.json`.

## Stills

`stills/paint_sherman.jpg`, `stills/paint_grant.jpg`: the aerial with what was read (green = crosswalk bars, blue =
broken lines, cyan = solid white, yellow = yellow, magenta = bars, orange rings = untyped small marks, white outline =
the roadway as flooded). `stills/posts_sherman.jpg`: green rings = reader candidates confirmed by eye, red = rejected by
eye, yellow = unchecked, blue squares = posts only the eye found.

## Before the whole lap — three things to decide

1. **Posts need a better reader or a by-eye pass.** The shadow reader as it stands misses 2 of 3 masts (their shadows
   merge with their arms') and passes trunks and fences. Options: (a) improve it (mast-and-arm shape, globe lamps as a
   bright dot at the shadow's foot) and still check every candidate by eye on the overlay; (b) read all posts by eye
   (this junction took one view; the lap has 55 signalled junctions). Either way no second source exists for posts.
2. **Paint is ready to run on the lap** as it is, with the "detected" grade kept apart. Running a second year would
   fill what vehicles hid. About 0.5 GB of range requests for the lap's corridor per year.
3. **Colfax's present layout** cannot be surveyed from free imagery. Kevin's captures or a paid 2024 tile would be
   the only sources.

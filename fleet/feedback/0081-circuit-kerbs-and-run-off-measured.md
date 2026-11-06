---
id: 0081
title: Racing kerbs and run-off for the circuits, measured off NAIP at its best (0.3 m 2023) and built on Lake Murray's engine
status: in-progress
scope: tracks/high-plains-lm, exotics-racing-lv-lm, aspen-lm, pueblo-lm, grand-junction-lm, milford-road-course-lm, pikes-peak-lm (not Sand Creek, the freeway, the rally stages or Lake Murray)
layer: project (measured inputs per track) + tools (opt-in keys only the circuits set)
train: -
---

(Numbered 0081: `claude/freeway-lm` took 0080 meanwhile; commit 9da219eb's message still says 0080.)

Cites ledger 0078 (Owed: "Racing kerbs and run-off outlines for the circuits, measured off NAIP / lidar"). Kevin,
2026-11-05: "Yes, start it." His standing words decide every call: "I just want real" — a circuit without real kerbs
gets none; a run-off that cannot be measured stays unbuilt and is reported; every invented number is marked
(`fleet/GATES-CHANGELOG.md` 2026-11-05).

## The data: NAIP at its best year and resolution per site

Round 4 read High Plains off NAIP 2023 as z18 web tiles (0.46 m at 39.7° N) and the other Colorado circuits off USGS's
NAIP ImageServer, which serves only Colorado's 2019 flight (0.6 m). Microsoft's Planetary Computer carries every NAIP year
as USDA delivered it (public domain, USDA FSA): **Colorado's 2023 flight is 0.3 m.** `tools/naip_crop.py` crops one STAC
item to a lon/lat box at native resolution (the data API, tiled, EPSG:4326, corners exact; certificate verification on).

| site | best NAIP (Planetary Computer) | used before |
|---|---|---|
| High Plains, Aspen, Pueblo, Grand Junction, Pikes Peak | 2023, **0.3 m** | 2023 z18 (HP), 2019 0.6 m (rest) |
| Nevada Nights (Las Vegas) | 2022, 0.6 m (2019 0.6 m; 2013 1.0 m is the course's year) | 2019 / 2013 |
| Milford (Michigan) | 2022, 0.6 m | 2022 0.6 m |

No higher-resolution public, licence-clean orthoimagery was found for these sites in reach of this Mac (county / regional
programmes either do not cover the sites or carry no clear public licence); NAIP is the source of record.

New tools (none in any chain; Lake Murray runs none of them): `tools/naip_crop.py` (the crop), `tools/edge_sheet.py`
(station-labelled zooms with the line's lane edges, to check spans by eye), `tools/kerb_spans.py` (measures each
hand-checked span: in / out of the paint across the lane edge, the edge in lon/lat, colour, profile),
`tools/built_beside.py` (the aerial beside the BUILT kn5's faces, per kerb object).

## High Plains (`high-plains-lm` 0.1.2): 20 measured runs, two paint schemes; no run-off

**What is really there (NAIP 2023-09-28, 0.3 m):** two kinds of edge paint, each checked by eye on
`tracks/high-plains/source/edges/kerbs_2023_030_sheet.jpg` (all 20 cells):
- **11 blue / white kerbs**, 1.3-2.9 m of paint across the edge (the wide blocks round the apexes): L s 212-239, 1,680-1,716,
  2,636-2,666, 2,845-2,856, 2,950-2,975; R s 448-486, 623-638, 1,519-1,540, 2,000-2,019, 2,328-2,411, 2,892-2,914;
- **9 blue / yellow edge stripes**, 0.45-1.05 m of paint on the asphalt edge (entries and exits): L s 517-537, 690-699,
  1,567-1,592, 2,038-2,073, 2,453-2,490; R s 263-299, 1,747-1,768, 2,678-2,697, 3,013-3,044.

Round 4's 12 runs are all inside these; its L s 2,056-2,071 "blue_white" kerb is a blue / yellow stripe at 0.3 m.

**Run-off: none paved, none built** (`runoff_2023_030_sheet.jpg`): the colour reader's 21 "asphalt past the edge" runs are the
other configurations' pavement (the north course's branches at s 1,348 / 2,722 / 2,832, the parallel loop beside s 265-322
and s 456-474), the pit lane (s 3,040-3,082) and dirt; beyond every kerb is graded dirt and prairie, which the ground already is.

**Built:** the 11 kerbs as before (the config's 0.08 m, invented); the 9 stripes **flat** (`"profile": "paint"`: lip only,
no height is seen), each in its colour through one atlas texture (`kerb.atlas`, `textures/kerb_atlas_hp.png`, made by
`make_kerb_atlas.py`: the blue / white file as it was beside a blue / yellow cell, the yellow NAIP's median stripe colour
(205, 194, 137)). 20 runs, 515 m built (round 4: 12, 243 m). Stills: `kerbs_built_beside_0.1.2.jpg` (each kerb: aerial |
built kn5 faces).

| High Plains (from an EMPTY workshop, `tools/ship_track.sh --no-install`, Mac) | 0.1.1 | **0.1.2** |
|---|---|---|
| soft top / severe / bumps /km / kinks /km | 0 / 0 / 0 / 1.87 | 0 / 0 / 0 / 1.87 |
| vertex bumps / drops / far ledges / obstructed / floating | 2 / 0 / 0 / 0 / 0 | 2 / 0 / 0 / 0 / 0 |
| audit_mesh / verify_kn5 / kn5_ground_check (road over ground p95) / house_seat | CLEAN / PASS / PASS (0.021) / PASS | CLEAN / PASS / PASS (0.021) / PASS |
| edge report: at 1 m strip or kerb / rise within 2 m p95 | 100 % / 0.014 m | 100 % / 0.015 m |
| kn5 | 15.6 MB | 15.6 MB (15,616,494 B) |

No gate is worse. **Not real yet (owed):** the build lays every run OUTSIDE the lane edge (round 4's placement), but the
measured paint sits mostly across or inside the live line's edge (in_m down to -2.05 m): the stills show the built kerbs up
to ~1.5-2 m outboard of the paint at s 1,680, 2,000, 2,328 and 2,950. Placing them at their measured offset puts a raised
kerb over the lane ribbon, which drive_test's wheel paths would then cross; that wants its own round.

## Nevada Nights: the apron cannot go physical yet: the draped pads are under the built ground

What is there is round 5's: the 2013 concrete apron, 16 runs read per 3 m station (`runoff_2013.json`), 14 built as visual
`PADAPRON_*` pads. NAIP's best for the site is 2022 at 0.6 m and the course is the 2013 one, so nothing better was read.

Tried on the Mac (`nv012`, from an empty workshop): the 14 pads named `1RUNOFF_apron_*` (an opt-in pad key `"surface":
"1RUNOFF"`, surfaces.ini RUNOFF physics, the same concrete skin). Every gate stayed as 0.1.1 (severe 0, kinks 0, drops 0 /
far ledges 3, audit CLEAN, kn5_ground_check PASS p95 0.021 m, verify_kn5 PASS, houses PASS, kn5 13.3 MB). **But the
aprons lie under the ground:** `tools/apron_seat_check.py` on the built OBJ, 6,536 samples on 1,634 apron triangles: the
1GRASS surface stands over the apron at **57.1 %** of them (median +0.046 m, p95 +0.70 m, max +1.16 m). A physical apron
the car cannot reach is not the real run-off, so **nothing was committed for Nevada**: the opt-in and the config change were
reverted, and 0.1.1 stands. The pads are draped at the author stage on 4 m cells at 6 cm over the ground of that moment;
the prep then re-seats the ground. The visual pads in 0.1.1 are the same cells under another name, so they are very likely
buried the same way (not measured: no 0.1.1 OBJ on this Mac; `python tools/apron_seat_check.py <ws>/data/track.obj PADAPRON`
on the PC's build answers it).

## The other circuits on NAIP 2023 at 0.3 m (measured on the Mac; nothing built)

Crops: `tools/naip_crop.py --track tracks/<live> --margin-m 40` with the 2023 0.3 m items (Aspen
`co_m_3910641_se_13_030_20230907_20240104`, Pueblo `co_m_3810443_se_13_030_20230920_20240104`, Grand Junction
`co_m_3910861_nw_12_030_20230924_20240104`, Pikes Peak `co_m_3810427_ne_13_030_20230920_20240104`).

- **Pueblo: red / white kerbs ARE there.** Round 4's "no painted kerbs readable" was the 0.6 m 2019 image. At 0.3 m the colour
  scan finds 10 candidates and all 9 checked by eye are red / white kerbs (`tracks/pueblo/source/edges/kerbs_2023_030_check.jpg`:
  L s 1,069, 1,578, 2,270, 3,075; R s 1,260, 1,284, 2,135, 2,560, 2,991), most running well past the scan's span (NAIP's
  faded red reads pink). Not built: the full extents are not measured yet. `tools/kerb_blocks.py` (light / dark blocks
  alternating along the edge, colour-blind) lists 75 candidate runs, 1,314 m
  (`kerb_blocks_2023_030.candidates.json`), but on High Plains it lists 70 / 1,633 m against the 20 / 560 m checked, so
  every one wants the eye.
- **Aspen: more kerb than round 4 built, and one run that 2023 does not show.** Zooms (`tracks/aspen/source/edges/
  kerbs_2023_030_check.jpg`, `_ends.jpg`, 10 m ticks): the L s 233-262 and R s 838-862 kerbs run on past both traced ends
  (white and faded-red blocks), the L s 1,017-1,038 kerb continues past s 1,050; at L s 1,495-1,566 (built in 0.1.1 off 2019)
  2023 shows a plain light edge band, no blocks. Not rebuilt: the extents want the same span-by-span pass High Plains got,
  and the 1,495 run is Kevin's call (gone by 2023, or painted over).
- **Grand Junction: none confirmed.** The colour scan finds nothing; the block finder's one run (L s 1,260-1,278) is the
  dashed white line between the track and the parallel pit lane, not a kerb. Faint light blocks show along the right edge
  near s ~200 and ~1,000 (`grand-junction` zooms, not committed): possibly faded kerbs, not readable as such at 0.3 m.
- **Pikes Peak: none.** Colour scan and reader: 0 kerb runs on the oval; the block finder's 19 candidates are along the
  outer wall and joints (round 5's wall is the measured edge there).
- **Milford:** NAIP's best is 2022 at 0.6 m, already read in round 4 (no kerbs: the hits were tree shadow). Unchanged.

No lidar runbook is written this round: QL2 lidar (2-8 pts/m², ~10 cm vertical noise) cannot see a 5-8 cm kerb's height,
and its intensity would only re-find paint the 0.3 m imagery already shows; it would earn a run for Grand Junction's faint
blocks or for the run-off surfaces' class (gravel vs ground), not before.

## Lake Murray unchanged

`git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty. Of what this round touched,
the chain runs only `tools/author_kerbs_blend.py` (the `kerbs` step, a no-op without `route.kerbs_file`, which Lake Murray
does not set; the atlas and the paint profile are read only from a config / kerbs file that sets them). The new tools are in
no chain. `tests/run_tests.py`: 1,272 passed, 13 failed, the same 13 as on fleet-lm-engine's head on this Mac (registry,
draft_equiv, ship_track_chain, bench_pad, ship_fleet: Windows paths).

## Round 2 (Mac, 2026-11-05)

### 1. Kerbs at their measured offset: High Plains 0.1.3

**Why the built kerbs sat outboard.** kerb_spans measures in_m / out_m across the LIVE line's lane edge; the port's ribbon is
its own line (the assembler smooths it), and at High Plains' apexes its lane edge lies 0.24-1.16 m OUTSIDE the live edge
(`kerbs.built.json` `edge_delta_m`). Round 4 laid every run from the port's edge outward, so a kerb measured 2 m inside the
live edge was built up to ~3 m outboard of its paint.

**Now (opt-in `kerb.placement: "measured"`, `tools/kerb_section.py`):** each ribbon row reads the measured edge nearest it
and lays the paint at in_m .. out_m from THAT, as an offset from its own edge: at High Plains the runs span from 2.98 m
inside the ribbon's edge (R s 2,000-2,019: -2.98 .. -1.33) to 1.72 m outside (R s 2,892). Over the lane the base is the ROAD
ribbon's own surface (a ray down, 0 misses); outside, the edge's height as before. Kerbs rise to the config's 0.08 m
(invented, as before); paint stays flat at the 3 mm lip. Each run is clipped to its measured ends (keying the ends to the
nearest ~3 m row cut up to half a row off each). The extents were re-read by the key colour (`kerb_spans.py --grow 10`:
blue, at most 10 m past the eye span): within 1-5 m of round 1's eye spans (L s 687-699, 2,843-2,856; R s 447-486,
622-638, 1,519-1,541, 2,673-2,698, 3,010-3,044), `s_eye` kept. 20 runs, 526 m built.

**The gate finding, and the one invented number it bought.** Laid at its measured place a kerb lies over the 12 m lane
(the live line's constant width; the real track is narrower at those apexes), so drive_test's interior wheel paths
(1.25 m and 2.75 m inside the edge) ride it. With full-height ends (build `hp013a`): **severe 4** (R s 1,996-2,015, 2.75 m
inside: the kerb's ends), kinks 7.8 /km (every run end on the 1.25 m path). With the tops ramped to the lip over
`kerb.end_ramp_m` 4.0 m at each end (invented, GATES-CHANGELOG; 2 % / 0.02 m per metre, under the bump and kink thresholds;
real kerbs are ramped at their ends, this length is not measured): every gate as 0.1.1 or better.

| High Plains (EMPTY workshop, `tools/ship_track.sh --no-install`, Mac) | 0.1.1 | 0.1.2 | **0.1.3** |
|---|---|---|---|
| soft top / severe / bumps /km / kinks /km | 0 / 0 / 0 / 1.87 | 0 / 0 / 0 / 1.87 | 0 / 0 / 0 / **0.62** |
| vertex bumps / drops / far ledges / obstructed / floating | 2 / 0 / 0 / 0 / 0 | same | 2 / 0 / 0 / 0 / 0 |
| audit_mesh (K kerb in carriageway) / verify_kn5 / kn5_ground_check (p95) / house_seat | CLEAN / PASS / PASS (0.021) / PASS | same | CLEAN (K 0) / PASS / PASS (0.021) / PASS |
| edge report: at 1 m strip or kerb / rise within 2 m p95 | 100 % / 0.014 m | 100 % / 0.015 m | 100 % / 0.012 m |
| kn5 | 15.6 MB | 15,616,494 B | **15,632,786 B (15.6 MB)** |

Stills: `tracks/high-plains/source/edges/kerbs_built_beside_0.1.3.jpg` (all 20: aerial | built kn5 faces); each built kerb
now lies on its paint. Seen there and not resolved: several blue / yellow stripes (L s 517, 690; R s 1,747, 2,678, 3,013)
look longer in the aerial than the blue blocks the grow follows (past the ends the stripe reads yellow only, which is the
dry grass's colour to the reader): their extents stay the blue's.

### 1b. Nevada's six kerbs: NOT re-placed: their offset cannot be measured on the imagery in reach

Nevada's kerbs file carries in_m / out_m -0.5 / 1.0 [invented] (round 4: traced by eye). Measured now on the 2019 crop
(0.48 m, `naip_2019_exr.png`): the red does not read as red at all (`kerb_spans` red-only: "no paint measured"), and the
white matches the lot's concrete (with the white, the widths ran to the band's edge: L s 915 -2.05 .. +2.45 m). A
colour-blind read of the alternating blocks (luminance alternation per offset, half-peak band) gives R s 265-400
-1.65 .. +0.75 and R s 690-770 -1.50 .. +0.45 (clear contrast; on High Plains, the control, the same read lands within
~0.3-1 m of the colour measure, so it is a lead, not a measure); the other four are weak or run to the band's edge. By eye
(`tracks/exotics-racing-lv/source/edges/kerbs_2019_zoom_r2.jpg`) the blocks lie along the inside of the lane edge, and at
R s 1,440-1,460 none show. So Nevada keeps 0.1.1's kerbs (outside the edge, the invented offsets), and the measured place is
**Kevin's call / owed**: NAIP 2022 (0.6 m) is no sharper; a ground photo or the course's own map would decide it.

`kerb_spans.py`: a red / white run's width is now read off its red blocks alone (the white reads like Pueblo's pale sand
and Nevada's concrete); no committed file was measured the old way.

### 2. Nevada Nights 0.1.2: the 2013 apron as real run-off, on the prepped ground

**0.1.1's visual pads are buried, measured** (this Mac's build of the committed 0.1.1, `nv011`, from an empty workshop):
`apron_seat_check.py ... PADAPRON`: 1,634 apron triangles, 6,536 samples, **ground over the apron at 57.1 %** (median
+0.046 m, p95 +0.70 m, max +1.16 m): the same as round 1's 1RUNOFF try. The installed 0.1.1 shows the ground through its
apron wherever the prep raised it.

**Now** (opt-in `scenery.bespoke.pads_seat: "ground"`, `pads_surface: "1RUNOFF"`; `tools/seat_pads_blend.py` inside prep,
after the prep's own ground work; `tools/pad_clip.py`): each pad is rebuilt from the PREPPED ground's own triangles under
its cells, each cut to the cell's outline in plan (so the pad keeps the measured 2013 outline: 11,526 m² against 0.1.1's
11,532 m², per pad the same to 1 m²), 6 cm over the ground (the pads' own lift), and named `1RUNOFF_apron_<k>`
(surfaces.ini RUNOFF: paved, off-track; the same concrete skin via `texture_overrides["1RUNOFF"]`). Self-checked in the
step (ground over 0 vertices of 14 pads). On the built OBJ: **ground over the apron 0.0 %** of 174,172 samples (the apron
6 cm over it everywhere, max -0.053 m).

| Nevada (EMPTY workshop, Mac) | 0.1.1 | **0.1.2** |
|---|---|---|
| soft top / severe / bumps / kinks /km / drops | 0 / 0 / 0 / 0.0 / 0 | 0 / 0 / 0 / 0.0 / 0 |
| far ledges (reported, not gated) | 3 (s 452, 15-16 m out) | **4** (the same place, one more at 13.5 m: the apron's outer lip over the falling ground) |
| audit / verify_kn5 / kn5_ground_check (p95) / house_seat | CLEAN / PASS / PASS (0.021) / PASS | CLEAN / PASS / PASS (0.021) / PASS |
| edge report: at 1 m kerb / rise within 2 m p95 | 100 % / 0.076 m | 100 % / 0.078 m |
| apron: ground over it / physics | 57.1 % / none (visual) | **0.0 % / 1RUNOFF** |
| kn5 | 13,328,116 B (13.3 MB) | **19,109,912 B (19.1 MB)** |

**Worse: size, +5.8 MB.** The apron now carries the ground's own resolution (43,543 triangles where 0.1.1 had 1,634 draped
4 m cells): the ground along Nevada's edges is fine (seat_edges), and a coarser apron is what lay under it. Merging the
cut pieces of each ground plane back saved almost nothing (the planes differ triangle to triangle). Kevin's call whether
19.1 MB stands. Still: `tracks/exotics-racing-lv/source/edges/runoff_built_beside_0.1.2.jpg` (2019 aerial | the built
apron faces).

### 3. Pueblo: the 75 candidates checked by eye; 15 are red / white kerbs; NOT built yet (the paint's offset cannot be read)

Every one of `kerb_blocks.py`'s 75 candidates checked on edge_sheet zooms of NAIP 2023 at 0.3 m (91 cells, long candidates
in pieces), the sheets kept beside the result: `tracks/pueblo/source/edges/candidates_2023_030_sheet_00..07.jpg`,
`kerbs_eye_2023_030.json` (each candidate: kerb or not, and what was seen). **15 kerbs**: L s 1,069-1,092, 1,556-1,599,
1,902-1,972, 2,069-2,129, 2,267-2,292, 2,596-2,628, 3,047-3,094; R s 1,129-1,138, 1,250-1,312, 1,494-1,535, 1,837-1,884,
2,131-2,171, 2,540-2,570, 2,992-3,048, 3,278-3,299 (round 1's nine are among them). 60 are not kerbs (plain edges, joints,
shadow, gravel, the paddock and drag-strip roads). Seen beside them: several kerbs run past the finder's span (L s 1,069
from ~1,062; L s 1,902 to ~1,980; L s 2,069 from ~2,045; L s 2,267 from ~2,255; R s 2,131 from ~2,115; R s 2,992 from
~2,988), and one kerb is no candidate at all: the right edge near s 1,190-1,215.

**Why nothing is built:** the measurer cannot read Pueblo's paint. Its red is faded to pink at 0.3 m (at L s 2,090 the
blocks read (245, 239, 234) white and ~(176, 168, 162) / (140, 132, 93) between: `kerb_spans`'s red class finds **0**
red pixels over L s 2,030-2,075 and R s 1,180-1,230), and the white is the pale sand's colour. A colour-blind read of the
alternating blocks (luminance alternation per offset) is a lead only: on High Plains, the control, it lands 0.3-1 m off
the colour measure. Building the 15 at a guessed offset would be invented, so Pueblo stays at 0.1.1 (no kerbs) and the
offsets are owed: a block-alternation measurer calibrated against High Plains' 20 colour-measured runs (no lidar
reaches Pueblo: its camber survey found no EPT point on the site), or a ground photo.

### 4. Aspen 0.1.2: the L s 1,495-1,566 run is not built (Kevin's call); the span pass at 0.3 m is owed

**Kevin, 2026-11-05, under "I just want real": the newest imagery is what's there.** The L s 1,495-1,566 run (read off 2019
at 0.6 m, built in 0.1.1) shows on NAIP 2023 (0.3 m) as a plain light edge band, no blocks (`kerbs_2023_030_check.jpg`),
so it is moved to `not_built` in `tracks/aspen/source/edges/kerbs.json` with its reason, and Aspen 0.1.2 builds the other
three (76 m). Nothing else changed:

| Aspen (EMPTY workshop, Mac) | 0.1.1 | **0.1.2** |
|---|---|---|
| soft top / severe / bumps /km / kinks /km / vertex bumps / drops / far ledges | 0 / 0 / 0.6 / 13.26 / 41 / 0 / 0 | the same |
| audit / verify_kn5 / kn5_ground_check (p95) / house_seat | CLEAN / PASS / PASS (0.021) / PASS | the same |
| edge report: at 1 m kerb / ground; rise within 2 m p95 | 99.6 % / 0.4 %; 0.0 m | the same |
| kerbs | 4 runs, 149 m | 3 runs, 76 m |
| kn5 | 7,847,326 B | **7,827,187 B (7.8 MB)** |

The three kept runs still sit OUTSIDE the edge at round 4's invented -0.5 / 1.0 m (not `placement: measured`): Aspen's red
is faded like Pueblo's (round 1: "white and faded-red blocks"), so its offsets and true extents (round 1: the L s 233 and
R s 838 kerbs run past both traced ends, L s 1,017 past s 1,050) wait on the same measurer. The span-by-span pass itself
is owed; not done this round.

### 5. Grand Junction: the lidar runbook (written, not run)

`tools/lidar_strip.py` (new, PC only, untested here: the Mac has no LAZ reader; its station / offset frame is checked on
GJ's line: a point 2 m past the right edge at s 200 reads s 200.0, o +2.00): every return of a 3DEP point cloud's EPT in
a box round each named span, gridded on the live line by station and offset (0.5 m cells, 4 m over the lane to 16 m past
the edge): returns, intensity mean / p90, mean z, ground (class 2) share, written to
`tracks/<track>/source/lidar/strip/<SIDE><s0>-<s1>.npz`. Runbook 4h below. What it decides: a kerb is a bright band at
the edge whose intensity alternates along s at the block period (~1-2 m); a gravel trap is a bright, non-ground-varying band
past the edge, packed dirt the ground's own intensity. QL2 (2-8 returns / m², 0.5 m cells hold ~0.5-2) is coarse for 1 m
blocks: expect a band, perhaps no period.

## PC runbooks (round 2)

ENG as 0078's table: `eng_hplm` for High Plains (no new texture: the atlas `textures/kerb_atlas_hp.png` is the port's own,
synced in by ship.json), `eng_nvlm` for Nevada (no new texture: the 1RUNOFF apron wears `building_*`, in REFERENCED.md5),
and for Aspen the copy its 0.1.1 used (round 6, 4c; its `kerb_redwhite.png` is the port's own). From
`D:/k10-worktrees/fleet-lm-engine` reset to `origin/claude/circuit-kerbs-lm` (this branch; nothing merged).

4g. **High Plains 0.1.3, Nevada 0.1.2, Aspen 0.1.2** (round 2). Each, from an EMPTY workshop:
   1. Rehearsal: `SHIP_PROJ=D:/k10-scratch/<ws>_r2 AIROSO=D:/k10-worktrees/fleet-lm-engine ENG=D:/k10-scratch/<eng> bash
      tools/ship_track.sh <track> --no-install` with `<track>` / `<ws>` = `high-plains-lm` / `high_plains_lm`,
      `exotics-racing-lv-lm` / `exotics_lm`, `aspen-lm` / the Aspen workshop of 4c. Expect the Mac's rows (round 2 tables
      above):
      - High Plains: `[kerbs] 20 kerb runs, 526 m, height 0.08 m (config), at their measured offsets (ROAD read missed 0)`;
        soft 0, severe 0, bumps 0, kinks 0.62 /km, vertex bumps 2, drops 0, far ledges 0; audit CLEAN (K 0); verify_kn5
        PASS; kn5_ground_check PASS p95 0.021; houses PASS; kn5 15,632,786 B.
      - Nevada: `[seat-pads] 14 pads laid on the prepped ground`, each line "ground over 0"; soft 0, severe 0, kinks 0,
        drops 0, far ledges 4; audit CLEAN; verify_kn5 PASS; kn5_ground_check PASS p95 0.021; houses PASS; kn5
        19,109,912 B. Then `python tools/apron_seat_check.py D:/k10-scratch/exotics_lm_r2/data/track.obj` must print
        `ground over apron 0 (0.0 %)`.
      - Aspen: `[kerbs] 3 kerb runs, 76 m ... outside the lane edge`; every gate as its 0.1.1; kn5 7,827,187 B.
   2. Install, replacing the same folders (`high_plains_lm`, `exotics_racing_lvms_lm`, `aspen_motorsports_park_lm`): the
      same command without `SHIP_PROJ` and without `--no-install`. AC closed. Kevin's word first for Nevada's 19.1 MB.
   High Plains 0.1.2 was never installed; 0.1.3 replaces 0.1.1.

4h. **Lidar strips (Grand Junction's faint blocks; run-off class where it decides a build)**, PC, fetching from USGS's public
   EPT (nothing to download by hand), with the Python 4f uses (laspy + lazrs, pyproj, numpy):
   ```bash
   PYTHONUTF8=1 python tools/lidar_strip.py tracks/grand-junction --spans R:170-230,R:970-1030 \
     --ept https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_CO_MesaCo_QL2_2015_LAS_2017/ept.json
   ```
   (the dataset GJ's camber survey read, `tracks/grand-junction/source/lidar/camber-survey/README.md`; no Pueblo run:
   its survey found no EPT point on the site, `CO_Eastern_B5_2018` holds none within the track). Expect per span a log line `[lidar_strip] R:170-230: <n> returns in the band, <cells> / 4,961
   cells, ~0.1-0.5 MB` and the median intensity by offset; a few thousand returns per span at QL2. Commit the npz files
   and the logs on this branch and push; nothing is built from them on the PC. Run-off: no circuit's run-off build waits on
   a surface class today (High Plains and Pikes Peak have none paved, Nevada's is the lot's concrete); when one does, the
   same command with that span past the edge reads it.

### Lake Murray unchanged (round 2)

`git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty. Every new behaviour is opt-in
under keys Lake Murray does not set: `kerb.placement` / `kerb.end_ramp_m` (read only by the kerbs step, a no-op without
`route.kerbs_file`), `scenery.bespoke.pads_seat` / `pads_surface` (the prep's new seat step prints no header without
it), `kerb_spans.py --grow` (a tool in no chain). `tests/run_tests.py`: 1,279 passed, 13 failed, the same 13 as on
fleet-lm-engine's head on this Mac; new: `tests/tools/test_kerb_section.py` (7), and the seat step's header registered in
`test_ship_track_chain.py`'s v4 extras (commit 9ad26ee1 had left that test red; fixed in the next).

## Round 3 (Mac, 2026-11-05)

### 1. A block reader calibrated against High Plains' 20 colour-measured runs

**The reader** (`tools/kerb_offsets.py`, new, in no chain): colour is not used. Luminance on a grid in the line's own
frame (0.25 m along s, 0.075 m across, -3.5 .. +3.5 m from the lane edge, bilinear); per station (every 1 m, a 6 m window)
every column detrended; the reference waveform is the column with the most block-period energy, then the mean of the band
found from it (2 refinements); each column's matched-filter coefficient on the reference (~1 wholly on the blocks, ~0 on
asphalt or dirt that never alternates); the paint's inner / outer edge is the band's half-maximum (the half-maximum of a
blurred step is the step); in_m / out_m = the median over stations, as `kerb_spans.py`'s are. Extent: the band's block
amplitude in a 3 m window, walked out from the eye span while over half its median. Invented numbers: GATES-CHANGELOG
2026-11-05 round 3. Tests: `tests/tools/test_kerb_offsets.py` (4).

**Against the 20 truths** (`kerb_spans.py`'s colour measure on the same NAIP 2023 0.3 m crop; the reader given only each
run's eye span). Record: `tracks/high-plains/source/edges/kerb_offsets_calibration.json`; straightened strips of every run
(aerial in the line's frame, lane edge cyan, the reader's edges and ends yellow, the truth's magenta):
`kerb_offsets_calibration_strips.jpg`.

| |residual| (m) | in_m median / p95 / max | out_m median / p95 / max | width p95 | s0 median / p95 | s1 median / p95 |
|---|---|---|---|---|---|---|
| raised blue / white (11) | 0.12 / 0.29 / 0.29 | 0.15 / **1.25** / 1.25 | 1.11 | 2.0 / 3.2 | 2.0 / 6.2 |
| ... R s 2,892's out excluded (10) | | 0.14 / **0.36** / 0.36 | 0.35 | | |
| flat blue / yellow stripes (9) | 0.27 / 0.48 / 0.48 | 0.20 / 0.67 / 0.67 | 0.84 | 6.0 / 12.0 | 4.8 / 7.8 |
| all 20 | 0.16 / 0.34 / 0.48 | 0.17 / 0.67 / 1.25 | 0.84 | 3.2 / 11.2 | 2.6 / 7.2 |

(n = 11 or fewer: p95 is the max.) Read on the strips:
- **R s 2,892's colour truth is wrong, not the reader**: its out +2.30 m (built so in 0.1.3, a 2.85 m kerb) lies on the
  plain dirt past the kerb (the white class took pale dirt); the blocks end at +1.05, where the reader puts them.
- The ends: the colour truth ends at the last BLUE station, so it stops a white block (~1 m) short of a blue / white
  kerb's visible end (R s 448, 2,892); the reader runs ~0.5-1.5 m past the visible end (its 3 m window). L s 1,680's s1
  (-6.2) is the kerb curving out of the median band by its end. The blue / yellow stripes' ends differ by 5-12 m because
  the reader sees the yellow-only ends the colour truth cannot (item 3).

**The bar** (⚠ invented, GATES-CHANGELOG): p95 of both edge residuals <= 0.4 m for the class measured (one 0.3 m pixel
plus the truth's 0.15 m step; under a third of the narrowest raised kerb, 1.3 m). **Raised blue / white kerbs pass**
(0.29 / 0.36, with R s 2,892 out excluded on the evidence above; with it counted, 1.25 fails, and the exclusion is a call
made on the strip, said plainly). **Flat blue / yellow stripes fail** (0.48 / 0.67: a 0.45-1.05 m stripe is 1.5-3.5
pixels, and the half-maximum of a blur that wide is the blur). So the reader measures raised kerbs (Pueblo's, Aspen's and
Nevada's red / white are raised blocks of this class) and not paint stripes. Ends carry no bar: every run's reader ends
are checked by eye on its strip.

### 2a. Pueblo 0.1.2: 15 red / white kerbs measured by their blocks and built at their measured place

**Measured** (`tracks/pueblo/source/edges/kerbs.json`, NAIP 2023 0.3 m; strips `kerbs_blocks_2023_030_strips.jpg`, end
zooms `kerbs_blocks_2023_030_ends.jpg` at 24 px/m with 1 m ticks). Pueblo's blocks read as strongly as High Plains' raised
kerbs (block amplitude 27-48 against 25-38 there). Two things the strips showed, handled:
- **The kerbs drift across the line's offsets along a run** (the band's middle moves 0.2-1.5 m p10..p90: R s 2,135
  -2.03 .. -0.91), so one median offset misplaces a run's ends by up to ~0.7 m. `--follow 1`: the run's edge_lonlat is
  the lane edge moved by the band middle's own deviation station by station (a running median of 9), so in_m .. out_m lie
  on the paint all along (the build's `edge_delta` reads the nearest edge point, unchanged). The strips draw the followed
  band; it sits on the blocks.
- **Ends**: the reader's ends agree with the end zooms within ~1 m on 10 runs; on 5 they do not and the eye's ends are
  used (`:eye`, the reader's kept in `reader.ends`): L s 1,068-1,095 (reader 1,092: one more white block), R s 1,128-1,140
  (reader 1,138), R s 1,496-1,534 (reader 1,501-1,542: the kerb curves off the band at its end), R s 2,135-2,158.5
  (reader 2,116-2,168: nothing is there past either end), R s 3,279-3,296 (reader 3,295: the last blocks turn outward).
  Round 2's "runs past the finder's span" notes (L s 1,069 from ~1,062, 1,902 to ~1,980, 2,069 from ~2,045, 2,267 from
  ~2,255) are not borne out at 24 px/m: the blocks stop where the reader stops.
- **R s 1,190-1,215 is not a kerb**: the strip from 7 m inside the edge to 6 m outside shows a plain asphalt edge and
  dirt, no blocks; nothing measured, nothing built.

| run | s | in_m .. out_m | run | s | in_m .. out_m |
|---|---|---|---|---|---|
| L | 1,068-1,095 (eye) | -0.66 .. +0.15 | R | 1,128-1,140 (eye) | -1.13 .. -0.50 |
| L | 1,557-1,596 | -0.49 .. +0.63 | R | 1,252-1,309 | -0.38 .. +0.61 |
| L | 1,903-1,971 | -0.10 .. +0.71 | R | 1,496-1,534 (eye) | -1.03 .. -0.17 |
| L | 2,070-2,129 | -1.30 .. -0.41 | R | 1,842-1,874 | -2.36 .. -1.45 |
| L | 2,268-2,293 | -0.81 .. +0.27 | R | 2,135-2,158.5 (eye) | -1.86 .. -0.93 |
| L | 2,596-2,627 | +0.09 .. +1.12 | R | 2,543-2,568 | -1.21 .. -0.27 |
| L | 3,048-3,095 | +0.15 .. +1.08 | R | 2,993-3,047 | -2.36 .. -0.89 |
| | | | R | 3,279-3,296 (eye) | -0.55 .. +0.50 |

**Built** (`tracks/pueblo-lm` 0.1.2: `route.kerbs_file`, `kerb.placement: "measured"`, `kerb.end_ramp_m` 4.0 as High
Plains', `texture_overrides["1KERB"]` = Aspen's `kerb_redwhite.png` copied as this port's own, synced by ship.json): `[kerbs]
15 kerb runs, 515 m ... at their measured offsets (ROAD read missed 0)`. Two measured widths are under author_kerbs_blend's
0.9 m floor and built 0.9 (R s 1,128: 0.63; L s 1,068: 0.81; GATES-CHANGELOG). Still: `kerbs_built_beside_0.1.2.jpg`
(each kerb: aerial | built faces): every built kerb lies on its paint.

| Pueblo (EMPTY workshop, `tools/ship_track.sh --no-install`, Mac) | 0.1.1 | **0.1.2** |
|---|---|---|
| soft top / severe / bumps /km / kinks /km | 0 / 0 / 0.29 / 8.01 | 0 / 0 / 0.29 / **8.30** |
| vertex bumps / drops / far ledges / obstructed / floating | 12 / 0 / 0 / 0 / 0 | 11 / 0 / 0 / 0 / 0 |
| audit_mesh (K) / verify_kn5 / kn5_ground_check (p95) / house_seat | CLEAN (0) / PASS / PASS (0.021) / PASS | CLEAN (0) / PASS / PASS (0.021) / PASS |
| edge report: at 1 m kerb / rise within 2 m p95 | 100 % / 0.000 m | 100 % / 0.002 m |
| kn5 | 10,572,602 B | **10,742,723 B (10.7 MB)** |

**Worse by one kink (28 -> 29: 8.01 -> 8.30 /km), not hidden.** R s 3,275, the wheel path 1.25 m inside the 12 m lane,
3.43 % (gate 3 %): the port ribbon's edge lies up to 1.54 m outside the live edge along R s 3,279-3,296 (`edge_delta_m`),
so the measured kerb lies 1.42 m inside the ribbon's edge and the fixed-offset path rides off its inner edge as the two
lines diverge. The real asphalt there is narrower than the 12 m lane. A first build (follow smoothed over 5 stations) read
3 more kinks (R s 3,000-3,010, a parked car's shadow zigging the band 0.58 m) and one more bump; smoothing over 9 stations
removed those. No number was invented to hide the last one: **Kevin's call** (install with one more kink, or not).

### 2b. Aspen 0.1.3: the three runs re-read at 0.3 m, at their measured place

Round 4's three runs (traced on 2019 0.6 m, built OUTSIDE the edge at the invented -0.5 / 1.0 m) re-read on NAIP 2023
0.3 m (`tracks/aspen/source/edges/kerbs.json`, the old values kept per run as `round4`; strips
`kerbs_blocks_2023_030_strips.jpg`, end zooms `kerbs_blocks_2023_030_ends.jpg`). Ends by eye on the end zooms (the reader
was 1-3.5 m short at L s 233's and R s 838's starts and ran past the L s 1,017 kerb's clear blocks onto a red structure
outside it); offsets by the block reader, `--follow 1`. All three lie INSIDE the live edge, not outside it:

| run | round 4 (0.1.1-0.1.2) | **round 3 (0.1.3)** |
|---|---|---|
| L | s 233-262, -0.5 .. +1.0 [invented] | **s 236-272, -1.11 .. -0.20** (block amp 27) |
| R | s 838-862, -0.5 .. +1.0 [invented] | **s 820-874.5, -1.68 .. -0.40** (block amp 30) |
| L | s 1,017-1,038, -0.5 .. +1.0 [invented] | **s 1,026-1,076, -1.28 .. -0.16** (block amp 29) |

Not built: L s 1,014-1,026 (a white band under a red structure 1-2.5 m outside the edge, no blocks along the edge at
0.3 m; in `not_built` with its reason), and L s 1,495-1,566 (round 2, Kevin's call, unchanged). `[kerbs] 3 kerb runs,
144 m ... at their measured offsets (ROAD read missed 0)` (0.1.2: 76 m outside the edge). Still:
`kerbs_built_beside_0.1.3.jpg`: each built kerb on its paint.

| Aspen (EMPTY workshop, Mac) | 0.1.2 (= 0.1.1's gates) | **0.1.3** |
|---|---|---|
| soft top / severe / bumps /km / kinks /km / vertex bumps / drops / far ledges | 0 / 0 / 0.6 / 13.26 / 41 / 0 / 0 | **the same** |
| audit (K) / verify_kn5 / kn5_ground_check (p95) / house_seat | CLEAN (0) / PASS / PASS (0.021) / PASS | the same |
| edge report: at 1 m kerb / ground; rise within 2 m p95 | 99.6 % / 0.4 %; 0.0 m | the same |
| kn5 | 7,827,187 B | **7,848,715 B (7.8 MB)** |

### 2c. Nevada: the reader would work at 0.6 m, but Nevada's kerbs do not show their blocks; nothing built, no 0.1.3

**Does 0.6 m allow it?** High Plains' 0.3 m crop box-averaged 2x2 to 0.6 m, the same calibration: raised blue / white
in p95 0.28 m, out p95 0.38 m (R s 2,892 out excluded as before), width p95 0.25 m: under the 0.4 m bar, just; every
station counted, block amplitude 13-29. (A box average is kinder than a native 0.6 m sensor; said plainly.) So the
resolution alone does not rule Nevada out.

**Nevada's kerbs on NAIP 2022 and 2019** (native 0.6 m crops, `nv_m_3611548_se_11_060_20220611`,
`..._20190706_20191118`; strips `tracks/exotics-racing-lv/source/edges/kerbs_blocks_2022_060_strips.jpg`, `_2019_`): the
six runs show as faint pinkish striated bands, not blocks. Block amplitude 8-14 (at the 8 floor; High Plains at 0.6 m
13-29), and the reader's stations count on 1-39 % of each run (2022: 44/136, 6/81, 1/51, 1/31, 6/91, 0/91; 2019: 53/136,
29/81, 3/51, 5/31, 5/91, 2/91), where every calibrated run counted 96-100 %. Outside what was calibrated, so **not
measured**: Nevada keeps 0.1.2 (0.1.1's six kerbs outside the edge at the invented -0.5 / 1.0 m). The 2013 course
imagery is 1.0 m. A ground photo or the course's own drawing would decide them (Kevin's call / owed).

### 3. High Plains 0.1.4: four blue / yellow stripes to their yellow ends, R s 2,892 to its blocks' outer edge

The five stripes' ends traced by eye on end zooms of NAIP 2023 0.3 m at 24 px/m with 1 m ticks
(`tracks/high-plains/source/edges/kerbs_stripe_ends_2023_030.jpg`, kept beside the trace; L s 690 also read back to
s 643 and R s 2,673 out to 6 m past the edge). At this scale the yellow is saturated against the tan grass at every end:

| stripe | blue (0.1.3) | **yellow ends by eye (0.1.4)** | |
|---|---|---|---|
| L s 517 | 517-537 | **512.5-541** | |
| L s 690 | 687-699 | **660.5-701.5** | the blocks run 26 m further back (pale blue the colour key missed); a white line before s 660 |
| R s 1,747 | 1,747-1,768 | **1,743.5-1,771.5** | whitish line before s 1,743 (not yellow) |
| R s 2,678 | 2,673-2,698 | **kept** | the yellow starts at ~2,668.5, but the stripe crosses 3-4 m of the line's offsets over s 2,668-2,681 (the line's edge leaves the asphalt's there); one in / out cannot place it, and paint is flat, which the block reader does not measure (item 1) |
| R s 3,013 | 3,010-3,044 | **3,006.5-3,047.5** | |

in_m / out_m stay the blue's (`s_blue` keeps the old span). And **R s 2,892's out_m +2.30 -> +1.05** (item 1: the colour
out was the dirt beyond; +1.05 is the block reader's, a raised kerb, inside the bar; `out_m_colour` kept). Not fixed and
owed: R s 2,673-2,681's first ~8 m are built at the run's median offset while the paint lies 1.5-3 m further out (the same
line divergence). The calibration record (item 1) was read against round 2's file (4b3958f6), not this one.

| High Plains (EMPTY workshop, Mac) | 0.1.1 | 0.1.3 | **0.1.4** |
|---|---|---|---|
| soft top / severe / bumps /km / kinks /km | 0 / 0 / 0 / 1.87 | 0 / 0 / 0 / 0.62 | 0 / 0 / 0 / **0.62** |
| vertex bumps / drops / far ledges / obstructed / floating | 2 / 0 / 0 / 0 / 0 | the same | the same |
| audit (K) / verify_kn5 / kn5_ground_check (p95) / house_seat | CLEAN / PASS / PASS (0.021) / PASS | CLEAN (0) / PASS / PASS (0.021) / PASS | the same |
| edge report: at 1 m strip or kerb / rise within 2 m p95 | 100 % / 0.014 m | 100 % / 0.012 m | 100 % / 0.012 m |
| kerbs | 12 runs, 243 m (round 4) | 20 runs, 526 m | **20 runs, 578 m** |
| kn5 | 15.6 MB | 15,632,786 B | **15,642,170 B (15.6 MB)** |

Stills: `kerbs_built_beside_0.1.4.jpg` (the five changed runs: aerial | built faces), each on its paint.

### 4. Grand Junction: the PC's lidar strips (4h) show no kerb; nothing built

The PC ran 4h (commit 42747ca2): `tracks/grand-junction/source/lidar/strip/R170-230.npz`, `R970-1030.npz`
(USGS_LPC_CO_MesaCo_QL2_2015, ~5,000 returns each, 0.5 m cells, about one return per cell, ~60 % of cells occupied).
Read on the Mac (`tools/lidar_strip_period.py`, new; `period_test.log` beside the strips): per offset column, the
intensity series along s, its strongest sine at a block period (1.2-3.0 m; 1.0 m is the cells' Nyquist), against the
same column shuffled 200 times.
- **No block period at the edge.** At every offset from 1.5 m inside the edge to 4 m outside, the period amplitude sits
  inside the shuffled null (p 0.31-1.0 at R s 170-230, 0.27-1.0 at R s 970-1,030; null p95 0.7-2.6k intensity units). The
  two columns under p 0.05 (-3.5 m at R s 170, +13.5 m at R s 970) are what ~40 tests give by chance, and neither is at
  the edge.
- **No paint band.** The intensity rises once, from the asphalt's ~20-21k (4 m inside to the edge) through ~24k / ~29k at
  +0.5 m to the ground's 28-33k from +1 m, and stays there: one asphalt-to-ground step 0.25-0.75 m past the line's edge,
  no band brighter or darker than both sides as a painted kerb would read. R s 170's 33k peak at +8.5-10 m is 9 m out, no kerb.

So the faint light blocks NAIP shows near R s ~200 and ~1,000 are not confirmed by the 2015 lidar (QL2: a kerb's
red / white contrast would have to exceed ~1-2.6k intensity units to show; none does). Nothing measured, nothing built;
Grand Junction stays without kerbs. A newer or denser survey, or a ground photo, is what would change that.

### Lake Murray unchanged (round 3)

`git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty (0 lines). Nothing in any
chain changed this round: `tools/kerb_offsets.py` and `tools/lidar_strip_period.py` are new tools in no chain; the ports'
configs and kerbs files are the circuits' own. `tests/run_tests.py`: 1,283 passed, 13 failed, the same 13 as on this
Mac's baseline (registry, draft_equiv, ship_track_chain, bench_pad, ship_fleet); new `tests/tools/test_kerb_offsets.py` (4).

### PC runbook 4i-kerbs (round 3)

From `D:/k10-worktrees/fleet-lm-engine` reset to `origin/claude/circuit-kerbs-lm` at **8de9fc2d or later** (nothing
merged). ENG as 4g: `eng_hplm` for High Plains, and for Aspen and Pueblo the ENG copy each one's 0.1.1 used (0078 4c). No
new texture in any ENG: Pueblo's `textures/kerb_redwhite.png` is the port's own (md5 3464f4a78bcf36acfe02b027dcdaffd4, the
same file as Aspen's), synced in by its ship.json. Nevada: nothing new (0.1.2 stands).

4i. **High Plains 0.1.4, Aspen 0.1.3, Pueblo 0.1.2**. Each, from an EMPTY workshop:
   1. Rehearsal: `SHIP_PROJ=D:/k10-scratch/<ws>_r3 AIROSO=D:/k10-worktrees/fleet-lm-engine ENG=D:/k10-scratch/<eng> bash
      tools/ship_track.sh <track> --no-install`, `<track>` / `<ws>` = `high-plains-lm` / `high_plains_lm`, `aspen-lm` /
      the Aspen workshop of 4c, `pueblo-lm` / `pueblo_lm`. Expect the Mac's rows (round 3 tables above):
      - High Plains 0.1.4: `[kerbs] 20 kerb runs, 578 m, height 0.08 m (config), at their measured offsets (ROAD read
        missed 0)`; soft 0, severe 0, bumps 0, kinks 0.62 /km, vertex bumps 2, drops 0, far ledges 0; audit CLEAN (K 0);
        verify_kn5 PASS; kn5_ground_check PASS p95 0.021; houses PASS; edge 100 % / p95 0.012; kn5 15,642,170 B.
      - Aspen 0.1.3: `[kerbs] 3 kerb runs, 144 m ... at their measured offsets (ROAD read missed 0)`; soft 0, severe 0,
        bumps 0.6, kinks 13.26 /km, vertex bumps 41, drops 0; audit CLEAN; verify_kn5 PASS; kn5_ground_check PASS p95
        0.021; houses PASS; kn5 7,848,715 B.
      - Pueblo 0.1.2: `[kerbs] 15 kerb runs, 515 m ... at their measured offsets (ROAD read missed 0)`; soft 0, severe 0,
        bumps 0.29, **kinks 8.30 /km** (0.1.1: 8.01; the one more is R s 3,275), vertex bumps 11, drops 0; audit CLEAN
        (K 0); verify_kn5 PASS; kn5_ground_check PASS p95 0.021; houses PASS; kn5 10,742,723 B.
   2. Install, replacing the same folders (`high_plains_lm`, `aspen_motorsports_park_lm`, `pueblo_motorsports_park_lm`):
      the same command without `SHIP_PROJ` and without `--no-install`, AC closed. High Plains and Aspen on the rehearsal
      matching; **Pueblo only on Kevin's word** (one kink more than 0.1.1). High Plains 0.1.4 supersedes 0.1.3 and Aspen
      0.1.3 supersedes 0.1.2 (4g's installs, if done, are simply replaced).
   3. Drive them: the kerbs now lie where the paint is, mostly over the 12 m lane's edge (inside the live edge by up to
      ~3 m at Pueblo R s 1,842 / 2,993 and High Plains R s 2,000): Kevin's drive is the judge of whether a kerb that far in
      reads right (the line's constant 12 m is wider than the asphalt there).

**PC (2026-11-05): 4g and 4i-kerbs rehearsals matched; all four INSTALLED on Kevin's word** ("All six, freeway 2a", asked
with Nevada's 19.1 MB and Pueblo's 8.01 -> 8.30 kinks said plainly). Each from a fresh real workshop (the 0.1.1 workshops
moved to `<ws>.0.1.1`), its rehearsal's ENG, every gate green, SHIP OK, no force; each installed kn5 kn5_equiv-equivalent
to its rehearsal's (tangents only). The 0.1.1 folders are parked in `D:/k10-track-archive/2026-11-05_2219xx-2223xx/`.
- Nevada Nights 0.1.2 (4b3958f6, ENG eng_nvlm): 19,109,912 B; records 9e2de8e.
- High Plains 0.1.4 / Aspen 0.1.3 / Pueblo 0.1.2 (f3a93c3f, ENG eng_hplm / eng_aslm / eng_pulm): 15,642,170 /
  7,848,715 / 10,742,723 B; records with this note. 4g's High Plains 0.1.3 / Aspen 0.1.2 were never installed.
- Not driven yet; step 3 (Kevin's drive) is open.

## Owed (start here)

(Rewritten at round 3's end; round 2's list is done or carried here.)

- **PC: runbook 4i-kerbs** (High Plains 0.1.4, Aspen 0.1.3, Pueblo 0.1.2: rehearse; install High Plains and Aspen on a
  match, Pueblo on Kevin's word). 4g's installs (High Plains 0.1.3, Aspen 0.1.2) are superseded; Nevada 0.1.2 (4g) stands.
- **Kevin's calls:**
  - Pueblo 0.1.2's one extra kink (8.01 -> 8.30 /km, R s 3,275: the 12 m lane's wheel path rides the measured kerb's
    inner edge where the ribbon and the live line diverge 1.5 m); nothing invented to hide it.
  - Round 2's still open: Nevada's 19.1 MB apron; the 4 m kerb end ramp (invented, chosen against drive_test).
  - The R s 1,014-1,026 part at Aspen (a white band under a red structure, not built) and L s 1,495-1,566 (round 2).
  - The bar used for the block reader (0.4 m p95, invented) and the one truth excluded from it (High Plains R s 2,892's
    colour out_m, the dirt; with it counted, out p95 is 1.25 m and the reader would not pass).
- **Nevada's six kerbs:** not measurable on NAIP 2019 / 2022 (faint bands, block amplitude at the floor, 0-39 % of
  stations); they stay at round 4's invented offsets outside the edge. A ground photo or the course's drawing decides them.
- **High Plains R s 2,673-2,681:** the stripe crosses 3-4 m of the line's offsets; the run's first ~8 m are built at its
  median offset, 1.5-3 m inside the paint. Flat paint is outside the block reader's calibration; a per-station colour
  follow (blue) would place it.
- **Grand Junction:** the 2015 QL2 lidar shows no kerb at R s 170-230 / 970-1,030 (no block period, no paint band); nothing
  built. Only a newer survey or a ground photo would change that.
- Round 1's carried items: Milford's ribbon creases (ledger 0078 round 4), Pikes Peak none.

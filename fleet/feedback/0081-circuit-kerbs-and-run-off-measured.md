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

## Owed (start here)

- **High Plains 0.1.2 is ready for a PC rehearsal and install** (runbook 4a's commands; ENG `eng_hplm` plus nothing new: the
  atlas is the port's own `textures/kerb_atlas_hp.png`, synced in by ship.json). Expect the table above; kn5 15.6 MB.
- **Kerb placement (all circuits):** build each run at its measured `in_m` (over the ribbon where the paint is on the
  asphalt) instead of outside the lane edge; first check what drive_test's edge wheel paths read over a raised kerb.
- **Nevada's apron:** seat the pads on the PREPPED ground (a pass after the prep, or the prep's own seat list), or drape
  them on the ground's own vertices; then `tools/apron_seat_check.py` must read ~0 % before naming them 1RUNOFF. Check
  0.1.1's PADAPRON pads the same way.
- **Pueblo:** the span-by-span pass High Plains got (scan + block finder → edge_sheet zooms → `tools/kerb_spans.py
  --spans ... red_white`), then `route.kerbs_file`, a `kerb_redwhite` texture and a build.
- **Aspen:** the same pass for its four runs' true extents; ask Kevin about L s 1,495-1,566.
- **Grand Junction:** a ground photo or lidar intensity at s ~200 / ~1,000 (right edge) before anything is built.

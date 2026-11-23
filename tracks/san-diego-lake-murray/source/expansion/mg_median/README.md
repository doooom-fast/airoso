# Mission Gorge Rd's raised median, measured (ledger 0099 round 3, 2026-11-23)

The measurements behind three items of Lake Murray's round 3: item 1 (the median's top is terracotta pavers, not grass),
item 1b (the island as the plan declares it runs across a real intersection) and item 2 (the J3 end of the median
stands about 13 m from where it really is; and the whole island is narrower than declared and off its place).

**What is built is the lidar's.** The G10 read the island's two curb faces, and the road's two outer curbs, off the
USGS 2024 lidar at every 2.5 m station (`mg_median_faces_g10.py` -> `mg_median_faces.lidar.g10.json`, s 25-300 and
930-1260, and `mg_median_faces_full.lidar.g10.json`, s 225-2245; `mg_median_faces.lidar.g10.md` is its method and its
checks). `fix_mg_median.py` sets the plan's rows from those two files and `mg_plants_data.py` the plants; nothing here
touches the scene.

**The photo came first, and my correction of it was wrong.** The sections from "What the photo shows" down are the
NAIP 2022 readings items 1 and 1b were first built on. They are kept as the record: the colour evidence (terracotta, not
grass; a real crossing) stands, and so do the raw readings. The numbers the first build took from them do not; see "The
photo method, and where it went wrong".

The photo is `tracks/san-diego-lake-murray/source/naip_2022_lm_full_z18.jpg` + `.georef.json` (USDA NAIP, flown
2022-04-25, about 0.50 m per pixel; Git LFS, sha256 `1764a80b...`, branch `claude/lm-naip-full-20261123` until that
branch is merged). The islands are `medians[].polygon_xz` of `data/expansion.north.json`: side A's stations, then side
B's reversed, 2.5 m apart along piece C (Mission Gorge Rd, J3 to J4). A point goes to a pixel exactly as
`tools/measure_median_tone.py` does it. Everything below is in piece C's frame: metres off its line, + = left of J3 ->
J4 travel = north-west.

## What is built: the lidar's faces (`fix_mg_median.py`, `mg_median_correction.json`)

A face is placed between the two neighbouring returns where the fewest fall on the wrong side; its +- is half that gap,
a median 0.03 m. Not measured there: the lidar's absolute horizontal accuracy (the NAD83(2011) -> WGS84 step is the null
transform, stated to 2 m).

| | the plan | the lidar |
|---|---|---|
| MD11, s 45-100 | 0.6-1.2 m wide on the line (-0.5) | 1.25 m wide, its middle -1.0 |
| MD11, s 102.5-130 | straight on | runs diagonally north-west, its middle -0.8 -> +2.65 |
| MD11, s 132.5-182.5 | ends at s 167.5 | faces +3.34 / +2.02: 3.2 m north-west of the declared band; last island station s 182.5 (a 0.61 m nose) |
| the first opening | s 167.5-182.5 | s 185-192.5 (four stations with none) |
| MD12 | s 182.5-195, 1.7 m wide | **s 195-207.5**, up to 3.6 m wide, its middle +1.14 |
| the second opening | s 195-210 | s 210-220 (five stations with none) |
| MD13's start | s 210 | a nose at s 222.5, an island from s 225, 1.26 m wide |
| MD13, s 285-310 | 2.5-3.0 m wide | widens 1.37 -> 4.77 m |
| the crossing | one island straight across | **no median s 1087.5-1112.5**; strip A (s 1012.5-1077.5) 1.24 m wide; strip B (s 1127.5-1192.5) 1.30 m wide, 2.3 m right of the line |
| MD13b, s 1850-2000 | widens to 7.1-8.0 m | 4.8-5.4 m: the widening is not real |
| MD13b, s 2152.5-2177.5 | 3-4 m wide to its end | narrows 4.3 -> 3.6, then 1.1-1.4 m wide from s 2177.5 to its end |
| the whole of MD13 / MD13b (747 island stations) | | **0.73 m narrower** than declared; its top 0.152 m over the road |

**How a row is set.** The lidar calls each station island, none or unclear.

- **island:** the two faces, each the median of its own station and the two beside it in the same island (a face off by
  one return's spacing at one station does not kink the curb; a ramp keeps its shape). Width = left - right.
- **none:** no median. The row's offset runs straight from the middle of the island before to the middle of the island
  after, so the lane lines do not jog across the opening **[inferred: there is nothing to measure]**.
- **unclear** (55 stations: a top just under 0.10 m, a nose, a taper, vegetation on the top, one face flush with a turn
  pocket): the Mac's rule was "use the photo there, or the nearest clear lidar, and say which". All 55 take **the
  nearest clear lidar**: a raised station if the nearest clear station on either side is an island, its faces drawn
  straight between the clear island stations either side of it (a nose takes the station beside it). The record lists
  each (`lidar.unclear`). The longest run is s 2162.5-2175, where the island tapers to its last narrow stretch.

881 rows of piece C (s 45-2245) are set; every one changes; 20 have no median. The islands: **MD11 s 45-182.5, MD12
s 195-207.5, MD13 s 222.5-1085 and MD13b s 1115-2245** (MD13b is new, so no other median's id moves). Each ring is
re-cut by the generator's own nose rule. The island and the paint of `north_mission_gorge` are
`tools/expansion_pieces.decorate`'s own output for piece C: islands on connector points 8-53, 67-354 and 365-741, and
MD12's four points 58-61, which are no island; 733 of the 746 points change. The two centre lines decorate's rule draws
where a road has no median are cleared at the 17 points with none (34 offsets; the photo shows no yellow there).
Idempotent: a further run leaves all four files byte-identical. The record keeps every declared value it replaced.

**Owed, and why.**

- **MD12** is 12.5 to 17.5 m long. Four connector points lie inside it; the median tool builds an island on six or
  more, and so does the lap's corridor. The Mac's rule: only on measured rows, never lengthened, no denser rows for this
  island alone. What is set is its PLACE: the plan's painted outline lies where the real island stands.
- **MD11 before s 45.** The lidar has the island from s 25 (1.0-1.3 m wide, its middle about -1.2; the J3 pad cuts at
  s 24.74). Tried on a scratch copy, the corridor tool refuses it: "v718 is not the first vertex of an authored island
  run", and the closure's pin at v712-713 goes to 1:0.17 with a 9-10 m plan radius (its limits: 1:3 and 20 m). It needs
  the J3 corner re-declared. Not forced: rows before s 45 keep the plan's values (`HOLD_BEFORE_S`).

## Where in the road the island goes (the 50 m bins)

The island's WIDTH needs no frame. Its PLACE does, and the plan's road is not a survey: its two edges are eye readings
on NAIP every 250 m, +-1.0 to 1.5 m each, and its median was declared on the middle between them. So "the island is
0.7 m south-east of the declared band" can mean the island is off in the road, or the road is off in the world. The
G10's outer curbs settle it per 50 m (its `reads`; 0.30 m **[invented]** as the line; both curbs read at 399 stations):

- over **s 1250-2000** both of the plan's curbs sit 1.6-3.0 m north-west of the real ones. The real road is about as
  wide as planned but displaced, and the real island stands within 0.6 m of the real road's middle;
- over **s 1100-1200** (strip B) the plan's edges are right, and the island is off in the road, as strip B really is.

**The rule (the Mac, 2026-11-23).** Width: the lidar's everywhere. Place, per bin:

| the bin reads | bins | the island's middle |
|---|---|---|
| the road edges are where the plan has them | 6 | the lidar's own place |
| the plan's road edges are off (or both off) | 28 | measured from the REAL road's middle, set from the PLAN's road's middle: lidar middle - (real road middle - plan road middle). The lane room either side is then the real one, inside a road that is itself misplaced |
| too few stations with both curbs read | 7 | **[inferred: interpolated]** the shift drawn straight between the nearest called bins either side; the lidar's width and shape kept (s 400, 750, 850, 900, 1500, 1850, 2000) |

A bin's rule holds at the bin's centre and is drawn straight to the next bin's centre, inside one island, so the curb
never steps sideways at a bin's edge (neighbouring bins differ by up to 1.5 m). Nothing is drawn across a real gap:
strip A keeps its bin's shift to its nose and strip B starts on its own. The first form of the rule gave a too-few bin
the plan's own middle; that swings the island off its line and back between called neighbours (by up to 1.95 m, at
s 772.5; over 0.3 m at 172 stations), which is not on the ground.

**The J3 end (MD11, MD12; s 45-207.5) stays at the lidar's own place.** The bins there are not sound: on the
north-west side the "edge" readings are the side street's mouth and a bank, not a curb (s 150-197.5: 0 curbs, 11 edges,
2.2 m outside the plan's). The south-east curb reads clean and within 0.33 m of the plan's over s 100-200. And the
plan's middle cannot carry MD11's 3.2 m veer. For the road-edge round: over s 50-100 the plan's south-east edge is
1.27 m too far out (16 curb stations).

**What it does.** Over MD13 / MD13b the island is set a median 1.65 m north-west of where the lidar has it (from
2.93 m north-west to 1.71 m south-east), because the plan's road is that far off the real one. Against the plan it is a
median 0.70 m narrower and 1.07 m north-west. Checked at the 374 stations where the island and both real curbs read,
lane room as built minus the real one:

| the island at | north-west side | south-east side |
|---|---|---|
| this rule | -0.15 m (p10 -1.44, p90 +0.48) | -0.18 m (p10 -1.41, p90 +0.29) |
| the lidar's own place, everywhere | +1.41 m | -1.74 m |
| the plan's place (0.20.5) | +0.11 m | -1.44 m |

Painted lanes (decorate spreads 3 + 3 evenly and drops to 2 under a 2.9 m lane): the plan had 2 instead of 3 on one
side at 220 station-sides (the south-east side over s 1585-2020, 435 m, and the north-west over s 465-520 and
952-1005). It is 111 now (north-west s 345-362.5, 755-827.5, 897.5-1010; south-east s 2000-2042.5, 2060-2080), all
where the plan's road is narrower than the real one. Those go with the road's edges.

**Owed: the road's edges.** Re-fitting piece C's edges to the measured curbs moves a six-lane road 1.6-3.0 m over
about 750 m. That is its own round (the ledger has its blast radius).

## The photo method, and where it went wrong

The photo readings below are per station the **equivalent width** (the excess R - G over the asphalt's, summed across
the island, over a full island's plateau) and that excess's **centroid**. Raw, they agree with the lidar: strip B's
middle -2.24 against -2.32; within 0.22 m on the reference stretches; MD11's veer, the two openings and MD12 where the
lidar has them.

What I added to them was wrong. To take out the photo's blur and registration I measured its bias "where the island
fills its declared band" (s 930-985 and 1215-1260: width 0.30 m short, middle 0.49 m right) and added both back. **The
island does not fill that band.** The lidar has it there 0.61 m narrower and 0.86 m right of it, over 41 stations. So
the 0.30 m and 0.49 m were the island's real difference from the plan, read as an error of the photo, and the
correction moved good readings off. The first build of item 1b made the strips beside the turn pockets **1.96 and
1.84 m wide, with their middles 0.70 and 0.58 m left of where the lidar has them**; they are 1.24 and 1.30 m. It was
not installed, and not rehearsed.

Two smaller things the lidar put right. MD11 runs to s 182.5, not 177.5: the terracotta stops at s 177.5 and a paler
strip runs on along the same line (R - G +0 to +4, which the measure does not count); that is the island's plain nose.
And the crossing's gap ends at s 1112.5, not 1117.5: strip B's nose starts 2.5-5 m earlier than the photo's.

## What the photo shows

| | |
|---|---|
| MD13 (piece C s 210-2245), whole island | terracotta: 28,392 of 32,153 inset pixels kept, mean 147.9 / 127.8 / 115.6 (`assets/textures/terracotta_paver.md`) |
| MD13 in 50 m bins (`md_bins_50m.json`, measured on the Mac with the tool's own masks) | kept pixels read R - G +13 to +27 over s 260-1010 and s 1210-2245; no bin is planted end to end (highest canopy share 0.27, at s 710-760 and s 1560-1610) |
| MD13 s 1010-1210, the four bins that read grey (R - G +10.7 / +3.5 / +4.7 / +7.1) | NOT grey paving: asphalt inside the declared band (below) |
| MD11 (piece C s 45-167.5, 0.57-1.62 m wide) | reads near-grey (R - G +8.4 / +0.8 / -2.8), for two reasons. Over s 45-105 the strip is narrower than the photo's colour resolution (one colour sample per about 1 m). Over s 105-167.5 the declared band is not on the real strip, which runs up to 3.8 m to its left (item 2, below). CORRECTED 2026-11-23: item 1 first gave the resolution as the only reason. Terracotta as the plan declares; its tone is [inferred from MD13] either way |
| MD12 | not sampled: its declared 12 m lie on the first opening's asphalt (`terracotta_paver.md`); the real island stands at s 195-207.5 (item 2) |

So item 1 builds both built islands terracotta over their whole length, with no grass stretch and no concrete stretch.
The plants keep their measured places.

## The grey stretch: a real intersection (item 1b)

Looked at (`md13_s1010-1110.png`, `md13_s1110-1210.png`: the photo at 5x with MD13's declared ring in cyan) and measured
station by station across the declared band (`profile_md.py` -> `md13_profile_s980-1240.json`; `gaps_md.py` ->
`md13_gaps.json`, the whole island, samples every 0.25 m):

- **s 1087.5-1107.5: no terracotta at all** on lit stations. The photo shows marked crosswalks on all four legs of a
  crossing; the median's noses stand at about s 1087 and s 1120. For about 33 m there is no median.
- **s 1012-1078 and s 1132-1193**: a strip much narrower than the declared band, beside a left-turn pocket each side
  of the crossing. This first look read them off a threshold as 1.75-2.5 m and about 2.25 m with a 2 m offset; those
  figures are **replaced** by the measurement in the next section.
- Everywhere else on MD13 the terracotta fills the band. The only other run with none is the first 15 m, the 0.6-1.9 m
  nose, too narrow to read.

"Terracotta" in these two scripts is R - G >= 10 on the 8-bit values. That number is **[invented]**: a look aid between
the asphalt's own value there (about -2 to -4) and the terracotta's (+13 to +27), not a gate and not a measured split.

## The faces off the photo (`faces_md.py`): the first build's numbers, superseded by the lidar

*Kept as the record of what item 1b was first built on. The strips' widths and middles in this section carry the
+0.30 m / +0.49 m that should not have been added (above); the lidar's are in "What is built".*

A 2 m strip is four pixels on this photo, and the mosaic stores one colour sample per about 1 m, so a face is not read
off a threshold. Two quantities survive the blur: the **equivalent width** (the excess R - G over the asphalt's, summed
across the island, divided by what a full island reads: +24.0 against the asphalt's -1.0) and that excess's
**centroid**. Per station of piece C, samples every 0.25 m; stations under canopy or shadow are left out.

- **The method is checked where the island fills its band** (37 stations of s 930-985 and s 1215-1260): there it reads
  the width 0.30 m short and the middle 0.49 m right of the declared band. Both are added back, so the corrected
  stretch meets the unchanged island without a step. One station scatters p10..p90 -1.41..+1.23 m in width and
  -0.94..+0.18 m in the middle on those stretches.
- **Strip A, s 1010-1085** (24 stations): 1.66 m + 0.30 = **1.96 m wide**, its middle **0.43 m left** (north-west) of the
  line the full island's middle follows. Its right face comes in about 1.8 m (the pocket) and its left about 1.0 m; the
  close-up `md13_s1015-1075.x10.png` shows asphalt inside the declared band on both sides.
- **Strip B, s 1120-1192.5** (26 stations): 1.54 m + 0.30 = **1.84 m wide**, its middle **1.50 m right** (south-east).
  Its right face then lies within 0.1-0.2 m of the declared right face and its left comes in 3.1 m: one lane, the pocket.
- **No median s 1087.5-1117.5** (13 stations; noses at s 1085 and s 1120).
- **Tapers** s 982.5-1010 and s 1192.5-1212.5, linear to the declared band. The second lies under tree shadow on the
  photo: its two ends are measured, the line between is **[inferred]**.

By count alone each strip's width holds to about +-0.15 m and its middle to about +-0.12 m. What the method does on a
strip narrower than the photo resolves, beyond that, is not measured. The USGS lidar's ground returns across the median
would measure the faces directly; the lidar is on the G10 and was not read for this.

**The centre line through the crossing: none** (source: the photo). Within 3 m of the declared centre over s 1090-1112.5
the yellowest pixel reads (R + G) / 2 - B = +3.5 to +7.5, the asphalt 5-8 m either side +1.5 to +5.5. What a double
yellow reads at this resolution was not measured on this photo, so this is "no yellower than the asphalt", not a
threshold passed.

## The J3 end off the photo (item 2; `faces_piece.py` -> `pieceC_faces_s40-250.json`): superseded by the lidar

*Kept as the record. No correction was added to these readings, and the lidar agrees with them to the photo's own
error, except at MD11's end (s 182.5, not 177.5: the plain nose).*

Looking for the plan's short island MD12 showed the whole J3 end of the median standing off the photo. The same measure
as above, per 2.5 m station and in 10 m windows, but off the piece's declared centre (there is no ring to follow where
the plan has an opening). **No registration correction is applied here**: no full-width island stands near enough to
take one from, so the lateral figures hold to about +-0.75 m (the Mac's registration range for this mosaic). Centres
are off the DECLARED centre, + = left = north-west:

| s | the plan | the photo |
|---|---|---|
| 40-100 | MD11, 0.6-1.2 m wide | a strip 0.5-1.1 m wide on the declared centre (-0.4 to +0.3) |
| 110-178 | MD11 to s 167.5, then an opening | the strip leaves the declared line to the LEFT: +1.12 at s 110, +1.98 at 120, +3.17 at 130, +3.76 at 140 and 150, +3.39 at 160, +3.40 at 170; its last station with terracotta is s 177.5; 1.1-1.5 m wide with the +0.30 |
| 180-192.5 | the opening's end, then MD12 (s 182.5-195) | **no terracotta** at any of the six stations: the first real opening |
| 195-207.5 | MD12's end, then an opening (to s 210) | **the real MD12**: 1.02 / 2.73 / 3.79 / 3.45 / 3.10 / 2.60 m wide station by station, its middle +0.90 / +1.18 / +1.73 / +1.34 / +2.20 / +2.36 |
| 210-222.5 | MD13 from s 210 | **no terracotta** at any of the six stations: the second real opening |
| 225 on | MD13 | a strip 1.0-1.4 m wide, 0.3-0.8 m right of the declared centre (inside the lateral error): MD13's real start |

**What the first build took from it** (the checkpoint commit d54f3909; not what is built now): MD11 leaves its declared line from s 100 and stands **3.6 m left** of it from
s 136 to its end at **s 177.5**, one straight line through the four measured windows, at its declared width; no median
s 180-192.5 and s 210-222.5; **MD12 at s 195-207.5, 3.40 m wide** (the middle five stations' median 3.10 + 0.30), its
middle 1.0 m left at s 195 and 2.3 m left at s 207.5; MD13 from **s 225**, as declared from there.

**The likely cause**: `tools/author_expansion.py` places the two openings at 174 and 202 (GAPS, "dossier st 174 / 202").
The dossier's station labels run about 14.6 m ahead of s on this piece ("C st 250" is s 235.37), and 202 - 14.6 = 187.4
is the middle of the first real opening. That is a reading of two numbers, not traced in the dossier.

**MD12 is not built; it is owed.** The real island is 12.5 to 17.5 m long (its ends lie between s 192.5 and 195 and
between s 207.5 and 210). The connector has four points inside its measured run (s 196.3, 199.3, 202.3, 205.3; a fifth,
s 208.3, inside its outer bound). The median tool builds an island on six points or more, and so does the lap's
corridor. The Mac's rule (2026-11-23): only on measured rows, never lengthened, and no denser rows for this island
alone, because the corridor reads one island point per connector vertex and its K-rail would not know the island is
there. What the correction sets is MD12's PLACE: the plan's painted outline (two edge lines round a run too short to be
an island, as the plan's own MD12 was) now lies where the real island stands, instead of on the opening.

**The centre line in the two openings: none** (source: the photo). Within 4 m of where the islands either side stand,
s 187.5-192.5 and s 212.5-217.5 read (R + G) / 2 - B = +4.0 to +5.5 against the asphalt's +2.0 to +4.5. The stations
beside the noses read +8 to +14 on light grey pixels (red, green and blue within 16 of each other): not yellow.

**Compared with the lidar** (the Mac's rule: where they differ by more than the photo's stated error, the lidar's).
Put in the piece's frame, the photo's middles stand 0.15-0.35 m north-west of the lidar's along MD11 and MD12 and
0.21 m south-east of it at MD13's start: inside the photo's +-0.75 m. Its widths read 0.0-0.4 m under the lidar's. What
differs is MD11's end (s 182.5, not 177.5: the plain nose), and with it the first opening (s 185-192.5); the second is
s 210-220, MD12 is s 195-207.5 and up to 3.6 m wide, and MD13's nose is at s 222.5.

## The scene (`tools/author_median_rebuild_blend.py`, author step `median_rebuild`)

Lake Murray never runs its draft again, so the islands are re-authored in the committed scene. The two islands the
blend holds on the line (MD11, rows 8-48; MD13, rows 63-741) are each found exactly as the record's data built them:
curb 246 and 4,074 vertices in CURB, deck 82 and 1,358, beams 140 and 2,692 and 235 posts in GUARDRAIL, 693 + 1,480
paint strips, every vertex within 2 mm of the rule's own, or the step refuses. They are taken out, and the three islands
the corrected data holds are built by the same rule (`tools/median_island.py`, the rule the draft tool builds with):
curb 276 / 1,728 / 2,262 vertices, deck 92 / 576 / 754, beams 160 / 1,128 / 1,484, 230 posts; the 716 + 1,428 changed
paint strips by the assembler's own paint function. The new decks stand 0.173-0.202 m over the road.

## The plants (`mg_plants_data.py`, `mg_median.median_spots.json`, `mg_plant_tops.g10.json`)

The median's plant spots are the draft's own, drawn on the island as the plan declared it. 329 of them stand on
Mission Gorge's island:

- **226 lie on the new deck** and stay where they are.
- **97 are dropped** (77 on pavement beside the island, 15 on a curb ring, 5 between the crossing's noses). Every one is
  bare on the lidar (under its 0.3 m floor): no plant the lidar saw is dropped.
- **6 have a plant on the lidar and the deck no longer reaches them** (spots 846, 852, 857, 862, 871, 888; 0.68 to
  5.46 m tall; none is 10 m or taller). The Mac, 2026-11-23: "a real plant the lidar saw is never dropped because the
  island moved under it" (Kevin, 2026-11-18: "we've reduced lake murrays center bushes far too much"). They are MOVED
  (`tools/make_treefx.py` `scenery.treefx.median_spots` "move", new):
  - **rule (3), three of them** (852, 857, 871): the lm-shrub plant top within 2 m (tops 400701, 401191, 403275, read by
    the Mac off the G10's `lm_shrub.tops.npz`): the spot takes the top's own place, a measured place. All six stand at
    s 745-996, where the island is set from the plan's road, so the top is carried across by the same shift the island
    was given (1.69-1.89 m) and the plant keeps its place ON its island.
  - **rule (2), the other three:** straight across onto the deck, 0.3 m inside its edge, an **[inferred position]**.
    Spots 862 and 888 have no plant top within 2 m; spot 846's top, carried across, lands off the deck.
  - They move 0.44 to 1.53 m. Each keeps its own lidar height (`source/vegetation/median_heights.lidar.json` stays the
    one source of heights).
- A spot with a plant where there is no island at all (between two noses) is FATAL in the script: that would mean the
  gap is wrong. There is none.

Why the plan has the crossing so: piece C's `median_w_m` is linear between eye readings every 250 m (st 1000: 4.5 m,
st 1250: 5.5 m), and the plan holds no side road there.

## The crossing

`osm_near.py` on the track's own extract (`data/osm.expansion.json`, osm_base 2026-10-14) -> `crossing_s1103.osm.json`.
At OSM node 1484501863 (lat 32.80958, lon -117.06795; piece C s about 1103):

- **Margerum Avenue**, way 135149732: `highway=tertiary`, 2 lanes, 2,015 m long, leaves on bearing 142 (south-east).
- **Mission Vista Drive**, way 5977531: `highway=residential`, 878 m long, leaves on bearing 311 (north-west).

Neither carries an access tag: both are public streets. The nearest private service ways are 50-70 m away and no part of
the crossing.

**The network already has both side streets as stubs** (ledger 0054 phase 5, `data/stubs.plan.json`, built and verified:
`data/stubs.built.json`, `data/verify_stubs.json`): `mission_vista_drive_5977531_L` at host segment 361 of
`north_mission_gorge` (left, 10.0 m wide, the class default [invented]) and `margerum_avenue_135149732_R` at host segment
362 (right, 9.6 m from OSM's two lanes [invented]), each 15 m long with a K-rail across it. So nothing is owed there but
the median itself: the island as built runs unbroken between the two mouths. (CORRECTED 2026-11-23: my first reading said
the network had nothing at the crossing and owed two stubs. I had read only `data/expansion.north.json`'s `stubs`, which
are the junction pads' arms S1-S6, and not the side-road stubs' own plan.)

Whether the crossing is signalised is **[inferred]** from its crosswalks: the extract holds no tagged node within 70 m,
and Phase 3's fresh signal query box ends at lon -117.068, about 5 m west of this node.

## Re-run

```bash
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/gaps_md.py . <mosaic.jpg> <georef.json> MD13 131.7
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/profile_md.py . <mosaic.jpg> <georef.json> MD13 980 1240
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/crop_md.py . <mosaic.jpg> <georef.json> MD13 1010 1110 out.png --ring
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/osm_near.py . MD13 1103
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/faces_md.py . <mosaic.jpg> <georef.json> --from 960 --to 1240
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/faces_piece.py . <mosaic.jpg> <georef.json> C 40 250 <the declared expansion.north.json>
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_median_faces_g10.py <tiles> <lm-shrub tool> <airoso> <out>   # the G10: the lidar's faces (its .md)
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/fix_mg_median.py            # the table; --write applies it
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_plants_data.py           # the plants; --write
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/props_on_islands.py . <project before> <project after>
```

`gaps_md.py`, `profile_md.py` and `faces_md.py` read MD13's ring as it was declared (one ring, s 210-2245), and
`faces_piece.py` the declared rows: run them on the data before the correction (git: 366a5a4c) to reproduce the
photo's numbers. The `*_scratch.json` files are what the scratch chain runs measured (item 1; item 1b on the photo fit;
the lidar build), and `crossing_before_after*.png` / `j3_before_after.png` the scene before and after, beside the photo.

131.7 is MD13's own median luminance after the canopy cut (`md_bins_50m.json` `shadow_ref_lum`), the reference of the
tool's shadow rule. Pillow only; no numpy.

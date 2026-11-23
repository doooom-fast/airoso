# Mission Gorge Rd's raised median, read off the aerial (ledger 0099 round 3, 2026-11-23)

The measurements behind three items of Lake Murray's round 3: item 1 (the median's top is terracotta pavers, not grass),
item 1b (the island as the plan declares it runs across a real intersection) and item 2 (the J3 end of the median
stands about 13 m from where the photo has it). The measuring scripts read; `fix_mg_median.py` and `mg_plants_data.py`
write the corrected data and its records; nothing here touches the scene.

The photo is `tracks/san-diego-lake-murray/source/naip_2022_lm_full_z18.jpg` + `.georef.json` (USDA NAIP, flown
2022-04-25, about 0.50 m per pixel; Git LFS, sha256 `1764a80b...`, branch `claude/lm-naip-full-20261123` until that
branch is merged). The islands are `medians[].polygon_xz` of `data/expansion.north.json`: side A's stations, then side
B's reversed, 2.5 m apart along piece C (Mission Gorge Rd, J3 to J4). A point goes to a pixel exactly as
`tools/measure_median_tone.py` does it.

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

## The faces, measured (`faces_md.py` -> the fit in `fix_mg_median.py`)

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

## The J3 end, measured (item 2; `faces_piece.py` -> `pieceC_faces_s40-250.json`)

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

**Built from it** (`fix_mg_median.py`): MD11 leaves its declared line from s 100 and stands **3.6 m left** of it from
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

**To be compared with the lidar.** The Mac started a job on the G10 (2026-11-23) that reads the island's curb faces
directly off the 2024 lidar's ground returns, every 2.5 m over s 40-250 and s 980-1215. Where it differs from the photo
by more than the photo's stated error (+-0.15 m in width at the crossing, +-0.75 m laterally at the J3 end), the
lidar's figure replaces the photo's.

## The correction (`fix_mg_median.py`, `mg_median_correction.json`)

The MD7 precedent (`source/expansion/phase2/fix_pv_median.py`), one script for both places. It is driven by two tables:
the stretches of s whose rows take the fit (s 100-231 and s 982.5-1212.5) and the islands the piece holds after it.

- **The rows.** 146 piece-C rows lie in the stretches and 140 change (91 at the crossing, 49 at the J3 end); 25 lose
  their median (13 between the crossing's noses, 6 in each real opening).
- **The medians.** MD11 s 45-177.5, MD12 s 195-207.5, MD13 s 225-1085 and a new **MD13b** s 1120-2245, so no other
  median's id moves. Each ring is re-cut inside the stretches by the generator's own nose rule and kept point for point
  outside them: 735 ring stations are the generator's own points (22 of MD11, 300 of MD13, 413 of MD13b).
- **The island and the paint** of `north_mission_gorge` are `tools/expansion_pieces.decorate`'s own output for piece C
  (decorate reproduces Mission Gorge's committed record exactly, so nothing rides along): 116 points change (26-51,
  54-61, 63-67 and 321-397); islands on points 8-51, 68-354 and 367-741, and MD12's four points 58-61, which are no
  island. Every other piece's record is identical.
- **The centre lines** decorate's rule draws where a road has no median are cleared at the 20 points with none
  (53-57, 63-67 and 356-365: 40 offsets). The photo shows no yellow there.
- Idempotent: a further run leaves all four files byte-identical. The record keeps every declared value it replaced
  (the rows, the island's points, the paint's offsets, the three rings' extents).

## The scene (`tools/author_median_rebuild_blend.py`, author step `median_rebuild`)

Lake Murray never runs its draft again, so the islands are re-authored in the committed scene. The two islands the
blend holds on the line (MD11, rows 8-48; MD13, rows 63-741) are each found exactly as the record's data built them:
curb 246 and 4,074 vertices in CURB, deck 82 and 1,358, beams 140 and 2,692 and 235 posts in GUARDRAIL, 114 + 250
paint strips, every vertex within 2 mm of the rule's own, or the step refuses. They are taken out, and the three islands
the corrected data holds are built by the same rule (`tools/median_island.py`, the rule the draft tool builds with):
curb 264 / 1,722 / 2,250 vertices, deck 88 / 574 / 750, beams 152 / 1,124 / 1,476, 228 posts; the 115 + 188 changed
paint strips by the assembler's own paint function.

## The plants (`mg_plants_data.py`, `mg_median.median_spots.json`)

39 of the median's plant spots stand on the changed points, all of them at the crossing: no spot stands on the J3 end's
narrow islands. 18 lie on the new deck and stay where they are. **21 are dropped** (6 between the noses, 14 on pavement
beside the island, 1 on a strip's curb ring); none is moved. Every dropped spot is bare on the lidar (0.04-0.25 m, under
its 0.3 m floor): no plant the lidar saw is lost, and the script refuses to drop one it did see, because that would mean
the outline is wrong.

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
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/fix_mg_median.py            # the table; --write applies it
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_plants_data.py           # the plants; --write
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/props_on_islands.py . <project before> <project after>
```

`gaps_md.py`, `profile_md.py` and `faces_md.py` read MD13's ring as it was declared (one ring, s 210-2245), and
`faces_piece.py` the declared rows: run them on the data before the correction (git: 366a5a4c) to reproduce the
numbers above. The `*_scratch.json` files and the two
`crossing_before_after*.png` pictures are what the scratch chain runs of items 1 and 1b measured.

131.7 is MD13's own median luminance after the canopy cut (`md_bins_50m.json` `shadow_ref_lum`), the reference of the
tool's shadow rule. Pillow only; no numpy.

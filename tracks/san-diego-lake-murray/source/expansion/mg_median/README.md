# Mission Gorge Rd's raised median, read off the aerial (ledger 0099 round 3, 2026-11-23)

The measurements behind two items of Lake Murray's round 3: item 1 (the median's top is terracotta pavers, not grass)
and item 1b (the island as the plan declares it runs across a real intersection). Everything here reads; nothing here
builds.

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
| MD11 (piece C s 45-167.5, 0.57-1.62 m wide) | reads near-grey (R - G +8.4 / +0.8 / -2.8): the strip is narrower than the photo's colour resolution (one colour sample per about 1 m). Terracotta as the plan declares; its tone is [inferred from MD13] |
| MD12 | not sampled: its declared 12 m lie on the crossover's asphalt (`terracotta_paver.md`) |

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

## The correction (`fix_mg_median.py`, `mg_median_correction.json`)

The MD7 precedent (`source/expansion/phase2/fix_pv_median.py`): the fit set on piece C's rows over s 982.5-1212.5 (91
rows change; 13 lose their median); **MD13 now ends at s 1085 and a new MD13b runs from s 1120**, so no other median's id
moves (722 ring stations as they were, 80 moved, 13 gone); `north_mission_gorge`'s island and paint are
`tools/expansion_pieces.decorate`'s own output for piece C (77 points change, 321-397; islands on points 8-48, 63-354,
367-741; every other piece's record identical). The two centre lines decorate's rule draws where a road has no median
are cleared at the ten points between the noses. Idempotent: a further run leaves all four files byte-identical.

## The scene (`tools/author_median_rebuild_blend.py`, author step `median_rebuild`)

Lake Murray never runs its draft again, so the island is re-authored in the committed scene: the old island of rows
63-741 is found exactly as the record's data built it (curb 4,074 vertices in CURB, deck 1,358, beam 2,692 and 224
posts in GUARDRAIL, 74 + 156 paint strips: every vertex within 2 mm of the rule's own, or the step refuses), taken
out, and the two islands built by the same rule (`tools/median_island.py`, the rule the draft tool builds with) and
the assembler's own paint function.

## The plants (`mg_plants_data.py`, `mg_median.median_spots.json`)

39 of the median's plant spots stand on the changed stretch. 18 lie on the new deck and stay where they are. **21 are
dropped** (6 between the noses, 14 on pavement beside the island, 1 on a strip's curb ring); none is moved. Every
dropped spot is bare on the lidar (0.04-0.25 m, under its 0.3 m floor): no plant the lidar saw is lost, and the script
refuses to drop one it did see, because that would mean the outline is wrong.

Why the plan has it so: piece C's `median_w_m` is linear between eye readings every 250 m (st 1000: 4.5 m, st 1250:
5.5 m), and the plan holds no side road there.

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
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/fix_mg_median.py            # the table; --write applies it
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_plants_data.py           # the plants; --write
python -I tracks/san-diego-lake-murray/source/expansion/mg_median/props_on_islands.py . <project before> <project after>
```

`gaps_md.py`, `profile_md.py` and `faces_md.py` read MD13's ring as it was declared (one ring, s 210-2245): run them on
the data before the correction (git: 366a5a4c) to reproduce the numbers above. The `*_scratch.json` files and the two
`crossing_before_after*.png` pictures are what the scratch chain runs of items 1 and 1b measured.

131.7 is MD13's own median luminance after the canopy cut (`md_bins_50m.json` `shadow_ref_lum`), the reference of the
tool's shadow rule. Pillow only; no numpy.

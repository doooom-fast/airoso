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
- **s 1012-1078**: the real median is a strip 1.75-2.5 m wide, about centred, in a declared band 4.6-4.8 m wide (a
  left-turn pocket takes the rest).
- **s 1132-1193**: a strip about 2.25 m wide whose middle sits about 2 m toward the ring's second side (south-east),
  partly outside the declared edge; the band is 5.1-5.3 m there.
- Everywhere else on MD13 the terracotta fills the band. The only other run with none is the first 15 m, the 0.6-1.9 m
  nose, too narrow to read.

"Terracotta" in these two scripts is R - G >= 10 on the 8-bit values. That number is **[invented]**: a look aid between
the asphalt's own value there (about -2 to -4) and the terracotta's (+13 to +27), not a gate and not a measured split.

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
```

131.7 is MD13's own median luminance after the canopy cut (`md_bins_50m.json` `shadow_ref_lum`), the reference of the
tool's shadow rule. Pillow only; no numpy.

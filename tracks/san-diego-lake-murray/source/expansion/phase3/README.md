# Lake Murray Phase 3: measured data for the three new roads

Data for [`EXPANSION-PHASE3-PLAN.md`](../../../EXPANSION-PHASE3-PLAN.md) (revision 2), measured 2026-11-23 for ledger
[0099](../../../../../fleet/feedback/0099-lake-murray-to-finished.md) ("Phase 3 is part of finished"). It holds the
same kinds of file Phase 2 has in `source/expansion/`, under the same names, for the three Phase 3 legs. These are
data files only. Nothing here is geometry, and nothing under `data/`, `track.config.json`, `ship.json`, `loop.blend`
or the existing `source/expansion/` files was touched. The PC session builds from this folder.

## Pieces and stations

| Piece | Road | From → to (clockwise) | cw / acw length (m) | Plan rev 2 (m) |
|---|---|---|---|---|
| `P3-WAR` | Waring Rd, divided | J2 → J6 | 671.2 / 670.3 | 669.8 / 668.9 |
| `P3-ZION` | Zion Ave, undivided | J6 → J7 | 1,569.1 / 1,596.2 | 1,567.3 / 1,594.4 |
| `P3-MG` | Mission Gorge Rd, divided | J7 → J3 | 2,369.3 / 2,394.3 | 2,364.8 / 2,389.7 |

- The piece ids are the dossier's road ids. Phase 2's letter `G` is already taken by the gorge leg, so letters were not reused.
- `s` is metres from the junction node at the start of each clockwise leg, along the clockwise OSM leg, as the plan
  defines it.
- `L` / `R` and every `+` offset are left of the clockwise direction.
- Lengths are in `data/centerline.local.json`'s local frame, the build's frame. The plan's lengths run 1.4–4.5 m
  (0.1–0.2 %) shorter on the same ways and nodes. Phase 2's research lens shows the same gap against
  `expansion.north.json`.
- New road: 4,609.6 m cw / 4,660.8 m acw. The western loop with Princess View: 5,718.8 / 5,798.7 m.

## Files

| File | What | Made by |
|---|---|---|
| `osm.expansion.json` | Fresh OSM roads and service ways. Same box and query as `data/osm.expansion.json` | `tools/fetch_osm.py --service` |
| `buildings.expansion.cache.json` (+ `.provenance.json`) | Fresh OSM building footprints over the same box. It already reaches −117.115, so it covers the −117.101 growth | `tools/fetch_buildings_cache.py --compare` |
| `routes__routes_analysis.json` | Legs in both senses: ways, controls, junction turns, median crossings, lengths | `scripts/p3x_legs.py` |
| `routes__legs.geojson` | The six legs | `scripts/p3x_legs.py` |
| `routes__mouths.json` | Every mouth branch, with its 3DEP grade, the plan's A1/A2 treatment and a census against the plan | `p3x_legs.py`, `p3x_3dep.py`, `p3x_profiles.py` |
| `routes__osm_diff.json` | Fresh OSM against the 2026-10-14 file | `p3x_legs.py` |
| `routes__stations.west.json` | The station frame: midline every 2.5 m, `y_3dep`, re-read curbs and medians. **Not** Step 1's `expansion.west.json` (no pads, stubs, welds or profile smoothing) | `p3x_legs.py`, `p3x_profiles.py` |
| `routes__profile_3dep.json` | 3DEP every 25 m along each cw leg | `p3x_3dep.py`, `p3x_profiles.py` |
| `revise__measure.json` | 3DEP every 5 m along both carriageways and the midline: junction heights, max grades, checks against the plan | `p3x_3dep.py`, `p3x_profiles.py` |
| `pipeline__mouth_geometry.json` | The J2/S2 and J3/S3 arm conversions against Phase 1's records. The J6 and J7 arms | `p3x_mouthgeo.py` |
| `pipeline__osm_lamps_signals.json` | OSM street lamps and traffic signals near the roads | `p3x_fetch_osm.py` |
| `aerial__widths_eye.csv` | The width table. Phase 2's columns first, then the re-read columns | A4 + `scripts/eye_reread.json` + `p3x_profiles.py` |
| `aerial__widths_reread.json`, `aerial__eye_panels/*.jpg` | This run's eye re-read and the panels it was read from | `p3x_crops.py` |
| `aerial__veg_bins.json` (+ `.calibration.json`) | [other, canopy, water, scrub] per piece, per 250 m bin, per side, in the 10–40 m band | `p3x_veg.py` |
| `aerial__paint_west.json` | Centre paint measured off NAIP every 2.5 m | `tools/aerial_paint_north.py`, **unchanged**, run on `routes__stations.west.json` (`scripts/p3x_paint.py`) |
| `terrain/` | Step 0.5 / 0.6: the 88-column grid and the 176,366 tier samples. Reused from the 2026-11-22 round-2 job | `scripts/round2/p3_{grow,plan,remap,west}.py` |
| `scripts/` | The scripts of record. `p3x_check_formats.py` reads these files through Phase 2's own readers | this run |
| `provenance.json` | Every file except this README: what it is, what made it, bytes, sha256 | `p3x_assemble.py` |

Phase 2's lens scripts were never committed: they lived in a session scratchpad, and only
`tools/aerial_paint_north.py` is in the repo. That tool was run unchanged. The other lenses are re-implemented in
`scripts/` on the repo's own code:
- `fetch_osm`, `fetch_buildings_cache` and `widths_from_osm._overpass` for the downloads;
- `author_expansion` for the frame, the midline, the smoothing and `max_grade`;
- `naip_carriageways.Mosaic` and `classify` for the NAIP reads.

## Sources

| Source | When (UTC) | Requests | Size |
|---|---|---|---|
| OSM roads, overpass-api.de (primary mirror, TLS verified, 7-day guard) | 2026-11-23 09:35:56 (OSM data 09:33:51) | 1 | 8,443,525 B. 21,481 ways, 80,438 nodes |
| OSM buildings, overpass-api.de | 09:38:27 (OSM data 09:35:51) | 1 | 8,066,314 B. 20,631 footprints; 20,621 of the old 20,631 unchanged |
| OSM lamps and signals, overpass-api.de | 09:44:16 (OSM data 09:43:02) | 6 (the first try was refused: 502, a mirror 175.5 days stale, 504) | 12,647 B. 0 lamps, 65 signals |
| USGS 3DEP 1 m getSamples | 09:39:40–09:40:07 | 8 | 736,518 B on the wire. 3,384 points, 0 no-value, 0 back-offs |
| NAIP 2022-04-25 0.3 m windows, The National Map ImageServer (for the paint tool) | 09:56–10:07 | 54 (27 windows + 27 catalog queries) | 32,823,698 B of PNG |
| *Reused:* NAIP 2022-04-25 0.6 m, Planetary Computer, item `ca_m_3211716_sw_11_060_20220425`. 24 tiles, i −10…−5, j 0…3 | 2026-11-23 03:42–04:37 | 25 | 120,006,479 B |
| *Reused:* 3DEP, the grid growth to `cols_w` 88 | 03:42–03:48 | 24 | 2,438,729 B. 10,354 new nodes |
| *Reused:* 3DEP, the tier need | 03:50–04:35 | 392 (14 back-offs on 502) | 41,472,461 B. 176,366 samples |

- The brief's estimates were ~177.4k samples in ~395 requests plus ~23 for the grid. The measured need was 176,366
  in 392 requests, plus 24 for the grid.
- The reused fetches are still valid. 3DEP and the 2022 aerial do not change, and the tier need was planned on legs
  that are unchanged in the fresh OSM. `routes__osm_diff.json` shows 0 nodes moved and 0 tags changed on the six
  legs. On all 239 ways within 60 m: 0 added, 0 removed, 0 changed.
- Every request used a generic client name, one at a time, with a pause between requests.
- The raw downloads are kept off-repo, with an md5 index.

## What is measured

- **The mouths reproduce the plan exactly** (`routes__mouths.json` `census`):

  | | Plan | Measured |
  |---|---|---|
  | Public side streets | 2 + 22 + 6 = 30 | **30**, the same streets at the same stations, ±4 m |
  | Mapped service drives | 12 (1 private) + 33 (3 private) = 45 | **45** (4 private) |
  | Closed junction arms | 5 | **5**: J6 Waring S (ways 1214006896 / 436411991), J6 Zion E (1430783899), the J6 slip (1214006895, Zion s 62), J7 Mission Gorge S (436428806 / 436428813), J7 Zion W (1220464880) |
  | Median openings on Mission Gorge | 5 | **5** at s 591 ×2, 1136, 1280 and 1739, plus the Old Cliffs Rd intersection crossing at s 930 |

  - Waring's median is crossed only by Greenbrier Ave (s 347).
  - "Bus Access Rd" (Zion s 1302) is unnamed in OSM (`residential`).
- **Heights and grades** (`revise__measure.json` `checks_vs_plan`, 3DEP every 5 m):

  | Item | Plan | Measured |
  |---|---|---|
  | J2 | 103.9 m | 103.86 m |
  | J6 | 99.7 m | 99.67 m |
  | J7 | 33.8 m | 33.78 m |
  | J3 | 33.4 m | 33.43 m |
  | Waring crest | 106.6 m at s 400 | 106.85 m at s 410 (midline); 106.6 m at s 385 (cw) |
  | Mission Gorge sag | 28.7 m at s 300–400 | 28.74 m at s 355 |
  | Zion's steepest | 10.2 / 10.1 / 9.8 % (20 m / 50 m / 100 m) at s 570–660 | 10.3 / 10.1 / 9.8 % at s 620–645 |
  | Waring max grade | 3.2–3.4 % | 3.2–3.6 % |
  | Mission Gorge max grade | 4.1–4.2 % | 3.7–4.3 % |

  The 11 % cap binds nowhere on the raw ground. The blends are Step 1's.
- **Turns** (20 m chords, `routes__routes_analysis.json` `junctions`):

  | Junction | Plan | Measured |
  |---|---|---|
  | J7 | +103° | +102.1° |
  | J2 | +84° | +83.6° |
  | J6 | +60° | **+73.5°** (the arms' own bearings, 220.5° → 297.3°, give +76.8°) |
  | J3 | +106° | +98.2° (Phase 1's pad arms give +107.5°) |

  The turn depends on how it is read. The PC should take the pad arms' bearings.
- **Widths** (`aerial__widths_eye.csv`):
  - `eye_curb_to_curb_m` on the 29 A4 stations is A4's eye reading of record (2026-10-14, 0.3 m zooms; its raw
    CSV was lost with a PC scratchpad).
  - Everything else is this run's re-read, made at every station and arm on the same NAIP item: the median width and
    kind, the carriageway split, the `reread_*` columns and the arm rows.
  - The re-read is the asphalt's edge. At 0.6 m a pixel, the gutter pan cannot be told from the curb. Against A4 it
    reads **0.7 m narrower on average** (median −0.8). 21 of 29 stations are within ±1.5 m. The 8 beyond it are
    WAR 450 (−2.7), WAR 600 (+3.5), ZION 900 (−2.0), MG 300 (−2.0), MG 1350 (−4.3), MG 1650 (−1.7), MG 2100 (−2.5)
    and MG 2250 (−1.7), mostly under trees.
  - The re-read medians:
    - Waring: planted with trees, 4–4.5 m, narrowing to a 1 m nose at the Greenbrier pocket;
    - Mission Gorge: terracotta, mostly 1.5–3.5 m, with planted 4–5 m stretches at s 150, 1500 and 1950–2250;
    - Zion: none, a double yellow and painted centre lanes.
- **The J2 / J3 arm conversions** (`pipeline__mouth_geometry.json`):

  | | J2 / S2 → `P3-WAR` start | J3 / S3 → `P3-MG` end |
  |---|---|---|
  | Where the new midline crosses Phase 1's straight arm cut | 3.1 m off the cut's middle | **5.6 m** off the cut's middle |
  | Angle to the arm's axis | −3.4° | −6.3° |
  | 3DEP at the cut minus the pad's datum | +0.04 m | −0.04 m |
  | Phase 1's declared arm width | 23.0 m | 28.0 m |
  | Re-read at Phase 1's own reading point | **not readable**: the left carriageway is under canopy; the right carriageway reads 9.0 m | **30.0 m ±1.5** |
  | Nearest A4 station | s 150: 28.0 m | s 2250: 33.7 m |
  | Built K-rail | 15.0 m out from the cut's middle | 15.1 m out from the cut's middle |

- **The paint** (`aerial__paint_west.json`, the tool's own [invented] thresholds, GATES-CHANGELOG 2026-10-19):
  - Zion has readings at 281 of 627 stations: 174 a double yellow, 107 a painted centre lane 3.2–3.9 m wide.
  - Waring and Mission Gorge are raised-median roads. Their readings are there, but `author_expansion` takes paint
    only on undivided roads.
- **Vegetation** (`aerial__veg_bins.json`): canopy share by bin and side.
  - Zion: 2–17 %. The dossier says 3–15 %.
  - Waring: 7–12 %.
  - Mission Gorge: 1–22 %, with scrub up to 32 % at s 1750–2000 left.
- **Lamps and signals:** OSM maps **no street lamps** around Phase 3. 30 of the 65 signals stand within 60 m of a
  piece.

## Not measured: owed

- **Curb-return radii at J6 and J7.** The plan's Step 1 reads them. Not read here.
- **Waring's left carriageway at S2.** It is under canopy on 2022 NAIP. Same-station width owed (Street View or
  leaf-off imagery).
- **The unmapped driveways** (Zion's houses, Grantville's lots). Plan Step 0.8 asks for a NAIP count. Not done; only
  OSM's 45 are listed.
- **Street-lamp positions.** OSM has none. Every Phase 3 lamp is authored until the Street View night check (plan D3).
- **Street View items:** the eucalyptus row (MG s ~1150–1250; its shadows are visible across the right carriageway at
  s 1200), the paint since 2022, guardrails, speed signs.
- **`tools/stub_roads.py declare`** on the three pieces. It needs the built pieces. `routes__mouths.json` is the input
  list, not the declaration.
- **3DEP not fetched**, counted only by the round-2 job:
  - the I-8 corridor rebuild that the far ring's move to −117.14 makes stale (38,325 samples / 86 requests);
  - the break-line profiles (4,149 / 10);
  - any samples near the future J6/J7 pads and stubs: the tier need was planned without them.
- Cross-sections and cut walls (Zion s 432–660, Mission Gorge). The tier samples cover them; Step 1 / 2 cuts them.
- Newer aerial than April 2022. The frame-rate baseline.

## [invented] numbers

Every number below is a tuning choice, not a measurement.

- **Routes** (`p3x_legs.py`):
  - `CROSS_M` 80: a branch reaching the other carriageway within 80 m is a median crossing;
  - `BRANCH_M` 15: a branch's heading is read over its first 15 m;
  - `CHORD_M` 20: junction bearings are read over 20 m chords;
  - `SIGNAL_NEAR_M` 40;
  - the 60 m radius of the OSM corridor diff;
  - the lamp box margin, ~300 m (`p3x_fetch_osm.py`);
  - the 60 m `near_phase3` radius.
- **Profiles** (`p3x_3dep.py`):
  - `STEP_M` 5;
  - `ARM_M` 40;
  - service mouths sampled at 0 / 10 / 20 m.
- **The eye panels** (`p3x_crops.py`):
  - `ALONG_M` 60, `PX_M` 0.2, `UPSCALE` 2, `ARM_AT_M` 30;
  - the half widths 24 / 16 / 26 / 22 m, and 36 m for the wide arm panels;
  - the 0.5–99.8 % contrast stretch.
  - Its automatic read uses `naip_carriageways`' own thresholds (GATES-CHANGELOG 2026-11-05) over `AUTO_ALONG_M` 20.
  - The automatic widths are wrong where lots and side streets are paved, as the plan says of the width walker.
    They are a hint, not the width.
- **Vegetation** (`p3x_veg.py`):
  - the class thresholds: `CANOPY_NDVI` 0.30, `CANOPY_BRIGHT` 90, `SCRUB_NDVI` 0.12, `WATER_NDVI` −0.05,
    `WATER_NIR` 45. They were chosen on a grid against Phase 2's own bins: mean error 0.083 in canopy + scrub share
    over 52 bins;
  - the sampling: 5 m along, 10–40 m out every 0.75 m, 250 m bins.
- **The station frame:**
  - widths linear between re-read stations and held flat beyond the first and last;
  - undivided Zion stations without a read median are typed `line` (the dossier's double yellow);
  - `author_expansion`'s [authored] `DIVIDED_SEP_M` 3.0 and `SMOOTH_SIGMA_M` 4.0.
- **The round-2 job:**
  - NAIP margin 150 m;
  - `PAIR_M` 45 in `p3_west.py`.
- The width transition of ≥ 60 m at the J2/J3 arms is the plan's [invented], not set here.

## For the PC builder

1. Copy `osm.expansion.json` and `buildings.expansion.cache.json` (+ provenance) into `data/`. They are fresh as of
   2026-11-23 and identical on the Phase 3 corridor. Re-run the 7-day guard if the build starts after 2026-11-30.
2. `terrain/heightfield.88.*` is `tools/grow_heightfield.py`'s `cols_w` 88 output (west edge −117.107285). Its proof is
   beside it.
3. Merge `terrain/p3_tier_samples.json.gz` into the re-keyed `data/terrain.samples.json.gz`
   (`tools/remap_sample_cache.py`, +1,408 base units; `terrain/remap.proof.json`).
4. The tier need was planned on `terrain/tier_plan_input.expansion.west.planned.json`, which has no pads and no stubs.
   Expect a few more samples near J6, J7 and the stubs, plus the corridor rebuild and the break lines (see Owed).
5. Arm widths at J2 and J3:
   - S3 re-reads 30.0 m against Phase 1's 28.0 m, and the real road runs 5.6 m off S3's cut middle at −6.3°;
   - S2 is unreadable.

   Both push the width transition into the new piece, as plan A4 says, and S3's offset will show in the weld.
6. J6's measured turn is ~74–77°, not the plan's 60°. Check the pad design against the arm bearings in
   `pipeline__mouth_geometry.json`.
7. The width table carries A4 as the width of record and the re-read beside it. The re-read is about one gutter
   narrower; decide which one V1 tests against. The panels in `aerial__eye_panels/` show every reading.
8. Zion's paint runs (`aerial__paint_west.json`) only partly match the plan's list of centre lanes. Example: the tool
   reads a double yellow at s 890–1002, but the eye panel at s 900 shows two yellow lines 2.5 m apart. Eye-check
   before authoring the paint.
9. To check this folder, run `python -I scripts/p3x_check_formats.py <repo> <this folder>`. It runs 68 checks: the
   provenance hashes, and Phase 2's readers (`author_expansion.reading_offsets` and `load_paint_measured`,
   `make_treefx.North.shares`).

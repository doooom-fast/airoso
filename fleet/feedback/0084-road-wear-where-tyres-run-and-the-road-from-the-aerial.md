---
id: 0084
title: "road textures need wear where tyres run" — one cracked-asphalt picture on a 4 m world grid; the wear repeats and ignores the lanes. Wear on the real wheel paths (streets) and the racing line (tracks, kerbs too), and the whole road sampled from the aerial
status: open — investigated 2026-11-07; pilot built 2026-11-09 (Milford 0.1.7, Mac, every gate green), integrated into Milford 0.1.9 the same day (ledger 0082); Milford 0.1.11 installed with it; High Plains 0.1.7 inputs + kerb rubber 2026-11-10, the photo's rubber by Kevin's word ("Use the photo's rubber"; built on the PC, runbook 0084-2); Kevin's drive closes it
scope: every track (the LM v4 engine's road material); proof cases chosen by the investigation
layer: engine
train: -
---

## Symptom

Kevin, 2026-11-07, verbatim:

> "Add a note that we'll need road textures to include wear along where tires run, in a realistic manner. I've also
> been curious about somehow sampling the entire road's texture from aerial data and mapping it directly onto the
> entire road instead of a repeating pattern that's not realistic (the tire wear repeats and doesn't follow the road
> itself)"

> "For tracks we'll use racing lines"

> "Which will help darken curbs realistically etc"

> "Well do this after my next drive test"

> "But maybe do the investigation now"

What he asks for:

- Wear where tyres actually run, drawn realistically.
- On streets: the wheel paths of each lane.
- On race tracks: the racing line, which also darkens the kerbs where the line rides them.
- No repeating pattern. The wear follows the road.
- An idea to look into: sample the whole road's picture from aerial imagery and map it onto the whole road.

## Evidence

- `1ROAD` binds one picture, `asphalt_cracked_diffuse.jpg` + `_normal.jpg` (`scripts/ac/pbr.py:17`, the same in
  Lake Murray's `engine-july-snapshot`). It is the mined LA Canyons texture (`assets/textures/SOURCES.txt`).
- The road ribbon is built with road-following UVs (U = lateral / `tile_m`, V = arc / `tile_m`, `tile_m=8.0`:
  `tracks/san-diego-lake-murray/scripts-v021/geometry/ribbon.py:56-58`, `build_network_mesh.py:760`). **But the LM
  engine's prep throws them away.**
  - `planar_uv` rewrites every 1ROAD loop as u = x / 4, v = z / 4 (`engine-july-snapshot/scripts/ac/build_kn5_loop.py:44`
    `UV_TILE = 4.0`, `:935-941`, called at `:1404`).
  - Measured du/dx = dv/dz = 0.25 on the built Del Mar, Milford, Sand Creek and High Plains LM kn5s (investigation
    below).
  - So the picture repeats on a 4 m world grid that ignores which way the road runs. Any wear in it comes back every
    4 m and never lines up with a lane.
- Ledger 0053 already did this once for kerbs.
  - Lake Murray's race kerbs got a worn atlas with four rubber levels; the UVs pick a level block by block.
  - The level came from corner geometry, because the AI drafts never touched a kerb.
  - A racing line would give it from where cars really run.
- The aerial road texture was researched on 2026-10-28 in `fleet/reference/SATELLITE-ROAD-TEXTURES.md`; nothing
  was built.
  - The plan: a road-following strip atlas baked from public-domain or owned orthoimagery (the macro colour),
    multiplied by an owned tiled micro asphalt through `ksPerPixelMultiMap_NMDetail`.
  - Lane paint stays geometry.
  - The handoff is in §6.
  - Its open limits: the real ground resolution we may ship (NAIP California 2024 = 60 cm), registration between
    the mesh and the photo, and baked shadows under AC's moving sun.
  - `scripts/aerial/` has no `ortho_*` modules yet.

## Diagnosis

Supported by the evidence above: one tiled picture cannot follow the lanes. The wear has to come from where tyres
run on this road, through a mask or a baked picture that follows the road's own arc length and lanes. Which way,
and from what data, is the investigation's job.

## Investigation (now)

Research only: no build, no install, no downloads without Kevin's yes.

- Where the wear goes:
  - Streets: the lanes and their wheel paths, from the data the engine already has.
  - Tracks: the racing line, from the source each track has.
  - Kerbs: where that line rides them, feeding 0053's rubber levels.
- How it is drawn:
  - a wear mask (rubber darkening, polish, oil drip down the lane middle) over the existing or a new micro asphalt;
  - in which shader slot;
  - what the kn5 exporter must add.
- The aerial road:
  - what each track's imagery can carry at the resolution we may ship;
  - whether real wear shows in it at that resolution, or must be drawn on top;
  - how §6 of the study changes now that every track builds on Lake Murray's engine.
- A first track to prove it on, and a still that shows the difference.

## Investigation findings (2026-11-07, research only)

Read from the engine on `origin/claude/fleet-lm-engine` and the built LM kn5s. No downloads, builds or Blender.
Scripts and stills: `/Volumes/Drive/codex/roadwear_work/` (`stills/01_street_lane_wear_sand_creek.png`,
`02_track_racing_line_rubber_milford.png`, `02b_track_apex_zoom_milford.png`).

**Streets: where tyres run**
- The painted lanes come from width alone (`scripts-v021/geometry/ribbon.py:350-411`).
  - The rule: a divider every 3.65 m from the centre, the edge line 0.55 m in, double yellow at ±0.09 m.
  - Stubs use OSM lane counts (`:485-523`). Only Lake Murray's 4 north pieces have paint measured off NAIP.
- Wheel paths (lane centre ±0.85 m [unverified]) can come from the same rule, so they line up with the paint by
  construction.
- On the LM loop, the width rule and OSM `lanes` agree at 2,632 of 3,542 tagged stations (74 %).
  - The strip left beyond the last full lane is p10 0.50 / median 1.10 / p90 3.45 m. It could be a bike lane, parking
    or shoulder; the data can't say which.
  - Side finding: at 3,377 stations the rule paints a dashed divider inside that strip.
- The rule fails at junction boxes, welded mouths, Sand Creek's 4 pads (7,543 m²), fold fans and unmarked circuits.
  There the wear fades to a general darkening [invented].

**Tracks: the racing line**
- No recorded line exists.
  - Every `fast_lane.ai` on disk (1,151) is a generated draft with an `ai_draft.json` beside it (ledger 0023).
  - Milford's draft is the centreline (offset ≤ 0.012 m).
  - Lake Murray's race drafts stay ≥ 1.04 m off every kerb (0053).
- Best source: Kevin records a line per layout and direction with CSP's AI recorder during a drive.
  - Fallback: a minimum-curvature model line [model].
- Into the bake: `data/racing_line.<layout>.json`.
  - Every layout's line is summed, so two-way layouts get both directions.
  - Each line paints two tyre tracks.
- Kerbs: each 1 m block's rubber level comes from how far the tyre band overlaps the kerb.
  - This replaces `kerb_wear_centres` (`tools/race_furniture.py:625-637`); 0053's atlas stays.
  - High Plains, Aspen and Exotics' traced kerbs have no wear today.

**Drawing it**
- The pick: a per-track baked, road-following strip atlas (`SATELLITE-ROAD-TEXTURES.md` §4.1) on the stock
  `ksPerPixelMultiMap_NMDetail`:
  - txDiffuse = tone × wear;
  - txMaps = polished wheel paths;
  - txDetail + txNormalDetail = an owned micro asphalt.
- The bake reads wear at each texel's world (x, z), so junctions and pads come out right.
- A second UV set isn't possible: a kn5 vertex carries one UV (`extract_kn5.py:9`).
- Changes:
  - 1ROAD skips `planar_uv` under the opt-in key. `_split_large` (`:902-926`) renames an authored layer to UVMap,
    so authoring alone isn't enough.
  - engine-july's `export_kn5_addon.py:111-131` and `pbr.py` gain the extra slots, the shader and the detail VARs.
- Memory at 10 cm, BC7 with mips:
  - Del Mar 2048², 5.6 MB;
  - Milford 4096², 22 MB;
  - Lake Murray (≈500,800 m²) 8192², 89 MB.
  - Milford's 1ROAD is at 65,196 of 65,535 vertices, so the split will run.
  - Textures stay power-of-two (L7).

**The aerial road**
- On disk, all NAIP and public domain:
  - Lake Murray: 2022, 0.50 m/px mosaic, 1,319 of 1,927 tiles missing;
  - Sand Creek: 2023, 30 cm source, 0.46 m/px mosaic;
  - Milford: 2022, 0.50 × 0.68 m;
  - Del Mar: 2012, 0.50 m (it shows the lots, not the 1987-92 temporary circuit).
- Real wear barely shows at that resolution.
  - Cross-road brightness over 160-180 m varies ~2 % in Lake Murray's lanes and ≤ 3 % at a Milford corner.
  - Sand Creek dips 7-13 % at lane scale, but registration (p95 2.4-3.3 m on a noisy edge test; 0055 measured Lake
    Murray +0.1 / -1.4 m, max 2.9 m) can't place them.
  - **So wear is drawn; the aerial can only give tone and patches.**
- Shadow pixels inside the built road: Lake Murray 16.0 %, Sand Creek 11.0 %, Milford 7.3 %, Del Mar 2.0 %. They read
  bluer, so they can be detected.
- Paint ghosts: Lake Murray 8.6 %, Sand Creek 9.1 %.
- `tools/aerial/naip.py` hard-codes EPSG 26913 (Colorado).
- §6 of the study moves to engine-july's prep and exporter; its §6.5 proof tracks are superseded.

**Proposed build** (after Kevin's next drive)
1. Strip-atlas UVs in the prep.
2. `tools/road_wear_bake.py` (numpy + Pillow).
3. Racing-line intake from `.ai`.
4. Kerb levels from the line.
5. Exporter slots.

- **Opt-in key** `road_wear` {mode lanes | line | both, texel_m, lines, kerb_from_line, macro, micro}. Absent, Lake
  Murray stays byte-identical.
- **Gates on the built kn5:**
  - wear peaks within 0.15 m of the declared paths [invented];
  - no repeat along a wheel path (autocorrelation);
  - texel density and roundness;
  - power-of-two, mips, every slot embedded;
  - the vertex cap;
  - road positions hash-equal, and the four gates' numbers equal.
- **Proof tracks:** first High Plains LM (38,467 m², 20 traced kerbs, 30 cm NAIP), then Sand Creek LM (lanes and a
  race layout).
- **Size** [estimate]: 1.5-2.5k lines plus tests.
- **Downloads:** none for wear. Optional full-resolution NAIP corridors: Sand Creek ~15-25 MB, High Plains ~5-8 MB
  [estimates], only on Kevin's yes.

**Open for Kevin**
- Record a racing line per layout and direction during the drive?
- High Plains as the proof track, or Del Mar?
- Aerial tone in the first build, or wear only?
- 10 cm on Lake Murray (89 MB)?
- Keep the dashed dividers inside the leftover strip?

## Fix

Not decided. It waits for the investigation and Kevin's next drive test. Every key is opt-in; Lake Murray must not
change unless it is chosen.

## Verification (decided before the fix)

- The built UVs and the shipped textures put the wear bands on the measured wheel paths and racing line (L5: read
  from the built artifact).
- No repeat visible at speed.
- The road's geometry and physics are untouched: drive_test, audit_mesh, verify_kn5 and kn5_ground_check numbers
  equal to the build before.
- Kevin's drive closes it.

## Build (pilot Milford 0.1.7, Mac, 2026-11-09)

Kevin, 2026-11-08 22:15, after driving: "the road texture from aerial isn't done yet" / "Keep going on all machines".
Pilot on Milford (not High Plains, as first planned) by the brief: its NAIP and lidar are on the Mac and it has an
installed build to compare against. Branch `claude/milford-road-wear-017` from `claude/milford-edge-strip-016` (d8d1473,
0.1.6). Built on the Mac's system disk: the Drive stopped creating files at ~13:35 (HFS+ "Invalid argument"; one file
written there, `tools/road_wear_check.py`, came back holding another file's blocks and was rewritten from the session).

### What was built (engine-level, opt-in)

- **`scripts/aerial/road_wear.py`** (the engine module, pure numpy): the aerial sampler on the engine's own projection,
  its registration to the BUILT road, the tone, the minimum-curvature line [model], the speed / rubber model [model],
  the tyre profile, the world-cell atlas, a minimal PNG writer. Every default is marked measured / model / invented in
  `DEFAULTS`.
- **`tools/road_wear_blend.py`** (Blender, the last part of prep, `tools/ship_track.sh prep_prep`): bakes the atlas from
  the world, rewrites the surfaces' UVs, rebuilds their materials, writes `data/road_wear.json` (the exporter's rows and
  every number) and `data/road_wear.line.<layout>.json`. Self-checks: no vertex moves (positions hashed before / after),
  the kn5 writer's vertex count (engine-july's own `_export_vertex_keys`, its own `_split_for_writer` if over), power of
  two.
- **engine-july `export_kn5_addon.py`** (airoso's copy and the snapshot, byte-identical; `PENDING-MIRROR.md5` line
  1bdc2628 -> 83b231e8): binds `data/road_wear.json`'s material rows only when the config names `road_wear`.
- **`tools/road_wear_check.py`** (gate `road_wear`, hard, opt-in in ship.json): fleet/GATES-CHANGELOG.md 2026-11-09.
- **The key** (`track.config.json road_wear`): `surfaces` (1ROAD first), `aerial` {image, bbox_lonlat}, `lines`
  [{layout, ai}], and an override of any default. Absent = nothing runs. Lake Murray names no key.

### How it draws (the two scales)

- **Macro** (txDiffuse; one 4096² RGBA atlas at 0.25 m a texel, alpha 0): m0 x tone x (1 - rubber). Square world cells
  of 64 m, each a 320 px tile holding the cell and an 8 m margin (the furthest vertex of any face is 7.26 m from its
  centroid); 131 tiles. Every face takes its centroid's cell. The faces are flat-shaded already, so the seams cost no
  vertex: 1ROAD 65,218 writer vertices before and after; the edge strip 26,144 -> 27,191.
- **Detail** (txDetail / txNormalDetail at UV x 256): the stock cracked asphalt and its normal, on exactly the prep's
  4 m grid and phase (cell, margin and pitch are whole 4 m tiles). Pre-brightened by 1/m0 (m0 0.855: the tone's p99.5
  maps to 1.0), so the median road texel is 0.1.6's look exactly; 0.44 % of its texels clip. JPEG q95, 3.30 MB (from
  the stock 2.37 MB).
- **Shader** `ksPerPixelMultiMap_NMDetail`; VARs detailUVMultiplier 256, detailNormalBlend 1.0, useDetail 1.0. No ks*
  VARs (the lighting response stays 0.1.6's, whose road ships none either); no txMaps (as 0.1.6).

### The open questions, answered from measurement

| question | answer | from |
|---|---|---|
| a recorded racing line? | **None exists.** The committed `ai/full/fast_lane.ai` is the generated centreline draft (`ai_draft.json` offset_max 0.012 m; fast_lane = pit_lane byte for byte). 0.1.7 uses the minimum-curvature line inside the built edges **[model]**. The key already names `source/road_wear/fast_lane.full.ai`, so a recorded line replaces it with no code change | measured |
| aerial tone in the first build, or wear only? | **Both.** Registered to the built road, the tone follows the photo (gate tone r 0.953) | measured |
| does real wear show in the aerial? | **No.** On NAIP 2022 the model line's tyre band regresses to 0.3 % darker, the centreline's to 0.7 %: whatever rubber Milford carries is under ~1 % at 0.5 m. So the rubber amplitude (0.22) is **[invented]**, and Kevin's drive picks it | measured |
| where is the photo against the mesh? | The aerial reads **1.00 m west** of the built road: the shift at which the built asphalt reads darkest against a 3 m ring, searched +-3 m at 0.25 m (contrast 0.0670 -> 0.0725). Applied | measured |
| shadows, paint ghosts | Shadows are **8.3 %** of the road (the dark tail under 0.6 x the lit median, b/r 1.43 against 0.93 lit; the masks grown one aerial pixel), filled from the lit asphalt within 3 m. Paint ghosts **0 %** (road p99 1.14) | measured |
| texel size | **0.25 m**, half NAIP's 0.50 m E-W pixel: the finest tone it carries. The rubber band (~3 m) is 12 texels across | measured (Nyquist) |
| kerbs | Milford has **no race kerbs** (no 1KERB_RACE). The edge strip (1KERB_sidewalk) shares the atlas, so where the line clips the edge at an apex the rubber carries onto it (the apex still) | - |
| 10 cm on Lake Murray; High Plains first; dividers in the leftover strip | Not answered here: Lake Murray is untouched, Milford was the brief's pilot | - |

### Gates (Mac, EMPTY workshops on the system disk, `--no-install`, no force)

- **0.1.5** = the installed build's Mac workshop (`/Volumes/Drive/codex/mf_work/v015/b1`).
- **0.1.7 A** = this commit with the `road_wear` key and gate taken out: the 0.1.6 build (its kn5 is 39,002,272 B, the
  PC's 0.1.6 to the byte).
- **0.1.7** = this branch.
- Workshops `/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex/{a17,b17}`; ENG = `mf_work/eng2` with this
  branch's exporter; the two 82 B TreeFX placeholders (11,247 trees planted in both).

| gate | 0.1.5 (b1) | 0.1.7 A (no key) | **0.1.7** |
|---|---|---|---|
| drive_test, full | PASS: soft top 0, obstructed 0, daylight 0, excursions 0, severe steps 0, bumps 0.0 /km, kinks 6.34 /km | PASS, equal | **PASS, equal** |
| audit_mesh (hard total) | CLEAN, every row 0; road 65,218 v, curb 26,144 v | CLEAN; 65,218 / 26,144 | **CLEAN; 65,218 / 27,191** (the strip's UV seams) |
| verify_kn5 + `--inis` | pass + pass | pass + pass | **pass + pass** |
| kn5_ground_check | PASS: walls p95 -0.186, road-over-ground 9 / 9,317 (max 0.073) | PASS: -0.186, 2 / 9,317 (max 0.052) | **PASS: -0.186, 2 / 9,317 (max 0.052)** |
| kn5_textures | 39,006,968 B, 19 textures, missing 0 | 39,002,272 B, 19, 0 | **42,611,917 B, 21, 0** |
| house_seat | PASS, 3, contact -0.323..-0.150 | PASS, equal | **PASS, equal** |
| edge_smoothness | PASS: lane p99 d2 1.19 / 1.22 cm, resid 0.38 / 0.39 cm | PASS, equal | **PASS, equal** |
| veg_verify (not a chain gate) | PASS: 11,247 trees, 385 colliders, nearest paved 4.65 m | - | **PASS, equal** |
| **road_wear (new)** | - | - | **PASS**: materials; density 60,956 triangles, worst 0.086 %; no_repeat 0 of 87,633 texels; detail phase 1e-5 tiles; tone r 0.953; rubber centroid +0.044 m, depth 0.217 against 0.209 declared |
| SHIP | OK | OK | **OK, no force** |

0.1.5 -> 0.1.7 A is 0.1.6's edge strip (ledger 0087); 0.1.7 A -> 0.1.7 is this pass. **The road is untouched**
(`source/road_wear/compare_ab.py`, A against 0.1.7's road kn5): all 32 meshes' triangle-corner positions are
bit-identical; UVs and materials changed on exactly 1ROAD_road and 1KERB_sidewalk; no other texture changed.

### Sizes

| | 0.1.5 | 0.1.7 A | **0.1.7** |
|---|---|---|---|
| road kn5 | 39,006,968 B | 39,002,272 B | **42,611,917 B (+3.61 MB on A)** |
| added | | | road_wear_macro.png 2,548,583; road_wear_detail_1road.jpg 3,299,551; road_wear_detail_1kerb_sidewalk.jpg 319,072; road_wear_flat_nm.png 76 |
| dropped | | | asphalt_cracked_diffuse.jpg 2,372,762 (now the detail's source); building_diffuse.jpg 231,365 |
| in VRAM | | | the 4096² RGBA macro: 64 MB + mips as decoded from PNG [estimate] |

The first 0.1.7 build wrote the detail as PNG (9.6 MB) and came to 50,015,603 B; JPEG fixed that.

### Stills (Blender EEVEE, NAIP's sun; the same cameras on 0.1.5 and 0.1.7)

Car height = the eye 1.1 m over the line 24 m before the spot; above = 28 m straight over it.

- `tracks/milford-road-course-lm/source/stills/road_wear_015_vs_017_front_straight.jpg` (station 12, 252 km/h)
- `tracks/milford-road-course-lm/source/stills/road_wear_015_vs_017_fast_curve.jpg` (station 152, R 148 m at 150 km/h)
- `tracks/milford-road-course-lm/source/stills/road_wear_015_vs_017_apex.jpg` (the hairpin, R 13.4 m at 45 km/h: the
  line clips the inside edge strip)

Blender has no NMDetail, so `source/road_wear/road_wear_stills_blend.py` wires a stand-in (macro x detail at UV x 256,
the macro's alpha ignored). The stills show the band on the line and the tone. They also show that **the 4 m grain
still repeats**: the detail is the same tile, by design, and the aerial tone breaks it up only as much as the photo
varies (tone p01..p99 0.73..1.14).

### Measured / model / invented

- **Measured**: the registration (-1.00, 0.00 m); the shadow rule (0.72 x median, b/r 1.06) and its 8.3 %; no paint; the
  texel (Nyquist of 0.50 m); the edges the line keeps inside (scanned off the built road, capped at the declared half
  width + 1 m); the car's track 1.60 m and half-width margin 0.95 m (real cars' dimensions); that NAIP sees <= ~1 %
  rubber.
- **Model**: the minimum-curvature line; the speed profile that weights the rubber (1.2 g lateral, 1.1 g braking,
  0.45 g traction, 70 m/s); the model lap of 107 s.
- **Invented**: the rubber amplitude 0.22; the line's spread 0.70 m (0.55 in the first build left two stripes with a
  light middle, a lane's look); the straight's base share 0.35; the 12 m smoothing; the tone clip 0.70-1.30; the
  headroom percentile 99.5; the 3 m fill radius; paint at 1.45 x; the 10 m layer; JPEG q95; every new gate threshold
  (GATES-CHANGELOG).

### Unverified, for the PC and Kevin

- AC's slot name and alpha. `txNormalDetail` is Content Manager's reading; the add-on's own table says `txDetailNM`.
  txDiffuse alpha 0 = full detail is CM's reimplementation. If the grain is missing in game, the alpha reads the other
  way; if the road is black or see-through, alpha is being used as transparency. CSP Objects Inspector on a Kunos road
  settles both.
- The rubber's strength and width: invented, Kevin's eye.

### To roll it to the other tracks

- **Circuits** (High Plains, Exotics, Pikes Peak, Pueblo, Aspen, Grand Junction): the key plus the track's own aerial
  and its bbox, nothing else. Race kerbs (1KERB_RACE, ledger 0053's atlas) are a separate surface: their per-block
  rubber level from where the line's tyre band overlaps them is not built yet (`tools/race_furniture.py`
  kerb_wear_centres).
- **Streets** (Lake Murray, Sand Creek) use lanes, not a racing line. Owed: a `lines` source "lanes" that builds one
  line per lane centre from the paint rule (`scripts-v021/geometry/ribbon.py:350-411`, a divider every 3.65 m) and the
  OSM lane counts, both directions, with the tyre profile on the lane's wheel paths (track 1.6 m) and a gentler,
  uniform rubber (traffic, not cornering). Junction boxes and pads get the tone only. Lake Murray's atlas at 0.25 m
  would be ~8192² (≈500,800 m² of road), or two materials.
- **The aerial frame** is per track (`aerial.bbox_lonlat`, a north-up lon/lat export); `tools/aerial/naip.py` still
  hard-codes EPSG 26913.
- **A non-repeating micro**: the 4 m cracked tile still repeats. An owned, larger or procedural micro is the next look
  step (SATELLITE-ROAD-TEXTURES §4.2).

### Lake Murray unchanged (`tracks/milford-road-course-lm/source/road_wear/mac_017/lm_ab.sh` and its `lm_ab.log`)

The Mac scripts of this build (the build, the A side, both A/Bs, the stills, the records) and their logs are in
`source/road_wear/mac_017/`; the stills' cameras in `source/road_wear/spots.json`.


- `git diff d8d1473 -- tracks/san-diego-lake-murray`: only the snapshot's `export_kn5_addon.py`, its `MANIFEST.md5` line
  and one added `PENDING-MIRROR.md5` line.
- Identical md5, base and branch: engine-july's `build_kn5_loop.py` (the prep, 2a653ee1), `build_spawn_kn5.py`, `pbr.py`
  (44615dd3) and `dummies.py`; airoso's `tools/ship_sd.sh` (5a4bbe29, no `road_wear` in it) and
  `tools/trim_connectors.py`. Lake Murray's config names no `road_wear`.
- **Trim A/B** (the base's tools against the branch's, on Lake Murray's own data): connectors.local.json 664da93b,
  mouths.json b73b70f4, median_bands.json f0c97952, the log 63af07cc: **byte-identical**.
- **Prep A/B**: the prep is not touched (md5 above), and the bake never runs without the key (it is not in ship_sd.sh).
- **Exporter A/B without the key** (`export_ab.sh`): the base's export driver (1bdc2628) and this branch's (83b231e8),
  each on 0.1.7 A's split road scene. The `.ini` is **byte-identical** (638a22a5); the kn5s are `tools/kn5_equiv.py`
  **EQUIVALENT** (tangents only, max 1.79e-7: the 2026-11-03 comparison rule; the same driver run twice differs the same
  way).

### Runbook 0084-1 (PC): rehearse 0.1.7 from an empty workshop; green = install (Kevin 2026-11-09: "I always want newer builds")

1. `git fetch && git checkout claude/milford-road-wear-017` at the head this section is pushed in; `git status` clean.
2. **The trees**: copy `Oak3.bin` (24111ede) and `SycamoreV2.bin` (7010d61f) into
   `tracks/milford-road-course-lm/source/trees/` and check their md5. Without them the chain plants 0 trees and still
   goes green (0.1.6's trap). Never commit them.
3. **ENG**: a copy of the engine 0.1.6 was built with (`eng_mflm_015`), with this branch's
   `scripts/ac/export_kn5_addon.py` copied over its own; md5 **83b231e8...** (the snapshot's PENDING-MIRROR line). The
   real engine-july is not edited until the mirror (the snapshot README's three lines); Lake Murray does not need it
   (the change is opt-in).
4. **Rehearse**: `ENG=<that copy> SHIP_PROJ=D:/k10-scratch/milford_017_reh bash tools/ship_track.sh milford-road-course-lm --no-install`,
   from an EMPTY `milford_017_reh`. Look for `[road_wear] ... atlas 4096 px at 0.25 m (131 cells ...)`,
   `shift (-1.00, +0.00) m`, `writer vertices {'1KERB_sidewalk': 27191, '1ROAD_road': 65218}` and `[treefx] 11247 trees`.
5. **Compare every row** with the 0.1.7 column above, `road_wear` included. The road kn5 must be 42,611,917 B
   (kn5_equiv to the Mac's b17 if it is copied across: tangents only); `data/road_wear.json` m0 0.85518.
6. **Green on every row = install**, with no further word: the real chain into `D:/k10-scratch/milford_lm` (0.1.6's
   workshop kept as `milford_lm.0.1.6`), ENG as above. ship_track parks 0.1.6 in `D:/k10-track-archive/<stamp>/`.
   Re-render the menu picture with 0.1.6's camera. If any row is red or differs: no install; report the row.
7. **In game** (Kevin's drive is the verdict). CSP Objects Inspector on the road: shader
   `ksPerPixelMultiMap_NMDetail`, the four slots bound, detailUVMultiplier 256. Look for:
   - the cracked grain as crisp as 0.1.6 at car height (missing = the alpha reads the other way);
   - the road neither black nor see-through;
   - the darker band on the line through the corners, and onto the inside edge strip at the hairpin;
   - no 4 m grid in the tone.
8. **Record a racing line** during the drive (CSP's AI recorder, the full layout, clockwise). Copy the `fast_lane.ai` it
   writes to `tracks/milford-road-course-lm/source/road_wear/fast_lane.full.ai`. The next build's rubber then follows
   where the car really ran; the bake prints `recorded source/road_wear/fast_lane.full.ai`.

### Integrated: Milford 0.1.9 (0.1.7 + 0.1.8), 2026-11-09

0.1.7 is merged with ledger 0082's furniture pass 3 (0.1.8) on `claude/milford-019`. See ledger 0082
"Milford 0.1.9 (0.1.7 + 0.1.8 integrated)" for the order in prep (the re-seat, then this bake, still last; the two
commute), the gate column and the PC runbook **0082-6**.

- `road_wear` PASS with every number above.
- The road kn5 is 42,676,006 B (0.1.7 + 0.1.8's 64,089 B).
- 1ROAD / 1KERB are byte-equal to 0.1.7's b17.

Runbook 0082-6 supersedes this runbook's install (steps 4-6). Step 7 (the in-game slot / alpha check) and step 8 (record a
line) now run on 0.1.9.

## High Plains 0.1.7 (2026-11-10: the inputs and the engine on the Mac, both builds on the PC)

Kevin, 2026-11-10: "lets continue, drives looked good". Then, while this was being prepared: "Move everything from the Mac to
the pc that you can, we seem to be filling up that drive too quickly". So **nothing was built on the Mac**. The Mac did only
what needs its data: it read the NAIP and wrote the inputs. The PC builds twice and installs (runbook 0084-2).

Branch `claude/high-plains-road-wear`, cut from `claude/treefx-cards` 98bb3510. Installed 0.1.6 is `5ce76a7e` per
`fleet/ac-installed.json` on `claude/ac-tidy`. Its records are at 1aeecb84, and 98bb3510 changes no High Plains source
after that.

### What came over from the Milford branches (engine only, no Milford track file)

These files were taken as they stand at `claude/milford-0111` (2dc444cd; equal to 4262162 for every one of them):

- `scripts/aerial/road_wear.py`
- `tools/road_wear_blend.py`
- `tools/road_wear_check.py`, including 4262162's ksAmbient / ksDiffuse 0.40 and the every-VAR check
- `tests/aerial/test_road_wear.py`
- `scripts/ac/export_kn5_addon.py` and the engine-july snapshot's copy, md5 83b231e8, with its `MANIFEST.md5` and
  `PENDING-MIRROR.md5` lines

Edited by hand:

- `tools/ship_track.sh`: only the `road_wear` prep block and `gate_road_wear`. Milford's far-ground, re-seat,
  kn5_textures and edge_smoothness pieces stayed behind, and this branch's `seat_pads` step is kept.
- `tests/tools/test_ship_track_chain.py` gets one V4_EXTRAS line.

This ledger file was taken from the same head, and this section is appended to it.

### New in the engine: the race kerbs (opt-in `road_wear.kerbs`)

High Plains' 20 traced kerb runs (`1KERB_circuit_<k>`, ledger 0081) carry their own paint in their own UVs: u runs across
inside the colour's cell of `kerb_atlas_hp.png`, and v = arc / 2 m repeats. So they cannot take the road's world atlas.

- `road_wear.kerb_*` and `road_wear_blend._kerbs` give each kerb face the rubber the same line puts on its centroid (the
  same `wear_at` the road's atlas is baked from).
- That rubber picks one of 16 copies of the kerb's own paint laid side by side. Copy k is the paint x (1 - k x 0.22 / 15),
  and copy 0 is the paint byte for byte. 16 levels is **[invented]**: a 1.5 % step.
- Each face's u moves into its copy. v and the positions are untouched.
- The material row is the exporter's own stock row (ksPerPixel, no VAR, so the add-on's 0.4 / 0.4 as in 0.1.6), with
  txDiffuse changed to the levelled paint.
- Each face's ring and level are written to `data/road_wear.json` for the gate.
- 18 of the 20 runs lie partly over the lane at their measured offsets (`kerbs.built.json` in_vs_ribbon_edge_m < 0). The
  line's tyres reach them there.
- Gate rows `kerb_materials`, `kerb_paint` and `kerb_levels` (fleet/GATES-CHANGELOG.md 2026-11-10). The road rows are
  unchanged and no threshold moved.

Proven so far without a build:

- `tests/aerial/test_road_wear_kerbs.py` passes 6 of 6, and `test_road_wear.py` 7 of 7.
- A synthetic Blender scene went through `_kerbs` and the three rows (`source/road_wear/mac_read/kt_*.py`): one kerb, 145
  faces, 122 darkened. Every row passed, and a triangle moved one level failed `kerb_levels`.

### The config (`tracks/high-plains-lm/track.config.json` 0.1.7, `ship.json`)

- `road_wear` = Milford's key with these changes:
  - `surfaces` 1ROAD + 1KERB_SIDEWALK (the circuit-edge-flush strip, ledger 0087);
  - `texel_m` **0.2**;
  - the aerial below;
  - `lines` full, recorded `source/road_wear/fast_lane.full.ai` when one exists;
  - `kerbs` {prefix 1KERB_CIRCUIT_, levels 16}.
- ship.json:
  - gate `road_wear` after kn5_ground;
  - sync_in: the aerial required and the recorded line optional;
  - sync_out: the three road_wear records.

### The aerial (measured on the Mac: `source/road_wear/mac_read/naip_read.py` + `.log`)

- **The image is committed** as `source/road_wear/naip_2023_030_hp.png`, beside its record `naip_2023_030_hp.json`:
  - USDA NAIP 2023-09-28, `co_m_3910317_ne_13_030_20230928_20240104`, public domain;
  - ledger 0081's crop, `/Volumes/Drive/codex/kerb_work/img/high-plains_2023_030.png`, md5 4da61327, byte-identical;
  - 4495 x 1202 px at 0.300 x 0.300 m, 10,762,351 B;
  - corners [W, N, E, S] exact (`tools/naip_crop.py`), bbox_lonlat (W, S, E, N) in the config.
  - It is **not LFS** (`.gitattributes` puts only `*_z18` aerials there).
  - The track's other on-disk aerial, `tracks/high-plains/source/naip_2023_hp_z18.png`, is a 133 B LFS pointer here.
- **Coverage**: the whole lap. 0 of 3,205 centreline stations at 0 / +-8 / +-10 m fall outside the image or on a black pixel.
  **No download was needed.**
- **Texel 0.2 m**:
  - It is finer than the 0.3 m pixel, so every tone the photo carries is kept.
  - It is a whole divisor of the 4 m detail tile, so the grain keeps the prep's grid and phase across the atlas seams.
  - Milford's rule, half the pixel (0.15 m), is not a divisor: 26.7 texels a tile, and the gate's detail_phase row would
    fail.
  - The next divisor, 0.125 m, needs an 8192 px atlas (4x Milford's VRAM).
  - Estimated off the centreline's cells: 78 cells of 64 m, a 4096 px atlas at 74-90 % fill. The bake measures the real
    plan on the built road.
- **Registration**: (-1.25, +1.25) m, contrast 0.0507 -> 0.0595. This was measured on the centreline +- 6 m, not the built
  road, so it is an estimate. The bake measures it again on the built road.
- **Shadows and paint**:
  - Shadows: 4.0 % of the road (masks grown by one aerial pixel).
  - The dark tail (< 0.72 x the lit median) is 3.57 % at b/r 1.103 against the lit 0.928, so Milford's shadow rule (0.72,
    1.06) still separates them here.
  - Paint: 9.54 % (raw 3.22 % over 1.45 x: the painted edge lines).
  - Tone p01 / p50 / p99: 0.712 / 0.999 / 1.300.
- **Model line**: the minimum-curvature line [model]. The committed `ai/full/fast_lane.ai` is the generated centreline draft
  (`ai_draft.json` "GENERATED DRAFT", offset_max 0.238 m). Model lap 89.5 s, 56.6-252 km/h.

### Finding: at 0.3 m the photo already shows the rubber

At Milford's 0.5 m it did not: the band there regressed to 0.3 % darker. At High Plains it does, measured on lit asphalt at
least 1.5 m inside the edges, at stations where the model line runs 2 m or more off the centre:

| distance from | 0-0.5 m | 0.5-1 | 1-1.5 | 1.5-2 | 2-3 | 3-4 |
|---|---|---|---|---|---|---|
| the model line | **0.915** | 0.925 | 0.935 | 0.958 | 0.988 | 1.010 |
| its mirror across the centreline | 1.075 | 1.086 | 1.074 | 1.076 | 1.055 | 1.031 |
| the centreline | 1.000 | 1.013 | 1.017 | 1.027 | 1.025 | 1.023 |

- Fitted on the model line's tyre profile, the photo's darkening is **A = 0.120** (measured; `fit_sim.log`).
- Consequence 1, double counting. The bake draws the rubber over the photo's tone, so with Milford's **0.22 [invented]** the
  line ships about 1 - 0.88 x 0.78 = 31 % darker than the lit road, where the photo shows about 12 %. At Milford that was
  right, because the photo showed nothing; here it counts the rubber twice.
- Consequence 2, the gate may go red. Simulated on the centreline corridor (`gate_sim.log`), the `rubber` row gives:

| drawn A | centroid (limit 0.15 m) | depth / declared |
|---|---|---|
| 0 | -0.668 m | - |
| 0.10 | -0.295 m | 1.55 |
| 0.22 | **-0.175 m** | 1.22 |

  The photo's own band sits about 0.7 m right of the model line at the gate's stations (or that much off in registration).
  So the row may be **red on the built road**. The PC's reference build settles it. Nothing is loosened if it is red.
- An attempt to read the line off the photo's rubber instead (`fit_sim.py`) is not usable as it stands:
  - the lateral shifts run to the search bounds (p5 / p95 -2.5 / +2.5 m) on edge paint and patches;
  - its A is 0.195.
  - It is not in the engine.
- What 0.1.7 first shipped, now superseded by the next section: **Milford's numbers unchanged** (0.22, spread 0.70, base 0.35). It is the feature as Milford was built,
  rolled out.
- **Kevin's call** (made the same day: (b), "Use the photo's rubber"; see the next section):
  - (a) keep 0.22;
  - (b) draw nothing on the asphalt (the photo is the wear) and give the kerbs the measured 0.12. This needs the rubber row
    to judge a photo-borne band, which is a gate change for Kevin's word, not a loosening slipped in;
  - (c) record a racing line in CSP (runbook step 9), which puts the drawn band where cars really run.

### High Plains 0.1.7: the photo's rubber (Kevin's call, 2026-11-10)

Kevin, verbatim: **"Use the photo's rubber"**. That is option (b) above, and it is what 0.1.7 now ships. It replaces
"Milford's numbers unchanged" for this track.

- **`road_wear.rubber: "photo"`** (opt-in; absent or "drawn" is Milford's mode, unchanged).
  - The asphalt gets **no drawn band**: the photo's tone carries the rubber.
  - The bake measures the photo's darkening across each line against its mirror across the centreline
    (`road_wear.photo_rubber`, on lit asphalt at least 1.5 m inside the built road, stations where the line runs at least
    2 m off the centre) and writes it to `data/road_wear.line.<layout>.json`.
  - The min-curvature line [model] is kept only to measure that and to say which kerb faces it clips.
- **The kerbs** take the measured profile D(u) at each face's signed offset from the line, through the 16 levels, whose top
  is the measured peak. The drawn model's 0.22 / 0.70 m / 0.35 and the speed weighting are not used here.
- **The gate**:
  - The drawn `rubber` row is not run in photo mode; it would demand a band that is not drawn.
  - The new `photo_rubber` row judges the shipped atlas's line-vs-mirror darkening against the bake's measurement on the
    photo: depth within 0.02, centroid within 0.15 m, the photo's depth at least 0.03 (fleet/GATES-CHANGELOG.md
    2026-11-10 later, every number marked).
  - No threshold of the drawn mode moved.
- **Measured on High Plains**, Mac, on the centreline corridor (`source/road_wear/mac_read/photo_sim.log`):
  - The photo's depth is **0.146** (|u| <= 0.75 m), its peak **0.156**, its centroid +0.42 m (642 stations).
  - The simulated shipped atlas reads 0.141 / +0.420 m, so photo_rubber **PASSES**.
  - The drawn 0.22 still fails the old row the same way: centroid -0.175 m (`gate_sim.log`, re-run).
  - The kerbs' top level is 0.156, in steps of 0.0104.
  - The profile is skewed (D 0.04 at u = +4 m, 0 by -3.5 m), so a kerb face 4 m right of the line steps down about 4
    levels at the profile's edge.
- **Which number.** The brief quoted 0.120. That is the regression of the photo on the model line's tyre profile
  against 3-4 m out (`fit_sim.log`). The line-against-mirror measure that was asked for reads 0.146 / 0.156, and that is
  what the build uses. The mirror takes out the road's own across-the-road shading but keeps any off-line dust (the outside
  of a corner reads lighter), so it reads higher than the regression.
- **Default for the other 0.3 m circuits.** Photo mode is the default when Pueblo, Aspen, Grand Junction and Pikes Peak
  (NAIP 2023 0.3 m on disk) get road wear, each checked by the same `photo_min_depth`.
  - Milford keeps its drawn band: at 0.5 m its photo shows under 1 %.
  - Lake Murray names nothing.
- Unit tests: `tests/aerial/test_road_wear_photo.py` (6). Lake Murray as before (`mac_read/lm_checks.log`; this pass
  touches neither its tools nor its tree).

### Lake Murray unchanged (Mac, `source/road_wear/mac_read/lm_checks.log`)

- `git diff 98bb351 -- tracks/san-diego-lake-murray` touches only the snapshot's `export_kn5_addon.py` (13 lines), its
  MANIFEST.md5 line and one PENDING-MIRROR.md5 line: the known mirror lines.
- `tools/trim_connectors.py` (8a456516), `tools/make_treefx.py` (d759fe89) and `tools/ship_sd.sh` (5a4bbe29, no
  `road_wear`) are byte-identical to the base. Lake Murray's config names no `road_wear`.
- **Trim A/B** on a copy of Lake Murray's data: connectors 664da93b, mouths b73b70f4, median_bands f0c97952 and the log
  63af07cc. These are ledger 0089's base numbers, **byte-identical**.
- **make_treefx A/B**: `plan(all_species=True)` with 98bb351's tool and with the branch's gives 8ce38a01 / 21,219 lines on
  both sides. **SAME.**
- The exporter without the key: Milford's export A/B (above) holds. Its `.ini` was byte-identical and its kn5s
  `kn5_equiv` EQUIVALENT.

### Records still owed (the PC)

- The gate column.
- The sizes.
- mesh_diff and compare_ab against the installed 0.1.6.
- Stills 0.1.6 vs 0.1.7 of the front straight, the kerbed corner and the fast curve.

All of these are runbook 0084-2's output and land under `tracks/high-plains-lm/source/road_wear/pc_017/`. The 0.1.6 column
to compare against is ledger 0089's: drive_test 0 / 0 / 0.62 / 0 / 0, audit 0, kn5_ground 0 / 1,908 p95 0.021,
house_seat PASS, edge_report 4,051 scalars, road kn5 14,511,475 B.

### Runbook 0084-2 (PC): reference build, rehearsal, compare every row, install when green, then the in-game look

Kevin: "I always want newer builds". A green 0.1.7 installs without asking, and the old build goes to the archive.
Downloads still need his word, and none is needed here.

1. **Worktree.**
   - `git fetch && git worktree add D:/k10-worktrees/hp-rw origin/claude/high-plains-road-wear`, at the head this section
     was pushed in or later.
   - `git status` must be clean.
   - Check `md5sum tracks/high-plains-lm/source/road_wear/naip_2023_030_hp.png` = **4da61327cb66cb155594cc48cd99b077**.
2. **ENG.**
   - `cp -r D:/k10-scratch/eng_hplm D:/k10-scratch/eng_hplm_rw`. eng_hplm itself stays untouched for any 0.1.6 rebuild.
   - Copy the worktree's `scripts/ac/export_kn5_addon.py` over `eng_hplm_rw/scripts/ac/export_kn5_addon.py`. Its md5 must be
     **83b231e840c09b34ef32cde98dbf2c35**.
   - Record the md5s of `eng_hplm_rw/scripts/ac/pbr.py` (expect 44615dd3) and `build_kn5_loop.py` (2a653ee1 or its
     PENDING-MIRROR predecessor; note which).
   - Real engine-july is not edited until the mirror.
3. **The K-rail re-seat (the PC's own change, carried in this same 0.1.7 build).**
   - High Plains 0.1.6's pit-wall K-rail `pit_wall_lidar` stands about 0.29 m buried: declared 1.03 m, 0.74 m showing at
     p50. This is Milford G1's mechanism.
   - The PC widens `tools/reseat_bespoke_blend.py`'s prefixes, opt-in `scenery.bespoke.reseat_prefixes` adding
     `"1WALL_KRAIL"`. The tool and its `prep_prep` call come from `claude/milford-0111`.
   - It sets `scenery.bespoke.reseat_on_prep: true` in High Plains' config.
   - Commit (fetch + rebase, never force) **before** step 4, so both builds are of one head.
   - In `prep_prep` the re-seat goes before the road-wear bake, as on Milford 0.1.9. The two commute: the re-seat moves only
     the rail kinds, and the bake writes only 1ROAD / 1KERB_SIDEWALK / 1KERB_CIRCUIT UVs and materials.
   - **The seat numbers it should then show** (`data/reseat_bespoke.json` and a `seat_built` read of the built kn5):
     - `pit_wall_lidar` 1.03 m showing at p50 (from 0.74), 0 m buried (from 0.29);
     - every other K-rail's p50 within a centimetre of its declared height;
     - no 1ROAD / 1KERB / 1GRASS vertex moved by the re-seat (its own report).
   - If that is not ready, build without it. The rest of this runbook does not depend on it.
4. **Reference build** from an EMPTY workshop:
   - `mkdir -p D:/k10-scratch/hp_rw_ref/data`, then
     `SHIP_PROJ=D:/k10-scratch/hp_rw_ref AIROSO=D:/k10-worktrees/hp-rw ENG=D:/k10-scratch/eng_hplm_rw bash tools/ship_track.sh high-plains-lm --no-install > hp_rw_ref.log 2>&1`.
   - No force. Look for:
     - `[road_wear] ... atlas 4096 px at 0.2 m` (8192 is possible if the built road takes more cells: record it);
     - `aerial registered to the built road: shift (...)`;
     - `line full: model: minimum curvature inside the built edges`;
     - `line full: the photo's rubber against the mirror: depth ~0.15 ...` (the Mac's estimate on the centreline corridor:
       0.146, peak 0.156, centroid +0.42 m; the built road may differ a little: record it);
     - `kerbs: 20 meshes, ... darkened (levels 16, step ~0.0104 ...)`;
     - `[export] road wear: [...]` naming 1ROAD_road_mat, 1KERB_sidewalk_mat and the 20 `1KERB_circuit_<k>_mat`;
     - every `[road_wear_check]` row PASS: materials, density, no_repeat, detail_phase, tone, **photo_rubber** (in place of
       rubber: photo mode draws no band), kerb_materials, kerb_paint, kerb_levels;
     - SHIP OK.
   - **If any row is red**, stop. The Mac's photo-mode simulation passes photo_rubber by 0.006 in depth and 0.002 m in
     centroid; the drawn `rubber` row is not run in photo mode. Nothing is changed, loosened or forced. Commit the log and every `data/*.json` under `source/road_wear/pc_017/ref/`
     and report the row.
5. **Rehearsal** from a second EMPTY workshop, `D:/k10-scratch/hp_rw_reh`, with the same command and the same head.
6. **Compare every row, reference against rehearsal.**
   - Every scalar of drive_test.full, audit, kn5_ground_check.full, house_seat, edge_report and road_wear_check must be
     equal.
   - `data/road_wear.json` must be equal except for absolute paths: m0, the plan, the registration, the kerb levels.
   - The two road kn5s must be byte-equal or `tools/kn5_equiv.py` EQUIVALENT (tangents only). Any other difference: no
     install; report it.
7. **Against the installed 0.1.6** (`D:/k10-scratch/high_plains_lm/build/high_plains.kn5`, or the AC folder's kn5):
   - `python tracks/high-plains-lm/source/road_wear/mesh_diff.py <0.1.6.kn5> D:/k10-scratch/hp_rw_ref/build/high_plains.kn5 --json pc_017/mesh_diff.json`;
   - `python tracks/high-plains-lm/source/road_wear/compare_ab.py <0.1.6.kn5> <ref kn5> 1ROAD 1KERB_SIDEWALK 1KERB_CIRCUIT_ [--moved 1WALL_KRAIL]`
     (`--moved` only when step 3 ran).
   - Pass means:
     - every 1ROAD / 1KERB / 1GRASS / BUILDING / MARKINGS / PADAPRON / ROOFTOP mesh's positions are bit-identical (only the
       K-rails' may move, under step 3);
     - UVs and materials changed only on 1ROAD_road, 1KERB_sidewalk and the 1KERB_circuit_* meshes;
     - the kerbs' v, shader and VARs are unchanged;
     - textures added: `road_wear_macro.png`, `road_wear_detail_1road.jpg`, `road_wear_detail_1kerb_sidewalk.jpg`,
       `road_wear_flat_nm.png`, `road_wear_kerb_kerb_atlas_hp.png`;
     - textures dropped are the ones they replace;
     - textures changed: none.
   - The gate numbers must equal ledger 0089's 0.1.6 column (above). The only expected changes are audit's road / curb
     vertex counts (the strip's UV seams, as Milford) and, under step 3, the K-rails' seat.
   - Lake Murray: `git diff 98bb351 -- tracks/san-diego-lake-murray` shows only the three mirror files. Re-run the trim and
     make_treefx A/B as `mac_read/lm_checks.log`; the numbers must be the same.
8. **Green on every row = install**, with no further word.
   - Move the old workshop to `high_plains_lm.0.1.6`.
   - Run the same command without `SHIP_PROJ` and without `--no-install`, AC closed. The install parks 0.1.6 in
     `D:/k10-track-archive/<stamp>/`.
   - `python tools/ac_tidy.py record <folder> --track high-plains-lm --branch claude/high-plains-road-wear --sha <head> --engine lm-v4`
     on `claude/ac-tidy`.
   - Re-render the menu picture with 0.1.6's camera.
   - **Stills**: `python tracks/high-plains-lm/source/road_wear/pick_spots.py D:/k10-scratch/hp_rw_ref pc_017/spots.json`
     gives front straight, fast curve and kerbed corner (the most-darkened kerb face). Then
     `blender --background --factory-startup --python-exit-code 1 --python tracks/high-plains-lm/source/road_wear/road_wear_stills_blend.py -- <ws>/blender/split/loop_main.blend <out-prefix> pc_017/spots.json`
     on 0.1.6's workshop (`high_plains_lm.0.1.6`) and on the reference. Compose the pairs as
     `tracks/high-plains-lm/source/stills/road_wear_016_vs_017_{front_straight,kerbed_corner,fast_curve}.jpg`.
   - Commit the records (`source/road_wear/pc_017/`: both logs, the gate JSONs, road_wear.json, mesh_diff, compare_ab, the
     sizes) and append the gate column 0.1.6 / 0.1.7 here. Fetch + rebase, never force.
9. **In game** (Kevin's drive is the verdict).
   - CSP Objects Inspector on the road: shader `ksPerPixelMultiMap_NMDetail`, the four slots bound, detailUVMultiplier
     204.8 (= 4096 x 0.2 / 4), ksAmbient / ksDiffuse 0.4.
   - Look for:
     - the cracked grain as crisp as 0.1.6 at car height (missing = the macro's alpha reads the other way: ledger 0084
       "Unverified");
     - the road neither black nor see-through;
     - the photo's own rubber (no drawn band): darker where cars really run, about 15 % against the off-line asphalt;
     - the kerbs where the line rides them darker (up to the measured ~15 %) than the ends of the same run, their paint
       otherwise unchanged;
     - no 4 m grid in the tone.
   - **Record a racing line** during the drive (CSP's AI recorder, the full layout). Copy its `fast_lane.ai` to
     `tracks/high-plains-lm/source/road_wear/fast_lane.full.ai`. The next build's rubber then follows where the car really
     ran: the kerbs' faces are then picked by the real line, and the photo's rubber is measured against it.

### High Plains 0.1.7: the PC's first builds red on detail_phase; texel 0.25 m (PC, 2026-11-10)

- Both builds, reference `hp_rw_ref` and rehearsal `hp_rw_reh`, came from empty workshops at a79b6a6 (ENG `eng_hplm_rw`). They were identical, and both stopped at `road_wear_check` detail_phase: worst 0.20001 tiles, detailUVMultiplier 204.8.
- 0.2 m broke the detail phase (204.8). 0.25 m is chosen so the multiplier is whole (256); it is still finer than the 0.3 m photo, so no photo detail is lost.
- Every other row passed. The re-seat (step 3) moved pit_wall_lidar +0.30 m at p50.
- Records: `tracks/high-plains-lm/source/road_wear/pc_017/{ref,reh}/` (399d03c).
- The bake now refuses a fractional multiplier before baking (GATES-CHANGELOG 2026-11-10 PC).

### High Plains 0.1.7: green and installed (PC, 2026-11-10)

- **Head** 2981db6d (texel 0.25 m + the whole-multiplier guard on a79b6a6's K-rail re-seat). ENG `eng_hplm_rw`.
- **Reference + rehearsal** from empty workshops `hp_rw_ref` / `hp_rw_reh`: SHIP OK, no force, every gate green.
  - `road_wear_check` passes every row: detail_phase worst 1e-05 tiles at multiplier 256; photo_rubber shipped 0.14143 vs declared 0.14139, centroid -0.1061 vs -0.1116 m; the kerb rows.
  - Atlas: 4096 px at 0.25 m, 74 cells, 45.2 % used.
  - The two builds are identical: drive_test / audit / kn5_ground / house_seat / edge_report / road_wear_check / road_wear / reseat JSONs equal bar paths, and the kn5s kn5_equiv (tangents only), 17,730,716 B.
- **Against the installed 0.1.6**:
  - mesh_diff: 1ROAD, 1KERB x21 (the strip and the 20 circuit kerbs) and two 1WALL (KRAILBW_1 / _4, the re-seated) differ; every 1GRASS / BUILDING / MARKINGS / PADAPRON / ROOFTOP mesh is equal.
  - Textures: asphalt_cracked_diffuse / building_diffuse / kerb_atlas_hp dropped; the road-wear set added (macro 2,089,872 B, detail_1road 3,395,491, detail_1kerb_sidewalk 331,034, flat_nm 76, kerb atlas 2,549).
  - compare_ab's "1WALL_KRAILBW_1 / _4: UVs differ" is the re-seat's re-triangulation: the same 784 / 192 corner points (plan + UV) are each raised by the re-seat's dz (p50 +0.303 / +0.102), and the moved quads split on the other diagonal. No UV moved.
  - Every gate scalar equals 0.1.6's, except audit wall_verts 7,078 -> 7,170 (the re-seated rails' splits).
- **The seat** (`wall_seat_abs.py`, top-ridge points vs the ground under them):

  | rail | declared | 0.1.6 showing p50 | 0.1.7 showing p50 |
  |---|---|---|---|
  | pit_wall_lidar | 1.03 | 0.74 | **1.03** |
  | pit_wall_naip_rest | 0.81 | 0.71 | **0.81** |
  | the other six | | as 0.1.6 | as 0.1.6 |

  The re-seat moved none of the other six, because the band's mechanism isn't theirs: pit_paddock_lidar 0.54 of 0.59, pit_paddock_naip_rest 0.76 of 0.81, back_straight_lidar 1.23 of 1.13.
- **Installed** 2026-11-10 13:28 from an EMPTY `D:/k10-scratch/high_plains_lm`; 0.1.6's workshop is kept as `high_plains_lm.0.1.6`.
  - "doooom Colorado — High Plains Raceway" 0.1.7.
  - kn5_equiv to the reference.
  - The install step parked 0.1.6 in `D:/k10-track-archive/2026-11-10_132827/`.
  - Menu picture: s0 at -0.3 EV, as before.
- Records: `source/road_wear/pc_017/green_{ref,reh}/`.
- Not driven.

### Pueblo 0.1.4: red, not installed (PC, 2026-11-10 overnight)

Kevin to the Mac: "build the road wear for the other circuits on the pc overnight". The Mac's rule for the 0.3 m
circuits: photo mode, and "If a 0.3 m track's photo shows no measurable rubber (its own depth under 0.03), stop that
track and report. Don't switch modes or tune."

- **Head** 483038aa on `claude/pueblo-road-wear` (from 6a788506). ENG `eng_pulm_rw` = eng_pulm plus the current exporter
  (export_kn5_addon.py 900ea391, as eng_hplm_rw).
- **Reference `pu_rw_ref` + rehearsal `pu_rw_reh`**, both from empty workshops, EXIT 1 in prep at the bake. They are
  identical: every data/*.json byte-equal, the same rows.
  - `aerial registered to the built road: shift (+1.75, +0.25) m`, contrast +0.0328 -> +0.0413; shadow 8.21 %, paint 2.2 %.
  - **The photo's rubber: depth 0.02166** over |u| <= 0.75 m, peak 0.02964, centroid +0.216 m (1275 stations). That is
    under the gate's photo_min_depth 0.03; High Plains' read 0.146. NAIP 2023 does not resolve Pueblo's rubber. By the
    Mac's rule the track stops here: no drawn band, nothing tuned.
  - **And the bake refused the kerbs:** `FATAL: 1KERB_circuit_0: u 0.000..2.111 outside the paint texture (0..1): its
    copies would bleed into each other`. Pueblo's red / white kerbs (textures/kerb_redwhite.png) repeat their paint along
    the run. The level copies need each face's u inside one copy of the texture, as High Plains' kerb atlas has it. Pueblo
    would need its kerbs re-mapped into 0..1 (or the levels laid out another way) before road_wear.kerbs can level them.
- Installed: still **0.1.3**. Records: `source/road_wear/pc_014/{ref,reh}/` (both logs, every data/*.json).
- Open, for the Mac and Kevin:
  - Pueblo's road wear needs a decision: drawn mode, as Nevada and Del Mar (Kevin's "Use the photo's rubber" was for
    photos that show it), or no road wear.
  - Its kerbs need their UVs into 0..1 first.

### Aspen 0.1.5: red, not installed (PC, 2026-11-10 overnight)

The same brief and rule as Pueblo above. Photo mode on NAIP 2023 at 0.3 m; stop when the photo's own depth is under 0.03.

- **Head** a473d209 on `claude/aspen-road-wear` (from 6a788506). ENG `eng_aslm_rw` = eng_aslm plus the current exporter
  (900ea391).
- **Reference `as_rw_ref` + rehearsal `as_rw_reh`**, both from empty workshops, EXIT 1 in prep at the bake. They are
  identical: every data/*.json byte-equal, the same rows.
  - `aerial registered to the built road: shift (-1.25, -0.25) m`, contrast +0.0252 -> +0.0276; shadow 0.0 %, paint 3.85 %.
  - **The photo's rubber: depth -0.00792** over |u| <= 0.75 m, peak 0.041, centroid +0.299 m (500 stations). The model
    line reads no darker than its mirror, so the photo shows no rubber (High Plains 0.146, Pueblo 0.022). The track stops
    by the Mac's rule.
  - **And the kerbs:** `FATAL: 1KERB_circuit_0: u 0.000..2.099 outside the paint texture (0..1)`, as Pueblo. The three
    kerb runs repeat their paint along the run.
- Installed: still **0.1.4**. Records: `source/road_wear/pc_015/{ref,reh}/`.
- Open, as Pueblo: the mode (drawn or none) is Kevin's call, and the kerbs need their UVs into 0..1.

## Engine fixes after the overnight run (Mac, 2026-11-10; code and tests only, no track build)

The PC's overnight run (Kevin: "build the road wear for the other circuits on the pc overnight") hit two engine limits.
Its notes are on `claude/pueblo-road-wear` a181c607, `claude/aspen-road-wear` 9992b8a3 and
`claude/pikes-peak-road-wear` d3fb491f (`pc_022/density_offenders.txt`). Branch `claude/road-wear-engine-fixes`, from main
06d782f. Gate log: fleet/GATES-CHANGELOG.md 2026-11-10 (Mac). No threshold moved.

### 1. The kerbs: paint that repeats (Pueblo 0.1.4, Aspen 0.1.5)

- **The failure.** `FATAL: 1KERB_circuit_0: u 0.000..2.111 outside the paint texture (0..1)` (Aspen 0..2.099).
- **Why u passes 1.** A kerb without a `kerb.atlas` cell gets u = offset / painted width (`tools/author_kerbs_blend.py`).
  The back fall past the painted width runs on to u = (w + ramp_out) / w, and the stock exporter's wrap addressing
  repeats the paint there. A level copy can't wrap, because its neighbour copy sits beside it.
- **The fix** (`scripts/aerial/road_wear.kerb_unwrap / kerb_repeats`, `kerb_wear_atlas` / `kerb_u` with `repeats`):
  - Every face's u moves back by its whole repeats, floor(its smallest u + 1e-6). frac(u) is what the wrap sampled, so
    every point reads the same texel.
  - A face still wider than one repeat (Pueblo's back fall, 1.0 .. 2.111) is **not split**. Each level copy holds
    `repeats` tiles of the paint side by side. That is the smallest power of two that holds every face, with more than
    one float32 step left before the copy's right edge. The tile seam inside a copy is the same column-W-1-to-column-0
    seam the wrap had.
  - Splitting would add vertices and faces and re-triangulate. This way no face, triangle or vertex changes: the
    physics, the gate's face join and the writer's vertex count are all as before.
  - The cost is the atlas width. Pueblo / Aspen's 64 px kerb_redwhite.png gives 64 x 2 x 16 = 2048 x 256. The bake
    refuses anything wider than 16,384 px (Direct3D 11's largest texture).
  - data/road_wear.json `kerbs` gains `repeats`, `faces_unwrapped`, `u_range` and `u_max_unwrapped`, only when the paint
    repeats.
- **The gate.** kerb_paint reads `repeats`: every tile of copy k is the paint x (1 - k step). kerb_levels is unchanged.
- **Unchanged where the paint doesn't repeat.** High Plains 0.1.7's cells (u 0.05 .. 0.95) move by exactly 0 and get
  repeats 1, so the arithmetic is the old code's, bit for bit.
- **The edge of a copy.** Bilinear filtering at a copy's outer edge reads half a texel of the next copy, as High
  Plains' copies always have. That isn't changed here.

### 2. The density row: slivers (Pikes Peak 0.2.2)

- **The failure.** 2 of 28,656 triangles, both slivers on the oval's apron pads:
  - 1ROAD_pad_NE 0.0020 m2, edges 1.01 / 5.06 / 6.07 m, 0.66 mm tall, read 0.86 % off;
  - 1ROAD_pad_NW 0.0189 m2, read 0.51 % off.
- **Why: the measurement, not the atlas.**
  - The bake gives every face one tile and u = east / (atlas_px x texel_m) + the tile's offset. That is exact for any
    shape.
  - The row's UV Jacobian divides by the triangle's height. So the kn5's float32 rounding (6e-5 m in u at 4096 px x
    0.25 m) is amplified by length / height, here ~10,000.
  - NE-shaped slivers mapped exactly and stored as float32 fail the old row 197 times in 200.
- **The fix** (`tools/road_wear_check.density_row`):
  - Each triangle gets a rounding bound on its Jacobian. Where that bound is under the tolerance (every road triangle),
    the triangle is judged by the Jacobian exactly as before.
  - Where it isn't, the triangle is judged by the texel footprint of its edges: |UV step in metres - the edge on the
    ground| <= density_tol x |edge|. A really mis-mapped sliver still fails (stretched 1 %, or one corner a texel off).
  - A triangle no float32 number can judge (every edge under ~4 cm) is counted and listed as `unjudged`. That is the one
    exemption, and its rounding model `f32_ulps` 1.0 is **[invented]**.
  - The old row's silent |det| < 1e-6 skip is gone from density: those triangles are edge-judged now.

### Proven (Mac)

- **Tests.** `tests/aerial/test_road_wear_*.py` 31 of 31 (20 before):
  - `test_road_wear_density.py`: 7 new;
  - `test_road_wear_kerbs.py`: 4 new. A run with u 0..2.1, its faces straddling 1.0 and 2.0: every texel centre each face
    covers reads the wrap's paint column from its level's copy; v is untouched; no loop is added. High Plains' range is
    byte for byte; kerb_paint passes 16 x 2 tiles and fails one texel off.
- **The bake in Blender, on synthetic scenes** (Blender 5.1.2 on the Mac, not the PC's 4.2;
  `tracks/pueblo-lm/source/road_wear/mac_fix/kerb_ab.log`), main's `_kerbs` against this branch's:
  - High Plains' shape gives identical UVs, atlas, record and gate rows (the material rows equal bar the code tree's
    path).
  - A Pueblo-shaped scene (u 0..2.111): main FATALs. This branch bakes it with repeats 2, positions and topology
    unchanged, every corner on its own paint texel, and all three kerb rows PASS. A triangle moved one level FAILS.
- **The installed tracks.** Milford 0.1.11, High Plains 0.1.7 and Nevada 0.1.6:
  - They name no repeating kerb paint, and the bake's non-kerb code is untouched (the diff is inside `_kerbs` only).
  - Their own roads, rebuilt from their records and mapped as the bake maps them
    (`tracks/pikes-peak-lm/source/road_wear/mac_fix/density_ab.log`), get the same density verdict and the same worst
    numbers before and after. Every triangle is judged by the Jacobian.
  - The kn5s are on the PC, so the gate has not been re-run on them here.
- **Lake Murray** names no road_wear key, and no shared code outside the three road-wear files changed. There is no LM
  A/B to run.
- `tests/tools/test_ship_track_chain.py` fails 4 tests on the Mac on main 06d782f as well. That is unrelated.

### Runbook 0084-3 (PC): rebuild Pueblo, Aspen and Pikes Peak on these fixes

(Superseded by "Runbook 0084-3, as Kevin picked" below: tone only, all four circuits.)

Run this once Kevin picks each track's rubber mode. All three photos show no rubber the gate can use: Pueblo 0.022,
Aspen -0.008, Pikes Peak -0.008, all under photo_min_depth 0.03. So it is "drawn" (Milford's band, its numbers
[invented]) or no road wear. Nothing is tuned until he says.

1. Merge `claude/road-wear-engine-fixes` (after Kevin's yes) into each track's branch, set `road_wear.rubber` to his
   pick, and rebuild reference + rehearsal from EMPTY workshops, as runbook 0084-2.
2. **Pueblo / Aspen.** The bake log shows `kerbs: the paint repeats (u 0.000..2.111): N faces moved back ...; each level
   copy holds 2 tile(s)`, and the kerb atlas `road_wear_kerb_kerb_redwhite.png` is 2048 x 256. kerb_paint reports
   `repeats 2`. kerb_levels: corners_in_two_levels 0, outside_every_declared_face 0.
3. **Pikes Peak.** density PASS. edge_judged should include 1ROAD_pad_NE / _NW's slivers (edge_off 0), with every other
   triangle jacobian_judged. Report edge_judged and unjudged and list unjudged_list. Then stage_force (the hairpin's
   verdict), which the red chain never reached.
4. **The installed tracks.** Re-run `python tools/road_wear_check.py <proj> --kn5 <installed road kn5>` on Milford
   0.1.11, High Plains 0.1.7 and Nevada 0.1.6. Every row should equal its record: density equal, plus the new keys
   (expect edge_judged = the slivers, if any, and unjudged 0). No rebuild is needed for them.
5. Green = install, older build archived (Kevin 2026-11-09). Red = stop and report.

## Tone only, no rubber (Kevin 2026-11-10; Mac, code and tests only, no track build)

Kevin, 2026-11-10, asked whether Pueblo, Aspen, Grand Junction and Pikes Peak (their photos show no rubber) take tone
only or Milford's drawn band: "Tone only, no rubber".

- **What the four photos show.** The photo's own line-vs-mirror depth (the PC's overnight run): Pueblo 0.022, Aspen
  -0.008, Grand Junction 0.002, Pikes Peak -0.008, all under `photo_min_depth` 0.03. Only High Plains' NAIP shows its
  rubber (0.146).
- **The new mode, `road_wear.rubber: "none"`** (`scripts/aerial/road_wear.rubber_mode`, `tools/road_wear_blend.py` 4c):
  - On the asphalt it bakes exactly what photo mode bakes, the photo's tone with no band drawn. Whatever the photo shows
    is in the tone; nothing is added.
  - The line is still found and the photo measured across it against its mirror, recorded in
    `data/road_wear.line.<layout>.json` as in photo mode, so the gate can show the atlas adds nothing.
  - It refuses `road_wear.kerbs` (FATAL): no rubber is drawn, so nothing levels the kerbs. Pueblo and Aspen drop the
    key, and their kerbs keep the stock paint and material they shipped before road wear. The repeating-paint fix above
    stays in the engine for a track that levels its kerbs.
  - It needs `road_wear.aerial` (FATAL without).
- **The gate row `no_rubber`** takes `photo_rubber`'s place (fleet/GATES-CHANGELOG.md 2026-11-10 (Mac, later)). For each
  line, the shipped atlas's line-vs-mirror depth must be within `photo_depth_tol` 0.02 of the photo's own: the atlas adds
  no band. The photo isn't asked to show rubber, and the centroid isn't judged. No threshold moved and none is added.
- **Unchanged.** "drawn" (Milford 0.1.11, Nevada 0.1.6) and "photo" (High Plains 0.1.7) are judged exactly as before;
  `photo_line_pass("photo", ...)` is the old expression term for term. Lake Murray names no road_wear key.
- **Proven (Mac).** `tests/aerial/test_road_wear_*.py` 34 of 34 (3 new, in `test_road_wear_photo.py`). On a photo with
  no band, "none" passes the atlas that is the photo and fails the same photo with a 0.15 band drawn on it, and "photo"
  fails it on min depth.

### Runbook 0084-3, as Kevin picked (PC): Pueblo, Aspen, Grand Junction, Pikes Peak, tone only

Kevin's words: "build the road wear for the other circuits on the pc overnight", then "Tone only, no rubber".

1. **Base.** This branch, `claude/road-wear-engine-fixes`, carries the kerb, density and tone-only fixes. Bring each
   track's overnight branch onto it (`claude/pueblo-road-wear` a181c607, `claude/aspen-road-wear` 9992b8a3,
   `claude/grand-junction-road-wear` c67ac595, `claude/pikes-peak-road-wear` d3fb491f). Nothing goes into main.
2. **Config, per track.**
   - `road_wear.rubber: "none"`, with `_rubber_doc` quoting Kevin's words.
   - Pueblo and Aspen: remove `road_wear.kerbs`.
   - Bump the version past the red overnight one: Pueblo 0.1.5, Aspen 0.1.6, Grand Junction 0.1.4, Pikes Peak 0.2.3.
3. **Build.** A reference build and a rehearsal, each from its own EMPTY workshop, matched row for row (runbook 0084-2),
   with every gate green and no force.
4. **What to expect.**
   - road_wear_check shows `no_rubber` PASS, with no `rubber` and no `photo_rubber` row. Report each line's
     declared_depth and shipped_depth.
   - The bake log reads `deepest rubber 0.0 %`.
   - No kerb rows on any of the four.
   - Pikes Peak: density PASS. Report edge_judged, unjudged and unjudged_list.
   - Pikes Peak's stage_force (the hairpin) comes next. Kevin's exemption was "for 0.2.0 only". Asked on 2026-11-11
     "May Pikes Peak 0.2.3 use the hairpin exemption you gave 0.2.0?", he said "Carry it over". So 0.2.3 may take
     that one forced verdict, the same as 0.2.0, and nothing else. It does not extend to later builds.
5. **The installed tracks.** As step 4 of the runbook above: re-run the gate on the installed Milford 0.1.11, High Plains
   0.1.7 and Nevada 0.1.6 road kn5s. Every row should equal its record. No rebuild.
6. **Green = install**, with the older build archived (Kevin 2026-11-09: "I always want newer builds"). Re-render the
   menu picture and push the records. Red = record why, skip that track, go on to the next. Change no threshold.

### Grand Junction 0.1.4: the gate's mask (Mac, 2026-11-11; code and tests only)

- **The PC's result** (records a5118c97). Reference and rehearsal are identical, and every row passes except no_rubber:
  the photo's own depth 0.00193 against the shipped atlas's -0.01907, 0.0210 apart against photo_depth_tol 0.02. Same 358
  stations, but the gate read 6,250 samples to the bake's 5,459.
- **The cause: the measurement, not the atlas.** The gate's restatement of where the bake measured was looser than the
  bake:
  - a 5-point edge test where the bake uses a ±1.5 m square;
  - a ±0.3 m shadow and paint growth where the bake grows them ±0.5 m;
  - the lit median where the bake uses the road median;
  - the nearest pixel where the bake samples bilinearly.
  So it took in samples near the edge at the corners, and on Grand Junction's flat photo that moved the depth by 0.02.
  The bake found 0.0 % shadow and 0.0 % paint there, so the edge test is most of it.
- **The fix.** `tools/road_wear_check.photo_mask` rebuilds the bake's own cells (GATES-CHANGELOG 2026-11-11 (Mac)). On a
  synthetic scene it equals the bake's numpy mask on all 58,466 road cells, and the two measurements agree sample for
  sample. No threshold moved.
- **Runbook 0084-4 (PC).**
  1. Re-run `tools/road_wear_check.py` on the installed High Plains 0.1.7, Pueblo 0.1.5, Aspen 0.1.6 and the built
     Pikes Peak 0.2.3. Each line should have shipped samples = declared samples (to float32 rounding), and every row
     should still pass. Report the depths before and after.
  2. Rebuild Grand Junction 0.1.4: reference and rehearsal from empty workshops, as runbook 0084-3. Green = install;
     red = stop and report.

### Runbook 0084-3 on the PC: tone only, Pueblo / Aspen / Grand Junction / Pikes Peak (PC, 2026-11-11)

Kevin's words (relayed by the Mac): "build the road wear for the other circuits on the pc overnight", then "Tone only,
no rubber". Installs under his "I always want newer builds" (typed on the PC); no force anywhere.

- **Base.** Each overnight branch merged with `claude/road-wear-engine-fixes` f71757b, nothing into main. The ledger was
  the only conflict: both sides appended, both kept. Exporter md5 900ea391 in every worktree and ENG copy. ENG copies as
  overnight (`eng_<x>_rw`). `tests/aerial/test_road_wear*.py`: 33 of 34 pass here. The one failure,
  `test_gate_kerb_paint_reads_the_repeated_copies`, is this PC's environment, not the code: Blender's python 3.11 loading
  the 3.14 PIL.
- **Configs** (rw_none.py, checked to round-trip):
  - `road_wear.rubber` photo -> `"none"`, with a `_rubber_doc` quoting Kevin and the overnight photo depth;
  - Pueblo and Aspen: `road_wear.kerbs` removed, so their race kerbs keep the stock paint;
  - `_doc` and ship.json's `_road_wear_doc` say tone only;
  - versions Pueblo 0.1.5, Aspen 0.1.6, Grand Junction 0.1.4, Pikes Peak 0.2.3.
- **Builds.** A reference + a rehearsal per track, each from its own EMPTY workshop (`<x>_none_ref` / `<x>_none_reh`),
  `--no-install`. Each install then built again from an empty workshop.

#### Pueblo 0.1.5: INSTALLED (2026-11-11 00:09; built at 39544272, records 4d825651)

- Reference, rehearsal and the install build are identical: gate rows 94 / 94 the same, kn5 kn5_equiv (tangents only,
  every other byte identical), AI lines equal, data/*.json equal bar workshop paths.
- road_wear_check, every row PASS:
  - materials;
  - density: 18,736 triangles; jacobian_judged 16,621, edge_judged 2,115, edge_off 0, unjudged 0;
  - no_repeat;
  - detail_phase (256.0);
  - tone (pearson_r 0.9235);
  - **no_rubber**, line full: declared_depth **0.02166**, shipped_depth **0.02615**.
  - No rubber or photo_rubber row, and no kerb rows. The bake reads `deepest rubber 0.0 %`.
- Against the installed 0.1.3 (compare_ab, prefixes 1ROAD 1KERB_SIDEWALK only, so the race kerbs had to stay as they
  were):
  - **19 / 19 meshes' positions bit-identical**;
  - UVs and material changed on 1ROAD_road and 1KERB_sidewalk only;
  - kn5 **10,742,931 -> 14,214,954 B**.
- Atlas looked at before installing (`pc_015/macro_cell_*.png`): the photo's asphalt with its crack sealant and edge
  paint; nothing parked on it.
- 0.1.3 parked in D:/k10-track-archive/2026-11-11_000936/. The folder holds the same 13 files, with no TreeFX bins
  before or after. Menu picture re-rendered (s3 of 6, -0.8 EV, same camera); the old one is backed up in
  2026-11-11_001157_previews.
- Records: `source/road_wear/pc_015/{ref,reh}/`, compare_ab_vs_installed.json, install.log.

#### Aspen 0.1.6: INSTALLED (2026-11-11 00:10; built at ca88fb14, records e3b0ab05)

- Reference, rehearsal and the install build are identical (gate rows 94 / 94, the one "differ" a path cut at a fixed
  width; kn5 tangents only; AI lines equal).
- road_wear_check, every row PASS:
  - density: 8,960 triangles; jacobian_judged 8,921, edge_judged 39, edge_off 0, unjudged 0;
  - detail_phase (128.0);
  - tone (pearson_r 0.8173);
  - **no_rubber**: declared_depth **-0.00792**, shipped_depth **-0.01293**;
  - no kerb rows; `deepest rubber 0.0 %`.
- Against 0.1.4: **7 / 7 meshes' positions bit-identical**; UVs and material on 1ROAD_road and 1KERB_sidewalk only; kn5
  **7,848,715 -> 9,739,836 B**.
- Atlas looked at (`pc_016/macro_cell.png`): clean asphalt tone.
- 0.1.4 parked in D:/k10-track-archive/2026-11-11_001032/; the same 13 files. Menu picture re-rendered.
- Records: `source/road_wear/pc_016/`.

#### Grand Junction 0.1.4: red on f71757b's gate (records a5118c97), then INSTALLED on adf3828's (below)

- Reference and rehearsal are identical (gate rows 84 / 84, kn5 tangents only). Both EXIT 1 at gate road_wear.
- materials, density (7,624 triangles, all jacobian_judged), no_repeat, detail_phase (128.0) and tone (r 0.9349) PASS.
- **no_rubber FAIL**: declared_depth 0.00193, shipped_depth -0.01907, 0.0210 apart against photo_depth_tol 0.02 (over by
  0.0010). Centroids -1.171 / -1.397 m; 358 stations; 6,250 atlas samples against the bake's 5,459.
- No threshold touched. The Mac traced it to the gate's mask, not the atlas (adf3828, runbook 0084-4 below).
- Records: `source/road_wear/pc_014/{ref,reh}/`.

#### Pikes Peak 0.2.3

- **Green on road wear, HELD at the forced install** (built at beb2a64c, records on `claude/pikes-peak-road-wear`).
- Reference and rehearsal from empty workshops (`pp_none_ref` / `pp_none_reh`) are identical but for 2 grass vertices.
  The audit reads grass 391,578 / 391,580: the tangent noise merging pairs, as overnight. The kn5s are kn5_equiv
  EQUIVALENT; AI lines 12 / 12 equal.
- road_wear_check, every row PASS:
  - density: 28,656 triangles; jacobian_judged 27,853, **edge_judged 803**, edge_off 0, **unjudged 0, unjudged_list []**
    (the overnight slivers now edge-judged);
  - detail_phase (256.0);
  - tone (r 0.8684);
  - **no_rubber** (oval): declared_depth -0.00791, shipped_depth -0.0121 (-0.00794 on adf3828's gate).
  - `deepest rubber 0.0 %`; no kerb rows.
- **The only red: drive_test infield FAIL**, the S-curve hairpin (s 650-695 m).
  - stage_force: every red row is inside the declared hairpin window.
  - why_not was only "build version 0.2.3 is not in the declared versions ['0.2.0', '0.2.1', '0.2.2']".
  - Installing it needs --force-install.
- **Kevin's word.** The Mac relayed his "Carry it over" (asked "May Pikes Peak 0.2.3 use the hairpin exemption you gave
  0.2.0?").
  - Recorded as data: `force_exemptions.stage.versions` + "0.2.3", with his words in `_versions_doc`.
  - NOT acted on: the PC forces an install only on Kevin's yes typed on the PC. On that yes, the install build is judged
    with adf3828's gate first (runbook 0084-4 step 4).
- **Against the installed 0.2.1** (compare_ab on all four kn5s):
  - the three layout kn5s are identical;
  - in the road kn5, 23 of 25 meshes' positions are bit-identical, UVs and material changed on the five road-wear
    surfaces only, kn5 51,513,251 -> 55,096,716 B;
  - **PADAPRON_0 / _1 differ**: 8 triangles fewer each.
  - That is main's pad-fold fix in `tools/seat_pads_blend.py` (84fefe1a, Nevada, 2026-11-09), which 0.2.1's branch
    d7d40c2 lacked.
  - Proven by an A/B: the same head with only that file from d7d40c2, from an empty workshop, gives seat-pads 58,946 /
    57,488 (0.2.1's) and **25 / 25 meshes' positions bit-identical to 0.2.1** (`pc_023/pad_ab/README.md`).
- Installed: still **0.2.1**. Records: `source/road_wear/pc_023/{ref,reh,pad_ab}/`.

#### The installed tracks, re-checked with f71757b's gate (no rebuild)

`tools/road_wear_check.py <workshop> --kn5 <installed road kn5>`; each workshop's build kn5 is md5-equal to the
installed one.

- **Milford 0.1.11, High Plains 0.1.7, Nevada 0.1.6: every row PASS.**
- Nevada: every shared key equals its record.
- Milford and High Plains: every shared key equals its record except density's maxima, which drop:
  - Milford worst_scale_err 0.000858 -> 0.000636 and worst_shear 0.000894 -> 0.00063;
  - High Plains worst_shear 0.000676 -> 0.000632.
  - The sliver triangles that set those maxima are now edge_judged: Milford 8,805 (worst_edge_err 0.000863), High
    Plains 2,055, Nevada 123.
  - edge_off 0 and unjudged 0 on all three.
- The new keys only add; off counts are 0 before and after.

### Runbook 0084-4 on the PC: the gate on the bake's own cells (adf3828), 2026-11-11

- **Base.** adf3828 merged into the four track branches with no conflict. It changes `tools/road_wear_check.py` and
  tests only, no bake code, so no built kn5 changes.
- **Tests here.** 33 of the 36 road-wear tests pass under Blender's python. The other 3 can't run on this PC: Blender's
  python has numpy, but its PIL import fails (it can only reach the 3.14 PIL). Plain python 3.14 has PIL but no numpy.
  The 3 are `test_photo_mask_is_the_bakes`, `test_gate_measures_the_bakes_samples` and
  `test_gate_kerb_paint_reads_the_repeated_copies`. Installing either package is a download, so not done.
- **Re-run of the new gate, no rebuild.** Every row PASS on all six. The line-vs-mirror depth, old gate -> new
  [samples], against the photo's own [declared_samples]:

| build | photo's own | f71757b gate | adf3828 gate |
|---|---|---|---|
| High Plains 0.1.7 installed (photo_rubber) | 0.14139 [16,255] | 0.14143 [18,066] | 0.14095 [16,232] |
| Pueblo 0.1.5 installed | 0.02166 [19,019] | 0.02615 [21,018] | 0.02156 [19,020] |
| Aspen 0.1.6 installed | -0.00792 [7,122] | -0.01293 [7,700] | -0.00811 [7,122] |
| Pikes Peak 0.2.3 ref and reh | -0.00791 [7,333] | -0.01210 [7,735] | -0.00794 [7,333] |
| Grand Junction 0.1.4 (the red build) | 0.00193 [5,459] | -0.01907 [6,250] | 0.00218 [5,460] |

  - Samples now match the bake's: equal on Aspen and Pikes Peak, +1 on Pueblo and Grand Junction.
  - High Plains reads 23 fewer of 16,255 (0.14 %). It is the one photo_rubber track, and its bake found shadow or paint
    on 31,983 cells.
  - Records: each track's `source/road_wear/pc_0xx/gate_0084_4*.json`.

#### Grand Junction 0.1.4: INSTALLED (2026-11-11 00:39; built at f421b750, records 1f42c6f5)

- Reference and rehearsal from empty workshops (`gj_mask_ref` / `gj_mask_reh`) and the install build are identical
  (gate rows 95 / 95, kn5 tangents only, AI lines equal).
- Every gate green, no force.
  - **no_rubber PASS**: declared_depth 0.00193, shipped_depth **0.00218** (5,460 samples, the bake's 5,459).
  - density: 7,624 triangles, all jacobian_judged, unjudged 0.
  - tone r 0.9349.
- Against 0.1.2: **4 / 4 meshes' positions bit-identical**; UVs and material on 1ROAD_road and 1KERB_sidewalk only; kn5
  **9,586,200 -> 11,207,631 B**.
- Atlas looked at: the photo's asphalt. On the main straight the photo's painted start grid (the staggered boxes and
  the line) shows faintly in the tone (`pc_014_mask/macro_cell_start_grid.png`). It is the track's own paint, not
  something transient like Del Mar's parked cars, so installed, and flagged here for Kevin's look.
- 0.1.2 parked in D:/k10-track-archive/2026-11-11_003921/; the same 13 files. Menu picture re-rendered (s1 of 6, same
  camera). ac-tidy 01d160a1.

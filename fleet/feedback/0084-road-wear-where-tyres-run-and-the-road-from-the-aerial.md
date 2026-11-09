---
id: 0084
title: "road textures need wear where tyres run" — one cracked-asphalt picture on a 4 m world grid; the wear repeats and ignores the lanes. Wear on the real wheel paths (streets) and the racing line (tracks, kerbs too), and the whole road sampled from the aerial
status: open — investigated 2026-11-07; pilot built 2026-11-09 (Milford 0.1.7, Mac, every gate green, not installed, not driven); Kevin's drive closes it
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

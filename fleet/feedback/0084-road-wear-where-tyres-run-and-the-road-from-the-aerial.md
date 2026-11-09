---
id: 0084
title: "road textures need wear where tyres run" — one cracked-asphalt picture on a 4 m world grid; the wear repeats and ignores the lanes. Wear on the real wheel paths (streets) and the racing line (tracks, kerbs too), and the whole road sampled from the aerial
status: open — investigated 2026-11-07 (findings below); the build waits for Kevin's next drive test
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

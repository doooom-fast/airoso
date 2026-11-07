---
id: 0084
title: "road textures need wear where tyres run" — one cracked-asphalt picture tiled every 8 m; the wear repeats and ignores the lanes. Wear on the real wheel paths (streets) and the racing line (tracks, kerbs too), and the whole road sampled from the aerial
status: open — investigation now (Kevin 2026-11-07); the build waits for Kevin's next drive test
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
- The road ribbon's UVs are U = lateral offset / `tile_m`, V = arc length / `tile_m`
  (`tracks/san-diego-lake-murray/scripts-v021/geometry/ribbon.py:56-58`). The road deck uses `tile_m=8.0`
  (`scripts-v021/geometry/build_network_mesh.py:760`).
  - So the picture repeats every 8 m along the road and every 8 m across it.
  - Any wear in the picture sits at fixed offsets from the centreline, not in the lanes, and comes back every 8 m.
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

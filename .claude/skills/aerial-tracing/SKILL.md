---
name: aerial-tracing
description: Read a real circuit off a georeferenced orthophoto with the engine's aerial stage (scripts/aerial/engine, ledger 0088) — the route from published track maps (similarity fit + handedness check), a hand sketch only as a shape aid, the driven dark band on open pavement; pavement edges measured at the sub-pixel boundary with kerbs and edge lines first; registration to lidar; measured pieces assembled into layouts with lap lengths against the published ones; clean overlay stills. Use for any circuit, kart track or private course with no usable OSM line, and whenever a trace is called inaccurate.
---

# Aerial tracing: the engine reads the aerial, nobody draws on it

Kevin, 2026-11-07, while Pikes Peak's infield was traced badly three times:

> "Those tracings aren't very accurate." / "Follow curbs and road wear, it's easy for human eye" /
> "how are you missing the dark areas that cars drive on? It's right there" / "We may need to update our track
> detection skill" / "I feel like this should be handled by the engine by now" / "Why aren't you using actual track
> maps?" / "Stop guessing"

Standing rule: **"I just want real".** Ledger 0088 has the story; 0085 (Pikes Peak), 0081 (kerbs), 0087 (edges) bought
the methods.

## The rules (each one bought by a bad trace)

1. **The route comes from published track maps.** A map picks WHICH pavement, in what order and direction (L1: a
   selection aid, never coordinates). Register it, check its handedness, read its line onto measured pavement.
   Two maps that agree are a check; say when they don't.
2. **A hand sketch is shape only.** Kevin: "Do them as published, i just drew shape". Its direction is never read;
   a sketched layout runs the way the published course runs on the stretches they share.
3. **Edges come from kerbs, edge lines and the pavement boundary**, found on cross-sections at the sub-pixel step,
   kerb / line inner face first, fitted with a curvature limit. Every residual and every inferred (bridged) stretch is
   logged with its reason: opening, weak, shadow, outlier.
4. **On open pavement (a lot, an apron) the line is the dark driven band**, measured with each side normalised to its
   own surface. Where the band is not seen, the bridge is straight and flagged.
5. **Register the aerial to lidar-measured features** where they exist (a wall face, a kerb). Report the offset;
   apply it when it is a pixel or more.
6. **Never place a point by eye.** No seeds, no clicked trace_px, no two-pin screenshot georeference. What a config
   may hold is DATA: files, ink colours, where a label or the S/F is printed, the pit lane a map draws in the course
   colour, the published direction and length.
7. **Show clean overlays**: one line on the band, the aerial lightly tinted, nothing else lit. Zoom sheets for the
   corners. Then let Kevin judge.

## Run

```bash
python -m scripts.aerial.engine tracks/<slug>/source/aerial-engine/engine.json --out <dir>     # or <project-dir>
python tools/aerial_engine_validate.py <pikes-peak | exotics | high-plains> ...                 # against measured truth
```

The stage is opt-in: no existing build path calls it, Lake Murray never sees it. Its output drops into the chain
that exists: `<id>.centerline.geojson` is `data/centerline.geojson`'s shape (elevation -> projection -> LM intake run
as for any aerial track), and `<id>.source.json` is a `source` block for track.config.json that `ship_track.sh`'s
`draft_aerial` step (build_aerial) turns into the same line.

## The config (data only): `tracks/<slug>/source/aerial-engine/engine.json`

| key | what |
|---|---|
| `image`, `georef` | the orthophoto; its CRS from its own metadata: GeoTIFF tags (any EPSG via pyproj; 4326 / UTM built in), a crop sidecar's corners (tools/naip_crop.py), a projected bbox sidecar, a tile georef, two corner pins of a crop |
| `origin_from` | the track's `data/centerline.local.json` (its ENU frame), so lidar surveys and lines line up |
| `colours` | channel overrides (`scripts/aerial/engine/channels.py` DEFAULTS); `edge_band` for a painted boundary of a known colour |
| `edges` | `edge_kind` surface (pavement ends) or lines (a circuit painted on a lot), `reach_m`, `noise_m`, `rmin_m`, `centre_smooth_m` |
| `lidar` | `walls` (tools/lidar_wall.py surveys) as measured edges; `register: wall_top` |
| `start_finish_px` / `_lonlat` | where a lap starts |
| `maps` | per map: file, `ink` rules for the course and the facility's other pavement, `sf_px`, `labels` (+ `label_ink`), `exclude_px` (a pit lane drawn in the course colour), `register_to` lidar or pavement, `direction` as published |
| `sketches` | Kevin's sketch-page strokes (georeferenced by their own corners) |
| `layouts` | id, route (`maps` or `sketch`), `direction` or `direction_from`, `published_length_m` |

If the course band is not one loop the stage stops and names the junction: mark the ink that is not the course
(`exclude_px`), never choose for it.

## What it writes (`--out`)

`report.json` (registration, every map's fit with all near-equal solutions tried and why one won, local refits,
the measurement per side, band runs, joins, corners, kerb candidates), `pieces.json` (each measured piece: edges,
centre and width per metre, residuals, inferred runs, evidence), and per layout `<id>.layout.json`,
`<id>.centerline.geojson`, `<id>.source.json`, `<id>_overall.jpg`, `<id>_zooms.jpg`.

## Validated (ledger 0088)

- Pikes Peak, against ledger 0085 / f11baae3: registration and both map fits identical (0.42 m; rms 0.62 / 6.90 m);
  road course lap 2,211.8 m vs 2,217.8 +-54, centre p50 0.34 / p95 3.3 m; infield-only 750.1 vs 760.3 +-36, centre
  p50 0.33 / p95 2.2 m; piece widths within 0.2 m (median).
- Exotics, against the 2026-10-28 trace: lap 1,822.4 vs 1,821.8 m, centre p50 0.60 / p95 3.2 m; two different
  stand-in sketches give the same lap to 0.21 / 0.43 m.
- High Plains: the block kerb reader reproduces tools/kerb_offsets.py to 0.000 m and 0081 round 3's residuals
  (in 0.15 / 0.35, out 0.17 / 0.70 m median / p95).

## What stays per track

The data in engine.json (above). Lidar surveys (tools/lidar_wall.py on the G10). Downloads: imagery, maps and lidar
need Kevin's yes; the stage only reads what is on disk. Building: the measured line still goes through elevation,
the LM assembler, the gates and Kevin's drive (Job 3 of fleet/REALISM.md).

## Retired

`scripts/aerial/build_aerial.py`'s auto-trace (largest asphalt blob -> skeleton) and its clicked `trace_px` are kept
only so existing configs still build; `build_aerial` now consumes the stage's `<id>.source.json`. Do not trace by
hand, do not pin a screenshot by two corners, do not seed a snap.

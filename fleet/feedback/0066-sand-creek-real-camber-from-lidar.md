---
id: 0066
title: Sand Creek's corners are flatter than the real road; its camber is now measured off the source lidar
status: fixed-awaiting-drive
scope: tracks/sand-creek (the tool is general: any street lap with 3DEP source lidar)
layer: project + engine (tools/lidar_crossfall.py; L10 amended)
train: -
---

## Symptom (Kevin, 2026-11-03, after driving the real road)

> "sand creek seems to smooth out too many of its actual rough elevation changes, particularly at the 56th -> sand creek
> corner. i drove it for real today and it dips and turns dramatically for a passenger road, it's not quite a corkscrew
> or anything but it takes effort to keep the car on the correct side of the yellow line. is this something about that
> track's data, or our smoothing algo's in general?"

## What was there (0.30.1)

- **Heights: not the smoothing.** Away from the bridges the built road is within 0.09 m of the 3DEP 1 m DEM at the 95th
  percentile; through the corner (2,560 to 2,615 m) within 0.2 m.
- **The bridge just before the turn** (E 56th over Sand Creek, 2,429 to 2,528 m) is held level between its abutments,
  because bare earth can't see a deck; the lidar's bridge-deck points (class 17) read it crowned. Not changed here.
- **Camber: the missing piece.** Sand Creek's draft has no crossfall step and no `road_profile.cambers`, so every
  section was flat. The lidar (tools/lidar_crossfall.py) shows the road rolling from +1 % to +4 % over 24 m into the
  turn (2,580 to 2,604 m, banked into it) and holding +2.5 to +4.5 % to 2,680 m, then easing to flat by 2,720 m.
- **Correction, same day.** The first hand comparison (the renders and camber chart sent to Kevin) converted lidar
  coordinates with a rounded metres-per-degree (110,540 m per degree of latitude against the engine's 111,032) and so
  sampled about 5 m north of the line at the corner: it read the turn as -1 % to +5.5 % in 20 m and -5 % by 2,790 m,
  its "our line runs 4–7 m off OSM" was the same error, and its bridge-deck heights (up to 0.45 m over ours) need
  re-measuring before the deck is touched. The tool uses `scripts.geometry.projection._meters_per_degree`.
- `scripts.elevation.crossfall`'s footprint mode would not have produced it: it keeps a tilt only at >= 2 %, never into
  a curve tighter than R 100 m (L10 as worded: "public streets are not superelevated"), and ramps every change at
  0.12 %/m (3.6 % per 30 m), all [invented].

Renders: `1_corner_topdown.png`, `4_profile.png`, `5_camber.png` (sent to Kevin 2026-11-03; scratch, not committed).

## Fix

- **`tools/lidar_crossfall.py`** (new): per 3 m station of `centerline.local.json`, the source lidar's points within
  4.5 m across and 1.5 m along (deck points on the declared bridges, ground points everywhere else); a trimmed
  least-squares plane tilt; a fit that isn't a road plane dropped and filled from its neighbours (flat past 30 m); a
  9 m median + mean for the fit's noise; capped at the legacy 6 %; every change limited to 0.2 %/m, just over the
  turn's measured ~0.16 %/m roll-in (the DEM tool's 0.12 %/m is what would have flattened it). Writes
  `data/crossfall.json` in build_mesh's legacy shape (`station_m`, `bank_rad`, + = left edge up), `status: measured`,
  and caches the per-station fits in `data/crossfall.lidar.json` (keyed to the line) so a rerun recomposes without
  fetching.
- **Sand Creek**: `road_profile.crossfall.method = "lidar"`; `ship.json` syncs `data/crossfall.json` into the
  workshop; build_mesh already rolls every road section by the file when a track has no hand-authored cambers.
  `scripts.elevation.crossfall` now leaves a lidar file alone. Version 0.31.0.
- **L10 amended**: a street's lidar-measured tilt is research and is built as measured, into a curve included.
- No gate threshold changed (Sand Creek's chain doesn't run `verify_crossfall`), so nothing in GATES-CHANGELOG.

## Measured, whole lap (`data/crossfall.json`, 2026-11-03)

- 3,233 stations every 3 m, 208 EPT nodes of CO_DRCOG_2_2020; 199 stations were not a road fit (a deck over E 45th Ave,
  most likely I-70's; curb and embankment runs) and are filled from their neighbours.
- |tilt| median 0.7 %, p95 3.1 %, max 5.8 %; none at the 6 % cap; worst roll change 5.85 % per 30 m (the 0.2 %/m limit).
- E 45th Ave by the third creek crossing (6,300 to 6,680 m) reads clean fits flipping -7 % to +9 % inside 40 m: most
  likely the line on the approach embankment, not the pavement. The roll limit turns it into ramps; worth a look in the
  seat, and a line check there if it reads wrong.
- The tool's own numbers are [invented] and listed in its header (HALF_M 4.5 m, MAX_SD_M 0.08 m, MAX_READ_PCT 8 %,
  MAX_GAP_M 30 m, SMOOTH_M 9 m, ROLL_RATE 0.2 %/m).

## Proof owed

- Sand Creek 0.31.0 through the chain, every gate on the built kn5, then installed: a build on the PC.
- Kevin's drive of the 56th Ave turn. The bridge deck's crown is the next piece if the turn-in still reads flat.

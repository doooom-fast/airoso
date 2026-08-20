# Mount Panorama — the second calibration track

Like `projects/nordschleife/`, this is **not a product**. It is the control that proves the
Nordschleife result was a property of the builder rather than of one track.

Nordschleife taught the elevation-source lesson (feedback 0030). Bathurst was then built with
**no tuning at all** — same engine, same defaults, a config written once — to see whether the
lesson transferred. It did, and by a wider margin.

## Why this track

- **Non-US**, so it exercises the SRTM path rather than 3DEP.
- **Violently vertical**: 174 m of elevation change in 6.2 km, with sustained ~16% gradients up
  Mountain Straight. If the grade limiter or the DEM were wrong, this track would show it.
- **Public roads**, so OSM has the real geometry.
- A high-quality reference exists in `blckbox_bathurst`.

## Source

OSM relation **6942508** (`Mount Panorama Circuit`, `type=circuit`), 19 ways. Two are Pit Lane
(`37594848`, `385686852`) and are excluded; the remaining 17 chain into a closed loop with **no
orphans and a 0 m closing gap**, which is a cleaner relation than the Nordschleife's.

The ways carry the real corner names — Hell Corner, Mountain Straight, Griffins Bend, The Cutting,
Reid Park, McPhillamy Park, Brocks Skyline, Sulman Park, The Esses, Forrest's Elbow, Conrod
Straight, The Chase, Murrays Corner — so the chained result is verifiable by inspection.

Chained length **6,197 m** against the real 6,213 m: **−0.26%**, before any processing.

## Reproduce

```bash
python3 -m scripts.elevation.heightfield projects/bathurst
python3 -m scripts.geometry.projection  projects/bathurst
python3 -m scripts.geometry.build_mesh  projects/bathurst
```

## Result — first build, no tuning

Registered rigidly onto `blckbox_bathurst`'s racing line (mirror + 178.7° rotation + translation,
lap phase 94.2%), 2,574 matched samples:

| | Mount Panorama | Nordschleife (for comparison) |
|---|---|---|
| lap length | 6,209 m vs 6,179 m (+0.5%) | +0.2% |
| elevation range | 178.0 m vs real 174 m | 293.3 m vs scan 293 m |
| lateral P50 | 2.5 m | 1.8 m |
| lateral, within 5 m | 98% | 99% |
| vertical RMS | **2.38 m** | 3.8 m |
| vertical P90 | 4.0 m | 6.0 m |
| vertical max | **6.8 m** | 13.7 m |
| sections worse than 8 m | **none** | 8 |

Better than the track it was calibrated on, which is the point: the fix was in the builder, not in
Nordschleife-specific tuning.

## What is still wrong: the drive test fails on roughness

`drive_test` reports **94.4 bumps/km against a 75/km tarmac limit** (and 140 severe steps). Geometry
is fine — 0 obstructed stations, 0 daylight gaps, 0 floating furniture, 0 undrivable corners, and
the deck sits *on* the ground (replication median 0.00 m, p95 0.21 m).

**This is not the elevation profile.** That was tested directly and the negative result is recorded
in `fleet/feedback/0031-roughness-is-not-in-the-profile.md`: smoothing the centerline at the DEM's
own scale improves the score against the reference *and* makes the build worse, because it lifts
the deck off the terrain. Bumps barely moved. The roughness lives in the mesh, and finding it is
the next piece of work — not more filtering.

## The caveat on the reference

`blckbox_bathurst` is a third-party mod, not a manufacturer laser scan like `ks_nordschleife`. It
is widely regarded as scan-derived and its numbers here are self-consistent (its own lap measures
6,179 m against the real 6,213 m), but it is a weaker answer key than the Nordschleife's. Treat the
Bathurst figures as corroboration of the Nordschleife result rather than as independent ground
truth.

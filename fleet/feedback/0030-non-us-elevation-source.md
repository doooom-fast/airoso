---
id: 0030
title: The DEM was the error, not the filter — SRTM 30 m for every non-US track
status: fixed (engine) — measured end-to-end on the Nordschleife calibration build
scope: every track outside USGS 3DEP coverage; today that is the Nordschleife calibration project
layer: engine
train: R5
---

## Symptom

The pipeline had exactly one elevation source, `usgs_3dep`, which is US-only. The first non-US
track therefore had no way to run Phase 2 at all. Standing it up on a public global DEM produced a
road whose *shape in plan was excellent and whose height was badly wrong*: registered against the
Kunos laser scan, vertical RMS **9.7 m**, P90 **15.5 m**, worst section **37.6 m**, in long
coherent stretches rather than as noise.

## What was actually measured

Built the Nordschleife from OSM relation 38566 + a public DEM, registered the result rigidly onto
`ks_nordschleife`'s AI line (mirror + 178.5° rotation + translation; lap phase offset 10.3%), and
compared road heights at 2,665 matched stations.

**The first instinct — that our smoothing was wrong — was tested and is false.** Sweeping the
profile filters over the *same* bad data moved RMS from 9.68 m to 9.07 m at best. Everything was
stuck in a 1 m band, which is the signature of an input-data floor rather than a processing bug:

| profile processing | RMS |
|---|---|
| raw, no processing | 10.4 m |
| `snap_to_ground` cap 9 med 33 (shipped default) | 9.68 m |
| `smooth_profile` med 201 mean 201 (best of 23 variants) | 9.07 m |

So the sources themselves were scored against the answer key instead — same centerline, same
stations, same registration, five DEMs:

| dataset | RMS | P90 | max |
|---|---|---|---|
| **srtm30m** | **3.80 m** | 6.2 m | 12.3 m |
| mapzen | 3.80 m | 6.2 m | 12.3 m |
| srtm90m | 5.85 m | 9.1 m | 22.8 m |
| eudem25m | 6.45 m | 10.2 m | 22.7 m |
| aster30m | 8.31 m | 14.9 m | 24.3 m |
| Copernicus 90 m (Open-Meteo) | 9.68 m | 15.6 m | 37.6 m |

## Diagnosis

Two independent faults in Copernicus-90-via-Open-Meteo, both fatal to a road profile:

1. **It is a surface model.** GLO-90 returns canopy height over forest, and the Eifel is forest for
   most of the lap. That is the mechanism behind the long coherent ±30 m sections — they are not
   noise, they are treetops.
2. **Open-Meteo rounds to whole metres.** A 1 m quantum across a 3 m centerline step reads as a
   33% grade. Raw grade came back P50 **0.00%**, P95 **46%**, max **98%** — a staircase, not a road.

The staircase then wrecked the grade limiter downstream. `snap_to_ground`'s clamp only ever cuts
downward, so on a saturated input it runs at full cap rate continuously: capped grade was *exactly*
9.00% at the median, and the profile was dragged down a mean of **5.6 m**, worst **44 m**. That
looked like a limiter bug and was not one — it was a limiter behaving correctly on garbage.

SRTM's C-band radar partially penetrates canopy and comes back as floats, so both faults go away
at once.

## Fix

`scripts/elevation/srtm.py` — new source. opentopodata.org `srtm30m`, keyless, with Open-Meteo kept
only as a fallback so a build still completes if opentopodata is down. Requests are decimated to
the DEM's own 30 m resolution and interpolated back up: sampling a 30 m source every 3 m spends 10x
the API budget to manufacture the same staircase we just removed.

`scripts/elevation/heightfield.py` — `_pick_source()` chooses 3DEP for US/unset `location.country`
and SRTM everywhere else; `_sample()` passes input spacing only to sources that decimate. The
corridor pass stays 3DEP-only, since its whole purpose is near-native lidar detail that a 30 m
source cannot supply.

**US tracks are byte-identical.** Both new parameters default to `usgs_3dep`, the corridor call is
guarded, and 3DEP is still called with the exact same argument list. 171 tests pass.

## Result

End-to-end rebuild of the Nordschleife, Phase 2 through Phase 4:

| | before | after |
|---|---|---|
| vertical RMS | 9.7 m | **3.8 m** |
| vertical P50 | 5.3 m | **2.3 m** |
| vertical P90 | 15.5 m | **6.0 m** |
| vertical max | 37.6 m | **13.7 m** |
| total climb per lap | 680.8 m | **573.8 m** (real: ~570 m) |
| lateral P50 / within 5 m | 1.7 m / 99% | 1.8 m / 99% (unchanged) |

Re-running the filter sweep on the *good* data closes the loop: the shipped default
(`snap_to_ground` cap 9 med 33) is now the best of 16 variants at 3.79 m, with every alternative
inside 0.2 m. **The engine's profile logic was correct the whole time and needed no change.**

## Verification

`projects/nordschleife/` is the standing gate. Rebuild Phases 2–4 and register against
`ks_nordschleife`; vertical RMS must stay at or below **4.0 m** and lateral containment within 5 m
at or above **99%**. A regression in either says the elevation seam moved.

## What this does not fix

The residual 8–14 m sections are DEM *resolution*, not source choice: 30 m posts cannot see a
cutting, an embankment, or a bridge deck. Closing that needs a real DTM — Rheinland-Pfalz publishes
1 m LiDAR for the Nürburg area — and is the next thing to try, not more filtering. The evidence
that filtering is exhausted is above.

## The transferable lesson

Twenty-three filter variants moved the number by 6%. One source change moved it by 61%. The engine
had a measurement gate on its own output and none on its input, so a bad input reached the mesh
looking like a modelling problem. **Score the data before tuning the code** — and prefer a bare-earth
DTM to a surface model for anything a car has to drive on.

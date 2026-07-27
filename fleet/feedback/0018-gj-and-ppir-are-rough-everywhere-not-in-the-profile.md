---
id: 0018
title: Grand Junction and Pikes Peak — rough everywhere, and it is NOT the elevation profile
status: open — two hypotheses killed, mechanism not found
scope: k10-colorado/grand-junction, k10-colorado/pikes-peak
layer: engine
train: 02
---

## State on engine v0.52.0

| | lap | severe | bumps/km (limit 75) | kinks/km |
|---|---|---|---|---|
| grand-junction | 1,032 m | 45 | 74.63 | 129.9 |
| pikes-peak | 1,649 m | 68 | 94.01 | 235.9 |

Both PASS ground-on-top (0) and fail on roughness alone. The kink rate is the tell: 130 and 236
per km against a 3%-slope-change-per-metre threshold is a **jagged deck everywhere**, not a few bad
spots — but severe steps also CLUSTER (GJ: 13 at station 460, 12 at 800, 9 at 860; PPIR: 12 at
1400, 11 at 640, 10 at 240 and 1020), so there are discrete offenders on top of a rough baseline.

## What v0.49.0/v0.50.0 gave for free

PPIR's worst step was **1.401 m at station 1400** — its infield connector, sitting above the
mainline exactly like Lake Murray's del_cerro_blvd. Junction reconciliation fired on its first run
here (`infield: reconciled to the mainline (max 2.23 m)`) and took severe 70 → 65. GJ has no
connectors so neither fix reached it (43 → 43).

## Hypothesis 1 — DEM noise in the elevation profile. KILLED.

These are engineered circuits on flat ground, and 3DEP sampled every 3 m over a 1 km lap is mostly
surface noise, so a wider despike should collapse the roughness. Declared
`road_profile.despike_window_m: 90` (default 33) and `max_grade_pct: 4`:

- GJ: bumps 83.35 → 74.63, but severe **43 → 45**
- PPIR: bumps 96.44 → 94.01, severe **65 → 68**

Bumps improved slightly, severe steps got *worse*. The roughness does not live in the centerline
profile. **The declared settings are left in place** (a graded circuit should have a smooth profile
regardless, and the bump numbers did improve) but they are not the fix.

## Hypothesis 2 — ribbon pleating. KILLED.

`_cap_offset`/`_signed_curvature` exist because a lateral offset exceeding the local curve radius
sweeps consecutive cross-sections backwards over each other and stacks decks (the Lariat's hogback,
0.3–0.6 m random steps). Measured at the worst cluster on each track:

| | width | half | local radius | half/R | stacked road surfaces |
|---|---|---|---|---|---|
| GJ @ 800 | 9.8 m | 4.9 | 1502 m | 0.00 | **1** |
| PPIR @ 1400 | 15.0 m | 7.5 | 158 m | 0.05 | **1** |

One road surface at each, and half/R nowhere near the 0.5 that pleats. Not pleating.

## What to try next

The steps are in the built mesh, are not stacked decks, and are not inherited from the centerline
profile — so look at what happens BETWEEN the profile and the ribbon: banking/crossfall
(`bank_at`, `crossfall.json`), the fold-plateau pass, and per-vertex width changes. A width step of
w metres at a crossfall of c gives a vertical step of w*c at the edge, and both tracks are wide
(9.8 / 15.0 m) with measured crossfall. Check whether `widths_m` steps discontinuously at the
cluster stations — that is cheap to measure and would explain clustering plus a rough baseline.

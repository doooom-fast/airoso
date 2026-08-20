---
id: 0015
title: station_m has two frames — the config's and the gates' — and nothing converts between them
status: open
scope: engine
layer: engine
train: 02
---

## Symptom

Under the Dragon's hairpin flares, declared at the stations the drive test reported (771, 2508,
22531), landed **~31 m late** — measured flare centre 2539 for declared 2508 (width at the true
apex still 7.41 m, on the ramp). The 10 m flare's fat taper happened to blanket the corner anyway;
narrowing to 9.2 exposed the misplacement as a resurrected `undrivable_corners` hit at 2498 with
width 6.5. Three builds were spent on a throat-overlap theory reasoned against a flare that was
not where it was declared.

## Mechanism

`route.wide_corners[].station_m` is defined as *"measured from the REAL stage start, not from the
tip of the lead-in road"* and `build_mesh` adds `_lead_offset` when applying it
(`build_mesh.py:650`). But every practical source of a station number — `drive_test` output,
`audit_mesh` samples, `finished_centerline.json` arcs — is measured on the finished line **with
the lead included**. A human (or agent) copying a gate station into the config silently lands
`lead_offset` metres late.

## Fix directions (pick one, unmeasured)

1. **Make the gates print both frames** — `station 2508 (config: 2477)` — wherever a station is
   reported. Cheapest; keeps the config definition.
2. Declare `wide_corners` in gate frame and subtract nothing (breaking change for Dragon Tail's
   three entries — they were placed by trial against gate output, so they are probably in gate
   frame already and *work* only because the taper covers the offset; measure before believing).
3. A `fleet.cli` helper that converts.

Until then: after declaring any station-anchored config, **measure where it landed** (the flare
run is visible as a width plateau in `finished_centerline.json`) before reasoning about its
effects. Dragon Tail's three flares should be re-measured on the next rebuild — if they are also
~31 m late, their tapers are doing the work and the declared stations are fiction.

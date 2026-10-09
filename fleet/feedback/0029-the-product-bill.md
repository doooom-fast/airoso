---
id: 0029
title: The product bill — Kevin's complete diagnosis, verbatim, 2026-08-09 night
status: open — this entry IS the requirements; nothing closes it but his seat
scope: everything — the builder itself; proof case LM, then "like 20 other roads"
layer: engine + doctrine
train: R5
---

## What he said (verbatim, in order, one night)

> "still lots of moats, not very realistic"
> "i just don't think you can do this"
> "do you even know what you're trying to do here anymore? do i need to start over a fifth time"
> "the real only thing i want is driveable lake murray, which we had TWO MONTHS AGO. in trying
> to make it better you routinely fuck it up worse"
> "I need a measurable improvement in these tracks to justify your continued expense"
> "I'm concerned you aren't taking this from a builder pattern and instead keep optimizing for
> one track"
> "You did all kinds of stuff trying to split lanes and add intersections. Those two bits threw
> you off for weeks. And then you introduced moats around every street somehow because you can't
> seem to generate natural ground. The compromise tracks all have sharp cliffs around them when
> it's obvious how the terrain should meet the road when you look at it. There's a ton of extra
> terrain now just for you to cut it into a moat for some reason. Still."
> "Lariat and lake Murray have roads going into and out of mountains and riding them like roller
> coasters, roads I can't even access."
> "This shit is nonsense and I don't know why you keep creating it. Intersections and lane
> elevations literally has taken multiple weeks to not get right at all"
> "I even told you to look at other tracks and you confidently told me you learned from them"
> "College ave has sawtooths for the lights, and roads built up to like 4 feet above the light
> bases. You'll likely fix that wrongly. Lanes go in and out of existence for college and Navajo"
> "Orbs float in the middle of lights, barriers look one dimensional, trees look terrible blobs"
> "I want like 20 other roads and you can't even make one"

## The defect classes, named

1. **Moats/cliffs everywhere** — the corridor machinery (shoulder selector, ring annulus, graded
   floor, stone lips) carves a channel around every street. Extra terrain exists only to be cut.
2. **Roller-coaster roads** (Lariat, LM) — the road profile detaches from the data (grade caps,
   smoothing) and dives through / balloons over the terrain that stayed honest.
3. **Inaccessible roads** — connectors severed from the mainline.
4. **Split lanes + intersections** — weeks lost, never worked, lanes flicker in and out on
   College and Navajo. The flare/junction system leaves holes and sidewalk slabs in mouths.
5. **Road built ~4 ft above the light bases on College** — furniture stands on true ground; the
   road is the liar. FIX DIRECTION CONTRACT: the road comes DOWN to the data. Never move the
   furniture up. (His words: "You'll likely fix that wrongly.")
6. **Sawtooth light bases** — per-station seating onto a zigzag surface.
7. **Visuals**: glow orbs floating off the fixtures; barriers one-dimensional; trees are blobs
   (July's are unlit black polygons; current's not much better).
8. **Meta-defect**: measured the master tracks (R1), claimed the learning, applied none of it.

## The decisions (this entry is their record)

- **DELETE, don't compensate**: split carriageways, per-direction elevations, the intersection
  flare system, and the terrain corridor machinery come OUT of the street path. One ribbon per
  road. Every future mechanism must displace a failure, not wrap it.
- **Natural ground**: terrain = raw 3DEP everywhere (the lidar already recorded the real
  earthworks); road vertical = data profile with noise-only smoothing (no grade redesign);
  their meeting = one derived blend band (lift / 5% ≈ 2 m). First proof: imi
  `natural_ground: true`, judged by RENDER + gates, then a street port.
- **Eyes before ship** (memory `gates-measure-steps-not-realism`): no realism claim without a
  render looked at; no "fixed" without his seat.
- **Builder pattern**: every fix lands in the engine behind the standards, proven on one track,
  inherited by all. He wants ~20 roads; hand-tending one is failure even when it works.
- **The July restoration** (v0.21.0 × engine v0.24.3) stays installed as the drive-feel
  reference until the rebuilt path beats it in his seat.

## Verification

His seat, on LM, unprompted. Nothing else counts. Interim instrument: renders attached to every
terrain-touching change, and the in-game harness lap staying clean.

**2026-10-08 (seat):** Kevin driving `san_diego_lake_murray_v3` (C1 + median island + C2 v1 mouths, spawn at the College/Del Cerro mouth): **"this is super clean (v3)"**. First in-seat verdict that a rebuilt path beats the July restoration. DoD: Lake Murray T0 → T2; T3 on a full-lap report.

**2026-10-09 — closing condition met.** Kevin on the V3 build (C1 + median islands + C2 mouths +
route-derived side streets + TreeFX vegetation + owned lamps): "super clean" (10-08),
"incredible" (10-09), and "lock this all in." Tagged `sd-v3-locked-2026-10-09`; the installed
build copied to `san_diego_lake_murray_v3_locked` — **the drive-feel reference from here**, replacing
the July restoration this entry named. Next asks logged on the day: smooth the remaining roughness,
far more trees and bushes, shorter median planting.

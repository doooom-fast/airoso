---
id: 0016
title: Spawn dummies face the start line's direction, not the road they sit on
status: fixed (v0.47.0)
scope: engine — every track with a curved start area
layer: engine
train: 02
---

## Symptom (Kevin, from driving)

> "Start from pit start ... car often points at edge"

## Mechanism

`kn5_write` computed ONE `start_yaw` — the road heading at `AC_START_0` — and wrote it into every
dummy whose name starts with `AC_START`, `AC_PIT` or `AC_HOTLAP`, regardless of where that dummy
actually sits (`kn5_write.py:306`, and the same again in the per-layout spawn kn5s at `:347`).

On a circuit the boxes bunch together on the start straight, so the inherited heading is right by
accident. Measured across the fleet:

| track | start heading | pit box headings | worst error |
|---|---|---|---|
| second-creek | 89.4° | 89.4° ×4 | 0.0° |
| imi | 171.1° | 169.8° ×4 | 1.2° |
| lookout-lariat | 33.7° | 33.7–33.9° | 0.2° |
| sand-creek | 76.9° | 77.2° ×4 | 0.4° |
| under-the-dragon-gravel | 140.3° | 140.3° ×4 | 1.5° |
| san-diego loop | 110.4° | 109.7–110.3° | 0.7° |
| **dragon-tail-gravel** | **−49.7°** | **−27.7 / −21.1 / −36.3 / −46.2** | **28.6°** |

**Dragon Tail starts on a bend.** Its boxes sit at centerline indices 9–19 while the start is at
index 5, so they inherit a heading from up to 14 points (~40 m) back down a curving road. A 28°
error on a 6.5 m stage points the nose straight off the driving line — which is exactly what
Kevin reports, and it is the one stage in the fleet where the defect is visible.

## Fix

Derive each facing dummy's heading at its OWN position, over a ±3 point baseline — long enough to
ignore resample noise, short enough to follow a real curve. Applied in both the main dummy loop
and the per-layout spawn kn5s (where a `reverse` layout additionally flips 180°).

## A latent bug found while measuring — deliberately NOT fixed

`rot()` (`kn5_write.py:153`) turns a direction by **minus** yaw:

```
x' = L·sin(θ − yaw)    z' = L·cos(θ − yaw)     →  heading becomes θ − yaw
```

but the dummy matrix is written with `phi = start_yaw + yaw`. The sign is wrong and the error is
`2 × yaw`.

It is invisible today because **every track in the fleet declares `true_north_rotation_deg` of
either 0 or 180**, and `2 × yaw` is then 0° or 360° — the same angle either way. The first track
to declare anything else (say 90°, giving a 180° error, or 45°, giving 90° — a car pointed at the
edge again) will hit it.

Left in place on purpose: changing it now moves nothing measurable, so the change could not be
verified, and a silent edit would remove the evidence. Fix it together with the first non-0/180
track, and check the spawn heading in-game on that track.

## Verification

- Rebuild dragon-tail-gravel; its four pit boxes read within a couple of degrees of the local road
  instead of 22–29° off.
- Every other track's spawn heading moves by less than ~1.5° (they were already correct).
- Kevin starts from the pits on Dragon Tail and the car points down the stage.

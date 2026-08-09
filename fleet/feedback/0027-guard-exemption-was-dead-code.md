---
id: 0027
title: The gate's guard exemption was dead code — no wall could ever be in the field it probed
status: diagnosed
scope: engine — every track that ships 1WALL geometry; proof k10-colorado/imi, regression any wall-less build
layer: engine
train: R4 (rides with 0025)
---

## Symptom (found instrumentally, closing 0025, 2026-08-08)

The 0025 campaign's last 3 excursion drops (IMI station 302.5, offsets 6.5 / 7.0 / 13.0) stayed
"unguarded" through every wall the builder placed — including measured stone lips verified
physically present in the built `track.obj`, on the gate's exact ray, at the exact heights the
guard scan probes.

## Evidence

Reproducing the gate's ray at station 302.5 against the built artifact:

```
 6.0 |  7.977  1WALL_PARA_stone     <- the lip, in the artifact, on the ray
 6.5 |  7.008  1GRASS_aj  << DROP
 7.0 |  6.048  SHOULDERUND << DROP
```

Yet the same build's gate reported all three drops gated-unguarded. The mechanism, in
`scripts/geometry/drive_test.py`:

- `DRIVABLE = ("1ROAD", "1KERB", "1RUNOFF", "1LAWN", "1GRASS")` — the loader routes every group
  by this prefix list: drivable → `surface`, everything else → `obstacle`. **1WALL is not
  drivable, so every wall lands in `obstacle`.**
- The guard scan probed `surface.top_at(...)` and accepted only owners starting `1WALL` — an
  owner that container can structurally never hold. `guarded` was always False.

Every guard-related behavior ever observed (imi toes "guard scan widened", four-condition
parapets) was therefore never actually exercised through this exemption — those drops died by
grading, or not at all. The exemption's own comment states the intent: "a drop BEHIND a
barrier/guard wall is GUARDED (the car never reaches it — that's the wall's job)". The
implementation just looked in the wrong field.

A useful side-effect of the same routing, worth keeping: walls being absent from `surface` means
the sweep's *height chain* reads the ground beneath a wall, so a placed lip never mints a phantom
"drop off the wall top". The routing is right; only the guard probe was wrong.

## Fix (engine, same file)

The guard scan now probes `obstacle.top_at` — the field walls actually live in. One word plus a
comment recording why. Owner filter unchanged (`1WALL*` only), so trees/fences/furniture between
the edge and a drop still do not guard it. Landed on the working tree with the 0025 closing move
(measured stone lips); rides the same train, tags as v0.66.1.

## Verification

- **Proof (IMI):** the 3 drops at 302.5 must leave `excursion_drops` (0 gated) while still being
  *reported* in `worst_excursions` with `gated=False` — measured, exempted, not hidden. Gate
  chain PASS end-to-end.
- **Regression (any wall-less track, e.g. a plain SD rebuild):** `obstacle` holds no 1WALL there
  either, so counts must be byte-identical before/after the one-word change.

## The durable rule

An exemption that has never once fired is not a rule, it is a comment. When a gate credits a
mitigation (walls, spans, flares), the crediting path needs its own proof case — one fixture
where the mitigation exists and is seen. 0025's measured lips became exactly that fixture, by
accident; keep one on purpose.

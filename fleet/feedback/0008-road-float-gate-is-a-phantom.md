---
id: 0008
title: The road-float gate is a phantom — it does not measure the built terrain
status: diagnosed
scope: every track that reaches the kn5 stage
layer: engine
train: 01
---

## Symptom

`kn5_ground_check` fails four Colorado tracks with "road floating over ground" on 73.7–88.7% of
samples, blocking every one of them from shipping — while `drive_test` (0 daylight gaps) and
`audit_mesh` (checks B and H both 0) pass the same builds.

## Evidence — the gate is insensitive to the geometry it claims to measure

Three builds of IMI with **materially different terrain** produced byte-identical gate output:

| Build | gate output |
|---|---|
| baseline (v0.21.1) | median +0.091  p95 +0.351  max +0.570  ·  101/137 (73.7%) |
| widened road-sample coverage in `grade_embankment` | **identical** |
| distance-recovery on the shoulder/kerb clamp (in-build gap 1.042 → 0.137 m) | **identical** |

Then the decisive test — **sink the entire grass mesh by 1 metre** before writing `track.obj`:

- `track.obj`: 1GRASS mean y **2.68** vs 1ROAD mean **3.63** → the sink landed.
- The shipped `.kn5`, parsed with the gate's own `_parse_tris`: 1GRASS mean **2.34** vs 1ROAD
  **3.67** → the kn5 is fresh and contains the sunk terrain.
- Gate output: **median +0.091, 101/137, 73.7% — unchanged to three decimals.**

A metre of terrain moved under the road and the "road floating over ground" metric did not budge.
It is not measuring the built terrain.

## Two hypothesised causes — BOTH CHECKED AND WRONG

Recorded so nobody re-tests them:

1. **"`1KERB` is wrongly in the GRASS-ONLY terrain set."** Wrong — it is deliberate. A later pass
   adds `1RUNOFF` to `tri_grs` describing it as "ground cover exactly like `1KERB`". The
   "GRASS ONLY" comment belongs to a different variable (`ground_h`), not to `tri_grs`.
   Measured on the shipped kn5: of 414 deck samples, **1GRASS supplies the surface 348 times** and
   `1KERB` only 66 — grass already dominates the reference.

2. **"Most of the road is never sampled."** Wrong. `_bucket()` prefix-matches, so `1ROAD_main`
   lands in `1ROAD_MAIN`. The check targets the DECK, and 137 samples over IMI's 1.44 km is one
   per ~10 m — that is the intended density, not a truncation.

**So the mechanism is still unknown.** The reproduction below is solid; the explanation is not.

## Consequence

**"Road floating" is not a geometry blocker.** Four tracks — imi, pueblo, second-creek,
high-plains — are held out of shipping by a measurement that does not respond to the geometry.
Whatever the true deck-to-terrain relationship is on those tracks, this gate has not established it.

Do not tune terrain code against this metric until it is fixed; that is chasing a number that does
not move.

## Next step

Start from the reproduction, not from a theory: instrument `kn5_ground_check` itself to dump, per
sample, the road vertex, the surface it selected, that surface's mesh, and the resulting gap — for
the SAME track built twice with a known terrain offset between them. The samples whose gap does not
change by that offset will name the mechanism directly.

Then add a self-test: perturb the terrain by a known offset and assert the reported gap moves by that
   offset. A gate that cannot detect a 1 m shift should fail loudly rather than report a number.

## Note on a related finding

While bisecting, the in-build terrain gap was traced pass by pass (`K10_GAP_TRACE`). The
shoulder/kerb anti-poke clamp opens the gap from **+0.084 m to +1.042 m** in one step: it passes
`reach=6.0`, but `clamp_terrain_below_road` raises that to `grid_spacing*2.2+0.5 = 11.5 m`, and at
that radius the *minimum* it clamps to is the shoulder's ground-meet drape descending to natural
ground — with `recover=0`, so no distance falloff. Giving it `foot_m=2.0, recover=0.35` (the same
treatment the road clamp already gets) brings the in-build gap to **+0.137 m**.

That change is **not committed**: it is verified against the in-build trace but cannot be validated
end to end while the gate is blind. Land it after fixing the gate, and confirm both together.

## Verification

- Sinking the terrain by a known offset moves the reported gap by that offset.
- Sample count is proportional to the road's actual vertex count, not ~1/20th of it.
- The terrain reference contains no `1KERB`, `1ROAD` or structural geometry.

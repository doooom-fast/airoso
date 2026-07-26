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

## Two defects found so far

1. **`1KERB` is in the "GRASS ONLY" terrain set.** Triangles are bucketed with
   `(tri_pav if name.startswith("1ROAD") else tri_grs)`, so `1KERB` lands in `tri_grs` — and the
   gate then measures the deck against its own kerb. The block's own comment forbids exactly this:
   *"GRASS ONLY … measuring the deck against its own shoulder/kerb/underside apron is the road
   resting on itself."* Excluding `1KERB` moves the numbers (0.091 → 0.133, 73.7% → 87.6%), so it
   is real — but it is not the whole story, since the result is still insensitive to the 1 m sink.

2. **Most of the road is never sampled.** `kn5_road = kn5.get("1ROAD_MAIN", []) + kn5.get("1ROAD", [])`
   — exact-key lookups. The kn5 carries **20,244** `1ROAD*` vertices, but the gate ends up with
   **137 samples** (`road[::7]` ⇒ ~960 verts). Groups named `1ROAD_main`, `1ROAD_shoulder_a` etc.
   match neither key, so the check runs on a small unrepresentative slice.

## Consequence

**"Road floating" is not a geometry blocker.** Four tracks — imi, pueblo, second-creek,
high-plains — are held out of shipping by a measurement that does not respond to the geometry.
Whatever the true deck-to-terrain relationship is on those tracks, this gate has not established it.

Do not tune terrain code against this metric until it is fixed; that is chasing a number that does
not move.

## Fix

1. Build the terrain reference from `1GRASS` **only** — matching the comment's stated intent.
2. Collect road vertices by **prefix**, not exact key, so the whole road is sampled.
3. Re-establish the baseline afterwards. The real gap may be fine, or may not — it is currently
   unknown, and that is the honest position.
4. Add a self-test: perturb the terrain by a known offset and assert the reported gap moves by that
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

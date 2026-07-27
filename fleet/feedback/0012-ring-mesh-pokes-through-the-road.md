---
id: 0012
title: 1GRASS_ring pokes through the road — the last blocker on Aspen and Grand Junction
status: diagnosed
scope: k10-colorado/aspen, k10-colorado/grand-junction
layer: engine
train: 01
---

## Symptom

Both tracks fail `drive_test` on `soft_top_in_lane`, and after the v0.27.0 skirt fix it is the
**only** thing failing them. Every hit comes from the same mesh:

| Track | hits | mesh | stations |
|---|---|---|---|
| aspen | 2 | `1GRASS_ring` | 1466 |
| grand-junction | 38 | `1GRASS_ring` | 472, 473, 476, 477, 688 |

Aspen's audit is otherwise clean on every check A–J; its only other issue is the same spot showing
as check B, a **+0.19 m** poke.

## What the ring is

`build_mesh` sweeps an annulus of grass columns beside the pavement (the "welded ring", `#17`). While
building each column it already clamps itself under the pavement — but only where it finds pavement
**directly under that column point** (`_pv17`). Where the road passes *between* column samples,
nothing clamps and the ring rides over the deck.

## Attempts, and what each proved

All reverted; recorded so they are not repeated.

1. **Sink ring vertices below the local road** (sampling `_road_tops` at each vertex and ±0.5 m).
   Fired on **zero** vertices for either track. So the ring's *vertices* are not above the road —
   its *faces* span over it between vertices.
2. **`drop_over_road(ring_mesh, …)`** — the existing helper, 7-point sampling (verts + edge midpoints
   + centroid), the same guard the warning barriers use. Grand Junction dropped 17 tris,
   38 → 32 hits. Aspen dropped **nothing**.
3. **Dense barycentric sampling** (a 4×4 grid over each face) added to that helper. Grand Junction
   dropped 20 tris, 32 → **27**. Aspen still dropped nothing and stayed at **2**.

So the direction is right for Grand Junction and simply does not see Aspen's case at all.

Two further observations that should shape the real fix:

- **Dropping triangles makes the surface worse.** Grand Junction's severe steps went **39 → 44** as
  tris were removed — holes leave edges the car reads as steps. Sinking or re-seating the ring is
  likely better than deleting it.
- Even at 27, Grand Junction still fails `severe_per_km` (~31 against a 12 limit), so the ring is
  not its only problem. Aspen, by contrast, is 2 hits away from passing everything.

## Where to look next

Why `drop_over_road` sees nothing on Aspen while `drive_test` sees 2 hits at station 1466 is the
crux — the same geometry, judged by two samplers, disagreeing. `_road_tops` reads the `road` mesh
built earlier in the function; `drive_test` reads `1ROAD_*` out of the finished `track.obj`. If a
later pass moves the deck (fold pads, flat zones, the lift), the ring is clamped against a road that
is no longer where it ends up. Compare the two surfaces at station 1466 before writing any more code.

## Verification

- `soft_top_in_lane` is 0 on both tracks.
- Grand Junction's severe steps do not rise as a side effect.
- Aspen packages (it has nothing else outstanding).

---

## Attempt 4 (v0.38.0) — reverted, measured no-op. But it located the real cause.

**Result:** Aspen 2 → 2, Grand Junction 38 → 38, Under the Dragon's ring hits 9 → 9. Reverted in
v0.38.1. Recorded so it is not tried a fifth time.

**What was tried:** all three scans the ring clamps with (`_deck_window_min7`,
`_shoulder_window_min8`, `_pav_at17`) drop triangles more than 60° off horizontal as "walls", and
on a steep stage the deck itself can qualify — the same blindness that hid a 0.54 m shoulder poke
from the corridor pin in [0014](0014-road-floats-over-the-mountain-on-rally-stages.md). Adding a
no-filter point test changed nothing, so that is not what is happening here.

**What the measurement actually shows.** Under the Dragon, station 2480, the offending triangle:

```
corner (4875.49, 5666.51)  ring 200.609   road 200.613   -0.004  OK
corner (4874.57, 5678.83)  ring 200.609   road 200.553   +0.056  POKE
corner (4878.30, 5667.43)  ring 200.609   road 200.613   -0.004  OK
edges: 12.4 / 12.0 / 3.0 m
```

Three corners at **exactly** the same height across 12 m — terrain sampled at three points 12 m
apart never lands on the same millimetre, so this is not a terrain-derived row. 200.609 is
`_grid_trisurf(grid_xyz) + 0.02` with **no clamp applied at all**, where a working clamp would give
`road − 0.03` = 200.583.

**So 0012's headline is half right.** The faces do span — but not because the clamp samples too
sparsely, which is why attempts 1–3 all failed (vertex sink fired on 0 verts; `drop_over_road`
38→32; dense barycentric 32→27; Aspen unmoved throughout). Dense *sampling* cannot help when the
node was never a candidate for clamping.

The poking corner is `_m0`, the **weld vertex at ring row 0** (`build_mesh.py:1804`). It is
deliberately outside the `_RINGS17` clamp loop because it is shared *exactly* with the shoulder's
ground-meet vertex — that sharing is what makes the pavement/terrain seam watertight. It folds only
when a distinct lower sheet is more than 0.10 m beneath it. At a hairpin the opposing leg is
~0.05 m away, so it neither folds nor terminates: it spans 12 m straight over the other
carriageway, level, grazing it.

**Why 12 m:** the ring quad spans two `_secs` cross-sections, and they are 12 m apart there. The
road's own vertices are ~3 m apart. The ring is built at a quarter of the road's own density.

## What to try next (in this order)

1. **Densify `_secs` through curvature** so ring quads span ~3 m rather than 12 m. This is the same
   move that fixed the terrain in 0014 — a surface cannot follow a road it is coarser than — and it
   shortens every span without touching the weld's watertightness.
2. **Terminate the annulus where a quad would cross another leg's carriageway**, regardless of
   height difference. The existing guard only terminates on a *deep* fold (>3 m); the hairpin case
   is a shallow one and slips through. `_kcut` already exists for exactly this.
3. Do **not** retry dropping triangles: 0012 attempt 2 raised Grand Junction's severe steps 39 → 44,
   because holes leave edges the car reads as steps.

Aspen's 2 hits and Grand Junction's 38 are almost certainly this same shallow-hairpin span, which
would explain why every fix aimed at sampling density has moved Grand Junction slightly and Aspen
not at all.

---

## Attempts 5–7 (v0.39.0–v0.42.0) — the in-lane hits SOLVED; the audit poke located

**v0.39.0 zone-rim guard** — the flat-zone pad snap was overwriting the ring clamp's correct
heights (traced: clamp computed 199.946, `_flatten_pavement(ring_mesh)` rewrote it to
plane+0.004 = 200.609). At the pad rim the road interpolates off the plane across one triangle
while a just-inside ring vertex holds it. Guard: after the snap, re-tuck any in-zone ring vertex
above the pavement actually overhead. **Aspen drive_test PASS for the first time ever (2→0);
Under the Dragon ring hits 9→0; Grand Junction 38→18.**

**v0.42.0 shallow-crossing termination** (option 2 from the notes above) — flaring UTD's
switchback legs to 10 m brought the carriageways together and one leg's annulus rode over the
other at its own height (31 hits). Terminate when pavement within 3 m of the row's height has a
nearest-road station >50 m of arc away; lap-wrap safe.

**Aspen's one remaining audit poke (+0.19 at (122.5, −64.1)) is NOT the ring** — instrumented
twice: the ring meets and rows there are all correct. It is the coarse contact pin's RAISE branch:
a grid node at −0.028 raised to ~0.26 by a filtered window value (0.271, the flat shoulder top
up-slope) straight through the steep face overhead at 0.088. Neither scan sees that face — the 60°
filter rejects it, and the **no-filter point test returns None because the face's triangles are
not in `_rc8` at pin time**: the surface matches `SHOULDERUND`, built in the #17 section AFTER the
pin's hashes are frozen. An ordering problem: the pin cannot clamp against geometry that does not
exist yet. Fix candidates, unmeasured: (a) gate the raise on pavement actually overhead at the
point; (b) run a post-#17 re-pin pass over nodes the raise moved; (c) hash the #17 extensions
before the pin. Do NOT widen the raise's stencil — that is the 0014 slope charge again.

Grand Junction's remaining 18 + bumps 85.29/km (limit 75) are separate defects, undiagnosed.

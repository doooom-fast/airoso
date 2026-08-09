---
id: 0025
title: Colorado at current gates — two clean laps blocked at the runoff edge, two on surface roughness
status: fixed at the gates (v0.66.3 wave, 2026-08-09) — 5 of 7 circuits green (imi, pueblo, aspen, high-plains, second-creek); sand-creek 1 soft-top from un-excavated cut-corridor grass (deferred), lariat its own campaign; in-seat verdict open
scope: k10-colorado/imi, pueblo, high-plains, lookout-lariat
layer: engine
train: R4
---

## Context

First rebuild of the four installed Colorado tracks on a modern engine (v0.63.0, from v0.16-era
installs), 2026-08-07. All four builds were **stopped by `drive_test`** — the gates doing their
job against standards that didn't exist when these tracks last built. The installs in AC remain
the old artifacts (driveable; now at least `circuit`-tagged so Race/Track Day appear).

## The matrix (drive_test on the v0.63.0 builds)

| track | lap | soft-top | severe | kinks/km | excursion drops | far ledges | verdict class |
|---|---|---|---|---|---|---|---|
| imi | 1,441 m | 0 | **0** | 9.7 | **30** | 0 | clean lap, runoff edge only |
| pueblo | 3,451 m | 0 | **0** | 9.0 | **118** | 2 | clean lap, runoff edge only |
| high-plains | 3,102 m | 0 | 30 | 37.1 | 96 | 0 | runoff + 0018-class roughness |
| lookout-lariat | 24,803 m | 0 | 251 | 68.3 | 690 | 378 | roughness + edge (hogback legacy) |

IMI and Pueblo drive **perfectly clean laps** — zero severe steps, zero ground-through-road — and
fail exclusively on `excursion_drops` (ground falling >20 cm just beyond the pavement).

## Hypotheses

1. **KILLED: terrain cell size.** Declared `terrain_cell_m` 1.25 (imi) / 2.0 (pueblo) +
   `corridor_refine_factor` 6 per L3b; rebuilt; drops effectively unchanged (28→30, 128→118).
   The declarations are kept (L3b hygiene) but they are not this mechanism.
2. **KILLED: no archetype declared.** Checked same day — imi and pueblo already declare
   `race_circuit` (S6's "ten tracks undeclared" note predates these configs). The runoff preset
   applies; the defect is downstream of it.
3. **DIAGNOSED, primary: the apron's outer seam.** `worst_excursions` cluster at lateral
   ±9.5–10 m on a ~9.8 m road — **~4–5 m beyond the pavement edge, 0.26–0.4 m steps** — the
   built runoff/shoulder apron ends against the raw terrain grid without a feather, exactly the
   road-grounding drape class. Assigned to the geometry surgeon (2026-08-07 pm): feather the
   outer hem in `build_mesh.py`, prove on imi + pueblo (excursion_drops → 0, no regressions).
4. high-plains / lookout-lariat additionally carry the 0018 roughness class (mechanism still
   open) — they ride 0018's resolution plus hypothesis 3's fix.

## Verification

- imi + pueblo rebuild PASS drive_test after the archetype declaration (or hypothesis 2 joins 1
  in the killed list with numbers).
- The passing builds install with grid/AI/cameras and Kevin drives one.

## Fix attempt 1 — KILLED BY THE GATE (v0.65.0, reverted in v0.65.1 same hour)

A feathered flush-band lift of grass nodes toward the shoulder's outer rim. drive_test verdict on
imi: drops 30 → 29 (no help) while **severe 0 → 27 and soft-top 0 → 161** — in CUT sections the
rim sits ABOVE the deck, so lifting grass toward it pushed lawn up through the lane. The pass
ignored the one distinction the builder itself makes (`road_shoulder`'s per-station construction
selector: cutting / fill / wall). Reverted; the gate did exactly its job.

**v2 direction (the durable cut):** rim targets from FILL and WALL stations only, using
`road_shoulder`'s `sections` metadata rather than re-deriving; per-node lift additionally capped
by the LOCAL deck height (never above deck − 0.3 within lane influence); verify on imi (drops → ~0
with severe/soft-top back to 0) before pueblo.

## The campaign (v0.66.0 → v0.66.1) — 30 drops to 0 in three mechanisms

~29 gated builds. What held, in the order it landed (each intermediate hypothesis that died is a
git-side note; the survivors):

1. **Graded floor (v0.66.0, committed):** every managed boundary the builder owns — ring edge,
   shoulder ground-meets, runoff rim — becomes a floor source; grass within 5 m of a source is
   floored at `source − 0.01 − 0.22·distance`, drop-edge-prefiltered against the natural-terrain
   snapshot so real banks stay wild, pavement-capped (road/runoff/kerb, never the shoulder — the
   self-reference stranded the floor 3×). IMI 30 → 3.
2. **Measured stone lips (v0.66.1):** the last 3 (station 302.5, a cut-bench trench invisible to
   `sections` metadata — "parapets 0v" at every warrant tried) fall to the builder mirroring the
   gate's own outboard sweep 1:1 over its built meshes and straddling every measured in-band drop
   face with a 0.6 m-thick 1913-pattern lip the 0.5 m guard-probe grid cannot step over.
   Metadata cannot see the trench; the measurement is the mesh itself.
3. **[[0027]] guard exemption un-deadened (v0.66.1):** the lips were present, on-ray, correct —
   and still "unguarded", because the gate's guard scan probed the one TriField that structurally
   cannot contain a wall. One-word fix in `drive_test.py` (probe `obstacle`, not `surface`).
   Filed separately as 0027 because it is a gate defect, not a grading one.

## The wave (2026-08-09, v0.66.3) — the toolkit against the rest of Colorado

Kevin: "So you only did two tracks?" Ran the other seven. Four more mechanisms fell out, each
traced to a vertex before it was fixed (the byte-identical rule: a parameter that changes nothing
is not the lever):

4. **Ring rows obey the graded floor:** the annulus sampled the RAW grid while the seam-weld
   raised the grass beside it — a 40% construction chute at every fill edge, tripping the gate at
   every 150 m sweep station (aspen: 18 gated drops of pure gradient).
5. **Buried skirts do not clamp (the 0028 defect inside the builder):** the ring's pavement clamp
   tucked rows under the shoulder's own hem — traced live: floor raises to 3.438, clamp pulls to
   3.177 under a "pavement" at 3.207 that sits below natural grade. Per-scan discriminator: the
   deck scan always clamps (a deck cut in at grade is still a deck — second-creek proved the
   overcorrection with 68 in-lane ring soft-tops), the shoulder-family scans only when +0.10
   proud of natural grade.
6. **Fan-stitch guard:** at a tight corner adjacent ring columns fan apart and the stitched face
   sweeps across the deck while every NODE is legal — second-creek's 24 soft-tops rode a 15 m
   sliver 21 mm over the apex, byte-stable through three node-level fixes because no node was
   ever wrong. Row segments fanned > 6 m get sampled for pavement and the stitch cut at the
   first crossing.
7. **corridor_refine_factor 6 is a fleet standard, not an imi tweak:** the floor raises NODES;
   on a 2 m grid the surface between a floored node and its natural neighbour sags back under
   the line and the gate's 0.5 m samples catch it. aspen/second-creek/sand-creek/high-plains
   configs now carry the refine the proven pair always had.

Killed on the way (recorded so they stay dead): a universal deck-cap (562k nodes moved to fix
one — and missed it); an under-deck sink (697k nodes, broke kn5_ground_check's float budget);
widening the meet clamp deadband (regressed sand-creek 3→13 drops).

**Matrix on identical v0.66.3 code, all four gates:** imi PASS, pueblo PASS, aspen PASS,
high-plains PASS, second-creek PASS, sand-creek FAIL (1 soft-top: refined grass at natural
height inside the shoulder's cut corridor spans the deck edge at 8047 — the honest fix is
corridor excavation, deferred; 1 severe at 1274 unprobed), lookout-lariat FAIL (severe 1033,
drops 184 — the mountain road is its own campaign). Aspen carries a known blemish inside its
passing budget: a 13 cm/m kink in finished_centerline y at stations 1517-1519 — elevation-side,
not mesh-side.

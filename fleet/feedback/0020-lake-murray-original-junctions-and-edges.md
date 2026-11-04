---
id: 0020
title: Restored Lake Murray original — recognizable again, but junctions/sidewalks and edges/seams are messy
status: open
scope: k10-san-diego/project
layer: engine
train: R3
---

## Symptom (Kevin, from driving the restored original, 2026-08-06)

> "it's back to being recognizable but messy"

Pinned down (same session, multi-select): the mess lives in **junctions & sidewalks** (sidewalks/
curbs through intersections, junction mouths, medians) and **edges & seams** (sawtooth road edges,
road↔terrain seams, floating/angled kerbs). Explicitly *not* flagged: surface feel, dressing.
AI modes untested at time of filing (were blocked by the missing `circuit` tag — fixed same day,
engine-side in `track_folder.py`).

## Context — which artifact this is

This is the **restored v0.15-era Blender-first original** (`loop.blend` → SD's own
`build_kn5.sh`, engine pin v0.60.0, reinstalled 2026-08-06 after the deleted week).
"Recognizable" is the headline: the loop.blend truth held — identity, direction, landmarks
survive the restore. The mess is the quality floor of that artifact's generation, not a regression.

Prior art: [0013](0013-lake-murray-sidewalks-and-college-sawtooth.md) measured the same two
classes on the *engine-path* build of this track (continuous `curb_sidewalk` sweep through every
junction in `build_loop_blend.py:658/:677`; 105 width jumps >1 m producing sawtooth). The
generated underlay in `loop.blend` shares that lineage, and this build predates every gate — no
OBJ was ever audited for it (0013 §"why no gate caught it").

## Evidence (first in-game telemetry on this artifact — `ac_drive_test`, 2026-08-06 21:45)

Kevin's lap, ks_mclaren_650_gt3, 4:42.794, harness attached end-to-end (first real capture):

- **lap_completes ✓ · stays_on_surface ✓** (worst tyres-out streak 0.2 s) · speed 1.3–262.7 km/h
- **no_unexplained_contact ✗ — damage +8.42 at normalized position 0.6073** →
  station ~8,202 m of 13,506 m, world (1042, 86, −1080) engine frame, centerline index 2732:
  **NAVAJO RD** (single-street 180 m window). Something on Navajo strikes a car near the
  driving line — kerb lip, sidewalk edge, or corridor object; unverified which. The pilot
  inspects this exact station in Blender first.
- Same session, verbal: track is "messy" (verdict repeated); AI drives the loop "mostly"
  (failure specifics not yet captured).

## Diagnosis — MEASURED (2026-08-07, first offline gates ever run on this artifact)

The v0.61.0 rebuild's kn5 was extracted back to `data/track.obj` (`modkit.kn5_to_gate_obj`, L5:
gate the shipped artifact) and both missing gates ran. **Kevin's two classes are exactly what they
found:**

**Junctions & sidewalks** (audit): **K = 1,096 kerb/sidewalk verts inside the carriageway**
(worst **+1.18 m** above the road) · **I = 1,203 sidewalk-isolating-pavement spots** (e.g.
−1445, −549). The 0013 mechanism — one continuous sidewalk sweep that never breaks at junction
mouths — confirmed on this artifact by count.

**Edges & seams** (audit + drive_test): F = 285 curbs not flush · 35 daylight gaps at edges ·
8 floating fence posts at (−1874, −1025) · H = 2 ground-cuts into the road, **worst +1.1 m**,
matching drive_test's severe-step cluster at **stations 3837–3870** (steps up to 0.86 m) ·
3,991 soft-top stations (grass surfacing mid-lane, e.g. station 3804 at −6 m lateral).

Also surfaced: **tree canopy/trunk hanging into the corridor at stations 10,545–10,548** — the
strongest candidate yet for the in-game contact class (the measured Navajo contact at 8,202 m is a
different station; both go on the corridor-sweep list). Clean elsewhere: A/B/C/E/J = 0 — the
terrain/support conforming holds; this artifact's problems are the *edge and junction* layer,
precisely as Kevin said from the seat.

drive_test verdict: **FAIL** (full numbers in `project/data/drive_test.json`; audit total 3,089).

## Fix direction (why this is R3's pilot charter, not a sweep patch)

Per `fleet/REALISM.md` §8: junction mouths, sidewalk gaps, median noses are **authored, in
Blender, once per place** — the engine provides junction data and audits the result; it stops
trying to sweep pavement through intersections. Edges/seams are underlay + gate work. This entry
is the concrete work list for R3's Lake Murray pilot:

1. Refresh the data underlay under `loop.blend` (GEN_* collections) without touching Kevin's
   authored work.
2. Author the junction mouths and edge treatments (Claude via live bridge, Kevin directing).
3. Export → OBJ → all four gates → kn5; drive_test and audit numbers recorded here.
4. Kevin drives; "messy" either survives or it doesn't.

## Corridor discipline outcome (2026-08-07, engine v0.63.0 — the mechanical half, landed)

Four build iterations, each steered by a gate catch (two palm-crown shears caught by
kn5_ground_check, one canopy miss caught by drive_test's centroid blind spot):

| metric | baseline | after v0.63.0 |
|---|---|---|
| obstructed stations | 14 | **0** |
| severe steps | 69 | **31** |
| trunks standing in a road | (uncounted) | **61 removed, whole** |
| audit total | 3,089 | 2,685 |
| K kerb/sidewalk in carriageway | 1,096 | 904 |
| I sidewalk isolating pavement | 1,203 | 1,008 |

Ground-on-top mid-lane (~4k stations) is untouched — that is R4 surface-layer work, not corridor
work. The residual K/I ≈900 with worst +1.18 m is the junction-mouth SHAPES: the authored half
(REALISM §8), which this entry stays open for. Installed same day with the full presentation
stack (grid, frame-fixed AI, traffic lanes, 39 TV cameras, GrassFX).

## Race kerbs leave Rule 1's carve (2026-11-03)

Rule 1 (no kerb face inside any carriageway) is for street kerbs and sidewalks. A race kerb (`1KERB_RACE_*`) is laid on the lane's edge
at a corner on purpose. On Lake Murray v5's engine ribbon the carve emptied two of them and broke the race kn5 export. The prep now
skips `1KERB_RACE_*` (`build_kn5_loop.corridor_carves_kerb`); verify_race E/O and the race layouts' drive_test judge them instead.
fleet/GATES-CHANGELOG.md, 2026-11-03.

## Verification

- No sidewalk/curb geometry inside any junction mouth on the loop (0013's criterion, now on this
  artifact).
- No width jump >1 m between adjacent centerline vertices; road↔terrain seams flush in lateral
  cross-sections of the exported OBJ (L9).
- Kevin drives the loop and the word he reaches for is not "messy".

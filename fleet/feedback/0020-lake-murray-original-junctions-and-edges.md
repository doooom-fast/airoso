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

## Diagnosis

Deferred — 0013's mechanisms are the obvious suspects, but per the doctrine this entry stays open
until measured on THIS artifact (export the OBJ from loop.blend, run `audit_mesh` + `drive_test`,
cross-section the junction mouths). An empty diagnosis is better than a confident wrong one.

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

## Verification

- No sidewalk/curb geometry inside any junction mouth on the loop (0013's criterion, now on this
  artifact).
- No width jump >1 m between adjacent centerline vertices; road↔terrain seams flush in lateral
  cross-sections of the exported OBJ (L9).
- Kevin drives the loop and the word he reaches for is not "messy".

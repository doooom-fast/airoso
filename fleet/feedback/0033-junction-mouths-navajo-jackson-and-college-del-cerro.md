---
id: 0033
title: Two junction mouths named undriveable — Navajo/Jackson, and Del Cerro's sidewalks criss-cross College
status: diagnosed
scope: k10-san-diego/project (stations ~6944 and ~3236–3248)
layer: project
train: -
---

## Symptom (Kevin, driving the installed track, 2026-08-19)

> "Intersection of Navajo and Jackson: messy and undriveable."
> "Intersection of College Ave and Del Cerro Blvd: criss-crossing sidewalks running THROUGH the
> street."

Artifact: the **v0.21.0 kn5 × engine v0.24.3** reference install (see
[0032](0032-college-ave-sawtooth-is-narrow-stripes.md) for provenance). The defect *class* is
already diagnosed — [0013](0013-lake-murray-sidewalks-and-college-sawtooth.md) §1's continuous
`curb_sidewalk` sweeps, [0001](0001-junction-flare-drags-the-sidewalks.md)'s flare drag — and
[0020](0020-lake-murray-original-junctions-and-edges.md) already counted it in the thousands
(K = 1,096 kerb/sidewalk verts in the carriageway, I = 1,203 on the restored artifact). What this
entry adds is the **per-place work list**: Kevin has now named the two worst mouths, and under
REALISM §8 junction mouths are *authored, in Blender, once per place* — so named places with
stations are exactly the unit the fix ships in.

## Evidence (data re-derived 2026-08-09 at the same pin, `k10-sd-v021/project/data/`)

**Navajo Rd & Jackson Dr — mainline station 6944 (vertex 2323).** Everything wrong on this track
converges on this one mouth:

- Width flips **9.0 → 24.0 in a single vertex** at the junction (verts 2311–2334:
  `[9.0 ×7, 24.0 ×17]`) — a split-carriageway narrow stripe (0032) colliding with the junction
  flare (0001).
- `navajo_road_opp` — the phantom opposing carriageway
  ([0035](0035-the-phantom-opposing-carriageway.md)) — **dead-ends at station 6953, 9 m past the
  junction**, 16.5 m off the mainline: a severed 9 m-wide ribbon end sitting in the mouth's
  sightline.
- The loop's continuous sidewalk (`build_loop_blend.py:658`) sweeps straight through the corner;
  nothing gaps it.

**College Ave & Del Cerro Blvd — mainline stations 3236–3248.** The `del_cerro_blvd` connector
(the 3.3 km sub-loop) meets College **twice, ~12 m apart**: connector pt 877 passes 3.4 m from
College's centerline (on the pavement, dy −0.2 m) and pt 222 at 9.8 m. Each connector leg is a
10 m ribbon that gets its own raised `curb_sidewalk` swept along *both* edges
(`build_loop_blend.py:677-679`) — so two pairs of raised sidewalks run **across College's
pavement**, while College's own continuous sidewalk runs across both connector mouths. That is
Kevin's "criss-crossing sidewalks running THROUGH the street," literally. The width array at the
same spot flickers `17.0 → 9.0 ×8 → 23.4 → 9.0 ×8 → 21.4` (verts 1075–1099) — a one-vertex 14 m
spike in the middle of the mouth (0032's stripes interleaved with the flare).

## Diagnosis

No new mechanism: 0013's sweep-through-every-junction plus 0001's flare, at the two places where
they compound with 0032/0035. Both sweeps take the full flared-and-striped widths array and never
break at a junction; the audit checks that see this (K, I) exist but K does not gate (see
[0036](0036-sidewalk-sweeps-vs-multi-street-networks.md)).

## Fix

Per REALISM §8 and 0020's R3 charter: these two mouths are **authored** — sidewalk gapped across
each mouth, curb returns and mouth shape hand-edited in `loop.blend` (Claude operating, Kevin
directing), on top of a draft that no longer sweeps pavement through them (engine half: 0036).
Do not rebuild the Blender-first project to get there — the underlay refresh must respect the
collection contract (REALISM §4). Prerequisites that make the authoring cheap: 0032 (delete the
stripes) and 0035 (delete the `_opp` ribbons) land first, so the mouths being authored are the
real ones.

## Scope

`k10-san-diego/project`, these two named places. The class fix for every other mouth on this
track and on Sand Creek rides 0036. Regression case: the mouths *not* named — after authoring
these two, audit K/I at the others should be unchanged (proves the edit was local).

## Verification

- Audit **K = 0 and I = 0 within the junction-mouth polygons** at stations 6944 and 3236–3248 on
  the exported OBJ (`audit_mesh` already reports both; scope them to the mouths).
- No ribbon dead-end visible in either mouth (0035's check).
- Kevin drives Navajo→Jackson and College past Del Cerro and neither word is "messy" nor
  "undriveable."

## 2026-10-08 — C2 v1 built: ribbon-through at every connector mouth

- `tools/trim_connectors.py` cuts each connector polyline at College's pavement edge (0.4 m
  overlap, no sliver): del_cerro_blvd → 3 pieces, 18 points inside the mainline dropped, **4 mouth
  cuts at College verts 1083–1088** — it is a 4-way crossing, both legs of the sub-loop meet
  College here. `tools/gap_mouths_blend.py` removes the mainline's own curb+sidewalk faces across
  each mouth on the connector's side (126 ring faces, station windows = connector half-width + 3 m).
  The island is gapped across the same mouths by `median_envelope` (verts 1072–1099).
- Measured on the gate OBJ (correct frame, island-aware): **K 1,096 → 387, I 1,203 → 417** vs the
  July reference. What remains is NOT College/Del Cerro: the samples sit at (3, −1654) — the
  southern seam where the wisconsin/connecticut connectors end beside the mainline without
  crossing it (ends 14.9 / 44 m off, so no cut) and the sub-loop streets meet EACH OTHER
  (airoso/adelante/colorado/connecticut/wisconsin). Connector-to-connector mouths = C2 v1.5.
- Navajo/Jackson (station 6944, vert 2323): the width flip and the `navajo_road_opp` stub are
  gone with C1; the ring's own sidewalk still wraps the inside of the corner as a ribbon. A
  proper 4-way pad is C3-class authored work (docs/JUNCTIONS.md, PAD topology).
- Not yet authored: corner-return arcs (JUNCTIONS R4). v1 is the gap 0036 routes; the pros wrap
  the corner on R 3–6.5 m — next authored step, after Kevin's seat on the gapped mouth.
- Spawn: `start_positions.json` → `0033-college-del-cerro` (vert 1078, right lane, mouth ~30 m ahead).

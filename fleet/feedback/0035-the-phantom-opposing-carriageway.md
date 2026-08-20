---
id: 0035
title: A westbound lane appears out of nowhere, floats, and cannot be reached — the split-carriageway `_opp` ribbons
status: diagnosed
scope: k10-san-diego/project (college_avenue_opp, 1585 m; navajo_road_opp, 806 m)
layer: project
train: -
---

## Symptom (Kevin, driving the installed track, 2026-08-19)

> "College Ave: a westbound lane that appears out of nowhere, floats like a ribbon, and is
> inaccessible to drive."

Kevin has seen it before, less specifically — [0029](0029-the-product-bill.md), verbatim: "Lanes
go in and out of existence for college and Navajo" and "roads I can't even access." Artifact: the
**v0.21.0 kn5 × engine v0.24.3** reference install (provenance in
[0032](0032-college-ave-sawtooth-is-narrow-stripes.md)).

## Evidence (data re-derived 2026-08-09 at the same pin, `k10-sd-v021/project/data/`)

The object is **`college_avenue_opp`** — the opposing carriageway that `route.split_carriageways`
adds beside the loop. Measured from `connectors.local.json` against the mainline:

- **Appears out of nowhere:** it is a 1,585 m ribbon whose ends are bare caps **11.1 m and
  14.2 m laterally from the mainline** (at mainline stations 2948 and 4539). No taper, no merge,
  no junction — `extra_lines.py:205-224` deliberately clips it to "the longest well-separated
  run" (≥ 11 m from the loop), so by construction it *starts and ends mid-street*.
- **Floats like a ribbon:** it is sampled on its own 3DEP line (`extra_lines.py:240-242`) and
  runs up to **±5.9 m vertically** from the adjacent mainline (College's real per-direction
  split), 11–21 m away laterally. And its ground contact is measured bad:
  [0019](0019-a-divided-street-loses-its-embankment.md)'s gate tail has
  `1ROAD_college_avenue_opp` at **p95 1.123 m, max 1.936 m above ground** — *after* 0019's fix;
  the pre-fix worst was 6.908 m, and the shipped v0.21 artifact predates all of it.
- **Inaccessible to drive:** constant 9.0 m width (`extra_lines.py:245-247`), behind the median
  gap, with its own raised `curb_sidewalk` swept along both edges
  (`build_loop_blend.py:673-679`) — curbed in on both sides, connected to nothing. No crossover
  exists anywhere on the loop.

`navajo_road_opp` is the same defect, 806 m, ending **9 m past the Navajo/Jackson junction**
(part of [0033](0033-junction-mouths-navajo-jackson-and-college-del-cerro.md)'s mess).

## Diagnosis

The split-carriageway feature emits each opposing carriageway as an independent connector-kind
ribbon: clipped to the divided run (so it terminates abruptly), elevation-sampled independently
(so it rides its own datum), never joined to the mainline (so it cannot be entered), and curbed
like a street (so even a grass excursion cannot reach it). Every property Kevin named is the
feature working as written. The narrowing it forces on the mainline is 0032.

## Fix

Already decided, in [0029](0029-the-product-bill.md): **"DELETE, don't compensate: split
carriageways, per-direction elevations … come OUT of the street path. One ribbon per road."**
Concretely: drop `split_carriageways`/`split_width_m` from `project/track.config.json`, re-derive
`connectors.local.json` (the `_opp` entries and `narrow_main` disappear), refresh the underlay
without touching authored collections. If Kevin ever wants a real divided College, it is authored
in `loop.blend` per REALISM §8 — a median island on one wide ribbon, with real mouths — not
generated as a second road. Do not build crossovers, tapers, or seating passes for the `_opp`
ribbons; that is compensation for machinery already ordered deleted.

## Scope

`k10-san-diego/project` only — the machinery is SD-local (`scripts/geometry/extra_lines.py`, on
the registry allowlist; no engine counterpart exists). Proof case: College Ave. Regression cases:
the Del Cerro sub-loop connectors must survive the re-derivation unchanged (they are `kind:
connector`, a different code path), and the mainline outside the divided sections must not move.

## Verification

- No group matching `*_opp` in the exported OBJ/kn5 (`verify_kn5` group listing or a grep of
  `track.obj`).
- Reachability: every `1ROAD_*` group connects to the mainline pavement (a drive_test-style flood
  from the grid; today `college_avenue_opp` fails it by 11.1 m of grass and two curbs).
- 0032's width criterion holds on the re-derived centerline (the stripes die with the same
  config key).
- Kevin drives College and there is exactly one College.

---

**2026-08-19 (C1 build):** split-carriageway machinery deleted (config + connectors.local.json); rebuilt via the v021 workshop; July verify gate PASS. Width steps >3 m on the mainline: 70 -> 0 (>1 m: 105 -> 62, remaining are OSM lane transitions). Installed side-by-side as san_diego_lake_murray_v3 (0.16.0) for the A/B. Status stays until Kevin's seat verdict.

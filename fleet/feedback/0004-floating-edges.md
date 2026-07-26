---
id: 0004
title: Roads, sidewalks and curbs still float; and San Diego is never drive-tested
status: open
scope: all kinds
layer: engine
train: 01
---

## Symptom

> "roads/sidewalks/curbs that don't float"

Deck hovering over the grass with a shadow gap under it, curbs floating at an angle beside the road,
run-off that ends in a cliff.

## Evidence

Unlike `0001`, this is not an undiagnosed defect — it is a **known failure class with existing
machinery**, which means the interesting question is where that machinery is not running.

Already in place:

- `road-grounding` (skill): build terrain *up* to the road with embankment fills and cuts, drape
  every edge strip onto the real grass surface, span deep gaps with bridges. Verify with lateral
  cross-sections of the **built** `track.obj`, not by eye.
- `audit_mesh`: check **B** terrain poke-through, check **E** walls floating over ground, plus the
  wall/curb cruft pass and the curb-flush check.
- `drive_test`: sweeps six wheel paths and asks what is under the tyre, what is in the corridor, and
  whether the surface is smooth at speed.
- `LAWS.md` L4 (conform passes never cross layers) and L9 (curbs tight to the edge at deck height).
- `build_mesh` already drapes the outer edge of both edge profiles onto `grass_surf`
  (`scripts/geometry/build_mesh.py:843-846`).

And yet floating persists. Two concrete reasons found so far:

1. **`k10-san-diego` never runs `drive_test`.** Its build scripts run `audit_mesh`, `verify_kn5` and
   `kn5_ground_check` — but not the one gate that simulates what the car feels
   (`fleet/cli.py lint`, rule S8). So the Lake Murray loop and the freeway network have never been
   checked for ground-through-road or steps at speed. That is 2 of the fleet's 15 tracks, including
   the largest.
2. **The pins have drifted.** Grounding fixes landed in the engine after `v0.16.0`; colorado and
   san-diego are still pinned there (rule S3). Whatever was fixed in `v0.17`–`v0.19` has never
   reached 12 of the 15 tracks.

## Diagnosis

Partly a coverage problem rather than a geometry problem: the gates that catch floating exist, but
they are not all running on all tracks, and the fixes are not all reaching all tracks. Fix the
coverage first — it is cheap, and it tells us what is actually still broken versus what was fixed
in a version 12 tracks never received.

What remains after that is expected to be the genuinely hard case: floating on **stacked** geometry
(switchbacks, canyon shelves, freeway decks), where L4's layer-gap rule decides which surface an
edge is allowed to seat onto. That interacts directly with `0002` — an edge cannot be seated
correctly against a road whose own vertical datum is wrong.

## Fix

1. Wire `drive_test` into `k10-san-diego`'s build paths (S8). Do this first; it is a few lines and
   it produces evidence.
2. Converge the pins (S3, `fleet/MIGRATION.md` M6), rebuild the fleet, and collect what still floats.
3. Triage the survivors with `road-grounding`'s cross-section method against the built `track.obj`.
   Re-file anything that turns out to have a distinct cause as its own entry rather than growing
   this one.

## Scope

All 15 tracks. `k10-san-diego/project` and `project_freeway_net` are the highest-value cases — they
are both large and both currently ungated by `drive_test`.

Caution: the SD loop is **Blender-first** — `loop.blend` is the source of truth and carries hand
edits. Gating it is safe; regenerating it is not.

## Verification

- `python3 -m fleet.cli lint` reports S8 clean for every repo.
- `drive_test` passes on all 15 tracks, and the failures it reports on its first run against San
  Diego are recorded here before being fixed.
- Lateral cross-sections at random stations on each track show no gap between deck, curb and
  terrain.

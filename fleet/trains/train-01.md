# Train 01 — clean drivable output

**Status:** loading · **Engine tag:** _(unassigned — see MIGRATION M1)_ · **Opened:** 2026-07-25

The first train. It carries Kevin's founding feedback on drivability, and it is deliberately
sequenced so that the invasive change lands last, against a fleet that is already converged and
already gated.

## Load

| # | Entry | Layer | Blast radius | Order |
|---|---|---|---|---|
| [0004](../feedback/0004-floating-edges.md) | Floating edges; SD never drive-tested | engine | coverage only — wires a gate, converges pins | **1st** |
| [0001](../feedback/0001-junction-flare-drags-the-sidewalks.md) | Junction flare drags curbs/sidewalks | engine | edge sweep on street tracks; road ribbon untouched | **2nd** |
| [0003](../feedback/0003-switchback-banking.md) | Crown + superelevation on real roads | standard → engine | cross-slope on street/rally tracks; circuits excluded | **3rd** |
| [0002](../feedback/0002-road-elevation-datum.md) | Road vertical datum vs bare earth | engine | road Z on **every** track — everything else re-gates | **4th** |

## Why this order

`0004` first because it is almost free and it produces evidence: wiring `drive_test` into San Diego
and converging the pins tells us how much of the floating is a genuine geometry defect versus a fix
that never reached 12 of the 15 tracks. Diagnosing the rest before that is guessing.

`0001` second because it is well-diagnosed, surgical, and touches only the edge sweep — the road
ribbon does not move, so nothing else in the train has to be re-proven because of it.

`0003` third, and it starts by **amending L10**, not by writing code.

`0002` last because it moves road Z everywhere. Landing it against a fleet whose edges are already
correct and whose gates are already running everywhere means a failure is attributable to it.

## Prerequisites

This train cannot converge until `fleet/MIGRATION.md` **M1** (publish + tag) and **M2** (re-point
consumers) are done — there is no tag for `fleet.cli pin` to point at yet. `0004`'s first step (wire
SD's `drive_test`) is independent and can start immediately.

## Build matrix

Filled in at step 6. `—` = deliberately excluded, with the reason.

| Track | Kind | mesh | drive_test | audit_mesh | kn5 | driven |
|---|---|---|---|---|---|---|
| k10-colorado/sand-creek | fictional_street_circuit | | | | | |
| k10-colorado/lookout-lariat | street_port | | | | | |
| k10-colorado/imi | circuit_port | | | | | |
| k10-colorado/aspen | circuit_port | | | | | |
| k10-colorado/grand-junction | circuit_port | | | | | |
| k10-colorado/pikes-peak | circuit_port | | | | | |
| k10-colorado/pueblo | circuit_port | | | | | |
| k10-colorado/high-plains | circuit_port | — | — | — | — | fabricated geometry (L1) |
| k10-colorado/second-creek | circuit_port | — | — | — | — | fabricated geometry (L1) |
| k10-colorado-rally/dragon-tail-gravel | rally_stage | | | | | |
| k10-colorado-rally/dragon-tail-tarmac | rally_stage | | | | | |
| k10-colorado-rally/under-the-dragon-gravel | rally_stage | | | | | |
| k10-colorado-rally/under-the-dragon-tarmac | rally_stage | | | | | |
| k10-san-diego/project | street_port | — | | | | Blender-first: gate only, no re-seed |
| k10-san-diego/project_freeway_net | street_port | | | | | |

## Exit criteria

- `python3 -m fleet.cli lint` clean (S3, S4, S6, S8 in particular).
- Every non-excluded row green.
- Kevin has driven Sand Creek (edges), Lariat (banking + grade) and the SD loop (floating) on
  Windows and signed off.
- Anything found in that drive is filed as new ledger entries for train 02 — not patched into this
  one after the matrix went green.

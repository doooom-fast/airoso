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

## Build matrix — measured 2026-07-25, k10-colorado through the engine (v0.21.1)

`GATE_EXCURSIONS_ADVISORY=1` (rc setting). Supersedes the v0.20.2 table below.

| Track | drive_test | audit_mesh | kn5 stage | blocker |
|---|---|---|---|---|
| sand-creek | **PASS** | **CLEAN** | — | road-float check (see below) |
| lookout-lariat | **PASS** | **CLEAN** | verify FAIL | dup mesh names — [0007](../feedback/0007-exporter-duplicates-mesh-names.md) |
| imi | **PASS** | **CLEAN** | — | road floating 73.7% |
| pueblo | **PASS** | **CLEAN** | — | road floating 76.0% |
| second-creek | **PASS** | **CLEAN** | — | road floating 79.9% · *fabricated* |
| high-plains | **PASS** | **CLEAN** | — | road floating 88.7% · *fabricated* |
| aspen | FAIL | — | — | drive test |
| grand-junction | FAIL | — | — | drive test |
| pikes-peak | FAIL | — | — | drive test |

**6 of 9 pass drive_test AND audit clean**, up from 0 building at all at the start of the day.
Sand Creek needed 29 despiked strip verts to get there; the rest came from un-forking colorado
(M3), the bridgeless-track crash fix (v0.20.2) and the curb-flush rescope (v0.21.0).

### The open contradiction — read this before working on road float

`kn5_ground_check` reports the road floating over ground on **73.7–88.7%** of samples for four
tracks. The same four percentages appeared before AND after un-forking, so it is not a fork
artifact and it is stable.

But two other gates measuring closely related things disagree, on the same builds:

- `drive_test`: **0 daylight gaps at edges**
- `audit_mesh` check B (terrain poking through road): **0**; check H (ground cutting into road): **0**

They cannot all be right about one piece of geometry. The difference worth chasing first is *what
each reads*: `audit_mesh` and `drive_test` measure the built `track.obj`, while `kn5_ground_check`
measures the **shipped kn5** — which on this path is written via an intermediate FBX
(`[build_kn5] no direct kn5 exporter found — wrote AC-standard FBX`) and a second Blender program.
So the disagreement may be about alignment between those two artifacts rather than about the road.

Given today's pattern — three of four investigations found a gate measuring the wrong thing rather
than broken geometry — establish which artifact is wrong before changing any terrain code.

## Build matrix — superseded (v0.20.2)

### v0.20.2 table


First honest sweep, after un-forking colorado (M3). `GATE_EXCURSIONS_ADVISORY=1` (rc setting).

| Track | mesh | drive_test | audit | kn5 | blocker |
|---|---|---|---|---|---|
| sand-creek | ok | **PASS** | **F=31** | — | curb flush (was 4619 — see below) |
| lookout-lariat | ok | **PASS** | **clean** | FAIL | duplicate `1WALL_barrier_a/_b` meshes — AC drops dup-named meshes from collision |
| imi | ok | **PASS** | **F=18** | — | curb flush |
| second-creek | ok | **PASS** | F=18* | — | curb flush · *fabricated geometry, proves nothing* |
| high-plains | ok | **PASS** | F=168* | — | curb flush · *fabricated geometry, proves nothing* |
| pueblo | ok | **PASS** | **clean** | FAIL | road floating over ground, 76.0% of samples |
| aspen | ok | FAIL | — | — | drive test |
| grand-junction | ok | FAIL | — | — | 23 ground-on-top, 42 severe steps |
| pikes-peak | ok | FAIL | — | — | 70 severe steps |

**6 of 9 pass the drive test.** Two tracks (grand-junction, pikes-peak) only got this far because
v0.20.2 fixed a crash that killed every bridgeless track in `build_mesh`.

**v0.20.5 rescoped check F** (`*` = not yet re-measured). The `1KERB` group is the whole swept
strip — curb, walk, verge, embankment skirt — so 99.3% of Sand Creek's 4,619 flags lay beyond 3.5 m
from any road vertex, and exactly **2** sat at the road edge. Scoped to the road edge, Sand Creek
reads **31**; the 7,789 skirt verts are still counted and reported as advisory.

The 31 that remain are real: curbs sitting **0.5–1.4 m BELOW** the adjacent road edge, clustered at
~6 locations (e.g. 3 verts at x=-1771/z=-488, 2 at x=767/z=75). That is the genuine version of the
defect, and it is small enough to fix by inspection.

The earlier dominant defect was **audit check F, curbs not flush** — and it is newly visible:
colorado's fork grepped a `"KERB"` prefix against groups named `1KERB_*`, so F reported "0 of 0"
for months. Sand Creek's 4,619 is the same underlying curb/sidewalk problem as
[0001](../feedback/0001-junction-flare-drags-the-sidewalks.md).

Not yet swept: **k10-colorado-rally** (held at v0.19.0 — see
[0006](../feedback/0006-head-regresses-rally-terrain.md)) and **k10-san-diego** (Blender-first; must
not be re-seeded).

## Build matrix — planned

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

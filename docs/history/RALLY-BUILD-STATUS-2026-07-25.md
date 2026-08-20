# Build status — Dragon Tail (gravel)

Written 2026-07-25, engine pinned at **prodrive-ac-builder v0.19.0**.

## Built, drivable, and past every geometry gate

| Gate | Result |
|---|---|
| `drive_test` | **PASS** — ground-through-lane 0, excursion drops 0, undrivable corners 0, obstructions 0, daylight gaps 0; severe 9.2/km (limit 12), bumps 111/km (limit 150 for gravel); replication vs measured road 0.06 m median, 0.79 m p95 |
| `audit_mesh` | **CLEAN** — zero on all nine checks |
| `verify_kn5` | **PASS** — no duplicate meshes, drivable surfaces face-up, spawns on road |
| `kn5_ground_check` fidelity | **EXACT** — every group 0.00 m worst deviation OBJ→kn5 (the native writer doesn't go through Blender) |

The kn5 is 230 MB: 156 meshes, 10 textures, 12 dummies, plus a reverse-spawn kn5.
Route is 25.2 km of County Road 116, real USGS 3DEP elevation (1,833–2,216 m, 619 m of
climb), point-to-point with the grid at 47 m, splits at 8.4 km and 16.8 km, finish at
25.18 km.

## The one gate still red: road-over-ground

`kn5_ground_check` fails its **contact** check — the 1GRASS surface sits below the deck by
more than the 5 cm the gate allows, on 98.5% of samples. `ROAD_GAP_FRAC = 0.0`: green means
zero, deliberately.

    deck-vs-mountain (tri-exact): median +0.466  p95 +1.482  max +3.495

**The gap scales with road grade** — measured under the centreline:

| local grade | samples | median gap |
|---|---|---|
| under 2% | 116 | **0.304 m** |
| over 10% | 29 | **1.111 m** |

That 3.7× spread is the diagnostic signal: whatever conforms the terrain under the deck
loses contact in proportion to how steeply the road is descending. This is the "deck+apron
raft" failure the repo has hit before (see the Lariat notes) — the road riding above the
world it is supposed to sit on.

**What is NOT the cause** (each ruled out by measurement, not reasoning):
- not kn5 assembly — fidelity is 0.00 m on every group
- not terrain resolution alone — this is at `terrain_cell_m: 8.0` (x5, 1.46 M verts), finer
  than the 10 m default
- not poke-through in disguise — the audit's checks B and H both read 0, and the drive test
  finds zero ground through the lane; the terrain is strictly *below* the road, just too far

**What was not confirmed:** the mechanism. The obvious suspect is
`clamp_terrain_below_road` taking a minimum over road vertices within `reach`
(18 m at 8 m cells), which on a grade would pull each grass node down toward the downhill
deck height. But the clamp's distance-graded `recover` should let the *nearest* vertex bind
first, which argues against it. Do not act on that guess without measuring.

**Not to be worked around:** `GATE_CONTACT_ADVISORY=1` silences this check. Its own message
says sub-5cm everywhere is blocked on the verge-density-gradient work (engine task #17).
Setting it would ship a track whose road floats half a metre over its terrain, against an
explicit "green needs to be zero" standard. It stays unset.

## Where the release stands

Dragon Tail gravel is **built and drivable** but **not released**, because this gate is red.
Everything downstream is staged and mechanical once it's green:

- tarmac twin: geometry already copied into `tracks/dragon-tail-tarmac/data/`, so it forks
  only at `road_surface`
- Under the Dragon: 25.7 km of CR 109, elevation already sampled and verified (1,802–2,045 m,
  both ends seated on real ground)
- `v0.1.0` release: four installable zips

## Two thresholds that want seat time

Both are new for unpaved roads and both are reasoned rather than driven:

- **bump rate 150/km** (vs 75 for tarmac). Dragon Tail measures 111. Derived from "gravel is
  rougher than the paved Sand Creek reference" — true, but not measured against anything.
- **run-off face limit 1.0 m.** The last excursion hits before the flare fix were 1.01 m and
  1.17 m, close enough to the line to matter.

Windows seat time is the only real calibration for either.

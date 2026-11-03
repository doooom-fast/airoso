---
id: 0076
title: Dragon Tail (Gravel) failed drive_test on one floating stone lip, not on its steps
status: fixed-awaiting-rebuild
scope: tracks/rally-dragon-tail-gravel (and every constructed-corridor track's measured-guard lips; every open stage's replication read)
layer: engine
train: -
---

## Symptom

PC chain run 1 (0.2.0, 2026-11-03), the stage's first build through the chain: drive_test FAIL. The report read severe
steps 182 (worst 0.198 m at 6,608 m), clusters at 5,430, 5,611-5,614, 5,949-5,982, 6,037-6,043, 6,403-6,411 and
6,602-6,615 m, kinks 60.18 /km, bumps 27.87 /km, floating furniture 2 at (3,449, -1,700) 1.84 m, and replication vs
measured road 0.96 / 3.41 / 9.66 m (median / p95 / max) against Pueblo's and Aspen's 0.03. Audit and kn5_ground_check
passed. Records: `origin/claude/dragon-tail-gravel-run1`.

## Evidence

Mac draft, `build_mesh` + `drive_test` on a copy of run 1's `tracks/rally-dragon-tail-gravel` (its OSM cache, 3DEP
heightfield and `corridor.elev.json`; no `loop.blend`), engine at run 1's head:

- Same numbers as the PC within the OBJ's last digit: severe 182, bumps 27.91 /km (PC 27.87), kinks 60.18, vertex bumps
  1,140 (1,141), far ledges 124 (125), floating furniture 2 at (3,449.3, -1,700.6) 1.84 m and (3,450.3, -1,700.6)
  1.85 m, replication 0.96 / 3.41 / 9.66. `finished_centerline.json` is identical to the PC's `gate_centerline.json`;
  `track.obj` differs in md5 only.
- **The verdict is the floating furniture alone.** `drive_test`'s fail rule (`scripts/geometry/drive_test.py`, the
  `fail =` block): severe 7.21 /km is under its 12, bumps 27.87 /km under gravel's 150; kinks do not gate. Every other
  zero-gate (ground on top, daylight, excursion drops, obstructions, undrivable corners, barriers) read 0.
- **Fold pads: none.** `build_mesh`: `[fold plateaus] 3 apex(es) leveled locally (declared: [6394, 6595, 7455])`,
  `[fold pads] discs at 0/3 apexes`; `flat_zones.json` is `[]`. The three apexes are the config's `wide_corners`
  (6,364 / 6,565 / 7,425 + the 30 m lead-in), each on a 9-10.5 % chord, so PR 25's `fold_pads: false` changes nothing
  here. `bridge.spans.auto.json` is `[]`.
- **L11 / L13.** The stage is open (8,413 points, no repeated vertex); the steps are 5-22 km from either end and nowhere
  near a seam. The ends' only artifact (the lead-in station over bare ground) is already skipped ("1 station skipped:
  no pavement").

## Diagnosis

**1. The floating lip (the gate failure).** `build_mesh`'s measured-guard pass sets a stone lip (`1WALL_PARA_stone`,
0.7 m tall, ledger 0025) where a cross-section drops > 0.115 m within 4 m of the built edge. It seats the lip at the
crossing (`min(prevH, deck + 1.8) - 0.2`) and lays it FLAT 1.5 m up and 1.5 m down the edge. At s 6,645, the exit of the
second switchback, the crossing is 9 m right of the centreline (the shoulder there reaches 8.6 m) on ground that falls
toward the hairpin bowl and the lower leg 10 m below: along the lip's 3 m the ground runs 188.47 -> 186.10 m. The lip's
base is 187.94 m, so its south foot hung 1.84 m over the grass (`1GRASS_ba` 186.10 under both corners). drive_test's
furniture-seating rule (base within 0.8 m of the surface beneath, excused only by a grounded column within 2.4 m) has
nothing to excuse it: the lip's other end is 3 m away. Nothing ever checked the lip's feet, only its crossing.

**2. The 0.96 m replication (a measurement bug, not the profile).** drive_test compares the gate line's vertex i with
`z_raw_m[i]`. The gate line carries build_mesh's lead-in (`[lead-in/out] 10 verts (30 m) of road past each open end`:
8,433 vertices against 8,413 measured), so every vertex was read against the road 30 m on; at the stage's 4.35 % mean
grade that is ~1.3 m. Aligned (the gate line's vertex 10 sits exactly on the local line's first point, 0.00 m) it is
**0.02 / 0.21 / 7.16 m**, Pueblo's and Aspen's class. The profile is not over-smoothed (local y vs raw: median 0.01 m)
and is not sampled on the wrong line. The 7.16 m max is real and is item 3c below.

**3. The 182 severe steps (pass the gate; diagnosed, not changed).** Re-measuring each one on the wheel path's own
travel (drive_test's own VERTEX BUMPS measure, which today it applies to 2.5-6 cm bumps only):

| group | stations | count | on own travel: <2.5 / 2.5-6 / >6 cm | mechanism |
|---|---|---|---|---|
| a. curves | 5,430-6,043, 8,562-9,904, 13,186-19,296, 21,635, 22,306 | 76 | 46 / 25 / 3 (+2 unmeasurable) | the probe, not the road: a fixed-offset path on 3 m vertices hops at each vertex on a 13-28 m radius (inner path advances 0.4-0.6 m, outer 1.3-1.6 m, in a 1 m step) and on a 5-15 % grade that hop alone reads 6-11 cm |
| b. the three declared hairpins | 6,403-6,411, 6,602-6,619, 7,464-7,499 | 83 | 20 / 29 / 34 | real: the inner lane of a 10-11 m-wide switchback on a 10-14 % climb, steepened by the ±40 m fold plateau, which flattens the apex and pushes the climb into the exits (built 13.2-13.3 % vs smoothed 10.4-10.9 % at 6,403 and 6,602) |
| c. two capped crests | 20,855, 21,444-21,447, 21,558 | 23 | 0 / 2 / 21 | the 18 % grade cap meeting a 3DEP hump: raw rises to 172.98 m at 20,872 and falls 8 m in 18 m (44 %, not a county road: the line reads a cut bank); the capped profile draws a tent +17 % -> -18 % with 9-10 %-pt grade changes at single 3 m vertices, every wheel path 6.1-6.7 cm. The hump is the 7.16 m replication max. 21,444 is the same shape at the top of an 18 % ramp |

Measured and not taken: dropping the fold plateau at the three declared apexes (a scratch switch, not committed) makes
it worse — severe 182 -> 260 (worst 0.208 m at 7,456), kinks 60.18 -> 66.63 /km, floating furniture 7. The plateau
stays.

No real road feature was found rough: no ford, cattle guard or bridge in the steps (no span minted; group c is a DEM
reading of a bank, not a road crest).

## Fix

Engine, both plain bugs everywhere; no gate threshold moved, no config key added.

1. `scripts/geometry/build_mesh.py`: `lip_foot_gap` / `lip_foot_reach`. Each lip foot (both corners, inboard and
   outboard) is read the way drive_test reads a 1WALL column; a foot more than 0.8 m over the surface beneath is pulled
   back toward the crossing in 0.25 m steps until it stands (a chained start, the previous lip's end, is left as it
   was). A lip whose feet already stand is byte-identical: on Dragon Tail 1,732 of 1,733 lips are unchanged and the one
   at s 6,645 now runs 1.0 m instead of 1.5 m south of its crossing (`track.obj` differs in exactly those 4 vertices).
2. `scripts/geometry/drive_test.py`: `pad_for_lead_in` aligns the measured heights with the gate line when the line is
   exactly 2k longer and its vertex k sits on the local line's first point (either x sign, for a mirrored frame). A
   loop, or any equal-length line, is compared as before. Logged in `fleet/GATES-CHANGELOG.md`.

`tracks/rally-dragon-tail-gravel` 0.2.0 -> 0.2.1 (and its tarmac twin, which the twin test keeps in step); no config
key changed.

## Proof (Mac, engine draft on run 1's data, no `loop.blend`)

| Dragon Tail (Gravel) | PC run 1 (0.2.0) | Mac baseline | Mac after (0.2.1) |
|---|---|---|---|
| verdict | FAIL | FAIL | **PASS** |
| floating furniture | 2 | 2 | **0** |
| severe steps (/km) | 182 (7.21) | 182 (7.21) | 182 (7.21) |
| bumps /km (limit 150) | 27.87 | 27.91 | 27.91 |
| kinks /km | 60.18 | 60.18 | 60.18 |
| fold / vertex bumps (reported) | 6 / 1,141 | 6 / 1,140 | 6 / 1,140 |
| ground on top / daylight / obstructed / undrivable | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| excursion drops / far ledges | 0 / 125 | 0 / 124 | 0 / 124 |
| replication (median / p95 / max) | 0.96 / 3.41 / 9.66 | 0.96 / 3.41 / 9.66 | **0.02 / 0.21 / 7.16** |
| audit_mesh | CLEAN | - | CLEAN |

Engine controls, run 1's engine vs this branch on the committed draft data: Milford (constructed corridor, 127 stone
lips) `track.obj` byte-identical (md5 `4789ac2092c4cb77d33b7abb1395006a`), drive_test PASS both; Under the Dragon
(Gravel) (3,516 lips) `track.obj` byte-identical (md5 `469d2492fd838b70cd9728e4afa98fd2`), its drive_test changes only
in the replication read (below).

Test: `tests/geometry/test_lip_feet_and_stage_replication.py` (stdlib only, 9 tests): a lip on level ground or on its
own 18 % grade keeps full length; a foot over ground falling along the edge is pulled back to where it stands; the
outboard corner counts; no surface is floating; the gap reads drive_test's window; the replication padding for a
lead-in, reversed, mirrored, and its no-op cases.

## Under the Dragon (Gravel)

**Not the same cause.** PC chain run 1 (`origin/claude/under-the-dragon-gravel-run1`, 932af52): drive_test FAIL on
**ground on top mid-lane 5**, floating furniture 0; severe 222 (8.64 /km, under 12), bumps 12.92 /km, kinks 44.35 /km,
vertex bumps 1,008, replication 0.91 / 2.93 / 5.46. The Mac draft on the committed data gives exactly those numbers.

Mac A/B (`build_mesh` + `drive_test`, no `loop.blend`):

| Under the Dragon (Gravel) | run 1 engine | this branch | this branch + `fold_pads` off (PR 25 switch, scratch config) |
|---|---|---|---|
| verdict | FAIL | FAIL | FAIL |
| ground on top mid-lane | 5 (2,536 m; 25,705-25,706 m x4) | 5 | 4 (25,705-25,706 m) |
| floating furniture | 0 | 0 | 0 |
| severe steps | 222 | 222 | 197 |
| bumps / kinks /km | 12.92 / 44.35 | 12.92 / 44.35 | 12.29 / 43.45 |
| replication | 0.91 / 2.93 / 5.46 | **0.01 / 0.12 / 3.39** | 0.01 / 0.12 / 3.39 |
| `track.obj` | `469d24...` | identical | - |

- This entry's lip fix does nothing there (no lip floated; `track.obj` byte-identical). The replication fix applies
  as on Dragon Tail: the 0.91 m median is the same 10-vertex lead-in misalignment.
- The fold pad at 2,506 m (`discs at 1/3`) is one ground-on-top hit (2,536 m, offset 3.76, `1GRASS_f`) and 35 of the
  222 severe steps (rims 2,475-2,481 and 2,528-2,537 m; 35 of 36 stay > 6 cm on own travel). Pads off removes both
  (severe 222 -> 197). That is ledger 0074's switch (PR 25), made the default in PR 29; not merged or set here.
- The other four ground-on-top hits are at the very end of the lead-out, 25,705-25,706 m of 25,706.1, ~15 m past
  AC_TIME_0: at offset +2.1 to +2.85 the grass end apron rises 2.4 cm over the last pavement row (`1GRASS_az` 10.564
  over `1ROAD_main` 10.540). drive_test's open-end skip only covers stations with no pavement at the centre. Pads off
  leaves these, so Under the Dragon still fails without a further fix (engine end apron, or the gate's end skip);
  owed, not done here. Dragon Tail's ends do not show it.
- Under the Dragon's 804-807 m cluster (33 m past the 771 m apex) is not a plateau rim: all 7 are under 6 cm on own
  travel (vertex hop, R ~28 m at 11 %). Its other clusters (1,176-1,182, 4,293-4,718, 13,636-13,667, 14,435-14,443,
  23,169-23,189 ...) are Dragon Tail's group a: of 170 severe steps on curves, 80 are under 2.5 cm and 64 are 2.5-6 cm
  on own travel.

## Owed

A PC build of Dragon Tail (Gravel) 0.2.1 through the chain (`tools/ship_track.sh rally-dragon-tail-gravel`). It should
show floating furniture 0, replication median ~0.02 m, and every other drive_test number no worse than run 1 (severe 182,
bumps 27.87 /km, excursion drops 0); audit and kn5_ground_check as run 1. Then Kevin's drive, with the hairpins at
6,394 / 6,595 / 7,455 m (group b) and the crests at 20,855 / 21,444 m (group c) the places to feel. Not done here and
owed to the engine: drive_test's severe count applies no own-travel re-measure (group a is 71 of 182), and the grade cap
draws tents where 3DEP reads a bank (group c); both change other tracks' numbers and want their own entries.

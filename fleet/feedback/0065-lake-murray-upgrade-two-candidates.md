---
id: 0065
title: Lake Murray's upgrade, two candidates side by side
status: in-progress — decided 2026-11-03: v4 is Lake Murray (Kevin: "I prefer v4"), v5 parked, V3 keeps 0.19.4; the houses kept by the chain and gated, the house textures wired (0.20.1, textured, owed on the PC)
scope: tracks/san-diego-lake-murray
layer: project
train: -
---

## Symptom (Kevin, 2026-11-01)

> "Let's get Lake Murray started on an upgrade against all the other changes."

> "do both as separate versions"

0.19.2 stays installed and untouched, as do the repo's `loop.blend` and `tools/ship_sd.sh`, until Kevin picks a winner in the seat. 0.19.3 stays built and held.
*(2026-11-03, later: Kevin picked v4 — see "Verdict" at the end.)*
*(2026-11-03: the installed V3 is now 0.19.4, rehearsal 2 over 0.19.2 on Kevin's word — see the last section. The repo's `loop.blend` and `tools/ship_sd.sh` are still untouched.)*

## v4, keep the roads: 0.20.0, installed as `san_diego_lake_murray_v4`, not driven yet

Branch `claude/lm-v4`, worktree `D:/k10-worktrees/lm-v4`, project `D:/k10-scratch/lm_v4`. Road kn5 55f2026c, 107.1 MB against 94.4.

Airoso's prep is not a drop-in for Lake Murray. Against 0.19.3's road kn5 it took 14,356 of 85,741 sidewalk positions (its rule against kerb faces in a carriageway), emptied a race
kerb so the exporter refused the race kn5, and moved the ground and every house and lamp (no T-junction weld, no kept-terrain refine, no house seat). So v4 is the general chain with the
prep the approved roads were built with, from rehearsal 2's blend (ledger 0062). Moving to airoso's prep belongs to v5.

| Gate | 0.19.2 | v4 |
|---|---|---|
| soft top in lane, street / cw / acw | 8 / 8 / 4 | 0 / 0 / 0 |
| audit, each layout | 53 | 0 |
| race drive_test | FAIL | PASS |
| severe steps | 0 / 4 / 6 | 0 / 4 / 6 (not gating at that rate; worst 0.106 m at 11-12 m lateral) |
| street excursion drops, limit 13 | 96 | **96: forced** |

The repairs (`tools/red_repairs.py` names them off the built OBJ, `tools/red_repairs_blend.py` applies them on the prepped scene): 63 sidewalk faces removed at the Del Cerro mouths and near
(112, -1476); 401 ground vertices lowered, at most 0.172 m, at two places on the lap around s 2175 and 2250.

**The bypass.** `--force-install` over the street layout's excursion drops alone, Kevin's word: "Force". Recorded in `fleet/GATES-CHANGELOG.md`. The red is mostly the sidewalk's outer bevel, a
28 % slope that falls 0.14 m per the sweep's 0.5 m sample against the 0.12 m limit; a real one stands at s 2100, -13 m lateral (1.52 m). A gentler bevel (the low edge 0.30 m further out) put
ground over the kerb in 3,465 places (verify_kn5 TERRAIN POKE) and came out.

Owed: Microsoft footprints' ODbL attribution before any release. 7,600 blocks may cost load time or frame rate; only the seat can say.

## v5, redraft the roads: 0.21.0, `claude/lm-v5`, `D:/k10-scratch/lm_v5`, not built past the draft

The underlay only empties `GEN_*`, and Lake Murray's blend has none, so a redraft has to remove the v021 layers itself. The engine's OSM stitch does not reproduce the track: 22.5 km against
13.5, another origin, 690 of 4,499 authored points with no draft line within 150 m. From the authored loop as `source.type: from_track` with the origin pinned: 13,484 m, plan offset median
2.57 / p95 4.89 / max 5.93 m, height median 0.12 / p95 1.1 / max 8.65 m. Everything keyed to the current line must move with it.

The bare mainline's first gates are red, as expected with none of the authoring: severe steps up to 0.43 m around s 2254, ground on top around s 1782-1904, a 3.64 m gated drop at s 2102, audit 6 (walls on the road).

Estimate: 3-5 days of runs, because the authoring tools expect the v021 ribbon.

## 2026-11-03: 0.19.2 replaced by the buildings rehearsal, installed as 0.19.4

> Kevin, asked whether rehearsal 2 (ledger 0062) should go side by side or over 0.19.2, knowing its buildings already ride in
> v4 and that this section's opening kept 0.19.2 as the baseline: "Over 0.19.2".

What is installed in `san_diego_lake_murray_v3` now: the scratch build `D:/k10-scratch/lm_bespoke/build/san_diego_lake_murray`
from 2026-11-01 08:32, i.e. 0.19.2's chain with `SD_BESPOKE=1` — the assembler's HOUSE / BUILDING boxes replaced by the
pipeline's 7,600 blocks, nothing else changed. Every installed file is byte-identical to that build except the three
`ui/<id>/ui_track.json`, which carry the chain's own names ("K10 - San Diego (V3) — <layout>") and version **0.19.4** (0.19.3 is
the held yellow-line build; 0.19.4 does not carry it). Road kn5 md5 05de4201…, 110.1 MB. The chain's install step was replayed
by hand (a `SHIP_PROJ` scratch build never installs itself): acs.exe not running, 0.19.2 parked in
`D:/k10-track-archive/2026-11-03_113243/san_diego_lake_murray_v3` (kn5 b170d319…), the build copied in, the ui names written.

Its gates, all on the built kn5 (ledger 0062 has the detail): every `drive_test` key of every layout identical to 0.19.2's
committed files, floating furniture 0; `audit_mesh` red as 0.19.2 (skirt-off-terrain 1,564 → 1,563); `kn5_ground_check`,
`no_route`, `house_seat` (6,239 judged), `rib_check` PASS (its counts within a few of 0.19.2's: nyquist > 0.5 m beyond 20 m of a
pavement 5,071 → 5,096). Installed red on the inherited keys under the chain's `--force-install` rule, no key worse than the
reference: recorded in `fleet/GATES-CHANGELOG.md`.

Not from the repo: the installed V3 was built from the scratch project, whose source (its `loop.blend`, `track.config.json`,
`data/*.json`, `ai/`, the planned `buildings.json`) is copied to `D:/k10-track-archive/2026-11-03_113243/lm_0.19.4_source/`. The
repo's `loop.blend` and `tools/ship_sd.sh` still build 0.19.2 / 0.19.3: a plain `tools/ship_sd.sh` run would put the
assembler's boxes back. v4 and v5 now compare against an installed V3 that has the buildings; 0.19.2's own gate files are still
the repo's `data/`, and its `drive_test` numbers are 0.19.4's.

Not driven. Owed before any release: the ODbL credit for Microsoft's footprints.

## Verdict (Kevin, 2026-11-03): v4 is Lake Murray

> "Lake Murray is very, very good. Keep going with that workflow."

> Asked which install: "V4"; "I prefer v4".

> "Lake Murray v4 should be what we build the rest from, it's an entirely different engine?" — "It's not hand authored"

> To the PC: "Lake Murray v4 had many more houses I[n] it this time, don't lose those"

> On the house textures: "Add textures, and restart"

- **The winner is v4** (0.20.0, `san_diego_lake_murray_v4`). Its geometry is generated by Lake Murray's own engine: the
  assembler `tracks/san-diego-lake-murray/scripts-v021` run under V021_SHIM, prepped and exported by engine-july, through the
  general chain `tools/ship_track.sh` with this track's `ship.json`. Not hand-authored. It is the line every later phase builds on
  (Phase 2, the Mission Gorge Speedway, starts from it: ledger 0054).
- **v5 is parked.** Kevin found the airoso-engine redraft "messy". `claude/lm-v5` and `D:/k10-scratch/lm_v5` stay as they are.
- **The V3 folder keeps 0.19.4** as installed (`san_diego_lake_murray_v3`, the buildings rehearsal over 0.19.2). Nothing reinstalls it.
- **Branch.** `claude/lm-v4-line` = `claude/lm-v4` (43f330f) + origin/main + this verdict. The repo's `loop.blend` on it is v4's (LFS, md5 3d840db1…); `tools/ship_sd.sh` is untouched and stays the 0.19.x chain. The merge changed no Lake Murray file
  and nothing Lake Murray's chain runs: its prep / exporter / spawn are engine-july's (main's #33 corridor carve and #29 fold-pad default
  live in airoso's `scripts/`, which LM's chain does not import: the assembler resolves `scripts` to scripts-v021). Two airoso
  tools it does run changed on main: `tools/race_furniture.py` (#19's fold in-leg search) plans v4's 37 race plans byte for byte as
  before (same md5 over every ring and station, the same five declared edge corners), and `tools/author_bespoke_blend.py`
  (ledger 0063's 1 m rim walk) now takes a per-group `rim_step_m`; Lake Murray declares v4's 2.0 m.

### The houses, kept (Part 0)

The 7,600 blocks were stood by a step only `tools/ship_sd.sh` ran (`SD_BESPOKE=1`); v4's `ship.json` had none, so a full
`ship_track.sh` redraft would have rebuilt `loop.blend` with the assembler's old boxes, and nothing would have said so.

- **The step.** ship.json draft `bespoke` (`tools/ship_track.sh draft_bespoke`), after `stubs_author` and before `gap_mouths`:
  where the rehearsal stood them. `scenery.bespoke`'s `_doc` says who reads it now. `--skip-blend` keeps the blend's blocks.
- **Proof (Mac, Blender 5.1.2).** On a scratch copy of v4's `loop.blend` (md5 3d840db1…) the step stands 7,600 of the plan's
  30,240 footprints (21,452 past 450 m of the lap, 1,188 refused: the numbers ledger 0062 recorded for rehearsal 2), and every
  one of the 23 `AUTH_bespoke` batches comes out identical to the one v4 shipped, vertex positions to the millimetre and faces
  (`source/bespoke/v4_blocks_proof.json`). The block ids are `data/bespoke.report.json`. At main's 1 m rim walk the same run
  stands 7,601, a different set.
- **The gate.** `houses` (`tools/house_gate.py`), after `house_seat`, hard: connected shells on the built road kn5 against
  `scenery.bespoke.house_gate` = v4's counts, roofs 7,600, blocks 7,600 (6,239 near + 1,361 far), colliders 275. The same count on
  v4's blend batches gives exactly the PC's numbers off the kn5. `fleet/GATES-CHANGELOG.md` has it as a new gate.
- **The textures.** Route: the chain stages them from airoso's `assets/textures`, not the engine-july snapshot. `track.config.json`
  `texture_overrides` points the ten block rows (BUILDING_STUCCO / TILTUP / METAL, FARBLOCK_TILTUP / METAL, 1WALL_TILTUP,
  ROOFTOP_SHINGLE / WHITE / TAN / DARK) at `assets/textures/<the row's own file>`, and ship.json `sync_in.assets` copies those ten
  tracked files into the workshop at the same path. engine-july's `pbr.load_overrides` resolves that path against the engine's root
  first and the project's copy when the engine lacks it, which it does for all ten; the prep binds them and the exporter stages and
  embeds them. Why this route: the bytes the kn5 embeds are the repo's own tracked files, on any machine and any engine copy
  (`eng_rehearsal`, engine-july, or whatever the engine-mapping work in ledger 0078 lands on), with no hand mirror into a folder git
  cannot see; the snapshot route would have left every build's look depending on a copy step outside the repo. FARBLOCK_STUCCO_0/1
  have no pbr row and stay untextured. The other 16 of the 26 files engine-july's pbr rows name and lacks belong to rows Lake Murray
  does not use (tents, cones, scrub and tree cards, rails, K-rail, Tec-Pro, dry stone, siding, the pad apron, the ghost wall).
- **Records that lived only in the workshop** (the PC's coverage trace): `red_repairs.plan.json`, `terrain.tiers.json.gz`,
  `terrain.refine.json.gz` now sync both ways, with `bridges.cache.json` (the prep's bridge spans read it; it was in the repo
  but never synced in) and the draft's caches (`network.cache.json`, `road_lanes.cache.json`, `osm.expansion.json`,
  `expansion.north.samples.json.gz`).

### PC check: textured 0.20.1, then a 0.21-line redraft

0.20.1 (the PC builds it): `--skip-blend` from `lm_v4`, textured, the house gate PASS, every other gate as 0.20.0.

Before any run that syncs in, compare the workshop's copies with the repo's: for each of `data/red_repairs.plan.json`,
`data/terrain.tiers.json.gz`, `data/terrain.refine.json.gz`, `data/bridges.cache.json`, `data/network.cache.json`,
`data/road_lanes.cache.json`, `data/osm.expansion.json`, `data/expansion.north.samples.json.gz`, `md5sum` both. A file the repo
lacks or holds with other bytes is pushed from the workshop first (as `claude/lm-v4-0.20.1` does for the first three); the sync-in
would otherwise overwrite the workshop's.

The redraft (the check any 0.21-line build must pass first), in a scratch workshop, `lm_v4` never touched:

```bash
git -C D:/k10-worktrees/lm-v4-line lfs pull
AIROSO=D:/k10-worktrees/lm-v4-line ENG=D:/k10-scratch/eng_rehearsal SHIP_PROJ=D:/k10-scratch/lm_v4_redraft \
  bash tools/ship_track.sh san-diego-lake-murray --no-install        # no --skip-blend: the whole draft runs
```

Pass when:
- `[bespoke] source/bespoke/buildings.json: 7600 buildings stood, 22640 dropped (21452 of them past 450 m of the lap)`, and the
  house gate reads roofs 7,600 / blocks 7,600 / colliders 275 PASS (`data/house_gate.json`);
- every hard gate passes and every forced key is no worse than 0.20.0's committed files (street excursion drops 96 under
  Kevin's "Force"; soft top 0 / 0 / 0; audit 0; race drive_test + no_route PASS; kn5_ground_check, house_seat, rib_check PASS);
- the textures: `build/texture/` holds the ten house files, md5 equal to airoso's `assets/textures/*`; the road kn5's materials
  BUILDING_STUCCO_*, ROOFTOP_*, *_TILTUP_*, *_METAL_* carry `txDiffuse` (and `txNormal` on the walls), FARBLOCK_STUCCO_* none;
- the kn5s against 0.20.1's: `python tools/kn5_equiv.py <0.20.1 kn5> <redraft kn5>` (tangent floats within 1e-6 are equal;
  Blender's tangent pass is not bit-stable) for the spawn kn5s, which a redraft should not move at all; for the road, race,
  street and closure kn5s equivalence is not expected, and the differences are listed instead.

Expected differences on a redraft (each listed in the run's report, none a gate change):
- the blocks are stood on the redraft's own ground at the draft point, not on v4's finished blend: the same ids are expected (the
  plan, the walk and the ground rule are the same), heights may differ by what the later draft steps would have moved;
- the 3DEP / OSM caches are the repo's, so any workshop cache that was newer than the repo's shows up here (the md5 check above);
- v4's red repairs were named off 0.20.0's built OBJ (`tools/red_repairs.py`): on a redraft the plan may name faces that moved, so
  `red_repairs_blend` reports what it could not find; a red that returns is listed, not forced;
- the race furniture and AI lines are re-authored every ship anyway (the same plans: see above);
- Track OBJ and gate JSON comparisons stay exact where the geometry did not move.

### PC, 2026-11-03: v4 rebuilt from the repo, and 0.20.1 installed (textured houses)

**The coverage trace.** v4's chain was run from the prep on a copy of `lm_v4` (`eng_rehearsal`, a fresh worktree at 43f330f),
with a Python audit hook in every Blender process and every system-Python step. Every engine-july file it loaded was in the
snapshot:
- 18 code files in MANIFEST.md5;
- 17 textures in REFERENCED.md5, md5-equal and byte-identical in airoso's tracked `assets/textures`;
- 3 EXCLUDED `kn52fbx` binaries, zipped with the import add-on and never launched (0 subprocess calls). airoso's `vendor/`
  carries identical copies.

The run read nothing from `D:\k10\engine-july`, `k10-sd-v021`, `lm_v4`, the main checkout, the archive or AC.

`D:/k10-scratch/eng_repro` is that engine from the repo alone: the snapshot's 23 files, plus 50 REFERENCED textures and the 3
binaries, each copied from airoso only where its md5 equals the manifest's. 4 REFERENCED textures differ in airoso
(pine_leaves, poplar_bark, poplar_leaves, street_lamp_new); v4 never opens them.

**Not bit-stable.** The same workshop rebuilt from the prep gives new kn5 md5s. Every differing byte is a vertex tangent, off
by at most 5.7e-7. The test of "the same build" is therefore `tools/kn5_equiv.py` (fleet/GATES-CHANGELOG 2026-11-03).

**The repro.** A workshop seeded only from the branch, `--skip-blend` on `loop.blend` 3d840db1, `ENG=eng_repro`. It parts
at the prep, on three files that lived only in the workshop, in this order:
1. `data/terrain.refine.json.gz`: the prep's kept-cell refinement. Without it, 1GRASS has 714,850 vertices against 817,802.
2. `data/terrain.tiers.json.gz`: the thin step, and rib_check, which crashes without it.
3. `data/red_repairs.plan.json`: the red repairs (63 kerb faces, 401 ground vertices).

Reseeded with exactly those three (md5 below), every kn5 is kn5_equiv-equivalent to v4's (the spawns byte-identical), and
every gate JSON is equal. The only exceptions:
- the trees, because the TreeFX models were absent;
- race_authored's bridge seating 328 -> 324, from the branch's stale `data/bridge.spans.auto.json`.

**What a repo-only v4 needs** (all on `claude/lm-v4-0.20.1`, all in ship.json's sync lists):

| file | bytes | md5 |
|---|---|---|
| `data/terrain.refine.json.gz` | 772,742 | 4ae505bcf9497c4f01614d0638d14411 |
| `data/terrain.tiers.json.gz` | 4,584,424 | 92a3a4a93973473d65b86a0b7666f9b8 |
| `data/red_repairs.plan.json` | 2,414 | 91c26b9ec5f6d62b806785335bf5742e |
| `data/bridge.spans.auto.json` (v4's; the repo's was a span stale) | 56 | 2c9d72977d0a275ab4bfb2ffd3086ec5 |
| `data/scatter_positions.json` (palms 890, trees 408, scrub 983, median planting 1,102: without it TreeFX plants 17,728 of 21,111) | 251,317 | 6c9ff7acd3aa05ce716caea86d580390 |

The TreeFX models are deliberately outside git: `source/trees/*.bin`, 16 files, personal use, never published. A second copy
is at `D:/k10-track-archive/treefx-lake-murray-2026-11-03/`, with `MANIFEST.md5` (md5 of the manifest
1721fe6444f8b6a740b2993512c3b431) and a do-not-publish README. Both copies are on this PC's D: drive only.

**0.20.1** (Kevin, 2026-11-03: "Add textures"):
- Base: `claude/lm-v4-line` 123a8b3, with the house textures through `sync_in.assets` and `texture_overrides`.
- `ENG=eng_repro`, `--skip-blend` on 3d840db1, the workshop seeded from this branch plus the archived TreeFX models.
- One clean run from a fresh workshop: `D:/k10-scratch/lm_v4_0201`.

The road kn5 by kn5_equiv: *"textures only: added [metal_wall_diffuse.jpg, metal_wall_normal.jpg, roof_dark_diffuse.jpg,
roof_tan_diffuse.jpg, roof_white_diffuse.jpg, shingle_roof_diffuse.jpg, stucco_wall_diffuse.jpg, stucco_wall_normal.jpg,
tiltup_wall_diffuse.jpg, tiltup_wall_normal.jpg], removed [], changed []; materials and geometry equivalent"*. 128 materials,
the same slots; 17 -> 27 embedded textures. ROOFTOP_SHINGLE_0 has 27,728 -> 27,729 vertices: one corner the exporter left
unmerged because its tangent is 6e-8 apart. Every triangle corner's position, normal and UV is identical and in order.

The rest of the proof:
- `_race`, `_street` and the closures are kn5_equiv-equivalent; the three spawns are byte-identical.
- The house gate: roofs 7,600 / blocks 7,600 / colliders 275, PASS.
- Every gate JSON equals 0.20.0's: drive_test x3, audit x3, kn5_ground x3, house_seat, no_route x2, verify_mouths / pads /
  stubs / fold_fans, rib_check, race_verify.scenery. Street excursion drops are 96 (Kevin's 0.20.0 "Force", the same count),
  far ledges 107, severe 0.
- One author-time count differs: race_verify.json's scenery reads 21,171 trees against 21,111. In a fresh workshop no gate
  OBJ exists when the author phase runs, so its tree plan skips the built-surface guard: rock 10, walk 2 and building 48 =
  the 60.
- The shipped trees.txt, the AI lines and every other track-folder file are byte-identical to 0.20.0's; only the kn5s and the
  version strings differ.
- `loop.blend` stays 3d840db1, the input. The author phase re-saves it (0dbbe67a) with no change that reaches a kn5.

**Installed** over `san_diego_lake_murray_v4`; 0.20.0 is parked in `D:/k10-track-archive/2026-11-03_214339/`. ship.json's
workshop is `lm_v4`, kept untouched, so `tools/ship_track.sh`'s install block was replayed by hand, as for 0.19.4: refuse
while acs.exe runs, park, copy, the ui_name_prefix names.

The installed road kn5 is 0a0b2342454e, 107,371,925 B (+236 KB). The clean run's kn5s are kn5_equiv-equivalent to the
installed ones.

Stills are in `tracks/san-diego-lake-murray/source/stills/houses_{0200_before,0201_after}_{1,2,3}.jpg`: Blender workbench
renders of the shipped road scene, with the same three cameras for 0.20.0 and 0.20.1. Before, the houses are grey shells;
after, stucco walls with windows, shingle / white / tan roofs, tilt-up panels and ribbed metal. They are not in-game shots.
Not driven yet.


## v5-bare: 0.21.0 installed 2026-11-03 as `san_diego_lake_murray_v5`, the street layout alone, forced on one gate (not driven yet)

Kevin: "Continue v5 now", then "Yes, v5-bare early", then "yes" to forcing the 18. Branch `claude/lm-v5`, project `D:/k10-scratch/lm_v5`. Road kn5
645002e6151a7f648a9d4bc551f9c582. No sidewalks, no bridge rails, no buildings, no race layouts: the engine's road and ground on the approved line.

What it took (each kept, each opt-in so no other track moves):
- **The line and heights are the approved ones.** `source.type: from_track` on the authored loop, `smooth_window` 0, the origin pinned; the fixes carry
  `ele` and `tools/profile_from_fixes.py` (draft step `profile`) puts the approved profile on the projected line, decks held, Kevin's College hump
  kept. My first conversion used a spherical Earth and put the line 4.4 m off; the engine projects on the ellipsoid.
- **The levelled fold pinch in the engine** (`ribbon.fold_level_deltas`, `route.fold_treatment: "pinch"`): ledger 0050's rule. At the four
  junction corners a 24-30 m road turns on 8-10 m; the engine's plateau and flat disc would have flattened the College hump (ledger 0057) and
  left a 0.33 m rim. Severe steps 18 -> 0, kinks 10.99 -> 2.52 /km.
- **`scenery.warning_barriers` / `fences` / `parapets: false`**: a real street's barriers are the ones it has, authored later.
- **The corridor splice read the wrong side of the road** (ledger 0067): 110 double-sheet cells -> 0.
- **The sidewalk edge's contact pass** read the sidewalk's 6-point rows with the shoulder's 4-point stride (fixed). The engine's sidewalk still
  stands up to 1.7 m over Lake Murray's falling yards (281 excursion drops), so v5-bare runs the shoulder edge; sidewalks come as authoring.

| street gate | 0.19.2 | v5-bare |
|---|---|---|
| soft top in lane | 8 | 0 |
| severe steps | 0 | 0 |
| kinks /km | 2.67 | 2.52 |
| fold bumps | 20 | 18 |
| excursion drops, limit 13 | 96 | **18: forced** |
| audit | 53 | CLEAN |
| kn5_ground_check | PASS | PASS |

Owed before v5 can be judged against v4: sidewalks, bridge rails, the race layouts on the new line, buildings, trees, lamps, signs.

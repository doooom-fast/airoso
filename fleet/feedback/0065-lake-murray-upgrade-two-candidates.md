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

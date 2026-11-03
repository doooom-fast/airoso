---
id: 0065
title: Lake Murray's upgrade, two candidates side by side
status: in-progress
scope: tracks/san-diego-lake-murray
layer: project
train: -
---

## Symptom (Kevin, 2026-11-01)

> "Let's get Lake Murray started on an upgrade against all the other changes."

> "do both as separate versions"

0.19.2 stays installed and untouched, as do the repo's `loop.blend` and `tools/ship_sd.sh`, until Kevin picks a winner in the seat. 0.19.3 stays built and held.
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

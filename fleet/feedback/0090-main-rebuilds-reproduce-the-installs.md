---
id: 0090
title: Main rebuilds the installed tracks. Two ship_track.sh faults found on the way (Pikes Peak's bare laps stopped the chain; on the PC Milford and High Plains skipped the rail re-seat with every gate green)
status: diagnosed
scope: tools/ship_track.sh (every ship_track track); proven on Lake Murray 0.20.2, Sand Creek 0.2.8, Milford 0.1.11, Pikes Peak 0.2.0
layer: tools
train: -
---

## Symptom

None from the driver's seat. The Mac asked the PC to prove that main (ca297e2, after the 2026-11-10 integration)
rebuilds what is installed: each track from an EMPTY workshop, compared against its installed build with kn5_equiv on
every kn5, the AI lines and every gate JSON. Its rule: "If anything differs beyond tangent noise, stop and send me the
row and file."

## Evidence

Each rebuild ran `tools/ship_track.sh <track> --no-install` with SHIP_PROJ an empty scratch workshop. Lake Murray is the
exception (below). The comparisons on the PC are in `D:/k10-scratch/proof_*.vs_*.txt`, made by the session's
cmp_proof.sh / cmp_folder.sh. "Equivalent" means `tools/kn5_equiv.py`: tangents within 1e-6 and every other byte
identical.

| Track (installed) | From | Result |
|---|---|---|
| Lake Murray 0.20.2 | main ca297e2, `--skip-blend` on a copy of `D:/k10-scratch/lm_phase2/project` | 8/8 kn5 equivalent (max 1.79e-7); 71/90 AC files byte-identical, every AI line; gates as 0.20.2's (the street drive_test red on the 96 drops Kevin forced past, its report byte-identical). Ledger 0054 has the detail |
| Sand Creek 0.2.8 | main ca297e2 | SHIP OK as 0.2.8; 3/3 kn5 equivalent (max 2.09e-7; 1GRASS_0 one vertex fewer, the tangent noise merging one more pair); 8/8 AI lines identical; 32/40 AC files byte-identical |
| Milford 0.1.11 | main ca297e2 | **the rail re-seat did not run** (fault 2): 14 rails / tyre walls / screens left on the author ground, GUARDRAIL_W_0 up to 1.48 m under the prepped ground; audit walls 43,761 v vs 43,907 v; kn5 DIFFERENT from 1WALL_GHOST_RAIL_0. Every gate still green |
| Milford 0.1.11 | `claude/main-proof-fixes` | SHIP OK; `[reseat] 14 objects moved`; kn5 equivalent (max 1.79e-7); AI lines identical; reseat_bespoke.json and audit.json byte-identical; 13/16 AC files byte-identical |
| Pikes Peak 0.2.0 | main ca297e2 | **EXIT 1** (fault 1): "split wrote no loop_race_inf.blend — lap inf would load no curb strip" |
| Pikes Peak 0.2.0 | `claude/main-proof-fixes` | kn5 equivalent (max 1.79e-7; two grass vertices fewer, the same merge); 12/12 AI lines identical; the gate rows identical (213/213) but the last. 0.2.0 was installed forced past the infield hairpin's undrivable corner; this run stops at NOT INSTALLED, as an unforced run must. 36/44 files byte-identical to the 0.2.0 install that 0.2.1 parked (D:/k10-track-archive/2026-11-10_141829) |

What differs on every track, none of it the build:
- the install-set ui_track.json names and the menu pictures;
- LICENSES.md, where main's asset table also names tyre_wall_diffuse.png (Milford's; the kn5s' embedded textures
  are identical);
- in the gate JSONs, paths, run seconds and timestamps, and main's newer empty fields (house_seat_check set_in,
  verify_pads grass_at_xz, road_wear_check's photo-mode tolerances);
- the two rows of the TreeFX gate (0089) where a track has trees, and no_route's per-object deck rows on Lake Murray.

## Diagnosis

**Fault 1: the lap steps asked for laps split never builds** (`tools/ship_track.sh:1213`, from c4094785, the Phase 2
port of ship_sd's laps).
- LAP_IDS was `race_lap.lap_ids`: every lap any layout names.
- `tools/split_exports_blend.py:198-202` writes a lap's common blend only for the laps a FURNISHED race layout names
  (ledger 0085: a lap only bare layouts drive is the road's own lanes, with no curb strip).
- Pikes Peak's road course (rc) and infield (inf) are bare laps, so the split check at :661-663 failed on them.
- Lake Murray's lap is furnished, so its run never showed it. 0.2.0 was built before the check existed.

**Fault 2: the re-seat's on/off test never matched on the PC** (`tools/ship_track.sh:636`).
- a79b6a68 (High Plains 0.1.7, the PC) rewrote the block through an edit script, and a `'\r'` in that script became
  a raw CR byte inside `tr -d '...'`. On the PC's checkout that still deleted the CR, so High Plains 0.1.7 built
  right.
- The merge into main turned the lone CR into a line break: `tr -d '<LF>'`.
- The PC's python prints `True<CR>`, so `[ "True<CR>" = "True" ]` is false and the step is skipped. On the Mac,
  python prints no CR and it runs.
- No gate notices: audit and drive_test pass a rail standing buried in the ground.
- The edit-script trap is the agent's Bash tool: it takes one level of backslashes out of a heredoc. Code holding escapes is
  written with the Write tool, or builds them with chr().

## Fix

On `claude/main-proof-fixes`, two commits on ca297e2:
- **83a68b44**: new `race_lap.furnished_lap_ids`, which LAP_IDS now comes from. Lake Murray's set is unchanged
  (['north']); Pikes Peak's is [], 0.2.0's step set.
  - test: `test_only_a_furnished_laps_layouts_give_it_a_common_set`.
- **707e3e1f**: `tr -d '\r'` spelled as an escape again.
  - test: `test_every_tr_strips_the_windows_cr_spelled_as_an_escape`, which reads ship_track.sh as bytes and fails
    on ca297e2.
- GATES-CHANGELOG 2026-11-10 records the wiring.

## Open

- **Lake Murray from an empty workshop.** The committed `tracks/san-diego-lake-murray/loop.blend` (sha256 3f13b887…)
  is the 0.20.2 workshop's byte for byte. But ship.json lists it, and the author-stage data, under sync_out only, so
  an empty workshop has no blend for `--skip-blend`. Until sync_in carries them, Lake Murray rebuilds only on a copy
  of lm_phase2/project (ledger 0054).
- **High Plains** was not in this proof. Built from ca297e2 on the PC it would skip its pit-wall K-rail re-seat
  (fault 2). A rebuild from the fix branch matched against 0.1.7 would prove it.
- **No gate measures rail seating.** The checks that found buried rails were measurements outside the chain:
  - ledger 0082 pass 3, Milford's;
  - the 2026-11-10 wall sweep against the declared heights.

  Making one a gate is a separate decision.

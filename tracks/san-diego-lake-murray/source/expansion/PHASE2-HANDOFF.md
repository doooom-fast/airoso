# Mission Gorge Speedway — Phase 2 handoff (2026-10-27)

Kevin: **"north drives incredible"**, then **"tally ho?"**. Preserve the north-road driving feel.
The separate College / College–Navajo realism+ work remains open in ledger 0055.

## Implemented, not enabled

`race.north.held.json` beside this file is a **held reference-line declaration**, not an overlay to
apply blindly to track.config.json. It selects the ~8.72 km north-loop candidate from the approved
Phase 2 scope; the 17.43 km grand-loop alternative is not implemented. Neither new layout is active.

The existing second-lap engine stitches its five source spans without altering the source points:

| Road | Source span | Lap vertices |
|---|---|---|
| Waring | north_J1_waring#0 0→317 | 0–317 |
| Princess View | north_princess_view 0→355 | 327–682 |
| Mission Gorge | north_mission_gorge 0→745 | 698–1443 |
| Jackson southbound | north_J5_jackson_north#0 651→0 | 1458–2109 |
| Navajo westbound | MAINLINE 2317→1517, reverse | 2113–2913 |

Measured against current v0.19.1 intermediates: **8,725.4 m, 2,918 unique vertices**. The remaining
vertices are straight interpolated joins: J2 27.992 m, J3 46.039 m, J4 41.995 m, J5 11.614 m,
J1 14.600 m. Those joins are accounting lines, **not proof of drivable corner geometry** and not AI.

### First defect repaired

The lap tool previously omitted all pad-owned stub arms. `junction_pads: [J2, J3, J4]` now requires
those pads to connect consecutive source-piece endpoints and adds each unused arm's world-space
probe to the existing forbidden-probe path. Total: **34 mouths** (26 ordinary side streets,
6 pad arms, 2 abandoned mainline branches). Missing, duplicated or disconnected declared pads fail.

| Pad arm | Road | Probe XZ (engine metres) |
|---|---|---|
| J2:S1 | Mound Avenue | −2723.198, 965.310 |
| J2:S2 | Waring southwest — future Zion connection | −2765.207, 969.103 |
| J3:S3 | Mission Gorge west — future Zion connection | −3063.121, 2020.674 |
| J3:S4 | Quarry drive | −3041.091, 2073.459 |
| J4:S5 | Mission Gorge east | −1167.662, 3199.999 |
| J4:S6 | MTRP visitor-centre entrance | −1221.486, 3222.699 |

Probes stand 10 m into each stub, before its end barrier; forward and reverse use identical world
points. This inventory does not prove containment. Existing Free Roam end barriers must not be the
only things sealing the future Speedway when Phase 3 opens the western connections.

## Verification and replay

No ZIDE.md was present. This Mac's system Python is 3.14; `.venv` was created with Pillow for the
existing map/track-folder tests. No new test framework was added.

From the repo root, focused tests (plain functions, as in `tests/run_tests.py`):

```sh
.venv/bin/python - <<'PY'
from tests.tools import test_race_lap, test_race_lap_pads
count = 0
for module in (test_race_lap, test_race_lap_pads):
    for name in sorted(n for n in dir(module) if n.startswith('test_')):
        getattr(module, name)()
        count += 1
print(f'{count} passed')
PY
```

**21 passed, 0 failed**. Covers synthetic forward/reverse and seam topology, refusal cases,
unchanged non-pad output, six real pad arms, and propagation of explicit XZ to forbidden probes.
Log: `build/phase2/race-lap-tests.log` (local, ignored).

Full suite: `PATH="$PWD/.venv/bin:$PATH" python tests/run_tests.py` → **966 passed, 6 failed**.
Log: `build/phase2/full-tests-with-path.log` (local, ignored). Failures left visible, not repaired
in this bounded Phase 2 change:

- `test_write_ai_line_payload::test_without_the_ai_block_every_file_is_todays_bytes`: byte differences.
- `test_author_expansion::test_the_committed_intermediate_is_reproduced_offline_byte_for_byte_but_the_stamp`: reproduction assertion.
- `test_engine_july_snapshot::test_snapshot_copies_match_their_manifest_and_stay_small`: snapshot
  `scripts/__init__.py` MD5 differs from its manifest.
- `test_ship_sd_chain::test_argument_guards_exit_2_before_any_file_operation` and
  `test_ship_track_chain::test_argument_guards_exit_2_before_any_file_operation`: backslash-form
  `/Volumes/...` path rejected as non-absolute rather than producing the test's expected message.
- `test_ship_track_chain::test_engine_rule_and_no_blend_yet_on_guard_runs`: shell `${p,,}` bad
  substitution and scratch-path rejection.

These results do not establish a clean full-suite baseline. No full track build was attempted.

## Next bounded build step

1. Judge the reference joins against the **built road**, author the required J1/J5 connections in
   coordination with 0055, and prove J2–J4 race-corner surfaces without degrading Free Roam.
2. Declare lap-local boxes, closure runs, kerbs, grid/pits and sectors for both race directions.
   Do not inherit mainline vertex numbers or College's old crossover chicane.
3. Prove planned **and built** containment at all 34 exits, including the J2/J3 future connections,
   with the lane complete and every spawn reachable. All four artifact gates still apply.
4. Only then enable the two layouts, reproduce the existing layouts' gate matrix, drive, and ship
   with Kevin's approval. No AI spline from this reference line; recording remains an in-game step.

No authored Blender layer, road mesh, live config, installed track, or release was changed here.

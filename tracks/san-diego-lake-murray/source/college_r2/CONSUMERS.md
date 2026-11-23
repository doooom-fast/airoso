# College split: who makes each object, and who reads the lap line

Read on round 1's base (`claude/lm-finish-20261122` at 3b03aead), 2026-11-22. Lake Murray is not redrafted: round 1
seeds the hand-authored `loop.blend` into an empty workshop (`ship.json` `sync_in.seed`) and the chain resumes with
`--skip-blend`. So the split is a new opt-in **author** step on the seeded scene, before the race steps.

## 1. The chain after the seeded blend (`ship.json` `steps`, `tools/ship_track.sh`)

| Phase | Step | Tool |
|---|---|---|
| author | `lamp_heads` | `tools/author_lamp_heads_blend.py` |
| author | `race_bands` | `tools/barrier_bands.py` (declares every race corridor: `data/barrier_bands.json` v2) |
| author | `race_planned_gate` | (the planned no-route fill) |
| author | `layout_dummies` | `tools/layout_dummies.py` |
| author | `race_author` | `tools/author_race_furniture_blend.py` (+ `tools/race_furniture.py`, `tools/race_corridor.py`) |
| author | `signs` | `tools/place_signs.py`, `tools/author_signs_blend.py`, `tools/plot_signs.py`, `tools/verify_signs.py` |
| author | `race_verify` | `tools/verify_race.py`, `tools/plot_race_furniture.py` |
| prep | `prep`, `split` | engine `scripts/ac/build_kn5_loop.py` (renames `ROAD` -> `1ROAD_road`, tiles `TERRAIN`, ...), `tools/split_exports_blend.py` |
| ship | `export_*`, `spawn_kn5`, `ai`, `track_folder`, `make_map`, `treefx`, ... | engine `export_kn5_addon.py`, `scripts/ac/write_ai_line.py`, `scripts/ac/track_folder.py`, `tools/make_map.py`, `tools/make_treefx.py` |
| gate | `verify_mouths`, `verify_stubs`, `verify_pads`, `rib_check`, `house_seat`, `houses`, `drive_test_*`, `audit_street`, `race_gates`, `fold_fans`, `kn5_ground` | `tools/verify_*.py`, `tools/rib_check.py`, `tools/house_*.py`, `scripts/geometry/drive_test.py`, `scripts/geometry/audit_mesh.py`, `tools/no_route.py`, `tools/verify_fold_fans.py`, `scripts/ac/kn5_ground_check.py` |

The draft steps that MADE College's objects (`median_envelope`, `build_loop_blend`, `median`, `weld_mouths`,
`seat_terrain`, `ground_release`, `lamps`, ...) do not run on a seeded blend. `ROAD`, `CURB`, `MARKINGS`, `YLINE`,
`GUARDRAIL`, `TERRAIN`, `LIGHTPOST_*`, `LIGHTS_0` and the `streetonly` median pieces are simply in the blend; the
race walls, closures and kerbs are re-authored every run by `race_author` from `barrier_bands.json`.

## 2. What reads the lap line (counts of references in each tool; "surface" = it samples the built mesh)

| Tool | Lap line (`centerline.local` / `finished` / `gate_centerline`) | `median_bands` / `barrier_bands` / `MedianZone` | Samples the built surface |
|---|---|---|---|
| `scripts/geometry/median_zone.py` | the one place that knows where the dividers are: the island is a half width **about the lap line** per vertex | yes (it is the reader) | no |
| `tools/barrier_bands.py` | yes | 2,123 lines of it: zones, closures "along each island's race-side curb", lanes `[y_lo, y_hi]` per vertex | no |
| `tools/race_furniture.py` | 3 | 34 | no: rings carry `y_hint = line y + lift` |
| `tools/author_race_furniture_blend.py` | - | 9 | yes: BVH ray from the hint height, `RAY_LEN_M` long |
| `tools/layout_dummies.py` | 5 | 2 | no |
| `tools/place_signs.py` | 8 | 5 | no |
| `tools/verify_race.py` | 5 | 16 | yes |
| `tools/no_route.py` | 4 | 16 | no (floods the gate OBJ) |
| `scripts/ac/write_ai_line.py` | 15 | 26 (drafts each layout's line inside `lane_by_vertex`) | yes |
| `scripts/geometry/drive_test.py` | 15 | 12 | walks the line; `_dense_step(top_at, xz3, y_ref)` picks the sheet near a reference height |
| `scripts/geometry/audit_mesh.py` | 2 | 7 | no |
| `scripts/ac/kn5_ground_check.py` | 7 | - | yes |
| `tools/verify_fold_fans.py` | 7 | 11 | yes |
| `tools/verify_mouths.py` | 9 | 4 | no |
| `tools/verify_pads.py`, `tools/verify_stubs.py` | 5 each | - | no |
| `tools/make_treefx.py`, `tools/make_map.py`, `scripts/ac/track_folder.py` | 3 / 6 / 4 | - | no |
| engine `scripts/ac/build_kn5_loop.py` (prep) | 14 | - | yes |
| `tools/split_exports_blend.py` | - | 4 | no |
| `tools/rib_check.py`, `tools/house_seat_check.py`, `tools/house_gate.py`, `tools/author_lamp_heads_blend.py` | - | - | no |

**The assumption under all of it:** one road, one height per lap-line vertex. The island is a strip about the line
(`island_half_at(i)`), the race lane is a pair of laterals from the line, furniture and gates start from the line's
height. A northbound carriageway 6 m above the line breaks that for every row with a number in the first two columns.

## 3. Two ways to build the split

- **A. Keep the lap line where it is** (it ends up in the planted bank) and teach the consumers that the road has a
  height per side. That is a change inside `median_zone`, `barrier_bands`, `race_furniture`, `drive_test`,
  `write_ai_line`, `verify_race`, `no_route`, `kn5_ground_check` and the prep: most of the gates, each with a
  GATES-CHANGELOG entry.
- **B. Two roads, each with its own line.** The mainline is re-registered onto the **southbound** carriageway through
  the split (its line moves up to about 9.5 m west and its width comes down to that carriageway's 10 m; no island in
  `median_bands` there), and the **northbound** carriageway becomes its own named road piece with its own line,
  widths and heights, joined to the mainline at both ends. The engine already has this shape: `race.laps`
  (`scripts/geometry/race_lap.py`, ledger 0054 phase 2) stitches a lap from MAINLINE plus named connectors, with
  declared joins; Mission Gorge Speedway is built that way. Speedway (clockwise) becomes a stitched lap that takes
  the northbound piece; Speedway Reverse stays on the mainline. Every consumer keeps "one road, one height per
  vertex"; the bank between the roads is plain ground.

  What B costs: the author step moves the mainline's vertices v1130-1480 and rewrites the data that mirrors them
  (`centerline.local.json`, `finished_centerline.json`, `gate_centerline.json`, widths, `median_bands.json`,
  `route.median_registration`), and the College mainline corridor, kerbs, chicane (`college_split`) and dummies are
  re-declared on lap vertices. The lap's length and every station after v1130 shift by the changed arc length.

**Recommended: B.** It uses machinery that already drives a shipped layout, and it leaves the gates alone.

## 4. Not read yet

- How a named piece's ribbon, curbs, paint and ground are authored on a seeded blend (the north pieces came from the
  draft's `expansion_decorate`; this piece has to come from the new author step).
- `race_lap.py`'s join rules at a piece's two ends (the northbound piece joins the mainline at a flat taper, not at
  a junction pad).
- What the prep does with a second road sheet beside the mainline (`hold_stacked_blend.py` is in the prep's list).
- Free Roam: the traffic direction data (`write_traffic_json.py`) and the one-way check for the northbound piece.

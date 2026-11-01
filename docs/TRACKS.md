# The tracks — the complete list, and what it takes to install each one

*Written 2026-11-01 (Kevin, 22:20 MDT: "get a complete track list and installed by morning"). One row per track
folder under `tracks/`, nothing left out. "Installed" means on the Windows box under `content/tracks/<install_folder>`,
put there by the chain (`tools/ship_track.sh`, `docs/ONE-CHAIN.md`); the chain installs a build only when its gates are
green, so the morning run installs what goes green and the matrix names the rest. `fleet/DEFINITION-OF-DONE.md` holds
the tier each track can claim; this file holds the list and the command.*

**The morning, on the Windows box** (C:/Users/Owner/Documents/GitHub/airoso, branch `claude/busy-hopper-hldxly` until
PR #12 merges; Blender 4.2 + AC + Content Manager; Overpass and USGS 3DEP reachable):

```bash
git fetch origin && git checkout claude/busy-hopper-hldxly && git pull
bash tools/ship_fleet.sh --list                 # the plan: ONE-CHAIN §4's order, the skips named
bash tools/ship_fleet.sh                        # every chain-ready track: draft-only first, then the full run
bash tools/ship_fleet.sh --include-deprioritised rally-dragon-tail-tarmac rally-under-the-dragon-tarmac   # the tarmac pair, if wanted
```

`tools/ship_fleet.sh` never forces an install (a red build is Kevin's call per track, with the Drive-1 verdict's July
reference where one exists), runs the next track after a red one, and writes `D:/k10-scratch/fleet/fleet-<stamp>.md`
with one row per track: the draft's exit, the full run's exit, installed or not, and why. Read that file first.

## The list

| # | Track (folder) | Slug, install folder | Kind, source | Chain state (2026-11-01) | Installed now | What the morning run reads first / what blocks |
|---|---|---|---|---|---|---|
| 1 | **Nevada Nights** (`exotics-racing-lv`) | `exotics_racing_lvms` | circuit_port, NAIP aerial trace | through the chain 2026-10-29, **T1** (ledger 0060) | **0.2.0**, 2026-10-29 | re-run to the same gates; not driven yet. Its edges are ledger 0061's subject |
| 2 | **Milford Road Course** (`milford-road-course`) | `milford_road_course` | circuit_port, NAIP aerial trace | through the chain, **T1** | **0.2.0** | as above; the banked esses' severe steps 15 at s 795–808 (0060) |
| 3 | **High Plains Raceway** (`high-plains`) | `high_plains` | circuit_port, OSM raceway ways | through the chain, **T1** | **0.68.0** | as above; the north section stays excluded (its config) |
| 4 | **Sand Creek Raceway** (`sand-creek`) | `sand_creek_raceway` | fictional_street_circuit, KML + capture | through the chain, **T1** | **0.28.0** (forward only) | as above; the reverse layout parked until its start is declared |
| 5 | **Lake Murray** (`san-diego-lake-murray`) | `san_diego_lake_murray` (installed as `san_diego_lake_murray_v3`) | street_port, OSM network | its own chain of record, `tools/ship_sd.sh` (ONE-CHAIN §2 row 6: the last migration) | **0.19.1**, driven: **T2** | not in the fleet runner: `bash tools/ship_sd.sh` is its command; the migration onto airoso's engine is ONE-CHAIN §4 row 9, after the four |
| 6 | **Lookout Mountain Lariat** (`lookout-lariat`) | `lookout_lariat` | street_port, OSM + the paint centreline | **chain-ready** (ledger 0048 "Started": the data stages, the Drive-1 gates and verdict, `SHIP_VARIANT` for D4) | July **0.15.0** (engine era; parked by the chain's install) | `data/network`-free: the draft's `[elev] profile by station` line, `road_profile`'s lid and grades, `bridge.spans.auto.json`; then the four reds the stand-in rehearsals predict — the climb's st 5,383 step, the real hairpins against the corner rule (A2, Kevin's call), the shoulder sheet under the road-inventory gate (0061), the stacked legs (P3a). D4 B: `SHIP_VARIANT=b_verge` (the same 3.58 m band on this grid: `drive1_variants` doc) |
| 7 | **Dragon Tail (Gravel)** (`rally-dragon-tail-gravel`) | `rally_co_dragon_tail_gravel` | rally_stage, OSM CR 116, point to point | **chain-ready** 2026-11-01 (name set, frame stated, `stage` layout, constructed corridor); rehearsed offline on the engine-era cached data: 25.26 km, drive_test FAIL (severe 237, bumps 64.5/km under gravel's 150, kinks 85.4/km, excursion drops 0, far ledges 115), audit CLEAN, one 18 m auto span at 9,530 m | engine-era package 0.1.0 (ledger 0014); its tier withdrawn | the gps print and the bridge-span line; then drive_test's severe steps (the engine-era profile read 237). Owed in the ship phase, not fixed: a single-layout track's AI is packed from `<project>/ai/`, the chain writes `ai/stage/` — the folder ships no AI line until reconciled (ship.json `_owed`); no SurfacesFX gravel key yet |
| 8 | **Under the Dragon (Gravel)** (`rally-under-the-dragon-gravel`) | `rally_co_under_the_dragon_gravel` | rally_stage, OSM CR 109, point to point | **chain-ready**; rehearsed offline: 25.71 km, drive_test FAIL (severe 222, bumps 12.9/km, kinks 44.4/km, drops 0, far ledges 99), audit CLEAN | engine-era package 0.1.0 | as row 7; which end the rally starts from is unknown without the event GPX (the config's `_loop_doc`) |
| 9 | Dragon Tail (Tarmac) (`rally-dragon-tail-tarmac`) | `rally_co_dragon_tail_tarmac` | rally_stage, the same road, tarmac physics (L8) | chain-ready, **deprioritised** (Kevin 2026-07-26: "may be cancelled"); rehearsed: drive_test FAIL (severe 237, bumps 64.5/km against tarmac's 75, drops 87) | never packaged | skipped by the runner unless `--include-deprioritised` |
| 10 | Under the Dragon (Tarmac) (`rally-under-the-dragon-tarmac`) | `rally_co_under_the_dragon_tarmac` | rally_stage, the same road, tarmac | chain-ready, **deprioritised** | never packaged | as row 9 |
| 11 | **San Diego Freeway Free Roam** (`san-diego-freeway`) | `san_diego_freeway` | street_port **network**, OSM motorways I-5 / I-8 / CA-52 / CA-163 | **chain-ready** 2026-11-01: the ship phase walks ONE declared real mainline, I 8 eastbound end to end (`network.reference_line`, the draft step `network_reference`); proven on the stand-in (Lake Murray's cached motorway ways): the line resolves from the draft's own edges, drive_test / write_ai_line / make_map / the prep's data half run on it | engine-era **0.5.0** | **the hole, by name:** every edge off the reference line (I 8 westbound, I 5, CA 52, CA 163, every ramp) is built and unjudged by the line gates — `data/network.reference.json` and drive_test list them; a stand-in finding owed to the engine: junction nodes get two heights where edges meet (0.13–0.60 m steps at the mainline joints, `network_elev` smooths each edge open-ended) — expect that class on the real run |
| 12 | **Pueblo Motorsports Park** (`pueblo`) | `pueblo_motorsports_park` | circuit_port, OSM raceway ways | **chain-ready** 2026-11-01 (frame to the chain's, name set, `smooth_window 0` as High Plains); offline: the gps step runs (3.51 km, 1,172 points, ring rotated 952) | engine-era 0.66.3 (its T1 withdrawn, ONE-CHAIN §4) | the bridge-span line (a flat course: any span is the detector reading the wrong ground), then drive_test's excursion drops (0025's mechanism at lateral 9.5–10 m) |
| 13 | **Aspen Motorsports Park** (`aspen`) | `aspen_motorsports_park` | circuit_port, OSM raceway way | **chain-ready**; offline: 1.68 km, 561 points, ring rotated 382 | engine-era 0.66.3 (withdrawn) | the bridge-span line (a mountain site with real relief), then the slope kinks at the old V1 stations 1517–1519 (0025) |
| 14 | **Grand Junction Motor Speedway** (`grand-junction`) | `grand_junction` | circuit_port, OSM raceway way | **chain-ready**; V1 never went green ("rough everywhere, mechanism not found", 0018 / 0031): this run drives the OSM polygon itself (`smooth_window 0`; V1's smoothed line was 5.7 m off it and the lap 22 % short) | engine-era (blocked) | the gps print (1.32 km / 442 points / close_gap 127), no span minted, then drive_test's severe steps against V1's s 460 / 800 / 860 |
| 15 | **Pikes Peak International Raceway** (`pikes-peak`) | `pikes_peak_international_raceway` | circuit_port, OSM raceway way (the oval) | **chain-ready**; the frame flip carries the bank: cambers −10° (L10: 10° in all four turns; one arc per end, T1–T2 and T3–T4), `ribbon_cols` 8 against the ramps' twist (Exotics' lesson) | engine-era (blocked, 0018 / 0031) | on the built deck the raised edge must be the OUTSIDE one in every turn and the AI must read counterclockwise; then drive_test's severe steps against V1's four ramp clusters |
| 16 | IMI Motorsports Complex (`imi`) | — | circuit_port, a hand-traced placeholder off a screenshot | **not chain-ready, on purpose** (left on the V1 frame so the chain refuses it): the 33-point trace cuts across the infield and misses the course, the KML is the same placeholder, the georeference is estimated — L1: fabricated geometry is a defect, not a status (`tracks/imi/track.config.json` `_chain_doc`) | engine-era 0.66.3 (its T1 was earned by the placeholder) | owed before the chain: a NAIP export of the site into `source/`, a trace off it by Exotics' method, control points from the image |
| 17 | Second Creek (`second-creek`) | — | circuit_port, historical, closed in the 2000s | **not chain-ready**: fabricated (registry `fidelity: FABRICATED`; "must not ship as a real port", L1); re-source first (ONE-CHAIN §4 row 7: a georeferenced pre-2008 aerial + two control points, then the aerial trace) | engine-era 0.66.3 (the same placeholder) | nothing to run; the sourcing is the whole task |

Not tracks: Nordschleife and Bathurst are the DEM answer keys under `docs/history/projects/` (calibration, never products).

## What the morning run is expected to do

- **Rows 1–4** re-run green and re-install at the same versions (nothing in the draft changed for them: every engine
  change of 2026-11-01 is opt-in or byte-identical for a uniform 3 m, unrotated-widths, no-`verge_m`, no-network
  track; `widths_from_osm` now orders its widths by the recorded permutation — Sand Creek, the one that runs it, has
  none, so byte-identical there too).
- **Row 6, the Lariat:** the draft's own gates (paint, one-way, roll rate) pass; the built gates read the four reds
  above and the chain refuses the install (`--force-install` is refused by the verdict while floating furniture is
  not 0). Installing it is a decision, not a run: the corner rule at the real hairpins (A2) and the sheet (0061)
  are the two Kevin's word moves.
- **Rows 7–8, the gravel stages:** the real-3DEP draft replaces the engine-era cached data the rehearsal used; the
  stage's severe steps are the number to read. The AI line gap in the ship phase (row 7) means a green build still
  installs without `fast_lane.ai`: driveable by Kevin, not by the AI (T4 is out of reach until reconciled).
- **Row 11, the freeway:** the first real network through the ship phase; the joint-height class is the expected red.
- **Rows 12–15, the circuits:** the chain's prep is the first new thing V1's two blocked tracks have seen.
- **Rows 16–17:** refused by the chain (exit 2 on the frame), as intended; the matrix says "refused".

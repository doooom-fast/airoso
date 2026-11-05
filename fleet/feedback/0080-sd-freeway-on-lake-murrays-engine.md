---
id: 0080
title: The San Diego freeway network on Lake Murray's engine (`tracks/san-diego-freeway-lm`)
date: 2026-11-05
track: san-diego-freeway (port: san-diego-freeway-lm)
routed: project (the port) + engine (opt-in, freeway-only keys)
status: in-progress — phase 1 (the line, I-8 EB) green on the Mac, not installed; phase 2 step 0 (lidar decks) done, 2a (I-8 WB) built red, 2b-2d owed
---

# 0080 — the San Diego freeway on Lake Murray's engine

Kevin, 2026-11-05: "Yes, start it." The last track in ledger 0078's order (Sand Creek → circuits → Lariat → rally →
the SD freeway network). Branch `claude/freeway-lm`, cut from `origin/claude/fleet-lm-engine` (a98fa35).

## Inputs: PR 34's freeway, copied, not merged

- `tracks/san-diego-freeway/**` and ledger 0075 are **copied** from `origin/claude/freeway-network-fixes` (b888f10,
  PR 34). Not merged: PR 34 carries main's PRs 24-36, which `claude/fleet-lm-engine` does not, and a merge would put
  ~8,800 lines of unrelated tool and engine diff into this branch. PR 34's `scripts/` network fixes (stable_snap,
  join_nodes, cap_dead_ends, seated walls) are **not** brought: the original freeway builds from PR 34 / main, never
  from here, and `git diff origin/claude/fleet-lm-engine -- scripts/` stays empty.
- PR 34's committed `data/` is the PC's first run (before its own fixes). The port reads the **final** PR 34 draft:
  PR 34's tree (b888f10) run on the Mac (`net → classify → network_elev → network_mesh → network_reference`, scratch
  `/Volumes/Drive/codex/fwlm_work/src_draft`); the outputs the port reads are committed under
  `tracks/san-diego-freeway-lm/source/network-draft/` with their md5s, and the port's intake reads them from there.

## The map: what Lake Murray v4's engine already carries of a freeway, and what it doesn't

Lake Murray is a network on this engine: one closed lap (the line) + side streets as **connectors**
(`data/connectors.local.json`, each its own 3DEP, swept as v021 3-row ribbons and merged into ROAD / KERB / MARKINGS),
made into junctions by `route_connectors → divide_connectors → trim_connectors` (cut at the host's pavement edge;
hosts = the mainline + `route.divided_connectors` trunks) `→ weld_mouths → seat_terrain → pads → gap_mouths → stubs`,
gated by `verify_mouths / pads / stubs / fold_fans`. Decks are the line's own (`capture.bridges` / `road_datum.decks`
levelled between real abutments, declared to the prep as `bridges.cache.json` so the prep's pin only pushes DOWN under
them). I-8 itself is in Lake Murray only as a corridor the lap crosses (`i8.local.json`: trench, deck levelling,
guardrails; piece 9, sort (c)). The engine-july prep also has a **merged network OBJ** import (step 1b: `data/track_*.obj`,
`_FW` names, `1WALL` / `HWYSTRUCT` double-sided) from the shipped "loop + freeway" combined kn5 of 2026-07.

| Freeway piece | What it is here | Carried by the LM engine today? | The port's tool / key |
|---|---|---|---|
| **The line** | I-8 eastbound end to end (`network.reference_line`), 10.67 km of the network's 225.6 km, open | **Yes.** `lm_intake` (`loop: false`, the rally ports' open line) → `build_loop_blend` (v021 smoother pins open ends) → `weld_mouths` (folds) → EJ prep → stage dummies (`tools/stage_dummies_blend.py`: grid 45 m in, AC_TIME_0 15 m short of the end, the original's L11 placement) | `lm_intake.source_track` (+ new `lm_intake.network_draft`, below) |
| **Its decks** | the six `capture.bridges` I-8 spans | **Yes**, as every port: levelled between the bank crests over the bare-earth dip, declared to the prep | the source's `capture.bridges` |
| **Its profile** | 3DEP along the line | **Yes**, uncapped (the network draft caps 5 % / 6.5 % on decks; the port does not) | none |
| **Its edge** | paved shoulder to a concrete barrier | **Partly.** `route.edge` (no curb, no walk, as the circuits / rally); v021 has no freeway barrier: `build_guardrails` is I-8-corridor-only (sort c) | `route.edge`; barriers owed (below) |
| **Lane paint** | one-way, white dashes, no centre line | **Yes** (`route.divided_double: false`, lane dividers on) | config |
| **The other carriageways** | I-8 WB, I-5 / SR-52 / SR-163 both ways (~106 km: 196 mainline edges, 116.6 km, less the line) | **Partly.** As connectors they sweep and merge (Lake Murray's Del Cerro trunk is the precedent; `route.divided_connectors` makes a connector a host) | new `tools/network_connectors.py` (edges → `connectors.local.json`), phase 2 |
| **Ramps + interchange connectors** | 416 edges, 109.4 km | **Partly.** Connectors, yes; but `trim_connectors` / `weld_mouths` cut a T at the host's edge, and a freeway merge is a 2-5° gore, not a T | phase 2: overlap at gores first, measured; a gore tool if the gates say so |
| **Interchange merges** (ramp ↔ mainline) | the gores along I-8 EB | **No** (see above); `verify_mouths` judges T mouths | phase 2 |
| **Flyovers / viaducts** (connector decks, up to 3 OSM layers) | ~ every interchange | **No, and the prep fights it.** EJ's contact pin sets every ground vertex under 1ROAD within `LAYER_WIN` 30 m of a deck to the deck, and its 3 m shelf + 6 m feather pull ground up beside it; only the LINE's declared spans are spared (`declare_bridge_spans` walks `centerline.local.json` only). A flyover connector would get a solid embankment that buries every road under it. The assembler's conform (`conform_terrain_to_road` 20 + 16 m, `band_clamp`, `carve_road_corridor`) does the same with connector points. | phase 2: deck pieces kept out of 1ROAD until after the prep (built as their own object, renamed by a post-prep step), and the assembler's terrain fed the pieces' at-grade line (opt-in `route.connector_terrain_lines`) |
| **Deck heights** | where a flyover is | **No measured source on the Mac.** 3DEP is bare earth (no deck); the network draft lifts by OSM `layer` x `scenery.viaduct.layer_height_m` 5.5 m — a modelled number, the source's, not a measurement | carried as the source's declared number, marked unmeasured; **lidar class 17 (PC) owed** |
| **Piers, deck bodies** | under every flyover | **No** (`author_bridges_blend` builds Lake Murray's two bridge bodies from `bridges.authored.json`; the network draft's piers are airoso's) | owed |
| **Barriers / walls** | concrete barrier both edges, every carriageway | **No** (airoso network mesh `1WALL`; v021 lays none but I-8 guardrails) | owed: a barrier author on the swept edges (`1WALL_*`, stub-style) |
| **Dead-end caps** | 156 caps where the bbox cuts a road | **Yes in kind**: Lake Murray's phase-5 stub barriers (`author_stubs_blend`, `1WALL_STUB_*`, `verify_stubs`) | phase 2 |
| **Terrain** | the 18 x 15 km box, Mission Valley to Kearny Mesa (~0-130 m) | **Yes**, but the ±22 m band clamp to the nearest road flattens every mesa to the line's grade while only the line is built; `terrain.tiers` keeps data far out | phase 1 reports it; tiers when the carriageways come in |
| **Water** | Mission Bay, the Pacific | **No** (network env); visual only | owed |

**So:** phase 1 = the line (I-8 EB, its decks, its edge, its paint) through the LM chain to green — the same thing
every port carries. Phase 2 = the network as connectors, which needs three freeway-only opt-ins the engine has no
piece for (gore merges, connector decks kept out of the prep's pin, connector terrain lines) and one measurement the
Mac cannot make (deck heights).

Not taken: carrying the network as airoso's draft `track.obj` through EJ's step 1b (the 2026-07 combined kn5's way). It
would be airoso's network engine inside an LM kn5, not a port: two terrains over one box, and its flyovers still meet
the contact pin above. Lake Murray's `tools/freeway_i8.py` (I-8's pavement drawn visual-only on the final ground,
`scenery.freeway`) is Lake Murray's own I-8 corridor, sort (c); the port does not use it.

Counts are the committed (PC) draft's 612 edges; PR 34's final draft re-nets to 563 edges, 225.7 km (stable_snap).

Lake Murray must not change: everything new is a new file or a key only `tracks/san-diego-freeway-lm` sets; proof as
0078's (`git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`, Lake Murray's draft A/B,
`tests/run_tests.py`).

## Phase 1 (Mac): the line through the LM chain — every gate green, nothing forced

`tools/ship_track.sh san-diego-freeway-lm --no-install` from an EMPTY workshop (`/Volumes/Drive/codex/fwlm_work/ws4`;
Blender 4.2.9, ENG = the engine-july snapshot's `scripts/` + `vendor/` + airoso's `assets/textures`; the script's
Windows Blender path and workshop root swapped in a scratch copy). **SHIP OK.**

Chain: `lm_intake` (the line from `source/network-draft-pr34`, width steps flared, the 3DEP grid cut to the line + 1 km,
the six decks levelled, no grade cap) → `build_loop_blend` → `weld_mouths` (mainline folds; no mouth) → `densify_ribbon`
→ **`deck_rails`** (new) → engine-july prep → stage dummies (grid at 49 m, finish at 10,620 m of 10,635) → split → export
→ gates + edge report.

| Gate (BUILT kn5) | first run (ws2) | **now (ws4)** |
|---|---|---|
| soft top in lane | 14 (s 25-27) | **0** |
| severe steps / bumps > 2.5 cm / kinks | 0 / 0 / 0 | 0 / 0 / 0 |
| excursion drops, gated (limit 10 = 1 /km) | 19 (every one at a deck edge) | **6** (0.14-0.18 m, s 1,350, 1,500, 3,752, 7,354) |
| far flare ledges (reported) | 4 | 19 |
| obstructed / floating / daylight / undrivable corners | 0 | 0 |
| drive_test verdict | FAIL | **PASS** |
| audit_mesh | CLEAN | **CLEAN** (walls 3,910 v: the deck rails) |
| verify_kn5 / verify_inis | PASS | **PASS** |
| kn5_ground_check | PASS | **PASS** (road over ground p95 0.021 m, 1 of 2,690 over 5 cm) |
| max grade / 10 m | — | **5.25 %** measured (the network draft capped 5.0 %) |

| kn5 | MB |
|---|---|
| `san_diego_freeway_lm.kn5` (road, terrain, rails, paint; the single layout's dummies in it) | **14.2** |
| total | **14.2** (budget 120) |

Edge report (built OBJ, 2,056 side-stations): 1 m past the lane edge = ground 100 %; rise within 2 m 0 / 0; road physics
past the edge 0; ground 10 m out p5 / median / p95 -0.87 / -0.18 / -0.05 m, 3.5 % more than 1 m below, 0 above.

What each fix did:
- **Soft top at s 25-27 (14 → 0).** The network draft's per-edge widths step at an edge joint (7.16 → 10.82 m at s 25);
  the v021 ribbon swept the step as one twisted quad and the prep's pinned ground stood over it. `lm_intake.width_taper`
  0.1 m per m (round 5's opt-in, Milford's rate) flares 44 points, widening only.
- **Excursions at the decks (19 → 6).** Every gated drop was off a declared deck's edge, where the real road has a bridge
  barrier and drive_test's own note reads "a bridge with no railing is the defect". `tools/deck_rails_blend.py` (new,
  draft step `deck_rails`) calls Lake Murray's `build_guardrails`, unchanged, once per declared deck, the deck's stretch
  of line standing in for Lake Murray's I-8 polyline: 0.95 m double-sided panels 0.15 m outside both edges, 22 m + 3
  points past each deck end (Lake Murray's numbers). On a flare each row takes the widest of itself and its neighbours (the
  first cut stood in the wheel paths at s 1,336-1,341 and 3,358-3,364: obstructed 5 → 0). The six left are 0.14-0.18 m
  shoulder ledges past the rails' ends, under the 1 /km limit.

What is NOT in phase 1 (the map above): the 543 other edges (215 km: I-8 WB, I-5, SR-52, SR-163, every ramp), their
decks, the edge barriers off the decks, the dead-end caps, water. The terrain outside 1 km of I-8 is not built.

### Lake Murray unchanged

- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is **empty**.
- Files Lake Murray's chain runs that changed: `tools/ship_track.sh` gains one function, `draft_deck_rails`, which runs
  only when a ship.json names `deck_rails` (Lake Murray's does not; `tools/ship_track_spec.py` unchanged, so Lake Murray's
  spec lines are byte-identical). `tools/lm_engine_intake.py` (never run by Lake Murray) gains `source_data` and
  `grid_crop_m`, both absent = as before. New files: `tools/network_line.py`, `tools/deck_rails_blend.py`. No shared
  junction tool (trim_connectors, mouth_weld, weld_mouths_blend, lm_pads_blend, strip_seam_blend, verify_pads,
  plan_buildings) changed. So Lake Murray's draft / trim A/B is byte-identical by construction: no line of code its
  draft or trim executes differs.
- `tests/tools/test_lm_engine_port.py` asserts Lake Murray's config names no `source_data`; the freeway port joins the
  empty-workshop intake test, and a new test checks the crop keeps the source samples exactly and the flare only widens.
  `tests/tools/test_network_line.py`: the raw 10 % climb survives (the draft's 5 % cap does not bind) and lon / lat come
  from the draft's geojson.
- `python3 tests/run_tests.py` on this Mac stops at `tests/tools/test_bench_pad.py` (`pytest.importorskip("scipy")`, no
  scipy here; the file is fleet-lm-engine's, round 13). The 630 tests before it pass but one,
  `test_registry_moves::test_real_registry_puts_the_lariat_at_airoso_once` (fleet/registry.json and the test unchanged
  from fleet-lm-engine: this machine's checkout layout). Every `tests/tools` file but bench_pad, run one by one with
  `python` on PATH (Python 3.12): **702 pass**; the 5 that do not are `test_draft_equiv.py`'s, which take pytest's
  `tmp_path` fixture (fleet-lm-engine's file, unchanged).

## PC runbook 0080-1: phase 1 rehearsal (no install)

ENG: a copy of `eng_repro` (no bespoke texture: the port's materials are the engine's own road / grass / paint and
`GUARDRAIL`, all in REFERENCED.md5), e.g. `D:/k10-scratch/eng_fwlm`.

1. Worktree: `git fetch && git worktree add D:/k10-worktrees/freeway-lm origin/claude/freeway-lm`.
2. Workshop: `mkdir -p D:/k10-scratch/san_diego_freeway_lm` (ship.json `workshop` D:/k10-scratch). EMPTY is enough: the
   intake reads `tracks/san-diego-freeway/source/network-draft-pr34` from the worktree.
3. Rehearse: `SHIP_PROJ=D:/k10-scratch/fwlm_try AIROSO=D:/k10-worktrees/freeway-lm ENG=D:/k10-scratch/eng_fwlm bash
   tools/ship_track.sh san-diego-freeway-lm --no-install`. Expect the Mac's ws4: `[lm_intake] ... 6 deck(s) levelled,
   grade cap none, steepest 5.25 %`, `[deck-rails] 654 rail panels on 6 declared deck(s)`, soft top 0, severe 0,
   excursions 6, obstructed 0, audit CLEAN, kn5_ground_check PASS, kn5 ~14.2 MB, SHIP OK.
4. Install only on Kevin's word: the same without `SHIP_PROJ` and without `--no-install`; it lands as
   `content/tracks/san_diego_freeway_lm` beside `san_diego_freeway`.

## PC runbook 0080-2: the deck heights (lidar) the network phase needs

The Mac cannot measure a flyover's deck: 3DEP is bare earth. For every OSM bridge way in
`tracks/san-diego-freeway/source/network-draft-pr34`'s network (the draft's `network.edges.local.json` lift > 0, from
`/Volumes/Drive/codex/fwlm_work/src_draft/data`, to be committed with phase 2), read the San Diego lidar's class 17
(bridge deck) returns along the edge's centreline every 5 m, as `tools/lidar_crossfall.py` reads class 2, and write
`[edge id, vertex, deck z, n returns]`. Where class 17 is absent, write nothing (no fill). Phase 2 takes those heights
for the decks instead of the draft's `layer x 5.5 m`.

## Phase 2 (Mac): the network

Kevin's calls for phase 2 (2026-11-05, "I just want real"): deck heights from the lidar, not OSM layer x 5.5 m; the
edge as it is (paved shoulder to the concrete barrier, Caltrans' standard plan); the whole box with tiered terrain;
gore merges and connector decks as new, freeway-only engine pieces. Order: 2a I 8 westbound, 2b I 5 / SR 52 / SR 163
mainlines, 2c ramps + gores, 2d interchange connectors + flyovers.

### Step 0: the network draft committed, the decks measured from the lidar (on the Mac)

- **Committed** (`tracks/san-diego-freeway/source/network-draft-pr34/`, md5-identical to the inputs `network_line.json`
  lists): `network.edges.local.json` (563 edges, each one's swept and at-grade lines), `network.geojson` (lon / lat,
  OSM `layer_profile`), `network.elevation.json` (3DEP per vertex), `network.local.json` (the frame).
- **The lidar is readable here.** USGS 3DEP point clouds as EPT on AWS (`usgs-lidar-public`), read with the scratch
  `lidarvenv` (laspy[lazrs], pyproj, scipy). The projects whose bounds touch the box: `CA_SanDiegoQL2_2014` (QL2,
  countywide), `CA_SanDiego_2015_C17_1` (its points are all east of the box: no bridged vertex inside its footprint),
  the Scripps 2002-06 coastal strips and the 2016 El Nino / East County sets (none inside). **The source is
  `CA_SanDiegoQL2_2014`** (https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CA_SanDiegoQL2_2014/ept.json).
  Datum check: its class-2 ground minus the draft's 3DEP, median **+0.11 m**.
- **`tools/network_deck_lidar.py`** (new): every edge with OSM `layer` != 0 (201 edges, 28.4 km bridged), stationed every
  5 m along its OSM centreline from 30 m before the first bridged vertex to 30 m past the last; class-17 and class-2
  returns within 2 m; the deck levels split at 2 m gaps; the level kept is the one continuing the last reading on the
  edge (within 15 m along, 2 m up / down), else the one nearest the draft's model (which chooses, never supplies a
  height); off OSM's bridge a deck counts only within 2 m of the 3DEP (an overpass ABOVE the road is not its deck). Its
  invented numbers are in `fleet/GATES-CHANGELOG.md` 2026-11-05 (step 0). Output
  `deck_profiles.lidar.json` (808 KB): every station's deck z + returns, the levels seen, ground z, the draft's model and
  3DEP. Rerun from the committed inputs reproduces it byte for byte (md5 bf2d42d5).
  Python's one TLS stream stalled on this Mac (0.2 MB in 10 min); `--dry --cache DIR` lists the 525 node files for a
  parallel `curl` (115 MB in under a minute), then the run reads the cache.
- **Result: 3,155 of 5,394 bridged stations read a deck (58 %), on 144 of 201 bridged edges.** Deck minus the draft's
  model: median -0.17 m, p5 / p95 -4.18 / +6.26 m (the 5.5 m-per-layer model is metres off at the extremes).
  Not read: **1,595 stations have no return at all** (the 2014 EPT has holes: 0.01-degree cells at -117.20 / 32.76
  (the I 5 / I 8 interchange, Morena) 802 + 211 + 115, Kearny Mesa -117.13 / 32.84 183, -117.18 / 32.85 (I 5 / SR 52)
  181, and a few smaller); 644 have returns but no class-17 deck there; 329 see a deck level but not one that is theirs.
- **A better source exists and is not reachable from here today:** USGS `CA_SanDiegoCo_D24` (the 2024 county lidar,
  published 2026-09-10, 1 km LAZ tiles, e.g. `USGS_LPC_CA_SanDiegoCo_D24_11SMS481624.laz` ~65 MB) and the 2014 project's
  own LAZ tiles over the EPT holes are on `rockyweb.usgs.gov` only, which answered HTTP 429 (rate limit) to every request
  from this Mac; not retried round it. The PC (runbook 0080-2) or a later Mac run can read them into the same table:
  `network_deck_lidar` reads EPT; a LAZ-tile reader is owed.

### Step 2a: I 8 westbound beside the line — BUILT, NOT GREEN (Mac, ws8)

New, all port-only (Lake Murray runs none of them):
- `tools/network_connectors.py`: each `lm_intake.network_connectors` entry resolved on the network draft by the line's
  own resolver (`scripts.geometry.network_reference.resolve`), x / z the at-grade OSM line, Y its own 3DEP (network_line's
  median + mean, no cap) and **on a deck the lidar** (`deck_profiles.lidar.json`); a bridged run the lidar misses runs
  straight between its readings or, with no measured end, is levelled crest to crest (`evidence.level_bridge_decks`);
  approaches raised to the bank crest off a measured deck's end; widths flared (0.1 m / m, widening only); a one-way
  paint record (v021 `lane_markings` numbers, no yellow); `deck` / `decks_all` ranges. Output committed:
  `tracks/san-diego-freeway/source/network-draft-pr34/connectors.local.json` + `network_connectors.json` (reproduced byte
  for byte from the committed inputs; `tests/tools/test_network_connectors.py`).
- **I 8 WB:** 17 edges (397 ... 198), 1,888 points, **9,409 m**; 5 measured decks over 66 points (deck-end steps to the
  approach <= 0.34 m), 66 bridged points levelled crest to crest in 3 runs (edge 186: the Morena EPT hole), 32 approach
  points raised. Edge 396 (1.4 km at the east end, the draft's travel direction 0 = undecided) and 276 (57 m) are not in
  the chain: WB stops ~1 km short of the line's east end.
- `tools/network_drive_lines.py` + gate `drive_test_network` (ship.json): WB is driven as a drive_test `--line`, hard.
- `tools/deck_rails_blend.py`: rails also on every network connector's `decks_all` (418 panels on WB's 6 decks).
- `tools/lm_engine_intake.py`: network connectors meet no host, so `mouths.json` is the empty record.
- ship.json: `weld_mouths` out of the draft (did nothing in phase 1; refuses a connector with no yellow block, see
  GATES-CHANGELOG); config: `lm_intake.grid_upsample` 2.

| Gate (BUILT kn5) | phase 1 (ws4) | 2a, 27.5 m ground (ws7) | **2a now (ws8)** |
|---|---|---|---|
| line: soft top in lane | 0 | 1,119 | **138** |
| line: severe / bumps / kinks per km | 0 / 0 / 0 | 5 / 0.75 / 12.98 | **0 / 0 / 3.2** |
| line: excursions gated (limit 10) | 6 | 10 | **9** |
| line: floating furniture | 0 | 10 | **10** (WB deck rails at x 1,278-1,287, 1.6 m) |
| line drive_test | PASS | FAIL | **FAIL** (soft top, floating) |
| WB: soft top / severe / kinks per km | — | 1,224 / 0 / 9.46 | **130 / 0 / 2.23** |
| WB: excursions gated (1 /km) | — | 42 | **17** (worst 4.44 m at WB s 6,000) |
| WB drive_test --line | — | FAIL | **FAIL** |
| audit_mesh | CLEAN | 1,589 | **1,589**: D walls on a road 352, I sidewalk isolating pavement 686, K kerb in carriageway 551 |
| verify_kn5 / verify_inis | PASS | PASS | **PASS** |
| kn5_ground_check | PASS | PASS | **PASS** |
| kn5 | 14.2 MB | 16.9 MB | **29.4 MB (+15.2: WB +2.7, the x2 ground +12.5)** |

Edge report (ws8, the line): 1 m past the lane edge ground 91.8 %, **lane 7.9 %** (the other carriageway), kerb 0.3 %;
rise within 2 m 0 / 0.014 m; ground 10 m out p5 / median / p95 -0.33 / -0.17 / +1.50 m, 9.5 % more than 1 m above.

Why it is red — three mechanisms, measured (`/Volumes/Drive/codex/fwlm_work/ws8`):
1. **The carriageways overlap.** The draft's widths are lane counts x 3.66 m + shoulders (up to 25.5 m); where I 8's
   median is narrow the two ribbons overlap (gap -2.1 to -3.7 m at line s 6,249-6,751; -0.8 m at s 9,251; 0.5-2.5 m over
   s 5,500-9,500). Each carriageway's edge strip then lies in the other's lane (audit K 551, I 686), and each's deck rails
   stand on the other's pavement (D 352). The real median there is a paved inside shoulder to a concrete median barrier;
   neither is built (Kevin's call 2, the barrier, owed).
2. **Close carriageways at different heights** at the I 5 / I 8 interchange (line s 3,400-4,100 / WB s 5,800-6,200):
   gap 1.9-4.3 m, WB 1.5-4.6 m above the line. The ground between them is a cliff (WB excursion 4.44 m) and its facets
   stand over the line's lane edge (soft top s 3,538-3,540). This is the EPT's Morena hole: the line's deck there
   [2,982, 3,462] is levelled crest to crest (unmeasured) and WB's edge 186 is 3DEP + a levelled run. **Neither height
   is measured**; the D24 tiles would settle it. (Where both are measured, the line's levelled decks sit 0.1-0.7 m
   under the lidar, median 0.45 m: phase 1's decks are close.)
3. **The ground at WB's open east end** (WB s 0, lateral -6: the terrain over the ribbon's cut end, where edge 396 is
   missing) and residual 13.75 m facets between the carriageways.

## PC runbook 0080-3: rehearse the newest green build (step 0, 9109a49d)

Step 0 changed no build input of the line: its rehearsal is runbook 0080-1 at **9109a49d** (or d1c676d4), expecting
ws4's numbers (soft top 0, severe 0, excursions 6, audit CLEAN, kn5_ground_check PASS, 14.2 MB, SHIP OK). Do NOT
rehearse `claude/freeway-lm` HEAD expecting green: 2a is red (above).

1. `git fetch && git worktree add D:/k10-worktrees/freeway-lm-s0 9109a49d`
2. `SHIP_PROJ=D:/k10-scratch/fwlm_s0 AIROSO=D:/k10-worktrees/freeway-lm-s0 ENG=D:/k10-scratch/eng_fwlm bash
   tools/ship_track.sh san-diego-freeway-lm --no-install`
3. Optional, the lidar on the PC (fills the Mac's EPT holes if rockyweb serves it there): the D24 LAZ tiles over the
   holes (TNM API `datasets=Lidar Point Cloud (LPC)`, bbox -117.215,32.735,-117.125,32.855, titles `CA_SanDiegoCo_D24`).
   A LAZ-tile reader for `tools/network_deck_lidar.py` is owed first (it reads EPT only).

## Owed (start here)

State (2026-11-05, end of the phase-2 session): step 0 green-neutral and pushed (9109a49d: data + lidar decks, no build
input changed); **2a built, red** (the table above; committed so the next session starts from it, nothing installed).
2b-2d not started.

- **Kevin:** drive phase 1 when installed (runbook 0080-1 / 0080-3 at 9109a49d, his word to install). Decide the median:
  where I 8's carriageways run within a few metres the real section is ONE paved width with a concrete median barrier;
  building that (not two ribbons with ground between) is the fix for 2a's mechanisms 1 and 3.
- **2a to green, in this order:**
  1. **The median.** Where two network carriageways' pavements come within a few metres (or overlap), pave the gap as
     inside shoulder and stand a median barrier on its centre line; trim the overlapping widths to it (never wider than
     the draft's, never invented: the gap is measured from the two lines). Caltrans' standard plan for the barrier
     (Type 60 concrete barrier, Caltrans Standard Plans; not looked up this session: cite the edition and sheet) gives the cross-section; build it as `1WALL_*`
     (drive_test credits a wall at the edge). A new port-only draft step (e.g. `tools/network_median_blend.py`); the
     shared `author_median_blend` is Lake Murray's and on the Sand Creek branch's list — read it, do not change it.
  2. **The outside edge** as measured: NAIP 2022/23 shoulder widths (`tools/naip_crop.py` on `claude/circuit-kerbs-lm`,
     or a Planetary Computer fetch) to the outer barrier, same cross-section; Lake Murray's guardrail only where a
     guardrail is really there (the deck rails today are Lake Murray's 0.95 m guardrail).
  3. **The Morena / Kearny Mesa heights:** the D24 lidar (or the 2014 LAZ tiles) over the EPT holes, via a LAZ-tile
     reader added to `tools/network_deck_lidar.py`; then the line's [2,982, 3,462] deck and WB's edge 186 are measured.
  4. WB's open east end (edge 396, travel undecided in the draft): decide its direction from OSM `oneway` and join it,
     or end WB with Lake Murray's stub barrier (`author_stubs_blend`) as the network's 156 dead-end caps.
  5. The floating rails at x 1,278-1,287 (WB deck rails 1.6 m over their support): read with the median in.
- **2b (I 5, SR 52, SR 163 mainlines, both ways):** `lm_intake.network_connectors` entries (ref + direction; the
  resolver refuses a broken chain, so read its message per road), then **the whole box**: drop `grid_crop_m`, set
  `terrain.tiers` (far cells at the 3DEP grid's native 55 m), and measure the assembler's terrain pass on the box first
  (`/Volumes/Drive/codex/fwlm_work/prof_terrain.py`; phase 1 did not finish in 45 min). If it is too slow, vectorise
  `conform_terrain_to_road` / `band_clamp` / `carve_road_corridor` (numpy, in a NEW module the port opts into by key,
  or in scripts-v021 with Lake Murray's draft A/B byte-identical) — not a crop. kn5 budget: 2a is 29.4 MB for ~20 km of
  carriageway; 2b adds ~97 km: expect the 120 MB budget to need the box's far ground at native spacing (tiers) and
  per-layout kn5s before any geometry is cut.
- **2c (ramps + gores):** ramps as connectors with mouths: `trim_connectors` cuts a T; a freeway merge is a 2-5 deg
  taper. A new gore tool (port-only), measured against `verify_mouths`; `weld_mouths_blend`'s empty-yellow-block refusal
  (`_dev` on a (0,) vs (0, 3) array) needs fixing by its owners (`claude/sand-creek-lm-assets`) or the gore tool must
  not depend on it.
- **2d (interchange connectors + flyovers):** deck pieces kept out of `1ROAD` until after the prep (EJ's pin raises ground
  to the highest 1ROAD within `LAYER_WIN` 30 m, and its bury-cull deletes pavement >= 0.3 m under other pavement: an
  at-grade road under a flyover would be culled), renamed after the prep by a port step; the assembler's conform fed
  each connector's `terrain_xyz_m` under its `decks_all` (opt-in key). 1,595 bridged stations have no lidar (the holes).
- Water (Mission Bay) and piers / deck bodies: not started.

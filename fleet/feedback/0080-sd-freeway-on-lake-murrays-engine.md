---
id: 0080
title: The San Diego freeway network on Lake Murray's engine (`tracks/san-diego-freeway-lm`)
date: 2026-11-05
track: san-diego-freeway (port: san-diego-freeway-lm)
routed: project (the port) + engine (opt-in, freeway-only keys)
status: in-progress — phase 1 (the line, I-8 EB) green on the Mac, not installed; phase 2 step 0 (lidar decks) done; 2a (I-8 WB) round 4 GREEN on the Mac (ws19: the median step from the lidar, the deck edge, the one-sided cut; not rehearsed on the PC, not installed; left: the unpaved median unread, NAIP vs lidar at Morena, WB s 7,052, the outside barrier, WB east end), 2b-2d owed
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

### Step 2a round 2: measured edges, the median barrier, WB's east end, the 2024 lidar — BUILT, NOT GREEN (Mac, ws9-ws12)

Kevin's calls (2026-11-05, "I just want real"): carriageway edges measured off the aerial, not lane counts; the
concrete median barrier where the median is one paved width; the outside shoulder at its measured width; the lidar
holes from the 2024 county lidar; WB closed to the line's end.

**1. Measured carriageway edges** — `tools/naip_carriageways.py` (new, port-only). NAIP 2022 (USDA FSA, 0.6 m, R G B
NIR; Planetary Computer items `ca_m_3211715_sw/_se_11_060_20220425`, the latest San Diego year it holds) read across
both I 8 carriageways every 5 m from the network lines. Pavement = low NDVI, unsaturated, not shadow; an edge = where
1.2 m of not-pavement starts. Within 45 m of each other the two are read as one section: a break between them = an
unpaved median (each inner edge where its pavement stops), none = ONE paved width with the barrier on the median's
sunlit-top ridge (seen) or the two lines' midline (not seen). Edges smoothed (running medians), unread runs up to 60 m
interpolated, longer ones keep the draft's edge (counted), each edge changes at most 0.1 m / m (the width_taper rate),
widening only, never past the barrier. Each vertex then moves to the measured pavement's centre with the measured
width: `centerline.measured.local.json`, `connectors.measured.local.json` (+ `median_barrier.json`,
`carriageway_edges.naip.json`: every station's reading, its kind, the provenance), read by the intake's new
`lm_intake.line_file` / `connectors_file` keys.
- Line: inner side barrier seen 590 / at the midline 802 / unpaved median 419 / unread 257 stations; outer read 1,118,
  unread 1,010 (another pavement or a ramp within 6 m: the draft edge kept there). WB: 601 / 787 / 429 / 155; outer 888 /
  1,157. Width minus the draft's p50 +2.9 m (the draft under-counted the shoulders).
- **Overlap: 0 of 1,941 paired stations** (2a's mechanism 1 was 0.5-3.7 m of overlap). Render checks (NAIP with the
  measured edges and barrier drawn) at line s 3,600 (Morena), 6,500 (2a's worst overlap), 8,500, 2,300 (an unpaved
  median) and x 3,600: the barrier sits on the real concrete barrier's shadow line; the edges on the pavement edge.

**2. The median barrier** — `tools/median_barrier_blend.py` (new draft step `median_barrier`, after `deck_rails`):
33 runs, 6,705 m, 1,374 sections, as `1WALL_MEDIAN` (engine-july's 1WALL: collidable, double-sided, concrete texture).
**Caltrans Concrete Barrier Type 60, Standard Plans A76A** (the 1999 edition's "Type 60"; the 2026 edition's sheet A76A
is "Concrete Barrier Type 60M"): 0.914 m (36 in) high, 9.1 deg faces (Caltrans Roadside Safety Research Group, "Type 60
median barrier MASH 2016" / FHWA report 140MASH3C16-04, built to the 1999 A76A / A76B), 0.610 m base; 0.317 m top
follows. **The sheet's own drawing was not read** (its DGN is compressed; no PDF reader on this Mac): owed, one look.
Each foot sits on its own built pavement (ROAD ray-cast); the inner edges stand 0.3 m off the foot (ws10: with the
edge at the foot, smoothing put pavement under the body: audit D 13,800). 472 sections have feet > 0.3 m apart: there
the low side's face runs down to the low pavement (a retaining face; the A76 unequal-grade variants not read). The
step also cuts the TERRAIN faces within 1 m of the barrier to <= 2 m edges (1,677 faces, +90k vertices): a 13.75 m
facet pinned to both pavements stood over the lower one's lane (ws10: WB soft top 112 at s 4,650-5,600, 0.2-0.5 m
between the carriageways).
- **The outside shoulder** is item 1's outer edge (measured where read). **No outside barrier is built**: NAIP at
  0.6 m does not resolve one reliably and the lidar has not been read for it; Lake Murray's rails stay on the decks only.

**3. WB's east end** — `network_connectors` `head`: edge 396 vertices 162 -> 1 put in front of 397 (+812 m, WB now
10,220 m). Evidence in the config's `_why`: 396 is two westbound roadways joined at its hairpin; 0..162 run 22-24 m
north of (left of) the line's EB edges; node A has only 397 leaving and ramp 395 arriving; the 28 backward votes /
49 = 0.57 = 162 / 284 vertices. OSM's `oneway` could not be re-read (Overpass 504 / timeout). The draft has no
westbound mainline east of x 4,236: **WB starts 290 m short of the line's end**; a stub barrier there is owed.

**4. The 2024 lidar** — rockyweb.usgs.gov retried politely (one request at a time, exponential backoff, no Retry-After
offered): `CA_SanDiegoCo_D24` tile `11SMS481624` came through (64.9 MB, 17:19); `11SMS480624` was refused (429) at
17:21, 17:25, 17:33 and later; the fetch was stopped at hand-back. `tools/network_deck_lidar.py --laz DIR` (new): LAZ
tiles (CRS from each tile's header, NAD83(2011) / UTM 11N + NAVD88 GEOID18) fill ONLY the stations the 2014 EPT returned
nothing for (a 14th column names the tile). **605 hole stations filled; decks read 3,155 -> 3,613.** WB: measured deck
points 66 -> 101, levelled (unmeasured) 67 -> 32. I 8's remaining holes: 111 stations in tile `11SMS480624` (west
Morena). The line's own decks are still `capture.bridges` levelled crest to crest (the intake's rule): putting the
lidar on the line's decks is owed.

| Gate (BUILT kn5) | phase 1 (ws4) | 2a (ws8) | measured + barrier (ws11) | **+ D24 decks (ws12, HEAD)** |
|---|---|---|---|---|
| line: soft top in lane | 0 | 138 | 1 | **1** (s 0, the west end, 5.6 m right) |
| line: severe / bumps / kinks per km | 0 / 0 / 0 | 0 / 0 / 3.2 | 0 / 0 / 0 | **0 / 0 / 0** |
| line: excursions gated (limit 10) | 6 | 9 | 10 | **10** |
| floating furniture (both lines) | 0 | 10 | 10 | **10** (WB's median-side deck rail on its approach, x -4,452..-4,467, 0.8-0.9 m over the unpaved median) |
| line drive_test | PASS | FAIL | FAIL | **FAIL** (soft top 1, floating 10) |
| WB: soft top / severe / kinks per km | — | 130 / 0 / 2.23 | 0 / 0 / 0 | **34 / 4 / 7.43** (all at s 7,037-7,074: the D24-measured Morena deck) |
| WB: excursions gated | — | 17 | 25 | **25** (5.82 m at s 7,052 off the D24 deck; 4.4-4.8 m at s 6,750-6,900 left; most others 0.12-0.4 m, median side, s 8,100-9,750) |
| WB drive_test --line | — | FAIL | FAIL | **FAIL** |
| audit_mesh | CLEAN | 1,589 (D 352, I 686, K 551) | 128 (D 128) | **128** (D 128, I 0, K 0) |
| verify_kn5 / verify_inis | PASS | PASS | PASS | **PASS** |
| kn5_ground_check | PASS | PASS | PASS | **PASS** |
| kn5 MB | 14.2 | 29.4 | 41.0 | **41.0** |

kn5 (one file, `san_diego_freeway_lm.kn5`; budget 120): 29.4 (ws8) -> 34.6 with the measured edges + barrier (ws10)
-> 41.0 with the terrain cut near the barrier (+6.4 MB, +90k ground vertices). Not cut. Tiering would save most where it
saves most already: the x2 ground (12.5 MB of 2a's) only needs to be fine near the roads.
Edge report (ws12, line): 1 m past the lane edge ground 77 %, **lane 1.8 %** (ws8 7.9 %), wall 12.2 % (the barrier).

What the round proved: the overlap was the whole of 2a's audit (I 686 -> 0, K 551 -> 0) and the median ground was
the whole of WB's soft top (130 -> 0 before the D24 deck); what is left is decks (rails off the deck, the prep vs a
measured connector deck) and edges with no barrier.

### Step 2a round 3: the Morena deck was an overpass, audit CLEAN, the line's decks from the lidar — BUILT, NOT GREEN (Mac, ws13-ws15)

**1. WB's Morena failure was the lidar picking the deck ABOVE WB, not the prep.** `deck_profiles.lidar.json` edge 186
s 360-385: WB's own deck (18.47 m at s 355) is hidden from the airborne scanner under the I 5 connector crossing over it
(only the 26.7-27.3 m level returns at s 360-370); `network_deck_lidar`'s continuation timed out after `CONT_M` 15 m and
the model-nearest pick (7.4 m off the model, inside `MAX_PICK_M` 8) took the connector, so WB climbed 8.8 m in 30 m
(s 7,043-7,073, a 29 % grade): every round-2 failure there (soft top 34, severe 4, kinks 7.4 / km, the 5.8 m drop).
Fix in the reader (`tools/network_deck_lidar.py`): where the station before had returns but only another deck's, our deck
is HIDDEN, and for `HIDDEN_M` 30 m from there it continues along its own measured grade (its last `CONT_M` of
readings), taking a level again only within `CONT_DZ_M` + `HIDDEN_GRADE` 0.08 x the distance since its last reading;
past that the model chooses, as before. Edge 186 now reads 18.47 -> 17.95 -> 17.70 (WB s 7,043-7,073: 17.49 -> 16.94).
Network-wide: 80 stations change (read -> unread 60, unread -> read 9, a different level 11), all on 15 edges where a
deck crossed over the edge's own; deck reads 3,613 -> 3,562 (an unread station is honest, an overpass read as the deck
is not). Edges 186 (WB), 277 and 394 were reading a flyover 8-21 m above themselves; the 60 dropped readings (edges 286,
302, 16, 103, 166...) sit in the first 30 m after another deck where the old pick had switched to it. Rerun from the cache:
md5 `be6d5f7a...` (the file), WB's connector regenerated (`network_connectors`: deck points 101, spanned 6 -> 4, deck minus
3DEP max 20.09 -> 11.56 m), `naip_carriageways` rerun (edges unchanged by Y).
- **The prep was not changed.** With the deck read right, WB at Morena is soft top 0, severe 0, kinks 0 (ws13) with
  engine-july's prep as it is, so its contact pin / the assembler's conform were not the cause, and no chain step Lake
  Murray runs was touched (no A/B owed: `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`
  is empty). A connector deck over a BUILT road (2d's flyovers) still needs the prep to spare it: owed with 2d.

**3. audit D 128 -> 0 (CLEAN).** Located (all 128 on `1WALL_MEDIAN`, 7 clusters): the barrier's foot vertices stood over
pavement because (a) the assembler smooths the line horizontally (route.smooth_sigma_pts 2, 2 passes) AFTER
naip_carriageways pinned its inner edge, moving the line up to 0.26 m toward the barrier (line s 5,891, 6,359, 6,549,
6,754, 10,289, 10,349; p95 0.38 m over the whole line), and (b) at WB s 4,045 a barrier run's first reading is ragged
(2 m sideways in 5 m) and the pin (nearest barrier station, perpendicular component) missed it. Fix in
`tools/naip_carriageways.py` (`clear_of_barrier`): the assembler's own `smooth_centerline` (the line's config sigma /
passes via `--config`; a connector's hard-coded 1.5 / 1) predicts the swept centre, and a vertex is narrowed (both
edges, about that centre) until its swept inner edge and the chords to its neighbours stand `BARRIER_CLEAR_M` 0.3 m off
every barrier run's foot (exact segment distance), neighbours closing at the width_taper rate on both sides. Line 743
vertices narrowed (median 0.30 m of width, max 1.70), WB 682 (median 0.10, max 2.10): round 2's pin had not actually held
the 0.3 m it declared. **Cost:** a symmetric cut moves the OUTER edge in by the same amount; the line's gated excursions
went 10 -> 16 (ledges at s 5,550, 5,700, 6,754 -11.5, 7,202 now inside drive_test's 4 m band). A centre shift instead
of a symmetric cut is owed (below).

**The line's decks from the lidar (owed in round 2).** New opt-in `lm_intake.line_decks_lidar` (the port's config only):
over each declared deck the line rides the lidar class-17 deck of its own edges (`network.reference.json` line edges,
stations within `LINE_DECK_MATCH_M` 4 m in plan), straight between readings, anchored on the levelled crest height at
each span end; levelled only where nothing was read. 82 points read, 17 between readings, 148 still levelled; measured
minus levelled median **+0.47 m** (Morena [2,982, 3,462]: lidar 15.6-16.4 m against 14.3-14.7 levelled; the 2014 EPT
and D24 tile 480624 holes leave the rest levelled).

**2. The floating deck rail: 10 -> 5.** `tools/deck_rails_blend.py`: a network connector's deck rail column with another
carriageway's pavement at least `FASCIA_MIN_M` 0.3 m lower within `FASCIA_PROBE_M` (0.5-3 m) beyond it has its foot carried
down to that pavement (the deck's edge girder face, at most `FASCIA_MAX_M` 3 m): 77 columns on WB's decks. The line's
rails are Lake Murray's, unchanged. Left: 5 columns at x -4,486 .. -4,497 (WB deck [1811, 1831], WB s ~9,050), 0.88-1.07 m,
where the line's pavement is further than 3 m: there the median ground itself is ~1 m under WB's deck edge.

| Gate (BUILT kn5) | phase 1 (ws4) | round 2 (ws12) | **round 3 (ws15, HEAD)** |
|---|---|---|---|
| line: soft top in lane | 0 | 1 | **1** (s 0, the west end, -5.6 m) |
| line: severe / bumps / kinks per km | 0 / 0 / 0 | 0 / 0 / 0 | **0 / 0 / 0** |
| line: daylight gaps | 0 | 11 | **7** (s 3,496-3,558, +8.3 m: inside the median barrier's body where WB is ~4 m above the line; the probe finds the ground under the barrier at WB's height) |
| line: excursions gated (limit 10) | 6 | 10 | **17** (deck ends 1,201 / 3,154 / 3,304 / 3,454 / 6,604 / 6,754 / 7,202 both sides; 1,351, 5,550, 5,700 median side) |
| floating furniture (both lines) | 0 | 10 | **5** (WB deck [1811, 1831]) |
| line drive_test | PASS | FAIL | **FAIL** |
| WB: soft top / severe / kinks per km | — | 34 / 4 / 7.43 | **0 / 0 / 0** |
| WB: daylight | — | 0 | **0** |
| WB: excursions gated (lap rule 1 / km; line gate 7.12 / km) | — | 25 | **24** (2.35 / km: 3.13 m at s 7,052 off the Morena deck's median edge, between the edge and its rail; 0.12-0.4 m on the median side at s 600-3,754 and 8,100-9,754, where the median ground falls from WB to the line, 1-2.7 m lower, in 2-10 m) |
| WB: line gate / drive_test's lap rule | — | FAIL / FAIL | **FAIL (floating only) / FAIL (floating, excursions)** |
| audit_mesh | CLEAN | 128 (D) | **CLEAN** |
| verify_kn5 / verify_inis | PASS | PASS | **PASS** |
| kn5_ground_check | PASS | PASS | **PASS** (road over ground p95 0.020 m, 115 / 6,019 > 5 cm) |
| kn5 MB (one file) | 14.2 | 41.0 | **41.0** (40.97: the deck fix and the narrowing add nothing measurable) |

Edge report (ws15, line): 1 m past the lane edge ground 76.7 %, lane 0.1 % (ws12 1.8 %), wall 17.9 %, kerb 5.3 %.

**7. Caltrans' sheet: not read.** The 2026 Standard Plans exist as one book PDF
(`dot.ca.gov/-/media/dot-media/programs/design/documents/2026-standard-plans_locked-final-a11y.pdf`), over the 10 MB a
page read takes; single sheets are DGN only. Downloading the book was not done (a file download needs Kevin's yes). The
2026 table of contents, read: A76A, A76AB, A76AC "Concrete Barrier Type 60M"; A76BA 60MP; A76BB 60PR; A76BC 60AP; A76C
60MF; A76D / A76E 60MG; A76F 60MGF; A76G / A76H 60MS; A76I 60MSF; A76BM-A76BR the luminaire variants. Which of these is
the unequal-grade section the 473 retaining sections need is on the drawings, not in the titles: still owed.

**8. WB's last 290 m: OSM has it.** Overpass (one polite request, answered): I 8 westbound east of x 4,236 is ways
1011676575 (-117.12657 -> -117.12940, 4 lanes), 361363276, 361363275, 361363278, 361363282, all `oneway=yes`, running west
into 361363280; eastbound is 361363274 -> 361359806. The draft (PR 34) has no westbound edge there, so it cannot come from
`network_connectors`' head (draft edges only): an OSM-way head (the way's geometry, its 3DEP, the same flare) is owed.

**Not done this round:** 4 (WB's median excursions, above), 5 (the line's s 0), 6 (the outside barrier from the lidar).

### Step 2a round 4: the median from the lidar, the deck's edge, the one-sided cut — GREEN on the Mac (ws16-ws19)

**The datum, first.** The draft's heights are NAVD88 less `network.local.json`'s origin `elev_m` 0.96 m; the lidar's are
NAVD88. With that subtracted, the lidar's class-2 pavement reads within 0.1 m of both built carriageways almost
everywhere it was read (exceptions: the line 0.35-0.45 m low at s 6,700-6,760, WB 0.15-0.25 m low at WB s 3,100-3,250).

**1. The median between carriageways at different heights (owed item 1): read off the lidar, built as measured.**
- New `tools/median_lidar.py` (lidar venv; reads the deck reader's EPT cache and the D24 tile, fetches nothing): at every
  line vertex paired with WB, class 2 across the gap (0.5 m bins, 4 m thick), each pavement's lidar edge height, and the
  median as UNREAD / SLOPE / STEP (a jump > 0.5 m steeper than 1:1 between neighbouring bins: ground does not stand
  steeper, so it is a wall). Written to `source/network-draft-pr34/median_ground.lidar.json` (config key
  `lm_intake.median_ground_file`). 636,218 class-2 returns from 526 files; 1,941 paired stations: **unread 1,601, slope
  282, step 58**. The cache holds the EPT nodes along the DECKS only (round 2's fetch), so the long unpaved median (WB s
  7,100-9,900) is unread: not guessed.
- The steps the lidar reads: the Morena retaining stretch, line s 3,355-3,641 and 3,696-3,847 (2.3-4.4 m, WB above the
  line over a 1.2-1.4 m barrier median; WB s 6,550-6,950), and beside deck 1 (s 1,216-1,306). At line s 3,425-3,611 the
  lidar's wall stands 0.5-2.8 m PAST WB's built (NAIP) inner edge (15 stations flagged `step_past_built_edge`): NAIP put
  WB's median edge over what the lidar reads as the line's level. Owed (below).
- New `tools/median_ground_blend.py`, a prep sub-step (after the prep's pin, before the split; only where the config
  names `lm_intake.median_barrier_file`): (a) along every barrier run where the two feet differ by > 0.3 m (2,081 of 6,087
  one-metre samples, up to 4.59 m), the terrain is cut along the barrier's HIGH foot (two vertical bisects, 0.05 m apart)
  and every ground vertex on the low side of it, in the gap and under no pavement, takes the low pavement's height less
  0.02 m (4,749 vertices, up to 3.74 m down): the low pavement's level runs to the wall, as the lidar shows, and the
  barrier's low face is the retaining face; (b) a lidar STEP with no barrier run within 1 m of its gap (and not within
  25 m of a line deck or 3 vertices of a WB deck: 2d's) gets the same ground and a retaining face, `1WALL_RETAIN`, at the
  high pavement's edge strip, up to that pavement (no parapet: nothing seen). One such station: line s 3,496 (4.21 m),
  the barrier run ending 3.4 m short of it.
- **Result:** the line's daylight 7 -> **0**. The SLOPE application (the measured ground in an unpaved median) is not
  built: of the 282 slope stations only ~80 have an unpaved gap (>= 2 m), all beside the decks (2d's ground); owed with
  the unpaved median's lidar.

**2. The line's excursions (owed item 2): one-sided cut + the deck's edge.**
- `tools/naip_carriageways.py` `clear_of_barrier`: only the barrier side's edge comes in; the vertex moves away from the
  barrier by half the cut, so the outer edge stays NAIP's; re-predicted on the assembler's smoothing until clear (3
  predictions). Line 739 vertices (max 0.85 m), WB 678 (max 1.05 m). Regenerated from the NAIP cache; the barrier runs'
  file is byte-identical (md5 `0c951365...`).
- `tools/deck_rails_blend.py`: the deck's edge under every port deck rail (`1KERB_SIDEWALK_DECK`, concrete): the panel
  stood 0.15 m past the pavement, the freeway's edge strip is 0.1 m, so it stood over the ground: an unguarded drop
  between pavement and rail at every deck station (the line's 1,201 / 3,154 / 3,304 / 3,454 / 6,604 / 6,754 / 7,202
  both sides) and a panel over a void (WB deck [1811, 1831]: the lidar reads it 8 m over the ground between two parallel
  bridges, ws15 floating 5). The slab runs from 0.1 m under the pavement's edge to 0.40 m past the panel, 0.03 m under the
  edge's height; not laid where a fascia was carried down or another pavement lies under its outer edge. 991 panels laid,
  75 skipped.
- **Result:** the line's gated excursions 17 -> **3** (s 5,550 both sides 0.14-0.15 m, s 5,700 +11.0 0.43 m: barrier-side
  ledges), floating 5 -> **0** (both lines).

**3. WB s 7,052 (owed item 3):** 3.13 -> 1.61 m, still gated on WB (inside WB's line gate). Not finished.

**4. The line's s 0 (owed item 4):** the end row was the narrow end of a taper (s 0-25 unread: the draft's 7.16 m widened
toward the first reading at s 30) and drive_test judges a row's stretch with the NEXT row's width: the outer wheel path
stood 0.09 m past the end row's edge. An open carriageway's end row now takes its neighbour's width where narrower (line
s 0 +0.975 m; WB's last row +0.053 m). Soft top 1 -> **0**.

**5, 6 (the outside barrier from the lidar; WB's last 290 m):** not started.

| Gate (BUILT kn5) | phase 1 (ws4) | round 3 (ws15) | **round 4 (ws19, HEAD)** |
|---|---|---|---|
| line: soft top in lane | 0 | 1 | **0** |
| line: severe / bumps / kinks per km | 0 / 0 / 0 | 0 / 0 / 0 | **0 / 0 / 0** |
| line: daylight gaps | 0 | 7 | **0** |
| line: excursions gated (limit 10) | 6 | 17 | **3** |
| floating furniture (both lines) | 0 | 5 | **0** |
| line drive_test | PASS | FAIL | **PASS** |
| WB: soft top / severe / kinks per km / daylight | — | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** |
| WB: excursions gated (line gate 7.12 / km) | — | 24 (2.35 / km) | **24 (2.35 / km)** |
| WB: line gate / drive_test's own lap rule | — | FAIL (floating) / FAIL | **PASS / FAIL (excursions 24 > 10)** |
| audit_mesh | CLEAN | CLEAN | **CLEAN** |
| verify_kn5 / verify_inis | PASS | PASS | **PASS** |
| kn5_ground_check | PASS | PASS | **PASS** (road over ground p95 0.020 m, 115 / 6,019 > 5 cm) |
| kn5 MB (one file) | 14.2 | 41.0 | **42.1** (42.07: the deck edge, the median cuts) |
| ship_track | — | rc 1 | **SHIP OK, rc 0** |

Edge report (ws19, line): 1 m past the lane edge ground 75.7 %, wall 18.4 %, kerb 5.7 %, lane 0.1 %.

**Lake Murray unchanged:** `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty.
The one shared file touched, `tools/ship_track.sh`, gains a prep sub-step behind `lm_intake.median_barrier_file`, which
Lake Murray's config has no `lm_intake` to name (no header, nothing run); `tests/tools/test_ship_track_chain.py`'s
Lake Murray parity holds with the header listed in V4_EXTRAS. No chain step Lake Murray runs changed: no A/B owed.

**Tests:** `tests/run_tests.py` 630 PASS, 1 FAIL (`test_registry_moves`, the same as round 3); pytest `tests/tools` 713
passed, 1 skipped.

### Step 2a round 5: more real, nothing downloaded (Mac, ws20 and up)

**Inputs.** Rebased onto the PC's d738203 (runbook 0080-4: the 2024 D24 tiles 480624 / 481624 read on the PC; WB's
deck heights moved, its measured file's md5 with them). `median_ground.lidar.json` was stale against it (it recorded
connectors.measured 461e3158, the PC's is 3baf3736): re-run on d738203's files with the Mac's lidar (the 2014 EPT cache
and tile 481624; tile 480624 is on the PC only): the same 1,941 paired stations, unread 1,601 / slope 282 / step 58 as
round 4 (WB's xz did not move). **ws20** = d738203 + that refresh, round 4's tools: ws19's numbers on every row (line
drive_test PASS, excursions 3; WB line gate PASS, 24; audit CLEAN; kn5_ground_check PASS; 42,067,878 B; SHIP OK).

**1. WB's median edge at Morena, on the lidar's wall (owed item 1).** NAIP saw no barrier top through Morena and put the
barrier at the midline between the two carriageways' centres ("barrier at the midline"); the lidar's wall stood
0.5-4.5 m from there.
- `tools/median_lidar.py --walls` (new `walls()`): at each line vertex paired with WB, class 2 binned from the line's
  inner edge to WB's CENTRE (round 4's `sections()` looked only 3 m past WB's built edge), the largest step steeper than
  1:1 kept only where it is THE wall between these two pavements: its low bin reads the low carriageway's built height
  and its high bin the high one's, each within 0.5 m (median_ground_blend's own pavement-edge tolerance, reused). Its
  line = the middle of the no-return gap (the barrier and the wall's face). Frozen as
  `median_wall.lidar.json` (48 stations: line s 3,380-3,621 at 8.6-12.6 m off the line's centre, 3-4.4 m tall; s
  3,701-3,721, 2.1-2.5 m; s 3,812-3,847, 0.5-0.9 m).
- `tools/naip_carriageways.py --walls`: a barrier-run station with a wall reading takes the wall's offset (running
  median over the read stations; unread gaps inside a reading up to FILL_M interpolated); the move off NAIP's line is
  ramped in from where the wall is not read at the width_taper rate (0.1 m per m), so no run jogs into a carriageway.
  Both inner edges follow the barrier (the existing pin): through s 3,410-3,530 WB's inner edge moved 2.5-2.9 m in (WB
  13.4 -> 10.6-10.8 m wide) and the line's paved width runs out to the wall's foot (+2.4-2.7 m): the lidar reads that
  strip at the line's level and NAIP reads it as pavement. 47 stations on the wall. `NAIP_OFFLINE=1`: a tile not cached
  is unread, never fetched (none was missing).
- Regenerated (offline) `carriageway_edges.naip.json`, `centerline.measured.local.json`,
  `connectors.measured.local.json`, `median_barrier.json`, then `median_ground.lidar.json` on them (unread 1,603, slope
  264, step 74).
- **ws21:** line drive_test PASS (excursions 3, unchanged), WB line gate PASS, audit CLEAN, verify_kn5 / inis PASS,
  kn5_ground_check PASS, 42,048,478 B, SHIP OK. WB's lap-rule count 24 -> **26**: two new drops at WB s 6,902, where the
  150 m excursion station now falls on the moved stretch: +6.0 (4.56 m: the sample lands inside the barrier's base,
  0.3 m off WB's new edge, where median_ground_blend keeps the LOW ground under the barrier's body) and -6.0 (0.75 m:
  a ground facet from under WB's moved pavement shows 0.6 m past its kept outer edge). Tried: the step at the barrier's
  low foot with the high ground under its body (ws22-ws24): verify_kn5 TERRAIN POKE 4,513 -> 1,107, red; reverted, owed.

**2. WB s 7,052: its cause found, half finished.** The 1.61 m drop was a HOLE in the median barrier: NAIP's line station
s 3,275 was unread between two "barrier at the midline" readings, so the barrier stopped 10 m short (runs [3,250, 3,270]
and [3,280, 3,310]) and WB's flared deck edge at WB s 7,052 faced the gap. The same one-station hole broke the barrier
26 times along I 8.
- `tools/naip_carriageways.py` (`JOIN_ONE_STATION_HOLES`): a barrier run broken by exactly one unread station is one
  run (the barrier runs through it at its neighbours' mean offset). 33 runs / 6,705 m -> 13 runs / 6,990 m.
- `tools/median_barrier_blend.py`: on a declared deck (the line's bridges_levelled, a connector's decks_all) the ground
  in the 0.3 m clearance and under the barrier is the real ground under the bridge, so drive_test's crossing fell there
  unguarded. The deck is carried under the barrier (1KERB_SIDEWALK_DECK, deck_rails_blend's 0.03 m / 0.1 m reused) on
  LEVEL sections: 40 quads. On a STEPPED section (feet > 0.3 m apart, WB s 7,052 is 1.3-1.6 m over the line) the slab
  fails audit_mesh F (ws25: 64 curb verts "not flush": 2 m from the low carriageway's edge, > 2 m from the high one's
  sparse edge vertices): not laid there.
- **ws26:** line drive_test PASS (excursions 3), WB line gate PASS (lap rule 25: s 3,450 gone; s 7,052 still 1.67 m on
  the stepped deck section), audit CLEAN, verify_kn5 / inis PASS, kn5_ground_check PASS, 42,203,383 B, SHIP OK.
- Owed for s 7,052: the stepped deck's barrier needs a surface under its body that audit F accepts (a slab joined to
  the high deck's edge vertices, or F reading a 1KERB under a 1WALL as the wall's footing).

**3. WB's last 290 m: an OSM-way head (owed item 5).** One read-only Overpass query (`way(id:...);out geom tags;`),
the response committed as `network-draft-pr34/osm_i8_wb_head.overpass.json`: ways 1011676575, 361363274-82, all
`oneway=yes` (so node order is travel), I 8 WB = 361363282 -> 278 -> 275 -> 276 -> 1011676575 -> 361363280.
- `tools/network_connectors.py` `head_osm` (config `lm_intake.network_connectors[0].head_osm`, `_why` there): the ways
  in travel order, projected as the draft projects OSM, resampled at the chain's own spacing, ending on the chain's first
  point (edge 396 vertex 162, 3.08 m off way 361363280: the head closes on it linearly along its length, no jog;
  `OSM_JOIN_MAX_M` 5 m [invented] or it refuses). Built from 1011676575's first node (x 4,525, 12 m east of the line's
  end) west: +67 points, +332 m (WB 10,220 -> 10,552 m). Heights: the draft has no 3DEP point heights there, so each
  head point takes the LINE's raw 3DEP abreast (18-42 m away across the median) shifted by WB's own offset at the join
  (-0.47 m); the 55 m grid read 1-4 m off the draft's point heights, so it was not used. Width: the draft's 18.14 m,
  then measured: the cached NAIP covers the head (`NAIP_OFFLINE=1`, nothing missing): 67 barrier-at-the-midline,
  30 read, 38 unread sides; the head 16.8-20.3 m wide. Barrier runs 6,990 -> 7,255 m; overlap 0 of 1,993 paired.
- Regenerated: connectors.local.json, network_connectors.json, the NAIP outputs, median_ground.lidar.json (1,993 paired:
  unread 1,643, slope 275, step 75). `median_wall.lidar.json` kept (absolute positions; the head has no wall).
- **ws27:** line drive_test PASS (excursions 4: + s 10,500 +9.0 0.12 m, the line's median side beside the new head),
  WB line gate PASS (lap rule 24 over 10,555 m: WB's 150 m stations now fall 332 m later, so the set moved: Morena's
  stepped barrier sections at WB s 7,054 / 7,204 and s 3,602 / 9,304 are sampled now), audit CLEAN, verify_kn5 / inis
  PASS, kn5_ground_check PASS (road over ground p95 0.020 m, 131 / 6,135 > 5 cm), 42,786,971 B, SHIP OK.

**4. The outside barrier from the cached lidar: counted, not built.** A census of every line / WB vertex's OUTER edge
(returns within 2.5 m along, from 0.5 m inside the edge to 2.5 m out; the 2014 EPT cache's 525 nodes and tile
481624, 1.57 M returns of classes 1, 2, 7, 17, 18, 20-22; probe `r5/outer_cov.py` in the session scratchpad):

| | vertices | no data | ground only | non-ground >= 0.6 m over the pavement in the first 1.5 m | other non-ground |
|---|---|---|---|---|---|
| line | 2,132 | 1,252 | 235 | 156 | 489 |
| WB | 2,050 | 1,193 | 282 | 106 | 469 |

Neither dataset classes a barrier: what stands at the shoulder's edge is class 1 (unclassified: barriers, vehicles,
sign posts, shrubs alike; 2024's 20-22 are not documented here). The 262 "barrier-like" stations are not separable
from parked vehicles or vegetation without a continuity rule this round did not invent; nothing was built, and 2,445 of
4,182 outer edges have no cached return at all (the cache follows the decks). Owed: a run-continuity reader (a
barrier is a line: a height step that persists station to station) on the outer-edge returns, or the lidar download
over the shoulders (Kevin's yes).

**5. WB's median-side drops, where cached class 2 covers the median: not built, counted.** ws27's 24 (WB 332 m longer:
its 150 m stations sample new places), by what the cache (2014 EPT nodes + tile 481624) holds over each median:
- covered (class 2 across the median, 10-26 of the 0.5 m bins): **8**: WB s 302 (0.13 m), 3,602 (1.09), 7,054 (4.21),
  7,204 x4 (+6.0 4.82, -6.0 3.31, -9.0 / -9.5 0.23: item 1's moved stretch), 9,304 (0.83). Every one is a sample inside
  or beside a barrier's base or a stepped barrier section, the ground under the body being the low side's (or lower);
- partly covered (4 of 11 bins): 2 at WB s 4,352;
- no cached return over the median: **14 wait on the median lidar download**: WB s 1,203 and 13 on the unpaved median
  (WB s 7,951 x2, 9,004, 9,751 x3, 9,901 x4, 10,051 x3: round 4's s 7,100-9,900 in the old stationing).
- The slope pass is not built. Tried (ws22-ws24): the step moved to the barrier's low foot with the HIGH side's ground
  under its body: verify_kn5 TERRAIN POKE 4,513 / 1,107 (raised vertices whose facets reach over the low side's edge
  strips and deck slabs), reverted. Owed: raise the LOW side's gap ground to the low pavement (never the high), off
  decks only, after the step's cut; and the stepped deck sections' surface under the barrier (item 2).

| Gate (BUILT kn5) | round 4 (ws19) | d738203 (ws20) | item 1 (ws21) | item 2 (ws26) | **item 3 (ws27, HEAD)** |
|---|---|---|---|---|---|
| line: soft top / severe / kinks per km / daylight / floating | 0/0/0/0/0 | 0/0/0/0/0 | 0/0/0/0/0 | 0/0/0/0/0 | **0/0/0/0/0** |
| line: excursions gated (limit 10) | 3 | 3 | 3 | 3 | **4** |
| line drive_test | PASS | PASS | PASS | PASS | **PASS** |
| WB: soft top / severe / kinks / daylight / floating | 0/0/0/0/0 | 0/0/0/0/0 | 0/0/0/0/0 | 0/0/0/0/0 | **0/0/0/0/0** |
| WB: excursions gated (line gate 7.12 / km) | 24 (2.35) | 24 (2.35) | 26 (2.54) | 25 (2.45) | **24 (2.27)** |
| WB: line gate / drive_test's own lap rule | PASS / FAIL | PASS / FAIL | PASS / FAIL | PASS / FAIL | **PASS / FAIL (24 > 10)** |
| audit_mesh | CLEAN | CLEAN | CLEAN | CLEAN | **CLEAN** |
| verify_kn5 / verify_inis | PASS | PASS | PASS | PASS | **PASS** |
| kn5_ground_check | PASS | PASS | PASS | PASS | **PASS** |
| kn5 B | 42,067,174 | 42,067,878 | 42,048,478 | 42,203,383 | **42,786,971 (42.8 MB)** |
| ship_track | SHIP OK | SHIP OK | SHIP OK | SHIP OK | **SHIP OK** |

Edge report (ws27, line): 1 m past the lane edge ground 74.6 %, wall 19.1 %, kerb 6.3 %, lane 0.0 %.

**Lake Murray unchanged:** `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty
after every commit. Every tool changed this round is port-only (median_lidar, naip_carriageways, median_barrier_blend,
network_connectors; median_ground_blend tried and reverted); no chain step Lake Murray runs changed: no A/B owed.
**Tests:** `tests/run_tests.py` (python 3.12) 630 PASS, 1 FAIL (`test_registry_moves`, as round 4); pytest `tests/tools`
714 passed, 1 skipped (test_network_connectors: the head shifts WB's indices by 67; one new test for the OSM head).
**Mac note:** ws25 ran while Sand Creek's prep was in Blender (my check missed a step boundary); every later build
waited for `pgrep -x Blender` to be empty.

## PC runbook 0080-6: rehearse 2a round 5, no install

Supersedes 0080-5 (which matched ws19 on the PC). No lidar or NAIP is needed: every generated input is committed.

1. `git fetch && git worktree add D:/k10-worktrees/freeway-lm-2a5 c3c988b9`
2. `SHIP_PROJ=D:/k10-scratch/fwlm_2a5 AIROSO=D:/k10-worktrees/freeway-lm-2a5 ENG=D:/k10-scratch/eng_fwlm bash
   tools/ship_track.sh san-diego-freeway-lm --no-install`
3. Expect ws27's column: line drive_test PASS (excursions 4), WB line gate PASS (24, 2.27 / km), audit CLEAN, verify_kn5 /
   inis PASS, kn5_ground_check PASS, 42,786,971 B, SHIP OK. Any other number: stop and file it here.
4. Optional (fills the Mac's gap): `median_lidar.py` with the PC's tile 480624 too (`--laz D:/k10-scratch/d24`, plus the
   2014 EPT cache), and `--walls` to a scratch file; diff against the committed `median_ground.lidar.json` /
   `median_wall.lidar.json`. If 480624 reads more of the median, commit both and rebuild.

**PC result (2026-11-05 21:05-21:19): every gate row matches ws27; the kn5 is 56 B larger. Not offered to Kevin.**
- Step 4 (a8534007): `median_ground.lidar.json` with 480624 + 481624 + the EPT cache, same inputs: unread 1,643 ->
  1,506, slope 275 -> 412, step 75 unchanged (137 stations unread -> slope, line s 2,186-2,865; no other row changed).
  `median_wall.lidar.json` NOT changed: on its own inputs (86cea68^) 481624 alone reproduces it byte for byte; with
  480624 the same 48 rows, only the header differs (carriageway_edges.naip.json records its md5).
- `fwlm_2a5` (c3c988b9, empty workshop, ENG eng_fwlm): line drive_test PASS (excursions 4), WB line gate PASS / lap rule
  FAIL (24, 2.27 / km), audit CLEAN, verify_kn5 / inis PASS, kn5_ground_check PASS (road over ground 131 / 6,135, p95
  0.020 m), edge report 74.6 / 19.1 / 6.3 / 0.0 %, SHIP OK, **42,787,027 B (ws27 42,786,971: +56)**.
- `fwlm_2a5c` (control: the same commit again) and `fwlm_2a5g` (a8534007: the new ground) are both kn5_equiv-EQUIVALENT
  to `fwlm_2a5` (tangents only), 42,787,027 B: the PC is repeatable, and the 137 slope rows change nothing built (the
  slope pass is not built).
- 56 B = one vertex (44) + two triangles (12): one edge split, a near-tie decided differently on the two machines? The
  PC's per-mesh table (vertices / triangles) for ws27's to diff: 1GRASS_0-7 55,965 / 110,840, 55,710 / 110,189,
  60,497 / 119,192, 59,958 / 117,917, 58,863 / 116,398, 56,209 / 111,057, 56,943 / 112,595, 58,371 / 115,561;
  1KERB_SIDEWALK_DECK 6,222 / 2,074; 1KERB_sidewalk 33,992 / 50,964; 1ROAD_road 50,959 / 16,988; 1WALL_MEDIAN 52,404 /
  17,492; 1WALL_guard 6,402 / 2,136; MARKINGS 42,820 / 26,000; textures 7,770,522 B, materials 3,879 B, nodes 1,398 B.
- **Mac verdict: MATCHED.** ws27's 1GRASS_2 is 60,496 / 119,190 (the PC's +1 vertex, +2 triangles = the 56 B); every
  other mesh, the textures and the materials match exactly: one ground edge split, terrain noise (as 4k's Lake Murray
  control). c3c988b9 (a8534007 equivalent) is offered to Kevin in place of c42b91ab; install only on his word.
- **INSTALLED on Kevin's word (2026-11-05, "All six, freeway 2a"**, asked with westbound's 24 median-side drops and phase
  1 as the fully clean choice said plainly): c3c988b9 from a fresh real workshop D:/k10-scratch/san_diego_freeway_lm, ENG
  eng_fwlm; every gate green as fwlm_2a5, SHIP OK, no force; `san_diego_freeway_lm` ("doooom San Diego — Freeway Free
  Roam (LM engine)" 0.1.0, nothing there before), kn5 42,787,027 B, kn5_equiv-equivalent to fwlm_2a5's. Records with
  this note (taken onto the branch head: nothing under tracks/san-diego-freeway-lm differs from c3c988b9). Not driven yet.

## PC runbook 0080-5: rehearse 2a (I 8 both ways), no install

2a is green on the Mac (ws19). The PC needs no lidar: `median_ground.lidar.json` is committed.

1. `git fetch && git worktree add D:/k10-worktrees/freeway-lm-2a c42b91ab`
2. `SHIP_PROJ=D:/k10-scratch/fwlm_2a AIROSO=D:/k10-worktrees/freeway-lm-2a ENG=D:/k10-scratch/eng_fwlm bash
   tools/ship_track.sh san-diego-freeway-lm --no-install`
3. Expect ws19's numbers: line drive_test PASS (soft top 0, severe 0, daylight 0, floating 0, excursions 3), WB line gate
   PASS (excursions 24, 2.35 / km), audit CLEAN, verify_kn5 / inis PASS, kn5_ground_check PASS, 42.1 MB, SHIP OK. Any
   other number: stop and file it here. Then Kevin drives it (install only on his word).

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

## PC runbook 0080-4: the lidar the Mac could not fetch (rockyweb 429)

The newest GREEN build is still phase 1 (runbook 0080-3 at 9109a49d / d1c676d4, ws4's numbers). Do NOT rehearse HEAD
expecting green. On the PC (its own network), one tile at a time:

1. `mkdir D:/k10-scratch/d24 && cd D:/k10-scratch/d24`, then fetch, sequentially (wait on any 429):
   `https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_SanDiegoCo_D24/CA_SanDiegoCo_2_D24/LAZ/USGS_LPC_CA_SanDiegoCo_D24_<tile>.laz`
   for `<tile>` = `11SMS480624` (I 8 west Morena, 111 hole stations: 2a needs it), then for 2b `11SMS873633`,
   `11SMS833634`, `11SMS823622`, `11SMS813623`, `11SMS883633`, `11SMS873625` (the Kearny Mesa / I 5 - SR 52 holes; the
   tile names are E km / N km in NAD83(2011) UTM 11N, from the hole stations), and `11SMS481624` (the Mac has it).
2. EPT cache: `python tools/network_deck_lidar.py tracks/san-diego-freeway/source/network-draft-pr34 D:/k10-scratch/lid
   --ept https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CA_SanDiegoQL2_2014/ept.json --cache D:/k10-scratch/ept14
   --dry`, fetch `D:/k10-scratch/ept14/nodes.txt`'s 525 files, then the same without `--dry` plus `--laz D:/k10-scratch/d24`.
3. Copy `deck_profiles.lidar.json` into `tracks/san-diego-freeway/source/network-draft-pr34/`, then
   `python tools/network_connectors.py <that dir> <that dir> tracks/san-diego-freeway-lm/track.config.json` and
   `python tools/naip_carriageways.py <that dir> <that dir> --cache <naip dir>` (numpy + Pillow; fetches NAIP 2022 from
   the Planetary Computer), commit the four files. Expect `deck_read` > 3,613 and WB's levelled points < 32.

## Owed (start here)

State (2026-11-05, end of 2a round 5): **2a green on the Mac** (the round 5 table, ws27: the line's drive_test PASS, WB's
line gate PASS, audit CLEAN, kn5_ground_check PASS, SHIP OK, 42.8 MB), nothing installed. The PC matched round 4 (ws19,
runbook 0080-5); round 5 is rehearsed with runbook 0080-6. Lake Murray unchanged (empty diff; no chain step it runs
changed). Nothing was downloaded this round (one read-only Overpass query; NAIP and lidar from the caches).

- **Kevin:** rehearse round 5 on the PC (runbook 0080-6), then drive it (install on your word). Say yes / no to:
  fetching the 2014 EPT nodes over the unpaved median (14 of WB's 24 lap-rule drops wait on it), the lidar over the
  outer shoulders (item 4), the Caltrans 2026 Standard Plans PDF. Look at Morena (the barrier now on the lidar's wall:
  the line's pavement runs to it, WB is 2.5-2.9 m narrower) and WB's new east head.
- **2a, left (none blocks green):**
  1. **The ground under a barrier's base where drive_test samples it** (WB lap rule: s 3,602, 7,054, 7,204 x4, 9,304,
     302): raise the LOW side's gap ground to the low pavement (never the high: ws22-ws24's pokes), off decks only.
  2. **WB s 7,054 (old 7,052) on the stepped Morena deck**: a surface under the barrier that audit F accepts (round 5
     item 2: a 1KERB slab across a step reads as a curb not flush).
  3. **WB s 7,204 -6.0 (old 6,902)**: a ground facet from under WB's moved pavement shows past its kept outer edge.
  4. **The unpaved median's ground** (WB s 7,950-10,050 now): the EPT nodes over it, with Kevin's yes (round 4 item 2).
  5. **The outside barrier** (item 4): a run-continuity reader on the outer-edge returns, or the shoulder lidar.
  6. **Tile 480624 on the Mac**: median_lidar ran with the 2014 EPT + 481624 only; runbook 0080-6 step 4 reads 480624
     on the PC.
  7. **The Caltrans sheet** (round 3 item 7).
- `weld_mouths` stays out (its empty-yellow-block refusal, owed to its owners on `claude/sand-creek-lm-assets`).
- Scratch: `/Volumes/Drive/codex/fwlm_work/run_ship_p6.sh` (round 5's worktree), ws20 (d738203 baseline), ws21 (item 1),
  ws26 (item 2), ws27 (HEAD); round-5 probes in the session scratchpad `r5/` (`xs.py` built sections across WB / the
  line, `tri_at.py` / `verts_near.py` the ground under a point, `cmp_edges.py` / `cmp_bar.py` old vs new edges and
  barrier, `outer_cov.py` the outer-edge census, `gates.py` a ws's gate summary).
- **2b (I 5, SR 52, SR 163 mainlines, both ways):** `lm_intake.network_connectors` entries (ref + direction; the
  resolver refuses a broken chain, so read its message per road), then **the whole box**: drop `grid_crop_m`, set
  `terrain.tiers` (far cells at the 3DEP grid's native 55 m), and measure the assembler's terrain pass on the box first
  (`/Volumes/Drive/codex/fwlm_work/prof_terrain.py`; phase 1 did not finish in 45 min). If it is too slow, vectorise
  `conform_terrain_to_road` / `band_clamp` / `carve_road_corridor` (numpy, in a NEW module the port opts into by key,
  or in scripts-v021 with Lake Murray's draft A/B byte-identical), not a crop. kn5 budget: 2a is 41 MB for ~20 km of
  carriageway; 2b adds ~97 km: expect the 120 MB budget to need the box's far ground at native spacing (tiers) and
  per-layout kn5s before any geometry is cut.
- **2c (ramps + gores):** ramps as connectors with mouths: `trim_connectors` cuts a T; a freeway merge is a 2-5 deg
  taper. A new gore tool (port-only), measured against `verify_mouths`; `weld_mouths_blend`'s empty-yellow-block refusal
  needs fixing by its owners (`claude/sand-creek-lm-assets`) or the gore tool must not depend on it.
- **2d (interchange connectors + flyovers):** deck pieces kept out of `1ROAD` until after the prep (EJ's pin raises ground
  to the highest 1ROAD within `LAYER_WIN` 30 m, and its bury-cull deletes pavement >= 0.3 m under other pavement: an
  at-grade road under a flyover would be culled), renamed after the prep by a port step; the assembler's conform fed
  each connector's `terrain_xyz_m` under its `decks_all` (opt-in key). The lidar holes (2014 EPT; D24 tile 480624 and
  the Kearny Mesa tiles still 429 from this Mac, runbook 0080-4).
- Water (Mission Bay) and piers / deck bodies: not started.

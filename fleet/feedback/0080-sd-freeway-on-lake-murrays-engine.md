---
id: 0080
title: The San Diego freeway network on Lake Murray's engine (`tracks/san-diego-freeway-lm`)
date: 2026-11-05
track: san-diego-freeway (port: san-diego-freeway-lm)
routed: project (the port) + engine (opt-in, freeway-only keys)
status: in-progress — phase 1 (the line, I-8 EB) green on the Mac, not installed; phase 2 (the network) owed
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

## Owed (start here)

- **Kevin:** drive phase 1 when installed (runbook 0080-1, his word to install). Decide the freeway's edge: the real one
  is a paved shoulder to a concrete barrier; neither is measured here (phase 1 lays no barrier off the decks, and the
  deck rails are Lake Murray's 0.95 m guardrail, not Caltrans' barrier).
- **Phase 2, the network**, in this order (the map's rows):
  1. `tools/network_connectors.py` (new): every edge but the line's from the draft's `network.edges.local.json` →
     `connectors.local.json` (one record per chained carriageway / ramp; its at-grade line carried beside it).
  2. The assembler's terrain fed each connector's at-grade line, not its deck (opt-in `route.connector_terrain_lines`
     in `build_loop_blend.py`, absent = Lake Murray's call), and `grid_crop_m` dropped for `terrain.tiers` over the box.
  3. Connector decks built as their own object (not `1ROAD`) so engine-july's contact pin (`LAYER_WIN` 30 m, shelf 3 m +
     feather 6 m) does not raise ground to them; renamed to `1ROAD_deck_*` after the prep by a port step. Engine-july
     itself is Lake Murray's and does not change.
  4. Gores: the ramps ↔ line through `trim_connectors` (hosts = the line + `route.divided_connectors` carriageways),
     measured against `verify_mouths`; a gore tool only if the T-mouth rule fails at 2-5°. Any change to
     trim_connectors / mouth_weld / weld_mouths_blend is opt-in and listed for the Sand Creek branch's merge.
  5. Barriers on every carriageway edge (the 1WALL rule drive_test credits), dead-end stubs (`author_stubs_blend`).
  6. Deck heights from runbook 0080-2.

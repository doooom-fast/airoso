---
id: 0080
title: The San Diego freeway network on Lake Murray's engine (`tracks/san-diego-freeway-lm`)
date: 2026-11-05
track: san-diego-freeway (port: san-diego-freeway-lm)
routed: project (the port) + engine (opt-in, freeway-only keys)
status: in-progress — the map; phase 1 (the line) building
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

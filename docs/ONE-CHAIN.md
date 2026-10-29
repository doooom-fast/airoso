# One chain, one name set — the fleet rebuild and consolidation plan

*Drafted 2026-10-28 from Kevin's asks of that day, in his order: "What built San Diego 0.19.1? We need
to rebuild every other track in this system. And delete every other system that we have, because I keep
getting confused and we need to name them correctly in a set." · "Rebuild all four with the Lake Murray
chain." Ledger: [0060](../fleet/feedback/0060-engine-era-tracks-look-terrible-rebuild-through-the-ship-chain.md).*
*Status: **decided 2026-10-28** — Kevin answered every row (§6). The chain work for the first four tracks is in this
change; the retirements run as their own PRs; nothing is deleted by this document itself.*

## 1. The one system

**A track is built by the chain and by nothing else.** `tools/ship_track.sh <track>`, driven by
`tracks/<track>/ship.json`, in five phases on the Windows box:

| Phase | What | Owner |
|---|---|---|
| **draft** | the engine, as a draft only: `gps` or `aerial` → `elev` → `project` → (`widths`) → `mesh` → **`underlay`** into `loop.blend` (`GEN_*`) | engine (`scripts/`) |
| **author** | hand and scripted authoring in `loop.blend`, `AUTH_*` collections the engine never touches (REALISM §4): mouths, medians, kerbs, banking from lidar, walls, signs from `signs.json`, lamps, race furniture, dressing | Kevin + Claude in Blender (`tools/author_*_blend.py`) |
| **prep · split** | `scripts/ac/build_kn5_loop.py`, `tools/split_exports_blend.py` | engine |
| **ship** | export (AC add-on) → AI draft → `verify_kn5` → gate OBJ → track folder → map → (trees) | engine |
| **gate** | `drive_test` → `audit_mesh` → `kn5_ground_check` (+ the race gates) on the **built** kn5 (L5) | engine; Kevin's seat is the verdict (REALISM §2 Job 3) |

Lake Murray 0.19.1 came out of this chain's San Diego form, `tools/ship_sd.sh`. Until 2026-10-28 the
general form stopped at "no blend yet" for every other track; the underlay now exists
(`scripts/blender/underlay.py`) and the first four tracks have their `ship.json`.

**What the engine is, from now on:** the draft steps and the gates. Nothing under `scripts/` produces a
track. `scripts/build.sh` as a complete pipeline is retired by this plan (row 1 below).

**The chain's frame (2026-10-29, ledger 0060).** The prep imports the draft's local (E, up, N) as Blender
(E, N, up) and the exporter writes kn5 (E, up, −N): geographically right with **no mirror and no yaw** — Lake
Murray 0.19.1 is `mirror_x: false`, `true_north_rotation_deg: 0`. The `mirror_x: true` + `180` that every
V1-era config carries were the V1 OBJ program's own import convention (`(x, −z, y)`) and its sun fix: through
this chain they ship a **mirrored** track (every turn the wrong way) with the sun 180° off, every gate
self-consistent and blind to it. `tools/ship_track.sh` refuses that frame before any copy; a track coming to
the chain sets both (and flips the sign of any banked `road_profile` camber, `scripts/geometry/profile.py`).
The first four tracks were set on 2026-10-29; IMI, Pueblo, Aspen, Grand Junction, Pikes Peak, Second Creek
still carry the V1 frame and will be refused until their turn.

## 2. Every other system, and what happens to it

Legend: **RETIRE** = delete after its last dependent is gone (the row says which); **KEEP** = part of
the one system; **HISTORY** = move under `docs/history/`, never run; **DECIDE** = Kevin's call.

| # | System | What it is | Used by | Disposition |
|---|---|---|---|---|
| 1 | `scripts/build.sh` (stages `gps elev project mesh env blend kn5 pack`) | the V1 pipeline: a complete track from data, furniture included | every engine-era track folder; the four builds of 2026-10-28 | **RETIRE** the `env blend kn5 pack` stages now (they are what made the four look terrible); the `gps elev project mesh` stages stay as the chain's draft steps. Replace the script with `scripts/draft.sh` = exactly those steps, or delete it and let `ship_track.sh --draft-only` be the draft runner |
| 2 | `scripts/environment/build_env.py` + `signs.py`, `props.py`, `buildings.py`, `treefx.py`, `zones.py`, `make_*` | V1 generated furniture (signs at every junction, props, baked trees, highways) | row 1's `env` stage | **RETIRE** after the four ship through the chain. What authoring still wants from them (OSM building footprints, lamp positions, zone bins) is already ported into `tools/author_*_blend.py` / `make_treefx`; anything missing is ported, not kept running |
| 3 | `scripts/ac/build_kn5.py` (OBJ → scene) + `scripts/ac/kn5_write.py`, `kn5_native.py` | the V1 kn5 program and the native kn5 writer | row 1's `blend`/`kn5` stages; `KN5_WRITER=native` | **RETIRE** now. V3-PLAN: "do not write kn5 generators". The chain's prep is `build_kn5_loop.py`; the exporter is the AC add-on |
| 4 | `scripts/build_loop.sh` | the Mac loop-blend pipeline (prep → kn5 → verify → pack) | nothing since `ship_track.sh` | **RETIRE** now; `ship_track.sh` is its superset |
| 5 | `scripts/build_network.sh` + `scripts/geometry/build_network_mesh.py` + `build_network_env.py` | the freeroam NETWORK builder (the 223 km San Diego freeway network, `san_diego_freeway`, still a published zip) | the freeway network track | **DECIDE.** (a) the freeway network is a track like any other and gets a `ship.json` + underlay (a network draft is a bigger OBJ, the chain's tiling copes); or (b) it is retired from the catalog. Default: (a), last in the rebuild order |
| 6 | `tracks/san-diego-lake-murray/scripts-v021/` (the quarantined loop assembler) + `engine-july-snapshot/` (the pinned prep/exporter) + `tools/ship_sd.sh` | San Diego's chain of record: three code bases pinned by `test_ship_sd_chain.py`, `test_engine_july_snapshot.py`, `test_v021_*` | Lake Murray, every ship | **KEEP until** `ship_track.sh san-diego-lake-murray` on airoso's engine (draft via `underlay`, prep via airoso's `build_kn5_loop.py`) rebuilds Lake Murray and Kevin's seat says it is no worse than 0.19.1. Then `ship_sd.sh` becomes the two-line shim V3-PLAN P1 allowed, and both pinned copies become HISTORY. This is the last migration and the only one that can regress the track Kevin drives |
| 7 | `scripts/scs/` (truck-sim importer) | SCS → centreline, stubs for the external tools | nothing | **RETIRE** now (docs/scs-to-ac-plan.md → HISTORY) |
| 8 | `scripts/game/` + `projects/gala-seed/` | the seed export owed to the game *1978* (k10-1978 `PIPELINE_BRIDGE.md`) | k10-1978 | **KEEP** (external contract); move `projects/gala-seed/` to `contracts/gala-seed/` so `projects/` can go |
| 9 | `projects/` (11 dirs) | stale duplicates of tracks, retired concepts, two fixtures, the seed | the two fixtures by tests | **RETIRE** now: fixtures → `tests/fixtures/`, gala-seed → row 8, the rest deleted (registry `engine_projects` already says "stale duplicate" / "retired concept") |
| 10 | `tracks/imi_motorsports/`, `tracks/san_diego_lake_murray/`, `tracks/sand_creek_raceway/` (62 MB of committed kn5 + track folders) | engine-era BUILT outputs committed as "git-pullable installs" | nothing (installs come from the chain; downloads from Releases) | **RETIRE** now. Builds are never committed again; the public zips live on the release home (docs/ORG-CONSOLIDATION.md) |
| 11 | `fleet/cli.py` `status` / `build` / pins / `fleet/trains/` / `fleet/MIGRATION.md` / `registry.json` `repos[]` beyond airoso | the multi-repo control plane (pins, trains, shadowing) | nothing: one repo | **RETIRE** the multi-repo parts (CLAUDE.md already calls them obsolete); **KEEP** `feedback`, `lint`, `tracks` (discovery), DEFINITION-OF-DONE, GATES-CHANGELOG. `MIGRATION.md`, `trains/` → HISTORY |
| 12 | `scripts/capture/`, `scripts/trace/`, `scripts/aerial/`, `scripts/gps/`, `scripts/elevation/`, `scripts/geometry/` (ribbon, mesh, drive_test, audit), `scripts/modkit/` | data front-ends, the draft, the gates and inspectors | the chain | **KEEP** — this *is* the engine |
| 13 | `tools/blender-bridge/` | the live Claude↔Blender bridge | authoring | **KEEP**; REALISM §4 wants it promoted to `scripts/blender/live_*` |
| 14 | docs: `V1-AUTOPSY.md`, `V2-OPERATING-MODEL.md`, `HANDOFF.md`, `PLAN.md`, `environment-plan.md`, `scs-to-ac-plan.md` | the record of the two failed generations and their plans | readers | **HISTORY** (`docs/history/`), each with a one-line header saying what superseded it. `V3-PLAN.md` stays the plan of record; `PRO-KN5-CONSTRUCTION`, `ROAD-CONSTRUCTION`, `JUNCTIONS`, `RACE-FURNITURE`, `PUBLISHING`, `TREEFX-FORMAT`, `RALLY-CONVENTIONS`, `STAGE-SOURCING` stay (they describe the chain's authoring) |

## 3. The name set

One rule each; everything else follows from them.

| Thing | Name | Rule |
|---|---|---|
| The system | **the chain** | `tools/ship_track.sh` + `tracks/<track>/ship.json`. Not "V3", not "the engine", not "prodrive". The engine is the chain's draft steps and gates |
| The repo | **airoso** (`doooom-fast/airoso`) | one repo; every other code repo is history (docs/ORG-CONSOLIDATION.md) |
| A track's folder | `tracks/<place>/`, lowercase, hyphens | the place, never the brand: `milford-road-course`, `exotics-racing-lv`, `sand-creek`, `high-plains`, `san-diego-lake-murray`, `lookout-lariat`, `rally-dragon-tail-gravel` |
| A track's slug | `track.config.json` `slug`, lowercase, underscores | the folder name with `_`; it names every kn5 (`<slug>.kn5`, `<slug>_race.kn5`, `<slug>__<layout>.kn5`) |
| The installed folder | `track.config.json` `install_folder` = the slug | `content/tracks/<slug>`; no `_v3`, no `_ai` suffixes (the Lake Murray install `san_diego_lake_murray_v3` is renamed to `san_diego_lake_murray` when row 6 lands) |
| The series | `ui_series` = **"doooom <Region>"** | Kevin, 2026-10-28: **"K10 is gone. doooom."** `doooom San Diego`, `doooom Colorado`, `doooom Michigan`, `doooom Nevada`. Content Manager shows "doooom <Region> - <Layout name>" (`ship.json` `ui_name_prefix`). SD's "K10 - San Diego (V3)" becomes "doooom San Diego" when §2 row 6 lands; every other `K10` string in the repo goes with the retirements |
| Layouts of a street network | **`<Area> Free Roam`**, **`<Area> Speedway`**, **`<Area> Speedway Reverse`** | Kevin's rule (ledger 0054): the open network; the race loop clockwise; anticlockwise. Ids stay stable (`street`, `race_cw`, `race_acw`) so setups survive |
| Layouts of a circuit | **`<Track>`** and **`<Track> Reverse`** | ids `full`, `reverse`. A circuit that gets a race-furniture version calls it `<Track> Race` |
| Rally stages | **`<Stage> (Gravel)`** / **`<Stage> (Tarmac)`** as two tracks | L8: surface physics is per track |
| A version | `track.config.json` `version`, per track, never reset | the chain keeps counting from where the engine era left off (Milford 0.2.0, Exotics 0.2.0, Sand Creek 0.28.0, High Plains 0.68.0, Lake Murray 0.20.0); the release notes say "chain" the first time. Resetting to 0.1.0 would collide with the retired installs |
| A release | `<slug>_v<version>.zip` on the public release home | docs/PUBLISHING.md |
| The workshop | `C:/Users/Owner/Documents/k10-workshops/<track>/project` | outside airoso (the sync rails). SD's `k10-sd-v021` moves there when row 6 lands |
| A track's public title | `track.config.json` `name` | the place, or Kevin's title for it: **Nevada Nights** is the Exotics Racing LVMS circuit (Kevin, 2026-10-28; the Exotics Racing mark is registered). Folder and slug stay place-based |
| Generations | **not a name** | "V1 / V2 / V3", "engine-july", "v021", "prodrive-ac-builder", "k10-track-agents" are history. They stay in `docs/history/` and in the ledger as dates, nowhere else |

## 4. The rebuild, in order

Every track enters at T0 **through the chain**; its engine-era tier is withdrawn (DEFINITION-OF-DONE). The
shape of the work per kind:

| Kind | Draft | Authoring the seat will ask for first |
|---|---|---|
| circuit_port | `gps` (from_track / OSM raceway) or `aerial`, `elev`, `project`, `mesh`, `underlay` | kerbs where the real ones are, banking from lidar sections (never curvature), pit lane, the buildings that make the place, run-off |
| street_port | `gps` (OSM route), `elev`, `project`, `widths`, `mesh`, `underlay` | junction mouths (JUNCTIONS.md), medians, lamps, signs from `signs.json`, the race corridor (RACE-FURNITURE.md) |
| fictional_street_circuit | as street_port, from the KML | the race furniture is the track |
| rally_stage | `gps`, `elev`, `project`, `mesh`, `underlay`; `natural_ground`; two tracks (gravel, tarmac) | trees, rock cuts, nothing urban (REALISM §6) |

| # | Track | Kind | Why here | State |
|---|---|---|---|---|
| 1 | Exotics Racing LVMS | circuit_port | smallest, flat, one banked corner; draft data committed | `ship.json` done; chain run owed |
| 2 | Milford Road Course | circuit_port | the hill course; draft data committed; Kevin's "build Milford first" | `ship.json` done; chain run owed |
| 3 | High Plains | circuit_port | the "road signs" case; OSM raceway cycle | `ship.json` done; chain run owed |
| 4 | Sand Creek | fictional_street_circuit | KML route; `full` first, `reverse` when its start is declared | `ship.json` done; chain run owed |
| 5 | Lookout Lariat | street_port | the plan exists (`V3-PLAN.md`, shelved 2026-10-12); add `mesh` before `underlay` | plan |
| 6 | Dragon Tail, Under the Dragon (gravel + tarmac) | rally_stage | four tracks, two surfaces | configs only |
| 7 | Second Creek | circuit_port | geometry **fabricated** (registry `fidelity`). **Kevin: re-source.** First step: the NAIP export of the site on the Windows box into `source/`, then `aerial` → the chain | owed |
| 8 | San Diego freeway network | street_port (network) | **Kevin: rebuild, by an agent.** The network draft (`build_network_mesh`) becomes draft steps of the chain and the 223 km network gets its own `tracks/san-diego-freeway/` + `ship.json` | agent spawned 2026-10-29 |
| 9 | Lake Murray on airoso's engine | street_port | §2 row 6: the last migration, judged against 0.19.1 in the seat | after the four |
| 10 | IMI, Pueblo, Aspen, Grand Junction, Pikes Peak | circuit_port | **Kevin: at the end.** Configs exist; Grand Junction and Pikes Peak were "rough everywhere, mechanism not found" under V1 — the chain's prep is the first new thing to try on them | configs only |

## 5. What this change does, and what waits for Kevin

**In this change:** the underlay; the chain's `aerial` and `mesh` steps; the gps stage dispatching on
`source.type`; four `ship.json`; the four tiers withdrawn; ledger 0060; the dossiers' §11 and
`RESEARCH-HANDOFFS.md` rewritten to the chain; this plan. Nothing deleted, nothing renamed.

**Waits for Kevin:** every RETIRE / HISTORY row in §2 (one PR per row, each removable on its own), the two
DECIDE rows, the name set in §3 (the SD rename in particular), and the order in §4. Say "approved" per row or
change it; the rows then run as small PRs, the deletions last.

## 6. Kevin's answers, 2026-10-28

| § | Row | Answer |
|---|---|---|
| 2.1 | retire `build.sh`'s `env blend kn5 pack` stages | **yes** |
| 2.2 | delete the V1 furniture generators after the four ship | **yes** |
| 2.3 | delete the V1 kn5 program and native writer | **yes** |
| 2.4, 2.7 | delete `build_loop.sh`; delete the SCS importer | **yes** |
| 2.5 | the freeway network | **rebuild through the chain, by an agent** |
| 2.9 | delete `projects/` (seed → `contracts/`, fixtures → `tests/fixtures/`) | **yes** |
| 2.10 | delete the three committed engine-era track folders | **yes** |
| 2.11 | retire the multi-repo control plane | **yes** ("if you say so") |
| 2.14 | V1/V2 docs → `docs/history/` | **yes** |
| 3 | the series | **"K10 is gone. doooom."** |
| 3 | install folder = slug, no suffixes; circuit layouts "<Track>" / "<Track> Reverse"; versions keep counting | **yes**, **yes**, **yes** |
| 3 | Exotics Racing's public title | **Nevada Nights** |
| 4 | Second Creek | **re-source** from imagery |
| 4 | order | the four → Lariat → rally → Second Creek → freeway → Lake Murray migration → **IMI / Pueblo / Aspen / Grand Junction / Pikes Peak last** |
| — | satellite road textures as an authoring-stage tool; NAIP + own drone imagery the shippable sources | **yes** |
| — | the GitHub org (docs/ORG-CONSOLIDATION.md) | fresh `track-releases` repo; the six unknown repos are not current (archive); delete `prodrive-ac-builder`; drop the `k10-` prefixes |

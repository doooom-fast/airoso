---
id: 0047
title: "Actually make it three versions: the regular one, and then the two tracks" — the open street loop plus two one-way race layouts, barrier-split on the wide roads, both starting on Alvarado
status: open
scope: tracks/san-diego-lake-murray (proof; layouts[], declared start, race furniture); engine scripts/ac/{build_kn5_loop,build_spawn_kn5,track_folder,verify_kn5,write_ai_line}.py + scripts/geometry/{median_zone,audit_mesh,drive_test}.py + new tools/ (barrier bands, race-furniture authoring, multi-layout ship); standard fleet/LAWS.md L8 wording + fleet/STANDARDS.md S6 (archetype is per-track, the race overlay is per-layout)
layer: project + engine + standard
train: -
---

## Status

**Open — designed, built as tools, gated, dry-run on a scratch copy; NOT shipped** (2026-10-11).
Everything below the Symptom was measured 2026-10-10; the design that followed is recorded in
"Decisions and the built design" and the ship chain is wired in `tools/ship_sd.sh` (the three-version
chain is now the only chain). **No kn5 has been exported, the hand-edit surface
`tracks/san-diego-lake-murray/loop.blend` has not been touched, the installed track is unchanged.**
One `bash tools/ship_sd.sh` run builds all three versions — but not before Kevin answers Q1, Q2, Q6
and Q7 below (they change authored geometry; the defaults are encoded and will ship if he says
"defaults"). The L8 wording amendment waits for Q9; nothing in `fleet/LAWS.md` is edited. The
original 2026-10-10 status, interpretation and open questions are superseded by the sections at the
end; the Evidence and Diagnosis stand.

**Fix round 2026-10-11 (still not shipped: nothing exported, synced from a real run or installed).**
The race strips would have shipped as building concrete: Lake Murray's `pbr.network_walls: true`
reskins the generic `1WALL` key and `1WALL_race_*` fell through to it (the 00:47 dry run's prepped scene
bound `building_diffuse/normal.jpg` on 29/29 strip materials). `scripts/ac/pbr.py` now carries its own
`1WALL_RACE` (concrete_barrier_*) and `1KERB_RACE` (kerb_diffuse.png) rows ahead of the generic ones,
mirrored into engine-july (both md5 `d3bbe940…`); re-measured on a scratch `--skip-blend --dry-run`:
29/29 concrete_barrier, 7/7 kerb stripe. Grid stagger 1.4 → 1.0 m (outer column 0.48 m off the strip
face, was 0.08) with spawn clearance a HARD fail below 0.30 m (`verify_race` F now re-measures every
`data/dummies_<id>.json`, plus the author tool and `barrier_bands`); new `verify_race` G: lamp masts vs
the strips, minimum margin 2.36 m, none inside. The street AI defaults to the V3 draft (`STREET_AI=july`
is opt-in; the July line is a July `write_ai_line` draft, never an in-game recording). `SHIP_PROJ` runs
every step on the absolute `$PROJ` and never syncs back or installs from a scratch copy; `pack_release`
rasterises every `ui/<id>/preview.svg` and the full package's CREDITS/LICENSES name the K-rail;
`place_signs` reads every `dummies_<id>.json` (the 18 approved posts did not move: pure placement
0.000 m, built-mesh march within 0.006 m of the approved coordinates). The build-of-record files
engine-july runs are snapshotted in `tracks/san-diego-lake-murray/engine-july-snapshot/` with a drift test.

## Symptom (Kevin, 2026-10-10, verbatim, in order)

> "I will also want two layouts, with Barriers making tracks out of north/south kind lanes. Place
> the starting line on Alvarado for both, just facing a different direction on the opposite side of
> the road. With Barriers between directions, leading up to medians but not on them"

> "The barriers are for wide roads, Alvarado should be the entire street"

> "Actually make it three versions: the regular one, and then the two tracks. The tracks will get
> additional race curbs and barriers along the inside of the sidewalks"

## Working interpretation — INTERPRETATION, not Kevin's words; confirm before design

- **Version 1 = today's open street loop** (`layouts[0] full`), untouched except possibly its start
  (open question 3).
- **Versions 2 and 3 = the same loop as a one-way race track, one per direction of travel.** On
  **wide** roads each layout is confined to its own carriageway by a **centre barrier chain** that
  runs **island-nose to island-nose across every junction gap and never on a median island**
  (the island already carries its own curb, planting and guardrail — 0037). "North/south kind lanes"
  is read as *the two directions of travel*, not compass bearings.
- **Narrow streets (Alvarado, the side streets) stay full-width with no centre barrier** — "Alvarado
  should be the entire street".
- **Start/finish on Alvarado for both race layouts**, one line, each grid in its own lane on its own
  side of the road, facing its direction of travel.
- **Race layouts also get racing kerbs and barriers along the road side of the sidewalks** ("along
  the inside of the sidewalks" = the pavement lip, inside the sidewalk curb), on every street
  including Alvarado.
- **Wide threshold = 17 m** (measured below: it is the width at which a carriageway beside a 0.67 m
  barrier still holds two lanes).

## Evidence

Frame throughout: `C:/Users/Owner/Documents/GitHub/k10-sd-v021/project/data/centerline.local.json`
(the build-of-record workshop; `tracks/san-diego-lake-murray/data/` mirrors it via `ship_sd.sh`) —
4,499 vertices, 13,489.5 m, 2.998 m spacing, forward order = Alvarado → College → Navajo → Jackson →
Lake Murray Blvd, v0 at the turn onto Alvarado (6, −1662). Installed artifact: `san_diego_lake_murray_v3`
kn5 of 2026-10-09 10:11.

**1. The layout law and what every reverse-capable reference actually ships.**
`CLAUDE.md` "Layouts": *all layouts share one kn5 model and differ only in AC configuration — never
rebuild the mesh per layout*; the one exception is surface physics (two installable tracks).
`fleet/LAWS.md:136-143` L8 says the same. Measured on disk (`grep -a` for dummy names, 2026-10-10):

| track | base kn5 | per-layout kn5 (loaded only by that `models_<layout>.ini`) | AC_START / AC_PIT / AC_TIME / HOTLAP in base | in per-layout |
|---|---|---|---|---|
| deepforest_raceway | 353.5 MB | `normal.kn5` / `reverse.kn5` 10.1 MB each | 0 / 0 / 0 / 0 | 40 / 40 / 16 / 2 |
| oregon_raceway_park | 154.4 MB | `_clockwise.kn5` / `_anticlockwise.kn5` 105.6 MB + `_markers.kn5` 0.7 MB | 0 / 0 / 0 / 0 | 40 / 40 / 12 / 2 (markers 0) |
| rt_california_highway | 146.0 MB | `100.kn5` (normal) / `001.kn5` (reverse) / `000.kn5` (roamfree) 65-68 KB; `_barr2.kn5` only in normal + reverse | 0 / 0 / 0 / 0 | 32 / 32 / 4-12 / 2 |
| pacific_coast_hwy | 298.3 MB | `layout_northbound.kn5` 125 KB / `layout_southbound.kn5` 69 KB / `layout_cruise.kn5` 177 KB | 0 / 0 / 0 / 0 | 100 / 52 / 140 starts, 2 hotlap |

**The main kn5 never carries a grid; every direction-capable reference ships a nodes-only (or
nodes + direction furniture) kn5 per layout, and rt_california adds a geometry kn5 (`_barr2`) to two
of its three layouts.** So "one shared kn5" in practice means *one shared road*; layouts add, they do
not replace. The reconciliation this entry proposes — shared main kn5 + one race-furniture kn5 listed
only in the two race layouts' `models_<layout>.ini` + a nodes-only spawn kn5 per layout — is exactly
that pattern. The engine already has half of it: `scripts/ac/build_spawn_kn5.py:1-13` ("keep the main
kn5 free of spawns and ship a small per-layout kn5"), `scripts/ac/track_folder.py:405-417` (loads
`build/<slug>__<layout>.kn5` as `MODEL_1` when `data/dummies_<layout>.json` exists),
`scripts/ac/verify_kn5.py:150-165` (checks each spawn kn5's dummies sit on the shared road). None of
it runs on the loop path (see Diagnosis).

**2. Widths — which streets are "wide".** Run-length of `widths_m` (2026-10-10):

| vertices | width | length | what it is |
|---|---|---|---|
| v0-14, v4483-4498 | 17.0-27.5 m | 85 m | the seam box at the Alvarado / Lake Murray Blvd corner |
| v15-24 | 16.6 → 13.4 m taper | 30 m | into Alvarado |
| **v25-723** | **13.0 m flat** | **2,097 m** | **Alvarado Road** — the only narrow street on the loop |
| v724-760 | 13.1 → 16.5 m taper | 108 m | Alvarado → College hairpin approach (C3's site, verts 760-770) |
| **v761-4452** | **17.0-32.5 m** (17.0 between junction flares) | **11,079 m** | College, Navajo, Jackson, Lake Murray Blvd (route order; the Jackson/LMB boundary is not recorded in the data) |
| v4453-4482 | 13.5-16.4 m | 90 m | Lake Murray Blvd on the I-8 overcrossing — arc 13,357-13,444 m, inside the declared bridge span 13,318.7-13,463.4 m (`bridge.spans.auto.json`) |

Totals: wide (≥ 17 m) 11,164.5 m; 13.5-17 m 227.8 m; ≤ 13 m 2,097.2 m. Per carriageway beside a
centre barrier of half-width 0.335 m: **17.0 m → 8.16 m clear = two 3.5 m lanes + 1.2 m; 13.0 m
(Alvarado) → 6.17 m clear = one lane and a shoulder**, which is the measured reason "Alvarado should
be the entire street" and why 17 m is the wide threshold. Alvarado's `widths_m` is 13.0 on every one
of v25-723, so the rule has no ambiguity there; the two taper stretches are where it must decide
(open question 2).

**3. Islands and junction gaps — where the chain stops.** `median_bands.json` `island_w_by_vertex`
(2026-10-09, five islands):

| island | vertices | length | max half-width × 2 |
|---|---|---|---|
| College 1 | v846-1073 | 228 verts | 7.0 m |
| College 2 | v1096-1258 | 163 | 7.0 m |
| College 3 | v1374-1487 | 114 | 7.0 m |
| Navajo 1 | v1540-1739 | 200 | 6.92 m |
| Navajo 2 | v2183-2297 | 115 | 5.93 m |

Island total 2,473.7 m. Gaps between islands on wide road, where the chain must run *through* the
junction: v1074-1095 (71.2 m — the College/Del Cerro 4-way), v1259-1373 (349.7 m), v1488-1539
(155.3 m), v1740-2182 (1,335.2 m, undivided Navajo); plus the undivided wide runs v761-845 (248.6 m)
and v2298-4452 (6,454.2 m). The island ends are authored as noses: `tools/author_median_blend.py:35-36`
(`NOSE_HALF 0.25`, `NOSE_VERTS 3`), set back `MOUTH_SETBACK_M 18.0` from every mouth
(`tools/divide_connectors.py:18,39,115-118`); the island's own guardrail (`GUARDRAIL → 1WALL_guard`,
only on runs ≥ `BARRIER_MIN_M 120`, `:38,191-209`) stops `NOSE_VERTS` short of each end. A chain that
ends at the nose therefore meets an island whose first 3 verts (~9 m) are a 0.25 m-wide taper — that
joint is a geometry the authoring tool has to close deliberately (nose cap), not something that
falls out of two bands.

`mouths.json` (2026-10-09): the mainline has three mouths — Del Cerro Blvd at **v1085 (side +1)** and
**v1086 (side −1)**, 22.9 / 21.8 m wide, both inside the College island gap v1074-1095; and
`medium#2+0` at **v4424 (side −1)**, 10 m, on Lake Murray Blvd 65 m before the seam box. Side +1 is
*left of forward travel* (`tools/gap_mouths_blend.py:12-14`). So with a centre chain, in each race
layout one Del Cerro mouth is across the barrier (unreachable) and one opens off the driven lane, and
the v4424 mouth opens off the forward layout's lane only (open question 1).

**4. The start line — Alvarado v300.** Straightness measured on the centreline: **v250-375 is 375.7 m
with a 375.7 m chord, heading range 1.70° (mean −78.6° = WNW), grade 0.89 % (y 10.53 → 7.17)** — the
straightest 376 m on the loop. The proposed line at **v300 (−761.98, 8.84, −1276.10), width 13.0 m**:
grid A at **v291 +3.25 m right of forward travel → (−734.79, 9.12, −1278.15), yaw 281.6°**, 27.0 m
before the line in its direction; grid B at **v310 −3.25 m (right of reverse travel) → (−792.10, 8.56,
−1273.56)**, 30.1 m before the line in its direction, facing 101°. v291-310 heading range 0.52°, grade
0.98 %. ±3.25 m is the lane centre of a 13.0 m street (6.5 m half, no barrier). An 8-car grid at
`PIT_SPACING_M 7.0` (`tools/set_start_blend.py:27`) reaches ~56 m behind each grid slot — still
inside v250-375 for both directions.

**5. Today's shipped start complex is on Jackson, and its grid is 5.7 km from its own line.** Parsed
out of the installed kn5 (`verify_kn5._parse`, kn5 frame, z mirrored):

| node | kn5 position | centreline | street |
|---|---|---|---|
| `AC_TIME_0_L/R` (start/finish) | (1733.1, 92.6, −780.9) / (1726.3, 92.6, −762.0) | **v2986**, arc 8,960 m, width 20.2 m | **Jackson Drive** |
| `AC_START_0` = `AC_HOTLAP_START_0`, `AC_PIT_0-7` | (−1428.7, 41.1, 568.3) … (−1448.2, 38.7, 625.6) | v1078 +6 m → v1101 | College Ave at the Del Cerro mouth |
| `AC_TIME_1`, `AC_TIME_2` | v4487 (seam box), v1487 (College) | | |

Why: the line is **derived**, not declared — `scripts/geometry/dummies.py:73-96` scans for the
straightest, flattest 260 m window (score = worst 4-vertex heading change + 300 × grade) and puts the
line 45 + 30 m into it; on this centreline that window is on Jackson. The grid is elsewhere because
`start_positions.json` `active: "0033-college-del-cerro"` (vertex 1078, +6 m) — the per-issue debug
spawn Kevin asked for on 2026-08-20 — moves `AC_START_0`/`AC_HOTLAP`/`AC_PIT_n` but not `AC_TIME_0`
(`tools/set_start_blend.py:66-90`). The declared-start plumbing already exists: airoso's
`scripts/ac/build_kn5_loop.py:798-802` passes `cfg.get("start_arc_m")` to `place_dummies` with the
comment *Kevin: "i prefer starting on alvarado toward college"*; but **`track.config.json` has no
`start_arc_m`**, and the build-of-record `ship_sd.sh` runs the engine-july copy
(`C:/Users/Owner/Documents/GitHub/engine-july/scripts/ac/build_kn5_loop.py:661`), which calls
`place_dummies(cl, widths, n_sectors=3, n_pits=n_pits)` with no start parameter at all. The workshop's
`data/dummies.json` (10:49) shows the prep's own placement (grid at v2976) while the airoso mirror
(10:55) and the installed kn5 (10:11) show set_start's — two files, two answers, neither on Alvarado.

**6. The barrier asset and the chain's size.** `assets/models/concrete_barrier_4m.obj` ("Concrete
Barrier 4 MTS", `assets/README.md:26`): **249 verts, 183 faces, 0.670 m wide (x ±0.335), 1.202 m
tall, 4.04 m long (z −4.000 … +0.040)** — 4.04 m pitch. Chain length = wide minus island =
**8,690.7 m → 2,151 modules** (the workflow's earlier "~2,127 for 8.5 km" is the same figure before the
taper stretches were classified; junction gaps add nothing because the chain runs through them).
As visible geometry that is ~536k verts (9 meshes under the 65,535 cap, L7). The reference pattern
keeps visuals and physics apart: rt_california ships `_barr.kn5` 132.3 MB with **0** `1WALL` and
`_wal.kn5` 2.4 MB with **85** `1WALL`; PCH ships `rails.kn5` 42.1 MB with 0 and `collision.kn5` 1.4 MB
with 5 — **a swept visual strip plus an invisible tall `1WALL` collider sheet**, which is also what
makes a 2,151-module chain cheap to collide against. The engine already instances this exact OBJ along
runs with a seat-to-surface sampler and both-ways faces (`scripts/geometry/build_mesh.py:2632-2733`,
`scripts/environment/props.py:48-134`, `props.concrete_barriers` from the `street_circuit` archetype)
— on the engine mesh path, not on the Blender loop path this track uses.

**7. The AI-line rule.** `docs/HANDOFF.md:250-255`: the correct AI spline is recorded in-game; a
generated one "loads but the AI can't follow properly". `scripts/ac/write_ai_line.py` can write a
reversed draft (`--direction reverse`, 0026) and checks grid alignment against `dummies.json`
(`:165-182`), but has **no lateral-offset option** — a race layout's line is the lane centre
(±3.25 m on Alvarado, ±4.1 m on a 17 m road beside the chain), not the road centre. A reversed,
lane-offset draft from the **built** centreline (`gate_centerline.json`, L5) is allowed as a draft;
per-layout in-game recording is the end state. Today `ship_sd.sh` copies the July reference's
`fast_lane.ai` into the single `ai/` (`tools/ship_sd.sh` install block) — a July `write_ai_line` DRAFT,
generated, never recorded in game (ledger 0023: "Lake Murray and IMI regenerated and reinstalled" by the
writer) — and that line is the road centre in forward order and is wrong for both race layouts.

**8. What the gates know today.**
- `scripts/geometry/drive_test.py:390-399`: ten wheel paths at symmetric offsets
  `(±(w/2−0.5), ±w/3, 0)`, no concept of direction (no `reverse`/`direction` anywhere in the file);
  the obstruction disc sits on the centreline (`:477-490`) except on island stations, where 0037
  moved it into the driven lane. A centre chain makes the 0.0 and ±w/3 paths and the disc hit
  `1WALL` at every wide station. Note `:395`: *"negative offsets are the right-hand side here"*,
  while `tools/set_start_blend.py:47-50` and `dummies.py` `offset(i, +half)` = L use positive = right
  / left respectively — three sign conventions for one lateral axis (the 0015 class).
- `scripts/geometry/audit_mesh.py:279-305` check **D** ("walls sitting on a road"): every `1WALL` vert
  within 1.2 m of the main carriageway counts, exempt only on the declared island band
  (`median_zone.py`, band + 0.6 m). The chain's ~536k visual verts (or the collider's ~5.8k) would all
  count. Today's D is in the hard total (`:684`).
- `scripts/geometry/median_zone.py:1-29` is "the one place that knows where the island is" — the
  natural home for "where the chain is".
- `drive_test.py:237,282,591-615`: `1WALL` groups go into the `obstacle` field, feed the
  furniture-seating gate (`floating_furniture`, **391 today**, already red) and credit guarded drops.
  The chain inherits both automatically.
- `fleet/GATES-CHANGELOG.md:1-15`: every threshold/exemption/wiring change gets an entry **in the
  same commit** — what changed, the measurement that justifies it, how it was proven; the 0037 entry
  (`:92-135`) is the model for "why an exemption is not a bypass".

**9. Config shape today.** `track.config.json` `layouts: [{id: "full", ai: "ai/full", uses_connectors: []}]`,
`archetype: "real_road"`. `scripts/config.py:62-90`: archetype is **per track**; `real_road` =
"NO racing furniture", `street_circuit` = "+ concrete barriers along the racing line + start/pit
furniture" (`fleet/STANDARDS.md` S6). `scripts/ac/track_folder.py:393-404`: `len(layouts) == 1`
selects the suffix-free folder (`models.ini`, `ui/`, `ai/`); more than one flips AC into multi-layout
mode (`models_<layout>.ini`, `<layout>/map.png`, `ui/<layout>/`, `<layout>/ai/`, `<layout>/data/`),
and `tools/make_map.py` writes one `map.png` in the kn5 frame (0038) at the root.

## Diagnosis — why today's build cannot be *configured* into three versions

1. **The loop path bakes the grid into the main kn5.** engine-july `build_kn5_loop.py:655-675`
   places one start complex and writes it as empties in the scene the exporter sends to the one kn5;
   `set_start_blend.py` then moves it in the blend. One grid per track, by construction. The per-layout
   spawn-kn5 machinery (evidence 1) exists for the network path and is **not running** on the loop
   path — a coverage gap, not new geometry.
2. **The race overlay is per-layout, and the engine's only switch for racing furniture is per-track**
   (archetype, evidence 9). Keeping `real_road` for the regular layout and adding barriers/kerbs for two
   others has no config expression today → `standard` (S6) before code.
3. **L8's wording forbids the reference pattern.** "Differ only in AC configuration" (CLAUDE.md) /
   "never rebuild the mesh per layout" (L8) — the second is right and stays; the first, read
   literally, bans the furniture kn5 that deepforest/ORP/rt_california/PCH all load per layout. The
   amendment is a sentence: *layouts share one road mesh; a layout may add kn5s (dummies, furniture),
   never alter or replace the shared one.*
4. **The gates have no lane and no direction** (evidence 8). Without lane-relative sweeps and a chain
   band, the race layouts fail D and drive_test everywhere the chain stands, and the only way to pass
   would be a bypass — the thing GATES-CHANGELOG exists to prevent.
5. **The start is derived, not declared** (evidence 5): the regular layout's line landed on Jackson by
   heuristic, the grid is a debug spawn, and the declared-start plumbing is in the wrong copy of the
   prep. Both race layouts need a declared start; the regular one needs Kevin's word.

No compensation pattern found: nothing downstream has been patched to hide a start or a barrier
problem. The one latent trap is the three lateral sign conventions (evidence 8) — a lane-relative
gate written in one and a grid placed in another puts the grid across the barrier. Fix by naming the
side (`driven_side`) rather than a sign, as `gap_mouths_blend` already does with `side ±1`.

## Fix — the 2026-10-10 design sketch (superseded by "Decisions and the built design" below; kept for the record)

**A. Config (project).** `layouts[]` gains per-layout `direction` (`forward` | `reverse`), `start`
(`{vertex, offset_right_m}` in the layout's own travel frame), `race_furniture` (bool), plus the
track-level rule `race.wide_threshold_m: 17.0`, `race.barrier_asset`. Proposed: `full` (forward,
start per open question 3, no furniture), `race_a` (forward, start v291 +3.25), `race_b` (reverse,
start v310 +3.25 in its own frame = −3.25 forward), both `race_furniture: true`. The line is one
`AC_TIME_0` at v300 in both race spawn kn5s (L/R swapped for the reverse layout).

**B. Barrier bands (tool, then engine).** `tools/barrier_bands.py` → `data/barrier_bands.json`,
per vertex: `centre_chain` (width ≥ threshold AND island_w == 0, with the chain ending at the island's
first non-zero vertex, i.e. at the nose), `edge_barrier_l/r` (every vertex, both sides, gapped at
mouths like `gap_mouths_blend`), `kerb_l/r` (same extent). Derived from `centerline.local.json` +
`median_bands.json` + `mouths.json` only; the rule parameters are config, the output is data the gates
read (L5: gates read the band to know what *should* be there, and measure the built OBJ for what is).

**C. Authoring in Blender (tool).** `tools/author_race_blend.py`, an additive layer in `loop.blend`
after `author_median_blend` and `gap_mouths_blend` (never a regenerate — the file carries hand edits):
`RACE_BARRIER_*` visual strip (the 4 m OBJ instanced, seated on the built road, ~536k verts split
under the cap), `RACE_WALL_*` → `1WALL_race` invisible collider sheet (2 verts per station, 1.2 m
tall), nose caps where the chain meets an island, `RACE_KERB_*` → `1KERB_race` along the pavement lip,
and the sidewalk-side `RACE_BARRIER`/`1WALL_race` runs; all in one collection so the export writes
them to a second kn5. `scripts/ac/export_kn5_addon.py:180-182` selects everything — it needs a
collection filter (or two exports: main scene without the race collection, race collection alone).

**D. Per-layout dummies and spawn kn5s (engine).** The loop prep stops baking `AC_*` into the main
kn5 when `len(layouts) > 1`; it writes `data/dummies_<layout>.json` per layout from `place_dummies`
on the forward or reversed centreline with the declared start and the lane offset; `build_spawn_kn5.py`
accepts the loop shape (`dummies_<layout>.json` present, no `layouts[].spawn` lon/lat); the
`start_positions.json` registry applies to `full` only. 0021 (grid slots) and 0016 (per-dummy yaw)
apply unchanged.

**E. AI drafts (engine).** `write_ai_line` gains `--offset-right <m>` (lane centre) and reads
`dummies_<layout>.json` for `grid_alignment`; a forward and a reversed lane-offset draft from
`gate_centerline.json` per race layout, `pit_lane.ai` = copy. End state per HANDOFF: recorded in-game,
one recording per race layout.

**F. Multi-layout ship (engine + tool).** `track_folder` already builds the multi-layout tree;
`models_full.ini` = main + `__full` spawn kn5, `models_race_*.ini` = main + race-furniture kn5 +
`__race_*` spawn kn5; `make_map.py` per layout; `ship_sd.sh` install block generalised (today it
copies the reference AI into the root `ai/`, which does not exist in multi-layout mode).

**G. Gates (engine; one GATES-CHANGELOG entry in the same commit).**
- `median_zone.py`: a `BarrierZone` from `barrier_bands.json` (band = 0.335 + 0.6 m laterally,
  ±2 m along), only where declared. Audit **D** exempts `1WALL_race` verts on the chain band; **K**
  exempts `1KERB_race` on the kerb band. Not a bypass: the chain's own correctness is gated by E
  (floating), drive_test `floating_furniture`, and the new check below; a track with no
  `barrier_bands.json` gets nothing.
- `drive_test --layout <id>`: walk the line in the layout's direction; paths lane-relative on the
  `driven_side` (from barrier face + 0.4 m to pavement lip − 0.5 m), obstruction disc centred in the
  lane; step/kink memory reset at chain ends like the island boundaries. New **`barrier_missing`**:
  at every station where the band declares a chain or edge barrier, probe for a `1WALL` top within
  the band — count, gate at **0**; plus continuity, any gap > one module (4.04 m) counts.
- `verify_kn5`: when `len(layouts) > 1` the main kn5 must carry **0** `AC_START`/`AC_PIT`; each
  `__<layout>.kn5` must carry ≥ `n_pits` `AC_START_n` (0021), every one on the layout's declared
  side of the chain band, facing within 25° of the centreline tangent in the layout's direction
  (0026's contract made a gate).

**H. Standards (first).** L8: add the "layouts may add kn5s, never alter the shared road" sentence.
S6: the archetype stays per-track; add `layouts[].race_furniture` as the per-layout overlay switch
with the `street_circuit` furniture set.

## Scope

- **Proof:** `tracks/san-diego-lake-murray` — the only track with a wide/narrow split, islands and a
  requested direction pair.
- **Consumers later:** `street_port` and `fictional_street_circuit` only (Sand Creek already has
  warning-run barriers from `build_mesh`; its `props.concrete_barriers` path must not change).
  `rally_stage` never (L11, one direction). `circuit_port` reverse layouts are the same D/F/G
  machinery with no chain — not in this entry.
- **Regression (must not move):** every single-layout track's `build/<slug>/` byte-identical
  (`track_folder` single path untouched); every track without `barrier_bands.json` gets identical gate
  numbers (zone `None`); Lake Murray's `full` layout gate numbers identical to today's
  (`drive_test.json`: severe 0, obstruction 0, soft_top 82, floating_furniture 391; audit K 169 / I 167
  / F 61) except where open question 3 moves the start.

## Verification — decided now, before anything is built

Measured on the built artifact (L5), before any drive:
1. `barrier_bands.json`: chain length 8,690 ± 30 m; **0** chain verts where `island_w > 0`; chain
   ends within one vertex of v845/846, 1073/1074, 1095/1096, 1258/1259, 1373/1374, 1487/1488,
   1539/1540, 1739/1740, 2182/2183, 2297/2298; **0** chain verts on v25-723 (Alvarado).
2. Race-furniture kn5: `1WALL_race` continuity max gap ≤ 4.04 m along the chain; module count
   2,151 ± 10; no mesh over 65,535 verts; `1KERB_race` top within 0.15 m of the road lip (L9, audit F).
3. Per-layout `drive_test`: `barrier_missing 0`, obstruction 0, severe 0 in each race layout's lane;
   `full` unchanged.
4. `verify_kn5`: main kn5 0 spawns; each spawn kn5 ≥ 8 `AC_START_n` on the declared side, facing
   its direction; `AC_TIME_0` at v300 in both.
5. `ui/<layout>/ui_track.json` × 3, `models_<layout>.ini` × 3, race kn5 listed only in the two race
   inis.

Kevin's seat, per race layout: spawn on Alvarado in the right-hand lane facing the way the layout
runs; the lap clock arms on crossing the line (not on spawn); at the Alvarado/College hairpin the
chain appears on the driver's left at the first island nose and is never on an island; no centre
barrier anywhere on Alvarado; the racing kerb hugs the sidewalk lip with no lip gap (L9); the
wrong-way warning never fires (0026); the opposite carriageway is unreachable for the whole lap.
Regular layout: drives exactly as today except the start, if moved.

## Decisions and the built design (2026-10-11, workflow `wf_…-c20` continued; nothing shipped)

**Config — `tracks/san-diego-lake-murray/track.config.json`.** `layouts[]` is exactly three
(`full` retired: `track_folder.ui_track_json` suppresses the suffix for `full`/`freeroam`):

| id | CM name | kind | direction | race_furniture | start (vertex into `data/centerline.local.json`) | sectors |
|---|---|---|---|---|---|---|
| `street` | K10 - San Diego (V3) — Street Loop | street | forward | no | line v300, grid v291 at +3.25 m right of travel (north lane), pits v274→257 | v1803, v3310 |
| `race_cw` | — Race — Clockwise | race | forward | yes | same line and grid as `street` | v1803, v3310 |
| `race_acw` | — Race — Anticlockwise | race | reverse | yes | line v300, grid v310 at +3.25 m right of ITS travel (south lane), pits v327→344 | v3310, v1803 |

Forward = increasing vertex index = clockwise seen from above (shoelace −8.87 km² in x=E, z=N):
Alvarado westbound → College northbound → Navajo eastbound → Jackson south → Lake Murray Blvd
southwest; right of forward travel = the lake-side carriageway. `direction` is the flag every tool
keys on, never the literal id `reverse`. The `race` block declares `wide_threshold_m 17.0`,
`centre_runs [[780,846],[1073,1096],[1258,1374],[1487,1540],[1739,2183],[2297,4440]]` (closed
vertex intervals, each island-side end ON the island's nose vertex, v780 / v4440 the free ends),
`barrier_profile_asset assets/models/concrete_barrier_4m.obj`, `barrier_height_m 1.2`,
`module_pitch_m 4.04`, `edge_mode road`, `edge_inset_m 0.82`, sealed mouths, continuous interior
corners, `kerbs {min_turn_deg 45, width 1.0, height 0.05, outer_extension [10, 30]}`, 8 grid slots,
8 pits. Q1 / Q2 / Q6 / Q7 are edits to this block, re-run `tools/barrier_bands.py`.

**Three kinds of kn5 from one `loop.blend` (L8 as amended, below).**

| kn5 | holds | listed in |
|---|---|---|
| `san_diego_lake_murray.kn5` (road) | every prepped object except the race furniture; **0 `AC_*` nodes** | `MODEL_0` of all three `models_<id>.ini` |
| `san_diego_lake_murray_race.kn5` | ONLY `1WALL_race_*` / `1KERB_race_*` objects (RACE-named materials), 0 `AC_*` | `MODEL_1` of `models_race_cw.ini` and `models_race_acw.ini` only (rt_california's `_barr2.kn5` shape) |
| `san_diego_lake_murray__<id>.kn5` ×3 | nodes only: `AC_START_0..7`, `AC_HOTLAP_START_0`, `AC_PIT_0..7`, `AC_TIME_{0,1,2}_{L,R}` | the last `MODEL_n` of its own ini |

How: `tools/barrier_bands.py` (pure, self-gated) declares the bands → `tools/layout_dummies.py`
(pure) writes `data/dummies_<id>.json` ×3 → `tools/author_race_furniture_blend.py` sweeps the strips
and kerbs into a `RACE` collection in `loop.blend` (idempotent) → `tools/verify_race.py` (pure gate)
→ the ENG prep (`build_kn5_loop.py`, two hunks: `1WALL_RACE`/`1KERB_RACE` keep their authored UVs;
with `len(layouts) > 1` it creates NO `AC_*` empties and writes `data/dummies.json = {}`) →
`tools/split_exports_blend.py` splits the PREPPED `blender/<slug>.blend` into
`blender/split/loop_main.blend` / `loop_race.blend` / `loop_spawn_<id>.blend` by REMOVING objects
(+ `meshes.remove` + `orphans_purge`, asserting RACE-only materials in the race scene and none in
the main) → `export_kn5_addon.py` (new `--blend <file>` / `--out <name.kn5>`) once per scene →
`build_spawn_kn5.py` reads `dummies_<id>.json` (engine frame + `_yaw_deg`) and exports the three
nodes-only kn5s. Objects are removed rather than deselected because the exporter that runs
(`exporter.kn5`, the AppData blender-assetto-corsa-tools 1.0.7) walks `blend_data.objects`,
ignores the selection and embeds every material with users > 0.

**Barriers.** A swept jersey STRIP whose cross-section is the measured half-profile of Kevin's
module (0.335 m base half-width, 1.20 m tall, 10-vertex closed ring, outward normals, texture
tiled at u = arc / 4.04 m so the joints read every module), one ring per centreline vertex (3 m),
seated by BVH onto the mainline ROAD (lowest sheet) and sunk 0.05 m. Centre chain on the six
declared runs (8,525 m, 2,853 rings, 8 objects `1WALL_race_kbar_<street>_<start>_<part>`), ends
tapered onto the island noses (half-width 0.335 → 0.25 m, height 1.20 → 0.30 m over 3 rings) or
free (height → 0.30 m). Kerb-line strips on BOTH curb faces of EVERY street (`road` mode: centre at
`half_w − 0.485`, road-side face at `half_w − 0.82`, 0.15 m clear of the curb batter), gapped only
inside the three declared bridge spans, straight across the three sealed mouths (26,307 m, 8,772
rings, 21 objects `1WALL_race_edge_<L|R>_<street>_<start>_<part>`; 27 rings dropped where the
inside lip folds at the five right-handers). Seven race kerbs (`1KERB_race_<apex>_<in|out>`, 1.0 m ×
0.05 m flat rumble strip with a 0.10 m lane-side ramp, inboard of the strip) at the five corners
the sign detector finds (`tools/place_signs.py`, imported read-only): outside lip only where the
chain is the inside (v1514, v2319, v3297), inside + outside at the hairpin v770 and the seam v0.
Budget: 122,338 positions in 36 objects, none over 8,000 positions / 31,960 loops (the add-on
splits at 65,535 render verts). Strips, not 2,100 instanced modules (≈ 2.2 M positions; every
reference measured ships strips/sheets).

**Dummies.** `tools/layout_dummies.py`: pole = `AC_START_0` = `AC_HOTLAP_START_0` 27-30 m behind
the line in each layout's own travel, grid `AC_START_1..7` in two staggered columns INSIDE the lane
(lane centre ± 1.0 m since 2026-10-11, was ± 1.4 m; pitch 5.5 m), pits single file 45 + 7 (p+1) m behind, `AC_TIME_0` at v300
(L/R swapped for `reverse`), sectors renumbered per direction (same two physical gates, L11). Yaw
= `atan2(tx, −tz)` (+π for reverse) at the dummy's OWN vertex — the measured facing correction
(see Notes). Grid clearance on 13.0 m Alvarado: the outer staggered column (4.25 m right of travel)
puts a 1.9 m car's edge 0.48 m off the kerb-line strip's face (5.68 m) — HARD floor 0.30 m in
`verify_race` F / `author_race_furniture_blend` / `barrier_bands` (was 0.08 m with the 1.4 m stagger, a
soft note); Q6 `walk` would add 0.93 m.

**AI.** `scripts/ac/write_ai_line.py --layout <id>`: direction and furniture from the layout; a
per-vertex right-of-travel lane offset between the divider face and the kerb-line strip face;
refuses a line that touches an island or comes within 0.6 m of a declared face. The race layouts
always get these GENERATED drafts (ledger 0023 stays open, no tier claimed; in-game recording per
layout is the end state). The street layout ships the V3 forward right-hand-lane draft by default
(`STREET_AI=draft` since 2026-10-11); `STREET_AI=july` opts back into the installed July line — also a
generated `write_ai_line` draft, not an in-game recording, and in the oncoming carriageway on every
divided run (Notes). See Q8.

**Folder and names.** airoso's `scripts/ac/track_folder.py` and `verify_kn5.py` run (the ENG
copies are no longer executed — they are pure Python, not part of the pinned drive-feel geometry,
and airoso's are strict supersets). `models_<id>.ini` ×3, `ui/<id>/ui_track.json` with
`name = "<cfg.name> — <layout name>"` (the install patch writes "K10 - San Diego (V3) — …") and
`run` = the layout's compass sentence, `<id>/{map.png, data/, ai/}`; stale single-layout structure
(root `ai/`, root `ui/ui_track.json`, `models.ini`, `ui/full`) removed by the packer; the set of
inis is asserted == `layouts[]`. `tools/make_map.py` writes every `<id>/map.png` in the kn5 frame.
Install folder stays `san_diego_lake_murray_v3` (previous build parked in `D:/k10-track-archive/<stamp>/`, never a second `_v3_prev` in content/tracks — Kevin 2026-10-11 "clear old versions").

**Gates (fleet/GATES-CHANGELOG.md 2026-10-11).** `median_zone` gains the `barrier` kind from
`barrier_bands.json`; `drive_test --layout <id>` per layout (reverse walks the lap backwards,
lane-relative sweep between the divider face and the strip face, the new `barrier_missing` at 0);
`audit_mesh --race --obj track.race.obj --out audit.race.json` (D exempt on the declared bands
only); `verify_kn5` multi-layout checks (a)-(f); `kn5_to_gate_obj --kn5 road --kn5 race --out
data/track.race.obj` (ONE OBJ for the kn5 set a race layout loads; the dot in the name is
deliberate — the prep merges every `data/track_*.obj` into the scene); `tools/verify_race.py`
(the authored furniture vs its declaration, before any kn5 exists). The street layout's numbers
must reproduce today's (drive_test 82 / 391 / 0 / 101, audit D 512 / K 154 / I 145 / F 15).

**Licence (Q10).** The K-rail pack is `UNRECORDED` in `assets/licenses.json`; `tools/pack_release.py`
now drops `san_diego_lake_murray_race.kn5`, `models_race_*.ini`, `ui/race_*/`, `race_*/` and the
race spawn kn5s from the CC0 variant (`strip_race_layouts`); the FULL (local) package carries all
three. The release READMEs say so.

## Proposed L8 wording — for Kevin's sign-off (Q9); NOT applied, `fleet/LAWS.md` is untouched

> ## L8 — Layouts share one road; physics does not
>
> Route and direction variants are **AC configuration over a single road mesh** — never rebuild,
> alter or re-export the shared mesh per layout. A layout MAY load additional kn5s beside the shared
> one through its own `models_<layout>.ini` (MODEL_1, MODEL_2 …): its nodes-only spawn kn5 (grid,
> pits, timing — `<slug>__<layout>.kn5`), and furniture that exists only in that layout (barriers,
> kerbs, boards — `<slug>_<overlay>.kn5`). Once a track has more than one layout the shared kn5
> carries **no `AC_*` spawn or timing nodes**; every layout's set rides in its spawn kn5. Added kn5s
> add; they never replace, move or duplicate anything in the shared kn5, and anything physical in
> them is judged by the same gates as the road (verify_kn5 on the binary, drive_test/audit on the
> loaded kn5 set) before it ships. Measured basis: deepforest, Oregon Raceway Park,
> rt_california_highway, Pacific Coast Hwy — every reverse-capable reference ships a spawn-free main
> kn5 (0 AC_START/PIT/TIME) plus per-layout kn5s (32-140 nodes each), and rt_california adds a
> geometry kn5 to two of its three layouts.
>
> The one exception, and the reason it is an exception: **`surfaces.ini` is applied per track, not
> per layout.** So a surface-physics fork (Rally Colorado's gravel vs tarmac) must be **two
> installable tracks**, each with its own slug, sharing the route by pointing at the same roads. A
> layout toggle makes the friction difference fragile.

Matching `CLAUDE.md` "Layouts" sentence: *"All layouts share one road kn5 and differ only in AC
configuration plus the kn5s a layout ADDS beside it (its spawn kn5; optional furniture kn5) — never
rebuild the road mesh per layout. The one exception is surface physics (L8)."*

`fleet/STANDARDS.md` S6 note (same sign-off): the archetype stays per track (`real_road` for Lake
Murray); `layouts[].race_furniture: true` is the per-layout overlay switch that builds the
street-circuit furniture set (centre chain, kerb-line barriers, race kerbs) into the overlay kn5 —
declared in config, not a second archetype.

## The ship run — what `bash tools/ship_sd.sh` does now (one command, three versions)

1. **sync** airoso `track.config.json` (three layouts + `race`) and `start_positions.json` → workshop.
2. **draft + author** as before (skipped by `--skip-blend`): median envelope, loop.blend regen,
   connectors, trim, seat terrain, slim far terrain, median island, mouth gaps, scatter/strip,
   lamps, signs (+ verify_signs, plot_signs).
3. **race furniture, every run** (also with `--skip-blend`, because it is idempotent and the only
   thing that keeps `loop.blend` in step with `race.*`): `barrier_bands.py` → `layout_dummies.py`
   → `author_race_furniture_blend.py` (saves `loop.blend` with the `RACE` collection) →
   `verify_race.py` (hard) → `plot_race_furniture.py`.
4. **prep** (spawn-free, UV-keep) → **split** → `--dry-run` stops here →
   **export** road kn5, race kn5 (content guard `tools/check_race_kn5.py`: RACE meshes, race textures, no `AC_*`), spawn kn5s ×3 →
   **AI** `write_ai_line --layout race_cw`, `--layout race_acw`, `--layout street` (`STREET_AI=july`
   copies the July `write_ai_line` draft instead) → **verify_kn5** (hard) → **track_folder** →
   **make_map** → **make_treefx**.
5. **gates**: `kn5_to_gate_obj` (road) → `drive_test --layout street` → `audit_mesh` →
   `kn5_to_gate_obj --kn5 road --kn5 race --out data/track.race.obj` → `drive_test --layout race_cw
   --layout race_acw` → `audit_mesh --race`.
6. **sync back** `loop.blend`, the data files (+ `barrier_bands`, `race_authored`, `race_verify`,
   `dummies_<id>`, `drive_test.<id>`, `audit.race`, `split_manifest`, `race_plots/`) and
   `ai/<id>/` ×3 into `tracks/san-diego-lake-murray/`.
7. **verdict**: any of the four gate exits red → not installed; `--force-install` installs red only
   when NO race layout is red on its own furniture gates (`barrier_missing` / obstruction — nothing
   exists to be "no worse than"); the street layout is expected red on the open 0046/0048 terrain
   class (82 ground-through, 391 floating, 101 excursions) exactly as today.
8. **install** `build/<slug>/` → `san_diego_lake_murray_v3` (previous → `_v3_prev`), the three
   `ui/<id>/ui_track.json` names patched to "K10 - San Diego (V3) — <layout name>".

Then Kevin's drive (fleet/templates/DRIVE-TEST-REPORT.md, one per layout) is the only ground truth:
three layouts in CM; each race spawn on Alvarado in its lane facing its way with the grid and pits
behind; the clock arms at the first crossing; the chain on the driver's left at the first nose,
never on an island, never on Alvarado; the kerb-line barrier hugging the curb; race kerbs at the
five corners; the wrong-way warning never fires; the opposite carriageway unreachable; the street
layout as today except the start.

## Dry run record (2026-10-11, `SHIP_PROJ=<scratch copy> bash tools/ship_sd.sh --skip-blend --dry-run` on a copy of the 2026-10-09 workshop build; nothing exported, nothing installed)

- bands: chain 6 runs / 8,525 m on 2,851 verts, edge strips on 4,393/4,499 verts (3 bridge gaps),
  7 kerbs at 5 corners, 3 sealed mouths; dummies ×3 (pole v291 yaw −101.6°, pole v310 yaw +79.0°,
  line 27.1 / 30.1 m ahead).
- author: 36 objects / 122,338 positions in the `RACE` collection; seated 13,144 hit / 3 near /
  0 interpolated; deck vs data worst −0.213 m (hairpin inside lip); 19 rings with another ROAD sheet
  0.18-0.54 m above the strip base (Del Cerro mouth v1081-1083, the Navajo/Jackson and hairpin
  inside lips — the ribbon's fold/mouth defects, 0033/0046 class, reported not papered over).
- verify_race: OK (chain worst ring spacing 3.16 m; edge missing {L 0, R 23} ≤ fold-dropped
  {L 0, R 27}; outside-lip ring spacing reaches 7.0 m → the strip chords the arc by ≤ 0.39 m, an
  author-tool refinement, noted).
- prep: `multi-layout (3 layouts): spawns ride in per-layout kn5s — no AC_* empties in the road
  scene, data/dummies.json = {}`; race names passed through `AC_NAME`.
- split on the PREPPED scene: main 20 meshes / 727,123 positions / 20 materials / 0 AC / 0 race;
  race 36 meshes / 122,330 positions (max 8,000) / 36 RACE-named materials / 0 AC; spawn ×3 =
  23 empties each; **problems: []** (the RACE-only-materials assertion now exercised on a prepped
  scene). Wall time of the whole dry run: 23 s.
- AI drafts (the ship command lines): race_cw 7,342/8,993 points offset into the right-hand
  carriageway, grid check +0.99 over 27 m, 100 % correct side, 0 island hits, min clear divider
  3.39 m / edge 3.36 m, est lap 365.5 s; race_acw the mirror (grid −0.99 over 30 m, 350.4 s);
  the street draft 1,718 points offset (islands only), 388.6 s. `lap_s_est` is the writer's
  curvature estimate, not a lap time.
- gates on the EXISTING road kn5 (the race furniture does not exist yet; the race gate OBJ is the
  road kn5 alone as the stand-in): street ground-through 82 / floating 391 / severe 0 / excursions
  101 / obstruction 0 / kinks 4.97 per km and audit D 512 / K 154 / I 145 / F 15 = 826 — identical
  to 2026-10-09 key for key (the 0046/0048 class, FAIL as today); race_cw / race_acw obstruction 0,
  ground-through 65 / 13, `barrier_missing` 34,833 / 34,833 → FAIL (the expected pre-build state,
  the gate has teeth) → `RACE_RED = race_cw race_acw`, so the install block refuses even with
  `--force-install`; `verify_kn5` refuses today's road kn5 under the three-layout config (16
  spawn/timing nodes in it, no race kn5, three spawn kn5s missing) — exactly what the chain must
  not pass; `track_folder --allow-missing-kn5` lays out `models_street.ini` [road, `__street`],
  `models_race_cw.ini` / `models_race_acw.ini` [road, `_race`, `__race_*`], `ui/<id>/` with the
  three names and run texts, pitboxes 8, `<id>/ai/` from `ai/<id>/`, and removes the stale root
  `ai/`, `ui/ui_track.json`, `models.ini`; `make_map` writes the four maps. Wall: gate OBJ 5 s,
  street drive_test 11 s, audits 9 s, both race drive_tests 20 s, verify_kn5 5 s, packer 7 s.

## Real rehearsal + weld pass (2026-10-11, `SHIP_PROJ=<scratch copy> bash tools/ship_sd.sh`; nothing synced back, nothing installed)

The first REAL rehearsal (no `--dry-run`) stopped at the race-kn5 size guard: `<slug>_race.kn5` 35,553,024 B.
It leaked nothing (36 meshes, all `1WALL_RACE*` / `1KERB_RACE*`; textures kerb_diffuse.png +
concrete_barrier_diffuse/normal.png, 2.4 MB) — it was 719,576 kn5 vertices for 241,190 triangles,
2.98 per triangle: the strips were flat-shaded, and the exporter (`exporter.kn5`, welds position +
normal + UV + tangent) writes one vertex per face corner then. verify_race also noted outside-lip ring
spacing up to 7.02 m. Fixed and re-run to the end (`--skip-blend`, the same authored scene):

- **Shading**: every RACE object smooth-shaded, hard edges only on creases > 30° (jersey base 90°,
  base/slope 33°, top lip 86°, the end caps; slope/upper is 17° + 12° and stays smooth) + the kerb
  outline. The prep was READ, not edited: `DOUBLE_SIDE` only touches merged `data/track_*.obj` groups
  (241,190 = authored quads × 2 + caps: nothing doubled), its bmesh round trip keeps the flags (all
  faces smooth, 4,300 hard edges on `1WALL_race_kbar_navajo_2297_0` after prep + split, as authored),
  its face-up pass flips 2 of 4,545 kerb faces (hairpin fold), it never un-smooths. engine-july
  `build_kn5_loop.py` 2dcc8e8b… / airoso 8752e963… unchanged.
- **Ring density**: `densify_rings` puts rings ON the declared offset curve: 81 inserted, spacing max
  3.50 m (was 7.02), chord vs the curve max 0.043 m (was 0.271 m at the seam corner's outside lip,
  0.171 m at the hairpin). verify_race H gates it (> 0.15 m FAILS): the old authored file FAILS H,
  the new one passes (11,668 spans measured, 0 over, 5 fold spans counted).
- **Race kn5**: 12,558,972 B; 36 meshes (max 12,809 v); **196,763 v / 242,810 tri = 0.81 per
  triangle** (predicted 196,774 before Blender); positions 123,148 authored / 123,140 after the prep,
  max 8,000 per object. The size guard is now a content guard (`tools/check_race_kn5.py` on
  `inspect_kn5 --json`): only RACE meshes, only pbr.py's race textures, no `AC_*` node — OK.
- **Road kn5 unchanged**: 31 meshes / 1,258,109 v / 1,232,927 tri / 14 textures / 91,934,629 B,
  per-mesh rows identical (the exporter is byte-nondeterministic: the same blend exported twice
  differs in 189,579 bytes).
- **Gates, every line identical to the same gates run on the pre-weld kn5 set** except the race
  audit's vertex inventory: street drive_test ground-through 82 / floating 391 / severe 0 / kinks
  4.97 per km / excursions 101 / obstruction 0 → FAIL; street audit D 512 / F 15 / I 145 / K 154 =
  826; verify_kn5 ✓; race_cw obstruction 220 / `barrier_missing` 22 of 34,833 / ground-through 65 /
  excursions 4 / kinks 5.12 → FAIL; race_acw obstruction 175 / `barrier_missing` 32 / ground-through
  13 / excursions 0 / kinks 2.74 → FAIL; race audit D 512 / F 15 / I 145 / K 154 = 826 →
  `RACE_RED = race_cw race_acw`, NOT INSTALLED (scratch: never installed anyway). The densified rings
  first read as 972 race-audit D walls: the band test's ±2 m rectangles left gaps between outside-lip
  band points ~7 m apart (460 verts) and the lap's closure duplicate carried Lake Murray's 27.5 m width
  at the seam (28) — both fixed in `scripts/geometry/median_zone.py` (fleet/GATES-CHANGELOG.md), D
  back to 512 on both the new and the pre-weld kn5 set.
- The race layouts' own reds (obstruction 220 / 175 stations, all on kerb-line strips — race_cw
  edge_R Jackson / College / Lake Murray, race_acw edge_L Lake Murray / College / Jackson;
  `barrier_missing` 22 / 32, worst runs at the seam and two mid-lap stretches) are unchanged by this
  pass, key for key, and stay open.

## Red-gates round (2026-10-11, the same scratch rehearsal, `bash tools/ship_sd.sh --skip-blend`; nothing synced back, nothing installed)

Three read-only diagnoses replayed the race layouts' own reds on the built OBJ. Two were gate bugs, one
geometry: (1) the race lane read the width of the vertex AHEAD of each station, up to 1.36 m too wide on
SD's mouth flares, so the scan disc hit the previous ring of a strip standing exactly on its declaration
(341 of 395 obstruction stations); the round disc also reached strips outside the declared lane along the
road (2); the presence probe read the lap's closure duplicate's 27.5 m and never wrapped the seam (1 + 1).
(3) `drop_folded_rings` kept the ear rings of the five inside-lip swallowtails and chorded back across the
fold: a hook of wall 1–3.5 m inside the exit carriageways of the three chained right-handers (52 race_cw
stations), six inside-out strip spans + one on the seam's inside kerb, and the declaration still put the
band on the folded offsets (52 `barrier_missing` stations). Fixed: the lane / probe / clip / seam in
`drive_test` (race layouts only), the strips and inside kerbs TRIMMED to the curb's own corner
(`race_furniture._trim_folds`, one mitred corner at X), the corners DECLARED (`barrier_bands.json`
`edge_corners`) and read by `median_zone` / drive_test / verify_race (D a set check against the
declaration, H on the corner polyline, new I: no inside-out span). Gate entries: fleet/GATES-CHANGELOG.md.

Result: race_cw obstruction 220 → **0**, `barrier_missing` 22 → **0**; race_acw 175 → **0**, 32 → **0**;
verify_race OK with 0 fold / 0 unmeasured spans and 0 inside-out (the built blend: 7 → 0); street
82 / 391 / 0 / 101 and audit D 512 / F 15 / I 145 / K 154, byte-identical reports; race audit 826 → 826.
The chain is still red on the INHERITED road defects (street + race ground-through-lane, floating 391,
street excursions 101, audit 826) — `RACE_RED` is empty now, so the install block falls back to the
July-reference rule. Still open: the seam closure steps 27.5 → 17.0 m in one 2.29 m segment inside the
right-hander, so 4.16 m of the seam corner's 6.99 m strip polyline stands off the ROAD ribbon over the curb
notch (1 ring seated by interpolation); the fix is a width taper in the centreline data and a ribbon
rebuild. Unchanged: the 6.3 m disc cap on a lane with no divider (Alvarado, the hairpin) — the trim removed
the hairpin knot the capped disc could not see; lifting the cap surfaces other stations that need their
own triage (diagnosis 1).

## Notes filed here (not conclusions elsewhere)

- **Spawn facing, two stacked causes** (measured on the workshop road kn5: `AC_START_0` local +Z ·
  AI travel = −1.00; the installed set_start build −0.91; deepforest +1.00). (1) The prep yaws every
  facing dummy with the SEAM tangent `cl[0]→cl[1]` (0016's class) wherever the grid is. (2) The
  add-on's `convert_matrix` maps `rotation_euler.z = ψ` to kn5 local +Z = (sin ψ, cos ψ); with
  ψ = atan2(tx, tz) that is (tx, tz) while the kn5-frame travel is (tx, −tz) — the error is
  heading-dependent, ~correct on east-west Alvarado by accident, backwards on north-south College.
  Fixed in `tools/layout_dummies.py`, gated by verify_kn5 (c). Whether this is 0026's mechanism is
  not concluded. k10-colorado's reverse layouts (`kn5_write.py:362`) share the reflection — out of
  scope here.
- **The July reference line drives the ONCOMING carriageway on every divided run** (frame-independent
  check at v1200, College northbound: July 7.5 m WEST of the V3 centreline, the V3 street draft 6.6 m
  EAST = lake side = right-hand for northbound; 1,642/1,642 island stations left of forward travel;
  under the race_cw declaration 5,322 July points are inside the chain's clearance). Every V3 install
  to date shipped it. Q8 below.
- **`data/track_race.obj` would have been swallowed by the prep**: `build_kn5_loop.py` step 1b merges
  every `data/track_*.obj` into the scene; the race gate OBJ is `data/track.race.obj` and
  `kn5_to_gate_obj` refuses a `track_*.obj` output name.
- **engine-july is a dangling git worktree** (`git status` refuses it): nothing there is committed; the
  mirrored files are recorded by md5 in the commit message (build_kn5_loop.py ENG `2dcc8e8b…` /
  airoso `8752e963…` — two hunks on each of two diverged files; export_kn5_addon.py, build_spawn_kn5.py,
  verify_kn5.py, median_zone.py, drive_test.py, audit_mesh.py byte-identical).
- **Ribbon folds at the inside apexes** (hairpin flare, the three 90° corners, the Del Cerro mouth step
  of 0.54 m) are the ribbon's defects; the author tool drops the folded rings/stations and chamfers
  the inside corner by a few metres rather than knot the wall. The lane disc judges it.

## Open questions for Kevin — Q1, Q2, Q6, Q7 change authored geometry; answer before the ship run

1. **Q1 Side-street mouths in the race layouts.** Default SEALED: the centre chain runs nose-to-nose
   across the Del Cerro 4-way (v1073-1096) and the kerb-line barrier runs straight across all three
   mainline mouths (Del Cerro v1085/v1086, Parkway/Wisconsin v4424) — the Macau pattern; the Del
   Cerro neighbourhood chain is unreachable in both race layouts; the street layout keeps every mouth
   open (it never loads the race kn5). Alternative: escape roads — gap the kerb-line barrier at each
   mouth (connector half-width + 3 m); race_cw then keeps the Del Cerro EAST leg + the v4424 mouth,
   race_acw only the WEST leg.
2. **Q2 The two 13.5-17 m stretches** (Alvarado→College taper v724-760, 108 m; I-8 overcrossing
   approach v4453-4482, 90 m) get NO centre chain under the 17 m rule (chain v780 → v4440; a two-way
   gap on the bridge between two chained runs, bridge rails only). Keep the rule, or carry the chain
   across at ~6.4 m per side?
3. **Q3 The street layout's start.** Recommend YES — Alvarado grid A (v291, +3.25 m north lane,
   westbound toward College = your 2026-08 words, line v300), the same spawn as Race — Clockwise;
   `start_positions.json` keeps working for the street layout only (`layout_dummies --issue-spawn`).
   Say no and the street layout keeps today's College debug spawn (still in its own spawn kn5, with
   the facing fix).
4. **Q4 Names and which direction is "A".** ids `street` / `race_cw` / `race_acw`; CM names "K10 - San
   Diego (V3) — Street Loop" / "— Race — Clockwise" (Alvarado westbound, College northbound = today's
   build direction) / "— Race — Anticlockwise" (Alvarado eastbound); your compass wording is the hover
   text. Today's build spawns you facing ~155° backwards on College (the yaw reflection) — confirm the
   names once the fixed spawn faces you forward. 8 grid slots + 8 pits per layout (ledger 0021).
5. **Q5 Barrier height.** The strip uses your module's full silhouette (0.67 m base, 1.20 m tall). Real
   street K-rail (Long Beach / Macau) is 0.81-1.07 m; at 1.20 m the wall hides the opposite
   carriageway's houses from the driver's eye. One constant (`race.barrier_height_m`) — keep 1.20?
6. **Q6 Kerb-line barrier placement.** Default ON THE ROAD against the curb face (the literal "inside
   of the sidewalks", the Long Beach placement; narrows every street by 0.82 m per side — Alvarado
   11.36 m clear, grids 1.5 m clear, the outer staggered column 0.48 m with the 1.0 m stagger). Alternative `walk`: on the
   SIDEWALK TOP behind the curb (every street at full width, road lip free for the kerbs, +0.93 m grid
   clearance). `race.edge_mode`, decided before authoring.
7. **Q7 Interior corners.** Default: chain continuous round College/Navajo, Navajo/Jackson and
   Jackson/Lake Murray (a median that continues; clockwise on the inside at R 34 / 25 / 23 m).
   Alternative: gap the chain ±30 m at each apex for the real-junction look (3 × 60 m open centre).
8. **Q8 Race kerbs and the street AI.** Seven kerbs at the five corners (outside lip at the three
   chained corners; inside + outside at the hairpin and the 70th→Alvarado seam corner), 1.0 m × 0.05 m
   flat red/white, inboard of the barrier; the minor v3282 kink excluded. Want kerbs anywhere else
   (island-nose gaps, the Del Cerro 4-way)? And the street layout's AI: the default is now the V3
   forward draft (`STREET_AI=draft`; 100 % right side, 0 island hits, unverified in game); say if you
   want the July line back (`STREET_AI=july` — a July `write_ai_line` draft, not a recording; drives as
   today, but in the oncoming carriageway on every divided run, see Notes).
9. **Q9 Sign-off on the L8 wording** above (+ the CLAUDE.md sentence and the S6 note). Nothing in the
   laws is edited until you say so.
10. **Q10 Licence.** `concrete_barrier_4m.obj` and its two PNGs are the owned Dropbox pack with an
    `UNRECORDED` entry in `assets/licenses.json`; the race kn5 and the two race layouts stay in the
    FULL (local) package only until the pack's licence is recorded. Also: import the pack's real
    Transition Barrier for the two free ends later instead of the procedural taper?
11. **Q11 Tall invisible collider.** Deferred: the visible 1WALL strip is its own collider (a 1.2 m
    rail vs a ~1.3 m car is the ordinary street-circuit case). Say if you want the Macau-style 2.5 m
    invisible sheet from the first drive anyway (`--collider`; needs the `1WALL_RACECOL` pbr/ALPHATEST
    row + `assets/textures/invisible_4x4.png`, generated — a material that cannot be seen working
    before you drive).

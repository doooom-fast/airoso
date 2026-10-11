---
id: 0047
title: "Actually make it three versions: the regular one, and then the two tracks" — the open street loop plus two one-way race layouts, barrier-split on the wide roads, both starting on Alvarado
status: open
scope: tracks/san-diego-lake-murray (proof; layouts[], declared start, race furniture); engine scripts/ac/{build_kn5_loop,build_spawn_kn5,track_folder,verify_kn5,write_ai_line}.py + scripts/geometry/{median_zone,audit_mesh,drive_test}.py + new tools/ (barrier bands, race-furniture authoring, multi-layout ship); standard fleet/LAWS.md L8 wording + fleet/STANDARDS.md S6 (archetype is per-track, the race overlay is per-layout)
layer: project + engine + standard
train: -
---

## Status

**Open — measured, not diagnosed as a defect, nothing designed or built** (2026-10-10, workflow
`wf_fe6ed9e1-c20`). This is a feature request with a data-proven shape; the "Diagnosis" below is
*what today's build does that the three versions cannot inherit*. Design/build queues behind 0043
(sodium lights), 0044 (arrow signs) and 0045 (GrassFX); it needs a kn5 rebuild, so it rides the same
single `ship_sd` run as 0046. Open questions for Kevin are at the end; two of them change the
geometry, so nothing here should be built until they are answered.

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
per-layout in-game recording is the end state. Today `ship_sd.sh` copies the July reference's recorded
`fast_lane.ai` into the single `ai/` (`tools/ship_sd.sh` install block) — that line is the road
centre in forward order and is wrong for both race layouts.

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

## Fix — design sketch, nothing built, pending the open questions

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

## Open questions for Kevin (the first two change geometry — answer before design)

1. **Side-street mouths in the race layouts.** Del Cerro Blvd opens off the driven lane at v1086 in
   one direction and v1085 in the other (inside the College island gap); the `medium#2+0` mouth at
   v4424 opens off the forward lane only. Close them with a barrier across the mouth (a sealed
   circuit), or leave them open as escape roads with the sidewalk barrier gapped?
2. **The two 13.5-17 m stretches.** Lake Murray Blvd on the I-8 overcrossing (v4453-4482, 90 m,
   13.5-16.4 m) and the Alvarado → College taper (v724-760, 108 m, 13.1-16.5 m). Under the 17 m rule
   both get no centre barrier, so the chain has a 90 m two-way gap on the bridge between two wide
   runs. Keep the rule (gap), or carry the chain across at 6.4 m per side?
3. **The regular layout's start.** Today it is on Jackson (derived) with the grid at a debug spawn on
   College. Your 2026-08 words were "i prefer starting on alvarado toward college"; 0026 recorded the
   opposite direction as the way you drive it. Put the regular layout's line at v300 on Alvarado as
   well — and which way?
4. Names for Content Manager (e.g. "Lake Murray", "Lake Murray Race — toward College", "— toward
   I-8"), and the grid size (8 slots today).

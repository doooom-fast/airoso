# Gates changelog

Every change to a gate threshold, bypass, exclusion or wiring gets an entry here **in the same
commit**: what changed, the measurement that justifies it, and how it was proven. Silent weakening
is how a gate goes vacuous while still printing green — the failure REALISM §1 was written about.
Append-only, newest first.

Gate *results* don't belong here; they live with the built artifact (`data/drive_test.json`,
`data/audit.json`) and in the ledger entry that provoked them.

**The standing rule:** a threshold calibrated against our own output is not a threshold, it is a
mirror. REALISM §3 and §5 exist to replace these numbers with envelopes measured off tracks that
feel right (`fleet/reference/MEASURED.md`). Until that lands, the ⚠ items below are known-invented.

---

## 2026-11-03 — Lariat Drive 1: the corner-arc step gate in the mesh step, and the builder values behind A2 / P3a (ledger 0048 "Drive 1 on the Mac")

No existing gate threshold moved. One new hard check, and the builder values the new opt-in modes use, every one of
them read only by a track that opts in (the Lariat 0.17.0); every other track builds byte-identically (Milford's draft
`data/track.obj`, `finished_centerline.json` and `dummies.json` md5-identical before / after, below).

| Gate / value | Where | Value | Flag |
|---|---|---|---|
| **corner-arc step gate** (new, hard: the mesh step exits on a failing corner) | `scripts/geometry/corner_arcs.py` via `build_mesh.finished_centerline` (`hairpin_fit.mesh_fit`) | on the fitted span +- 5 vertices of the SWEPT line: heading change <= spacing / R x 57.3 deg + **1 deg**; neighbours differ <= **1.5 deg** | the plan's P2 step 2 values, ⚠ invented there; the 5-vertex margin ⚠ invented |
| corner transition length | same | **8 m** clothoids each side of the arc | ⚠ invented (the 1.5 deg rule needs >= 2.6 m at R 14.9 m) |
| corner arm lines | same | least squares through **16-40 m** before / after the apex; apex searched within **40 m** of `st_m`, window **+-15 m** | ⚠ invented |
| cross-section slopes | `scripts/geometry/cutfill.py` (`terrain.cross_section.build`) | rock cut **0.25:1**, fill **1.5:1** | [std: docs/ROAD-CONSTRUCTION.md, the Lariat's section] |
| fill bench / cut bench | same | **1.2 m / 3.2 m** beyond the verge | ⚠ invented: one 1.11 m cell's diagonal less the verge (kn5_ground_check's flush edge, L3b); audit H's 2 m sample plus that diagonal less the verge |
| stacked-leg hold | same | ground held **0.3 m** clear of the midpoint height on its own leg's side; legs < **2 m** apart in height not held | ⚠ invented; the pair rule is the stacked-leg gate's own (40 m / 150 m) |
| `corridor_refine_margin` (new key) | `build_mesh` corridor refinement | default **1** (unchanged); the Lariat **0** | wiring, no threshold |
| `corridor_stencil_factor` | existing key | the Lariat **0.05** (default 0.25) | ⚠ invented per track (measured: road-over-ground p95 0.131 -> 0.065 m) |
| `road_profile.fold_plateaus` / `fold_pads`, `road_edge.draft_walls` | `build_mesh` | the Lariat **false** each (default on) | switches, no threshold |

Proof: `tests/geometry/test_corner_arcs.py` (4: a 78.5 / -76 deg node fitted at R 14.9 / 16.08 m passes the gate with
the vertex count, the heights and everything outside the arms unchanged; a closed lap keeps its seam; a radius too large
for the arms is skipped, never forced), `test_cutfill.py` (6: both slopes, the crossfall at the edge, the stacked hold on
both sides, the lateral cap at the medial line, the grid grading), `test_lariat_drive1_switches.py` (5: every switch
defaults to the old build; the loops and branches it gates, read from `build()`'s source; the Lariat opts in; no other
track does). Byte identity: Milford's draft built with the engine at `c5722f2` and with this change: the three files
md5-identical and the two mesh logs identical.

## 2026-11-03 — BYPASS: Lake Murray 0.19.4 (the buildings rehearsal) installed red on 0.19.2's inherited keys, by Kevin's word (ledgers 0062, 0065)

The chain's `--force-install` rule, applied by hand to a scratch build: `D:/k10-scratch/lm_bespoke` (rehearsal 2, `SD_BESPOKE=1`,
`--no-install`) installed over 0.19.2 as `san_diego_lake_murray_v3` 0.19.4. Kevin's word: "Over 0.19.2". Red as 0.19.2 is red, on
the street and race `drive_test` and `audit_mesh` exits, with no key worse than the installed 0.19.2's committed files: every
`drive_test` key of every layout identical (floating furniture 0), `audit_mesh` skirt-off-terrain 1,564 → 1,563, the rest of
the audit's classes unchanged; `kn5_ground_check`, `no_route`, `house_seat`, `rib_check` and `verify_kn5` PASS. A `SHIP_PROJ`
scratch build never installs itself, so the chain's install step (park, copy, ui names) was replayed by hand with the
version written 0.19.4. No threshold changed.

## 2026-11-01 — BYPASS: Lake Murray v4 installed red on one gate, by Kevin's word (ledger 0065)

`--force-install` on `san_diego_lake_murray_v4` 0.20.0, over the street layout's `drive_test` excursion drops alone: 96 against the limit of 13. Kevin's word: "Force". The count equals the installed 0.19.2's. No threshold changed; this is one install, not a rule. Every other gate on the proof build: soft top 0 / 0 / 0, audit 0 on all three layouts, race drive_test and no_route PASS, kn5_ground_check PASS, house seat floating / sunken / buried 0.

## 2026-11-01 — a race layout without furniture; the street-only kn5 carries the centre line (ledger 0063)

No threshold moved. Three wiring changes, each so a new shape of track is judged on the kn5 set it loads:

- `drive_test`: a layout of `kind: race` with no `race_furniture` (Sand Creek's lap) is judged on `data/track.obj`; it has no race or closure kn5 to
  build a `track.race.obj` from. A furnished race layout's requirement is unchanged. `track.obj` here includes the street-only kn5's paint, and paint is
  no obstruction (`PAINT`), so the drive reads the same.
- `verify_kn5 --inis`: such a layout must list exactly the road kn5 and its spawn kn5, and no race layout may list `<slug>_street.kn5`.
- `race_chicane.is_street_only_name` also matches the road's `YLINE*` (not the I-8's `YLINE_I8_*`), and `has_street_kn5` is true on any track with both kinds of
  layout, so `check_street_kn5` and `verify_kn5` hold the yellow line to the street set.

Not a gate, recorded because it decides what a gate measures: `corridor_refine_connectors: "ribbon"` (Sand Creek) refines the ground under a street's pavement and
not under its verge, with `corridor_refine_factor` 4 where it was 6. Proven on the built kn5: lap numbers unchanged from 0.30.0 (severe 1, kinks 11.06 /km, fold bumps
21, replication median 0.01), excursion drops 2 -> 3, far ledges 7 -> 9, and `kn5_ground_check` road-over-ground p95 0.049 m, double-sheet cells 0 -> 10.

## 2026-11-01 — the block collider is a skirt; Microsoft's footprints as a planner source; a big low footprint is a house

No gate threshold changed. Lake Murray's second rehearsal (ledger 0062), not installed.

- **The block collider's foot follows the ground** (`tools/author_bespoke_blend.py`: `COLLIDER_STEP_M` 3 m `[invented]`;
  `COLLIDER_GROUND_M` removed). `drive_test` reads each `1WALL` vertex's lowest point against a surface within ±2.5 m of it; a
  flat foot at the footprint's lowest ground stood 2.9 m under the grass at the high corner of a sloped lot — the two Mission
  Gorge columns. A vertex every 3 m, each 0.15 m under its own ground: floating furniture 0 on every layout, 275 colliders where
  the first rehearsal stood 22.
- **`tools/plan_buildings.py` reads its footprint sources in order of trust and dedupes** (`DEDUPE_CELL`): a later footprint
  whose centroid lies inside an earlier one is dropped and its height offered where the earlier has none. **Microsoft
  GlobalMLBuildingFootprints** (`tools/msft_footprints.py`, ODbL) is Lake Murray's third source, checked before use: nearly
  disjoint from OSM there (10,549 of 12,035 where OSM has nothing), heights 4.3 / 5.6 / 8.9 m at OSM's 1 / 2 / 3 levels.
- **An untagged footprint that area alone would class commercial or industrial is a house when a known height puts it under
  7.5 m and it is under 1,000 m²** (`HOUSE_MAX_H_M`, `HOUSE_MAX_AREA_M2` `[invented]`): 1,225 big single-storey houses at Lake
  Murray that would have worn parapets.
- The author step prints a tally of every drop reason, not the first twelve.

## 2026-11-01 — the one-way gate judges a parked layout too (the Lariat started; ledger 0048 "Started"; wiring, no threshold)

`tools/route_oneway_check.py` (a hard draft gate in the chain: `steps.draft route_oneway_check`) read `layouts[]`
alone. The chain's first pass ships ONE layout and parks the others in `track.config.json` `_layouts_v3_owed`
(Sand Creek's reverse 2026-10-28; the Lariat's `street_reverse`, `race_acw`, `race_cw` 2026-11-01), which would have
taken Street Reverse's four declared against-the-arrows stretches (4,486.5 m, D2 a) out of the gate's sight for as long
as it is parked. Now every layout under `_layouts_v3_owed.layouts` is judged beside the live ones, marked `parked` in
`data/oneway_check.json` and on the printed line; a race layout stays SKIP as before. No number moved (`snap_m` 3.0,
`min_cos` 0.7). Proven on the real Lariat (Full 0 m against, Reverse (parked) 4,486 m in 33 runs all on its four
stretches, PASS) and by `tests/tools/test_route_oneway_check.py`, which reads the real config.

### Same day — the elevation profile by station (the Lariat's 1 m paint centreline; builder side, no gate moved)

`scripts/elevation/heightfield.py` `build()` handed `snap_to_ground` a hard-coded `spacing_m` of 3.0 (the gps stage's
resample), which is how its 33 m despike, 9 m mean and grade cap become points. Every other track's centreline is
3 m (measured 2026-11-01: ten tracks, no segment under 2.07 m); the Lariat's paint centreline is 1 m over the climb
and Paradise Rd (9,208 of 14,444 segments), so there the 16 % cap was **48 % per metre** and the windows a third of
their width. The stand-in rehearsal read 25–30 % one-metre steps on Paradise Rd through the "capped" profile, and
`build_mesh`'s measured-guard then stood ten stone lips in the lane at st 10,620 (drive_test obstruction 10, audit D 28).
Now `profile_along`: when more than 5 % of a line's segments are under 0.8 × 3 m, the raw profile is read onto a
~1 m station grid, `snap_to_ground` runs there with that spacing, and the result is read back; a uniform 3 m line
takes the old call unchanged (`tests/elevation/test_profile_by_station.py`: byte-identical on 3 m, four 1.0 m cliffs
capped to ≤ 16.5 %/m where the 3 m read let 25 %+ through). No gate threshold moved; `drive_test`'s replication
reference (`z_raw_m`) is untouched. `centerline.elevation.json` records the path taken under `profile`.

### Same day — the D4 verge width from the config (`road_profile.verge_m`; builder side, no gate moved)

`build_mesh` built the shoulder's gentle band and the grading band at a hard-coded 2.5 m each side (`ribbon.road_shoulder`
`verge_w`, `grade_embankment` `band`, the connector trim's `_VERGE_W`: "must break at the same line"). Kevin's D4
(V3-PLAN, 2026-10-11) builds the Lariat twice, at 0.4 m (the real width, then the real edge) and 1.25 m (a firm strip),
and on the 2026-10-12 branch that width lived only in the branch's own underlay. Now `road_profile.verge_m`, when a
track declares it, is that band in all three places and `SHIP_VARIANT` writes the variant's value into the workshop
config per run; every track without the key keeps 2.5 m, byte-identical. **Floored at the grid's representable band**
(`grade_embankment`'s half-diagonal + 1 m, which it already enforced on its own band): the stand-in rehearsal of the
full draft order read the stagger of a 0.4 m sheet against a 3.6 m shelf as 67 ground-on-top samples and 55 severe
steps at the lane edge (rehearsal 3, ledger 0048 "Started"), so the one floored value goes to both, the build says
when the declared edge is narrower than its grid can carry, and the narrower edge is P3a's to author — on the Lariat's
7 × 7 km box at the 3 M-vertex budget (3.6 m cells) D4 A and B build the same 3.6 m band until then. The face that
drapes from the band to the ground is unchanged — it is what ledger 0061 (2026-11-01, the paved-hillside edges on the
four chain tracks) puts on trial, and it will move there, not here.

### Same day — the review's fixes: widths in the local order, the seam rule both ways, the closed ring without its duplicate (builder side, no gate moved)

A fresh-eyes review of the Lariat integration (ledger 0048 "Started") found four defects, each fixed with a test:
- **`scripts/gps/widths_from_osm.py` wrote its per-vertex widths 1:1 by geojson index** into `centerline.local.json`,
  whose ring projection re-orders to `route.start_at` / `route.reverse` after the geojson is written (High Plains: 815
  of 1,074 points). Now it applies the permutation projection records (`in_local_order`, ledger 0060) and marks
  `widths_order: "local"`; `scripts/gps/measured_widths.py` rotates only a file without the mark. No shipped track
  changes: Sand Creek (the only chain track that runs `widths`) has no recorded permutation (identity), the Lariat's
  `measured_widths` already undid the offset by matching. `tests/gps/test_widths_local_order.py`,
  `test_measured_widths.py` (+1).
- **`build_mesh.seam_rule_spans`** dropped only a span ending on the closing vertex with vertex 0 low; the mirror (a
  span starting on vertex 0 with the closing vertex low) is the same self-disagreement and is dropped too, and a tail
  span that continues from vertex 0 into a run too short to be its own span now carries that run with it.
  `tests/geometry/test_bridge_seam.py` (+2).
- **`build_kn5_loop.detect_bridge_spans`** clamped a span's head pad at 0 when the bridge began within `pad_m` of the
  seam; on a closed lap the pad now continues before the seam like the tail pads do.
- **`heightfield.profile_along`** forced the last grid value to vertex 0's for any `closed` line; a closed ring that
  does not repeat its first vertex keeps its last vertex and the grid runs on round to vertex 0 (`close_seg_m`);
  `road_profile.verge_m` of 0 is 0, not the 2.5 m default; one haversine pass instead of two.
  `tests/elevation/test_profile_by_station.py` (+1).
Also: `road_profile` no longer writes `z_raw_local_m` (nothing read it; a reader taking it beside `z_raw_m` would
rotate twice). Noted, not changed: `extract_kn5.parse(keep=)` cannot step over a SkinnedMesh (its layout is unknown,
"not supported yet" stands); `crossfall.compose`'s roll-rate scans are O(n·|bad|) (2 s on the Lariat's 8,305 stations).

### Same day — a road network's reference line: what the line gates judge, and what they do not (wiring, no threshold)

`tools/ship_track.sh` gained the draft step `network_reference` (`scripts/geometry/network_reference.py`, opt-in on
`track.config.json` `network.reference_line`): a road network's ship phase — the prep, `write_ai_line`, `make_map`,
`verify_kn5`, `drive_test` — walks ONE declared real mainline resolved from the draft's own edges (the San Diego
freeway: I 8 eastbound, end to end), never an invented line (L1). `scripts/gps/classify.py` records each edge's
direction of travel from the OSM ways' order only when the block exists; `build_network_mesh` records every swept
edge line (`data/network.edges.local.json`) only then. **The hole is named, never hidden:** `drive_test` writes a
`reference_line` key (the edges judged, the km built, every unjudged edge by id and name) and prints the list;
`make_map` draws every edge; `ship.json` `_owed` says "NOT JUDGED". No threshold moved; a track without the block
writes every file byte for byte as before (`tests/geometry/test_network_reference.py`,
`tests/ac/test_network_ship_contract.py`, `tests/gps/test_classify_travel_dir.py`). The stand-in rehearsal on Lake
Murray's cached motorway ways also found a network-draft defect, owed to `scripts/elevation/network_elev.py`: a
junction node gets two heights where two edges meet (0.13–0.60 m pavement steps at the mainline joints).

## 2026-10-31 (later) — `house_seat` on every chain track; the buildings pipeline's planner checks itself; a collider only on the fine ground; GrassFX zones off the aerial

`tracks/milford-road-course`, `high-plains`, `sand-creek` and `exotics-racing-lv` `ship.json` all run `author_bespoke` and the
`house_seat` gate now (`tests/tools/test_ship_track_chain.py` pins the pairing). No gate threshold changed. Three rules the batch
bought, all in `tools/author_bespoke_blend.py` and marked `[invented]` there:

- **A collider only within 60 m of the lap, on `1GRASS` within 2 m of its foot** (`COLLIDER_REACH_M`, `COLLIDER_GROUND_M`).
  `drive_test` culls ground triangles by cell round a wall and reads a `1WALL` with nothing loaded under it as "floating 99":
  High Plains' corner-worker huts (8 columns) and Sand Creek's far warehouses (351, then 80, then 8 at 100 m) went red on it
  three times before the reach fell to 60 m. Past that reach a building stands see-through; no car gets there. *(2026-11-01:
  the 2 m foot rule measured the walls' bottom, not the collider's, and the collider's flat foot was the mechanism behind the
  last two columns — replaced by the skirt below.)*
- **A planned footprint with no built ground under it stands as a far block** (`FARBLOCK_*`, no collider, not `BUILDING` so
  never a GrassFX occluder) instead of being dropped.
- **A block is authored at the prep's own floor** (`PREP_SINK_M` 0.4, `PREP_SHOW` 0.5: the prep's `house_seat` constants), so
  the prep's re-seat moves its walls by nothing and the roof, a separate object the prep never touches, stays on them; a
  parapet carries on from the eave ring's own vertices, since the prep re-seats a `BUILDING*` mesh by ISLAND (on the Lake
  Murray rehearsal every separate parapet island was pushed to the ground as a 0.7 m "building": 1,271 buried).
- **The guard lips become `1WALL_GHOST_*`** (a transparent alpha-test skin) and keep standing as the collider the gates judged;
  the W-beam `GUARDRAIL` over them is visual only. `scripts/ac/build_kn5_loop.py` exempts the new prefixes from the planar UV
  and the weld as before.

San Diego runs engine-july's prep and texture table: both changes are recorded as pending in
`tracks/san-diego-lake-murray/engine-july-snapshot/PENDING-MIRROR.md5` (`scripts/ac/pbr.py` with the new rows; engine-july's
`build_kn5_loop.py` with the two exemption tuples only, never airoso's chain prep), rehearsed on an engine scratch copy
(`ENG=`), and the real engine-july is untouched until mirrored.

`tools/plan_buildings.py` (the buildings pipeline, `.claude/skills/buildings`) is a planner, not a gate, but it refuses its own
reading three ways, each `[invented]` in its header except the first: a sun under 30 deg (NAIP's own floor; a vote that needs
one has found the camera's lean on tall walls — Sand Creek 2023 and Nevada 2013 both), a shadow / OSM median outside 0.6–1.6
where five OSM heights exist, and an unchecked stage (no OSM heights) unless the plan's `shadow.trust_unchecked` says so after a
`--debug` drawing was read. Every height row says its source.

`tools/plan_grassfx_aerial.py` + `ship_grassfx_aerial` (before `track_folder`): GrassFX `[GRASS_FX_ADJUSTMENT]` world rectangles
bound to the config's looks by a colour rule on the track's aerial, cells of 30–40 m, at most 48 rectangles, fade 10–14 m; the
rule's bounds per track are `[invented]` by reading that photograph. The rectangle `CENTER` carries the lap's mid height; whether
CSP reads the rectangle on the ground or by that height is **unverified in game**.

Milford's trace was on a squashed frame (the USGS export has square-degree pixels; `source/trace/unsquash_frame.py`): the lap
is 4.90 km, not 4.07, and the road now sits within 0.21 m of the measured line (`replication_vs_measured` max; it read 28 m
on the first corrected run before the mesh was rebuilt). `drive_test` on the rebuilt track: severe steps 26
(5.3/km, under the 12/km line), excursion drops 1, far ledges 33 (reported, not gated).

---

## 2026-10-31 — `house_seat` joins Nevada Nights' gates; the bespoke prefixes skip the prep's UV flatten and weld (no threshold changed)

`tracks/exotics-racing-lv/ship.json` now stands two buildings (`steps.author` `bespoke`, `tools/author_bespoke_blend.py`),
so it runs `gate_house_seat`, the existing `tools/house_seat_check.py` with its existing limits; no other chain track
changes. `tests/tools/test_ship_track_chain.py` pins that a track gets this gate exactly when it has the author step.

`scripts/ac/build_kn5_loop.py`: `BUILDING_FABRIC`, `1WALL_FABRIC` and `PROPCONE` keep their UVs (a top-down projection
would smear a wall), `BUILDING_FABRIC` and `PROPCONE` are never welded (ledger 0024's inside-out shells). San Diego runs
engine-july and is untouched. The author tool's own self-check limits are marked `[invented]` in its header.

---

## 2026-10-29 — the split's single-layout rule; `--from <step>` never skips a gate (ledger 0060; wiring, no threshold)

The first non-San-Diego chain run (Exotics Racing, the Windows workshop) passed the draft, the underlay and the prep
and stopped at `tools/split_exports_blend.py` with three PROBLEMs no single-layout track can satisfy: "no race
furniture" (no layout declares any), "no curb strip in loop_race.blend" (a race scene it had no reason to write),
"no dummies_full.json" (the prep bakes a single layout's AC_* into the road scene — `scripts/ac/build_kn5_loop.py`
— and `verify_kn5`'s single-layout branch judges them in `<slug>.kn5`). The split had only ever run on Lake Murray's
three layouts.

| Check | Was | Is | Scope |
|---|---|---|---|
| split: race furniture required | always | only when a layout declares `race_furniture` (and RACE objects with no such layout are refused) | the common race scene is written only then |
| split: `loop_main.blend` and the AC_* nodes | always removed; any left = PROBLEM | **one** `layouts[]` entry: kept, none left = PROBLEM; **more than one**: as before | keyed on the config's layout count, as the prep and `verify_kn5` are |
| split: spawn scene per layout | always, `dummies_<id>.json` required | multi-layout only | a single layout's grid rides in the road kn5 |

Proven on the real prepped Exotics scene under the `bpy` module (before: the Windows run's three PROBLEMs, byte for
byte; after: 67 meshes + 23 AC nodes in `loop_main.blend`, no race or spawn scene, exit 0) and in
`tests/tools/test_split_single_layout.py`. `tools/ship_track.sh --from <step>` (resume at a draft / author / prep /
ship step) refuses a gate name: every gate runs on every run.

### Same day, the re-run: `verify_kn5` red on the pits, and the frame underneath it

The Exotics re-run (`--from split`) exported and stopped at `verify_kn5`: `AC_PIT_3..7` 14.8–45.4 m off the road
(`PIT_ROAD_MAX_M` 13.5, unchanged). Root cause, reproduced here on the draft mesh to the decimetre: the prep's
single-layout branch recomputed the dummies from the unmirrored `centerline.local.json` (8 pits) while the mesh was
built mirrored (`mirror_x: true`), so the pit row stood on the road's mirror image. Underneath it: **the chain's frame
is San Diego's** (the prep's `(x, z, y)` import + the exporter's `(x, z, −y)` = kn5 `(E, up, −N)`, right with no
mirror and no yaw; Lake Murray is `mirror_x false`, `true_north 0`), and `mirror_x: true` + `true_north 180` were the
V1 OBJ program's own import convention `(x, −z, y)` and its sun fix — through this chain they ship a **mirrored**
track with the sun 180° off while every gate stays self-consistent (`kn5_ground_check` even applies the 180° yaw the
prep never made). No gate could have caught it; Kevin's seat would have.

| Check | Was | Is | Scope |
|---|---|---|---|
| chain: the frame | not checked | `tools/ship_track.sh` refuses `mirror_x: true` or `true_north_rotation_deg ≠ 0` on the source config before any copy (exit 2) | every chain track; the four configs set to the chain's frame (Exotics' T2 bank sign flips with it: `profile.py`) |
| prep: single-layout dummies | recomputed from `centerline.local.json`, 8 pits, facing `atan2(E, N)` | the draft's `data/dummies.json` (the engine's placement on the finished centreline; the recomputation only with no draft), facing `atan2(E, −N)` at the start — the measured convention of the per-layout spawn scenes (`tools/layout_dummies.yaw_deg`, ledger 0047) | single-layout tracks; `verify_kn5` single-layout branch has no facing check, so the old `atan2(E, N)` (a north-bound grid facing south) would have shipped silently |
| `write_ai_line` grid check | `dummies_<id>.json` only (single layout: "unverified") | falls back to `data/dummies.json` on a single-layout track | the direction contract is now checked there too |
| `check_lights_ini` (track-folder step, both chains) | crashed on a track with no `data/lights.local.json` (every track but Lake Murray) | no lamps file = nothing to match: PASS, unless the written ini carries a `[LIGHT_N]` with no lamp behind it (FAIL, a stray light) | the Exotics full run of 2026-10-29 stopped here after `verify_kn5` PASS |
| prep: terrain contact conform (`build_kn5_loop._conform_and_reseat`) | always, on every 1GRASS mesh | skipped on an engine draft (`data/underlay.report.json` present: the ground is build_mesh's, conformed to the road per L3); `track.config.json prep.terrain_conform` true / false overrides | the conform was written for the SD assembler's independent terrain grid; on an engine draft its 3 + 6 m feather pulled the embankment up to deck height and left a cliff: Milford 75 and High Plains 103 excursion drops > 20 cm at 10–12.5 m lateral, Sand Creek 217 (the V1 Milford build: 1). Reproduced and fixed on Milford's draft here: 1 → 0 gated drops with the conform off, the engine's own numbers otherwise. SD unchanged |
| `from_track` smoother (`scripts/gps/from_track._smooth`) | 5-fix moving average, always, not circular | `source.smooth_window` (default 5; 0 = none for a node list); wraps on a closed loop | High Plains' 79 OSM nodes were cut 26.8 m at the corners and the ring's ends parted 466 m (bridged with a chord): the deck floated and the engine minted four bridges. With 0: the line is on the source polygon to 0.00 m, closing gap 0 |
| the install guard (both chains) | refused while `acs.exe` **or** Content Manager runs | refused while `acs.exe` / `acs_x86.exe` runs; Content Manager may stay open | Kevin, 2026-10-27, on the Windows box's auto-memory, verbatim: "you can install when that's running just not while AC is driving the track" (CM does not lock the track files; a running game does). A loosening, on his word; relayed by the Milford bridge session 2026-10-29 |

No threshold moved. Tests: `tests/geometry/test_dummies_draft.py` (the yaw agrees with `layout_dummies.yaw_deg` on
every heading), the frame refusal in `test_ship_track_chain.py` (a guard run on IMI's V1-frame config).

### Same day — the gate line on an engine draft (Sand Creek's three bridges; wiring, no threshold)

Sand Creek's second chain run (the conform skipped) went red on `drive_test` with 127 severe steps of up to 1.75 m,
12 "ground on top" and 12 daylight gaps, every one inside the three bridge spans the mesh had levelled over the creek
(`evidence.level_bridge_decks`, max lift 7.9 m), while `audit_mesh` and `kn5_ground_check` were green. The gate was
walking the wrong line: `drive_test`'s `top_at(y_ref, window=2.5)` takes the highest drivable surface within 2.5 m of
the gate centreline's height, and the loop prep (`scripts/ac/build_kn5_loop.declare_bridge_spans`) had **overwritten
build_mesh's `data/finished_centerline.json`** — the swept line, corner-rounded, smoothed, decks levelled — with the
raw `centerline.local.json` line (its Y the bare-earth profile, diving into the creek), which `kn5_to_gate_obj` then
handed to the gates as `gate_centerline.json`. Wherever the deck rode more than 2.5 m above the raw line it left the
window: a step reading where it left and where it came back, the creek bed as "ground on top" in the one band where
it was inside the window, nothing (no reading at all) through the middle. The conform-on run had been green on the
same spans only because its anti-poke pass had put the grass at deck−0.02 under the decks, so both surfaces left the
window together and no step could register. V1 was never exposed: `scripts/build.sh` ran the gates on the engine's own
file. The prep was written for San Diego, whose assembler has no engine draft and whose raw line IS the line.

| Check | Was | Is | Scope |
|---|---|---|---|
| prep: the gate line (`declare_bridge_spans`) | always the raw `centerline.local.json` line → KN5 frame; `bridge.spans.auto.json` from an OSM-way scan | an engine swept line in `data/` (build_mesh's, frame "mesh …") goes to the KN5 frame with its widths and **its** auto spans (the stations the builder left open are the stations the gate exempts); the prep's own earlier write (frame "kn5 …", a `--from prep` re-run) stays; with neither, the raw line as before, now marked `frame`/`source` | every chain track with an engine draft; SD unchanged. An unmarked file beside an engine draft is an earlier prep's raw copy: WARNING printed, the engine's line is back on the next run from the draft |
| `tools/ship_track.sh draft_mesh` | left the last run's `data/gate_centerline.json` | removes it before `build_mesh` (a `drive_test` on the draft's OBJ would prefer the stale kn5 line) | the draft-only test the Windows box runs |

Expected on Sand Creek: the 127 / 12 / 12 vanish with the frame of reference, and what is left on the spans is the
mesh's. The same cause behind Milford's 15 lane steps in the banked esses against the draft's 8, measured on its
committed draft: the swept line's six largest plan offsets from the raw line (0.38–0.54 m) are at stations 792–807,
where the chain's gate read every one of those steps (s 795–808). Tests: `tests/ac/test_loop_conform.py` (the engine's line kept,
levelled deck and rounded corner intact, OSM scan not run; a re-run keeps the prep's copy; the lost-line warning).

### Same day — the ring rotation and the elevation file (High Plains; wiring, no threshold)

High Plains' full run at `59bd8f0` (0.68.0) passed `drive_test` (severe 0, excursion drops 0 gated), `audit_mesh` and
`verify_kn5`, and **failed `kn5_ground_check`: road floating over ground, p95 gap 0.604 m > 0.1 (149 / 919 samples,
16.2 % over 0.05 m)**, with the mesh step printing "bridge spans: 1 (['1126-1675m']) — deck+piers, no fill" on a
course with 15 m of relief and no bridge, and `drive_test` replication 2.91 / 12.08 / 14.62 m. Found by the Windows
bridge session, checked on the data: `scripts.geometry.projection` rotates the ring to `route.start_at` (815 of 1,074
points) AFTER the elevation stage has written `centerline.elevation.json` in `centerline.geojson` order, and two
readers paired the two files by bare index — `build_mesh`'s bridge detector (`raw_ground`, the along-road 3DEP
profile the span test compares the deck against) and `drive_test`'s replication. The detector saw the bare earth 2.4 km
along the lap under every road point, read an invented 549 m valley and built a deck with no fill over real ground;
the kn5 gate caught the road floating. Cyclically shifting the elevation by 815 points puts the deck on the smoothed
profile to 0.01 m median / 0.16 max — the deck itself was right. The same artefact sat under the earlier High Plains
run (rotated 251 points: four fake spans, replication p95 11.3) and under Exotics' replication 1.79 / 2.84 / 3.06
(rotated 48 points, no span crossed the detector's threshold), V1 included; Milford and Sand Creek are not rotated.

| Check | Was | Is | Scope |
|---|---|---|---|
| `projection` (route orientation) | re-ordered coords / widths / z, wrote nothing about it | also writes `source_index` (local point i ← geojson/elevation point) and `route_orientation` into `centerline.local.json` when `route.reverse` / `route.start_at` changed the order; an unrotated file is byte-identical | every rotated or reversed track |
| `build_mesh` bridge detector (`raw_ground`) | `z_raw_m[i]` against local point i | `projection.in_local_order(local, z_raw_m)` — identity without a recorded re-ordering | the span test compares the deck with the ground under it again |
| `drive_test` replication | `z_raw_m[i]` against gate point i (handled `reverse`, not rotation) | the same mapping before the lap / reverse handling | the "replication vs measured road" number is a measurement again on rotated tracks |

No threshold moved; `BRIDGE_MIN_H_M` 3.5 / `BRIDGE_MIN_SPAN_M` 12 unchanged. Expected on High Plains: no span,
the fill back under the road, `kn5_ground_check` green, replication at Milford's level (0.02). Tests:
`tests/geometry/test_projection_orientation.py` (the recorded permutation lines the elevation up with the rotated,
reversed and rotated-and-reversed line; the bare-index pairing is wrong at every point; no route = no key).

### Same day — the builder's mirror of the excursion sweep, and the weld's cap (Sand Creek's draft; builder side, no gate moved)

With the gate line and the rotation right, Sand Creek's chain run was red on two things the draft itself carries and
the gate was right about: 2 "ground on top" at the pavement lip (s 8047 / 8461, cuts) and 8 "floating furniture" on
one stone lip (s 6522, the approach to span 3). Diagnosed on the committed draft (`a856cbe`) with cross-sections of the
rebuilt OBJ; both are late `build_mesh` passes (ledger 0060 has the measurements).

| Check | Was | Is | Scope |
|---|---|---|---|
| `build_mesh` measured-guard sweep (the builder's 1:1 mirror of `drive_test`'s outboard crossing) | same origin, band, stride and flare exemption as the gate — but not the gate's **declared-span ± 20 m** exemption; no height rule | skips declared spans ± 20 m as the gate does; refuses a lip whose inboard surface is already > 1.5 m under the deck (a deck-edge element; the face above it is the pavement's own) | the lip at the toe of a 6 m retaining wall on a bridge approach (5.7 m under the deck, two feet over a bank falling 4 m) is gone; 14 of 472 lips removed on Sand Creek, 2 ordinary ones added |
| `build_mesh` seam-weld floor cap | road / runoff / kerb | + the shoulder, less its buried hem (`ribbon` returns `hem_idx`) | in a cut the floor off a ring edge 2 m above the road lifted the pinned shoulder band back to natural (+1.5 .. +2.3 m of dirt over a 1ROAD_shoulder at deck height); with the hem in the cap the toe apron broke at every fill (999 lips, far ledges 26 — rebuild 2) |

`drive_test` on the rebuilt draft: ground on top 0, floating 0, severe 1, excursion drops 2 gated, far ledges 7 (the
baseline's). No gate threshold or exemption changed. Tests: `tests/geometry/test_build_mesh_edge_rules.py`.

## 2026-10-28 — scripts/build.sh runs no gate any more, because it builds no track (ledger 0060; ONE-CHAIN §2 row 1)

Wiring only, no threshold moved. `scripts/build.sh` is cut to the engine's draft (`gps elev project mesh` →
`data/track.obj`); its `env / blend / kn5 / pack` stages and the four gate calls they carried (`drive_test`,
`audit_mesh` on the OBJ after `env`; `verify_kn5`, `kn5_ground_check` after `kn5`) are gone with them. The gates
run where they always ran for Lake Murray: in the chain's `gate` phase (`tools/ship_track.sh`: `drive_test_street`,
`audit_street`, `kn5_ground`, the race gates), on the BUILT kn5 (L5), with the thresholds unchanged. The native
kn5 path (`KN5_WRITER=native`, `scripts/ac/kn5_write.py`) is no longer a build path; the writer stays as the
gate tests' fixture harness only. Proven: `tests/ac/test_build_kn5_loop.py::test_the_chain_wires_the_loop_program_and_the_draft_builds_no_track`.

## 2026-10-26 — Lake Murray expansion P4 integrated (v0.19.1, Drive 2) + the lenses' fix round (ledger 0054 "P4 — dressing, integrated")

The four P4 branches (lamps, buildings + rock, trees + GrassFX, signs + map) merged as unions onto airoso main 1b5a6b3
(ledger 0054 "P4 — dressing, integrated"; the four entries above are each piece's own). The merged branch was
rehearsed on the full chain, refuted by the four verification lenses on the built output, fixed at the causes and
rehearsed again. **No threshold moved anywhere in this entry.** Every number below is in the code beside its reason.

### The two gate widenings of "P4 signs", restated so nobody reads them as a loosening later

| Gate | Was | Is | Scope |
|---|---|---|---|
| `verify_kn5` (f) closure kn5 / `check_race_kn5 --role closure --owner T` | `1WALL_RACE_CLOSE_T_*` only | + T's OWN `SIGNPLATE/SIGNARROW/SIGNPOST_T_<k>` meshes and their materials / textures; `--role common` gains a NEW refusal of any sign plate | the owner token only; a plate of another layout is still refused |
| `verify_signs` (g) for kind LAYOUT | on_road refused | on_road allowed on the sealed opening's deck (that layout does not drive it); instead (c) 1.3–3.0 m of clearance to the layout's own sealing wall + on_wall refused | LAYOUT plates only; the shared W1-6 plates keep (g) |

### The fix round — new rules, every invented number

**`tools/make_treefx.py` — the built-surface guard** (lens: 11 north plants on `1GRASS_ROCK` faces, 2 on a walk, 593
inside building footprints). Every guarded plant is read against the gate OBJ (`data/track.obj`) LAST: dropped when the
plan triangle under it is `1ROAD*` / `1KERB*` / `1GRASS_ROCK*` / `HOUSE*` / `BUILDING*` (first match wins), or when a
HOUSE / BUILDING triangle lies within `BUILT_BUILDING_CLEAR_M` **1.0 m** ⚠ (the apron rule's own margin: a bush against
a wall is a hedge, a trunk inside a wall is a tree through the roof). `BUILT_CELL_M` 12 is a bucket size, not a rule.
The islands' plantings (`median_planting`, `north_median_trees`) are unguarded (they stand on the pavement under their
island by design). Without the OBJ (verify_race G on the plan, before Blender) nothing is guarded; the written file is
re-judged with it. The report (`data/treefx.report.json rejected_on_built_surface[_loop_zones]`) counts each reason.
Hard? No new exit; `verify_race --scenery-only` on the written file is the hard gate as before.
**As written** (run 2's own post-check of the written file: one loop Sage 4 mm clear of a building ring in the plan, 6 mm inside it once rounded to the file's centimetres): every spot is rounded to the file's 0.01 m before any guard judges it, and the plan's entries carry the rounded spot. Not a threshold — the file's own precision.

**`tools/rock_faces_rules.py` + `tools/rock_faces_blend.py` — the boundary clean-up** (lens: a sawtooth of 1–2 m grass
teeth along the whole Jackson 1225–1525 toe; 146 steep grass faces / 115 m2 inside Jackson's faces). On the band's
face set, after the per-face slope rule (unchanged, 0.7 m/m) and before the hole fill:
- speckles under `MIN_PATCH_M2` 40 dropped first (so the smoothing cannot join outcrop speckles into a wall);
- `smooth_boundary`: a grass face with ≥ 2 of its 3 edge-neighbours rock → rock; a rock face with ≥ 2 grass
  edge-neighbours (among band faces) → grass; both read one state per pass (synchronous); `SMOOTH_PASSES` **2** ⚠ (a
  tooth is a one-triangle feature; more passes only walk a strip's end back one triangle per pass — the asynchronous
  6-pass first cut eroded 2,556 faces and never settled);
- `fill_tongues`: a grass component under `MAX_HOLE_M2` 60 (unchanged) whose boundary sides are `TONGUE_ROCK_FRAC`
  **0.6** ⚠ or more against rock (a side with no neighbour — band edge, mesh edge — counts as open) → rock;
- speckles dropped again; `CLEAN_ROUNDS` **2** ⚠ (the second round catches the first's own teeth).
A face with a corner BENEATH a pavement sheet may never become rock, in every rule (the self-check refuses it as before)
— and "beneath" now reads height: the sheet above the corner must be higher than it by `BENEATH_TOL_M` 0.005 m (a
corner over the walk's buried apron, 0.2 m below the ground, is not beneath anything; in plan alone every toe
triangle along the walk was "under"). Measured on run 1's pre-rock scene (offline, `D:/k10-scratch/p4/integrate/fix/
rock_test6.log`): grass / rock teeth 379 / 893 → 100 / 137; rock 10,716 faces / 12,459 m2 → 9,803 / 11,936 m2 in 8
meshes (B_right_711_896's 42 m2 patch gone as a speckle); 179 tongue faces in 82 tongues filled; 0 beneath-pavement
teeth. Reported in `data/rock_faces.json boundary_smoothing` (teeth before / after / per zone). No vertex moves.

**`scripts-v021/blender/build_loop_blend.py build_buildings`** (lens: footprints 1.9–9.3 m from their true place; 10
new houses with a wall corner on Del Cerro's walk, 25 within 5 m of a road surface):
- projection: `_meters_per_degree` = the roads' WGS84 series (`scripts-v021/geometry/projection.py`), replacing
  111320·cos(lat) / 110574 (0.1 % / 0.3 % short at 32.79° — 9 m south at J4, 2.7 m on the loop). Not a gate number:
  a measured error at its cause. It moves every building, the loop's 153 included (≤ 5 m), stated in the ledger.
- `BUILDING_CORNER_CLEAR_M` **3.1 m** [std: the curb profile's width, curb face 0.08 + walk 1.8 + grade strip 1.2]:
  no footprint corner within it of the pavement's edge (centre distance less half width, bucketed nearest), in both
  bands, besides the centroid rule (`BUILDING_CLEAR_M` 5.0, unchanged). Offline replay on run 1's inputs
  (`p4-proofs/analysis/count_bands.py`): 334 → 329 (old band 153 → 145, north 61 → 62, Del Cerro + stubs 120 → 122);
  the corner-clearance histogram with the rule off: 24 under 5 m, 6 under 3 m, 2 under 1 m (those two ON the walk).
- `house_seat_check` thresholds unchanged; it re-judges every building at its new place.

**Terrain beyond 40 m, stated as measured** (lens: "identical to v0.19.0" fails as a vertex-set test): 3,108 ground
vertices only in the merged build and 221 only in v0.19.0 beyond 40 m of any road, the surface within 4 cm (p95), one
lattice point 1.26 m off on a 1.7 m/m bank at (−1764, 2793) — the thinning keeps a different set after the release's
re-triangulation ([thin] 983,255 → 526,101 vs 983,650 → 515,973). "No vertex moves" is true of the release and rock
steps, not of the shipped vertex set. No gate reads that set; `rib_check` and the drive gates read the surface.

### Measured — run 1 (merged, before the fix round) and run 2 (after), against the v0.19.0 floor (r3run)

| Gate / count | v0.19.0 (r3run) | run 1 (ecf5f5d) | run 2 (fix round) |
|---|---|---|---|
| Free Roam ground-on-top / severe / kinks / excursion drops / audit | 8 / 0 / 2.67 / 96 / 53 | 8 / 0 / 2.67 / 96 / 53 | 8 / 0 / 2.67 / 96 / 53 |
| Speedway / Reverse severe, kinks, barrier_missing, audit | 4 / 6, 6.46 / 6.09, 0, 53 / 53 | same | same |
| no_route cw / acw | PASS 0/439 both | PASS 0/439 both | PASS 0/439 both |
| lines expansion fwd / rev (kinks, drops) | PASS 2.39 / 2.53, 40 / 38 | same | same (far ledges fwd 21 → 20, ungated) |
| verify_mouths / stubs / pads | 32 / 26 + 29 / J2–J4 PASS | same | same |
| verify_signs posts | 19 | 29 PASS | 29 PASS (4 layout plates) |
| rib_check step jogs (densest) | 69 (4 / 5) | 69 (4 / 5) | 68 (4 / 5) |
| house_seat_check | PASS 153 | PASS 334 | PASS 329 |
| kn5_ground_check x3 (lamp posts) | PASS (238) | PASS (323) | PASS (323) |
| check_lights_ini / `[LIGHT_n]` | — / 238 | 323 / 323 | 323 / 323 |
| TreeFX plants (built-surface drops) | 15,739 | 21,171 (—) | 20,464 (rock 10, walk 2, building 695) → 20,463 as written (building 696); post-check 0 / 0 / 0 |
| rock faces / m2 / meshes; teeth grass / rock | — | 10,716 / 12,459 / 8; — | 9,805 / 11,935.7 / 8; 380 / 893 → 100 / 137 |
| buildings (old band / new band) | 153 | 334 (153 / 181) | 329 (145 / 184) |
| road kn5 bytes (ceiling 145 MB) | 89,815,220 | 94,316,244 | 94,173,764 (+4.36 MB vs v0.19.0) |
| `[GRASS_FX]` tiles | 16 | 16 (no rock, no far ring) | 16 (no rock, no far ring) |
| chain end | NOT INSTALLED (2 pre-existing reds) | same | same |


## 2026-08-10 — Baseline inventory (no changes; recording current state)

Re-derived directly from the engine at `v0.66.3`+, not inherited. The v2-reboot draft that seeded
this file cited line numbers from prodrive-ac-builder `3e1aa52`; all but one had moved, so every
row below was re-read from the current source. Nothing here is endorsed by being listed.

### Bypass environment variables — both still live

| Var | Where | Effect | Flag |
|---|---|---|---|
| `GATE_EXCURSIONS_ADVISORY=1` | [drive_test.py:718](../scripts/geometry/drive_test.py:718) | Unguarded off-road drops report but don't gate. Comment says "NEVER set for a full (non-rc) release" | ⚠ remove once the construction selector lands |
| `GATE_CONTACT_ADVISORY=1` | [kn5_ground_check.py:648](../scripts/ac/kn5_ground_check.py:648) | Overrides the measured road-contact fraction | ⚠ remove |

A bypass that outlives the reason it was added is indistinguishable from a lowered bar. Both carry
a named owner in their comment; neither has a removal date.

### `drive_test` — the seat-time proxy

| Threshold | Value | Flag |
|---|---|---|
| bump step | 2.5 cm ([:39](../scripts/geometry/drive_test.py:39)) | |
| severe step | 6.0 cm ([:40](../scripts/geometry/drive_test.py:40)), gate at **>12/km** ([:728](../scripts/geometry/drive_test.py:728)) | ⚠ invented |
| bumps/km | **75 tarmac / 150 gravel** ([:713](../scripts/geometry/drive_test.py:713)) | ⚠ **self-referential** — the 75 line is calibrated against Sand Creek's own output (~19/km), and the code says so |
| excursion drops | >1 per km fails ([:724](../scripts/geometry/drive_test.py:724)) | ⚠ a car-destroyer allowance |
| obstructions / undrivable corners / floating furniture / soft-top-in-lane / daylight gaps | gate at 0 | correct shape — count, not tolerance |
| cornering model | 1.3 lat-g, 30–260 km/h, calibrated at 100 km/h ([:49–52](../scripts/geometry/drive_test.py:49)) | hand-calibrated |

The gravel split (150/km) is the one threshold here with a real argument behind it: Dragon Tail
measures ~114/km straight off 1 m lidar of the actual road while its severe rate and replication
both sit well inside their limits — holding a rally stage to the tarmac line would mean smoothing
it until it drove like a circuit. That reasoning is in the source; it is the model the other
numbers should follow.

**Open against this gate:** ledger 0031 — Bathurst builds to 2.38 m RMS against the Kunos scan and
still fails at 94.4 bumps/km. Two hypotheses (elevation source, profile smoothing) are dead with
evidence. The limit itself is a live suspect precisely because of the ⚠ above.

### `audit_mesh`

| Threshold | Value | Flag |
|---|---|---|
| grass poke above road | 0.10 m within 5.0 m ([:29–30](../scripts/geometry/audit_mesh.py:29)) | |
| pier "standing in the road" | within 3.5 m xz, 1.5–45 m below deck ([:31–32](../scripts/geometry/audit_mesh.py:31)) | |
| wall float | a 0.6 m column floats only if no supported column within reach ([:338–362](../scripts/geometry/audit_mesh.py:338)) | neighbour-forgiveness — bought by a real false positive (a seated wooden fence read as +1.6 m floating because min-y was the rail) |

Historical note: this repo's k10-colorado fork grepped a `KERB` prefix against groups named
`1KERB_*` for months, so the curb-flush check reported "0 of 0" — a gate that passes by finding
nothing is worse than no gate. Fixed by the un-forking (`registry.json`).

### `verify_kn5`

| Threshold | Value | Flag |
|---|---|---|
| vertex cap | 65,535/mesh | AC hard limit |
| drivable faces pointing up | ≥90% ([:33](../scripts/ac/verify_kn5.py:33)) | |
| pit/start box to road | ≤13.5 m xz, ≤1.0 m dy ([:34–37](../scripts/ac/verify_kn5.py:34)) | |
| terrain pokes tolerated | **20** ([:40](../scripts/ac/verify_kn5.py:40)) | ⚠ the one line the draft cited that hasn't moved — still a nonzero hole allowance in a shipped kn5 |

### `kn5_ground_check`

| Threshold | Value | Flag |
|---|---|---|
| import/export float tolerance | 0.08 m ([:35](../scripts/ac/kn5_ground_check.py:35)) | |
| sampling | every 23rd vert per bucket ([:36](../scripts/ac/kn5_ground_check.py:36)) | sampled, not exhaustive |
| deck vs mountain | 0.05 m, fraction over it must be **0** ([:37–40](../scripts/ac/kn5_ground_check.py:37)) | correct shape |
| p95 gate | 0.10 m ([:51](../scripts/ac/kn5_ground_check.py:51)) | measured — set from imi/second-creek/pueblo/high-plains p95s recorded in the source |
| bridge-span exemption | span half-length + **170 m** of approach ([:264](../scripts/ac/kn5_ground_check.py:264)) | review — a large blanket, and 0008 was a phantom gate born of exactly this kind of carve-out |

### Wiring

`build.sh` runs all four gates hard under `set -euo pipefail`. Stage-resume (`build.sh <dir> mesh`)
skips gates bound to earlier stages — a resumed build is not a gated build. `build_network.sh` and
`build_loop.sh` are separate paths and do not run the full set; REALISM §4 folds them into one
gated export path (`scripts/blender/export.py`, R3, not started).

## 2026-10-08 — median island awareness (ledger 0037)

**Change.** `scripts/geometry/median_zone.py` (new) reads `data/median_bands.json` — the per-vertex
island width `tools/median_envelope.py` writes for divided roads — and the gates consult it:

| Gate | Before | After |
|---|---|---|
| audit **D** walls-on-road | every median-barrier vert counted (25,896 on Lake Murray r2) | verts on the declared island band exempt |
| audit **K** kerb-in-carriageway | island curb counted (4,213 incl. ~3,100 island) | island band exempt — K measures *intrusions* again |
| audit **I** sidewalk-isolating | island curb counted (pavement on both sides, by design) | island band exempt |
| drive_test wheel paths | centre pair swept over the island (curb = "severe step", deck = "soft top in lane") | on island stations the ten paths move into the driven lane; step/kink memory resets at island boundaries |
| drive_test obstruction scan | 6.3 m disc on the centreline — the barrier/planting at every island station (2,670 + 2,589 hits) | on island stations, and within 2 stations of one (the disc otherwise reaches the nose), the scan covers the driven lane instead |

**Why it is not a bypass.** The exemption is a *band* (island half-width + 0.6 m, laterally,
±2 m along), only where the track declares an island, only for the three checks whose invariant
("nothing that is not road stands on the road") the island legitimately breaks. The island's own
correctness is still gated: the kn5 rename pass enforces its curb is `1KERB` (collidable) and its
deck `1GRASS`; `verify_kn5` still checks the spawn and face-up; F (curb flush) is untouched. A
track that declares no island gets no exemption (`median_bands.json` absent → zone `None`).

**Measured basis.** rt_macau / union_island / ks_black_cat_county dissections
(docs/JUNCTIONS.md): islands and traffic islands stand ON continuous pavement in every pro track
measured; a gate that forbids that forbids the professional pattern.

**Still owed (0036 / C2).** K becomes part of the *hard* exit total once the connector-mouth
sidewalk sweeps are gapped — until then K would fail every street track on inherited defects.

### Same day — gate centreline frame (a wrong-frame gate, found while measuring the above)

`drive_test` prefers `data/finished_centerline.json` (the line the ribbon was swept along). On the
loop path that file is written by `build_kn5_loop` **in the kn5 frame (z mirrored)** for
`kn5_ground_check`, while `kn5_to_gate_obj` un-mirrors the kn5 into the **engine frame** for
`drive_test`/`audit_mesh`. Result on Lake Murray r2: the drive test swept a z-mirrored path over a
local-frame OBJ — "14 obstructed stations", a 0.4 m step at the median run end, island soft-tops
— **all from the wrong side of the map**; the correct-frame run finds different, real defects
(a 1.5 m step and palm trunks at the College/I-8 approach). The median-zone exemption inherited
the same mismatch and exempted nothing (D 25,896 → 25,812).

Fix: `kn5_to_gate_obj` now also writes `data/gate_centerline.json` (finished_centerline with z
un-mirrored, i.e. the OBJ's frame) and `drive_test` + `median_zone` prefer it. Nothing else
changes: `finished_centerline.json` stays in the kn5 frame for its kn5-reading consumers. A gate
walking a line in a different frame than its mesh is the phantom-gate class (0008); this entry
exists so the next person who sees a "clean" OBJ-gate run on a Blender-first track asks which
frame it walked.

## 2026-10-10 — GrassFX occluder allow-list: `BUILDINGS` → `BUILDING` prefix, `HOUSE` added (ledger 0045)

`scripts/ac/ext_config.py` `OCCLUDE_PREFIXES` (airoso + the engine-july build-of-record copy,
md5-identical) is the crash guard: a far-field or oversized mesh enrolled as a GrassFX occluder
explodes the occlusion volume at session load and freezes the whole PC (shipped v0.12.1–v0.12.6).
It is an allow-list of near-field, ground-seated solids and stays one.

| | Before | After |
|---|---|---|
| building prefix | `BUILDINGS` (Sand Creek's plural) — Lake Murray V3's singular `BUILDING` mesh **not** matched, blades through every building pad | `BUILDING` — a prefix, so `BUILDINGS`, `BUILDING_a..` and `BUILDING` all match |
| houses | no prefix — V3's `HOUSE` mesh skipped | `HOUSE` added (`WAREHOUSE` does not start with it; listed separately as before) |

**Measured basis** (gate OBJ `k10-sd-v021/project/data/track.obj`, 2026-10-10): `BUILDING` 1,637
verts, X −2174..452 / Z −1591..1774; `HOUSE` 10,335 verts, X −2078..2532 / Z −1740..1787 — both
inside the 1ROAD lap extent. The V3 occluder envelope grows from 4,698 × 3,413 m / 140,338 verts
(16.0 km²) to 4,805 × 3,527 m / ~152k verts (16.9 km²): still exactly the lap, nothing elevated,
nothing far-field, against the v0.12.x failure's 24,000 × 1,450 m MOUNTAINS backdrop. Every dry-track
author in the census lists building floors/walls (nohesi `?Building?`, Targa, PCH).

**Why not a per-track add list.** The add list is the crash class; the only way to enrol a mesh
stays the prefix table plus `tests/ac/test_ext_config_occluders.py` (which now pins `BUILDING`,
`HOUSE` in and `LIGHTPOST_0` out). Review discipline unchanged: every ship diff shows the
`OCCLUDING_MESHES` line, and a future far-field mesh named `HOUSE*` / `BUILDING*` would be
auto-enrolled — the same class of review `BUILDINGS` already carried.

Same commit: the `[GRASS_FX]` writer (`scripts/environment/treefx.py`) moves to the grammar every
shipped CSP config uses and rejects unknown/retired keys; `lighting.grassfx = {"enabled": false, …}`
takes the OFF branch. Not a gate change — recorded in ledger 0045 and `docs/TREEFX-FORMAT.md`.

## 2026-10-10 — `verify_signs` ship gate (ledger 0044)

**Change.** A new gate, `tools/verify_signs.py`, runs in `tools/ship_sd.sh` right after the W1-6
authoring step (after the lamps step, inside the `SKIP_BLEND` block) and before the prep/export. It
reads `data/signs.local.json` — the record `tools/place_signs.py` writes and
`tools/author_signs_blend.py` extends with the Blender measurements — and exits 1 on any FAIL;
under the script's `set -euo pipefail` that exit propagates through `| tail -3` and **aborts the
ship before a kn5 exists**. Per sign:

| Check | Threshold | Flag |
|---|---|---|
| (a) ray strike | the failed-to-turn ray from A along t passes within ±0.61 m of the plate centre (half the 48 in plate), tested at the **un-slid** post point base − slid_m·u (the lamp/plant slide along the curb, ≤ 1.0 m, is the only lateral deviation the rule allows; a paired post adds half its pair split) | the sign stands where a car that did not turn would hit it (MUTCD 2C.09) |
| (b) facing | \|angle(f, −t)\| ≤ 1° — the plate looks straight back down the approach heading | |
| (c) built-edge clearance | mainline 1.3–3.0 m, connectors ≥ 1.0 m, **measured two ways and both must pass**: (1) the minimum distance from the base to the built outside-edge polyline the authoring pass recorded (`built.outside_edge_xz`, ROAD-top probes per station); (2) with `--blend`, an independent BVH top-surface scan inside Blender (ROAD vs CURB/SIDEWALK/TERRAIN, 5° polar scan at 0.25 m steps, bisected; `tools/signs_mesh.py`, `data/signs_measured.json`). Nothing self-reported is read. | ⚠ tautological in the first dry run — see below |
| (d) outside of turn | cross(t_local, C − P) > 0 for D < 0 — the side is a geometric test, never a convention | |
| (e) / (f) heights | plate bottom = y_base + 2.13 ± 0.05 m; post base = y_base − 0.30 ± 0.05 m (n/a on an analytic run with no Blender section) | |
| (g) obstacle disc | no SIGN* vertex inside drive_test's min(lane_half, 6) + 0.3 m disc of **any** centreline, the post's own side street included (4.9 m on a 10 m street) — recomputed by the verifier from the centreline/connector json over the plate footprint (base ± 0.61 m along every plate's right vector); and the base is off pavement (measured clearance > 0, scan `on_road` false). Connector posts can now trip it; the authoring pass marches a post along its ray until both the clearance and the disc hold and SKIPS a corner that cannot satisfy both within 6 m of the built curb | extended this round: connectors were "measured for the record" only |
| (h) one per approach | exactly one record per id (+1 under the hairpin clause), none at a `signs.json` `skip` id, no `-fwd`/`-rev` twin of a paired post | |
| (i) spacing | no two posts' bases closer than 2.0 m, across approaches and ribbons — not only the hairpin clause's ≥ 12 m. A two-way corner whose two posts would stand < 2.0 m apart on the built mesh is emitted as ONE post carrying both plates (`place_signs.merge_pairs`) | added this round (absent at `ac8975d`) |
| (j) expect_arrow | the placed arrow (left / right) equals `signs.json`'s per-corner `expect_arrow` where one is declared; the placement itself skips such a corner with a logged reason rather than relocating it | added this round (the key existed in `signs.json`; nothing read it) |
| Blender normals | `blender.normal_mismatches` = 0 — every plate, arrow and post polygon faces as emitted | |
| harness | every `"$BL" --background --python` call in `tools/ship_sd.sh` carries `--python-exit-code 1`; `author_signs_blend.py` unlinks `signs.local.json` / `signs_preview.svg` / `signs_measured.json` at start, so a Python exception inside Blender can neither exit 0 nor leave the previous run's record for the gate to pass | added this round |

**Measured basis.** The thresholds are the sign's own dimensions (0.61 m = half of 48 in), the
MUTCD mounting rule (2.13 m = 7 ft over a walk, 2A.15), the walk section the loop is built with
(curb face 0.08 + walk 1.8 / 1.5 − 0.25 set-back = 1.63 / 1.33 m;
`scripts-v021/blender/build_loop_blend.py:658/677`) and drive_test's existing disc. None of them is
calibrated against our own output.

**⚠ Check (c) was tautological in the first dry run — fixed this round.**
`author_signs_blend.mesh_sign_point` wrote `mesh_clear_m` as `(curb_face + walk_w) × frac`, i.e.
the design constant (1.63 / 1.33), and the verifier preferred that key, so `1.3 ≤ clear ≤ 3.0`
compared the target with itself and was green on all 20 signs — including seven connector posts the
polyline field put ON pavement (`edge_clear_m` −0.06 … −1.74 at DCL-2 fwd/rev, MED-6 fwd/rev,
MED-8-rev, MED-10-fwd, MED-13-rev) and the DCL-2 pair standing 0.44 m apart. That is the mirror
class the standing rule at the top of this file describes: a value written by the thing being
checked is not a measurement. This round (c) becomes the perpendicular distance from the post to
the built curb face found by the ray-cast, and the spacing and `expect_arrow` rows are added so the
DCL-2 overlap and a mirrored plate fail by number. The six mainline signs (M1, M2, M2-2, M3, M4,
M5) passed on the built mesh with 0.06–0.61 m mesh shifts and are held to ±0.3 m through the fix.

**Not changed.** `drive_test`, `audit_mesh` (never reads `SIGN*`) and `verify_kn5` are untouched.
`kn5_ground_check`'s `SIGNPOST` bucket (0.08 m) is not run by `ship_sd.sh` and would flag the
0.30 m post sink if it ever is — exempt the bucket or sink 0.08 m then (0044, Verification §3).

## 2026-10-11 — race layouts: divider bands, per-layout drive test, spawn kn5 checks (ledger 0047)

**Change.** `data/barrier_bands.json` (the centre chain's 0.67 m base per vertex, the kerb-line
barrier strip on both curb faces with its 0.82 m lane inset, the three sealed-mouth polylines, the
seven race-kerb runs — written by `tools/barrier_bands.py` from the declared `race.centre_runs`
and VALIDATED there, the file `tools/author_race_blend.py` builds the strips from) joins
`median_bands.json` as a second divider kind in `scripts/geometry/median_zone.py`. The kinds load
independently; default `contains()` kinds stay `('island',)`, so every existing caller and every
track without the file gets byte-identical numbers; a length mismatch disables that kind only,
loudly. The gates consult the barrier kind only for layouts with `race_furniture: true`:

| Gate | Before | After |
|---|---|---|
| audit **D** walls-on-road | every race 1WALL vert counted (the strips would add ~117k) | `--race [--obj track.race.obj --out audit.race.json]`: verts on the declared centre band (0.335 + 0.6 m laterally, 2 m along), edge band (\|lat − (w/2 − 0.485)\| ≤ 0.935) or a mouth polyline exempt; K/I island-only (the 0.05 m race kerb is under K's 0.10 m); **E and F unchanged** — E is the strips' seating gate |
| drive_test lanes | ten paths about the centreline, clamped ±6 m of it; island stations move right | one run **per layout** (`run(project, layout)`; CLI `--layout <id>` repeatable, default every `layouts[]` entry); `direction: reverse` walks the lap backwards (points, widths, bands, bridge spans, replication); kind `race` is judged on `data/track.race.obj`; lane = (dh + 0.4 + 0.75) .. (w/2 − inset − 0.4 − 0.75) with dh = max(island half, chain half 0.335), inset the kerb-line strip's; no divider + no inset = today's lines verbatim; clamp lane-relative \|off − mid\| ≤ min((hi − lo)/2, 6); step/kink memory resets when the lane moves > 0.5 m |
| drive_test obstruction disc | centreline disc; lane disc on island stations ±2 vertices | lane disc on every divider/edge station and within **7 m** along the line of one (`NEAR_DIVIDER_M`: the 6.3 m disc reaches a strip end or nose from 6 m out); a station with no divider of its own borrows the nearest one's; inner edge 0.1 m off the divider face, outer edge 0.1 m off the kerb-line strip's face |
| drive_test `barrier_missing` (new) | — | race layouts: at every station whose BOTH bracketing vertices declare a band, a 1WALL must stand within ±0.3 m of the band centre (chain: centreline; strip: w/2 − 0.485 each side) rising > 0.25 m over the deck; no hit within half a module (4.04 / 2 m) along the band = missing; **gate 0**; per-layout files `data/drive_test.<id>.json`, `data/drive_test.json` becomes the summary (`fail` = any layout) |
| verify_kn5 | spawns within 13.5 m of road, main or `__*.kn5`, no facing read | `len(layouts) > 1`: (a) road and race kn5 spawn-free, exactly one `<slug>__<id>.kn5` per id, no stray; (b) each spawn kn5 nodes-only, carrying exactly `dummies_<id>.json`'s set, START/PIT/HOTLAP on the road kn5's 1ROAD; (c) heading: local +Z (node matrix row 2) · the layout's kn5-frame travel at the nearest `finished_centerline.json` vertex ≥ cos 30° ⚠, dot printed; (d) START/PIT right of travel ((−t.z, t.x) in the kn5 frame), ≥ 0.335 + 1.0 m ⚠ off the centreline where the chain is declared; (e) AC_TIME_0 within 2 m of `start.line_vertex`, 0 < d ≤ 35 m ahead of AC_START_0, sectors increasing in driving order (L11); (f) race kn5: every mesh and material RACE-named, ≥ 1 1WALL_RACE and 1KERB_RACE, under the cap, no dup name across road + race, no spawn node, < 20 MB. Single-layout tracks: unchanged. `_parse()` keeps its 2-tuple shape; `_parse_full()` adds the heading and the material names |
| tools (self-gates, exit 1) | — | `barrier_bands.py`: every run vertex ≥ 17 m wide, off any island except a run END on the nose vertex (one short = fail), not on a narrow street, not inside a hairpin arc (\|D\| ≥ 135°), ≥ 9 m ⚠ clear of a declared bridge span; edge gaps == bridge spans; grid columns clear of the strip face. `layout_dummies.py`: ids unique and never `full`/`freeroam`, direction ∈ {forward, reverse}, kind ∈ {street, race}, `race_furniture ⇒ race`, vertices in range, AC_TIME_0 0 < d ≤ 35 m ahead of the pole, sectors increasing in driving order on a < 1°/vertex ⚠ straight off any island |

**Why it is not a bypass.** Bands only where the track declares a strip and only for the layouts
that load it; a strip off its band still fails D; the strip must be present (`barrier_missing`,
with the 4.04 m continuity rule), seated (E, floating furniture) and clear of the swept lane (the
lane disc); the anticlockwise carriageway of College/Navajo/Jackson/Lake Murray is swept for the
first time. The street layout never reads the bands and never loads the race kn5.

**Measured basis.** centerline.local.json 4,499 verts / 13,480.1 m; Alvarado 13.0 m on v25–723,
every other mainline run 17–32.5 m; five islands 2,474 m; declared chain 6 runs / 8,525 m on 2,851
verts ending on the ten nose vertices (v780 and v4440 the free ends); kerb-line strip on 4,393
verts, gapped only inside the three declared spans (v609–619, v856–902, v4444–4491); module
0.67 × 1.20 × 4.04 m (249 verts, measured off `assets/models/concrete_barrier_4m.obj`); grid
clearance +0.08 m at 8 slots (car edge 5.60 m vs strip face 5.68 m on 13.0 m Alvarado).

**Dry run (2026-10-11, a scratch copy of the 2026-10-09 workshop build under the three-layout
config; no kn5 exported, nothing installed).** street: ground-through-lane 82, floating 391,
severe 0, excursions 101 (79 far), obstruction 0, kinks 4.97/km — every key identical to the
2026-10-09 `data/drive_test.json`; audit D 512 / K 154 / I 145 / F 15 identical; `--race` audit on
the same OBJ: D 512 (no existing wall stands on a declared band). race_cw / race_acw on the same
OBJ (no strip built yet): obstruction 0 in BOTH carriageways, ground-through-lane 65 / 13 (today's
82 split by lane), `barrier_missing` 34,833 / 34,833 → FAIL — the gate has teeth. Wall time:
street 11 s, both race runs 21 s, audits 10 + 9 s, verify_kn5 7 s on the 92 MB kn5. verify_kn5 on
today's road kn5 under the three-layout config: refused (16 spawn/timing nodes in the road kn5, no
race kn5, three spawn kn5s missing) — exactly the state the ship chain must not pass.

**Still owed.** The 30° heading, 0.4 m lane clearance, 1.0 m chain straddle, 4.04 m continuity,
7 m transition window, 9 m bridge clearance, 1°/vertex sector straightness and the kerb lengths
are ⚠ invented pending a measured envelope; `kn5_ground_check` still not in the SD chain; the
race-run wall time with ~153k 1WALL verts (strips built) is to be re-measured on the first ship.
engine-july mirrors of `median_zone.py` (new there), `drive_test.py`, `audit_mesh.py`,
`verify_kn5.py` are plain copies of airoso's (engine-july is a dangling worktree: nothing there is
committed; the md5s live in the 0047 handoff/commit).

### Same day — the lane sweep's centre clamp

`drive_test.py` clamped every wheel path to ±6 m about the centreline, written for the centred sweep
and never made lane-relative when the island sweep landed (2026-10-08): seven of ten island paths
collapsed onto 6.0 m and the inner wheel LINE at isl + 0.4 sat the wheel 0.35 m inside the island
curb. Fixed with the lane-relative clamp and the wheel-line at dh + 0.4 + 0.75. Measured on
Lake Murray: no island-station count moved (82 / 82 ground-through-lane, 0 / 0 obstruction).

### Same day — spawn facing

Measured on the workshop road kn5 (2026-10-09 ENG prep): AC_START_0 local +Z · AI travel =
−1.00. Two stacked causes. (1) The prep yaws every facing dummy with the SEAM tangent
`cl[0]→cl[1]` (ledger 0016's class) while `place_dummies` put the grid on Jackson — the Alvarado
westbound heading applied 5.5 km away. (2) The add-on's `convert_matrix` (decompose → quaternion
axis (x, z, −y)) maps `rotation_euler.z = ψ` to kn5 local +Z = (sin ψ, cos ψ): predicted
(−0.952, −0.307) for the seam ψ, measured (−0.95, −0.31). With ψ = atan2(tx, tz) (the prep and
`tools/set_start_blend.py`) +Z = (tx, tz) while the kn5-frame travel is (tx, −tz): +0.81 on the
seam heading, −0.98 on north-south College (the installed build's −0.91). Fixed in
`tools/layout_dummies.py` (ψ = atan2(tx, −tz) at the dummy's OWN vertex, +π for `reverse`),
gated by verify_kn5 (c); `tests/ac/test_verify_kn5_layouts.py` pins the derivation on the real
centreline. k10-colorado's reverse layouts (`kn5_write.py:362`) share the reflection — ledgered,
not fixed here.

### Same day — the ship chain's own gates (ledger 0047, wiring)

`tools/ship_sd.sh` is now the three-version chain (street + race_cw + race_acw; one road kn5,
one race-furniture kn5, three spawn kn5s). What it gates on, beyond the entry above:

| Gate | What it checks | Exit |
|---|---|---|
| `tools/verify_race.py` (new, after the author step, before any kn5 exists) | `data/race_authored.json` vs `data/barrier_bands.json`: A provenance (not a stand-in, same edge_mode / height, RACE prefixes, no failed run, ≤ 1 % interpolated rings); B budgets per object (≤ 900 rings, < 60,000 positions, loops × 1.5 < 65,535 render verts, unique RACE name, seating gap ≤ 0.05 m); C chain (one object per declared run, every ring on a declared vertex, never on an island beyond the nose, never on Alvarado / inside the hairpin arc, run ends within 1.5 m of the declared vertices, parts joined); D kerb-line strips (every declared vertex has a ring on each side except the author's fold-dropped count, no ring inside a bridge span, every `join` end met, every `free` end at a declared gap); E kerbs (declared set == authored, corners match); F spawn clearance (no overlap, real dummies) | 1 on any miss |
| race kn5 size | `build/<slug>_race.kn5` < 20 MB ⚠ (a leak of road geometry or the texture table into it) | 1 |
| `kn5_to_gate_obj --kn5 road --kn5 race --out data/track.race.obj` | ONE gate OBJ for the kn5 set a race layout loads (vertex offset carried across files); the name has a DOT because the loop prep merges every `data/track_*.obj` into the scene — the tool refuses a `track_*.obj` output | 1 |
| `--force-install` | never covers a race layout red on `barrier_missing` or obstruction (no reference exists to be "no worse than"); the street layout keeps the July-reference comparison rule | 1 |

**Not a gate, but load-bearing.** The prep (`build_kn5_loop.py`, both the engine-july pin and
airoso's copy) creates NO `AC_*` empties and writes `data/dummies.json = {}` when `len(layouts) > 1`,
and keeps the authored UVs of `1WALL_RACE*` / `1KERB_RACE*`; `export_kn5_addon.py` takes `--blend`
/ `--out` and runs once per split scene with one `.ini` per pass; the race author step runs on
every ship (also `--skip-blend`) so `loop.blend` never drifts from `race.*` in the config.

**Dry run (2026-10-11, scratch copy, `--skip-blend --dry-run` then the gate half by hand).**
bands → dummies → author (36 objects / 122,338 positions, 0 interpolated) → verify_race OK → prep
(`multi-layout (3 layouts) … dummies.json = {}`) → split on the PREPPED scene (race: 36 meshes /
36 RACE-named materials / 0 AC nodes; main: 0 race / 0 AC; problems []) in 23 s. Gates on the
existing road kn5: street 82 / 391 / 0 / 101 and audit 512 / 154 / 145 / 15 — identical to
2026-10-09; race_cw / race_acw `barrier_missing` 34,833 / 34,833 FAIL (nothing built yet) →
`RACE_RED = race_cw race_acw` → the install block refuses even with `--force-install`; verify_kn5
refuses (16 spawn nodes in the road kn5, no race kn5, three spawn kn5s missing). Wall: gate OBJ
5 s, street drive_test 11 s, audits 9 s, both race drive_tests 20 s, verify_kn5 5 s, packer 7 s.

### Same day — race gates tightened and extended (ledger 0047 fix round)

| Gate | Was | Now | Basis |
|---|---|---|---|
| `verify_race` F spawn clearance | the AUTHOR's record only: FAIL on overlap (clear < 0), a note below 0.30 m | **re-measured by verify_race itself** from every race layout's `data/dummies_<id>.json` (what `build_spawn_kn5` ships) against the declared strip faces (bands params: `half_w + edge_centre_from_lip_m − barrier_half_m`; chain `centre_w / 2`); FAIL when a 1.9 m car on any grid / pit / hotlap slot is < **0.30 m** off a face; the author tool's record fails on the same floor | ⚠ 0.30 m is invented (no measured reference grid-to-wall gap yet); it replaces a 0.08 m clearance (1.4 m stagger) that passed. Proven: synthetic slots at 0.73 / 0.23 / −0.27 m pass / fail / fail-OVERLAP (`tests/tools/test_verify_race.py`); real data 0.48 m on AC_START_1/3/5/7 of both race layouts |
| `barrier_bands` no-gap zone | FAIL when the outer grid column overlaps the strip face (clear < 0) | FAIL below **0.30 m** (the same floor); the stagger / pitch / pit constants are now READ from `tools/layout_dummies.py` instead of restated (a stale 1.4 m copy would have declared a clearance the grid does not have) | as above; `no_gap_zones.grid_clearance_m` 0.08 → 0.48 on all three layouts, nothing else in `barrier_bands.json` changed |
| `verify_race` G lamp masts (new) | — | every lamp mast (base = `lights.local.json` head set back road-ward by `author_lamps_blend.ARM_M`, parsed from that file; footprint radius from `assets/models/lamp_post.obj` at `POST_H`, 0.585 m) stands OUTSIDE every kerb-line strip and centre-chain footprint; FAIL on any overlap (margin < 0), minimum margin reported | geometric (an overlap is a mast inside a barrier), not a tuned number. Real data: 238 of 239 masts beside a strip, minimum margin 2.36 m, none inside |
| `verify_race --pre-author` (new mode) | — | F + G alone, no `race_authored.json` needed | wiring only; the ship chain still runs the full check after the author step |

**Texture binding (not a gate, found while auditing what ships).** `pbr.network_walls: true` (Lake
Murray, for the merged freeway's barriers) reskins the generic `1WALL` key; the race strips had no row
of their own and fell through to it. The prepped dry-run scene of 2026-10-11 00:47 bound
`building_diffuse/normal.jpg` on 29/29 `1WALL_race_*` materials. `scripts/ac/pbr.py` (airoso and the
engine-july copy, byte-identical) gained `1WALL_RACE` / `1KERB_RACE` rows ahead of the generic ones;
the re-run binds `concrete_barrier_*` on 29/29 and `kerb_diffuse.png` on 7/7.
`tests/ac/test_pbr_race_rows.py` resolves both names with network_walls on and off.

### Same day — race kn5 judged on content; ring density becomes a gate (ledger 0047 weld pass)

| Gate | Was | Now | Basis |
|---|---|---|---|
| race kn5 guard (`tools/ship_sd.sh`, after the race export) | `build/<slug>_race.kn5` < 20 MB ⚠, "the split leaked road geometry or textures into it" | **content**: `python -m scripts.modkit.inspect_kn5 <race kn5> --json data/race_kn5.json`, then `tools/check_race_kn5.py`: FAIL unless every mesh upper-starts with `1WALL_RACE` / `1KERB_RACE`, every embedded texture is in the race set READ from `scripts/ac/pbr.py`'s `1WALL_RACE*` / `1KERB_RACE*` rows (kerb_diffuse.png, concrete_barrier_diffuse.png, concrete_barrier_normal.png), no node (transform or mesh) is named `AC_*`, and at least one mesh exists; the size is printed with verts / tris / ratio and WARNs at ≥ 20 MB, never fails | the size cap fired on the first real rehearsal for a kn5 that leaked nothing (36 RACE meshes, 3 race textures, 35,553,024 B — flat shading made it 2.98 verts per triangle); size measures shading, not leaks. `inspect_kn5`'s parse gained a `nodes` list (class-1 node names: the root `BlenderFile` here) so the AC_* check is not blind. Proven: `tests/tools/test_ship_sd_chain.py::test_race_kn5_guard_is_a_content_check` (clean passes with a size WARN; a road mesh, a road texture, an `AC_START_0` node, no mesh, a parse without `nodes` each FAIL); the old kn5 passes content with the WARN, the road kn5 fed to it FAILS on 31 meshes / 14 textures; the rebuilt race kn5 passes (12,558,972 B, 0.81 per triangle) |
| `verify_race` H ring density (new; was the "spacing reaches 7.02 m … chords ~0.39 m" note) | reported, never gated (estimate gap² / (8 × 16 m)) | every consecutive pair of chain / kerb-line strip ring centres vs the DECLARED offset curve, rebuilt in verify_race from the bands + centreline alone (centre lerped along each centreline segment, left normal of the normalised lerp of the two vertex tangents, declared lateral `half_w + edge_centre_from_lip_m` lerped; lat 0 for the chain; 32 samples per interval): chord error > **0.15 m** FAILS; spans where the declared curve folds back (inside lips the author chords on purpose) are counted, not judged; rings > 0.5 m off the curve or spans > 40 intervals are counted unmeasured (C / D judge those); spacing above 3.5 m is a note | ⚠ 0.15 m is invented (the author's target is 0.10 m, `race_furniture.CHORD_MAX_M`; 0.15 leaves room for the 0.01 m rounding of `ring_centres`). Measured: the pre-densify authored file chords 0.271 m at the seam corner's outside lip (`1WALL_race_edge_L_lakemurray_4492_0`) and 0.171 m at the hairpin → FAIL; the densified one 0.043 m, spacing 3.50 m → OK. `tests/tools/test_verify_race.py::test_ring_density_is_judged_against_the_declared_offset_curve` (on-curve strip passes, one ring dropped on a 109.5 m lip 0.05 m passes, five dropped 0.49 m FAILS, a ring shoved 0.31 m off FAILS, H never runs without widths) |
| `audit_mesh --race` D exemption (`scripts/geometry/median_zone.py` barrier kind) | each declared band POINT owns a ±2 m-along × (0.335 + 0.6) m-lateral rectangle; the closure duplicate of a closed lap was a band point of its own (the LAST street's width, 27.5 m vs v0's 17.0 m on SD) with one-sided tangents at both seam vertices (6.8° off) | the band is **continuous between consecutive declared vertices of the same kind** (distance to the segment between their band points, the same 0.935 m reach; the ±2 m rectangles still own a run's ends); on a closed lap the duplicate is vertex 0's band and the seam tangents wrap (central difference) | no widening: same lateral reach, nothing past a run's end. The ±2 m rectangles only covered the declared strip where band points stand ≤ 4 m apart; on the outside lips of the five corners they stand ~7 m apart, and the densified rings in those gaps read as **460** walls on the road (race D 512 → 972 on the first weld-pass rehearsal); with the continuity 28 remained, all on `1WALL_race_edge_L_lakemurray_4492_0` at the seam — the duplicate's width put its band point 5 m inboard. Both fixed: race D 512 on the new kn5 set AND on the pre-weld one (`track.race.base.obj`, i.e. nothing the old build counted is exempted now), street D untouched (it never reads the barrier kind). `tests/geometry/test_median_zone_kinds.py` (mid-gap points inside, 2.5 m past a run's end still outside, the closed-lap seam band at vertex 0's width with a wrapped normal; the three tests fail on the previous module). drive_test reads only the per-vertex lookups, not `contains`, so its numbers cannot move. engine-july's copy (`dc1b2ef1…`, not run by the ship chain's gates) is NOT edited — the two copies now differ |

**Not a gate, but load-bearing.** `tools/author_race_furniture_blend.py` now smooth-shades every RACE
object (`Mesh.shade_smooth`) and marks hard only the edges `race_furniture.sharp_edges` (> 30°) and
`kerb_outline_edges` return, and refuses to save if the flags did not land. The prep was read, not
edited: `DOUBLE_SIDE` (`1WALL`, `HWYSTRUCT`) appends reversed faces only to groups merged from
`data/track_*.obj` / `env_*.obj` (none on SD), so a `1WALL_race_*` from `loop.blend` is never
doubled — the 241,190 triangles the old race kn5 carried are exactly the authored quads × 2 + caps;
its bmesh round trip keeps the smooth / sharp flags (measured on `loop_race.blend` after prep + split:
7,158 / 7,158 smooth faces and 4,300 hard edges on `1WALL_race_kbar_navajo_2297_0`, as authored), its
face-up pass reverses 2 of 4,545 kerb faces (the hairpin fold of `1KERB_race_770_in`), and it only ever
sets `use_smooth = True` (above 65,535 loops; no RACE object comes near). engine-july
`scripts/ac/build_kn5_loop.py` md5 2dcc8e8b9d4024ec9a9ee3fadb1236b8 and airoso's
8752e96360b2882021c089322f0e5771, both unchanged.

### Same day — the race furniture gates measure the built lane and the built corner (ledger 0047 red-gates round)

The first full REAL rehearsal of `tools/ship_sd.sh` (scratch `SHIP_PROJ`, `--skip-blend`) passed everything
except the race layouts' own furniture gates: race_cw obstruction **220** / `barrier_missing` **22**,
race_acw **175** / **32** (34,833 probes each). Three read-only diagnoses replayed the gates on the built
OBJ; the stations split into two gate bugs and one geometry bug, and every fix below is measured on that
rehearsal.

| Gate | Was | Now | Basis |
|---|---|---|---|
| `drive_test` race lane width (race layouts only — the street layout and every single-layout track read `widths` exactly as before) | the lane and the scan disc at a station between vertices i-1 and i used `widths[i]`, the vertex AHEAD | `_wl` lerped at the station (`w_lane`); on a closed lap the closure duplicate is vertex 0 (it carried Lake Murray's 27.5 m vs Alvarado's 17.0 m — median_zone's rule) | not a threshold. SD's mouth flares grow 0.55–1.50 m per ~3 m vertex, so the lane was up to 1.36 m too wide and the disc reached the PREVIOUS ring of a strip standing on its declaration (OBJ footprint minus declared face: median +0.009 m, 332 of 341 within ±0.03 m): **341 of the 395** obstruction stations |
| `drive_test` race lane clip (new `TriField.rising_in(keep=)`) | a round disc mid-lane (radius half-lane + 0.3, cap 6.3 m) | an obstacle vertex inside the disc counts only if it stands inside the declared lane AT ITS OWN STATION (projected onto the walked line, ±8 segments ⚠, wrapped on a closed lap), with the disc's existing 0.1 m off each face (no new margin) | can only DROP a vertex outside the declared lane; one inside it still fails. The disc reaches as far along the road as across it, so on a steep flare it caught strip rings on their declaration up to 1.33 m behind the station (s2271, s4534) |
| `drive_test` barrier presence (`barrier_missing`) | probe at `widths[i]/2 + edge_centre_from_lip` (the closure duplicate's 27.5 m put the seam probe 5.25 m outboard of the strip); continuity check linear in station, blind across the seam | probe at the lerped width; a station inside a declared trimmed corner (`edge_corners`, below) probes the declared in → X → out polyline at the same fraction of its length, the ±0.3 m spread along the polyline's normal (every declared metre still probed, nothing skipped); on a closed lap a miss within half a module of the seam is covered by hits across it | the seam station s13480 (race_cw edge_L) / s0 (race_acw edge_R) was a gate bug: the forward-left strip there is complete. Skipping the fold stations instead was measured 0 / 0 and REJECTED as a bypass (chords up to 5.26 m > one 4.04 m module would go unprobed) |
| `scripts/geometry/median_zone.py` barrier kind (audit D `--race` exemption, drive_test lookups) | an edge band point at every flagged vertex, incl. the folded inside-lip offsets | `edge_corners` loaded: a trimmed vertex has NO band point on that side; the band across it is the polyline in-vertex band point → X → out-vertex band point (same 0.935 m reach, no extension); `edge_corner_spans(kind)`; `reversed()` swaps the side and maps k → (n−1−k) mod (n−1) | the exemption stands on the built corner only. audit `--race` D 512 → **512** |
| `tools/barrier_bands.py` (the declaration) | inside-lip band points declared on the folded offset curve at every vertex | `edge_corners` (+ `edge_fold_vertices`, `summary.edge_corners`) from `race_furniture.edge_fold_corners` — the author's own plan + trim; FAIL when a fold's removed vertices are > 15 ⚠ vertices from every inside corner apex of that side | SD declares 5, all side R: loop v763→774 (hairpin, −74.9°), loop v1508→1517 (−66.8°), loop v2314→2324 (−92.8°), extend v3292→3300 (−85.7°, 3.09 m), extend v4495→5 (seam, −73.1°, 6.99 m); 41 vertices |
| `tools/verify_race.py` D | `len(missing) ≤` the AUTHOR's own `fold_skipped_run` count — passed 23 missing against 27 self-reported drops that were not the same vertices | a SET check: every declared edge vertex without a ring must be in a declared corner's `removed` (a ring within 0.05 m ⚠ `CORNER_TOL_M` of the vertex's declared band point also covers it — inside a tight corner the nearest-vertex map loses the leg rings); every declared corner must have a ring of that side within 0.05 m ⚠ of its X | ⚠ 0.05 m: `ring_centres` are rounded to 0.01 m and the corner ring stands ON X by construction (measured 0.002–0.006 m) |
| `tools/verify_race.py` H | fold spans counted, not judged (5 fold + 4 unmeasured on the rehearsal) | across a declared trimmed corner the declared curve IS the in → X → out polyline (X a sample), so those spans are measured | rehearsal: 5 fold / 4 unmeasured → **0 / 0**, chord max 0.0428 m unchanged |
| `tools/verify_race.py` I (new) | nothing failed an inverted span | from `ring_centres` + `ring_frames` (tangent + lateral scale per ring, written by the author tool): both extreme profile columns (±`barrier_half_m` × ls; a kerb ±`kerb_width_m`/2 × ls about its mid-line) must advance along each span's mean tangent; any inside-out span FAILS; an object without matching frames FAILS | geometric, not tuned. Built blend (all 36 RACE objects, their own vertices; before = the weld-pass blend authored by HEAD's plan code): **7 → 0** (`edge_R_alvarado_620_0` ×3, `college_903_0`, `navajo_1519_0`, `jackson_2324_1`, `1KERB_race_0_in`) |

**The geometry fix (not a gate, load-bearing).** `race_furniture.drop_folded_rings` tested a ring only
against its own tangent, kept the "ear" rings past the offset curve's self-intersection (v768, v1512,
v2317, v3295) and chorded BACKWARDS from them: the inside-out spans above and a hook of wall standing
1–3.5 m inside the exit carriageway of the three chained right-handers (**52** of race_cw's 220). It is
replaced by `_trim_folds` (strips and the inside kerbs): two-sided backward test, folds within 6 m ⚠
merged, the cluster cut where the in- and out-leg cross (`loop`) or where their last real steps extended
≤ 8 m ⚠ meet (`extend`), ONE mitred corner record at X (lateral scale 1/cos(ψ/2), cap 2.0 ⚠), every leg
record nearer X than the mitre's reflex tip + 0.25 m ⚠ dropped; fill rings on a corner chord stand square
to the chord and keep their leg's width. The author refuses a declaration whose `edge_corners` differ
from what it trims (`match_declared_corners`). Kerbs: `1KERB_race_770_in` one loop corner,
`1KERB_race_0_in` one extend corner (+59°, it follows the ribbon's width-step jog at the seam).

**Measured on the rehearsal** (same scratch project, `bash tools/ship_sd.sh --skip-blend`, before →
after):

| line | before | after |
|---|---|---|
| street drive_test: ground-on-top / floating / obstruction / excursion | 82 / 391 / 0 / 101 | 82 / 391 / 0 / 101 (`drive_test.street.json` byte-identical) |
| street audit D / F / I / K (total) | 512 / 15 / 145 / 154 (826) | 512 / 15 / 145 / 154 (826) (`audit.json` byte-identical) |
| race_cw obstruction / barrier_missing | 220 / 22 | **0 / 0** |
| race_acw obstruction / barrier_missing | 175 / 32 | **0 / 0** |
| race_cw ground-on-top / floating / excursion / kinks per km | 65 / 391 / 4 / 5.12 | 67 / 391 / 4 / 5.27 |
| race_acw ground-on-top / floating / excursion / kinks per km | 13 / 391 / 0 / 2.74 | 13 / 391 / 0 / 2.82 |
| audit `--race` D / F / I / K (total) | 512 / 15 / 145 / 154 (826) | 512 / 15 / 145 / 154 (826) |
| verify_race edge missing / fold spans / unmeasured / inside-out | R 23 vs author 27 / 5 / 4 / (not measured) | R 30, all declared (41 trimmed) / 0 / 0 / 0 |
| verify_kn5 | passed | passed |

The race ground-on-top rows moved only in their wheel offsets (the lane is now the declared one): the
same stations before and after (College/Navajo s4535-4539 and Lake Murray s10242-10243, ribbon folds /
ground through the road — inherited, also in the street layout's 82). Gate-only on the OLD build:
52 / 24 and 0 / 28 (all at the folds); geometry-only (old gate on the NEW build): 170 / 60 and 175 / 54 —
neither half alone reaches 0. **Known ribbon defect, not gated:** the seam closure steps 27.5 → 17.0 m in
one 2.29 m segment inside the right-hander, so 4.16 m of the seam corner's 6.99 m polyline stands off
the ROAD ribbon over the curb notch (1 ring seated by interpolation; Jackson/Lake Murray's Z-fold leaves
0.40 m); the fix is a width taper over the seam corner in the centreline data and a ribbon rebuild.
Tests: `tests/geometry/test_drive_test_layouts.py` (a 17 → 24 m flare with strips on their declaration
has 0 obstructions, a ring 1 m in the lane fails; a trimmed corner built by race_furniture passes
presence + obstruction both ways, cut away it fails, undeclared it fails, the untrimmed knot is an
obstruction), `tests/geometry/test_median_zone_kinds.py`, `tests/tools/test_barrier_bands.py`,
`tests/tools/test_race_furniture.py` (an R 8 m / 11.5 m right-hander trims to one mitred corner, no ring on
the lane side of either leg, no inside-out span; the inside kerb too; a drifted declaration is refused),
`tests/tools/test_verify_race.py` (D needs the declaration's trim, not the author's count; a declared
corner must be built; H on the polyline; I fails a turned ring, a backward ring, missing frames).

## 2026-10-11 — `write_ai_line` write-time self-check: geometry refusals, segment ruler (ledger 0047 fix round)

**Change.** The AI draft writer's self-check (it refuses to write; it is not one of the four build
gates) gains geometry refusals and a truer lateral ruler. The audit of the installed three-version
build found race_cw's draft folding at the three chained right-handers (R 0.3 m, 7 km/h at
College/Navajo) and the street draft jogging 21–27° in one step at twelve island noses; both had
passed the old check, which measured only lane clearance.

| Check | Before | After |
|---|---|---|
| fold | — | **refuse** any backward step (a step against the nearest station's tangent) or self-crossing (segments 2–200 apart) |
| curvature | — | **refuse** a step turning > `TURN_MAX_DEG` 10° ⚠ where the road is not that tight (road radius at the point's place ≥ 8.6 m, the radius a 10° step means at 1.5 m), or a 3-point radius < `RADIUS_CHECK` 0.95 ⚠ × min(road radius there, `RADIUS_FLOOR_M` 12 m ⚠). "There" = the tightest raw centreline radius (6 m chord) within ±(3 stations + the point's lateral offset): a lane line rounding a corner sits ~its offset along the leg from the apex. With `--lane-offset none` only the fold refusal applies (the legacy centreline is not reshaped) |
| lateral ruler | nearest declared VERTEX, its central tangent, its own channels | nearest declared SEGMENT (among the segments of every vertex within 4 m of the nearest), signed point-to-segment distance; width interpolated along the segment, divider / island / inset the larger end (the resampler's declaration rule). The apex vertex's diagonal normal overstated a corner-cutting point's lateral by up to (1 − 1/√2) of it |
| edge | kerb-line barrier face − 0.6 m only where an inset is declared | also the pavement edge − 0.6 m where none is (the street layout's lane is "inside the pavement − 0.6 m") |
| divider hits | island hits only | + `divider_hits` (on the island or the chain), reported |

**Why it is not a bypass.** Every old refusal stands (island, divider face + 0.6 m, barrier face −
0.6 m, right side 100 %); the ruler change only removes the vertex ruler's overstatement inside
tight corners (measured: one street point at College/Navajo read 0.34 m from the edge by the
vertex ruler, 0.83 m by the segment it actually sits beside — the ribbon edge is straight between
edge vertices). The new refusals are added, not traded.

**Measured basis (scratch copy of the workshop, `write_ai_line --layout <id>`).** street / race_cw /
race_acw: 0 backward steps, 0 self-crossings, 0 steps > 10° (installed: 29 / 17 / 16), min radius
12.5 / 12.6 / 10.3 m (installed 3.28 / 0.27 / 4.27), min divider clearance 4.21 / 1.51 / 3.39 m, min
edge clearance 0.83 / 3.60 / 3.61 m; Dragon Tail and Under the Dragon (gravel) drafts written, 0 refusals
(Dragon Tail was refused by an intermediate version whose Laplacian smoother dragged R 10 m bends onto
the lane edge — the shipped smoother is a Taubin pair that returns its best state). ⚠ 10° / 12 m /
0.95 are the ledger-0047 audit's numbers, not measured envelopes. Tests:
`tests/ac/test_ai_line_geometry.py`, `tests/ac/test_write_ai_line_layouts.py`.

## 2026-10-11 — race corridors: `no_route` containment gate, barrier_bands v2 self-gates, per-layout lanes (ledger 0049)

**Change.** Kevin's race brief ("the entire other lane blocked off from access", "an Alvarado's width for
the entire track", open intersections at the corners the race turns at) replaces 0047's shared centre
chain with one closure per direction. Nothing gated containment before this: every gate checked the lane
the car is *supposed* to drive, none checked that it cannot leave it. New and changed gates:

| Gate | Before | After |
|---|---|---|
| **`tools/no_route.py`** (new, hard) | — | flood fill per race layout from `AC_START_0` on the layout's BUILT gate OBJ (`track.<id>.obj` = road + common race + that layout's closure kn5): FAIL on any cell reached outside the declared corridor, on a reached forbidden probe, or when a lane-centre cell / `AC_START_n` / `AC_PIT_n` is not reached ("corridor blocked at v…"). Writes `data/no_route.<id>.json`, exit 1. A v1 declaration is read with its own semantics (chain / island face) |
| no_route PLANNED (new, inside `barrier_bands.py`) | — | the same fill on the declared polylines (both strips with trimmed corners + this layout's closure + mouth lines, ±0.335 m) before any authoring; `data/no_route.<id>.planned.json`. Not an L5 gate: the declaration checking its own topology |
| `barrier_bands.py` | v1: chain runs validated (17 m threshold, nose butt joints, hairpin arc, `BRIDGE_CLEAR_M`), strips gapped at the bridge spans | v2 self-gates (exit 1): zones cover every vertex once, boxes hold their corner arcs, derived runs == `race.corridor.closure_runs`; pins on the far strip centre ±0.01 m and not on a trimmed fold vertex; rates (toward the race side ≤ 1:12, away ≤ 1:6, pin zones ≤ their forced rate +2 %, nothing steeper than 1:3); clear ≥ 6.5 m everywhere, ≥ 10.86 m except listed island / pin-zone / convergence vertices; pocket ≥ 2.0 m behind every running closure; closure ≥ 0.15 m off the AUTHORED island (nose taper included) at every vertex; 0 backward steps; plan radius ≥ 20 m; mouth policies; grid + pit slots ≥ 0.30 m off both lane faces; exactly 10 kerbs ≥ 0.05 m off every closure; strips on every vertex; `centre_runs` refused; the Alvarado re-measure within 0.02 m of `clear_width_m`; planned no_route 0 leaks, lap complete |
| `median_zone` | one barrier zone for every race layout | `MedianZone.load(project, layout=<id>)`: both curb strips + THAT layout's closure band (same ±(0.335 + 0.6) m, continuous between declared vertices); `lane_r(i)`, `closure_at(i)`, `zone_at(i)`. Without a layout: unchanged. A v2 file without the asked layout: SystemExit |
| `drive_test --layout` (race, v2) | lane = divider face .. kerb-line face, neighbour borrowing near dividers; OBJ `track.race.obj` | lane = the declared `lane_by_vertex` faces lerped at the station, `DIVIDER_CLEAR_M` 0.4 inside each face, no borrowing (the declared lane is continuous; boxes / whole street are full width, 6.3 m disc cap kept); `barrier_missing` adds key `closure` (probed on the line between the two declared ring centres); OBJ default `track.<id>.obj`; report `lane`. v1 files: unchanged |
| `audit_mesh --layout <id>` | `--race`: D exempt on every declared band | D exempt on that layout's bands only (its closure, never the other direction's); defaults `track.<id>.obj` → `audit.<id>.json`; **new W** = a race-strip vert inside another wall's footprint or vice versa (plan ±0.05 m, inside its height range), hard under `--layout`, reported under `--race` |

**Retired.** `BRIDGE_CLEAR_M` 9 m (invented); "edge gaps == declared bridge spans"; the 17 m
`wide_threshold_m`; the nose butt-joint rule; the hairpin-arc chain rule; `declared_open`. The three
bridge spans had no rail on most of their length (Alvarado v609-619 none at all; College rail only
v864-887 of v856-902; I-8 only v4454-4474 of v4444-4491): a strip gap there was a door.

**Teeth (measured 2026-10-11 on scratch copies; nothing built, exported or installed).**

| Run | Result |
|---|---|
| TODAY's installed race build (`track.race.obj`, v1 semantics), race_cw | **FAIL** 752,562 m² outside the corridor, 11 door clusters: Alvarado bridge v606-620 L+R, College bridge v854-903 (race side), I-8 bridge + chain end v4438-4493 L+R, chain end v779-781, all five islands' race faces nose to nose (the beam alone is not a wall) — every door escapes to the open map |
| same, race_acw | **FAIL** 752,263 m², 11 clusters, the mirror |
| planned v2, race_cw / race_acw | **PASS** 0 / 0 leaks, 139,130 / 138,826 m² reached (the study's prototype: 138.8 k / 138.4 k), lap complete |
| planned v2 with today's bridge gaps put back | **FAIL** 5 clusters per layout at exactly the uncovered spans (v608-619 L+R, v855-902 race side, v4443-4491 L+R), 210 / 406 probes reached |
| v2 swept into a virtual BUILT OBJ (declared strips + closure seated on the deck + today's road-kn5 `1WALL_guard`) | **PASS** 0 leaks both layouts, 0 / 406 probes reached, spawns reached |
| synthetic (tests) | sealed L-corridor passes both ways; 1.5 m door FAILS at its vertex/side (off_road, escapes); 0.8 m crack passes; beam-only closure (0.63-0.93 m) FAILS, posts or not; unpinned closure end FAILS (opposite); cross wall → "blocked"; seed in a wall → exit 2; reached probe FAILS |

The prototype counted 51 "clusters" because it bucketed door cells per 4 vertices and never merged
same-side buckets; the gate clusters door cells spatially (cells within 2 m), so the same doors read as 11.

**Regression floor.** The street layout's paths are untouched (no layout → the zone, lanes and OBJ are
today's). Today's race OBJ re-audited under `--race`: D / K / I / F = 512 / 154 / 145 / 15 (the stored
`audit.race.json`), W = 0. Planned v2 strips stand 0.15 m inboard of the College and I-8 deck rails in plan.

**Wall rule detail (measured).** Per cell the union of the height ranges of the wall triangles touching it
and its 8 neighbours must cover every 0.05 m bin of [deck + 0.20, deck + 0.90] (deck = the centreline y at
the projection + 0.10). One cell alone sees only one face of the jersey profile (the steep face is 0.47-1.20,
the toe 0-0.38), so the 3 × 3 union is what makes a K-rail a wall; the beam (0.63-0.93) stays open. Today's
race strips measured: base -0.05 m, top +1.15 m relative to that deck (the v2323 ribbon fold: base -0.52, top
1.16 — still spans).

| Value | Status |
|---|---|
| cell 0.25 m, tile 64 m, domain w/2 + 25 m, PROBE_R 0.5 m, TOL 0.75 m, wall band 0.20-0.90 m, height bin 0.05 m + 3 × 3 union, door link 2 m | ⚠ INVENTED |
| pocket 2.0 m, hard minimum 6.5 m, floor 10.86 m (band −0.5 / +1.5), rates 1:12 / 1:6 / I-8 1:10, steepest 1:3, pin zone 120 m, base ±60 m / σ 20 m, island envelope 30 m, attract 40 m, smooth 4 m, opening ≤ 100 m, radius floor 20 m on a ±6 m stencil, box pad 2, kerb clip 0.05 m, convergence reach 150 m, W tolerance 0.05 m, mirror report window 100 m | ⚠ INVENTED |
| clear width 11.36 m (re-measured 11.36: median w − 2 × 0.82 on Alvarado), strip inset 0.82, strip centre 0.485, K-rail half base 0.335, nose 0.25 m over 3 vertices | MEASURED |

Tests: `tests/tools/test_no_route.py`, `tests/tools/test_race_corridor.py` (the port reproduces the study's
solution, fixture `tests/tools/fixtures/sd_corridor_proto.json`, to 1 mm), `tests/tools/test_barrier_bands.py`
(every v2 self-gate fires on its crafted defect), `tests/geometry/test_median_zone_kinds.py`,
`tests/geometry/test_drive_test_layouts.py`, `tests/geometry/test_audit_race_flag.py`.

### Same day — the authored furniture, the export split and the kn5 checks (ledger 0049, geometry)

**Change.** The furniture behind the corridors: both curb strips authored as ONE closed loop per side (across
all three bridges), each race layout's closure authored into its own collection (`RACE_CLOSE_CW` /
`RACE_CLOSE_ACW`) and exported to its own kn5, the 10 race kerbs clipped against every closure. The gates that
judge it before and after the export:

| Gate | Before | After |
|---|---|---|
| `verify_race` C (chain) → **C′ closures** | one chain object per declared centre run, rings on centre_w vertices, never on an island / Alvarado / the hairpin arc, ends within 1.5 m of the run's vertices | per race layout: one object chain per declared closure run, parts joined on a shared ring (0.05 m); EVERY ring within `CLOSE_TOL_M` 0.05 m of the declared closure line (closure_y lerped between vertices, the densify curve); no declared closure vertex in a BOX / WHOLE zone; each run's first / last ring AT its pin: within `PIN_TOL_M` 0.05 m of the declared far curb-strip line, at the pin vertex ±1 |
| `verify_race` D | every DECLARED edge vertex covered (gaps allowed), "no ring inside a bridge span", a `free` end must stand at a declared gap | EVERY centreline vertex covered on both sides, bridge spans included (C1 — the inversion), except the declaration's `edge_corners[].removed` (set check, unchanged); declared corners built (unchanged) |
| `verify_race` E | declared (apex, in/out) set == authored | + each kerb's run == the declaration's (clipped) i/j; + every kerb footprint (mid-line ± 0.5 m × ls) ≥ `KERB_CLEAR_M` 0.05 m off EVERY layout's AUTHORED closure footprint (re-measured on the ring centres) |
| **`verify_race` J** (new) | — | zero free ends: every curb-strip end is a `join` met by a same-side neighbour's end (0.05 m, re-measured); every closure end is a join with its run's next part or a PIN whose centre stands ≤ 0.05 m off the AUTHORED far strip's centre polyline, full height (`h == barrier_height_m`) and full width (`ls == 1`) |
| **`verify_race` K** (new) | — | every closure's name token is a declared corridor token, its record's owner / layout / collection (`RACE_CLOSE_<TOKEN>`) agree; common furniture owns no token and sits in `RACE`; no RACE object of an unknown kind (the old `1WALL_racecol_*` collider included) |
| **`verify_race` L** (new) | — | 0 interpolated rings inside the declared bridge spans (`race_authored.bridge_seating`, the author's new per-ring seat record); every span carries seated strip rings |
| **`verify_race` M** (new) | — | every `closed_mouths` line lies ≤ `MOUTH_TOL_M` 0.10 m from the authored strip of its side (both strips are common: sealed in both layouts); every mouth has a policy per layout; `behind_closure` = that layout's authored closure runs past the whole mouth (on its declared line, the lane on the race side of it) |
| **`verify_race` N** (new) | — | no `1WALL_race_kbar_*` object; `centre_w_by_vertex` all 0; no centre run |
| `verify_race` F / G | edge faces + centre chain | + the layout's declared lane (`lane_by_vertex`) ≥ 0.30 m off each face; lamps vs every layout's closure footprint (lerped at the mast) |
| `verify_race` H / I | chain + strips | strips + closures (closure curve = the declared closure line) |
| `check_race_kn5` | role-free: RACE meshes, race textures, no AC_* | `--role common` (default in the CLI): no CLOSE / KBAR mesh, ≥ 1 `1WALL_RACE_EDGE_*`, exactly the declared kerb count (`--expect-kerbs`, else `len(kerbs)` of `--bands` / the barrier_bands.json beside the parse); `--role closure --owner <t>`: every mesh `1WALL_RACE_CLOSE_<T>_*`, ≥ 1. `check(parsed, allowed)` without a role is unchanged |
| `verify_kn5` (d) | START/PIT right of travel; ≥ barrier_half + `CHAIN_CLEAR_M` 1.0 m off a declared chain | race layout with a declared lane: every START/PIT car (half-width 0.95) inside the lane, ≥ `LANE_MARGIN_M` 0.30 m off each face (kn5 frame converted: lateral-left = (X−PX)·f.z − (Z−PZ)·f.x on the forward kn5 tangent); otherwise right of travel. `CHAIN_CLEAR_M` retired |
| `verify_kn5` (f) | `<slug>_race.kn5`: RACE meshes ≥ 1 wall + 1 kerb, RACE materials, no dup across road + race | common kn5: + ≥ 1 `1WALL_RACE_EDGE_*`, no CLOSE, no KBAR; per race layout `<slug>_closure_<id>.kn5` present, every mesh `1WALL_RACE_CLOSE_<TOKEN>_*` of that layout's declared token (corridors.<id>.token, else layouts[].closure_token), ≥ 1, RACE materials, no spawn node, < 20 MB, no 1-prefixed name shared with road + common; a stray `<slug>_closure_*.kn5` fails |
| **`verify_kn5 --inis` (g)** (new) | — | on the packed `build/<slug>/`: each race `models_<id>.ini` lists exactly [road, `_race`, `_closure_<id>`, `__<id>`], the street's [road, `__street`]; no ini lists another layout's closure; every listed kn5 is in the folder |
| `split_exports_blend` manifest | race scene RACE-only | + `loop_closure_<id>.blend` per race layout; problems for an undeclared token, a KBAR object, an empty closure blend, a closure in `loop_race.blend` (or the other layout's in a closure blend), (race ∪ closures) ≠ every RACE object, a material no kept object uses |

**Retired.** verify_race's chain checks (C), "no ring inside a declared gap (bridge span)", "a free end must
stand at a declared gap"; verify_kn5's `CHAIN_CLEAR_M` 1.0 m (⚠ invented) centre-chain spawn check; the
author's `--standin-bands` and `--collider` (Q11 not built for per-direction closures).

**Teeth (dry run 2026-10-11, scratch copies only; the workshop loop.blend untouched).** Authored on a copy of
the workshop `loop.blend` against barrier_bands.py v2's own declaration: verify_race OK — 15 curb-strip
objects (closed loops, 0 free ends, every vertex covered but the 41 declared trims), 6 + 6 closure objects off
their declared lines by ≤ 0.007 m, 16 pins ≤ 0.006 m off the far strip line and 0.000 m off the authored
strip, 328 bridge rings seated by direct hit, 0 interpolated. Prep + split: `loop_race.blend` 25 meshes,
`loop_closure_race_cw.blend` / `_acw` 6 meshes each, problems []. Exported: `check_race_kn5` OK for all three
roles; the cw closure file checked as `acw` or as `common` FAILS. With the road and spawn kn5s exported too, `verify_kn5` passes on the full scratch build (every race START/PIT inside its lane, nearest face 0.48 m — verify_race F's number), and `verify_kn5 --inis` passes on the folder track_folder packed (after the road kn5 is copied in); the same folder with race_cw's ini pointed at the acw closure FAILS twice. Synthetic tests: every new check with a
passing and a failing case (`tests/tools/test_verify_race.py`, `tests/tools/test_check_race_kn5.py`,
`tests/ac/test_verify_kn5_layouts.py`, `tests/tools/test_race_furniture.py`).

| Value | Status |
|---|---|
| `CLOSE_TOL_M` 0.05, `PIN_TOL_M` 0.05, `MOUTH_TOL_M` 0.10, `KERB_CLEAR_M` / `KERB_CLOSURE_CLEAR_M` 0.05, loop-start margin `FOLD_SEARCH_RINGS` + 2 vertices | ⚠ INVENTED |
| `LANE_MARGIN_M` 0.30 = `SPAWN_MARGIN_M` (2026-10-11), car half-width 0.95 | as before |

### Same day — `write_ai_line` inside the race corridors: face refusals walked along the line (ledger 0049, AI)

**Change.** With a version-2 `data/barrier_bands.json` a race layout's AI draft is written inside
`corridors.<id>.lane_by_vertex` (the retired centre chain is never used; a version-2 file without the
layout's corridor, or with no corridors at all, REFUSES; a version-1 file keeps the 0047 lane byte for
byte). The write-time self-check (it refuses to write; it is not one of the four build gates) gains:

| Check | Before (0047) | After (0049 race layouts) |
|---|---|---|
| ruler | the line's POINTS against per-vertex divider / inset channels | every point of the LINE, walked every `CHECK_STEP_M` 0.25 m ⚠ along each 1.5 m segment, against the corridor's two wall FACES as polylines on the walls' own vertex frame (race_furniture's tangent v−1 → v+1, densified 1 m on the declared curve, fold-trimmed at the five inside lips like the strips) — a chord can pass the sharp trimmed corner X much closer than either end point (measured: 0.53 m between two points both ≥ 0.71 m) |
| corridor | — | **refuse** any probe beyond a face (past a closure, in a side street) or < `CHECK_CLEAR_M` 0.6 m from one (funnels, island faces and the trimmed inside corners included) |
| islands | raw `island_w_by_vertex` (no nose taper) | the island as AUTHORED (author_median_blend: NOSE_HALF 0.25 over NOSE_VERTS 3, MEASURED) is an obstacle of its own: **refuse** a probe on it or < 0.6 m from it; the legacy segment check also uses the authored outline for race corridors |
| sealed mouths | — | **refuse** a probe < 0.6 m from a `closed_mouths` mouth line |
| shape | today's fold / turn / radius refusals | unchanged, and apply |

Line-shaping constants (not refusals, all ⚠ INVENTED): lane-centre smoothing `CORRIDOR_MU_M` 25 m;
open-corner outside hold `BOX_APPROACH_M` 60 m, held `BOX_EDGE_IN_M` 0.25 m inside the comfort edge,
slope-limited at `BOX_EDGE_SLOPE` 1:10 (an earlier version chased the 1:3.3 funnel face and put a
58 km/h flick before an 88 km/h corner); box arcs searched from `BOX_R_MAX_M` 150 m down a 0.92 ladder to
the 12.6 m floor fillet, bisected 8 steps, comfort clearance `FILLET_COMFORT_CLEAR_M` 1.5 m first;
corners turning > `BOX_TURN_MAX_DEG` 170° (the hairpin) keep the floor fillet; an arc window never
reaches into another corner's arc.

**Why it is not a bypass.** Every 0047 refusal stands for the street layout and for a version-1 race
declaration (both drafts byte-identical to the installed ones on the scratch copy). For a corridor the
divider/inset ruler is replaced by the faces it approximated, and judged along the line instead of at its
points — strictly more probes, same 0.6 m floor.

**Measured basis (scratch copy of the workshop; barrier_bands v2 on the ledger-0049 config).**
race_cw / race_acw: 0 probes outside / under 0.6 m / on an island; wall clearance minimum 1.48 / 1.49 m;
sealed mouths ≥ 5.85 / 5.72 m; box arcs v0 45.1 / 47.5 m, v1514 28.7 / 52.3 m, v2319 32.8 / 52.3 m, v3297
44.5 / 58.5 m (0047 drafts floor-limited at 12.6 / 10.3 m there); min radius 12.57 / 12.54 m (the
hairpin), min target speed 50.6 / 50.5 km/h; 0 backward steps, 0 self-crossings, 0 steps > 10°; point 0
on the start/finish line. An independent check against the per-vertex declaration (not the writer's
faces) found 0 violations. Tests: `tests/ac/test_ai_corridor.py`,
`tests/ac/test_ai_line_geometry.py::test_a_point_half_a_metre_from_a_closure_face_is_refused`.

| Value | Status |
|---|---|
| `CHECK_STEP_M` 0.25, `CORRIDOR_MU_M` 25, `BOX_APPROACH_M` 60, `BOX_EDGE_IN_M` 0.25, `BOX_EDGE_SLOPE` 0.10, `BOX_R_MAX_M` 150, `BOX_R_LADDER` 0.92, `BOX_R_BISECT` 8, `BOX_TURN_MAX_DEG` 170, box window up to 108 points | ⚠ INVENTED |
| `CHECK_CLEAR_M` 0.6, `FILLET_COMFORT_CLEAR_M` 1.5, `RADIUS_FLOOR_M` 12 | as before (ledger 0047) |
| island nose `NOSE_HALF` 0.25 over `NOSE_VERTS` 3 | MEASURED (tools/author_median_blend.py) |

### Same day — `tools/ship_sd.sh`: the corridor chain wired, per-layout BUILT gates, RACE_RED on containment (ledger 0049, integration)

**Change.** The ship chain now builds and judges what ledger 0049 declares: barrier_bands v2 (with its planned
no_route) → layout_dummies → the author (`RACE` + `RACE_CLOSE_CW` / `RACE_CLOSE_ACW`) → verify_race → plots →
prep → split (road / common race / one closure blend per race layout / spawns) → exports, each kn5
content-checked → spawn kn5s → AI per layout → verify_kn5 → track_folder → verify_kn5 `--inis` → make_map →
make_treefx → the gates per layout → RACE_RED → sync → install (unchanged mechanics).

| Gate / rail | Before (0047 chain) | After |
|---|---|---|
| planned no_route read-back (new, hard) | — | after `barrier_bands.py` (which already exits 1 on a planned leak) the ship reads every race layout's `data/no_route.<id>.planned.json` and stops before Blender unless it exists, is a report, says `fail` false with 0 leak cells, nothing blocked, no probe reached, no spawn unreached. `--no-planned-route` never appears in the ship |
| closure exports (new) | — | per race layout: `loop_closure_<id>.blend` must exist after the split, is exported to `${SLUG}_closure_<id>.kn5`, parsed with `inspect_kn5` to `data/closure_<id>.kn5.json` and judged by `check_race_kn5 --role closure --owner <token>`, the token read from the DECLARATION (`barrier_bands.json corridors.<id>.token`) |
| common race kn5 check | role-free content guard | `check_race_kn5 --role common --bands data/barrier_bands.json` (kerb count pinned to the declaration) |
| `verify_kn5 --inis` (wired) | — | after track_folder AND after the road kn5 is copied into `build/<slug>/` (before that copy it fails, correctly: the ini names a kn5 not yet in the folder) |
| race gate OBJ | ONE `data/track.race.obj` (road + race kn5) for both race layouts | one per race layout: `data/track.<id>.obj` = road + common race + THAT layout's closure kn5 (the set its ini loads) |
| race drive_test / audit | one drive_test call over both layouts on `track.race.obj`; `audit_mesh --race` → `audit.race.json` | per layout `drive_test --layout <id>` → `drive_test.<id>.json`, `audit_mesh --layout <id>` → `audit.<id>.json` (D exempt on that layout's bands only, W hard) |
| no_route BUILT (wired, hard) | — | per race layout, `python tools/no_route.py "$PROJ" --layout <id>` on `track.<id>.obj` → `data/no_route.<id>.json` |
| stale verdicts | the gates read whatever per-layout file was on disk | every `drive_test.<id>.json`, `audit.<id>.json`, `no_route.<id>.json`, `no_route.<id>.planned.json` and `track.<id>.obj` is deleted before the step that rewrites it, so a gate that does not run reads "not run" (red), never last run's pass |
| `RACE_RED` | rows of `drive_test.json` with `kind == race`: `barrier_missing` > 0, `obstruction_stations` > 0, or `fail` null; checked only when some gate exit was nonzero | keyed on the DECLARED race ids (a race layout missing from `drive_test.json`, or no `drive_test.json` at all, is red) + `no_route.<id>.json` missing, `fail` not false, `leak_cells` > 0, or any `blocked` / `forbidden_reached` / `spawns_unreached`; decided FIRST, independent of the other exits, and never overridden by `--force-install`; a no_route exit ≠ 0 (2 = input error) also stops the install |
| sync back | + `audit.race.json` | + `no_route.<id>.json`, `no_route.<id>.planned.json`, `audit.<id>.json`, `closure_<id>.kn5.json`, `race_kn5.json`; the retired `audit.race.json` is removed from the repo copy; gate OBJs (66-78 MB) are never synced |

**Retired.** `data/track.race.obj` and `data/audit.race.json` (removed from the project at the gate step and from
`tracks/san-diego-lake-murray/data/` at the sync). No constant was added: the ship only wires the gates above.

**Measured — the full scratch rehearsal (P7), 2026-10-11.** A fresh copy of the workshop project (minus
`build/`), `SHIP_PROJ=<copy> bash tools/ship_sd.sh --skip-blend`, run twice on fresh copies with identical
numbers (about 5 min each; the workshop `loop.blend` and the AC folder untouched):

| Gate | race_cw | race_acw | street |
|---|---|---|---|
| planned no_route | PASS 0 leaks, 139,130 m² | PASS 0 leaks, 138,826 m² | — |
| verify_race | OK (common + both layouts) | | — |
| check_race_kn5 | common OK (10,283,552 B, 15 strips + 10 kerbs); closure `cw` OK (5,433,534 B, 6 meshes) | closure `acw` OK (5,432,722 B, 6 meshes) | — |
| verify_kn5 / `--inis` | OK / OK | OK / OK | OK / OK |
| drive_test | barrier_missing 0 / 37,869, obstruction 0, severe 0 (soft top 44, floating 391, excursion 1 — inherited counters) | 0 / 37,870, 0, 0 (soft top 40, floating 391, excursion 0) | 82 / 391 / 0 / 101 — identical |
| audit | D 0 / K 158 / I 145 / F 15, W 0 | the same | D 512 / K 154 / I 145 / F 15 — identical, `audit.json` byte-identical |
| no_route BUILT | **PASS** 0 leaks, 0 / 406 probes, lap complete, spawns reached | **PASS** the same | — |
| RACE_RED | not red | not red | — |

The run ends `NOT INSTALLED` (exit 1) only on the inherited street / race drive_test and audit counters, exactly
as every build of this track has; a scratch project is never installed anyway.

**Named, not exempted.** Race K 158 vs the 154 baseline = 4 verts of the new inside kerb `1KERB_race_1514_in`
at v1518: the road there is two `1ROAD` sheets 0.093 m apart (the College/Navajo inside-corner fold, 0033/0046
class); the kerb sits flush on the upper (driven) sheet and K measures it against the lower one (+0.133 /
+0.136 m). Race D 0 vs the street's 512: all 512 are the road kn5's own `1WALL_guard`, every one inside a race
layout's declared band, where `--layout` exempts D by design — the street audit keeps counting them.

**Teeth on the real kn5s.** `no_route --layout race_cw` on road + common WITHOUT the closure kn5: FAIL, 81,466 m²
through 5 doors (4 opposite, 1 island), 390 / 406 probes reached. On road + common + the OTHER direction's
closure: FAIL, 60,266 m² through 10 opposite doors, 311 / 406 probes, the lap blocked in 20 spans. Tests:
`tests/tools/test_ship_sd_chain.py` (stage order, the per-layout gate loop, RACE_RED and the planned read-back
RUN on crafted verdict files — clean passes, every red condition turns red, a missing `drive_test.json` turns
both layouts red).

### Same day — fix round: no kerb under a road sheet, scenery out of the race lanes (ledger 0049, critic round)

**Change.**

| Gate / rail | Before | After |
|---|---|---|
| `barrier_bands` self-gate 9 (kerbs) | exactly 10 kerbs (hard-coded), each clear of every closure | every detected kerb (2 per corner) is either DECLARED or DROPPED (`kerbs_dropped`, each with its why); none both; each declared kerb clear of every closure. `track.config.json race.kerbs.trims` is the only way a kerb leaves or shortens: `{apex, kind, why}` + `drop: true` or `i` / `j` — a PULL-BACK inside the detected run, in walk order. A trim that matches no kerb, names one twice, lengthens a run, reverses it, mixes drop with i/j or carries no `why` FAILS |
| `verify_race` E (kerbs) | declared set == authored set, i/j equal, clear of the authored closures | + no kerb station under another ROAD sheet: the author measures `objects[].under_road` on the real deck (lip, mid-line and outer edge of every 0.3 m station: two ROAD sheets more than 0.02 m apart within 1.5 m, the upper one more than 0.005 m over the kerb's top) and E FAILS any; a declared-dropped kerb that was authored FAILS by name. An authored file without the measure is a warning (pre-fix-round author), never a pass of the check |
| `verify_race` G (scenery, new) | lamp masts only | + every CSP TreeFX trunk (r 0.30 m, INVENTED: palm trunks are 0.3-0.5 m across) and every W1-6 sign post (`signs.local.json base_xz`, r 0.03 m: the 2 in post) against EACH race layout's lane (`lane_by_vertex`, lerped) and its wall footprints (both curb strips; that layout's closure): a disk overlapping the lane or a wall FAILS. Items farther than half-width + 2.0 m (INVENTED) from the centreline are counted, not measured. The trees come from `make_treefx.plan` (every species assumed present: positions only) at author time |
| `ship_sd.sh` scenery re-check (new, hard) | — | right after `make_treefx`: `verify_race --scenery-only --trees build/<slug>/extension/trees/trees.txt` judges the WRITTEN file (kn5 frame x, y, -z flipped back) → `data/race_verify.scenery.json` (synced back) |
| `ship_sd.sh` install guard (new) | — | the REAL install refuses (exit 1) while `acs.exe` / `acs_x86.exe` / `Content Manager*.exe` runs (`tasklist`): the park is a `mv`, which fails half-way on a held folder. Scratch runs never reach it |

**Why.** The critic of the 0049 build: race audit K 158 vs the installed 154 = 4 verts of the new
`1KERB_race_1514_in` at v1518, and `1KERB_race_2319_in` sitting up to 0.44 m UNDER the folded ribbon at the
Navajo/Jackson apex (a red/white kerb vanishing under the asphalt) — no gate failed either. And no gate checked
scenery against the race lanes: two scatter palms (v763 on the hairpin kerb, v4495 at the seam) were kept out
of `trees.txt` only because `make_treefx`'s centreline guard happened to catch them.

**Measured** (scratchpad `corr2/m/kerb_sheets2.py`: every 1ROAD sheet under each kerb station's footprint on the
previous rehearsal's built road kn5): `1KERB_race_1514_in` 18 of 34 stations single-sheet (about 1.5 m each side
of the fold), 13 under the upper sheet (≤ 0.05 m) — DROPPED; `1KERB_race_2319_in` 8 of 51 stations under the upper
sheet by up to 0.42 m, single-sheet pieces 4.5 m on entry and about 5 m on exit, neither at the apex — DROPPED;
`1KERB_race_770_in` (installed since 0047) 13 of 139 stations under the hairpin fold's upper sheet (v764 ≤ 0.04 m,
v774 ≤ 0.14 m) — PULLED BACK to v751-763 (111 stations, all one sheet); `3297_in` has two sheets 0.026-0.028 m
apart at v3298-3299 with its top 0.012 m clear of the upper one — kept, under-road 0. The ribbon folds stay a
named ribbon defect (0033/0046 class) for the ribbon's owner.

**The rehearsal** (fresh copy of the workshop minus `build/`, `SHIP_PROJ=<copy> bash tools/ship_sd.sh --skip-blend`,
14:41:36-14:46:56): every kerb `under_road` 0 (8 kerbs); verify_race OK incl. G scenery (15,261 TreeFX entries +
18 sign posts, 394 beside the race road, 0 in a lane or a wall, nearest 0.655 m — a median bush vs the
closure); the written-trees re-check OK (nearest 0.656 m); race audit K **154** both layouts (D 0 / I 145 / F 15,
W 0); no_route BUILT PASS both; street gates identical to the installed build (`audit.json` md5 `296a2bc1…`).

**Teeth.** `kerb_sheets2.py` on the previous build reproduces the author's reports; `scenery_margins` on the RAW
(unguarded) scatter palms FAILS exactly the two the critic found (v763 lane −0.52 m, v4495 lane −2.18 m, both
layouts). Tests: `tests/tools/test_barrier_bands.py` (the 8 declared + 2 dropped + 770 pull-back; every trim
refusal; neither/both declared-and-dropped), `test_verify_race.py` (E under-road and dropped-but-authored; G
scenery: lane, curb strip, closure, open box, the far tree uncounted; trees.txt frame; the `--scenery-only` CLI),
`test_race_furniture.py` (a dropped kerb leaves its corner), `test_make_treefx_plan.py` (`plan()` is what
`build()` writes), `test_ship_sd_chain.py` (the re-check after `make_treefx`, hard; the install guard).

## 2026-10-11 — side-street mouths: the weld, `verify_mouths`, `verify_race` O hard, the race step check on the whole lane

**Why.** The read-only mouth diagnosis (2026-10-11) on the installed build: `del_cerro_blvd#0` (the W leg, College
v1085, 76.9°, College grade 4.56 %) ended as a LEVEL ribbon square to Del Cerro, so its south corner stood up to
+0.51 m over College 3.4 m inside College's pavement (2.33 m past the race_acw lane face) and its north corner left a
grass notch 0.3-0.6 m below; its sidewalk ran 2.78 m further in at +0.67..+0.75; the prep then pinned a grass
triangle up through College by +0.07..+0.37. Mechanisms: `trim_connectors` took the cut height from the host's
NEAREST vertex; its 30 m blend pulled only the centreline, and never ran when the cut was a piece's START
(`del_cerro_blvd#1` dropped 0.58 m in 2.1 m, `medium#2+0#0#0` 0.33 m in 3.3 m); the assembler sweeps connectors with no
cross-fall; `seat_terrain`'s clamp made a cut end a 14.6 m disc of "connector"; `gap_mouths` sized the sidewalk gap as
if square. None of it failed a gate: the race author listed "another deck above the strip" (0.539 m at v1081) as a
WARNING. The same list carried 0.458 m at Navajo v2314 — not a mouth: the mainline ribbon folding on the inside of the
Navajo / Jackson corner (half-width 12 m round a 7.4 m centreline radius), one of five such folds on the lap.

**Change — gates.**

| Gate / rail | Before | After |
|---|---|---|
| `tools/verify_mouths.py` (NEW; in `ship_sd.sh` hard, right after the street gate OBJ; its stale `data/verify_mouths.json` removed first) | — | every `data/mouths.json` record judged on the BUILT road (`data/track.obj`), heights from its triangles only; HD = the host's lowest 1ROAD sheet ON its centreline, level across. MOUTH LINE: every 1ROAD sheet on the host edge − 0.2 m across the connector's span (where its two edges cross that line, corners 0.75 m in) within **0.05 m** of HD. HOST LANE: over the span ± 3 m, centre to half-width − **0.45 m** on the mouth side (the island excluded), no 1ROAD / 1KERB top > HD + **0.02 m**, no 1GRASS ≥ HD − 0.005 m. NOTCH: at half-width + 0.15 m across the span the top sheet is 1ROAD within 0.05 m of HD. APPROACH: along the connector's centreline and both wheel lines (half-width − 1 m), −3..30 m, the grade over a 2.5 m wheelbase changes ≤ **3 %/m** (the 1 m figure reported beside it), and no 1GRASS within 0.005 m of the road from 0.5 m out (samples of a wheel line folding round a tight corner — plan step off ±40 % — not measured). SIDE: mouths.json's side = the side the piece approaches from. Exit 1 on any FAIL, 2 on an input error |
| `verify_race` O (+ `author_race_furniture_blend.OTHER_DECK_M`) | reported only, at 0.15 m | **HARD**: any strip / kerb ring with another ROAD sheet > **0.05 m** over its base fails; the author records `other_deck_threshold_m`, and an authored file measured looser (or that does not say) fails |
| `drive_test` race-corridor step check | ten wheel paths clamped to ±6 m about the lane middle; the lane-edge paths excluded from steps / kinks; a step at `w ≥ 9.5 and |off| > 3.5` (off the CENTRELINE) reported as an exempt "apron" step — most of a race lane | the WHOLE declared lane, face to face: no 6 m cap, the edge paths gate, no apron exemption inside a declared race lane. Street layout and single-layout tracks unchanged |
| `tools/ship_sd.sh` | `AIROSO` hard-coded | `AIROSO="${AIROSO:-<main checkout>}"` (rehearse a worktree's tools); the weld step; verify_mouths; `mouth_welds.json` + `verify_mouths.json` synced back; the street audit floor re-stated (below) |

⚠ Invented: verify_mouths' 0.05 / 0.02 / 0.45 m are the diagnosis's own numbers; mine are the 0.005 m "grass at the
deck" (the prep pins grass 0.02 m under a deck at its vertices; between them it rose to 0.009 m under College's edge on
the welded mouths), the 0.15 m notch reach, the 0.75 m corner inset, the 2.5 m wheelbase (a 1 m difference on a 3 m-row
triangulated deck reads every row crease as a kink) and the 3 %/m approach limit. O's 0.05 m is the task's.

**Change — geometry** (no gate reads these differently; they are why the gates move). `trim_connectors`: the cut height
interpolated along the host segment; the blend walks FROM the cut whichever end it is; an earlier pass's cut is frozen;
the side is the approach's (`medium#2+0#0` at `del_cerro_blvd#1` v82 was recorded +1 while arriving from −1, so
gap_mouths gapped the far sidewalk and the near one stood across the mouth); mouths.json gains host_seg / host_t /
angle_deg / host_grade / piece / end. `weld_mouths_blend` + `mouth_weld` (NEW, after the trimmed rebuild, before the
seat): refuses unless every connector block equals the assembler's own sweep vertex for vertex; mends every ribbon line
that runs backwards (a swallowtail cut at its self-intersection, the apex at the higher leg's height; a hook replaced by
the cheapest forward chord); mitres each connector end onto the host edge − 0.4 m (road) / the edge (curb); warps road
+ curb + paint by (host deck − level end) × smoothstep(1 − s / 30 m); turns twisted quads to their ridge diagonal;
self-checks before saving. `seat_terrain`: the deck read off the welded ROAD; a cut end no longer seats its host's
pavement; terrain densified to 1.5 m under the welded approaches (0.75 m under a connector corner tighter than 3 ×
its half-width), 0.6 m along the host edge at each mouth, and cleared from under the inside half of each mended
mainline fold (its fan is no plane a 4.5 m grass facet can lie under; densifying it instead put the prep's western
1GRASS tile at 80,362 positions and the prep refused). `gap_mouths`: half-width / sin(angle) + 3 m by arc from the cut's
station, plus the first station past each end.

**Measured — the full scratch rehearsal** (a fresh copy of the workshop minus `build/`, `AIROSO=<worktree>
SHIP_PROJ=<copy> bash tools/ship_sd.sh --no-install`, no `--skip-blend`: median → build → route → divide → trim →
rebuild → WELD → seat → … → gates; 20:27-20:35 on the last run; the workshop `loop.blend` md5 `fbf091e3…` before and
after; nothing installed). Baseline = the installed build of 18:26 (same config, same inputs).

| Gate | installed | this build |
|---|---|---|
| verify_mouths `del_cerro_blvd#0` (W) | FAIL: mouth line 0.534 m, host lane +0.752 m road/curb + 124 grass samples at/above (+0.371), notch 94 / 95 (0.539), approach 19.4 %/m, 11 grass on the approach | PASS: 0.015 / 0.0 (grass −0.006) / notch 0.020 / 1.13 %/m |
| verify_mouths `del_cerro_blvd#1` (E) | FAIL: 0.680, notch 72 / 78 (0.739), approach 33.2 %/m, 25 grass | PASS: 0.016 / 0.0 (−0.009) / 0.016 / 0.98 %/m |
| verify_mouths `medium#2+0#0#0` start (Lake Murray Blvd v4424) | FAIL: host lane +0.124, notch 1 / 34 | PASS: 0.003 / 0.0 / 0.005 / 1.82 %/m |
| verify_mouths `medium#2+0#0#0` end (`del_cerro_blvd#1` v82) | FAIL: SIDE (+1 recorded, −1 real), host lane +0.147, notch 40 / 42 (the host's sidewalk +0.14 across the mouth) | PASS: 0.004 / 0.0 / 0.010 / 0.97 %/m |
| verify_race O (other deck over the strip) | 4 rings, max 0.539 m (v1081-1083 W mouth, v2314 Navajo fold) — then a warning | **0 rings** at 0.05 m; verify_race OK, both layouts |
| race author seating | 17,498 hit / 1 interpolated (the seam) | 17,499 hit / 0 interpolated; deck vs data max 0.463 m (was 0.194: strip rings on the mended fold fans) |
| no_route BUILT race_cw / race_acw | PASS / PASS | **PASS / PASS** (0 leaks, 0 / 406 probes, lap complete, spawns reached) |
| RACE_RED | none | **none** |
| street drive_test soft top / severe / kinks/km / excursions / floating / daylight | 82 / 0 / 4.97 / 101 / 391 / 0 | **42** / 0 / 3.86 / 100 / 391 / 0 (apron steps 22 → 7) |
| street audit D / K / I / F | 512 / 154 / 145 / 15 (826 total) | **512 / 20 / 20 / 13** (565) |
| race_cw drive_test soft top / severe / bumps/km / kinks/km | 44 / 0 / 0.37 / 1.48 | 23 / 31 / 7.42 / 6.45 |
| race_acw drive_test soft top / severe / bumps/km / kinks/km | 40 / 0 / 0.30 / 1.34 | 22 / 28 / 10.24 / 7.57 |
| race audits D / K / I / F, W | 0 / 154 / 145 / 15, 0 | 0 / 20 / 20 / 13, 0 (both layouts) |

**The street audit floor, re-stated** (`ship_sd.sh`'s audit step now says D 512 / K 20 / I 20 / F 13): every K and I
sample was located (scratchpad `classify_ki.py` on both builds). Installed K 154 = 81 at the five mainline folds
(hairpin v763-773 31, Navajo / Jackson 23, v3292-3297 17, the seam 5, College / Navajo 5: the inside sidewalk folded
back over the road), 20 at the mouths (12 at the medium end — the host sidewalk left standing across it —, 6 at the W
mouth, 2 at v4424) and 53 where the connectors' own ribbons fold (the Del Cerro hilltop loop rows 65-85 and 145, the
medium route rows 200-207, `del_cerro_blvd#1` row 240). This build: 0 at the mainline folds, 2 per mouth (the curb
return at each corner, 8) and 12 on the hilltop loop (its outer curb line at rows 72-74 overlaps itself across a
hairpin narrower than the ribbon: the weld reports it "left as built") + `del_cerro_blvd#1` row 240. I 145 → 20 the
same way (81 → 0 at the folds, 19 → 8 at the mouths, 45 → 12 on the connectors). F 15 → 13: two fewer not-flush curb
verts (counted, not located). D 512 untouched (the road kn5's own guard rails, as before).

**Named, not exempted.** The race drive_test moves for two reasons, separated by running each code on each build:
(a) the step check now covers the whole declared lane — the NEW check on the INSTALLED race_acw OBJ finds 94 severe
steps (the W mouth's floating corner at s 10249-10250 up to 0.60 m, the seam, the Navajo fold up to 0.70 m, the hairpin
33, …) where the old one found 0; (b) the geometry — the OLD check on THIS build's race_acw OBJ finds soft top 11
(was 40), severe 2. What the new check still finds on this build (31 / 28) stands on the inside of three mended mainline
folds: the Navajo / Jackson fan (v2310-2329: up to 0.40 m where the low leg's slivers rise to the apex — the legs meet
there 0.5 m apart, which the fold used to hide as a 0.46 m sheet edge), the hairpin fan (v760s) and the seam (v0 /
v4490s); race_acw's 22 soft tops are all on the hairpin (11) and College / Navajo (11) fans. A re-grade of the fan's inside line over
8 rows each side was tried and REJECTED: soft top fell to 6 / 11 but severe rose to 46 / 44, and it lifted the strip
rings 0.69 m off the centreline height no_route bands walls against — 3 doors, 316,424 m² leaked. The fold fans are the
next owner's (ledger 0033 / 0046 class); race severe/km 2.3 / 2.1 stays under drive_test's 12/km.

**Found by the independent verify, not in the rows above.** (1) Street drive_test worst slope kink 11.3 % → **23.7 %**
at s 6946 (v2315, the Navajo fold mend: the overlapping sheet became a crease; new kinks also at the seam, s 11-13) and
bumps/km 0 → 0.15; kinks/km overall still fell 4.97 → 3.86. (2) The OLD race step check on this build's race_acw OBJ
finds 2 new 0.10 m severe steps at s 6535-6536, offset 2.6 m (the Navajo fold) where the installed build had 0 — a
small regression inside the swath that was checked before, against the installed build's hidden 0.70 m fold edge
there. (3) `medium#2+0#0#0` start: a triangle crease on the inside of the connector's own 64° corner, 25-29 m from the
Lake Murray Blvd mouth (slope 5 → 16 %, installed 3 → 11.6 %); verify_mouths leaves a wheel line folding round a tight
corner unmeasured (21 samples on each ±4 m line), so APPROACH does not see the inside of tight corners. (4) HOST LANE
stops 0.45 m inside the host edge and the weld puts the connector's end row at edge − 0.4 m: a raised end row is caught
by MOUTH LINE / NOTCH / APPROACH (all three fired on the verifier's planted defect), not by HOST LANE. **Shipped anyway
(2026-10-11, v0.17.1):** every one is smaller than what it replaced, all are under drive_test's thresholds, and the
drive is the judge; the Navajo fold fan is the next owner's.

**Teeth.** verify_mouths on the installed build: all four mouths FAIL, each where the diagnosis put it.
`tests/tools/test_verify_mouths.py` (a synthetic built road: the assembler's square level end fails mouth line / host
lane / notch, the welded one passes; a wrong side, an approach step, grass in the lane, grass on the approach, the host
sidewalk left across the mouth each fail), `test_mouth_weld.py` (the defect reproduced then mended: every line on the
host edge at the deck, nothing over the host, no fold, the approach under 3 %/m, rows past 30 m untouched; the swallowtail
cut at the legs' crossing, the hook's chord, a U-turn refused; the gap window's skew and its end stations),
`test_trim_connectors.py` (interpolated cut height, the START blend, the frozen cut, the approach side — each fails on
the previous trim), `test_verify_race.py` (O: a 0.458 m and a 0.06 m ring fail, a 0.15 m author threshold fails),
`test_ship_sd_chain.py` (the weld between the rebuild and the seat with the workshop on sys.path; verify_mouths after
the street gate OBJ, hard; the AIROSO default). engine-july is not edited: no file `ship_sd.sh` runs from ENG changed.

## 2026-10-11 — Lookout Lariat P0: `route_oneway_check`, the OSM staleness guard (ledger 0048)

Both landed in 324ec41 / 0e96423 without an entry here; recorded now.

**`tools/route_oneway_check.py` (NEW; not yet wired into a ship chain — the Lariat's P1 chain will run it
before any geometry).** The July route list drove the Lariat's lap ~100 m the wrong way up a one-way at the
US-6 ramp end and 84 m at I-70 exit 259, and no gate could see it: every gate measures the built road, none
asks which way the real road runs. This asks it of the route itself. Per **street** layout (race layouts are
closed roads, not checked), each centreline segment is matched to the OSM way it runs along in the route
stage's own Overpass snapshot (`data/osm.cache.json`); runs against a `oneway=yes|-1` or roundabout way must
lie on a stretch the layout declares (`layouts[].against_oneway` → `divided.stretches[].ways`), every
declared stretch must actually be driven against (a stale declaration FAILs), and a layout that declares
nothing must drive against nothing. Exit 1 on any FAIL, 2 on a usage/config error; `data/oneway_check.json`.

| Item | Value | Flag |
|---|---|---|
| verdict | the real road's direction, from its OSM `oneway` / `junction` tags; `reversible` / `alternating` listed, never judged | [std] |
| `SNAP_M` | 3.0 m — both segment ends within this of the way | ⚠ invented (a matching parameter, not a threshold) |
| `MIN_COS` | 0.7 — \|cos\| between the segment and the way's local direction (~45°) | ⚠ invented (matching parameter) |
| unmatched segments | a segment straddling a junction corner matches no single way: reported as a junction gap, never as a run | |

Proven on the P0 line: Full 0 m against; Reverse 4,486.5 m against on the four declared divided stretches
(D2 (a), Kevin's call), 0 undeclared.

**OSM staleness guard (`scripts/gps/widths_from_osm.py` `OSM_MAX_AGE_DAYS`; also `overpass.py`,
`centerline.py`).** 2026-10-11: overpass.kumi.systems served OSM as of 2026-07-28 while overpass-api.de was
minutes old, and the width/route stages fell back to it without a word. A live Overpass answer whose
`osm3s.timestamp_osm_base` is older than the limit (or carries none) is never written to a snapshot: the stage
stops, naming the mirror and its data date. Per track `route.osm_max_age_days`; one-off `--allow-stale-osm`.
A snapshot already on disk is never judged by age (pinning old data on purpose is what a snapshot is for).

| Item | Value | Flag |
|---|---|---|
| `OSM_MAX_AGE_DAYS` | 7.0 days — healthy mirrors lag minutes to hours; a week behind means the copying stopped | ⚠ invented |
| without a cache path | warns only | |

## 2026-10-11 — paint gate: `tools/verify_centreline_paint.py` replaces the fitter's 1.5 m-from-OSM ceiling (ledger 0048, Lariat P2)

The aerial pass (NAIP 2019, airoso e82ff8c) traced the Lariat's painted centre line. It found the OSM line, which the fitter's position check measured against, 7.6 m off the paint at C4 and 4.8 m at C10. OSM cuts those hairpins. So the ceiling passed fits that missed the real road and failed C9, where OSM was within 0.60 m of the paint. Position is now judged against the paint.

| Gate | Before | After | Flag |
|---|---|---|---|
| `tools/fit_hairpins.py` `max_move_m` | a fitted corner FAILS beyond 1.5 m from the OSM line, both ways; the radius scan picks the nearest radius inside it | **removed**. Status = the step gate only. `lateral_move_m` is reported with `judged_by: tools/verify_centreline_paint.py`. The radius scan picks the nearest radius that passes the step gate. `hairpin_fit.gate.max_move_m` is deleted from the Lariat config | the 1.5 m was ⚠ invented. Measured against the paint, it passed C4 at 7.25 m and C10 at 4.35 m, and failed C9 (2.06 m from OSM, OSM 0.60 m from the paint) |
| `verify_centreline_paint` (a) paint (new) | — | every high/medium yellow point of `data/aerial/paint_traces.json` within **0.75 m**, measured to the nearest segment running the same way (\|angle\| < 60°) | ⚠ invented. Context: OSM scatters 0.74 m rms / 1.35 m p90 about the paint on straight road (862 points). The judged point set depends on the confidence rules in `tools/aerial/traces.py`, all ⚠ invented: a run of >= 4 profiles, within 0.3 m over ±4 m, prominence >= 0.5 × the window's median, drift <= 0.15 m/m; unusable width stations count as low |
| (b) curvature on the climb (new) | the fitter's two rules, on fitted spans only | over `hairpin_fit.climb_st_m` (stations on the OSM source line, via `osm_station_m`): step <= spacing × \|k_local\| × 57.3 + **1°**, where k_local is the line's turn over **±5 m** divided by that window's length; neighbouring steps differ by <= **1.5°**; climb spacing **0.95-1.05 m** | all ⚠ invented. The spacing band exists because the neighbour rule depends on spacing (at 3 m it fails real spirals, denser makes it trivial) |
| (c) topology (new) | — | no vertex turning >= **120°**, no segment < **1 mm**, no crossing of non-adjacent segments | ⚠ invented. The OSM line's largest single step is 78.5°, a junction node |
| (d) closure (new) | — | `coords[0] == coords[-1]` exactly, and the seam vertex passes (b) across the wrap, v[-2] -> v0 -> v1 (L13) | [std: L13] |

Proof:
- `tests/tools/test_verify_centreline_paint.py` (5): 0.3 m passes and 1.0 m fails; a lost leg is not rescued by the stacked opposite leg; facets, curvature jumps and 3 m spacing fail while a 1 m clothoid passes; a figure that crosses itself and a fold both fail; an open seam and a seam kink fail while a smooth lap passes.
- `tests/tools/test_fit_hairpins.py`: a kink with a radius now PASSes and is spliced, its >1.5 m move reported.
- On the Lariat, the OSM line fails: (a) 1,320 points over 0.75 m, worst 7.56 m; (b) 444 step + 971 neighbour + 2,367 spacing fails; (d) the seam neighbour rule, at 1.84°.
- The paint centreline (`tools/paint_centreline.py`) passes all four: worst 0.61 m; 0 / 0 / 0 on 7,114 climb points; seam 2.20° against a limit of 3.16°.

Wiring: not in build.sh or any ship chain yet. It runs by hand after `tools/paint_centreline.py` (Lariat build order: gps -> paint_centreline -> remap_centreline_config --write -> elev). Exit 1 on any fail. Output goes to `data/aerial/paint_gate.json`.

## 2026-10-11 — Lariat P1: a ship chain that isn't San Diego, and the loop prep's three preconditions (ledger 0048)

### The ship chain (`tools/ship_track.sh <track>`, driven by `tracks/<track>/ship.json`)

Wiring only; no threshold moves. `tools/ship_sd.sh` is untouched (byte-identical) and stays San Diego's chain
of record. `ship_track.sh` carries every gate `ship_sd.sh` runs, with the same exit semantics (set -e on the hard
ones; drive_test / audit exits collected; `--force-install` never covers a race layout red on its own gates or a
no_route input error). New in the chain:

| Gate | Where | Exit |
|---|---|---|
| ship.json vocabulary | a step name with no `<phase>_<name>` function in the script, or a value outside `tools/ship_track_spec.py`'s patterns (unknown key, `..`, absolute or shell-shaped path, unknown phase, `prep` other than exactly `[prep, split]`) | 2, before any file operation |
| race furniture declared but not authored | a layout declares `race_furniture` and `steps.author` has no `race_author` | 2 |
| `no blend yet` | no `loop.blend` in the project and nothing in the run can build one (`--skip-blend`, or no available blend builder) | 0 on `--dry-run`, 1 otherwise; nothing synced in |
| Lariat draft: `verify_centreline_paint` + `route_oneway_check` | after `gps -> paint_centreline -> remap_config --write`, before `elev` (the paint gate's "wiring: not in any ship chain yet" above is now wired, for the Lariat) | 1 on FAIL |

Proof: `tests/tools/test_ship_track_chain.py` (19). San Diego parity at airoso 8a2f076: the step headers
`tracks/san-diego-lake-murray/ship.json` selects equal `ship_sd.sh`'s, every branch, in order (static), and a real
`--skip-blend --dry-run` of both scripts on the same scratch copy of the workshop printed identical step headers
(7) and wrote an md5-identical `split_manifest.json` (`37e960f0…` on that scratch path; the manifest embeds absolute paths, so the hash is per-path — the independent verify got `d8c5c490…` for BOTH scripts on another path). The Lariat's route draft
rehearsed with `--draft-only` on a scratch project reproduces `data/centerline.geojson`, `data/centerline.osm.geojson`
and `track.config.json` byte for byte, paint gate and one-way check PASS.

### The loop prep (`scripts/ac/build_kn5_loop.py`, airoso's copy only; engine-july's and the snapshot untouched)

| Gate / guard | Before | After | Flag |
|---|---|---|---|
| 0020 corridor discipline (`_corridor_hash`: kerb faces carved out of carriageways, trunks and canopies cleared from the driving envelope) | built from `data/finished_centerline.json` (KN5 frame, north negated) and queried in Blender's frame: the mainline corridor stood at the north-south mirror image of the road; connectors (local frame) were right | the mainline is un-negated before hashing; mainline, connectors and queries share Blender's (east, north) | a frame bug, no number. `tests/ac/test_build_kn5_loop_prep.py` fails on the old function: a point on the road read 1e9 m from any carriageway, its mirror image read inside one |
| over-cap tiling (`_split_large`) | > 60,000 positions -> K = n // 60,000 + 1 equal-width bands along the longer axis; a band holding a switchback knot overflowed (the FATAL `assert_under_cap` then stopped the build) | > `PIECE_CAP` **50,000** positions -> `balanced_tiles`: halve at the median face centre along the longer side until every piece is <= 50,000 positions | ⚠ 50,000 is invented (the plan's number; 15,535 of headroom under AC's hard 65,535 for the weld and smooth-shading after the split). Proven: a strip + dense knot whose equal bands overflow a 2,000 cap tiles under it by halving |
| terrain seat on stacked legs (L4) | the deck under a ground vertex = the highest road within `LAYER_WIN` 30 m vertically; the contact-band target = the nearest road point in 3D (any leg); the band weight from the nearest road vertex in plan (any leg) | **station matching**: every ground vertex carries the leg + station of the nearest centreline / connector segment in plan (`LegIndex`); it seats only on road triangles of that leg within `STATION_WIN_M` **40 m** of its station (cyclic on a closed lap); the band weight is the plan distance to that leg's footprint. `LAYER_WIN` is gone | ⚠ 40 m is invented. Bounds: a same-leg seat can be off by at most 0.115 × 40 = 4.6 m of grade (the lap's steepest 20 m, -11.5 %), under the smallest stacked gap (6.5 m); on the Lariat's paint centreline every pair of distinct stretches within 30 m in plan is >= **79.9 m** apart in station (closest in plan 19.4 m, station gap 113.9 m at st 5,472 / 5,586). Blender proof on a synthetic switchback (legs 20.5 m apart, 6.5 m road, leg B on a fill): ground vertices 0.3-9 m outside a leg's edge more than 0.5 m off a seat on their own leg: HEAD prep **459 of 3,509, worst 21.11 m**; this prep **28 of 3,509, worst 0.63 m** (the residue is the footprint-distance approximation of the check itself) |

Not changed (no stacked-leg exposure on a road whose legs never overlap in plan): the anti-poke clamp (lowest
drivable sheet within ±20 m, push-down only), the corridor query's 3.5 m / 7 m deck windows (bridges), the props'
terrain-delta ride (±40 m).

Which kn5s these change: only kn5s prepped by airoso's `scripts/ac/build_kn5_loop.py` (`scripts/build_loop.sh`,
and `tools/ship_track.sh` for every track but San Diego). Today that is **none that ships**: San Diego preps with
engine-july's copy (`ship_sd.sh`, and `ship_track.sh` keeps that for SD), the Colorado circuits, rally stages and
Sand Creek build through `scripts/build.sh` -> `scripts/ac/build_kn5.py` (the OBJ program, its own
`_split_over_cap`, untouched), and the only `loop.blend` in the fleet is San Diego's. The first kn5 this prep
writes will be the Lariat's.

**Post-merge fix (independent verify finding).** `LegIndex.neighbour_keys` on a closed lap returned (k−1, k, k+1);
the last chunk is short whenever the lap is not a multiple of `STATION_WIN_M`, so near the seam a point's 40 m window
reached a chunk that set missed (1,010 m lap: station 5 is same-leg with 985, chunk 24, outside (25, 0, 1)). It now
collects every chunk the station interval [start − 40, end + 40] touches round the lap.
`tests/ac/test_build_kn5_loop_prep.py::test_seam_chunks_hold_every_same_leg_station_when_the_last_chunk_is_short`
walks every station pair within the window on such a lap; it fails on the merged code, passes on the fix. No
threshold changed.

## 2026-10-11 — tiered terrain: the far ring's `verify_kn5` check, balanced terrain tiles, the far decimation retired, L3's clamp made distance-weighted (ledger 0046)

Kevin, 2026-10-10: *"more terrain near the roads, and the I-8 trench and adjacent causeway cut out"*, *"I want to see
cowles mountain"*. The ground is now one multi-resolution lattice sampled from USGS 3DEP **at every vertex**
(`scripts/elevation/terrain_sample.py` + `scripts/geometry/terrain_tiers.py`, opt-in per track by a `terrain.tiers`
list; every track without it is byte-identical). Lake Murray is the only consumer. Rehearsed in full on a scratch
copy of the workshop (2026-10-12, `ship_sd.sh --no-install`, ENG = a scratch copy of engine-july): **every gate
verdict file identical to v0.17.1 field for field** (drive_test street / race_cw / race_acw, audit street / race_cw /
race_acw but `grass_verts`, no_route planned + built, verify_mouths, verify_race, verify_race scenery); race and
closure kn5 vertex positions identical.

### Gates and wiring

| Item | Before | After | Flag |
|---|---|---|---|
| `verify_kn5` far ring (new, hard) | — | every mesh named `GRASS_FAR*` must carry **no digit prefix** (a `1GRASS_FAR` would be collided with, gated and GrassFX-listed) and stay ≤ 65,535 positions; prints the terrain tile count. A track without a far ring prints nothing and is judged as before | [std] the cap is AC's; the prefix rule is L6 |
| engine-july `build_kn5_loop._split_large` (pending mirror) | `1GRASS` cut into `n // 60000 + 1` equal-width bands | `1GRASS*` / `GRASS_FAR*` tiled by recursive **median bisection** (palm.chunk_mesh's rule); every other mesh keeps the bands. 1GRASS 236,771 v → 4 tiles (max 59,692), GRASS_FAR 106,557 v → 2 (max 53,414) | wiring |
| engine-july `build_kn5_loop` T-junction weld (new, pending mirror) | — | after the conform, a terrain face whose boundary edge carries another vertex (within 1 mm, in its line) is re-fanned through it from its centroid: in-plane, no vertex moves. 1,906 faces | wiring |
| `GRASS_FAR` face-up | — | joins the face-up pass of `1GRASS` | wiring |
| `tools/slim_far_terrain_blend.py` | `FAR_M 220`, `RATIO 0.35`: every TERRAIN vertex > 220 m from a road collapsed to 35 % so one uniform sheet fit two sub-65k tiles | **deleted** with its `ship_sd.sh` step. It existed to pay for the equal-width bands (the cap decided how much world there was) and it ate the deepest I-8 cut | ⚠ its 220 / 0.35 were invented; gone |
| `tools/triangulate_terrain_blend.py` (new step after the seat) | the decimation also triangulated every TERRAIN face (BEAUTY) | the same BEAUTY triangulation, alone; no vertex moves (exit 1 if the count changes). The near-road ground the gates were tuned on is that triangulation's; without it the first rehearsal read +21 soft-top stations | wiring |
| `make_treefx` `SURFACE_MATERIALS` | hard-coded `1GRASS_0_mat, 1GRASS_1_mat, 1ROAD_road_mat` | read off the built road kn5's gate OBJ (every `1GRASS*` material + the road); exit 1 without the OBJ. `GRASS_FAR` is not physical and is not listed | wiring |
| road gate OBJ | written after the track folder | written **before** it (ext_config's GrassFX lists and make_treefx read the tile names off it) | wiring |
| `ext_config` GrassFX | `GRASS_MESHES = 1GRASS_0, 1GRASS_1` | `1GRASS_0..3` (the `startswith(("1GRASS","1LAWN"))` rule, unchanged); `GRASS_FAR` never listed; `OCCLUDING_MESHES` unchanged | [std] the v0.12.x TDR rule |

### The standard: L3 "Fake mountains" (Kevin's approval: D6(i) of the Lariat V3 plan, "Those changes are good")

The ±`terrain_band_m` clamp (22 m) now holds in full only within `terrain.clamp_corridor_m` of a pavement and
releases (smoothstep) to the raw DEM by `terrain.clamp_blend_m`; beyond, 3DEP stands uncapped. On the build:
5,153 lattice vertices clamped (max lift 25.2 m, max cut 18.4 m), all within 250 m of a road; Del Cerro hilltop 258.1 m
(was 163.7 / 168.4), Cowles 484.3 m (was absent; world max 220.0).

### Invented numbers (⚠ every one; measured, none calibrated against a reference track)

| Number | Value | Range the ledger gave / why |
|---|---|---|
| `clamp_corridor_m` | 80 m — **superseded 2026-10-13 by 20 m** (ledger 0054 D3, below: 80 filled a real canyon by 25 m and planed real ridges 12–18 m) | 60–100 (corridor 20 + blend 16 + one cell … ~100) |
| `clamp_blend_m` | 250 m — **superseded 2026-10-13 by 40 m** (ledger 0054 D3, below) | ~250 or the medium tier's edge |
| `tiers` | 5 m (x-split) within 60 m of a pavement, 20 m (x-split) to 500 m, 40 m beyond | the ledger's own example; 5 m is the only nesting cell under criterion 5's 7 m (20/3 m would put 10.2 % of the fine tier's facets past 7 m in 3D on its slopes) |
| `tier_options.keep_cells` | the graded 20 m grid's own cells within 18 m of a pavement | the seat moves ground ≤ 11.1 m past a pavement and subdivides ≤ 15.1 m; the prep pins ≤ 9 m and subdivides ≤ 16 m |
| `keep_surface_m` / `keep_feather_m` | 20 / 16 m — from the pavement **and** (2026-10-12) from the nearest kept node (the kept-node feather retired by the fix round below, where the kept cells themselves take the pavement feather past 20 m) | the conform corridor and blend. The kept-node feather removed 1,355 of the 1,404 ledges (> 100 % built slope, > 2× the data's) the pavement-only feather left at the kept cells' outer edge, with every gate identical |
| `physical_within_m` | 250 m | drive_test sweeps ≤ 20 m off the road, TreeFX fills ≤ 200 m |
| I-8 corridor | ±80 m at 5 m; floor every 10 m, 2 m sections every 25 m | the ledger asked 10 m cells; 10 m does not nest beside a kept 20 m cell (two levels) |
| `include.cowles_mountain` | 20 m cells over the summit box | the ledger's 20 m |
| `far_extent` | 32.755–32.822 N, 117.0895–116.998 W | the dossier's landmark box, widened so criterion 3's x ≤ −4000 / ≥ 4500 faces exist |
| sightline thresholds (`tools/sightline_check.py`) | crest 9.0°, v2240 8.1°, v1640 5.1° | the crest's is the ledger's; the others take the same 0.35–0.4° allowance. Measured, not gated |

### Verification criteria (ledger 0046 §Verification) — measured on the built gate OBJ against fresh 3DEP, NOT gated

Results are in the ledger. As first rehearsed two read FAIL as written, with the cause measured: criterion 5's 15–60 m p90
was 9.05 m (the kept near-road cells and the prep's slivers of them reach ~46 m out; fixed at that cause by the fix
round below: 5.27 m), and criterion
3's "no vertex below 100 m" is premised on a real low of ~121 m — fresh 3DEP puts the San Diego River side of the box
at 20–100 m (20,622 vertices; a 1,684-vertex sample against fresh 3DEP: p95 0.005 m, and the 16 off by > 1 m are
graded ground 13–42 m from a pavement or in the clamp's release band). Neither is loosened here:
they are reported against their own wording.

### `tools/ship_track.sh` re-synced to the new `ship_sd.sh` (after the merge of main a0557e0, 2026-10-12)

Wiring only, no threshold moves. The Lariat P1 section above recorded `ship_sd.sh` as byte-identical; ledger 0046
changed it, so `ship_track.sh`'s vocabulary and `tracks/san-diego-lake-murray/ship.json` follow (the SD header parity
in `tests/tools/test_ship_track_chain.py` passes before and after the dry stop): `draft_terrain_sample` /
`draft_terrain_resample` around the trim, `draft_triangulate_terrain` after the seat, `draft_slim_far_terrain`
deleted; the assembler and the weld through `V021_SHIM` from `tracks/<track>/scripts-v021` (the workshop-on-sys.path
and its shadowing guard are gone, as in `ship_sd.sh`; a draft naming the assembler without one exits 2); the road
gate OBJ is `ship_road_obj`, before the track folder, for San Diego and the Lariat alike (`gate_road_obj` removed);
San Diego's engine honours `ENG=<dir>` as `ship_sd.sh` does (no other track can name an engine); the 3DEP cache and
the I-8 corridor files cross in and out. `ship_sd.sh` stays San Diego's chain of record, not a shim.


### Fix round (2026-10-12, after the truth + visual verify): the kept cells refined past 20 m, a prep fin check, the far ring's chaparral, the summit cone

Two independent verifiers refuted the rehearsed build on criterion 5 (15–60 m facet p90 9.02 m), criterion 4 (19 of
171 I-8 sections) and the I-8's look from the seat, and found the far ring wearing a grey gravel tile. The cause of the
first three was one thing: the kept v0.17.1 20 m cells reach ~46 m out, and past the prep's reach they stayed 20 m
graded facets (the legacy 1 m trench and clamp included). Rehearsed in full again (ship9, `ship_sd.sh --no-install`,
ENG = the scratch engine-july): **every gate verdict file identical to v0.17.1 field for field** (`grass_verts` and
no_route timing aside), race and closure kn5 unchanged in size.

| Item | Before | After | Flag |
|---|---|---|---|
| engine-july `build_kn5_loop._refine_kept_terrain` (new, pending mirror; opt-in by `data/terrain.refine.json.gz`, absent on every other track) | the kept cells stayed the graded grid's 20 m triangles out to ~46 m | after the conform and the T-junction weld, before the re-seat: (1) coincident vertices merged at 1 mm; (2) every edge > `edge_m` of a kept-cell face reaching past `move_beyond_m` (or centred past `min_face_d_m`) halved until none is — coplanar, nothing moves; one cut = `tri_1edge`, three = `tri_3edge`, the two-cut pentagon ear-clipped (never a zero-area cap); near-vertical faces (\|n_z\| < 0.05, the graded surface's own steps) never halved; (3) merge + weld again; (4) every kept-cell vertex past `move_beyond_m` — by the data's pavement distance or the BUILT road's, whichever is nearer — takes the 3DEP sub-lattice under the L3 clamp, feathered toward its graded height exactly as the lattice beside it (`keep_surface_m` / `keep_feather_m`). On the build: 97,637 edges halved, 63,193 vertices moved (max 8.23 m), 0 fins | wiring |
| the same, fin check (new, **FATAL**) | — | a plan-flat face with a moved vertex that is not flat in 3D (a vertical fin over a crack) refuses the export. 0 on the build. The first cut of this pass (bmesh's generic triangulation of the two-cut pentagon, and halving vertical faces) stood ~7,300 such fins up; the gate OBJ now has 199 face-down 1GRASS triangles (v0.17.1: 209, zero-area or near it) and the same 7 non-manifold edges as v0.17.1 | [std] 0 is not invented: a fin is a crack |
| `terrain_tiers` `keep_cells.refine` (new, opt-in) + `terrain_sample` | — | plans the 5 m x-split sub-lattice of every kept 20 m sub-cell not wholly within `beyond_m` of a pavement (34,036 sub-cells, 76,926 nodes; 66,878 new 3DEP samples, 149 requests, cached in `terrain.samples.json.gz`); the topology the assembler meshes is unchanged vertex for vertex | wiring |
| the assembler's kept-node feather (2026-10-12, ship6) | non-kept vertices feathered from the nearest kept node too | **retired** when `refine` is on: the kept cells now follow the same pavement feather past 20 m, so the field is one surface across the kept edge (its 1,355 ledges cannot recur — the kept edge is no longer the graded surface) | wiring |
| `tools/sightline_check.py` | target = the nominal (1380, 2700), "the highest within 40 m" | target = the summit's TOP (the highest built vertex within 60 m, criterion 1's radius); the summit as seen = the cone's highest angle; judged against every step outside the cone; the top's, the shoulder's and the nominal point's angles all printed. The nominal is a 20 m-lattice probe ~14 m off the real top; the ledger's own Evidence calls the profile's last 10 m "the summit's own shoulder" | measured, not gated |
| `track.config.json` `texture_overrides.GRASS_FAR` | pbr's stock `ground_dry_diffuse.jpg` (mean RGB 139/132/122, a grey gravel) | `tracks/san-diego-lake-murray/textures/chaparral_far_diffuse.jpg`, grey-olive sage scrub over tan soil (mean 93/93/66), derived reproducibly from the stock grass + ground_dry tiles (`make_chaparral_far.py`); synced by `ship_sd.sh` `TRACK_TEXTURES` and `ship.json` | look only |
| prep log grep (`ship_sd.sh`, `ship_track.sh`) | — | `kept-cell refinement` line shown | wiring |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `keep_cells.refine.cell_m` | 5 m | the near-road tier's own cell (x-split) |
| `refine.beyond_m` | 10 m | sub-cells wholly within it never move and need no data (the prep pins ≤ 9 m) |
| `refine.edge_m` | 5.5 m | halves a 20.07 m edge to 5.02 m and a 28.4 m diagonal to 3.55 m — the x-split sub-lattice; criterion 5's 7 m |
| `refine.move_beyond_m` | 20 m | criterion 7's band (ground within 20 m of a pavement \|Δy\| ≤ 0.05 m); equal to `keep_surface_m`, so the feather starts at weight 1 |
| `refine.min_face_d_m` | 12 m | past the excursion sweep (≤ 9 m past the edge): refining there is coplanar, so the number only bounds the vertex cost |

Measured (ledger 0046 Results, ship9 gate OBJ against fresh 3DEP, the truth lens's own code): criterion 5 15–60 m
p90 **5.27 m** (was 9.02), 60–500 m 20.2 m; criterion 4 162 of 171 (was 152): the 7 near-road failures are sections
whose rim or centre lies on a pavement or within 20 m of one (criterion 7 holds that ground to v0.17.1), the 2 away are
2–4 m-wide 3DEP features (a 4 m step within 2 m; a median berm) under 5 m cells; criterion 7 within 20 m: 3D distance to
the v0.17.1 surface 0.000 m max. The cost: physical `1GRASS` 236,771 → 335,070 vertices in 8 balanced tiles (max
42,411), road kn5 107.3 → 112.6 MB. Neither criterion is loosened here.


### Fix round 2 (2026-10-13, after the truth + visual lenses refuted the fix round): the finest tier anti-aliased, plain cells split along their grain, `tools/rib_check.py`; criteria 2 and 3 re-worded where fresh 3DEP fails them too

The visual lens found washboard ribbing — 6–10 parallel steps — in two places: ~150 m SE of the Lake Murray Blvd
overcrossing (gate x 143..253, z −1696..−1734, `1GRASS_4`) and on the cut slopes west of College (x −3275..−3317,
z −953..−1008, `GRASS_FAR_0`). **Real or artifact, measured** (fresh 3DEP on a 1 m local grid over both boxes, 32,322
points, TLS on, 2026-10-13; the USGS hillshade and NAIP over the same boxes): both features are real. Spot 1 is the
concrete-lined Alvarado Creek channel, ~7 m wide and 5–6 m deep with vertical walls, crossing the lattice at ~27°.
Spot 2 is two ~5 m-wide drainage benches on the I-8 cut slope, slanting across it. The ribs are an artifact of two
things together: (a) **sampling aliasing** — each 5 m vertex was one 3DEP point, so a feature narrower than two cells
lands in one node and misses the next; (b) **the fixed SW→NE diagonal** of every plain cell, which folds the surface
across the feature's grain in every cell it crosses. They are not tier T-junctions and not the kept-cell refinement: the ribbed nodes of both
spots are plain 5 m I-8 corridor cells (no x-split centre, no kept or refine node among them), and the staircase runs
along the feature, not along any tier edge. A simulation of the 5 m lattice over the 1 m grid reproduces the staircase
from point samples plus the fixed diagonal and removes it with a low-pass plus a data-chosen diagonal; the build
confirms it.

| Item | Before | After | Flag |
|---|---|---|---|
| `terrain_tiers` `tier_options.antialias` (new, opt-in) + `terrain_sample` | every vertex one 3DEP point | every vertex of a finest-level (5 m) leaf, and every refine node, takes the **tent-filtered** 3DEP of the 2.5 m base lattice around it (weights 1/4, 1/2, 1/4 per axis, `AA_TAPS`): exact on a plane, it moves a vertex only where the ground bends inside a cell (on the build: median 0.03 m, p99 0.50 m, max 2.34 m). The cache stays point samples (+384,009 taps in 854 requests, 2026-10-13T15:28Z, cached in `terrain.samples.json.gz` with provenance); the filter is applied on every run. In the far ring the move is held to `far_max_move_m` of the vertex's own point (criterion 6) | wiring |
| `terrain_tiers.data_diagonals` (new, opt-in by `tier_options.diagonals`) + the assembler | plain square cells split SW→NE | each plain square cell whose four corners are more than `beyond_m` from a pavement (and are not kept-cell nodes) splits along the diagonal whose corners differ least in height; no vertex moves, kept cells and x-split fans untouched. 44,328 cells flipped on the build | wiring |
| `tools/rib_check.py` (new, **hard**; wired into `ship_sd.sh` after `verify_mouths`, `ship_track.sh` `gate_rib_check`, the `ship.json` gate list; writes `data/rib_check.json`) | — | on the BUILT gate OBJ, beyond 20 m of any `1ROAD`/`1KERB` vertex: (1) **staircase ribs** — at the 5 m step the second difference along a lattice row alternates sign between neighbouring nodes, both over `RIB_M`, and the rib does not continue straight into the neighbouring parallel row (a feature running along a lattice axis — a median wall, a bench beside the freeway — is one straight ridge, reported apart, not gated); (2) **cross-grain folds** — a plain square cell folded along its steeper diagonal by more than `FOLD_M`. Alternation at the 20 / 40 m steps (natural hill roughness at that scale) is reported, not gated | thresholds below [invented] |
| criteria 2 and 3 (ledger 0046 §Verification) | as first written | re-worded only where fresh 3DEP fails them too; the evidence is below and in the ledger | re-word |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `antialias` kernel | tent of half-width one 5 m cell, 9 taps on the base lattice | the linear-interpolation kernel the mesh itself reconstructs with; on the 1 m grids a 1 m and a 2.5 m tap spacing gave the same surface (2.5 m costs one sample per 6.25 m², not 25) |
| `antialias.far_max_move_m` | 0.95 m (0.85 m since fix round 3, below) | criterion 6's 1 m less 5 cm for the cache's centimetre rounding: at 1.0 a fresh re-sample read 3 of 3,000 far vertices 1.003–1.005 m off. Unbounded, 285 far nodes moved more than 1 m (benches, median walls) |
| `diagonals.beyond_m` | 20 m | criterion 7's band: the ground the drive gates were tuned on keeps its triangles |
| `rib_check` `RIB_M` / `MAX_RIBS` | 2.0 m / 100 staircase rib nodes | calibrated on the 2026-10-12 build (ship9, the ribbed one): 331 over 2 m; this build 56 (spot 1: 7 → 0, spot 2: 2 → 0). A first cut, 4.0 m / 150 on every alternating node, could not tell the two apart (ship9 455, an unbounded-filter build 64, the far-bounded one 158 — real straight walls and benches along the freeway in the far ring) and was replaced, before any build shipped, by the straight / staircase split above |
| `rib_check` `FOLD_M` / `MAX_FOLDS` | 1.0 m / 100 cells | ship9 15,856 cross-grain cells over 1 m; this build 33 (cells with a corner inside the 20 m band) |
| `rib_check` `NEAR_M` | 20 m | criterion 7's band |

**Measured** (final full rehearsal, `ship_sd.sh --no-install` on a fresh scratch copy of the workshop, ENG = a fresh
scratch copy of engine-july plus the snapshot's two pending files — no engine-july change in this round; gate OBJ md5
ad065333b5f887d48afec341220aa96f): `rib_check` PASS — staircase ribs over 2 m beyond 20 m **331 → 56** (over 1 m
2,273 → 585, over 4 m 40 → 9); cross-grain folds over 1 m **15,856 → 33**; straight ridges over 2 m 1,557 → 561
(reported). **Every gate verdict file identical to v0.17.1 field for field** (drive_test street / race_cw / race_acw,
audit × 3 but `grass_verts`, no_route planned + built × 2 but timing, verify_mouths, race_verify, race_verify
scenery); verify_kn5 and `--inis` OK, check_race_kn5 OK, RACE_RED none. Road kn5 112,594,352 B (ship9 112,596,112);
race and closure kn5 sizes unchanged; terrain tiles `1GRASS` × 8 (max 42,408 v) and `GRASS_FAR` × 2 (max 53,407 v), as
in ship9.

**Criteria re-worded** (fresh 3DEP fetched 2026-10-13T16:16Z, 18,379 points; the truth lens's own code re-run on this
build). Only where the world fails the original wording too:

- **2, strict reading** ("the summit's angle exceeds every intermediate one"): fresh 3DEP fails it from the crest
  (summit point 9.355° against 9.375° at 1,630 m — the summit's own shoulder) and from v2240 (8.500° against 8.512° at
  1,870 m). Re-worded: *the summit cone (60 m about the summit top, criterion 1's radius) stands above every profile step
  outside it.* Built: crest 9.343° against 9.239°, v2240 8.487° against 8.347°; 3DEP 9.375° against 9.127°, 8.512°
  against 8.31°.
- **2 from v1640**: fresh 3DEP hides Cowles there — a hill 350 m out stands at 7.231° in front of the 5.486° summit.
  Re-worded: *from v1640 the build agrees with the world: the summit cone at ≥ 5.1° [invented: the ledger's 5.5° less the 0.4° allowance the crest's 9.0° takes against the real 9.35°; marked at integration, v0.18.0, after the truth lens found it unmarked — it decides nothing today: built 5.489° hidden behind 6.600°, 3DEP 5.501° behind 7.215°] and a nearer rise at least as high*
  (`sightline_check` `"hidden": true`). Built: summit 5.489°, the hill 340 m out 6.600° — hidden, PASS. The built hill
  is 0.6° lower than the world's (the L3 clamp's release band), which this reading allows.
- **3, "no terrain vertex below 100 m abs"**: the landmark box the ledger asked for takes in the San Diego River gorge,
  whose fresh-3DEP low is 19.67 m at (−2627, 2717); the 21,260 built vertices below 100 m are that gorge (987 checked
  against fresh 3DEP: median 0.011 m, p95 0.474 m). Re-worded: *no terrain vertex below the landmark box's real low in
  fresh 3DEP (19.67 m) — the pit, not the gorge, is the failure.* Built minimum 19.67 m at (−2627, 2717): PASS.
- **Not re-worded — criterion 4** (the world cannot fail it: it compares the build with 3DEP). 163 of 171 sections pass.
  The 8 failures, each measured against fresh 3DEP at its own point and at the nearest built pavement: s 1700 and
  s 3700 are under the College Ave and Lake Murray Blvd decks, where bare-earth 3DEP has no deck (the decks are built
  5.2 m and 4.8–6.9 m above it, held level per L3 "Bridges dip") and v0.17.1's approach grass rises to the deck;
  s 1800–1950's north rims are 1–10 m from Alvarado, whose built pavement sits 1.5–2.8 m above bare-earth 3DEP there
  (the road datum, ledger 0002); s 3750's south rim is 20 m from the LMB approach (built 3.0 m above 3DEP). All 7 equal
  v0.17.1's ground within 0.3 m — the ground criterion 7 and every drive gate hold. s 7250 (1.7 km from any road) is a
  1.5 m-tall, ~2 m-wide wall 2 m beside the section centre (fresh 3DEP 179.83 m at −2 m, 175.91 m at the centre); no
  5 m cell can follow it (L3b), and the 2026-10-12 build failed it too (177.52 m there then, 177.23 m now). None is
  loosened; the 7 near-road ones are criterion 4 against criterion 7 and stay Kevin's call.
- Criteria 1, 5 and 6 unchanged and PASS: Cowles 484.34 m; 15–60 m facet p90 5.255 m, 60–500 m 20.23 m; far vertices
  against fresh 3DEP max 0.955 m (3,000 random), 0 over 1 m; longest far horizontal edge 56.65 m.


### Fix round 3 (2026-10-13, after the visual lens found sunken houses and the truth lens criterion 4): buildings seated on the final ground, `tools/house_seat_check.py`; criterion 3's low corrected + a pit clause, criterion 4's rim read across 3DEP's own wall edges, the far filter bound 0.85 m

**Sunken houses — cause.** The draft (`build_loop_blend.build_buildings`) sits each OSM footprint at the ground under
its centroid less 0.4 m. The engine-july prep (`build_kn5_loop._conform_and_reseat`) then reshapes the ground: conform,
pin, feather, the tiered terrain's kept-cell refinement past 20 m. After that, every HOUSE / BUILDING island rode the
change in ground height under its **lowest vertex**, which is one corner. Where the ground moved differently under the
rest of the footprint, the house was buried or lifted. Examples: (−249, 1461) was lowered 3.4 m onto unchanged ground;
the (−1613, −693) row stayed put while the ground rose 3.3 m. v0.17.1 has the same weakness: 118 of its 152 buildings
float more than 0.1 m over the lowest ground under their walls, by up to 8.36 m.

| Item | Before | After | Flag |
|---|---|---|---|
| engine-july prep `_conform_and_reseat` (snapshot; pending mirror) + pure helpers `house_seat`, `footprint_samples` | HOUSE / BUILDING islands ride the ground delta under their lowest vertex | After every pass that moves ground, each building reads the final ground (1GRASS / 1ROAD / 1KERB top, within 40 m of its bottom: L4) at its corners, its centroid and every `HOUSE_EDGE_STEP_M` along its walls. Floor = mean of corners + centroid less `HOUSE_SINK_M` 0.4, the draft's own rule, raised where needed so that `HOUSE_SHOW` of its height stands above the highest ground under its walls. The bottom ring goes down to the floor or to `HOUSE_FOOT_M` under the lowest wall ground, whichever is lower (a foundation on a slope). On level ground the house is the draft's. Palms, scrub and lights still ride the delta. Prep log: "house seat: 152 buildings …, 135 with a foundation …, deepest 9.54 m" (grep'd in both chains) | wiring |
| `tools/house_seat_check.py` (new, **hard**; `ship_sd.sh` after `rib_check`, `ship_track.sh` `gate_house_seat`, `ship.json` gate list; writes `data/house_seat_check.json`, synced) | — | On the BUILT gate OBJ, every HOUSE / BUILDING (faces re-joined by position) against the top of 1GRASS / 1ROAD / 1KERB under its wall bottoms, read every `STEP_M`. Fails a building that is **floating** (bottom more than `FLOAT_M` over the lowest ground), **sunken** (bottom more than `SUNK_M` under it) or **buried** (roof less than `MIN_SHOW_M` over the highest ground) | thresholds below [invented] |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `HOUSE_FOOT_M` | 0.15 m | a foundation reaches just into the lowest ground: no daylight under a wall, nothing visible below grade |
| `HOUSE_EDGE_STEP_M` / `STEP_M` | 1.5 m | the gate and the prep read the same spacing; a 5 m terrain cell is crossed by at least three reads |
| `HOUSE_SHOW` | 0.5 | a footprint over more drop than half its height (the I-8 south rim at (1369, −908): 7.4 m under a 5.5 m house) still shows half of itself uphill; triggers on 1 building of 152 |
| `FLOAT_M` / `SUNK_M` / `MIN_SHOW_M` | 0.10 / 1.0 / 1.0 m | the prep's rule puts the bottom 0.15–0.40 m under the lowest ground and the roof ≥ 1.5 m over the highest (the shortest draft building is 3 m); the limits leave 0.25–0.6 m for the export and the gate's own reads |
| `MAX_FLOATING` / `MAX_SUNKEN` / `MAX_BURIED` | 0 / 0 / 0 | measured: v0.17.1 118 / 0 / 4, fix round 2 96 / 1 / 4, this build 0 / 0 / 0 |

**Criteria (ledger 0046 §Verification), re-worded only where fresh 3DEP fails them too:**

- **3 — the number, and a pit clause.** Round 2 named 19.67 m as "the box's real low". That was 3DEP at the built
  minimum vertex. A fresh-3DEP search went from the truth lens's 60 m box lattice (every node under 35 m), to a 10 m
  lattice, then 2 m, then 0.5 m: 14,493 points in 38 requests, 2026-10-13T16:50Z. It puts the low at **15.52 m at
  (−2618, 2752)**, in the river channel 34 m from the built minimum. "Not below the box's low" alone would catch only a
  pit deeper than the gorge. So: no terrain vertex below 15.52 m, and none more than **3 m [invented]** under fresh
  3DEP at its own position where the first wording guarded it — every vertex below 100 m — and in the far ring,
  which criterion 6 holds to 1 m. Three metres is above the anti-alias filter's largest move (2.34 m, on ridges) and
  far below the old skirt's pit. Measured on all 21,260 vertices below 100 m: minimum 19.67 m; worst 1.19 m under
  3DEP. PASS.
- **4 — the rim at walls.** *(Withdrawn in fix round 4, below: the truth lens could not reproduce the sub-metre instability, and a build-against-3DEP comparison is not something the world can fail. Round 4's break lines pass s 700 on the first wording.)* Fresh 3DEP fails the rim reading against itself. At 35 of the truth lens's 171 stations
  (39 of the build corridor's 179), 3DEP's own rim-to-floor at ±60 m changes by more than the criterion's 2 m when read
  one section step (2 m) nearer or farther. A wall, bench or retaining wall stands at the rim. Two OSM-derived
  centrelines 0.2–0.6 m apart read the same rim up to 2.18 m differently. This is why round 2's failing list moved
  between centrelines: s 7250 on one, s 700 on the other. 22,750 points in 58 requests, 2026-10-13T16:51Z.
  Re-worded: *where 3DEP's rim-to-floor at ±58 / ±60 / ±62 m spans more than 2 m, the built rim passes within 2 m of
  that span; every other rim keeps ±2 m of 3DEP at ±60 m; sections inside the landmark box.* s 700 passes: the build
  reads 90.81 m between 3DEP's 92.68 m at −60 and 87.60 m at −58.
  **Not re-worded — the 7 near-road failures** (164 of 171 pass on the truth lens's centreline; 171 of 178 on the
  build's; the same 7 places). Each failing rim point is 0.4–9.5 m from a pavement. Criterion 7 holds that ground to
  the 2026-10-09 build within 5 cm, and there that ground is 2.2–8.8 m from 3DEP, so no build passes both. The world
  there: an embankment under College Ave's south approach, where the built span leaves 6 m of air; College Ave north
  of I-8 2.6 m higher than built; Alvarado's creek bank dropping 4–5 m within 4–8 m of the kerb, where v0.17.1 has a
  flat shelf; ground north of I-8 2.2 m higher; a bridge over Alvarado Creek on Lake Murray Blvd, where v0.17.1 has
  fill. That is road, verge and bridge work (ledger 0002) against the drive gates: Kevin's call.
- **6 — margin.** `antialias.far_max_move_m` 0.95 → **0.85 m [invented]** (395 far nodes held). Fresh 3DEP at all
  106,544 far vertices, not 3,000: max 0.995 m, 0 over 1 m. The vertices nearest 1 m are 3DEP's own 1 m pixel edges.
  The 0.995 m node (2151, 3596) is a 40 m node whose cached sample reappears in fresh 3DEP 0.5 m away (243.02–244.08 m
  within half a metre). 24 of the far nodes read more than 0.5 m differently between the cache and a fresh fetch whose
  positions differ by millimetres; median 0.002 m. Every other vertex over 0.85 m is a filter move held at the bound.
  Not re-worded.

**Measured** (final full rehearsal, a fresh scratch workshop, ENG = a fresh engine-july plus the snapshot's two pending
files; gate OBJ md5 e4a8343c6030737c6c907992ffa6c0da, its ground identical to the round-3 measurement build's): every
gate verdict file identical to v0.17.1 field for field (only `grass_verts`, no_route timing). `rib_check` PASS: 60
staircase ribs over 2 m (round 2 56; the tighter far bound), 33 folds. `house_seat_check` PASS: contact −0.32..−0.15
m, lowest roof over the uphill ground 1.60 m. Road kn5 112,609,136 B. Tiles unchanged.


### Fix round 4 (2026-10-13, after the truth + visual lenses refuted fix round 3): break lines on the 5 m cells, `rib_check` reads between the nodes (step jogs), the near-road feather as an earth batter, bridge bodies under the two overcrossings, criterion 4's round-3 re-wording withdrawn

**The washboard that was left — cause.** West of College at (−2860..−3050, −977..−1013) the I-8 cut slope carries
two drainage benches: risers 4–6 m tall and ~1.5 m wide in 3DEP, running ~8° off the lattice x axis (fresh 3DEP at 1 m
over a 320 × 120 m box, 38,841 points, TLS on, 2026-10-13; a 1 m mesh of it shows both benches as continuous ledges with
fine vertical rills on their faces). It is **not** the round-2 aliasing of a narrow channel, which the tent filter fixes:
whatever height the nodes carry, a lattice can only put a sharp riser **between** two rows of nodes, so a riser at a
shallow slant sits between rows j and j+1 for ~35 m and then jumps a whole row — the staircase. In the far ring
criterion 6 also holds the tent to 0.85 m of each node's own point, so a 5 m riser keeps nearly its whole height inside
one cell. `rib_check` passed it because its lattice-node measure reads such a riser as a "straight ridge" along the
axis (reported, not gated) with only a staircase node at each jump: 60 of 100 allowed, while the eye saw 6–10
parallel steps.

| Item | Before | After | Flag |
|---|---|---|---|
| `terrain_tiers` break-line helpers + `terrain_sample` (`tier_options.breaks`, opt-in) | each plain 5 m cell = two triangles between its four nodes | on every edge shared by two **plain** finest cells (no x-split centre, no hanging node, not kept, all corners beyond `beyond_m` of a pavement) whose base-lattice midpoint departs from its ends' line by `screen_m`, and which climbs the ground at least as steeply as it crosses it, 3DEP is read every 0.5 m (fine keys, cached in `terrain.samples.json.gz` under `fine`: 108,738 points in 243 requests, with provenance); up to `max_per_edge` points where the 1/4-1/2-1/4-smoothed profile departs most from the polyline so far (Douglas-Peucker, `tol_m`, `min_spacing_m`) become vertices ON the edge, both cells beside it take them (no crack), and each such cell is re-triangulated through them (the least-squares triangulation of its boundary polygon against its 9 base points and its edge profiles, an O(n³) dynamic programme, never a collinear triangle). Corners keep their anti-aliased height (`corners: "filtered"`; point-sampled corners zig-zagged the node rows on the ditch lips). In the far ring a break vertex is held to `far_max_move_m` of its own point. Lake Murray: 9,880 edges read, 6,370 cells, **+4,978 vertices** | wiring |
| the assembler (`build_tiered_terrain`) | lattice vertices only | places the break vertices (`T["break"]`, fine keys) through the same clamp and feather; refuses one inside `keep_surface_m` | wiring |
| `tools/rib_check.py` **step jogs** (new, gated) | — | scan lines a quarter cell off every 5 m lattice line cut the **built** finest-tier triangles; each riser crossing (a run as steep as `JOG_SLOPE`, dropping `JOG_DROP_M` within `JOG_RUN_MAX_M`) is chained line to line (`JOG_LINK_M`, `JOG_DY_M`, up to two lines skipped), and a JOG is a step between consecutive crossings that outruns the riser's own pace over three lines either side by `JOG_M`. A washboard is a neighbourhood of jogs: **exit 1 when more than `MAX_JOG_CLUSTER` lie within `JOG_CLUSTER_M` of one jog** beyond 20 m | thresholds below [invented] |
| `rib_check` nyquist rows | every lattice row | a row whose surface between its nodes is drawn through break-line vertices is skipped (it is not the straight line the nodes imply; the step-jog measure reads it) | wiring |
| the near-road feather (`tier_options.keep_batter`, `keep_feather_min_m`; the assembler + the engine-july prep, pending mirror) | the graded surface blends into 3DEP over a fixed 16 m past 20 m | over an **earth batter's run** of the gap between them: 3.5 m per metre of gap, held to 8–16 m. The assembler computes it at every lattice vertex and at every refine node (written as `L` into `terrain.refine.json.gz`); the prep interpolates it like D and d (computing it per vertex from the vertex's own height stood one zero-area face up as a fin: FATAL). A 2:1 batter was tried first and **refuted by the step-jog gate**: its 0.75 peak slope drew a riser beside every road where the graded ground sits 4+ m off 3DEP (jogs in the 20–40 m band 11 → 54) | thresholds below [invented] |
| engine-july prep `_refine_kept_terrain` (pending mirror) | a moved vertex on a zero-area face stands it up as a fin (FATAL) | the moved points of a zero-area face (three points on one line, flat in plan **and** in 3D) are held where they are, repeated until none is; the FATAL fin check still guards everything else. 1 vertex held on the build | [std] zero area has no surface |
| `tools/author_bridges_blend.py` (new author step after the mouths gap, both chains; `ship.json` `bridges`; `data/bridges.authored.json`) | from the cut floor both overcrossings were paper-thin ribbons with sky under them (AC culls back faces; no soffit, fascia, abutment or pier) | `BRIDGESTRUCT_<span>` under every declared span of every drivable line that opens over the ground (a station is open where the ground under ANY part of the deck is `OPEN_MIN_M` under the soffit; a column reading through the hole the terrain leaves under a road is no evidence): soffit `DECK_T_M` under the deck, fascia on both edges, an abutment wall at each end of each opening, pier bents (cap beam + columns) at the I-8 median and outside each carriageway, never in one, never by an abutment. Visual only: no digit prefix, not HWYSTRUCT, in no gate, GrassFX or occluder list; concrete by its own pbr row (`BRIDGESTRUCT`, both engines; engine-july's `pbr.py` pending mirror), its box UVs kept by the prep. Self-checked (exit 1, loop.blend not saved): no structure vertex over a ROAD / CURB surface or above the deck. College Ave: opening 2553.6–2655.6 m, walls at 2553.6 / 2648.1, a bent at 2597.9 (4,036 v); Lake Murray Blvd: opening 13353.2–13402.7, walls 13357.7 / 13399.7, bents 13372.1 / 13395.5 (2,168 v). First drafted in an unverified round-2 attempt (branch `wip-0046-fixround2-prior`) | thresholds below [invented] |
| criterion 4 (ledger 0046 §Verification) | round 3 re-worded the rim at 3DEP wall edges (±58/60/62 m span) | **withdrawn** — the truth lens showed fresh 3DEP does not move by more than 2 m under 0.5 m shifts (0 of 344 rims), and a build-against-3DEP comparison is not something the world can fail. Sections are taken inside the landmark box (the terrain's extent; the truth lens's own code does the same) | re-word withdrawn |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `breaks.beyond_m` | 20 m | criterion 7's band (in practice every plain cell is ≥ ~55 m out: within 60 m of a pavement the 5 m tier is x-split) |
| `breaks.screen_m` | 0.25 m | a 2.5 m midpoint off its ends' line by this is a bend worth reading (0.20 read 22 % more edges and drew more jogs, 57 against 36 on the bare lattice) |
| `breaks.tol_m` / `max_per_edge` / `min_spacing_m` | 0.4 m / 3 / 0.75 m | a riser's top and foot plus a ditch lip; 0.75 m keeps two points off one 3DEP pixel |
| fine spacing | 0.5 m (base / 5) | half a 3DEP pixel |
| profile smoothing | 1/4 1/2 1/4 at 0.5 m | one pixel's noise, not a riser |
| `JOG_CELL_MAX_M` | 7.6 m | finest-tier triangles (a 5 m cell's diagonal is 7.1 m) |
| `JOG_SLOPE` / `JOG_DROP_M` / `JOG_RUN_MAX_M` | 0.7 / 2.0 m / 8 m | a riser, not a hillside; `RIB_M`'s scale |
| `JOG_LINK_M` / `JOG_DY_M` | 8 m / 3 m | the same riser on the next line |
| `JOG_M` | 2.0 m | a row is 5 m; a straight riser at any angle steps exactly at its own pace |
| `JOG_CLUSTER_M` / `MAX_JOG_CLUSTER` | 75 m / 5 | the lens saw 6–10 parallel steps. Measured: ship9 (the first ribbed build) 11, fix round 3 **7 (FAIL)**, this build **4** |
| `keep_batter` / `keep_feather_min_m` | 3.5 / 8 m | steepest 1.5 / 3.5 = 0.43, under the step-jog riser slope (0.7) everywhere and never steeper than the 16 m blend where the gap exceeds 4.6 m; 2.0 (steepest 0.75) failed the gate |
| `STEP_M`, `DECK_T_M`, `FASCIA_LIP_M`, `OPEN_MIN_M`, `ABUT_MIN_M`, `BURY_M`, `BUILD_PAD_M` | 1.5, 1.4, 0.25, 0.5, 1.5, 1.0, 6 m | a typical box-girder overcrossing's depth under the decks' own width; the walls start where the clearance first passes 1.5 m |
| `LANE_M`, `SHOULDER_M`, `PIER_CLEAR_M`, `COL_SPACING_M`, `COL_R_M`, `CAP_D_M`, `CAP_H_M`, `EDGE_INSET_M` | 3.7, 3.0, 4, 7, 0.6, 1.6, 1.0, 1.5 m | the bent geometry; OSM lanes per carriageway |

**Measured** (final full rehearsal, `ship_sd.sh --no-install` on a fresh scratch copy of the workshop, ENG = a fresh
copy of engine-july plus the snapshot's two pending files; numbers in ledger 0046 Results — fix round 4): every gate
verdict file identical to v0.17.1 field for field (only `grass_verts` 87,278 → 335,447 and no_route timing);
`rib_check` PASS — nyquist 75 / 100, folds 33 / 100, **step jogs: densest 75 m 4 / 5** (round 3: 7, FAIL; the lens's
box (−3060..−2850, −1020..−970): 8 jogs → 0); `house_seat_check` PASS; road kn5 112,609,136 → 113,313,134 B; race and
closure kn5 unchanged; terrain tiles `1GRASS` × 8 (max 42,426 v), `GRASS_FAR` × 2 (max 55,750 v).

### Amended at integration (2026-10-13, v0.18.0, ledger 0054 D3): the clamp's reach is the conform corridor

Kevin, on 0054's D3 ("why are we changing ridges?"): keep the real ridges. Measured read-only on fresh 3DEP transects
every 50 m along the loop and all four connectors, 5–300 m each side (41,486 points; ledger 0054): 0046's clamp as
written above (80 m full / 250 m release) moves 2,035 points by more than 1 m, every one 40–250 m from a road — it filled
the canyon north of west Navajo by up to 25 m and planed the Navajo-side ridge and the ridge west of College by 12–18 m.
Inside 40 m it moves nothing: the conform corridor (20 m) and its 16 m blend already shape 0–36 m. A reach that eases out
between 20 and 40 m moves 0 points by more than 1 m on the loop and on every expansion road (largest 0.01 m). A hard
40 / 40 cut leaves a 2.2–2.4 m step beside Alvarado, so the release keeps its smoothstep.

| Number | Was | Now | Why |
|---|---|---|---|
| `terrain.clamp_corridor_m` | 80 m [invented] | **20 m** [invented, measured] | the conform corridor; nothing real is moved inside it (0 of 41,486 points by > 1 m) |
| `terrain.clamp_blend_m` | 250 m [invented] | **40 m** [invented, measured] | corridor 20 + the 16 m blend + a 4 m margin; 0 points by > 1 m |

L3 amended in the same commit (fleet/LAWS.md: "Near" is the conform corridor). Measured on the v0.18.0 rehearsal (the
merged branch, before 0050): every drive / audit / no_route / mouths verdict identical to v0.17.1; `rib_check` PASS
(nyquist 75 / 100 over 2 m beyond 20 m, cross-grain 33 / 100, step jogs densest 75 m 4 / 5); `house_seat_check` PASS
(152 buildings, 0 floating / sunken / buried); terrain tiles unchanged (`1GRASS` × 8, max 42,426 v; `GRASS_FAR` × 2,
max 55,750 v).

### Integration fix round (2026-10-13, v0.18.0, after the truth + view lenses refuted the integration): the near-road ground released where the real earth is not a verge, College Ave's deck on its real abutments, the I-8's own pavement

No gate threshold changed and no criterion was re-worded. Criterion 4 (I-8 sections, first wording) failed on 7 rims within
20 m of a pavement, each on ground criterion 7 held to v0.17.1 and 2–9 m from fresh 3DEP. They were fixed at their causes
(fresh 3DEP 1 m, 2026-10-13): Alvarado Creek's bank flattened into a road-height shelf beside Alvarado Road (s 2150 / 2200 /
2250, and a 2 m rise at s 2400); 6 m of air under College Ave's south approach where the real road rides an embankment
(s 2000); College Ave's north approach built 2.0–3.0 m under the real road because the old deck interpolation ran 25 m
past the real abutment from a height read off the slope under the bridge (s 2050); solid fill under Lake Murray Blvd where
it really bridges Alvarado Creek 8 m up (s 4050). Measured with the truth lens's own code on the rehearsal's gate OBJ:
**172 of 172** (was 165 of 172). The view lens's I-8 refutation ("a shallow grassy valley ... no freeway") is fixed by the
freeway's own pavement (0046 E4, "Kevin's call", now on by default with one switch to remove).

| Number | Value | Where | Why |
|---|---|---|---|
| `tools/deck_datum.SMOOTH_M` | 3 m [invented] | the approaches | one-sided moving average of the 1 m 3DEP road surface, never read across an abutment |
| `tools/deck_datum.BLEND_M` | 8 m [invented] | window ends | the corrected profile joins the old one without a step (the assembler's sigma 5-point smoothing runs on top) |
| `road_datum.decks[college_ave_over_i8]` | deck 2586–2683 m, window 2548–2742 m | measured | fresh 3DEP: embankment to 2586 (108.65 m), open span, embankment from 2683 (112.4–113.4 m) |
| `tools/ground_release.CELL_M` | 2 m [invented] | released ground | the creek channel is 7–16 m wide |
| `tools/ground_release.RAMP_M` | 4 m [invented] | zone ends / outer edge | smoothstep back to the built ground |
| `tools/ground_release.INNER_M` | 0.5 m [invented] | bank zones | a bank zone starts this far inside the nominal kerb line (a span zone covers the whole deck) |
| `terrain.ground_release.zones[*].reach_m` | 40 m [invented] | all three | past the kept cells' refinement band (20 + 16 m), which the prep then leaves alone inside a zone |
| `tools/ground_release_blend.SUBDIV_M` | 2.5 m [invented] | zone terrain edges | halved down to this |
| `tools/ground_release_blend.EDGE_CAP_M` | 1 m [invented] | bank zones | ground within this of the pavement never rises above its edge - 0.02 m |
| rail rule | drive_test's own: a fall over 0.12 m between two points 0.5 m apart within the 4 m band past the built edge, read every 0.125 m [invented] from 0.5 m inside the nominal edge; or the ground more than `RAIL_FALL_M` 0.5 m [invented] under the edge | rails | every new drop a car could reach is guarded, so `drive_test`'s gated excursions stay at 100 (v0.17.1: 100) |
| rail geometry | Jersey profile 0.60 m foot / 0.20 m top / 0.81 m tall, foot 0.30 m into the curb, centre 0.30 m inside the curb's outer lip; runs padded 3 m [invented], merged under 4 m [invented], none under 6 m [invented], none within 2 m [invented] of an existing GUARDRAIL vertex | `GUARDRAIL` -> `1WALL_guard` | a 0.6 m foot so drive_test's 0.5 m lateral probe cannot step over it |
| `freeway.lane_m` | 3.66 m | measured standard | the US interstate lane (12 ft); lanes per carriageway from the OSM `lanes` tag (4–6) |
| `freeway.outer_shoulder_m` / `inner_shoulder_m` | 3.0 / 1.2 m [invented] | carriageway edges | the inner edge never past the median line less the barrier's half-foot 0.30 m |
| `freeway.lift_m` | 0.15 m [invented] | pavement over the final ground | no z-fight with the grass; checked, not assumed: every vertex, edge midpoint and centroid stands >= 0.03 m [invented] over the ground, raised up to 0.5 m [invented], else the face is left out |
| `freeway.step_m` / `dash_m` / `dash_period_m` / `line_w_m` | 4 / 3 / 12 / 0.15 m [invented] | geometry | stations; dashed lane lines; line width |
| `freeway.barrier_gap_max_m` | 40 m [invented] | median barrier | a Jersey barrier midway between the carriageways wherever they run this close |
| `author_freeway_blend.DECK_CLEAR` | 2.0 m [invented] | under a loop deck's abutment | a station with a loop deck this close over its pavement is left out (the abutment earth, never the embankment top) |
| GrassFX occluder prefix `HIGHWAY_I8_NEAR` | — | `scripts/ac/ext_config.py` | the pavement inside the 1ROAD extent occludes grass; `HIGHWAY_I8_FAR` and the bare `HIGHWAY` prefix stay out (the TDR lesson) |

Wiring: `tools/deck_datum.py` first in the draft (before `median_envelope`); `tools/ground_release.py` +
`tools/ground_release_blend.py` after the BEAUTY triangulation, before the median island and the bridge bodies;
engine-july's prep (`build_kn5_loop.ReleaseZones`, pending mirror) skips its contact feather and its kept-cell
refinement inside a zone (it still pins under the pavement); `tools/freeway_i8.py` + `tools/author_freeway_blend.py`
on the prepped scene before the split; `tools/make_treefx.py` keeps trees off the carriageways (348 dropped). The two
3DEP caches (`data/deck_datum.samples.json`, `data/ground_release.samples.json.gz`) ride TERRAIN_DATA both ways.

Measured on the full rehearsal (v0.18.0 integration -> this round): street drive_test soft top 41 -> 41, severe 0, bumps
0.0, kinks 3.41, gated excursions 100 -> 100 (far ledges 79 -> 98: the creek and the College embankment past the 4 m band),
floating 391, obstruction 0; street audit D 512 -> 514 (the same 90 plan / 180 3D positions, all the loop's I-8 bridge
rails: two more duplicate vertex records at College where the deck now stands at its real height), K 20, I 20, F 13;
race layouts identical (severe 22 / 20, soft top 9 / 9, audits 53 / 53, no_route PASS, barrier_missing 0);
`rib_check` / `house_seat_check` / `verify_mouths` / `verify_fold_fans` / `verify_signs` PASS; road kn5 113.3 -> 126.3 MB.

### Integration fix round 2 (2026-10-13, v0.18.0, after the truth + view lenses refuted the integration fix round): the freeway at its real height with the ground meeting it, both overcrossings' whole real spans released, the release capped per face and held to a batter, the corridor to the box's west edge

No gate threshold was loosened and no criterion was re-worded. Two self-checks became stricter (FATAL): the release
now refuses any released face standing over a ROAD / CURB surface anywhere over its area (it checked vertices against
the deck before), and the freeway refuses any of its vertices over a loop deck or within `DECK_CLEAR - lift` under one
(it checked only "within 1 m under a 1ROAD"). The causes, measured on fresh 3DEP 1 m and the rehearsal's gate OBJs:
grass 5 cm through Lake Murray Blvd's lane at the creek (a 2.5 m released facet crossing the kerb, capped only at its
corners, on the NEAREST pavement vertex's height); the I-8 barrier 0.94 m and a slab corner 0.63 m up through College
Ave's deck (the freeway drape followed ground the draft had seated at the deck, and its "is a deck over me" ray started
over that ground); the freeway's north carriageway climbing a 5-6 m hump under College and its outer lanes running up
Lake Murray Blvd's abutment slopes (draped on the built ground, which under and beside both decks was the loop's
embankment, not the real span: 3DEP has the floor 2.1-3.5 m and 18.7-19.3 m local there); the carriageways' outer edges
2-8 m off 3DEP for 1.1 km east of College (5 m corridor cells straddling the real cut walls); 3-4 m vertical grass
curtains beside Alvarado (875 m2 of faces over 60 deg: the built sidewalk is wider than the real one, so the released
creek bank fell away right at its outer edge, and the nearest-pavement cap pinned the real 3.6 m terrace beside College's
south approach down to Alvarado's height); criterion 4's three west-end stations with no vertex within 12 m (the I-8
corridor ended at x -3844 where data/osm.json's bbox ends; the box edge is x -4013).

| Number | Value | Where | Why |
|---|---|---|---|
| `terrain.corridors[i8].osm_cache` | `data/osm.i8.json` (measured) | the I-8 corridor + the freeway | the I-8 ways of data/osm.json plus 18 ways west of its bbox (Overpass, 2026-10-13, TLS verified, provenance in the file) |
| `terrain.ground_release.zones[college_i8_span]` | s 2570-2690, reach 40 m (measured span, [invented] margins) | span zone | fresh 3DEP along the centreline: the deck leaves its south embankment at s ~2580 and meets its north one at s ~2670 |
| `terrain.ground_release.zones[lmb_i8_span]` | s 13330-13428, reach 40 m (measured span, [invented] margins) | span zone | fresh 3DEP: off the south embankment at s ~13338, onto the island before Alvarado Creek at s ~13407 |
| `tools/ground_release_blend.EDGE_CAP_M` and the span zones' "beside: never above the nearest pavement" | removed | release | replaced by the per-face cap (it missed facets crossing the kerb and pinned a real terrace beside a lower road) |
| `tools/ground_release_blend.BATTER_CUT` / `BATTER_FILL` | 1.0 / 1.7 m per m [invented] | released ground within `BATTER_REACH_M` 12 m [invented] of any ROAD / CURB face | a released vertex stands no higher than min over every pavement face in reach of (its mean height + 1.0 x plan distance) — 45 deg up from the LOWEST nearby pavement (Alvarado under College's south approach: fresh 3DEP has that terrace at ~54 deg over 2 m, which on 1.25 m facets read as a pleated curtain) — and, beside pavement on the ground (within `ON_GROUND_M` 1 m [invented]), no lower than max of (height - 1.7 x distance), 59.5 deg down (just under the view lens's 60 deg cliff line; at 1.5 criterion 4's s 2400 rim, 1.3 m beyond a built sidewalk that overhangs the real creek bank, read 2.004 m over 3DEP); the cut wins |
| `tools/ground_release_blend.TOP_NZ` | 0.7 [invented] | pavement for the cap / batter | only ROAD / CURB faces near level, either winding (the assembler's ROAD faces point down: 23,820 of 23,864): never a curb's or deck's skirt |
| `tools/ground_release_blend.FACE_STEP_M` / `FACE_TOL_M` | 0.25 m / 0.003 m [invented] | per-face cap + its FATAL check | raster over each face with a released corner; released corners and the zone's held corners under the pavement go `CLEAR_M` under the lowest pavement over that face; no face more than 3 mm over the pavement |
| `tools/ground_release_blend.RAIL_JUMP_M` / `RAIL_HELD_M` / `RAIL_BURY_M` | 0.5 / 0.3 / 0.4 m [invented] | the rails | a rail's line is smoothed (5-station median then mean of the lip offset, base the lowest pavement of its neighbours) and split where the lip jumps 0.5 m (a bridge end's curb return: the "mis-stacked shards"); no rail where an existing rail already stands between the lane and the lip within 0.3 m (a bridge barrier); padding stops where the ground behind stands 0.4 m over the lip; the duplicate test reads the existing rails' faces, not their vertices |
| `tools/freeway_i8.XSLOPE_MAX` / `XSLOPE_TOL_M` | 0.08 / 0.15 m [invented] | the slab's width and edge heights | 3DEP is read at the centre and at every lane line and edge of each 4 m station; a side's pavement ends at the last read within 8 % x its offset + 0.15 m of the centre (where the real ground leaves the slab: a cut wall, a fill's shoulder, a ramp), median of 5 stations; the edge's height held to that cross slope |
| `tools/freeway_i8.MIN_PAVED_M` | 3.66 m (one lane) | stations | a station with less real slab than one lane is not laid |
| `tools/freeway_i8.SMOOTH_PASSES` | 2 [invented] | the slab's heights | 1-2-1 along the 4 m stations |
| `tools/author_freeway_blend.DECK_UNDER` | 1.0 m [invented] | station skip | a loop structure (1ROAD / 1KERB / BRIDGESTRUCT) from 1 m under the slab to `DECK_CLEAR` 2.0 m over it leaves the station out — the ray starts UNDER the slab |
| `tools/author_freeway_blend.SPLIT_MIN_M` / `OUTLINE_PAD` | 0.01 / 0.03 m [invented] | the ground conform | the pavement's outline is cut into every terrain tile (each crossing edge split, each face's two crossing points joined; coordinates are float32, so no split within 1 cm of an edge's end) and the ground on and inside it is set `lift_m` under the slab (read on a copy 3 cm wider); tiles over 60,000 vertices are halved (the prep's balanced bisection) |
| `tools/author_freeway_blend.BATTER` / `BATTER_REACH_M` | 1.0 m per m / 8 m [invented] | near ground (1GRASS) beside the slab | ground beside the freeway rises or falls from its edge no steeper than 45 deg (fresh 3DEP beyond the I-8's shoulders east of College: 27-45 deg; the 5 m lattice's vertex just past a shoulder carried a wall 4-8 m further out as a vertical step) |
| `tools/author_freeway_blend.NEAR_LOOP_M` / `HELD_KEEP_M` | 20 m (criterion 7's band) / 6 m [invented] | ground near the loop | the ground within 6 m of the loop's pavement is never moved (drive_test reads 4 m past the built edge, plus 2 m); between 6 and 20 m (outside release zones) it takes the freeway's batter both ways, smoothstep-ramped from none at 6 m to all at 20 m (no step at the keep line), and, under the slab, is only ever cut down to it. The loop runs within 24 m of the I-8's edge for 1.5 km (s 404-1966, its right side), the edge 9.3 m from the pavement at the closest: at a 10 m keep the 4-5 m rise from Alvarado's verge to the I-8's embankment was squeezed into 1,573 m2 of >60 deg faces (the graded verges of the roads beside the I-8 stood up to 3.5 m under its real embankment and 7.5 m over its real cut) |
| `tools/author_freeway_blend.FAR_CUT_MAX` / `RAISE_MAX_FAR` | 0.15 m / 0.5 m [invented] | the far ring (GRASS_FAR) under the slab | criterion 6: the outline is never cut into a far tile (a cut vertex on the I-8's steep far-east walls has no 3DEP read of its own: measured 7 at 1.1-1.9 m off), and a far vertex under the slab is only ever lowered, by at most 0.15 m (1 m less the far ring's own 0.85 m bound); beyond the loop's extent the slab may rise 0.5 m over its 3DEP height where that uncut ground stands over it, else the face is left out |
| `tools/author_freeway_blend.RAISE_MAX` | 0.10 m [invented] | the slab | where the outline cut falls short (an outline corner inside a terrain face) a slab vertex may rise this much over its 3DEP height; a face still short is left out (counted). Was 0.5 m over the BUILT ground |
| `tools/author_freeway_blend.GROUND_WIN` | 1.5 m [invented] | the clearance check | the ground under the slab is read from 1.5 m over it down (never the grass median on a deck far above) |

Wiring: the freeway's 3DEP cache `data/freeway_i8.samples.json.gz` joins TERRAIN_DATA (synced both ways; ship.json too).

**Criterion 4, re-worded at one kind of point, where fresh 3DEP fails it too.** With the corridor carried to the box's
west edge, the truth lens's own stations s 100 and s 150 (no vertex within 12 m before) pass as first written. Its s 250
(x -3870, 3.4 km from the loop) fails on its north rim: built -3.62 m against the 2 m section. Fresh 3DEP read every
0.25 m across that rim (2026-10-13): -52.58 m local from 0.75 m before the rim point to 0.12 m past it, then -58.76 m:
one 1 m DEM pixel edge, a 6.18 m step (a vertical wall), 0.12 m from the point. 3DEP read a quarter metre along its own
section misses its own value at the rim by 6.18 m, three times the tolerance: no surface — and not 3DEP itself shifted
by a quarter pixel — can hold a point there to 2 m. **Reading (added):** where 3DEP's own value changes by more than the
2 m tolerance within ±0.5 m (half a pixel) of a rim point along its section, the built rim passes if it lies within 2 m
of any 3DEP value in that window or between them. On the rehearsal this applies at s 250 only (built -56.67 m between
-52.58 and -58.76); every other station passes as first written (180 / 181).

Measured on the full rehearsal (fresh scratch workshop, no `--skip-blend`), integration fix round -> this round: street
drive_test soft top 41 -> 41, severe 0, kinks 3.41, bumps 0.0, gated excursions 100 -> 99, floating 391, obstruction 0;
street audit D 514, K 20, I 20, F 13; race layouts unchanged (severe 22 / 20, soft top 9 / 9, audits 53, W 0, no_route
PASS planned and built, barrier_missing 0, obstruction 0); verify_ai_line PASS (2.544 / 2.386 m); verify_mouths,
verify_fold_fans, verify_signs, rib_check, house_seat_check PASS; the release's own FATAL face check 0 (10 faces held
over by an unreleased corner, each within 2.4 cm, reported); the freeway's 0 vertices over or just under a deck; grass
over a driven lane only at v0.17.1's own five places; criterion 6 within 8 m of the freeway max 0.850 m (17,812 far
vertices, fresh 3DEP); road kn5 126.3 -> 128.3 MB.

### Integration fix round 3 (2026-10-13, v0.18.0, Kevin's decisions + the view lens's three defects): the freeway OFF, the clamp's reach confirmed, the release's teeth and rail caps fixed at their causes

No gate threshold changed and no criterion was re-worded. **Kevin's decisions:** (a) the I-8 freeway that fix round 1 drew
(`tools/author_freeway_blend.py`) is OFF — `scenery.freeway.enabled: false`, his stated default ("terrain only, NO I-8
pavement ribbon"; on the Lariat extra highways "look like wavy ribbons"). Off means `tools/freeway_i8.py` writes no plan
and removes a stale one, so the author step never runs: no slab bed, no batter cut / fill, no held-verge batter; the
I-8 cut is the 3DEP-shaped terrain cut again. Every `freeway_i8` / `author_freeway_blend` row in the fix round 2 table
above is now inert (kept with the tool, its tests and its 3DEP cache; `enabled: true` is the whole switch). (b) The
clamp's reach stays 20 / 40 m (the 0054 D3 subsection above; the two 80 / 250 rows in the 2026-10-11 table are marked
superseded) and LAWS L3's bullet now reads Kevin's principle: near-road relief is shaped to the road within the road's
own construction zone, ~20-40 m; real relief beyond is never reshaped.

**The view lens's three defects, with the freeway gone** (re-rendered from its own viewpoints first): (1) the shark-fin
bank along Alvarado's I-8 side was the freeway's 45 deg batter cut into 5 m facets — gone with it, nothing else needed.
(2) and (3) survived and are fixed in `tools/ground_release_blend.py` / `tools/ground_release.py`:

| Number / rule | Value | Where | Why |
|---|---|---|---|
| span-zone fill read at the nearest pavement point | rule | release batter (2b), span zones only | the grass teeth beside College's south abutment wall: the fill batter's "pavement on the ground" was tested at each sidewalk FACE's centroid, and a 3.5 m face whose centroid stood over the embankment held a vertex 0.8-1.9 m over 3DEP beside a corner of it already 2 m in the air. In a span zone the ground under the pavement is the released real earth, so the gap is now read at the point of the face nearest the vertex (linear over the face, each corner read `GAP_INSET_M` inside it). Bank zones keep the face test: there the ground under the pavement is held (the prep pins it), and a pointwise read over the released creek bank switched the curtain-closing fill off (steep faces in the four 50 m cells beside Alvarado's creek bank 38 -> 367 in a trial) |
| `tools/ground_release_blend.GAP_INSET_M` | 0.4 m [invented] | the span-zone gap | a corner on the pavement's outer edge sits over the released ground beyond it |
| `tools/ground_release_blend.FILL_EASE_M` | 0.25 m [invented] (with `ON_GROUND_M` 1.0) | span-zone fill | the fill starts at the pavement while the gap is under 0.25 m and eases (smoothstep) to the ground under it at 1.0 m, so it fades with the ground where the approach leaves its embankment instead of switching off |
| zone ramp toward the prep's ground | rule | release step 2 | the comb west of College's north approach: the kn5 prep refines a kept cell past 20 m to the data but leaves every zone vertex alone, so a ramp blended toward the graded ground before the prep froze a band 2-4 m over 3DEP between two pieces of 3DEP. A ramp vertex in a kept cell now blends toward the prep's own refined height (engine-july `build_kn5_loop.RefineField`, read from the snapshot; no bytecode written into it) |
| no ramp at a shared station | rule | `ground_release.Zones.weight` | an end that lies inside another zone on the same side does not ramp: Lake Murray Blvd's I-8 span and creek (s 13428) and College's approach foot / south approach / I-8 span each ramped to nothing at the shared station, a dip back toward the built ground between two released pieces |
| release rails per side over the union of the zones | rule | release rails (3) | overlapping zones each drew their own rail over the shared stations: two prisms 3 cm apart whose end caps stood up as white teeth on the parapet (College approach, Lake Murray Blvd creek). One rail per contiguous run of stations now (10 rails, the zone names joined) |
| `tools/ground_release_blend.RAIL_TAPER_M` / `RAIL_END_H_M` | 2.0 m / 0.05 m [invented] | release rails | a free-standing end slopes down over its last 2 m to 5 cm (a sloped end treatment) instead of standing its square Jersey profile up as a pointed white tooth (the College approach rail ending beside the bridge parapet) |

Tried and dropped (measured, not shipped): a zone ramp lengthened to an earth batter's run of its step (3.5 m per m,
4-16 m) raised the constructed bumps beside Alvarado's creek bank (49 -> 62 over 0.6 m) and under Lake Murray Blvd.

Measured on the full rehearsal (fresh scratch workshop, fresh scratch engine-july, no `--skip-blend`), v0.17.1 -> this
build: street drive_test soft top 42 -> 41, severe 0, kinks 3.86 -> 3.41 /km, bumps 0.15 -> 0.0 /km, gated excursions
100 -> 99, floating 391, obstruction 0, daylight 0; street audit D 512 -> 514 (corrected in fix round 4: NOT the release rails, which add 0 D — the same 90 `1WALL_guard`
positions as v0.17.1, two of them on College's deck, now 1.6 m higher at its real height, written as one more duplicate
vertex record each by the kn5 exporter, as the first integration fix round's entry above says),
K 20, I 20, F 13; race_cw / race_acw severe 31 / 28 -> 22 / 20, soft top 9 / 9, audits D 0 K 20 I 20 F 13 W 0, no_route
PASS planned and built (leak 0, 0 / 406), barrier_missing 0, obstruction 0; verify_mouths PASS x4, verify_fold_fans PASS,
verify_ai_line PASS (2.544 / 2.386 m), verify_kn5 + --inis, check_race_kn5, verify_race, verify_signs (23 posts),
rib_check, house_seat_check PASS. Release: batter cut 412 / fill 446; steep faces (> 60 deg, > 0.5 m) within 12 m of a
pavement 786 -> 549 (439 -> 329 not under a deck). Teeth (a terrain vertex > 0.6 m over the mean of its neighbours and
not 3DEP's own): within 20 m of College's south abutment 5 -> 0; within 25 m of the comb west of the north approach 18 -> 7 (the refuted build -> this one). Road kn5 92,502,895 B
(v0.17.1) -> 116,011,770 B (128,277,872 with the freeway).

### Integration fix round 4 (2026-10-14, v0.18.0, after the gates, runtime and view lenses refuted round 3): rails over every drop, the pit under College's sidewalk lifted, the straight bank, coincident faces, the lamp lenses

No gate threshold changed and no criterion was re-worded. **Corrected:** round 3's "D 512 -> 514 (the release rails)" was
wrong — the release rails add 0 D (fixed in the round 3 text above).

| Number / rule | Value | Where | Why |
|---|---|---|---|
| a rail stands full height over every station that needs it | rule (`tools/ground_release.rail_heights`) | release rails | the gates lens: round 3's sloped ends (to 5 cm over 2 m) stood over live drops wherever a run's padding was clipped by a zone or block end — College Ave's approach foot, s 2500-2502, 4.9 m down; beside College's deck; Lake Murray Blvd. drive_test credits any 1WALL as a guard whatever its height, so the gates could not see it. A slope is built only over padding past the last station over a drop |
| `tools/ground_release.RAIL_HOLD_M` | 1.0 m [invented] | release rails | full height at least this far past the first / last station over a drop |
| `tools/ground_release.RAIL_TAPER_MIN_M` | 0.5 m [invented] | release rails | a sloped end shorter than this is not built: the end stays square |
| rail stations past a zone's end | rule | release rails | the gates lens: at College's approach foot (s 2496-2500) a 3-5 m curtain off the sidewalk had no rail because the stations stopped at the zone; the same embankment edge, College 4-6 m over Alvarado, ran unguarded back to s ~2401 since v0.17.1. From every zone end not inside another zone on that side, stations continue outward while the drop does |
| `tools/ground_release_blend.RAIL_EXT_FALL_M` | 1.0 m [invented] | the outward stations | past a zone only a real embankment edge carries the rail on: a steep fall (drive_test's 0.12 m per 0.5 m) AND the ground more than this under the edge (the zone rule's 0.5 m fall alone fenced ordinary street verges, 120 m runs in a trial) |
| `tools/ground_release_blend.RAIL_EXT_MAX_M` | 120 m [invented] | the outward stations | at most this far past a zone end |
| a pit under the pavement in a bank zone lifted to it | rule | release step 2 + the per-face cap | the view lens's stepped curtain under College's south approach: the draft seats that ground at Alvarado's level, 6 m under College's sidewalk; the prep pins ground under a deck only to a sheet within its window of the vertex's own height and leaves zone vertices alone otherwise, so it stayed a pit under the sidewalk, sawn against the released bank beside it. A held vertex more than `HELD_PIT_M` under its lowest upward ROAD / CURB sheet is lifted to it, and its faces are capped with the released ones (a lifted corner under a curb top must not stand over the gutter beside it). Lifting EVERY held vertex was tried on this round's second rehearsal and dropped: the ground under a curb top stood 0.13 m over the gutter, street soft top 42 -> 211 |
| `tools/ground_release_blend.HELD_PIT_M` | 1.0 m [invented] | release step 2 | deeper than this under its sheet is a pit; shallower, the seat's height under the pavement stands, as in v0.17.1 |
| the straight bank between two pavements | rule (`tools/ground_release.batter_z`) | release batter (2b) | where a fill from a high pavement and a cut from a low one cannot both hold (College's sidewalk 5-6 m over Alvarado's, 2-3 m apart) "the cut wins" left a vertical curtain under the high one. There the ground is the straight bank between the two edges, by distance |
| `tools/ground_release.STRAIGHT_BANK_MIN_M` | 1.0 m [invented] | the straight bank | only between pavements this far apart in height; below it (one road's own grade) the cut still wins |
| zone `college_approach_foot` from s 2410 (was 2500) | config | track.config.json | the embankment edge first falls over 1 m at s 2410; the old start at s 2500 put the boundary between released and held ground in the middle of the curtain the view lens saw from Alvarado (209 3DEP nodes fetched, TLS verified, cached with provenance) |
| zone `college_north_approach` s 2690-2745, bank, both sides | config | track.config.json | the view lens's fins 20-50 m west of College's north approach: `college_i8_span` ended at s 2690 and ramped over 4 m back to a verge fresh 3DEP reads 1.3-3.3 m over the real earth; the 1.25 m lattice sampled the ramp as teeth. The zones abut (no ramp at s 2690); 1,266 3DEP nodes fetched |
| release halving by PLAN length | rule | release step 1 | the runtime lens's zero-length normals: a vertical edge of the seat's curtain (two vertices on one plan point) was halved round after round, stacking up to 31 coincident faces back to back |
| coincident faces / vertices removed | rule | release; `tools/triangulate_terrain_blend.SLIVER_M2` 0.01 m2 [invented] | faces on one vertex set: a sliver group goes, a real face keeps one copy; coincident vertices welded (1e-4 m) after the release. In the triangulation, a quad with a T-vertex on its diagonal split into a zero-area sliver, its neighbour into the same sliver reversed: groups under 0.01 m2 removed, with a vertex left with no face (no vertex moves) |
| engine-july prep: LIGHTS do not ride the terrain delta | rule (snapshot `build_kn5_loop.py`, pending mirror) | kn5 prep re-seat | the runtime lens: a lamp's lens marker moved by the ground change under its arm while its LIGHTPOST stayed (LIGHT_123 on Lake Murray Blvd's I-8 deck 0.68 m over its own plate, LIGHT_122 0.15 m) — the head shadowed its own pool |
| `scripts/ac/ext_config.py` GRASS_NIGHT includes `GRASS_FAR` | rule | ext_config | the far ring kept its day ksDiffuse 0.22 at night beside the near grass's 0.14 |
| the release rails are their own physical mesh `1WALL_guard_release` | rule | release rails | found on this round's first rehearsal: appended to GUARDRAIL, the longer rails took the prep's 1WALL_guard past the kn5 exporter's 65,536-vertex mesh cap; the exporter wrote two meshes of one name and verify_kn5 stopped the chain ("DUPLICATE physical mesh '1WALL_guard' x2 — AC drops dup-named meshes from collision"). The name keeps the 1WALL_GUARD material row and the WALL surface (prefix match) |
| `tools/ground_release_blend.RAIL_CHUNK_TRIS` | 18,000 [invented] | release rails | triangles per rail mesh before a second one (`1WALL_guard_release_<k>`): 3 exporter vertices per triangle at worst stays under the cap |

**Not changed, named instead (both still worse than v0.17.1 on paper; `--force-install` would assert otherwise). Both fixed in round 5 below.**
(a) Street audit D 512 -> 514: the same 90 `1WALL_guard` positions as v0.17.1; at two of them on College's deck, now
1.6 m higher at its real height, the kn5 exporter writes one more duplicate vertex record each (it dedups corners by
exact float normal equality, and the slope changed the rounding). No wall moved onto the road. (b) race bumps / km
7.42 / 10.24 -> 7.72 / 10.39: drive_test's own per-station steps (re-run read-only) put the net +4 / +2 at two places —
cw s 4539-4549 (acw s 8933-8943), the inside of the levelled fold pinch at (-1961, 593) (ledger 0050, rows 1508-1516),
where v0.17.1 had grass standing on the road in the lane (12 / 11 of its 23 / 22 soft-top hits are those stations): the
wheel paths now read the pinch's road fan, 2.5-6 cm second differences; and cw s 6946-6969, the Navajo / Jackson riser
ledger 0050 levelled, its 0.39 m severe steps now 3-6 cm bumps. Steps over 2.5 cm in all (bumps + severe): 131 -> 126
(cw), 166 -> 160 (acw).

Measured on the final rehearsal (fresh scratch workshop, fresh scratch engine-july with the pending prep change, no
`--skip-blend`), v0.17.1 -> this build: street drive_test soft top 42 -> 33, severe 0, kinks 3.86 -> 3.41 /km, bumps
0.15 -> 0.0, excursions 100 -> 98, floating 391, obstruction 0, daylight 0; street audit D 512 -> 514 (above), K 20, I 20,
F 13; race_cw / race_acw severe 31 / 28 -> 22 / 20, soft top 23 / 22 -> 9 / 9, kinks 6.45 / 7.57 -> 6.23 / 7.05, bumps
(above), audits D 0 K 20 I 20 F 13 W 0, no_route planned 139,130 / 138,826 m2 and built 139,148 / 138,847 m2 PASS
(leak 0, 0 / 406), barrier_missing 0, obstruction 0; verify_mouths x4, verify_fold_fans, verify_ai_line (2.544 /
2.386 m), verify_kn5 + --inis, check_race_kn5, verify_race (+ scenery), verify_signs (23 posts), rib_check,
house_seat_check PASS. Release: 327 pits under the pavement lifted, batter cut 460 / fill 604 / straight bank 115,
2,732 coincident faces removed and 961 coincident vertices welded (0 coincident face sets left in TERRAIN, round 3 448);
10 rails, 0 rail vertices on a road, College's approach foot railed from s 2388 (the stations past a zone end: 19 over a
drop). Steep faces (over 60 deg, over 0.5 m) within 12 m of a pavement in the zones 549 -> 849: the two zones added and
the straight banks (a 60-70 deg bank where the two sidewalks stand 2-3 m apart) — counted, not hidden.

### Integration fix round 5 (2026-10-14, v0.18.0, after the gates lens refuted round 4): the deck rails off the pavement, drive_test's fold bumps

The gates lens refuted round 4 on two metrics worse than v0.17.1: street audit D 512 -> 514 (over the floor `ship_sd.sh`
prints) and race bumps / km 7.42 / 10.24 -> 7.72 / 10.39. Both are now fixed at their causes; every other gate is as in
round 4.

| Change | Value | Where | Why |
|---|---|---|---|
| the I-8 deck guardrails stand 0.15 m outside the pavement edge | `GUARDRAIL_SET_M` 0.15 m [invented] | `tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.build_guardrails` | D counts a 1WALL vertex lying on a carriageway triangle within 1.2 m of it. Every one of the 90 panel positions on College Ave's and Lake Murray Blvd's decks was built ON the road's edge line (`hw`), so all of them lay on the road's own boundary: v0.17.1's 512 was those 90 positions x 5-6 kn5 vertex records, and round 4's 514 was the same 90 with two more exporter duplicates where College's deck now has its real slope (the exporter dedups corners by exact float normal). A bridge barrier stands on the curb behind the gutter line, not on the pavement: 0.15 m puts each panel on the curb top, its foot still inside the curb. Street D 514 -> **0**; E 0 (the foot is in the curb); the release rails' "already held" test (a GUARDRAIL between the lane and the lip) reads the same |
| the street audit's printed regression floor | D 512 -> **0** (K 20 / I 20 / F 13 unchanged) | `tools/ship_sd.sh` step header, `tracks/san-diego-lake-murray/ship.json` `audit_note` | tightened to what the build now measures |
| FOLD BUMPS: a 2.5-6 cm second difference over a metre where the fixed-offset wheel-path point runs backwards is reported (`fold_bumps`), not counted in `steps_per_km` | rule; `_advance` < 0 on the metre or the metre before it | `scripts/geometry/drive_test.py` (every track, every layout) | criterion re-worded where fresh 3DEP fails it too (evidence below). drive_test's wheel paths are fixed lateral offsets; round a corner tighter than the offset (Lake Murray's fold fans: centre radii 7-8 m under race lanes 9-13 m wide) the point lies past the turning centre and hops 1-2.5 m to and fro across the fan, so its 1 m second difference re-traces the plan, not a step under a tyre. A SEVERE step (> 6 cm) on such a sample still counts (ledger 0050's 0.37 m Navajo / Jackson lip was read on one); kinks are unchanged; the levelled fans' real wheel paths stay judged by `tools/verify_fold_fans.py` |

**Evidence for the re-wording (fresh USGS 3DEP 1 m, TLS verified through `scripts.tls`, 10,125 points on 45 x 45 m grids
round the five Lake Murray fans: the hairpin, College / Navajo, Navajo / Jackson, the seam, the east corner at (2603,
516)).** The least-squares plane of the real ground within 15 m of each fan (grades 7.0 / 5.5 / 3.0 / 1.4 / 3.2 %), the
smoothest surface the real corner can have, read through drive_test's OWN sample positions (the race_cw and race_acw
paths, logged from the build): of 158 backward samples per layout, 76 / 74 read a bump and 34 / 35 a severe step — the
real ground's plane fails the bump rule there half the time. The raw 3DEP reads 62 / 60 bumps on them. (Forward samples
also read some bumps on the plane — 163 of 2,742 — from the stations' changing spacing round a corner; those are not
exempted: the rule is only the backwards case.)

**The same rule on both builds** (drive_test re-run read-only on v0.17.1's installed gate OBJs, `k10-sd-v021/project`,
output redirected; nothing written there): race_cw bumps 100 -> 65 counted + 35 fold (v0.17.1), 104 -> 59 + 45 (this
build); race_acw 138 -> 97 + 41, 140 -> 91 + 49; street 2 + 20, 0 + 20. On the samples a wheel can drive, this build has
fewer bumps than v0.17.1 on every layout (65 -> 59, 97 -> 91, 2 -> 0); all of round 4's increase was in backward samples
(35 -> 45, 41 -> 49), the College / Navajo and Navajo / Jackson fans whose grass-over-road and 0.39 m risers this
branch removed.

Measured on this round's full rehearsal (fresh scratch workshop, fresh scratch engine-july with the pending prep files,
no `--skip-blend`, `ship_r5.log`), v0.17.1 (as gated then) -> this build: street drive_test soft top 42 -> 33, severe 0,
bumps 0.15 -> 0.0 /km (fold 20), kinks 3.86 -> 3.41, excursions 100 -> 98, floating 391, obstruction 0, daylight 0;
street audit **D 512 -> 0**, K 20, I 20, F 13, E 0; race_cw / race_acw severe 31 / 28 -> 22 / 20, soft top 23 / 22 -> 9 /
9, **bumps 7.42 / 10.24 -> 4.38 / 6.75 /km** (fold 45 / 49; v0.17.1 under the same rule 4.82 / 7.20), kinks 6.45 / 7.57
-> 6.23 / 7.05, barrier_missing 0, obstruction 0; race audits D 0 K 20 I 20 F 13 W 0; no_route planned 139,130 / 138,826
m2 and built 139,148 / 138,847 m2 PASS (leak 0, 0 / 406); verify_mouths x4, verify_fold_fans (3 x 3), verify_ai_line
(2.544 / 2.386 m), verify_kn5 + --inis, check_race_kn5, verify_race (+ scenery), verify_signs (23 posts), rib_check,
house_seat_check PASS. The terrain is round 4's but for 344 of 928,435 triangles beside the two decks, moved at most
0.024 m.

## 2026-10-12 — Lariat Drive-1 build: the Drive-1 verdict, the D4 variant per run (ledger 0048; from branch 793441f, carried onto main 2026-11-01 — the two chain steps it also added are not taken, see below)

The integration of the three P2 parts (data stages, underlay, Drive-1 gates) into one Drive-1 chain
(`tracks/lookout-lariat/ship.json`). Every value below is P5's own, carried with P5's tag; the one new value is the
lid-end window. San Diego's chain is untouched: none of these steps is in its ship.json, the D4 helpers are no-ops
without `SHIP_VARIANT` or `drive1_variants`, and `tests/tools/test_ship_track_chain.py`'s SD parity tests pass.

### The Drive-1 verdict (new: `tools/drive1_gates.py`, step `drive1_verdict`, thresholds in `track.config.json gates.drive1`)

| Row | Threshold | Flag |
|---|---|---|
| drive_test per street layout: soft-top in lane, obstruction, floating furniture, undrivable corners, daylight gaps | 0 each | [std: drive_test's existing count gates] |
| drive_test: severe steps (≥ 6 cm) | **0** per layout | ⚠ [invented] (P5; drive_test's own line is > 12/km) |
| drive_test: replication of the built road vs raw 3DEP | p95 ≤ **0.5 m**; not measured = red | ⚠ [invented in 0048] |
| drive_test: kinks/km | ≤ `gates.drive_test.kinks_per_km_max` (19.49) | [std: MEASURED §8] (the gates part's entry above) |
| drive_test: unguarded drops, far ledges, bumps/km, drive_test's own `fail` | recorded, not gating | P5 "recorded, not gating" (Drive 1 builds no edges) |
| audit_mesh (street): A B D E G H I | 0 each | [std: audit_mesh's existing hard total] |
| audit_mesh: F (curb not flush) | ≤ **15** | ⚠ [invented: Lake Murray V3's own count] (the street audit's own exit still gates F at 0 in ship_track.sh) |
| kn5_ground_check | its own verdict (road over ground p95 ≤ 0.10 m [std]) | existing |
| the lid: a severe step within **5 m** of either end of `capture.bridges` (each layout's own stations; reverse = lap − s) | ≤ **0.10 m** | 0.10 m ⚠ [invented in 0048]; the 5 m window ⚠ [invented] 2026-10-12 |
| one-way, hairpin / paint, roll rate | the draft's own hard verdicts, re-read | existing (P0, P2) |
| road inventory, stacked legs | their own verdicts | the gates part's entry above |
| tier seams | n/a until P3a's tiers (GEN_terrain is the one-sheet placeholder) — never a pass | — |
| verify_edges, verify_signs, TreeFX, sightline_check, race gates | recorded: Drive 2 / Drive 3 | P5 |

A gating row whose report is missing is red ("not run"), never a pass. `--force-install` (P5, 0047): the verdict's
`force_install_ok` is false when any street layout is worse than the July reference on any key
(`gates.drive1.july_reference`: severe 253, kinks 68.3/km, drops 738, far ledges 382 [measured on v0.46.0]) or not 0
on obstruction / floating furniture / soft-top; `tools/ship_track.sh` then refuses the forced install (before, the
Drive-1 road gates passed `--force-install` on the caller's word alone).

Proof: `tests/tools/test_drive1_gates.py` (7): all-green passes and the recorded rows never gate (drive_test's own
`fail` from drops does not make its Drive-1 row red); each threshold flips exactly its own row (severe 1, p95 0.51,
p95 absent, kinks 19.5 > 19.49, daylight, undrivable, B 3, F 16, kn5_ground_check FAIL, road inventory, stacked legs,
roll rate, paint, one-way); the lid's ends in forward and reverse stations; every missing report is red; the July
comparison key by key and the always-0 trio; input errors exit 2; the Lariat's declared values.

### Not carried onto main (2026-11-01): the kn5-internal `kn5_ground_check` step and `split_street`

Main's chain runs `kn5_ground` as the last gate on the kn5 set each layout loads (`data/kn5_ground_check.<id>.json`,
EXPANSION-PLAN V5), and its split handles a single layout since 2026-10-29 (the entry above "the split's
single-layout rule"); `tools/ship_track_spec.py` keeps `prep = [prep, split]`. The verdict reads the per-layout JSON.

### The D4 variant per run (`SHIP_VARIANT`)

`SHIP_VARIANT=<drive1_variants id>`: checked before anything is touched (exit 2), applied to the install folder and
installed name (`drive1_variants.<id>.install_folder` / `ui_name_prefix`), and never synced back. No threshold. *On
main (2026-11-01) the branch's `--variant` to its own underlay becomes `road_profile.verge_m` written into the workshop
config, which `build_mesh` reads (the entry of 2026-11-01 below); the guard is that a variant run drafts in full
(`--skip-blend` and `--from` refused), so no `loop.blend` drafted for the other edge is ever prepped.*

### Measured on the first Drive-1 build (scratch, not installed; ledger 0048 "P2 integrated")

D4 A / D4 B, Full / Reverse:
- **Green:** kn5_ground_check p95 0.038 m; audit CLEAN; road inventory PASS (0 forbidden meshes, 0 of 57,776
  pavement triangles off the route, 100.0 % paved); replication p95 0.04 m; kinks 6.8-7.0 /km; roll rate, paint and
  one-way PASS.
- **Red:**
  - severe steps 40-53 (all at C12 / C13 / C14 / C18 / the lid's east end);
  - soft-top 395-412 (ground above the lane: p50 5 mm, max 0.21 m at C13);
  - undrivable corners 83, i.e. the real hairpins C4-C10 and C13 at their measured 6.8-8.3 m;
  - the lid's east end 0.17 m;
  - stacked legs 137 / 144 (placeholder ground).
- `force_install_ok` is false (far ledges 923-947 > July 382; soft-top must be 0). No threshold was moved to change
  any of this.

## 2026-10-12 — Lariat P2 data stages: the roll-rate gate, footprint crossfall, measured widths, the profile by station, the declared lid, L13 for the span detectors (ledger 0048)

The Lariat's draft now runs `elev -> road_profile -> project -> widths -> measured_widths -> crossfall ->
verify_crossfall` (`tracks/lookout-lariat/ship.json`, one appended block of step functions in
`tools/ship_track.sh`). Every engine change is opt-in or provably inert for other tracks (proof list below).

| Gate / guard | Before | After | Flag |
|---|---|---|---|
| **roll rate (a)** (new, `tools/verify_crossfall.py`, hard in the Lariat draft) | — | on EACH half of the section (`left_pct`, `right_pct`; a legacy file is read as one plane), the tilt changes by **<= 4 %** between any two stations within **30 m**, the seam wrapped (L13) | ⚠ invented (V3-PLAN P5) |
| **roll rate (b)** (new) | — | no swing from **>= +3 %** to **<= -3 %** (or back) within **30 m**: 0 | ⚠ invented (V3-PLAN P5) |
| crossfall file honesty (new, same tool) | — | a `status` (`estimated` until a 3DEP source-lidar sample agrees), stations ascending in [0, lap), no gap over two steps, the seam included | a record check, no number |
| crossfall method (`scripts/elevation/crossfall.py`, opt-in `road_profile.crossfall.method = "footprint"`) | `build`: a 3DEP pair 0.6 m inside each pavement edge every 2nd vertex (geojson stations), deadband 1.5 %, cap 6 %, median 9 + mean 5 vertices | `build_footprint` (local stations): 5 samples across the real-width footprint, the outermost **1.0 m** inside each edge (one 3DEP cell), every **3 m**; plane tilt by least squares; ground at **2 / 5 / 8 m** beyond each edge only to classify **bench** (one side rises **>= 1.0 m** above the road centre while the other rises **< 0.5 m**) vs crown, runs under **30 m** joined; measurement smoothed by a **30 m** median + **15 m** mean (length-weighted); kept only where **>= 2 %**, **<= 6 %**, not tilting INTO a curve tighter than **R 100 m** by more than 2 %, off a declared deck, outside **+-30 m** of a roll-rate failure of the measured series itself, and in a kept run **>= 30 m**; everything else the construction standard (**2 %** crown, or **2 %** toward the cut ditch on a bench); every change ramped at **0.12 % per metre** (the mean of the Lipschitz minorant and majorant: 3.6 % per 30 m, so the file passes (a) and (b) by construction) | 2 % is [std: docs/ROAD-CONSTRUCTION.md "Drainage"]; 6 % is the legacy cap's value; every other number ⚠ invented. `build` is byte-identical for every track that does not opt in (no track in airoso has a `crossfall.json`) |
| measured widths (`scripts/gps/measured_widths.py`, new, opt-in by the ship step) | `widths_from_osm`: OSM lanes table, junction flares, hard-corner flares (>= 14 m), a **10 m** floor on every fold over 110°; geojson-indexed widths written 1:1 into the local ring | measured (aerial) > published (`width_overrides.width_m`) > OSM table, per top-level `width_overrides` stretch (touching measured stretches interpolate as one), measured = edge-line centre-to-centre **+ 0.10 m** (one stripe) or, on a town street with no edge lines, curb-to-curb; no flares, no fold floor; rotated into the local frame; changes rate-limited at **0.25 m/m** round the closed lap | 0.10 m [std: MUTCD 3A.05 normal line 4-6 in]; 0.25 m/m is `projection.slew_limit_widths`'s existing rate, now applied cyclically (L13). `widths_from_osm` itself is untouched |
| road profile (`scripts/elevation/road_profile.py`, new, after heightfield) | heightfield's windows counted in vertices, sized for 3 m (on the Lariat's 1 m climb: an 11 m median, a 3 m mean, a 48 %-per-metre effective grade cap) | the same 33 m median, 9 m mean and cut-only grade cap, in METRES: windows by station, filters weighted by each vertex's length of road, the cap per real segment (L3) | no threshold moves. Proven equal to `heightfield.snap_to_ground` on uniform 3 m lines (open and closed); `heightfield.py` untouched |
| declared deck (`bridges.declared`, new) | July: the height detector's spans | the 19th St lid from its OSM tunnel footprint (ways 533503591 + 533679737, each buffered by half its pavement width) plus **8 m** abutments each side, held straight in the raw profile before smoothing; recorded as `capture.bridges` (local stations) | 8 m ⚠ invented (copies the prep's `BRIDGE_PAD_M`) |
| span seam rule, `build_mesh._bridge_detector` | a run of high stations reaching the closing vertex became a span (July's 525 m [24,278-24,803]) | opt-in `bridges.l13_seam_rule`: on a closed lap such a run is dropped unless vertex 0 is also high (it continues from vertex 0) | [std: L13]. Off by default: every other track's detector output is unchanged |
| span seam rule, `build_kn5_loop.detect_bridge_spans` (the prep) | the last span ran `pad_m` past the lap's end; vertex 0's pad was cut at 0 | spans and pads wrap at the seam, clamped to [0, lap]; a span reaching the closing vertex always continues from vertex 0; open roads unchanged | [std: L13]. No shipping track preps with this file |
| drive_test replication | `z_raw_m` (per geojson vertex) paired by index with the local ring | `z_raw_local_m` when present (written by `road_profile`: the same samples in the local index space), else `z_raw_m` as before | a frame fix, no number. On the Lariat the ring is rotated by 2 vertices (2-6 m along a climb of up to 10 %) |

Proof:
- `tests/elevation/test_road_profile.py` (10): equal to heightfield on uniform 3 m lines (open, closed); windows of
  33 / 9 samples at 1 m; mixed 1 m / 3 m spacing leaves an 8 % ramp within 0.13 m (by vertex count: > 0.5 m off);
  a closed lap's filters are rotation-invariant; the cap per real segment; a deck from a footprint, held straight
  over a 6 m trench; a deck across the seam refused; `build --write` writes `capture.bridges` in local stations and
  `z_raw_local_m` rotated by projection's k.
- `tests/elevation/test_crossfall_footprint.py` (6): legacy `build` output byte-identical to airoso a0557e0's file;
  CLI dispatch; the two roll-rate rules incl. across the seam; plane / crown fit; on a synthetic lap a flat road on
  a bench takes -2 / -2 toward the cut (raw tilt < 0.01 %: the beside-the-road samples never enter a tilt), an
  outsloped 4 % road keeps its measurement, flat ground the crown, a deck the standard, and the result passes.
- `tests/gps/test_measured_widths.py` (4), `tests/geometry/test_bridge_seam.py` (6),
  `tests/geometry/test_drive_test_raw_local.py` (1), `tests/tools/test_ship_track_chain.py` (+1).

On the Lariat (clean scratch run, 3DEP and Overpass fetched live, TLS verified): see ledger 0048 "P2, the data
stages" for the numbers. The roll-rate gate PASSES on the written file (worst 3.4 % / 30 m, 0 swings); on the raw
in-footprint measurement it would fail at 1,836 stations with 36 swings, and on the smoothed measurement at 1,030
with 18: the measurement alone is not a road surface, which is why the file is "estimated" and mostly standard.

## 2026-10-12 — Lariat Drive-1 gates that do not wait for the terrain: road inventory, stacked legs, the kink ceiling (ledger 0048)

V3-PLAN P5's Drive-1 set, the three parts that do not depend on the tiered terrain (ledger 0046's job). All three
judge the BUILT artifact (L5): the gate OBJ `scripts.modkit.kn5_to_gate_obj` writes from the shipped kn5, walked
along drive_test's own line (`gate_centerline.json` > `finished_centerline.json` > `centerline.local.json`,
`tools/gate_route.py`). None has run on a Lariat build yet: there is none (the underlay, P2 step 3, is not written).

### Road inventory (new: `tools/verify_road_inventory.py`; a separate tool, not a `verify_kn5` section, while the terrain job holds `scripts/ac/verify_kn5.py`)

| Check | Threshold | Flag |
|---|---|---|
| `HIGHWAY*` / `HWYSTRUCT*` / `MOUNTAINS*` groups, with or without a `<digits><KEY>_` prefix | 0 | [std: Kevin's "no extra highways", 0048; MOUNTAINS: L1 as 0046 applies it to the sine ridge] |
| pavement off the route: every triangle of a pavement group (prefixes from the exemption file; the Lariat's `1ROAD`, `AUTH_OVERPASS`) at its 3 vertices and centroid, each within the route's lerped half-width **+ 2.0 m** or inside a declared exemption polygon | 0 triangles | ⚠ 2.0 m [invented] (the plan's number) |
| exemptions: `tracks/lookout-lariat/pavement_exemptions.json`, each naming the `AUTH_*` object it covers; `footprint` or `name_and_footprint` (the C-470 decks); lon/lat or OBJ-frame polygons | an entry with no polygon exempts NOTHING (listed as unmeasured); `active: false` (D2 b's route: Kevin chose D2 a) exempts nothing | not a bypass: today all 19 active entries are unmeasured, so nothing off the route is exempt until its object is authored and its polygon drawn |
| the pavement is the lap: each layout's line walked at 1 m, pavement under it within drive_test's deck window (±2.5 m, its existing `top_at` window), share of the lap paved | ≥ 99 % (within 1 %) | ⚠ 1 % [invented] (the plan's number) |

Exit 1 on any fail, 2 on an input error (no OBJ, no line, a malformed exemption file: an object not `AUTH_*`, a
duplicate id, an unknown match). Proof: `tests/tools/test_verify_road_inventory.py` (10): a clean road passes and is
100 % paved; each forbidden name fails, prefixed or not, and look-alikes (`GRASS_mountain`, `AUTH_overpass_*`) do
not; a slab 1.5 m past the edge passes and 2.5 m fails (beyond 0.5 m reported); a lot passes only inside its
polygon (OBJ frame or lon/lat), a half-covering polygon still fails; unmeasured and inactive exemptions exempt
nothing; `name_and_footprint` exempts only its own group; a 10 m hole in 200 m fails, a 1 m hole passes; the
`--kn5` path decodes a real kn5 to the same answer; the Lariat file declares the plan's whole list.

### Stacked legs (new: `tools/verify_stacked_legs.py`, rule L4)

| Check | Threshold | Flag |
|---|---|---|
| pair: two lap points (1 m) < **40 m** apart in plan and > **150 m** apart along the lap (cyclic) | — | ⚠ both [invented] (the plan's numbers) |
| a ground / edge / sign / closure vertex at a pair (its own leg = the plan-nearest lap point, which has a partner; the other leg = the nearest lap point > 150 m along, within 40 m of the vertex and of its own point) sits closer in height to the other leg's BUILT road (the highest 1ROAD within ±2.5 m of the line) than to its own | **0** | ⚠ [invented] (the plan's number) |
| a stacked lap point with no built road under it (cannot be judged) | 0 | new, a failure, never a skip |
| crossings: where two lap segments > 150 m apart along the lap intersect in plan, vertices whose own and other point are both within **40 m** (along the lap) of the crossing are not judged (plan-nearest names neither road there); counted (`crossing_skipped`) and the crossing listed | — | ⚠ 40 m [invented] 2026-10-12. On the Lariat's paint line there is **no crossing**, so it skips nothing |

Classes are group-name prefixes (closure first, so a `1WALL_closure` is a closure; the road is never tested);
`track.config.json gates.stacked_legs.classes` can override them. `--line-only` measures pairs on the line's own
heights and never passes (exit 0, `fail: null`).

Measured (the plan's "the count is re-measured and recorded on the V3 line"), on 1 m resamples, heights from July's
3DEP corridor samples (`data/source-july/corridor.elev.json`, IDW): the **paint centreline** has **10,659 pairs on
680 lap points** in 12 stacked runs (st 2,493–3,152, Tiers of Zion; st 5,305–5,996, the upper hairpins), nearest
**21.3 m** in plan, vertical gap **6.49–14.90 m (median 9.98 m)**, no crossing. The same tool on the July line:
10,614 pairs, nearest 20.48 m, 6.51–14.85 m (median 10.09 m), no crossing — the plan's July figures (1,188 pairs on
its 3 m line ≈ 10,614 / 9; 6.5–14.7 m, median 10.1 m, nearest 20.5 m) reproduce, so the definition is the plan's.

Proof: `tests/tools/test_verify_stacked_legs.py` (8), on a synthetic 850 m switchback (legs 25 m apart, 10 m
apart in height) and a figure of eight on a 7 m bridge: vertices beside their own leg pass; one beside leg A at leg
B's height fails in every class (ground, `GEN_terrain`, `AUTH_cut`, edge, sign, closure) with its two stations; a
vertex outside the stacked stretch (46.9 < z < 353.1, derived in the test) is never judged; a 20 m hole in the road
under a stacked stretch fails; line-only reports nearest 25 m and gap 10 m and never passes; the bridge is
reported at st 150 / 750 and its 6 footprint vertices skipped; a config class override works; no road / no OBJ is
exit 2.

### The kink ceiling (drive_test, opt-in per track; the Lariat's value)

| Threshold | Before | After | Flag |
|---|---|---|---|
| kinks/km (slope change > 3 %-points per 1 m on the six interior paths) | reported, never gating (every track) | gates only where `track.config.json gates.drive_test.kinks_per_km_max` is declared; the report then carries `kinks_per_km_max` | wiring |
| the Lariat's ceiling | V3-PLAN P5: ≤ 5/km [invented: Lake Murray V3's own 4.97/km] | **≤ 19.49/km** | [std: measured on reference mountain roads] |

The calibration (`tools/calibrate_kinks.py`; `fleet/reference/MEASURED.md` §8; raw rows
`fleet/reference/raw/kinks_*.json`): drive_test itself, run on each reference's physics road (read only) along its
AI line moved to the lane centre — simtraxx Pikes Peak pp100ahc **19.49/km** (20.0 km, a coarse 2.75 m physics
mesh), la_canyons mt_wilson_hillclimb **0.73** (6.8 km), simtraxx Targa Florio stage 1 **0.49** (14.2 km),
la_canyons angeles_crest_east **0.00** (40.9 km). The ceiling is the kinkiest reference: a looser bar than the
plan's invented 5, and the reason is written down: the dense (scan-class) references read 0–0.73, the coarse one
19.5, so the metric reads mesh creases as much as road. July read 68.3/km (v0.46.0) and 108.9/km (v0.66.3). The
scan-class alternative (0.73/km, also [std]) is recorded in MEASURED §8 for after Drive 1.

Every other track: byte-identical. No other config declares `gates`; the key is read once, after every existing
gate decided, and adds to the report only when present. Proof: `tests/tools/test_calibrate_kinks.py::
test_drive_test_kink_ceiling_is_opt_in_per_track` (no key: no ceiling key and kinks never fail the run; a tight
ceiling fails it; a loose one passes with a report equal key for key to the no-key report but for the ceiling),
and a one-off parity run of HEAD's (a0557e0) drive_test against this one on the suite's straight and wall fixtures,
the kink fixture and the real mt_wilson reference project: `drive_test.json` md5-identical on all four.

### `scripts/modkit/extract_kn5.parse(keep=, textures=)` (no threshold)

Two keyword arguments, both defaulting to today's full decode: `keep` steps over the vertex and index bytes of a
mesh it rejects; `textures=False` steps over the blobs. Parity: `parse()` of la_canyons `main_roads.kn5` (196
meshes, 11 textures) and Targa Florio `wall.kn5` (160 meshes) equals HEAD's `parse()` exactly; `keep=` equals the
full parse filtered; `tests/tools/test_calibrate_kinks.py::test_parse_keep_returns_exactly_the_kept_meshes`.

### Wiring (`tools/ship_track.sh`, Lariat only)

`gate_road_inventory` and `gate_stacked_legs`, one marked block after the existing vocabulary; the Lariat's
`ship.json` runs them after `road_obj` (the built gate OBJ), syncs `pavement_exemptions.json` in and both reports
out. Exits collect in `D1_G`; red stops the install, and `--force-install` passes it exactly as it passes a red
street drive_test / audit (the caller asserts no metric is worse than the reference). San Diego's `ship.json`
names neither. Proof: `tests/tools/test_ship_track_drive1_gates.py` (4); `tests/tools/test_ship_track_chain.py`
(19) unchanged and passing.

## 2026-10-12 — `verify_signs` (k) direction coverage, (j) read from signs.json, race furniture never the signs' ground (ledger 0051)

**Why.** Kevin, from the seat: "arrow signs are only placed for one direction of driving". All signs ship in the one
road kn5 that all three layouts load, and every mainline plate faced the clockwise approach. race_acw drives the lap
anticlockwise, and `verify_signs` passed v0.17.1 anyway, because no check read which directions are driven.

No numeric threshold is added or moved. Every number below is an existing rule constant.

| Check | Before | After | Flag |
|---|---|---|---|
| (k) direction coverage (new) | — | Driven directions come from `<project>/track.config.json` `layouts[].direction` (forward → fwd, reverse → rev; absent or null = forward; any other word FAILs). Every MAINLINE corner with a plate in one driven direction needs, in every other driven direction, either a plate or a skip record EVERY one of whose reasons is the rule finding no arrow corner on that approach (`RULE_SKIP_RES`: R_apex, \|D\|, mouth flare, or the ray never leaving pavement / leaving it out of range / ending at a T / landing outside [PC, PT]) or a signs.json skip with a non-empty reason that signs.json itself still makes for that approach. FAIL: a skip caused by `expect_arrow`; a placement that failed (OUTSIDE ASSERTION, base ON pavement, obstacle disc, lamp clearance: the rule wanted an arrow there); a reasonless signs.json skip; a direction with no record at all. `place_signs` also refuses a signs.json `skip` with no reason at load. | no number |
| (j) expect_arrow | compared the record's own `expect_arrow` with its arrow | Re-read from signs.json here (`--signs`, else `tracks/<slug>/signs.json`). The entry names the FORWARD approach, so a -rev plate expects the mirror image unless the entry's `rev` sub-object names its own. A record whose `expect_arrow` disagrees with signs.json FAILs. An explicit `--signs` that does not exist FAILs. | no number |
| race furniture as ground (new) | `tools/signs_mesh.py` counted `1KERB` (race kerbs included) as ground | `load_bvhs` leaves race furniture out of ground and road: 1KERB_RACE / 1WALL_RACE names, and the RACE / RACE_CLOSE_* collections. `verify_signs` FAILs if the authoring record or its own scan lists one. | no number |

**Proof that the checks bite.** All runs were record-level, on a scratch copy, logs in
`scratchpad/round2/signs/teeth_*.log`.
- (k) FAILs on v0.17.1's record: 5 corners with "no record at all for rev (race_acw)".
- The race-ground check FAILs on the diagnosis's unfiltered authoring run: 8 × `1KERB_race_*`.
- (j) FAILs on a -rev plate given a right arrow.
- (k) FAILs with one -rev plate removed, and again with a -rev skip whose reason is `expect_arrow`.
- Added after review (the reviewer planted `"M4": {"rev": {"skip": true}}` with no reason and the first cut of (k)
  PASSed with race_acw's Jackson/Navajo arrow gone). `place_signs` now exits 1 on that signs.json, and on a blank
  reason. (k) FAILs on records whose M4-rev skip reads `signs.json skip: (no reason given)`, `sign base is ON
  pavement`, `OUTSIDE ASSERTION FAILED`, or a signs.json skip that signs.json does not make. A reasoned
  `"rev": {"skip": true, "reason": "…"}` still places 22 and PASSes. Logs: `scratchpad/round2/signs/fix2/teeth2_*.log`.
- `parse_id` no longer reads a corner named `…-2` (e.g. a merged `DCL-2` post) as a hairpin's second arrow: the
  record's `corner.second_arrow` decides, and for a skip, whether the id minus `-2` was placed.
- The 0051 record PASSes.
- `tests/tools/test_place_signs.py` covers each case on a synthetic square loop.

**Rehearsal.** On a scratch copy of the workshop's `loop.blend` as it is, with 35 race objects present.
- `verify_signs --blend` PASS: 23 posts, 23 plates.
- The 18 v0.17.1 posts moved 0.000 m. Ground was CURB + TERRAIN, with no race kerb in it.

**Who else this reaches.**
- The Lookout Lariat's config declares reverse layouts (street_reverse, race_cw). When its chain gains the signs
  step, (k) will FAIL until its own signs.json sets `both_directions_mainline: true`.
- `place_signs.DEFAULTS` is unchanged (false), so a track with no signs.json still writes the same bytes. This
  was checked on SD with the knob off: the output was byte-identical to HEAD's.

### Integration (2026-10-13, v0.18.0): (l) named corners stay signed — the verifier's gap closed

The 0051 verifier planted M4-fwd and M4-rev both lost (as "ON pavement" skip records, or gone) and `verify_signs` passed:
(k) only judges a corner that still has a plate in some direction, and `author_signs_blend` exits 0 on mesh-stage skips —
so 0050 reshaping the Navajo/Jackson curb could have cost every layout its Jackson/Navajo arrows with every gate green.

| Check | Rule | Threshold |
|---|---|---|
| (l) named corners | every corner `signs.json` names and does not skip outright keeps at least one plate; a MAINLINE one a plate in every driven direction (`layouts[].direction`) unless `signs.json` skips THAT approach with a reason — a rule reason (R_apex, \|D\|, …) does not cover a corner Kevin named; a side-street one a plate in each approach, or a skip there that (k) counts as coverage | none (structural) |

Teeth (tests/tools/test_place_signs.py::test_a_named_corner_that_lost_every_plate_fails_l): both M4 plates as
"ON pavement" skips (k blind) → FAIL; both records gone → FAIL; M4-rev lost to a rule reason → FAIL (k passes it); the
same with `"rev": {"skip": true, "reason": ...}` → PASS; MED-6-rev lost to OUTSIDE ASSERTION → FAIL, to R_apex → PASS.
On the v0.18.0 build: 23 posts, 11 named corners (M1–M5, MED-1/6/7/8/10/13) all signed, M4-fwd / M4-rev clear the race
curb strip by +1.853 / +1.762 m (verify_race G's own margin).

## 2026-10-12 — worn race kerbs: the atlas wrap, the no-black-slot guard, the opt-in wheel kerb effect (ledger 0053)

Kevin, from the seat on v0.17.1: "i'd like the race curbs to be tire-worn/textured". The eight `1KERB_race_*` kerbs
keep every vertex, face and hard edge (scratch rehearsal: `race_authored.json` ring centres and frames identical for
all 35 objects, 167,958 positions before and after), so no driving-surface gate moves: `drive_test`, `audit_mesh`
(K 154), `verify_race`, `kn5_ground_check` judge the same geometry. What changes is the picture, the wrap and one
guard. Every number below is **[invented]** unless it says measured.

| Value | Where | Number | Flag |
|---|---|---|---|
| atlas repeat along the kerb | `race_furniture.KERB_ATLAS_V_M` | 8.0 m (2,048 px at 256 px/m) | ⚠ invented |
| red / white block | `KERB_BLOCK_M` | 1.0 m (the 0047 stripe was 0.5 m + 0.5 m) | ⚠ invented |
| rubber levels | `KERB_ATLAS_COLUMNS`, `kerb_wear` | 4 columns; level = min(3, int(4 w)), bins of 0.25 | ⚠ invented |
| inside-kerb lobes | `KERB_WEAR_IN_*` | each direction's late apex PC + 0.6 arc / PT − 0.6 arc; sigma max(5 m, 0.15 arc); floor 0.15 | ⚠ invented |
| outside-kerb lobes | `KERB_WEAR_OUT_*` | each direction's track-out PT + 0.2 E / PC − 0.2 E; sigma 6 m; floor 0.10 | ⚠ invented |
| joint snap | `KERB_JOINT_SNAP_MAX_M` | a whole metre of the kerb's own mid-line becomes a joint station only if a station lies within 0.25 m; v is warped so every joint station sits on a whole metre; a block takes the highest raw level of its stations; the column changes only there | ⚠ invented |
| column pad | `KERB_ATLAS_PAD_PX` | 8 px each side of a 256 px column (mip level 3 stays inside its column) | ⚠ invented |
| wrap handedness | `KERB_V_SIGN` | L −1, R +1: every kerb's (T × B) · N = +1 in the Blender frame, the sign of the prep's `planar_uv` road wrap (a kn5 tangent has no handedness sign). Not a threshold: derived and tested | measured (tests) |
| kerb material | `pbr.KS_PROPS["1KERB_RACE"]` | ksAmbient 0.40 / ksDiffuse 0.40 (the add-on default every neighbouring race material ships at, measured) ; ksSpecular 0.10, ksSpecularEXP 20 (Kunos Laguna `red_curb` measured at 0.35 / 20, technique only) | ⚠ 0.10 invented |
| the picture | `tools/make_kerb_texture.py` | colours (RAL 3020 / 9016 weathered), `RUBBER_COVER` 0 / 0.12 / 0.30 / 0.55, `RUBBER_OPACITY` 0 / 0.55 / 0.70 / 0.82, `RUBBER_HAZE` 0 / 0.12 / 0.28 / 0.46, `CHIP_COVER` 0.035, `NORMAL_STRENGTH` 2.2, JPEG q90 4:4:4 | ⚠ invented, tuned by eye on Blender stills |
| texture budget | `make_kerb_texture.MAX_BYTES` | ≤ 2,000,000 B per file (painted: 567,921 + 980,349) | ⚠ invented |
| render-vertex cost of a seam | `render_vertex_count(..., face_uvs)`, `KERB_SEAM_RENDER_VERTS` | exactly +4 per seam: the 5 cm outer face always wraps column 0 (`KERB_OUTER_FACE_COLUMN`, pixel-identical in every column), so a seam re-cuts the lip, both faces at the ramp-top edge and the top's outer edge, not the outer face's two (the first cut re-cut all 6: 7,356) | measured: pure 7,050 → 7,254 for 51 seams = the built kn5's KERB count exactly |
| Lake Murray kerb render budget | `tests/tools/test_kerb_wear.py` `SD_KERB_RENDER_VERTS_MAX` | KERB ≤ 7,300 render vertices (installed v0.17.1: 7,050), pre-registered in the diagnosis before the fix; held, not moved (verify round 1) | ⚠ invented (pre-registered) |
| normal-map convention | `make_kerb_texture.normal_rg`; `test_normal_map_is_opengl_green_up`, `test_joints_are_grooves_in_the_normal_map` | OpenGL like every map in assets/textures: a synthetic ramp rising down the image gives G > 128; every joint is a groove (G < 110 just above, > 146 just below; measured ≈ 36 / ≈ 220). Pillow flips kernels vertically; the first cut was DirectX (≈ 223 / ≈ 33) | test thresholds ⚠ invented; convention measured |

**New gate — `tools/check_race_kn5.py` `black_slots` (hard, both roles, every race kn5).** Every texture the
`pbr.TEXTURES` race rows bind for the meshes present must be embedded with > 0 bytes, and (when the parse carries
materials) each race mesh's material must bind exactly its row's `txDiffuse` / `txNormal` and nothing unembedded.
Why: `ship_sd.sh` exports from engine-july, which stages textures from ITS `assets/textures`; a file that is only in
airoso is skipped with a WARNING and the slot renders black (LAWS L7) — the old role checks passed such a kn5. Proof:
the installed v0.17.1 race kn5's parse now FAILS (`kerb_diffuse.png` outside the race set, the worn pair not
embedded, 16 bindings disagree); the rehearsed kn5 PASSES. `tests/tools/test_check_race_kn5.py::test_ledger_0053_no_black_kerb_slot`.

**Opt-in — `track_folder.surfaces_ini(kerb_ff_effect=0)`.** `FF_EFFECT=<n>` on the KERB block only, read from
`track.config.json` `kerb_ff_effect` (absent = 0). The default output is byte-identical (md5 pinned for tarmac /
gravel × wall, `tests/ac/test_road_surface.py`); opt-in changes exactly one line. 1 is the Kunos convention
(measured FF_EFFECT=1 on Vallelunga, Silverstone, Laguna Seca, Brands Hatch, Red Bull Ring, Barcelona, Imola, Mugello;
0 on Zandvoort; absent on Highlands). Caveat recorded: KEY=KERB also covers the street `1KERB_sidewalk` (114,081 m²
in the main kn5), so an opted-in track's sidewalks get the wheel effect too. No track opts in in this commit
(Lake Murray's config is the integration run's, Kevin's call).

Rehearsal (scratch copy of the v0.17.1 workshop + a scratch engine-july carrying this pbr.py and the two textures):
author → `verify_race` OK → prep → split → `<slug>_race.kn5` **10,253,676 → 11,815,506 B (+1,561,830 B, +15.2 %)**
(the textures embedded are the bytes packed at the prep — see ledger 0053 "Integration"), `check_race_kn5 --role
common` OK, all 8 kerb materials `ksPerPixelMultiMap` txDiffuse + txNormal, ksSpecular 0.1. Re-run after verify
round 1 (the OpenGL normal map and the 4-per-seam wrap): `<slug>_race.kn5` 10,253,676 → **11,811,590 B (+1,557,914 B,
+15.2 %)**, the embedded normal map 980,349 B with the committed file's md5, KERB **7,254** render verts (≤ 7,300),
every column split on a whole-metre joint, every outer-face vertex in column 0, kerb positions and triangles
identical to installed v0.17.1.

### Integration (2026-10-13, v0.18.0): the textures ride the pending-mirror record

`tools/snapshot_engine_july.py` now also writes a referenced texture the real engine-july lacks (old md5 "-") or holds at
another md5 into `PENDING-MIRROR.md5`, and `test_live_engine_july_has_not_drifted_from_the_snapshot` / `--check` read
such a line as pending, not drift — so the worn kerb atlas (`kerb_race_worn_diffuse.jpg` f599d4a7…, `_normal.jpg`
8f4b343a…) is on the mirror list beside `pbr.py` (now both the BRIDGESTRUCT and the worn 1KERB_RACE rows, CRLF md5
48617c1e…) instead of failing the suite until the install. No threshold changed.

## 2026-10-12 — the AI line gate: `tools/verify_ai_line.py`, and the writer's opt-in (ledger 0052)

Kevin, from the seat, after a 7-AI race on the installed v0.17.1 race layouts: "ai races need tuning, they tend to
crash and slow down weirdlu". Nothing measured a written `fast_lane.ai` against the walls the car hits:
`ai_draft.json` judges the line against the writer's own CorridorFaces declaration, at 0.6 m.

### The gate (`tools/verify_ai_line.py <project> --layout <id>`, new)

It reads the line AS WRITTEN (`<project>/ai/<id>/fast_lane.ai`, kn5 frame) and the BUILT gate OBJ
(`data/track.<id>.obj`: road + race + that layout's closure kn5, engine frame). It writes
`data/ai_verify.<id>.json` and exits 1 on any FAIL. Thresholds can be overridden per track in
`track.config.json` `ai.verify`. The "MEASURED" references are the 217 AI lines installed on this PC, measured in
the 0052 diagnosis. Kunos walls were read from their `NNWALL` physics meshes through `scripts/modkit`'s kn5
reader.

| Check | Threshold | Flag | v0.17.1 race_cw / race_acw | 0052 lines (scratch) |
|---|---|---|---|---|
| V1 `length` = the 3D distance to the previous point | median error < **0.01 m** | MEASURED (Kunos 0.0001-0.001 m; 0 of 186 reference lines cumulative) | 6,732 / 6,721 m | 0.0 / 0.0 |
| V1 `direction` | ±1 on every point; = −sign(heading change over ±10 points) on ≥ **99 %** of points turning > 0.5° | MEASURED (Kunos 99.0-99.5 %) | 0 everywhere | 100 % / 100 % |
| V1 header lapTime / sampleCount | **0 / 0** | MEASURED (every Kunos line; actools "usually zeroes") | 281085/8979, 281338/8964 | 0/0 |
| V1 `radius` = the 3-point circumradius | median \|ln\| error < **0.01** | MEASURED (Kunos 0.0006-0.0025) | 0.194 / 0.242 | 0.0 / 0.0 |
| V1 `camber` = asin(normal · right) of the BUILT 1ROAD under the point | median ratio **0.9-1.1** where the road tilts > 0.01 rad, else median \|diff\| < 0.005 rad; normal not (0,1,0) everywhere | MEASURED (Kunos ratio 0.94-0.99) | ratio 0 (camber 0, normal up) | 1.0 / 1.0 |
| V2 wall clearance: the line's centre to the nearest BUILT 1WALL footprint (horizontal, layer band −2/+4 m, L4) | min ≥ **2.0 m** | MEASURED (ks_monza66 1.981, ks_black_cat_county 2.066) | 1.506 / 1.504 m | 2.517 / 2.387 m |
| V2 lap within 2.5 m of a built wall | ≤ **1.0 %** | ⚠ INVENTED (BCC 0.58 %, Monza66 3.2 %) | 1.38 % / 1.77 % | 0.00 % / 0.04 % |
| V3 spurious dips (defined below) | **0** points | MEASURED (0 on ks_black_cat_county, ks_vallelunga, ks_highlands) | 160 / 875 | 0 / 0 |
| V3 bend flips: car-scale curvature (turn over ±4 points) with \|k\| > 1/300 changing sign within 30 m | ≤ **0.75 per km** | MEASURED (BCC 0.72) | 1.71 / 0.97 | 0.67 / 0.52 |
| V4 sides: sideLeft / sideRight past the first BUILT wall a horizontal ray PERPENDICULAR to the line meets | **0** points | — (geometry) | 0 / 0 | 0 / 0 |
| V5 the line's own 3-point radius | ≥ **11.4 m** | the writer's RADIUS_FLOOR_M 12 × RADIUS_CHECK 0.95 | 12.56 / 12.55 m | 13.78 / 14.33 m |

**The spurious-dip definition (V3).** Two physics speed profiles are built from the same line:
- the same settings for both: μ 1.0, 0.9 g braking (backward pass), 0.35 g acceleration (forward pass),
  69.4 m/s cap, two passes each round the closed lap;
- one profile uses the payload's radius field; the other uses the line's car-scale radius (the circumradius
  through the points ±4 = ±6 m).

A point where the payload profile is more than **10 %** slower than the car-scale profile is a spurious dip. In
plain terms: the file tells the AI to slow for a bend the car-sized line does not have.

**V4 corrects the diagnosis.** The diagnosis counted 23 race_acw points with `sideLeft` "past a built wall". That
used the nearest wall on the left half-plane in any direction. Every one of the 23 was a wall 16-18 m BEHIND the
point, 0.1-0.9 m to its side (probe at idx 2965-2977, 4919-4923, 6519-6525). On a perpendicular ray, the
v0.17.1 sides stop exactly 1.2 m (the margin) short of the wall, median, with 0 overreach. The gate uses the ray.

Wiring: not in a ship chain yet — `tools/ship_sd.sh` and `tools/ship_track.sh` are held by concurrent jobs this
round. Ledger 0052 "Held files" gives the exact change. Note that the AI step there runs BEFORE the race gate OBJs
are extracted (`ship_sd.sh`: write_ai_line at :251, `kn5_to_gate_obj` at :304, after the `rm` at :289), so the
extraction has to move ahead of the AI step for the gate and the writer's `ai.surface` to see this run's world.

### The writer (`scripts/ac/write_ai_line.py`, opt-in `track.config.json` `ai`; absent = today's bytes)

| Knob | Value | Flag |
|---|---|---|
| `ai.wall_clear_m`: a corridor line's comfort clearance (box approach, box arcs, floor fillets) | **2.5 m** (FILLET_COMFORT_CLEAR_M 1.5 stays the default) | ⚠ INVENTED (a 1.9 m car's half-width + 1.55 m; the 6.86 m narrowest corridor fits 2.5 m each side with 1.86 m to spare) |
| fair_line hold on the input line `FAIR_W` / curvature weight `FAIR_ALPHA` / leash `FAIR_U_MAX_M` | **1e-6 / 1e-2 / 3.0 m** | ⚠ INVENTED, swept on SD race_cw: w 1e-4 kept every gentle road S (1.49 flips / km); α 1e-3 left 0.82 / km; α 3e-2 pressed the line onto its bounds (32 dips) |
| polish after the fairing `FAIR_POLISH_W` / `FAIR_POLISH_U_M` | **1e-4 / 0.3 m** | ⚠ INVENTED. Without it, nearby settings left 9-77 dips where an active bound met the line; with it, 0 in every setting swept |
| the fairing's own wall margin `FAIR_CLEAR_EXTRA_M` | **+0.5 m** over wall_clear (never closer than where the point stood) | ⚠ INVENTED (0 and 0.25 also passed; 0.5 keeps the 2.5 m band empty on race_cw) |
| bound envelope `FAIR_BOUND_SMOOTH_PTS` | **±4 points**, min then mean, twice (conservative by construction) | ⚠ INVENTED |
| payload `direction` window | **±10 points, 0.5°** | MEASURED (the window the Kunos agreement was measured over) |
| `ai.surface: gate_obj`: seat on the BUILT 1ROAD within **3 m** of the point's height; the walls' layer band **−2 / +4 m** | — | ⚠ INVENTED bands (the diagnosis' filter); the writer refuses a missing gate OBJ, or one older than a kn5 its header names |

Proof:
- `tests/ac/test_write_ai_line_payload.py` (9 tests).
  - Byte identity: golden md5s of all 25 files of the two end-to-end fixtures, HEAD 5ccf20b's writer.
  - On a synthetic built world: the payload's meaning, the wall clearance, the gate passing the opted-in line and
    failing the legacy one.
  - The banded solver, fair_line's bounds, the OBJ reader's layer filter and rays, the stale-OBJ guard.
- Byte identity on the real workshop (scratch copy, no `ai` block): `race_cw` `8d4696a4…`, `race_acw`
  `c234c87c…` and `street` `93a09e5a…` are md5-identical to the installed / HEAD files. The same holds for every
  `side_*.csv` and `ai_draft.json`.

### Repair, 2026-10-13 — labels re-measured, camber sign, the box rule on the written line (ledger 0052)

An independent check refuted three things above. The rule applied here: a threshold says MEASURED only if every
Kunos line it cites passes it; anything else is ⚠ INVENTED, with the references it was chosen against. The rows in
the tables above stand as the record of what was first claimed; **this subsection supersedes their flags and
values.** Evidence: the gate's own `measure()` / `judge()` run on all 34 Kunos lines installed on this PC, each
line's own stored normal standing in for the built road (scratch `v018/ai/kunos/kunos_v1.txt`).

| Check | Threshold now | Flag now | Kunos (34 lines) | v0.17.1 race_cw / race_acw | repaired lines |
|---|---|---|---|---|---|
| V1 line family | SEGMENT (length = one segment, 3-point radius) or WINDOW (length = 5 segments summed, radius through ±5 points, direction ramp over **10** points per end) — the length field decides; a line that matches neither is judged as SEGMENT | MEASURED (33 SEGMENT; ks_silverstone/international WINDOW, as are 33 third-party lines) | 34 / 34 classified | SEGMENT (matches neither) | SEGMENT |
| V1 `length` | median error < **0.01 m** against the family's reference; SEGMENT also ≤ **0.1 m** on every point but the last | MEASURED (median 0.0000-0.0016 m; SEGMENT point max 0.056 m; the last point carries ~5 × spacing on every Kunos line, so it is not judged) | pass 34 / 34 | 6,732 / 6,721 m | 0.0 / 0.0 |
| V1 `direction` | ±1 on every point but the last (WINDOW: but the seam ramps); = −sign(LOCAL heading change, ±**1** point) on ≥ **99 %** of points turning > 0.5° | MEASURED (0.9977-1.0 at ±1 point; the first version's ±10 window gave 0.968-0.995, 23 of 33 under 0.99) | pass 34 / 34 | 0 % | 100 % / 100 % |
| V1 `radius` | the family's circumradius, median \|ln\| error < **0.01** | MEASURED (0.0001-0.0035) | pass 34 / 34 | 0.194 / 0.242 | 0.0 / 0.0 |
| V1 `camber` (SEGMENT) | = **−direction × asin(normal · right)** of the BUILT road (the tilt measured toward the bend), median ratio 0.9-1.1 where it tilts > 0.01 rad | MEASURED (ratio 0.998-1.001; the sign rule holds on 0.95-1.00 of tilted points on every reference line, plain asin(normal · right) on ~0.5) | pass 33 / 33 | ratio 0 | 1.00 (34 / 62 tilted points) |
| V1 `camber` (WINDOW) | not judged | — (Kunos' own stores the normal as (0,1,0) beside a real camber, so nothing shows what it is measured from) | — | — | — |
| V1 camber on a flat road | median \|difference\| < **0.005 rad** | ⚠ INVENTED (passes every SEGMENT Kunos line) | | | |
| V1 measuring parameters: a bend = turn > **0.5°**; a tilted road = > **0.01 rad** | — | ⚠ INVENTED | | | |
| V2 wall clearance min | ≥ **2.0 m** | ⚠ INVENTED — was "MEASURED", but ks_monza66 measures **1.981 m**, so 2.0 is a choice between the two walled Kunos references (BCC 2.066), not a value both pass | — | 1.506 / 1.504 m | 2.549 / 2.387 m |
| V3 spurious dips | **0** | ⚠ INVENTED — was "MEASURED (0 on BCC, Vallelunga, Highlands)", but ks_highlands/layout_int has 422 by the gate's own code; 20 of 34 Kunos lines have 0, 14 have 5-885 (recorded lines carry them) | 0 on 20 / 34 | 160 / 875 | 0 / 0 |
| V3 bend flips within 30 m | ≤ **0.75 / km** | ⚠ INVENTED — was "MEASURED (BCC 0.72)"; Kunos 0-1.24 / km, ≤ 0.75 on 17 of 34 | 0-1.24 | 1.71 / 0.97 | 0.74 / 0.52 |
| V4 sides past a built wall | **0** | ⚠ INVENTED (geometry rule) | | 0 / 0 | 0 / 0 |
| V5 the line's 3-point radius | ≥ **11.4 m** | ⚠ INVENTED (the writer's RADIUS_FLOOR_M 12 × RADIUS_CHECK 0.95, both invented) | | 12.56 / 12.55 m | 13.78 / 14.33 m |
| V6 (new, `--baseline <line>`): every baseline corner (car-scale minimum under 80 m within ±60 points) keeps ≥ **0.85 ×** its radius | | ⚠ INVENTED (the 0052 diagnosis' pre-declared box rule) | | — | 0.860-0.863 / 0.860-0.877 |

The payload `direction` window in the writer is now **±1 point** (MEASURED, as above), replacing the ±10 points
recorded in the writer table above.

Writer additions (`scripts/ac/write_ai_line.py`, opt-in `ai.fair` only; no change without the `ai` block):

| Knob | Value | Flag |
|---|---|---|
| `FAIR_BOX_KEEP`: the fairing never takes a box corner's car-scale radius (points ±4) under this × the arc the v0.17.1 rule (comfort 1.5 m) lays at that corner in the same world, within the corner's stations ± `FAIR_BOX_GUARD_PTS` | **0.86**, ± **20 points** | ⚠ INVENTED (the 0.85 rule + 1 % margin; 20 points = 30 m) |
| `BOX_RULE_KEEP`: the writer REFUSES a faired line whose box corner ends under this × that arc | **0.85** | ⚠ INVENTED (the diagnosis' rule, declared before the fix) |

What the first version got wrong, and what changed:
- **Camber sign.** It stored plain asin(normal · right). race_acw carried all 62 tilted points at the opposite sign
  from every reference line (race_cw agreed only because its tilted points all carry direction −1). Writer, gate and
  test now use −direction × asin(normal · right); the plain form FAILS the gate on race_acw.
- **The box rule.** The diagnosis declared each box ≥ 0.85 × today's radius before the fix. The first version met it
  on the arcs before fairing (0.885-0.935) and missed it on the written line (cw 0.819-0.845, acw 0.79-0.87). The
  written line now keeps 0.860-0.877, and the writer refuses under 0.85. Each box apex is 4-6 km/h slower on paper
  than v0.17.1 (it was 4-9 km/h in the first version).
- **Kunos lines failing the gate.** Every Kunos line failed the first version's V1 (direction window, the last
  point's length, the recorder's seam). V1 now passes all 34, and either family of in-game recording.

Proof: still failing every v0.17.1 defect (10 FAILs per layout: V1 length, length per point, direction ±1, direction
agreement, header, radius; V2 min, V2 band; V3 dips, V3 flips). Planted on the repaired lines, each of these FAILS:
cumulative length, direction 0 / flipped, header set, min-of-5 radius, camber 0 with normal up, camber sign flipped,
the plain-asin camber (race_acw), a 0.8 m bump toward the K-rail, 0.25 m / 30 m and 0.6 m / 60 m S-wiggles, 3 cm
jitter, a 1.5 m kink, sides +3 m, one length 0.5 m off its segment. The same line re-expressed in the WINDOW family
PASSES (scratch `v018/ai/planted/plant.txt`). Tests: `tests/ac/test_write_ai_line_payload.py` 12 (adds: the
WINDOW family accepted and a cumulative length judged as SEGMENT; the writer's box-rule refusal).

### Integration (2026-10-13, v0.18.0): the chain order the opt-in needs

`track.config.json` `"ai"` (race_cw, race_acw; kunos payload, 2.5 m off the K-rail, faired, seated on the gate OBJ) is
set, so the writer refuses a missing or stale gate OBJ. `tools/ship_sd.sh` (and `ship_track.sh`'s `ship_ai`, for a track
whose config names the layout) now extracts each race layout's gate OBJ (road + common race + ITS closure kn5) right
before `write_ai_line`, after every export, and runs `tools/verify_ai_line.py --layout <id>` straight after it, hard
under `set -e` (no `--baseline`: the writer holds the box rule itself). The gate stage re-extracts the same file from the
same kn5s. `data/ai_verify.<id>.json` is synced back. No threshold changed.

Measured on the v0.18.0 rehearsal (the 0046 terrain, 0050's levelled fans, 0053's kerbs): race_cw PASS (wall min
2.549 m, 0 m within 2.5 m, dips 0, flips 0.743 /km against the [invented] 0.75, min radius 13.78 m, lap est 279.4 s);
race_acw PASS (2.387 m, 0.00045 of the lap within 2.5 m, flips 0.521 /km, 14.33 m, 272.7 s); the box rule held on the
written line (cw 38.8/45.13, 24.65/28.68, 28.19/32.78, 38.37/44.52 m; acw 41.88/47.49, 46.36/52.27, 45.4/52.32,
51.1/58.54 m). race_cw's flips keep their thin margin (0.007 /km).

### Integration fix round (2026-10-13, v0.18.0): the writer's fairing round cap

`scripts/ac/write_ai_line.FAIR_RADIUS_ROUNDS` 12 -> **24** [invented]. On the integration fix round's world (College Ave's
deck on its real abutments, the released ground, the rails) race_acw's fairing ran out of rounds with 9 box points still
tightened (the polish 4) and left a 5-point kink at the v1514 box exit, which `verify_ai_line` V3 filed as a 12.9 % phantom
speed dip (61 vs 70 km/h) — the gate was right, the solve was unconverged. With 24 it converges at 18 rounds (box points
left tightened 0), V3 0 dips; race_cw converges at 5 either way (unchanged). No threshold of the gate changed.

## 2026-10-13 — 0050 levelled fold pinches + `tools/verify_fold_fans.py`; drive_test's in-fan severe steps (ledger 0050)

**Why.** Kevin, from the seat: "the small steps are a problem at jackson/navajo". The 2026-10-11 weld pinched the
Navajo/Jackson inside edge at its HIGHER leg and left the lower leg's last row 6 cm away: a 901 % road triangle, a lip
0.13 m tall 3 m from the centre line and 0.47 m at the kerb. drive_test filed the street's 0.24 m of it as an exempt
"apron step" (w ≥ 9.5, |off| > 3.5), and the race layouts' severe 31 / 28 was shipped as "the next owner's"
(2026-10-11, "Named, not exempted").

### The weld (`tools/mouth_weld.unfold_line`, `level` follows `strict`: the weld's MAINLINE only)

| Number | Value | Why |
|---|---|---|
| `FOLD_LEVEL_ROWS` | 8 rows each leg [invented] | the diagnosis: 6 rows → 1 m second difference 0.031 m, 12 → < 0.025 |
| `FOLD_HALF_JUMP_MAX_M` | 0.28 m — ROAD edges and curb p0 / p1 only; p2 / p3 uncapped | derived: a 1.20 m K-rail buried 0.05 m covers no_route's [0.20, 0.90] band only within ±0.30 m of its reference, less a 0.02 m margin [invented]. Not the seal guarantee (the reference is the projected centre line, not the leg): no_route and verify_fold_fans (7) are. Measured at Navajo/Jackson: ROAD / p0 0.248, p1 0.251, p2 0.317, p3 0.359 m — capped, p2 / p3 stopped the build (the review's BLOCKER 1) |
| `FOLD_LEVEL_XFALL_MAX` | 4 % [invented] | an eased row's height change over its plan distance to the centre row (Navajo/Jackson: ~2 %) |
| overlap refusal | a leg window over another cut (or its windows) on the line | the result never depends on the order the cuts are found |

### The gate (`tools/verify_fold_fans.py <project>`, new; hard in `ship_sd.sh` / `ship_track.sh` after the race gates; `--force-install` does not cover it)

Per levelled pinch (`data/mouth_welds.json` `folds.MAINLINE.levelled`; a pre-0050 file: re-found on the ROAD edge rebuilt
from the gate centreline), per layout, on the BUILT gate OBJ, in the driven lane (street ±(w/2 − 0.5) less the median
island + 0.4 m; race `lane_by_vertex`), on wheel paths cut at their own self-intersection:

| Check | Threshold | Status |
|---|---|---|
| window | rows k − 8 − 4 … l + 1 + 8 + 4 (`WINDOW_PAD_ROWS` 4) | [invented] |
| paths | every 0.25 m across the lane, sampled every 0.05 m | [invented] |
| (1) FINE step | rise over 0.10 m beyond the previous metre's grade ≥ 0.02 m | 0.02 m = the diagnosis' step a tyre hits; 0.10 m window [invented] |
| race kerb lip allowance | ≤ 0.055 m when a `1KERB_race` kerb is on one side | the authored 0.05 m kerb + 5 mm sampling [invented] |
| (2) DT | 1 m second difference > 0.06 m, unless the metre touches a race kerb | drive_test `STEP_SEVERE_M`, reused |
| (3) road jump | two 1ROAD vertices ≤ 0.10 m apart in plan, heights ≥ 0.02 + 0.25 × distance apart | 0.10 m [invented] |
| (4) grass in the lane | > 0.02 m over the pavement beneath, on the rows the leveller moves (k − 7 … l + 8) | 0.02 m = (1)'s [invented]; the prep pins grass 0.02 m under the deck at its vertices, so facets graze the deck by millimetres between them (v0.17.1: up to 0.030 m at the hairpin's row 755, a row the leveller does not move) |
| (5) steep road triangle | plan area ≥ 0.01 m² and slope > 25 % | both [invented]; the installed riser was 901 % |
| (6) the pinch at its midpoint | every road vertex within 0.02 m of X within 0.01 m of (y_k + y_l) / 2 | 0.01 m [invented] |
| (7) race walls | 0.5 m cells, base = 3×3 minimum, within 25 m of X; base + 0.05 − (no_route reference + 0.10) within ±0.28 m | 25 m [invented]; ±0.28 m derived as above; the 3×3 aggregation is the 0050 review's |

Calibration (the review's BLOCKER 2: as first specified the gate failed the FIXED build): scoped by the driven lane, not
by exempting curbs (the street median curb is outside the lane); to the levelled pinches (the chord mends' pre-existing
0.07-0.08 m race DT stay drive_test's); grass by depth on the moved rows. Teeth on the installed v0.17.1 OBJs: FAIL at
Navajo/Jackson on (1) (2) (3) (4) (5) (6) (7) — 45 / 44 / 44 paths, FINE 0.422, DT 0.481 / 0.465, the 901 % triangle,
0.499 m between two vertices 0.055 m apart, grass 0.192 m over the road, X 109.310 vs 109.061, walls +0.498 — and at the
hairpin and College/Navajo on (6) only. On v0.18.0: PASS, 3 pinches × 3 layouts (ledger 0050 Results).

### drive_test (engine; opt-in by `data/mouth_welds.json`, every other track byte-identical)

| | Before | After |
|---|---|---|
| a severe step (> 6 cm) inside a levelled fold fan | "apron step" on pavement ≥ 9.5 m wide past 3.5 m (exempt) | severe (fan = rows k − B … l + 1 + B of each levelled ROAD pinch, discs of half-width + 0.5 m [invented]; a pre-0050 file: every ROAD cut) |
| a bump (2.5-6 cm) there | apron bump | unchanged: measured, the fixed-station paths read 56 street "bumps" in the two fans from their own changing spacing round corners tighter than the offset (2.5-4.7 cm on a 2-3 % grade) where verify_fold_fans' real paths read ≤ 0.025 m |
| the seam's 0.06-0.07 m street step (s 12-13, a chord mend) | apron step | unchanged (race_cw already counts it); not 0050's |

A weld that records a different row count from the gate centreline is refused (SystemExit).

**Measured** (v0.18.0 full rehearsal): street severe 0, bumps 0.15 → 0.0 /km, kinks 3.86 → 3.41, soft top 42 → 41;
race_cw severe 31 → 22, soft top 23 → 9; race_acw 28 → 20, 22 → 9; no_route BUILT PASS both (walls' worst offset near X
+0.263 m); audits unchanged; verify_mouths byte-identical to v0.17.1.

## 2026-10-14 — race layouts on their own LAP: every race gate counts along the layout's line (ledger 0054 phase 2 groundwork)

Phase 2 (Mission Gorge Speedway) needs a race lap that runs partly on the loop and partly on the expansion roads.
Every race tool read exactly one lap line — the mainline centreline — and counted along it by vertex number. Opt-in
now: `layouts[].lap = <lap id>` on a race layout, `race.laps.<lap id>` = `{pieces, corridor, kerbs, roads}`
(`scripts/geometry/race_lap.py`: the pieces stitched VERBATIM, junction gaps bridged by points resampled on the
straight join at the pieces' median spacing, closed, with `source_by_vertex` back to (line, vertex)). **No threshold
changed**: every gate below runs the same rule on the lap's own line and declaration
(`data/lap.<lap>.json`, `data/barrier_bands.<lap>.json`, `race_authored.<lap>.json`). A track whose layouts name no
lap runs byte-identical (the identity proof: the full v0.18.0 chain with main's tools and with these, md5 of every
output — the report of this change).

| Gate / tool | On a lap layout |
|---|---|
| `tools/barrier_bands.py` self-gates 1-12 + PLANNED no_route | one declaration per group (the mainline's race layouts → `barrier_bands.json`, each lap's → `barrier_bands.<lap>.json`); the lap's mouths = its pieces' side streets (a side street of a piece walked backwards flips side) + the BRANCH it abandons at each junction |
| `tools/no_route.py` | the lap's line + declaration; a probe carrying `xz` (a branch) is tested at that point |
| `tools/verify_race.py --lap <lap>` | A-O + F + G on the lap group; K now also fails a common object whose name carries the wrong group's lap token (or none) — the split routes on it |
| `tools/check_race_kn5.py --role common --lap <lap>` | `<slug>_race_<lap>.kn5`: every strip / kerb named `lap<lap>`; without `--lap` none may be (new check, same FAIL wording class) |
| `scripts/ac/verify_kn5.py` (f) / (g) | each lap's common kn5 checked like `<slug>_race.kn5` (+ the lap-token routing), stray `<slug>_race_*.kn5` fails; a lap layout's spawns judged on the lap (kn5 frame) against its own lane; its ini lists `<slug>_race_<lap>.kn5` |
| `scripts/geometry/drive_test.py`, `median_zone.py`, `audit_mesh.py --layout` | the lap's line + declaration (the fold-fan discs stay on the mainline rows the weld indexes) |
| `tools/verify_fold_fans.py` | a pinch the lap does not run over is skipped for that layout (behind its walls); the others take the lap's lane mapped back to the mainline row |
| `scripts/ac/write_ai_line.py` + `tools/verify_ai_line.py` | the line is drafted on `data/lap.<lap>.json`; the gate reads only the line and the BUILT OBJ (unchanged) |

New constants (all in `scripts/geometry/race_lap.py`):

| Constant | Value | Flag |
|---|---|---|
| `DEDUPE_M` — consecutive piece ends this close are one point (no join) | 0.25 m | [invented] |
| `BRANCH_PROBE_M` — a branch probe stands this far past the lap's curb along the abandoned line | 10 m | = `barrier_bands.MOUTH_PROBE_M` (the side-street probe), reused |
| `BRANCH_ON_LAP_PAD_M` — a "branch" whose probe lies within half-width + this of the lap is the lap itself | 1.0 m | [invented] |
| `CONNECTOR_ISLAND_SNAP_M` — a connector vertex takes the island width of the nearest `connector_islands` point within this | 1.0 m | [invented] |
| join spacing | the pieces' median vertex spacing (`race.laps.<lap>.join_spacing_m` overrides) | measured per lap |

A stitched junction is a zero-radius corner: its inside offset never crosses itself, so `race_furniture`'s fold trim
has no corner to trim the inside kerb to (it stops with "author this corner by hand"). That is DECLARED, not derived:
`race.laps.<lap>.kerbs.trims` drops it with its why (tests/tools/lap_world.py does exactly that).

Proven by `tests/tools/test_race_lap.py` on a synthetic world (a 2.4 km rounded-rectangle mainline, a connector up
its middle, a 1.6 km lap = the west half + the connector): the lap declared with every self-gate and the planned fill
green, the mainline's declaration byte-identical with or without the lap, the seal holding planned and BUILT and a
gap across a branch caught (forbidden probe + leak), spawns on the lap, the AI line inside its corridor and green on
`verify_ai_line`, drive_test's lane = the lap's (barrier_missing 0; a missing closure → `closure` missing), the lap's
ini loading its own common kn5.

## 2026-10-14 — College Ave's split section: the median trust test, a cut face, the Speedway chicane (ledger 0055)

Kevin (seat, v0.18.0): "one of the lanes swerves into where the other lane should be ... we should just cut into the
hillside the way California does ... But for the racetrack versions, I do like the chicane". **No existing threshold
was loosened.** One test was re-pointed (it measured the wrong line), one zone got its own reach, and three things are
new: a cut zone's rounding, the declared race chicane (its own self-gate, 13), and the street-only island kn5.

**`tools/median_envelope.py` trust test — the upper bound reads what it says.** `SEP_TRUST` 24 m (unchanged) was
compared with the RAW line's offset to the opposing carriageway's OSM way; it is now compared with the two
carriageways' separation (opposing way's lateral − the ridden way's lateral, the ridden way within the existing 8 m
chain bound, now the named constant `RIDDEN_MAX_M`). The lower bound (`MIN_SEP` 11 m) and the along-the-road test
still read the raw offset. Measured (diagnosis replay, the tool's own functions): over College v1282-1350 the raw line
sits on the aerial's southbound carriageway while OSM draws both ways ~3.5 m east of their pavement, so the raw offset
read 24.1-24.7 m (> 24: untrusted) where the carriageways are 20.5-21.2 m apart; the run split at v1280/v1353 and the
two run-end tapers swung the road 12 m onto the southbound carriageway and back. Whole-loop replay: College becomes one
run (825-1509), Navajo's two runs unchanged, no other run moves. Proven by `tests/tools/test_college_split_0055.py`
(a raw line 3.5 m outboard of its way, carriageways 21 m apart: ONE run, flat inside; 25.5 m apart: none).

**`tools/ground_release` — a CUT zone (`college_split_cut`).** Per-zone keys, absent on every other zone:

| Key | Value | Flag |
|---|---|---|
| `cut_reach_m` — the batter's CUT reads pavement within this (`BATTER_REACH_M` 12 m otherwise; the fill keeps 12 m) | 20 m | = `terrain.clamp_corridor_m` (L3's construction zone), not invented: at v1279-1306 the hill stands 12-13.8 m over the deck 12-14 m out |
| `round_m` — the cut's top is rounded into the real ground (a smooth minimum, never above the cut or the ground) | 3 m | [invented] inside docs/ROAD-CONSTRUCTION.md's researched 2-5 m |
| `ROUND_MAX_M` — the largest `round_m` accepted | 5 m | the research's upper bound |
| `rails: false` — no rail stations on a declared cut zone (only with `cut_reach_m`) | — | measured: the first rehearsal stood an 816 m jersey rail along the cut — the only fall a station read there is the sidewalk's own outer apron (0.14 m over 0.5 m), as on every street of the loop |
| `DEGEN_AREA_M2` / `DEGEN_DIST_M` — zone faces under this area are slivers of the halving, dissolved (was 1e-8 m², zone vertices only) | 1e-5 m² / 1e-3 m | [invented]: the cut zone's 800 m of kerb seam left 22 collinear slivers; one on the terrain's open edge carried its own corner as a T-junction and stopped the kn5 prep's weld ("face already exists") |

`BATTER_CUT` (1 m per metre) is the existing earth batter. The prep reads the same zones (unchanged: extra keys ignored).

**Race chicanes (`race.chicanes`, `scripts/geometry/race_chicane.py`, `tools/barrier_bands.py` self-gate 13).** A
declared chicane carries a race layout's lane across the road and back: the closure sweeps into the far curb strip
(pinned, the run split there) while a RACE-SIDE wall (`corridors.<id>.chicane_walls`, `race_wall_y_by_vertex`) sweeps
in parallel from the race-side strip (pinned), holds the far carriageway, and both return. Gate 13 FAILS on: declared ≠
driven; a zone other than `chicane` in the span; a race island inside it (past the modelled noses); the wall missing a
vertex (a door) or not pinned on the race strip centre (`PIN_TOL_M` 0.01, existing); the closure standing between the
legs or missing on a leg, or its chicane pins off the far strip centre; the lane past the strip faces, or narrower than
min(`clear_floor_m`, the corridor's own width at the chicane's two ends) or `clear_hard_min_m` (existing); any wall step
steeper than `steepest_pin_rate` 1:3 (existing); a wall plan radius under `RADIUS_MIN_M` 20 m or a backward step
(existing); the lane's faces not ON the walls; a crossing under `MIN_CROSSING_M`. The closure runs either side keep
gates 1-12 unchanged (the leg is their pin zone, its rate their pin rate, judged against the same 1:3).

| Constant | Value | Flag |
|---|---|---|
| `MIN_CROSSING_M` — the lane's centre moves at least this across the road | 15 m | [invented]; v0.18.0's crossing (the one Kevin liked) was 18.4 m, this one 19.9 / 20.4 m |
| `race_chicane.EASE` — each leg's slope eases in / out over this fraction (steepest = mean / (1 − EASE)) | 0.35 | [invented]: 0.2 (an 18 m ramp) bunched the AI line's turn-in under `verify_ai_line`'s ±6 m car scale — 57 V3 "spurious dip" points on the first rehearsal |
| `ISLAND_NOSE_VERTS` — the island author's nose taper | 3 | MEASURED (`author_median_blend.NOSE_VERTS`): the race island stays non-zero 3 vertices past each street-only cap so every tool's modelled nose lies beyond the physical, full-width cap |
| College legs v1253-1289 / v1343-1379 | 36 vertices each | measured: 26 stood at 1:2.85-3.0, 30 at 1:3.0-3.4 with EASE 0.2; 36 / 0.35 gives 1:3.2-3.5 |

The consumers judge the new wall exactly as a closure: `race_furniture` sweeps it into the layout's own closure kn5
(`wall: chicane`), `verify_race` C' / H / J / G measure it against `race_wall_y_by_vertex` (pins on the race-side strip),
`no_route` (planned) walls it, `median_zone` bands it (kind `chicane`) and `drive_test` probes it for `barrier_missing`
(a stricter gate: one more declared band to find a wall on). `write_ai_line` knows the zone (`chicane`, a walled lane).

**The street-only island (`<slug>_street.kn5`).** Where a chicane's span crosses the median, the island's curb and
barrier there are authored as `1KERB_sidewalk_streetonly_median` / `1WALL_guard_streetonly_median`
(`tools/author_median_blend.py`; no shrub planted — TreeFX is track-wide), routed by `tools/split_exports_blend.py` to
`loop_street.blend`, exported as `<slug>_street.kn5`, checked by the new `tools/check_street_kn5.py` (every mesh
street-only, every material's diffuse embedded, no AC_* node, under the vertex cap), listed in every NON-race layout's
ini (`track_folder`; `verify_kn5 --inis` now expects `[road, street, spawn]` there and FAILS a race ini that lists it;
`verify_kn5` FAILS the street kn5 missing, stray, or doubling a road mesh) and folded into `data/track.obj` (the street
layout's gate OBJ), never into a race layout's. Every race tool reads the island through
`race_chicane.race_island_w` (zero inside the span).

### Round 2 (2026-10-14, after the truth and gates lenses refuted round 1): the road on the measured carriageways, zones by vertex, the reverse layout's pocket probes, the AI line through the chicane

**No existing threshold was loosened.** One gate bug fixed (a probe planner that only worked forward), one AI-line bound
added where a chicane's walls sweep, one config mechanism added (a declared lateral registration), one zone form added
(by vertex). **Corrected:** round 1's text above says OSM draws College's two ways "~3.5 m east of their pavement" so the
raw offset read 24.1-24.7 m. The 3.6 m between the line and its own OSM way is `median_envelope`'s sphere projection of
OSM (`_meters_per_degree`, R 6371 km: 93,479 m per degree of longitude) against the line's WGS84 series (93,676), at
x ~ -1730 m. The re-pointed upper bound stands: the separation is invariant to that offset. The projection is not
changed (a WGS84 replay drops College v825-980's island and adds a Navajo run v2037-2161, outside ledger 0055; filed as
a follow-up). Round 1's aerial checks also read NAIP on its requested bbox; the ImageServer widens the latitude extent of
an EPSG:4326 window to square-degree pixels (the diag tile was served 16 % taller), so those numbers were 3-12 m off
north-south. Ledger 0055 has the re-measurement.

| Number / rule | Value | Where | Why |
|---|---|---|---|
| `route.median_registration` | rule | `tools/median_envelope.registration`, track.config.json | a declared, measured lateral move of a FINISHED divided road onto its real carriageways, cosine between declared points (zero slope at each: no kink), only inside one divided run of the named road, first / last lateral 0 (ramps declared), else exit 1 with the raw line restored. Lake Murray: College v1104-1505, +2.0..+5.5 m west, measured on USGS 3DEP 1 m (the median slope's half-height point between the benches, 61 sections v1190-1430) and NAIP 2022 on its served extent (22 sections), agreeing within ~0.5-1 m. Result: island centre minus the 3DEP median middle -4.3 m (round 1) -> -0.02 m (|max| 1.0) |
| `tools/median_envelope.REG_MAX_M` | 6.0 m [invented] | the registration guard | the largest declared move; College needs 5.5 m |
| a ground-release zone may be declared by centreline vertex (`v: [from, to]`, fractional) | rule | `tools/ground_release.resolve_zones` (resolved to stations on the current centreline; `s_m` OR `v`, never both) | a station is a place only while the road before it keeps its length: College's realignment shortened the lap 6.6 m and slid the station-declared Lake Murray Blvd I-8 span / creek zones 6.6 m off their abutment. `lmb_i8_span` (v4447.108-4479.852), `lmb_alvarado_creek` (v4479.852-4491.888) and `college_split_cut` (v1197.643-1468.542) are vertex-declared at their v0.18.0 / round-1 places (re-resolved on v0.18.0's centreline: 13330 / 13428 / 13464 within 0.05 m) |
| `race.corridor.boxes` Jackson / Lake Murray Blvd apex | v3296 (was v3297) | track.config.json | barrier_bands self-gate 1 requires the declared apex to be a detected one; place_signs' detector walks 1 m stations from v0, so the 0.45 m shorter lap moved its max-curvature station one vertex (2.1 m on the R 10.8 m arc). The corner and every vertex past v1510 are byte-identical; the box v3289-3304 still holds PC v3291 .. PT v3302. Tests pinned on v0.18.0's data keep v3297 |
| chicane pocket probes spaced by travel | rule (`tools/barrier_bands._chicane_record`: `abs(st - st at the last probe) >= PROBE_STEP_M`) | self-gate + planned no_route | the gates lens: the loop compared `st[v] >= next_s`, which never fires again when the stations run backward (race_acw walks v1379 -> v1253): 1 probe on race_acw, 12 on race_cw. Now 12 / 12 (test: counts within 2 of each other) |
| the AI line holds `wall_clear_m + FAIR_CLEAR_EXTRA_M` off both walls through a declared chicane | rule; 2.5 + 0.5 = 3.0 m on Lake Murray (both existing numbers) | `scripts/ac/write_ai_line.corridor_offsets(clear=...)`, build_line | the gates lens: with the 1 m hard bound (`LINE_MIN_CLEAR_M`) the smoothed lane-centre target cut each bend of the S toward its inside wall: race_cw under-band 0 -> 13.5 m, race_acw 6 -> 66 m (min 2.168 m), every new run in the chicane. Round 2: 0 m / 6.0 m and 2.52 / 2.385 m, as v0.18.0 (0 / 6.0, 2.544 / 2.386 at the same non-College places) |

**Measured on the round-2 full rehearsal** (fresh scratch workshop and engine-july, no `--skip-blend`,
`D:/k10-scratch/college/logs/full6.log`), v0.18.0 -> this build: street soft top 33 -> 32, severe 0, kinks 3.41 -> 3.41,
gated excursions 98 -> 100; race_cw severe 22 -> 25, kinks 6.23 -> 6.61; race_acw severe 20 -> 22, kinks 7.05 -> 6.46;
barrier_missing 0, obstruction 0; audits 53 / 53 / 53 (D 0); no_route planned and built PASS (leak 0, 0 / 411);
verify_ai_line PASS. **The three raw increases are drive_test's sampling, not the road** (named, not hidden): its 1 m
and 150 m stations start at v0, so a lap 6.565 m shorter on College re-samples everything after it. On v0.18.0's own
mesh with the start moved +6.565 m (a read-only copy of drive_test, start offset only) the same counts read 102 / 26 / 25
and kinks 3.19 / 7.20 / 7.20. Matched place by place: race_cw severe steps before College 8 = 8, on College 0 = 0, after
it 17 = 17 at the same vertices; race_acw 13 = 13, 0 = 0, 9 = 9; street gated excursions before College 34 = 34, on
College 0 (v0.18.0: 4), after it 66 vs 64, the +2 at v3806 where drive_test's flare exemption (`widths[i] > median + 1.5`)
reads the lap's median width, raised 17.0 -> 17.64 m by College's continuous divided run (the mesh there is identical).

## 2026-10-14 — the modern LED street light: one light per lens, the lamp's own mast in G, the pool measured (ledger 0056)

Kevin, 2026-10-14: "make lighter lamp model" / "more modern" / "Taller too". `tools/author_lamps_blend.py` now stands
the model `track.config.json` `scenery.streetlights.model` names at every post (`led_cobra` on Lake Murray; absent =
`street_lamp_2026_10`, the v0.18.0 path byte-for-byte — the one-key rollback). The model is generated by
`tools/make_streetlight_led.py` (CC0, deterministic). **No gate threshold changed**; two gate inputs follow the model and
one clustering rule was fixed. Full rehearsal (no `--skip-blend`, scratch copies, `--no-install`): every gate number
equal to v0.18.0 (street soft top 33 / severe 0 / kinks 3.41 / audit 53 (K 20, I 20, F 13); race severe 22 / 20,
no_route PASS both, barrier_missing 0, obstruction 0; verify_mouths, verify_fold_fans, verify_ai_line, verify_signs,
verify_race (+ `--scenery-only`), rib_check, house_seat_check all PASS and identical), except verify_race G's lamp margin
(below).

| Change | Where | Before → after | Flag |
|---|---|---|---|
| `[LIGHT_N]` clustering of the LIGHTS vertices | `scripts/ac/ext_config.py` `lamp_clusters` (airoso only: the ship chain's `track_folder` runs airoso's writer; engine-july's copy has long diverged and is not snapshotted) | fixed 5 m `(x // 5, z // 5)` buckets → single-linkage at `LAMP_LINK_M` **2.0 m** (horizontal), centroid of the DISTINCT vertex positions | [invented] 2.0 m: lamps stand ≥ 25 m apart (build_streetlights), a lens is < 0.6 m. The bucket rule split a lens that straddled a bucket edge into two lights at one lamp — v0.18.0 shipped 4 such pairs (ledger 0043: LIGHT_17/18, 169/170, 229/230, 231/232) and a 0.52 m LED lens would straddle ~1 in 6. Lake Murray: 243 → **239** lights = one per lamp; the four lamps that ran two lights now run one |
| verify_race G mast footprint | `tools/verify_race.py` `lamp_model_info` | radius of `lamp_post.obj`'s base at POST_H (0.585 m) for every model → the SELECTED model's: `assets/models/streetlight_led.json` `mast_radius_m` **0.124 m** for `led_cobra` (the pole's buried foot), unchanged for the default | measured off the model. Lake Murray minimum mast margin 2.364 → **2.825 m**, 0 inside (the bases did not move: base = head − `ARM_M` road-ward, as before) |
| road datum under each LED lamp | `tools/author_lamps_blend.py` `HEAD_ABOVE_ROAD_M` | — → **8.944 m** below the recorded head | measured, not invented: ledger 0043 found the 2026-10 light 6.94 m over the nearest road vertex, and that light sat 2.004 m under the head (the author's own geometry). Re-measured on the rehearsal's gate OBJ the 2026-10 light stands 6.61 m (p10–p90 6.50–6.65) over the nearest 1ROAD vertex today, so the LED lens is **11.48 m** over it (light 11.33 m, p10–p90 11.21–11.37), not the nominal 11.81 m — still inside the 35–40 ft band; recalibrating the datum is one constant |
| LED LIGHTPOST batching | `tools/author_lamps_blend.py` `LAMPS_PER_MESH` | `CAP` 60,000 vertices per mesh → **16** lamps per mesh | [invented] for culling: ~0.9 km of loop per mesh (15 meshes, max 5,914 render points; none near the 65,535 cap) |
| mounting height / pole / arm | `tools/make_streetlight_led.py` | 2026-10 lamp: 11.5 m model, light 6.94 m, head 1.6 m road-ward → pole **10.67 m** (35 ft), arm **3.66 m** (12 ft), lens **11.81 m** (38'-9") over the road datum, 4.04 m road-ward | sourced: Caltrans Standard Plan ES-6A (Type 21 = 35 ft pole; mounting height 38'-9" with the 12 ft arm, Type 15 + 12 ft = 33'-9"); City of San Diego SDE-101 (arm 12 ft for the steel standard; its own table tops out at 30 ft for the 250 W HPS / 180 W LPS arterial lamp). Lens offset per lamp, in its own frame: **+2.440 m road-ward, +4.718 m up** (recorded in `data/lights.local.json` `provenance`; measured on the written ini: 2.424–2.457 / 4.710–4.720, along-road ±0.017) |
| lamp render budget | `tests/tools/test_streetlight_led.py` | — → twin + lens ≤ 300 shared-normal corners (the Blender/exporter count adds MikkTSpace tangent splits: measured 365.7 + 5.7 = **371 kn5 render points per lamp** against 4,045) | [invented] ceiling, set ~10 % over the generated model so a later edit that doubles it fails |

**The light settings did not change** (ledger 0043's `lighting.streetlight`, Kevin-approved). `tools/streetlight_pool.py`
measures the road under CSP's documented terms — range plateau to `RANGE_GRADIENT_OFFSET × RANGE` then a fade
(`linear` = 0043's reading, `quadratic` reported beside it; CSP's exact curve is not public: [invented model shape]),
the spot term `(cos θ − cos(SPOT/2)) / ((1 − cos(SPOT/2))(1 − SPOT_SHARPNESS))`, and `DIFFUSE_CONCENTRATION` as
`(1 − c) + c cos θ`. On the written v0.18.0 vs rehearsal inis: **under each lamp 0.972×** (1.004× predicted lamp for lamp —
the 2.8 % is the four doubled lights gone), **between lamps dark both** (5 % → 3 % of mid-block stations lit; mean 1.2 % →
0.2 % of the under level), so intensity stays **0.013**. What the taller source does change, recorded for Kevin's seat:
the pool flank 8–14 m from a lamp is 1.15× (quadratic) to 1.45× (linear) brighter and the lit road 1.42–1.67× on average,
while the range sphere's ground radius shrinks 24.0 → ~22 m. Levers if the seat reads it as brighter: intensity 0.0091
(quadratic) / 0.0078 (linear) matches the road average at the cost of the core under each lamp; `range_m` 26.7 restores
the 24 m footprint.


## 2026-10-14 — road_datum PROFILE WINDOWS + Lake Murray Blvd's decks + the assembler's per-window sigma_y (ledger 0057)

Kevin (v0.18.0): "my cars with clutches would roll back from stoplights there ... Stoplight would be heading onto Alvarado
from college." The diagnosis (ledger 0057) measured the two uphill waits flattened by two stacked smoothings of the frozen
pre-median profile (the August heightfield's 33 m median + 2 x 39 m box means + lap-seam blend, then the assembler's
sigma_y 5 Gaussian, ledger 0042): College southbound into the Alvarado signal +3.5 % built against +5.9 % real, Alvarado
from 70th -6.1 % against -7.7 %, the 70th junction 0.7 m low behind Lake Murray Blvd's 1.2-2.1 m-low decks. **No gate
threshold, bypass or exclusion changed.** This is a datum change, opt-in per declared window; outside every window the
assembler's profile is byte-identical to its sigma_y 5 result on the same input (and on the College main descent
identical to v0.18.0).

| What | Value | Flag | Why |
|---|---|---|---|
| `tools/deck_datum.PROFILE_SIGMA_M` | 3 m | [invented] | Gaussian on the 1 m 3DEP profile inside a window (= 1 centreline vertex): rounds the DEM's +-10 cm sample noise. Swept 2 / 3 / 4 / 6 m (simulated on both windows, ledger 0057 Fix): 6 m (the diagnosis' "sigma ~2 points") cost the two stop-line approaches another 0.07 / 0.21 points and bought nothing the gates need |
| `tools/deck_datum.PROFILE_BLEND_M` | 30 m | [invented] | default blend into the old profile at each window end (`road_datum.profiles[].blend_m`); both window ends sit where old and fresh agree within ~0.2 m |
| profile reference | mean of 3DEP at both carriageway centres (+-width/4 off the line) | measured choice | the line itself reads the crown: on College's approach the centre line runs +5.3 % where both lanes run +5.8-5.9 %; the mean of the two carriageway centres reads the lanes |
| deck spans inside a window | held straight between abutments, one-sided `SMOOTH_M` reads (the deck rule) | reused | a profile never reads the I-8 trench or Alvarado Creek |
| `road_datum.profiles[].hold_straight_m` (new key) | College/Alvarado: pre-median s 2289-2323 | measured (rehearsal 1) | the hairpin's levelled fold fan (rows 763-774, ledger 0050) pinches its inside edge to ONE height and cannot carry the real hump: with the hump in it the first full rehearsal failed `verify_fold_fans` (DT 0.087 m > 0.06 on the inside paths, all three layouts) and doubled drive_test's severe steps there (race 22/20 -> 39/37). Held straight like a deck span it passes (DT 0.028-0.034) |
| `road_datum.profiles[].assembler_sigma_y_pts` | 1.0 pts College/Alvarado, 1.5 pts 70th/Alvarado | [invented], rehearsed | inside a window the input is already fresh 3DEP smoothed at 3 m, which is what 0042's sigma 5 was written for. Rehearsed: 1.5 / 1.5 -> College stop line +5.23 %, every listed gate no worse than v0.18.0; 1.0 / 1.0 -> +5.44 % but street kinks 3.41 -> 3.56 /km (refused); 1.0 / 1.5 -> +5.44 %, street kinks 3.34 /km, every listed gate no worse (shipped) |
| `road_datum.profiles` (Lake Murray) | `college_alvarado_junction` pre-median s 2200-2530; `seventieth_alvarado` 13280 -> seam -> 230 | measured | fresh 3DEP 1 m, 2026-10-14 (data/deck_datum.samples.json, TLS on) |
| `road_datum.decks` (Lake Murray, added) | `lmb_over_i8` 13347-13424 (126.2 -> 126.2 m), `lmb_over_alvarado_creek` 13432-13457 (126.2 -> 125.6 m) | measured | the item ledger 0046 deferred: fresh 3DEP abutments at both carriageway centres; both lie inside `seventieth_alvarado`, which holds them (their own window pass is skipped and reported `re_derived_by_profile`) |

Refusals (SystemExit, no silent fallback): a profile window cutting a deck span; a hold inside the window's blend; a
window shorter than twice its blend or not shorter than the lap; a seam window on an open line; an uncached 3DEP sample
under `--offline` (L2). The closing duplicate vertex is v0's height, never a second vertex (L13). `smooth_centerline`
refuses a weight list that is not one per unique vertex.

Wiring: none new — `tools/deck_datum.py` is already the first draft step (ship_sd.sh / ship_track.sh) and its cache
already rides TERRAIN_DATA; `scripts-v021/blender/build_loop_blend.py` reads the same `road_datum.profiles` (stations on
the pre-median file, index-aligned with raw.local) and passes `y_sigma_windows` only when one is declared.

Gates on the shipped config (full `ship_sd.sh --no-install` rehearsal, v0.18.0 -> this): street soft top 33 -> 31,
severe 0 -> 0, kinks 3.41 -> 3.34 /km, audit D/K/I/F 0/20/20/13 unchanged; race severe 22 -> 17 / 20 -> 17,
barrier_missing 0, no_route BUILT PASS both; verify_fold_fans, verify_mouths (4), verify_signs, verify_race,
verify_ai_line (both), rib_check, house_seat_check PASS. Not on the list and slightly up: race_cw kinks 6.23 -> 6.45 /km
(race_acw 7.05 -> 6.38) — reported, not gated.

Proven by `tests/tools/test_profile_datum.py` (a seam window on a closed ring moves both sides, keeps v0 closed, leaves the
rest untouched, is idempotent; a deck inside a profile is held by it; a hold is straight and refused inside the blend;
offline refuses a gap; the assembler's windows are exact outside and keep a crest inside; Lake Murray's declaration
resolves and runs offline from the committed cache to the real grades) and the rehearsal in ledger 0057 Results.

### Fix round (2026-10-14, after the refutation): the fold-fan fit replaces the held box

The truth lens refuted round 1 on its own stop-line range: `hold_straight_m` held the College/Alvarado junction box
(pre-median s 2289-2323) straight, so the crest sat 0.55 m under the real road centre (1.15 m under the southbound
lane) and a car stopped a few metres into the box got a much shallower hill than real (last 15 m to s 2305: built
+2.92 % against a real +7.16 % on the lane). Cause, measured on a model of the ribbon that reproduces the built gates
(the fan model read 0.0868 / 0.0342 m where `verify_fold_fans` read 0.087 / 0.034 on rehearsals 1 / 4; the
drive_test replica read rehearsal 5's 10 street severe steps at the same stations and heights to 1 mm): two gates
judge this corner on paths a tight hairpin bends out of shape. Every wheel path inside the fold fan folds and is cut at
its own self-intersection, so it turns sharply at a point on the corner's medial axis and its grade jumps there by
the surface's slope along the axis; and drive_test's fixed-offset wheel paths jump sideways where the segment normal
turns. The real crest inside the fan fails both (fan DT 0.076-0.087 m; with the fan alone fitted, rehearsal 5: street
severe 0 -> 10, kinks 3.41 -> 5.86 /km, race severe 22 / 20 -> 27 / 26). The box passed both by removing the crest.
**No gate threshold, bypass or exclusion changed.**

| What | Value | Flag | Why |
|---|---|---|---|
| `road_datum.profiles[].hold_straight_m` | removed (code and config) | — | replaced by `fold_fan_fit` |
| `road_datum.profiles[].fold_fan_fit` (new key) | College/Alvarado: `fit_m` pre-median s 2250-2340, `dt_max_m` 0.05 | `fit_m` measured; `dt_max_m` [invented] | inside `fit_m` the profile takes the change with the smallest misfit to the 3DEP target (heights, grades, grade changes, on the heights the assembler will build) that keeps (1) every levelled fold pinch within `dt_max_m` on `verify_fold_fans`' own `survey_pinch` and (2) drive_test's wheel paths over `fit_m` +- 10 rows (street; a race lane both ways) at no severe step and no more kinks, nor kink excess, than the frozen profile had there as v0.18.0 built it — read on the ribbon the build will carry (the assembler's own smoothing: 5e-5 m from the built centreline; `mouth_weld.unfold_line` levelled; drive_test's own constants). Outside `fit_m` nothing moves. `fit_m` ends at 2340: a fit reaching 2360 steepened College's flank into a sag at s 2328-2346 where the seated ground's 10 m facets came up through the road by up to 9 mm (drive_test soft tops street 33 -> 39, race 9 -> 21 / 19; rehearsal 6) |
| `tools/deck_datum.FAN_DT_MAX_M` | 0.05 m | [invented] | the gate's `DT_MAX_M` 0.06 less 0.01 for the model |
| `FAN_COARSE_MARGIN_M` | 0.003 m | measured | the solver surveys the pinches at 0.5 / 0.1 m (the gate: 0.25 / 0.05); that read up to 0.0029 m under the full survey; it solves to 0.047 and the full survey of the result must meet 0.05 |
| `FAN_BUMP_SPACING_M` / `FAN_BUMP_SIGMA_M` / `FAN_TAPER_M` | 6 / 4.5 / 12 m | [invented] | Gaussian bumps ~2 vertices apart, never one vertex; faded to zero at both ends of `fit_m` |
| `FAN_GRADE_WEIGHT_M2` / `FAN_BEND_WEIGHT_M2` | 100 / 400 m^2 | [invented] | the misfit weighs a 1 % grade error like 0.1 m of height and a 1 % grade change between neighbouring vertices like 0.2 m: on heights alone the fit steepened College's last 15 m to the stop line 1-1.5 points past the target |
| `FAN_WHEEL_PAD_ROWS` | 10 rows | [invented] | drive_test's wheel paths are walked over `fit_m`'s rows +- 10 (~30 m) |
| race lane for the wheel paths | the full street between the edge strips, `w/2 - race.edge_inset_m` (0.82) each side | measured | the declared corridor is that box through the hairpin (barrier_bands `lane_by_vertex` +-14.18 at w 30); the declaration itself is authored later in the chain |
| `FAN_STEP0_M` / `FAN_STEP_MIN_M` / `FAN_PENALTY` / `FAN_COUNT_PENALTY` / `FAN_MAX_EVALS` | 0.16 / 0.01 m / 1e7 / 1e3 / 2500 | [invented] | deterministic coordinate descent from zero, one step per coordinate per sweep, halved to 1 cm; every constraint a hard wall |
| `FAN_MAX_MOVE_M` | 0.25 m | [invented] | a fit that moves a built height further than this from the 3DEP target is refused (a pattern-search variant of the descent settled 0.6 m off on Alvarado's leg; not shipped) |
| 3DEP read position inside `fit_m` | the plan the assembler builds (its smoothing of the line), tapered over `FAN_TAPER_M` | measured | round the hairpin the assembler's plan smoothing moves the line up to 3.6 m and the junction tilts 8 % across: read on the pre-median plan, the slab sat 0.1-0.3 m off the real road under the built one. Outside `fit_m`: the pre-median plan, as before (median_envelope moves divided roads after this step; no median reaches a fold fan) |
| `road_datum.assembler_smooth` (new key) | `tracks/san-diego-lake-murray/scripts-v021/geometry/smooth.py` | wiring | the module the fit predicts the build with; a `fold_fan_fit` without it is refused |
| `fold_fan_fits` in data/deck_datum.samples.json | the solved bump amplitudes, keyed by the md5 of everything the solve reads | cache | a solve takes 3-5 min; a hit is re-surveyed in full like a fresh solve (rehearsals 5-7 hit it; a fresh solve reproduced the cached amplitudes and the pre-median output byte for byte); the file already rides TERRAIN_DATA |

Refusals (SystemExit): `fit_m` inside the window's blend; no `assembler_smooth`; a fit that cannot meet the fan target
(solver or full survey), a fine step on the pinch paths, a severe step or extra kinks on the wheel paths, a move past
`FAN_MAX_MOVE_M`, a pinch reaching past the surveyed rows, a pinch the weld would refuse (half-jump, cross-fall) — each
says "author the junction as a pad (JUNCTIONS 2.0 B)".

Level slab, the reason now measured: the race layouts run the junction's full width and the race walls' containment
is judged against the centre line (no_route BUILT, `verify_fold_fans` (7): +-0.28 m); the real 8 % tilt puts the walls
1.1 m off it 14 m out.

Gates on the shipped config (rehearsal 7, full `ship_sd.sh --no-install` on fresh scratch copies, v0.18.0 -> round 1 ->
this): street soft top 33 -> 31 -> 9, severe 0 -> 0 -> 0, kinks 3.41 -> 3.34 -> 2.97 /km, audit D/K/I/F 0/20/20/13
unchanged; race severe 22 / 20 -> 17 / 17 -> 17 / 18, soft top 9 / 9 -> 9 / 8 -> 8 / 7, barrier_missing 0, no_route BUILT
PASS both; verify_fold_fans PASS (hairpin DT 0.047 street / 0.044 race, grass-on-top 0), verify_mouths (4), verify_signs,
verify_race (+ scenery), verify_ai_line (both), rib_check, house_seat_check PASS. Not on the list: race kinks 6.23 /
7.05 -> 6.68 / 6.82 /km. Rehearsals 5 (the fan alone: street severe 10, race 27 / 26) and 6 (`fit_m` to 2360: soft tops
39 / 21 / 19) were refused by these same comparisons. The built profile against fresh 3DEP is in ledger 0057.

Proven by `tests/tools/test_profile_datum.py` (a crest in a synthetic hairpin's fold fan is carried, the fan within
`dt_max_m`, drive_test's street paths no worse, nothing outside `fit_m` moved, the cache re-used to the same bytes; the
refusals; Lake Murray's declaration and its committed cache).

**Round 3 (same day, after the second refutation): no threshold, constant or config changed.** The truth lens refuted on
stops at s 2305-2309, which lie inside the intersection box: College's southbound signal is at s 2312.3 and Alvarado's at
s 2273.2. I re-ran the fit offline with each limit relaxed in turn, to find the bound; the table is in ledger 0057 round 3.
- `dt_max_m` 0.05 -> 0.057: no change. The fan settles at 0.047 either way, so it is not the binding limit.
- drive_test's kink cap round the hairpin is the binding limit. Freeing it buys ~1 point at s 2305-2308. The cost is
  street kinks/km past v0.18.0 (2.97 -> ~4.2, against 3.41) and race kinks ~2.5x at the corner.
- No gate at all: a level slab still misses s 2305 by 0.8 points on 15 m. That needs crossfall, which the race-wall band
  (`WALL_BAND_M` 0.28 about the centre line, no_route BUILT) forbids above ~2 %.

None of these variants shipped, and `FAN_DT_MAX_M` stays 0.05.


## 2026-10-14 — v0.18.1 integration: 0055 + 0056 + 0057 on one build; named lamp relocations (ledgers 0055, 0056, 0057)

Three branches merged (College 0055 `a4e2a81`, LED lamp 0056 `4992d16`, hills 0057 `ed6b98b`), `track.config.json`
`version` 0.18.1. **No gate threshold changed.** One new authoring self-check, for the verifier-found lamp placements:

| Change | Where | Before → after | Flag |
|---|---|---|---|
| named lamp relocations | `tools/author_lamps_blend.py` RELOCATIONS + `tools/streetlight_relocate.py` (pure, tested); `track.config.json` `scenery.streetlights.relocate` | every post where the draft put it → six named posts moved (lamp 53 off a junction carriageway onto the sidewalk; lamps 30 / 32 / 34 / 43 out of `1WALL_guard_release`; lamp 237 = 0057's LIGHTPOST_8 off the raised creek deck onto its embankment). `data/lights.local.json` keeps `lampheads_draft` + `relocated`; every downstream reader (place_signs, verify_race G, ext_config through the lens) sees the moved post | self-check, exit 1 and `loop.blend` not saved: the named post must exist, the new base must not be on a road surface, the pole must stand **≥ 0.5 m** from every wall / guardrail (`WALL_CLEAR_M`, the integration brief's number), the pole foot must be in the earth |
| how a post is named | `MATCH_TOL_M` | — → **1.0 m** around the draft's base | [invented] lamps stand ≥ 25 m apart (build_streetlights), so 1 m names exactly one; a draft that moves a named lamp further fails the build loudly |
| how far a relocation may go | `MAX_MOVE_M` | — → **15 m** | [invented] a nudge to the right spot, not a new lamp (used: 1.0 / 1.0 / 1.0 / 1.0 / 6.3 / 10.4 m) |
| seat "ground" | `HEAD_OVER_GROUND_M` | — → **8.8 m** head over the ground under the post | sourced: build_loop_blend.build_streetlights' own rule (9.0 m post − 0.2 m) |
| "on a road surface" / "foot in the earth" | `relocate()` | — → road top within **0.3 m** of the ground top under the base; earth ≥ foot + **0.05 m** | [invented] tolerances |
| the barrier lamps' move | config | — → **1.0 m** straight away from the road, behind the rail, light height kept (`seat: keep`) | [invented] measured clearance after: 0.67–0.68 m (≥ 0.5 m) |

**Gates, full rehearsal r2** (`ship_sd.sh --no-install`, fresh scratch copies D:/k10-scratch/v0181/r2/{project,
engine-july}; no snapshot file differed) against v0.18.0 (the shipped workshop reports):

| | v0.18.0 | v0.18.1 |
|---|---|---|
| street soft top / severe / kinks /km / bumps /km | 33 / 0 / 3.41 / 0.0 | **8 / 0 / 2.97 / 0.0** |
| street excursions (gated) / floating / daylight / obstruction | 98 / 391 / 0 / 0 | **100** / 391 / 0 / 0 (below) |
| audit street / race_cw / race_acw (D/K/I/F) | 53 / 53 / 53 (0/20/20/13) | 53 / 53 / 53 (0/20/20/13) |
| race severe cw / acw | 22 / 20 | **15 / 20** |
| race soft top cw / acw | 9 / 9 | 8 / 4 |
| race barrier_missing / obstruction | 0 / 0 | 0 / 0 |
| no_route BUILT + PLANNED, both | PASS, leak 0 | PASS, leak 0 (0/411 probes) |
| verify_mouths ×4, verify_fold_fans, verify_ai_line ×2, verify_signs (23), verify_race + `--scenery-only`, rib_check, house_seat_check, verify_kn5 + `--inis`, check_race_kn5, check_street_kn5 | PASS | PASS |
| not gated: race kinks /km cw / acw | 6.23 / 7.05 | 6.90 / 6.23 |

**The one higher gated count — street excursions 100 vs 98 — explained place by place** (every gated excursion mapped to
its centreline vertex on both builds; `drive_test` samples one crossing every 150 m from station 0, and 0055's registration
re-stations everything downstream of College): −4 at College v1302 / v1352 (the 0055 fix; the island and lanes moved
onto the real road); +4 at v1753 and v2755, −1 at v2103, −1 at v4306 — the same 0.13–0.14 m
sidewalk-back ledges v0.18.0 has at those places, met or missed by the shifted stations (v0.18.0's own mesh sampled on
this build's downstream stations reads 102, with all of these); +2 at v3806, where the mesh and widths are byte-identical
(w = 18.91 m, a junction flare's taper) but `drive_test`'s flare exemption is `widths[i] > median(widths) + 1.5` and
College's one continuous divided run raised the lap's median width 17.00 → 17.64 m (exemption 18.5 → 19.14 m); and
+4 / −2 at v4457 / v4454 — **CORRECTED in the fix round below**: this was first filed here as more sidewalk-back ledges
with "no geometry is worse", which was wrong. Two of v4457's four are 6.05 / 6.32 m deck-edge drops on Lake Murray Blvd's
I-8 overcrossing, 1.4–1.9 m taller than v0.18.0's at every vertex v4455–4473, because 0057 put that deck at its real
3DEP height; they sit behind the deck's bridge rail, which `drive_test` could not see (fix round).
Race severe, place by place: cw −4 Alvarado v5, −4 College/Alvarado junction (0057), −1 Navajo v1514 (0055), +1 LMB
v3300, +1 the 70th seam fold fan v4495–4497 (0057's raised deck); acw −2 Alvarado, −2 junction, +4 the 70th seam fold fan
(0057, outermost fixed paths at ±11.8 m — flagged by 0057's gates lens for Kevin's Speedway drive).

**What else changed with the merge** (not gates): College's registration shortens the lap 6.565 m, so the draft's 55 m
lamp spacing re-stations every lamp after College (~6 m along) and the last post before the seam drops: **238** lamps /
`[LIGHT_N]`, not 239 (0055's own build already had 238). verify_race G lamp margin 2.825 → **2.741 m** (lamp 120 vs
`closure_race_acw`, re-stationed by 0055). Road kn5 **73.57 MB** (73,574,557 B; 834,667 v / 1,229,616 tri) against
116.3 MB in v0.18.0 and 72.7 MB on the lamp branch alone (818,510 v there: LIGHTPOST 87,403 → 86,881 v with one
lamp fewer, the other +16.7 k vertices are 0055 / 0057 geometry); LIGHTPOST 15 meshes, 365 render points per lamp, the
largest mesh 5,923 v; LIGHTS_0 1,350 v. `[LIGHT_N]` 238, `COLOR = 255, 165, 30, 0.015` in every block; each light 0.146–0.155 m
under its lens, the six moved lamps' lights moved with them and no other.

### Fix round (2026-10-14, after the gates / runtime / view lenses refuted r2): the guard probe sees a panel rail; lamp 53 off the curb line

Two findings, each fixed at its cause; full rehearsal **r3** (fresh scratch copies D:/k10-scratch/v0181/r3/{project,
engine-july}, no snapshot file differed, `--no-install`; it ended EXIT 1 / NOT INSTALLED, exactly as v0.18.0 and r2 did).

| Change | Where | Before → after | Flag |
|---|---|---|---|
| excursion guard: a wall the car's path passes THROUGH | `scripts/geometry/drive_test.py` (`_wall_crossed`, the excursion sweep) | a drop counted as guarded only when the downward `top_at` probe (every 0.5 m out from the lane edge) landed on a 1WALL. A vertical panel has no plan area, so the probe can never land on one → a drop is now also guarded when the straight path from `max(we − 0.4, 0.5)` to `off − 0.25`, **WALL_CROSS_H_M** over the pavement edge, crosses a 1WALL triangle (Möller–Trumbore). The rule text is unchanged ("ANY 1WALL between the pavement edge and the drop guards it"), and so are the thresholds, step, band and flare rule. A wall too low (top under edge + 0.5 m), or one standing beyond the drop, still guards nothing | **WALL_CROSS_H_M = 0.5 m [invented]**: above a wheel centre (~0.3 m) and below every barrier top the loop builds (0.81 m Jersey `1WALL_guard_release`, 0.95 m bridge panel `1WALL_guard`). Test: `tests/geometry/test_drive_test.py::test_a_vertical_panel_rail_guards_the_deck_edge_drop_v0181`. In it a bare deck is gated, a panel-railed deck is not, and a 0.3 m panel or a panel past the drop is still gated. The pre-fix gate gates the railed deck (checked) |
| lamp relocation self-check: the whole footprint | `tools/author_lamps_blend.py` `footprint_on_road` | the base POINT was ray-cast against ROAD, so lamp 53 passed with its axis 2 cm onto the curb and its 0.124 m pole 0.10 m over the asphalt → now the axis plus a ring of radius mast + **ROAD_SETBACK_M** in **16** directions, each read down from 1 m over the ground. Any point whose top surface is a ROAD fails (exit 1, loop.blend not saved) | **ROAD_SETBACK_M = 0.46 m**, sourced: the AASHTO Roadside Design Guide's 1.5 ft minimum lateral offset from the curb face on curbed streets (cited from memory, not re-read). **FOOTPRINT_DIRS = 16 [invented]**: 22.5°, so a 0.58 m ring's chord is 0.23 m |
| lamp 53's spot | `track.config.json` relocate entry | (−1450.13, −533.51), on the curb line → **(−1447.2, −531.8)**, mid-slab on the junction corner: axis 1.30 m from the nearest road surface and 1.04 m from the slab's back edge (r2 track.obj, 0.1 m raster). The move from the draft's base is 12.08 m (≤ 15) | measured |

**Why the probe change is a measurement fix, not a loosening.** The loop's I-8 bridge rails (`scripts-v021`
`build_guardrails`) are double-sided 0.95 m vertical panels, standing on the curb 0.15 m outside the lane edge. On Lake
Murray Blvd's deck they are at ±6.90 m, with the deck at 25.36 m and the rail from 25.36 to 26.31 m. `TriField.top_at`
skips every triangle with zero plan area, so the sweep's guard probe has never been able to land on one. Every drop
behind those rails read "unguarded", in v0.18.0 as well. Each gate was measured with a dump-patched copy of itself: the
new one in D:/k10-scratch/v0181/fix2, the old one from the gates lens's own dumps in D:/k10-scratch/v0181/verify_gates.

| street excursions, gated | old probe | new probe |
|---|---|---|
| v0.18.0 mesh (its own stations, median 17.00) | 98 | **96**. The 2 credited are v4454 ±10.5 m, on the LMB I-8 deck behind its rail |
| r2 / r3 mesh (identical road geometry) | 100 | **96**. The 4 credited are v4457 ±9.5 m (0.14) and ±10.0 m (**6.05 / 6.32 m**), on the same deck behind the same rail |
| dense sweep, every vertex, r2 mesh | 4,786 | 4,686. 100 are credited, all behind a crossed 1WALL: v4452–4473 (the LMB I-8 deck's panel rail), v4480–4483 (the creek deck's Jersey), and v695–698 / 710 / 828–831 (Alvarado's `1WALL_guard_release` Jersey rails at −11.9…−12.5 m, whose tops stand outside `top_at`'s ±2.5 m window). 0 are newly gated |
| dense, gated drops > 0.5 m (not holes) | v0.18.0 44 (max 5.09), r2 42 (max 6.82) | v0.18.0 6 (max 1.57), r2 4 (max 1.52) |

So the brief's comparison holds on either gate. Under the corrected probe it is **96 against 96**. Under the old probe
r3 reads 100 against 98, and every extra entry is a sampling station, the flare median, or this deck.

**The deck geometry.** 0057's `road_datum.decks` `lmb_over_i8` holds Lake Murray Blvd at its real 3DEP road height:
126.2 m at both abutments, where the pre-median deck ran 1.2–2.0 m low. The drop from the deck edge to the real I-8 floor
(119.3–120.1 m on 3DEP) is therefore 6.0–6.8 m, where v0.18.0's was 4.4–5.2 m. It is taller because it is true, and it
is behind the bridge rail.

**Not gated on either build, and not changed:** the sweep's NO-SURFACE holes (9.99: no surface within 8 m of the deck) at
the creek deck's far end, v4478–4484. In the dense sweep they rise from 4 to 10, because the deck now stands 8.3–10.5 m
over the real creek bed (115.7–117.9 m on 3DEP). They lie behind the creek deck's Jersey rail (−10.0…−10.6 m), but the
hole branch takes no guard credit and this round does not change that. Neither 150 m sweep samples them. The worst gated
street excursion on r3 is 1.52 m at v701, as on r2 (v0.18.0: 1.57 m).

**Gates, r3 against v0.18.0.** r3 equals r2 in every number except street excursions. Its road geometry, centreline,
widths and `median_bands.json` are byte-identical to r2's.

| Gate | v0.18.0 | r3 |
|---|---|---|
| street soft top | 33 | 8 |
| street severe | 0 | 0 |
| street kinks /km | 3.41 | 2.97 |
| street bumps /km | 0.0 | 0.0 |
| **street excursions** | **98** | **96** |
| floating / daylight / obstruction | 391 / 0 / 0 | 391 / 0 / 0 |
| audit, all three layouts | 53 (D 0, K 20, I 20, F 13) | 53 (D 0, K 20, I 20, F 13) |
| race severe, cw / acw | 22 / 20 | 15 / 20 |
| race soft top, cw / acw | 9 / 9 | 8 / 4 |
| race excursions / barrier_missing / obstruction | 0 / 0 / 0 | 0 / 0 / 0 |
| no_route BUILT + PLANNED, both | PASS | PASS (leak 0, 0/411 probes) |

These also pass on r3: verify_mouths ×4, verify_fold_fans (3 × 3), verify_ai_line (wall minimum 2.542 / 2.384 m),
verify_signs 23, verify_race and `--scenery-only`, rib_check, house_seat_check, verify_kn5 and `--inis`,
check_race_kn5, check_street_kn5.

The verify_race G lamp margin is now **2.435 m**: lamp 53 at its new corner, 16.9 m off College's race edge strip (r2:
2.741 m, lamp 120). 0 masts stand inside a strip. Road kn5 is 73,574,689 B (834,670 v / 1,229,616 tri). There are 238
`[LIGHT_N]` blocks, all `255, 165, 30, 0.015`; from r2 to r3 only `[LIGHT_59]` (lamp 53's lens) moved.

**Lamps on the BUILT r3 split scenes.** Three audits were run (the integrator's lamp_audit, and the view lens's
pole_audit and road_gap; output in D:/k10-scratch/v0181/r3audit). Across 238 poles:
- 0 axes are over 1ROAD and 0 pole edges are over 1ROAD.
- 0 feet are in the air.
- 0 poles are less than 0.5 m from a 1WALL.
- The nearest pole SURFACE to any road top surface is 0.816 m (lamp 119, unmoved).
- Lamp 53 is now 1.156 m from the road (axis 1.28 m); on r2 it was −0.104 m.

Lamp 53's road-ward lens (east) now hangs over College's carriageway instead of running along the curb.

### Fix round 2 (2026-10-14, after the gates lens refuted r3): race bumps re-measured on the wheel's own travel; the lap seam's chord graded

The gates lens refuted r3 on one gated metric: race_cw `steps_per_km` 4.38 -> 5.20 (59 -> 70 counted 2.5-6 cm bumps),
absent from the r2 / r3 tables above. Both causes are fixed. Full rehearsal **r4** (fresh scratch copies
D:/k10-scratch/v0181/r4/{project, engine-july}; no snapshot file differed; `--no-install`; it ended EXIT 1 / NOT
INSTALLED, the v0.18.0 pattern).

**Diagnosis, every counted bump on both builds** (drive_test with a per-step dump, D:/k10-scratch/v0181/bumps). Most
of r3's 70 sit where a fixed-offset wheel path HOPS at a centreline vertex: it jumps forward round the outside of a corner
(1.8-3.9 m at 10-13 m out) or creeps on the inside (0.1-0.6 m). The bump rule compares the height change over that hop
with the one over the previous metre, so a plane at grade g reads g x (hop - 1): 3.4 cm on the 1.25 % Navajo / Jackson
plane at s 6954, already in v0.18.0. Ledger 0057's real grades (+5.9 % into the College light, -7.7 % off 70th) made
the same hops read more. Re-measured on the wheel's own travel, 60 of r3's 70 read under 2.5 cm and 10 stay over (v0.18.0: 4 of 59 stay over). Six
of those 10 were at the lap seam's exit (s 12-14, -5.8 / -6.5 m), on a sliver the weld built: the seam's hook (the 27.5
-> 17 m width step, rows 4496 -> 5) is bridged by a forward chord whose rows kept their OWN heights. Rows 1-4 bunched
into about 2 m of chord at 24.465-24.491 m, with row 5's own edge 0.78 m on at 24.405 m: a 6-9 cm drop in under a
metre. Along the same wheel path v0.18.0's mesh reads -2.8 / -17.8 / -11.4 / -3.4 % in 0.1 m steps. It is the fold
mend's own sliver, made worse by the real grade behind it.

| Change | Where | Before -> after | Flag |
|---|---|---|---|
| VERTEX BUMPS: a 2.5-6 cm bump is re-measured on the wheel path's own travel (the grades of its two metres over the plan distance each covered, their change over the mean of the two, x STEP_M^2). Under 2.5 cm it is reported (`vertex_bumps`, with its re-measured value), not counted in `steps_per_km`; still over, it counts | `scripts/geometry/drive_test.py` `_own_travel_step` (every track, every layout) | every 2.5-6 cm second difference counted as read, whatever distance each of its metres covered -> re-measured. Severe steps (> 6 cm) are never re-measured; kinks, fold bumps and apron bumps are unchanged. Where both metres cover 1 m it IS the old measure, so a straight road reads exactly as before | **VERTEX_MIN_TRAVEL_M = 0.05 m [invented]**: a metre covering less plan than this is not re-measured (a grade over a few cm is facet noise) and the bump counts as read. Test `tests/geometry/test_drive_test.py::test_a_plane_round_a_polygon_corner_reads_vertex_bumps_not_gated_bumps_v0181`: a 5 % plane round a 10-degree polygon corner reads 92.4 bumps /km under the old measure (17 bumps, 0 severe) and 0 counted + 17 vertex bumps under the new (re-measured 1.6-2.1 cm); a real 5 cm crease on a straight still counts (30 /km, 0 vertex bumps) |
| the levelled MAINLINE's forward chord carries its own straight grade | `tools/mouth_weld._grade_chord` (called from `unfold_line` when `level`: the weld's MAINLINE, deck_datum's fan prediction, verify_fold_fans' re-find) | each chord row at its own row's height -> at the height of E[k] -> E[l + 1] at its plan fraction of the chord. Plan positions unchanged; connectors and paint (level off) unchanged; the paint is re-laid on the deck as before | refused (WeldError, the build stops) where a row would tilt more than `FOLD_LEVEL_XFALL_MAX` (4 %, [invented] in 0050) against its own height over its distance to the centre row. Tests: `tests/tools/test_mouth_weld.py::test_level_grades_a_forward_chord_straight_and_refuses_a_steep_tilt_v0181`, and test (g) re-stated |

**Why the re-measure is a measurement fix, not a loosening.** The v0.18.0 FOLD BUMPS entry above recorded that forward
samples on the real 3DEP plane also read bumps "from the stations' changing spacing round a corner" and left them
counted, because that rule was a blanket exemption for the backwards case. This is not an exemption: every bump is
measured again over the distance the wheel actually covered, and only a bump that is under 2.5 cm on that measure leaves
the count. A plane reads zero, a real crease reads what it always read, a severe step is untouched, and nothing can be
added to the count. Measured both ways on both meshes:

| race bumps counted (phase 0, the shipped sampling) | race_cw | race_acw |
|---|---|---|
| v0.18.0 mesh, old measure (as shipped) | 59 (4.38 /km) | 91 (6.75 /km) |
| v0.18.0 mesh, re-measured | **4 (0.30 /km)** | **10 (0.74 /km)** |
| r3 mesh, re-measured | 10 (0.74 /km) | 7 (0.52 /km) |
| **r4, re-measured (the gate of record)** | **6 (0.45 /km)**, 60 vertex bumps | **5 (0.37 /km)**, 78 vertex bumps |
| r4, old measure | 66 | 83 |

**race_cw 6 against v0.18.0's 4, place by place.** v0.18.0's 4 are all on the seam sliver (s 8-11 at -6.5 / -5.8 / -2.9
m, re-measured 2.7-5.2 cm), now gone: the fine profile along the same path reads -1.0 / -2.4 / -2.2 / -4.3 % on r4. r4's
6 are:
- s 14, -6.5 / -5.8 m (re-measured 2.59 / 2.57 cm): Alvarado's real descent rolling off the seam corner, facet kinks
  of about 2 % per row over the 0.6 m the inside path covers.
- s 2268 / 2273, -4.8 / -5.1 m (2.67 / 3.32 cm): inside the College / Alvarado fold fan's eased leg (0057's fit).
- s 9884, -12.15 m (3.78 cm): the inside race kerb at Lake Murray Blvd v3296 (`1KERB_race_3296_in`), its 5 cm lane-side
  ramp crossed by the lane-edge path. The surface there reads the same on both builds in 0.1 m steps (the kerb kept
  rows 3291-3302; only its name followed the street boundary from v3297 to v3296).
- s 13471, -11.78 m (4.18 cm): the seam's inside race kerb (`1KERB_race_0_in`, the same plan on both builds).

None of the last four is new geometry; each is where the integer-metre stations happen to fall. Sampled at the three
other phases (stations at +0.25, +0.5 and +0.75 m, the same patched drive_test, both meshes):

| race_cw counted, re-measured | phase 0 | 0.25 | 0.5 | 0.75 | mean |
|---|---|---|---|---|---|
| v0.18.0 | 4 | 12 | 10 | 9 | **8.75** |
| r4 | 6 | 6 | 6 | 3 | **5.25** |

v0.18.0 reads the same kerbs (s 9890-9891 and 13473) and the same eased fan leg (s 2265-2275) at the other phases. On
three of the four phases r4 has fewer; on the shipped phase it has two more, none of them on new geometry.

**Gates, r4 against v0.18.0** (v0.18.0's bump rate shown both as shipped and re-measured):

| Gate | v0.18.0 | r4 |
|---|---|---|
| street soft top / severe / bumps /km | 33 / 0 / 0.0 | 8 / 0 / 0.0 |
| street kinks /km (not gated) | 3.41 | **2.67** (r3 2.97) |
| street excursions / floating / daylight / obstruction | 98 (96 on the corrected probe) / 391 / 0 / 0 | 96 / 391 / 0 / 0 |
| audit, all three layouts | 53 (D 0, K 20, I 20, F 13) | 53 (D 0, K 20, I 20, F 13) |
| race severe cw / acw | 22 / 20 | 15 / 20 |
| race soft top cw / acw | 9 / 9 | 8 / 4 |
| **race bumps /km cw / acw** | 4.38 / 6.75 as shipped; **0.30 / 0.74** re-measured | **0.45 / 0.37** (above) |
| race fold bumps cw / acw (not gated) | 45 / 49 | 56 / 42 |
| race kinks /km cw / acw (not gated) | 6.23 / 7.05 | 6.46 / 6.09 |
| race excursions / barrier_missing / obstruction | 0 / 0 / 0 | 0 / 0 / 0 |
| no_route BUILT + PLANNED, both | PASS | PASS (leak 0, 0/411 probes) |

These also pass on r4: verify_mouths x4, verify_fold_fans (3 x 3; DT max 0.047 / 0.044 / 0.044), verify_ai_line (wall
minimum 2.542 / 2.384 m), verify_signs 23, verify_race and `--scenery-only` (G lamp margin 2.435 m, lamp 53), rib_check,
house_seat_check, verify_kn5 and `--inis`, check_race_kn5 x3, check_street_kn5. Road kn5 73,574,777 B. `[LIGHT_N]` 238,
every one `255, 165, 30, 0.015`; ext_config.ini is byte-identical to r3's. Lamp audit on the built split scenes: 238
lamps / 238 lights, 0 bases over 1ROAD, 0 feet in the air, 0 poles under 0.5 m from a 1WALL. The centreline, widths,
`median_bands.json` and `lights.local.json` are byte-identical to r3's. The hills grades re-measure the same to the
hundredth, except Alvarado westbound s 0-25 -2.92 -> -2.89 % and s 0-100 -6.83 -> -6.82 % (the seam's graded edge).

## 2026-10-14 — Lake Murray expansion P0: `fetch_osm` freshness guard, `route_append`, held authored routes, `grid_grow`, the frame pin, `remap_sample_cache` (ledger 0054)

No gate threshold moves. These are the data-side guards and identity proofs the expansion's geometry phases stand on;
every opt-in is absent on every other track, and on Lake Murray every new key is either inert (read by nothing in the
ship chain) or proven bit-identical to v0.18.0 (below).

| Item | Value | Flag |
|---|---|---|
| `tools/fetch_osm.py` freshness | through `widths_from_osm._overpass` + `OSM_MAX_AGE_DAYS` 7.0 (2026-10-11 entry above): an answer older than 7 days, or without `osm3s.timestamp_osm_base`, is refused, nothing written; `--allow-stale-osm` writes it with `stale_allowed: true`. Was: three servers in turn (TLS verified), no staleness check | the 7.0 is the 2026-10-11 ⚠ invented value, reused |
| `tools/fetch_buildings_cache.py` (new) freshness | the same guard and limit | reused |
| `tools/route_append.py` (new) | append only: the existing routes must re-serialise byte-identically and stay a byte prefix of the new file; a leg's routed path must equal the spec's `path_nodes`; every edge checked against its way's `oneway` (`yes`/`true`/`1` along, `-1`/`reverse` against, `junction=roundabout` implied) | std (the real road's direction, OSM tags); the equality checks are exact |
| `tools/route_tracks.py` | refuses to rewrite an existing `data/routes.json` that differs (`--overwrite` to discard on purpose) | wiring |
| `route.route_connectors.authored_routes` (new, opt-in) | a listed route is HELD: no constant-width connector is drawn from it (`north`, until P1's intermediate + P3) | wiring; proven byte-identical (`tests/tools/test_route_connectors_held.py`) |
| `terrain.grid_grow` (new, opt-in; scripts-v021 `heightfield.py`) | whole cells; `rows_n` must equal `rows_s` (the meta's mid-latitude sets every consumer's column spacing); old nodes sampled by the same float expression | exact; the 37 / 37 / 26 / 0 sizes are the plan's, checked against the north route's kept cells (119.9 m / 120.5 m to spare) |
| `tier_options.frame.pin` (new, opt-in; `terrain_tiers.Frame.heightfield`) | the meta's recorded `grid_grow` must equal the pin's offsets; the meta's anchor within **1e-6 deg** (+1e-12) of the pinned anchor shifted by whole cells | 1e-6 deg derived: a meta bbox rounded to 6 decimals is within 5e-7 deg of the full-precision value; the margin is the rounding's, not a tuning |
| `tools/remap_sample_cache.py` (new) identity proof | every cached key at the same lon/lat within **1e-9 deg**; `h_cm` lists byte-identical; 1,000 random old nodes (seed 54) identical sample + position; the re-keyed cache loads under the pinned frame (SampleCache's own 1e-9 m frame check) | 1e-9 deg ⚠ invented (EXPANSION-PLAN P0 step 6; ~0.1 mm, measured float error 1.4e-14) |

**Proven (2026-10-14, all on v0.18.0's installed data, 4a9e66f):**

- `data/routes.json`: `full` / `medium` / `short` re-serialise to md5 `10d26665…` (the v0.18.0 file) and the old
  file minus its closing brace is a prefix of the new one; `north` re-derives from `tracks/san-diego-lake-murray/data/
  route.north.spec.json` on `data/osm.expansion.json` (every leg equal to the routes lens's path, 0 edges against a
  one-way).
- `heightfield.py`, `grid_grow` absent: fed the installed grid's own values it writes `heightfield.npy` +
  `heightfield.meta.json` byte for byte; HEAD's and the new `heightfield.py`, fed a sampler keyed on each point's exact
  float bits, write byte-identical `centerline.elevation.json`, `heightfield.npy`, `heightfield.meta.json`,
  `elevation_profile.svg`.
- `heightfield.py`, `grid_grow` 37 / 37 / 26 / 0: 149 x 167 = 24,883 nodes; all 11,439 old nodes sampled at their
  bit-identical positions (the old block IS the installed grid) and projected by the consumers' formula within
  1.4e-14 deg of where they were; 13,444 new nodes to fetch.
- The frame: pin with offsets 0 on the installed meta = today's frame, bit for bit; the pinned frame on the grown meta =
  the remap tool's new frame, bit for bit (unpinned it would sit 4e-10 m off; re-rounded, up to ~5 cm).
- `remap_sample_cache` on the installed cache: 723,527 keys + 111,708 fine keys shifted by [+416, −592] (fine [+2080,
  −2960]); max position change 1.42e-14 deg (all keys), 7.1e-15 deg (fine); `h_cm` byte-identical; 1,000 / 1,000 random
  nodes identical.
- `terrain_sample` (offline, scratch copy of the workshop): with the committed config minus D2's two boxes (frame pin 0,
  `grid_grow`, `route.bbox`, the held `north`) the plan's I / J / h / keep / tris / phys / refine / break arrays equal the
  installed v0.18.0 `terrain.tiers.json.gz`.

## 2026-10-14 — Lake Murray expansion P1: the weld rehearsal's opt-ins — `authored_take`, `swept_mouths` (A7 split), `weld_exact_deck` (weld + verify_mouths HOST LANE), `verify_race` M on split rows (ledger 0054)

No threshold moves: every tolerance below is the one already in force (the weld's 2 cm `SELF_TOL_M`, verify_mouths'
`LANE_TOL_M` 2 cm / `GRASS_AT_M` 5 mm, barrier_bands' `MOUTH_CORNER_M` 3 m / `MOUTH_PROBE_M` 10 m). What changes is
*which surface* two gates measure against, and *how far* a mouth is declared, for the mouths a config key names. Every
key is absent from the committed config (the north route stays HELD until P3); with the keys absent every output is the
v0.18.0 one (the existing `test_barrier_bands`, `test_verify_mouths`, `test_route_connectors_held` and the new tests).

| Item | Value | Flag |
|---|---|---|
| `route.route_connectors.authored_take` (new, opt-in; `tools/route_connectors.py`) | `{route: [weld id]}`: those weld stubs of `data/expansion.<route>.json` become connectors as authored (centre + width per point; the 3DEP height smoothed as every route piece's); refused when the file is missing, in another frame, or lacks the id | wiring |
| `race.swept_mouths` (new, opt-in; `tools/barrier_bands.py`) | connector-name prefixes: the mouth is declared from the piece's swept road edges (assembler smoothing) crossing the host edge, + `MOUTH_CORNER_M` of arc, joined with gap_mouths' sidewalk gap (`mouth_weld.gap_window`); its policy is derived **per vertex** and split into runs (EXPANSION-PLAN A7: a far-side opening past a box pin is `sealed_far_strip` in the box, `behind_closure` in the funnel; at a pin the far strip is the seal); self-gate 7 judges a split row on every vertex of its run | wiring; the 3 m and 10 m are the existing constants |
| swept-mouth probes | every **6 m** of host arc across the opening (1.5 m in from each edge crossing) and at both ends of the declared window, each **3 m** and 10 m past the host edge | 6 m and 3 m ⚠ invented (ledger 0054 P1: one probe per lane-width along a 30-50 m opening; 3 m = surely on the new road) |
| `route.weld_exact_deck` (new, opt-in; `tools/mouth_weld.ExactHostDeck`, `weld_mouths_blend.py`) | connector-name prefixes whose weld reads the host deck off the host ribbon's own triangles on its pavement (the projection model off it): the warp target AND the self-check | no threshold; measured: the J1 3-line stub's end-row chord vs the projection deck 2.4 cm (fails the 2 cm self-check on its paint), vs the host's triangles 1.7 cm; on a straight host the two are equal to 1e-9 (`test_mouth_weld_exact_deck`) |
| verify_mouths HOST LANE under `route.weld_exact_deck` | the deck at each sample is the host's lowest road sheet there (was HD(s), the centreline deck level across) | no threshold; measured on the v0.18.0 road with NO mouth at J5: the level-across HD reads the corner's own fanned / levelled deck as 8 samples up to 2.2 cm "above itself" and 21 grass samples "at" it (`p1-proofs/host_lane_baseline.py`) |
| `verify_race` M | a split mouth row (`split` present) is judged on its own `vertex_from..vertex_to`; every other row on the closed mouth's window, as before | wiring |
| `tools/author_expansion.py` (new) — `[authored]` numbers | `SMOOTH_SIGMA_M` 4, `DIVIDED_SEP_M` 3, `NOSE_M` 6, `NOSE_CLEAR_M` 6, `NOSE_W_M` 0.6, `CROSSOVER_W_M` 12, `PAD_CUT_PAD_M` 2, `STUB_LEN_M` 15, `WELD_STUB_OUT_M` 100, `ENTRY_MIN_DEG` 15, `ENTRY_EASE_M` 3, `EASE_ENTRY_DEG` 30; J3's two north corner radii 6 m, the visitor-centre arm 12 m wide | ⚠ invented (authoring choices, no measurement; listed in the file's `parameters`) |
| `tests/tools/test_author_expansion.py` tolerances | swept edge vs authored curb ≤ 0.5 m; junction heights within 0.5 m of revise/measure.json; built width at an eye station within 0.02 m | 0.5 m ⚠ invented; V1's 1.5 m p95 and V2's ±1 m pads are the plan's (themselves ⚠ invented there) |

**Proven (2026-10-14):** with the rehearsal delta (`tracks/san-diego-lake-murray/source/expansion/p1-proofs/
rehearsal_delta.py`) on a fresh scratch copy of the workshop: both welds self-check clean (J1 straight-curb stub, J5 with
its R 10 return and NE ease); planned and BUILT `no_route` PASS on both Speedways with 428 probes (22 new, past v1521
included); the A7 split live in race_cw (J1 v1509-1521 `sealed_far_strip`, v1522-1523 `behind_closure`; J5 v2310
`behind_closure`, v2311-2325 `sealed_far_strip`); verify_mouths PASS on J1 and on every existing mouth (byte-for-byte
the v0.18.0 numbers); J5 verify_mouths FAILS on 11 grass-at-deck samples on the loop's centreline at v2311-2313 that
the v0.18.0 road carries identically (0 road above the host, MOUTH LINE 3.5 cm, NOTCH 3.8 cm, APPROACH 0.45 %/m);
drive_test / audit / fold fans on all three layouts equal to v0.18.0 key for key (street soft top 33, severe 0, kinks
3.41 /km, audit 53; race severe 22 / 20, barrier_missing 0). Details: ledger 0054 "P1",
`p1-proofs/rehearsal_result.json`.

### P1 fix round (2026-10-14, after the verifier refuted P1): J5's grass and steps at their causes, J1's R 30 return built (apron AP1), the mouths' overlap removed (ledger 0054)

The refutation's two failing checks and their causes: (1) verify_mouths J5 HOST LANE, 11 grass samples within 5 mm
under the loop's road at v2311-2313 (v0.18.0 carries them identically): the kn5 prep pins grass 2 cm under the road at
its vertices and leaves a 4.5 m plane between them, and the 0050 fan's eased inside edge creases the deck along the
centre line; then 4-5 more at the loop's edge, from the weld's end-row chords lying within 2 cm over / under the host's
own sheet (the prep's anti-poke steps down road sheets 2 cm at a time and cannot see the lower one). (2) drive_test
severe steps at the J5 box in both Speedways (race_cw s 6954-6959, race_acw s 6523-6529, 6.1-7.9 cm; v0.18.0's): every
one on a fixed-offset path running BACKWARDS past the fan's turning centre, where verify_fold_fans' and the verifier's
own arc-length wheel paths read at most 2.5 / 3.0 cm. Every change below is opt-in by a new key; absent, every output is
v0.18.0's (the existing tests; `test_drive_test_fold_bumps`, `test_trim_connectors`, `test_verify_mouths`,
`test_barrier_bands_swept`, `test_make_treefx_plan` gain the opt-in cases; `test_apron.py` is new).

| Item | Value | Flag |
|---|---|---|
| `tools/seat_terrain_blend.py` HOST LANE refinement (opt-in: `route.weld_exact_deck`) | terrain edges under the host's lane on the mouth side, over the mouth's span + **4.0 m** each way, from **1.0 m** across the centre line to the edge + 0.5 m, halved to **0.75 m** (the prep then pins the grass every 0.75 m; a 2 % crease lifts a facet ~4 mm, not 2.2 cm) | 0.75 m / 4.0 m / 1.0 m ⚠ invented (span + 4 m covers verify_mouths' span + 3 m) |
| `route.mouth_fill` (new, opt-in; `tools/apron.mouth_fill`, `tools/author_aprons_blend.py`) | the connector's ROAD strips from its end out to its first row wholly outside the host (every point and both chords **0.05 m** past the host edge) replaced by one piece whose outline is the host's own edge between the connector's two edge crossings, those edges and that row; heights: the outline's existing vertices (points inserted ON the straight 3-D seams every **1.0 m**), inside the cotangent-Laplace film | 0.05 m and 1.0 m ⚠ invented; measured: J5 multi-sheet samples 0 (P1: the weld sheet 2.55 m into the lane, within 1.9 cm of it) |
| `route.aprons` (new, opt-in; `tools/apron.py`, `tools/author_aprons_blend.py`) | J1's NE return: the circle of the design's **R 30 m** (dossier 20-40) tangent to the stub's edge at the edge vertex within **3 m** of the design tangent point, to where it meets the loop edge (within 1 vertex of the design's apron end); deck = the existing seam vertices + the film (arc points within **1.0 m** of a seam take its run-on; interior grid **1.0 m**, none within **0.35 m** of the outline; arc points every **0.75 m**); the return curb + walk is build_loop_blend's curb_sidewalk profile; the stub's curb on the apron removed (faces only); terrain under it and its walk seated by seat_terrain's verge rule (edges ≤ 1.5 m) | 3 m / 1.0 m / 0.35 m / 0.75 m ⚠ invented; R 30 m and 20-40 m the dossier's |
| apron / fill self-check | no well-shaped triangle (smallest altitude ≥ **0.25 m**) steeper than the steeper seam it joins + **2 %**; no apron vertex over the host deck by > 0.01 m within 0.5 m of its edge; the CDT covers the outline (2 % + 0.5 m²); the curb's lane edges on the road edges at T / E_row (2 mm) | 0.25 m and 2 % ⚠ invented |
| `gap_mouths_blend` (opt-in: `data/aprons.json`) | the host's walk opened from P0's row to the row the return curb meets (E_row) | wiring |
| `barrier_bands` swept mouth (opt-in: `route.aprons` + `data/aprons.json`; refuses the key without the file) | the opening runs to the apron's end on the loop edge; the sidewalk gap to E_row | wiring; the 6 m / 3 m probes as in P1 |
| `verify_mouths` APRON (opt-in: `data/aprons.json`) | NOTCH runs on along the host while the return's pavement edge stands ≥ NOTCH_OUT_M + **0.18 m** past the notch line; HOST LANE window to the apron's end + 3 m; the stub seam (**0.15 m** either side, from 0.75 m past P0 to sqrt(2 R · 0.33) short of T): road on both sides within NOTCH_TOL_M (5 cm), nothing over the apron side; the deck every **0.5 m**, **0.3 m** inside its outline: road present, no grass at/above it (GRASS_AT_M) | 0.18 / 0.15 / 0.5 / 0.3 m ⚠ invented; the tolerances are the existing ones |
| `route.trim_blend_grade_cap` (new, opt-in; `tools/trim_connectors.py`) | a listed connector's blend onto its host lengthened from 30 m in **5 m** steps to at most **90 m** until the blended grade stays within route_connectors' 11 % (A6); measured: Waring at J1 fell **14.8 %** in 30 m (the loop stands 1.44 m over 3DEP there) -> **70 m, 11.0 %**; Jackson north keeps 30 m (3.6 %) | 5 m / 90 m ⚠ invented; 11 % is route_connectors' MAX_GRADE |
| `author_lamps_blend` (opt-in: `data/aprons.json`) | a post whose base stands in an apron (or within **0.5 m** of it) moves behind the return curb, **0.83 m** (the walk's middle), base on the walk top; `lights.local.json` rewritten so every later reader sees it | 0.5 m ⚠ invented; 0.83 m = curb face 0.08 + 0.75 |
| `make_treefx` (opt-in: `data/aprons.json`) | no plant on an apron or within **1.0 m** of it | 1.0 m ⚠ invented |
| `drive_test.fold_fan_severe = "verify_fold_fans"` (new, opt-in; `scripts/geometry/drive_test.py`) | a SEVERE reading (> 6 cm) on a sample whose metre or previous metre runs backwards INSIDE a levelled fan (the 0050 zones) is filed as `fold_severe` (reported, not gated here); `tools/verify_fold_fans.py` judges the same fans on the real wheel paths (fine steps ≥ 2 cm, 1 m second differences > 6 cm; rows k − 12 … l + 13 ⊇ these zones; hard, never covered by --force-install). A forward sample, or one outside a levelled fan: severe as before | no threshold moves; measured: race_cw 22 -> 6 + 16 fold_severe, race_acw 20 -> 3 + 17 (the 22 / 20 under the old rule are v0.18.0's exactly); every one in the J5 box and at the hairpin, verify_fold_fans PASS with DT max 0.018-0.025 m there |

**Proven (2026-10-14, the fix-round rehearsal: full `ship_sd.sh --no-install` on a fresh scratch workshop copy, the
chain run to its end):** verify_mouths PASS on all six mouths (J1 mouth line 0.6 cm / notch 0.6 / grass max −1.3 cm,
apron seam 77 samples max 0.6 cm, deck 350 samples no hole, no grass; J5 mouth line 1.7 / notch 2.2 / grass max −0.7
cm; the four existing mouths byte-for-byte v0.18.0's numbers). Under the level-across HOST LANE method (for the record)
J5 still reads 8 samples of the host's OWN sheet "over" it (v0.18.0 without a mouth: the same 8, max 2.2 cm) and no
other sheet. Every drive_test / audit key of the three existing layouts equal to v0.18.0's (street soft top 33, severe 0,
kinks 3.41; audits 53 / 53 / 53), severe under v0.18.0's rule 22 / 20 unchanged; no_route BUILT PASS both Speedways
(0 / 434 probes); verify_fold_fans PASS. Details: ledger 0054 "P1 fix round", `p1-proofs/rehearsal_result_fixround.json`.

## 2026-10-14 — Lake Murray expansion P2: the grown heightfield in one change, `planned_pavement`, 0046 criterion 3 restated, the cut-wall and V7 measures (ledger 0054)

No gate threshold is loosened. One criterion is restated (the plan's step 5) by adding a guard while keeping the old
ones. One V7 row is re-worded, because fresh 3DEP fails its first wording too. Every new key is opt-in. With the keys
absent every output is the old one, byte for byte (tests).

| Item | Value | Flag |
|---|---|---|
| `tools/grow_heightfield.py` (new) | `build_heightfield`'s own layout. Every old node is looked up at its EXACT float position in the installed grid. The ungrown layout must re-derive the installed meta, else it refuses. New nodes come from `usgs_3dep._sample_batch` (TLS, 4 tries; a no-data point aborts, never filled). Also refuses: no `grid_grow`, an already-grown meta, `elevation_scale` ≠ 1, any fetch under `--offline` | exact; no tolerance |
| `tier_options.frame.pin` | rows_n **37** / cols_w **26**, the same change as the grown grid and the re-keyed cache (P0's held step) | the plan's sizes (P0) |
| `terrain.tier_options.planned_pavement` (new, opt-in; `terrain_tiers.Topology(plan_lines=)`, `terrain_sample.planned_inputs`) | an authored intermediate's pieces (half-width = the WIDER curb offset), pad outlines and stub pavements (rings of zero width) mark the tiers and the physical ground (pockets included) like built pavement. Never keep_cells / refine / break lines / clamp / feather. Its file joins the plan's `inputs_md5` (planner and assembler) | the wider curb: never under-marks [invented choice, conservative] |
| `scenery.scatter(index_offset=)` (scripts-v021; build_loop_blend passes 2 × the meta's `grid_grow` rows_n / cols_w) | each node's jitter and pick hashed on its UNGROWN (row, col) | exact; (0, 0) = today's |
| `make_treefx` density fill on a grown grid | the loop's own cells only, numbered as the ungrown grid numbered them; the added cells plant nothing until P4 / A9 | wiring; rehearsal `trees.txt` = v0.18.0's, md5 b476f62e |
| ship chain sync-in | airoso's `data/heightfield.npy` + `.meta.json` into the workshop (ship_sd.sh with `expansion.north.json`; ship.json `sync_in.optional`) | wiring |
| **0046 criterion 3, restated** (ledger 0046 "Criterion 3's low clause restated") | (i) NEW: no terrain vertex more than **2 m** under the 3DEP value at its own position (its point sample, or a finest-level vertex's anti-aliasing tent), beyond the graded near-road band (**36 m** of a built pavement = keep_surface_m 20 + keep_feather_m 16, and the ground_release zones); (ii) KEPT: below 100 m abs, none more than 3 m under the 3DEP point; the far ring within 1 m (criterion 6); (iii) KEPT: none below 15.52 m | 2 m: EXPANSION-PLAN P2 step 5 ⚠ invented; 36 m: criterion 7's own band; the tent reference is fix round 2's filter. Not loosened: (i) adds a guard, (ii) and (iii) unchanged. The plan's "2 m everywhere" fails on v0.18.0 itself, by design: 21,189 graded near-road vertices, worst 16.3 m; one ridge vertex anti-aliased 2.34 m under its point |
| V7 "Kwaay Paay from Jackson s 550: visible, 8.0 ± 0.5°", **re-worded** | the summit judged as a **150 m** cone (nothing more than 150 m short of the top stands higher) instead of sightline_check's 60 m (Cowles') | 150 m ⚠ invented. Fresh 3DEP fails the 60 m wording too: the dome's own shoulder, 90 m short of the top, reads 8.075° over the cone's 8.046° |
| V7 cut walls (EXPANSION-PLAN step 3 / V7) | 12-20 m from the centreline every 5 m, against fresh 3DEP: a real wall ≥ 3 m is LOST when the built (P3-projected graded) ground keeps under **half** of it; ≥ 50 m of lost wall = a hand-authored cut slope | 3 m / 50 m: the plan's; "under half" ⚠ invented |
| P2's "loop ground unchanged" | every v0.18.0 1GRASS vertex within 150 m of a road, and back: |Δy| ≤ **0.05 m** except beside the two weld mouths (the plan's named exception) | 0.05 m: the plan's (invented there) |

**Proven (2026-10-14; ledger 0054 "P2", `tracks/san-diego-lake-murray/source/expansion/p2-proofs/`):**
- The planner on v0.18.0's config reproduces the installed plan array for array: 268,976 + 5,157 break-line vertices.
- On the grown grid and the re-keyed cache, without D2 and `planned_pavement`, the plan is v0.18.0's with every key
  shifted by (+416, −592) and every value identical (positions within 1e-12 m).
- The committed grid's old block, written back, is v0.18.0's grid, md5 35ce2b92 / 1e14cf9c.
- The full `ship_sd.sh --no-install` rehearsal, on a fresh scratch workshop and a fresh engine-july copy:
  - the three existing layouts' drive_test, verify_mouths, verify_fold_fans, no_route, barrier_bands and race_verify
    files are byte-identical to v0.18.0's. Street: soft top 33, severe 0, kinks 3.41 /km, audit 53. Race: severe
    22 / 20, barrier_missing 0, audits 53 / 53;
  - rib_check and house_seat PASS;
  - the loop's ground within 150 m is |Δy| 0.000 m except beside J1 / J5: 37 + 1,429 vertices, max 1.68 m, all within
    85 m of the planned pavement;
  - 1GRASS is 8 tiles (max 58,612) and GRASS_FAR 4 (max 40,314); 0 open tier seams; the far ring is ≤ 0.85 m off 3DEP;
  - V7 passes, with Kwaay Paay as re-worded; facets 20-60 m from the planned pavement have p90 5.02 m;
  - criterion 3 as restated has 0 offenders on both v0.18.0 and the rehearsal;
  - the road kn5 is 125.0 MB.
---

## 2026-10-14 — phase 5 side-road stubs: `tools/verify_stubs.py` (new, hard), audit D's declared stub-barrier exemption, the stub draft's numbers (ledger 0054)

Kevin 2026-10-14: *"a road we are not completing gets a barrier, not a curve."* An unbuilt public side road gets its
real mouth (curb returns, the host sidewalk gapped), a short stub of real road and a K-rail barrier across it
(`tools/stub_roads.py` declare + draft, `tools/author_stubs_blend.py`, docs/JUNCTIONS.md R18 (d)). **Opt-in**: with no
declaration (`STUBS=` / `tracks/<track>/stubs.json` absent) no step runs, no file is read or written, and every output
is what it was — the identity proof is under "Measured".

### The gate (`tools/verify_stubs.py <project>`, new; hard in `ship_sd.sh` right after `verify_mouths`, only when `data/stubs.plan.json` exists)

On the BUILT road gate OBJ (data/track.obj — the stubs ride in the road kn5, every layout loads them), per declared stub:

| Check | Threshold | Basis |
|---|---|---|
| S1 present | the mouth + piece in mouths.json, the authored record, ≥ 1 `1WALL_STUB_<id>` triangle | — |
| S2 mouth | `verify_mouths.check_mouth`, unchanged (0.05 / 0.02 / 0.05 m, 3 %-pt/m over 2.5 m) | verify_mouths' own (2026-10-11) |
| S3 drivable, mouth line → barrier toe | a 1ROAD sheet every 0.25 m on the centre + both wheel lines; neighbouring samples ≤ **0.05 m** apart; no grass within 0.005 m; nothing else (another wall, a post, a house, a TreeFX trunk) > **0.05 m** over the carriageway (±(w/2 − 0.3)) | 0.05 / 0.05 [invented]; grass = verify_mouths GRASS_AT_M |
| S4 span | across the stub's own cross-section at the declared distance, back of walk to back of walk (half-width + 0.08 + 1.5), every 0.05 m: the barrier top ≥ **0.80 m** over the surface | [invented]; real K-rail 0.81–1.07 m (Q5), the module is 1.20 m |
| S5 seat | each barrier vertex's least gap within **0.45 m** in plan (its own ring's toe) ≤ **0.05 m** (no hover); sunk into the stub's road / curb / walk ≤ **0.15 m** (the ends may stand buried in a bank) | 0.05 m = the task's seating limit; 0.45 = 0.255 across the jersey + a 0.25 m ring step; 0.15 [invented] (a 0.67 m base on a 15 % grade sinks 0.10) |
| S6 host lane | every barrier vertex ≥ **1.0 m** outside the host's pavement edge | [invented] |
| S7 returns | at each corner's arc midpoint: 1ROAD 0.5 m inside the arc, no grass at/above it; 1KERB ≥ **0.10 m** over the lane edge 0.6 m outside | [invented]; the curb is 0.14 m |
| S8 curb cut | the host walk 0.5 m behind a driveway's lip ≤ lip + 0.03 m + its share of the apron rise | [invented] |

Teeth (tests/tools/test_verify_stubs.py, a synthetic welded stub dressed by stub_geom): passes dressed; fails a 2-ring gap
in the barrier (S4), the barrier lifted 0.12 m (S5), a post in the carriageway (S3), a missing return (S7), no barrier (S1).

### audit_mesh D (wall on a road) — the declared stub barrier only

The barrier stands ON its stub's road by design. D skips a vertex only when it is a `1WALL_STUB*` object's AND lies
within its DECLARED footprint (data/stubs.built.json: the ring path ± the 0.335 m half base + **0.15 m** [invented]);
any other wall there, or a stub-barrier vertex off its footprint, still counts. Presence, span, seating and the host
lane are S1 / S4–S6. No stubs.built.json: nothing read, nothing printed — proven byte-identical below (A4).

### The draft's and the authoring's numbers (`tools/stub_roads.py`, `tools/stub_geom.py`, `tools/author_stubs_blend.py`)

| Number | Value | |
|---|---|---|
| stub length, mouth line → barrier centre | 15.0 m | [invented]; ≥ 13.65 m survives trim's 15 m MIN_PIECE_M |
| road behind the barrier centre | 1.0 m | [invented]: the 0.67 m base stands wholly on the stub |
| stub row spacing | 1.0 m | denser than the loop's 3 m (JUNCTIONS R6: never coarser) |
| vertical curve | grade change ≤ 0.015 /m, ≥ 4 m; 3DEP grade capped at 15 % | [invented]; half verify_mouths' 0.03 |
| widths | OSM `width`; else `lanes` × 3.6 + 2 × 1.2 m; else residential / unclassified 10.0 (= route_connectors), living 8, tertiary 12, secondary 14, primary 16 | [invented] |
| side-road detection | an OSM node within half-width + 3 m of the BUILT centreline is on the host; < 25° to the host = a carriageway / slip; a connector within 6 m of the branch 5–25 m out = already built | [invented] |
| driveway curb cut | lip 0.03 m, flare 1.5 m each side, apron 4 m when OSM gives none | [invented] |
| return | the circle tangent to both road edges at the host's gap-end row (mouth_weld.gap_window: R = tH tan(φ/2)), stations ≤ 0.3 m, the walk compressed inside 0.85 R | 0.3 m = JUNCTIONS R5/R10 (macau 0.18 m); 0.85 [invented] |
| barrier | rings ≤ 0.25 m across (every curb profile point ringed), base 0.02 m under the lowest surface under its footprint | [invented] |
| ground under a corner | halved to 0.75 m within its tangent + 3.5 m (never the host's pavement + 0.3 m), pinned 0.16 m under the pavement / walk (seat_terrain's rule), 0.02 m under the verge | 0.16 = seat_terrain; 0.75 / 3.5 / 0.3 [invented] |

### Changed tools, every change opt-in

- `tools/trim_connectors.py`: a record's own `blend_m` (stubs carry 0 — their profile is already on the host deck), no
  REACH extension of a stub's ends, a stub on a CONNECTOR host cut against that host's pieces (phase 1's expansion
  roads). Records without those keys: proven byte-identical (A1).
- `tools/weld_mouths_blend.py`: a piece shorter than the 30 m warp (every row warped) no longer raises IndexError on the
  island bookkeeping; for every existing piece (K + 1 ≤ rows) the line is unchanged.
- engine-july (rehearsed on a scratch ENG copy, `PENDING-MIRROR.md5`): `pbr.TEXTURES["1WALL_STUB"]` (the K-rail
  module's own row, immune to the network-wall reskin) and the prep's planar-UV exemption for `1WALL_STUB`; no v0.18.0
  mesh name binds differently (A5).

### Measured (2026-10-14; scratch copies of the workshop, `--no-install`, the worktree's tools, the patched ENG copy)

**Demo** (the old loop, 6 of the 70 unbuilt public side roads declared: Reservoir Dr off Alvarado, Saint Therese Way and
Lambda Dr (63°) off College, Camino Estrellado (76°) and Margerum Ave (66°) off Navajo, Hyde Park Dr (12 m) off Jackson;
`tracks/san-diego-lake-murray/source/phase5/stubs.demo.json`), full chain on a fresh copy: `verify_stubs` PASS 6/6
(barrier span short 0 everywhere, seat float −0.02 m, sink ≤ 0.084 m, host edge ≥ 8.4 m away, 12 returns R 1.73–6.10 m);
`verify_mouths` PASS 10/10 (the six stub mouths: line ≤ 0.01 m, approach ≤ 1.29 %/m); planned + BUILT `no_route` PASS
both layouts (412 probes, 6 of them the new mouths); street drive_test soft top 33 / severe 0 / kinks 3.41 / obstruction
0, audit 53 (D 0, K 20, I 20, F 13); race_cw 9 / 22 / 6.23, race_acw 9 / 20 / 7.05, barrier_missing 0, audits 53 / 53
(D 0, 4,040 stub-barrier vertices exempt on 398 declared segments); verify_fold_fans PASS — every v0.18.0 number equal.
Two corner-ground defects the gates caught on the way (verify_mouths HOST LANE / NOTCH, grass within 1–3 mm of a deck
where a 4 m facet spanned the corner seam) are fixed in the tool (the corner's lane edge blends the host and stub decks;
the corner ground is refined across the host edge), not by any threshold.

**Identity** (no declaration): A1 trim_connectors (HEAD vs worktree, the workshop's own inputs) — every output file
identical; A2 stub_roads apply — no file touched; A3 verify_stubs — exit 0, nothing written; A4 audit_mesh HEAD vs
worktree on the v0.18.0 BUILT gate OBJs (street, race_cw, race_acw) — audit*.json byte-identical (53 / 53 / 53); A5 pbr —
all 69 mesh names of the v0.18.0 gate OBJs bind the same row and textures; A6 ship_sd.sh — every added executable line
sits under a stub-file test or only names stub files. B: the FULL chain from the worktree with no declaration on a fresh
workshop copy vs the installed v0.18.0's own files: 199 written files byte-identical (every drive_test / audit /
verify_mouths / verify_fold_fans / race_verify verdict, mouths.json, mouth_welds.json, connectors, every AI line, every
ini); the 29 others differ only in absolute paths and timings, plus 103 of 2,026,253 road-OBJ triangles moved ≤ 0.2 mm
in one ground_release zone (tools/ground_release_blend.py iterates Python sets of BMVerts — run-to-run order; that tool
is untouched here).


## 2026-10-18 — Phase 1 prep: the phase-5 stub tool's four cosmetic notes fixed at their causes; the real-data tests pinned to the data their numbers came from (ledger 0054)

No gate threshold changes. Every change below is in the phase-5 stub tools (opt-in: no stub declaration, no step runs)
or in the assembler's connector paint (one function, byte-identical off a stub), so the three installed layouts are
v0.18.1's: the held rehearsal (north route HELD, no stubs) wrote `drive_test.{street,race_cw,race_acw}.json`,
`verify_mouths.json`, `verify_fold_fans.json`, `lights.local.json`, `mouths.json`, `mouth_welds.json` and
`connectors.local.json` byte-identical to the installed v0.18.1's (Measured, below).

### The four notes (the phase-5 verifier, 2026-10-14) and their causes

| Note | Cause | Fix |
|---|---|---|
| doubled edge lines near the mouth and the barrier; paint 1 m past the barrier | `ribbon.lane_markings` paints a dashed divider every 3.65 m that fits inside the edge inset: on a 9.6-12 m two-lane side street that is a 3 m dash 0.6-1.8 m inside each edge line, falling at the 15 m stub's two ends; the paint follows the whole polyline, which runs 1 m past the barrier | `ribbon.connector_markings` (scripts-v021, the ONE call the assembler and `weld_mouths_blend`'s layout check both make; a plain connector = `lane_markings(.., center_yellow=True)` exactly): a stub paints `lanes_per_side` − 1 dividers a side (`stub_roads.lanes_per_side`: OSM `lanes` / 2, ≥ 1) and stops **0.5 m** [invented] short of the barrier's road-side toe |
| K-rail "one continuous slab" across the carriageway | a swept strip has no joint in its shape | `stub_geom`: a V-groove every **4.04 m** (the module, measured) laid symmetric about the barrier's middle: a ring of Kevin's module's own end face (`JOINT_HALF_PROFILE`, measured off `concrete_barrier_4m.obj`: base inset 0.020 m, top 1.202 → 1.106 m) between two full rings **0.020 m** (measured: the obj's end chamfer) either side; u starts on the first groove. No joint within **0.30 m** [invented] of an end; a joint within **0.06 m** [invented] of a profile-point ring (the 0.08 m curb face / top pair) slides past it. The two end rings stand **0.02 m** [invented] inside the grass meets (a ring ON the strip's boundary edge read no surface: Saint Therese Way, v0.18.1 road) |
| V-notch at the acute corners (Lambda 57°, Margerum 64°) | only the arc stations were compressed: the host's gap-end row A kept its full walk (mainline 1.88 m + 1.2 m verge, past the centre of an R 1.4-2.5 m return) and the walk stepped back out at B | the compression is continuous: row A compressed, the host rows behind it eased back over **3.0 m** [invented] (`stub_geom.host_ramp`; their walk-back / grass-meet vertices move, no index changes), J taken at least **3.0 m** [invented] past B and the tail eased back to the stub's own walk |
| jagged grass behind the returns | the loop's verges end 0.20 m under the road (curb_sidewalk grass_clearance) and the kn5 prep lays the ground beside every road at deck − 0.02 m, then clamps it 0.02 m under the lowest drivable sheet: the verge's foot is buried and the two rules meet along it. On the host's coarse ground that meeting is one long facet; on the corner zone's ground refined to 0.75 m it alternated cell by cell (measured after the prep; the author stage's own ground there was smooth) | (a) the return's interior grass meet stands **0.02 m** under its lane edge (the prep's GROUND_CLEAR, engine-july build_kn5_loop), eased to the strips' own over **1.5 m** [invented] at each end (`stub_geom.MEET_H_M` / `MEET_RAMP_M`): the return's verge lands on the ground the prep lays there; (b) the corner zone is still refined to 0.75 m, except under the straight strips' verges (the stub's own kept curb rows, the host's rows behind the gap end) and the **1.0 m** [invented] behind their grass meet (`COARSE_OUT_M`), where the buried foot stays on coarse ground like the host's |

### The real-data tests (not a gate; recorded because they judge the race and corridor tools)

Ten tests pin numbers measured on v0.18.0's road (their own docs say "the data pinned here is the installed v0.18.0
build's") but read `tracks/san-diego-lake-murray/data/` live. The v0.18.1 install (704f1d0) synced the rebuilt road
into it and they failed on main (12 failures there, the same 12 on this branch before this round; the other two are the
CRLF md5 pins). They now read `tests/fixtures/lake_murray_v0180/data/` (git 8f25c48, the v0.18.1 merge before its
install) through `tests/sd_v0180.py`, with the current config as before. Nothing in a tool changed.

### New numbers (all phase-5 stub tools; opt-in)

| Number | Value | |
|---|---|---|
| `stub_geom.HOST_RAMP_M` | 3.0 m | [invented] a compressed return's host walk eases back to full over this |
| `stub_geom.STUB_RAMP_M` | 3.0 m | [invented] ... and its stub walk over at least this (2.0 m read a 45 deg flare per station on the 58 deg test corner) |
| `stub_geom.MEET_H_M` | −0.02 m | the prep's GROUND_CLEAR (engine-july build_kn5_loop) |
| `stub_geom.MEET_RAMP_M` | 1.5 m | [invented] |
| `stub_geom.JOINT_HALF_M`, `JOINT_HALF_PROFILE` | 0.020 m; (0.315, 0), (0.311, 0.113), (0.147, 0.375), (0.117, 0.466), (0.073, 1.106) | measured off `assets/models/concrete_barrier_4m.obj` (its end face) |
| `stub_geom.JOINT_CLEAR_M` | 0.30 m | [invented] |
| `stub_geom.JOINT_KEY_CLEAR_M` | 0.06 m | [invented] |
| `stub_geom.END_INSET_M` | 0.02 m | [invented] |
| `author_stubs_blend.COARSE_OUT_M` | 1.0 m | [invented] |
| `ribbon.STUB_PAINT_STOP_M` | 0.5 m | [invented] |
| `stub_roads.lanes_per_side` | OSM `lanes` // 2, ≥ 1 | a side street is two-way |

### Measured (2026-10-18; fresh scratch copies of the workshop, the full `ship_sd.sh --no-install` chain, ENG = a fresh engine-july copy + the snapshot's two pending files)

**Held** (the north route HELD, no stub declaration): every v0.18.1 gate number — street soft top 8 / severe 0 / kinks
2.67 /km / obstruction 0, audit 53 (D 0, F 13, I 20, K 20); race_cw / race_acw severe 15 / 20, soft top 8 / 4, kinks
6.46 / 6.09, barrier_missing 0, audits 53 / 53, BUILT no_route PASS both (0 / 411 probes); verify_mouths PASS ×4,
verify_fold_fans PASS, verify_ai_line PASS both (wall min 2.542 / 2.384 m), verify_signs 23 posts PASS, verify_race
(0 fails, H chord max 0.043 m), rib_check PASS, house_seat PASS (153 buildings). Byte-identical to the installed
v0.18.1: `drive_test{,.street,.race_cw,.race_acw}.json`, `verify_mouths.json`, `verify_fold_fans.json`,
`lights.local.json`, `mouths.json`, `mouth_welds.json`, `connectors.local.json` (48 of the 77 data/ files the chain
wrote). The 29 that differ: absolute paths and timings; the grown terrain of P2 (heightfield, tiers, samples, corridor,
`audit*.grass_verts` 480,743 vs 373,416, house_seat contacts within 2 cm, ground_release report); and the
Lake Murray Blvd I-8 span stations in `barrier_bands.json` / `race_authored.json` / `race_verify.json` (13312.1-13456.8
vs 13318.7-13463.4, bridge_seating hits 328 vs 324): the installed declaration carried v0.18.0's stations, 6.6 m off
the v0.18.1 lap (College's realignment), while its own `bridge.spans.auto.json` already reads 13312.1 — the rehearsal
reads the file, nothing else in the race files moves (`no_route` PASS, every probe and wall the same).

**Demo** (5 stubs of `source/phase5/stubs.demo.json` on the v0.18.1 road: Saint Therese Way is skipped because its
mouth, v1257, sits inside College's chicane out-leg v1253-1289 (ledger 0055) and barrier_bands refuses a mouth
"behind the closure" where the closure leaves the curb — a real Phase 5 finding, not fixed here):
verify_stubs 5/5 PASS, verify_mouths 9/9, every gate number above unchanged; per corner on the BUILT gate OBJ
(`source/phase5/proofs/2026-10-18/`, `analyze.py`): lane dividers on a stub 0 (was 66-72 vertices each), the farthest
paint 0.50 m before the barrier's toe (was 1.34 m past it), K-rail grooves every 4.04 m, symmetric (±2.02 / ±6.06 m about
the middle of the 15 m barriers, 5 on Hyde Park's 17.5 m); folded kerb triangles unchanged; grass facets steeper than 45° and taller than 0.10 m within R + 5 m of the 10
corners 57 → 35 (the comb behind the returns gone; left: long sliver creases where the ground climbs behind Lambda Dr's
uphill corner, max 0.60 m, and the welded approaches' own bumps along the stub walks, as at v0.18.1's existing mouths
(max 0.19 m)); grass within 5 mm of a corner's road: as the 2026-10-14 demo (Lambda c0 6 samples at −2 mm, Hyde Park c0
5 at 0.0).

## 2026-10-18 — Lake Murray expansion P3 (Drive 1, v0.19.0): the north roads built; two new gates (`verify_pads`, `drive_test --line expansion`); drive_test's furniture seating reads every wall on its own ground (ledger 0054)

No existing threshold changes. Two new hard gates; one existing gate (drive_test's FURNITURE SEATING) now reads walls it
could not read before (below). Every other change is opt-in by a new key (absent: the old output).

### New gates

| Gate | Rule | Numbers |
|---|---|---|
| `tools/verify_pads.py` (hard, after `verify_stubs`, only with `data/pads.built.json`) | per junction pad on the BUILT road: P1 its deck / curb / every stub barrier present; P2 single coverage over the pad's outline; P3 every arm row vertex has a pad vertex within 1 mm, none 1 mm-5 cm off (JUNCTIONS rule 3), the two surfaces 2 cm either side of the seam within the gap; P4 no grass over the deck; P5 no curb triangle over the pad's pavement; P6 every barrier ≥ 0.8 m over the deck, its base ≤ 0.05 m over the surface under it; P7 the deck at the junction node within 1 m of its 3DEP | COVER_STEP_M 0.5 m [invented], SHEET_DZ_M 0.25 m [invented], raster phase 0.137 / 0.311 m (never on the deck's own 1 m grid), SEAM_STEP_M 0.25 m [invented], SEAM_GAP_M 0.010 m [EXPANSION-PLAN V3], 1 mm / 5 cm [JUNCTIONS rule 3], GRASS_OVER_M 0.005 m [invented], 0.8 m / 0.05 m [tools/verify_stubs.py's], NODE_TOL_M 1.0 m [EXPANSION-PLAN V2] |
| `drive_test --line expansion` (hard, after the street drive_test; a red is never installed, `--force-install` does not cover it) | the north network's own lines (tools/expansion_lines.py: each direction's right-hand carriageway, J1 → … → J5 and back, through the pads on a cubic turn), driven by drive_test's own sweep on the street OBJ; the verdict is EXPANSION-PLAN V6: obstructions, floating furniture, undrivable corners, daylight gaps 0; severe steps 0; soft top ≤ 6.1 /km; kinks ≤ 4.97 /km. drive_test's own lap rule (soft top 0, excursions ≤ 1 /km) is reported beside it, not gated — the loop's street layout itself ships red on it since v0.18.0 | LINE_SOFT_PER_KM 6.1, LINE_KINK_PER_KM 4.97 [invented in the plan, copied from the loop's rates]; expansion_lines MEDIAN_CLEAR_M 0.3 m [invented], EASE_M 15 m [invented] |

(Superseded 2026-10-19 by repair round 1, below: `travel_kinks` removed, the verdict's documentation made the code's,
excursions per km added, kn5_ground_check run, verify_stubs S4 read on the built crest.) drive_test `--line` only (the lap
and every layout are unchanged): a kink read on a fixed-offset sample that runs
backwards (`folded`) is filed as `fold_kinks`, and one whose grade change on the path's OWN travel (VERTEX BUMPS' rule,
v0.18.1, applied to the grade) is within KINK_PCT as `travel_kinks` — both reported, not gated: on the inside of a pad's
right turn a fixed-offset path covers well under 1 m a station and the turn's curvature changes from station to station,
so the grade over the metre it did not travel jumps (10-17 %-points on the first build, every one on the inside path at
J2 / J3 / J4, the pad decks themselves 1.6-4.8 % at their steepest). A crease in the deck reads on its own travel and
still counts (the Jackson arm's seam at J4, 3.9-4.6 %-points on every path, is counted).

### verify_stubs (hard since phase 5): S2 and S4

- S2 now reads the host deck the way verify_mouths does under `route.weld_exact_deck` (the same mouth, the same
  verdict); before, a stub on an exact-deck host was judged twice, the second time on the level-across deck.
- S4 reads the barrier's CREST within CREST_SEARCH_M 0.3 m [invented] of its declared distance along the stub
  (CREST_STEP_M 0.05 m): the author stage stations the barrier on the welded mesh's own rows, and on a steep host the
  weld's mitre moves a stub's first row up to 0.17 m along it (Laura St off Princess View's 9.6 %) — a cross-section
  0.17 m off the crest read the jersey's sloped face (0.75-0.79 m) instead of its 1.1 m top, at all 264 points. The
  rule (≥ 0.8 m over the stub back of walk to back of walk) is unchanged.

### drive_test FURNITURE SEATING: every wall on its own ground

The seating check reads each 1WALL column against the surface under it, but the corridor cull loaded surfaces only
within 120 m of the swept line: a wall farther out had nothing under it and read "floating 99" whatever stood under it.
On the v0.18.1 street layout that was 391 columns (re-read on the held rehearsal's own OBJ with the change: 0 — every one
of them stands on its ground); the north network's island rails and stub barriers made it 3,743. The ground under every
wall is now loaded; every wall is still judged. Not a loosening: no wall escapes the check, the ones it could not see
are now seen.

### Changed behaviour, opt-in

| Where | Key | What |
|---|---|---|
| `tools/route_connectors.py` | `route_connectors.authored_take` naming a piece (A-D) | takes the whole piece (tools/expansion_pieces.py) |
| `tools/trim_connectors.py` | a capped connector carrying `expansion` | OFFSET blend (the piece's own line lifted onto the host, easing out) at the shortest length whose grade stays within its own steepest + OWN_GRADE_PLUS 0.03 [invented: drive_test's KINK_PCT] (and the 11 % cap) |
| `tools/seat_terrain_blend.py` | `route.tight_approach_host_grade` 0.06 [invented] | a side street off a host climbing ≥ 6 % is TIGHT over its whole approach (0.75 m ground); a coarse edge reaching under it from a kept cell is read by its ends too |
| `tools/verify_mouths.py` | a connector island with `offset_aware` | its reach on the mouth side is its own lateral + half-width (the north medians stand off the centre line) |
| `tools/stub_roads.py` | declaration `defaults.straight` | each stub on the chord of its OSM branch (the returns fit one straight edge) |
| `tools/stub_roads.py`, `tools/author_stubs_blend.py`, `tools/verify_stubs.py` | a curb cut on a connector host | the host line from the connector (trim's renamed piece found by the cut) |
| `tools/ground_release.py` (+ `_blend`, engine-july prep `_release_zones`) | a zone with `line` / `piece` / `piece_s_m` | resolved onto the trimmed connector, judged on its own line (cut zones only: `cut_reach_m`, rails false) |
| `scripts-v021 ribbon.connector_markings` | a connector record's `paint` | paint_markings: exactly the authored lines (tools/expansion_pieces.py decorate) |
| `scripts/geometry/audit_mesh.py` D | `data/pads.built.json` | its stub barriers exempt on their declared footprint, as stubs.built.json's |
| `track.config.json` | `route.weld_exact_deck` += `STUB_` | the north side streets read the host deck off its triangles (hosts up to 9.6 % round curves) |

### New numbers (P3 tools)

| Number | Value | |
|---|---|---|
| `expansion_pieces.PROFILE_HALF_M` | 30 m | [invented] the profile's local quadratic fit reach (tricube) |
| `expansion_pieces.MEDIAN_EDGE_M` | 0.30 m | [invented] |
| `expansion_pieces.BIKE_LINE_M` / `BUFFER_M` / `PARKING_LINE_M` | 1.80 / 0.90 / 2.40 m | [invented] (the parking lane 8 ft) |
| `expansion_pieces.PAIR_IN_M` | 0.24 m | [invented] the double-double yellow's pair spacing |
| `expansion_pieces.PLAIN_DOUBLE_UNDER_M` | 1.0 m | [invented] |
| `expansion_pieces.HATCH_EVERY_M`, hatch stroke width | 6.0 m, 0.30 m | [invented] |
| `expansion_pieces.LANE_MIN_M` | 2.9 m | [invented] |
| lanes per direction | Waring 2, Princess View 2 + 2 (3 downhill on its last 614 m), Mission Gorge 3 + 3, Jackson 2 + 2 | the intermediate's pieces[].paint (dossier §2) |
| `junction_pad.SNAP_MAX_M` | 0.6 m | [invented] the built arm row vs the design cut |
| stub far edge | level across, at its middle's 3DEP + 0.10 m | the corners stand on curb lines (gutter / kerb / verge) |
| `author_junction_pad_blend.ARM_GRADE_REACH_M` | 30 m | [invented] |
| pad steepness self-check | ≤ the steepest of the arms', the stubs' and the chords between two seams + 2 % | tools/author_aprons_blend.py's GRADE_OVER_SEAMS |
| six cut zones (ground_release) | reach 40 m, cut reach 20 m, round 3 m, rails false | College's cut face (ledger 0055), the very parameters |

### Measured (the final rehearsal, D:/k10-scratch/phase1/p3final: fresh workshop copy + fresh engine-july copy, FULL chain, `--no-install`)

The same end as the held v0.18.1 rehearsal ("NOT INSTALLED": the street lap's own soft-top rule, red since v0.18.0); no
key of the three existing layouts worse (`source/expansion/p3-proofs/compare_vs_held.json`).

| | held v0.18.1 | v0.19.0 rehearsal |
|---|---|---|
| street: soft top / severe / kinks per km / excursions | 8 / 0 / 2.67 / 96 | 8 / 0 / 2.67 / 96 |
| street floating furniture | 391 | 0 (the reading fix above; 0 on the held OBJ too) |
| race_cw: severe (fold fans apart) / soft top / kinks | 15 / 8 / 6.46 | 4 + 11 fold = 15 / 8 / 6.46 |
| race_acw: severe (fold fans apart) / soft top / kinks | 20 / 4 / 6.09 | 6 + 14 fold = 20 / 4 / 6.09 |
| audit_mesh (each layout) | 53 | 53, class for class |
| no_route both Speedways | PASS | PASS (leak 0 m²) |
| verify_mouths | PASS | 30 mouths PASS (J1 0.006 / 0.025 m, J5 0.017 m) |
| verify_stubs | — | 24 stubs + 27 curb cuts PASS |
| verify_pads J2 / J3 / J4 | — | PASS: multi-coverage 0, seam max 1.1 / 0.7 / 0.9 mm, near misses 0, node −0.03 / +0.13 / +0.27 m vs 3DEP, barriers 1.08 m |
| drive_test --line expansion fwd / rev | — | PASS / PASS: soft top 2 / 0, severe 0 / 0, kinks 3.66 / 1.11 per km |
| verify_signs | 23 | 19 PASS (M3 and M4 skipped, two posts each: P1's reasons; their race-file plates are P4) |
| road kn5 | 82.27 MB | 108.18 MB, 92 meshes, 1,445,573 positions; largest mesh 1WALL_guard 65,251 of 65,535 |
| race kn5 | 11.80 MB | 11.72 MB |

## 2026-10-19 — Lake Murray expansion P3, repair round 1 (the gates, truth and view lenses refuted P3): the line gate's late exemption removed, its verdict and its documentation made one, kn5_ground_check run on every layout, verify_stubs S4 read on the barrier as built; the cut walls, J4's deck, the terrain's vertical slivers and two missing side streets fixed at their causes (ledger 0054)

No existing threshold is loosened. One exemption added late in P3 is removed (`travel_kinks`); one search that took the
best of 13 readings is replaced by a single reading on the built barrier (verify_stubs S4); one rule is added to the line
gate (excursions per km); one engine gate runs where it did not (`kn5_ground_check`).

### drive_test --line expansion

- **`travel_kinks` is gone.** P3 added it (re-measuring a kink on the wheel path's own travel) one minute before the
  final rehearsal, after the forward line read 5.09 kinks/km against its 4.97 limit; it turned that verdict to PASS. The
  cause was not the measure: tools/expansion_lines.py strung each turn through a pad as a cubic between the two lanes'
  centres carrying a 12-16 m carriageway, so the right-hand wheel paths of every right turn ran up the pad's curb return
  (10-17 %-point kinks at s ~960 / ~2060 / ~4320: a wheel climbing a 0.14 m curb). Fixed there (below); the forward line
  now reads KINKS without any exemption.
- **The verdict and its documentation are one.** The code's verdict was V6 only while the docstring, the gate comment and
  data/drive_test.expansion.json's `_doc` said "drive_test's rule or V6". The verdict stays the plan's V6 (EXPANSION-PLAN,
  decided before the build) plus one added rule — **unguarded excursion drops ≤ LINE_EXC_PER_KM 7.12 /km** [invented:
  the loop's own held v0.18.1 street rate, 96 over 13.47 km, copied the way V6 copied its two rates]. drive_test's own lap
  rule (soft top 0, excursions ≤ 1 /km — failed by the loop's street layout since v0.18.0) is read on every line and
  written beside the verdict with its reasons (`drive_test_rule_fail`, `drive_test_rule_reasons`), and printed.
- **Nothing uncounted is unrecorded.** Each line report now carries, with their places: `fold_kinks_all` (the one
  reading the line does not count — a fixed-offset sample running backwards round a turn, FOLD BUMPS' rule),
  `excursions_all`, `soft_top_all`, `kinks_all`.

### tools/expansion_lines.py: the turn stays inside the curb

Where data/pads.built.json exists, every line point casts a ray to each side against the pads' curb faces (the outline's
`edge` runs); a carriageway edge within CURB_CLEAR_M 0.5 m [invented: drive_test's edge path runs 0.25 m past the edge
it is given, so it stays 0.25 m off the face] of a face is pulled back to it, the other edge kept, never narrower than
MIN_W_M 6.0 m [invented: one 3.6 m lane + its edge paths], each edge eased into it over EASE_PTS 4 points [invented]
(never past the face); RAY_PAD_M 1.0 m. A piece's own curbs are its carriageway already: only the pads' are read.

### kn5_ground_check on every layout (EXPANSION-PLAN V5)

V5 lists it on all three layouts; neither the held nor the P3 chain ran it (a gap on main too). It now runs after
verify_fold_fans, per layout, on the kn5 SET that layout loads (`--kn5`: the street-only kn5, or the common race kn5 +
its closure), writing data/kn5_ground_check.<id>.json; its red counts with the street gates (`--force-install` only under
0047's no-key-worse rule). Where data/track.obj is the kn5's own gate OBJ (kn5_to_gate_obj's gate_centerline.json beside
it) the fidelity half is skipped as for a Blender-authored project: it compared the kn5 with itself, in another frame
("1ROAD unalignable" on v0.18.1). Every physical check is unchanged and runs.

### verify_stubs S4: the barrier read where it stands

P3's S4 took the best barrier-over-surface reading of 13 cross-sections within CREST_SEARCH_M ±0.3 m of the declared
distance. Now one reading per lateral sample, on the barrier's own crest line as built (data/stubs.built.json
barrier.path_xz, ring by ring), and a new rule: that crest line within BAR_STATION_TOL_M 0.25 m [invented] of the
declared distance along the stub (P3's search tolerated 0.3 m without saying so).

### The ground: cut walls (tools/ground_release.py AUTO CUTS; tools/ground_release_blend.py RAISE-ONLY)

Replaces P3's six hand-declared cut zones. terrain.ground_release.auto_cuts {pieces A-D}: per piece, every
probe_step_m 5 m [invented], each side, 3DEP on the release lattice's own 2 m nodes from probe_from_curb_m 1 m to
probe_to_curb_m 29 m [invented: the conform corridor's 20 m + most of its blend] past the curb (probe_every_m 1 m: every
node across is met, deduped); a station-side is a CUT where the real ground stands min_rise_m 1.0 m [invented] over the
road (the piece's own 3DEP profile); cut stations within merge_gap_m 20 m [invented] join; a stretch shorter than
min_len_m 10 m [invented] is a bump; each stretch is padded pad_m 15 m [invented] and split into batter_window_m 50 m
[invented] windows, each window's batter the p90 of its stations' steepest probe-to-probe climb, held to
docs/ROAD-CONSTRUCTION.md's 1.0-2.0 m per metre (common earth 1:1 .. fractured rock 0.5:1) and rounded to batter_step 0.25
[invented]; equal neighbours join, the pieces abut (no ramp between them). Each zone: bank, rails false, College's
reach 40 / cut reach 20 / round 3 m, `batter` "max" (default): its `cut_slope` is cut_slope_max 2.0, a BOUND, never a
target (the ground is 3DEP wherever 3DEP stands under it); it binds only where the built walk and apron (2.8 m) cover the
real wall's toe (the first full rehearsal used each window's own p90 climb: Mission Gorge's south wall then stood 1.1-1.9 m
short 18-20 m out); `batter` "face" keeps the windowed reading. And RAISE-ONLY, in tools/ground_release_blend.py:
  * the released height is taken only where it stands over the ground the vertex had, never lower, except down to the
    cut batter where the seat left ground standing over it at the pavement edge (min(max(released, had), batter));
  * "the ground it had" is the LOWEST sheet at the vertex's plan point (the seat's vertical curtains put two vertices on
    one plan point: raised each from its own they stood as 780 vertical faces up to 1.3 m; from the lower one they
    collapse and the zone weld takes the pair);
  * never under what the prep's contact band would have left: the prep feathers every vertex OUTSIDE a zone toward the
    nearest road deck (PREP_BAND_M 3.0 m full, smoothstep over PREP_FEATHER_M 6.0 m: build_kn5_loop's BAND_M / FEATHER_M)
    and leaves zone ground alone, so a raise-only cut takes the up half of it, max(released, feather); and under the walk
    (not the road) exactly the prep's feather + anti-poke (min(feather, lowest sheet - 0.02)). Without both, the grass
    behind every walk in a cut stood 0.2-0.35 m low and bared the walk's buried apron (excursions 39 -> 60 on the first
    rehearsal), and a face from a vertex under the curb top to one under the gutter stood 2-4 cm over the road (soft tops);
  * its faces are capped under the WALK and the ROAD only, not the walk's buried outer apron (CURB faces sloping more than
    APRON_NZ |normal z| 0.985 [invented]: the apron at 0.96, a walk top on a 15 % hill at 0.989), the same surface the
    release's own self-check reads for those faces.

resolve_zones refuses raise_only off a declared cut and cut_slope outside 0.5-2 (loose soil 2:1 .. fractured rock). An
auto zone that moves nothing is reported, not fatal (a declared one still is).

### The terrain's vertical slivers (tools/terrain_mend.py; the engine-july snapshot's build_kn5_loop, PENDING MIRROR)

BEAUTY can cut an n-gon with a T-vertex m on its straight edge a-b into the ear (a, m, b): no plan area; once m moves off
the line the ear stands up as a one-sided vertical fin over a crack (the see-through slit on Jackson north; 1,978 within
80 m of the north roads before the release). triangulate_terrain_blend and ground_release_blend (after its halving and
after its heights) rotate a-b inside the quad it makes with the face across it — no vertex moves or is added — or delete
the fin on the open edge; a face across a-b already fanned through m is rebuilt by hand. LINE_TOL_M 1 mm [invented],
END_FRAC 1e-3, MAX_ROUNDS 6 [invented]. The kn5 prep's corridor subdivision made 262 more the same way (a halved edge
beside a coarser face, BEAUTY after it, the pin / feather after that): the snapshot prep mends them right after its
triangulation, before anything moves, by the same rule and tolerances (`_collinear_middle`, `_mend_vertical_slivers`).
That file is recorded in engine-july-snapshot/PENDING-MIRROR.md5 (757a0ac6...), not yet copied into the live engine-july.

### The junction pads' decks follow the real ground (tools/junction_pad.py)

The plan reads 3DEP every GROUND_STEP_M 2 m [invented] inside each pad's design outline (cached in data/pads.3dep.json);
the author stage pulls the soap film toward a quadratic fitted to it (+ LIFT 0.10 m): the screened film minimises the
cotangent energy + Σ λ_i (h_i − guide_i)², λ_i = λ × the smoothstep of the distance inside the design outline over
GUIDE_FADE_M 10 m [invented] (the stub tails keep the plain film to their level far edges). λ is the strongest of
GUIDE_LAMBDAS (1, 0.3, 0.1, 0.03, 0) [invented] whose deck keeps the pad's own steepness bound (the seams' grades + 2 %,
unchanged) AND creases no route seam more than the plain film does or CREASE_MAX 3 % [invented: drive_test's KINK_PCT]
(each seam vertex's arm grade into the pad against the deck's over CREASE_IN_M 2 m [invented]; without it a dev rehearsal
pulled J4 into an 8 % ramp onto its Jackson seam, a 6.3 cm severe step on the forward line); 0 is P3's film exactly. Recorded per pad
(pads.built.json deck.ground_guide: the pull, the crease, the plain film's crease).

### The side streets the stub tool could not see (tools/stub_roads.py)

A way counted as a host carriageway when 60 % of its nodes lay within the host's half-width + 3 m and it was over 20 m
long: Glenroy St's south-west leg (way 663868618, 3 of 5 nodes inside Princess View's 22 m) and Doreen Rd (5955946, 2 of
3 inside Jackson's) were taken for Princess View and Jackson and got no entry at all. A host way must now also run ALONG
the host where it is on it (length-weighted |cos| of its on-host segments ≥ cos PARALLEL_DEG 25°, the tool's own number).

### Lamps on a corner apron's walk (tools/author_lamps_blend.py)

A post standing on a return's walk (within LAMP_WALK_BAND_M 2.8 m behind the apron outline: curb 0.08 + walk 1.5 +
grade 1.2) is re-seated where it stands on the built walk (head = surface + HEAD_OVER_GROUND_M 8.8 m, the draft's rule);
a moved post is seated on the built walk under its new base the same way. Lamp 77 behind J1's R 30 return only.

### Measured (the final rehearsal, D:/k10-scratch/phase1/r1final: fresh workshop copy + fresh engine-july copy with the snapshot's two pending files, FULL chain, `--no-install`, commit 285147c)

The same end as the held v0.18.1 rehearsal ("NOT INSTALLED": the street lap's own soft-top rule, red since v0.18.0, and
kn5_ground_check's lamppost reading, red on v0.18.1 as well); no key of the three existing layouts worse
(`source/expansion/p3-proofs/compare_vs_held.json`).

| | held v0.18.1 | P3 (refuted) | repair round 1 |
|---|---|---|---|
| street: soft top / severe / kinks per km / excursions / audit | 8 / 0 / 2.67 / 96 / 53 | same | 8 / 0 / 2.67 / 96 / 53 (K 20, F 13, I 20) |
| race_cw / race_acw severe (fold fans apart) | 15 / 20 | 4 + 11 / 6 + 14 | 4 + 11 / 6 + 14 |
| race soft top, kinks, barrier_missing, audit, no_route | 8 / 4, 6.46 / 6.09, 0, 53, PASS | same | same (leak 0 m², reached 138,776 / 138,218 m², as held) |
| kn5_ground_check street / race_cw / race_acw | FAIL (lampposts: no ground in reach under 38.4 %, seat median −3.04 m: the LED lamps' buried feet; double-sheet 0, lamp orphans 0, road over ground p95 0.021 m) | not run | FAIL, the same reason and numbers (walls 50 objects, hovering 0; road over ground p95 0.021 m) |
| drive_test --line expansion fwd / rev | — | "PASS" (the forward line only through travel_kinks) | PASS / PASS: soft top 0 / 0, severe 0 / 0, kinks 2.86 / 0.32 per km, excursions 44 / 43 (7.0 / 6.8 per km), fold kinks 2 / 0; drive_test's own lap rule FAIL on excursions alone (fwd 38 walk aprons + 5 median curbs + 1 fill, rev 29 + 7 + 7) |
| verify_mouths | PASS | 30 PASS | 32 PASS (J1 mouth line 0.006 m, J5 0.017 m) |
| verify_stubs | — | 24 + 27 PASS | 26 stubs + 29 curb cuts PASS (S4 on the built crest, every crest within 0.149 m of its declared distance) |
| verify_pads J2 / J3 / J4 | — | PASS, node −0.03 / +0.13 / +0.27 m | PASS, seams 1.2 / 0.7 / 2.4 mm, node −0.02 / +0.04 / +0.02 m, ground-guide pull 0.1 / 0.1 / 1.0 |
| pad deck − 3DEP inside each design outline (p95; points over 0.3 m) | — | 0.31 / 0.29 / 0.44; 17 / 38 / 152 | 0.21 / 0.17 / 0.20; 6 / 17 / 12 |
| J4's Jackson seam crease | — | 3.9-4.6 %-points | 2.87 % (its plain film 5.48 %) |
| real walls 3 m+ kept, 12-20 m off the centre line (stations / > 1 m short / under half / runs ≥ 20 m) | — | 249 / 109 / 97 / 12 | 250 / 4 / 0 / 0 (Mission Gorge south, s 1490-1555: the built walk covers the wall's toe) |
| the same, 12-35 m | — | 678 / 517 / 478 / 23 | 678 / 0 / 0 / 0 |
| vertical grass faces, whole OBJ / within 80 m of the north roads | 730 / 3 | 2,700 / 1,972 | 46 / 26 (one over 0.25 m tall) |
| road kn5 | 82.27 MB | 108.18 MB, 92 meshes, 1,445,573 positions | 115.96 MB, 94 meshes, 1,585,066 positions (1WALL_guard 65,251 of 65,535, unchanged) |

## 2026-10-19 — Lake Murray expansion P3, repair round 2 (the truth lens refuted round 1): the north roads' centre paint measured off the aerial, three raised islands where the aerial has them, Mission Gorge's south rock face from the back of the walk, the kn5 prep counting what the kn5 writer counts (ledger 0054)

No existing threshold is loosened and no gate is bypassed. One engine guard gains the count it was missing (the kn5
writer's own vertex count, below); every other change is in what is built.

### The centre paint, measured (tools/aerial_paint_north.py -> source/expansion/aerial__paint_north.json)

The intermediate placed every undivided station's centre paint from the aerial eye readings (one every ~250 m),
interpolated; the lens traced Jackson's painted median ~1.65 m to one side of the built one for ~1 km. Now measured at
every 2.5 m station off NAIP (EPSG:3857, 0.3 m pixel, TLS verified; windows WIN_HALF_M 150 m every WIN_EVERY_M 200 m
[invented], cached outside the repo): a cross profile every DL_M 0.1 m [invented] over ±18 m, each sample the mean of
ALONG_N 5 readings ALONG_STEP_M 1.0 m apart [invented], yellowness = min(R, G) − B; re-read about the station line
smoothed by a gaussian of FRAME_SIGMA_M 15 m [invented] (the station line is OSM's chords: |offset to its smooth| p95
0.60 m, max 2.49 m on Jackson); profiles stacked (mean) over ±SMOOTH_HALF_M 7.5 m [invented]; read between the curbs
less CENTRE_CLEAR_M 3.3 m [invented: a bike lane 1.8 m + half a lane; the narrowest real carriageway, Jackson s 380-520,
leaves the paint ~3.8 m off the curb]. A yellow stretch stands SEG_MIN 6 [invented, NAIP 8-bit units] and half the
profile's peak over the zone's median; two stretches MEDIAN_SEP_M 0.9-6.5 m apart [invented] with the weaker at least
PAIR_RATIO 0.35 [invented] of the stronger are a painted median's faces (width + 2 × FACE_IN_M 0.18 m: expansion_pieces'
own face-to-line offset); one stretch at least MERGED_W_M 1.3 m wide [invented] is a narrow median, its faces BLUR_M
0.35 m [invented] inside its edges; a reading narrower than MEDIAN_MIN_M 1.6 m [invented: NAIP's 0.6 m pixel spreads a
0.36 m double yellow to a 1.2-1.4 m stretch] is one double yellow. Along the road: a reading more than SANITY_M 5 m
[invented] off the intermediate's centre is dropped (a painted curb return), one more than OUTLIER_M 1.5 m [invented] off
its neighbours' running median over ±OUTLIER_HALF_M 25 m [invented] is dropped, a run of one kind shorter than
KIND_MIN_M 10 m [invented] between the other is dropped, gaps up to GAP_MAX_M 30 m [invented] are interpolated, longer
ones keep the intermediate's values.

tools/author_expansion.py takes it on Princess View and Jackson only (PAINT_MEASURED_PIECES; Waring's and Mission Gorge's
raised medians are curbs, checked fine by the lens): a painted median's offset and width, or a double yellow's offset,
per station. And MEASURED_ISLANDS: the raised islands the aerial shows that the eye readings and the dossier missed or
misplaced — Princess View s 399-535 (the Fontaine St island; the dossier's "nose st ~500-557" stood on the Fontaine
crosswalk) and s 612-700 (planted), Jackson s 32-118 (the J4 approach's concrete island) — each its measured outline
less 2 × FACE_IN_M and 2 × ISLAND_EDGE_M 0.30 m (expansion_pieces.MEDIAN_EDGE_M: the built yellow edge line stands that
far off a raised face). They take the median rule every north island already has (author_median_blend: a barrier on an
island of BARRIER_MIN_M 120 m or more — Princess View's s 399-535).

### Mission Gorge's south rock face (tools/ground_release_blend.py, RAISE-ONLY)

Round 1 kept every real wall but four stations 18-20 m off Mission Gorge's centre, 1.2-1.5 m short. Read on the built
cross-sections and the release's own numbers (s 1495): the zone's cut-top rounding (ledger 0055 round_m 3 m) is a smooth
minimum of the real ground and the batter whose HEIGHT round_k = round_m / 2 × the batter assumes level ground beside the
cut; up a rock face climbing 1.2-1.6 m per metre against a batter of 2 the two stay within that height for metres, and the
whole kept face was lowered by up to k / 4 = 0.75 m. In a raise-only cut the rounding's height now uses the batter LESS
the real ground's own climb away from the road at the vertex (central difference on the release lattice over
±ROUND_GRAD_M 1.0 m [invented]); where the natural ground beyond the cut is level it rounds exactly as before
(`raise_only_rounding_on_the_real_climb` in ground_release.report.json). Tried on development builds and dropped:
the batter measured from the back of the walk instead of the apron's foot (light "teeth" along every cut's toe), the
ground under the apron released with it (the kn5 prep's anti-poke puts it back), the toe band on 1 m facets
(vertical grass faces 46 → 123, the wall unchanged), and a 1 m 3DEP lattice in the toe band (the face unchanged: the
same 3DEP read on a 1 m grid stands 1.0 m under the single 1 m sample the measure takes at the 20 m mark — that is the
residual, see the measured table).

### The kn5 prep counts what the kn5 writer counts (engine-july snapshot scripts/ac/build_kn5_loop.py, PENDING MIRROR)

The prep's split pass and its FATAL over-cap guard read Blender vertices; the writer that runs
(blender-assetto-corsa-tools exporter/node_writer.py) emits one kn5 vertex per unique (position, normal, uv, tangent) of a
TRIANGLE corner after its own bmesh triangulation, and splits past 2**16 into meshes of one name (AC drops them from
collision). The median barriers' 1WALL_guard: 15,136 Blender vertices, 65,251 kn5 positions on round 1, 66,367 with
Princess View's island barrier — verify_kn5 "DUPLICATE physical mesh '1WALL_guard' x2". After the per-mesh pass, a mesh
whose triangle corners exceed VERT_CAP is counted exactly as the writer counts (the writer's triangulation on a copy); over
VERT_CAP it is triangulated the same way and tiled by balanced_face_tiles over those keys into uniquely named tiles of at
most SPLIT_CAP 60,000 (the prep's existing numbers), each tile re-checked by assert_under_cap on the writer's count.

### Measurements of record (p3-proofs)

- measure_p3.py `pads`: the lens's reading — the built pad deck at every ground-guide point of the pad plan (3DEP every
  2 m inside the design outline + the 0.10 m lift). Round 1's ledger quoted J3 at 0.17 m from another reading; on the
  plan's own points round 1 reads J2 / J3 / J4 0.207 / 0.226 / 0.209 m (6 / 17 / 12 points over 0.3 m).
- measure_paint.py: the built YLINE vs the aerial per 10 m station on Princess View and Jackson (the lens's paint check).

### Measured (the final rehearsal, D:/k10-scratch/phase1/r2run3: fresh workshop copy + fresh engine-july copy with the snapshot's two pending files, FULL chain, `--no-install`)

The same end as the held v0.18.1 rehearsal ("NOT INSTALLED": the street lap's own soft-top rule and kn5_ground_check's
lamppost reading); every key of the three existing layouts equal to round 1's and no worse than held
(`source/expansion/p3-proofs/compare_vs_held.json`).

| | repair round 1 | repair round 2 |
|---|---|---|
| street / race_cw / race_acw keys, audit, no_route, kn5_ground_check | as held v0.18.1 | the same |
| drive_test --line expansion fwd / rev | PASS / PASS: kinks 2.86 / 0.32 per km, excursions 44 / 43 | PASS / PASS: kinks 2.39 / 2.53 per km, excursions 40 / 38 (6.36 / 6.01 per km), soft top 0 / 0, severe 0 / 0 |
| verify_mouths / verify_stubs / verify_pads | 32 PASS / 26 + 29 PASS / PASS | the same (seams 1.2 / 0.7 / 2.4 mm) |
| centre paint vs NAIP (measure_paint.py): Jackson, a clear painted median's real centre − built (n, p50, \|p90\|) | 53, +1.70 m, 2.43 m | 69, 0.00 m, 0.14 m |
| the same, Princess View | 0 clear medians built | 29, −0.03 m, 0.32 m |
| built yellow line → nearest aerial yellow, p50: Princess View / Jackson | 1.15 / 1.63 m | 0.11 / 0.05 m |
| pad deck − (3DEP + 0.10) on the plan's guide points, \|p95\| J2 / J3 / J4 (points over 0.3 m) | 0.207 / 0.226 / 0.209 (6 / 17 / 12) — round 1's ledger quoted J3 0.17 | the same |
| real walls 3 m+ kept, 12-20 m (stations / > 1 m short / under half / runs ≥ 20 m) | 250 / 4 / 0 / 0 | 250 / 3 / 0 / 0 (Mission Gorge south s 1495 / 1530 / 1555: 1.16 / 1.14 / 1.08 m) |
| the same, 12-35 m | 678 / 0 / 0 / 0 | 678 / 0 / 0 / 0 |
| vertical grass faces, whole OBJ / within 80 m of the north roads | 46 / 26 | 51 / 29 |
| road kn5 | 115.96 MB, 94 meshes, 1,585,066 positions | 116.05 MB, 95 meshes (1WALL_guard_0 / _1: 33,192 / 33,177), 1,586,930 positions |
| Waring s 0-45 out of J1 over 3DEP (max), steepest 20 m | 1.285 m, −8.79 % | the same (the J1 tilt is Kevin's call) |

## 2026-10-19 — Lake Murray expansion P3, repair round 3: the road kn5 thinned without moving a vertex, rib_check reads the lattice the thinning took, kn5_ground_check finds a lamp's feet per lamp (ledger 0054)

No threshold is loosened and no gate is bypassed. Two gates change how they FIND what they measure (below, each with
the build that shows it judges at least what it judged before); one new self-checked author step, every number of it
invented and listed here.

### The size, and where it came from

Road kn5 116.05 MB on r2run3 (1GRASS 818,196 vertices) and 122.6 MB on r2run2 (941,699, round 2's 1 m cut toe since
dropped in 273b116); v0.18.1 73.6 MB (355k). kn5 bytes are ~44 per vertex + 6 per triangle (r2run2: 1,704,346 vertices,
2,615,733 triangles, textures 31.9 MB = 90.7 MB of geometry); 1GRASS + GRASS_FAR were 60 % of the vertices. TERRAIN
through the chain, v0.18.1 -> r2run2: the assembler's tiers 163k -> 229.8k (the north roads' 5 m band); the seat
174k -> 372.6k (137,015 edges halved under the welded approaches and the host edges, 37,707 of them to 0.75 m under the
host lanes at 28 exact-deck mouths); the ground release 200k -> 732.8k (44 zones, 35 of them round 1's auto cuts, edges
halved to 2.5 m and 1 m); stubs and pads ~32k; the prep's corridor subdivision 57k -> 80k edges and kept-cell refinement
94k -> 106k on top. Most of it was never moved again: on r2run2 268k of the 555k vertices within 20 m of a pavement lay
in their neighbours' plane to 2 mm.

### tools/thin_terrain_blend.py + tools/terrain_thin.py (new, between the prep and the freeway drape / the split)

Greedy half-edge collapse on every 1GRASS / GRASS_FAR tile of the prepped scene: a vertex merges into a neighbour, no
vertex moves, none is made. The new surface's deviation from the chain's own is computed EXACTLY over the star (both are
linear on the overlay of the two triangulations: v and every old-spoke / new-edge crossing) and accumulated per triangle
as an interval; every triangle keeps the strictest tolerance of every vertex it has covered. Tolerances by the plan
distance to the pavement (1ROAD / 1KERB, the race kerbs out — read on the flattened pavement):

| where | up / down | longest new edge | |
|---|---|---|---|
| under the pavement | UNDER_UP_M 0.005 / UNDER_DOWN_M 0.015 | MAX_EDGE_NEAR_M 8 | [invented] the prep pins it 0.02 under the deck; verify_fold_fans fails grass 0.02 over the lane (worst today 0.003); 0.035 under stays inside the ground gate's 0.05 contact line |
| beside it to NEAR_EXACT_M 6 | TOL_NEAR_M 0.005 | 8 | [invented] the drive gates' 4 m excursion band (+2 m); an excursion is a 0.12 m fall between 0.5 m samples |
| to NEAR_ROAD_M 22 | TOL_M 0.03 | MAX_EDGE_M 20 | [invented] the near-road bound for this round was 0.05 |
| beyond, to FAR_EDGE_FROM_M 60 | FAR_TOL_M 0.10 | 20 | [invented] 60 = terrain.tier_options' own 5 m band |
| beyond 60 m | FAR_TOL_OUT_M 0.15 | MAX_EDGE_FAR_M 40 | [invented] the 20 / 40 m tiers and the far ring |

Left alone [invented]: every vertex within HOUSE_CLEAR_M 2 m of a building (tolerance 0: no star around it changes), the
prep's hole-fill n-gons, tile seams and boundaries, every vertex of a face with |normal z| under NZ_LOCK 0.25. A new
triangle is refused when it flips or degenerates (plan area x 2 under MIN_AREA2 1e-6), is thinner than ASPECT 0.02 of its
longest edge, or is steeper than the steepest it replaces by NZ_SLACK 0.02 (normal z); the link condition holds.

**rib_check's own inputs** (it gates the ground past its NEAR_M 20 m, to the nearest pavement vertex): every removed
vertex ON the lattice (node or lattice line) is written to data/terrain_thin.nodes.json.gz (rib_check below); a
cross-grain FOLD (a plain cell whose diagonal leans across the grain by more than HALF_CELL_EX 0.25 m [invented] —
rib_check reports folds from 0.5 m, gates them from 1 m) with its centre past CELL_LOCK_M 18 m [invented] keeps its four
corners, and no new plain cell may lean across the grain by more than HALF_CELL_EX; from JOG_ZONE_M 12 m [invented] out,
a star with any triangle (old or new) steeper than NZ_FINE 0.84 [invented: 0.65 m per metre, under rib_check's JOG_SLOPE
0.7] keeps every new edge under FINE_CAP_M 7.5 m [invented: rib_check's step jogs read finest-tier triangles, extent
<= 7.6 m] — a triangle that could carry a riser never grows out of the jog measure's reach, and one that cannot (gentler
than 0.65) carries no riser segment to lose.

Self-checks (exit 1, the blend not saved): at every removed vertex the thinned surface within that vertex's own
tolerance; every face the thinning made facing up, no tile with more faces not facing up than before; every tile's
material kept. data/terrain_thin.json records every tile, every parameter.

### tools/rib_check.py — the lattice is the ground's, not the vertex list's

`thinned_lattice`: with data/terrain_thin.nodes.json.gz present (written by the thinning, same lattice frame or
SystemExit), a removed NODE is read as before with its height off the BUILT triangles at that point (L5), and a removed
lattice-LINE vertex still marks its row as drawn through a break. Without the file nothing changes. No threshold moved.
Measured on the round-1 build thinned offline (D:/k10-scratch/phase1/r3dev/r1p, the same gate code as r1final):
lattice nodes 555,669 = 555,669 (198,243 of them read on the surface), nyquist gated 87 = 87, cross-grain 44 = 44, step
jogs 68 -> 69 beyond 20 m (densest 75 m: 4 = 4, limit 5) — the jog measure saw one more, never fewer.

### scripts/ac/kn5_ground_check.py — a lamp's feet are the lamp's

The seating lens takes the lowest vertex of every 1.5 m column with no lower column within ~3.5 m as a FOOT. The 2026-10
LED standard (ledger 0056: a 3.66 m arm, the lens 4.04 m from the pole, two arms back to back) leaves its outer arm
columns 11 m up as feet with nothing in their 4 m support window: 38.4 % of Lake Murray's lampposts "no-ground" (the
gate's > 10 % rule; its message printed only median / p95 / hovering). MAST_BUCKETS ("LIGHTPOST", "GANTRY"): the object
is the chain of occupied columns (8-neighbour) its vertices draw, its feet the columns within the existing 0.8 m of that
chain's lowest — on r2run2's street set exactly 238 chains for 238 lamps. A pole hovering keeps its pole column as its
foot (tests/ac/test_lamp_mast_seating.py: 20 long-armed lamps 1.5 m over the ground FAIL; the same on the ground PASS, and
FAIL on the old rule at 66.7 % no-ground). Every other bucket keeps the old rule. The fail message now names no-ground.
r2run2 street set: lampposts no-ground 38.4 % -> 0.0 %, seat-gap median -3.04 / p95 -2.97 unchanged — the poles' feet
are 2.5 m under the road datum by the model's own footing (streetlight_led.json pole_bury_m), in the earth on every
slope, which this lens never failed (it fails hovering, not buried); every other line identical.

### Measured (the final rehearsal, D:/k10-scratch/phase1/r3run: fresh workshop copy + fresh engine-july copy with the snapshot's two pending files, FULL chain at 751550b, `--no-install`)

| | r2run2 (round 2, with its 1 m toe) | r2run3 (round 2 final) | r3run (round 3) |
|---|---|---|---|
| road kn5 | 122,608,352 B | 116,050,024 B | **89,815,220 B** |
| 1GRASS exported vertices (16 tiles) / GRASS_FAR | 941,699 / 160,499 | 823,164 (the prep's tiles) / 160,499 | **392,918** / 123,172 (the thinning: 983,650 -> 515,973 over 20 tiles) |
| road kn5 totals | 1,704,346 v, 2,615,733 tri | 1,586,930 positions | 1,118,236 v, 1,448,351 tri (textures 31.9 MB, unchanged) |
| verify_mouths / verify_stubs / verify_pads | 32 / 26 + 29 / J2-J4 PASS | the same | the same (pads: seams 1.2 / 0.7 / 2.4 mm, nodes -0.019 / 0.039 / 0.017 m) |
| verify_signs | 19 PASS | 19 PASS | 19 PASS (M3 / M4 still skipped until P4) |
| rib_check nyquist / cross-grain / step jogs (densest 75 m) | 87 / 44 / 68 (4) | 87 / 44 / 68 (4) | 87 / 44 / 69 (4), limits 100 / 100 / 5 |
| house_seat_check contact min / max | -0.303 / -0.148 | -0.303 / -0.148 | -0.303 / -0.143, 0 floating / sunken / buried |
| drive_test street: soft top / severe / kinks / excursions | 8 / 0 / 2.67 / 96 | the same | the same |
| drive_test --line fwd / rev: kinks, excursions | 2.39 / 2.53, 40 / 38 | the same | the same (soft top 0 / 0, severe 0 / 0) |
| race_cw / race_acw: severe (fold) / kinks / barrier_missing | 4 (11) / 6 (14), 6.46 / 6.09, 0 | the same | the same |
| audit street / race_cw / race_acw | 53 / 53 / 53 | the same | the same (F 13, I 20, K 20) |
| no_route built race_cw / race_acw | PASS 0/439 | PASS | PASS 0/439, reached 138,776 / 138,218 m2 |
| verify_fold_fans | PASS 3 x 3 | PASS | PASS 3 x 3 |
| kn5_ground_check street / race_cw / race_acw | FAIL x 3 (lampposts no-ground 38.4 %) | FAIL x 3 | **PASS x 3** (lampposts 0.0 %, median -3.04 / p95 -2.97; road-over-ground 12/10785, p95 0.021 -> 0.022 m) |
| six cut walls, built max over the road (measure_p3 walls) | Mission Gorge 3.87, Jackson 5.54 / 6.40 / 4.28 / 5.49 / 7.08 | MG 4.13, the rest the same | the same as r2run3 |
| real walls 3 m+ 12-20 m: stations / > 1 m short / median shortfall | 250 / 4 / 0.19 | 250 / 3 / 0.18 | 250 / 3 / 0.17 (12-35 m: 678 / 0 / 0.12 in all three) |
| vertical grass faces, whole OBJ / within 80 m of the north roads | — | 51 / 29 | 47 / 25 |

The ground near the roads, at every r2run3 terrain vertex within 22 m of a pavement vertex (503,605 compared; 968 on
near-vertical faces skipped): within 6 m p99 0.0037 m and 5 vertices over 0.05 m at three places (max 0.091), 6-20 m and
20-22 m at most 0.030 m. The three places are not the thinning's: this run's own prep output, rebuilt offline before any
thinning (D:/k10-scratch/phase1/r3dev/r3pre), already stands there (the author stage's sliver mend rebuilt 27 slivers in
this run, 24 in r2run3 — run to run). Against that pre-thinning ground of the same run, at all 981,984 terrain vertices
off near-vertical faces: under the pavement p99 0.0036 m, 0-6 m at most 0.005, 6-22 m at most 0.030, 22-60 m at most
0.100, beyond at most 0.150 (7 vertices under the College / I-8 bank read no surface at their height in EITHER build —
they stand on near-vertical faces a downward ray cannot hit). Against r2run2: 28,906 of the 28,918 vertices within 6 m that
moved more than 0.05 m lie in the 35 raise-only cut zones (round 2's 273b116: the 1 m toe dropped, the cut top's rounding
on the real climb); the 12 others <= 0.145 m (near-vertical faces and run-to-run).

## 2026-10-26 — Lake Murray expansion P4 lamps (ledger 0054 P4 step 2, EXPANSION-PLAN D4): streetlights on the four north pieces, every post seated on the built ground and kept off every pavement, one CSP light per lamp proved on the written file

No threshold is loosened and no gate is bypassed. The lamp author gains a hard self-check on EVERY post (not only the
relocated ones, as since v0.18.1), the track-folder step gains a hard read-back of the written `ext_config.ini`, and the
draft's lamp walk is extended to the north pieces with the numbers below, every invented one marked.

### The pieces' posts (scripts-v021 `geometry/streetlights.py`, called by `build_loop_blend.build_streetlights` after the loop's posts; opt-in `scenery.streetlights.expansion`)

The loop's rules, kept as they are: spacing 55 m, no two posts within 25 m (the loop's posts counted), sides alternating,
the head 1.8 m road-ward of the post and 8.8 m over the draft ground (`build_streetlights`: `spacing`, the 25 m test,
`arm`, `post_h - 0.2`). The pieces' own:
- `WALK_OFFSET_M` 0.83 — the post stands mid-walk: the curb face 0.08 + half the connectors' 1.5 m walk (`ribbon.curb_sidewalk`
  `curb_face_w`, `sidewalk_w`). Not invented: `tools/author_lamps_blend.py` `LAMP_BEHIND_CURB_M`, the rule lamp 77 stands by on
  J1's return since the P1 fix round. (The loop's posts stand hw + 2.8 m, on the graded back edge of their 1.8 m walk; the
  pieces' cut faces rise right there, so the walk it is.)
- `PAVEMENT_CLEAR_M` 1.5 [invented] — a base closer than this to ANOTHER pavement's edge (the mainline, any other connector)
  is in its way: the pole's mast radius 0.124 + the author's `ROAD_SETBACK_M` 0.46 + 0.9 m of margin for the curb and walk
  that stand on that edge.
- `STUB_CLEAR_M` 10.0 [invented] — past a side-street stub's pavement edge along its host, on the stub's side: its curb
  returns (R 6-8 m, `tools/stub_geom.py`) and the walk round them.
- `PAD_CLEAR_M` 3.0 [invented] — from a junction pad's outline (`expansion.north.json` pads[].outline_xz) and from each
  pad's stub arms' pavement polygons: the returns' curb and walk stand on the outline.
- a curb cut (a lowered curb at a driveway, `stubs.plan.json` curb_cuts) blocks its host and side for `half_span_m +
  flare_m + PAVEMENT_CLEAR_M` either way of its station.
- `SLIDE_M` 12.0 in `SLIDE_STEP_M` 2.0 [invented] — a blocked station slides along the walk (closest first), then the
  other side is tried at the same station and its slides, then the station is SKIPPED with every reason recorded
  (`lights.local.json` expansion.skipped). The grid itself never moves: the next station is 55 m from the one that was
  blocked, not from where its post landed.
- `OSM_MATCH_M` 15.0 [invented] — a real OSM `highway=street_lamp` node within this of a piece's pavement edge stands a post
  AT its station, on its side, on the walk (its own lateral offset is not trusted at 1-2 m). `OSM_STRETCH_PAD_M` 27.5
  (half the spacing): nodes closer than 110 m to each other make one OSM-grounded stretch reaching 27.5 m past its end
  nodes, inside which the loop's spacing is not used. Each post records `source` "osm:<id>" or "authored"; each piece its
  stretches. The P0 research (`source/expansion/pipeline__osm_lamps_signals.json`, 30 nodes, OSM base 2026-10-12) has no
  node nearer than 745 m to any piece (Jackson north's nearest, node 13715721518), so every stretch of the four pieces is
  **authored** — the plan's own label until a Street View night check.
- D4's unlit stretch: `scenery.streetlights.expansion.unlit` [{piece D, s 250-1500}] in the intermediate's station frame
  (from J4) — Kevin's 2026-10-13 default; a station inside it is skipped outright, never slid around.
- the draft ground under a piece post is the assembler's 20 m grid as before; the author then seats EVERY piece post on the
  built walk (below): on the steep pieces the walk stands 0.1-2.3 m over that grid.

### Every post seated on the built ground, every pole clear (`tools/author_lamps_blend.py` `reseat_and_check`, hard — exit 1, loop.blend not saved)

After the named relocations and the apron moves, before the model is stood up, on the authored scene's own BVH:
- `RESEAT_TOL_M` 1.0 [the P4 brief] — a loop post whose BASE (the road datum under its head: LED `head - 8.944`) stands more
  than this under or over the built surface under it is re-seated by the draft's own rule, head = that surface + 8.8 m.
  The model's footing (`streetlight_led.json` pole_bury_m 2.5) is by design and is never counted. A piece post (new in
  this build) is always seated on the built walk (tolerance 0). Every move is recorded (`lights.local.json` reseated).
- the footprint rule of the v0.18.1 relocations now runs on every post: the pole's axis + a ring of `mast_radius + 0.46 m`
  read in 16 directions must find no road surface; the pole >= `WALL_CLEAR_M` 0.5 from every wall / guardrail / K-rail
  along its whole height; its foot in the earth.
- `LENS_APART_M` 2.0 — `scripts/ac/ext_config.py` `LAMP_LINK_M`: no two heads (hence lenses) closer than this
  horizontally, or two lamps would be written as one light.
- `lamp_bases_xz` (one base per head, as built) is written for `tools/place_signs.py` and `tools/verify_race.py` G, which
  used to re-derive every base from the MAINLINE (meaningless 500 m from it, and 3.6 m wrong at J2-J4 where the signs
  stand); both take the recorded base when it is there and keep their old rule otherwise.

### One light per lamp on the written file (`tools/check_lights_ini.py`, in the track-folder step of both chains, hard)

`POS_TOL_M` 0.05 [the writer rounds POSITION to 0.01 m]: every `[LIGHT_N]` of the written `extension/ext_config.ini` must
stand within this of exactly one recorded lens (`lights.local.json` provenance.lens_xyz; kn5 frame = local with z negated,
POSITION y = lens y - 0.15), every lens must have its light, the count must equal the lamp count, and COLOR / SPOT /
RANGE / RANGE_GRADIENT_OFFSET / SPECULAR_MULT must be the config's on every block (ledger 0043 / 0056's look, unchanged:
colour 255,165,30 at 0.015, SPOT 150, RANGE 25, offset 0.5, specular 0.1). v0.18.0 shipped 4 duplicate lights out of
this clustering (ledger 0043); 238 of 238 on v0.19.0's rehearsal (r3run).

### Stills (`tools/lamp_stills_blend.py`)

EEVEE night renders off the gate OBJ: a render spot light of 16,000 W [a render number, not CSP's intensity] at every lens
within 320 m of the eye, the lenses emissive in the sodium colour; `--day` Workbench for a pole-foot close-up. Nothing of
it ships.

### Measured (the rehearsal, D:/k10-scratch/p4/lamps/run1: fresh workshop copy + fresh engine-july copy with the snapshot's files, FULL chain, `--no-install`)

| | v0.19.0 floor (r3run, installed) | P4 lamps run1 |
|---|---|---|
| lamps / CSP `[LIGHT_N]` / at their lens | 238 / 238 / 238 | **323 / 323 / 323** (A 16, B 18, C 40, D 11; all authored, 0 OSM-grounded; 23 unlit stations on D, 0 skipped for a blockage) |
| road kn5 | 89,815,220 B, 95 meshes, 1,118,236 positions | **91,373,396 B** (+1.56 MB), 101 meshes, 1,150,111 positions; largest 1KERB_sidewalk_0 62,439 (unchanged) |
| LIGHTPOST / LIGHTS meshes, largest | 15 + 1, 5,923 | 21 + 1, 5,944 |
| 1WALL_guard_0 / _1 / _release | 33,192 / 33,177 / 32,279 | the same |
| race / closure cw / closure acw / street kn5 | 11,722,654 / 5,496,964 / 5,496,156 / 872,525 B | the same |
| author seat check (new) | — | 323 lamps, 89 re-seated (loop 0 +0.89, 32 -1.16, 113 +1.27, 143 +1.25 m; 85 piece posts on their walk, +0.25 to +2.12 m), base vs ground -0.914 / 0.199 / 0.983 m, 0 footprints on a road, wall clearance min 0.667 m |
| drive_test street: soft top / severe / kinks / excursions / obstructed | 8 / 0 / 2.67 / 96 / 0 | the same |
| drive_test --line fwd / rev: kinks, excursions, soft top, severe | 2.39 / 2.53, 40 / 38, 0 / 0, 0 / 0 | the same |
| race_cw / race_acw: severe / kinks / soft top / barrier_missing / obstructed | 4 / 6, 6.46 / 6.09, 8 / 4, 0, 0 | the same |
| audit street / race_cw / race_acw | 53 / 53 / 53 | the same |
| no_route built race_cw / race_acw | PASS 0/439, leak 0 | the same |
| verify_mouths / verify_stubs / verify_pads / verify_signs | 32 / 26 + 29 / J2-J4 PASS / 19 PASS | the same |
| verify_fold_fans / rib_check (nyquist, cross-grain, step jogs, densest) / house_seat_check | PASS 3 x 3 / 87, 44, 69 (4) / PASS | the same |
| kn5_ground_check street / race_cw / race_acw | PASS x 3 (lampposts 238, no-ground 0.0 %, median -3.04 / p95 -2.97) | PASS x 3 (lampposts 323, no-ground 0.0 %, median -3.03 / p95 -2.71, hovering 0) |
| verify_race G lamps | 238/238, min margin 2.434 m | 323/323, min margin 2.434 m (lamp 53), nearest to a closure 2.741 m |
| check_lights_ini (new) | 238 / 238 / 238 PASS (run after the fact) | 323 / 323 / 323 PASS |
| terrain thinning / tiles | 983,650 -> 515,973; 1GRASS x16 (max 29,695), GRASS_FAR x4 | 983,649 -> 515,983; the same tiles |
| chain verdict | NOT INSTALLED on the two reds red since v0.18.0 | the same two, no key worse |

## 2026-10-26 — Lake Murray expansion P4 "buildings + rock" (ledger 0054 P4 step 4 and the cut faces): the buildings pass reads two caches over two bands, the cut faces split out as `1GRASS_ROCK_*`, the cut toes re-triangulated on the raised ground

No threshold is loosened and no gate is bypassed. One new self-checked ship step (`tools/rock_faces_blend.py`, inside the
prep phase after the I-8 pavement, before the split), one author step changed at its cause (`tools/ground_release_blend.py`
step 2d), one assembler pass widened (`scripts-v021/blender/build_loop_blend.build_buildings`), one reader narrowed
(`scripts/ac/ext_config.py` GRASS_MESHES), one pbr row (`1GRASS_ROCK`, engine-july-mirrored, `PENDING-MIRROR.md5`).
Every number below is invented unless marked measured. Rehearsed fresh, full chain, `--no-install`,
`D:/k10-scratch/p4/buildings` (proj/ + eng/ fresh copies; chain.log; stills/); proofs in
`tracks/san-diego-lake-murray/source/expansion/p4-proofs/`.

### The buildings pass: two bands, two caches (`build_loop_blend.build_buildings`)

- A footprint is kept when it stands within **120 m** of ANY drivable piece — the mainline, every connector
  (`data/connectors.local.json`: the four north roads, the Del Cerro sub-loop, the phase-5 stubs) and the three junction
  pads (`data/pads.plan.json`: each pad's outline as the convex hull of its arms' cut lines and its stubs' pavement) — and
  not within **half the pavement + 5 m** of any of them (the same 120 / +5 as v0.18.x, now `BUILDING_BAND_M` /
  `BUILDING_CLEAR_M`; a pad's edge is read as a pavement edge with no half width; inside a pad = crowding).
- **The old band** (within 120 m of the mainline) still reads `data/buildings.cache.json` with the mainline-only crowding
  rule and the cap: byte for byte the v0.19.0 pass. **The new band** (within 120 m of a connector or a pad and NOT in the
  old band) reads `data/buildings.expansion.cache.json` (ledger 0054 P0 step 7, 20,631 footprints, provenance beside it),
  uncapped. Measured on the rehearsal: old band 153 (v0.19.0: 153 seated), new band 181 — 61 along the north roads
  (OSM holds 74 footprints within 120 m of them: Waring 4, Princess View 32, Mission Gorge 23, Jackson north 15 — the
  Allied Gardens houses along Waring are simply not mapped), 120 along the Del Cerro sub-loop and the stubs. The
  expansion cache read in the old band would give the same 153 footprints, 0 of them new or edited since the old cache,
  so the two caches agree there and the choice changes nothing; the old cache stays the old band's by rule.
- The ship sync carries both caches and the provenance in (`tools/ship_sd.sh BUILDING_CACHES`, `ship.json
  sync_in.optional`); airoso's copies are the source of truth (the workshop's `buildings.cache.json` was byte-identical).

### The cut faces: `tools/rock_faces_blend.py` (new, prep phase, self-checked)

- Reads the SAME declaration the ground release built the walls from (`data/ground_release.auto_cuts.json`: piece,
  stations, side, `cut_reach_m` 20, `round_m` 3) and the intermediate's stations (`data/expansion.north.json`: x, z, curb
  offsets); a band per zone and side from the curb line out to `cut_reach_m + round_m + BAND_PAD_M` (**6 m**).
- Inside a band a ground triangle (1GRASS_<n>, after the prep and the thinning) is rock when it stands at
  `terrain.rock_faces.slope_min_m_per_m` = **0.70 m per metre (35 deg)** or steeper: the angle of repose of loose earth —
  steeper ground beside these roads is cut rock, not a grassed bank (the real faces climb 1.1-1.6, `auto_cuts
  face_p90_m_per_m`; the batter cap is 2.0). A zone whose measured real rise over the road (`auto_cuts
  measured.max_rise_m`) is under **MIN_RISE_M 3.0 m** [std: ledger 0054 P2 / repair round 1's own "a real wall 3 m or
  taller" bar] is a bank and gets no rock however steep a facet of it is. Clean-up: a rock patch under **MIN_PATCH_M2
  40 m²** goes back to grass, a grass hole inside the rock under **MAX_HOLE_M2 60 m²** becomes rock (components over
  the edge adjacency, across tiles by vertex position). Measured, rehearsal 5 at 12 / 20 m² and no rise bar: 17-35 m²
  outcrop speckles on Mission Gorge's south bank (`stills/run5_mg_apartments`), and the lattice's 1 m bench rows left
  as 10-20 m grass stripes across the Jackson walls; the three bars above are the answer to both.
- Self-checks, exit 1 = the blend is not saved: no rock vertex in a pavement's plan column (a ray down from 0.05 m over
  it and from 60 m over it against 1ROAD / 1KERB); no rock face centroid within **TOE_CLEAR_M 0.30 m** (plan) of a
  pavement edge; tile faces before == tile faces after + rock faces; every rock mesh under 65,535. No vertex moves: the
  split only decides which mesh a triangle belongs to; the two meshes share their boundary by position.
- Names `1GRASS_ROCK_<tile>`: the digit prefix keeps the physics, the GRASS key keeps `surfaces.ini` unchanged, and
  every gate that reads ground by the 1GRASS prefix (drive_test, audit_mesh, verify_kn5 face-up, kn5_ground_check,
  house_seat_check, rib_check) reads them exactly as before. Two readers tell them apart: pbr's `1GRASS_ROCK` row
  (before `1GRASS`; stock skin `stone_tan.png`, Lake Murray's `texture_overrides["1GRASS_ROCK"]` = its own generated
  sandstone / conglomerate pair, CC0, `textures/make_sandstone_cut.py`) and ext_config's GRASS_MESHES (no GrassFX on a
  rock wall). UVs: a wall projection per face (u along the face's strike, v up it, 4 m per tile; a top-down projection
  stretches a face this steep 1.5-3x).
- Report `data/rock_faces.json` (synced out): per zone faces / area / rise / slope; the thin toe triangles counted in
  the bands before the split (for P3 "Left").

### The cut toes re-triangulated (`tools/ground_release_blend.py` step 2d, at the cause of P3's thin lighter triangles)

- The halving chose its triangles in PLAN, on the flat, before step 2 raised the batter; a triangle from the toe row to
  the second batter row then cut through the raised face as a tooth standing flatter than the wall (lit from above while
  the wall is in shade: the pale slivers at the foot of every Jackson cut, `p4-proofs/stills/v0190_jackson_toe.png`).
- Now, after the heights and BEFORE the per-face cap (step 2c-0, so the cap and its self-check judge the final
  triangles), every triangle of a raise-only cut zone whose three corners are released (none under the pavement), whose
  centre lies within **TOE_BAND_M 30 m** of a pavement (the cut's reach 20 + its rounding 3 + the lattice's spread: the
  hillside beyond the construction zone keeps its triangles) and whose corners, edge midpoints and centre all stand more
  than **TOE_KEEP_M 0.10 m** off every drivable sheet's plan footprint (ROAD / CURB less the walk's buried apron, which
  the toe stands over by design, plus every other `1ROAD_*` / `1KERB_*` object: the corner aprons' decks, the junction
  pads, the mouth fills) is handed to Blender's beautify (`bmesh.ops.beautify_fill`, ANGLE): edge rotations only, no
  vertex moves, none is made, each rotated pair keeps the plan it covered. Counted before / after: triangles with a
  shortest altitude under **TOE_THIN_ALT_M 0.25 m** and an edge over **TOE_THIN_LONG_M 1.5 m**. The remaining thin ones
  are slivers IN the face's plane (the halving's own lattice), which share their neighbours' normal and do not show.
- Why the two fences (measured, three rehearsals): with the rotation over every raise-only face (303,611 faces, 39,909
  rotations, thin 5,277 -> 2,330) a rotated diagonal left 2 grass samples 7 mm over J1's apron deck `1ROAD_apron_AP1`
  (verify_mouths FAIL: the release's own deck set is ROAD / CURB, so neither its cap nor its batter knows the aprons or
  the pads); moving the rotation before the cap and inside the 30 m band (264,177 faces, 35,817 rotations, thin
  5,197 -> 2,255) still left them (the cap reads the same ROAD / CURB set); keeping every rotated pair off every
  drivable sheet's footprint is what makes the rotation unable to touch ground over any pavement. The final rule:
  263,599 faces in the bands, 35,692 edges rotated, thin 5,182 -> 2,258; verify_mouths 32 PASS (J1's apron deck: 0 grass
  samples at or over it, max −0.018 m as v0.19.0).

### Rehearsal vs v0.19.0 (the floor; nothing may get worse)

Six rehearsals from fresh copies (`D:/k10-scratch/p4/buildings/run.sh`, `chain.log`; the last is the one below; runs
1-5 are the fences above being found). Every gate reads as v0.19.0 (`p4-proofs/gates_v0190.txt` vs `gates_p4.txt`, a
line-for-line diff; the only differences are the ones this change makes):

| | v0.19.0 (r3run) | P4 buildings + rock (run 6) |
|---|---|---|
| Free Roam soft top / severe / kinks / edge drops / audit | 8 / 0 / 2.67 / 96 / 53 | **8 / 0 / 2.67 / 96 / 53** |
| Speedway / Reverse severe | 4 / 6 | **4 / 6** |
| Speedway / Reverse kinks | 6.46 / 6.09 | **6.46 / 6.09** |
| Speedway / Reverse barrier_missing, no_route | 0, PASS 0/439 both | **0, PASS 0/439 both** (reached 138.8 / 138.2 k m²) |
| new roads `--line expansion` fwd / rev | PASS (2.39, 40) / PASS (2.53, 38) | **PASS (2.39, 40) / PASS (2.53, 38)** |
| verify_mouths / stubs / pads | 32 PASS / 26 + 29 PASS / J2-J4 PASS | **the same, every number** |
| verify_signs / fold fans / rib_check | 19 / PASS / 69 (worst 4 of 5) | **19 / PASS / 69 (worst 4 of 5)** |
| house_seat_check | 153 judged, PASS (contact −0.303..−0.143) | **334 judged, PASS** (contact −0.330..−0.143; floating / sunken / buried 0) |
| kn5_ground_check street / cw / acw | PASS ×3 | **PASS ×3** (the same wall / lamp / sign / deck / road-over-ground lines) |
| road kn5 | 89.82 MB, 95 meshes, 1,118,236 v | **92.74 MB, 104 → 103 meshes** (16 ground tiles + 8 rock; 1,118k → ~1,177k v) |
| race / closure / street-only / spawn kn5s | 11,722,654 / 5,496,964 / 5,496,156 / 872,525 / 2,104 B | **byte-for-byte the same sizes** |
| CSP `[LIGHT_n]` | 239 | **239** (colour, pool, intensity untouched) |
| GRASS_MESHES | 16 tiles | **16 tiles** (no `1GRASS_ROCK`); OCCLUDING_MESHES carries BUILDING + HOUSE as before |
| 1WALL_guard | 65,251 pre-split → `_0` 33,192 / `_1` 33,177 | **the same** |
| end state | NOT INSTALLED (the Free Roam lap's own soft-top rule, red since v0.18.0) | **the same reds, nothing new** |

Measured on the built OBJs (`p4-proofs/analysis/compare_buildings.py`): the 153 buildings within 120 m of the mainline
are **identical** to v0.19.0's (0 re-seated by 2 cm or more, 0 missing, 0 extra); the new band holds 181 (HOUSE 128,
BUILDING 53). Rock: 10,718 faces / **12,459 m²** of cut face in 10 of the 16 zones standing 3 m or taller, 8 meshes
(`1GRASS_ROCK_2/4/5/6/7/12/13/14`, 8,077 vertices in the blend); 13,733 facets were steep, 5,214 of them under a pavement
left grass, 3,170 in patches under 40 m² back to grass, 155 hole faces filled. Per zone: Jackson north SW wall (`D_right_25_1595`)
4,431 m²; Mission Gorge north side (`C_left_635_1100`) 3,584 m², south face (`C_right_1335_2253`, s 1475-1560 in it)
2,301 m², `C_right_1070_1335` 595 m²; Princess View's left cut (`B_left_496_731`) 835 m²; `C_left_1360_1665` 222 m²,
`C_left_1665_1860` 228 m², `C_right_670_795` 156 m², `B_left_86_276` 61 m², `B_right_711_896` 46 m²
(`p4-proofs/rock_faces.json`). The cut toes: 263,599 faces in the bands, 35,692 edges rotated, thin 5,182 -> 2,258
(`cut_toe_retriangulated`); on the Jackson 320-485 cut's own face (`analysis/thin_tris.py` on the gate OBJs, the
connector's left side, s 1459-1624), thin triangles 228 -> 155 — 139 -> 99 of them 3-7 m past the pavement edge, 40
-> 13 beyond 7 m, and 38 -> 38 in the 3-4 m strip, the flat shoulder between the walk's buried apron and the first batter
row, which is kept off the rotation by the 0.10 m fence (its zigzag boundary with the batter is still visible at the foot:
`stills/p4_jackson_toe.jpg`, honestly). Tests: `tests/run_tests.py` 921 passed, 0 failed (4 new in
`tests/ac/test_pbr_rock_row.py`).


## 2026-10-26 — Lake Murray expansion P4 trees: the north network planted by zone from the aerial bins, caps by area, GrassFX confirmed (ledger 0054, P4 step 3 + 5)

**P4 trees.** `tools/make_treefx.py` plants the heightfield cells P2's growth added (the `grid_grow` block of
`heightfield.meta.json`), opt-in by `track.config.json scenery.treefx` (San Diego only; a project without the key is
today's make_treefx, byte for byte). The loop's own cells keep their numbering and their trees: the v0.19.0 reference's
`trees.txt` (D:/k10-scratch/phase1/r3run, 15,763 lines) is the first 15,763 lines of this build's, byte for byte. No
gate threshold changed; nothing is bypassed. Every number this step invents:

| Number | Value | Why |
|---|---|---|
| `NORTH_TREE_PER_CANOPY` | 2.5 [invented] | p(tree per 10 m sub-cell) = 2.5 x the aerial bin's canopy share (the 10-40 m band's NAIP CIR pixels, `source/expansion/aerial__veg_bins.json`): one ~50 m2 crown per 100 m2 sub-cell at a 40 % canopy. Waring's 5-14 % canopy lands at 0.13-0.35, the loop's own yard-band rate (`FILL_BANDS` 0.30), so the two sides of J1 are planted by the same rule. |
| `NORTH_BUSH_PER_SCRUB` / `NORTH_BUSH_FLOOR` | 2.0 / 0.05 [invented] | p(bush) = 2.0 x the bin's scrub share, + 0.05 under any canopy (understorey). |
| `NORTH_P_TREE_MAX` / `NORTH_P_SUM_MAX` | 0.85 / 0.95 [invented] | one plant per sub-cell at most (the loop's rule); a few cells stay open even in a 69 % canopy. |
| `NORTH_FAR_FROM_M` / `NORTH_FAR_FACTOR` | 120 m / 0.5 | past 120 m from the pavement the rate halves, exactly as the loop's own far band (120-200 m) halves its slope band. |
| the caps | the loop's density x the north's planted area x `cap_scale` (1.0) | EXPANSION-PLAN A9 / Risk 14: "tree caps scale with area". The loop's caps (3,500 / 9,000) over its own in-band sub-cells (471.8 ha, 47,179 sub-cells of 100 m2: 7.29 trees/ha, 18.88 bushes/ha) set the north's caps over its 201.9 ha: 1,498 trees / 3,852 bushes. Thinning is uniform over the north alone (hash salt 9, the loop's own), so the zones keep their relative density; the loop's thinning never sees a north candidate. `scenery.treefx.cap_scale` is Kevin's lever after Drive 2 (the bins imply 8,900 trees: 5.9x). |
| `NORTH_ROCK_RISE_M` / `NORTH_ROCK_REACH_M` / `NORTH_ROCK_PAD_M` | 3 m / 20 m / 5 m | a REAL wall of 3 m or more is bare rock (EXPANSION-PLAN V7's own threshold), read from P3's measurement of record (`source/expansion/p3-proofs/measure_p3.json` `walls.real_walls_ge_3m`: 16 stretches on Mission Gorge's south side and Jackson's SW side, the six walls Kevin keeps among them); nothing stands from the curb to 20 m along them (V7: the walls stand 12-20 m off), the stretch padded by the measurement's 5 m station. The lower banks (the 35 auto-cut zones) are soil and get their scrub. |
| `NORTH_MEDIAN_TREE_STEP_M` / `NORTH_MEDIAN_TREE_MIN_W_M` | 12 m / 2.5 m [invented] | A2: Waring's planted median has trees at st 250-550 (`scenery.treefx.median_trees`): one small tree (PepperV1 0.45-0.65, Oak3 0.40-0.55) every 12 m down the island's middle where it is 2.5 m or wider. |
| `NORTH_MEDIAN_INSET_M` / `NORTH_MEDIAN_END_CLEAR_M` | 0.5 m / 6 m | a median tree stands 0.5 m inside the island's outline and 6 m (author_expansion `NOSE_M`) from each nose. The islands' LOW planting is not make_treefx's: `author_median_blend` already plants every raised island, the north pieces' included (`export_scatter_blend` ships it as `median_planting`, 1,102 plants in v0.19.0, the Fontaine nose among them), so make_treefx adds no bush there — a first draft of this step doubled them and was caught on the dry-run still. |
| pads, pavement, K-rail, curbs, sidewalks | 0 plants | the J2-J4 pads are excluded by their built outlines (`data/pads.built.json`, + `APRON_PLANT_CLEAR_M` 1 m, the apron rule); every pavement including the 24 stubs is in the corridor field, and the fill starts 6 m past the curb (`FILL_BANDS`), which covers the walks and the K-rail (15 m out on the stub itself). |
| species per zone | `scenery.treefx.zones`, first match wins | A9 / dossier §6: Waring suburb mix; Princess View, the gorge sides and Jackson's canyon `north_canyon_trees` (Oak3 / Pine_Aleppo / Gum) over `north_scrub` (Sage / Yucca / Bush / Bush3 / Agave); the river belt C L 300-1200 `north_riparian_trees` (SycamoreV1 / V2 / Oak3); the apartment frontage C R 500-1000 `north_street_trees`; E1 on Jackson D L 1000-1400 `north_gum_belt` (Gum 5 : Oak3 1 — the library's Gum is the eucalyptus until Street View confirms; 0040 stays the later species pass). No palms in the canyon. |
| `verify_race --scenery-only` | unchanged, PASS | the north zones are in `plan(all_species=True)`, so G judges them before Blender as well as the written file. |

**GrassFX (P4 step 5).** No change was needed: `scripts/ac/ext_config.py` already lists every `1GRASS*` group of the
built road kn5's gate OBJ (`data/track.obj`) and nothing else; the plan's "4 -> 5-6 tiles" is superseded by the
balanced bisection (ledger 0046) + P3's thinning: **16 physical tiles, `1GRASS_0` .. `1GRASS_15`**, in both
`GRASS_MESHES` and `GRASS_MATERIALS`, the far ring (`GRASS_FAR_*`) in neither. `[TREES] SURFACE_MATERIALS` is the same
16 tiles + `1ROAD_road_mat`, read off the same OBJ (the plan's "hard-coded at :32" was already retired in 0046).

**Chain.** `tools/ship_sd.sh` and `tools/ship_track.sh` / `ship.json` sync the two research files in
(`source/expansion/aerial__veg_bins.json`, `source/expansion/p3-proofs/measure_p3.json`: `TREEFX_RESEARCH` /
`sync_in.optional`) and `data/treefx.report.json` out (per zone, per species, the north per piece, the areas, the caps);
the make_treefx step prints the loop's and the north's planted areas, densities and caps before anything is written.
The step title changed in both chains together (parity test green).

**Tests** (`tests/tools/test_make_treefx_plan.py`, +7): the config plants the added cells and moves nothing of the
loop's (every `fill_*` entry identical with and without it; `north_*` only with it, 6 m off every pavement, never in the
loop's block); density follows the bins per side and station (a bare bin plants nothing, a scrub-only side gets no
trees); nothing on a pad or a measured wall, a bank under 3 m keeps its plants; median trees only where declared, on
raised planted medians only, never a duplicate of the assembler's low planting; the caps scale with area at the loop's density and `cap_scale` scales
them; `build` writes the zones and the report; a declared zoning with a missing bins file is an error.

### Measured (the rehearsal, D:/k10-scratch/p4/trees: fresh workshop copy minus build/release + fresh engine-july copy, nothing pending in the mirror, FULL chain, `--no-install`; `gates.txt` kept as `source/expansion/p4-proofs/gates_trees.txt`)

Every v0.19.0 gate number (the floor, r3run) is unchanged — the only built file that differs is `trees.txt` (and the
tree-count comment in `ext_config.ini`; the ini is otherwise byte-identical to the reference's, lights included):

| | v0.19.0 reference (r3run) | P4 trees rehearsal |
|---|---|---|
| road kn5 | 89,815,220 B | 89,815,866 B (+646 B, run to run; ceiling 145 MB) |
| 1GRASS tiles / GRASS_FAR after the thinning | 16 (max 29,695 v) / 4 (max 38,122 v) | 16 (max 29,693 v) / 4 (max 38,122 v) |
| verify_mouths / verify_stubs / verify_pads | 32 / 26 + 29 / J2-J4 PASS | the same (seams 1.2 / 0.7 / 2.4 mm, nodes -0.019 / 0.039 / 0.017 m) |
| verify_signs | 19 PASS (M3 / M4 skipped until P4 signs) | 19 posts, 19 plates, PASS |
| rib_check step jogs (densest 75 m) | 69 (4, limit 5) | 69 (4) PASS |
| house_seat_check | 0 floating / sunken / buried | the same, PASS |
| drive_test street: soft top / severe / kinks / excursions | 8 / 0 / 2.67 / 96 | 8 / 0 / 2.67 / 96 |
| drive_test --line fwd / rev: kinks, excursions | 2.39 / 2.53, 40 / 38, PASS both | the same, PASS both |
| race_cw / race_acw: severe / kinks / barrier_missing | 4 / 6, 6.46 / 6.09, 0 | the same |
| audit street / race_cw / race_acw | 53 / 53 / 53 | the same |
| no_route built race_cw / race_acw | PASS 0/439, 138.8 / 138.2 k m2 | the same |
| verify_fold_fans | PASS 3 x 3 | PASS 3 x 3 |
| kn5_ground_check street / race_cw / race_acw | PASS x 3 (lampposts 0.0 %, road-over-ground 12/10785) | PASS x 3, the same numbers |
| CSP `[LIGHT_n]` blocks / `[GRASS_FX]` | 238 / 16 tiles, no far ring | 238 (byte-identical blocks) / 16 tiles `1GRASS_0`..`1GRASS_15`, no far ring |
| `[TREES] SURFACE_MATERIALS` | 16 tiles + `1ROAD_road_mat` | the same |
| verify_race --scenery-only (plan, then the written file) | 15,739 trees, 0 in a lane / wall | 21,171 trees, 0 in a lane / wall, 392 beside the race road; nearest 0.654 m (the same median plant as before) |
| trees.txt | 15,763 lines, 1,129,790 B | 21,219 lines, 1,528,168 B; **the first 15,763 lines byte-identical** |
| TreeFX instances | 15,739 | 21,171 (+5,432: the north's 5,406 fill + 26 median trees) |

Per species, reference -> this build (the delta is the north's): Agave 831 -> 1,125; Bush 2,967 -> 3,912; Bush3 1,330
-> 1,905; Gum 1,123 -> 1,423; Oak3 704 -> 1,366; PalmV1 679 -> 710; PalmV2 274 / PalmV3 102 unchanged; PepperV1 620 ->
681; Pine_Aleppo 765 -> 1,173; Sage 4,259 -> 5,725; SycamoreV1 407 -> 497; SycamoreV2 66 -> 90; Yucca 1,612 -> 2,188.
Per piece (`data/treefx.report.json`): **A Waring 691** (Bush 233, Bush3 181, Sage 165, PepperV1 35 — 26 of them the
median trees — Oak3 28, SycamoreV1 22, PalmV1 14, Gum 7, Pine 6); **B Princess View 1,124** (Sage 367, Bush 184, Yucca
174, Bush3 107, Agave 93, Oak3 90, Pine 69, Gum 40); **C Mission Gorge 1,965** (Sage 515, Bush 299, Oak3 247, Yucca 220,
Bush3 186, Pine 143, Agave 126, Gum 95, SycamoreV1 67, PepperV1 26, SycamoreV2 24, PalmV1 17); **D Jackson north 1,576**
(Sage 394, Oak3 297, Bush 196, Pine 189, Yucca 182, Gum 158, Bush3 85, Agave 75); the 150-200 m ring the growth added
around the loop's own roads 76. The loop's planted area 471.8 ha (47,179 in-band sub-cells; 7,263 / 18,114 candidates,
kept 0.482 / 0.497 to the caps: 7.29 trees/ha, 18.88 bushes/ha); the north's 201.9 ha (20,195 sub-cells): the bins imply
8,900 trees / 3,988 bushes, the caps 1,498 / 3,852, kept 1,550 / 3,856 (the hash thinning lands within 4 % of a cap);
dropped on a pad 55, on a measured wall 160. The chain ends `NOT INSTALLED` on the same two reds v0.19.0 carries
(Free Roam's own soft-top / excursion rule and the Speedways' own drive test; `--force-install` under 0047's rule, no key
worse). Tests: the whole suite, `tests/run_tests.py`.

## 2026-10-26 — Lake Murray expansion P4 signs: the north corners, the Speedways' own M3 / M4 plates, the per-layout map (ledger 0054 "P4 signs")

No threshold is loosened and no gate is bypassed. The W1-6 rule (tools/place_signs.py, tools/author_signs_blend.py)
learns two kinds of corner it could not see, one gate gains a check per layout, two content guards admit a race layout's
own plates into its closure kn5, and the map gets an opt-in scope. Every invented number is here.

### The rule (tools/place_signs.py)

| what | number | why |
|---|---|---|
| the stitched north ribbon "north" (`tools/expansion_lines.centre_ribbon`): the four pieces' connectors strung J1 → J5 through the pads on the drive lines' own cubic (`stitch`), scanned both ways | no number (the pieces' own points and widths; the cubic's handles a third of the chord, as `expansion_lines.bezier` already had them) | each piece ends at its pad's cut, so no piece carries the turn made ACROSS the pad; the pieces' own scans only ever found their mouth-flare ends (v0.19.0: 19 "north_*" skips, 0 plates) |
| the junction pads' BUILT decks (data/pads.built.json outline, stub arms included) as pavement polygons in the field; the north drive lines (`expansion_lines.compute_lines`) as disc-only ribbons `expansion_fwd` / `expansion_rev` | no number | the ray crosses the deck and leaves at a curb return or down a stub arm (A8); a north post must clear what `drive_test --line expansion` sweeps, which is the lane, not the piece's centreline |
| the pieces' pad ends are not mouths for the north ribbon (`Context.mouth_excludes`); the J1 / J5 cuts stay | — | they are its own interior; for the pieces' own scans they still are mouths (unchanged skips) |
| foot window past PT for a ray that leaves through a pad: `RAY_PAST_PT_M` 10 + the pads' stub reach (`pad_stub_reach_m`: stub_length_m 15 + tail_m 1 = **16 m**, read from data/pads.plan.json) | 16 m, read, not invented | a foot 16 m down a stub arm is still the turn's own outside (J4-fwd: PC+46 on an arc of 26) |
| **THROUGH_ROAD_M 8 m** ⚠ invented: a failed-to-turn ray that runs ≥ 8 m along ANOTHER road's pavement before it leaves pavement is the rule's own skip ("a through road"); a pad deck, a `STUB_*` connector and the north ribbon's own four pieces never count | 8 m: wider than a mouth flare crossed at its corner (a 10 m street's corner, crossed obliquely, is 2–5 m), narrower than any carriageway pair; M3-rev measured 16 m across the Waring opening | v0.19.0's M3-rev (Navajo westbound) would have stood at the Waring mouth's far corner with a left arrow pointing away from Waring; `verify_signs` RULE_SKIP_RES accepts the wording as the rule's own |
| a `per_layout` MAINLINE corner (signs.json, validated: bool, MAINLINE only, never with skip): the shared attempt as always, then for each race layout that drives the approach and got no shared plate a LAYOUT PLATE on the MAINLINE's field alone (`PavementField.query(only=("MAINLINE",))`), standing `edge_centre_from_lip_m + barrier_half_m + lateral_offset_m` past the lip = **−0.485 + 0.335 + 1.63 = 1.48 m** (data/barrier_bands.json params + the curb rule's own offset; no race declaration = a skip the verifier counts as the rule's) | 1.48 m is DERIVED: the sealing curb strip's far face stands in for the curb face, the curb rule's 1.63 m behind it | A7: "both move into the Speedways' own race files … just past the outside edge, now on the sealed opening"; the mouth-flare rule does not apply to a layout attempt (the mouth IS the sealed opening) |
| ids: `<corner>-<dir>@<layout>`; a layout plate never pairs; skipped ids dedupe per layout | — | `verify_signs.parse_id` strips the layout |

### The mesh stage (tools/author_signs_blend.py, tools/signs_mesh.py)

| what | number | why |
|---|---|---|
| **WALL_CLEAR_M 0.5 m** (reused: tools/author_lamps_blend.py's WALL_CLEAR_M): every post ≥ 0.5 m from every 1WALL* face (`signs_mesh.load_wall_bvhs()["all"]`, measured 0.6 m up the post), a march criterion and a final check; `verify_signs` (w) re-measures it | 0.5 m, the lamp rule's | a north post marches past a stub's K-rail; a mainline post beside a guard rail |
| a LAYOUT PLATE on the mesh: the ray walked from 4 m before the polyline lip to **LAYOUT_WALL_SCAN_M 30 m** ⚠ invented past it; the layout's wall (`load_wall_bvhs()[token]`: RACE + RACE_CLOSE_<TOKEN>, 1WALL_RACE* names) entered at s_in, left at s_out; the post from s_out + lateral_offset_m on until the NEAREST face of that wall is ≥ lateral_offset_m (1.63) away, capped `RAY_EXTRA_CAP_M` 6 m past s_out; y_base = the highest of ROAD / ground (it stands on the sealed opening's deck, never pushed off ROAD); checks: wall clearance 1.3–3.0 m (the mainline's `GATE_MIN` / 3.0, measured to the wall), on no wall, the MAINLINE disc, every wall ≥ 0.5 m | 30 m: the widest opening (Jackson north 29.5 m) crossed obliquely; 1.3 / 3.0: the mainline curb range, unchanged | M4-rev@race_acw's ray crosses the curved strip at J5 obliquely: 1.63 m along the ray was 1.16 m from the wall (refused), the nearest-face march puts it at 1.62 |
| **SIDE_STEP_MAX_M 2.5 m** ⚠ invented: a CONNECTOR / north post whose march caps with no clear point on the ray (a grazing exit: the ray leaves the pad's curb return at so flat an angle that no point within the cap clears the curb) steps square off the ray, to the OUTSIDE of the turn, until the built clearance, the gated disc and the walls hold; recorded as `checks.lateral_step_m` + `ray.side_step_from_m` | 2.5 m: a plate width past the 1.5 m behind-the-walk cap | J2-rev (0.90 m) and J3-rev (1.15 m) at the pads' curb returns; the polyline stage already stepped sideways at its cap (`lateral_step_m`), the mesh stage had no fallback and skipped both |
| meshes `SIGNPLATE_<token>_<k>` / `SIGNARROW_<token>_<k>` / `SIGNPOST_<token>_<k>` linked into RACE_CLOSE_<TOKEN>; the signs step moved AFTER the race furniture (ship_sd.sh, ship.json, ship_track.sh), every ship | — | tools/author_race_furniture_blend.py empties RACE_CLOSE_* on every ship |

### The gate (tools/verify_signs.py)

| check | before | after | number |
|---|---|---|---|
| Field | the centrelines | + the north ribbon (rebuilt here from the connectors, `el.centre_ribbon`), the drive lines as disc-only (`el.compute_lines`), the pad decks (`el.pad_polygons`) for `edge()`; `gated` = MAINLINE + the lines | — |
| (a) ray hits plate | ±0.61 m | + the recorded square side step + 0.1 m, ONLY when this gate's own ray, on its own field, confirms the grazing exit (`Field.grazing`: off pavement, the edge distance stays under the target 1.33 / 1.63 for the whole 6 m cap); an unconfirmed step keeps ±0.61 | 0.1 m: the march's own quantisation |
| (c) clearance, LAYOUT kind | — | to the layout's wall: the scan's `layout_wall_m` (nearest face of RACE + RACE_CLOSE_<TOKEN>) and the analytic MAINLINE-lip distance minus the record's declared strip offset; 1.3–3.0 m | the mainline's range |
| (e) (f) LAYOUT | ground = the ground top | ground = the highest of ROAD / ground under the post (the deck) | — |
| (g) LAYOUT | not on ROAD | on ROAD allowed (behind the wall), on no wall (`on_wall` from the scan), the MAINLINE disc only | — |
| (i) spacing | every pair | pairs one layout can load together (two layouts' own plates never meet) | 2.0 m unchanged |
| (k) RULE_SKIP_RES | — | + "ray runs N m down X before leaving pavement (a through road)", + "no race declaration (…)" | — |
| **(m) layout coverage (new)** | — | per layout of track.config.json, in its direction: every MAINLINE corner with a plate anywhere has a plate THAT layout loads (shared, or its own) or a skip for that direction applying to it (shared, or carrying its id) whose reasons are coverage as (k) words them | none (structural) |
| (w) wall clearance (new) | — | every post ≥ 0.5 m from every 1WALL* face (the scan's `wall_m`) | 0.5 m |
| the measurement | — | `signs_measured.json` gains `wall_m`, and per layout plate `layout_wall_m`, `on_wall`, `layout_walls` | — |

Teeth: tests/tools/test_p4_signs.py (the field, the through-road rule, a per_layout corner on a synthetic square with a
Waring-like street, (m), the names, both kn5 guards, the map, the chain order).

### The kn5 guards (tools/race_furniture.py, tools/split_exports_blend.py, tools/check_race_kn5.py, scripts/ac/verify_kn5.py, tools/verify_race.py)

| guard | before | after |
|---|---|---|
| `race_furniture.race_role` / `race_owner` | close / edge / kerb / kbar / other | + `sign` for `SIGN(PLATE|ARROW|POST)_<token>_<k>` (`layout_sign_owner`; a material `<object>_mat` matches on its object; the road kn5's `SIGNPLATE_<k>` never match) |
| the export split | the closure scene = ITS closure walls | + ITS sign plates; the common scene refuses any sign plate; `_classify` / the census count sign plates as race objects; sign materials allowed in a closure scene |
| `check_race_kn5 --role closure --owner T` | every mesh 1WALL_RACE_CLOSE_T_* | or T's own sign plates; their textures (the SIGNPLATE / SIGNARROW / SIGNPOST rows of pbr.py, read from the table) allowed in that file only when such plates are present; `--role common` refuses any sign plate |
| `verify_kn5` (f) closure kn5 | 1WALL_RACE_CLOSE_T_* only | + T's own plates and materials (`layout_sign_owner`, restated: the gate reads only the kn5) |
| `verify_race` G scenery | every sign post vs every race layout | a layout plate vs its own layout only (the item carries `layout`) |

### The map (tools/make_map.py)

`layouts[].map`: `"network"` (default, as before: byte-identical maps) or `"lap"` = that layout's map.png + data/map.ini
from the mainline alone, to its own extent, and `ui/<id>/outline.png` redrawn the same way (track_folder's colours);
any other value refused. The root map is always the network. Lake Murray: the two Speedways `lap`, Free Roam the network.

### Measured (the dev pass on the v0.19.0 reference loop.blend, D:/k10-scratch/p4/signs/dev)

29 posts, 29 plates: the 19 of v0.19.0 byte-for-byte in base and facing (every row `ok`), **J2 / J3 / J4 both ways** (six;
J2-rev and J3-rev by the square side step, 0.90 / 1.15 m, confirmed by the gate's own ray; J4-fwd behind the Mission
Gorge east stub's K-rail, 3.44 m from it, clearance 2.75 m) and **four layout plates**: M3-fwd@race_cw (wall 1.67 m, on the
Waring mouth's deck), M3-rev@race_acw (1.61 m, the loop's walk at Waring's south-west corner), M4-fwd@race_cw (1.76 m,
the walk east of the Jackson-north mouth), M4-rev@race_acw (1.62 m, the mouth's deck). Shared skips: M3-fwd "ray never
leaves pavement" (College into Waring), M3-rev "ray runs 16 m down north_J1_waring#0 (a through road)", M4-fwd / M4-rev
"apex 13 m from the J5 mouth". (m): street M1 M2 M5 + M3 / M4 skipped by the rule; race_cw / race_acw every corner.
verify_signs PASS. The rehearsal of the full chain is in ledger 0054 "P4 signs" (its numbers below once it ran).

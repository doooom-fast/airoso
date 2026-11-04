---
id: 0054
title: "Expand College down Waring to Princess View, Princess View to Mission Gorge, Mission Gorge to Jackson, then extend Jackson down to Mission Gorge" — the Lake Murray network grows north, phase 1
status: open
scope: tracks/san-diego-lake-murray (routes, connectors / network, terrain extent, layouts); the SD ship chain; engine where the plan says so
layer: project + engine
train: -
---

## Request (Kevin, 2026-10-12)

> "i have another plan instead of the lariat rebuild so let's shelve that for now. we're going to expand college down
> waring to princess. view, princess view to mission gorge, and mission gorge to jackson, then extend jackson down to
> mission gorge. we'll add to the network map instead of building the lariat. save the plan for the lariat for after
> we've built a few phases of lake murray"

The roads, in Kevin's order: **College Ave → Waring Rd → Princess View Dr → Mission Gorge Rd → Jackson Dr**, and
**Jackson Dr extended from the loop down to Mission Gorge Rd**. "Add to the network map": the drivable San Diego
network grows; this is the first of several Lake Murray phases (the Lariat, ledger 0048, waits for "a few phases").


> "the new loop will connect to the old one" (Kevin, 2026-10-12, right after)

So the expansion is **one network with the existing loop, not a second track**: the new northern loop shares the
College/Navajo corner (Waring straight on) and the Navajo/Jackson corner (Jackson north). Both corners become real
four-way junctions you can drive through in every direction in the street version.


> "this will be called lake murray free roam vs the lake murray speedways (clockwise is normal, counterclockwise is
> reverse)" — "we may add mission gorge speedway etc" (Kevin, 2026-10-12)

**Names.** `<Area> Free Roam` is the open network; `<Area> Speedway` is a race layout, clockwise the normal direction,
anticlockwise `<Area> Speedway Reverse`. Applied 2026-10-12: street → **Lake Murray Free Roam**, race_cw → **Lake
Murray Speedway**, race_acw → **Lake Murray Speedway Reverse** (config `layouts[].name` / `ui_description`, the
release READMEs, and the installed v0.17.1 `ui/<id>/ui_track.json`, originals in
`D:/k10-track-archive/2026-10-12_ui_names_before_rename/`). Layout ids stay (folder names: saved setups and records
survive). With the expansion, Free Roam is the whole connected network; a **Mission Gorge Speedway** (+ Reverse) on
the new roads is a candidate for a later phase.

## First read (from the cached OSM, `data/osm.json`, fetched 2026-08-10, bbox 32.760-32.808 N — preliminary)

- College Ave's north end (32.7938 N, −117.068) is where **Waring Rd** begins westward and **Navajo Rd** begins
  eastward: the loop's existing College/Navajo corner (open race box v1506-1521). "College down Waring" = carry on
  through that corner onto Waring instead of turning onto Navajo.
- Waring Rd in the cache: 32.7938-32.7980 N, −117.0759..−117.0676 (it runs on north-west past the cache).
- **Princess View Dr is outside the cache**; Mission Gorge Rd appears only at its edge (32.807-32.808 N,
  −117.077..−117.071); Jackson Dr runs to 32.812 N in the cache. A fresh Overpass fetch (TLS on, staleness guard) is
  the first step.
- "Extend Jackson down to Mission Gorge" starts at the loop's Navajo/Jackson corner (open race box v2311-2328) and
  runs north, downhill to the river valley.

## Status

**Open — 2026-11-04 (step 2d): PLANNED, held** (see "Phase 2 — step 2d" at the end: the PC's seating fix 22988c6 cherry-picked; J4's inside kerb pulled back to v1457-v1462 by its own geometry; the author's inside-out pre-check now reads verify_race I's record; the PC re-runs 0.20.2 with no install). Was: **Open — 2026-11-04 (step 2c): PLANNED, held** (see "Phase 2 — step 2c": the PC's step 3 passed all five joins; Princess View's wide median was two street trees on the aerial, fixed at the source and carried to a scratch loop.blend by tools/reshape_island_blend.py; strip keep 0.03; plan_north PLANNED, 34 / 34 sealed, planned no_route PASS, no gate moved; the PC builds 0.20.2 with no install). Was: **Open — 2026-11-04 (later): the PC's step 3 answered on the Mac, held** (see "Phase 2 — step 2b": J2-J4 refit onto the built pads, every north median where it stands, five noses; 34 / 34 sealed, planned no_route PASS; ONE self-gate line left for Kevin — Princess View's real 5.9 m median leaves a 6.42 m lane against the 6.5 m hard minimum; the PC re-judges the joins). Was: **Open — 2026-11-04: Phase 2's two tools built and proved on the Mac, held** (see "Phase 2 — step 2" at the end: the median-nose closure end and the station smoothing, opt-in and byte-identical off; laps in tools/ship_track.sh; the north plan PLANNED with every self-gate clear, 34 / 34 exits sealed, planned no_route PASS; the PC runbook builds 0.20.2 through ship_track.sh, held from install). Was: **Open — 2026-11-03: Phase 2 (the Mission Gorge Speedway) declared and planned on v4, held** (34 exits sealed in the plan, the median noses open). Was: **Open — v0.19.0 INSTALLED 2026-10-20 (Drive 1; Kevin 2026-10-26: "the barriers look great"); P4 (lamps, signs + map, trees + GrassFX, buildings + rock) INTEGRATED on one branch as v0.19.1 2026-10-26, rehearsed, refuted by the four lenses, fixed at the causes and rehearsed again, not installed** (see "P4 — dressing, integrated" at the end: no tree on a rock face / walk / in a building, buildings at their true place with no wall on a walk, the cut toes a row not a saw; every v0.19.0 gate number equal; Drive 2 is Kevin's `--force-install`). Was: **P4 trees built and rehearsed on a branch 2026-10-26, not merged** (see "P4 trees" at the end: the north network planted by zone from the aerial bins at the loop's density, Waring's median trees, GrassFX confirmed at 16 tiles; every v0.19.0 gate number unchanged; the other three P4 pieces run in parallel). Was: **Open — P3 repaired a third time and rehearsed again on the branch 2026-10-19, v0.19.0, not installed** (see "P3 repair round 3" at the end: the ground thinned before the export without moving a point, the road model back to about 90 MB; the lamp-post check finds each lamp's own foot; the J1 question for Kevin still open). Was: **Open — P3 repaired a second time and rehearsed again on the branch 2026-10-19, v0.19.0, not installed** (see "P3 repair round 2" at the end: Jackson's painted median and Princess View's centre lane put where the aerial shows them, three raised islands added or moved to their real places, Mission Gorge's south rock face raised 0.3-0.5 m, the model export's duplicate barrier piece fixed; the three existing layouts no worse than v0.18.1; the J1 question for Kevin still open). Was: **Open — P3 repaired and rehearsed again on the branch 2026-10-19, v0.19.0, not installed** (see "P3 repair round 1" at the end: the three checks' refusals fixed at their causes — the drive test's late exemption removed and its verdict written as it works, kn5_ground_check run on all three layouts, every real wall beside the new roads kept, the holes in the hillside closed, the corners on the real ground, Glenroy St's south-west leg and Doreen Rd stubbed; the three existing layouts no worse than v0.18.1; one question for Kevin: tilt the College/Navajo crossroads to its real slope?). Next: Kevin's Drive 1, then P4 dressing. Was: **Open — P3 (the north roads) built and rehearsed on a branch 2026-10-19, v0.19.0, not installed** (refuted by three checks; see "P3" at the end: four roads, three junction pads, two permanent welds, 24 barrier-closed side streets, six cut slopes kept; every gate of the three existing layouts no worse than v0.18.1; the new roads driven both ways PASS). Next: Kevin's Drive 1, then P4 dressing. Was: **Open — P2 (the ground over the expansion) done on a branch 2026-10-14** (see "P2" at the end: the grown heightfield, the pin's 37 / 26 and the re-keyed cache in one change; the tiers planned over the held north network; 3DEP fetched; the existing three layouts byte-identical to v0.18.0 on every drive, mouth and route gate; the loop's ground within 150 m unchanged except beside the two weld mouths; six cut-wall stretches listed for P3's hand authoring; the low clause restated). Was: **Open — P1 done on a branch 2026-10-14, after a fix round** (see "P1 fix round" at the end: both new mouths pass verify_mouths, J1's R 30 return is built as apron AP1 to v1526.3, no road lies over another at either mouth, no step over 6 cm at J5 in any layout on the real wheel paths, both Speedways sealed; the existing three layouts equal to v0.18.0 key for key). Was: **Open — P1 (the readable intermediate, the numbered map, the J1 / J5 weld rehearsal) done on a branch 2026-10-14** (refuted: J5 failed verify_mouths, drive_test still read 6-8 cm steps at J5). Was: **Open — P0 (data, no geometry) done on a branch 2026-10-14** (see "P0" at the end: guarded OSM + buildings, `north`
appended with full/medium/short byte-identical, config per D2, `grid_grow` + frame pin + cache remap proven; the grown
grid, the pin's offsets and the re-keyed cache land together in P2). Next: P1, the readable intermediate. Was: **Open — planned 2026-10-13** (`tracks/san-diego-lake-murray/EXPANSION-PLAN.md`, revision 2 after an independent critic; place facts in `DOSSIER-EXPANSION-NORTH.md`). Kevin's answers to D1-D4 pending (D3 amends law L3: needs his explicit yes). Was: **Open — research and plan first** (dossier-style: routes, junctions with the loop, elevation and the gorge,
widths and medians off the aerial, terrain extent, layouts, budget, gates), then the build after v0.18.x lands
(terrain 0046 + the seat fixes 0050-0053), because it shares every file those touch. Diagnosis n/a (a request).

## Verification

Decided in the plan, before geometry. At minimum: the new roads match OSM + aerial in plan (paint where visible),
3DEP in profile (L5, on the built road), every new mouth on the loop passes `verify_mouths`, the race layouts stay
sealed (`no_route` PASS) with the new mouths closed, the existing three layouts' gates no worse, and Kevin's seat.

## Kevin's answers to the plan (2026-10-13)

> "Why are wec changing ridges? Defaults to the rest"

- **D1, D2, D4: defaults** — no Mission Gorge Speedway in phase 1; the far ring grows north to 32.850 / west to
  −117.108 with the Cowles patch to 32.828; lamps everywhere except Jackson's open canyon (~90).
- **D3: keep the real ridges.** The 24.3 m / 11.6 m figures in the plan were what the 0046 rule *as written* (80 m full,
  250 m release) would do beside the two hillside roads; the plan's default (the iron reaches 40 m from the pavement,
  3DEP beyond) moves **0** of 4,050 transect points on them. Kevin's question is the principle: **real ridges are not
  changed.** Taken as the yes to D3's default, and as the direction for the loop too — the v0.18 terrain still irons
  the loop's hills 80-250 m out (the 0046 truth lens: up to 13.7 m low 92-119 m from Navajo's pavement), so the same
  40 m reach is measured on the loop next and applied there unless it breaks a gate.

**Measured on the loop (2026-10-13, read-only, independent check not refuted; scratchpad `ridges/`).** Fresh 3DEP
transects every 50 m on the mainline and all four connectors, 5-300 m each side (41,486 points). The 0046 clamp as
written (80 m full / 250 m release) moves 2,035 points by > 1 m, all 40-250 m from a road: it fills the canyon north
of west Navajo by up to 25 m, planes the Navajo-side ridge and the ridge west of College by 12-18 m, and fills the
hollows beside the Del Cerro climb by up to 16 m. **Inside 40 m it moves nothing** (the conform corridor 20 m + 16 m
blend already shapes 0-36 m). A reach that eases out between 20 and 40 m (`terrain.clamp_corridor_m` 20,
`terrain.clamp_blend_m` 40) moves 0 points by > 1 m on the loop AND on every expansion road (largest 0.01 m) — one
global setting, so D3's per-road clause is not needed. On the v0.18 gate OBJ it takes the 80-250 m band from max
25.2 m off 3DEP to 1.8 m; within 20 m, 0.000 m moves; tile counts unchanged; rib_check PASS. A hard 40/40 cut would
leave a 2.2-2.4 m step beside Alvarado, so 20/40 it is. **To apply in v0.18.0 before it ships**, with LAWS L3 and
GATES-CHANGELOG amended in the same commit and one full rehearsal.

**Applied in v0.18.0 (integration, 2026-10-13; not installed).** `terrain.clamp_corridor_m` 20 / `clamp_blend_m` 40 in
track.config.json, LAWS L3 and GATES-CHANGELOG amended in the same commit, one full rehearsal: 3,363 loop terrain
vertices moved by more than 1 m against the pre-change v0.18 build (max 25.24 m), none within 20 m of a road; every
drive / audit / no_route verdict identical to v0.17.1 before 0050; `rib_check` PASS; from v1640 the hill in front of
Cowles now stands at 7.157° (3DEP 7.231°; it was 6.600°). Details in ledger 0046 "Integration (v0.18.0)". Integration fix round 3 (2026-10-13): kept at 20 / 40 with the freeway off; LAWS L3's bullet now reads Kevin's principle (near-road relief is shaped to the road within the road's own construction zone, ~20-40 m; real relief beyond is never reshaped); from v1640 the hill reads 7.157° against fresh 3DEP's 7.215° (ledger 0046 "Integration fix round 3").

## The roadmap of Lake Murray phases (Kevin, 2026-10-14)

> "Phase 3 will be waring to Zion, Zion to mission gorge"

- **Phase 1** (this entry, building): Waring (J1→J2), Princess View (J2→J3), Mission Gorge (J3→J4), Jackson north
  (J4→J5). Free Roam only.
- **Phase 2: Mission Gorge Speedway** (+ Reverse) — confirmed by Kevin 2026-10-14 ("Phase 2 is correct"); the plan's
  D1 default. Needs the race tools generalised past one lap line first (every race tool counts along one lap by point number).
  **Builds on v4** (ledger 0065 verdict, Kevin 2026-11-03: "Lake Murray v4 should be what we build the rest from"): every
  Phase 2 declaration counts along v4's committed intermediates (`claude/lm-v4-line`), the PC builds on its `lm_v4` workshop
  line, and v4's 7,600 houses ride along under the `houses` gate.
- **Phase 3 (Kevin):** **Waring from J2 south-west to Zion Ave (~0.6 km), Zion Ave west to Mission Gorge Rd
  (~1.6 km, 32.7927-32.7930 N, from Waring at −117.0807 to Mission Gorge at −117.0976, fresh OSM 2026-10-14),** and
  Mission Gorge Rd from Zion back up to J3 (~2.3 km) so it joins the network. A western loop J2 → Waring → Zion →
  Mission Gorge → J3 → Princess View → J2; Princess View stays. Terrain: Zion's west end lies inside the D2 far box
  (west −117.108) but ~1.6 km west of phase 1's grown physical grid edge (−117.0807), so phase 3 grows the grid
  again with the same whole-cell pin + `tools/remap_sample_cache.py` (no old node moves).

- **Phase 4 (Kevin):** *"And then phase 4 will be waring to 8, and we'll start working on freeway ramps. 8 will then
  go to college one way and mission gorge the other"* — Waring Rd south from Zion to its I-8 interchange (~−117.09),
  the freeway ramps, and **I-8 itself drivable** east to the College Ave interchange (the loop's own College deck,
  ~−117.06/−117.07) and west to the Mission Gorge Rd / Fairmount Ave interchange (~−117.10/−117.11): about 3.9 km each
  way (fresh OSM 2026-10-14; 71 I-8 motorway ways in the box). This settles the I-8 question for the long run: the
  freeway becomes real, drivable road in phase 4 (physics, ramps, decks over it), not the drawn see-only freeway the
  v0.18.0 integration added and then switched off. Reusable: the SD freeway network track's data/tools (registry
  `k10-san-diego` freeway), `tools/author_freeway_blend.py` (visual, OFF), the College/LMB bridge bodies from 0046.
  Terrain: the Mission Gorge/Fairmount interchange is near the D2 far box's west edge (−117.108) — phase 4 grows the
  physical grid west again (same pin + remap).

- **Phase 5 (Kevin):** *"We are going to change intersections, such that a road we are not completing gets a barrier,
  not a curve. That's phase 5"* — every unbuilt side road keeps its mouth and a short stub, closed by a **barrier
  across it**, instead of today's curb return that curves the curb round and erases the road. Network-wide (the old
  loop's sealed side streets and every expansion mouth), all layouts. Until then, phase 1's new junctions and stubs are
  built so phase 5 can swap the curb return for a barrier without rebuilding the road (the stub ribbon and mouth are
  kept; only the closure object changes). Touches: `docs/JUNCTIONS.md` R18(c) (stub = curb returns + invisible wall),
  `gap_mouths_blend` / the sealed-mouth curb sweep, the Speedways' sealed-mouth policy (`barrier_bands` mouths,
  `no_route` probes), `verify_mouths`.

(Naming: the plan's build steps P0-P7 are *steps*; "Phase N" is Kevin's expansion phase.)

**Parallel work (Kevin, 2026-10-14: "Yes and a").** Started alongside Phase 1: the Phase 2 groundwork (race tools
taught a second lap, proven byte-identical on both Lake Murray Speedways; the Mission Gorge Speedway design), the
Phase 3 + Phase 4 plans (read-only research), and the Phase 5 barrier-stub tool — **option (a): Phase 1's ~24 public
side streets get barrier stubs from the start**, not curved curbs later. Phase 5 proper (converting the old loop's
side streets) keeps its place in the order.

**Phase 3 and 4 plans (2026-10-14).** `tracks/san-diego-lake-murray/EXPANSION-PHASE3-PLAN.md` (Zion western loop:
4.60 km of new road, loop 5.71 km, J6 Waring/Zion, J7 Zion/Mission Gorge, Zion drops 66 m at up to 10 %, Mission
Gorge's 28.7 m sag becomes the network's low point, 35 barrier stubs) and `EXPANSION-PHASE4-PLAN.md` (Waring south
1.59 km to I-8; I-8 EB 2.85 km Fairmount on-ramps -> College exit, WB 2.36 km College on-ramps -> Mission Gorge exit;
ramps at X8/X9/X10; Mission Gorge south through Grantville incl. Friars Rd; at Waring I-8 is two levels up to 18.8 m
apart), place facts in `DOSSIER-EXPANSION-WEST.md`. Revision 2 after an independent critic (11 errors fixed). Decisions
with defaults pending Kevin; the big one is the **lamp weight**: Phase 4 projects to 161-174 MB of road kn5 without a
lighter streetlight model.

**Lamp weight, measured on the installed v0.18.0 road kn5 (116.3 MB; 42 meshes, 1,697,179 verts, 2,026,253 tris;
`scripts.modkit.inspect_kn5 --json`):** LIGHTPOST = 17 meshes, **966,725 verts (57.0 %) and 899,835 tris (44.4 %)** for
243 lamps (~4,000 points each; six LIGHTPOST meshes sit at the 65,535 cap). All drivable ground (1GRASS) is 357,262
verts (21.1 %). A lamp ~10x lighter would remove ~870k verts — the single biggest load-time lever, and the precondition
both expansion plans name before more lamps. The lamp is Kevin's own model ("Kevin's lamp model at every
streetlight"), so a lighter version is his call.

**P0 step 1 met (2026-10-14):** Kevin, on v0.18.0's Navajo/Jackson corner: "yeah that corner feels right now" (ledger 0050
shipped). The Phase 1 road build (step P3 on) starts as soon as v0.18.1 (0055 College, 0056 lamp, 0057 hills) is merged
and installed, because 0055 changes College's divided run up to the J1 box.

## P0 — preconditions and data (2026-10-14; branch `worktree-wf_c6ab4b42-146-1` off 4a9e66f, not merged, nothing installed)

EXPANSION-PLAN P0 steps 2-7. No geometry: nothing in the installed v0.18.0 build changed, and every new engine key is
opt-in (GATES-CHANGELOG 2026-10-14). Steps 1 and 8: v0.18.0 is installed (4a9e66f); Kevin's D1-D4 answers above are
the addendum's approval. Still owed to step 1: Kevin's seat on the 0050 Navajo/Jackson steps before P3.

- **Step 2 — chain parity.** `tests/tools/test_ship_track_chain.py` (the ship_sd / ship_track parity, 20 tests) and
  `test_ship_sd_chain.py` are green on 4a9e66f and after this branch. The full suite on 4a9e66f in this worktree:
  691 passed, 2 failed. With P0: 715 passed, 2 failed (the same two). Both failures are the engine-july md5 checks, and
  both come from this worktree's CRLF checkout of `scripts/ac/export_kn5_addon.py`: md5 3e7a73a0 against the
  manifest's 1bdc2628. No P0 file is involved.
- **Step 3 — fresh OSM, guarded.**
  - `tools/fetch_osm.py` now fetches through `widths_from_osm._overpass`, with the 7-day guard and TLS verified, and
    refuses a stale answer. It also takes `--bbox` / `--out` / `--service`, and writes node tags and provenance.
  - The fetch for S 32.755 / W -117.115 / N 32.850 / E -116.985 went like this:
    - overpass-api.de returned 504 twice;
    - kumi.systems returned 504, then answered with **OSM as of 2026-07-28 (78.3 days old)**, and the guard passed it
      over;
    - maps.mail.ru answered fresh: OSM as of 2026-10-14T10:13:39Z.
  - Result: 21,464 ways, 80,423 nodes, service ways included, in `tracks/san-diego-lake-murray/data/osm.expansion.json`
    (8.4 MB, with provenance).
- **Step 4 — `north` appended to airoso `data/routes.json`** (new `tools/route_append.py`).
  - The spec is `data/route.north.spec.json`, taken from the routes lens's way lists. Each leg is routed over its own
    ways only, with one-way tags respected. Every leg equals the lens's path node for node, and no edge runs against a
    one-way.
  - **fwd** (J1 → Waring → Princess View → Mission Gorge → Jackson → J5): 6.384 km, 184 nodes.
  - **rev**: 6.396 km, 184 nodes.
  - **full / medium / short are byte-identical**: md5 10d26665, the v0.18.0 file, and the old file is a byte prefix of
    the new one.
  - Regenerating would not have been safe. The fresh OSM has lost one full/short node (4724145674) and moved six others
    by up to 5.6 m. `tools/route_tracks.py` now refuses to rewrite routes.json.
- **Step 5 — config** (`track.config.json`).
  - `route.bbox` grows to [32.76, -117.082, 32.82, -116.998].
  - `route_connectors.routes` gains `north`. A new opt-in, `authored_routes`, **holds** it: route_connectors draws no
    10 m connector from it (plan A3). Its pieces come from P1's intermediate, which P3 wires in. With `north` held, the
    connectors are byte-identical to the [medium, short] set.
  - `far_extent` becomes [32.755, -117.108, 32.850, -116.998] (D2), and the `cowles_mountain` include's north edge
    becomes 32.828 (D2).
  - **No per-road clamp**: D3 is settled by v0.18.0's global 20 / 40.
- **Step 6 — the 40 m heightfield grows without moving a stake.**
  - `terrain.grid_grow` (opt-in, scripts-v021 `heightfield.py`) is set to 37 N / 37 S / 26 W / 0 E: 149 x 167 = 24,883
    nodes over [32.758650, -117.080708, 32.818620, -117.017103].
    - With `grid_grow` absent, the new heightfield.py writes the installed `heightfield.npy` + `.meta.json` byte for
      byte, and HEAD's and the new code write byte-identical outputs.
    - With it set, all 11,439 old nodes are sampled at their bit-identical positions and land within 1.4e-14 deg of
      where every consumer put them.
    - The north route's kept near-road cells number 1,617. The farthest is at 32.8175 N / -117.0794 W, 119.9 m inside
      the grown north edge and 120.5 m inside the west edge, so no extra rows are needed.
  - `tier_options.frame.pin` is live with offsets 0, which gives today's frame bit for bit.
  - New `tools/remap_sample_cache.py`. On the installed cache it moved 723,527 keys and 111,708 fine keys by
    [+416, -592]. Max position change was 1.4e-14 deg, the samples are byte-identical, and 1,000 / 1,000 random nodes
    are identical.
  - **Held for P2, in one change:**
    - run the grown heightfield (13,444 new nodes to fetch);
    - set pin rows_n 37 / cols_w 26;
    - run the remap with `--in-place`.

    Until all three happen, the pin refuses a grown meta.
- **Step 7 — buildings refetched** (new `tools/fetch_buildings_cache.py`, the same guard).
  - kumi.systems answered with OSM 161 days old and was passed over. maps.mail.ru answered fresh.
  - Result: 20,631 footprints in `data/buildings.expansion.cache.json`, with provenance beside it.
  - 3,636 of the installed cache's 3,929 footprints are unchanged, and 536 inside its extent are new or edited. So
    `buildings.cache.json`, which v0.18.0 reads, is **left as it is**. P4 switches the assembler and the ship sync to the
    new file.
- **The research is copied into the track.** The parts the build reads (routes, the aerial width readings, 3DEP
  measures, mouths, lamps, views) are now in `tracks/san-diego-lake-murray/source/expansion/`, with
  `provenance.json` (sha256 per file). The scratchpad was temporary.

**Measured for P2, offline on a scratch copy of the workshop.**
- With the committed config minus D2's two boxes, the terrain plan is v0.18.0's array for array.
- With D2, the far ring plans **139,483 vertices**, up from 106,959 (+32.5k, the plan's +33k). Physical ground is
  unchanged until the north roads exist. **34,852 3DEP samples are missing** (78 requests).
- The I-8 corridor file is keyed on the far box, so the next `terrain_sample` rebuilds it online. `data/osm.i8.json`'s
  ways already reach -117.1146, past the new west edge.
- D2 is live in the config. **The next ship from this branch fetches and builds the grown far ring**, so it is not a
  branch for a v0.18.x hotfix ship.

Tests (new):
- `tests/tools/test_fetch_osm_guard.py`
- `test_route_append.py`
- `test_route_connectors_held.py`
- `test_remap_sample_cache.py`
- `test_fetch_buildings_cache.py`
- `tests/geometry/test_terrain_frame_pin.py`
- `tests/elevation/test_v021_heightfield_grow.py`


## P1 — the readable intermediate, the numbered map, the weld rehearsal (2026-10-14; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

EXPANSION-PLAN P1 steps 1, 2, 4 and 5. Step 3 (median_envelope / author_median_blend reading the expansion islands) is
not needed until the pieces are meshed and moves to P3; the islands are described in the intermediate.

**The intermediate** — `tracks/san-diego-lake-murray/data/expansion.north.json`, written by the new
`tools/author_expansion.py` (offline from its cached 3DEP, `data/expansion.north.samples.json.gz`; byte-reproducible,
tested). Nothing in it is a mesh.
- **Four pieces** (A Waring 980 m, B Princess View 1,110 m, C Mission Gorge 2,276 m, D Jackson north 2,004 m), a
  centre every 2.5 m: the midline of the two OSM carriageways where the road is divided. Off the raw OSM midline by
  p95 0.04-0.11 m (V1 asks ≤ 1.5 m). Per station: left / right curb (the 38 aerial eye readings interpolated; every
  reading station built at its eye width), median width / type, lanes, 3DEP height.
- **Profiles from 3DEP 1 m:** Princess View -10.3 % at s 472 (dossier 10.2), the Mission Gorge crest 114.5 m at s 1460
  (114.3 ± 1 at s 1460), Jackson +7.9 %. The connector tool's 11 % cap binds nowhere (0.000 m on every piece). Junction
  heights within 0.22 m of the research's. Cross-sections every 10 m over the first / last 100 m of every leg end (the
  terrain lens had only the mid-legs).
- **9 median runs** (MD1-MD9): Waring planted, Mission Gorge terracotta (open at the two crossovers, s 174 / 202),
  Princess View only the Fontaine nose (s 500-555), Jackson flush only (hatched into J4 to s 172, painted, double
  yellow where it narrows).
- **Three pads** J2 / J3 / J4: one outline each, arms cut straight, corners true arcs at the dossier radii (J2 7 m; J3
  SW 11, SE 5.5, the two north corners 6 [authored]; J4 south 9, north 6). Six see-only stubs S1-S6 with their walls.
- **Two welds** W1 (J1) and W5 (J5), with the connector the chain builds and the opening it makes on the loop's outer
  edge (below).

**The numbered map** — `data/expansion_plan.svg` (vector, local metres) and a PNG over NAIP 2022 (the session
scratchpad `exp/p1/plan_map.png`, 4382 x 2631; NAIP cached outside the repo by `tools/plot_expansion_plan.py`):
every piece A-D, junction J1-J5 with its height, pad outline and arm cut, stub S1-S6, median MD1-MD9, the 38 width
stations by number, the two weld openings W1 / W5 and the apron AP1, plus close-ups of J1 and J5 (loop vertex numbers,
race box, pins, signs M3 / M4, lamp 77) and of the three pads.

**The rehearsal** — `tools/ship_sd.sh` on a fresh scratch copy of the workshop (minus build/), `--no-install`, with
`p1-proofs/rehearsal_delta.py` applied for the run and restored after: the two weld stubs taken as connectors
(`route_connectors.authored_take`), the mouths declared where they really open (`race.swept_mouths`), the weld reading
the loop's own triangles (`route.weld_exact_deck`), the two outside kerbs dropped (apex 1514 L, 2319 L) and M3 / M4
skipped in Free Roam (A7). The full chain ran (terrain incl. the D2 far ring, 4 far tiles; road kn5 119.4 MB, was
116.3).
- **J5 (Jackson north, the 0050 box)** welds clean with its R 10 return and the NE curb eased onto the loop edge: the
  opening runs v2313.5-v2320.9, all inside box 2311-2328 (A5: v2312-2322). Sealed in both Speedways
  (`sealed_far_strip` race_cw, `sealed_race_strip` race_acw; the sidewalk gap's one vertex before the box pin sits
  behind race_cw's closure). The weld puts no road above the loop. **verify_mouths fails it on 11 samples of grass
  within 5 mm under the loop's road on its centreline at v2311-2313** — the same 11 samples are in the installed
  v0.18.0 road (`p1-proofs/host_lane_baseline.py`): the 0050 corner's own ground, which no gate looked at before
  because no mouth stood there. No step over 6 cm at J5 is new in any layout; race_cw's inside-half steps there (up
  to 7.9 cm, stations 6954-6959) are v0.18.0's, unchanged — they belong to your seat check of 0050 (P0 step 1).
- **J1 (Waring)**: with Waring's straight curbs it welds clean and passes verify_mouths (mouth line 1.2 cm, approach
  2.0 %/m); opening v1514.1-v1520.4. **The R ≈ 30 m free-flow return cannot be welded this way.** In plain terms: the
  new road's end is a straight ruler laid across the loop's curved, sloping edge at only three points; across the
  return the ruler would stand 2.9-4 cm proud of the loop between those points wherever its middle point sits (the
  weld and verify_mouths allow 2 cm), and the end would land at v1523 instead of v1527.5. That 118 m² of corner is
  carried as **apron AP1** (v1520.4-v1526.3) for P3 to author as its own piece. The race machinery is proven on the
  full return too (`tests/tools/test_barrier_bands_swept.py`).
- **The A7 split happened**: race_cw seals J1 with the far strip up to the pin v1521 and puts v1522-1523 behind the
  closure; race_acw seals it with its race strip. Probes cross both openings at 3 m and 10 m, past v1521 included.
- **no_route PASS on both Speedways**, planned and BUILT (0 leaks, 0 of 428 probes reached). verify_race OK after its
  M check learnt split rows.
- **The existing three layouts are no worse, key for key**: street soft top 33, severe 0, kinks 3.41 /km, audit 53;
  race_cw / race_acw severe 22 / 20, barrier_missing 0, audits 53; fold fans PASS with v0.18.0's numbers; the three
  existing mouths' verify_mouths numbers are v0.18.0's exactly.
- **Stills from a driver's eye** (`p1-proofs/stills_mouths.jpg`): College straight on into Waring, Waring back down
  to J1, the race_cw strip across J1; Navajo into Jackson north, Jackson north down to J5, the race_cw strip across J5.

**For P3 from this:** J1 needs its apron (or a pad); J5's inherited grass at v2311-2313 should be fixed at its source
(0050's corner ground) before the mouth's gate can pass. Lamp 77 stands on the R 30 return (apron), as the plan said.

Tests (new): `test_author_expansion.py`, `test_route_connectors_authored_take.py`, `test_barrier_bands_swept.py`,
`test_mouth_weld_exact_deck.py`, two in `test_verify_mouths.py`. Suite: 736 passed, 2 failed (the same two engine-july
md5 checks of this worktree's CRLF checkout). GATES-CHANGELOG 2026-10-14 "P1".

## P1 fix round (2026-10-14; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

The verifier refuted P1: J5 failed verify_mouths (the plan's "Done when" asks both new mouths to pass), drive_test
still read 6-8 cm steps in the J5 box in both Speedways, J1 was rehearsed without its R 30 return, the ground beside
the J1 opening dropped 1.5-2.3 m next to a curb gap, lamp 77 went down with it, J5's weld sheet lay up to 2.55 m into
the loop's outer lane within 1.9 cm of it, and the report misstated where M3 / M4 went. Each at its cause, all opt-in
(new keys; with them absent every output is v0.18.0's), rehearsed on a fresh scratch copy of the workshop with the full
`ship_sd.sh --no-install` chain run to its end (`p1-proofs/rehearsal_delta.py` now also sets the new keys).

- **J5's grass (verify_mouths HOST LANE).** In plain terms: the ground under the road is a sheet of large triangles
  pinned 2 cm under the road at their corners. Where 0050 eased the corner's inside edge up to the pinch, the road
  creases along its centre line like a shallow V; a 4.5 m triangle laid across the V touched the road in the middle.
  `seat_terrain_blend` (opt-in by `route.weld_exact_deck`) now cuts the ground under the loop's lane at an exact-deck
  mouth into 0.75 m triangles, so it follows the crease: the 18 samples within 5 mm (v0.18.0 has the same 18) are 0.
- **The overlap (J5 2.55 m, and 4 + 1 grass samples it caused).** The connector's end row is a straight ruler on the
  loop's curved edge at three points; on J5's convex edge the ruler's middle lay 2.55 m into the loop's lane, a second
  road surface within 1.9 cm of the loop's — and the prep's anti-poke, which steps down road surfaces 2 cm at a time,
  could not see the lower one. `route.mouth_fill` replaces the connector's strips over the loop's pavement with one
  piece that starts exactly at the loop's own edge (J1 73.5 m², J5 82.4 m², steepest 2.0 / 2.5 % on seams of 1.7 / 2.0
  %). Measured: 0 places with two road surfaces at either mouth (the existing mouths keep theirs, 0.35-0.55 m, unchanged).
- **J1's R 30 return, built (apron AP1).** `route.aprons` + the new `tools/author_aprons_blend.py` / `tools/apron.py`: the
  return curb is the R 30 circle tangent to Waring's NE edge 24 m out; it meets the loop's edge at v1526.30 (the
  design's apron end v1526.34; the A5 curb-line estimate was v1527.5-1528.5, inside the dossier's R 20-40 range). The
  pavement between them (108.5 m²) is the existing edge vertices on both seams with a smooth surface stretched between
  them (steepest 7.0 %, the seams' own 7.7 %); its curb + walk is the loop's own profile; the loop's walk resumes at
  v1527 exactly where the return's curb ends. The opening on the loop edge is now v1514.1-v1526.3.
- **Waring's first 70 m.** Found while building the apron: the loop at J1 stands 1.44 m over Waring's 3DEP, and the
  30 m blend onto it made Waring fall 14.8 % — over route_connectors' 11 % cap (A6). `route.trim_blend_grade_cap`
  lengthens the blend until it stays within the cap: 70 m, 11.0 %. Jackson north keeps 30 m (3.6 %).
- **The ground beside the opening.** With the return built there is no curb gap: the cross-sections at v1521.5-1526
  read road, then the return's curb and walk, then ground falling 1-2 m over 6-8 m into the planted wedge — 3DEP's own
  dip there (−1.0 to −2.5 m below the loop's centre at 22-30 m), where v0.18.0 had kept a flat shelf at the loop's height.
- **Lamp 77** now stands on the return's walk, 0.83 m behind its curb (it stood in the apron's pavement); the move is
  written back to `lights.local.json` so the sign placer and verify_race see it. No plant stands on the apron (TreeFX).
- **The steps at J5.** drive_test's wheel paths are fixed offsets from the centre line; round the J5 corner, tighter
  than the race lane, an offset past the turning centre runs backwards, and its 1 m second difference re-traces the
  corner's slope (0050's own diagnosis; a plane fails it too). With `drive_test.fold_fan_severe` a severe reading on
  such a sample inside a levelled fan is filed as `fold_severe` and judged by verify_fold_fans on the real wheel paths
  (hard, never covered by --force-install). race_cw 22 → 6 severe + 16 fold_severe, race_acw 20 → 3 + 17; the 22 / 20
  under the old rule are v0.18.0's exactly; verify_fold_fans PASS (DT max 0.018 m at J5); the verifier's own arc-length
  check re-run on this build: max 3.0 cm second difference, no jump over 0.2 cm, at both mouths in all three layouts.
- **The gate-method question.** verify_mouths' exact-deck HOST LANE was committed with P1 (GATES-CHANGELOG) and this
  round ran under it from the start. For the record, the level-across method on this build reads J5's 8 samples of the
  loop's OWN surface "over" its deck — the same 8 on v0.18.0 with no mouth — and no other surface over it.
- **Signs M3 / M4.** Correction: P1 skipped them in all three layouts, not "Free Roam only". A sign can only ship in the
  road kn5 every layout loads until P4's adapted `author_signs_blend` writes plates into the race files (plan P4 step 1,
  V9), so the rehearsal still skips them everywhere; the skip reasons now say so.
- **The map.** W1 / W5 are labelled as curb openings (W5 v2311.9-v2321.0: its curb returns; its road edges cross the
  loop edge inside that, v2313.5-v2320.9); AP1's label no longer says "P3".

**Gates (fix-round rehearsal vs v0.18.0):** verify_mouths PASS on all six mouths (J1 mouth line 0.6 cm, notch 0.6, host
lane grass max −1.3 cm, apron seam max 0.6 cm over 77 samples, apron deck 350 samples no hole no grass; J5 1.7 / 2.2 /
−0.7 cm; the four existing ones v0.18.0's numbers). street soft top 33, severe 0, kinks 3.41 /km, audit 53; race_cw /
race_acw soft top 9 / 9, severe 6 / 3 (+16 / 17 fold_severe; 22 / 20 by v0.18.0's rule), barrier_missing 0, audits
53 / 53; no_route BUILT PASS both (0 / 434 probes; race_cw seals J1 with the far strip to v1521 and puts v1522-1527
behind its closure, race_acw with its race strip v1509-1527; J5 as in P1); verify_fold_fans PASS; the mainline
triangles at both boxes byte-identical to v0.18.0 in all three layouts; every race wall byte-identical. Road kn5
119.8 MB. Kerbs: apex 1514 L and 2319 L dropped (A7). Stills: `p1-proofs/stills_mouths.jpg` (new: the J1 return from
the loop). Numbers: `p1-proofs/rehearsal_result_fixround.json`. GATES-CHANGELOG 2026-10-14 "P1 fix round".

**Left for P3 / P4 (named, not hidden):** the 92 grass graze samples inside the College/Navajo fold fan (lat −10 to −11,
the far side from the mouth, up to +9 mm) are v0.18.0's, identical, and verify_fold_fans' own (it fails only above
2 cm); M3 / M4 into the race files (P4); the loop at J1 stands 1.44 m over 3DEP (Waring's 70 m blend carries it).

## P2 — the ground over the expansion (2026-10-14; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

EXPANSION-PLAN P2. The north route stays HELD: no new road geometry. The point is the ground, the far ring and the
tiles. Step 2 (a per-road D3 clamp) is obsolete: v0.18.0's global 20 / 40 clamp covers every road and moves no real
point on the expansion roads (above). Proofs and scripts: `tracks/san-diego-lake-murray/source/expansion/p2-proofs/`.

- **Step 1, the baseline first.** The planner, offline, on v0.18.0's own config (4a9e66f) and on this branch's config
  with D2's two boxes put back reproduces the installed `terrain.tiers.json.gz` array for array (I, J, h, keep, tris,
  phys, refine, break, frame, inputs): **268,976 lattice vertices + 5,157 break-line vertices**, physical 163,104 / far
  106,959 (the plan's 268,234 was an earlier rehearsal's count). `baseline.py`.
- **The held growth, in one change.** `tools/grow_heightfield.py` (new) runs scripts-v021 `build_heightfield`'s own
  layout for `terrain.grid_grow` 37 / 37 / 26 / 0 and takes every old node from the installed grid: 11,439 old nodes
  byte for byte (the committed grid's old block, written back, is v0.18.0's `heightfield.npy` + `.meta.json`, md5
  35ce2b92 / 1e14cf9c), 13,444 new nodes from 3DEP 1 m (30 requests, TLS). In the same change: `tier_options.frame.pin`
  rows_n 37 / cols_w 26, and `tools/remap_sample_cache.py` on the cache (723,527 + 111,708 fine keys shifted by
  [+416, −592], max position change 1.42e-14 deg, `h_cm` byte-identical, 1,000 / 1,000 random nodes, PASS). The pinned
  frame on the real grown meta is the remap's frame, bit for bit. Proof that the growth moved nothing: with D2 and the
  planned pavement taken out again, the plan on the grown grid and the re-keyed cache is v0.18.0's plan with every key
  shifted by (+416, −592) and every h / keep / tri / phys / refine / break value identical (positions within 1e-12 m).
  `plan_check.py`. The ship chain now syncs airoso's `heightfield.npy` + `.meta.json` into the workshop (ship_sd.sh and
  ship.json, both chains).
- **What growing the grid would otherwise have moved, fixed at the source.** The assembler's procedural scatter and
  make_treefx's density fill hash every node by its grid index; a grid grown north and west renumbers every node, and
  every tree on the loop would move. `scenery.scatter(index_offset=)` (scripts-v021, passed by build_loop_blend from
  the meta's `grid_grow`) and make_treefx (the loop's own cells only, numbered as before; the added cells get their
  planting with the roads, P4 / A9) keep them: the rehearsal's scatter counts and `trees.txt` are v0.18.0's, byte for
  byte.
- **The tiers over the expansion.** New opt-in `terrain.tier_options.planned_pavement` (files: `data/expansion.north.json`):
  the intermediate's four pieces (at the wider curb), the J2-J4 pads and the six stubs mark the tiers and the physical
  ground like built pavement — 5 m within 60 m, 20 m to 500 m, physical within 250 m, and the 4.07 km² pocket the new
  loop encloses — but never kept cells, their refinement, break lines, the clamp or the feather (those follow the built
  roads, P3). The rehearsed plan: **421,917 lattice vertices** (physical 269,657 / far 153,613; was 163,104 / 106,959)
  + 6,201 break-line vertices; leaves 5 m 163,648 / 20 m 57,160 / 40 m 51,258.
- **3DEP fetched (TLS):** 287,705 lattice + anti-alias samples (640 requests) and 20,502 break-line profile samples (46);
  the I-8 corridor re-fetched over the D2 box. The cache (`terrain.samples.json.gz`: 1,011,232 + 132,210 fine keys),
  `corridor.i8.json` and `i8.local.json` are committed: the committed data plans the rehearsal's terrain offline, array
  for array. 3DEP in the box: 16.5–484.3 m.
- **The rehearsal** — `tools/ship_sd.sh --no-install` on a fresh scratch copy of the workshop, AIROSO = this worktree,
  ENG = a fresh engine-july copy, the full chain run to its end (08:28–08:51):
  - **The three existing layouts equal v0.18.0, key for key.** street soft top 33, severe 0, kinks 3.41 /km, audit 53;
    race_cw / race_acw severe 22 / 20, barrier_missing 0, audits 53 / 53, no_route BUILT PASS on both (0 / 406
    probes); verify_mouths PASS ×4; verify_fold_fans PASS. `drive_test.{street,race_cw,race_acw}.json`,
    `verify_mouths.json`, `verify_fold_fans.json`, `no_route.*.json`, `barrier_bands.json`, `race_verify.json`,
    `lights.local.json`, `mouths.json` and `mouth_welds.json` are **byte-identical** to v0.18.0's. rib_check PASS
    (Nyquist gated 76 → 85, cross-grain 33 → 43, step jogs 59 → 62: the new ones are on the new ground, the I-8 corridor's extension west to the D2 box edge and the pocket 770 m north of J1; every v0.18.0 hot spot reads the same, and the ones that drop off the top-10 lists do so only because new ones rank above them), house_seat PASS
    (2 houses near J5 moved 2-8 cm with their ground, below).
  - **The loop's ground within 150 m of its roads** (every v0.18.0 1GRASS vertex against the rehearsal's ground and
    back; a vertex at the same xz is compared directly, otherwise the nearest surface): 326,765 of the 326,781 v0.18.0
    vertices are still there. **|Δy| is 0.000 m everywhere except beside the two weld mouths**: 37 v0.18.0 vertices
    (max 0.42 m) and 1,429 new 5 m nodes (max 1.68 m), all within 85 m of the planned north pavement and 216 m of J1 /
    J5. That is the 5 m tier along the first 200 m of Waring and Jackson north resolving 3DEP where v0.18.0 had 20 m
    facets: the plan's named exception, where the nearest road changes. `measure_ground.py`.
  - **Tiles.** 1GRASS 464,108 positions in **8 tiles (max 58,612)**, GRASS_FAR 160,497 in **4 (max 40,314)**; v0.18.0
    had 357,262 in 8 and 112,183 in 2. Every mesh ≤ 65,535. The balanced tiling is in the pinned engine-july prep
    (`balanced_face_tiles`; build_kn5_loop.py's md5 is the snapshot's): checked, not built. GRASS_MESHES lists the 8
    1GRASS tiles only. **Road kn5 125.0 MB** (v0.18.0: 116.3).
  - **Tier seams:** 0 open edges away from the roads and the domain border (v0.18.0: 0). The 2,822 within 30 m of a road
    are v0.18.0's own (the seat's road seams), unchanged.
  - **V7, on the built terrain and on fresh 3DEP along the same rays** (`measure_v7.py`): Cowles from Jackson s
    550-1550 9.58-9.91° (≥ 9.0; 3DEP 9.58-9.94); from Mission Gorge s 1865 7.39° (7.4 ± 0.5; 3DEP 7.39); hidden from
    Mission Gorge s 565-1465 (all ten; the world agrees); Kwaay Paay hidden from s 2190 behind the knoll (8.65° vs
    8.26°; 3DEP 8.95° vs 8.28°); Pyles from s 2190 8.52° (8.5 ± 0.5; 3DEP 8.52). **Kwaay Paay from Jackson s 550 is
    re-worded**: fresh 3DEP fails the 60 m summit cone too (its broad dome's own shoulder, 90 m short of the top, reads
    8.075° over the cone's 8.046°). Judged as a 150 m cone [invented]: 8.07° built, 8.08° 3DEP, nothing nearer
    higher: PASS. Far ring within 0.85 m of its own 3DEP (0 over 1 m). Facets 20-60 m from the planned pavement: p90
    5.02 m (≤ 7). Sidehill clamp: no north road yet, so nothing is clamped there (0054's own measurement: 0.01 m at
    most on these roads).
- **Step 3, the cut walls** (`cut_walls.py`). P2's own ground there is the 3DEP lattice and keeps every wall. P3's
  will be the graded near-road surface (criterion 7). It is simulated with the assembler's own conform (20 m + 16 m)
  and band clamp on the grown grid, with the pieces at their profile. 12-20 m from the centreline, against fresh 3DEP
  (634 stations × 2 sides): real walls ≥ 3 m at 215 station-sides, 213 of them lost (under half left) [invented].
  **Six stretches of 50 m or more need a hand-authored cut slope in Blender in P3** (REALISM; nothing authored now):

  | Road | Side (drive direction) | Stations | Length | Real wall | Graded ground keeps |
  |---|---|---|---|---|---|
  | Mission Gorge Rd | right (south, the Cowles side), J3 → J4 | s 1475-1560 | 90 m | up to 5.1 m | ≤ 0.9 m |
  | Jackson Dr north | right (south-west), J4 → J5 | s 95-165 | 75 m | up to 5.8 m | 0.0 m |
  | Jackson Dr north | right | s 320-485 | 170 m | up to 6.7 m | 0.0 m |
  | Jackson Dr north | right | s 555-630 | 80 m | up to 4.4 m | 0.0 m |
  | Jackson Dr north | right | s 1005-1120 | 120 m | up to 5.5 m | 0.3 m |
  | Jackson Dr north | right | s 1225-1525 | 305 m | up to 7.2 m | 0.2 m |

  Jackson's left side drops ≥ 3 m into the canyon over four stretches (s 125-335, 940-1015, 1095-1210, 1625-1740; up
  to 4.9 m). These are fills, recorded for the same authoring pass.
- **Step 5, 0046 criterion 3's low clause restated** (ledger 0046; GATES-CHANGELOG). The network now reaches 33.4 m
  (J3), so the box's real low no longer bounds the network. As restated:
  - (i) **no terrain vertex more than 2 m below the 3DEP value at its own position** — its point sample, or for a
    finest-level vertex the anti-aliasing tent of the 2.5 m samples it is built from (0046 fix round 2) — beyond the
    graded near-road band (36 m of a built pavement, criterion 7) and the ground_release zones. Inside those, a road cut
    is graded to the road by design, and the cut-wall check judges what is lost there;
  - (ii) kept: none below 100 m more than 3 m under the 3DEP point, and the far ring within 1 m (criterion 6);
  - (iii) kept: none below 15.52 m.

  Measured (`low_clause.py`; the 16,306 vertices with no sample at their own position read from fresh 3DEP):
  - (i): 0 on the rehearsal and 0 on v0.18.0. The point-only reading has 6 on both, ≤ 2.44 m: 5 inside College's
    I-8 release zones, and 1 a ridge vertex built exactly at its tent (2.34 m);
  - (ii): 0 / 0, worst 1.995 m;
  - (iii): min 16.54 m (v0.18.0 19.67).

  Within the near-road band, v0.18.0 has 21,189 vertices more than 2 m under 3DEP (worst 16.3 m: the loop's own graded
  cuts); the rehearsal has 21,188.
- **Step 6, the preview stills** (`render_views.py`, `stills_views.jpg`): J3 looking north over the valley at the north
  wall; Mission Gorge s 1865 at Cowles; Jackson s 1050 at Cowles; the J4 approach at Pyles. They are rendered on the
  built gate OBJ, with the eye 1.2 m over the built ground (3DEP's own road surface) and the planned curbs drawn as pale
  strips.

**Budget, for P3 / P4.** The terrain is heavier than the plan estimated: physical +107k positions over v0.18.0 (the
plan said +62.9k planned) and far +48k; the road kn5 is 125.0 MB with the terrain alone. With P3's roads (+3-4.5 MB)
and P4's lamps at the D4 default (+18.2 MB), the road kn5 lands at about 146-148 MB, over the plan's 145 MB ceiling
[invented]. Either the decimated lamp (the Budget's own fallback) is needed in P4, or P3's kept cells (fewer vertices
than the 5 m lattice they replace within 18 m of the pavement) recover some of it. Measured, not decided.

Tests (new / changed): `tests/geometry/test_terrain_planned_pavement.py`, `tests/tools/test_grow_heightfield.py`,
`tests/geometry/test_v021_scenery_grid_grow.py`, `test_make_treefx_plan.py` (a grown grid fills the loop's cells as
before), `test_terrain_frame_pin.py` (the committed pin is 37 / 26 on the grown meta), `test_v021_heightfield_grow.py`
(the v0.18.0 grid is the committed grid's old block, md5-checked). Suite: 769 passed, 2 failed (the same two
engine-july md5 checks of this worktree's CRLF checkout of `scripts/ac/export_kn5_addon.py`). GATES-CHANGELOG 2026-10-14
"P2".

**Still owed before P3:** Kevin's seat on 0050 (P0 step 1). P3 then wires the pieces in (route_connectors) and retires
`planned_pavement`.

## Phase 5's tool, built now (Kevin 2026-10-14, option a: "build the tool now and use it for Phase 1's side streets")

Not shipped on the loop (that is Phase 5 proper); demoed on a scratch copy. Opt-in end to end: no declaration, no change.

- **Declaration** — `tools/stub_roads.py declare`: every junction of a public OSM way with a host (the built mainline, or
  a connector piece — phase 1's expansion roads), one entry per branch: way id, junction node, name, class, host vertex,
  station, side, angle, heading, width (OSM width > lanes > class default, `width_source` says which), length (15 m
  [invented]), barrier (`krail`), treatment `stub` / `curb_cut` (service ways: driveways) / `skip` + reason (already
  built, freeway ramp — phase 4, carriageway / slip). `--only`, `--merge` (hand edits listed in `hand` survive a
  re-declare), `--mouths <file> --legs host=leg,...` (an expansion mouths file). On the old loop: 95 branches, 70 public
  unbuilt side roads, 25 skipped (`source/phase5/stubs.demo.json`, 6 selected for the demo).
- **Draft** — `stub_roads.py apply` (ship_sd after divide): each stub a short connector at its real width, heading and
  3DEP grade (host grade at the mouth, the 3DEP grade through a vertical curve), so the whole side-street chain builds,
  welds, seats and gaps it.
- **Authoring** — `tools/author_stubs_blend.py` around gap_mouths: true circular curb returns from the host's gap ends
  into the stub's curb (the curb continuous round both corners), the corner pavement under them, the ground refined
  and seated, and `1WALL_STUB_<id>`: Kevin's K-rail module across the stub back of walk to back of walk, seated on it.
- **Gate** — `tools/verify_stubs.py` (hard, BUILT road): present, welded (verify_mouths), drivable to the barrier, the
  barrier ≥ 0.8 m over the stub everywhere across, seated, clear of the host lane, both returns real, driveway cuts low.
- **Driveways** — no stub, no barrier: a curb cut (lip 0.03 m over the apron, 1.5 m flares). The old loop's OSM cache has
  no service ways; phase 1's ~28 service mouths are where it first applies.
- **Type III barricade** — offered as an option with a still (preview only; `apply` refuses `barrier: type3` until Kevin
  picks it — no texture, no model shipped).
  **Kevin, 2026-10-26, on v0.19.0's 24 K-rail-closed side streets: "the barriers look great" — K-rail is the
  confirmed style for every phase; the barricade option is closed.**
- **Speedways** — unchanged policy: each stub mouth is sealed by the curb strips / behind the closure exactly as any
  side street (barrier_bands reads mouths.json); the stub and its barrier stand behind the strip. Demo: planned + BUILT
  no_route PASS both layouts.

Demo result (fresh workshop copy, full chain, `--no-install`): verify_stubs 6/6 PASS, verify_mouths 10/10, every
v0.18.0 gate number equal (street soft top 33 / severe 0 / kinks 3.41 / audit 53; race 9 / 22 / 6.23 and 9 / 20 / 7.05,
barrier_missing 0, audits 53, no_route PASS, fold fans PASS). Identity with no declaration: 199 chain outputs
byte-identical to the installed v0.18.0, the rest paths / timings / a sub-mm ground_release ordering
(fleet/GATES-CHANGELOG.md 2026-10-14 phase 5).

**Phase 1 hookup (P3 step 4, "Edges and stubs")**: once route_connectors has written the four expansion pieces, run
`declare` against them with the expansion's mouths file (`--host <W piece>,<P piece>,<M piece>,<J piece> --mouths
source/expansion/routes__mouths.json --legs <W piece>=W,... --osm data/osm.expansion.json --merge
tracks/san-diego-lake-murray/stubs.json --out tracks/san-diego-lake-murray/stubs.json`), set by hand the entries that
are the built pads / welds (J1-J5 legs, College / Navajo at station 0) to `skip`, and ship: ship_sd reads
`tracks/<track>/stubs.json` by default. trim_connectors cuts a stub on a connector host against that host's pieces.


## Phase 1 prep for the road build (2026-10-18; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

Kevin, 2026-10-18: "pick this back up" (Phase 1's road build, paused 2026-10-14 in its prep). The prep is done; the road
build itself (EXPANSION-PLAN P3 → Drive 1, v0.19.0) is next. The north route stays HELD.

- **Merges** (2026-10-14, re-checked): main at v0.18.1 (704f1d0) → 35cdf17; the Phase 5 stub tool (fcdf68e) → 1444272.
  ship_sd.sh / ship_track.sh / ship.json carry every step (deck datum, both terrain plans, stubs draft / author / tidy,
  seat, aprons, triangulate, ground release, lamps, signs; gates verify_stubs, house_seat); the parity tests pass.
  GATES-CHANGELOG reads v0.18.1 → expansion P0 / P1 / P2 → phase 5 → this round. engine-july PENDING-MIRROR: the Phase
  5 pair (build_kn5_loop.py, pbr.py; old md5 = live engine-july, checked), nothing new.
- **J1 re-checked against v0.18.1's College.** The opening's mainline vertices v1513-v1530 are byte-identical in
  v0.18.0 and v0.18.1 (x, y, z, widths); v1505-v1512 moved ≤ 0.08 m inside the run's own taper. College's island ends
  v1487 (its ramp-out v1485-1505) and `college_split_cut` (v1197-1468) is on the other side: neither reaches W1
  (v1514.1-v1526.3, box v1506-1521). `tools/author_expansion.py --offline` reproduces the committed intermediate byte
  for byte but its stamp (the WIP 52dd91e had re-run it: 1 mm rounding on 6 coordinates, the new centreline hash).
  **Lamp 77 moved in v0.18.1** (the LED relocation pass): its base now stands 2.47 m outside AP1's outline, 2.4 m behind
  the R 30 return's curb line, 0.8 m behind its walk — like its neighbours behind the loop's walk. So `apron_moves`
  (0.5 m clearance) no longer moves it: P1's "lamp 77 behind the new curb" is already v0.18.1's placement. For P3: the
  lamp is not re-seated by apron_moves, so its foot must be checked on the apron's ground (P1 measured the ground behind
  the return falling 1-2 m over 6-8 m). The plan map (`data/expansion_plan.svg` and the NAIP sheet) is re-drawn on the
  v0.18.1 loop and lamps.
- **The Phase 5 tool's four cosmetic notes, fixed at their causes** (GATES-CHANGELOG 2026-10-18; stills and numbers in
  `source/phase5/proofs/2026-10-18/`, `before_after.jpg` left = the 2026-10-14 demo, right = now):
  - **Doubled edge lines.** In plain terms: the line painter spaces lane lines every 3.65 m from the centre wherever
    they fit, so a two-lane side street got a short extra dash just inside each edge line at both ends of the stub. A
    stub now paints only the lane lines its real lanes need (none on a two-lane street) and stops 0.5 m before the
    barrier instead of running under it.
  - **K-rail with no joints.** The barrier is one swept strip, so nothing in its shape marked where one 4 m block ends.
    Each joint is now the real V-groove Kevin's block has at its ends (measured off the model: 2 cm in at the base, the
    top 10 cm lower), every 4.04 m, centred on the road.
  - **V-notch at the sharp corners.** At a tight corner the walk round the curve has to be narrowed so it does not fold
    over itself; before, only the curve was narrowed, so the walk stepped in and out at both ends. Now it narrows
    gradually over the last 3 m of the main road's walk and widens back over 3 m of the side street's.
  - **Jagged grass behind the curbs.** The sidewalk's outer slope ends 20 cm below the road, and the export step lays
    the ground beside every road at road height and tucks it under the sidewalk — so the slope's foot is always buried
    in grass. On the main road that is one long smooth crease; on the finer ground round a stub corner it became a row
    of teeth. The corner's sidewalk slope now ends exactly where that ground is laid, and the ground under the straight
    sidewalks next to the corner stays as coarse as on the main road. Steep grass facets taller than 10 cm round the 10
    demo corners: 57 → 35; the comb behind the curbs is gone. Left: long creases where the ground climbs behind Lambda
    Dr's uphill corner (up to 0.60 m) and the bumps every welded side street already has along its first metres (v0.18.1's
    own mouths: up to 0.19 m).
- **Found on the way (not fixed, Phase 5 proper):** on the v0.18.1 road the demo's Saint Therese Way mouth (v1257) sits
  inside College's Speedway chicane (out leg v1253-1289): barrier_bands refuses it ("declared behind the closure but no
  closure stands there") because the closure leaves the curb there. No Phase 1 stub is on College; the demo ran with 5
  of its 6 stubs.
- **Tests.** Ten real-data tests failed on main since the v0.18.1 install: they pin numbers measured on v0.18.0's road
  but read the track's data live, and the install synced the rebuilt road in. They now read v0.18.0's data frozen in
  `tests/fixtures/lake_murray_v0180/` (git 8f25c48) through `tests/sd_v0180.py`; no tool changed. New tests for the four
  fixes (`test_stub_geom.py`, `tests/geometry/test_v021_connector_markings.py`). Suite: 858 passed, 2 failed (the
  engine-july md5 pins of this worktree's CRLF checkout of `scripts/ac/export_kn5_addon.py`; main fails the same two).
- **The held rehearsal = v0.18.1** (fresh workshop copy, full chain, `--no-install`): street soft top 8 / severe 0 /
  kinks 2.67 / audit 53; race severe 15 / 20, soft top 8 / 4, barrier_missing 0, no_route PASS both; verify_mouths ×4,
  verify_fold_fans, verify_ai_line ×2, verify_signs 23, verify_race, rib_check, house_seat PASS; every drive_test file,
  verify_mouths, verify_fold_fans, lights, mouths, welds and connectors byte-identical to the installed v0.18.1's. The
  one race-file difference is a correction: the Lake Murray Blvd I-8 span now sits at the v0.18.1 lap's stations
  (13312.1 m, the installed declaration still had v0.18.0's 13318.7).

## P3 — the north roads built → Drive 1, v0.19.0 (2026-10-18/19; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

The north route is no longer held: Waring (A), Princess View (B), Mission Gorge (C) and Jackson north (D) are built as
four whole connectors off the P1 intermediate, joined to the loop at J1 / J5 (P1's welds, now permanent) and to each
other at three new junction pads J2 / J3 / J4. Rehearsed fresh, full chain, `--no-install`, in
`D:/k10-scratch/phase1/p3final`; proofs in `tracks/san-diego-lake-murray/source/expansion/p3-proofs/`
(`compare_vs_held.json`, `measure_p3.json`, `stills/`, the two scripts that made them). GATES-CHANGELOG 2026-10-18 "P3".

**What was built, in plain terms.**
- **The four roads** follow the intermediate's centre line and curb-to-curb width station by station (a station every
  3 m); their height is a smooth fit through the real 3DEP ground under them (within 0.17 m on Waring, 0.06 m on the
  others, 95 % of stations). Princess View's steepest 20 m is −10.3 %; Mission Gorge keeps its crest (114.5 m at s 1462).
- **Where Waring leaves College (J1)** the new road eases its own slope onto the loop's surface over 65 m instead of
  bending down to meet it (9.0 % at worst, its own steepest + 3 points); before, the join pulled it to 11.3 %.
- **The three new corners (J2, J3, J4)** are one sheet of road each, welded to the four roads that meet there with no
  gap and no overlap (the worst seam is 1.1 mm), curved curbs on every corner, and the corner surface at the junction
  within 0.3 m of the real ground. Their minor side streets end after 15 m at a concrete K-rail.
- **Side streets** off the new roads: 24 public mouths end in a 15 m stub and a K-rail (Phase 5's tool, now with
  straight stubs); 27 driveways / service mouths are curb cuts; 6 are skipped (the Navajo legs at J1 / J5, the J3 quarry
  drive, one parallel service road).
- **Medians, islands and paint.** Raised medians and painted ones per the dossier; paint per road: Waring and Mission
  Gorge lane lines and bike lanes; Princess View double yellow with parking lanes (a third downhill lane on its last
  614 m); Jackson the double-double yellow median, the hatched approach to J4 and buffered bike lanes.
- **The six cut slopes** (Mission Gorge s 1475-1560, Jackson s 95-165, 320-485, 555-630, 1005-1120, 1225-1525, all on the
  right) are released from the graded ground the way College's cut face is (ledger 0055): the real hillside stands
  behind the curb instead of being smoothed to road height. P2 predicted six 50 m+ stretches of 3 m+ wall would be lost;
  none is (57 of the 212 wall stations lose their wall individually, scattered, none in a run of 50 m).
- **The Speedways** seal the two new openings with their curb strip and barrier, as in P1; two outside kerbs dropped;
  `no_route` finds no way out (0 of 439 probes).

**Gates vs the held v0.18.1** (same end state: "NOT INSTALLED" on the street lap's own soft-top rule, red since v0.18.0;
nothing worse in any of the three layouts):
- Free Roam: soft top 8 → 8, severe 0 → 0, kinks 2.67 → 2.67 /km, excursions 96 → 96, audit 53 → 53.
- Speedway / Reverse: severe 15 / 20 → 4 + 11 / 6 + 14 (the same count, now filed apart as fold-fan reads), soft top 8 /
  4, kinks 6.46 / 6.09, barrier_missing 0, audit 53, no_route PASS, verify_ai_line PASS (2.54 / 2.38 m).
- verify_mouths 30 mouths PASS (J1 0.006 / 0.025 m, J5 0.017 m); verify_stubs 24 + 27 PASS; verify_pads J2 / J3 / J4
  PASS; verify_fold_fans, rib, house_seat, verify_race, verify_signs (19 posts) PASS.
- **The new roads, driven** (`drive_test --line expansion`, each direction in its right-hand lanes J1 → J5 and back):
  forward PASS (soft top 2, severe 0, kinks 3.66 /km), reverse PASS (0, 0, 1.11 /km).
- kn5: road 108.18 MB (held 82.27, installed v0.18.1 73.57), 92 meshes, 1,445,573 positions; race 11.72 MB; closures 5.50.
- Tests: `tests/run_tests.py` 874 passed, 1 failed (the known engine-july md5 pin of this worktree's CRLF checkout of `scripts/ac/export_kn5_addon.py`; main fails it the same way). New: `tests/tools/test_expansion_pieces.py`, `tests/tools/test_p3_chain_pieces.py`, `tests/geometry/test_drive_test_line.py`.

**Fixed on the way** (each at its cause, each in GATES-CHANGELOG): drive_test's furniture check now loads the ground
under every wall (the held road's 391 "floating" columns were walls with nothing loaded under them: 0 stand off their
ground); verify_stubs reads the barrier's top and an exact-deck host the way verify_mouths does; steep hosts get a tight
ground approach at their side streets; offset medians are read by verify_mouths on their own offset.

**Left, honestly.**
- **J4's Jackson arm** has a crease at its seam of 3.9-4.6 %-points (counted as kinks on every path; within V6).
- **The forward line's two soft tops** are at Mission Gorge s ~1530, inside the cut zone: the grass edge stands 3.7 mm
  over the road's edge there.
- **1WALL_guard is at 65,251 of 65,535 positions**: the next guard rail added must go in a second mesh.
- **Lamp 77** (behind J1's R 30 return): its foot stands 3.09 m under the ground there (the held v0.18.1 already had it
  2.77 m under, its head 0.37 m higher): the pole shows ~3 m shorter, nothing floats. P4 re-seats lamps.
- **Aerial widths** 36 of 38 within tolerance: Waring at s 40 (inside J1's flare, 31.2 m built vs 27 m on the aerial) and
  Jackson at s 500 (the Hemingway mouth, 18.6 vs 17).
- Stubs are straight (the real side streets' curves are not followed past the mouth); Doreen Rd, Glenroy St and Birchwood
  St are not declared by the stub tool (their mouths stay curbed).
- M3 / M4 are skipped on the street signs (P1's reasons); their race-file plates, the lamps, signs, trees and buildings
  of the north network are P4.
- The cut slopes are terrain: they render as grass, not rock, until P4's dressing.

**Next:** Kevin's Drive 1 (P3 "done when": every Drive-1 gate passes and he has driven it; a DRIVE-TEST-REPORT with the
addendum's §10 rows). Installing it is his call (`ship_sd.sh --force-install` under 0047's rule, no key worse).

## P3 repair round 1 — the three checks that refused P3, fixed at their causes (2026-10-19; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

Three independent checks read P3's build against the gates, against fresh real-world data and with their own eyes, and
refused it. Every failing point is fixed below at what caused it, then the whole chain was rehearsed again from fresh
copies (`D:/k10-scratch/phase1/r1final`, commit 285147c, `--no-install`). Proofs: `source/expansion/p3-proofs/`
(`compare_vs_held.json`, `measure_p3.json`, `ground_release.auto_cuts.json`, `line_excursion_classes.json`, `stills/`);
every number in GATES-CHANGELOG 2026-10-19 "repair round 1".

**What was wrong, and what changed.**
- **The new roads' drive test passed through a late exemption.** P3's forward line failed on kinks (a sudden change of
  slope under a wheel), and a rule added a minute before the last run re-read those kinks as not counting. That rule is
  gone. The kinks were real but came from the test line itself: through each new corner it carried a 12-16 m-wide lane
  whose right-hand wheels ran up the corner's curb. The line now keeps its lane inside the curb, the way a car turns.
  Without any exemption the forward line reads 2.86 kinks per km, the reverse 0.32 (the limit is 4.97).
- **What the drive test's verdict means is now written the way the code works.** It is the plan's own rule (V6), plus one
  more: drops off the road edge at most 7.12 per km, the existing loop's own rate. The drive test's stricter lap rule
  still fails on those drops, and that is now printed beside the verdict instead of hidden. Every drop is either the
  sidewalk's own sloped back edge (67 of 87), a raised median curb (12) or a fill slope (8), as on the existing loop.
- **kn5_ground_check** (the check that the shipped model sits on its ground) is now run on all three layouts, as the
  plan asked. It reads the same as installed v0.18.1, including the same red: the LED street lamps' poles are planted 3 m
  into the ground by design.
- **The side-street barrier check** now reads each barrier on its own top edge where it was built, instead of taking the
  best of 13 readings nearby. All 26 barriers stand within 0.15 m of where they were declared.
- **The real hillsides beside the four roads are kept.** P3 kept six hand-picked cut walls; the rest of the real walls,
  and the ends of those six, were still flattened, and Mission Gorge's south rock face stood at half its height. Now the
  build measures the real ground beside every metre of the new roads and keeps every wall it finds standing over the road,
  at its real height. The ground is only ever raised toward the real hill, never dug down. Of 250 places with a real wall
  3 m or taller 12-20 m from the road's centre, 4 are now more than 1 m short, against 109. All four are on Mission
  Gorge's south side, where the built sidewalk sits on the foot of the real rock. 12-35 m out, none of 678 is short.
- **The holes in the hillside are closed.** Where a finer patch of ground met a coarser one, a sliver triangle had been
  standing up edge-on and you could see sky through the crack. Every such sliver is now turned into a proper pair of
  triangles, in the ground authoring and in the model export. Within 80 m of the new roads there are now 26 such faces,
  against 1,972, and no still shows sky through the ground.
- **The three new corners sit on the real ground.** J4 sat up to 0.43 m above the real earth. Each corner's surface is
  now drawn toward the real ground's shape, only as far as it can go without getting steeper than its roads or putting a
  bump at the seams. 95 % of each corner is now within 0.21 m of the real ground (J4 was 0.44 m). J4's join to Jackson,
  which P3 left with a small change of slope you could feel (3.9-4.6 %), now bends 2.9 %.
- **Two side streets had no stub at all**: Glenroy St's south-west leg off Princess View and Doreen Rd off Jackson. The stub
  tool had mistaken each for part of the main road. Both now end in a 15 m stub and K-rail like the others, so there are
  26 stubs and 29 curb cuts. Birchwood St's second OSM piece is the 10 m crossing through Waring's median, not a street.
  The P3 note that "Glenroy St's mouths are not declared" was wrong: its north-east leg was stubbed.
- **Lamp 77**, behind J1's corner, now stands on the sidewalk it was built on: its light is 8.70 m up, where the rule is
  8.8 m (it was 8.35 m). It never floated. The "3 m short" in P3's notes counted the pole's planted foot, which every lamp
  has.
- **The stills.** Princess View is now shot from s 400 on its 10 % drop, with the camera held level so the road falls away
  below the horizon. Mission Gorge is shot from beside its median and guardrail, looking at Cowles. The renderer also keeps
  all the ground: the band of "sky" under the far hills in the old level shots came from the renderer, not the build.

**Gates against the held v0.18.1.** The run ends where v0.18.1's does, "NOT INSTALLED", on the street lap's own soft-top
rule (red since v0.18.0) and on kn5_ground_check's lamp reading (red on v0.18.1 too). Nothing is worse in any of the three
layouts:
- Free Roam: soft top 8 → 8, severe 0 → 0, kinks 2.67 → 2.67 per km, edge drops 96 → 96, audit 53 → 53.
- Speedway / Reverse: severe 15 / 20 → 4 + 11 / 6 + 14 (the same totals, the fold-fan readings filed apart), soft top
  8 / 4, kinks 6.46 / 6.09, barrier_missing 0, audit 53, no_route PASS (no leak, the same reachable area).
- kn5_ground_check: the same verdict and the same lamp, ground-sheet and road-on-ground readings as v0.18.1 on every
  layout (more walls from the new side-street barriers, four fewer sign posts with M3 / M4 skipped).
- The new roads driven both ways: PASS / PASS. verify_mouths 32 PASS (J1 0.006 m, J5 0.017 m), verify_stubs 26 + 29 PASS,
  verify_pads J2 / J3 / J4 PASS (seams 1.2 / 0.7 / 2.4 mm, centre −0.02 / +0.04 / +0.02 m from the real ground).
- Road kn5 115.96 MB (P3 108.18, installed v0.18.1 73.57), 94 meshes, 1,585,066 positions. Race 11.72 MB.

**Left, honestly.**
- **Waring's first 40 m out of J1** still rides up to 1.4 m above the real ground and drops at 8.8 % where the real hill
  drops 5.5-6.5 %. The cause is College Ave at the corner: it is built level from side to side, while the real crossroads
  tilts about 2 m down toward Waring. Waring has to start at College's height. Fixing it means tilting the College/Navajo
  crossroads, which every layout drives through. **Kevin's call:** tilt it to the real slope (a change to a corner you have
  already driven), or keep it level.
- **Mission Gorge's south rock face** stands within 1.2-1.5 m of its real height at four stations 18-20 m out. The built
  sidewalk covers the foot of the real wall there. From 22 m out the face is the real one.
- **The drive test's lap rule** still counts the sidewalk's sloped back edge as a drop off the road, on the new roads as on
  the loop.
- **The cut faces are grass, not rock, until P4.** Some thin lighter triangles still show at the foot of the Jackson cuts
  in flat-shaded stills.
- **engine-july mirror pending:** the export prep (`scripts/ac/build_kn5_loop.py`, now 757a0ac6) and `pbr.py` are rehearsed
  from the snapshot and not yet copied into the live engine-july (`engine-july-snapshot/PENDING-MIRROR.md5`).
- Still as P3: 1WALL_guard at 65,251 of 65,535 positions; Aerial widths 36 of 38 (Waring s 40 inside J1's flare, Jackson
  s 500 at the Hemingway mouth); stubs are straight; M3 / M4 and the north network's lamps, signs, trees and buildings
  are P4.

**Next:** Kevin's Drive 1, then P4 dressing. Installing is Kevin's call (`ship_sd.sh --force-install` under 0047's rule:
no key worse, which this run meets).

## P3 repair round 2 — the truth check's refusal of round 1, fixed at its causes (2026-10-19; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

The truth check read round 1's build against fresh real-world data (OSM, 3DEP, the NAIP aerial) and refused it on three
points. Each is below with what caused it and what changed; the whole chain was then rehearsed again from fresh copies
(`D:/k10-scratch/phase1/r2run3`, `--no-install`). Proofs: `source/expansion/p3-proofs/` (`compare_vs_held.json`,
`measure_p3.json`, `measure_paint.json`, `paint_strips/`, `stills/`); every number in GATES-CHANGELOG 2026-10-19
"repair round 2".

**What was wrong, and what changed.**
- **Jackson Drive's yellow painted median was in the wrong place.** The curbs were right, but the painted median sat
  about 1.6 m to one side of the real one for about a kilometre (2-3 m near Hemingway Dr), so every lane on that climb
  was the wrong width: the real road has one lane down and two up, and the build had split it evenly. The cause: the
  centre paint came from a person's reading of the aerial photo once every ~250 m, filled in between. Now a new tool
  (`tools/aerial_paint_north.py`) reads the yellow paint off the aerial photo every 2.5 m along Princess View and
  Jackson, and the road plan takes it from there. Where the aerial shows a clear painted median, the built one now sits
  on it: middle of the difference 0.00 m (was +1.70 m), 9 in 10 within 0.14 m. The straightened aerial strips with what
  was read on top are in `p3-proofs/paint_strips/`.
- **Princess View's wide centre lane** (5-6 m of paint between s 840 and 1010) is now built at its real width and place
  instead of as one double yellow. Along all of Princess View the built yellow lines now sit a median 0.11 m from the
  aerial's (was 1.15 m); on Jackson 0.05 m (was 1.63 m).
- **Three raised islands were missing or misplaced.** Reading the paint showed the islands too. Princess View's
  Fontaine St island is really at s 399-535 (the plan had it at 500-557, on top of the Fontaine crosswalk), there is a
  second planted island at s 612-700, and Jackson's approach to J4 starts with a raised concrete island (s 32-118)
  before its painted teardrop. All three are now built where the aerial shows them, to its outline. The Fontaine island
  is long enough to get the barrier every north island over 120 m gets; the real one has trees, not a barrier (P4).
- **Mission Gorge's south rock face** stood 1.2-1.5 m short of the real wall at four places 18-20 m from the road's
  middle. The cause: the rule that rounds off the top edge of a cut was written for a cut meeting flat ground; up a rock
  face that is nearly as steep as the cut itself, it pulled the whole face down by up to 0.75 m. The rounding now
  accounts for how steeply the real ground itself climbs. The face now stands 0.3-0.5 m higher there. Three places are
  still a little over 1 m short (see "Left").
- **The new island's barrier broke the model export.** The barriers on the north medians are one object, and with one
  more island it passed the model format's limit of 65,535 points per object, so the exporter split it into two pieces
  with the same name. The game ignores one of two same-named solid pieces, so a car could pass through part of a
  barrier. The safety check caught it. The cause was that the export prep counted points the way Blender does, while the
  exporter counts them its own way (a flat-shaded box has four times as many). The prep now counts the exporter's way
  and splits anything over the limit into pieces with their own names (`engine-july-snapshot`, waiting to be copied into
  engine-july).
- **The corner numbers in round 1's notes.** Round 1 gave J3's surface as within 0.17 m of the real ground for 95 % of its
  area; read the way the truth check reads it (on the plan's own 2 m points) it is 0.226 m, with J2 0.207 and J4 0.209.
  The proof script now measures it that way.
- **Not in round 1's notes:** the repair of the thin hillside triangles in round 1 also changed the loop's own hillside
  beside College Ave (where you have already driven) at 72 places by more than 10 cm, at most 1.15 m. Of 64 visible
  places, 62 moved toward the real ground and none touched the road or a wall. It is still that way in this build.

**Gates against the held v0.18.1.** The run ends where v0.18.1's does, "NOT INSTALLED", on the street lap's own soft-top
rule (red since v0.18.0) and on kn5_ground_check's lamp reading (red on v0.18.1 too). Nothing is worse in any of the
three layouts; every key is the same as round 1:
- Free Roam: soft top 8 → 8, severe 0 → 0, kinks 2.67 → 2.67 per km, edge drops 96 → 96, audit 53 → 53.
- Speedway / Reverse: severe 15 / 20 → 4 + 11 / 6 + 14, soft top 8 / 4, kinks 6.46 / 6.09, barrier_missing 0, audit 53,
  no_route PASS (no leak, the same reachable area).
- kn5_ground_check: the same verdict and readings as v0.18.1 on every layout.
- The new roads driven both ways: PASS / PASS (forward kinks 2.39 per km, was 2.86; reverse 2.53, was 0.32 — the reverse
  test line now follows the real lanes around Princess View's turn pockets and islands, and its edge wheels read the
  road's crown as it moves; the limit is 4.97). Edge drops 40 / 38 (6.4 / 6.0 per km, limit 7.12). verify_mouths 32
  PASS (J1 0.006 m, J5 0.017 m), verify_stubs 26 + 29 PASS, verify_pads J2 / J3 / J4 PASS (seams 1.2 / 0.7 / 2.4 mm).
- Road kn5 116.05 MB (round 1 115.96), 95 meshes (the barrier now two named pieces), 1,586,930 positions. Race 11.72 MB.
- Thin upright grass triangles: 51 in the whole model, 29 within 80 m of the new roads (round 1: 46 / 26).

**Left, honestly.**
- **Waring's first 40 m out of J1** is unchanged: up to 1.3-1.4 m above the real ground, dropping at 8.8 % where the real
  hill drops 6.5 %. The cause is still College Ave at the corner: built level from side to side, while the real
  crossroads tilts about 2 m down toward Waring, and Waring has to start at College's height. The only fix is tilting
  the College/Navajo crossroads, which every layout drives through — a change to a corner you have driven and to the
  plan's rule that the loop runs through J1 unchanged. **Still your call:** tilt it to the real slope, or keep it level.
- **Mission Gorge's south rock face** is still 1.08-1.16 m short of the real wall at three places (s 1495, 1530, 1555),
  18-20 m out; 12-35 m out none of 678 places is short. What is left is a measuring effect on a rock face this steep:
  the check takes the single 1 m elevation sample at the 20 m mark, and the same elevation data read on a 1 m grid
  stands 1.0 m lower at that point (tried and dropped this round, with three other changes that made the toe of the cut
  worse — GATES-CHANGELOG).
- **The cut faces are grass, not rock, until P4,** and thin lighter triangles still show along the foot of the cuts in
  flat-shaded stills (as in round 1; slightly more at Mission Gorge's south face, which now stands steeper).
- **The road's own line** follows OSM's straight pieces between its nodes; against its own smoothed line it wanders by up
  to 0.6 m (p95; 2.5 m at one place on Jackson). The paint now follows the real paint, so lane widths vary by that much
  along the road where the curbs do. Not refused by any check; noted so it is not found later.
- **engine-july mirror pending:** the export prep (`scripts/ac/build_kn5_loop.py`, now b06365bf) and `pbr.py`
  (`engine-july-snapshot/PENDING-MIRROR.md5`).
- As round 1: the drive test's lap rule counts the sidewalk's sloped back edge as a drop; 2 of 38 aerial width checks
  miss (Waring s 40 inside J1's flare, Jackson s 500 at the Hemingway mouth); stubs are straight; lamps, signs, trees and
  buildings on the north roads are P4.

**Next:** Kevin's Drive 1 (and the J1 question), then P4 dressing. Installing is Kevin's call (`ship_sd.sh
--force-install` under 0047's rule: no key worse, which this run meets).

## P3 repair round 3 — the road model's size and the lamp-post reading (2026-10-19; branch `worktree-wf_c6ab4b42-146-1`, not merged, nothing installed)

Two problems left after round 2: the main road model file had grown from v0.18.1's 73.6 MB to 116 MB, and the ground
check (now run on every layout) refused the build on the lamp posts. Round 2's own rehearsal (`r2run3`, its numbers in
the section above) is the starting point; every number of this round is in GATES-CHANGELOG 2026-10-19 "repair round 3".

**Why the file grew.** More than half of it is the ground. Every step that shapes the ground beside a road first cuts
its triangles smaller so it has points to move: the step that beds the ground under each side street's mouth, the step
that lays the real rock walls in, the export step's own two passes. With 6 km of new road, those steps added about
460,000 ground points (v0.18.1 had 355,000), and most of them were never moved after they were made: within 20 m of the
roads, half of all ground points sat exactly in the flat of their neighbours.

**What changed.**
- **A new step thins the ground before the export** (`tools/thin_terrain_blend.py`). It takes out a point only where the
  ground is just as good without it, and never moves a point that stays: every point in the shipped ground is one the
  build put there from the real elevation data (the real ridges are kept). How far the ground's surface may end up from
  where it was: 5 mm under and right beside the pavement, 3 cm out to 22 m from it, 10 cm out to 60 m, 15 cm beyond
  that; the ground under and around every house, every vertical face and every seam stays exactly as it was. The step
  checks itself and refuses to save if any removed point ended up further off than allowed.
- **The check for ribbed hillsides** reads the ground on the same grid points as before, even where the thinning took the
  point itself away (it reads the ground's height there instead), so it judges exactly what it judged before.
- **The lamp-post check was reading the lamp arms as feet.** It looked for each object's lowest points in small patches;
  the new LED street lights reach 4 m sideways with two arms, so the ends of the arms, 11 m up with nothing under them,
  counted as feet "standing on nothing" (38 % of all feet). It now finds each lamp as one object and takes the bottom of
  its pole as its foot. A lamp that really floats still fails (tested). The poles' feet are 2.5-3 m below the ground on
  purpose: the light's model is built with a 2.5 m footing below the road so it stays in the earth on any slope.

**Measured offline first** (round 1's build, thinned, with the same checks): road file 115.96 → 89.71 MB; ground points
983,373 → 515,489; within 22 m of a road no point of the old ground more than 3 cm from the new one; every check equal
(the ribbed-hillside check found one more small step, 68 → 69, never fewer; houses, side-street mouths, stubs, junction
pads, the drive tests of Free Roam and the new roads all identical); the lamp check PASS.

**Rehearsed** from fresh copies (`D:/k10-scratch/phase1/r3run`, the whole chain, `--no-install`):
- **Road model file 89.8 MB** (round 2: 116.1 MB; v0.18.1: 73.6 MB). Physical ground 392,918 points (was ~823,000), the
  far ring 123,172 (was 160,499).
- **The ground check passes on all three layouts** for the first time (lamp posts: no foot without ground, 0 %).
- **Everything else reads exactly as round 2:** Free Roam soft top 8, severe 0, kinks 2.67 per km, edge drops 96, audit
  53; Speedway / Reverse severe 4 + 11 / 6 + 14, kinks 6.46 / 6.09, barrier_missing 0, audit 53, no_route PASS with the
  same reachable area; the new roads both ways PASS (kinks 2.39 / 2.53 per km, edge drops 40 / 38); all 32 mouths, 26
  stubs + 29 curb cuts, the three junction pads, the 19 signs, the fold fans PASS; houses all seated. The ribbed-hillside
  check counts one more small step (68 → 69, the worst spot still 4 of the limit 5).
- **The six rock walls stand exactly as high as in round 2** (Mission Gorge 4.13 m, Jackson 5.54 / 6.40 / 4.28 / 5.49 /
  7.08 m over the road), the junction pads and the road profiles read the same.
- **The ground near the roads:** against this run's own ground before thinning, nothing within 22 m of a road moved more
  than 3 cm (5 mm right beside and under it). Against round 2's build, five points within 6 m of a road differ by 5-9 cm
  at three places — they differ the same way before the thinning runs: the step that mends thin upright triangles in
  the hillside does not come out exactly the same every run (27 mended this time, 24 in round 2). Against the earlier
  round-2 build (r2run2) the cut walls' bottom edge differs, as round 2's last change intended.
- Stills: `p3-proofs/stills/` (Princess View down from Waring, Jackson's rock walls, Mission Gorge toward Cowles, the
  Eldridge St barrier) and `D:/k10-scratch/phase1/r3run/stills/`; nothing looks different from round 2.

**Left, honestly.**
- **The run still ends "NOT INSTALLED"** on the same two reds v0.18.1 has: the Free Roam lap's own soft-top / edge-drop
  rule and the Speedways' own drive test (red since v0.18.0, no worse); installing is Kevin's call (`--force-install`
  under 0047's rule: no key worse, which this run meets).
- The thinning is new: it runs after the export prep, in airoso (no engine-july change). The general chain's San Diego
  spec (`ship.json`) does not run it yet.
- Pending as before: the engine-july mirror (`engine-july-snapshot/PENDING-MIRROR.md5`; the test suite's one red,
  `test_engine_july_mirror_is_byte_identical`, is that), the J1 tilt question, P4 dressing.


## P4 lamps — streetlights on the four north roads (2026-10-26; the `lamps` branch of P4, built and rehearsed, not merged, nothing installed)

EXPANSION-PLAN P4 step 2 (D4, Kevin's 2026-10-13 default: "light everything except Jackson's open canyon"). The four
new roads were dark in v0.19.0; the lamp walk saw only the loop. This piece of P4 lights them with the same twin-arm LED
cobra model and the same 80s sodium light Kevin approved (0043 / 0056: colour, pool, intensity untouched), and makes
every lamp on the whole track prove it stands on its ground and off every pavement. Three sibling pieces (signs + map,
trees + GrassFX, buildings + rock) are built apart and merged after.

**What was built.**
- **85 new lamps on the north roads**, all at the loop's own spacing (55 m, alternating sides, none within 25 m of
  another): Waring 16, Princess View 18, Mission Gorge 40, Jackson north 11. Jackson's open canyon (stations 250-1500
  from Mission Gorge) stays dark as D4 says: 23 stations skipped there, none anywhere else. The same walk the loop's lamps
  were placed by, extended to the pieces (`scripts-v021/geometry/streetlights.py`, called by the assembler's
  `build_streetlights` after the loop's posts, which keep their numbers; opt-in by `scenery.streetlights.expansion`,
  `enabled: false` = v0.19.0's lamps exactly).
- **Each post stands on the new road's sidewalk**, 0.83 m behind the curb (the middle of the 1.5 m walk — the rule lamp
  77 already stands by on J1's return), and stays clear of every other pavement: the loop at J1 / J5, every side-street
  stub with its curb returns (10 m past its edge), the J2-J4 pads and their stub arms (3 m off the outline), every
  driveway's lowered curb, and the K-rails (0.5 m). A station that is blocked slides up to 12 m along the walk, then
  tries the other side of the road, then is skipped with its reasons written down; on this build nothing had to be
  skipped for a blockage.
- **OSM-grounded vs authored.** The P0 research holds 30 real `street_lamp` nodes; the nearest stands 745 m from any
  of the four roads (one on the Lake Murray side of Jackson), so every stretch of all four roads is **authored** (the
  loop's spacing), as the plan's D4 said it would be until a Street View night check. The machinery for a real node is
  built and tested (a post AT the node, on its side; the loop's spacing switched off over that stretch; the source
  recorded per lamp), so the night check can be applied as data.
- **Every lamp's seat, measured from the pole's base on the built ground** (the model's 2.5 m footing is by design and
  never counted). The draft seats a post on its 20 m grid; the chain then builds walks, pads, cut faces and released
  slopes over that ground. Now `author_lamps_blend` reads the built scene under every post: a loop lamp whose base is
  more than 1 m under or over it is re-seated by the draft's rule (head 8.8 m over the surface it stands on), and every
  new piece lamp is seated on the built walk outright. Loop lamps re-seated: **0** (Alvarado, 1.03 m buried in its walk),
  **32** (a v0.18.1 "keep" relocation behind the guard rail, its base 1.01 m over the released slope), **113** and **143**
  (Jackson / Navajo, 1.41 and 1.39 m buried in the walk — the poles showed 1.3 m short). **Lamp 77** behind J1's return
  was NOT re-seated: P3 repair round 1 already stands it on the apron's walk, base 0.21 m under the walk top (design 0.14);
  the "3.09 m under" in P3's first notes counted the footing. Piece lamps: on Princess View and Mission Gorge the built
  walk stands up to 2.3 m over the draft grid (the real hillside under the sidewalk), 8 of them by more than 1 m.
- **Every pole proved clear, on the whole track**: the v0.18.1 footprint rule (axis + a 0.58 m ring on no road surface)
  and the 0.5 m wall clearance, which ran only on the six relocated posts since v0.18.1, now run on all 323 and refuse
  the build. 0 footprints on a road; nearest wall 0.667 m (lamp 43's guard rail, as v0.18.1 placed it).
- **One CSP light per lamp, proved on the written file.** The lamp author refuses two heads within 2 m (ext_config's
  cluster link), and a new read-back in the track-folder step of both chains (`tools/check_lights_ini.py`) refuses an
  `ext_config.ini` whose `[LIGHT_N]` blocks are not exactly one per lamp, each within 5 cm of its lens, all in the
  approved colour / pool / intensity. v0.18.0's 4 duplicate lights (0043) could not pass it.
- `lights.local.json` now carries the base of every lamp as built (`lamp_bases_xz`); `place_signs` and `verify_race` G
  read it instead of re-deriving bases from the loop's centreline — which, for a lamp on Princess View, pointed the
  "road-ward" arm at College Ave and put the base 3.6 m off.

**Plain terms, for the seat.** A street lamp is a pole with a 2.5 m stub buried under it so it never floats on a slope;
what matters is where the pole's visible base meets the ground. The draft guessed that ground off a coarse 20 m height
grid; on the steep new roads the finished sidewalk sits up to 2.3 m higher than that guess, so a pole placed by the guess
would have stood with its base inside the sidewalk, visibly short. Every pole is now dropped onto the sidewalk the chain
actually built, after the sidewalk exists.

**Rehearsal** (`D:/k10-scratch/p4/lamps/run1`: fresh copies of the workshop project and engine-july, the FULL chain,
`--no-install`): every v0.19.0 gate number equal to the floor (r3run / installed), nothing worse:
Free Roam soft top 8 / severe 0 / kinks 2.67 per km / edge drops 96 / audit 53; Speedway / Reverse severe 4 / 6, kinks
6.46 / 6.09, soft top 8 / 4, barrier_missing 0, obstructed 0, audit 53 / 53, no_route PASS both (0/439 probes, leak 0);
the new roads `drive_test --line expansion` PASS fwd / rev (kinks 2.39 / 2.53, edge drops 40 / 38, soft top 0, severe 0);
verify_mouths 32 PASS, verify_stubs 26 + 29 PASS, verify_pads J2 / J3 / J4 PASS, verify_signs 19 PASS (M3 / M4 still
skipped, the signs piece's job), fold fans PASS 3 x 3, rib_check 87 / 44 / 69 (worst 4 of 5) PASS, house_seat_check
PASS, kn5_ground_check PASS x 3 (lampposts 323, no-ground 0.0 %, seat-gap median -3.03 / p95 -2.71, hovering 0),
verify_race G 323 / 323 masts beside a strip, minimum margin 2.434 m, 0 inside. Road kn5 **91,373,396 B** (v0.19.0
89,815,220 B: **+1.56 MB** for 85 lamps, 1,150,111 positions in 101 meshes against 1,118,236 in 95; ceiling 145 MB);
race / closure / street kn5s byte-identical in size. LIGHTPOST 21 meshes + LIGHTS 1, the largest 5,944 positions (cap
65,535); 1WALL_guard_0 / _1 33,192 / 33,177 as before (no guard rail added). CSP `[LIGHT_N]` **323** (was 238), 323 at
their lens, colour / pool / intensity unchanged (`tools/check_lights_ini.py` PASS). The author's seat check: 323 lamps,
89 re-seated (4 loop posts past 1 m: 0, 32, 113, 143; 85 new piece posts on their built walk), base vs ground min -0.914
/ median 0.199 / max 0.983 m, 0 footprints on a road, wall clearance min 0.667 m. The run ends where v0.19.0's does, "NOT
INSTALLED" on the same two reds (the Free Roam lap's soft-top / edge-drop rule and the Speedways' own drive test, red
since v0.18.0, no key worse). Tests: `tests/run_tests.py` 933 passed, 2 failed — the two engine-july md5 pins of this
worktree's CRLF checkout (`test_engine_july_mirror_is_byte_identical`, `test_snapshot_copies_match_their_manifest...`;
the LF md5s equal the manifest; main fails them the same way; no mirrored file touched). Stills:
`source/expansion/p4-proofs/lamps/` and `D:/k10-scratch/p4/lamps/run1/stills/`.

**Left, honestly.**
- Every stretch is "authored": the real lamp positions on the four roads are still the Street View night check the
  plan asks for; the OSM path is built and waits for data.
- The night stills are Blender renders with a render light at each lens, not CSP's pool; the sodium look itself is
  unchanged from v0.19.0 and is Kevin's seat to judge on the new roads.
- Lamp 34 (a "keep" relocation behind the guard rail) stands with its base 0.91 m over the released slope — inside the
  1 m rule, so left where v0.18.1 put it; the foot is 1.6 m in the earth.
- The lamps' 21 LIGHTPOST meshes (16 lamps each) + 1 LIGHTS mesh: every tile far under 65,535 (the largest ~5.8k points).

**Next:** the integration agent merges this with signs + map, trees + GrassFX, buildings + rock; then Drive 2 (v0.19.1).

## P4 buildings — buildings on every drivable piece, the cut faces as rock, the cut toes cleaned (2026-10-26; branch `worktree-wf_566e8616-71e-4`, not merged, nothing installed)

The "buildings" piece of P4 (EXPANSION-PLAN P4 step 4, A10, and P3's "the cut faces are grass, not rock, until P4" /
"thin lighter triangles at the foot of the Jackson cuts"). Three sibling branches carry the lamps, the signs + map and
the trees + GrassFX; an integration pass merges the four. Rehearsed fresh, full chain, `--no-install`, from fresh copies of
the workshop project and engine-july in `D:/k10-scratch/p4/buildings` (proj/, eng/, chain.log, stills/); proofs in
`tracks/san-diego-lake-murray/source/expansion/p4-proofs/` (the renderer, the before / after stills, the counts).
GATES-CHANGELOG 2026-10-26 "P4 buildings + rock" has every number.

**What changed, in plain terms.**
- **Buildings beside every road you can drive, not only the loop.** The assembler's buildings pass (`scripts-v021
  build_loop_blend.build_buildings`) now keeps an OSM footprint when it stands within 120 m of ANY drivable piece: the
  mainline, each of the four north roads, the Del Cerro sub-loop, the side-street stubs, and the three junction pads
  (their outlines from `data/pads.plan.json`) — and not within 5 m of any of their pavements. Two bands, two caches: the
  loop's own band (120 m of the mainline) still reads the old `data/buildings.cache.json` with the old rule, so the
  loop's buildings are exactly v0.19.0's (153 of them; the expansion cache would give the same 153 there, none new or
  edited); the new band reads `data/buildings.expansion.cache.json` (P0 step 7). Measured: **181 new buildings — 61 along
  the north roads and 120 along the Del Cerro sub-loop and the stubs.** OSM holds only 74 footprints within 120 m of the
  north roads (Waring 4, Princess View 32 — the Grantville self-storage and industry, Mission Gorge 23, Jackson north
  15): the Allied Gardens houses along Waring are not mapped in OSM, and the Mission Gorge apartment blocks (C 500-1000)
  are mapped as a handful of large footprints. That is what OSM has; nothing is invented. Both caches and the provenance
  are synced into the workshop by `tools/ship_sd.sh` / `ship.json` (`BUILDING_CACHES`); airoso's are the source of truth.
- **The cut faces are rock.** A new ship step (`tools/rock_faces_blend.py`, after the kn5 prep and the thinning, before
  the split into road / race scenes) reads the same auto-cut declaration the ground release built the walls from and, in
  each cut's band (the declared side, from the curb to the cut's reach + its top rounding + 6 m), moves every ground
  triangle standing steeper than 0.7 m per metre (35 deg, the angle at which loose earth stops holding — steeper than
  that beside these roads is cut rock, not a grassed bank; the real faces climb 1.1-1.6) into its own mesh
  `1GRASS_ROCK_<tile>`. Nothing moves: the split only decides which mesh a triangle belongs to, and the two meshes share
  their boundary by position, so there is no crack. The name keeps the `1GRASS` prefix on purpose — same `surfaces.ini`
  key (GRASS), same physics, read as ground by every gate — and binds its own pbr row (`1GRASS_ROCK`, before `1GRASS`),
  so the loop's turf override never reaches it; GrassFX leaves it out (`ext_config` GRASS_MESHES). The split lands at the
  toe (the first batter row past the sidewalk) and at the top rounding by that one slope rule; a cut whose real rise is
  under 3 m (the ledger's own "real wall" bar) is a bank and gets no rock; rock patches under 40 m2 go back to grass,
  grass holes under 60 m2 (the lattice's 1 m bench rows across a wall) become rock. Self-checked: no rock face under a
  pavement sheet, every triangle accounted for, no vertex moved, every mesh under the cap.
- **The rock texture is ours.** `textures/make_sandstone_cut.py` draws a tileable sandstone / conglomerate pair (diffuse +
  OpenGL normal, 1024², 4 m per tile) deterministically — the Stadium Conglomerate and Friars sandstone the Mission Gorge
  cuts stand in: tan bedded sandstone, rounded cobbles (~20 %), dark weathering streaks under the rim. No captured pixels,
  CC0, recorded in `assets/licenses.json` and `fleet/reference/ASSET-LIBRARY.md`; bound by `track.config.json
  texture_overrides["1GRASS_ROCK"]`, synced in with the chaparral tile (`TRACK_TEXTURES`). The UVs run along the wall and
  up it (a top-down projection would stretch the tile 1.5-3x on a face this steep).
- **The thin lighter triangles at the foot of the cuts, fixed at their cause.** The ground release halves the terrain's
  edges and chooses the triangles in PLAN, on the flat, before it raises the batter; a triangle running from the toe row
  to the second batter row then cut through the raised face as a tooth standing flatter than the wall, lit from above
  while the wall is in shade — the pale sawtooth at the foot of every Jackson cut (`p4-proofs/stills/v0190_jackson_toe.png`,
  the v0.19.0 build). Now, once the heights are set and before the release's own cap checks every face against the
  pavement, every triangle of a raise-only cut zone whose corners are all released, within 30 m of the road and clear of
  every drivable sheet (the walk, the corner aprons, the junction pads) is re-triangulated on the raised surface
  (Blender's beautify: edge rotations only, no vertex moves, none made). It took three rehearsals to fence it right: the
  first two rotations (over every zone face, then inside the band) each left two grass samples 7 mm over J1's corner
  apron deck, a sheet the release tool's cap does not know (it reads ROAD / CURB only) — verify_mouths refused both, as
  it should. Measured on the final rule: 35,692 edges rotated, thin toe triangles in the cut bands 5,182 -> 2,258; on
  the Jackson 320-485 wall itself 228 -> 155, of which the slivers up the face (3-7 m out) 139 -> 99 and beyond 7 m 40 ->
  13; the 38 in the flat 3-4 m shoulder between the walk's buried apron and the first batter row are untouched (the
  fence keeps the rotation off the walk), and that shoulder's zigzag edge against the batter is what still shows at the
  foot (`p4_jackson_toe.jpg`, before / after). The rest lie in the face's own plane and do not show.

**Rehearsal (full chain, `--no-install`; v0.19.0 = `D:/k10-scratch/phase1/r3run`, the installed build).**

- **Every gate reads exactly as v0.19.0** (`p4-proofs/gates_v0190.txt` vs `gates_p4.txt`, line for line): Free Roam soft
  top 8, severe 0, kinks 2.67 per km, edge drops 96, audit 53; Speedway / Reverse severe 4 / 6, kinks 6.46 / 6.09,
  barrier_missing 0, no_route PASS (0 of 439 probes, the same reachable area); the new roads driven both ways PASS
  (kinks 2.39 / 2.53, edge drops 40 / 38); verify_mouths 32, verify_stubs 26 + 29, verify_pads J2-J4, verify_signs 19,
  the fold fans, kn5_ground_check on all three layouts (the same wall / lamp / sign / deck lines), rib_check 69 (worst 4
  of 5), all PASS; house_seat_check PASS on **334** buildings (153 + 181; floating / sunken / buried 0). It ends where
  v0.19.0 ends: "NOT INSTALLED" on the Free Roam lap's own soft-top rule, red since v0.18.0, nothing new red.
- **Buildings:** the 153 within 120 m of the loop are identical to v0.19.0's on the built model (0 moved, 0 missing, 0
  extra; `analysis/compare_buildings.py`); 181 new (128 houses, 53 buildings): 61 along the north roads, 120 along the
  Del Cerro sub-loop and the stubs. Vertices in the model: HOUSE 22,887, BUILDING 4,349 (both under the 65,535 cap, one
  mesh each); the budget's "< 0.6 MB" holds (the road model grew 2.9 MB in all, the rock meshes and their two textures
  included).
- **Rock:** 10,718 triangles, **12,459 m² of cut face** in 10 of the 16 cuts standing 3 m or taller, 8 meshes, 8,077
  vertices: Jackson's south-west wall 4,431 m², Mission Gorge's north side 3,584 m², its south face 2,301 m² (the s
  1475-1560 wall inside it) and another 595 m² by the crest, Princess View's left cut 835 m², the rest 46-228 m². The
  texture is the generated sandstone pair (override, 367 KB). Stills: `p4-proofs/stills/p4_jackson_walls.jpg` (driver's
  eye, climbing, the walls on the right), `p4_jackson_walls_rev.jpg`, `p4_jackson_toe.jpg` (the foot of the 320-485 cut,
  before / after), `p4_mg_cut_cowles.jpg` (the south face on the right, Cowles ahead), `p4_mg_apartments.jpg`,
  `p4_grantville_waring.jpg`, `p4_grantville_pv.jpg` (the self-storage and industry from Princess View), `p4_j5_shops.jpg`.
- **Road kn5 92.74 MB** (v0.19.0 89.82; ceiling 145), 103 meshes (16 ground tiles + 8 rock + the rest as before); race,
  closure, street-only and spawn kn5s byte-for-byte the same sizes; CSP `[LIGHT_n]` 239, intensity and pool untouched;
  GRASS_MESHES the 16 ground tiles, no rock; 1WALL_guard as before. Tests 921 passed, 0 failed (4 new).

**Left, honestly.**
- OSM is thin along the north roads: 74 footprints within 120 m, 61 kept. Waring's houses and most of the Mission Gorge
  apartment blocks are not in OSM; adding them means tracing footprints off the aerial (P0's `aerial-tracing` path, a
  later pass), not inventing them.
- The rock rule is one slope threshold inside the declared cut bands (plus the 3 m rise bar and the patch / hole sizes):
  a real grassed bank steeper than 35 deg inside a band reads as rock, a real rock face flatter than that reads as grass,
  and a few grass tongues stay inside the Jackson walls where a lattice bench is wider than 60 m2 or opens to the hill
  (`p4_jackson_walls.jpg`). The six named walls all stand well over the bar; Kevin's drive and the aerial are the check.
- The foot of each cut still shows a zigzag where the flat shoulder behind the walk meets the first batter row (the two
  vertex rows are offset, so the grass / rock boundary saws between them). The tooth slivers up the face are what the
  re-triangulation removed; a straight toe needs the batter's first row laid along the toe line itself, a change to the
  ground release's lattice, not to its triangles.
- `tools/make_treefx.py` still lists every `1GRASS*` material as a TreeFX surface, the rock faces included (harmless: a
  tree gets its ground height from whatever ground it stands on); the trees sibling branch owns that list.
- `engine-july` mirror pending for `scripts/ac/pbr.py` (`engine-july-snapshot/PENDING-MIRROR.md5`; the live ENG is never
  edited by an agent). The suite's one red, `test_engine_july_mirror_is_byte_identical`, is this worktree's CRLF checkout
  of `scripts/ac/export_kn5_addon.py` (equal to ENG modulo line endings; main's checkout is LF).


## P4 trees — the north network planted by zone, GrassFX confirmed (2026-10-26; branch `worktree-wf_566e8616-71e-3`, not merged, nothing installed)

Plan P4 steps 3 and 5 (A9), one of the four P4 pieces built in parallel (lamps / signs + map / trees + GrassFX /
buildings + rock); the integration agent merges them. Kevin, 2026-10-26, on v0.19.0's side-street closures: *"the
barriers look great"* — the K-rail is the confirmed style, and nothing here stands on one.

**What the trees do, in plain terms.** The game draws each tree itself at runtime (CSP TreeFX): the track file only
carries a list of spots, a species name and a size per spot, and the game stands the model on whatever ground is under
it. v0.19.0 carried the loop's 15,739 spots and left the four north roads bare. This build adds the north's spots the
way the loop got its own: the ground grid is walked in 10 m squares, and each square 6-200 m from a pavement gets a
tree, a bush or nothing, by a fixed dice roll per square, so the same inputs always give the same forest. Three things
are new on the north:

- **The density comes from the aerial.** P0 measured, off the April 2022 NAIP infrared sheets, how much of a 10-40 m
  band each side of each road is tree crown and how much is scrub, per 250 m (`aerial__veg_bins.json`). A square's
  chance of a tree is 2.5 x its bin's crown share, of a bush 2 x its scrub share [invented, GATES-CHANGELOG]. Waring's
  5-14 % crown comes out at the loop's own yard rate, so College and Waring meet at J1 planted by one rule; Jackson's
  rims (20-69 %) and the river belt (30-58 %) come out 3-6x denser than Waring.
- **The species come from the zone** (A9, dossier §6; `track.config.json scenery.treefx.zones`): Waring the suburb mix;
  Princess View, the gorge sides and Jackson's canyon chaparral and sage scrub with oak, Aleppo pine and the odd gum
  over it; the river belt north of Mission Gorge (C 300-1200) sycamore and oak as the willow / cottonwood stand-ins; the
  apartment frontage on Mission Gorge's south side (C 500-1000) street trees; E1, the tall belt on the NE side of
  Jackson's canyon (D 1000-1400), the library's Gum — the eucalyptus until Street View confirms it (0040's species pass
  stays a later request). No palms in the canyon.
- **The caps scale with area.** The loop's 3,500 trees / 9,000 bushes over its own 471.8 planted hectares (7.3 trees
  and 18.9 bushes per hectare) set the north's cap over its 201.9 ha: 1,498 trees / 3,852 bushes. The north is thinned
  on its own; the loop's thinning never sees a north spot, so **the loop's 15,763 lines of trees.txt are byte for
  byte v0.19.0's** (the test and the rehearsal both check it). The aerial implies 8,900 trees on the north; at the
  loop's density 1,550 stand. `scenery.treefx.cap_scale` (1.0) is the lever for Drive 2: 5.9 lets the north carry
  what the aerial shows.

**Where nothing stands.** On the J2-J4 pads (their built outlines + 1 m), within 6 m of any pavement (the curbs, the
walks, the 24 stubs and their K-rail), on the measured real walls (P3's `measure_p3.json`: 16 stretches 3 m or more
on Mission Gorge's south side and Jackson's SW side, the six walls Kevin keeps among them — bare from the curb to
20 m; the lower banks are soil and get their scrub), on Mission Gorge's terracotta median, on the noses and on the
painted / hatched medians. Waring's planted median gets its real trees at st 250-550 (A2: one small pepper or oak every
12 m down the middle, 0.5 m inside the island). The islands' low planting was already there: the assembler plants every
raised island, the north pieces' included, and v0.19.0 shipped it (a first draft of this step planted the islands a
second time; the dry-run still caught it). `verify_race --scenery-only` judges the north zones with
the loop's, before Blender (the plan) and on the written file: 0 trunks in a Speedway lane or wall.

**GrassFX (step 5).** Nothing to change: the writer already lists every physical `1GRASS` tile off the built road
kn5 and never the far ring. The plan's "4 -> 5-6 tiles" was overtaken by 0046's balanced tiling and P3's thinning:
**16 tiles, `1GRASS_0` .. `1GRASS_15`** in `GRASS_MESHES` / `GRASS_MATERIALS`, `GRASS_FAR_*` in neither;
`[TREES] SURFACE_MATERIALS` the same 16 + `1ROAD_road_mat`. (The plan's "surface list hard-coded at :32" was already
retired in 0046: it is read off `data/track.obj`.)

**Chain.** `ship_sd.sh`, `ship_track.sh` + `ship.json` sync the two research files in and `data/treefx.report.json`
out; the make_treefx step prints both planted areas, densities and caps before writing. Tests: +7 in
`tests/tools/test_make_treefx_plan.py` (GATES-CHANGELOG 2026-10-26 "P4 trees").

**Stills** (`source/expansion/p4-proofs/stills/`, day, driver's eye, 1.2 m over the built road on the forward drive
line; the trees are stand-in shapes at the planted spots and sizes, since the real TreeFX models are drawn by the game,
not by Blender): Waring's median trees at s 300, Princess View's canyon side at s 420, Mission Gorge's apartment
frontage at s 650, Jackson's NE rim at s 1150.

**Rehearsed** from fresh copies (`D:/k10-scratch/p4/trees`, the whole chain through Blender, `--no-install`; the gate
extract kept as `source/expansion/p4-proofs/gates_trees.txt`, the planting record as `p4-proofs/treefx.report.json`):
- **Every v0.19.0 number unchanged**: Free Roam soft top 8, severe 0, kinks 2.67 / km, edge drops 96, audit 53; Speedway /
  Reverse severe 4 / 6, kinks 6.46 / 6.09, barrier_missing 0, no_route PASS 0/439 both; the new roads both ways PASS
  (kinks 2.39 / 2.53, edge drops 40 / 38); 32 mouths, 26 stubs + 29 curb cuts, pads J2-J4, 19 signs, fold fans, the
  ribbed-hillside check (69, worst 4 of 5), houses, kn5_ground_check x 3 all PASS; road model 89.8 MB (+646 B, run to
  run); the CSP lights byte-identical (238 blocks); GrassFX 16 tiles, no far ring.
- **Trees: 15,739 -> 21,171** (+5,432: the north's 5,406 fill + Waring's 26 median trees); the loop's 15,763 lines of
  trees.txt byte for byte v0.19.0's; the scenery gate 0 trunks in a Speedway lane or wall, on the plan and on the written
  file. Per piece: Waring 691, Princess View 1,124, Mission Gorge 1,965, Jackson north 1,576, the 150-200 m ring the
  growth added around the loop 76 (per species in GATES-CHANGELOG 2026-10-26). Dropped: 55 on the pads, 160 on the
  measured walls. trees.txt 1.53 MB (was 1.13).
- **The run ends `NOT INSTALLED`** on the same two reds v0.19.0 has (Free Roam's own soft-top / edge-drop rule and the
  Speedways' own drive test); installing is Kevin's call (`--force-install` under 0047's rule: no key worse, which this
  run meets).

**Left, honestly.**
- The north stands at the loop's density (1,550 trees where the aerial implies 8,900): the cap is the plan's rule, and
  `cap_scale` is the one knob. Kevin's seat decides after Drive 2 whether Jackson's rims and the river belt want the
  aerial's density (5.9) or the loop's.
- The species are stand-ins by zone (A9): the Gum model is the eucalyptus on E1 until Street View confirms; 0040's
  species pass (jacaranda, coral tree, pepper, the flowering shrubs) is still the later request.
- The stand-in stills show where and how dense; the real foliage is the game's. Nothing on the loop moved.
- The lamps (D4, lamp 77), the signs (M3 / M4), the map, the buildings and the rock texture on the cut faces are the
  other three P4 pieces, merged after this one.

## P4 signs — the north corners, the Speedways' own M3 / M4, the per-layout map (2026-10-26; branch `worktree-wf_566e8616-71e-2`, not merged, nothing installed)

Kevin, 2026-10-26, on v0.19.0's barriers: *"the barriers look great"* — K-rail confirmed (this entry's plates stand behind
them where a turn's outside is a stub). P4 step 1 (signs, A8 / A7) and step 6 (map, A12), one of the four P4 pieces built in
parallel; lamps, trees + GrassFX, buildings + rock are sibling branches, merged after.

**What was built (in plain terms).** A W1-6 "large arrow" is the yellow plate with the black arrow that stands just past
the outside curb of a tight corner, square to the road you arrive on — where a car that did not turn would end up. Two
things stopped the rule seeing the new corners. First, each north road piece ends at its junction pad's cut, so no piece
carries the turn made ACROSS the pad; the rule now also reads ONE stitched centre line J1 → J2 → J3 → J4 → J5 through the
pads (`tools/expansion_lines.centre_ribbon`), with the built pad decks as pavement, and finds the three turns both ways.
Second, M3 (College → Navajo) and M4 (Navajo → Jackson) stand where Free Roam now drives straight on into Waring and
Jackson north: an arrow there would point you away from a real road. Those two corners are marked `per_layout` in
`signs.json`: Free Roam gets no plate (the rule's own skip), and each Speedway gets ITS own plate behind ITS sealing wall
(the K-rail curb strip that runs across the opening in that layout), built into that layout's `RACE_CLOSE_<TOKEN>`
collection and shipped in its closure kn5 — the file only that layout loads. A new rule clause makes the first case
general: a failed-to-turn ray that runs 8 m or more down ANOTHER road before it leaves pavement is "a through road" and no
shared plate (v0.19.0's M3-rev would have stood at the Waring mouth's far corner pointing away from Waring).

**Where the plates stand** (dev pass on the v0.19.0 reference loop.blend; the rehearsal below reads the same):
- **J2** (Waring → Princess View): forward, at the pad's west curb return between Princess View and the Waring south-west
  stub (the ray crosses the deck; clearance 1.56 m); reverse (Princess View → Waring, a left), at the curb return by Mound
  Ave — a grazing exit, the post stepped 0.90 m square off the ray to the outside (the new mesh-stage fallback, confirmed
  by the gate's own ray).
- **J3** (Princess View → Mission Gorge): forward, at the north curb return beside the quarry drive (1.51 m); reverse, at
  the west curb return between the Mission Gorge west stub and the quarry drive (stepped 1.15 m).
- **J4** (Mission Gorge → Jackson): forward, the ray runs down the Mission Gorge EAST stub arm and the plate stands behind
  its K-rail (A8 as written: 3.44 m from the rail, 2.75 m clear of the pavement); reverse, at the north-west curb return by
  the visitor-centre entrance (1.50 m).
- **M3** at J1: `M3-fwd@race_cw` on the Waring mouth's deck 1.67 m behind the Speedway's wall; `M3-rev@race_acw` on the
  loop's walk at Waring's south-west corner, 1.61 m behind Reverse's wall. Free Roam: no plate (College runs on into
  Waring: the ray never leaves pavement; Navajo westbound runs 16 m across the opening: a through road).
- **M4** at J5: `M4-fwd@race_cw` on the walk just east of the Jackson-north mouth (1.76 m); `M4-rev@race_acw` on the mouth's
  deck (1.62 m; the ray crosses the curved strip obliquely, so the post is placed by the nearest wall face, not by its
  length along the ray). Free Roam: no plate (the apex is 13 m from the J5 mouth, the mouth-flare rule).
- Every one of v0.19.0's 19 plates stands exactly where it did.

**The gate.** `verify_signs` measures a layout plate against the walls its layout loads (1.3–3.0 m to the sealing wall;
on the deck, on no wall; the mainline's disc) and every post against every wall (≥ 0.5 m, the lamp rule's number); its
new check (m) asks, per layout and per corner, "does THIS layout load a plate here, or does the rule's own skip apply to
it?" — the question v0.19.0 could not ask (M3 / M4 skipped everywhere, the Speedways turning there with no arrow). The
closure kn5 guards (`split_exports`, `check_race_kn5`, `verify_kn5`) admit a layout's own `SIGN*_<token>_<k>` plates and
their solid textures into its closure file and nowhere else; `verify_race`'s scenery check judges a layout plate against
its own layout only. The signs step runs AFTER the race furniture now, every ship (the furniture author empties the
closure collections). Every number: GATES-CHANGELOG 2026-10-26.

**The map (A12).** `layouts[].map: "lap"` on both Speedways: their minimap and Content Manager outline are drawn from the
13.5 km lap alone, to its own extent (no 1.21× shrink for roads they cannot reach); Free Roam's and the root's show the
whole network. Opt-in; a track without the key gets byte-identical maps.

**Tests:** `tests/tools/test_p4_signs.py` (11); the suite 926 passed, 2 failed — the two known reds of this checkout
(`test_engine_july_mirror_is_byte_identical`, `test_snapshot_copies_match_their_manifest_and_stay_small`: the CRLF
checkout of `scripts/ac/export_kn5_addon.py`, as on main). No engine-july file touched.

**Rehearsed** (`D:/k10-scratch/p4/signs/run1`: fresh workshop copy minus build/release, fresh engine-july copy with the
snapshot's two differing files, the FULL chain from this branch, `--no-install`): see "Rehearsal numbers" below.

**Stills** (`D:/k10-scratch/p4/signs/run1/stills/`): the J2 approach with its arrow (driver's eye), Speedway's M3 at J1,
Free Roam at J1 with no arrow, the three maps.

**Left, honestly.**
- Drive 2 asks whether the layout plates read right from the seat: M3-rev@race_acw and M4-fwd@race_cw stand on the loop's
  own walk beside the sealed openings (the wall stands in for the curb there), the other two on the openings' decks.
- J4-fwd stands 3.4 m behind the Mission Gorge east K-rail (the march found a modelled walk at the stub's end); a plate
  nearer the rail is a `slide_along_curb_m` / `base_xz` pin in signs.json if Kevin wants it closer.
- The north plates' lateral offsets are the CONNECTOR rule's (1.33 m, a 1.5 m walk); the north roads' real walks are the
  pads' returns. The 1.0 m gate minimum holds on every one.
- Speed-limit plates (A8: Waring 35/40, Mission Gorge 55) and the W1-7 second-pass devices are not built; the rule still
  builds W1-6 only.

## P4 — dressing, integrated → Drive 2, v0.19.1 (2026-10-26; branch `worktree-wf_566e8616-71e-5` of k10-track-agents, off airoso main 1b5a6b3; rehearsed twice — the second after the lenses' fix round; not installed)

The four P4 pieces built in parallel are one branch: lamps (`worktree-wf_566e8616-71e-1`, fb4569f), buildings + rock
(`-4`, 3fde21a), trees + GrassFX (`-3`, 364699d) and signs + map (`-2`, 9e2e72e), merged in that order onto airoso main
with every conflict resolved as a union of both sides' intent:

- `tools/ship_sd.sh`: one chain in the order the pieces need — the lamps inside the assembler (draft stage), the rock
  faces inside the prep phase after the I-8 pavement and before the split, the signs AFTER the race furniture on every
  ship (the signs branch moved them there; `--skip-blend` included), the map and TreeFX after the exports, then the
  gates; the sync-in list carries the lamp research, the two building caches, the sandstone pair and the trees'
  research; the sync-out list carries `lights_ini_check.json`, `rock_faces.json` and `treefx.report.json`.
  `tools/ship_track.sh` and `ship.json` match (parity tests green; `steps.draft` loses `signs`, `steps.author` gains it
  after `race_verify`).
- `track.config.json`: `scenery.streetlights.expansion`, `scenery.treefx`, `terrain.rock_faces`, the `1GRASS_ROCK`
  texture override and the Speedways' `map: lap` all land; **version 0.19.1**.
- `tools/place_signs.py` / `tools/verify_race.py`: the signs rewrite carries the lamps' `lamp_bases_xz` reads (the
  pieces' posts have their own road-ward); `build_loop_blend.py` carries both the lamp planner and the two-band
  buildings pass; `fleet/GATES-CHANGELOG.md` and this ledger keep the four "P4 <name>" sections in merge order.
- `engine-july` mirror: the union is ONE file, `scripts/ac/pbr.py` (the `1GRASS_ROCK` row; `engine-july-snapshot/
  PENDING-MIRROR.md5` 92569ac8… → 79baf515…). No other mirrored file was edited by any piece.

**Texts (P5 is Kevin's click, not this branch's):** Free Roam's `ui_description`, the track-level text and both
release READMEs (`release/full`, `release/cc0`, the trees README) now carry the north network — Waring 980 m, Princess
View 1,110 m, Mission Gorge 2,276 m, Jackson north 2,004 m = 6.4 km joined to the 13.5 km loop at J1 and J5, about
19.9 km of road in Free Roam — and P4's dressing; the plant / lamp counts updated (~21,000 / ~320).

**Tests:** `tests/run_tests.py` on the merged tree: 955 passed, 2 failed before the line-ending fix — the two md5 tests
(`test_engine_july_mirror_is_byte_identical`, `test_snapshot_copies_match_their_manifest_and_stay_small`) read CRLF
bytes in this `core.autocrlf=true` checkout; with the snapshot copies and their live counterparts rewritten to the line
ending the manifest md5s were taken on (working tree only; `git diff` empty) all three md5 tests pass. The suite on
the final commit was re-run as the rehearsal started (`D:/k10-scratch/p4/integrate/tests_final.log`).

**Rehearsal run 1 (the merged branch at ecf5f5d; `D:/k10-scratch/p4/integrate/chain_run1.log`, project `proj_run1`):**
the FULL chain, `--no-install`, on fresh copies (SHIP_PROJ = k10-sd-v021/project minus build/release, ENG = engine-july
+ the snapshot's `pbr.py`, AIROSO = this worktree) ended at 22:20 exactly as v0.19.0's did — `NOT INSTALLED` on the two
reds red since v0.18.0 (Free Roam's lap soft-top / excursion rule; the Speedways' own drive test), nothing new red.
Every v0.19.0 floor number equal: Free Roam ground-on-top 8 / severe 0 / kinks 2.67 / excursion drops 96 / audit 53;
Speedway / Reverse severe 4 / 6, kinks 6.46 / 6.09, barrier_missing 0, audit 53 / 53, no_route PASS 0/439 both; the
new roads' lines PASS fwd / rev (kinks 2.39 / 2.53, drops 40 / 38); verify_mouths 32, verify_stubs 26 + 29, verify_pads
J2–J4 (seams 1.2 / 0.7 / 2.4 mm), **verify_signs 29 posts PASS** (19 + 6 north + 4 layout plates), fold fans 3x3,
rib_check 69 (densest 4 of 5), house_seat_check PASS on 334, kn5_ground_check PASS x3 with 323 lamp posts (seat-gap
median −3.03 m, hovering 0), check_lights_ini 323 / 323. Road kn5 **94,316,244 B** (v0.19.0 89,815,220; the lamps'
+1.56 MB and the buildings + rock's +2.9 MB add up; ceiling 145 MB); race / street kn5 byte-identical in size, each
closure +~10 KB (its M3 / M4 plates). ext_config: 323 `[LIGHT_n]` at 255,165,30 / 0.015, GRASS_MESHES the 16 ground
tiles, no rock and no far ring in it. Rock 10,716 faces / 12,459 m2 in 8 meshes; TreeFX 21,171 (the north 5,406 + 26
median trees; the loop's first 15,739 lines byte for byte v0.19.0's); the Speedways' maps their lap alone.

**The four lenses' refusal of run 1 (2026-10-26 evening) and the fix round, each at its cause — never a gate loosened:**

1. *Trees on the cut faces and on walks* — 11 north plants stood on `1GRASS_ROCK` faces (Mission Gorge's north side
   C s 936–1023, Princess View's left cut B s 697–733) and 2 on a walk: `make_treefx` kept plants off P3's 16 measured
   walls only, while the rock step splits 10 of the 16 cut bands. *Cause:* the planner judged plans, never the built
   ground. *Fix:* the **built-surface guard** (`tools/make_treefx.py BuiltSurfaces`): every guarded plant is read
   against the gate OBJ last — dropped when the triangle under it is a road, a walk, a rock cut face, or a HOUSE /
   BUILDING footprint (+ 1.0 m). The loop's lines keep their numbering; only the dropped lines go.
2. *Trees through roofs* — 593 plants stood inside a building footprint (131 on the north; 377 of them v0.19.0's own):
   the trees and the buildings were placed without each other. *Fix:* the same guard (building kind). On the loop this
   drops v0.19.0's roof-piercing plants too — a change to what Kevin drove, stated here: a tree through a roof is wrong
   in any reading, and the lines that stay are byte-identical.
3. *The cut toes a sawtooth, grass tongues up the faces* — along the whole Jackson 1225–1525 wall the foot read as 1–2 m
   green teeth into the rock; 146 steep grass faces (115 m2) stayed inside Jackson's faces. *Cause:* the slope rule read
   every triangle alone, and the ground release lays the batter as lattice rows: where a flat row meets a raised row the
   triangles between them alternate flat / steep. *Fix:* `tools/rock_faces_rules.py` (pure, tested) called by the rock
   step: a grass tooth (two of three neighbours rock) becomes rock, a rock tooth becomes grass, synchronously, 2 passes;
   a grass tongue under 60 m2 with 60 % or more of its boundary against rock (a bench row across the wall, open to the
   hill) becomes rock; speckles under 40 m2 dropped before and after; two rounds. The lace is now MEASURED
   (`data/rock_faces.json boundary_smoothing`): grass / rock teeth 380 / 893 → **100 / 137** on run 2's build (0 beneath a pavement; per zone: Jackson's SW wall 27 / 46 over 1.5 km, Mission Gorge's north side 29 / 32, its south face 21 / 25 + 5 / 6 by the crest, Princess View's left cut 11 / 13); 179 tongue faces in 82 tongues filled, 3,356 speckle faces dropped, 0 holes left. The "beneath a pavement"
   rule reads height now (a corner is beneath a sheet only when the sheet is higher than it; a corner over the walk's
   buried apron is not), the self-check with it. No vertex moves; the per-face slope rule is unchanged.
4. *Buildings 1.9–9.3 m from their true place* — the assembler projected footprints with 111320·cos(lat) / 110574 while
   the roads use the WGS84 series (110,901 here): 0.3 % short, 9 m south at J4, 2.7 m on the loop. *Fix:* the buildings
   pass uses the roads' own series (`build_loop_blend._meters_per_degree`). This MOVES every building to where OSM has
   it — the loop's 153 included (by up to 5 m), a decision made here and stated, not a silent change.
5. *Crowding on Del Cerro Blvd* — 10 new houses had a wall corner on the built walk: the crowding rule read the
   centroid against the declared half width. *Fix:* besides the centroid rule (5 m), no footprint CORNER within
   `BUILDING_CORNER_CLEAR_M` 3.1 m of the pavement edge — the curb profile's own width (curb face 0.08 + walk 1.8 +
   grade strip 1.2 m), so no wall stands on a walk. Both bands. Offline replay on run 1's inputs: 334 → 329 (the loop
   153 → 145: eight v0.19.0 houses whose corner lands on the walk once they stand in their true place; the north 61 →
   62; Del Cerro and the stubs 120 → 122).
6. *Terrain beyond 40 m "identical"* — the truth lens found 3,108 ground vertices only in the merged build and 221 only
   in v0.19.0 beyond 40 m of any road (the thinning keeps a different set after the release's re-triangulation), the
   surface within 4 cm (p95) except one lattice point 1.26 m off on a 1.7 m/m bank at (−1764, 2793). Restated here as
   what was measured: *no vertex moves* is true of the release and rock steps; the SHIPPED ground vertex set differs
   from v0.19.0's by what the thinning keeps, the surface does not (within 4 cm). Not a fix — a true statement.
7. *The two gate widenings named* (the gates lens asked): (a) a race layout's closure kn5 may carry its OWN layout's
   `SIGN*_<token>_<k>` plates and materials (verify_kn5 (f), check_race_kn5 `--role closure --owner`), and the common
   kn5 gains a NEW refusal of any sign plate; (b) verify_signs waives on_road for a LAYOUT plate standing on the sealed
   opening's deck and requires 1.3–3.0 m of wall clearance + on_wall instead. Both scoped to the owner token; no number
   moved. They are in GATES-CHANGELOG "P4 signs" and repeated in the P4 integration entry.
8. *Not fixed, by the plan's own source rule:* the Mission Gorge apartment blocks (C 500–1000) and Waring's Allied
   Gardens houses are not in OSM, so they are not built (A10 says "from OSM footprints"). Adding them is a research
   step — footprints traced off the April 2022 aerial into `buildings.expansion.cache.json` with provenance — not an
   invention here. Left.
9. *One plant through the guard's ring, found by run 2's own post-check* — of 20,464 written plants, one loop Sage at (−1358.81, −1172.46) stood 6 mm inside a house's 1.0 m ring. *Cause:* the guard judged the plan's exact spot (4 mm clear) while `trees.txt` carries centimetres, and the rounding moved it 1 cm toward the wall. *Fix:* `make_treefx` rounds every spot to the file's own precision BEFORE any guard (corridor, apron, built surface) and writes that rounded spot; the plan's entries carry it too, so `verify_race` G judges the numbers the file holds. No new threshold — the file's precision (0.01 m) is the rule. Test `test_built_surface_guard_judges_the_spot_as_written` (a diagonal wall; a spot 0.4 mm clear raw, 4 mm inside once rounded). Re-proved in place on run 2's built OBJ (`p4-proofs/fix-round/treefx_rerun.log`: 20,463 plants, building drops 696, post-check rock 0 / walk 0 / building 0, in-footprint 0, G scenery PASS) and by run 3 (EXIT 1 on the same two reds, 0 Tracebacks; road kn5 94,174,420 B, +656 B vs run 2 (the ground thinning's run-to-run jitter, 14 vertices; every gate value equal; the other kn5s the same bytes); 20463 plants, post-check 0 / 0 / 0, in-footprint 0; gate JSONs moved vs run 2: `audit.json` (1 leaves); `audit.race_cw.json` (1 leaves); `audit.race_acw.json` (1 leaves); `verify_mouths.json` (1 leaves); `rib_check.json` (3 leaves); `house_seat_check.json` (1 leaves); `race_verify.json` (7 leaves); `terrain_thin.json` (121 leaves); `ground_release.report.json` (457 leaves)).

**Rehearsal run 2 (the fix round; `D:/k10-scratch/p4/integrate/chain.log`, fresh copies again, `run2.sh`):** ended 2026-10-26 23:31 MDT (42 min), 0 Tracebacks, `EXIT 1` on the same two pre-existing reds as v0.19.0 (`GATES: street drive_test exit 1, street audit exit 1, race drive_test exit 1, race audit exit 1, race no_route exit 0, kn5_ground_check exit 0` — v0.19.0's line, word for word; NOT INSTALLED). **Every v0.19.0 floor number equal:** Free Roam soft top 8 / severe 0 / kinks 2.67 / edge drops 96 / audit 53; Speedway / Reverse severe 4 / 6, kinks 6.46 / 6.09, soft top 8 / 4, barrier_missing 0, audit 53 / 53, no_route PASS both (0/439 probes, leak 0, reached 138.8 / 138.2 k m2); the new roads' line gate PASS fwd / rev (kinks 2.39 / 2.53, drops 40 / 38, soft top 0, severe 0); verify_mouths 32 PASS (J1 0.006 m, J5 0.017 m), verify_stubs 26 + 29 PASS, verify_pads J2–J4 PASS (seams 1.2 / 0.7 / 2.4 mm), verify_signs **29 posts / 29 plates** (19 + 6 north + 4 layout plates), 176 skipped, PASS, fold fans PASS 3×3, rib_check **68** step jogs (v0.19.0 69; densest 4 of 5) PASS, house_seat_check PASS on **329** buildings (floating / sunken / buried 0, contact −0.34..−0.145 m, lowest roof 1.601 m over its ground), kn5_ground_check PASS ×3 (323 lamp posts, no-ground 0.0 %, seat-gap median −3.03 / p95 −2.71, hovering 0; sign posts 24 / 26 / 26; road-over-ground 12 / 10,785 samples, p95 +0.022 m), check_lights_ini 323 / 323 PASS, verify_race G lamps 323 / 323 (min margin 2.434 m), G scenery on the WRITTEN trees.txt PASS (0 in a lane or a wall; nearest 0.654 m, the same loop median plant as v0.19.0). **Built and looked at:** 329 buildings at the roads' own projection (the replay's bands: the loop 145, the north 62, Del Cerro + the stubs 122), the view lens's own check 0 floating / 0 with a wall over a road (run 1 had one of each); rock **9,805 faces / 11,935.7 m2 in 8 meshes** over 9 of the 16 bands (run 1 10,716 / 12,459 — the clean-up's teeth, tongues and speckles), the lace 380 / 893 → **100 / 137** grass / rock teeth, 0 beneath a pavement, 179 tongue faces in 82 tongues filled, 3,356 speckle faces dropped; the ground release's toe step 35,686 edge rotations over 263,599 faces, thin toe triangles 5,182 → 2,257. TreeFX: the planter's built-surface guard dropped rock 10 / walk 2 / building 695 (592 of them v0.19.0's own loop plants); **20,464** plants written; the post-check of the WRITTEN file against the gate OBJ (`p4-proofs/fix-round/post_trees_check.json`) found rock 0 / walk 0 / **building 1** / road 1,128 (the 1,128 are the islands' plantings, unguarded by design: 599 on the pavement under an island, 529 on a median), the view lens's ray check 0 in any footprint. That one — a loop Sage at (−1358.81, −1172.46), 4 mm clear of a house's 1.0 m ring in the plan and 6 mm inside it once `trees.txt` rounded the spot to centimetres — is a bug in the guard, fixed at the cause (item 9 below), re-proved in place on run 2's own built OBJ (the TreeFX step and its gate re-run: **20,463** plants, building drops 696, post-check 0 / 0 / 0, in-footprint 0, G scenery PASS; `p4-proofs/fix-round/treefx_rerun.log`) and by rehearsal run 3 (ended Tue Oct 27 00:27:34 MDT 2026, 0 Tracebacks, `EXIT 1` on the same two reds (`GATES: street drive_test exit 1, street audit exit 1, race drive_test exit 1, race audit exit 1, race no_route exit 0, kn5_ground_check exit 0`). The road kn5 is 94,174,420 B vs run 2's 94,173,764 (+656 B: the ground thinning's run-to-run jitter — 14 ground vertices of 552,868, `audit grass_verts` 429,696 → 429,710, one mouth's grass sample 1 mm, one roof 1 mm; v0.19.0's own two rehearsals differed by 646 B the same way; every gate value equal; race / closure / street / spawn kn5s the same bytes); the plan-stage scenery count 20,736 → 20,737 (one fill spot more before the gate OBJ exists; the WRITTEN file is identical, so is its race_verify.scenery.json); trees.txt byte-identical to the in-place re-proof (20463 plants; guard drops {'rock': 10, 'road': 0, 'walk': 2, 'building': 696}); post-check rock 0 / walk 0 / building 0 / road 1128 (the islands); in-footprint 0; house_seat_check PASS on 329; check_lights_ini 323 / 323; rock 9802 faces / 11935.7 m2, teeth [100, 137]. Gate JSONs that moved between run 2 and run 3: `audit.json` (1 leaves); `audit.race_cw.json` (1 leaves); `audit.race_acw.json` (1 leaves); `verify_mouths.json` (1 leaves); `rib_check.json` (3 leaves); `house_seat_check.json` (1 leaves); `race_verify.json` (7 leaves); `terrain_thin.json` (121 leaves); `ground_release.report.json` (457 leaves) (`D:/k10-scratch/p4/integrate/run3_outputs/diff_gates_run2_vs_run3.txt`); the run 3 vs v0.19.0 diff is the run 2 one above, line for line, plus the plant count). **kn5:** road **94,173,764 B** (v0.19.0 89,815,220, +4.36 MB: the lamps' +1.56 MB, the 8 rock meshes + the sandstone pair, the new band's buildings; run 1 94,316,244, −142 KB of teeth; ceiling 145 MB), race 11,722,654 / street-only 872,525 / spawns 2,104 B byte-identical in size to v0.19.0, the closures 5,506,635 / 5,505,921 (+9.7 KB each: the 3 meshes, materials and textures of their own M3 / M4 plate). ext_config: **323 `[LIGHT_n]`** at 255,165,30 / 0.015, `GRASS_MESHES` the **16** ground tiles (no rock, no far ring), `[TREES]` the 16 tiles + the road. `1WALL_guard` as v0.19.0 (65,251 → _0 33,192 / _1 33,177). The thinning keeps a different ground set after the toe step (rib_check `terrain_vertices` 552,868 vs v0.19.0 516,090); no gate reads the set, the surface gates above read the surface.

**Gate JSONs vs v0.19.0 (`diff_gates.py` against `D:/k10-scratch/phase1/r3run/proj/data/`):** 33 gate JSONs compared. **Unchanged (no scalar moved):** drive_test.json / .street / .race_cw / .race_acw / .expansion / .line.expansion_rev, no_route ×4 (built + planned), verify_pads, verify_fold_fans, race_kn5, street_kn5, terrain.tiers.report, barrier_bands. **Moved, each explained:** (1) `drive_test.line.expansion_fwd` — `excursion_far_ledges` 21 → 20 and the `worst_excursions` list re-ordered (one informational far flare ledge at s 2851 in place of one at s 153; every gated key — drops 40, kinks 2.39, soft top 0 — identical): the toe re-triangulation re-chose a verge triangle beyond the lane. (2) `audit` ×3 — `grass_verts` 392,918 → 429,696, issues 53 → 53: the thinning keeps more ground vertices after the toe re-triangulation (rib_check `terrain_vertices` 516,090 → 552,868, `thinned.line_vertices` 106,237 → 103,622); not a gate key. (3) `kn5_ground_check` ×3 — lampposts 238 → 323, `lamp_heads` 290 → 393, seat-gap median −3.044 → −3.029 / p95 −2.968 → −2.711 (the 85 new posts seated on their walks with the same 2.5 m footing), signposts 18 → 24 (street: the 6 north plates) / 26 (each Speedway: + its 2 layout plates), their median −0.377 → −0.351 / −0.363. (4) `verify_mouths` — two `max_grass_m` values swapped by 1 mm (−0.019 ↔ −0.020 at mouths 7 and 28): the toe re-triangulation beside a mouth; both still below the deck, the gate reads 'grass above the deck'. (5) `verify_stubs` — `thresholds.trees_checked` 347 → 1,000: the stubs' tree check sees the north's plants now (1,000 is its sample cap); 26 + 29 PASS as before. (6) `rib_check` — step jogs 69 → 68 (near a road 12 → 11), nyquist counts −1..−2, the vertex counts as in (2): fewer jogs, nothing worse. (7) `house_seat_check` — buildings 153 → 329, contact −0.303..−0.143 → −0.34..−0.145 m, `show_m_min` 1.598 → 1.601, the ungated 'buried share' 12 / 0 → 14 / 1 over 30 % / 50 % (one building on a bank, foundation included): every building re-judged at its new place, PASS. (8) `race_verify` (the authored plan) — lamps 238 → 323, lamp 53's margin 2.435 → 2.434 m (lat 16.924 → 16.923, its re-seat), scenery trees 15,739 → 20,736 on the plan, `scenery_beside` 392 → 391, the nearest ids renumbered (`median_planting#2398` → `#2336`: the same plant, 62 dropped lines before it). (9) `race_verify.scenery` (the written file) — signs 19 → 29, trees 15,739 → 20,464 (20,463 after item 9's fix), beside 392 → 395, the nearest ids renumbered (Sage #2398 → #2331, Bush #2457 → #2390), the minimum distances identical (0.656 / 0.654 m). (10) `closure_race_cw` / `_acw` kn5 — meshes / materials / textures 8 → 11, tris +62, verts +178 / +180, bytes +9,671 / +9,765: each closure's own M3 / M4 SIGNPLATE / SIGNARROW / SIGNPOST. (11) `signs_measured` — the 6 north + 4 layout plates new, `wall_m` recorded for every plate (a new field), `race_excluded` 0 → 37 (the race objects the street scan excludes), `walls` {RACE 15, cw 8, acw 8, all 65} new. (12) `terrain_thin` — removed lattice vertices 304,201 → 297,597 and every tile's vertex / face counts: the thinning on the re-triangulated toe ground and the rock split; the 16 tiles the same. (13) `ground_release.report` — `cut_toe_retriangulated` new (263,599 faces, 35,686 rotations, thin 5,182 → 2,257), `coincident_vertices_welded` 6,990 → 7,053, the per-face cap's worst list `face_cap.those` re-ordered (its ten worst stand elsewhere after the rotation; the cap's own numbers 0.004–0.035 m): the fix round's toe step. (14) `ai_verify` ×2, `race_authored`, `signs_measured.blend` — path strings only (the scratch project's). The full diff: `p4-proofs/fix-round/diff_gates_run2.txt`.

**Stills (`D:/k10-scratch/p4/integrate/stills/`, day + night, off run 2's gate OBJs):** the full set in `D:/k10-scratch/p4/integrate/stills/` (34 files: 6 night, 8 day rock / buildings, 4 trees, 7 signs, 3 maps + 3 outlines, the signs preview; the same set rendered by the view lens into `D:/k10-scratch/p4/verify_view/run2/`), the after-set copied as JPG into `p4-proofs/fix-round/stills/*_run2.*`. Seen: `day_jackson_toe` — the green tongues up the Jackson 320–485 face are gone (run 1's `jackson_toe_run1_before.png` beside it shows 1–2 m green stripes up the wall); the very foot keeps the flat shoulder's zigzag against the first batter row (Left, a vertex row, not a triangle choice); `day_jackson_walls` — rock faces with the few benches the aerial also shows as grass; `day_trees_waring_median` — the median trees every 12 m, the roofs with no trunk through them; `day_grantville_pv` / `day_grantville_waring` — the Grantville blocks off the walk; `night_princess_view_from_j2` / `night_mission_gorge_u1300` — sodium pools on the road, every post on the walk side; `sign_street_J2-fwd` — one arrow past the outside curb at the T, the K-rail beyond; `sign_street_J1_..._noarrow` — Free Roam at J1 with no arrow; `sign_race_cw_M3-fwd` — M3 on the sealed Waring mouth's deck behind the Speedway's wall; `map_street` the whole network, `map_race_cw` / `_acw` the lap alone.

**Tests:** `tests/run_tests.py` on the final code, item 9's test included (957 on the merge + 10 fix-round + 1): **968 passed, 0 failed**, twice (`D:/k10-scratch/p4/integrate/tests_run3.log`, `tests_run4.log`). The 10 fix-round tests and the as-written test pass directly; `bash -n` on both chains OK; `tools/snapshot_engine_july.py --check` OK (pbr.py pending as before).

**Left, honestly** (after the fix round):
- Lamp positions on the four roads are authored at the loop's spacing; the real ones wait on a Street View night check
  (the OSM path is built; fresh Overpass has no street_lamp within 746 m of the four roads). The canyon is dark by D4.
- The north's trees stand at the loop's density (the aerial implies 8,900); `scenery.treefx.cap_scale` is the knob.
  Species are stand-ins by zone; 0040's species pass is still the later request.
- OSM is thin along the north roads: Waring's houses and the Mission Gorge apartment blocks are not there (item 8).
- The rock is one slope rule inside the cut bands plus the boundary clean-up; 100 grass / 137 rock teeth remain along
  ~6 km of boundary and the flat 3–4 m shoulder between the walk and the first batter row is grass, as a real cut's
  drainage shoulder is. A straight toe row in the release's lattice (a vertex change) is the later round, if Kevin's
  seat asks for it. The facet shading of the faces is the game's (smooth-shaded, the sandstone normal map) — Drive 2.
- J4-fwd stands 3.4 m behind the Mission Gorge east K-rail; speed-limit plates and the W1-7 devices are not built.
- M3-fwd@race_cw and M4-rev@race_acw stand on the sealed mouth's pavement behind their wall (verify_signs PASS; that
  pavement is not drivable in that layout) — cosmetic.
- `scripts/ac/pbr.py` is pending its mirror into the live engine-july; this branch lives in the retired
  k10-track-agents repo and lands in airoso by a fetch + fast-forward from 1b5a6b3.

**For Kevin, in plain terms:** nothing about the roads changed between v0.19.0 and v0.19.1 — same asphalt, curbs,
corners and barriers. What changed is everything standing beside them: lamp posts dropped onto the sidewalk the chain
actually built (a lamp is a pole with a buried stub, and every pole now stands on its sidewalk, not above or under it),
arrow signs just past the outside curb where a car that missed the turn would end up, trees placed where the April 2022
aerial shows crown and scrub, the buildings OpenStreetMap knows about, and the steep cut faces along Mission Gorge and
Jackson painted as the tan sandstone they are instead of grass. The fix round after the four checks: no tree stands on
a rock face, on a sidewalk or inside a house any more (the planter now looks at the finished ground, not the plan);
every building stands where the map has it (the old maths was 0.3 % short, which put a house at the far end of Mission
Gorge nine metres from its lot) and no house wall stands on a sidewalk; and the foot of each rock cut is a line along
the ground's own rows instead of a saw blade of green teeth. The game still draws the trees and the grass itself; the
track only carries the list of spots.

## Phase 2 — the Mission Gorge Speedway on v4 (2026-11-03; branch `claude/lm-phase2` off `claude/lm-v4-line`; held, nothing enabled, nothing installed)

Built on v4 (ledger 0065 verdict). The 2026-10-27/28 handoff (832facf: `PHASE2-HANDOFF.md`, `race.north.held.json`,
`race.north.joins.json`, `rehearse_north.py`, `probe_north_blend.py`) is on this branch as found. Its lap-tool change (pad
arms) was never committed; it is re-done here in `scripts/geometry/race_lap.py`, with the curved joins it needed.

**The lap.** `race.laps.north` (held in `source/expansion/phase2/race.north.declaration.json`, not in `track.config.json`):
Waring 0→317, Princess View 0→355, Mission Gorge 0→745, Jackson north 651→0, Navajo (mainline 2317→1517, reversed).
`race_lap.stitch` now takes `joins_file` / `joins` (a declared join's interior points replace the straight one between exactly
those piece ends; ends within 0.05 m or refused) and `junction_pads` (each pad must join two consecutive pieces by its two route
arms; every other arm becomes a `pad_arm` exit probed 10 m into the stub, before its Free Roam end barrier). On v4's
intermediates: **8,732.7 m, 2,936 vertices**; the five corners barrier_bands detects are exactly the five joins (J2 v320 R 19.6 m,
J3 v707 R 17.0, J4 v1458 R 19.8, J5 v2130 R 9.1, J1 v2932 R 8.3); **34 exits**: 26 side streets, 6 pad arms (probes equal the
handoff's table within 1 mm), 2 abandoned mainline branches. `tests/tools/test_race_lap_pads.py` pins all of it and the refusals.

**The joins, judged from v4's committed records** (`judge_joins_records.py` → `joins_records.json`: an 8 m band round each
join + 10 m of each approach, every 0.5 m, against the road ribbons at half width, the pads as built and the aprons):

| Join | Line | Records verdict | What the PC authors |
|---|---|---|---|
| J2 Waring → Princess View | curve 30.2 m (chord 28.0), through pad J2 | 909 / 909 samples on pavement | nothing for the surface if step 3 passes; kerbs out v315-333 / in v316-332 on the pad deck (verify_race E) |
| J3 Princess View → Mission Gorge | curve 49.2 m (chord 46.0), through pad J3 | 1,251 / 1,251 | the closure's start at Mission Gorge's median nose (v718, 18 m past the box): see "the median noses" |
| J4 Mission Gorge → Jackson north | curve 43.9 m (chord 42.0), through pad J4 | 1,152 / 1,152 | box carried to v1470 so the pad's Mission Gorge east arm (S5) is sealed by the far strip |
| J5 Jackson north → Navajo | straight 11.6 m, inside the mainline's Navajo/Jackson box | 576 / 576 | the inside kerb (it folds on itself: held as a drop); the curb strip across the abandoned Jackson-south branch, judged on the built deck where the mainline drops its own inside kerb for the ribbon fold |
| J1 Navajo → Waring | straight 14.6 m, inside the mainline's College/Navajo box | 630 / 630 | the inside kerb (same fold class: held as a drop); Waring's median nose 33 m out (v11); coordinated with 0055 (below) |

Records are not the road: the band at half width ignores curb returns, flares and welds. The built judgement is step 3.

**The declaration** (both directions, lap-local; no mainline vertex number, no `race.chicanes`): whole street on Navajo
v2426-2616 (undivided, 17 m: the grid); boxes J2 [314, 334], J3 [695, 713], J4 [1452, 1470], J5 [2121, 2136], J1 [2926, 2];
closure runs [2, 314], [334, 695], [713, 1452], [1470, 2121], [2136, 2426], [2616, 2926]; the Speedway's limits unchanged
(clear 11.36 m, rates, floors); kerbs: 8 at 5 corners, the J1 and J5 insides dropped with their whys; `north_cw` (token `ncw`)
start v2536, grid v2527, `north_acw` (`nacw`) grid v2546, sectors v584 / v1565 (a third and two thirds of the lap, both on
straights).

**Planned (plan_north.py → `plan_north.report.json`).** Containment: **all 34 exits sealed in both layouts** (15 + 11 behind
the closure / on the race strip, 8 on the far strip), planned `no_route` **PASS** both ways, leak 0, 0 doors, nothing forbidden
reached. The mainline declaration is the same with the lap declared (its one difference from the committed
`data/barrier_bands.json`, a bridge span 6.6 m along at s 13312, is the repo's stale `bridge.spans.auto.json`, which now syncs).
**Refused by the corridor's own self-gates in 16 lines, all one cause, the median noses:** Waring's raised median starts 33 m
after J1 (v11) and ends 8 m before J2 (v306), Mission Gorge's starts 5 vertices after J3 (v718); a closure pinned on the far
curb strip at a box edge cannot cross ~13 m to the median's race face at 1:3 in that room (1:1.82 / 1:1.90 on Waring, 1:0.92 and
R 12 m on Mission Gorge), and two pin zones miss their gentlest rate by a little (v683-685 1:5.49-5.67 of 1:6, v1477-1479
1:4.62-4.75 of 1:5.01). No threshold was moved and no box was stretched over a median to hide it.

**The median noses (done 2026-11-04, step 2 below).** Where a median runs into the junction, the closure now ENDS at the
nose, and a short K-rail crosses the far carriageway from the closure to the far curb strip. Before, a diagonal ran from a
far-strip pin to the nose. It is a new closure end kind, declared per corridor (`race.corridor.noses`).

**Pictures** (`source/expansion/phase2/`): `north_overview.png` (the lap, joins, boxes, whole street, both closures, every
exit probe coloured by kind) and `north_junctions.png` (J1-J5 at 0.15 m/px with the pads, stub pavement and stub end lines).

**J1 and ledger 0055.** 0055 owns College's divided run up to the College/Navajo box and the Speedways' College chicane; the
lap's J1 box (lap v2926..2) is that crossroads seen from Navajo, so anything authored at J1 is one change with 0055: the existing
Speedways' College chicane and both their gate matrices are re-run with it, and the J1 tilt question below is answered once for
both entries.

### Phase 2 — step 1 (Mac, done 2026-11-03): the lap, the declaration, planned containment, pictures

`.venv/bin/python tracks/san-diego-lake-murray/source/expansion/phase2/plan_north.py [<out>]` (it exited 1 on 2026-11-03 with
the 16 refused lines; it exits 0 since step 2), `plot_north.py <out>`, `judge_joins_records.py <out>/data/lap.north.json`.
Inputs are the repo's v4 intermediates only.

### Phase 2 — step 2 (Mac, done 2026-11-04, branch `claude/lm-phase2-build`): the nose end, the lap in `ship_track.sh`

**The nose end** is opt-in through `race.corridor.noses` [{end, median, why}]. Each entry names a closure-run end (a box edge)
and its island nose. With the key absent, every tool runs as before.
- `tools/race_corridor.py`:
  - the pin P is the vertex beside the nose, toward the box;
  - its lateral is L = U = the island's enveloped race face plus the strip centre (`nose_pin_g`);
  - the walk from the box edge to P stands open (`nose_open`);
  - `solve(..., nose_pins=)`.
- `tools/barrier_bands.py`:
  - declares the nose (`zones.noses`) and the open walk (zone `box`);
  - the lane at P is the closure's, and it narrows to the closure's lane one vertex earlier, so a lerped lane never sweeps
    the K-rail (drive_test, write_ai_line);
  - the run end joins `nose`;
  - `corridors.<id>.nose_walls` declares the K-rail: P's normal, from the closure's race face (the closure's end cap sits
    inside it) to the far strip centre (its far cap buried there);
  - self-gate 14 `noses`: the nose is a real authored island end with no island before it, the K-rail is >= 0.15 m off it,
    the closure is on the race face and the K-rail on the far strip (both 0.01 m), outside any box, and the lane at P is
    >= 6.5 m.
- `tools/race_furniture.py` + `tools/author_race_furniture_blend.py`: the K-rail is a closure object,
  `1WALL_race_close_<tok>_nose_<P>_0`, in that layout's closure kn5, with rings every <= 1 m so its base follows the crown.
  It clips the kerbs like any closure.
- `tools/verify_race.py`:
  - C': the run end lies on its K-rail's line, every K-rail ring is on its declared line, its far end on the far strip and
    its near end on the closure's race face;
  - J: the same, on the authored rings.
- `tools/no_route.py`: the K-rail is in the planned fill, and the open walk in front of it is allowed at full width.
- `scripts/geometry/median_zone.py`: the K-rail is a band of its own layout, so audit D and drive_test exempt it as they do
  a closure.

**`race.corridor.smooth_window: "station"`** (opt-in, the north lap only) fixes the 4 pin-zone lines. The closure's 4 m
Gaussian ran over +-4 vertices; it now runs over +-12 m of station with trapezoid weights. Where the lap's 2 m curved joins
meet its 3 m streets, the vertex window was lopsided. It pulled the closure 8 cm off its own envelope:
- v683-685: 1:5.49 against a limit of 1:6;
- v1477-1479: 1:4.62 against 1:5.01.

They now read 1:5.91 and 1:4.98, within the 2 % the gate allows. No rate or limit moved. fleet/GATES-CHANGELOG 2026-11-04
records both changes.

**Off is byte-identical.** `proofs/prove_nose_off.py` runs the tree before (2ce9495) and this branch on fresh copies of
v4's project, and the outputs are identical on every key (`proofs/nose_off_md5.json`):
- `barrier_bands.json` byte for byte (the planned fill's seconds blanked);
- both planned no_route fills;
- edge corners `df334caf7bca` (PR 33's number);
- the declared kerbs, the closure / lane / zone / runs of race_cw and race_acw;
- the race-furniture plans: edge 15, kerb 6, close 16, and the object names;
- `kerb_closure_clips`;
- `race_corridor.solve` both ways;
- verify_race on v4's committed `race_authored.json` (0 fails);
- median_zone's bands for both Speedways.

**The north plan, re-run** (`plan_north.report.json`, the pictures redrawn with the K-rails): **PLANNED, exit 0**.
- **Every self-gate clear**: the 16 lines are gone and none is new.
- **34 / 34 exits sealed** in both layouts.
- **Planned no_route PASS** both ways: leak 0, 0 doors, nothing forbidden reached, nothing blocked; 93,412 / 93,414 m2
  reached.
- The mainline declaration is unchanged with the lap declared, and no source file changed.

| Nose | Pin | K-rail cw / acw | Lane at the pin |
|---|---|---|---|
| Waring after J1 (v11, 1.5 m wide) | v10 | 14.59 m | 10.85 m |
| Waring's tail before J2 (v306) | v307 | 14.86 m | 8.91 m (the island's 3-3.9 m tail, listed island) |
| Mission Gorge's splitter after J3 (v718-723, 0.6-1.0 m) | v717 | 17.10 m | 14.11 m |

**The kerbs follow the clip rule.** The box-edge pins at v2 / v314 / v713 no longer clip the outside kerbs; the K-rails now
do:
- J2 outside: v308-333 (was v315-333);
- J3 outside: v696-716 (was v696-712);
- J1 outside: v2927-v5 (was v2927-v1).

All 8 stand >= 0.05 m clear of every closure and K-rail.

Without the K-rails, the planned fill reaches the pockets behind both closures (`tests/tools/test_race_noses.py`). They carry
the seal.

**J1 / J5's held inside kerbs: unchanged, still held.** They are dropped for a surface reason: each folds on itself on a
straight join inside a mainline box, where the mainline drops its own. The nose work touches neither:
- J1's nose walk starts at the box edge v2, past the kerb's v2928-2934;
- J5 has no nose: Jackson north's island starts 15 vertices after J5's box, and the closure reaches it at 1:3.55, within
  limits.

The only change at J1 is the outside kerb's 8 m above. They are re-declared after the PC's step 4, as before.

**Laps in `tools/ship_track.sh`**, ported from `tools/ship_sd.sh`'s LAP_IDS blocks:
- `LAP_IDS` / `HAS_MAIN` / `RK` / `BB` after the layout lists;
- `author_race_verify` and `ship_race_scenery_gate`: the mainline under HAS_MAIN, plus `--lap <lap>`;
- `prep_split` checks `loop_race_<lap>.blend`;
- `ship_export_race`:
  - a stale `<slug>_race_<lap>.kn5` is removed;
  - the mainline common kn5 is exported under HAS_MAIN;
  - each lap's common kn5 is exported and checked (an echo header, as in ship_sd, so the step-header parity holds);
  - the closure token comes from that layout's declaration;
- `ship_ai`, `gate_race_gates` and `gate_kn5_ground` load `RK[$lid]` in place of `<slug>_race.kn5`;
- ship.json carries a `{lap}` template (ship_track_spec + `expand`), and Lake Murray's sync_out lists the lap's line,
  declaration and reports;
- sync_in brings `source/expansion/race.north.joins.json`.

**Parity:** `proofs/ship_track_lap_parity.py` runs the race functions of the old and new script under logging stubs on
Lake Murray's layouts. Every command is identical but two, both intended:
- the `rm` of a stale lap kn5, which matches nothing in v4's workshop;
- the `{lap}` paths, which expand to nothing.

The lap case shows the north layouts loading `_race_north.kn5` and their own closures. test_ship_track_chain's header parity
passes; its 2 guard runs that need bash 4 fail on the Mac's bash 3.2, as before this change.

**Where it meets `claude/fleet-lm-engine`.** That branch's ship_track.sh hunks are the header, the engine selection, draft
functions, `gate_edge_report` after `gate_verify_pads`, the step checks and the final verdict. Its ship_track_spec.py hunks
are `engine` in TOP / ENGINES / lines(). This port touches other functions and other lines:
- the race functions;
- a block after the layout lists;
- `expand`;
- `_rel`'s template set and the sync_out doc line.

No hunk overlaps. Expect a clean merge, or at most adjacent-context conflicts near the step checks.

### Phase 2 — step 2b (Mac, 2026-11-04, `claude/lm-phase2-build`): the PC's step 3 answered — the joins refit, the medians where they stand

**What the PC found** on v4's built road (judge_joins_built.py, after its re-seat fix at 56a0fdd): J1 and J5 PASS. J2, J3 and
J4 failed on severe steps (7 / 8 / 5), where the planned lane's inside face stood on the pads' curb returns. Waring's real
median also runs to a tip at s ≈ 929.8, off the lap line.

**1. The joins, refit** (`phase2/fit_joins.py --write` → `source/expansion/race.north.joins.json`, each join with its `fit`
record).
- **What it measures against.** The pad deck as built: `data/pads.built.json` outline_xz, plus the pieces' own ribbons
  beyond the cut.
  - The built outline is 0.1-1.75 m tighter at the inside corners than expansion.north.json's planned outline. At J2 v324
    it reads 10.18 m, where the PC measured the curb at 10.2-10.4 m.
  - So the fit uses the built outline, not the planned one.
- **What it keeps.** Each curve keeps its end points, end tangents and point count. Every lap vertex number is unchanged
  (2,936), and the lap is now 8,737.9 m.
- **What it fits.** Both race strips stand on the built pavement, on both sides, with the largest smallest radius the
  pavement allows:
  - the radius never drops below w/2 + 0.5 m, so the inside curb line never folds;
  - no join grows more than 25 % longer.

| Join | Strip face (min, both sides) | Judge's lane samples | Radius | Length |
|---|---|---|---|---|
| J2 | -1.32 → 0.00 m | -0.16 → +1.17 m | 17.7 → 19.2 m | 30.2 → 31.3 m |
| J3 | -2.98 → 0.00 m | -1.83 → +1.17 m | 16.1 → 23.0 m | 49.2 → 51.7 m |
| J4 | -2.11 → 0.00 m | -0.94 → +0.98 m | 17.8 → 26.2 m | 43.9 → 45.4 m |

- **On pavement, on both sides.** The fit never had to leave the junction's asphalt on the outside: J3's binding point is
  on its outside, at 0.00.
- **The new corners:** J2 apex v327 (R 19.0), J3 v705 (R 22.9), J4 v1464 (R 26.1).
- **The records judge** (`judge_joins_records.py`) reads 0 band samples off the recorded pavement on all five joins.

**2. The medians where they stand** (`race.laps.north.island_offsets`: scripts/geometry/race_lap.py, tools/race_corridor.py,
tools/barrier_bands.py, opt-in).
- **What was wrong.** Each north median's own centre line (median_bands connector_islands) stands up to 2 m off its connector
  line. The 1.0 m snap dropped every point beyond 1 m, which cut the medians into fragments: Waring v188-264, Princess View
  v477-502 and v534-559, Mission Gorge v724-780 and more (lap vertices).
- **The fix.** The lap now takes each point within 2.5 m, with its lateral offset. The closure stands on the offset island's
  race face.
- **Applied to all four north pieces, not Waring alone.** With Waring alone (variant B, measured), the closure stands ON the
  real median at 530 north_cw / 286 north_acw vertices. The noses move to the real ends:
  - Waring starts at v8, 1.3 m right; it ends at its 2.0 m tail at v315, 1.7 m left, beside the J2 box;
  - Mission Gorge's median runs unbroken from v718 to v1451, beside the J4 box;
  - Jackson's starts at v1490.

**The re-declaration** (race.north.declaration.json):

| Box | Apex | Span |
|---|---|---|
| J2 | v327 | v316-333 (from PC: the tail stands at v315) |
| J3 | v705 | v691-712 |
| J4 | v1464 | v1452-1472 |

The closure runs are [2, 316] [333, 691] [712, 1452] [1472, 2121] [2136, 2426] [2616, 2926]. There are five noses:

| Nose | Pin | Where the K-rail stands |
|---|---|---|
| Waring, J1 side (v8) | v7 | 3 m before the nose |
| Waring's tail (v315) | v316 | on the J2 box edge |
| Mission Gorge, J3 side (v718) | v717 | 3 m before the nose |
| Mission Gorge, J4 side (v1451) | v1452 | on the J4 box edge |
| Jackson (v1490) | v1489 | 3 m before the nose |

A pin on the box edge is now allowed: the median runs up to the box, so there is no open walk before the K-rail. no_route
allows that segment at full width.

**The north plan now** (`plan_north.report.json`, pictures redrawn):
- **34 / 34 exits sealed** both ways.
- **Planned no_route PASS** both ways: leak 0, nothing forbidden reached, 89,000 / 92,095 m² reached.
- Every self-gate is clear **but one line, which is Kevin's call (below):** `clear north_cw: v538 lane 6.44 m < the hard
  minimum 6.5 m`.
  - Princess View's real median there is 4.9-5.9 m wide, about 1 m toward the north_cw side of a 24 m road.
  - That leaves 6.42-6.44 m at v538 / v539 / v542.
  - The median was invisible to the corridor before the offsets: in that variant the closure stood on it.
- `plan_north.py` exits 1 on that line alone; tests/tools/test_race_noses.py pins it as the only one.

**Off is still byte-identical.** `proofs/prove_nose_off.py` re-run on this tree against 2ce9495 gives every key identical,
the same md5s as `proofs/nose_off_md5.json`. No lap without `island_offsets` changes either: the test stitches it and
compares.

### Phase 2 — step 2c (Mac, 2026-11-04, `claude/lm-phase2-build`): Princess View's median fixed at the source; strip keep 0.03; PLANNED

**What the PC's step 3 found on f9d4b42** (its files: `D:/k10-scratch/lm_phase2/{plan_north.f9d4b42.log, joins_f9d4b42.json,
step3b_read.txt, step3b_fine.json, naip/edges.txt, naip/pv_table.txt}`):
- **All five joins PASS** in both layouts. Holes, soft top, severe steps and obstructions are all 0 (J2 severe 7 → 0, J3 8 → 0,
  J4 5 → 0). No join needs step 4.
- **Island sides:** both LEFT of the lap's travel in the engine frame, as the data says. Waring's tail is centred +1.70 and
  tapers out at s 929.6; Mission Gorge's J4 end is +2.00 from v1448, with nothing past v1451 + 0.16. (The earlier "right"
  was the PC's mistake.)
- **Casts on the built OBJ:**
  - All 516 lane samples at ±(w/2 − 1.32) land on 1ROAD. The worst margins are J2 +1.15, J3 +1.17, J4 +1.17.
  - Of the strip faces at ±(w/2 − 0.15) (refined to 2 mm), 498 land on 1ROAD. 18 land on the pad curb's toe
    (1KERB_sidewalk_padJx), never on ground: J2 11 / 126 by 1-19 mm (all on the right, s 948.4-955.4), J3 4 / 208 by
    1-5 mm, J4 3 / 182 by 3-5 mm.
- **Princess View v536-556: the wide median is measurement noise.**
  - expansion.north.json MD7 ("aerial island", one automatic reading every 2.5 m) swings 3.6 ↔ 5.9 m at s 632.5-650, all on
    the RIGHT face; the left face holds at +1.4..+1.9.
  - On NAIP 2022 z18 two street trees stand IN the median (v533-535 and v537-540). Their crowns and westward shadows are what
    the reader took for island.
  - Calibrated to the built faces on the clear run v543-556 (offset −2.58), a line fit puts the right face at −3.45 →
    −3.38 m over v535-v556 (sd 0.35). Projection: scripts-v021 projection.py's WGS84 series on
    source/naip_2022_lm_z18.jpg (a plain-sphere equirectangular is ~9 m E / 5 m N off).
  - The noise runs both ways: about 1.3 m too wide at v538 / 539 / 542, about 1.2 m too narrow at v535-537 and v540 / 541.
  - The real median is about 5.0-5.3 m wide, centred −0.9..−1.0. North_cw's lane beside it is 6.91-6.98 m.
  - v4's built road carries the noise too: a 1KERB ring (+0.18 m) at v538 [−3.91, +1.73], its right face jogging 1.3 m out
    and back.

**1. The median, corrected at the source** (`phase2/fix_pv_median.py --write`; the record is `phase2/pv_median_correction.json`,
and the provenance is also in expansion.north.json MD7 `correction`). The right face of every piece-B row on the tree run
(s 620-647.5, lap v532-v542) is set to the PC's line fit; the left face is kept. Three files change:
- `data/expansion.north.json`: 12 piece-B rows (`median_w_m`, `median_off_m`), plus MD7's polygon and `width_m`;
- `data/median_bands.json`: connector_islands north_princess_view at 11 vertices (lap v532-v542), by expansion_pieces.decorate's
  formula; the points keep their heights;
- `data/connectors.local.json`: north_princess_view's two yellow median edge lines at the same vertices.

The lap's island offsets and the race plan read these files, so they agree with the corrected source.

| lap v | before: left / right / width / centre | after: left / right / width / centre |
|---|---|---|
| v533 | −1.57 / −3.56 / 2.00 / −2.56 | −1.57 / −3.45 / 1.89 / −2.51 |
| v534 | +0.40 / −2.67 / 3.07 / −1.14 | +0.39 / −3.45 / 3.85 / −1.53 |
| v535 | +1.55 / −2.19 / 3.74 / −0.32 | +1.55 / −3.45 / 5.00 / −0.95 |
| v536 | +1.60 / −2.71 / 4.32 / −0.55 | +1.61 / −3.44 / 5.05 / −0.92 |
| v537 | +1.57 / −2.56 / 4.13 / −0.49 | +1.57 / −3.44 / 5.01 / −0.94 |
| v538 | +1.75 / −3.92 / 5.67 / −1.09 | +1.75 / −3.44 / 5.19 / −0.84 |
| v539 | +1.92 / −3.94 / 5.86 / −1.01 | +1.92 / −3.44 / 5.36 / −0.76 |
| v540 | +1.59 / −2.55 / 4.14 / −0.48 | +1.59 / −3.43 / 5.03 / −0.92 |
| v541 | +1.46 / −2.17 / 3.63 / −0.35 | +1.47 / −3.43 / 4.89 / −0.98 |
| v542 | +1.84 / −3.92 / 5.76 / −1.04 | +1.84 / −3.46 / 5.30 / −0.81 |
| v543-v556 | unchanged (the clear run: right −3.62..−3.34, width 4.63-5.19) | unchanged |

(Lap frame, metres off the connector line, + = left of travel. v532 moves by 1 cm: the row s 620 shapes it.)

**2. How the corrected median reaches the built road without regenerating v4.** The tool is
`tools/reshape_island_blend.py` (pure part `tools/island_reshape.py`). It runs on a scratch copy of v4's loop.blend.
- Why not re-run a draft step: an LM chain without `--skip-blend` loses the 7,600 houses. `tools/author_median_blend.py` joins
  its islands INTO CURB / TERRAIN, so re-running it would author every island twice.
- What the tool does:
  - It computes the island's curb rings and deck exactly as author_median_blend lays them, from the old data and from the
    corrected data. The runs are the same, so the vertex count and order are the same.
  - It requires every old vertex to be in the blend (≤ 3 mm), else it refuses and saves nothing.
  - It moves those vertices to their corrected positions. The island's two yellow edge lines (YLINE) follow their face.
  - Faces, vertex order and every other vertex stay as they are, so the prep's 65k splits do not move.
- **Proved on the Mac** with v4's loop.blend (LFS 0656308e) and the f9d4b42 median_bands (`proofs/reshape_pv_mac.json`):
  - all 592 PV island vertices found at 0.00 mm;
  - CURB 78 and TERRAIN 26 vertices moved (stations 200-212, connector frame), YLINE 88; largest move 1.287 m;
  - in a digest of all 145 objects, only CURB / TERRAIN / YLINE differ, in positions only (77 / 24 / 88 vertices beyond
    1e-5 m), with the same topology and materials;
  - re-run on the result against the corrected data: 592 found, 0 moved. Run on v4's blend against the corrected data: it
    refuses (96 vertices not where that data lays them).
- **Known and accepted:**
  - the ring keeps v4's own heights: the island stands where v4 stood it, and the base moves up to 1.3 m across the deck's
    crossfall;
  - the TreeFX median plantings keep their positions (scatter_positions.json).

**3. Strip keep 0.03** (`fit_joins.py`: STRIP_KEEP_M and END_KEEP_M 0.03, the coordinator's call), refit from the original
curves. End points, tangents and point counts are kept: 2,936 vertices, lap 8,739.6 m.

| Join | Strip face, min both sides | Judge's lane samples | Radius | Length |
|---|---|---|---|---|
| J2 | +0.030 m | +1.195 m | 19.1 m | 31.34 m |
| J3 | +0.030 m | +1.195 m | 22.8 m | 51.70 m |
| J4 | +0.025 m (5 mm short, within FIT_TOL_M 0.02) | +1.192 m | 15.7 m (floor 15.75) | 47.15 m |

The new corners are J2 apex v326 (box v316-333), J3 v705 (v691-712) and J4 v1463 (v1452-1472). The records judge reads 0
samples off pavement on all five joins.

**4. Re-plan: `plan_north.py` exits 0, PLANNED.**
- Every self-gate is clear. clear_hard_min_m stays 6.5.
- 34 / 34 exits are sealed both ways.
- Planned no_route PASS both ways: leak 0, nothing forbidden reached, 89,060 / 92,139 m² reached.
- North_cw's lane at v537-v542 is 6.90-6.93 m (it was 6.42 m on the trees). The smallest lane anywhere on the lap is 6.705 m
  (v480, Princess View's other median).
- The mainline declaration is unchanged and no source moved under the plan.
- The existing Speedways are byte-identical: `prove_nose_off.py` against 2ce9495 on the corrected data gives the same md5s as
  `proofs/nose_off_md5.json`, every key.
- Tests: 206 pass; the 2 failures are the guard runs that need bash 4 (the Mac has 3.2). The PC's judge tests pass.

### Phase 2 — step 3 (PC, done 2026-11-04 on f9d4b42): all five joins PASS

As above. The step is re-run on 0.20.2's built road in step 5.

### Phase 2 — step 4 (PC): Princess View's island on a scratch loop.blend

No join needs authoring. The one authored change is Princess View's island, by the tool, on a scratch copy; `lm_v4` is never
written. From a worktree of `claude/lm-phase2-build` (this push; `git lfs pull` first):

```bash
# 1. the scratch workshop: v4's project without build/, then the three corrected data files from the repo
robocopy D:/k10-scratch/lm_v4 D:/k10-scratch/lm_phase2/project /E /XD build
cp tracks/san-diego-lake-murray/data/{median_bands.json,connectors.local.json,expansion.north.json} D:/k10-scratch/lm_phase2/project/data/
# 2. the island, vertex for vertex (Blender 4.2), from v4's own median_bands (the blend was authored from it)
"C:/Program Files/Blender Foundation/Blender 4.2/blender.exe" --background --python-exit-code 1 \
  --python tools/reshape_island_blend.py -- D:/k10-scratch/lm_phase2/project --island north_princess_view \
  --old-bands D:/k10-scratch/lm_v4/data/median_bands.json --out-blend D:/k10-scratch/lm_phase2/project/loop.pv.blend \
  --report D:/k10-scratch/lm_phase2/reshape_pv.json
mv D:/k10-scratch/lm_phase2/project/loop.blend D:/k10-scratch/lm_phase2/project/loop.v4.blend
mv D:/k10-scratch/lm_phase2/project/loop.pv.blend D:/k10-scratch/lm_phase2/project/loop.blend
```

**Pass:** the report reads 592 found (worst ≤ 0.5 mm), moved CURB 78 / TERRAIN 26, stations [200, 212], largest move
1.287 m, YLINE 88 — the Mac's numbers. A refusal means `lm_v4/data/median_bands.json` is not the data the blend was
authored from: stop and report it. (The chain's sync-in does not carry median_bands.json or connectors.local.json; step 1's
copy is what puts the corrected files in the workshop.)

### Phase 2 — step 5 (PC): 0.20.2 through `ship_track.sh` on the reshaped scratch, the layouts in the config, held from install

1. **A build branch** off `claude/lm-phase2-build`, for example `claude/lm-phase2-0202`; never `claude/lm-v4-line`. The north
   lap and its two layouts go into `track.config.json` exactly as plan_north composes them: the Speedway's limits, the lap's
   own zones, the noses, smooth_window, the joins file and the island offsets. Bump the version to 0.20.2:

   ```bash
   python -c "import json,sys; sys.path.insert(0,'tracks/san-diego-lake-murray/source/expansion/phase2'); import plan_north as p
   b=json.load(open(p.PROJECT/'track.config.json',encoding='utf-8')); d=json.load(open(p.HERE/'race.north.declaration.json',encoding='utf-8'))
   c=p.compose(b,d); c['version']='0.20.2'
   open(p.PROJECT/'track.config.json','w',encoding='utf-8').write(json.dumps(c,indent=2,ensure_ascii=False)+'\n')"
   ```

2. **The run**, on step 4's scratch (no sync-back, no install; `ENG` is the repo-only engine):

   ```bash
   AIROSO=<worktree> ENG=D:/k10-scratch/eng_repro SHIP_PROJ=D:/k10-scratch/lm_phase2/project \
     bash tools/ship_track.sh san-diego-lake-murray --skip-blend --no-install 2>&1 | tee D:/k10-scratch/lm_phase2/ship.log
   ```

   The log must show:
   - `laps: north (mainline race layouts: 1)`;
   - the lap's `barrier_bands.north.json` written with 0 fails;
   - both planned verdicts PASS;
   - `verify_race --lap north`;
   - `<slug>_race_north.kn5` exported and checked (`check_race_kn5 --role common --lap north`).

**Pass when every line below holds.** Kevin reads the numbers before anything is installed.
- **Every gate (rewritten in step 2e).** The chain cannot print `SHIP OK`. 0.20.1's own rebuild (the control) ends NOT
  INSTALLED on the inherited street drive_test red: excursion drops 96, covered by Kevin's 0.20.0 force. The pass:
  - the chain runs every step to its `GATES:` line, and every hard gate before it passes;
  - that line reads `street drive_test exit 1` and every other exit 0;
  - `race layouts red on their own gates: none`, and the Drive-1 road gates exit 0;
  - it ends on `NOT INSTALLED (Kevin never loads a build the machine failed)` for that one key, with street drive_test's
    keys equal to 0.20.1's (excursion drops 96).

  Any other red fails the step. `--force-install` is used only on Kevin's word, at install. This includes **the house
  gate**: roofs 7,600, blocks 7,600, colliders 275 (`data/house_gate.json`).
- **Princess View's island on the built road** (step 3b's read, on `lm_phase2/project/data/track.obj`): the 1KERB ring at v538
  stands at about [−3.44, +1.75], and the right face reads −3.45..−3.38 over v535-v556, with no jog.
- **Built containment at all 34 exits**, in both north layouts:
  - `data/no_route.north_cw.json` and `north_acw.json`: fail false, leak 0, `forbidden_reached` empty, `blocked` empty;
  - the six pad-arm probes are sealed by the Speedway's own furniture, not by the Free Roam end barriers alone (Waring SW at
    J2 and Mission Gorge W at J3 above all);
  - the five K-rails per layout stand in the built OBJ: verify_race C' / J (`data/race_verify.north.json`, `nose_pins`
    `far_line_m` and `closure_face_m` ≤ 0.05).
- **Every spawn reachable:** `spawns_unreached` empty on both; `layout_dummies` and spawn clearance (verify_race F) clean.
- **The existing layouts and Free Roam, against 0.20.1.**
  - street / race_cw / race_acw `drive_test`, `audit_mesh`, `kn5_ground_check`, built `no_route`, `verify_mouths`,
    `verify_stubs`, `verify_pads`, `rib_check`, `house_seat`, `verify_fold_fans`, `verify_ai_line`: every key equal to
    0.20.1's committed files.
  - A key that is not equal is listed with its 0.20.1 and 0.20.2 values and must sit at Princess View's island (lap v530-v545,
    Free Roam's north lines). Any other difference fails.
- **The kn5s.** `python tools/kn5_equiv.py <0.20.1 kn5> <0.20.2 kn5>` must read equivalent (tangent floats within 1e-6) for
  `_race`, `_street`, `_closure_race_cw` and `_closure_race_acw`, and the existing three spawn kn5s must be byte-identical. The
  road kn5 is judged by SURFACE since step 2e. `--list` re-tiles the ground whenever a terrain face is added, so it cannot hold
  to the island box. `tools/kn5_surface_delta.py` decides, as in step 2e. The island's kn5-frame box is x −3001.7..−2968.3,
  z −1592.1..−1537.9 (_street's YLINE and the road's 1KERB_sidewalk piece still move only inside it). The 0.20.1 kn5s are the
  `D:/k10-scratch/lm_v4_0201` build (ledger 0065).
- **The four artifact gates on the north layouts:**
  - `drive_test --layout north_*`: the lane, barrier_missing 0, obstruction 0;
  - `audit_mesh --layout north_*`;
  - `verify_kn5` plus `--inis`: each north ini lists road + `<slug>_race_north.kn5` + its own closure + its spawns, and no
    mainline race or closure kn5;
  - `kn5_ground_check` per layout;
  - plus `verify_race --lap north` and `check_race_kn5 --lap north`.
- **The joins re-judged on the built 0.20.2 road:** `judge_joins_built.py` as in step 3, on `lm_phase2/project/data/track.obj`,
  with `--plan` a fresh plan_north out dir. All five pass, and every strip-face cast lands on 1ROAD: none on a pad curb's toe at
  the 0.03 keep.

AI: the chain writes lane-offset drafts only; the real lines are recorded in game.

**Install only on Kevin's word, after these numbers.** On that word:
- the same run against a workshop Kevin names, carrying the reshaped loop.blend and the corrected data, without `SHIP_PROJ` /
  `--no-install`;
- the config change commits to the line.

Until then nothing is installed. Kevin's drive and publishing approval remain required.

### Phase 2 — step 4/5 run (PC, 2026-11-04, on 58f8c05): the island reshaped; 0.20.2 stops at J4's inside kerb

Branch `claude/lm-phase2-0202` (worktree `D:/k10-worktrees/lm-phase2-0202`, LFS pulled); workshop
`D:/k10-scratch/lm_phase2/project` (robocopy of lm_v4 without build/, the three corrected data files from the repo). lm_v4 is
untouched. Nothing installed.

**Step 4: PASS, the Mac's numbers exactly.** `reshape_island_blend.py` (Blender 4.2) read 592 island vertices from the OLD
data, 592 found (worst 0.00 mm); moved CURB 78, TERRAIN 26, stations [200, 212], largest move 1.287 m, YLINE 88, MARKINGS 0.
loop.blend swapped (v4's kept as loop.v4.blend). Report: `D:/k10-scratch/lm_phase2/reshape_pv.json`.

**Step 5: the config composed** (plan_north.compose, version 0.20.2), then `ship_track.sh --skip-blend --no-install`
(ENG = eng_repro, SHIP_PROJ = the workshop):
- **Run 1: FAIL at the race furniture.** 785 of 12,397 north rings had no deck (> 1 %); `1KERB_race_lapnorth_1463_in`
  had none at all. Every one stands over `1ROAD_pad_J2/J3/J4` or `1ROAD_mouthfill_0/1` (probed in the blend): the author
  seated a lap on ROAD alone. Fixed in the author for lap groups (GATES-CHANGELOG 2026-11-04 WIRING); the mainline report
  is identical leaf for leaf.
- **Run 2: FAIL at verify_race I (hard), north only.** The north lap seats 12,487 hit / 0 near / 0 interpolated; the
  mainline verify passes; every other north check passes (C' / J pins 44, gap max 0.008 m; H chord max 0.080 m; F spawn
  clearance 2.48 m; G lamps and scenery clear). The one failure: **2 inside-out spans in `1KERB_race_lapnorth_1463_in`
  (spans 44, 46)**, J4's inside kerb at the apex.
  - Why: J4's refit apex is R 15.38 m (v1463) / 15.51 m (v1464) by the three-point radius (15.7 m on the ±6 m stencil),
    on a road w/2 = 14.41 / 14.31 m. The inside curb line turns on about 1.0-1.2 m. The kerb's footprint (KERB_W 1.0 + ramp
    0.10, 0.05 m off the strip's road face at w/2 − 0.82) runs from w/2 − 1.97 to w/2 − 0.87, so its inner column passes
    about 1.8 m from the corner's centre on a ~2 m polyline turning ~7.5° per vertex: two kerb stations step backwards.
  - Not authored or forced here: J4's corner (its radius floor, or a race.kerbs.trims entry for the inside kerb, as J1 /
    J5's) is the plan's call. The gate matrix, kn5s and step 5's other checks wait for a passing run.
- **Princess View's two extra checks** (on the data; the built read waits for the passing run):
  - scatter plants at lap v530-v545: 6, all `median_planting` (0.36-0.68 m), every one inside both v4's island and the
    corrected one; none on pavement or on the curb;
  - v4's own curb-ring seat (the baseline for the moved faces): base vertices sit at median −0.020 m (unmoved right
    v543-v558 −0.027..−0.019; left −0.071..+0.009).

### Phase 2 — 0.20.2 run on step 2d (PC, 2026-11-04, 34c9f53 merged into `claude/lm-phase2-0202`): not shippable yet

Same workshop (step 4 stands); config re-composed from the base (J4's trim in); plan_north PLANNED / exit 0 from a clean
tree (in the composed worktree it reads each north layout twice: "closure_token 'ncw' is also north_cw's").

**The chain** (`D:/k10-scratch/lm_phase2/ship_2d.log`): the race furniture authors clean (author-time and verify I both 0;
1463_in over v1457-1462), every export, verify_kn5 + --inis, verify_ai_line, the track folder, maps and TreeFX pass. It
stops at the scenery gate: **sign `M3-fwd@north_cw` stands in north_cw's lane at lap v0 (lat +4.88)**. The W1-6 step gives
every race layout the mainline's layout plates (M3 / M4, fwd and rev) — race_cw's J1 plate spot lies in the north lap's
lane. The remaining gates were run by hand on the scratch (the chain's commands; `gates_2d.log`), information only:

| Gate | Existing layouts (street / race_cw / race_acw) | North layouts |
|---|---|---|
| verify_mouths / stubs / pads, rib_check, house_seat, house gate (7,600 / 7,600 / 275) | pass | — |
| drive_test | every key equal to 0.20.1 (street FAIL on excursion drops, inherited: 0 of 193 keys differ) | north_acw PASS (severe 15, not failing); north_cw FAIL: obstruction 9 = the M3 sign; severe 9, worst 0.17 m at s 4375-4378 lat −3.2 (v1478-1479: a 2 m 1KERB_sidewalk_0 piece of v4's in the lane) |
| audit_mesh | CLEAN, counts only differ (curb −5, grass −19 verts) | D 14,106 / I-K 2,007: audit_mesh reads the mainline's barrier_bands.json for a layout's exemptions (no lap support) |
| built no_route | every key equal | FAIL both: a "door" at J3 v694-699 L. The edge wall stands there (1.2 m) on the pad deck 0.21-0.27 m below the centreline; no_route's band [cl + 0.30, cl + 1.00] misses its top by 3-7 cm (the deck reference is the centreline, not the local deck) |
| verify_fold_fans | keys equal | written correctly ("not on lap north"); the tool then crashes printing a record without `rows` |
| kn5_ground_check | pass, keys equal | pass |
| drive_test --line expansion | fwd steps/km 0.32 → 0.48 | — |

**The kn5s against 0.20.1** (`lm_v4_0201`): `_race`, `_closure_race_cw`, `_closure_race_acw` equivalent; the three spawn
kn5s byte-identical; `_street` differs at YLINE_0 only, every moved corner in the island box. The road kn5 `--list` names
25 meshes: 1KERB_sidewalk_0 (all 311 moved corners in the island box) — and terrain / rock / building meshes elsewhere:
16 of 20 1GRASS tiles re-tessellated (the prep's pre-thin vertex counts differ, terrain_thin.json), mostly within 60 m of
the north lap; ~250 triangles near the mainline > 1 km from it (1GRASS_0 / 8 / 9 / 10 / 11); 1GRASS_ROCK_6 up to 4.9 m
36-43 m from the lap; five building meshes ≤ 0.2 mm, three houses 1-6 mm (house_seat rows 1932 / 2628 / 6079, 32-50 m from
the lap). **A control** (the same tools at 34c9f53, v4's blend and data, no north layouts; `D:/k10-scratch/lm_phase2/control`)
gives every kn5 equivalent to 0.20.1, the road included: the changes are 0.20.2's inputs, not drift. The control is NOT
INSTALLED by the chain on the inherited street drive_test red alone: 0.20.2 cannot print SHIP OK without --force-install.

**Princess View on the built road:** the ring at v538 [−3.43, +1.75]; the right face −3.43..−3.45 at v535-v542, then the
uncorrected run (−3.61 at v543; the largest step 0.16 m, v542 → v543). The moved faces' seat: median −0.017 m against
v4's −0.020 (unmoved −0.022 / −0.020); v534 +0.026 (v4 +0.031 there) and v535 +0.007 outside ±2 cm. TreeFX: 6 plants
(Bush / Sage) at v530-v545, all inside the built ring (≥ 1.80 m from the moved face); the written trees.txt is identical
to 0.20.1's (21,111). **Joins on the built road:** all five PASS; strip faces 0 / 524 on a curb (worst +0.011 J2,
+0.017 J3, +0.021 J4).

### Phase 2 — 0.20.2 run on step 2f (PC, 2026-11-04, d1dbe5b merged into `claude/lm-phase2-0202`): two rows left

2e's rebuild was stopped for 2f (its first try had stopped at verify_race G on the workshop's stale signs.local.json:
verify_race reads the file before the sign step rewrites it, so a re-used workshop carries the last run's plates — v4's
29-sign file was restored first). Workshop as before; loop.v4.blend = lm_v4's (sha256 0656308e…).

- **Step 4 again (curb only):** 592 found (0.00 mm); CURB 78, **TERRAIN 0**, YLINE 88; stations [200, 212]; 1.287 m;
  deck "kept". plan_north from the line's config: PLANNED / exit 0; compose once (0.20.2).
- **The chain** (`ship_2f.log`) reaches its GATES line: street drive_test exit 1, street audit 0, race drive_test 0,
  **race audit exit 1**, race no_route 0, kn5_ground_check 0; NOT INSTALLED. The prep prints v4's numbers (terrain conform
  80,161 / 177,586 / 49,992 / 125,428; split 1GRASS 817,802 -> 16 tiles). Signs 29 posts / 29 plates (4 mainline layout
  plates, none @north). verify_fold_fans prints the north skips and passes.
- **race audit exit 1 = audit_mesh north_cw / north_acw D 32 each** (I / K 0; the lap islands line printed). All 32 are
  verts of the lap's own `1WALL_race_edge_lapnorth_L_navajo_2130_1` at J1: x −1980.7..−1962.3, z 589.6..593.4, ~14 m off
  lap v2931, bases at the road ±0.07 m, tops +1.15 m — the lap's left edge wall where its band does not cover it.
- **The road kn5 against 0.20.1 (`--list`): 6 meshes** — 1KERB_sidewalk_0 (the island, ≤ 3.9 m from the lap) and
  1GRASS_1 / 2 / 4 / 13 / 15 (triangles in / out within 4.8-27.3 m of the lap: J1 / J5 on Navajo, J2, J4); no far tile, no
  rock, no building. `_street`: YLINE_0, every moved corner in the island box. `_race` and both closures equivalent; the
  three spawns byte-identical. Prepped tiles (proofs/prep_tile_dump + cmp vs 0.20.1's prepped blend): 28 / 28, the same
  names, 0 faces differing inside the island box, 574 outside in 1GRASS_1 / 2 / 4 / 13 / 15 (sampled 6.6-26.8 m from the lap).
- **Existing layouts against 0.20.1:** drive_test street / race_cw / race_acw, kn5_ground_check x3, verify_mouths / stubs /
  pads, house gate (7,600 / 7,600 / 275) and **house_seat: every key equal** (the three houses back). audit and rib_check:
  counts only (curb −5, grass +3, F side −2; terrain_vertices +3). **Built no_route race_cw / race_acw: pass, but
  `local_deck_cells` 166 each, wall_cells +166, reached_m2 and allowed_m2 −2** — the cells at mainline v760-779 (6),
  v1060-1089 (88), v1510-1519 (16), v2320-2329 (56).
- **North:** built no_route PASS both (leak 0, 0 / 325 probes; local_deck_cells 4,830 / 4,831). drive_test north_cw: fail
  false, barrier_missing 0, obstruction 0, severe 5 (s 6322, 8725-8726) — **v1478-1479 clear**; north_acw: fail false,
  severe 12 (its s 15, 2419, 4348). kn5_ground_check pass.
- **drive_test --line expansion fwd 0.48 (rev 0.16): the line, not the road.** drive_lines.expansion.json is regenerated
  from the synced north data: v4 / 0.20.1 6e3db835…, both controls and 0.20.2 de1b21a2…. 0.20.2's road driven on v4's line
  reads 0.32 — the same two steps as 0.20.1 (s 2 at J1, s 949 at J2). The third (s 4342, lat +3.46, 0.045 m, at J4 ~5.5 m
  off lap v1476) exists only on the new line, where it crosses the J4 pad / Jackson ribbon seam (a smooth 3-5 % grade at
  0.25 m). Not at Princess View. (0.20.1's committed drive_test.expansion.json was last written at b79dafe, v0.19.0.)
- **Joins on the built road:** all five PASS; strip faces 0 / 524 on a curb (worst +0.011 / +0.017 / +0.021).
- **Princess View:** the ring at v538 [−3.43, +1.75] (−3.43..−3.45 v535-v542); the moved faces' seat median −0.017 m (v4
  −0.020; v534 +0.026 where v4 had +0.031, v535 +0.007); TreeFX trees.txt identical to 0.20.1's, the six plants inside
  the ring (≥ 1.80 m from the moved face).
- **kn5 MB:** road 102.4, _race 11.2, _race_north 8.8, closures race 5.3 / 5.3, north 4.5 / 4.5, _street 3.7, spawns ~0.

### Open questions for Kevin (Phase 2)

- **Princess View's wide median: closed — measured, noise, fixed at the source; no gate change** (step 2c).
- **J1 (open since P3 repair round 1):** tilt the College/Navajo crossroads to its real slope, or keep it level? The real
  slope is about 2 m down toward Waring, so Waring's first 40 m would stop riding 1.3-1.4 m over the ground at 8.8 %.
  Recommended: **keep it level for Phase 2**, and take the tilt with 0055's College work as one change:
  - the Speedway takes J1 as a slow right turn (R 8.3 m);
  - the north drives Kevin called "incredible" were on the level crossroads;
  - a tilt moves a corner every layout drives.
- **The median noses: decided** (the K-rail at the nose, "your own side of every road"). Built as above.
- **Where the K-rail stands:** one vertex (about 3 m) before the island's tip, on pavement, or against the tip itself?
  Recommended: **one vertex before**. Where the median reaches the box edge (Waring's tail, Mission Gorge at J4), it stands on
  the box edge.
- **The station smoothing for the existing Speedways?** Recommended: **no**. Their lines are uniformly spaced, the vertex
  window does them no harm, and turning it on would move every closure by sub-millimetres for nothing.

### Phase 2 — step 2d (Mac, 2026-11-04, `claude/lm-phase2-build`): J4's inside kerb pulled back by its own geometry; the author's pre-check reads verify's record

**What the PC found.** The 0.20.2 run at 58f8c05 (branch `claude/lm-phase2-0202` at 405bae7; ledger section "step 4/5 run")
stopped twice.
- **Run 1, the seating wiring.** The author seated a lap on ROAD only, so 785 north rings over the pads and mouth fills
  had no deck. The PC fixed it in 22988c6: a lap seats on ROAD plus every other 1ROAD_* mesh, and the mainline's
  race_authored.json is identical. **Cherry-picked here as dc9575f**, with its GATES-CHANGELOG "WIRING" entry.
- **Run 2, J4's inside kerb.** verify_race I failed on 2 inside-out spans in `1KERB_race_lapnorth_1463_in` (spans 44 and
  46). The author-time column test had read 0.

**Why the pre-check read 0.** The author tested the kerb's unrounded stations. verify_race I tests the RECORD the author
writes: ring and station centres rounded to 0.01 m, frames to 5 decimals.
- At J4's refit apex (R 15.4 m at v1463, against w/2 = 14.4 m), the kerb's outer column swings round about 1.8 m from the
  corner's centre.
- Over v1463-v1464 it advances only 2-9 mm per 0.3 m station. That is positive unrounded, but within the record's rounding,
  which flips spans 44 and 46.
- Fixed: the author now counts with `race_furniture.recorded_inside_out`, the same arrays verify_race I reads. On 58f8c05's
  data it reads **2** (spans 44, 46) before the trim and **0** after.
- On the mainline it reads the same 0 as before on all 37 objects, so race_authored.json is unchanged.

**The trim, from the kerb's own geometry** (`race.kerbs.trims` in race.north.declaration.json: apex 1463, inside, i 1457,
j 1462, with its why).
- **The rule** is in `race_furniture.kerb_column_margin` / `kerb_standing_run`. A span must move both columns forward by at
  least the record's resolution, COLUMN_ADVANCE_MIN_M = 0.01 × √2 = 0.0141 m (the most two 0.01 m roundings can move a
  difference).
- **How it applies to J4.**
  - The kerb's longest run of stations that stands ends 0.3 m before v1463 (12.6 m long).
  - Rounded in to vertices it is **v1457-v1462**: 11.2 m of the detected 26.9 m, the turn-in to the apex. Its column margin
    is 0.0147 m.
  - The exit side v1465-v1469 (10.4 m) stands too, but a declared kerb is one run, so the longer side is kept.
  - J4's radius floor is not raised.
- **The check.** `plan_north.py` now checks every north kerb with this rule. A kerb that fails refuses the plan, and the
  message names the pull-back that stands. That is how the trim above was sized.
- **Where it doesn't apply.** It is the lap's check only. The mainline's 0_in kerb sits at 0.0140 m and passes verify on its
  record, and making this a mainline gate would move it.

| Kerb (north) | Run | Column advance, min | Spans under 0.0141 m |
|---|---|---|---|
| J2 326_out | v317-332 | 0.2525 m | 0 |
| J2 326_in | v317-331 | 0.0964 m | 0 |
| J3 705_out | v692-716 | 0.2846 m | 0 |
| J3 705_in | v693-710 | 0.0858 m | 0 |
| J4 1463_out | v1453-1481 | 0.2134 m | 0 |
| J4 1463_in | v1457-1462 (was v1457-1469) | 0.0147 m (was 0.0021) | 0 (was 11; the record read 2 inside-out) |
| J5 2130_out | v2122-2135 | 0.0964 m | 0 |
| J1 2932_out | v2927-v5 | 0.1646 m | 0 |

**Re-plan.**
- `plan_north.py` exits 0, **PLANNED**: every self-gate clear, 34 / 34 exits sealed both ways, planned no_route PASS both
  ways, the report carrying `kerb_column_margins`.
- No threshold moved.
- `prove_nose_off.py` against 2ce9495 gives the same md5s as `proofs/nose_off_md5.json`.
- Tests: 241 pass; the 2 failures are the bash-4 guard runs (the Mac has bash 3.2).

**The PC's re-run** (`D:/k10-worktrees/lm-phase2-0202`, or wherever claude/lm-phase2-0202 is checked out). Step 4 is not
redone: the race step replaces its own objects in the reshaped scratch loop.blend.

```bash
cd <the claude/lm-phase2-0202 worktree>
git fetch origin && git merge origin/claude/lm-phase2-build    # 22988c6 is on both sides (cherry-picked as dc9575f)
# re-compose from the line's own config (the composed one already holds the lap: compose would append the layouts twice)
git checkout origin/claude/lm-phase2-build -- tracks/san-diego-lake-murray/track.config.json
# plan BEFORE the compose (step 2e: plan_north composes onto whatever config it finds; on a composed one it read each north layout twice)
python tracks/san-diego-lake-murray/source/expansion/phase2/plan_north.py D:/k10-scratch/lm_phase2/north-plan-2d   # PLANNED, exit 0
python -c "import json,sys; sys.path.insert(0,'tracks/san-diego-lake-murray/source/expansion/phase2'); import plan_north as p
b=json.load(open(p.PROJECT/'track.config.json',encoding='utf-8')); d=json.load(open(p.HERE/'race.north.declaration.json',encoding='utf-8'))
c=p.compose(b,d); c['version']='0.20.2'
open(p.PROJECT/'track.config.json','w',encoding='utf-8').write(json.dumps(c,indent=2,ensure_ascii=False)+'\n')"
AIROSO=<this worktree> ENG=D:/k10-scratch/eng_repro SHIP_PROJ=D:/k10-scratch/lm_phase2/project \
  bash tools/ship_track.sh san-diego-lake-murray --skip-blend --no-install 2>&1 | tee D:/k10-scratch/lm_phase2/ship_2d.log
```

The merge reads clean: `git merge-tree` of this branch against 405bae7 reports no conflict. If one does appear, it can only be
where both sides appended text (the end of fleet/GATES-CHANGELOG.md, or ledger sections): keep both sides.

**Pass:** step 5's list as written above, plus:
- `author: inside-out spans (author-time column test): 0` in the log, and verify_race I 0 on the north group;
- `1KERB_race_lapnorth_1463_in` authored as v1457-v1462;
- the other seven north kerbs authored as the table says.

Install only on Kevin's word.

### Phase 2 — step 2e (Mac, 2026-11-04, `claude/lm-phase2-build`): the 0.20.2 run's eight items, each at its cause

The PC's 0.20.2 run on step 2d (`claude/lm-phase2-0202` fceccbe, section "0.20.2 run on step 2d") stopped at the scenery
gate and found seven more things by hand. Each is fixed here, or answered with the measurement that settles it. No threshold
moved. The existing Speedways are byte-identical: `prove_nose_off.py` against 2ce9495 gives the md5s in
`proofs/nose_off_md5.json` (24 keys).

1. **The layout plates on the wrong lap (the stop).**
   - **Cause.** `place_signs.race_layouts` gave every race layout driving a direction the MAINLINE corners' per_layout plates.
     So `M3-fwd@north_cw` stood at race_cw's J1 spot, which lies in north_cw's lane at lap v0 (drive_test north_cw
     obstruction 9 is the same sign).
   - **Fix.** A layout on its own lap (`layouts[].lap`) gets no mainline plate. `verify_signs.driven_directions` skips it the
     same way. The north lap gets no plates: its declaration asks for none.
   - **Proven.** On the line's config place_signs is byte-identical. On the composed config: 29 signs, plates M3 / M4
     fwd@race_cw and rev@race_acw only (it gave 33 with the four north clones).
2. **The curb in north_cw's lane past J4 (s 4375-4378, lat −3.2, v1478-1479).** It is the real curb of Jackson's median.
   - **Cause.** The median starts at lap v1478 as a 1.5 m nose 3.57 m right of the line, and stands 2.6-3.6 m off the line
     through v1489. The lap's island snap (2.5 m) dropped those points, so the lap had no island at v1478-1489. The Jackson
     nose was declared at v1490, and the corridor gave north_cw the whole street over the curb.
   - **Fix.** median_bands' offset_aware islands carry one point per connector vertex. `race_lap.offset_islands` now reads
     them by index, however far off the line they stand; snap_m stays for every other island.
   - **The nose.** It moves to the real start: median v1478, pin and K-rail v1477, 15 m after the J4 box.
   - **North_cw's lane at v1478** is now [−12.60, −4.64]: its face is 0.32 m outside the island's −4.32 face, and the strip
     stands at −4.30.
   - **Side effects.** The J4 outside kerb is clipped to v1453-1476, short of the K-rail. The island runs are unbroken at
     Princess View (v531-559) and Jackson (v1478-1506). Mainline: no lap, no change.
3. **no_route's door at J3 (v694-699 L).** A MEASUREMENT-BUG FIX (GATES-CHANGELOG): built no_route also measures each wall
   triangle from the 1ROAD deck under it, and a cell seals in either frame.
   - The 1.2 m edge wall on the J3 pad (0.21-0.27 m below the line) spans [0, 1.2] above its own deck.
   - Every centreline-frame wall stays a wall, so nothing that sealed can open. `local_deck_cells` counts what the deck frame
     adds: 0 means every other key reads as before.
   - The wall is not made taller.
4. **audit_mesh on the north layouts (D 14,106 / I-K 2,007).**
   - **Cause.** It did zone a north layout on its lap: barrier_bands.north.json, the lap's islands and the connectors'
     islands, since b8705a0. What it lacked were the mainline's own medians. A lap's gate OBJ is the whole road kn5, so every
     mainline island curb, nose and post read as D / K / I.
   - **Fix.** `MedianZone.road_islands` adds them for a layout on a lap, island kind only, as a race layout meets them.
     Mainline audits take no new branch.
5. **verify_fold_fans' KeyError 'rows'.** The record was right ("not on lap north"). The printer read `rows` off a
   `skipped` record, and now prints the skip instead. The written record is unchanged.
6. **The road kn5's drift outside the island: the island reshape, not the north layouts.** The PC's island-only control
   (`D:/k10-scratch/lm_phase2/control_island`: tools at 34c9f53, no north layouts, the reshape on a fresh v4 blend) gives the
   same 25 meshes and fwd steps/km 0.48.
   - **The mechanism, measured on the Mac.** v4's loop.blend against the reshaped one (`loop_pv.blend`): the reshape moves
     24 TERRAIN vertices, up to 1.28 m, all inside x −2993.7..−2976.2, y 1552.3..1582.7 (Blender frame).
     - Four of the 38 edges they touch, the island top's cross edges, grow past the prep's CORRIDOR_EDGE_M 4.5 m: 3.69 → 4.57,
       3.30 → 4.56, 3.88 → 4.61 and 3.70 → 4.59 m. The prep's corridor subdivision halves each of them once
       (`build_kn5_loop._conform_and_reseat`, 3D length, within FEATHER_M + 10 of a road vertex), adding faces in the island.
     - `_split_large` tiles 1GRASS by MEDIAN bisection of every face centre (`balanced_face_tiles`), so a handful of faces more
       moves every later cut across the map. 16 of 20 tiles hold different faces, and ~250 triangles change tile at the cuts
       near the mainline > 1 km away.
     - `tools/thin_terrain_blend.py` then thins each tile with its seams locked, so a re-cut tile thins to a different
       triangulation. The vertex counts differ (terrain_thin.json), and a rock tile cut from a different ground tile
       "moves" metres.
     - Not ground_release jitter: the first control, with no reshape, is equivalent everywhere.
   - **What the surface may do outside the island.** The pre-thin surface outside the island is the same: a split is
     inserted on a straight edge, and the cuts only regroup faces. The thinned surface each run stays within
     terrain_thin's own bounds of it: ±5 mm within 6 m of a pavement, ±3 cm to 22 m, ±10 cm beyond, ±15 cm past 60 m. So two
     runs can differ by up to twice those, and by most where the far tiers thin hardest. That is now measured, not assumed:
     `tools/kn5_surface_delta.py` (new) differences two kn5s' 1GRASS* ground on a plan grid, per tile, for the rock, and by
     distance to the lap.
   - **The rule.**
     - Outside the island's band, mm near the pavement (≤ 1 cm within 6 m, where every drive gate reads) is
       "surface-equal outside the island", recorded with the numbers.
     - A far-field difference above that is the re-thinning, not a moved ground. It is still a moved surface, so it comes back
       to the Mac with the per-tile table. The island-local cure is then to keep the reshape's island-top edges on the same
       side of CORRIDOR_EDGE_M, i.e. the same face count, so the cuts never move. That cure is not built until the numbers ask
       for it.
   - **The north layouts' own six meshes (control_island → 0.20.2)** sit at three of the lap's junctions:
     - 1GRASS_2 at x −2757..−2717, kn5 z −1133..−884 holds lap v300-345: the J2 box v316-333 and the 326 kerbs v317-332;
     - 1GRASS_13 at x −1427..−1096, z −3194..−3165 holds v1417-1487: the J4 box v1452-1472 and the 1463 kerbs;
     - 1GRASS_3 is at J1 (the 2932_out kerb);
     - 1GRASS_1 / 4 / 15 change by a handful of triangles: the thinning of the faces regrouped there.

     The prep's conform reads every `1KERB*` mesh, the race kerbs included (as it has read the mainline's since 0047):
     - the anti-poke clamp under the lowest drivable sheet;
     - the bury-cull;
     - the re-seat ground.

     It reads no `1WALL`. So the lap's furniture moves ground only under its own kerbs, inside the lap's band at J1, J2 and
     J4. That is ground seating, not leakage. The surface table confirms it: the differences sit within the lap's band at
     those three boxes.
   - **The expansion line's new steps (0.32 → 0.48 fwd, the island too).** drive_test `--line` now writes `steps_at`
     [s, lateral, step, x, z] (engine frame) per line (reported, not gated; a lap run's report is unchanged), so the run
     places them.
     - At Princess View, a step at the moved curb face is the real island: a fixed-offset path grazing the curb that now
       stands where NAIP puts it.
     - A step on the island top or at the curb's toe would be a seat defect at the moved faces. Bring that back to fix.
     - Anywhere else, trace it.
   - **house_seat's three houses (1-6 mm, 32-50 m from the lap)** are the same re-thinning, within the 3 cm near-road bound.
7. **The pass list** of step 5 is rewritten (above): the chain stops on the inherited street drive_test red alone, and
   installing needs `--force-install` on Kevin's word.
8. **Command order.** plan_north composes the declaration onto whatever config it finds. The runbooks now plan before the
   compose (step 2d's block corrected). `plan_north.compose` is idempotent too: it replaces the lap's layouts, so a composed
   tree plans the same lap.

**Re-plan.**
- plan_north PLANNED, exit 0: every self-gate clear, 34 / 34 exits sealed both ways, planned no_route PASS both ways
  (north_cw reached 88,417 m², north_acw 91,688 m²). The kerb margins are unchanged (1463_in 0.0147 m); 1463_out runs
  v1453-1476.
- Pictures redrawn.
- Tests: tests/tools + tests/geometry, 874 pass. The failures:
  - four `test_ship_track_chain` guard runs, which are the Mac's environment (`python: command not found` under bash 3.2);
  - `test_ship_fleet` (the rally tarmac pair's skip), which is not this branch's.
- test_author_expansion's byte-for-byte check, broken since step 2c, is mended. The author builds exactly the BEFORE values that
  fix_pv_median.py recorded for MD7's corrected rows, and the committed file holds the AFTER values. Everything else is still
  byte for byte.

**The PC's re-run** (in the claude/lm-phase2-0202 worktree; step 4 stands; the race step replaces its own objects in the
reshaped scratch loop.blend; nothing installed). `L201` is the 0.20.1 road kn5 (`D:/k10-scratch/lm_v4_0201`'s
`build/san_diego_lake_murray.kn5`, or wherever 0.20.1's road kn5 lies).

```bash
cd <the claude/lm-phase2-0202 worktree>
git fetch origin && git merge origin/claude/lm-phase2-build
git checkout origin/claude/lm-phase2-build -- tracks/san-diego-lake-murray/track.config.json   # the line's own config
python tracks/san-diego-lake-murray/source/expansion/phase2/plan_north.py D:/k10-scratch/lm_phase2/north-plan-2e   # PLANNED, exit 0
python -c "import json,sys; sys.path.insert(0,'tracks/san-diego-lake-murray/source/expansion/phase2'); import plan_north as p
b=json.load(open(p.PROJECT/'track.config.json',encoding='utf-8')); d=json.load(open(p.HERE/'race.north.declaration.json',encoding='utf-8'))
c=p.compose(b,d); c['version']='0.20.2'
open(p.PROJECT/'track.config.json','w',encoding='utf-8').write(json.dumps(c,indent=2,ensure_ascii=False)+'\n')"
# 1. the surface, before the rebuild: the island alone, against 0.20.1 (the spread) — 2 m grid (~10-15 min each), by
#    distance to the lap, and everything outside the island's kn5-frame box on its own; then the island box at 0.25 m
LAP=D:/k10-scratch/lm_phase2/north-plan-2e/data/lap.north.json; ISL=-3001.7,-1592.1,-2968.3,-1537.9
python tools/kn5_surface_delta.py "$L201" D:/k10-scratch/lm_phase2/control_island/build/san_diego_lake_murray.kn5 \
  --line "$LAP" --exclude "$ISL" --json D:/k10-scratch/lm_phase2/surface_island_vs_0201.json
python tools/kn5_surface_delta.py "$L201" D:/k10-scratch/lm_phase2/control_island/build/san_diego_lake_murray.kn5 \
  --box "$ISL" --step 0.25 --json D:/k10-scratch/lm_phase2/surface_island_box.json
# 2. the rebuild
AIROSO=<this worktree> ENG=D:/k10-scratch/eng_repro SHIP_PROJ=D:/k10-scratch/lm_phase2/project \
  bash tools/ship_track.sh san-diego-lake-murray --skip-blend --no-install 2>&1 | tee D:/k10-scratch/lm_phase2/ship_2e.log
# 3. what the north layouts add on top of the island (their own ground), and the whole of 0.20.2 against 0.20.1
python tools/kn5_surface_delta.py D:/k10-scratch/lm_phase2/control_island/build/san_diego_lake_murray.kn5 \
  D:/k10-scratch/lm_phase2/project/build/san_diego_lake_murray.kn5 --line "$LAP" --exclude "$ISL" --json D:/k10-scratch/lm_phase2/surface_0202_vs_island.json
python tools/kn5_surface_delta.py "$L201" D:/k10-scratch/lm_phase2/project/build/san_diego_lake_murray.kn5 \
  --line "$LAP" --exclude "$ISL" --json D:/k10-scratch/lm_phase2/surface_0202_vs_0201.json
# 4. where the expansion line's bumps stand (written by the chain's drive_test --line expansion)
python -c "import json; [print(k, r) for k in ('fwd','rev') for r in json.load(open('D:/k10-scratch/lm_phase2/project/data/drive_test.line.expansion_'+k+'.json'))['steps_at']]"
```

**Pass when:**
- **The chain.** It runs to its `GATES:` line under step 5's rewritten pass: the street drive_test red alone, NOT INSTALLED
  on it. Along the way:
  - the scenery gate passes, with no `@north_*` plate in `data/signs.local.json`;
  - verify_fold_fans prints its north skips and exits on its verdict;
  - `drive_test --line expansion` passes (it is hard).
- **north_cw drive_test.** obstruction 0, barrier_missing 0, and no severe step at s 4375-4378 (v1478-1479).
- **Built no_route, north_cw and north_acw.** fail false, leak 0, no forbidden probe reached, nothing blocked, J3 v688-703
  sealed, with `local_deck_cells` > 0 and recorded.
- **Built no_route, race_cw and race_acw.** Every key equals 0.20.1's, with `local_deck_cells` recorded. If it is not 0,
  list its cells; they must be walls on a deck below the line, and every other key still equal.
- **audit_mesh.**
  - `--layout north_*` prints "lap layout north_*: + the road kn5's own islands". The counts that remain are listed by
    check with their worst places; they must be the lap's own furniture or 0.
  - street / race_cw / race_acw are CLEAN and equal to 0.20.1.
- **The surface.**
  - `surface_island_vs_0201`: `outside_exclude`, `by_distance_to_line` and `by_tile_a` hold the numbers to record (`surface_island_box` the island itself).
    Within 20 m of the lap (the pavement band), max |d| ≤ 0.01 m away from Princess View's v520-v560. The far tiers are
    recorded as they are, and anything over 0.01 m within 60 m of any pavement comes back with its tile and box.
  - `surface_0202_vs_island`: every point over 1 mm lies within 20 m of the lap at J1, J2 or J4 (the kerbs' seating).
  - The rock: `rock` max |d| recorded, and any point over 0.05 m listed.
- **The expansion steps.** Every `steps_at` entry of the new ones stands at Princess View (the island box x −3001.7..−2968.3, z 1537.9..1592.1 in the engine
  frame, v530-v545 of the lap) at the moved curb face. Otherwise it is listed and traced.
- **Everything else** as step 5 (the house gate 7,600 / 7,600 / 275; the joins re-judged; kn5s `_race`, `_street` (YLINE in
  the island box only), the closures and spawns as before).

Install only on Kevin's word.

### Phase 2 — step 2f (Mac, 2026-11-04, `claude/lm-phase2-build`): the island reshape leaves the prep's terrain as v4 had it

**Why the ground moved** (step 2e, item 6). Step 4's reshape moved the island's curb (CURB, 78 vertices) and its deck
(TERRAIN, 26 vertices). The deck is terrain, and the prep reads it.
- **The deck sits under the road slab.** Measured on v4's prepped scene at all 28 Princess View deck vertices, the grass
  stands 0.020 m under the road. The prep pins every deck vertex to the road − 0.02, so the island's visible top is the
  slab whatever the deck's width.
- **The moved deck.** Four of its cross edges grew past CORRIDOR_EDGE_M (3.30-3.88 → 4.56-4.61 m), and its face centres
  moved by up to 1.3 m. The prep halves terrain edges longer than 4.5 m near a road, and tiles 1GRASS by MEDIAN bisection of
  every face centre. So one face more, or one centre across a cut, moves every later cut, and the per-tile thinning re-meshes
  ground kilometres away.

**The cure.** `tools/reshape_island_blend.py` now moves the CURB (and the paint) and leaves the deck exactly as v4 authored
it (`island_reshape.moves(move_deck=False)`; `--move-deck` restores step 4's behaviour). Nothing visible changes:
- The deck is pinned under the slab, and the curb, the yellow edge lines and the TreeFX ring are what you see.
- At v207-208 and v211 the deck's left edge stands 0.23-0.27 m outside the new curb base, under the carriageway, pinned
  0.02 m under it. That is ground under pavement, which no gate reads as on top.

A first cure tried a narrower deck, which kept the four edges under 4.5 m. It held the corridor split (80,161 edges, v4's
count) but still moved four tiles (1GRASS_4-7, 2,036 faces outside the island, tile 6 −8 vertices). The narrowed deck's face
centres crossed a bisection cut. Keeping the deck removes both mechanisms.

**Proven on the Mac** (Blender 5.1.2, the engine-july snapshot's `build_kn5_loop.py` run whole on scratch copies of the
project; v4's loop.blend is LFS 0656308e):

| Prep run | Corridor edges split | 1GRASS verts before the split | Terrain tiles | Faces differing from v4 (outside / inside the island box) |
|---|---|---|---|---|
| v4, run twice | 80,161 / 80,161 | 817,802 | 20 / 20 | 0 / 0 (the prep is deterministic) |
| step 4's reshape (deck moved) | 80,165 | 817,806 | 20 | **4,278** / 98, in all 16 1GRASS tiles: the 0.20.2 spread, reproduced |
| deck narrowed under 4.5 m | 80,161 | 817,802 | 20 | 2,036 / 82, in 1GRASS_4-7 |
| **deck kept (this cure)** | 80,161 | 817,802 | 20 | **0** / 0 |

With the deck kept, every terrain face of the prepped scene equals v4's to 0.1 mm, inside the island box too. The moved
curb changes no ground there: the prep's anti-poke already held the ground 0.02 m under the slab. The same holds after
`tools/thin_terrain_blend.py`: 983,287 → 541,820 vertices in both, and 1,060,989 thinned faces identical, tile for tile.
So with the island alone, the road kn5's 1GRASS / rock tiles stay 0.20.1's, and only the curb (1KERB_sidewalk) and the
paint (`_street`'s YLINE) change, inside the island box. Proof record: `proofs/island_prep_2f_mac.json`. The tools are
`proofs/prep_tile_dump.py` and `proofs/prep_tile_cmp.py`; the PC can run the same on its prepped
`blender/san_diego_lake_murray.blend` against 0.20.1's.

**Blend digest, v4 → the cured reshape:** 145 objects in both, the same set; only CURB and YLINE differ, in positions only
(the topology, UVs, materials and transforms are equal); TERRAIN is identical, byte for byte. The island deck's longest edge
is 5.417 m, v4's own (5 deck edges over 4.5 m on v4, the same 5 now). Report: `proofs/reshape_pv_2f_mac.json`
(592 found, 0.00 mm; CURB 78, TERRAIN 0; stations 200-212; largest move 1.287 m; YLINE 88).

**The PC's re-run.** Step 4 is redone from v4's blend, followed by the rebuild. Run it in the claude/lm-phase2-0202
worktree. Nothing is installed.

```bash
cd <the claude/lm-phase2-0202 worktree>
git fetch origin && git merge origin/claude/lm-phase2-build
# step 4 again, from v4's own blend (the workshop kept it as loop.v4.blend; it must be lm_v4's loop.blend byte for byte)
certutil -hashfile D:/k10-scratch/lm_phase2/project/loop.v4.blend SHA256      # = certutil of D:/k10-scratch/lm_v4/loop.blend
"C:/Program Files/Blender Foundation/Blender 4.2/blender.exe" --background --python-exit-code 1 \
  --python tools/reshape_island_blend.py -- D:/k10-scratch/lm_phase2/project --island north_princess_view \
  --old-bands D:/k10-scratch/lm_v4/data/median_bands.json --blend D:/k10-scratch/lm_phase2/project/loop.v4.blend \
  --out-blend D:/k10-scratch/lm_phase2/project/loop.pv2f.blend --report D:/k10-scratch/lm_phase2/reshape_pv_2f.json
mv D:/k10-scratch/lm_phase2/project/loop.pv2f.blend D:/k10-scratch/lm_phase2/project/loop.blend
# the config, the plan before the compose (as step 2e)
git checkout origin/claude/lm-phase2-build -- tracks/san-diego-lake-murray/track.config.json
python tracks/san-diego-lake-murray/source/expansion/phase2/plan_north.py D:/k10-scratch/lm_phase2/north-plan-2f   # PLANNED
python -c "import json,sys; sys.path.insert(0,'tracks/san-diego-lake-murray/source/expansion/phase2'); import plan_north as p
b=json.load(open(p.PROJECT/'track.config.json',encoding='utf-8')); d=json.load(open(p.HERE/'race.north.declaration.json',encoding='utf-8'))
c=p.compose(b,d); c['version']='0.20.2'
open(p.PROJECT/'track.config.json','w',encoding='utf-8').write(json.dumps(c,indent=2,ensure_ascii=False)+'\n')"
AIROSO=<this worktree> ENG=D:/k10-scratch/eng_repro SHIP_PROJ=D:/k10-scratch/lm_phase2/project \
  bash tools/ship_track.sh san-diego-lake-murray --skip-blend --no-install 2>&1 | tee D:/k10-scratch/lm_phase2/ship_2f.log
python tools/kn5_equiv.py "$L201" D:/k10-scratch/lm_phase2/project/build/san_diego_lake_murray.kn5 --list
```

**Pass**, on top of step 2e's list:
- **The reshape report** reads 592 found (worst ≤ 0.5 mm), moved CURB 78 / TERRAIN 0, stations [200, 212], largest move
  1.287 m, YLINE 88, deck "kept".
- **The prep** prints v4's numbers in `terrain conform` and `split 1GRASS`. 0.20.1's log has them.
- **The road kn5 `--list` against 0.20.1** names only:
  - meshes whose box lies inside the island's kn5-frame box x −3001.7..−2968.3, z −1592.1..−1537.9;
  - the north lap's own kerb seating at J2, J1 and J4 (1GRASS_2 / 3 / 13);
  - 1GRASS_1 / 4 / 15's handful of triangles, as the island-only control against 0.20.2 named them, each moved box
    within 60 m of the lap.

  No tile far from both. `kn5_surface_delta` is then recorded as in step 2e, and outside the island box and the lap's band it
  must read 0.
- **drive_test `--line expansion`:** fwd steps/km back to 0.32 (rev 0.16), or every new `steps_at` entry inside the island
  box at the moved curb face. The ground is v4's now, so the curb is the only thing there that moved.
- **house_seat:** the three houses back to 0.20.1's rows.
- **Everything else as step 2e.**

Install only on Kevin's word.

### Phase 2 — step 2g (Mac, 2026-11-04, `claude/lm-phase2-build`): the 0.20.2-on-2f run's four rows

The PC's run on d1dbe5b (`claude/lm-phase2-0202` 2d7cf23, section "0.20.2 run on step 2f") left four rows. Each is
answered at its cause; no threshold moved. plan_north is PLANNED with its report equal to step 2e's (timings aside), and
`prove_nose_off` matches `proofs/nose_off_md5.json` (24 keys).

1. **audit_mesh north D 32: the zone, not the wall.** `1WALL_race_edge_lapnorth_L_navajo_2130_1` stands where the lap's
   bands put it. It is the lap's left edge on the offset curve round the outside of J1: R 8.3 m at v2932, a 30 m box,
   band points 11-13 m apart.
   - **Cause.** `median_zone` joined consecutive band points with the straight chord. The strip follows the curve
     (`race_furniture.densify_rings`), which bows ~1 m off the chord there.
   - **Fix.** The band is that curve too, at the same reach. Before, 7 ring points of the lap's 17,793 sat outside the band
     per layout, all on navajo_2130_1 at v2930-2931 (x −1980.65..−1962.30, z 589.57..593.38, the PC's box). Now 0.
   - Only audit_mesh's D reads barrier bands, and the change only adds exemption: the mainline's D stays 0.
2. **no_route race_cw / race_acw `local_deck_cells` 166: 104 of them were another road.**
   - **Reproduced on the Mac** on v4's own prepped scene (a gate OBJ exported from it): 163 cells. 104 of them were
     `1WALL_guard_0`, the median guardrail, measured from decks −3.79..+7.15 m off the line's: the I-8 under the bridge, an
     overpass. Step 2e's deck frame took the 1ROAD sheet nearest a wall's foot, whatever road it was.
   - **Fix.** Only sheets within DECK_REACH_M = WALL_HI_M − WALL_LO_M = 0.70 m of the line's deck count (derived: within it,
     the two bands overlap). The report now lists what the deck frame sealed (`local_deck_walls`).
   - **What remains** (Mac, race_cw): 59 cells, all mainline race curb strips standing on decks below the line. They are
     `college_774` (v763-776, −0.13..+0.01 m), `navajo_1517` (J1 mouth, v2314-2323, ±0.24 m) and `jackson_2324` (J5 mouth,
     v2324-2327, −0.24..−0.14 m). These are real walls, so the key change is the measurement fix doing its job: wall_cells
     594,840 → 594,899, reached / allowed 138,758 → 138,757 m², every verdict key equal. Recorded in GATES-CHANGELOG.
   - Step 5's pass now expects it: built race_cw / race_acw keys equal to 0.20.1's except wall_cells (+ local_deck_cells)
     and reached_m2 / allowed_m2 (≤ a few m² down), with every `local_deck_walls` object a `1WALL_race_*` on a deck within
     ±0.70 m.
3. **The expansion line: right as regenerated, and J4 is fine.** Reproduced on the Mac on v4's own road, driven on both
   lines: v4's line reads fwd 0.32 (s 2, s 949), the regenerated one 0.48 (+ s 4342, 0.0452 at (−1192.680, 3152.387)).
   - **The diff.** The regenerated line (`tools/expansion_lines.py` on the corrected data, de1b21a2…) differs from v4's
     (6e3db835…) only at Princess View: fwd points 520-540 (s 1556-1616, up to 0.21 m, widths up to 0.48 m), rev
     1574-1590 (≤ 1 mm). That is where the median data changed. Everywhere else the points and widths are equal, and the
     stations after Princess View shift 7.6 mm (the line is that much shorter there).
   - **The J4 step is a sampling artefact.** The +3.46 m wheel path hops across line vertex 1450: that metre covers 0.497 m
     of plan. drive_test re-measures such a hop on the path's own travel (VERTEX BUMPS): v4's line reads 0.02486 m, filed
     as a vertex bump and not counted; the new one 0.02546 m, over STEP_BUMP_M 0.025, counted. The difference is the 7.6 mm
     station shift.
   - **The surface there is smooth.** `proofs/probe_seam.py` walks that path every 2 mm over ±1.2 m, ±3 cm across. The J4
     pad / Jackson ribbon seam is continuous: 1ROAD_pad_J4 → 1ROAD_road at dh 0.1 mm, no gap, no jump over 5 mm. The real
     grade change there is ~1.9 %-points on the path's own travel.
   - **Nothing shipped reads the file.** Only drive_test --line reads it; place_signs / verify_signs recompute the lines in
     memory (signs 29 / 29 as 0.20.1), and no AI draft or verify_ai_line uses it.
   - `steps_at` now carries mm precision.
   - (0.20.1's committed `data/drive_test.expansion.json` was last written at b79dafe, v0.19.0: not a 0.20.1 reading.)
4. **Stale signs in a re-used workshop: the chain order.**
   - `ship.json` steps.author is now … race_author, **signs, race_verify**, and `tools/ship_sd.sh` is moved the same way.
   - `tools/ship_track.sh` refuses a ship.json that lists race_verify before signs.
   - The signs step already unlinks the last run's `signs.local.json` at its start, so verify now reads this run's plates.

Tests:
- test_median_zone_kinds (the J1 curve), test_no_route (the listed pad wall; a wall on another road's deck seals nothing),
  test_drive_test_line and the ship chain suites pass, apart from the four bash-4 guard runs that fail on the Mac.
- The full tools + geometry run: 877 pass. The 5 failures are the four bash-4 guard runs and `test_ship_fleet` (the rally tarmac pair; not this branch's).

**The PC's re-run: gate re-runs only, on the existing 2f build** (`D:/k10-scratch/lm_phase2/project`; no rebuild: neither
the race step nor the blend changes). In the claude/lm-phase2-0202 worktree, merged with this push:

```bash
cd <the claude/lm-phase2-0202 worktree>
git fetch origin && git merge origin/claude/lm-phase2-build
P=D:/k10-scratch/lm_phase2/project
# 1. audit_mesh, every layout (the gate OBJs the chain wrote are still there)
python -m scripts.geometry.audit_mesh "$P"                         # street: CLEAN, equal to 0.20.1
for lid in race_cw race_acw north_cw north_acw; do python -m scripts.geometry.audit_mesh "$P" --layout "$lid" | tail -18; done
# 2. built no_route, every race layout
for lid in race_cw race_acw north_cw north_acw; do python tools/no_route.py "$P" --layout "$lid"; done
# 3. the expansion line's bumps placed at mm, and the J4 seam probed on the built street OBJ
python -m scripts.geometry.drive_test "$P" --line expansion
python tracks/san-diego-lake-murray/source/expansion/phase2/proofs/probe_seam.py "$P/data/track.obj" \
  "$P/data/drive_lines.expansion.json" fwd -1192.680 3152.387 3.46 --band 0.03 --half 1.2
```

**Pass:**
- **audit_mesh.** north_cw / north_acw D 0 (I / K 0); street / race_cw / race_acw CLEAN and equal to 0.20.1.
- **no_route race_cw / race_acw.** PASS, with `local_deck_walls` listing only `1WALL_race_*` objects at about v760-779 /
  v2310-2329 (the College mouth, J1 and J5 mouth fills), each on a deck within ±0.70 m. `1WALL_guard*` must be gone.
  - Every key equals 0.20.1's except wall_cells (+ local_deck_cells) and reached_m2 / allowed_m2 (a few m² down). Record the
    numbers.
- **no_route north_cw / north_acw.** PASS, as 2f.
- **drive_test --line expansion.** fwd's third bump at s 4342 lat +3.46, `steps_at` 0.045 m, at about (−1192.680, 3152.387).
- **probe_seam.** It reads the seam continuous (no gap, no jump over 5 mm), as on the Mac. A gap or a jump there is a seam
  defect: bring it back.

Then step 5's held state stands. The next full run, whenever there is one, authors signs before race_verify by itself.
Install only on Kevin's word.

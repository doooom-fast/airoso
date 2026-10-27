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

**Open — P3 repaired a third time and rehearsed again on the branch 2026-10-19, v0.19.0, not installed** (see "P3 repair round 3" at the end: the ground thinned before the export without moving a point, the road model back to about 90 MB; the lamp-post check finds each lamp's own foot; the J1 question for Kevin still open). Was: **Open — P3 repaired a second time and rehearsed again on the branch 2026-10-19, v0.19.0, not installed** (see "P3 repair round 2" at the end: Jackson's painted median and Princess View's centre lane put where the aerial shows them, three raised islands added or moved to their real places, Mission Gorge's south rock face raised 0.3-0.5 m, the model export's duplicate barrier piece fixed; the three existing layouts no worse than v0.18.1; the J1 question for Kevin still open). Was: **Open — P3 repaired and rehearsed again on the branch 2026-10-19, v0.19.0, not installed** (see "P3 repair round 1" at the end: the three checks' refusals fixed at their causes — the drive test's late exemption removed and its verdict written as it works, kn5_ground_check run on all three layouts, every real wall beside the new roads kept, the holes in the hillside closed, the corners on the real ground, Glenroy St's south-west leg and Doreen Rd stubbed; the three existing layouts no worse than v0.18.1; one question for Kevin: tilt the College/Navajo crossroads to its real slope?). Next: Kevin's Drive 1, then P4 dressing. Was: **Open — P3 (the north roads) built and rehearsed on a branch 2026-10-19, v0.19.0, not installed** (refuted by three checks; see "P3" at the end: four roads, three junction pads, two permanent welds, 24 barrier-closed side streets, six cut slopes kept; every gate of the three existing layouts no worse than v0.18.1; the new roads driven both ways PASS). Next: Kevin's Drive 1, then P4 dressing. Was: **Open — P2 (the ground over the expansion) done on a branch 2026-10-14** (see "P2" at the end: the grown heightfield, the pin's 37 / 26 and the re-keyed cache in one change; the tiers planned over the held north network; 3DEP fetched; the existing three layouts byte-identical to v0.18.0 on every drive, mouth and route gate; the loop's ground within 150 m unchanged except beside the two weld mouths; six cut-wall stretches listed for P3's hand authoring; the low clause restated). Was: **Open — P1 done on a branch 2026-10-14, after a fix round** (see "P1 fix round" at the end: both new mouths pass verify_mouths, J1's R 30 return is built as apron AP1 to v1526.3, no road lies over another at either mouth, no step over 6 cm at J5 in any layout on the real wheel paths, both Speedways sealed; the existing three layouts equal to v0.18.0 key for key). Was: **Open — P1 (the readable intermediate, the numbered map, the J1 / J5 weld rehearsal) done on a branch 2026-10-14** (refuted: J5 failed verify_mouths, drive_test still read 6-8 cm steps at J5). Was: **Open — P0 (data, no geometry) done on a branch 2026-10-14** (see "P0" at the end: guarded OSM + buildings, `north`
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


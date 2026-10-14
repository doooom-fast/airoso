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

**Open — planned 2026-10-13** (`tracks/san-diego-lake-murray/EXPANSION-PLAN.md`, revision 2 after an independent critic; place facts in `DOSSIER-EXPANSION-NORTH.md`). Kevin's answers to D1-D4 pending (D3 amends law L3: needs his explicit yes). Was: **Open — research and plan first** (dossier-style: routes, junctions with the loop, elevation and the gorge,
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

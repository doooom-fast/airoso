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

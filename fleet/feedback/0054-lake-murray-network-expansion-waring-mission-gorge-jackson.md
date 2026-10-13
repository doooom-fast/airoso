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

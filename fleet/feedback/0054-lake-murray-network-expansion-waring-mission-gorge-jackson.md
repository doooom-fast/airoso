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

**Open — P0 (data, no geometry) done on a branch 2026-10-14** (see "P0" at the end: guarded OSM + buildings, `north`
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

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

**Open — P1 done on a branch 2026-10-14, after a fix round** (see "P1 fix round" at the end: both new mouths pass verify_mouths, J1's R 30 return is built as apron AP1 to v1526.3, no road lies over another at either mouth, no step over 6 cm at J5 in any layout on the real wheel paths, both Speedways sealed; the existing three layouts equal to v0.18.0 key for key). Was: **Open — P1 (the readable intermediate, the numbered map, the J1 / J5 weld rehearsal) done on a branch 2026-10-14** (refuted: J5 failed verify_mouths, drive_test still read 6-8 cm steps at J5). Was: **Open — P0 (data, no geometry) done on a branch 2026-10-14** (see "P0" at the end: guarded OSM + buildings, `north`
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

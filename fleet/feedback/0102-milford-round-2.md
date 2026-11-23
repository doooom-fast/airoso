---
id: 0102
title: Milford round 2 — GM's 2.9 mi loop and the shoulder (Kevin's calls, Nov 22)
track: milford-road-course-lm
status: in-train
opened: 2026-11-22
---

# Milford round 2

Kevin, 2026-11-22, on the Mac's calls page (board row calls-1122), verbatim:

| Call | Answer |
|---|---|
| Milford: which length? | Build the 2.9 mi loop |
| Milford: the 32 far ledges? | Reshape the shoulder |

The Mac gave both to the PC (session 37e02e50) on branch `claude/mf-finish-r2-20261122`, cut from main 7e31699c. Round 1
(ledger 0100: T3, the start / finish, grass, colliders, the NW building, the pads' shading, verge trees, concrete) is the
Mac's, on `claude/mf-finish-20261122` (0.1.14). Round 2's config goes on top of it once it merges, as 0.1.15.

## 1. GM's 2.9 mi loop

### What differs

Source: OSM, an Overpass read the Mac fetched on Kevin's yes (board asset f61ccecb57d1acdca11e1905258c10ff; committed as
`tracks/milford-road-course/source/trace/gm_loop/osm_mpg_overpass_20261123.json`). The first-mapped dates come from the
way history. Matched against 0.1.13's line (`data/centerline.geojson`) and drawn over NAIP 2022.

- GM's loop is OSM's older ways, clockwise:
  - 72577419 (2010), the outer loop, from node 41 round east, south and west to node 15;
  - then 72577413 (2010), the infield, end to end.
- The PC's projection measures it at 4,710 m. GM's own figure is "2.9 mi", 4,667 m. The Mac's earlier 4,664 m was a live
  read that was never saved.
- Our lap differs at **one** place. At s 768-1,299 it rides 1030539760 (first mapped 2022-02-11), the 534 m southern
  hairpin loop. GM's takes 72577413's own inner turn there (nodes 41-59), 370 m.
  - Swapping only that piece on OSM gives 4,874 m: the same as our 4,887-4,898 m. The hairpin explains the whole gap.
- 1030539761 (2022, the SE hook) is not on our lap.
- The NW corner differs only by the line through the wide apron (~20 m inside, on the same pavement). Our measured line
  stays there.

### The inner branch, measured

Oakland County's 2025 ortho (7.62 cm) shows the inner branch is **concrete**, with an asphalt band on its inner edge.
Source: the Mac's crop, board assets 8a8086d41a7cbf20b69318824f7da18b (md5 7f53c304) and georeference
089196c463697260729e740b41ff8da8. So the road's width there is the whole pavement.

1. **Centre.** Traced off NAIP 2022 by the original tracer's method (`trace_inner.py`): net_extract's colour rule, a
   centre-seeking shortest path via OSM's turn node, perpendicular scans. It runs between `mrc_fixes.json` fixes 337
   (s 834) and 518 (s 1,286), where the two paths part and rejoin.
   - NAIP's width reads were unusable at 0.6 m. The worn asphalt (lum 181-200) and the concrete (209-213) blur together,
     and scans read 0.3-30 m.
2. **Width.** Re-centred and measured on the ortho every 2 m (`ortho_width.py`).
   - Classes sampled on the crop: grass lum 149-156 / chroma 34-35; asphalt lum 193-196 / chroma 13-15; concrete lum
     206-222.
   - Pavement width: the diagonal 15.4-17.4 m, the turn 11-16 m, the return 13-15 m narrowing to 9.8-10.8 m before the
     merge. Then finalize.py's rules (7-18 m valid, a 21-station running median) and to_fixes.py's 9-16 m clamp.
3. **Splice** (`splice_gm_loop.py` → `tracks/milford-road-course/data_gm/`, read by the port through
   `lm_intake.source_data`).
   - Every station outside geojson points 279-369 keeps its committed position, width and raw 3DEP sample bit for bit.
     The projected plan is bit for bit; the heights agree to 1.1 cm (2 cm at the junction point, where the profile's
     windows reach across).
   - The new piece is 91 points / 276.5 m:
     - the joins a cubic Hermite over 30 m, then 4 binomial passes (both [invented]); the first try had 3 m turns of
       -16 / +30 / +15 deg at a join;
     - widths 10.8 / 15.0 / 16.0 m (min / p50 / max);
     - raw heights native 3DEP off the committed `corridor.elev.json`, inverse distance over 4 (the intake's corner-arc
       method). At the kept stations they read p50 1.6 / max 10.4 cm off the committed samples.
   - Controls: the stages' own code reproduces the committed profile and projection to 0.0067 m.
   - The lap on the source line: 4,900.7 → **4,726.0 m**. On the intake line: 4,927.9 → 4,753.2 m. The largest 3 m turn on
     the piece is 10.6 deg (the rest of the lap's is 9.4).
   - `data_gm/heightfield.npy` is force-added (the committed grid's bytes; .gitignore keeps *.npy only in `data/`).
4. **Edge evidence.** `source/edges/edge_evidence_gm.json` = the committed points plus 1,037 on the new piece (526 NAIP, 511
   lidar).
   - Measured by `measure_edges.py` along the GM intake line, with the G10's class-2 points of the hairpin box (board asset
     ebd01b27bdddbb38274afb8b5c987304, npz md5 15ef9535) and NAIP 2022.
   - Both sensors sit within p50 +0.05..+0.75 m of line ± w/2 (the most on the 17 m diagonal, clamped to 16 m).
   - That run's own registration, fitted on the box: naip - lidar east 0.06, north 0.719, outward 0.282 m. The lap-wide fit
     was -0.119 / 0.329 / 0.257.
5. **Measured surface.** The G10 read the GM line (board asset 7da6810244a541615b95aced5f6e5290, md5 3d7b0009: the ring +
   mf_lidar, 9,454 stations, the same plan shift and datum). `tools/measured_surface.py fit` →
   `source/surface/road_surface_gm.fit.json`.
   - 168 stations without a plane, longest gap 37 m; bank p50 5.18 / max 28.42 %.
   - The Mac: outside the splice it matches Nov 13 to p50 2.5-2.8 / p90 8.4-10.5 mm.

### The station-keyed entries, re-read on the GM line

Re-read by position: an old station's point on 0.1.13's intake line, then the nearest point of the GM intake line.

| Entry | Old s | GM s (point moved) |
|---|---|---|
| edge_retrace[0] (front straight, widen) | 4,530-150 | 4,355.5-150 (0.33 m) |
| edge_retrace[1] (agree) | 431-459 | 431.2-458.8 (0.27 / 0.25) |
|  | 1,228-1,237 | **dropped**: on the 2022 loop, 13.7-16.1 m off the GM line |
|  | 2,556-2,600 | 2,380.8-2,424.6 (0.25 / 1.01) |
|  | 2,638-2,675 | 2,462.9-2,499.6 |
|  | 3,468-3,496 | 3,292.5-3,321.0 |
|  | 3,909-3,919 | 3,734.4-3,744.3 |
|  | 4,113-4,144 | 3,938.6-3,969.7 |
|  | 4,224-4,249 | 4,049.3-4,074.1 |
| round 1's painted line (s 4,639.86 on 0.1.13) | 4,639.9 | 4,465.2 (0.22); race_start is lon/lat, so it carries |

Everything else is by position (lon/lat or the local frame) and carries over: race_start, the grid and pits, route.paint,
the rails, the pads, the edge evidence, the lidar patches, the trees.

### Off the lap with the 2022 loop

Distance to the GM lane edge, on round 1's config:

- **T3** (t3_s1000_apron_back): 62.6-77.5 m off. It also leaves edge_retrace[1].rails. Round 1 moved its start 0.2 m;
  round 2 takes it out.
- **Run-off pad R0998:** 37.6-71.0 m off.
- **Run-off pads L1175 and L0883:** now under the new lane, up to 5.4 / 6.6 m inside it. L0883 was the inner branch's own
  concrete, drawn as a pad while the branch was off the lap.
- Every other rail and pad keeps its distance (G4 10.0 m min, as before).
- The 2022 loop itself builds as ground, like the other unused pavement (route-notes L8).

## 2. The inner turn is a real banked turn

The Mac flagged it off the G10's read: at GM s 905-993 (the 147 deg left turn, R ~34 m) a plane misses the seven paths by
p50 0.22 m RMS.

- **It is on pavement.** All seven paths lie on concrete or asphalt in the 2025 ortho at every station s 880-1,008.
- **The 1 m grid continues the shape.** At s 920 the outer side rises to +0.99 / +1.69 / +1.94 / +2.51 / +2.94 / +3.50 m at
  u = -3..-8 (the half width is 8.0 m), about 45-55 % at the outer edge. The inside falls 10-15 %.
- **The fit misses it, and worse than flattening.** On the curve the fit drops the steep outer paths as outliers and
  refits on the flat inner part: b is -16 % at s 940 against -27..-33 % through the paths. The built plane would miss the
  road by over 1 m at both edges.

The fix, opt-in on that stretch only:

- `tools/measured_surface.py section` turns the G10's wide read (board asset 6e9c423785a22056cc77cafdd691cdb8, md5
  976fa8d1: s 850-1,050, 39 paths every 0.5 m, -9.5..+9.5 m) into `source/surface/road_section_gm.json`.
  - Per station and offset: the read's height, low-passed along by fit()'s raised cosine, minus the fit's plane.
  - That misfit: p50 0.091 / p95 1.167 / max 2.714 m.
  - Against a stand-in off the committed 1 m grid (shifted by the same registration): inside ±7.5 m, p50 7 mm / p90 2 cm /
    max 6.8 cm apart.
- `tools/densify_ribbon_blend.py` `route.densify.section` (spans [[870, 1030]] of the product's s, col_m 1.0, taper_m 15,
  both [invented]):
  - the rows over the spans are cut into ~1 m columns (up to 16);
  - every row vertex, and every CURB / MARKINGS / YLINE vertex over a row, moves by that misfit at its lateral offset;
  - writes `data/densify_section.json`.
- The Mac's flags past ±8 m: the high outer edge reads 10-14 % non-ground returns (pavement's end or vegetation
  [inferred]); the inner side's intensity steps up at +7.75 m. The lane edges sit at ±7.6-8 m.

## 3. The shoulder

### Measured on 0.1.13

drive_test's own paved excursion sweep, replayed by `source/ground/scripts/ledge_sweep_blend.py` every 3 m instead of
every 150 m, with the 2017 lidar read at every sample. Records: `source/ground/records/ledges_0102.json`.

- At the 150 m stations it reproduces drive_test's list exactly (28 far + 3 gated; drive_test counts 4 more far at
  s 300 L, which this probe calls guarded).
- **Every 3 m: 1,491 far drops on 404 of 3,266 crossings, ~1.2 km of edge.**
  - Only **91** sit where the lidar also drops over 0.12 m per 0.5 m.
  - At 1,382 the lidar is flatter.
  - The built ground at the drop's foot sits a median **0.58 m** (p5 2.04 m) **under** the lidar.
- The cross-sections show why. The prep holds a shelf at the deck for 3 m and feathers 3-9 m onto TERRAIN. In the
  corridor patch's ramp (0 lidar at 9 m, 1 at 16 m off the lane edge) TERRAIN is still the assembler's draft ground, up
  to 3 m under the real ground. So the built ground drops into a trench 3-14 m out and climbs back, even where the real
  ground rises away from the road (s 900 R: the lidar rises 31.35 → 33.6 m while the build falls to 29.8 m).

### The fix

`tools/shoulder_grade_blend.py`, opt-in `terrain.shoulder_grade`. It runs on the prepped scene after far_ground_prep,
before the pads, the re-seat and the road wear (which follow it).

- From 2 m off the drivable edge, the ground is graded outward on the 1 m lidar:
  - never falling faster than 1V:6H (AASHTO's preferred foreslope, [invented] here);
  - never rising faster than 1V:2H [invented];
  - no fill deeper than 1 m over the lidar [invented]: a deeper real drop stays real;
  - the culvert's headwall patch (culvert_4349_w) kept as is.
- Full weight to 15 m, blended back to the prepped ground by 20 m. Vertices also take the exact cone off their nearest
  edge point: the 1 m grid alone let a vertex just past 2 m fall a whole cell's worth.
- It self-checks its own rule (exit 1, the blend not saved) and writes `data/shoulder_grade.json`.
- **The registration (new here).** The committed 1 m grid sits (-0.375, +0.938) m off the road's frame (the measured
  surface's registration). With the shift the grid meets the G10's paths to p50 1.9 / p90 7.3 cm; without it, 6.9 / 25.9 cm.
  The shoulder takes `lidar_shift_m`. The ledger-0092 ground patch still reads the grid unshifted: not changed here.
- The ring's 1 m ground (the Mac's product c, 768,710 ground cells against 421,519) fills none of the corridor's empty cells
  inside the shoulder band (the 2017 flight returned no ground there). The committed grid stays, its holes filled from
  their neighbours.

### Tested on a copy of 0.1.13's prepped blend

The dense sweep was re-run after each step:

| | far, every 3 m | gated, every 3 m | at the 150 m stations |
|---|---|---|---|
| 0.1.13 as built | 1,491 | 98 | 28 far + 3 gated |
| shoulder, no fill cap | 73 | 4 | 2 far |
| **shoulder, 1 m fill cap, culvert kept** | **230** | **4** | **7 far, 0 gated** |

- Of the capped run's 230:
  - 69 are the copy's pads, still seated on the old ground. The chain re-lays them after this step.
  - 151 are the culvert's real ravine (GM s 4,300-4,400: the lidar itself drops there; the shoulder stands its 1 m fill
    before it).
  - 6 are real drops at s 1,000-1,025, and 4 are single small ones.
- With no cap, the fill over the culvert reached 6.6 m, so the cap stays (the Mac: "if it's a culvert or a real ditch,
  leaving the real drop is right").

## Tests

`tests/tools/test_milford_round2_0102.py`: 6 tests, all PASS on the PC (4 under the system python, the 2 numpy ones under
the lidar venv). They cover:

- the GM loop's kept stations and its new piece;
- section recovering a known curvature;
- densify's Section delta / weight;
- the shoulder's wiring order and helpers.

To come with the config commit: round 1's two tests that name T3 (`test_milford_finish_0100.py`,
`test_milford_furniture.py`) move to the round-2 config.

## Not done

- **The config commit.** `source/round2/edit_config_0102.py` applies it to round 1's 0.1.14. On a local merge it reads
  clean through the intake: the measured surface at all 6,304 points, off the read line p50 0.048 / max 1.171 m. It waits
  for round 1's merge.
- **The rehearsal** from an empty workshop: when the PC has the slot.
- **In game:** the GM loop's inner turn and its bank, the shoulder beside the banked corners, the culvert.

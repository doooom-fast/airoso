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

Round 1 merged into main at b8d39f78 (PR 50; installed). This branch merged that main at a841d670 (a merge, not a rebase:
no force-push) and takes 0.1.15 on top of it. Section 4 says what came in and how the three places both rounds touch were
resolved.

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
the rails, the edge evidence, the lidar patches. The plans round 1 made on the built line itself (the run-off pads, the
verge trees, the trunk colliders) are re-made on the GM lap by their own tools: section 4.

### Off the lap with the 2022 loop

Distance to the GM lane edge, on round 1's config:

- **T3** (t3_s1000_apron_back): 62.6-77.5 m off. It also leaves edge_retrace[1].rails. Round 1 moved its start 0.2 m;
  round 2 takes it out.
- **Run-off pad R0998:** 37.6-71.0 m off.
- **Run-off pads L1175 and L0883:** now under the new lane, up to 5.4 / 6.6 m inside it. L0883 was the inner branch's own
  concrete, drawn as a pad while the branch was off the lap.
- The three pads go, but not by hand: the pads' own outliner, re-run on the GM line, drops them (section 4.2).
- Every other rail keeps its distance (G4 10.0 m min, as before).
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
  - That misfit: p50 0.091 / p95 1.157 / max 2.714 m (p95 1.167 before section 5's lookup fix).
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
  On the Mac's call (fix it in round 2 where it changes ground the build relies on) it is now one opt-in key,
  `terrain.lidar_shift_m`, read by the ledger-0092 ground patch (`tools/lidar_ground_patch.py`'s committed-grid path:
  the lattice nodes stay the grid's own cell centres, moved into the frame) and by the shoulder. Across the corridor's
  9-45 m band it moves the ground p50 0.05 / p90 0.14 / p99 0.29 m (2 % of cells over 0.25 m), the culvert's headwall up
  to 2.2 m. culvert_4349_w's polygon, drawn on the unshifted lidar's headwall, moves by the same in the config. Still read
  unshifted, not changed here: the far ground's own product (data/far_ground.lidar.npy) and the trees' crowns.
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

## 4. On top of round 1 (0.1.14)

### What came in with the merge

Main b8d39f78 brought round 1, ledger 0100, as installed:

- the start / finish on the painted line (race_start, route.paint), the 20-car grid and 20 pits as patterns from it;
- GrassFX at 6 m cells everywhere (0092's near band dropped);
- the trunk colliders within 20 m of the drivable surface (derived from the barrier lines);
- the 883 NAIP-only verge trees;
- the pads shaded smooth with pads_shade_crease_deg 10;
- T3's start moved 0.2 m, mpg_nw_complex_0 set in its slope, the owned concrete.

The merge was clean (no conflicts).

### One command for 0.1.15

`source/round2/apply_0102.sh` takes round 1's 0.1.14 files to 0.1.15, every step in order, each by its own tool:

1. `edit_config_0102.py`: the config edits (section 1-3 and above).
2. `predict_lines_0102.py`: the GM lap's intake line and swept line into `data/`, as the build will write them: an empty
   workshop with ship.json's sync_in, the intake, then the draft's own smoothing (route.smooth_*). On 0.1.14's config it
   reproduces the committed 0.1.14 files **byte for byte** (raw md5 0923d812, swept 1244fc50). The build never reads them:
   the intake deletes the raw snapshot and sync_in copies neither, so the rehearsal makes its own and brings them back.
3. Round 1's plans on the swept line, re-made on the GM lap by their own tools, unchanged: `runoff_pads.py --write` (its doc:
   "re-run it after the line or the widths move"), then `veg_naip_verge.py --write` and `veg_trunks_reach.py --write` (both
   read the pads as drivable, so they come after them).
4. `edit_config_0102.py --docs`: the numbers below into the config's docs.

GM lap, swept: 6,304 points, 4,723.67 m (0.1.14: 6,537 points, 4,898.25 m).

### 4.1 The start / finish

race_start's line, route.paint's sf_line and the grid / pit patterns are declared by the **measured** paint (lon / lat), not
by station. So tools/circuit_dummies_blend.py re-reads them on the build's own lap; no old number is carried. On the GM lap's
swept line (scripts/geometry/circuit_start.plan, the build's own plan):

| | 0.1.14 | 0.1.15 (GM) |
|---|---|---|
| the painted line | s 4,639.86 | s 4,465.28 |
| grid (20) | s 4,546.0-4,632.5 | s 4,371.4-4,457.9 |
| pits (20) | s 4,647.9-4,734.3 | s 4,473.3-4,559.7 |
| AC_TIME_1 / _2 (thirds) | s 1,374.4 / 3,007.1 | s 1,316.2 / 2,890.7 |
| plan problems | none | none |

All on the front straight, 3.3 km from the splice (s ~768-1,045). The build's self-check (ROAD under every car's corners)
reads it again in the rehearsal.

### 4.2 The pads

`runoff_pads.py` on the GM intake line keeps **18** strip pads (0.1.14: 19), plus the ride pad:

- the 4 before the splice keep their keys (R0125, L0338, R0356, L0395);
- the 12 after it are the same NAIP blobs, renamed by the GM line's stations (keys are side + station: L1530 -> L1355 ...
  L4775 -> L4601) and re-sampled on their 4 m rows: outlines change 0.2-23 % (L4359 -> L4184: 305 -> 235 m2);
- L0883, R0998 and L1175 go (as section 1 found by hand);
- **R0880 and R1008 are new**: the 2022 loop's grey pavement beside the GM inner turn (748 / 1,296 m2, NAIP blue / red
  0.937 / 0.931, 0 folds).

pads_shade "smooth" and pads_shade_crease_deg 10 are keys of the scenery.bespoke block, so every pad, the new two included,
keeps round 1's shading. Every pad starts at the strip's lip on the GM lane (min 1.76-1.90 m, as on 0.1.14).

Why re-outline and not edit: with the old outlines, R0356's inner edge came 0.20 m closer to the GM lane (1.83 -> 1.63 m at
s 426.5), onto the edge strip. Measured cause (the agree retrace, instrumented on both configs): the GM line reaches the
retrace about 4 mm off 0.1.14's at s 395-440. That is enough to put an 8th lidar point inside the ±7.5 m window at s 427.8
(the tool's MIN_POINTS 8). One more row measures (NAIP 10.59 / lidar 10.29 m, mean 10.44), and the Gaussian carries it to
s 419.5. The right edge there moves out 0.1-0.4 m, toward both sensors (s 426: NAIP 11.64 / lidar 10.64; fit 9.45 -> 9.86).
The retrace's own threshold, not an error. The re-outline follows it.

### 4.3 The grass and the trees

- **Grass:** tools/plan_grassfx_aerial.py runs in the build (ship_grassfx_aerial) on its own line and pads. With 0.1.14's
  near band dropped, the 6 m cells read the class map whatever the lane; only the pad looks move. On the GM lap: 3,963
  rectangles (0.1.14: 3,952).
- **Colliders:** the reach rule re-run on the GM lap gives **20 m** again (g4_infield_esses' median standoff 19.07 m; T3, a
  tyre wall, is gone but was never the widest). 251 colliders (167 lidar + 84 verge; 0.1.14's file on 0.1.13's line: 261).
  On the intake line instead of the swept line the rule would have read 19 m (18.81): it has to be the swept line.
- **Verge trees:** 884 (0.1.14: 883): one more clears the drivable surface's corridor margin; left out 28 (was 29). Keys are
  KEY0 + rank, so 286 of the 884 take new keys (TreeFX's model and angle draw); 598 keep theirs.
- **Lidar trees:** one within 4.41 m (margin + half a cell) of the GM drivable surface, the same one as on 0.1.14's lap; none
  within 3 m. Nothing to clear.

### 4.4 What an empty workshop needs

The intake test caught it: ship.json's sync_in did not list round 2's files, so an empty-workshop build would have failed.
Added: `source/edges/edge_evidence_gm.json`, `source/surface/road_surface_gm.fit.json`, `source/surface/road_section_gm.json`.
sync_out now carries back `data/densify_section.json` and `data/shoulder_grade.json`.

## 5. The first rehearsal (red) and its two fixes

The PC rehearsed b61ebc05 from an empty workshop on 2026-11-23, 03:45-04:41 (`D:/k10-scratch/milford_0115_reh`, `--no-install`,
ENG eng_mflm_0114, AIROSO_NUMPY_PY = the lidar venv). It was **red on one gate**: the street drive_test read 1 "ground on top
mid-lane" (s 947.0, u -0.75, 1GRASS_1). Nothing was installed.

Correction (2026-11-23, after the second rehearsal): the same street drive_test also read **69 daylight gaps**, a second
failing row. The PC reported only the ground on top. Section 6 has the 69.

Everything else was green:

- race drive_test / audit / no_route; audit CLEAN;
- kn5_ground_check PASS (road over ground p95 +0.021 m);
- textures (25 embedded, 0 missing); road wear PASS (tone r 0.963); houses PASS; edge_smoothness PASS;
- the start / finish at s 4,465.3 (kn5 heading +1.000); the pads' seat 0 ground-over; the road kn5 51,192,541 B
  (0.1.14: 53,213,752);
- data/centerline.raw.local.json and centerline.local.json byte for byte the committed prediction.

### Measured on the built road

Off the gate OBJ (`source/round2/lane_poke_0102.py`, read-only: the highest ROAD / KERB and grass face every 0.25 m along
and across the lane):

- 86 points on s 922-975 have grass over the road, up to +3.1 cm. The rest of the lap has none; the installed 0.1.14 has 4
  on its whole lap, max 2.6 mm.
- Every grass vertex under the lane sits at the deck -0.0200 m (the prep's pin worked). The faces stand over the road where
  the road folds inside them (0.85 m faces).

Two causes:

1. **A lookup bug** (25 points, max +3.1 cm, the inner edge, s 922-975). `measured_surface.Product._nearest` stopped after
   ring 1 of its 6 m cells whenever ring 0 / 1 held any station, so a point more than a cell off the line could take a
   farther station.
   - On the inside of the turn, section() put u >= +7.0 at s 970-976 on station s 966.0 (4-10 m back). The plane under it
     fell 0.3-0.5 m, so the delta stepped +0.27..+0.47 m from u +6.5 to +7.0.
   - The raw read has no step (paths +6.5 / +7.0 at s 974: 23.65 / 23.57 m), nor has the committed 1 m grid.
   - Built: at s 974 the lane fell -14.2 % then climbed +31.8 % in its inner 0.9 m. That is a 25 cm ramp the wheel paths
     never swept (drive_test clamps them at 6.0 m).
2. **The bowl's real folds** (61 points, max +2.1 cm, s 925-962, u -2.0..+1.9). Densify's ~1 m columns fold the lane
   (s 953: -47 / -41 / -22 / -7 % at u -2.9 / -1.9 / -0.9). A 0.85 m grass chord across a 16-19 % fold stands ~4 cm over
   it: 2 cm past the prep's clearance. Drive_test's hit is one of these.

### Fix 1: the lookup

- `_nearest` stops only when no farther ring can hold a nearer station (best <= (r x cell)^2).
- No other consumer changes: of the intake's queries, 0 of 6,304 (GM product, GM swept line) and 0 of 6,537 (round 1's
  product, 0.1.14's line) take another station; the farthest is 1.33 / 1.51 m off.
- `predict_lines_0102.py --check` on this tree: the committed lines ARE the prediction. On 0.1.14's tree (b8d39f78, the
  new file copied in): 0.1.14's lines (0923d812 / 1244fc50) ARE the prediction.
- section(): 481 of 15,600 points take another station. Most move one 1.5 m station (s 850-976, |u| >= 6.5); the big ones
  are at s 970-976.
- `road_section_gm.json` regenerated (md5 6cad591d -> 642763ad): 156 of 5,226 cells moved, max 0.413 m (s 976.0, u +7.0);
  on s 922-975, 62 of 1,404, max 0.311 m (s 974.5, u +7.0). The u +6.5 -> +7.0 step at s 966-980 now reads 0.047-0.070 m,
  as its neighbours do (it read up to 0.469).

### Fix 2: the ground under the bowl

- Opt-in `route.seat_edges_section` (Milford only) in `tools/seat_edges_blend.py`; the rule is `tools/seat_edges_section.py`.
- Every TERRAIN face under the road on the section's stretch (its spans, + taper_m and PAD_M: s 845-1,055) is read on a
  15-point barycentric grid against ROAD + CURB.
- Its fold excess is the most its chord, laid through the road's height at its corners (where the prep will pin them),
  stands over the road. A face over 1 cm (seat_edges' CHORD rule, half the prep's 2 cm clearance) is cut by
  ceil(excess / 1 cm). Nothing moves: the prep pins the new vertices.
- Self-checked: every such face is read again, exit 1 and loop.blend not saved if one would still stand over the clearance.
- Tried on a scratch copy of the red rehearsal's loop.blend (`D:/k10-scratch/mf_0115_seat_test`, 69 s; its road still had
  the old section):
  - 85,670 faces read, fold excess max 3.87 cm;
  - 1,379 cut (1 / 2 / 3 cuts x 1,156 / 197 / 26), +4,263 TERRAIN vertices;
  - after: max 1.48 cm, 199 faces over 1 cm, 0 over the 2 cm clearance.
- The 2 cm clearance is unchanged. `edit_config_0102.py` writes the key (step 4b), so the one-command flow from 0.1.14
  reproduces the committed config.

## 6. The second rehearsal (red) and the daylight probe

The PC rehearsed a05c4924 (both fixes) from an empty workshop on 2026-11-23, 07:51-08:48 (`D:/k10-scratch/milford_0115b_reh`,
`--no-install`, ENG eng_mflm_0114, AIROSO_NUMPY_PY = the lidar venv). Nothing was installed.

### Both fixes held

- lane_poke on s 922-975 (0.25 x 0.25 m, 11,855 lane points): **0 above the road**, 0 within 5 mm under. The whole lap
  (1.0 x 0.25 m, 257,791 points): 0 above, 14 within 5 mm under (0.1.14: 4 above, max 2.6 mm).
- drive_test's ground on top mid-lane: 0 (the first rehearsal: 1).
- The seat-edges section, s 845-1,055:
  - 23,164 faces under the road read, fold excess max 5.11 cm;
  - cut 1 / 2 / 3 / 4 / 5 times x 962 / 304 / 102 / 21 / 2, 3,697 edges split;
  - TERRAIN 310,656 -> 316,625 vertices (+5,969);
  - after: excess max 1.94 cm, 371 faces over 1 cm, 0 over the 2 cm clearance.
- The road kn5 51,527,489 B (the first rehearsal 51,192,541: +334,948 B, +0.65 %).
- The lines byte for byte the committed prediction.
- Green: verify_kn5 and its --inis; street audit CLEAN; race drive_test / audit / no_route; kn5_ground_check PASS; textures;
  road wear (all six rows); houses; edge smoothness.

### The one red row: 69 daylight gaps

The street drive_test's other rows were the first rehearsal's: bumps 4.87 / km, kinks 12.7 / km (not gated on Milford),
vertex bumps 2, severe 0, gated excursions 0. It failed on **daylight gaps 69** (limit 0). The first rehearsal read the same
69 (see the correction in section 5).

Measured with read-only copies of drive_test on the finished workshop (scratchpad `r2/dt_daylight.py`,
`r2/dt_daylight_cmp.py`, the report write redirected):

- All 69 lie at s 912-980, on the left, at the probe's point 0.8 m past the edge: the outer side of section 2's banked
  turn.
- **None is a hole.** At every one the kerb or the grass stands 0.03 m under to 0.30 m over the road's own edge.
- The built left edge stands 2.59-3.68 m over the centre deck (s 936: +0.96 m at u -2, +3.50 m at u -7.5), the measured
  bank of section 2.
- drive_test's window runs from 7.5 m under to 2.5 m over the **centre** deck (`top_at(..., deck_c - 2.5, 5.0)`), so on
  this bank the surface beside the edge is above its top.

### The fix: opt-in `drive_test.daylight_edge_ref`

The Mac's call, 2026-11-23: "Build (a), not (b); no force-install."

- `scripts/geometry/drive_test.py`: with the key, the same window (5 m, limit 0) hangs from the road's own height at each
  edge, the highest 1ROAD face 0.15 m inside it [invented] (`_road_top_at`, `DAYLIGHT_EDGE_INSET_M`). A station with no
  road there keeps the centre deck. The report carries `daylight_edge_ref` (the inset, the probes read off the edge, the
  ones that fell back). It moves where the probe looks, not its limit. Without the key the report is byte for byte as before.
- `edit_config_0102.py` step 4c writes the key into Milford's config, so the one-command flow from 0.1.14 reproduces it.
- Entry in `fleet/GATES-CHANGELOG.md` (2026-11-23).

Proven with the old (a05c4924) and the new drive_test on finished workshops (scratchpad `r2/dt_run.py`, `r2/dt_proofs.sh`):

| build | without the key: old vs new | with the key |
|---|---|---|
| High Plains `full_course` | byte-identical (md5 278bbe21) | not named |
| Milford 0.1.14 (`milford_lm`) | byte-identical (230089e7), 0 gaps | 0 gaps in 9,798 probes, all read off the edge, 0 fell back; no other field moves |
| Milford 0.1.15 (`milford_0115b_reh`) | byte-identical (b1698c84), 69 gaps | **0 gaps** in 9,448 probes, all read off the edge, 0 fell back; only `daylight_gaps` and `fail` move: the street drive_test **passes** |

Install waits for Kevin's word on the key (the Mac is asking him, with before and after: his Nov 22 "Show me before and
after first").

## Tests

`tests/tools/test_milford_round2_0102.py`: 16 tests, all PASS on the PC (the numpy ones under the lidar venv). They cover:

- the GM loop's kept stations and its new piece;
- section recovering a known curvature;
- densify's Section delta / weight;
- the shoulder's wiring order and helpers;
- 0.1.15's config and the files an empty workshop gets;
- the edit script refusing anything but 0.1.14;
- the committed lines being the prediction (runs the intake);
- the start / finish on the GM lap;
- the pads as the outliner's, round 1's shading kept;
- section 5: the ring search finishing (synthetic), the s 970-976 points taking their own station with no step in the
  committed section, the fold rule, and the key opt-in (Milford only, written by the edit script);
- section 6: the daylight key opt-in (Milford only, written by the edit script, drive_test reads it).

`tests/geometry/test_drive_test.py::test_daylight_edge_ref_hangs_the_probe_from_the_banked_edge_ledger_0102` (synthetic):
an 8 m road on a 70 % bank, its left edge 2.8 m over the centre deck and the grass beside it 3.31 m over. Without the key
there is one gap a station; with it none, every probe read off the edge. Every other gated reading is equal, and a flat
road's report is equal but for the new field. The drive_test test files (`tests/geometry/test_drive_test*.py`,
`test_lariat_drive1_switches.py`, `tests/tools/test_calibrate_kinks.py`, `test_seat_edges_grade.py`): 41 passed;
`test_sand_creek_lm_assets.py` (dense_hops / vertex_kinks opt-ins): 44 PASS under the lidar venv.

`test_seat_edges_grade.py` pins the tool's early return; it now names the third opt-in (`sec_s is None`).

Round 1's tests moved to the GM lap, the 0.1.14 numbers kept beside them:

- `test_milford_finish_0100.py`: T3 off the lap, its move restated; the line at s 4,465.28; 251 colliders; 884 verge;
  version 0.1.15;
- `test_milford_furniture.py`: no rail opts into stand_on since T3 left;
- `test_milford_line_edges.py`: the front span [4,355.5, 150]; 18 pads;
- `test_milford_ground_0092.py`: 3,963 grass rectangles.

`test_ship_track_chain.py`'s V4_EXTRAS now names the shoulder's step header. It had failed on this branch since ca6622a6
(the hook commit); the full suite caught it.

The full suite on this PC's system python: 11 failed + 8 collection errors, the same names as on main b8d39f78 (numpy /
Pillow missing on that python); every Milford test that needs numpy passes under the lidar venv.

## Not done

- **The third rehearsal** from an empty workshop, on section 6's head, when the PC queue reaches it, still 0.1.15. Then
  check: the street drive_test's daylight gaps 0 with `daylight_edge_ref` 0 fell back; lane_poke as the second rehearsal
  (0 over on s 922-975 and the lap); every gate; the kn5 expected at the second rehearsal's 51,527,489 B [inferred: nothing in
  section 6 touches a build step].
- **Install** only after Kevin's word on the key (the Mac is asking him).
- **In game:** the GM loop's inner turn and its bank, the shoulder beside the banked corners, the culvert.

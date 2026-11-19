---
id: 0091
title: Milford's line and edges toward High Plains — the line pre-compensated for the assembler's smoothing, the flared stretches re-traced in or out, the widths' breathing smoothed, finer rows
status: diagnosed
scope: track:milford-road-course-lm (tools/lm_engine_intake.py, tools/edge_retrace.py; opt-in config)
layer: engine
train: -
---

## Request (Kevin, 2026-11-18)

> "milford is still very messy. let's do a measured, parallelized effort to get it closer to high plains in terms of
> quality and accuracy."

This entry is the road line and the lane edges (one of four parallel pieces; the ground beside the road, run-off, grass,
trees, buildings, race furniture and the road texture are the others'). It codes the geometry audit's Fixes B, A, C and
D and its Gap 7 as opt-in config, measured on the Mac with the intake's own data stages (no Blender build). The PC builds.
Not here: the audit's Gap 4 (edge heights: needs a G10 read) and Gap 6 (the lidar's own waviness: Kevin's call), and the
layout (Kevin is deciding whether Milford should be the 2.9 mi loop rather than this 4,887 m variant).

## Symptom

From the audit (the Mac's geometry auditor, 2026-11-18, main 74b46263; its scripts and JSON are in the Mac's
`milford-hp-audit-20261118/geometry/` folder):
- **The road sits inside every bend.** Where both edge sensors agree (27 % of the lap), the built centre is 0.36 m
  (p50) / 1.01 m (p90) off the measured centre; the intake's own line, before the assembler's smoothing, is 0.22 / 0.64 m.
  Worst runs 1.1-1.3 m (s 2,377-2,443, 2,934-2,960, 442-481).
- **One-sided paving built two-sided.** At gores and service-road mouths the far edge runs 1.3-2.0 m into grass (s
  435-455, 2,545-2,560, 3,905-3,915; straight chamfers at s 4,117 and 4,228).
- **The width breathes** 98 / 212 mm RMS in the 20-40 / 40-80 m bands (High Plains: a constant 12 m).
- **The s 978-998 kinks** (28, all of them) and 16 vertex bumps: a gate artefact of 1.5 m rows on the R 15 m, -14 %
  corner, not felt (none over 0.68 %/m on a wheel's own travel).
- **The front straight's 0.1.12 retrace shift** adds lateral jerk on the fastest part of the lap.

## Evidence (the Mac's dry run reproduces the build)

`tools/lm_engine_intake.py` run on the Mac into an EMPTY workshop (ship.json's sync_in, as
`tests/tools/test_lm_engine_port.py` does) with main's config writes `data/centerline.local.json` **byte-identical** to the
committed `data/centerline.raw.local.json` of 0.1.12 (the assembler's snapshot of it; md5 69add48c…), and the same
crossfall. The audit's scoring re-run on that line reproduces its numbers exactly (centre 0.357 / 1.014 m, edges
0.383 / 1.190 and 0.388 / 1.248 m, width bands 97.6 / 211.8 mm), its validated ribbon + drive model gives 28 kinks / 16
vertex bumps / 0 severe, and a proxy of the built lane (the line through the assembler's own smoothing, swept by
`scripts-v021 ribbon.road_ribbon`, then `tools/edge_smoothness.py --gate-default`) gives 0.1.12's p99s (d2 0.0120 /
0.0119, resid 0.0039 / 0.0041 m against the build's 0.0120 / 0.0120, 0.0040 / 0.0040). The same code with this
branch's tools and main's config is again byte-identical (centerline, crossfall, edge_fit, edge_retrace, lm_intake.json):
the refactor alone changes nothing.

## Diagnosis

As the audit found, each checked in the code:
1. `scripts-v021/geometry/smooth.py` is a count-preserving Gaussian with no shrink correction: a bend of radius R comes
   in by about sigma^2 / 2R, and `build_loop_blend` sweeps the widths unchanged about the smoothed line, so both edges
   come in together.
2. `lm_intake.width_taper` widens a width step symmetrically about the line (it only widens), so a one-sided gore flares
   both sides; `tools/edge_retrace.py` could only widen ("never in") and spanned only the front straight.
3. The trace's width is a 0.25 m scan through a +-24 m running median, rescaled by heading; edge_fit's +-15 m LOESS takes
   out only the part shorter than ~20 m.
4. drive_test reads a fixed-offset wheel path's slope across each 1.5 m vertex: on R 15 m at 4.5 m off it hops 0.45 m.
5. The retrace's per-side edges (NAIP's scatter along the straight, smoothed 8 m) carry 20-80 m wiggle into the line
   shift; and the assembler then smooths that shift (S(D), not D), so the edges it measured are not quite the ones built.

## Fix (this branch; every key opt-in, absent = as before)

**`tools/lm_engine_intake.py`**
- `lm_intake.line_precomp` true (Fix B), right after the resample: x, z <- 2 P - S(P), S = the route's own smooth
  (`route.smooth_*`, horizontal). The assembler's S(2 P - S(P)) = P - (I - S)^2 P. Y, widths and count kept. edge_fit,
  edge_retrace and measured_surface each still smooth the line they are handed, so each reads the line the assembler
  builds. Reported as `lm_intake.json` `line_precomp`.
- `lm_intake.width_smooth_m` (Fix C), after edge_fit and before the retrace: a Gaussian of sigma m by arc length on the
  assembler's line (closed lap). Held where a retrace record in mode "widen" acts (its spans and its 60 m fade, by its own
  weight); a record in mode "agree" then re-traces its stretches over the smoothed widths. Reported as `width_smooth`.
- `lm_intake.edge_retrace` may be a LIST of records, run in turn (a dict is 0.1.12's, written as before). New optional keys
  per record: `mode`, `smooth_m`, `erode_m`, `gap_m` (the tool's SMOOTH_M / ERODE_M / GAP_M), and `shift_precomp` true: the
  record's line shift D goes in as 2 D - S(D) (S linear: S(D) = S(P + D) - S(P)), so the assembler builds ~D. An unknown key
  stops the intake. A list writes `data/edge_retrace.json` as `{"runs": [...]}`.
- `lm_intake.resample_m` 0.75 (Fix D) needed no code.

**`tools/edge_retrace.py`**: `mode "agree"` (Fix A). Per row, NAIP's and the lidar's medians (+-7.5 m, 8 points each, as
the widen mode's); the row measures only where they agree within `edge_fit.AGREE_M` (0.6 m, ledger 0087's fit-mode rule),
and reads their mean; points are owned from 0.3 x today's half width out (a tapered flare's real edge sits up to ~4.4 m
inside today's). The edge goes there in OR out (the 5 m Gaussian's cap is +-0.3 m of the row's reading). The erosion
works toward zero (the least widening, or the least narrowing, within +-erode_m; a window holding both is no change), and
the rails' headroom is eroded on its own and binds the change before the 8 m smoothing; the final rail clamp, the fade and
the smoothing are the widen mode's. Rows that do not agree keep today's edge. `mode "widen"` (the default) is unchanged
(a test checks the explicit defaults give the same result, bit for bit). The windowed sums now visit only the rows within
reach, in the same index order, so they are the full pass's bit for bit (0.1.12's record reproduces byte-identical).

**`tracks/milford-road-course-lm/track.config.json`** (lm_intake and route keys only):
- `route.smooth_sigma_pts` 4 -> **10** with `lm_intake.resample_m` 1.5 -> **0.75** (7.5 m, the audit's modelled 5 pts at
  1.5 m: with the precomp the least smoothing that leaves the line no noisier than 0.1.12's).
- `lm_intake.line_precomp` **true**; `lm_intake.width_smooth_m` **10.0** [the audit's modelled sigma].
- `lm_intake.edge_retrace` = two records:
  1. the front straight (s 4,530 -> 150, G2 / G3, NAIP, clear 0.20 m, taper 60 m) as 0.1.12, plus `shift_precomp` true and
     `smooth_m` / `erode_m` **12 / 12** [invented, Gap 7; the measured trade is in the table below].
  2. `mode "agree"` over the eight stretches width_taper flared (where the source widths were widened, located on this
     line): s 431-459, 1,228-1,237, 2,556-2,600, 2,638-2,675, 3,468-3,496, 3,909-3,919, 4,113-4,144, 4,224-4,249; **all 11
     rail keys** of scenery.bespoke.rails for the clamp; clear 0.20 m, taper 60 m, 8 m smoothing (the tool's), `erode_m`
     **2.5** [invented, measured trade below], `shift_precomp` true.
The version is not bumped here (the other three pieces edit the same file; the orchestrator's merge sets it).

## Measured on the Mac (dry run of the intake; the audit's metrics on the assembler's line)

Each column adds to the one before. "Agreed" = both sensors' 15 m medians within 0.6 m (the audit's rows, fixed in world
coordinates). Zones: built edge minus measured, median (+ = built wider).

| measured | 0.1.12 (main) | + B precomp | + A agree | + C widths | + Gap 7 | **+ D 0.75 m = the config** |
|---|---|---|---|---|---|---|
| centre to the measured centre, p50 / p90 m (share > 0.5 m) | 0.357 / 1.014 (36.5 %) | 0.236 / 0.679 (19.6 %) | 0.228 / 0.650 (17.3 %) | 0.228 / 0.650 | 0.228 / 0.652 | **0.227 / 0.652 (17.2 %)** |
| left edge to the measured edge, p50 / p90 m | 0.383 / 1.190 | 0.293 / 0.936 | 0.273 / 0.867 | 0.271 / 0.853 | 0.270 / 0.852 | **0.270 / 0.851** |
| right edge, p50 / p90 m | 0.388 / 1.248 | 0.292 / 1.034 | 0.266 / 0.932 | 0.258 / 0.928 | 0.262 / 0.929 | **0.263 / 0.930** |
| width minus the measured width, p50 abs m | 0.280 | 0.280 | 0.268 | 0.287 | 0.289 | **0.287** |
| far edge s 435-455, right (20 rows) | +1.87 | +1.63 | +0.52 | +0.51 | +0.51 | **+0.47** |
| far edge s 2,545-2,560, right (8 rows) | +2.15 | +1.87 | +0.41 | +0.46 | +0.46 | **+0.43** |
| chamfer s 4,117-4,147, left (20 rows) | +0.38 | +0.56 | +0.11 | +0.17 | +0.17 | **+0.19** |
| chamfer s 4,228-4,252, left (10 rows) | +0.52 | +0.66 | +0.04 | +0.01 | +0.01 | **+0.08** |
| s 3,905-3,915, left (5 rows; the right has no agreed row) | -0.19 | -0.08 | -0.15 | -0.28 | -0.28 | **-0.21** |
| width band RMS 20-40 / 40-80 m, mm | 97.6 / 211.8 | 97.3 / 212.5 | 94.8 / 227.6 | 44.7 / 188.3 | 42.8 / 183.2 | **45.5 / 188.6** |
| width reversals >= 0.10 m, per km | 17.2 | 17.2 | 17.6 | 13.9 | 13.5 | **14.3** |
| line: 20-40 m curvature RMS (1/m); min R | 9.27e-4; 15.0 m | 8.75e-4; 15.0 | 8.76e-4 | 8.81e-4 | 8.78e-4 | **8.79e-4; 15.0 m** |
| gate lap, m | 4,886.9 | 4,897.8 | 4,898.2 | 4,898.3 | 4,898.3 | **4,898.2** |
| front straight: lateral jerk p95 (m/s3); edge to NAIP, median L / R m | 48.6; 0.385 / 1.104 | 41.3; 0.411 / 1.103 | 41.3 | 41.3 | 36.5; 0.481 / 1.217 | **40.9; 0.504 / 1.207** |
| edge_smoothness proxy: d2 p99 L / R; resid p99 L / R (m); ragged | 0.0120 / 0.0119; 0.0039 / 0.0041; 0 | 0.0122 / 0.0125; 0.0040 / 0.0041; 0 | 0.0120 / 0.0120; 0.0039 / 0.0040; 0 | 0.0078 / 0.0078; 0.0019 / 0.0020; 0 | 0.0077 / 0.0078; 0.0022 / 0.0022; 0 | **0.0075 / 0.0076; 0.0019 / 0.0017; 0 (PASS)** |
| drive model: kinks / vertex bumps / severe / apron steps | 28 / 16 / 0 / 0 | 35 / 17 / 0 / 3 | 37 / 19 / 0 / 2 | 37 / 19 / 0 / 2 | 37 / 19 / 0 / 2 | **9 / 5 / 0 / 0** |
| road triangles; densify worst warp; max columns | 24,470; 94.6 mm; 19 | 24,454 | 24,410 | 24,384; 96.0; 20 | 24,374; 96.0; 20 | **33,396; 48.2 mm; 10** |
| closest rail face to the lane edge: G2 / G3; T3; G1 (m) | 0.167 / 0.171; 0.883; 3.76 | 0.106 / 0.140; 0.403; 3.64 | 0.106 / 0.140 | 0.108 / 0.140; 0.393 | 0.169 / 0.180; 0.393; 3.64 | **0.167 / 0.176; 0.392; 3.64** |

How these were read (Mac scratch scripts, read-only on the repo; Blender's python for numpy): the audit's own metrics
(`accuracy_centre.py`, `sim_edges_precomp.py`, `sim_widths.py`, `metrics.py`: its station CSV of both sensors' 15 m
medians on the as-built line, held fixed in world coordinates, projected onto each candidate line; FFT bands on the closed
lap at 1 m); the drive model is the audit's `ribbon_model.py` + `drive_model.py` on the intake's line, widths and
crossfall; the rails are every scenery.bespoke.rails polyline every 0.5 m against the lane edge +-w/2. Column 1 reproduces
the audit and the build (above). The precomp alone lands on the audit's model (0.235 / 0.677, edges 0.293 / 0.941 and
0.289 / 1.036, lap 4,897.9). Fix A acts only over the eight flared stretches (with their 60 m fades), so its lap-wide gain
is small (edge p50 0.29 -> 0.27 m); where it acts the far edges come in 1.1-1.7 m. 0.75 m rows change edge_fit's verdicts:
0 samples rejected (1.5 m: 2, the s 2,942 left spike), since a 3 m dip now spans more than SPIKE_MAX_ROWS rows; the 10 m
width Gaussian takes it out (0.18 m over 3 m).

Choices inside the table, measured:
- **Agree record's erosion** (far edge at s 435-455 / 2,545-2,560; agreed rows left > 0.25 m inside the sensors' +-5 m
  reading): erode 10 m (the widen mode's) +1.12 / +1.28 m, 0 rows; 5 m +0.76 / +0.80, 1; **2.5 m +0.52 / +0.41, 4**; 0 m
  +0.45 / +0.20, 9 (of ~450).
- **Front straight (Gap 7)**, with the line pre-compensated and shift_precomp (lateral jerk p95 over s 4,560 -> 150 at the
  model's speed / the edge vs NAIP's points, median, left / G2's and G3's closest face to the lane edge): 8 / 10 (0.1.12's)
  49.6 m/s3 / 0.40 m / 0.179 / 0.199 m; **12 / 12 36.5 / 0.48 / 0.169 / 0.180**; 12 / 15 33.8 / 0.58 / 0.180 / 0.184; 14 / 10
  33.7 / 0.45 / 0.150 / 0.168 (and a 2 cm edge residual where the clamp starts); no retrace at all 34.3 / 1.58. Without
  shift_precomp, 8 / 10 left G2's face 0.108 m off the edge (10.5 m under 0.15) at 41.3 m/s3: the assembler's sigma 7.5 m
  smooths the shift more than 0.1.12's 6 m did.
- The audit's "66 curvature reversals" on the front straight (built) against 13 (no shift) is mostly the mm rounding of
  data/gate_centerline.json: the file differs from the float line by up to 0.55 mm, which is 2.3e-4 1/m on a 3 m chord. On
  the float line 0.1.12 reads 12; every variant here 12-14. The jerk p95 is not rounding (48.6 on the float line).

## Scope

Milford's port only (`tests/tools/test_milford_line_edges.py::test_the_0091_options_are_milfords_alone`). Other ports:
the new blocks are guarded by their keys; High Plains' and Exotics' intakes were run on the Mac on main and on this
branch: byte-identical outputs. Lake Murray runs no intake. No gate threshold moved.

## Verification (decided before the build)

The PC's rehearsal (runbook 0091-1) must show, against 0.1.12:
- SHIP OK, no force; every gate PASS with no threshold moved;
- `data/lm_intake.json`: `line_precomp.moved_m` p50 0.20 / max 3.23 m; `edge_retrace` two runs (widen, agree), both
  `shift_precomp`; `width_smooth.changed_m` p50 0.044 / max 0.655 m; resample 1,635 -> 6,537 points; gate lap ~4,898 m;
- drive_test: severe 0, kinks ~9 (1.8 / km, all at s 990-1,000), vertex bumps ~5 [the audit's ribbon model]; the
  excursion drops (0.1.12: 2, gated, s 901 / 1,201) not more;
- edge_smoothness PASS, 0 ragged (proxy: d2 p99 0.0075 / 0.0076, resid p99 0.0019 / 0.0017 m);
- the rails: no post left out (bespoke report), G2 / G3 faces >= 0.15 m off the lane edge (proxy min 0.167 / 0.176 m),
  T3 (s 1,000 apron back) 0.39 m at its closest (0.1.12 0.88 m: the line now holds the corner's real radius);
- verify_kn5: 1ROAD under 65,535 writer vertices (0.1.12: 17,194 smooth-shaded; ~33,400 road triangles here, +36 %, so
  ~23,000 expected [estimate: 17,194 x 1.36]);
- road_wear PASS (its registration reads the line, which moved); kn5_ground PASS; houses PASS.
Then Kevin drives it: the edges at the NW corner, the s 2,550 gore and the bottom service-road mouths; the front straight.

## Runbook 0091-1 (PC): rehearse, NO install without Kevin's word

1. Check out this branch once the orchestrator has pushed it (`git status` clean; `GIT_LFS_SKIP_SMUDGE=1` is fine, the draft
   rebuilds loop.blend). The TreeFX bins into `tracks/milford-road-course-lm/source/trees/` as runbook 0082's (md5-checked;
   never commit a .bin). ENG = 0.1.12's (`eng_mflm_017`).
2. Rehearse from an EMPTY `D:/k10-scratch/milford_0091_reh`:
   `ENG=<ENG> SHIP_PROJ=D:/k10-scratch/milford_0091_reh AIROSO=<checkout> PYTHONUTF8=1 bash tools/ship_track.sh milford-road-course-lm --no-install`.
   The intake must print (the Mac's dry run, byte-equal to it if the inputs are):
   - `resampled every 0.75 m: 1635 -> 6537 points`;
   - `line pre-compensated for the assembler's smoothing (sigma 10.0 pts x 2): points moved p50 0.201 / max 3.231 m outward; lap 4901.8 -> 4927.4 m`;
   - `edge fit (judge, ...): 0 samples rejected`;
   - `widths smoothed (Gaussian sigma 10.0 m; 691 rows held for a widen retrace, 160 blended): changed p50 0.044 / p99 0.551 / max 0.655 m`;
   - `edge retrace (naip, widen, ... shift pre-compensated): widths 9.19..21.62 -> 9.19..21.62 m (change -0.34..+3.35 m), the line moved -0.47..+1.11 m`;
   - `edge retrace (naip+lidar, agree, ... shift pre-compensated): widths 9.19..21.62 -> 9.46..21.62 m (change -1.78..+1.66 m), the line moved -1.10..+0.97 m`;
   - `measured surface ...: off the measured line p50 0.176 / max 1.359 m ... bank max 18.33 %`;
   - `milford-road-course: 6537 pts, lap 4928 m, widths [9.46, 13.51, 21.62] m`.
   md5 of `data/centerline.local.json` on the Mac: `0923d812…`; `data/crossfall.lm.json`: `23f8a78f…`.
3. Read every gate (no threshold moves; any FAIL stops the install and comes back to the Mac):
   - drive_test (street): severe 0; kinks ~9 (1.8 / km, s 990-1,000) and vertex bumps ~5 [the audit's ribbon model;
     0.1.12 28 / 16]; excursion far ledges / drops not more than 0.1.12's 30 / 2;
   - edge_smoothness PASS, 0 ragged (the proxy: d2 p99 0.0075 / 0.0076, resid p99 0.0019 / 0.0017 m);
   - verify_kn5: 1ROAD under 65,535 writer vertices (0.1.12: 17,194, smooth-shaded; ~33,400 triangles here, so ~23,000
     expected [an estimate: 17,194 x 1.36]); audit_mesh CLEAN;
   - kn5_ground PASS; road_wear PASS (it registers on the line, which moved: compare its rubber centroid and tone r with
     0.1.12's 0.041 m / 0.959); houses PASS; kn5_textures PASS.
4. Measure the build where the Mac could not: `data/bespoke.report.json` (no rail post left out: G2, G3, G1, T1-T3);
   each rail's face to the built 1ROAD edge (as 0087's table: G2 / G3 >= 0.15 m, the Mac's proxy 0.167 / 0.176; T3 0.39 m
   at its closest); edge_report's rise / ground rows against 0.1.12's; the agree stretches on the gate OBJ (s 431-459,
   2,556-2,600, 4,113-4,144, 4,224-4,249) against `data/edge_retrace.json`'s runs[1] rows.
5. Report the numbers into this ledger. **No install** until Kevin says so; then his drive is the verdict (the NW corner,
   the s 2,550 gore, the bottom service-road mouths, the front straight).

(Runbook 0091-1 is superseded by the combined one below: 0.1.13 carries both 0091 and 0092.)

## 0092 on this line (Mac, 2026-11-19, branch claude/milford-0.1.13-20261119)

Ledger 0092 owed "If the line or the widths move: re-run runoff_pads.py --write". The intake's dry run on the merge
(843cd8a2 + 5f227e29) writes the same line as 0091 alone (`data/centerline.local.json` md5 `0923d812…`, crossfall
`23f8a78f…`): 0092 changed no intake input. Two of 0092's readers took `data/centerline.local.json` for the lane, which
with `lm_intake.line_precomp` it no longer is: the intake's line sits outside every bend so that the assembler's smoothing
lands on the trace (0.21 m p50 / 0.80 p90 / 2.27 p99 / 4.25 m max off the built line, the worst at the s 1,000 hairpin;
on 0.1.12 the same file sat 0.12 / 0.43 / 0.98 / 1.68 m off its own built line). Both now read the assembler's line (the
route's own smooth of that file, +- widths / 2):

**The run-off pads** (`source/runoff/scripts/runoff_pads.py`, re-run with `--write --line <the dry run's line>`; the
committed `data/centerline.local.json` untouched):
- Outlined on the intake's line, pad R0355 (the NW corner's inside) lay 0.92 m onto the lane and 7 quads folded. On the
  assembler's line: 0 folds after one row dropped where the offset curve turns back on the inside of the NW hairpin
  (R 25 m, 10-14 m off the edge: R0356, `rows_dropped` 1), and every kept pad that meets the lane starts 1.83-1.90 m off
  the built lane edge (LIP_M 1.9; the edge strip ends at +1.3 m). The committed pads against 0.1.13's built edge would
  have stood at 0.55 m (s 993), 0.98 m (s 1,169) and 1.15 m (s 394): on the edge strip.
- **The same 24 blobs, the same 19 kept and 5 left out** (no blob changed side; 0 overlaps). Outlines against 0092's:
  IoU p50 0.89 (min 0.71, L3500 -> L3510, 168 m2; R0993 -> R0998 0.83, 660 -> 580 m2); 1,105 m2 only in 0092's, 837 m2
  only in the new; vertices moved p50 0.03-1.29 m per pad; ends moved by up to 12 m where a blob's pixels now project to
  other stations (R0356 starts at s 256, not 268). Kept area within 30 m 15,252 -> 15,160 m2.
- The keys carry the new stations: runoff_R0125, L0338, R0356, L0395, L0883, R0998, L1175, L1530, L2508, L2588, R3239,
  R3370, R3453, L3510, R3883, L4359, R4375, L4512, L4775 (left out: L3717, L3770, L3874, L3939, L4385). Only
  `scenery.bespoke.pads` changed in the config. The record carries its line's md5 (`0923d812…`), and
  `tests/tools/test_milford_ground_0092.py` now reproduces it off the intake run into an empty workshop.

**The corridor** (`tools/lidar_ground_patch.py`, corridor patches only: Milford's alone): `in0_m` 9 m read off the
intake's line weighted lattice nodes as close as 6.18 m to the built lane edge (1,305 nodes inside drive_test's 9 m
excursion reach, 53 inside 8 m; on 0.1.12's line 8.08 m, 730), the band 0092 kept off the lidar because seating it moved
a model of 0.1.5 from 0 gated drops to 5. Off the assembler's line: 9.00 m, none inside. 318,126 nodes weighted (0.1.12:
317,872).

**GrassFX** (`tools/plan_grassfx_aerial.py`, not changed: it reads the intake's line for its 30 m near band, a look, not
a gate): 2,656 near cells, 2,090 rectangles on 0.1.13's line (2,638 / 2,066 on 0.1.12's with the new pads).

## Runbook 0091+0092 (PC): Milford 0.1.13 — one rehearsal, NO install without Kevin's word

1. `git fetch && git checkout claude/milford-0.1.13-20261119` at the head the orchestrator pushed; `git status` clean
   (`GIT_LFS_SKIP_SMUDGE=1` is fine: the draft rebuilds loop.blend). The lidar grid is committed
   (`source/lidar/milford_lidar_1m.npz`, 942,695 B): no lidar fetch, no network in the patch step.
2. The TreeFX models into `tracks/milford-road-course-lm/source/trees/` (Oak3 `24111ede…`, SycamoreV2 `7010d61f…`, else stop;
   never commit a .bin). ENG = `eng_mflm_017` (0.1.12's) or the install's.
3. Rehearse from an EMPTY workshop:
   `ENG=<ENG> SHIP_PROJ=D:/k10-scratch/milford_0113_reh AIROSO=<checkout> PYTHONUTF8=1 bash tools/ship_track.sh milford-road-course-lm --no-install`.
   The log must show, in order:
   - the intake (0091; the Mac's dry run, byte-equal when the inputs are):
     - `resampled every 0.75 m: 1635 -> 6537 points`;
     - `line pre-compensated for the assembler's smoothing (sigma 10.0 pts x 2): points moved p50 0.201 / max 3.231 m outward; lap 4901.8 -> 4927.4 m`;
     - `edge fit (judge, ...): 0 samples rejected` (0.1.12: 2; at 0.75 m rows the s 2,942 dip is no longer a 1-2 row spike);
     - `widths smoothed (Gaussian sigma 10.0 m; 691 rows held for a widen retrace, 160 blended): changed p50 0.044 / p99 0.551 / max 0.655 m`;
     - `edge retrace (naip, widen, ... shift pre-compensated): widths 9.19..21.62 -> 9.19..21.62 m (change -0.34..+3.35 m), the line moved -0.47..+1.11 m`;
     - `edge retrace (naip+lidar, agree, ... shift pre-compensated): widths 9.19..21.62 -> 9.46..21.62 m (change -1.78..+1.66 m), the line moved -1.10..+0.97 m`;
     - `measured surface ...: off the measured line p50 0.176 / max 1.359 m ... bank max 18.33 %`;
     - `milford-road-course: 6537 pts, lap 4928 m, widths [9.46, 13.51, 21.62] m`;
     - md5 `data/centerline.local.json` `0923d812…`, `data/crossfall.lm.json` `23f8a78f…`. If they differ, stop: the pads,
       the corridor and every station below were measured on the Mac's line.
   - the ground patch (0092; **shifted by 0091's line**):
     - `draft: the declared patches' lidar ground off the committed 1 m grid`, then
       `[lidar_patch] corridor: 812 x 1184 nodes of the 1 m grid, 275249 read, 42877 filled from their neighbours, 318126 weighted`
       (0092-1 said 275331 / 42541 / 317872, on 0.1.12's line and off the intake's line) and
       `[lidar_patch] culvert_4349_w: 26 x 19 nodes of the 1 m grid, 409 read, 26 filled` (unchanged);
     - `[ground-patch] corridor: TERRAIN <n> -> <n + ~83,000> vertices ..., ~99,000 seated ..., largest move ~7.9 m` and
       `[ground-patch] culvert_4349_w: ... +~1,700 vertices ... largest move ~4.3 m` (0092's model on 0.1.5's loop.blend;
       the corridor's nodes moved by 0.1 %, and TERRAIN's own count moves with the 0.75 m road rows: not modelled);
   - the pads (0092; **re-outlined on 0091's line**): `[bespoke] pad ride_pad: ... cells` and 19 `[bespoke] pad runoff_...`
     lines with the keys above (runoff_R0125 ... runoff_L4775), no `self-check FAILED`;
   - seat-pads: `[seat-pads] PADAPRON_0 -> 1RUNOFF_apron_0 ...` through `PADAPRON_19 -> 1RUNOFF_apron_19`, `ground over 0`
     each (the same 20);
   - grassfx: `[grassfx] 100 x 131 cells of 12 m, 2656 of them read as 4 cells of 6 m (within 30 m of the lane edge); ...
     2090 rectangles, 2090 kept` (0092-1: ~2,640 / ~2,060 on 0.1.12's line; the Mac's run on this config and line);
   - `SHIP OK`, no force.
4. Read every gate on the BUILT artifacts (no threshold moves; any FAIL: stop, no install, report the rows):
   - `drive_test.full.json` (street): severe 0; kinks ~9 (1.8 / km, s 990-1,000) and vertex bumps ~5 [0091's ribbon
     model; 0.1.12 28 / 16]; `excursion_drops` / `excursion_far_ledges` not more than 0.1.12's 2 / 30 (0092: the sweep's
     reach is left as built, now 9 m off the built edge everywhere; 0091 moves the lane outward in the bends, so the reach
     reads other ground: not modelled — any new gated drop, report its station and offset);
   - `audit.json` CLEAN; `edge_smoothness.json` PASS, 0 ragged (0091's proxy: d2 p99 0.0075 / 0.0076, resid p99
     0.0019 / 0.0017 m);
   - verify_kn5: 1ROAD under 65,535 writer vertices (0.1.12 17,194 smooth-shaded; ~33,400 road triangles here, ~23,000
     expected [estimate]); `kn5_textures.json` PASS with 1RUNOFF's `building_diffuse.jpg` / `building_normal.jpg` embedded;
   - `kn5_ground_check.full.json` PASS, `seating.walls` against 0.1.12's, and report `seating_info.walls_trunk` /
     `walls_rest`;
   - `house_seat_check.json` PASS; `road_wear_check.json` PASS (it registers on the line, which moved: report the rubber
     centroid and tone r against 0.1.12's 0.041 m / 0.959);
   - the road kn5's size against 0.1.12's 42,337,727 B: +4-6 MB from 0092 [its model] plus the road's +36 % triangles
     (not modelled in bytes); the prep's time.
5. Measure where the Mac could not: `data/bespoke.report.json` (no rail post left out: G1-G4, T1-T3); each rail's face to
   the built 1ROAD edge (G2 / G3 >= 0.15 m: the Mac's proxy 0.167 / 0.176; T3 0.39 m at its closest; G1 3.64 m); the 19
   pads' inner edges on the gate OBJ (the Mac: 1.83-1.90 m off the lane edge where they meet it); the agree stretches
   (s 431-459, 2,556-2,600, 4,113-4,144, 4,224-4,249) against `data/edge_retrace.json` runs[1]; edge_report's rise /
   ground rows against 0.1.12's.
6. Report every number of steps 3-5 into this ledger. **No install** until Kevin says so; then his drive is the verdict:
   the edges at the NW corner, the s 2,550 gore and the bottom service-road mouths; the front straight; the hillsides past
   the run-off (s 1,000-1,225, the s 4,350 culvert from the left); the run-off pads (driven onto: paved, not grass); grass
   at the pad edges and none through the ride pad; B's softer edge. VERIFY IN-GAME.

## Open, for Kevin

1. **Gap 7's trade** (the front straight): 12 / 12 is in the config. Jerk p95 48.6 -> 40.9 m/s3 (36.5 at 1.5 m rows),
   the left edge's median gap to NAIP's paving 0.39 -> 0.50 m. 8 / 10 keeps 0.1.12's widening at 0.1.12's jerk (49.6);
   12 / 15 removes the jerk the retrace added (33.8, the no-retrace floor 34.3) and gives back 0.17 m more.
2. **Fix D** costs +36 % road triangles for a gate artefact nobody feels. The alternative, drive_test's own opt-in
   `drive_test.vertex_kinks` (read the slope on each wheel's own travel), is a gate method: his call.
3. **The 2.9 mi loop.** Every station here (the agree spans, the front straight's) is on this 4,887 m layout's line; a
   new layout needs them located again (the spans are where width_taper widened: one script).
4. Not reached: the far edge at s 2,571-2,600 (right) and 2,655-2,676 (right) — only one sensor reads it there (or the
   two disagree by 1-4 m), so the agree record leaves today's edge. A NAIP year with less shadow would decide them
   (the audit's §5, a download: his yes).

---
id: 0087
title: Ragged road edges on Milford and Sand Creek — the built edge measured, its sources found, the outliers cut
status: in-progress
scope: engine (tools/edge_fit.py, tools/edge_smoothness.py, lm_intake.edge_fit), track:milford-road-course-lm
layer: engine
train: -
---

## Request (Kevin, 2026-11-07)

> "These are getting really good. Some of the curves and straights on Milford and sand creek have messy edges, we need to
> figure out how to cut inaccurate outliers out of the data set, but keep accurate ones. Milford should very smooth edges
> and they're ragged in places. Sc has it, and LM to a lesser degree."

Also 2026-11-07, on names: "Get rid of Lm Version from names, nothing should be on any other engine now" / "LM is the
airoso engine". Branch `claude/milford-edges` from `48daf25a` (Milford 0.1.2), version **0.1.4** (0.1.3 is the vegetation
pass on `claude/milford-vegetation`).

## 1. The raggedness, measured on the built roads (`tools/edge_smoothness.py`)

New tool, stdlib only, on the built `data/track.obj` (L5). For each reference line (the gate centre line; with
`--connectors` every connector, smoothed as the assembler smooths them) and each side, every 1 m a ray from the line along
its normal reads the first **1ROAD boundary** crossing (the lane edge) and the next **1KERB_sidewalk boundary** crossing
(the edge strip's outer lip). That gives the edge's offset d(s). Per sample: **d2** = d(s-1) - 2 d(s) + d(s+1) (the 1 m
second difference: a notch, a kink) and **resid** = d - a robust local-quadratic fit of d over +-8 m (tricube, bisquare,
3 iterations). A sample more than 1.5 m off the line's half width is a mouth / flare: counted, never judged. A **ragged
stretch** is a run of samples with |resid| > 5 cm or |d2| > 4 cm (merged across 4 m gaps).

| build | lane edge \|d2\| p95 / p99 / max | lane edge \|resid\| p95 / p99 / max | ragged stretches (lane / strip) |
|---|---|---|---|
| **Milford 0.1.2** (Mac c4 = the installed head 48daf25a's build) | 2.8 / 4.5 / 7.9 cm | 4.6 / 8.4 / 14.6 cm | **163 / 166** |
| **Sand Creek 0.2.6** (Mac rr2 = 5dc7fc88's build), lap + 88 connectors | 0.07 / 4.9-6.7 / 184-227 cm | 0.04-0.07 / 6.8-8.3 / 118-289 cm | **423 / 271** |
| **Lake Murray v4** (its build record: no Mac build exists, see §1.3), lap + 34 connectors | 0.15 / 2.1 / 77 cm | 0.29 / 7.7 / 36 cm | **125** (113 on the lap) |

### 1.1 Milford: where

The built lane edge is **exactly** the record's half width about the smoothed line: d - w/2 is within 2 mm at every one
of 9,774 samples (p1 -0.001, p99 +0.001 m). So every notch in the edge is a notch in `widths_m`, and **both sides move
together** (the ribbon is +-w/2): the left and right edges carry the same jitter mirrored. The worst stretches (lane edge,
resid; the strip's outer lip follows the lane edge to the millimetre):

| s (m) | side | resid | d2 | where |
|---|---|---|---|---|
| 4,268-4,274 | right | 14.6 cm | 5.0 cm | the bottom straight before the SW corner (the newer dark patch) |
| 1,232-1,236 | left | 12.0 cm | 7.7 cm | the serpentine exit fork (the trace's ZONES smoothing, `finalize.py`) |
| 3,547-3,550 | both | 11.9 cm | 3.1 cm | the east side |
| 425-429 | right | 11.7 cm | 6.8 cm | the NW apron (ledger 0069's `apron_corner.py` splice) |
| 861-864 | right | 11.3 cm | 7.5 cm | the hairpin approach |
| 2,956-2,959 | left | 11.7 cm (strip) | 3.3 cm | the NE corner |

The 50 m bins worst on the lane edge sit all round the lap (s 400, 600, 850, 950, 1,200, 1,250, 1,550, 2,800-2,950, 3,350,
3,500-3,550, 3,900, 4,100, 4,250): 10-15 cm wobbles over 3-6 m, everywhere, not a few bad points.

### 1.2 Sand Creek: where

The lap's edges are smooth where the street is one width (p95 under 1 mm); the raggedness is concentrated at width changes.
`edge_smoothness` + `/Volumes/Drive/codex/edges_work/scripts/sc_causes.py` sort the 423 lane-edge stretches:

| cause | stretches | resid max: median / p90 / max |
|---|---|---|
| at a mouth (within 25 m of a `mouths.json` cut) | 282 | 32 / 34 / 86 cm |
| the width record steps there (built edge = record, \|d - hw\| < 2 cm) | 96 | 8 / 31 / 121 cm |
| the built edge leaves the record (a weld, a pad, a divider) | 36 | 20 / 82 / 289 cm |
| facets on a curve | 9 | 2 / 3 / 3 cm |

Worst: lap s 2,286-2,300 right (2.9 m, the 56th merge's 42 m corner flare, ledger 0079 item 3), s 5,786-5,800 right
(1.2 m: the width steps 4.3 m a side in 14 m), s 1,233-1,253 left (1.2 m off the record: the 50th / Dahlia pad),
s 5,823-5,842 left, s 8,586 right (86 cm at a mouth), s 598-614 both (82 / 72 cm at the 50th / Ash pad's flare).

### 1.3 Lake Murray v4: to a lesser degree

No Lake Murray build exists on the Mac (none of the workshops holds its track.obj). Its edges are built by the same ribbon
(+-w/2 about the smoothed line; Milford's built OBJ proves it to 2 mm), so the same metric on its build record
(`data/finished_centerline.json`, and every connector at the assembler's sigma 1.5) measures them, mouths aside (welds are
not in the record): p95 |resid| **0.29 cm** against Milford's 4.6 cm. The 125 stretches are its junction flares' corners
(lap s 2,267 35.9 cm, s 4,531 34.9 cm, s 8,220 / 8,253 25 cm, s 4,501 20 cm, s 13,347 19.7 cm) and one connector,
`north_J5_jackson_north` (28 cm). Nothing changed there (§6).

## 2. Where each track's edge comes from, and what makes each ragged stretch

### Milford (the width series, end to end)

1. `tracks/milford-road-course/source/trace/finalize.py:33-51` `scan()` and `:88` `raw_width_m`: perpendicular scans of a
   colour-classified paved mask on NAIP 2022, every 2 m, in **0.5 px = 0.25 m steps** (`range(-90, 91)` x 0.5 px x
   0.5 m/px). Every width is a multiple of 0.25 m before anything else touches it. (`:92-94`'s own running median is
   written as `width_m` and not used downstream.)
2. `to_fixes.py:16-24`: the raw widths clamped to 9-16 m, aprons (> 22 m) and gaps filled from the nearest, then a
   **running median over 25 stations (+-24 m)**. A running median of quantized, noisy samples is a staircase: flat runs
   joined by 0.25 m steps that flip back and forth where the true width sits between two levels. The 16 m clamp also
   holds the front straight (s 0-150, 4,530-4,890) at 16.0 m flat.
3. (the clamp's 16 m is scaled by F in step 4: the front straight reads 16.0 m in the record.)
4. `unsquash_frame.py:34-41` (ledger 0062): each width rescaled by its heading from a +-5-fix tangent, `w * F / hypot(tx,
   F ty)` (F = 1.357): the steps grow to 0.25-0.34 m and pick up the tangent's own wobble.
5. `apron_corner.py` (ledger 0069): fixes 383-424 re-laid by hand: two splices (s ~425, ~440).
6. `tools/lm_engine_intake.py:330-365` `width_taper` (0.1 m/m a side, widening only) and `:568-598` the 1.5 m linear
   resample: each step becomes a 1.5-3 m ramp, the kink at each end of it.
7. The assembler (`scripts-v021/blender/build_loop_blend.py:1226, 1293`, `geometry/ribbon.py:25-67`) sweeps +-w/2 per row
   about the line it smoothed (sigma 6 m, 2 passes). **It never smooths a width.** The line is smooth; the widths are not.

**The cause of every ragged Milford stretch is (1), (2) and (4): 0.25 m quantization through a running median and a
heading rescale**, spread by (6). Not a bad sample: `edge_fit` judged every row of the trace against its own robust fit and found **one**
1-2 row spike on the whole lap (s 2,942, 18 cm; the lidar does not support it on the left, does on the right). The
trace has no outliers left to cut (the medians removed them); it has a staircase.

### Sand Creek (OSM widths, flared)

- `scripts/gps/widths_from_osm.py:205` `pavement_width`: one width per OSM way from its tags (lanes x lane width): the lap
  holds 163 distinct widths, 1,414 rows at 11.0 m, 317 at 7.5, 313 at 12.0, 236 at 16.5, 236 at 10.0.
- `:270 / :499` `_smooth(win 9)`: a 9-point moving average at 3 m spacing: every class change is a 27 m linear ramp with a
  kink at each end.
- `:404-435` `flare_widths` (applied at `:523`): every junction and every "hard route corner" (`detect_turn_corners`,
  `:335`) widens the ribbon to the junction's pavement size within +-size/2, then a straight 7 m taper: a trapezoid,
  four kinks per side, **on both sides at once** (it is a width). 30 lap bumps over 1 m: a street joins both sides at 4,
  one side at 5 (there the far side bulges **6.5 m median, 15.7 m max** where no street is), no mouth record at 21 (pads
  and corners).
- After the assembler: `tools/weld_mouths_blend.py` (mitre + warp at every mouth) and the measured pads move the built
  edge off the record (the 36 "built edge leaves the record" stretches).
- Its connectors: OSM widths, `lm_intake.connector_widths` / the lidar profiles (ledger 0079 round I).
- So Sand Creek's ragged stretches are **flare shapes and class steps**, plus the welds' and pads' joins; there is no
  noisy per-station measurement to robust-fit. A robust fit there would flatten real junction pavement: a dry run of
  `edge_fit` (judge, +-15 m, no evidence file) moves the lap's widths -4.8..+3.6 m. **Not proposed for Sand Creek as is**
  (§7).

### Lake Murray

The same OSM + flare stages (its widths are `scripts.gps.widths_from_osm`'s, the lap's flares the `flare_widths`
trapezoids); its worst stretches are exactly the flare corners listed in §1.3.

## 3. The fix: `tools/edge_fit.py`, in the data handling, opt-in (`lm_intake.edge_fit`)

`tools/lm_engine_intake.py` (after the resample, before the write) takes `lm_intake.edge_fit {"evidence", "mode",
"fit_half_m"}`; absent, nothing runs (Lake Murray runs no intake at all; no other config names the key,
`tests/tools/test_edge_fit.py::test_both_are_opt_in`). It smooths the line exactly as the assembler will
(`scripts-v021/geometry/smooth.py`, the port's `route.smooth_*`), then per side:

1. **The data set.** The trace's half width at each 1.5 m row, and the **measured edge points**
   (`tracks/milford-road-course-lm/source/edges/edge_evidence.json`, `measure_edges.py`): every 1 m and both sides, the
   steepest outward rise of excess green on NAIP 2022 (8,239 points, contrast > 15 [measured: the p10 along the lap is
   7-10, shadow and aprons]) and the dark-to-bright step in the **2017 lidar's ground-return intensity** (8,237 points,
   contrast > 3,000 [measured: p10 1,400-2,800]). The two are put in one frame first: over 5,397 stations where both read
   an edge within 1.5 m, naip - lidar = **-0.12 m E, +0.33 m N** (NAIP's registration against the lidar) and **+0.26 m**
   outward (split between them: which one reads the true edge at 0.6 m GSD is unresolved) [all three measured]. Each
   point is owned by its nearest row; it reads as an offset on that row's normal.
2. **The fit.** A robust local quadratic of the edge offset along the line (LOESS): half window **15 m** [invented: at
   +-10 m the staircase still left 14 samples over 5 cm, at +-15 m none; a real width change on this circuit runs
   20-50 m], tricube in station, Tukey bisquare on the residual (c = 4.685 sigma, sigma = 1.4826 MAD, floor 5 cm
   [invented]), 3 iterations.
3. **The rule (Hampel).** Every sample over **3 sigma** [the textbook cut] is a candidate. Consecutive candidate rows of one
   source form a run:
   - **a spike** (1-2 rows, Kevin's "one or two samples"): **cut**, unless the evidence near it (the median of the points
     owned by rows i-2..i+2, >= 3 points) sides with the sample over the fit: then **kept** ("kept_spike_supported").
   - **a sustained change** (3+ rows): **kept** (a corner-exit widening, a gore flare, a taper), with its support
     recorded (supported / unsupported / no evidence).
   - in `"fit"` mode only: a sustained trace run the dense evidence contradicts is cut, and the evidence builds the fit.
   Every candidate is written to `data/edge_fit.json` with its station, side, source, value, fit, residual and reason.
4. **The width** is fit_left + fit_right; the line is not moved.

**Two modes, and which one ships.** `"judge"`: the trace is the data set and the evidence only judges its candidates.
`"fit"`: the evidence enters the fit (weight 1 a point against the trace's 0.15 a row) wherever it is dense, both sensors
read the edge, their window medians agree within 0.6 m [invented] and scatter under 0.5 m [invented]. Measured on
Milford's line:

| mode | edge to the measured points, median (L / R) | edge moved | width record d2 p99 / resid p99 / max (1 m) | new short wobbles |
|---|---|---|---|---|
| as built (0.1.2) | 0.73 / 0.72 m | - | 4.5 / 8.5 / 11.9 cm | - |
| **judge, +-15 m (0.1.4)** | **0.73 / 0.72 m** | **-0.13..+0.20 m** | **1.2 / 0.4 / 1.0 cm** | none |
| fit, +-15 m | 0.61 / 0.61 m | -2.1..+1.6 m (width) | not built | 65 stretches where the width moves > 0.3 m, most 3-20 m long (the seams between trusted and untrusted windows) |

The sensors agree well enough to be trusted on only ~21 % of the lap (677 / 686 of 3,268 rows a side); elsewhere they
disagree (tree shadow on the east side, the aprons, the painted edge line) and the fit flips between evidence and trace,
which makes new ragged edges, the thing being fixed. So **0.1.4 ships `"judge"`**: smooth edges where they were, within
0.2 m of the trace everywhere. Its residual to the real edge is unchanged, and that is the honest result: Milford's lane
edges sit 0.7 m median off the measured pavement edge, which is a trace question, not an outlier (§7, Q1).

The one spike on the lap: s 2,942, both sides 0.18 m under the fit for 2 rows (3 m). The left side's evidence reads the
fit (cut, "spike"); the right side's reads the narrower edge (kept, "kept_spike_supported"). 0 sustained candidates.

## 4. Milford 0.1.4 (Mac, an EMPTY workshop `/Volumes/Drive/codex/edges_work/mf/c5`, `--no-install`, no force)

Built from this worktree with ENG = `/Volumes/Drive/codex/mf_work/eng2` (ledger 0082's: the engine-july snapshot + airoso's
assets/textures). Against 0.1.2 = Mac c4 (the installed head's build).

| gate | 0.1.2 (Mac c4) | **0.1.4 (Mac c5)** |
|---|---|---|
| drive_test, full (street) | PASS: ground on top 0, severe steps 0, bumps 0.0 /km, slope kinks 6.34 /km, daylight gaps 0, obstructed 0 | **PASS, every row equal** |
| audit_mesh (street, hard total) | CLEAN, every row 0 | **CLEAN, every row 0** (roads 65,218 v) |
| race drive_test / audit / no_route | exit 0 / 0 / 0 | **exit 0 / 0 / 0** |
| verify_kn5 + `--inis` | pass | **pass** |
| kn5_ground_check | PASS: walls seat-gap p95 -0.27; deck-vs-mountain max +0.086; road-over-ground 7 / 9,314 over 5 cm, p95 +0.021 m | **PASS**: -0.26; +0.073; 9 / 9,317, p95 +0.021 m (known ground noise) |
| kn5_textures | 40,714,845 B, 20 textures, missing 0 | **40,735,735 B, 20, missing 0** |
| houses | PASS (contact -0.323..-0.15 m) | **PASS, equal** |
| **edge_smoothness (new, hard)** | not in its chain; run on its OBJ: **FAIL** every row (p99 \|d2\| 0.045 m, p99 \|resid\| 0.085 m, 163 stretches) | **PASS** at the thresholds set from this build (GATES-CHANGELOG 2026-11-07, ⚠ a mirror) |
| edge_report (not a gate) | rise at 2 m p95 0.066 m; kerb at 1 m 99.5 % | 0.065 m; 99.5 % |
| ship | SHIP OK | **SHIP OK, no force** |

The mesh differs only where the widths moved: the densify pass re-cut 2,704 half-quads (c4 2,702), every other authoring
count equal. The c5 gate verdict above is re-run with the final GATE_DEFAULT on the c5 OBJ
(`/Volumes/Drive/codex/edges_work/es_c5.json`; c4's: `es_c4.json`); the chain's own `data/edge_smoothness.json` ran
under the earlier draft thresholds (0.03 / 0.04 m) and also passed.

**The road stays where it is apart from the edges.** The intake's line is byte-identical to c4's
(`centerline.raw.local.json` points: max difference 0.0 m); only `widths_m` changed (max 0.34 m a row, both sides
together; each edge -0.13..+0.20 m).

**Edge jitter and the real edge, before / after (lane edge, the built OBJ):**

| lane edge, built OBJ (left / right) | 0.1.2 (c4) | **0.1.4 (c5)** |
|---|---|---|
| \|d2\| p95 / p99 / max | 2.8 / 4.5 / 7.9 cm (both) | **0.7 / 1.2 / 2.0 cm** |
| \|resid\| p95 / p99 / max | 4.7 / 8.5 / 12.0 cm ; 4.5 / 8.4 / 14.6 cm | **0.23 / 0.38 / 1.1 cm ; 0.24 / 0.39 / 0.9 cm** |
| ragged stretches, lane edge / strip lip | 163 / 166 | **0 / 0** |
| samples not judged (mouth / flare) | 5 / 8 | 5 / 8 |
| edge to the measured points, median (p90) | 0.733 (2.03) / 0.72 (2.00) m | 0.73 (2.04) / 0.72 (2.00) m |
| each edge moved | - | -0.13..+0.20 m (median 0.0) |

The last two rows are the intake's (`data/edge_fit.json`, the width record; the built edge is the record to 2 mm, §1.1).
The jitter is gone; the distance to the real edge is unchanged, as `"judge"` intends (§3, §7 Q1).

**The one spike, as built.** s 2,942: the left side's 2 rows are cut, the right side's kept (its evidence reads the
narrower edge). Kept is kept in the data set, not in the shape: a +-15 m fit cannot draw a 3 m feature, so the kept dip
reads under 1 cm in the built right edge (its \|resid\| max anywhere is 0.9 cm). For a 1-2 row run the verdict only
decides whether the sample pulls the fit; the verdicts that change geometry are the sustained ones (none on this lap).

## 5. Stills (Blender EEVEE, NAIP's sun, the same cameras on c4 and c5; `/Volumes/Drive/codex/edges_work/`)

`source/edges/edge_stills_blend.py` on each build's split scene, at the four worst stretches of 0.1.2: `bottom_straight`
(s 4,271 right), `serpentine_exit` (s 1,234 left), `east_side` (s 3,548 left), `hairpin_approach` (s 862 right). Per spot
`_low` (the eye 1.0 m over the lane, 1.5 m in from the edge, 22 m back, looking 18 m ahead at the edge) and `_top`
(12 m straight over the edge). `mf_c4_*` before, `mf_c5_*` after. Also the NAIP overlays `ov_*.png` / `fov_*.png`
(red: the built edge, yellow: NAIP's edge, cyan: the lidar's, green: the `"fit"` mode's edge).

Rendered 2026-11-07 (`stills_c4.log`, `stills_c5.log`: exit 0, 8 stills each): `/Volumes/Drive/codex/edges_work/
mf_c4_<spot>_{low,top}.jpg` and `mf_c5_<spot>_{low,top}.jpg`.

- `bottom_straight_top` (the worst stretch of 0.1.2, s 4,271 right): c4's painted edge line and the strip's outer lip jog
  side to side down the frame (one jog halfway down reads at a glance); c5's line and lip run straight.
  A small step of a few centimetres is still visible on c5's strip lip about a third of the way down: the
  ground seam (`strip_seam_blend.py`) or the ground cut along the lip, not the lane edge (the gate reads the lip's
  \|resid\| max 1.3 cm). Not chased in this pass.
- `serpentine_exit_low` (s 1,234 left, the driver's eye): c4's edge line kinks in the foreground; c5's curves cleanly
  through. Everything else in the frame (rails, tyre wall, trees) is unchanged.
- `hairpin_approach_top` (s 862 right): c4's line and lip both kink a third of the way down; c5's sweep through in one
  curve.
- `east_side_top` (s 3,548 left): c5's edge line is straight; where the grass meets the strip's outer lip there are two
  small notches (the ground's cut against the lip, the same ground-side effect as the step on `bottom_straight`), not
  the paved edge.

## 6. Lake Murray unchanged

- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`: **empty** (and against 48daf25a).
- Every engine change is opt-in by key: `lm_intake.edge_fit` (only Milford's port names it; Lake Murray runs no intake),
  the `edge_smoothness` gate (only Milford's ship.json names it). `tools/edge_fit.py` and `tools/edge_smoothness.py` are
  new files nothing else imports. `tests/tools/test_edge_fit.py::test_both_are_opt_in`.
- **Trim A/B** (`/Volumes/Drive/codex/edges_work/lmtrim/`, `edges_work/trim_ab.sh`): **byte-identical**: `connectors.local.json` `664da93b…`, `mouths.json` `b73b70f4…`, `median_bands.json` `f0c97952…`,
logs identical (`63af07cc…`); the same three md5s as ledger 0082's lmtrim2.
- **Tests** (`tests/run_tests.py`, the .venv python as `python` on PATH): **1,297 pass, 8 fail**, the known 8 (draft_equiv x5, registry_moves, bench_pad x2; ledger 0082's 1,291 + this
pass's 6 in `test_edge_fit.py`, all PASS). Log: `/Volumes/Drive/codex/edges_work/tests.log`.

## 7. Owed, and questions for Kevin

Neither Q1 nor Q2 is in 0.1.4: both are open (asked 2026-11-07, unanswered at this commit). 0.1.4 is the outlier cut and
the smoothing alone; the road's position against the real pavement is unchanged.

- **Q1 (Milford, the real edge).** The measured pavement edge (NAIP and the lidar, where they agree) sits **0.7 m median**
  off the built lane edge, both sides, and they agree well enough to trust on only ~21 % of the lap. Where they agree
  over long runs the built road is narrower than the paving: the front straight (s 0-150 and 4,530-4,890, the trace's 16 m
  clamp) by 1.5-3.5 m, which is where the rails G2 / G3 already stand 0-1.7 m past the lane edge (ledger 0082). Re-trace
  those stretches to the measured edge (a sustained, supported change: the rule keeps it), or keep the traced 16 m?
  Moving the lane edge also moves where the rails stand relative to it.
- **Q2 (Sand Creek).** Its ragged edges are the shapes in the record, not noise: the junction flares are trapezoids swept
  on BOTH sides (`widths_from_osm.flare_widths`), so at the 5 one-sided junctions the far kerb bulges 6.5 m median with no
  street there, and every OSM width class change is a 27 m ramp with a kink at each end. The fix that fits Kevin's rule is
  a measured one: the lidar curbs (ledger 0079 already reads them on Quebec) as edge evidence, flares one-sided and only
  where the paving is. Build after the side-street corners land (claude/sand-creek-grid-mouths)?
- **Q3 (the gate fleet-wide).** `edge_smoothness` stays Milford-only until Sand Creek's flares are measured shapes and the
  PC has run it on every installed track.
- **Owed: the install folder.** 0.1.4 keeps `milford_road_course_lm` (the coordinator, 2026-11-07); the folder becomes
  `milford_road_course` once, at the merge of this branch with `claude/milford-vegetation` (0.1.3), and that install
  removes the old-engine folder and the `_lm` folder from AC (Kevin: "We want to delete old copies from ac when installing
  new ones"). The repo folder `tracks/milford-road-course-lm` is renamed in the one pass after the current agents land.
- Owed: the PC rehearsal (runbook 0087-1); nothing installed.
- Owed: the stills are Blender, not AC (L12): Kevin's drive is the verdict.

## Runbook 0087-1 (PC): rehearse 0.1.4, NO install without Kevin's word

1. `git fetch && git checkout claude/milford-edges` (a clean checkout of the head below). The display name is now
   **"Milford Road Course (unofficial)"** (no "(LM engine)": Kevin 2026-11-07, "LM is the airoso engine"); the folder is
   still **`milford_road_course_lm`** for 0.1.4.
2. `bash tools/ship_track.sh milford-road-course-lm --no-install` (the workshop D:/k10-scratch/milford_lm). The intake
   prints `[lm_intake] edge fit (judge, source/edges/edge_evidence.json): 2 samples rejected ...`; compare
   `data/edge_fit.json` with the Mac's (the same verdicts: s 2,942 left cut, right kept).
3. Every gate row against the Mac's c5 table (§4), the new `edge_smoothness` row included; the road kn5's bytes against
   the Mac's (known ground noise only).
4. Report; **no install** until Kevin says so. When he does (and once 0.1.3 and 0.1.4 merge), the install goes to
   `milford_road_course` and removes `milford_road_course_lm` and the old-engine folder from content/tracks (parked in
   D:/k10-track-archive, never beside it).

## PC: rehearsal 0087-1 and the 0.1.4 install (2026-11-07)

- **Rehearsal** (a clean detached worktree at `5c588428`, an EMPTY scratch workshop `D:/k10-scratch/milford_lm_f3_reh`,
  ENG `eng_mflm_f2`, its 95 textures md5-equal to this head's except SOURCES.txt): SHIP OK, no force, 31 min. Every row
  is the Mac's c5: the intake's "2 samples rejected" (s 2,942: left "spike" cut 0/2, right "kept_spike_supported" 2/2);
  drive_test PASS (0 / 0 / 0.0 /km / kinks 6.34 / vertex bumps 16 / 0 / 0); audit CLEAN (roads 65,218 v); race 0/0/0;
  verify_kn5 + inis pass; kn5_ground_check PASS (seat-gap p95 -0.26, deck-vs-mountain max +0.073, 9/9317 p95 +0.021);
  kn5_textures PASS 40,735,735 B (the Mac's size), 20 textures, missing 0; houses PASS; **edge_smoothness PASS**, lane
  edge |d2| p99 1.19 / 1.22 cm, |resid| p99 0.38 / 0.39 cm, 0 ragged runs. kn5 md5 `5f7941e5…`.
  One count the ledger did not list: the G2 rail stands one more post (465 -> 467 m, 247 -> 248 posts, 48 -> 47 left
  out on 'lane'), walls 20,743 -> 20,783 v: the moved edge (the Mac: nothing to chase).
- **Install** on Kevin's word, asked here ("Install it (Recommended)"): from an EMPTY `D:/k10-scratch/milford_lm`
  (0.1.2's workshop parked as `milford_lm.0.1.2`), SHIP OK 22:32. 0.1.2 parked by the install in
  `D:/k10-track-archive/2026-11-07_223238/`. Installed = the workshop build (ui_track.json only); its kn5 = the
  rehearsal's, tangents only (170,458 values, max 1.79e-07). In AC: `milford_road_course_lm` 0.1.4, "doooom Michigan —
  Milford Road Course (unofficial)"; no other Milford folder.
- **Menu picture**: re-rendered from this build with the camera of 74de8b1's (s3, -0.5 EV; eye and look identical),
  committed at `source/ui/` and copied over the pack's preview.png (the old one in
  `D:/k10-track-archive/2026-11-08_001402_previews/`).
- This commit: the outputs the install synced back (ai/, data/, loop.blend) + the picture + `tools/menu_preview_*.py`
  (the same file as on every branch). Recorded in `fleet/ac-installed.json` on claude/ac-tidy.

## Milford 0.1.5 (2026-11-08): this branch merged with the vegetation pass; runbook 0087-2 = 0082-4

- `claude/milford-lm-015` merges ce98214 (this branch with the PC's 0.1.4 install records), `claude/milford-vegetation`
  (0.1.3) and `claude/milford-furniture-lm`. The edges keep the road edge and the intake: the Mac's 0.1.5 build
  (`/Volumes/Drive/codex/mf_work/v015/b1`, empty workshop, no force) has every road, kerb, grass, rail and building mesh
  equal to 0.1.4's (`mesh_diff`), `edge_smoothness` PASS at 0.1.4's numbers (lane |d2| p99 1.19 cm, |resid| p99 0.38 cm),
  and its intake line, `edge_fit.json`, drive_test and ai/ byte-identical to the PC's 0.1.4 records.
- The install folder owed above is done: slug and folder `milford_road_course`; the old-engine track's are
  `milford_road_course_v06` (S7). Details, the gate column (0.1.4 / 0.1.3 / 0.1.5) and **the one runbook for both entries,
  0082-4 / 0087-2**: `fleet/feedback/0082-milford-furniture-pass-1.md`, "Milford 0.1.5".

## Milford 0.1.6 (PC, 2026-11-08): the edge strip flush with the ground the prep leaves

Kevin (PC session, 2026-11-08 ~22:15): **"Milford still looks messy on the edges of the high speed curves"**.

**Measured on the installed 0.1.5 (`D:/k10-scratch/milford_lm`, its gate OBJ):**
- The lane outline is smooth: edge_smoothness resid p99 3.9 mm (max 1.1 cm), 0 ragged runs. The mess is not the outline.
- The circuit edge (`route.edge`, ledger 0078) grades the strip 0.15 m down over its outer 1.0 m.
- engine-july's prep (`build_kn5_loop._conform_and_reseat`) pins ground under 1ROAD only. Past the ROAD edge it holds a 3 m contact band at the lane edge's height - 0.02, then feathers 6 m.
- So the strip lies in a gutter with a wall of ground at its lip. At s 2,957 and 3,693, both sides: the strip -0.14..-0.15 at +1.25 m; the ground -0.05..-0.13 at +1.4 m and -0.02 at +1.8 m.
- Between strip_seam's points the ground's triangles climb over the strip's lower half. In Blender stills of the fast curves (s 2,594 / 2,798 / 2,957 / 3,693 / 4,355; R 146-296 m, ~155-220 km/h) that reads as saw teeth along the outsides.

**Fix (0.1.6, opt-in per track):** `route.edge.grass_clearance` -0.08.
- The strip's outer lip now stands 2 cm under the lane edge, level with the prep's band, not 15 cm under it.
- Rehearsed from an EMPTY workshop (`D:/k10-scratch/milford_016_reh`, ENG `eng_mflm_015`, branch `claude/milford-edge-strip-016` from 871fbde): SHIP OK, every gate green.
- The same stations now read: strip 0.00..-0.02, ground -0.02..-0.04 under it, -0.02..-0.03 past the lip. No gutter, no wall.
- The stills show the strip meeting the grass in a clean line: `tracks/milford-road-course-lm/source/stills/edges_015_vs_016.jpg`, 0.1.5 left, 0.1.6 right.
- Unchanged: drive_test 0 severe / 0 excursions, edge_report ground_3m median -0.027 (was -0.028), kn5_ground PASS.
- kn5 39,002,272 B (0.1.5: 39,006,968).

**Owed:**
- Install on Kevin's word: replaces `milford_road_course` 0.1.5 (archive by the family rule; re-render the menu picture).
- Kevin's drive is the verdict: the stills are Blender, not AC.
- The same circuit edge profile is on the other circuit ports (High Plains, Exotics, Pikes Peak, Pueblo, Aspen, Grand Junction); each needs the same check.

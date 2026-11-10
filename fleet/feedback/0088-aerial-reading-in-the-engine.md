---
id: 0088
title: Aerial reading in the engine — published maps for the route, kerbs and wear for the edges, lidar registration, measured pieces into layouts (scripts/aerial/engine)
status: diagnosed
scope: kind:circuit_port, kind:fictional_street_circuit; proof cases tracks/pikes-peak, tracks/exotics-racing-lv, tracks/high-plains
layer: engine
train: -
---

## Symptom (Kevin, 2026-11-07, verbatim, while Pikes Peak's infield was traced badly three times)

> "Those tracings aren't very accurate."
> "Follow curbs and road wear, it's easy for human eye"
> "how are you missing the dark areas that cars drive on? It's right there"
> "We may need to update our track detection skill"
> "I feel like this should be handled by the engine by now"
> "Why aren't you using actual track maps?"
> "Stop guessing"

Overnight: "Try to get as far as you can across the machines overnight". Standing rule: "I just want real".

## Evidence

- The skill on disk (`.claude/skills/aerial-tracing/SKILL.md`, before this entry) taught two-point screenshot georef,
  a largest-blob skeleton auto-trace, or a clicked `trace_px`: every one a point placed by eye or a guess.
- What worked was scattered in per-track scripts, each hard-wired to its track: Pikes Peak's registration, edge
  re-trace, map reading and lot band (branch `claude/pikes-peak-road-course` f11baae3, ledger 0085); the colour-blind
  kerb block reader (`claude/circuit-kerbs-lm`, 0081; `tools/aerial/naip.py` hard-codes EPSG 26913); robust edge fits
  (`claude/milford-edges`, 0087); Exotics' seeded line snap (`tracks/exotics-racing-lv/source/trace/`).

## Diagnosis

No engine stage owned aerial reading, so every track re-invented it, and the first attempt each time was an eyeball
trace. The methods that measured (edges at the sub-pixel step, kerbs first, maps registered by similarity with a
handedness test, the driven band on open pavement, lidar registration) were sound; they were not general.

## Fix: `scripts/aerial/engine` (new, opt-in; nothing existing changed)

One stage: orthophoto + optional lidar + optional published map(s) + optional hand sketch -> measured pieces and
layouts. `python -m scripts.aerial.engine <engine.json | project-dir> [--out DIR]`. A per-track
`tracks/<slug>/source/aerial-engine/engine.json` holds only data (files, ink colours, label / S/F / pit-lane pixels
read off the maps, published direction and lengths). Modules:

| module | what (generalised from) |
|---|---|
| `ortho` | the CRS from the image's own metadata: GeoTIFF tags (any EPSG via pyproj; 4326 / UTM built in by the Krueger series, any zone), crop-sidecar corners, projected bbox sidecars, tile georefs, two corner pins; a local ENU frame (`origin_from` the track's centerline.local.json); pixel <-> ENU by a cubic fit checked to < 0.01 px; the registration shift applied to every conversion |
| `register` | lidar wall surveys (tools/lidar_wall.py) as measured edges; the wall top on the image fitted `b + dE nE + dN nN`, bootstrap spread, applied at >= 1 pixel (0085 register_wall.py) |
| `channels` | pavement / kerb / white / edge-line / track-specific boundary-band scores; colours overridable per track (0085 naip.py) |
| `edges` | both edges on cross-sections: steepest fall of the pavement score (sub-sample), a kerb or edge line within 1.5 m inside takes precedence (its inner face), or painted boundary bands paired across the road; lidar edges where the image has none before them; openings, weak, shadow, outliers and junction mouths rejected and bridged; robust curvature-limited splines (closed loops wrap); residuals per side (0085 pieces.py / retrace.py; Exotics refine_trace.py's pairing) |
| `kerbs` | the colour-blind block reader and candidate scan (0081 kerb_offsets.py / kerb_blocks.py), colour runs along a fitted edge (0085) |
| `maps` | ink rules, outline, similarity ICP from every 10 deg in both handednesses, near-equal fits decided by how much of the course line lands on measured pavement then the S/F, the course band chained into one loop (stops and asks if it is not: `exclude_px`), local refit where a schematic strays off pavement (bounded), labels -> stations (0085 schematic.py / maps_route.py) |
| `band` | the dark driven band on open pavement, each side normalised to its own surface (0085 lot_band) |
| `route` | route line -> guide down the pavement's middle, held to the line by a corridor (0085 pieces.guide) |
| `network` | the first layout measured whole; later layouts share its measured road (within its half-width + 2.5 m) and measure only their own stretches; open-pavement runs (an opening >= 80 m with no lidar edge opposite) take the band; joins reported and blended; pieces cut where layouts part |
| `emit` | `<id>.centerline.geojson` (data/centerline.geojson's shape: the elevation -> projection -> LM intake chain reads it) and `<id>.source.json` (a track.config.json `source` block ship_track.sh's draft_aerial / build_aerial turns into the same line) |
| `stills` | clean overlays: one line, the aerial tinted to 78 %, nothing else; zoom sheets |

Route precedence (rules in the skill): published maps first; a sketch for shape only (direction from the published
course on shared stretches, or the config); the driven band where a route crosses open pavement; never a point by eye.

## Validation (no downloads; only imagery, maps and lidar already on disk)

**High Plains kerbs** (NAIP 2023 0.3 m crop `kerb_work/img/high-plains_2023_030.png`, its sidecar; the 20 colour-measured
runs and their eye spans from `kerb_offsets_calibration.json` on `claude/circuit-kerbs-lm`; the gate line
`data/gate_centerline.json`). `tools/aerial_engine_validate.py high-plains`:

| |stage - colour truth| (m) | median | p95 | max | ledger 0081 round 3 (tools/kerb_offsets.py) |
|---|---|---|---|---|---|
| in_m (20) | 0.15 | 0.35 | 0.48 | 0.16 / 0.34 / 0.48 |
| out_m (20) | 0.17 | 0.70 | 1.25 | 0.17 / 0.67 / 1.25 |
| width (20) | 0.21 | 0.85 | 1.11 | 0.21 / 0.84 / 1.11 |

The stage's reader against tools/kerb_offsets.py's own record: **0.000 m on in, out, s0, s1 for all 20** (the same
reader; the p95 differences are numpy's interpolated percentile against 0081's nearest-rank). The candidate scan over
both whole sides finds 13 of the 20 (as 0081: candidates, each still checked on its strip).
Record: `tracks/high-plains/source/aerial-engine/validation.json`.

**Pikes Peak** (NAIP 2023 0.3 m crop `kerb_work/img/pikes-peak_2023_030.png` + its sidecar; the 2018 lidar wall survey
`source/lidar/wall-survey/wall_right.json`; the two published maps in `pp_work/maps_dl` and Kevin's infield stroke in
`pp_work/sketch/routes`, all downloaded on his word for 0085, none committed). Reference: f11baae3's
`route_from_maps.naip.json` and `infield_pieces.naip.json` (read from `origin/claude/pikes-peak-road-course`).
`tools/aerial_engine_validate.py pikes-peak`:

| | stage | f11baae3 (0085) |
|---|---|---|
| registration to the lidar wall face | **E +0.09, N -0.41 m (0.42 m), sd 0.04, rms 0.16 / p50 0.12 / p95 0.32 m, 374 stations: applied** | the same, to the centimetre |
| RC map outline to wall face | rms 0.62 / p95 1.09 m, S/F miss 1.4 m, affine 0.47 m / axis 1.005 | the same |
| SCCA map | rms 6.90 / p95 11.36 m, S/F miss 6.5 m, affine 2.7 m / axis 1.072 | the same |
| handedness | RC's mirror fits the outline equally (rms 0.62) but puts 10 % of the course off pavement (89.7 % on vs 100 %); SCCA's mirror fits the outline BETTER (6.89) and is rejected the same way (88.4 % vs 92.8 %) | decided by labels / infield centroid |
| SCCA's line where it strays off pavement | 2 local refits applied (the top hairpin: scale 1.021, -1.1 deg, moved 11.9 m, 80 % -> 0 % off pavement; the NW: 1.013, -18 deg, 98 % -> 14 %), 2 refused (scale 0.88 / 0.83) | 1 refit at the top hairpin |
| do the maps agree? | 86.9 % of SCCA's line lies on the RC-measured road, covering 89.9 % of it | "both maps give the same route" |
| **RC-D lap** (from the painted S/F, CCW) | **2,211.8 m** (published 2,074 / 2,116: +137.8 / +95.8) | 2,217.8 +-54 m: **difference -6.0 m** |
| RC-D centre to centre | **p50 0.34, p95 3.28, max 9.8 m**; 120 m of the lap over 3 m: the service-road mouth on the back stretch, the NE diverge, the NW merge, where f11baae3 joins pieces straight over 6-9 m gaps | |
| **IF-K lap** (Kevin's infield stroke, shape only; direction as RC-D runs on the shared stretches) | **750.1 m** | 760.3 +-36 m: **difference -10.2 m** |
| IF-K centre to centre | **p50 0.33, p95 2.2, max 3.1 m** | |
| widths on f11baae3's pieces (stage minus f11, median / abs p50) | ne_lane +0.02 / 0.16, hairpin_w -0.16 / 0.27, diag_n +0.09 / 0.25, diag_s -0.15 / 0.17, arc_nw +0.08 / 0.24, bottom -0.06 / 0.48, s_curve +0.08 / 0.19 m (junction-wide c_road / west_n -3.3 / -0.9) | |
| corner stations, RC T1-T9 | 299, 529, 880, 1,109, 1,436, 1,586, 1,634, 1,699, 1,835 m | 299, 529, 879, 1,119, 1,437, 1,589, 1,636, 1,704, 1,842 |
| corner stations, SCCA 1-9 | 220, 925, 1,140, 1,415, 1,602, 1,649, 1,737, 1,791, 1,986 m | 220, 926, 1,152, 1,417, 1,605, 1,647, 1,743, 1,804, 1,993 |

RC-D's edges: left (the oval's inside edge, then the infield's) seen 69 %, residual p50 0.17 / p95 0.63 m, by
surface 2,314 / kerb 373 / line 348 stations; right seen 73 % (the wall's lidar face 2,576 stations, then the
infield's line 1,168 / surface 1,886 / kerb 141), residual p50 0.17 / p95 0.71 m. **The lot** (both maps' lines over open pavement): the open-pavement rule found two
runs (an opening over 80 m, no lidar edge opposite) and read the driven band there: 427 sections, 352 seen, band
width p50 8.3 and 10.2 m, limit residual p50 0.06-0.12 m, depth 22-35 grey levels; 24 m bridged straight on the lot's
north-east side, where 48 sections show no band 6 grey levels below both sides (0085 found the same side unseen and
bridged 64 m).
Pieces: RC-D is cut where IF-K leaves and rejoins it: rcd.p1 (the oval from the S/F, the NE lane, the hairpin),
rcd.p2 (diag, the lot, the bottom road: shared by both layouts), rcd.p3 (west road, sweeper, the oval back to the
S/F); IF-K = its own S-curve + C road east (measured, residual p50 0.20-0.23 m) + rcd.p2. Kerb candidates read along
RC-D: 35 runs, 885 m (candidates until checked on their strips). Stills: `tracks/pikes-peak/source/aerial-engine/out/`.

**Exotics** (the committed NAIP 2019 crop `naip_2019_exr.png` + its two corner control points; no published map on
disk, no sketch from Kevin). The circuit is painted on a lot: its edges are blue-grey bands (yellowness -18..+5 at lum
138-178, sampled) and red / white kerbs; `edge_kind: lines` pairs a band each side. The route is a stand-in sketch
made from the 2026-10-28 trace and degraded so it cannot carry geometry (a vertex every 30 m, each moved +-3 m;
`sketch_from_trace.json`), direction clockwise as the config infers it.

| | stage | 2026-10-28 trace |
|---|---|---|
| lap | **1,822.4 m** | 1,821.8 m (published "1.2 mi" 1,931 m) |
| centre to centre p50 / p95 / max | **0.60 / 3.2 / 6.7 m** | |
| width (asphalt between the bands' inner faces) | p50 11.0 m | band middle to band middle, floored 11.5, capped 20, smoothed: the stage's width + the bands' widths (p50 ~2.9 m) is within ~0.4 m of it |

The 3-7 m differences sit at the pit merge and the inner loops' junction mouths, where the trace filled from its
neighbours and the stage bridges by its fit. **Independence:** a second sketch (a vertex every 40 m, +-5 m, another
seed) gives the same lap to **0.21 m p50 / 0.43 m p95** (lap 1,822.6 m): the measurement does not come from the guide.
Records: `tracks/exotics-racing-lv/source/aerial-engine/{validation.json, independence.json, out/}`.

## Invented numbers (no gate changed, so none in GATES-CHANGELOG; listed here)

Carried from the per-track methods: the channel colours (0085), the edge finder's run / fall / band / weak / shadow /
outlier rules and the 4 m curvature limit (0085), the band's valley / sides / depth / width / jump (0085), the block
reader (0081 round 3), the ICP starts and handedness search (0085). New for the stage, all ⚠ invented: lidar
tolerance 2.0 m; a junction mouth = a surface edge 3.0 m past its 200 m baseline (kerb / line edges exempt); open
pavement = an opening of 80 m with no lidar edge opposite; band blend 20 m; near-equal map fits = rms within 1.5x
the best + 2 m; local refit where half of 15 m is off pavement, refused outside scale 0.85-1.15 or 20 deg; a later
layout shares a road within its half-width + 2.5 m (cap 10 m), own stretches under 10 m (or 30 m between two
stretches of the same layout) absorbed; joins blended over 25 m.

## What stays per track

- `engine.json`: the image and its sidecar; the maps' ink colours, `sf_px`, labels, `exclude_px` for a pit lane drawn
  in the course colour, the published direction and lengths; the S/F on the aerial; a boundary band's colour where a
  circuit is painted on a lot; lidar survey files. All read off the sources, none a coordinate of the route.
- Downloads: imagery, maps, lidar (Kevin's yes each time). The stage reads only what is on disk.
- The build: the measured line still goes through elevation, the LM assembler, every gate and Kevin's drive. Pikes
  Peak's 0085 owed list (the apron's slope, the infield ground, the lot's north-east side) is unchanged by this entry.

## Lake Murray unchanged

No existing file under `scripts/`, `tools/` or `tracks/san-diego-lake-murray/` changed (new files only, plus the skill
and this entry); nothing in a build path imports `scripts.aerial.engine`. `git diff origin/claude/fleet-lm-engine --stat`
lists only added paths and `.claude/skills/aerial-tracing/SKILL.md`.

**The output reaches the chain unchanged:** Exotics' `full.source.json` put in a scratch copy of the track's config
and run through `python -m scripts.aerial.build_aerial` (ship_track.sh's draft_aerial step) gives a centerline.geojson
of the same length (1,822.5 m), the same widths (p50 11.05 m) and the same line to 0.017 m p50 / 0.11 m max.

## Tests

`tests/aerial/test_engine.py` (14, all pass): synthetic images with known answers (a ring road with a kerb: centre
and width to 0.15 / 0.3 m, kerb inner face taken; a lidar edge overriding the image only where it is the boundary;
the dark band on a lot to 0.2 m; a map's similarity and handedness, and its mirror; a course band with a pit chord
refused until `exclude_px` drops it; kerb blocks across an edge to 0.15 m; a known registration shift to 0.03 m and
one under a pixel left alone; a guide down a road whatever side the line is drawn; the GeoTIFF CRS and UTM inverse
against pyproj to 1e-8 deg; the whole stage end to end on a synthetic track: lap to 3 m), plus the fixture
`tests/fixtures/aerial_engine/ppir_diag_2023_030.png` (a 280 x 290 px NAIP window of Pikes Peak's diag road; width
11.6-13.0 m, residual p50 < 0.25 m each side). Full suite (`python tests/run_tests.py`, the airoso venv): **1,291
passed, 8 failed, all known** (draft_equiv x5, registry_moves x1, bench_pad x2).

## Verification still owed

- Kevin's eye on the clean stills (`tracks/<slug>/source/aerial-engine/out/*_overall.jpg`, `*_zooms.jpg`).
- A track built from a stage output end to end (not done here: no builds tonight, by the brief).
- Exotics against a published map (none on disk).

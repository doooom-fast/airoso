---
id: 0086
title: "Sand Creek's grid streets don't connect to the main road, they float": square, sunk corners at every mouth
status: fix built on the Mac (0.2.7, m7d): SHIP OK, verify_kn5 TERRAIN POKE 0 (rr2 9); not installed
scope: tracks/sand-creek-lm (113 mouths of 0.2.6, 117 of 0.2.5); tools (opt-in keys only, Lake Murray unchanged)
layer: project + engine
train: -
---

## Symptom (Kevin, PC session, 2026-11-07, relayed verbatim, in order)

> "How are we doing on road grids? They don't connect to the main road very well at all, which is an old problem coming back hp"

Asked what a bad junction looks like, he picked **"Bump, step or lip"** and typed:

> "Doesn't connect, floats"

> "Actually LM works, it's SC"

> "Sand creek too but I haven't looked at today's"

He saw it on 0.2.5 or earlier; 0.2.6 is installed and not looked at yet. Lake Murray v4's side-street joins are fine by
his eye and are the reference for "works".

## Evidence (Mac, read-only, on the BUILT artifacts; L5)

Tool: `tools/mouth_survey.py` (new, diagnostic, not a gate). Built artifacts:
- Sand Creek 0.2.6 = `sclm_work/rr2` (the Mac's round-R build of the 0.2.6 config; its kn5_ground_check is the PC's
  installed numbers exactly: road_over_ground 27 / 11,781, p95 0.021, max 0.291).
- Sand Creek 0.2.5 = `sclm_work/rj2`.
- Lake Murray v4 = `sclm_work/rp_lmdt` (0.20.1 config, 32 mouths; road_over_ground 24 / 10,785, max 0.255, as the PC
  reported).

### 1. The old problem, and which of its fixes Sand Creek has

| Lake Murray's junction defect and fix | In Sand Creek LM 0.2.6? |
|---|---|
| 0041 (2026-10-09, "side street intersections, lots of hovering"): side-street ends 0.10-0.91 m off the host. Fix: `trim_connectors` lands each cut on the host's height and blends 30 m; later `weld_mouths` | **Yes.** verify_mouths: mouth line max 0.072 m (grid_primary_80, allowed), all others < 0.04 m |
| 0033 / 0036: the host's sidewalk swept across every mouth. Fix: `gap_mouths` deletes the host's curb strip over the connector's span + `GAP_CORNER_M` 3 m each side | **Yes**: 4,116 faces at 113 mouths. It is now half the problem (below) |
| 0054 Phase 5 (2026-10-14..18): `author_stubs_blend.py`: curb returns round both corners, the corner pavement under them, the corner ground refined and pinned (its "teeth of grass behind the returns" fix) | **No.** Sand Creek's grid streets are through streets, not stubs; nothing replaced it |
| 0054 P1 / P3: `author_aprons_blend.py` corner apron + `mouth_fill` (also deletes paint inside the apron) | **No** |
| 0078 round 5: `strip_seam`, so the ground stops burying the edge strip | **The lap and the pads only** (`tools/strip_seam_blend.py:60`), not the 88 grid pieces |

### 2. road_over_ground located (kn5_ground_check's own sampler, `mouth_survey.py --rog`; 27 of 11,781, every one placed)

- **20 at mouths.**
  - 15 in a mouth's corner: the host's pavement edge over the side street's sunk strip, 0.7-2.8 m along the host
    from the street's edge: 0.205 / 0.194 (grid_primary_35 at the lap, s≈2320), 0.166 (grid_primary_84 at the lap),
    0.116, 0.109, 0.104, 0.093, 0.092, 0.076, 0.074, 0.056, 0.052, 0.051 x 3.
  - 5 more at the I-70 bridge mouths of grid_primary_78 / 84 on the lap (s 5794-5820): 0.241, 0.161, 0.155, 0.155,
    and grid_primary_35's own edge (0.161).
- **4 on pad deck edges** over the lap's strip: colorado_50th 0.217, 50th_dahlia 0.152 / 0.144, 48th_colorado 0.055.
- **3 along grid_primary_7's edge** 20-100 m from its fork with grid_primary_6: 0.291 (the max), 0.083, 0.069. The
  deck stands 0.21-0.29 m over the grass with a second strip under it. Not a mouth; owed.

### 3. Every mouth, beyond verify_mouths (0.2.5, 117 mouths, reads the same: lip median 0.175 / max 0.327, bare 145.0 m, teeth 24.9 %)

| measured on the built OBJ | Sand Creek 0.2.6 (113 mouths) | Lake Murray v4 (32) |
|---|---|---|
| **corner lip**: host's road edge over the top surface just past it (b ≤ 0.15 m), within 6 m of the street's edge | median **0.175 m**, max 0.327; > 0.10 at 108 mouths, > 0.05 at **113**, both corners at 102 | median 0.033, max 0.163; > 0.05 at 8, both corners at 0 |
| **bare host edge** (grass > 5 cm under the road edge, b = 0.15) | 110 mouths, **138.6 m** | 5 mouths, 2.1 m |
| **turning wheel**: inside wheel 1 m in, R 9 m round the corner | drop median **0.133**, p90 0.198, max 0.349; > 5 cm at 181 of 226 corners | median 0.039, p90 0.222; > 5 cm at 27 of 64 |
| **grass over the street's strip**, first 20 m | **24.8 %** of samples, max 0.203 m | 0.0 % |
| host's edge line painted across ≥ half the opening | **93** mouths | 0 |
| plan offset / width: strip gap vs. pavement span | ≤ 0.03 m / ≤ 0.1 m (6 acute or forked mouths: up to 1.85 / 4.3 m) | |
| straight wheel paths, ±5 m / +12 m: fine step (0.10 m) | ≤ 0.024 m; one at the 48th/Colorado pad arm: 0.203 m at 9.7 m along grid_primary_49 | ≤ 0.048 |
| overlap (two road sheets) / daylight / grass on the deck | ≤ 0.024 m / 0 / 8 samples | ≤ 0.011 / 0 / 1 |

The corner, typical (grid_unclassified_38 → grid_tertiary_2). Along the host, 0.15 m past its edge, from the side
street's edge outward:
- 0-1.8 m: the side street's own edge strip falls from 0 to -0.16 m.
- 1.8-5 m: grass at -0.02 m. The host's strip is deleted here.
- From 5-6 m: the host's strip resumes at 0.00.

At the strip's lip the ground stands up to 0.18 m over it: the grass block in the stills. The host's road slab ends
in the air over the trench.

**Worst first** (lip; bare host edge; R 9 turn drop):
1. grid_primary_84 (start) → lap, I-70 bridge approach (cut 1806.8, -487.3): 0.327 m; 9.9 m; 0.349.
2. grid_primary_78 (end) → lap, the same bridge (cut 1802.2, -466.4): 0.327; 7.4 m; also the 0.241 sample.
3. grid_primary_35 (end) → lap, s≈2320 (cut -919.7, 1116.4): 0.211, plus the street's own edge 0.189; 9.3 m.
4. grid_secondary_39 (start) → lap: 0.159; 3.5 m; 0.275.
5. grid_unclassified_28 (start) → grid_residential_12: 0.200; 0.276.

Then about 100 mouths at 0.16-0.22 m.

Stills (numpy z-buffer off the gate OBJ, no Blender): `/Volumes/Drive/codex/sc_mouths/`.
- `sc1`-`sc5` are these mouths. `lm1` / `lm2` are Lake Murray: a stub return, and a plain lap mouth.
- Views: A = the driver's eye in the host lane; B = low across the corner; C = from the side street;
  D = oblique, 3 m up.

### 4. What Lake Murray does at a mouth that Sand Creek doesn't

- **27 of LM's 32 mouths are authored.** `author_stubs_blend.py` (draft steps `stubs_author` / `stubs_tidy`,
  `tools/ship_track.sh:372,386`) builds:
  - a circular curb return from the host's gap end round into the side street's curb;
  - the corner pavement under it, a ROAD fan from K;
  - the corner ground, refined and pinned under the strips.

  The two north mouths have `mouth_fill` plus an apron.
- **LM's edge goes UP.** A 0.14 m curb, then the walk. Where gap_mouths leaves a gap, the street's walk end reads as
  a curb end and the ground at the prep's contact height is flush with the road: lip median 0.033.
- **Sand Creek's edge goes DOWN.** `route.edge`: no curb, falling 0.20 m over 1.5 m. Its plain mouths are open
  trenches.
- LM's mouths show no paint in the host's edge band.

## Diagnosis (the mechanism)

1. **The side street's strip ends open, sunk, at the host's edge.**
   - `scripts-v021/blender/build_loop_blend.py:1317-1318` sweeps each connector's edge strip (`curb_sidewalk`, Sand
     Creek's `route.edge` at `tracks/sand-creek-lm/track.config.json:367`: curb_h 0, down 0.20 m over 1.5 m) to the
     cut with no end.
   - It runs down beside the host's edge to -0.16..-0.22 m.
2. **The host's strip is deleted 3 m past each of the street's edges.**
   - `tools/gap_mouths_blend.py:104,140` deletes it with `tools/mouth_weld.py:50` `GAP_CORNER_M` 3.0 and `:491`
     `gap_window`.
   - The window was sized for Lake Murray's raised walks.
   - On Sand Creek it leaves the host's slab edge with nothing beside it: 1.2-1.5 m of bare edge per corner.
3. **The prep raises the ground into the gap.**
   - `engine-july-snapshot/scripts/ac/build_kn5_loop.py:1181-1199`: every ground vertex within 3 m of a road edge goes
     to the road's height - 0.02.
   - In the gap the ground rises to -0.02, right beside the street's strip sunk to -0.2: a trench at the host's edge
     with a grass wall at its far end.
   - A wheel cutting the corner (any inside-wheel R > 3.4 m) drops into it. That is "bump, step or lip". The slab
     ending in the air over it is "floats".
4. **Nothing pins the ground to the side streets' strips.** `strip_seam` seams the lap and the pads only
   (`tools/strip_seam_blend.py:60`). 24.8 % of each street's first 20 m of strip is under grass: the teeth.
5. **The host's edge line is unbroken.** `build_loop_blend.py:1299` `lane_markings` sweeps it along the whole host
   and nothing gaps it at a mouth, so a white line is painted across 93 of the 113 openings.

verify_mouths measures none of this. Its notch runs inside the street's span, the corners are outside it, and its
approach lines are straight. kn5_ground_check counts the corners in its 27 (it reads 1KERB as ground, so the sunk
strip passes for support) but gates on p95.

## Fix (proposed; nothing built; every key opt-in, Lake Murray names none)

1. **`route.mouth_returns`** (connector-name prefixes, Sand Creek `["grid_"]`): `author_stubs_blend.py`'s return,
   corner-fan and corner-ground stages on through mouths, with no barrier and no stub length.
   - The return carries `route.edge`'s profile round the corner, from the host strip's row at the gap's end into the
     street's strip.
   - The street's strip faces before row J go (FACES_ONLY, as the stubs do).
   - The ground in the corner zone is pinned to the strip as the stubs pin it.
   - Radii are measured per corner on NAIP 2023, as 0073 measured the lap's `curb_radius_m`.
   - `stub_geom` must learn curb_h 0.
2. **`strip_seam.connectors: true`**: the lap's ground seam along every connector strip's lip.
3. **`road_markings.gap_mouths: true`**: delete the host's edge-line faces between the street's two edge crossings,
   as author_aprons does inside an apron.
4. Separately owed:
   - the I-70 bridge mouths' ground (grid_primary_78 / 84);
   - grid_primary_7's raised edge;
   - the pad deck edges over the lap's strip;
   - the 48th/Colorado pad arm's 0.203 m reading.

**The gate that would have caught it**: `verify_mouth_corners`, opt-in by `route.verify_mouth_corners`, on the built
gate OBJ, promoting mouth_survey's CORNERS / TEETH / MARKINGS:
- corner lip (b ≤ 0.15, 6 m either side) ≤ 0.05 m [measured: kn5_ground_check's ROAD_GAP_M, the sampling ceiling for
  contact];
- grass over the street's strip ≤ 2.1 % [measured: Sand Creek's own lap, `edge_report` ground at 1 m];
- edge line across the opening 0 m [invented: policy];
- the R 9 turn drop reported, not gated.

On 0.2.6 the gate would fail at 113 of 113 mouths. LM v4 passes the lip rule at 24 of 32 and is not opted in.

## Fix (0.2.7, built on the Mac; Kevin: "Yes, build it")

**Kevin's word** (2026-11-07, relayed by the coordinator, which showed him the fix above): "Yes, build it". With it, on
the names: "Get rid of Lm Version from names, nothing should be on any other engine now", "LM is the airoso engine", and
"We want to delete old copies from ac when installing new ones". So 0.2.7 is plain **Sand Creek Raceway**, slug and AC
folder `sand_creek_raceway` (layouts "Sand Creek Raceway" / "Sand Creek Free Roam"); the repo directory stays
`tracks/sand-creek-lm` until directories are renamed in one pass.

### What was built (every key opt-in; Lake Murray names none)

| | key / file | what it does |
|---|---|---|
| 1 | `route.mouth_returns: ["grid_"]`, `tools/mouth_returns.py` + `tools/mouth_returns_blend.py` (draft step `mouth_returns`, after `lm_pads`) | Lake Murray's stub returns on through mouths: a circular return from the host's strip row round into the street's strip at each corner's measured radius, `route.edge`'s no-curb profile carried round it (`stub_geom.return_stations(meet_h=None)`), the corner paved (a ROAD fan), the ground refined and pinned; the street's strip faces before J removed FACES_ONLY. Writes `data/mouth_returns.json` |
| 2 | `tools/mouth_radii.py` -> `source/mouth_radii.naip.json` (`route.mouth_radii_file`) | each corner's radius off NAIP 2023 (z18, 0.46 m px): the real edges of both legs, then the arc that best separates pavement from its side. **150 of 216 corners measured**, median 7.5 m, p10 / p90 1.2 / 16.0 m; the 66 not measured (an edge not found, or found at the search's end; a weak or flat arc score; a fit at the grid's end) are built at the median of the measured corners on their host, and say so |
| 3 | `strip_seam.connectors: true` (`tools/strip_seam_blend.py`) | the lap's ground seam along both strips of every grid street and every return's lip |
| 4 | `road_markings.gap_mouths: true` (`tools/gap_mouths_blend.py gap_paint`) | the host's white edge line cut at every opening, out to the returns' tangent points |
| 5 | `route.strip_under_road: true` (`mouth_returns_blend.strip_under_road`) | strip faces whose centre lies under another road's pavement removed (aimed at the owed pad-edge / grid_primary_7 readings; **it fixed none of them**, below) |
| 6 | `route.mouth_returns_skip` | no returns at grid_primary_78 end (I-70 bridge) and grid_primary_80 end (E 56th): m7a built them and verify_mouths went red there (78: APPROACH 4.0 %/m; 80: mouth line 0.072 -> 0.139 m) |
| 7 | gate `verify_mouth_corners` (`tools/verify_mouth_corners.py`, `route.verify_mouth_corners: true`) | corner lip <= 0.05 m, grass over the street strips <= 2.1 %, the host's edge line across an opening <= 0.25 m (one sample); `route.verify_mouth_corners_allowed` 21 rows, each with its measured why |

`tools/mouth_survey.py`'s paint sampler was wrong and is fixed: it sampled b −0.5 / −0.3 / −0.15 and counted YLINE, but the
host's line lies at −0.61..−0.49 (v021 `lane_markings` edge_inset 0.55, 0.12 wide; −0.60..−0.50 on the built OBJ). The
street's own edge and centre lines reach 0.17-0.31 m past the host edge at the weld, so every opening read 0.25-1.5 m
with the host's line gone. It now samples white MARKINGS at −0.58 / −0.55 / −0.52 (GATES-CHANGELOG 2026-11-07).

### Four builds (Mac, `sclm_work/`, workshop root `/Volumes/Drive/codex/sclm_work`, TMPDIR on the Drive)

- **m7a** (returns at every corner the tool could build; resumed twice: `--from mouth_returns` after a ROAD-count guard
  that did not allow `densify_ribbon`'s 130 appended vertices, then `--from export_race` after macOS bash 3.2's
  `${tok^^}`): 198 corners at 102 mouths. verify_mouths red at grid_primary_78 end (APPROACH) and grid_tertiary_74 start
  (NOTCH); the paint sampler finding above.
- **m7b** (+ the skip list, + strip_seam leaving out rows whose strip faces were gone): verify_kn5 TERRAIN POKE x24.
  Reverted the seam change.
- **m7c** (this branch's head, clean, from an empty workshop): **verify_kn5 TERRAIN POKE x24 (worst +0.29 m) > 20: RED.**
  The seam change was not the cause (m7b and m7c have the same 24). The rest of the chain was run with verify_kn5 made
  non-fatal (`m7/run_soft.sh`, a Mac rehearsal runner only, `m7c.soft.log`) to read every other gate; **that run is not a
  candidate and is not quoted as SHIP OK.**
- **m7d** (clean, from an empty workshop; the seam fix below, `strip_under_road` dropped): **SHIP OK**, verify_kn5 PASS
  with **0** TERRAIN POKEs.

### Gates, 0.2.6 (rr2) against 0.2.7 (m7c, then m7d)

| gate | rr2 (0.2.6, installed) | m7c (0.2.7, red) | **m7d (0.2.7, SHIP OK)** |
|---|---|---|---|
| **verify_kn5** | PASS (TERRAIN POKE 9) | **FAIL: TERRAIN POKE 24** (> 20) | **PASS: TERRAIN POKE 0** |
| **verify_mouth_corners** (new) | 113 red: lip median 0.175 / max 0.327; teeth 24.76 %; host line across 111 openings | PASS, 21 ALLOWED: lip median 0.02 / max 0.327 (78, skipped); teeth 0.21 %; R9 turn drop median 0.013 (p90 0.197) | **PASS**, 21 ALLOWED: lip median **0.02** / max 0.327; teeth **0.23 %** (157 / 68,942); R9 turn drop median **0.013** (p90 0.193; rr2 0.144 / 0.202) |
| verify_mouths | PASS (80 allowed) | PASS (80 and 74-start allowed) | PASS (80 and 74-start allowed) |
| kn5_ground_check race / street | PASS; road_over_ground 27 / 11,781, p95 0.021, max 0.291 | PASS; 16 / 12,949, p95 0.021, max 0.295 | PASS; **17** / 12,956, p95 0.021, max 0.295 |
| drive_test street / race, audit, no_route, fold_fans, verify_pads x4 | as runbook 4n | every row identical | every row identical |
| houses / house_gate | 2,183 / PASS | 2,182 / PASS | 2,182 / PASS (one building fewer: a corner zone) |
| textures | 0 untextured | 0 untextured | 0 untextured (128 visible meshes on the road kn5) |
| road kn5 | 92,160,949 B | 116,013,226 B | **116,115,917 B** (TERRAIN 439k -> 973k verts: the corner zones and the seams) |
| race / closure / street kn5 | 10,196,549 / 9,701 / 6,923,402 B | the same sizes | the same sizes |

Against m7c, m7d is better on verify_kn5 (24 -> 0) and the R9 p90, equal everywhere else but two rows a hair worse,
both from putting the strip faces under the decks back (`strip_under_road` dropped): road_over_ground 16 -> 17 (one
sample, 0.222 m, on the lap 1.7 m past its edge at s 1255.6, the 50th_dahlia pad's stretch) and teeth 0.21 % -> 0.23 %
(144 -> 157 samples of ~69,000). Both are far inside their gates and far better than rr2.

**The 24 pokes** (`m7/pokes.py`, verify_kn5's own sampler, located; kn5 z is −N): rr2's 9 are all still there (the lap's
strip by the 50th_ash and 48th_colorado pads, and three more on it at x ≈ −1,400..−1,500 m). The **15 more** are grass 0.16-0.30 m over a
street's sunk edge strip, mostly away from the openings: grid_primary_7 beside its fork (0.295 / 0.222: the owed raised edge, now over its strip),
and single vertices on grid_unclassified_96 / 17 / 9 / 79 / 28, grid_residential_29#2, grid_tertiary_4#0#1, 43, 2 and 84.
At each, a KERB triangle 3.6-5.5 m long with the ground standing over it: the strip's teeth the connector seam was meant
to end.

**Their cause, found on m7d's way (it was NOT the seam's misses):** every one of the 24 (rr2's 9 too) is a seam vertex.
`m7/pokes2.py` prints each poke's KERB triangle and barycentric weights: the minimum weight is 0.0 every time, and the
grass vertex lies 0.05 m from a lip vertex along the strip row, i.e. the seam point (INSET_M inside the lip) ON the row's
own line, which is the edge two strip triangles share. engine-july's anti-poke (build_kn5_loop 2c) finds the strip under a
ground vertex with a downward ray; a ray down a shared edge hits neither triangle (`m7/poke_blend.py` on m7c's prepped
blend: no drivable hit at those vertices), so the vertex kept the contact band's road − 0.02, 0.16-0.30 m over the strip,
and verify_kn5's lens (barycentric, edges inclusive) counts it. 41,752 seam points on m7c against 7,134 on rr2 made 24 of
what was 9. **The fix** (`tools/strip_seam_blend.py` OFF_EDGE, with `strip_seam.connectors` only, so the Lariat's seam is
unchanged): every strip seam point moves (9.7, 7.1) mm off the row's line into a triangle's interior, one vector for all
seams so shared points stay shared. No gate tolerance touched, no allow row added. m7d: 0 pokes; strip_seam's 13 misses
are unchanged and caused none of them.

**The owed spots** (`mouth_survey --rog`): on m7c 4 of the 16 road_over_ground samples are in a mouth's corner (rr2 15),
all at allowed mouths (35 x 2, 84 start, 43). `strip_under_road` changed none of its targets: the colorado_50th pad edge
0.217, 50th_dahlia 0.152 / 0.144, 48th_colorado 0.055 and grid_primary_7's 0.295 all read as on rr2. The I-70 bridge
mouth (78 end, skipped) still reads 0.241. **Decision (m7d): `route.strip_under_road` dropped** (the key, its code in
mouth_returns_blend.py and its number). Its only measured effect was one road_over_ground sample at the 50th_dahlia
stretch (0.222 m, back on m7d) and 13 grass-over-strip samples; its five targets read the same with and without it.

**Lake Murray unchanged:**
- `git diff` against this branch's base: nothing under `scripts/` or `tracks/san-diego-lake-murray/`.
- gap_mouths A/B on Lake Murray's committed project (`sclm_work/lm86`, HEAD's tools against this branch's): logs and the
  145-object blend digest identical (`c1722523…`).
- Lake Murray names none of the keys (test); `stub_geom.return_stations`' default is the stubs' `MEET_H_M`, unchanged.
- Tests: 1,353 pass under pytest; the 1 failure is the known `test_registry_moves` (also red before this branch).
- m7d: the gap_mouths A/B re-run on fresh copies with m7d's tools: logs and digest identical again (`c1722523…`). Lake Murray runs neither mouth_returns nor
  strip_seam; the Lariat's strip_seam (no `connectors`) computes its points by the same expression as before.
- m7d tests: 1,353 pass, the known `test_registry_moves` fails (as before).

**Stills** (numpy z-buffer off the gate OBJs, same cameras as above): `/Volumes/Drive/codex/sc_mouths/m7c/`,
`cmp_<mouth>_<view>.jpg` = 0.2.6 | 0.2.7. sc5 (grid_unclassified_38 -> grid_tertiary_2) D: the square trench and grass
block become a round concrete-edged return with the edge line broken; sc2 (grid_primary_35 at the lap) A: the same from
the driver's seat.

### Owed after 0.2.7 (start here)

1. (done on m7d) the pokes: the seam points off the strip rows' shared edges; verify_kn5 0 pokes.
2. (done on m7d) `strip_under_road` dropped.
3. The 21 allowed corner rows: 11 mouths where neither corner could be built (the street's edge fit has 0-2 rows past a
   long weld re-spread: 7, 49, 5, 74 x 2, 105, 19, 29#2, 43; the 27/65 crossing, shorter than its fit, x 2); 4 with one
   corner built (11: the other's host strip cut by a pad; 84 x 2: an edge that never meets the host's; 10: a 21.5 m
   tangent off its host's end); 4 with both built and still over the lip (35, 39, 34, 96); 2 skipped (78, 80).
4. The I-70 bridge mouths' ground, the pad deck edges, grid_primary_7's raised edge (0086's owed list, unchanged).

**Runbook 4o** (ledger 0079, PC runbooks): the PC's rehearsal of m7d's head; see its status line there.

## Verification

- `tools/mouth_survey.py` on the rebuilt workshop:
  - lip ≤ 0.05 at every grid mouth;
  - teeth ≤ 2.1 %;
  - edge line 0 m;
  - the 15 corner samples gone from road_over_ground;
  - verify_mouths unchanged.
- Lake Murray's built OBJs byte-identical.
- Kevin turns in and out of the grid streets, both ways, and does not say "floats".

## PC (optional; the Mac's rr2 already matches the installed gate numbers)

```
cd D:\k10\airoso && git fetch origin && git show origin/claude/sand-creek-grid-mouths:tools/mouth_survey.py > tools\mouth_survey.py
set PYTHONUTF8=1 && python tools/mouth_survey.py D:/k10-scratch/sand_creek_lm --rog --json D:/k10-scratch/sand_creek_lm/data/mouth_survey.json > D:/k10-scratch/sand_creek_lm/mouth_survey.txt
```

**Ran on the PC, 2026-11-08 19:20** (the installed 0.2.7 workshop `D:/k10-scratch/sand_creek_lm`, the branch's own
`tools/mouth_survey.py` at ae5fc2d, nothing copied over the main checkout): exit 0, 113 mouths, 0 errors, 2 min 20 s.
Output: `tracks/sand-creek-lm/data/mouth_survey.json` (md5 b12007ab) and `D:/k10-scratch/sand_creek_lm/mouth_survey.txt`.

| | m7d's gates (table above) | installed 0.2.7, `mouth_survey --rog` |
|---|---|---|
| lip median / max | 0.02 / 0.327 | 0.021 / 0.327 (78#0 end) |
| teeth | 0.23 % (157 / 68,942) | 0.23 % (157 / 68,942) |
| road_over_ground | 17 / 12,956, max 0.295 | 17 / 12,956, max 0.295; 4 in a mouth's corner (35 lo x 2, 84 start hi, 43 start hi) |
| mouths at lip <= 0.05 | | 88 of 113 |

The same numbers as the Mac's build. R9 is not compared: the survey's `turn_r9_drop_m` (median 0.033, p90 ~0.21) is a
different measure from verify_mouth_corners' R9 turn drop (0.013 / 0.193). The 21 allowed corners (owed item 3) are
still the ones over 0.05; nothing new.

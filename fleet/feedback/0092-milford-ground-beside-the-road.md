---
id: 0092
title: Milford's ground beside the road — the lidar past the shelf, the paved run-off as pads, finer grass looks
status: diagnosed
scope: track:milford-road-course-lm
layer: project
train: -
---

## Symptom

Kevin, 2026-11-18: "milford is still very messy. let's do a measured, parallelized effort to get it closer to high plains
in terms of quality and accuracy." The read-only scenery audit of that day
(`/Volumes/Sundowning/codex/mac/milford-hp-audit-20261118/scenery/REPORT.md`, Milford 0.1.12 against High Plains 0.1.7)
ranked what reads as messy beside the road. This entry codes its items 1, 2 (checked), 3, 5, 6 and 7b, opt-in, on branch
`claude/mf-ground-20261118`. Item 4 (NAIP-only trees at the verge) waits for Kevin's yes (ledger 0082, Owed 3); the road
line, edges, surface, buildings, race furniture and the road texture are other coders'.

## Evidence (the audit's, re-measured where this branch could)

Every number is measured on files on the Mac unless marked [invented] (chosen) or [modelled] (a model of what the PC
builds). The 0.1.12 build is only on the PC; the Mac's stand-ins are the 0.1.5 workshop on Sundowning
(`/Volumes/Sundowning/codex/mf_work/v015/b1`): its gate OBJ (what the audit measured), its kn5, and its synced-out
`loop.blend`, whose TERRAIN (370,451 vertices) is the draft TERRAIN 0.1.11 still ships (runbook 0082-8:
`TERRAIN 370451 -> 370451 verts`).

1. **The terrace and the cliff.** The assembler holds the 3DEP grid at the road's height for `terrain_band_m` 22 m; the
   built ground 12-30 m out is 0.69-0.86 m (p50) off the 2017 lidar (`source/lidar/milford_lidar_1m.npz`), p95 2.6-2.9 m,
   up to 8.2 m at s 4,325-4,375 (the road crosses a culvert there: the lidar shows a 7 m headwall into the path 11-13 m off
   the left lane edge, and a 6.6 m one 15 m off the right).
2. **The far ledges** (drive_test's excursion sweep, a drop over 0.12 m per 0.5 m beyond the built edge + 4 m; reported,
   not gated): 21 on 0.1.5, 30 on 0.1.12, High Plains 0. The audit expected item 1 to fix them.
3. **Paved run-off drawn as turf**: class D (the measured class map) and bright grey concrete within 30 m of the lane edge.
5. **The GrassFX patchwork**: 14,982 m of look boundary within 30 m on a 12 m staircase (High Plains 656 m); B (unmown) cells
   read the right look 65 %, D 54 %.
6. **The ride pad** (PADAPRON_0, 16,812 m², 6 cm over 1GRASS) reads the base look (mown blades) in all of its cells.
7b. `kn5_ground_check`'s walls median (-0.461 m on 0.1.5, -0.48 on 0.1.12) is set by the unseen trunk colliders.

## Diagnosis

### Item 2 is NOT fixed by item 1 at Milford (modelled on 0.1.5)

`source/ground/scripts/ground_emulate_blend.py` (Blender; records `source/ground/records/sweep_v015_*.json`): the 0.1.5 gate OBJ's ground re-seated the way terrain.lidar_patches + engine-july's
prep would leave it (under the pavement pinned; within 3 m of a road vertex the shelf; 3-9 m the prep's smoothstep onto
the new TERRAIN; beyond, the new TERRAIN; the anti-poke clamp), then drive_test's sweep replayed with its wall guard. The
replay without changes reproduces 0.1.5's own `drive_test.full.json`: **0 gated drops, 21 far ledges**.

| the patch's weight off the lane edge | gated drops (limit 4) | far ledges |
|---|---|---|
| none (0.1.5 as built) | 0 | 21 |
| full lidar from the lane edge | **5** (s 900.7 R, 1050.3 R x2, 1201.3 R x2) | 53 |
| ramp 0 at 3 m -> 1 at 9 m | 0 | 46 |
| ramp 6 -> 12 m | 0 | 32 |
| ramp 6 -> 16 m | 0 | 22 |
| **ramp 9 -> 16 m (committed)** | **0** | **21** |

The lidar itself falls 0.12-0.28 m per 0.5 m (24-55 %) within 9 m of the edge on the low side of the banked corners
(s 900-1201) and at s 1650, 3150, 3751, 4050, 4200: real slopes, which the sweep's 0.12 m rule counts. Of 0.1.5's 21, 18
are the build falling where the lidar is flat (the audit's finding) and they would go with the lidar; but the real slopes
add more than that, and 0.1.12 already has 2 gated drops of its limit 4. So the patch leaves the sweep's reach (the lane
edge + 9 m, where the prep's shelf and feather rule) as built: drive_test's numbers stay 0.1.12's (expected: 2 gated,
30 far), and the terrace and cliff past it go. A far-ledge count near High Plains' 0 needs either a gate that tells a real
slope from a ledge (Kevin's: a threshold is his alone) or graded run-off where Milford has none.

### Item 1: the ground past 9 m seated on the lidar (measured on the 0.1.5 draft TERRAIN, before the prep)

`source/ground/scripts/terrain_resid_blend.py`: TERRAIN minus the lidar on the audit's 1 m cells with ground returns, before / after
`tools/ground_patch_blend.py` with the committed patches, on a copy of that loop.blend (`records/terrain_v015_before.json`, `terrain_v015_after_split4.json`, `_split3.json`):

| off the lane edge | cells | \|Δ\| p50 before -> after | \|Δ\| p95 | over 1 m |
|---|---|---|---|---|
| 0-3 m | 16,209 | 0.197 -> 0.197 | 1.33 -> 1.33 | 13.9 -> 13.9 % |
| 3-9 | 54,069 | 0.332 -> 0.330 | 1.51 -> 1.50 | 14.3 -> 14.1 % |
| 9-12 | 26,017 | 0.475 -> 0.364 | 2.01 -> 1.52 | 19.9 -> 12.0 % |
| 12-20 | 67,467 | **0.686 -> 0.053** | 2.63 -> 0.54 | 34.7 -> 1.2 % |
| 20-30 | 78,012 | **0.858 -> 0.023** | 2.85 -> 0.10 | 44.1 -> 0.0 % |
| 30-45 | 101,484 | 0.470 -> 0.080 | 1.84 -> 0.76 | 20.7 -> 2.8 % |

25 m side-stretches (3-20 m) with \|Δ\| p90 over 0.5 m: 344 -> 230 of 392; s 1,000-1,225 at 9-30 m: p50 2.29 -> 0.07 m;
s 4,325-4,375 worst 8.19 -> 4.82 m (the rest inside 9 m, by design). TERRAIN 370,451 -> 455,233 vertices (+84,782), 740,436
-> 910,000 faces, every face a triangle, 0 duplicates; 21 s. split_m 3 instead of 4 fits the same (20-30 m p50 0.019, p95
0.084) for +153,000 vertices, so 4. The culvert's west headwall now stands as the step (a section across it:
30.4, 29.9, 28.9, 26.7, 23.1, 22.8 m at 1 m steps; before, 30.4-30.9 m out to 25 m). The 0-9 m band is the prep's
(engine-july, frozen: Lake Murray's); 0.1.12's gate OBJ is on the PC.

**A latent fault found on the way (not fixed for Sand Creek / Pikes Peak, whose output must not move):** the patch's
default cut (`subdivide_edges` + `triangulate`, 12 passes) on ground holding zero-area slivers cuts the same edges pass
after pass and doubles duplicate faces each time: on the 0.1.5 gate OBJ's prepped ground (a stand-in) 767,963 faces ->
2,348,881, 1,296,864 of them duplicates. The real 0.1.5 draft TERRAIN has 134 zero-area faces. The opt-in
`split_mode: "bisect"` (below) cannot do it. Whether Sand Creek's and Pikes Peak's builds carry duplicates is not
measured here (their OBJs are on the PC): worth a count (`source/ground/scripts/mesh_check_blend.py` on a loop.blend) before their next build.

### Item 3: the paved blobs, outlined (`source/runoff/scripts/runoff_pads.py` -> `source/runoff/runoff_pads.json`)

Class D or NAIP grey (mean over 165, channel spread under 24 [invented]) within 40 / 30 m of the lane edge, outside the ride
pad, 8-connected: 24 blobs of at least 150 m². Within 30 m: D 12,260 m² (the audit 12,180), grey 7,856 m² (the audit
4,690: its grey rule was stricter), 20,116 m² in all. **19 kept** (NAIP p50 blue / red 0.91-0.95: the lanes read
(188,185,174) = 0.93, the ride pad (166,167,164) = 0.99); **5 left out** (0.73-0.80: L3707, L3759, L3862, L3929, L4374:
on NAIP they are dry grass and bare ground the lidar's intensity reads as D, `source/runoff/left_out_blobs.jpg`; kept examples `kept_blobs_sample.jpg`). The kept 19 hold
15,252 m² of the 20,116 (6,048 m² within 9 m); their outlines 19,383 m². Outlined in the road's own frame every 4 m of
station; a blob within 3 m of the lane edge starts at the edge strip's lip, lane edge + 1.9 m (the 0.1.5 OBJ's 1KERB p99
per 250 m: 1.73-1.84 m, + 0.1 [invented]); 0 folded quads, 0 overlaps.

### Items 5 and 6: GrassFX (`source/ground/scripts/grassfx_metrics.py`, the audit's metrics in the draft's own frame; `records/grassfx_0112_vs_0092.json`)

| within 30 m of the lane edge | 0.1.12 (12 m cells) | this branch |
|---|---|---|
| rectangles (B / C / D) | 1,277 (409 / 588 / 280) | 2,059 (848 / 908 / 303) |
| class = look, off the pads: C / B / D / base | 82.1 / 65.4 / 42.7 / 83.8 % | **89.4 / 76.8 / 65.1 / 86.6 %** |
| look boundary | 14,978 m (B/base 8,078) | **21,270 m** (B/base 13,440) |
| D/base boundary | 1,280 m | 528 m |
| ride pad cells with the D look (no blades) | 0 % | 96.1 % |
| class-map D under the run-off pads | 42.8 % | 3.5 % (they are 1RUNOFF: an ext_config occluder) |

The photograph's own class boundary within 30 m is 44,878 m: finer cells put the looks where NAIP shows them (the audit's
"35 % of B cells get the wrong look" falls to 23 %), and that **lengthens** the boundary. What softens it is B's fade
(12 m [invented], twice the base 6 m) — how CSP blends a FADE wider than a 6 m rectangle is unverified. VERIFY IN-GAME.

### Item 7b: kn5_ground_check (the 0.1.5 kn5, the tool of main and of this branch: `records/kn5_ground_check_v015_old.log`, `_new.log`)

The gated lines and the JSON are identical (`walls objects 336 ... median -0.46 p95 -0.19`, PASS); two info lines follow:
the trunk colliders 312 objects, median -0.44, p95 -0.19; the other walls 24 objects, median -1.24, p95 -0.26, hovering 0.
Gated on their own both would pass on 0.1.5; 0.1.12 is not measured, so they are reported, not gated (no verdict moves).

## Fix (every key opt-in; no other track names one; Lake Murray untouched)

- `tools/lidar_ground_patch.py --npz` (or `terrain.lidar_patches_npz`): the patches' lattices off a committed 1 m grid,
  no network; the grid's own cell centres; holes filled from neighbours; a patch's `"corridor"` gives each node a weight
  off its distance to the lane edge (0 to `in0_m`, up to 1 at `in1_m`, 1 to `full_m`, 0 at `zero_m`).
- `tools/ground_patch_blend.py`: a lattice with `"w"` moves each vertex by its bilinear weight and cuts only where it is
  over 0; a patch's `"split_mode": "bisect"` cuts by longest-edge bisection. Without them: the code path of before.
- `tools/ship_track.sh` `draft_ground_patch`: with `terrain.lidar_patches_npz`, the lattice is measured first (a
  build product, `data/ground_patches.lidar.json`, ~9 MB, not synced out); no key = no new header.
- `tools/plan_grassfx_aerial.py`: `frame: "projection"`, `near: {cell_m, reach_m}`, `pad_looks`, `fade_by_map`.
- `tools/seat_pads_blend.py`: unchanged (Nevada's route, ledger 0081).
- `scripts/ac/kn5_ground_check.py`: the walls lens as a function (the same expressions); info lines when
  `1WALL_GHOST_TRUNK` meshes exist (Milford only).
- Milford's `track.config.json`: `terrain.lidar_patches` (corridor: in0 9, in1 16, full 35, zero 45 m [invented], split 4
  m [invented], bisect; culvert_4349_w: the west headwall's floor, hard_edges 1-8, feather 3 m [invented], split 1 m),
  `lidar_patches_npz` / `_file`; `scenery.bespoke.pads` (the ride pad first, then the 19 run-off strips),
  `pads_seat "ground"`, `pads_surface "1RUNOFF"`; `grassfx_zones` frame / near / pad_looks / fade_by_map;
  **`texture_overrides["1RUNOFF"]`** = the concrete skin Nevada's apron wears (`assets/textures/building_*`): outside the
  four key groups this branch was given, the one line the concrete skin needs. The ride pad, PADAPRON_0, becomes
  `1RUNOFF_apron_0` too (pads_surface names every pad): paved physics where it had grass under a visual sheet, the same
  concrete skin (NAIP reads it grey, 0.99 blue / red).
- Milford's `ship.json`: draft step `ground_patch` after `kerbs`; `source/lidar/milford_lidar_1m.npz` synced in.

## Scope

Milford (`tracks/milford-road-course-lm`) only. Sand Creek and Pikes Peak name `terrain.lidar_patches` without `corridor`,
`split_mode` or `lidar_patches_npz`: their patches are cut and seated by the same lines as before. Nevada's pads are
unchanged. Lake Murray names none of the keys and its chain (`tools/ship_sd.sh`) has no ground_patch step; its kn5 has no
`1WALL_GHOST_TRUNK`.

## Verification

Mac: the tests below; the models above. PC: runbook 0092-1, then Kevin's drive.

### Tests

`tests/tools/test_milford_ground_0092.py` (new, 15): the npz lattice on a synthetic grid (cell centres, a hole filled), the
corridor's weight profile and its nulls, the EPT path refusing a corridor, Milford's own lattice off the committed grid;
`weight_at`; the run-off record reproduced byte for byte and the config's pads equal to its kept blobs; the planner without
the new keys byte-identical to main's planner (74b46263) on Milford's reading, and with them 6 m cells, the ride pad D, B's
fade; only Milford names the keys; ship.json and draft_ground_patch; kn5_ground_check on a synthetic kn5 (sunk trunk
colliders, a hovering rail): main's tool and this one return the same verdict and numbers, this one adds `seating_info`.

The whole suite in a sparse clone (tools, tests, scripts, fleet, assets, Milford x2, Sand Creek, Nevada): main 74b46263
200 failed / 1,344 passed / 11 collection errors (files outside the sparse set); this branch 200 / 1,359 / 11, the same
failure list (+15 passed, the new file). The touched tools' 24 test files alone: 50 failed / 205 passed on main, 50 / 219
here, the same 50.

## PC runbook 0092-1: rehearse Milford with the ground beside the road from an EMPTY workshop; report, do not install

1. `git fetch && git checkout <the merge carrying claude/mf-ground-20261118>`; `git status` clean. The lidar grid is
   committed (`source/lidar/milford_lidar_1m.npz`, 942,695 B): no lidar fetch, no network in the patch step.
2. The TreeFX models and ENG as runbook 0082-8 (Oak3 `24111ede…`, SycamoreV2 `7010d61f…`; ENG `eng_mflm_017` or the
   install's).
3. Rehearse: `ENG=<ENG> SHIP_PROJ=D:/k10-scratch/milford_0092_reh AIROSO=<checkout> PYTHONUTF8=1 bash tools/ship_track.sh
   milford-road-course-lm --no-install`. The log must show:
   - `draft: the declared patches' lidar ground off the committed 1 m grid`, then
     `[lidar_patch] corridor: 812 x 1184 nodes of the 1 m grid, 275331 read, 42541 filled from their neighbours, 317872 weighted` (the Mac, on the committed 0.1.12 line) and
     `[lidar_patch] culvert_4349_w: 26 x 19 nodes ..., 409 read, 26 filled` (the counts move a little with 0.1.12's line);
   - `[ground-patch] corridor: TERRAIN <n> -> <n + ~83,000> vertices (edges <= 4.0 m in the box, where its weight is over 0),
     ~99,000 seated ..., largest move ~7.9 m`; `[ground-patch] culvert_4349_w: ... +~1,700 vertices ... largest move ~4.3 m`
     (the Mac, on 0.1.5's loop.blend: 370451 -> 453501, 98811 seated, 7.87 m; 453501 -> 455233, 825 seated, 4.25 m);
   - `[bespoke] pad ride_pad: ... cells` and 19 `[bespoke] pad runoff_...` lines, no `self-check FAILED`;
   - `[seat-pads] PADAPRON_0 -> 1RUNOFF_apron_0 ...` through `PADAPRON_19 -> 1RUNOFF_apron_19`, `ground over 0` each;
   - `[grassfx] 100 x 131 cells of 12 m, ~2,640 of them read as 4 cells of 6 m ...; ~2,060 rectangles`;
   - `SHIP OK`.
4. Read the gates (BUILT artifacts):
   - `drive_test.full.json`: `excursion_drops` and `excursion_far_ledges` as 0.1.12's (2 / 30; the sweep's reach is
     untouched) — any more gated drops: stop and report the stations;
   - `audit.json` CLEAN; `kn5_ground_check.full.json` PASS, `seating.walls` as 0.1.12's, plus `seating_info.walls_trunk` /
     `walls_rest` (report both);
   - `house_seat_check.json` PASS (no building stands within 45 m of the lane edge); `kn5_textures.json` (1RUNOFF's skin
     is `building_diffuse.jpg` / `building_normal.jpg`: must be embedded), `road_wear_check.json`, `edge_smoothness.json`
     unchanged;
   - the road kn5's size (0.1.11 Mac 44,555,580 B): expect about +4-6 MB (TERRAIN ~+85,000 vertices, 19 pads on the
     ground's triangles) [modelled]; and the prep's time (the TERRAIN is ~23 % larger).
5. On the gate OBJ: `python <audit>/scripts/obj_ground_blend.py`-style numbers if the scenery audit's scripts are carried
   (built − lidar 12-30 m p50 expected ≤ 0.06 m), else skip.
6. Report every number of step 4; no install without Kevin's yes. Then Kevin's drive: the hillsides past the run-off
   (s 1,000-1,225, s 4,350's culvert from the left), the run-off pads (driven onto: paved, not grass), grass at the pad
   edges and none through the ride pad, B's softer edge. VERIFY IN-GAME.

## Owed

1. The PC: runbook 0092-1.
2. Kevin: whether a gate should tell a real slope from a ledge (item 2); whether the NAIP-only trees go in (item 4, 0082
   Owed 3); whether B's size step (1.1-1.5 against base 0.7-1.1) should shrink too.
3. If the line or the widths move (another coder's lm_intake / route work): re-run `runoff_pads.py --write`.
4. Sand Creek / Pikes Peak: count duplicate faces in their patched TERRAIN (the latent fault above).

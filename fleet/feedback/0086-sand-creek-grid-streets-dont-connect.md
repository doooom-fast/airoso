---
id: 0086
title: "Sand Creek's grid streets don't connect to the main road, they float": square, sunk corners at every mouth
status: diagnosed
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

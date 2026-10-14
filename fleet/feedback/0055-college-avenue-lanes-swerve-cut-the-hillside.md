---
id: 0055
title: "One of the lanes swerves into where the other lane should be ... we should just cut into the hillside the way California does" — College Avenue's split section; the Speedways keep their chicane
status: in-progress — diagnosed (tools/median_envelope.py's trust test measured the raw line, not the carriageways), fixed and rehearsed 2026-10-14 (full scratch chain, every gate no worse than v0.18.0), not installed; Kevin's seat closes it
scope: tracks/san-diego-lake-murray (College Ave mainline between the College hairpin and the College/Navajo box; median_bands / connector islands there; race corridor on College)
layer: project (+ engine if the ribbon/median sweep is the cause)
train: -
---

## Symptom (Kevin, seat, 2026-10-14, v0.18.0)

> "One thing I'd like fixed about college Avenue is it seems like one of the lanes swerves into where the other lane
> should be, and then the other lane is swerving to where houses are. To go through an area that I think is a split
> lane, um, and so instead of this swerving stuff, I think we should just cut into the hillside the way California does
> and has like a flat side of the hill alongside one side of the road. I think that would be more accurate than swerving
> around it like this. But for the racetrack versions, I do like the chicane that kind of goes from one side of the road
> across to the other and back."

Two asks: **Lake Murray Free Roam** — no swerve: the road runs where it really runs, cut into the hillside with a flat
cut face along one side (a California road cut), not swerving around the slope. **Speedway / Speedway Reverse** — keep
the chicane that crosses the road and back (built as race furniture on the corrected road if the road itself stops
swerving: one road kn5 serves every layout, L8).

## Evidence / Diagnosis

**Where.** College Ave northbound on the loop, v1262-1374 (stations ~3776-4120, about 32.7889 N, -117.065 W), between
the Del Cerro Blvd mouth (v1085) and the College/Navajo box (v1506). v0.18.0's road jogged ~12 m sideways at
v1262-1280, ran ~215 m on the wrong alignment, and jogged back at v1352-1370; the island stopped at v1258 and restarted
at v1374. `median_bands.json` had two College runs (825-1280, 1353-1509) where the real road is one divided section.

**Mechanism (file:line, v0.18.0).** Not the ribbon, the island author or the race corridor: `tools/median_envelope.py:196`
trusted a vertex only while `MIN_SEP <= s <= SEP_TRUST (24 m)`, `s` = the RAW centreline's offset to the opposing OSM
carriageway. On College the raw line sits on the aerial's southbound carriageway while OSM draws BOTH ways ~3.0-3.7 m
east of their pavement (a consistent OSM-vs-NAIP offset), so over v1282-1350 `s` read 24.1-24.7 m where the carriageways
are 20.5-21.2 m apart — rejected by the upper bound alone (replay with the tool's own functions). The 69-vertex gap
exceeded `GAP_BRIDGE` (8): the run split, each end took the cosine taper (shift -11.8 → 0 over v1262-1280, 0 → -11.1
over v1352-1370; width 32 → 17 m), the island was pulled back. Between the run ends the slab returned to the single
southbound alignment ±8.5 m: its west edge 4-6 m over the house lots, the northbound lanes painted on the southbound
carriageway, the real northbound carriageway ~20 m east left as green hillside — exactly Kevin's two observations.
`barrier_bands` inherited the jog: race_cw's lane swung 18.4 m (the chicane Kevin likes), race_acw only ~4 m.

**What the real road is.** A divided road on a hillside, split level (NAIP 2022 sections every ~25 m; 3DEP 1 m
cross-sections every 25 m): northbound carriageway ~[-27.5, -13] (laterals from the raw line, + west), a 6-8 m treed
median, southbound ~[-6, +7], ~34 m overall, no opening between Del Cerro and Navajo. The northbound carriageway rides
a bench over the southbound one: +2.4 m at v1216, +5.5-5.7 m over v1243-1279, +5.0-5.3 m to v1342, fading to +1.6-1.9 m
by v1396-1414; east of it the hill rises another 4-8 m within 20 m (to 168-171 m against a road at ~157 m) — a real
cut slope; west of the southbound carriageway, house lots at road grade.

**L3 note (Kevin's choice, recorded).** The build carries both carriageways on ONE slab at the southbound grade (ledger
0037), as v0.18.0 already did on both sides of the gap. So through v1243-1360 the northbound lanes run up to ~5.7 m
under their real bench. Kevin's ask — one road with a flat cut face on the uphill side — is that simplification made
deliberate; it is the only tension with L3, and it is his call.

## Fix (2026-10-14, branch worktree-wf_6ef1e18f-ee6-2, rehearsed full chain on scratch, NOT installed)

1. **The road where it runs** — `tools/median_envelope.py`: the trust test's upper bound is the two CARRIAGEWAYS'
   separation (opposing way's lateral − the ridden way's lateral), not the raw line's offset; the lower bound and the
   along-the-road test unchanged; no threshold changed. College is ONE run (v825-1509), Navajo's runs unchanged, nothing
   else moves (whole-loop replay). Only v1259-1373 change in `median_bands.json`; the centreline moves only on
   v1264-1368.
2. **The California cut** — zone `college_split_cut` (track.config.json terrain.ground_release, s 3590-4400, right =
   east, ~v1197-1470): the ground east of the slab is real 3DEP cut back by the existing 1:1 earth batter from the east
   pavement edge, read out to `cut_reach_m` 20 m (= `terrain.clamp_corridor_m`, the construction zone), the top rounded
   into the hill over `round_m` 3 m (docs/ROAD-CONSTRUCTION.md 2-5 m), `rails: false` (a cut has no drop; the first
   rehearsal stood an 816 m jersey rail on the sidewalk apron). `tools/ground_release_blend.py` also dissolves the
   zone's collinear slivers (one had stopped the kn5 prep's T-junction weld). Beyond the daylight line nothing is
   reshaped; the west side has no zone.
3. **The Speedways keep a chicane** — `race.chicanes` `college_split` (out leg v1253-1289, back leg v1343-1379), built
   as race geometry on the straight road, never a second road kn5 (L8): in each Speedway the closure sweeps into the far
   curb strip while a race-side wall sweeps in parallel from the race-side strip, both pinned; the lane holds the far
   carriageway ~160 m and comes back. Speedway (race_cw, northbound) crosses to the southbound carriageway and back;
   Speedway Reverse (race_acw) the mirror — it now gets a real crossing too (v0.18.0's was a ~4 m wiggle).
   `scripts/geometry/race_chicane.py`, `tools/barrier_bands.py` (self-gate 13), the walls in each layout's own closure
   kn5 (`tools/race_furniture.py`), judged by `verify_race`, `no_route`, `median_zone` / `drive_test` (barrier_missing
   probes the new wall), `write_ai_line` (zone `chicane`).
4. **Free Roam keeps the island the Speedways cross** — the median over v1253-1379 is authored as street-only objects
   (`1KERB_sidewalk_streetonly_median`, `1WALL_guard_streetonly_median`) and ships in `<slug>_street.kn5`, loaded by
   Lake Murray Free Roam only (`split_exports_blend`, `ship_sd.sh`, `track_folder`, `verify_kn5`, the new
   `tools/check_street_kn5.py`); the street gate OBJ (data/track.obj) includes it, no race gate OBJ does. No median
   shrubs over that span (TreeFX is track-wide and a race lane crosses there).
   Every invented number is in fleet/GATES-CHANGELOG.md (2026-10-14, ledger 0055).

## Verification (decided with the fix, measured on the BUILT rehearsal, D:/k10-scratch/college)

- **No swerve.** One College run 825-1509 with no taper inside; the island non-zero on every vertex v1240-1487 (v0.18.0:
  0 on v1259-1373). Lateral displacement from the pre-median line every ~25 m over v1230-1400: -10.1 … -12.2 m, the
  largest 25 m change 0.59 m (v0.18.0: 7.81 m); over the formerly swerving v1266-1365 ≤ 0.45 m. The 0.57-0.74 m changes
  at v1230-1257 and v1374-1392 are byte-identical to v0.18.0 (the real median widening / narrowing). Street AI at
  v1280-1352: lateral -9.88 m from the new centreline, i.e. in the northbound lanes (v0.18.0: on the centre line).
- **Lanes vs the aerial.** On the clean NAIP sections (the classifier's grey also catches roofs, drives and shadows —
  only v1310 / v1334 read as exactly two carriageways): east slab edge 0.6 / 1.45 m from NAIP's northbound east kerb,
  island centre 1.75 / 2.3 m east of the median's centre, lane centres within 0.7-2.9 m of their carriageways; the
  west slab edge stops 2.6 / 3.45 m short of NAIP's southbound west kerb (never over the house lots). Same accuracy as
  College's existing runs (the island centres on the raw-offset midline; a later refinement could centre it on the
  true midline, which would move every run — not done).
- **The cut face vs 3DEP** (built TERRAIN on the diagnosis' 3DEP 1 m sections, east side): from the pavement edge the
  face rises at 0.99-1.07 m per metre to 7-15.5 m (v1216-1414), planar RMS 0.06-0.17 m on most sections; past the
  daylight + rounding the built ground sits 0.02-0.36 m off fresh 3DEP (the 2 m release lattice). The west side within
  20 m: unchanged from v0.18.0 except where the slab itself moved (v1261-1351, ≤ 1.0 m, the old swerve's verge).
- **Gates, Free Roam (no worse than v0.18.0):** drive_test street soft top 33 (33), severe 0 (0), kinks 3.27 /km
  (3.41), gated excursions 98 (98); audit 53 (53: K 20 / I 20 / F 13); verify_mouths ×4 PASS; verify_fold_fans PASS;
  verify_signs PASS; rib_check / house_seat_check PASS; verify_kn5 + --inis PASS (street ini = road + street + spawn).
- **Gates, Speedways:** barrier_bands self-gates 1-13 and the PLANNED no_route PASS (leak 0, both); BUILT no_route PASS
  both (leak 0, 0/411 and 0/400 probes, lap complete); drive_test barrier_missing 0 (38,065 stations, the chicane walls
  included), obstruction 0, severe 21 / 21 (v0.18.0 22 / 20 — race_acw's +1 is the lap seam's step, the built road
  there byte-identical (611 / 611 road + kerb vertices within 40 m), sampled 6.7 m further round because College is
  6.7 m shorter); audit 53 / 53 (53 / 53), W 0; verify_race (incl. --scenery-only) OK; verify_ai_line PASS both (dips 0,
  wall min 2.35 / 2.17 m); the lane's centre crosses 19.85 m (race_cw) / 20.38 m (race_acw) (v0.18.0 race_cw 18.4 m),
  walls at 1:3.2-3.5, radius ≥ 63 m.
- **Stills** (D:/k10-scratch/college/stills: before = v0.18.0, after = the rehearsal, compare/ side by side): Free Roam
  both seats show straight lane lines, the continuous island and barrier, the cut face on the uphill (east) side;
  Speedway and Speedway Reverse show the walled crossing; cut_face/ the wide view.

Open: the install and Kevin's seat (the only verdict). Not addressed here: the relayed "morew modern" (likely 0056's
streetlight).

---
id: 0044
title: "Arrow signs on TIGHT corners, where they actually go" — AT the corner, just past the outside edge, facing the approach; never as a warning before it
status: in-progress — rule judged and dry-run on the V3 data (read-only); the tools and the first kn5 with plates are the next commit; Kevin's drive decides
scope: tracks/san-diego-lake-murray (signs.json, data/signs.local.json, the 20 W1-6 plates, start_positions 0044-sign-*); engine scenery doctrine (scripts/environment/build_env.py road_signs rule superseded; scripts/ac/pbr.py SIGNPLATE/SIGNARROW keys in airoso + engine-july)
layer: project + engine
train: -
---

## Symptom (Kevin, seat, 2026-10-10)

> "we need to have you look at turn sign placement, we need arrow signs on TIGHT corners, where
> they actually go. You've been trying to place them as warnings before a corner but they go AT
> the corner, just past the outside edge. It's hard to describe but very easy to see when it's
> right or wrong."

Kevin's user-line for the pass: **"Tight corners, not right corners"** — the qualifier is the
radius and the deflection, never a 90-degree term, and never which way the road bends.

## Evidence

**What ships today.** The V3 kn5 carries no sign mesh at all: `tools/strip_scenery_blend.py:17`
strips only `PALMFROND/PALMTRUNK/TREECANOPY/TREETRUNK/SCRUB`, but V3 never runs `build_env`'s
scenery pass in the first place, and the SD config's `scenery` block
(`tracks/san-diego-lake-murray/track.config.json:189`) has no `road_signs` key. So this is a clean
re-introduction, not a relocation — nothing on the installed `san_diego_lake_murray_v3` has to be
found and deleted.

**The old engine rule** — `scripts/environment/build_env.py`, the thing Kevin is describing:

- `:1070-1071` — "euro road signs (scenery.road_signs): sharp-turn arrows at warning-barrier
  entries". The detector is the jersey-barrier walk, `scripts/geometry/kerbs.py:230
  warning_barriers`, run forward (`:1098`) and on the reversed lap (`:1102`), so every corner
  shipped a plate for BOTH directions — on a one-way lap that is a grey back per corner.
- `kerbs.py:299-313` — a "spot" is a run of per-vertex turn > 0.9 deg (`per_vtx_thr`), including
  the gentle lead-in and settle-out either side of the hard part; `apex_idx = (i + j) // 2` is the
  run's MIDPOINT, `start_idx` is 28 m before it. The walk is `i = 1 … n-1`, open-ended, so a
  corner straddling vertex 0 (M1, the lap seam) is two half-corners, each under the 60-deg
  triage — the old build shipped four mainline arrows, not five.
- `build_env.py:1115-1117` — the comment claims "at the corner apex on the OUTSIDE of the turn
  … facing the approaching driver", but `:1118-1130` does this: take the run midpoint, face along
  the tangent 6 stations earlier, then step PERPENDICULAR TO THAT APPROACH TANGENT by
  `max(widths[apex] / 2 + 2.8, 6.8)` on the side `_outside = -side` — a convention flip
  (`:1126`, "wrong side usually") that is right under `mirror_x` and wrong for SD's ENU frame.
- `:1131-1133` — never two plates within 150 m in one direction; `:1136-1140` the plate is a
  `USSIGN` cell of a transparent atlas (renders black under ksPerPixel — the lesson the lamps
  pass already paid for, ledger 0040: solids only).

**MUTCD, the placement Kevin is describing.** W1-6 One-Direction Large Arrow (2C.09): on the
outside of a turn or curve, in line with and at right angles to approaching traffic — i.e. the
spot a car that failed to turn would hit. 2A.17: on a curved alignment the plate's angle is set by
the approaching traffic's direction, not by the roadway edge it stands behind. 2C.10 para 05: no
arrow where the alignment does not change (a through leg is a junction, not a turn). The device the
old rule actually built — a plate 50-95 m upstream facing the approach — is the W1-1 Turn diamond
+ W13-1P plaque, a different sign with a different rule (Table 2C-3), and it is NOT in this pass.

**The survey + dry run** (scratchpad `signs/survey_corners.json`, 60 corners; `signs/ray_rule_mutcd.py`
→ `ray_rule_mutcd.json`, 89 approaches, read-only against the workshop's
`centerline.local.json` / `connectors.local.json`): on all five mainline tight corners the
failed-to-turn ray from the PC leaves pavement INSIDE the arc, 22-37 m past the PC and 12-34 m
short of the apex (`in_arc: true`), i.e. a plate there faces the car while it is still going
straight — the "AT the corner, just past the outside edge" Kevin means. Where the rule says no:
DCL-1's forward ray never leaves pavement (`exit: null` — the del_cerro_blvd#1 trunk continues),
MED-16's exits 6 m past its PT into Del Cerro Blvd's far curb (a T-end), MED-17's `outside_dot`
is -9.8 (the mouth flare), and the Alvarado S-curve Mb2/Mb3 is R 64-70 m at 45 deg — a curve a
driver takes without braking.

## Diagnosis

Two things made the old arrows read as "warnings before the corner":

1. **The point.** A step perpendicular to the APPROACH tangent through the run's midpoint lands
   the plate abeam of the bend, on the extension of the approach's outside curb line — beside a
   turning car, never in front of a car going straight. With the apex width (24-30 m flares at
   M2-M5) in the offset, it stood 15-17 m from the centreline, in the yard, and the only place a
   driver could see it from was well upstream.
2. **The detector.** The barrier run midpoint drifts toward whichever side has the longer gentle
   lead-in, the lap seam split M1, and the side was a convention rather than a geometric test.

The correct construction has no convention in it: launch a ray from the PC along the heading the
car had over its last 10 m, march until it is off ALL pavement, step back off the walk, stand
there, face straight back down the ray. Right/wrong becomes mechanical, which is what makes it
"very easy to see".

## Fix — the rule (judged 2026-10-10; full text in the pass brief, repeated here only where a number is load-bearing)

**Qualifies (TIGHT, direction-agnostic).** Detector = 1 m resample of every ribbon (mainline
modular so the seam corner is one corner; connectors open, both point orders because they are
two-way), heading from the 4 m chord, signed curvature over a 12 m window, corner = run of
|k| > 1/60 (gaps ≤ 10 m merged), apex = max |k|, PC/PT = the R 60 crossings with 6-station
hysteresis, D = heading change PC→PT (D < 0 = right). A W1-6 when ALL of: R_apex ≤ 30 m (the
loop's gap is R 14.4 → 38.7, so the number is not load-bearing); |D| ≥ 45 deg (keeps MED-7 at
47.8, drops the 13-30 deg curb-return bends); the failed-to-turn ray leaves ALL pavement with
5 ≤ s_C ≤ 80 m and its foot in [PC, PT + 10 m] (never leaves = junction with a through leg;
exits later = curve); apex ≥ 15 m from any mouth cut or connector end (else mouth flare,
skipped). **Hairpin clause:** |D| ≥ 135 and arc ≥ 50 m → a second W1-6 from the R 20 crossing,
kept if the bases are ≥ 12 m apart (M2 only, 51 m). Mainline signs the driven direction only
(clockwise — the AC_TIME_0_L witness); connectors get one plate per qualifying approach.
`kerbs.warning_barriers` is never the detector.

**Sign point.** Approach tangent t = unit(P[PC-2] − P[PC-12]). Launch A = P[PC] + right ×
(island/2 + (w_app − island)/4) with w_app = min width over [PC−40, PC] — the un-flared approach
(14.3 / 13.5 / 20.2 / 24.3 / 20.5 m at M1..M5), NEVER the apex width. Ray Q(s) = A + t·s; C = first
Q off all pavement (per-station half-widths in a spatial hash, margin 0 — the curb face IS the
ribbon edge). Keep marching the same ray until the perpendicular clearance to every ribbon edge
≥ d = curb_face 0.08 + walk 1.8 − 0.25 = **1.63 m** mainline (1.33 m on 1.5 m connector walks;
`scripts-v021/blender/build_loop_blend.py:658/677`), cap +6 m then step perpendicular. S = that
point: the post stands on the flat walk 0.25 m inside its back edge, 1.55 m of walk kept.
Outside assertion is geometric — cross(t_local(sC), C − P[sC]) > 0 for D < 0 — and a failure
aborts that corner by id, never relocates it. Clearances: lamp bases ≥ 3.0 m, plants ≥ 2.5 m,
resolved by sliding S ±1.5 m along the curb; lamps are never moved. Ground: BVH over
CURB + SIDEWALK + TERRAIN of the loop.blend COPY, ROAD rejected, analytic y_road(sC) + 0.24 wins
when the hit is > 0.30 m off (gapped walks at mouths). Post base sunk 0.30 m.

**Facing.** Plate normal f = −t exactly — the plate looks straight back down the heading the car
had before the hard turn, never the curb tangent, never the exit leg (at M2 it faces north up the
approach although the curb under it runs east-west). Arrow head along the driver's right for D < 0
(W1-6R), left for D > 0 (W1-6L); nothing else distinguishes left from right. ELI15 on the frames:
engine → Blender swaps two axes, which is a mirror, and a mirror turns every triangle inside-out;
so every triangle is emitted reversed (as `tools/author_lamps_blend.py` does) and that reversal is
the only thing that makes the plate face the car. The kn5 z-mirror needs nothing (the ENU frame
IS the real world: clockwise lap, signed area −8.87 km²). First-drive acceptance: at M1 a RIGHT
arrow straight ahead through the windscreen; a left arrow means every plate is mirrored and one
flip of the right vector fixes all 20.

**The sign.** W1-6, 48 × 24 in (1.219 × 0.610 m), yellow field, black arrow per FHWA SHS sheet
2-7 (39 in overall, 13.5 × 18 in head, 25.5 × 6.67 in shaft), bottom edge 2.13 m (7 ft, 2A.15
pedestrian areas) above the walk, centre 2.44 m. California companion ON by default: OM1-3 Type
N-1(CA) all-yellow 18 in diamond on the same post, top point 0.05 m under the plate — the one
thing that makes a San Diego arrow look Californian. One 2 in square galvanized post (SDM-104
look), base y_base − 0.30 to plate top + 0.05. Built as GEOMETRY, not texture: plate quad, arrow a
fan-triangulated 7-vertex polygon 4 mm proud, grey back on its own verts 3 mm behind (the prep's
weld and planar-UV overwrite are why artwork textures collapse and why the lamps use 64 × 64
solids). Materials: `SIGNPLATE` → `solid_sign_yellow.png` (255, 205, 0), `SIGNARROW` →
`solid_sign_black.png` (20, 20, 20), both keys added identically to airoso AND engine-july
`scripts/ac/pbr.py`, PNGs in both `assets/textures`, "generated, CC0-1.0" in `assets/licenses.json`
(keeps docs/PUBLISHING.md's CC0 split clean); `SIGNPOST` reuses the existing key (`pbr.py:89`).
Mesh names `SIGNPLATE_k / SIGNARROW_k / SIGNPOST_k`, visual-only (no `1` prefix), flushed below
60,000 verts. Never `USSIGN`/`mutcd_atlas`, never a `LIGHTS*`/`SIGNS`/`1*` name.

**Deliverables (this pass).** `tools/make_sign_textures.py` (two 64 × 64 solids, run once);
`tools/place_signs.py` (pure python, reads centerline / connectors / mouths / median_bands /
lights / scatter_positions + `signs.json`, writes `data/signs.local.json` — one record per sign
with corner, approach, ray, base, y_base {analytic, raycast, source}, facing, checks — and
`data/signs_preview.svg`, one 60 m top-down window per sign: pavement, lane line, A→C ray, curb,
walk band, post, plate, facing arrow, N arrow, scale bar — Kevin's "easy to see" picture BEFORE
any build); `tools/author_signs_blend.py` (Blender 4.2, opens loop.blend, deletes
`SIGNPLATE_*/SIGNARROW_*/SIGNPOST_*` first, BVH ground, emits the batches, always prints one
`[signs] N placed (...) K skipped` line even for zero — the ship pipe's grep exits 1 under
`set -euo pipefail` otherwise); `tools/verify_signs.py` (the eight checks below). Two lines in
`tools/ship_sd.sh` after the lamps step (`:70`) inside the `SKIP_BLEND` block; `signs.local.json`
added to the outputs-sync list (`:98-100`); `tools/make_treefx.py` reads `exclude_plants`.
Overrides live in `tracks/san-diego-lake-murray/signs.json` (`defaults{r_sign_max_m 30,
defl_min_deg 45, hairpin_deg 135, lateral_offset_m 1.63, lateral_offset_connector_m 1.33,
height_m 2.13, om1_3 true, skew_deg 0, include_connectors true, both_directions_mainline false,
lamp_clear_m 3.0, plant_clear_m 2.5, kappa_window_m 12, hysteresis_stations 6}`, per-corner
`skip | slide_along_curb_m | base_xz | face_bearing_deg | plate | arrow | second_arrow | force`);
an override whose detected apex moved > 30 m is refused with a WARN.

**Result on this loop — 20 W1-6, ship the 6 mainline first.**

| id | where | R / D | plate(s) | S (E, N), dry run | note |
|---|---|---|---|---|---|
| M1 | 70th St → Alvarado Rd (lap seam, v0) | 12.2 m / −95 | W1-6R, faces 27° | (−0.9, −1673.6) | ray exits in-arc 4-5 m past the apex; modular seam detector mandatory; ribbon width steps 27.5 → 17 m across segment 4497→0, so the Blender BVH-vs-ROAD test is authoritative here |
| M2 | Alvarado Rd → College Ave south hairpin (v770) | 9.2 m / −186 | W1-6R ×2, faces 19° / 104° | (−1962.0, −1290.2) + (−2008.0, −1267.2) | hairpin clause, bases 51 m apart; four W1-8R chevrons are the opt-in replacement for the second arrow |
| M3 | College Ave → Navajo Rd (v1514) | 10.3 m / −113 | W1-6R, faces 143° | (−1985.1, 613.2) | w_app 20.2 so lane_off 5 m; palm at 4.4 m passes clearance, sight-line check listed |
| M4 | Navajo Rd → Jackson Dr (v2319) | 9.6 m / −111 | W1-6R, faces 230° | (65.6, 1731.3) | Navajo's median run ends 22 verts earlier, no island term |
| M5 | Jackson Dr → Lake Murray Blvd (v3296) | 10.6 m / −89 | W1-6R, faces 307° | (2628.0, 504.6) | palm at 4.8 m, sight-line check |
| MED-1 | Wisconsin / Connecticut (v10) | 9.5 m / 72 | R fwd + L rev | fwd (85.8, −1452.1) | apex 28 m from the Lake Murray mouth passes the 15 m bar; the REVERSE plate stands in the Wisconsin throat 19 m from the cut — the fiddliest spot on the track, check its SVG window first |
| MED-6 | Connecticut → Delaware (v205) | 5.7 m / 120 | L fwd + R rev | (−68.1, −914.3) / (−65.3, −920.7) | sharpest connector corner; modelled pavement bends with no through leg → W1-6, not W1-7 |
| MED-7 | Delaware → Pennsylvania Ln (v245) | 14.4 m / 48 | L fwd + R rev | fwd (−183.1, −977.9) | kept by the 45° floor; the reverse ray exits 1 m past the PT (dry run `qualifies: false` at the literal arc, kept by the +10 m tolerance) — FLAGGED, Kevin can drop it |
| MED-8 | Pennsylvania Ln → Colorado Ave (v313) | 7.8 m / −88 | R fwd + L rev | fwd (−188.9, −1188.3) | after the 189 m straight — the most visible plate on the grid |
| MED-10 | Colorado → Adelante (v390) | 11.4 m / 63 | L fwd + R rev | fwd (−403.4, −1126.0) | reverse exits obliquely 9 m past the apex; the perpendicular-clearance march keeps it off the walk |
| MED-13 | Airoso → Del Cerro Ave (v701) | 13.5 m / −98 | R fwd + L rev | fwd (−1301.7, −1033.5) | reverse exit oblique (+4.5 m extra travel) |
| DCL-2 | Del Cerro loop east turnaround (v75) | 4.6 m / −150 | R fwd + L rev | (−540.9, −888.8) / (−539.6, −885.9) | probably a cul-de-sac turnaround nobody signs — Kevin's call, `skip: true` drops both |

Nothing at: Mb1-Mb18 (R 64-119 m, 8-46 deg: the Alvarado S-curve Mb2/Mb3 is a 30 mph curve,
curve-sign territory if advance signs are ever added), DC0-x / MED-2..5, 9, 11, 12, 14, 15
(R 33-55 m and/or < 45 deg — MED-14/15 at R 39-48 are the first to enter if R is ever raised to
50, and their posts would land on OSM SIDEWALK strips), DCL-1 (through-leg junction: the forward
ray runs 60+ m down the #1 trunk), MED-16 (T-end: the stem arriving at Del Cerro Blvd / Madra —
a W1-7 Two-Direction Large Arrow on the far curb, S ≈ (−1174, −604), is a SECOND PASS after
confirming the mouth mesh models the stem ending), MED-17 / MED-b1 / DC1-b2 (mouth flare, 4 / 13 /
10 m from a cut — skipped with a log line), and nothing at the modelled mouths where the host is
straight (College / Del Cerro v1085-1086, Lake Murray Blvd / Wisconsin v4424).

**Deliberately NOT in this pass:** the advance W1-1 Turn diamond + W13-1P plaque (driver's
right, 0-30 m before the PC, ≥ 30 m from any other sign, W1-11 Hairpin at M2/DCL-2), the four
W1-7 T-end plates, M2's chevron run (W1-8, 18 × 24 in vertical, Table 2C-5 spacing 12.2 m for
R < 61 m; only M2 has room for ≥ 3, and only after Kevin drives the two-arrow build), the night
retro-reflective pop (ksEmissive under NIGHT_SMOOTH for `SIGNPLATE_mat` — an `ext_config.py`
follow-up once 0043's workflow releases that file), and counter-direction mainline plates (the
real streets carry no arrows at these five junctions, so `both_directions_mainline=false` costs
no realism and saves five grey backs).

**Junction honesty.** In the model M1-M5 are two-leg bends of one road ending at a curb (nearest
mouth or connector end 219-3196 m away), so the modelled alignment changes and the W1-6 applies;
the real-world signalized cross streets are not in the model and the rule does not pretend they
are. The dossier records the five arrows as track furniture, not a survey finding; the moment a
through leg or stub is modelled at any of them, the ray stays on pavement and that corner drops
out automatically.

## Scope

- **Project** — `tracks/san-diego-lake-murray`: `signs.json`, `data/signs.local.json`,
  `data/signs_preview.svg`, the 20 plates, the `0044-sign-*` spawns. Proof cases: M1 (seam
  corner + the 0034 width step), M2 (the hairpin pair), MED-1 reverse (the Wisconsin throat).
  Regression cases that must stay UNSIGNED: Mb2/Mb3 (R 64-70 at 45°), DCL-1 (through leg),
  MED-17 (mouth flare).
- **Engine (doctrine)** — the "warning before the corner" construction in
  `build_env.py:1070-1140` is superseded for every street_port and circuit_port that builds
  furniture: the arrow goes at the failed-to-turn point, outside, facing −t; the detector is the
  curvature/ray rule above, never `warning_barriers`; the side is a cross-product, never a
  convention; the offset uses the un-flared approach width, never the apex width (the Colorado
  tracks' 15-17 m yard plates are this bug). Lookout Lariat and the SD freeway network inherit the
  rule on their next furniture pass. The `SIGNPLATE` / `SIGNARROW` pbr keys land in both engine
  copies in the same commit (fleet/REALISM.md §6 — street ports' presentation floor names
  signage first).

## Verification (decided before the fix)

1. `tools/verify_signs.py` on `data/signs.local.json`, exit 1 on any failure: (a) the ray from A
   along t at 2.0-3.0 m above the road strikes the plate within ±0.61 m of its centre; (b)
   |angle(f, −t)| ≤ 1°; (c) 1.3 ≤ perpendicular clearance ≤ 3.0 m; (d) outside cross > 0; (e)
   plate bottom = y_base + 2.13 ± 0.05; (f) post base = y_base − 0.30 ± 0.05; (g) no SIGN*
   vertex within min(lane_half, 6) + 0.3 m of any centreline (the drive_test disc: 6.3 m mainline,
   4.9 m on 10 m streets; posts land at 10-17.5 m and ~6.9 m) nor inside any pavement polygon;
   (h) exactly one sign per qualifying approach (+1 per hairpin), none at a skipped id. Listed
   extension: the sight line (eye 1.1 m, 60 m back along the lane, trunks within 1.5 m of the
   line) — move the sign ±1 m along the curb, never the palm. The 200 m spawn exclusion in (h)
   reads the SHIPPING starts (grid v2976 Jackson / v1078 College), not `start_positions.active`:
   the `0044-sign-*` spawns below deliberately sit 90 m from a plate.
2. `data/signs_preview.svg` — Kevin looks at the twelve windows before any build; a plate that
   looks "one lane off" from the seat is fixed with `slide_along_curb_m`, never by changing the
   formula (starting the ray from the centreline instead moves S only 4-5 m along the same curb
   and the facing is identical).
3. Gates unchanged: drive_test (plates outside the 6.3 m / 4.9 m disc, bottoms above its 1.8 m
   ceiling), audit_mesh (never reads SIGN*), verify_kn5. `kn5_ground_check`'s SIGNPOST bucket
   (`scripts/ac/kn5_ground_check.py:28, :394`, 0.08 m) is not run by `ship_sd.sh` and would flag
   the 0.30 m sink if it ever is — exempt the bucket or sink 0.08 m then.
4. **Kevin's drive — the only ground truth.** `active: "0044-sign-M1"`: a RIGHT arrow straight
   ahead through the windscreen, past the outside curb, as the car reaches the turn. Then M2's
   pair, then M3-M5, then the grid. Per corner his verdict is right or wrong; a wrong one is a
   `signs.json` override with its reason, and a wrong PATTERN reopens this entry.

## Start positions (added this day, `tracks/san-diego-lake-murray/start_positions.json`; `active` unchanged)

| key | vertex | offset | where |
|---|---|---|---|
| `0044-sign-M1` | 4463 | 5.0 | 70th St southbound, 90 m before M1's PC (station 13468), 103 m before the seam apex; 13.5 m road |
| `0044-sign-M2` | 721 | 5.0 | Alvarado Rd at the Mb6 kink, 89 m before the hairpin's PC (2249), 111 m before the first plate; 13.0 m road |
| `0044-sign-M3` | 1478 | 6.0 | College Ave inside the third median run (island 7.0 m — 2.5 m off its curb), 91 m before the PC (4525); AC_TIME_2 31 m ahead |
| `0044-sign-M4` | 2284 | 6.0 | Navajo Rd in the tail of the second median run (island 2.2 m), 89 m before the PC (6941) |
| `0044-sign-M5` | 3261 | 5.5 | Jackson Dr, 42 m before the Mb16 kink and 89 m before the PC (9869); 17 m road |

Connector corners (MED-1 … DCL-2) have no spawn entry: `tools/set_start_blend.py` indexes
`vertex` into the MAINLINE centreline only, and an entry it would misplace is worse than none. A
`connector` key in the registry + the mover is the small follow-up if Kevin wants to spawn on the
grid rather than drive there.

## Status at filing (2026-10-10, evening)

Judged and dry-run only. Exists: the survey (60 corners) and the ray dry run (89 approaches) in
the session scratchpad, read-only against the workshop data; nothing under `scripts/`, `tracks/`,
the workshop, the installed track, `ext_config.py` or `loop.blend` was modified, no Blender run, no
kn5 export. Next: the four tools + textures + pbr keys + `signs.json` in one commit, the Blender
authoring proven on a COPY of `loop.blend` under the scratchpad, then the next `ship_sd.sh`
rebuild with the 6 mainline plates, then Kevin's drive from `0044-sign-M1`.

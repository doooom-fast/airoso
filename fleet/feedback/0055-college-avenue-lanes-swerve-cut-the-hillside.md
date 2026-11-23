---
id: 0055
title: College Avenue's split section and College/Navajo continuity — Drive 2, realism+; connected split-level roads before race features
status: open
scope: tracks/san-diego-lake-murray (College Ave mainline between the College hairpin and the College/Navajo box; median_bands / connector islands there; race corridor on College)
layer: project (+ engine if the ribbon/median sweep is the cause)
train: -
---

## Drive 2 — College remains unresolved (Kevin, 2026-10-27, v0.19.1)

**This seat report supersedes the older rehearsal's claim of a fix, not its historical measurements.**
Drive 2 is "great" overall, but College is not accepted:

> "drive 2 is great with some issues on college ave: it seems to go around a hill that the actual road cuts through, making one direction swerve onto the other and the whole thing go outward in a way that’s not realistic. same with the junction at college and Navajo: it seems to jut inwards, making you have to swerve through the intersection to land correctly past Navajo which isn’t correct. the thing is about the college part that goes around the hill: i _do_ want the race course to continue to change which side of the road it’s on there for a kind of chicane"

Kevin then qualified the race-design request:

> "it may not be realistic though to leep that chicane, if the lanes are diverged there in real life, but we don’t diverge them here"

### Design decision — realism+ (same conversation, supersedes conditional retention)

Kevin then chose the direction:

> "can you split them up and do something fun? i would prefer realism+"

And identified the failure to avoid:

> "claude has a hard time splitting up lanes and keeping a coherent system in place"

**Author the real separated, separately graded carriageways as one connected road system.**
This supersedes the previous one-slab simplification and the requirement to retain its crossover chicane.
Race enjoyment must fit the real road; no specific replacement race feature has yet been selected or sourced.
Do not preserve a defective street alignment to keep a race feature, or invent a crossover through the hill.
College/Navajo's unwanted through-junction swerve is a separate correction, not an intentional chicane.

The old `route.split_carriageways` mechanism stays deleted (0032/0035). The new approval is for authored,
connected split-level roads, not re-enabling independent `_opp` ribbons that start and stop mid-street.

The older research below describes northbound 2.4–5.9 m above southbound, while the model uses one slab at
southbound grade. That is existing research, not a fresh measurement of the installed v0.19.1. The earlier
"Kevin's choice" language about that simplification must not be read as renewed acceptance after this feedback.

### Evidence and next verification

- Current `track.config.json` still declares `route.median_registration`, `terrain.ground_release.zones`
  entry `college_split_cut`, and the race-only `race.chicanes` entry `college_split`.
- Read-only inspection of this checkout's `median_bands.json` finds one College run v825–1509 and no zero
  island widths at v1190–1430. The cached intermediate does not exhibit the old split-run gap; this does not
  establish what the Windows install loads or whether the current street is realistic.
- The previous fix deliberately retained the College run-end taper into Navajo (old verification below,
  v1493–1509); registration also returns to zero by v1505. Inspect their combined effect and the J1 Waring
  mouth against the real through alignment. **Candidate to investigate, not a proven cause.**
- Before another geometry edit, compare the artifact AC actually loads with these declarations and the
  real-road reference. Do not assume the old gap returned or that a rehearsal proves the installed road.
- This Mac checkout has only a Git LFS pointer for `loop.blend` (134 bytes), no `data/track.obj` or
  `data/track.street.obj`, and no local confirmation of the Windows-loaded artifact. `tools/ship_sd.sh`
  still names retired Windows workshop/engine paths; do not run those defaults against retired repos.
  Git LFS is unavailable; installed Blender is 5.1.2, not the pinned export version 4.2. System Python also
  lacks numpy/scipy/shapely/pytest. Built-geometry diagnosis and a corrected export remain unperformed here.
- Acceptance: a registered aerial comparison and built cross-sections through the College cut, a continuous
  through-junction lane trace across College/Navajo into Waring in both directions, the existing built-artifact
  gates for Free Roam and both Speedways, and Kevin's repeat drive. Resolve the race crossover design explicitly;
  no gate thresholds are changed and no new tier is claimed.

### Bounded proof before network integration

1. Recover the canonical LFS `.blend`, inspect its authored collections without regeneration, and obtain
   the loaded v0.19.1 artifact/manifest for comparison. Use a scratch copy and the pinned author/export tools.
2. Register the real carriageway edges and elevations in the engine frame, with served aerial extents
   (the two frame errors documented below must not recur). Select both ends at real connections, not a
   separation-distance threshold. Include the approach to College/Navajo/Waring in the proof.
3. Author both carriageways, the median/cut and both transitions together. Shared boundary vertices,
   single-coverage pavement, and no sidewalk across an opening are the contract (`docs/JUNCTIONS.md`).
   No broad old slab remains hidden underneath the separated road and median.
4. Reuse the existing pad authoring and built-pad verification where applicable
   (`tools/junction_pad.py`, `author_junction_pad_blend.py`, `verify_pads.py`); do not assume their current
   J2–J4 connector-arm support already handles a cut through MAINLINE at J1.
5. Check every consumer before integration: terrain seating must use the correct carriageway/layer; paint,
   curbs, lamps and barriers its actual surface; race paths their own named road pieces and junction paths.
   `scripts/geometry/race_lap.py` offers named pieces, but its straight joins are not proof of a drivable
   junction and it currently inherits race settings. Old mainline-indexed chicane declarations cannot
   silently carry onto a new piece sequence. No GPS-generated AI spline is part of this fix.
6. On the BUILT proof, demonstrate connected pavement through both transitions in both directions,
   through College/Navajo/Waring and along the intended turns. A connectivity check must consider height
   and actual seam adjacency, not plan overlap alone. Check median/cut contact, no pavement duplication,
   no grass/curb obstruction, and both race layouts' containment. Any necessary new gate is documented
   in GATES-CHANGELOG with its change; no threshold is relaxed to accommodate the split.
7. Only after that proof, integrate with the shared road model, run all existing gates and compare the
   unaffected network with v0.19.1. Seat screenshots and Kevin's repeat drive decide acceptance.

**Status:** investigation and design decision recorded; no split geometry authored, no export, no install.

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

**Measurement frames (round 2: every round-1 aerial number was off).** Two errors sat under the first diagnosis and
round 1's own checks. (a) The diagnosis scripts projected NAIP / 3DEP on a sphere (R 6371 km) while the engine projects
with the WGS84 series (`scripts/geometry/projection.py`): 3.6 m east-west at College's x ~ -1730 m (the truth lens).
(b) The NAIP ImageServer, asked for an EPSG:4326 window whose degree pixels are not square, WIDENS the latitude extent
to make them square (its `f=json` reply: the diag tile was served over 32.785474-32.792317, not the requested
32.786017-32.791773), so a tile read on its requested bbox is squeezed ~16 % north-south about its centre: 3-12 m on
College, ~0.3 of that sideways (found 2026-10-14 by cross-correlating two tiles: 12 m apart until read on their served
extents, then 0.0 m, r = 0.998). Everything below is in the engine frame, NAIP 2022-04-25 (m_3211716_sw_11_060) read on
its served extent, fresh USGS 3DEP 1 m through `scripts.elevation.usgs_3dep` (TLS on). The two sources are independent
and agree on the real median's middle within ~0.5-1 m.

**Mechanism of the swerve (file:line, v0.18.0).** `tools/median_envelope.py:196` trusted a vertex only while
`MIN_SEP <= s <= SEP_TRUST (24 m)`, `s` = the RAW centreline's offset to the opposing OSM way. The raw line is built from
the southbound OSM way with the WGS84 series, but the tool projects OSM on a sphere (`_meters_per_degree`: 93,479 m per
degree of longitude against the line's 93,676), which puts BOTH OSM ways 3.6 m east of the line's own way at College.
Over v1282-1350 `s` therefore read 24.1-24.7 m where the two ways are 20.5-21.2 m apart, rejected by the upper bound
alone. The 69-vertex gap exceeded `GAP_BRIDGE` (8): the run split, each end took the cosine taper (shift -11.8 -> 0 over
v1262-1280, 0 -> -11.1 over v1352-1370; width 32 -> 17 m), the island was pulled back. Between the run ends the slab fell
back to the single southbound alignment +-8.5 m: the northbound lanes painted on the southbound carriageway, the real
northbound carriageway left as green hillside (Kevin's two observations). Round 1 attributed the 3.6 m to OSM drawn east
of the aerial; that reading came from the sphere frame. `barrier_bands` inherited the jog: race_cw's lane swung 18.4 m
(the chicane Kevin likes), race_acw only ~4 m.

**Where the real road is, and where v0.18.0 / round 1 put it.** Laterals from the raw line (+ west), 61 sections
v1190-1430: the real median's middle (3DEP: the half-height point of the slope between the two benches) runs -6.8 ->
-7.8 (v1250-1310) -> -6.3 (v1350) -> -5.2 (v1370-1400); NAIP's northbound carriageway ~[-23.5, -12], vegetated median
~[-12, -2.5], southbound ~[-2, +9.5]. OSM draws both ways 2-4 m east of their pavement and the tool's sphere projection
adds 1.3-2.1 m, so every College median run sits east of the real road: island centre minus the real median middle
-3.4 m (v0.18.0, median of 33 sections) and -4.3 m (round 1, 61 sections, up to -5.9). Round 1's continuous island stood
mostly on the real northbound carriageway and ~6 m of its southbound lanes on the real median slope. The truth lens's
-5 to -7 m (NAIP) carried the extent error; its 3DEP figures stand.

**What the real road is.** A divided road on a hillside, split level: the northbound carriageway rides a bench over the
southbound one (+2.4 m at v1216, +5.5-5.9 m over v1243-1290, +5.0-5.3 m to v1342, fading to +1.6-1.9 m by v1396-1414);
east of it the hill rises another ~5-9 m (a real cut, ~0.55-0.6 V:H, its toe at L -22..-29); west of the southbound
carriageway, house lots at grade. No opening between Del Cerro and Navajo.

**L3 note (Kevin's choice, recorded).** The build carries both carriageways on ONE slab at the southbound grade (ledger
0037), as v0.18.0 did on both sides of the gap: through v1238-1330 the northbound lanes run 5.0-5.89 m under their real
bench (worst v1258), easing to ~1.6-2 m by v1390-1430. Kevin's ask (one road with a flat cut face on the uphill side) is
that simplification made deliberate. Its price is the cut face: it rises from the deck, not from the bench, so it stands
up to about twice the real cut's height (Verification).

## Fix (branch worktree-wf_6ef1e18f-ee6-2, rehearsed full chain on scratch, NOT installed)

1. **One divided run.** `tools/median_envelope.py` `trusted()`: the upper bound reads the two carriageways' separation
   (opposing way's lateral minus the ridden way's lateral), which a uniform OSM-vs-line offset (the sphere projection's
   3.6 m here) cannot change; the lower bound, the along-the-road test and every threshold unchanged. The projection is
   NOT changed: on the WGS84 series a replay drops College v825-980's island (true separation 7-11 m < MIN_SEP) and adds
   a Navajo run v2037-2161, two medians Kevin drives every lap, outside this ledger; filed as its own follow-up.
2. **On the real road (round 2).** `route.median_registration` (track.config.json; `median_envelope.registration`):
   the finished College road moves sideways onto the measured real median, cosine between declared points: 0 at v1104
   (past the Del Cerro mouth's island gap), +2.0 (v1190), 2.6, 3.4, 4.2, 4.5, 4.7 (v1330), 5.5 (v1355-1375), 4.3, 3.75
   (v1430), 4.2 (v1485), 0 at v1505 (inside the run's own taper into the Navajo box). Measured as above (3DEP + NAIP,
   smoothed +-10 verts). Height untouched. Guarded: points inside one divided run of the named road, ramps declared,
   |lateral| <= 6 m.
3. **The California cut.** Zone `college_split_cut` (terrain.ground_release, east side, centreline v1197.6-1468.5): the
   ground east of the slab is real 3DEP cut back by the existing 1:1 earth batter from the east pavement edge, read out
   to `cut_reach_m` 20 m (= clamp_corridor_m), the top rounded over `round_m` 3 m, `rails: false`. With the
   registration the built cut's toe stands at the real cut's toe.
4. **Zones by vertex (round 2).** `tools/ground_release.py`: a zone may name its extent by centreline vertex (`v`)
   instead of station. College's realignment shortens the lap 6.6 m, which slid the station-declared Lake Murray Blvd
   I-8 span / creek zones 6.6 m off their abutment (rails and ground at the seam moved). `lmb_i8_span`,
   `lmb_alvarado_creek` and `college_split_cut` are vertex-declared now (their v0.18.0 places); the zones before College
   keep their stations (byte-identical there). The race corridor's Jackson / Lake Murray Blvd box apex is declared v3296
   (the detector's 1 m stations moved with the lap; the corner and every vertex past v1510 are unchanged).
5. **The Speedways keep a chicane.** `race.chicanes` `college_split` (out leg v1253-1289, back leg v1343-1379): in each
   Speedway the closure sweeps into the far curb strip while a race-side wall sweeps in parallel from the race-side
   strip, both pinned; the lane holds the far carriageway ~160 m and comes back (race_cw crosses to the southbound
   carriageway, race_acw the mirror). Round 2: the planned no_route's pocket probes are spaced by travel on the reverse
   layout too (race_acw had 1 where race_cw had 12; now 12 / 12), and `write_ai_line` holds the race line wall_clear +
   0.5 m (3.0 m) off both walls through a declared chicane (with the 1 m hard bound the smoothed line cut each bend of
   the S to 2.17 m off its inside wall: every new verify_ai_line V2 under-band run of round 1).
6. **Free Roam keeps the island the Speedways cross.** The median over v1253-1379 is street-only
   (`1KERB_sidewalk_streetonly_median`, `1WALL_guard_streetonly_median`) in `<slug>_street.kn5`, loaded by Lake Murray
   Free Roam only; no median shrubs over that span (TreeFX is track-wide).
   Every invented number is in fleet/GATES-CHANGELOG.md (2026-10-14, ledger 0055, rounds 1 and 2).

## Verification (round 2, on the BUILT rehearsal D:/k10-scratch/college/ship4, engine frame)

- **No swerve.** One College run 825-1509; the island non-zero v1100-1487. Lateral displacement from the pre-median
  line every ~25 m over v1230-1400: largest change 0.47 m (v0.18.0 7.88 m); the run-end taper into the Navajo box
  (v1493-1509) is v0.18.0's. Street AI at v1280-1352: -9.88 m from the centreline, in the northbound lanes.
- **Lanes vs the real road** (61 sections v1190-1430; model minus real, + west; v0.18.0 / round 1 / round 2): island
  centre vs the 3DEP median middle -3.4 / -4.3 / **-0.02 m** (round 2 |max| 1.0 m on all 61); vs NAIP's median -4.9 /
  -5.1 / **-0.5** (|max| 2.0, n 22); northbound lane centre vs NAIP -3.8 / -4.1 / **+0.1** (|max| 1.8, n 20);
  southbound -5.1 / -5.5 / **-1.4** (|max| 2.9, n 13); east slab edge vs NAIP's northbound east kerb **+0.1** (17 of 20
  within +-2 m, the rest -2.6 / +2.6 / +2.7); west slab edge vs the southbound west kerb **-1.1** (10 of 13 within
  +-3 m; at most 1.1 m past it, no pavement on house lots; the -4.2 / -4.6 outliers are driveways NAIP reads as
  pavement). Aerial sheet: stills/compare2/aerial_lanes.png.
- **The cut face vs 3DEP** (east side, 57 sections with a face): the built toe at the real cut's toe (-2..+2 m on 54 of
  57; v1254-1258 read 6-10 m where 3DEP's toe is irregular); 0.94-1.09 V:H, planar RMS <= 0.17 m; daylight 3-18 m from
  the edge (inside cut_reach 20 m); the cut up to 7.2 m into 3DEP (round 1 10.3 m). Because the face rises from the deck
  it stands up to ~15-18 m at v1290-1300 where the real cut above the bench is ~8-9 m: the L3 price. Past the daylight,
  inside the zone: |built - 3DEP| <= 0.68 m, mostly <= 0.25 m (the 2 m release lattice). Road vs 3DEP: southbound lanes
  -0.20..+0.42 m; northbound lanes 1.4-5.89 m under the bench.
- **Ground beyond the construction zone.** Every TERRAIN vertex >= 40 m from a pavement is exactly the 3DEP height the
  tier planner sampled for it: 5,762 / 5,762 in round 2, 5,852 / 5,852 in v0.18.0 (0 off by > 0.05 m). What changes is
  which lattice nodes exist: the planner's 5 m band follows the road (within 60 m of a pavement, ledger 0046), so on a
  2 m grid 1,882 of 81,887 points >= 40 m out moved > 0.05 m (298 > 0.5 m, max 2.54 m), 1,148 toward fresh 3DEP and 734
  away (median |error| 0.155 vs 0.214 m). No real relief is reshaped.
- **Gates vs v0.18.0** (round 2 chain). Street soft top 32 (33), severe 0 (0), kinks 3.41 (3.41), gated excursions 100
  (98); race_cw severe 25 (22), kinks 6.61 (6.23); race_acw severe 22 (20), kinks 6.46 (7.05), steps 4.90 (6.75);
  barrier_missing 0 and obstruction 0 on all three. The raw increases are sampling: drive_test's 1 m and 150 m stations
  start at v0, so College's 6.565 m shorter length re-samples everything after it. A phase harness (a read-only copy of
  drive_test, start offset only) on v0.18.0's OWN mesh at +6.565 m reads 102 / 26 / 25 and kinks 3.19 / 7.20 / 7.20.
  Matched by place: race_cw severe steps before College 8 = 8, on College 0 = 0, after it 17 = 17 at the same vertices
  (v0.18.0 aligned); race_acw 13 = 13, 0 = 0, 9 = 9; street excursions before 34 = 34, on College 0 (v0.18.0 4), after
  66 vs 64. The +2 is v3806 (0.13-0.14 m drops beside a Lake Murray Blvd flare, mesh identical), gated now because
  drive_test's flare exemption reads the lap's MEDIAN width, which College's continuous divided run raises 17.0 ->
  17.64 m; the I-8 deck edge drop at s 13353 (4.9 m) is v0.18.0's own at s 13359.5, sampled now. Audit 53 on all three
  layouts (D 0, E 0, K 20, I 20, F 13, W 0) = v0.18.0. verify_mouths x4, verify_fold_fans, verify_signs (23),
  verify_race + --scenery-only, rib_check, house_seat_check (153 buildings, 0 floating / sunken / buried), verify_kn5 +
  --inis: PASS. Speedways: barrier_bands self-gates 1-13 and planned no_route PASS; BUILT no_route PASS (leak 0,
  0 / 411 probes, 12 chicane-pocket probes each); the lane crosses 19.85 m (race_cw) / 20.38 m (race_acw);
  verify_ai_line PASS, wall min 2.52 / 2.385 m (2.544 / 2.386, the same non-College places), under-band 0 m / 6.0 m
  (0 / 6.0): round 1's chicane under-band runs are gone.
- **Stills** (D:/k10-scratch/college/stills/after2; compare2 = v0.18.0 | round 2): Free Roam from both seats shows
  straight lane lines, the continuous island and its barrier, and the cut face on the uphill (east) side; both Speedways
  show the walled crossing; cut_face/ has the wide view.

Open: the install and Kevin's seat (the only verdict). Not addressed here: the relayed "morew modern" (likely 0056's
streetlight).


## v0.18.1 integration (2026-10-14; merged with 0056 + 0057, full rehearsal r2, NOT installed)

College's plan in the combined build is the verified one: centreline x/z identical at all 4,499 vertices to this
ledger's rehearsal (D:/k10-scratch/college/ship4), `median_bands.json` identical, widths identical; heights differ only
inside 0057's windows (v0-83, v737-849, v4422-4498 — College's split run v1100-1506 untouched). Chicane walls on both
Speedways: one declared, one object, off-curve max 0.006 m, pins 0.001-0.005 m from the race line at v1253 / v1379.

**Race severe re-measured on the combined build: cw 15, acw 20 (v0.18.0 22 / 20)** — no longer above v0.18.0. Place by
place (severe steps mapped to vertices on both builds): cw −4 Alvarado v5, −4 College/Alvarado junction (0057), −1
Navajo v1514, +1 LMB v3300, +1 the 70th seam fold fan v4495-4497; acw −2 Alvarado, −2 junction, +4 the 70th seam fold
fan (0057's raised deck, outermost fixed paths). **Street gated excursions** read 100 against 98 on r2: −4 here
(v1302 / v1352), sampling ±1-4 elsewhere (v0.18.0's own mesh on these stations reads 102), +2 at v3806 where the mesh is
unchanged but drive_test's flare exemption follows the lap's median width, which this run's one divided College run
raised 17.00 → 17.64 m, and +4 at v4457 (see the fix round below — not ledges; GATES-CHANGELOG v0.18.1). Stills: D:/k10-scratch/v0181/stills/freeroam_college_nb_*.png, D:/k10-scratch/v0181/stills/speedway_chicane/,
D:/k10-scratch/v0181/stills/speedway_reverse_chicane/.

### v0.18.1 fix round (2026-10-14, rehearsal r3)

Correction to round 2's note above ("the I-8 deck edge drop at s 13353 (4.9 m) is v0.18.0's own"): that was true of this
ledger's own build, whose Lake Murray Blvd deck still stood at v0.18.0's height. In the combined build 0057 puts that
deck at its real 3DEP height, so the same drop is 6.05 / 6.32 m (v4457 ±10.0 m). It stands behind the deck's 0.95 m
bridge-rail panels at ±6.90 m, which drive_test's guard probe could not see (a vertical panel has no plan area). The
probe now credits a 1WALL the car's path crosses (GATES-CHANGELOG v0.18.1 fix round): street excursions **96** on r3,
**96** on v0.18.0's own mesh under the same probe (98 / 100 under the old one). College is untouched by this round.
Centreline, widths and `median_bands.json` are byte-identical to r2, and both Speedway chicanes are as verified.

## Round 2, stage A (the PC, 2026-11-22): measured, designed, a proof scene; no geometry in the build yet

Files: `tracks/san-diego-lake-murray/source/college_r2/` (README there has the numbers and how to rerun).

- **Measured** (USGS CA_SanDiegoCo_D24 2024 lidar, class 2, read by the G10; NAIP 2022 for the pavement): the road is
  split level from about v1180 to v1440. Northbound over southbound: 1.3 / 2.2 / 3.1 / 5.4 / 5.8 / 5.3 / 5.5 / 5.1 /
  1.2 / 1.9 / 1.0 / 0 m at v1180 / 1200 / 1220 / 1240 / 1260 / 1280 / 1320 / 1340 / 1400 / 1420 / 1440 / 1460. Each
  carriageway is about 10 m of pavement; the planted bank between them is median 10.5 m wide. The build is one slab at
  the southbound grade, its northbound half up to 6.1 m below the real carriageway. The built outer edges sit a median
  0.5 m (east) and 2.0 m (west) from the measured ones.
- **Designed** (`college_design.json`): four control points across the road at every vertex v1130-1480; v1297-1300
  bridged under the trees; northbound over southbound up to 6.17 m; long grade 9.5 % northbound, 9.3 % southbound (as
  built 8.7 %); the ends meet the built road within 5 cm. Authoring keeps the built outer edges and rebuilds the middle
  and the northbound height.
- **The race on College:** each direction on its own carriageway: Speedway on the upper northbound road, Speedway
  Reverse on the lower southbound one. The Mac decided it from the race corridor's standing rule, "an Alvarado-wide
  lane on your own side of every road" (ledger 0049 section 9, the layouts' description; cited in ledger 0054 for the
  median noses). Those are the layout description's words, not a sentence Kevin typed; he was asked on the PC the same
  evening and had not answered. This replaces the crossover (`race.chicanes` entry `college_split`), which goes when
  the split is built.
- **Proof scene** (`college_proof.jpg`): before and after from three cameras. A shape study, not a game mesh.
- **Next:** stage B, on a scratch copy of `lm_phase2/project`: both carriageways, the bank and island, the two
  transitions, J1 tilted to its measured 6.08 % toward Waring as one change, then every consumer listed under "Bounded
  proof" step 5; stage C, a full rehearsal through the Mac's queue. No gate threshold changes.

## Round 2, stage B step 1 (the PC, 2026-11-22): the split as road data; nothing in the build yet

The design is in `tracks/san-diego-lake-murray/source/college_r2/STEP-DESIGN.md` (option B of `CONSUMERS.md`: two
roads, each with its own line; the two ends are plain road, not pads: step 2 below). The base is Lake Murray 0.20.4 (round 1c, ledger 0099),
merged into `claude/lm-finish-r2-20261122`. The College step runs first in the author phase (college, `lamp_heads`,
`walk_grade`, the race steps), so `walk_grade` grades the rebuilt walks like any other street's.

- **Step 1, the data** (`college_split_data.py` -> `college_split.data.json`, `college_split.png`; no Blender), written
  only into a scratch copy of the project. The mainline is the southbound road (345 vertices moved, v1131-1475, numbers
  kept, up to 10.67 m west, 9.99 to 15.34 m wide); the northbound road is the piece `college_nb` (273 points, 8.36 to
  14.1 m wide, up to 5.81 m over the southbound road); the bank between them has no width at the nose and the tail
  (the two roads meet in a point there) and is up to 12.18 m wide. The lap `college` (mainline, the piece, mainline, two declared joins) stitches with the mainline's own
  4,498 vertex numbers; Mission Gorge Speedway's lap is unchanged. Largest turn between 3 m segments 1.53 deg (the
  built line: 1.08); largest grade step between segments 0.65 points (built: 0.57). Heights: the built west edge
  keeps its place and its height (stage A: the west walk, the house lots and the ground behind them stay put), and
  the lidar gives the shape laid onto it: each road's crossfall (within about 5 %) and the northbound road's rise.
  So absolute heights stand off the lidar by what the built west edge does (-0.54 to +0.83 m): **they are the built
  edge's heights, not measured ones; only the crossfall and the northbound rise are measured.** The offset is
  recorded per vertex in `source/college_r2/college_datum_offset.json` (v, station, built edge, lidar there, built
  minus lidar). Where the built height came from is not established (within 0.4 m of
  `data/centerline.elevation.json`'s smoothed 3DEP profile, but not that profile). Putting College on the lidar
  would move the west walk and the house lots: on the list for after College, not in this round.
- **The no-route gate and the forks (CORRECTED 2026-11-23).** This note first said the no-route gate did not cover
  the forks and that a green gate "says nothing about those four openings". That was wrong. `race_lap.stitch` does
  skip the other carriageway as a mouth ("the branch is the lap"), but `tools/no_route.py` floods every cell within
  half the road's width + 25 m of the lap's line and fails any reached cell outside the declared corridor, so an
  unsealed fork is a leak it reports. Step 4 declared the corridor through each fork (the closure run to the point
  where the roads part); no probe was added by hand.
- **`college_edges.json`: `built_from_m` / `built_to_m` are not edges.** They are the built road's extent floored to
  the lidar's 0.5 m cells (they step by half a metre from station to station; a midline taken from them turns 5.9 deg
  between segments). The built outer edge is half the centreline's width (ROAD's own edge column). Stage A's decision
  to keep the built outer edges stands; nothing may read those two fields as the edge.
- **The Speedway lane on the northbound road follows the real road** (the Mac, 2026-11-22): the corridor is narrowed
  to the measured carriageway on that piece (8.36 m at its narrowest, against the 11.36 m it asks for elsewhere); the
  road is not widened to fit the corridor, and a gate that cannot pass on the real width is reported, not loosened.
- **The race on College:** built as decided above (each direction on its own carriageway); Kevin's answer on the board
  wins if it differs.

- **Step 2, the ribbons** (`college_split_blend.py`, on the scratch scene only): the mainline rows become the southbound
  road, the northbound road is a new ribbon in ROAD; 41,072 plan samples, every one on pavement under exactly one face
  and every one on the bank under none; a second run changes nothing. The forks turned out to need no pads: with the
  built outer edges kept, the built rows already pave them (tilt eased in, a fan of six faces where the two roads begin).
  The island begins and ends in a point. Walks, the old island, paint, lamps and ground are the next steps.

- **Step 3, the middle** (`college_middle_blend.py`, scratch scene only): the old island, its grass top, its barrier, the
  street-only pieces and the paint are out between rows v1116 and v1476; in their place the bank's island and grass top,
  a barrier at the top of the bank, the east walk raised with the northbound road (up to 5.55 m) and new paint on the
  forks and the two one-way roads. Faces per object and the checks are in `STEP-DESIGN.md`, "Step 3 done". No lamp or
  sign stood on the old median. **120 median bushes (TreeFX, `data/scatter_positions.json`) still stand on rows
  v1114-1478, 30 of them on what is now the fork's pavement**: the data step has to drop them and plant the bank.

## Known defect of the current build: every median shows asphalt between its curbs (measured 2026-11-23)

Found while reading the prep for round 2. It is in the build already (0.20.2, 0.20.3; 0.20.4 does not change it) and is
not something round 2 introduces.

- **What.** No Lake Murray median has a grass top in the game. Between an island's two curb strips the visible surface
  is the road's own asphalt; the bushes stand on it.
- **Why.** The median tool (`tools/author_median_blend.py`) joins each island's grass top into `TERRAIN`, 0.185 m over
  the slab the island stands on. The prep Lake Murray runs (engine-july `scripts/ac/build_kn5_loop.py`,
  `_conform_and_reseat`, "pin + feather") sets every ground vertex that has pavement straight above or below it to the
  deck less 0.02 m. The whole island stands on pavement, so its whole top goes 0.02 m under the road. The tool's own
  header says so for the street-only span ("the prep pins it under the road"); it holds for every island.
- **Measured** on the 0.20.3 rehearsal's own output, read-only: `D:/k10-scratch/rehearse_0099_1/data/track.obj` (the
  street layout's kn5 set as one OBJ), with `source/college_r2/median_tops_check.py` ->
  `source/college_r2/median_tops_0_20_3.json`. At the centre and the two quarter points of every island row at least
  1.2 m wide: the highest 1GRASS surface against the highest 1ROAD surface straight above or below.
  **14 islands, 7,464 m; 2,486 rows sampled; 2,486 with the grass 0.02 m under the road; 0 with grass over it.** (18
  more rows are nose tapers under 1.2 m wide and were not sampled.)

| Line | Rows | Stations (m) | Length (m) | Width (m) | Rows sampled | Grass under the road | Grass over it |
|---|---|---|---|---|---|---|---|
| mainline, College Avenue | v846-1073 | 2526-3210 | 684 | 3.4-7.0 | 228 | 228 | 0 |
| mainline, College Avenue | v1096-1487 | 3281-4455 | 1174 | 4.39-7.0 | 392 | 392 | 0 |
| mainline, Navajo Road | v1540-1739 | 4610-5208 | 598 | 2.66-6.92 | 200 | 200 | 0 |
| mainline, Navajo Road | v2183-2297 | 6543-6885 | 342 | 1.5-5.93 | 115 | 115 | 0 |
| del_cerro_blvd | v5-215 | 15-648 | 632 | 3.72-5.35 | 211 | 211 | 0 |
| del_cerro_blvd | v240-308 | 721-924 | 203 | 3.81-5.02 | 69 | 69 | 0 |
| del_cerro_blvd | v320-473 | 958-1419 | 461 | 4.7-6.0 | 154 | 154 | 0 |
| north_J1_waring | v8-315 | 22-931 | 910 | 1.5-5.99 | 308 | 308 | 0 |
| north_princess_view | v129-173 | 387-519 | 132 | 1.0-5.7 | 43 | 43 | 0 |
| north_princess_view | v200-228 | 600-685 | 84 | 1.77-5.36 | 29 | 29 | 0 |
| north_mission_gorge | v8-48 | 24-145 | 120 | 0.62-1.61 | 25 | 25 | 0 |
| north_mission_gorge | v54-57 | 163-172 | 9 | 1.71-1.76 | 4 | 4 | 0 |
| north_mission_gorge | v63-741 | 190-2222 | 2032 | 1.5-7.98 | 679 | 679 | 0 |
| north_J5_jackson_north | v621-649 | 1857-1939 | 82 | 1.43-6.1 | 29 | 29 | 0 |
- **Round 2 and College.** The split replaces College's island between rows v1116 and v1476 by a bank that has no slab
  under it; its top is released ground, which the prep pins only under pavement, so it stays grass (checked on the
  scratch scene's prep run, below). The two College islands that stay (to v1116; v1476-1487) and every other median
  are NOT touched in this round. Whether the rest joins round 2 or goes after is the Mac's call.

## Round 2, stage B steps 4a to 4c (the PC, 2026-11-23): the prep run on the scratch scene; the ground; the plants

Numbers, the six prep runs and what each one showed are in `source/college_r2/STEP-DESIGN.md`, "Step 4a to 4c done".

- **The prep Lake Murray runs is engine-july's** (`ENG`, a copy of `D:/k10-scratch/eng_repro`), not airoso's
  `scripts/ac/build_kn5_loop.py`; my first notes on it were read off the wrong file and are corrected there. It pins
  ground under pavement at the ground's own vertices, leaves released ground (`data/ground_release.json`) as the
  scene has it, and cuts long ground edges before it pins.
- **On the scratch scene the split comes out of the prep clean** (run 6): no ground within 5 mm of either road's
  surface or the forks' at 5,218 samples; the bank's grass top exactly as authored at 1,335 samples, so **College's
  bank is grass, not asphalt**; behind the raised east walk the ground stands 0.02 m under the road's edge on all 170
  rows sampled and the walk's lip is under it on every one.
- That took fixes in the scripts, each from a measured fault: rows planar across; the east ground as a strip of its
  own; the old ground under the split cut to 1.5 m edges and pushed under the lower inner edge inside the bank;
  vertices told apart by a tag on the mesh, not by a Python reference (step 3's "no other vertex moved" check could
  not fail before; it now compares 83,646 vertices).
- **The median plants** on rows v1114-1478: 120 spots; 53 dropped (all bare on the lidar: 44 on the forks' pavement, 7
  on the southbound pavement, 2 beside a new island nose); 67 kept (38 with a lidar height, 29 bare), their feet put
  on the bank's top. Kevin's 33 tall plants ("Keep all 33 at their lidar heights"): 14 are on these rows, all 14 on
  the bank, none on pavement. Nothing new is planted: the lidar's plant tops are on the G10. Report only so far
  (`college_plants.report.json`); written in step 4d.
- **The barrier at the top of the bank cannot be told from the PC's data** (aerial 0.6 m a pixel, bare-ground lidar).
  It stays `[invented]` until the G10's lidar returns are read along the northbound road's inner edge.

## Round 2, stage B steps 4d and 4e (the PC, 2026-11-23): the rail out, the bank planted from the lidar, the author phase green on scratch

Scratch workshop only; nothing built into the chain, nothing installed. `source/college_r2/STEP-DESIGN.md`,
"Step 4d and 4e done", has the tables.

- **No rail on the bank.** The G10 read the 2024 lidar along both inner edges, rows v1176-1440
  (`college_bank_rail.g10.json`): northbound 0 rail-like bins of 53, 0.43 returns a metre in the 0.5-1.2 m band (a
  W-beam gives about 45 a bin); southbound, the control, 0 of 53. Step 3's invented beam and posts are gone. One
  object is not identified: about 0.65 m tall, 0.6 to 1.0 m behind the northbound edge at v1186-1195. Nothing is
  built there.
- **The bank is planted from measured tops** (`college_bank_tops.g10.json`, 465 tops): 396 planted where they stand at
  their own height and crown (263 trees, 133 shrubs); 42 are kept median spots (21 tops on 13 of Kevin's 14 tall
  plants, 21 on 12 of the other 22 measured spots); 25 are not on the bank's grass top as built and are listed, not
  moved (9 northbound pavement, 6 southbound, 10 curb ring); 2 are not plants; 0 duplicate a tree the planner
  already places (it places none on the bank). Spot 191 (v1250, one of the 14) has no top within 2 m: the nearest
  is 3.25 m off; it stays.
- **Shrub or tree at 4.0 m, `[invented]`**: the lm-shrub tool's own fallback. The 2024 lidar shows no shrub/tree
  valley at Lake Murray: `lm_shrub.summary.json` (md5 5d9e08b708e591e1b67c7ffe7fbbae41, 2026-11-16; tops npz md5
  e722d5daa98c540f05ded2f854a1ca92) has `shrub_tree_split_m.antimode_natural` null. Species cannot be read off
  lidar: shrubs take the median's bush mix, trees Lake Murray's `trees` mix.
- **The exclusion list is 82 median spots**, declared, no measured file rewritten: 53 on pavement, the 28 bare spots
  on the bank, and one measured spot (208, v1410, 7.0 m) that stands on the curb ring 0.13 m from the southbound
  edge; `tools/verify_race.py` G refused it (trunk 0.03 m into the race curb strip) and its own measured top is
  planted in its place.
- **Engine changes, each opt-in and tested:** `tools/make_treefx.py` `scenery.treefx.lidar_plants` (a declared list
  of measured plants; the split is the config's, no default); `scripts/geometry/race_lap.mainline_approach` with
  `tools/place_signs.py` and `tools/verify_signs.py` (a layout on a lap that walks the mainline through a
  per-layout corner gets its plate there: the Speedway on the College lap keeps M3 and M4, the north lap still gets
  neither).
- **Step 4e:** on the scratch workshop the College step and the chain's author phase all pass: `lamp_heads`,
  `walk_grade`, `race_bands` (planned no-route PASS for all four race layouts), `race_planned_gate`,
  `layout_dummies`, `race_author`, `signs` (29 posts, 4 layout plates, verify PASS), `race_verify` (OK on the
  mainline and both laps). The prep, the export and the gates after them are the rehearsal's.

## The medians fixed on scratch, and College wired into the chain (the PC, 2026-11-23; version 0.20.5, not built)

- **College is in the chain.** `tools/ship_track.sh` `author_college_split`, first in Lake Murray's author phase,
  opt-in `route.college_split`: the data step held to the committed split, then the three scene steps. Airoso's own
  config and road data carry the split. On a workshop seeded the way the chain seeds one from main 04e0a9b4 (the
  0.20.4 blend) every author step passes, and a second run of the College commands leaves the blend and the data
  byte for byte the same. `source/college_r2/STEP-DESIGN.md`, "Wired into the chain".
- **The medians: releasing the ground cannot work.** The prep pins every 1GRASS vertex that has pavement above or
  below it, released or not, and its anti-poke pass clamps the rest. The prep of record is not changed.
- **The fix (the Mac's option (a)).** `tools/author_median_tops_blend.py`, author step `median_tops`, opt-in
  `route.median_tops`: each island's grass top leaves TERRAIN for its own object, `1LAWN_median`, which the prep does
  not take as ground. The name is the surface and the material in AC; `lawn_as_grass` writes the LAWN key with
  GRASS's own values, so the grip is grass. TreeFX seats the median plants on it.
- **Measured through the build's own prep on scratch:** one island first (Navajo v1540-1739: 200 of 200 rows
  grass), then all 14: **2,123 of 2,123 island rows read grass** (0.20.3: 0 of 2,486). The top stands 0.141 to 0.228 m over the road after the prep on all 4,282 of its vertices (median 0.185), the same as before it: the prep does not move it, and no vertex is without road under it.
- **Mission Gorge v54-57 is not an island (corrected the same day).** First reported as "one island, 4 rows, still
  asphalt". The median tool builds an island only from a run of 6 rows or more, so it built nothing there: no curb
  ring, only the two yellow lines. Nothing is authored; a raised island there (the plan's MD12, 12.5 m) would be new
  geometry, owed if wanted. The measure and the step's report now count a run under 6 rows apart.
- **Mission Gorge's raised median is declared terracotta in the plan.** The median tool authors every island's top
  as grass and the pipeline has no terracotta surface, so its 2.15 km now read grass where 0.20.4 showed asphalt.
  Not decided here.
- **Checks.** No check refuses grass over pavement for this object. `verify_kn5` check 6 and `audit_mesh` B read
  1GRASS only and do not judge the top; `verify_kn5` face-up and `drive_test`'s soft-top-in-lane do
  (`fleet/GATES-CHANGELOG.md`, 2026-11-23). The full chain's gates have not run on it: that is the rehearsal.

## 0.20.5's first rehearsal red at kn5_ground_check; the split's ground fixed on scratch (the PC, 2026-11-23; not built)

- **The rehearsal** (b844ad07, `D:/k10-scratch/rehearse_0205`): every gate green but `kn5_ground_check`, on all five
  layouts: "terrain has 202 double-sheet cells" (0.20.4: 0), and "deck-vs-mountain max +5.181" (0.20.4: +0.255,
  reported only). Not installed; nothing forced.
- **Cause, mine.** The strip of ground the College step adds east of the northbound road (the east shelf) ran every
  row on to 19.5 m, at the lower of the falling fill and 0.30 m under the old ground: under the cut it lay up to
  19.4 m down inside the hill, a second sheet of ground. The notes said "0.3 m under it"; the code did not do that.
  The 5.18 m was old ground left at the old slab's height just outside the raised road's edges, under the walk, the
  curb and the bank's top: hidden walls, read by the check at the road's own edge vertices.
- **Why it reached a rehearsal.** My scratch pass ran the prep and the medians' measure, never `kn5_ground_check`.
- **The fix** (`source/college_r2/college_ground_blend.py`, `college_shelf.py`; no gate, threshold or prep changed):
  the shelf ends where it goes under the old ground; old ground wholly under the bank's top or the open shelf is
  taken out of TERRAIN (32,342 faces); what is left at a seam sits just under the surface over it; the ground
  under the split's own roads is set where the prep will pin it; the step refuses to save a scene in which a 2 m
  cell near the split holds ground heights more than 12 m apart that it did not before (the gate's lens and number).
- **Measured on scratch through the chain's own commands** (author phase, prep and its sub-steps, split, road
  export, `kn5_ground_check`; then street and race_cw `drive_test`, `audit_mesh`, `no_route`): double-sheet cells
  **0** (202); deck-vs-mountain max +0.313 (+5.181; 0.20.4 +0.255); street `drive_test` PASS: 10 drops, 44 far ledges, severe 0;
  street audit CLEAN; race_cw `drive_test` PASS: severe 7, 0 drops, 142 far ledges; race_cw audit CLEAN; `no_route` PASS: leak 0, reached 138.2 k m2.
  `source/college_r2/STEP-DESIGN.md`, "0.20.5's first rehearsal", has the table and what is left.
- **Kept**: `source/college_r2/scratch/` (the scratch run and `ground_look.py`, which lists the places behind the
  check's numbers). Every College change goes through that run before it is pushed (the Mac, 2026-11-23).


## 0.20.5 rehearsal 2 green and the install, no force (the PC, 2026-11-23)

- **Rehearsal 2** (c6352faf, empty workshop `D:/k10-scratch/rehearse_0205b`, ENG a fresh copy of eng_repro, `--no-install
  --skip-blend`, 08:50-09:27): SHIP OK, every gate exit 0. `kn5_ground_check` on all five layouts: double-sheet cells **0**
  (rehearsal 1: 202), deck-vs-mountain max **+0.313** (+5.181), the north junction 0.20.4 has too. Street `drive_test`
  off-road drops 10 (rehearsal 1: 11). The line gates pass both ways; drive_test's own lap rule reads its excursions as
  before (fwd 17, rev 21: reported, as on 0.20.4).
- **Against rehearsal 1** (b844ad07): the gate rows differ only in the College ground's numbers and what the ground carries.
  The race, closure and street kn5 are EQUIVALENT (tangents only); the 20 AI files are identical. In the main kn5 the
  terrain tiles, rock and a few seated things moved: buildings re-seated by 6 mm at most, 6 sidewalk lip vertices by
  3.6 cm at most; `1LAWN_median` holds the same points in another order.
- **The install** (09:30-10:08, the chain's own empty workshop `D:/k10-scratch/lm_line`; 0.20.4's moved to
  `D:/k10-scratch/lm_line.0.20.4`, kept): SHIP OK, all five layouts 0.20.5 as `san_diego_lake_murray_v4`, 0.20.4 parked in
  `D:/k10-track-archive/2026-11-23_100800/`. = rehearsal 2: 1,135/1,135 gate rows (the workshop's name aside); every kn5
  equivalent but the main one, whose `1LAWN_median` and `ROOFTOP_SHINGLE_0` hold the same points in another order
  (ROOFTOP_SHINGLE_0 27,729 -> 27,728 vertices by the exporter's merge, as between the two rehearsals); AI identical. The
  14 kn5 in AC are byte-identical to the build; the trees came along (14 .bin, the same list as 0.20.4).
- **Menu pictures.** The install brought the track outline as its picture (the branch's `source/ui` holds none of 0.20.4's):
  0.20.4's five pictures are put back in AC as a stopgap (the outlines kept in
  `D:/k10-track-archive/2026-11-23_101500_lm0205_pictures_stopgap`, PREVIEWS.tsv there). 0.20.5's are drawn in a later PC slot.
- **The blend.** The install synced back `loop.blend` at 204,545,652 B, sha256 bc7f772e... (0.20.4's pinned 495a2198...,
  `tests/tools/test_lake_murray_0099.py`); committed as the sync-back, as 0.20.4's was. The next empty workshop seeds it.
- Records on `claude/lm-0205-install-20261123` (sync-back 3a789d9c, main fcef3efe merged d60d786b); nothing pushed onto
  `claude/lm-finish-r2-20261122`. Kevin's standing word on the PC: "Yes and I always want newer builds".

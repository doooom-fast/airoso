---
id: 0055
title: "One of the lanes swerves into where the other lane should be ... we should just cut into the hillside the way California does" — College Avenue's split section; the Speedways keep their chicane
status: in-progress — diagnosed, fixed and rehearsed 2026-10-14 (round 2, after the truth + gates lenses refuted round 1; full scratch chain), not installed; Kevin's seat closes it
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
fan (0057's raised deck, outermost fixed paths). **Street gated excursions 100 vs 98** stay one higher: −4 here
(v1302 / v1352), sampling ±1-4 elsewhere (v0.18.0's own mesh on these stations reads 102), +2 at v3806 where the mesh is
unchanged but drive_test's flare exemption follows the lap's median width, which this run's one divided College run
raised 17.00 → 17.64 m (GATES-CHANGELOG v0.18.1). Stills: D:/k10-scratch/v0181/stills/freeroam_college_nb_*.png, D:/k10-scratch/v0181/stills/speedway_chicane/,
D:/k10-scratch/v0181/stills/speedway_reverse_chicane/.

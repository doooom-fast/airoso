# Milford Road Course: route notes (2026-10-28)

Kevin, 2026-10-28: "Build Milford first" (the first build in `DOSSIER.md` Part C, approved).

## Where it is

The road course is in the **south-east corner of the Milford Proving Ground**, between the main
engineering campus (west) and Hickory Ridge Rd (east). Centroid 42.57002, -83.66360. This is the
Oakland County side of the county line, so one lidar project covers it.

## Why this is the MRC (dossier §10 checks)

| Check | Dossier says | Measured on the trace | Verdict |
|---|---|---|---|
| Relief, 3DEP 1 m along the line | 41 ± 2 m (SAE 2005) | **39.7 m** (316.1 to 355.8 m) | pass |
| Length | 4.55 to 4.85 km (GM "2.9 mi") | **4.07 km** | **fails, -13 %** |
| Corners | 17 (GM) / 18 (forum) / 20 (SAE) | 15 bends of 20° or more with radius under 150 m; the count depends on the threshold | not a test |
| A paved road course with kerbs and run-off | — | the only one at MPG; every other `highway=raceway` there is a test road, the Circle Track or Black Lake | pass |
| OSM | — | `highway=raceway`, `oneway=yes`, `access=private`: ways 72577419, 72577413, 1030539760, 72577375, 72577386, 72577423, 1030539761, 72577404 | topology agrees |

**CORRECTED 2026-10-31 (`trace/unsquash_frame.py`, ledger 0061): the export had square-degree pixels and the trace was squashed north-south by 0.737; unsquashed, the lap is 4.90 km (+5 % on GM's figure) and OSM's outline was right all along. The paragraph below is what the squashed frame looked like.** The length gap is not explained. In the 2022 photo, every clockwise lap you can drive comes out
between 4.0 and 4.4 km:

- the full lap: 4.07 km
- through the SE back section instead of the east side and bottom: about 4.0 km
- back section upper, then the cross-connector, then the east side: about 4.4 km

The 2016–18 lidar relief image shows no old road bed beyond today's pavement. So "2.9 mi" is either
a different configuration or a rounded figure. OSM's own sum gets to about 4.7 km only because its
outer loop is drawn about 190 m too far south. **The trace is what exists. The dossier's figure
is not used** (§11: the trace sets the layout, not the file).

## OSM is wrong here (L1)

Way 72577419, the outer loop, was traced off Yahoo imagery and runs through the houses south of the
course. Its 2,986 m and 39.5 m relief are not the course's. The infield way 72577413 roughly fits.
OSM is used only for the topology and the one-way direction.

## The lap (clockwise; direction from the OSM oneway tags, unverified against video)

From the S/F on the west front straight (16 m wide), northbound:

1. NW corner (right), onto the wide apron
2. right-hand hairpin dropping south
3. esses south
4. U-turn
5. back north
6. east along the top of the infield into the **serpentine** round the central wood, including its
   tight south-east hairpin
7. out onto the top straight, eastbound
8. long NE corner
9. the east side, south, under the tree line: the fastest stretch, about 316 m, the lowest point
   of the lap
10. the sweeping bottom, westbound, climbing
11. the SW corner, back onto the straight at 356 m, the highest point

Widths:

- median 11 m
- front straight 16 m
- infield 9–12 m

## The hill

The lap is steeper than the engine's defaults allow. Once despiked, the 3DEP profile climbs
**26.6 % over 21 m** at s ≈ 3,650 (SW corner, the climb from the bottom sweeper to the front
straight), about 13 % at s ≈ 3,450 and about 10 % in the esses.

Lidar cross-sections show the road cut into a hillside there:

- ground 2–3 m lower 20 m to the left, 1–2 m higher 20 m to the right
- both edges climb with the line

It is real terrain, not a trace error. The engine's 9 % default grade cap put the deck up to
5.96 m under the ground, and drive_test failed on it. `road_profile.max_grade_pct` is 32 so the cap
never binds (L3).

A 2 m dip at s ≈ 3,605 is where the yellow-lined service road passes under the course. Bare earth
deletes the deck, and the 33 m despike removes the dip. **First question for the drive:** is that
climb drivable at speed, or is the lidar showing earthworks newer than the pavement?

## Unused pavement, for later layouts over the same kn5 (L8)

- The inner hairpin short-cut in the esses (OSM 1030539760).
- The top-straight bypass between the apron and the serpentine exit.
- The SE back section (OSM 72577375 + 72577386 + 72577404), the cross-connector (72577423) and
  the hook (1030539761).
- Dark service roads with yellow centre lines (SW loop, lot access): not course.

## Engine draft status (2026-10-28)

What each change did to drive_test on the built mesh. The runs used `scripts/build.sh`'s stage
commands one by one, because `build.sh` itself stops at its PoT pre-flight on two Lake Murray
sign-tool chevrons this track never binds.

**The constructed corridor passes drive_test and audit_mesh.** It needed `natural_ground` removed and
the engine's constructed shoulder branch restored (`build_mesh.py`: the 6f1c734 port had orphaned
it):

| Constructed corridor (now) | Value |
|---|---|
| Ground on top | **0** |
| Severe steps | 7 (1.7/km, limit 12) |
| Bumps/km | 17.2 (limit 75) |
| Drops >20 cm, gated | **1** (limit 4) |
| Road vs lidar p95 / max | 0.20 / 1.61 m |
| audit_mesh | CLEAN |

96 measured-guard stone lips stand at in-band drops. On a proving ground they should read as W-beam
guardrail, which is a look item.

Earlier builds, natural ground:

| Build | Ground on top | Severe steps | Bumps/km | Drops >20 cm (limit 4) | Road vs lidar p95 / max |
|---|---|---|---|---|---|
| 2.0 m cells, 9 % grade cap | 28 | 0 | 9.1 | 20 | 3.35 / 8.55 m |
| 1.25 m cells (L3b), 9 % cap | 14 | 0 | 9.1 | 28 | 3.35 / 8.55 m |
| **1.25 m cells, cap 32 % (real hill)** | **14** | 7 | 17.2 | 31 | **0.20 / 1.61 m** |
| + measured crossfall (reverted) | 53 | 17 | 89.7 | 52 | 0.20 / 1.61 m |

Crossfall is still off (no `data/crossfall.json`).

What natural ground left, now closed by the constructed corridor:

- **Grass on top (14).**
  - At s 786, 995, 2168 and 2372 it is the L3b edge class: grass pinned about 2 cm under the deck
    bridges 1–3 cm through it at the very lip.
  - **s 622 (esses) is real.** Grass tops the edge by up to 16 cm where the road is banked about 4 %
    and the deck is flat.
- **Off-road drops (31).** Worst are 49 cm at s 3,451 (8 m left), 39 cm at s 752 (12.5 m right) and
  29 cm at s 452. These are the hillside: the road is cut into the slope and the far side falls
  away. The engine's guard-wall construction (#17) is pending. `GATE_EXCURSIONS_ADVISORY=1` exists
  for test builds only.
- **Banking.** The lap is really banked: 1 m lidar sections read 4–8 % through the esses, the U-turn
  and the s 995 right. Done properly that is authoring (an `AUTH_` cross-section from lidar, V3 /
  REALISM §4), not the measured-crossfall flag.

## Open

- **Direction:** confirm clockwise from an onboard lap (dossier A2.3, the Autoweek Stingray lap).
- **The "Carousel":** no bowl is obvious in the photo. Candidates are the serpentine's SE hairpin
  and the esses U-turn. Take lidar cross-sections before authoring any bank (L10).
- **Pit lane / paddock:** a narrow paved strip runs beside the front straight on its east side, and
  a dark paved lot sits west of it. Neither is modelled yet.

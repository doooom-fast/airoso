# Location dossier addendum: Lake Murray west and the I-8 corridor (san-diego-lake-murray, ledger 0054 Phases 3 and 4)

> This addendum covers only the roads of Kevin's Phases 3 and 4. The loop's facts stand as built in v0.18.0, and Phase 1's are in [`DOSSIER-EXPANSION-NORTH.md`](DOSSIER-EXPANSION-NORTH.md).
> - **Sources:**
>   - OSM osm_base 2026-10-14T10:13:39Z (the Phase 1 worktree's `osm.expansion.json`, box S 32.755 / W −117.115 / N 32.850 / E −116.985, through the 7-day guard, TLS verified), plus one guarded fetch for waterways, rail, barriers and ramp meters (overpass-api.de, osm_base 2026-10-14T15:08Z);
>   - USGS 3DEP 1 m;
>   - NAIP 2022-04-25 at 0.6 m (quarter-quad m_3211716_sw_11_060_20220425), the only NAIP year the USGS service serves here.
> - The research files are in the session scratchpad `p34/{routes3,routes4,terrain,aerial,pipeline,revise}/`. Step 0 of each plan copies what its build needs into the workshop, with this provenance.
> - **Stations:**
>   - Phase 3: metres from the junction node at the start of each leg, in clockwise order J2 → J6 → J7 → J3.
>   - Waring south: metres from J6. The aerial's Waring stations run from J2, so subtract ~671 m.
>   - I-8: longitude; where needed, metres along the OSM carriageway chain (EB from −117.1146, WB from −117.0487), or aerial stations along the westbound line from −117.1118.
> - **Names** (chosen not to collide with Phase 1's W1/W5 welds and S1–S6 stubs):
>   - Road segments: P3-WAR, P3-ZION, P3-MG (Phase 3); P4-WAR, P4-MG, P4-I8 (Phase 4).
>   - J6 is Waring/Zion and J7 is Zion/Mission Gorge.
>   - X8 is the Fairmount Ave / Mission Gorge Rd interchange (exit 8), X9 Waring Rd (exit 9), X10 College Ave (exit 10).
>   - END-W and END-E are the ends of the drivable freeway.
> - Plans: [`EXPANSION-PHASE3-PLAN.md`](EXPANSION-PHASE3-PLAN.md) and [`EXPANSION-PHASE4-PLAN.md`](EXPANSION-PHASE4-PLAN.md).

## 1. Identity and intent

- **Kind:** `street_port`, the same kind as the loop. Phase 4 adds the project's first drivable freeway, but the kind stays: real public roads as they exist.
- **Why:** Kevin's father's neighbourhood grows west and south: Allied Gardens and Grantville, down to the river valley and the freeway everyone here used. The drive we are after:
  - **Phase 3:** Waring's planted boulevard, the plunge down Zion through a neighbourhood of houses and schools, and the fast six-lane run back up Mission Gorge along the river.
  - **Phase 4:** down Waring's canyon to I-8, then the freeway itself: a split-level hill where one direction rides 18 m above the other, off at College one way and at Mission Gorge the other.
- **Kevin's words:**
  - Phase 3: *"waring to Zion, Zion to mission gorge"*. That is Waring J2 → J6, Zion J6 → J7, and Mission Gorge J7 → J3 to join the loop up. Princess View stays.
  - Phase 4: *"waring to 8, and we'll start working on freeway ramps. 8 will then go to college one way and mission gorge the other"*. That is Waring J6 → X9, the ramps at X8, X9 and X10, I-8 eastbound to exit 10 and westbound to exit 8. Mission Gorge Rd J7 → X8 links it (Phase 4 plan, D2).
- **Layouts:** one model for all of them (L8).
  - Lake Murray Free Roam is the whole network.
  - The Lake Murray Speedways keep their laps.
  - The Mission Gorge Speedway (Phase 2) seals the new arms at J2 and J3.

## 2a. Route geometry: Phase 3 (the western loop)

| Seg | Road (OSM) | Length cw / acw | Lanes / width (eye, NAIP 2022, ±1–1.5 m) | Notes |
|---|---|---|---|---|
| P3-WAR | **Waring Rd**, J2 → J6. cw (SW-bound) ways 436411990, 436411984, 436411982, 436411988, nodes 1713352279 → 49397489; acw (NE-bound) 436411980, 436411989, 436411987, 436411992, nodes 49333076 → 49333080 | 669.8 / 668.9 m | 2+2 plus bike lanes, 3 at the Greenbrier and Zion pockets. **28.0 / 29.5 / 29.7 / 22.0 m** at s 150 / 300 / 450 / 600 | **Divided:** OSM carriageway lines 8.8–10.1 m apart; **raised planted median 2.5–5.5 m with trees**. 35 mph (40 mph tagged on 32 m of the Greenbrier pocket). Signals at J2, Greenbrier Ave (s 333–352, yellow school ladder) and J6 (s 653–670). Sidewalks both sides. Arrives at J2 at ~239° and leaves SW at ~224°. **Phase 1's S2 arm is declared 23.0 m wide**, so the piece widens from 23 to 28 m inside itself |
| P3-ZION | **Zion Ave**, J6 → J7: 19 ways, 1220464886 … 641705013, nodes 49397489 → 49317051; acw 49317049 → 49333076 via the median crossovers 641705017 / 641705003 | 1,567.3 / 1,594.4 m | 2 lanes, undivided. **11.2–15.1 m** (12.0, 12.0, 13.5, 11.5, 12.0, 13.0, 11.5, 11.2, 15.1, 14.8 m every 150 m) | Double yellow. Centre turn lanes at s 0–104, 211–279, 934–983, 1204–1258 and 1450–1567; a painted two-way left-turn lane ~3.5 m at s ~900–1050. 30 mph; no bike lanes. Signals at J6 (s 13), 51st St (s 242, school crosswalk), Crawford St (s 1221–1242) and J7 (s 1556). Uncontrolled crossing at s 1317. Straight E–W at ~32.7928 N. The last ~300 m is Grantville commercial at ~15 m. It continues west past J7 toward Friars Rd |
| P3-MG | **Mission Gorge Rd**, J7 → J3. cw (NE-bound) 20 ways 436411957 … 436424129, nodes 49317051 → 1484501766; acw (SW-bound) 12 ways 436424134 … 436428811, nodes 1484501883 → 49317049 | 2,364.8 / 2,389.7 m | 3+3, 4–5 at the pockets, bike lane on the right almost everywhere. **26.3–33.7 m** (32.1, 31.0, 27.5, 26.3, 27.3, 30.5, 27.0, 29.0, 31.3, 27.5, 32.7, 30.1, 31.9, 33.5, 33.7 m every 150 m) | **Divided:** carriageway lines 12.7–18.1 m apart; **terracotta raised median**, mostly 3–5 m, planted, with 1.5 m strips at s ~900–1350. 45 mph J7 → Old Cliffs (s 929), then 55 mph. Signals at J7, Greenbrier Ave / shopping-centre entrance (s 590), Old Cliffs Rd (s 929) and J3 (s 2347). **5 median openings**: s 590 ×2, 1134, 1277, 1736. **Phase 1's S3 arm is declared 28.0 m wide** against 33.5–33.7 m read just before J3: a width transition inside the piece |
| P1-PV | Princess View (Phase 1) closes the loop: cw southbound J3 → J2 | 1,106.2 / 1,134.9 m | see the north dossier | — |

- **Totals:**
  - new Phase 3 road: **4,601.9 m cw / 4,653.0 m acw**;
  - the western loop: 5,708.1 / 5,787.9 m;
  - the outer north loop (skipping Princess View): 12,233.2 m;
  - a grand loop (the loop with Navajo's 2,413.1 m swapped for the outer route): 20,941.8 m.
- **Bridges, rail, rivers:** none on Phase 3. I-8 is ~1.1 km south.
- **Junctions** (3DEP at the node):

  | | Nodes (both carriageways) | Height | Shape | Turn cw | Arms closed in Phase 3 |
  |---|---|---|---|---|---|
  | J2 Waring / Princess View / Mound | 1713352279, 49333080 | 103.9 m | four-way, Phase 1's pad (not built yet) | PV S → Waring SW +84° | Mound Ave (S1) stays; **S2 (Waring SW) becomes road** |
  | J6 Waring / Zion | 49397489, 49333076 | 99.7 m | four-way signal, yellow school ladders on every leg | Waring SW → Zion W +60° | Waring S (divided; Phase 4), Zion E (residential, 25 mph, way 1430783899), the Zion EB → Waring SB free-right slip (secondary_link 1214006895, stop-controlled, Zion s 62) |
  | J7 Zion / Mission Gorge | 49317051, 49317049 | 33.8 m | signal; Grantville | Zion → MG NE +103° | MG S (5 lanes in; Phase 4), Zion W (tertiary to Riverdale St, ~200 m) |
  | J3 Princess View / Mission Gorge | 1484501766, 1484501883 | 33.4 m | Phase 1's pad (not built yet); MG straight through (65° in, 66° out) | MG → PV S +106° | the quarry drive (S4) stays; **S3 (MG W) becomes road** |

  - Anticlockwise, the mirror-image left turns run −75° to −107°.
  - **Curb-return radii at J6 and J7: unknown.** Phase 3's Step 1 measures them on NAIP.
- **Side mouths, all closed by Phase 5 stubs** (`routes3/mouths3.json`; the J6 slip is counted once, as a junction arm):

  | Road | Public side streets (station) | Mapped service mouths | Median openings |
  |---|---|---|---|
  | Waring | Greenbrier Ave NW and SE (s ~340, signal) | — | — |
  | Zion | Glenroy N 104 / S 161; 51st N/S 242; Winona N 521; Estrella N/S 679; Clara Lee N/S 776; Delbarton N/S 863; Cartwright N/S 959; Seaman N/S 1051; Burgundy N/S 1143; Crawford N/S 1232; Bus Access Rd S 1301; Archwood N 1308; unnamed S 1434 | 12 (1 private) | — |
  | Mission Gorge | Allied Rd SE 500; Greenbrier Ave SE 590; Old Cliffs Rd SE and W 929; Katelyn Ct SE 1736; Goen Pl SE 2024 | 33 (3 private; including a 1.75 km service road at s 1277) | 5 |

  Totals: **30 public side streets (2 + 22 + 6) plus 5 junction arms = 35 barrier stubs**; 45 mapped service mouths; 5 median openings. Residential driveways on Zion and Grantville's commercial driveways are mostly unmapped. **Unknown; NAIP count, then Street View.**

## 2b. Route geometry: Phase 4 (Waring to I-8, the interchanges, I-8)

| Seg | Road | Length | Lanes / width | Notes |
|---|---|---|---|---|
| P4-WAR | **Waring Rd**, J6 → X9 | 1,585 m SB / 1,580 m NB | Divided to ~32.7816, 2+2, widening to 3 at intersections; then a 3-lane two-way road (2 SB, 1 NB) over the WB bridge. **22–24 m** with short raised islands to Orcutt (23.8 / 24.2 / 21.5 / 23.7 m at s ~80 / 230 / 380 / 530); **canyon 18.8–24.0 m** with a 0.6–1.4 m raised concrete median; overcrossing deck ~17.5 m out to out | 35 / 40 / 45 mph. Signals at J6 (s 0), Orcutt Ave (s ≈ 294), Adobe Falls Rd (s ≈ 1074, 32.7845), the WB ramps (s ≈ 1315) and the south end (s ≈ 1588, the T with the EB ramps). **Passes UNDER the Alvarado Canyon Rd flyover** (~32.7817), **crosses OVER I-8 WB** (ways 27056754 + 436607389, 33 + 18 m) and **passes UNDER I-8 EB** (way 27056788, 41–44 m). Del Cerro Tennis Club at s ~980 |
| P4-MG | **Mission Gorge Rd → Fairmount Ave**, J7 → X8 | ~1.5 km to Fairmount (aerial 1,473 m); ~1.8 km to the X8 south ramp ends | Three parts. **(1) J7 to ~32.7906 (~300 m): divided one-way pairs** (436428813 / 622962331 / 436428671 / 436428673 / 226939096–7 / 436428669), 3–5 lanes each way, 45–50 mph. **(2) ~32.7906 to ~32.782: undivided**, 4–5 lanes, **19.7–24.4 m**, a two-way left-turn lane then double yellow, 35 mph. **(3) ~32.782 south: divided pairs again**, under I-8, becoming Fairmount Ave (trunk, 2–4 lanes each way, 50–55 mph) | **Friars Road** (primary, 3+3, one-way pair 436428664 / 622962332, plus primary_links 159483493 / 159783714 / 159783716) meets it ~150 m south of J7 at a signal cluster (nodes 11309269635, 11309269589, 2356790505, 11309269640). Then side streets: Orcutt Ave (32.7909), Rainier Ave (signal, 32.7898), Glacier Ave (32.7888), Vandever Ave (signal, 32.7877), Twain Ave (signal, 32.7850), Mission Gorge Pl (signal, 32.7832), old Fairmount Ave (tertiary, signal cluster at 32.7813), and the **Camino del Rio North / Alvarado Canyon Rd** junction (32.7802). 54 mapped service ways touch it. Grantville commercial strip. Passes **under** I-8 at −117.1014/−117.1010 |
| P4-I8 | **I-8 (Mission Valley Freeway)**, drivable EB −117.1000 → exit 10 (−117.06985), WB College on-ramps' merge (−117.07262) → exit 8 (−117.0975) | **EB 2,848 m, WB 2,357 m** (along the OSM chains), plus closure tapers and see-only continuations; the Fairmount-to-College stretch is 4,220 m EB / 4,225 m WB from −117.1045 to −117.0600 | EB lanes 4 / 6 / 5 / 6 (extra lane at exit 10) / 5. WB 6 from the Waring on-ramp to past Fairmount, 5 from Waring east, 4 after 7B. Standard section at aerial st 250, **43.4 m** edge to edge (shoulders 2.4 / 1.8 / 1.7 / 2.2, barrier 0.8, lanes 15.0 and 16.7) | 65 mph. No HOV lanes tagged. Concrete lanes, dark asphalt shoulders, asphalt dikes. **One concrete median barrier** wherever the directions are side by side; a pavement gap of ~5.4–6.8 m including both inside shoulders. **No sound walls** |

- **Separation between the two directions' centrelines:**

  | Stretch | Separation |
  |---|---|
  | West of Waring | 20–29 m |
  | The split, −117.093..−117.072 | 37–64 m |
  | East of −117.071 | 16–21 m |

  The scrub median in the split is 9 / 31 / 34 / 22 / 10 m wide at aerial st 2000 / 2500 / 2750 / 3000 / 3250.
- **The split level.** EB stands above WB by:

  | Longitude | −117.0897 | −117.0870 | −117.0843 (max 18.8 m at −117.0835) | −117.0817 | −117.0791 | −117.0764 | −117.0738 |
  |---|---|---|---|---|---|---|---|
  | EB above WB | 9.7 m | 14.9 m | 18.0 m | 16.6 m | 11.5 m | 6.8 m | 2.0 m |

  The directions rejoin near −117.071.
- **Exits and merges** (from OSM `motorway_junction` and way ends; chain metres in brackets):

  | Point | Eastbound | Westbound |
  |---|---|---|
  | 7, I-15 / CA-15 | leaves at −117.11462 | 7B leaves at −117.10405, 7A at −117.10627 |
  | EB collector (from I-15 and Camino del Rio) | its two feeders merge at −117.10663; it splits at −117.10416 into a 3-lane branch to Fairmount and a 2-lane branch rejoining I-8 at −117.10145 | — |
  | WB collector "I 8 West; I 15" (way 804836716, 3 lanes) | — | starts at −117.10346 from the Fairmount on-ramps; feeds I-15 and I-8 West only |
  | 8, Fairmount / Mission Gorge | EB on-ramps join at −117.09949 [EB 1,422 m] and −117.09766 | leaves at −117.0975 [WB 4,663 m] |
  | 9, Waring | leaves at −117.09406 [EB 1,941 m]; on-ramp joins −117.08373 [EB 2,912 m] | leaves at −117.08432 [WB 3,417 m]; on-ramp joins −117.09064 [WB 4,011 m] |
  | 10, College | leaves at −117.06985 [EB 4,221 m]; on-ramps join −117.0625 [EB 4,914 m] | leaves at −117.06157 [WB 1,263 m]; on-ramps join −117.07262 [WB 2,306 m] |
  | 11, 70th St / Lake Murray Blvd (outside the default) | leaves at −117.04835 | leaves at −117.04372 |

  **The College deck** crosses at ~−117.066 [EB 4,581 m, WB 1,686 m]: after eastbound's last exit and before westbound's first entrance, so under the default nobody drives under it.
- **Ramps in scope** (one-way; lengths along the ramp; grades from 3DEP; drivable in the default unless marked):

  | Interchange | Ramp | Length | Lanes | Notes |
  |---|---|---|---|---|
  | X8 | EB on-ramp from Fairmount | 436 m | 1 | 2 small bridges, ramp meter, joins at −117.09949 |
  | X8 | EB on-ramp from Fairmount south | 505 m | 2 | forks at −117.10011: "I 8 East" (meter, joins at −117.09766) drivable; "I 8 West" to the WB collector closed at the fork |
  | X8 | WB exit 8 to Mission Gorge Rd / Alvarado Canyon Rd | 294 / 329 m | 1 then 2 | 22 m bridge; 38 → 26 m; its short branch onto Alvarado Canyon Rd is stubbed |
  | X8 | EB collector road | ~350 m to its split plus ~300 m of branches | 3–4 | not drivable (comes only from I-15) |
  | X8 | WB on-ramps from Fairmount | — | 1–2 | not drivable (feed only the WB collector) |
  | X9 | EB exit | 567 m | 2 | — |
  | X9 | EB on-ramp | 402 m | 2 | 2 meters, 37.8 → 54.7 m (~4.2 %), joins at −117.08373 |
  | X9 | WB exit (a loop down to Waring) | 399 m | — | passes under the Alvarado Canyon Rd flyover |
  | X9 | WB on-ramp | 428 m | 1–2 | 2 meters, joins at −117.09064; passes under the flyover |
  | X10 (partial cloverleaf: loops NE and SW) | EB exits | 293 / 294 / 354 m | — | climbs 94 → 107 m (8.5 %), signalised |
  | X10 | EB on-ramps | 508 m (loop) / 683 m | — | meters, join at −117.0625; not drivable (they lead only into the closure) |
  | X10 | WB exits | 392 / 393 m | — | not drivable (they leave before westbound's start) |
  | X10 | WB on-ramps | 838 / 924 m | — | meters; 124 → 86 m, up to 9.3 % |

  Totals in the box −117.1035..−117.06:

  | Interchange | Link ways | Length |
  |---|---|---|
  | X8 | 29 | 2,730 m |
  | X9 | 9 | 1,796 m |
  | X10 | 23 | 2,972 m |

  The whole box also holds 26 motorway ways (11.5 km, 5 of them bridges, 217 m), 63 motorway_link ways (8.3 km, 4 bridges, 161 m) and 31 trunk / trunk_link ways (3.6 km).
- **What crosses I-8, and which way** (W → E):

  | Longitude | Crossing | Over or under I-8 |
  |---|---|---|
  | −117.1125..−117.1121 | the I-15 / CA-15 decks and flyovers (layer-2 links among them) | over (outside the default) |
  | −117.1014 / −117.1010 | Fairmount / Mission Gorge Rd and two ramps | under; I-8's decks above |
  | −117.0964..−117.0958 | **MTS Green Line trolley** viaduct (layers 2–3); also runs along I-8's north side from Fairmount, and south of EB from −117.096 to −117.076 | over |
  | ~−117.088 | **Waring Rd** | over WB, under EB |
  | −117.0690 | Alvarado Creek, in a culvert | under |
  | ~−117.066 | **College Ave** (twin 96 / 97 m bridges; the loop's own deck) | over |
  | −117.0544 | an unnamed stream, in a culvert (outside the default) | under |
  | −117.0460 | Lake Murray Blvd (outside the default) | over |

  The **San Diego River is not crossed.** It lies 180–200 m north of I-8 at −117.11, then turns north-east up Mission Gorge.
- **Alvarado Canyon Rd.** It starts at an all-way stop on Adobe Falls Rd (node 49105019, 32.7829, ~80 m east of Waring; Adobe Falls Rd meets Waring at the signal at 32.7845). Its **392 m curved flyover** (way 34539869, `layer=1`) sweeps south-west **over both Waring carriageways (159243459, 159243460) and two X9 WB ramps (5952893, 5952897)**, then over Alvarado Creek. It becomes the north frontage road: 2 lanes, double yellow, parking, behind one concrete barrier from westbound I-8, running west to the Mission Gorge Rd / Camino del Rio North junction (32.7802).
- **The stack order at X9 is in OSM.** The three `layer=1` structures never cross each other: each crosses a `layer=0` road. Waring 27056754 is over WB 1010908005; EB 27056788 is over Waring 436607390; the flyover is over Waring and the two WB ramps. What OSM doesn't give is the deck heights (§3).
- **Junctions and ramp ends:**
  - Waring's south end is a signalised T with the EB ramps, ~45 m south of EB.
  - The WB ramps meet Waring on the north side.
  - X8's WB exit ends on Mission Gorge Rd (one branch onto Alvarado Canyon Rd). The EB on-ramps start on Fairmount, north and south of I-8.
  - At X10, the ramp ends are on the loop's College Ave, signalised. **19 ramp ends lie within 20 m of the loop's pavement: 16 at v791–976 (s 2361–2913) and 3 at v4433–4457 (Lake Murray Blvd).**
- **Grantville trolley station:** elevated with a glass canopy at ~−117.0975. **Union Grantville** apartments were under construction there in April 2022.

## 3. Elevation and drainage

3DEP 1 m. Phase 3 grades are over 50 / 100 m and a 20 m chord; Phase 4's are over 200 m windows and a 20 m chord.

| Road | Height | Max grade | Character |
|---|---|---|---|
| Waring J2 → J6 | 103.9 → 99.7 m over a **106.6 m crest at s 400** | 3.2–3.4 % | at grade; no cut or fill over 2 m |
| Zion J6 → J7 | 99.7 → 33.8 m (**−66 m**, average −4.3 %) | **10.1 % / 50 m, 9.8 % / 100 m, 10.2 % / 20 m chord at s 570–660**; a sustained 8–10 % over s ~450–900, centred ~−117.087 | a one-sided cut, 3.7 m within 12–20 m and 9.1 m within 28–40 m (s 432–600) |
| Mission Gorge J7 → J3 | 33.8 → 33.4 m; **sag 28.7 m at s ~300–400 cw**, rise to 36.4 m (s ~672) | 4.1–4.2 % | valley floor; a one-sided cut 4.9 m, a one-sided fill 5.5 m. **The new network low** |
| Waring J6 → I-8 | 99.7 → ~37.8 m (−62 m) | 7.0–7.9 % over 200 m, s ~550–1250 (p95 8.2 % on a 20 m chord); 1–3 % elsewhere | **sidehill**: the NB side is cut up to 8.8 m within 20 m and 22 m at 28–40 m (s 504–960) |
| Mission Gorge J7 → I-8 / Fairmount | 34.3 → sag 23.2 m (s 458) → 28.3 m | 5.1 % | valley floor |
| I-8 EB | 26.8 m (−117.1045) → 39–40 m flat (−117.097..−117.090) → a steady 2.8–3.1 % climb to 103.6–108 m at College → 110.2 m (−117.0600) | ~3 % | climbs the hillside in the split |
| I-8 WB | 27 m at the west end; **39.8 m crest at −117.096**; **30.1 m sag at −117.0888** (creek level) | 5.0 % in the split | follows Alvarado Creek |
| Ramps | College WB on: 124.3 → 85.6 m over 836 m | **9.3 %** | cut 8 m then fill 9 m |
| | Waring EB off: 39.7 → 54.7 m | 7.8 % | in a **cut 9–12.6 m deep for ~250 m** |
| | College EB off 8.5 % (fill 7 m); College WB off 6.5 % (cut 7 m); Waring WB on 6.5 %; Fairmount WB off 8.6 % p95; Fairmount EB on 4.6 % | — | the Fairmount WB off's −12.9 % is one chord at its bridge end, a bare-earth artefact |

- **Clearances.** One definition throughout: **clearance = deck underside (soffit) minus the road surface beneath**, with soffit = deck top − 1.4 m (`DECK_T_M`, `tools/author_bridges_blend.py:54`). 3DEP is bare earth with bridges removed, so every deck top below except College's is **interpolated between abutments**, not measured, and reads low. Caltrans's design minimum for new work is 5.03 m.

  | Deck | Over | Deck top over road | Soffit clearance |
  |---|---|---|---|
  | The loop's College deck (v0.18 built centreline) | I-8 EB | 110.19 over 103.58 = 6.61 m (v874.4) | **5.21 m** (as built) |
  | The loop's College deck | I-8 WB | 111.12 over 103.86 = 7.26 m (v881.8) | **5.86 m** (as built) |
  | I-8 EB / WB | Fairmount | 5.3–5.5 / 5.4–5.6 m (bare-earth gap 5.0–5.9 m) | 3.9–4.1 / 4.0–4.2 m (interpolated; real decks surely higher) |
  | I-8 EB | Waring's south end | 43.8 over 37.96 = 5.8 m | 4.4 m (interpolated) |
  | Waring | I-8 WB | ~6.3–7.0 m (abutments 36.9 / 37.1 m over WB at 30.1–30.8 m) | ~4.9–5.6 m |
  | Alvarado Canyon Rd flyover | Waring and two WB ramps | **unknown** | **unknown** |
  | X8 link decks | — | 4.3 / 5.2 m ± 1 | 2.9 / 3.8 m (**suspect bare-earth**) |

  The Phase 4 plan's rule (A5): where soffit clearance comes out under 4.9 m [invented], the deck is raised, never the ground lowered; every raise is listed and checked on Street View.
- **Drainage:**
  - Alvarado Creek runs along the north side of WB from −117.09 to −117.072, passes under I-8 in a culvert at −117.0690, and runs on along the south side east of College.
  - The San Diego River's riparian belt lies NW of Zion / Mission Gorge.
  - No river crossing anywhere.
- **Network relief:** 33–212 m after Phase 1; 28.7 m low after Phase 3; **23.2–212 m** after Phase 4 (Mission Gorge's sag south of Zion).
- **L4, stacked roads: YES, for the first time.** At X9: Waring over WB, EB over Waring, and the Alvarado Canyon Rd flyover (see-only) over Waring and two WB ramps. At X8: I-8's decks over Fairmount (see-only in the default), plus exit 8's and the EB on-ramp's own small bridges. The trolley over I-8 (see-only). At X10, College over I-8 (see-only freeway under it in the default). Phase 4's Step 1 exists for this.
- **The L3 real-ridges clamp** (global 20/40 m) stays. The split-level bank is real ground: its 18.8 m rise sits under the 22 m band, so the clamp can't settle where the two carriageways' road zones overlap. The plan authors an earth bank or wall there.
- **Banking:** none (L10). Real elevation only.

## 4. Corner-by-corner character

| # | Corner / place | What defines it | Drive test must confirm |
|---|---|---|---|
| J2 | Princess View → Waring SW (+84°, cw) | Phase 1's pad; Waring's median noses | the new arm is welded with no seam step; the pad is unmoved; the 23 → 28 m widening reads as natural |
| P3-WAR | Waring's crest (s 400) | planted boulevard, Greenbrier's school crosswalk | no float over the crest |
| J6 | Waring → Zion (+60°) | library NW, Arco SW, Grocery Outlet SE, park and pool N; school ladders on every leg | no seam step on the pad; the Waring S stub and the slip read as closed roads (until Phase 4) |
| P3-ZION | Zion's pitch, s 570–660 | 10 % between houses; Foster Elementary's blacktop on the south side (s ~450) | no launch at the top; no bottoming at the foot; the cut on the one side reads as a bank |
| J7 | Zion → Mission Gorge (+103°) | Grantville: Kaiser Zion Medical Center and Vons to the south; industry north; river woodland across Mission Gorge | the pad on the valley floor; Mission Gorge S and Zion W stubs closed (MG S until Phase 4) |
| P3-MG | Mission Gorge s 300–400, and s 1150–1250 | the 28.7 m sag; then the tall-tree row whose shadows cross all six lanes | no bottoming in the sag; the median openings drivable |
| J3 | Mission Gorge → Princess View (+106°) | Phase 1's pad on the valley floor | the converted arm welded; MG straight through J3 is smooth |
| P4-WAR | Waring's canyon, s ~550–1250 | 7–8 % down through chaparral and tall trees, a narrow concrete median | no steps; the NB cut wall kept |
| X9 | Waring between the two levels of I-8 | under the flyover, over the WB bridge, under the EB bridge, to the T | no step at either deck; real headroom under the EB deck and the flyover; no flyover pier in a lane |
| I8-split | EB on the hillside, −117.093..−117.072 | EB up to 18.8 m above WB, chaparral bank between | no wobble at 65 mph and above; the bank reads as a hillside, not a wall |
| X10 | College exit | the EB exit climbs 8.5 % to College; the loop's twin 96 m decks just ahead; SDSU's red tile to the SW | the closure taper steers you onto the exit; the ramp meets the loop cleanly; the see-only freeway under the deck reads right |
| X8 | Fairmount / Mission Gorge | I-8 over Fairmount; the trolley viaduct and the Grantville station | the WB exit 8 bridge seats; the closure taper steers you off; Fairmount under the decks has headroom |
| P4-MG | Mission Gorge south, Friars Rd to Fairmount | divided at Friars, undivided through Grantville, divided again under I-8 | every side street reads as a closed street; Friars Rd's two barriers read right |
| END-W / END-E | The closures | K-rail lane-closure taper, then the barrier across; see-only pavement beyond | the taper steers you off at the last exit at speed; the barrier spans every closed lane |

Reference imagery: `aerial/overlays/00_p34_overview.jpg`, `x_zion_waring.jpg`, `x_zion_mgr.jpg`, `c_grantville_osm.jpg`, `x_waring_i8_*.jpg`, `x_college_i8_osm.jpg`, `x_fairmount_i8_osm.jpg`, `c_i8_corridor_osm.jpg`, and routes4's `naip_*_osm.png`. **Street View frames: unknown until the Street View pass.**

## 5. Built environment and landmarks

- **Waring, J2 → J6:** single-family homes, sidewalks on both sides. The Allied Gardens shops are at J6.
- **J6:**
  - NW: Benjamin Branch Library;
  - SW: Arco;
  - SE: the Grocery Outlet / Dollar Tree centre and its big lot;
  - N: Allied Gardens Community Park and pool.
- **Zion:** single-family homes. Foster Elementary (blacktop playground, south side, s ~450) and Magnolia Science Academy (south). The last ~300 m: Kaiser Zion Medical Center and the Vons lot (south), industry (north).
- **Mission Gorge, J7 → J3:**
  - **NW (river) side:** dense riparian woodland near Zion, then open lots and the quarry behind fences or K-rail, with dirt shoulders (s 1050–1350).
  - **SE side:** parking lots and commercial, including the shopping centre at the Greenbrier signal.
- **Mission Gorge south of Zion:** Grantville's commercial strip; Friars Road's divided junction just south of J7.
- **Waring south:** canyon slopes of chaparral and coastal sage, with homes on the rims. The Del Cerro Tennis Club is at s ~980. Palms at the curve (s ~530).
- **The I-8 corridor:**
  - SDSU's Spanish-revival red-tile campus is SW of College; the trolley curves into the SDSU tunnel south of I-8.
  - Grantville: Home Depot, Norm Reeves Toyota and DCH Honda to the W/N; the elevated Grantville trolley station; the Union Grantville apartments (under construction in 2022).
  - An overhead sign gantry ~30 m east of aerial st 1250.
  - Gore chevrons at every merge.
- **Signs:**
  - mapped speed limits: Waring 35 / 40 / 45 mph, Zion 30 mph, Mission Gorge 45 / 55 mph north of Zion and 45–50 / 35 / 50–55 mph south of it, I-8 65 mph;
  - school crosswalks at J6, Greenbrier (Waring) and 51st St (Zion);
  - about 14 ramp-meter nodes;
  - corner arrows by Kevin's 0044 rule at the tight corners, both directions.
- **Furniture:**
  - lamp positions **unknown** until a Street View night check;
  - signal heads not modelled;
  - guardrails can't be resolved at 0.6 m (**unknown; Street View**);
  - no sound walls anywhere from Fairmount to College.

## 6. Vegetation and terrain palette

**Canopy share** in a 10–40 m band each side, per 250 m bin. CIR/NDVI thresholds are invented and eye-checked.

| Place | Canopy | Scrub |
|---|---|---|
| Zion | 3–15 % | — |
| Urban legs generally | 3–17 % | — |
| Waring canyon (aerial st 1250–1500) | 40–45 % | 26–34 % |
| I-8 north slope | 30–60 % (shrub) | — |
| I-8 split median | 16–55 % | 34–66 % |

**Zones:**
- Waring's median: planted median trees.
- Zion: residential street trees.
- **The river belt** NW of Zion / Mission Gorge: riparian woodland. Eucalyptus, willow and palms are likely, **not confirmed**. Stand-ins: Sycamore V1/V2 and Oak3.
- **Cut slopes, the Waring canyon and the I-8 split bank:** chaparral and coastal sage scrub (Sage, Yucca, Bush, Agave). Shrubs, not trees, in the split.
- **Palms:** Waring s ~530 (south of Zion); Mission Gorge near Zion.

**Eucalyptus candidates** (0040). All are identified from shadow length (~25 m, so 20 m or taller); species can't be confirmed at 0.6 m:
- the Mission Gorge SE-side row at s ~1150–1250;
- the Waring canyon's east side at aerial st 1300–1450 (s ~630–780 from J6);
- the river woodland NW of J7.

**Street View confirms.** The installed Gum model goes there first.

**Backdrop and skyline.** The far ring's west edge today is −117.108. From a freeway end at −117.1045 it misses **53.5 %** of the skyline (worst 4.29°, azimuth 249):

| West edge | Skyline missing | Worst gap |
|---|---|---|
| −117.115 | 28.2 % | — |
| −117.125 | 15.5 % | — |
| −117.13 | 12.7 % | — |
| **−117.14** | **2.8 %** | 0.69° |
| −117.15 | 1.4 % | — |

- From the Fairmount deck: 42.3 % → 2.8 %.
- From Mission Gorge at Zion: 8.5 % (−117.12 is enough).
- From Waring at I-8: 16.9 % → 1.4 %.
- The south edge (32.755) is fine: the mesa wall is 0.2–0.8 km away.

## 7. Atmosphere and light

- Latitude 32.78–32.80 N. True north as on the loop.
- **Bearings in drive order:**

  | Road | Bearing |
  |---|---|
  | Waring J2 → J6 | ~224–239° (SW) |
  | Zion | ~270° (W), cw |
  | Mission Gorge J7 → J3 | ~65° (ENE) |
  | Waring south | roughly S |
  | Mission Gorge south | roughly S |
  | I-8 | E–W |

- **Sun:**
  - clockwise down Zion, westbound, drives into the afternoon sun;
  - Mission Gorge north-eastbound and I-8 eastbound drive into the morning sun;
  - I-8 westbound drives into the late-afternoon sun.
- **Presets:** as the loop ships, plus 0043's sodium night on the lit stretches (Phase 3 D3; Phase 4 D4 interchanges).
- **The one photo that sets the mood:** not chosen. Candidates: the top of Zion's hill looking west over Grantville; eastbound I-8 on the split level at golden hour with westbound below. **Kevin's pick.**

## 8. Asset plan, owned assets first

| Need | Owned asset | Notes | Or GAP |
|---|---|---|---|
| Street road, curbs, sidewalk, paint | the loop's materials | none | — |
| Planted median / terracotta median | the loop's median set; Phase 1's terracotta texture | none | — |
| Side-road barrier stubs, freeway closure barriers and tapers | **Kevin's 4.04 m K-rail jersey module** (the race walls' profile) | none | — |
| Freeway concrete median barrier | the K-rail profile swept continuous, as `1WALL`, double-sided | none | — |
| Freeway concrete lanes (PCC) | none owned | CC0 concrete texture (ambientCG), 1024 px | GAP: CC0, no purchase |
| Asphalt shoulders, dikes, lane / edge / gore paint | the loop's asphalt and markings | none | — |
| Bridge bodies and piers | 0046's BRIDGESTRUCT bodies (1.4 m deep) | piers from the built pavement | — |
| Trolley viaduct and Alvarado Canyon Rd flyover (see-only) | none owned | authored box section and piers | GAP: authored, no purchase |
| Sodium lamp | LIGHTPOST (0043); **a lighter variant is needed** (~1/10 of the points) | decimation | precondition |
| Signs | W1-6 arrows and speed plates (`make_sign_textures`) | closure signs from the same set | overhead guide signs: later |
| Trees | TreeFX: Gum, Sycamore V1/V2, Oak3, Sage, Yucca, Bush, Agave, palms | none | flowering shrubs: 0040 |
| Buildings | OSM footprint extrusion | none | — |

**Licensing:** Kevin's stance stands. Releases are never gated on asset provenance. Packages follow `docs/PUBLISHING.md`.

## 9. Data sources and capture assets

All of these are in the session scratchpad `p34/`.

- **OSM:**
  - the Phase 1 worktree's `data/osm.expansion.json` (2026-10-14);
  - `routes4/osm.extra.json` (waterways, rail, barriers, ramp meters);
  - `aerial/osm_ctx.json` (trolley, bridges, walls, landmarks).
- **Route analysis:**
  - `routes3/{analysis3.json, mouths3.json, legs3.geojson, profile3.json, route_map_phase3.png}`;
  - `routes4/{movements.json, crossings.json, i8_ways.json, i8_stations.json, links.json, phase4_routes4_map.png}`;
  - `revise/{r1.py, r2.py}` (Mission Gorge south and Alvarado Canyon Rd census; I-8 chain stations).
- **3DEP:**
  - `terrain/{profiles,budget,grid,horizon,missing,extra}.result.json`, `samples.json`, `dep_cache.json`;
  - `routes4/profiles.json.gz`.
- **NAIP 2022-04-25:**
  - cached outside the repo at `C:/Users/Owner/AppData/Local/airoso/naip_sd_p34/`;
  - `aerial/widths_eye.csv` (45 stations), `i8_xsec.json`, `i8_separation.json`, `veg_bins.json`, `xstreets.json`;
  - `aerial/overlays/`, `aerial/sheets/`, `aerial/zoom/`, `routes4/naip_transects.json`.
- **Pipeline:**
  - `pipeline/{i8_census.json, ramp_mouths.json, road_kn5.json}` and their scripts.
- **No KML.** Every road is on the real network (L1).
- **Missing, to be captured:**
  - the Street View pass: J6/J7 corners, Zion driveways, lamps at night, the eucalyptus rows, guardrails, ramp lanes and signals, deck heights, the flyover's piers, the Union Grantville apartments;
  - the stack table's heights (Phase 4, Step 0);
  - a shoulder-width aerial pass;
  - the curb-return radii at J6 and J7;
  - a same-station width re-read at the J2 and J3 arms.

## 10. Location-specific QA (these become the §Look rows in the drive reports)

**Phase 3:**
1. Turning onto Waring SW at J2: no seam step where Phase 1's stub used to be.
2. Over Waring's crest and into J6: the corner reads as Allied Gardens, with the library, the Arco and the park. The Waring S stub reads as a closed road.
3. Down Zion's 10 % between the houses: no launch at the top, no bottoming at the foot. Every side street ends in a barrier on a short stub, not a curved curb.
4. At J7, Grantville: the turn onto Mission Gorge at road speed with no seam step.
5. Mission Gorge's sag at s 300–400 is the lowest point you have driven here. The tall trees' shadows cross all six lanes around s 1200. You can U-turn at the median openings.
6. The Mission Gorge Speedway is still sealed at J2 and J3.

**Phase 4:**

7. Down Waring's canyon to I-8: under the flyover, over the westbound bridge, under the eastbound one, with real headroom and no step at either deck.
8. Up the eastbound split-level hill at speed: no wobble, and westbound visibly below you across a chaparral bank.
9. Eastbound toward College: the closure taper steers you onto exit 10 at speed, and the ramp meets the loop with no step. The see-only freeway under the College bridge reads right.
10. Westbound from College to X8: exit 8 to Mission Gorge, the trolley crossing overhead, and the closure taper before the Fairmount bridges. Then back up Mission Gorge Rd past Friars Rd to Zion.
11. At each closure, the barrier spans every closed lane, and the see-only pavement beyond doesn't look like the end of the world.
12. Both Lake Murray Speedways are still sealed at the College ramp ends.

**Both phases:**

13. Load time and frame rate no worse than v0.18.0, by Kevin's judgement, at the fixed spots recorded in each report.

## 11. Build plan

- **Phase 3** (EXPANSION-PHASE3-PLAN.md):
  - Step 0: data, the `west` route, the grid to 88 columns, stub declaration;
  - Step 1: `expansion.west.json`, the J6/J7 pads, the J2/J3 arm swaps with width transitions, the map;
  - Step 2: ground;
  - Step 3: road → Drive 1;
  - Step 4: dressing → Drive 2;
  - Step 5: release.
- **Phase 4** (EXPANSION-PHASE4-PLAN.md):
  - Step 0: data and the stack table;
  - Step 1: the stacked-road rule, proven byte-identical and rehearsed;
  - Step 2: the freeway intermediate, the profile planner and the JUNCTIONS merge and freeway-end rules;
  - Step 3: ground and the split bank;
  - Step 4: road and every structure over a lane → Drive 1;
  - Step 5: dressing → Drive 2;
  - Step 6: release.
- **Config changes:**
  - `route.bbox` west to −117.101 (Phase 3), then −117.107 (Phase 4);
  - the `west`, `freeway`, `waring_s` and `mgr_s` routes;
  - `terrain.grid_grow.cols_w` 88 and the frame pin (90 or 104–105 only if Phase 4's D1 west alternatives are chosen);
  - `terrain.far_extent` west per Phase 3's D2;
  - lamp stretches, tree zones and stubs (`data/stubs.json`).
- **Authored in Blender**, never overwritten by the draft:
  - the J6 and J7 pads;
  - ramp-end pads;
  - the split-level bank or wall;
  - any lost cut slopes;
  - the trolley viaduct and the Alvarado Canyon Rd flyover;
  - the see-only frontage road.
- **Gates:** each plan's Verification table, with all four L5 gates on the built file, `kn5_ground_check` included once it is wired.
- **First question for each drive test:**
  - Phase 3: *"Drive down Waring to Zion, down Zion's hill to Grantville and back up Mission Gorge to Princess View. Did any corner, the Zion pitch or the Mission Gorge sag catch the car?"*
  - Phase 4: *"Drive down Waring to I-8, east up the split-level hill and off at College onto the loop, then back west from College and off at Mission Gorge, and up Mission Gorge Rd to Zion. Did any deck, merge, closure or the split-level hill catch the car?"*

---
**Kevin's approval:** ☐ approved as-is · ☐ approved with the changes noted above. Date: \_\_\_\_

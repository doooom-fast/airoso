# Location dossier addendum: Lake Murray north expansion (san-diego-lake-murray, ledger 0054 Phase 1)

> This addendum covers the new roads only. The loop's facts stand as built: v0.17.1, with v0.18.x in flight.
> - **Sources:**
>   - OSM from the Overpass primary server, data as of 2026-10-12T18:03Z (0.003 days old; TLS verified; 7-day guard passed);
>   - USGS 3DEP 1 m;
>   - NAIP 2022-04-25 at 0.6 m, the only year the USGS ImageServer serves here.
> - The research files are in the session scratchpad `expansion/{routes,terrain,aerial,pipeline,revise}/`. P0 copies what the build needs into the workshop, with this provenance.
> - **Stations are metres from the junction node at the start of each leg, in drive order J1→J5.** The terrain lens's stations started 50–95 m after each node and have been shifted to match. The aerial stations match these to within about 20 m.
> - Plan: [`EXPANSION-PLAN.md`](EXPANSION-PLAN.md).

## 1. Identity and intent

- **Kind:** `street_port` (real public roads as they exist), the same kind and archetype as the loop.
- **Why:** Kevin's father's neighbourhood grows north, from the Lake Murray plateau down to the San Diego River valley and back up to the Navajo crest. The drive we are after has three parts:
  - the 10 % plunge down Princess View to the valley floor;
  - the fast divided sweep of Mission Gorge Rd along the river, with the gorge walls rising either side;
  - the 118 m climb up Jackson's canyon, with Cowles filling the windscreen.
- **Kevin's words, read leg by leg:**
  - "college down waring to princess view" = Waring Rd, J1→J2;
  - "princess view to mission gorge" = Princess View Dr, J2→J3;
  - "mission gorge to jackson" = Mission Gorge Rd, J3→J4;
  - "extend jackson down to mission gorge" = Jackson Dr north, from the Navajo/Jackson corner down to J4.

  Every connection exists as described.
- **Layouts:** one model for all of them (L8).
  - Lake Murray Free Roam (`street`) becomes the whole connected network.
  - Lake Murray Speedway and Speedway Reverse (`race_cw` / `race_acw`) keep their laps, with the new openings sealed.
  - Mission Gorge Speedway (+ Reverse) is a Phase-2 candidate: the north loop (8.72 km) or the grand loop (17.43 km).

## 2. Route geometry: facts per segment

| Seg | Roads (OSM, forward sense) | Length fwd / rev | Lanes / width (eye, NAIP 2022) | Kerb / sidewalk | Surface | Notes |
|---|---|---|---|---|---|---|
| A | **Waring Rd**, node 304728588 → 1713352279. Westbound ways 436315962, 436315958, 436411981, 436411978, 159243455, 1370375342, 436411993 | 977.8 / 956.6 m | 2+2 (3 at the turn pockets). Curb to curb 24.0–27.5 m (median of readings 26.5) | curbs; sidewalks right behind the curb on both sides | asphalt | **Divided:** OSM carriageways 13.1 m apart (max 18.4); planted raised median 1.5–6 m, trees st 250–550. 35–40 mph. Signals at J1, Eldridge St (st ~415–440) and J2; stop sign at Galewood. Leaves J1 heading ~321° (NW) and curves through west to ~236° (SW) at J2 |
| B | **Princess View Dr**, 1713352279 → 1484501766. Ways 1220464891, 1220464885, 1343339700, 1224662143, 1224662147, 1224662142, plus 135149733 and 1224662145 across the medians | 1,106.2 / 1,134.9 m | 2+2, then 3+2 on the last 614 m. 22.5–28.0 m (median of readings 24.0) | curbs, parking lanes, sidewalks on both sides | asphalt | **Undivided**, double yellow. Raised nose and turn pocket at Fontaine St (st ~500–557). Signal at Glenroy St (st 79–88). Yellow school ladder crosswalks at J2 and Glenroy (Lewis Middle School). No maxspeed tag |
| C | **Mission Gorge Rd**, 1484501766 → 1484501806. Eastbound ways 436567838, 436567835, 436413313, 436424128, 1075032356, 436424133, 1075032355, 436413315, 436413312, 436413316, 436413317, 436413319 | 2,272.1 / 2,267.7 m | 3+3 plus bike lanes. 27.5–33.0 m (median of readings 30.2) | curbs on both sides | asphalt | **Divided:** carriageways 16.1 m apart (max 18.6); **terracotta raised median** 1.5–8 m. 55 mph. Turn pockets at Margerum Ave (st 1099–1108; **no signal tagged in OSM**). Two median crossovers (st 174 / 202). Nine commercial service mouths at st 45–384 |
| D | **Jackson Dr north**, driven 1484501806 → 1713415645 (23 ways, including 265724311, 763 m long) | 1,999.3 / 2,008.2 m | 2+2, with a painted double-double-yellow median 1.5–4.5 m and buffered bike lanes. 17.0–26.0 m (median of readings 21.0); narrowest at Hemingway Dr, st 500 | curbs on both sides | asphalt | **Undivided**, except the last ~180 m into J4, which OSM maps as two one-way ways about 12 m apart (436413311 / 436413304, 1076791040, 436413294). The aerial shows a hatched, painted 3–4 m median there. On the 763 m piece: 1 lane downhill, 2 uphill. Left-turn pockets at Tuxedo Rd (st 790–800) and Park Ridge Blvd (st 1623–1635, signalised). No maxspeed tag |

- **Total, junction node to junction node:** 6,355.4 m forward / 6,367.4 m reverse.
- **Bridges, culverts, rail:** none. No route way carries a bridge, layer or tunnel tag. A segment test against every river, stream, motorway and trunk found 0 crossings.
- **Closest approaches:**

  | Feature | Distance | From |
  |---|---|---|
  | San Diego River | 248–325 m | Mission Gorge and Princess View at J3 |
  | San Diego River | 580 m | J4 |
  | I-8 | 1.58 km | |
  | SR-52 | 3.63 km | |
  | SR-125 | 3.8 km | |

- **Junctions.** All five are signalised (3–4 traffic_signals nodes within 35 m). Heights are 3DEP at the node.

  | | Position | Height | Shape | Turn (forward) | Curb returns |
  |---|---|---|---|---|---|
  | J1 College/Navajo/Waring | 32.79385, −117.06764 | 124.9 m (loop: 125.1–125.3) | **Y with three arms**: College→Waring is straight through, Navajo branches NE | straight (−12°) | NE free-flow sweep ~30 ± 10 m round a planted wedge; SE ~10 m |
  | J2 Waring/Princess View/Mound | 32.79734, −117.07601 | 103.9 m | near-orthogonal four-way; Mound Ave 11 m wide | right 84° | 6–8 m |
  | J3 Princess View/Mission Gorge | 32.80667, −117.07898 | **33.4 m** (lowest point) | T plus a 12 m quarry/industrial drive (OSM: "Tierrasanta Boulevard (Proposed)", way 683943070) | right 76° | SW 10–12 m, SE 5–6 m |
  | J4 Mission Gorge/Jackson | 32.81699, −117.05952 | 92.4 m | T plus the north arm to the MTRP visitor centre (OSM service way w60516202); gravel trailhead lot to the NW | right 74° | south 8–10 m, north ~6 m |
  | J5 Navajo/Jackson | 32.80394, −117.04610 | 209.9 m (loop: 209.2–210.2; 209.7 at v2318) | four-way; Jackson south 34 m wide, Jackson north 24 m | straight (+7°) | 8–12 m |

  The reverse direction mirrors these, with left turns of 66–82°.
- **Junction arm widths, 60 m out from the node:**

  | Junction | Arm | Width (m) | Median |
  |---|---|---|---|
  | J1 | Navajo | 29.0 | 2.5 m planted |
  | J1 | College | 27.5 | 5.5 m planted |
  | J1 | Waring | 26.5 | 1.5 m |
  | J2 | Waring NE | 27.0 | |
  | J2 | Waring SW | 23.0 | |
  | J2 | Princess View | 22.5 | |
  | J2 | Mound | 11.0 | |
  | J3 | Mission Gorge E | 33.0 | |
  | J3 | Mission Gorge W | 28.0 | |
  | J3 | Princess View | 27.0 | |
  | J3 | North drive | ~12 | |
  | J4 | Mission Gorge E | 31.0 | |
  | J4 | Mission Gorge W | 29.0 | |
  | J4 | Jackson | 28.5 | 3.0 m painted |
  | J5 | Navajo E | 30.0 | |
  | J5 | Navajo W | 28.0 | |
  | J5 | Jackson S | 34.0 | |
  | J5 | Jackson N | 24.0 | |

- **The openings on the loop's outer (L) curb** (`revise/mouth_sides.py`, against `centerline.local.json`):

  | | J1 Waring | J5 Jackson north |
  |---|---|---|
  | Opening starts | v1514, where Waring's SW curb crosses the loop's outer curb | v2314.8, where Jackson north's SW curb crosses it |
  | Other side | Waring's NE curb crosses at v1520.6, and its R ≈ 30 m return reaches v1528.5 (R 20–40 gives v1525.7–1531.6) | the R 8–12 m return reaches back to v2312; the NE side runs on as Jackson south's east curb (within 1 m at v2321–2323) |
  | Opening | **v1513.5–~1528.5 (~52 m)**; ~7 vertices (~25 m) past box end v1521, in race_cw's exit funnel | **v2312–~2322**, inside box 2311–2328, covering apex 2319 |
  | Centreline crosses the curb | ~v1517.4 | ~v2317.7 |
  | Carriageway cuts | outbound v1520 at 81.7°, inbound v1516 at 75.6° | v2318 at 57.8° |

  The existing mainline mouths are 76.9–89.4°, on straights.
- **Side mouths along the new roads.** None of these is built as drivable. The full table is in `routes/mouths.json`.

  | Road | Public streets (station) | Service ways |
  |---|---|---|
  | Waring | Galewood 122, Eldridge 415, Birchwood 687, Mound 978 | — |
  | Princess View | Glenroy 79, PV Ct 175, PV Pl 315, PV Way 384, Fontaine 545, Laura 714 | 4 |
  | Mission Gorge | Conestoga 429, Margerum 1099, Mission Montana 1381, Mission Vista 1673, Deerfield St/Cres 2018 | ~14 (2 private) |
  | Jackson | Doreen 179, Hemingway 503, Winding Creek 646, Tuxedo 790, Park Ridge 1623, Birchcreek 1802 | 8, plus the SDCWA emergency road at 239 (unpaved, access=no) |

  Residential driveways on Princess View and Jackson are mostly unmapped. **Unknown; the Street View pass counts them.**
- **Width source:** eye readings on NAIP at 0.3 m, against a 10 m grid. The automatic walker is not used: it drops a carriageway on Princess View and Jackson.

## 3. Elevation and drainage

3DEP 1 m, node to node, every 5 m. Grades are taken over a 20 m chord after a 25 m smooth (`revise/measure.json`).

| Road | Height | Max grade | Within 100 m of the junctions | Sustained (per 100 m) |
|---|---|---|---|---|
| Waring | 125.0 → 103.9 m (−21.1) | −6.9 % at s 70 (6.0 % uphill on the reverse carriageway) | −6.9 % leaving J1; −1.8 % into J2 | 6.5 % |
| Princess View | 103.9 → 33.4 m (−70.5) | **10.2 % down at s 480; 10.4 % up on the reverse** (loop max 8.9 %; connector cap 11 %) | ≤ 3.7 % | 10.0 % |
| Mission Gorge | 33.4 → **114.3 m crest at s 1460** (32.8121, −117.0657) → 92.4 m (+80.9 / −21.9) | 7.4 % | ≤ 2.6 % | 7.2 % |
| Jackson north | 92.4 → 210.1 m (**+117.7**, no descent) | 7.9 % uphill at s 975; **9.2 % on the downhill carriageway ~180 m from J4**, on the divided approach | 7.5 % climbing out of J4 | 7.8–8.0 % |

**Cross-section character.** These are terrain-lens readings over the mid-legs; the 50–95 m nearest each node is measured in P1.
- **Waring:** at grade, within ±1.4 m.
- **Princess View:**
  - a convex break off the plateau at s ≈ 175;
  - a sag near the bottom;
  - half-cuts up to +6.4 m and half-fills down to −3.9 m.
- **Mission Gorge:**
  - west third at grade or half-fill toward the river. The river side falls 3–4.5 m below the road, and up to 9.6 m below the westbound side at s 255–630.
  - cut into the south wall from s ≈ 1115 to J4, by +3 to +11.4 m within 16–40 m;
  - full cuts at s 1515–1565 and 1715–1815.
- **Jackson north:**
  - sidehill the whole way;
  - the SW side is cut 2.5–10.3 m, with a ridge 30–50 m above the road at 70–115 m out (18–22° above the eye);
  - the NE side falls away 4–8 m.

**Other facts.**
- **Network relief:** 101–212 m today; 33–212 m with the expansion.
- **Drainage:** the San Diego River runs 248–580 m north of the route and is never crossed. The riparian woodland marks it.
- **Banking:** none (L10). This is a street port, with real elevation only.
- **L4:** no stacked roads. No expansion point has another road within 150 m in plan that is more than 20 m above or below it.
- **L3 clamp, re-simulated on fresh 3DEP transects** (`revise/clamp_options.py`):

  | Rule | Jackson north | Mission Gorge | Princess View |
  |---|---|---|---|
  | As amended (full to 80 m, released by 250 m) | 384 points moved > 1 m, worst −24.3 m | 122 points, worst −6.3 m | 10 points, worst −2.8 m |
  | With the D3 default (40 m on the two sidehill roads) | 0 points moved | 0 points moved | unchanged |

  Within 40 m of the sidehill pavements the real ground is never more than 22 m from the road (0 of 4,050 points).

## 4. Corner-by-corner character

| # | Corner | What defines it | Kerb reality | Drive test must confirm |
|---|---|---|---|---|
| J1 | College → Waring, straight on (the loop turns right onto Navajo here) | Y-junction, three median noses, yellow school crosswalk across College; St Therese church and Fire Station 31 | curbs, planted medians; a 52 m opening on the loop's outer curb | no step at the weld; both Speedways still sealed, including past v1521 |
| J2 | Waring → Princess View, right 84° | near-orthogonal four-way, yellow ladder crosswalks on all legs, Waring's planted median noses | returns 6–8 m | no seam step on the pad; the Mound Ave and Waring stubs read as streets you can't enter |
| PV | Princess View descent | convex break at s ≈ 175, ~10 % for ~900 m, sag at the bottom | — | no launch at the break; no bottoming at the sag |
| J3 | Princess View → Mission Gorge, right 76°, the 33.4 m low point | vacant dry-grass lot to the SW; quarry drive to the north; Mission Gorge 28–33 m wide | SW 10–12 m, SE 5–6 m | the pad on the valley floor; the quarry visible to the north |
| MG | Mission Gorge crest at s ≈ 1460 | full cuts at s 1515–1565 and 1715–1815 | — | no float over the crest; the cut walls read as walls |
| J4 | Mission Gorge → Jackson, right 74° | terracotta median noses, white ladder crosswalks, park entrance to the north; Jackson climbs away at 7.5 % | south 8–10 m, north ~6 m | the pad at the foot of the climb; the visitor-centre stub sealed |
| J5 | Jackson north → the loop, straight (+7°) | big four-way; Keils', Ace Hardware and restaurants on the SE/E corners | returns 8–12 m; raised medians on Navajo | **no step ≥ 6 cm (the 0050 box)** in any layout |

Reference imagery: the NAIP sheets `aerial/overlays/02–06_*.png`. A Street View frame for each corner is added in the Street View pass. **Unknown until then.**

## 5. Built environment and landmarks

- **Waring:** dense single-family homes, mostly with their sides and backs to the road. The Allied Gardens shops at Waring/Zion are off the route, SW of J2. Schools: Lewis Middle School and Marvin Elementary, near J2.
- **Princess View:** single-family homes, then Grantville self-storage and industry on both sides (B 750–1078), then a vacant lot at J3.
- **Mission Gorge:**

  | Stretch | North side | South side |
  |---|---|---|
  | st 0–300 | the Grantville aggregate **quarry** and batch plants (~32.815, −117.0724): a huge white terraced pit | |
  | st 300–1200 | San Diego River riparian woodland, canopy down to the curb | **apartment blocks at st 500–1000** |
  | st 1100–1300 | Margerum retail and apartment strip | |
  | st 1300–2250 | open slope and canopy | houses behind rear-yard block walls |

- **Jackson north:** an open-space canyon with houses only on the rims (D ~250–1500). Dailard Elementary is to the west. Commercial at J5.
- **Landmarks off the route but nearby or in view:**
  - MTRP Visitor & Interpretive Center (~32.8202, −117.0561), about 350 m north of J4;
  - Kumeyaay Grinding Rocks (32.8244, −117.0544);
  - Old Mission Dam (32.8397, −117.0432), on Father Junipero Serra Trail, not on Mission Gorge Rd;
  - Kumeyaay Lake (32.8420, −117.0323).
- **Peaks:**

  | Peak | Height | Position |
  |---|---|---|
  | Cowles | 483.2 m (3DEP) | |
  | Pyles | 420 m | 32.823 |
  | Kwaay Paay | 364 m | 32.828 |
  | South Fortuna | 333 m | |
  | North Fortuna | 393.5 m | 32.847 |

- **Signs:**
  - mapped speed limits: Waring 35–40 mph, Mission Gorge 55 mph;
  - Princess View and Jackson untagged (**unknown; Street View**);
  - school crosswalks at J2 and Glenroy;
  - corner arrows by Kevin's 0044 rule at J2, J3 and J4, in both directions (0051).
  - The loop's M3 (J1) and M4 (J5) stand inside the new pavement. They move to the Speedways' race files.
- **Furniture:**
  - lamp positions are **unknown** until a Street View night check. The plan's default lights everything except Jackson's open canyon, labelled authored.
  - signal heads are not modelled, as on the loop.
  - OSM has one fence, near C st 1997.
  - guardrails can't be resolved at 0.6 m (**unknown; Street View**).
- Furniture stands on true ground: the road comes down to the data, never the furniture up.

## 6. Vegetation and terrain palette

**Canopy share** in a 10–40 m band each side of the road (CIR/NDVI; the thresholds are invented and eye-checked):

| Road | Canopy | Other |
|---|---|---|
| Waring | 5–14 % | |
| Princess View | 2–24 % | |
| Mission Gorge | 3–6 % at J3, rising to 30–58 % on the north side at C 1250–2289 | |
| Jackson | 20–69 % | scrub 10–55 % |

**Species zones:**
- **Open slopes** (Jackson's canyon and the gorge sides): chaparral and coastal sage scrub. Sage, Yucca, Bush, Agave.
- **The river belt north of Mission Gorge:** riparian woodland, bright red in CIR. Likely willow, cottonwood or sycamore; **not confirmed**. Stand-ins: Sycamore V1/V2 and Oak3.
- **Waring:** planted median trees.
- **The canyon:** no palms.

**Kevin's later requests (ledger 0040):**
- **Eucalyptus.** The candidate belt **E1** is a stand of tall grey-green, open-crowned trees casting ~20 m shadows, on the NE side of Jackson's canyon (D ~1000–1400, ~32.810, −117.051). NAIP can't confirm the species; **Street View confirms**. The installed Gum model goes there first.
- **Flowering shrubs.** Red and pink patches show at the curb at D ~500 (SW side) and on Navajo east of J1. Each zone carries a flowering-shrub slot for 0040's species pass: bougainvillea, oleander, hibiscus, lantana, bird of paradise, and ice plant on the cut slopes.

**Ground:** dry chaparral and tawny grass. The quarry's pale terraces come from 3DEP plus a dry-ground texture.

**Backdrop and skyline.** 26 % of the skyline seen from the expansion lies outside the 0046 far box.

| Direction | Share of skyline | Angle above the eye | Ground |
|---|---|---|---|
| North of 32.822 | 17 % | median +3.1°, max +9.4° | up to 416 m |
| West of −117.0895 | 10 % | median +0.4°, max +2.3° | low mesa |

- Proposed far box: [32.755, −117.108, 32.850, −116.998].
- Proposed `cowles_mountain` include: north edge 32.82 → 32.828.

**Gorge walls**, seen from Mission Gorge s 1165–2165:
- south side +10 to +15°, with 170–180 m ground at 265–460 m;
- north side +5 to +7.6°, with 220–229 m ground at ~1 km.

**Peaks from the new roads** (fine line of sight, eye 1.2 m):

| From | Cowles | Others |
|---|---|---|
| Princess View near J3 | +5.7° at 4.5 km | |
| Mission Gorge s 565–1465 | **hidden** | |
| Mission Gorge s 1865 | +7.4° | |
| Mission Gorge s 2190 (J4 approach) | +8.2° | Pyles +8.5°; **Kwaay Paay hidden** behind a +8.85° knoll 321 m away |
| Jackson s 550–1550 | +9.6–9.8° | Kwaay Paay +8.0° at s 550 |
| Jackson s 1915 | +9.4° | |

## 7. Atmosphere and light

- Latitude 32.8 N. True north as on the loop (already written back).
- **Road bearings in drive order:**

  | Road | Bearing |
  |---|---|
  | Waring | ~321° leaving J1, curving to ~236° at J2 |
  | Princess View | ~320–345° (NNW) |
  | Mission Gorge, J3→J4 | ~58° (ENE) |
  | Jackson north, J4→J5 | ~140° (SE) |

- **Sun by road:**
  - eastbound Mission Gorge drives into the morning sun, up the valley;
  - Waring, NW-bound out of J1, drives into the late-afternoon sun;
  - on the Jackson climb, the morning sun is behind-left and Cowles is ahead.
- **Presets:** as the loop ships, plus 0043's sodium night on the lit stretches.
- **The one photo that sets the mood:** not chosen yet. The candidate is Jackson Dr mid-climb at golden hour, with Cowles above the canyon rim. **Kevin's pick.**

## 8. Asset plan, owned assets first

| Need | Owned asset | Conversion notes | Placement | Or GAP |
|---|---|---|---|---|
| Road, curbs, sidewalk, paint | the loop's materials (installed v0.17.1) | none | all four roads and the pads | — |
| Planted median island | the loop's College/Navajo median set | none | Waring | — |
| Terracotta median top | none owned | CC0 concrete texture tinted red (ambientCG), 1024 px power of two | Mission Gorge | GAP: CC0 texture, no purchase |
| Sodium lamp | LIGHTPOST (0043), 4,045 points each | a decimated variant only if the road kn5 passes 145 MB | lit stretches (D4) | — |
| Signs | W1-6 arrow and speed-limit plates (`make_sign_textures`) | none | J2–J4; M3/M4 in the race files | — |
| Trees | TreeFX: Gum, SycamoreV1/V2, Oak3, Sage, Yucca, Bush, Bush3, Agave, Pine_Aleppo, PepperV1 | none | §6 zones | flowering shrubs: GAP, owned by 0040 |
| Buildings | OSM footprint extrusion (the `build_loop_blend` pass) | none | within 120 m of the new roads | — |
| Far ground | 0046's dry-chaparral key | none | far ring | — |
| Race seals at the new openings | the loop's race strips (race kn5) | none | the Speedways | — |

**Licensing:** Kevin's stance stands: releases are never gated on asset provenance. The full and CC0 packages follow `docs/PUBLISHING.md`.

## 9. Data sources and capture assets

Everything below is in the session scratchpad `expansion/`. P0 copies the files the build needs into the workshop's `data/`, with a `PROVENANCE.md` entry.

- **OSM:**
  - `routes/data/osm_expansion.json`: 27,730 elements, bbox 32.755..32.850 N, −117.115..−116.985, as of 2026-10-12T18:03:18Z, from overpass-api.de with TLS verified;
  - `routes/routes_analysis.json`, `routes/mouths.json`, `routes/legs.geojson` (node-to-node legs);
  - `terrain/data/osm_peaks.json`, `aerial/osm/pois.json`.
- **3DEP:**
  - `revise/measure.json` with `revise/dep_cache.json.gz` (node-to-node profiles, junction heights, frame offsets);
  - `terrain/out/profiles.{txt,json}` (mid-leg cross-sections);
  - `views.json` and `los_fine.json` (skyline and line of sight);
  - `budget.json` (the 0046 planner run);
  - `clamp_transects.json`, plus `revise/clamp_options.py` (the L3 re-simulation).
- **NAIP 2022-04-25:** tiles m_3211716_sw/ne, 47 windows (~300 MB) in `aerial/naip/`.
  - Eye widths in `aerial/widths_eye.csv`;
  - overlays in `aerial/overlays/01–09_*.png`;
  - vegetation in `aerial/veg_bins.json`.
- **Pipeline:**
  - `pipeline/mouth_geometry.json` and `revise/mouth_sides.py` (the openings on the loop's outer curb);
  - `pipeline/road_kn5.json` (the installed kn5 census);
  - `pipeline/map_extent.json`, `pipeline/gate_times.txt`.
- **No KML:** every new road is on the real network (L1).
- **Missing, to be captured:**
  - the Street View pass: paint, speed limits on Princess View and Jackson, Margerum's signal, the driveway count, guardrails, lamps at night, and the E1 eucalyptus;
  - newer NAIP (the USDA APFO service reset the TLS connection; retry later).

## 10. Location-specific QA (these become the §Look rows in the drive reports)

1. Driving straight from College onto Waring feels like the real Y: no step at the weld. Both Speedways are still sealed there, past v1521 included.
2. Turning right at J2 at road speed: no seam step on the pad, and the Mound Ave and Waring stubs read as real streets you can't drive into.
3. Princess View's break off the plateau doesn't launch the car, and the sag at the bottom doesn't bottom it.
4. At J3 the quarry's white terraces show to the north, and the valley floor is the lowest point you have ever driven here.
5. Mission Gorge reads as a fast divided arterial with a terracotta median, river woodland to the north and gorge walls on both sides. Cowles drops behind the south wall at s ~565 and comes back by s ~1865.
6. The crest at s ≈ 1460 runs between real cut walls, with no float.
7. Climbing Jackson, Cowles fills the windscreen at 9–10°. The ridge stands above the SW side and the canyon falls away to the NE. The tall grey-green trees on the NE side read as eucalyptus.
8. Arriving at J5 from the north: no step ≥ 6 cm (0050's box), and the turn onto Navajo works both ways.
9. At night the lit stretches glow sodium and the canyon is dark (if D4 is kept).
10. In the Speedways, the M3 and M4 arrows read right on the sealed openings.
11. Load time and frame rate are no worse than v0.18.x, by Kevin's judgement.

## 11. Build plan

- **Stages:**
  - **P0 data:** guarded OSM, the appended `north` route, the config, `heightfield.py grid_grow`, the frame pin, the cache remap, buildings.
  - **P1 readable intermediate** (`data/expansion.north.json`): the four pieces with per-station widths and medians, the J2–J4 pads, the J1/J5 welds at their measured extents, and the stubs. Then the plan map, and a weld-and-policy rehearsal.
  - **P2 terrain:** 0046's tiers over the pinned frame, the D2 far box, the D3 clamp (once Kevin says yes), and a cut-wall check.
  - **P3** road and ground → Drive 1.
  - **P4** signs, lamps, trees, buildings, map → Drive 2.
  - **P5** release.
- **Config changes** (`track.config.json`):
  - `route.bbox` to at least N 32.820 / W −117.082;
  - `route.route_connectors.routes` gains `north`;
  - `terrain.far_extent` [32.755, −117.108, 32.850, −116.998];
  - the `cowles_mountain` include's north edge to 32.828;
  - `terrain.grid_grow` {rows_n 37, rows_s 37, cols_w 26, cols_e 0}, with more north/south pairs if the planner needs them;
  - `tier_options.frame.pin`;
  - a per-road clamp of 40 m on Jackson north and Mission Gorge;
  - lamp stretches, tree zones, and per-layout sign entries (M3/M4 and the skips);
  - `race.kerbs.trims` drops at apex 1514 L and 2319 L.
- **Authored in Blender**, and never overwritten by the draft stage (REALISM §4):
  - the J2–J4 pads (`AUTH_pad_J2/J3/J4`);
  - the median islands (`AUTH_median_waring`, `AUTH_median_missiongorge`);
  - the corner stubs;
  - any cut slopes P2 finds missing.
- **Gates** (thresholds in EXPANSION-PLAN.md §Verification):
  - `verify_mouths` on the J1 and J5 openings;
  - pad coverage and seams;
  - `no_route` and `verify_race` on both Speedways, including the probe past v1521;
  - `drive_test` on the three layouts, plus `--line expansion` in both directions;
  - `audit_mesh`, `verify_kn5`, `kn5_ground_check`;
  - 0046's sightline, far-ring and facet checks at the new stations;
  - for Drive 2, `verify_signs` and the TreeFX checks.
- **First question for the drive test:** "Drive from College straight onto Waring, round the new loop, and back down Jackson to Navajo. Did any junction, the Princess View break or the J5 box catch the car?"

---
**Kevin's approval:** ☐ approved as-is · ☐ approved with the changes noted above — date: \_\_\_\_

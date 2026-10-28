# Location dossier: Exotics Racing, Las Vegas Motor Speedway (`exotics-racing-lv`)

> Researched 2026-10-28 for a separate Opus build session. **Nothing here is built.** Every factual
> row has a source tag `[Sn]` that resolves in the Sources table at the end. Where the only evidence
> was a search-engine summary of a page this session could not open, the tag reads `[Sn·snip]`.
> `[unverified]` means no source was found. `[derived]` means arithmetic on sourced figures.
> **Not one coordinate or width in this file is invented.** Where geometry is unknown, the file says
> what the build has to measure and where.
>
> **Session limits that shaped this file:** WebFetch could not reach any host (exoticsracing.com,
> wikipedia.org and others failed DNS), and the egress proxy refused Overpass, Nominatim and The
> National Map (`tnmaccess`) with HTTP 403. All evidence therefore comes from web-search results.
> No OSM query, DEM tile or image was pulled. The build session has to run those steps first (§9, §11).
>
> **Repo note:** researched in a `k10-track-agents` cloud session on 2026-10-28 and ported here the
> same day. No `track.config.json` exists yet: Kevin picks target A or B (§0) and approves before any
> geometry is made.

---

## ⚠ 0. Read first: the brief's premise is out of date

| Finding | Evidence |
|---|---|
| **The Exotics Racing track at LVMS closed on 28 Nov 2021.** The business moved to SpeedVegas and reopened there on 1 Dec 2021. | Perisset LinkedIn post [S8·snip]; merger effective 29 Nov 2021 [S6][S7] |
| The LVMS lease expired. The space was "turned over to research and development for autonomous cars and autonomous delivery company Nuro". | Las Vegas Review-Journal (RJ), 2021 [S5·snip] |
| Nuro took **74 acres of LVMS** for a closed-course proving ground. In 2021 it said the site would be operational in 2022. In July 2025 it was still testing there. | Nuro [S28]; Forbes [S29]; TechCrunch 2025 [S30] |
| **Exotics Racing today *is* at SpeedVegas** (14200 S Las Vegas Blvd, Exit 25 on I-15 near Sloan Rd). The brief asked for SpeedVegas to be disambiguated as a different track. It is a different *track*, but since Dec 2021 it is Exotics Racing's *home*. | [S3][S5·snip][S6][S9] |
| "Exotics Racing" is a registered US trademark (reg. 3891602, 2010, renewed 2021; reg. 5254267, 2017). The owner is Las Vegas Motorsports Park, LLC. | Justia/USPTO [S48·snip] |

**So there are two candidate targets. Kevin picks one before any geometry is built:**

| | **A: Exotics Racing @ LVMS, c.2015–2021 (this dossier's subject)** | **B: Exotics Racing @ SpeedVegas, 2021–present** |
|---|---|---|
| Status | Shut down. The ground is now Nuro's proving ground, and its current condition is unknown [S5·snip][S28] | Operating [S3] |
| Kind | `circuit_port` (a "shut down" facility is allowed by CLAUDE.md's kind table) | `circuit_port` |
| Length / turns | 1.2 mi, 7 turns [S1][S2·snip][S4·snip] | 1.3 mi, 10 turns [S3·snip]; 1.9 km, 11 turns, counter-clockwise [S51·snip] |
| Straight | 1,800 ft [S1][S4·snip] | 2,000 ft [S3·snip]; 600 ft shorter than the 2016 SpeedVegas straight [S5·snip] |
| Banking | Turn 2 is a "high speed banked bowl" [S1]: **11 %** [S4·snip][S20·snip] | 2016 layout had 15° [S49·snip] or 20° [S50·snip] banking; post-2021 value [unverified] |
| Elevation change | Flat desert lot [unverified; no source gives grade] | 60 ft total on the 2016 layout [S49·snip] |
| Imagery | **Historical only** (2015–2021). Current imagery may show Nuro's changes | Current imagery works |
| Risk | Higher: the vintage has to be pinned and the asphalt may be gone | Lower data risk, but a different and hillier track |

The rest of this file builds the case for **A**, as the brief asked. A short §B appendix gives B's
facts in case Kevin redirects.

---

## 1. Identity & intent

| Field | Value | Source |
|---|---|---|
| Name | Exotics Racing (EXR), Las Vegas Motor Speedway track | [S1][S2·snip] |
| Slug (proposed) | `exotics_racing_lvms` (it has to be unique fleet-wide, STANDARDS S7) | — |
| Kind / archetype | `circuit_port` / `race_circuit` (racing kerbs, engineered run-off, pit lane, floodlights). These agree under STANDARDS S6 | STANDARDS.md S6 |
| Founders | Romain Thievin (racing driver) and David Perisset (investment banker). They opened in Las Vegas in 2009 with five cars | [S11·snip][S10·snip] |
| Phase 0 (2009 to c.2011) | A tent operation that ran on the **LVMS infield road course** ("relatively tight and low-speed") | [S4·snip][S14·snip] |
| Phase 1 (by 2013) | Moved "across the street into a parking lot with tents and their own self built … course". Dream Racing then took over the old infield spot | FerrariChat 2013/2014 [S15·snip] |
| Phase 2 (2015 to 28 Nov 2021) | New 14,000 ft² Driving/Welcome Center opened **10 Mar 2015**, grand opening **4 Jun 2015**. Investment was $4.5 M in the building and $3.5 M in the track | [S16·snip][S4·snip] |
| Design credit | Thievin and Perisset designed it. "Validated by the official track designer for the IndyCar Series" (the designer is not named; this is EXR's own claim) | [S1][S12·snip] |
| Why a private track | "to allow for events to run concurrently with others held on the LVMS campus" | [S12·snip] |
| Displacement | On NASCAR and EDC weekends (2018–2019) EXR ran at Spring Mountain's 1.6-mi East Track instead. This suggests the site was inside the LVMS event footprint | [S24·snip][S25·snip] |
| Sister site (context only) | Exotics Racing LA at Auto Club Speedway, Fontana, from Mar 2014 [S13·snip]. ACS demolition began Oct 2023 [S55·snip]. The closing date of EXR LA is [unverified] | — |
| Satellite business | Vegas Superkarts launched at LVMS on 14 May 2019: a **2,100-ft, 14-turn** outdoor kart track, separate from the 1.2-mi supercar track | LVMS press release [S26·snip] |

**The drive we're chasing.** A short, flat 1.2-mile supercar course in the Mojave. It has one long
1,800-ft blast into an 11 % banked bowl. Everything else is cone-marked technical corners laid out
on a desert lot, with the 1.5-mi oval's grandstands and the northern ranges as the backdrop. A real
lap took about 56 s in a 488 GTB under instructor limits [S21·snip]. That is a dense, readable
track that Kevin can learn in five laps.

**Layouts.** One layout: the customer layout, direction [unverified] (§4). Possible later variants,
which are AC configs over the one shared kn5 (L8): the reverse direction, and a short layout
**only** if imagery shows a cut-through. The kart track is a separate surface and out of scope for v1.

### Location and disambiguation

| Place | Where | Relationship | Source |
|---|---|---|---|
| LVMS 1.5-mi tri-oval | 36°16′17″N 115°00′40″W, about **36.2714, −115.0111** | Host campus, 7000 N Las Vegas Blvd, 89115. 20° turns since 2006 | [S36·snip] |
| LVMS campus | 1,200 acres | Holds the oval, the 3/8-mi **Bullring** (1985), the ¼-mi drag strip **"The Strip"**, the **Neon Garage** (2006, infield), and the infield and outside road courses | [S36·snip][S37·snip] |
| LVMS infield road course | 1.1 mi, 9 (or 11) turns. Open infield is 780 × 375 ft | Phase 0 venue. Dream Racing's "Inside" course | [S37·snip][S53·snip] |
| LVMS outside road course | 2.4 mi, 14 turns (2.0-mi, 11-turn variant). Clockwise per lapmeta | Not the EXR track | [S38·snip] |
| Dream Racing "Outside" course | 1.2 mi, 10 turns, "in the LVMS parking lot", "elevations and bumpy corners" | A **different operator**. Whether it overlaps EXR asphalt is [unverified] | [S54·snip] |
| **EXR LVMS track (target A)** | **Exact position [unverified].** Directories give 6925 Speedway Blvd Ste C105 "across from Shelby Museum" [S62·snip] and 6949 Speedway Blvd geocoded to 36.27803, −115.01788 [S61·snip]. EXR's own structured data gave 7065 Speedway Blvd [S3·snip]. **Caution:** 6949 Speedway Blvd is also the Harsch Speedway Commerce Center II [S63·snip], so that geocode may point at a warehouse, not the track | Has to be found in 2015–2021 imagery (§11 step 1) | — |
| Nuro proving ground | 74 acres of LVMS (exact parcel [unverified]) | Took over the EXR space after the lease expired | [S5·snip][S28] |
| **SpeedVegas** | 14200 S Las Vegas Blvd, 89054, near Sloan Rd / I-15 Exit 25. About 35 km SSW of LVMS [derived from the two areas' latitudes] | **Not** at LVMS. Opened 15 Apr 2016. EXR's home since Dec 2021 | [S49·snip][S50·snip][S6] |

---

## 2. Route geometry: facts per segment

The corner numbering is EXR's own 7-turn count [S1]. The order of corners after Turn 2 is not
published anywhere that was found. **The build reads it off the imagery and the onboard videos and
writes it back here.**

| Segment | What it is | Length | Width (measured, with source) | Kerb / edge | Surface & condition | Notes / source |
|---|---|---|---|---|---|---|
| Main straight → T1? | The 1,800-ft straight | 1,800 ft = **548.6 m** [S1][S4·snip][derived] | **Unknown. Measure it** (§11) | [unverified] | Asphalt | One 2014 reviewer: "the longest straightaway is only about 1/3 of a mile" (≈536 m, which agrees) [S19·snip]. Whether the straight ends at T1 or T2 is unresolved: an AC reviewer calls **T2 "end of long straight"** [S32·snip] |
| T2 | High-speed **banked bowl, 11 %** (≈6.3° [derived]) | [unverified] | Measure | Run-off "about 450 ft" at the end of the straight [S18·snip]. Gravel trap and F1 **Tec-Pro** barriers [S17·snip] | Asphalt | "Braking too hard into the second turn" (DetailedImage driver) [S20·snip]. The AC mod's reviewer says T2 "needs more on camber" [S32·snip] |
| T3–T7 | Technical infield section | Remainder of 1,931 m − 549 m ≈ **1,382 m** [derived] | Measure | Cones mark the **braking point, apex and exit** of every corner [S19·snip]. Kerb presence [unverified] | Asphalt | EXR describes the corner types generically ("hairpins, double apex turns, fast sweepers, chicanes", "a banked turn"), but that list comes from the **later SpeedVegas marketing** [S3·snip]. Do not map it onto the LVMS track without imagery |
| Pit lane | **Covered** pit lane beside the Welcome Center, with 35 carports | [unverified] | Measure | — | Asphalt/concrete | [S16·snip] |
| Lap | 1.2 mi = **1,931 m** [S1][derived] | — | — | — | — | Older EXR page stats block: "9 turns, 2,000 ft straight, 140 mph top" [S2·snip]. **Conflicts with the 7-turn/1,800-ft figures.** Treat it as later marketing copy or a re-count [unverified]. An m3post forum post says "1.4 mi" [S14·snip]; a single forum post, discounted |

**Widths.** No published width was found anywhere. **Do not take a default.** Measure it from a
≤15 cm/px ortho (§9) at at least 8 stations (straight, T2 entry/apex/exit, each other apex, pit
entry), and record the mean and range in `track.config.json` with `_note` provenance. Use
per-vertex width if the range is greater than 1.5 m.

**Turn-count conflict (7 / 8 / 9 / 10).** 7 = LVMS-era official [S1][S4·snip]. 9 = an EXR stats
block [S2·snip]. 8 and 10 = the **SpeedVegas** track [S27·snip][S3·snip]. Stick to 7 for target A
unless the imagery shows otherwise.

---

## 3. Elevation & drainage

| Item | Value | Source |
|---|---|---|
| Site elevation | LVMS ≈ **1,950 ft = 594 m** | na-motorsports [S39·snip] |
| Terrain | NE Las Vegas Valley floor, flat Mojave bajada. Local grade **[unverified]**. Expect a gentle fall to the S/SE toward Las Vegas Wash [unverified; general valley geography] | — |
| Real superelevation | **Turn 2: 11 % banked bowl** (≈6.28°) | RJ 2015 [S4·snip]; DetailedImage [S20·snip]; LVMS "high speed banked bowl" [S1] |
| Other corners | No banking published → **none invented** (L10) | — |
| Crown / drainage | [unverified]. A purpose-built lot track in a 4-in/yr desert likely has cross-fall to the edges, but **measure it, don't assume it** | — |
| **3DEP lidar** | **USGS `NV_ClarkCounty_2018_C19`** (work unit `NV_ClarkCounty_B1_2018`): SNWA/Clark County, Merrick & Co., **5 non-contiguous AOIs, about 289 mi²** in the Las Vegas Valley. **QL2 (1 m DEM)** for SNWA; **QL1 (0.5 m)** for the Desert Conservation Program | Lidar mapping report [S40]; vendor XML incl. `SNWA_2018_DEM_TIF_QL2` [S41·snip]; QL table [S42] |
| **Coverage of LVMS** | **[unverified].** Whether one of the 5 AOIs covers the NE valley at LVMS has to be checked in the Lidar Explorer [S43] or the 1 m DEM availability viewer | — |
| Why 2018 matters | It was flown **while the EXR track was operating** (2015–2021). If it covers LVMS, its point cloud shows the circuit as built, **T2 bowl included**. A 6° bank across about 10 m is about 1.1 m of rise, which QL2 resolves easily [derived] | — |
| Later lidar | Anything flown after Nov 2021 may show Nuro's regrade. **Do not use it for the circuit surface**, only for the surrounding terrain | — |
| Fallback | 3DEP 1/3″ (10 m), then SRTM 30 m. Too coarse to capture the bowl, so T2 then goes in as a researched `grading.overrides[]` entry (§11) | elevation skill |

---

## 4. Corner-by-corner character

**Direction of travel: [unverified].** Settle it first from an LVMS-era onboard
([S21] 488 GTB, best lap 55.97 s; [S22]; [S23] 2015 promo) by timing the 1,800-ft straight and
the side the bowl falls away on. Cross-check against the imagery (which side the gravel trap
and Tec-Pro barriers sit on at the end of the straight).

| # | What defines it | Kerbs / edges | Hazard the drive test must confirm | Reference |
|---|---|---|---|---|
| Straight | 549 m [derived]. Welcome Center and covered pit lane alongside [S16·snip] | Cones at the braking point [S19·snip] | Top speed about 130–140 mph in the fleet cars ("140 mph top" [S2·snip]) | [S21][S22] |
| T1 / T2 | **11 % banked bowl** after the straight [S4·snip][S32·snip]. About 450 ft of run-off, gravel trap, Tec-Pro barriers [S17·snip][S18·snip] | [unverified] | The bank sign has to lean **into** the turn, and the ramp in and out must not kick | [S20·snip] |
| T3–T7 | Technical section of cone-marked apexes [S19·snip] | [unverified] | That narrow sections don't fall below the measured width | [S21][S22] |
| Final corner → straight | [unverified] | [unverified] | That exit traction onto the straight is clean | — |

**Do not borrow corner descriptions from SpeedVegas.** The Love of Driving 2023 account
("a long turn, possibly turn 3, that tightens…", S-curves, a final hairpin) [S52·snip] is a
**SpeedVegas** review. A 2013 FerrariChat note about a "9-turn infield course with a zig-zag last
three" [S15·snip] describes the **LVMS infield road course** (Phase 0 / Dream Racing), not
target A.

---

## 5. Built environment & landmarks

| Element | Detail | Source |
|---|---|---|
| EXR Welcome / Driving Center | 14,000 ft², opened 2015. Covered pit lane, viewing terrace, meeting rooms, café, **35 carports**, video/light/sound systems | [S16·snip][S4·snip] |
| Early facility | Tents (2009–c.2013) | [S4·snip][S15·snip] |
| Safety furniture | "More than $1 million in safety": **F1 Tec-Pro barriers**, **gravel trap** | RJ photo caption [S17·snip] |
| Corner furniture | **Traffic cones** at the braking point, apex and exit of every corner. These are a defining visual of the EXR experience | [S19·snip] |
| Fencing, light poles, signage | [unverified]. Read them off the imagery and onboards. No floodlights are mentioned anywhere; daytime-only operation is likely [unverified] | — |
| LVMS backdrop | The 1.5-mi oval's grandstands (they dominate any horizon facing the oval), the Neon Garage (infield, 2006), the Bullring, the drag strip "The Strip" | [S36·snip] |
| Mountains | The **Sheep Range** and **Las Vegas Range** form the valley's north edge. The **Spring Mountains** (Mt Charleston, 11,916 ft) rise far to the W | RJ mountains guide [S59·snip] |
| Strip skyline | About 13–15 mi to the **SW** [derived from coordinates; S59·snip context] | — |
| Kart track | 2,100 ft, 14 turns (2019), beside the supercar operation [S26·snip]. Exact position [unverified] | — |

Furniture stands on true ground. The road comes down to the data, never the furniture up
(0029 §5).

---

## 6. Vegetation & terrain palette

| Item | Detail | Source |
|---|---|---|
| Plant community | Mojave **creosote bush (*Larrea tridentata*) – white bursage (*Ambrosia dumosa*)** scrub. It dominates broad flats below 4,000 ft | [S58·snip] |
| Soil | A calcic horizon (caliche) shallow to the surface, with gravel/cobble surface lag | USDA ESD R030XB005NV [S58·snip] |
| Density near the track | Sparse to none. The track sat in graded LVMS lots (a "parking lot" [S15·snip]), so expect bare compacted caliche and asphalt lots, with native scrub only beyond the campus edge [unverified; confirm in imagery] | — |
| No | Lawns, trees on the infield, GrassFX green. A **tan/ochre desert ground** shader replaces grass | — |

---

## 7. Atmosphere & light

| Item | Detail | Source |
|---|---|---|
| Latitude | 36.27°N [S36·snip]. Summer solar noon elevation about 77°, winter about 30° [derived: 90 − 36.3 ± 23.4] | — |
| Sun | About **85 %** of possible sunshine annually (77 % Jan → 93 % Jun). About 210 clear days a year | [S57·snip] |
| Heat | July mean highs about 104–106 °F (heat shimmer, washed-out midday sky) | [S57·snip] |
| Presets worth shipping | **Spring morning** (low E sun, long shadows across the lot, a crisp Sheep Range); **high-summer midday** (the true EXR customer condition: flat light, pale sky); **golden hour** (sun setting over the Spring Mountains to the W, grandstands lit) | — |
| True north | Derive it with `lighting` from the georeferenced trace; write it back to config | lighting skill |
| Mood photo | [unverified]. Pick a frame from [S23] (2015 promo) or [S21] | — |

---

## 8. Asset plan: owned assets first

| Need (§5–§6) | Owned asset (Dropbox `/Blender`, ASSET-LIBRARY.md) | Conversion notes | Placement | Or GAP → candidate purchase |
|---|---|---|---|---|
| Tec-Pro barrier modules | `Barrier02.obj`, `Barrier_end01/02.obj`, `Barrier_circle.obj` (generic) | Metres, Y-up; retexture to Tec-Pro red/white or blue/white; ≤2K | Outside T2 and any other barrier line seen in imagery | **GAP**: a Tec-Pro-specific model |
| Concrete wall / jersey | `Concrete Barrier 4 MTS + Transition` | As the library notes | Pit wall / paddock edge if the imagery shows one | — |
| Traffic cones | none | — | Brake/apex/exit markers (an `AUTH_` cone set, non-collidable, or a 1WALL-free prop) | **GAP**: a simple cone, trivially authored in Blender |
| Welcome Center + covered pit + 35 carports | `ModularBuildings.blend1`, `building_1.blend` | Re-save the .blend1 first; massing to the imagery footprint | `AUTH_` massing | — |
| Oval grandstands (backdrop) | `Racetrack_1.blend` (617 MB kitbash) | Kitbash only; decimate | Far backdrop toward the oval | — |
| Chain-link fence | `Fence.FBX` / procedural `make_chainlink` | — | Campus perimeter per imagery | — |
| Light poles | `Street_Lamp.zip` | Only if the imagery shows lot lighting | — | — |
| Creosote / bursage shrubs | none (poplar and pine only) | — | Campus edge only | **GAP**: low desert shrub cards, CC0 |
| Desert ground / caliche | `grass_path_2` (wrong biome) | — | — | **GAP**: a CC0 dry-dirt/caliche PBR set (Poly Haven class) |
| Sky | `bloem_hill_02_4k.exr` (wrong biome) | EXR → PNG; CSP/Sol drives the sky | — | Sol default sky is fine |

No mined mod content ships (REALISM §3). The Pellefred mod (§9) is a **reference only**.

---

## 9. Data sources & capture assets

| Source | What it gives | Status / vintage | Source |
|---|---|---|---|
| **OSM** | Whether `highway=raceway` ways exist for the EXR track | **Not checked.** Overpass was blocked this session; no web result mentions an OSM way. Run: `[out:json];(way(around:1500,36.2714,-115.0111)[highway=raceway];way(around:1500,36.2714,-115.0111)[leisure=track];);out geom;` | — |
| Clark County "most current flight" | Cached ArcGIS MapServer, NAD83 StatePlane NV East (ft). **Current imagery shows Nuro-era ground, not the circuit** | Resolution [unverified] | [S44] |
| **Clark County historical aerials** | **2015–2020 flights sold by section, $20 a section (4th free)**. These cover the track's whole life and are the best candidate truth source | Resolution [unverified]; GISMO office | [S45·snip] |
| NAIP Nevada | 2019 NV NAIP 4-band exists. The national standard has been 0.6 m with a 0.3 m option since 2018. NV-specific GSD per year [unverified]. Public domain | — | [S46][S47·snip] |
| Google Earth Pro historical | Multiple 2015–2021 dates likely for the Las Vegas metro [unverified]. **Screenshot it for tracing only; it is not license-clean to ship** | — | — |
| ESRI / Bing tiles | Current only. Post-2021, so likely Nuro-era | [unverified] | — |
| **3DEP lidar 2018** | QL2 1 m DEM + classified LAS (QL1 in the DCP areas) | Coverage at LVMS [unverified] | [S40][S41·snip][S43] |
| Street View / Mapillary | Speedway Blvd coverage likely, campus interior unlikely [unverified]. Not checked | — | — |
| Site plan / CAD | None found. The track was designed by Thievin and Perisset [S1] | — | — |
| Onboard video | 488 GTB, best lap 55.97 s (instructor-limited) [S21]; "EXR LV Track at LVMS" [S22]; 2015 promo [S23] | YouTube (not opened this session) | — |
| GPS lap data | None found in RaceChrono / Harry's / TrackAddict / VBOX. lapmeta entries are SpeedVegas-era [S51·snip]. EXR's own LVMS-era timing archive exists but was not reached | [S2·snip] context | — |
| **Existing AC mod** | **"Exotics Racing Track Las Vegas" v1.0 by Pellefred**, 19 Mar 2019, 100.7 MB, 2,420 downloads. Rated 2.5★ from 8 ratings (RaceDepartment). Reviews: "turns… spot on" vs "wrong track map / length off", "surface and edges/curbs don't line up", "T2 needs more camber, bumps too sharp" | Reference only, no provenance claim | [S31·snip][S32·snip][S33·snip] |
| Scale-reference AC mods | "lvms dream racing inside road" (overtake.gg 77575); VB Assetto **"LVMS Outside Road Course" v0.91** (Patreon, paid; drift / CW / CCW / Dream Racing CCW layouts) | Reference only | [S34·snip][S35·snip] |
| iRacing / rFactor | LVMS oval + road courses exist in iRacing [S36·snip context]. No EXR track found | — | — |

---

## 10. Location-specific QA (these become the drive-test §Look rows)

1. **Lap length** of the built centerline = 1,931 m ± 3 %, and the straight = 549 m ± 3 % [S1].
   Either one outside tolerance means the georeference is wrong. Stop.
2. **T2 leans into the turn at about 6.3°** (11 %), ramped, with no step at the bank transition
   (`drive_test` severe-step count = 0 in T2).
3. **The AC 488 GTB lap is at or under about 56 s.** The real lap was 55.97 s *with instructors
   holding drivers back* [S21·snip]. A lap well over that means width, length or a corner radius
   is wrong.
4. **Cones read as EXR**: brake/apex/exit triplets at every corner [S19·snip], non-collidable or soft.
5. **The horizon reads as LVMS**: oval grandstands in the right bearing, the northern ranges
   behind, the Strip skyline faint to the SW.
6. **Ground reads Mojave**: no green anywhere, caliche tan, a few creosote clumps only at the
   campus edge.
7. **Surface is smooth.** A freshly laid private lot track (2015, $3.5 M [S4·snip]) should not
   repeat the Pellefred mod's "bumps too sharp" [S32·snip]. bumps/km should be well under the 75
   tarmac line (GATES-CHANGELOG notes that line is self-referential).

---

## 11. Build plan — through the Lake Murray chain

> **Rewritten 2026-10-28 (Kevin: "build these the same way that we build Lake Murray 0.19.1").** The first
> version of this section prescribed the engine-era pipeline (`aerial-tracing` → `elevation` → `track-grading`
> → mesh → gates → kn5); v0.1.0 was built that way on 2026-10-28 and retired the same evening. What that build
> established stays (the "Answered 2026-10-28" block above: target A, the 2019 NAIP trace, the lidar T2 bank,
> dressing as in 2013). The track builds through the ship chain: `tools/ship_track.sh exotics-racing-lv`, steps
> in [`ship.json`](ship.json).

1. **Draft (the engine, as a draft only).** `aerial` (`scripts.aerial.build_aerial` on `source/naip_2019_exr.png`
   with the two control points and the refined `trace_px`, measured widths per point) → `elev` (3DEP 1 m) →
   `project` → `mesh` (`data/track.obj`: the ribbon with the −6.0° T2 bank from `road_profile`, kerbs, the
   natural-ground verge, ground) → **`underlay`** (`scripts/blender/underlay.py`: the OBJ into `loop.blend` as
   `GEN_road` / `GEN_kerb` / `GEN_wall` / `GEN_terrain` / `GEN_misc`, plus `GEN_refs`).
2. **Author in Blender (`AUTH_*`, never regenerated).** First pass: nothing — the draft ships so the seat can
   judge the bowl. Then, from Kevin's calls: the 2013 dressing (the two small south-west buildings, no Welcome
   Center, no covered pit, no carports), the Mojave ground in place of the default grass, the Tec-Pro line and
   gravel trap at the end of the straight, cones as the imagery shows them, the LVMS grandstands as low far
   geometry. Satellite imagery as the road's macro texture (§12, `fleet/reference/SATELLITE-ROAD-TEXTURES.md`)
   is an authoring-stage texture on the road object, never a mesh step.
3. **Prep → split → export** from airoso's `scripts/ac`. One layout, `full`, clockwise; the AI line is the
   writer's draft until recorded in game. Installed name "K10 Las Vegas - Exotics Racing Las Vegas (unofficial)";
   the public name is Kevin's call at publish time (the mark is registered).
4. **Gates on the built kn5:** `drive_test` → `audit_mesh` → `kn5_ground_check`, thresholds unchanged
   (GATES-CHANGELOG). Watch item: the T2 bank ramps against drive_test's step and kink checks — the first build
   passed them (soft top 0, severe 0, kinks 0.55/km).
5. **Install** as `content/tracks/exotics_racing_lvms`; the previous build is parked in the archive.
6. **First question for the drive test** stands: *"Braking from the end of the straight into the bowl: does T2
   hold the car at bowl speed and lean the right way, and does a 488 GTB lap come in at or under 56 s?"* The
   first build's sign error (T2 off-camber until the mirror was accounted for) is exactly what the seat, not the
   gates, would have caught.

---

## 12. Satellite imagery as road texture: what it could bring *here*

(Input for the sibling technique study.)

| Factor | This site | Implication |
|---|---|---|
| Flat, sunny, dry | 594 m desert floor [S39·snip], about 85 % sunshine [S57·snip] | Ortho tiles are rarely cloud-obscured; colour is consistent between flights |
| **Vintage constraint** | The track existed only from 2015 to Nov 2021 [S16·snip][S8·snip]; afterwards it was Nuro ground [S5·snip] | **Only 2015–2021 imagery is usable as texture.** Current tiles may show regraded or repainted ground. This is the strongest site-specific constraint |
| Resolution available | Clark County historical flights, GSD [unverified] (county programmes are often ≤15 cm, but the figure was **not found**); NAIP ≥ 0.6 m / 0.3 m option [S47·snip] | At 0.6 m a ~10–12 m road is under 20 px across. Usable for **run-off, lot asphalt and caliche ground albedo**, not for the 1ROAD diffuse. The Clark County flights are the only candidate for the driving surface, and only if their GSD is ≤ 7.5–10 cm |
| Baked content | Cones, rubber lines, Tec-Pro shadows, parked cars in the 35 carports, lot paint | Rubber lines are **real racing-line evidence** (AI-line cross-check) and authentic texture. Cones and car shadows must be cloned out. High summer sun gives short shadows, but winter flights give long pole shadows |
| Geometric fit | The ortho is the trace source too | The texture registers perfectly to the traced mesh by construction (same georeference) |
| Licensing | NAIP is public domain [S47·snip]. Clark County terms [unverified]. Google/ESRI/Bing are **not** shippable | Ship only with NAIP or confirmed-clean county imagery; Google stays private and tracing-only (REALISM §3) |
| Best use here | (1) the draped `GEN_` underlay for authorship; (2) the off-track ground and lot ring texture (huge flat areas, where most of the "LVMS feel" lives); (3) the near-road surface only with ≤10 cm county imagery, blended with a tiling asphalt detail map | — |

---

## Appendix B: target B (Exotics Racing @ SpeedVegas), if Kevin redirects

| Fact | Value | Source |
|---|---|---|
| Address | 14200 S Las Vegas Blvd, NV 89054. Exit 25 I-15, near Sloan Rd | [S50·snip][S6] |
| Opened (as SpeedVegas) | 15 Apr 2016: 1.5 mi, 12 turns, half-mile straight, **60 ft elevation change**, 15° (or 20°) banking | [S49·snip][S50·snip] |
| 2021 rework | Merger on 29 Nov 2021; "newly redesigned and renovated" track on a 100-acre site; 600 ft cut from the straight (top speed about 130 vs 160 mph); gravel traps, F1 barriers, asphalt run-off | [S6][S5·snip][S9·snip] |
| Current spec | 1.3 mi, 10 turns, 2,000-ft straight [S3·snip]. lapmeta: 1.9 km, 11 turns, **CCW**, fastest 50.760 s (Ferrari 296 Challenge, 2024) [S51·snip] | — |
| Character | "Long turn, possibly T3, tightens… super late apex", back-to-back S-curves, final hairpin | [S52·snip] |
| Grading | A real 15–20° bank on the 2016 layout. The post-2021 value has to be re-researched (L10) | — |
| Imagery | Current tiles are valid (extant facility) | — |
| AC mod | None found | [search, this session] |

---

## Open items for Kevin

1. **A or B?** (§0). A is the brief's track but needs vintage imagery. B is the live Exotics Racing.
2. Naming: "Exotics Racing" is a registered mark of Las Vegas Motorsports Park, LLC [S48·snip].
   For a private build, any name works. For anything shared, consider a descriptive name
   ("LVMS Supercar Circuit 2015–21") and no EXR logos.
3. OK to spend about $20–40 on Clark County historical sections [S45·snip]?

**Answered 2026-10-28 (build session):**
- **Target A.** Kevin drove this track in 2013. Free USDA NAIP covered it, so no county imagery
  was bought. 2019-07-06 at 0.6 m was the trace source, and 2013-09-28 at 1 m was the
  cross-check.
- **Location (§1, was [unverified]):** the circuit sits in the LVMS lots between I-15 and Speedway
  Blvd, north-west of the drag strip. The lap centroid is 36.28245, −115.01823. The Welcome
  Center is at 36.28087, −115.02109, on the circuit's south-west corner.
- **Phase 1 vs Phase 2 (§1):** by September 2013 the circuit was already a real paved track, with
  painted edges, kerbs and the same lap as 2019. The 2015 work added the Welcome Center and the
  covered pit, not a new layout. "Parking lot with tents" described the 2013 buildings.
- **Dressing: as in 2013** (Kevin: "As in 2013"). The two smaller 2013 buildings on the
  south-west corner, with no Welcome Center, no covered pit and no carports.
- **Geometry (§2/§3):** the lap is 1,825 m (published 1.2 mi, −5.3 %). The straight is about
  470 m. Width runs 11.6 m on the straight and 15–19.5 m at corner exits. T2 is the NE corner,
  a 129 m arc of 62 m radius. Its 11 % bank is confirmed by 3DEP lidar (+10.0 to +10.9 % across
  ±5 m, against about +2 % elsewhere). The direction is clockwise (inferred). All of it is in
  `source/trace/README.md` and `track.config.json`.
- **Name:** "Exotics Racing Las Vegas (unofficial)" for now. Naming for a public release is
  Kevin's call at publish time.

---

## Sources

`·snip` = the claim rests on a search-engine summary of the page, because the page could not be
opened in this session. Re-verify before quoting.

| # | URL | Used for |
|---|---|---|
| S1 | https://www.lvms.com/tracks/exotics/ | 1.2 mi, 7 turns, 1,800-ft straight, banked bowl, IndyCar-designer validation |
| S2 | https://exoticsracing.com/track/track/view/id/1/ | Older EXR page: T2 banked bowl; stats block 9 turns / 2,000 ft / 140 mph |
| S3 | https://exoticsracing.com/racetrack/ | Current EXR: 1.3 mi, 10 turns, 2,000 ft, on Las Vegas Blvd; 7065 Speedway Blvd in structured data |
| S4 | https://www.reviewjournal.com/business/youll-be-able-to-race-exotic-cars-at-the-speedway-soon-photos/ | 2015: 14,000 ft² centre, 4 Jun grand opening, $4.5 M/$3.5 M, 1,800 ft, 7 turns, 11 % bowl, tent start |
| S5 | https://www.reviewjournal.com/business/speedvegas-critic-now-ceo-of-high-speed-operation-2498986/ | Lease expired → Nuro; move to SpeedVegas; 600 ft cut, gravel traps, F1 barriers |
| S6 | https://exoticsracing.com/news/exotics-racing-and-speed-vegas-join-forces.html | Merger 29 Nov 2021; 100 acres; redesigned track; Exit 25 |
| S7 | https://vegasnews.com/213220/exotics-racing-speedvegas-join-forces-to-become-speedvegas-motorsports-park-nov-29.html | Merger release republished 17 Nov 2021 |
| S8 | https://www.linkedin.com/posts/davidperisset_after-12-years-at-exotics-racing-in-las-vegas-activity-7029709044743376896-Y_SJ | Speedway location closed 28 Nov; new site opened 1 Dec |
| S9 | https://en.wikipedia.org/wiki/Speed_Vegas | Merger 2021; Thievin CEO; post-merger safety upgrades |
| S10 | https://en.wikipedia.org/wiki/Romain_Thievin | EXR based at LVMS since 2009 |
| S11 | https://exoticsracing.com/about-us/ | Founders; 2009, five vehicles |
| S12 | https://www.thespeedjournal.com/exotics-racing-las-vegas/ | Own 1.2-mi course, to run concurrently with LVMS events |
| S13 | https://news.dupontregistry.com/blogs/sponsored/exotics-racing-experience-track | "Built our own track on an existing speedway"; LA from Mar 2014 |
| S14 | https://www.m3post.com/forums/showthread.php?t=670767 | Originally the LVMS infield; own circuit "next door" ("1.4 mi") |
| S15 | https://www.ferrarichat.com/forum/threads/exotics-racing-in-vegas.419202/page-2 | 2013 "across the street… parking lot… self built"; Dream Racing in the old spot |
| S16 | https://exoticsracing.com/es/news/.html | 10 Mar 2015 driving centre; covered pit lane, terrace, café, 35 carports |
| S17 | https://www.reviewjournal.com/business/tourism/questions-surround-recently-acquired-lamborghini-in-deadly-speedvegas-crash/attachment/exotics-racing-has-invested-more-than-1-million-in-safety-at-its-track-at-the-las-vegas-motor-speedway-formula-one-tec-pro-barriers-and-a-gravel-trap-are-designed-to-minimize-damage-from-a-car-c/ | Over $1 M of safety work; Tec-Pro; gravel trap at the LVMS track |
| S18 | https://www.reviewjournal.com/local/local-las-vegas/multiple-factors-contributed-to-fatal-speedvegas-crash-experts-say/ | About 1,800-ft straight, about 450 ft of run-off |
| S19 | https://95octane.com/2014/03/19/exotics-racing-las-vegas-review/ | Cones at brake/apex/exit; longest straight about 1/3 mi |
| S20 | https://www.detailedimage.com/Ask-a-Pro/racing-at-the-las-vegas-motor-speedway-with-exotics-racing-part-2/ | T2 11 %; braking into the 2nd turn |
| S21 | https://www.youtube.com/watch?v=AOQw32bCOCo | 488 GTB onboard, best lap 55.97 s |
| S22 | https://www.youtube.com/watch?v=4KqxVGItGNM | EXR Las Vegas track at LVMS video |
| S23 | https://www.youtube.com/watch?v=39kryJaY4lk | 2015 EXR promo |
| S24 | https://speedvegas.com/news/new-track-spring-mountain-motorsports/ | 2018 NASCAR/EDC weekends moved to the SMMR East Track |
| S25 | https://www.thevoxagency.com/exotics-racing-announces-it-will-operate-from-spring-mountain-motor-resort-and-country-club-on-sept-14/ | Same pattern, 2019 |
| S26 | https://www.lvms.com/documents/news-release---vegas-superkarts-announcement.pdf | 14 May 2019 kart track, 2,100 ft, 14 turns; separate 1.2-mi track |
| S27 | https://www.fortloc.com/pages/articles/experiencesgen2/Exotics-Racing-Las-Vegas/ | Move from LVMS to SpeedVegas; SpeedVegas 8 turns |
| S28 | https://medium.com/nuro/introducing-our-new-manufacturing-facility-and-test-track-bbee738d0ec8 | Nuro 74 acres of LVMS |
| S29 | https://www.forbes.com/sites/alanohnsman/2021/08/26/nuro-building-las-vegas-factory-test-track-for-electric-delivery-robots/ | Nuro LV test track, 2021 |
| S30 | https://techcrunch.com/2025/07/17/uber-makes-multi-million-dollar-investment-in-lucid-nuro-to-build-robotaxi-service/ | Closed-track testing at Nuro's LV proving grounds, 2025 |
| S31 | https://www.overtake.gg/downloads/exotics-racing-track-las-vegas.25939/ | Pellefred AC mod v1.0, 2019 |
| S32 | https://www.overtake.gg/downloads/exotics-racing-track-las-vegas.25939/reviews | Mod reviews (T2 camber, bumps, map/length) |
| S33 | https://www.racedepartment.com/downloads/exotics-racing-track-las-vegas.25939/ | 2.5★ from 8 ratings |
| S34 | https://www.overtake.gg/downloads/lvms-dream-racing-inside-road.77575/ | LVMS Dream Racing inside road AC mod |
| S35 | https://www.patreon.com/vb_assetto/posts/lvms-outside-v0-150977052 | VB Assetto LVMS Outside v0.91 |
| S36 | https://en.wikipedia.org/wiki/Las_Vegas_Motor_Speedway | Coordinates, oval, Bullring, drag strip, Neon Garage, 1,200 acres |
| S37 | https://www.lvms.com/tracks/road-courses/ | Infield 1.1 mi; infield 780 × 375 ft (track-rentals page) |
| S38 | https://lapmeta.com/en/track/variation/247 | LVMS 2.4-mi outside road course |
| S39 | https://na-motorsports.com/Tracks/NV/LasVegasMS.html | LVMS elevation 1,950 ft |
| S40 | https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/metadata/NV_ClarkCounty_2018_C19/NV_ClarkCounty_B1_2018/reports/2018_Clark_County_Lidar_mapping_report.pdf | 2018 Clark County lidar: SNWA, 289 mi², 5 AOIs, QL2/QL1 |
| S41 | https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/metadata/NV_ClarkCounty_2018_C19/NV_ClarkCounty_B1_2018/reports/vendor_provided_xml/ | SNWA_2018_DEM_TIF_QL2 etc. |
| S42 | https://www.usgs.gov/3d-elevation-program/topographic-data-quality-levels-qls | QL2 = 1 m DEM, QL1 = 0.5 m |
| S43 | https://apps.nationalmap.gov/lidar-explorer/ | Coverage check |
| S44 | https://maps.clarkcountynv.gov/arcgis_images/rest/services/CACHED/mostcurrentflight/MapServer/info/iteminfo | County current-imagery service, SP NV East ft |
| S45 | https://www.clarkcountynv.gov/government/departments/geographic_info_systems/services/data-and-products | Historical imagery 2015–2020, $20 a section |
| S46 | https://www.fisheries.noaa.gov/inport/item/68146/printable-form | 2019 Nevada NAIP 4-band |
| S47 | https://en.wikipedia.org/wiki/National_Agriculture_Imagery_Program | NAIP 0.6 m standard / 0.3 m option since 2018; public domain |
| S48 | https://trademarks.justia.com/870/96/exotics-87096242.html (also …/850/30/exotics-85030748.html) | EXOTICS RACING marks; owner Las Vegas Motorsports Park, LLC |
| S49 | https://www.tomorrowstechnician.com/speedvegas-track-to-open-on-april-15/ | SpeedVegas 2016: 1.5 mi, 12 turns, 60 ft, 15° |
| S50 | https://www.prnewswire.com/news-releases/this-friday-speedvegas-track-to-open-to-the-public-with-special-opening-festivities-300250668.html | 20° banking; 14200 S Las Vegas Blvd |
| S51 | https://lapmeta.com/en/track/variation/408 | SpeedVegas exotic track 1.9 km, 11 turns, CCW, 50.760 s |
| S52 | https://www.loveofdriving.com/2023/04/speedvegas-part-1-exotics-racing.html | SpeedVegas corner character (not LVMS) |
| S53 | https://dreamracing.com/tracks | Dream Racing inside course 1.2 mi, 9 turns |
| S54 | https://www.fortloc.com/pages/articles/experiencesgen2/DreamRacing/ | Dream Racing outside course, parking lot, 10 turns |
| S55 | https://en.wikipedia.org/wiki/Auto_Club_Speedway | ACS demolition from Oct 2023 |
| S57 | https://www.currentresults.com/Weather/Nevada/Places/las-vegas-weather-averages.php | About 85 % sunshine; July highs |
| S58 | https://birdandhike.com/Veg/HabType/Creo-Bur/_Creo-Bur.htm ; https://edit.sc.egov.usda.gov/services/descriptions/esd/030X/R030XB005NV.pdf | Creosote–bursage; calcic soils |
| S59 | https://neon.reviewjournal.com/?p=3312455 | Sheep and Las Vegas Ranges on the north edge; Spring Mountains |
| S61 | https://www.merchantcircle.com/exotics-racing2-las-vegas-nv | 6949 Speedway Blvd, 36.27803, −115.017881 (directory geocode) |
| S62 | https://maps.roadtrippers.com/us/las-vegas-nv/sports/exotics-racing | 6925 Speedway Blvd Ste C105, across from the Shelby Museum |
| S63 | https://property.jll.com/listings/harsch-speedway-commerce-center-ii-6949-speedway-blvd-las-vegas | 6949 Speedway Blvd = a commerce centre (geocode caution) |

---
**Kevin's approval:** ☐ approved as-is · ☐ approved with the changes noted above. Target: ☐ A (LVMS 2015–21) · ☐ B (SpeedVegas). Date: \_\_\_\_

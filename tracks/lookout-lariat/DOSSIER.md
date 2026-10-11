# Location dossier — Lookout Mountain Lariat (`lookout-lariat`)

> **Filled 2026-10-11 from read-only research, and revised twice the same day after review.
> Nothing has been built.**
> - **Approval.** Kevin approves this before any geometry is made (template rule).
> - **The build plan** is [`V3-PLAN.md`](V3-PLAN.md), beside this file. It opens with the decisions
>   for Kevin: **D0–D7**, each with a default, plus the defaults it applies unless he objects
>   (**A1–A13**). This file cites them as *(D#)* / *(A#)*.
> - **Ledger:** [0048](../../fleet/feedback/0048-lookout-lariat-rebuild-v3-style-no-extra-highways.md).
>
> **How to read the numbers.**
> - **Stations.** "st 2,600" means 2,600 metres along the lap from the stone pylons, driving the
>   Full direction.
> - **Heights** are metres above sea level unless marked "local y". Local y is the track's own
>   frame, where 0 m = 1,782.7 m above sea level, the lap's lowest point.
> - **Unknowns.** "Unknown — verify via X" is a real answer here; nothing below was filled in by
>   guessing. Values measured today on the recovered July data are marked as such.

---

## 1. Identity & intent

- **Kind `street_port`, archetype `real_road`.** The two agree (STANDARDS S6).
  - These are real public roads as they exist: no invented roads (L1) and no invented banking
    (L10).
  - The installed ui tags say `fictional`; that tag goes.
- **The drive we are chasing.**
  - The 1913 Lariat Trail climbs the east face of Lookout Mountain in stacked hairpins, with Golden
    and the plains falling away below the stone guardrails.
  - Then it crosses the pine-covered top past Buffalo Bill's grave, runs fast down Mt Vernon
    Canyon, and comes home through Golden to the 1917 stone pylons.
  - It is a historic scenic road first and a fast road second. The climb is a 20 mph road with a
    double yellow line, and it should look like one.
- **Layouts: four by default, sharing one road model** (`kn5`, AC's track model file) *(D3)*:
  1. **Street — Full** (up the Lariat, anticlockwise).
  2. **Street — Reverse.**
  3. **Race — anticlockwise** *(D3 a)*.
  4. **Race — clockwise** *(D3 a)*.

  Under *(D3 b)* only the two street layouts are built. How they fit together:
  - Each layout gets its own tiny start-position file (ledger 0047).
  - The race layouts add one shared race-furniture file, with closures and boxes (§4c).
  - There is no gravel/tarmac fork, so L8's two-track exception does not apply.
- **Kevin's race brief (2026-10-11),** written for Lake Murray and the Lariat together:
  - *"racetrack versions of these, we need full intersections available for turning. And the
    entire other lane blocked off from access."*
  - *"We want more or less an Alvarado's width for the entire track with deviances in various
    areas"*
  - open boxes at the *"Corners the race turns at"*.

  On this road the deviance is most of the lap. Only Golden's streets come near Alvarado's width
  (§4c), and no layout can widen the shared road (L8). So whether the Lariat gets a race version at
  all is Kevin's call *(D3)*; if he keeps it, §4c applies the brief segment by segment.
- **What this lap is not.** It is not the official Lariat Loop Scenic Byway, a loop of about 40
  miles that leaves the mountain westward toward Genesee and Evergreen. This lap comes off the top
  via Paradise Rd and Mt Vernon Canyon and rejoins the byway at I-70 exit 259. The in-game
  description should say "a lap built on the Lariat Trail", not "the Lariat Loop".
- **Facts the in-game text must get right.** The old route notes got these wrong.
  - Length: 24.94 km (15.5 mi), not "~13 mi".
  - Buffalo Bill lot: about 2,228 m (7,310 ft). The lap's high point is 2,288 m (7,507 ft), on the
    back side.
  - Relief: 505 m.
  - Direction: Full runs **anticlockwise** seen from above. Both installed ui files say
    "clockwise".
  - Drop the Nordschleife comparisons and the unsourced claim that these are "the most photographed
    corners in Colorado".

## 2. Route geometry — facts, per segment

### 2a. The lap, in driving order (Full)

The lap was re-derived today two ways, and they agree exactly:
- the recovered July centreline: 8,319 points, 24,941.8 m;
- a fresh run of the engine's own centreline step on a 2026-10-11 Overpass snapshot of the config's
  query: 24.94 km, closed, 8,319 points.

| # | st (m) | Road | OSM class | Length | Lanes / width (source) | Kerb / sidewalk | Notes |
|---|---|---|---|---|---|---|---|
| 1a | 0–1,070 | Lookout Mountain Rd, inside Golden (Beverly Heights) | tertiary | 1.07 km | 2 lanes; **width not measured** (aerial owed) | none mapped; sidewalk unknown | 20 mph; 3 speed humps at st ~134 / 391 / 595 (15 mph plaque each; left out of the first build, A10); homes and private stone walls on the east side |
| 1b | 1,070–7,100 | **The Lariat Trail** (National Register district) | tertiary (CR 68) | 6.03 km | 2 lanes averaging 3.35 m (11 ft), so ~6.7 m paved. As narrow as **6.1 m** (20 ft, the 1913 design width). Lanes narrow to **2.74 m** (9 ft) at the Tiers of Zion switchbacks, about st 2,500–3,100. (Jeffco/FHU 2025, NRHP) | **none**; no paved shoulder anywhere; OSM `sidewalk:both=no` | double yellow the whole way, 20 mph. Uphill side: rock cut at the pavement edge. Downhill side: fill, cliff or 2:1 slope. Night gates at st ~1,074 and ~7,680 |
| 1c | 7,100–7,700 | Summit: Buffalo Bill lot, Lookout Mountain Park | tertiary | 0.60 km | 2 lanes; not measured | none | 35 mph sign at st ~7,569 |
| 1d | 7,700–9,710 | Lookout Mountain Rd, back side | tertiary | 2.01 km | 2 lanes, 35 mph; not measured | none mapped | houses among pines, driveways, ~10 residential side streets (§4b); lap high point 2,288 m at st ~9,150 |
| 2 | 9,710–11,652 | Paradise Rd | residential | 1.94 km | no OSM lane or width tags; **measure** | unknown | ends at stop signs on US-40 beside the RTD Paradise Hills Park-n-Ride (exit 256) |
| 3 | 11,652–16,546 | US-40 down Mt Vernon Canyon (unnamed in OSM) | secondary | 4.89 km | `lanes=3`; the split is unclear (one 300 m piece is tagged 2 eastbound + 1 westbound), **verify on the aerial**. Shoulders were widened in CDOT's 2021 resurfacing; widths unpublished | none | 50 mph (35 near exit 259). I-70 runs 20–50 m beside it for ~75 % of the leg (median 30 m) |
| 4 | 16,546–18,344 | I-70 Business / US-40 ("Lariat Loop Scenic Byway") | primary | 1.80 km | 3–5 lanes, divided in places | urban, to measure | from the exit-259 signals past Heritage Square. **Route defect at exit 259 (§2d)** |
| 5 | 18,344–20,191 | West Colfax Ave | primary | 1.85 km | 2–6 lanes; **309 m is one side of a divided piece** (one-way) | urban, to measure | signals at st ~19,139 and ~19,861–19,909; concrete retaining walls at st ~19,232–19,816; **the lap passes under C-470 at st ~19,300** (§2e) |
| 6 | 20,191–23,831 | US-6, the carriageway heading toward Golden (West 6th Ave 0.82 km, unnamed 1.09 km, "Lariat Loop Scenic Byway" 1.73 km) | trunk, one-way | 3.64 km | 2 lanes of a 2+2 divided expressway. The two carriageway centrelines are 7–16 m apart, so the median is narrow; probably a barrier where they nearly touch | none | 45 → 55 mph; signals at Johnson Rd (~21,000) and Heritage Rd / Jefferson County Pkwy (~22,100); **the lap passes under C-470 at st ~21,100** (§2e); lowest point 1,783 m at st ~23,050 |
| 7 | 23,831–24,247 | US-6 northbound off-ramp to 19th St | trunk_link, one-way | 0.42 km | 1 lane (2 at the split) | retaining walls at st ~24,070–24,085 | 35 mph advisory; climbs out of US-6's sunken cut. **Route defect at its end (§2d)** |
| 8 | 24,247–24,942 | 19th St | secondary 144 m, then tertiary 496 m | 0.69 km | 2 lanes; divided at the ramp terminals (**105 m one-way**) | bike lanes with plastic flex posts; raised crosswalk table at st ~24,462 | 25/30 mph; crosses US-6 on the "Linking Lookout" lid park at st ~24,390 (~550 m before the pylons); climbs +5.7 % to the pylons |

**Width honesty.** The July Lariat Kevin has driven gives him about **22.6 m of drivable surface**:
- `1ROAD_main` averages 9.8 m;
- `1ROAD_shoulder_a/b/c` add ~6.4 m of drivable "shoulder" per side.

The real road is **6.1–6.7 m** of pavement with no shoulder. That is a 3× cut in what is under his
wheels, so it is his decision, not a silent default *(D4)*:
- **A** is real width with the real edge;
- **B** adds a 1–1.5 m firm gravel strip;
- both are built for Drive 1.

The July shoulders were the fix for 25 km of 6.5 m lane lined with 5 cm vertical-lip rumble
strips, *"undriveable slop"* (track.config.json `kerb._doc`). V3 has no rumble lips in either
variant.

What still has to be measured:
- Every "not measured" above, from aerial imagery, before the road is drawn.
- `docs/ROAD-CONSTRUCTION.md` says the 1913 design widened turns to ~24–26 ft (7.3–7.9 m). Each
  hairpin is still measured rather than assumed.

### 2b. Direction, start/finish, length

- **Start/finish:** the two 1917 stone pylons on 19th St at the foot of the Lariat
  (39.7424, −105.2285, 1,829 m). The line sits at the pylons. Every layout's grid stands on 19th
  St / Lookout Mountain Rd at the pylons, facing its own direction.
- **Full** goes up the Lariat first. Seen from above, it runs **anticlockwise**: up the mountain on
  the west, over the top to the south, east down the canyon, then north home through Golden. The
  signed area measures +16.9 km², which confirms the direction.
- **Reverse** is the same pavement driven the other way: 19th St → the ramp → US-6 → Colfax → US-40
  up the canyon → Paradise Rd → over the top → down the Lariat to the pylons.
  - Under the default *(D2a)* it drives all four divided stretches against the arrows: the ramp
    and US-6, plus the three short pieces on Colfax, on 19th St and at exit 259 (about 4.6 km in
    all). The ui text says so.
  - Option *(D2b)* gives it its own legal route instead: US-6's other carriageway, the 19th St
    on-ramp (way 642334992), and the other side of each short piece (at exit 259, way 42005706).
    That means its own centreline and a different length.
- **Length:** 24.94 km along the centreline, which matches the ui length of 24,942 m.
  - As last built, drive_test measured 24.80 km.
  - The config's `full._doc` still says "~20.9 km", which is out of date.
  - If *(D1)* picks Heritage Rd, the lap becomes ≈ 22.7 km.

### 2c. Road set = the lap, and nothing else

**What stays:**
- the lap's own pavement (all eight segments above, including its own off-ramp);
- the real ground around it.

**Structure that crosses the lap stays as structure, never as road:**
- **The 19th St lid** over US-6.
- **C-470's two bridges** over the lap, at st ~19,300 and ~21,100 *(D5)*. These are static decks
  and abutments only: nothing drivable on top, and nothing running along the lap.

**Authored pieces that make the place read right, none of them a second route:**
- the divided stretches as one slab each, with the median on it (ledger 0037's pattern) *(D2)*;
- short non-drivable side-road stubs at the named junctions (§4b) *(A9)*;
- OSM buildings on the town stretches *(A9)*.

**What goes:** everything the current build draws that is not the lap.
- All of it comes from the engine's environment stage (`scripts/environment/build_env.py`). V3 never
  runs that stage, and nothing in `route.*` ever asked for these roads.
- The figures below come from two measurements: re-running the July environment input offline, and
  extracting the installed kn5.

| Thing drawn today | Source ways | Deck length after clipping | Within 100 m of the lap |
|---|---|---|---|
| I-70 mainline, both carriageways (the "wavy ribbons" beside US-40) | 20 | 14.2 km | 7.6 km |
| C-470 (motorway "CO 470"). *Ledger 0048 first missed it.* | 32 | 5.75 km | 0.27 km |
| Unnamed motorway ramps (I-70 exits, C-470 links) | 60 | 8.1 km | 0.87 km |
| Pieces of US-6's opposite carriageway | 26 | 1.3 km | — |
| Other trunk ramps | 21 | 1.0 km | — |
| Ways reaching outside the box (see note) | 43 | 10.3 km | — |
| **Total** | 202 | **≈ 40.6 km** of 22 m-wide deck (the kn5 measures 37.3–40.8 km) | |
| `MOUNTAINS`: two sine-wave silhouettes 8.6 and 12.8 km west, each 24.4 km long | — | — | — |
| `WATER`: creek ribbons fetched as whole ways, reaching 13.4 km west | — | — | — |
| `GANTRY_pylons`: a power-line run at st 20,600–24,000, 55 m off the road (not checked against reality) | — | — | — |
| Baked forest: `PINETREE` (~900 3D pines) and `CONIFER` (~120k flat tree cards), 62 % of the file | — | replaced by TreeFX (§6) | — |
| 304 street lamps at 96 m spacing | — | replaced by the real inventory if Kevin reverses his July call (§5d, *D7*) | — |

The 43 out-of-box ways include:
- one 3.9 km I-70 way running west toward Genesee. This is `HWYSTRUCT_1`, not Clear Creek Canyon
  as 0048 first said;
- US-6 and CO-93 pieces north of Golden;
- the I-70/C-470 interchange.

**Two honest consequences.**
1. **I-70's empty shelf.** I-70 really is 20–50 m from US-40 for most of the canyon. Bare-earth
   elevation data still includes the freeway's cut and fill, so with I-70 removed the ground keeps
   I-70's flat graded bench.
   - Down the canyon that reads as an **empty flat shelf** beside US-40: real ground shape with no
     pavement on it.
   - That is the price of "no extra highways". Ground cover (grass and scrub on the shelf) dresses
     it; it does not become a road.
2. **The C-470 crossings.** The same data keeps C-470's approach embankments where the lap passes
   under it. With the decks removed, the lap would drive at speed, twice a lap, through a gap
   between two freeway fills. Hence *(D5)*: static bridges, not graded-away ground.

### 2d. Route-data defects — fix before drafting *(A1)*

1. **The U-turn at the end of the ramp (st 24,226–24,318).**
   - The config's `id:` list ends on OSM way 533503214. That is the ramp's **right-turn** branch,
     onto 19th St *east*.
   - So the lap turns back on itself (the heading swings ~190° in 15 m, R≈7 m) and runs about 100 m
     the wrong way on a one-way.
   - The real move is the **left** branch onto 19th St *west*: ways 533503210 + 1283267904. Both
     are tagged `destination=19th Street west;Lookout Mountain Road` and `turn:lanes=left`; I
     confirmed this today in the recovered July snapshot.
   - Fix: `id:484287799,1351773584,533503588,533503210,1283267904`. Re-run the centreline and check
     the start/finish seam before trusting it.
2. **84 m the wrong way at exit 259 (st ~16,602–16,686).** Measured today on the recovered July
   centreline against the July snapshot.
   - **What it drives:** the lap heads north-east (25–36°) along way 42005706, which is
     `primary, oneway=yes, lanes=4, turn:lanes=left|||right`, drawn south-west-bound (84 m).
   - **The divided pair:** its north-east-bound partner is way 119006778 (`primary, oneway=yes,
     lanes=2`, 85 m), which meets it at the same node.
   - **The geometry:** the July line also carries a 90° kink and ±14° zig-zags at st
     ~16,547–16,690.
   - **The fix:** route the lap on 119006778, and drop 42005706 from the `ref:US 40` match. That
     needs a new opt-in route key, since the gps stage has no way to exclude a way today.
   - **Confirm** on the aerial before trusting it.
   - **It is a divided pair,** so it is also one of D2's divided stretches (§2e). After the fix,
     Full drives 119006778 with its arrows; Reverse meets the same 85 m from the other side
     *(D2)*.
3. **The Colfax dog-leg (st ~20,190)** *(D1)*.
   - The lap makes a 152° left (R≈11 m) through the signalised US-6/Colfax junction, then runs
     1.9 km back, roughly parallel to the Colfax it just drove.
   - OSM has no turn restriction there; whether the movement is legal is unverified.
   - The real byway uses Heritage Rd (~1.5 km) instead. That would remove the reversal and make the
     lap about 22.7 km.
4. **A gate, so this class can't return:** P0's one-way check map-matches the re-derived centreline
   to the snapshot. It fails on any `oneway=yes` way the Full direction drives against (V3-PLAN P0
   step 8).
5. **Stale text:**
   - `full._doc` says "~20.9 km";
   - the ui files say `"run": "clockwise"`;
   - the ui `tags` include `fictional`;
   - the author is given as `prodrive-ac-builder`.

### 2e. One-ways, medians, bridges, structures

- **Divided pieces, treated one way *(D2)*.** Four stretches of the lap are one side of a divided
  road, driven as a single carriageway:
  - US-6 (all of segment 6, 3.64 km) plus its off-ramp;
  - 309 m of one-way West Colfax;
  - 105 m of one-way 19th St at the ramp terminals;
  - 85 m at exit 259: way 119006778 (`oneway=yes`, 2 lanes, north-east-bound) once A1's fix is
    in, with way 42005706 (`oneway=yes`, 4 lanes, south-west-bound) as its other half (§2d #2).

  The default *(D2a)* builds each as **one slab with its real median and the other side's lanes on
  it**, never as a second ribbon. Full drives with the arrows everywhere once A1's two fixes are
  in. Reverse drives all four against them unless Kevin picks *(D2b)*.
- **Bridges and decks.**
  - **The 19th St lid** over US-6 is Colorado's first highway lid, a park deck about 85 m (280 ft)
    wide measured along US-6.
    - The lap crosses it where the US-6 tunnel ways 533503591 and 533679737 (layer −1, ~85 m each)
      pass under 19th St, at st ~24,390. That is **~550 m before the pylons, not at the lap seam.**
    - Its level span is **declared from that tunnel footprint** (tens of metres along the lap),
      held level between its ends (L3, "Bridges dip").
  - **The July auto-detector's spans are both suspects.**
    - `[24,278–24,803]` is 525 m and ends on the lap's last vertex: a wrap artefact (L13). Held
      level, it would erase 19th St's real +5.7 % climb.
    - `[20,742–21,166]` (where its `_creek_bridge` dressing sat) contains the C-470 underpass at
      ~21,100: the lap passes *under* a bridge there, not over one.
    - Both are dropped unless the aerial shows a real lap bridge.
- **Overhead: C-470, measured today against the July snapshot.**
  - **st ~19,300, on Colfax.** C-470 ways 84720931 and 84720904 (both carriageways) and motorway
    links 84721006 and 1459465701 cross over the lap. All are tagged `bridge=yes, layer=1`.
  - **st ~21,100, on US-6.** C-470 way 84720905 crosses over the lap (`bridge=yes, layer=1`).
  - Bare-earth 3DEP drops the decks but keeps the approach fills. Default: static visual decks and
    abutments *(D5)*.
- **Other overhead structures:**
  - the 6th Ave pedestrian bridge crosses at st ~21,411;
  - other structures stand 15–40 m off the Colfax stretch at st ~19,432 / 19,573. Whether the lap
    passes under them is unverified.
- **US-6's sunken section:** through Golden, US-6 runs below the lid (an OSM tunnel of 171 m), with
  retaining walls on the ramp.
- **No rail crossing** on the lap. A US-6 warning sign refers to one off to the side.
- **No Clear Creek crossing.** The lap stays south of the creek.

## 3. Elevation & drainage

Source: USGS 3DEP 1 m bare earth, sampled every 25 m along the centreline (2026-10-11).

| Stretch | From → to | Net | Average | Steepest 100 m |
|---|---|---|---|---|
| Lariat climb, st 0–7,100 | 1,829 → 2,228 m | +398 m in 7.1 km | +5.6 % | +7.6 %. The 9.0 % over 50 m is probably the DEM reading the uphill cut, not the road |
| Summit + back side, st 7,100–9,710 | 2,228 → 2,284 m (high point 2,288 at st ~9,150) | +56 m | rolling | — |
| Paradise Rd | 2,284 → 2,179 m | −105 m | −5.4 % | −10.3 % |
| US-40, Mt Vernon Canyon | 2,179 → 1,942 m | −237 m | −4.9 % | −7.3 % |
| I-70 Business / US-40 | | | −4.1 % | |
| Colfax + US-6 | down to 1,783 m at st ~23,050, the lap's low point | | | |
| Ramp + 19th St | back up to 1,829 m at the pylons | ≈ +46 m | 19th St +5.7 % | |

- **Totals:** 505 m of relief (1,783 → 2,288 m) and about 552 m of climbing per lap.
- **The 1913 design rules:** grades no steeper than 6 %, and no curve tighter than a 50 ft (15.2 m)
  radius.
  - The data agrees on grade.
  - The hairpins are tighter than the rule on the OSM line (R≈12–14 m), and that line is faceted
    (§4). The aerial measures the real radius before the fit.
- **Grade cap: keep 16 % *(A7)*.**
  - The config set 16 % for a Paradise Rd grade of "−14.5 %" that the 1 m data does not reproduce:
    it measures −10.3 % over 100 m and −11.5 % at worst over 20 m. So 16 % never binds.
  - The config also records why the default was abandoned: the 6 % cap *"flattened the descent and
    floated the road metres above the canyon floor"*.
  - Any change is gated on replication vs 3DEP, measured before and after.
- **Crests and blind spots:** every hairpin on the climb is blind on the inside, where the rock cut
  stands. Jeffco says the outcrops limit sight distance and that there are no safe passing places.
- **Sideways tilt of the road (crossfall) *(A6)*.**
  - **No published figure exists for the Lariat.** The July file is **DEM-estimated, not
    measured**. Re-measured today:
    - ~10 % of its stations sit exactly at the 6 % cap, and 19 % on US-40;
    - in 9 separate places (8 on the climb), the tilt swings from ≥ 3 % one way to ≥ 3 % the other
      within 30 m. A looser count finds 16.
  - **The likely cause:** on a 6.1 m road, a lateral pair of 1 m DEM samples at the pavement edge
    reads the cut or the fill, not the road (L3b).
  - **V3's method:**
    - re-measure inside the real-width footprint;
    - gate the roll rate (V3-PLAN P2 step 4);
    - check a sample against 3DEP's source lidar before calling anything "measured".

    Where it fails, the construction standard applies: 2 % crown, or 2 % toward the cut ditch on
    bench sections.
  - The switchbacks get **no banking** (L10; ledger 0003 stays open).
- **Drainage:** there is no surveyed inventory of culverts or ditches.
  - The build uses the construction standard as an authored default and labels it as authored.
    The standard is the Lariat table in `docs/ROAD-CONSTRUCTION.md`: 450 mm culverts about every
    150 m and at hairpin apexes, plus a 0.4 × 1.2 m ditch at the foot of the cut side.
  - Mount Vernon Creek runs down the canyon beside US-40, with a strip of streamside vegetation
    (species unverified).

## 4. Corner-by-corner character

Turn angle and radius are measured on the drafted centreline. Advisory speeds come from OSM tags
(posted plaques). **Every corner still needs reference imagery.** A Street View / Mapillary pass
along the Lariat is owed (§12). It is what turns "authored" walls, rails and signs into "surveyed"
ones.

**The hairpins are faceted in the data.**
- The OSM hairpin ways have nodes every 4–5 m that turn 17–27° each, and the engine never smooths
  an OSM line in plan.
- Measured today at the base hairpin (st 252–297), consecutive 3 m points step 0, 9, 17, 14, 12, 20,
  9, 16, 16, 5 and 25°. A smooth R 12 m arc steps an even 14°.
- On the whole climb, 134 points turn ≥ 10° from their neighbour.
- Every hairpin is therefore fitted as a smooth arc at its measured radius before the road is built
  *(A2)*. Kevin's 14 m widening at C1 is re-asked only after he drives the fitted curve.

| # | st | Corner | Turn / radius | Posted / advisory | What defines it (sources) | Barrier mapped in OSM | The drive test must confirm |
|---|---|---|---|---|---|---|---|
| C0 | 0 | **The pylons** (start/finish) | straight | 25/30 → 20 | the two 35 ft stone pylons | — | no step at the lap seam (L13) |
| C1 | ~262 | **Base hairpin** (Kevin's "impossible" turn) | ~164°, R≈12 m on the OSM line; **faceted** (25° steps) | 20 / **10 mph** (way 1432442175) | the first hairpin above the Golden homes | — | drivable at real speed in both directions on the **fitted** curve; the July 14 m widening is off for Drive 1 and re-asked after it *(A2)* |
| C2 | ~1,070 | Chimney Gulch / lower night gate | 138° | 20 | trail crossing, pull-off, gate; the Golden/Jeffco line | — | gate posts stay outside the lane |
| C3 | ~1,390 | Below Lookout Mountain Crag | 133° | 20 | a climbing cliff at mile 1.4 | metal rail near st 1,651 | — |
| — | ~1,700–2,300 | Lariat Scenic View, Tiers of Zion trailhead, **Sensation Point** | bends | 20 | Sensation Point's concrete overlook wall, with a pipe rail on top, rising straight out of the rock; concrete guard rail mapped at st ~2,225 | concrete | it reads as concrete on rock, not W-beam |
| C4–C6 | ~2,600 / 2,830 / 2,990 | **The three Lower Hairpins**, stacked | 178–189°, R≈12–14 m | 20 / 15 (ways 1432442169/71/73) | scattered pines; the narrowest lanes are here | metal rail at st ~2,459 / 2,762 / 2,942 | **stacked legs:** nothing between legs takes the other leg's height (L4); rock cut + fill between legs, no invented walls *(A3)*; no grade spike on the inside edge |
| — | ~3,636 | The M, 63 m off the road | — | — | Colorado School of Mines' whitewashed rock M on Mount Zion | — | visible from the road, and from the pylons at +12° |
| — | ~4,920–4,965 | **Windy Saddle** lot | bend | stop sign | 24-space paved lot, dry-stone walls 1–2 m high, trailheads | — | the lot's entrance is flush with the road |
| C7–C10 | ~5,410 / 5,500 / 5,600 / 5,860 | **The four Upper Hairpins**, stacked, north-facing | 181–199°, R≈12–14 m | 20 / 15; one is 10 uphill / 15 downhill (way 1432422186) | dense conifers; the 1916 Spring House ruin nearby | metal rail at st ~5,179 / 5,459 / 5,569 / 5,742 | the same stacked-leg checks; the closest legs on the map (20.5 m apart, st 5,334 / 5,501) are here |
| C11 | ~6,450 | **Wildcat Point** bend | 121–123° | 20 | massive rock outcrops, sloping stone retaining walls, the 1963 Cement Bill memorial; the plunge view into Clear Creek Canyon | metal rail at st ~6,653 | the view exists: about −11.8° down to the canyon mouth |
| — | ~7,100–7,700 | Summit | — | 35 from st ~7,569 | Buffalo Bill lot; tower cluster 22–26 m off at st ~7,190 | concrete barrier at st ~7,219; rail at st ~7,380 | — |
| C12 | ~9,730 | Paradise Rd tee | 90° left, R≈13 m | unknown | T-junction; Lookout Mtn Rd continues south | — | authored junction mouth; **race open box** (§4c) |
| C13 | ~10,590 | Paradise Rd bend | R≈12 m | unknown | homes in pines | — | — |
| C14 | ~11,652 | Paradise Rd → US-40 | unknown | stop | Park-n-Ride, exit 256 area | — | authored junction mouth; **race open box** |
| C15 | ~16,546 | Exit 259 signals | 90° kink + zig-zags on the July line | signals | interchange, Wooly Mammoth Park-n-Ride | — | **after A1's fix, no wrong-way run** (§2d #2); **race open box** |
| C16 | ~20,190 | Colfax → US-6 | 152° left, R≈11 m | signals | route shape *(D1)* | — | **race open box** if the dog-leg stays |
| C17 | ~23,831 | US-6 → off-ramp | diverge | 35 advisory | the point where the ramp splits off | — | a gore, not a box; the race seals US-6 beyond it |
| C18 | ~24,250 | Ramp end → 19th St | **today a ~190° U-turn (defect)**; after the fix a normal left | signals | bike lanes | — | an ordinary left turn with no reversal; **race open box** |

**Counting check.**
- The sources count seven hairpins. The NRHP form describes three, then four more; Visit Golden
  counts 56 curves including seven hairpins.
- Jeffco counts about 35 curves tighter than a 25 mph design speed.
- The detector finds the 7 named hairpins, plus the base hairpin, plus 3 more bends of 120–140°.
  That is consistent with the sources.
- The port audit's "11 hairpins ≥ 135°" is the 7 named hairpins and C1–C2, plus the two route
  defects C16 and C18.

**Stacked legs, defined.** A "stacked pair" is two lap points less than 40 m apart on the map and
more than 150 m apart along the lap. Measured today on the July centreline:
- **1,188 pairs**, all at st ~2,500–2,950 and ~5,300–5,850;
- vertical gap 6.5–14.7 m (median 10.1 m);
- closest on the map 20.5 m;
- at the real 6.7 m width, the legs' edges stay ≥ 13.8 m apart.

The stacked-leg gate tests exactly these pairs (V3-PLAN P5).

### 4b. Junctions the lap passes (cross streets)

Measured today: every OSM way in the July snapshot that comes within 4 m of the lap line. Stations
are ±50 m.
- **≈ 145 ways touch the lap:**
  - 64 service drives;
  - 30 residential streets;
  - 12 secondary, 7 primary and 3 tertiary roads;
  - the rest ramps and links.
- **About 45 named side-road mouths.** In the street layouts each gets a **short, non-drivable
  stub** (JUNCTIONS R18(c): visual stub, curb returns, an invisible wall across the mouth line) so a
  signal junction has a road crossing it *(A9)*.
- **In the race layouts** every one of them is closed with a barrier at its edge (§4c).
- **Service drives** get flush aprons in town and nothing on the mountain.

| Stretch | Named junctions (≈ st) | Signals |
|---|---|---|
| Golden, Beverly Heights | Goldenvue Dr (~6), Mount Zion Dr (~645), Bonvue Dr (~777) | — |
| Lariat, st 1,070–7,100 | none; only pull-offs, overlooks, the Windy Saddle lot and the night gates | — |
| Summit + back side | Buffalo Bill / Lookout Mountain Park access, Panorama Dr (~7,814 / 7,964 / 9,224), Colorow Rd (~8,090 / 9,572), Larkspur Dr (~8,627), Grandview Ave (~9,104), Mountsfield Dr (~9,170), Crestvue Dr (~9,554), Westview Ave (~9,572); Lookout Mtn Rd's south leg at the C12 tee | — |
| Paradise Rd | Dekker Dr (~9,940), Paradise Circle (~10,120), Lamb Ln (~10,410), Cabrini Blvd (~10,608), Monte Vista Rd (~10,916), Sunrise Dr (~11,141), Charros Dr (~11,180), Mount Vernon Circle (~11,291) | — |
| US-40 canyon | exit 256 ramps + US-40 west (~11,618–11,702), South Grapevine Rd (~11,929), Cabrini Blvd (~13,945), exit 259 ramps (~16,005 / 16,323) | — |
| Exit 259 → I-70 Business | Hogback Rd (~16,583), I-70 ramps (~17,900), CR 93 link (~18,197), Heritage Rd (~18,389; the D1 alternative) | exit 259 (C15) |
| West Colfax | Zeta St (~18,731), West St / Rooney Rd (~19,184), Violet St (~19,466), Corporate Dr (~19,610 / 19,628), Interplaza West (~19,928), West 6th Ave / US-6 (~20,237, C16) | Rooney Rd (~19,139), Interplaza West (~19,861–19,928), C16 |
| US-6 | ramps (~20,464–20,713), Johnson Rd (~21,037–21,055), Heritage Rd / Jefferson County Pkwy (~22,123–22,201), ramp (~22,957) | Johnson Rd, Jefferson County Pkwy |
| Ramp + 19th St | 19th St east at the ramp terminal (C18), Parfet Estates Dr (~24,487), Moly Rd (~24,514), Pinal Rd (~24,580 / 24,700), Tangent Way (~24,700), Smith Rd (~24,925) | C18 |

### 4c. The race version *(D3)* — Kevin's brief, segment by segment

**Whether there is one is Kevin's call *(D3)*.** His brief asks for *"more or less an Alvarado's
width for the entire track with deviances in various areas"* (Alvarado ≈ 13 m curb to curb).
Measured against this lap:
- **Near Alvarado's width: only Golden.** I-70 Business and Colfax (2–6 lanes) are 3.65 km, 15 % of
  the 24.94 km lap. Golden from exit 259 home, adding US-6's 2-lane carriageway, the ramp and 19th
  St, is 8.40 km (34 %), but those additions are narrower. US-40's three canyon lanes (4.89 km) may
  come close once measured.
- **Half Alvarado:** the 6 km Lariat Trail, at 6.1–6.7 m. The summit and back side are 2-lane
  roads; Paradise Rd is unmeasured.
- **No widening:** every layout drives the same road surface (L8), so a race layout cannot make the
  mountain road wider.
- **No town-only loop with that width.** The only loop that closes in Golden is ≈ 5.2 km: Colfax
  from Heritage Rd (st ~18,389) to US-6 (st ~20,191), US-6 back to Heritage Rd / Jefferson County
  Pkwy (st ~22,123–22,201), then ~1.5 km of Heritage Rd back to Colfax. Heritage Rd is not part
  of the lap, and it is mostly 2 lanes (OSM `lanes=2`, measured today in the July snapshot), as
  is US-6's carriageway. So that loop does not have Alvarado's width either, and the option is
  dropped.

The default is **(D3 a)**: the race version below, on the real narrow road. Under **(D3 b)** there
is no race version and nothing in this section is built.

**The rule set is Lake Murray's** (its corridor design run is landing now):
- a per-direction corridor of about Alvarado's width (13 m street, ~11.4 m clear);
- the other direction's access closed;
- open intersection boxes where the race turns;
- side streets sealed;
- no route to the other side.

**On this road, three local rules:**
1. **A 6–7 m two-lane mountain road is used whole, one-way.** Closing "the other lane" would leave a
   3 m strip, and there is no other lane left to close.
2. **No K-rail down a historic 6 m road, and no barrier added along its edges.** The real edges
   (stone, W-beam, open) are the race edges.
3. **Closures go at junction edges.** Curb-line barriers go only where a real curb line exists, on
   the town streets.

| Segment | Real width | Race corridor | Closed off |
|---|---|---|---|
| Lookout Mtn Rd in Golden (st 0–1,070) | 2 lanes, to measure | whole road, one-way | the 3 side streets at their edges |
| The Lariat (st 1,070–7,100) | 6.1–6.7 m | **whole road, one-way** (the main deviation: about half Alvarado) | nothing in the road; pull-offs, overlooks and the Windy Saddle lot stay open (dead ends, no route anywhere) |
| Summit + back side | 2 lanes, to measure | whole road | the park access and ~10 side streets; Lookout Mtn Rd's south leg at the C12 box edge |
| Paradise Rd | to measure | whole road | its 8 side streets |
| US-40 canyon | 3 lanes, to measure | whole road (about Alvarado if 3 lanes) | exit 256 ramps and US-40 west at the C14 box edge; Grapevine, Cabrini; exit 259 ramps |
| I-70 Business | 3–5 lanes; at exit 259 an 85 m divided pair (2 lanes north-east-bound, 4 lanes south-west-bound) | about 13 m on the race side; a lane-closure barrier closes the rest, leading up to medians but never on them (Lake Murray's rule). At exit 259 the race keeps the 2-lane side (way 119006778) | Hogback Rd and the I-70 ramps at the C15 box edge; exit 259's 4-lane side (way 42005706), also at the C15 box edge; CR 93 link; Heritage Rd |
| West Colfax | 2–6 lanes | about 13 m; the whole road where it is 2 lanes; the 309 m divided piece is its own carriageway | Zeta, West St / Rooney, Violet, Corporate, Interplaza |
| US-6 | one carriageway, 2 lanes | that carriageway | every median gap; Johnson Rd, Jefferson County Pkwy / Heritage, the ramps; US-6 beyond the C17 gore |
| Ramp | 1 lane (2 at the split) | the ramp | — |
| 19th St | 2 lanes + bike lanes | whole road | 19th St east at the C18 box edge; Parfet Estates, Moly, Pinal ×2, Tangent, Smith |

- **Open boxes (race turns): C12, C14, C15, C16, C18.**
  - The whole intersection is drivable for the turn.
  - The legs the race doesn't take are sealed at the box edge.
  - The clockwise race uses the same boxes, turning the other way.
- **Race kerbs:** none on the mountain. Kevin's July finding about rumble lips on this lane
  (*"undriveable slop"*) stands.
- **Files:**
  - the closures live in one race kn5, shared by both race layouts (L8 as amended by 0047);
  - the shared road kn5 is unchanged;
  - the closure barriers use Kevin's 4 m K-rail silhouette, so the race kn5 stays in the Full
    package until that pack's licence is recorded (as on Lake Murray).

## 5. Built environment & landmarks

**Rule (template, 0029 §5):** furniture stands on true ground. The road comes down to the data;
the furniture never gets raised to the road. On the Lariat the rule is sharper:
- where the ground outside a curve falls away, a sign post or rail post must stand on the real slope
  or be mounted on the wall or rail;
- it never floats at road height over a drop;
- on stacked legs, everything is seated to its own leg's station (L4).

### 5a. By segment

**st 0–1,070, Golden**
- Edges: private stone walls (one is hit repeatedly by cars at night), yellow steel bollards
  (st ~649), 3 speed humps, crosswalks, power poles (an OSM speed sign hangs on one at st ~403).
- Buildings: Beverly Heights homes on the east side; they drop out of view quickly. They are built
  from OSM footprints *(A9)*.

**st 1,070–7,100, the Lariat** — the edges come in three layers.
1. *The original stone and concrete:*
   - 3 stone guardrails, built with deliberate gaps for views and drainage. They still carry
     eye-bolts from the old cable rails.
   - 2 sloping stone retaining walls at Wildcat Point.
   - Sensation Point's concrete wall.
   - Old concrete posts behind the steel at Windy Point.
   - Dry-stone walls at Windy Saddle.
2. *Steel W-beam (the corrugated highway guardrail):* 13 runs already existed in 1988. Jeffco says
   it now lines the drop-offs, damaged and below current standard.
3. *Nothing:* open edges where the slope is gentle, about 20 dirt pull-offs (16 on switchbacks),
   4 paved overlooks, and the Windy Saddle lot.

Also on this stretch: rock cuts at the pavement edge on the uphill side, trail signs, cyclists
(about 30 % of road users), and occasional paragliders (launch site unverified). The National
Register inventory lists **only the two Wildcat Point walls and the Windy Saddle walls** as
retaining walls on the climb. Between stacked legs the ground is therefore cut and fill, not stone
*(A3)*.

**st 7,100–7,700, summit**
- Edges: concrete barrier at st ~7,219; the Lookout Mountain Park gate (st ~7,680) and a ranch gate.
- Buildings: the Buffalo Bill Museum (1979) and Pahaska Tepee (1921, closed); a stone picnic
  shelter; the tower cluster 22–26 m off the road; the main antenna farm 300–600 m SE.

**st 7,700–9,710, back side**
- Edges: unmeasured.
- Buildings: houses among ponderosa pines (OSM footprints, *A9*), Boettcher Mansion, the Nature
  Center (~200 m off), the Apex Park West trailhead (st ~9,581).

**Paradise Rd**
- Edges: unmeasured.
- Buildings: homes in pines (OSM footprints; detail unverified); the Park-n-Ride and bus stops at
  the US-40 end.

**US-40 canyon**
- Edges: guardrail was improved in the 2021 resurfacing (positions unpublished). What separates
  US-40 from I-70 (grade, fence or barrier) is unknown; the aerial is owed.
- Other: cut slopes and canyon walls. At exit 259: masts, the Wooly Mammoth Park-n-Ride, truck/RV
  parking.

**I-70 Business / Colfax**
- Edges: concrete retaining walls at st ~19,232–19,816; C-470's bridges overhead at st ~19,300
  *(D5)*.
- Buildings: Heritage Square (current state to verify), commercial frontage, the Rocky Mountain
  Quilt Museum (130 m off), the USMC Memorial (st ~20,000).

**US-6**
- Edges:
  - W-beam at st ~20,652–21,411, around the C-470 underpass at ~21,100;
  - a median barrier where the carriageways nearly touch (unverified);
  - 1.4 mi of wildlife fence, with an at-grade animal crossing at st ~23,530 (rumble strips and
    sensor-triggered strobes).
- Other: CDOT guide and warning signs, the 6th Ave pedestrian bridge, the US-6 Trail path alongside,
  and probably the Jefferson County Government Center near Johnson Rd (verify).

**Ramp + 19th St**
- Edges: retaining walls on the ramp; flex bike-lane posts.
- Other: the lid park (trees on the deck, a small amphitheatre, picnic tables) near the Mines west
  campus.

**The stone is the memorial-grade detail.** The National Register listing rests on the road being
unchanged since 1913: its alignment, curve radii, width, grades and stone works. So these are built
as **those specific objects**, not as generic W-beam *(A4)*:
- the stone guardrails, with their gaps;
- the Wildcat Point walls;
- Sensation Point's wall;
- the Windy Saddle walls.

The rest:
- **Modern W-beam** goes only where it really is.
- **The edge inventory:** no data source says which edge has stone, which has steel and which has
  nothing; the Street View pass has to supply that run by run.
- **Kevin's July call** lined warning-barrier runs with his 4 m concrete modules (*"Kevin's model
  pack: 4 m concrete barrier modules instanced along warning-barrier runs as collidable 1WALL
  geometry"*). V3 asks him to reverse that for the real edges *(D7)*.

### 5b. Barrier positions already mapped (OSM, forward stations)

- Metal guard rail near st 858, 1,651, 2,459, 2,762, 2,942, 5,179, 5,459, 5,569, 5,742, 6,653 and
  7,380.
- Concrete guard rail at st ~2,225 (probably Sensation Point).
- Concrete barrier at st ~7,219 (summit).
- Dry-stone walls at st ~4,920–4,965 (Windy Saddle).
- W-beam on US-6 at st ~20,652–21,411.

These are points, not runs. The survey has to supply where each run starts and ends.

### 5c. Signs

**What stands there, from the data:**

- **The Lariat (Jefferson County):**
  - 13 regulatory 20 mph signs are mapped, at st ~75, 221, 403, 897, 1,002, 1,672, 1,675, 2,489,
    3,116, 4,251, 4,374, 4,877 and 24,833. A 35 mph sign stands at st ~7,569.
  - Advisory plaques:
    - 10 mph at the base hairpin (way 1432442175);
    - 15 mph at the lower hairpins (ways 1432442169/71/73) and most upper ones;
    - 10 uphill / 15 downhill at one upper hairpin (way 1432422186);
    - 15 mph at each speed hump (these go only if the humps do, A10).
  - "No vehicles over 30 ft" signs stand at Pinal Rd/19th St and at the Buffalo Bill access. OSM
    says 24 ft, so the two conflict; verify.
  - Also: night-closure signs at both gates; trailhead, Denver Mountain Parks, Jeffco Open Space and
    byway markers.
- **No arrow or chevron sign is mapped anywhere on the Lariat.** The data cannot say where the real
  ones stand. Jeffco's study calls today's signage redundant and recommends replacing it to current
  MUTCD standards, so expect many older signs rather than a clean modern set.
- **US-6 / Golden (CDOT):**
  - Speed: 45/55 mph limits on US-6; an EXIT 35 M.P.H. advisory; 25 mph on 19th St.
  - Warning signs: Right Lane Ends, Signal Ahead, Sharp Left Curve, Merging Traffic, a
    cross-traffic/railroad warning, and wildlife-crossing warnings with strobes.
  - Green guide signs: Johnson Road NEXT SIGNAL, C-470 to I-70 West, East C-470 / West I-70.
  - I-70's own 65 mph signs are visible from US-40, but they belong to I-70 and do not go on US-40.

**Kevin's July call, and the V3 proposal.** The July config reads: *"Euro faces per Kevin:
sharp-turn arrows at warning-barrier entries; 70 disc on the climb, 110 discs on the plains
legs."* V3 asks him to reverse it for US faces on a US road *(D7)*. If he keeps it, the sourced
positions below still apply, with his faces.

**The build, in one pass *(A5)*:**
1. **Sourced signs first:** the 13 mapped 20 mph limits, the 35 mph at the summit, the advisory
   plaques at their mapped hairpins, and the US-6 set above.
2. **Then the arrows, by Kevin's approved ledger 0044 rule, marked authored** (none is mapped):
   - **Placement.** The W1-6 is the yellow sign with a fat black arrow. It goes **at the corner,
     just past the outside edge, facing the approach**: the spot a car that failed to turn would
     hit.
   - **Which corners qualify.** The corner must be tight: apex radius ≤ 30 m and at least 45° of
     turn. The "failed-to-turn ray" must also leave the pavement inside the arc.
   - **Hairpin clause.** A corner of ≥ 135° with ≥ 50 m of arc gets a second W1-6, or a W1-8
     chevron run (opt-in).
   - **Both directions.** San Diego signed one direction only. Here the street layouts share one
     model and the real road is two-way, so each qualifying corner gets a sign facing each
     direction.
   - **Candidate corners** (drafted centreline): C1, C2, C3, C4–C6, C7–C10, C11, C12 and C13.
     That is 14 corners; about eight qualify for the hairpin clause. C16 and C18 are route shapes:
     fix or keep the route, don't sign them.
   - **The count, shown to Kevin before the build:** ≈ 14 × 2 + 16 ≈ **44 authored plates** on a
     National Register road. He can cap it.
3. **Set-back and mounting.** San Diego's 1.63 m came from its sidewalk; the Lariat has none.
   - The post stands on true ground just beyond the pavement edge or guardrail line.
   - Where the slope drops away, the sign is mounted on the W-beam rail.
   - **Where the edge is a historic stone guardrail over a drop,** the post stands on true ground
     within 2 m behind the wall, or the sign is left out. Never on the stone, never floating, never
     in the lane.
4. **What MUTCD practice says about chevrons.** Whether arrows or chevrons are expected depends on
   the gap between the posted speed and the advisory speed.
   - 20 → 15 mph (most hairpins): optional.
   - 20 → 10 mph (the base hairpin and one upper hairpin): the "recommended" band.
   - So chevron runs go **only where the survey shows real ones**.

The build's arrow set is an authored choice, not a replica, and the ui text says so.

### 5d. Street lamps — only where real *(D7)*

**Kevin's July call:** *"Streetlights ON per Kevin: yellow, 96 m, dim wide pools."* That put 304
lamps along the whole lap, including the mountain and canyon, which have no street lighting. V3
asks him to reverse it, as follows:
- **Lamps only where they stand:** the inventory below.
- **His wide, dim pool shape stays:** *"Kevin: ~3x spread, no ground saturation"*.
- **Night stays available.**

**The inventory.**
- 39 OSM-mapped lamps stand within 40 m of the lap.
- Treat that as a floor: 509 of the 576 lamps in the area carry no type tag, so Golden's main roads
  are under-mapped.
- Expect a few dozen in total, not 304.

| Stretch | Lamps mapped within 40 m |
|---|---|
| Golden part of Lookout Mtn Rd (st 500–1,000), plus near the pylons | 1 + 2 |
| **The Lariat, st 1,070–7,100** | **none** (and none in the National Register inventory) |
| Buffalo Bill complex, st 6,500–7,000 | 1 |
| Back side, Paradise Rd | none (at most porch and driveway lights, unverified) |
| **US-40 canyon, st 11,654–15,500** | **none**; I-70's headlights are the only moving light |
| Exit 259, st 15,500–16,500 | 8 |
| Heritage / Colfax, st 19,000–19,500 | 1 (clearly incomplete: every junction has signals) |
| US-6, st 20,191–23,831 | 3 at Johnson Rd. The rest is tagged `lit=no`; the wildlife crossing's "lit=yes" means its sensor strobes |
| 19th St interchange, ramp, lid and 19th St, st 23,000–24,500 | 23 |

**Lamp type:** 24 of the tagged lamps are high-pressure sodium (bent-arm cobra heads, high masts,
straight masts) and 1 is LED. Colour and era are in §7.

### 5e. Landmarks worth modelling

| Landmark | Where | When |
|---|---|---|
| **The 1917 stone pylons**: two ~10.7 m (35 ft) rough-stone columns, each with a pedestrian arch; the east one reads "Entrance to the Denver Mountain Parks" | st 0 | **first build**: they are the start/finish |
| **C-470's two bridges over the lap** (static decks + abutments, no road on top) | st ~19,300, ~21,100 | **first build** *(D5)*, so Drive 1 never passes through a gap between fills |
| Stone guardrails, Wildcat Point walls, Sensation Point wall, Windy Saddle walls | §5a | **Drive 2**: they are the road's edges |
| OSM buildings on the town stretches; kerbs, sidewalks, side-road stubs | §4b, §5a | **Drive 2** *(A9)* |
| The M on Mount Zion: whitewashed rock, roughly 30 × 30 m; lit at night since the 1930s, with LED bulbs since 2008 | st ~3,636, 63 m off | second pass (marked on the ground, lights optional) |
| Windy Saddle lot (walls, picnic tables, trailhead signs) | st ~4,950 | second pass |
| The summit towers (22–26 m off) and the antenna farm, including the 730 ft Lake Cedar master tower | st ~7,190 / 300–600 m SE | later; the tall tower is the most visible man-made thing on the mountain from Denver |
| Buffalo Bill Museum / Pahaska Tepee | st ~7,080 | later |
| The 19th St lid park | st ~24,390 | first build as a level deck over its tunnel footprint; dressing later |
| A low-poly Denver skyline from OSM building heights | 19.6–23.2 km east | after Drive 2 *(D6 ii)* |
| 6th Ave pedestrian bridge | st ~21,411 | later (the car drives under it) |
| Heritage Square, USMC Memorial, wildlife crossing | segments 4–6 | later |

## 6. Vegetation & terrain palette

### 6a. Bands (which way a slope faces matters more than its height)

North- and east-facing slopes carry conifers. South- and west-facing slopes are open grass and
shrub. The National Register form describes exactly that pattern on the climb: foothill grass and
shrubs first, scattered pines at the lower hairpins, then plenty of evergreens in the shaded upper
section.

| Band | Where | What grows | Density |
|---|---|---|---|
| Golden + plains legs, 1,783–1,900 m | st 16,500–24,942 and the first ~1 km | watered lawns, cottonwoods and planted street trees in town; short dry grasses (blue grama, sideoats grama, purple threeawn) on unwatered ground; soapweed yucca, prickly pear and smooth sumac on dry slopes | street trees only; no forest |
| Lower Lariat, 1,830–2,000 m | st 0–~2,500, east face | open grass and shrub: skunkbush sumac, mountain mahogany, American plum and chokecherry in the gulches; scattered Rocky Mountain juniper and ponderosa | sparse, which is why the views are open |
| Lower hairpins → Windy Saddle, 2,000–2,110 m | st ~2,500–4,950 | scattered ponderosa and juniper with grass between; Douglas-fir in shaded pockets | patchy |
| Upper hairpins, north-facing, 2,110–2,230 m | st ~5,000–6,500 | **dense** ponderosa and Douglas-fir, with Rocky Mountain maple, ninebark, common juniper, raspberry and barberry underneath; spruce in the Spring House drainage (species unconfirmed) | closed canopy |
| Summit + back side, 2,225–2,290 m | st 7,100–9,710 | ponderosa groves with grass and wildflower meadows; houses among the pines | open woodland |
| Paradise Rd + Mt Vernon Canyon, 2,284 → 1,942 m | st 9,710–16,546 | the south-facing side is open grass and shrub with juniper and mahogany; the north-facing side has denser ponderosa and Douglas-fir; a streamside strip along Mount Vernon Creek (species unverified) | split by which way the slope faces |

**Do not use:**
- Gambel oak: no source puts it on Lookout Mountain; its range is further south.
- Pinyon pine: there is only one outlier record.
- Anything urban on the mountain.
- Windy Saddle's noxious weeds (Dalmatian toadflax, myrtle spurge): they are not palette species.

**This replaces** the installed "wall of trees": ~120k flat tree cards packed within ~25 m of the
road edge, spread evenly over the whole lap.
- **Slope direction leads:** the lower east face and the plains legs stay almost bare.
- **Kevin's July rule, *"more trees the higher up"*, is proposed for reversal, not kept *(D7,
  item 5)*.** The July config ran the forest *"sparse at the Golden base, dense at the Buffalo Bill
  summit"*. The research in the table above disagrees at the top:
  - The densest real stand is on the north-facing upper hairpins (2,110–2,230 m): a closed canopy
    of ponderosa and Douglas-fir, the shaded upper section the Register form describes as full of
    evergreens.
  - The summit and back side (2,225–2,290 m) are ponderosa groves with grass and wildflower meadows
    and houses among the pines: open woodland, the usual form of Front Range ponderosa stands (the
    life-zone and USGS ponderosa-woodland sources in §13).
  - So density rises from Golden to the upper hairpins, then opens out over the top. If Kevin keeps
    his call, the top band is built densest instead.

### 6b. TreeFX palette — stand-ins from what is on this machine *(A8)*

TreeFX is a Custom Shaders Patch feature. It draws trees when the track loads, from a text list
plus `.bin` tree models, so the trees add nothing to the track file's size. The models the old
config names (`MRS_pine_high_2_1`, `MRS_Sapin_3_0_high`, `MRS_Sapin_4_0_high`) are **not on this
machine**. These are:

| Real species | Stand-in `.bin` (where it lives today) | Fit | Licence |
|---|---|---|---|
| Ponderosa pine (the signature tree) | `ScotsPine.bin` (shuto_revival_project_beta); alternates `Pine.bin` (nohesi_110) and `Pine_1.bin` (Kruth_Larcenaire) | closest shape: tall clear trunk, orange plated bark, open crown; **verify in game** | mined, personal use only |
| Douglas-fir | `Spruce1–4.bin` and `Spruce_11.bin` (algarve_portimao_2023); `Spruce_1.bin` and `MRS_Sapin_0_0.bin` (Kruth_Larcenaire) | a dark cone-shaped conifer; a stand-in | mined, personal use only |
| Spruce (Spring House drainage) | the same spruce set | fine | mined |
| Rocky Mountain juniper | `AlaskaCedar1/2.bin` (shuto), scaled well down; or leave it out | **weak**; a gap | mined |
| Cottonwood / town street trees | `SycamoreV1–3.bin` (already in SD's `source/trees/`) | a broadleaf streamside stand-in | mined |
| Mountain mahogany, skunkbush, chokecherry/plum | `Bush.bin`, `Bush2.bin`, `Bush3.bin` (SD set, originally from algarve) | generic shrub; fine at speed | mined |
| Soapweed yucca (dry lower slopes) | `Yucca.bin` (SD set); check its size first | plausible | mined |
| **Missing outright** | a true ponderosa, a true Douglas-fir, Rocky Mountain juniper, a cottonwood | purchase or find free models (§8) | — |

Every model above is third-party mod content.
- It rides only in the **Full** package, on this machine.
- The public CC0 zip ships with `[TREES]` commented out and no `.bin` files (docs/PUBLISHING.md):
  **the public Lariat has no vegetation** *(A12)*.

### 6c. Ground cover, grass, season

- **Ground texture: Kevin's July call.** The July config says *"Alpine grass instead of dry dirt
  (Kevin)"* (ambientCG Grass001, green).
  - **The case for reversing it:** the real slopes are green only in May–June and tawny short
    grass from July to October.
  - **What V3 asks:** reverse it for a late-summer tawny ground *(D7)*.
  - **Gap:** a CC0 dry-grass / foothill-scrub ground texture (§8). The July `ground_dry_diffuse`
    is mined from LA Canyons, so it is Full-only.
- **GrassFX** (CSP's 3D grass blades), in 0045's corrected grammar:
  - on the near-road ground only (corridor and medium tiers);
  - never on the visual-only tiers;
  - never on rock cuts or wall faces. Those are separate meshes so grass never grows on a cliff.
- **Season:**
  - Grass: green May–June, tawny gold July–October.
  - Sumac, maple and chokecherry turn red-orange in late September–October; cottonwoods in town go
    gold.
  - Conifers and juniper stay dark green all year.
  - Winter: brown, with snow lingering on north faces and the upper hairpins.
  - Default: late-summer tawny (if D7 reverses the alpine grass).

### 6d. Terrain extent and relief — what the views need

The driver sees far more than the July terrain covers. That terrain was the lap's bounding box plus
150 m, at 40 m cells. Measured sightlines (bare earth, eye height 1.1 m):

| From | To | Angle | Distance |
|---|---|---|---|
| Pylons | the M | **+12°** | ~1 km |
| Pylons | Mount Galbraith | +6.4° | 3.2–3.7 km |
| Windy Saddle | Golden | −7.4° | 1.6–2.9 km |
| Wildcat Point | Clear Creek Canyon mouth | **−11.8°** | 1.5–2.2 km |
| Top of US-40 | Genesee Mountain (the western skyline) | +5.6° | 3.5–7 km |
| Lower hairpins (st ~2,600) and higher | downtown Denver | visible with ~0.6° to spare: a thin skyline about 1° below eye level | 19.6–23.2 km east |
| Pylons | Denver | **blocked**, by 0.13° (South Table Mountain's shoulder) | — |
| Lap high point (st ~9,150) | Mount Blue Sky (Evans) | +3.0°, clears by 0.6° | 36–40 km |
| Summit / back side | Longs Peak, Pikes Peak | just clear the horizon (+0.1° to +0.4°) | 66 / 100 km |

So the ground is built in tiers *(D6)*:

1. **Road corridor, ≤ 3 m cells, ~20–25 m past the pavement edge.** The cells must be smaller than
   the 6.1 m road (L3b).
   - The ground is shaped the way the road was built (`docs/ROAD-CONSTRUCTION.md`):
     - rock cut 0.25:1 on the uphill side with a toe ditch;
     - fill 1.5:1 (hand-placed rock) on the downhill side;
     - each meeting the natural ground.
   - **Between stacked hairpin legs** (6.5–14.7 m apart vertically, ≥ 13.8 m apart edge to edge on
     the map), that section closes without walls. A 13 m drop fits in 11 m: 6.8 m of rock cut
     takes 1.7 m, and 6.2 m of fill takes 9.3 m.
   - **Walls only where the survey shows them**, or where the section genuinely cannot close.
     Those are labelled authored *(A3)*. The Register lists two walls on the climb; stone at every
     hairpin would fabricate National Register structures (L1).
   - Every ground point is seated to its own leg by station, never to the nearest surface (L4).
2. **Medium tier:** 15–20 m cells out to ~500 m.
3. **View tier (visual only):** 20–30 m cells out to ~3 km **on the north and east (view) side**.
   - It covers the Clear Creek mouth, Golden, Mount Zion and the M, North Table Mountain and Mount
     Galbraith.
   - At far-ring cells (60–100 m), a canyon a few hundred metres wide smears away, and ±0.5° at
     1.5–3 km is only ±13–26 m.
4. **Far tier (visual only):** real, unflattened 3DEP at 60–100 m cells.
   - It reaches at least 10 km west, south and north: Genesee, Mount Morrison, Mount Galbraith,
     North Table Mountain and the Clear Creek Canyon walls.
   - It is for looking at only: no physics, no GrassFX, and the gates never test it.
5. **East:** a coarse, nearly flat plains plane out to ~25 km.
6. **Between tiers:** no cracks. Shared tier boundaries coincide within 0.05 m or are skirted, and
   a seam check gates it.
7. **The Denver skyline** *(D6 ii)*: a low-poly skyline extruded from OpenStreetMap building heights
   for downtown Denver, at the measured bearing and distance. That is sourced, not invented, so L1
   allows it. Default yes, after Drive 2.
   - **Without it,** the view is the plains plus a night glow to the east.
   - **The distant peaks** (Blue Sky, Longs, Pikes) are not built. A coarse DEM sample of them would
     also be sourced; it can be added if Kevin wants it.

- **If D6(i) is declined:** tiers 3–5 and the skyline are not built, and L3's ±22 m band applies
  beyond the corridor. On a 505 m mountain that flattens the climb's views.
- **One more check:** AC/CSP must actually draw terrain at 10–25 km. That is confirmed in game in
  Drive 2, and the far tier is trimmed to what draws.

## 7. Atmosphere & light

- **Sun.** Latitude 39.73° N. At noon the sun stands about 74° high at the summer solstice and
  about 27° at the winter solstice.
  - The climb faces east/north-east, so **mornings light the switchbacks**, with the plains in haze
    below.
  - By late afternoon the sun drops behind the mountain. The east face goes into shadow first,
    while the back side and Paradise Rd stay lit.
  - True north is re-derived when the track moves to the loop frame (V3-PLAN P0) and written back
    to config. The sun direction is then checked in game.
- **Sky.** Semi-arid Front Range: clear mornings, and summer afternoon thunderheads building over
  the peaks to the west.
- **Presets worth shipping:** `morning` (the climb's money shot), `noon` and `golden_hour`, the
  three the config already lists.
- **Night: keep it honest.** The Lariat and the US-40 canyon are **dark**; there is no street
  lighting anywhere on the mountain.
  - **Gated since November 2024:** the Chimney Gulch → Lookout Mountain Park section (st
    ~1,074–7,680, 6.6 km of the lap) is shut to cars from an hour after sunset in summer and from
    7 pm in winter.
  - A real night drive there is no longer possible. A night drive is either a pre-2024 memory or a
    fiction; either way the mountain is dark. The gates are shown open.
  - **Kevin's July lamp call** and the V3 proposal to reverse it are in §5d *(D7)*.
  - What lights the night:
    - the street lamps of Golden, exit 259 and US-6 at Johnson Rd (§5d);
    - **the lit M** on Mount Zion (whether it is lit every night is unverified);
    - red aircraft-warning lights on the summit towers (type and colour come from the FCC
      registration; unverified);
    - Golden's street grid and the brewery below;
    - **Denver's glow** on the eastern horizon.
- **Lamp colour and era.**
  - OSM tags the nearby lamps as high-pressure sodium (HPS). Golden owns its streetlights (bought
    from Xcel); I found no record of Golden converting them to LED.
  - HPS is warm orange, about 2,000–2,200 K. Ledger 0043's HPS line is `255, 183, 76` with
    single-frequency 0.7.
  - Today the lamps are probably partly LED (3,000–4,000 K); unverified.
  - San Diego's low-pressure-sodium finding does **not** transfer here.
  - Whatever the colour, intensities are in the 255-scale range (0043). The installed `0.35` is the
    255× error.
- **The one photo that nails the mood:** not chosen yet; Kevin's pick. Candidate: the lower hairpins
  seen from Windy Saddle in morning light, with Golden and the plains below.

## 8. Asset plan — owned first

| Need | Owned / on-machine asset | Conversion notes | Placement | Or GAP → candidate |
|---|---|---|---|---|
| 1917 stone pylons | none | author in Blender from photos: two stacked-stone columns with an arch | st 0, both sides | stone texture: `assets/textures/stone_tan.png` (**its source is not recorded** in SOURCES.txt; check before public use), or a CC0 rough-stone set (ambientCG / Poly Haven) |
| Stone guardrails, sloping walls, low stone walls along the edge | none (only procedural `RETWALL`/parapet code inside the July engine pass) | a new authoring tool; dry-stone wall leaning back 1:6, low wall 0.5 × 0.4 m (ROAD-CONSTRUCTION table) | §5a / survey only *(A3, A4)* | CC0 dry-stone texture |
| Sensation Point concrete wall, summit concrete barrier | `concrete_barrier_4m.obj` (Kevin's Dropbox pack; licence `UNRECORDED`) | use as-is for the summit barrier; Sensation Point is authored | st ~2,225, ~7,219 | — |
| W-beam guardrail | no W-beam model owned (the type of Dropbox `Barrier02.obj` is unknown) | author it by sweeping the W-beam cross-section along the edge, posts every 1.905 m, with proper end pieces | survey + a rule for where a drop needs a rail | texture: `guardrail_diffuse/normal.png` is **mined from LA Canyons** (personal use only), so the public zip needs CC0 galvanized steel. The Dropbox US-signs pack carries `galvanized.jpg` (owned) |
| Rock cuts, outcrops | `rock_granite_red.png` (source not recorded); Dropbox `cliff.obj` (303 MB, must be simplified before use) | rock-cut faces as their own meshes | uphill edges, Wildcat Point | CC0 rock texture if the source can't be confirmed |
| C-470 overpass decks *(D5)* | none | author: deck slab + parapets at the real C-470 width and alignment, abutments meeting the 3DEP fills, piers outside the lap corridor | st ~19,300, ~21,100 | CC0 concrete: ambientCG Concrete034 (`_salvage/k10-sd-v021/assets/textures/`) |
| Arrow / chevron signs | W1-6 solids and `mutcd_w1-8l/r.png` chevron artwork (CC0, generated; MUTCD designs are public domain) | the existing `signs_mesh` / `make_sign_textures` | §5c rule | — |
| Speed-limit and advisory plaques, trail signs | Dropbox "US traffic signs pack" (OBJ + 57 sign JPGs) | fix scale, set Y-up, power-of-two textures | OSM-mapped positions (§5c) | generated MUTCD faces (public domain) |
| Street lamps (Golden cobra heads) | `lamp_post.obj` + `lamp_lens.obj` (Kevin's model: ~3k vertices, which AC counts as ~4k positions per lamp) | owned; check the arm matches a single-arm cobra head | §5d inventory only | a lower-detail version if the lamp budget bites |
| Buildings *(A9)* | OSM footprints + heights/levels | extruded low-poly (SD V3's method, ported into the underlay) | town stretches, ≤ ~150 m from the road | facade textures: the engine's `building_*` are **mined from Hamburg** (Full only); CC0 Concrete034 / ambientCG facades for the public zip |
| Denver skyline *(D6 ii)* | OSM building heights, downtown Denver | low-poly extrusions, one visual-only mesh in the backdrop kn5 | 19.6–23.2 km east, at the measured bearing | — |
| Race closures *(D3 a)* | Kevin's `concrete_barrier_4m.obj` silhouette, swept as strips (Lake Murray's race pattern) | the race kn5 | junction edges, Golden lane lines (§4c) | licence `UNRECORDED`, so Full-only, as on Lake Murray; a CC0 jersey profile would let it go public |
| Trees, shrubs | TreeFX `.bin` stand-ins (§6b) | Full package only | zones by slope direction (§6) | a true ponderosa, Douglas-fir, juniper and cottonwood |
| Ground | `grass_diffuse.jpg` (ambientCG Grass001, CC0) | — | corridor + medium tiers | CC0 tawny foothill grass / scrub ground *(D7)* |
| Road surface | `asphalt_cracked_*` (mined from LA Canyons; Full only); `aerial_asphalt_01` (Poly Haven, CC0; the public swap) | `tools/repack_kn5_textures.py` swaps them | all pavement | — |
| Towers, museum, lid park, pedestrian bridge | none | later passes | §5e | — |
| Power-line pylons | `pylon.obj` | **not used**: the July pylon line is unverified | — | — |

Rules:
- Owned assets come before purchases.
- Purchases come only from the GAP column, and only after an owned asset has been tried in game and
  found wanting.
- Nothing mined goes into anything that ships publicly (REALISM §3).
- **The live public zip breaks this today** (V3-PLAN *D0*). It binds:
  - LA Canyons `asphalt_cracked_*`, `ground_dry_diffuse` and `bushes_atlas`;
  - Hamburg `building_*`;
  - the TurboSquid-derived `conifer_atlas`;
  - `pine_tree.zip`'s pines;
  - the `UNRECORDED` barrier pack;
  - `stone_tan` (source not recorded).

  All of it ships under a CC0 claim.
- **A record to fix:** `assets/licenses.json` lists `building_*` as ambientCG Concrete034, while
  `SOURCES.txt` says those bytes were mined from Hamburg.

## 9. Data sources & capture assets

| Source | What | Date | Where |
|---|---|---|---|
| The retired twin's git history | 19 derived data files, incl. the centreline (8,319 pts, 24,941.8 m) and the full Overpass payload (2,493 ways, fingerprint 253170f584109f60). **Only the frame-free ones are restored** into `data/source-july/` (V3-PLAN P0): `osm.widths.cache.json`, `osm.ways.json`, `centerline.geojson`, `corridor.elev.json` (lon/lat stations), `environment.geojson` (reference only). Everything keyed to the July frame or July stations is regenerated | widths 2026-07-27T15:03Z; env 2026-07-20 | `k10-colorado` commit `0a897bb^`, path `tracks/lookout-lariat/data/`. Read with `git show`; never check out the retired repo. **This contradicts 0048's first claim that "no Overpass snapshot survives"; 0048 is corrected** |
| Overpass snapshot of the config's own query | 196 elements; reproduces the July lap exactly | 2026-10-11 16:45Z | scratch only (session temp). Python's TLS store rejects the Overpass certificate; curl works (P0 fixes the store, never by disabling verification) |
| USGS 3DEP 1 m | the elevation profile every 25 m, plus the sightline samples | 2026-10-11 | scratch only |
| Measured today on the recovered July data | the exit-259 wrong-way run (ways 42005706 / 119006778); the C-470 and tunnel crossings of the lap (§2e); the ≈145 ways touching the lap (§4b); the 1,188 stacked-leg pairs; the hairpin facets; the crossfall statistics | 2026-10-11 | session scratch; reproducible from the restored snapshot |
| The installed track | kn5 inventory (550.5 MB, 321 meshes, 19 textures), ext_config (304 lights), AI drafts (Aug 10) | built 2026-07-27 (engine v0.46.0) | `D:/SteamLibrary/steamapps/common/assettocorsa/content/tracks/lookout_lariat/` |
| The twin's `.blend` | **Engine output, not hand edits.** It has 0 collections, 0 text blocks and 0 modifiers, every object at an untouched position, and it was saved right after the 0024 barrier-winding commits on Aug 8 | 2026-08-08 | `k10-colorado/tracks/lookout-lariat/blender/`. Archive it (not delete; vertex-level edits can't be ruled out); there is nothing to salvage |
| KML | none needed: the whole lap is on the OSM road network | — | — |
| Owed | aerial imagery for widths, hairpin radii and C-470 clearances; a Street View / Mapillary pass for walls, rails, signs, lamps and kerbs; view/far-tier 3DEP samples (a live USGS fetch); 3DEP's source lidar for a crossfall check; OSM building heights for downtown Denver | — | — |
| Unknown | whether there are any Lariat drive recordings in Dropbox `/simracing` | — | check |

## 10. Location-specific QA — the look rows for Kevin's drives

**Drive 1 (road + ground):**
1. **Start:** the car sits on 19th St facing uphill, with the two stone pylons either side of the
   road ahead. The M is up and to the right, about 12° above eye level.
2. **Width:** drive both installs (*D4* A and B). Which feels like the real road and is still
   drivable?
3. **Base hairpin (st ~262):** on the fitted curve, does a normal car take it at a sane speed in
   both directions, without the 14 m widening *(A2)*?
4. **Every hairpin turns smoothly.** There are no flat facets or sudden steering steps through the
   turn.
5. **Lower and upper hairpins:** they read as stacked legs, and you see the road above and below.
   - Nothing between the legs floats, sags, or takes the other leg's height.
   - Between legs the ground is rock cut and fill, not a wall at every hairpin.
6. **US-40:** it descends Mt Vernon Canyon with **nothing beside it but the canyon** and I-70's
   empty graded shelf. No wavy ribbons, no floating decks.
7. **Exit 259:** the lap goes through on the north-east-bound side, with no kink and no wrong-way
   stretch.
8. **C-470, twice (st ~19,300 on Colfax, ~21,100 on US-6):** you pass under a bridge deck sitting on
   its abutments. There is no gap between two embankments, and no road on or along it *(D5)*.
9. **US-6 home:** one divided highway with its median *(D2)*, not two ribbons.
10. **Ramp → 19th St:** an ordinary left turn onto 19th St westbound, with no U-turn. The lid (st
    ~24,390) is level over US-6 with no bump at either end. 19th St still climbs to the pylons, and
    there is no jolt at the lap seam.
11. **No pavement anywhere except the lap** and the declared pieces: pads, mouths, stubs, the lid,
    the C-470 decks and the D2 slabs. Nothing is drawn in Clear Creek Canyon, and there are no
    sine-wave mountains.

**Drive 2 (+ edges, signs, trees, lamps, buildings, views):**

12. **Edges:**
    - stone guardrails with gaps wherever the survey puts them;
    - Sensation Point's concrete wall on rock;
    - W-beam only where it is real;
    - open dirt pull-offs where they are real;
    - no continuous generic barrier.
13. **Signs:** the real 20 mph limits and the advisory plaques at their hairpins. The authored
    arrows match the count Kevin approved. No sign floats over a drop or stands on the stone.
14. **Views:**
    - From Windy Saddle, Golden lies below (about −7°).
    - From Wildcat Point, the ground drops away into Clear Creek Canyon (about −12°), and the
      canyon reads as a canyon, not a smear.
    - From the lower hairpins up, the Denver skyline or glow appears to the east *(D6)*.
    - The far terrain actually draws at distance in AC/CSP.
15. **Golden:** the town stretches have their buildings. Signal junctions have their cross streets
    as stubs.
16. **Summit:** the towers stand just off the road at st ~7,190, and the pine woodland opens out.
17. **Night:** the mountain is dark. Lamps light only Golden, exit 259, Johnson Rd and 19th St
    *(D7)*.
18. **Trees:**
    - a bare lower east face;
    - patchy lower hairpins;
    - dense north-facing upper hairpins;
    - open pine woodland on top *(D7, item 5; the densest band instead if Kevin keeps his July
      call)*.

    No wall of trees, and no tree in the lane.

**Drive 3 (+ the layouts D3 settles on, four by default; AI):**

19. **Each layout spawns on its own grid, facing its own way.** Reverse's ui says it drives the
    divided stretches against the arrows *(D2a)*.
20. **Race layouts** *(D3 a)*:
    - the mountain road is open edge to edge, one-way, with nothing in it;
    - every side road is barriered at its edge;
    - the five turn corners are open boxes;
    - on Golden's multi-lane streets you have about Alvarado's width;
    - on US-6 and at exit 259 there is no way across to the other side.

## 11. Build plan (summary — the full plan is [`V3-PLAN.md`](V3-PLAN.md))

1. **P0:** fix Python's certificate store, then restore only the frame-free July data. Archive the
   twin's `.blend` and point the registry at airoso. Apply both route fixes *(A1)* and rewrite the
   July config (the layouts D3 settles on, the D7 knobs). Then add the one-way check.
2. **P1:** generalise the ship chain so a non-SD track can ship, race stages included, on the race
   tools Lake Murray's corridor run lands. SD's `ship_sd.sh` stays byte-identical. The prep fixes
   are the frame bug, balanced tiling and station-matched seating.
3. **P2:** draft route-only.
   - The hairpin fit runs first.
   - The engine's route, elevation, re-measured crossfall and spans feed a new underlay builder,
     `scripts/blender/underlay.py`.
   - The lid is declared from the tunnel footprint.
   - There is no environment stage, so there are no highways and no sine-wave mountains.
4. **P3:** author in Blender:
   - ground (cut/fill seated by station, the terrain tiers incl. the 3 km view tier);
   - the C-470 decks;
   - the junction mouths, side-road stubs and the lid;
   - pads where the measured width calls for one;
   - stone works and W-beam;
   - the divided slabs;
   - signs, TreeFX, lamps and GrassFX;
   - buildings, kerbs and sidewalks;
   - the race closures and open boxes *(D3 a)*.
5. **P4:** four layouts (two under *D3 b*) on 0047's per-layout machinery, with cameras and
   Content Manager images.
6. **P5:** the gates, with every number tagged [std] or [invented] by a stated rule, and a named
   Drive-1 set.
7. **P6:** Kevin's three drives.
8. **P7:** after T3, a Full zip kept local and a CC0 street-layout zip. *D0*, the live zip, comes
   first and separately.

**First question for the drive test:** does the climb drive like the real road (tight, narrow,
stacked hairpins at their real width and grade, turning smoothly), with nothing beside US-40 but
the canyon? And which edge, A or B?

## 12. What we don't know yet

| Unknown | Why it matters | How to find out |
|---|---|---|
| Run-by-run edge inventory (stone / W-beam / nothing) on the Lariat | it is the memorial-grade detail, and it drives the wall and rail authoring | Street View / Mapillary pass, st 0–7,700 |
| Pavement width and **radius** at each hairpin; width on 1a, 1c, 1d and Paradise Rd | the road's real width is the first thing a driver feels; the radius drives the hairpin fit | aerial measurement |
| Whether way 119006778 is the right exit-259 fix | A1 | aerial |
| C-470's clearance and deck width at st ~19,300 and ~21,100 | the D5 decks | aerial + Street View |
| The lid's exact footprint along 19th St | the level span | OSM tunnel ways + aerial |
| US-40's 3-lane split; what separates US-40 from I-70 | the cross-section of segment 3 | aerial + Street View |
| US-6, Colfax, 19th St and exit 259 median type and width | the D2 slabs | aerial + Street View |
| Whether the Colfax → US-6 turn is legal | the route *(D1)* | Street View |
| Arrow, chevron and advisory sign positions at each hairpin | the real sign set vs an authored one | Street View / Mapillary |
| Golden's kerbs and sidewalks on 1a and 19th St | A9 | aerial + Street View |
| Golden's lamp inventory and era (HPS vs LED) | the night look *(D7)* | Street View (including night imagery), Golden Public Works |
| Whether the M is lit every night; the tower lights' type | the night look | Colorado School of Mines; FCC antenna registration |
| The length restriction (30 ft vs 24 ft) | a sign plate | Street View |
| The spruce species at the Spring House; the streamside species on Mount Vernon Creek | the tree palette | field guides / site plant lists |
| Whether the July power-line run (st 20,600–24,000) exists | it is dropped unless real | aerial |
| Heritage Square's current state; whether Jeffco's proposed changes (rumble strips, new guardrail) are built yet | present-day accuracy | news / county posts |
| The Lariat's real crossfall | today's tilt is DEM-estimated, not measured | a 3DEP source-lidar sample (REALISM §5) |
| Whether AC/CSP draws terrain at 10–25 km | the far tier's size | in game, Drive 2 |
| The licences of `pine_tree.zip` and the concrete-barrier pack | D0's re-pack option; the race kn5's public release | Kevin's purchase records |
| The texture lists of the other five v0.14.0 Colorado zips | D0 | `gh release download` once `gh` is logged in |
| Lariat drive recordings | a reference for feel | Dropbox `/simracing` |
| The mood photo | §7 | Kevin |

## 13. Sources

- National Register nomination, Lariat Trail Scenic Mountain Drive (90001711): https://npgallery.nps.gov/NRHP/GetAsset/NRHP/90001711_text
- Jefferson County / Felsburg Holt & Ullevig, Lookout Mountain Road Corridor Study (Feb 2025): https://www.jeffco.us/DocumentCenter/View/49802
- Jefferson County, study open-house boards (Jul 2024): https://www.jeffco.us/DocumentCenter/View/45472/Lookout-Mountain-Road-Study-Open-House-Presentation-Boards-PDF
- Jefferson County, public improvement projects post (May 2026): https://www.jeffco.us/Blog.aspx?IID=283
- The Cultural Landscape Foundation, Lariat Trail Scenic Mountain Drive: https://tclf.org/landscapes/lariat-trail-scenic-mountain-drive
- Denver Gazette, gates and possible bike lanes (2024-08-23): https://www.denvergazette.com/2024/08/23/gates-possible-bike-lanes-changes-coming-to-mountain-road-in-colorado/
- 9News, Lookout Mountain closing after dark: https://9news.com/article/life/style/colorado-guide/lookout-mountain-closing-after-dark-illegal-activity/73-19854928-bb7a-4ba6-b2d7-25fddffb5166
- Visit Golden, mile-by-mile guide: https://www.visitgolden.com/blog/post/lookout-mountain-mile-by-mile-guide/
- Visit Golden, Lariat Loop byway: https://visitgolden.com/things-to-do/scenic-drives/lariat-loop
- CDOT, Lariat Loop byway: https://www.codot.gov/travel/colorado-byways/north-central/lariat-loop
- Wikipedia, Lariat Loop Scenic and Historic Byway: https://en.wikipedia.org/wiki/Lariat_Loop_Scenic_and_Historic_Byway
- Wikipedia, Lookout Mountain Park: https://en.wikipedia.org/wiki/Lookout_Mountain_Park
- Colorado Encyclopedia (staging), Lariat Trail Scenic Mountain Drive: https://encyclopediastg.exemplifi.io/article/lariat-trail-scenic-mountain-drive
- Golden Today, Cement Bill Williams: https://www.goldentoday.com/cement-bill-williams/
- Golden Today, the other pillars: https://www.goldentoday.com/the-other-pillars/
- Golden Today, Buffalo Bill's funeral (1917): https://www.goldentoday.com/a-memorable-funeral/
- Buffalo Bill Museum & Grave, park amenities: https://buffalobill.org/visit-us/park-amenities-and-things-to-do
- Mines Athletics, the M: https://minesathletics.com/facilities/?id=17
- Rocky Mountain PBS, Golden's Mount Zion M: https://www.rmpbs.org/news/education/golden-mount-zion-m-mines
- Scott Fybush, Lookout Mountain / Lake Cedar Group tower: https://fybush.com/site-20180202
- America's Transportation Awards, Linking Lookout (US 6 / 19th St): https://americastransportationawards.org/colorado-department-of-transportation-linking-lookout-us-6-and-19th-street-project/
- CDOT, US 6 traffic realigned in Golden (2016): https://codot.gov/news/2016-news-releases/07-2016/u-s-6-traffic-realigned-in-golden
- CDOT, US 40 resurfacing Genesee to CR 93 (2021): https://www.codot.gov/news/2021/may-2021/us40-genessee-resurfacing-begins
- CDOT, US 6 Golden Wildlife Crossing Mitigation Report (2020): https://www.codot.gov/programs/research/reports/other-reports/us6-golden-wildlife-crossing-mitigation-report-final.pdf/@@download/file/US6%20Golden%20Wildlife%20Crossing%20Mitigation%20Report%20FINAL.pdf
- Denver7, wildlife-migration technology on US 6: https://www.denver7.com/news/front-range/golden/technology-preserving-wildlife-migration-and-protecting-drivers-in-golden
- BusinessDen, Lookout Mountain night activity / Beverly Heights wall: https://businessden.com/?p=119302
- Schweich, Windy Saddle Park plant list: https://schweich.com/geoCOJefWindySaddlePark.html
- Schweich, Apex Park plant records: https://schweich.com/geoCOJefApexPark.html
- Colorado Birding Trail, Lookout Mountain Nature Center: https://coloradobirdingtrail.com/?p=913
- USGS NVCS, ponderosa pine / mountain mahogany woodland: https://www1.usgs.gov/csas/nvcs/unitDetails/686379
- Fort Collins Natural Areas, Colorado life zones: https://www.fcgov.com/naturalareas/mn-res-pdf/lifezones2014.pdf
- Boulder Reporting Lab, streetlights to LED (notes that Golden owns its lights), 2023: https://boulderreportinglab.org/2023/08/23/boulder-to-switch-all-streetlights-to-leds-aiming-for-energy-savings-and-starry-night-skies/
- BizWest, Xcel statewide LED streetlight plan: https://bizwest.com/?p=324202
- OpenStreetMap way 17070828 (Lookout Mountain Rd, closure note, 20 mph): https://www.openstreetmap.org/way/17070828
- OpenStreetMap way 1432442175 (base hairpin, 10 mph advisory): https://www.openstreetmap.org/way/1432442175
- OpenStreetMap way 533503210 (the ramp's left-turn branch: the route fix): https://www.openstreetmap.org/way/533503210
- OpenStreetMap way 533503214 (the ramp's right-turn branch: today's U-turn): https://www.openstreetmap.org/way/533503214
- OpenStreetMap way 42005706 (exit 259, south-west-bound one-way the July lap drives against): https://www.openstreetmap.org/way/42005706
- OpenStreetMap way 119006778 (exit 259, the north-east-bound partner: the fix): https://www.openstreetmap.org/way/119006778
- OpenStreetMap way 84720905 (C-470 bridge over US-6): https://www.openstreetmap.org/way/84720905
- OpenStreetMap ways 533503591 / 533679737 (US-6 under the 19th St lid): https://www.openstreetmap.org/way/533503591
- Overpass API (snapshot 2026-10-11 16:45Z of the config's query): https://overpass-api.de/api/interpreter
- USGS 3DEP Elevation ImageServer (1 m samples): https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer
- In-repo:
  - `docs/ROAD-CONSTRUCTION.md` (the Lariat construction table, the fill→wall trigger);
  - `docs/JUNCTIONS.md` (R18);
  - `docs/PUBLISHING.md` (the two variants);
  - `docs/RACE-FURNITURE.md`;
  - `assets/textures/SOURCES.txt` and `assets/licenses.json`;
  - `fleet/LAWS.md` (L1, L3, L3b, L4, L8, L10, L13);
  - ledgers 0003, 0010, 0025, 0037, 0040, 0043, 0044, 0045, 0046, 0047, 0048.

---
**Kevin's approval:** ☐ approved as-is · ☐ approved with the changes noted above — date: \_\_\_\_

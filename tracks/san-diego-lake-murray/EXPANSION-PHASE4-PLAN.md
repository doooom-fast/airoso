# Lake Murray network expansion: Phase 4 build plan (Waring to I-8, the ramps, I-8 drivable)

> **2026-10-14, revision 2. This is a plan only. Nothing is built.**
> - Ledger [0054](../../fleet/feedback/0054-lake-murray-network-expansion-waring-mission-gorge-jackson.md), section "The roadmap of Lake Murray phases", Phase 4. The place facts are in [`DOSSIER-EXPANSION-WEST.md`](DOSSIER-EXPANSION-WEST.md), §2b onward. Phase 3's plan is [`EXPANSION-PHASE3-PLAN.md`](EXPANSION-PHASE3-PLAN.md).
> - **Research** ran on 2026-10-14 and was read-only. It lives in the session scratchpad `p34/`, in five lenses plus a revision pass:
>   - **routes4:** the fresh OSM in the Phase 1 worktree (2026-10-14T10:13Z), plus one guarded Overpass fetch for waterways, rail, barriers and ramp meters (overpass-api.de, osm_base 2026-10-14T15:08Z, TLS verified). It also used 3DEP every 5 m and NAIP 2022;
>   - **terrain:** 3DEP 1 m, the grid and tile planner, and a skyline scan;
>   - **aerial:** NAIP 2022-04-25 at 0.6 m, with freeway cross-sections read by eye;
>   - **pipeline:** the chain file by file, and what a stacked road breaks;
>   - **routes3:** Phase 3's lens;
>   - **revise** (`p34/revise/`): after review, the gores and roads around the old west cut line, the I-8 chain stations of every ramp, the Alvarado Canyon Rd flyover's crossings, Mission Gorge Rd south of Zion, and the built-ground ratio.
> - **Stations and names.**
>   - On Waring south, stations are metres from J6 (Zion). The aerial's Waring stations run from J2, so subtract ~671 m to convert.
>   - On I-8, positions are given as longitude, and where needed as distance along the OSM carriageway chain (EB from −117.1146, WB from −117.0487).
>   - The three interchanges are **X8** (Fairmount Ave / Mission Gorge Rd, exit 8), **X9** (Waring Rd, exit 9) and **X10** (College Ave, exit 10).
>   - The freeway's ends are **END-W** and **END-E**. (Phase 1 already uses W1/W5 for its welds.)
> - **Words.** "Phase N" is your expansion phase. This plan's stages are **steps**.
> - **Order.** Phase 4 starts at Phase 3's Zion corner (J6), so its build waits for Phase 3 to be merged, installed and driven. A good deal can start much earlier (see each step and First moves). Most importantly, Step 1, the stacked-road rule, can start as soon as Phase 1's road build has landed, because it shares those files.
>
> Kevin, 2026-10-14, verbatim: *"And then phase 4 will be waring to 8, and we'll start working on freeway ramps. 8 will then go to college one way and mission gorge the other"*

## The short version

- **Your words, read phrase by phrase:**

  | Your words | What it is | Size |
  |---|---|---|
  | "waring to 8" | **Waring Rd south**, from J6 (Zion) down to I-8 at X9 | 1.59 km. It drops 62 m (99.7 → 37.8 m) at a steady 7–8 % through a canyon |
  | "freeway ramps" | the ramps that make your two trips work, at **X8, X9 and X10** | X9: all four (1.80 km); X10: the eastbound exit to College and the westbound on-ramps from College (~2.7 km); X8: westbound exit 8 and the two eastbound on-ramps from Fairmount (~1.2 km) |
  | "8 … to college one way" | **I-8 eastbound**, from the Fairmount on-ramps past Waring to exit 10 (College) | 2.85 km |
  | "and mission gorge the other" | **I-8 westbound**, from the College on-ramps past Waring to exit 8 (Mission Gorge) | 2.36 km |
  | (so it connects) | **Mission Gorge Rd south**, from J7 (Phase 3's Zion corner) down through Grantville to X8 | ~1.5–1.8 km (D2) |

- **Each direction of I-8 runs from where you can get on to where you must get off.** Past its last exit, a line of K-rail closes the lanes one by one, the way a real construction closure does, and steers you off; then a barrier. The pavement carries on beyond it, see-only, so the closure doesn't look like the end of the world. 65 mph, 4–6 lanes each way, concrete lanes, dark asphalt shoulders.
- **The big surprise: at Waring, I-8 is two roads at different heights.**
  - For about 1.9 km (−117.093 to −117.072) the eastbound side climbs the hillside and rides up to **18–18.8 m above** the westbound side, 37–64 m away, with a steep chaparral bank between them.
  - Waring Road threads between the two levels. It crosses **over** westbound I-8 on its own bridge, then passes **under** eastbound I-8's bridge, and ends at a signal just south of it. Alvarado Canyon Rd's curved flyover also passes over Waring and two of the ramps there.
  - Picture a parking garage: Waring is on the middle floor.
- **This is the first freeway the project has made drivable, and the hard part isn't the pavement.** The chain today knows nothing of three things:
  - **freeway lanes**: shoulders instead of sidewalks, a concrete median barrier, edge lines;
  - **merges**: a ramp joining a moving carriageway at a shallow angle;
  - **roads stacked on top of each other.** Every pass today asks "which road is nearest, looking straight down?". Under a bridge, the answer is the bridge. So the ground under a bridge gets pulled up toward the deck, and the final prep **deletes** any road with another road within 20 m above it as "buried". At Waring that would delete Waring under the eastbound bridge and westbound I-8 under Waring's.

  Most of this plan teaches the chain those three things, and proves it changes nothing on the roads you already have.
- **It ties into your loop at College Ave**: the eastbound exit lands on the loop's College Ave, and the westbound on-ramps start from it.
  - **Honest consequence of your words:** in this default nobody drives **under** the loop's College bridge. Eastbound is steered off at exit 10 just before the bridge, and westbound joins just after it. The freeway under the bridge is drawn, see-only. D1 gives the alternative that makes it drivable (carry on to the Lake Murray Blvd interchange).
  - About 16 ramp ends sit inside the Speedways' race zones (v791–976), and they are sealed like side streets. **Both Speedways keep their laps.**
- **Free Roam grows from ~28.9 km to roughly 43 km** [estimate].
- **Budget, honestly:** Phase 4 does **not** fit the 145 MB ceiling even with no new lamps: about 161–174 MB. With a lighter lamp on every lamp in the network, the fully lit network is ~127–140 MB, under the ceiling but close. **So the lighter lamp is a precondition of Phase 4, not an option.** The drivable ground roughly reaches ~910k points (2.5× today's). (See Budget.)
- **Two drives:** Drive 1 is the freeway, the ramps, Waring south, Mission Gorge south, the ground and **every structure that stands over a lane you can drive** (drivable or not). Drive 2 is lamps, signs, trees, buildings and the rest of the see-only scenery. Before Drive 1 there is one internal rehearsal, with the freeway as a non-drivable slab, to prove the stacked-road rule.

## Decisions for Kevin

**There are five questions, ordered by what they hold up.** Each default is complete, and the build goes ahead on the defaults if you don't answer. None changes a law. The JUNCTIONS amendment (merges, freeway ends) is a standards change, and it is shown to you with the Step 2 map.

| # | Question | Default | Why |
|---|---|---|---|
| **D1** | **Where does drivable I-8 stop?** | **Each direction stops at its last exit, by your words.** **Eastbound** is drivable from just east of the I-8 bridges over Fairmount (about −117.1000; you join from the two Fairmount on-ramps, which merge at −117.09949 and −117.09766) to exit 10 at College (−117.06985): **2.85 km**. **Westbound** is drivable from the College on-ramps' merge (−117.07262) to exit 8 at Mission Gorge (−117.0975): **2.36 km**. Past each last exit, a K-rail taper closes the through lanes and steers you off, then a barrier; past each start, a barrier stands behind you. Ramps that would only lead into a closure are closed at their street mouths with Phase 5 barrier stubs and drawn see-only: College's eastbound on-ramps and westbound exits, Fairmount's westbound on-ramps (they feed only the I-15 collector), and the eastbound collector road from I-15. **See-only pavement carries on ~500 m [invented] past each barrier on real ground**; beyond that only the ground keeps the freeway's shape. That is not v0.18.0's drawn freeway, which is OFF, and Drive 1 asks whether it reads right. | No barrier ends up near a gore nose. The first draft's single line at −117.1045 sat 32 m from the eastbound collector's split and 42 m inside exit 7B, and missed the 7B ramp. **The cost:** nobody drives under your College bridge, or over I-8's bridges at Fairmount. **Alternatives:** **East, to exit 11** (Lake Murray Blvd / Alvarado Rd, about +1.7–2.1 km each way): you drive under the College bridge both ways and the freeway meets your loop at both of its decks. It adds the Lake Murray Blvd ramps, 3 more ramp ends near the lap (v4433–4457) and a second stacked deck. **West, a straight cut at about −117.1053**, between the gores (≥ 91 m from each): you also drive eastbound over the Fairmount bridges, but westbound I-8, the 7B ramp and the westbound collector still have to be closed back to exit 8. It crosses 5 roads and 17 lanes and needs a 90-column grid. **West, to the I-15 decks (−117.1115):** a 104–105-column grid (+16–17), plus the I-15 stack's decks. **Holds up: Step 0's config and every count.** |
| **D2** | **Mission Gorge Rd from Zion south to I-8.** | **Drivable.** J7 → X8 is ~1.5–1.8 km (aerial: 1,473 m from Zion to Fairmount; to the X8 south ramp ends about 1.8 km). It is three roads in a row: divided one-way pairs for the first ~300 m (45–50 mph), with **Friars Road** (primary, 3+3 lanes, divided) at a signal cluster ~150 m south of J7; then 4–5 lanes undivided, 35 mph, 19.7–24.4 m, with signals at Rainier, Vandever, Twain and Mission Gorge Pl; then divided again from ~32.782 past old Fairmount Ave and the **Camino del Rio North / Alvarado Canyon Rd** junction, under I-8, becoming Fairmount Ave (trunk, 50–55 mph). Friars Rd gets two barrier stubs (one per carriageway). Fairmount Ave south of the X8 ramps gets a barrier stub. It runs 34.3 m → a sag at 23.2 m (s 458) → 28.3 m, max 5.1 %. | Without it, westbound exit 8 lands on a road you can't drive, and "mission gorge the other" never reaches the network. Cost: +25.4k planned physical points (~+48k built), +45k samples, ~+3–4 MB, and no extra grid columns. **Holds up: Step 0's route and samples.** |
| **D3** | **Alvarado Canyon Rd and its 392 m curved flyover.** It starts at an all-way stop on Adobe Falls Rd (node 49105019, 32.7829, ~80 m east of Waring; Adobe Falls Rd itself meets Waring at the signal at 32.7845). The flyover then sweeps south-west **over both Waring carriageways and two of X9's westbound ramps** and over Alvarado Creek, and runs about 1 km west beside westbound I-8, behind one concrete barrier, to the Mission Gorge Rd / Camino del Rio North junction (32.7802). | **Not drivable in Phase 4.** Its west mouth on Mission Gorge Rd and exit 8's short branch onto it get barrier stubs; its east end is on Adobe Falls Rd, beyond that street's own stub at Waring, so it needs nothing there. **The flyover is drawn see-only in Drive 1**, because it stands over four drivable pieces: its piers are placed from the built pavement, and the clearance, pier-in-lane and `drive_test` obstruction gates check it. The frontage road west of it is drawn see-only in Drive 2. | It is a ready-made surface link from Waring to Mission Gorge, worth promoting in a later phase once the stack is proven. Leaving the flyover out would remove a real overhead structure from Waring's descent. **Holds up: Step 2's scope.** |
| **D4** | **Lights on the freeway.** | **Interchanges only:** ramps, gores and ramp ends, not the mainline in between. **Only with the lighter lamp.** The positions stay *authored* until a Street View night check. | At today's lamp, lighting the freeway's full length is 257 lamps and **+51.7 MB**. Lighting just the interchanges is the usual pattern on this kind of urban freeway, but **it is not verified here**. **Holds up: Step 5 and the budget.** |
| **D5** | **The Green Line trolley viaduct.** It crosses over both directions of I-8 at about −117.096, inside both drivable stretches. It runs on a viaduct along the north side from Fairmount, past the elevated Grantville station (~−117.0975). | **See-only deck and piers, built with the Drive 1 decks**, every pier placed clear of the pavement. No station canopy yet. | You drive under it in both directions, so the gates must see it; leaving it out removes a real overhead structure. The station can come later. **Holds up: Step 4.** |

The far ring's west edge (−117.14) is decided in Phase 3 (its D2), because Phase 3 grows the ground for both phases.

### Defaults I will apply unless you say otherwise

- **A1. What is drivable.**
  - **I-8** per D1: eastbound −117.1000 → exit 10; westbound College on-ramps' merge → exit 8; plus the closure tapers and barriers.
  - **Ramps:**
    - **X9 (Waring):** all four. Eastbound exit (567 m), eastbound on-ramp (402 m), westbound exit (399 m loop), westbound on-ramp (428 m).
    - **X10 (College):** the eastbound exit to College north and south (293 / 294 / 354 m, climbing 94 → 107 m) and the two westbound on-ramps (838 and 924 m). College's eastbound on-ramps (508 m loop, 683 m) join I-8 at −117.0625, only ~230 m before the old east line and after eastbound's last exit, and its westbound exits leave at −117.06157, before westbound's start: both pairs are closed at their College mouths and drawn see-only.
    - **X8 (Fairmount / Mission Gorge):** westbound exit 8 (294–329 m, its own 22 m bridge) to Mission Gorge Rd; the eastbound on-ramp from Fairmount (436 m, 1 lane, two small bridges); the eastbound on-ramp from Fairmount south (505 m, 2 lanes) up to its fork, where the "I 8 West" branch (toward the I-15 collector) gets a barrier.
  - **Waring J6 → X9**, where Phase 3's stub at J6 and its slip-lane barrier come off.
  - **Mission Gorge J7 → X8** (D2), where Phase 3's stub at J7 comes off.
  - **Not drivable:**
    - Alvarado Canyon Rd (D3);
    - Friars Rd and Fairmount Ave south of X8 beyond their stubs;
    - the eastbound collector road from I-15, the westbound collector to I-15, exits 7A and 7B, and I-15 / CA-15 (see-only only within the ~500 m past END-W, then nothing);
    - the trolley (D5).
  - **Side streets** on Waring south (Orcutt Ave, Adobe Falls Rd, …) and Mission Gorge south (Friars Rd, Orcutt Ave, Rainier, Glacier, Vandever, Twain, Mission Gorge Pl, old Fairmount Ave, Camino del Rio North, …) get Phase 5 barrier stubs. Service drives get curb cuts (54 mapped service ways touch Mission Gorge south). The exact list is declared in Step 0.
- **A2. The freeway's cross-section.**
  - **Where the two directions run side by side** (centrelines 20–29 m apart west of Waring, 16–21 m east of −117.071), they are **one pavement with the concrete median barrier standing on it**. That is the same rule as every median here (JUNCTIONS rule 12), and it is how a real barrier median is built.
  - **The measured standard section** at aerial st 250 is 43.4 m edge to edge:

    | Element | Width (m) |
    |---|---|
    | WB outer shoulder | 2.4 |
    | WB lanes | 15.0 |
    | WB inside shoulder | 1.8 |
    | Barrier | 0.8 |
    | EB inside shoulder | 1.7 |
    | EB lanes | 16.7 |
    | EB outer shoulder | 2.2 |

    The barrier zone, with both inside shoulders, is 5.4–6.8 m.
  - **In the split-level stretch** (about −117.093 to −117.072), the two directions are **two separate roads with the real hillside between them**. The research's "median of the two chains" line runs at 22.2 % in places and is never driven. Where the pavement forks apart and rejoins, the gore follows JUNCTIONS rule 7.
  - **Lanes follow the measured concrete width where it disagrees with OSM.** Near College, OSM says 5 westbound lanes, but the concrete is 15.3–16.9 m: 4 lanes.
  - **Shoulders** are re-measured in Step 0. NAIP under-reads the dark asphalt.
  - **Edges:**
    - concrete lanes, dark asphalt shoulders, asphalt dikes at the outer edges;
    - **no sound walls**, because none exist here (none on the aerial, none in OSM);
    - the one concrete barrier between westbound I-8 and Alvarado Canyon Rd, from Fairmount to Waring;
    - guardrails only where the 0046 "rails over every drop" rule asks for them.
- **A3. Merges and diverges** (a new JUNCTIONS rule, drafted in Step 2). Picture a ramp as a lane that slides in beside you, not a road laid on top of yours.
  - The freeway owns priority and runs straight through.
  - The carriageway widens on one side into the extra lane (a parallel lane plus a taper).
  - The ramp butt-welds to that widened edge at the gore nose, and the gore is filled and painted with chevrons (rule 7).
  - The retired network builder's `_merge_taper` is **not** reused. It lays the ramp over the carriageway, which breaks rule 1.
- **A4. Ramp ends at street level are junction pads**, like Phase 1's corners. They are:
  - X8's ends on Mission Gorge Rd / Fairmount Ave;
  - Waring's south-end T with the eastbound ramps;
  - the westbound ramp ends at Waring;
  - the College ends on the loop (built ramps and stubbed ones alike).

  About 14 ramp-meter signals and the signalised ramp ends are painted stop lines, not working signals.
- **A5. Bridges are held at deck heights, never at bare-earth height** (L3: "bridges dip"), and every clearance in this plan means one thing:
  - **Clearance = the deck's underside (soffit) minus the road surface beneath it.** The soffit is the deck top minus **1.4 m** (`DECK_T_M`, `tools/author_bridges_blend.py:54`, the depth every bridge body here is built with).
  - **Deck tops** come from the 3DEP ground at both abutments, joined by a vertical curve. 3DEP is bare earth with the bridges removed, so the deck tops between abutments are interpolated, not measured, and they read low. **Where that leaves a soffit clearance under 4.9 m [invented, about 16 ft; Caltrans's design minimum for new work is 5.03 m], the deck is raised, never the ground under it lowered** (real ridges are never reshaped). The raise is blended into the approaches within the piece's grade cap, listed by name, and checked against Street View.

  | Deck | Length (m) | Deck top over road (3DEP interpolated) | Soffit clearance at that height | Expected action |
  |---|---|---|---|---|
  | I-8 EB over Fairmount / Mission Gorge (see-only in the default) | 55 + 33 | 5.3–5.5 m | 3.9–4.1 m | raise ~0.8–1.0 m |
  | I-8 WB over Fairmount / Mission Gorge (see-only in the default) | 52 + 35 | 5.4–5.6 m | 4.0–4.2 m | raise ~0.7–0.9 m |
  | I-8 EB over Waring's south end | 41–44 | 5.8 m | 4.4 m | raise ~0.5 m, inside the eastbound profile gate |
  | Waring over I-8 WB | 33 + 18 | ~6.3–7.0 m (abutments) | ~4.9–5.6 m | none expected |
  | Alvarado Canyon Rd flyover over Waring and two WB ramps (see-only) | 392 | unknown | unknown | Step 0 stack table |
  | X8 link decks | — | 4.3 / 5.2 m ± 1 | 2.9 / 3.8 m | almost certainly a bare-earth error; re-measured in Step 0 |
  | **The loop's College deck** (0046 BRIDGESTRUCT_1/2; freeway under it see-only in the default) | 96 + 97 | 6.61 m over EB, 7.26 m over WB | **5.21 / 5.86 m** | none: it stays as built |

  - Every new deck gets a bridge body, with piers placed from the **built** pavement so no pier stands in a lane (`_viaduct_struct`'s skip-column idea, the one transferable piece of the retired net).
- **A6. A drivable profile.**
  - Each carriageway gets its own height line from its own OSM chain and 3DEP. This reuses `tools/freeway_i8.py`'s planner, but with real vertical curves, deck stations kept, and a **6 % grade cap** [invented].
  - The real grades are: eastbound a steady 2.8–3.1 % from Waring to College; westbound up to 5.0 % in the split stretch; 0.2–0.4 % west of Fairmount; ramps up to 9.3 % (the College westbound on-ramp, under the 11 % connector cap).
  - A wobble gate counts grade reversals per km. Ledger 0048's wavy-ribbon failure measured 10.9 per km and 24.8 % grades.
- **A7. Ground.**
  - The grid is already 88 columns wide (Phase 3). Its west edge (−117.107285) is ~540 m west of the westernmost drivable road (Fairmount under I-8, ~−117.1015) and ~260 m past where the see-only pavement ends (~−117.1045). The real-ridges clamp stays at 20/40 m.
  - **The split-level bank is real ground from 3DEP.** Where the two carriageways' 20 m road zones overlap in a 25–40 m median, the clamp can't settle it: the 18.8 m rise is under the 22 m band. So Claude authors an earth bank (about 1:1.5) or a retaining wall there in Blender, like 0046's release zones (REALISM: lean in, never eject).
  - **Cut walls kept:**
    - Waring south's northbound side: cut 8.8 m within 20 m, and 22 m at 28–40 m (s 504–960);
    - the Waring eastbound off-ramp's cut, 9–12.6 m deep for ~250 m;
    - the College ramps' 7–8 m cuts and 7–9 m fills;
    - I-8's 4–8 m cut west of the College deck (−117.0680..−117.0667), now under see-only pavement.
  - **See-only pavement** past the barriers sits on the physical ground only. West of the grid edge, the far ring's 40 m cells and its I-8 ground corridor carry the freeway's shape as ground, with no pavement and no I-15 decks.
- **A8. The ends** (Phase 5 at freeway scale, with your K-rail module):
  - **Lanes heading toward a closure close one at a time, from the left, and steer you off at the last exit.** The length per closed lane follows the US merging-taper rule L = W × S: 12 ft × 65 mph = 780 ft, about **238 m per lane**. Closing 5 lanes is about **1.2 km**:
    - eastbound into exit 10 (5 through lanes; the 6th lane is the exit lane): the taper starts ~1.2 km before −117.06985, only ~120 m after the Waring eastbound on-ramp merges at −117.08373;
    - westbound into exit 8 (6 lanes; exit 8 is 1 then 2 lanes): the taper starts ~1.2 km before −117.0975, and the Waring westbound on-ramp (merging at −117.09064) joins on the right inside it.

    Because both tapers overlap a Waring merge, they close lanes from the left while the Waring ramp joins on the right. Step 2 designs them; the lengths are invented until then.
  - A barrier crosses the closed lanes just past each last exit's gore, then see-only pavement carries on.
  - **Starts** are barriers behind you: eastbound at ~−117.1000, westbound at ~−117.0726. No traffic approaches them, so a gore nearby is only a looks question.
  - **Ramp closures** at street mouths are ordinary Phase 5 stubs.
- **A9. The Speedways.**
  - Lake Murray Speedway and Speedway Reverse keep their laps, starts, AI and closures byte-identical.
  - **College's ramp ends near the lap:** 19 ramp ends lie within 20 m of the loop's pavement. 16 are in scope, at v791–976 (s 2361–2913), bracketing the deck at s 2548–2742. The other 3 are at v4433–4457, the Lake Murray Blvd interchange (only with D1's east alternative).
    - Each of the 16, built or stubbed, gets a mouth policy (`sealed_race_strip` or `behind_closure`) and a `no_route` probe placed **outside the deck's footprint**.
    - `trim_connectors`' left-turn island pocket is held inside race zones (island 134, closure 66), so `zone_by_vertex` and `lane_by_vertex` stay byte-identical.
  - The Mission Gorge Speedway (Phase 2) doesn't touch any Phase 4 road.
- **A10. No AI or traffic on the freeway.** AC's AI follows one line per layout, and lines are never generated from GPS. CSP's traffic lane graph (`scripts/ac/write_traffic_json.py`, "Highway" role, unwired, mainline only) is a later item.
- **A11. Signs:**
  - speed plates: 65 mph on the mainline; Waring south 35 / 40 / 45 mph; Mission Gorge south per OSM (45–50 mph at Friars, 35 mph through Grantville, 50–55 mph on Fairmount);
  - your 0044 corner arrows on the tight loop ramps;
  - painted gore chevrons; closure signs ahead of each taper.

  Overhead guide signs need text artwork and come later.
- **A12. Trees:**
  - chaparral and coastal sage scrub on the cut slopes and the split-level bank. The bank is 30–60 % dense shrub and 34–66 % scrub on the aerial: shrubs, not trees;
  - in the Waring canyon, 40–45 % canopy, with a tall-tree row on the east side at s ~630–780 (a eucalyptus candidate) and palms at s ~530;
  - **nothing in the freeway's clear zone.** Its width is set in Step 2 [invented].
- **A13. Buildings** within 120 m: SDSU's red-tile campus (SW of College), Del Cerro Tennis Club (on Waring), Home Depot, Norm Reeves Toyota, DCH Honda, and the Union Grantville apartments. Those apartments were under construction in 2022, so Street View is needed.
- **A14. The chain.**
  - The freeway is built in the **author stage, before the prep**, as drivable 1ROAD (see-only stretches unprefixed). Today's `author_freeway_blend.py` runs after the prep and is visual-only.
  - engine-july changes go through the engine-july-snapshot and the PENDING-MIRROR process.
  - Every step lands in `ship_sd.sh` and `ship_track.sh` together.
- **A15. Versions.** Drive 1 is the next minor version after Phase 3's. Drive 2 is a patch on it. Publishing is your click.

**Asked later, not now:**
- an overhead guide-sign pass;
- the Grantville station;
- promoting Alvarado Canyon Rd or Friars Rd;
- the east and west alternatives of D1;
- freeway traffic.

## Where it stands today

| | State |
|---|---|
| **I-8 in the installed build** | The 0046 terrain cuts a trench for I-8 under the loop's College and Lake Murray Blvd decks (BRIDGESTRUCT_1/2, openings 8.16 m and 8.55 m, built 1.4 m deep). The drawn see-only freeway (`tools/author_freeway_blend.py`, after the prep, visual-only) is **OFF** since v0.18.0. |
| **I-8 data** | `data/osm.i8.json` was clipped at −117.0895 east. `corridor.i8.json` covers only −117.09..−116.998: 180 m of the Fairmount–Waring stretch and 2,160 m from Waring to College. Its floor (the median of the two chains) runs at up to 22.2 %, with 56 grade reversals. |
| **Gates** | `kn5_ground_check` runs in **neither** `ship_sd.sh` nor `ship_track.sh` (only in `scripts/build.sh:112`), although LAWS L5 names it as one of the four abort gates. |
| **Phases 1–3** | Phase 1 is building (P0–P2 done on edd5096; P3 not run). Phase 2's lap tool and Phase 5's stub tool are in flight. Phase 3 is planned. |

## Steps

### Step 0 — Data and the stack table (no geometry). Can start now.

1. **Preconditions, for Step 4 only:**
   - Phase 3 merged, installed and driven (J6 and J7 exist);
   - the lighter lamp landed (Budget);
   - Step 1 merged.
2. **I-8 data rebuilt from the fresh fetch** for −117.1135..−117.040, as one-way chains per carriageway, collector and ramp, from `osm.expansion.json` plus routes4's extra fetch (`osm.extra.json`: waterways, rail, barriers, ramp meters). If the far ring moves to −117.14 (Phase 3's D2), the far-ring I-8 ground corridor is refetched west of −117.1146 too: about +15k see-only points.
3. **Append routes** to `data/routes.json`:
   - `freeway`: the drivable EB and WB stretches, the closure tapers, and the see-only continuations, marked as such;
   - `waring_s`: J6 → X9, both directions;
   - `mgr_s`: J7 → X8;
   - the ramps as named pieces, each marked drivable or see-only (A1).

   Every existing route stays byte-identical.
4. **The stack table: who is over whom, and at what height.** The **order** comes from OSM: each `layer=1` bridge crosses a `layer=0` road, never another bridge.
   - Waring 27056754 over I-8 WB 1010908005;
   - I-8 EB 27056788 over Waring 436607390;
   - Alvarado Canyon Rd 34539869 over Waring 159243459 and 159243460 and X9 WB ramps 5952893 and 5952897;
   - I-8 over Fairmount and a ramp; the trolley over I-8; College over I-8; exit 8's 22 m bridge; the eastbound Fairmount on-ramp's two small bridges; the X8 link decks.

   The **heights** come from 3DEP abutments, the clearance rule (A5) and Street View. Each crossing is written into the dossier with its deck top, soffit and clearance. (The College deck is known: 1.4 m deep, 5.21 / 5.86 m of clearance.)
5. **A dedicated aerial pass** for shoulder widths and lane lines near College. A Street View pass for ramp lanes, signals, the flyover's piers, and anything built since April 2022.
6. **3DEP:** Phase 4's tier samples on top of Phase 3's fetch (which already includes the −117.14 far edge): about **68.8k samples / ~153 requests**, plus **~45.1k / ~100** for Mission Gorge south (D2).
7. **Config:** `route.bbox` west to −117.107; `route_connectors.routes` gains the new routes. The grid is unchanged (88 columns since Phase 3).
8. **Stub declaration** for Waring south, Mission Gorge south (Friars Rd's two carriageways included), Fairmount south, Alvarado Canyon Rd's west mouth and exit 8's branch onto it, and the closed ramp mouths at College and Fairmount (`stub_roads.py declare`). The tool declares ramps `skip` by default; here each ramp is listed as built or stubbed per A1.

**Done when:**
- the new chains are within 1.5 m of OSM;
- the routes diff is clean;
- the stack table has every crossing, with its order from OSM and its heights from a named source;
- nothing installed has changed.

### Step 1 — The stacked-road rule (pipeline lens "4a"). Can start once Phase 1's road build has landed, on its own branch.

**In plain terms:** today every pass finds "the road nearest you, looking straight down". Under a bridge, that is the bridge. Step 1 changes it to "**the road at your own level**", one rule shared by every pass and gate. Where nothing is stacked, which is every road you have today, the answer is the same as before, and that is proven byte for byte.

1. **In the assembler** (`scripts-v021/blender/build_loop_blend.py`, `ribbon.py`):
   - `conform_terrain_to_road(target="nearest")` (ribbon.py:188–233; its own docstring says a grade-separated route needs "min");
   - `band_clamp` (:106–136);
   - the tiered-terrain kd-tree (:230–245, which also hard-codes "line 0 = the closed loop" at :232).

   `cut_i8_trench` (:443–465, half-width 16 m against the ±22 m freeway at College) is retired, because the freeway, drivable or see-only, grades its own ground.
2. **In the engine-july prep** (`build_kn5_loop.py`, through the snapshot and PENDING-MIRROR):
   - **BURY-CULL** (:843–873) learns layers instead of deleting any road face that has another drivable sheet within 20 m above it. Its undocumented `*_FW` exemption is replaced, not relied on.
   - the `_surf_z` pin (:832–842, :958–975);
   - `detect_bridge_spans` stops excluding motorways (:94–107), so I-8's own bridges are declared and the ground isn't filled up under them.
3. **In the gates:**
   - `drive_test` turns its layer window `top_at(y_ref, 2.5)` on under decks (:216–220) and takes `--line` per piece, one-way, with the entry speed taken from the piece before it or the posted limit;
   - `verify_mouths` reads the host deck at its own level (:270–273);
   - `no_route` probes sit outside deck footprints;
   - `audit_mesh` check A reads the built bridge bodies against the built freeway;
   - `kn5_ground_check` gets per-piece spans **and is wired into both chains**;
   - `author_bridges_blend` learns "a road passes beneath, with clearance" instead of exiting 1.
4. **Rehearsal:** the freeway as a **non-drivable slab** through X9 (Waring over WB, EB over Waring, the flyover over Waring and the ramps) and X8 (Fairmount under I-8's decks), plus the see-only pavement under the College deck.

**Done when:**
- on the installed network, every output is byte-identical and every gate key identical;
- on the rehearsal, every stacked road survives the prep (BURY-CULL removes 0 of their faces);
- the ground under each deck sits at the lower road's level, not the deck's;
- the clearance check reads 5.21 / 5.86 m at College.

### Step 2 — The freeway's readable intermediate (pipeline "4b")

1. **new `tools/author_freeway.py`** writes `data/expansion.freeway.json`:
   - one-way carriageways with **per-side widths** (lanes, shoulders, auxiliary lanes);
   - the barrier-median pavement where the directions run together (A2), and two roads with their fork and rejoin gores in the split stretch;
   - ramps with gore noses;
   - ramp-end pads;
   - every deck, with a datum per bridge way (**adapted** `tools/deck_datum.py`, generalised past the mainline) and any clearance raise (A5);
   - the closure tapers, barriers and starts (A8), and the see-only continuations;
   - the stubs;
   - Waring south and Mission Gorge south with widths and medians.
2. **The profile planner** (A6). It reuses `freeway_i8.py`'s chains, lane counts and 3DEP edge reads (its cross-slope hold, XSLOPE_MAX 0.08). It replaces the two 1-2-1 smoothing passes over 4 m (:51), and keeps the bridge stations it drops today (:15, :161).
3. **adapted `ribbon` / `route_connectors`:**
   - a piece **kind** (street, freeway carriageway, ramp, see-only), each with its own edge: shoulders and dikes, or curbs and sidewalks; a yellow left edge, a white right edge, dashed lane lines;
   - **asymmetric widths**, so an extra lane can widen one side;
   - a cross-section point at every lane line. Today it is 3 points, symmetric: a 25 m carriageway would be two triangles across;
   - width and grade cap per kind. Today they are a constant 10 m (:36) and 11 % (:37).
4. **JUNCTIONS.md amended:** the merge/diverge rule (A3) and the freeway-end rule (A8). GATES-CHANGELOG is amended in the same commit with the new gates (Verification).
5. **The numbered plan map over NAIP:** every lane, gore, deck, ramp end, taper, barrier and stub. You get it with the JUNCTIONS text.
6. **One interchange rehearsed end to end, on a scratch copy:** X9 Waring, the hardest, with its two drivable decks, the see-only flyover and the split level. It goes through draft → prep → every gate.

**Done when:**
- centrelines are within 1.5 m of OSM;
- the plan passes the profile gate (6 % or less; reversals per km);
- X9's rehearsal passes;
- you have the map.

### Step 3 — Ground over the freeway

1. **reused `terrain_tiers.py`** over the 88-column frame:
   - **561,074 lattice points** planned (physical 433,518, far 129,213 in the D2 box), or 586,405 with the far edge at −117.14; +25.4k physical for Mission Gorge south. These counts were planned for the full Fairmount-to-College pavement; the default's see-only stretches still get road-shaped ground, so they stand as an upper bound.
   - **Built, that is ~910k physical points (~955k with Mission Gorge south)**: v0.18.0's ratio of ~1.49 × (planned + refine), with ~54k refine for the freeway. The prep's recursive bisection at the 60,000 cap then makes **16–32 physical tiles** (16 average 57–60k, so some branches split again), against 8 today. The planner's "8 tiles, largest 55,236" is the plan lattice before refine and the prep. Every tile stays ≤ 65,535 by construction; far tiles stay at 4.
2. **The split-level bank** (A7): real 3DEP ground, with the authored bank or wall where the two road zones overlap.
3. **The cut walls** (A7), measured against 3DEP as in Phase 1.
4. **The College deck's release zone** (`college_i8_span`) re-checked now that I-8 has see-only pavement under it.
5. **Preview stills:**
   - Waring s ~1300, looking down the canyon toward I-8, with the flyover ahead;
   - eastbound at −117.0835, looking down at westbound 18 m below;
   - the eastbound closure taper approaching exit 10;
   - the X8 interchange from the exit 8 bridge.

**Done when:**
- seams have 0 open edges;
- every mesh is 65,535 points or fewer;
- the 0.05 m ground-unchanged check holds on the loop and Phases 1–3, except at named zones (the College trench and the J6/J7 arms);
- the bank holds 3DEP beyond 40 m from either carriageway.

### Step 4 — Road build → **Drive 1** (pipeline "4c")

1. **The freeway as 1ROAD in the author stage.** Reused from `author_freeway_blend.py` and moved before the prep:
   - the cut where ground meets slab;
   - the 1:1 batter;
   - the held verges;
   - `FAR_CUT_MAX`;
   - `split_oversize`.
2. **Merges and diverges** per the new JUNCTIONS rule. Ramp-end pads. Waring south welded at J6 and Mission Gorge south at J7, where Phase 3's stubs come off.
3. **Decks:** bridge bodies, piers from the built pavement, and the on-curb rails (`build_guardrails`, reused). **Every structure over a drivable lane is in this drive**: the drivable decks, the see-only I-8 decks over Fairmount, the Alvarado Canyon Rd flyover (D3) and the trolley crossing (D5).
4. **Barriers:**
   - the concrete median barrier as `1WALL`, double-sided;
   - the Alvarado Canyon Rd barrier;
   - the closure tapers, end barriers and starts (A8).
5. **Stubs and curb cuts** on the new streets and the closed ramp mouths.
6. **Paint:** lane lines, edge lines, gore chevrons, ramp-meter stop bars.
7. **The Speedway seals at College** (A9).
8. **`drive_test --line`** per piece, one-way, at speed.
   - Its step rule scales with speed, so at 200 km/h a 1.25 cm step counts as a bump. The freeway becomes the most demanding surface on the network.
9. **The gates** (Verification), including the new ones: clearance, freeway profile, layer check, `verify_merges`. `--force-install` is used only under 0047.

**What you see:** you can drive Waring down the canyon, under the flyover, over the westbound freeway and under the eastbound one, and take the ramps. Eastbound, you run the split-level hill and get steered off at College onto the loop. Westbound from College, you run back past Waring and come off at Mission Gorge, then back up Mission Gorge Rd through Grantville to Zion.

**Done when:** every Drive-1 gate passes and you have driven it. A DRIVE-TEST-REPORT is filed with the addendum's §10 rows.

### Step 5 — Dressing → **Drive 2**

- lamps (D4, lighter lamp);
- the rest of the trolley viaduct along I-8's north side;
- Alvarado Canyon Rd's frontage road, see-only (D3);
- signs (A11);
- trees (A12);
- buildings (A13);
- GrassFX tiles;
- the map.

**Done when:** the Drive-2 gates pass and you have driven it.

### Step 6 — Release

As `docs/PUBLISHING.md` sets out. Publishing is your click.

## Tool map

| Tool | Status | Change |
|---|---|---|
| fresh I-8 chains (from `osm.expansion.json` + `osm.extra.json`) | **new** data | replaces the clipped `osm.i8.json` for the freeway stretch |
| `tools/route_tracks.py` / `routes.json` | adapted | `freeway`, `waring_s`, `mgr_s`, ramps appended |
| `build_loop_blend.py`, `ribbon.py` | **adapted** | layer-aware conform, band_clamp and kd-tree; `cut_i8_trench` retired; piece kinds; asymmetric widths; lane-line points |
| engine-july `build_kn5_loop.py` | **adapted** (snapshot + PENDING-MIRROR) | layer-aware BURY-CULL, pin and spans; motorway bridges declared |
| `tools/author_freeway.py` | **new** | the freeway's readable intermediate |
| `tools/freeway_i8.py` | adapted | the per-carriageway planner with vertical curves, deck stations and a 6 % cap |
| `tools/author_freeway_blend.py` | adapted | moved before the prep; drivable 1ROAD; see-only past the barriers |
| `tools/deck_datum.py` | adapted | a datum for every piece and bridge way; clearance raises |
| `tools/author_bridges_blend.py` | adapted | a road beneath, with clearance; piers from the built pavement; see-only decks over lanes |
| `route_connectors`, `divide_connectors`, `trim_connectors` | adapted | piece kinds; caps per kind; island pocket held in race zones |
| `author_junction_pad_blend.py` | reused (Phase 1) | ramp-end pads |
| Phase 5 stub tools | reused | street and ramp-mouth stubs; adapted for the freeway taper and barrier |
| `docs/JUNCTIONS.md` | amended | merge/diverge; freeway ends |
| `drive_test` | adapted | per-piece one-way lines, entry speed, layer window on |
| `verify_mouths`, `no_route` | adapted | layer-aware host; probes off deck footprints |
| `verify_merges` | **new** | gore nose, single coverage over the taper, edge and cross-fall continuity, lane-line continuity |
| clearance, freeway-profile and layer checks | **new** gates | Verification V3, V2, V9 |
| `audit_mesh` check A | adapted | built bridge bodies vs the built freeway |
| `kn5_ground_check` | adapted + **wired** | per-piece spans; in both chains |
| `terrain_tiers.py` | reused | freeway tiers; the authored bank |
| `barrier_bands`, `verify_race` | reused | the 16 College ramp ends |
| `build_streetlights`, `make_treefx`, `place_signs`, `make_map` | reused / adapted | freeway pieces |
| `write_traffic_json.py` | not used | a later item (A10) |

## Budget

**Starting point:** Phase 3 as planned. That is **~135–142 MB** with no new lamps after Phase 1; ~169–177 MB with every road lit at today's lamp; ~95–102 MB lit with the lighter lamp.

**Ground is projected as in Phase 3's plan:** built ≈ 1.49 × (planned + refine), the ratio v0.18.0 shipped (357,262 built from 163,404 + 76,926), at ~56 bytes per built point.

| Phase 4 item | Points | Size |
|---|---|---|
| Freeway and ramp pavement, drivable and see-only (~14.5 km of carriageway plus ramps), ~9 bridge bodies at 0.32 MB | — | **+9 to +14 MB** (pipeline lens) |
| Physical ground | +93.9k planned (339,596 → 433,518) + ~54k refine; built **~+220k**, so ~910k physical | **~+12.3 MB** |
| Mission Gorge south (D2): road and ground | +25.4k planned; ~+48k built | ~+3–4 MB |
| Far ring | −26.8k in the D2 box, as physical ground takes over far cells; 154,544 total with the −117.14 edge | small |
| Structures over lanes (trolley crossing, flyover, see-only decks), barriers, tapers | small [estimate] | ~1–2 MB [estimate] |
| Freeway lamps, at most 257 (D4 default: interchanges only, counted in Step 2) | up to +1.04 M at today's model | **up to +51.7 MB**, or ~+5.2 MB with the lighter lamp |

**The road kn5, honestly.** The 145 MB ceiling is invented.

| After | No new lamps | Every road lit, today's lamp | Every road lit, the lighter lamp (~10×) |
|---|---|---|---|
| Phase 3 | ~135–142 MB | ~169–177 MB | ~95–102 MB |
| **Phase 4** | **~161–174 MB** | **~247–261 MB** | **~127–140 MB** |

- The pipeline lens's own figures (137–144 MB with no new lamps; 223–230 all lit; 103–110 lit with the lighter lamp) leave out the ground growth. The table adds it.
- **Even with no new lamps, Phase 4 is ~16–29 MB over the ceiling**, because the 239 loop lamps already weigh 47.9 MB. The lighter lamp on every lamp brings it back to ~127–140 MB: under the ceiling, but with little room. **It is a precondition.** If the built ground comes out at the top of its range, the next lever is thinning the kept-cell refine away from the roads.
- Points: the installed build has 1,697,179, of which the lamps are 966,725 (57 %). Physical ground grows from 357k today to ~910k built.

**Load time and frame rate. What we know and what we don't:**
- **No frame-rate number exists in this repo, and nothing here measures it.** Your "great" on v0.18.0 (116.3 MB, 244 CSP lights) is the only baseline.
- **The drivable ground grows ~2.5×** (357k → ~910k points, 8 → 16–32 tiles). It is collision mesh as well as drawn mesh [cost not measured].
- **The freeway changes what is in view, not just what is in the file.** From the eastbound side on the split-level hill you see the whole valley at once: two carriageways, three interchanges, the trolley, Grantville. More objects in view at once is likelier to cost frames than the file size is [not measured].
- **CSP lights:** ~414 after Phase 3, plus the interchange lamps (D4). The full mainline would take it to ~670.
- **AC loads the whole road kn5 for every layout** (L8), so both Speedways load the freeway too. If load time or frames suffer:
  1. the lighter lamp (already a precondition);
  2. ground decimation away from the roads, and mesh decimation of far pieces;
  3. a per-layout model list (AC's `models_<layout>.ini`) so the Speedways skip the freeway. That conflicts with JUNCTIONS rule 20 and the one-model rule, so it is a last resort and your call.
- **The proposal from Phase 3 stands:** load seconds and FPS at fixed spots, here adding X9 and the eastbound split-level hill, in every drive report.
- **Gate time:** about 17 km of new swept line (I-8 5.2 km one-way, ~5.7 km of ramps, Waring south and Mission Gorge south both ways ~6.4 km), so +1–2 min [estimate]. The terrain planner and export grow too.
- **Network:**
  - 3DEP: ~153 tier requests plus ~100 for Mission Gorge south;
  - one guarded refetch of the I-8 ground corridor west, if the far ring moves.

## Risks

1. **Stacked roads, the core risk.**
   - The prep's BURY-CULL would delete Waring under the eastbound bridge and westbound I-8 under Waring's bridge.
   - The conform pass would pull ground up toward each deck (at College, a ~6.8 m wall at the freeway shoulder).
   - `author_bridges_blend` exits 1 on a road beneath.
   - Mitigation: Step 1 first, proven byte-identical on today's network and rehearsed with a slab.
2. **engine-july is pinned.** Prep changes go through the snapshot and PENDING-MIRROR, and a mirror drift would ship a different prep than the one rehearsed.
3. **A wavy freeway.** The research's corridor floor runs at 22.2 % with 56 reversals, and 0048 measured the wavy-ribbon failure at 10.9 reversals per km.
   - Mitigation: a per-carriageway profile, the 6 % cap and the reversals gate.
4. **The split level.** Two road zones fight over a 25–40 m bank.
   - Mitigation: an authored bank or wall. The clamp is never stretched to iron it.
5. **Merges.** `verify_mouths`' span grows 10–29 times at 2–6° merge angles.
   - Mitigation: the new `verify_merges` and the JUNCTIONS rule, before any ramp is built.
6. **The closure tapers overlap the Waring merges** (eastbound taper starts ~120 m after the Waring on-ramp merge; the westbound Waring on-ramp joins inside the westbound taper).
   - Mitigation: lanes close from the left while ramps join on the right; `drive_test` sweeps each taper at 65 mph; Step 2 designs it before any build.
7. **Deck heights are interpolated, not measured.** At the abutment-interpolated heights, three decks give 3.9–4.4 m of soffit clearance.
   - Mitigation: the A5 rule raises the deck, never lowers the ground, lists every raise, and Street View checks them.
8. **The Alvarado Canyon Rd flyover is a fourth stacked case at X9**, see-only over four drivable pieces.
   - Mitigation: built in Drive 1 with piers from the built pavement; clearance, pier-in-lane and obstruction gates.
9. **College ramp ends inside race zones (16).**
   - Mitigation: policies and probes off the deck footprint; the island pocket held. Any byte change to `zone_by_vertex` fails V5.
10. **Budget.** Phase 4 is over the ceiling without the lighter lamp, and only ~5–18 MB under it with.
11. **`drive_test` at freeway speed** flags 1.25 cm steps at 200 km/h. Expect a long first fix list on the freeway.
12. **`kn5_ground_check` isn't in either chain today.**
    - Mitigation: wired in as the first move, on today's build.
13. **Data gaps:**
    - shoulders under-read on NAIP;
    - OSM and measured widths disagree on lanes near College;
    - one X8 deck reads 4.3 m (likely a bare-earth error);
    - the flyover's deck height is unknown;
    - the 2022 aerial predates the Union Grantville apartments.
14. **The default doesn't drive under your College bridge.** If that matters to you, D1's east alternative is the fix; it is cheaper to choose before Step 0.
15. **Free Roam's freeway is empty** (no AI). It is honest, but it is a change in feel. The traffic graph is a later item.
16. **Time.** This is the largest phase so far.
    - Mitigation: Steps 0–2 and the first move run long before Phase 3 lands.

## Not in this plan

- I-8 past exit 10 eastbound (the Lake Murray Blvd interchange) or past exit 8 westbound (the I-15 stack), except as D1's alternatives.
- Alvarado Canyon Rd and Friars Rd as drivable roads.
- Fairmount Ave south beyond its stubs.
- I-15 / CA-15, exits 7A and 7B, and the collectors to and from them.
- Freeway AI, CSP traffic, a freeway race layout.
- Working ramp meters and signals.
- Overhead guide signs with text.
- The Grantville station.
- Sound walls: none exist.
- Phase 5 proper: the old loop's side streets.

## Verification (decided now, before any geometry)

Everything runs on the **built** file (L5), against OSM, NAIP and 3DEP.

| # | Check | Threshold |
|---|---|---|
| **V1 Plan** | Centrelines vs OSM | p95 ≤ 1.5 m [invented] |
| | Freeway section at aerial st 250 | 43.4 ± 1.5 m edge to edge |
| | Carriageway separation in the split | 37–64 m |
| | Street widths at the aerial stations | ±1.5 m [invented] |
| **V2 Profile** | Built roads vs 3DEP, off the decks and their listed approach raises | p95 ≤ 0.5 m [invented] |
| | EB climb, Waring → exit 10 | 2.8–3.1 % ± 0.5 |
| | WB in the split | 5.0 % ± 0.5 |
| | EB above WB | 18.0–18.8 m ± 1 at −117.0835..−117.0843 |
| | Mainline grade | ≤ 6 % [invented] |
| | Reversals per km | ≤ the loop's rate [invented] |
| | Waring south | 7.0–7.9 % ± 0.5 |
| | Ramps | max 9.3 % ± 0.5 |
| | Spot heights | EB 39–40 m flat at −117.097..−117.090; WB crest 39.8 m at −117.096; WB sag 30.1 m at −117.0888; Waring's south end 37.8 m; each ± 1 |
| **V3 Decks** | **Soffit clearance** (deck top − 1.4 m − road beneath) over every lane of every drivable piece, under any deck, drivable or see-only | ≥ 4.9 m [invented] |
| | College (deck unmoved) | 5.21 / 5.86 m ± 0.2 |
| | Deck raises | every raise listed with its size; none lowers ground below 3DEP |
| | Piers | 0 in any lane (`audit_mesh` A), flyover and trolley included |
| **V4 Merges, pads, mouths, stubs** | `verify_merges` | PASS |
| | Pads | multi-coverage 0 m², seams ≤ 10 mm |
| | `verify_mouths`, `verify_stubs` | PASS |
| | End barriers | span every closed lane, edge to edge (S4) |
| | Tapers | each closes to its exit's gore; `drive_test` at 65 mph finds no obstruction ahead of the gore |
| **V5 Speedways** | `zone_by_vertex`, `closure_y_by_vertex`, `lane_by_vertex`, runs, pins, AI, spawns | byte-identical |
| | `mouths` | gains exactly the in-scope College ramp ends |
| | `no_route` | PASS, with probes off the deck footprints |
| **V6 Existing roads no worse** | all four gates on every layout | no key worse [std: 0047] |
| **V7 New roads** | `drive_test --line` per piece, one-way, at the posted limit | obstructions, floating and undrivable 0 [std]; severe steps 0 [invented] |
| **V8 Ground** | Bank | holds 3DEP beyond 40 m from either carriageway |
| | Cut walls (A7) | kept (Phase 1's rule) |
| | Low clause | holds |
| | Seams | 0 open |
| **V9 Layers** | BURY-CULL faces removed from any stacked road | 0 |
| | 1GRASS within a layer gap above a lower road under an upper one | 0 |
| **V10 Format** | Every mesh | ≤ 65,535 points |
| | Road kn5 | ≤ 145 MB [invented] |
| **V11 Dressing** | `verify_signs`, TreeFX checks | PASS |
| **V12 Your seat** | Two DRIVE-TEST-REPORTs | the only verdict that closes Phase 4 |

**Drive 1 is gated on V1–V10. V11 gates Drive 2.**

## First three moves after approval

1. **Now, independent of every phase:**
   - wire `kn5_ground_check` into `ship_sd.sh` and `ship_track.sh`, proven on v0.18.0's build. It closes an L5 gap on the roads you drive today;
   - take your load-time and FPS baseline on v0.18.0;
   - start the lighter lamp, which Phases 1, 3 and 4 all need;
   - your answer to D1 if you want to drive under the College bridge (the east alternative changes Step 0's counts).
2. **Step 0 on a branch:**
   - the fresh I-8 chains;
   - the stack table;
   - the shoulder and Street View passes;
   - the stub declaration.

   No geometry.
3. **Step 1 on its own branch, once Phase 1's road build lands:** the stacked-road rule, proven byte-identical on the installed network and rehearsed with the slab at X9 and X8. In parallel, the JUNCTIONS merge and freeway-end text and the freeway profile planner on a scratch copy. Step 4 starts once Phase 3 is installed and driven.

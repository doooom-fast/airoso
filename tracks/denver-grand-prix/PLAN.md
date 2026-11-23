# Denver Grand Prix — build plan

> **2026-11-23. A plan only: no geometry is built, no `track.config.json` exists yet, the track is not in the
> registry.** Written in a cloud session that could not reach Overpass or USGS, so **the route below is Kevin's
> list plus what is known of the streets, not yet read off OSM** — every unverified line says so. The mountain
> numbers in §3 are measured (plan-grade DEM, `source/horizon/`). Ledger:
> [0096](../../fleet/feedback/0096-denver-grand-prix-and-the-front-range-backdrop.md).
>
> Kevin's ask, 2026-11-23: *"Let's plan a new track, this one will be more complicated than the others and will
> likely need us to push what the system can do and use all of its techniques for the tracks so far all in one.
> This will be a Denver Grand Prix track."* · *"Both free roam and race course"* · *"Car starts facing west"* ·
> *"We need the mountains modeled in accurately, and we'll need those same mountains place accurately into sand
> creek."*

## Decisions for Kevin

**Eight questions. "Defaults" is a complete answer.** Ordered by what they hold up first.

| # | Question | Default | Why |
|---|---|---|---|
| **D1** | **Turn 2: Stout St runs under the Colorado Convention Center, not the Performing Arts Complex.** DPAC is the next complex north-west (Curtis / Champa, 13th to 14th St). Which did you mean: Stout under the Convention Center (the covered road with the light-rail station), or a street through DPAC? | **Stout, as you wrote it,** under the Convention Center. | Stout is the street you named and it is the one with a roof over it. To be confirmed on OSM (P0). |
| **D2** | **Turns 7–9, Kalamath.** Where is the hairpin: how far south of Colfax does the lap run before it turns back? And the lap comes back up the same street, so Kalamath is split down its length by a barrier, out on one side and back on the other. | **Hairpin at W 13th Ave** (about 200 m past Colfax), Kalamath split by a K-rail, hairpin around its end. | A hairpin right at Colfax's far kerb has no braking zone. I could not confirm from here where Kalamath meets Speer or whether it crosses Colfax at grade; P0 reads it off OSM and the aerial and comes back if the junction is not what the list assumes. |
| **D3** | **The lap drives several streets against their real one-way** (Stout north-east, the Kalamath return, possibly Blake). Race: no issue. Free roam: real directions, signs and paint as they stand? | **Race as listed; free roam as the streets are,** one-ways signed and painted as real, nothing enforced. | Lake Murray and Sand Creek both ship the free roam "as the roads are". |
| **D4** | **How much city does the free roam get?** | **The lap's streets, every street inside the lap, and one block outside it.** The count comes from OSM in P0; Sand Creek's free roam has 106 grid streets for scale. | Enough that every corner of the lap has its real cross streets to turn into; bounded so the kn5s stay in Lake Murray's size class. |
| **D5** | **Pit lane.** A street circuit has none; it is a design choice (`tracks/PIT-LANES.md`). | **None for Drive 1.** A grid on Colfax behind the Sherman crosswalk. A pit lane is proposed with the dossier (candidates: Colfax's north kerb lanes Grant to Lincoln, or Lincoln St beside the Capitol). | The grid is needed to race at all; the pit lane needs the measured widths first. |
| **D6** | **Mountains at their true distance and size (§3), one shared source for Denver, Sand Creek and later the Lariat?** The alternative is a shrunken ring a few km out, which is cheaper and wrong: the peaks slide against the city as you drive. | **True distance and size.** Shrunk only if AC cannot draw 105 km (P0 tests that first). | "Accurately" and "those same mountains" both mean one surveyed surface, placed by each track's own origin. |
| **D7** | **Sand Creek gets the mountains as its own point release, before Denver is drivable?** | **Yes: Sand Creek 0.2.9,** a backdrop kn5 added to both layouts, nothing else touched. | It is the first proof of the backdrop on a track you already know, and it does not wait on Denver's road. |
| **D8** | **Which Denver: today's streets, or the 1990–91 CART race's?** The real Grand Prix of Denver ran 1.9 miles around Civic Center; your lap is about three times that and is its own circuit. Today's Colfax east of Broadway is also mid-rebuild for the bus lanes. | **Today's streets, at the date of the lidar and the newest NAIP;** the dossier names the date per street. No 1990 furniture. | L1: build what the survey shows. A street under construction is built as the survey last saw it finished. |

## 1. Identity

- **Folder** `tracks/denver-grand-prix/`, **slug / install folder** `denver_grand_prix`, **name** "Denver Grand Prix".
- **Kind** `fictional_street_circuit`, **archetype** `street_circuit` (a racing loop invented on real streets, as
  Sand Creek). **Engine** `lm-v4` through the chain (`tools/ship_track.sh`, `docs/ONE-CHAIN.md`).
- **Layouts**, one shared road kn5 (L8):
  - `race` — the lap below, one way, barriers and kerbs, side streets sealed, grid behind the Sherman crosswalk;
  - `street` — free roam, the same roads open, plus the grid of D4.
- **Start/finish:** the crosswalk across Colfax at Sherman St, the Capitol's west steps on the driver's left.
  **The car faces west.**

## 2. The lap

Kevin's list, in order. "Known" is from general knowledge of the streets, **not from OSM**; P0 replaces this table
with measured legs (length, width, lanes, one-way, median, grade).

| # | Kevin's words | The road, as understood | To verify in P0 |
|---|---|---|---|
| Front straight | Colfax from Logan to the chicane around Civic Center Park | E Colfax west from Logan, past Sherman (S/F), Lincoln, Broadway, along the park's north edge. Falls about 20 m from Capitol Hill toward Speer. | median and bus-lane state (D8); width per block |
| T1/2 | park chicane | Colfax bows north around the Voorhies Memorial at the park's north end (Bannock to about 15th St) | the real kerb lines: left-right as built, no invented chicane |
| T2 | right onto Stout, curves under/through DPAC | from Colfax near Speer's east-bank carriageway, north-east on Stout under the Convention Center (D1). Light-rail tracks share the street. | where Stout actually leaves Colfax / Speer; the roof's extent and clear height; the rails |
| T3 | left onto 15th St | north-west on 15th, Stout to Blake (about seven blocks) | |
| T4 | left onto Blake | south-west on Blake | Blake's real direction (D3) |
| T5 | Blake slight right over the river | Blake's bridge over **Cherry Creek** (the creek in its walled channel between Speer's two carriageways; the South Platte is 600 m further on) | bridge deck from lidar class 17; the bend |
| T6 | left onto Speer | Speer's west-bank carriageway, south-east along the creek | |
| T7 | right onto Kalamath | D2 | where Speer and Kalamath meet; at grade or not |
| T8 | hairpin over Colfax back onto Kalamath the other way | D2 | the Colfax crossing: at grade, signals, rail |
| T9 | right onto Speer | Speer south-east again | that this is the same carriageway as T6 |
| T10 | left onto 14th | **W 14th Ave**, east past the Art Museum, the Library, the park's south edge and the Capitol's south side, climbing back up the hill (about 1.3 km) | not 14th *Street* (which the lap also crosses downtown) |
| T11 | left onto Logan | north on Logan, two short blocks | |
| T12 | left into Colfax | west onto the front straight | |

- **Length:** roughly 6 km, an estimate from block counts. Measured in P0.
- **Relief:** about 30 m. Plan-grade DEM: 1,617 m at Colfax / Sherman, 1,596 m at Speer / Colfax.
- **Self-crossing:** none expected, but the Kalamath out-and-back shares one street, and the lap passes within
  about 100 m of itself at Colfax / Speer / Stout on opposite banks of the creek. The race gate
  "no route to the other side" (`tools/no_route.py`) decides it on the built walls.

## 3. The mountains — measured

Method: the terrain skyline by bearing, from a car's eye (1.2 m) at three points, Earth curvature and standard
refraction applied. DEM: AWS Terrain Tiles zoom 10 (about 60 m cells), the one elevation host this session could
reach. **Plan-grade: re-run on 3DEP before any mesh is cut.** Script and numbers:
`source/horizon/horizon_study.py`, `source/horizon/horizon.plan-grade.json`.

**What the numbers say**

- **The whole Front Range stands 1.0–2.5° above the horizontal.** Highest: Mt Blue Sky (Evans), 2.38° from the start
  line, 2.47° from Speer / Colfax, 2.11° from Sand Creek.
- **The skyline is formed 20–100 km away,** median 42 km from the start line and 50 km from Sand Creek. Nothing
  nearer than 16 km contributes west of the city.
- **The arc that matters is bearing 180° to 335°** (Pikes Peak round to north of Longs Peak).
- **Pikes Peak is on Denver's skyline (1.14°, 100 km) and not on Sand Creek's** (hidden behind nearer ground on
  this DEM; to be re-checked on 3DEP).
- **A 12 m building 300 m away is as tall as the mountains.** Downtown they show only down the west-facing street
  canyons and across the open ground: Colfax from the Capitol (the start-line view), Speer, Kalamath, the Blake
  bridge, the Auraria side. The dossier lists each sightline with its bearing window, and a gate checks each one.

| Peak | From the start line (Colfax / Sherman) | From Sand Creek's origin |
|---|---|---|
| Pikes Peak | 182.9°, 100.2 km, 1.14° | 185.7°, 105.7 km, hidden |
| Mt Morrison | 248.5°, 21.5 km, 1.93° | 242.8°, 28.5 km, 1.46° |
| Mt Blue Sky (Evans) | 253.5°, 58.8 km, 2.38° | 250.6°, 65.5 km, 2.11° |
| Green Mtn (Lakewood) | 254.6°, 17.2 km, 1.46° | 246.1°, 24.0 km, 1.06° |
| Mestaaehehe Mtn | 261.2°, 44.0 km, 2.25° | 256.4°, 50.3 km, 1.95° |
| Grays / Torreys | 261°, 72 km, hidden behind Chief Mtn's ridge | 258°, 78 km, at the ridge line (Torreys just clear) |
| Lookout Mtn | 267.8°, 21.7 km, 1.67° | 257.5°, 27.7 km, 1.32° |
| North Table Mtn | 284.3°, 19.5 km, 1.03° | 269.2°, 24.2 km, 0.86° |
| James Peak | 281.9°, 61.5 km, 2.00° | 276.6°, 65.9 km, 1.85° |
| South Arapaho Peak | 299.3°, 64.9 km, 1.92° | 293.3°, 67.4 km, 1.85° |
| Bear Peak / the Flatirons | 312.9°, 36.1 km, 1.35° | 301.4°, 37.2 km, 1.34° |
| Longs Peak | 317.1°, 78.5 km, 1.65° | 311.7°, 78.7 km, 1.67° |

**What that forces on the design**

1. **One surveyed surface, not a picture.** Sand Creek's origin is 5.3 km east and 5.1 km north of the Denver
   start line. Evans moves 2.9° between them, Longs 5.4°, North Table Mountain 15°. A painted ring or a rotated
   copy cannot be right in both places; the same 3DEP surface placed by each track's origin is.
2. **Earth curvature is baked in per track.** At 100 km the ground sits 785 m below the observer's flat plane
   (about 680 m with refraction): two thirds of Pikes Peak's height above Denver. Each track's bake drops every
   vertex by its distance from that track's origin. So the kn5 differs per track; the source and the builder do not.
3. **Only what can be seen is meshed.** The bake keeps the cells in the union viewshed of the track's own roads
   (plus a margin), and drops everything behind a nearer ridge. Cell size follows distance: one screen pixel at
   60 km is about 60 m.
4. **Visual only.** No digit prefix, its own `<slug>_backdrop.kn5`, listed in every layout
   (the Lariat plan's backdrop tier, `tracks/lookout-lariat/V3-PLAN.md` "terrain tiers").
5. **L3 holds.** Far relief is data, never invented and never reshaped; the near ground keeps its construction-zone rule.

**The shared piece: `tracks/_reference/front-range/`** (new) holds the source heightfield, its provenance and the
bake config. Denver, Sand Creek and the Lariat each reference it. The Denver skyline (the towers from lidar and
OSM heights) is the second shared layer: it is the Lariat's D6 (ii) and Sand Creek sees it about 7 km to the south-west.

**Unknown, tested first (P0):** whether AC / CSP draws geometry 100 km out (far clip, depth precision, fog and
haze by distance). One test kn5: three walls at 25, 60 and 105 km, driven on the PC. If 105 km fails, the fallback
is a uniform shrink toward the track origin by the smallest factor that draws, with the parallax error it costs
stated in degrees for the lap's extremes, for Kevin to accept or not.

## 4. Every technique, and where it lands here

| Technique | Proven on | Here |
|---|---|---|
| OSM carriageways by id, real widths, junction pads | Sand Creek (0073, 0079) | the whole lap; the right carriageway of Speer, Colfax, Kalamath |
| Real elevation along the road, lidar crossfall | Sand Creek, Lake Murray | Capitol Hill's fall on Colfax and climb on 14th Ave |
| Bridge decks held between abutments, measured deck profile from lidar class 17 | Sand Creek's E 56th deck (0068) | Blake over Cherry Creek; any Speer / Colfax structure P0 finds |
| Free-roam grid: connectors, welded mouths, mouth returns | Sand Creek 0.2.3 (0079, 0086), Lake Murray | the D4 grid, about the same count on shorter blocks |
| Medians and islands from lidar and NAIP | Lake Murray | Speer's parkway medians, Colfax |
| Race corridor: barrier strips, closures, race kerbs, sealed mouths, the race gates | Lake Murray (0047 / 0049), Sand Creek round K | the whole lap; the Kalamath split is a closure on a shared street |
| Race furniture: start line, grid, paint | High Plains (0093) | Colfax at Sherman |
| Buildings: footprints, lidar heights and roof forms, class skins, `house_seat` | Lake Murray, Del Mar (0083), circuits (0094) | every block face the lap passes: the densest set so far |
| Bespoke landmarks | Exotics, Lake Murray | the Capitol and its dome, City and County Building, Voorhies Memorial, Art Museum, Central Library, Convention Center and its bear, the DPAC arch |
| TreeFX from NAIP crowns | Lake Murray, Sand Creek | Civic Center Park, Speer's trees, the Capitol grounds |
| Lamps, signs, name blades | Lake Murray, Sand Creek | signals at every junction are new in number |
| Lidar ground patches, retaining walls | Sand Creek round I | Cherry Creek's walled channel, the Convention Center's ramps |
| Far ground and terrain tiers | Lake Murray (0046), Milford (0082), Del Mar (0083) | the plains and the Platte valley out to the backdrop |
| Road wear, owned surfaces, no repeats | 0084, 0095 | concrete streets, brick crosswalks, the rails |

**What the system does not do yet** (each is a named piece of work, not a surprise):

1. **A road under a roof** (Stout under the Convention Center). `kn5_ground_check` and `drive_test` cast from
   above; a deck overhead must be declared and exempted the way a bridge span is, the reverse way round. Lights
   that are on by day; a covered-section entry in the AI and rain configs.
2. **Rails in the street** (Stout; the Colfax / Speer crossing). Visual first; a physics lip only if the survey
   shows one and Kevin wants it.
3. **A backdrop baked from a shared regional source** with curvature and a viewshed cull (§3), and its gate:
   for each named peak, bearing and altitude from the start line within 0.1° of the 3DEP value.
4. **Tall buildings.** The buildings chain has stood houses, sheds and grandstands; 200 m towers need a height
   source check (lidar first return against OSM `height`) and a facade class that does not tile visibly.
5. **A sunken, walled creek between two carriageways,** with paths and water at the bottom.
6. **An out-and-back on one street** in the race corridor (the Kalamath split).
7. **Signals** as furniture in the hundreds.

## 5. Phases

Each phase ends on its gates and a still or a drive; nothing claims a tier without its artifact
(`fleet/DEFINITION-OF-DONE.md`). Tiers per `CLAUDE.md`: authoring and diagnosis on the session model, mechanical
checks on `sonnet`, lookups on `haiku`.

| Phase | What | Where | Ends on |
|---|---|---|---|
| **P0 — facts** | OSM extract of the box (lap + D4), the lap resolved to way ids, **D1 and D2 answered from the map**; lidar (CO_DRCOG_2_2020) and NAIP tiles listed; `DOSSIER.md` filled from the template; the AC far-clip test (§3) | Mac for the data (it reaches Overpass and USGS); PC for the far-clip drive | Kevin approves the dossier; the far-clip result |
| **P1 — the backdrop, on Sand Creek first** (D7) | `tracks/_reference/front-range/`; the bake tool with curvature and the viewshed cull; `sand_creek_raceway_backdrop.kn5` in Sand Creek 0.2.9 | Mac builds, PC ships | the peak gate green; stills from Sand Creek's west-facing straights against a real photo; Kevin's drive |
| **P2 — Drive 1: the lap's road and ground** | config, `ship.json` (lm-v4), the draft through the chain: centreline, widths, elevation, crossfall, decks, the roofed section declared; `race` layout drivable with plain barriers; the Denver bake of the backdrop | PC | drive_test, audit_mesh, verify_kn5, kn5_ground_check; Kevin drives the lap |
| **P3 — the race** | corridor, closures, kerbs, the Kalamath split, start line and grid, AI draft | PC | the race gates incl. no-route; Kevin races it |
| **P4 — the city** | block massing from lidar for every face on the lap, then classes and skins; the landmarks one by one; the creek; trees; lamps, signals, signs | Mac authors, PC ships | `house_seat`, `houses`, textures; a still per landmark against its photo |
| **P5 — free roam** | the D4 grid through the junction steps; one-ways as real | PC | verify_mouths, drive_test street; Kevin drives it |
| **P6 — Lariat** | the same backdrop and skyline baked for the Lariat (its D6) | PC | its own gates |

P1 does not wait on P0's dossier approval, only on the far-clip result. P2 waits on the dossier.

## 6. Who does what

Seen 2026-11-23: the local sessions **Tracks:Mac** (waiting on an answer from Kevin about three tracks),
**Milford**, and **Finish the road-wear menu pictures**. The status board is the bridge on the G10; this cloud
session cannot reach it or the local machines, so it has asked Tracks:Mac to post this plan there and to run
P0's OSM fetch (the message is quoted in ledger 0096).

- **This cloud session:** the plan, the ledger entry, the horizon study; next, the dossier once the OSM extract
  is on the branch.
- **Mac (Tracks:Mac):** P0 data, P1's bake tool, P4 authoring.
- **PC:** every chain run, the far-clip test, installs.
- **Textures sessions:** the Denver surface and facade set joins their queue at P4; nothing is asked of them before.

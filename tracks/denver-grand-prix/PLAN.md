# Denver Grand Prix — build plan

> **2026-11-23. A plan only: no geometry is built, no `track.config.json` exists yet, the track is not in the
> registry.** The route in §2 **is read off OSM** (the Mac fetched the extract the same day); widths and grades are not yet. The mountain
> numbers in §3 are measured (plan-grade DEM, `source/horizon/`). Ledger:
> [0096](../../fleet/feedback/0096-denver-grand-prix-and-the-front-range-backdrop.md).
>
> Kevin's ask, 2026-11-23: *"Let's plan a new track, this one will be more complicated than the others and will
> likely need us to push what the system can do and use all of its techniques for the tracks so far all in one.
> This will be a Denver Grand Prix track."* · *"Both free roam and race course"* · *"Car starts facing west"* ·
> *"We need the mountains modeled in accurately, and we'll need those same mountains place accurately into sand
> creek."*

## Decisions for Kevin

> **DECIDED 2026-11-23 (Kevin): "defaults on all eight".** Every Default below stands: Stout under the Convention
> Center (D1); the Kalamath hairpin at W 13th Ave with the street split by a K-rail (D2), still to be confirmed on the
> map in P0; race as listed and free roam as the streets are (D3); the lap, everything inside it and one block outside
> (D4); no pit lane for Drive 1 (D5); mountains at true distance and size from one shared source (D6); Sand Creek
> 0.2.9 gets them first (D7); today's streets (D8).
> **Two changed the same day, both by Kevin's word given to Tracks:Mac and taken here on his say ("You should have
> answers for those from the mac agent"):**
> - **D2, the hairpin: "Use the real one-way route"** (his pick, 2026-11-23T01:47Z): Kalamath south across Colfax, left on
>   W 14th Ave, Santa Fe Dr north, the northbound Kalamath to Speer (§2 Finding 1). The 13th Ave split street is dropped.
> - **D7: "Mountains can be added to SC when Denver is done."** Sand Creek gets the backdrop after Denver, not first.
> - Confirmed by Kevin directly in the cloud session afterwards: "New hairpin is good" · "Sc mountains after Denver".
> - **Where the files live: "Its own bridge project: a dashboard and checks, files stay in airoso."**

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

## 2. The lap — read off OSM (2026-11-23)

Source: `source/osm.json` (Overpass, OSM as of 2026-11-23T01:12Z, fetched on the Mac on Kevin's "Download now").
Routed leg by leg on the named streets by `source/lap_route.py`; the way ids are in `data/lap_ways.plan.json`.
Frame: metres east / north of the Colfax / Sherman crosswalk. Lengths are along OSM's lines, before any smoothing.
Widths, kerbs, medians and grades are not read yet (the dossier, from NAIP and lidar).

| # | Kevin's words | The road on the map | Length | OSM lanes | Notes |
|---|---|---|---|---|---|
| Front straight | Colfax from Logan to the chicane | Colfax's westbound carriageway, Logan (x +218) past Sherman (S/F, x 0) to Speer's northbound side (x −1133) | 1,389 m (215 before the line, 1,174 after) | 2–4 | divided the whole way; the park bow is in this leg |
| T2 | right onto Stout, curves under/through DPAC | **two rights:** right onto Speer northbound for 151 m, then right onto Stout. Stout does not touch Colfax; it starts on Speer. | 151 m + 578 m | 5, then 2 | **Stout is covered for 344 m** (OSM `tunnel=building_passage`, `covered=yes`, `maxheight=5`), x −1148 to −925, ending 27 m before 14th St. That is the Convention Center (D1 confirmed). |
| T3 | left onto 15th St | 15th St north-west, Stout to Blake | 738 m | 2–4 | |
| T4–T5 | left onto Blake, slight right over the river | Blake south-west, bending west after 14th St onto its **39 m bridge over Cherry Creek**, into Auraria Pkwy to Speer's southbound side | 302 m | 2–4 | here both of Speer's carriageways are west of the creek |
| T6 | left onto Speer | Speer southbound, south-east to the Kalamath fork | 803 m | 4–5 | |
| T7 | right onto Kalamath | Kalamath leaves Speer at y +201, **north of Colfax**, and runs due south across Colfax at grade (x −1305) | 388 m to W 14th Ave | 3–4 | no bridge at Colfax: "over" is across |
| T8 | hairpin over Colfax back onto Kalamath the other way | **see the finding below** | 66 m + 189 m + 148 m | 3–5 | |
| T9 | right onto Speer | a hard right at the Speer / Stout / Kalamath junction (x −1247, y +123) onto Speer southbound, across Colfax | 342 m to W 14th Ave | 4–6 | joins Speer 80 m south of where T7 left it: no shared pavement |
| T10 | left onto 14th | W 14th Ave east: its 42 m bridge over Cherry Creek, the Parkway past the park, E 14th Ave past the Capitol | 1,365 m | 2–4 | |
| T11–T12 | left onto Logan, left into Colfax | Logan north, then Colfax west to the line | 180 m, then the front straight | 2 | |

**Lap: 6,639 m** on OSM's lines (the plan's estimate was "roughly 6 km").

**Finding 1, the hairpin (D2) — decided: Kevin, "Use the real one-way route".** The map shows
what "back onto Kalamath the other way" most likely is, and it needs no split street:

- Kalamath (one-way south) and **Santa Fe Dr (one-way north)** are a pair. South of Colfax they converge: 66 m apart
  at W 14th Ave, 20 m apart 125 m south of Colfax, 13 m apart 58 m south of it.
- North of Colfax, Santa Fe's northbound lanes carry on as a road OSM also names **North Kalamath Street**, 148 m
  north-east to the Speer / Stout junction. That is Kalamath "the other way", and the right onto Speer is at its end.
- So the hairpin as the streets exist: **Kalamath south across Colfax, left on W 14th Ave (66 m), left onto Santa Fe
  north, across Colfax, up the northbound Kalamath to Speer.** 180 m south of Colfax, all real pavement, nothing invented.
- A tighter turn-back nearer Colfax, where the two are 13–20 m apart, exists only if the aerial shows pavement between
  them. The dossier checks; if it is an island, building across it would be an invented road (L1).
- **Recommended: the W 14th Ave version above, in place of the accepted default** (13th Ave with Kalamath split by a
  K-rail, which the map shows is 358 m south of Colfax, not the "about 200 m" this plan said). The table and the
  6,639 m use the recommended version.

**Finding 2, direction (D3).** With that hairpin, **the whole lap runs with the real one-way direction of every
street: 0 m against traffic.** The free roam and the race drive the same way round; D3 has nothing left to decide.

**Finding 3, no self-crossing.** The lap uses Speer southbound twice, on two separate stretches (Blake to y +201,
then y +123 to W 14th Ave), and crosses Colfax's two carriageways three times at junctions it does not otherwise
use. It never shares or crosses its own pavement. `tools/no_route.py` still decides it on the built walls.

**Relief:** about 30 m (plan-grade DEM: 1,617 m at Colfax / Sherman, 1,596 m at Speer / Colfax). Real grades in P0's elevation step.

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

## 3b. If AC cannot draw the true distance — and what "look right" means either way

Playbox read the player's CSP settings without running AC: `[ADAPTIVE_CLIP_PLANES] FAR_PLANE=20000,30000`. Untested
prediction: nothing past 20–30 km draws. The skyline is formed 20–100 km out. Kevin, 2026-11-23: *"How can we fake
it"* · *"it needs to look right"* · *"not just be closer"*.

**Order of preference.** 1. Raise the far plane from the track's own config, if CSP allows it (the PC test finds
out): the mountains stay where they are. 2. Failing that, the pulled-in backdrop below. Either way the same six
things decide whether it looks right, and **moving the mesh closer supplies only the first.**

| # | What makes a far mountain look far | True distance | Pulled in | How it is kept |
|---|---|---|---|---|
| 1 | Bearing and height of every peak on the skyline | exact | exact from the lap's centre, drifting off it | the map below |
| 2 | **Layering:** near ridges slide against far ones as you drive | exact | lost on a single shell | pull in by a monotonic map, not onto one shell: 14 km stays 14, 105 km lands at 26 km, everything between keeps its order and its spacing in proportion (log of distance). Foothills still move more than the Divide. |
| 3 | **Haze:** contrast falls and colour goes blue with real distance | the game's fog does it, **but AC's fog is tuned for a few km and may swallow a 60 km peak whole** | the game fogs it as 20 km: too crisp | haze baked into the mesh's colour from each vertex's **real** distance; the backdrop taken out of the game's distance fog if CSP allows, so it is not fogged twice. Untested. |
| 4 | **Shading:** the sun models the real slopes | exact | squeezing depth flattens every face toward the viewer, so the game would light it as a wall | normals carried over from the real surface, not recomputed from the squeezed one |
| 5 | **Surface:** forest below, rock and snow above, by real elevation and aspect | same work either way | same | colour from elevation, slope and aspect of the real surface; snow line per season as a choice |
| 6 | **It answers the weather and the hour:** disappears in murk, silhouettes at dusk | free if 3 works | a baked haze does not change with the weather | the open risk. Needs CSP to drive the backdrop's fade from the weather; unknown until tried. |

**Measured cost of pulling in** (worst case anywhere on the lap, which reaches 1,087 m from its centre; error against the
true view; `source/horizon` peaks):

| Peak (true distance) | Single shell at 17 km: bearing error, size error | Layered map (14–26 km): bearing error, size error |
|---|---|---|
| Mt Blue Sky (58.8 km) | 2.06°, 3.4 % | 1.34°, 2.2 % |
| Longs Peak (78.5 km) | 2.35°, 4.8 % | 1.45°, 3.0 % |
| Pikes Peak (100.2 km) | 2.78°, 3.1 % | 1.64°, 1.9 % |
| Lookout Mtn (21.7 km) | 0.54°, 1.2 % | 0.59°, 1.3 % |
| Green Mtn (17.2 km) | 0.03°, 0.1 % | 0.38°, 0.6 % |

For scale, the whole range is 2.4° tall. The layered map halves the far peaks' error and keeps the layering; it is
the form to build if the far plane cannot be raised. A wider far plane (28 km in place of 20) shrinks every number.

**Acceptance is a picture, not a number.** For each named sightline (the start line down Colfax first), a still
from the game beside a real photograph from the same spot, same hour, clear and hazy. The peak gate (bearing and
height within 0.1° from the start line) only proves row 1. **Kevin's eye on the stills, then from the seat, passes
rows 2–6.** Reference photographs are a dossier item: dated, located, with the lens known.

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

## 4b. Streetlights, signs and paint — surveyed, and the build depends on them

Kevin, 2026-11-23: *"An addition I want for this track is streetlights and road signs that are as accurate as you
can make them. Same with road paint, we do a terrible job currently. Currently track builds don't depend on this."*

**What the chain does today** (read from the tools, not from memory):

| | Today | Why it is not accurate |
|---|---|---|
| Streetlights | `tools/plan_streetlights.py`: a post every 55 m along the lap, alternating sides, one fixture (`led_cobra`) | a rule, not a survey: no real post stands where it is drawn |
| Signs | W1-6 arrow plates at tight corners by rule (`tools/place_signs.py`), street-name blades; plates are flat colour, the arrow is geometry | no stop, one-way, speed, turn or guide sign exists; a sign face cannot carry artwork because the prep overwrites every mesh's UVs |
| Paint | the assembler paints from the centreline: double yellow, edges and dividers by width. Measured paint only as hand-declared exceptions (`route.paint`) | lane count, stop bars, crosswalks, arrows and bike lanes are not read from anywhere |
| Gates | lamps: one CSP light per lens. Signs: the arrow's own geometry. Paint: none | **nothing compares any of it with the street**, so a build is green with all of it wrong |

**What is on this lap** (counted on the OSM extract, the lap's 101 ways): **55 signals**, **108 crossings** (54 zebra,
43 signal-controlled), **5 rail crossings at grade**, 63 nodes where the lap meets another street, turn lanes tagged on 32
ways, bike lanes on 33, bus lanes on 6. Limits 25–35 mph. Surface asphalt with 13 concrete ways. All of it tagged lit.

**The rule: an inventory, then the build is held to it.**

1. **One inventory file per class** under `source/survey/`: `lamps.json`, `signals.json`, `signs.json`, `paint.json`.
   Every item has a position, a type, the source it was read from and a grade:
   - `measured` — its position read off lidar or an aerial (about ±0.5 m);
   - `detected` — found in street-level imagery, snapped to the kerb line (a few metres);
   - `tagged` — OSM says it exists at this junction; stood where the standard (MUTCD) puts it;
   - never `invented`. A stretch that was surveyed and has none says so (`"none": true`), so silence is not a pass.
2. **The chain authors only from the inventory.** No post every 55 m, no paint by width.
3. **Three new gates, on the built kn5 (L5), each fails the build:**
   - *present*: every inventory item is built within its grade's tolerance, right type, facing the right way;
   - *nothing extra*: nothing of that class is built that the inventory does not hold (L1);
   - *covered*: every metre of the lap and every junction on it has an inventory record or a declared none.
   The gate report states the share of each grade. That share is the honest answer to "how accurate".

**Sources, best first. What is not confirmed says so.**

| Class | Position | Type and face | Not confirmed |
|---|---|---|---|
| **Paint** | the aerial, read by the aerial engine (ledger 0088) that already measures edge lines at the sub-pixel boundary; lidar intensity as a second reading; OSM `lanes` / `turn:lanes` / `crossing:markings` to settle a count the picture leaves open | colour and pattern from the same picture; MUTCD dimensions for arrows, stop bars and crosswalk blocks | NAIP (0.3–0.6 m) shows crosswalks and stop bars but not a 10 cm lane line reliably. The region's 3-inch aerials (DRCOG's DRAPP) would; past years are said to be free from DRCOG's catalog, the current year is sold. **Which year we can get is P0's first check.** |
| **Streetlights** | lidar (CO_DRCOG_2_2020): a pole is a thin vertical cluster, its height read directly; the aerial's shadow as the check | fixture class per street from street-level imagery; one owned model per class (downtown has more than one: cobra heads, pedestrian globes) | the lidar is 2020: a post moved since is caught only by newer imagery |
| **Signals** | OSM's 55 nodes say which junctions; masts and arms from lidar and the aerial | mast-arm, pedestal and pedestrian heads as owned models | new furniture: none exists in the asset library |
| **Signs** | hardest. OSM gives the junction and the rule (stop, one-way, limit), not the post. Street-level detections (Mapillary publishes sign positions by class) give candidates; each is checked against a frame | MUTCD artwork is public domain and already drawn procedurally for W1 (`tools/make_sign_textures.py`); extended to the regulatory and guide set | Mapillary needs an access key and its licence read before anything from it ships. Without it, signs are `tagged` grade at best, plus whatever your own captures show. |

**Engine work this needs** (added to §4's list): 8. sign plates that keep their own UVs through the prep (it now
overwrites them; the note is already in `make_sign_textures.py`), so a face can carry its artwork; 9. the lidar pole
reader; 10. paint from an inventory in place of paint by width, on the junction pads as well as the ribbon; 11. the three gates.

**Targets for the lap's corridor** (the free-roam grid gets the same tools at a lower bar): paint 100 % `measured`;
streetlights and signal masts ≥ 95 % `measured`; every regulatory sign the lap's junctions require present, grade as the
sources allow. The numbers are proposals [invented] until the first survey shows what the sources give.

> **DECIDED 2026-11-23 (Kevin): "Defaults for e1-4".** Hard gates for Denver, opt-in elsewhere until proven (E1);
> signals modelled, lit steady at night, no cycle (E2); Mapillary first if its licence allows, and his own captures
> (E3); the race layout keeps the real paint, signs and lights, with the start line and grid added (E4).

**Four questions. "Defaults" is a complete answer.**

| # | Question | Default |
|---|---|---|
| **E1** | Are these gates hard for Denver only, or for every track from now on? | **Hard for Denver.** Offered to the others as an opt-in, and written into STANDARDS once Denver has proven them. Turning them on fleet-wide today would turn every installed track red. |
| **E2** | Signals: modelled and dark, or lit and cycling? | **Modelled, lit steady at night, no cycle.** A cycle is animation work with no gate; say if you want it. |
| **E3** | Street-level imagery for the signs and the fixture classes: a Mapillary key (you create it; I ask for it through the secure form, never in chat), your own captures, or both? | **Both, Mapillary first** if its licence allows shipping what is derived from it. |
| **E4** | The race layout keeps the real paint, signs and lights, as a real street race does, with the start line and grid added? | **Yes.** |

## 5. Phases

Each phase ends on its gates and a still or a drive; nothing claims a tier without its artifact
(`fleet/DEFINITION-OF-DONE.md`). Tiers per `CLAUDE.md`: authoring and diagnosis on the session model, mechanical
checks on `sonnet`, lookups on `haiku`.

| Phase | What | Where | Ends on |
|---|---|---|---|
| **P0 — facts** | OSM extract of the box (lap + D4), the lap resolved to way ids, **D1 and D2 answered from the map** (done, §2); the survey sources of §4b checked (which aerial year, the lidar tiles, the street-level key) and the first inventory of the lap; lidar (CO_DRCOG_2_2020) and NAIP tiles listed; `DOSSIER.md` filled from the template; the AC far-clip test (§3) | Mac for the data (it reaches Overpass and USGS); PC for the far-clip drive | Kevin approves the dossier; the far-clip result |
| **P2 — Drive 1: the lap's road and ground** | config, `ship.json` (lm-v4), the draft through the chain: centreline, widths, elevation, crossfall, decks, `tracks/_reference/front-range/` and the bake tool with curvature and the viewshed cull; the roofed section declared; **paint from the inventory** (§4b: paint is part of the road); `race` layout drivable with plain barriers; the Denver bake of the backdrop | PC | drive_test, audit_mesh, verify_kn5, kn5_ground_check; Kevin drives the lap |
| **P3 — the race** | corridor, closures, kerbs, the Kalamath split, start line and grid, AI draft | PC | the race gates incl. no-route; Kevin races it |
| **P4 — the city** | block massing from lidar for every face on the lap, then classes and skins; the landmarks one by one; the creek; trees; **streetlights, signals and signs from the inventory, held by §4b's gates** | Mac authors, PC ships | `house_seat`, `houses`, textures; a still per landmark against its photo |
| **P5 — free roam** | the D4 grid through the junction steps; one-ways as real | PC | verify_mouths, drive_test street; Kevin drives it |
| **P6 — Sand Creek, then the Lariat** (D7 as Kevin changed it) | the same backdrop baked for Sand Creek (`sand_creek_raceway_backdrop.kn5`, a point release, nothing else touched), then the backdrop and skyline for the Lariat (its D6) | Mac builds, PC ships | the peak gate; stills from Sand Creek's west-facing straights against a real photo; Kevin's drive |

P2 waits on the dossier and on the far-clip result. The backdrop is first built and driven on Denver (P2); Sand Creek's bake follows Denver (P6).

## 6. Who does what

Seen 2026-11-23: the local sessions **Tracks:Mac** (waiting on an answer from Kevin about three tracks),
**Milford**, and **Finish the road-wear menu pictures**. The status board is the bridge on the G10; this cloud
session cannot reach it or the local machines, so it has asked Tracks:Mac to post this plan there and to run
P0's OSM fetch (ledger 0096 "Coordination").

- **This cloud session:** the plan, the ledger entry, the horizon study; next, the dossier once the OSM extract
  is on the branch.
- **Mac (Tracks:Mac):** P0 data, P1's bake tool, P4 authoring.
- **PC:** every chain run, the far-clip test, installs.
- **Textures sessions:** the Denver surface and facade set joins their queue at P4; nothing is asked of them before.

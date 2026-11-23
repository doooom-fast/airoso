# Location dossier — Denver Grand Prix (`denver_grand_prix`)

> **First dossier, 2026-11-23, for Kevin's approval. No geometry is built.** Written from
> `fleet/templates/LOCATION-DOSSIER.md`. Every number here names the file it was read from; a section that the data
> does not yet fill says "unknown, will verify via X". The decisions (D1–D8, E1–E4) are answered and recorded in
> [PLAN.md](PLAN.md) and ledger [0096](../../fleet/feedback/0096-denver-grand-prix-and-the-front-range-backdrop.md);
> nothing here re-opens them.
>
> **What is measured in this file:** the route off OSM, the elevation along it (USGS 3DEP, 1 m cells), the lidar's
> coverage of it, which aerial years exist and at what resolution, and the mountains' bearings and altitudes on 3DEP.
> **What is not:** any width, kerb, median, pole, sign or paint line. Those are the survey this dossier's sources make
> possible; none has been read yet.

## 1. Identity & intent

- **Kind** `fictional_street_circuit`, **archetype** `street_circuit` (a racing loop invented on real streets, as Sand
  Creek). They agree (STANDARDS S6). Not yet in `fleet/registry.json`; no `track.config.json` exists.
- **Why this place** (Kevin, 2026-11-23): "this one will be more complicated than the others and will likely need us
  to push what the system can do and use all of its techniques for the tracks so far all in one." A lap from the
  Capitol's west steps down Colfax, under the Convention Center, through LoDo, along Cherry Creek on Speer and back up
  Capitol Hill on 14th Ave, with the Front Range standing where it really stands.
- **Layouts**, one shared road kn5 (L8): `race` (the lap, one way, barriers, sealed side streets, grid behind the
  Sherman crosswalk) and `street` (free roam: the lap's streets, every street inside the lap and one block outside it,
  D4). No surface fork.
- **Start/finish:** the crosswalk across Colfax at Sherman St. The car faces west.

## 2. Route geometry — facts, per segment

Source: `source/osm.json` (Overpass, OSM as of 2026-11-23T01:12:49Z), routed by `source/lap_route.py` into
`data/lap_ways.plan.json` (way ids) and `data/lap_line.plan.json` (nodes in driving order). `s` is metres from the
start line along OSM's lines. Heights and grades: `data/lap_profile.3dep.json` (§3), read from a 30 m running mean;
+ is uphill in the driving direction. **Lap 6,639 m. 0 m against any street's real one-way direction.**

| Segment | Roads | s (m) | Length | OSM lanes · limit | Height → height, mean grade | Kerb / sidewalk | Surface (OSM) | Notes |
|---|---|---|---|---|---|---|---|---|
| Front straight | E / W Colfax Ave westbound carriageway, Sherman → Speer northbound | 0–1,174 | 1,174 m | 2–4 · 30 mph | 1,606.2 → 1,590.4, −1.35 % | unknown, will verify via the 3-inch aerial and lidar | asphalt, some concrete | divided. The park bow (the "chicane") is s 260–420. Steepest part of the lap going down: §3 |
| T2 a | N Speer Blvd northbound | 1,174–1,325 | 151 m | 5 · 35 mph | 1,590.4 → 1,589.2, −0.8 % | unknown, same | asphalt | Stout does not meet Colfax; it starts on Speer |
| T2 b | Stout St, Speer → 15th St | 1,325–1,903 | 578 m | 2 · 25 mph | 1,589.2 → 1,591.6, +0.4 % | unknown, same; under the roof via Kevin's captures or street-level imagery (no aerial sees it) | concrete | **Covered s 1,386–1,730 (344 m)**: OSM `tunnel=building_passage`, `covered=yes`, `maxheight=5`: the Convention Center. OSM marks 5 rail crossings at grade on the lap (PLAN §4b); the extract holds no rail lines, so where the rails run is unknown, will verify via the 3-inch aerial outside the roof and captures inside |
| T3 | 15th St, Stout → Blake | 1,903–2,641 | 738 m | 2–4 · 30 mph | 1,591.6 → 1,582.5, −1.2 % | unknown, same | asphalt, concrete | bike lane tagged separate on the left |
| T4–T5 | Blake St → Auraria Pkwy, to Speer southbound | 2,641–2,943 | 302 m | 2–4 · 25–35 mph | 1,582.5 → 1,582.6 | unknown, same | asphalt | **bridge over Cherry Creek s 2,780–2,818** (OSM way 461500433, `bridge=yes`, layer 1) |
| T6 | N Speer Blvd southbound, Auraria Pkwy → Kalamath | 2,943–3,746 | 803 m | 4–5 · 35 mph | 1,582.6 → 1,588.5, +0.75 % | unknown, same | asphalt | Cherry Creek's walled channel on the driver's left the whole way |
| T7 | N Kalamath St south, across Colfax at grade (s 3,940), to W 14th Ave | 3,746–4,133 | 388 m | 3–4 · 25 mph | 1,588.5 → 1,591.1, +0.7 % | unknown, same | not tagged | |
| T8 a | W 14th Ave east, Kalamath → Santa Fe | 4,133–4,199 | 66 m | not tagged · 30 mph | 1,591.1 → 1,590.8 | unknown, same | not tagged | the hairpin's short side (D2: "Use the real one-way route") |
| T8 b | N Santa Fe Dr north to Colfax | 4,199–4,389 | 189 m | 3–5 · 25 mph | 1,590.8 → 1,589.9, −0.5 % | unknown, same | not tagged | 13–20 m from Kalamath's southbound lanes near Colfax; what lies between is unknown, will verify via the 3-inch aerial (L1: an island stays an island) |
| T8 c | the northbound road OSM also names N Kalamath St, Colfax → Speer / Stout | 4,389–4,536 | 148 m | 3 · 25 mph | 1,589.9 → 1,589.4 | unknown, same | not tagged | |
| T9 | N Speer Blvd southbound, across Colfax (s 4,659), to W 14th Ave | 4,536–4,879 | 342 m | 4–6 · 35 mph | 1,589.4 → 1,590.9, +0.5 % | unknown, same | asphalt | joins Speer 80 m south of where T7 left it |
| T10 | W 14th Ave, W 14th Ave Pkwy, E 14th Ave → Logan | 4,879–6,244 | 1,365 m | 2–4 · 30 mph | 1,590.8 → 1,611.0, +1.5 % | unknown, same | asphalt | **bridge over Cherry Creek s 4,888–4,930** (way 44932761). The climb of the lap: §3. Bike lane tagged separate on the right |
| T11 | Logan St north | 6,244–6,417 | 180 m | 2 · no limit tagged | 1,611.0 → 1,610.2, −0.4 % | unknown, same | asphalt | the lap's high point is the 14th / Logan corner |
| T12 | E Colfax Ave west, Logan → the line | 6,417–6,639 | 215 m | 2 · 30 mph | 1,610.2 → 1,606.9, −1.55 % | unknown, same | asphalt | |

- **Widths: none measured.** OSM carries no `width` on any of the lap's 101 ways. Unknown, will verify via the DRCOG
  2022 3-inch aerial (§9) with the aerial engine, checked against lidar. OSM lane counts are a prior, not a width.
- **Medians and islands** (Colfax's divider, Speer's parkway median, the Kalamath / Santa Fe wedge): unknown, will
  verify via the same aerial and lidar.
- **On the lap, from OSM** (PLAN §4b): 55 signals, 108 crossings, 5 rail crossings at grade, 63 nodes where the lap
  meets another street. Tagged, not surveyed.
- **Creek crossings:** two, both on bridges: Blake St and W 14th Ave. The lap crosses Colfax three times (on Kalamath,
  on Santa Fe / Kalamath northbound, on Speer southbound), each time west of the creek; **it does not use Colfax's own
  bridge over Cherry Creek, and Stout's part of the lap starts east of the creek and never crosses it.** The 3DEP
  profile agrees: bare earth leaves the road at exactly two bridges (§3).
- **Free-roam grid (D4):** not counted yet. Unknown, will verify via `source/osm.json` (it holds 3,827 ways for the
  box) once "inside the lap and one block outside" is drawn.

## 3. Elevation & drainage

**Measured: `data/lap_profile.3dep.json`** (script `source/elevation/lap_profile.py`): USGS 3DEP through the engine's
sampler (`scripts.elevation.usgs_3dep`), every 2 m along OSM's lines, 3,320 samples, **1 m cells on every sample
checked (133 of 133)**, fetched 2026-11-23. Bare earth, NAVD88, not smoothed in the file.

- **Relief 31.6 m:** highest 1,611.0 m at the 14th Ave / Logan corner (s 6,244); lowest 1,579.4 m is the creek bed
  under the Blake bridge; the lowest road is about 1,582.5 m at 15th / Blake (s 2,641). Road relief about 28.5 m.
  Start line 1,606.6 m.
- The plan's numbers (1,617 m and 1,596 m, from the 60 m tiles) were 10 m and 6 m high. These replace them.

**Colfax's fall from the Capitol** (cross streets from OSM, heights from the profile):

| Stretch | s (m) | Height | Grade |
|---|---|---|---|
| Sherman (the line) → Lincoln | 0–108 | 1,606.3 → 1,600.2 | **−5.6 %**, steepest 50 m −6.6 % at s 32 |
| Lincoln → Broadway | 108–217 | 1,600.2 → 1,597.2 | −2.8 % |
| Broadway → Speer | 217–1,174 | 1,597.2 → 1,590.4 | −0.7 %; low point 1,589.3 at Welton / Galapago (s 1,032), then 1 m up to Speer |

**14th Ave's climb:**

| Stretch | s (m) | Height | Grade |
|---|---|---|---|
| Speer → Bannock | 4,943–5,508 | 1,590.9 → 1,597.3 | +1.1 %; Delaware → Cherokee +2.1 % |
| Bannock → Broadway (the Parkway past the park) | 5,508–5,810 | 1,597.3 → 1,598.2 | +0.3 % |
| Broadway → Lincoln | 5,810–5,919 | 1,598.2 → 1,600.1 | +1.7 % |
| Lincoln → Sherman | 5,919–6,026 | 1,600.1 → 1,606.5 | **+6.0 %**, steepest 50 m +7.2 % at s 5,946 |
| Sherman → Grant → Logan | 6,026–6,244 | 1,606.5 → 1,609.4 → 1,611.0 | +2.7 %, then +1.5 % |

The start is a 5.6 % downhill launch and the last climb before the line is 6 %: both are the Capitol's hill between
Sherman and Lincoln, one block apart.

**Where bare earth is not the road** (3DEP against the lidar, `source/survey/lidar_coverage.json`):

| Place | What 3DEP does | What the lidar holds |
|---|---|---|
| **Blake St bridge** (s 2,784–2,814) | drops 4.2–5.1 m into the channel (1,584.5 at the abutments, 1,579.6 in the bed) | **class 17 (bridge deck) returns, 1.4 per m²,** 3.7–5.2 m above 3DEP's value: the deck is in the point cloud |
| **W 14th Ave bridge** (s 4,888–4,930) | drops 3.3–4.0 m (1,591.0 at the abutments, 1,587.0 in the bed) | class 17 returns, 1.1 per m², up to 4.1 m above 3DEP's value |
| **Stout under the Convention Center** (s 1,386–1,730) | a smooth line, 1,587.9–1,590.8 m, dipping 1.8 m to its lowest at s 1,560 | **no ground or deck return at all for 304 m (s 1,402–1,706).** Every return is the roof, 22–34 m up. 3DEP's line under the roof is interpolated between the portals, not measured |
| **15th St short of Lawrence** (s 2,284–2,316) | a 5.1 m pit, 30 m long, on the centre line | ground returns are thin here (under 2 returns per m² for s 2,240–2,328, between towers) and range from the pit's floor to street level. NAIP 2023 shows an ordinary street. **Read as a DEM artefact;** unknown until verified on the point cloud itself |

- So: the two bridge decks take their profile from lidar class 17 (the Sand Creek E 56th method, ledger 0068), not
  from 3DEP. Stout's road under the roof has **no elevation source from the air**; its two portals are measured (1,589.4
  m at s 1,390, 1,591.5 m at s 1,730). Unknown, will verify via Kevin's captures or a published section of the
  building; until then the only honest profile is the straight line between the portals, declared as such.
- **Colfax over Cherry Creek, and Speer's own structures:** not on the lap's centre line, so not in the profile.
  Whether any part of Speer the lap drives is on structure: the profile shows no departure from ground anywhere on
  Speer, and OSM tags no bridge there.
- **Drainage:** Cherry Creek, in a walled channel between Speer's two carriageways, bed about 4–5 m below the streets at
  both bridges; it runs north-west to the South Platte. Everything on the lap
  falls toward it. Gutters, inlets and crossfall: unknown, will verify via lidar (`tools/lidar_crossfall.py`).
- No invented banking: this is a street circuit (L10). Crossfall is whatever lidar shows.

## 4. Corner-by-corner character

Geometry is from §2. **Reference imagery, what defines each corner, and kerb reality are all unknown, will verify via
the DRCOG 2022 3-inch aerial, Mapillary if its licence allows (E3), and Kevin's captures.** Nothing below describes
what a corner looks like.

| # | Where | Known from the data | To verify |
|---|---|---|---|
| T1 | the park bow on Colfax, s 260–420 | Colfax bends north round Civic Center Park and back, 60 m of offset, nearly flat (1,596.9 → 1,596.3) | kerbs, the divider through the bow, sightline to the mountains |
| T2 | right onto Speer, right onto Stout, s 1,174 and 1,325 | two rights 151 m apart; 5 lanes into 2 | the Stout mouth, rails, the portal 61 m after the turn |
| under the roof | Stout, s 1,386–1,730 | 344 m covered, headroom tagged 5 m, a curve through it | everything: columns, lighting, kerbs, the rail position |
| T3 | left onto 15th, s 1,903 | 1,591.6 m, then 9 m downhill to Blake | |
| T4 | left onto Blake, s 2,641 | the low road point of the lap | |
| T5 | Blake bends west onto the bridge, s 2,769–2,832 | 39 m bridge, a 2 m rise onto the deck and off it | the deck joints, the crest |
| T6 | left onto Speer, s 2,943 | | |
| T7 | right onto Kalamath, s 3,746 | leaves Speer north of Colfax | |
| T8 | Kalamath → W 14th Ave → Santa Fe, s 4,133 and 4,199 | two lefts 66 m apart; flat (1,590.8–1,591.1) | whether the wedge nearer Colfax is pavement or island |
| T9 | hard right onto Speer, s 4,536 | at the Speer / Stout / Kalamath junction | |
| T10 | left onto W 14th Ave, s 4,879 | straight onto the 42 m creek bridge | |
| the hill | E 14th Ave, Lincoln → Sherman, s 5,919–6,026 | +6.0 %, then eases: a crest at Sherman | **blind crest? the drive test must say** |
| T11 | left onto Logan, s 6,244 | the lap's high point, 1,611.0 m | |
| T12 | left onto Colfax, s 6,417 | 215 m downhill to the line | |

## 5. Built environment & landmarks

- **Landmarks named in the plan:** the Capitol and its dome, the City and County Building, the Voorhies Memorial, the
  Art Museum, the Central Library, the Convention Center and its bear, the DPAC arch. Their footprints are in OSM;
  heights and roof forms: unknown, will verify via lidar (`tools/lidar_buildings.py`, `tools/lidar_roof_forms.py`).
  The lidar is there: along Stout the returns stand 22–34 m over the street (the Convention Center roof), and returns
  152 m above the ground were read within 15 m of 15th St's line.
- **Architecture stock per block face:** unknown, will verify via the 3-inch aerial, lidar heights and street-level
  imagery.
- **Signals, signs, streetlights, paint (PLAN §4b):** no inventory exists yet. OSM's counts are in §2. What each
  source can give, as measured today:
  - **DRCOG 2022, 3-inch (0.25 ft, 7.6 cm):** freely downloadable (§9). A 34 × 60 m window at the start line shows
    every lane dash, the double yellow, each crosswalk block, the stop bars, the signal mast arms with their heads,
    and lamp posts with their shadows. Leaf-off, so trees do not hide the street. This is the paint source and the
    position source for masts and posts. It is 2022: anything repainted since is caught only by newer imagery.
  - **NAIP 2023, 0.3 m:** shows crosswalk blocks, stop bars and lane dashes in the open at the start line; leaf-on,
    with long building shadows. Second reading, and the newest free date.
  - **Lidar, CO_DRCOG_2_2020:** **4.0 returns per m², 2.0 of them ground** (3.3 first returns per m²), one flight day,
    2020-05-27. At this density a lamp post is a handful of returns. It gives a post's height and confirms one the
    aerial shows; whether it can find posts unaided is unknown, will verify by running a pole reader on one block and
    counting against the 3-inch aerial. The plan's "≥ 95 % measured from lidar" for lamps should be read as "from the
    aerial, heights from lidar" until that is done.
  - **Signs:** as the plan says: OSM gives the junction and the rule, not the post. Unknown, will verify via Mapillary
    (needs a key and a licence read, E3) and Kevin's captures.
- **Fencing, hydrants, wires, bus shelters, the light-rail catenary on Stout:** unknown, will verify via the 3-inch
  aerial and street-level imagery.
- Furniture stands on true ground; the road comes down to the data (ledger 0029 §5).

## 6. Vegetation & terrain palette

- **Street and park trees** (Civic Center Park, the Capitol grounds, Speer's parkway): species and positions unknown,
  will verify via NAIP 2023's crowns (leaf-on, near-infrared band) and lidar (`tools/lidar_buildings.py --trees`).
- **Ground cover:** unknown, will verify via the aerials.
- **Backdrop: the Front Range, measured on 3DEP.** `source/horizon/horizon.3dep13.json` (script
  `source/horizon/horizon_3dep.py`): USGS 3DEP 1/3 arc-second, about 10 m cells, seven 1 × 1 degree tiles, bearing
  180–335°, rays to 112 km, eye 1.2 m, curvature with refraction 0.13. Against the plan-grade study:
  `source/horizon/horizon.compare.json`.

  | Peak | From the start line | From Speer / Colfax | From Sand Creek's origin |
  |---|---|---|---|
  | Pikes Peak | 182.8°, 100.2 km, 1.15°, clear by 0.29° | 182.1°, 1.16°, clear by 0.28° | 185.6°, 105.8 km, 1.05°: **see below** |
  | Devils Head | 190.6°, 54.3 km, 1.23° | 189.2°, 1.25° | 194.7°, 60.5 km, 1.07°: as Pikes |
  | Mt Morrison | 248.6°, 21.6 km, 2.03° | 247.3°, 2.20° | 242.9°, 28.6 km, 1.51° |
  | Mt Blue Sky (Evans) | 253.5°, 58.8 km, **2.44°** | 253.2°, **2.51°** | 250.6°, 65.5 km, 2.15° |
  | Green Mtn (Lakewood) | 255.3°, 17.0 km, 1.56° | 254.1°, 1.75° | 246.5°, 23.8 km, 1.11° |
  | Mestaaehehe Mtn | 261.3°, 44.0 km, 2.30° | 261.0°, 2.40° | 256.4°, 50.2 km, 1.98° |
  | Grays / Torreys | 261–262°, 72 km, hidden by 0.22° / 0.39° (Chief Mtn's ridge, 44–46 km) | hidden by 0.28° / 0.42° | 258°, 78 km: Grays level with the ridge (0.00°), Torreys clear by 0.11° |
  | Lookout Mtn | 267.3°, 22.4 km, 1.65° | 267.2°, 1.80° | 257.4°, 28.4 km, 1.29° |
  | James Peak | 281.9°, 61.5 km, 2.03°, clear by 0.10° | 282.1°, 2.10°, clear by 0.01° | 276.6°, 66.0 km, 1.87°, clear by 0.07° |
  | North Table Mtn | 286.2°, 19.2 km, 1.07° | 287.4°, 1.20° | 270.5°, 23.8 km, 0.86° |
  | South Arapaho Peak | 299.6°, 65.1 km, 1.95° | 300.1°, 2.01° | 293.6°, 67.5 km, 1.88° |
  | Bear Peak | 311.7°, 35.9 km, 1.42° | 313.1°, 1.49° | 300.2°, 37.2 km, 1.39° |
  | Longs Peak | 317.1°, 78.5 km, 1.69° | 317.8°, 1.73° | 311.7°, 78.7 km, 1.70° |

  - **What changed by more than 0.1° from the plan-grade table** (start line and Sand Creek, the two sites the plan
    printed): **Mt Morrison from the start line, 1.93° → 2.03°; Green Mtn (Lakewood) from the start line, 1.46° →
    1.56°.** No peak's visibility changed. Every other altitude moved by 0.07° or less, all upward (10 m cells hold a
    summit the 60 m cells averaged down). Three bearings differ by 0.5–2° (Green Mtn, North Table Mtn, Bear Peak)
    because the bearing is now to the DEM's own summit and not to the nominal coordinate; a mesa has no single summit.
  - **The skyline by bearing** (311 bearings): from the start line 6 bearings differ by more than 0.1° (largest 0.16°,
    at 272.5°), from Speer / Colfax 7 (largest 0.13°), mean +0.03° and +0.02°. From Sand Creek's origin 88 differ, 87
    of them because the skyline there is formed 300 m away (below).
  - **Pikes Peak from Sand Creek, settled as far as terrain goes:** the far terrain does not hide it. The highest
    ground between is at 66 km and Pikes clears it by **0.35°**. What hid it in the plan-grade study, and still does
    from the origin point, is **ground 8 m higher than the origin, 300 m to its south** (1,599 m against 1,590.4 m),
    which stands 1.29° high. Devils Head is the same story. So Pikes is in Sand Creek's backdrop mesh, and whether a
    driver sees it depends on where on that lap he is, which is a viewshed from Sand Creek's own roads, not yet run.
    The same bank forms 62 of Sand Creek's 311 skyline bearings.
  - Unchanged from the plan: the range stands 1.0–2.5° up, formed 20–100 km out (median 42 km from the start line,
    40 km from Speer / Colfax, 65 km from Sand Creek), arc 180–335°.
- **Per-sightline windows** (which street canyons show which peaks): unknown, will verify via a viewshed from the
  lap's own samples against building heights from lidar.

## 7. Atmosphere & light

- Latitude 39.74° N, 1,580–1,611 m. The lap's long legs run east–west (Colfax, 14th Ave) and on the downtown grid
  at 45° (Stout, 15th, Blake); the start faces west, into the afternoon sun and the mountains.
- True north, time-of-day presets, sky: unknown, will verify via the `lighting` skill once a config exists.
- The photo that nails the mood: unknown; Kevin's pick. A west-facing frame from the Capitol steps is the candidate.
- The covered section needs light by day (PLAN §4, item 1): unknown how CSP handles it, will verify in P2.

## 8. Asset plan — owned first

No asset has been chosen. Rows are needs, from §5–§6 and PLAN §4; every one is unknown until checked against
[`fleet/reference/ASSET-LIBRARY.md`](../../fleet/reference/ASSET-LIBRARY.md).

| Need | Owned asset | Conversion notes | Placement | Or GAP |
|---|---|---|---|---|
| Signal masts, pedestal and pedestrian heads | unknown, will verify via the asset library | — | from `source/survey/signals.json` (not yet made) | the plan says none exists: GAP, to be modelled (`bespoke-assets`) |
| Streetlight classes (cobra head, pedestrian globe, others the survey finds) | `led_cobra` exists (`tools/make_streetlight_led.py`); the rest unknown | — | from `source/survey/lamps.json` (not yet made) | likely GAP for each further class |
| Regulatory and guide sign faces | W1 arrows exist (`tools/make_sign_textures.py`); the rest unknown | plates must keep their UVs through the prep (PLAN §4b, engine work 8) | from `source/survey/signs.json` (not yet made) | MUTCD artwork is public domain: drawn, not bought |
| Tower facades that do not tile visibly | unknown | — | P4 | unknown |
| Landmarks (Capitol, City and County Building, Convention Center, the rest of §5) | none | — | P4, one by one | bespoke, each against its photo |
| Concrete street, brick crosswalk, rail-in-street surfaces | unknown, will verify via the owned-surface set (ledger 0084, 0095) | — | P2 | unknown |
| Trees | TreeFX from NAIP crowns (`tools/make_treefx.py`) | — | P4 | species unknown |

## 9. Data sources & capture assets

Large rasters and point clouds are **not in git**. Each row gives where it comes from, so any machine can fetch it
again; the cloud session that measured these kept them outside the repository and they are gone with it.

| What | Source | Date | Size | In the repo |
|---|---|---|---|---|
| OSM extract of the box 39.728,−105.010 to 39.756,−104.978 | Overpass (overpass-api.de), fetched on the Mac | OSM as of 2026-11-23T01:12:49Z | 1.9 MB | `source/osm.json` |
| The lap | routed by `source/lap_route.py` | 2026-11-23 | | `data/lap_ways.plan.json`, `data/lap_line.plan.json` |
| Elevation along the lap | USGS 3DEP ImageServer `getSamples`, 1 m cells | fetched 2026-11-23 | 3,320 samples | `data/lap_profile.3dep.json`; script `source/elevation/lap_profile.py` |
| Regional DEM for the mountains | USGS 3DEP 1/3 arc-second staged tiles, `rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/13/TIFF/current/<tile>/USGS_13_<tile>.tif`: n39w105, n39w106, n40w105, n40w106, n40w107, n41w106, n41w107 | files dated 2026-03-23 (n40w105), 2026-07-08 (n41w106), 2026-11-12 (the other five) | 365–426 MB each, **2.79 GB** | not in git. URLs, sizes and grid in `source/horizon/horizon.3dep13.json` under `dem`; result in the same file; `python3 source/horizon/horizon_3dep.py tiles <dir>` prints the fetch list |
| Plan-grade horizon (superseded, kept) | AWS Terrain Tiles zoom 10 | 2026-11-23 | | `source/horizon/horizon.plan-grade.json` |
| **Lidar** | USGS 3DEP `CO_DRCOG_2_2020`, public EPT `s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json` (39.4 billion points in the dataset) | **flown 2020-05-27** over the lap (one day, from GpsTime) | within 15 m of the lap: 141 nodes, **40 MB**, 5.9 M points in the nodes, 776,396 in the corridor | not in git. Coverage, density, classes and the four spots: `source/survey/lidar_coverage.json`; script `source/survey/lidar_coverage.py` |
| **NAIP 2023** | USDA FSA via Microsoft Planetary Computer (`tools/naip_crop.py`). **One scene covers the whole lap:** `co_m_3910417_nw_13_030_20230925_20240104` (its west edge is 13 m beyond the lap's line at Auraria Pkwy, so a corridor with margins needs the next scene too; `co_m_3910524_ne_13_030_20230925_20240104` overlaps it to the west, and `…3910409_sw…` / `…3910516_se…` start north of 39.7473° for the grid) | **2023-09-25**, **0.3 m**, 4 bands, leaf-on | 19,864 × 25,128 px per scene | not in git; crops are cut on demand |
| NAIP, older | same catalog: 2021 (0.6 m, 2021-07-28), 2019 (0.6 m), 2017, 2015, 2013, 2011 (1.0 m) | | | The newest year the catalog holds is 2023. USGS's own NAIP service is "primarily 0.6 m" |
| **DRCOG aerials (DRAPP), 3-inch** | the public bucket `drapparchive.s3.amazonaws.com`, one prefix per flight year. Tiles over the lap's centre line: **`N1E190c`, `N1W199b`, `N1W199d`, `S1E100a`, `S1E100b`, `S1W109b`** (`<year>/<tile>.tif` + `.tfw`), 0.25 ft pixels, 10,560 × 10,560, 4 bands, uncompressed, Colorado State Plane Central US ft (inferred from the world files) | **2022: downloads without an account** (as do 2020, 2018, 2016). **2024 (`2024/3inch/`, 5,783 tiles) is listed but every download is refused (403).** Day of flight within each year: unknown, will verify via DRCOG's metadata | 446 MB a tile, **2.68 GB for the six**; a corridor with margins will add neighbours | not in git. Tile list per year: `source/survey/drapp_tiles.json`; script `source/survey/drapp_tiles.py`. `source/survey/drapp_window.py` reads a window of a tile by HTTP range without downloading it (19 MB fetched for the start-line window) |
| Street-level imagery | Mapillary (E3) | | | unknown: needs Kevin's key and a licence read before anything derived from it ships |
| Kevin's captures | | | | none yet. The only source for Stout under the roof |
| KML | none: the lap never leaves the real road network | | | |

Hosts refused to the cloud session of 2026-11-23: `overpass-api.de` (the extract was already on the branch;
`overpass.kumi.systems` answered), `data.drcog.org` and `gis.drcog.org` (DRCOG's catalog and metadata), the NAIP
blob store behind the Planetary Computer (its data API answered, which is what `tools/naip_crop.py` uses), and The
National Map's product API. Nothing was stood in for them.

## 10. Location-specific QA

What the drive must confirm here, beyond the standard report. Each becomes a §Look row.

1. The launch down Colfax from the line reads as the Capitol's hill: 6 m of fall before Lincoln.
2. E 14th Ave, Lincoln to Sherman, climbs at 6 % and the crest at Sherman does not launch the car.
3. The Blake bridge and the 14th Ave bridge: no step at either joint, the creek visible below both.
4. Stout under the Convention Center: lit by day, no clipping overhead, no ground poking through, the rails where they are.
5. From the grid, facing west: Mt Blue Sky at 253.5°, 2.4° up, in the right place against Colfax's buildings.
6. The Kalamath / W 14th / Santa Fe hairpin drives as three real streets, not a U-turn.
7. Speer beside the creek reads as a parkway with a sunken channel, not a road beside a ditch.
8. Paint, signals and lamps at the Colfax / Sherman crosswalk match the 2022 aerial item for item.

More rows: unknown until the survey exists.

## 11. Build plan

As PLAN §5; nothing here changes it. What this dossier adds to it:

- **Before any mesh:** Kevin's approval below; the far-clip result (`source/farclip/README.md`, with the PC).
- **The survey comes first in P2** because paint is part of the road: fetch the six 2022 3-inch tiles (plus margin
  neighbours) on a machine that keeps them, register them to lidar, and read widths, kerbs, medians and paint with
  the aerial engine. Then lamps and masts from the same picture, heights from lidar.
- **Config deltas this place needs:** the two bridge spans declared with their class 17 deck profiles; the roofed
  span declared (PLAN §4 item 1) with its profile marked "between measured portals" until a capture replaces it; the
  15th St pit excluded from any ground the build takes from 3DEP.
- **Gates:** the four standard gates on the built artifact, plus §4b's three (present, nothing extra, covered) and the
  peak gate (bearing and altitude from the start line within 0.1° of `horizon.3dep13.json`).
- **Bespoke authorship in Blender:** the landmarks of §5, the creek channel, the Convention Center's underside.
- **First question to the drive test:** does the lap flow as a circuit at speed, start line to start line, before a
  single building stands?

**Open items this dossier could not close** (each has its "will verify via" above): every width, kerb and median;
the road under the Convention Center roof; whether lidar alone finds lamp posts at 4 returns per m²; the day of the
2022 flight; the sign inventory's source; the free-roam grid's street count; the Sand Creek viewshed for Pikes Peak.

---
**Kevin's approval:** ☑ approved as-is · ☐ approved with the changes noted above — date: 2026-11-23 ("dossier approved, start the survey")

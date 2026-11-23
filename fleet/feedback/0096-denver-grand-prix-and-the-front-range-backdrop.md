---
id: 0096
title: Denver Grand Prix — a new street circuit, and the Front Range modeled once for Denver and Sand Creek
status: open
scope: project:tracks/denver-grand-prix (new), project:tracks/sand-creek-lm (the backdrop), tracks/_reference/front-range (new, shared)
layer: project
train: -
---

# 0096 — Denver Grand Prix, and the Front Range backdrop

## The ask

Kevin, 2026-11-23: "Let's plan a new track, this one will be more complicated than the others and will likely need
us to push what the system can do and use all of its techniques for the tracks so far all in one. This will be a
Denver Grand Prix track." His lap, in his words:

- Front straight: Colfax from Logan to the chicane around civic center park
- Turn 1/2: park chicane
- Turn 2: right onto stout, curves under/through DPAC
- Turn 3: left onto 15th st
- Turn 4: left onto Blake
- Turn 5: Blake slight right over the river
- Turn 6: left onto Speer
- Turn 7: right onto kalamath
- Turn 8: hairpin over Colfax back onto kalamath the other way
- Turn 9: right onto speer
- Turn 10: left onto 14th
- Turn 11: left onto Logan
- Turn 12: left into Colfax
- Start finish: crosswalk at state capitol at Sherman across Colfax
- "Both free roam and race course" · "Car starts facing west"
- "We need the mountains modeled in accurately, and we'll need those same mountains place accurately into sand creek."

## State

**Planned and decided (defaults on all eight, Kevin 2026-11-23), nothing built.** The plan: [`tracks/denver-grand-prix/PLAN.md`](../../tracks/denver-grand-prix/PLAN.md).

## Evidence so far

- **The route is not yet read off OSM.** The cloud session that wrote the plan was refused by every Overpass
  server and by USGS (network policy). Two lines of the lap need the map before a centreline exists (PLAN D1, D2):
  Stout runs under the Colorado Convention Center, not DPAC; and where Kalamath meets Speer and crosses Colfax
  was not confirmed.
- **The mountains are measured, plan-grade** (`tracks/denver-grand-prix/source/horizon/`, AWS Terrain Tiles zoom 10,
  about 60 m cells): the Front Range stands 1.0–2.5° above the horizontal from both tracks, the skyline is formed
  20–100 km out, the arc is bearing 180–335°. Sand Creek's origin is 7.4 km from the Denver start line and the peaks
  move 3–15° in bearing between them, so one surveyed surface placed by each track's origin is the only form that
  is right in both. Curvature is 785 m at 100 km and is baked per track.

## Owed

1. P0 (PLAN §5): the OSM extract and the lap as way ids; the dossier; the AC far-clip test at 25 / 60 / 105 km.
2. ~~Kevin's answers to D1–D8.~~ **Answered 2026-11-23: "new project, defaults on all eight".** Every default in the plan stands; on the board Denver is a new project.
3. The horizon study re-run on 3DEP.

## Coordination

2026-11-23, sent from the cloud session to the local session Tracks:Mac (it reaches Overpass, USGS and the board),
after Kevin allowed the cloud session to message his local sessions. In substance:

1. Post a card on the board: "Denver Grand Prix: planned, 8 decisions waiting on Kevin, P0 (OSM + far-clip test)
   next". Which board project it sits under is Kevin's call, asked and not yet answered.
2. When free, fetch P0's OSM extract and push it to the branch:
   `python tools/fetch_osm.py --bbox 39.7280 -105.0100 39.7560 -104.9780 --service --out tracks/denver-grand-prix/source/osm.json`.

Tracks:Mac's reply, the same day:

1. **Done.** The board has the card: row `dgp-plan`, section "next", state "Waiting on you", machine Cloud, pointing
   at PLAN.md, this entry, the branch and draft PR 46. Its Luminescent Bridge project is noted as Kevin's call.
2. **Not done.** Every download on the Mac needs Kevin's own yes to that session, and Kevin told it today: "let's
   complete lake murray, sand creek, and high plains. let's pause on the rest for now". It has asked him.

So P0's OSM fetch waits on Kevin, and Denver sits behind Lake Murray, Sand Creek and High Plains unless he says
otherwise. P1 (the backdrop on Sand Creek) is Sand Creek work; whether it counts as "completing Sand Creek" is his call.

## The route, read off OSM (2026-11-23)

Tracks:Mac fetched the extract on Kevin's "Download now" (`tracks/denver-grand-prix/source/osm.json`, commit b7f35d8).
Routed on it (`source/lap_route.py`, `data/lap_ways.plan.json`; PLAN §2):

- **Lap 6,639 m.** Stout is covered for 344 m under the Convention Center (`tunnel=building_passage`, maxheight 5).
  Stout starts on Speer, not Colfax: turn 2 is two rights with 151 m of Speer northbound between them.
- **The hairpin:** Kalamath (south) and Santa Fe Dr (north) are a one-way pair that converges at Colfax, and the
  northbound road north of Colfax is itself named Kalamath. Kalamath south, left on W 14th Ave (66 m), Santa Fe north,
  the northbound Kalamath to Speer: all real pavement, and with it the whole lap runs with every street's real one-way
  direction. This differs from the default Kevin accepted for D2 (13th Ave, a split street); recommended in its place,
  his word owed.
- **D7 is open:** Tracks:Mac reports Kevin told it "Mountains can be added to SC when Denver is done"; here he took
  the default (Sand Creek first). His word owed.

## Streetlights, signs and paint (Kevin, 2026-11-23)

"An addition I want for this track is streetlights and road signs that are as accurate as you can make them. Same with
road paint, we do a terrible job currently. Currently track builds don't depend on this."

Planned in PLAN §4b: a surveyed inventory per class (lamps, signals, signs, paint), every item graded measured /
detected / tagged and never invented; the chain authors only from it; three new gates on the built kn5 (present,
nothing extra, covered) that fail the build. Today the lamps are a post every 55 m by rule, the only signs are W1-6
arrows and name blades, the paint is drawn from the centreline by width, and no gate compares any of it with the
street. On the lap: 55 signals, 108 crossings, 5 rail crossings at grade. Four questions (E1–E4) are with Kevin.

## Kevin's answers through Tracks:Mac (2026-11-23)

Kevin to the cloud session: "You should have answers for those from the mac agent". As Tracks:Mac reported them, his words:

- **The hairpin:** "Use the real one-way route" (his pick on the Mac's open-calls page, 01:47:43Z). Kalamath south, W 14th
  Ave, Santa Fe north, the northbound Kalamath to Speer. The page did not name the dropped default (13th Ave, split street).
- **D7:** "Mountains can be added to SC when Denver is done" (chat, to the Mac). The plan's phases are re-ordered: the
  backdrop is built and driven on Denver first, Sand Creek's bake follows.
- **Where Denver lives:** "New project for dgp"; on the page, "Its own bridge project: a dashboard and checks, files stay
  in airoso". The bridge dashboard is `denver-grand-prix`.
- **E1–E4** (PLAN §4b: the lamp, sign and paint gates) were never put to him on the Mac.

Kevin, directly in the cloud session, the same day: "Defaults for e1-4" · "New hairpin is good" · "Sc mountains after
Denver". **Every decision in the plan is now answered.** Owed: the dossier, the far-clip test, the survey sources of §4b.

## The far-clip test: asked of the PC, not yet run (2026-11-23)

Kevin: "have the pc run the far-clip test". Spec: `tracks/denver-grand-prix/source/farclip/README.md`. Playbox's reply:
nothing built, copied or run. Two blocks, both Kevin's to lift, to the PC session directly: anything written into AC
needs his yes typed there; and looking at AC needs either computer use on the PC (he declined it earlier) or his own
eyes from a checklist.

Read by Playbox from the settings files alone (no AC run): CSP 0.3.0-preview581; the player's
`graphics_adjustments.ini` has `[ADAPTIVE_CLIP_PLANES] FAR_PLANE=20000,30000`; AC's `video.ini` `FARPLANE=600`.
**Prediction, untested: the far clip is 20–30 km, so the 60 and 105 km walls will not draw and 25 km is borderline.**
The Front Range skyline is formed 20–100 km out (median 42 km), so at these settings most of it would be clipped.
Whether a track's own `ext_config.ini` can raise the far plane is not known; it is part of the test.

## "It needs to look right, not just be closer" (Kevin, 2026-11-23)

Asked how to fake the mountains if AC clips at 20–30 km. PLAN §3b: raising the far plane from the track's config comes
first; failing that, a layered pull-in (14 km stays, 105 km lands at 26 km, order kept) with haze baked from the real
distance, normals from the real surface, colour from real elevation. Worst error on the lap for the far peaks: about
1.3–1.6° in bearing against 2.1–2.8° on a single shell. Whether the backdrop can follow the weather is the open risk.
Acceptance is a game still beside a real photograph per sightline, and Kevin's eye.

## P0's facts, measured (2026-11-23, a second cloud session that reaches USGS)

Files under `tracks/denver-grand-prix/`; the first dossier is [`DOSSIER.md`](../../tracks/denver-grand-prix/DOSSIER.md), waiting on Kevin's approval.

- **Elevation along the lap** (`data/lap_profile.3dep.json`, 3DEP 1 m cells every 2 m): relief 31.6 m; start line 1,606.6 m,
  high point 1,611.0 m at 14th / Logan, low road about 1,582.5 m at 15th / Blake. Colfax falls 5.6 % from Sherman to Lincoln
  (steepest 50 m 6.6 %); E 14th Ave climbs 6.0 % from Lincoln to Sherman (steepest 50 m 7.2 %). The plan's 1,617 / 1,596 m
  were 10 and 6 m high.
- **Bare earth against the road:** 3DEP drops 4–5 m at the Blake bridge and 3–4 m at the W 14th Ave bridge; the lidar has
  class 17 deck returns on both. The lap crosses Cherry Creek only at those two; it does not use Colfax's bridge, and its
  part of Stout starts east of the creek. Under the Convention Center the lidar has **no ground return for 304 m**: 3DEP's
  line there is interpolated, so the road under the roof has no elevation source from the air. A 5 m pit in 3DEP on 15th St
  short of Lawrence is read as an artefact (NAIP shows a plain street); not yet checked on the points.
- **The horizon on 3DEP 1/3 arc-second** (`source/horizon/horizon.3dep13.json`, `horizon.compare.json`): two altitudes moved
  by more than 0.1°, both from the start line (Mt Morrison 1.93 → 2.03°, Green Mtn Lakewood 1.46 → 1.56°); no visibility
  changed. **Pikes Peak from Sand Creek:** the far terrain clears it by 0.35°; it is hidden from the origin point only by
  ground 8 m higher 300 m south of it. Not run: a viewshed from Sand Creek's own roads.
- **Survey sources:** NAIP 2023-09-25 at 0.3 m, one scene over the whole lap. Lidar CO_DRCOG_2_2020: flown 2020-05-27,
  4.0 returns per m² along the lap (2.0 ground). **DRCOG's 3-inch aerials: 2022 (and 2020, 2018, 2016) download freely from
  `drapparchive.s3.amazonaws.com`; 2024 is listed and refused (403).** Six tiles cover the lap, 2.68 GB a year. A window of
  the 2022 tile at the start line shows every lane dash, crosswalk block, mast arm and lamp post. No large raster is in git;
  `source/survey/` holds the tile lists and the scripts.
- **Not measured:** any width, kerb, median, pole, sign or paint line; the day of the 2022 flight; the free-roam grid's count.
- **Refused to that session:** overpass-api.de, data.drcog.org, gis.drcog.org, the NAIP blob store, The National Map's product API.

Owed now: Kevin's approval of the dossier; the far-clip test; then the survey itself (PLAN §4b) on a machine that keeps the tiles.

## The dossier approved; the survey started (Kevin, 2026-11-23)

"dossier approved, start the survey". `DOSSIER.md` is ticked. The survey of PLAN §4b (paint, streetlights, signal masts,
then signs) is given to the cloud session that reaches the aerial archive and the lidar, lap corridor first.

## The survey's pilot: Colfax, Logan to Lincoln (2026-11-23)

Kevin, in the cloud session that ran it: "go" (to the pilot; the planning session relayed "dossier approved, start the
survey"). Report: [`source/survey/pilot/PILOT.md`](../../tracks/denver-grand-prix/source/survey/pilot/PILOT.md), files and three stills beside it.

- **Paint reads.** From the 2022 3-inch aerial through the aerial engine's frame and channels: 308 marks on 385 m, 125
  graded measured (crosswalks, broken and solid lines, double yellow, stop bars), 183 detected (fragments, untyped
  symbols). **Checked against the 2020 lidar's intensity (another sensor, another year): 98 of the 125 confirmed, 11
  contradicted, 16 too few returns.** Aerial and lidar agree to 0.3 m with no scale error, which also tests the tiles'
  inferred CRS. 14.4 % of the roadway was under vehicles and is absent from the file.
- **Posts do not read from the lidar.** Seven of eight posts checked have no return above 2 m (4 returns per m²). PLAN
  §4b assumed they would. A reader on the aerial's shadows finds 6 of the 10 posts at Colfax / Sherman (1 of 3 signal
  masts) with 9 false candidates; no second source for posts exists; heights need the flight's date and hour.
- **Signs:** tagged from OSM per junction only. Nothing from the air.
- **Colfax has changed.** OSM today tags it two lanes each way with a designated bus lane; the 2022 aerial and NAIP
  2023-09 both show the old layout. No free photograph shows the street as it is. Both recorded, nothing picked.

Owed before the lap is run: a decision on posts (better reader plus an eye check, or by eye throughout), and on Colfax's
present layout. Paint can run on the lap as it stands.


## The far-clip test: run (PC, 2026-11-22 MST)

`tracks/denver-grand-prix/source/farclip/RESULT.md` (commit 7d7b4f2e). AC + CSP 0.3.0-preview581 draws 25, 60 and 105 km
when the track's `ext_config.ini` sets `DISTANT_FIX = 1` and `DISABLE_FAR_PLANE_CLIPPING = 1` on the backdrop's meshes,
present at load; without it drawing stops between 19 and 25 km. **True distance (D6) stands; the pull-in is a fallback.**
Under Pure the fog saturates by 15-20 km: past that only outline and fog colour read (PLAN 3a). Not tested: motion,
frame rate, which key alone suffices. Kevin has not seen the working version.

## The survey on the whole lap, unattended (Kevin, 2026-11-23)

After the pilot's three questions: "I want the best versions of these that you can do with no more input from me tonight".
Decided on his behalf, and given to the survey session to run without stopping:

- **Paint:** the whole lap; a second flight year (2020, then 2018) to fill what vehicles hid; symbols typed where the
  picture supports it; the thin-line width over-read corrected; split crosswalks joined; the lidar-intensity check on
  every firm mark.
- **Posts:** a better shadow reader, then **every candidate checked by eye** and the misses added by eye; a second
  flight year as the independent reading; heights only where the sun's elevation derives cleanly.
- **Colfax:** the 2022 state, per D8, with OSM's present bus-lane tags recorded beside it as changed and unsurveyed.
- **Signs:** tagged per junction from OSM; nothing invented.
- A refutation pass on a fresh sample per class before it is called done; Stout's covered 344 m declared unsurveyed.

## The shared backdrop: source, bake and gate built; Denver baked (Mac, 2026-11-23)

Branch `claude/dgp-backdrop-20261123`. PLAN 3 and 3a. **Nothing here has been seen in the game**: no kn5, no install, no drive.

**Built**

- **The source:** the seven 3DEP 1/3 arc-second tiles, 2,790,192,468 bytes, at
  `/Volumes/Sundowning/Claude/airoso-data/front-range/dem/` (outside git; the volume has 4.9 TB free). Byte counts equal the
  horizon study's, so these are the files it measured. URLs, sha256s and server dates: `tracks/_reference/front-range/provenance.json`.
- **`tracks/_reference/front-range/`:** `README.md` (how a track references it), `provenance.json`, `bake.config.json`,
  `ext_config.backdrop.ini` (`[SHADER_REPLACEMENT_BACKDROP_FR] MESHES = BACKDROP_FR_?`, `DISTANT_FIX = 1`,
  `DISABLE_FAR_PLANE_CLIPPING = 1`; a fragment, installed nowhere).
- **`tools/backdrop_bake.py`:** a polar lattice about the track origin, true geodesic bearing and distance (WGS84), curvature
  with refraction 0.13 baked from the origin, 0.001 rad cells (60 m at 60 km, never under 20 m, twice that along the line
  of sight), bearing 180 to 335, 2 to 112 km, culled to the union viewshed of the road line, real normals, objects
  `BACKDROP_FR_nnn`. Output: an OBJ.
- **`tools/backdrop_peak_gate.py`** and `tests/tools/test_backdrop_bake.py` (15 tests). `fleet/GATES-CHANGELOG.md` has the entry.

**The Denver bake** (`tracks/denver-grand-prix/data/backdrop.bake.json`; the OBJ, 180 MB, is at
`…/airoso-data/front-range/bakes/denver-grand-prix/`, sha256 `bff69609…`)

- **1,765,565 triangles, 913,893 vertices, 83 objects.** Before the viewshed the lattice is 5,347,350 triangles: a third is kept.
- By distance: 2 to 10 km 136 k, 10 to 20 km 282 k, 20 to 40 km 956 k, 40 to 70 km 324 k, 70 to 112 km 67 k.
- Extent: 2.0 to 108.7 km from the origin; x −78.5 to 0 km, z −108.7 to +90.8 km; ground 1,556 to 4,345 m; mesh y −199 to +2,503 m.
- Viewshed: 58 viewpoints along the 6,646 m lap, eye 12 m. 8,433 vertices moved onto a DEM summit.
- **Origin: provisional.** The start line (−104.9853, 39.7401), ground 1,604.59 m. Denver has no `track.config.json`; when it
  has an origin, bake again.

**The gate on that mesh: PASS** (`tracks/denver-grand-prix/data/backdrop.peak_gate.json`). From the start line, eye 1.2 m.
Mesh minus study, degrees:

| Peak | Bearing | Altitude | |
|---|---|---|---|
| Pikes Peak | +0.004 | 0.000 | |
| Devils Head | 0.000 | 0.000 | |
| Mt Morrison | +0.005 | +0.001 | |
| Mt Blue Sky (Evans) | +0.007 | +0.001 | |
| Green Mtn (Lakewood) | 0.000 | +0.001 | |
| Bergen Peak | 0.000 | −0.010 | |
| Mestaaehehe Mtn | +0.003 | 0.000 | |
| Lookout Mtn | 0.000 | −0.004 | the mesh's highest vertex in the box is 0.26° from the study's; the top spans both |
| South Table Mtn | 0.000 | 0.000 | mesa |
| James Peak | −0.004 | 0.000 | |
| North Table Mtn | 0.000 | 0.000 | mesa |
| Thorodin Mtn | −0.007 | 0.000 | |
| South Arapaho Peak | −0.006 | 0.000 | |
| Mt Audubon | 0.000 | +0.001 | |
| South Boulder Peak | −0.001 | +0.001 | |
| Bear Peak | +0.009 | −0.026 | see below |
| Green Mtn (Boulder) | +0.007 | 0.000 | |
| Longs Peak | −0.006 | 0.000 | |
| Mt Meeker | +0.084 | +0.012 | see below; the nearest to the limit |

- 19 visible peaks, all within 0.1°. Hidden in the study, not gated: Grays and Torreys are not in the mesh (dropped by the
  viewshed); Mt Rosalie, Mt Bierstadt and Chief Mtn are in it (the margin, or seen from elsewhere on the lap) and read within 0.08°.
- **Skyline, reported, not gated:** 311 bearings, none over 0.1°, mean −0.003°, worst −0.024° (at 299.0°).

**Found on the way**

1. **The study's bearings were spherical.** `horizon_3dep.py` took bearings on a sphere from geodetic latitudes: up to 0.12°
   from the true azimuth here (Longs Peak 317.06° where the geodesic says 316.95°), 7 of the start line's 24 peaks by more
   than 0.1°. Altitudes move by 0.007° at most; no visibility changes. The bake uses the ellipsoid, so the gate's
   reference is a re-run: `horizon_3dep.py --wgs84` → `source/horizon/horizon.3dep13.wgs84.json` (pyproj; no code shared
   with the bake). `horizon.3dep13.json` is untouched. **Owed: DOSSIER section 6's table and PLAN section 3's were
   printed from the spherical file; their bearings are up to 0.1° off. Not edited here.**
2. **Three of the study's "summits" are the edge of its search box, not a summit:** Bear Peak's is South Boulder Peak's slope
   (2,586 m; the real Bear Peak, 2,579 m, is 1.19° north in the same box), Mt Meeker's is Longs Peak's, Lookout Mtn's a
   slope rising out of the box. The nominal coordinates in `horizon_study.py` want correcting. The gate passes them
   through its flat-top rule (`FLAT_DEG`, invented, in the changelog).
3. **A plain 60 m lattice reads sharp summits low** (Mt Blue Sky 19 m, 0.02°) and a neighbouring bump can then outrank the
   summit. Hence the kept summits; each is the DEM's own point.

**Not verified, not done**

- The game: nothing drawn, no frame rate. 1.77 M triangles is this recipe's count, not a budget anyone agreed (the Lariat
  plan's backdrop is 100 to 140 k). Triangles go with 1 / `pixel_rad`²; `radial_factor` and `near_m` are the other knobs.
- The viewshed is from bare earth along the lap at 12 m, not from buildings: it keeps far more than a driver downtown
  sees, by design. It has not been checked against a second, independent viewshed. The skyline check from the start line
  is the only evidence that nothing visible was dropped; from Speer / Colfax and the rest of the lap it is unchecked.
- The seam between the backdrop's near edge (2 km) and the track's own ground: no track ground exists yet.
- Haze, fog and the material (PLAN 3a); colour by elevation; the towers; Sand Creek's and the Lariat's bakes; the kn5
  export and the `models_*.ini` listing; `DISTANT_FIX` on real terrain; motion.
- The full test suite on this Mac ran in a venv outside git with the project's declared dependencies (result in the PR).

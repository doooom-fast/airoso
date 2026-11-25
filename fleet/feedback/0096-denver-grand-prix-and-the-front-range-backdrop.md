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

## 0.1.0 (Drive 1): the lap's road and ground, race and street, built on the Mac (2026-11-25)

Kevin, 2026-11-24: "When these are installed, I want you to tag team the Denver Grand Prix build out"; at 23:06,
"get what as much as you can done and installed at 7am". Branch `claude/dgp-buildout-20261125` (from main 60c694e2, the
widths survey `claude/dgp-widths-20261125` c03567a5 merged). The engine work of PRs 61 / 60 / 66 and the SIGNFACE rows are
Codex's integration; this build does not depend on them and is re-run once that base is merged.

**What 0.1.0 is.** `tracks/denver-grand-prix/` on Lake Murray v4's engine (`ship.json` `engine: lm-v4`, Sand Creek's
pattern): slug and install folder `denver_grand_prix`, `fictional_street_circuit`, `mirror_x` false, north 0. Two layouts on
one road kn5: **Race** (the lap one way, Lake Murray's K-rails along both edges as Sand Creek uses them, every side street
sealed, the race kerbs the detector finds at 11 corners, the grid on Colfax behind the Sherman crosswalk facing west, one
W1-6 race plate at the hairpin in the race closure kn5) and **Free Roam** (the same roads open, plus each side street's
mouth). No pit lane (D5). The draft is written from committed files by `source/draft/draft_line.py` (the line, its
heights and widths, the 3DEP grid) and `source/draft/mouth_stubs.py` (the mouths); `lm_intake` reads them as its own source
track.

**Measured, and from what**

| What | Source |
|---|---|
| the route | OSM as of 2026-11-23 (`data/lap_line.plan.json`, the lap's nodes in driving order) |
| the edges, kerb to kerb | `source/widths/widths.json` (c03567a5): the kerb face from the 2020 lidar's class-2 step, else the asphalt edge (lidar intensity, 2022 aerial) plus the measured 0.46 m pan. At this build's 2,184 line points: 3,157 edges measured, 184 detected, 1,025 inferred |
| the line | moved to the middle of its two measured edges (offset −4.3 to +9.8 m from OSM's line); width 6.6–32.0 m |
| heights | 3DEP 1 m along OSM's line (`data/lap_profile.3dep.json`), a 33 m median despike and a 9 m mean, **no grade cap**: steepest 7.3 % over 10 m (E 14th Ave, Lincoln to Sherman) |
| the two bridges | level decks at the class-17 lidar's p50: Blake 1,584.60 m (widths s 2,780–2,822.5), W 14th Ave 1,591.05 m (s 4,895–4,937.5) |
| Stout's portals | road z 1,589.27 m (entry) and 1,591.67 m (exit, 14th St), lidar |
| the ground | USGS 3DEP 1/3 arc-second tiles, a 40 m lattice over the lap plus 470 m, pre-divided to 20 m by the intake |

**Every [invented] number** (each also in `track.config.json` beside the key it sets)

- **Corner curb radius 6.0 m** on the lap's 12 corners over 45°: the fillet radius is 6.0 + the mean of the two legs'
  measured half widths (9.3–17.3 m), Sand Creek's rule. No curb return on the lap is measured (the survey bridges every
  junction mouth straight across).
- Across each corner (tangent + **6 m**) the line's offset and width run linearly between the zone's ends; running means
  of **15 m** on the offset and **9 m** on the width.
- **Stout under the Convention Center, s 1,387.5–1,730:** the road between the measured portals is a straight line, and
  its edges are the survey's linear fill (276 inferred edges). Built **open-air**: no roof, no soffit, no columns.
  `capture.covered_spans` (PR 61) is not in this base; nothing overhead is built, so no gate needs it yet.
- **15th St short of Lawrence:** the 5 m 3DEP pit (profile s 2,282–2,318) is a straight line between its measured ends,
  and both edges are filled linearly over widths s 2,285–2,327.5. The kerb reader found steps inside the pit: 5.75–11 m
  where the street reads 16–21 m either side.
- **Kalamath / Santa Fe south of Colfax, the lap's two directions side by side:** each direction's edge stops **1.8 m**
  short of the middle between the two lap lines (paint.json has no double yellow there; its two yellow pieces read
  6.6–6.8 m from Kalamath's line, at that middle). That leaves a 3.6 m strip of ground where the real street is paved
  across. The K-rails stand on each side of it, and in the race no_route holds the lap one way with no short cut. Within
  **30 m** of each other the two lines' heights are blended to their mean (full weight within 20 m); they differed by
  0.03–0.12 m.
- **Side-street mouths:** OSM ways that meet the lap's own nodes, followed **40 m**. A stub is dropped if its far end stays
  within **20 m** of the lap (the lap's other carriageway) or if less than **12 m** of it leaves the lap's pavement. A stub
  stops **6 m** short of another part of the lap. Widths by class: primary 9.5, secondary 10, tertiary 10,
  unclassified 8, residential 8, links 6 m. Heights: the 1/3 arc-second surface's rise from the lap's edge.
  **74 built** (72 mouths). **17 excluded**, each named with the gate reading that refused it (verify_mouths notch /
  approach / host lane, audit K / I, one drive_test ground-on-top), at the junctions where Sand Creek needed pads and
  returns: Colfax between Speer's two legs, the Speer / Stout / Kalamath junction, Auraria Pkwy at Speer, Stout at 15th,
  Logan at 14th, Sherman at the line, W 14th at Kalamath.
- **The edge is Sand Creek's:** no curb, no sidewalk; the lane edge flat for 0.3 m, then down 0.2 m over 1.5 m. The real
  kerbs read 0.06–0.18 m.
- **The grid and the timing:** the line at the crosswalk (vertex 50, 152 m after station 0), the pole 3 vertices behind
  it. Race columns are at ±1.0 m (the chain's), the free roam's at +1.0 / +3.0 m right of centre. Sectors are derived.
  These are the chain's rules, not Denver's grid paint.
- **Race furniture:** Lake Murray's K-rail 0.82 m inside each edge, the race kerbs at 11 corners, and the hairpin's W1-6
  plate. The plate is there because a whole-lap race closure kn5 carries its layout's plates (Sand Creek's pattern). Every
  other corner the W1-6 rule would sign is skipped in `signs.json` with its reason, so no rule-placed sign stands in the
  free roam.
- The origin's `elev_m` 1,580 is a datum for local Y, not a reading.
- **Textures: the engine's stock rows.** The owned asphalt and concrete pairs are Kevin's for the four tracks he is
  finishing ("On every track now", scoped to them 2026-11-22), not Denver until he says so (240b2797's follow-up: the Mac
  build of eada16c2 had carried Sand Creek's overrides; the change binds textures only, no geometry).

**The Mac build of eada16c2, from an empty workshop (a `git archive` of the commit), `--no-install`** (Blender 4.2.9; ENG = the engine-july snapshot with
`assets/textures`; the runner changes only the Blender path and bash 3.2's `declare -A` / `${tok^^}`): **SHIP OK, every gate
green, no force, no threshold or tolerance changed, no engine change.**

| Gate (built kn5) | Free Roam | Race |
|---|---|---|
| drive_test | **PASS**: ground on top 0, severe 0, bumps 0 /km, kinks 2.3 /km, excursions 0 (8 far flare ledges reported), obstructed 0, daylight 0 | **PASS**: ground on top 0, severe 0, bumps 0 /km, kinks 4.6 /km (station 5.82, vertex kinks 8 reported), barrier stations without a wall 0 of 13,056 |
| audit_mesh | **CLEAN** (A–K 0) | **CLEAN** (A–K, W 0) |
| no_route (built) | — | **PASS**: leak 0 m², 0 doors, 0 of 72 mouth probes reached, 77.4 k m² reached |
| kn5_ground_check | **PASS**: road over ground 37 / 5,142 > 0.05 m, p95 0.021 m | **PASS** (the same, walls and plate seated) |
| verify_mouths | **PASS**, 72 mouths | (the same road) |
| verify_kn5 / --inis / textures | PASS / PASS / PASS (0 untextured) | the same; race kn5 and closure checked |
| verify_race / verify_signs / planned no_route | — | OK / PASS / PASS |

kn5: road `denver_grand_prix.kn5` 38,303,638 B; race `denver_grand_prix_race.kn5` 9,365,823 B; closure
`denver_grand_prix_closure_race.kn5` 5,599 B; spawn kn5s 2,104 B each. Built lap 6.53 km on the driven line (6,639 m on
OSM's: the corners are rounded). AI: generated drafts, race 196 s, free roam 211 s (estimates, not recordings).

**Left out of 0.1.0, owed**

- The full D4 free-roam grid: every street inside the lap and one block out. 0.1.0 has the lap's own roads and 72
  mouths, each 40 m long and ending there.
- The 17 hard junctions' mouths (pads and corner returns, as Sand Creek's), the medians as raised islands, curbs and
  sidewalks, and the measured curb radii at the corners.
- Paint from the survey's inventory: PR 61's `paint_inventory` step is not in this base. 0.1.0 carries the engine's
  default paint by width, with no centre yellow.
- Lamps, signals and signs from the survey (0.1.1, the furniture plan `claude/dgp-furniture-plan-20261125` 0cd1a05c).
- Stout's inside: the roof, the columns, the rails and the lights. Its declaration as a covered span comes with PR 61.
- The creek channels under the two bridges: no `capture.bridges` span is declared, so the ground is pinned to the deck.
- The buildings and landmarks (P4), the trees, crossfall from lidar, and the Front Range backdrop (PR 59, D6).

**For Kevin** (none blocks the install): the 6.0 m corner radius; the Kalamath / Santa Fe divider; the 17 mouths not
built; the 15th St pit; Stout open-air. The widths session fixed the false kerb at the start line (c03567a5): Colfax at the
grid is one street, about 20.5 m kerb to kerb.

## Runbook 0096-1 (PC): rehearse Denver Grand Prix 0.1.0 from an empty workshop, then install on green

1. **Code.** A clean checkout of `origin/claude/dgp-buildout-20261125` at the head the coordinator names. Denver commits no
   blend and needs no LFS object.
2. **ENG.** A fresh copy, as the Mac built with: `scripts/` and `vendor/` from
   `tracks/san-diego-lake-murray/engine-july-snapshot` (MANIFEST-exact), plus the checkout's `assets/textures` beside them,
   for example `D:/k10-scratch/eng_dgp_010`. The live engine-july still holds the PENDING-MIRROR md5s; do not point ENG at it.
   The AC add-on is Blender 4.2's, as for every lm-v4 build.
3. **Rehearse.** `set PYTHONUTF8=1`, then set `AIROSO_NUMPY_PY` to the PC's python with numpy, then run:
   `SHIP_PROJ=D:/k10-scratch/denver_grand_prix_0961_reh ENG=D:/k10-scratch/eng_dgp_010 bash tools/ship_track.sh denver-grand-prix --no-install > D:/k10-scratch/dgp_0961_reh.log 2>&1`.
   Use no `--from`, no `--skip-blend` and no force. The SHIP_PROJ folder must not exist yet.
4. **Expected, as on the Mac:**
   - `[lm_intake] denver-grand-prix: 2184 pts`, `connectors in`;
   - `[weld] 72 mouth(s) welded, self-check clean`;
   - `[bands] ... strips on 2184/2184 verts`, `22 kerbs at 11 corners`, `planned no_route: PASS`;
   - `[signs] 1 placed (... 1 layout plate (DGP-HAIRPIN@race))`;
   - `[split] closure race ... 3 sign plates`.
   - Then every row of the table in "0.1.0 (Drive 1)" above: both drive_tests PASS with ground on top 0 and severe 0;
     audit CLEAN on both; no_route PASS; kn5_ground_check PASS on both; verify_mouths PASS on 72; textures PASS.
   - The log ends `SHIP OK`.
   - Kn5 sizes: race 9,365,823 and closure 5,599 should hold within a few hundred bytes. The road kn5 will differ from
     the Mac's 38,303,638: that figure is eada16c2's, built with the owned asphalt / concrete pair, and 3aa0c02b binds the
     stock textures (geometry unchanged). Compare kn5s with `tools/kn5_equiv.py`, never md5: the tangent pass is not
     bit-stable.
   - Call out any row that differs.
5. **Install on green.** AC must be closed. Run the same command without `SHIP_PROJ` and without `--no-install`:
   `ENG=D:/k10-scratch/eng_dgp_010 bash tools/ship_track.sh denver-grand-prix`.
   - The workshop is `D:/k10-scratch/denver_grand_prix`, empty the first time.
   - It installs as `content/tracks/denver_grand_prix`, a new folder, so nothing is parked.
   - The sync-back writes `loop.blend` and the data files into the checkout. `loop.blend` is a record: keep it in the PC's
     track archive with its md5, never in git.
   - A red rehearsal installs nothing; report its first red row with its numbers.
6. **Report:** SHIP OK or the first red row; the kn5 sizes; the run's start and end; the install path.
7. **Kevin's first drive** (DOSSIER §10):
   - the launch down Colfax from the Capitol;
   - E 14th Ave's 6 % climb to Sherman;
   - both bridges;
   - Stout between its portals, open-air in 0.1.0;
   - the Kalamath / W 14th / Santa Fe hairpin as three streets;
   - the free roam's mouths.

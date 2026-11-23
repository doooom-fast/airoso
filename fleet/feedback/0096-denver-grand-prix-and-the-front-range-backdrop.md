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
- **E1–E4** (PLAN §4b: the lamp, sign and paint gates) were never put to him on the Mac. Still owed.

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

**Planned, nothing built.** The plan and its eight decisions: [`tracks/denver-grand-prix/PLAN.md`](../../tracks/denver-grand-prix/PLAN.md).

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
2. Kevin's answers to D1–D8 ("defaults" is an answer).
3. The horizon study re-run on 3DEP.

## Coordination

2026-11-23, sent from the cloud session to the local session Tracks:Mac (it reaches Overpass, USGS and the board):

> Denver Grand Prix is planned on branch claude/kind-turing-5xrxlc: tracks/denver-grand-prix/PLAN.md, ledger 0096.
> Two asks, both from Kevin's message of today ("work with them if you can and see if you can use them to post to my
> internal status board"): (1) post a card for it on the board: "Denver Grand Prix: planned, 8 decisions waiting on
> Kevin, P0 (OSM + far-clip test) next"; (2) when you are free, fetch the OSM extract for P0 and push it to the
> branch. Neither should interrupt work Kevin has you on.

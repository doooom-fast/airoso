---
id: 0002
title: Roads follow bare-earth elevation instead of the road's own engineered grade
status: open
scope: all kinds
layer: engine
train: 01
---

## Symptom

> "roads/sidewalks/curbs that don't float and also don't directly follow the geo-elevation data but
> instead respect road-elevation data"

The road surface inherits the *ground's* shape rather than the shape a road actually has. Real roads
are engineered objects: constant-grade tangents joined by parabolic vertical curves, sitting in cuts
where the hill was too high and on fills where the ground was too low. A bare-earth DEM samples the
hill, not the road.

## Evidence

The pipeline samples elevation **along the road line** from USGS 3DEP bare earth, then cleans it
statistically — median-despike, smooth, grade-cap by real segment distance. That is a *filter on
ground samples*, not a road profile. Where the difference is large enough to break something, the
fix so far has been a targeted patch per failure mode:

- **Bridges** — bare-earth DEMs contain no deck, so a road over a freeway samples the trench and
  dips. Patched by holding each OSM bridge span level between abutments
  (`k10-san-diego/scripts/geometry/bridge_level.py`, SD-unique).
- **Interchange aliasing** — a coarse terrain grid aliased 70th St up into an embankment and read a
  57% cliff. Patched by sampling that road at its own points instead of off the grid.
- **Everything else** — absorbed by the smoother, which is why the remaining artifacts are subtle:
  gentle undulation on what should be a constant grade, and cut/fill edges that have to be forced
  flush afterwards (`road-grounding`, and see `0004`).

Each patch is correct. But they are three fixes for one missing concept.

## Diagnosis

There is no **road vertical datum** — no representation of "what grade is this road actually built
at" that is separate from "what height is the dirt here". Without it, every road-vs-ground
discrepancy has to be discovered as its own failure mode and patched individually, and the terrain
work (`0004`) is left to reconcile a road that never had a designed profile in the first place.

Note this is the *inverse* of the law the fleet already enforces. `LAWS.md` L3 says the ground
conforms to the road — which is right, and which only works if the road's own profile is trustworthy.
Today it is trustworthy only after enough smoothing to blur real crests.

## Fix

A road-profile stage between elevation sampling and projection:

1. Sample bare earth along the line as today (that stays the input — L1: real data).
2. **Fit an engineered vertical profile**: constant-grade tangents joined by parabolic vertical
   curves, with grade and curve length bounded by the road's class and design speed. Real crests
   survive as real vertical curves; DEM noise does not survive at all, because it cannot be
   expressed in the model.
3. Emit **`cut_fill_m` per vertex** — the signed delta between the fitted road and bare earth. This
   is the number the terrain stage wants: positive = the road sits on a fill (build an embankment up
   to it), negative = the road sits in a cut (bench into the hill). That is exactly what the
   `real_road` archetype already promises in words: *"bench cuts into the ridge, fills with retaining
   structure where earth can't reach, ditches"*.
4. Fold the bridge and interchange patches into it: a bridge is a span where `cut_fill_m` exceeds
   what earth can hold, which is the *general* form of the rule `road-grounding` already states —
   span deep gaps with a bridge instead of paving over them.

Known cost: this changes road Z on every track, so the whole fleet must be re-gated. It is the most
invasive item in train 01 and should land last, after `0001` and `0004` are proven.

## Scope

All kinds. The mountain and canyon tracks show it most — `lookout-lariat` (25 km of foothills),
`dragon-tail`/`under-the-dragon` (mesa and canyon shelf), `aspen`. Flat sites (`sand-creek`,
`grand-junction`) are the regression cases: their profiles should barely move, and if they move a
lot the fit is wrong.

## Verification

- On a flat site, fitted profile vs current profile differs by **< 0.15 m** everywhere.
- On `lookout-lariat`, no grade exceeds the road's class maximum, and every real switchback crest
  present in 3DEP is still present as a vertical curve (compare against the raw samples, not against
  the old smoothed output).
- `cut_fill_m` is non-zero and plausible on the canyon shelves — a road on a shelf should read as
  cut on the uphill side.
- `drive_test` reports no new steps or slope kinks anywhere in the fleet.

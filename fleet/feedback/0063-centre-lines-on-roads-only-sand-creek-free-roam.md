---
id: 0063
title: Centre lines belong on actual roads; Sand Creek gets a free roam with its grid, and 3D trees
status: fixed-awaiting-drive
scope: every race layout and race circuit; tracks/sand-creek; tracks/san-diego-lake-murray
layer: engine + project
train: -
---

## Symptom (Kevin, 2026-11-01)

> "we need to remove centerlines from the race tracks, only keep for actual roads, and remove from the racetrack versions (ie keep only on freeroam)"

> "we want to fill out the grid around sand creek for its free roam version"

> "is our assets tool building 3d trees or 2d? i'm seeing 2d on sand creek which needs a lot of work in general"

Wanted installed to drive the same afternoon. No specifics yet behind "a lot of work in general": ask, do not guess.

## What was there

- **Race circuits** (no `road_markings.style`: Nevada Nights, Milford, High Plains, Pueblo, Aspen, Grand Junction, Pikes
  Peak, IMI, Second Creek) took `ribbon.road_markings`: white edge lines and a dashed white centre.
- **Lake Murray** paints its double yellow as `YLINE_*` in the road kn5, which all three layouts load, so the race layouts
  have it too.
- **Sand Creek** has one layout (`full`), style `lane`, double yellow on. Its trees are `TREECARD_*`: 6,673 crossed
  double-sided cards (`tools/author_bespoke_blend.py` `cards`). Every chain track's vegetation is cards; only Lake Murray
  runs 3D TreeFX models (`tools/make_treefx.py`), which are personal-use and stay on the Windows box.

## The rule

A race circuit has edge lines and no centre line. A track with both kinds of layout keeps its centre line in the free roam
alone. White lane lines on a race layout of a real road stay: the request named centre lines.

## Fixes

- `scripts/geometry/ribbon.py` `road_markings`: the dashed centre is gone (`tests/geometry/test_circuit_no_centreline.py`).
  Takes effect on each circuit's next draft.
- `scripts/geometry/race_chicane.py`: any track with both kinds of layout routes `YLINE*` to `<slug>_street.kn5`, which non-race layouts load. The Lariat's parked
  race layouts follow the same rule when they return.

## Results, 2026-11-01 (installed, none driven yet)

| Track | Version | What | Road kn5 |
|---|---|---|---|
| Nevada Nights | 0.7.0 | fresh draft, edge lines only: kinks 6.59 -> 0 /km, fold bumps 21 -> 3 (the gates and AI now walk the swept line) | 79e68787 |
| High Plains | 0.71.0 | fresh draft, edge lines only: every drive_test number unchanged; guardrail 553 -> 561 m; `post9` and `post12` lost their colliders (the merged fine-ground rule) | 4e9a62d6 |
| Milford | 0.4.0 | edge lines only: every gate number equal to 0.3.0 | 64ccb077 |
| Sand Creek | 0.30.1 | race + Free Roam, 6,357 TreeFX trees, 108 real OSM street pieces (40 km) | 28580713 |

**Lake Murray 0.19.3** is built, the yellow line in Free Roam only, and held at Kevin's word; 0.19.2 stays installed. The upgrade is ledger 0065.

**Kevin first set the circuits to paint only, then lifted it:** "We want those tracks updated to be the better geometry." Nevada 0.6.0 and High Plains 0.70.0 were the paint-only builds; they sit in `D:/k10-track-archive`.

**What the day found:**
- The repo's Milford heightfield predated its corrected frame and the chain's sync-in overwrote the workshop's good one; a draft on it spanned 500 m terrain triangles. `ship.json` now syncs the heightfield back.
- `build_mesh`'s debug `track_render.svg` filled the C: drive on a 10 M vertex ground. It is now skipped over 2 M triangles.
- Editing `tools/ship_track.sh` while a chain runs kills the run: bash reads the file as it goes. Run from a copy.

**Sand Creek:**
- No cottonwood model exists, so SycamoreV1 / V2 / V3 stand in; the neighbourhood trees are Oak3 and SycamoreV2. The models are personal-use: Sand Creek's public package must not carry them.
- `route.grid.exclude` leaves out `grid_tertiary_94`, 80 m of real road at the lap's east end whose smoothed line ran 2.57 m under the lap's bank (186 of 191 kn5 pokes). It is a real road the Free Roam lacks.
- The side streets stand in both layouts because the road kn5 is shared (L8); the race layout has no walls keeping a car off them.
- Unmodelled bridges: `grid_primary_11` rides up to 3.2 m over the ground at about (-1533, -740), and the lap itself up to 8.15 m at about (1314, -866), the declared deck over the creek. Street pieces carry no bridge body.

**Workshops moved to `D:/k10-workshops`** (Kevin, 2026-11-01), the four tracks above; the others move as they next build.

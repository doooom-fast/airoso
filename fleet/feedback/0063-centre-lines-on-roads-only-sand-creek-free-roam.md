---
id: 0063
title: Centre lines belong on actual roads; Sand Creek gets a free roam with its grid, and 3D trees
status: in-progress
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
- Owed, on the Windows box: `YLINE_*` routed to the street-only kn5 on Lake Murray; Sand Creek's race and free roam
  layouts, the grid, TreeFX. The results land in this entry. The Lariat's parked race layouts follow the same rule when
  they return.

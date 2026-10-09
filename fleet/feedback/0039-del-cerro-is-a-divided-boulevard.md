---
id: 0039
title: Side streets "not connecting correctly" — Del Cerro Blvd is a divided boulevard swept as two skinny roads
status: in-progress
scope: tracks/san-diego-lake-murray (del_cerro_blvd connector); engine pattern (any OSM dual carriageway chained into a loop)
layer: track + tools
train: -
---

## Symptom (Kevin, seat, 2026-10-08, `san_diego_lake_murray_v3`)

> "the side streets, something's wrong with them where they're not connecting correctly. So
> there's a chirality issue somewhere."

(The chirality half was the minimap — [0038](0038-the-minimap-is-mirrored.md). Side streets
seen through a mirrored map join on the wrong side; the geometry itself is not mirrored.)

## Evidence

- Top-down render of the gate OBJ at College/Del Cerro: the connector ribbons DO butt into
  College's edge and College's sidewalk IS gapped at the mouths (C2 v1 works) — but Del Cerro
  arrives as **two 10 m ribbons ~12 m apart with raised sidewalks on all four edges, sidewalks
  back-to-back between them**, i.e. two skinny streets where one boulevard should be.
- `connectors.local.json.pre-trim` → `del_cerro_blvd`: 1,104 points, 3,312 m. Nearest
  other-part-of-itself distance every 25 points: **11.9–15.0 m for points 0–475 and 625–1,100**,
  then 141–440 m for 500–600. The polyline is the boulevard's two carriageways chained by
  `merge_ways` into one out-and-back loop, plus a real loop road at the far (hilltop) end.
  OSM tags are stripped in `network.cache.json` (only name/highway/geom), so `oneway` could
  not confirm it — the geometry does.

## Diagnosis

The same defect class as [0032](0032-college-ave-sawtooth-is-narrow-stripes.md)/[0035](0035-the-phantom-opposing-carriageway.md)/[0037](0037-divided-roads-need-their-median.md):
a divided road modelled as independent ribbons instead of one slab with the median standing on
it. At the mouth the two legs read as two junctions 12 m apart with a 2 m sidewalk strip between.

## Fix (built this day)

`tools/divide_connectors.py` (config `route.divided_connectors`): pairs each point with its
counterpart on the other carriageway, collapses the two legs into ONE trunk (centreline = pair
midpoints, width = separation + 8 m, island = separation − 8 m), keeps the far loop as a plain
ribbon closed onto the trunk end, zeroes the island within 18 m of College (left-turn pocket)
and at the trunk ends. Islands are authored by `tools/author_median_blend.py` (now reads
`median_bands.json["connector_islands"]`) and exempted in the gates by
`scripts/geometry/median_zone.py`. Trim + mouth gap then see one ~20 m mouth.

## Verification

Kevin: Del Cerro leaves College as one boulevard with a planted median and a left-turn pocket at
the mouth; the far loop still drives. Audit K/I must not rise (the island is exempt by band).

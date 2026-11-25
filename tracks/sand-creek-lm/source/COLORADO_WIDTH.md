# Colorado Blvd at its real width: the measured table and what moves (PC, 2026-11-24)

**Source.** The G10's `lap_colorado_quebec.lidar.json`, stretch `colorado`: claude/sc-roads-lidar-20261124 @ 10f75a0e,
USGS CO_DRCOG_2_2020 class 2. 181 stations every 2.5 m along the lap's s, v3205 -> v140 and on to s 415.8. Faces are
good to about 0.25 m.

**Frame.** u is lateral in the lap's frame, + = left of travel. The built ribbon is +-8.25 m (16.5 m); the 48th pad's run
is wider.

**Placement.** "What moves" is read off rehearsal 0211 (727b3578): its `data/` and `source/bespoke/`. Each item is
placed at its nearest station within 1.25 m along and 40 m across.

## The width table, per 50 m of the stretch (medians of the stations; real faces only, `none` faces excluded)

| run m | s_lap | divided / stations | real curb to curb, divided | built | median width | near cw | far cw | right curb u (real - built) | median faces u | far left curb u |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-50 | 9605-13 | 0/20 | (38-41 m, the 48th approach, no median) | 16.5 | - | - | - | -12.75 (-4.0) | - | +26.0 |
| 50-100 | 16-63 | 0/20 | (38.25 m, the approach) | 16.5 | - | - | - | -14.75 (-6.5) | - | +24.1 |
| 100-150 | 66-113 | 0/20 | (26.25 m, one crowned road) | 16.5 | - | - | - | -5.25 (+3.0) | - | +21.0 |
| 150-200 | 116-163 | 7/20 | 26.1 | 16.5 | 4.5 | 10.75 | 11.1 | -5.0 (+3.25) | +5.75 / +10.25 | +21.1 |
| 200-250 | 166-213 | 16/20 | 25.5 | 16.5 | 4.25 | 11.0 | 10.25 | -5.25 (+3.0) | +5.75 / +10.0 | +20.25 |
| 250-300 | 216-263 | 16/20 | 25.1 | 16.5 | 4.25 | 11.0 | 10.25 | -5.5 (+2.75) | +5.5 / +9.75 | +19.75 |
| 300-350 | 266-313 | 11/20 | 26.4 | 16.5 | 3.75 | 11.9 | 11.0 | -7.0 (+1.25) | +5.25 / +9.0 | +12.25 (few) |
| 350-400 | 316-363 | 8/20 | 27.0 | 16.5 | 2.0 | 12.5 | 13.0 | -6.75 (+1.5) | +5.75 / +7.9 | +5.25 (few) |
| 400-450 | 366-413 | 0/20 | - | 24.15 | - | - | - | -7.0 (+3.3) | - | - |

- **The divided road** (s 143-353): 25.75 m curb to curb (median of the 25 stations with both outer curbs). The median
  is 4.25 m (narrowing to 1.5-2.5 past s 315) with its top +0.14 / +0.15 m. Near carriageway 11.0 m, far 10.5 m.
- **The built ribbon is not either carriageway.** It is 3.0 m wide of the real right curb and runs 2.5 m onto the real
  median. The lap's real carriageway is u -5.25 .. +5.75: 11 m, its centre +0.25 m left of the built line.

## What moves (the 0.2.11 scene)

- **Lamps.** The six near Colorado alternate sides at u +-11.05 (2.8 m past the built edge).
  - The three on the LEFT would stand in the real far carriageway: lamp 0 (s 58, the approach, real road to +23.5),
    lamp 2 (s 166, median +6.0 / +10.25) and lamp 4 (s 276, median +5.25 / +9.5). They need new spots: on the median, or
    past the far curb.
  - The three on the RIGHT (lamps 1, 3, 5) stand 5.8 m outside the real right curb, which is fine.
- **Pads.**
  - colorado_50th (rows v129 / v151): 22 of its 48 sampled outline points are by a Colorado station.
  - 48th_colorado (rows v3193 / v3216): 24 of 46.
  - Their outlines come from the lidar and are unchanged. Their seam rows and arm rows follow the lap's new widths.
- **Mouths on the lap along Colorado:** one, grid_unclassified_76#0#0 (start), v95, its cut at u -7.85 on the built right
  edge. With the real right curb at -5.25 its cut moves in about 3 m.
- **Name blades:** nb0 (s 276, u -10.36), right side, outside the real curb. It stays.
- **Trees:** 2 near (u +23 / +26, past the far curb). Neither is in the road.
- **Buildings:** 1 corner within 40 m (osm_buildings41, u -39). None is in the road.
- **Signs:** none on the stretch itself. SC-C50 (colorado_50th) and SC-48C / SC-48S (48th) sit at its ends, on the
  pads; their failed-turn rays change with the new edges and get re-placed.
- **The race layout** drives Colorado. Its walls (race_edge), the corridor (Kevin: "Full street width") and both
  layouts' AI lines follow the lap's edges and get rebuilt. A width change here is a race-layout change.

## Decisions the round needs (not measured)

1. **What the lap is on Colorado:**
   - (A) the near carriageway only: 11 m, centre +0.25 m, the median as a raised island beside it, the far carriageway
     as a new side piece;
   - (B) Lake Murray's one-slab divided road: 26 m with the raised island on it (median_envelope + author_median_blend,
     not in Sand Creek's ship.json today).
2. **The race corridor on a divided Colorado.** Kevin's "Full street width" was given for an undivided street. With the
   median, is the race lane the near carriageway or curb to curb across it?
3. **The two ends** (the 48th approach, 38-41 m with no median; s 63-140, one 26 m crowned road), and how the width
   eases into the pads.

## Decided (the Mac, 2026-11-24 / 25) and built in 0.2.13

1. (A): the lap is the near carriageway. The right edge sits on the measured curb over s 66-348, and the left edge on
   the median's near face over s 143-348, with 25 m raised-cosine eases. The median is concrete islands where the lidar
   reads one raised. The far carriageway is the side piece grid_primary_colorado_sb.
2. The race corridor runs curb to curb on the lap's carriageway, with no closure wall.
3. The 48th approach and s 63-140's left side stay as built. s 63-140's left side is owed: one real 26.25 m road.
4. Lamps: the 12 DRAPP 2022 poles in place of lamps 0-5.

The records, the tool and the readings are in fleet/feedback/0098-sand-creek-to-finished.md, section "PC, 2026-11-25:
0.2.13".

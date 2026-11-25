# Denver Grand Prix — the lap's widths, kerbs, medians, bridge decks and Stout's portals

*2026-11-24/25, read on the Mac for the Denver 0.1.0 build-out (Tracks:Mac's brief; Kevin: "When these are installed, I
want you to tag team the Denver Grand Prix build out"). Data only: no track config, no Blender scene.*

```bash
PY=/Volumes/Sundowning/Claude/airoso-data/venv/bin/python   # numpy, scipy, laspy+lazrs, tifffile, pyproj
PYTHONUTF8=1 $PY tracks/denver-grand-prix/source/widths/widths.py   # about 40 s on the Mac
```

Inputs are the files in `source/survey/DATA.md` (outside git): the 2020 lidar corridor and the 2022 DRAPP 3-inch tiles.
The first run writes a lidar corridor cache to `<data>/widths-cache/`.

## Files

| File | What |
|---|---|
| `widths.json` | Every 2.5 m along OSM's lap line (2,659 stations, 6,646 m): both edges as an offset from the line, lap-frame E/N and lon/lat, grade, source, both readings, the kerb step height, the aerial−lidar difference, raised medians, and whether another OSM carriageway lies between the kerbs |
| `stretches.json` | Per contiguous OSM way, 101 stretches: width p10/p50/p90, grades, confidence, the measured gutter pan, two-reading count and disagreement (>0.3 m) with its runs, share spanning an opposing carriageway |
| `bridges.json` | Blake over Cherry Creek and W 14th Ave's bridge: the deck from class 17 lidar, its profile along (every 2 m) and across (every 0.5 m at mid-span), and the ground at both abutments |
| `stout_portals.json` | Stout under the Convention Center: both portals' widths, road height, the covered span, and the inside declared |
| `widths.py` | How it was read. Every tuning value is `[invented]` and written into each file's `meta.tuning_invented` |

**Frame:** ENU metres about the Colfax / Sherman crosswalk (−104.9849, 39.7401), using the aerial engine's
metres-per-degree series (`scripts.aerial.engine.ortho.mpd`). This is the survey's frame (PR 66, `lapgeo.py`). `s` runs
in driving order from the S/F crosswalk. Offsets are across the line, **+ is the driver's left**. Each edge also carries
lon/lat, so nothing downstream depends on this frame.

## How the edges were read

The engine's edge reader (`scripts/aerial/engine/edges.py`) was tried first and is not used. Downtown, asphalt meets a
concrete gutter pan, a kerb and a concrete sidewalk. All three pass its near-neutral pavement test, so its score does not
fall at the kerb. Its colour tuning has no upper luminance bound to configure. The reader here uses the engine's frame,
geometry and running medians with a section rule for a city street:

1. **Kerb face, from the lidar (2020-05-27, class 2 ground):** returns within ±2.5 m along the station, binned 0.25 m
   across. The face is the first outward place past 1.5 m where the ground steps up 0.06–0.40 m and stays up.
   - Parked cars do not interfere: they are not class 2.
   - The search runs free from the line. An earlier pass tied it to an asphalt reading, and bike-lane paint, a concrete
     lane or a tower's shadow carried it off the kerb (seen on stills at 14th Ave and 15th St).
2. **Asphalt edge, from lidar intensity:** asphalt returns near 0; concrete and paint return 500–3,000. The edge is a
   rise of 400 over the road that holds for 0.5 m. Streets that are concrete across the whole section give no reading.
3. **Asphalt edge, from the 2022 aerial:** the same rule on luminance, a rise of 30, as the second source.
4. **Gutter pan:** measured per way as kerb face minus asphalt edge. **Lap-wide median 0.46 m on both sides.** That
   matches a 1.5 ft pan, which is a check on the method; the pan figure itself is the median of the readings.
5. **Edge of record:**
   - the kerb face, graded `measured`;
   - else the asphalt edge plus the way's pan: `measured` when the intensity and aerial readings agree within 0.3 m,
     `detected` from one;
   - else filled linearly along s, graded `inferred`, with its reason: `mouth` (another road's edge, more than 1.6× the
     side's running median and 2 m out), `no_reading`, or covered.

   The record is smoothed by a 5-station running median.

**Grades, all 5,318 edges:** 3,859 measured (73 %), 198 detected (4 %), 1,261 inferred (24 %). Inferred breaks down as
276 under Stout's roof, about 330 at junction mouths, and the rest unread.

**Checked by eye** on the aerial, with the edges drawn (stills beside this file at four places, more were looked at):
- the kerbs sit on the kerbs on Colfax at Civic Center, 14th Ave at Kalamath, Speer at the Blake split, Kalamath and
  Santa Fe (including the brick median between them), and Colfax at the Capitol;
- junction mouths are bridged straight across;
- 15th St in a tower's shadow reads its kerbs; the aerial cannot see them there, the lidar can.

## Two sources: where they disagree

The brief asks where the aerial and the lidar disagree by more than 0.3 m. Where the lidar has a kerb face, the aerial's
asphalt edge plus the pan is compared with it; elsewhere the aerial is compared with the intensity edge.

- **1,929 edges have both readings; 1,429 (74 %) differ by more than 0.3 m.** The median difference is +0.10 m, and the
  16th–84th percentile range is −1.3 to +4.2 m.
- The aerial is the weak reading. It reads a parked car, a tree lawn, a crosswalk bar or a shadow as the edge.
- So the **position of record rests on the lidar**, and the disagreement is mostly the aerial failing, not two good
  readings in conflict.
- Every station carries `aerial_minus_lidar_m` and `disagree`; every stretch lists its disagreement runs.

## Per leg

Width is the p50 of the kerb-to-kerb record. Measured is the share of edges graded measured.

| Leg | s (m) | Width p50 (m) | Measured | Aerial vs lidar >0.3 m |
|---|---|---|---|---|
| Colfax WB to Speer NB | 0–1175 | 11.4 | 76 % | 332 of 465 |
| Speer NB to Stout | 1178–1325 | 15.9 | 76 % | 31 of 52 |
| Stout to 15th St (incl. 344 m covered) | 1328–1905 | 9.5 | 27 % | 26 of 28 |
| 15th St to Blake | 1908–2642 | 17.8 | 77 % | 175 of 186 |
| Blake to Speer SB | 2645–2945 | 16.3 | 74 % | 79 of 82 |
| Speer SB to Kalamath | 2948–3748 | 15.6 | 80 % | 192 of 290 |
| Kalamath S to W 14th Ave | 3750–4138 | 18.4 | 79 % | 46 of 46 |
| W 14th Ave to Santa Fe | 4140–4202 | 11.9 | 69 % | 3 of 4 |
| Santa Fe N to Colfax | 4205–4392 | 21.3 | 88 % | 22 of 24 |
| Kalamath NB branch to Speer SB | 4395–4540 | 17.9 | 65 % | 16 of 16 |
| Speer SB to W 14th Ave | 4542–4882 | 15.9 | 77 % | 42 of 98 |
| 14th Ave E to Logan | 4885–6250 | 12.9 | 78 % | 357 of 489 |
| Logan N to Colfax | 6252–6430 | 11.8 | 63 % | 50 of 67 |
| Colfax W to S/F | 6432–6645 | 16.4 | 77 % | 58 of 82 |

Per-way detail, with confidence `high` / `medium` / `low`, is in `stretches.json`. Of the 6,646 m, `high` covers about
4.7 km, `medium` 1.2 km and `low` 0.1 km; the covered 342 m has none.

## Read this before cutting the road

- **Kerb to kerb, not lane to lane.** Where OSM maps a street as two one-way ways with only paint between them (Colfax
  east of Logan and at the Capitol, parts of Kalamath / Santa Fe, 15th at Blake), the two kerbs hold the other direction
  too. The width is then the whole street's.
  - `opposing_carriageway_within` marks those stations: 129 of 2,659, with the other way's offset and id.
  - The painted divider (double yellow) is in PR 66's `paint.json`.
  - Whether the race uses the whole street there is the build's call.
- **A raised median on the lap's side is a kerb face here.** Colfax at Civic Center and Speer's parkway read to the
  median kerb. Where the lidar also finds the median's far face it is listed in `medians`, raised, with both offsets.
- **Painted medians are not read here.** They are in PR 66's `paint.json`.
- **Kerb type** is recorded as the step height (`kerb_step_m`, p50 per stretch). Vertical kerbs read 0.10–0.18 m;
  mountable or rolled kerbs are not told apart.
- **Concrete streets** (parts of Colfax at Civic Center, 15th, 14th Ave): no asphalt reading from either source; the
  kerb face alone carries them.
- **Junctions:** the edge is carried straight across each mouth (`inferred`, `mouth`). The mouths' own returns and
  radii are the junction step's job, from OSM and the aerial.
- **State:** the 2022 aerial and the 2020 lidar (D8: Colfax as it stood before the bus-lane rebuild). OSM's present-day
  bus lanes are not built.

## Bridge decks (class 17 lidar)

| Bridge | s (m) | Deck p50 z | Ground before / after | Deck edges (offset, class 17 p2/p98) |
|---|---|---|---|---|
| Blake St over Cherry Creek | 2780.0–2822.5 (42.5 m of deck returns; OSM's way is 39 m) | 1584.60 | 1584.39 / 1584.68 | −7.89 / +8.52 |
| W 14th Ave over Cherry Creek | 4895.0–4937.5 (42.5 m; OSM 42 m) | 1591.05 | 1590.95 / 1590.98 | −7.63 / +8.70 |

Both decks sit within 0.25 m of the ground at their abutments: no hump to model, a deck held level between
abutments. The profiles in `bridges.json` hold the detail; the edges include the parapets' returns.

## Stout under the Convention Center

- **Covered span:** OSM way 453022192, `tunnel=building_passage`, `covered=yes`, `maxheight=5`, 2 lanes; s 1387.5–1730.0
  on this line.
- **Entry (south-west):** 7.9 m kerb to kerb (left 3.62 / right 4.25), road z 1589.26.
- **Exit (north-east, at 14th St):** 6.0 m (3.00 / 3.00), road z 1591.67.
- **Clear height:** 5.0 m, OSM-tagged and not measured. The lidar sees the roof, not the soffit: the structure top within
  8 m is 1628.7 m at the entry.
- **Inside:** `between measured portals [invented]` (Tracks:Mac's call for tonight). The edges are interpolated linearly
  from portal to portal. No source sees under the roof; a capture by Kevin would replace it.

## Not done

- No sign faces or post heights (unchanged from the survey).
- No mouth geometry at junctions.
- The aerial reading was not improved past the point where it ceased to matter for the record.
- The 2020 aerial year was not used.

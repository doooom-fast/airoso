# College Ave "realism+": the real road against the built one (round 2, step 1)

Kevin (ledger 0055): "can you split them up and do something fun? i would prefer realism+". This folder is proof step 2
of that ledger: the real carriageways' heights, registered in the engine frame, beside the road as built. No geometry
is authored here and nothing in the shared config changes.

## What is here

| File | What |
|---|---|
| `college_xsec.lidar.g10.json` | measured: USGS CA_SanDiegoCo_D24 (2024) lidar, class 2, at every centreline vertex v800-1560, offsets -30..+30 m every 0.5 m (read by the G10, nothing downloaded on the PC; `job1_report.g10.json` has the tiles and md5s) |
| `j1_waring.lidar.g10.json` | measured: the J1 crossroads on a 1 m grid, Waring sections s 0-200 m, the crossroads plane |
| `college_sections.py` | reads the lidar and the 0.20.2 gate OBJ, writes `college_sections.json` (benches, the built extent, built minus measured per station) |
| `college_sheet_data.py`, `college_sheet.py` | the picture `college_sections.png` (twelve stations) |

Run: `<blender python> college_sections.py <workshop>/data/track.obj`, then `college_sheet_data.py` (same python),
then `python college_sheet.py` (Pillow). Offsets: + = left of travel = west on College northbound. Heights: engine
y = NAVD88 - 100.8.

## What it shows

- **The real road is split level from about v1180 to v1440** (3,537 to 4,314 m along the lap). The northbound
  carriageway (east) rides a bench above the southbound (west):

  | v | 1180 | 1200 | 1220 | 1240 | 1260 | 1280 | 1320 | 1340 | 1400 | 1420 | 1440 | 1460 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | northbound over southbound, m | 1.3 | 2.2 | 3.1 | 5.4 | 5.8 | 5.3 | 5.5 | 5.1 | 1.2 | 1.9 | 1.0 | 0 |

  The G10's own check against the older research agrees (+2.51 / 5.59 / 5.91 / 5.33 / 5.02 / 1.85 m at v1216 / 1243 /
  1258 / 1290 / 1342 / 1396).
- **Where the benches sit** (v1240-1340): southbound about +4 to +14 m, northbound about -15 to -6 m, each 8 to 10 m
  wide; the bank between them is about 9 m wide and rises up to 6 m.
- **The build is one slab**, -14 to +16 m, at the southbound grade. Its northbound half sits **up to 6.1 m below** the
  real northbound carriageway (built minus measured: -6.1 m at v1260), cut into the hillside the real road rides on.
- At v880 the built road is 7 m above the class-2 ground: a bridge deck, as built.
- `[invented]` in the reading: a bench = at least 6 m of measured ground with cross slope under 8 % (taken over 1.5 m).

## J1

The crossroads plane off the same lidar (r 25 m): 6.08 % falling to bearing 277°, toward Waring, rms 0.13 m (the G10's
read; `j1_waring.lidar.g10.json`). Kevin: "Tilt it now", as one change with the College work.

## Next (ledger 0055, "Bounded proof" steps 3 to 7)

Author both carriageways, the bank and both transitions together as one connected system, on a scratch copy; prove
connected pavement through College / Navajo / Waring in both directions on the built proof; only then integrate.

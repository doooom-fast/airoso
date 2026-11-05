# E 56th Ave bridge deck over Sand Creek: 2020 lidar vs the build

Analysis only; nothing in the mesh, config or build changed. Source: USGS CO_DRCOG_2_2020 EPT, classes 17 (deck) and 2 (ground),
every 2 m from station 2,380 to 2,600, median of points within 1.5 m along and 4.5 m across the finished line
(`finished_centerline.json`, kn5 frame, height = y + origin elev_m). Metres/degree from `_meters_per_degree(origin lat)`.
Stations are cumulative plan (horizontal) arc length along the finished line from point 0 (lap 9,674.1 m).
Per-station data: `e56th_bridge_deck.json`. Chart: `e56th_bridge_deck.png`. Heights are metres, 3DEP vertical datum as in the lidar.

## Deck extent
- Class-17 points start at about station 2,402 (3 points) and are solid (>= 10 per station) from 2,404 to 2,522; 5 points remain at 2,524, none at 2,526.
- Lidar deck is 2,404 to 2,522, about 118 m. Full-density coverage (about 60 to 70 points per station) runs 2,412 to 2,520.
- The declared 2,429 to 2,528 (99 m) does not match on this line: those look like draft-line stations, and the finished line is up to 23 m shorter. In finished-line stations the deck begins about 25 m earlier and ends about 6 m earlier than the declared span.
- The 3DEP DEM drops into the creek bed over the same 2,408 to 2,522 (see the chart), which agrees with the lidar extent.

## Crown
- Deck ends (mean of the two end stations each side): 1579.636 m at about 2,405 and 1579.272 m at about 2,521 (total fall 0.36 m).
- Max height above the straight line between the ends: 0.29 m, at station 2464.
- Highest deck point is 1,579.77 m near 2,440 to 2,446; the deck is a flat-topped hump, rising 0.14 m in the first 36 m, near level to 2,450, then falling about 0.50 m to the east end.

## Deck minus built height (over the 60 stations 2,404 to 2,522)
- p50 +0.41 m, p95 +0.49 m, max +0.50 m (at 2464); min +0.15 m (at the west abutment).
- The build is below the real deck at every deck station; the gap grows from +0.15 m at the west end to about +0.47 to +0.50 m over 2,446 to 2,474, then closes to +0.23 m at the east end.
- This confirms the first rough look (about 0.45 m) but here it is measured at the correct place.

## Step at each abutment (approach ground vs deck, same station)
- West, 2,404: deck 1579.630 vs ground 1579.650, step -0.020 m; at the next stations -0.04 m. No real step: the deck is within 4 cm of the approach, and the approach ground itself climbs about 0.14 m from 2,400 to 2,410.
- East, 2,522: deck 1579.248 vs ground 1579.291, step -0.043 m; at 2,520 it is -0.022 m. No real step.
- The build vs the approaches: approach ground minus built is [-0.025, 0.017, 0.097] (min, median, max) on the west approach and [0.088, 0.173, 0.234] on the east approach to 2,560. The built road is up to 0.23 m below the real road east of the bridge, so the approach error is not just the deck.

## Cross-slope (least-squares tilt across 9 m; + = left higher)
- Median -1.21 % (right side higher), range -1.64 % to 1.88 %.
- West half, 2,406 to 2,486: steady -1.0 to -1.6 %.
- East end, 2,488 to 2,504: about -0.2 to -0.4 %, passing through zero near 2,506 and reaching +1.9 % at 2,522 (sharing the approach's turn).
- Fit residual sd is in the per-station JSON (`deck_xslope_sd_m`); a single plane across 9 m, so a crown across the deck would cancel in it.

## Recommended deck profile (station: height, every 5 m)
Cubic fit to the lidar deck medians (2,412 to 2,520), rms residual 0.9 cm, max 2.8 cm. 2,404 to 2,522 is deck; 2,400 and 2,525 to 2,530 are the lidar ground medians so the approaches meet it.
  - 2400: 1579.595  (built 1579.498, ground (approach))
  - 2405: 1579.663  (built 1579.474, deck (cubic fit))
  - 2410: 1579.691  (built 1579.455, deck (cubic fit))
  - 2415: 1579.715  (built 1579.438, deck (cubic fit))
  - 2420: 1579.735  (built 1579.413, deck (cubic fit))
  - 2425: 1579.750  (built 1579.394, deck (cubic fit))
  - 2430: 1579.760  (built 1579.376, deck (cubic fit))
  - 2435: 1579.766  (built 1579.351, deck (cubic fit))
  - 2440: 1579.768  (built 1579.335, deck (cubic fit))
  - 2445: 1579.766  (built 1579.315, deck (cubic fit))
  - 2450: 1579.759  (built 1579.291, deck (cubic fit))
  - 2455: 1579.749  (built 1579.274, deck (cubic fit))
  - 2460: 1579.734  (built 1579.248, deck (cubic fit))
  - 2465: 1579.716  (built 1579.231, deck (cubic fit))
  - 2470: 1579.694  (built 1579.215, deck (cubic fit))
  - 2475: 1579.668  (built 1579.188, deck (cubic fit))
  - 2480: 1579.638  (built 1579.171, deck (cubic fit))
  - 2485: 1579.605  (built 1579.155, deck (cubic fit))
  - 2490: 1579.568  (built 1579.128, deck (cubic fit))
  - 2495: 1579.528  (built 1579.111, deck (cubic fit))
  - 2500: 1579.485  (built 1579.089, deck (cubic fit))
  - 2505: 1579.438  (built 1579.068, deck (cubic fit))
  - 2510: 1579.388  (built 1579.051, deck (cubic fit))
  - 2515: 1579.335  (built 1579.030, deck (cubic fit))
  - 2520: 1579.279  (built 1579.008, deck (cubic fit))
  - 2525: 1579.235  (built 1578.990, ground (approach))
  - 2530: 1579.198  (built 1578.965, ground (approach))

## Uncertainty
- Deck span differs from the declared 2,429 to 2,528: 2,404 to 2,522 on the finished line (118 m vs 99 m). The offset is probably the draft-vs-finished line station difference; the declared span was not re-derived.
- The DEM column is `z_raw_m` from `centerline.elevation.json` (draft-line stations), mapped to each finished-line station by nearest draft point (gap in `dem_match_dist_m`); it reads the creek bed under the deck, as expected.
- The first and last deck stations (2,402 to 2,406, 2,522 to 2,524) have fewer points and no cross-slope fit; the cubic profile is anchored on stations with >= 20 points.
- Class 17 is the lidar's own classification; rails, barriers or curbs of the deck are inside the 4.5 m window only if classed 17, and the median is robust to a few.

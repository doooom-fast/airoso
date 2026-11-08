# Pikes Peak International Raceway: the road course and the oval's inside edge (ledger 0085)

Research only, in no chain; nothing here is built. Kevin, 2026-11-07: "pikes peak is an oval yes but also it has a road
course we're supposed to be building in, that takes advantage of the existing oval."

## Route from the published maps (supersedes "which route" below)

Kevin: "Why aren't you using actual track maps?" / "Stop guessing" / "Do them as published, i just drew shape". The two
maps (downloaded on his word, not committed; `PPIR_MAPS`, default `/Volumes/Drive/codex/pp_work/maps_dl`):
SCCA Track Night (`scca_trackmap_ppir.png`) and racingcircuits.info 2017 to date (`racingcircuits_ppir_road_2017.png`).

| file | what |
|---|---|
| `schematic.py` | map outline, thinning, similarity ICP (both handednesses), warp |
| `maps_route.py` -> `route_from_maps.naip.json`, `still_route_from_maps.jpg` | each map registered to the lidar wall face, its line read onto the measured pieces, SCCA's top hairpin refit locally, the lot's driven band measured, RC-D and the infield-only loop assembled, T1-T9 placed |

Run after `routes.py` (it reads `oval_mid.npy` from `PP_CACHE`); Kevin's infield-only stroke from `PPIR_SKETCH`
(default `pp_work/sketch/routes/infield_only.json`). Further stills in `PPIR_MAPS_OUT` (`lot_band.jpg`,
`top_hairpin_refit.jpg`). A map is a selection aid (L1): it picks the pieces and their order; every coordinate is a
measured piece, the measured lot band, or the oval's mid-surface line. Numbers: ledger 0085 "Route from the published maps".

## Re-trace (edge-measured; supersedes the eyeball trace below)

Kevin, on the first overlays: "Those tracings aren't very accurate." The infield centre line by eye and the oval's
first-gap inside edge are kept as `infield_network.eyeball.json` / `inside_edge.eyeball.json` (`inner_edge.py`).
Their replacements, every number in ledger 0085's Re-trace section:

| file | what |
|---|---|
| `register_wall.py` -> `registration.json` | NAIP against the 2018 lidar wall face: the image sits 0.42 m off (E +0.09, N -0.41), applied |
| `naip.py` | image channels (grey, smooth-texture, kerb, white, green paint), ENU <-> pixel with the shift removed |
| `pieces.py` | the 14 infield pieces (which road each is: a few via pixels; WHERE it is: measured), edge finding, spline fit, wear |
| `retrace.py` -> `infield_pieces.naip.json`, `inside_edge.naip.json` | both edges, centre, width per metre, residuals, inferred stretches, kerb runs, wear per piece; the oval's inside edge, apron line, wall-to-edge width |
| `routes.py` -> `layouts.naip.json` | the oval's mid-surface line, junction stations, ten candidate layouts assembled from the pieces, lap lengths, wear support |
| `stills.py` | `/Volumes/Drive/codex/pp_work/retrace/`: `overall.png`, 33 `zoom_*.png` (60 x 60 m, 4x, wear tinted), 10 `layout_*.png` |

Run order (needs the NAIP crop, `geo.IMG` / `PPIR_NAIP`): `register_wall.py`, `retrace.py`, `routes.py`, `stills.py`.
Intermediate arrays go to `PP_CACHE` (default `pp_work/retrace/_cache`), not the repo.

Superseded below: the 623.6 m "newest loop" (now RC-A, 1,872 m with the oval, edge-measured), the 18.3 m median inside
edge (from the port line; the wall-to-edge width is now measured per station), and "which route the aerial cannot
decide" (still true: RC-B and RC-C both land within the junction uncertainty of the published length).

## What the road course is (sources)

| fact | value | source |
|---|---|---|
| length | 1.289 mi (2.074 km) | Wikipedia, infobox "Road Course (1997-2026)" |
| length | 1.315 mi (2.116 km), "2017 to date" and every period before it | racingcircuits.info |
| length | "1.3-mile interior road course" | SCCA location page (Track Night in America) |
| turns | 9 | Wikipedia; LapMeta (search snippet; the page answers 403) |
| direction | counter-clockwise | LapMeta and the-fastlane (search snippets only; both pages answer 403) [unverified at the source] |
| shape | S/F "in the middle of the D-shaped oval", into Turn 1, "the longest corner", heavily banked; "eight turns in a tight space" inside | LapMeta (search snippet) [unverified at the source] |
| other layouts | "Track Sprints ... the infield portion of our track in various layouts" | PPIR ticketing (search snippet) |
| oval | 1.006 mi, 10 deg; "variable width from 60-71 feet" | Wikipedia; racingcircuits.info |

Reading those together, with the geometry below: a counter-clockwise lap runs the oval's front stretch, Turn 1 = the oval's
banked turns 1-2 ("the longest corner"), the back stretch, leaves the oval for the infield and its eight turns, and rejoins
the oval at the end of turns 3-4. **Corner names: none found.** **Which infield roads the lap takes: not settled** (below).

## What NAIP 2023 0.3 m shows (on disk)

The infield's pavement (`pave_mask.py` on the crop `naip_2023_030.json` describes; `still_road_course_candidates.jpg`):

- **Two junctions with the oval, both on its inside:**
  - **NE: a diverge on the back stretch.** A lane leaves the oval's inside pavement at lap s 947 (the LM port's line;
    lidar bank 8.6 %, 4.9 deg) and separates behind a grass gore by s 1037 (15.6 %, 8.9 deg). A CCW car peels left
    here; a car could not join the CCW oval here (the gore points the wrong way).
  - **NW: a merge at the end of turns 3-4**, s 1344, on the full bank (17.4 %, 9.8 deg), **21.5 m inside the line, i.e.
    ~14 m inside the built lane's left edge**: on the oval's real inside pavement, which the port does not build (below).
- **The newest (light-grey) pavement is one continuous loop** between them: the NE lane up the north-east side, a hairpin
  at the top, south to a second hairpin by the skidpad lot, west along the bottom, north up the west side, and west onto
  the oval (`infield_network.naip.json`, centre line traced by eye on the masked crop, not edge-snapped, ~1-2 m
  [unverified]). **623.6 m.**
- Older, darker pavement: an S-curve section between the west road and the C road, a parallel lane north-east of the C
  road to the skidpad lot, and the paved skidpad / autocross lot (the circle). Not traced.
- Red / white kerbs on almost every infield corner (visible at 0.3 m; not traced).

**The newest loop is not the published course by length.** Oval share of a CCW lap s 1344 -> 0 -> 947 on the port's line:
1,263 m (the port's line runs near the wall; the published 1.0 mi oval is 1,609 m against this line's 1,660 m). With the
loop: **1,887 m (1.17 mi) against 2,074-2,116 m published, 187-229 m short.** The S-curve section or a lap of the skidpad lot
would make up a difference of that size; which one, the published map shows and the aerial cannot (L1: never guess a line
and name it after the real course).

## The inside edge (Part 1's open question)

`inner_edge.py` -> `inside_edge.naip.json` (`still_oval_inside_edge.jpg`: cyan the built lane, magenta its right edge on
the lidar wall face, orange the measured inside edge): along each station's inside normal, the first non-pavement run of
1.5 m or more.

- Inside pavement edge: median **18.3 m** inside the port's centre line (p10 15.9 m; p90 34.9 m where it runs into the
  pit lane and the infield roads; 32 of 555 stations meet other pavement with no gap before 40 m: s 171-311 by the pit
  exit and the south-turn service roads, and s 1320-1332 / 1474-1483 at the NW junction).
- By section (median inside edge / pavement past the built lane): turns 1-2 18.3 / 10.8 m, turns 3-4 19.5 / 13.1 m, back
  stretch 16.1 / 8.6 m, front stretch 17.2 / 11.0 m.
- **Past the built lane's left edge: median 11.4 m of real pavement is not built** (p10 8.6 m). Wall face to inside edge is
  ~25 m: the racing surface's 60-71 ft (18.3-21.6 m) plus an apron.
- Its cross-slope is NOT measured: the survey band stops 6.5 m inside the line. Building it as the banked plane carried on
  would invent its slope (aprons are usually flatter); the 2018 lidar holds it.

## What is missing (not on disk; nothing was downloaded)

1. **The route.** The published course map, SCCA: `https://www.scca.com/wp-content/uploads/2026/02/trackmap_Pikes-Peak-International-Raceway.webp`
   (one image, size not read; a map image is a selection aid for which asphalt, never traced, L1). Or Kevin's word on the route.
2. **The 2018 lidar over the oval's inside half and the infield** (USGS 3DEP `CO_Eastern_ElPaso_2018` EPT, the same project
   the camber and wall surveys streamed on the G10): the apron's cross-slope, the infield's ground (the port's 3DEP grid is
   40 m), kerb heights, and a true re-fit of narrow bands across the banking. Size [unverified estimate]: tens of MB
   (roughly 30-80 MB for a ~600 x 700 m box at QL2 density, read on the G10 under its 4 GB cap).
3. **OSM raceway ways in the infield**, one Overpass query (a few kB); not queried.

---
id: 0073
title: Sand Creek's lap is re-sourced from OSM: the same streets on their real centrelines, street corners at a measured radius
status: fixed-awaiting-drive
scope: tracks/sand-creek (engine: an opt-in route.fillet for any source.type osm route; tools/lidar_crossfall.py reads a draft's swept line)
layer: engine + project
train: -
---

## Symptom (Kevin, 2026-11-03, after driving Sand Creek 0.31.0)

> "i think the sand creek roads are a bit wiggly w/r/t lines and curves/edges, they're not realistic and messy"

Ledger 0070 split that into four defects; this entry is **A, the line** (fix A1). Asked whether to re-source the line
from OSM or only smooth Google's, Kevin answered:

> "Re-source from OSM"

## The evidence (ledger 0070, A)

- The lap was Google Maps' Directions polyline (`source/Sand Creek Raceway Drive-3.kml`, `source.type kml`): 453
  vertices a median 13.7 m apart, rounded to 1e-5 deg (up to +-0.56 m), resampled linearly to 3 m. Nothing snapped it
  to OSM.
- 93 % of the draft line's turning sat within 3 m of a Google vertex; jogs were opposite kinks 20-30 m apart.
- Zig-zag p95 per 30 m: draft 13.1 deg, swept 5.2 deg, the OSM way under it 0.78 deg.
- The five 90 deg street corners came out as one or two Google vertices, rounded by build_mesh to a ~7 m radius
  under a 20-42 m road; the ribbon's pleat guard engaged at 23 vertices, all at those corners.
- L1 allows KML only where a route leaves the road network. Every station of the old line is within 4.7 m of an OSM way.

## What changed (0.33.0)

### The route: the same streets, OSM's ways (`source.type osm`)

The KML lap was map-matched onto OSM (the widths snapshot's 1,571 drivable ways, nearest segment with a heading
penalty, every 3 m) and the run of ways it drives is now declared in `route.roads`, one `id:` leg per street in lap
order, fetched into `data/osm.cache.json` (79 ways, OSM 2026-11-03) and stitched by the engine's own
`build_centerline` (`build_ring` joins each leg to the next at their shared node: every join gap 0.0 m). The KML stays
in `source/` for history; no step reads it.

| leg | OSM ways | carriageway |
|---|---|---|
| North Colorado Blvd, E 48th to E 50th | 628714841, 800407125, 628714840 | the northbound one-way (the lap's direction) |
| E 50th Ave, N Ash St (the jog), E 50th Ave | 16988702; 16988425; 16988698, 800494399 | single two-way ways |
| Dahlia St | 132271133, 16969721, 628649540 | single way |
| E 56th Ave | 132271105, 628655280, 44769372, 628649528 | one two-way way: its line is the street's median line |
| the 56th -> Sand Creek Dr slip | 628649529 (primary_link) | the slip itself (ledger 0066's camber corner) |
| Sand Creek Dr South | 1456718434 ... 628728310 (10 ways) | single way |
| N Northfield Quebec St | 186241514, 44769365, 16977970, 427698233, 257721786 | the southbound one-way |
| the Quebec -> E 45th slip | 944920188 (primary_link) | the slip |
| the I-70 frontage roads: E 45th Ave, E 45th North Dr, E 46th Ave | 28 ways (incl. 944914475, a 6 m motorway_link piece of the same carriageway) | each one-way, with its arrows |
| E 46th Ave Access, E 48th Ave | 1456709180, 946631199, 16986952; 132271123, 99826469 | single ways |

**Carriageways, chosen.** Where OSM has two one-way carriageways (Colorado, Quebec, the frontage pair) the lap takes the
one it drives, never the median line between them: that is real pavement, it is the side whose lanes
`widths_from_osm` reads, and the grid already drops the other side (`route.grid.parallel_m`).
`tools/route_oneway_check.py` on the new line: 0 m against an arrow (street layout PASS; race layouts are closed
roads). Where OSM has one way for a wide street (E 56th, 5 lanes) its line is the median line: the new line runs 2.9 to
3.2 m north of the old one there (Google drove the eastbound lanes).

**E 45th Ave (ledger 0068's nudge stretch), chosen.** By the aerial (0068's work) 45th there is a one-way three-lane
road whose two south lanes are the I-70 ramp and whose north lane carries on as E 45th, narrowing to one lane 2 m from a
barrier at the old 6,494. The lap is E 45th, not the ramp, so it takes OSM's E 45th ways: the three-lane way's centre
(944920187) until the ramp leaves, then the one-lane way's (16986954, then 864873958 over the creek). Against the old
line: 1.8 to 3.0 m south of it at old 6,325 to 6,375 (off the north edge line it rode), within 0.7 m at 6,400 to
6,425, then 0.2 to 1.6 m north of it to 6,650 (the single lane's centre). 0068's 1.5 m nudge was reverted on its
branch; nothing of it is carried here.

### The line: rounded once, before the resample (`route.fillet`, `scripts/gps/fillet.py`, new, opt-in)

- **Declared corners.** At each 90 deg street corner the OSM polygon has one shared node. `route.fillet.corners[]`
  puts the circle of `radius_m` tangent to both leg lines there (a rational quadratic Bezier, exactly circular). The
  radius is from the street: `radius_m = curb_radius_m + the mean of the two legs' half widths`, the half widths being
  `widths_from_osm.pavement_width / 2` of the way at the node (the width the ribbon is built at), so the built
  ribbon's inside edge follows a curb return of `curb_radius_m`. `curb_radius_m` is read off NAIP 2023
  (`source/naip_2023_sc_z18.jpg`, 0.46 m/px, about +-2 m); `source/feedback-0073/corners_over_naip.jpg` shows each
  corner: the old swept line (yellow), the OSM polygon (cyan), the new line (red) and its edges at that half width
  (white).

| corner | curb return (NAIP) | half widths | radius | deflection | swept min R | old swept |
|---|---|---|---|---|---|---|
| Colorado Blvd -> E 50th Ave | 6 m, round the grass island | 10.0 / 5.0 | 13.5 m | 101.8 deg | 13.0 m | ~7 m |
| E 50th Ave -> N Ash St | 3 m, an industrial square corner | 5.0 / 5.0 | 8.0 m | 95.7 deg | 8.0 m | ~7 m |
| E 50th Ave -> Dahlia St | 3 m, square at the truck yard | 5.0 / 5.5 | 8.2 m | 89.9 deg | 8.3 m | ~7 m |
| Dahlia St -> E 56th Ave | 15 m, a truck route's sweep | 5.5 / 11.75 | 23.6 m | 89.1 deg | 22.6 m | ~7 m |
| Sand Creek Dr S -> Quebec St | 6 m | 9.0 / 8.25 | 14.6 m | 52.2 deg | 15.8 m | |
| E 48th Ave -> Colorado Blvd | 4 m, the island tip | 5.5 / 8.25 | 10.9 m | 84.1 deg | 10.5 m | ~7 m (the old seam) |

- **Every other node** is replaced by the arc tangent to its two segments at their midpoints, after nodes within
  `simplify_m` 0.25 m [invented] of their neighbours' chord are merged (Douglas-Peucker between the declared arcs). A
  curve OSM draws node by node keeps its own radius (Ash St into E 50th, the two slips, 46th Ave Access into 48th), a
  1 deg node on a straight becomes an arc of hundreds of metres, and a way join is not rounded inside one 3 m segment:
  the 56th slip meets Sand Creek Dr at 26 deg, R 9.5 m without the merge, R 20 m with it.
- **Station 0.** `route.start_at` [39.78413, -104.94043] is North Colorado Blvd, 40 m north of the E 48th Ave node, put
  on the line as an exact point. The old v0 was that corner itself (the KML started and ended there and closed with a
  4.1 m chord); the seam is now on a straight (L13).
- **The origin is pinned** (`origin` = the 0.31/0.32 centroid value, elev_m 1572.38), so the local frame did not move
  with the line: loop.blend's authored layers, the spawns, the AI lines and the deck's absolute heights stay put
  (0068: a 2 cm nudge of a centroid origin moved all of them).
- `build_mesh`'s smoothing and 28 deg rounding still run; on this line they move it at most 7 mm in plan from what the
  draft line implies. Nothing in `build_mesh` changed.

### The swept line read in its own frame (`tools/lidar_crossfall.py`)

Straight after a draft, `finished_centerline.json` is build_mesh's (frame "mesh ...": z = north); after the PC prep it
is the kn5 frame (z = -north). The tool read both as kn5, so on a Mac draft every station sat on the line's
north-south mirror image. It now reads the file's `frame` (test added).

## The re-key (by position, never by arc length)

Each value -> its point on the old line, in the frame that value is keyed to -> the nearest point of the new line in
the same kind of frame (searched within 250 m of its proportional station, so the frontage pair never cross). Old
frames: `centerline.local.json` (draft, 9,697.6 m) and the 0.31.1 `finished_centerline.json` (swept, kn5 frame,
9,674.3 m); new: 9,662.5 m and 9,655.4 m.

| key | frame | old | new | old point to the new line |
|---|---|---|---|---|
| `layouts[race, street].start.line_vertex` | draft vertex | 2805 (8,420.3 m) | 2782 (8,354.6 m) | 0.53 m |
| `layouts[].start.grid_vertex` | draft vertex | 2795 (30.0 m behind) | 2772 (30.1 m behind) | 0.41 m |
| `layouts[].start.sector_vertices` | draft vertex | [655, 1730] | [637, 1709] | 1.29 / 0.33 m; at 0.333 / 0.666 lap; both pass layout_dummies' straight check |
| `layouts[].start.offset_right_m` | m right of travel | 1.9 | 1.9 (kept) | see below |
| `capture.bridges[e56th]` center_m / len_m | swept (the deck's start) | 2463 / 118 (deck 2,404-2,522) | 2415 / 118 (deck 2,356-2,474) | 3.2 / 2.9 m (56th's median line) |
| `capture.bridges[e56th]` profile_m, profile_ramp_m | metres from the deck's start | unchanged | unchanged | heights absolute |
| `capture.bridges[quebec]` center_m / len_m | draft | 5950 / 130 | 5887 / 128 | 0.6 / 0.2 m |
| `capture.bridges[e46th_leg]` center_m / len_m | draft | 6549 / 110 | 6484 / 110 | 1.1 / 1.5 m |
| `road_profile.crossfall.spans_m` | swept | [[2540, 2740]] | [[2491, 2690]] by position (1.1 / 0.0 m), then started at 2540: see the camber section | |
| `route.grid.exclude` | piece name | grid_tertiary_94 | grid_tertiary_93 | the same OSM piece, matched by geometry (mean distance 0.0 m): pieces are numbered by length, and the lap change renumbered them |

- **offset_right_m kept at 1.9.** Kept on the ground, the pole would be 2.31 m right of the new line (the old line ran
  0.41 m left of OSM there), and on this 7.5 m one-lane frontage road the outer grid column would put a car 0.5 m past
  the built edge (0.1 m with 1.9). The pole stays at the same place along the road and 1.9 m right of the road's
  centre: 0.41 m from its old spot on the ground.
- The bridges' OSM ways on the new line agree: E 56th 2,358-2,478 (ways 628655280 + 44769372), Quebec 5,854-5,956,
  E 45th 6,460-6,514.
- **Draft vs swept at the decks (0068's two frames).** On the OSM line they differ by 3.8 m at the E 56th deck's start
  and by 4.0 / 4.7 m at Quebec / E 45th (14 m and 19 m on the KML line). build_mesh's auto-detected spans
  (`bridge.spans.auto.json`): E 56th 2,366-2,468 against the declared deck 2,356-2,474 (0.32.0 on the old line:
  2,426-2,528 against 2,404-2,522, 22 m late at the start), Quebec 5,864-5,942, E 45th 6,473-6,506. The
  `_bridge_detector`'s draft/swept station mix is its own item; the line change shrinks it, it does not fix it.
- Not re-keyed, and why: `source/realworld_capture.json` (the phone capture's stations are on the old line;
  `capture.use_elevation` is false, so no draft step reads them; re-project them before turning it back on); the
  parked reverse layout declares no start; the PC's gate files (`dummies*`, `drive_test*`, `kn5_ground_check*`,
  `audit.json`, ...) are the 0.31/0.32 build's and the next chain overwrites them. `data/gate_centerline.json` (the old
  kn5's line, which drive_test prefers over the swept line) is deleted, as `draft_mesh` does.

## The camber at the 56th Ave turn, re-measured

`tools/lidar_crossfall.py tracks/sand-creek`, a full refetch (208 EPT nodes) along the new swept line: 3,219 stations,
236 not a road fit. Over the re-keyed span (new 2,491-2,690), as measured: +1.0 % at 2,496 to +4.1 % at 2,532 (the roll-in, 0.2 %/m), then
4.3 to 5.1 % to 2,574, 2.4 to 4.9 % to 2,616, easing to flat by 2,664. 0.31.1 read +1.2 -> +4.2 % over its roll-in and
2.6 to 4.5 % through. The shape holds; the peak is 5.11 % (2,538) against 4.56 %: the fit now centres on the slip's
OSM line, not Google's, and the raw reading there is 6.3 %.

**But laid as measured it made four severe steps** (2,529-2,532, 6.3-6.9 cm, on the centre wheel paths): the roll-in
(+1.9 -> +5.1 % over 2,519-2,537) runs across the slip's merge into Sand Creek Dr, where the ribbon flares 5.5 -> 23 m
(2,516-2,525) on a 5 % fall. A Mac A/B of the same draft proved it:

| crossfall span | camber at the merge | severe | kinks /km | steps /km |
|---|---|---|---|---|
| [[2491, 2690]], as re-keyed | rolls +1.9 -> +5.1 % across the flare | 4 | 9.42 | 2.28 |
| [[2491, 2515], [2545, 2690]] (zeroed across the flare) | 1.4 % -> 0.2 % -> back up: in, out and in again | 0 | 5.90 | 1.55 |
| **[[2540, 2690]] (starts just past the merge): chosen** | 0.4 -> 1.3 % across the flare | **0** | **6.63** | **2.07** |

So the span now starts at 2,540, the least invasive change the evidence supports (config only, no tool or gate
change; the zeroed variant reads a little smoother but makes the camber roll in, out and in again, which the real road
does not). The turn reads +1.3 % at 2,529 rolling to +4.1 % at 2,556 (the 0.2 %/m limit, from about 20 m later than the
road's own roll-in), then 2.4 to 4.9 % through to 2,619, flat by 2,664; max 4.93 %. What it gives up: the measured
+3.5 to +5.1 % at 2,529-2,540, the first 20 m of the real roll-in, is laid at 1.3 to 2.2 %. The cure that keeps it is
0070 B's (no 23 m flare at a slip merge), not a crossfall rule.

## Before and after (Mac drafts: gps, elev, project, widths, grid, build_mesh, drive_test, audit_mesh)

Baseline: 0.32.0 (the camber, main's terrain-mirror fix and 0068's measured deck) on the KML line; the camber-only base
(before the deck merge) in brackets where it differs.

| | 0.32.0, KML line | 0.33.0, OSM line |
|---|---|---|
| lap, draft / swept | 9,697.4 / 9,674.1 m | 9,662.3 / 9,655.4 m |
| zig-zag p95 per 30 m, draft / swept (0070's measure, full precision) | 13.85 / 5.10 deg | 0.34 / 0.38 deg |
| the same on the written files (1 cm coordinates: a 1.5 deg floor) | 14.24 / 5.02 deg | 1.53 / 1.53 deg |
| swept line from the OSM ways outside the declared corners, p50 / p95 / max | (0070: 0.60 / 2.56 / 4.7 m) | 0.05 / 0.21 / 0.82 m |
| min radius, swept | 4.0 m | 8.0 m (E 50th -> Ash, declared) |
| swept vertices under R 10 m / 15 m | 19 / 25 | 4 / 19 |
| vertices where the flared half width >= the local radius (the pleat guard's case) | 24 | 17 (at the 33-34 m corner flares: 0070 B) |
| drive_test race / street | PASS / PASS | PASS / PASS |
| severe steps | 1 (s 1,275) | 0 |
| kinks /km | 14.89 (15.61) | 6.63 |
| steps /km | 2.79 | 2.07 |
| fold bumps / vertex bumps (reported) | 23 (21) / 9 | 20 / 6 |
| excursion drops / far ledges | 4 / 10 | 7 / 8 |
| soft top in lane, obstruction, floating furniture, ground on top, daylight | 0, 0, 0, 0, 0 | 0, 0, 0, 0, 0 |
| replication max | 0.57 m (4.08) | 0.52 m |
| audit_mesh | 3 issues: B terrain pokes 3 (+0.45 m) | CLEAN |

Both layouts read the same numbers (one road kn5; neither declares race furniture).

- The OSM line with the re-keyed span as measured read 4 severe steps (kinks 9.42 /km, steps 2.28 /km), all at the
  slip's merge; the A/B above found the cause and the span start removed them. Every other number is the same in both.
- **Excursion drops 4 -> 7**: verge ledges 11 to 12.5 m off the line, six of them 0.12-0.13 m; the worst, 0.52 m at
  7,803 (E 45th North Dr by I-70), is 0.32.0's 0.35 m at 7,951, the same embankment edge, now nearer the line.
- The baseline's one severe step (1,275, the E 50th -> Dahlia approach) and its three terrain pokes are gone.

## Tests

`tests/gps/test_fillet.py` (new, 7): a declared corner is the circle of its radius tangent to both legs; a node is
rounded inside its segments; an off-route or overlapping corner is refused; the 0.25 m merge keeps a curve's radius
through a way join; start_at becomes an exact vertex; build_centerline end to end from an offline snapshot; a route
without `route.fillet` is stitched as before. `tests/tools/test_lidar_crossfall.py`: a draft's mesh-frame line.

## Proof owed

- **A PC chain build** of 0.33.0 (`tools/ship_track.sh sand-creek`): the underlay drops the new GEN_* draft into
  loop.blend (the origin is pinned, so the AUTH_ layers stay registered), every gate on the built kn5, then install.
  `layout_dummies` and the spawn kn5 re-run on the new vertices; the AI lines are re-recorded on the new line.
  `ship.json` now syncs `data/osm.widths.cache.json` in, so the PC's widths read the same OSM snapshot as this draft.
- **Kevin's drive**: the corners (Colorado -> 50th, the Ash jog, 50th -> Dahlia, Dahlia -> 56th, Sand Creek Dr ->
  Quebec, 48th -> Colorado), the 56th slip and its camber, E 45th at the ramp split.
- Not done here: 0070 B (the flares and the paint), C (barriers), D (dressing). The pleat guard at the 33-34 m corner
  flares, and giving the slip's camber back its first 20 m (2,520-2,540) once the merge has no 23 m flare, are B's.

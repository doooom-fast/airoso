---
id: 0098
title: "Sand Creek to finished, round 1 (Mac): the map-edge cut reached, the one-sided flares measured, both lamp heads lit, the owned surfaces"
status: 0.2.9 INSTALLED 2026-11-23 (PC: Runbook 0098-1 on the combined head 5a8e2c05, rehearsal 0209e SHIP OK, install build equal to it); known defect: the sandcreek_quebec deck edge hangs up to 0.935 m on the Northfield Quebec arms (round 2); not driven
scope: tracks/sand-creek-lm; tools (opt-in keys only; every other track's outputs unchanged)
layer: project + engine
train: -
---

## Request (Kevin, 2026-11-22, relayed by the coordinator)

> "let's complete lake murray, sand creek, and high plains"

then "go". This is Sand Creek's round 1, on the Mac. The orchestrator, later that day: Kevin wants the work spread across the
Mac, the PC and the G10 (below, "Scope").

## Kevin's answers (calls page, 2026-11-22, the option text verbatim)

| asked | Kevin |
|---|---|
| "One-sided junction flares, measured?" | "Build it with the disconnected-roads fix" |
| "Free roam: how much is part of finished?" | "Only the 7 streets onto the lidar" (NOT the 4-lane road east of the retaining wall) |
| "Two changed gate readings: confirm them?" | "Show me before and after first" |
| "The parked pad where the lap turns onto Quebec?" | "Build it on the PC with its lidar, no download" |
| "Light the back head of two-arm lamps?" | "Yes, light both heads" |
| "The owned asphalt and concrete on the other tracks?" | "On every track now" |

Mountains in Sand Creek: after Denver is done, not this round.

## Scope (the orchestrator, 2026-11-22) and the files the other pieces will touch

Kept on the Mac: the disconnected roads (1), the one-sided measured flares (2), the gate readings before and after (4),
the lamps (5), the owned textures (6), the version and this ledger (7). **Dropped from this round:**

- **The 7 streets onto the lidar: the G10 fetches and reads that lidar.** It will touch
  `tracks/sand-creek-lm/source/connector_profiles.lidar.round_i.json` (or a new profile file named by
  `lm_intake.connector_profiles` in `track.config.json`) and that key. Merge notes for it:
  - **Read each point at its own lon / lat.** The grid's points are in `tools/route_connectors._mpd`'s frame (a sphere);
    the lidar tiles and the lap are in `scripts.geometry.projection`'s (the ellipsoid). The same lon / lat is at
    (x · 1.0024949, z · 0.9985216) there, so a grid point (x, z) read as lidar (x, z) is read 0.25 % of x toward the
    origin in x and 0.15 % of z away from it in z: 4.7 m off at the grid's east edge, 2.0 m at its north edge (measured: the lap to OSM's own ways is 0.05 m median in the ellipsoid's frame and 1.32 m in the sphere's;
    the grid to OSM is 0.00 m in the sphere's and 1.39 m in the ellipsoid's). Round I's 99 profiles were read that way.
    Re-read at the street's own position (the Mac's 353-tile cache, `--surface`, nothing fetched), they move median
    0.026 m, p95 0.132 m, max 1.35 m (grid_residential_19); 8 streets more than 0.25 m somewhere, 3 more than 0.5 m, 1 more
    than 1 m (grid_residential_19 1.35, grid_primary_66 0.80, grid_secondary_45 0.56). Not changed this round.
  - **What the right frame does to the 7 (measured on the Mac's tiles, `--surface`, nothing wired):** grid_secondary_8,
    grid_secondary_42 and grid_primary_71 lose round I's jumps (largest neighbour step 1.38 / 0.74 / 1.25 m read beside the
    street, 0.32 / 0.48 / 0.48 m at the street). grid_secondary_39 keeps 0.52 / 0.99 / 0.59 m at x 443-461 and 626 (4-7
    returns a point). grid_primary_11's first 30 m lie on a deck (class 17 at 31.0 m, ground 29.0-29.6 m under it), then
    fall 7 m in 25 m. grid_unclassified_77 dips 3 m at x 1361-1367. grid_primary_15 is the viaduct: it reads smoothly on
    the deck (0.16 m), and still needs a street-bridge path so its terrain band does not bury two houses (round J).
  - **grid_primary_71 is reached in this round** (below): if its profile changes, nothing needs re-running.
    `tools/lm_engine_intake.apply_grid_reach` re-eases the joint onto the end height the piece has then, using the
    record's `from_y`.
- **The sandcreek_quebec / dahlia_56th pads and the side-street join leftovers: a PC session, from the PC's caches.** It will
  touch `lm_pads` in `track.config.json` (the `parked` to `pads` move), `source/pads/sandcreek_quebec.json` /
  `dahlia_56th.json`, `route.verify_mouths_allowed` and `route.verify_mouth_corners_allowed`, perhaps
  `tools/trim_connectors.py`. The mutual-T rank at N Ivy / E 50th is described under "Not done". Merge notes for it:
  - This round touches the lap's line and widths only at **v2657-2667** (E 45th North Dr, the one flare that moves).
    It touches nothing in **v767-787** or **v1937-1946**. v1895-1922 is declared, measured, and moves 0 rows. The coordinator
    relayed this answer to the PC session.
  - New mouths: grid_primary_71#0 (start) on the lap at host_vertex 2050 (cut (1636.8, -770.0)). grid_primary_78#0 (end,
    v1936) and grid_primary_84#0#0 (start, v1942) are unchanged.
  - **16 pieces are renamed** by trim, one cut level more, once E 56th is built. Every row and radius that names them
    follows; see "1".

## 1. The disconnected roads (ledger 0086, "Disconnected roads located")

### The causes, measured

- **The map-edge cut (the largest group).** `tools/grid_connectors.py:180-183` clips every OSM way 60 m inside the
  SOURCE track's 3DEP grid (lat 39.798823, grid z 1313.9). The port's own grid reaches 39.801706. E 56th Ave runs at
  z 1315-1336, just past the clip, so it was never built. 11 street ends and Quebec's two carriageways stop 2.5-10 m short
  of it: Grape, Holly, Kearney, Krameria, Leyden, Locust, Monaco, Magnolia, Niagara, Newport, Roslyn, Quebec SB / NB.
  E 56th's built stretch (grid_primary_80) ends at its node with Eudora.
  - **Why the clip is not simply moved.** Re-running grid_connectors on the port's grid would rename every piece (pieces are
    named by length rank). Every re-resampled point would need a 3DEP point fetch (a download), and every lidar profile is
    checked point by point.
  - **What is done instead: the cut pieces are REACHED, additively.** No existing point or name moves.
- **Northfield Quebec's 160 m piece (grid_primary_71 / 73), 8.6-12.95 m short of the lap at E 45th.** The lap leaves
  Quebec on the slip to E 45th (v2044-2074, OSM primary_link) and never passes the Quebec / E 45th node 71 starts at.
  - The 25-40 m of Quebec southbound between them was under `route.grid.min_piece_m` (40 m) and dropped.
  - Quebec northbound north of E 45th runs beside the lap and was dropped as the lap's other carriageway
    (`route.grid.parallel_m`), so 73 ends at E 45th on nothing.
- **The frame (found on the way, above).** The grid is displaced against the lap and the lidar by 0.25 % of x and 0.15 % of z
  (4.7 m at its east edge, 2.0 m at its north edge). That is part of every gap the finder reads near the grid's edges (71's start: 4.1 m in x,
  1.2 m in z). It is reported, not moved: moving it moves every street, and every overlay measured on them.

### The fix (all opt-in, Sand Creek only)

- **`tools/grid_reach.py`** (new) walks a piece END, named in `route.grid.reach`, along the OSM way it lies on.
  - It uses the source's `data/osm.ways.json`, `route.grid.classes` and grid_connectors' projection, going way to way
    through OSM's nodes: the straightest continuation, or toward a `via` OSM vertex at a fork.
  - It resamples every 3 m as grid_connectors does, up to a `stop`: a line (`x_max`), or "on" a road (grid_connectors' own
    on-lap rule).
  - Heights come off the lidar at the point's own lon / lat (lidar_connector_profile's reading, `--surface`, on the Mac's
    tile cache; a missing tile is no reading, never a fetch). Elsewhere they are the port's 3DEP grid, moved by the lidar
    offset interpolated between its read neighbours (lidar_connector_profile.fill's rule).
  - The joint is eased onto the piece's own end height over 30 m (trim's BLEND_M).
  - It writes `source/grid_reach.json`; `tools/lm_engine_intake.apply_grid_reach` (`lm_intake.grid_reach`) adds the points
    after the profiles.
- **Three records** (md5 c7b10bc6…, 45,355 B):

| piece end | walked | to | points | heights |
|---|---|---|---|---|
| grid_primary_80 (start), E 56th Ave | 2,526.7 m along OSM's E 56th, its eastbound carriageway past the fork at x 1420 (via OSM vertex (1508, 1322)) | x 1877.5, the grid's own east extent (the same clip's) | +843 | 377 lidar, 466 3DEP + offset (14 tiles of row z 1300-1400 not on the Mac); lidar - 3DEP -0.57 .. +1.00 m, median +0.19; largest neighbour step 0.168 m; steepest 5.6 % |
| grid_primary_71 (start), Quebec SB | 19.2 m north along OSM's Quebec SB | the lap (11.8 m from its centre line) | +7 | 7 lidar |
| grid_primary_73 (end), Quebec NB | 11.3 m west along OSM's E 45th | grid_primary_71 | +4 | 4 lidar |

- **The 11 street ends and Quebec's two need no record.** Once E 56th exists, `trim_connectors`' own REACH (15 m) takes each
  to it: 13 new mouths on grid_primary_80#0. With 71#0 on the lap and 73#0 on 71#0, there are **15 new mouths; 113 → 128**.
  The dry trim (lm_intake + trim on the committed inputs, pure python) gives the chain's 128 mouths, the same
  pieces and names; without `lm_intake.grid_reach` it gives m7d's `connectors.local.json`, `mouths.json` and
  `street_junctions.json` byte for byte. sc9a (no flares) and sc9b differ in one cut only: grid_unclassified_81's at the
  flare, 5 cm (the line moved there).
- **Trim names 16 pieces one level deeper** once they are cut at E 56th:

| was | now |
|---|---|
| grid_primary_6 | grid_primary_6#0 |
| grid_primary_71 | grid_primary_71#0 |
| grid_primary_73 | grid_primary_73#0 |
| grid_unclassified_57 | grid_unclassified_57#0 |
| grid_unclassified_82 | grid_unclassified_82#0 |
| grid_residential_22 | grid_residential_22#0 |
| grid_residential_12#0, 19#0, 21#0, 24#0, 26#0 | grid_residential_12#0#0, 19#0#0, 21#0#0, 24#0#0, 26#0#0 |
| grid_residential_29#0, #1, #2 | grid_residential_29#0#0, #0#1, #0#2 |
| grid_residential_47#0, #1 | grid_residential_47#0#0, #0#1 |

  `source/mouth_radii.naip.json` moves 24 corner keys and 32 host names to the new names (the same corners; no radius
  changed). Two `verify_mouth_corners_allowed` rows follow (19#0 → 19#0#0, 29#2 → 29#0#2).
- The new mouths' corner returns take the median radius (7.5 m) of the measured corners: the NAIP measure (tools/mouth_radii.py)
  needs the built workshop and reads NAIP in the lap's frame (owed, below).
- E 56th's westbound carriageway x 1420-1877 is not built (owed). Quebec and Roslyn meet the eastbound one, which carries
  the street. What lies north of E 56th stays off the map: Kevin's "Only the 7 streets".

### sc_disconnects, before and after (the same tool, the same OSM)

| group | before: m7d (0.2.7's gate OBJ; 0.2.8 changed only the lap's strip) | after: sc9b (0.2.9) |
|---|---|---|
| places | 233 (113 mouths, 63 ends, 57 OSM junctions) | 236 (128 mouths, 48 ends, 60 OSM junctions) |
| NOT CONNECTED (separate drivable sheets) | 6: Quebec's two north ends (7.0 / 6.9 m), Northfield Quebec 71 start / 73 end at E 45th (12.95 / 8.6 m), 71 end / 73 start at the south map edge (7.5 / 7.4 m: the two one-way carriageways at the world's edge) | **2**: only the two one-way carriageways at the south map edge, 7.5 / 7.4 m apart, as before |
| dead ends where OSM has a junction or the road going on | 52: OSM_JUNCTION on the clip box 13, OSM_JUNCTION 11, OSM_CONTINUES on the clip box 16, OSM_CONTINUES 6, the 6 above | **37**: OSM_JUNCTION on the clip box **1** (grid_unclassified_97 start, the west edge, 6.6 m to E 52nd Ave), OSM_JUNCTION 11, OSM_CONTINUES on the clip box 16, OSM_CONTINUES 7 (grid_primary_6#0 end, renamed), the 2 above |
| OSM junctions with no mouth | 57 (56 with one built road: 41 at an unbuilt link or ramp; 1 crossing two built roads, Quebec 6 / 7 at a primary_link) | 60: +4 on E 56th, its cross streets north of it not built (Eudora St, Fairfax St, two primary_links); -1 (E 45th / Northfield Quebec, now a mouth) |
| mouths with a hole > 0.2 m on a wheel line | 11 (N Ivy / E 50th 5.1 / 4.9 m; E 46th / 45th N Dr 5.4; Quebec 7 / 6 5.2; Colorado 49 / 52 5.15; the I-70 bridge 2.95 / 2.0; 4 at 0.35-1.3) | 12: the 11, plus grid_primary_71#0 at the lap 1.40 m (no corner return there, below) |
| holes on the wheel lines, worst | 12.05 m (E 45th / Northfield Quebec, the floating piece) | 12.0 m, at an unbuilt residential street off E 52nd Pl (as before). E 45th / Northfield Quebec: 12.05 → 7.15 m, an unbuilt motorway link |

- **Closed: 15 dead ends and 4 separations.** E 56th's 11 street ends (Grape, Holly, Kearney, Krameria, Leyden, Locust,
  Monaco, Magnolia, Niagara, Newport, Roslyn) and Quebec SB / NB now meet E 56th. Northfield Quebec 71 start / 73 end meet
  the lap / 71. Every new mouth is one drivable sheet with its host (0 disconnected mouths).
- **The 15 new mouths, as the finder reads them:** the 13 on E 56th: step 0.000, slab-edge hang 0.021-0.028 m, the strip's
  kerb lip 0.18-0.21 m (route.edge's no-curb strip falling 0.2 m, as at every Sand Creek mouth), no hole. 73#0 on 71#0:
  step 0.113 m, hang 0.033. 71#0 on the lap: step 0.194 m, hang 0.178, hole 1.40 m (no return; see "The Mac rehearsal").
- **Left: 37 dead ends.**
  - 16 on the clip box, with the road going on 18-209 m past them: the world's edge. One of them is E 56th's new east end
    at x 1877.5.
  - 1 at the west edge, 6.6 m short of E 52nd Ave / the Vasquez frontage.
  - 11 at a junction with a street not built (US 6-85, an unnamed residential, a link) or on a pad.
  - 7 where OSM's road goes on: Colorado and its frontage roads at the pads, and grid_primary_35's start (E 56th west of
    the lap). The finder's box grew with E 56th, so that end no longer reads as "on the clip box".
  - 2 the south edge's carriageways.

## 2. One-sided measured flares (ledger 0087 section 7 Q2)

ledger 0087's census (on 0.2.6's gate centre line) lists 30 lap width bumps over 1 m. A street joins both sides at 4 of them,
one side at 5, none at 21. The 5 one-sided ones, and what this round does:

| lap stations / vertices | where | lidar on the Mac | this round |
|---|---|---|---|
| s 2292-2344, v769-787 | the 56th → Sand Creek Dr merge, the parked dahlia_56th pad | no: tile (-9, 10) | not declared: the PC's pad session |
| s 5680-5740, v1895-1922 | grid_tertiary_5's mouth, Sand Creek Dr S | yes (1 tile missing at the far end) | **declared, measured: 0 rows move** |
| s 5761-5835, v1924-1950 | the I-70 bridge mouths, the parked sandcreek_quebec pad | no: tile (17, -5) | not declared: the PC's pad session |
| s 7968-8001, v2652-2676 | grid_unclassified_81's mouth, E 45th North Dr / N Grape | yes | **declared, measured: 11 rows move** |
| s 9536-9618, v3182-3211 | inside the built 48th_colorado pad | yes | not declared: the pad's measured deck is the junction there |

- **`tools/flare_one_sided.py`** (new) reads the far side of each declared flare off the source lidar, per lap vertex.
  - The cross-section is class-2 medians every 0.25 m, within 0.75 m along.
  - The step map is lidar_curb_trace's.
  - The edge is the innermost rise (a curb) or fall (the platform's edge) of 0.08 m or more (naip_edge.STEP_M). It is
    searched from 1.5 m inside the street's own half width (the running minimum of the widths over +-25 m, 0087's census)
    to 1.5 m past the flared half.
  - A 5-row running median is applied along the flare.
  - The applied far half is held between the street's own half and the flared half, interpolated between read rows. **No
    row moves where nothing was read.**
- It writes `source/flares_one_sided.lidar.json` (md5 231065b1…, 17,339 B). `tools/lm_engine_intake.apply_flare_one_sided`
  (`lm_intake.flare_one_sided`) keeps the near side and moves the vertex half the difference toward the street. The record
  names its vertices and positions and is refused on any other line.
- The street sides are read off the built `data/mouths.json` cuts, and OSM has no street on the far side of either:
  - **Sand Creek Dr S (v1895-1922), street on the right:** the far side is road crossfall (-1.5 % to -2 %) out to 10-12 m
    from the line, then an embankment drops 0.4-1.2 m. The source's flared half is 10.5 m and the street's own is 7.25 m.
    The edge was read at 2 rows (drops at 11.62 / 10.62 m, past or at the flare) and was not resolved at 26 (the drop
    starts past the search window). **The paved and graded platform is as wide as the flare: nothing narrows.** The
    flare is not a phantom here.
  - **E 45th North Dr / N Grape (v2652-2676), street on the right:** curbs at 13 of 25 rows (12 rises, 1 fall), 4.1-5.9 m
    from the line where the source's half is 6.0 m. Where the source is at the street's own width (v2652-2656), the clamp
    keeps it. **v2657-2667: the far (left) edge comes in 0.12-1.13 m and the line moves 0.06-0.565 m toward the street;
    the near edge stays where it was** (a test pins it).
- No gate or threshold changes. The constants are in GATES-CHANGELOG 2026-11-22.

## 3. The 7 streets onto the lidar: dropped from this round (the G10's), with the measurements above

## 4. The two gate readings, before and after (Kevin: "Show me before and after first")

The same build data each time: one built workshop and one OBJ set. Only the key is changed (a scratch copy with the key
deleted). Nothing else changed, no gate or threshold.

**`drive_test.vertex_kinks`** (ledger 0079 round P): a slope kink over 3 %/m is re-measured on the wheel path's own travel.
One under 3 %/m is reported, not counted. Sand Creek gates no kink rate (no `gates.drive_test.kinks_per_km_max`), so the
key changes a reported number and no verdict.

| build | layout | key ON (as shipped) | key OFF |
|---|---|---|---|
| m7d (0.2.7) | street | PASS; kinks 0.52 /km counted, 14 re-measured under 3 %/m (station reading 1.97 /km) | PASS; kinks 1.97 /km |
| m7d (0.2.7) | race | PASS; kinks 6.85 /km, 39 re-measured (station 10.89 /km); severe 22 (10 deferred to fold_fans) | PASS; kinks 10.89 /km; severe 22 |
| sc9b (0.2.9) | street | PASS; kinks 0.52 /km counted, 13 re-measured (station 1.87 /km) | PASS; kinks 1.87 /km |
| sc9b (0.2.9) | race | PASS; kinks 6.85 /km, 39 re-measured (station 10.89 /km); severe 22 | PASS; kinks 10.89 /km; severe 22 |

**`fold_fans.wall_frame: "local_deck"`** (round P): verify_fold_fans (7) reads each wall cell against the deck under the
wall triangle, as no_route does. This one decides a verdict:

| build | key ON (as shipped) | key OFF |
|---|---|---|
| m7d (0.2.7) | PASS: 2 levelled pinches x 2 layouts; race chord 3190-2 walls worst -0.278 m over (band +-0.28) | **FAIL**: race chord 3202-3207, (7) 14 race-wall cells within 25 m of X outside the band; worst -0.431 m at (-1491.2, -282.8) (the S at 48th / Colorado, K-rails on the measured deck ~0.4 m under the lap's centre line) |
| sc9b (0.2.9) | PASS; walls worst -0.152 m (chord 122-154) / -0.278 m (chord 3190-2) | **FAIL**: the same 14 cells, worst -0.431 m at (-1491.2, -282.8) |

Every other row of both gates is identical ON and OFF. The keys stay as they are, for Kevin.

## 5. Both heads of the two-arm lamps lit (Kevin: "Yes, light both heads")

- `scenery.streetlights.light_both_heads: true` (opt-in; LED model with arms 2 only, refused otherwise). The twin post's heads
  stand at +-4.42 m. `tools/author_lamps_blend.py` lays the back head's lens too: the road-ward lens mirrored through the pole
  (lens centre -4.04 m road-ward), with its winding kept, since a mirror flips it once more.
- Both lenses are recorded in `provenance.lens_xyz` (road-ward first), with `heads_lit` 2. A self-check refuses two lenses
  closer than LENS_APART_M (2 m), which ext_config would cluster into one light.
- `tools/check_lights_ini.py` expects the lamp count times `heads_lit` (1 when absent), one light per recorded lens. Every
  other rule and tolerance is unchanged (GATES-CHANGELOG 2026-11-22).
- sc9b: 171 lamps (175 placed, 4 dropped on a road as before), **342 lenses**; `[ext_config]` 342 [LIGHT_N];
  `[lights-ini] 342 [LIGHT_N] for 171 lamps, 342 at their lens: PASS`; kn5_ground_check: 171 lamp posts, 0 hovering.
  The light's look (lighting.streetlight) is unchanged: each lamp now casts two of them.

## 6. The owned asphalt and concrete (Kevin: "On every track now")

- `texture_overrides["1ROAD"]` → `assets/textures/asphalt_dense_{diffuse,normal}.jpg` (339c4244… / 7a71dfce…), in place of
  the borrowed cracked tile (LA Canyons, personal use). It binds the lap, every grid street and the pads (all 1ROAD).
- `texture_overrides["1KERB_SIDEWALK"]` → `assets/textures/concrete_plain_{diffuse,normal}.jpg` (d77c7ca9… / 2692b423…).
  Its generator says it is MEANT FOR 1KERB_SIDEWALK. It replaces Hamburg's board-formed concrete (`building_diffuse.jpg`,
  mined). On m7d the 1KERB_sidewalk_* meshes (every edge strip, corner return and the fork 91/92 island) are the only
  meshes of the road kn5 that bind building_diffuse.jpg: 4 of 128.
- `ship.json sync_in.assets` names the four. `assets/licenses.json` already lists them (CC0, tools/make_owned_surfaces.py):
  **nothing to add**. Both pairs' mean colours were measured off the files they replace.
- **`road_wear.detail_highpass_m` is not set.** It is a road_wear key and Sand Creek has no road_wear bake, so the high-pass
  has nothing to act on: the owned tile is used as made, on the 4 m planar grid. Bringing road wear to Sand Creek (an aerial
  crop and lines) is a separate call. `tests/aerial/test_road_wear_highpass.py` now lets Sand Creek bind the pair without
  the high-pass.

## 7. Version, shared files, tests

- **0.2.8 → 0.2.9** (`track.config.json version`). `fleet/ac-installed.json` is unchanged; on an install it needs Sand
  Creek 0.2.9's row, as every install writes it.
- **Shared files touched** (every change opt-in, a no-op without its key):
  - `tools/lm_engine_intake.py` (`apply_grid_reach`, `apply_flare_one_sided`);
  - `tools/author_lamps_blend.py` (`light_both_heads`);
  - `tools/check_lights_ini.py` (`heads_lit`);
  - `tools/split_strip_blend.py` (`route.split_strip_balanced`: the Lariat's draft step `split_strip`, with a balanced mode
    for a strip that carries side streets);
  - `tools/grid_reach.py` (new);
  - `tools/flare_one_sided.py` (new);
  - `fleet/GATES-CHANGELOG.md`;
  - tests: `tests/tools/test_sand_creek_0098.py` (new, 14), `test_sand_creek_lm_assets.py`, `tests/ac/test_verify_kn5_layouts.py`
    (the version pins), `tests/aerial/test_road_wear_highpass.py` (Sand Creek's pair).
- No other track's config names a new key (`test_the_0098_keys_are_opt_in`). lm_intake on the committed inputs without
  the keys reproduces m7d's trim outputs byte for byte (above).
- **Tests:** the full suite on the Mac, `PATH=<venv>/bin:$PATH python -m pytest -q -p no:cacheprovider tests`: **1,724 passed,
  0 failed** (main 9aacb34c: 1,710). The Sand Creek files and those of every touched tool pass.

## The Mac rehearsal

Two empty workshops on the Mac (`tools/ship_track.sh sand-creek-lm --no-install`, SHIP_PROJ scratch, AIROSO_NUMPY_PY the
venv, ENG the engine-july snapshot with `assets/textures` beside it, Blender 4.2.9). The runner changes only the Blender path,
the workshop root, bash 3.2's `${tok^^}` and `declare -A` (Sand Creek has one race layout) and AIROSO_MAIN. None of those is in
the repo.

- **sc9a** (this branch before the flares and the strip split, the content of a217d3fe + c9eb5094 less the flares): draft and author clean (128 mouths, 223 returns, both lamp heads). Then
  **the prep refused**: `'1KERB_sidewalk_2' has 67258 positions (> 65535) even after the split pass`.
  - The prep (ENG, not editable from here) cuts a non-terrain mesh into equal-WIDTH bands. E 56th's 2.5 km of strip and
    its 13 mouths' returns crowd the eastern band.
  - **Fix** (4aa9c037, opt-in `route.split_strip_balanced`): the Lariat's draft step `split_strip`
    (tools/split_strip_blend.py) gains a balanced mode. The strip, the lap's and every side street's, is tiled by median
    bisection before the prep. On sc9b: CURB 175,372 vertices → `1KERB_sidewalk_lm0..3` of 44,953 / 41,473 / 43,819 /
    44,600. pbr binds 1KERB_SIDEWALK (the owned concrete), the physics stay KERB, and nothing moves.
- **sc9b** (4aa9c037, everything, from an empty workshop).
  - Stopped at the ship step `treefx`: `0 trees written, 3471 planned; models absent: Oak3.bin, SycamoreV1-3.bin`. The
    TreeFX models are personal use and on the PC only (lm_intake: "none on this machine"). The gate (ledger 0089) postdates
    m7d. **Not a 0.2.9 defect.** Resumed `--from race_scenery_gate` to read every gate.
  - Then: `verify_mouth_corners` **FAIL**, 1 red mouth. The four gates after it were run by hand with the chain's
    commands.

| gate | m7d (0.2.7, Mac) | **sc9b (0.2.9, Mac)** |
|---|---|---|
| verify_kn5 / --inis | PASS / PASS | **PASS / PASS** |
| lights_ini | PASS (171) | **PASS: 342 lights for 171 lamps, every lens** |
| treefx | (no gate then) | **FAIL on the Mac only**: the models are the PC's |
| drive_test street / race | PASS / PASS | **PASS / PASS**: street severe 0, kinks 0.52 /km; race severe 22 (deferred 10, judged), kinks 6.85 /km |
| audit street / race | CLEAN / CLEAN | **CLEAN / CLEAN** |
| no_route BUILT (race) | PASS | **PASS**: leak 0 m², 0 doors |
| verify_fold_fans | PASS | **PASS**: walls worst -0.152 / -0.278 m |
| kn5_ground_check race / street | PASS / PASS; road_over_ground 17 / 12,956, p95 0.021, max 0.295 | **PASS / PASS; 16 / 13,494, p95 0.021, max 0.23**; 0 double sheets; 171 lamp posts, 27 sign posts, 0 hovering |
| verify_pads | PASS x4 | **PASS x4** (seams 0.9-1.6 mm) |
| verify_mouths | PASS 113 | **PASS 128** |
| verify_mouth_corners | PASS (21 allowed); lip median 0.02 / max 0.327; teeth 157 / 68,942 = 0.23 %; R9 median 0.013, p90 0.193 | **FAIL, 1 red mouth**; lip median 0.02 / max 0.327 (78, skipped as before); teeth 169 / 78,414 = 0.22 %; R9 median 0.012, p90 0.189. The 15 new mouths: 13 on E 56th lip 0.001-0.024, 73#0 on 71#0 0.023, **71#0 on the lap 0.199 m** |
| verify_race / verify_signs | OK / PASS 6 posts | **OK / PASS 6 posts** |
| house_seat / houses | PASS 1.261 m / 2,182 | **PASS 1.261 m / 2,182** (floor 2,181) |
| textures | 0 untextured | **0 untextured** (130 visible meshes; `asphalt_dense_*` and `concrete_plain_*` embedded, `asphalt_cracked_*` and `building_*` gone) |
| road / race / closure / street kn5 | 116,115,917 / 10,196,549 / 9,701 / 6,923,402 B | **121,802,258 / 10,196,549 / 9,789 / 7,259,818 B** (md5 0301ac31… / a870ea29… / 5601f505… / 9974e5f1…) |
| connectors / mouths | | `data/connectors.local.json` md5 448724bb…, `data/mouths.json` 45b2ef36… |

**The one red row: grid_primary_71#0 (start) → MAINLINE, corner lip 0.199 m.**
- It is the mouth this round made: Northfield Quebec walked onto the lap at the slip. The piece floated 12.95 m from the lap
  before.
- `mouth_returns` built no return there: "only 2 rows to fit the street's edge on". That is the class of 11 of 0.2.7's 21
  allowed rows (ledger 0086 "Owed after 0.2.7" item 3).
- **No allowance was added and no threshold moved** (an allowance is the coordinator's and Kevin's call; this round's rule).
  The choices:
  1. An allowed row like those 11, with its measured why.
  2. Drop the record for grid_primary_71 from `route.grid.reach`, which brings back the 12.95 m gap.
  3. The owed fix for a short edge fit (returns on fewer rows).

  The rest of the chain is green.

## Not done, owed

- **N Ivy / E 50th (the side-street join leftovers; the PC session's).** E 50th (grid_tertiary_2) starts on N Ivy's interior.
  N Ivy (grid_tertiary_4, joined with 46 and 37) ends on E 50th's interior at seg 943. Each piece ENDS on the other
  somewhere, so trim's RANK falls back to the hierarchy and cuts Ivy at E 50th's start: holes 4.9 / 5.1 m. A per-meeting
  rank would fix it: at a meeting, the piece that ends there is cut there.
- The new corners' radii off NAIP 2023 (tools/mouth_radii.py on a built 0.2.9 workshop; it reads NAIP in the lap's frame,
  so the grid's 1-4.7 m displacement applies there too).
- E 56th's westbound carriageway (x 1420-1877); E 56th's 466 points off the 3DEP grid (14 tiles of row z 1300-1400 are not on
  the Mac, listed in `source/grid_reach.json` `tiles_missing`).
- The dead ends at the other map edges (16 OSM_CONTINUES on the clip box): the world's edge, the road going on 18-209 m
  past it. Not reached: it would grow the map past "Only the 7 streets".
- Unbuilt cross streets (OSM junctions with one built road): links and ramps (not in `route.grid.classes`) and trunk US 6-85.
  Not built: new streets.

## Runbook 0098-1 (PC): rehearse 0.2.9 from an empty workshop, NO install

A rehearsal only, from an EMPTY workshop. Install nothing: the install is Kevin's word, which the PC asks for.

1. **Code.** A clean checkout of `origin/claude/sc-finish-20261122` at its head, with the 3 LFS blobs pulled. ENG = the
   engine copy the PC's Sand Creek builds use (runbook 4o: `eng_sclm_a`), with `assets/textures` holding the four owned
   files at these md5s: `asphalt_dense_diffuse.jpg` 339c4244d8b07494be81df14eb963c8c (2,346,705 B),
   `asphalt_dense_normal.jpg` 7a71dfcefbbce0267cb0d17f0c931fb0 (3,198,685 B), `concrete_plain_diffuse.jpg`
   d77c7ca9c8faa202951821133628a4e4 (262,056 B), `concrete_plain_normal.jpg` 2692b4231be5d2c24c6b4f0f3705bb84 (370,970 B).
   Copy them in from the checkout's `assets/textures` if they are missing (they are in the repo; nothing is fetched).
2. **Rehearse.** `set PYTHONUTF8=1`, `set AIROSO_NUMPY_PY=<the PC's python with numpy>` (the lidar venv, as 0091 / 0093
   ran), then with `SHIP_PROJ` a scratch folder that does not exist yet (for example
   `D:/k10-scratch/sand_creek_lm_0098_reh`):
   `SHIP_PROJ=D:/k10-scratch/sand_creek_lm_0098_reh ENG=<eng> bash tools/ship_track.sh sand-creek-lm --no-install > D:/k10-scratch/sc_0098_reh.log 2>&1`
   No `--from`, no `--skip-blend`, no force. The pads stay as the config has them (sandcreek_quebec / dahlia_56th
   parked): they are the PC pad session's, not this runbook's.
3. **Read, in order, against the Mac's column (the table above):**
   - draft:
     - `[lm_intake] the grid's map-edge cut reached (source/grid_reach.json): grid_primary_80 (start) +843 pts, 2526.7 m,
       grid_primary_71 (start) +7 pts, 19.2 m, grid_primary_73 (end) +4 pts, 11.3 m`;
     - `[lm_intake] one-sided measured flares ...: sand_creek_dr_s_tertiary_5 0 row(s) ..., e45th_n_dr_unclassified_81
       11 row(s), far side in up to 1.13 m, line moved up to 0.565 m`;
     - `[trim] 88 connector piece(s), 128 mouth cut(s)`;
     - `[gap-mouths] ... 128 mouths`;
     - `[returns] ... corner return(s)` (the Mac's count below);
     - `[lamps] 171 lamps ... lens 4v x 2 (both heads lit)`.
   - ship: `[ext_config] 342 per-lamp [LIGHT_N] entries`; `lights_ini_check.json` `n_lights` 342, `n_lamps` 171,
     `heads_lit` 2, ok.
   - gates: every row of the Mac's table, named, with its numbers. Call out any row that differs. Expected as on the
     Mac: `verify_mouth_corners` red at ONE mouth, `grid_primary_71#0(start)->MAINLINE`, lip about 0.199 m (the call in
     "The Mac rehearsal"); the chain stops there (hard). Then run the four gates after it by hand, as the Mac did:
     `python tools/house_seat_check.py <proj> --json <proj>/data/house_seat_check.json`,
     `python tools/house_gate.py <proj> --kn5 <proj>/build/sand_creek_raceway.kn5 --json <proj>/data/house_gate.json`,
     `python tools/verify_textures.py <proj> --json <proj>/data/verify_textures.json`, `python tools/edge_report.py <proj>`.
     The TreeFX gate should PASS on the PC (its four `.bin` models are there; the Mac has none).
   - draft, the strip split: `[split-strip] CURB (175372 vertices, ...) tiled by median bisection into 4 pieces:
     1KERB_sidewalk_lm0 (44953 v), ...lm1 (41473 v), ...lm2 (43819 v), ...lm3 (44600 v)`; and `[returns] 223 corner
     return(s) at 114 mouth(s) (radius measured 139, a median 84); 31 skipped`.
   - textures: 0 untextured; the road kn5 embeds `asphalt_dense_*` and `concrete_plain_*`, and no longer
     `asphalt_cracked_*` / `building_*`.
4. **The disconnects and the two readings on the rehearsal's own OBJ:**
   - `python -I tools/sc_disconnects.py --project D:/k10-scratch/sand_creek_lm_0098_reh --obj D:/k10-scratch/sand_creek_lm_0098_reh/data/track.obj --osm tracks/sand-creek/data/osm.widths.cache.json --out D:/k10-scratch/sc_0098_disc`
     and report its group counts against the table in "1".
   - On a COPY of the rehearsal workshop, with `drive_test.vertex_kinks` deleted from the copy's config:
     `python -m scripts.geometry.drive_test <copy> --layout street` and `--layout race`.
   - On another copy, with `fold_fans.wall_frame` deleted: `python tools/verify_fold_fans.py <copy>`.
   - Report the kinks per km (counted / station reading), severe, and verify_fold_fans' verdict and walls worst, next to
     the shipped keys' (section 4).
5. **Report:** SHIP OK or the first red row, with the numbers; the four kn5 sizes and md5s; md5 of the rehearsal's
   `data/connectors.local.json` and `data/mouths.json` against the Mac's (they should match: the same inputs, pure
   python); the run's start and end times.
6. **Owed to Kevin's drive (not the PC's call):** E 56th from Eudora to Roslyn, and its 13 mouths; Northfield Quebec at
   E 45th; the lamps at night (two lights a post); the road and the strips in daylight (the owned asphalt and concrete).

## PC, 2026-11-23: Runbook 0098-1 run on the combined head; 0.2.9 rehearsed and installed

The combined branch claude/sc-finish-0209-20261122 at **5a8e2c05**: the Mac's round 1, the PC's pads branch
(claude/sc-finish-pc-20261122) and the four fixes its rehearsals needed (ledger 0079, "PC, 2026-11-23" sections):
- the dahlia_56th config and box;
- SC-D56 skipped both ways;
- `ai.fillet_split`;
- `ground_on_mesh` for sandcreek_quebec.

ENG `D:/k10-scratch/eng_sclm_0209` (eng_sclm_a plus the four owned textures at the runbook's md5s); AIROSO_NUMPY_PY the
lidar venv. The pads are UNPARKED here (the Mac's sc9b had sandcreek_quebec and dahlia_56th parked), so the rows that
touch them differ from sc9b, as below.

**The rehearsal of record:** empty workshop `D:/k10-scratch/sand_creek_lm_0209e_reh`, `--no-install`, 05:33:29-06:37:12,
**SHIP OK**. Every row against the Mac's sc9b column:

| gate | sc9b (Mac, pads parked) | **0209e (PC, 5a8e2c05)** |
|---|---|---|
| verify_kn5 / --inis | PASS / PASS | **PASS / PASS** |
| lights_ini | PASS: 342 for 171, every lens | **PASS: 342 for 171, every lens, heads_lit 2** |
| treefx | FAIL on the Mac only | **PASS: 3,472 of 3,472 written; Oak3 + SycamoreV1-3 present; 186 rejected in the corridor** |
| drive_test street | PASS; severe 0, kinks 0.52 /km (13 re-measured, station 1.87) | **PASS; severe 0, kinks 0.62 /km (15 re-measured, station 2.18)** |
| drive_test race | PASS; severe 22 (10 deferred), kinks 6.85 /km (39, station 10.89) | **PASS; severe 26 (10 deferred, judged), kinks 7.57 /km (47, station 12.45)** |
| audit street / race | CLEAN / CLEAN | **CLEAN / CLEAN** |
| no_route BUILT (race) | PASS, leak 0, 0 doors | **PASS, leak 0, 0 doors, 87.8 k m2** |
| verify_fold_fans | PASS, walls worst -0.152 / -0.278 | **PASS, walls worst -0.152 / -0.278** |
| kn5_ground_check race / street | PASS / PASS; 16 / 13,494, p95 0.021, max 0.23 | **PASS / PASS; 52 / 14,158 (0.4 %), p95 0.022, max 0.935** (the known defect below); 0 double sheets; 171 lamp posts; sign posts 28 race / 26 street; 0 hovering |
| verify_pads | PASS x4 (seams 0.9-1.6 mm) | **PASS x6** (seams 0.9-2.7 mm; dahlia_56th 1.3 mm, node -0.015 m vs 3DEP; sandcreek_quebec 2.7 mm, -0.173 m) |
| verify_mouths | PASS 128 | **PASS 125**: the pads' arms replace 3 mouths (grid_primary_35 at dahlia_56th; grid_primary_78 and grid_primary_84 at sandcreek_quebec) |
| verify_mouth_corners | FAIL, 1 red (71#0 0.199); lip max 0.327; teeth 169 / 78,414 = 0.22 % | **PASS, 0 red**; lip median 0.02 / max 0.206; teeth 160 / 75,836 = 0.21 %; R9 median 0.012, p90 0.185. 78's 0.327 went with its mouth |
| verify_race / verify_signs | OK / PASS 6 posts | **OK / PASS 5 posts** (SC-D56, ledger 0079) |
| house_seat / houses | PASS 1.261 m / 2,182 | **PASS 1.261 m / 2,182** (floor 2,181) |
| textures | 0 untextured (130 visible meshes) | **0 untextured** (154 visible meshes, 25 textures; asphalt_dense_* and concrete_plain_* embedded; no asphalt_cracked_* / building_*) |
| road / race / closure / street kn5 | 121,802,258 / 10,196,549 / 9,789 / 7,259,818 B | **126,378,146 / 10,203,989 / 9,789 / 7,244,306 B** (md5 c843b909… / 1235b85d… / 5601f505… / a508e1b6…) |
| connectors / mouths | 448724bb… / 45b2ef36… | **f3ea862d… / f8113e8a…**: the pads' 3 mouths; the same in all five PC rehearsals of this head series |

The draft lines, against the runbook's:
- **The same:**
  - grid_reach: +843 / +7 / +4 pts.
  - Flares: tertiary_5 0 rows; unclassified_81 11 rows, 1.13 / 0.565 m.
  - Lamps: 171, both heads lit.
- **Changed by the pads:**
  - trim: 88 pieces, 125 cuts.
  - returns: 224 at 114 mouths, radius measured 139, median 85, 25 skipped.
  - split-strip: CURB 175,760 v into 44,908 / 41,233 / 43,726 / 45,077.

**grid_primary_71#0 (start) -> MAINLINE:** mouth_returns did not build it. The step's line: "NOT built: fitted past the
re-spread (rows 4-8), its edge line meets the host 10.2 m (+1) / 3.9 m (-1) from the street's own edge at the cut
(> 1.0 m)". Its lip is 0.199 m, ALLOWED by its 0098 row, so **the allowance row stays**.

**sc_disconnects on 0209e's OBJ** (236 places: 125 mouths, 51 ends, 60 OSM junctions):
- NOT CONNECTED: 2, the south edge's pair, 7.5 / 7.4 m (as sc9b).
- Dead ends: 40 (sc9b 37). The 3 more are the pad arms (35#0 end, 78 end, 84#0#0 start), which the finder reads as ends;
  it knows mouths, not pad arms. The groups: on-clip junction 2, junction 11, on-clip continues 17, continues 10.
- OSM junctions with no mouth: 60 (as sc9b).
- Mouths with a hole > 0.2 m on a wheel line: 10 (sc9b 12). The I-70 bridge pair (2.95 / 2.0 m) is not in the list. By
  inference those were the two Quebec mouths the pad replaces; not diffed.
- Worst hole 12.0 m and E 45th / Northfield Quebec 7.15 m, both as sc9b.

**The two readings on copies of 0209e**, one key deleted from each copy's config:
- `drive_test.vertex_kinks` off: street PASS 2.18 /km (severe 0); race PASS 12.45 /km (severe 26).
- `fold_fans.wall_frame` off: verify_fold_fans **FAIL**, race chord 3202-3207, the same 14 cells, worst -0.431 m at
  (-1491.2, -282.8). On (as shipped): PASS.
- The same pattern as section 4.

**The race severe, 26 against sc9b's 22:** +10 / -6, all from the two pads' flares, not the AI change.
- +10 at sandcreek_quebec: s 5810-5825, lateral -14.38 / -15.13, 0.060-0.082 m, the deck at the flared edge.
- -6 gone at Dahlia: s 2321-2331, lateral -19.18, the old flare.
- They are reported, not gated, and the Mac accepted them for 0.2.9.
- They also show that Quebec's 34.2 m flare at v1937-1946 is not the real road: the deck climbs about 0.39 m to its
  ribbon edge.

**KNOWN DEFECT of 0.2.9: the sandcreek_quebec deck edge hangs over the grass on the Northfield Quebec arms.**
- kn5_ground_check's road-over-ground max is 0.935 m, against 0.2.8's 0.295 m. The worst 8 samples sit on the pad's
  built outline: 0.935 m at (1807.17, -472.69), then 0.304, 0.288 and 0.254 m.
- sc_disconnects §5 reads the slab edge:
  - grid_primary_78 (end) hangs 1.068 m at (1811.95, -474.32), 42.1 m of edge over 0.05 m;
  - grid_primary_84#0#0 (start) hangs 1.033 m at (1811.99, -474.26), 29.7 m of edge.
- **The gate passes on p95** (0.022 m, gate 0.1 m), so the chain stays green.
- It predates `ground_on_mesh`: rehearsal 4's data, its pads built without the key and run on in a copy, read 0.934 m
  over 50 samples.
- Not yet located. The pad's build line reads deck_fill unfilled 146, smooth_moved max 0.88 m, seam residual max
  0.728 m. One reading, NOT proven: the deck is drawn up to the arms' ribbons while the ground stays pinned to the
  measured deck.

**Round 2's first items** (the Mac, 2026-11-23, in this order; then the rest of round 2 as listed in ledger 0079):
1. Quebec's 34.2 m flare off at v1937-1946, measured like Dahlia's.
2. The deck-edge overhang on the Quebec arms. Locate it first: it may be the same flare, or the arms' edge pinned
   above the bank. Fix it so no edge hangs over 0.30 m, with no threshold moved.
3. The SC-D56 plate (ledger 0079): the mesh stage stands a post on falling ground with no built walk. Then SC-D56
   comes back both ways, verify_signs (e, f) unchanged.
4. The race kink rise, 6.85 -> 7.57 /km: locate it.

**The install** (Kevin's standing word for a finished, green Sand Creek build: "When they're done, install them" /
"I always want newer builds"):
- 0.2.8's workshop was set aside as `D:/k10-scratch/sand_creek_lm.0.2.8`. The install build ran from a fresh EMPTY
  `D:/k10-scratch/sand_creek_lm`, 06:39:05-07:41:51, at 5a8e2c05 with the same ENG. SHIP OK, no force.
- The install step parked the installed 0.2.8 in `D:/k10-track-archive/2026-11-23_074151/`. Installed: "doooom
  Colorado — Sand Creek Raceway" and "... Sand Creek Free Roam" 0.2.9, in the plain `sand_creek_raceway`.
- **Against the rehearsal:**
  - 345 / 345 gate rows identical.
  - Road, `_race` and `_street` kn5 are kn5_equiv EQUIVALENT (tangents only, max 1.79e-07). The closure and both
    spawn kn5s are byte-identical.
  - connectors / mouths md5 are the same.
  - The four TreeFX `.bin` in AC's `extension/trees/` are at their source md5s (24111ede / 0986f1ea / 7010d61f /
    0ad53d67), and trees.txt is the rehearsal's (3,472 trees).
  - Both layouts' AI lines are byte-identical.
- **Menu pictures:**
  - Race (s0, phase 0) and street (s1, phase 0.5) were rendered off the installed split scenes with 0.2.8's cameras
    (`tools/menu_preview_blend.py`, exposure 0, no stand-ins). The camera and sun are the same as 0.2.8's sidecars.
  - They were cut into `source/ui/<layout>/` and copied over the pack's `ui/<layout>/preview.png`. The pack's own are
    in `D:/k10-track-archive/2026-11-23_074403_previews/`.
- `fleet/ac-installed.json`'s Sand Creek row: 0.2.9, sha 5a8e2c05, with the known defect named.
- The sync-back is with this note: 46 files under `tracks/sand-creek-lm` (data, ai, the synced-back loop.blend), no
  deletions.
- Not driven yet. Owed to Kevin's drive (Runbook 0098-1 step 6):
  - E 56th from Eudora to Roslyn and its 13 mouths;
  - Northfield Quebec at E 45th;
  - the lamps at night;
  - the road and the strips in daylight;
  - the two new pads (Dahlia / 56th, Sand Creek / Quebec, and the Quebec arms' edge above).

**The merge with main (4a5c38e0), 2026-11-23:** four conflicts, each resolved so every track's output stays as built.
- `fleet/GATES-CHANGELOG.md`: both sides kept, newest first.
- `tools/lm_pads_blend.py`: main's High Plains membrane fill (ledger 0097 round 3) and this round's `ground_on_mesh` each
  added a call that pins the ground under a pad. Now there is ONE call: the membrane's built deck, else ground_on_mesh's
  lower of deck_z and the deck mesh, else deck_z. A pad naming both is refused.
- `tests/aerial/test_road_wear_highpass.py`: Sand Creek's and Lake Murray's owned-road cases, unioned.
- **Both heads lit, the same key twice.** `scenery.streetlights.light_both_heads` is this round's (author_lamps_blend.py
  lights the back head in the lamps step) AND ledger 0099's (the author step lamp_heads). Lake Murray runs both steps, so a
  plain merge would have doubled its back heads. The Mac's call: `scenery.streetlights.both_heads_by: "lamps"`, Sand Creek
  only.
  - With it, the lamps step lights both heads and check_lights_ini reads heads_lit, wanting no heads file. lamp_heads
    refuses to run.
  - Without it (Lake Murray), the lamps step lights one head as before 0098; lamp_heads and lights.heads.json do the back.
  - GATES-CHANGELOG 2026-11-23 (PC); no threshold moved.
  - **Owed to Sand Creek round 2:** the two paths become one. Sand Creek moves onto lamp_heads (round 2 changes its LIGHTS
    mesh anyway) and both_heads_by goes.

## PC, 2026-11-23: round 2 (0.2.10), the Mac's order

Branch `claude/sc-finish-r2-20261123`, from main fcef3efe (PR 54, 0.2.9). The Mac's order, items 1-7, then the rest of
round 2 (ledger 0079):

1. **Quebec's 34.2 m flare off** (9663b80f): route.corner_flare_off gains the sandcreek_quebec corner; the intake re-lays
   v1933..v1951 between its legs' 18.00 and 16.50 m (v1942 34.2 -> 17.24 m).
2. **The deck edge hanging over the grass on the Northfield Quebec arms**: located and fixed (below).
3. **SC-D56 back, fwd only** (9663b80f; rev skipped after rehearsal 0210, the Mac's call): signs.json
   defaults.walk_built_only (opt-in) brings the fwd plate back.
   - Rehearsal 0210 (6769e802) stopped at verify_signs: FAIL SC-D56-rev c_built_edge_clearance. The scan's mesh
     clearance read 1.619 m (MAINLINE's 1.3-3.0), but the record's outside-edge polyline, the lap's own edge, which the
     dahlia_56th pad replaced there, read 11.12 m away. SC-D56-fwd passed every check (clear 1.644 / polyline 1.963 m;
     plate bottom 9.0548 = ground 6.9248 + 2.13; post base 6.6248 = ground - 0.30).
   - rev's cause, as round Q recorded it (build rq1): reversed, the lap comes west on E 56th and turns left onto Dahlia;
     straight on runs across the pad's deck into E 56th west (grid_primary_35, a through street the sign field does not
     hold), and the failed-turn rule stands the plate off that street.
   - `corners.SC-D56.rev = {"skip": true, "reason": ...}`, the per-approach sub-object place_signs.effective_override
     merges; no tool change. As SC-48S rev: no race layout drives rev, and in Free Roam a left arrow there would point
     away from a road a driver may take.
   - Posts: 0.2.8 had 6 (its M-c5-fwd is this corner's fwd plate under its old id), 0.2.9 had 5, 0.2.10 has 6, on 0.2.8's
     corners.
   - **Owed:** SC-D56 rev, until the sign field holds grid_primary_35 or the polyline check reads the pad's outline.
4. **The race kink rise located** (9663b80f): the 7 new kinks sit inside item 1's flare.
5. **Both heads on lamp_heads** (9663b80f): both_heads_by gone; one path, Lake Murray's.
6. **The 7 streets onto the lidar:**
   - grid_secondary_8, grid_secondary_42 and grid_primary_71 joined at their true lon / lat (eac45b45);
   - grid_primary_15, 11, 39 and 77 held;
   - E 56th fully on the lidar (1725f2a1, the Mac).
7. **The Northfield Quebec arms at their true lon / lat** (b798d89c, the G10): the file is committed but NOT wired (the
   Mac's call, 2026-11-23). The arms are drawn in the grid frame, 4.6 m west of the true street. Round I's heights, item
   2's patches and its lift caps all read the lidar at those drawn points: one frame. The true-street heights are
   +0.095..+0.315 m (median +0.186) over round I's, so wiring them would stand the drawn roads 0.19 m over the ground
   read beside and under them, and every edge hang on the arms would grow by that much. The file waits for the round
   that moves the whole grid to the true frame, where the patches get re-read too.

### Item 2: where the edge hangs, and why

**The step** (a scratch draft at b798d89c, the chain's own commands through gap_mouths, read after each step at 15
points):
- seat_terrain leaves arm 78's north-west half under the road; no step before or after changes it.
  - Ground minus road at s 0 (3 m past the pad row), 4.5 m left of the centre: −1.03 m before seat, −0.61 after.
  - On the walk, 6 m left: −1.04 -> −0.70. Seated is −0.16.
  - The same offset at s 3 seats: −0.82 -> −0.19.
- Arm 84 seats with round 2's heights: its NW half reads −0.10..−0.19 m from seat on (0.2.9's cluster, up to 0.77 m, is
  gone).

**The cause** (a copy rebuilt to the weld, seat_terrain alone, its triangles read before and after):
- After the weld, the ground at 78's NW half is the assembler's 10 m grid.
- Seat halves it once, to 5 m. The triangle under (1806.07, −459.76) then has two corners pinned (under the road
  24.767, under the walk 24.894) and a third at (1802.87, −456.59), 2.4 m past the walk, left at 23.547.
- Past the pinned strip, seat only pulls the ground down; it lifts a dip only when it is over 2.5 m × (1 − t). So the
  triangle stays tilted down under the walk's edge. The later steps cut it finer (0.45-0.65 m edges at the end of the
  draft) and keep the tilt.
- Beside the arms, the built grass is the port's 40 m 3DEP grid. It is 0.4-1.1 m under the lidar ground there. The lidar
  ground is within −0.12..+0.07 m of the road top at every place the edge hangs (the Mac: within ±0.41 m 6-12 m out).

**Where the draft's edge hangs over 0.30 m before the fix** (road top minus the lowest ground outside the road in a 1.25 m
square around each edge cell; 0.25 m rasters of the draft's loop.blend; the draft is before prep, so this is not the gate's number):

| m | cells | at | what |
|---|---|---|---|
| 0.90 | 22 | (1804.62, −458.38) | 78's NW walk at s 0; under the road there, the ground sags up to 0.78 m over 209 cells |
| 0.77 | 53 | (1805.62, −471.38) | the median's nose at the pad (0.2.9's 0.935 / 1.07 m spot) |
| 0.58 | 39 | (1797.88, −458.88) | the pad's NW corner, between Sand Creek Dr N and 78 |
| 0.42 | 4 | (1803.88, −461.88) | the 78 row's NW corner |
| 0.36 | 20 | (1812.62, −496.38) | the pad's SE edge |
| 0.34 | 43 | (1792.62, −519.38) | the pad's S end |
| 0.32 | 5 | (1834.12, −446.88) | the median's 84 side, 26 m up |

### Item 2: the fix (all opt-in, Sand Creek only)

**Three ground patches** (terrain.lidar_patches, after wall_49):
- quebec_nw78: the wedge between Sand Creek Dr N and grid_primary_78, from the pad up to z −447. 41 points, 135 m²;
  feather 2 m on that cut only.
- quebec_median: the whole median between grid_primary_78 and grid_primary_84, from the nose to the merge. 176 points,
  246 m²; every edge hard.
- quebec_se84: the strip along the pad's SE edge, s −32..−12 along grid_primary_84. 12 points, 101 m²; feather 3 m
  outward.
- Each is traced off the plan rasters (a 0.2.9 gate OBJ over 1785..1895 × −505..−345, the round 2 draft's loop.blend over
  1765..1850 × −530..−430). Each keeps at least 0.53 m off every road and walk cell, with no road cell inside, and is
  hard on its road sides.
- Measured by tools/lidar_ground_patch.measure itself, on an Ept stand-in that reads only the cached CO_DRCOG_2_2020
  tiles 17_-5, 17_-6, 18_-4, 18_-5, 18_-6 and refuses a missing one: nothing fetched.
- Nodes filled for having no returns: 2 / 3 / 0.
- wall_49's measured record is byte-identical (sha256 be105a14…, pinned in the test).
- **The median patch is the ground only.** Quebec's raised median (a later round 2 item) builds its curb and top on it
  by its own step.

**Two lift zones**, last in the list (quebec_lift_pad, quebec_lift_arms), for tools/ground_patch_blend.py's new opt-in
`lift`:
- The rule: a TERRAIN vertex under a road-class surface (ROAD, CURB, 1ROAD; the lowest sheet) rises to min(the lidar,
  that sheet − 0.16 m). A vertex off the road within 1.25 m of one rises to min(the lidar, the road's height at its
  nearest point − 0.16 m): the lip.
- It never lowers anything, never lifts above the lidar or past the lip, cuts nothing, and moves nothing past 1.25 m.
- The zones run s −45..80 along grid_primary_78. They keep off the two bridge decks the 2020 lidar reads as class 17:
  - Quebec St over Sand Creek, at the pad's S end;
  - I-70, NE of the arms' merge.
- Nodes filled: 70 (the largest hole is 26 nodes on Sand Creek Dr N's walk) and 3.

**feather_spares_roads** (opt-in, the two feathered patches): no patch's feather moves a vertex under a road or walk. The
first test showed why: quebec_se84's end edges lowered the ground under the pad by up to 0.046 m, and quebec_nw78's cut
lowered it under 78's walk by up to 0.123 m.

**No gate and no threshold changed:** GATES-CHANGELOG is untouched. lm_pads' edge band is unchanged; the lift runs in
ground_patch, after every cutting step.

### Item 2: measured on the round 2 draft (ground_patch_blend on a copy, before / after, 0.25 m rasters over 1765..1880 × −530..−380)

- **Under the road, sag over 0.30 m:** 360 cells (max 0.775) -> 0 (max 0.296).
- **Edge hang over 0.30 m:** 238 cells (max 0.898) -> 80 (max 0.372), in 4 clusters:
  - 0.372 m, 3 cells, at the 78 row's NW corner (1803.88, −461.88): the pad's own edge drops 0.2-0.3 m within 0.7 m (24.86
    -> 24.57-24.65) while the lidar there is level at 24.75-24.76. The ground was lifted only to the lip of that lower edge
    (24.48-24.50). **Owed with the pad's deck shape.**
  - 0.339 m at the pad's S end: the deck held to the lap's S row (below). **Owed.**
  - 0.368 m in the creek channel W of the pad: the lidar there is 5.5 m down. Real.
  - 0.355 m NE of the merge, in the I-70 shadow: no class 2 there, outside the zones, unchanged.
- **The seated ground against the lidar** (|after − lidar|, p50 / p95 / max; before in brackets):
  - quebec_nw78: 0.007 / 0.043 / 0.288 (0.414 / 0.757 / 0.932);
  - quebec_median: 0.013 / 0.118 / 0.296 (0.217 / 0.381 / 0.498);
  - quebec_se84: 0.004 / 0.023 / 0.069 (0.138 / 0.291 / 0.328).
- **The lifts:**
  - quebec_lift_pad: 1,242 vertices under a road and 436 beside one, 81 of them capped by the lidar, largest 0.74 m.
  - quebec_lift_arms: 1,490 and 61, 28 capped, largest 0.23 m.
- **Elsewhere under the road** (outside the feather fault above): the re-cut triangles moved the ground by at most 4 mm.

### Measured and owed (not round 2)

- **The lap's height on the Quebec St bridge over Sand Creek** (the Mac's wording): the intake levels the deck flat; the
  2020 lidar's class-17 returns give the real deck's slope.
  - The pad's S row (24.115, flat) stands 0.26-0.47 m over the class-17 deck (23.65-23.86): +0.26..+0.32 at the E end,
    +0.45 at the centre, +0.47 at the W end. The creek bed is 5.5 m below the W end (18.59).
  - The lap at v1950 reads +0.38 over the class-2 ground.
  - The ground on both sides of the pad's S edge is level (23.81-23.98) and the built grass already matches it
    (−0.03..+0.06), so no patch is drawn there.
  - Its own round after round 2: the lap's profile is what every pad and mouth near it follows.
- **The pad's deck shape at the 78 row's NW corner:** the 0.372 m above.
- **The true frame:** the whole grid (route_connectors' sphere frame) onto the true one; then item 7's file gets wired
  and the Quebec patches get re-read.

## What needs Kevin, a download or the PC

- **Kevin:**
  - The two readings (section 4): keep `drive_test.vertex_kinks` and `fold_fans.wall_frame`, or drop them? With the
    walls read against the line's deck, verify_fold_fans fails the S; vertex_kinks changes only a reported number.
  - Building E 56th Ave (2.5 km, 13 mouths) as the map-edge fix. It is a street the 13 meet, not one of "the 7"; drop
    `lm_intake.grid_reach` to take it out.
  - Road wear on Sand Creek, if the owned asphalt should get its high-pass (`road_wear.detail_highpass_m` is a road_wear
    key).
  - His drive of 0.2.9 (Runbook 0098-1's last step).
- **A download (none made):** the lidar under E 56th's 466 3DEP points: the 14 EPT tiles of row z 1300-1400 listed in
  `source/grid_reach.json` `tiles_missing` (USGS CO_DRCOG_2_2020 EPT,
  `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json`, 100 m tiles + 5 m; sizes not known
  without fetching). The G10's lidar round can take them with the 7 streets.
- **The PC:**
  - Runbook 0098-1 (the rehearsal).
  - Round 2: the 0.2.10 rehearsal (the section above), then the install on Kevin's standing word if it is green.
  - The pads session: sandcreek_quebec / dahlia_56th, the two one-sided flares inside their boxes (v769-787, v1924-1950),
    the N Ivy mutual T.
  - On an install: `fleet/ac-installed.json`'s Sand Creek row, 0.2.9.
- **The G10:** the 7 streets onto the lidar, read at each point's own lon / lat (section "Scope"); the 99 profiles'
  frame (median 0.026 m, max 1.35 m), if the coordinator wants them re-read.
- **Nothing for `assets/licenses.json`:** the four owned files are listed there already (CC0).

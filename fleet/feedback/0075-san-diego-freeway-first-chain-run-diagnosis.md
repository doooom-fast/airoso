---
id: 0075
title: San Diego freeway, first chain run red - five mechanisms, diagnosed, not fixed
status: in-progress — four opt-in engine switches (walls.seat seated, join_nodes, stable_snap, cap_dead_ends) + two config changes (terrain east, capture.bridges), proven on the Mac's network draft: drive_test and audit both exit 0 (third addendum); a PC build and Kevin's drive close it
scope: tracks/san-diego-freeway (scripts/geometry/build_network_mesh.py, scripts/elevation/network_elev.py, scripts/geometry/drive_test.py)
layer: engine (network draft) + one gate note
train: -
---

## Symptom

The freeway's first run through the chain (`tools/ship_track.sh san-diego-freeway --no-install`, Windows box, 2026-11-03, workshop
`D:/k10-workshops/san-diego-freeway`) went red and was not installed.

- `drive_test` on the declared I 8 eastbound line, 10,669.7 m: severe 90, soft top 151, floating furniture 22,475,
  daylight 602, excursion drops 53, kinks 36.18 /km, steps 10.4 /km, fold bumps 6, obstruction 0.
- `audit_mesh`: A 0, B 0, C 9 (6 ramp, 3 mainline), D 1,724, E 46 (worst +16.97 m), H 0, I 0, J 23 (worst 800 m edge), K 0.
- `kn5_ground_check` PASS; the Drive-1 road gates exit 0.
- 549 more edges are built and unjudged (`data/network.reference.json`).

What follows is a bounded pass, about an hour: mechanisms with their evidence, in order of how much each explains. Nothing is fixed here.

## 1. The barrier stands 3.2 m outside the pavement at deck height (floating 22,475; most of D and the 9.99 m drops)

`build_network_mesh._wall` sweeps the freeway barrier at `half + scenery.walls.offset_m`, default 3.2 m. Its base is the
deck's own height less 0.35 m, and nothing reads the ground where it stands. The graded shoulder beside a freeway is
`ribbon.road_shoulder(verge_w=3.0)`, so the barrier lands 0.2 m past the end of the only surface built to deck height.
Wherever the road rides above its surroundings (embankment, flyover, viaduct), the barrier hangs over the falling ground.

Measured on the built gate OBJ (`data/track.obj`), with drive_test's own seating test re-run outside it (0.6 m columns,
0.8 m support, 2.4 m grounded-neighbour excuse):
- 23,460 floating columns have ground under them, at real gaps (median 3.53 m, p90 11.28 m, worst 35 m). Only 214 have
  nothing under them, so it is not a gate artefact: with drive_test's 60 m giant-triangle skip lifted, the count barely moves (23,671).
- Every floating column stands 3.20 m in plan from the nearest road-edge vertex (median and p90 both 3.20), all of
  them `1WALL_part_*`, the network's barrier.

The two 9.99 m excursions at 3,152 and 3,304 m are inside the viaduct span 3,002-3,379 m. The deck edge has no guard
there: its barrier stands 3.2 m out in the air. drive_test exempts declared bridge spans only when there is no reference
line (`spans = [...] if line is None else []`), so the viaduct's sides read as gated drops.

**Proposed fix (engine, `build_network_mesh._wall`):**
- On a deck (flyover or viaduct), place the barrier on the deck edge (offset about 0.3 m inside it).
- At grade, keep it within the graded shoulder (offset no more than `verge_w`) and seat its base on the ground
  under it (drape), not on the deck height.
- A config-only experiment is available first: `scenery.walls.offset_m` is already read (default 3.2). Setting it to
  about 0.5 m would move every barrier onto the shoulder or deck edge without code, and would show how much of the
  22,475 is this mechanism.

## 2. Edge joints carry height steps (the severe steps)

The reference line's severe steps sit on its edge joints. Oriented joint heights of `network.edges.local.json`
(surface, with at-grade in brackets) against drive_test's severe stations:

| joint | station | surface dy | at-grade dy | severe at |
|---|---|---|---|---|
| 148 -> 150 | 1,373 m | -3.33 | -0.40 | 1,379 |
| 204 -> 102 | 3,190 m | -2.40 | -2.40 | 3,197-3,198 (2.406 m) |
| 102 -> 101 | 3,373 m (6.5 m gap) | -4.09 | +6.18 | 3,380-3,387 (2.84 m) |
| 592 -> 498 | 3,914 m (6.7 m gap) | -0.63 | -0.63 | 3,927-3,935 |
| 331 -> 330 | 7,036 m | -3.87 | -0.20 | (span end 7,055) |
| 221 -> 148 | 33 m (6.1 m gap) | +0.53 | +0.53 | 33-40 |

Two mechanisms:
- **(a)** `scripts/elevation/network_elev.py` smooths and caps each edge on its own (`_smooth_edge`,
  `_despike_smooth_cap`), so a node two edges share gets two heights. That's the 3,190 m joint: -2.40 m at grade with
  no plan gap, read as 2.406 m by drive_test.
- **(b)** The viaduct / flyover lift (the reference line's `spans`: 1,204-1,379, 3,002-3,379, 3,616-3,756,
  6,602-6,747, 6,905-7,056, 7,151-7,271 m) is laid per edge and ends at an edge boundary. The next edge starts at
  grade, so surface dy is -3.3 to -4.1 m where at-grade dy is small (1,373 and 7,036 m).
- Three joints the reference line bridges across 6.1-6.7 m (`join_tol_m` 7) aren't shared nodes at all. Their steps are
  two separate pavements meeting.

**Proposed fix (engine):** after per-edge smoothing, pin every shared OSM node to one height, the mean of its edges,
and blend each edge back over a ramp length. Ramp the deck lift across the joint into the next edge instead of ending
it at the edge boundary. The ledger's earlier stand-in note (0.13-0.60 m at the mainline joints) is mechanism (a) at
small scale.

## 3. The barrier gap test knows only freeway decks (D 1,724)

`_wall`'s crossing gap reads `fw_road_hash`, which holds freeway decks only (`is_fw`). A surface street's ribbon
(`curb_sidewalk` edges) is never in it, so a freeway barrier that meets a surface street at grade is never gapped and
stands on its pavement. D was 624 on the draft OBJ and 1,724 on the built gate OBJ. The built count also carries
mechanism 1 at merges, where a barrier 3.2 m out lands on the neighbouring ramp. Why the prep multiplies the count is
not established here.

**Proposed fix (engine):** gap against every drivable ribbon (`deck_all` plus the surface edges), and keep the
height window. Mechanism 1's offset fix removes the merge share.

## 4. The 9 at-grade crossings are merges, and C does not gate

`audit_mesh` reports C but does not gate on it (`return 1 if hard else 0`, C non-gating since walls are gapped there).
At all five sites the edges within 0-7 m are one road family at nearly one height:
- CA 163 mainline 7 / 566 / 564 at 130.4-130.5 m;
- I 5 ramps 231 / 239 / 240 at 10.1-10.8 m;
- unnamed ramps 234 / 235 / 237, 249 / 250, 609 / 610.

These are diverges and merges at shared nodes, not separate roads crossing. At three sites one of the edges carries
OSM `layer_profile` 1 (239, 240, 566) while sitting at grade at the shared node: the layer lift starts from the node,
which is mechanism 2's join.

**Proposed fix (engine, `audit_mesh` C):** classify a crossing at a shared OSM node as a merge. No geometry change is owed.

## 5. J: the terrain skirt spans the road (J 23, worst 800 m)

`build_network_mesh._skirt` lays an 800 m apron outward from the heightfield grid's perimeter. The gate OBJ holds
4,688 drivable-group triangles over 60 m, all `1GRASS_skirt`, the longest 828 m. J's worst edge (800 m) is a skirt
triangle. Where a freeway edge runs past the terrain grid's boundary (the network's roads aren't cropped to the grid),
the apron's triangles lie over its pavement.

**Proposed fix (engine):** size the heightfield grid to the edges' extent plus a margin, or clip the skirt where a road
leaves the grid.

## Order of work, when there is a go

1. The `scenery.walls.offset_m` experiment, config only, re-gated. It shows the size of mechanism 1 before any code.
2. `_wall` on the deck edge and seated at grade (1, with 3's merge share).
3. `network_elev`: shared nodes pinned, deck lift ramped across joints (2).
4. The skirt (5); C's merge classification (4).

## Addendum 2026-11-03: four barrier experiments (mechanism 1), then handed to a Mac agent

Re-gated on the Windows box from `network_mesh`, each against the same draft. The branch `claude/freeway-fixes` carries
experiment 1 only; the patch scripts of 2-4 are in `tracks/san-diego-freeway/source/experiments/` (not applied).

| | baseline (offset 3.2) | 1: offset 0.5 | 2: drape, deck barrier 0.35 m inside the edge | 3: drape, 0.05 m outside | 4: + 0.6 m 1KERB parapet base |
|---|---|---|---|---|---|
| floating furniture | 22,475 | 13,234 | 4,466 | 13,421 | not reached |
| audit D walls on a road | 1,724 | 1,311 | 90,101 | 1,276 | 453 (draft OBJ) |
| obstructed stations | 0 | 3 | 334 | 4 | - |
| audit E walls floating | 46 | 7 | 3 | 4 | 6 (draft OBJ) |
| excursion drops | 53 | 22 | 19 | 20 | - |
| verify_kn5 | pass | pass | pass | pass | FAIL: 39 terrain pokes (worst 0.85 m); draft audit K 463 kerbs in the carriageway (worst +1.19 m), F 51 |

- **Experiment 1** puts the at-grade barrier on the 3 m graded shoulder and takes 41 % of the floating columns. It is
  config only (`scenery.walls.offset_m` 0.5).
- **About 9,000 of the rest are barriers on elevated stretches.** Inside the pavement edge they stand on the road (D,
  obstruction); just outside it they hang over the valley (the shoulder drops away in centimetres). A real viaduct
  carries its parapet on a slab beyond the travelled way: experiment 4.
- **Experiment 4 failed for two reasons, both mine:**
  - "on a deck" was read as the centreline more than 1.5 m over the raw 3DEP ground under it, which takes embankments and
    low fills too, where the sloping terrain rises through the strip;
  - at merges and diverges on decks one edge's strip lies over the neighbouring ramp's pavement.

**Plan for the agent:**
1. Classify decks from `data/network.viaduct.json`: per edge, per vertex, the deck's lift over at-grade, 0 at grade and
   9 m or more on the flyovers. Embankments then take the at-grade drape.
2. Clip the parapet strip, and gap the barrier, wherever another edge's pavement lies under the strip's footprint
   (merges and gores), as at crossings.
3. Re-gate. Severe 90, soft top 151 and daylight 602 never moved in any experiment: they are mechanism 2 (the joints,
   `network_elev`), next after the barrier.

## Second addendum 2026-11-03: five fixes on the Mac, draft re-gated (branch `claude/freeway-network-fixes`)

**How it was proven.** The chain's draft steps ran on the Mac from the repo root (net, classify, network_elev, network_mesh,
network_reference), then `drive_test --layout freeroam` and `audit_mesh` on that draft's `data/track.obj`. No kn5, nothing
installed. Live Overpass and 3DEP reproduced the PC's committed `network.geojson`, `network.elevation.json` and
`heightfield.npy` byte for byte, so the PC's data is the baseline. Re-meshed here with exp1's config, it reads exp1's
drive_test numbers within noise:
- floating 13,223 (PC 13,234); soft top 151; severe 90; daylight 602; excursions 22; obstruction 3;
- kinks 35.9 /km (PC 36.18).

The audit's C 9 and E 7 match. Its D (469, PC 1,311) and J (14, PC 23) count vertices, and the PC's gate OBJ comes from
the kn5, which carries per-corner vertices. That explains section 3's open question, why the prep multiplies D.

Every fix is opt-in by config, and without its key the build is byte for byte as before. Checked: the default-seat
`track.obj` md5, default `net` + `classify` md5 against the committed graph, and `_smooth_edge` on all 612 edges. Only
the freeway sets the keys. Per-fix numbers, every row re-gated with the final `scripts/`, are in
`tracks/san-diego-freeway/data/mac_draft_gates.log`:

| | floating | soft top | severe (/km) | daylight | excursions | obstructed | D | E | J | K (not gating) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0: exp1 (PC data, Mac draft) | 13,223 | 151 | 90 (8.44) | 602 | 22 | 3 | 469 | 7 | 14 | 0 |
| 1: + `scenery.walls.seat` "seated" | 5 | 107 | 92 (8.62) | 0 | 11 | 9 | 0 | 0 | 14 | 34 |
| 2: + terrain bbox east -117.115 | 1 | 107 | 92 (8.62) | 0 | 11 | 9 | 0 | 0 | 0 | 34 |
| 3: + `network.join_nodes` | 1 | 98 | 46 (4.31) | 0 | 13 | 4 | 0 | 0 | 0 | 6 |
| 4: + `network.stable_snap` (final) | **0** | **5** | 37 (3.47) | **0** | 9 (limit 10) | **0** | 0 | 0 | 0 | 2 |

Final audit: A 0, B 0, C 8 (not gating), D 0, E 0, F 0, H 0, I 0, J 0, K 2 (not gating). The audit exits 0. drive_test
exits 1 on soft top 5 and nothing else.

**1. The barrier seated (`build_network_mesh._wall_seated`, `_deck_edge`; mechanisms 1 and 3 and the PC's plan steps 1-2).**
- **Decks.** A deck is the network's own viaduct lift (≥ 1 m, the mesh's own lifted-deck threshold), or a span the mesh
  already builds slab + piers under (deck > 2.8 m over the carved ground, its bridge-run rule).
  - Not centreline height over raw 3DEP: that is what failed exp4.
  - On a deck the barrier stands 0.7 m past the pavement edge on a 1 m `1KERB_deckedge` slab at pavement height.
  - A slab vertex closer than 0.3 m over the built ground is not a deck there, so terrain can never poke it.
  - The slab runs one segment past a deck run and 0.5 m past an edge's end node. A barrier column on the slab's very
    edge read floating by OBJ millimetre rounding.
- **At grade.** The barrier stands `offset_m` out, with its base 0.5 m under the built ground at the barrier: the final
  carved grid, triangle-exact.
- **Over other pavement.** Wherever another edge's pavement lies under the barrier or the slab, the barrier is gapped and
  the slab clipped, per side.
  - The test is triangle-exact against every built ribbon, the same footprint test as audit D.
  - A slab flush with or under a neighbour's lanes stays: a lane gain or a merging ramp at a joint. Clipping it opened 7
    daylight gaps at 3,379 m.
- **Width.** The barrier follows the ribbon's own per-vertex width, a ramp's merge taper included.
- **Crossing gap.** The old centreline gap is kept, but at 1 m past a neighbour's edge instead of 3.5 m. At 3.5 m it left
  the median and gore sides open over 0.13-0.24 m shoulder ledges (on the final draft, excursions 14 → 9). At 0 m,
  ramps' barriers stood in the line's corridor at gores (obstructed 6).
- **Shoulder.** A grass-shoulder triangle lying over a neighbour's lanes (2 cm over them at 6,465 m) is dropped.
- **A trap found on the way.** `for pr, p, _w in edge_local` rebound `_w`, the heightfield's west bound `terr_y` reads, so
  `terr_y` returned garbage after that line. Renamed. Nothing in the default flow calls `terr_y` after it.

**2. Terrain grid east to -117.115 (config; mechanism 5).** The edges run to -117.1224, 250 m past the old grid. The
800 m skirt lay over their pavement, and their barriers stood over the skirt. J 14 → 0. The last floating columns were
there.

**3. One height per shared node (`network.join_nodes`; `scripts/geometry/network_joins.py`; mechanism 2a/2b).**
- **The cause at grade** is bigger than the diagnosis said. `network_elev._smooth_edge` grade-caps FORWARD only, so an
  edge's END drifts from 3DEP: 334 of 365 shared nodes disagreed by more than 6 cm, 169 by more than 0.5 m, the worst by
  19.86 m.
- **The rule.** Each node takes the mean of its THROUGH pair: the two ends that continue each other straightest,
  mainline before ramp. A ramp branching off takes the mainline's value.
- **At grade** (network_elev) each edge is capped at 5 % with both ends pinned to their nodes. Where the pins are further
  apart than the cap allows, the edge takes one straight grade.
- **The deck lift** (build_network_mesh) is joined the same way and ramped back over max(40 m, |d| / 4 %). The deck's
  6.5 % cap then runs with both ends held.

**4. One coordinate, one node (`network.stable_snap`; `scripts/gps/network.py`, `scripts/gps/classify.py`; mechanism 2c).**
The three 6.1-6.7 m holes were not dropped stubs: a stub collapse was written, run, found nothing and was removed. The
greedy snap is the cause:
- `_NodeGrid.assign` moves a cluster's centre by running mean, so a vertex two OSM ways share, met again in a later way,
  can land in a different cluster. The ways then end at two nodes a few metres apart, with no link.
- 101 such end pairs in this network; none with the key.
- With the key every point is mapped to its nearest FINAL centre and placed at the node's seed point.
- It also snaps only within one OSM layer; an exactly shared coordinate still joins across layers. The layer-blind snap
  had merged a layer-3 flyover's vertices into the layer-2 I 8 node it passes over, a junction that does not exist. That
  is the PC draft's 2.406 m step at 3,190 m. Joined, it pulled the flyovers 4 m down into the mainline's corridor
  (severe 5 m, 24 obstructed stations, until the layer rule).
- classify's travel vote then reads an edge's interior samples, or a short edge's middle vertex. A node's point can be a
  ramp's vertex at a gore, and an 18.7 m I 8 piece came out undecided, so network_reference refused the line.
- The graph is now 563 edges. The line's 19 joints all have a 0.0 m gap, soft top 98 → 5, and its ids changed (live
  data; `edge_ids` stays null).

**What is still red, and why.**
- **drive_test soft top 5, and with it the 0.8 m severe at s 2.** These are the reference line's FIRST station, s 0,
  which lies exactly on the ribbon's end row, where I 8 eastbound is cut by `source.bbox` (a dead end). Five wheel-path
  points fall a hair past that row, and the grass 0.84 m below reads "on top".
  - drive_test's own off-pavement guard at a line's ends exists for exactly this, but it asks only the station's
    centre point, which lands on the ribbon.
  - The grid spawns 45 m in, so no car meets it.
  - Not forced. This is a gate-precision question, or an engine dead-end cap, for Kevin.
- **Excursions 9 (passes, limit 10).**
  - Two are real viaduct drops at 3,155 and 3,305 m, inside the 3,002-3,379 m span: nothing within 8 m below the slab,
    behind its barrier. drive_test's "no surface" branch gates without asking for a guard, and it exempts only spans
    declared in `capture.bridges`; this config declares none.
  - The rest are 0.13-0.24 m shoulder and median-fill ledges, plus a 1.14 m one at 10,054 m where a median strip ends.
- **Not gating:** severe 3.47 /km (limit 12), C 8 (merges at shared nodes, the PC's step 4, not touched), K 2.
- **Unjudged:** 543 more edges are built and unjudged (no line gate walks them).

**For Kevin.**
- **(a)** The line-start soft top. Options:
  - i. drive_test's end guard asks per wheel path (a gate change, GATES-CHANGELOG);
  - ii. the engine caps network dead ends (a barrier across, an authoring item);
  - iii. accept it red until the line is authored.
- **(b)** Should the network's own spans (`data/bridge.spans.auto.json`, written by network_reference) feed drive_test's
  bridge exemption, as `capture.bridges` does for a loop? That is gate wiring, so his call.

**What a PC build still has to show.**
- The same chain through prep/export/kn5, with the gates on the BUILT gate OBJ. Expect D and J to scale by the kn5's
  per-corner vertices.
- verify_kn5: the new `1KERB_deckedge` slab is face-up and must not trip the terrain-poke check that exp4 failed.
- kn5_ground_check.
- The underlay into `loop.blend`.
- Kevin's drive of I 8, and of the unjudged network.

## Third addendum 2026-11-03: dead-end caps and the declared decks (the coordinator's two decisions); drive_test green

The coordinator decided the second addendum's two questions, and neither touches a gate:
- **(a)** cap the network's dead ends, under Kevin's JUNCTIONS 18(d): "a road we are not completing gets a barrier, not a
  curve";
- **(b)** declare the real viaduct spans in `capture.bridges`, project config, as every other track does.

**(a) `network.cap_dead_ends`** (`build_network_mesh._cap_wall`; `network_reference._trim_capped`):
- **What gets capped.** Every freeway edge end no other edge shares ends in a closed stub: a barrier across the
  carriageway 2 m inside the ribbon's end, joining both side barriers, with the pavement running on behind it. The
  bbox cut I 8 off at both ends, and the same holds at every other bbox edge and at every ramp that led to a surface
  street.
- **How the gates read it.**
  - The barriers are `1WALL_STUB_cap_*`, declared in `data/stubs.built.json` the way Lake Murray's phase-5 stub
    barriers are, so audit D reads them as stub barriers: 6,180 vertices on 156 footprints, D 0.
  - They are recorded in `data/network.caps.json`. From it `network_reference` starts and ends the line 10 m inside a
    cap, past drive_test's 6.3 m corridor disc: I 8 starts 12.2 m and ends 13.0 m inside its caps.
  - The gate's end guard is unchanged.
- **Counts.** 156 caps. 39 were moved in off a deck to the edge's last at-grade vertex (a road cut mid-viaduct).
- **22 ends are left open**, listed in `network.caps.json` "uncapped" with the reason: their edge has no at-grade vertex
  at all (deck or a high span end to end). That includes the I 5 mainline cut by the bbox on a 5 m deck (edge 263,
  18 m wide). A cap ON a deck is more than the stub rule gives.
  - Tried once: audit E then read 3 mid-carriageway columns of the 18 m I 5 cap as floating. E measures against the
    nearest road VERTEX within 4.5 m, and a ribbon has vertices only at its edges.
  - Reverted. Those 22 are an authoring item.

**(b) `capture.bridges`** (track.config.json): network_reference's six I 8 spans, each checked against the line's own
deck lift (1.00-11.19 m along every span) and the OSM bridge layers under it (1, or 2-3 on the 3,002-3,463 m stack):

| id | centre m | length m | lift m | OSM layers |
|---|---|---|---|---|
| i8eb_deck_1190 | 1,282.8 | 185.2 | 1.10-4.07 | 1 |
| i8eb_deck_2982 | 3,222.7 | 480.4 | 1.36-11.19 | 2, 3 |
| i8eb_deck_3598 | 3,665.6 | 135.2 | 1.00-1.69 | 1 |
| i8eb_deck_6581 | 6,654.0 | 145.2 | 1.05-2.28 | 1 |
| i8eb_deck_6884 | 6,969.5 | 170.3 | 1.03-3.87 | 1 |
| i8eb_deck_7130 | 7,189.9 | 120.1 | 1.33-1.52 | 1 |

The stations are this draft's. A net step on changed live OSM moves them: re-read `bridge.spans.auto.json` after one
and re-declare (the config's `capture._doc` says so).

**Re-gated on the Mac** (final row of `data/mac_draft_gates.log`):

| | floating | soft top | severe (/km) | daylight | excursions | obstructed | D | E | J |
|---|---|---|---|---|---|---|---|---|---|
| 4: stable_snap (second addendum's final) | 0 | 5 | 37 (3.47) | 0 | 9 | 0 | 0 | 0 | 0 |
| 5: + caps + capture.bridges | **0** | **0** | 16 (1.50) | **0** | **6** | **0** | 0 | 0 | 0 |

- **drive_test exits 0.** The caps alone already passed (soft top 0, excursions 9); the declared decks took excursions
  9 → 6.
- **audit exits 0:** A-K 0 but C 8 and K 2, which do not gate.
- **The 6 excursions left are all off any bridge:** 0.12-0.29 m shoulder and median-fill ledges at 1,651, 5,704 (two),
  5,854 and 7,650 m, and a 0.79 m one at 3,905 m (offset -12.5, past the far edge of a median strip).
- **Defaults stay byte-identical** without the key (no `network.caps.json`): checked by md5 on `track.obj`,
  `finished_centerline.json`, `dummies.json` and `network.reference.json`.

**What a PC build still has to show**, unchanged:
- the chain through prep, export and kn5, gated on the BUILT gate OBJ (D and J scale with per-corner vertices; the
  stub exemption keys on `1WALL_STUB_*` names, which the underlay keeps as object names);
- verify_kn5 on the face-up `1KERB_deckedge`, then kn5_ground_check and the underlay;
- Kevin's drive.

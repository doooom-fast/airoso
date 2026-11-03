---
id: 0075
title: San Diego freeway, first chain run red - five mechanisms, diagnosed, not fixed
status: diagnosed
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

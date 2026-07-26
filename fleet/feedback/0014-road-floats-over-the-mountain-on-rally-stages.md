---
id: 0014
title: The road floats over the mountain — the contact pin charges slope, and 8 m cells cannot pay
status: diagnosed
scope: k10-colorado-rally/dragon-tail-gravel, k10-colorado-rally/under-the-dragon-gravel, k10-colorado/lookout-lariat
layer: engine
train: 02
---

## Symptom

Dragon Tail gravel passes `drive_test` (0 ground-on-top), passes `audit_mesh` (CLEAN) and passes
`verify_kn5`, then fails `kn5_ground_check`:

```
deck-vs-mountain (tri-exact): median +0.400  p95 +1.114  max +3.216
road-over-ground: 7064/7213 samples gap > 0.05 m (97.9%)   gate ROAD_GAP_P95_M = 0.10
```

98% of a 25 km stage has air under it — typically 40 cm, worst case 3.2 m. The car sits on the
road (which is why the drive test is happy); the *road* sits on nothing. Off the edge is a drop,
not a transition, which on a gravel stage is the entire driving surface.

## Method

Three independent harnesses rebuilt the measurement from the shipped artifacts — `data/track.obj`
(1,915,827 verts; `1ROAD_main` 16,864 tris) triangulated against `data/ground.local.json`
(nx=2166 ny=676 dx=+8.0342 dz=−8.0023) using `_grid_trisurf`'s diagonal split
(`build_mesh.py:185-201`). All three reproduce the gate to three decimals
(+0.400 / +1.111 / 97.9%), and a from-scratch re-run of the contact pin reproduces the built grid
to **p95 |node error| = 0.0006 m**. Every number below is therefore a measurement of the real
operator, not a model of it.

## What it is NOT (all refuted with numbers — do not re-investigate)

- **The deck is not lifted after grading.** All 16,866 `1ROAD_main` verts against the 8,433 points
  of `finished_centerline.json`: min −0.005, median +0.000, max +0.005 m. That ±5 mm is the ribbon
  crown. `ROAD_LIFT_M = 0.0001` (`build_mesh.py:31`) is 0.1 mm. Fold pads (+0.028 m) never fired —
  no vert deviates that far. `flat_zones.json` is `[]`, so all seven `_flatten_pavement` calls are
  no-ops. **This kills the standing suspicion in [0012](0012-ring-mesh-pokes-through-the-road.md)**
  that "a later pass moves the deck".
- **`clamp_terrain_below_road` is not the cause.** Its reach *is* inflated to 18.1 m
  (`ribbon.py:459-462`, `max(reach, grid_spacing*2.2 + 0.5)`) and it *does* take a minimum rather
  than a nearest-clearance — but of 41,955 nodes in reach only 7,508 are clamp-bound, and it is
  not what sets the nodes under the pavement.
- **Not the wrong grass mesh, and not the corridor splice.** The surface under the deck is the
  graded grid, and the splice runs before grading.
- **Not a gate artefact.** The terrain grid covers 17.3 × 5.4 km against a road extent of
  17.1 × 5.1 km, so the stage is inside the heightfield end to end. Worth ~0.03 m at most.

## The mechanism

Grass nodes under pavement are pinned to a **window MINIMUM** of the deck/shoulder over a stencil
of radius `_hs7 = meta["spacing_m"] * 0.55` (`build_mesh.py:1445`) — **4.42 m axis-aligned, 6.25 m
diagonal** at 8.03 m cells — via `_deck_window_min7` (`:1447-1464`) and `_shoulder_window_min8`
(`:1507-1531`).

That buys poke-through immunity by paying **(stencil radius × local slope)** of air at *every*
node under the road. This stage's local |grade| is median 3.1%, p95 12.3%, max 21.0%, and the
shoulder cross-fall drops 0.836 m between 5 and 7 m lateral. Multiply and you get the observed
sag — pervasive because every node under a mountain road has slope.

**The drop is charged on SLOPE when chord safety only requires CURVATURE.** On a constant grade the
correct extra drop is zero; the code charges the full slope over 4.4–6.25 m.

### The shoulder pass dominates the deck pass ~14:1

| counterfactual (same 2,410 samples) | median | p95 | poke |
|---|---|---|---|
| as built | +0.400 | +1.110 | 0.00% |
| exact **deck** pin (stencil removed) | +0.379 | +1.065 | — |
| exact **shoulder** pin (stencil removed) | **+0.114** | **+0.565** | — |
| both stencils removed | +0.036 | +0.249 | **10.92%**, max +0.167 |
| 4.02 m cells, current policy | +0.170 | +0.515 | 0 |
| 2.68 m cells, current policy | +0.078 | +0.277 | 0 |

The deck stencil is worth 0.021 m of the 0.400 m median. The shoulder stencil is worth 0.286 m.

## The decisive finding

**The gate cannot be met at 8 m cells by any pin policy.** With both stencils removed entirely —
nodes pinned exactly to pavement − 0.01, the theoretical best — p95 is **+0.249 against a 0.10
gate**, and that residue is pure chord interpolation across the 8.03 m cell. Three harnesses agree
on this row.

So resolution near the road is **mandatory**, not an optimisation. This is L3b stated exactly:
the cell (8.03 m) is larger than the road it must follow (6.5 m carriageway).

## A bug found on the way (fixed)

`build_mesh.py:1598` — the shoulder pin's deck cap **and its bridge guard** both lived inside the
`if _tgt8 > _gy8:` raise branch. A pin that *lowered* fell through to the write with neither
applied. 68.4% of road-footprint nodes are set by that path, up to 1.779 m below the deck pin.
The bridge guard is now applied in both directions — under a declared span the terrain must keep
its natural height whichever way the pin wants to move it. The deck cap is left raise-only pending
the resolution work, because flooring a shoulder-side node at deck − clearance would push terrain
up through the *shoulder*.

## Why the obvious fixes do not work

- **Uniform refinement is unbuildable.** 2.01 m cells globally = 8661 × 2701 = **23.4 M** grass
  verts (780–3,120 chunks through `split_mesh_under_cap`'s 30k cap, `build_mesh.py:115`). The kn5
  is already **266 MB** at 8 m.
- **Corridor-only subdivision breaks the raster contract.** `grid_xyz` is a strictly rectangular
  list-of-lists; the pin's write-back indexes `[_j7w][_i7w]`; `ribbon.grass_terrain` (`ribbon.py:527`)
  triangulates `j*nx+i`; `write_ground_local` emits `{x0,z0,dx,dz,nx,ny,y}` and its docstring states
  the invariant ("the grid stays axis-regular"). Four further modules re-read it as a regular
  raster — `audit_mesh.py:475` (check G), `build_env.py:549` (all scenery seating),
  `build_network_mesh.py`, `build_network_env.py`. Sub-cell nodes cannot be expressed in any of them.
- **And it would crack.** 11,562 terrain quads intersect the pavement footprint; splitting only
  those leaves 2 hanging nodes on every boundary edge for 25.26 km — daylight beside the pavement,
  the failure class of [0004](0004-floating-edges.md). Cost is *not* the objection (+92k nodes at
  ×3); the stitching is.

## The fix worth building

A **corridor terrain strip**: a separately-triangulated fine mesh (~2.7 m) covering the pavement
footprint plus a margin, welded to the coarse raster along an explicit seam, with the coarse quads
it covers removed. The regular raster stays exactly as it is for `ground.local.json`, scenery
seating and check G, so no downstream contract changes. Vertex cost is ~0.15–0.2 M — *less* than
uniform refinement by two orders of magnitude, and it spends vertices where the car is instead of
on the 99% of the 94 km² grid nobody drives within 20 m of.

Pair it with a chord-safe (second-difference) pin rather than the slope-charging window minimum.
**Neither half reaches the gate alone** — pin policy alone floors at p95 +0.918 in its safe form,
2.68 m cells alone floor at +0.277.

⚠️ The specific chord operator proposed during diagnosis (`t = 2*ym − yn` at `h = spacing*0.5`
with a `ym` fallback) was **measured to be a near-no-op**: median +0.400 → +0.341, p95 → +1.026.
At 8 m cells the far sample lands off the 6.5 m carriageway for essentially every node, so it
degrades to today's full slope charge. Any chord form must be measured before it is believed.

## Verification

- `kn5_ground_check` p95 ≤ 0.10 m on Dragon Tail with **zero** grass-above-deck points (the
  no-stencil counterfactual pokes at 10.92% of 33,730 probe points — that is the trade to avoid).
- Sand Creek, Aspen, Grand Junction, Pikes Peak, IMI, Pueblo, High Plains, Lariat unchanged or
  better — they share every function touched.
- Kevin drives Dragon Tail and the grass meets the gravel at the edge.

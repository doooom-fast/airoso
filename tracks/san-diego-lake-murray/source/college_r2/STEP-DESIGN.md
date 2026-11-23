# The College split as an author step: design (draft, before any code)

Decided by the Mac, 2026-11-22: option B of `CONSUMERS.md`. Two roads, each with its own line, the way Mission Gorge
Speedway is built; every gate untouched; a new opt-in author step on round 1's chain (the seeded `loop.blend`), written
after Lake Murray 0.20.3 is green and merged. This file is the plan the step will be written to; nothing here is built.

## What the step does

Opt-in by a config key (absent = no-op, the blend not saved, as the other author steps). It reads
`source/college_r2/college_design.json` and runs **first in the author phase**, before `race_bands`, so the race
corridor, the dummies, the signs and every gate read the split road.

1. **The mainline becomes the southbound carriageway** through the zone. Its vertices keep their **numbers**; each
   moves sideways to the southbound pavement's midline, and its width becomes that carriageway's. No vertex is added
   or removed, so every vertex-keyed entry (below) still names the same place along the road.
2. **The northbound carriageway is a new named piece** (a record in `data/connectors.local.json`: name, points,
   widths; heights the measured ones), built by the step itself, since no draft step runs on a seeded blend.
3. **Pavement is covered once.** West of the shared line the mainline, east of it the piece; where there is no island
   the two ribbons share one edge (the crown) vertex for vertex; where the island stands, nothing is paved between
   its edges. No old slab stays underneath.
4. **The ground** between the carriageways (the planted bank) and east of the northbound road goes to the surveyed
   heights; real hills are not reshaped, only the road's own zone (Kevin: "Why are we changing ridges?").
5. **Curbs, walks, paint, the yellow line, the rail and the streetonly median** are rebuilt on the new section; the
   east lamps are re-seated; the houses are not moved (a check reports any whose seat the raised ground changes).
6. **The data that mirrors the scene** is rewritten in the same step: `centerline.local.json`, `finished_centerline.json`,
   `gate_centerline.json`, the widths, `median_bands.json` (no island on the mainline in the zone),
   `connectors.local.json`.
7. **Self-checks** (exit 1 = the blend is not saved): every mainline vertex outside the zone unmoved (hash); vertex
   count unchanged; pavement single coverage in the zone; the two ribbons' shared edge identical; design minus built
   at the zone ends under 5 cm; no ground over pavement. Idempotent: on a blend that already carries the split it is
   a no-op that says so (the synced-back blend becomes the next seed).

## The race

- **Speedway** (clockwise; northbound on College) becomes a stitched lap in `race.laps`: MAINLINE up to the piece,
  the northbound piece, MAINLINE from its far end, with declared joins at the two tapers (not junction pads).
- **Speedway Reverse** stays on the mainline, now the southbound carriageway.
- The crossover goes: `race.chicanes` entry `college_split` (`out_leg [1253, 1289]`, `back_leg [1343, 1379]`) is
  removed with its streetonly median pieces.
- **Mission Gorge Speedway** (`race.laps.north`) turns at College / Navajo with its box at v1452-1472 (apex 1463),
  noses ending at v1452 and closure runs to v1452. **Decided (the Mac, 2026-11-23): the split ends before that box.**
  The island ends at v1444 and the blend into the built road finishes by v1452, where northbound is about 0.6 m over
  southbound; the box is not re-declared. `college_design.py`'s zone (today v1130-1480, blended over its last 30 m)
  is re-cut to end at v1452 when the step is written.
- **J1's tilt** (Kevin: "Tilt it now"; measured 6.08 % falling toward bearing 277°, rms 0.13 m on the r 25 m plane) is
  its own change on the box's vertices, in the same round, with that lap's corridor and closures re-checked after it.
  A gate the tilt turns red is reported, never loosened.

## Keyed entries in `track.config.json` (round 1's base)

Vertex-keyed (unchanged, because the mainline keeps its vertex numbers): `layouts[].start.*`, `race.corridor.boxes /
closure_runs / whole`, `race.kerbs.trims`, `race.laps.north.pieces` and its corridor entries. To be re-declared because
the road under them changes: `race.chicanes` (removed), `route.median_registration` (10 of its 12 points are in the
zone; the island it registered is gone from the mainline), and the College stretch of the Speedway corridor (the lane
is the whole northbound carriageway, about 10 m, under the 11.36 m the corridor asks for elsewhere).

Station-keyed, in metres along the lap (these shift after the zone by the change in arc length, a few metres at most;
each gets its old and new value written down, as the Mac asked): `terrain.ground_release.zones[].s_m` (6),
`road_datum.decks[].deck_m / window_m`, `road_datum.profiles[].window_m / fold_fan_fit.fit_m`. The `college_split_cut`
ground-release zone exists for today's cut and goes with it.

## Free Roam traffic

No traffic lane graph is built for Lake Murray in this chain (`scripts/ac/write_traffic_json.py` is not a step in
`ship.json`), so there is no one-way data to set today. If traffic is added later, the northbound piece is one lane
set in its real direction, as that tool already writes each direction as its own one-way lane.

## Open before code

- The exact tiling at the two ends: where the piece's ribbon starts beside the mainline (a shared crown edge with the
  mainline narrowing to its southbound half), and how `race_lap.py` joins a piece that leaves the mainline at a taper.
- What the prep does with the piece beside the mainline (tiling of `ROAD`, the ground split within 16 m of a road).
- The Speedway lane on a 10 m carriageway: full width with both curb strips, or something narrower.
- Whether the bank needs a barrier along the northbound road's inner edge in the race layouts (the no-route flood must
  not reach the bank).

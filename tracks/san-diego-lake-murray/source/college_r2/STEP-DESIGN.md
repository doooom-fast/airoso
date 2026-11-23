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
- **Correction (2026-11-23): Mission Gorge Speedway does not run on College's split.** `race.laps.north`'s box at
  "v1452-1472" is in that LAP's own vertices (pad J4, Mission Gorge / Jackson north), not the mainline's; I read it as
  mainline vertices and the Mac's "end the split before that box" followed from my misreading. That lap uses the
  mainline only from v2317 back to v1517 (Navajo Road) and turns at J1 = the **mainline's** College / Navajo box,
  v1506-1521 (apex 1514), the same box both Speedways turn at. So the split's north end has from the island's tail
  (v1444) to that box (v1506), about 186 m; the south end has v1130 to the nose (v1172), about 126 m.
- **J1's tilt** (Kevin: "Tilt it now"; measured 6.08 % falling toward bearing 277°, rms 0.13 m on the r 25 m plane) is
  its own change on the vertices of the box at v1506-1521, in the same round, with every lap that turns there
  (Speedway, Reverse, Mission Gorge Speedway both ways) re-checked after it. A gate the tilt turns red is reported,
  never loosened.
- **The crossover was Kevin's.** `race.chicanes` `college_split` records his words (seat, 2026-10-14): "for the
  racetrack versions, I do like the chicane that kind of goes from one side of the road across to the other and
  back". Ledger 0055's realism+ decision (2026-10-27, "can you split them up and do something fun?") supersedes
  keeping it on a road that is not real, and says no replacement race feature was chosen. Each direction on its own
  carriageway, 6 m apart in height, is the proposal; Kevin has been asked and has not answered.

## The two ends: forks as measured pads (read 2026-11-23; the approach to build)

Through the split the mainline is the southbound carriageway; outside it the mainline is the whole road with the
island on its line (the College run of `median_bands.json`, v825-1509). Between the two meanings the line moves
sideways by 5 to 6.4 m and the width changes from the whole road (25 to 30 m) to one carriageway (about 10 m).

What the reads found:

- **`island_offsets` cannot carry it.** It is lap-only, refuses MAINLINE by name (`race_lap.py:428`), and its snap
  is capped at 3.0 m (`ISLAND_OFFSET_SNAP_MAX_M`). But it is not needed: the real road has **no island** in the two
  drift zones. The island read (`college_edges.json`) is v1104-1116, **v1172-1444**, v1476-1507; the build's 7 m
  island across v1117-1171 and v1445-1475 is not on the ground. It goes there (island width 0), so nothing stands
  off the line while the line drifts.
- **A lap's join needs no pad.** `race_lap.stitch` bridges consecutive pieces along the straight join, or takes a
  declared join whose two ends sit within 0.05 m of the piece ends (`JOIN_END_TOL_M`); `junction_pads` is optional.
- **A wedge is the wrong shape.** With the northbound piece starting as a sliver at the east curb, Speedway's lane
  (the road's east half) lies across two ribbons through the drift, and the curb strips that every lap line gets on
  both edges would stand along the shared edge, across open pavement.
- **The engine already has the right shape: a pad on the lap.** `tools/lm_pads_blend.py` (ledger 0078 round 7):
  "the LAP itself is both main arms". The mainline is cut at two declared rows, every ROAD / CURB / MARKINGS / YLINE
  face between them goes (the vertices stay, so index-reading steps still work), and a **measured deck** is
  triangulated inside the measured pavement outline and welded to the rows, seam 0.000 m. Ledger 0055's own step 4
  pointed here ("Reuse the existing pad authoring ... do not assume their current J2-J4 connector-arm support already
  handles a cut through MAINLINE").

So each end of the split is a **fork pad**:

| | South fork | North fork |
|---|---|---|
| mainline rows | v1130 (whole road) to v1172 (the nose: southbound carriageway) | v1444 (the tail) to v1476 (whole road, the short island resumes) |
| third arm | the northbound piece's first row, at the nose | the northbound piece's last row, at the tail |
| length | about 126 m | about 96 m |
| deck | the measured pavement between the rows, heights off the lidar's 1 m grid | the same |

Inside a pad the mainline's line drifts from the road's centre to the southbound midline as a reference only (no
ribbon is swept there). Speedway is a stitched lap that drives through both pads onto and off the northbound piece
(`race.laps`, `junction_pads`); Speedway Reverse stays on the mainline through both. The two rows of each pad are
chosen where the read is clean; the numbers above are the read's, to be confirmed on the outline.

What the pad tooling says (read 2026-11-23):

- **`tools/lm_pads_blend.py` cannot be run as it is on Lake Murray** ("Lake Murray never runs it"): it is a draft step
  for the circuit ports' edge-strip section, and Lake Murray's streets carry a curb-and-walk section in `CURB`. Lake
  Murray's own pads (J2-J4) come from `tools/junction_pad.py` + `tools/author_junction_pad_blend.py`, which weld onto
  connector ends and take no lap arm. So the new step builds the fork decks itself, with the same parts both tools
  use: the assembler's row layout (`tools/mouth_weld.py` `mesh_layout` / `road_index`: left edge, centre, right
  edge), `draft_pads`' deck fill and seam fade, `stub_geom`'s K-rail.
- **A third arm is already a known shape** (`lm_pads.arms: "streets"`, ledger 0079): "each arm's end row joins the
  deck exactly as a lap cut row does: spliced into the outline along its box edge, a seam (its vertices pinned), its
  departure from the lidar faded in". The northbound piece's first and last rows are that arm.
- **The step between the carriageways is grade, not seam** (the Mac's check). The deck's heights are the lidar's 1 m
  ground, so it carries the real fall between the northbound and southbound sides (0.6 to 1.3 m at the two ends)
  across the deck's width. Each arm's row is pinned at that arm's own heights, and since the design's heights are the
  same lidar smoothed over 15 m, the deck's departure at a seam is centimetres, faded in over the seam's length.
- **The gate takes them as pads.** `tools/verify_pads.py` reads `data/pads.built.json` and judges, on the built
  OBJ: deck, curb and barriers present; single coverage; every arm's seam within 10 mm and each arm row's three
  vertices matched within 1 mm; no ground over the deck; no curb over it; the node's height. The step records the two
  forks there in `author_junction_pad_blend.py`'s schema (objects `1ROAD_pad_<id>`, `1KERB_sidewalk_pad<id>`; seams
  per arm). No threshold moves.
- **The race corridor already has a zone for it.** In `barrier_bands.py` every vertex outside a closure run is `box`
  (or `whole` inside the one whole-street interval): an open intersection. The two forks are declared as boxes and
  the closure runs stop at their rows.

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

- The exact rows of each fork (the south one between v1130 and v1172, the north one between v1444 and v1476),
  chosen on the measured outline.
- What the prep does with the piece beside the mainline (tiling of `ROAD`, the ground split within 16 m of a road).
- The Speedway lane on a 10 m carriageway: full width with both curb strips, or something narrower.
- Whether the bank needs a barrier along the northbound road's inner edge in Free Roam (in the race layouts the
  northbound piece's own curb strips seal it).

## Order of work

1. The data: the northbound piece's record and the mainline's moved vertices, widths and island widths, written to a
   scratch workshop only; the stitched Speedway lap declared and `race_lap.stitch` run on it (no Blender).
2. The scene, ribbons only: the mainline's rows moved, the piece's ribbon built, the old faces gone; self-checks.
3. The two fork decks, their curbs and seams; `verify_pads` on the built OBJ of the scratch scene.
4. Ground, curbs, walks, paint, lamps; then the race steps of the chain in the scratch workshop.
5. A full rehearsal through the Mac's queue.

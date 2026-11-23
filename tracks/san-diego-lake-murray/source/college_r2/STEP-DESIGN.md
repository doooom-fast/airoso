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
   widths), built by the step itself, since no draft step runs on a seeded blend. Its heights are NOT measured
   heights: they are the built west edge's height plus the measured rise ("Step 1 done", `college_datum_offset.json`).
3. **Pavement is covered once.** West of the shared line the mainline, east of it the piece; where there is no island
   the two ribbons share one edge (the crown) vertex for vertex; where the island stands, nothing is paved between
   its edges. No old slab stays underneath.
4. **The ground** between the carriageways (the planted bank) and east of the northbound road follows the two roads
   (which carry the datum's offset from the lidar) and meets the surveyed ground beyond the road's own zone; real hills are not reshaped, only the road's own zone (Kevin: "Why are we changing ridges?").
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

## The two ends: forks as measured pads (read 2026-11-23; SUPERSEDED by "Step 2 done" below: the forks are plain road)

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

## Step 1 done: the data (2026-11-22)

`college_split_data.py` (pure Python, no Blender) computes it, `college_split.data.json` is its output and
`college_split.png` the picture of it. `--write` puts it into a project's data; so far only into the scratch copy
`D:/k10-scratch/lm_r2_college/project` (each file kept once beside itself as `<name>.pre-split`).

What `--write` changes, checked against the pre-split files:

- `centerline.local.json`, `finished_centerline.json`, `gate_centerline.json`: 345 vertices moved (v1131-1475) and
  their 345 widths. Nothing else: 4,499 points with the closing one, every other point, width and key identical.
- `median_bands.json`: island width 0 on v1117-1475 (359 vertices, were 4.39 to 7.0 m); the College entry of `runs`
  becomes two (825-1116 and 1476-1509).
- `connectors.local.json`: one record added, `college_nb` (273 points and widths); the 34 others unchanged.
- the project's own `track.config.json`: `race.laps.college` added, nothing else.

How the lines are made. Each rule is there because the simpler one measured wrong:

| Tried first | What it measured | What the script does now |
|---|---|---|
| Line = midline of the raw measured edges | 7.8 deg turn between 3 m segments (the built line: 1.08) | the inner edges are relaxed (1-2-1, 24 passes, ends held) |
| Relax the midline itself | the inner edge moves by twice the correction: the two roads overlap 0.24 m at the nose | relax the EDGES; the northbound inner edge = the southbound one less the bank's width, and the bank's width is relaxed with its ends held, so it is never negative |
| Built outer edges from `college_edges.json` | 5.9 deg: `built_from_m` / `built_to_m` are floored to the lidar's 0.5 m cells | built outer edge = half the centreline's width (ROAD's own edge column) |
| Fork line = midline of the built edges | 3.3 deg at v1171: the built road's own edge has a 6 deg corner there | in a fork the line is a cubic that meets both ends in place and in direction; it takes nothing from the built edges |
| Heights sampled raw from the measured section | grade steps of 2.1 points between segments (the built line: 0.57) | height = the built road's height + the relaxed measured tilt (the tilt is smoothed, never the road) |
| Heights = the measured surface itself | the southbound road leaves its built height by up to 0.8 m, so the west walk and the house lots behind it would have to move (stage A: they stay put) | the datum is the BUILT WEST EDGE, which keeps its place and its height; the lidar gives the shape across the road: each road's crossfall and the northbound road's rise |

`SMOOTH_PASSES = 24` (about +-10 m along the road) is `[invented]`.

The numbers (`college_split.data.json` `report`):

| | Built line | Mainline (southbound road) | Lap `college` (joins + `college_nb`) |
|---|---|---|---|
| Largest turn between segments | 1.08 deg | 1.53 deg | 1.38 deg |
| Steepest grade down / up | -8.16 / +8.76 % | -8.03 / +8.77 % | -8.79 / +8.77 % |
| Largest grade step between segments | 0.57 points | 0.65 | 0.75 |
| Segment length | 3.0 m | 2.94 to 3.11 m | 2.72 to 3.28 m |
| Width through the two roads | 25 to 32.5 m (whole road) | 9.99 to 15.34 m | 8.36 to 14.1 m |

- The mainline moves up to 10.67 m west; its length grows by 1.93 m (13,471.3 to 13,473.2 m to the last vertex).
- The northbound road rides up to 5.81 m over the southbound one, line to line; 0.57 m where the island begins, 0.56 m
  where it ends (the road is banked there). Across the bank, inner edge to inner edge: nothing at the nose and the
  tail (one point, see step 2), up to 6.11 m; the bank's slope is up to 52 %.
- The bank between them: no width at the nose and the tail (the two roads meet in a point), up to 12.18 m.
- After smoothing the inner edges stand up to 0.38 m (southbound) and 0.73 m (northbound) off the measured edges.
- **What is measured and what is not** (the Mac, 2026-11-23). Measured: each road's crossfall and the northbound
  road's rise over the southbound one. NOT measured: the absolute heights, which are the built west edge's; that
  edge stands -0.54 to +0.83 m off the lidar. `college_datum_offset.json` records it per vertex (v, station, built
  edge, lidar there, built minus lidar). Where the built height came from is not established: it is within 0.4 m
  of `data/centerline.elevation.json`'s smoothed 3DEP profile through the zone but is not that profile. Putting
  the road on the lidar would move the west walk and the house lots; it is on the list for after College.
- Heights. A row is tilted, not flat: west edge, line + 0.10, east edge, each at its own height (`edges` in the data
  file). The built west edge keeps its height, so every height here stands off the lidar by what that edge does
  (-0.54 to +0.83 m, smooth along the road). The mainline's line moves -0.25 to +0.23 m from its built height (the
  southbound crossfall, -4.8 to +3.3 %, rising east positive); the northbound crossfall is -4.4 to +4.3 %.

The lap. `race_lap.stitch(proj, cfg, "college")` on the scratch project: 4,498 lap vertices, the mainline's own count;
both declared joins accepted (their ends 0.000 m off the piece ends; 41 and 31 points, 127.3 m and 96.7 m); every lap
vertex taken from the mainline has the mainline's number, and the piece is lap v1172-1444; lap length 13,472.8 m.
Mission Gorge Speedway's lap (`north`) stitched again on the same data is identical to its `data/lap.north.json`
(0.0 m, same widths, same islands).

Metre-keyed config entries after the zone (the rest of `terrain.ground_release.zones` ends at 2,745 m, before the
zone's 3,386 m, or is keyed by vertex, so none of it shifts):

| Entry | Old (m) | New (m) |
|---|---|---|
| `road_datum.decks[1].deck_m` | 13347.0, 13424.0 | 13348.9, 13425.9 |
| `road_datum.decks[1].window_m` | 13322.0, 13432.0 | 13323.9, 13433.9 |
| `road_datum.decks[2].deck_m` | 13432.0, 13457.0 | 13433.9, 13458.9 |
| `road_datum.decks[2].window_m` | 13424.0, 13472.0 | 13425.9, 13473.9 |
| `road_datum.profiles[1].window_m` | 13280.0, 230.0 | 13281.9, 230.0 |

Found for the next steps:

1. **The forks' other road is not a mouth the lap knows.** Stitch skips both ("MAINLINE beyond v1130" and "MAINLINE
   before v1476": "the branch is the lap"), because its probe 10 m past the fork row still stands on the lap's own
   pavement. So the no-route gate will not ask on its own that the other carriageway is sealed: the southbound road
   at the nose and the tail for Speedway, the northbound piece's two ends for Reverse. Those closures and their probes
   have to be declared in step 4; until they are, a green no-route gate says nothing about them.
2. **`college_edges.json`'s built edges are floored to 0.5 m.** Not to be used as the built edge anywhere.
3. **Lake Murray 0.20.4 is the base now** (round 1c, `claude/lm-sidewalk-20261122` c8debb5f, ledger 0099; merged into
   this branch 2026-11-22, c6e1b599). It adds the author step `walk_grade` (`tools/author_walk_grade_blend.py`,
   second after `lamp_heads`) and the prep sub-step `--seat`. `walk_grade` finds a walk's back-grade lip by shape (an
   edge 1.0 to 1.45 m in plan and 0.10 to 0.45 m down from the walk's back edge) and raises it to a slope the drive
   test passes. So the walks this step rebuilds must have the draft's own section (0.08 m batter up 0.14 m, a flat
   walk, a 1.2 m back grade) for it to find them, and the College step must run BEFORE `walk_grade`: first in the
   author phase, as planned above, then `lamp_heads`, `walk_grade`, the race steps. A lip in a ground-release zone is
   held to the released ground: `college_split_cut` goes with the split, so the zone that replaces it decides what
   the east walk's lip is held to.
4. **The Speedway lane on the northbound road** is 8.36 m at its narrowest against the 11.36 m the corridor asks for
   elsewhere: still open (above).

## Step 2 done: the scene's ribbons (2026-11-22)

`college_split_blend.py` edits the object ROAD of the open blend from `college_split.data.json`. Run on the scratch
scene and saved as a copy, `D:/k10-scratch/lm_r2_college/step2/loop.split.blend`; the seed copy is untouched (md5
ef4d0ca3 before and after). `college_split_stills_blend.py` renders ROAD and TERRAIN only from five cameras, before
and after: `college_split_step2.jpg`.

Read first, read-only:

- ROAD's mainline block is three vertices per centreline vertex for all 4,498 of them (3v = west edge, 3v+1 = line,
  3v+2 = east edge), flat at the line + 0.10, four triangles per segment, UV = (offset from the line / 4, station / 4).
- **No side street joins College inside the zone**: no face of the zone uses a vertex outside the mainline block and no
  edge vertex stands off its drafted place (ROAD's 32 welded mouths are all elsewhere).
- The prep (`scripts/ac/build_kn5_loop.py`) reads ROAD as plain triangles; nothing there counts on vertex numbers.
- What else stands in the zone's footprint: CURB (both walks and the old island), the street-only median pieces
  (v1253-1379), GUARDRAIL and YLINE on the line, MARKINGS, LIGHTPOST_3 / _4 and LIGHTS_0, TERRAIN (1,444 vertices under
  the old island up to 0.29 m over the line; 4,277 in the east strip), and the race walls the chain re-authors.

What the step does:

- **Two roads, v1172-1444.** The mainline's row becomes the southbound road: the west vertex is not touched, the line
  vertex goes to the new line, the east vertex to the island's west side. Its four faces per segment stay, so no old
  slab is left under the northbound road. The northbound road is a new ribbon of three vertices per station appended to
  ROAD (817 vertices, 1,088 faces), its east vertex where ROAD's east vertex stood, raised.
- **Rows are tilted, not flat**: each vertex has its own height (step 1's datum: the built west edge).
- **UVs keep the built convention everywhere** (u = offset from the BUILT line / 4, v = the built row's own), so the
  asphalt runs unbroken across the forks and both roads.

Result (the step's own checks; exit 1 and no save on any failure): 26,944 -> 27,761 vertices, 35,209 -> 36,301 faces
(8 removed, 1,100 added); 690 vertices moved and no other, the west edge column included; no face of the zone
degenerate or turned over, the steepest lies 7 % off level; **coverage: 41,072 plan samples, 31,486 on pavement each
under exactly one face of ROAD, 9,586 on the bank under none.** A second run on its own output changes nothing.

**The forks are not pads (this changes the plan above).** The fork-pad plan cut the mainline at two rows, deleted the
faces between them and laid a measured deck with its own records and gate. Reading the scene showed that is not
needed: with the built outer edges kept, the fork's pavement outline IS the built road's, and the built rows already
pave it. So in a fork (v1131-1171, v1445-1475) the three vertices of each row keep their place and take the tilt
easing in from the flat outer row, and between the last fork row and the first row of the two roads the four old
faces are replaced by a fan of six from the fork row's centre vertex. One ribbon in the fork, nothing deleted but
those eight faces, no deck, no `pads.built.json` record, no `verify_pads` involvement: the forks are plain road, judged
by the street gates (drive test, street audit, ground check). The lines through a fork (the mainline's and the lap's)
are references that drift inside that pavement. What a pad would have given the race (a probe on the road the lap
turns away from) is met by the declared closures and probes of step 4 either way.

**The island begins and ends in a point.** The design tapered the island to 0.35 m / 0.30 m at the nose and tail rows
with an 0.18 m step between the roads: in the mesh that is a 0.35 m sliver of pavement at 52 %. The bank's width and the
step across it now run to zero at those two rows, so the two roads share one vertex there (0.11 m and 0.12 m of step
one row in).

Seen in the stills, for the later steps: the old island's ground stands up to 0.3 m over the line inside its old
footprint, so it shows through the fork's pavement (the prep pins ground under pavement; to be confirmed when the
chain runs); the northbound road rides over ground that still sits at the slab's height.

Order of work from here (replaces 3 to 5 above):

3. The old middle goes and the new one is built: CURB's island faces on v1117-1475, the street-only median, GUARDRAIL,
   YLINE and MARKINGS on College; then the two roads' inner curbs along the bank, the east walk at the northbound road's
   height (the draft's section, so `walk_grade` finds its lips), paint on both roads.
4. Ground (the bank, the east side cut, the old island's fill), lamps; then the data into the workshop and the chain's
   race steps, with the fork closures and probes declared.
5. A full rehearsal through the Mac's queue.

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
| Steepest grade down / up | -8.16 / +8.76 % | -7.91 / +8.76 % | -8.74 / +8.76 % |
| Largest grade step between segments | 0.57 points | 0.61 | 0.74 |
| Segment length | 3.0 m | 2.94 to 3.11 m | 2.72 to 3.28 m |
| Width through the two roads | 25 to 32.5 m (whole road) | 9.99 to 15.34 m | 8.36 to 14.1 m |

- The mainline moves up to 10.67 m west; its length grows by 1.93 m (13,471.3 to 13,473.2 m to the last vertex).
- The northbound road rides up to 5.82 m over the southbound one, line to line; 0.46 m where the island begins and
  where it ends (the road is banked there; rows planar since step 4, see "Step 4a to 4c done"). Across the bank, inner edge to inner edge: nothing at the nose and the
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

1. **The forks' other road is not a mouth the lap knows, and it does not need to be.** Stitch skips both ("MAINLINE
   beyond v1130" and "MAINLINE before v1476": "the branch is the lap"), because its probe 10 m past the fork row still
   stands on the lap's own pavement. CORRECTED 2026-11-23: this note first said a green no-route gate "says nothing
   about" the other carriageway. That was wrong. `tools/no_route.py` floods every cell within half the road's width
   + 25 m of the lap's line and fails ANY reached cell outside the declared corridor, mouth or no mouth; the other
   road at each fork lies inside that reach, so an unsealed fork is a leak the gate reports. What step 4 had to do was
   declare the corridor there (the closure through each fork), not add probes by hand.
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

## Step 3, the plan (read 2026-11-23, before code)

What stands on the old middle, and who made it (`tools/author_median_blend.py`, ledger 0037 / 0055):

| Thing | Where it lives | Shape |
|---|---|---|
| Island curb | joined into `CURB` | a ring of six vertices per station about the line: base at +-3.50 (0.02 under the road), top at +-3.46 and +-3.35 (0.18 over it); four bands of quads between rings; a nose tapers over 3 stations to a half width of 0.25 m and is capped |
| Island top | joined into `TERRAIN` (grass) | two vertices per station at +-3.28, 0.185 over the road; one quad per segment |
| Barrier | joined into `GUARDRAIL` | a box beam 0.24 m wide from 0.45 to 0.75 m over the curb top on the line, posts every 8 m or so; only on islands of 120 m or more, and not within 3 stations of an end |
| Shrubs | joined into `SCRUB` | two crossed quads per clump, one clump every 3.2 m or more, on the top |
| Street-only pieces | `1KERB_sidewalk_streetonly_median`, `1WALL_guard_streetonly_median` | the same curb and beam over v1253-1379, where the race layouts cross (the chicane `college_split`) |
| Paint | `MARKINGS`, `YLINE` | loose quads per segment: double yellow at +-0.09, white edge lines 0.55 m inside each edge, dashed white dividers every 3.65 m from the line (3 m on, 9 m off, by station), 0.015 over the road |
| Walks | `CURB` | four vertices per station per side: lane edge, curb top (0.08 out, 0.14 up), walk back (1.8 m), lip (1.2 m further, 0.10 under the line). Not addressable by index on College (the strip's numbering is shifted by the mouth welds): by position |
| Lamps | `LIGHTPOST_3`, `LIGHTPOST_4`, `LIGHTS_0` | posts stand in the two walk strips, none on the median; their arms reach over the road |

So on the old median stood: the barrier, the shrubs and the street-only pieces. No lamp post. Signs are re-authored by
the chain every run (the `signs` step) from the road's data.

Step 3a, the old middle out (everything by position in the built line's frame):

- `CURB`: the island's faces on the segments between rows v1116 and v1476; the two islands that stay (to v1116, from
  v1476) get the tool's own nose: their last three rows taper to a half width of 0.25 m and are capped.
- `TERRAIN`: the island top's faces on the same segments (and the three tapered rows' top vertices follow the taper).
- `GUARDRAIL`: the College island's beam and posts from row v1114 on (the island that stays to the south keeps its beam
  up to three rows before its new end); all of it north of v1475 (the island left there is 24 m, under the 120 m rule).
- `SCRUB`: every clump on the old island between v1114 and v1478.
- the two street-only objects, whole (their span is the chicane's, which goes).
- `YLINE` and `MARKINGS`: every quad with both ends on rows v1130..v1476.

Step 3b, the new middle and the east side:

- **The bank's island** into `CURB`, rows v1173..v1443: the same six-vertex ring, its west side on the southbound
  road's inner edge and its east side on the northbound road's (each side at its own road's height); at v1172 and
  v1444, where the two roads meet in a point, a fan of five faces from that point up to the first ring (a pointed nose
  that rises from the road). **The bank's top** into `TERRAIN`: one quad per segment between the two curb tops.
- **The east walk** in `CURB`: its vertices on rows v1131..v1475 rise with the road's east edge (the same amount as
  ROAD's east vertex of that row); its section does not change, so `walk_grade` finds its lips. The west walk is not
  touched.
- **The barrier** into `GUARDRAIL`: the tool's beam and posts, standing at the top of the bank just behind the
  northbound road's inner curb, rows v1176..v1440. A car that leaves the northbound road toward the bank meets it; the
  southbound road's inner edge has rising ground behind its curb and needs none.
- **Shrubs** into `SCRUB`, on the bank, by the tool's own rule (one clump every 3.2 m or more).
- **Paint**: the forks keep the built pattern on the tilted surface, the double yellow bending to the point where the
  roads part. Each road of the split is one-way: a solid yellow line 0.55 m inside its median edge, a solid white one
  0.55 m inside its outer edge, dashed white dividers every 3.65 m counted from the yellow, none closer than 2.4 m to
  the white edge line [invented: lanes are not measured yet; the 10 cm aerial work replaces this].

Left for step 4: the ground under and beside all this (the old ground inside the bank's footprint, the east side's cut
up to the raised walk, the fill of the old island in the forks), the east lamps and `data/lights.local.json`, then the
data into a workshop and the chain's own steps.

## Step 3 done: the middle (2026-11-23)

`college_middle_blend.py`, run on step 2's scene and saved as a copy
(`D:/k10-scratch/lm_r2_college/step2/loop.middle.blend`; the seed copy untouched, md5 ef4d0ca3). Stills with road,
curbs and walks, rail and paint shown, before and after: `college_split_step3.jpg`.

Faces out and in, per object:

| Object | Faces removed | Faces added | What |
|---|---|---|---|
| `CURB` | 940 | 1,094 | out: the old island's curb between rows v1116 and v1476 (936 band faces and the 4 cap faces at the chicane's two cuts). In: 271 rings of the bank's island (1,080 faces), a pointed nose of 5 faces at each end, the 4 cap faces of the two islands that stay |
| `TERRAIN` | 360 | 270 | out: the old island's grass top, one quad per segment. In: the bank's top |
| `GUARDRAIL` | 1,300 | 1,408 | out: the College island's beam and posts from row v1114 on. In: the beam on rows v1176-1440 (1,056 faces) and 88 posts |
| `1KERB_sidewalk_streetonly_median` | 504 | 0 | the object is gone (its span was the chicane's) |
| `1WALL_guard_streetonly_median` | 672 | 0 | the same |
| `YLINE` | 1,384 | 1,384 | repainted on rows v1130-1476 |
| `MARKINGS` | 2,556 | 2,186 | repainted on the same rows |

The step's own checks (exit 1 and no save on a failure): in `CURB` no vertex moved but the 1,380 of the east walk (4 a
row on rows v1131-1475; they rise 0.001 to 5.551 m with the road's east edge) and the 36 of the six tapered rows; no
`CURB` vertex stands on either road's pavement along the two roads; none of the old island is left between rows v1116
and v1476; every paint vertex in the zone stands 0.015 m over its own road (none over the bank; no divider had to be
left out). A second run on its own output changes nothing.

What stood on the old median, and where it went:

- **No lamp**: the posts of `LIGHTPOST_3` / `_4` stand in the two walk strips; only their arms reach over the road.
  (The east ones still stand at the old height: step 4.)
- **No sign**: the nearest signed corner is J1, apex v1514, outside the zone.
- **The barrier**: out with the island; a new one stands at the top of the bank, 0.45 m behind the northbound road's
  inner edge.
- **Plants: yes, as data.** This scene has no `SCRUB` object; the median's plants are TreeFX bushes from
  `data/scatter_positions.json` `median_planting`. **120 of them stand on rows v1114-1478**: 30 in the south fork (on
  what is now pavement), 72 along the two roads, 18 in the north fork and beyond. Nothing in the scene moves them: the
  data step has to drop those 120 and plant the bank instead. Until then a build would put bushes on the fork's
  pavement. That is in step 4's list.
- **The islands that stay** (to v1116 in the south; v1476-1487 in the north) end in the median tool's own nose now:
  three rows tapering to 0.5 m and a cap. The north one is 12 rows long.

Choices made here, each `[invented]` until something measured replaces it: the barrier's place (0.45 m behind the
inner edge, posts 0.35 m into the bank, beam four rows in from each end); the paint on the two one-way roads (yellow
0.55 m inside the median edge, white 0.55 m inside the outer edge, dashed dividers every 3.65 m from the yellow, the
built clip rule; the double yellow of each fork opens into a gore that meets the two yellows where the roads part).
The lanes are not measured: the 10 cm aerial work replaces this paint.

Step 4 from here: the ground (the old ground inside the bank's footprint and under the northbound road, the east
side's cut up to the raised walk, the old island's fill in the forks), the east lamps and `data/lights.local.json`,
the 120 median plants in `scatter_positions.json`, the config (the chicane, `route.median_registration`, the
`college_split_cut` zone, the corridor on the piece at its real width, the fork closures and probes), then the data
into a workshop and the chain's own steps.

## Step 4, what is settled before code (2026-11-23)

The Mac's rules for this step:

- **Build without the chicane** (the board tells Kevin it goes with the split by default; he has not answered otherwise).
- **Plants.** Kevin decided on 2026-11-22: "Keep all 33 at their lidar heights" (the 33 tall median plants). Which of
  the 33 fall on rows v1114-1478 has to be checked. Any on the real bank stay at their measured place and height. Any
  that would land on pavement are LISTED (id, station, which road) for the Mac to decide; they are not moved or dropped
  here. The median bushes now on the fork's pavement are dropped. The bank is planted only from measured positions (the
  lidar canopy or the aerial, the way the 33 were found), never from an invented spacing; if the bank's real planting
  cannot be read, nothing new is planted and the report says so. The report gives the count dropped and the count
  planted, and where each came from.
- **The barrier.** Look at the lidar or the aerial: does the real bank have a rail at its top? If it has none, say so
  in the ledger and take step 3's rail out. If it cannot be told, it stays `[invented]`.
- **The paint** stays `[invented]` until the 10 cm aerial work replaces it.
- **Queue.** When (e) is green, tell the Mac. Round 2 goes after Lake Murray 0.20.4 installs and merges; then merge
  main at the commit the Mac names (no rebase) and take the next version after 0.20.4.

What the prep does with ground (`scripts/ac/build_kn5_loop.py` `_conform_and_reseat`, read 2026-11-23):

- Every grass vertex within reach of a road is given a LEG (the mainline, or a connector of
  `data/connectors.local.json`) and a station, and seats only on its own leg's pavement within 40 m of its own station.
  `college_nb` becomes a leg as soon as it is in the data.
- Under its own leg's pavement a vertex is SET to the deck less 0.02 m (up or down). Past the edge the first 3 m are
  held at the edge's height and the next 6 m blend back to the vertex's own height.
- Then any grass vertex that stands over the lowest drivable sheet (road or kerb) at its place is pushed under it.
- Terrain edges near a road are split to about 4.5 m first, so authored quads get more vertices, each treated as above.
- The old island's grass top lies over the slab, so the prep pins it under the road: in the game the built island
  shows asphalt between its curbs, with the bushes standing on it.
- `data/ground_release.json` (the draft's released ground: 44 zones and a 2 m lattice of heights) is not read by the
  prep at all.

What that means for the bank, to be settled by looking, not by reading: step 3's authored bank top is grass, so the
prep will hold its first 3 m beside whichever road each vertex is given to at that road's edge height and blend from
there; the old ground under the bank and under the northbound road is treated the same way. The first thing to do in
step 4 is therefore to run the prep on the scratch scene once (a scratch workshop, below-normal priority) and look at
what the bank, the forks and the east side come out as. The ground is designed from that picture.

## Step 4a to 4c done: the prep read and run, the ground, the east lamps (2026-11-23)

**Correction to "Step 4, what is settled before code".** What that section says about the prep was read off airoso's
`scripts/ac/build_kn5_loop.py`. Lake Murray does not run that file: `tools/ship_track.sh` runs the prep from `ENG`, a
copy of engine-july (`D:/k10-scratch/eng_repro`, as ledger 0099's runbooks name it), and its `build_kn5_loop.py` is a
different program. What Lake Murray's prep does with ground (`_conform_and_reseat`):

- A ground vertex with pavement straight above or below it (the highest road surface there; no legs, no stations) is
  SET to that surface less 0.02 m. Only at the ground's own vertices.
- Past the edge, the first 3 m are held at the nearest pavement's height and the next 6 m blend back, UNLESS the vertex
  is in a released zone (`data/ground_release.json`: a station range on the mainline, a side, from 0.5 m inside the
  pavement edge out to `reach_m`). Released ground is left exactly as the scene has it. So it IS read, and it is the
  mechanism for the split's ground.
- Ground edges near a road are cut to about 4.5 m BEFORE the pin, at heights interpolated from the old ground; a vertex
  the prep makes inside a released zone keeps that height.
- Any ground vertex over the lowest road or kerb surface at its place is pushed under it.
- Before all that the ground is welded at 5 cm and its holes of up to 16 sides are filled.

**The test set-up** (scratch only): workshop `D:/k10-scratch/lm_r2_college/ws4` (the split's data, the scene after
steps 2 to 4 with the old race furniture taken out, since the chain re-authors it), engine copy
`D:/k10-scratch/eng_r2_college` (identical to `eng_repro`), the released zone `college_split_cut` widened in the
workshop's `ground_release.json` to the whole split (rows v1130-1476, the mainline's right side, 40 m).
`college_prep_look_blend.py` exports the prepped ground, road and kerbs near College and renders stills;
`college_prep_measure.py` samples them (no Blender). **Six prep runs** were needed (the Mac had cleared one; each took
4 minutes at below-normal priority, one Blender at a time): each run showed a real fault of mine, listed here because
every one of them would have reached a build.

| Run | What it showed | What changed |
|---|---|---|
| 1 | ground through the southbound road at 148 samples and the forks at 16; the east walk up to 1.9 m over its ground on rows v1131-1197; old ground 0.35 m through the bank's top | see below |
| 2 | the east side and the forks clean; the southbound road still 332 of 2,439 | rows planar; the east shelf as its own strip |
| 3 | the bank's top cut to pieces by my own step | old ground cut fine under the split |
| 4 | the bank's top whole again; southbound road 75 | the bank's top tagged on the mesh |
| 5 | southbound road 34, all at the inner edge on rows v1257-1304 | old ground in the bank pushed under the lower inner edge |
| 6 | **clean** | cut and split triangles in the same round |

What the faults were, and the rule each one left in the scripts:

1. **Rows are planar across** (`college_split_data.py`). A line used to carry a height of its own, up to 0.06 m under
   the chord of its road's two edges (0.10 m in the forks): a shallow valley along the line that ground facets bridged.
   Now every line rides on that chord. Where the two roads part and meet, their rows and the fork's row are one
   straight section (the shared point is put on the chord from the built west edge to the east edge: 0.108 m at the
   nose, 0.144 m at the tail), and that correction is eased out over 20 rows with each row's own value, so neither
   line's grade steps there (0.61 and 0.74 points at most, the built line 0.57).
2. **The east ground is a strip of its own** (`college_ground_blend.py`). Raising the old ground's vertices worked only
   where it is dense. The strip runs along rows v1130-1476 from the built east edge: at the edge's road height less
   0.02 m for 3.5 m, then falling 1 in 2 until it is under the old ground (4.5 to 8.5 m out, on all 347 rows), then
   0.3 m under it. Where the hill is higher the old ground shows (the cut); where it is lower the strip is a fill.
   (CORRECTED 2026-11-23, "0.20.5's first rehearsal" below: the code did not hold it 0.3 m under the old ground. It
   ran every row on to 19.5 m at the lower of the falling fill and that, up to 19.4 m down inside the hill.)
3. **The old ground under the split is cut to 1.5 m edges first**, under the whole footprint (both roads, the bank, the
   forks): 47,628 edges in 13 rounds. Under the one slab it was a few triangles 10 to 70 m across; the prep pins them
   at their own corners only, and puts its own vertices on their long edges inside the released bank at the old slab's
   height.
4. **Old ground inside the bank is pushed 0.10 m under the lower of the two inner edges** (3,589 of 10,371 vertices,
   up to 0.47 m). The southbound road's inner edge lies up to 0.5 m under the old slab.
   (CHANGED 2026-11-23, "0.20.5's first rehearsal" below: beside each road it is now SET just under that road's inner
   edge, and what lies wholly under the bank's top is taken out.)
5. **A vertex is told apart by a tag on the mesh, never by a Python reference.** `bmesh.ops.subdivide_edges` leaves
   every earlier reference invalid; after its first round the bank's top was no longer protected. The same weakness
   was in step 3's "no other vertex moved" check, which could not fail; it now compares 83,646 surviving vertices by an
   id stored on the mesh.
6. **A cut splits its own triangles** (`use_single_edge`, `use_grid_fill`). Triangulating the many-sided leftovers
   afterwards fans out in long diagonals, which the prep then cuts itself.

**Measured on run 6** (`college_prep_measure.scratch.json`; stills `college_split_prepped.jpg`):

| What | Samples | Result |
|---|---|---|
| The bank's top against what was authored | 1,335 | all within 0.02 m (largest 0.000) |
| Ground against the southbound road | 2,439 | none within 5 mm of the surface or over it (closest 0.016 m under) |
| Ground against the northbound road | 2,439 | none (closest 0.018 m under) |
| Ground against the forks' pavement | 340 | none (closest 0.019 m under) |
| Ground behind the east walk, 0.5 to 3.3 m past the edge | 170 rows | 0.02 m under the road's edge height on every row |
| The east walk's lip against the ground beside it | 170 rows | 0.157 m under the ground on every row (none in the air) |
| The bank's two curb tops over their road edges | 89 rows each | 0.18 m on every row |
| The two College islands that stay | 22 rows | grass 0.02 m under the road: the known defect (ledger 0055), not touched |

**The east lamps** rise with the walk in the same step: 70 parts of `LIGHTPOST_3` / `_4` and 10 of `LIGHTS_0`, up to
5.52 m. `data/lights.local.json` still has them at the old heights: step 4d.

**The median plants** (`college_plants_data.py`, report only so far, `college_plants.report.json`): 120 of the
track's 1,102 median spots stand on rows v1114-1478. **53 are dropped**: all bare on the lidar (under 0.3 m), 44 on the
forks' pavement, 7 on the southbound pavement, 2 beside a new island nose. **67 stay**: 38 with a lidar height (37 on
the bank, 1 on an island that stays) and 29 bare ones (28 on the bank, 1 on an island). Of Kevin's 33 tall plants
(10 m and over), 14 stand on these rows, **all 14 on the bank; none lands on pavement, so there is nothing to list**.
The kept bank plants' feet go 0.14 to 3.72 m up, onto the bank's top. **Nothing new is planted**: the lidar's plant
tops (`lm_shrub.tops.npz`) are on the G10, not on this machine. A dropped spot leaves both files
(`scatter_positions.json`, `median_heights.lidar.json`) so they stay in step, and every spot that stays gets `_key` =
its old index, which `tools/make_treefx.py` uses in place of the index, so no other median plant changes its model,
size or angle.

**The barrier at the top of the bank: cannot be told from here.** The aerial on this machine is 0.6 m a pixel and the
lidar here is the bare-ground grid; a 0.3 m beam shows in neither. The G10's lidar returns could show it (a line of
returns 0.5 to 1 m over the ground along the northbound road's inner edge, rows v1176-1440). Until that is read the
rail stays `[invented]`.

Still open in step 4: 4d the data step (the plants written, `lights.local.json`, the released zone and the config:
the chicane out, the corridor on the piece at its real width, the fork closures and probes), 4e the chain's author and
race steps in the workshop.

## Step 4d and 4e done: the data, the rail out, the bank's plants, the chain's author phase (2026-11-23)

Scratch only (`D:/k10-scratch/lm_r2_college/ws5`: the branch's 0.20.4 config and data, the split written into it). Not
in the chain yet, not built, not installed.

**The race declaration** (`college_race_config.py`): Speedway (`race_cw`) on the lap `college`, Reverse on the
mainline; the chicane gone; `race.corridor.whole` two stretches (`[4454, 777]` and the two roads `[1171, 1445]`,
`tools/barrier_bands.py` taught to take several); the College closure run cut in two, `[777, 1171]` and
`[1445, 1506]`, so the closure runs through each fork to the point where the roads part. `tools/barrier_bands.py`
exits 0: plan radius at least 24.1 m (Reverse) and 22.4 m (Speedway); all four planned no-route fills pass with no
leak and no door.

**The rail is out.** The G10 read the 2024 lidar along both inner edges, rows v1176-1440
(`college_bank_rail.g10.json`): the northbound edge has 0 rail-like bins of 53 and 336 returns in the 0.5-1.2 m band,
0.43 a metre (a W-beam would give about 45 a bin); the southbound edge, the control, 0 of 53 and 0.68 a metre.
No rail stands there, so step 3 authors none (`college_middle_blend.py`: GUARDRAIL 1,300 faces of the old island's
beam removed, 0 added; the invented `RAIL_SET_M`, `POST_BURY_M`, `RAIL_ROWS_IN` are gone, and so is the invented
shrub rule). One thing is not identified: a short flat object about 0.65 m tall, 0.6 to 1.0 m behind the northbound
edge at v1186-1195 (the tops file's two `solid` tops, v1189 and v1190). Nothing is built there.

**The bank's plants** (`college_plants_data.py`; lists in `college_plants.report.json`):

| | count |
|---|---|
| Measured tops on the bank (`college_bank_tops.g10.json`) | 465 |
| Planted, each at its own height and crown | **396**: 263 trees, 133 shrubs |
| It is a kept median spot (within 2 m): one of Kevin's 14 tall | 21 tops, on 13 of the 14 spots |
| It is a kept median spot: one of the other measured spots | 21 tops, on 12 of the 22 spots |
| A tree the planner already stands within its crown radius | 0 (6,316 planner trees compared; none stands on the bank) |
| Not on the bank's grass top as built: listed, not moved, not planted | 25: 9 on the northbound pavement, 6 on the southbound, 10 on the curb ring (15 of them trees) |
| Not a plant (the job's own `solid` flag) | 2 (the object above) |

- Shrub or tree is split at **4.0 m, `[invented]`**: the lm-shrub tool's own fallback. Its summary has no measured
  split (`antimode_natural` null: the 2024 lidar shows no shrub/tree valley at Lake Murray); file and md5 are in the
  config entry's `_split_doc`. The split lives in the config entry, not in `tools/make_treefx.py`.
- A shrub takes the median's bush mix (78 Bush, 55 Sage), a tree Lake Murray's `trees` mix (78 pepper, 55 oak, 43 + 35
  sycamore, 41 gum, 11 Aleppo pine): the lidar cannot tell species. Heights 0.26 to 34.7 m, median 10.2 m.
- 11 kept median spots have no top within 2 m: one of Kevin's 14 (spot 191 at v1250, 16.4 m, nearest top 3.25 m) and
  10 of the others. They stay as they are.
- **The exclusion list is 82 spots** (`college_plants.median_spots.json`): the 53 on pavement, the 28 bare spots on
  the bank (the Mac, once the bank had measured plants), and **one measured spot, 208 at v1410 (7.0 m)**. It stands
  on the bank's curb ring, 0.13 m from the southbound road's inner edge, and `tools/verify_race.py` check G refused
  it: its trunk reached 0.03 m into the race curb strip. Its own measured top (266775, 9.3 m, 1.44 m away on the
  grass) is planted in its place. One of Kevin's tall plants would never be dropped this way: it would be listed.
  36 kept bank spots get their foot on the bank's top.
- How they are planted: `tools/make_treefx.py` `scenery.treefx.lidar_plants` (opt-in, tested): a declared list, each
  plant at its own height and crown, its model and angle hashed on its own key, emitted after every other line.
  No measured file is rewritten. The planner on the scratch workshop: 21,484 plants (was 21,117).

**Step 4e, the chain's author phase on the scratch workshop, in the chain's order with the College step first:**

| Step | Result |
|---|---|
| College: split, middle, ground | all three self-checks pass (41,072 coverage samples; 83,646 old vertices unmoved; 10 east lamps raised) |
| `lamp_heads` | 323 back lenses |
| `walk_grade` | CURB 17,272 lips, 15,606 raised; 1,301 held by released ground, 513 under furniture, 10 by the red plan |
| `race_bands` | exit 0; planned no-route PASS for all four race layouts |
| `race_planned_gate` | PASS, 0 leak cells, for `race_cw`, `race_acw`, `north_cw`, `north_acw` |
| `layout_dummies` | 5 layout files |
| `race_author` | mainline 28 objects, lap `college` and lap `north` authored; 0 inside-out spans |
| `signs` + `tools/verify_signs.py` | 29 posts, 4 layout plates, PASS (after the fix below) |
| `race_verify` | OK on the mainline, on lap `college` and on lap `north`; nearest plant to a race strip 0.074 m clear |

**One red check on the way, fixed in the rule, not loosened.** With the Speedway on its own lap, the sign rule gave it
no layout plate at the College/Navajo and Navajo/Jackson corners (M3, M4): a layout on a lap "never gets" a mainline
corner's plate, a rule written for the north lap, which turns off before both. `tools/verify_signs.py` (l) failed for
both corners. The College lap IS the mainline there, so the rule now asks the lap:
`scripts/geometry/race_lap.mainline_approach` says a lap drives a mainline corner where it walks the mainline for 20
vertices `[invented]` either side of the apex, one way. The College lap does at all five mainline corners; the north
lap at neither M3 nor M4 (it leaves the mainline 3 and 2 vertices short of them), as before. `tools/place_signs.py`
places by it and `tools/verify_signs.py` check (m) holds a lap layout to it. Tested.

**Noted, not a failure:** the race author reports the built deck up to 0.294 m off the data height at the strip, at
v1456-1459 (the north fork). The strips are seated on the built deck by ray, so they sit right; the data's edge
height assumes a level row and the fork's rows are tilted.

**Not covered by 4e:** everything after the author phase (the prep in the chain, the export, drive test, the built
no-route, the kn5 checks). That is the rehearsal, through the Mac's queue. Before it: the College step wired into
`ship.json` as the first author step, the data step before it, the config edits written into airoso's own
`track.config.json`, `college_bank_plants.json` synced into the workshop, and the metre-keyed entries moved 1.9 m.
(Done the same day, next section. The metre-keyed entries turned out not to move: see there.)

## Wired into the chain (2026-11-23, on main 04e0a9b4 = Lake Murray 0.20.4)

**The step.** `tools/ship_track.sh` `author_college_split`, first in Lake Murray's author phase (`ship.json`), opt-in by
`route.college_split`. It runs `college_split_data.py <project> --chain`, then `college_split_blend.py`,
`college_middle_blend.py` and `college_ground_blend.py` on the project's `loop.blend`.

**The data step's chain mode** differs from `--write` in three ways. What it computes from the project must BE the
committed `college_split.data.json` (the scene scripts read that file), or it stops. It does not write the config: the
project's `race.laps.college` must already be this lap. And a project whose data already carries the split is verified
and left as it is, because the built line it would need is gone from it.

**Config and data in the repo.** `college_race_config.py --repo --write` wrote every College edit into airoso's own
`track.config.json` (and keeps the file's hand-compacted lines). The seven data files the data step writes are in
`tracks/san-diego-lake-murray/data/` as the split has them, taken from a workshop seeded from the repo and split by
the chain's own step. So a fresh workshop seeds split data and the 0.20.4 blend: the data step verifies, the three
scene steps apply.

**Proved on a workshop seeded the way the chain seeds one** (`D:/k10-scratch/lm_r2_college/ws6`: ship.json's
required, optional, assets and 93 seed files from the merged repo, the 0.20.4 blend), the chain's own commands in the
chain's order:

| Step | Result on the 0.20.4 seed |
|---|---|
| `college_split`: data `--chain` | what it computed is the committed file; the seven data files written |
| `college_split`: split, middle, ground | the same self-check numbers as on the 0.20.2 scene |
| `lamp_heads` | 323 back lenses |
| `walk_grade` | CURB 17,264 lips: 15,174 already at grade (0.20.4's), 272 raised |
| `race_bands`, `race_planned_gate` | exit 0; planned no-route PASS for all four race layouts |
| `layout_dummies`, `race_author` | 5 layout files; mainline, lap `college`, lap `north` authored |
| `signs` + verify | 29 posts, 4 layout plates, PASS |
| `race_verify` | OK on the mainline and both laps |
| **the College commands a second time** | each says the scene already carries it; `loop.blend` and the seven data files are byte for byte the same |

**The metre-keyed config entries do not move.** Step 1 listed `road_datum.decks[]` and `profiles[]` for a 1.9 m
shift. They are stations on the PRE-MEDIAN raw centre line (`tools/deck_datum.py`, a draft step), which the split does
not touch. What does move is in the data: the mainline is 1.929 m longer through the split, and the prep finds a
released zone by its station, so the two mainline zones declared by vertex past the split (`lmb_i8_span`,
`lmb_alvarado_creek`) get their stations re-read from their vertices (13,323.4 -> 13,325.4 m and so on). A zone keyed
by station only that reached past the split's start would stop the data step; there is none.

**Tests.** About 26 tests pinned numbers measured on the one-road College while reading the live config, and some
the live data. `tests/sd_v0180.one_road_college` puts the declaration back as main 04e0a9b4 had it (the adapter
returns main's config exactly); the spawn and swept-mouth tests read five data files frozen as 0.20.4 has them
(`tests/fixtures/lake_murray_v0204`). The chain tests name the new lap and the new author order.

## The medians: every island's grass top in its own object (2026-11-23; the Mac: option (a))

**Releasing the ground cannot do it.** Read off the prep's own code (engine-july `scripts/ac/build_kn5_loop.py`,
`_conform_and_reseat`): the pin comes first and has no exception, every 1GRASS vertex with pavement above or below is
set to the deck less 0.02 m; the released check is only in the other branch (no pavement there); a zone's band starts
at the pavement edge and runs outward; and the anti-poke pass clamps any grass over the lowest road or kerb sheet. So
the one-island release test was not run: it would have reproduced today's result. The prep of record is not changed.

**What is done instead.** `tools/author_median_tops_blend.py` (the chain's author step `median_tops`, second, after
`college_split`; opt-in `route.median_tops`): every loose strip of TERRAIN that stands 0.185 m over a road surface on
every vertex is a median's deck (the median tool's own, found by what it is). It is moved, face for face, into the
object `1LAWN_median`, wound up. Nothing else in TERRAIN moves. A loose strip with no road under it (College's bank
top) is ground and stays.

**Why that name.** In AC a mesh's physical surface IS its name: the digits, then a surfaces.ini KEY. The same name
picks the mesh's material row in the engine's table. The prep takes as ground any object named `1GRASS...`, so the
top cannot keep the GRASS key. The engine's table has one other physical turf row, `1LAWN` (the same two grass
textures Lake Murray's ground wears through its override); a new prefix would have no row and render black, and
adding a row means changing the engine copy. So the top's own key is LAWN, and `lawn_as_grass: true` makes
`scripts/ac/track_folder.py` write this track's LAWN block from the GRASS block's own values (friction 0.60,
damping 0.1, dirt, the grass sound), so a car on an island is on grass, exactly. Lake Murray's road model has no
other LAWN mesh.

**What reads grass against pavement, read before building:**

| Check | What it keys on | The top |
|---|---|---|
| the prep's pin and anti-poke | objects named `1GRASS...` | not touched: it is not ground to the prep |
| the prep's face-up flip | `1ROAD`, `1GRASS`, `1KERB`, paint | not flipped: the tool winds the top up itself and checks it |
| `scripts/ac/verify_kn5.py` check 6 (terrain poke), `audit_mesh` B | vertices of `1GRASS...` over a road or kerb | not judged: it is not 1GRASS |
| `scripts/ac/verify_kn5.py` check 2 (face up) | `1ROAD / 1GRASS / 1KERB / 1RUNOFF / 1LAWN` | judged |
| `scripts/geometry/drive_test.py` `soft_top_in_lane` | `1GRASS` or `1LAWN` on top under a wheel path | judged: a top in a driven lane fails |
| the exporter's physical set, GrassFX's grass meshes | include `1LAWN` | physical; gets the 3D grass the ground gets |
| TreeFX seating (`tools/make_treefx.py`) | `1GRASS...` and the road | the top's material is added where `route.median_tops` is declared |

None refuses grass over pavement for this object; the two poke checks simply do not read it. That is recorded in
`fleet/GATES-CHANGELOG.md`.

**Measured on scratch** (`D:/k10-scratch/lm_r2_college/ws7`: the author phase's scene, the tool, then the build's own
prep from the engine copy, then `median_tops_check.py` on the prepped ground, road and top; records
`median_tops_r2_scratch.json`, `median_tops.author.scratch.json`):

| | rows |
|---|---|
| 0.20.3 as built (`median_tops_0_20_3.json`): rows sampled / grass / asphalt | 2,486 / 0 / 2,486 |
| One island first, Navajo v1540-1739: grass / asphalt on that island | 200 / 0 (every other island still asphalt) |
| All 14 islands, after the prep: rows sampled / grass / asphalt | 2,123 / **2,123** / 0 |

- 2,123, not 2,486: College's 359 rows between v1117 and v1475 are the bank now, which has no slab under it and was
  already grass; and 4 rows were never an island (next point).
- The top stands 0.141 to 0.228 m over the road after the prep on all 4,282 of its vertices (median 0.185), the same as before it: the prep does not move it, and no vertex is without road under it.
- **Mission Gorge v54-57 is not an island, and none is authored there.** The band in the data is 1.7 m wide over 4
  rows (9 m; the plan's MD12, a 12.5 m terracotta island). The median tool builds an island only from a run of 6
  rows or more (`tools/author_median_blend.py` `_segments`: its two three-row noses need them), so it built nothing
  there: the scene has no curb ring, only the two yellow lines either side. A top alone, by the tool's rule, would be
  a strip 0.1 to 0.33 m wide standing 0.185 m over the road with no curb round it. The measure first counted these 4
  rows as an island showing asphalt (that was the "2,123 of 2,127" first reported); it now counts a run under 6
  rows apart, and so does the author step's report. Owed, if the real island is wanted: a raised island there, curb
  and all, which is new geometry and not this step.
- **Mission Gorge's raised median is declared terracotta** (the plan, `data/expansion.north.json` MD11 to MD13:
  "terracotta raised median"). The median tool has always authored its top as grass, like every island, and nothing
  in the pipeline has a terracotta surface (no material row). So its 2.15 km now read grass, where 0.20.4 showed
  asphalt. Whether it should be terracotta is not decided here.
- Two rows (Princess View v204 and v210) have the top at two of their three points: the built island is narrower
  than its band in the data on one side there. They read grass by the measure's own rule.
- 14 strips, 4,282 vertices, 4,254 faces moved; before the prep the decks stand 0.142 to 0.228 m over the road's own
  triangles (median 0.185; 7 vertices more than 0.03 off). A second run changes nothing: the blend is byte for byte
  the same.
- The measure itself changed in two places, both about the island's ends: a nose row's two side points are now taken
  inside the island as built (the median tool tapers its last three rows), and an end row is measured 0.3 m inside
  the island (the row itself is the deck's edge). On 0.20.3 every point of every row was asphalt, so its count stands.
- The plants: every plant line of the plan is identical with and without `route.median_tops` (the key is read only
  where the seating list is written), so the 14 and the 22 kept measured spots keep their heights; with the key the
  seating list gains `1LAWN_median_mat`, so median plants stand on the island and not on the slab under it.

## 0.20.5's first rehearsal: red at kn5_ground_check; the split's ground made one sheet (2026-11-23)

**The red.** Lake Murray 0.20.5 (b844ad07) was rehearsed on the PC (`D:/k10-scratch/rehearse_0205`). Every gate passed
but `kn5_ground_check`, on all five layouts: "terrain has 202 double-sheet cells" (ground heights more than 12 m apart
in one 2 m cell of plan; the gate fails over 20; 0.20.4 read 0), the worst 19.4 m. The same check read
"deck-vs-mountain max +5.181" (0.20.4: +0.255; reported, not gated: the gate is the p95, +0.022). Not installed.

**Cause of the red: the east shelf ran on inside the hill.** `college_ground_blend.py` gave every row all 21 columns,
out to 19.5 m past the east edge, and past the column where the shelf went under the old ground its height was
`min(the falling fill, the old ground less 0.30)`. This file said "then 0.3 m under it" (step 4a to 4c, point 2); the
code did not do that. East of College the hill climbs (the cut) while the fill falls 1 in 2, so the outer columns lay
up to 19.4 m down inside the hill: a second sheet of ground under the first. All 202 cells lie along those columns
(every cell listed with the check's own reader, `scratch/ground_look.py`: its lowest and its highest vertex both
ground, no road within 5 m; record `ground_look.0_20_5_rehearsal.json`).

**Cause of the 5.18 m: old ground left as walls under the higher road's edges.** 37 of the check's 58 road samples
over 0.05 m were at the split, every one on a road's own edge vertex: the northbound road's inner edge (13, to
5.18 m), its east edge (9, to 4.49 m), the southbound road's inner edge (15, to 0.66 m). At an edge vertex the check's
triangle test misses the surface that meets the edge (the shelf, the curb) and reads the old ground under it: a
triangle from ground the prep pins under the road down to old ground left at the old slab's height just outside it.
(The prep pins ground under 1ROAD only, not under a walk or a curb, and leaves released ground beside the road
alone.) Hidden under the walk, the curb and the bank's top: not a hover, and nothing a driver could see; but it was a
second sheet too.

**Why the scratch pass did not see it.** It ran the prep and measured the medians. It never ran the chain's
`kn5_ground_check`, nor the prep's sub-steps after `build_kn5_loop`. It does now (below). The Mac's rule from here:
every College change goes through that run before it is pushed.

**The fix, all in `college_ground_blend.py`** (no gate, no threshold, no line of the prep changed):

1. **The shelf ends where it goes under the old ground** (`college_shelf.py`, pure, tested): past the column where a
   row goes under, it lies 0.30 m under the old ground and no deeper; a row ends at the furthest such column of
   itself and the rows either side of it, so every face between two rows reaches both rows' own columns and nothing
   runs on inside the hill. 2,717 vertices and 2,354 faces where it had 7,287 and 6,920; rows end
   4.5 to 8.5 m past the edge; at most 1.81 m under the old ground (the one column where it
   goes under, at the fill's own height where the hill steps up past it).
2. **Old ground that lies wholly under one of the step's own surfaces is taken out of TERRAIN**: 15,668 faces
   under the bank's top, 16,674 under the shelf where it is in the open, 13,879 vertices. A face goes
   when its three corners lie 0.10 m or more under the surface and its edges' middles and its own middle are under
   it too. For that the old ground is cut to 1.5 m edges under the shelf as well as under the roads and the bank
   (54,755 edges; 47,628 before).
3. **What is left of it at a seam sits just under the surface over it.** Under the shelf: 0.05 m under it
   (2,628 vertices, raised by up to 5.87 m). Beside the higher road: 0.10 m under that road's inner edge,
   or under the bank's top where that is lower (2,410 vertices, raised 0.79 to 6.97 m). Beside the
   lower road: 0.10 m under its inner edge, up or down (2,331 vertices, -0.47 to +1.53 m; before, only
   down). Between the two it is pushed down as before. Nine vertices at the shelf's two ends keep an uncut edge
   and stay as they were (0.11 to 0.19 m under the shelf).
4. **The ground under the split's own roads is set where the prep will pin it**: the road's surface less 0.02 m
   (34,952 vertices, by up to 7.05 m). Found on the second scratch run. The prep splits every ground edge
   near the road that is longer than 4.5 m in space BEFORE it pins. An edge from old ground still at the old slab's
   height under the road to a seam vertex raised beside it stood on end, was split, and its middle, where it fell
   outside the road, stayed half-way down: the road's east edge read 1.16 m and 1.07 m over the ground on rows v1306
   and v1320. With the ground under the roads already in place there is no such edge.
5. **The step checks itself with the gate's lens and number.** No 2 m cell of ground near the split may hold heights
   more than 12 m apart that it did not before (0 before, 0 after); exit 1 and nothing
   saved otherwise.

**The scratch run** (`scratch/make_ws.py`, `scratch/run_full.ps1`, `scratch/run_gates.ps1`: a workshop seeded as the
chain seeds one, then the chain's own commands in its order): the author phase; `build_kn5_loop`, `thin_terrain`,
`freeway_i8` (not enabled), `rock_faces`, `red_repairs`, the walk's `--seat`; the split; `export_road`;
`kn5_ground_check`; then the street set and the Speedway's (race_cw, lap college: the layout on the northbound
road): kn5s, gate OBJs, `drive_test`, `audit_mesh`, `no_route`. The control first: the medians test's unfixed scene,
taken through the split, the export and the check, reproduces the red (the same four worst cells, 19.4 m, max
+5.181; 555 cells there, that scene not being thinned).

| | 0.20.4's rehearsal | 0.20.5's rehearsal (b844ad07) | fixed, on scratch |
|---|---|---|---|
| double-sheet cells (gate: over 20 fails) | 0 | **202** | **0** |
| deck-vs-mountain max (reported) | +0.255 | +5.181 | +0.313 |
| road samples over 0.05 m | 24 of 10,785 | 58 of 10,900 | 43 of 10,900 |
| of those at the split | | 37, to 5.18 m | 22, to 0.094 m |
| road-over-ground p95 (gate 0.1 m) | +0.022 | +0.022 | +0.022 |
| terrain pokes, verify_kn5 check 6 alone (gate: over 20) | | 3 | 3 |
| street `drive_test` | PASS | PASS: 11 drops, 44 far ledges, severe 0 | PASS: 10 drops, 44 far ledges, severe 0 |
| street `audit_mesh` | CLEAN | CLEAN | CLEAN |
| race_cw `drive_test` | | PASS: severe 7, 0 drops, 144 far ledges | PASS: severe 7, 0 drops, 142 far ledges |
| race_cw `audit_mesh` | | CLEAN | CLEAN |
| race_cw `no_route`, built | | PASS: leak 0, reached 138.2 k m2 | PASS: leak 0, reached 138.2 k m2 |
| ground vertices in the road kn5 | | 444,336 | 443,435 |

- **What is left of the road-over-ground reading.** The worst, +0.313 m, is not at College: kn5 (-558.42, 881.61), a junction of the north network, and 0.20.4's own road kn5 holds the same three triangles there (ground 41.783, walk 41.813, road 42.126). The check takes every seventh road vertex and College's new road moved which ones it takes; 0.20.4's worst (+0.255) is the road vertex 3 m from this one. At the split 22 samples are over 0.05 m, the largest 0.094 m, every one on a road's own edge vertex (the northbound road's east edge 3, to 0.060 m; its inner edge 7, to 0.094 m; the southbound road's inner edge 12, to 0.088 m): the ground at a seam stands 0.05 to 0.10 m under the surface over it (point 3), where the prep holds ground 0.02 m under a road.
- **The one street drop that went** (11 to 10): station 4050.3, 6.5 m east of the line, 0.45 m, a gated one. It was
  on the bank just past the southbound road's inner curb, where the old ground lay 0.47 m under that road's edge; it
  is 0.10 m under it now (point 3).
- **Two of the Speedway's far ledges went** (144 to 142): (4051.1, +5.0, 5.05 m) and (4202.9, +5.0, 1.09 m), both off
  the northbound road's inner edge: the wall of old ground under that curb.
- The prep's sub-steps read as in the rehearsal: `thin_terrain` 1,021,079 to 540,064 vertices (the rehearsal 1,032,547 to 540,949);
  `rock_faces` 9,805 faces (9,804); `red_repairs` 396 ground vertices at 2 places, worst 0.172 m (the same);
  the walk's seat 3,202 lips lowered (3,203). The author phase reads as before: `walk_grade` 272 lips raised and
  15,174 at grade, 29 sign posts and 4 layout plates, `verify_race` OK on the mainline and both laps.
- **Not run on scratch**: race_acw's and the north layouts' gates, the whole of `verify_kn5`, the AI lines, TreeFX,
  the track folder. Those are the rehearsal's.


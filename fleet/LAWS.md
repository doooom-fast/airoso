# The laws

Every one of these was paid for by a build that shipped broken. They were restated, in different
words and with different emphasis, in four separate `CLAUDE.md` files — which is how two of them
came to be enforced in one repo and quietly dropped in another. **This file is the single source.**
A project repo's `CLAUDE.md` should point here, not re-explain.

Each law carries the failure that bought it. Keep the failure in the text — a law with its reason
stripped off is a law someone will optimise away.

---

## L1 — The screenshot is a selection aid, not data

Precise geometry comes from **OpenStreetMap via Overpass**, from a **georeferenced aerial trace**
(`aerial-tracing`, for circuits with no OSM presence), or from hand-drawn **KML** *only* where the
intended route deliberately leaves the real road network. A map image tells us *which* asphalt to
grab; it is never traced for coordinates.

Corollaries, each bought separately:

- **Never invent a road.** There is no "Cowles Mountain road" — that was a stitching error that
  reached the mesh.
- **Never guess a line and name it after a real stage.** Four of the six Rally Colorado stages are
  absent from OSM. The honest options are a GPX/KML from the organiser or an aerial trace — not a
  plausible-looking line called "Cathedral".
- **A track folder must record where its geometry came from** (`source` in the config, with a
  `_note` when the provenance is non-obvious).
- **Fabricated geometry is a defect, not a status.** `high-plains` and `second-creek` still carry
  compressed lat/lon traced off the old unified map. They are marked `FABRICATED` in the registry
  and must be re-sourced to real location + real aerial + real 3DEP.

## L2 — The whole pipeline is reproducible from `track.config.json`

No hardcoded coordinates, widths, or rotations in scripts — read them from config, and write
derived values (`true_north_rotation_deg`) back to it. A clean checkout + the config + the source
inputs must rebuild the track end to end.

## L3 — Roads keep their REAL elevation; the ground conforms to the road

Sample **USGS 3DEP 1 m** (US) → OpenTopography → SRTM 30 m, along the *actual road*, then
median-despike + smooth + **grade-cap by real segment distance**, so real crests survive but
nothing launches or floats. Then the terrain is built to meet the road — never the reverse.

The three specific ways this breaks, all seen:

- **Fake mountains.** A raw DEM carries real peaks that tower over a neighbourhood loop (Cowles
  ~500 m over Lake Murray). Clamp terrain to within a band of the nearest road height
  (`terrain.terrain_band_m`, 22 m in SD). *Roads keep their real elevation* — Jackson/Navajo really
  do climb to ~213 m.
- **Bridges dip.** Bare-earth DEMs contain no bridge decks, so a road crossing a freeway samples the
  trench underneath. Hold each real OSM bridge deck level between its abutments, after projection,
  before mesh.
- **Interchange aliasing.** A coarse terrain grid aliases a flat road up into an embankment (70th St
  read a 57% cliff). Sample that road's elevation directly from 3DEP at its own points, not off the
  grid.

> **Open work:** L3 governs *terrain* elevation. Road elevation should follow the **road surface**,
> not bare earth — cuts, fills, embankments and engineered grades are the road's own datum. See
> `fleet/feedback/0002-road-elevation-datum.md`.

## L3b — A terrain cell can only follow a cut it is smaller than

The ground is pinned to the **lowest** deck surface within ~0.55 of a terrain cell, deliberately:
pin each grass vertex to the deck directly above *it* and the straight triangle edge between two
vertices bridges **up through** the road wherever it cambers or sags between them — grass poking
through the pavement, which launches the car.

The price is that the deck-to-ground gap scales with **cell size × local deck slope**. Measured on
IMI (8 m road, `kn5_ground_check` gates at 5 cm):

| terrain cells | median gap | over 5 cm |
|---|---|---|
| 5.0 m (default) | +0.091 m | 73.7% |
| 2.5 m | +0.026 m | 16.1% |
| 1.25 m | +0.017 m | 0.7% |

So a track whose road is narrower than its terrain triangles cannot be made flush by better
clamping — the triangle spans the carriageway no matter how well its corners are pinned. **Declare
`terrain_cell_m` finer than the road** on any track where the gap gates. It costs vertices
(`terrain_vertex_budget`), and the right value differs by kind: a 6.5 m gravel stage needs finer
cells than a 12 m circuit; a flat street loop is already fine at the default.

## L4 — Conform passes never cross layers

Any pass that seats, clamps, grades or drapes something "to the nearby surface" — grass clamp,
embankment grading, shoulder sink, barrier and prop seating — **must reject reference points more
than a layer gap from its own height** (~20 m generally; ~4 m for a shoulder against its own deck).

On stacked switchbacks and canyon shelves, XZ-proximity alone grabs the *wrong leg*. That single
omission, present in four passes at once, shipped the "rainbow road" build: road, shoulder and
ground on three different layers with fences in the sky.

## L5 — Gate the built artifact, never a reconstruction

An audit that validates props against the same data that placed them is structurally blind. The
gates run in this order and each looks at the real thing:

| Gate | Runs on | Catches |
|---|---|---|
| `drive_test` | built `track.obj` | what a car feels: ground through the road, things in the corridor, steps/kinks at speed |
| `audit_mesh` | built `track.obj` | supports in the road, terrain poke-through, junctions crossing their own road, wall/curb cruft |
| `verify_kn5` | the exported **kn5** | dup meshes, drivable faces pointing down, the 65 k vert cap, spawns off-road |
| `kn5_ground_check` | the shipped **kn5** vs the audited OBJs | assembly bugs — dropped, displaced or stale groups |

All four abort the build. A repo that skips one is shipping past a check that already exists and is
already known to catch real defects.

## L6 — Units and axes

- **Metres**, everywhere in the geometry/Blender/AC pipeline.
- Local frame is **`x = east, y = up, z = north`** (AC/kn5 is Y-up). Convert once, at the projection
  boundary, and stay consistent after.
- The Blender importer remaps to **Z-up** as `(x, z, y)`. **That remap is a reflection** — it
  inverts face winding. Drivable faces end up pointing down, and the car falls through the world.
  Fix it deterministically by reversing only the faces whose `normal.z < 0`. **Never**
  `recalc_face_normals` — it guesses, and it guesses differently on watertight vs open geometry.
- **True north** is resolved and written back so computed sun shadows align with the real world.

## L7 — What AC will refuse, crash on, or render black

- **Surface prefixes.** `1ROAD_*` drivable (keyed to `surfaces.ini`), `1KERB_*` kerbs, `1WALL_*`
  barriers, no numeric prefix = visual-only, no physics.
- **Required dummies.** `AC_START_0..N`, `AC_PIT_0..N`, `AC_TIME_0_L`/`_R` (+ one pair per sector),
  `AC_HOTLAP_START_0`.
- **65,535 verts per mesh is a hard cap** and the over-cap guard is fatal. Clustered foliage must be
  pre-chunked by balanced median bisection — an equal-width band split once left a `PALMFROND` band
  at 82,797 verts.
- **Every material needs a texture.** A texture-less kn5 material renders **black** in-engine. Solid
  colour paint gets a solid-colour PNG, not a bare colour value.
- **Non-power-of-two textures can hard-crash the GPU** (whole-PC freeze) on load — the mipmap/DXT
  upload hangs the driver. `build.sh` pre-flights this; keep that pre-flight.
- **A TreeFX species with no `.bin` is dropped, never referenced.** Resolve every species at build
  time, drop the unresolvable ones, and skip `[TREES]` entirely if none resolve.

## L8 — Layouts share one kn5; physics does not

Route variants are **AC configuration over a single mesh** — never rebuild the mesh per layout.

The one exception, and the reason it is an exception: **`surfaces.ini` is applied per track, not per
layout.** So a surface-physics fork (Rally Colorado's gravel vs tarmac) must be **two installable
tracks**, each with its own slug, sharing the route by pointing at the same roads. A layout toggle
makes the friction difference fragile.

## L9 — Curbs and kerbs are tight to the road edge, at deck height

`1KERB` hugs the `1ROAD` edge at the deck's elevation. No floating lips, no gaps, no hovering at an
angle. Verify with lateral cross-sections of the **built** `track.obj`, not by eye.

## L10 — Banking is researched, not invented

Real banking, per track, looked up: PPIR oval is 10° in all four turns; High Plains runs 1.5–4% with
a deliberately off-camber Turn 1. A road course gets **none**. Public streets are not superelevated
— they get real elevation only.

Where a corner's banking is genuinely unknown, derive it from the racing line's own curvature
(`track-grading`) — and only on purpose-built circuits.

## L11 — Point-to-point is not a lap

`loop: false` means the grid goes at the **start of the road**, `AC_TIME_0` goes at the **finish**
(the single crossing the driver makes is the one that posts a time), splits number up from 1 in
driving order, and no gate wraps past the end of the road. Get it wrong and the symptom appears
only in-game: the run simply never times.

## L12 — Show, don't assert

When operating Blender or reporting on a build, check the actual scene/mesh state before claiming
anything. When Kevin says the real world is a certain way and the data disagrees, **trust Kevin and
fix the data** — he has driven these roads.

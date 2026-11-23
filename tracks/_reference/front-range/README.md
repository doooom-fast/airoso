# The Front Range backdrop — one surveyed surface, shared

The mountains west of Denver as three tracks see them: Denver Grand Prix first, then Sand Creek and Lookout Lariat.
Decided in `tracks/denver-grand-prix/PLAN.md` §3 (D6: true distance and size; D7: one shared source). Ledger:
`fleet/feedback/0096-denver-grand-prix-and-the-front-range-backdrop.md`.

**Nothing here has been seen in the game.** The far-clip test (`tracks/denver-grand-prix/source/farclip/RESULT.md`)
drew three walls at 25, 60 and 105 km. No baked terrain has been exported to kn5, installed or driven.

## What is here

| File | What it is |
|---|---|
| `provenance.json` | The source: seven USGS 3DEP 1/3 arc-second tiles, with URL, size, sha256 and the server's date for each. 2.79 GB, **not in git**. |
| `bake.config.json` | The bake recipe (`params`) and one entry per track (`tracks`). |
| `ext_config.backdrop.ini` | The two CSP keys the backdrop's meshes need to draw past 20 km. A fragment; a track's build merges it. |
| `tools/backdrop_bake.py` | The bake: config + track + DEM directory → `<slug>_backdrop.obj` and `<slug>_backdrop.bake.json`. |
| `tools/backdrop_peak_gate.py` | The gate: reads the baked OBJ, exits 1 if a peak is off by more than 0.1°. |
| `tests/tools/test_backdrop_bake.py` | Both, on an analytic surface. |

The tiles live at `/Volumes/Sundowning/Claude/airoso-data/front-range/dem/` on Kevin's Mac. On another machine, fetch
the URLs in `provenance.json` into any directory outside git and check the sha256s. Bakes are written outside git too
(`…/airoso-data/front-range/bakes/<track>/`); an OBJ is 100 MB or more.

## What the bake does, and what it never does

- **Places every vertex at its true bearing and distance from the track's origin** (geodesic on the WGS84 ellipsoid),
  x east, y up, z north. Near the origin this is the engine's own local frame.
- **Bakes Earth curvature and standard refraction per track:** `y = elevation − origin elevation − d²(1 − 0.13) / (2 ×
  6,371 km)`, `d` from the origin. At 100 km that is 683 m. So the mesh differs per track; the source and the tool do not.
  Seen from a point of the lap away from the origin, the error is 0.009° per km of that offset.
- **Keeps only what the track's roads can see:** the union viewshed of points every 100 m along the road line, eye
  12 m over the ground, plus anything within 0.1° of being seen and two cells around it. Ground nearer a viewpoint
  than 2 km hides nothing (the track rebuilds its own near ground). The far side of every ridge is dropped.
- **Cell size follows distance:** 0.001 rad of bearing, which is 60 m at 60 km (about one screen pixel); never under
  20 m; twice that along the line of sight. Where the step changes the rows are stitched, so there is no crack.
- **Bearing 180° to 335°, 2 km to 112 km** from the origin.
- **Keeps summits:** a 60 m lattice can step over a sharp summit and read it 20 m low. Where the highest DEM point
  of the ground a vertex owns (half a cell around it) is higher than all eight neighbours', the vertex is moved onto
  it: real position, real height, inside its own cell. Denver: 8,433 of 913,893 vertices.
- **Real normals:** the DEM's own slope at each vertex, not the mesh's faces.
- **Visual only:** objects `BACKDROP_FR_000…`, no digit prefix, at most 60,000 vertices each.
- **Never (LAWS L3):** no smoothing, no vertical exaggeration, no invented summit, no filled hole. A vertex's
  height is the DEM's value at the point where it stands (bilinear between its four cells) and nothing else.

## How a track references it

1. Add an entry under `tracks` in `bake.config.json`:

   ```json
   "<track-id>": {
     "slug": "<slug>",
     "origin_lon_lat": [lon, lat],
     "origin_elev_m": 1234.5,
     "road_line": "tracks/<track>/data/<its road line>.json",
     "gate": {"horizon": "tracks/…/horizon.3dep13.wgs84.json", "site": "<the study's site name>",
              "start_line_lon_lat": [lon, lat]}
   }
   ```

   `origin_lon_lat` and `origin_elev_m` are the track's own (`track.config.json` `origin`, `data/local.meta.json`
   `elev0`): the same numbers its roads were projected with, or the mountains will not line up with the streets.
   `road_line` is every road a driver can be on, as `{"nodes": [{"lon", "lat"}]}`, GeoJSON lines or a list of
   `[lon, lat]`. A track may override any recipe value under its own `"params"`.
2. Bake and gate:

   ```bash
   python tools/backdrop_bake.py tracks/_reference/front-range/bake.config.json <track-id> --dem <tiles dir> --out <dir outside git>
   python tools/backdrop_peak_gate.py <out>/<slug>_backdrop.obj tracks/_reference/front-range/bake.config.json <track-id> --report <out>/<slug>_backdrop.peak_gate.json
   ```

   The gate's reference must be a horizon study from that track's start line
   (`tracks/denver-grand-prix/source/horizon/horizon_3dep.py --wgs84`; add the site to `horizon_study.py`'s `SITES`).
3. The track's kn5 build turns the OBJ into `<slug>_backdrop.kn5`, lists it in every layout's `models_*.ini`, and
   merges `ext_config.backdrop.ini` into the track's `extension/ext_config.ini`. **Not built yet**: that step is the
   engine's and no track does it today.
4. Bake again whenever the track's origin, its origin elevation or its road line changes.

## Tracks

| Track | State |
|---|---|
| `denver-grand-prix` | Baked and gated on 2026-11-23 with a **provisional origin** (the start line, Colfax at Sherman; the track has no `track.config.json` yet). Numbers: ledger 0096 and `tracks/denver-grand-prix/data/backdrop.*.json`. |
| Sand Creek | Not baked. Needs its origin and road line here, and note the study's finding that Pikes Peak is in its mesh (DOSSIER §6). |
| Lookout Lariat | Not baked. It is inside the mountains: `near_m`, the arc and the 2 km blocker rule were chosen for a city on the plains and need their own look. |

## Not here

The haze and fog look of the material (PLAN §3a: the next PC test). The Denver skyline towers (the second shared
layer). The pulled-in fallback of PLAN §3b. Colour by elevation, snow line. The kn5 export.

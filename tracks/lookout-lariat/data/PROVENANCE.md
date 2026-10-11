# `data/`: the V3 Lariat's regenerated route data

**Written 2026-10-11, V3-PLAN P0 steps 7 and 8 (ledger 0048).** Nothing here is geometry: no
elevation, no mesh, no kn5. `source-july/` holds the restored July reference files and has its own
`PROVENANCE.md`; nothing in it is read by a stage.

## Frames

| Frame | What it is | Used by |
|---|---|---|
| **WGS84 lon/lat** | GeoJSON's own frame (RFC 7946), longitude first | `centerline.geojson`, `osm.cache.json` |
| **V3 loop frame** | local ENU metres about the centreline centroid, x = east, y = up, z = north; `mirror_x` false, true north 0 (`scripts/geometry/projection.py`) | `centerline.local.json` (P2, not written yet) and every vertex/station in `track.config.json` |

- **Geojson v0 vs local v0.** The gps stage rotates the ring so v0 is the raw OSM node nearest
  `route.start_at` (the pylons, 2.78 m away). `projection.py` re-applies `start_at` with its own
  metric and picks geojson v8300, 2.15 m before v0 along the lap. So **local index = geojson
  index + 1** (mod 8,301), and local stations = geojson stations + 2.15 m. Every vertex the config
  declares (layout starts, sectors, race boxes) is in the local index space. This was checked by running
  `projection.py` on a scratch copy with zeroed elevation (plan only).
- **Stations** in `oneway_check.json` are metres from geojson v0, measured in the plan frame.

## Files

| File | Written by | Frame | Bytes | md5 |
|---|---|---|---:|---|
| `osm.cache.json` | `python -m scripts.gps.centerline` (live fetch, TLS verified) | lon/lat | 223,955 | `ea0af589b09dca74afdee541c5a6ea61` |
| `centerline.geojson` | the same stage, re-run offline from the cache above | lon/lat | 390,779 | `28dcc7b644510179fe366eb56d3911e5` |
| `centerline_preview.svg` | the same stage | screen (north up) | 105,919 | `2894e729d4e78879251efa5de9a9b34b` |
| `oneway_check.json` | `python tools/route_oneway_check.py <project>` | report (see its `frame` key) | 60,972 | `8338197ce598a4237db13d6d35eb8a26` |
| `route_map.png` | session-scratch drawing script (Pillow), from the files above | plan, north up | 1,932,217 | `31a0c8f51fc16908c14c4223d68b907b` |
| `route_map_switchbacks.png` | the same script | plan, north up | 762,974 | `c1b6ad9782ac62ffba95e5a732676136` |

### `osm.cache.json`: the route stage's Overpass snapshot

- **The query.** It is `route.roads` + `route.bbox` from `track.config.json`, including A1's ramp ids
  `id:484287799,1351773584,533503588,533503210,1283267904`.
- **The snapshot.**
  - Query fingerprint `93e1c28d8828c2f2`.
  - Fetched 2026-10-11T19:29:58Z from overpass-api.de, with TLS verified.
  - OSM data timestamp 2026-10-11T19:28:01Z.
  - 197 ways, and no `remark` (Overpass error) field.
  - sha256 `a2b0d88679dd73a97c22b6d14f3cba7e37b34e43c3b6e91205ef31f833c3e26a`.
- **What it replaced.** The earlier snapshot of the July query, fingerprint `bee91bb364ab65e1`, 196
  ways, fetched 2026-10-11T19:15:07Z. A copy is kept in session scratch only.
- **`route.exclude_ids` is applied when the stage parses this file**, not in the query. So the
  snapshot still contains the excluded ways 42005706 and 533500102, and the one-way check uses them.
- **To refresh:** delete the file. Any change to `route.roads` or `route.bbox` changes the
  fingerprint, which also forces a live re-fetch.

### `centerline.geojson`: the V3 centreline

- **The lap.**
  - 24,890.8 m along the great circle, 8,302 points, closed (the closing vertex equals v0 exactly).
  - 24,905.7 m in the plan frame.
  - All six corner gaps are 0.0 m.
- **How it was made.** `config.default_width_m` is 6.7, and `exclude_ids` is [42005706, 533500102],
  both recorded in the feature's properties.
- **It reproduces.** Re-running the stage with networking blocked gives the same bytes from the
  cache.
- **Against the July line** (`source-july/centerline.geojson`):
  - it is identical to within 0.036 m up to exit 259;
  - it differs only at the three A1 places: exit 259 (st 16,595–16,690), the ramp end (st
    24,250–24,310) and 19th St's westbound side (st 24,316–24,369);
  - elsewhere it is within 1 m, a difference that comes from resampling;
  - it is 51 m shorter, mostly from removing the U-turn.

### `oneway_check.json`: P0 step 8's report

| Layout | Verdict | Runs against `oneway=yes` |
|---|---|---|
| `street_full` | **PASS** | none |
| `street_reverse` | **PASS** | 4,486.5 m in 33 runs, all on the four declared D2 stretches |
| `race_acw` | skipped | closed road, not checked |
| `race_cw` | skipped | closed road, not checked |

The four D2 stretches are:
- `exit259`, 86.2 m;
- `colfax`, 311.6 m;
- `us6_offramp`, 4,035.1 m;
- `nineteenth`, 53.6 m.

### `route_map.png` and `route_map_switchbacks.png`: the map Kevin sees before any geometry

Drawn 2026-10-11 (V3-PLAN P0, "Kevin sees"). They are pictures of the data above, not data, and no
stage reads them.

- **What they show.**
  - The V3 lap in plan view, north up, with a scale bar.
  - Corners C0–C18 in the dossier's numbering. The vertex for each comes from the V3 line: the
    race corners use the config's box apex, and the other corners use the peak of the turn.
  - Both A1 fixes as before/after insets: the July line dashed grey, V3 solid, and the roads' own
    one-way arrows.
  - The five race-turn boxes and the two C-470 crossings. The crossing points are computed where
    the config's C-470 ways cross the line: km 19.35 on Colfax and km 21.14 on US-6.
  - Start/finish at the pylons, direction arrows for Full/race anticlockwise and Reverse/race
    clockwise, and segment labels.
- **The switchbacks image** is a crop drawn at 2× the main map's scale. It adds two 6× panels of
  the stacked hairpins, with the closest legs measured on the V3 line (C7–C10 20.5 m, C4–C6
  27.0 m).
- **Inputs, all read-only:** `centerline.geojson`, `osm.cache.json`, `../track.config.json`, and
  `source-july/centerline.geojson` + `source-july/osm.widths.cache.json` (the July line and the grey
  context roads).
- **Stations** printed on the maps are in the config's local frame (geojson station + 2.151 m).
- **Symbols are not to scale.** Line widths, markers and boxes are symbols. The grey bands in the
  6× panels are the published widths (5.48 m Tiers of Zion, 6.7 m Lariat average), not
  measurements of each hairpin.
- **The script is not in the repo.** It lives in session scratch (`lariat/map/compose.py`,
  `route_map.py`, `geo.py`). Re-running it gives the same bytes.

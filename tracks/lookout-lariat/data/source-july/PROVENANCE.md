# `data/source-july/`: the July Lariat's frame-free data, restored for reference

**Restored 2026-10-11, V3-PLAN P0 step 2 (ledger 0048).** These five files are the July build's
data that are keyed by longitude/latitude rather than by the July track frame or July stations.
They are **reference only**. No pipeline stage reads this folder. The stages read `data/<file>`
directly, and nothing here is copied there.

## Where they came from

- **Repo:** `k10-colorado`, retired, read-only history.
- **Revision:** `0a897bb^` = `cb798c2bc938382f7fc2523e6e412153451aaf53` (2026-08-09 16:48 −0600,
  "CM-visible versions bump to 0.66.3 + honest circuit tags"). This is the last revision that has
  them. The next commit, `0a897bb` (2026-08-09 19:12, "Delete all generated output"), deleted them.
- **Path:** `tracks/lookout-lariat/data/<file>`. All five were there; none lives anywhere else.
- **How:** `git -C <k10-colorado> show 0a897bb^:tracks/lookout-lariat/data/<file> > <file>`. The
  retired repo was never checked out or modified. Each restored file's `git hash-object` equals
  the blob id at that revision, so the bytes are identical.

| File | Bytes | md5 | Git blob | Last written in | Fetched |
|---|---:|---|---|---|---|
| `osm.widths.cache.json` | 1,756,404 | `b27b83b0a17679611f3bfcf1a2f48a44` | `c8bfe7bc1bd0` | `c7c4fd8` 2026-07-27 | **2026-07-27T15:03:07Z** (in file); OSM base 2026-07-02T16:51:45Z |
| `osm.ways.json` | 585,449 | `1f7e18f75af9e91920ad50a9508aaa2f` | `a2002e7f2d18` | `c7c4fd8` 2026-07-27 | derived from the cache above, same run |
| `centerline.geojson` | 391,670 | `43b9e4e9eb6ca6b8beca637015017f53` | `6b8701e90e3a` | `48f236d` 2026-07-21 | from OSM via the gps stage; first written `32deb14` 2026-07-20 |
| `corridor.elev.json` | 1,349,625 | `d15b7adf1d78378aeda64df140af817c` | `8ea64bd6cc3d` | `1178f2d` 2026-07-22 | USGS 3DEP; no date in file, committed 2026-07-22 18:52 −0600 |
| `environment.geojson` | 1,291,181 | `09f5d9e5b3cf8ff112f8293f36d5b927` | `03f17c34b315` | `32deb14` 2026-07-20 | Overpass; no date in file, committed 2026-07-20 18:50 −0600 |

## What each one is, and what it is for

**`osm.widths.cache.json`: the July Overpass snapshot.**
- Every drivable OSM way in the bbox, 2,493 ways with full tags (806 carry `oneway`), node ids and
  geometry.
- Written by `scripts/gps/widths_from_osm.py` `fetch_ways`. Query fingerprint `253170f584109f60`.
  Bbox S,W,N,E = 39.694161, −105.254801, 39.750911, −105.187713, which is the July centreline's
  extent ± 0.0015°.
- **For:** the record of what OSM said in July. A fresh fetch (P0 step 3) can be diffed against it
  to see what OSM changed since.
- The A1 ways are all in it, so the route fix and the one-way check (P0 step 8) can be prototyped
  offline. Those ways are 533503210, 1283267904 and 119006778, plus the replaced 533503214 and
  42005706.
- **Not** the gps stage's cache: it sits outside `data/`, so the stage never sees it. Don't copy it
  there. The fingerprint is a hash of the bbox query, and the bbox is the centreline's extent
  ± 0.0015°. A V3 line with the same extent as July's would match it and silently reuse July's
  OSM. P0 step 3 stores its own payload, with its own date.

**`osm.ways.json`: the street map the CM preview drew.**
- 2,358 ways, with highway class + lon/lat geometry only.
- It is the cache above after the identity lock, which drops undeclared motorway/trunk ways:
  195 freeway-class ways in the cache, 60 kept.
- Written by `widths_from_osm.py:356` and read by `scripts/ac/track_folder.py` for the Content
  Manager preview.
- **For:** reference. V3 regenerates it with the new route.

**`centerline.geojson`: the July lap, in lon/lat.**
- One closed LineString of 8,319 points, `length_m` 24,941.8. It starts and ends at
  (−105.228526, 39.742385), the 19th St gates. It also carries per-point `widths_m` and the July
  `roads` list.
- **It carries both July route defects** that A1 fixes:
  - the ramp end via way 533503214, a ~190° U-turn and ~100 m the wrong way up a one-way;
  - exit 259 via way 42005706, 84 m against the arrows.
- **For:** comparing against the re-derived V3 centreline (P0 step 7). Away from those two places
  the two lines should agree, unless OSM changed since July (the snapshot diff will say where).
- Never an input.

**`corridor.elev.json`: July's near-road 3DEP elevation samples.**
- 3,061 stations every 6 m along the July centreline × 25 lateral offsets (−60 to +60 m at 5 m).
  Elevations run 1,775.0 to 2,297.5 m.
- Written by `scripts/elevation/heightfield.py` `fetch_corridor`.
- The points are lon/lat, so nothing depends on the July frame. The stations, though, follow the
  July line, defects included.
- **For:** a reference to check V3's fresh corridor sample against.
- **Never copy it to `data/`.** `fetch_corridor` treats it as a cache hit when `n_src` (8,319)
  equals the new centreline's point count. A V3 line that happened to have 8,319 points would
  silently reuse July's samples for a different line.

**`environment.geojson`: July's OSM environment zones.**
- 1,968 features `{cls, kind, coords}`: green poly 1,417, water line 241, **highway line 238**,
  water poly 57, wetland poly 15. Extent lon −105.384 to −105.147, lat 39.681 to 39.770.
- Written by `scripts/environment/zones.py`.
- The 238 highway lines are every motorway/trunk/link way in the box. `build_env._build_highways`
  laid a 22 m deck along each of them outside the lap's own corridor: I-70, C-470 and their ramps,
  the "wavy ribbons" of ledger 0048.
- **For:** reference only (water, green and wetland outlines when V3 lays out ground cover and
  trees).
- **Never built, and never copied to `data/environment.geojson`.** `build_env` reads that path.

## Not restored (regenerated instead)

The other 14 files at that revision stay in the retired repo's history.

**Keyed to the July frame or July stations** (the plan's list):
- `finished_centerline.json` (mirrored);
- `centerline.local.json`;
- `crossfall.json` (4,159 July stations);
- `bridge.spans.auto.json` (24,802.6 m built frame);
- `dummies.json`, `dummies_reverse.json`;
- `heightfield.npy`;
- `flat_zones.json`, `drive_test.json`, `street_labels.json`.

Reusing any of them would repeat ledger 0015 (two station frames under one key) and 0038 (the
mirror).

**Also left behind**, because they are not on the plan's restore list and each depends on the
July build:
- `centerline.elevation.json`: keyed by July station distance;
- `heightfield.meta.json`: the header of `heightfield.npy`;
- `lighting_presets.json`: carries July's true north of 180°;
- `seed_overview.png`: a preview image of the July build.

Every file V3 regenerates records its own frame.

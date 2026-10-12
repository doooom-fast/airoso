# `data/aerial/`: the Lariat's aerial measurements

**Written 2026-10-11, the V3 aerial pass (ledger 0048, dossier section 12 "aerial owed"); the
measurement was ported into the repo the same day (`tools/aerial_measure.py` + `tools/aerial/`) and
re-run from it, and the paint it traced now places the centreline (P2).** The measurements change no
geometry themselves. `paint_traces.json` is what `tools/paint_centreline.py` follows to write
`../centerline.geojson`, and what `tools/verify_centreline_paint.py` judges it against. No Blender, no
kn5.

## Files

Bytes and md5 of the text files are of their content with LF line ends, as git stores it (a Windows
checkout with `core.autocrlf` has CRLF bytes; the tools hash text with line ends normalized). The aerial
pass's own figure for `aerial_measurements.json` (163,190 bytes, `13dfaf0f...`) was of its CRLF copy;
its committed LF content hashes `cd22b9e5775be25d338286e31fc5097f`.

| File | What it is | Bytes | md5 |
|---|---|---:|---|
| `aerial_measurements.json` | sources, the 49 windows, per-corner radius + method + confidence (C1-C13), widths (34 stations, 28 usable, + hairpin legs + apexes + junction arms), edge observations, the two C-470 crossings, OSM registration. Written by `tools/aerial_measure.py` | 156,158 | `d2cc238254d680206a8d8eda019759f3` |
| `aerial_spec.json` | the measurement plan the tool runs (which windows, centred where; each corner's traced stretch from the P0 fitter run; the manual seed and turn rule per corner; the width stations; the crossings) and the observations written by eye (shadows, pull-offs, barrier lines, the dossier's figures) that it carries into the JSON verbatim | 33,018 | `7c2540b4e6c0f34f9dd932945467dc60` |
| `paint_traces.json` | the traced paint of every window (49: 11 corners, 34 width stations, a few with nothing traced in tree shadow, 4 junction arms) in the engine plan frame (xz about the OSM line's centroid, the origin recorded), each point with its lap station, direction of travel and confidence (high / medium / low); per window the paint centre as one continuous `reference`, and at each hairpin its core's yellow-line and edge-line circles | 1,058,937 | `e149f86f608de7dcf24ffb7c485eaa81` |
| `paint_centreline.json` | `tools/paint_centreline.py`'s report: the paint stretches it followed, the smoothed regions, per window the worst distance from the paint (new line vs OSM), per hairpin the tightest radius vs the measured one | 20,284 | `7dacb13637f9d9172992e2024ce6a67e` |
| `paint_gate.json` | `tools/verify_centreline_paint.py` on `../centerline.geojson`: PASS on all four checks | 6,096 | `e4d444fb373b5c107a565f170b159e3d` |
| `overlays/paint_C4.png`, `paint_C9.png`, `paint_C10.png`, `paint_climb.png` | for Kevin: before (the OSM line, grey) and after (the paint centreline, yellow) over the painted edge lines, at C4, C9, C10 and the whole climb (`tools/paint_pictures.py`) | 69-816 KB | listed below |
| `overlays/C1.png` ... `C10.png`, `C12.png`, `C13.png` | per-corner overlay: imagery crop, OSM lap line and nodes (datum-shifted), traced pavement edges, edge lines and centre line, fitted circles, the result in magenta, the core wedge | 74-128 KB each | listed below |
| `overlays/X19340.png`, `X21138.png` | the two C-470 decks over the lap: traced deck edges, OSM bridge ways, the lap | 123-126 KB | listed below |

There is no `C11.png`: the bend is in deep tree shadow and nothing was measured there.

Overlay md5s: C1 `22d17edc6d40fb2b0bd20604d9c64285`, C2 `e7e08a1280024ba13625145f2952763d`,
C3 `e3c5c294c4981d70dda45046a6439717`, C4 `1ca31ae05f8b6d4c19e28a96a8419123`,
C5 `a80b6593ec4f633fba218edb05733096`, C6 `7643f17a9dd4e642789eef42b6121ff3`,
C7 `8c30b9d89a94813dc53cbd4491e43674`, C8 `77a19c5d354ff798e5ef339528fae35d`,
C9 `20d2c19393911fdafbf46f4f6112610f`, C10 `936738179b5f43ba2414d8b6abafd732`,
C12 `4dad36177ba63c6ce5e1884b583e192e`, C13 `08b0f37d0de6d990b8b217e5ed69cd67`,
X19340 `325eef3c3fb7ca2c0b3577c8f5defc40`, X21138 `baf8f0c6119317a04389216ddb2d188a`. All 14 are
byte-identical when the ported tool re-draws them.
Paint pictures: paint_C4 `c716af1e94913a2af7f5c327302c3c8e`, paint_C9 `9ba99e159a44de8281ac19fb7c5c365f`,
paint_C10 `17ca53945a23203834776446b93088fb`, paint_climb `0dab3aa764079b27ae6c934df1b65f1e` (its NAIP
window is 1.6 m per pixel, fetched once with TLS verification on).

## The imagery

- **What:** USDA NAIP, Colorado 2019, 4 bands (red, green, blue, near-infrared), 0.6 m ground
  sample distance. Three quarter-quads cover the lap's windows: `m_3910523_nw_13_060_20190919`
  (flown 2019-09-19), `m_3910515_sw_13_060_20190919` (2019-09-19) and
  `m_3910522_ne_13_060_20190913` (2019-09-13, Paradise Rd).
- **From where:** USGS The National Map, `USGSNAIPImagery` ImageServer, `exportImage`. 2019 is the
  only Colorado year this service (and its NAIP Plus sibling) carries over the lap. USDA's own NAIP
  service, which has later years, refused the connection from this machine, so no newer flight was
  used.
- **Licence:** public domain (a US federal work: USDA FSA imagery distributed by USGS). The service
  asks for the credit "USGS, USDA, The National Map: Orthoimagery".
- **What is in the repo:** only the overlay pictures above (palette PNG, public domain).
- **What is not:** the raw windows. They live in a window cache outside the repo: the aerial pass's
  `.../scratchpad/lariat2/naip/`, copied for the port to `.../scratchpad/paint/naip_cache/` (session
  scratch, `C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/`);
  the tool's default cache is `%LOCALAPPDATA%/airoso/naip` (or `$AIROSO_NAIP_CACHE`). Each window has
  a JSON beside its PNGs with the bbox, the exact request URL, the raster names and the fetch time;
  `aerial_measurements.json` repeats that list under `windows`. A missing window is fetched again: the
  service serves identical pixels (checked on C4, 2026-10-11).
- **How it was fetched:**
  - TLS verification was on (`scripts/tls.https_context`).
  - Each window was requested twice: true colour (bands 0,1,2) and colour-infrared (bands 3,0,1).
  - Both requests used EPSG:26913 (NAD83 / UTM 13N) for the bbox and the image. That is the
    quarter-quads' own projection, so the server does not reproject.
  - PNG, bilinear resampling, 0.3 m pixels (the service's pixel; the effective resolution is the
    source's 0.6 m).
- **The windows:**
  - 120 x 120 m at each corner;
  - 50 x 50 m at each width station;
  - 150 x 150 m at each C-470 crossing.

## Frames and registration

- **Imagery frame:** NAD83 / UTM 13N metres (`utm13n_nad83` in the JSON). It is the frame every
  measurement was made in.
- **OSM frame:** WGS84 lon/lat. It was put on the UTM grid with **no** datum shift, and the
  remaining offset was then measured.
  - The traced double-yellow line was compared with the raw OSM ways in `../osm.cache.json` on
    straight road. OSM chords cut hairpins, so curved road was left out.
  - 862 points in 31 windows.
- **Result:** OSM sits **1.33 m WNW** of the imagery (-1.20 m E, +0.56 m N). OSM's own scatter
  about the painted line is 0.74 m rms.
- **The whole offset is the datum, not mapping.** The NGS 14-parameter ITRF2008 -> NAD83(2011)
  transformation predicts -1.23 m E, +0.56 m N here at epoch 2019.7.
- **`lonlat_wgs84` values** in the JSON are imagery points moved by the measured offset, so they
  line up with OSM, `centerline.geojson` and `track.config.json`.
- **Not tied to the stations:** the overlays draw OSM moved into the imagery frame.

## Methods (summary; the JSON's `methods` block has the detail)

- **Hairpins C1-C10:**
  - Traced profiles find the double-yellow line, both white edge lines and both pavement edges.
  - The core is headings 20-80 % of the turn between the traced legs (the fitter's own core).
  - Rays every 0.5 deg from an iterated centre cover the core.
  - One centre with two radii is fitted to each edge pair.
  - The radius is the mean of the pavement-edge pair where that pair is clean, else the mean of the
    painted edge-line pair, else the yellow line. No hairpin's pavement-edge pair was used. Only
    C2's met the fit criteria, and it sat 2.7 m outside the painted estimates because its outer edge
    takes in an apron. Elsewhere the pavement edges run into aprons, pull-offs, gravel margins and
    tree shadow and are not circular (rms 0.4-2 m), while the painted lines are circular to
    0.1-0.2 m. Eight hairpins therefore use
    the edge-line pair and C1 the yellow line (its outer edge line shows on only a third of the
    core). The pavement-edge fits are still in the JSON for every corner.
  - C7's apex is in shadow; its radius comes from a search for the circle that best follows the
    sunlit yellow paint (low confidence).
- **Junctions C12, C13:**
  - The inside kerb return is fitted as an arc tangent to both arms' inside pavement edges.
  - The lap-centreline radius is the kerb-return radius plus the arms' inside half-width.
- **Widths:** medians over profiles every 0.5 m, as two widths:
  - **edge line to edge line:** the travelled way;
  - **pavement:** to where the surface stops matching this window's asphalt in NDVI, chroma and
    brightness. It is an upper bound: gravel and dirt can read as asphalt at 0.6 m.
- **Thresholds:** every one is [invented] for this pass and listed in `methods.thresholds_invented`.
  None is a gate.

## Limits, stated once

- An aerial cannot tell a stone guardrail from W-beam or a concrete wall. Nor can it give a
  barrier's height, the depth of a drop or a bridge's clearance. `edges` says what is visible,
  not what it is.
- The C-470 decks stand above the bare-earth surface the orthophoto was rectified to. Their
  footprints can therefore sit a few metres off in absolute position, though their widths and
  angles hold. Abutments and piers are not visible.
- One flight, mid-morning, late summer. North-facing conifer stretches (C11, upper climb
  st ~6,200-7,000, parts of C7/C9) are shadowed.

## Reproducing

    PYTHONUTF8=1 python tools/aerial_measure.py tracks/lookout-lariat --cache <window cache> [--no-fetch]

It writes `aerial_measurements.json`, the 14 measurement overlays and `paint_traces.json` here (about a
minute, pure Python + Pillow). Run on the aerial pass's own windows it reproduces the aerial pass's
JSON exactly but for two things, neither a measurement:
- `source.cache` names the window cache actually used (it named the scratch directory);
- ten width stations' `station_m` are written as integers (`2050`) where the pass wrote floats
  (`2050.0`): those stations had been re-run with float arguments.
Every overlay is byte-identical. How the pass's two versions of its corner script are kept: the pass
measured C4 and C7 with the turn taken from the traced legs and the other hairpins with the turn of the
integrated reference heading (it changed the rule after the first batch); `aerial_spec.json`'s
`turn_rule` records that per corner, so the committed numbers reproduce. The scratch scripts of the pass
(`.../lariat2/v2/`, `.../lariat2/lib/`) are superseded by the tool.

## `paint_traces.json`: the paint the centreline follows

- **One record per window** (`kind` corner, width_station or junction_arm): `yellow` (the double-yellow
  centre line), `edge_left` / `edge_right` (the white edge lines, left / right of Full travel), each a
  set of parallel arrays: `xz_m`, `lap_st_m`, `heading_deg`, `confidence`, `source` (`profile`, or
  `core_ray` for the polar rays over a hairpin's core); `reference` (the paint centre as one polyline
  every 0.5 m, `supported` where a medium+ yellow point is within 0.35 m); `core` at a hairpin.
- **Frame:** `frame.origin_lonlat` + `frame.m_per_deg` turn `xz_m` back into WGS84 lon/lat exactly;
  the imagery points were first moved by the measured OSM-minus-imagery offset (-1.20 m E, +0.56 m N),
  so they sit in the OSM / centreline frame. `lap_st_m` are stations on `../centerline.osm.geojson`.
- **Confidence** (every threshold [invented], listed in `tools/aerial/traces.py`): a point is medium when
  it belongs to a run of >= 4 consecutive profiles, lies within 0.3 m of its +-4 m neighbours, has a
  yellow prominence of at least half the window's own median, and runs along the road (<= 0.15 m
  sideways per metre); high adds a run of >= 8, prominence >= 15 and both edge lines at 2.4-5.0 m. A
  profile point inside a good core circle's sector but off it is low; a width station the measurement
  itself found unusable (W06900) contributes low points only. 5,813 yellow points are medium or high.

## The paint centreline (`paint_centreline.json`, `paint_gate.json`, the `paint_*.png` pictures)

`tools/paint_centreline.py` moved the OSM line onto the traced paint and resampled the climb at 1 m as
one curvature-continuous line; it is `../centerline.geojson` (the OSM line is kept as
`../centerline.osm.geojson`). `tools/verify_centreline_paint.py` passes it on all four checks:
- (a) all 5,813 medium+ paint points within 0.75 m of it, worst 0.61 m (C13's in-arm); OSM misses 1,320
  of them, worst 7.56 m (C4);
- (b) 7,114 climb points at 0.998-0.999 m: no step and no neighbour failure (OSM: 444 and 971);
- (c) no reversal, no self-intersection; the largest single step is 71.7 deg, the C13 junction node,
  kept as a node (an arc at the measured junction radius does not fit between the ends of the traced arm
  paint: that is P3b's junction mouth);
- (d) closed exactly, and the seam is smooth across the wrap (2.2 deg step, limit 3.2; OSM's 4.9 deg
  facet there failed the neighbour rule).

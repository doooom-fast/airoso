# `data/aerial/`: the Lariat's aerial measurements

**Written 2026-10-11, the V3 aerial pass (ledger 0048, dossier section 12 "aerial owed").**
These are measurements only: no geometry, no Blender, no kn5 and no config change. Nothing in a
build reads these files yet. P2 decides what goes into `hairpin_fit.corners[].radius_m`, the width
table and the C-470 decks.

## Files

| File | What it is | Bytes | md5 |
|---|---|---:|---|
| `aerial_measurements.json` | sources, the 49 windows, per-corner radius + method + confidence (C1-C13), widths (34 stations, 28 usable, + hairpin legs + apexes + junction arms), edge observations, the two C-470 crossings, OSM registration | 163,190 | `13dfaf0f458221552dddd877fa0b542a` |
| `overlays/C1.png` ... `C10.png`, `C12.png`, `C13.png` | per-corner overlay: imagery crop, OSM lap line and nodes (datum-shifted), traced pavement edges, edge lines and centre line, fitted circles, the result in magenta, the core wedge | 74-128 KB each | listed below |
| `overlays/X19340.png`, `X21138.png` | the two C-470 decks over the lap: traced deck edges, OSM bridge ways, the lap | 123-126 KB | listed below |

There is no `C11.png`: the bend is in deep tree shadow and nothing was measured there.

Overlay md5s: C1 `22d17edc6d40fb2b0bd20604d9c64285`, C2 `e7e08a1280024ba13625145f2952763d`,
C3 `e3c5c294c4981d70dda45046a6439717`, C4 `1ca31ae05f8b6d4c19e28a96a8419123`,
C5 `a80b6593ec4f633fba218edb05733096`, C6 `7643f17a9dd4e642789eef42b6121ff3`,
C7 `8c30b9d89a94813dc53cbd4491e43674`, C8 `77a19c5d354ff798e5ef339528fae35d`,
C9 `20d2c19393911fdafbf46f4f6112610f`, C10 `936738179b5f43ba2414d8b6abafd732`,
C12 `4dad36177ba63c6ce5e1884b583e192e`, C13 `08b0f37d0de6d990b8b217e5ed69cd67`,
X19340 `325eef3c3fb7ca2c0b3577c8f5defc40`, X21138 `baf8f0c6119317a04389216ddb2d188a`.

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
- **What is in the repo:** only the overlay crops above. They are small (about 25-55 m across,
  palette PNG) and public domain.
- **What is not:** the raw windows. They stay in session scratch,
  `C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/scratchpad/lariat2/naip/`.
  Each window there has a JSON beside its PNGs with the bbox, the exact request URL, the raster
  names and the fetch time; `aerial_measurements.json` repeats that list under `windows`.
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

The scripts are session-scratch helpers, not engine code:
`.../scratchpad/lariat2/v2/` (`aer.py`, `aer2.py`, `core.py`, `corners.py`, `hough.py`,
`junction.py`, `widths.py`, `reg.py`, `datum.py`, `xmeasure.py`, `xfinal.py`, `finalize.py`,
`build_json.py`), plus `../lib/` (`geo.py`, `lap.py`, `naip.py`, `img.py`). They need only Pillow.
To re-run them:

1. `widths.py fetch` (and `lib/naip.window` for the corner and crossing windows) re-fetch into the
   cache.
2. `core.py` and `junction.py` measure the corners.
3. `widths.py measure` measures the stations.
4. `reg.py` measures the registration.
5. `xfinal.py` measures the crossings.
6. `finalize.py` and then `build_json.py` write these files.

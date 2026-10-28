# Research handoffs awaiting Kevin's approval

Research-only dossiers written for a build session. **Nothing here is built**, and none of these
tracks has a `track.config.json` yet. Each follows `fleet/templates/LOCATION-DOSSIER.md` and ends
with the build session's first concrete steps. Kevin approves a dossier before any geometry.

| File | Subject | Decision Kevin owes |
|---|---|---|
| [`tracks/milford-road-course/DOSSIER.md`](../tracks/milford-road-course/DOSSIER.md) | GM proving grounds worldwide (deep on Milford), every Michigan road course, ranked recommendation, full dossier for the Milford Road Course (Part D) | **Approved 2026-10-28** ("Build Milford first"). Built: v0.1.0 at T1, see `tracks/milford-road-course/source/route-notes.md` |
| [`tracks/exotics-racing-lv/DOSSIER.md`](../tracks/exotics-racing-lv/DOSSIER.md) | Exotics Racing, Las Vegas | **The LVMS track closed 2021-11-28; Exotics Racing now runs at SpeedVegas.** Pick target A (shut-down LVMS circuit from historical imagery) or B (current SpeedVegas track) |
| [`fleet/reference/SATELLITE-ROAD-TEXTURES.md`](../fleet/reference/SATELLITE-ROAD-TEXTURES.md) | Orthoimagery as hi-res AC road textures: sources and licences, GSD at driver height, shader layering, texture budget, proposed engine addition and gates | Whether to add the three `scripts/aerial/ortho_*` modules; which imagery licence to accept per track |

## Caveats shared by all three (2026-10-28)

The research session's network policy denied every direct page fetch and returned 403 for Overpass,
Nominatim, the USGS National Map, Clark County GIS and Michigan open data. Every row is sourced from
web-search results and tagged (`·snip`, `[unverified]`, `[derived]`) accordingly. No OSM query, DEM
tile or image was pulled; each file's §9/§11 says what the build session runs first.

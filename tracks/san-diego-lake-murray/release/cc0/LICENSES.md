# K10 - San Diego (V3) — Lake Murray Loop — licence manifest

Every bundled binary asset is CC0-1.0 (public domain); credit is courtesy, not required. Stock
Assetto Corsa surface sounds are referenced by name (`data/surfaces.ini` `WAV=`), never
redistributed. No third-party mod content is included.

## Ours — CC0-1.0

| Asset | Files |
|---|---|
| Geometry: road, kerbs, sidewalks, median islands, terrain seating, lamp posts | `san_diego_lake_murray.kn5` meshes |
| AI line, map, outline, preview | `ai/*`, `map.png`, `ui/*` |
| Generated textures: lane lines, kerb stripe, lamp solids | `line_white.png`, `line_yellow.png`, `solid_metal_dark.png`, `solid_lens_warm.png` |
| Street-lamp model | Kevin Conboy's asset library (`fleet/reference/ASSET-LIBRARY.md`, ledger 0005) |
| TreeFX placement list (positions only, no models) | `extension/trees/trees.txt` |

## CC0 from others — bundled in the kn5

| Asset | Files | Source | Licence | URL |
|---|---|---|---|---|
| aerial_asphalt_01 | `asphalt_cracked_diffuse.jpg`, `asphalt_cracked_normal.jpg` (names kept for the material bindings; bytes are Poly Haven's) | Poly Haven | CC0-1.0 | https://polyhaven.com/a/aerial_asphalt_01 |
| Grass001 | `grass_diffuse.jpg`, `grass_normal.jpg` | ambientCG | CC0-1.0 | https://ambientcg.com/view?id=Grass001 |
| Plaster004 | `house_diffuse.png` | ambientCG | CC0-1.0 | https://ambientcg.com/view?id=Plaster004 |
| Concrete034 | `building_diffuse.jpg`, `building_normal.jpg` | ambientCG | CC0-1.0 | https://ambientcg.com/view?id=Concrete034 |

## Not included on purpose

The authored build uses CSP TreeFX models taken from No Hesi 1.10, Algarve Portimão 2023 and
Shutoko Revival Project, and road/building textures from LA Canyons and Hamburg by 4r. None of
those authors license redistribution, so none of it is in this zip. `extension/trees/README.txt`
explains how to drop in TreeFX models you own.

## Data sources

| Source | Licence | Attribution | URL |
|---|---|---|---|
| OpenStreetMap road geometry | ODbL-1.0 | required | https://www.openstreetmap.org/copyright |
| USGS 3DEP 1 m elevation | Public domain (US Government) | courtesy | https://www.usgs.gov/3d-elevation-program |

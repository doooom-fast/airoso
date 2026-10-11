# K10 - San Diego (V3) — Lake Murray Loop — licence manifest

What is ours is CC0-1.0 (public domain; credit is courtesy, not required). What is not ours is
listed below with its origin, and **is not licensed for redistribution** — it is here because this
is Kevin Conboy's own personal build of his father's neighbourhood. Stock Assetto Corsa surface
sounds are referenced by name (`data/surfaces.ini` `WAV=`), never redistributed.

## Ours — CC0-1.0

| Asset | Files |
|---|---|
| Geometry: road, kerbs, sidewalks, median islands, terrain seating, lamp posts, W1-6 Large Arrow signs (plate, arrow, post) | `san_diego_lake_murray.kn5` meshes |
| AI line, map, outline, preview | `ai/*`, `map.png`, `ui/*` |
| Generated textures: lane lines, kerb stripe, lamp solids, sign solids | `line_white.png`, `line_yellow.png`, `solid_metal_dark.png`, `solid_lens_warm.png`, `solid_sign_yellow.png`, `solid_sign_black.png` |
| Generated MUTCD sign artwork — W1-6L/R Large Arrow, W1-7 Two-Direction Large Arrow, W1-8L/R chevron (MUTCD sign designs are public-domain US Government works, 17 U.S.C. §105) | `mutcd_w1-6r.png`, `mutcd_w1-6l.png`, `mutcd_w1-7.png`, `mutcd_w1-8l.png`, `mutcd_w1-8r.png` |
| Street-lamp model | Kevin Conboy's asset library (`fleet/reference/ASSET-LIBRARY.md`, ledger 0005) |

## CC0 from others — bundled in the kn5

| Asset | Files | Source | Licence | URL |
|---|---|---|---|---|
| Grass001 | `grass_diffuse.jpg`, `grass_normal.jpg` | ambientCG | CC0-1.0 | https://ambientcg.com/view?id=Grass001 |
| Plaster004 | `house_diffuse.png` | ambientCG | CC0-1.0 | https://ambientcg.com/view?id=Plaster004 |

## Third-party — personal-use only, NOT redistributable

| Asset | Files | Taken from | Terms |
|---|---|---|---|
| Cracked asphalt road surface | `asphalt_cracked_diffuse.jpg`, `asphalt_cracked_normal.jpg` | LA Canyons 1.2 (Phoenix77), `main_roads.kn5` / `lac_tarmac_detail_cracked_04.dds` | mod author's; no redistribution licence |
| Tilt-up concrete (buildings) | `building_diffuse.jpg`, `building_normal.jpg` | Hamburg by 4r, `nhh_detail.kn5` material `concretebunker` (TextureCom `TCom_Wall_ConcreteBunker2`) | TextureCom / KitBash3D commercial maps embedded in the mod; no redistribution licence |
| Concrete K-rail barrier (race layouts) — Kevin's owned asset pack, licence not recorded, personal use only | `concrete_barrier_diffuse.png`, `concrete_barrier_normal.png` in `san_diego_lake_murray_race.kn5`; the race barrier strips sweep the silhouette of the pack's `concrete_barrier_4m.obj` | Kevin's owned asset pack (`assets/licenses.json`: licence `UNRECORDED`, ledger 0047 Q10) | licence not recorded — personal use only; the CC0 package leaves the race layouts and this kn5 out |
| TreeFX models: PalmV1/V2/V3, PepperV1, SycamoreV1/V2, Sage, Yucca, Agave | `extension/trees/*.bin` | No Hesi 1.10 (`nohesi_110/extension/trees`) | No Hesi's licence forbids derivative works and redistribution |
| TreeFX models: Gum, Oak3, Bush, Bush3 | `extension/trees/*.bin` | Algarve Portimão 2023 (`algarve_portimao_2023/extension/trees`) | mod author's; no redistribution licence |
| TreeFX model: Pine_Aleppo | `extension/trees/Pine_Aleppo.bin` | Shutoko Revival Project 0.9.3 (`Pine_Aleppo_Desktop_5_Forest_custom1`; a SpeedTree asset) | mod author's / SpeedTree; no redistribution licence |

## Data sources

| Source | Licence | Attribution | URL |
|---|---|---|---|
| OpenStreetMap road geometry | ODbL-1.0 | required | https://www.openstreetmap.org/copyright |
| USGS 3DEP 1 m elevation | Public domain (US Government) | courtesy | https://www.usgs.gov/3d-elevation-program |

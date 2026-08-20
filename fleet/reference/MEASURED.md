# Measured — the reference shelf, first pass

*2026-08-06. `scripts/modkit/inspect_track.py` run over 22 installed tracks on the Windows box —
every Kunos + reference mod in Kevin's curated install, and all five installed k10 tracks, measured
with the same ruler. Raw per-track JSON in `fleet/reference/raw/`. These are **file measurements**;
nothing here is an in-game claim (rule 0). Numbers cross-checked by direct triangle probes where
flagged.*

**The instrument:** `inspect_kn5` (per-surface mesh density, invisible-physics split, materials/
shaders/textures, 65k-cap pressure) + `inspect_track` (models.ini aggregation, surfaces.ini feel
params, AI line headers, CSP ext_config features, VAO, cameras). Known caveats: `grid` derives
from area/tris and assumes isotropic meshing — anisotropic decks (SRP) and catch planes skew it
(see §3); per-surface aggregates include everything carrying the key, driven or not.

---

## 1. Physics road density — the headline table

"grid" ≈ edge of an equivalent right-triangle grid, area-weighted across the surface's meshes.

| Track | Class | ROAD grid (m) | invisible / total | Notes |
|---|---|---|---|---|
| pacific_coast_hwy | canyon mod (Phoenix77) | **0.29** | 253/254 | densest measured; full visual/physics split |
| ks_nordschleife | Kunos scan | **0.53** (ASPH-NURB) / 0.70 (TRM-NRM) | all invisible | KERB 0.46, CURB 0.81 |
| ks_laguna_seca | Kunos scan | **0.53** | 139/139 | KERB 0.62 |
| ks_brands_hatch | Kunos scan | **0.62** (ASPH_BRANDS) | all invisible | KERB 0.47 |
| la_canyons | canyon mod | **0.64–0.94** (12 ROAD* keys) | ~all invisible | per-segment friction palette |
| union_island | island network | **0.70–0.87** (ROAD/B/C) | mostly invisible | |
| ks_highlands | Kunos fictional | **1.04** | all invisible | PAVE 0.50 |
| ks_black_cat_county | Kunos fictional network | **1.14** | all invisible | closest genre to our street ports |
| muracciole_vezzani | rally (Corsica) | **0.83** | visible single-layer | KERB **0.26** |
| glencoe | rally (78 km) | **0.85** | visible single-layer | 1.06M m² of road |
| willow_springs | US club circuit | **0.93** | visible single-layer | |
| oregon_raceway_park | US club circuit | **0.91** | visible single-layer | |
| mulholland_v1 | canyon mod | **0.95** | visible single-layer | |
| bilsen_road | road mod (older) | 3.15 | visible | the coarse outlier among refs |
| shuto_revival_project_beta | highway | **~1–1.5 lateral × 100–750 long** (probed) | 214/271 | anisotropic decks — see §3 |
| nohesi_110 | LA freeway | same technique (probed) | 0/129 | textures external (15 MB in kn5) |
| **san_diego_lake_murray** | **k10 street port** | **4.71** | **0/1 — one mesh, visible, physics = visuals** | KERB 1.76 |
| **lookout_lariat** | **k10 street port** | **2.93** | 0/4 | WALL 0.25 (203k verts of fence) |
| **imi_motorsports** | **k10 circuit** | **2.85** | 0/2 | KERB 0.35 ✓ |
| **high_plains** | **k10 circuit** | **3.01** | 0/2 | KERB 0.37 ✓ |
| **pueblo_motorsports_park** | **k10 circuit** | **3.00** | 0/2 | KERB 0.36 ✓ |

**The gap:** every reference road, whatever the genre, meshes its driven surface at **0.3–1.1 m**
(or SRP-style ~1–1.5 m lateral); ours are **2.9–4.7 m, single-layer, visible**. At 4.7 m spacing no
surface texture below ~10 m wavelength can exist in the mesh, and every vertex step is a felt
event — the data-side shape of 0018's "rough everywhere" and the deleted week's "god awful".
Linear gap ~3–9×; vertex-budget gap on the road only ~10–80× (spacing²), which is affordable
precisely because the references make the physics road **invisible** and keep the visual skin
coarser (Kunos: 100% of scanned physical surfaces are non-renderable meshes).

**Good news the same table carries:** our KERB meshes (0.35–0.37) already sit at reference density
(Kunos 0.46–0.62, Muracciole 0.26) — the engine's kerb generator is not the problem. Circuit GRASS
(1.5–2.0) is denser than most references (2.5–6.7); SD/Lariat GRASS (12.8–16.8) is coarse but
terrain is low-felt-impact.

## 2. AI lines — universal, and one trick worth stealing

Every reference ships `fast_lane.ai` v7 at **1.53–1.64 m point spacing** — including 93 km of it
on LA Canyons' 2-way layout and 24.7 km per direction on PCH. Kunos additionally ships
`data/ideal_line.ai` (same format) and `pit_lane.ai` everywhere; several mods ship
`pit_lane_with_grid.ai`. **k10 tracks: zero .ai files across the fleet** (known — R2's keystone).

The traffic trick: freeroam/traffic layouts (LA Canyons `2way`, Union Island `traffic`, Mulholland
`freeroam`) set **`pit_lane.ai` = a copy of `fast_lane.ai`** — AC then treats the whole road as
valid for both, which is what lets traffic AI run point-to-point roads. SRP and No Hesi ship **no
.ai at all** — their traffic is CSP lane-graph (`traffic.json`) + server-side, confirming the two
distinct traffic architectures in RESEARCH.md §B6.

## 3. The SRP discovery — anisotropic decks and catch planes (probed directly)

`physical.kn5` `1ROAD_yaesu`: coherent sliver strips **~190 m long × ~0.97 m wide** (probe: edges
190.0 / 190.3 / 0.97 m). The Shuto viaduct is engineered-smooth, so SRP spends its physics budget
laterally (crown/lane shape) and lets straights span hundreds of metres — smoothness by
construction; feel comes from `surfaces.ini` (`ROAD fric=1 vib=0.05x0.06`, `BRIDGE
wav=bridge.wav`, expansion-joint keys like `OVERLAP`/`OLD`).

The `1ROAD_minato2.*` meshes are **not roads**: 45°-tilted planes spanning ~1.6 km × ±275 m
vertically (probe: 533–923 m edges, y from +255 to −277) — out-of-bounds **catch surfaces** keyed
as ROAD so cars that leave the deck land on something. Lesson for the study kit *and* for our own
tracks: physics keys carry catch geometry too, and per-surface aggregates must be read with that
in mind (this is what made SRP's raw area totals absurd).

## 4. surfaces.ini — palettes, not single keys

- **Kunos ROAD friction: 0.97–0.98** (Laguna 0.97, Nordschleife ASPH-NURB 0.98, Brands 0.98).
  Mods: 0.9741 (Union), 0.97 (PCH, Glencoe), 1.0 (SRP/No Hesi/Muracciole — grippier for traffic/
  rally styles). **Ours: 0.99 everywhere** — slightly above the Kunos band; worth a deliberate
  choice per archetype rather than one global value.
- **The references use friction *palettes* keyed to road segments:** LA Canyons carries **26
  surface keys** (ROADACM 0.955, ROADMTW 0.915, ROADSRE 0.913, parking lots 0.91–0.94 …) — the
  canyon roads get older/dirtier friction by segment. PCH 17 keys (DRIVEWAY 0.93, GASROAD 0.92,
  MANSIONROAD 0.96). Nordschleife 18 (TRM-NRM 0.98, CONCRETE 0.85, CNC-KRS with damp+vib).
  **Ours: one ROAD key per track.** A street port with driveways, old lanes and new lanes reading
  as one uniform surface is part of why it feels generated.
- **Kerb recipes** (for reference): Kunos KERB fric 0.90–0.97 + `kerb.wav@1.3` + vib 0.2×0.4–1.0;
  CURB variants at 1.0 pitch. Ours (0.92 + kerb.wav@1.3 + vib 1.0×1.5) is in-family, vib a touch
  hot.
- **Off-road feel is SIN bumps**: grass/gravel/sand carry `SIN_HEIGHT 0.01–0.04 × SIN_LENGTH
  0.4–1.0` + damping on every reference. **Our GRASS/LAWN have no SIN at all** — flat-feeling
  runoff for free.

## 5. The Kunos asphalt material, copyable (Laguna, via `inspect_kn5 --materials`)

Laguna's road family is **`ksMultilayer_fresnel_nm`** — a mask-blended multilayer, not the plain
MultiMap the community guides assume:

```
[ksMultilayer_fresnel_nm] asphalt_norm
  ksAmbient=0.42 ksDiffuse=0.38 ksSpecular=0.02 ksSpecularEXP=10
  magicMult=0.85 fresnelEXP=4 fresnelMaxLevel=4 tarmacSpecularMultiplier=4
  txDiffuse=asph.dds txMask=tarmac_mask.dds
  txDetailR/G/B/A=tarmac_detail_B.dds txDetailNM=tarmac_detail_NM_B.dds
```

Variants measured: `asphalt_2` (multR 0.2/multG 0.9 detail scaling), `asphalt_dark` (ambient/
diffuse 0.33, magicMult 0.7), `asphalt_broken` (detail channels swap to gravel textures),
`asphalt_dirt`, `concrete` (stucco detail). Pattern: **ambient/diffuse 0.33–0.45, specular ≤0.1
with EXP 10, fresnel 3–4, and a 4-channel detail mask** that blends clean/worn/dirty asphalt along
one surface — that mask-blend is how one material reads as a weathered real road.

## 6. Presentation floor

| Track | grass_fx | rain_fx | lights | trees | VAO | cameras |
|---|---|---|---|---|---|---|
| ks_nordschleife (CSP-era config shipped) | yes | – | 1 | yes | – | **1080** |
| la_canyons | – | – | 1+19 series | – | – | **1611** |
| union_island | yes | yes | 1+1 | – | – | 385 |
| pacific_coast_hwy | yes | yes | 0+1 | – | – | 245 |
| willow_springs | – | – | – | – | **yes** | 293 |
| oregon_raceway_park | yes | yes | 1 | – | **yes** | 18 |
| shuto_revival_project_beta | yes | yes | **4+54 series** | yes | **yes** | 84 |
| nohesi_110 | yes | yes | 0+1 | yes | – | 12 |
| **k10 (all five)** | colorado yes / SD no | yes | Lariat **305**, circuits 33–46, SD 1 | no | **none** | **0** |

Ours already generate real `[LIGHT_N]` entries (the Lariat's 305 streetlights are ahead of most
mods). Missing across the fleet: **VAO patches (0/5), cameras (0/5), trees/TreeFX, grass_fx on
SD**, and every track's AI. Cameras matter more than expected — references treat replay/TV cameras
as core content (Kunos ships 41–1080).

## 7. What this buys each train (targets, in numbers)

- **R2 (harness):** ship `fast_lane.ai` v7 at ~1.5 m spacing + `pit_lane.ai`; the traffic trick
  (§2) covers point-to-point and freeroam layouts.
- **R3 (Blender seam):** the export path gains the visual/physics split — invisible `1ROAD` at
  target density, pieces ≤32k verts / ≤1 km (RESEARCH A3), visible skin free to be pretty.
- **R4 (surface truth):** physics road at **≤1.0 m** isotropic on circuits/streets (Kunos band
  0.53–1.14); rally stages may follow the sliver pattern (lateral ≤1 m) where stages are smooth
  gravel; SIN bumps on every off-road key; friction palettes per segment class; roughness synth
  to RESEARCH B3 targets.
- **R5 (floor):** VAO patch + ≥20 cameras + grass_fx everywhere + SurfacesFX gravel on rally +
  per-archetype `surfaces.ini` palette. Lint the floor (REALISM §6).

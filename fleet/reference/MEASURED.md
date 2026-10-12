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

## 8. Kinks on reference mountain roads — drive_test's own ruler (2026-10-12)

*Lookout Lariat V3-PLAN P5 (ledger 0048): "Before Drive 1 the kink metric runs on la_canyons and simtraxx Pikes
Peak (both on this machine); a ceiling re-set from those reference mountain roads becomes [std]." Measured with
`tools/calibrate_kinks.py`, which does not re-implement the metric: it writes the reference road as a gate
project in scratch and runs `scripts.geometry.drive_test.run` on it, exactly as on our builds (1 m stations, the
six interior wheel paths, a kink = slope change > 3 %-points between consecutive 1 m steps). Raw rows:
`fleet/reference/raw/kinks_*.json`. File measurements, read only; nothing here is an in-game claim.*

**What is measured.** The layout's physics road only: every mesh AC reads as physical (`<digits><KEY>…`) whose
surfaces.ini KEY is the road (`^ROAD`; Targa Florio's `^ASPH`), from the kn5s its `models_<layout>.ini` loads,
decoded with `scripts.modkit.extract_kn5.parse(keep=…)`. The line is the layout's own `fast_lane.ai` moved to the
middle of the valid road its sideLeft / sideRight record (smoothed over ±10 points), so the wheel paths sit where
ours do: on the lane, not on a racing line that cuts every apex.

| Reference | Layout | Physics road | Lane (m, median) | Length | Kinks | **Kinks/km** | Bumps/km |
|---|---|---|---|---|---|---|---|
| simtraxx Pikes Peak 0.81 (archived copy, `Dropbox/simracing/mods archive/`; not installed) | pp100ahc (hill climb), `_fast_lane.ai` | `ROAD`, 3 meshes, 44.4k tris, grid 2.75 m | 8.21 | 19.96 km | 389 | **19.49** | 27.8 |
| la_canyons | mt_wilson_hillclimb | `ROAD*` (13 keys), 387 meshes, invisible physics at ~0.72 m | 8.86 | 6.84 km | 5 | **0.73** | 4.1 |
| simtraxx Targa Florio | stage_1 | `ASPH-TARG` | 7.89 | 14.22 km | 7 | **0.49** | 0.5 |
| la_canyons | angeles_crest_east | as mt_wilson | 8.37 | 40.86 km | 0 | **0.00** | 0.0 |

Notes on the rows:
- Pikes Peak's kinks are where its coarse mesh creases: 263 of ~390 are on the two OUTER interior wheel paths
  (±3.5 m on an 8.2 m road, 0.66 m inside the mesh edge), 24 on the centre pair; magnitudes p50 3.8, p90 5.8,
  max 9.3 %-points (an independent re-count by wheel path, 19.74/km). Its mesh is 8.3 m wide where the AI sides
  say 8.2 m, so the paths are on the road, not off its edge.
- Mt Wilson's 5 kinks are one feature (st 1,511–1,517); Targa Florio's worst are at the start (st 2–4).
- Every row also "fails" drive_test on daylight gaps and excursions: only the road was extracted (no ground
  beside it), so those two counts mean nothing here. Kinks, bumps and severe steps are road-only and stand.
- Pikes Peak is the plan's named reference and the only Colorado mountain road on the shelf. It is not installed
  under `content/tracks`; it was read from the archived copy in Kevin's mods archive, read only.

**The proposed ceiling: kinks ≤ 19.49 /km on the Lariat [std: measured on reference mountain roads].** The
kinkiest of the four: a Lariat that reads more is kinkier than every reference mountain road on the machine. It
replaces V3-PLAN's 5/km, which was [invented] (Lake Murray V3's own 4.97/km). It is a per-track value
(`track.config.json gates.drive_test.kinks_per_km_max`); drive_test gates kinks for no other track.

What the band says beyond the ceiling:
- The references split into two classes: densely meshed physics roads (la_canyons' invisible 0.7 m road,
  Targa Florio) read **0.0–0.73/km**; a coarse 2.75 m physics road (Pikes Peak) reads **19.5/km**. The metric
  measures mesh creases as much as the road. A V3 Lariat reading between ~1 and 19.5/km is inside the band but
  meshed coarser than a scanned road; below ~1/km it is scan-class.
- For scale, the installed July Lariat read **68.3/km** (v0.46.0) and the v0.66.3 run **108.9/km**: 3.5–5.6×
  the ceiling.
- If Kevin wants the scan-class bar after Drive 1, the same rows give it as [std] too: 0.73/km (the kinkiest
  dense reference). It is not proposed for Drive 1: the draft road's physics mesh density is not decided yet,
  and the plan wants Drive 1 judged, not red by design.

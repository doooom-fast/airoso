# Reference research — the seed for R1/R2/R4

*Web research run 2026-08-06 (two sweeps: the modding craft, and the public-data realism sources).
Everything here was verified against live sources that day unless flagged **[unverified]**. This
file seeds the study kit; measured findings from our own inspections land beside it in
`fleet/reference/` as R1 produces them.*

---

## Part A — The modding craft

### A1. How the reference mods were actually made

- **Shutoko Revival Project** (highway gold standard, v0.9.3): a volunteer *team* production built
  from real-world data + video + on-the-ground recon; moved to ~4.5k 3D trees on the C1 in 2023.
  No published toolchain postmortem — process knowledge lives in their Discord/Patreon.
- **No Hesi "110"** (LA's 110 freeway, 35+ km): built from scratch by Quadbreak Studios with
  **~20 engineers/artists**; their ArtStation breakdowns are the closest thing to a modern freeway
  build postmortem (artstation.com/artwork/GvYQDN, /mAYG61). Takeaway: the freeway bar is now
  studio-grade — which is fine, because our studio is an agent fleet.
- **LA Canyons (Phoenix77)**: 115 km of real Angeles Crest roads in v1.2, ~900 km² terrain, three
  years of work starting 2017 — and it *predates* easy lidar (he has said future roads depend on
  sourcing "detailed enough reference data (LiDAR)"). We start with the data he wished he had.
- **Tail of the Dragon**: the current reference is **Project Kaido's full scratch rebuild of
  US-129** (started mid-2025, v1.1 Nov 2025, rally-stage layout planned for v2.0), with a
  community traffic plan. **Directly relevant to our Dragon Tail stages — acquire and study.**
- **Rally**: Simtraxx's Transfagarasan (~100 km, laser-scanned + photogrammetry) is the
  max-fidelity reference; Peyregrosse–Mandagout and Semetin are the most-loved stages.
  **acrallycentral.com** is the current hub for AC rally standards.
- **LilSki (Watkins Glen, Bridgehampton, Lime Rock)** — *the* validation of our bet: he builds
  Kunos-adjacent US circuits **in Blender**, from aerial lidar, and has said "Blender's spline
  functionality is superior to 3ds Max" — and that **even with lidar he still builds the road from
  a spline and hand-matches it to the data**. His CloudCompare + Blender "LIDAR point cloud to
  mesh" tutorial (overtake.gg thread 131207) transplants directly to our 3DEP situation.
- **Fat-Alfie (Feldbergring, Thomson Road)** — best documented process thread (Deutschlandring,
  overtake.gg thread 132099): digitized centerline → coarse terrain → **loft along a spline with
  three cross-section profiles** (flat / center-crowned / raised-edge hairpin) → **drive-test in
  AC early and often**. A 10 km track began as a 192-vert spline and a 4,600-tri first loft.
  This is our engine's underlay philosophy, done by hand in 2016 — and a year of authorship on top.

### A2. Studying kn5s (tools beyond our own modkit)

- **Our `modkit.extract_kn5` already parses kn5 natively** (proven against `ks_laguna_seca` on the
  Windows box 2026-08-06) — the inspector builds on it, no dependency needed.
- **leBluem/io_import_accsv** (updated Nov 2025, Blender 3.0+): imports **kn5 tracks + fast_lane/
  pit_lane .ai + side/groove CSVs + camera INIs** into Blender — reference track and its AI lines
  in one scene. The study-side importer of choice.
- **CSP Objects Inspector** (in-game dev app): click any mesh on a loaded track → shader name,
  every material param, textures, mesh stats. **The best instrument for Kunos road materials.**
- Others: LKOLA/blender-kn5-addon (import/export, no ksEditor), 3DSimED3 (£30, 20-day trial),
  CM "Unpack KN5" (dev mode), RaduMC/kn5-converter (C#) and MarvinSt/kn5-obj-converter (Python,
  scriptable batch stats), SeizureSaladd/Kn5Decrypt for protected kn5s. Format doc: site.hagn.io.
- Imported materials are metadata to *read*, not faithful Blender visuals — AC shaders don't map
  to Blender nodes.

### A3. The measured bar (what good tracks ship)

- **Physics road**: the standard technique is an **invisible dense physics mesh under a pretty
  visual skin** — physics piece named `1ROAD_*`, ksEditor "Is Renderable = false" (or CSP
  `[MESH_ADJUSTMENT_...] IS_RENDERABLE=0`); pieces **≤ ~32k verts and ≤ 1 km each**, a track split
  into 10–20 pieces. "Don't be afraid of poly count on the invisible road."
- **Density reference**: Nordschleife's invisible physics road is ~1.33M verts over 20.8 km —
  **~0.5 m longitudinal spacing across the full width** (derived, not quoted); Monza's road is
  ~400k tris. Community rule of thumb: physics ~0.5–1 m spacing, visual coarser. R1 measures the
  exact Kunos numbers with our own inspector.
- **Asphalt material**: `ksPerPixelMultiMap` family — txDiffuse + txNormal + txMaps
  (spec/gloss/reflect channels) + **txDetail** grain tiled via detail-UV multiplier. Copy Kunos
  scalar params (ksAmbient/ksDiffuse/ksSpecular/ksSpecularEXP + multimap balance) via Objects
  Inspector.
- **surfaces.ini feel**: FRICTION (asphalt ~0.96–1.0, kerb ~0.92), DAMPING (0 asphalt, >0 loose),
  WAV/WAV_PITCH, **SIN_HEIGHT/SIN_LENGTH** (procedural sine bumps — how flat kerbs/gravel get
  texture; linear, no randomization), VIBRATION_GAIN/LENGTH (FFB rumble, tuned by ear),
  DIRT_ADDITIVE, IS_VALID_TRACK, IS_PITLANE.
- **CSP SurfacesFX** (public since CSP 0.2.4; we run 0.2.12.1): **`_EXT_SURFACE_TYPE=GRAVEL`** in
  surfaces.ini with LOOSE/REGULAR/FIRM modifiers; reference gravel = FRICTION 0.89,
  SIN_HEIGHT 0.02, SIN_LENGTH 0.4 (acrallycentral.com/surfacesfx). **This is what makes 2026
  gravel feel like gravel — the Dragon Tail stages want it.**
- **Kerbs**: real 3D geometry + dedicated surfaces entry; leading edge tucked under or glued onto
  the road so tyres never strike a step; serration modeled where real; WAV + VIBRATION + SIN
  supply the feel. Painted kerbs read fake; un-surfaced geometry feels dead. (Matches L9.)

### A4. The 2026 presentation floor (ext_config)

- **GrassFX**: `[GRASS_FX]` with GRASS_MATERIALS/MESHES, OCCLUDING_MATERIALS, mask-driven spawning
  (MASK_MAIN_THRESHOLD ~0.5, luminance bounds), shape/trim params, regional adjustment zones,
  `[INCLUDE: common/grass_fx.ini]` mixins.
- **RainFX**: PUDDLES/SOAKING/SMOOTH/ROUGH/LINES material lists (LINES is a *physics* effect —
  paint gets slippery) + STREAM_POINT/EDGE water routing in world coords.
- **LightsFX**: `LIGHT_SERIES` on lamp meshes — SPOT/RANGE/COLOR/FADE + MATERIAL_ADJUSTMENT
  emissives. SRP-class night maps ship hundreds. The SD freeway at night needs this.
- **VAO patch**: baked with CustomTracksBakery.exe or GPU acc-bakeryoptix → `<track>.vao-patch`
  beside the kn5. **A release without VAO reads flat-lit and dated.**
- **TreeFX** (CSP ≥0.1.79) is the 2026 tree floor — 3D/impostor trees replacing X-billboards;
  community packs run 1,250–17,000 trees with LODs; placement tooling can parse existing
  billboard positions.
- **License-clean asset pools**: Poly Haven, ambientCG, Kenney (CC0); AC-specific tree/texture
  resource threads on assettocorsamods.net. Much of the circulating mod ecosystem uses ripped
  Forza/Kunos assets — **our CC0/PD/own-library pipeline (ledger 0005 + Part B signage) is a
  genuine differentiator**, not a handicap.

### A5. Blender→kn5 state of the art

- **Actively maintained exporter: jwl-7/blender-assetto-corsa-tools** (fork of moppius, lineage
  from Hagnhofer) — kn5 export for **cars and tracks**, .ksanim, ksEditor-persistence processing,
  texture bundling; v1.0.7 released 2026-03-25. Stated Blender 3.0+; **no addon explicitly claims
  4.2 support — pin and test, as we already do.** R3 work item: evaluate this fork against our
  vendored addon.
- **No dominant geometry-nodes road generator exists** — the masters use spline + loft +
  cross-section profiles, hand-matched to data. Our engine is the programmatic version of exactly
  that; the underlay keeps the spline editable where their hands were.
- **BlenderGIS** for georeferenced OSM/DEM/orthophoto import (the ortho-draping tutorial at
  assettocorsamods.net thread 1517 matches our NAIP plan); **CloudCompare** fronts lidar→mesh.
- **Race Track Builder** is aging (2025: Google integration now needs your own billed API key);
  serious builders treat its output as a starting mesh. Nothing it does beats our own pipeline.

---

## Part B — What reality measures like, and where to get it

### B1. Lidar point clouds (the realism unlock)

The same USGS 3DEP source we already trust, but **per-return instead of rasterised** — the 1 m DEM
averages away exactly the cross-slope signal the point cloud preserves.

- **Access: AWS Entwine Point Tiles, free and anonymous.** `s3://usgs-lidar-public`, endpoint
  `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/<ProjectName>/ept.json`. Project
  boundaries index: `github.com/hobuinc/usgs-lidar` (`boundaries/resources.geojson`).
  **Caveat: EPT is stored in EPSG:3857** — reproject (PDAL `filters.reprojection`) before any
  metric geometry or cross-slopes come out scaled wrong.
- **PDAL pipeline:** `readers.ept` (with corridor `bounds`) → `filters.outlier` → ground returns
  via `Classification[2:2]` (ASPRS class 11 "road surface" is rarely populated in 3DEP
  deliverables) → reproject → write. OpenTopography's `OT_3DEP_Workflows` repo has ready-made
  notebooks. Note OpenTopography's own portal is now login/subscription-gated for point clouds and
  its 1 m raster API is academic-only — **use the AWS bucket; it has no restrictions.**
- **Density where we build** (aggregate incl. swath overlap):

  | Region | Project | Density |
  |---|---|---|
  | San Diego County | San Diego QL2 (2014–15) | ~4.9 pts/m² |
  | Denver metro / Front Range (IMI, Second Creek) | CO_DRCOG_2020 | **21.6 pts/m²** |
  | Eastern CO plains (High Plains) | CO_CentralEasternPlains_2020 | QL2+ **[density unverified]** |
  | US-129 TN side (Blount Co.) | Blount County QL2 (2015) | ~2 pts/m² |
  | US-129/NC-28 NC side | NC statewide Phase 4–5 (2017, Geiger-mode) | **QL1, 8 pts/m²** |

- **What it can and cannot give** (per-point vertical noise ~10 cm RMSEz on hard surfaces):
  - **Crown / cross-slope / superelevation: YES, statistically.** A 2% crown over a 3.6 m lane is
    7.2 cm of relief; fitting a plane/quadratic over a 10–20 m longitudinal window gives hundreds
    to thousands of ground returns, so recovered cross-slope is good to well under 0.5% absolute.
    On the Dragon's hairpins at 8 pts/m² this beats assuming AASHTO tables. Watch inter-swath bias
    (a few cm) — fit per-swath or use long windows.
  - **Embankments, cuts, bridge decks, building heights: YES** (first-return minus ground nDSM —
    self-consistent with our terrain and license-clean).
  - **IRI-scale surface roughness (mm–cm at 0.5–30 m wavelength): NO** — below the noise floor.
    Synthesize it instead (B3).
  - Asphalt is dark at 1064 nm — expect thinner return density on the road surface itself.
- Prior art: RTB's paid "LidarToolBox" plugin; the England-DEFRA-lidar AC community thread; OHW
  Solutions' commercial terrestrial-scan tracks (mm-class, different instrument class — 3DEP gets
  us real crown/superelevation/grade, not real texture).

### B2. Cross-section truth (AASHTO / state DOT numbers)

- **Normal crown: 2%** on tangent, high-type pavement; urban curbed streets often one 2% plane
  toward the gutter. **Streets are not superelevated** (consistent with L10) — crown + real
  elevation, with measured lidar cross-slope overriding assumption where density permits.
- **Superelevation:** Green Book emax ∈ {4, 6, 8, 10, 12}%; practice: 8% max in snow/ice states,
  ≤6% urban, TxDOT-style default 6%. Sample pairs: 60 mph @ e=6% → Rmin ≈ 506 m; 60 mph @ e=8% →
  Rmin ≈ 366 m; 45 mph urban @ e=4% → Rmin ≈ 217 m. Between Rmin and tangent, interpolate e ∝ 1/R
  down to normal crown. Transition (runoff) length: cross-slope change × rotated width / max
  relative gradient (0.50%, i.e. 1:200, at ≥50 mph); ~2/3 of runoff on the tangent.
- **Lane widths:** Interstate 12 ft mandatory; arterials 10–12 ft; collectors/local 9–11 ft; 9 ft
  on low-speed residential. **Shoulders (Interstate):** right paved 10 ft (12 ft heavy trucks);
  left 4 ft → 10 ft where ≥3 lanes/direction. Rural two-lane 2–8 ft by volume. Urban curbed:
  no shoulder, curb-and-gutter.

### B3. Roughness — target IRI, synthesize the band the data can't carry

Three-layer model, so nothing is double-counted:

| Wavelength | Source |
|---|---|
| > 30 m | real 3DEP elevation (already have) |
| 0.5–30 m | **synthesized** to an ISO 8608 spectrum scaled to a target IRI |
| < 0.5 m | textures/normal maps + `surfaces.ini` feel, never triangles |

- **IRI targets (FHWA):** good < 95 in/mi, poor > 170 (1 m/km = 63.36 in/mi). Measured 2022 rural
  Interstate distribution: ~85% under 95, median well under. Working targets: **healthy freeway
  55–75 in/mi** (SD network), **city streets 95–170**, **old mountain asphalt 120–250**
  [calibrated estimates — per-route IRI exists in state HPMS data].
- **ISO 8608:** Gd(n) = Gd(n0)·(n/n0)^−2, n0 = 0.1 cycles/m. Class means at Gd(n0), ×10⁻⁶ m³:
  A ≈ 16 (new/maintained highway), B ≈ 64 (worn paved), C ≈ 256 (poor urban).
- **Recipe:** sum cosines with random phase over n ∈ [1/30, 1/0.5] cycles/m → run a quarter-car
  IRI computation (Sayers algorithm, ~50 lines) on the synthetic profile → scale amplitude until
  IRI hits target → apply as two wheelpath profiles (correlated long, decorrelated short). Sanity:
  class-A comes out ~5–15 mm RMS in-band — subtle is correct.
- This retires invented bumps/km limits: drive_test judges against the envelope for the track's
  road class, and 0018's "rough everywhere" gets a measurable definition of *too rough*.

### B4. Roadside furniture — anchors from OSM, inventory from rules

- **OSM tags that work:** `barrier=guard_rail` (ways), `barrier=jersey_barrier`, `barrier=fence`,
  `highway=street_lamp`, `power=pole` / `power=tower`, `emergency=fire_hydrant`,
  `highway=traffic_signals`, `highway=stop`. Speed limits ride `maxspeed=*` on the way (sign nodes
  are rare); US residential mailboxes are effectively unmapped.
- **US completeness reality:** patchy-to-absent on rural roads. **OSM gives anchors, not
  inventory** — generate the rest from road class + context rules. Best fusion rule: *guardrail
  wherever the lidar shows an embankment drop beyond threshold beside the carriageway* — two
  datasets we already pull.
- **Supplements:** Mapillary Graph API `map_features` (traffic_signs layer, 1,500+ classes,
  3D-reconstructed positions; US-129 is among the most-photographed roads in America); Overture
  Maps infrastructure theme (schema'd OSM-derived, ODbL); some state DOTs publish sign/guardrail
  inventories (MD SHA, TxDOT verified; CDOT/Caltrans/TDOT to check).
- **Signs are a generator feature, not an asset purchase:** MUTCD device designs are public domain
  by rule. Official dimensioned vector art: FHWA *Standard Highway Signs* (2004/2012 + 11th-ed
  pages). Thousands of ready SVGs: Wikimedia Commons `Category:PD_MUTCD`. Fonts: FHWA Series A–F
  specs are PD; use a free digitization (Roadgeek 2005/2014 — check per-version license;
  "Highway Gothic FHWA 2025" claims free commercial). Series E-Modified for freeway guide signs.
  Pipeline: SVG → rasterize → atlas → quad/extrusion.

### B5. Terrain and scenery sources (all license-clean)

- **NAIP aerials:** public domain w/ attribution (USDA), 60 cm standard (30 cm optional), re-flown
  every 2–3 years, leaf-on. AWS buckets are requester-pays; also on Microsoft Planetary Computer /
  USDA GeoHub. NIR band → NDVI = free 60 cm vegetation mask.
- **NLCD Annual (1985–2024, 30 m):** land cover + **fractional impervious surface**, public
  domain. Classes 41–43 forest / 52 shrub / 71 grass / 81–82 ag / 21–24 developed drive
  tree-and-grass scattering; impervious fraction gates urban texture blending.
- **Building footprints:** Microsoft GlobalMLBuildingFootprints (ODbL; US heights only on the old
  9.8M subset) or Overture buildings (ODbL). **Heights: derive our own nDSM from the 3DEP point
  cloud** (first return − ground) — self-consistent and clean.
- **Google Photorealistic 3D Tiles: confirmed prohibited** (no offline use, no extraction, no
  machine analysis — display-only streaming). The blosm/RenderDoc rips modders use are ToS
  violations with real distribution risk for a published fleet. Our stack (NAIP + NLCD + lidar +
  footprints + PD signage) needs none of it.

### B6. AI lines, traffic, and the automated-lap seam

- **`fast_lane.ai` is writable offline.** Format verified from gro-ove/actools `AcTools/AiFile/`:
  header 4×Int32 (`version`=**7**, point count, lapTime, sampleCount); per-point 20 B (pos 3×f32,
  cumulative length f32, id i32); extras array: Int32 count then **18×f32 per point** (speed, gas,
  brake, obsoleteLatG, radius, sideLeft, sideRight, camber, direction, normal xyz, length,
  forwardVector xyz, tag, grade); optional spatial-grid trailer. **Workflow caveat:** an
  externally-written .ai must be re-saved through ksEditor — or AC started holding Shift with
  `side_l.csv`/`side_r.csv` present — so the sim rebuilds derived data. Blender import/export
  exists: leBluem/io_import_accsv (also does side CSVs; v1.6 supports point-to-point → our rally
  stages).
- **In-game recording (fallback/reference):** `ENABLE_DEV_APPS=1` → practice → AI app → record →
  `ai/fast_lane.ai.candidate`. Esotic's **AI Line Helper** records `side_l/side_r.csv` boundaries.
- **Traffic for the freeway network:** modern path is **CSP's Lua Traffic Tool** — draws a lane
  graph saved as `traffic.json` beside `surfaces.ini` (lane roles, speed limits, priorities,
  intersections; needs the separate traffic data pack; 2REAL app builds on it). Legacy
  SRP/No Hesi pattern: one layout per lane each with its own `fast_lane.ai`, plus `ai_hints.ini`
  (`[HINT_n]`/`[BRAKEHINT_n]`/`[DANGER_n]`), CSP "new AI behaviour" enabled.
- **Automated laps:** write `cfg/race.ini` and launch `acs.exe` directly (no CM UI;
  `steam_appid.txt` = 244210 if launcher never ran). **No true headless mode** — needs a
  GPU/window; run windowed/minimized. Telemetry: `acpmf_physics`/`acpmf_graphics`/`acpmf_static`
  memory-mapped files at sim rate (struct docs: assettocorsamods.net shared-memory reference;
  maintained reader: ACLIB/SharedMemory). No turnkey scripted-screenshot sweep found — CSP Lua
  scripting is the extension point.

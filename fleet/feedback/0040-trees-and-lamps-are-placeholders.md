---
id: 0040
title: "The trees and lamps are pretty trash" — procedural cross-quad palms, blob trees and box lamps
status: in-progress
scope: tracks/san-diego-lake-murray scenery; engine TreeFX route (scripts/environment/treefx.py, scripts/ac/ext_config.py)
layer: track + tools
train: -
---

## Symptom (Kevin, seat, 2026-10-08)

> "let's start replacing the trees and lamps. They're pretty trash right now."

## What is there today

`build_loop_blend.py` generates 898 Mexican fan palms as cross-quad fronds on cylinder trunks
(PALMFROND_A–H / PALMTRUNK_A–B, ~500k verts), 420 shade trees as blob canopies, 1,000 scrub blobs,
and 239 streetlights as 9 m box posts (LIGHTS) from which `ext_config` clusters [LIGHT_N].

## Inventory (3 agents, 2026-10-08)

- **Owned library** (C:\Users\Owner\Dropbox\Blender): no palm of any kind; every file is a
  Dropbox online-only stub (0 bytes resident) until marked "Available offline". The one owned
  lamp (Street_Lamp.zip) is already decimated into the repo: `assets/models/lamp_post.obj`
  (2,060 v) + `lamp_lens.obj`; its emissive/opacity PBR maps are only in the dehydrated zip.
- **Jackpot — No Hesi 1.10** (installed, hydrated): CSP TreeFX `.bin` models of the right
  Southern-California species — PalmV1/V2/V3 (20/25/28 m fan palms with LOD chains),
  PepperV1 (California pepper), SycamoreV1–V6, Agave/Yucca/Sage/Ocotillo. Plus
  algarve_portimao_2023 (Gum = eucalyptus, Bush1–3) and shuto (Pine_Aleppo). All personal-use
  mod content: `*.bin` is gitignored, never leaves this machine, never in a shared folder
  (No Hesi's licence forbids derivative works — Kevin's standing personal-use decision covers it).
- **rt_california_highway_palms.kn5**: 61 real fan-palm meshes with the dead-frond skirt —
  ~13.6k verts each, so only for a few hero palms or as a billboard texture source.
- **Engine**: `scripts/environment/treefx.py` + `scripts/ac/ext_config.py` already emit
  `extension/trees/trees.txt` + `[TREES]`; nothing was ever wired for Lake Murray.

## Fix — pass 1 (vegetation, built this day)

TreeFX: `tools/export_scatter_blend.py` reads every palm/tree/scrub/median-plant position out
of the built scene (island walk; the scatter is deterministic), `tools/strip_scenery_blend.py`
deletes the procedural meshes, `tools/make_treefx.py` writes `trees.txt` + `[TREES]` with
species mixes (palms 60/30/10 V1/V2/V3 scaled to residential 13–19 m; yards pepper/sycamore/
eucalyptus/Aleppo pine; chaparral sage/yucca/bush/agave; median planting small bush/sage),
positions in the kn5 frame, snapping onto `1GRASS_0_mat, 1GRASS_1_mat, 1ROAD_road_mat`, and a
corridor guard (TreeFX is invisible to the gates, so no tree may stand within half-width + 1 m
of any centreline). Wired into `tools/ship_sd.sh`.

## Fix — pass 2 (lamps, next)

Replace the LIGHTS box posts with `assets/models/lamp_post.obj` instances (chunked under the
65k cap), lens as the LIGHTS emitter so `ext_config`'s clustering keeps one [LIGHT_N] per lamp;
style vs the real cobra-head poles unverified until Kevin looks.

## Verification

Kevin's seat: palms read as Mexican fan palms at believable heights, pepper/sycamore in the
yards, scrub on the Cowles side, median planting on the islands; no tree in any lane; frame rate
no worse (TreeFX is instanced). Then the lamp pass.

## 2026-10-08 — both passes shipped (installed as `san_diego_lake_murray_v3`)

- **Pass 1 (vegetation):** 2,906 TreeFX trees (892 palms, 412 street trees, 992 scrub, 610 median
  plants; 17 rejected by the corridor guard), 13 species; procedural PALM*/TREE*/SCRUB meshes
  stripped from the kn5 (80 → 46 MB before lamps).
- **Pass 2 (lamps):** `tools/author_lamps_blend.py` — 239 × `lamp_post.obj` (2,060 v) + lens
  (994 v) → 9 LIGHTPOST + 4 LIGHTS meshes; ext_config clusters **296 [LIGHT_N]** (was 367 from
  the box posts; the 0.5 m lens straddles 5 m cells at some lamps). kn5 now 107 MB — the lamp
  geometry is ~730k verts; re-decimate the mast to ≤700 v if frame rate says so.
- Gates vs the July reference: no metric worse (drive: severe 0, obstruction 0; audit
  K 169 / I 167 / F 61).
- Open after Kevin's look: lamp *style* (the owned model is a symmetric double-arm luminaire,
  placed arm-axis across the road; real Lake Murray poles are single-arm cobra-heads — hunt a
  closer model or trim one arm), palm species read (PalmV1-3 are smooth-trunk; the skirted
  Mexican fan palm exists only as kn5 mesh in rt_california_highway — hero-palm option),
  flower texture for the island beds, scrub density on the Cowles side.

## 2026-10-08 (later) — seat: palms invisible; lights "way too bright", "still the glowing ball"

- **Zero trees rendered.** CSP log: `🚨 Failed to load trees: Tree manifest is missing:
  ...\extension\trees\san_diego_lake_murray — V` — CSP read the `;` comment line at the top of
  my trees.txt as a manifest filename and rejected the whole list. The working packs (nohesi,
  algarve) carry no comments at all; `tools/make_treefx.py` now emits none. Fixed in place
  (list reinstalled, 2,906 trees, first line `configure:`) — verify in the CSP log next session:
  no "Failed to load trees".
- **Lights:** `lighting.streetlight.intensity` 5.0 → 1.6 and lens emissive 0.35 → 0.08 (config
  keys the engine's ext_config reads; patched into the installed ext_config.ini too, 295 lights).
  The "glowing ball" is the 0.5 m lens mesh with ksEmissive: `tools/author_lamps_blend.py` now
  places the engine's own 2 cm marker triangle instead (invisible, still clusters one [LIGHT_N]
  per lamp) — lands with the next build. Lamp style ("old style, okay") accepted for now.

**2026-10-09 (seat):** Kevin on the rebuilt V3 (TreeFX vegetation, dimmed lights, route-derived side streets): **"incredible."** Detailed verdicts (palm species/height, lamp style, each mouth) still to come from a full drive.

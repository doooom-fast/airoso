---
id: 0056
title: "Make lighter lamp model" / "more modern" — the streetlight is 57 % of the track's vertices
status: in-progress
scope: tracks/san-diego-lake-murray lamps (tools/author_lamps_blend.py, the lamp asset, LIGHTPOST / LIGHTS meshes, data/lights.local.json, ext_config [LIGHT_n]); every later lamp (expansion D4, phase 3/4)
layer: project + asset
train: -
---

## Request (Kevin, 2026-10-14)

> "make lightr lamp moidel" — "morew modern"

## Evidence

Installed v0.18.0 road kn5 (116.3 MB; 1,697,179 verts / 2,026,253 tris): LIGHTPOST = 17 meshes, 966,725 verts (57.0 %),
899,835 tris (44.4 %), for 243 lamps (~4,000 points each); six LIGHTPOST meshes at AC's 65,535 cap (ledger 0054).
Both expansion plans make a lighter lamp the precondition for more lamps (Phase 4 projects 161-174 MB without it).

## Fix (defaults)

A modern street light (a contemporary LED cobra-head / shoebox fixture on a tapered steel pole with a mast arm, the
kind San Diego streets carry now) at about a tenth of today's points, same positions and heights, same light: the 80s
low-pressure-sodium colour, intensity and pool shape Kevin approved (ledger 0043) stay exactly as they are — only the
fixture changes. CSP light sources stay at the lens.

## Verification

Per-lamp and total LIGHTPOST points; road kn5 size before/after; ext_config [LIGHT_n] positions unchanged (or moved with
the lens by a recorded offset); lamps out of every lane (verify_race scenery gate, drive_test obstruction 0); day and
night stills; Kevin's seat (look, load time, FPS).

## Built and rehearsed (2026-10-14, branch of record: this commit; NOT installed — Kevin's seat is the verdict)

**The model.** `tools/make_streetlight_led.py` (deterministic, self-made → CC0; `assets/licenses.json`,
`fleet/reference/ASSET-LIBRARY.md`) writes `assets/models/streetlight_led_post_twin.obj` (pole + two mast arms + two
LED cobra heads → LIGHTPOST), `_post_single.obj` (the single-arm variant), `_lens.obj` (the flat LED lens under the
road-ward head → the emissive LIGHTS mesh) and `streetlight_led.json` (the spec). A galvanised tapered round steel pole,
an upswept davit mast arm, a flat-bottom LED cobra head with a twist-lock photocell and a flat 0.52 × 0.23 m lens. Smooth
shading on the pole / arm / shell, sharp edges at the lip, caps and lens (OBJ smoothing groups → per-face smooth + sharp
edges in `author_lamps_blend._mk_shaded`); cylindrical / box UVs (the prep re-projects them planar, harmless on the solid
pbr textures). Materials are the existing LIGHTPOST / LIGHTS pbr rows — no pbr.py change, so nothing to mirror.

**Taller.** Kevin, right after: "Taller too". The number, from the standards rather than from taste:

| Source | Pole | Arm | Mounting height |
|---|---|---|---|
| City of San Diego SDE-101 (Street Lighting Standard, 1975–2006; Street Design Manual 2017 §4.1c points to it) | 25–28 ft | 8 ft max (concrete / fibreglass), **12 ft for the steel Type 15** | 27–30 ft; 30 ft for the 250 W HPS / 180 W LPS arterial lamp |
| Caltrans Standard Plan ES-6A, Type 15 | 30 ft | 6 / 8 / 10 / 12 / 15 ft | 31'-6" … 34'-3" (33'-9" with 12 ft) |
| Caltrans Standard Plan ES-6A, **Type 21** | **35 ft** | **12 ft** | 36'-6" … 39'-3" (**38'-9" = 11.81 m** with 12 ft) |

Chosen: the Type 21 standard with the 12 ft arm SDE-101 allows on steel — 35 ft (10.67 m) pole, 3.66 m arm, lens at
38'-9" (11.81 m) over the road datum. Honest note: the City's own drawing tops out at 30 ft (9.14 m) for its largest
lamp; 11.81 m is the state-highway practice for a 4–6 lane arterial and the top of what Kevin asked for (35–40 ft). The
2026-10 lamp's light stood 6.94 m (ledger 0043) — 6.61 m over the nearest road vertex on today's road.

**The switch.** `track.config.json` `scenery.streetlights` = `{model: "led_cobra", arms: 2}`. Rollback = one key:
`model: "street_lamp_2026_10"` (Kevin's decimated Street_Lamp, byte-for-byte the v0.18.0 author path; the old OBJs stay).
`arms: 2` keeps the configuration every 2026-10 lamp has (back-to-back heads; only the road-ward one is lit, as before);
`arms: 1` = the single cobra head (~204 render points).

**Measured on the full rehearsal** (no `--skip-blend`; fresh copies of k10-sd-v021/project and engine-july on
D:/k10-scratch/lamp; `--no-install`):

| | v0.18.0 (installed) | LED lamp |
|---|---|---|
| road kn5 | 116.3 MB (116,304,573 B) | **72.7 MB** (72,676,095 B), −37.5 % |
| road kn5 verts / tris | 1,697,179 / 2,026,253 | **818,510 / 1,198,357** |
| LIGHTPOST | 17 meshes, 966,725 verts (57.0 %), 899,835 tris; 8 meshes at the 65,535 cap | **15 meshes, 87,403 verts (10.7 %), 71,700 tris; largest 5,914 — none near the cap** |
| render points per lamp | 4,045 + 3 (marker) | **365.7 + 5.7 (lens) = 371** (9.2 %) |
| LIGHTS | LIGHTS_0, 717 v (2 cm markers) | LIGHTS_0, 1,370 v (239 flat lenses) |
| `[LIGHT_n]` | 243 (239 lamps + 4 coincident pairs, ledger 0043) | **239**, one per lamp (ext_config's clustering fixed, GATES-CHANGELOG) |
| `[LIGHT_n]` keys | COLOR 255,165,30,0.013 … | identical in every block; `[MATERIAL_ADJUSTMENT_STREETLIGHTS]` and `[LIGHT_POLLUTION]` identical |
| `[LIGHT_n]` positions | — | each = its v0.18.0 light + **2.440 m road-ward, 4.718 m up** in the lamp's frame (written: 2.424–2.457 / 4.710–4.720, along ±0.017; recorded in `data/lights.local.json` `provenance` with every lens) |
| light over the nearest road vertex | 6.61 m median (p10–p90 6.50–6.65) | **11.33 m** (11.21–11.37); lens 11.48 m |
| verify_race G mast margin | 2.364 m (mast r 0.585) | 2.825 m (mast r 0.124), 0 inside |

Every gate equal to v0.18.0: street soft top 33 / severe 0 / kinks 3.41 / audit 53 (K 20, I 20, F 13); race severe
22 / 20, kinks 6.23 / 7.05, no_route PASS both (leak 0, reached 139,148 / 138,847 m²), barrier_missing 0, obstruction 0;
verify_mouths, verify_fold_fans, verify_ai_line (both), verify_signs (23 posts), verify_race + `--scenery-only`,
rib_check, house_seat_check PASS — the reports identical to v0.18.0's but for paths, timings and the G lamp margin.
(The chain exits 1 / NOT INSTALLED exactly as v0.18.0 did: the street drive_test / audit inherited reds.)

**The light, on the road** (`tools/streetlight_pool.py`, CSP's documented range / spot / diffuse terms; GATES-CHANGELOG):
under each lamp 0.97× (1.00× lamp for lamp — the 3 % is the four doubled lights gone); between lamps dark as before
(5 % → 3 % of mid-block stations lit) → **intensity stays 0.013, colour / cone / softness untouched**. What a higher
source does change: the pool flank 8–14 m out is 1.15–1.45× brighter and the lit road 1.42–1.67× on average, the range
sphere's ground radius 24.0 → ~22 m. If Kevin's seat reads it as brighter: 0.0091 matches the road average; `range_m`
26.7 restores the footprint.

**Stills** (Blender Eevee of the exported road scene; night = the lens's ext_config emissive + a spot at every written
`[LIGHT_n]`, indicative only): D:/k10-scratch/lamp/stills/street_day.png, street_night.png, lamp_closeup_day.png,
lamp_closeup_night.png.

**Open — Kevin's seat:** the look, load time and FPS (half the road kn5's vertices are gone); whether the back head
should stay (arms 1); whether the brighter flanks want 0.0091.

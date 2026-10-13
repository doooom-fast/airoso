---
id: 0053
title: "i'd like the race curbs to be tire-worn/textured" — the race kerbs were a 771-byte, two-colour picture with no grain, wear or bump map; now a generated worn atlas with rubber where tyres run, and an opt-in wheel kerb effect
status: diagnosed
scope: tracks/san-diego-lake-murray (race_cw, race_acw: the 8 common 1KERB_race_* kerbs in <slug>_race.kn5); tools/{race_furniture,author_race_furniture_blend,check_race_kn5,make_kerb_texture}.py; scripts/ac/pbr.py (the 1KERB_RACE row + its KS_PROPS row only; airoso + the engine-july snapshot, engine-july itself at integration); scripts/ac/track_folder.py (opt-in kerb_ff_effect, default byte-identical fleet-wide); assets/textures/kerb_race_worn_{diffuse,normal}.jpg + assets/licenses.json
layer: project + engine
train: -
---

## Status

Fix implemented and rehearsed on a scratch copy of the v0.17.1 workshop (branch of this commit). **Not installed.**
It reaches the game only through the integration run (the engine-july mirror below) and closes on Kevin's drive.

## Symptom

Kevin, 2026-10-12, from the seat, on the installed v0.17.1 race layouts, verbatim:

> "i'd like the race curbs to be tire-worn/textured"

Same round: "the track width and race track layouts are incredible" (keep the corridor model) and "i didn't notice
anything off other than jackson/navajo". This is a presentation request, not a defect report: the kerbs' position
and height are not in question.

## Evidence

Installed build, repo inspectors only (`scripts.modkit.inspect_kn5 --materials`):

| | Installed race kerbs | Installed race K-rail (for contrast) | Kunos Laguna `red_curb` (technique only) |
|---|---|---|---|
| meshes | 8 `1KERB_race_*`, 7,050 v, 6,984 tri, 469 m² | 15 strips | — |
| shader | **ksPerPixel** | ksPerPixelMultiMap | ksPerPixelMultiMap |
| textures | **txDiffuse=kerb_diffuse.png only** | txDiffuse + txNormal | txDiffuse + txNormal + txMaps + txDetail |
| params | ksDiffuse 0.4 / ksAmbient 0.4 (add-on defaults: no KS_PROPS row) | same defaults | ksAmb 0.3, ksDiff 0.3, ksSpec 0.35, EXP 20 |

- `kerb_diffuse.png` in the race kn5 is **771 bytes**: 256×256, exactly two colours. With v = arc / 1 m it painted
  **0.5 m red / 0.5 m white** blocks with no grain, joints, chips or rubber. The same file is the generic `1KERB`
  row's texture for every circuit track, so it could not be changed in place.
- No owned kerb texture exists (fleet/reference/ASSET-LIBRARY.md has none; assets/licenses.json only the stripe).
- The wrap was a mirror image on the three R-side (inside) kerbs: tangent handedness + on L, − on R. A kn5 vertex
  stores a tangent with no handedness sign (extract_kn5.py:9), so a bump map would have read inverted on one side.
- Both race directions drive every kerb (barrier_bands: whole/box at every kerb vertex; race_cw increasing, race_acw
  decreasing). The AI drafts never touch a kerb (clearance ≥ 1.04 m), so the wear comes from corner geometry.
- Feel: installed surfaces.ini KERB `FF_EFFECT=0`, VIBRATION 1.0 × 1.5, kerb.wav@1.3, FRICTION 0.92 (track_folder
  hard-coded FF_EFFECT=0 on every surface). Installed references: FF_EFFECT=1 on ks_vallelunga, ks_silverstone,
  ks_laguna_seca, ks_brands_hatch, ks_red_bull_ring, ks_barcelona, imola, mugello; 0 on ks_zandvoort; absent on
  ks_highlands. KEY=KERB also covers the street `1KERB_sidewalk` (114,081 m² in the main kn5).

## Diagnosis

Nothing was broken: the kerbs were a placeholder paint job — one flat picture (`pbr.py` 1KERB_RACE row), no bump
map (so the exporter picked plain ksPerPixel), a 1 m tile of two flat colours. A kerb reads as real from the seat
through three things this lacked: block joints that catch the light (a normal map — a picture that tells the
lighting which way each bit of surface faces, so a flat plate shows grooves without any change of shape), chipped
and dirty paint, and black tyre rubber where cars ride it. Real rubber is not uniform: it sits on the lane half of
the kerb, at each direction's late apex on an inside kerb and where each direction runs wide on exit on an outside
kerb. One picture tiled every metre cannot put it there, so the wrap chooses, block by block, how much rubber each
metre shows.

## Fix (as built)

The geometry does not move by a millimetre: every kerb vertex, face and hard edge is what it was (rehearsal:
race_authored ring centres + frames identical for all 35 objects). Only the picture and the wrap change.

1. **The picture** — `tools/make_kerb_texture.py` (Pillow only, seeded, deterministic; CC0, assets/licenses.json
   "Worn race kerb (generated)"): `kerb_race_worn_diffuse.jpg` (567,921 B) + `kerb_race_worn_normal.jpg` (980,349 B),
   1024×2048. Four 256 px columns = rubber level 0..3 (8 px pad each side); down the image 8 m of kerb at 256 px/m —
   eight 1 m blocks, weathered red / white, a grime-filled joint at every block end, chips to the grey concrete on
   the lane-side ramp and beside the joints, dirt on the outer edge, rubber streaks drawn out along the kerb in the
   band tyres ride. Every column shares the same paint, chips and joints; level c's rubber is a superset of level
   c−1's, so a column switch only ever adds marks. Seamless along the kerb. Normal map in OpenGL convention like
   every other in assets/textures: joints are grooves, chips slightly lower, fine grain, rubber fills the grain.
   (A normal map is a picture that tells the lighting which way each speck of the flat plate faces, so a 1.5 cm
   joint can look cut in without moving any geometry. "OpenGL" means its green channel says "this speck leans
   toward the top of the picture"; the other common convention flips green, and a flipped map turns every groove
   into a raised ridge.) The first cut WAS flipped (see "Verify round 1"): fixed, and pinned by a pixel test.
2. **The binding** — `pbr.py` `"1KERB_RACE": ("kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg", 0.55, …)`
   + `KS_PROPS["1KERB_RACE"]` (0.40 / 0.40, specular 0.10, EXP 20). With a normal present the exporter picks
   ksPerPixelMultiMap with diffuse + normal — the path the race K-rail already renders through in game; no exporter
   change. `1KERB` and `1KERB_SIDEWALK` are untouched (every other track's kerbs and every street curb).
3. **The wrap** — `race_furniture` (pure): `kerb_wear` gives each span a rubber level from the corner (inside: lobes
   at PC + 0.6 arc and PT − 0.6 arc; outside: PT + 0.2 E and PC − 0.2 E); v runs along the kerb's **own** mid-line
   length (the hairpin's outside kerb is 119.9 m against 87.0 m of centreline — the old v used the centreline and
   squeezed or stretched the stripes), warped so every joint station sits exactly on a whole metre, and the column
   only changes there, inside the joint's grime line. u across the profile by real surface length; the 5 cm outer
   face (the kerb's back, which no tyre touches and no column paints differently) always wraps column 0, so a
   column change re-cuts only the ramp and the top. `KERB_V_SIGN`
   runs v backwards on the L kerbs so all eight share the prep's planar road wrap's handedness (tested in the Blender
   frame). `kerb_mesh` itself is unchanged (md5-pinned against HEAD). `author_race_furniture_blend._mk` writes the
   per-face-corner UVs (asserting validate() kept the faces) and race_authored.json records per kerb `wear`
   {m_by_level, seams, heavy_spans_m_from_apex} and a `kerb_atlas` census.
4. **The guard** — `check_race_kn5` `black_slots` (hard, both roles): every texture the race rows bind for the meshes
   present must be embedded with > 0 bytes and bound to the right slot. It FAILS the installed v0.17.1 race kn5 and a
   kn5 exported from an engine-july that lacks the new files (the L7 black slot).
5. **Feel (opt-in, Kevin's call)** — `track_folder.surfaces_ini(kerb_ff_effect=0)`: FF_EFFECT=<n> on the KERB block
   only, read from `track.config.json` `kerb_ff_effect`; absent = byte-identical (md5-pinned). Lake Murray does not
   opt in in this commit (its config is the integration run's). VIBRATION stays 1.0. The docstring's "the kerb mesh
   is already 3D-ridged" is corrected: the race kerb is a flat 5 cm plate with a 10 cm ramp.

Where the rubber lands on Lake Murray (metres of kerb at level 0 / 1 / 2 / 3; heavy = centreline metres from the apex):

| kerb | length (own / centreline) | metres per level | seams | heaviest rubber |
|---|---|---|---|---|
| 770_out (hairpin, L) | 119.9 / 87.0 | 86.2 / 10.1 / 8.8 / 14.8 | 9 | −59.1…−49.8 and +11.7…+15.9 (both exits) |
| 770_in (R) | 26.0 / 33.0 | 7.1 / 4.0 / 2.9 / 12.1 | 3 | −32.6…−17.0 |
| 1514_out (College/Navajo, L) | 55.4 / 33.6 | 34.2 / 7.6 / 6.9 / 6.6 | 6 | −17.6…−14.0, +13.9…+16.1 |
| 2319_out (Navajo/Jackson, L) | 59.8 / 39.0 | 34.8 / 8.0 / 6.3 / 10.7 | 6 | −18.4…−13.0, +16.4…+20.8 |
| 3297_out (Jackson/LMB, L) | 51.4 / 33.6 | 28.4 / 7.6 / 4.8 / 10.6 | 6 | −17.5…−12.7, +11.3…+16.3 |
| 3297_in (R) | 11.4 / 14.8 | 4.5 / 5.1 / 1.0 / 0.9 | 5 | +3.7…+6.1 |
| 0_out (seam, L) | 102.7 / 85.2 | 57.7 / 13.0 / 11.1 / 20.9 | 12 | −21.7…−12.1, +19.1…+29.3 |
| 0_in (R) | 22.5 / 29.2 | 6.5 / 1.8 / 2.0 / 12.3 | 4 | −8.1…+11.1 |

51 column seams; KERB render vertices 7,050 → 7,254 (4 per seam: the lip, the ramp-top edge on both its faces and
the top's outer edge; the outer face never changes column), inside the pre-registered ≤ 7,300.

Not done, by design: no kerb geometry change (L9 seat, audit K 154, drive_test unchanged); no txMaps / txDetail (the
exporter is held and would need new slots); no alpha rubber decal (a non-physical prefix the split and the content
guard refuse).

## Verify round 1 (2026-10-12): two findings, both fixed at their cause

1. **The normal map's green was flipped (DirectX, not OpenGL).** The verifier measured G ≈ 223 just above every
   joint and ≈ 33 just below: the lighting would have read each joint as a raised ridge, the opposite of the
   asphalt's cracks on the road beside it. Cause: Pillow's `ImageFilter.Kernel` flips a kernel upside down before
   applying it (its documented behaviour), and the vertical Sobel kernel was written as if it did not; the
   horizontal one is symmetric top-to-bottom, so red came out right by luck. Fix: `make_kerb_texture.normal_rg`
   with `SOBEL_GY` written for the flip; the normal map regenerated (980,349 B, md5 `8f4b343a…`; now G ≈ 36 just
   above a joint, ≈ 220 just below). The diffuse is byte-identical (`f599d4a7…`). New tests: a synthetic height
   ramp pins the convention, and every joint of every column is checked to be a groove in the render and in the
   committed JPEG (the first cut's file fails it).
2. **KERB render vertices 7,356 broke the diagnosis's pre-registered ≤ 7,300.** The first cut moved the line to
   "7,050 + 6 × seams" after measuring. Cause: a column change re-cut all 6 render vertices of its station row,
   including the two on the kerb's 5 cm outer face, a face no column paints differently (rubber stops at 60 % of
   the profile; the outer face is 95–100 %). Fix: the outer face always wraps column 0 (`KERB_OUTER_FACE_COLUMN`,
   pixel-identical, tested), so a seam costs 4 (`KERB_SEAM_RENDER_VERTS`): 7,050 + 4 × 51 = **7,254**, measured in
   the rehearsed kn5. The rubber placement, the 51 seams and every wear number above are unchanged; the test is
   back on the pre-registered 7,300.

## Integration (held files — the merge run does these; nothing here edited them)

1. **engine-july** (it runs the prep and the export): `cp` airoso `scripts/ac/pbr.py` → `ENG/scripts/ac/pbr.py`
   (md5 `dc3f92527866bfb869e6c3670f08104f`, the CRLF working copy, same convention as today's `d3bbe940…`), and
   `assets/textures/kerb_race_worn_{diffuse,normal}.jpg` (md5 `f599d4a7…` / `8f4b343a…`; the normal map is the
   verify-round-1 regeneration, NOT the first cut's `38f2527a…`) → `ENG/assets/textures/` (or
   `python tools/make_kerb_texture.py --out-dir C:/Users/Owner/Documents/GitHub/engine-july/assets/textures`).
   **Before the prep**, not only before the export: the prep packs the images into `blender/<slug>.blend` and the
   add-on embeds the packed bytes — a re-export from a stale split shipped the old pixels in this rehearsal.
   Without the copy the kerbs render black (L7); `check_race_kn5` now FAILS that kn5.
2. `tools/snapshot_engine_july.py` (held): run it after step 1 so MANIFEST.md5 (pbr.py; this branch already wrote
   the new md5 into that one line) and REFERENCED.md5 (+ the two new textures) are regenerated.
3. `tests/tools/test_engine_july_snapshot.py:85` (held): `'"1KERB_RACE": ("kerb_diffuse.png"'` →
   `'"1KERB_RACE": ("kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg"'`.
4. `tests/tools/test_ship_sd_chain.py:281` (held): the literal set →
   `{"kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg", "concrete_barrier_diffuse.png", "concrete_barrier_normal.png"}`.
5. `tracks/san-diego-lake-murray/track.config.json` (held), only if Kevin says yes to Q1: top-level
   `"kerb_ff_effect": 1` with `"_kerb_ff_effect_doc": "ledger 0053: FF_EFFECT=1 on the KERB surface (Kunos
   convention, 8 of 10 references). KERB also covers 1KERB_sidewalk, so the sidewalks get the wheel kerb effect too"`.
6. `tools/ship_sd.sh`, `scripts/ac/export_kn5_addon.py`: no change needed (the common-race check step already runs;
   a normal present already selects ksPerPixelMultiMap).
7. Optional: fleet/reference/MEASURED.md — the KERB FF_EFFECT row above beside "Kerb recipes";
   tracks/san-diego-lake-murray/README.md — one line that the race kerbs bind `kerb_race_worn_*`.

## Scope

Lake Murray race_cw + race_acw: the 8 common kerbs. The street layout, the main kn5 and every other track are
unchanged: `kerb_mesh` md5-pinned, the 1KERB / 1KERB_SIDEWALK rows pinned, `surfaces_ini()` default md5-pinned, the
KS_PROPS row matches only `1KERB_RACE*` names. Proof corners: the 770 hairpin and Jackson/LMB (3297).

## Verification (decided before the fix)

1. **Pure tests** — PASS (tests/tools/test_kerb_wear.py, test_make_kerb_texture.py, test_check_race_kn5.py,
   tests/ac/test_pbr_race_rows.py, test_road_surface.py): kerb_mesh byte-identical to HEAD; on every SD kerb v
   continuous, u inside its column's pad, every level change on a whole-metre joint, blocks within 0.25 m of real
   length, one handedness (+1, the planar road wrap's) on all eight; every outside kerb heavy on both sides of the
   apex and never within ±5 m of it; 770_in and 0_in ≥ 10 m (centreline) of level 3 (15.6 / 19.2); 51 seams ≤ 60;
   **KERB render verts ≤ 7,300** (the threshold fixed here before the fix: 7,254 = 7,050 + 4 × 51, exactly 4 per
   seam); textures 1024×2048, ≤ 2 MB, deterministic, columns equal wherever level 3 has no rubber, the outer face
   identical in every column, **the normal map OpenGL (a synthetic ramp) and every joint a groove (G < 128 just
   above it, > 128 just below, render and committed JPEG)**, committed files = the generator's; pbr rows;
   surfaces_ini default md5 and the one-line opt-in; the guard fails a missing / empty / mis-bound kerb texture.
2. **Rehearsal** (scratch) — author: positions identical; `verify_race` OK (kerb under_road 0). Prep → split →
   `<slug>_race.kn5`: **10,253,676 → 11,811,590 B (+1,557,914 B, +15.2 %; ≤ 13 MB)**; `check_race_kn5 --role common`
   OK with exactly {kerb_race_worn_diffuse.jpg 567,921 B, kerb_race_worn_normal.jpg 980,349 B (md5 = the committed
   file), concrete_barrier_diffuse.png, concrete_barrier_normal.png}; all 8 kerb materials ksPerPixelMultiMap,
   txDiffuse + txNormal, ksSpecular 0.1 / EXP 20; KERB 7,254 render verts (the pure estimate exactly, ≤ 7,300); in
   the kn5 every column split sits on a whole-metre joint, every outer-face vertex is in column 0, all 8 kerbs one
   wrap handedness; kerb positions + triangles identical to installed v0.17.1, walls identical but for tangents
   (≤ 1.8e-7). Not run here (the
   integration run's full rehearsal): drive_test / audit / kn5_ground_check on the built race OBJs — no input of
   theirs changed.
3. **Eyeball** — Blender 4.2 Cycles stills at driver height (scratch/round2/kerbs/stills/): the 770 hairpin outside
   kerb at noon and at a low sun, College/Navajo (1514), Jackson/LMB (3297) outside and inside. 1 m blocks, grime
   joints, chips on the ramp lip, rubber on the lane half at the exits; no black kerb; no visible column line.
   Blender resolves wrap handedness per vertex, so the stills cannot show the AC groove/ridge question — that rests
   on the handedness test (same as the road's) and on the drive.
4. **Kevin's drive closes it**, in his words.

## Open questions for Kevin

- **Q1:** the wheel kerb effect (`kerb_ff_effect: 1`): on, knowing the street sidewalks share the KERB surface and
  would rumble in the wheel too?
- **Q2:** how dirty — the four rubber levels and how dark level 3 is are a guess; the stills go to him first.

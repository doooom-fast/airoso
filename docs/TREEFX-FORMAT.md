# TreeFX + GrassFX vegetation — verified format & emitter

The kn5 exporter is Blender-on-Windows. This is the **Mac-native** alternative for *foliage*: instead
of baking billboard/OBJ tree meshes into the kn5, we generate the CSP (Custom Shaders Patch) config
that makes AC render real **TreeFX** 3D trees at runtime, plus a **GrassFX** block.

- **Emitter:** `scripts/environment/treefx.py` (pure stdlib — runs on Mac system python, no bpy/numpy).
- **Producer:** `scripts/environment/build_env.py` (gated by `scenery.treefx.enabled`) writes
  `data/treefx.json`.
- **Consumer:** `scripts/ac/ext_config.py` renders `extension/trees/trees.txt` + the `[TREES]` /
  `[GRASS_FX]` sections.
- **Tests:** `tests/environment/test_treefx.py`, `tests/ac/test_ext_config_treefx.py`.

> **VERIFY IN-GAME.** CSP config keys drift between versions. The `trees.txt` line grammar below is
> validated against docs *and* a real pack and is stable; the `[GRASS_FX]` appearance keys are a
> conservative, documented starting point — confirm on the first Windows drive.

---

## Licensing — reference, don't bundle (CRITICAL)

The actual `.bin` tree **models** are third-party, licensed, and **user-supplied**. prodrive-ac-builder
**never downloads or commits** them. Everything we emit only *references* a species by its `.bin`
**filename**; the config we generate (`trees.txt` + the ext_config `[TREES]` block) is ours and
license-clean.

- `.bin` models are gitignored (`*.bin`) and dropped by the user into `extension/trees/` locally.
- Every build **logs which `.bin` filenames it expects** and writes an `extension/trees/README`
  manifest, so nothing is guessed.
- A **missing** model is harmless — its `tree:` lines simply render nothing until the file is present.

---

## `extension/trees/trees.txt` — the tree list

Plain text, **one directive per line**, order-sensitive. Comments start with `;`.

### `tree:` line

```
; simple form — filename first, then position:
tree: MRS_pine_high_2_1.bin; 12.5, 2103.4, -55.2

; extended form — position tagged pos=, then optional key=value params:
tree: pine.bin; pos=12.5, 2103.4, -55.2; angle = 137; size = 3.2; width = 0.9; color = 1, 1, 0.9
```

| Field | Meaning |
|-------|---------|
| `<model>.bin` | **First**, terminated by `;`. This filename **is** the species id. |
| `X, Y, Z` | Position, **metres**, AC/kn5 world space, **Y = UP**. Simple form omits `pos=`; extended form writes `pos=X, Y, Z`. Trees auto-snap vertically onto `SURFACE_MATERIALS`, so `Y` may be approximate — we emit the real ground `Y` anyway. |
| `angle = <deg>` | Yaw in **degrees**, 0–360. |
| `size = <mult>` | Uniform size multiplier (`1` = the model's native size). |
| `width = <mult>` | Width-only multiplier (`1` = native). |
| `color = R, G, B` | RGB **multiplier** (`1, 1, 1` neutral; may exceed 1). |

Each optional param is preceded by its own `; ` separator, `key = value` with spaces around `=`.

### `configure:` line — per-zone defaults

`configure:` sets a default for **every tree that FOLLOWS** it (until the next `configure` for the same
key). Use it for natural variation instead of hand-jittering every line.

```
configure: seed = 42
configure: size variance = 0.9, 1.1        ; each following tree scaled by a random factor in [0.9, 1.1]
configure: angle variance = 0, 360         ; each following tree yawed randomly in [0, 360)
```

The emitter groups the list **per zone**: a `; --- zone ... ---` comment, the zone's `configure`
lines, then its `tree:` lines.

---

## `ext_config.ini` `[TREES]` section

```ini
[TREES]
LIST_0 = trees/trees.txt
SURFACE_MATERIALS = 1GRASS_mat, 1ROAD_main_mat, 1ROAD_shoulder_mat
SURFACE_MESHES = 1GRASS
; COMPILED_LIST = compiled_trees.bin   ; optional baked VAO — external bakery, not required
```

| Key | Meaning |
|-----|---------|
| `LIST_0`, `LIST_1`, … | Text lists relative to `extension/`. Numbered for multiple lists. |
| `SURFACE_MATERIALS` | **This track's real** surface material names (grass + road). Trees snap vertically onto these and align lighting to them. Read from the build's material names (`pbr.py` names materials `<obj>_mat`) — **never** hardcode another track's. |
| `SURFACE_MESHES` | *(optional)* mesh names, same purpose as `SURFACE_MATERIALS`. |
| `SEASON_AUTUMN_0` / `SEASON_WINTER_0` | *(optional)* seasonal CONDITION names. Skipped in v1. |
| `COMPILED_LIST` | *(optional)* the baked binary VAO produced later by the external bakery running AC headless — **not** produced here, **not** required. Emitted **commented-out**; the text list loads directly in-game. |

---

## `ext_config.ini` `[GRASS_FX]` section

Written in the grammar **every shipped CSP track config uses** (census 2026-10-10 of 73 third-party
inis + 19 CSP-bundled `loaded/*.ini` on this machine, ledger 0045), bound to **our** mesh/material
names. Gated per-track by `lighting.grassfx` (default **off** — over a huge network the occlusion
field can bust the GPU watchdog and freeze the PC): `true` = the minimal block below; a dict = the
tuning keys in the table; `{}` is OFF (truthiness — the documented gotcha); `{"enabled": false, …}`
switches a tuned dict off without losing it. Keys beginning with `_` are documentation; **any other
unknown key fails the build** (L2) — including the retired `brightness`, `health` and
`texture = grass_fx/grass_ks.dds`.

What `lighting.grassfx = true` emits (the la_canyons / fn_bahrain minimal form; no `TEXTURE` line
means CSP's built-in atlas):

```ini
[GRASS_FX]
GRASS_MATERIALS = 1GRASS_mat
GRASS_MESHES = 1GRASS
OCCLUDING_MESHES = 1ROAD_main, 1ROAD_shoulder, 1KERB_corners, BUILDING, HOUSE
ORIGINAL_GRASS_MATERIALS =
; mask: colour-gated (colorado-2013 quartet) - blades only where the ground texel reads as grass
MASK_MAIN_THRESHOLD = 0.5
MASK_RED_THRESHOLD = 0.05
MASK_MIN_LUMINANCE = 0.02
MASK_MAX_LUMINANCE = 0.35
; shape: blade size multiplier (1 = CSP default); 'a, b' pairs are a per-blade range
SHAPE_SIZE = 0.9
```

A tuned dict (Lake Murray V3: one look, weekly-mown irrigated turf, mask opened because both
terrain tiles are 100% grass):

```jsonc
"lighting": {
  "grassfx": {
    "mask": "open",                       // -1 / 0 / -1 / 1: blades on every texel of the listed grass
    "shape_size": [0.7, 1.1],             // 'a, b' pairs span TRIM_PERIOD (just cut -> fully grown)
    "shape_width": 0.6, "shape_tidy": [1, 0.6], "shape_cut": [1, 0.5],
    "trim_period": "THURSDAY",
    "texture": "grass_fx/highlands.dds", "texture_grid": [8, 3]
  }
}
```

| Ini key | Config key | Meaning |
|-----|-----|---------|
| `GRASS_MATERIALS` | — (derived) | Our grass **material** names (`<mesh>_mat`); the key 23/23 third-party configs use. Always emitted. |
| `GRASS_MESHES` | — (derived) | Our grass **mesh** names (`1GRASS*` / `1LAWN*`); wiki-documented, CSP's own Nordschleife override uses it. Same geometry bound a second way. Always emitted. |
| `OCCLUDING_MESHES` | — (allow-list) | **ALLOW-LIST** of ground-seated solids the grass must not grow through (road / kerb / runoff / markings / building + house footprints / water), from `OCCLUDE_PREFIXES` in `ext_config.py`. Never far-field/oversized meshes (mountains, elevated decks) or thin props/foliage — an over-broad list explodes the occlusion volume at load and freezes the PC (shipped bug, v0.12.x). Omitted when empty; **no per-track add list exists**, by design. |
| `ORIGINAL_GRASS_MATERIALS` | `original_grass_materials` | Stock ksGrass-shader grass to hide while GrassFX is on. Default empty — but the line is always written: a *missing* line hides every ksGrass object. |
| `TEXTURE`, `TEXTURE_GRID` | `texture`, `texture_grid` | Blade atlas + its `cols, rows`. Only when set; `grass_fx/highlands.dds` 8×3 is embedded in CSP (no file on disk). A custom atlas ships beside `ext_config.ini`; the writer copies nothing. Set automatically (with a note) when `texture_groups` is used. |
| `MASK_MAIN_THRESHOLD` / `MASK_RED_THRESHOLD` / `MASK_MIN_LUMINANCE` / `MASK_MAX_LUMINANCE` | `mask` preset + `mask_*` | Where blades spawn, keyed off the **ground texel** (blades take its colour). Preset `default` = 0.5 / 0.05 / 0.02 / 0.35 (colorado-2013, colour-gated); `open` = −1 / 0 / −1 / 1 (wiki spawn-everywhere). Each `mask_*` overrides its one line on top of the preset. |
| `MASK_BLUR` | `mask_blur` | 0–3, clamped. Softens the mask for texture-driven patchiness. |
| `SHAPE_SIZE` | `shape_size` | Blade size (`1` = CSP default; fleet default `0.9`). Smaller = denser = costlier; keep ≤ ~1.2 where TreeFX bushes stand (la_canyons: tall blades swallow baked shrubs). |
| `SHAPE_WIDTH` / `SHAPE_TIDY` / `SHAPE_CUT` | `shape_width` / `shape_tidy` / `shape_cut` | Blade width (dry 0.5 … lush 1.0); tidy and cut `1 → 0.5` with a weekday `TRIM_PERIOD` = the mown idiom. |
| `TRIM_PERIOD` | `trim_period` | Weekday name (`THURSDAY`, mown weekly) or days (`365`, never). The shape pairs span it. |
| `HEIGHT_MULT`, `TEXTURE_BRIGHTNESS`, `COLOR_FACTOR` | `height_mult`, `texture_brightness`, `color_factor` | Shipped (fn_bahrain, Nords template, black_cat) but undocumented — passed through verbatim, **VERIFY IN-GAME**. `TEXTURE_BRIGHTNESS` is the only track-side lever if lamp-lit blades read neon at night (static; darkens day too). |
| `[GRASS_FX_TEXTURE_GROUP_n]` `PIECE_k = c, r[, w, h]`, `_CHANCE`, `_SIZE_MULT`, `_WIND` | `texture_groups: [[{piece, chance?, size_mult?, wind?}, …], …]` | Extra blade shapes from the atlas (row 0 = base blades, so rows 1+ matter; `(4,1,2,2)` is highlands' long-grass tuft). ≤ 4 groups × ≤ 8 pieces. |
| `[GRASS_FX_CONFIGURATION_A..D]` | `configurations: {"A": {…}}` | A look: any subset of the mask / blur / shape / trim / height keys plus `texture_base_chance` and `texture_group_chances: [...]` (→ `TEXTURE_BASE_CHANCE`, `TEXTURE_GROUP_n_CHANCE`). Letters A–D only (dwrite.dll carries exactly four). Chance keys are **not** accepted at `[GRASS_FX]` top level — to thin the base look, bind a configuration to all grass materials. |
| `[GRASS_FX_ADJUSTMENT_<name>]` `MATERIALS` / `MESHES` / `CENTER, SIZE, ANGLE, FADE` + `MAP` | `adjustments: [{name?, map, materials | meshes | rect: {center, size, angle?, fade?}}]` | Binds a configuration by material, by mesh, or by a world rectangle (**kn5 frame** — z-mirrored vs the gate OBJ; the writer does not convert). `map` = `"A"` \| `"A, 0.5"` \| `"wA, wB, wC, wD"`; a letter must exist in `configurations`. Default name `...` = CSP auto-index. |

**Retired, never emitted:** `[GRASS_FX_TEXTURE_0]`, `[GRASS_FX_CONFIGURATION_0]`, `MATERIALS` inside
a configuration, `BRIGHTNESS`, `HEALTH`, `grass_fx/grass_ks.dds` — the earlier writer's block, which
matched none of the 90+ configs read and whose texture existed nowhere (not even inside
`dwrite.dll`), so enabling it drew CSP defaults at best. The six installed Colorado inis still carry
it until their next regeneration.

**Known degradation:** `ext_config` reads the *previous* run's `data/track.obj` (the gate OBJ is
rewritten after it); with no OBJ at all the lists are placeholders (`1GRASS`) and the writer now says
so loudly. Regenerate after the gate OBJ exists.

---

## Config schema — `track.config.json` → `scenery.treefx`

```jsonc
"scenery": {
  "treefx": {
    "enabled": true,                     // OFF => baked billboard/OBJ foliage (unchanged legacy path)
    "seed": 20260724,                    // emitted as `configure: seed` per zone
    "surface_materials": null,           // override; null => ext_config derives grass+road materials
    "surface_meshes": [],                // optional [TREES] SURFACE_MESHES
    "compiled_list": "compiled_trees.bin",  // optional; emitted commented-out
    // (no "grassfx" here: ext_config never reads it; lighting.grassfx is the ONLY GrassFX gate)

    "zones": {                           // keyed by name; a build_env placement `source` -> one zone
      "<zone-name>": {
        "source": "fill_terrain",        // poly_scatter | fill_terrain | forest3d | creek | bush
        "species": ["a.bin", "b.bin"],   // .bin filenames mixed within the zone (drop-in a new one to fill it)
        "weights": [0.7, 0.3],           // optional species weights (default uniform)
        "size_variance": [0.85, 1.15],   // optional -> `configure: size variance`
        "angle_variance": [0, 360],      // optional -> `configure: angle variance`
        "color": [1, 1, 1],              // optional per-tree color multiplier
        "band_m": 24.0,                  // creek zones: max distance from the water polyline
        "density": {
          "by": "elevation",             // elevation | constant
          "elev_lo_m": 1750, "elev_hi_m": 2100,   // elevation ramp (keep rises lo->hi)
          "keep_lo": 0.2, "keep_hi": 1.0, "curve": 1.4,
          "aspect_bonus": 0.25, "aspect_favored": ["N", "E"]   // N/E slopes denser
          // ("by": "constant" uses a single "keep": 0.8 instead)
        }
      }
    }
  }
}
```

### Sources (which build_env foliage loop feeds a zone)

| `source` | build_env loop | Notes |
|----------|----------------|-------|
| `poly_scatter` | OSM green/wetland polygon scatter | urban green islands |
| `fill_terrain` | continuous forest band swept along the whole lap | **mountain tracks** (Lariat) |
| `forest3d` | near-corridor real-geometry trees | carries per-tree `size` (scale) + `angle` (yaw) |
| `creek` | riparian band along OSM water polylines | respects `band_m`; already water-gated |
| `bush` | trackside shrub scatter | San Diego palm/bush |

A source with **no** zone plants nothing under TreeFX (the baked billboard is not built either). The
legacy baked-mesh path is used unchanged when `treefx.enabled` is false.

### Density model

- `elevation`: keep-probability rises **monotonically** with `Y` — `t = clamp((y − elev_lo) / (elev_hi
  − elev_lo))`, shaped by `t ** curve` (`curve > 1` keeps low slopes barer), lerped `keep_lo → keep_hi`.
  Sparse at the low end, thick toward the summit.
- `aspect_bonus`: extra keep on slopes facing a favored compass direction. **Convention: +X = East,
  North = −Z.** N/E slopes hold more moisture (northern hemisphere) → denser conifer forest. The bonus
  scales with slope strength; flat ground gets none. build_env samples the aspect from `ground_y`.
- `constant`: a single `keep` probability (creek/urban zones are already spatially gated by their loop).

---

## Per-track density models

### Lariat (mountain) — the concrete first target

`source: fill_terrain`, `density.by: elevation` (sparse at the low Golden end ~1750 m, thickening
toward the summit ~2100 m; N/E slopes denser). Species = the pack conifers mixed by filename:
`MRS_pine_high_2_1.bin`, `MRS_Sapin_3_0_high.bin`, `MRS_Sapin_4_0_high.bin`, `treePine1`.

**Real generated sample** (deterministic, `seed = 20260724`, a short climbing stretch — note the
density rising with `Y`):

```
; --- zone 'forest' (fill_terrain): 28 trees, species=MRS_pine_high_2_1.bin/MRS_Sapin_3_0_high.bin/MRS_Sapin_4_0_high.bin/treePine1 ---
configure: seed = 20260724
configure: size variance = 0.85, 1.15
configure: angle variance = 0, 360
tree: MRS_Sapin_4_0_high.bin; -766, 1774.11, 328.9
tree: treePine1; -766, 1773.73, 263.98
tree: MRS_Sapin_3_0_high.bin; -766, 1771.82, 248.86
tree: MRS_Sapin_3_0_high.bin; -720, 1795.93, 284.63
tree: MRS_pine_high_2_1.bin; -674, 1818.49, 345.29
...
tree: MRS_Sapin_4_0_high.bin; -398, 1957.52, 288.38
tree: MRS_Sapin_3_0_high.bin; -398, 1957.37, 281.91
tree: MRS_pine_high_2_1.bin; -398, 1956.05, 247.57
tree: MRS_Sapin_4_0_high.bin; -398, 1955.97, 205.81
tree: treePine1; -398, 1956.64, 212.94
```

### Sand Creek — riparian band

`source: creek`, `band_m: 24`, `density.by: constant`. Dense trees within the band of the OSM creek
polylines (build_env already reads the water polylines for bridges — the same lines feed this). Species
= a riparian filename the user supplies, e.g. `cottonwood.bin` / `willow.bin`, plus light street trees
on the verges via a `poly_scatter` zone.

### San Diego — deciduous + palm + bush

Zones for deciduous (`poly_scatter`), a `palm.bin`, and a `bush.bin` (`source: bush`). Species
filenames come from config — drop a `.bin` filename into a zone's `species` to fill that zone.

---

## Data flow

```
build_env.build()   scenery.treefx.enabled
   └─ foliage loops record real positions -> TreeFXCollector (density + species)
   └─ writes data/treefx.json                (removed on a non-treefx rebuild)

ext_config.generate()
   └─ reads data/treefx.json
   └─ writes extension/trees/trees.txt + extension/trees/README (expected .bin manifest)
   └─ emits [TREES] (SURFACE_MATERIALS from the track's real materials) + [GRASS_FX]
```

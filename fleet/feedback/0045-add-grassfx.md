---
id: 0045
title: "add grassfx" — the writer's GrassFX block was in a grammar no shipped CSP config uses, and the occluder allow-list skipped BUILDING and HOUSE
status: diagnosed
scope: engine scripts/environment/treefx.py grassfx_block + scripts/ac/ext_config.py OCCLUDE_PREFIXES / lighting.grassfx gate (airoso canonical + engine-july mirror, md5-identical); tracks/san-diego-lake-murray (lighting.grassfx); fleet-wide every track with lighting.grassfx (lookout_lariat, sand_creek, imi, pueblo, second_creek, high_plains carry the old block as installed)
layer: engine + project
train: -
---

## Symptom (Kevin, 2026-10-10, on the installed `san_diego_lake_murray_v3`)

> "add grassfx"

The installed ini carried the writer's own `; GrassFX DISABLED` comment (lines 8–10): V3 shipped
with no 3D grass at all, flat irrigated-turf texture only.

## Evidence

**Read-only measurement, 2026-10-10** (three agents: writer map, 20 reference tracks on this
machine, CSP docs/texture/real-world research — `tasks/wt3ckdiw5.output`), not re-measured here.

**The writer's block was fiction.** `grassfx_block()` (`treefx.py`, byte-identical in airoso and
engine-july, md5 `bd4e9c58…`) emitted `[GRASS_FX] GRASS_MESHES / OCCLUDING_MESHES / MASK_* /
SHAPE_SIZE` plus a `[GRASS_FX_TEXTURE_0] TEXTURE = grass_fx/grass_ks.dds` section and a
`[GRASS_FX_CONFIGURATION_0] MATERIALS / BRIGHTNESS / HEALTH` section. Census of **73 third-party
track inis + 19 CSP-bundled `extension/config/tracks/loaded/*.ini`** with GrassFX on this machine:

| Writer emitted | Shipped configs using it |
|---|---|
| `[GRASS_FX_TEXTURE_0]` | **0** (`TEXTURE` / `TEXTURE_GRID` live in `[GRASS_FX]`; pieces in `[GRASS_FX_TEXTURE_GROUP_N]`) |
| `grass_fx/grass_ks.dds` | exists **nowhere** — not in the track's `extension/`, not in CSP's `extension/textures/`, not inside `dwrite.dll` (which embeds `highlands.dds` 8×3 and `generic.dds`) |
| `[GRASS_FX_CONFIGURATION_0]` with `MATERIALS` | **0** (configurations are lettered A–D and bound by `[GRASS_FX_ADJUSTMENT_...] MATERIALS/MESHES/rect + MAP`) |
| `BRIGHTNESS`, `HEALTH` | **0** |
| `GRASS_MESHES` | 0 of 19 CSP loaded configs; wiki-documented and used by CSP's own Nordschleife override |
| `GRASS_MATERIALS` | **23 / 23** third-party configs |

So enabling it as-is would have bound grass by one unverified key and drawn CSP defaults at best.
Every key the new block emits appears in the census: `GRASS_MATERIALS` (37 mentions),
`GRASS_MESHES` (5), `OCCLUDING_MESHES` (10), `ORIGINAL_GRASS_MATERIALS` (8), `TEXTURE` (74),
`TEXTURE_GRID` (16), the four `MASK_*` (15–24 each), `SHAPE_SIZE/WIDTH/TIDY/CUT` (56/11/27/27),
`TRIM_PERIOD` (20); the exact values `TEXTURE_GRID=8, 3`, `TRIM_PERIOD=THURSDAY`, `SHAPE_CUT=1, 0.5`,
`SHAPE_TIDY=1, 0.6`, `MASK_MAIN_THRESHOLD=-1` / `MASK_MIN_LUMINANCE=-1` / `MASK_MAX_LUMINANCE=1` are
all shipped verbatim (vhr_phoenix, fn_bahrain, la_canyons A, Nords-own, willow_springs).

**The occluder allow-list skipped two near-field footprints.** `ext_config.py:74-76`
`OCCLUDE_PREFIXES` had `"BUILDINGS"` (Sand Creek's plural) and no `HOUSE`; V3's gate OBJ
(`k10-sd-v021/project/data/track.obj`, 28 groups = the 28 kn5 meshes) names them `BUILDING`
(1,637 verts, X −2174..452 / Z −1591..1774) and `HOUSE` (10,335 verts, X −2078..2532 / Z
−1740..1787) — both inside the 1ROAD lap extent, so blades would grow through every house pad on
the Del Cerro front yards. The writer's rule yielded `1KERB_sidewalk, 1ROAD_road, MARKINGS_0,
MARKINGS_1` (4,698 × 3,413 m, 140,338 verts); with the two added the envelope is 4,805 × 3,527 m /
~152k verts — still exactly the lap, nothing elevated, nothing far-field, against the v0.12.x
crash's 24,000 × 1,450 m MOUNTAINS backdrop. Every dry-track author in the census lists building
floors/walls (nohesi `?Building?`, Targa `building_01_d`, PCH `mansion_foundations`); nobody lists
guardrails, lamp posts or markers, so `1WALL_guard`, `LIGHTPOST_0..8`, `LIGHTS_0`, `YLINE` stay out.

**What the ground is.** `1GRASS_0_mat` / `1GRASS_1_mat` (verified by parsing the installed kn5)
carry `grass_diffuse.jpg` = Kevin's irrigated-green `texture_overrides` (mean sRGB 68,92,40). CSP
blades take the colour of the ground texel under them, so v1 can express exactly one look — mown
irrigated turf — which is right within ~10 m of the kerb (1963–69 permit cards' 10 ft planting
strips, median decks, Kiowa Dr park) and wrong on the reservoir slopes (annual oats/brome, straw
8–9 months a year) in exactly the way the ground texture is already wrong.

**TDR.** Grass set 2 meshes / 77,948 verts / 27.9 km² bbox (the 1GRASS_0 terrain skirt reaches
2.6–3.3 km past the loop); occluders 6 near-field meshes. nohesi (91 grass meshes, 622 occluders
incl. a 39 × 100 km card), la_canyons (169 meshes, 910 km²) and Hamburg (7.7 M occluder verts) all
run on this PC; CSP's `grass_fx.ini` generation maps are camera-local (1024 px × 0.25 m at
QUALITY 2). Judged low.

## Diagnosis

Two engine defects, one project opt-in. (1) The GrassFX writer was written from a template nobody
had checked against a shipped config — L2's "stale config silently produces a different track"
class, here "fictional grammar silently produces no grass". (2) The allow-list's prefix table was
spelled for Sand Creek's mesh names and never widened for the Blender-authored loop tracks' singular
`BUILDING` / `HOUSE`. (3) V3 never opted in (`lighting.grassfx` absent).

## Fix — config-only install, no kn5, no loop.blend (landed 2026-10-10, uncommitted)

1. **Engine — `scripts/environment/treefx.py` `grassfx_block()`** (signature unchanged; airoso
   first, cp to engine-july, md5 `15a33d0a…` both): emits the shipped grammar — always
   `[GRASS_FX]` with `GRASS_MATERIALS` + `GRASS_MESHES` (same geometry bound both ways, so a wrong
   assumption about either binding path still spawns), `OCCLUDING_MESHES` (only when non-empty),
   `ORIGINAL_GRASS_MATERIALS =` (a missing line hides every ksGrass object), the four `MASK_*`
   lines (preset `default` = colorado-2013's 0.5/0.05/0.02/0.35, `open` = −1/0/−1/1) and
   `SHAPE_SIZE` (default 0.9); only when the config asks: `TEXTURE` + `TEXTURE_GRID`, `MASK_BLUR`,
   `SHAPE_WIDTH/TIDY/CUT`, `TRIM_PERIOD`, `HEIGHT_MULT`, `TEXTURE_BRIGHTNESS`, `COLOR_FACTOR`,
   `[GRASS_FX_TEXTURE_GROUP_n]`, `[GRASS_FX_CONFIGURATION_A..D]`, `[GRASS_FX_ADJUSTMENT_...]` by
   materials / meshes / rectangle. Comments own-line only. `_`-keys skipped; any other unknown key
   and the retired `brightness` / `health` / `grass_ks.dds` raise `ValueError`. A bare `true`
   stays minimal: versus the old block the two fictional sections vanish, `GRASS_MATERIALS` and
   `ORIGINAL_GRASS_MATERIALS` appear, the `SHAPE_SIZE` trailing comment goes, every other line
   byte-identical.
2. **Engine — `scripts/ac/ext_config.py`** (md5 `ee7bb5f5…` both copies; the street-light,
   light-pollution and TreeFX paths untouched): `OCCLUDE_PREFIXES` `BUILDINGS → BUILDING` (prefix,
   so `BUILDINGS` and `BUILDING_a..` still match) and `HOUSE` added, with the near-field
   justification in the comment; `lighting.grassfx = {"enabled": false, …}` takes the OFF branch
   (`{}` stays OFF by truthiness, documented); a loud note when no gate OBJ exists and the GRASS
   lists are placeholders. Recorded in `fleet/GATES-CHANGELOG.md` (it is the crash guard).
3. **Project — `tracks/san-diego-lake-murray/track.config.json`** `lighting.grassfx`: `mask open`,
   `shape_size [0.7, 1.1]`, `shape_width 0.6`, `shape_tidy [1, 0.6]`, `shape_cut [1, 0.5]`,
   `trim_period THURSDAY`, `texture grass_fx/highlands.dds`, `texture_grid [8, 3]`, with the ladders
   in its `_doc` (sparser/denser size bands, a tuft group + configuration A for "golf course"
   uniformity, mask `default` + blur for patchiness, `texture_brightness` for neon at night,
   `enabled false` to switch off without losing the tuning).
4. **Tests + docs** in the same commit: `tests/environment/test_treefx.py` (V3 golden byte-for-byte,
   open mask, groups/configurations/adjustments, rect adjustment, letter E / `brightness` /
   `shape_sise` / `grass_ks` → `ValueError`, `_doc` accepted, no empty `OCCLUDING_MESHES`),
   `tests/ac/test_ext_config_occluders.py` (`BUILDING`, `HOUSE` in; `LIGHTPOST_0` out;
   `enabled: false` emits no `[GRASS_FX]`); `docs/TREEFX-FORMAT.md` key table rewritten, the dead
   `scenery.treefx.grassfx` field retired (ext_config never read it). Both repos: 31/31 on the three
   files, full `tests/run_tests.py` 184/184 (airoso) and 178/178 (engine-july). `pytest` is not
   installed for the only interpreter (Python 3.14) and was not installed unasked — the repo's own
   dependency-free loader was used.
5. **Install** exactly as 0043: config → `k10-sd-v021/project/`, `python -m scripts.ac.ext_config`
   from engine-july (243 `[LIGHT_N]` re-clustered from the 2026-10-09 kn5; deletes `trees.txt`),
   `python tools/make_treefx.py` from airoso (`[treefx] 15261 trees`, `trees.txt` md5 `a0c7873d…`
   = the installed one), backup `ext_config.ini.pre-grassfx` (113,551 B, md5 `71c28358…` = the
   sodium install of 19:04), copy ONLY `extension/ext_config.ini`.

## Scope

- **Proof case:** `tracks/san-diego-lake-murray` → `san_diego_lake_murray_v3`.
- **Fleet fallout (not work now):** the six installed Colorado inis carry the fictional block and
  pick up the fixed writer on their next regeneration; the prefix change and the removed sections
  change their output textually, not their expected look — each its own unverified claim until driven.
- **Not in scope:** kn5, `loop.blend`, `tools/ship_sd.sh` (another workflow is editing it), the
  v0.23.0 release zips.

## Verification

**Measurable, done 2026-10-10 19:54 on the installed file** (114,621 B CRLF, md5 identical to the
workshop copy): the complete `diff -u` against `ext_config.ini.pre-grassfx` is the three `GrassFX
DISABLED` lines replaced by the 25-line block, nothing else; `[GRASS_FX]` once, no other
`GRASS_FX_*` section; 243 `[LIGHT_N]` blocks, `[LIGHT_POLLUTION]`, `[MATERIAL_ADJUSTMENT_STREETLIGHTS]`
and `[TREES]` byte-identical to the backup; everything from the RainFX header to EOF byte-identical
(5,403 lines); strict `configparser` parses 252 sections, no duplicates; `extension/trees/` untouched.

**Kevin's seat, decided before the drive**, with `san_diego_lake_murray_v3_locked` / `_v3_prev`
left as fallback launches, GrassFX QUALITY Medium, a short day session first with nothing unsaved:

- **Blades appear at all** — the only proof of the grammar. If not: CSP's `ENABLED`/`QUALITY` in
  `extension/config/grass_fx.ini`, then `APP_GRASSFX_DEBUG=1` to see the mask, then drop the
  `GRASS_MESHES` line (config-only).
- **None through house/building pads**, the road, sidewalks or markings; grass at the guardrail
  base is real and expected.
- **Reads as mown suburban turf** near the kerb and in the park; the reservoir slopes will be the
  same green — say before he drives that this is D1, not a v1 defect.
- **Night preset** (22:00 clear): blades under the 243 sodium cones may read neon; the only
  track-side lever is `texture_brightness` (static).
- Fallback: restore `ext_config.ini.pre-grassfx`.

**After Kevin approves:** commit the two writers (both repos), config, tests, docs, changelog and
this entry; move to `shipped`.

## Deferred (same mechanism, later)

- **D1 — straw slopes.** The reservoir slopes need a straw ground texture under the blades:
  `loop.blend` split of 1GRASS by zone (verge/parkway vs slope) + kn5 rebuild, then a colour-gated
  configuration B for the slope material (`SHAPE_SIZE 0.7–1.2`, `SHAPE_WIDTH 0.5`, `TRIM_PERIOD 365`,
  the dry mask band) — the writer already expresses all of it.
- **D2 — fleet regen.** Colorado's six installed inis: regenerate + drive on their next ship.
- **D3 — markings as alpha occluders.** `MARKINGS_0/1` stay hard occluders (redundant inside
  `1ROAD_road`); move to `OCCLUDING_MATERIALS_ALPHA` only once `MARKINGS_*_mat` is verified alpha.
- **D4 — the reservoir bed.** No WATER mesh exists in V3, so open-mask blades grow on the lake
  basin, far field and off-route. A config-only `[GRASS_FX_ADJUSTMENT]` rectangle with
  `TEXTURE_BASE_CHANCE 0` over the basin needs the lake's kn5-frame coordinates; a WATER mesh in
  `loop.blend` is the real fix.

**Side finding, own ledger line later:** the installed `[MATERIAL_ADJUSTMENT_LIT_WINDOWS]
MATERIALS = BUILDING_mat` names a material that does not exist in the kn5 (real names
`BUILDING_mat.001` / `HOUSE_mat.001` / `YLINE_mat.001`, Blender suffixes), so lit windows are
silently off. Unchanged by this entry.

## Status (2026-10-10 19:54) — installed, awaiting Kevin's day drive, then the night preset

Everything in **Fix** is in the airoso working tree uncommitted, mirrored to engine-july, and the
installed `san_diego_lake_murray_v3/extension/ext_config.ini` is the regenerated file with the old
one beside it as `ext_config.ini.pre-grassfx` (and 0043's `ext_config.ini.pre-sodium`). No
`loop.blend`, no kn5, no `trees/`, no `ship_sd.sh` touched.

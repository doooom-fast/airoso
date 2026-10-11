---
id: 0043
title: "Very harsh and very bright… more like sodium lights from the 80s" — a 255× intensity scale error, and Del Cerro's 80s lamps were low-pressure sodium
status: in-progress
scope: tracks/san-diego-lake-murray (lighting.streetlight, lighting.light_pollution); engine scripts/ac/ext_config.py streetlight writer (airoso canonical + engine-july mirror); fleet-wide every track that builds a LIGHTS mesh
layer: project + engine
train: -
---

## Symptom (Kevin, seat, 2026-10-10, on the installed `san_diego_lake_murray_v3`)

> "Can we do something about the lights? They're very harsh and very bright. And they need to be
> more like sodium lights from the 80s."

Second report in three days: 2026-10-08 was "way too bright" (ledger 0040), answered with
intensity 5.0 → 1.6 (commit 45b5a61). Kevin saw no change worth naming, and this entry explains
why he could not have.

## Evidence

**What Kevin drove** (`D:/SteamLibrary/steamapps/common/assettocorsa/content/tracks/san_diego_lake_murray_v3/extension/ext_config.ini`
as installed 2026-10-09 10:11, byte-identical to the workshop's `k10-sd-v021/project/build/san_diego_lake_murray/extension/ext_config.ini`;
kept beside the new one as `ext_config.ini.pre-sodium`): **243** `[LIGHT_N]` blocks (not 241 — see
the coincident pairs below), every one of them

```
COLOR = 255, 209, 140, 1.6       SPOT = 124        SPOT_SHARPNESS = 0.3
RANGE = 22.0                     RANGE_GRADIENT_OFFSET = 0.2
SPECULAR_MULT = 0.6              FADE_AT = 1200    FADE_SMOOTH = 200
DIRECTION = 0, -1, 0             CONDITION = NIGHT_SMOOTH
```

`[LIGHT_POLLUTION] COLOR = 1.0, 0.86, 0.66 / DENSITY 0.22 / RADIUS_KM 6.0` (ini:24–29);
`[MATERIAL_ADJUSTMENT_STREETLIGHTS] ksEmissive 255, 209, 166, 0.08` on `LIGHTS_0_mat` (ini:3692–3697),
which since 0040 pass 2 is a 2 cm marker triangle, i.e. invisible (`tools/author_lamps_blend.py:126–131`).

**Where it comes from.** `tracks/san-diego-lake-murray/track.config.json` `lighting.streetlight`
= `{intensity 1.6, emissive 0.08, range_m 22.0}` — no colour, spot, sharpness, gradient or specular
keys, so those are the writer's defaults. `scripts/ac/ext_config.py` (airoso; the engine-july
build-of-record copy is `diff`-identical, same line numbers):

- 192 `sl_i = sl.get("intensity", 5.0)` — default 5.0.
- 197–201 defaults `spot_deg 124, spot_sharpness 0.3, range_gradient_offset 0.2, specular_mult 0.6,
  color [1.0, 0.82, 0.55]`.
- 221 `c255 = [round(255 * float(v)) for v in sl_c]` then 226 `COLOR = {c255…}, {sl_i}` — the
  0..1 config colour is scaled to 0..255 **and paired with an intensity sized for 0..1 colour**.
- 231 `"FADE_AT = 1200", "FADE_SMOOTH = 200"` hardcoded.
- 258–261 `[LIGHT_SERIES_STREETLIGHTS]` fallback writes the colour **unscaled** (0..1) at the same
  `sl_i`, and hardcodes `SPOT = 124 / SPOT_SHARPNESS = 0.3` ignoring the other keys.
- 211–214 clusters LIGHTS vertices on 5 m `(x//5, z//5)` buckets.
- No `DIFFUSE_CONCENTRATION`, `SINGLE_FREQUENCY`, `SHADOWS*`, `VOLUMETRIC_LIGHT`, `LONG_SPECULAR`
  anywhere in the writer.

**CSP does not normalise COLOR by 255** — measured on this machine, not from the wiki:

| Source | Street-lamp `COLOR` | Other keys |
|---|---|---|
| CSP's own `extension/config/tracks/loaded/ks_nordschleife.ini` | `255,187,81,0.05`, `255,255,255,0.05` | — |
| CSP's own `loaded/tajo.ini` | `215,215,255,0.1` **and** `1, 0.7, 0.1, 10` in the same file | — |
| `nohesi_110` (SoCal freeway) | `208, 137, 52, 0.01` **and** `1,1,1,8.5` in the same file | SPOT 170–175, RGO 0.5, SPECULAR_MULT 0, DIFFUSE_CONCENTRATION 0.9 |
| `shuto_revival_project_beta` "Street Lights" | `255, 173, 65, 0.006` (two stacked per head) | RANGE 35, SPOT 140, RGO 0.65, SINGLE_FREQUENCY 0.7, DIFFUSE_CONCENTRATION 0.15, SHADOWS 1, FADE_AT 650 |
| `la_canyons` | RANGE 30, SPOT 170–180, RGO 0.25 | `[LIGHT_POLLUTION]` DENSITY 0.35 |

Both conventions coexist in CSP's bundled files and in the same mod ini: radiance is
`rgb × 4th term`. 255-scale colour pairs with 0.005–0.1; 0..1 colour pairs with 8–40. Ours is
255-scale colour at **1.6 → effective 255 × 1.6 = 408** per channel, against SRP's 1.5 (3.0 for its
stacked pair) and a community median around 10. The 2026-10-08 round moved 3× inside a 255× error.

**Geometry, measured 2026-10-10 from the workshop kn5 + installed ini** (scratch script, 243 lights
vs 17,978 `1ROAD` vertices): light height above the nearest road vertex **median 6.94 m**
(p10–p90 6.92–6.96); nearest-neighbour spacing **median 57.5 m** (p10–p90 55.6–61.6);
**4 coincident pairs 0.02 m apart** — LIGHT_17/18 (x −1815, z 921), 169/170 (1055, −1087),
229/230 (2395, −179), 231/232 (2400, −242): the marker triangle's `+0.02 x` vertex straddles a 5 m
bucket edge, so those four posts run two lights (eff 816 today). union_island's heads sit 7.2 m
above road at ~29 m spacing, rt_california's freeway heads 12.7 m at ~40 m — our 11.5 m post /
6.94 m light / 57.5 m spacing is a normal residential-arterial layout. **Geometry is not the
problem; the fix is entirely in the ini.**

## Diagnosis

**"Very bright" is a scale error, not taste.** Effective radiance 408 clips all three channels
white at the pool core, so the written colour (255, 209, 140 — a 3000 K warm-white/LED, not
sodium in any case) never reaches the screen.

**"Harsh" is four separate knobs stacked on top of that:**

1. **Cone rim inside the range edge.** At 6.94 m, SPOT 124 puts the cone rim on the ground at
   6.94 × tan 62° = 13.1 m while RANGE 22 reaches √(22² − 6.94²) = 20.9 m: a hard-edged 26 m disc
   with a wall, then nothing. 124° is the narrowest street lamp in the 25-track reference set
   (norm 140–180).
2. **Specular.** `SPECULAR_MULT 0.6 × 408 = 245` units of highlight on asphalt and car paint; CSP's
   track-light default is 0 and the sodium references run 0–0.15.
3. **Hard terminator.** `DIFFUSE_CONCENTRATION` unset → CSP default 0.88, a crisp shadow line on
   posts, kerbs and car flanks; sodium references run 0.015–0.5.
4. **Hard dynamic shadows**, switched on silently by CSP because SPOT < 180 and RANGE > 15, at
   full resolution with no blur: a black wedge under every post.

`RANGE_GRADIENT_OFFSET 0.2` adds a hot centre; sodium references hold an even dim plateau at
0.45–0.65 and fade late.

**LPS, not HPS, decided from the San Diego record rather than from "sodium orange" in general.**
San Diego adopted low-pressure sodium city-wide in 1982, reversed to HPS 5–4 in June 1983, and
on 6 February 1984 — after Caltech/Palomar lobbying — reversed again 6–3 to convert the entire
city (17,000 mercury-vapour + 10,000 HPS lamps) to LPS, the conversion running through the mid/late
80s; Palomar named asteroid 3043 San Diego in thanks
([California Tech, 10 Feb 1984](https://campuspubs.library.caltech.edu/1274/1/1984_02_10_85_17.pdf);
[Physics World, "Astronomers versus activists"](https://physicsworld.com/a/astronomers-versus-activists-the-battle-over-san-diegos-streetlights/);
[RAND N-2089, 1984](https://www.rand.org/pubs/notes/N2089.html)). The 1993/94 amendments allowed
HPS only south of I-8, the City's 2001 Report 01-128 states that north of I-8 every city street
light was LPS, "distinguished by their strong yellow color", and the City's street-lighting page
still describes LPS as its monochromatic-yellow lamp inside the 30-mile Palomar radius
([sandiego.gov street lights](https://www.sandiego.gov/street-div/services/electrical/strlight)) —
Del Cerro / Lake Murray is north of I-8, so "sodium lights from the 80s" on these streets means
the deep monochromatic 589 nm yellow (CRI ≈ 0), not the peach-pink HPS of Los Angeles. Honest gap:
the exact conversion year for these blocks (1985–88 window; SDG&E wood-pole units may have lagged),
so an early-80s memory could be blue-white mercury vapour. HPS (`255,183,76`, SINGLE_FREQUENCY 0.7)
and mercury (`[0.85, 0.97, 1.0]`, SINGLE_FREQUENCY 0) are each a one-line config change if Kevin
says the hue is wrong.

## Fix — config-driven, no kn5, no loop.blend

**Spec (final, 2026-10-10; three independent designs converged, differences resolved below):**

| Key | Today | Spec | Why |
|---|---|---|---|
| COLOR rgb | 255, 209, 140 | **255, 165, 30** (config `[1.0, 0.647, 0.118]`) | sRGB proxy for the 589 nm D-lines, hue ~37°, 88% saturated; between CSP's tajo `1,0.7,0.1` and SRP `255,173,65`; yellower and more saturated than every HPS reference, which is the LPS-vs-HPS relation |
| intensity | 1.6 (eff 408) | **0.010** (eff 2.55) | soft-sodium cluster 0.0045–0.015 (SRP 0.006 ×2, Stockholm, hiroshima, mirandopolis); 15% under SRP's stacked 3.06 because "too bright" has now been said twice. Ladder if too dark: 0.015 → 0.020 → ceiling 0.03, never back toward 0.1+ |
| RANGE | 22 | **25** | SRP's 35 × height ratio 6.94/10 = 24.3; ground radius √(25² − 6.94²) = 24.0 m → pools ~48 m across at 57.5 m spacing, ~10 m dim gap mid-block: the 80s pool/dim/pool rhythm |
| SPOT | 124 | **150** | rim at 6.94 × tan 75° = 25.9 m, just outside the 24.0 m range edge, so the distance gradient defines the pool and the cone never draws a ring (140 would put the rim at 19.1 m, inside); < 180 keeps shadows available |
| SPOT_SHARPNESS | 0.3 | **0.2** | soft group 0.0–0.3 (PCH 0.1, la_canyons 0.25, SRP 0.3); a hard angular edge was part of "harsh" |
| RANGE_GRADIENT_OFFSET | 0.2 | **0.5** | sodium cluster 0.45–0.65: full strength to a 12.5 m slant (~10 m lateral, an even wash across the road like a refractor cobra head), then a 14 m fade; 0.65 re-creates the hot disc as soon as intensity climbs the ladder |
| DIFFUSE_CONCENTRATION | (0.88 default) | **0.25** | Hamburg's value, soft group 0.015–0.5; light wraps posts, kerbs and car flanks. Not SRP's 0.15 because SRP has lit buildings for fill and our grass is black |
| SPECULAR_MULT | 0.6 (245 units) | **0.1** (0.26 units) | ~1000× glare cut, leaves a hint of asphalt sheen. Step to 0 if glare remains, 0.2 if the road goes dead-matte |
| SINGLE_FREQUENCY | (unset) | **0.9** | CSP's documented sodium switch: lit surfaces drain toward the lamp hue. This, not the hue, makes a pool read as LPS rather than orange tungsten. Top of the shipped range (ddm 0.9, nohesi 0.8, SRP 0.7); fallback 0.7 if car paint looks like a rendering fault |
| SHADOWS / _HALF_RESOLUTION / _EXTRA_BLUR | (implicit on, full res) | **1 / 1 / 1** | pins what CSP already does so a RANGE edit cannot silently kill shadows; a SOX U-tube is a ~0.45 m source 7 m up, so penumbrae are soft — half-res + blur approximates that and removes the black wedge. CSP caps shadowed lights at the nearest 15 + 16, so 243 lamps is not a cost multiplier. `SHADOWS_EXP_FACTOR` deliberately left default (second-iteration lever) |
| VOLUMETRIC_LIGHT | (unset) | **0** | no street-lamp block in the reference set uses it; dry inland air; 243 cones is fog plus GPU cost |
| LONG_SPECULAR | (unset) | **0** | wiki says never with shadowed lights; on RainFX-wet asphalt it is pure glare |
| FADE_AT / FADE_SMOOTH | 1200 / 200 (hardcoded) | **800 / 200** | trims the far wall of overlapping distant pools and the cost of 243 shadowed lights, keeps the near-shore pools across the lake; 200 hides pop-in on the lakeside straights |
| lens emissive | 255, 209, 166 × 0.08 | **255, 165, 30 × 0.08** | visually inert (invisible marker) but hue-matched so a future visible head is already sodium; raise to the SRP/la_canyons band 0.5–0.7 only when a head is authored (loop.blend + re-export, out of scope) |
| `[LIGHT_POLLUTION] COLOR` | 1.0, 0.86, 0.66 | **1.0, 0.70, 0.30** | the sky glow must match the lamps or the horizon reads as another city; nohesi ships 1.0, 0.72, 0.30, la_canyons 255,183,76. DENSITY 0.22 / RADIUS_KM 6 unchanged |

**What changes, where:**

1. **Engine — `scripts/ac/ext_config.py`** (airoso canonical first, then hand-mirrored to the
   orphaned engine-july worktree so the build-of-record writes the same ini): read
   `diffuse_concentration`, `single_frequency`, `shadows`, `shadows_half_resolution`,
   `shadows_extra_blur`, `volumetric_light`, `long_specular`, `fade_at`, `fade_smooth` from
   `lighting.streetlight` and emit them in each `[LIGHT_N]`; fix the `[LIGHT_SERIES_STREETLIGHTS]`
   fallback (258–261) to write the same 255-scaled colour and the same keys instead of unscaled
   colour + hardcoded SPOT 124 (at intensity 0.010, unscaled colour is an invisible light if
   `build/<slug>.kn5` ever fails to parse). **Landed 2026-10-10 (uncommitted):** one
   `light_params` list feeds both paths; the new keys are emitted only when the config sets them
   (`_LIGHT_OPTIONAL_KEYS`), so tracks without them keep a byte-identical ini; `FADE_AT`/`FADE_SMOOTH`
   read from config with 1200/200 as the defaults; engine-july mirrored (`diff` clean against the
   airoso working copy). **Still pending:** the writer's **default** `intensity 5.0` must come down
   to the 255-scale decade (~0.02–0.04) — or the writer must emit 0..1 colour with intensities of
   5–10, the other valid CSP convention — and whichever is chosen goes into
   `fleet/GATES-CHANGELOG.md` so the next "too bright" is not tuned inside the wrong decade.
2. **Project — `tracks/san-diego-lake-murray/track.config.json`** `lighting.streetlight`:
   `intensity 0.010, range_m 25.0, color [1.0, 0.647, 0.118], spot_deg 150, spot_sharpness 0.2,
   range_gradient_offset 0.5, specular_mult 0.1, emissive_color [255, 165, 30], emissive 0.08,
   diffuse_concentration 0.25, single_frequency 0.9, shadows 1, shadows_half_resolution 1,
   shadows_extra_blur 1, volumetric_light 0, long_specular 0, fade_at 800, fade_smooth 200`;
   `lighting.light_pollution.color [1.0, 0.70, 0.30]`.
3. **Install as a config-only swap:** `cp` the config to `k10-sd-v021/project/` (the `ship_sd.sh`
   workshop), `PYTHONUTF8=1 python -m scripts.ac.ext_config <PROJ>` (clusters from the existing
   `build/san_diego_lake_murray.kn5`, 2026-10-09 10:49), `python tools/make_treefx.py <PROJ>`
   (re-appends `[TREES]`), back up the installed ini as `extension/ext_config.ini.pre-sodium`, copy
   only `extension/ext_config.ini` into `san_diego_lake_murray_v3/extension/`. No `loop.blend`,
   no kn5, no `ship_sd` install block.

**Deferred, same mechanism, later commits:** (a) merge heads < 0.5 m apart (or bucket on one vertex)
so the four coincident pairs stop doubling, both writer copies; (b) density — 243 lamps at 57.5 m is
~3× San Diego's 1981–95 mid-block standard of 600 ft, so the next step toward an 80s night after
colour and level land is `ACTIVE = 0` on roughly two of every three mid-block lamps (posts stay as
furniture), a selection rule in the writer, not a parameter.

## Scope

- **Proof case:** `tracks/san-diego-lake-murray` → `san_diego_lake_murray_v3` (243 lamps).
- **Same 255× mis-scale, live today:** `lookout-lariat` and `sand-creek` (`intensity 0.35`,
  colour `[1.0, 0.85, 0.3]` → effective 89); every other track inherits the writer default 5.0
  with colour `[1.0, 0.82, 0.55]` → **effective 1275** wherever a LIGHTS mesh exists (IMI, High
  Plains, Pueblo, Second Creek). Those get the same decade shift on the next pin, not another 3×.
- **Not in scope:** lamp post model, lens geometry, kn5, `loop.blend`, the v0.23.0 release zips
  (re-pack only if they are to ship with the new lights, after Kevin's verdict).

## Verification

Kevin's seat, decided before the swap: one fixed time (**22:00, clear**), the same lap against
`ext_config.ini.pre-sodium`, headlights on and off.

- **Scale question is binary.** If every pool vanishes at 0.010, CSP normalised after all and the
  correction is intensity ~2.5 with the same colour, everything else unchanged. If pools are there,
  the 255× diagnosis stands and the ladder (0.010 → 0.015 → 0.020, ceiling 0.03) is the only
  level knob.
- **Reads as sodium:** the road under a lamp goes yellow-grey, car paint drains toward the lamp
  hue (SINGLE_FREQUENCY), grass goes black between pools, no ring at the pool edge, no highlight
  streak on asphalt, no black wedge under the post.
- **Hue wrong?** HPS or mercury alternatives above, one config line each.
- Measurable before the drive — **done 2026-10-10 19:04 on the installed file:** 243 `[LIGHT_N]`,
  every one with the full 17-key block and `COLOR = 255, 165, 30, 0.01` (uniform, no stragglers);
  `[LIGHT_POLLUTION] COLOR = 1.0, 0.7, 0.3`; lens emissive `255, 165, 30, 0.08`; no
  `[LIGHT_SERIES]`; `[TREES]` present, `trees/trees.txt` 15,285 lines; all 243 `POSITION` lines
  identical to the backup; the diff against `ext_config.ini.pre-sodium` touches light keys and the
  emissive `VALUE_0` only.

**After Kevin approves:** commit `track.config.json` + the writer edit (both copies), record the
255× scale finding in `fleet/GATES-CHANGELOG.md`, move this entry to `shipped`.

## Status (2026-10-10 19:04) — installed, awaiting Kevin's night drive

Config-only swap done exactly as in **Fix** step 3: `track.config.json` (spec values, both the
streetlight and `light_pollution` blocks) and the writer edit are in the airoso working tree
**uncommitted**, engine-july carries the same writer, the workshop ini was regenerated from the
2026-10-09 kn5 (243 lights clustered, `[TREES]` re-appended), and
`san_diego_lake_murray_v3/extension/ext_config.ini` is the new file (113,551 bytes) with the old
one beside it as `ext_config.ini.pre-sodium` (74,641 bytes). No `loop.blend`, no kn5, no
`ship_sd` install block touched. Next: Kevin at 22:00 clear; then commit, GATES-CHANGELOG, and the
deferred items (writer default, coincident pairs, 1-in-3 density).

---
name: bespoke-assets
description: Model, texture and place bespoke (self-made, CC0) buildings, props, textures and vegetation for a track, and replace the borrowed assets the kn5s still carry — the mined TreeFX .bin trees, the LA Canyons asphalt, the Hamburg concrete — so the public package is complete and every licence line is true. Use when a dossier's §8 asset plan has a GAP row, when §5 names a building to stand (Exotics' two south-west buildings), when ledger 0005 or docs/PUBLISHING.md's borrowed list needs an owned replacement, or when Kevin says "make a lighter / more modern / our own X". Authoring runs on the Blender machine (astra); the chain and the gates prove the result on Windows.
---

# Bespoke assets

An asset is **bespoke** when we made it: a deterministic generator or a Blender session on astra produced
every vertex and every pixel, from measurements we can cite, and we own it outright (CC0). That is the
only kind of asset that answers the public-package problem for good. The other two kinds stay useful but
carry a condition: **owned** (Kevin's Dropbox library, `fleet/reference/ASSET-LIBRARY.md`) ships in the
full package with its licence recorded honestly, often `UNRECORDED`; **borrowed** (mined from other mods
with `scripts/modkit/extract_kn5.py`) never leaves Kevin's machine (REALISM §3, ledger 0040).

Read before anything: `fleet/LAWS.md` (L1, L6, L7, L12), `fleet/REALISM.md` §3 §4 §6,
`docs/PUBLISHING.md` (the two zips and the borrowed list), `fleet/reference/ASSET-LIBRARY.md`,
`assets/README.md` and `assets/licenses.json`, and the track's `DOSSIER.md` §5–§8.

## 1. What is borrowed today, and what replaces it

From `docs/PUBLISHING.md`, `assets/licenses.json`, `scripts/ac/pbr.py` and
`tracks/san-diego-lake-murray/textures/README.md`:

| Borrowed bytes | From | Bound by (`pbr.TEXTURES` row) | Replacement route |
|---|---|---|---|
| `extension/trees/*.bin` TreeFX models (14 on Lake Murray; `PalmV1-3`, `Pepper`, `Sycamore`, `Gum`, `Pine_Aleppo`, `Oak3`, `Sage`, `Yucca`, `Bush*`, `Agave`) | No Hesi 1.10, Algarve Portimão 2023, Shutoko Revival Project | `tools/make_treefx.py` species lists; `[TREES]` in `ext_config.ini` | §5 — the hardest; the CC0 zip has **no vegetation** until this lands |
| `asphalt_cracked_diffuse/normal.jpg` | LA Canyons 1.2 | `1ROAD`, `1RUNOFF`, `HIGHWAY` | a CC0 pair as the engine default (Poly Haven `aerial_asphalt_01` is already the pack-time swap in `_salvage/k10-sd-v021/assets/textures/`), or a generated one; the aerial-derived route is `fleet/reference/SATELLITE-ROAD-TEXTURES.md` |
| `building_diffuse/normal.jpg` tilt-up concrete | Hamburg by 4r (TextureCom map), `PERSONAL-USE-ONLY` | `BUILDING`, `CURB`, `SIDEWALK`, `1KERB_SIDEWALK`, `1WALL_GUARD`, `HWYSTRUCT`, `BRIDGESTRUCT` — the widest reach of any borrowed file | a CC0 concrete pair as the default (ambientCG `Concrete034` is the pack-time swap), or generated; then the Hamburg bytes leave `assets/textures/` |
| `warehouse_*.jpg` | mined Hamburg | `WAREHOUSE` | CC0 / generated |
| `bushes_atlas.png` | LA Canyons `bo_bushes_11` | `BUSHES` | a generated or own-photo CC0 billboard atlas |
| `ground_dry_diffuse.jpg` | LA Canyons dirt | `1GRASS` (stock), `GRASS_FAR`, `SHOULDERUND` — and an input to `make_chaparral_far.py` | CC0 dry ground (Poly Haven class); re-derive `chaparral_far` from clean inputs |
| `rock_granite_red.png` | "Kevin's stone-wall asset harvest" (pbr comment; provenance not in `licenses.json`) | `ROCKCUT` | confirm provenance first |

Buildings as **geometry** are a second front: Lake Murray's houses are OSM footprint boxes from the
v021 assembler (`tools/fetch_buildings_cache.py` schema, `house_seat` in the prep) skinned with the
Hamburg concrete; the chain tracks (Exotics, Milford, High Plains, Sand Creek) have **no building step
at all** — their dossiers' §8 list buildings as `AUTH_` massing. The first bespoke building through the
chain is Exotics' 2013 dressing: the two small south-west buildings, no Welcome Center (DOSSIER §8, §11).

## 2. Three ways to own an asset, in order of preference

1. **Generated.** A deterministic script writes the OBJ / PNG / JSON; rerunning reproduces the bytes;
   a test pins the committed files against the generator (`--check`). Every dimension in the docstring
   has a source. The exemplars, read them before writing a new one:
   - `tools/make_streetlight_led.py` — the Caltrans ES-6A Type 21 pole + LED cobra head (ledger 0056):
     pole 10.67 m, arm 3.66 m, lens at 11.81 m, OD 219 → 94 mm taper, every number from the Caltrans
     standard plan and San Diego SDE-101. OBJ with smoothing groups and real UVs, a JSON spec the
     placer and the verifier read, `tests/tools/test_streetlight_led.py` pins the bytes. ~360 render
     points against the 4,045 of the Dropbox lamp it replaced.
   - `tools/make_sign_textures.py` — MUTCD artwork (public domain, 17 U.S.C. 105) drawn procedurally.
   - `tools/make_kerb_texture.py` — a worn kerb atlas from seeded noise, no photograph (ledger 0053).
   - `tracks/san-diego-lake-murray/textures/make_sandstone_cut.py` — a geology-specific rock tile,
     drawn from the description of the Stadium Conglomerate, bound by a track `texture_overrides` row.
2. **Hand-modelled on astra**, from footprints, photos and measurements, saved as OBJ + CC0 textures,
   with a provenance README beside it (what was measured where, what the textures are from).
3. **Converted from Kevin's owned library** (`ASSET-LIBRARY.md` → `assets/README.md` conversion
   table): decimate, PoT textures, metres, Y-up, base at y = 0. Owned, not CC0 — the licence line
   says `UNRECORDED` or what the pack says, never "CC0" by assumption.

Dossier §8's rule stands: owned assets before purchases, purchases only from a GAP row. Bespoke is the
GAP filler and the only route that makes the CC0 package whole.

## 3. The laws that bind an asset

- **L1 — not invented.** A building stands where the footprint says (NAIP 0.6 m, the 2013 image for
  Exotics; OSM `building`, `building:levels`, `height`), is as tall as the levels or the shadow says,
  and is the kind of building the imagery and §5 say (metal-clad hangar, stucco ranch house). A lamp is
  the standard the agency publishes. Write the source beside each number; where a number is a guess,
  write `[invented]` the way the gates do, and say so in the dossier.
- **L6 — metres, Y-up.** Author in the engine frame (x = east, y = up, z = north, base or road datum at
  y = 0). The prep's import remap `(x, y, z) → (x, z, y)` is a reflection, so face winding is reversed
  on import to keep outward normals (`tools/author_lamps_blend.py`, `load_obj_full` + the reversed
  face tuples). Never pre-mirror an asset; the chain's frame is San Diego's — `mirror_x false`,
  `true_north_rotation_deg 0` (ledger 0060 and `docs/ONE-CHAIN.md` §1, on the chain PR).
- **L7 — what AC refuses.** Textures power-of-two and ≤ 2048 px; **every material needs a texture**
  (a texture-less kn5 material renders black — solid colours are 64×64 PNGs, as the sign solids are);
  65,535 verts per mesh hard, and the prep tiles anything over `PIECE_CAP` 50,000; no numeric prefix =
  visual-only, `1WALL_*` = collidable. Props ≤ 10k tris (ASSET-LIBRARY), a building a few thousand,
  a far backdrop less: the chain has no LODs.
- **L12 — show, don't assert.** Fixed-station stills (`tools/lamp_stills_blend.py`,
  `tools/sign_stills_blend.py` are the pattern), the gate numbers, and Kevin's drive. A tier is claimed
  with its artifact or not at all (`fleet/DEFINITION-OF-DONE.md`).
- **REALISM §3, clean room.** The reference tracks installed on the Windows box are for *measuring
  technique* with `scripts/modkit/inspect_kn5.py` (tri budgets, texture sizes, shader params); their
  meshes and textures never enter an asset. `*.bin` stays gitignored.
- **REALISM §4, the collection contract.** Everything an author places goes in an `AUTH_<thing>`
  collection; the engine regenerates `GEN_*` beside it and never through it. The lamp and sign tools
  predate the contract and link to the scene root — a new tool follows the contract.
- **REALISM §6, the floor.** Street ports: signage, poles, driveways, the buildings that make a
  neighbourhood recognisable. Circuits: kerbs with real sections, tyre walls, marshal posts, paddock
  mass. Rally: nothing urban. The asset list for a track is the floor for its archetype, from §5.

## 4. The pipeline, one asset at a time

**0. Need → decision.** Read the dossier §5–§8. Name the need in one line ("Exotics: two single-storey
metal buildings, SW corner, 2013 footprint"). Check `ASSET-LIBRARY.md` for an owned candidate; if none
fits or the package must be CC0, the §8 row says `bespoke` and points at this skill. The row is
written before the asset is.

**1. Measure.** Footprint and orientation off the georeferenced image (the aerial-tracing skill's
control-point frame gives metres); height from `building:levels` × 3.0–3.5 m, a measured shadow, or
a known type; materials from the imagery and photos. For street furniture, the agency standard
(Caltrans / MUTCD / the city's standard drawings). For vegetation, the plant community in §6
(Exotics: Mojave creosote–bursage; Lake Murray: coastal sage scrub, palms, peppers). Write the numbers
and their sources into the generator docstring or `assets/README.md` / the track's `textures/README.md`.

**2. Model.** On astra, in Blender 4.2 (the running app through the K10 live bridge —
`tools/blender-bridge/live_server.py` inside Blender on `127.0.0.1:9761`, `live_client.py` sends
Python, globals persist, set `_` to return a value — or `blender --background --python`, or the `bpy`
pip module for a generator). Rules: metres, origin at the base, +y up when written as OBJ; quads and
clean topology; smoothing groups (`s 1..n` round parts, `s off` flat caps) so the placer marks sharp
edges; real UVs (0..1 per face set, or tiled by real metres so a 4 m tile reads at 4 m). A box with a
roof is a correct first building; detail is the look's business, not the gate's.

**3. Texture.** CC0 sources with the URL recorded (ambientCG, Poly Haven — confirm the licence on the
page, never from the filename), own photographs, or a seeded Pillow generator. PoT, diffuse JPG /
alpha PNG, normal maps in the OpenGL (+y green) convention. Bind one of two ways:
- a **fleet-wide class** gets a `scripts/ac/pbr.py` `TEXTURES` row (name → diffuse, normal, roughness,
  fallback colour, metallic, water). `match_key` takes the **first** prefix in dict order, so a row
  named `BUILDING_STUCCO` must sit before `BUILDING` or it never binds. Alpha-cutout billboards go in
  `pbr.BILLBOARD` and get a `KS_PROPS` entry (vegetation at full ksDiffuse went "radioactive").
- a **track-specific tile** lives in `tracks/<track>/textures/` with a `README.md`, bound by
  `track.config.json` `texture_overrides["<PREFIX>"]` (project-relative paths; add the files to
  `ship.json` `sync_in.optional` so the workshop gets them — the sandstone cut is the model).
The exporter picks `ksPerPixelMultiMap` when a normal exists, `ksPerPixel` otherwise, `ksTree` for
billboards, and embeds only what it staged into `build/texture/`.

**4. Place — a `tools/author_<thing>_blend.py`,** modelled on `tools/author_lamps_blend.py` and
`tools/author_signs_blend.py`:
- reads its declaration from `track.config.json` (footprint corners, heights, model key, count) —
  never a coordinate typed into code; a hand-placed object is declared, then placed by the tool, so a
  re-run reproduces it;
- loads the OBJ with `load_obj_full` (UVs + smoothing groups kept), remaps `(x, z, y)` with winding
  reversed, marks sharp edges;
- seats on the **built** ground read from the scene's `1GRASS` / `1ROAD` BVHs (`tools/signs_mesh.py`;
  buildings per the prep's `house_seat` rule: floor at the mean ground − 0.4 m, foundation to 0.15 m
  under the lowest ground, half the box showing where the footprint straddles a cut);
- names: `BUILDING_<key>_<k>`, `PROP_<key>_<k>`, collidable parts `1WALL_<key>_<k>`; links everything
  into `AUTH_<thing>`; removes its own earlier objects (by that collection) first, so it is idempotent;
- **self-checks, exit 1 and the blend NOT saved** on any: footprint off every road and kerb (ring, not
  axis), clearance to walls and the drive corridor, foot in the ground, no `AC_*` touched, every face
  with a material whose prefix binds a texture;
- prints one line per object with the numbers it checked (L12).
The prep then renames by `AC_NAME` (unknown names pass through), flattens UVs with a top-down planar
projection on every mesh **except** names starting `PALM`, `TREE`, `SCRUB`, `BUSHES`, `CHAINLINK`,
`ROADTEXT`, `1WALL_RACE`, `1KERB_RACE`, `BRIDGESTRUCT`, and welds the rest. **A textured prop or
building must be on that exemption list** or its UVs are destroyed and its shells welded inside out
(ledger 0024): extend the tuple in `scripts/ac/build_kn5_loop.py` for the new prefix, with a test,
in the same change as the tool. Never move or rename anything under `scripts/`.

**5. Wire into the chain.** `tracks/<track>/ship.json` `steps.author` names the step;
`tools/ship_track.sh` gains `author_<thing>()` (the closed vocabulary — `tests/tools/
test_ship_track_chain.py` checks every step is a function). The gates that judge it, all on the built
kn5 (L5): `tools/house_seat_check.py` (FLOATING / SUNKEN / BURIED buildings, ledger 0046),
`scripts/ac/kn5_ground_check.py` (furniture seating, mast integrity), `tools/verify_race.py
--scenery-only` (trunks and posts out of every race lane and wall) where race layouts exist,
`drive_test`'s obstruction band, `verify_kn5`'s 65k cap. A new check or a changed threshold gets its
`fleet/GATES-CHANGELOG.md` entry in the same commit.

**6. Record.** `assets/licenses.json` entry (`name`, `files`, `source` — "airoso tools/make_x.py
(generated …)" or the CC0 URL — `license`, `url`); `assets/README.md` provenance row (or the track's
`textures/README.md`); `ASSET-LIBRARY.md` row in the self-made style of the LED light; dossier §8
row updated; the ledger entry it answers (0005 for the stand-ins, 0040 for the borrowed bytes) gets
its Evidence; `scripts/ac/credits.py` renders `CREDITS.txt` / `LICENSES.md` from `licenses.json`, and
a generated document must not lie.

**7. Prove.** `bash tools/ship_track.sh <track>` on the Windows box (or `--from` the author step),
gates green, stills from the fixed stations, Kevin's drive. Then the tier moves in
`fleet/DEFINITION-OF-DONE.md`, with the artifact.

## 5. Vegetation — the open route

TreeFX `.bin` models are CSP's own format; this repo only *references* filenames
(`docs/TREEFX-FORMAT.md` "Licensing — reference, don't bundle"). **Whether CSP ships a tool that
compiles our own tree into a `.bin` is not established in this repo** — find out on the Windows box
before planning on it. Until then, bespoke vegetation is mesh vegetation baked into the kn5: billboard
crosses or low-poly cards from CC0 or own-photo atlases under the exempt prefixes (`PALM*`, `TREE*`,
`SCRUB*`, `BUSHES*`), alpha cutout via `pbr.BILLBOARD`, shading via `KS_PROPS`, never welded, excluded
from the seating lens (`kn5_ground_check` lists `CONIFER`, `FENCEWOOD`); it looks less than TreeFX and
it ships. Start small: Exotics' creosote clumps at the campus edge (DOSSIER §6, §8 GAP row) are a
dozen cards and one atlas.

## 6. What astra needs

Blender 4.2 (the app, or `pip install bpy==4.2.0` into a Python 3.11 venv), this repo, Pillow for
the generators, the K10 live bridge loaded in the running Blender, and the Dropbox library (the
connector or a local sync) when converting owned assets. No AC add-on and no Assetto Corsa: export
and the gates are the chain's job on Windows. Workshops live outside the repo; what is committed is
the generator or the OBJ + textures + JSON spec, the test that pins them, the author tool and its
tests, and the records in §4 step 6.

## Do not

- Ship, commit or derive from anything mined — not a mesh, not a pixel, not as an input to a
  generator (`make_chaparral_far.py` takes the LA Canyons dirt as an input; re-derive it clean).
- Type a coordinate into a tool. Declare it in `track.config.json`; the tool places it.
- Invent a dimension without writing `[invented]` beside it. Measure or cite (L1, L10).
- Leave a material without a texture, a texture non-PoT or over 2048, a mesh over the cap.
- Put a textured asset through the prep without its prefix on the UV/weld exemption list.
- Regenerate `GEN_*` through `AUTH_*`, or place into the scene root.
- Write a licence line that is not true. `UNRECORDED` is a true line; "CC0" by assumption is not.
- Call a tier reached without the gates and the stills.

## Open before the first asset

- **astra** — assumed here to be the Blender authoring machine (`CLAUDE.md`: "astra and every machine
  clone this"). If it is the Mac, the `bpy` module path applies; if it has Blender, the bridge.
- Whether to swap the Hamburg concrete and the LA Canyons asphalt fleet-wide **now** (the CC0 swap
  bytes already exist in `_salvage/`) or per track as each ships — Kevin's call; the first makes every
  future full package CC0-clean at once.
- CSP TreeFX model authoring (§5).
- The Dropbox library's licence terms (ASSET-LIBRARY: "Poly Haven naming suggests CC0 — confirm").

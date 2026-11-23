---
id: 0101
title: The owned asphalt and concrete on every installed track, beyond the pilot's two
status: fixed-awaiting-rebuild
scope: aspen-lm, del-mar-lm, exotics-racing-lv-lm, grand-junction-lm, lookout-lariat-lm, pikes-peak-lm, pueblo-lm, san-diego-freeway-lm
layer: project
train: -
---

## Symptom

Ledger 0095: the road's 4 m texture repeats far down the road (Kevin, 2026-11-18). Its pilot put the owned asphalt and a
0.5 m detail high-pass on Milford 0.1.13 and High Plains 0.1.8, both installed with their gates the same as their PC
rehearsals.

Kevin, 2026-11-22, asked "The owned asphalt and concrete on the other tracks?":

> On every track now

Lake Murray, Sand Creek, High Plains and Milford have their own coders, who do their own. This entry is every other
installed track.

## Evidence

**The installed tracks** (`fleet/ac-installed.json`, role current), less those four, and with no rally tracks (Kevin
retired them on 2026-11-13):

- `aspen_motorsports_park`: aspen-lm 0.1.6
- `del_mar_fairgrounds`: del-mar-lm 0.2.7
- `exotics_racing_lvms`: exotics-racing-lv-lm 0.1.6
- `grand_junction`: grand-junction-lm 0.1.4
- `lookout_lariat_lm`: lookout-lariat-lm 0.1.0
- `pikes_peak_international_raceway`: pikes-peak-lm 0.2.3
- `pueblo_motorsports_park`: pueblo-lm 0.1.5
- `san_diego_freeway_lm`: san-diego-freeway-lm 0.1.0

`pikes_peak_international_raceway_lm` 0.1.0 is superseded. It is the same track's older folder, so nothing here touches it.

**What each installed build wears.** Each track's `data/split_manifest.json` lists the objects in its kn5s. I passed
every object through `scripts/ac/pbr.resolve` with the track's own overrides (`pbr.load_overrides`).

- The manifests on Aspen, Grand Junction, Pueblo and Nevada come from their 0.1.4, 0.1.2, 0.1.3 and 0.1.4 installs.
- Road wear came after those installs. It moved no position: it changed only the road's UVs and materials (the notes in
  `fleet/ac-installed.json`). So the object list still holds.
- engine-july's frozen table (`tracks/san-diego-lake-murray/engine-july-snapshot/scripts/ac/pbr.py`) has the same rows
  as airoso's for every key below.

| track | wears the borrowed cracked asphalt (LA Canyons) | wears building_* (Hamburg's board-formed concrete) |
|---|---|---|
| aspen-lm | 1ROAD | 1KERB_SIDEWALK (the edge strip) |
| del-mar-lm | 1ROAD | 1KERB_SIDEWALK |
| exotics-racing-lv-lm | 1ROAD | 1KERB_SIDEWALK; the 14 apron pads 1RUNOFF_apron_<k> (through the track's own 1RUNOFF override); its PADAPRON override, which no object binds |
| grand-junction-lm | 1ROAD | 1KERB_SIDEWALK |
| lookout-lariat-lm | 1ROAD (3 objects) | none: the verge 1KERB_SIDEWALK is the track's gravel override, and 1WALL_STUB is Kevin's barrier module |
| pikes-peak-lm | 1ROAD (4 objects) | 1KERB_SIDEWALK |
| pueblo-lm | 1ROAD | 1KERB_SIDEWALK |
| san-diego-freeway-lm | 1ROAD | 1KERB_SIDEWALK (2 objects); 1WALL_GUARD (the deck's concrete rail: the parapet) |

None of these builds has a 1RUNOFF / HIGHWAY stage on the cracked tile. None has a CURB, SIDEWALK, HWYSTRUCT,
BRIDGESTRUCT, BUILDING, BARRIER or WAREHOUSE object.

**The owned pairs** (`assets/textures`, `tools/make_owned_surfaces.py`, CC0, merged with `claude/owned-surfaces-20261116`):

| file | md5 | bytes | replaces |
|---|---|---|---|
| asphalt_dense_diffuse.jpg | 339c4244d8b07494be81df14eb963c8c | 2,346,705 | asphalt_cracked_diffuse.jpg (2,372,762) |
| asphalt_dense_normal.jpg | 7a71dfcefbbce0267cb0d17f0c931fb0 | 3,198,685 | asphalt_cracked_normal.jpg (1,969,781) |
| concrete_plain_diffuse.jpg | d77c7ca9c8faa202951821133628a4e4 | 262,056 | building_diffuse.jpg (231,365) |
| concrete_plain_normal.jpg | 2692b4231be5d2c24c6b4f0f3705bb84 | 370,970 | building_normal.jpg (328,479) |

`concrete_aged_*` (meant for WAREHOUSE) has no user on these tracks and stays unbound.

**Measured on the Mac, 2026-11-22.** Pillow decode, as Blender's Non-Color load, as ledger 0095 measured:

- **Mean colour.**
  - asphalt_dense: 0.38895. The cracked tile: 0.38795.
  - concrete_plain: 0.51078. building_diffuse: 0.51109. Per channel the two concretes are 0.5278 / 0.5159 / 0.4886 against
    0.5287 / 0.5153 / 0.4890.
- **Normal tilt, p50 / p90.**
  - asphalt_dense_normal: 13.2 / 24.0 deg. The cracked normal: 12.9 / 23.5.
  - concrete_plain_normal: 4.0 / 7.4 deg. building_normal: 3.5 / 8.9.
- **The high-pass on asphalt_dense:** std/mean 27.90 -> 27.87 %, the mean kept.
- **The clip.** The share of the road-wear detail over 1 after `/ m0`, at each track's last bake m0 (`data/road_wear.json`,
  committed with its install):

| track | m0 | 1ROAD: the cracked tile (recorded) | the cracked tile (here) | owned, no cut | owned + 0.5 m | 1KERB_SIDEWALK: building_* | concrete_plain |
|---|---|---|---|---|---|---|---|
| aspen-lm | 0.76923 | 1.27 | 1.27 | 0.40 | 0.408 | 0.0 | 0.0 |
| del-mar-lm | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| exotics-racing-lv-lm | 0.85209 | 0.468 | 0.468 | 0.074 | 0.075 | 0.0 | 0.0 |
| grand-junction-lm | 0.79498 | 0.971 | 0.971 | 0.268 | 0.263 | 0.0 | 0.0 |
| pikes-peak-lm | 0.76923 | 1.27 | 1.27 | 0.40 | 0.408 | 0.0 | 0.0 |
| pueblo-lm | 0.76923 | 1.27 | 1.27 | 0.40 | 0.408 | 0.0 | 0.0 |

(%, [measured]). The method gives every recorded value back: on these six, and on High Plains (0.408) and Milford (0.069)
with the owned tile and the cut. m0 is read off the tone alone (`tools/road_wear_blend.py`: the tone's headroom
percentile), so a new detail does not move it. On a rebuild with the same road it holds exactly.

## Diagnosis

**Where the high-pass goes. I decided this from the code.**

- `tools/road_wear_blend.py` step 5 bakes a detail for every surface `road_wear.surfaces` names (`pbr.resolve(...)`
  diffuse / m0, with the resolved normal). It does this for every rubber mode (`drawn`, `photo`, `none`), with or without
  an aerial. There is no branch that skips it.
- Step 5b (`rw.highpass_cuts`) then filters the surfaces that `road_wear.detail_highpass_m` names.
- So every track with a `road_wear` key has a 1ROAD detail tile. That is Aspen, Pueblo, Grand Junction and Pikes Peak
  (tone only, rubber `none`), Nevada (drawn band, NAIP 2022 tone) and Del Mar (drawn band, no aerial). Each takes
  `{"1ROAD": 0.5}`, as the pilot.
- The Lariat and the freeway have no `road_wear` key, so `spec_from_config` returns None. The bake does nothing ("No key =
  nothing happens"). There is no macro, and 1ROAD's diffuse is the tile itself on the prep's 4 m planar grid.
- `detail_highpass_m` lives under `road_wear` and needs that bake. Cutting the plain diffuse would need new code, and it
  would take the road's only coarse variation with nothing in its place. So those two get the pair and no cut.
- **Del Mar's macro carries only the drawn band.** Its tone is 1.0 by Kevin's "Drawn band, no photo" (0.2.7). The cut
  takes away only what repeats on the 4 m lattice: a 4 m tile holds nothing coarser than 4 m, so it removes no real
  large-scale tone. The far road's look there is [not measured].
- **The edge strip's detail is not cut** on any track (the pilot's rule).

**The owned concrete exists.** `concrete_plain_*` is a 4 m tile with no joints or tie holes, made for the prep's planar
grid. Every stage in the first table that wore building_* now binds it by `texture_overrides`, the pilot's mechanism.

- 1KERB_SIDEWALK and 1WALL_GUARD take the prep's 4 m planar UVs (engine-july's `planar_uv` skip list names neither). On
  road wear's atlas the strip's detail stays on the same 4 m grid.
- Nevada's aprons keep their own UVs, at world metres / 8 (`tools/seat_pads_blend.py` UV_M, laid inside prep). The new tile
  repeats every 8 m there, as building_* did.
- Nevada's 1RUNOFF and PADAPRON overrides said "the run-off is concrete (the edge strip's own skin)". They move with the
  strip.

## Fix (branch `claude/owned-textures-fleet-20261122`; config only, opt-in per track)

| track | stages | what binds | version | high-pass | why |
|---|---|---|---|---|---|
| aspen-lm | 1ROAD; 1KERB_SIDEWALK | asphalt_dense pair (road wear's 1ROAD detail + its normal); concrete_plain pair (the strip's detail + normal) | 0.1.6 -> 0.1.7 | 1ROAD 0.5 m | road_wear (tone only) bakes a 1ROAD detail |
| del-mar-lm | 1ROAD; 1KERB_SIDEWALK | as Aspen | 0.2.7 -> 0.2.8 | 1ROAD 0.5 m | road_wear (drawn, no aerial) bakes a 1ROAD detail; its macro is the band alone |
| exotics-racing-lv-lm | 1ROAD; 1KERB_SIDEWALK; 1RUNOFF; PADAPRON | as Aspen; the 14 apron pads and the unused PADAPRON row: concrete_plain diffuse + normal (were building_*) | 0.1.6 -> 0.1.7 | 1ROAD 0.5 m | road_wear (drawn, NAIP 2022) bakes a 1ROAD detail |
| grand-junction-lm | 1ROAD; 1KERB_SIDEWALK | as Aspen | 0.1.4 -> 0.1.5 | 1ROAD 0.5 m | road_wear (tone only) |
| lookout-lariat-lm | 1ROAD | asphalt_dense pair as the road's diffuse + normal | 0.1.0 -> 0.1.1 | none | no road_wear: no bake, no detail tile, no macro |
| pikes-peak-lm | 1ROAD; 1KERB_SIDEWALK | as Aspen | 0.2.3 -> 0.2.4 | 1ROAD 0.5 m | road_wear (tone only) |
| pueblo-lm | 1ROAD; 1KERB_SIDEWALK | as Aspen | 0.1.5 -> 0.1.6 | 1ROAD 0.5 m | road_wear (tone only) |
| san-diego-freeway-lm | 1ROAD; 1KERB_SIDEWALK; 1WALL_GUARD | asphalt_dense pair as the road's diffuse + normal; concrete_plain pair on the strip and the deck rail | 0.1.0 -> 0.1.1 | none | no road_wear |

Every changed track's `ship.json` `sync_in.assets` names the owned files its config binds, with `_owned_textures_doc`:
the asphalt pair on all eight, and the concrete pair on all but the Lariat. engine-july's `assets/textures` does not carry
them, unless an engine copy had them added by hand, as the pilot's did (ledger 0093, PC rehearsal 2). `tools/ship_track.sh`
copies them into the workshop. The override looks in the engine's own folder first and in the workshop after it, so
runbook step 1 md5-checks whichever one it will read.

**Kevin's forces, carried on the Mac's word as Pikes Peak 0.2.2's was.** They cover the same place and the same window.
This change moves no position and no UV; only the named materials' textures change.

- Pikes Peak `gates.drive1.force_exemptions.stage.versions` adds 0.2.4: the infield hairpin.
- The Lariat's `gates.drive1.force_exemptions.versions` adds 0.1.1: its two rows.
- Neither is installed forced on this word: Kevin's own yes first (Open).

Nothing else changes:

- no engine code;
- no gate, threshold, or gate list;
- no `pbr.TEXTURES` row;
- `assets/licenses.json` and `fleet/ac-installed.json` (Open).

## Scope

The eight tracks above, and nothing else:

- **Lake Murray, Sand Creek, High Plains and Milford are their coders'.** High Plains and Milford keep ledger 0095's
  1ROAD row. None of the four binds the owned concrete here.
- Milford's 1RUNOFF doc calls its building_* "Nevada's apron skin (ledger 0081)". Nevada's aprons now wear
  concrete_plain, so following them or not is the Milford coder's call.
- **Not covered.** The other borrowed files on these tracks are not asphalt or concrete: `ground_dry_diffuse.jpg` (LA
  Canyons) on 1GRASS where a track has no ground tile of its own, and the stock `kerb_*`.

## Verification

**Mac (this branch):**

- `tests/aerial/test_owned_textures_fleet.py` (new, 1 test) checks:
  - the four owned files' md5s;
  - every current installed track is this ledger's, the pilot's, or Lake Murray's / Sand Creek's;
  - each changed track binds the asphalt pair on 1ROAD, and the concrete pair on exactly the rows above;
  - the cut is `{"1ROAD": 0.5}` where road_wear is, and there is no road_wear on the Lariat and the freeway;
  - no object in its installed manifest still resolves to a borrowed asphalt_cracked_ / building_ / warehouse_ file;
  - its `ship.json`, read by `tools/ship_track_spec.load`, syncs every owned file it binds;
  - a carried force names the config's version;
  - every other track binds neither pair (the pilot's two: the asphalt only).
- Mutation checks: each of these failed the test, and the test passed with the tree as it is.
  - the freeway's 1WALL_GUARD row dropped;
  - one concrete file left out of Aspen's sync list;
  - Pueblo's cut dropped;
  - an owned 1ROAD on Sand Creek;
  - Pikes Peak's 0.2.4 left out of its force.
- `tests/aerial/test_road_wear_highpass.py`: the "only the pilot's tracks" check learns this ledger's tracks, as
  72f30590 did at its integration. It is renamed `test_only_the_pilot_and_fleet_tracks_opt_in_and_they_bind_the_owned_pair`.
- The full suite on this branch: 1,711 passed, 0 failed (main 9aacb34c: 1,710 passed; the one more is the new test).

**The kn5's bytes: an estimate from the files' sizes, [not measured].**

- Road-wear tracks:
  - +1,228,904 B for the 1ROAD normal;
  - +42,491 B for the strip's normal;
  - the two re-encoded details (`road_wear_detail_1road.jpg`, `road_wear_detail_1kerb_sidewalk.jpg`): new pixels, size
    [not measured]. The 0095 audit expected about -0.15 MB for the 1ROAD detail.
- Nevada: as the road-wear tracks, and +30,691 B for the aprons' diffuse.
- The Lariat: +1,202,847 B.
- The freeway: +1,276,029 B.

### PC runbook 0101-1 (rehearsal only; install only on Kevin's word)

One rehearsal per track, from this branch's head. Each from an EMPTY workshop, as ledger 0090's proofs ran.

1. **Setup, per track.**
   - Check out this branch's head detached. ENG = the engine copy the track's last install used (ledger 0084's runbooks;
     the Lariat's and the freeway's per ledgers 0078 / 0080).
   - Nevada needs its TreeFX bins in place first, md5-checked (runbook 0089-2).
   - Before the run, md5-check the four owned files where the override will resolve them. That is
     `$ENG/assets/textures/<f>` when ENG has the file, else the workshop's `assets/textures/<f>` that sync_in copies in.
     The md5s are in the table above.
2. **Run.**

   ```
   AIROSO_NUMPY_PY=<a python with numpy + Pillow> SHIP_PROJ=<an empty scratch dir, absolute, outside airoso> \
     bash tools/ship_track.sh <track> --no-install
   ```

   - The tracks: aspen-lm, del-mar-lm, exotics-racing-lv-lm, grand-junction-lm, pikes-peak-lm, pueblo-lm,
     lookout-lariat-lm, san-diego-freeway-lm.
   - No `--force-install`. Pikes Peak and the Lariat stop at NOT INSTALLED on their forced rows, as an unforced run must
     (ledger 0090).
3. **Report, per track.**
   - **The ship log** (road-wear tracks).
     - `[road_wear] 1ROAD: detail high-pass 0.5 m on asphalt_dense_diffuse.jpg: std/mean 27.90 -> 27.87 %` (about).
     - The `[road_wear] macro atlas ...: m0 <x>` line: m0 should equal the table's.
   - **`data/road_wear.json`.**
     - `m0`.
     - `detail.1ROAD`: `from` asphalt_dense_diffuse.jpg, `normal` asphalt_dense_normal.jpg, `highpass_m` 0.5, and the
       road clip, `clipped_pct`, with the expected value from the table (owned + 0.5 m column).
     - `detail.1KERB_SIDEWALK`: `from` concrete_plain_diffuse.jpg, `normal` concrete_plain_normal.jpg, `clipped_pct` 0.0.
   - **`road_wear_check`**: every row next to the installed build's (`tracks/<track>/data/road_wear_check.json`, committed
     with its install). Expect PASS on each, with the same values: the detail's pixels are read by no row.
   - **kn5.**
     - Each kn5's bytes, next to the installed folder's.
     - `python tools/kn5_textures.py <SHIP_PROJ>/build --json <scratch>/kn5_textures.json`, by hand where ship.json names
       no `textures` gate (it is a report, not a gate): 0 missing. The owned names are embedded, and no
       asphalt_cracked_* or building_* is embedded in any kn5.
   - **Every gate row against that track's installed build.** Each gate JSON of the run (drive_test, audit, kn5_ground,
     road_wear_check, house_seat_check, edge_report, verify_pads / verify_mouths / stage_force on Pikes Peak, road
     inventory / stacked legs / drive1_gates on the Lariat) goes next to the one its install committed under
     `tracks/<track>/data/`: equal, or the difference named.
   - **`python tools/kn5_equiv.py <installed kn5> <built kn5>`** on every kn5. Expect "textures only", naming exactly:
     - Road-wear tracks:
       - `road_wear_detail_1road.jpg` and `road_wear_detail_1kerb_sidewalk.jpg` changed;
       - asphalt_cracked_normal.jpg and building_normal.jpg out;
       - asphalt_dense_normal.jpg and concrete_plain_normal.jpg in;
       - on Nevada also building_diffuse.jpg out and concrete_plain_diffuse.jpg in.
     - The Lariat: asphalt_cracked_* out, asphalt_dense_* in.
     - The freeway: asphalt_cracked_* and building_* out, asphalt_dense_* and concrete_plain_* in.
     - Pikes Peak's spawn kn5s: equivalent.
   - **Anything else beyond tangent noise: stop and send the row and the file** (ledger 0090's rule). The Lariat (installed
     2026-11-04) and the freeway (2026-11-06) predate ledger 0090's proofs, and main has not been shown to rebuild them.
     A geometry difference there is not this change: report it, do not fix it.
   - **A still from the seat**, down the longest straight, next to the installed build's, if the PC can (Blender, as
     ledger 0095's stills).
4. **Install nothing.**
   - Each install waits for Kevin's word.
   - Pikes Peak 0.2.4 and the Lariat 0.1.1 install forced only on his own yes, typed on the PC.

## Open

- **Kevin:**
  - the install word for each track;
  - for Pikes Peak 0.2.4 and the Lariat 0.1.1, whether the forces carry over ("Carry it over", as for 0.2.3) and his typed
    yes. If he says no, the two `versions` entries come out;
  - his drive: the far road on every track, the close look of the concrete strip.
- **The PC:** runbook 0101-1.
- **`assets/licenses.json`** (not edited here). The owned-surfaces row's `_note` says the asphalt pair is bound per track
  on Milford and High Plains only. It now needs to say:
  - the asphalt pair also binds 1ROAD on Aspen, Del Mar, Nevada, Grand Junction, the Lariat, Pikes Peak, Pueblo and the
    freeway;
  - concrete_plain binds 1KERB_SIDEWALK on seven of them, 1WALL_GUARD on the freeway, and 1RUNOFF / PADAPRON on Nevada.

  `assets/textures/SOURCES.txt` still says "Not bound yet" for both pairs (stale since ledger 0095), and was not edited
  either.
- **`fleet/ac-installed.json`** (not edited here): nothing until an install. Then `tools/ac_tidy.py record` per track, with
  the new version, this branch and its sha.

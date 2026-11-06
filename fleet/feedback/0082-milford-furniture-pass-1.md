---
id: 0082
title: Milford furniture pass 1 — the rails, tyre walls and sheds NAIP shows, on Lake Murray's engine
status: in-progress
scope: track:milford-road-course-lm
layer: project
train: -
---

## Request (Kevin, 2026-11-06)

> "after that, we to keep going, prioritizing furniture passes on milford and buildings started on del mar"

His standing words: "I just want real". Milford's port (`milford_road_course_lm` 0.1.0, ledger 0078) was a bare circuit:
road, ground, the turf tile, the tree cards, the pad tent and two far plant blocks. This entry is the first furniture
pass: inventory first, then the physical classes (anything a car can hit), then the visual ones, then a candidate
through the full ship chain. Branch `claude/milford-furniture-lm`, cut from `origin/claude/fleet-lm-engine` a98fa35b.

## 1. The inventory (committed first: `tracks/milford-road-course-lm/source/furniture/`)

Read off NAIP 2022-08-16 (tile `m_4208327_ne_17_060_20220816`, `source/naip_2022_mrc.jpg` on its true extent, ledger
0062; 0.50 x 0.68 m pixels). Every vertex is a pixel read by eye off a crop with a labelled source-pixel grid
(`grid.py`), +-1 px. Identity comes from form (posts, turned-down terminals, segmented bars) and from tone (`rgb.py`): a
shadow on this image reads blue (b/r 1.1-1.9), so the black bars, which read neutral (b/r 0.89-0.95), are black objects
and not shadows. The sun on the image (`sun.py`, the tent's shadow vector) stands at azimuth ~113 deg, elevation ~42 deg
(10:40 EDT; +-7 deg of azimuth = 36-46 deg). No lidar point cloud is in the repo or the Mac's caches (the camber survey
kept only its plane fits), and OSM is not cached: **no height below is measured**.

| id | what | where | size | height (source) | identity | built |
|---|---|---|---|---|---|---|
| G1 | W-beam | NW corner, outside, between the apron and the boundary | 106.5 m | 0.70 m [invented: standard] | high | yes |
| G2 | W-beam | front straight, east (infield) side, across S/F | 556.1 m | 0.70 m [invented] | high | yes |
| G3 | W-beam | front straight, west side, s 4,516-4,711 | 195.7 m | 0.70 m [invented] | medium-high | yes |
| G4 | W-beam | infield between the NW hairpin's exit and the esses | 362.2 m | 0.70 m [invented] | high | yes |
| T1 | tyre wall | NW hairpin exit, 13 m west of G4's north end | 43.9 x 1.5 m | 1.0 m [invented] | medium | yes |
| T2 | tyre wall | esses, in front of G4 at the east leg's bend | 52.9 x 1.2 m | 1.0 m [invented] | medium | yes |
| T3 | tyre wall | the back of the s 1,000 run-off apron (ledger 0069's corner) | 32.4 x 1.5 m | 1.0 m [invented] | medium | yes |
| S1, S2 | containers / site trailers | the ride pad's west edge | 4.5 x 12.8, 3.5 x 12.1 m | 2.6 m [invented] | medium | yes (visual) |
| F1 | something tall | the NW boundary (apron to the outside road / lot) | 256.7 m | 4-5 m by its shadow [low] | low: screen fence, wall or hedge | no (owed) |
| G5, G6, T4 | a short rail, a line behind T3, a dark line on the unused short-cut | | 34, 35, 44 m | - | low | no |
| T5, T6 | black bars beside mown two-tracks, 46-225 m off the lap | | 83, 103 m | - | low | no |
| U1 | the service road's portal under the lap at the SW climb | | 12.6 m | - | high | no (no bridge modelled) |
| P1 | the pad tent | ride pad | 20 x 53 m | eave 3.5 [invented]; its shadow reads 3.6-5.6 m | high | already in 0.1.0 |

**Looked for, not found at 0.6 m:** concrete walls along the lap; pit / paddock / garage buildings (the paddock is the
ride pad and its tent; the front straight's wide west half and the dark lot west of it are the only pit-like pavement,
unmarked); timing or control towers; light poles; signs; marshal posts; gates. Each is under a metre across or absent.
**What 0.1.0 has:** road, edge strip, turf ground, 4,431 tree cards, the pad tent (+ collider), the ride pad, the two
plant blocks. **What it lacks:** every item above marked "yes", F1, the portal.

## 2. What was built (all opt-in; `tools/author_bespoke_blend.py` `scenery.bespoke.rails`, `blocks`)

- **W-beam (kind `wbeam`, new).** Posts every 1.905 m (AASHTO M 180, as the 0.6.0 rail) on the built ground; the rail's
  face on the measured line, facing the nearest lap point; its top 0.70 m over the ground [invented: an NCHRP-350-era
  strong-post W-beam's 27-28 in, not measured here]. Visual `GUARDRAIL_W_*` (the engine's GUARDRAIL row,
  `wbeam_rail_diffuse.png`, UVs kept), collider `1WALL_GHOST_RAIL_*` (the transparent 1WALL_GHOST row) behind the face.
  G2 / G3 stand 0-1.7 m off the traced edge, inside the assembler's edge strip (the asphalt held 0.30 m + a 1.0 m
  [invented] grade): `over_strip` lets their posts stand over the strip, never over the lane.
- **Tyre walls (kind `tyres`, new).** Module lines of tyre columns (0.62 m [invented]) at the NAIP width, 1.0 m tall
  [invented]. They ride the `1WALL_TECPRO` prefix: engine-july's prep (frozen, Lake Murray's) keeps authored UVs only for the
  prefixes it lists, and binds a texture only by a pbr row; Milford has no Tec-Pro, so `texture_overrides["1WALL_TECPRO"]`
  is the tyre skin, generated (`tools/make_bespoke_assets.py tyre_wall`, CC0) and synced in by `ship.json sync_in.assets`.
- **Every new foot under its whole ground triangle** (`down_low`, capped 2.0 m [invented]): see the diagnosis below.
- **The pad sheds** as `blocks`: metal walls, tan / light roofs as the photo shows them, 2.6 m [invented]; 200+ m from the
  lap, so no collider (the block rule's 60 m).

## 3. The candidate builds (Mac, `tools/ship_track.sh` with the Mac Blender, EMPTY workshops in `/Volumes/Drive/codex/mf_work/`, `--no-install`, ENG = the engine-july snapshot's `scripts/` + `vendor/` with airoso's `assets/textures`)

Three builds: **b0** = 0.1.0's tree (a98fa35b, `git archive`), **c1** = the first candidate (a44a23ff + the sheds,
version 0.1.1), **c2** = the adopted candidate (4d38fd75, version 0.1.1; 6782e184's config byte for byte). b0 reproduces
0.1.0's committed records (the PC's): kinks 6.34 /km, severe 0, 38.2 MB.

| gate (BUILT artifact) | 0.1.0 (b0) | c1 | **0.1.1 (c2)** |
|---|---|---|---|
| drive_test: soft top / severe / undrivable / daylight gaps | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** |
| drive_test: kinks /km, vertex bumps, fold bumps, apron steps | 6.34, 16, 0, 5 | the same | **6.34, 16, 0, 5** |
| drive_test: obstructed stations, floating furniture | 0, 0 | 0, 0 | **0, 0** |
| drive_test: gated drops / far ledges (reported) | 0 / 22 | 0 / 22 | **0 / 22** |
| drive_test: barrier rows (race furniture only; none here) | 0 / 0 | 0 / 0 | 0 / 0 |
| drive_test verdict | PASS | PASS | **PASS** |
| audit_mesh A-K (D walls on a road, E walls floating) | CLEAN (walls 24 v) | **E 4, worst +1.52 m: RED** | **CLEAN** (walls 19,291 v; D 0, E 0) |
| verify_kn5 + --inis | PASS | PASS | **PASS** |
| kn5_ground_check | PASS: 4 wall objects, hovering 0; road-over-ground 7 / 9,314 > 5 cm, p95 0.021 m | PASS (14 wall objects) | **PASS: 21 wall objects, hovering 0, seat median -1.24 / p95 -0.27 m; road-over-ground 7 / 9,314, p95 0.021 m** |
| house_seat | PASS, 1 judged | PASS, 3 | **PASS, 3 judged** (floating / sunken / buried 0) |
| edge_report at 1 m (not a gate) | strip 100 % | strip 100 % | strip 99.5 %, wall 0.5 % (G2 / G3 at the edge) |
| chain | SHIP OK | exit 1 (audit) | **SHIP OK, no force** |

| kn5 | 0.1.0 (b0) | 0.1.1 (c2) |
|---|---|---|
| road `milford_road_course_lm.kn5` | 38,158,099 B (md5 ddc64d23…) | **40,646,952 B** (md5 c278c912…) |

**What c2 stood** (the author log): G1 107 m (58 posts, none out); **G2 465 of 556 m** (3 runs; 48 posts out, every one
on the lane: the traced 16 m includes the rail's line there); **G3 181 of 196 m** (7 out, the lane); G4 364 m (192
posts); T1 71 modules / 44 m, T2 85 / 53 m, T3 48 / 33 m (3 out at the lap's edge); the two sheds (2.6 m on 16.8-17.1 m
ground).

**c1's red, diagnosed (not forced).** audit E: 4 wall columns 1.44-1.52 m over every ground vertex within the rule's
4.5 m: G4's collider at (-208.5, 193.8) and T2's modules at (-198.0, 201.3), both on a single 1GRASS triangle 10.4 / 14.2
m across, its corners at 20.24-24.27 m (a ~40 % bank between the esses' legs). Each foot was 0.10-0.15 m under the
INTERPOLATED surface (`source/furniture/probe.py`: ground 21.87 / 21.25 m, feet 21.77 / 21.10): seated, as
kn5_ground_check's tri-exact read agreed (hovering 0). The rule reads nearest vertices; the coarse triangle's high
corners were beyond its reach. Fix: the new kinds' feet go under the lowest corner of the triangle they stand on
(`down_low`), at most 2.0 m [invented] under their ground (inside drive_test's +-2.5 m support window). No threshold
moved. c1 also left 184 / 65 of G2 / G3's posts out on the assembler's edge strip, which the trace's width and its 1.0 m
[invented] grade put over the measured rails: `over_strip` (opt-in) lets them stand over the strip, never the lane.

## 4. Lake Murray unchanged

- The diff of `tracks/san-diego-lake-murray` and `scripts/` against `origin/claude/fleet-lm-engine`: **empty** (at 6782e184).
- **Trim A/B** (`/Volumes/Drive/codex/mf_work/lmtrim/`): Lake Murray's committed trim inputs through fleet-lm-engine's
  `tools/trim_connectors.py` (a98fa35b) and this branch's: **byte-identical** (`664da93b…`, `b73b70f4…`, `f0c97952…`), the
  logs identical too.
- **Opt-in by key** (`tests/tools/test_milford_furniture.py::test_keys_are_opt_in`): no config but Milford's port names
  the `wbeam` / `tyres` kinds, `depth_m`, `over_strip` or the tyre skin. In shared code the only change a config that
  names none of them reaches is `bvh()` recording each polygon's lowest corner (a list nothing else reads), the
  `1WALL_GHOST_RAIL` prefix in `OWN_PREFIXES` and the guardrail lip filter (objects only the new kind writes). Lake
  Murray's chain runs `author_bespoke_blend.py` for its blocks only: no rails, no guardrail.
  `make_bespoke_assets.py --check`: every committed asset matches the generator.
- **Tests:** `tests/run_tests.py` (the .venv python, `python` on PATH): **1,284 pass, 8 fail**, the same 8 as round K's
  baseline (`test_draft_equiv` x5, `test_registry_moves` x1, `test_bench_pad` x2), none in a file this round touches.
  New: `test_milford_furniture.py`, 7 pass.

## 5. Stills

Blender EEVEE on c2's split scene, NAIP's own sun (az 113, el 42), `source/furniture/furniture_stills_blend.py`; on
this Mac, not in the repo (`/Volumes/Drive/codex/mf_work/stills/`):
- `mf011_pitstraight_G2_G3.jpg`: the front straight northbound, G3 ahead-left, G2 along the right;
- `mf011_nw_corner_G1.jpg`: G1 outside the NW corner;
- `mf011_hairpin_exit_T1_G4.jpg`, `mf011_above_nw_infield.jpg`: T1 and G4's north end;
- `mf011_esses_T2_G4.jpg`: T2 in front of G4 on the bank (the modules step up the bank, each flat-topped);
- `mf011_s1000_apron_T3.jpg`: T3 at the apron's back;
- `mf011_above_pad_sheds.jpg`: the ride pad, the tent and the two sheds.

Not seen in game.

## 6. What is invented (every one also in `fleet/GATES-CHANGELOG.md` 2026-11-06)

- The W-beam's top, 0.70 m; its post / blockout / collider depths (0.15 / 0.20 / 0.20 m).
- The tyre walls' 1.0 m height and 0.62 m column; their widths are NAIP's.
- The sheds' 2.6 m walls.
- The feet's 2.0 m cap under the ground.
- Identity, where the table says medium: the tyre walls by tone and form, never seen on video.

## 7. Downloads that would turn the inventions into measurements (none fetched; Kevin's call)

| file | source | size | turns into |
|---|---|---|---|
| USGS 3DEP point cloud, EPT `USGS_LPC_MI_31Co_Oakland_2016_LAS_2019`, the nodes within ~45 m of the lap (`tools/lidar_wall.py` both sides, as High Plains' survey in ledger 0078 round 5) | `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_MI_31Co_Oakland_2016_LAS_2019/ept.json` | not measured; the camber survey's 5 m read of the same project took 97 s on the G10; expect tens of MB | every rail / tyre-wall / F1 height; G5 / G6 / T4's identity; the east side under the trees |
| OSM, the MPG box (`way[barrier]`, `building`, `highway=street_lamp`, `man_made`) | `https://overpass-api.de/api/interpreter`, bbox -83.6700,42.5605,-83.6570,42.5795 | ~0.1-1 MB | any mapped fence, gate, building or lamp |
| Onboard laps (DOSSIER A2.3): Mero's ZR1 lap; the 2013 Autoweek Stingray lap | `https://www.youtube.com/watch?v=tNRWvk5nMu0`; `https://www.corvetteblogger.com/2013/08/05/video-take-a-lap-around-the-milford-proving-grounds-in-the-2014-corvette-stingray/` | ~100-300 MB each | the tyre walls' identity, F1, signs, marshal posts, the white line on the straight |
| Another NAIP vintage on the same frame (the trace README's ImageServer export, another date) | `https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage` | ~2-6 MB | a second sun angle: shadow heights for F1 and the tent; a check on every line |

## 8. PC runbook 4n: rehearse 0.1.1 from a clean checkout (no install)

The shape of 0079's runbook 4m. **Rehearse only: no install** (installs happen on Kevin's word).

1. A clean checkout at `6782e184` or later on `claude/milford-furniture-lm` (`git lfs pull` is not needed for this track:
   the port builds from an EMPTY workshop and reads no blend). ENG = round 4b's `D:/k10-scratch/eng_mflm`, unchanged:
   every new texture comes from airoso through `ship.json sync_in.assets`. Check the synced copies in the workshop's
   `assets/textures/`: `tyre_wall_diffuse.png` c7f4764d722ae452b0306d2d6cbc7d62, `metal_wall_diffuse.jpg`
   326b3841477610400a7926a577926ee7, `metal_wall_normal.jpg` 5a1721de1b28d55e11b86908b27e2936, `roof_tan_diffuse.jpg`
   247c5d4f295e6cf8fab875bcd21b0596.
2. An empty workshop, the whole chain, no install:
   ```bash
   SHIP_PROJ=D:/k10-scratch/milford_lm_f1_reh AIROSO=<that checkout> ENG=D:/k10-scratch/eng_mflm \
     bash tools/ship_track.sh milford-road-course-lm --no-install
   ```
3. Compare every row of section 3's 0.1.1 column with the run's `data/drive_test.full.json`, `audit.json`,
   `kn5_ground_check.full.json`, `house_seat_check.json`, `edge_report.json` and the log's verify_kn5 lines
   (`python tracks/milford-road-course-lm/source/furniture/gate_table.py <rehearsal>` prints them; it reads
   `<rehearsal>.log` beside the folder), and the author log's rail lines (G2 465 m / 48 out, G3 181 m / 7 out, T3 3 out).
   Known noise: +-1-3 grass vertices. Every gate row equal, else stop and report the row.
4. The kn5 bytes: the Mac's road kn5 is 40,646,952 B; expect it within the ground noise (`tools/kn5_equiv.py` against a
   carried-over Mac copy when there is one; never md5, ledger 0065). The installed 0.1.0 is untouched.
5. Push the rehearsal's records on a branch of their own only if a row differs; no install.

## Owed (after pass 1; start here)

Start here:

1. **Heights off the lidar** (Kevin's go on the EPT read, section 7): `tools/lidar_wall.py` beside the whole lap, both
   sides, to ~45 m. Replace every `[invented]` height (W-beam 0.70, tyre walls 1.0) with the measured top; confirm or
   drop T1-T3's identity (a tyre wall reads as a ~1 m band of returns, a screen as a tall thin one); read F1.
2. **F1, the tall thing along the NW boundary**: 257 m, its shadow reads 4-5 m. A screen fence, a wall or a hedge: the
   lidar (1) or an onboard frame says which; then build it (a physical class) or plant it.
3. **G2 / G3's 91 + 15 m left out on the lane**: the rail line and the traced 16 m width disagree by up to a pixel on
   the straight. Re-measure the straight's edges against the rails (a newer NAIP, or the lidar's road plane) and narrow
   the lane there or move the line; then build the rails whole.
4. **The low-confidence lines**: G5 (east straight inside), G6 (behind T3), T4 (the unused short-cut's hairpin), and the
   east side under the tree shadow: the lidar (1).
5. **Signs, light poles, marshal posts, the white line ~260 m south of S/F**: not resolvable at 0.6 m; the onboard laps
   (section 7) are the only source in reach. Nothing is built from a guess.
6. **The underpass portal** (U1) and the deck over the service road: a bridge the port does not model (route notes: the
   2 m dip at s 3,605); its headwalls are furniture once the deck is.
7. **The look, in game**: the tyre walls step up the esses' bank module by module; the W-beam runs end without
   terminals. Kevin's drive decides whether either matters.
8. **The PC rehearsal** (section 8), then Kevin's word on an install of 0.1.1 beside 0.1.0.

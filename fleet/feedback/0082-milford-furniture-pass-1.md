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
   the port builds from an EMPTY workshop and reads no blend). ENG = round 4b's `D:/k10-scratch/eng_mflm` **plus
   airoso's `assets/textures` at the head being built, md5-checked** (corrected after the PC's first run, below: pbr's
   stock table reads ENG's `assets/textures` only, so `wbeam_rail_diffuse.png`, `ghost_alpha.png` and the three
   shed / roof textures were referenced but not embedded; `sync_in.assets` reaches the workshop, which only
   `texture_overrides` reads). Check the synced copies in the workshop's
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

## PC rehearsal 0082-1 (2026-11-06): MATCHED on the second run

- **Run 1** (`D:/k10-scratch/milford_lm_f1_reh`, ENG `eng_mflm` as section 8 first said): every gate row equal to the
  0.1.1 column and the author log equal (G1 107 / G2 465, 48 out / G3 181, 7 out / G4 364 m; T1-T3 71 / 85 / 48
  modules, 3 out; sheds 2.6 m), but the road kn5 40,611,042 B, 35,910 B short: 5 textures referenced and not embedded
  (`ghost_alpha.png` on the 4 `1WALL_GHOST_RAIL_*` colliders, `wbeam_rail_diffuse.png`, `metal_wall_diffuse.jpg`,
  `metal_wall_normal.jpg`, `roof_tan_diffuse.jpg`). In AC the ghost colliders would have taken pbr's flat fallback and
  likely shown as solid walls. **No gate caught it; the byte count did.**
- **Run 2** (`D:/k10-scratch/milford_lm_f1b_reh`, ENG `eng_mflm_f1` = `eng_mflm` + airoso's `assets/textures` at
  2d4f56be, 38 added, 57 identical, md5-checked): every gate row equal, SHIP OK with no force, road kn5 40,646,952 B
  (the Mac's size), 20 textures embedded, none referenced-but-missing. md5 differs from the Mac's (tangents, as every
  Mac rerun); no Mac copy on the PC for kn5_equiv.
- **Rule for every PC runbook from here** (coordinator, 2026-11-06): ENG = the engine snapshot + airoso's
  `assets/textures` at the head being built, md5-checked.
- **Owed (engine):** a gate that every texture a kn5's materials name is embedded in it; proven on Lake Murray's real
  built kn5s before it gates anything.

## Owed after pass 1 (superseded: start at "Owed (after pass 2; start here)" at the end)

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
8. **The PC rehearsal**: done, matched (above). Kevin's word on installing 0.1.1 over the installed 0.1.0 (the PC asks).
9. **The texture gate** (above): every texture a kn5 names is embedded.

---

# Pass 2 (2026-11-06): the heights off the lidar, F1 built, the texture gate, 0.1.2

Kevin, 2026-11-06, to "Fetch the lidar for Milford (size unmeasured, est. tens of MB) and Del Mar (2 tiles, 129 MB)?":
**"Yes, fetch both"** (Milford's half: the 3DEP EPT within ~45 m of the lap; stop above 100 MB). Commits on
`claude/milford-furniture-lm`: d9d8bcc7 (the read), bd04574f (the heights, F1), 3a0c3c39 (the gate), ab660775 (tests /
TLS), d2982862 (version), 85ec24a8 (the screen's panels), 522e0e80 (0.1.2's records), 5ec89c3a (stills script).

## P2.1 The read (`tracks/milford-road-course-lm/source/lidar/`, README there)

- `USGS_LPC_MI_31Co_Oakland_2016_LAS_2019`. **Flown 2017-05-03** (14:10-14:39 UTC, the points' GPS time): five years
  before NAIP 2022-08-16.
- Sized first (`scripts/ept_plan.py`: hierarchy + HEAD only): every node whose box comes within the lane edge + 45 m,
  **71 nodes, 39,604,920 B** of LAZ (under the 100 MB stop), then fetched; + 46,380 B of metadata.
- **5,727,790 points read, 1,427,749 kept** within the lane edge + 45 m: ground 931,962, unclassified 495,390 (no
  building class), noise 291, water 29, class 10 77. Ground density on the item lines 1.2-2.9 / m2.
- Raw tiles on the Mac only: `/Volumes/Drive/codex/lidar_dl/milford_oakland2016/`. Committed: `lidar_read.json`, a 1 m
  grid (`milford_lidar_1m.npz`, 943 kB), `sumitems.json`, `f1.json`, `f1_entries.json`, `poles.json`, `overview.jpg`,
  four cross-sections, the scripts.

## P2.2 What the lidar measured, object by object

**The flight predates the rails and the tyre walls.** The lap was paved in May 2017 (the intensity grid shows the whole
circuit and its painted lines), but nothing stood on any rail or tyre line. Within 1 m of each line, returns 0.35-1.6 m
over the ground per metre, against ~0.5-1.0 / m that a W-beam (rail + blockout + post, ~0.35 m deep in plan) would give at
that density, and against F1's 3.1 / m on the same flight:

| object | pass 1 (invented) | pass 2 |
|---|---|---|
| G1 W-beam, 107 m | 0.70 m | 0.09 / m: **nothing in 2017. Not measurable; stays 0.70 m [invented]** |
| G2 W-beam, 556 m | 0.70 m | 0.04 / m: as G1 |
| G3 W-beam, 196 m | 0.70 m | 0.03 / m: as G1 |
| G4 W-beam, 362 m | 0.70 m | 0.00 / m: as G1 |
| T1 / T2 / T3 tyre walls | 1.0 m | 0.00 / m each: no ~1 m band. **Identity neither confirmed nor dropped** (NAIP 2022 still shows the black bars); stays 1.0 m [invented] |
| S1 / S2 sheds | 2.6 m | 207-257 m from the lap, **outside the read**: stays 2.6 m [invented] |
| P1 tent eave | 3.5 m | outside the read: stays [invented] |
| **F1, the NW boundary** | 4-5 m by its shadow, not built | **measured: 4.06 m (NE 112 m), 3.54 m (20 m step), 3.18 m (SW 63 m); built** |
| G5 (rail?) | not built | 0.27 / m: ~10 returns 0.2-0.9 m in 7 m at one end, a shrub's shape: **not confirmed, not built** |
| G6, T4 | not built | 0.00 / m: **not confirmed, not built** |
| U1 portal headwall | not built | 0.6-1.6 m returns (0.56 / m); its deck is not modelled: not built |

The buffer-wide scan (`scripts/lines.py`) agrees: **no linear structure 0.4-1.4 m tall longer than 16 m anywhere within
45 m of the lap**.

**F1 is a screen, not a hedge.** 197 m of it inside the read (s 262-393, 11.7-44.6 m off the edge). One thin line of
returns (plan sd 0.39 m), 93 % of the top returns single pulses with returns down its face (opaque), a level top (p90 per 4
m bin 3.92-4.33 m over the NE 112 m) stepping down to 3.1-3.35 m in the SW. NAIP 2022 reads the line itself light grey
(R 204-212) with the shadow 2-4 m WNW. A hedge's top would wander and spread. **A light, opaque screen ~4 m tall: a precast
screen wall or a screened fence**; the lidar cannot say which. The NE ~60 m (45-74 m off the edge) is outside the read.

**What NAIP missed** (`poles.json`): an overhead line's wires along the east side (single returns 10.7-12.8 m up, s
3,177-3,496, 27-32 m off; poles in the treeline, not separable): not built. Two small objects (2.4 m, 4.3 m) 3 m inside
the traced edge on the s 960-986 apron in May 2017: on the pavement, transient: not built. Sparse 1.7-2.4 m returns
along the W / NW boundary that may be a chain-link's top rail, mixed with shrubs: not confirmed, not built. No isolated
light pole or sign within 45 m of the edge.

## P2.3 What was built, dropped, changed

- **F1 built**: rails kind `screen` (new, opt-in; `tools/author_bespoke_blend.py`): `1WALL_TILTUP_SCREEN_<k>`, a
  collider on the stock tilt-up concrete row (UVs kept by engine-july's prep, real-metre UVs), on the line fitted
  through F1's own returns, at the three measured heights; an entry without a measured `height_m` is refused. Panels
  4.0 m nominal, fitted whole to each segment (c3 fitted whole 4 m panels per ~4 m segment and stood only 20 panels / 80
  m: caught in the author log, fixed in 85ec24a8; c4 stands 29 + 5 + 16 = 50 panels over 197 m), 0.20 m thick
  [invented], feet under the whole ground triangle as the tyres'.
- **Kept as pass 1 built them**: G1-G4, T1-T3, the sheds; every `_source` now carries the lidar's word and stays
  [invented]. `source/furniture/inventory.json` carries a `lidar_2017` reading per item.
- **Dropped**: nothing that was built. G5, G6, T4 stay unbuilt (not confirmed).

## P2.4 The texture gate (`tools/kn5_textures.py`, GATES-CHANGELOG 2026-11-06)

Every texture a built kn5's materials name must be embedded in it (exact name; an empty map or a zero-byte texture
fails too). Opt-in: `gate_kn5_textures` in `tools/ship_track.sh`, named only by Milford's ship.json (after
`kn5_ground`), on `$PROJ/build/*.kn5`, `data/kn5_textures.json`. Proven: c2 PASS (20 / 34 / 48 textures / materials /
maps), b0 PASS (14 / 22 / 35), c4 PASS in the chain (20 / 37 / 54); a copy of c2's kn5 with the PC run 1's five
textures cut from its texture section comes to **40,611,042 B, run 1's size to the byte, and FAILS naming all five**
(`ghost_alpha.png` x 4 materials, `wbeam_rail_diffuse.png` x 3, `metal_wall_diffuse.jpg`, `metal_wall_normal.jpg`,
`roof_tan_diffuse.jpg`). Not fleet-wide: the Mac has no Lake Murray build; the PC runs it on every installed kn5 first
(0082-2 step 5).

## P2.5 The candidate (Mac, EMPTY workshops in `/Volumes/Drive/codex/mf_work/`, `--no-install`)

ENG = `/Volumes/Drive/codex/mf_work/eng2`: the engine-july snapshot's `scripts/` + `vendor/` (0 files differ from
pass 1's) + airoso's `assets/textures` at d2982862, **96 / 96 md5-identical**. c3 = d2982862 (the holed screen), **c4 =
85ec24a8, version 0.1.2, adopted**. No force anywhere.

| gate (BUILT artifact) | 0.1.1 (c2) | c3 | **0.1.2 (c4)** |
|---|---|---|---|
| drive_test: soft top / severe / undrivable / daylight gaps | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** |
| drive_test: kinks /km, vertex bumps, fold bumps, apron steps | 6.34, 16, 0, 5 | the same | **6.34, 16, 0, 5** |
| drive_test: obstructed stations, floating furniture, off-pavement | 0, 0, 0 | 0, 0, 0 | **0, 0, 0** |
| drive_test verdict | PASS | PASS | **PASS** |
| audit_mesh A-K | CLEAN (walls 19,291 v) | CLEAN (19,875 v) | **CLEAN (walls 20,743 v; D 0, E 0, worst float 0.0)** |
| verify_kn5 + --inis | PASS | PASS | **PASS** |
| kn5_ground_check | PASS: 21 wall objects, hovering 0, seat median -1.238 / p95 -0.268 m; road-over-ground 7 / 9,314, p95 0.021 m | PASS: 26 walls | **PASS: 24 wall objects, hovering 0, median -1.238 / p95 -0.268 m; road-over-ground 7 / 9,314, p95 0.021 m** |
| kn5_textures (new) | PASS 20 / 34 / 48 (run after) | PASS 20 / 37 / 54 | **PASS 20 / 37 / 54, none missing** |
| house_seat | PASS, 3 judged | PASS, 3 | **PASS, 3 judged** |
| edge_report at 1 m (not a gate) | strip 99.5 %, wall 0.5 % | the same | **strip 99.5 %, wall 0.5 %** |
| chain | SHIP OK | SHIP OK | **SHIP OK, no force** |

| road kn5 `milford_road_course_lm.kn5` | 0.1.1 (c2) | **0.1.2 (c4)** |
|---|---|---|
| bytes | 40,646,952 (md5 c278c912…) | **40,714,845** (md5 d06ec161…) |

Author log, c4: G1 107 m / 0 out; G2 465 m, 48 out; G3 181 m, 7 out; G4 364 m; T1-T3 71 / 85 / 48 modules, 3 out;
**f1_nw_screen_ne 29 panels / 113 m, _step 5 / 21 m, _sw 16 / 63 m, 0 out**. The committed `data/` records are c4's
(they were 0.1.0's).

## P2.6 Lake Murray unchanged

- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`: **empty**.
- **Trim A/B** (`/Volumes/Drive/codex/mf_work/lmtrim2/`): fleet-lm-engine's `tools/trim_connectors.py` + `scripts/`
  (git archive) and this branch's, each on a fresh copy of the committed trim inputs: **byte-identical**
  (`664da93b…`, `b73b70f4…`, `f0c97952…`), logs identical.
- Opt-in by key: `test_milford_furniture.py::test_keys_are_opt_in` (now with `screen`), `test_kn5_textures.py::
  test_the_gate_is_opt_in` (only Milford's ship.json names the gate).
- **Tests** (`tests/run_tests.py`, the .venv python on PATH): **1,291 pass, 8 fail**, the known 8 (draft_equiv x5,
  registry_moves, bench_pad x2). New: `test_kn5_textures.py` 6; `test_milford_furniture.py` 8.

## P2.7 Stills (Blender EEVEE, NAIP's sun; the Mac only, `/Volumes/Drive/codex/mf_work/stills2/`)

`source/furniture/furniture_stills_pass2_blend.py` on c2 and c4, the same cameras: `mf_c2_*` / `mf_c4_*`
`lap_F1_ne_back`, `lap_F1_ne_ahead`, `lap_F1_sw_back`, `lap_F1_sw_ahead` (the driver's eye 45 m either side of each
piece) and `above_nw_boundary_F1`. 0.1.1 shows open grass to the NW boundary; 0.1.2 shows the grey panel wall behind
G1, stepping down to the SW. The fitted line carries the lidar's ~0.4 m jitter: the panels zig-zag gently seen from
above. Not seen in game.

## P2.8 What is still invented

- Every rail top (0.70 m) and tyre wall top (1.0 m): the only lidar predates them.
- The sheds' 2.6 m and the tent's eave: outside the read.
- The W-beam's post / blockout / collider depths; the tyre column; the screen's panel (4.0 m) and thickness (0.20 m);
  the feet's 2.0 m cap.
- F1's identity between a wall and a screened fence; its NE ~60 m (outside the read) is not built.
- The tyre walls' identity (NAIP tone and form only).

## PC runbook 0082-2: rehearse 0.1.2 from a clean checkout, and the texture check on every installed kn5 (no install)

1. A clean checkout at the ledger's pass-2 commit or later on `claude/milford-furniture-lm` (no `git lfs pull` needed:
   the port builds from an EMPTY workshop).
2. **ENG = round 4b's `D:/k10-scratch/eng_mflm` + airoso's `assets/textures` at the head being built, md5-checked** (the
   rule after 0082-1): 96 files, every one equal to the checkout's. Spot md5s: `tiltup_wall_diffuse.jpg`
   7a4ed52a856098256fd63b6e23a71de1 (F1's screen, new in 0.1.2), `tiltup_wall_normal.jpg` 2e7a85baf12bc77e0dd39ddeef12ea9e,
   `ghost_alpha.png` 33f4744856ed62b26778f5a2d325adbd, `wbeam_rail_diffuse.png` a9e3650a0f3097aed63b661d926fbe19,
   `tyre_wall_diffuse.png` c7f4764d722ae452b0306d2d6cbc7d62.
3. An empty workshop, the whole chain, no install:
   ```bash
   SHIP_PROJ=D:/k10-scratch/milford_lm_f2_reh AIROSO=<that checkout> ENG=<ENG of step 2> \
     bash tools/ship_track.sh milford-road-course-lm --no-install
   ```
   The chain now runs `kn5_textures` after `kn5_ground`: it must print PASS (20 textures, 37 materials, 54 maps).
4. Compare every row of P2.5's 0.1.2 column (`python tracks/milford-road-course-lm/source/furniture/gate_table.py
   <rehearsal>`) and the author log's rail lines (above, with **f1 29 / 5 / 16 panels**). Known noise: +-1-3 grass
   vertices. The road kn5: the Mac's is 40,714,845 B; expect it within the ground noise (`tools/kn5_equiv.py` against a
   carried Mac copy when there is one; never md5). Every row equal, else stop and report the row.
5. **The texture check on every installed track's kn5s** (read-only; this decides whether the gate goes fleet-wide):
   ```bash
   python tools/kn5_textures.py "<AC>/content/tracks" --recursive --json D:/k10-scratch/kn5_textures_installed.json
   ```
   Report, per track folder, PASS / FAIL and every missing name, Lake Murray's kn5s first. Fix nothing.
6. Push the rehearsal's records and the installed-kn5 report as data only; **no install**. Installing 0.1.2 over what is
   installed is Kevin's word: the PC asks.

## Owed (after pass 2; start here)

1. **The PC: runbook 0082-2** (above): rehearse 0.1.2, and run `kn5_textures` on every installed kn5. Then Kevin's word on
   installing 0.1.2.
2. **The texture gate fleet-wide**: once 0082-2 step 5 is clean on Lake Murray's installed kn5s (or every FAIL is
   explained), name `kn5_textures` in every ship.json (and Lake Murray's chain of record), with a GATES-CHANGELOG entry.
3. **Rail and tyre heights**: the 3DEP flight over the lap (2017) predates them. The onboard laps (DOSSIER A2.3; section 7
   above: ~100-300 MB each, not approved) or another NAIP vintage's shadows are the sources left; ask Kevin before
   fetching.
4. **F1**: its NE ~60 m (45-74 m off the edge) is outside the read: a second, small read (the nodes there) would let it
   stand whole. Wall or screened fence: an onboard frame says which. The fitted line could be smoothed further (a
   straight-segment fit) if the zig-zag shows in game.
5. **G2 / G3's 91 + 15 m left out on the lane** (pass 1 Owed 3): the 2017 intensity grid shows the pavement edges
   plainly; re-measure the straight's edges against them (the pavement may have changed by 2022) and narrow the lane or
   move the rails' lines.
6. **The underpass portal (U1)**: the lidar reads its headwall (0.6-1.6 m); still waits on the deck.
7. **Signs, light poles, marshal posts, the white line on the straight**: none resolvable in the 2017 lidar either (no
   isolated pole within 45 m); onboard laps only.
8. **The look, in game** (pass 1 Owed 7, plus F1): Kevin's drive decides.

## PC: the 0.1.1 install (2026-11-06)

- **INSTALLED on Kevin's word** (2026-11-06, "Install over 0.1.0 (Recommended)", asked with: the heights are standard
  sizes, not measured): 2d4f56be from an empty `D:/k10-scratch/milford_lm` (0.1.0's workshop parked as
  `milford_lm.0.1.0`), ENG `D:/k10-scratch/eng_mflm_f1` (eng_mflm + airoso's `assets/textures` at 2d4f56be, md5-checked:
  0082-1's run 1 on eng_mflm alone left 5 textures out of the kn5); every gate green, SHIP OK, no force. 0.1.0's folder
  parked in `D:/k10-track-archive/2026-11-06_163602/`; `milford_road_course_lm` 0.1.1, kn5 40,646,952 B,
  kn5_equiv-equivalent to the 0082-1 run-2 rehearsal (tangents only). The sync-back's records are on their own branch
  `claude/milford-lm-0101-installed` (0c74170): this branch's later rounds rewrote the same `data/*.json`. Not driven yet.

## PC: rehearsal 0082-2, the installed-kn5 texture check, and the 0.1.2 install (2026-11-07)

- **0082-2 MATCHED** (1357968b, `D:/k10-scratch/milford_lm_f2_reh`, ENG `D:/k10-scratch/eng_mflm_f2` = eng_mflm +
  airoso's `assets/textures` at 1357968b, 96/96 md5-equal; tiltup_wall diffuse 7a4ed52a / normal 2e7a85ba): kn5_textures
  PASS (40,714,845 B, 20 textures, 37 materials, 54 maps; missing / empty / zero-byte / unused 0); drive_test 0/0/0/0,
  kinks 6.34, vertex bumps 16, apron steps 5, obstructed 0, floating 0; audit CLEAN (walls 20,743 v); verify_kn5 + --inis
  PASS; kn5_ground_check PASS (24 walls, hovering 0, seat median -1.24 / p95 -0.27); road over ground 7 / 9,314; house_seat
  PASS (3); F1 29 / 5 / 16 screen modules over 113 / 21 / 63 m, 0 left out; road kn5 40,714,845 B (the Mac's size; md5
  8e8da5b3, tangents).
- **Step 5, `tools/kn5_textures.py` on every installed kn5** (read-only, 2026-11-07 after the installs below;
  `source/furniture/kn5_textures_installed.json` + `.summary.txt`): **Lake Murray `san_diego_lake_murray_v4` PASS on all
  13 kn5s**; every doooom folder PASS (15 folders: the 13 `_lm` + `del_mar_fairgrounds` 0.1.0 + Lake Murray). Not ours:
  93 folders, 2 with a FAIL, not fixed: `berowra_valley_national_park` (`asquith_start.kn5` / `asquith_start_reverse.kn5`,
  6 missing each) and `vn_motorland_aragon_complex` (`xtras_speed.kn5`, 3 missing) — names in the JSON. The tool exits 1
  on those third-party FAILs.
- **INSTALLED on Kevin's word** (2026-11-07, "Install over 0.1.1 (Recommended)"): 1357968b from an empty
  `D:/k10-scratch/milford_lm` (0.1.1's workshop parked as `milford_lm.0.1.1`), ENG eng_mflm_f2; kn5_textures PASS in the
  chain; SHIP OK, no force. 0.1.1's folder parked in `D:/k10-track-archive/2026-11-07_134653/`; `milford_road_course_lm`
  0.1.2, kn5 kn5_equiv-equivalent to the rehearsal (tangents only). Records with this note (no record path changed on this
  branch since 1357968b). Not driven yet.

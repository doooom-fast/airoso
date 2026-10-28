---
id: 0058
title: "Rebuild the Colorado tracks, Sand Creek first" — Sand Creek's lap re-sourced onto OSM and the draft built from a clean checkout again
status: diagnosed — all four gates PASS on the 2026-10-28 draft (drive_test forward + reverse, audit CLEAN, verify_kn5 incl. --inis, kn5_ground_check); packed build/sand_creek_raceway_v0.27.0.zip (version bumped from July's 0.26.0); not installed, no seat verdict
scope: tracks/sand-creek (proof case); the engine fixes reach every build.sh track — see Scope
layer: engine (+ project: tracks/sand-creek/track.config.json source block)
train: -
---

## Symptom

Kevin, 2026-10-27/28 (to astra, then here): rebuild the Colorado tracks in airoso, Sand Creek first, then High
Plains. Nothing of it had started. From a clean checkout `scripts/build.sh tracks/sand-creek` could not get past
its first stage, and every stage after it had a defect of its own waiting.

## Decision (Kevin, 2026-10-28: "Yes, defaults")

The lap is the first LineString of `source/Sand Creek Raceway Drive-3.kml` (Colorado & 48th → Colorado & 48th,
9,687 m, closed), map-matched onto the OSM drivable network so its geometry is OSM's (L1). The second LineString
(Colorado & 48th → 6409 E 45th Ave, open, 9,680 m, through the 49th / Pontiac / Oneida / Monaco / Ivy interior
grid) is set aside — probably the dropped `interior` layout. Config: `source.line 0`, `source.connector_lines {}`,
`source.snap "osm"`.

## Evidence → diagnosis → fix, in the order the build hit them

1. **build.sh's pre-flight refused every track**: `assets/textures/mutcd_w1-8l/r.png` were 1024×1365 (L7). Lake
   Murray never saw it (`tools/ship_sd.sh` skips the pre-flight). `tools/make_sign_textures.py` now renders the
   18×24 in chevron at 768×1024 centred on a transparent 1024×1024 canvas; nothing binds these files today.
2. **The gps stage ignored `source.type`** (KeyError `route["roads"]`). `scripts/gps/centerline.py:main` now
   dispatches `kml` to `centerline_from_kml`, which gained the `line` / `connector_lines` / `snap` keys.
3. **`map_match` chorded 4.3 km of the lap.** A short GPS blip merged into a neighbouring way kept the arc it
   carried along the *other* way, so the run was cut at a foreign arc and the stitch drew a straight line —
   Sand Creek Dr South (2,779 m) was cut `2 → 2`. Measured: the first "match" was 9,538 m of which only ~5,242 m
   followed OSM. Fix: re-project each run's end fixes onto the run's own way (`_arc_on`). After: 9,677 m, within
   4.2 m of the KML both ways. Regression test
   `tests/gps/test_mapmatch.py::test_a_blip_merged_at_a_run_end_is_reprojected_onto_the_run_way` fails on the old
   code (first point 250.7 m off).
4. **Two Overpass fetches had no snapshot** (L2) and Overpass returned 502/504 three times that morning.
   `overpass.post_cached` (the `fetch_ways` fingerprint contract for any query) now backs
   `fetch_drivable_ways` → `data/osm.cache.json` and `street_labels` → `data/street_labels.osm.cache.json`. The
   duplicate `fetch_drivable_ways` definition is gone.
5. **`street_labels` ran in the gps stage** but reads `data/centerline.local.json`, which the project stage
   writes: a clean checkout crashed, and a rebuild labelled the new lap against the previous build's local line.
   It now runs right after projection (`labels`).
6. **build_mesh had no default road edge.** The natural_ground port (6f1c734) turned the shoulder arm's `else:`
   into `elif natural_ground:`, so every track with neither `profile: sidewalk` nor `natural_ground` crashed
   (`UnboundLocalError: edge_group`) — every `build_mesh` track except IMI (Lake Murray builds with its
   quarantined `scripts-v021`, not `build_mesh`). The pre-port call is restored unchanged as the default arm.
7. **drive_test FAIL, floating furniture 6.** All `1WALL_PARA_stone` from the 0025 measured-guard pass: 4 columns
   at the third creek crossing (st 6,522 / 6,580, 7–8 m off the line, bases 4.8–5.0 m below the deck — chained
   lips on the creek-channel slopes, 3.4–7.7 m below the deck from 6,516 to 6,613), 2 on a cut bank (st
   7,990–7,993, +7.3–8.2 m, base 1.6 m over the deck hovering 1.35–1.63 m over the ground under it). Two
   mechanisms: (a) the gate skips its excursion sweep inside declared bridge spans ±20 m, but the pass that exists
   to mirror that sweep did not, so it guarded drops the gate never measures; (b) a lip stands inboard of the drop
   but took the crest's height for its base. Fix: skip declared spans ±20 m exactly as the gate does; seat each
   lip's base on the lowest ground under its own corners, top unchanged (the gate credits a guard by its top, so
   credit is unchanged).
8. **drive_test FAIL, soft-top 1 at st 8,047** — the one 0025 deferred. Cross-section: road edge at +6.0, flat
   shoulder to +8.5 at deck height, but grass +0.51 … +1.06 m *above* the shoulder from +6.25 outward, rising at
   exactly 20%: the seam-weld floor (`source − 0.01 − 0.20·d`) radiating from the cut's bank crest lifted the
   shoulder's own pinned grass through the verge, and its pavement cap leaves the shoulder out on purpose (a
   −0.06 cap under a fill face pulls grass off the toe). Fix: a second cap, at shoulder −0.01, that binds only
   where the floor would end *above* the shoulder over it — on a fill the floor is already under the face, so
   nothing there changes.

## Verification

| drive_test (forward, then named `full`; reverse identical) | before fixes 7–8 | after |
|---|---|---|
| verdict | FAIL | **PASS** |
| soft-top in lane | 1 (8,047) | **0** |
| floating furniture | 6 | **0** |
| severe steps | 1 (1,273, 7 cm) — 0.1 /km, limit 12 | unchanged |
| excursion drops (gated, limit 1/km = 9) | 4 | 5 |
| far flare ledges (reported) | 7 | 30 |
| obstructions / undrivable / daylight / barrier gaps | 0 | 0 |

`audit_mesh` CLEAN. Blender 4.2.9 exported `build/sand_creek_raceway.kn5` (421 MB). `kn5_ground_check` PASS:
every group matches the audited OBJs (worst 0.00 m), 461 walls / 97 lamp posts / 6 sign posts 0 hovering,
road-over-ground p95 0.014 m (gate 0.1).

The first `verify_kn5` FAILED on L8 packaging only: the road kn5 carried 15 AC_* nodes and no
`build/sand_creek_raceway__<id>.kn5` existed — build.sh's OBJ path (`scripts/ac/build_kn5.py`) predated 0047's
multi-layout split, which lived only in the loop chain.

9. **L8 on build.sh (Kevin, 2026-10-28: "Teach build.sh L8").** `build_kn5.py` places no AC_* empty when
   `layouts[]` has more than one entry; build.sh then runs `tools/layout_dummies.py` and
   `scripts/ac/build_spawn_kn5.py --obj-frame`. Three frame facts made that more than wiring:
   (a) the road kn5 on this path is the mesh frame yawed by true north — for Sand Creek (mirror_x, 180°) that
   is (x_engine, y, −z_engine), the loop frame by coincidence — but `build_spawn_kn5`'s loop branch adds true
   north to every facing yaw, which would have faced the whole grid backwards; `--obj-frame` places the node
   with build_kn5's own transform and carries the travel through it. (b) `verify_kn5` read
   `finished_centerline.json` as the kn5 frame; on this path it is the mesh frame (180° round the origin here)
   — it now rotates a `frame: mesh…` file first (GATES-CHANGELOG 2026-10-28). (c) `layout_dummies` read
   `centerline.local.json`, up to 7.9 m under the as-built deck on the bridges; it now reads the finished line
   on this path. Config: each layout got `direction` / `kind` / `start` — the line, pole and forward sectors
   where build_mesh's own placement had them (E 45th Ave, st 6,796 / reverse 6,910, pole 30 m behind), the
   grid moved into the right lane (+3.0 m on the 12 m street), reverse TIME_2 on v116 (17.3 m Colorado Blvd)
   rather than the derived v142 on the 24.7 m flare into the 50th Ave junction. The layout id `full` became
   **`forward`**: `layout_dummies` refuses `full` / `freeroam` (they suppress the CM name suffix, 0047), so the
   Content Manager names are now "K10 Colorado - Sand Creek Raceway — forward" / "— reverse" — on the Windows
   install that is a new layout folder beside July's `full`.

   Result: `verify_kn5` PASS — heading min +1.00 on all 17 facing nodes of each layout, spawns on 1ROAD, side,
   line; `--inis` PASS; build complete, `build/sand_creek_raceway_v0.27.0.zip` (260 MB; repacked after the version bump). Only proven at a 180°
   true north (sin = 0); the s-terms meet their first test on a track with another angle.

The cost of fix 8, measured: measured-guard lips 355 → 799. Not a new defect — with grass no longer covering the
verge the cuts read as they are built (flat verge, cut face, bank crest) and the pass now sees, and guards, the
crest drops the 20% grass ramp hid (0.10 m per 0.5 m probe step, just under its 0.115 m trip). It is ~440 more
0.7 m stone blocks along cut crests (155 of them on E 45th N Dr, 8,000–8,500): how that reads from the seat is
open.

Same lap as August: 0025's two Sand Creek defects (soft-top 8,047, severe 1,274) reappear at the same stations,
so the OSM-snapped lap reproduces the July/August one.

## Scope

- Fixes 2–5 (gps / Overpass / labels): every `build.sh` track. Fix 3: any track that map-matches (KML snap,
  `scripts.gps.mapmatch` drives).
- Fix 6: every `tracks/` entry without `road_edge.profile: sidewalk` or `natural_ground` — aspen, grand-junction,
  high-plains, pikes-peak, pueblo, second-creek, lookout-lariat, the four rally stages, sand-creek.
- Fixes 7–8: every shoulder track with declared bridges or cuts. None of the other tracks has been rebuilt on
  this code; their numbers are unmeasured, not unchanged.
- engine-july: San Diego's build of record runs engine-july's own copies, so it is untouched. One file here is in
  its manifest — `scripts/ac/build_spawn_kn5.py`, which the snapshot README lists as byte-identical to airoso's;
  it no longer is (the opt-in `--obj-frame` branch). San Diego never passes the flag, so nothing is owed to the
  mirror, but that README line is now stale.

## Open

- Install on Windows and drive it: the tier stays T0 until a seat verdict (DEFINITION-OF-DONE). `version` is
  0.27.0 (July's install is 0.26.0), so CM shows "[build 0.27.0]".
- The creek bridges' parapets are visual-only `build_env._creek_bridge` concrete, not `1WALL`.
- 7 tests fail on this Mac on a clean HEAD export too (Windows-path guards, no `python` on PATH, engine-july
  snapshot md5, two Lake Murray byte-reproduction checks) — not this work.

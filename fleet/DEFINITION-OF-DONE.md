# Definition of Done — the tier ladder

*Ported into the fleet 2026-08-10 from the v2-reboot draft (prodrive-ac-builder PR #21), rewritten
against this repo's gates, ledger and REALISM doctrine.*

**"Done" is not a word this repo can use about a track.** `fleet/REALISM.md` §3 makes the game the
judge, and every track is therefore either *seen in game* or *unproven* — which collapses fifteen
tracks in wildly different states into one undifferentiated pile, and is exactly why "what's
finished?" has no answer today.

This file is the missing middle. Progress is claimed as a **tier**, and only with the tier's
artifact. Tiers are per track, cumulative, and cannot be skipped.

| Tier | Claim | Required artifact |
|---|---|---|
| **T0 — Builds** | The repo's build command completes end-to-end from a clean checkout at the pinned engine | Build log + the zip in `build/` |
| **T1 — Gates pass** | All four gates green on the **built artifact** (L5): `drive_test` → `audit_mesh` → `verify_kn5` → `kn5_ground_check` | The gate output, with thresholds recorded and any bypass env var named |
| **T2 — Installs & loads** | Installs via Content Manager and loads to the spawn without crash, on the Windows box | Drive-test report §Install + a screenshot of the car on track |
| **T3 — Drivable** | Kevin completes 3 consecutive clean laps: no fall-through, no invisible walls, no car-breaking geometry | Full `DRIVE-TEST-REPORT` with verdict DRIVABLE |
| **T4 — Playable** | The **AI laps it** — field launches the way the grid faces, completes a lap, timing and sectors fire; real minimap + CM preview | Harness lap output + the `ai/` contents that produced it |
| **T5 — Polished** | Reads as the real place: dossier look-checks pass, presentation floor met (REALISM §6), stable frame rate; Kevin calls it finished | Report §Look verdicts + final zip |

## The rules that make the ladder mean anything

- **T1 is a pre-check, never a proxy for T2+.** Substituting green gates for a drive is the
  founding failure — three consecutive Lake Murray builds were each worse to drive than the
  original while every gate was green (REALISM §1). A track at T1 has been proven *self-consistent*
  and nothing more.
- **A regression drops the tier** until re-proven, and the drop is recorded with its cause.
- **The tier is claimed with the artifact or it is not claimed.** "Gates green, therefore good" is
  the banned sentence; "the data says X, unverified in game" is the strongest one allowed
  (REALISM §8).
- **Distribution is a non-goal** — personal use, so kitbashed content is welcome at every tier and
  there is no "releasable" bar to clear. Clean-room still applies to anything shipped
  (REALISM §3): we imitate technique, we do not redistribute extracted third-party assets.

## Standing, 2026-08-10

Recorded conservatively — a tier not evidenced here is not held.

| Track | Tier | Evidence / what blocks the next one |
|---|---|---|
| IMI, Pueblo, Aspen, Second Creek | **T1** | Green at the v0.66.3 gate wave (ledger 0025); in-seat verdict open. Second Creek's geometry is fabricated, not sourced — flagged in `registry.json`, must not ship as a real place |
| **Nevada Nights (Exotics Racing LVMS)** | **T1 — gates pass, through the chain** | 2026-10-29, ledger 0060, airoso `bd3f1ba` (`tracks/exotics-racing-lv/`: `loop.blend` in LFS, `data/drive_test.full.json`, `audit.json`, `kn5_ground_check.full.json`, `split_manifest.json`, `ai/full/`). `tools/ship_track.sh exotics-racing-lv` on the Windows box at `f02ba1f`: draft → underlay (67 GEN + 5 refs) → prep → split (67 meshes, 15 AC nodes) → export (106 MB kn5) → `verify_kn5` PASS → **`drive_test` PASS** (severe steps 0, bumps 0.0/km, excursion drops 0 gated, obstructed 0) → **`audit_mesh` CLEAN** (every class 0) → **`kn5_ground_check` PASS** (double-sheet 0, hovering walls 0, road-over-ground 0/4162). The frame checked in the artifact: clockwise in-game as Lake Murray is, T2's outside edge raised. **Installed** 2026-10-29 at `2bd258d` as "doooom Nevada — Nevada Nights 0.1.0" (`content/tracks/exotics_racing_lvms`, kn5 md5 756e4791…), re-packed the same day at `59bd8f0` as **0.2.0** (`--from track_folder`: the new `ui_track.json` defaults, kn5 unchanged). Not T2: not yet driven. The `drive_test` "replication vs measured road" 1.79 m (the V1 build read the same) was the gate pairing a ring rotated by 48 points with the unrotated elevation file, not the road — fixed on the branch, to be re-read |
| **Milford Road Course** | **T1 — gates pass, through the chain; installed** | 2026-10-29, ledger 0060, airoso `b62de58` (`tracks/milford-road-course/`: `loop.blend` in LFS, the gate files, `ai/full/`). `tools/ship_track.sh milford-road-course --from prep` on the Windows box at `07c5e33` (the prep's terrain conform skipped on the engine draft): `verify_kn5` PASS, **`drive_test` PASS** (excursion drops 0 gated, ground on top 0, obstructed 0; severe steps 15 at s 795–808, the banked esses — the draft alone reads 8: the chain's gate walked the raw line there, half a metre beside the swept esses, fixed on the branch), **`audit_mesh` CLEAN**, **`kn5_ground_check` PASS** (flush edges +0.17 / +0.78). Installed as "doooom Michigan — Milford Road Course (unofficial) 0.1.0" (kn5 md5 bf3783ed…), re-packed the same day at `59bd8f0` as **0.2.0** (kn5 unchanged). The first chain run (`f02ba1f`) went red on 75 excursion drops from the prep's conform; the V1 build had 1. Not T2: not yet driven |
| **Sand Creek, High Plains** | **T0 owed — through the ship chain** | 2026-10-28/29, ledger 0060. Both went red on `drive_test` at `bd3f1ba` with Milford's signature (217 and 103 excursion drops from the prep's conform; `audit_mesh` CLEAN, `kn5_ground_check` PASS, `verify_kn5` PASS), High Plains also on its own gps smoothing and a start line in the pre-July displaced frame; fixed at `07c5e33`. **High Plains** full run at `59bd8f0` (0.68.0): `drive_test` PASS (severe 0, drops 0 gated), `audit_mesh` CLEAN, `verify_kn5` PASS, **`kn5_ground_check` FAIL** (road over ground p95 0.60 m): the ring rotation to `route.start_at` (815 of 1,074 points) left `centerline.elevation.json` in the old order and the bridge detector built a deck with no fill over real ground — fixed on the branch (projection records the permutation), full run owed. **Sand Creek** second run at `07c5e33`: the apron fixed (217 → 3 gated drops), `drive_test` red on the three creek spans (127 severe steps, 12 ground on top, 12 daylight gaps) — the prep had overwritten the engine's swept gate line with the raw one and the gate lost the levelled decks out of its 2.5 m window; fixed on the branch, a run from the draft owed. Their engine-era builds of the same day (Milford v0.1.0 T1, Exotics v0.1.0 T1, Sand Creek v0.27.0, High Plains v0.67.0: all `scripts/build.sh`, all "terrible" from the seat) are **retired, no tier held**. Kevin: "rebuild all four with the Lake Murray chain". Each has a `ship.json`; the first artifact is `loop.blend` from `scripts/blender/underlay.py` (the draft), then prep → export → the gates on the built kn5 → install, on the Windows box. T0 is claimed when `tools/ship_track.sh <track>` completes from the chain, not before |
| Lookout Lariat | **T0** (July v0.46.0 build only; current pin fails drive_test) | Its own campaign (0025: drive_test FAIL at v0.66.3, severe 1,033). *2026-10-11:* the V3 rebuild is approved (ledger 0048, `tracks/lookout-lariat/V3-PLAN.md`) and nothing of it is built yet |
| Lake Murray | **T2** | 2026-10-08, Kevin in the seat on `san_diego_lake_murray_v3` (C1 + median island + C2 v1 mouths): **"this is super clean (v3)"** — the first rebuilt build to beat the July restoration in his seat (0029's condition). T3 claims on a full-lap DRIVE-TEST-REPORT; open: sub-loop connector-to-connector mouths, corner returns, the College south-end hairpin (C3). *2026-10-12:* the race layouts (v0.17.1, ledger 0049) drew **"the track width and race track layouts are incredible"** (dictated) — a seat verdict, not yet the full T3 report |
| Dragon Tail / Under the Dragon (gravel) | **T0** | Packaged and shipped; gates not re-run at current engine |
| Grand Junction, Pikes Peak | **blocked** | Rough everywhere, mechanism not found (0018 / 0031) |
| Dragon Tail / Under the Dragon (tarmac) | **blocked** | No packaged build |
| Nordschleife, Bathurst | **calibration** | Not products — the answer key that fixed the DEM (0030) and is testing the roughness mechanism (0031) |

**No k10 track has ever held T2.** As of v0.14.0 / v0.22.0 / v0.3.0 every packaged track ships a
generated `fast_lane.ai`, which makes T4 *attemptable* for the first time — the AI line existing is
not the tier; the AI lapping is.

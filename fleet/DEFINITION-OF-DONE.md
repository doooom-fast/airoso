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
| **Nevada Nights (Exotics Racing LVMS)** | **T1 — gates pass, through the chain** | 2026-10-29, ledger 0060, airoso `bd3f1ba` (`tracks/exotics-racing-lv/`: `loop.blend` in LFS, `data/drive_test.full.json`, `audit.json`, `kn5_ground_check.full.json`, `split_manifest.json`, `ai/full/`). `tools/ship_track.sh exotics-racing-lv` on the Windows box at `f02ba1f`: draft → underlay (67 GEN + 5 refs) → prep → split (67 meshes, 15 AC nodes) → export (106 MB kn5) → `verify_kn5` PASS → **`drive_test` PASS** (severe steps 0, bumps 0.0/km, excursion drops 0 gated, obstructed 0) → **`audit_mesh` CLEAN** (every class 0) → **`kn5_ground_check` PASS** (double-sheet 0, hovering walls 0, road-over-ground 0/4162). The frame checked in the artifact: clockwise in-game as Lake Murray is, T2's outside edge raised. **Installed** 2026-10-29 at `2bd258d` as "doooom Nevada — Nevada Nights 0.1.0" (`content/tracks/exotics_racing_lvms`, kn5 md5 756e4791…). Not T2: not yet driven. Open, not chased: `drive_test` "replication vs measured road" median 1.79 m (the V1 build read the same) |
| **Milford Road Course, Sand Creek, High Plains** | **T0 owed — through the ship chain** | 2026-10-28, ledger 0060. Milford's first chain run (2026-10-29, `f02ba1f`) reached the gates and went **red on `drive_test`**: 75 off-road excursion drops > 20 cm at 10–12.5 m lateral (the V1 build had 1), `audit_mesh` CLEAN, `kn5_ground_check` PASS, `verify_kn5` PASS; not installed; diagnosis in ledger 0060 (the prep's terrain conform on an engine-conformed embankment). Their engine-era builds of the same day (Milford v0.1.0 T1, Exotics v0.1.0 T1, Sand Creek v0.27.0, High Plains v0.67.0: all `scripts/build.sh`, all "terrible" from the seat) are **retired, no tier held**. Kevin: "rebuild all four with the Lake Murray chain". Each has a `ship.json`; the first artifact is `loop.blend` from `scripts/blender/underlay.py` (the draft), then prep → export → the gates on the built kn5 → install, on the Windows box. T0 is claimed when `tools/ship_track.sh <track>` completes from the chain, not before |
| Lookout Lariat | **T0** (July v0.46.0 build only; current pin fails drive_test) | Its own campaign (0025: drive_test FAIL at v0.66.3, severe 1,033). *2026-10-11:* the V3 rebuild is approved (ledger 0048, `tracks/lookout-lariat/V3-PLAN.md`) and nothing of it is built yet |
| Lake Murray | **T2** | 2026-10-08, Kevin in the seat on `san_diego_lake_murray_v3` (C1 + median island + C2 v1 mouths): **"this is super clean (v3)"** — the first rebuilt build to beat the July restoration in his seat (0029's condition). T3 claims on a full-lap DRIVE-TEST-REPORT; open: sub-loop connector-to-connector mouths, corner returns, the College south-end hairpin (C3). *2026-10-12:* the race layouts (v0.17.1, ledger 0049) drew **"the track width and race track layouts are incredible"** (dictated) — a seat verdict, not yet the full T3 report |
| Dragon Tail / Under the Dragon (gravel) | **T0** | Packaged and shipped; gates not re-run at current engine |
| Grand Junction, Pikes Peak | **blocked** | Rough everywhere, mechanism not found (0018 / 0031) |
| Dragon Tail / Under the Dragon (tarmac) | **blocked** | No packaged build |
| Nordschleife, Bathurst | **calibration** | Not products — the answer key that fixed the DEM (0030) and is testing the roughness mechanism (0031) |

**No k10 track has ever held T2.** As of v0.14.0 / v0.22.0 / v0.3.0 every packaged track ships a
generated `fast_lane.ai`, which makes T4 *attemptable* for the first time — the AI line existing is
not the tier; the AI lapping is.

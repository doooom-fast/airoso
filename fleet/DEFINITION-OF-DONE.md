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
| IMI, Pueblo, Aspen, High Plains, Second Creek | **T1** | Green at the v0.66.3 gate wave (ledger 0025); in-seat verdict open. Second Creek's geometry is fabricated, not sourced — flagged in `registry.json`, must not ship as a real place |
| Sand Creek | **T0** | 1 soft-top from un-excavated cut-corridor grass, deferred (0025) |
| Lookout Lariat | **T0** | Its own campaign (0025) |
| Lake Murray | **T2** | 2026-10-08, Kevin in the seat on `san_diego_lake_murray_v3` (C1 + median island + C2 v1 mouths): **"this is super clean (v3)"** — the first rebuilt build to beat the July restoration in his seat (0029's condition). T3 claims on a full-lap DRIVE-TEST-REPORT; open: sub-loop connector-to-connector mouths, corner returns, the College south-end hairpin (C3) |
| Dragon Tail / Under the Dragon (gravel) | **T0** | Packaged and shipped; gates not re-run at current engine |
| Grand Junction, Pikes Peak | **blocked** | Rough everywhere, mechanism not found (0018 / 0031) |
| Dragon Tail / Under the Dragon (tarmac) | **blocked** | No packaged build |
| Nordschleife, Bathurst | **calibration** | Not products — the answer key that fixed the DEM (0030) and is testing the roughness mechanism (0031) |

**No k10 track has ever held T2.** As of v0.14.0 / v0.22.0 / v0.3.0 every packaged track ships a
generated `fast_lane.ai`, which makes T4 *attemptable* for the first time — the AI line existing is
not the tier; the AI lapping is.

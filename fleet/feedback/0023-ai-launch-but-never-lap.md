---
id: 0023
title: Generated AI launches off the grid but never completes a lap
status: open
scope: k10-san-diego/project (first observed); any track using write_ai_line output
layer: engine
train: R2
---

## Symptom (observed via CM-launched 7-AI race, 2026-08-07, ~31 min)

Race configured and started on the v0.61.0 Lake Murray rebuild (7 AI + player parked last).
In game, verified: player spawned exactly on the new `AC_START_7` (shared-memory position matched
the dummy to 0.1 m), the road ahead of the grid was empty from the first observation (~minute 7)
— the AI field launched and drove off. But over 31 minutes **no car posted a lap total** on the
leaderboard (leader lap should be ~6–7 min at racing pace).

Also observed: a wrong-way indicator over the (parked, correctly-facing) player at spawn — the
line's direction sense vs the track's is worth checking while in there (note: the generated line
follows the OSM centerline order, which is the REVERSE of Kevin's canonical driving direction —
see sd-restart canon).

## Hypotheses (unresolved, in order)

1. **Extras `speed` unit.** `write_ai_line` writes m/s (flagged as an empirical assumption in the
   v0.61.0 commit). If AC interprets the field as km/h, AI target ~3.6× slower speeds — a 13.5 km
   lap at ~30–45 km/h ≈ 20–27 min, marginally consistent with "no lap by minute 31" but not
   proven (no lap posted even at ~31 min).
2. **A blockage or spline discontinuity mid-loop** — candidates: the corridor tree canopy at
   stations 10,545–10,548 (0020), or the 7.09 m worst-case replication deviation drive_test
   measured. AI could be piled against an obstacle.
3. hasGrid=0 / missing derived data degrading AI throttle control (accepted by AC — cars DID
   drive — but possibly with broken speed lookup).

## Next probes (cheap, in order)

- Regenerate with speeds ×3.6 (write km/h) on IMI (961 pts, 65 s expected lap — a 4 min test
  settles the unit question fast, and IMI has no corridor obstructions).
- If unit is not it: spectate/track cam at the canopy station and the junction mouths; look for
  the pile-up.
- CSP "new AI behaviour" toggle on/off comparison.

## Relevance check (Kevin, same session)

> "2real traffic is far more interesting to me than track day or races"

For street ports the product mode is **CSP lane-graph traffic (traffic.json + 2REAL-style
apps), not racing AI** — so this entry matters mainly for circuits (IMI etc.) and for the
`ac_drive_test` harness (an AI that laps is still the automated test driver). Priority
accordingly: fix on IMI for the harness; Lake Murray's soul rides the traffic workstream.

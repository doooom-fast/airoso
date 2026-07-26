---
id: 0010
title: Lookout Lariat is caught between a floating road and floating guardrails
status: diagnosed
scope: k10-colorado/lookout-lariat (mountain real_road; any high-relief route)
layer: engine
train: 01
---

## Symptom

Lariat passes `drive_test`, audits CLEAN, and — since v0.24.3 — its kn5 verifies with no duplicate
meshes. It still cannot package, because the two terrain resolutions available to it each break a
different gate.

## Evidence

25 km mountain loop, 7 m road, default terrain 6.67 m cells:

| terrain cells | `drive_test` | `kn5_ground_check` |
|---|---|---|
| 6.67 m (default, x6) | **PASS** | **FAIL** — road over ground 99.1%, p95 **+1.560 m** |
| 5.0 m (x8, 1.44 M verts) | **FAIL** — 11 floating guardrail posts | not reached |

The floating furniture is one cluster, not a spread: `(-417.6, 2422.4, 1.15) (-418.1, 2422.0, 1.14)
(-417.6, 2421.5, 0.86)` — a single guardrail run hovering 0.86–1.15 m after the finer terrain
dropped away beneath it. `floating_furniture` has **no advisory mode** by design ("get the drive
test to fail on what I'm driving right now").

It cannot simply go finer: at x8 the grid is already 1.44 M verts over 25 km, and x14 (~2.9 m cells)
would be ~4.4 M — Dragon Tail peaked at 7 GB for 2.87 M.

## Diagnosis

Both symptoms are L3b in tension. Coarse cells cannot follow a mountain bench, so the deck sits
metres above the interpolated terrain (p95 1.56 m — the "raft perched above the ACTUAL terrain along
the whole Lariat" the code comments already describe). Fine cells follow the bench, which drops the
ground out from under props that were seated against the coarse surface.

**The prop seating is the weaker link.** The guardrail run should be re-seated against the FINAL
terrain, whatever its resolution — 11 posts at one location is a seating pass that ran too early or
skipped that cluster, not a fundamental limit. Fixing that unlocks the fine-cell path, which is the
one that also fixes the road float.

## Next step

Find where guardrail/fence props are seated relative to the terrain passes (the same ordering
question that `_gap_trace` answered for the deck), and re-seat after the contact pins. Then rebuild
at 5.0 m cells and confirm both gates.

## Verification

- At 5.0 m cells: `floating_furniture` 0 AND road-over-ground p95 ≤ 0.10 m.
- Lariat packages.

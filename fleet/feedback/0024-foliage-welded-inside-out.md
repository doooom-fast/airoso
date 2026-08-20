---
id: 0024
title: Foliage renders inside-out — remove_doubles welds double-sided shells into coin-flip winding
status: diagnosed
scope: k10-san-diego/project (measured); any Blender-first track with prop groups
layer: engine
train: R3
---

## Symptom (Kevin, 2026-08-07)

> "our 3d objects render weirdly in game, like points are closing with the wrong vectors"

## Evidence (kn5 winding-vs-normal coherence scan, same day)

Per-mesh scan of the shipped v0.61.0 kn5 (geometric winding normal vs stored vertex normals):
every road/kerb/grass/building/marking group is **0% incoherent** — but **PALMTRUNK 15–16%
inverted (+245–438 non-unit normals), SCRUB 8% (+2% orthogonal)**. The inversions are
salt-and-pepper: 7,490 inverted tris in 6,422 runs of length 1–2 — NOT per-instance (rules out
mirrored placements), randomly per-triangle.

## Diagnosis

`build_kn5_loop.py` ran `bmesh.ops.remove_doubles(dist=1e-4)` on **every** mesh. Foliage props
(mined Kunos vegetation) are double-sided by construction: duplicated face pairs at identical
positions with opposite winding. The weld collapses each pair into one face and keeps a
random side — scattered inverted triangles; AC's backface culling then eats them from one side
and lights the rest wrong. The L6 z<0 flip pass is NOT the culprit (it only touches the
near-horizontal groups, where it is sound and measured clean).

## Fix (landed with this entry)

The weld now skips the prop prefixes (`PALM/TREE/SCRUB/BUSHES/CHAINLINK`) — the same tuple the
planar-UV pass already exempts. Welding exists to clean generated seams, not authored props.

## Verification

- Re-run the coherence scan on the rebuilt kn5: PALMTRUNK/SCRUB at ~0% inverted, unit normals.
- Kevin looks at a palm and it reads as a palm from every side.

## Extension — barriers carry the same class (Kevin, 2026-08-08)

> "The barriers look weird too like they have the same wrongly closed vertices"

Measured on the installed Lariat: `1WALL_barrier_*` (the corner guardrails, ~116k tris across
five bands) run **20–22% inverted** — worse than the palms were; PARA stone and RETWALL are
clean, so it is the barrier sweep's emission plus the unconditional weld closing coincident
instance end-caps. Fix (v0.64.1): the consensus-flip repair now runs on wall-class groups in
BOTH pipelines (OBJ path post-weld; loop path via the weld-exempt branch), never on grass/road
(their winding is authored — the graveyard of normal passes documented in build_kn5.py stands).
Root-cause entry for the sweep's winding stays open if residual clustered inversion survives the
repair (consensus heals scatter, not whole-side mirrors).

**Parity result (v0.64.3, measured on a fresh Lariat kn5):** installed-era 20–22% → modern build
7.4% (consensus repair provably blind in the OBJ path: imported normals restate winding) →
**1.4–1.8% with parity propagation** (55,333 faces flipped across 245 components — the ~half-per-
component ratio says the barrier sweep emits ALTERNATING winding per strip; root-cause cleanup in
the sweep is the durable follow-up, the repair ships meanwhile). Residual ~1.6% is at the metric's
curvature-noise floor; whether anything remains visible is Kevin's eyeball call on the next
installed build.

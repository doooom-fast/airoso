---
id: 0028
title: Audit B counts the shoulder's buried apron as deck — every correct cut bank reads as a poke
status: diagnosed
scope: engine — every track with cut sections; proof k10-colorado/imi, regression any flat track (B unchanged)
layer: engine
train: R4 (rides with 0025/0027)
---

## Symptom (found instrumentally, closing 0025, 2026-08-08)

First IMI build to pass drive_test then failed audit check B with **59,162 "terrain poking through
road", worst +2.44 m** — a count that had been masked on every prior build because drive_test
failed first and aborted the chain.

## Evidence

All eight worst pokes probe identically: bank grass over `1ROAD_shoulder`, nothing else.

```
at (137.1, -198.1) poke +2.44:      # station ~302.5, the 0025 cut bench
    7.763  1GRASS_ai                # the natural bank — real, wanted geometry
    5.382  1ROAD_shoulder           # the apron's ground-meet/hem quads, buried by design
```

Mechanism, both halves in `scripts/geometry/audit_mesh.py`:

- B's road set was `_obj_tris(track.obj, ("1ROAD",))` — the prefix catches `1ROAD_shoulder`,
  whose outer profile verts (ground-meet, hem at −0.8) bury into cut banks **by construction**
  (`road_shoulder`'s four-condition selector). Grass standing metres above them is the terrain
  doing its job.
- `_surf_at` returns the **lowest** in-window surface, so wherever deck and buried apron both
  exist, the buried apron reads as "the road" — maximizing the false positive.

This is the exact bench-cut false-positive class B's own comment says the footprint-exact rewrite
was built to kill ("the old vertex-radius test false-positived on legitimate bench-cut faces
standing legally beside the deck") — reintroduced through one prefix.

## Fix (engine, same file)

`_obj_tris` gains an `exclude` substring filter; B's road set is now
`("1ROAD",) exclude ("SHOULDER",)` — the driven deck. Grass through `1ROAD_main` still fails;
grass draped over the transition apron does not. Rides the 0025 train, tags as v0.66.1.

## The same defect, one gate later

`verify_kn5` check 6 re-runs the poke test on the shipped binary with its own copy of the same
scope — `("1ROAD", "1KERB")`, lowest-surface pick — and failed the same bank the same way
(**52,658, worst +2.44 m**) the moment audit B stopped masking it. Same fix applied there
(`"SHOULDER" in name` excluded). Two checks, two copies of one wrong meaning — the durable rule
below applies twice.

## Verification

- **Proof (IMI):** B → 0 on the same artifact that showed 59,162, with A/C/D–K counts unchanged.
- **Regression (flat track, no cuts):** B identical before/after — the exclusion only removes
  tris that sit below terrain by construction.

## The durable rule

Same family as [[0027]]: the gates and the builder must agree on what a name MEANS. `1ROAD_*` is
one prefix carrying two meanings — "car can roll on it" (drive_test's built_edge, correct to
include the shoulder) and "the deck nothing may stab through" (audit B, correct to exclude the
apron). When a check borrows a prefix, it inherits the other meaning silently; scope by what the
check measures, not by what the exporter happened to name.

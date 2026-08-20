---
id: 0032
title: College Ave sawtooth — the split-carriageway narrowing is 35 disjoint stripes
status: diagnosed
scope: k10-san-diego/project (College Ave + Navajo Rd divided sections)
layer: project
train: -
---

## Symptom (Kevin, driving the installed track, 2026-08-19)

> "College Ave: sawtooth pattern on the road edges — edge geometry oscillates, undriveable."

Recurrence of [0013](0013-lake-murray-sidewalks-and-college-sawtooth.md) §2, and expected: the
artifact he drove is the **v0.21.0 kn5 × engine v0.24.3** (kn5 mtime Jul 26, reinstalled
2026-08-10 into `D:\SteamLibrary\...\content\tracks\san_diego_lake_murray\` with fresh AI) —
kept installed deliberately as the drive-feel reference per
[0029](0029-the-product-bill.md)'s decisions. 0013 measured the sawtooth on this generation;
nothing has replaced it in his seat. What is new here is the *mechanism* — 0013 stopped at
"whatever assigns per-vertex width … is switching instantaneously." This entry names it.

## Evidence (data re-derived 2026-08-09 at the same pin, `k10-sd-v021/project/data/`)

Reproduced 0013's numbers exactly: **105 adjacent width jumps > 1 m**, 29 of them > 8 m, worst
9.0 → 30.0 in one 3 m step at station 2307 (`centerline.local.json`).

The jumps are not only at junction boundaries. `connectors.local.json` `narrow_main` — the set of
mainline vertices narrowed to one carriageway (9.0 m) where College/Navajo are divided — is
**35 disjoint runs of ~7–8 vertices each**, spaced every 60–90 m along the divided sections
(runs at stations 2292–2307, 2334–2355, 2394–2415, 2484–2504, …). The road width *stripes*
9 ↔ 17/24/30 dozens of times down College Ave. Swept into a ribbon, that is the sawtooth; the
continuous `curb_sidewalk` sweep and the lane markings inherit the same widths array, so the
edges, curbs and paint all oscillate together.

## Diagnosis

Two lines produce the striping:

- `k10-san-diego/scripts/geometry/extra_lines.py:229-231` — a mainline vertex is narrowed if it
  is within **12 m of `lr_xz[::3]`** — every *third* raw OSM point of the divided run. OSM point
  spacing on College is large enough that 12 m circles around every third point do not overlap:
  membership flickers, and the "narrow the divided section" intent becomes 35 stripes with
  full-width (often junction-flared, per [0001](0001-junction-flare-drags-the-sidewalks.md))
  gaps between them.
- `k10-san-diego/scripts/blender/build_loop_blend.py:642-644` — the narrow is applied as a
  per-vertex `widths[i] = min(widths[i], 9.0)` with **no transition**, so every stripe boundary
  is an instantaneous 8–21 m step.

(Paths above are the restored worktree at `C:/Users/Owner/Documents/GitHub/k10-sd-v021`; both
files are SD-local allowlisted scripts, not engine code — hence `layer: project`.)

## Fix

The decision is already recorded in [0029](0029-the-product-bill.md): **split carriageways come
OUT of the street path — one ribbon per road.** Deleting `split_carriageways` from
`project/track.config.json` removes `narrow_main` entirely; College stays at its full/flared
width, which is also 0013's "on a divided road it should simply stay wide."

Under the white-glove method (REALISM.md, Jobs 1–3), the residue is then authored: the engine
emits the one-ribbon draft, the divided-median read of College is hand-edited in `loop.blend` if
Kevin wants it at all, and the gates verify. Do **not** patch the radius test or add a taper —
that is compensation for machinery 0029 already ordered deleted.

## Scope

`k10-san-diego/project` only — `split_carriageways`/`extra_lines.py` exist in no other track and
not in the engine (grep of `k10-track-agents/scripts/` finds no `split_carriageways`). Companion
defect on the same config: [0035](0035-the-phantom-opposing-carriageway.md). The engine-side
flare half of the jumps is [0001](0001-junction-flare-drags-the-sidewalks.md), unchanged and
still unlanded (`widths_base_m` still has no consumer — see 0036).

## Verification

- 0013's criterion, kept: **no adjacent width jump > 1 m** on the persisted centerline
  (`centerline.local.json`), measured before export. Today: 105.
- `narrow_main` absent from `connectors.local.json` after the config change.
- Kevin drives College Ave and the edges hold a line.

---

**2026-08-19 (C1 build):** split-carriageway machinery deleted (config + connectors.local.json); rebuilt via the v021 workshop; July verify gate PASS. Width steps >3 m on the mainline: 70 -> 0 (>1 m: 105 -> 62, remaining are OSM lane transitions). Installed side-by-side as san_diego_lake_murray_v3 (0.16.0) for the A/B. Status stays until Kevin's seat verdict.

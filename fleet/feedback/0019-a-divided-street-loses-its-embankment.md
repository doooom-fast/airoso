---
id: 0019
title: A divided street loses its embankment — every seating pass picks the wrong carriageway
status: fixed (the 4 m cliff); the connector float tail is still open
scope: k10-san-diego/project (Lake Murray loop)
layer: engine
train: 02
---

## How it surfaced

Lake Murray's port to the native OBJ→kn5 writer (`KN5_WRITER=native`) was blocked on an immovable
**4.051 m** connector float. Six hypotheses had already failed. Rather than propose a seventh, the
grid node under the float was instrumented and its height printed at **every write** between
`grade_embankment` and `grass_terrain` — the RINGDBG method that cracked ledger 0012. The instrument
is now `scripts/geometry/nodedbg.py`:

```bash
NODEDBG="-702,-865.5" NODEDBG_STOP=1 python3 -m scripts.geometry.build_mesh <project-dir>
```

It swaps the owning grid row for a `list` subclass whose `__setitem__` reports the write and the
source line, so no pass can move a node unobserved. Inert when the env var is unset.

## The trace

```
[NODEDBG 1] y 45.710                project_grid (bare 3DEP)
[NODEDBG 2] y 47.840  dy  +2.130    ribbon.py grade_embankment()
[NODEDBG 3] y 43.600  dy  -4.240    ribbon.py clamp_terrain_below_road()   <-- one line later
[NODEDBG 4] y 43.598  dy  -0.002    contact pin #2
[NODEDBG 6] y 43.784  dy  +0.187    corridor refine
```

`grade_embankment` builds the fill shelf correctly at 47.840. The **next pass** drops it 4.240 m,
and the argmin probe names the winner: a road vertex at y 43.610, 6.90 m away.

## What is actually there

Not a connector-over-mainline crossing — the loop is **414 m away**. `del_cerro_blvd` is a **divided
street**: two carriageways 13–20 m apart horizontally and 2.0–4.7 m apart vertically over ~412 m of
ribbon. It is the only such stretch on the track, and *every* pass that seats terrain against
pavement picked the wrong one of the two:

| pass | what it did |
|---|---|
| `clamp_terrain_below_road` | shaved the upper carriageway's embankment to the lower deck (`LAYER_DY = 20 m` cannot separate legs 4.1 m apart) |
| the same pass, calls #2/#3 | re-shaved a node the first call had correctly spared, because the layer test read the node's *already-lowered* height |
| connector verges | `1ROAD_del_cerro_blvd_verge` covered one node **twice**, at 47.837 and 44.760; the window scans take the minimum |

Nothing downstream could recover it: the node is **0.184 m outside** the upper carriageway's pavement
(5.184 m from centreline, half-width 5.00), so the contact pin — which needs a road triangle
overhead — skips it. The control node 0.4 m further in survives only because `corridor_refine_factor`
re-pins it last. The grass therefore carried a **4.1 m cliff exactly one cell wide, welded to the
pavement edge**: 47.901 inside, 43.784 eighteen centimetres outside.

## Fix

Four changes, all in the passes that decide terrain *shape*:

1. **The layer window is the fill face, not a constant.** L4 already says the gap is scale-dependent
   ("~20 m generally; ~4 m for a shoulder against its own deck"); a divided street is where the
   general figure has nothing to bite on. A road vertex may only pull a node down if the node is
   within `clear + (d - band) / ratio` of it — the profile `grade_embankment` itself builds. Near
   the pavement the window closes to `clear`, so anti-poke is untouched. No new constant: the clamp
   and the grading now share `GRADE_RATIO` and the effective `band`.
2. **Ownership is decided once.** The clamps take a `layer_ref` — the height the grading gave each
   node — instead of re-reading ownership off the running height.
3. **The grading is not overruled by more than one cell of fill.** Both roads pass the cone test at
   a grade separation; distance is the discriminator it cannot see, and the grading already applied
   it. This pass exists to catch the *built* ribbon sitting below the *sampled* surface — a
   cell-scale correction, not a 3 m one.
4. **Verges are trimmed against each other,** not only against the mainline. The junction trim has
   claimed to cover verges colliding "with the mainline or each other" since it was written — and
   cites this very number, `max 1.941 -> 4.051` — but only ever asked about the mainline.

## The negative result — pins do NOT get a layer opinion

Extending the same floor to the contact pins and `_fine_height` moved the gate's p95 from 0.198 to
0.186 and bought **3058 terrain pokes through the road** (audit B, worst +1.05 m). The clamps decide
terrain shape and need to know which road owns a node; the pins are the anti-poke *guarantee*, and
the pavement they measure is the built truth while the grading is only an estimate. Letting the
estimate overrule the truth is how grass ends up in the lane. Reverted, and recorded in the code so
it is not re-attempted.

## Result

Measured on the built `track.obj`, `1ROAD_del_cerro_blvd` within 30 m of the float:

| | median | p95 | max |
|---|---|---|---|
| before | 0.020 | **4.051** | 4.077 |
| after | 0.041 | **0.182** | 0.445 |

`college_avenue_opp`'s worst fell 6.908 → 1.936 from the same change. Gates: `audit_mesh` **CLEAN**,
`verify_kn5` **PASS**, `drive_test` unchanged on every safety metric (`soft_top_in_lane`,
`daylight_gaps`, `off_pavement_stations`, `undrivable_corners` all still 0; severe steps still 21)
with excursion drops 437 → 358 and far ledges 163 → 149.

Fleet regression on **Lookout Lariat** (24.8 km of stacked switchbacks, no connectors, so it
isolates the clamp change): `audit_mesh` CLEAN, severe steps 253 → 251, excursion drops 738 → 690,
far ledges 382 → 378, `B_terrain_poke` and `soft_top_in_lane` still 0.

## Still open — the port is NOT unblocked

`kn5_ground_check` still FAILs: **p95 0.198 m against a 0.100 m gate**, max 1.685. This is a
different defect from the one above. The tail is entirely connector terrain:

```
group                          n   >0.05   >0.10      p95      max
1ROAD_del_cerro_blvd         314      92      78    0.693    1.478
1ROAD_college_avenue_opp     152      78      71    1.123    1.936
1ROAD_navajo_road_opp         77      37      26    0.584    0.763
1ROAD_main                  1285      20      15    0.021    1.342
```

The mainline is *clean* at p95 0.021; three connectors own 175 of the ~198 samples over 0.10. That is
ledger 0014's corridor-resolution family, not layer ownership, and the negative result above says
more pass-level layer work will cost pokes rather than metres. The lever to try next is
connector-side resolution — the refine region already includes connector pavement (v0.52.0), so the
question is whether the connectors need their own finer `terrain_cell_m` the way L3b says a track
whose road is narrower than its terrain triangles does.

## Verification

- No grid node is shaved to a carriageway it was not graded to (`NODEDBG` at any node on the
  divided section shows the clamp rejecting the far leg).
- `audit_mesh` B and H stay at 0 on Lake Murray **and** on a stacked-switchback track.
- `kn5_ground_check` p95 under 0.10 — **not yet met**.

---

## Resuming this work

Branch `claude/k10-track-agents-connector-debug-ce619e`, one commit ahead of `main`. Everything
needed is committed; nothing lives outside the repo. **`k10-san-diego/project` was never written to**
— every build above ran against a throwaway copy, so that project still holds its pre-fix artifacts
and must be rebuilt to see any of these numbers.

Set up a scratch copy (the inputs are ~6 MB; the outputs are ~1.8 GB, which is why they are excluded
going in and why this does not run in place):

```bash
rsync -a --exclude='track.obj' --exclude='*_render.svg' --exclude='environment.obj' \
      --exclude='ground.local.json' <k10-san-diego>/project/ /tmp/lm/
```

Rebuild and gate (~25 min for the mesh on Lake Murray, most of it the ×6 corridor refine):

```bash
python3 -m scripts.geometry.build_mesh   /tmp/lm
python3 -m scripts.geometry.audit_mesh   /tmp/lm      # expect CLEAN
python3 -m scripts.geometry.drive_test   /tmp/lm      # expect the pre-existing lap-seam FAIL, 21 severe steps
python3 -m scripts.ac.kn5_write          /tmp/lm
python3 -m scripts.ac.verify_kn5         /tmp/lm      # expect PASS
python3 -m scripts.ac.kn5_ground_check   /tmp/lm      # expect FAIL at p95 0.198 (gate 0.100)
```

`drive_test`'s FAIL is **not** from this work: it is ledger 0017's still-open lap seam (worst severe
0.442 m at station 13478 on a 13478 m lap) plus the 0.29–0.35 m junction lip. Every one of its
metrics is bit-identical to the pre-fix baseline except the two excursion counts, which improved.

Aiming the next attempt — find *where*, then *why* (`scripts/diag/README.md`):

```bash
python3 -m scripts.diag.gate_tail_by_group /tmp/lm/data/track.obj
NODEDBG="<x>,<z>" NODEDBG_STOP=1 python3 -m scripts.geometry.build_mesh /tmp/lm
```

`NODEDBG_STOP=1` aborts right after the last pre-grass write, so a trace costs a corridor pass
(~4 min) instead of a full build. Two nodes worth re-reading: `-702,-865.5` (the original float, now
seated) and `-1643.13,-126.228` (college_avenue, still on the tail).

The regression target for any further change to these passes is **Lookout Lariat** — 24.8 km of
stacked switchbacks and no connectors, so it isolates the clamp behaviour from the verge behaviour.
Compare its `data/drive_test.json` against the one committed in `k10-colorado`; that comparison is
trustworthy because Lake Murray's shipped `drive_test.json` reproduced bit-for-bit from a clean
build, which shows the committed artifacts were built at current HEAD.

---
id: 0036
title: Sidewalk generation makes multi-street networks undrivable — gap the draft at every mouth, and make audit K gate
status: diagnosed
scope: kind:fictional_street_circuit, kind:street_port — every track with road_edge.profile=sidewalk and any junction/connector (Sand Creek, Lake Murray, SD freeway net)
layer: engine
train: -
---

## Symptom (Kevin, 2026-08-19 — the systemic statement behind 0033's two named places)

> "The sidewalk generation currently makes multi-street networks impossible to drive — sidewalks
> intrude into roadways at junctions."

This is Kevin restating, as a fleet property, what he has now hit on every multi-street artifact:
Sand Creek ("clean centerline but absolutely crazy lanes/sidewalks", 0001), Lake Murray v0.21
(0013 §1, and again today — 0033), and the restored original (0020: K = 1,096 sidewalk/kerb verts
inside the carriageway, I = 1,203). One street works; the moment streets *meet*, the sidewalks own
the junction.

## Evidence — the mechanisms are proven; neither fix has landed

Both halves were diagnosed months ago and are still in the current engine head:

1. **The sweep never stops at a mouth.** No junction gap exists anywhere in the sweep path:
   the engine sweeps one `curb_sidewalk` per side along the whole centerline
   (`scripts/geometry/build_mesh.py:1171`, `scripts/geometry/ribbon.py:238`), and the SD
   Blender path does the same for the loop and for every connector
   (`build_loop_blend.py:658/:677` — 0013's citation, unchanged). Every connector's sidewalk
   therefore crosses the street it joins.
2. **The edges follow the junction flare.** `widths_base_m` — the pre-flare "street's own line
   (sidewalks follow THIS)" — is still written (`scripts/gps/widths_from_osm.py:363,427`) and
   **still has zero consumers**; `build_mesh.py:1122-1124` still re-derives `_sw_widths =
   max(median, flared)` and sweeps the edge profile from it. 0001's fix, assigned to train 01,
   never landed.
3. **The gate that sees it does not gate.** `audit_mesh` measures exactly this defect — check
   **K, kerb/sidewalk in carriageway** — but K is **absent from the `hard` exit total**
   (`scripts/geometry/audit_mesh.py:671-675`: A,B,D,E,F,G,H,I gate; K only prints). A street
   track ships green with a thousand sidewalk verts standing in its junctions, which is how
   0013's artifact and 0020's artifact both passed whatever ran.

The **compensation pattern** is fully formed and must come out with the fix: the ±4-vertex
`_sw_line` median, the `_sw_roll` curb-flattening and the apron probes (0001's inventory at
`build_mesh.py:1122-1171`) all exist to soften a sidewalk that should never have entered the
mouth at all.

## Diagnosis

Sweeping pavement through intersections is the procedural pipeline doing authorship badly —
REALISM §8 already retired it as doctrine ("the engine provides junction *data* … and audits the
result; the junction itself — sidewalk gaps, median noses, flare shapes — is authored in Blender
once, per place"). The doctrine is written; no code enforces it. The engine draft still emits
un-gapped sidewalks, and the one audit check that would refuse them is advisory.

## Fix (routed for the white-glove method — draft + hand-edit + gate, not a smarter sweep)

1. **Gap the draft.** The engine already computes junction data (`detect_junctions()`,
   `widths_from_osm.py:187` area; connector meet points are known at mesh time). Break the
   `curb_sidewalk` sweep across every junction mouth ± a margin, in both the engine path
   (`build_mesh.py`) and the loop-underlay path. A gapped draft is deliberately dumb: no mouth
   shapes, no median noses — those are authored per place (0033 is the Lake Murray work list;
   Sand Creek gets its own).
2. **Sweep the edges off `widths_base_m`** and delete the compensation passes — 0001's fix,
   unchanged; this entry does not re-diagnose it, it re-routes it: the surviving sweep serves the
   *draft*, so simple-and-wrong-nowhere beats clever-and-wrong-at-mouths.
3. **Make K gate.** Add `K_kerb_in_carriageway` to the `hard` total in `audit_mesh.py` for
   street kinds (K = 0 to ship, like I). This is the deterministic check that verifies both the
   draft gap and every hand-edit afterwards — the gate is the half of the white-glove loop that
   survives regeneration.

## Scope

| Track | role |
|---|---|
| `k10-colorado/sand-creek` | **primary proof case** — multi-street, engine path, no hand edits to lose; 0001's own proof case |
| `k10-san-diego/project` | proof via the authored path (0033); never re-seed `loop.blend` |
| `k10-san-diego/project_freeway_net` | junction-dense; K count before/after |
| `k10-colorado/lookout-lariat` | regression — no sidewalk profile; zero diff expected |
| `k10-colorado-rally/*` | regression — `osm_road_widths: false`, no sidewalks; zero diff expected |

## Verification

- Audit **K = 0 and I = 0 on Sand Creek** from the gapped draft alone, before any hand edit —
  today's baseline on the same class of artifact is K ≈ 900–1,096 (0020).
- `grep -rn widths_base scripts/` returns a consumer (0001's own criterion, still unmet).
- Regression rows above build with bit-identical edge geometry.
- Kevin drives a multi-street network — Sand Creek or Lake Murray — and the junctions are the
  part he doesn't mention.

## 2026-10-08 — fix landed as V3 tools; K-gate promotion still owed

Both routed mechanisms are now handled OUTSIDE the quarantined assembler, as scripted authoring
on the draft (the white-glove shape): `tools/trim_connectors.py` (the side street ends at the
mainline's edge — ribbon-through) and `tools/gap_mouths_blend.py` (the mainline sweep stops at
every mouth). Audit K on Lake Murray: 1,096 (July reference) → 4,213 (island counted, pre-fix)
→ 387. The island itself is exempt by construction (`scripts/geometry/median_zone.py`).

**K hard** waits on C2 v1.5 (connector-to-connector mouths inside the Del Cerro sub-loop):
promoting it today would fail the build on 387 inherited verts the fix does not yet reach.
Tracked in fleet/GATES-CHANGELOG.md ("Still owed").

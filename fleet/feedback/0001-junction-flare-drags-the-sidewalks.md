---
id: 0001
title: Junction/corner width flare drags the curbs and sidewalks with it
status: diagnosed
scope: kind:fictional_street_circuit, kind:street_port — every track with osm_road_widths + road_edge.profile=sidewalk
layer: engine
train: 01
---

## Symptom

> "I often end up with a clean centerline but absolutely crazy lanes/sidewalks."

Earlier passes of the same thing, in Kevin's words, already recorded in the code comments:
*"very zigzaggy"*, *"sidewalks jut into the road"*, *"sidewalks should never isolate driving
surfaces"*. The centerline is right; the edges are not.

## Evidence

The road width is deliberately **flared** outward at real intersections and hard corners:

- `scripts/gps/widths_from_osm.py:325-333` — `detect_junctions()` + `detect_turn_corners()` feed
  `flare_widths()`, widening the road itself at every junction the route drives through. The
  comment records why: an overlapping **pad** was tried first, poked above the sloped road and read
  as bumps, so the pad approach was abandoned (`:395-399` deletes any stale
  `intersections.local.json`) in favour of widening the ribbon.
- `:334-378` — plus a fold tier: heading changes over 110° across a ±15 m window get a 10 m flare,
  tapering at 0.14 m per metre, so a single hairpin perturbs the width for **~70 m of road**.

The intent was already to keep the edges off that:

- `:327` — `widths_base_cl = widths_cl[:]  # pre-flare: the street's own line (sidewalks follow THIS)`
- `:391` — written out as `widths_base_m`.

**But `widths_base_m` is never read.** It appears nowhere outside the file that writes it
(`grep -rn widths_base scripts/` returns only `widths_from_osm.py`). The sidewalk sweep instead
takes the **flared** widths and re-derives a substitute:

- `scripts/geometry/build_mesh.py:522` — `widths = local["widths_m"]` (the flared array)
- `:853-855` — `_sw_line` = rolling median over a **±4-vertex** window, then
  `_sw_widths = max(_sw_line, widths)`
- `:902` — that is what `ribbon.curb_sidewalk()` sweeps.

At 2–5 m centerline spacing, ±4 vertices is a ±8–20 m window. The flare taper is **70 m wide**. A
median that narrow cannot remove it — so the walk still swings out at every junction, and `max()`
guarantees it follows the flare outward at the mouths by construction. Everything downstream
(`_sw_roll` curb-flattening at `:884-901`, the apron probes at `:895-899`) is compensation applied
*after* the geometry has already been dragged.

## Diagnosis

Two separate things are being asked of one number. `widths_m` is doing double duty as *the drivable
pavement* (which genuinely should open out at a junction mouth) and as *the street's own edge line*
(which should not). The pre-flare array that separates them exists and is discarded.

The flare itself is not the bug — a junction mouth really is wider. Dragging the **curb, sidewalk,
verge and embankment** through it is.

## Fix

1. **Sweep the edges off `widths_base_m`.** `build_mesh` reads it when present and passes it to
   `ribbon.curb_sidewalk()`, replacing the `_sw_line` median and the `max()`. The road ribbon keeps
   using flared `widths_m`; only the edge profile changes source. Delete the compensation passes
   that exist to undo the drag, and keep `_sw_roll` **only** for genuine paved-beyond-the-walk cases
   (the driving-surface isolation rule stands — see `:857-860`).
2. **Barriers instead of flares at unmapped crossings.** Where a side street meets the route but is
   *not part of the track*, the correct answer is neither a flare nor a pad: it is a **closed
   crossing**. Emit `data/crossings.local.json` from `detect_junctions()` (station, mouth width,
   angle, whether the side road is on the route), and have `build_mesh` place a `1WALL_*` barrier
   line across the mouth for the off-route ones — which is what a real street circuit does, and what
   `street_circuit`'s `props.concrete_barriers` preset already implies.
3. Restrict flaring to junctions the route **actually turns through**, plus declared
   `route.wide_corners`. An off-route crossing gets a barrier, not width.

## Scope

| Track | Affected | Role |
|---|---|---|
| `k10-colorado/sand-creek` | yes — every symptom above was reported here | **primary proof case** |
| `k10-colorado/lookout-lariat` | yes (`osm_road_widths: true`, mountain profile) | second case: no sidewalks, so it isolates the *road* half of the change |
| `k10-san-diego/project` | Blender-first — `loop.blend` is truth, so a rebuild would discard hand edits | do **not** rebuild; apply to future re-seeds only |
| rally stages | no (`osm_road_widths: false`) | regression check only |

## Verification

- `widths_base_m` has a consumer (`grep` proves the dead-data condition is gone).
- Measured: lateral offset of the sidewalk back-edge from the centerline varies by **< 0.5 m** over
  any 70 m window that contains a junction, on Sand Creek.
- `drive_test` and `audit_mesh` clean on Sand Creek and Lariat (no new curb/wall cruft, no isolated
  drivable islands).
- Kevin drives Sand Creek and the edges read as a street.

---
id: 0034
title: The turn onto Alvarado is "a mess" — the lap-seam corner carries a 10.5 m width step
status: open
scope: k10-san-diego/project (lap seam at Alvarado/70th, station 0/13460; alternate candidate Alvarado/College, station 2280)
layer: project
train: -
---

## Symptom (Kevin, driving the installed track, 2026-08-19)

> "The turn onto Alvarado: 'a mess.'"

Artifact: the **v0.21.0 kn5 × engine v0.24.3** reference install (provenance in
[0032](0032-college-ave-sawtooth-is-narrow-stripes.md)).

## Which corner this is

The loop runs Alvarado → College → Navajo → Jackson → Lake Murray Blvd → (close), so driven
forward, the turn *onto* Alvarado is the **lap-seam corner at Alvarado & 70th (station 0/13460)**.
Driven the other way it would be Alvarado & College (station 2280). Both corners carry measured
defects — different ones — so the entry stays `open` until Kevin confirms which he meant (or the
harness screenshot shows it). Evidence for both below; the primary reading is the seam.

## Evidence (data re-derived 2026-08-09 at the same pin, `k10-sd-v021/project/data/`)

**Primary — the seam corner (Alvarado & 70th, station 0):**

- `centerline.local.json` is a closed loop (`points[0] == points[-1]`), and **`widths[-1] = 27.5`
  while `widths[0] = 17.0`** — a 10.5 m width discontinuity *at the same physical point*, i.e.
  a 5.25 m instantaneous edge step on each side, swept into the ribbon exactly where the driver
  turns onto Alvarado. The approach flares 19.2 → 27.5 over the last ~40 m (stations 13423–13435)
  and then collapses to 17.0 across the closure vertex.
- This is **LAWS L13 defect #4, verbatim** ("a junction at the seam flared one side and the width
  collapsed 26.98 → 17.00 m in one 2.4 m step"). The L13 fixes (`_closed` detection +
  `d = min(d, _lap - d)`, now at engine `scripts/gps/widths_from_osm.py:293-303`) landed *after*
  v0.24.3 — the pin this project is held at (`k10-sd-v021/.engine-version`), kept deliberately per
  [0029](0029-the-product-bill.md). So the seam flare is a **stale-pin defect that is already
  fixed in the engine** and simply never reached this artifact.
- Independent same-place evidence: [0017](0017-lake-murray-hole-in-the-upper-deck-at-a-grade-separation.md)'s
  still-open lap-seam severe step (0.442 m at station 13478), and the 0.29–0.35 m junction lip
  noted in [0019](0019-a-divided-street-loses-its-embankment.md). This corner is also the I-8
  interchange (bridge decks, guardrails, the trench cut) — the most machinery-dense spot on the
  loop.

**Alternate — Alvarado & College (station 2280):** the flare taper 13.5 → 24.0 collapses
**24.0 → 9.0 in one vertex** at vert 766 (0013's own quoted trace), and the sharpest interior
kinks on the whole loop (17–18° per vertex) sit at verts 769–770 right after it. If Kevin means
this corner, the mechanism is 0032 + 0001, already diagnosed there.

Not the cause: the seam heading itself is clean — measured across the wrap the corner kink is
14°, in family with every other street corner. (An earlier read of "108° at vertex 0" was an
artifact of walking into the closure duplicate; recorded here so it is not re-found.)

## Diagnosis (pending Kevin's confirmation of the corner)

Seam reading: L13-class wrap-blindness in the width flare at pin v0.24.3, compounding with 0017's
seam step and the interchange furniture. Not new engine work — the engine already carries the
width fix.

## Fix

- If the seam corner: re-derive the width array with the L13-fixed flare (pin bump or a one-shot
  re-derivation of `widths_m` only — **not** a re-seed of `loop.blend`, which carries hand
  edits), then author the mouth per REALISM §8. 0017's vertical step at the seam is its own open
  entry and closes separately.
- If Alvarado & College: the work is 0032 + 0033's authoring pattern applied to that mouth.

## Verification

- Invariant, gateable now: **`widths[0] == widths[-1]`** on any closed persisted centerline (the
  closure vertex carries one width). Today: 17.0 vs 27.5.
- No adjacent width jump > 1 m within 250 m of the seam.
- Kevin makes the turn onto Alvarado and calls it a corner, not a mess.

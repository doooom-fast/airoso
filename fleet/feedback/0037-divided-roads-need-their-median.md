---
id: 0037
title: C1's single slab loses realism — divided roads need their median back, as a raised island ON the pavement
status: in-progress
scope: tracks/san-diego-lake-murray (College Avenue, Navajo Road)
layer: track + tools
train: -
---

## Symptom (Kevin, driving the _v3 C1 build live, 2026-08-20)

> "it's gone [the phantom westbound ribbon] but it loses realism in the process because that road
> doesn't look like that there. what can we do?"

Asked what the real medians carry: **"flowers and barriers"**, then **"grass etc"**, **"shrubs"**.
Context: same session he confirmed "dimensions look good on college and navajo" — the C1 fix
(delete split carriageways, [0029](0029-the-product-bill.md)/[0032](0032-college-ave-sawtooth-is-narrow-stripes.md)/[0035](0035-the-phantom-opposing-carriageway.md))
is right, but it flattened a genuinely divided street into one undifferentiated slab.

## Diagnosis

Both prior representations were wrong:
- split ribbons (v0.21 era): two disconnected roads, phantom lanes, sawtooth (0032/0035);
- C1 single slab: correct physics, wrong look — the real College/Navajo are divided by raised
  landscaped medians.

The professional pattern is neither ([docs/JUNCTIONS.md](../../docs/JUNCTIONS.md), measured from
rt_macau): **one continuous pavement slab; the median stands ON it as a raised island** (curb
ring + landscaped top), exactly like their traffic islands on continuous junction pavement.
Physics stays single-coverage; the divided look is authored dressing.

## Fix (built 2026-08-20, this session)

1. `tools/median_envelope.py` — measures the real median from the OSM dual-carriageway geometry
   (the old machinery's clustering, reused for good, with the mainline chain explicitly excluded,
   point-to-SEGMENT distance, an 11–24 m trust window, flare gap-bridging), then re-centers the
   raw centerline over the true middle and spans both carriageways (tapered ~36 m — no steps).
   Config key: `route.median_islands`. Found: College 1,614 m + 526 m; Navajo 776 m + 513 m of
   real median; island gapped at the del_cerro_blvd mouth (left turns) and pulled back from
   every run end.
2. `tools/author_median_blend.py` — authors the island into loop.blend after the scene build:
   curb ring → CURB (collidable 1KERB), grass deck → TERRAIN (1GRASS green turf), barrier beam +
   posts on runs ≥ 120 m → GUARDRAIL (collidable 1WALL), shrub clumps → SCRUB. Joining into
   existing objects inherits all material/physics/rename paths unchanged.

Parked: proper flower texture/color pass (SCRUB's chaparral material reads as green planting;
flowers need a texture of their own).

## Verification

Kevin's seat, same protocol as C1: does College now read as the real divided street? Island in
the right place (it derives from the true carriageway midline, not our ribbon's center)? Left
turn at Del Cerro still open? Barriers/planting where he remembers them?

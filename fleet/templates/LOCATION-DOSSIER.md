# Location dossier — \<Place name\> (\<slug\>)

> Copy to the track's own directory as `dossier.md`. Fill every section — "unknown, will verify
> via X" is a valid answer; silence is not. **Kevin reviews and approves this before any geometry
> is built.**
>
> This document is the answer to 0029's "I'm concerned you aren't taking this from a builder
> pattern and instead keep optimizing for one track." The *engine* stays general; the dossier is
> where a place gets to be specific. Anything this file can express is configuration and research —
> not a new code path. If a location seems to need engine surgery, that is the thing to question.

## 1. Identity & intent
- Which of the four kinds is this (`fictional_street_circuit` / `street_port` / `circuit_port` /
  `rally_stage`), and which `archetype` does it map to? They must agree (STANDARDS S6).
- Why this place? The drive we're chasing, in 2–3 sentences.
- Layouts wanted. Variants are **AC configs over one shared kn5** — never a rebuilt mesh (L8). The
  single exception is a surface-physics fork (gravel vs tarmac), which must be two tracks.

## 2. Route geometry — facts, per segment
| Segment | Roads | Length | Lanes / width (measured, with source) | Kerb / sidewalk | Surface & condition | Notes |
|---|---|---|---|---|---|---|

Sources: OSM tags — **verify widths against aerial measurement, don't trust defaults** — county GIS,
dashcam and session captures, LiDAR. Record one-ways, medians, painted vs raised islands, rail
crossings, bridges and culverts. L1 stands: no invented roads.

## 3. Elevation & drainage
Real grades along the route (3DEP in the US; **SRTM 30 m elsewhere** — ledger 0030 measured five
DEMs against the Kunos Nordschleife scan and SRTM won at 3.80 m RMS). Crests, dips, blind spots,
bridge decks, creek crossings, drainage.

Street ports get **real elevation only** — no invented banking. `track-grading` is for purpose-built
circuits, where superelevation is real (L10).

## 4. Corner-by-corner character
Numbered corners with: reference imagery (Street View / Mapillary / capture frame), what *defines*
the corner (a building at the apex? a pole line? a fence?), kerb reality, and any hazard the drive
test must specifically confirm (crest, off-camber, narrowing).

## 5. Built environment & landmarks
Architecture stock (industrial metal? brick? stucco?), the specific landmarks that make the place
recognisable, signage inventory (blades, regulatory, overhead), street furniture (lights, hydrants,
poles, wires), fencing per stretch.

**Furniture stands on true ground; the road comes down to the data, never the furniture up** —
0029 §5, the College Ave defect, and its explicit "you'll likely fix that wrongly."

## 6. Vegetation & terrain palette
Species actually present, density per stretch, ground cover, backdrop and skyline. Rally stages get
**nothing urban** — that is their regression case (REALISM §6).

## 7. Atmosphere & light
Sun character for the latitude and orientation, typical sky, time-of-day presets worth shipping,
and the one photo that nails the mood. True north is derived and written back to config
(`lighting`).

## 8. Asset plan — owned first
| Need (from §5–§6) | Owned asset (Dropbox path) | Conversion notes (scale / Y-up / PoT / EXR→PNG) | Placement | Or GAP → purchase candidate |
|---|---|---|---|---|

Master list: [`fleet/reference/ASSET-LIBRARY.md`](../reference/ASSET-LIBRARY.md). Rules: owned
assets before purchases; purchases only from the GAP column and only after an owned asset has been
proven to look right in game; no mined mod content in anything that ships (REALISM §3).

## 9. Data sources & capture assets
Overpass extracts, DEM tiles, KML (**only** where the route deliberately leaves the real road
network), recordings, LiDAR, route maps — with paths and dates.

## 10. Location-specific QA
What the drive test must confirm *here*, beyond the standard report. Concrete and checkable:
"the Quebec St bridge joint doesn't launch the car", "the warehouse row reads as Commerce City, not
generic". These become the §Look rows in the drive-test report.

## 11. Build plan
Which pipeline stages in what order, the config deltas this place needs, the bespoke authorship it
wants in Blender (`AUTH_*`, never overwritten by the engine — REALISM §4), the gates and their
thresholds, and the first question to put to the drive test.

---
**Kevin's approval:** ☐ approved as-is · ☐ approved with the changes noted above — date: \_\_\_\_

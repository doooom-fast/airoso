# Stage sourcing — what's real, what isn't, and how to add the rest

Rally Colorado has six signature stages. This repo builds the ones whose roads can be sourced
honestly. This document records what was checked, so nobody re-does the search or — worse —
invents a route and ships it under a real stage's name.

## The survey (2026-07-24)

Queried Overpass for every `CR NNN` and `County Road NNN` way across the Rangely region, well past
the rally's footprint (39.6–40.7 N, 109.6–108.1 W — roughly Meeker to the Utah line and Dinosaur to
Douglas Pass). Rio Blanco County's OSM data uses **both** naming conventions, so both were tried for
every stage road.

| Stage (as the rally lists it) | Road | In OSM | Mapped |
|---|---|---|---|
| Dragon Tail — CR 116/133 NW | County Road 116 | **yes** — 3 ways, `highway=tertiary`, `surface=unpaved` | 25.2 km, contiguous |
| Under the Dragon — CR 109 | County Road 109 | **yes** — 10 ways, `highway=tertiary`, `surface=unpaved` | 25.6 km |
| Cathedral — CR 100 West | CR 100 | no | — |
| Valley of the Gods — CR 131 E | CR 131 | no | — |
| Quest for Darwin — CR 73 W | CR 73 | no | — |
| Earl's Revenge — CR 96 W | CR 96 | no | — |

The four absent roads are genuinely unmapped, not mis-queried: no ways under either naming
convention anywhere in the region. They're BLM and ranch roads on the mesas, the kind OSM covers
patchily out here — the same survey returned hundreds of unnamed `highway=track` ways nearby, which
is what those stages most likely are.

Two further caveats on the two stages we *do* build:

- **Dragon Tail is the CR 116 leg only.** The rally lists the stage as "CR 116/133 NW"; CR 133 is
  unmapped, so this build is the 25.2 km of CR 116 that exists.
- **Stage extents are the mapped road, not the surveyed stage.** Without the event's GPX we don't
  know exactly where the start and flying finish sit along each road, so each build runs the full
  mapped length. The geometry is real; the stage boundaries are our best reading.

## Adding one of the missing four

Two supported routes, in order of preference. Either way, record which one you used in the stage's
`source/route-notes.md` — a stage folder must be able to say where its geometry came from.

**1. KML from the event GPX.** Get the stage trace from
[rally-maps.com](https://www.rally-maps.com/Rally-Colorado-2026), export it as KML, drop it in the
stage's `source/`, and set `source.type: "kml"`. This is the accurate option: it is the real
surveyed route, including the parts OSM never mapped.

**2. Aerial tracing.** If only imagery exists, use the engine's `aerial-tracing` skill: trace the
graded road off a georeferenced satellite screenshot into the same `centerline.geojson` the OSM path
produces. Slower and less exact, but it stays elevation-correct because it georeferences to real
lon/lat.

**What is not acceptable:** drawing a plausible line on a map and naming it after a real stage. The
screenshot is a selection aid, not data.

## Re-running the survey

```bash
cd .engine && python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from scripts.gps import overpass
BBOX = (39.75, -109.25, 40.45, -108.40)
for stage, names in [("Cathedral", ["CR 100", "County Road 100"]),
                     ("Dragon Tail", ["CR 116", "County Road 116", "CR 133", "County Road 133"]),
                     ("Under the Dragon", ["CR 109", "County Road 109"]),
                     ("Valley of the Gods", ["CR 131", "County Road 131"]),
                     ("Quest for Darwin", ["CR 73", "County Road 73"]),
                     ("Earl's Revenge", ["CR 96", "County Road 96"])]:
    ways = overpass.fetch_ways(BBOX, names)
    print(stage, {n: len(w) for n, w in ways.items() if w} or "NOT IN OSM")
PY
```

If OSM gains one of these roads later, this is the check that will show it.

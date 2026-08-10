# Nordschleife — the calibration track

This project is **not a product**. It exists to calibrate the builder against a known answer key.

The Nürburgring Nordschleife is the one track where we have both halves of the experiment:

- **The input** any track gets: public OSM geometry + a public DEM.
- **The answer key** no other track has: Kunos' laser-scanned `ks_nordschleife`, which is a
  measurement of the real road rather than an opinion about it.

So we build it from the public data, register the result onto the scan, and measure the error.
Whatever the error turns out to be is a property of *the builder*, not of this track — which is the
whole point. Every fix it earns rides the engine to all fifteen real tracks.

## Source

OSM relation **38566** (`Nürburgring Nordschleife`), 52 member ways, chained in relation order.

The bbox way-query alone is not enough: roughly half the circuit — Pflanzgarten, Bergwerk, the
Karussell — carries no individually-tagged `raceway` way inside the bbox and only appears as
relation membership. Chaining what the bbox returns yields 9,880 m of a 20,746 m lap and looks
plausible while being half a racetrack. Fetch the relation, not the area.

`osm_relation_ways.json` is the cached geometry for all 52 ways (`way(r); out geom;` after
`relation(38566)`). `osm_raw.json` is the wider area query, kept only to show what the bbox
approach does and does not contain.

Overpass rate-limits and 504s on a 52-way id-list; the single recurse-down query succeeds.

## Elevation

Germany is outside USGS 3DEP, so this track is what forced a second elevation source. See
`fleet/feedback/0030-non-us-elevation-source.md` for the bake-off that picked SRTM 30 m and the
measured reason Copernicus 90 m lost.

## Reproduce

```bash
python3 -m scripts.elevation.heightfield projects/nordschleife
python3 -m scripts.geometry.projection  projects/nordschleife
python3 -m scripts.geometry.build_mesh  projects/nordschleife
```

`data/centerline.geojson` is regenerated from `source/osm_relation_ways.json`; it carries
`kind: "full"` and `closed: true`, which the projection stage requires.

## Where it stands

Measured against the scan, registered rigidly in XZ (mirror + 178.5° rotation + translation,
lap phase offset 10.3%):

| | build 1 (Copernicus 90 m) | build 2 (SRTM 30 m) |
|---|---|---|
| lap length | 20,842 m vs 20,799 m (+0.2%) | same |
| lateral P50 | 1.7 m | 1.8 m |
| lateral, share within 5 m | 99% | 99% |
| vertical RMS | 9.7 m | **3.8 m** |
| vertical P90 | 15.5 m | **6.0 m** |
| vertical max | 37.6 m | **13.7 m** |

**Plan shape is done.** The scan's AI line is a *racing* line that legitimately uses the road's
full width, so a P50 of 1.8 m against a road centerline is at the floor of what this comparison can
resolve — there is no signal left in it to chase.

**Elevation is where the remaining error lives**, and it is now dominated by DEM resolution: SRTM's
30 m post spacing cannot see a cutting, an embankment or a bridge deck, which is exactly what the
residual 8–14 m sections are. Closing that needs a better DTM (Rheinland-Pfalz publishes 1 m
LiDAR), not more filtering — every smoothing variant tested lands within 0.2 m of the default.

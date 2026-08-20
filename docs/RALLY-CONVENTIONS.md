# K10 Colorado Rally — track project

Assetto Corsa builds of the **Rally Colorado** stages near **Rangely, Colorado** — the ARA gravel
stage rally in Rio Blanco County, promoted to National championship status for 2026. Each stage is
built twice from one geometry: a realistic **gravel** version and a fantasy **tarmac** version.

Sibling of `k10-colorado` (the circuits) and `k10-san-diego` (the street loops). Same engine, same
laws, different terrain: high-desert mesa and canyon instead of Front Range foothills or suburbs.

---

## What is actually real here (read this before adding a stage)

The rally has six signature stages. **Only two of them exist in OpenStreetMap.** Verified against
Overpass across the whole Rangely region (bbox 39.6–40.7 N, 109.6–108.1 W) on 2026-07-24:

| Stage | Road | In OSM? | Mapped length |
|---|---|---|---|
| Dragon Tail | County Road 116 | **yes** — 3 ways, `tertiary`, `surface=unpaved` | 25.2 km |
| Under the Dragon | County Road 109 | **yes** — 10 ways, `tertiary`, `surface=unpaved` | 25.6 km |
| Cathedral | CR 100 West | no | — |
| Valley of the Gods | CR 131 East | no | — |
| Quest for Darwin | CR 73 West | no | — |
| Earl's Revenge | CR 96 West | no | — |

The four missing roads are not mis-named, mis-cased, or just outside a bbox — they are absent under
both the `CR NNN` and `County Road NNN` conventions Rio Blanco County uses in OSM, across a region
far wider than the rally. They are BLM/ranch two-tracks OSM has not mapped.

So: **we build the stages we can source honestly.** Adding one of the missing four means supplying
its route as KML (from a rally-maps.com GPX) or tracing it with the `aerial-tracing` skill — not
guessing a line and calling it Cathedral. A stage folder must say where its geometry came from.

> **The screenshot is a selection aid, not data.** Geometry comes from OpenStreetMap via Overpass,
> or hand-traced asphalt off a georeferenced aerial. A map image tells us *which* road to grab; it
> is never traced for coordinates.

---

## The gravel/tarmac fork

Both variants of a stage are the **same road, same elevation, same mesh** — they fork on exactly one
config key, `road_surface`:

| | gravel | tarmac |
|---|---|---|
| `FRICTION` | 0.70 | 0.99 |
| `DAMPING` | 0.03 | 0 |
| `DIRT_ADDITIVE` | 1 | 0 |
| roll sound | `gravel.wav` | silent (tyre roll carries it) |
| 1ROAD texture | `gravel_road_diffuse.png` | cracked asphalt |

The engine reads that one key and forks both the physics (`track_folder.ROAD_SURFACES`) and the look
(`pbr.load_overrides`), so a stage can never drive like dirt while looking paved. Everything else —
kerb, runoff, grass — is identical, so the car still behaves correctly when it leaves the road.

**Two installable tracks per stage, not two layouts.** AC applies `surfaces.ini` per track, so a
layout toggle would make the friction difference fragile. Each variant is its own project dir with
its own slug; they share the route by pointing at the same roads.

The tarmac variant is **deliberate fiction** — these roads are dirt in reality. Don't go looking for
a paved source. It gets the same scenery as gravel; only the road surface changes.

---

## Stages are point-to-point, not laps

A rally stage has two ends. `loop: false` in the config means the engine:

- puts the grid at the **start of the road** (a stage starts where the road starts — not at
  whichever window scores straightest, which is the closed-circuit rule),
- puts `AC_TIME_0` — what AC treats as start/finish — at the **finish**, so the single crossing the
  driver makes is the one that posts a stage time,
- numbers the splits up from 1 in driving order (cross 1, then 2, then 0),
- never wraps a gate past the end of the road.

Get this wrong and the symptom is in-game only: the run simply never times.

---

## Non-negotiable laws (inherited — do not relearn these the hard way)

> **Roads stay tight to their REAL elevation.** Sample USGS 3DEP along the actual road, then
> median-despike + smooth + grade-cap by real segment distance, so the real crests survive but
> nothing launches or floats. The ground conforms to the road, never the reverse.

> **Conform passes never cross layers.** Any pass that seats something "to the nearby surface" must
> reject reference points more than a layer-gap from its own height. On stacked switchbacks and
> canyon shelves, XZ-proximity alone grabs the wrong leg.

> **Gate the built artifact, never a reconstruction.** `mesh-audit` and `drive-test` run on the real
> `track.obj`; `kn5_ground_check` gates the shipped kn5 against it. An audit that validates props
> against the same data that placed them is structurally blind.

> **Every material needs a texture.** A texture-less kn5 material renders BLACK in-engine. Solid
> colour paint gets a solid-colour PNG, not a bare colour.

> **A TreeFX species with no `.bin` is dropped, never referenced.** A `tree:` line naming a model
> that isn't in the packaged `extension/trees/` is the "tree manifest missing" failure. The engine
> resolves every species at build time and drops the unresolvable ones; if none resolve it skips
> `[TREES]` entirely. Rangely is high desert — sparse juniper and sagebrush, not forest — so these
> stages lean on GrassFX and billboards rather than TreeFX models we don't have.

---

## Build

```bash
./bootstrap.sh                          # fetch the pinned engine into .engine/
./build.sh tracks/dragon-tail-gravel    # phases 1-5 -> tracks/<stage>/build/<slug>_v<ver>.zip
./build.sh tracks/dragon-tail-gravel mesh   # resume past the slow Overpass/USGS half
```

Stages: `gps → elev → project → mesh → env → drive → audit → kn5 → verify → fidelity → pack`.
The `drive` and `audit` gates exit nonzero and abort the build before anything is exported.

Phases 1–5 are code-driven on the Mac. **Phase 6 is Windows-only** — installing, driving, recording
AI lines, and visual QA need AC + Content Manager + CSP on a GUI. Don't pretend those are scriptable
here.

---

## Repo layout

```
k10-colorado-rally/
├── CLAUDE.md               # this file
├── bootstrap.sh            # fetch engine -> .engine/ (gitignored)
├── .engine-version         # the pinned engine ref
├── build.sh                # thin wrapper -> .engine/scripts/build.sh
├── assets/textures/        # rally-specific textures (the engine carries the shared set)
├── docs/
│   └── STAGE-SOURCING.md   # what's in OSM, what isn't, how to add a missing stage
└── tracks/
    └── <stage>-<variant>/
        ├── track.config.json   # source of truth
        ├── source/             # route notes, any KML
        └── data/               # centerline.geojson, heightfield, splines
```

# k10-track-agents

Build **Assetto Corsa** tracks from real-world data — and manage the fleet of them.

Feed the engine a location and a route; get back a complete, installable AC track folder — geometry
from OpenStreetMap or a georeferenced aerial trace, real elevation from USGS 3DEP, accurate sun and
lighting, gated at four points, reproducible from a single `track.config.json`.

> **First principle:** the screenshot is a *selection aid, not data*. Precise geometry comes from
> OpenStreetMap via Overpass, or a georeferenced aerial trace; hand-drawn KML only where the route
> deliberately leaves the real road network.

This repo is the former `prodrive-ac-builder`, absorbed whole, plus the control plane that was
missing: the thing that knows what tracks exist, whether they conform, and how one fix reaches all
of them.

## Two halves

- **`scripts/`** — the engine. Consumer repos pin a tag and run these modules from `.engine/`.
- **`fleet/`** — the control plane. Registry, laws, standards, feedback ledger, build trains.

## The fleet

Fifteen tracks across four repos and four kinds — a fictional street circuit on real roads
(Sand Creek), real street ports including whole networks (Lookout Lariat, Lake Murray, the San Diego
freeway graph), real circuit ports both extant and shut down (IMI, Pikes Peak, Second Creek), and
real rally stages (Rally Colorado, gravel and tarmac).

```bash
python3 -m fleet.cli status      # repos, engine pins, drift
python3 -m fleet.cli tracks      # every track, kind, archetype, version
python3 -m fleet.cli lint        # standards check
python3 -m fleet.cli feedback    # the ledger
python3 -m fleet.cli build --run --from mesh
```

## Building one track

```bash
./scripts/build.sh <project-dir>          # phases 1-5 -> installable .zip
./scripts/build.sh <project-dir> mesh     # resume offline from cached data
```

Phases 1–5 run headless on a Mac. Phase 6 — install, drive, record AI lines, visual QA — needs
Assetto Corsa with Content Manager and CSP on Windows, and is not scriptable.

## Documentation

| File | What |
|---|---|
| `CLAUDE.md` | How to work in this repo |
| `fleet/LAWS.md` | The non-negotiable laws, each with the failure that bought it |
| `fleet/STANDARDS.md` | What every project repo must satisfy |
| `fleet/MIGRATION.md` | The engine absorption cutover |
| `fleet/feedback/README.md` | How feedback becomes a fix on every track |
| `fleet/trains/README.md` | How a batch of fixes ships |

## License

See `LICENSE`.

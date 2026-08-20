# k10-track-agents

**The track engine and the control plane above it.** This repo builds Assetto Corsa tracks from real
world data, and it orchestrates the four project repos that own the tracks.

It *is* `prodrive-ac-builder` — that repo's full history was absorbed here, `scripts/` and all, with
package paths unchanged. See `fleet/MIGRATION.md` for the cutover state.

---

## The two halves

| | Path | What it is |
|---|---|---|
| **Engine** | `scripts/` | The pipeline: OSM/aerial/KML → centerline → real elevation → mesh → gates → kn5 → installable track folder. Consumer repos run these modules directly from a pinned checkout at `.engine/`. |
| **Control plane** | `fleet/` | Which repos and tracks exist, what standards they must meet, what feedback is outstanding, and how a fix reaches all fifteen tracks at once. |

**Never move or rename anything under `scripts/`.** Consumers execute
`(cd .engine && python3 -m scripts.<pkg>.<mod> <ABSOLUTE-project-dir>)`. Those import paths are the
seam that makes the whole fleet work; breaking them breaks every repo simultaneously.

## Read these before working

- **`fleet/LAWS.md`** — the non-negotiable laws, each with the failure that bought it. This is the
  single source; project repos point here rather than restating them. Read it before any geometry
  change or any diagnosis.
- **`fleet/REALISM.md`** — the doctrine since 2026-08-06: the engine prepares a data underlay,
  authorship happens in Blender (lean in, never eject), the game is the judge. Read it before
  deciding *what kind* of fix any track problem deserves.
- **`fleet/STANDARDS.md`** — what a project repo must look like. Enforced by `fleet.cli lint`.
- **`fleet/DEFINITION-OF-DONE.md`** — the T0–T5 tier ladder and where every track actually stands.
  "Done" is not a word this repo uses about a track; a tier is claimed with its artifact or not at
  all. Read it before reporting progress on anything.
- **`fleet/GATES-CHANGELOG.md`** — every gate threshold and bypass, with the invented ones marked.
  Amend it in the same commit as any gate change.
- **`fleet/MIGRATION.md`** — the engine absorption cutover, still in progress.
- **`fleet/feedback/README.md`** — how feedback becomes a fix on every track.

`fleet/templates/` holds the two forms that bracket a build: **`LOCATION-DOSSIER.md`** (the research
a place gets *before* geometry — the engine stays general, the dossier is where a track is allowed
to be specific) and **`DRIVE-TEST-REPORT.md`** (the Windows drive that closes the loop).
`fleet/reference/ASSET-LIBRARY.md` is the owned-asset master list behind ledger 0005.

## The fleet

Four repos, fifteen tracks, four kinds:

| Kind | Meaning | Tracks |
|---|---|---|
| `fictional_street_circuit` | a racing loop invented on real streets | Sand Creek Raceway |
| `street_port` | real public roads as they exist, route or network | Lookout Lariat, Lake Murray, SD freeway network |
| `circuit_port` | a real facility, extant or shut down | IMI, Aspen, Grand Junction, Pikes Peak, Pueblo, High Plains, Second Creek |
| `rally_stage` | a real point-to-point special stage | Dragon Tail, Under the Dragon (gravel + tarmac each) |

```bash
python3 -m fleet.cli status      # repos, engine pins, drift
python3 -m fleet.cli tracks      # every track, kind, archetype, version
python3 -m fleet.cli lint        # standards check (exit 1 on FAIL)
python3 -m fleet.cli feedback    # the ledger
python3 -m fleet.cli build --run --from mesh
```

Project repos live beside this one and are declared in `fleet/registry.json`: `k10-colorado`
(circuits + the Lariat), `k10-colorado-rally` (Rangely stages), `k10-san-diego` (Lake Murray +
freeway). Tracks are **discovered** by scanning, not listed by hand.

## Orchestrators

`.claude/agents/` — the reason this repo exists:

- **`standards-auditor`** — audits the fleet against STANDARDS; sorts k10-colorado's 72 shadowing
  modules into delete / port-up buckets.
- **`feedback-router`** — raw observation → evidence-grounded ledger entry, routed to engine,
  project, or standards.
- **`geometry-surgeon`** — implements a diagnosed engine geometry fix and proves it with a gate.
- **`fleet-builder`** — builds a selection across repos, reports the matrix *including its holes*.
- **`engine-pin`** — operates the version seam: rehearse, cut over, converge, bisect.

`.claude/skills/` — the pipeline skills (`gps-extraction`, `aerial-tracing`, `elevation`,
`road-grounding`, `track-grading`, `mesh-audit`, `drive-test`, `ac-track-modding`, `lighting`,
`route-tracing`, `scs-extraction`) plus **`track-feedback`** for filing into the ledger.

---

## Engine reference

### Build pipeline

| Phase | Task | Where | Skill |
|-------|------|-------|-------|
| 0 | Screenshot, location, route notes | — | — |
| 1 | Roads → Overpass/KML → resampled centerline | Mac | `gps-extraction` |
| 1-alt | No OSM data? Trace asphalt off a georeferenced aerial | Mac | `aerial-tracing` |
| 2 | Sample USGS 3DEP + margin grid, smooth | Mac | `elevation` |
| 3 | Project to local metres, set origin + true north | Mac | `geometry` / `lighting` |
| 4 | Road ribbon + grass + dummies | Mac | `geometry` / `ac` |
| 5 | Gates → Blender → kn5 → track folder | Mac | `ac` |
| 6 | Install, drive, record AI lines, QA | **Windows** | `ac` |

```bash
./scripts/build.sh <project-dir>          # phases 1-5
./scripts/build.sh <project-dir> mesh     # resume offline from cached data
```

Phases 1–5 are code-driven on the Mac. **Phase 6 is Windows-only** — AC + Content Manager + CSP on a
GUI. `ac-track-modding` documents what it cannot own; don't pretend those steps are scriptable here.

### Conventions

Metres, Y-up, origin per track, true north written back to config. Surface prefixes `1ROAD_*`
drivable, `1KERB_*`, `1WALL_*`, unprefixed = visual-only. Dummies `AC_START_*`, `AC_PIT_*`,
`AC_TIME_*_L/R`, `AC_HOTLAP_START_0`. kn5 export needs **Blender 4.2** with the vendored AC Tools
addon (`scripts/bootstrap_blender.sh` pins it). Full detail and the reasons: `fleet/LAWS.md` L6–L8.

### The gates

`drive_test` → `audit_mesh` → `verify_kn5` → `kn5_ground_check`. All four run on the **built**
artifact, all four abort the build. Never validate geometry against the data that placed it (L5).

### Layouts

A `layouts[]` entry is a route variant. All layouts **share one kn5 model** and differ only in AC
configuration — never rebuild the mesh per layout. The one exception is surface physics, which AC
applies per track: a gravel/tarmac fork must be two installable tracks (L8).

### External contract

`projects/gala-seed/` + `scripts/game/export_seed.py` are owed to the **`k10-1978`** game repo per
its `PIPELINE_BRIDGE.md`. Absorbing the engine moved that contract here — the game repo's bridge doc
points at the old location and needs updating (MIGRATION M1).

`projects/` otherwise holds stale duplicates of tracks now owned by project repos. **Do not build
from them** — see `fleet/registry.json` `engine_projects` for each one's disposition.

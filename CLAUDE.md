# airoso — THE one repo (V3)

**Every track, the engine, the gates, the doctrine, and the ledger live HERE.** All other track
repos (prodrive-ac-builder, k10-track-agents, k10-colorado, k10-colorado-rally, k10-sd-v021) are
retired and tombstoned — never work in them, never build from them. This repo carries
k10-track-agents' full history (which itself absorbed prodrive-ac-builder), so nothing was lost.
`prodrive-agents` is the telemetry product — unrelated, leave it alone.

**Where it lives (2026-10-27):** GitHub `doooom-fast/airoso` (private) — the ONE remote; astra and every
machine clone this. `*.blend` is in Git LFS (`loop.blend` ~160 MB). History was rewritten 2026-10-27 to drop 17 old
`.blend` copies and move the current one to LFS, so commit IDs quoted in the ledger before that date don't match;
the pre-rewrite repo is kept byte-exact at `D:/k10-track-archive/2026-10-27_airoso_before_lfs.git` (look old IDs up
there). Release packages still publish from `k10-motorsports/k10-san-diego` (docs/PUBLISHING.md). The `engine`
remote (local k10-track-agents) is history only.

**The V3 model (docs/V3-PLAN.md):** the engine emits first drafts; Claude hand-authors geometry
(Blender / readable intermediates); deterministic gates judge every build; Kevin's drive test is
the only ground truth. Do not write kn5 generators, do not reverse-engineer binaries, do not
generate AI splines from GPS (docs/history/HANDOFF.md bans stand). Priority: San Diego — the Lake Murray network expansion, in phases (Kevin 2026-10-12: College → Waring → Princess View → Mission Gorge → Jackson; ledger 0054). Lookout Lariat is SHELVED until after a few Lake Murray phases (plan kept: `tracks/lookout-lariat/V3-PLAN.md`, ledger 0048). Then Sand Creek.

---

## The pieces

| | Path | What it is |
|---|---|---|
| **Engine** | `scripts/` | The draft pipeline: OSM/aerial/KML → centerline → real elevation → mesh → gates → kn5 → installable track folder. |
| **Doctrine + ledger** | `fleet/` | Laws, standards, DoD ladder, feedback ledger, reference measurements. (The multi-repo pin/train machinery in here is obsolete — one repo now.) |
| **Tracks** | `tracks/<slug>/` | Per-track source of truth. `san-diego-lake-murray/` includes `loop.blend` (the hand-edit surface — NEVER regenerate over authored layers) and the quarantined `scripts-v021/` build tooling of record. |
| **Tools** | `tools/` | blender-bridge (live agent↔Blender socket), kn5 inspectors. |

**Never move or rename anything under `scripts/`.** Everything executes as
`python -m scripts.<pkg>.<mod> <ABSOLUTE-project-dir>` from the repo root; those import paths are
load-bearing (and on Windows, run with `PYTHONUTF8=1`).

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
- **`docs/PUBLISHING.md`** — how a build reaches doooom.fast (GitHub Releases, read by
  prodrive-server), the CC0-vs-full package split, and why the full one stays on this machine.

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

## Agent model tiers (Kevin, 2026-10-26)

Every Workflow/Agent call inherits the session model unless `model` is set. **Decide the tier for each
agent before launching, never afterward; an omitted `model` is a bug, not a default.**

| Tier | Jobs |
|---|---|
| session model (Fable/Opus-class), `effort: high` | geometry authoring, Blender builds iterated against gates, branch integration/merge, judgment lenses (real-world truth, the look), diagnosis |
| `sonnet`, `effort: low`/`medium` | mechanical verification (re-run gates and diff the numbers, check the files AC loads, md5/manifest checks), log parsing, scouting, listing |
| `haiku` | trivial lookups and greps |

Put the tier in `meta.phases[].model` so the progress tree shows it, and say the tiering in the launch
message. Sequential mechanical follow-up (merge → engine-july mirror → tests → ship) runs inline, no agent.
The quality comes from the build → refute → repair loop, not from the top model on every seat.

`.claude/skills/` — the pipeline skills (`gps-extraction`, `aerial-tracing`, `elevation`,
`road-grounding`, `track-grading`, `mesh-audit`, `drive-test`, `ac-track-modding`, `lighting`,
`route-tracing`) plus **`track-feedback`** for filing into the ledger.

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

`contracts/gala-seed/` + `scripts/game/export_seed.py` are owed to the **`k10-1978`** game repo per
its `PIPELINE_BRIDGE.md`. Absorbing the engine moved that contract here — the game repo's bridge doc
points at the old location (`projects/gala-seed/`) and needs updating (MIGRATION M1).

`projects/` is retired (ONE-CHAIN §2 row 9, 2026-10-28): the seed moved to `contracts/`, the
`dashcam-loop-0406` test fixture to `tests/fixtures/` (the SCS sample went with the importer, row 7), and the
stale duplicates were deleted — the DEM answer-key configs of bathurst, nordschleife and the freeway loop are
kept under `docs/history/projects/`. Tracks live in `tracks/<place>/`; see `fleet/registry.json` `engine_projects`.

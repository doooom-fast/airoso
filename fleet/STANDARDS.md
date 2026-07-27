# Standards — what every project repo must satisfy

`fleet/LAWS.md` is *how a track is built correctly*. This is *how a repo is shaped* so a fix landed
once reaches every track. Each rule below is checked by `python3 -m fleet.cli lint`; a **FAIL** is a
standards violation, a **WARN** is drift that may exist briefly.

```bash
python3 -m fleet.cli lint
```

---

## The reference shape

**`k10-colorado-rally` is the model consumer.** It carries no `scripts/` of its own at all: a
`bootstrap.sh`, an `.engine-version`, a thin `build.sh` that `exec`s the engine's, and
`tracks/<slug>/{track.config.json,source/,data/}`. Everything else runs from `.engine/`. When in
doubt about how a repo should look, look at that one.

```
<project-repo>/
├── CLAUDE.md              # what is unique about THIS repo; points at fleet/LAWS.md for the laws
├── bootstrap.sh           # fetch the engine into .engine/ at .engine-version
├── .engine-version        # a tag in k10-track-agents
├── build.sh               # thin wrapper -> .engine/scripts/build.sh (or a documented reason not to)
├── scripts/               # ONLY code that is genuinely unique to this repo (declared in the registry)
└── tracks/<slug>/         # or project*/ — whatever the registry's tracks_glob says
    ├── track.config.json  # source of truth
    ├── source/            # KML, aerials, notes, capture
    └── data/              # derived, deterministic, safe to rebuild
```

---

## The rules

### S0 — The repo exists where the registry says it does
Paths in `fleet/registry.json` are relative to this repo. If a checkout moved, fix the registry;
the orchestrators resolve everything through it.

### S1 — Every repo pins the engine
`bootstrap.sh` + `.engine-version` present. An unpinned repo builds against whatever happened to be
checked out, which makes a build unreproducible and a regression un-bisectable.

### S2 — The pin resolves to a real engine tag
`.engine-version` must name a tag that exists in `k10-track-agents`.

### S3 — All repos sit on the same pin
Different pins mean **a fix landed once does not reach every track** — which is exactly the state
the fleet is in today (colorado `v0.16.0`, rally `v0.19.0`, san-diego `v0.16.0`). One repo lagging
behind the newest tag is a WARN; repos disagreeing with each other is a FAIL.

Converge with:
```bash
python3 -m fleet.cli pin v0.19.0 --dry-run
```

### S4 — No undeclared shadowing of engine modules
A repo-local `scripts/<pkg>/<mod>.py` at the same path as an engine module is a fork, and forks go
stale silently — that already happened twice, which is why the engine was centralised in the first
place. Genuinely repo-unique code is legitimate: declare it in the registry's
`local_scripts_allowlist` with a reason, and lint will stop objecting.

Current state: **k10-colorado shadows 72 engine modules** (a whole parallel copy of the pipeline),
**k10-san-diego shadows 21**, of which 8 are declared SD-unique. See `fleet/MIGRATION.md` M3.

### S5 — Track configs carry the required keys
`slug`, `name`, `version`, `loop`, `source`, `location`, `layouts`.

### S6 — Every track declares an `archetype`
The archetype is a **construction philosophy, not a tag** — it selects the presets in
`scripts/config.py ARCHETYPES`, which decide whether the track gets kerbs, runoff, racing furniture
or street furniture. A track with no archetype gets **none of those presets applied**, silently.

Implemented today:

| archetype | means | gets |
|---|---|---|
| `real_road` | a public road as it exists | civil-engineering edges (bench cuts, fills, ditches), real signage and street lighting, **no** racing furniture |
| `street_circuit` | a racing loop made from real streets | the `real_road` base + concrete barriers along the racing line + start/pit furniture |
| `race_circuit` | a purpose-built facility | racing kerbs, engineered runoff, pit lane and paddock, floodlights not streetlights |

**Ten tracks currently declare no archetype** — every Colorado circuit except Sand Creek and the
Lariat, plus all of San Diego.

**Proposed, not implemented: `rally_stage`.** The four Rally Colorado stages use `real_road`, which
gets the important things right (no kerbs, no runoff). A dedicated archetype would additionally
mean: no sidewalks or curbs at all, gravel-appropriate edge treatment, and spectator/hazard furniture
instead of street furniture. Adding it means adding it to `ARCHETYPES` — not just writing it in a
config, where it would silently match nothing.

### S7 — Slugs are unique across the fleet
The slug is the AC install directory name. Two tracks sharing one collide on install.

### S8 — Every repo's build path reaches all four gates
`drive_test`, `audit_mesh`, `verify_kn5`, `kn5_ground_check` (see L5). Delegating to the engine's
`build.sh` satisfies this, since that script runs the full set.

Current state: **k10-san-diego never runs `drive_test`** — it runs the other three. So the one gate
that simulates what the *car* feels (ground poking through the road, things in the corridor, steps
at speed) has never looked at the Lake Murray loop or the freeway network.

---

## Running things (learned the hard way)

Two failure modes cost several hours overnight, both of which *look* like the fleet breaking:

- **`python3 -m fleet.cli` only works from this repo's root.** Launched from a project directory it
  dies with `ModuleNotFoundError: No module named 'fleet'`, and the build matrix then prints FAIL for
  every track having never run one. Use **`./fleet.sh`**, which cd's itself.
- **A project's `build.sh` only exists in that project.** After any command that changes directory
  (or one that times out and leaves the shell elsewhere), `./build.sh` gives `exit 127`. Always
  invoke it with an explicit absolute path.

Neither error produces track output, so treat "every track failed instantly with no gate output" as
a launch mistake, not a regression.

- **A `cd` inside one command leaks into the next.** The session's working directory persists, so a
  command ending in `cd <track-dir>` leaves the following command running there — and
  `python3 scripts/...` or `git commit` then fails on a path that exists only from the repo root.
  This shape has cost five separate cycles. Use `git -C <repo>` and absolute script paths in every
  command that follows a `cd`, rather than assuming where the shell is.
- **An instrumented `.engine` blocks the next pin.** Debug prints patched into a consumer's
  `.engine/` checkout leave it dirty; the next `bootstrap.sh` then dies with *"Your local changes
  would be overwritten by checkout"* and every build after it silently never runs. Always
  `git -C .engine checkout .` when an instrumented experiment ends — in **every** repo you
  instrumented, not just the one you remember.

## Adding a track

1. Create `tracks/<slug>/track.config.json` in the owning repo, with S5's keys, an `archetype` (S6),
   and a `source` that records real provenance (L1).
2. Put the inputs in `source/`.
3. Annotate it in `fleet/registry.json` under `track_annotations` with its `kind` and `fidelity`.
   *Discovery is automatic* — the registry only records what the config cannot say about itself.
4. `python3 -m fleet.cli lint` until clean, then `python3 -m fleet.cli build --track <slug> --run`.

## Adding a repo

Declare it in `fleet/registry.json` `repos[]` with its path, remote, `tracks_glob`, and build
command. Then satisfy S1–S8. Copy `k10-colorado-rally`'s shape.

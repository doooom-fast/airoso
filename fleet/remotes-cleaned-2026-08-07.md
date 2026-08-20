# Remotes cleaned — 2026-08-07

Kevin: "we want all the remotes cleaned with only blender-based builds." Every remote now carries
the Blender-first lineage only. Every deleted tip is recorded here by SHA — GitHub keeps commits
fetchable by SHA (and via PR refs) long after branch deletion, so nothing here is unrecoverable.

## k10-san-diego

`main` **force-pushed** (with lease) from `8b17ea7` to the Blender-first line — removing the
native-kn5 port merge (PR #4) from the branch per the restart decision ("Blender stays in the
loop"; the generated-OBJ/native path is not to be used for SD).

Deleted branches:

| branch | tip | merged? | subject |
|---|---|---|---|
| claude/lake-murray-native-kn5-port | 39179da | no — the discarded direction | Record where the native-kn5 port stands |
| claude/port-freeway-updates-20a1bb | c58375b | no — release of the RETIRED single-ribbon freeway (registry: superseded by project_freeway_net) | release: v0.20.0 freeway drives clean |
| claude/central-engine | 4a7917d | merged | Consume the central engine |
| claude/engine-flip-v0.16.0 | a1fb4cd | merged | Proof-run derived data from v0.16.0 |

## k10-colorado

`main` pushed (pin v0.63.0 + L3b terrain declarations). Deleted branches — **all merged**, history
intact in main:

engine-pin-v0.16.0 (44e5c66) · fix-intersection-bumps (b3cfa1e) · flush-fix (4b169d5) ·
lariat-dense-forest (cc7fa6f) · lariat-treefx (7685982) · lariat-treefx-bundle (06717ea) ·
mountain-road-feel (db30773) · mountain-road-pine-trees-28a2f9 (f95e683) ·
native-kn5-writer (e9782e2) · ppir-combined (b5a4e67) · real-directions (f95e683)

## k10-track-agents

Deleted: claude/k10-track-agents-connector-debug-ce619e (752bc6d, merged via PR #1).

## k10-colorado-rally

Already clean — `main` only, in sync.

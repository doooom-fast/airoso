# airoso

**THE repo. The only one.** Every Assetto Corsa track, the engine, the gates, the doctrine, and
the feedback ledger live here. If you are working on tracks and you are not in
`C:\Users\Owner\Documents\GitHub\airoso`, you are in the wrong place — the old repos
(prodrive-ac-builder, k10-track-agents, k10-colorado, k10-colorado-rally, k10-sd-v021) are
retired, tombstoned, and read-only history. (`prodrive-agents` is the telemetry product's repo —
unrelated to tracks, still live, leave it alone.)

Named for Airoso Avenue, in the neighborhood the memorial track remembers.

## The V3 operating model (docs/V3-PLAN.md)

1. **The engine drafts.** `scripts/` (the absorbed k10-track-agents engine, full history) emits a
   regenerable data underlay — centerline, terrain, first-pass road — never a finished track.
2. **Hands author.** Claude edits geometry in Blender (`tools/blender-bridge/` for live sessions,
   headless otherwise) and in readable intermediates. Authored work lives in `AUTH_*` layers the
   engine never regenerates over (`fleet/REALISM.md`).
3. **Gates judge.** drive-test, mesh-audit, kn5 checks — deterministic, no bypass flags. Kevin
   never loads a build the machine already failed.
4. **Kevin drives.** The seat is the only ground truth. No drive-test report, no claim.

## Layout

| Path | What |
|---|---|
| `scripts/` | The engine. Package paths are load-bearing (`python -m scripts.<pkg>.<mod>`) — never move or rename. |
| `tracks/<slug>/` | One dir per track = source of truth (config, data, dossier, authored blends). Priority: `san-diego-lake-murray`, then `sand-creek`. |
| `tools/` | Blender bridge, kn5 inspectors, install/reload helpers. |
| `fleet/` | Doctrine + ledger: LAWS, REALISM, DEFINITION-OF-DONE, GATES-CHANGELOG, `feedback/` (0001–0036), reference measurements. |
| `docs/` | V3-PLAN, the V1/V2 postmortems, measured pro standards (PRO-KN5-CONSTRUCTION, ROAD-CONSTRUCTION, JUNCTIONS). |
| `tests/` | Hermetic suite — `python tests/run_tests.py` (177 tests, CI-wired). |

## History, honestly

V1 (prodrive-ac-builder, Jun–Jul 2026) built a real engine and never verified a track in-game.
V2 (airoso's minimal generator, Aug 2026) proved the one-shot approach dead a second time. The
fleet era (k10-track-agents + consumer repos) fixed a lot and diagnosed everything, but green
gates kept shipping undrivable junctions. V3 is the synthesis: draft → author → gate → drive.
Read `docs/V1-AUTOPSY.md` and `fleet/REALISM.md` before repeating any of it.

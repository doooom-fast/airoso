# San Diego — Lake Murray Loop (the memorial track)

Source of truth for `san_diego_lake_murray`. Imported 2026-08-19 from the `k10-sd-v021`
salvage (the vanished k10-san-diego repo's Windows snapshot; raw copy preserved at
`C:\Users\Owner\Documents\GitHub\_salvage\k10-sd-v021`). Plan: `docs/V3-PLAN.md`, Phase 4.

## What's here

- `track.config.json` + `data/` — config, centerlines (geojson/local/raw), connectors,
  OSM caches (network/lanes/sidewalks/buildings), cached 3DEP `heightfield.npy`.
- `loop.blend` (56 MB) — **the hand-edit surface.** The whole track as editable Blender
  meshes (ROAD / CURB / MARKINGS / YLINE / TERRAIN / HOUSE…). V3 rule #1: never re-run
  `build_loop_blend.py` over this file — it factory-resets the scene and destroys hand work.
  Regeneration is only allowed into GEN_* layers per fleet/REALISM.md.
- `source/` — route sources.
- `scripts-v021/` — **quarantined snapshot** of the k10-san-diego build tooling that produced
  the installed reference track (engine pin **v0.24.3**, kn5 built on Kevin's Mac Jul 26).
  Build tooling of record, NOT part of the live engine — it forks old engine modules
  (extra_lines, ribbon, build_loop_blend, build_kn5_win.sh). Consult it to understand the
  installed build; don't extend it.

## Not imported (in the salvage copy only)

- `data/track.obj` (40 MB) and `project/blender/san_diego_lake_murray.blend` (91 MB) — derived,
  regenerable from loop.blend via the prep/export path.
- `project_freeway/`, `project_freeway_net/` — the freeway-net half of the combined build;
  campaign C1–C3 targets the loop only.

## Open campaign (fix order — see V3-PLAN Phase 4 and fleet/feedback/)

C1 delete split carriageways (0029/0032/0035) → C2 junction mouths + make audit K gate
(0033/0036) → C3 the turn onto Alvarado (0034) → C4 full-loop drive report.

The installed kn5 (~66 MB, ui version 0.15.0) is the standing drive-feel reference (0029) —
preserve it before any reinstall over the same slug.

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
  installed build; don't extend it. **Since 2026-10-11 (ledger 0046) it is also what runs:**
  `tools/ship_sd.sh` executes `scripts-v021/blender/build_loop_blend.py` from here (V021_SHIM registers
  this folder as the `scripts` package inside Blender) instead of the retired workshop's copy, which it
  matched byte for byte when switched. Its one change is opt-in: with `terrain.tiers` in the config the
  TERRAIN comes from the tiered 3DEP lattice (`scripts/geometry/terrain_tiers.py`, loaded by path; the
  graded 20 m grid kept under and beside the roads) plus the visual-only far ring `GRASS_FAR`.

## Not imported (in the salvage copy only)

- `data/track.obj` (40 MB) and `project/blender/san_diego_lake_murray.blend` (91 MB) — derived,
  regenerable from loop.blend via the prep/export path.
- `project_freeway/`, `project_freeway_net/` — the freeway-net half of the combined build;
  campaign C1–C3 targets the loop only.

## Open campaign (fix order — see V3-PLAN Phase 4 and fleet/feedback/)

C1 delete split carriageways (0029/0032/0035) → C2 junction mouths + make audit K gate
(0033/0036) → C3 the turn onto Alvarado (0034) → C4 full-loop drive report.

**Status 2026-10-08.** C1 shipped and seat-confirmed ("dimensions look good"). 0037 median
island built (r2) — seat verdict pending. C2 v1 built (`tools/trim_connectors.py` +
`tools/gap_mouths_blend.py`): Del Cerro's 4-way at College trimmed and gapped; K/I now 387/417
vs the July reference's 1,096/1,203; connector-to-connector mouths (v1.5) and corner-return
arcs still open. C3's real site measured: the College south-end hairpin (verts 760–770), not
the seam. The gates themselves were fixed this day (frame + island awareness —
fleet/GATES-CHANGELOG.md); the July reference has NEVER passed them.

**Build it:** `bash tools/ship_sd.sh` from airoso (draft → author → ship → gate → install;
`--no-install`, `--force-install`, `--skip-blend`). Spawn site: `start_positions.json` → `active`.

The installed kn5 (~66 MB, ui version 0.15.0) is the standing drive-feel reference (0029) —
preserve it before any reinstall over the same slug.

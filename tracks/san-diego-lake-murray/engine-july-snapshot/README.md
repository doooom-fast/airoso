# engine-july snapshot — read-only provenance copy of the Lake Murray build-of-record engine

**What this is.** A byte-for-byte copy, taken 2026-10-11, of every file `tools/ship_sd.sh` executes
from `C:/Users/Owner/Documents/GitHub/engine-july` (ENG) — the prep, the kn5 exporter driver, the
spawn-kn5 builder, the modules they import, and the add-on code that writes the kn5 — with an md5
manifest. ENG is a **dangling git worktree** of the retired k10-track-agents repo: `git status`
refuses it and nothing in it is committed, yet it is what builds every San Diego kn5. This folder is
the only place git sees that code.

**What this is not.** It is not run. `tools/ship_sd.sh` still executes ENG (`ENG=` in the script);
nothing imports from here, and nothing here is edited by hand. To change the build, change ENG (and
mirror any file that also exists in airoso by `cp` + md5 equality), then refresh this snapshot.

## Contents

| path (relative here) | live source | why it is here |
|---|---|---|
| `scripts/ac/build_kn5_loop.py` | ENG | the prep — `"$BL" … --python "$ENG/scripts/ac/build_kn5_loop.py"` (diverged from airoso's copy: ENG `2dcc8e8b…`, airoso `8752e963…`) |
| `scripts/ac/export_kn5_addon.py` | ENG | the exporter driver, run once for the road kn5 and once for the race kn5 (byte-identical to airoso's) |
| `scripts/ac/build_spawn_kn5.py` | ENG | the nodes-only spawn kn5 per layout (byte-identical to airoso's) |
| `scripts/ac/pbr.py` | ENG | imported by the prep (`from scripts.ac import pbr`) and the exporter (`import pbr`); byte-identical to airoso's since the 2026-10-11 race-row fix (`1WALL_RACE` / `1KERB_RACE`) was mirrored |
| `scripts/geometry/dummies.py` | ENG | imported by the prep on its single-layout path only (diverged: ENG `b30e5800…`, airoso `e91f574a…`) |
| `scripts/__init__.py`, `scripts/ac/__init__.py`, `scripts/geometry/__init__.py` | ENG | the package chain those imports resolve through |
| `vendor/io_import_accsv/` (.py + README) | ENG | zipped and installed into Blender by the exporter and the spawn builder on every run |
| `appdata-addons/blender-assetto-corsa-tools/` | `%APPDATA%/Blender Foundation/Blender/4.2/scripts/addons/` | **the add-on that actually writes the kn5** — v1.0.7 (Hagnhofer, Greveson, Murdoch, JWL; GPL-3.0, `LICENSE.txt` kept). It registers `exporter.kn5`, which `export_kn5_addon._find_export_op` picks first; the vendored add-on's own `export_kn5.write` is not the one that runs. It lives outside ENG, so it is snapshotted here for the same reason |

`MANIFEST.md5` lists every copied file with its md5 — text files hashed with CRLF read as LF, so the
Windows checkout that writes the manifest and the LF blob git hands a Linux runner agree (binaries hash
raw). Two more lists record what was deliberately **not** copied, so the omission is visible rather than
silent:

- `EXCLUDED.md5` — `vendor/io_import_accsv/kn52fbx/{AcTools.dll, FbxConverter.exe, kn52fbx.exe}`
  (5.5 MB): the add-on's kn5→FBX **import** helpers, never loaded by an export.
- `REFERENCED.md5` — md5 + size of every `assets/textures/*` file a `pbr.TEXTURES` row or the Lake
  Murray `texture_overrides` names that exists in ENG (54 files, 91.3 MB): binaries the snapshotted
  code stages into every kn5 by name. Recorded, not copied — the snapshot itself is 0.39 MB.

## The drift check

`tests/tools/test_engine_july_snapshot.py` runs in `tests/run_tests.py`: every copy here must match
its manifest md5, every path `ship_sd.sh` names under `"$ENG/…"` must be in the manifest, and — when
ENG exists on the machine — every live file in `MANIFEST.md5` and `REFERENCED.md5` must still have the
recorded md5. A silent edit to ENG (or to the Blender add-on, or to a staged texture) fails the suite
until the snapshot is refreshed on purpose. Without ENG (another machine, CI) the live comparison is
skipped and only the snapshot's own integrity is checked.

## A change rehearsed before it is mirrored (`PENDING-MIRROR.md5`)

ENG is never edited in place by an agent: a change is made on a scratch COPY of engine-july
(`ENG=<copy> bash tools/ship_sd.sh ...` runs the chain on it) and recorded here first. Refreshing with
`ENG=<copy> python tools/snapshot_engine_july.py` snapshots the copy and writes `PENDING-MIRROR.md5`:
one line per changed file, `<md5 still live in the real engine-july>  <md5 of this snapshot>  <path>`.
The live drift test accepts exactly that old md5 for exactly that path until someone mirrors it:

```bash
cp tracks/san-diego-lake-murray/engine-july-snapshot/<path> C:/Users/Owner/Documents/GitHub/engine-july/<path>
md5sum C:/Users/Owner/Documents/GitHub/engine-july/<path>     # must equal the line's new md5
PYTHONUTF8=1 python tools/snapshot_engine_july.py              # refresh from the real ENG: the PENDING file goes
```

Ledger 0046 (2026-10-11, tiered terrain) is the first such change: `scripts/ac/build_kn5_loop.py` (terrain
tiles by balanced bisection, `GRASS_FAR` face-up, the T-junction weld) and `scripts/ac/pbr.py` (the textured
`GRASS_FAR` row; airoso's `scripts/ac/pbr.py` carries the same bytes).

## Refresh (after a deliberate ENG change)

```bash
cd C:/Users/Owner/Documents/GitHub/airoso
PYTHONUTF8=1 python tools/snapshot_engine_july.py --check   # what drifted (exit 1 on any)
PYTHONUTF8=1 python tools/snapshot_engine_july.py           # re-copy + rewrite the three manifests (keeps this README)
PYTHONUTF8=1 python tests/run_tests.py
```

Commit the refreshed snapshot in the same commit as the change it records, and say in the message
which ENG files changed (old → new md5).

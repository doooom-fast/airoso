---
id: 0007
title: The vendored kn5 exporter splits ~12 meshes into DUPLICATE-named pairs
status: open
scope: k10-colorado/lookout-lariat (measured); any track on the OBJ export path
layer: engine
train: 01
---

## Symptom

`verify_kn5` blocks Lookout Lariat — the one Colorado track that passes drive_test *and* has a
completely clean audit:

```
✗ kn5 verification FAILED:
   - DUPLICATE physical mesh '1WALL_barrier_a' x2 — AC drops dup-named meshes from collision
   - DUPLICATE physical mesh '1WALL_barrier_b' x2
```

AC drops dup-named physical meshes from collision, so the car would drive **through** those
barriers.

## Evidence

The duplication is broader than `verify_kn5` reports — it only inspects `1`-prefixed meshes. The
shipped kn5 actually contains **12 duplicated names**:

`1WALL_barrier_a`, `1WALL_barrier_b`, `LAMPHEAD_a`…`LAMPHEAD_i`, `LIGHTPOST_a`

| Where | State |
|---|---|
| `data/track.obj` | `1WALL_barrier_a` appears **once**, 29,998 verts |
| `data/environment.obj` | no wall/barrier groups at all |
| `blender/lookout_lariat.blend` | **175 mesh objects, 175 unique names, zero duplicates** |
| `build/lookout_lariat.kn5` | **186 meshes**, 12 names duplicated ×2 |

So the blend is clean and the kn5 is not: the split happens **inside the vendored exporter**
(`vendor/io_import_accsv`), which `export_kn5_addon.py` runs against that same blend
(`bpy.ops.wm.open_mainfile`). The pairs' vertex counts show a cap-split:
`1WALL_barrier_a` → `[65535, 35607]`, `1WALL_barrier_b` → `[65535, 35741]`,
`LAMPHEAD_a` → `[65534, 31014]`. 65535 = 0xFFFF, the 16-bit index limit.

## What was ruled out (don't re-test these)

Measured in the actual blend, for `1WALL_barrier_a`:

| Hypothesis | Measurement | Verdict |
|---|---|---|
| Two OBJs both carry the group | env OBJ has none | **no** |
| The blend accumulates across runs | `read_factory_settings(use_empty=True)` at build start; blend has no dup names | **no** |
| The build-side splitter re-splits `_a` into `_a`/`_b` | both are ~30k, far under any cap | **no** |
| Positions over cap | 29,406 | **no** |
| UV seams inflate render verts | unique (pos, uv) = 29,663 | **no** |
| Split normals inflate render verts | unique (pos, normal, uv) = 29,663 | **no** |

By every definition of "render vertex" the mesh is ~30k, yet the exporter emits 101,142 for it.

**The discriminator is not mesh size.** `1GRASS_a` has 174,591 loops / 29,998 unique — statistically
almost identical to `1WALL_barrier_a` (174,279 / 29,663) — and is **not** split. Something other
than geometry size decides. One untested difference: the split meshes carry per-mesh materials
(`1WALL_barrier_a_mat`), and all 12 are in the group the build logs as receiving *real-world
texture overrides* (`1GRASS`, `LAMPHEAD`, `LIGHTPOST`).

## Next step

Read the vendored exporter's mesh-writing path in `vendor/io_import_accsv` and find its actual
split rule. That is the one thing not yet inspected, and everything upstream of it is proven clean.

## Also rejected

A pre-split pass was added to `scripts/ac/build_kn5.py` (porting `build_kn5_loop._split_large`,
which solved this for the loop front-end) and **reverted** — it never fires on these meshes, since
the smooth-shading rescue runs first and the render estimate then reads the position count (~30k).
Shipping an untested code path that would someday trigger is worse than not having it. The loop
front-end's `_split_large` is still the right shape for the fix *once* the exporter's rule is known.

## Verification

- `verify_kn5` passes on Lookout Lariat.
- The kn5 has as many meshes as the blend has objects, all uniquely named.
- Every barrier collides in-game — the car cannot drive through one.

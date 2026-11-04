---
id: 0071
title: Barriers inside out and smeared; the engine's wall props wound once, outward, and kept out of the top-down UV pass
status: fixed-awaiting-rebuild
scope: tracks/sand-creek (1WALL_barrier, 1WALL_PARA_stone), tracks/high-plains + tracks/milford-road-course (1WALL_PARA_stone, 1WALL_CHAINL_warn, BARRIER_warning), tracks/exotics-racing-lv (1WALL_CHAINL_warn, BARRIER_warning)
layer: engine
train: -
---

Fix C1 of ledger 0070 (`fleet/feedback/0070-sand-creek-wiggly-roads-and-old-dressing.md`, section C, on branch
`claude/sand-creek-feedback-0070`). Filed as its own entry because 0070 is not on main yet.

## Symptom

Kevin, 2026-11-03, after driving Sand Creek 0.31.0: "it seems to use some ugly barriers that render wrong".

## Evidence

Every number below was measured again for this entry, on the PC-built blends (fetched from LFS, read in Blender
5.1.2, `inspect_blend.py`: per mesh island, faces whose normal points toward the island's centre line) and on the
module asset.

**The stamp writes each face twice on the same vertices, and the underlay halves it.**
`props.instance_barriers` (and the rim-arc path in `build_mesh.py`) appended every module face in both windings on
one vertex block. `underlay._add_group` calls `me.validate()`, which deletes one face of every pair sharing a vertex
set. Sand Creek's `loop.blend` (Blender 4.2.22, the PC's): `1WALL_barrier` 13,393 verts, 26,488 faces, 54 islands
of 493 triangles each, that is single-sided. **13,447 of its 26,488 faces (51 %) point into the barrier; 1,035 of
2,109 top faces point down; 33 of 54 modules are mostly inside out.** The prep's 1WALL consensus repair cannot fix
this (scratch run below: it flips 253 and leaves 1,553).

**Half the stamped modules are mirrored.** The stamp's basis (module +X to the run's outward normal
`(-tz*side, tx*side)`, +Z to the tangent) has determinant `-side`: on the +1 side it is a reflection, which turns
every face inside out. That is the "mirrored bases flip winding" the old comment named; double-siding hid it until
validate() picked a copy.

**The loader fans concave polygons.** `props.load_module` triangulated every polygon as a fan from its first vertex.
The module's end faces are concave 8- to 16-gons (the jersey profile, the connector slot); fanned, **41 of the 493
triangles face against their polygon's authored normal** and 0.32 m² per module is covered twice (summed area 14.391
vs 14.067 m²). Every other model in `assets/models/` is convex: 0 polygons change.

**The loader collapses UV seams.** 439 UVs on 249 positions; 159 positions carry more than one, 141 of 183 faces
touch a seam (0070 C3, confirmed).

**The prep re-projects the walls from above.** `build_kn5_loop.py` `planar_uv` (u = x / 4 m, v = y / 4 m) runs on
every mesh not in its skip tuple, which named `1WALL_RACE`, `1WALL_TILTUP`, `1WALL_TECPRO`, `1WALL_KRAILBW`, but none
of the engine draft's own walls. Census of the PC `underlay.report.json` files, names the prep flattened:

| Track | Flattened wall props |
|---|---|
| Sand Creek | `1WALL_barrier`, `1WALL_PARA_stone` |
| High Plains | `1WALL_PARA_stone`, `1WALL_CHAINL_warn`, `BARRIER_warning` |
| Milford | `1WALL_PARA_stone`, `1WALL_CHAINL_warn`, `BARRIER_warning` |
| Exotics (Nevada Nights) | `1WALL_CHAINL_warn`, `BARRIER_warning` |

All four carry authored UVs that a top-down projection turns into one texel column per vertical face. The freeway's
`CHAINLINK` was already skipped; the engine's fence is `1WALL_CHAINL_warn`, which `CHAINLINK` does not prefix.

**The fences: verified, same class.** `build_mesh` fence quads wrote 4 triangles on 4 shared vertices (front and
back). Exotics' PC `loop.blend`: `1WALL_CHAINL_warn` 172 verts, 86 faces, 43 islands of 2: **every panel single-sided.**

**Found while verifying: three more wall props wound inside out (no double-siding involved).**
- Stone lips (`1WALL_PARA_stone`, measured guards, ledger 0025): one winding for both sides, the +1 side inside out.
  Sand Creek's blend: **141 of 296 lips mostly inward, 282 of 592 top faces pointing down.**
- #17 stone parapets (the same object name): one winding for both sides, the -1 side inside out, and the two end
  caps wound alike (the start cap faced into the run on both sides). Derived and reproduced in the scratch scene;
  no PC blend inspected has one.
- The swept jersey (`BARRIER_warning`, `kerbs.warning_barriers`): wound inward on both sides. Exotics' blend:
  **all 430 of its top faces point down.**

`underlay.py:49-51` said the prep doubles the faces "at prep time, on the same names". It does not for scene objects:
`DOUBLE_SIDE` is used only in `_add_obj_meshes`, the import of extra OBJs (`data/track_*.obj`, `data/env_*.obj`).

## Diagnosis

The engine's wall props were wound by hand, once, for one side of the road, and a double-sided stamp on shared
vertices papered over the barrier's half of it until the underlay's validate() picked a copy at random. On top of
that the loader fanned concave faces and dropped UV seams, and the prep's top-down UV pass smeared what was left.

## Fix

- `scripts/environment/props.py`
  - `module_tris` / `place_module`: one copy of each face per placement; winding reversed exactly when the
    placement's basis is a reflection (det of (x_axis, up, z_axis) < 0). `instance_barriers` and the rim-arc path in
    `build_mesh.py` both stamp through it. Vertex positions are unchanged.
  - `load_module(keep_seams=True)`: one vertex per (v, vt) pair, the module's unwrap kept (249 -> 439 vertices per
    module). The barrier loads this way; the default keeps the old behaviour for `build_env`'s trees, lamps and panels.
  - `triangulate`: the old fan when it is valid (every convex polygon loads byte-identical), ear clipping when it is
    not. Only the barrier changes: 12 polygons, 41 -> 0 reversed triangles.
  - `append_sheet`: a two-sided sheet's back faces on a second copy of its vertices. The fence uses it.
- `scripts/geometry/build_mesh.py`
  - `stone_lip_box`: the measured-guard lip, wound outward on both sides; UVs u = metres along the lip, v = metres up
    (1.25 m tiles, the RETWALL/ROCKCUT skins' scale); the top gets its own 4 vertices so its UVs run across it
    (8 -> 12 vertices per lip, the first 8 at the same positions). Its top is still two consecutive triangles,
    which `tools/author_bespoke_blend.py` `guardrail` relies on.
  - `stone_parapet_run`: the #17 parapet, wound outward on both sides, end caps facing out.
- `scripts/geometry/kerbs.py` `warning_barriers`: the sweep's two triangles per quad reversed (outward).
- `scripts/ac/build_kn5_loop.py`: the planar_uv skip tuple gains `1WALL_BARRIER`, `1WALL_PARA`, `1WALL_CHAINL`,
  `BARRIER_WARNING`, each named in the comment with its track and its UVs. Lake Murray's prep (engine-july) is
  untouched; Lake Murray ships none of these props.
- `scripts/blender/underlay.py`: the wrong comment replaced; `underlay.report.json` now records `validate_dropped`
  per group, and the run prints any group validate() cut, so a duplicate-face draft can never be silent again.

Not changed: `props.instance_line` (ranch fences, pylons) still double-sides on shared vertices, but it runs only
in `build_env`, which no `ship.json` chain runs. The 1 m proximity trim that cuts modules open (0070 C4) is untouched.
No gate threshold or wiring changed (GATES-CHANGELOG untouched).

## Proof (this Mac, Blender 5.1.2, headless)

The underlay's own group path (`build_mesh.write_obj` -> `underlay.parse_obj` -> `group_to_mesh` -> `_add_group`
with `validate()`), on a scratch scene: a 40 m-radius bend with 3 stamped modules on each side, 4 rim-arc modules,
3 stone lips and a #17 parapet run on each side, 3 fence quads on each side, and a swept jersey on a 90-degree
corner. "Before" runs origin/main's code (eaf85b0), "after" this branch. Inward = against the authored normal
(barrier), away from the box/segment centre (lips, parapets), toward the row centre line (jersey).

| Object | | written | after validate | dropped | inward | top faces down | prep repair flips |
|---|---|---|---|---|---|---|---|
| 1WALL_barrier (10 modules) | before | 9,860 | 4,930 | 4,930 | 1,652 (43.8 of 143.9 m²) | 148 / 492 | 253, 1,553 left |
| | after | 4,930 | 4,930 | 0 | 35 (0.94 cm², slivers) | 7 / 493 | 0 |
| 1WALL_PARA_stone | before | 164 | 164 | 0 | 82 | 24 / 48 | 0 |
| | after | 164 | 164 | 0 | 0 | 0 / 48 | 0 |
| 1WALL_CHAINL_warn (6 quads) | before | 24 | 12 | 12 | two-sided quads 0 / 6 | | 0 |
| | after | 24 | 24 | 0 | two-sided quads 6 / 6 | | 0 |
| BARRIER_warning | before | 350 | 350 | 0 | 331 | 50 / 50 | |
| | after | 350 | 350 | 0 | 19 (criterion misfires at run ends) | 0 / 50 | |

Before, by placement: side +1 1,338 of 1,479 inward, side -1 135, rim arc 179 of 1,972. After: 10, 10, 15, all
slivers the OBJ's millimetre rounding flips. The 7 "down" top faces after are the end slot's ceiling (authored). The
summed area falls 3.2 m² (the fan's double cover, 0.32 m² per module).

Plot: `tracks/sand-creek/source/feedback-0070/barrier_faces_before_after.png`.

Tests: `tests/environment/test_barrier_stamp.py` (stamped modules: once, the rigid image of the authored normals on
both sides and on rotated and reflected bases, every face away from the centre line except the 24 authored notch
faces; seams kept; concave faces clipped inside the outline; fence two-sided on separate vertices; lips, parapets and
the jersey outward on both sides; lip UVs never constant along the run) and `tests/ac/test_planar_uv_skip_walls.py`.

## Verification owed (PC chain build, Kevin's word)

A rebuild of Sand Creek (and High Plains, Milford, Exotics for the lips, fences and jersey) through `tools/ship_track.sh`
should show:

1. `underlay.report.json`: `validate_dropped` 0 on every group (the old draft would have read 26,488 for
   `1WALL_barrier` and half the fence's faces); `1WALL_barrier` at 439 verts and 493 faces per module, about 23,700
   verts and 26,600 faces for ~54 modules, fewer where the proximity trim cut; `1WALL_PARA_stone` 12 verts and 8
   faces per lip.
2. The prep log: no `consensus-flipped` line for `1WALL_barrier` or `1WALL_PARA_stone`.
3. In the blend or kn5: every barrier and lip top face pointing up.
4. In game: whole concrete modules from both sides, the concrete texture's own pattern (no vertical streaks), the
   stone lips tiled, the chain-link pattern upright and visible from both sides.
5. High Plains / Milford: `author_bespoke_blend.py`'s guardrail now finds the +1-side lips' real tops. Before, those
   lips' tops pointed down and their FEET pointed up, so it read a foot as the top (inferred from the code and Sand
   Creek's measured lips; Milford's and High Plains' blends were not inspected): expect its `rail_m` to change.
6. The four gates as before (positions did not move; only lips gained 4 coincident top vertices each).

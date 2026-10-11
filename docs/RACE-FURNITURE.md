# Race furniture — the Lake Murray race layouts' barriers and kerbs, and the export split

Ledger 0047 (Kevin, 2026-10-10): three versions of the loop — the open street loop as today, and
the loop as a one-way race track in each direction, "with barriers making tracks out of the
north/south lanes … leading up to medians but not on them … barriers are for wide roads, Alvarado
should be the entire street … the tracks will get additional race curbs and barriers along the
inside of the sidewalks". This document covers the Blender side of that: **what
`tools/author_race_furniture_blend.py` builds, how it is seated and named, and how
`tools/split_exports_blend.py` turns one authored blend into the three kinds of export scene** that
L8-as-amended needs (one shared road kn5 + one race-furniture kn5 + one nodes-only spawn kn5 per
layout). The gates, the declaration file, the dummies and the AI lines are other agents' parts of the
same ledger entry and are referenced, not restated.

Status: **wired into `tools/ship_sd.sh`, dry-run only** (2026-10-11, scratchpad copies of
`loop.blend`). Nothing has been exported to a kn5, nothing has reached
`tracks/san-diego-lake-murray/loop.blend` or the installed track. Every number below is measured on
the dry run against the data agent's real `data/barrier_bands.json`; the second dry run
(`SHIP_PROJ=<scratch> bash tools/ship_sd.sh --skip-blend --dry-run`) reproduced them through the
ship script's own command lines, including the prep and the split on the PREPPED scene (§5, §10).

---

## 1. What gets built

| Kind | Mesh names | Where | Geometry |
|---|---|---|---|
| Centre K-rail chain | `1WALL_race_kbar_<street>_<run-start>_<part>` (8 objects) | the six declared `centre_runs` on the ≥ 17 m roads: v780-846, 1073-1096, 1258-1374, 1487-1540, 1739-2183, 2297-4440 | a swept jersey strip whose cross-section IS Kevin's `assets/models/concrete_barrier_4m.obj` silhouette (0.67 m base, 1.20 m tall), one ring per centreline vertex (3.0 m), continuous round the three interior corners, nose-to-nose with the five median islands, tapered free ends |
| Kerb-line barriers | `1WALL_race_edge_<L\|R>_<street>_<run-start>_<part>` (21 objects; `run-start` = the first ring's vertex, so an inside-lip piece that begins after a dropped fold starts a few vertices past the apex) | BOTH curb faces of EVERY street incl. Alvarado, gapped only inside the three declared bridge spans | the same strip, centre at `half_w − 0.485` (road-side face at `half_w − 0.82` = `race.edge_inset_m`, curb-side face 0.15 m clear of the curb batter); straight across the three sealed mouths (Q1) |
| Race kerbs | `1KERB_race_<apex-vertex>_<in\|out>` (7 objects) | the five corners the sign detector finds at \|D\| ≥ 45°: v770 (in + out), v1514, v2319, v3297 (out only — the chain is the inside), v0 (in + out) | 1.0 m wide × 0.05 m flat rumble strip ON the pavement, inboard of the edge strip (outer edge at `half_w − 0.87`), 0.10 m lane-side ramp, height tapering over the first/last 3 stations, 0.3 m stations |
| (optional, OFF) tall invisible collider | `1WALL_racecol_<k>` | `--collider` only | 2-vert/station sheet, deck −0.3 … +2.5 m — the Macau pattern, deferred (Q11); needs the `1WALL_RACECOL` pbr/ALPHATEST row and `assets/textures/invisible_4x4.png` (generated, CC0) first |

All of it lands in a Blender collection **`RACE`** and every name upper-starts with one of
`RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")` — that prefix is what the export split, `verify_kn5`
and `audit_mesh --race` key on. `L`/`R` are in the FORWARD frame (increasing vertex index =
clockwise); the strip on the chain's far carriageway is the other layout's outer wall, so both race
layouts share one race kn5 by construction.

**Why strips, not 2,100 instanced modules.** 123,148 positions in 36 objects (none over 8,000
positions) versus ~2.2 M positions for ~8,700 modules; every reference measured (SRP, nohesi,
Macau, rt_california) ships strips/sheets. The texture tiles at u = arc / 4.04 m so the joints
still read every module.

**Shading and ring density (2026-10-11 weld pass).** The first real rehearsal exported a 35.6 MB
race kn5 that leaked nothing — 36 RACE meshes, the three race textures — but carried 719,576
vertices for 241,190 triangles (2.98 per triangle): the strips were flat-shaded, so the exporter
(`exporter.kn5`, which welds face corners sharing position + normal + UV + tangent) wrote one vertex
per triangle corner. Every strip and kerb is now SMOOTH-shaded with hard edges only on real creases
— `race_furniture.sharp_edges`: faces meeting at more than 30° (the jersey base corner 90°,
base/slope 33°, top lip 86°, the end caps 90°; the slope/upper break is two steps of 17° and 12°
over a 9 cm chamfer and stays smooth) plus the kerb outline (`kerb_outline_edges`: ramp/top and
top/outer). UVs are per vertex (u along, v across the profile, no seam), so only hard edges split a
vertex: ~16 render verts per 20-triangle ring interval, `render_vertex_count` ≈ 0.81 per triangle
before the export. The prep keeps it (its bmesh round trip preserves the smooth/sharp flags, its
`DOUBLE_SIDE` pass only touches merged `data/track_*.obj` groups, its face-up pass flips 2 of 4,545
kerb faces at the hairpin fold, and it only ever ADDS smooth shading above 65,535 loops).
The same rehearsal measured outside-lip ring spacing up to 7.02 m (one ring per ~3 m centreline
vertex on a 10 m corner) with the strip chording the arc by up to 0.27 m. `densify_rings` now inserts
rings ON the declared offset curve (centre lerp + normalised lerp of the vertex tangents × lerp of the
declared lateral) until consecutive rings are ≤ 3.5 m apart and within 0.10 m of the curve; a
fold-drop chord (the inside lips the sweep drops) is only cut on its own straight line. 81 rings
inserted, spacing max 3.50 m, chord max 0.043 m. The new rings exposed two defects in `audit_mesh
--race`'s band test (`scripts/geometry/median_zone.py`): ±2 m rectangles round band points that
stand ~7 m apart on the outside lips left gaps (460 strip verts read as walls on the road), and a
closed lap's duplicate last vertex was a band point of its own at the last street's width (28 more at
the seam). The band is now continuous between consecutive declared vertices and the seam is vertex
0's — race D back to 512, the same as the pre-weld kn5 set re-audited with the fixed module.

## 2. Frames and winding

Everything is authored in the **engine frame** (x = E, y = up, z = N) by the pure module
`tools/race_furniture.py` (no bpy; testable) and emitted into Blender as (x, z, y) with **every face
reversed** — the remap is a reflection (LAWS L6, the `author_lamps_blend.py` pattern). The strip is a
closed solid with outward normals under the right-hand rule; the test
`tests/tools/test_race_furniture.py::test_strip_is_a_closed_solid_with_outward_normals_in_both_frames`
pins that every directed edge is matched exactly once (caps included) and the signed volume is
positive in both frames. It caught the end caps wound inside-out on 2026-10-11 — the ring order
(right base → up the right face → over the top → down the left) is clockwise seen from +t, so the
plain ladder faces −t and belongs on the START cap.

`right of travel` = `(tz, −tx)` of the layout's own travel tangent; `left_normal(tx, tz) = (−tz, tx)`.
The exporter mirrors z into the kn5; nothing here needs to know that.

## 3. The declaration is the authored line

`data/barrier_bands.json` (written by `tools/barrier_bands.py`, the data agent's self-gated file) is
read for everything that decides WHERE geometry goes, so the declared band and the authored strip are
the same thing (the 2026-10-08 median_zone precedent; L5 still holds because the gates measure the
built OBJ):

- `centre_w_by_vertex` / `runs[kind=centre]` → the chain runs (an end on an island-nose vertex gets
  the nose taper, else the free-end taper).
- `edge_inset_by_vertex` → where the kerb-line strips run (0 inside the bridge spans → a gap with
  tapered ends on both sides) and the lane inset.
- `streets` → the street token in every object name and the split points between streets
  (boundaries at the corner apexes: Alvarado 0-769, College 770-1513, Navajo 1514-2318, Jackson
  2319-3296, Lake Murray 3297-4498). Without the table the spec's measured table is used.
- `kerbs` → the kerb runs by (apex, side): the detector (`tools/place_signs.py`, imported read-only)
  still finds the corners and decides inside/outside, but the declared `i`/`j` replace its own
  [PC−E, PT+E] so the bridge-clearance clipping is honoured (the seam corner's outside kerb starts at
  v4492, after the I-8 span, not v4484). A declared run that matches no detected corner is a loud
  warning in the report (`kerbs_declared_unmatched`); `verify_race` is the gate.
- `closed_mouths` are gate-only here: the edge strip is continuous across a mouth line by construction
  (sealed, Q1); the escape-road alternative would be a gap in `edge_inset_by_vertex`.

If the file is absent the tool refuses, unless `--standin-bands` writes one from the spec's vertex
runs (flagged `_standin`, for dry runs only). `--edge-mode walk` (Q6) moves the edge strip onto the
sidewalk top (centre at `half_w + 0.445`, seated on CURB) and the kerbs to the lip; `--barrier-height`
(Q5) is one constant; `--no-kerbs` drops the kerbs.

## 4. Seating (measured on the 2026-10-09 loop.blend)

Every ring is seated by a Blender BVH ray cast onto **ROAD's mainline rows only** (the ribbon lays
the mainline's 3-vertex rows first, connectors after; the tool asserts row k's centre vertex IS
centreline v k for three k), taking the **lowest** sheet where the ribbon folds on itself (the inside
of the seam corner and the Navajo/Jackson apex), with a ±0.4 m probe when the centre falls in a
fold's uncovered wedge and linear interpolation from the run's seated neighbours for anything left.
Strip base = deck − 0.05 m (5 cm buried: drive_test's floating-furniture probe and audit E both read
"grounded"); kerb base = deck − 0.01 m. The honest counters land in `data/race_authored.json`:

| counter | dry run 2026-10-11 |
|---|---|
| rings seated by direct hit / within 0.4 m / interpolated | 13,144 / 3 / 0 (a run with no seated ring at all fails; > 1 % interpolated fails) |
| built deck vs data height, worst | −0.213 m at `1WALL_race_edge_R_alvarado_620_0` v768-769 (the hairpin's inside lip; the Navajo/Jackson apex rings that read −0.445 m are fold-dropped now) |
| another ROAD sheet > 0.15 m ABOVE a strip base | 19 rings, max 0.539 m: `1KERB_race_770_in` ×11 (the hairpin's inside lip, v768-775), edge_L College v1081-1083 ×3 (the Del Cerro mouth: the connector's deck stands up to 0.54 m above the mainline sheet at the trim line), edge_R Alvarado v768-769 ×3, edge_R Navajo ×2 (the inside apexes) |

The second row is **a junction/fold defect for its owner, not a seating choice**: at the two tight
apexes the ribbon's inside edge folds over itself and the lowest sheet is up to 0.5 m under the upper
one, so a kerb or strip seated there is partly hidden inside the fold (0033/0046 class). It is
reported, not papered over.

**Folded rings and stations are dropped.** Where the pavement lip's offset path runs backwards
against the centreline tangent (the lip's local radius goes negative: the hairpin's inside lip on the
30 m flare, and every inside apex where the raw polyline's kink is tighter than the ~8 m lip offset)
a strip or kerb swept there is a knot of overlapping faces — a sharp V the driver would hit.
`race_furniture.drop_folded_rings` / `drop_folded_stations` remove those rings/stations, so the wall
chords across the fold at the lip path's own crossing point. Dry run: 27 edge-strip rings dropped,
all on the forward-RIGHT (inside) lip (the five corners are right-handers): the hairpin 6, the seam 5,
and 16 along the College→Lake Murray run at College/Navajo, Navajo/Jackson and Jackson/Lake Murray —
folds are dropped per WHOLE run before the street cut, so a street boundary never splits one — and
51 of 211 kerb stations at `1KERB_race_770_in`, 37 of
106 at `1KERB_race_0_in`. The counts land in the object records as `fold_skipped_run` /
`fold_skipped`, and the real-data test pins that the only flagged vertices without a ring are those.

## 5. The export split — one blend, three kinds of kn5

`tools/split_exports_blend.py <blend> --project <dir> [--out-dir DIR] [--layouts a,b,c]` opens the
input fresh for each output and **removes** what does not belong (then `meshes.remove` +
`orphans_purge`), never saving over the input:

| output | holds | dry run |
|---|---|---|
| `loop_main.blend` | everything EXCEPT RACE members / `1WALL_RACE*` / `1KERB_RACE*` names and every `AC_*` object | 18 meshes / 716,927 positions / 8 materials / 0 AC nodes / 0 race objects |
| `loop_race.blend` | the race furniture ONLY | 36 meshes / 122,338 positions (max 8,000) / 0 AC nodes |
| `loop_spawn_<id>.blend` ×3 | `AC_*` empties from `data/dummies_<id>.json` (tools/layout_dummies.py) — Blender (x, z, y), `rotation_euler.z = _yaw_deg` for START/PIT/HOTLAP, TIME unrotated; nothing else | 23 empties each, 0 meshes, 0 materials |
| `split_manifest.json` | census per output + problems (exit 1 on any) | problems: [] |

Why removal and not selection, collections or `__` renames: the exporter that actually runs
(`exporter.kn5`, the AppData blender-assetto-corsa-tools 1.0.7) walks `blend_data.objects`
(selection ignored), embeds every material with `users > 0` (a mesh datablock keeps its material
"used" after the object is gone), and the prep's `_split_large` re-links tiles to the scene root so
collection membership cannot be trusted after the prep. The race filter is therefore RACE-membership
OR name prefix.

**Materials.** The authored meshes carry no material; the prep (`build_kn5_loop.py` step 4,
`pbr.setup_material`) creates `<object>_mat` per mesh by name prefix, so after the prep every race
material is RACE-prefixed too, and binds its OWN pbr row: `1WALL_race_…_mat` → `1WALL_RACE` (Kevin's
`concrete_barrier_diffuse/normal.png`, roughness 0.85, the 1WALL concrete parameters) and
`1KERB_race_…_mat` → `1KERB_RACE` (`kerb_diffuse.png`, red/white along v: the kerbs keep their own UVs,
v = arc / 1 m, so a 0.5 m red + 0.5 m white pair per metre). The rows were added 2026-10-11 ahead of the
generic `1WALL` / `1KERB` rows (prefix order = match priority), in `scripts/ac/pbr.py` and engine-july's
byte-identical copy: before them the strips fell through to the generic `1WALL` key, which Lake
Murray's `pbr.network_walls: true` reskins with the building tile — the prepped dry-run scene of
00:47 bound `building_diffuse/normal.jpg` on 29/29 strip materials; the re-run binds
`concrete_barrier_*` on 29/29 and `kerb_diffuse.png` on 7/7, and the exporter's own lookup
(`shader_and_textures`: key by prefix, override by key) resolves the same. No new texture. The two prep hunks landed 2026-10-11 in BOTH copies of
the prep (engine-july's pin and airoso's diverged copy): the planar-UV skip tuple carries
`"1WALL_RACE", "1KERB_RACE"`, and with `len(layouts) > 1` the prep creates no `AC_*` empties and
writes `data/dummies.json = {}`. Measured on the prepped scratch scene: `loop_race.blend` = 36
meshes / 122,330 positions / **36 RACE-named materials** / 0 AC nodes, `loop_main.blend` = 20 meshes
/ 727,123 positions / 20 materials / 0 AC / 0 race objects, `split_manifest.json` problems `[]`.

**Export.** `export_kn5_addon.py` (engine-july, mirrored byte-identical into airoso) takes
`--blend <file>` and `--out <name.kn5>` and runs once per split scene — `loop_main.blend` →
`<slug>.kn5`, `loop_race.blend --out <slug>_race.kn5` (content-checked by the ship script:
`inspect_kn5 --json` then `tools/check_race_kn5.py` — every mesh 1WALL_RACE* / 1KERB_RACE*, every
texture from `pbr.py`'s race rows, no `AC_*` node; the size is printed, WARN above 20 MB); each
pass purges and rewrites the one persistence `.ini` (named after its kn5) from the materials the
opened scene holds, so the race kn5 embeds only its own material table.

**Spawn blends vs `scripts/ac/build_spawn_kn5.py`.** The chain of record builds the spawn kn5s with
`build_spawn_kn5.py` straight from `dummies_<id>.json` (same placement, plus the true-north yaw
composition, 0.0 on SD). The split's `loop_spawn_<id>.blend` files are the inspectable equivalent —
open one in Blender to see the grid — and a fallback input, not a second source of truth.

## 6. Budget

Measured on the 2026-10-11 weld-pass rehearsal (`SHIP_PROJ=<scratch> bash tools/ship_sd.sh
--skip-blend`, run to the end): authored positions, the author's predicted render verts
(`render_vertex_count`) and what the exporter actually wrote into `<slug>_race.kn5`, against the
flat-shaded rehearsal before it.

| | objects | positions | worst object (positions) | predicted render verts | kn5 verts / tris (worst mesh) | flat-shaded kn5 before |
|---|---|---|---|---|---|---|
| chain | 8 | 28,530 | 7,160 | 45,768 | 45,768 / 56,996 (11,466) | 169,948 / 56,996 (42,706) |
| edge strips | 21 | 88,530 | 8,000 | 141,836 | 141,837 / 176,736 (12,809) | 522,482 / 175,116 (47,568) |
| kerbs | 7 | 6,088 | 1,400 | 9,170 | 9,158 / 9,078 (2,100) | 27,146 / 9,078 (6,254) |
| **race kn5** | **36** | **123,148** (123,140 after the prep's weld) | 8,000; `MAX_RINGS_PER_OBJECT = 800` | **196,774** | **196,763 / 242,810 = 0.81 per triangle; 12,558,972 B** | 719,576 / 241,190 = 2.98; 35,553,024 B |

Chain 8,525.3 m = 2,853 rings = 2,110 × 4.04 m modules; edge strips 26,307.4 m = 8,853 rings
(8,772 + 81 densified) after the fold skip; kerbs 481.6 m of declared runs = 1,522 stations after it.
The road kn5 is unchanged: 31 meshes / 1,258,109 v / 1,232,927 tri / 14 textures / 91,934,629 B,
per-mesh rows identical (its md5 is not stable: re-exporting the same `loop_main.blend` twice gives
two md5s, 189,579 bytes apart — the exporter, not the scene).

## 7. Commands

Dry run (never the hand-edit surface — a copy; the tool refuses an `--out-blend` under `airoso/tracks`):

```bash
BL="C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
cd C:/Users/Owner/Documents/GitHub/airoso
PYTHONUTF8=1 python tools/barrier_bands.py  "$P"                      # data agent's declaration
PYTHONUTF8=1 python tools/layout_dummies.py "$P"                      # data/dummies_<id>.json x3
"$BL" --background --python-exit-code 1 --python tools/author_race_furniture_blend.py -- "$P" --blend "$COPY"
"$BL" --background --python-exit-code 1 --python tools/split_exports_blend.py -- "$COPY" --project "$P" --out-dir "$OUT"
PYTHONUTF8=1 python tools/plot_race_furniture.py "$P"                 # data/race_plots/*.png (--planned before any Blender run)
PYTHONUTF8=1 python tests/run_tests.py
```

In `tools/ship_sd.sh` (wired 2026-10-11): `barrier_bands.py` → `layout_dummies.py` → the author →
`verify_race.py` → `plot_race_furniture.py` run on EVERY ship, after the signs block and outside
the `--skip-blend` guard (the author is idempotent and is what keeps `loop.blend` in step with the
config's `race.*`); the prep follows, then the split runs on the PREPPED `blender/<slug>.blend`
(materials assigned, no `AC_*` under the multi-layout guard), then the exporter runs once per
split scene, then `build_spawn_kn5.py`. `--dry-run` stops right before the first export;
`SHIP_PROJ=<dir>` (absolute, outside airoso) points EVERY step at a scratch copy — no relative `project`
argument remains — and a scratch run never syncs back into `tracks/san-diego-lake-murray/` or installs,
so it is safe without `--dry-run` too (`tests/tools/test_ship_sd_chain.py` pins both).

## 10. The gate before the kn5 — `tools/verify_race.py`

Reads `data/race_authored.json` + `data/barrier_bands.json` (+ the centreline and the island
bands) and exits 1 on any miss: provenance (not a stand-in, the same edge mode and height as the
declaration, the RACE prefixes, no failed run, ≤ 1 % interpolated rings), per-object budgets
(≤ 900 rings, < 60,000 positions, loops × 1.5 < 65,535 render verts, unique RACE name, seating gap
≤ 0.05 m), the chain (one object per declared run, every ring on a declared vertex, never on an
island beyond the nose or on Alvarado / inside the hairpin arc, run ends within 1.5 m of the
declared vertices, parts joined on their shared ring), the kerb-line strips (every declared vertex
covered on each side except the fold-dropped rings this file reports, no ring inside a bridge span,
every `join` end met by its neighbour, every `free` end at a declared gap edge), the kerbs (the
declared (apex, in|out) set == the authored set), the spawn clearance — HARD since 2026-10-11:
re-measured from every `data/dummies_<id>.json` of a race layout (what the spawn kn5s are built from),
a 1.9 m car on every grid / pit / hotlap slot stands ≥ 0.30 m off every strip face, else FAIL (the
author tool's own record fails on the same floor) — and the lamp posts (G: every mast, base = the
`lights.local.json` head set back by `author_lamps_blend.ARM_M`, footprint radius 0.585 m from
`lamp_post.obj`, stands outside every strip footprint; minimum margin reported) and, since the
2026-10-11 weld pass, the ring density (H: every chain / kerb-line strip span vs the DECLARED offset
curve rebuilt from the bands + centreline alone; a chord error above 0.15 m FAILS, fold spans are
counted not judged, spacing above 3.5 m is reported — the pre-densify build measures 0.271 m / 7.02 m
at the seam corner's outside lip and FAILS; the densified one 0.043 m / 3.50 m). `--pre-author` runs F
and G alone. Dry run (before the weld pass): OK — spawn minimum 0.48 m (AC_START_1/3/5/7 of both race layouts), lamps 238
masts beside a strip, minimum margin 2.36 m, none inside; chain worst ring spacing 3.16 m; edge missing {L 0, R 23} against
fold-dropped {L 0, R 27}; the two notes it raises are the 19 `other_deck_above` rings (the
ribbon's folds and the Del Cerro mouth step) and the outside-lip ring spacing: with one ring per
centreline vertex the outside lip of a 10 m corner gets rings 5-7 m apart and the strip chords the
arc by up to ~0.39 m (that estimate; measured against the declared curve it was 0.27 m — now H, and
fixed by `densify_rings`). Writes `data/race_verify.json`.

## 8. Pictures

`tools/plot_race_furniture.py` draws, Pillow only, an overview and 180 m windows (Alvarado grids,
hairpin, Del Cerro 4-way, the three chained corners, the I-8 chain end, the lap seam): pavement,
islands, chain (red), edge strips (orange forward-left / cyan forward-right), kerbs (red/white), the
three bridge gaps (yellow), the island noses, each layout's grid / pits / timing lines. It reads the
SEATED ring centres from `data/race_authored.json`; `--planned` draws the pure plan so the picture
exists before Blender.

## 9. What Kevin decides before the ship run (the constants)

| Q | knob | default |
|---|---|---|
| Q1 mouths | `edge_inset_by_vertex` (bands) | sealed — strip straight across the three mouth lines |
| Q5 height | `race.barrier_height_m` / `--barrier-height` | 1.20 m (the module's full silhouette) |
| Q6 edge placement | `race.edge_mode` / `--edge-mode` | `road` (on the pavement, 0.15 m off the curb) — `walk` puts it on the sidewalk top and gives the outer grid column +0.93 m |
| Q7 interior corners | `race.centre_runs` | continuous |
| Q8 kerbs | detector + declared runs | the seven runs at five corners |
| Q10 licence | `assets/licenses.json` → `UNRECORDED` entry for the K-rail pack | race kn5 FULL package only until recorded |
| Q11 collider | `--collider` | off |

Grid note (both race layouts): the grid stagger is 1.0 m (`tools/layout_dummies.GRID_STAGGER_M`, read
by `barrier_bands` and `race_furniture.synth_dummies`; 1.4 m until 2026-10-11). The staggered outer
slots (AC_START_1/3/5/7) sit at 4.25 m right of travel on 13.0 m Alvarado, so a 1.9 m car's outer
edge is 0.48 m from the edge strip's face at 5.68 m (`verify_race` F, `race_authored.json.spawn_clearance`,
`barrier_bands.json.no_gap_zones` all agree); the inner column is at 2.25 m. 0.30 m is the hard floor
(it was 0.08 m with the 1.4 m stagger — legal then, a fail now). Q6 `walk` would add 0.93 m.

AI lines (other agents' part, recorded here because the default changed): every layout ships a
GENERATED `write_ai_line` draft. The street layout's default is the V3 right-hand-lane draft
(`STREET_AI=draft` in `tools/ship_sd.sh`); `STREET_AI=july` opts into the installed July line, which
is itself a July `write_ai_line` draft — not an in-game recording — and drives the oncoming
carriageway on every divided run (ledger 0047 Notes).

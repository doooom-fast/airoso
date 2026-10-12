# Race furniture — the Lake Murray race corridors: barriers, kerbs, closures, the export split, the AI lines

Ledger 0047 (Kevin, 2026-10-10): three versions of the loop — the open street loop as today, and
the loop as a one-way race track in each direction, "with barriers making tracks out of the
north/south lanes … leading up to medians but not on them … barriers are for wide roads, Alvarado
should be the entire street … the tracks will get additional race curbs and barriers along the
inside of the sidewalks".

Ledger 0049 (Kevin, 2026-10-11) changed what the race versions ARE: "racetrack versions of these, we
need full intersections available for turning. And the entire other lane blocked off from access."
— "We want more or less an Alvarado's width for the entire track with deviances in various areas" —
open boxes at the "Corners the race turns at", side streets sealed. The 0047 shared centre chain is
retired; each race direction gets its OWN corridor (§0).

This document covers **what the race furniture is, how it is declared, authored, seated, named and
split into kn5s, how the race AI lines are drafted inside it, and which gates stand between it and an
install**. The design of record is the judged spec of 2026-10-11 (to be filed as ledger 0049, with the
brief verbatim); each tool's own docstring carries the detail.

**Status (2026-10-11): ledger 0049 has been built end to end on a SCRATCH copy of the workshop only —
nothing has reached `tracks/san-diego-lake-murray/loop.blend`, the workshop's `loop.blend` or the AC
folder.** The installed race layouts are still the 0047 build, which the containment gate measures as NOT
sealed (11 door clusters per layout, 752k m² reachable outside the corridor: the three bridge-span strip
gaps, the two chain free ends, all ten island noses — ledger 0049 Evidence). The full rehearsal
(`SHIP_PROJ=<scratch copy> bash tools/ship_sd.sh --skip-blend`, §7) ran every step from the v2 declaration to
the built gates; its gate lines are in §10 "Measured on the full rehearsal". In one line: both race layouts are
contained on their BUILT kn5 sets (no_route 0 leaks, lap complete, 0 / 406 forbidden probes reached),
`barrier_missing` 0 and `obstruction_stations` 0, and the street layout's gates are identical to the
pre-change build. The §1, §4 numbers marked "0047" were measured on the 0047 build and are kept because the
curb strips and kerbs are the same objects. **Fix round (2026-10-11, after the critic of `c0361f7`):** the
College/Navajo and Navajo/Jackson inside kerbs are dropped and the hairpin's inside kerb pulled back to
v751-763 (each lay across a ribbon fold, under the other road sheet — `race.kerbs.trims`, measured), so race
audit K is back to 154; `verify_race` E now fails any kerb under a road sheet and G any TreeFX trunk or sign
post in a race lane or wall (re-checked on the written `trees.txt` in the ship); build 0.17.0. The fix-round
rehearsal is at the end of §10; the exact ship command is `bash tools/ship_sd.sh --skip-blend --force-install`
with Assetto Corsa and Content Manager closed (ledger 0049 "Ship"). No tier is claimed: Kevin's drive is the only
ground truth.

---

## 0. The corridor (ledger 0049)

**The rule.** Each race layout drives an **Alvarado-wide lane on its own side of every road**:

| | What | Number |
|---|---|---|
| width | 11.36 m clear, wall face to wall face — Alvarado as raced (13.00 m curb to curb − 2 × 0.82 m strip inset, measured on 688/688 built stations) | MEASURED; running band 10.86-12.86 INVENTED |
| race side | the existing curb strip on that direction's right-hand curb, the whole lap | road face at `w/2 − 0.82` |
| closure | the SAME K-rail jersey strip (1.20 m, 0.67 m base), road face 11.36 m from the race-side strip face, following a flare-free base width (it stays straight where the curb wiggles) | `tools/race_corridor.py` solves it |
| whole street | where the base width is under 15.67 m (less than a 2 m lane would remain behind the wall): Alvarado and the I-8 deck | v4454 → v0 → v777 |
| islands | beside a median the corridor is that direction's own carriageway: the closure runs on the pavement 0.15 m off the island's race-side curb, nose tip to nose tip, crossing each tip on the race side ("leading up to medians but not on them") | 6.86 m clear minimum (College-1/2, Navajo-1/2) |
| open boxes | the whole intersection, curb strip to curb strip, at the corners the race turns at; each closure ends **pinned** into the far curb strip at the box edge (no free end, no cross barrier) | boxes v1506-1521, v2311-2328, v3289-3304; the seam and the hairpin lie in the whole-street zone |
| side streets | sealed: the race-side strip runs straight across the mouth, a far-side mouth is behind the closure, and both strips are continuous in the common kn5 | |
| no way across | every wall end is buried in another wall; both curb strips are closed loops (bridges included) | `no_route` proves it per layout |

**Zones (both layouts, vertex ranges):** WHOLE v4454 → v0 → v777; BOX [1506, 1521] [2311, 2328]
[3289, 3304]; CLOSURE A [777, 1506] College, B [1521, 2311] Navajo, C [2328, 3289] Jackson,
D [3304, 4454] Lake Murray Blvd (~10.9 km per direction, ~2.47 km of it along island faces). Pins:
v777, 1506, 1521, 2311, 2328, 3289, 3304, 4454. Funnels are 1:6 or gentler except the three the
geometry forces: 1:4.7 (v1506), 1:3.6 (v1521: the Navajo-1 island tip is 57 m from the box), 1:3.3
(v2311); the I-8 pin is 1:10 (the only at-speed funnel).

**Why one closure per direction, not one shared wall.** On a 17 m road the clockwise and anticlockwise
corridors overlap by 7.36 m, so each direction's closure stands INSIDE the other direction's lane. Each
race layout therefore loads only its own closure kn5 (§5); loading both would block both lanes.

| | 0047 (installed) | 0049 |
|---|---|---|
| centre K-rail chain shared by both race layouts | 8.5 km in 6 runs, free ends at v780 / v4440 | **retired** (`1WALL_race_kbar_*` anywhere FAILS) |
| curb strips | both curbs, gapped over the 3 bridge spans | both curbs, **one closed loop per side, no gaps** |
| closure | none | **one per direction**, 4 pinned runs |
| race kerbs | 7 | **10** — the inside kerbs at v1514 / v2319 / v3297 come back, clipped clear of every closure |
| kn5s a race layout loads | road + `_race` + spawn | road + `_race` (common) + `_closure_<id>` (its own) + spawn |
| containment gate | none | `no_route` flood fill per layout, planned and built; hard, blocks install |

Frames: **y** = metres forward-LEFT of the increasing-vertex tangent (the declaration and the author
sweep in it); **r** = metres right of a layout's own travel (cw `r = −y`, acw `r = +y`). race_cw travels
increasing v with its race side R (the lake side, the inside of every bend); race_acw travels decreasing v
with its race side L.

## 1. What gets built

| Kind | Mesh names | Where | Geometry |
|---|---|---|---|
| Kerb-line strips (COMMON) | `1WALL_race_edge_<L\|R>_<street>_<start>_<part>` | BOTH curb faces of EVERY street, Alvarado included, as **one closed loop per side** — continuous over all three bridge spans (`race.edge_gaps: "none"`), cut into objects at street boundaries that share rings (no caps, no free ends) | a swept jersey strip whose cross-section IS Kevin's `assets/models/concrete_barrier_4m.obj` silhouette (0.67 m base, 1.20 m tall), centre at `half_w − 0.485` (road face at `half_w − 0.82` = `race.edge_inset_m`), straight across every sealed mouth; the inside lip trimmed to the curb's own corner at the five folds (§4) |
| Closures (ONE PER RACE LAYOUT) | `1WALL_race_close_<token>_<street>_<start>_<part>`, `token` = `layouts[].closure_token` (`cw` / `acw`) | that layout's four closure runs (§0), split at ≤ 800 rings with shared boundary rings (~7 objects per direction) | the same strip on the declared `closure_y_by_vertex` curve; first and last ring centred ON the far curb strip's centre line at the pin vertex, full height, no taper — the cap is buried inside the strip's 0.335 m half base |
| Race kerbs (COMMON) | `1KERB_race_<apex>_<in\|out>` (10 objects) | inside + outside at each of the five corners (v0, v770, v1514, v2319, v3297), each clipped to the longest run of stations that stands ≥ 0.05 m clear of EVERY race layout's closure footprint | 1.0 m wide × 0.05 m flat rumble strip ON the pavement, inboard of the edge strip (outer edge at `half_w − 0.87`), 0.10 m lane-side ramp, height tapering over the first/last 3 stations, 0.3 m stations |
| (optional, OFF) tall invisible collider | `1WALL_racecol_<k>` | `--collider` only | 2-vert/station sheet, deck −0.3 … +2.5 m — the Macau pattern, deferred (Q11); needs the `1WALL_RACECOL` pbr/ALPHATEST row and `assets/textures/invisible_4x4.png` (generated, CC0) first |

Every name upper-starts with one of `RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")` — what the export
split, `verify_kn5`, `check_race_kn5` and `audit_mesh --race` key on — so the `pbr.py` rows
`1WALL_RACE` / `1KERB_RACE` bind all of it and no new texture exists. In Blender the common objects sit
in collection `RACE` and each direction's closures in `RACE_CLOSE_CW` / `RACE_CLOSE_ACW` (toggle a
direction to see it); the NAME token is authoritative, because the prep re-links objects to the scene
root. `L`/`R` are in the FORWARD frame (increasing vertex index = clockwise).

The strip itself (measured on the 0047 build; the closures are the same strip):

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
trimmed corner's two chords (leg ring → corner X → leg ring, §4 below) are only cut on their own straight lines, the fill rings square to the chord. 81 rings
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

`data/barrier_bands.json` **version 2** (written by `tools/barrier_bands.py` from
`track.config.json` `race.*` + `layouts[]`, self-gated, exit 1 on any failure) is read for everything
that decides WHERE geometry goes, so the declared band and the authored strip are the same thing (the
2026-10-08 median_zone precedent; L5 still holds because the gates measure the built OBJ).

**Config (`tracks/san-diego-lake-murray/track.config.json`).** `race.corridor` declares the rule:
`clear_width_m` 11.36 with `clear_width_source: "alvarado"` (re-measured as median(w − 2 × 0.82) over
v25-723; > 0.02 m off FAILS), `island_mode: "pavement"`, `whole` [4454, 777], the three `boxes`, the
PINNED `closure_runs` (a derived run that differs FAILS — "declared, validated, never derived
silently"), the rates (toward the race side 1:12, away 1:6, pin zone 120 m at ≥ 1:6, the I-8 pin 1:10,
steepest 1:3), the base-width filter (open ±60 m, σ 20 m), `clear_floor_m` 10.86, `clear_hard_min_m`
6.5, `pocket_min_m` 2.0. `race.edge_gaps: "none"`. `race.centre_runs` / `wide_threshold_m` /
`interior_corners` are REMOVED — barrier_bands v2 FAILS while `centre_runs` is present. Each race layout
carries `closure_token` (`cw` / `acw`).

**The file.** Kept from version 1: `params` (with `params.corridor` echoed), `streets`, `corners`,
`edge_corners` (the five trimmed R-side folds), `closed_mouths`, `kerbs` (now 10, with the clipped i/j),
`bridge_spans_m` (informational). Changed: `edge_strip_by_vertex` all 1, `edge_inset_by_vertex` all 0.82,
`edge_gaps` [], `centre_w_by_vertex` all 0 (kept one version so old readers see no chain), `runs` [].
New, per race layout, `corridors.<id>`:

| key | what |
|---|---|
| `token`, `direction`, `race_side`, `closure_side` | `cw` / forward / R / L and `acw` / reverse / L / R |
| `zone_by_vertex` | `whole` / `box` / `pin` / `closure` / `island` |
| `closure_y_by_vertex` | the closure strip CENTRE, forward-left metres; null where none stands (pins included) |
| `lane_by_vertex` | `[y_lo, y_hi]`, the corridor's two wall FACES, forward frame — what drive_test, median_zone, verify_kn5 (d), no_route and the AI writer all read |
| `runs`, `pins` | each closure run with its pins, rates, clear minimum and every vertex below the floor with its reason |
| `mouths` | per side-street mouth: `sealed_race_strip` or `behind_closure` |
| `no_route` | seed `AC_START_0` and the forbidden probes (a pocket centre every 25 m, every island top every 25 m, 10 m into each connector mouth) |

The author reads the declaration: `edge_strip_by_vertex` for the strips (all ones = one closed loop per
side), `closure_y_by_vertex` (lerped, the same declared curve as the strips) for the closures,
`kerbs` for the kerb runs (the detector still finds the corners and decides inside/outside; the
declared i/j replace its own), `streets` for the street token and the split points. `closed_mouths` are
gate-only here (the strip is continuous across a mouth by construction). If the file is absent the
author refuses; `--edge-mode walk` (Q6) and `--barrier-height` (Q5) remain one constant each.

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

**Folds are trimmed to the curb's own corner (2026-10-11).** Where an inside lip is tighter than the
strip's offset (|lat| > R: the hairpin v770, College/Navajo v1514, Navajo/Jackson v2319, Jackson/Lake
Murray v3297, the seam v0) the offset curve runs forward through a self-intersection X to a cusp,
BACKWARDS to a second cusp, and forward through X again — a swallowtail; the ROAD ribbon's own inside
edge folds the same way, and the pavement's real inside boundary, the curb, is the TRIMMED curve: the
in-leg up to X, then the out-leg. `race_furniture._trim_folds` does exactly that to a strip's rings and
to an inside kerb's stations: a backward step is one behind its predecessor along EITHER record's
tangent, backward steps within 6 m are one fold, each fold is cut between the in-leg and out-leg
segments that cross (`loop`: the hairpin, College/Navajo, Navajo/Jackson) or, where the legs never cross
because the lip flares or the width steps while it folds, the last real in-leg step and first real
out-leg step are extended to meet (`extend`, ≤ 8 m each: Jackson/Lake Murray 3.09 m, the seam 6.99 m),
and ONE mitred corner record stands at X (profile on the bisector, lateral scale 1/cos(ψ/2), 1.20–1.45
here) with every leg record nearer X than the mitre's reflex tip dropped too. The one-sided drop it
replaces (`drop_folded_rings` / `drop_folded_stations`) tested a ring only against its own tangent, kept
the "ear" rings past X (v768, v1512, v2317, v3295) and chorded BACKWARDS from them: six inside-out
strip spans, a hook of wall standing 1–3.5 m inside the exit carriageways of the three chained corners
(52 of race_cw's 220 obstruction stations) and seven inverted inside-kerb spans. The trimmed corners are
DECLARED — `barrier_bands.json` `edge_corners`, computed by `race_furniture.edge_fold_corners`, the same
plan + trim, and the author refuses a declaration that differs — so audit D's band, drive_test's presence
probe and verify_race D / H all stand on the built corner. Rehearsal 2026-10-11: 41 edge rings trimmed,
all forward-RIGHT (hairpin 10, College/Navajo 8, Navajo/Jackson 9, Jackson/Lake Murray 7, seam 7); kerbs
`1KERB_race_770_in` 73 stations (one loop corner), `1KERB_race_0_in` 25 (one extend corner, +59° — it
follows the ribbon's 27.5 → 17 m width-step jog at the seam). Each object records `fold_corners` and
`fold_skipped(_run)` (a corner is reported by the object holding its corner ring); the real-data test
pins that the only flagged vertices without a ring are the declared corners' removed sets.

**The seam corner stands over the ribbon's notch.** The closure steps the road from Lake Murray's 27.5 m
(v4497) to Alvarado's 17.0 m (v0) inside one 2.29 m segment, so the ribbon's inside lip jogs 5.25 m
sideways inside the right-hander; the strip's extend corner continues Lake Murray's strip line straight to
Alvarado's and 4.16 m of its 6.99 m corner polyline stands off the ROAD ribbon, over the curb notch (one
ring seated by interpolation; Jackson/Lake Murray's Z-fold finger leaves 0.40 m off). No gate fails on it.
The fix is the ribbon's, not the strip's: taper the width over the seam corner in the centreline widths
(the mouth flares elsewhere step ≤ 1.5 m per 3 m vertex) and rebuild the ribbon (a draft-layer change).

**Bridges (0049).** The curb strips now run over all three spans (C1), seated on the mainline deck rows like everywhere else: 0.82 m inboard of the College panel and ~0.15 m inboard of the I-8 deck rail; audit's wall-crossing check gates any clash, and the author reports the rings seated inside the spans as hit / near / interpolated (verify_race L fails any interpolated one). The 0047 `BRIDGE_CLEAR_M` gap and the free-end / nose tapers are retired.

## 5. The export split — one blend, four kinds of kn5

`tools/split_exports_blend.py <blend> --project <dir> [--out-dir DIR] [--layouts a,b,c]` opens the
input fresh for each output and **removes** what does not belong (then `meshes.remove` +
`orphans_purge`), never saving over the input:

| output | holds | → kn5 (loaded by) |
|---|---|---|
| `loop_main.blend` | everything EXCEPT RACE members / `1WALL_RACE*` / `1KERB_RACE*` names and every `AC_*` object | `<slug>.kn5` — the road, unchanged (all three layouts) |
| `loop_race.blend` | the COMMON race furniture: both curb strips + the declared kerbs (8 since the 0049 fix round); no `1WALL_RACE_CLOSE_*` | `<slug>_race.kn5` (race_cw, race_acw) |
| `loop_close_<id>.blend` ×2 | that race layout's `1WALL_RACE_CLOSE_<TOKEN>_*` only | `<slug>_closure_<id>.kn5` (that layout ONLY) |
| `loop_spawn_<id>.blend` ×3 | `AC_*` empties from `data/dummies_<id>.json` (tools/layout_dummies.py) | `<slug>__<id>.kn5` (own layout) |
| `split_manifest.json` | census per output + problems (exit 1 on any: an undeclared token, a KBAR object, an empty closure blend, a closure object in `loop_race.blend`, race ∪ closures ≠ all RACE objects, an orphan material) | |

**The inis (`scripts/ac/track_folder.py`).** `models_race_cw.ini` = [`<slug>.kn5`, `<slug>_race.kn5`,
`<slug>_closure_race_cw.kn5`, `<slug>__race_cw.kn5`] — spawn last, as before; `models_race_acw.ini`
the mirror with its own closure; `models_street.ini` unchanged ([road, `__street`]). **No ini ever names
another layout's closure kn5.** The closure name comes from the layout id, the mesh token from
`closure_token`; `closure_kn5_name` refuses a declaration that is not whole (race.corridor declared and a
race layout without a token, two layouts with one token, a token on a non-race layout). With
race.corridor declared, a race layout whose `build/<slug>_closure_<id>.kn5` is missing is a HARD error
(`--allow-missing-kn5`, dry runs only, still names it), and a `<slug>_closure_*.kn5` in the folder that no
declared layout loads is removed before packing. A track without race.corridor keeps the 0047 shape
([road, `_race`, spawn]).

**The packages (`tools/pack_release.py`).** By default the CC0 variant is Lake Murray Free Roam only: it drops the
race layouts, `<slug>_race.kn5` and EVERY `<slug>_closure_*.kn5` (by name, so a stale one goes too);
`--with-race` keeps all three layouts in it (and renders the release texts' `[[with-race]]` blocks: the K-rail
credit on every race kn5, the three-version README). The split is a tool, not a rule — which package goes
public is Kevin's call at publish time (Kevin, 2026-10-11: "No one actually cares about assets in free mods for
a 13 year old game"; `docs/PUBLISHING.md`). What the K-rail is, for the record: Kevin's owned asset pack (the
4 m jersey module, `assets/models/concrete_barrier_4m.obj` + `concrete_barrier_diffuse/normal.png`,
`fleet/reference/ASSET-LIBRARY.md`), whose licence terms are not recorded in `assets/licenses.json`. The
street layout is in both packages.

Why removal and not selection, collections or `__` renames: the exporter that actually runs
(`exporter.kn5`, the AppData blender-assetto-corsa-tools 1.0.7) walks `blend_data.objects`
(selection ignored), embeds every material with `users > 0` (a mesh datablock keeps its material
"used" after the object is gone), and the prep's `_split_large` re-links tiles to the scene root so
collection membership cannot be trusted after the prep. The race filter is therefore RACE-membership
OR name prefix, and the closure filter the `1WALL_RACE_CLOSE_<TOKEN>` name token.

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
writes `data/dummies.json = {}`. Measured on the prepped scratch scene (0047, chain included): `loop_race.blend` = 36
meshes / 122,330 positions / **36 RACE-named materials** / 0 AC nodes, `loop_main.blend` = 20 meshes
/ 727,123 positions / 20 materials / 0 AC / 0 race objects, `split_manifest.json` problems `[]`.

**Export.** `export_kn5_addon.py` (engine-july, mirrored byte-identical into airoso) takes
`--blend <file>` and `--out <name.kn5>` and runs once per split scene — `loop_main.blend` →
`<slug>.kn5`, `loop_race.blend --out <slug>_race.kn5`, and per race layout
`loop_close_<id>.blend --out <slug>_closure_<id>.kn5`. Each is content-checked by the ship script with
`inspect_kn5 --json` then `tools/check_race_kn5.py`: `--role common` FAILS on any non-RACE mesh, any
CLOSE or KBAR mesh, no edge mesh, a kerb count other than the declaration's (`--bands`: 8 on SD), a texture outside the race rows or any
`AC_*` node; `--role closure --owner <token>` FAILS unless every mesh is `1WALL_RACE_CLOSE_<TOKEN>_*` (at
least one, no kerbs or edges, race textures only, no `AC_*`). Both WARN above 20 MB. Each pass purges
and rewrites the one persistence `.ini` (named after its kn5) from the materials the opened scene holds,
so each kn5 embeds only its own material table.

**Spawn blends vs `scripts/ac/build_spawn_kn5.py`.** The chain of record builds the spawn kn5s with
`build_spawn_kn5.py` straight from `dummies_<id>.json` (same placement, plus the true-north yaw
composition, 0.0 on SD). The split's `loop_spawn_<id>.blend` files are the inspectable equivalent —
open one in Blender to see the grid — and a fallback input, not a second source of truth.

## 6. Budget

**0049, measured on the full scratch rehearsal (2026-10-11)** — the spec §8 estimates were ~9.9 MB common and ~3.8 MB per closure:

| kn5 | meshes | verts / tris (per triangle) | bytes | loaded by |
|---|---|---|---|---|
| `<slug>.kn5` (road) | 31 | 1,258,109 / 1,232,927 | 91,934,629 (unchanged) | all three layouts |
| `<slug>_race.kn5` (common) | 25 = 15 curb strips + 10 kerbs (fix round: 23 = 15 + 8) | 152,576 / 188,326 (0.81); fix round 151,984 / 187,764 | 10,283,552; fix round 10,253,588 | race_cw, race_acw |
| `<slug>_closure_race_cw.kn5` | 6 | 58,272 / 72,684 (0.80) | 5,433,534 | race_cw only |
| `<slug>_closure_race_acw.kn5` | 6 | 58,256 / 72,664 (0.80) | 5,432,722 | race_acw only |

The closures are 1.6 MB each over the estimate (the exporter writes ~93 B per render vertex here, not 63.8). The
FULL package's race files grow from 12.56 MB (0047's one race kn5) to 21.15 MB, **+8.6 MB**; the CC0 package is
unchanged by default (`tools/pack_release.py` strips `_race.kn5` and every `_closure_*.kn5` unless `--with-race`,
which adds the same +21 MB to it). The table below is the
**0047** build as measured.

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
PYTHONUTF8=1 python tools/barrier_bands.py  "$P"                      # v2 declaration + self-gates + planned no_route
PYTHONUTF8=1 python tools/layout_dummies.py "$P"                      # data/dummies_<id>.json x3
"$BL" --background --python-exit-code 1 --python tools/author_race_furniture_blend.py -- "$P" --blend "$COPY"
PYTHONUTF8=1 python tools/verify_race.py "$P"                         # common + each race layout
"$BL" --background --python-exit-code 1 --python tools/split_exports_blend.py -- "$COPY" --project "$P" --out-dir "$OUT"
PYTHONUTF8=1 python tools/plot_race_furniture.py "$P"                 # data/race_plots/<id>/ (--planned before Blender)
PYTHONUTF8=1 python -m scripts.ac.write_ai_line "$P" --layout race_cw     # and race_acw, street
PYTHONUTF8=1 python -m scripts.ac.track_folder "$P" --allow-missing-kn5   # dry run: inis name every kn5
PYTHONUTF8=1 python tests/run_tests.py
# the BUILT gates of one race layout (after its three kn5s exist):
PYTHONUTF8=1 python -m scripts.modkit.kn5_to_gate_obj "$P" --kn5 "$P/build/$SLUG.kn5" --kn5 "$P/build/${SLUG}_race.kn5" \
    --kn5 "$P/build/${SLUG}_closure_race_cw.kn5" --out "$P/data/track.race_cw.obj"
PYTHONUTF8=1 python -m scripts.geometry.drive_test "$P" --layout race_cw   # data/drive_test.race_cw.json
PYTHONUTF8=1 python -m scripts.geometry.audit_mesh "$P" --layout race_cw   # data/audit.race_cw.json
PYTHONUTF8=1 python tools/no_route.py "$P" --layout race_cw                # data/no_route.race_cw.json
```

In `tools/ship_sd.sh` the order is (spec §14):

1. `barrier_bands.py` v2 — the corridor solve, the self-gates and the PLANNED no_route per race layout (exit 1
   on any of them); the ship then reads `data/no_route.<id>.planned.json` back and stops before Blender unless
   each says fail false with 0 leaks, nothing blocked, no probe reached, every spawn reached. Earlier runs'
   planned and built verdicts are deleted first, so a stale pass is never read.
2. `layout_dummies.py` → the author (collections `RACE`, `RACE_CLOSE_CW`, `RACE_CLOSE_ACW`) → `verify_race.py`
   (common + each layout) → `plot_race_furniture.py`.
3. The prep → the split: `loop_main.blend`, `loop_race.blend` (common), `loop_closure_<id>.blend` per race layout
   (the chain stops if one is missing), `loop_spawn_<id>.blend` ×3. `--dry-run` stops here.
4. The exports, each content-checked: road; `${SLUG}_race.kn5` + `check_race_kn5 --role common --bands
   data/barrier_bands.json`; per race layout `${SLUG}_closure_<id>.kn5` + `check_race_kn5 --role closure
   --owner <token>` (the token read from `barrier_bands.json corridors.<id>.token`).
5. Spawn kn5s → AI per layout → `verify_kn5` (d)/(f) → `track_folder` (a race layout without its closure kn5 is a
   HARD error) → the road kn5 copied into the folder → `verify_kn5 --inis` (g) → `make_map`, `make_treefx`.
6. Gates. Every per-layout verdict file (`drive_test.<id>.json`, `audit.<id>.json`, `no_route.<id>.json`,
   `track.<id>.obj`) is deleted first; 0047's shared `track.race.obj` / `audit.race.json` are retired. Street:
   `kn5_to_gate_obj` (road) → `drive_test --layout street` → `audit_mesh`. Per race layout: `kn5_to_gate_obj`
   (road + common + ITS closure → `data/track.<id>.obj`) → `drive_test --layout <id>` → `audit_mesh --layout
   <id>` → `no_route --layout <id>` (BUILT).
7. `RACE_RED`: a race layout is red when its drive_test row is missing or not run, `barrier_missing` > 0,
   `obstruction_stations` > 0, or its BUILT `no_route.<id>.json` is missing or reports a leak, a blocked span,
   a reached forbidden probe or an unreached spawn. A red race layout is never installed, `--force-install`
   or not; a no_route input error (exit 2) also stops the install.
8. Sync back (adds `no_route.<id>.json`, `no_route.<id>.planned.json`, `audit.<id>.json`,
   `closure_<id>.kn5.json`, `race_kn5.json`; removes the retired `audit.race.json`; never the 66-78 MB gate
   OBJs) → install (unchanged mechanics).

`SHIP_PROJ=<dir>` (absolute, outside airoso) points EVERY step at a scratch copy and a scratch run never
syncs back or installs.

## 8. Pictures

0047: `tools/plot_race_furniture.py` drew, Pillow only, an overview and 180 m windows (Alvarado grids,
hairpin, Del Cerro 4-way, the three chained corners, the I-8 chain end, the lap seam): pavement,
islands, chain (red), edge strips (orange forward-left / cyan forward-right), kerbs (red/white), the
three bridge gaps (yellow), the island noses, each layout's grid / pits / timing lines. It reads the
SEATED ring centres from `data/race_authored.json`; `--planned` draws the pure plan so the picture
exists before Blender.

0049 (spec §10): per race layout (`data/race_plots/<id>/`) an overview, the five corners, Del Cerro, the I-8 end, the ten noses and the eight pins, the closure drawn in its own colour; `--planned` still draws the declaration before Blender.

## 9. What Kevin decides (the constants)

| Q | knob | default |
|---|---|---|
| Q1 mouths | `edge_strip_by_vertex` / `mouths` (bands) | sealed — the race-side strip straight across, a far-side mouth behind the closure |
| Q2 / Q7 the 13.5-17 m stretches / interior corners | (0047 `centre_runs`) | **moot**: the chain is retired; the corridor rule decides (§0) |
| Q5 height | `race.barrier_height_m` / `--barrier-height` | 1.20 m (the module's full silhouette); real street K-rail is 0.81-1.07 m, which would let you see over the closure to the closed lanes |
| Q6 edge placement | `race.edge_mode` / `--edge-mode` | `road` (on the pavement, 0.15 m off the curb) |
| Q8 kerbs | detector + declared runs + `race.kerbs.trims` | eight runs at five corners (0049 fix round: the 1514 / 2319 inside kerbs dropped and the 770 inside kerb pulled back to v751-763, each off a ribbon fold, measured), clipped clear of every closure |
| Q9 L8 wording | "layouts add kn5s, never alter the road" | the build proceeds under the proposed wording; the law entry waits for Kevin's OK |
| Q10 licence | — | **settled** by Kevin's stance (2026-10-11): provenance never withholds a release; `pack_release --with-race` puts the race layouts in the CC0 package when he wants them public (default street-only until the site catalog is updated) |
| Q11 collider | `--collider` | off |

**Tune after the drive, not before (one knob each):** width on the 17 m roads (`race.corridor.clear_width_m`
11.36; the alternative is own-side-only, ~7.7 m with the wall on the centre line), the median carriageways
(`island_mode` pavement, 6.86 m minimum; `island_top` gains 0.97 m after the three proofs of spec §5), the
steep exit funnels (start them inside the box edge), the grid (centred, §13 of the spec).

Grid note (both race layouts, unchanged by 0049 — both grids are on Alvarado, whole street): the grid
stagger is 1.0 m (`tools/layout_dummies.GRID_STAGGER_M`); the staggered outer slots (AC_START_1/3/5/7)
sit 4.25 m right of travel on 13.0 m Alvarado, 0.48 m from the edge strip's face (floor 0.30 m); the
nearest closure is about 1.3 km away.

## 10. The gates (spec §11)

Three invariants, checked at four stages; a race layout that fails any of them is **never installed,
`--force-install` or not** (`RACE_RED` in `tools/ship_sd.sh`).

| invariant | plan (`barrier_bands` v2) | authored (`verify_race`) | kn5 | built (gate OBJ) |
|---|---|---|---|---|
| **CONTAINED** — from AC_START_0 nothing outside the corridor is reachable | planned `no_route` = 0 | D (both strips every vertex, bridge spans included), J (no free ends: edges join, closures end in pins), L (no interpolated ring inside a span) | owners + inis | `no_route` = 0, `barrier_missing` = 0 |
| **CLEAR** — the lane is open end to end | no closure in BOX/WHOLE; floors | C′ (every closure ring on the declared curve, pins at the far strip line full height), F (spawns), G (lamps vs strips AND closures) | — | `obstruction_stations` = 0; the no_route lap complete |
| **OWNED** — each layout loads only its own closure | tokens declared | K (tokens declared, rings on their layout's curve) | `check_race_kn5` roles; `verify_kn5` (f) per-layout closure + (g) each race ini = [road, `_race`, `_closure_<id>`, `__<id>`], no ini lists another's closure | per-layout gate OBJ |

`tools/verify_race.py` (after authoring, before any kn5; exit 1) keeps A, B, E, H, I as before and adds
C′, J, K, L, M (mouths per policy on the authored rings), N (no `1WALL_race_kbar_*`, `centre_w_by_vertex`
all 0); D inverts 0047's "no ring inside a span". The built gates run per race layout on
`data/track.<id>.obj` (road + `_race` + `_closure_<id>` through `kn5_to_gate_obj`): `drive_test --layout`
(the lane is `lane_by_vertex`, 0.4 m in from each face; boxes and the whole street full width),
`audit_mesh --race --layout` (D exempt only on this layout's bands; at or below the street baseline), and
`no_route --layout` — a 0.25 m flood fill from AC_START_0 over everything within `w/2 + 25 m` of the built
centreline, where only a wall spanning [deck + 0.20, deck + 0.90] counts (the island beam alone must NOT
seal an island), dilated 0.5 m; any reached cell outside the corridor, a reached forbidden probe or an
unreached lap point FAILS. The spec's teeth: today's `track.race.obj` FAILS with 51 door clusters; the
planned 0049 passes both layouts. Every threshold, bypass and INVENTED constant is in
`fleet/GATES-CHANGELOG.md`.

### Measured on the full rehearsal (2026-10-11, scratch copy of the workshop, `bash tools/ship_sd.sh --skip-blend`)

Run twice on fresh copies with identical numbers; about 5 minutes end to end.

| stage | race_cw | race_acw |
|---|---|---|
| planned no_route (`barrier_bands` + the ship's read-back) | PASS: 0 leaks, 0 blocked, 0 / 406 probes, 0 spawns unreached, 139,130 m² reached | PASS: the same, 138,826 m² |
| verify_race (common + each layout) | OK — closure 6 objects / 4 runs / 3,637 rings, ≤ 0.007 m off the declared line, 8 pins ≤ 0.006 m off the far strip line | OK — 3,636 rings, ≤ 0.007 m, pins ≤ 0.005 m |
| common set (verify_race) | 15 curb-strip objects / 9,054 rings, closed loops; every vertex covered on both sides except 30 R vertices, all inside the 41 declared trimmed-corner vertices (0 undeclared gaps, worst gap 3.503 m); 328 bridge rings seated by direct hit, 0 interpolated; 0 free ends; 16 pins 0.000 m off the authored far strip; 10 kerbs | |
| split | `loop_race.blend` 25 meshes; `loop_closure_race_cw.blend` 6 meshes | `loop_closure_race_acw.blend` 6 meshes |
| check_race_kn5 | common OK (15 strips + 10 kerbs, no closure); closure `cw` OK | closure `acw` OK |
| verify_kn5 / `--inis` | OK — 16 START/PIT cars inside the lane, nearest face 0.48 m; ini = road + `_race` + `_closure_race_cw` + spawn | OK — the mirror, ini lists only `_closure_race_acw` |
| drive_test (`track.<id>.obj`) | `barrier_missing` 0 of 37,869 probed, `obstruction_stations` 0, severe steps 0 | 0 of 37,870, 0, 0 |
| audit_mesh `--layout` | D 0 / K 158 / I 145 / F 15, W 0 | D 0 / K 158 / I 145 / F 15, W 0 |
| no_route BUILT | **PASS** — 0 leaks, 0 doors, 0 / 406 probes, lap complete, 0 spawns unreached, 139.1k m² reached | **PASS** — the same, 138.8k m² |
| RACE_RED | not red | not red |

Street (the regression floor): drive_test 82 / 391 / 0 / 101 (soft top / floating / severe / excursion
drops), audit D 512 / K 154 / I 145 / F 15 — identical to the pre-change workshop build, `audit.json`
byte-identical in every field; the street AI line is byte-identical.

**Read these two numbers correctly.**
- **Race K 158 vs the 154 baseline — a ribbon defect, named, not exempted.** The 4 extra hits are one spot: the
  end of the new inside kerb `1KERB_race_1514_in` at v1518 (College/Navajo inside corner). The road there is
  TWO `1ROAD` sheets 0.093 m apart (y 24.372 and 24.465 at (-1960.5, 595.3)) — the inside-corner fold, the
  0033/0046 class. The kerb sits flush on the upper sheet (the one a wheel meets, kerb top +0.04 m); check K
  measures every kerb vert against the LOWEST sheet beneath it and reads +0.133 / +0.136 m (2 positions × the
  smooth-shading split). The fix belongs to the ribbon (one sheet at the fold), not to the kerb or the gate.
- **Race D 0 vs the street's 512 — an exemption effect, not a fix.** All 512 street D verts are the road kn5's
  own `1WALL_guard` (bridge rails, island-beam ends); every one stands inside a race layout's declared curb-strip
  or closure band, where `--layout` exempts D by design. The street audit still counts all 512.

**Teeth on the real kn5s** (same scratch build, `no_route --layout race_cw --obj ...`): road + common WITHOUT the
closure kn5 → FAIL, 81,466 m² outside the corridor through 5 door clusters (4 opposite, 1 island), 390 / 406
probes reached; road + common + the OTHER direction's closure (`_closure_race_acw`) → FAIL, 60,266 m² through 10
opposite doors, 311 / 406 probes reached, the lap blocked in 20 spans.

### Measured on the fix-round rehearsal (2026-10-11, 14:41:36-14:46:56, a fresh scratch copy, `--skip-blend`)

The K 158 above is gone: the kerbs it came from are out of the declaration (§9 Q8, ledger 0049 "Fix round").

| stage | race_cw | race_acw |
|---|---|---|
| planned no_route | PASS: 0 leaks, 0 blocked, 0 / 406 probes, 0 spawns unreached, 139,130 m² | PASS: the same, 138,826 m² |
| verify_race | OK — 8 kerbs, `under_road` 0 on every one; closure 3,637 rings ≤ 0.007 m, pins ≤ 0.006 m; G lamps 0 inside; G scenery 15,261 TreeFX + 18 sign posts, 394 beside the race road, 0 in a lane or wall (nearest 0.655 m) | OK — 3,636 rings, ≤ 0.007 m, pins ≤ 0.005 m |
| check_race_kn5 | common OK (15 strips + 8 kerbs, 10,253,588 B); closure `cw` OK | closure `acw` OK |
| verify_kn5 / `--inis` | OK / OK | OK / OK |
| scenery on the written `trees.txt` | OK — 0 in a lane or wall, nearest 0.656 m | |
| drive_test | `barrier_missing` 0 of 37,869, obstruction 0, severe 0; soft top 44, excursion 1 | 0 of 37,870, 0, 0; soft top 40, excursion 0 |
| audit_mesh `--layout` | **D 0 / K 154 / I 145 / F 15, W 0** | **D 0 / K 154 / I 145 / F 15, W 0** |
| no_route BUILT | **PASS** — 0 leaks, 0 doors, 0 / 406 probes, lap complete, spawns reached | **PASS** — the same |

Street: identical to the installed build (drive_test 82 / 391 / 0 / 101, `audit.json` byte-identical, street AI
byte-identical). race_acw's soft top 40 (the installed 0047 build: 13) is the same inherited grass-through-road
on the unchanged road kn5 seen through a wider lane — the open boxes are now the whole intersection (ledger 0049,
"No worse than the installed build").

## 11. The AI lines (`scripts/ac/write_ai_line.py --layout race_cw|race_acw`)

With a version-2 bands file a race layout drafts inside `corridors.<id>`, never the retired chain (a
version-1 file keeps the 0047 lane byte for byte; a version-2 file without the layout's corridor
refuses). What the writer does:

- **Lane.** `lane_by_vertex` converted to metres right of the layout's own travel (lo may be past the
  centreline on a 17 m road), stopped at each authored island outline (`author_median_blend`'s nose
  taper); the target is the lane centre — about 2 m right of the centreline on a 17 m road, 0 on
  Alvarado, the deck and in a box — smoothed by a bounded least-squares solve (25 m, INVENTED) so funnels,
  convergences and the whole-street/closure joins are tapers, never steps.
- **Open corners.** At every declared corner whose apex is in an open zone and that turns ≤ 170° (the seam
  and the three boxes; the 177° hairpin keeps today's 12.6 m floor fillet), the line holds the corridor's
  OUTSIDE comfort edge from 60 m before the corner's arc to its end — as an envelope that never moves
  sideways faster than 1:10, so a steep funnel face is not chased — and the corner is replaced by the
  largest straight-arc-straight that keeps 1.5 m off every face (the apex lands 1.5 m off the trimmed
  inside corner X). A window never reaches into another corner's arc.
- **Refusals (hard, on top of today's backward-step / self-crossing / turn / radius checks).** Any point
  of the line — walked every 0.25 m along it, not only at its 1.5 m points (the binding constraint is the
  sharp corner X, which a chord can pass much closer than either end) — beyond a face, on an authored
  island, or under 0.6 m from a face (funnels and island faces included) or a sealed mouth line. The faces
  are polylines on the walls' own vertex frame, fold-trimmed at the five inside lips like the strips.
- **sideLeft / sideRight** are the distances to the two faces minus the margin. `ai_draft.json` carries a
  `corridor` block with every number below.

**Measured 2026-10-11** on a scratch copy of the workshop data with the barrier_bands v2 declaration
(`tools/barrier_bands.py` on the ledger-0049 config; identical results on the spec's prototype fixture):

| | race_cw | race_acw |
|---|---|---|
| wall clearance, minimum (along the line) | 1.48 m | 1.49 m |
| points beyond a face / under 0.6 m / on an island / sealed-mouth minimum | 0 / 0 / 0 / 5.85 m | 0 / 0 / 0 / 5.72 m |
| corner arcs, radius (speed): seam v0 | 45.1 m (96 km/h) | 47.5 m (98 km/h) |
| v1514 College/Navajo | 28.7 m (76 km/h) | 52.3 m (103 km/h) |
| v2319 Navajo/Jackson | 32.8 m (82 km/h) | 52.3 m (103 km/h) |
| v3297 Jackson/Lake Murray | 44.5 m (95 km/h) | 58.5 m (109 km/h) |
| min radius / min target speed (the hairpin) | 12.57 m / 50.6 km/h | 12.54 m / 50.5 km/h |
| points in an open box | 56 | 64 |
| start | point 0 on the start/finish line (0.0 m off it); grid 27.0 m behind | point 0 on it (0.0 m); grid 30.0 m behind |
| estimated lap | 281 s (0047 draft: 369 s) | 281 s (0047 draft: 350 s) |

For comparison the spec's estimates (largest constant-radius arc, approximate) were ~34 / ~35 / ~39 m
(cw) and ~52 / ~52 / ~55 m (acw); the 0047 drafts were floor-limited at 12.6 m (cw) and 10.3 m (acw) in
those corners. The clockwise arcs are smaller than its estimates at v1514 / v2319 because the
approach is not allowed to chase the 1:3.3 / 1:3.6 funnel faces outward: the first version did, and it
put a 58 km/h flick in front of an 88 km/h corner. An independent check of both files against the
per-vertex declaration (not the writer's faces) found 0 violations, the nearest declared face 1.67 m
(cw) / 1.58 m (acw) away from the corners and the nearest declared inside corner X 1.91 / 1.93 m (strip
centre) away. The street draft is byte-identical to today's. These are still **GENERATED DRAFTS**: ledger
0023 stays open, no tier is claimed, `pit_lane.ai` is still a copy, and whether the AI laps is decided in
game.

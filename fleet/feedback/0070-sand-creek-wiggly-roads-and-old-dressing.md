---
id: 0070
title: "Sand Creek's roads are wiggly and messy: a Google line, junction flares at way splits, paint that follows them; the barriers render wrong; no new lamps, no textured kerbs"
status: open
scope: tracks/sand-creek (proof, 0.31.1). Engine parts reach every osm_road_widths track (Sand Creek, Lookout Lariat), every road_markings "lane" track (+ the tarmac rally stages) and every prepped 1WALL object outside the planar-UV skip list
layer: engine + project + authoring (routed per fix below)
train: -
---

## Symptom (Kevin, 2026-11-03, after driving Sand Creek 0.31.0)

> "i think the sand creek roads are a bit wiggly w/r/t lines and curves/edges, they're not realistic and messy"

> "also it seems to use some ugly barriers that render wrong, doesn't have the new lights or textured curbing. this may be handled in some of the current work"

The first concrete part of Nov 1's (ledger 0063):

> "is our assets tool building 3d trees or 2d? i'm seeing 2d on sand creek which needs a lot of work in general"

Read as four defects, kept apart below: **A** the line wiggles, **B** the edges and the paint wiggle, **C** the barriers render wrong, **D** the dressing is the old set (no lamps, no kerbs). A and B are both "wiggly", but they have different causes and different fixes.

## How it was measured

Everything is on branch `claude/sand-creek-camber` (0.31.1), offline on the Mac. No build was installed or regenerated.

- Lines: `data/centerline.local.json` is the draft (9,697 m, ENU). `data/finished_centerline.json` is the swept line (9,674 m, kn5 frame, so north = −z). Both have 3,231 vertices, 3 m apart.
- OSM: `data/osm.widths.cache.json`, 1,571 ways.
- The KML: `source/Sand Creek Raceway Drive-3.kml`.
- Projection: `scripts.geometry.projection._meters_per_degree(origin lat)`, with origin 39.786449 N, −104.922793 E. That gives 85,659 m per degree east and 111,031 m per degree north.
- Stations: on the swept line, unless a number says "draft".
- Pictures are in `tracks/sand-creek/source/feedback-0070/`:

| file | what it shows |
|---|---|
| `line_wiggle_vs_station.png` | zig-zag along the lap (draft, swept, OSM), and the offset from OSM with the KML vertices marked |
| `straightened_sand_creek_dr.png` | Sand Creek Dr S, 2,700–4,400 m, laterals against OSM (no flares here) |
| `width_vs_station.png` | pavement width, pre-flare width and edge-line width; every flare classified |
| `topdown_colorado_50th_ash.png` | the 90° corners at 380–720 m, true scale |
| `topdown_quebec_to_e45th.png` | 5,880–6,330 m, true scale |
| `topdown_e46th_ave.png` | 8,980–9,420 m, true scale |

**Zig-zag** is the metric used for line wiggle. Over a 30 m window, take the sum of |heading change| and subtract |net heading change|. It is 0 on a straight or a clean arc. It is positive only where the line turns one way and then back.

## A. The line wiggles

### Evidence

**What the line is made of.**
- The line is Google Maps' Directions polyline, not OSM. `track.config.json` `source.type kml` sends the gps stage to `scripts/gps/centerline.py:382` `centerline_from_kml`. That function linearly resamples the KML's longest LineString to 3 m (`:427`). Nothing in the chain snaps it to OSM: `widths_from_osm` map-matches only to choose widths and never moves a point.
- The KML has 453 vertices. They are a median 13.7 m apart (p95 62 m, max 341 m).
- The coordinates have at most 5 decimals. 1e-5° is 0.86 m east and 1.11 m north, so each vertex carries up to ±0.43 m / ±0.56 m of rounding.
- The first and last vertex are 4.1 m apart. The ring closes with a chord.
- The KML vertices sit 0.64 m from the OSM way centreline at the median, 2.8 m at p95 and 4.2 m at worst. The swept line sits 0.60 m / 2.56 m / 4.7 m from it.

**Where the line turns.**
- The line turns at Google's vertices. The median vertex turn is 2.7°; 133 vertices turn by more than 5° and 67 by more than 10°.
- 93 % of the draft line's turning (sum of |heading change|) happens within ±3 m of a KML vertex. Those stretches are only 36 % of its length.
- Jogs are opposite kinks 20–30 m apart, each one a 0.5–1 m sideways step. Examples: 2,010/2,030, 4,293/4,315, 4,931/4,955, 5,237/5,265/5,289 and 9,610/9,632 (draft stations).

**The smoothing does not remove it.**
- `scripts/geometry/build_mesh.py:349` `smooth_centerline` (λ 0.45, 4 passes) keeps 44 % of a 20 m wobble, 70 % of 30 m, 82 % of 40 m and 97 % of 100 m.
- After it, the swept line still has 74 % of its turning at the KML vertices. The draft and the swept line differ by 0.12 m at p95 (3.5 m max at the corners).

**Zig-zag p95, per 30 m.**

| line | p95 |
|---|---|
| draft | 13.1° |
| swept | 5.2° |
| the OSM way under it | 0.78° |

**Worst 100 m windows, by the swept line's mean zig-zag.** The seam at 9,625 is left out because OSM is as bad there.

| from (m) | swept | draft | OSM | where |
|---|---|---|---|---|
| 6,175 | 12.3 | 29.4 | 0.0 | Quebec → E 45th (`primary_link`) |
| 5,850 | 8.6 | 16.5 | 13.0 | Sand Creek Dr → Quebec |
| 8,000 | 7.3 | 20.4 | 0.9 | E 45th North Dr |
| 6,075 | 6.5 | 13.1 | 0.4 | Quebec |
| 5,975 | 4.2 | 7.3 | 0.3 | Quebec |
| 8,650 | 3.6 | 8.1 | 0.1 | E 46th |
| 2,825 | 2.9 | 9.1 | 0.0 | Sand Creek Dr |
| 2,500 | 2.6 | 21.1 | 0.0 | the 56th → Sand Creek Dr ramp, ledger 0066's camber corner |
| 4,025 | 2.6 | 4.3 | 0.0 | Sand Creek Dr |
| 9,375 | 2.6 | 6.2 | 0.0 | E 46th Ave Access |

**Curves are polygons.**
- Five 90° street corners are made of one or two Google vertices: 416–486, 556–628, 1,234–1,306, 2,340–2,414 and 9,610–9,668.
- `round_sharp_corners` (`build_mesh.py:376`, kinks over 28°) leaves each one as a 24–26° per 3 m apex, which is a radius of about 7 m. That apex is under a road flared to 20–42 m wide (B).
- Longer curves turn in lumps: there is more than one curvature peak per corner at 628–723 (four), 2,549–2,635 (two), 5,842–5,909 (two), 6,167–6,235 (three plus two) and 9,227–9,296 (three).

### Diagnosis

The geometry comes from Google's simplified route polyline, used as coordinates. LAWS L1 allows KML "*only* where the intended route deliberately leaves the real road network", and Sand Creek's never does: every station matches an OSM way within 4.7 m. The route choice is real; the coordinates should be OSM's.

The engine then treats the result as GPS noise. The Laplacian smoothing, the 28° corner rounding and the >120° junction fillet are downstream compensation for an upstream polygon: they spread each kink over ±10 m and remove none of the jogs.

## B. The edges and the paint wiggle

### Evidence

**The width profile.**
- `widths_m` runs from 5.5 to 42.3 m (median 11, p95 21.0). 613 vertices are flared: 1,839 m, 19 % of the lap.
- `widths_base_m` (the street before flares) runs from 5.5 to 23.5 m.
- Width changes at up to 4.46 m per m (p95 0.43, p99 1.36). 284 vertices change faster than the 0.25 m/m that `projection.slew_limit_widths` was written to cap. Sand Creek does not set `route.width_slew_m_per_m`, and neither does any other track, so that limiter is off.

**There are 52 flare events. 48 of the 62 "junctions" behind them are not junctions.**
- `scripts/gps/widths_from_osm.py:278` `detect_junctions` flares the road at any OSM node within 16 m where two ways of class tertiary or above meet. It counts **ways**, not roads.
- OSM splits one street into two ways wherever a tag changes, at every bridge end and at every side street. `detect_turn_corners` was already fixed for exactly this (`:339-343`: "Same name/ref continuing = one road", which came from the Lariat's switchbacks).

Of the 62 nodes:

| what is at the node | count | stations |
|---|---|---|
| a real junction of two arterials | 14 | |
| a minor side street on one arterial | 17 | e.g. E 46th at 9,125 and 9,176 |
| nothing: OSM only splits the street | 31 | e.g. 9,245; 6 at bridge ends (2,399 / 2,444 on E 56th, 5,900 / 5,999 on Quebec, 6,507 / 6,561 on E 45th); 3 are the crossing road's own split at a real junction (7,006, 7,812, 8,635) |

- The function's own docstring rules out the minor-street case ("NOT every minor residential T-junction").
- Each flare is +3 m, which is 1.5 m per side over a 7 m taper (`flare_widths` `blend_m`), about a 12° kink in each edge. On a 7.5 m street (E 46th, 9,116–9,320) that is a 40 % bulge every 50–70 m.
- `detect_turn_corners` adds 7 corner flares of 18–42.3 m: 32.9 m at Colorado → 50th, 42.3 m at Dahlia → 56th, 34.2 m at Sand Creek Dr → Quebec.
- Each of those is a ribbon swept around the R ≈ 7 m apex from A. The ribbon's pleat guard (`ribbon.py:62` `_cap_offset`) is engaged at 23 vertices, all at those corners: 0–3, 448–457, 593–596, 1,270–1,274, 2,375–2,385, 5,872–5,877 and 9,646–9,671. `topdown_colorado_50th_ash.png` shows the torn inside corners.

**Street widths step with OSM `lanes` tags.**
- There are 25 base-width transitions, each ramped over 23–27 m by `_smooth(9)` (`:270`).
- Sand Creek Dr, 5,381–5,839 m: 11 → 14.5 → 11 → 14.5 → 18 → 14.5 → 18. That is seven steps in 460 m.
- E 45th, 6,369–7,767: 16.5 → 8.5 → 12 → 15.5 → 19.
- E 46th steps between 7.5 and 11 m.
- The two `primary_link` slips run one lane plus 2 m: 56th → Sand Creek Dr (2,507–2,623, 23.5 → 5.5 → 23 m) and Quebec → 45th (6,164–6,291). Both are inside corners.

**The paint follows every one of these.**
- *Edge lines.* `build_mesh.py:1510-1516` ("EDGE LINES FOLLOW THE LANE ... flare pavement stays OUTSIDE the stripe") takes a 9-vertex (27 m) rolling median of `widths_m`, then the min with the pavement. Every flare here is 18–76 m long (6–25 vertices), so the median passes it through. The stripe is never more than 0.5 m inside the pavement anywhere on the lap. All 52 flares bulge the white edge lines, by 1.3–15.6 m per side.
- *The street's own line goes unused.* `widths_base_m` is what `widths_from_osm` writes as "the street's own line" (`:470`), and `build_mesh` never reads it. Ledger 0001 found the same unused value.
- *Lane dividers.* `ribbon.py:975-977` `lane_markings` derives the lane count from width, at 3.65 m per lane. OSM widths add a 3–6 m class allowance to `lanes × 3.5`, and that allowance paints as a phantom lane each side.
  - Of the 2,869 stations with a `lanes` tag, 100 % are painted with more lanes than OSM says, usually +2.
  - Dahlia (2 lanes) is painted 4–12. Quebec (3) is painted 6–10. E 56th (5) is painted 8–12.
  - A dashed divider starts or stops 75 times a lap, 71 of them at a flare.
- *No pleat guard on the paint.* `lane_markings` has no `_cap_offset`. At 17 vertices on those same corners, the inside edge line's offset exceeds the local radius, so the painted line folds over itself.
- *The yellow line* is the centreline, so it carries every kink from A one to one. It is in the street kn5, so it shows only in Free Roam.

### Diagnosis

Two engine defects: `detect_junctions` counts OSM ways instead of distinct roads, and the markings are keyed to the pavement width instead of the street. They sit under a stack of compensation, each layer added to soften the one before:

- the `_match_per_vertex` de-jitter and `_smooth(9)`;
- `flare_widths` only ever widening;
- `slew_limit_widths` (opt-in, off);
- the 27 m rolling median for the edge lines;
- `instance_barriers`' "max width over the module's span";
- the barrier proximity trim ("flare tapers pull a handful of modules tighter");
- drive_test's flare exemption keyed to the lap's median width.

The corner flares are REALISM §8's "junction whack-a-mole in engine code": a 42 m ribbon swept along a centreline is not an intersection.

## C. The barriers render wrong

### Evidence

**What is in the build.** `data/split_manifest.json` lists 272 objects. The walls are:
- `1WALL_barrier`: Kevin's 4 m module, `assets/models/concrete_barrier_4m.obj`, instanced by `scripts/environment/props.py:48` `instance_barriers` because `props.concrete_barriers: true`;
- `1WALL_PARA_stone`: the stone-lip guards from `build_mesh`;
- `1WALL_TILTUP_0`: the buildings' collider.

`scripts/ac/pbr.py:106` binds `1WALL_barrier` to the same texture as Lake Murray's K-rail (`concrete_barrier_diffuse.png` + normal). The texture is not the difference. The geometry and the UVs are.

**1. Half the faces wind inward.**
- `instance_barriers` stamps every face twice, once in each winding, on the **same** vertices (`props.py:132-136`, "DOUBLE-SIDED stamping ... 'some barriers are still inside out' survived two winding fixes").
- The underlay then imports the OBJ with `me.validate()` (`scripts/blender/underlay.py:223`). Blender deletes any face that uses the same vertices as another ("Face 2 is a duplicate of 0"; tried here on Blender 5.1.2).
- The PC's own report shows it happened there too. `data/underlay.report.json`, Blender 4.2.22: `1WALL_barrier` has 13,393 vertices and 26,488 faces. That is about 54 modules at 493 triangles each, which is single-sided. Double-sided would be about 53,000.
- Which copy of each face survives is effectively arbitrary. Through the same `instance_barriers` → `underlay.group_to_mesh` → `validate` path, a 3-module run kept 639 of 1,479 faces pointing into the barrier on one side of the road and 837 on the other. Checked against the module's own authored normals, all 183 of which agree with its winding.
- The prep's 1WALL repair (`scripts/ac/build_kn5_loop.py:1007-1026`, consensus flip) flips only 81 of them, so 642 and 834 remain.
- From any one viewpoint about half of every module is back-face culled: see-through, patchy concrete.
- `underlay.py:49-51` says "the prep does [double the faces], at prep time, on the same names". It does not for scene objects. `DOUBLE_SIDE` (`build_kn5_loop.py:59`) is used only in `_add_obj_meshes` (`:523`), the merged-OBJ path.

**2. The prep re-projects its UVs from above.** `build_kn5_loop.py:991-995` calls `planar_uv` (u = x / 4 m, v = y / 4 m) on every mesh not in a skip list. The list includes `1WALL_RACE`, `1WALL_TILTUP`, `1WALL_TECPRO` and `1WALL_KRAILBW`, but not `1WALL_barrier` or `1WALL_PARA`. Every vertical face therefore takes one texel column from top to bottom, and the concrete smears into vertical streaks. The stone lips (`stone_tan.png`) get the same treatment.

**3. The module's UV seams are collapsed before that.** `props.load_module` (`props.py:20-45`) keeps "last-seen vt per vertex". The module has 439 UVs on 249 vertices: 159 vertices carry more than one, and 141 of the 183 faces touch a seam. This is moot while (2) overwrites everything, and it shows the moment (2) is fixed.

**4. Some modules are partly cut.** The proximity trim (`build_mesh.py:2926-2955`) deletes any barrier triangle within 1 m of the carriageway. 13,393 vertices is not a multiple of 249, so at least one module is cut open.

**Lake Murray does none of this.** Its race K-rail is authored in Blender by `tools/author_race_furniture_blend.py`:
- `1WALL_race_*` strips swept along a declared corridor, `u = arc / 4.04 m`;
- skipped by `planar_uv` and by the weld;
- wound once, consistently, with the remap's reflection accounted for (`tools/race_furniture.py:7`), not by duplicate faces on shared vertices.

Its stub barriers are `1WALL_STUB`, the same strip, from `tools/author_stubs_blend.py`.

### Diagnosis

Three engine defects stack: a double-sided stamp that the underlay's `validate()` silently halves, a prep UV pass that does not know the module, and a loader that drops UV seams. The game evidence ("render wrong") is consistent with (1) and (2). Which barrier Kevin saw is not yet tied to a station: see Verification.

## D. The dressing is the old set

**What Sand Creek has.** `ship.json` runs, in authoring, only `layout_dummies` and `bespoke` (440 buildings). The prepped scene has:
- no `LIGHTPOST`, `LIGHTS`, `LAMP*`, `SIGN*` or `1KERB*` object;
- no race furniture (`race_objects: []`);
- no CSP streetlight either: there is no `data/lights.local.json`, and `scripts/ac/ext_config.py`'s light series keys on a `LIGHTS` mesh that does not exist.

**Config that nothing in the chain reads:**
- `scenery.lamp_model "street_lamp_new.obj"`, `scenery.light_spacing_m 96`, `lighting.streetlight` and `scenery.signs`. These are `scripts/environment/build_env.py`'s pre-chain keys, and build_env is never a draft step (V3-PLAN P2 step 6).
- `kerb {height_m 0.05, width_m 1.4, ...}`. The `street_circuit` archetype sets `kerb.enabled: false` (`scripts/config.py:77-78`).
- The phone capture's `1KERB` and `BARRIER` texture overrides (`source/realworld_capture.json`). There is no 1KERB object, and `1WALL_barrier` matches the `1WALL` key, not `BARRIER`.

**Kerbs today.** The road edge is `road_edge.profile "shoulder"`: Kevin, 2026-07-26: "I do want sand creek to have no sidewalks". So Sand Creek has no curb and no race kerb anywhere.

**What Lake Murray's chain has that Sand Creek's lacks:**

| Lake Murray step / tool | what it makes | Sand Creek can use it today? |
|---|---|---|
| `draft_lamps`: `tools/author_lamps_blend.py`, model `led_cobra` from `tools/make_streetlight_led.py`, `tools/check_lights_ini.py` | the 0056 LED cobra-head lamps, one CSP light per lens | **No.** The post plan `data/lights.local.json` is written only by `tracks/san-diego-lake-murray/scripts-v021/geometry/streetlights.py` (quarantined). An engine-draft track has no lamp planner. `led_cobra` is Caltrans ES-6A, San Diego's spec, not Commerce City's. |
| `author_signs`: `tools/author_signs_blend.py`, `tools/verify_signs.py`, `tools/plot_signs.py` (`tools/place_signs.py`) | W1-6 large-arrow signs at tight corners (0044, 0051) | Untested. It reads the built mesh, but it has only ever run on Lake Murray. |
| `race_bands`, `race_planned_gate`, `race_author`, `race_verify`: `tools/barrier_bands.py`, `tools/author_race_furniture_blend.py`, `tools/verify_race.py`; ship `export_race`; gates `race_gates`, `race_scenery_gate` | race K-rail (`1WALL_RACE`), closures, and the worn race kerbs (`1KERB_RACE`, the 0053 atlas from `tools/make_kerb_texture.py`) | Only with a race corridor declared (ledger 0049) and `layouts[race].race_furniture: true`. Sand Creek has neither. |
| `pads_plan` / `pads`: `tools/junction_pad.py`, `tools/author_junction_pad_blend.py` | one authored deck per crossroads with curb returns: the authored answer to B's flares | Not as built. It needs a pads declaration, and every pad carries a `1KERB_sidewalk_pad<id>` curb and walk (the header, `:16`), which Sand Creek's shoulder edge does not have. |
| `weld_mouths`, `gap_mouths`, `aprons`, `stubs`, `median` | side-street mouths, curb gaps, corner aprons, stubs, islands | scripts-v021 assembler steps, sidewalk-based: n/a while Sand Creek keeps `shoulder` |
| `bridges`: `tools/author_bridges_blend.py` | bridge bodies under the overcrossings | 0068 is authoring the E 56th deck now |

## Scope

- **A (line):** Sand Creek only. It is the only `source.type kml` track.
  - Regression cases: every `osm`, `from_track` and `aerial` source, untouched.
- **B (flares, markings):** flares on `osm_road_widths: true`, which is Sand Creek and Lookout Lariat. Markings on every `road_markings.style "lane"` track: Sand Creek, the Lariat, and the two tarmac rally stages.
  - Regression cases: the Lariat's `measured_widths` reads `widths_base_m` (pre-flare), so its `widths_m` must stay byte-identical. The rally stages have no OSM widths, so they must keep width-derived lanes as the fallback and stay byte-identical.
- **C (barriers):** `props.concrete_barriers` is Sand Creek only. The planar-UV skip list is fleet-wide.
  - `1WALL_PARA` comes from any engine draft with measured guards.
  - `1WALL_CHAINL` (Exotics, High Plains, Milford) is also planar-UV'd by the same list. That is unverified as a defect and not reported by Kevin: check it, do not claim it.
  - Regression case: Lake Murray's `1WALL_RACE` / `1WALL_STUB` / `1WALL_guard` must stay byte-identical.
- **D (dressing):** Sand Creek. A lamp planner for engine-draft tracks would serve every street track after it.

## Fix: routed, with what each touches

| # | Fix | Layer | Files | PC? | Collides with |
|---|---|---|---|---|---|
| **C1** | Stamp barriers single-sided with the winding corrected per placement. The placement map is a reflection for `side = +1`. Or give the back faces their own vertices, as the foliage does. Fix the underlay comment. Split vertices per (v, vt) in `load_module`. Add `1WALL_BARRIER` and `1WALL_PARA` to the `planar_uv` skip list. | engine | `scripts/environment/props.py:20-45, :48-137`; `scripts/ac/build_kn5_loop.py:991-995`; `scripts/blender/underlay.py:49-51`; a test in `tests/` | Mac for code and test. PC for the underlay, prep, export and stills. | Nothing on the line. Prep changes reach every track: Lake Murray's skip-listed objects are the regression check. |
| **B1** | `detect_junctions` keeps a node only where two **distinct** arterial roads meet: `detect_turn_corners`' identity test, plus excluding minor side streets per its own docstring. This drops 48 of the 62 flares. | engine | `scripts/gps/widths_from_osm.py:278-309` | Mac (A/B: widths → build_mesh → drive_test, as 0066 did) | None. Widths only, so the station frame is unchanged. |
| **B2** | Paint follows the street. Edge lines from `widths_base_m`, smoothed. Lane count from OSM `lanes` per vertex (written by `widths_from_osm` next to `widths_base_m`), with width-derived lanes as the fallback when there is no tag. `_cap_offset` on every marking offset. Delete the 27 m rolling median (`build_mesh.py:1510-1516`), which is the compensation. | engine | `scripts/gps/widths_from_osm.py`, `scripts/geometry/build_mesh.py:1509-1530`, `scripts/geometry/ribbon.py:875-978` | Mac | 0063's yellow-line rule, which keeps `center_yellow` and the street kn5. |
| **B3** | Width changes ramp at a declared rate: `route.width_slew_m_per_m: 0.25` (`slew_limit_widths`' own default, written for Lake Murray's College Ave). This is the interim for the 14 real junctions and the 7 corner flares. | project | `tracks/sand-creek/track.config.json` | Mac | None |
| **A1** | Re-source the line from OSM. The KML still chooses the roads, and OSM gives the coordinates (L1). Feed the KML route through `scripts/gps/mapmatch.py` as the "drive", via a small adapter in `centerline_from_kml` behind an opt-in `source.snap: "osm"`, so it picks the ways and stitches their geometry, slips included. Then refit it as one curvature-continuous line (as `tools/paint_centreline.py` step 3 does for the Lariat), with real curb-return radii at the five 90° corners instead of R ≈ 7 m. Re-derive every station and vertex the config holds with `tools/remap_centreline_config.py`: `layouts[].start` (2805/2795, sectors 655/1730), `capture.bridges` (2,485 / 5,950 / 6,549), `road_profile.crossfall.spans_m` [[2540, 2740]] plus a `tools/lidar_crossfall.py` rerun (its cache is keyed to the line). | engine (adapter) + project (source, config) | `scripts/gps/centerline.py:382-447`, `scripts/gps/mapmatch.py`, `tracks/sand-creek/track.config.json`, `data/crossfall.json` | Mac for the draft. PC for the chain and the drive. | **0068's E 45th nudge** (6,300–6,500 m) moves the same line: on an OSM line it must be re-derived as a declared offset, not carried over. **0066's camber span** is keyed to stations on this line. 0069: none. |
| **D1** | A lamp planner for engine-draft tracks: port `scripts-v021/geometry/streetlights.py`'s spacing and clearance rules to an airoso tool that writes `data/lights.local.json`. Then `draft_lamps`, `tools/author_lamps_blend.py`, `tools/check_lights_ini.py`. The model needs the place's research: Commerce City / Adams County arterial fixtures, in a location dossier. Retire the dead `build_env` keys. | engine tool + project + authoring | new `tools/plan_streetlights.py` (or similar), `tracks/sand-creek/ship.json` (`steps.draft` += `lamps`), `track.config.json` `scenery.streetlights` | PC (Blender) | `ship.json` steps. 0068 authors in the same `loop.blend`, so AUTH_ collections must not collide. |
| **D2** | Kerbs, per Kevin's decision below. Race kerbs need a race corridor declaration (ledger 0049) and `race_furniture: true`, then the `race_*` author steps and the `export_race` / `race_gates` ship and gate steps. That also brings Lake Murray's K-rail, which can replace C's instanced modules. | project + authoring | `track.config.json` (`race.corridor`, `race.kerbs`), `ship.json` steps | PC | A1. Corridors are declared by vertex, so they go after the line is final. |
| **D3** | Signs: `author_signs` (W1-6 at tight corners). | authoring | `ship.json` (`steps.author` += `signs`) | PC | A1, since the corners move with the line |

## Proposed order

1. **C1.** Independent of the line, small, and the most visible fault. Mac code and test, then one PC chain.
2. **B1 + B2 (+ B3).** Widths and paint only, so the station frame, 0066's camber and 0068's nudge are untouched. Mac A/B first.
3. **A1**, after 0068 lands, absorbing its nudge as a declared offset on the OSM line, or with Kevin's word to let the OSM line replace it. One `remap_centreline_config` pass carries every station.
4. **D1 → D3 → D2** on the final line, on the PC.

**What the current work covers.**
- 0068 moves ~200 m of the line by ~1.5 m on E 45th (6,300–6,500 m). It is the same mechanism as A, the Google line not being on the road, and fixes that stretch only. It touches none of B, C or D.
- 0069 (Milford), 0066 (camber at one corner) and 0067 (terrain mirror, on main) touch none of A–D.
- So: **none of this is covered by current work.**

## Verification (decided before the fix)

- **A:**
  - Swept-line zig-zag p95 ≤ 1.0° per 30 m. Now 5.2°; OSM reads 0.78°.
  - |swept − OSM centre| ≤ 1.5 m outside declared offsets. Now 4.7 m max, 2.56 m p95.
  - At the five 90° corners, minimum radius ≥ the declared curb-return radius, and `_cap_offset` engaged at 0 vertices (now 23).
  - Stills at 2,825, 6,175 and 8,000 m.
- **B:**
  - Flares only at the 14 two-arterial junctions plus the declared corners; 0 at the 31 way splits and 17 minor streets listed by `width_vs_station.png`.
  - Edge-line offset steady within 0.1 m through every non-junction flare site.
  - Painted lanes = OSM `lanes` wherever tagged (now 0 of 2,869 stations match).
  - Dashed dividers start or stop only where OSM's lane count changes (now 75 a lap).
  - Paint pleats 0 (now 17).
  - Lookout Lariat and the tarmac rally stages: `widths_m` and the markings mesh byte-identical.
  - drive_test no worse than 0.31.1.
- **C:**
  - In the prepped scene, for every `1WALL_barrier` module: faces = 493 × sides, 0 faces whose normal opposes the module's authored normal, side-face UVs not equal to the planar projection, and no module partly cut.
  - Lake Murray's `1WALL_RACE` / `1WALL_STUB` byte-identical.
  - The same CSP free-camera stills of two barrier runs, before and after, then Kevin's look.
- **D:**
  - Lamp count = planned posts, `check_lights_ini.py` PASS (one [LIGHT_N] per lens), no pole on a road or within 0.5 m of a wall.
  - Kerbs as decided, `verify_race` PASS.
  - Kevin's drive is the verdict.

## Needs Kevin's decision

1. **"Textured curbing"**: worn race kerbs at Sand Creek's race corners (needs a race corridor; also brings the Lake Murray K-rail), or concrete street curbs (reverses "no sidewalks", 2026-07-26), or both?
2. **The line**: re-source from OSM (L1; it moves every station, absorbs or replaces 0068's E 45th nudge, and re-keys the 0066 camber), or keep Google's route and only smooth it?
3. **The junction corners** (42 m at Dahlia → 56th, 34 m at Sand Creek Dr → Quebec, 33 m at Colorado → 50th): keep engine flares slew-limited (B3), or author junction pads in Blender as Lake Murray does?
4. **Lamps**: which fixture? Commerce City's real one, researched, or Lake Murray's `led_cobra` as a stand-in?

## Fixed (B1, B2): Sand Creek 0.34.0, built and gated on the PC, NOT installed (2026-11-03)

**What changed (engine).**
- **B1.** `widths_from_osm.detect_junctions` keeps a node only where the arterial ways there carry two or more distinct road identities. `road_ident` is `detect_turn_corners`' name / ref / way test, now shared by both. Minor side streets were already outside `MAJOR`.
- **B2.**
  - `widths_from_osm` writes `lanes_osm` (the way's OSM `lanes`, None where untagged) beside `widths_base_m`.
  - `build_mesh` paints the edge lines at `min(widths_base_m, widths_m)` and deletes the 27 m rolling median. With no `widths_base_m` (or a different count), the paint keeps the pavement width.
  - `ribbon.lane_markings` takes `lanes`: OSM `lanes // 2` lanes a side where tagged, the width-derived count where not. Every marking offset goes through `_cap_offset`.
- **Not touched:** `detect_turn_corners`, `width_slew_m_per_m`, any gate threshold.
- **Tests:**
  - `tests/gps/test_junctions_distinct_roads.py` (a bare way split, a minor side street, two distinct arterials, the identity);
  - `tests/geometry/test_paint_follows_street.py` (the untagged fallback equals the old output, OSM lanes set the dividers, a tight corner holds the lines 0.9 R out);
  - `tests/gps tests/geometry`: 243 pass.

**Verification B, 0.33.0 → 0.34.0** (measured on each build's own workshop data; the same scratch tool both times):

| | 0.33.0 | 0.34.0 |
|---|---|---|
| Flared junction nodes (`detect_junctions`) | 64 | **14**: the 14 two-arterial junctions; 0 of the 32 way splits, 0 of the 18 minor side streets |
| Corner flares (`detect_turn_corners`, untouched) | 8 | 8 |
| Flared vertices | 616 | 214 |
| Edge line off the street at a flared vertex | 613 of 616, up to 15.65 m a side | **0 of 214** (max 0.00 m) |
| Painted lanes = OSM `lanes`, tagged stations | 0 of 2,892 | **2,892 of 2,892** (496 are one-lane tags: edge lines, no divider) |
| Dashed divider starts / stops per lap (one side) | 77 | **12**: 11 at an OSM lane-count change, 4 touching an untagged station (the width fallback) |
| Paint pleats (an offset past 0.9 R) | 20 | **0** |

**Regression proofs.**
- **Lookout Lariat:** `widths_m` is byte-identical: md5 `f9d184ebcd4f`, the same from the old engine, the new engine and the D4 A workshop. B1 cuts `widths_from_osm`'s raw junction flares there from 111 to 22, but `measured_widths` sets the final widths from `widths_base_m`. The only new key is `lanes_osm`.
- **Tarmac rally stages' markings mesh:** byte-identical.
  - `rally-dragon-tail-tarmac`: white `d655a233dba6`, yellow `b115d679ddf0`.
  - `rally-under-the-dragon-tarmac`: white `4318d945a25c`, yellow `9b2107e67c79`.

**The barrier trim (C, brief).** The lone barrier slab is gone with B1, so `instance_barriers` is not changed. Open barrier edges standing over the surface, 0.33.0 → 0.34.0:
- 0.33.0: 57 open edges, 29 standing more than 8 cm, one cluster at (−1485.8, 178.0) up to 1.26 m.
- 0.34.0: 18 open edges, none standing more than 8 cm (one between 2 and 8 cm).

**drive_test, 0.33.0 → 0.34.0** (race and street read the same): RED, so not installed. 0.33.0 stays in `sand_creek`.

| | 0.33.0 | 0.34.0 |
|---|---|---|
| severe steps | 0 | **8** |
| floating furniture | 0 | **1** |
| apron steps | 3 | **6** |
| bumps /km | 2.07 | 1.86 |
| slope kinks /km | 6.63 | 6.52 |
| vertex bumps | 6 | 3 |
| fold bumps | 20 | 20 |
| excursion drops / far ledges | 7 / 8 | 7 / 8 |
| obstruction, daylight, undrivable, soft top, barrier missing | 0 | 0 |

Both regressions are B1 removing a flare that had been hiding something the brief kept out of scope.

- **Severe 8, at 2,550–2,551 m:** 6.9–8.6 cm, on all four inner wheel paths (±1.86 m, ±3.36 m).
  - The 56th → Sand Creek Dr slip is a one-lane `primary_link` (base 5.5 m). `detect_turn_corners` flares its corner to 23.0 m from 2,522 to 2,546 m.
  - In 0.33.0 a way-split "junction" flare just past it (+3 m, 15.6 → 15.0 m at 2,552–2,570 m) stretched that corner flare's exit over about 30 m (22 → 15.6 → 11 m). B1 removes that way split, as it should.
  - The corner flare now drops 23 → 7.3 m in about 12 m: 21.7 → 7.8 m between the sections at 2,546 and 2,552 m.
  - That is exactly where ledger 0066's measured crossfall span begins (2,540–2,690 m): the tilt ramps 2.8 → 3.75 % across 2,541–2,553 m.
  - A rolled section 21.7 m wide meeting a differently rolled one 7.8 m wide 6 m later puts a crease of several centimetres across the road. 0.33.0 already showed it at reduced size: a 4.55 % kink at 2,551 m, 4.43 m left.
  - The centreline height is unchanged: 5.44 → 5.40 m in both builds.
- **Floating furniture 1:** `1WALL_PARA_stone` (a measured-guard stone lip) near 8,572 m, at engine (−746.8, −685.6), its foot 1.18 m over the ground (the rule is 0.8 m).
  - B1 drops a way-split flare there (21.0 → 17.5 m), so the road edge, and the lip with it, moves about 1.75 m inward over lower ground.
  - This is the failure class ledger 0076 fixes in the engine (Dragon Tail Gravel, PR 31, `lip_foot_reach`: a lip foot over a drop is pulled back until it stands).
- **Apron steps 3 → 6:** reported, not gated.

**Stills** (`tracks/sand-creek/source/feedback-0070/paint_0330_site{1,2,3}.png` vs `paint_0340_site{1,2,3}.png`), workbench obliques at the three worst 0.33.0 flare sites, the yellow centre line shown: (−902.0, 1102.6) 2,324 m, (−1494.4, −298.4) 9,604 m, (−777.0, 1197.9) 2,486 m.
- The edge lines hold the street through every flare, with the flare pavement outside them as an apron.
- The phantom dividers are gone.
- Where OSM steps from 4 lanes to 2 (site 3), the edge lines move in over `widths_base_m`'s own ~25 m ramp. That is the street's step, not a flare.

**What would let it install** (not done; the brief kept these out of 0.34.0):
- (a) the slip corner's exit: B3 (`route.width_slew_m_per_m`), or authored junction pads in place of the corner flares (decision 3 above);
- (b) ledger 0076's lip-foot fix (PR 31) merged under Sand Creek.
- Then one chain from `widths`.

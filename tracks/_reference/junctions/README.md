# Junction pattern library

Reference geometry cropped from three professional AC tracks during the 2026-08-19 junction
dissections. This is the study material behind **`docs/JUNCTIONS.md`** — read that first; this
index tells you which file demonstrates which rule.

All OBJs are in **world coordinates, y-up**, extracted with `scripts/modkit/extract_kn5` and
cropped to the studied junction box. Object names and materials are preserved, so importing into
Blender (File → Import → Wavefront, "Split by Object" on) gives you the pros' actual layer
structure: select by material/object to isolate pavement vs curbs vs markings vs physics.
`_physics`/`_phys` files are the **invisible collision meshes** (in-game they are never rendered);
everything else is the visual skin. PNGs are top-down plan renders, material-colored, for
orientation before opening Blender. Total: ~1.9 MB. Source tracks in
`D:/SteamLibrary/steamapps/common/assettocorsa/content/tracks/` (read-only).

---

## rt_macau/ — Guia Circuit (Reboot Team). Urban street junctions: real 200 mm curbs, sidewalks, paint overlays

The **ribbon-through** topology: the racing ribbon is never broken; side streets butt-weld onto
its edge vertices. JUNCTIONS.md rules R2(a), R3, R9–R12, R14, R18(b)(c).

| File | Junction | What to look at |
|---|---|---|
| `crop_siteA_reservoir_-767_722_visual.obj` | Reservoir crossroads, two side-street mouths (one open, one barriered), 60×60 m | Side-street pavement (TRACKSURFACEOFFROAD_3) butt-welded to the unbroken main ribbon; curb strips (KERBS_1) wrapping corner-return arcs R 0.8–5.6 m and terminating at the road edge; sidewalk plates (PAVINGSTONES_1) at +195–200 mm following behind; the raised traffic island standing ON continuous pavement; ROADLINES_1 paint floated +20 mm |
| `crop_siteA_reservoir_-767_722_physics.obj` | same | The 0.82 m invisible physics ribbon running through unchanged; the coarse `1ROAD_EXT_0434` cap at the open mouth (9 tris, 2–6.5 m deep); the invisible 1WALL detouring around the cap but running straight across the barriered mouth |
| `crop_siteB_sanfran_-108_142_visual.obj` | San-Francisco-Hill crossroads, both mouths barriered (pure scenery), 60×60 m | Full curb returns on all four corners (clean fits R=1.4 and R=5.0 m) even though nothing drives there; return segmentation ~0.18 m vs ~2.3 m on straights; side streets modeled 25–30 m deep |
| `crop_siteB_sanfran_-108_142_physics.obj` | same | The set-dressing recipe: NO side-street physics at all, 1WALL dead straight across both mouths — the physics corridor ignores the junction entirely |
| `crop_siteC_fisherman_-1205_875_visual.obj` | Fisherman's-Bend 90° corner with zebra crosswalk, 90×90 m | Zebra bars as individual quads (0.5–1.2 × 3.1–3.5 m) in the paint mesh; the 45–50 mm orange racing kerb (KERBS_1.001) vs the 200 mm street curbs; TRACKEDGESTRANS grime strips ~0.13 m along road-edge seams |
| `crop_siteC_fisherman_-1205_875_physics.obj` | same | The physics fan around a 90° corner holding the 0.83 m grid; the ONLY collidable kerb — the racing kerb's invisible 1KERB twin; physics pavement extending beyond the wall line (collidable apron) |
| `render_siteA…/_phys/_walls.png` (×3 each site) | all three | Plan views: visual materials / physics coverage / wall routing. Start here to orient before importing the OBJs |

## union_island/ — 33.5 km road network. The junction-pad topology, shoulders, junction gutters, decals, marking vocabulary

The **welded pad** topology at paved-paved junctions, plus the cheap minor-mouth patterns.
JUNCTIONS.md rules R1–R5, R8, R9, R13, R15, R16, R18(a), R21.

| File | Junction | What to look at |
|---|---|---|
| `snippet_J1_visual.obj` | Ashton village paved T (7.5 m × 8.3 m streets) | THE pad exemplar: both ribbons cut at the junction limits, one pad mesh filling the T with a semi-radial fan; corner fillets as true arcs R=5.62/6.53 m, verts every 0.6–0.8 m; the 0.55–0.7 m shoulder strip (`road_edge`) routed continuously AROUND both fillet arcs into the side street — welded to the asphalt at 0.000 m, never crossing it |
| `snippet_J1_markings.obj` | same | Dash lines bending through the junction; one-way text stencil at the mouth; the two 1.0 m-wide `1KERB_road_junction` gutter strips slit into the pad seams (collidable — the audible junction-limit cue) |
| `snippet_J1_physics.obj` | same | The dedicated per-place physics chunk `1ROAD_ashton_cross` (0.60 m grid, ~1.6× denser than the 0.95 m approach); straight transverse seam vertex-welded at 0.000 m |
| `snippet_J2_visual.obj` | dirt/paved crossroad east of Clifton | The stacked wear-decal pair (`dirt crossroad02/03` at +26.8/+30.8 mm, 3.9 mm apart): exact clones of the pavement triangles with a tire-fan alpha texture — how a crossing movement is dressed without any pavement geometry |
| `snippet_J2_dirt.obj` | same | The dirt ribbon as two stubs terminating AT the paved road's shoulder line — zero crossing of the pavement; the loose (81 mm) butt joint hidden under the continuous shoulder + underlap mesh |
| `snippet_J5_visual.obj` | Ashton minor T + Y-merge pair | The cheap minor-mouth pattern: side street butts to within 0.7 m of the major's edge, no pad, no fillets; the `road_crack` worn-asphalt junction-zone material change on the major; shoulder omitted where village frontage owns the edge |
| `snippet_J5_markings.obj` | same | Give-way bar 0.4 × 3.0 m placed 1.2 m before the major's edge; solid center line replacing dashes for the last ~9 m of approach |
| `plan_J1_markings.png`, `plan_phys_j1.png`, `plan_J2_dirt.png`, `plan_J5_markings.png`, `plan_ashton_overview.png` | all | Plan views of the above, plus the whole-village overview showing how pads, minor mouths and shoulders compose into a street network |

## ks_black_cat_county/ — Kunos rural network. Single-owner junction chunks, gores, layout closures

The Kunos discipline: junction interior in ONE chunk, bit-exact arm cuts, density identical to the
road, OFF shoulder strips that never cross pavement. JUNCTIONS.md rules R1, R3, R4, R6, R7, R17, R20.

| File | Junction | What to look at |
|---|---|---|
| `crop_J3_phys.obj` | 3-arm Y-merge at (457, 317) — the cleanest example | One owner chunk (`16ROAD010`) holding fork + crotch + flares; three arms ending at straight lateral cuts 13–21 m out, each sharing 12–20 bit-exact verts; crotch tip rounded R≈1.1 m; OFF gore welded to both arm edges; junction grid 1.37 m vs arm 1.39 m — no densification |
| `crop_J3_vis.obj` | same | The visual twin: same welded construction ~3× coarser (4.0 m vs 1.4 m), EnvHI + EnvLOW LOD pair stacked on one footprint, sitting on the physics surface to +0.3 cm |
| `crop_J1_phys.obj` | 4-arm junction at (-238, -451) | Fork + through road + side arm all meeting one chunk; corner fillet R≈9.9 m onto the fast road; OFF strips hugging every fillet |
| `crop_J1_vis.obj` | same | Visual layer of the above |
| `crop_J4_phys.obj` | start-area double Y-split at (-282, 289) | Gore construction: 3.75 m wide at 6 m past the crotch tip growing ~7 cm/m; crotch R≈8.6 m; also Kunos' own defects — 3 thin unwelded interior slits mid-pavement (never at junction seams) — calibrates what a weld gate must tolerate |
| `crop_J4_vis.obj` | same | Visual layer incl. the asphalt-patch decal object |
| `crop_J4_layout1_strip.obj`, `crop_J4_layout2_strip.obj` | same | The per-layout closure paint strip, exact geometry: 10 verts / 8 tris, 0.374 m wide × 13–14 m, every vertex conformed to the road slope, floated +5–18 mm — repaints the double-yellow across a closed arm. The entire per-layout junction dressing is this + a 16-vert invisible wall + props |

---

*Numbers, methodology and caveats: `docs/JUNCTIONS.md` §2 and §5. Full uncropped extracts and the
analysis scripts (janalyze/jfillet/jmeasure/dissect_phys/objlib…) live in the session scratchpad
`junction-study/dissect-{0,1,2}/` — regenerate crops from there if these ever need widening.*

# JUNCTIONS — the junction construction standard

*2026-08-19. Written from three triangle-exact dissections of shipped professional kn5s:
**rt_macau** (Reboot Team Guia Circuit — urban street junctions with real curbs and sidewalks),
**union_island** (33.5 km freeroam road network — paved/paved and paved/dirt junctions), and
**ks_black_cat_county** (Kunos — rural forks, gores, layout splits). Snippet geometry from all
three lives in `tracks/_reference/junctions/` (see §5). This document answers the one question
`fleet/reference/MEASURED.md` and `docs/PRO-KN5-CONSTRUCTION.md` left open: how the pros build the
place where two roads meet. It does not re-derive what those docs establish (road grids 0.3–1.1 m,
physics/visual split, weld doctrine) — it applies them at the mouth.*

*Scope: this is the standard for **hand-authoring junctions in Blender** (V3 doctrine, REALISM §8:
the engine drafts and audits; the junction itself is authored once, per place). Every number below
was measured, not assumed.*

---

## 1. The failure we're fixing

Our engine sweeps each street as an independent ribbon with continuous curb+sidewalk strips down
both sides, so where streets meet the ribbons simply overlap and the sidewalks run straight through
the crossing pavement. Kevin has now hit this on every multi-street artifact and named it twice in
the ledger: [0033](../fleet/feedback/0033-junction-mouths-navajo-jackson-and-college-del-cerro.md)
(Navajo/Jackson "messy and undriveable"; College/Del Cerro "criss-crossing sidewalks running
THROUGH the street" — 1,096 kerb/sidewalk verts standing in the carriageway on the restored
artifact) and [0036](../fleet/feedback/0036-sidewalk-sweeps-vs-multi-street-networks.md) (the
systemic statement: "sidewalk generation currently makes multi-street networks impossible to
drive", with the three mechanisms — the sweep never stops at a mouth, the edges follow the
junction flare, and the audit check that sees it (K) doesn't gate). The measurements below show
that **no professional track contains a single instance of either defect**: across ~300k physics
road triangles and thirteen dissected junction sites on three tracks, pavement-over-pavement
overlap is zero and sidewalk/curb/shoulder-over-pavement is zero.

---

## 2. How the masters do it

### 2.0 Two junction topologies (and when to use each)

Every professional junction measured is one of two constructions — never overlapping ribbons:

**A. Ribbon-through** *(rt_macau, all three sites; union_island J2/J5 minor mouths)* — the priority
road's mesh runs through the junction **completely unchanged**, visual and physics both; the minor
street is a separate mesh that **butt-welds** onto the ribbon's existing edge vertices (a
*butt-weld*: the two meshes end against each other and share the exact same vertex positions along
the seam, so there is no gap and no overlap). Use when one road is clearly "the track" and the
other is a side-street mouth, driveway, or set dressing.

**B. Junction pad** *(union_island J1; ks_black_cat_county J1/J3/J4)* — every incoming ribbon is
cut short at a straight transverse edge, and the whole junction interior (crossing polygon, corner
fillets, crotch rounding) is filled by **one** pad mesh whose boundary vertices are
position-identical with the ribbon cut edges. Use for real drivable intersections where cars turn:
crossroads, T-junctions, forks, merges.

Both topologies share the same invariant, verified at every site: **the junction pavement is a
single-coverage surface** — every point in plan view is covered by exactly one road triangle.
Measured: rt_macau 0 overlapping tri centroids at 3 sites; union_island 0/651 at J1, 0/118 dirt
tris over asphalt at J2; BCC 0 m² multi-coverage at 4 junctions and only 3 centroids of 298,453
overlapping anywhere in the whole network (one legacy sliver seam).

### 2.1 Pavement

- **Seams are exact, and exactness is binary.** rt_macau: 12–25 exact vertex coincidences (≤1 mm)
  per mouth and **zero** near-misses (nothing between 1 mm and 5 cm) — weld discipline has no
  "close enough" band. union_island: pad↔ribbon nearest-vert median distance **0.0000 m**. BCC:
  arm cut rings share 5–28 **bit-exact** vertices with the junction chunk. (A *weld*: making two
  meshes share identical vertex positions along their common edge, so the surfaces are watertight;
  in Blender the arm's end *edge loop* — the ring of vertices across the cut — and the pad's mouth
  edge loop are literally the same vertices before the object is split.)
- **Arm cuts are straight and near.** BCC terminates arms at straight lateral cuts 13–21 m from
  junction center; union_island ends its pad 6–8 m beyond the crossing road's pavement edge (just
  past the fillet tangents). The whole junction interior lives inside **one chunk** (BCC junction
  owner meshes are ordinary: 466–621 verts / 817–1,162 tris).
- **Corner fillets are true circular arcs, part of the pad.** Measured radii: 0.8–1.5 m for
  small/service mouths (macau), 5.6–6.5 m for residential streets (union J1: R=6.53 fit residual
  32 mm, R=5.62 residual 25 mm, 13 points each at 0.6–0.8 m spacing ≈ 9°/segment; macau clean fits
  0.8/1.4/5.0 m), up to ~10 m where a side arm meets a fast through road (BCC J1: 9.9 m). Concave
  fork crotches are rounded too: R≈1.1 m for a tight V-merge, R≈8.6 m for a shallow highway split
  (BCC).
- **Gores** (the wedge between two diverging arms): BCC's fork gore starts 3.75 m wide at 6 m past
  the crotch tip and grows ~7 cm per metre; the wedge is filled with the shoulder/terrain surface
  welded to **both** arm edge rings at edge height.
- **Junction density equals road density.** The junction interior is never coarser than its arms
  and at most modestly denser: BCC 1.37 m core grid vs 1.39 m arms (identical) and 2.63 vs 2.66 m
  on the highway fork; union_island densifies its dedicated junction physics chunk ~1.6× (0.60 m
  edge median vs 0.95 m approach); macau's 0.82 m ribbon runs through unchanged.
- **Minor mouths can be cheap.** union_island J5: an unmarked village side street just butts to
  within 0.7 m of the major's pavement edge — no pad, no fillets — with a give-way bar dressing the
  visual gap; J2's dirt road terminates in two stubs at the paved road's shoulder line (unwelded,
  81 mm gap, hidden under the continuous shoulder strip). Even at their laziest the pros never let
  the minor ribbon cross the major's pavement.

### 2.2 Curbs, sidewalks, shoulders

The direct fix for 0033/0036. All three tracks, one law: **edge strips never cross a junction
mouth.**

- **rt_macau (urban — real raised curbs and sidewalks):** each curb strip (KERBS_1) wraps a
  corner-return arc and **terminates at the main-road edge**; the sidewalk plate (PAVINGSTONES_1)
  follows behind the curb around the same arc at +195–205 mm above pavement and terminates with
  it. Full curb returns are built on all four corners even when the side street is barriered
  scenery. Curb cross-section: vertical face **exactly 0.200 m** built with duplicated vertex
  columns (two vertices at the same position so the top and face get separate shading — a hard
  edge), ~0.2 m top ledge, then the sidewalk plate. Returns are segmented densely (~0.2 m
  stations) vs ~2.3 m on straights. Street curbs are **visual-only** — no physics twin, no
  surface-key prefix.
- **union_island (rural — 0.55–0.7 m shoulder strips, the sidewalk analog):** the strip follows
  the pavement outline **continuously around both fillet arcs into the side street**, its inner
  edge welded to the asphalt at 0.000 m — routed along the junction polygon boundary like a real
  curbline. At minor/dirt mouths the major's strip stays continuous and the minor tucks under it.
  Where village frontage or parking owns the edge, the strip is simply **omitted** — never forced
  through. Measured: 0 of 116 edge-strip tris over asphalt at J1.
- **ks_black_cat_county (rural — invisible OFF shoulder physics):** OFF strips flank every arm,
  wrap the corner fillets, fill the fork gore — and never cross the pavement (0 m² OFF-over-ROAD
  at all four junctions; 12,232 of 55,376 OFF verts network-wide are bit-exact welded onto road
  edge verts).
- **Racing kerbs are a different animal from street curbs:** macau's apex kerb is 45–50 mm tall,
  orange, and is the **only** kerb class with an invisible physics twin (1KERB, ~0.67 m grid,
  KERB fric 0.96 vib 0.05×0.03).
- **Traffic islands:** the junction pavement stays continuous underneath; the island is a closed
  curb ring **standing on** the pavement (curb tops +167–250 mm) with an infill plate. The island
  is never cut out of the pavement polygon (macau site A).

### 2.3 Markings

Two professional systems for base paint, one law for junction paint:

- **All-geometry overlay** (macau, union_island): every line, arrow, stop bar, text stencil and
  zebra bar is a separate alpha-tested mesh (*alpha-tested*: the texture's transparent pixels are
  simply not drawn, giving hard paint edges without blending cost) floated above the pavement.
  macau: 0.25 m-wide quad ribbons at exactly +20 mm (p10=p90=20 mm over 24,813 tris), zebra bars
  as individual quads 0.5–1.2 × 3.1–3.5 m, groove overlay above that at +30 mm. union_island:
  0.2 m dashes at +10 mm, text stencils +12–27 mm.
- **Baked into the road texture** (BCC): lane paint lives in the road diffuse (8192×1024 ≈ 114 m
  of road, ~72 px/m) and flows through the junction via each arm's UVs (*UVs*: the per-vertex
  coordinates that map the flat texture image onto the 3D surface).
- **Junction-specific paint is always decal geometry** (*decal*: a thin separate mesh floated just
  above a surface to add detail, like a sticker). union_island's junction wear decals are exact
  **clones of the underlying pavement triangles** (identical edge statistics) floated at a
  constant +10–31 mm, stacked pairs separated ~4 mm so the layers don't *z-fight* (two coplanar
  surfaces flickering because the renderer can't decide which is in front). BCC's per-layout
  closure strips are 8-tri, 0.374 m-wide ribbons whose every vertex is conformed to the local road
  slope, floated +5–20 mm.
- **Junction marking vocabulary** (union_island): give-way bar 0.4 × 3.0 m (one lane width) placed
  1.2 m before the major's pavement edge; solid no-overtake center line for the last ~9 m of
  approach; the major road's center line runs through the junction **uninterrupted** (the minor
  never breaks it); at a priority T the dash line bends into the priority leg.
- **Paint is physically inert everywhere.** No collidable marking mesh exists on any of the three
  tracks (macau's surfaces.ini LINES key is legacy — no mesh carries it).

### 2.4 Physics vs visual

- **The physics junction is invisible and dense; the visual junction is the same construction,
  coarser.** Physics grids at the junctions: macau 0.82–0.83 m, union 0.60 m (junction chunk),
  BCC 1.4–2.7 m. Visual grids over the same pavement: 3.4–3.8 m (macau), ~1.5 m pad (union),
  4–8 m (BCC) — 3–5× coarser, built with the same welded single-coverage discipline (BCC visual
  regions share 2–59 bit-exact boundary verts, with HI/LOW LOD twins — *LOD*: a lower-detail copy
  swapped in at distance).
- **The two surfaces agree vertically to millimetres.** macau physics-vs-visual median −1.5 mm
  (p10/p90 ±6 mm); BCC median 0.0–0.3 cm; union deliberately holds physics 10 mm *below* the skin
  (median −10.0 mm). One is derived from the other — never re-derived from source data.
- **Three physics recipes for the mouth itself:**
  - *macau*: the invisible 1ROAD ribbon runs through unchanged. Enterable mouths get a coarse
    `1ROAD_EXT` cap (9-ish tris, edges 0.6–6.2 m) extending 2–6.5 m past the ribbon edge,
    butt-jointed within 10 mm, and the invisible 1WALL detours around the cap perimeter.
    Barriered mouths get **no physics at all** — the 1WALL runs straight across the mouth line
    while the visual street behind it still gets full curb returns and sidewalks.
  - *union_island*: each junction gets a dedicated, per-place-named invisible chunk
    (`1ROAD_ashton_cross`, 961 v) spanning gutter-line to gutter-line, ~1.6× denser than the
    approach, seamed to it with a straight welded transverse cut.
  - *BCC*: one shared physics network in its own kn5 loaded by every layout; per-layout closures
    are just a tiny invisible wall across the closed mouth (10–30 verts) + visible props + one
    8-tri paint strip. The junction physics is never duplicated or re-cut per layout.
- **The visual road kn5 carries zero physics keys.** union_island deliberately disables three
  would-match meshes by prefixing `__` (`__1ROAD_test1` — the double underscore kills the
  surface-key match; a trick worth stealing). Low-speed surfaces may instead be single-layer
  *visible* physics meshes in the scenery kn5: union's 1KERB junction gutters, speed bumps, and
  1ROADD dirt roads.
- **Surface palette changes mark the junction to the tires:** union's village streets use ROADB
  (fric 0.90, vib 0.01×0.3) vs the main road's ROAD (0.9741); the junction zone on the major
  switches to a worn-asphalt visual material for ~35 m; the pad seams carry 1.0 m-wide collidable
  gutter strips (KERB fric 0.92) that give an audible cue crossing the junction limit. (This is
  MEASURED.md §4's "palettes, not single keys" applied at a junction.)

---

## 3. THE RULES

The union of the three dissections' transferable rules, deduplicated. Each rule states the check
that proves it and the evidence behind it. "Zero" means zero — the pros' tolerances are binary.

**Topology and pavement**

1. **Never sweep two road ribbons through each other.** The junction pavement is a
   single-coverage surface: zero road-triangle centroids inside another same-level road triangle
   in plan view. *(Evidence: 0 overlaps at all 13 sites; BCC network-wide 3/298,453, all one
   legacy sliver.)*
2. **Pick the topology per mouth:** junction **pad** (§2.0 B) for drivable intersections;
   **ribbon-through** with a butt-welded side mesh (§2.0 A) when one road owns priority or the
   side street is scenery. Never a third thing. *(macau A/B/C; union J1 vs J2/J5; BCC J1/J3/J4.)*
3. **Weld every pavement seam exactly.** Seam vertices are position-identical (0.000 m), and
   nothing sits between 1 mm and 5 cm of a seam vertex — no near-misses. In Blender: build the
   pad and arm from shared edge loops, then split; never "snap close". *(macau 12–25 exact +
   0 near-misses per mouth; union median 0.0000 m; BCC 5–28 bit-exact verts per cut.)*
4. **Keep the whole junction interior in one mesh chunk**; terminate each arm at a straight
   transverse cut 5–30 m from the junction center (6–8 m past the crossing pavement edge is the
   village-scale number). Chunk sizes stay ordinary: ~450–1,000 verts. *(BCC cuts at 13–21 m;
   union pad ends 6.3–8.2 m past the far edge.)*
5. **Fillet every convex corner with a true circular arc**, drawn with verts every 0.6–0.8 m
   (~9°/segment), belonging to the pad: R 0.8–1.5 m service mouths, R 3–6.5 m residential
   streets, R up to ~10 m onto fast roads. **Round every concave crotch**: R ~1 m tight V-merge
   to ~9 m shallow fork. No polygon corners, no *n-gons* (faces with more than four sides —
   exporters triangulate them unpredictably); quads and triangles only. *(macau fits 0.8/1.4/
   5.0/5.6 m; union 5.62/6.53 m at residuals ≤32 mm; BCC crotches 1.1/8.6 m, fillet 9.9 m.)*
6. **Mesh the junction at the arm's density — or up to ~1.6× denser, never coarser.** Density
   carries bump truth; the mouth is not a place to save triangles. *(BCC 1.37 vs 1.39 m —
   identical; union junction chunk 0.60 vs 0.95 m approach; macau ribbon unchanged at 0.82 m.)*
7. **Between diverging arms leave a gore** starting ~3.75 m wide 6 m past the crotch tip, growing
   ~7 cm/m, filled with the shoulder/terrain surface welded to both arm edge rings. *(BCC J4.)*
8. **Minor/driveway mouths may be cheap** — butt the minor ribbon to within ~0.7 m of the major's
   pavement edge with no pad — but only if (a) the major's edge strip runs continuous over it and
   (b) a give-way bar or wear decal dresses the gap. The minor still never overlaps the major.
   *(union J5 mouth, J2 dirt stubs: 0/118 tris over asphalt.)*

**Curbs, sidewalks, edge strips**

9. **Sidewalk/curb/shoulder strips NEVER cross a junction mouth.** Each strip follows the
   junction pavement outline around the corner-return arc — terminating at the major's edge
   (urban curbs) or continuing around the arc into the side street (shoulders) — with its inner
   edge welded to the pavement edge. Zero strip triangles over any pavement. This is the direct
   fix for 0033/0036. *(macau: all curb strips terminate at return arcs; union 0/116 strip tris
   over asphalt, inner edge welded at 0.000 m; BCC 0 m² OFF-over-ROAD, 12,232 bit-exact edge
   welds.)*
10. **Urban curb profile:** vertical face exactly 0.20 m tall, built with duplicated vertex
    columns for a hard shading edge; ~0.2 m top ledge; sidewalk plate continues at +195–205 mm
    above pavement. Segment corner returns at ~0.2 m stations, straights at ~2.3 m. Street curbs
    are visual-only — no physics twin, no surface prefix. *(macau, all sites.)*
11. **Racing kerbs are a separate low element:** 45–50 mm total height, and the only kerb class
    that gets an invisible 1KERB physics twin (~0.67 m grid). Never conflate with the 200 mm
    street curb. *(macau site C.)*
12. **Traffic islands stand ON continuous pavement:** closed curb ring (top +0.20–0.25 m) plus
    infill plate; never cut the island out of the junction polygon. *(macau site A.)*
13. **Where frontage/parking owns the edge, omit the strip entirely** — never force a sidewalk
    through. *(union J5 west side.)*

**Markings**

14. **All paint is separate geometry, never baked into the pavement mesh and never collidable.**
    Line ribbons: constant-width quad strips (0.20–0.25 m) floated at a constant +10–20 mm; text
    stencils +12–27 mm; zebra bars individual quads ~0.5–1.2 × 3.1–3.5 m; layer stack pavement 0 /
    paint +10–20 mm / groove +30 mm. Alpha-tested material, no surface-key prefix. *(macau
    +20 mm median across 24,813 tris; union +10 mm; no collidable marking mesh on any track.)*
15. **Decals clone the surface under them:** copy the pavement's own triangles, assign the decal
    material, float at a constant offset in the +5…+30 mm band, conform every vertex to the local
    slope; stack layers ~4 mm apart to avoid z-fighting. Never re-triangulate a decal
    independently, never use a flat plane, never exceed ~3 cm (visible gap). *(union wear decals:
    identical edge stats to the pavement, +26.8/+30.8 mm pair; BCC strips slope-conforming,
    +5–18 mm.)*
16. **Junction marking vocabulary:** give-way bar 0.4 × 3.0 m, 1.2 m before the major's pavement
    edge; solid center line for the last ~9 m of a give-way approach; the major's center line
    runs through the junction uninterrupted; at a priority T, bend the line into the priority
    leg. *(union J1/J5.)*

**Physics and visual**

17. **Build the junction twice: invisible dense physics + visible coarse skin**, same welded
    single-coverage construction in both, visual 3–5× coarser, and the two agreeing vertically
    to millimetres (|median dz| ≤ 10 mm; derive one from the other, never re-derive). *(macau
    −1.5 mm median; BCC 0.0–0.3 cm; union −10 mm by design.)*
18. **Physics recipe per mouth:** (a) drivable junction → per-place-named invisible chunk
    (`1ROAD_<place>_cross`) spanning the junction limits, welded straight cuts to the approaches;
    (b) enterable-but-minor mouth → leave the main ribbon unchanged and add a coarse `1ROAD_EXT`
    cap 2–6.5 m deep (edges 0.6–6 m), butt-jointed ≤10 mm, with the invisible wall detoured
    around the cap; (c) set-dressing mouth → **no physics at all**, wall straight across the
    mouth line, full visual curb returns behind it. *(union J1; macau A open vs A/B barriered.)*
19. **The visual road kn5 carries zero physics keys.** Prefix `__` to kill an accidental
    surface-name match. Exception class: low-speed features (junction gutters, speed bumps, dirt
    roads) may be single-layer visible physics meshes (1KERB/1ROADD) in the scenery kn5.
    *(union `__1ROAD_test*`; macau: every visual layer unprefixed.)*
20. **Layout variants share one physics network:** per layout add only a small invisible wall
    across the closed mouth (10–30 verts), barrier/sign props, and a slope-conformed paint strip
    repainting the through-line across the closed arm. Never duplicate or re-cut junction physics
    per layout. *(BCC layouts 1/2/3.)*
21. **Optional pro flourishes that make a junction read:** a 1.0 m full-width collidable gutter
    strip (1KERB, surface −9…+14 mm vs road) slit into the pad seam as an audible junction-limit
    cue; a worn-asphalt material change on the major for ~35 m through the junction zone; a
    different surface key (ROADB-style friction/vibe) for the minor network. *(union J1/J5;
    aligns with MEASURED.md §4 friction palettes.)*

---

## 4. Machine gates (audit-check candidates)

Rules that reduce to deterministic geometry checks. These are the half of the white-glove loop
that survives regeneration (0036): the draft must pass them before hand-authoring, and every
hand-edit is re-verified against them.

| Gate | Check (on the built OBJ / kn5) | Rule | Threshold (measured basis) |
|---|---|---|---|
| **K gates hard** | kerb/sidewalk verts (K) and tris (I) inside the carriageway = **0** for street kinds — promote existing audit K from advisory to the `hard` exit total (`audit_mesh.py:671-675`), exactly as 0036 routes it | R9 | pros: 0 at all 13 sites |
| **Pavement single-coverage** | road-tri centroids inside another same-level road tri = **0** within every junction polygon; network-wide tolerate ≤3 legacy slivers, 0 at junction seams | R1 | BCC ships 3/298,453; every junction 0 |
| **Seam weld binarity** | at each junction seam: every boundary vert either coincides <1 mm with its partner or is >5 cm away; count in (1 mm, 5 cm) = **0** | R3 | macau 0 near-misses; union 0.0000 median |
| **Junction density ratio** | junction-core grid ÷ approach-ribbon grid ∈ **[0.6, 1.0]** (equal or denser, never coarser) | R6 | BCC 0.99×; union 0.63× |
| **Marking float band** | every marking/decal vert +5…+30 mm above the pavement directly below; per-object offset constant (p90−p10 ≤ 5 mm); no marking carries a surface key | R14, R15 | macau p10=p90=20 mm; union +10…+31 mm |
| **Physics/visual dz** | \|median physics−visual dz\| ≤ 10 mm sampled over the junction polygon | R17 | measured medians −10…+3 mm |
| **No dead-ends in mouths** | zero open mesh ends (boundary edge rings of a ribbon) inside any junction-mouth polygon — 0035/0033's severed-ribbon check | R1, R8 | union dirt stubs end AT the shoulder line, not in the mouth |
| **Visual kn5 physics-free** | zero surface-prefixed object names in the visual road kn5 (allow `__`-prefixed) | R19 | union/macau: 100% split |
| **Curb-return segmentation** | curb/strip station spacing ≤0.3 m within fitted corner-return arcs (flags un-authored square corners) | R5, R10 | macau 0.18 m median in returns |

Not machine-checkable (stay human/Claude judgment in Blender): topology choice per mouth (R2),
fillet radii appropriateness (R5 values), marking vocabulary (R16), island/gutter flourishes
(R12, R21).

---

## 5. Pattern library

Reference geometry extracted from the three tracks, cropped to the junctions studied, in
`tracks/_reference/junctions/` — indexed in detail by its
[README](../tracks/_reference/junctions/README.md). Load any OBJ straight into Blender
(world coordinates, y-up) and study it next to this document:

| Dir | Track | What it teaches |
|---|---|---|
| `rt_macau/` | Guia Circuit street junctions | ribbon-through topology, urban 200 mm curb returns, sidewalk termination, +20 mm paint overlay, 1ROAD_EXT mouth caps, wall detours, traffic island on continuous pavement |
| `union_island/` | paved T + dirt crossroad + minor mouths | junction-pad topology, R 5.5–6.5 m fillets, shoulder routed around the pad outline, junction gutters, wear decals cloned from pavement, give-way marking vocabulary, dedicated `_cross` physics chunk |
| `ks_black_cat_county/` | Kunos rural forks and layout splits | single-owner junction chunks, bit-exact arm cuts, gore construction, crotch rounding, per-layout closure kit (wall + 8-tri paint strip), OFF shoulder discipline |

The full extracts and every analysis script remain in the session scratchpad
(`junction-study/dissect-{0,1,2}/`) for re-running against other junctions; the crops in
`tracks/_reference/junctions/` are the durable, under-10 MB set.

**Caveats carried from the dissections** (read before citing a number as universal): fillet radii
5.5–6.5 m were measured on 7.5–8.3 m village roads — treat as the floor for residential corners;
no dropped-curb pedestrian ramps were confirmed anywhere (street curbs hold 200 mm at every
sampled point); union's unwelded dirt-stub joint (81 mm) is tolerable only because a continuous
strip hides it — never generalize it to paved seams; raised-island paint and chevron geometry
remain unmeasured (BCC has none; macau's island is curb ring + infill); "weld" claims are
1 mm-grid coincidence tests on extracted OBJs, and the zero-near-miss result is the operative
evidence of snap discipline.

---
id: 0061
title: Edges are paved hillsides, not road ends — the draft's edge is a ≥5 m asphalt sheet plus a 22 % terrace
status: open
scope: every constructed-corridor track (no `natural_ground`, no `road_edge.profile: sidewalk`): milford-road-course, high-plains, sand-creek first; exotics-racing-lv (natural_ground) for the runoff only
layer: engine
train: -
---

> *Filed 2026-11-01 by the feedback router on this box (no kn5, no Blender, no network: §B is the selector replayed on
> the engine's cached cross-sections; file:line cites are as of airoso `fb1e594`). Same day, after it was written:
> `road_profile.verge_m` (the Lariat's D4, ledger 0048 "Started") now sets the width of the shoulder's flat band per
> track — 2.5 m stays the default everywhere else (GATES-CHANGELOG 2026-11-01). The face draped from that band, its
> 2.5 m floor, the runoff and the terrace are untouched: they are this entry's fix A.*

## Symptom (Kevin, 2026-11-01, verbatim)

> "I've seen the current versions of the new tracks have messy edges like paved hillsides instead of the roads
> ending realistically on the edges."

"The new tracks" are the four that came through the chain on 2026-10-29 (ledger 0060, DEFINITION-OF-DONE): Nevada
Nights 0.2.0, Milford Road Course 0.2.0, High Plains 0.68.0, Sand Creek 0.28.0 — each T1, gates green, the draft
shipped with no authoring (0060: "the first pass of each track ships the *draft* through the chain"). None had been
driven before today.

## Evidence

### A. What the engine builds at a road edge (the code)

The edge of every constructed-corridor draft is ONE sheet, `ribbon.road_shoulder` (`scripts/geometry/ribbon.py:134-261`),
four points out from the lane edge per station and side:

1. the inner lip at the lane edge (`:171`);
2. a **flat 2.5 m verge** at deck − 0.01 (`verge_w: float = 2.5`, `:135`; `:174-175`);
3. the **ground-meet**, draped onto the graded terrain at the construction selector's slope (`:181-233`): cut 0.75:1,
   fill 4.5:1 (22 %) on tarmac, a 1:6 wall face above 4 m of fill. Its distance beyond the verge is
   `extra = min(60, max(2.5, drop × slope_r))` (`:215`) — **floored at 2.5 m**, so the face is never narrower than
   2.5 m even where the ground is 5 cm off the deck, and re-sized against the drop at the meet up to six rounds
   (`:226-233`) so a fill face chases ground that falls faster than 22 % out to the 60 m cap;
4. a 1 m **buried hem** 0.8 m into the dirt (`:240-245`).

`scripts/geometry/build_mesh.py:1240-1244` builds it with `ground=grass_surf` and names the whole sheet
**`1ROAD_shoulder`, material `road`**. From there every stage treats all four points as road:

- `scripts/ac/pbr.py:17` + `:237` (`match_key`: first prefix that matches): any `1ROAD*` object gets
  `asphalt_cracked_diffuse.jpg` — the verge, the fill face, the cut face and the hem are all cracked asphalt.
- `scripts/ac/track_folder.py:74` (`surfaces.ini` KEY=1ROAD) and `scripts/ac/export_kn5_addon.py:190` (`DRIVABLE`):
  the whole sheet has asphalt physics and collides as road.
- The construction doctrine's stone faces — `RETWALL_face` (fill wall > 4 m) and `ROCKCUT_face` (cut > 2 m),
  `build_mesh.py:2416-2417`, `:3363-3366` — **built 0 triangles on all four tracks** (`grep -c RETWALL\|ROCKCUT
  tracks/*/data/split_manifest.json` → 0). Every face in the four installs is asphalt-textured.
- `SHOULDERUND` (`build_mesh.py:2936-2938`, `pbr.py:54` dry dirt) is the same sheet seen from *below*; from the
  driver's seat it is never visible.

On a `race_circuit` (`scripts/config.py:83-87` defaults `runoff.enabled: true`) `kerbs.corner_runoff`
(`scripts/geometry/kerbs.py:161-220`) adds a **9 m asphalt apron from 2.5 to 11.5 m off the lane edge** on the
outside of every corner, **at deck height** (`:206-210`: vertex y = centreline y ± bank; no drape), `1RUNOFF_corners`
→ `pbr.py:18` cracked asphalt. The engine's own comment, `build_mesh.py:1004-1006`: *"a flat apron 'at graded
terrain height' makes sense beside a flat circuit, but on a pitched mountainside it's a tarmac shelf with a step at
the road band."*

Beyond the sheet the ground is engineered too: the `1GRASS_ring` annulus has rows at 1.5 / 4 / 10 / 22 m from the
meet (`build_mesh.py:2134`) and each row is raised to `meet − 0.01 − 0.22 × d` wherever natural ground is lower
(`:2236-2239`, "the 22 % floor"); the seam-weld raises every grass node within 5 m of a ring/runoff edge to a 20 %
line off it (`:2997-3119`, `_fW = _yW − 0.01 − 0.20 × _dW` at `:3108`). Both are dirt-textured (`pbr.py:48`,
`ground_dry_diffuse.jpg`, every `1GRASS*` tile on Milford, High Plains and Exotics; Sand Creek overrides `1GRASS`
to the Lariat's grass).

Why 22 %: the drive-test excursion sweep (`scripts/geometry/drive_test.py:1093-1100`, `:1151`) walks from the
centreline to `we + 9 m` every 150 m, and on a tarmac track gates any drop > 0.12 m per 0.5 m sample (24 %) inside
`built_edge + 4 m`, on the stated premise *"on a paved circuit … run-off there is a flat apron, so any drop really is
a ledge."* `built_edge` is the last `1ROAD*` surface, i.e. the shoulder's own outer lip (`:1153-1161`). The selector
was then tuned to fit under that budget — `ribbon.py:181-215`, "THE COMPLETE SELECTOR/GATE AGREEMENT (ledger 0025,
27 builds of evidence)": "on tarmac the whole 0–4 m fill range grades at 4.5:1 (22 %)". 0025's campaign (30 → 0
gated drops on IMI, ~29 builds) is where the graded floor, the ring rows obeying it, the stone lips and the
corridor_refine standard came from. **The compensation pattern:** the gate asked for a flat apron, and the builder
answered by paving and terracing every edge to 22 %, on every kind of track, whatever the real road does there.

### B. Measured on the four tracks (this box, 2026-11-01)

Replay of the selector (`ribbon.py:181-233`, the exact formula) against the **real 3DEP cross-sections** the engine
cached in `data/corridor.elev.json` (25 offsets, −60..+60 m, every ~6 m of lap), deck = `data/gate_centerline.json`
(the finished line in the engine frame; `finished_centerline.json` has z negated) + origin elevation. Scratch script
`edge_xsec.py` / `runoff_xsec.py` (the second calls the engine's own `corner_runoff` on the gate line). Numbers are
per station-side, both sides of the lap.

| | Milford (hill course) | Sand Creek | Exotics (flat lot) | High Plains |
|---|---|---|---|---|
| edge mode | constructed, `race_circuit` | constructed, `street_circuit` (runoff off, kerb off) | **`natural_ground`**: 2-point verge, no drape (`ribbon.py:249-252`) | constructed, `race_circuit` |
| relief / width | 39.6 m / 11 m med | 30.8 m / 11 m med (5.5–42 OSM) | 11.5 m / 13.6 m | 15.1 m / 12 m |
| deck − ground at the verge (edge + 2.5 m) | median 0.29, p90 0.88, max 1.78 m | 0.26 / 1.58 / 10.17 m | 0.16 / 0.63 / 0.96 m | **no corridor file — not measured** |
| cut / fill / wall (> 4 m fill) | 47 / 53 / 0 % | 41 / 55 / 3 % | 50 / 50 / 0 % | — |
| **paved `1ROAD_shoulder` beyond the lane edge** | **median 5.0, p90 6.9, max 23.2 m**; > 5 m 19 %, > 8 m 7 %, > 12 m 4 % | **median 5.0, p90 28.1, max 54.2 m**; > 8 m 18 %, > 20 m 15 % | 2.5 m flat verge (by code path) | ≥ 5.0 m by code (the 2.5 m floor + 2.5 m verge) |
| cut faces paved at 0.75:1 | 126 sides > 0.5 m of cut, 3 > 1.5 m | 199 > 0.5 m, 88 > 1.5 m | none > 1.5 m | — |
| natural cross-slope 10–25 m out | med 4.5 %, p90 13.1 %, max 24.6 % | med 4.3 %, p90 31.4 %, max 59 %; **18 % of sides steeper than 22 %** | med 1.5 % | — |
| `1RUNOFF_corners` (actual footprint) | **718 stations, ~2,378 m of a 4,074 m lap**; rim (deck height) vs real ground: median 0.48, p90 1.53, max 2.84 m; **48 % of rim verts > 0.5 m off the ground** (24 % hung over fill, 24 % cut into the hill), 25 % > 1 m | off (archetype) | 292 stations, ~965 m of 1,822 m; rim median 0.15, p90 0.83, max 1.07 m; 19 % > 0.5 m (18 % below ground) | same code; not measured |

So: with the 2.5 m floor, **the paved sheet is at least 5 m wide on both sides of 100 % of stations** on every
constructed track, on an 11–12 m road — the drivable asphalt is 21–22 m wide before any runoff. Where the ground
leaves the deck it grows with it: on Milford's side slopes to 7–23 m, on Sand Creek's creek banks (ground falling
faster than the 22 % sheet can meet) to 28–54 m — a sheet of cracked asphalt down the bank. In the cuts (half of every
lap) the "hillside" above the road is a 2.5 m flat asphalt shelf and then an asphalt face climbing into the hill: no
ditch, no soil, no daylight rounding. The replay reproduces the one cross-section 0060 recorded on the built Sand
Creek OBJ (s 6522: shoulder flat to ±6.5 m then a 1:6 face to 29.4 at 8.0 m — the wall case, `extra = 6.2/6`).

### C. What the gates saw, and why they are green

All four pass (`data/drive_test.full.json`, `kn5_ground_check.full.json`, `audit.json`): excursion drops gated 0 / 0 /
0 / 2, far ledges 7 / 5 / 13 / 7 (Exotics / Milford / High Plains / Sand Creek), the worst ungated at 14–18 m lateral
(Milford [2251.4, −14.0, 0.37], High Plains [2552.8, −14.0, 0.31]) — i.e. **beyond** the sheet, where the engineered
terrace meets the real ground. `kn5_ground_check` "flush edges" (deck − surface at edge + 3.5 m and + 6 m,
`scripts/ac/kn5_ground_check.py:576-603`): +0.03/+0.70, +0.17/+0.78, +0.13/+0.47, +0.12/+0.54 (DoD rows) — on a
≥ 5 m sheet both samples land on the **sheet itself** (`:597` "nearest surface here (pavement or verge)"), so the
metric that "matches the driver's eye" measures the engine's own asphalt, not the ground. Every gate measures
self-consistency (REALISM §1); none asks what the edge is made of or how wide the pavement is. Nothing here is a
coverage gap to close first — the machinery is running and cannot see this.

### D. What the doctrine says the edge is

`docs/ROAD-CONSTRUCTION.md`: *"verge 0.3–0.5 m gravel"* (real_road), *"Cut-toe DITCH: V, ~0.4 m deep × 1.2 m wide
against the face"*, *"Round the cut top into natural ground over 2–5 m"*, fill 2:1 / 1.5:1 earth, stone wall above
4 m, *"sidewalk 1.5 m attached or gravel verge"* and *"cut/fill ≤ 1 m at 4:1"* for the Sand Creek street. The
Milford dossier (`tracks/milford-road-course/DOSSIER.md:239-243`): *"Runoff extent is unknown. A proving ground may
have guardrail close to the edge, so verify it from video before accepting the preset's runoff."* — the preset was
accepted. The Exotics dossier (`:100`, `:161`): T2's run-off is *"about 450 ft"* with a **gravel trap** and Tec-Pro
barriers — the preset can only express asphalt. `fleet/LAWS.md` L3 says the ground conforms to the road and L9
keeps kerbs tight to the edge; no law says what the road *ends* in. REALISM §2: edge treatments are authored — but
the engine is supposed to prepare a *truthful* underlay, and this one is wrong at every station.

## Diagnosis

As far as the evidence carries it: what Kevin is describing is the engine's edge construction, not a per-track
defect. The draft has no road end — it has a **continuous asphalt sheet** (`1ROAD_shoulder`: 2.5 m flat verge +
a ≥ 2.5 m face draped to the ground + hem, asphalt in texture and physics, `ribbon.py:134-261`, `build_mesh.py:1244`,
`pbr.py:17/237`) that is at least 5 m wide beyond both lane edges everywhere and widens with every cut and fill, a
**deck-height 9 m asphalt runoff** on the outside of every race-circuit corner regardless of the ground under it
(`kerbs.py:161-220`), and beyond those a **dirt terrace graded to the same 22 %** out to 22 m (`build_mesh.py:2134,
2236, 3108`). On a hillside the three read as one graded, paved slope from the lane edge to 20–30 m out — "paved
hillsides". On flat ground (Exotics) the same code produces a 2.5 m paved verge and the aprons; the look there is
not verified and may be close to the real lot.

The width floor, the asphalt naming and the 22 % grade are each the gate's budget written into the geometry (ledger
0025), not anything from the construction doctrine; the stone faces the doctrine promises never build. This is a
compensation pattern: the fix is the cross-section, not another pass over it.

Not proven on this box: that the in-game look Kevin saw is this sheet rather than (or as well as) the dirt terraces
beyond it. The two are the same mechanism but different fixes; if his answer is "the dirt steps beyond the asphalt",
that half becomes its own entry.

## Fix (options, with cost)

**A. The engine draft builds the construction cross-section (the real fix, `engine`).** Split `road_shoulder` into
(i) a **verge** — the only part that stays `1ROAD_*`/asphalt — whose width comes from the archetype or the dossier
(`road_edge.verge_m`: race_circuit 0–1 m paved shoulder, real_road 0.3–0.5 m gravel, street curb/gutter), and (ii)
the **cut or fill face as terrain**: `1GRASS`-family material and physics (or `ROCKCUT_face` / `RETWALL_face` where
the selector says so, which today build 0 verts), with the doc's cut-toe ditch and 2–5 m daylight rounding, and the
2.5 m floor on `extra` (`ribbon.py:215`) removed so the face's width is the construction's, not the gate's. Fold the
ring floor / seam-weld 22 % reach into the same cross-section (a fill face at 2:1 and natural ground beyond, not a
terrace). **Cost:** the drive-test excursion rule (`drive_test.py:1099-1100`, 24 % inside `built_edge + 4 m`) was the
reason for the 22 % sheet and will go red on every 2:1 fill face the day the face stops being `1ROAD`; the gate must
learn the cross-section — beyond the verge, a face at the selector's own grade is the surface, not a ledge (the
unpaved branch at `:1116-1121` already reasons this way) — as a `fleet/GATES-CHANGELOG.md` entry in the same commit.
0025's "selector/gate agreement" rewritten, both halves at once. 2–4 days of geometry-surgeon work plus a fleet
rebuild; the Colorado matrix 0025 tuned (IMI, Pueblo, Aspen) must stay green under the amended rule.

**B. Runoff only where the place has it (`engine`, small).** `corner_runoff` draped onto the graded ground like the
shoulder, with the surface per corner from the dossier (`runoff.corners[]`: tarmac / gravel / grass / none) and the
`race_circuit` default **off** until declared. Milford's dossier already says to verify before accepting; Exotics' T2
is a gravel trap the preset cannot express. Independent of A; a day.

**C. Material and physics only (cheap, partial, not shippable alone).** Name the face and hem a terrain-family group
(dirt texture, 1GRASS physics) and keep the 2.5 m verge as `1ROAD`. Fixes what the face is made of, not its width or
the terrace — and moves `built_edge` to the verge, so every fill face falls inside the gate's band and goes red until
A's gate change lands. It is A's first step, not an alternative.

**D. Authoring (REALISM §2 Job 2).** Re-cut the `GEN_road` shoulder per track in `loop.blend`. Hand work × 4,
discarded by every draft regenerate, and the draft is wrong at 100 % of stations: this is an engine defect, not an
edge treatment to author. Authoring belongs *after* A, for the places that are specific (the Carousel's kerb line,
the Tec-Pro row, Sand Creek's industrial aprons).

## Scope

- **Affected:** every track built in constructed-corridor mode — any config with neither `natural_ground: true`
  nor `road_edge.profile: "sidewalk"`: Milford, High Plains, Sand Creek now; Pueblo, Aspen, Grand Junction, Pikes
  Peak, Second Creek, the Lariat and the four rally stages when they come through the chain (`fill_apron` is tarmac
  only, so the gravel stages keep steep faces but the same asphalt-named sheet). `natural_ground` tracks (Exotics,
  IMI) carry the 2.5 m paved verge and, on race_circuit, the runoff. `curb_sidewalk` (`ribbon.py:264-348`, "point 4:
  drape onto the ground at a fill/cut slope") is the same family for sidewalk tracks.
- **Proof cases:** **Milford** (hill course; all three pieces: sheet, runoff, terrace; 41 m of relief, cross-sections
  cached) and **Sand Creek** (the creek banks: the 28–54 m runaway sheet; `osm_road_widths`; runoff already off, so
  it isolates the sheet).
- **Regression cases:** **Exotics** (flat, `natural_ground`): the edge should barely move except T2's runoff; a big
  change there means the fix is wrong. **rally-dragon-tail-gravel/tarmac** (unpaved vs tarmac branch of the same
  gate rule). **IMI / Pueblo / Aspen** (0025's matrix: must stay green under the amended gate). **San Diego**:
  `ship_sd.sh` byte-identical, the assembler's own terrain — unchanged by anything in `build_mesh`.

## Verification (decided before the fix)

1. **An edge-construction measurement on the BUILT gate OBJ**, added to `kn5_ground_check` where the flush-edges
   sampler is (`kn5_ground_check.py:576-603`), reported per station at the lateral sections: paved width beyond the
   lane edge (`1ROAD_*` + `1RUNOFF_*` surface owner) ≤ declared verge + 0.5 m at ≥ 95 % of station-sides (today:
   ≥ 5 m at 100 % on the constructed three); the surface beyond it is a terrain-family group; at cut stations a
   ditch (a local minimum ≥ 0.3 m deep within 2 m of the verge). The same numbers from the replay script on the
   corridor file for the draft, as a text rule in `tests/geometry/test_build_mesh_edge_rules.py`.
2. `drive_test` green on Milford, High Plains, Sand Creek, Exotics under the amended excursion rule, far ledges not
   up; `audit_mesh` CLEAN; `kn5_ground_check` PASS with deck-vs-mountain unchanged (p95 ≤ +0.02 as today).
3. **Kevin's seat (T2 → T3 of DEFINITION-OF-DONE):** stopped at the edge in Milford's esses / Carousel (s 620–800)
   and on a side-slope station of the back half, and at High Plains' Prairie Corkscrew: the asphalt ends at a verge,
   the ground past it is dirt or grass rising or falling at a bank's angle, the hill reads as a hill. Fixed-station
   stills before/after from the same camera (REALISM §4 `views.py`) in the drive-test report.

## Not verified on this box

- The kn5s and `loop.blend` scenes are not here; nothing in-game was looked at. Section B is the selector replayed
  on the engine's cached cross-sections, not the built OBJ (which 0060's one Sand Creek section matches).
- High Plains has no `corridor.elev.json`; its numbers are by code path only.
- Sand Creek's replay does not know the bridge spans (the shoulder drape does not either — only the ring columns
  break at spans, `build_mesh.py:2228-2229`); the 54 m maximum is at a creek crossing.
- Whether the prep (`build_kn5_loop.py`) re-materials anything at the edge: the prefix table says no, not run here.
- Which of the three bands Kevin's "messy" names — asked above.

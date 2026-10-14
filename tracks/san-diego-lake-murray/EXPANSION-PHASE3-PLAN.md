# Lake Murray network expansion: Phase 3 build plan (the Zion western loop)

> **2026-10-14, revision 2. This is a plan only. Nothing is built.**
> - Ledger [0054](../../fleet/feedback/0054-lake-murray-network-expansion-waring-mission-gorge-jackson.md), section "The roadmap of Lake Murray phases". The place facts for Phases 3 and 4 are in [`DOSSIER-EXPANSION-WEST.md`](DOSSIER-EXPANSION-WEST.md). Phase 1's plan of record is [`EXPANSION-PLAN.md`](EXPANSION-PLAN.md). Phase 4's plan is [`EXPANSION-PHASE4-PLAN.md`](EXPANSION-PHASE4-PLAN.md).
> - **Research** ran on 2026-10-14 and was read-only on the repo, the worktrees, k10-sd-v021, engine-july and the AC folder. It lives in the session scratchpad `p34/`, in five lenses plus a revision pass:
>   - **routes3:** fresh OSM, osm_base 2026-10-14T10:13:39Z, through the 7-day guard (`_overpass`), TLS verified. It is the same data as the Phase 1 worktree's `data/osm.expansion.json`.
>   - **terrain:** USGS 3DEP 1 m, about 75k new samples. Phase 1's own P2 planner was reproduced exactly first: 421,917 points.
>   - **aerial:** NAIP 2022-04-25 at 0.6 m, 47 windows, with widths read by eye at 1 m ticks.
>   - **pipeline:** the chain, file by file, plus a census of the installed road kn5.
>   - **routes4:** Phase 4's lens, used here for where Phase 3's open arms lead.
>   - **revise:** re-measurements after review (`p34/revise/`): the stub counts, the Phase 1 stub widths in `expansion.north.json`, the built-to-planned ground ratio of the installed build, and the 3DEP fetch with the far-ring move.
> - **Stations** are metres from the junction node at the start of each leg, in clockwise drive order J2 → J6 → J7 → J3, measured along the routes3 OSM legs. The aerial stations match them to within about 10–20 m. The terrain lens's legs start a little after each node, and its stations have been shifted to match.
> - **Words.** "Phase N" means your expansion phase. This plan's own stages are **steps** (Step 0 to Step 5). Road IDs in the dossier are P3-WAR, P3-ZION and P3-MG; Phase 1 keeps its own W1/W5 (welds) and S1–S6 (stubs).
> - **Order.** Your roadmap runs Phase 1 (building now), then Phase 2 (Mission Gorge Speedway), then Phase 3.
>   - Steps 0–2 (data, the readable plan, the ground plan) can start now, on a branch off Phase 1's branch, and get rebased later.
>   - Step 3, the build, waits for Phase 1 to be merged, installed and driven. It builds on Phase 1's J2 and J3 corners, which are not built yet.
>
> Kevin, 2026-10-14, verbatim: *"Phase 3 will be waring to Zion, Zion to mission gorge"*

## The short version

- **Your roads exist as you said, and with Princess View they make a loop.**

  | Your words | Road | From → to | Length (clockwise / anticlockwise) |
  |---|---|---|---|
  | "waring to Zion" | **Waring Rd** south-west | J2 (Princess View corner) → **J6** (Zion Ave) | 0.67 km (669.8 / 668.9 m) |
  | "Zion to mission gorge" | **Zion Ave** west | J6 → **J7** (Mission Gorge Rd, Grantville) | 1.57 km (1,567.3 / 1,594.4 m) |
  | (so it joins up) | **Mission Gorge Rd** north-east | J7 → J3 (Phase 1's Princess View corner) | 2.36 km (2,364.8 / 2,389.7 m) |

  - Your estimates of ~0.6, 1.6 and 2.3 km check out.
  - The new loop is J2 → Waring → J6 → Zion → J7 → Mission Gorge → J3 → Princess View → J2. It is **5.71 km clockwise**, and every turn is a right turn, the same sense as Phase 1 and the Speedway.
  - **4.60 km of new road.** There are no bridges, no freeway and no river crossing. I-8 lies 1.1 km south; that is Phase 4.
- **It joins the network only at Phase 1's own corners, J2 and J3.**
  - Two of Phase 1's short closed-off arms become real road: **S2**, Waring south-west at J2, and **S3**, Mission Gorge west at J3.
  - The 13.48 km loop is not touched at all. **Lake Murray Speedway and Speedway Reverse stay byte-for-byte the same.**
- **Three very different roads:**
  - **Waring** is a boulevard with a planted median, 28–30 m curb to curb. It runs over a small 106.6 m crest. Speed limit 35 mph.
  - **Zion** is a residential two-lane street, 11.5–15 m wide, 30 mph. It **drops 66 m to the valley, with a 10 % pitch at s 570–660**. After Princess View, it is the network's second steep street.
  - **Mission Gorge** is a six-lane divided arterial on the valley floor, 27–34 m wide, with a terracotta median. It is 45 mph, then 55 mph. Its sag at **28.7 m becomes the network's new lowest point**, 4.7 m below J3.
- **Every side road ends in a barrier, on a short real stub.** This is your Phase 5 choice, used from the start.
  - 30 public side streets, plus the 5 closed arms at the two new corners (one of them a slip lane), each get a 15 m stub of real road closed by a K-rail barrier. That is 35 barrier stubs.
  - 45 mapped driveways and service drives get curb cuts.
- **Free Roam grows from about 24.3 km (after Phase 1) to about 28.9 km.**
- **The ground grows west once, sized for Phase 4 as well.** That is +62 columns of the 40 m survey grid, and no old stake moves.
- **The honest cost is the streetlights first, and the ground second.** At today's lamp model, lighting Phase 3 would push the track file about 24–32 MB past the 145 MB ceiling. A lighter lamp fixes that (see Budget). The ground mesh you drive on roughly doubles from today's 357k points to ~690k, which is a frame-rate question nobody has measured yet.
- **Two drives:** Drive 1 is the roads, corners and ground. Drive 2 is the signs, lamps, trees and buildings.

## Decisions for Kevin

**There are three questions, ordered by what they hold up.** Each default is complete, and the build goes ahead on the defaults if you don't answer. None of them changes a law.

| # | Question | Default | Why |
|---|---|---|---|
| **D1** | **How does the Mission Gorge Speedway (Phase 2) treat J2 and J3?** That Speedway turns right at both corners. Phase 3 puts real road almost straight ahead at J2 (Waring comes in at 239° and Waring SW leaves at 224°) and off to the west at J3. | **Phase 2's race tools seal both openings from day one, with the same kind of sealed mouth they use at every other side street.** When Phase 3 lands, it only removes the stub's barrier, and the Speedway's seal doesn't move. No race layout on the western loop: Free Roam only. | If Phase 2 counted on Phase 1's stub barrier as its seal, Phase 3 would quietly open the Speedway's corridor. The Phase 2 lap tool (`scripts/geometry/race_lap.py`, in flight) already models "the abandoned branch beyond every junction, with a probe point on it", so this is a declaration, not a new tool. Zion (30 mph, 10 %, 11.5–15 m, houses on both sides) is not a race road. **Holds up: Phase 2's corridor design, which is in progress now.** |
| **D2** | **How far west do the views reach?** The far ring (the painted backdrop that is the real shape of the land) ends at −117.108 today. From Mission Gorge at Zion, 8.5 % of the skyline lies past that edge. From Phase 4's freeway at the Fairmount interchange, **42.3 %** does; from a freeway end at −117.1045 it would be 53.5 %, the worst gap 4.29° above the eye. | **Move the far ring's west edge to −117.14 now, once, for both phases.** From the Fairmount interchange only 2.8 % of the skyline is then missing (worst 0.69° from −117.1045). It costs about +25.3k see-only ground points and about +40.7k 3DEP samples (~91 requests). | It is see-only: no drive gate (`drive_test`, `verify_mouths`, `no_route`) reads it. The only check that touches it is V7's far-cell check (within 1 m of 3DEP). Doing it in Phase 3 means one config, sampling and tiling change instead of two. The south edge (32.755) is fine as it is: the mesa wall 0.2–0.8 km away closes that view. **Holds up: Step 0's config and the 3DEP fetch.** |
| **D3** | **Streetlights on Phase 3's roads.** Lighting all 4.6 km at the loop's spacing (17.7 per km) is about **80 lamps**. Today's lamp is heavy: 4,045 points and 0.201 MB each. That would add **+16 MB** to a file every layout loads, and the file is already projected at 143–147 MB after Phase 1. | **Light all three roads, but only with a lighter lamp, about 10× fewer points, applied to every lamp on the network.** That lamp lands before Phase 3's Drive 2. If it hasn't landed, Phase 3 ships unlit and the lamps follow. The positions stay labelled *authored* until a Street View night check. | Lamps are already 57 % of the installed road kn5's points and 41 % of its size: 966,725 points and 47.9 MB for 239 lamps. A lighter lamp brings the whole network, fully lit, back well under the ceiling (see Budget). **Holds up: Step 4, and the lamp-model work, which also helps Phase 1.** |

### Defaults I will apply unless you say otherwise

- **A1. Exactly the three roads are drivable.** The other arms of the new corners are closed with Phase 5 barrier stubs (5 junction arms):
  - **J6 (Waring/Zion):**
    - Waring south, divided (ways 1214006896 out / 436411991 in). **Phase 4 opens it** toward I-8.
    - Zion Ave east, residential, 25 mph (way 1430783899).
    - The free-right slip lane from Zion eastbound to Waring southbound (secondary_link 1214006895, stop-controlled, at Zion s 62). It is built with its island and closed with a barrier; Phase 4 removes that barrier together with Waring south's.
  - **J7 (Zion/Mission Gorge):**
    - Mission Gorge south, divided (436428806 in, 5 lanes / 436428813 out). **Phase 4 opens it.**
    - Zion Ave west, the ~200 m tertiary road to Riverdale St (1220464880 → 5993798).
  - **J2 and J3:** Mound Ave (S1) and the quarry drive (S4) stay as Phase 1 builds them.
- **A2. Side roads get Phase 5 barrier stubs** (`tools/stub_roads.py declare`, then `apply`). Kevin chose this on 2026-10-14.

  | Road | Public side streets (stub + barrier) | Mapped service drives (curb cut) | Median openings |
  |---|---|---|---|
  | Waring J2→J6 | 2: Greenbrier Ave NW and SE, s ~340, signalised | — | — |
  | Zion J6→J7 | 22: Glenroy N s 104 / S s 161 (offset); 51st St N/S s 242 (signal); Winona N s 521; Estrella N/S s 679; Clara Lee N/S s 776; Delbarton N/S s 863; Cartwright N/S s 959; Seaman N/S s 1051; Burgundy N/S s 1143; Crawford N/S s 1232 (signal); Bus Access Rd S s 1301; Archwood N s 1308; an unnamed road S s 1434 | 12 (1 private) | — |
  | Mission Gorge J7→J3 | 6: Allied Rd SE s 500; Greenbrier Ave SE s 590 (signal); Old Cliffs Rd SE and W s 929 (signal); Katelyn Ct SE s 1736; Goen Pl SE s 2024 | 33 (3 private), including the paired shopping-centre entrance at the Greenbrier signal and a 1.75 km service road at s 1277 | 5 |
  | **Total** | **30**, plus the 5 junction arms in A1 (the J6 slip is counted there, not here) = **35 barrier stubs** | **45** | **5** |

  - **A stub** is 15 m of real drivable road at the side street's own width, heading and 3DEP grade, with its paint. It is closed by your owned 4.04 m K-rail jersey modules, standing across it curb to curb and over both sidewalks (`STUB_LENGTH_M` 15, invented, in GATES-CHANGELOG 2026-10-14).
  - **A curb cut** keeps the curb continuous and drops its top over the driveway width, so the sidewalk ramps down like a real driveway apron.
  - **Unmapped driveways** (Zion's houses, Grantville's commercial lots) are counted on NAIP in Step 0 and added as authored curb cuts. A Street View pass checks them later.
- **A3. Medians: one pavement with the real median standing on it** (Phase 1's A2; JUNCTIONS rule 12). Think of a single sheet of asphalt with a raised planter set on top, not two separate roads.
  - **Waring:** raised, planted median, 2.5–5.5 m, with trees. The OSM carriageway lines are 8.8–10.1 m apart.
  - **Mission Gorge:** terracotta raised median, mostly 3–5 m and tree-planted, narrowing to 1.5 m strips at s ~900–1350. The OSM carriageway lines are 12.7–18.1 m apart.
    - **The 5 median openings stay open, as on the real road** (s 590 ×2, 1134, 1277, 1736). Each is a gap in the island on continuous pavement, so U-turns work in Free Roam.
  - **Zion:** undivided, with a double yellow line.
    - A painted two-way left-turn lane, about 3.5 m, at s ~900–1050.
    - Centre turn lanes at s 0–104 (Waring), 211–279 (51st), 934–983 (Cartwright), 1204–1258 (Crawford) and 1450–1567 (Mission Gorge).
- **A4. Real widths, curb to curb, read by eye off the aerial and varying along the road** (±1–1.5 m):

  | Road | Stations | Width (m) |
  |---|---|---|
  | Waring | s 150 / 300 / 450 / 600 | 28.0 / 29.5 / 29.7 / 22.0 (narrowing to Zion) |
  | Zion | every 150 m, s 150–1500 | 12.0, 12.0, 13.5, 11.5, 12.0, 13.0, 11.5, 11.2, 15.1, 14.8 (the last ~300 m is Grantville commercial at ~15 m) |
  | Mission Gorge | every 150 m, s 150–2250 | 32.1, 31.0, 27.5, 26.3, 27.3, 30.5, 27.0, 29.0, 31.3, 27.5, 32.7, 30.1, 31.9, 33.5, 33.7 |

  - The automatic width walker is not used. It misreads under tree shadow (Waring s 600, Mission Gorge s 450) and runs onto crosswalks and dirt shoulders (it reads Waring s 300 as 38.7 m).
  - **Where a new road meets Phase 1's arm, the widths disagree.** Phase 1 declares S2 (Waring SW at J2) at **23.0 m** and S3 (Mission Gorge W at J3) at **28.0 m** (`expansion.north.json`, eye readings at the arm). Phase 3 reads Waring at 28.0 m at s 150 and Mission Gorge at 33.5–33.7 m over the last ~265 m before J3 (turn pockets). So each new piece carries a **width transition inside itself**: it starts at the pad arm's width and widens to its own station widths, over at least 60 m [invented]. The pad is never widened to meet it. Step 1 re-reads both widths at the same station on NAIP; if Phase 1's arm reading is wrong, that is fixed in Phase 1's own record, not here.
- **A5. Junctions.**
  - **J6 and J7 are new corners and get authored junction pads**, using `author_junction_pad_blend.py`, the tool Phase 1 will write (it does not exist yet). A pad is one rug of asphalt poured under the whole crossroads, instead of two strips of tape laid over each other.
    - J6 is a four-way signal, with yellow school ladder crosswalks on every leg. Clockwise it is a right turn of +60°.
    - J7 is a +103° right turn onto Mission Gorge.
    - **Their curb-return radii are not measured yet.** Step 1 reads them off NAIP.
  - **J2 and J3 keep Phase 1's pads.** Only the arm's closing piece changes: the stub and its barrier are replaced by the new road, welded to the same straight cut on the pad. **Phase 1's P3 has not run yet**, so this depends on P3 building S2 and S3 as separate closing pieces on a straight arm cut. That request goes to Phase 1 now (First moves).
  - Clockwise turns: J6 +60°, J7 +103°, J3 +106°, J2 +84°. Anticlockwise, the mirror-image left turns are −75° to −107°.
- **A6. Real heights and real grades** (3DEP 1 m):

  | Point | Height (m) |
  |---|---|
  | J2 | 103.9 |
  | Waring crest, s 400 | 106.6 |
  | J6 | 99.7 |
  | J7 | 33.8 |
  | Mission Gorge sag, s ~300–400 clockwise | **28.7, the new network low** |
  | J3 | 33.4 |

  - **Zion** has the steepest grade: 10.1 % over 50 m and 9.8 % over 100 m at s 570–660, or 10.2 % on a 20 m chord.
  - The connector grade cap stays at 11 %, and **a gate proves it binds nowhere**. Zion sits within 0.8 points of the cap, so the height blends into J6 and J7 are checked separately. The terrain lens warns that a junction blend can steepen a grade the way Waring's J1 blend did in Phase 1.
  - **Waring** is easy, at 3.2–3.4 % max. **Mission Gorge** is at most 4.1–4.2 %.
  - The new roads meet Phase 1's pads at the pads' built height; the pads are never moved to meet them.
- **A7. Layouts.**
  - **Lake Murray Free Roam** becomes the whole network.
  - **Lake Murray Speedway and Speedway Reverse** are untouched, because Phase 3 adds no opening on the loop.
  - **Mission Gorge Speedway (+ Reverse)**, if Phase 2 has shipped, follows D1.
- **A8. Signs.**
  - **Corner arrows by your 0044 rule** ("tight corners", at the corner, just past the outside edge, facing the approach), in both directions per 0051. The new movements are J6, J7, Mission Gorge → Princess View at J3, and Princess View → Waring SW at J2. That is about **8 plates**, counted in Step 1.
  - **Speed limits from OSM:** Waring 35 mph; Zion 30 mph; Mission Gorge 45 mph from J7 to Old Cliffs (s 929), then 55 mph.
  - **School crosswalks:** yellow ladders at J6, at Greenbrier on Waring, and at 51st St on Zion.
  - **No signal heads.** The network has none.
  - The sign preview is shown to you before the build.
- **A9. Trees by zone** (the 0040 rule):
  - Waring's median: small median trees.
  - Zion: street trees at its real low canopy, 3–15 %.
  - Mission Gorge, north-west side near Zion: San Diego River riparian woodland. The likely mix is eucalyptus, willow and palms; Sycamore V1/V2 and Oak3 stand in for the broadleaf trees.
  - **Eucalyptus candidate:** a row of trees on Mission Gorge's south-east side at s ~1150–1250, whose shadows reach ~25 m, so the trees are 20 m or taller. The installed Gum model goes there. Street View confirms the species.
  - Palms along Mission Gorge near Zion.
  - Tree caps scale with area, as in Phase 1.
- **A10. Buildings:** OSM footprints within 120 m of the new roads.
  - At J6: the Benjamin Branch Library (NW), the Arco station (SW), the Grocery Outlet / Dollar Tree centre and its lot (SE), and Allied Gardens Community Park and pool (N).
  - On Zion: Foster Elementary, Magnolia Science Academy, Kaiser Zion Medical Center, and the Vons lot.
  - Grantville industry along Mission Gorge.
- **A11. No AI on the new roads.** AC's AI follows one line, and Free Roam's line stays on the loop. AI lines are never generated from GPS.
- **A12. Map.** Free Roam's map shows the whole network. Each Speedway's map shows only its own lap.
- **A13. Chain.** Every step lands in `tools/ship_sd.sh` and `ship_track.sh` in the same change, and the parity test stays green.
- **A14. Ground grown once, to Phase 4's width:** `cols_w` goes from 26 to **88**, not 72. The 16 extra columns cost 2,672 grid nodes and no mesh until roads are planned on them. The alternative is two regrows, each with its own pin, remap and meta change. (88 covers Phase 4's default; Phase 4's west alternatives need 90 or 104–105 columns, see its D1.)
- **A15. Versions.** Drive 1 is the next minor version after Phase 2's (v0.21.0 if Phase 2 ships as v0.20). Drive 2 is a patch on it. Publishing follows `docs/PUBLISHING.md` and is your click.

**Asked later, not now:**
- the real lamp positions (after the night check);
- the eucalyptus row (after Street View);
- whether a longer Speedway wants the western roads (after Drive 2).

## Where it stands today

| | State |
|---|---|
| **Installed** | **v0.18.0**: the 13.48 km loop plus side streets, in three layouts (Lake Murray Free Roam / Speedway / Speedway Reverse). Ledger 0046's terrain is in, with the global real-ridges clamp 20/40 m. The road kn5 is 116.3 MB with 1,697,179 points; 239 lamps make up 966,725 of those points and 47.9 MB. The physical ground is 8 tiles (1GRASS_0–7), 357,262 points built from a planned 163,404 + 76,926 refine nodes. The drawn see-only I-8 (`tools/author_freeway_blend.py`) is OFF. |
| **Phase 1** | Branch `worktree-wf_c6ab4b42-146-1` at edd5096. P0 (data), P1 (the readable intermediate and the J1/J5 weld rehearsal) and P2 (the ground: grid grown 37/37 rows and 26 west columns, frame pinned, cache re-keyed) are done. **P3, the road build, has not run**; it needs `author_junction_pad_blend.py`, which is not written yet. S2 and S3 are declared, not built: 23.0 m and 28.0 m wide, 15 m long. |
| **Phase 2** | Groundwork in flight: `scripts/geometry/race_lap.py` and the race tools taught a second lap (worktree `wf_25fb3033-882-1`, uncommitted). |
| **Phase 5 tool** | In flight: `tools/stub_roads.py`, `stub_geom.py`, `author_stubs_blend.py` and `verify_stubs.py` (worktree `wf_f07e8864-ebf-1`, uncommitted). Option (a): Phase 1's side streets get barrier stubs from the start. |
| **Data** | `osm.expansion.json` (fresh 2026-10-14) already covers all of Phase 3: its box runs west to −117.115. `route.bbox` [32.76, −117.082, 32.82, −116.998] stops 1.6 km short of Zion's west end. The grown grid's west edge is −117.080708. |
| **Research** | Session scratchpad `p34/{routes3,terrain,aerial,pipeline,routes4,revise}/`. That scratchpad is temporary, so Step 0 copies what the build needs into the workshop, with a provenance note. |

## Steps

Each tool is marked **reused** (as is), **adapted** (opt-in, with the existing network's output byte-identical) or **new**.

### Step 0 — Data (no geometry). Can start now, on a branch off Phase 1's.

1. **Preconditions, for Step 3 only:**
   - Phase 1 merged, installed and driven, including the J2 and J3 pads seat-checked;
   - Phase 2 merged, in your order;
   - for Drive 2, the lighter lamp (D3).
2. **OSM.** Reuse `osm.expansion.json` (osm_base 2026-10-14T10:13Z). If it is more than 7 days old when the build starts, refetch it through `scripts.gps.widths_from_osm._overpass(max_age_days=7)`, with TLS on.
3. **Append a `west` route to `data/routes.json`.**
   - It runs J2 → J6 → J7 → J3 in both directions, with one-way tags respected.
   - Clockwise way lists: Waring 436411990, 436411984, 436411982, 436411988; Zion's 19 ways, 1220464886 … 641705013; Mission Gorge's 20 NE-bound ways, 436411957 … 436424129.
   - Anticlockwise: Waring 436411980, 436411989, 436411987, 436411992; Zion through its median crossovers 641705017 and 641705003; Mission Gorge's 12 SW-bound ways, 436424134 … 436428811. Full lists are in `routes3/analysis3.json`.
   - **It is appended, not regenerated:** `full`, `medium`, `short` and `north` must diff byte-identical.
4. **Config** (`track.config.json`):
   - `route.bbox` west to −117.101, which takes in Zion's west stub at −117.0995 with margin;
   - `route.route_connectors.routes` gains `west`;
   - `terrain.far_extent` west edge per D2 (−117.14);
   - `terrain.grid_grow.cols_w` 26 → **88**, with `tier_options.frame.pin` to match. Rows stay 37/37: I-8's southernmost pavement is 32.7776 N, well inside the grid's south edge at 32.75865.
5. **Grow the 40 m grid again without moving a single old stake.** Think of the ground as survey stakes 40 m apart: growing the grid only adds stakes on the same spacing.
   - **reused** `tools/grow_heightfield.py` adds +62 columns and +10,354 nodes, putting the west edge at −117.107285. That takes about 23 3DEP requests.
   - **reused** `tools/remap_sample_cache.py` re-keys the sample cache. The key shift becomes +1,408 base units in total (88 × 16), up from +416.
6. **3DEP for Phase 3's tiers:** **~177.4k samples in ~395 requests**: 136,687 samples / 304 requests for the tiers in the D2 box, plus ~40.7k / ~91 for the far ring's move to −117.14 (D2), in the same pass. The grid's ~23 requests come on top.
7. **Buildings:** refetch the building cache over the grown box. Today it stops at Phase 1's box.
8. **Stub declaration** (`stub_roads.py declare` on the three pieces). This writes the **30 public stubs, the 5 junction arms (the J6 slip among them) and the 45 curb cuts** (A1, A2).
   - It is cross-checked against `routes3/mouths3.json`, with the slip counted once.
   - The NAIP driveway count for Zion and Grantville is added as authored curb cuts.
9. **Dossier addendum approved.** Your answers to D1–D3 count as approval.

**Done when:**
- the routes diff is clean;
- the grid regrow proof holds: every old node keeps its bit-identical position, and with `cols_w` 26 the tool writes Phase 1's grid byte for byte;
- the cache-remap proof holds: 1,000 random old nodes give byte-identical samples;
- the stub declaration lists every routes3 mouth exactly once;
- nothing installed has changed.

### Step 1 — The readable intermediate (what Claude authors; no mesh yet)

1. **adapted `tools/author_expansion.py`** writes `data/expansion.west.json`, a plain-text description of the new roads:
   - **three road pieces** (Waring J2→J6, Zion J6→J7, Mission Gorge J7→J3), each a centreline at 2–3 m spacing. On the divided roads the centreline is the midline between the two OSM carriageways.
   - per station: the curb offsets (A4), the median polygon and its type (A3), and the paint. That means lane lines and bike lanes on Waring and Mission Gorge; on Zion, the double yellow, the two-way left-turn lane and the centre turn pockets.
   - **the width transitions** at the J2 and J3 ends (23.0 → 28 m on Waring; 28.0 → 33.5 m on Mission Gorge), after a same-station re-read on NAIP (A4).
   - **two new pad outlines**, J6 and J7. Their curb-return radii are measured on NAIP in this step.
   - **two arm conversions**, at J2 (S2) and J3 (S3): the stub's closing piece comes off, and the new piece welds to the same straight cut.
   - the stub arms (A1) and the declared stubs (Step 0).
2. **Profile:** 3DEP 1 m along each piece, node to node.
   - The 11 % cap is checked, not applied blind, and it must bind nowhere. That includes the height blends into J6 and J7.
   - Cross-sections are cut at both pads and over Zion's hill (s 432–660).
3. **adapted** `median_envelope` and `author_median_blend` read the Waring and Mission Gorge islands and the openings. Every existing island stays byte-identical.
4. **Show, don't assert (L12).** `expansion_west_plan.svg` and a PNG over NAIP draw every road, pad, stub, curb cut, median opening and station width, numbered so you can point at things.
5. **A scratch rehearsal on a copy of the workshop**, once Phase 1's P3 has built S2 and S3 (until then, on P3's own rehearsal output).
   - The J2 and J3 arm conversions run through `trim_connectors` → weld → `verify_mouths` → `verify_stubs`.
   - If Phase 2 has merged, the Mission Gorge Speedway's `no_route` runs with probes into Waring SW past J2 and Mission Gorge W past J3 (D1).

**Done when:**
- the plan map shows every piece;
- each centreline lies within 1.5 m of OSM, or of the carriageway midline;
- the J2 and J3 pad outlines are byte-identical to Phase 1's, except the arm's closing piece; every width change lives inside the new piece;
- the rehearsal passes `verify_mouths` on both conversions;
- the Mission Gorge Speedway is still sealed;
- you have the map.

### Step 2 — Ground over the western loop (0046's tiers, extended)

1. **reused `scripts/geometry/terrain_tiers.py`** over the pinned, grown frame.
   - First, the planner's baseline must reproduce Phase 1's **421,917** points exactly (428,118 with the break vertices).
   - Phase 3 then plans **494,052** lattice points: physical 339,596 (+69,939), far 156,025 (+2,412 in the D2 box; about +25.3k more with D2's −117.14 edge).
   - **Those are plan-lattice counts, not what ships.** The build adds the new roads' refine nodes (~+19k at the loop's ~4.3k per km) and the prep's own vertices. On v0.18.0, 357,262 built physical points came from 163,404 planned + 76,926 refine: a ratio of ~1.49. Applied here, Phase 3's built physical ground is **~690k points** (Phase 1's ~556k + ~132k).
2. **The real-ridges clamp is global at 20/40 m** (LAWS L3, as amended in v0.18.0). There is no per-road clause.
   - Done when the re-simulation on fresh transects moves 0 points by more than 1 m beyond 40 m from any pavement.
3. **Cut walls.** The road's own construction zone, 20–40 m out, is shaped to the road; real relief beyond it stays as it is.
   - **Zion s 432–600:** a one-sided cut of 3.7 m within 12–20 m, and 9.1 m within 28–40 m.
   - **Mission Gorge:** a one-sided cut of 4.9 m and a one-sided fill of 5.5 m.
   - If a real wall of 3 m or more is lost over 50 m or more of road, that stretch gets a hand-authored cut slope in Blender (REALISM: lean in, never eject).
4. **The low clause, as Phase 1 restated it:** no terrain vertex more than 2 m below its own 3DEP value. It already covers Mission Gorge's 28.7 m sag; this step checks that it does.
5. **Tiling.** The planner's lattice tiles (8 at the 60,000 split cap, largest 43,299) are not the shipped tiles. The prep's recursive median bisection (`balanced_face_tiles`, `build_kn5_loop.py:190`) splits until every tile is ≤ 60,000, so ~690k built points come out as **~16 physical tiles** (~43k each), against 8 today. Every tile stays ≤ 65,535 by construction; the cost is the longer GrassFX and TreeFX lists (Risk 9).
6. **Preview stills** from four fixed camera stations:
   - Zion s 600, looking west down the hill to the valley;
   - J7, looking north-east up Mission Gorge;
   - Mission Gorge s 1200, under the tall-tree row;
   - J6, looking south down Waring toward I-8 (a preview of Phase 4).

**Done when:**
- tier seams have 0 open edges;
- every mesh is 65,535 points or fewer;
- the loop's ground within 150 m of its roads is unchanged (|Δy| ≤ 0.05 m);
- Phase 1's ground is unchanged, except beside the two converted arms. Those exceptions are listed by name.

### Step 3 — Road and ground build → **Drive 1**

1. **The `ship_sd.sh` draft.**
   - **adapted** `route_connectors` (Phase 1's per-station widths) takes the three pieces.
   - `divide_connectors` passes them through untouched.
   - `stub_roads apply` appends the stubs.
   - `trim_connectors` cuts at the pads, the arm conversions and the stub mouths.
2. **The pads** (`author_junction_pad_blend.py`, from Phase 1):
   - J6 and J7 are built as single-coverage pads, with seams welded to 0.000 m and arc corners with points every 0.6–0.8 m (JUNCTIONS rules 1–6).
   - At J2 and J3, only the arm's closing piece changes.
3. **Stubs and curb cuts** (`author_stubs_blend.py`, Phase 5):
   - curb returns, corner pavement and the K-rail across each stub;
   - `gap_mouths` cuts the host sidewalk at each stub, and `seat_terrain_blend` re-seats the ground;
   - curb cuts drop the curb top at the driveways.
4. **Edges:** curbs, sidewalks and gutters along all three roads (JUNCTIONS rules 9–10).
5. **Paint** as in Step 1.
6. **Mission Gorge Speedway** (D1): its `no_route` and `verify_race` are re-run with the probes. The Lake Murray Speedways need nothing.
7. **`drive_test --line west`** (adapted in Phase 1) sweeps the new roads in both directions. Without it, 4.6 km would never be swept.
8. **The gates** (Verification). `--force-install` is used only under 0047's rule: no key worse than the installed build.

**What you see:** Free Roam with the western loop. You can drive down Zion's hill to Grantville and back up Mission Gorge to Princess View. Every side street reads as a street with a barrier across it. The Speedways look exactly as before.

**Done when:** every Drive-1 gate passes and you have driven it. A DRIVE-TEST-REPORT is filed with the addendum's §10 rows, including the load-time and frame-rate rows.

### Step 4 — Dressing → **Drive 2**

1. **Signs (A8).**
   - **adapted** `place_signs` finds the tight corners on the `west` pieces.
   - `author_signs_blend` writes the plates, and `verify_signs` checks them.
   - The preview is shown to you first.
2. **Lamps (D3).** **adapted** `build_streetlights` (Phase 1's connector-aware version) lays them out with the lighter lamp. Same sodium look as 0043.
3. **Trees (A9).** `make_treefx`, with Phase 1's config surface list and area caps.
4. **Buildings (A10).** The building pass keeps anything within 120 m of any drivable piece.
5. **GrassFX tiles regenerated** at the new tile count (~16 physical).
6. **Map (A12).**

**Done when:** the Drive-2 gates pass and you have driven it.

### Step 5 — Release

`pack_release` builds both packages, as set out in `docs/PUBLISHING.md`. The draft release text gives Free Roam's new length. Publishing is your click.

## Later (not in Phase 3)

These are candidates for you to pick from after Drive 2:
- **Longer Speedways** on the grown network:
  - the outer north loop, 12.23 km: J1 → Waring → J2 → Zion → Mission Gorge → J3 → J4 → Jackson → J5 → Navajo west → J1, skipping Princess View;
  - a grand loop of 20.94 km.

  Zion's 30 mph and 10 % pitch make the western loop a poor race road on its own.
- **Zion west past Mission Gorge toward Friars Rd, and Zion east of Waring.**
- **Phase 4** opens Waring south and Mission Gorge south.

## Tool map

| Tool | Status | Change |
|---|---|---|
| `scripts/gps/widths_from_osm._overpass` | reused | the guarded fetch, only if the cache is stale |
| `tools/route_tracks.py` / `data/routes.json` | adapted (Phase 1) | append `west`; every existing route byte-identical |
| `tools/grow_heightfield.py`, `heightfield.py grid_grow` | reused (Phase 1) | `cols_w` 26 → 88 |
| `terrain_tiers.Frame` pin | reused (Phase 1) | `cols_w` 88 |
| `tools/remap_sample_cache.py` | reused (Phase 1) | +1,408 base units, with the identity proof |
| `tools/author_expansion.py` | adapted | `expansion.west.json`: three pieces, width transitions, two pads, two arm conversions |
| `tools/stub_roads.py`, `stub_geom.py`, `author_stubs_blend.py`, `verify_stubs.py` | reused (Phase 5 tool) | 30 public stubs, 5 junction arms, 45+ curb cuts |
| `terrain_tiers.py` / `terrain_sample.py` (0046) | reused | grown box; the far ring per D2 |
| `route_connectors`, `divide_connectors`, `trim_connectors` | reused (Phase 1 adaptations) | — |
| `author_junction_pad_blend.py` | reused (Phase 1's new tool, not yet written) | J6, J7; arm swap at J2/J3 |
| `median_envelope`, `author_median_blend` | adapted (Phase 1) | Waring and Mission Gorge islands, openings |
| `verify_mouths`, `gap_mouths`, `seat_terrain_blend` | reused | — |
| `barrier_bands`, `no_route`, `verify_race`, `race_lap.py` | reused (Phase 2) | Mission Gorge Speedway probes at J2/J3 (D1) |
| `drive_test --line` | reused (Phase 1) | `--line west` |
| `audit_mesh`, `verify_kn5`, `kn5_ground_check` | reused | `kn5_ground_check` is wired into both chains by Phase 4's first move (it is missing from both today) |
| `place_signs`, `author_signs_blend`, `build_streetlights`, `make_treefx`, `make_map`, building pass | reused (Phase 1 adaptations) | new pieces in config |
| lighter lamp model | **new** (D3) | LIGHTPOST at about 1/10 of its points, network-wide |
| `ship_sd.sh` + `ship_track.sh` | adapted | new steps in both chains |

## Budget

**Starting point:** Phase 1 as projected on the **installed** 116.3 MB, not on the 107.3 MB rehearsal Phase 1's plan started from. That is **125–128 MB** with no Phase-1 lamps and **143–147 MB** with Phase 1's 90 lamps (pipeline lens).

**How built ground is projected here.** On v0.18.0 the physical ground ships 357,262 points from 163,404 planned lattice points + 76,926 refine nodes, a ratio of ~1.49. Ground costs ~56 bytes per built point (44 per point + 6 per triangle, at ~2 triangles per point). So: built = 1.49 × (planned + refine), and size = 56 B × built.

| Phase 3 item | Points | Size |
|---|---|---|
| Road, curbs, sidewalks, paint for 4.60 km | **+42k to +64k**. 42k is the loop's rate of 9.2k per km; the ×1.5 upper bound allows for 27–34 m roads with medians and two pads | +2.1 to +3.2 MB |
| 35 barrier stubs (15 m of road plus a K-rail barrier each) and 45+ curb cuts | small [estimate] | < 1 MB |
| Physical ground | +69.9k planned (269,657 → 339,596) + ~19k refine; built **~+132k**, so **~690k physical in all** (Phase 1 ~556k) | **~+7.4 MB** |
| Far ring | +2.4k (D2 box), or about +27.7k with the −117.14 edge | about +0.1 to +1.5 MB |
| Lamps (D3), ~80 | +324k at today's model, ~+32k with the lighter lamp | **+16 MB**, or ~+1.6 MB lighter |
| Buildings, signs | small | < 0.6 MB |

**The road kn5, honestly.** The 145 MB ceiling is invented.

| After | No new lamps | Every road lit, today's lamp | Every road lit, the lighter lamp (~10×) |
|---|---|---|---|
| Phase 1 | 125–128 MB | 143–147 MB | ~84–87 MB |
| **Phase 3** | **~135–142 MB** | **~169–177 MB** | **~95–102 MB** |

- The pipeline lens's own Phase-3 figure (128–130 MB) counts road only. Adding the ground (~+7.4 MB) and the far ring gives the 135–142 above.
- **Lit at today's lamp, Phase 3 breaks the ceiling by 24–32 MB.** The lighter lamp is the lever: lamps are 57 % of the installed points and 41 % of the file.

**Load time and frame rate. What we know and what we don't:**
- **No frame-rate number exists in this repo, and nothing here measures it.** Your "great" on v0.18.0 is the only baseline. That build is 116.3 MB, 1.70 M points and 244 CSP lights.
- AC loads the whole road kn5 for every layout (L8: one model), so the Speedways also pay for Free Roam's new roads.
- What grows in Phase 3:
  - file size, which roughly tracks load time [not measured];
  - **the drivable ground mesh: from 357k points in 8 tiles today to ~690k in ~16 tiles after Phase 3** (Phase 1 does most of that). It is collision mesh as well as drawn mesh, so it is the second most likely frame cost after lights [not measured];
  - objects: road, stub and building meshes, plus the extra ground tiles;
  - **CSP lights**, from ~334 after Phase 1 to ~414. At night, lights are likelier than points to cost frames [not measured];
  - TreeFX instances, which scale with area.
- **Proposal:** you note load seconds and FPS at three fixed spots (the start line, J3 looking up Princess View, the top of Zion's hill) on v0.18.0 now, and in every drive report after. A drop of 10 % or more [invented] brings the lighter lamp in first, then ground decimation (thinning kept-cell refine away from the roads).
- **Gate time:** `drive_test` costs about 1–3 min per 25 km of swept line. Phase 3 adds about 9.3 km, both directions, so roughly +0.4–1.1 min [estimate].
- **Network:**
  - 3DEP: ~395 tier and far-ring requests plus ~23 for the grid;
  - one buildings fetch;
  - OSM reused.

## Risks

1. **Phase 1's J2/J3 arms not built for a clean swap.** Phase 1's P3 hasn't run and the pad tool doesn't exist yet. If the stub isn't a separate closing piece on a straight arm cut, Phase 3 has to rebuild a pad that has already been seat-checked.
   - Mitigation: ask Phase 1's P3 now to keep S2 and S3 as separate pieces; the Step 1 rehearsal diffs both pad outlines.
2. **Arm widths disagree** (S2 23.0 m vs Waring 28.0 m at s 150; S3 28.0 m vs Mission Gorge 33.5–33.7 m before J3).
   - Mitigation: a same-station NAIP re-read, and the width transition inside the new piece; the pad is never widened.
3. **Zion's 10.2 % is within 0.8 points of the 11 % cap.** A junction blend can push it past.
   - Mitigation: the cap is checked, including the blends, and never applied blind. Where it would bind, the blend is shortened, not the hill cut.
4. **The Mission Gorge Speedway's seal** depends on D1 being built into Phase 2.
   - Mitigation: probes past J2 and J3 in Phase 2's own `no_route`.
5. **Lamps.** See Budget. Without the lighter lamp, Phase 3 is either unlit or over the ceiling.
6. **Unmapped driveways.** OSM maps only 12 service mouths on Zion and 33 on Mission Gorge.
   - Mitigation: a NAIP count in Step 0, Street View later.
7. **Regrowing the grid a second time.** A careless regrow shifts every ground point.
   - Mitigation: the same whole-cell growth, pin and remap proof as Phase 1.
8. **`1KERB_sidewalk` is at 55,021 of 65,535 points (84 %).** The prep does not fail on it outright: `_split_large` (`build_kn5_loop.py:670`) cuts any non-ground mesh over 60,000 into equal-width bands along its longest axis. The real risk is that the bands are uneven in points, and a dense band over 65,535 makes the prep refuse to export (its FATAL check).
   - Mitigation: print band counts in Step 3; split curbs by piece if a band comes near the cap.
9. **Tile counts.** ~16 physical ground tiles instead of 8 lengthen the GrassFX lists and press on the TreeFX caps.
   - Mitigation: the built tile count is printed in Step 2 and the GrassFX list regenerated in Step 4.
10. **The aerial is from April 2022.** Paint, medians or shops may have changed since.
    - Mitigation: a Street View pass before Drive 1.
11. **Chain drift between `ship_sd` and `ship_track`.**
    - Mitigation: A13.
12. **Regenerating `routes.json`** would re-route full, medium, short and north.
    - Mitigation: append only, with a byte diff.

## Not in this plan

- Phase 4: Waring south of Zion, Mission Gorge south of Zion, I-8 and the ramps. They are stubs here.
- Any race layout on the western roads, and any change to the Lake Murray Speedways.
- Zion east of Waring, Zion west of Mission Gorge, Greenbrier, and every side street beyond its 15 m stub.
- Phase 5 proper: converting the old loop's side streets.
- AI on the new roads, working signals, live traffic.
- 0040's species pass beyond the zones and the Gum row.

## Verification (decided now, before any geometry)

Everything runs on the **built** file (L5), against data that did not place it: OSM, NAIP and 3DEP.

| # | Check | Threshold |
|---|---|---|
| **V1 Plan** | Built centreline vs OSM, or the carriageway midline | p95 ≤ 1.5 m [invented] |
| | Curb to curb at the aerial stations (A4) | ±1.5 m of the eye reading [invented]; the transition stretches at J2/J3 excluded and listed |
| | Medians | Waring planted 2.5–5.5 m; Mission Gorge terracotta with 5 open gaps; Zion none, with the two-way left-turn lane at s ~900–1050 |
| **V2 Profile** | Built new roads vs 3DEP | p95 ≤ 0.5 m [invented in 0048] |
| | Heights | J6 99.7, J7 33.8 and Waring crest 106.6 (± 1 m, within 20 m of s 400); Mission Gorge sag 28.7 ± 1 m at s 300–400 |
| | Zion max grade | 10.1–10.2 % ± 0.5 at s 570–660 |
| | Grade cap (11 %) | binds nowhere, blends included |
| | J2 / J3 | the new road meets Phase 1's **unmoved** pads; weld seams 0.000 m |
| **V3 Pads, mouths, stubs** | Pads J6/J7 | multi-coverage 0 m²; seam gap ≤ 10 mm |
| | `verify_mouths` | PASS at J2/J3 and every stub; every existing mouth unchanged |
| | `verify_stubs` S1–S8 | PASS on all 35 stubs and every curb cut |
| **V4 Layouts** | Lake Murray Speedway / Reverse | `race_authored`, zones, closures, AI and spawns byte-identical to the installed build |
| | Mission Gorge Speedway | `no_route` PASS, with probes past J2 (Waring SW) and J3 (Mission Gorge W) |
| **V5 Existing roads no worse** | `drive_test`, `audit_mesh`, `verify_kn5`, `kn5_ground_check` on every layout | no key worse [std: 0047] |
| **V6 New roads** | `drive_test --line west`, both directions | obstructions, floating furniture and undrivable spots 0 [std]; severe steps 0 [invented]; soft-top ≤ 6.1/km and kinks ≤ 4.97/km [invented, the loop's rate] |
| **V7 Ground** | Real-ridges clamp | 0 points moved > 1 m beyond 40 m |
| | Cut walls (Zion s 432–600, Mission Gorge) | no stretch ≥ 50 m with a real wall ≥ 3 m lost |
| | Low clause | no vertex > 2 m below its own 3DEP |
| | Far cells (the only check that reads the far ring) | within 1 m of 3DEP |
| | Tier seams | 0 open edges |
| **V8 Format** | Every mesh, ground tiles and banded meshes included | ≤ 65,535 points [std: AC] |
| | Road kn5 | ≤ 145 MB [invented] |
| **V9 Signs** | `verify_signs` | PASS; ~8 new arrows; 0 sign bases on pavement |
| **V10 Trees** | TreeFX checks | PASS; loop verge density within ±5 % [invented] |
| **V11 Your seat** | Two DRIVE-TEST-REPORTs with the addendum's §10 rows | the only verdict that closes Phase 3 |

**Drive 1 is gated on V1–V8. V9 and V10 gate Drive 2.**

## First three moves after approval

1. **Now:**
   - ask Phase 1's P3 to build S2 and S3 as separate closing pieces on straight arm cuts (A5), and re-read their widths at the arm;
   - on a branch off Phase 1's (Step 0): the appended `west` route with its diff; the config; the grid regrow to 88 with the identity proofs; the 3DEP (with the far-ring move) and buildings fetches; the stub declaration.

   No geometry.
2. **The readable intermediate and the numbered plan map** (Step 1). D1 goes to the Phase 2 work in flight today, so its seals are designed in.
3. **The ground planner on a scratch copy** (Step 2): the baseline reproduced first, then the Phase 3 numbers and the built tile projection. In parallel, the lighter lamp model (D3) and your v0.18.0 frame-rate baseline. Step 3 starts once Phase 1 is installed and driven, and Phase 2 is merged.

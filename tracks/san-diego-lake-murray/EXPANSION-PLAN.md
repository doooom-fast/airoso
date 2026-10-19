# Lake Murray network expansion: Phase 1 build plan

> **2026-10-13, revision 2. This is a plan only. Nothing is built yet** (committed as the plan of record). Kevin answered D1–D4 on 2026-10-13 (ledger 0054). P0, the data with no geometry, was done on a branch on 2026-10-14 (see P0). P1, the readable intermediate, the numbered map and the J1 / J5 weld rehearsal, followed the same day (see P1), and P2, the ground over the expansion (see P2).
> - The ledger entry is [0054](../../fleet/feedback/0054-lake-murray-network-expansion-waring-mission-gorge-jackson.md). The place facts are in the dossier addendum, [`DOSSIER-EXPANSION-NORTH.md`](DOSSIER-EXPANSION-NORTH.md).
> - The research ran on 2026-10-12/13 and was read-only on the repo, the workshop and the AC folder. It lives in the session scratchpad `expansion/`, in four lenses plus a revise pass:
>   - **routes:** fresh OSM, as of 2026-10-12T18:03Z, from the primary Overpass server with TLS verified;
>   - **terrain:** USGS 3DEP 1 m, plus the 0046 planner run read-only;
>   - **aerial:** NAIP 2022-04-25 at 0.6 m;
>   - **pipeline:** the chain, file by file;
>   - **revise** (`expansion/revise/`): node-to-node 3DEP profiles, the mouth extents on the loop's outer curb, and the clamp re-simulation.
> - **Stations.** Every station in this plan is in metres from the junction node at the start of the leg, in drive order J1→J5, measured along the routes lens's OSM legs.
>   - The terrain lens measured legs that start 50–95 m after each node, so its stations have been shifted by that amount to match.
>   - The aerial stations match these to within about 20 m.
> - The plan follows the shape of the shelved Lariat plan (`tracks/lookout-lariat/V3-PLAN.md`).
> - **Order:** the build waits for **v0.18.x** to be merged, installed and driven. v0.18.x is ledger 0046's terrain plus the seat fixes 0050–0053. Data and rehearsal work can start sooner, on a branch (P0).
>
> Kevin, 2026-10-12, verbatim:
> - *"we're going to expand college down waring to princess. view, princess view to mission gorge, and mission gorge to jackson, then extend jackson down to mission gorge. we'll add to the network map instead of building the lariat."*
> - *"the new loop will connect to the old one"*
> - *"this will be called lake murray free roam vs the lake murray speedways … we may add mission gorge speedway etc"*

## The short version

- **Your roads exist exactly as you described them, and together they make a loop.** Read phrase by phrase, from the corner each one starts at:

  | Your words | Road | From → to |
  |---|---|---|
  | "college down waring to princess view" | **Waring Rd** | the College/Navajo corner (J1) → Princess View Dr (J2). College runs straight on into Waring here. |
  | "princess view to mission gorge" | **Princess View Dr** | J2 → J3, downhill all the way |
  | "mission gorge to jackson" | **Mission Gorge Rd** | J3 → J4, east up the river valley |
  | "extend jackson down to mission gorge" | **Jackson Dr north** | the Navajo/Jackson corner (J5) → J4, downhill from the Navajo end |

  - Every connection exists as you said it, so there is no alternative to choose.
  - Jackson stops at Mission Gorge. North of that corner there is only the park entrance.
  - All five junctions (J1–J5) are real signalised intersections.
  - Driving from College, every turn on the new loop is a right turn, so it runs clockwise, the same way as the Speedway.
- **6.36 km of new road, measured junction node to junction node:**

  | Road | Length | What it is |
  |---|---|---|
  | Waring Rd | 0.98 km | divided boulevard with a planted median; drops 21 m |
  | Princess View Dr | 1.11 km | 4–5 lanes; the steepest road on the network, falling 70 m at up to 10.4 % |
  | Mission Gorge Rd | 2.27 km | divided 55 mph arterial with a red-tinted raised median, over a 114 m crest |
  | Jackson Dr north | 2.00 km | climbs 118 m up a canyon with no dip, to the Navajo crest at 210 m |

  - There are no bridges, no river crossings and no freeway.
  - The San Diego River runs 248–580 m north of the route and is never crossed.
- **It joins the loop only at the two corners it already has**: the race boxes v1506–1521 (J1) and v2311–2328 (J5). The installed lap does not move by a single point.
  - **Lake Murray Free Roam** becomes the whole network: about 24 km of drivable road, against 17.9 km today.
  - **Lake Murray Speedway** and **Speedway Reverse** keep their exact laps. The two new road openings are sealed, like every other side street.
- **The ground grows with the roads.** The 0046 terrain is extended north over the river valley. That terrain is detailed ground near the roads plus a far ring you can see but not drive on.
  - The extension brings in the gorge walls. On the south side that is the slope up to Cowles; on the north, the Mission Trails peaks (Pyles, Kwaay Paay, the Fortunas).
  - Climbing Jackson, Cowles fills the windscreen at 9.4–9.8° above the eye. That is as big as the Navajo-crest view you asked for in 0046.
- **No new race layout in Phase 1.** A *Mission Gorge Speedway* (8.72 km: the new roads plus Navajo) is Phase 2. It needs one piece of machinery first, because today every race tool can follow only one lap line.
- **Two drives:**
  - Drive 1: the roads, the junctions and the ground.
  - Drive 2: the signs, lamps, trees and buildings.

## Decisions for Kevin

**There are four questions, ordered by what they hold up.** For D1, D2 and D4, the answer "defaults" is complete, and the build goes ahead on the default if you don't answer. **D3 changes one of your laws (L3), so it needs an explicit yes.** Typing "defaults" counts as that yes; silence does not. Only one step waits on it, the P2 terrain build. Everything else goes ahead.

| # | Question | Default | Why |
|---|---|---|---|
| **D1** | **A race layout on the new roads now?** | **No. Phase 1 grows Free Roam only, and both Speedways keep their laps.** A *Mission Gorge Speedway* (+ Reverse) is Phase 2: either the 8.72 km north loop or a 17.43 km grand loop. | Every race tool reads exactly one lap line and counts along it by point number. That covers the corridors, closures, start grids, AI and `no_route`. A second lap needs that generalised first, which is the largest single job here. It should not hold up driving the roads. Holds up: P1 scope (connector vs mainline). |
| **D2** | **How far do the views reach?** The far ring stops at 32.822 N today. Think of it as a painted backdrop that is the real shape of the land. From the new roads, 26 % of the skyline lies outside it. To the north the missing peaks stand up to 9.4° above the eye: Pyles 420 m, Kwaay Paay 364 m, North Fortuna 393.5 m. To the west there is only a low mesa across Mission Valley, at 2.3° or less. | **Grow the far ring north to 32.850 and west to −117.108. Grow the detailed Cowles patch north to 32.828 so Pyles is drawn properly.** That costs about +33k see-only ground points. No separate detailed patch for Mission Trails. | It is the real skyline of the gorge, and it is cheap: none of it is physical, and the driving gates never check it. Without it, the view north from Mission Gorge and Jackson ends at an edge. Holds up: the P0 config and the P2 sampling. |
| **D3** | **The ground beside the two canyon roads. This is a change to law L3, which needs your yes.** The 0046 rule irons the ground near any road to within 22 m of the road's height. The iron works in full out to 80 m and lets go by 250 m. That rule was tuned on the flat loop. Jackson north and east Mission Gorge are cut into hillsides, with real walls 3–11 m high and a ridge 30–50 m above Jackson. Under the rule as written, that ridge is planed down by up to **24.3 m** and the canyon on the other side is filled by up to **11.6 m**. Mission Gorge loses up to 6.3 m. That is 506 transect points moved by more than 1 m. | **On Jackson north and Mission Gorge, the iron reaches 40 m from the pavement. Past that, the ground is the survey data.** In L3 this is one more clause: the reach can be set per road, and these two roads use 40 m. | Re-simulated on the same fresh 3DEP transects (`revise/clamp_options.py`), the rule then moves **0** points on those two roads. Within 40 m of their pavement, the real ground is never more than 22 m from the road (0 of 4,050 points), so the iron never bites there and there is no seam where it stops. The rule exists to stop fake mountains looming over a neighbourhood. These walls are real, and Jackson without its canyon walls would not be Jackson Dr. Holds up: P2's terrain build only. |
| **D4** | **Streetlights on the new roads.** Each lamp is heavy: 4,045 points in the track file. Lighting all 6.36 km at the loop's spacing (17.7 per km) is about 113 lamps and about +23 MB, in a file every layout loads. | **Light everything except Jackson's open canyon (D 250–1500, about 1.25 km).** That is about 90 lamps and about +18 MB. Mission Gorge is lit along its whole length: its river stretch has apartment blocks on the south side (C 500–1000). This stays labelled *authored* until a Street View night check shows where the real lamps stand. | You liked the 80s sodium night (0043). An unlit canyon with houses only on its rims is the usual real pattern, but it is **not verified here yet**. If the file grows too big, the fallback is a lighter lamp model (see Budget). Holds up: P4. |

### Defaults I will apply unless you say otherwise

- **A1. Exactly your four roads, and nothing else drivable.**
  - **Side streets along them** are handled the way the installed loop handles side streets that aren't in your routes: the curb and sidewalk run straight past. There are 24 public streets and about 28 mapped service drives.
  - **The real other arms of J2, J3 and J4** each get a short see-only stub: a curb return, a little pavement, and an invisible wall across the mouth line (JUNCTIONS rule 18c). The arms are:
    - at J2: Mound Ave, and Waring beyond Princess View;
    - at J3: Mission Gorge west, and the quarry drive (OSM calls it "Tierrasanta Boulevard (Proposed)"; the aerial shows a 12 m industrial driveway);
    - at J4: Mission Gorge east, and the visitor-centre entrance.
  - Each corner then reads as a real crossroads, but you can't drive off the network.
- **A2. Medians.** The divided roads are built as **one pavement with the real median standing on it**. This is how the College/Navajo islands are built (JUNCTIONS rule 12: an island stands on continuous pavement), and it avoids the banned "two carriageways with no junction model" (0035/0037).
  - **Waring:** planted raised median, 1.5–6 m wide, with trees at st 250–550.
  - **Mission Gorge:** terracotta raised median, 1.5–8 m wide.
  - **Princess View:** undivided, with a double yellow line and a short raised nose at Fontaine St (st ~500–557).
  - **Jackson north:** undivided, with a painted double-double-yellow median. On its last ~180 m into J4, OSM maps it as two one-way ways, about 12 m apart (436413311 one way; 436413304/1076791040/436413294 the other). The aerial shows a **painted, hatched** 3–4 m median there, not an island. It is built as one pavement with that hatch, running into the J4 pad.
- **A3. Real widths, curb to curb, from the aerial, varying along the road.** These are eye readings at 30 stations on 0.3 m zooms with a 10 m grid:

  | Road | Width (m) | Median (m) |
  |---|---|---|
  | Waring | 24.0–27.5 | 1.5–6 |
  | Princess View | 22.5–28.0 | — |
  | Mission Gorge | 27.5–33.0 | 1.5–8 |
  | Jackson north | 17.0–26.0 (narrowest at Hemingway Dr, st 500) | painted, up to 4.5 |

  - The connector tool's fixed 10 m width is not used.
  - The automatic width walker isn't used either: it drops a whole carriageway on Princess View and Jackson.
- **A4. Two kinds of junction.**
  - **J2, J3 and J4 (the new corners) get an authored junction pad.** Think of one rug of asphalt poured under the whole crossroads, instead of two strips of tape laid over each other. A 23–33 m wide road can't simply bend 74–84° around a 6–12 m curb corner: its inside edge would crumple over itself, like a belt folded too sharply.
    - Each pad gets true-arc corners at the measured curb-return radii:

      | Corner | Radius (m) |
      |---|---|
      | J2 | 6–8 |
      | J3, SW | 10–12 |
      | J3, SE | 5–6 |
      | J4, south side | 8–10 |
      | J4, north side | 6 |

    - The road strips end at straight cuts welded to the pad (JUNCTIONS rules 2–5).
    - The J4 pad sits at the foot of Jackson's climb: 7.5 % within the first 100 m.
  - **J1 and J5 (the loop corners) use ribbon-through instead, which is a deliberate exception to JUNCTIONS rule 2.** Ribbon-through means the loop's road runs through the corner completely unchanged, and the new road is a separate, fully drivable piece welded seam-tight onto its outer curb.
    - Rule 2 asks for a pad wherever cars turn. Rule 2 also allows ribbon-through when one road owns priority, and here the loop is "the track" for both Speedways.
    - A pad at J1 or J5 would cut the mainline ribbon. That would move the lap, the race boxes, the closure runs and the start, sector and sign vertices. At J5 it would also redo the corner fan that 0050 has just fixed.
    - In Free Roam you can still drive through in every direction, College→Waring straight on included, which is what 0054 asks for.
    - Phase 2 revisits this: when a Mission Gorge Speedway drives straight through J1 and J5, those two corners become pads.
- **A5. How big the two openings on the loop's outer curb really are** (measured, `revise/mouth_sides.py`).

  | | J1 Waring | J5 Jackson north |
  |---|---|---|
  | Junction shape | **a Y with three arms**, not a four-way. College→Waring is the straight line; Navajo branches north-east. | a real four-way |
  | Where it opens | Waring's SW curb meets the loop's outer curb at **v1514** | Jackson north's SW curb meets the loop's outer curb at **v2314.8** |
  | Corner return | Waring's NE curb meets it at v1520.6, then sweeps round onto Navajo on its R ≈ 30 ± 10 m free-flow return, ending at **v1528.5** (R 20–40 gives v1525.7–1531.6) | its R 8–12 m return ends at **v2312**. The NE side runs on as Jackson south's east curb, within 1 m of it from v2321–2323. |
  | Opening on the outer curb | **v1513.5 → ~v1528.5**, about 52 m | **v2312 → ~v2322**, the whole outside of the corner |
  | Against the race box | **the last ~7 vertices (~25 m) lie past box end v1521**, in race_cw's exit funnel | entirely inside box 2311–2328, apex 2319 included |

  At J1, the wedge between Waring and Navajo stays planted ground.
- **A6. Real height, real grades** (3DEP 1 m, node to node, `revise/measure.json`).

  | Point | Height (m) |
  |---|---|
  | J1 | 124.9 (the loop there sits at 125.1–125.3) |
  | J2 | 103.9 |
  | J3 | 33.4, the lowest point on the network |
  | Mission Gorge crest | 114.3, at s ≈ 1460 (32.8121, −117.0657) |
  | J4 | 92.4 |
  | J5 | 209.9 (the loop there sits at 209.2–210.2; 209.7 at v2318) |

  - The connector grade cap stays at 11 %. Princess View's steepest is 10.2 % downhill and 10.4 % uphill, so the cap should never bite, and a gate proves it doesn't.
  - There are no bridges, so there are no bridge decks to hold level.
  - The new roads meet the loop at the loop's own height. The loop is never moved to meet them.
- **A7. The three existing layouts.**
  - **The mainline isn't touched.** Race boxes, closure runs, starts, signs, kerbs and AI are all counted along it by point number.
  - **The Speedways' seals.**
    - Each new opening is one mouth, assigned to its race box by where the new road's centreline crosses the outer curb: about v1517.4 at J1, about v2317.7 at J5.
    - Speedway (race_cw) seals them as "sealed_far_strip". Speedway Reverse (race_acw) seals them as "sealed_race_strip". The race tools already handle a mouth inside an open box.
    - At J1, about 25 m of the opening runs past the box into race_cw's exit funnel (v1521–1528.5). The curb strip already runs unbroken along that whole edge (edge_gaps none), so the furniture there doesn't change. The P1 rehearsal runs `barrier_bands`' validation and `no_route` with one probe placed past v1521.
    - If the validator rejects a mouth that crosses the pin, the fix is to split its policy at v1521: the box part stays "sealed_far_strip", and the funnel part becomes "behind_closure" for race_cw. That is a small `barrier_bands` change, made only if needed.
  - **Race kerbs: the two outside kerbs at these corners are dropped, using `race.kerbs.trims`' existing drop.** They are apex 1514 L (v1507–1520) and apex 2319 L (v2312–2327).
    - At J5 the opening covers the apex, so only a 14 m exit stub would be left.
    - At J1 the kerb would stop exactly where Waring opens.
    - A kerb that ends at a road opening reads wrong. The inside kerbs at both corners stay.
  - **Signs M3 (College→Navajo) and M4 (Navajo→Jackson): you approved both, and both now stand inside new pavement.** M3's base is 1.7 m from Waring's line; M4's is 9.5 m from Jackson north's.
    - In Free Roam, straight on at those corners is now a real road, so a turn arrow there would point you away from it.
    - Default: **both move into the Speedways' own race files**. They stand where you approved them, just past the outside edge, now on the sealed opening.
    - Free Roam drops them. Any 0051 reverse-direction plate that ends up standing in a new opening gets the same treatment.
    - Drive 1 asks whether that reads right.
  - **Lamp #77** (its head 8.8 m from Waring's line, inside the new road) moves behind the new curb.
- **A8. Signs on the new roads.**
  - **Corner arrows by your 0044 rule** ("tight corners", at the corner, just past the outside edge, facing the approach). The tight corners here are J2, J3 and J4, in both directions per 0051, so 6 plates.
  - Where the outside of a turn is a stub (A1), the plate stands behind the stub's wall.
  - The sign preview is shown to you before the build, as in 0044.
  - **Speed limits where OSM has them:** Waring 35/40 mph, Mission Gorge 55 mph. None on Princess View or Jackson until Street View gives the real limits.
  - **No signal heads.** The loop has none either.
- **A9. Trees, by zone, not one uniform mix (the 0040 rule).**

  | Zone | Planting |
  |---|---|
  | Open slopes (Jackson's canyon, the gorge sides) | chaparral and coastal sage scrub: Sage, Yucca, Bush, Agave |
  | North of Mission Gorge, C 300–1200 | riparian woodland, using Sycamore V1/V2 and Oak3 as stand-ins for willow, cottonwood and sycamore |
  | Waring's median | small median trees |
  | The canyon | no palms |

  - **Eucalyptus (your later 0040 request).** The one strong candidate is a belt of tall grey-green trees on the north-east side of Jackson's canyon (D ~1000–1400, about 32.810, −117.051). They cast shadows about 20 m long, the tallest trees on any leg. The installed Gum model goes there. NAIP can't confirm the species, so Street View checks it.
  - **Flowering shrubs (0040).** Each zone carries a flowering-shrub slot, so 0040's species pass can fill it later without re-laying anything.
  - **Tree caps scale with area.** Today 3,500 trees and 9,000 bushes are thinned evenly over everything, so adding area would otherwise thin the loop's own verges.
- **A10. Buildings** from OSM footprints within 120 m of the new roads, as on the loop:
  - Grantville industry and self-storage;
  - the Margerum retail strip and apartments;
  - houses on the canyon rims;
  - the shops at Navajo/Jackson.

  The quarry north of J3 is ground, not a building: 3DEP has its terraces.
- **A11. No AI on the new roads.** AC's AI follows one line, and Free Roam's line stays on the loop. AI lines are never generated from GPS. The Phase-2 Speedway gets its AI the same way the existing ones did.
- **A12. Map.** Free Roam's map shows the whole network. Each Speedway's map shows only its own lap, so it doesn't shrink 1.21× to fit 6 km of road it can't use. `make_map` gets an opt-in per-layout filter.
- **A13. Chain.** The work lands in `tools/ship_sd.sh` (the SD chain of record) and in `ship_track.sh`'s vocabulary in the same change. The 0046 branch has already re-synced the two (d966817), so after the merge the parity test must be green, and it stays green.
- **A14. Versions.**
  - Drive 1 is v0.19.0: roads, junctions, ground and far views.
  - Drive 2 is v0.19.x: signs, lamps, trees and buildings.
  - Packaging follows `docs/PUBLISHING.md`. Publishing is your click.

**Asked later, not now:**
- the speed limits on Princess View and Jackson (after Street View);
- the real lamp positions (after the night check);
- whether the Speedways want M3/M4 kept (Drive 1);
- which Phase-2 item comes first (after Drive 2).

## Where it stands today

| | State |
|---|---|
| **Installed** | v0.17.1: a 13.48 km loop plus 4.41 km of connectors, in three layouts: Free Roam (`street`), Speedway (`race_cw`) and Speedway Reverse (`race_acw`). Road kn5 is 92.5 MB with 1,268,240 positions; 1GRASS_0 is at 64,572 of 65,535. DoD **T2**. |
| **In flight** | v0.18.x, on branch `worktree-wf_b291cd05-e2e-1` at 4d20681. It holds the 0046 terrain: the rehearsal road kn5 is 107.3 MB, with physical ground at 236,771 points in 4 tiles and the far ring at 106,557 in 2. It already carries balanced tiling in its engine-july snapshot (`balanced_face_tiles`, build_kn5_loop.py:181) and the ship_sd/ship_track re-sync. Also in flight are the seat fixes 0050 (Navajo/Jackson steps, **the box Jackson north joins**), 0051, 0052 and 0053. |
| **Data** | `route.bbox` [32.76, −117.075, 32.808, −116.998] stops short of Princess View and Mission Gorge. `data/osm.json` dates from 2026-08-10. The v021 40 m heightfield [32.771983, −117.069563, 32.805287, −117.017103] misses 2,187 of the 2,312 expansion points, and `heightfield.py` can't grow it today (P0 step 6). |
| **Research** | In the session scratchpad `expansion/{routes,terrain,aerial,pipeline,revise}/`. That scratchpad is temporary, so P0 copies what the build needs into the workshop with a provenance note. |

## Phases

Each tool is marked **reused** (as-is), **adapted** (opt-in; the existing loop's output stays byte-identical) or **new**.

### P0 — Preconditions and data (no geometry)

> **2026-10-14: steps 2–7 done on branch `worktree-wf_c6ab4b42-146-1` (off 4a9e66f, v0.18.0 installed). Not merged. Details and numbers are in ledger 0054, "P0".**
> - **Step 2:** the parity tests are green.
> - **Step 3:** `osm.expansion.json` was fetched under the 7-day guard. The guard passed over a mirror that was 78 days stale.
> - **Step 4:** `north` is appended to routes.json. `full` / `medium` / `short` are byte-identical.
> - **Step 5:** the config changes are made. `north` is *held* through `route_connectors.authored_routes`, so no 10 m connector is drawn from it before P1/P3.
> - **Step 6:** `grid_grow` 37/37/26, the frame pin (offsets 0, live) and `tools/remap_sample_cache.py` are proven, and no extra rows are needed. The grown heightfield, the pin's 37/26 and the re-keyed cache are **held for P2, to land in one change**.
> - **Step 7:** buildings were refetched into `buildings.expansion.cache.json`. The installed `buildings.cache.json` is untouched.
> - **Research:** copied into `source/expansion/` with provenance.
> - **New for P2:**
>   - the D2 far ring plans 139,483 vertices;
>   - 34,852 3DEP samples are missing;
>   - the I-8 corridor file is rebuilt online, because it is keyed on the far box.
> - **Still owed:** step 1, your seat on 0050.

Steps 2–8 can start now on a branch off the 0046 branch, and get rebased after the merge. Only P3 waits for step 1.

1. **v0.18.x is merged and installed, and the 0050 Navajo/Jackson steps are confirmed fixed in your seat.** Jackson north's opening lands in that box, so the expansion must start from the fixed box.
2. **The ship_sd/ship_track parity test is green after the merge.**
3. **Fresh OSM, guarded.**
   - Fetch bbox S 32.755 / W −117.115 / N 32.850 / E −116.985 through `scripts.gps.widths_from_osm._overpass(max_age_days=7)`, with TLS verification on.
   - `tools/fetch_osm.py` falls back to mirrors with **no** staleness check (lines 37–68). It gets the same 7-day guard, or it isn't used.
4. **Append a `north` route to airoso `data/routes.json`.**
   - It runs J1 → Waring → Princess View → Mission Gorge → Jackson → J5 in both directions, respecting one-way tags. The way lists are in the routes lens's `routes_analysis.json`.
   - It is appended, not regenerated: `full`, `medium` and `short` must diff byte-identical.
5. **Config changes** (`tracks/san-diego-lake-murray/track.config.json`):
   - `route.bbox` grows to at least N 32.820 / W −117.082;
   - `route.route_connectors.routes` gains `north`;
   - the terrain `far_extent` becomes [32.755, −117.108, 32.850, −116.998] (D2);
   - the `cowles_mountain` include's north edge moves to 32.828 (D2);
   - ~~the sidehill clamp is set per road, written in but held until D3 is answered.~~ Not needed. D3 was settled by v0.18.0's global `clamp_corridor_m` 20 / `clamp_blend_m` 40, which moves 0 real points on every expansion road (ledger 0054).
6. **Grow the 40 m heightfield without moving a single old stake.** Think of the ground as survey stakes 40 m apart. Growing it must add stakes on the same spacing; if the grid's anchor moves, every old stake shifts.
   - **adapted `scripts-v021/elevation/heightfield.py`.** Today `build_heightfield` sizes the grid from the loop's own bbox plus 150 m (`:98-115`). No code anywhere reads an extent key: the only mention is the comment at `:189-192`. The change is a new opt-in `terrain.grid_grow` key (`{rows_n, rows_s, cols_w, cols_e}`, whole cells).
   - **How the new grid is laid out.**
     - The latitude, `gx` and `gy` still come from the loop's own points, so every old node keeps its exact position.
     - The default growth is **+37 rows north, +37 rows south and +26 columns west**. That gives [32.758650, −117.080708, 32.818620, −117.017103] and 24,883 nodes.
     - Growing north and south equally also keeps the meta bbox's mid-latitude where it was.
     - The grid must cover every *kept* near-road cell. Those reach about 18 m past each pavement, and the furthest is about 32.8174 N near J4. P2's planner checks this, and adds another north/south pair if any kept vertex falls outside.
   - **The 0046 lattice frame gets pinned** (adapted `terrain_tiers.Frame`, opt-in `tier_options.frame.pin`).
     - The frame is anchored on the installed meta's *rounded* bbox. A regrown meta, rounded to 6 decimals again, could move it by up to ~5 cm.
     - The pin stores the installed rounded anchor plus whole-cell offsets, at full precision, so neither the growth nor the rounding moves it.
   - **The 3DEP sample cache** (`terrain.samples.json.gz`) is re-keyed by those whole-cell offsets with a one-off **new** `tools/remap_sample_cache.py`.
     - Proof: 1,000 random old nodes keep their positions to 1e-9° and give byte-identical samples.
     - The alternative, a naive regrowth, moves the mid-latitude by +0.0065°. Nodes 5 km east would drift 0.37 m, and all ~360k samples (~800 requests) would be fetched again.
7. **Buildings:** refetch the OSM building cache over the new bbox. Today it stops at 32.808 N.
8. **Dossier addendum approved.** Your answers to D1–D4 count as approval.

**Done when:**
- steps 1–8 hold;
- the routes diff is clean;
- the remap proof is identical;
- with `grid_grow` absent, `heightfield.py` writes today's grid byte-for-byte;
- nothing in the installed build has changed.

### P1 — The readable intermediate (what Claude authors; no mesh yet)

> **2026-10-14: done on branch `worktree-wf_c6ab4b42-146-1` (steps 1, 2, 4, 5; step 3 moves to P3). Not merged. Details in ledger 0054, "P1".**
> - **The intermediate:** `data/expansion.north.json` (`tools/author_expansion.py`): 4 pieces within 0.11 m p95 of the OSM midline, 38 width stations at their eye widths, 9 median runs, pads J2-J4, stubs S1-S6, welds W1 / W5. The 11 % cap binds nowhere; Princess View -10.3 %, the crest 114.5 m at s 1460.
> - **The map:** `data/expansion_plan.svg` + a PNG over NAIP 2022 (`tools/plot_expansion_plan.py`).
> - **The rehearsal** (full chain, scratch copy, `p1-proofs/rehearsal_delta.py`):
>   - **J5** welds and seals in both Speedways; opening v2313.5-v2320.9, inside the box. Its verify_mouths fails only on 11 grass samples under the loop's centreline at v2311-2313 that v0.18.0 already has (0050's corner ground): fix at the source in P3.
>   - **J1** welds with Waring's straight curbs (opening v1514.1-v1520.4). **The R ≈ 30 m free-flow return cannot be welded by a connector ribbon** (its end would stand 2.9-4 cm proud of the loop; the gates allow 2 cm): it is **apron AP1** (v1520.4-v1526.3, 118 m²), authored in P3. A4 / A5 stand otherwise.
>   - **A7's split happened** (race_cw: far strip to the pin v1521, behind the closure past it). `no_route` PASS on both Speedways, planned and built, with probes past v1521.
>   - **The existing three layouts are no worse, key for key.**
>
> **2026-10-14, P1 fix round** (the verifier refuted P1; ledger 0054 "P1 fix round"): every failing check fixed at its
> cause, opt-in, and the full chain re-run on a fresh scratch copy to its end.
> - **Both new mouths pass verify_mouths.** J5's grass was the ground's 4.5 m triangles across the 0050 fan's crease
>   (now 0.75 m under an exact-deck mouth's lane) and a second road surface within 2 cm of the loop's: `route.mouth_fill`
>   now starts each new road exactly at the loop's own edge (0 overlapping surfaces; J5 had 2.55 m).
> - **J1's R 30 return is built: apron AP1** (`route.aprons`, `tools/author_aprons_blend.py`), to v1526.3 with its own
>   curb and walk; the loop's walk resumes at v1527; lamp 77 behind the new curb; no curb gap, no shelf-edge cliff.
>   Waring's first 70 m now stay within the 11 % cap (`route.trim_blend_grade_cap`; it fell 14.8 % in 30 m).
> - **No step over 6 cm at J5 in any layout** on the real wheel paths; drive_test's backwards fixed-offset readings
>   inside the levelled fans go to verify_fold_fans (`drive_test.fold_fan_severe`). Severe by v0.18.0's rule: 22 / 20,
>   unchanged.
> - M3 / M4 are skipped in all three layouts until P4 (correcting P1's "Free Roam only").

1. **new `tools/author_expansion.py`** writes `data/expansion.north.json`, a plain-text description of the new network:
   - **four road pieces** (Waring, Princess View, Mission Gorge, Jackson north), each a centreline at 2–3 m spacing. On the divided stretches the centreline is the midline between the two OSM carriageways.
   - per station: the left and right curb offsets (interpolated between the 30 aerial stations), a median polygon and its type (planted / terracotta / painted / hatched / nose), and the paint;
   - **three pad outlines** (J2, J3, J4), with straight arm cuts and arc corners at the measured radii;
   - **two weld mouths** on the mainline, at the A5 extents: J1 v1513.5–~1528.5 and J5 v2312–~2322;
   - **stub mouths** for the see-only arms (A1).
2. **Profile:** 3DEP 1 m along each piece, node to node. The 11 % `route_connectors` grade cap is checked, not applied blind: it must bind nowhere.
   - Cross-sections are cut at every pad and weld. The terrain lens's cut and fill numbers cover only the mid-legs; the first and last 50–95 m of each leg are measured here.
3. **adapted** `median_envelope` + `author_median_blend` read the expansion islands from this file. The mainline islands stay byte-identical.
4. **Show, don't assert (L12).** `expansion_plan.svg` and a PNG over NAIP draw every road, pad, mouth, station width and median, numbered so you can point at things.
5. **A scratch rehearsal of the two welds and their race policies,** on a copy of the workshop. It runs `trim_connectors` → weld → `verify_mouths` → `barrier_bands` validation → `no_route`, for both Speedways. Neither mouth shape has been through the chain before:
   - **J5:** a 58° mouth that covers the apex of a corner whose outer edge has R ≈ 10 m. The existing mainline mouths are 77–90°, on straights.
   - **J1:** an opening of about 52 m that runs past the box pin at v1521.
   - Relevant code:
     - `trim_connectors.py:81-92`;
     - `verify_mouths`, half-width = (w/2)/sin(angle) with a 25 m edge search (`:58-59`, `:232-266`);
     - `barrier_bands._mouth_policies` `:807-819` and validation step 7 `:1036-1054`.

**Done when:**
- the plan map shows every piece;
- each centreline lies within 1.5 m of OSM, or of the carriageway midline;
- the rehearsal passes `verify_mouths` on both new mouths, with every existing mouth unchanged;
- the rehearsal passes `barrier_bands` validation and `no_route` on both Speedways, with the predicted policies (or the A7 pin split applied);
- you have the map.

### P2 — Terrain over the expansion (0046's tiers, extended)

> **2026-10-14: done on branch `worktree-wf_c6ab4b42-146-1`, the north route still HELD (no road geometry). Not merged.
> Details and numbers in ledger 0054, "P2"; proofs in `source/expansion/p2-proofs/`.**
> - **Step 1:** the baseline reproduces v0.18.0's plan exactly: 268,976 lattice + 5,157 break-line vertices (the 268,234
>   below was an earlier rehearsal's). The grown heightfield (`tools/grow_heightfield.py`: the installed nodes byte for
>   byte, 13,444 new from 3DEP), the pin's 37 / 26 and the re-keyed cache landed in one change; without D2 and the
>   planned pavement the plan is v0.18.0's, every key shifted by whole cells.
> - **The tiers over the expansion** come from `tier_options.planned_pavement` (the intermediate marks the tiers and the
>   physical ground, pocket included, never the kept cells): 421,917 lattice vertices, physical 269,657 / far 153,613.
>   287,705 + 20,502 samples fetched (TLS), committed with the I-8 corridor.
> - **Step 2 is obsolete:** v0.18.0's global 20 / 40 clamp moves no real point on the expansion roads.
> - **Rehearsal** (`ship_sd.sh --no-install`, fresh scratch copy): the three layouts' drive_test / verify_mouths /
>   verify_fold_fans / no_route files byte-identical to v0.18.0's; the loop's ground within 150 m |Δy| 0.000 m except
>   beside J1 / J5 (≤ 1.68 m, within 85 m of the new pavement); 1GRASS 8 tiles (max 58,612), GRASS_FAR 4 (max 40,314);
>   0 open tier seams; V7 passes (Kwaay Paay from Jackson re-worded: fresh 3DEP fails the 60 m cone too); road kn5
>   125.0 MB.
> - **Step 3:** six stretches of 50 m or more lose a real wall of 3 m or more under P3's graded ground: Mission Gorge
>   s 1475-1560 (right) and Jackson north s 95-165, 320-485, 555-630, 1005-1120, 1225-1525 (right). They are P3's
>   hand-authored cut slopes; nothing is authored yet.
> - **Step 4:** the balanced tiling is in the pinned engine-july prep (checked).
> - **Step 5:** restated in ledger 0046 (below). **Step 6:** `p2-proofs/stills_views.jpg`.
> - **Budget:** the terrain alone takes the road kn5 to 125.0 MB; with P3's roads and the D4 lamps it lands near 146-148
>   MB, over the 145 MB ceiling. See ledger 0054 "Budget, for P3 / P4".

1. **reused `scripts/geometry/terrain_tiers.py`** (0046), run over the pinned frame:
   - physical ground within 250 m of every new pavement. That includes the 4.07 km² pocket the new loop encloses, which the planner's pocket rule makes physical.
   - the see-only far ring over the D2 box.

   First, the planner's baseline must reproduce 268,234 points exactly.
2. ~~**The D3 clamp** (adapted, opt-in per road; the loop's own roads stay 80/250). This step builds only after your yes.~~ Obsolete: v0.18.0's global `clamp_corridor_m` 20 / `clamp_blend_m` 40 covers every road (ledger 0054).
3. **Cut walls beside the sidehill roads.** Within 20 m of a pavement, the ground is the graded near-road surface by design (0046 criterion 7). Past 20 m, 0046's `keep_cells.refine` already puts the kept cells onto 3DEP at 5 m.
   - **P2 measures** how well the built ground keeps the real cut walls. On Mission Gorge s 1115 → J4 and on all of Jackson north, it compares built ground against 3DEP between 12 and 20 m from the centreline.
   - If a wall of 3 m or more is lost for 50 m or more of road, that stretch gets a hand-authored cut slope in Blender (REALISM: lean in, never eject). It is not an engine change.
4. **Tiling.** v0.18.x's balanced tiling must be in the pinned engine-july prep. It already is on the 0046 branch, so this is checked, not built. AC's 65,535-point limit is fatal.
5. **Restate 0046's "no terrain vertex below 100 m" clause.** The network itself now reaches 33.4 m at J3. New wording: *no terrain vertex more than 2 m below the 3DEP value at its own position.*
   - As applied (2026-10-14, ledger 0046): the value is the vertex's point sample, or a finest-level vertex's anti-aliasing tent. The clause holds beyond the graded near-road band (36 m of a built pavement, and the ground_release zones), where a road cut is graded to the road by design.
   - 0046's 3 m guard below 100 m and the 15.52 m floor are kept. As a single "everywhere" sentence it would fail v0.18.0 itself (graded cuts up to 16.3 m), so nothing is loosened.
6. **Preview stills from four fixed camera stations:**
   - J3, looking north at the valley and the north wall;
   - Mission Gorge s 1865, looking at Cowles;
   - Jackson s 1050, looking at Cowles;
   - the J4 approach (Mission Gorge s 2190), looking north-east at Pyles. Kwaay Paay is hidden from there behind a knoll, which the built terrain must reproduce.

**Done when:**
- tier seams have 0 open edges;
- every mesh is ≤ 65,535 points;
- V7 passes;
- the loop's existing ground within 150 m of its roads is unchanged (|Δy| ≤ 0.05 m), except beside the two weld mouths, where the nearest road changes. Those exceptions are expected and listed by name.

### P3 — Road and ground build → **Drive 1 (v0.19.0)**

> **2026-10-18: prep done on branch `worktree-wf_c6ab4b42-146-1` (ledger 0054, "Phase 1 prep").** v0.18.1 and the
> Phase 5 stub tool merged; J1 re-checked against v0.18.1's College (the opening's vertices unchanged; lamp 77 already
> stands behind the R 30 return — check its foot on the apron's ground in step 3); the stub tool's four cosmetic notes
> fixed; the held rehearsal equals v0.18.1. Steps 1-8 below are next.
>
> **2026-10-19: steps 1-8 built and rehearsed (full chain, `--no-install`), v0.19.0, not installed (ledger 0054, "P3").** J2 / J3 / J4 single-coverage pads (seams ≤ 1.1 mm), J1 / J5 welds permanent, 24 barrier stubs + 27 curb cuts, the six cut slopes released (none lost over 50 m), paint per road, Speedways sealed (no_route PASS), `drive_test --line expansion` PASS both ways; the three existing layouts no worse than v0.18.1 on any key. JUNCTIONS 18(d) applied to the pad arms (each pad's side-street arms are 15 m of real, drivable road closed by a physical K-rail, in place of step 4's see-only stubs). Step 6's M3 / M4 race-file plates move to P4 with the lamps and signs. Next: Drive 1.
>
> **2026-10-19: repair round 1 (ledger 0054, "P3 repair round 1"; GATES-CHANGELOG 2026-10-19).** Three checks refused the
> first build; fixed at their causes and rehearsed again from fresh copies: the step-7 lines keep their lane inside the
> pads' curbs (no late exemption; the V6 verdict as written, + edge drops per km at the loop's rate); V5's kn5_ground_check
> runs on all three layouts; the cut walls of step 4 are measured off 3DEP along every piece and kept as raise-only cuts
> (P3's six hand zones retired); the terrain's T-vertex slivers mended (author stage and kn5 prep); step 2's pads follow
> the real ground within their steepness and seam bounds; Glenroy St's south-west leg and Doreen Rd get their stubs. The
> three existing layouts stay no worse than v0.18.1. Open for Kevin: J1's College/Navajo crossroads is built level where
> the real one tilts ~2 m toward Waring, so Waring's first 40 m start up to 1.4 m high.

1. **The `ship_sd.sh` draft.** **adapted** `route_connectors` takes the four pieces with their per-station widths. `divide_connectors` passes them through untouched. `trim_connectors` cuts at the pads and the two welds, then the rebuild runs.
2. **new `author_junction_pad_blend.py`** builds J2, J3 and J4 as single-coverage pads:
   - seams welded to 0.000 m;
   - arc corners with points every 0.6–0.8 m (JUNCTIONS rules 1–6).
3. **reused** mouth weld at J1 and J5. `gap_mouths` cuts the loop's sidewalk across each opening, and `seat_terrain_blend` re-seats the ground there.
4. **Edges and stubs.** Curbs, sidewalks and gutters run along all four roads (JUNCTIONS rules 9–10), and the see-only stubs go in at the corner arms (rule 18c).
5. **Paint**, as the loop's markings tool draws it:
   - Waring and Mission Gorge: lane lines and bike lanes;
   - Princess View: double yellow;
   - Jackson: the double-double-yellow painted median, the hatched approach to J4, and buffered bike lanes.
6. **The Speedways.**
   - The seal policies (A7) go in.
   - The two outside kerbs are dropped.
   - M3 and M4 move to the race files.
   - `no_route` and `verify_race` are re-run.
7. **adapted `drive_test --line expansion`** sweeps the new roads in both directions. Today drive_test walks only the mainline, which would leave 10.8 of 24.3 km never swept.
8. **The gates** (Verification). `--force-install` is used only under 0047's rule: no key worse than v0.18.x.

**What you see:** Free Roam with the new roads, the three new corners and the gorge views. The Speedways look exactly as before, apart from two sealed openings and two corner kerbs gone.

**Done when:** every Drive-1 gate passes and you have driven it. A DRIVE-TEST-REPORT is filed with the addendum's §10 rows.

### P4 — Dressing → **Drive 2 (v0.19.x)**

1. **Signs (A8).**
   - **adapted** `place_signs` detects tight corners on the expansion pieces in both directions.
   - `signs.json` gets the M3/M4 per-layout entries, plus skip entries with reasons.
   - **adapted** `author_signs_blend` writes plates to the race files per layout.
   - **reused** `verify_signs`.
   - The preview is shown to you first.
2. **Lamps (D4).** **adapted** `build_streetlights` takes connector lines and stays clear of every pavement. Today it sees only the mainline, and lamp #77 already stands in Waring. Same sodium look as 0043.
3. **Trees (A9).** **adapted** `make_treefx`:
   - the surface list comes from config (today "1GRASS_0_mat, 1GRASS_1_mat, 1ROAD_road_mat" is hard-coded at `:32`);
   - the caps scale with area;
   - the fill reads 0046's grid files.
4. **Buildings (A10).** **adapted** in `build_loop_blend`: a building is kept if it is within 120 m of **any** drivable piece, not only the mainline (`:479`).
5. **GrassFX tiles regenerated:** `GRASS_MESHES` goes from 4 to 5–6.
6. **Map (A12).**

**Done when:** the Drive-2 gates pass and you have driven it.

### P5 — Release

`pack_release` builds both packages, as set out in `docs/PUBLISHING.md`. The draft release text gives Free Roam's new length. Publishing is your click.

## Phase 2 and later ("a few phases of Lake Murray")

Candidates in the order I'd suggest. You pick after Drive 2.

1. **Mission Gorge Speedway + Reverse.** Either the 8.72 km north loop (J1 → Waring → Princess View → Mission Gorge → Jackson → J5 → Navajo westbound → J1) or the 17.43 km grand loop.
   - It needs a per-layout lap line built from spans of named pieces. Every race tool that counts by point number then reads it: `barrier_bands`/`race_corridor`, `layout_dummies`, `write_ai_line`, `no_route`, `drive_test`, `track_folder`, `kn5_to_gate_obj`.
   - J1 and J5 become pads and open straight through.
   - It reuses the Alvarado-width corridor model, which you called incredible.
   - New race boxes go at J2, J3 and J4.
2. **Mission Gorge Rd east into the gorge, toward Santee (4.07 km).**
   - The character changes at Golfcrest Dr, the signal 1.25 km past J4. From there to about 3.1 km there is no curb: the asphalt runs edge to edge into scrub, with a pale rock cut at 2.0–2.3 km.
   - The road is 20.5–32 m wide, and the reading at the narrows is uncertain (±2.5 m, in shadow).
   - Separately, **Father Junipero Serra Trail** (the park road along the river to Old Mission Dam) is the river gorge itself.
3. **Side-street stubs along the new roads**, so Eldridge, Glenroy, Margerum and Park Ridge read as streets.
4. **A Free Roam spawn on the new roads.** This needs `layout_dummies` to accept points that are not on the mainline.
5. **0040's species pass** over the whole network: eucalyptus confirmed, then jacaranda, coral tree, pepper and the flowering shrubs.
6. **A lighter lamp model**, if Drive 2's frame rate or file size asks for one.

The Lariat resumes after these (ledger 0048), and Sand Creek after that.

## Tool map

| Tool | Status | Change |
|---|---|---|
| `scripts/gps/widths_from_osm._overpass` | reused | the guarded fetch |
| `tools/fetch_osm.py` | adapted | 7-day guard on the mirror fallback, or not used |
| `tools/route_tracks.py` / `data/routes.json` | adapted | append `north`; full/medium/short byte-identical |
| `scripts-v021/elevation/heightfield.py` | **adapted** | opt-in `terrain.grid_grow` (whole rows/cols; latitude, gx, gy from the loop's own points) |
| `scripts/geometry/terrain_tiers.py` `Frame` | **adapted** | opt-in `tier_options.frame.pin` |
| `tools/remap_sample_cache.py` | **new** | one-off whole-cell re-key of the 3DEP sample cache, with the identity proof |
| `tools/author_expansion.py` | **new** | the readable intermediate: pieces, widths, medians, pads, mouths |
| `terrain_tiers.py` / `terrain_sample.py` (0046) | reused | grown box (config) |
| band clamp (`terrain_tiers.py:140`, `build_loop_blend.py:220`) | adapted | per-road `clamp_corridor_m` / `clamp_blend_m` (D3) |
| `route_connectors` | adapted | per-station widths from the intermediate (today a constant 10 m, `route_connectors.py:36`) |
| `divide_connectors`, `trim_connectors` | adapted | pass-through for authored pieces; cuts at the pads |
| mouth weld, `gap_mouths`, `seat_terrain_blend`, `verify_mouths` | reused | the new mouths are rehearsed in P1 |
| `author_junction_pad_blend.py` | **new** | JUNCTIONS topology B, which no SD tool builds today |
| `median_envelope`, `author_median_blend` | adapted | expansion islands and hatches |
| `barrier_bands`, `verify_race`, `no_route` | reused | adapted only if the P1 rehearsal needs the v1521 policy split |
| `race.kerbs.trims` | reused | drop at apex 1514 L and 2319 L |
| `drive_test` | adapted | `--line` to sweep connector pieces |
| `audit_mesh`, `verify_kn5`, `kn5_ground_check` | reused | — |
| `place_signs`, `author_signs_blend` | adapted | expansion corners; per-layout plates (M3/M4) |
| `build_streetlights` | adapted | connector lines, pavement clearance |
| `make_treefx` | adapted | surface list from config, caps by area |
| `build_loop_blend` (buildings pass) | adapted | 120 m from any drivable piece |
| `make_map` | adapted | per-layout lap filter |
| `ship_sd.sh` + `ship_track.sh` + `ship.json` | adapted | new steps and sync-in entries in both chains |
| engine-july prep balanced tiling | reused (0046 branch) | precondition: v0.18.x merged |
| `sightline_check` (0046) | reused | new stations |

## Budget

**Starting point:** v0.18.x as rehearsed. Road kn5 107.3 MB; physical ground 236,771 points in 4 tiles; far ring 106,557 points in 2 tiles.

| Item | Points | Size |
|---|---|---|
| Road, curbs, sidewalks, paint for 6.36 km | **+58k to +90k**. 58k is the loop's own rate (164k on 17.9 km = 9.2k per km). The ×1.5 upper bound allows for 17–33 m roads with medians, three pads and curbs on both sides. | +2.9 to +4.5 MB |
| Physical ground | +62.9k planned → 300–328k built, in 5–6 tiles | |
| Far ring with D2 | +33k → ~140k, in 3 tiles | |
| Terrain total | | +5.4 to +7.2 MB |
| Lamps, D4 default (~90 × 4,045) | ~+364k | ~+18.2 MB |
| Lamps, all 113 | +457k | +22.8 MB |
| Buildings | the loop's BUILDING + HOUSE is 11,975 points for 13.48 km, so ~6k here, up to ~12k with Grantville's big roofs | < 0.6 MB |
| Signs | 6 plates (+2 moved) | negligible |

- **Road kn5:**
  - **about 134–138 MB** with the D4 default;
  - about 116–120 MB with no lamps;
  - about 139–142 MB with every new road lit.
  - **The ceiling is 145 MB** [invented]. Past it, a decimated lamp is used before anything ships.
- **CSP lights:** 244 → about 334.
- **TreeFX:** the caps scale by area, and the count is printed before the build.
- **GrassFX:** 4 → 5–6 tiles.
- **Gate time:** +15–25 s on today's ~124 s for the three layouts, plus about 10 s for the new expansion sweep [estimate]. Export takes about 30 % longer.
- **Network:**
  - one guarded Overpass fetch and one buildings fetch;
  - about 56 requests to sample the grown 40 m grid in full (24,883 nodes);
  - about 270 requests for the new tiered samples (~120k points).

## Risks

1. **J5 is the 0050 box.** Jackson north's opening covers the whole outside of that corner (v2312–2322), right where the fold-fan steps were.
   - Mitigation: 0050 is fixed and seat-confirmed first; the P1 rehearsal; a step check at J5 on every layout.
2. **J1's opening runs past the race_cw pin.** About 25 m of the Waring opening (v1521–1528.5) sits in race_cw's exit funnel, and no policy has handled that before.
   - Mitigation: the P1 rehearsal, with a probe placed past v1521. The fallback is the pin split (A7).
3. **The heightfield frame.** Growing it carelessly shifts every existing ground point and throws away the sample cache.
   - Mitigation: whole-cell growth, the pinned frame, and the remap proof (P0 step 6).
4. **Tile cap.** 1GRASS_0 is at 98.5 % of AC's limit today.
   - Mitigation: v0.18.x's balanced tiling, already on the 0046 branch, is a precondition.
5. **Corner folds.** A wide road bent around a tight curb corner crumples.
   - Mitigation: pads at J2–J4, plus gates for single coverage and seam gaps of 10 mm or less.
6. **D3 unanswered or declined.** Under the rule as written, the clamp planes 24.3 m off Jackson's ridge and fills its canyon by 11.6 m. The road is still right, but the canyon isn't.
7. **The aerial is from April 2022.** That is the only NAIP year the USGS service serves; the USDA service reset the TLS connection.
   - Paint, bike buffers or medians may have changed since. The eye readings are good to ±1–1.5 m.
   - A Street View pass comes before Drive 1.
8. **Things OSM doesn't say:**
   - no signal tagged at Margerum Ave (st 1099);
   - no speed limits on Princess View or Jackson;
   - residential driveways mostly unmapped;
   - guardrails too small to resolve on the aerial.

   Those parts stay labelled *authored* until Street View fills them in.
9. **Cut walls inside 20 m.** The graded near-road surface may smooth the real 3–11 m walls.
   - Mitigation: measured in P2, with hand-authored slopes where they are lost.
10. **Gate coverage.** Without `drive_test --line`, 10.8 of 24.3 km of drivable road would never be swept.
11. **Size and frame rate.** The shared road kn5 grows by about +27–31 MB. You call load time and frame rate great today, and only your seat can judge them after this.
    - Fallbacks: first a decimated lamp. Then a street-only kn5, but that conflicts with JUNCTIONS rule 20, so it is not the default.
12. **Chain drift.** A step that lands in one chain but not the other breaks parity.
    - Mitigation: A13.
13. **Regenerating routes.json** would re-route full/medium/short.
    - Mitigation: append only, with a byte diff.
14. **Tree density.** Even caps would thin the loop's verges.
    - Mitigation: area-scaled caps, and a density check.

## Not in this plan

- A new race layout (Phase 2, D1), and any change to the Speedways' laps, corridors, AI or starts.
- Mission Gorge Rd east of Jackson, Father Junipero Serra Trail, Waring beyond Princess View, and every side street (Phase 2+).
- AI on the new roads, and AI lines from GPS (banned).
- Working traffic signals and live traffic.
- 0040's species and model work beyond the zones and the Gum belt.
- I-8 as drivable road.
- The Lariat (shelved, ledger 0048) and Sand Creek.

## Verification (decided now, before any geometry)

Everything runs on the **built** file (L5), against data that did not place it: OSM, NAIP and 3DEP. Stations are in the junction-node frame.

| # | Check | Threshold |
|---|---|---|
| **V1 Plan** | Built pavement centreline vs OSM, or the carriageway midline | p95 ≤ 1.5 m [invented] |
| | Curb to curb at the 30 aerial stations | within ±1.5 m of the eye reading [invented; the eye's own ±1–1.5 m] |
| | Medians | raised on Waring and Mission Gorge where the aerial shows them; Princess View only Fontaine's nose; Jackson painted, with the hatched 3–4 m approach to J4 and no raised island |
| **V2 Profile** | Built new roads vs 3DEP | p95 ≤ 0.5 m [invented in 0048; the loop's is 0.42] |
| | Princess View max grade | 10.2 % downhill / 10.4 % uphill, ± 0.5 |
| | Mission Gorge crest | 114.3 ± 1 m, within 20 m of 32.8121, −117.0657 (s 1460) |
| | J2 / J3 / J4 pads | 103.9 / 33.4 / 92.4 ± 1 m |
| | J1 and J5 | the new road meets the **unmoved** loop: mainline heights in the boxes byte-identical to v0.18.x (v0.17.1: J1 125.1–125.3 m, J5 209.2–210.2 m); weld seams 0.000 m [std: JUNCTIONS rule 3] |
| | Grade cap (11 %) | binds nowhere |
| **V3 Mouths and pads** | `verify_mouths` | PASS on both new mouths; every existing mouth unchanged |
| | Opening extents | J1 within v1512–1532, J5 within v2311–2323 [measured, ± the return radius] |
| | Pads J2–J4 | multi-coverage 0 m²; seam gap ≤ 10 mm; open ribbon ends inside a mouth polygon 0 [std: JUNCTIONS] |
| **V4 Speedways** | `no_route` | PASS on race_cw and race_acw [std: 0049], including a probe into the J1 opening past v1521 |
| | `verify_race` | PASS, including E/O (no kerb under a weld sheet) |
| | Unchanged | `zone_by_vertex`, `closure_y_by_vertex`, `lane_by_vertex`, `runs` and `pins`: byte-identical to v0.18.x. AI lines and spawns: byte-identical |
| | Changed by exactly | `corridors.<id>.mouths` gains the 2 new mouths with the predicted policies (or the A7 split); `no_route.forbidden_probes` gains their probes; `kerbs_dropped` gains apex 1514 L and 2319 L; nothing else in `race_authored` changes |
| **V5 Existing layouts no worse** | `drive_test`, `audit_mesh`, `verify_kn5`, `kn5_ground_check` on all three layouts | no key worse than v0.18.x [std: 0047] |
| | J5 box, every layout | no step ≥ 6 cm [invented: drive_test's ⚠ value]; 0050's own check re-run |
| **V6 New roads, both directions** | `drive_test --line expansion` | obstructions, floating furniture and undrivable spots all 0 [std]; severe steps 0 [invented]; soft-top-in-lane ≤ 6.1/km and kinks ≤ 4.97/km [invented, copied from the loop's rate] |
| **V7 Terrain** | Cowles from Jackson s 550–1550 (eye 1.2 m) | ≥ 9.0° (real 9.6–9.8°) |
| | Cowles from Mission Gorge s 1865 | 7.4 ± 0.5° |
| | Cowles from Mission Gorge s 565–1465 | blocked by built terrain (real: blockers at +6.3 to +15°) |
| | Kwaay Paay from Jackson s 550 | visible, 8.0 ± 0.5°, judged as a 150 m summit cone [invented; P2: fresh 3DEP fails the 60 m cone too, the dome's own shoulder 90 m short of the top] |
| | Kwaay Paay from Mission Gorge s 2190 | **hidden** behind the +8.85° knoll 321 m away |
| | Pyles from Mission Gorge s 2190 | 8.5 ± 0.5° |
| | Far cells | within 1 m of 3DEP |
| | Sidehill clamp | moves no point on Jackson north or Mission Gorge by more than 1 m |
| | Cut walls 12–20 m off Jackson north and Mission Gorge s 1115→J4 | no stretch of 50 m or more where a real wall of 3 m or more is lost |
| | Facets 20–60 m from a new road | longest edge p90 ≤ 7 m [0046 criterion 5] |
| | Pit clause (restated) | no vertex more than 2 m below its own 3DEP (its point, or a finest-level vertex's tent) beyond the graded near-road band; 0046's 3 m below 100 m and 15.52 m floor kept |
| | Tier seams | 0 open edges |
| **V8 Format** | Every mesh | ≤ 65,535 positions [std: AC] |
| | Far meshes | no `1` prefix |
| | Road kn5 | ≤ 145 MB [invented] |
| | `GRASS_MESHES` | lists only 1GRASS tiles |
| **V9 Signs** | `verify_signs` | PASS |
| | Plates | 6 new arrows; M3/M4 present in both race files and absent from Free Roam; 0 sign bases inside Free Roam's drivable pavement |
| **V10 Trees** | The existing TreeFX checks | PASS |
| | Loop verge density | within ±5 % of v0.18.x [invented] |
| **V11 Your seat** | Two DRIVE-TEST-REPORTs with the addendum's §10 rows | the only verdict that closes 0054 Phase 1 |

**Drive 1 is gated on V1–V8. V9 and V10 are recorded in Drive 1 and gate Drive 2.**

## First three moves after approval

1. **Now, on a branch off the 0046 branch** (P0 steps 2–8):
   - the guarded OSM fetch;
   - the appended `north` route, with the diff;
   - the config changes;
   - `heightfield.py grid_grow`, the frame pin and the remap tool, with the identity proof;
   - the buildings refetch.

   No geometry. It is rebased after v0.18.x merges.
2. **The readable intermediate and the numbered plan map (P1).** In parallel, the scratch rehearsal of the J1 and J5 welds and their race policies, with the probe past v1521. You get the map.
3. **The terrain planner on a scratch copy (P2).**
   - The baseline is reproduced first. Then the expansion, the D2 box and the D3 clamp are added, and the tile counts, sightlines and cut-wall check are printed.
   - In parallel, the Street View pass: paint, speed limits, Margerum's signal, lamps at night, and the Jackson eucalyptus belt.
   - P3 starts once v0.18.x is installed and you've confirmed 0050 in your seat.

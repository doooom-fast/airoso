# Location dossier — Del Mar Grand Prix, the IMSA circuit on the Del Mar Fairgrounds (del-mar)

> **Status 2026-11-01: ESTIMATED LAYOUT.** Kevin (2026-11-01): "Commit and build to an estimated historical layout
> of the city that would match." The course was temporary walls on parking lots, 1987–1992, and the fairgrounds
> were rebuilt 1991–93, so no asphalt survives to trace and today's imagery does not carry 1987's fixed features
> except the horse oval, its infield lakes and the barn rows. Everything below says which of its facts are
> *measured*, *read off period video*, or *estimated*. Research record: `docs/research/del-mar/SOURCES.md`.

## 1. Identity & intent
- Kind `circuit_port`, archetype `race_circuit` (a shut-down temporary facility with a defined course; STANDARDS S6).
- Why: the Camel GT prototypes' season finale in San Diego County, 1987–1992 — Jaguar XJR-9s, Nissan GTP ZX-Turbos,
  Porsche 962s on a walled parking-lot course between the horse track and the lagoon, 33,000 people (RSC, 1988).
  Kevin named it from a video he saw and asked for it as a track (2026-11-01).
- Layouts: one, `full`, counter-clockwise, 10 turns. No variants claimed.

## 2. Route geometry — facts, per segment
| Segment | Where (today's ground) | Length | Width | Surface | Source / status |
|---|---|---|---|---|---|
| Main straight, S/F | along the north side of the 1987 hall block, heading west | ~350 m (est.) | 13 m (est. from the 1987 grid shot: ~3 cars wide between walls) | lot asphalt | video (7:19, 7:45 1987) + estimate |
| T1–T2 | right-angle at the hall's west end, into the paddock lot | — | — | lot | video (7:27 "T.2") |
| T3 paddock hairpin | pointed hairpin wrapping the paddock, apex ~20 m east of the oval's east turn | — | — | lot | video (7:35 "T.3": oval rail immediately beside) + estimate |
| T4–T6 west and south legs | down the west side, along the SW halls by the river lot | — | — | lot / dirt lot | video (7:51 "T.6") + estimate |
| T7–T8 east lobe | across Jimmy Durante Blvd into the east lot, hairpin under I-5 | — | — | dirt/asphalt lot | video (8:07 "T.8") + **estimate: the lobe's extent is the least certain thing here** |
| T9–T10 return | west along the north, the kink into the straight | — | — | lot | video (8:10 "T.9": tent and sponsor wall on open dirt) + sketch |

Lap: **about 2.0 km as built** (engine's smoothed line 2006 m; the placed sketch 2170 m) against **2570 m published**
(RSC "2.570 kms", Fastlane 2.579 km, Motor Sport "1.6 miles"). The published length does not fit inside the
grounds with the drawn shape: at 2570 m the sketch's 2:1 proportions put the lobe in the lagoon or the bottom in
the river, and each placement that cleared the fixed ground (the oval's rail, Jimmy Durante's river-side stretch
where the boulevard sits on the bank) shortened it further. The TV map's proportions are the suspect; the course
may also have used more of the north-east lot than the sketch shows. L1 stands: no roads are invented — the whole
course is on lots that exist, and the one public road it uses (Jimmy Durante Blvd, crossed twice) is the
"street" of the "street circuit" billing.

Placement history (`source/estimate/placement.json`, all north-up, x-scale hairpin apex → east lobe apex, y-scale
capped at the bottom): E2 apex (1280,430) bottom 1430 — hairpin arm on the oval's dirt, bottom on the river bank:
drive_test red (severe steps + stone guard at s 1232–1242). E3 apex (1360,440) bottom 1360 — bottom still along
the boulevard: red (s 1172–1193). **E4 apex (1360,440) bottom 1290 — draft drive_test PASS** (severe 7 at s
1131–1137 of 7 cm, obstructed 0, floating 0); built 2026-11-01 run 4.

## 3. Elevation & drainage
Flat river terrace, 3–5 m above the San Dieguito lagoon. Real USGS 3DEP elevation only (`elev` stage); no banking,
no invented camber (`road_profile.cambers: []`). Drainage: the lots fall gently south to the river; nothing the
course would feel.

## 4. Corner-by-corner character
Counter-clockwise from S/F (video timestamps are the 1987 broadcast, `docs/research/del-mar/frames/`):
1. **T1** (7:27): straight ends in a near right-angle left by the hall's end; a Dodge bridge over the braking zone.
2. **T2**: short link past the striped paddock tents.
3. **T3** (7:35): pointed hairpin around the paddock, transporters inside, the oval's rail outside; bleachers and a
   sponsor-board wall on the outside (1988 25:00).
4. **T4–T5**: the west and south legs, long sweeps past the SW halls; red/white painted kerbs at the apexes.
5. **T6** (7:51): the corner by the halls' east side.
6. **T7–T8** (8:07): the east lobe hairpin on the open lot.
7. **T9** (8:10): corner on dirt by a red/white circus tent, sponsor wall (Miller, Quaker State, Camel, Goodyear,
   Yokohama) with the I-5 / Via de la Valle mesa behind — the one corner that looks out over open ground.
8. **T10**: the kink before the straight.
Hazards for the drive test: lot paint under the racing line (visual only), the right-angle T1, the two hairpins.

## 5. Built environment & landmarks
Seen in the broadcasts: the fairgrounds' Spanish tower (the old grandstand entrance) ahead of the grid; the big
exhibit hall with a white ridge skylight inside the loop (rebuilt since: today's hall is on a different footprint and
axis); barns to the north; the horse oval and its lakes to the west; Jimmy Durante Blvd; I-5 and the lagoon east;
Del Mar village on the bluff south across the river. None of the temporary structures survive.

## 6. Vegetation & terrain palette
Palms along the pit straight and by the Spanish buildings; otherwise bare asphalt and dirt lots, eucalyptus on the
hills north, salt marsh east. `scenery.tree_cap: 0` in the draft; palms are bespoke.

## 7. Atmosphere & light
October afternoons, 1–3 pm starts, "cool, sunny" (RSC 1988). Coastal haze, low sun by the finish. Presets
morning / noon / golden_hour.

## 8. Asset plan — owned first
| Item | Seen | Plan |
|---|---|---|
| White K-rail with debris fence at corners | every frame | bespoke (the K-rail stubs Kevin approved 2026-10-26 are the base) |
| Plank fence lines on the outside | 1988 13:20 | bespoke |
| Aluminium bleachers, straight and hairpins | 1987 7:45, 1988 25:00 | bespoke |
| Sponsor bridges (Camel GT, Dodge) | 1987 7:19, 1988 15:00 | plain spans with period-coloured generic boards (trademarks not reproduced) |
| Sponsor-board walls at corners | 1988 2:10:00 | generic coloured boards |
| Painted lot stalls under the line, red/white kerb paint | 1987 7:30, 1988 25:00 | road markings / kerb texture |
| Palms, the Spanish tower | 1987 0:12, 1:10:00 | bespoke, later pass |

## 9. Data sources & capture assets
- Layout: NA-Motorsports 1987–92 drawing (CC-NC-SA, reference only) → `source/estimate/sketch_loop.json`;
  ESPN 1988 map (`docs/research/del-mar/frames/1988_1108_espn_track_map.jpg`, same shape).
- Placement: `source/estimate/placement.json` (north-up, x-scale hairpin→lobe, y-scale river lot;
  `placement_on_naip_2012.jpg` is the overlay). Base image `source/naip_2012_delmar.png`: USDA NAIP 2012-05-19, public
  domain, Web Mercator z18 crop, control points = crop corners.
- Period video: ESPN Speedworld 1987 (YouTube yJ84S9eTHRs) and 1988 (e8zZ3brQpac), downloaded 2026-11-01 with
  Kevin's OK for frame study; not shipped.
- Georeferencing tool for the correction pass: `docs/research/del-mar/tools/georef.html`.
- **Wanted:** one north-up USGS NAPP / Google Earth Pro frame of the fairgrounds, 1989–1996.

## 10. Location-specific QA
- The lap must come out 2.3–2.6 km; a draft outside that range means the placement moved.
- S/F heading west, T1 a left; pits on the driver's right on the grid.
- The paddock hairpin must not cross the oval's rail (the rail is at the hairpin's outside).
- Nothing enters the barns (north) or the river (south); the east lobe stays west of the I-5 frontage.

## 11. Build plan
1. **Draft** (the engine): `aerial` (source.trace_px → centerline) → `elev` (3DEP) → `project` → `mesh` → `underlay`.
2. **Prep / ship** through `tools/ship_track.sh del-mar`; gates `drive_test`, `audit_mesh`, `kn5_ground_check` on the
   built kn5. First pass: no authoring, no install until Kevin says.
3. **Correction pass** when era imagery arrives: re-place in the georef tool, re-run from `aerial`.
4. **Dressing pass**: section 8 as bespoke work.

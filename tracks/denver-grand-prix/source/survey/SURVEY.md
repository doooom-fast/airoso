# Denver Grand Prix: the lap survey (PLAN §4b)

2026-11-23/24. The lap corridor: the lap's pavement and 30 m either side of OSM's line, and every junction on it. A measured
inventory of road paint, streetlights and other posts, signal masts, and signs. **No geometry, no `track.config.json`.**
The pilot (`pilot/PILOT.md`) proved the sources on 385 m of Colfax; this is the whole lap, 6,646 m.

| File | What | Grades |
|---|---|---|
| [`paint.json`](paint.json) | 5,993 items: 185 + 10 crosswalks, 224 stop bars, 3,105 lines, 1,566 bars, 918 small marks (23 typed arrows), 5 coloured surfaces | 22 % measured, 78 % detected |
| [`lamps.json`](lamps.json) | 534 posts that are not signals: 323 lamps, 142 sign or small posts, 18 utility poles, 51 posts of unknown kind | 79 % measured, 21 % detected |
| [`signals.json`](signals.json) | 119 signal masts, 82 signal posts (58 also carry a light); the count at every OSM-signalled junction | 90 % measured, 10 % detected |
| [`signs.json`](signs.json) | 57 junctions, 5 rail crossings, 15 speed-limit changes: what OSM implies | 100 % tagged |
| `stills/legNN_*.jpg` | one overlay per leg on the 2022 picture | |
| `refutation/` | every refutation round, the lap-wide registration check | |
| `eye/` | the brief the eye worked from and every verdict file | |

**Nothing is invented.** `measured` = read off an aerial at its own place (a mark's pixels, a post's shadow foot). `detected` =
found, but weak (a fragment, an untyped mark, one flight year only, or placed by eye with no shadow foot). `tagged` = OSM says it,
no position beyond the junction. Silence is never a pass: an unsurveyed stretch is declared (below) and every eye panel without a
post carries `"none": true` in `lamps.json` → `stretches`.

## Sources

| Source | Date | How | Bytes |
|---|---|---|---|
| DRCOG aerials (DRAPP), 3-inch, `drapparchive.s3.amazonaws.com/<year>/<tile>.tif` | **2022, 2020, 2018** (flight day not known: DRCOG's metadata host refuses this session) | `lap_fetch.py`: rows by HTTP range into a sparse cache, cut into 60 work tiles of 150 m + 12 m margin | about 5.6 GB fetched; nothing in git |
| Lidar USGS 3DEP `CO_DRCOG_2_2020` (EPT) | flown 2020-05-27 | `ept_box.py` per work tile | 60 tiles; nothing in git |
| OSM, `source/osm.json` | 2026-11-23T01:12Z | signals, crossings, one-ways, limits, lanes | in git |

NAIP 2023 was not needed: the 3-inch archive answered for three years. 2024 (DRCOG) is listed and refused (403), as in P0.
Every fetch went through `scripts.tls.https_context`. The cache: the scratchpad of the session (rasters and points are not in git;
`lap_fetch.py <cache> --years 2022,2020,2018 --lidar` rebuilds it).

## How it runs

```
python3 lap_fetch.py <cache> --years 2022,2020,2018 --lidar     # the corridor's pictures and points
python3 paint_tile.py <cache>          # paint per work tile, three years, one frame        -> <cache>/paint/*.pkl
python3 paint_lap.py <cache>           # the lap's paint, symbols, surfaces, grades          -> paint.json
python3 paint_register.py <cache>      # paint against the lidar                             -> refutation/paint_registration.json
python3 posts_tile.py <cache>          # shadow strokes per tile and year (first pass)
python3 posts_lap.py cluster <cache>   # candidates + eye panels; eye/verdicts_b*.json are the eye's
python3 posts_tile.py <cache> --known <cache>/known_posts.json   # second pass, the sun from confirmed posts
python3 posts_lap.py cluster2 <cache>  # new candidates only; eye/verdicts_r2_b*.json
python3 posts_lap.py apply <cache>     # lamps.json, signals.json (eye/corrections.json applied)
python3 signs_build.py                 # signs.json
python3 stills.py <cache>              # stills/
python3 refute.py <cache> paint.json <out> <round> j:<s,...> m:<s,...>   # refutation overlays
```

Every threshold is written into the output files as `thresholds_invented`: they are tuning of colour readers, not measurements.

## Paint

**Counts** (`paint.json` → `counts`): crosswalks 185 measured + 10 detected, **1,406 bars read and 18 inferred** (a bar between read
bars at the row's spacing where the 2022 picture is hidden by a vehicle or shadow; written `inferred: true`), 32 crosswalks joined from
pieces split by hidden bars; stop bars 146 + 78; lines: 327 broken, 322 solid, 37 double solid, 147 dotted, 2,252 single dashes or
fragments; lone bars 566 + 1,000; small marks 918, of which **23 typed** (18 left-turn, 2 right-turn, 3 through arrows); 5 red / green
surfaces (bus-lane panels, coloured crossings), outlines only.

**Grades.** 1,340 measured items: 886 seen in all three flight years, 380 in two, 74 in one (2022 only, firm). 1,815 items fill what
vehicles and shadow hid in 2022 from the older years; **418 are flagged possibly removed** (seen in 2020 / 2018, bare pavement in
2022); they stay `detected`.

**The independent readings.**
- **Lidar intensity** (2020-05-27, another sensor): of the 1,322 measured lines, bars and crosswalks, **947 confirmed, 64 contradicted,
  311 unreadable** (too few returns). Crosswalks: 170 confirmed, 15 contradicted. A lone bar or line the lidar contradicts while
  the 2020 picture shows it is graded detected (a gutter pan or slab edge is likely).
- **Position, lap-wide** (`refutation/paint_registration.json`): the lidar's bright ground returns shifted over the measured paint in
  0.15 m steps, per work tile. 33 of 53 tiles have enough returns to say: **the paint sits 0.21 m (median), 0.34 m (p84 and p95)
  from where the lidar puts it, mean bias 0.06 m east, 0.03 m north.** The step is 0.15 m, so this is "within two steps"; no
  registration shift is applied. Claim for a measured mark: **±0.35 m absolute, about 0.1 m relative to its neighbours.**
- **Between flight years:** 2020 and 2018 are moved onto 2022 per tile by correlating their paint; most tiles need 0–2 pixels
  (0–15 cm), a handful 5–12 pixels (`paint.json` → `year_to_2022_shift_px`).

**Widths** (the pilot's over-read). Each mark's luminance profile across it is fitted with a box blurred by the picture's own point
spread (σ 0.049 m in 2022, 0.036 in 2020, 0.035 in 2018, from wide bars' edges). White lane lines: **fitted 0.18 m median** (p16–p84
0.15–0.26) against **read 0.23 m**. Each line carries `width_m` (fitted), `width_read_m` and `width_standard_in` / `_m`, the nearest
MUTCD width (4, 6, 8 or 12 in): 126 lines at 6 in, 104 at 8, 55 at 12, 22 at 4. Crosswalk bars 0.51 m (fitted) and stop bars 0.64 m.
Double yellow: the fitted width spans both lines and the gap, and says so.

**Symbols.** Typed by mask overlap with exemplars cut from this imagery and named by eye (`exemplars/`): the turn arrow (its mirror
is the other hand) and the through arrow. The threshold (0.70) was set on a gallery of every match at 0.5: all at 0.77+ were arrows,
none under 0.65. Every typed arrow was then looked at (all 23 are arrows; the type and heading of each are right). OSM turn:lanes is
written beside each arrow; it was never needed as a tiebreak. **Not typed:** bicycle symbols, BUS / ONLY legends (they sit on
red and green panels the white reader does not hold as shapes) and worn arrows (score 0.56–0.65). They are untyped marks or absent.

**What could not be read** (per leg in the table below; `paint.json` → `per_leg`):
- **Stout St under the Convention Center, s 1,386–1,730 (344 m): unsurveyed.** No aerial sees it; 16 marks on the roof were dropped;
  nothing is filled.
- **Vehicles:** 9–22 % of each leg's roadway in 2022; filled where 2020 or 2018 saw the place clear.
- **Building shadow:** 57 % of Stout's and 55 % of 15th St's roadway in 2022. Read with a per-tile gain (`prep.py`); paint at
  9 grey levels over asphalt at 32 is there, and two years agree on most of it, but a third of the crosswalk bars under the darkest
  shadow were not read by any year.
- **In no year:** 6–34 % of a leg's roadway was hidden in all three pictures (34 % on Stout, the shadow).
- **Paint on bright concrete** (Stout St's lanes) is not read: the reader looks for paint over dark pavement. Declared, not filled.
- **Kerbs, slab joints, rail slabs:** the light-rail slab's edges on Stout and Speer and the white borders of brick crossings read
  as lines; the refutation counts them as false.

## Posts (lamps, signal masts, signal posts, signs posts)

**The lidar does not see them** (pilot: 7 of 8 with no return above 2 m). Posts are read from their **shadows**: a thin dark stroke
of the sun's bearing starting at the post's foot.

1. **Reader** (`posts_tile.py`): the darkness test relative to the background (lawns are dark in 2020), strokes opened along the
   year's shadow bearing, arms and the lamp head at the foot recorded, nothing read inside a building's shadow. **Two flight years
   with different sun bearings** (2022 and 2018 about north, 2020 north-west, and north in part: its flight lines were flown at
   different hours) mean a post's strokes in two years **start at one point and point different ways**: that is the independent
   reading, and how far apart the years' feet are is the position check.
2. **Every candidate checked by eye.** 133 panels (2022 beside 2020, 58 m, 5 m ticks), eight readers, 1,643 candidates; then a second
   reader pass with the sun's bearing taken per tile from the confirmed posts, 299 new candidates and 44 rings the first readers could
   not find, on 138 panels that also show every accepted post. **1,942 candidates, all classed by eye** (`eye/verdicts_*.json`).
   Then a **sign-post pass**: four readers at all 55 junction boxes on the lap, looking only for posts with no square (62 added,
   mostly corner and median sign posts and small globe lamps), and the misses of the four refutation rounds (below).
   **336 posts were added by eye** where the reader missed them: 189 at the foot of a shadow stroke within 1 m (measured), 147 by eye
   only (detected, ±1.5 m). After the passes, `eye/corrections.json` removed 28 accepted posts (not posts, meters, a square on another
   post's shadow), moved 3, reclassed 27 and flagged 4 positions; each entry says why.
3. **The reader against the eye:** precision **0.23**, recall **0.56**. Its false candidates are bare trees (by far the most), mast arms
   seen over the road, paint, cars, roof clutter seen over the street by the towers' lean, creek-bank rocks. Its misses: globe lamps
   under trees, lamps and masts in building shadow, short sign posts, corner masts whose shadow merges with the arm's.

**Classes** (settled after refutation round 2, `eye/README.md`): `signal_mast` has an arm reaching over the roadway; `signal_post` is
any pole or pedestal carrying signal or pedestrian heads with no such arm, tall or short (`carries_lamp` where it also has a light);
`lamp` carries no heads; `sign_or_small_post` is short (about 1.5–3 m of 2022 shadow), usually ending in a plate; parking meters,
bollards and delineators are not posts here.

**Counts:** 323 lamps, 119 signal masts, 82 signal posts, 142 sign or small posts, 18 utility poles (light-rail catenary, span-wire
poles), 51 posts of unknown kind. 735 posts in all; **457 (62 %) confirmed by a second flight year** (220 in three years, 237 in two),
148 seen in one year (the others in shadow or the post not there), 130 placed by eye with no stroke in any year (in building shadow,
or under trees).

**Position:** where two or three years' feet are read, they agree to **0.45 m median, 0.78 m p84, 0.95 m p95** (`position_check`). The
eye's own placements: ±0.5 m at a shadow foot, ±1.5 m otherwise, ±2–2.7 m where flagged (`position_note`).

**Signals at every junction** (`signals.json` → `junctions`): OSM tags 55 signal nodes at 49 junctions. **All 47 signalled junctions on
the lap have at least one mast or signal post**: 1 mast at 4 junctions, 2 at 17, 3 at 22, 4 at 2, 5 at 1, none but signal posts at 1
(Santa Fe / W 14th: one signal post). **The other 2 OSM signal nodes (Colfax / Pennsylvania, a Logan St node 160 m north of Colfax) lie on lap ways
beyond the lap: not surveyed, nothing claimed.** 4 signal posts stand where OSM tags no signal (light-rail crossings and a mid-block
pedestrian crossing).

**Heights: not written.** A shadow's length gives a height with the sun's elevation. On the pilot stretch two building shadows against
lidar roofs gave 58° and 47° for one 2022 picture; 2020 holds flight lines of different hours; DRCOG's metadata (flight date and time)
is refused. No clean elevation exists for any year, so no height is claimed. `shadow_m` per year is kept on every post; a height
follows as soon as the elevation does.

**Signs on posts:** a sign post's plate is seen only as a shadow; its face is not read.

**Not read from the air:** what a post carries (fixture type beyond lamp / globe / cobra seen by the eye, signal heads and their
number, any sign face), posts in deep building shadow in both years, and anything under the Convention Center roof.

## Colfax: 2022, as surveyed

PLAN D8: build the last state a survey saw finished. **`paint.json` holds Colfax as the 2022 picture shows it** (two general lanes each
way, a centre turn lane, the pilot's crosswalks). OSM today tags the lap's Colfax ways `lanes=2`, `bus:lanes=designated|yes`: **changed
since, not surveyed**; the tags are in `paint.json` → `colfax.osm_present_tags`, the implied bus-lane signs are in `signs.json` →
`colfax_note`. No new paint is guessed.

## Signs

From OSM only, per junction (`signs.json`): the control (49 signal, 2 stop / give-way, 6 nothing tagged), the lap street's and each
cross street's one-way, limit, lanes, turn and bus lanes; what those tags imply under the MUTCD (82 one-way plates and turn
prohibitions, 2 STOP / YIELD, signal faces); 5 light-rail crossings at grade; 15 speed-limit changes along the lap. **No post position
beyond the junction, no face.** Each junction lists what a street-level source must supply: every sign's post and face, name blades,
lane-use signs, parking and bus-stop signs. Signs mounted on the posts in `lamps.json` / `signals.json` are not told apart from the air.

## Per leg

| Leg | m | Crosswalks | Stop bars | Paint measured / detected | Lidar on measured (conf / contra / unread) | 2022 hidden: vehicles / shadow | Hidden every year | Lamps | Masts | Sig. posts | Other posts | Posts in 2+ years |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Colfax WB to Speer NB | 1,176 | 44 | 43 | 291 / 677 | 240 / 6 / 41 | 12 % / 6 % | 8 % | 74 | 27 | 13 | 45 | 92 / 159 |
| Speer NB to Stout | 151 | 5 | 3 | 21 / 58 | 12 / 1 / 8 | 15 % / 0 % | 10 % | 7 | 2 | 2 | 3 | 9 / 14 |
| Stout to 15th St (344 m covered) | 579 | 7 | 11 | 29 / 154 | 19 / 8 / 2 | 9 % / 57 % | 34 % | 10 | 4 | 8 | 14 | 24 / 36 |
| 15th St to Blake | 739 | 19 | 39 | 142 / 1,016 | 77 / 7 / 54 | 12 % / 55 % | 15 % | 48 | 13 | 15 | 13 | 39 / 89 |
| Blake to Speer SB | 302 | 10 | 11 | 49 / 158 | 36 / 0 / 13 | 16 % / 3 % | 15 % | 24 | 6 | 9 | 10 | 40 / 49 |
| Speer SB to Kalamath | 803 | 13 | 28 | 137 / 403 | 90 / 4 / 43 | 9 % / 0 % | 7 % | 47 | 13 | 9 | 19 | 72 / 88 |
| Kalamath S to W 14th Ave | 388 | 8 | 15 | 103 / 315 | 68 / 4 / 29 | 9 % / 0 % | 7 % | 9 | 8 | 1 | 15 | 26 / 33 |
| W 14th Ave to Santa Fe | 66 | 3 | 2 | 17 / 73 | 7 / 7 / 3 | 22 % / 4 % | 19 % | 2 | 1 | 1 | 4 | 5 / 8 |
| Santa Fe N to Colfax | 190 | 4 | 1 | 30 / 96 | 21 / 1 / 8 | 10 % / 2 % | 8 % | 6 | 1 | 1 | 4 | 7 / 12 |
| Kalamath NB branch to Speer SB | 148 | 5 | 7 | 45 / 132 | 24 / 2 / 16 | 6 % / 0 % | 6 % | 2 | 2 | 1 | 11 | 9 / 16 |
| Speer SB to W 14th Ave | 342 | 13 | 10 | 75 / 242 | 47 / 7 / 21 | 12 % / 8 % | 10 % | 7 | 7 | 1 | 6 | 15 / 21 |
| 14th Ave E to Logan | 1,367 | 53 | 43 | 320 / 1,110 | 235 / 16 / 65 | 10 % / 10 % | 11 % | 73 | 26 | 18 | 51 | 100 / 168 |
| Logan N to Colfax | 180 | 4 | 2 | 26 / 87 | 25 / 0 / 1 | 12 % / 2 % | 8 % | 4 | 3 | 1 | 5 | 5 / 13 |
| Colfax W to S/F | 216 | 7 | 9 | 55 / 132 | 46 / 1 / 7 | 14 % / 5 % | 8 % | 10 | 6 | 2 | 11 | 14 / 29 |

(Crosswalks and stop bars counted by the leg whose lap point is nearest; a junction's crosswalks fall to one leg.)

## Refutation (build, refute, repair)

Each round: overlays of the current inventory on **fresh** boxes not used for tuning (junctions and mid-block stretches spread round
the lap: Speer, 15th St, Blake, Kalamath / Santa Fe and W 14th Ave in every round), read critically, false marks, misses and
misplacements counted, causes fixed, everything re-run. Counts are by eye; files in `refutation/`.

**Paint**

| Round | Boxes read | Measured: precision | Real marks: recall | Detected: precision | Causes found → fixed |
|---|---|---|---|---|---|
| 1 | 4 of 20 | 0.89 (98 items) | 0.90 | 0.47 | the look-window reached past kerbs onto plazas and roofs → width per OSM lanes; lidar ground within 0.75 m (was 1.5); weak older-year and shadow-gain marks dropped; lidar contradiction grades lone bars detected |
| 2 | 3 of 20 | 0.89 (37) | 0.86 | 0.67 | the gutter's lip read as a solid line → a kerb / edge test in the tile stage |
| 3 | 20 of 20 | 0.92 (215) | 0.91 | 0.68 | lines wandering along a shadow's stepped edge → a smoothness test grades them detected |
| 4 | 12 of 20 | **0.93 (157)** | **0.92** | 0.65 | **none new**: every error was of a kind already named and left unfixed (below). The loop stopped. |

Left unfixed, and why: paint on bright concrete (Stout) needs a second reader for light pavement; the light-rail slab's edges and
crossing borders are bright bands on the roadway that the colour reader cannot tell from paint; off-street parking stripes inside the
look-window are real paint within reach of the street line. Each counts as an error in every round.

**Posts**

Fresh boxes each round, 10 junctions and 10 mid-block stretches, read by a reader who had not read panels there; the inventory's
squares drawn on 2022 beside 2020. Precision counts a real post at the wrong class or 1.5–2 m off as found (strict: only fully right).

| Round | Squares | Precision (strict) | Recall | Errors found | Causes → fixed |
|---|---|---|---|---|---|
| 1 | 108 | 0.94 (0.94) | 0.93 | 8 missed (6 small sign posts), 4 class, 2 false, 1 misplaced | small sign posts at corners and islands missed by both passes → **a sign-post pass at every junction** (62 added) |
| 2 | 152 | 0.93 (0.86) | **0.97** | 9 class, 8 false (3 on another post's shadow, 2 meters), 3 misplaced, 2 duplicate, 4 missed | eye placements snapped to any stroke end within 2 m → **1 m**; readers disagreed on tall poles with heads and no arm → **the class definition settled** |
| 3 | 124 | 0.95 (0.89) | 0.97 | 7 class, 6 false (3 meters), 1 misplaced, 3 missed | the definition had not been applied to labels made before it → **applied lap-wide from each post's own eye note** (12 reclassed) |
| 4 | 105 | **0.97 (0.94)** | 0.94 | 6 missed (3 globe lamps, 2 signs), 3 false (1 meter), 2 lamps 1.8 m off, 1 class | **none new**: every error is of a kind named in rounds 1–3. The loop stopped. |

Every error each round found was fixed in the inventory (its misses added through `eye/verdicts_refute_r*.json`, the rest in
`eye/corrections.json`), so the rounds' numbers describe the inventory BEFORE their own fixes. What remains, by the rounds' evidence:
a few small posts and globe lamps missed per 20 boxes (under trees, in shadow), meters now and then taken for sign posts, a post here
and there 1.5–2 m from its foot.

## Decisions made without Kevin, and why

1. **Three flight years, 2022 as the state.** 2022 is the surveyed state (D8); 2020 and 2018 fill what 2022 hid and grade by agreement.
   A mark only in older years stays detected and is flagged possibly removed when 2022 shows bare pavement there.
2. **Corridor 30 m about OSM's line** (the brief's "about 15 m each side" of a pavement up to 17 m wide on a line not always centred).
   Posts: 25 m.
3. **The look-window is narrowed by OSM's lane count** (OSM says where to look, never where anything is).
4. **Shadow gain** for tower shadows downtown, and per-tile white balance (2018's warm cast failed the asphalt test).
5. **The width model** (box blurred by the picture's point spread) replaces area / length; the nearest MUTCD width is given beside
   the measured one, never in place of it.
6. **Crosswalk bars inferred only where the 2022 picture is hidden** at that spot; a gap over visible pavement stays a gap.
7. **Symbols by exemplar, not by a feature rule.** A first rule-based arrow typer called 1,300 things arrows; a gallery showed most
   were not. Replaced by exemplars cut from this imagery and named by eye, with a threshold set on the gallery.
8. **Every post by eye.** The shadow reader's precision (0.23) is far too low to stand alone; the eye classed all 1,942 candidates
   and added 336 misses (a dedicated sign-post pass at every junction among them). The reader's verdict is kept beside the eye's on every post.
9. **The sun's bearing per tile from the posts the eye confirmed** (second pass): 2020's flight lines differ by an hour or more.
10. **No heights** (above). **No Mapillary** (no key in this session; E3 stands for later).
11. **Signal nodes on lap ways that run past the lap are declared not surveyed**, not "none found".
12. **`signal_post` covers any pole with heads and no arm over the road**, tall or short, with `carries_lamp`: the readers disagreed,
    and the build needs the heads more than the pole's height class.
13. **Eye placements snap to a shadow's foot only within 1 m** (2 m put some on another stroke's end).

## Not done / open

- Heights of posts (needs the flight hours or a clean sun elevation per flight line).
- Bicycle symbols, BUS / ONLY legends, green crossbike blocks as types; paint on Stout's concrete.
- What posts carry; every sign's position and face (street-level imagery, E3).
- Stout under the Convention Center (Kevin's captures).
- The free-roam grid (D4): this survey is the lap's corridor only.

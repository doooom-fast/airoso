# Drive-test report — san_diego_lake_murray build 0.17.0 (race corridors, ledger 0049) — 2026-10-1\_

> Pre-filled for Kevin from `fleet/templates/DRIVE-TEST-REPORT.md` (2026-10-11). Fill in the blanks after the
> drive; short answers are fine, screenshots beat prose. **Only this drive closes the loop** — every gate below
> was green on a scratch copy, and none of them has sat in the car.
>
> Findings become ledger entries via the `track-feedback` skill. Nothing here claims a tier.

## Kevin's verdict so far

- **2026-10-12, build 0.17.1** (race corridors + mouth weld): *"is tracked with and race track layouts are
  incredible"* — read as "the track width and race track layouts are incredible" (dictation). Filed in ledger
  0049 "Drive verdict 1". The questions below are still open.

## What you are driving (and what changed since the last install)

The last install (0047, `8fbfa0e`) split the wide roads with ONE shared concrete wall down the middle, used by
both race versions. A flood-fill check found 11 ways per version to get through to the other side (the three
bridges had no wall, the middle wall had two loose ends, and every median island could be driven across).

This build (0049) gives **each race direction its own track**:

- **Your lane** is about as wide as Alvarado (11.4 m between the walls), on **your own side** of every road:
  a concrete K-rail along your curb, and a **second K-rail closing off the opposite lanes**. Beside a median
  island that second wall runs along your side of the island, nose to nose, so the island is behind it.
- **Alvarado and the I-8 bridge deck are the whole street** (no closing wall), from the bridge, round the corner
  onto Alvarado, down Alvarado and round the College hairpin.
- **Open intersections at the three corners the race turns at**: College/Navajo, Navajo/Jackson and
  Jackson/Lake Murray Blvd. The full intersection is yours; the closing wall ends by angling into the far
  curb wall at the intersection's edge (no loose end anywhere).
- **Side streets are sealed** (the curb wall runs straight across them).
- **Kerbs**: red/white at the corners. NEW in this build: no inside kerb at College/Navajo or Navajo/Jackson
  (the road surface folds over itself on those two inside corners, and a kerb there sat under the asphalt),
  and the hairpin's inside kerb is shorter (it now stops about 4 m before the apex instead of wrapping round it).
- Each version loads only **its own** closing wall: the clockwise wall stands in the anticlockwise lane.

Install: `bash tools/ship_sd.sh --skip-blend --force-install` with **Assetto Corsa and Content Manager closed**
(the install refuses while either runs). Content Manager shows three layouts under "K10 - San Diego (V3)",
`[build 0.17.0]`.

## Install  → T2
- Folder: `content/tracks/san_diego_lake_murray_v3` (build 0.17.0) · method: ship_sd install
- Installed without errors? Y / N
- All three layouts listed in CM (Street Loop, Race — Clockwise, Race — Anticlockwise)? Y / N
- Each loads to the grid without a crash? Street Y / N · Clockwise Y / N · Anticlockwise Y / N — if not, attach the AC/CM log
- **Load time** (CM "Drive" to the car on the grid): Clockwise \_\_ s · Anticlockwise \_\_ s · Street \_\_ s
  (each race version now loads one extra ~5 MB file for its closing wall)
- Screenshot of the car on the grid:

## The spots to look at — Race — Clockwise
Lap order: Alvarado westbound → College hairpin → College northbound → **College/Navajo** (right) → Navajo
eastbound → **Navajo/Jackson** (right) → Jackson south → **Jackson/Lake Murray Blvd** (right) → Lake Murray Blvd
southwest → I-8 bridge → corner onto Alvarado.

| # | Where (street) | What to look for | great · ok · wrong · broken | Note / screenshot |
|---|---|---|---|---|
| C1 | **Grid on Alvarado** (whole street, line at the start/finish) | 8 grid slots, staggered; the outer cars sit about half a metre off the curb wall. Room to launch without touching it? | | |
| C2 | **College hairpin** (bottom of College, whole street) | The intersection is all yours. Inside kerb is shorter now — does the apex still read? Any wall where you don't expect one? | | |
| C3 | **Leaving the hairpin onto College** | The closing wall starts here, angling in gently (about 1 m sideways per 6 m forward). Clear where your lane is? | | |
| C4 | **College beside the three median islands** | Your lane narrows to about 6.9 m between the curb wall and the wall along the island (the tightest stretch of the lap). Racing room? Two cars side by side? | | |
| C5 | **Into the College/Navajo intersection** | The closing wall angles away into the far curb; the whole intersection opens. Inside kerb is GONE here (road fold) — does the corner still read without it? Outside kerb ends at the intersection edge. | | |
| C6 | **Exit onto Navajo eastbound** (the ledger's v1521 funnel) | The steepest squeeze on your lap: the wall closing the westbound lanes angles in at about 1 m sideways per 3.6 m forward (the Navajo median starts 57 m later). Does it catch you on the exit? Hit it once on purpose at speed: does the car ride up the wall's sloped foot and over into the closed lanes? | | |
| C7 | **Navajo beside the median islands** | 6.9 m lane again, wall along the island nose to nose. | | |
| C8 | **Navajo between the islands, Jackson, Lake Murray Blvd** (the 17 m roads) | Two parallel K-rails on your left: the closing wall, and 3-4 m behind it the far curb wall with an empty dead lane between them, for about 6.7 km of the lap. Does it look right or like a wall too many? Lane paint shows along the foot of the closing wall (about 9 cm of the dashed line) — OK? | | |
| C9 | **Into the Navajo/Jackson intersection** | The closing wall angles away at about 1 m per 3.3 m. Inside kerb GONE here (road fold — it used to vanish under the asphalt right at the apex your AI line uses). | | |
| C10 | **Exit onto Jackson south** | Gentle funnel (1 m per 6 m). | | |
| C11 | **Jackson/Lake Murray Blvd intersection**, in and out | Open box, gentle funnels both ends, inside kerb still there. | | |
| C12 | **Lake Murray Blvd onto the I-8 bridge** | The closing wall ends at the bridge deck (it angles out at 1 m per 10 m) and the whole bridge is yours. | | |
| C13 | **Corner from the bridge onto Alvarado** (the lap seam) | Rough patch known from before; any new wall issue? | | |
| C14 | **Wherever the closing wall meets the curb wall** (the ends at each intersection, the hairpin exit, the bridge) | Any flicker or shimmer where the two wall tops overlap? | | |

## The spots to look at — Race — Anticlockwise
Lap order: Alvarado eastbound → corner onto Lake Murray Blvd and over the I-8 bridge → Lake Murray Blvd northeast → **Jackson/Lake Murray
Blvd** (left) → Jackson north → **Navajo/Jackson** (left) → Navajo westbound → **College/Navajo** (left) → College
southbound → College hairpin → Alvarado.

| # | Where (street) | What to look for | great · ok · wrong · broken | Note / screenshot |
|---|---|---|---|---|
| A1 | **Grid on Alvarado** | As C1, the other way round. | | |
| A2 | **Alvarado just before the corner onto Lake Murray Blvd** | The AI line slows to about 83 km/h here — does that look like a sane braking point? | | |
| A3 | **Off the I-8 bridge onto Lake Murray Blvd** (the ledger's I-8 funnel, about 80 m long) | The only squeeze you take at full speed: the closing wall angles in at about 1 m sideways per 10 m forward right as you leave the bridge. Does it feel like a trap at speed? Hit it once on purpose: does the car climb the wall's sloped foot? | | |
| A4 | **Lake Murray Blvd, Jackson, Navajo between the islands** (17 m roads) | As C8, mirrored: closing wall on your left, dead lane behind it. | | |
| A5 | **Jackson/Lake Murray Blvd intersection** | Open box, gentle funnels. | | |
| A6 | **Navajo/Jackson intersection, exit onto Navajo westbound** (the ledger's v2311 funnel) | The steepest squeeze on the whole track: about 1 m sideways per 3.3 m forward as the full intersection narrows back to your lane. | | |
| A7 | **Navajo and College beside the median islands** | 6.9 m lane, wall along your side of each island. | | |
| A8 | **College/Navajo intersection, exit onto College southbound** (the ledger's v1506 funnel) | 1 m per 4.7 m squeeze on the exit. | | |
| A9 | **College hairpin** | Whole intersection yours; the hairpin's inside kerb is shorter now. | | |
| A10 | **Wall joints** | As C14. | | |

## Laps  → T3
- Race — Clockwise: laps attempted \_\_ · clean laps \_\_ · Race — Anticlockwise: laps attempted \_\_ · clean laps \_\_
- **Can you get to the other side anywhere?** (through a gap, over an island, round a wall end, off a bridge) Y / N — where
- Fall-through anywhere? Y / N — where
- Invisible walls or phantom collisions? Y / N — where
- Car-breaking bumps or launches (including over a wall after a hit)? Y / N — where
- **Direction**: does the field launch the way the grid faces, and does AC agree you're going the right way? Clockwise Y / N · Anticlockwise Y / N
- **FPS** on the College/Navajo intersection \_\_ and on the I-8 bridge deck \_\_ (Clockwise) · \_\_ / \_\_ (Anticlockwise) — compare with the Street Loop at the same spots: \_\_ / \_\_

## AI  → T4
- **AI race with 7 opponents** (the grid has 8 slots, so 7 is the most): Clockwise — do they get through the three
  intersections and the exit squeezes without piling into the walls? Y / N — where · Anticlockwise Y / N — where
- Do they cope two-wide on the 6.9 m island stretches? Y / N
- Does the AI complete a lap on its own? Clockwise Y / N · Anticlockwise Y / N — where does it leave the lane
- Lap time: Clockwise \_\_\_\_ · Anticlockwise \_\_\_\_ (the AI lines are generated drafts, not recordings; a big gap is information)
- Timing and sectors fire? Y / N

## Worst three spots — street names, please
1. \<spot\> — what's wrong — screenshot / timestamp:
2. \<spot\> — what's wrong — screenshot / timestamp:
3. \<spot\> — what's wrong — screenshot / timestamp:

## Look & feel  → T5
| Area / asset | great · ok · wrong · broken | Note |
|---|---|---|
| The lane width (Alvarado-wide everywhere) | | |
| The second wall on the 17 m roads (two K-rails, dead lane between) | | |
| The open intersections | | |
| The kerbs (two inside kerbs gone, hairpin's shorter) | | |
| Street Loop unchanged from last time? | | |

Knobs to turn after this drive, one each (ledger 0049): lane width on the 17 m roads (own side only would be
about 7.7 m with the wall on the centre line), the median stretches (wall on top of the island instead, +1 m of
lane), the steep exit squeezes (start them inside the intersection), the far curb wall behind the closing wall on
the 17 m roads, a centred grid.

## Does it feel like the place?  \_\_ / 5
One sentence why:

## Verdict
Clockwise: ☐ NOT INSTALLABLE  ☐ LOADS, NOT DRIVABLE  ☐ **DRIVABLE** (3 clean laps)  ☐ **AI LAPS IT**  ☐ **LOOKS RIGHT**
Anticlockwise: ☐ NOT INSTALLABLE  ☐ LOADS, NOT DRIVABLE  ☐ **DRIVABLE** (3 clean laps)  ☐ **AI LAPS IT**  ☐ **LOOKS RIGHT**

Recording: \_\_\_\_
The one thing you most want fixed next: \_\_\_\_

# Del Mar IMSA circuit (1987–1992) — sources

Step 1 of `docs/DEL-MAR-RESEARCH-PLAN.md` §4. Every row: URL, date fetched, what it gave, and whether the page
was **read** (opened in the Windows box's browser) or is **snippet** (search result text only). Kevin,
2026-11-01: the track is era **B**, the IMSA circuit of the 80s–90s, a `circuit_port`; the 1960s SCCA
parking-lot course (era A) is history only.

## Read (page opened)

| Source | Fetched | What it gave |
|---|---|---|
| https://www.na-motorsports.com/Tracks/CA/DelMar.html (Guy Watney, Kansas City Region SCCA; page licence CC-NC-SA, 2005–2007) | 2026-11-01 | Both layout drawings as GIFs: 1960s course `images/delmar/delmar0.gif`, **IMSA 1987–92 course `images/delmar/delmar1.gif` (480×240)**, each with a north arrow and start/finish flag. Text: "a 1.6-mile temporary street course set up in the parking lot of the Del Mar Fairgrounds … used in the mid-1960s. A different 1.6 mile track, built on the same site, was used by IMSA in 1987-92." Address given as Jimmy Durante Blvd & Turf Rd; lat/lon 32.973766, -117.258443; elevation 13 ft. The drawings are **not georeferenced** and not to a stated scale. Licence is non-commercial share-alike: store the URL, hand-trace a readable intermediate; do not ship the GIF. |
| https://www.racingsportscars.com/track/Del%20Mar.html | 2026-11-01 | RSC covers 1958–1964 and 1987–1992, 121 events. Championships: West Coast, Pacific Coast (the SCCA era), IMSA / GTU / GTO / GT / Supercar (1987–92). |
| https://www.racingsportscars.com/race/Del_Mar-1988-10-23.html | 2026-11-01 | "Camel Grand Prix of Southern California", 23 Oct 1988, "Del Mar Fairgrounds Road Circuit, 2.570 kms", 2 hours, 27 started, attendance 33,000, cool and sunny. Pole Lammers/Brundle Jaguar XJR-9 **1:06.529**; fastest lap Brundle **1:09.18 = 133.996 km/h** (consistent with 2.570 km). Programme scans: cover, entry list, schedule; **"Track map is not available."** |
| https://www.racingsportscars.com/race/Del_Mar-1991-10-12.html | 2026-11-01 | Track map not available. |
| https://www.racingsportscars.com/race/Del_Mar-1990-11-11.html, …/Del_Mar-1987-10-25.html | 2026-11-01 | No track-map entry at all. |
| https://www.motorsportmagazine.com/database/circuits/del-mar/ | 2026-11-01 | Official name Del Mar Fairgrounds; co-ordinates **32.973626, -117.263250**; "Street Circuit 1987–1992, temporary street circuit, 1.6 miles"; also a 1-mile dirt oval, 1949 (the AAA/Indy cars). No layout drawing on the page as rendered (a consent dialog covers it; not accepted). |
| https://www.the-fastlane.co.uk/racingcircuits/Tracks/USA/DelMarFG.html | 2026-11-01 | **Not readable from this box**: Cloudflare bot check in the built-in browser, and the Wayback Machine's 2025-09-18 capture is the challenge page too. Snippets say: IMSA circuit 1987–1992, temporary, **counter-clockwise, 2.579 km / 1.603 mi**, its layout drawn "from an aerial survey flight", and that the layouts on Frank Sheffield's site and the GEL Motorsport page "seem to be a highly distorted version". This is the one page that ties the course to imagery — Kevin to screenshot it. |

## Snippet only

| Source | What it gave |
|---|---|
| Wikipedia 1987–1991 IMSA GT Championship season pages | Del Mar rounds: 1987-10-24 (GTO 1 h), 1988-10-22 (GTU 45 min), 1989-10-22 (GT 1 h), 1990-11-10 (GT 1 h), 1991-10-12 (GT 1 h). RSC dates the headline GTP races a day later each year (Sunday). |
| https://en.wikipedia.org/wiki/Del_Mar_Fairgrounds | Lists the 1992 Vons Grand Prix of San Diego; lap record 1:06.390 Dan Marvin, GTP Lights. Address 2260 Jimmy Durante Blvd. |
| https://library.revsinstitute.org/imsa-camel-gt-san-diego-grand-prix/126573 | Revs Institute photo record of the 1992 "IMSA Camel GT San Diego Grand Prix", venue "Del Mar Fairgrounds Road Circuit". Photo hunt candidate. |
| https://www.racingphotoarchives.com/classic/del-mar-fairgrounds-1988-dan-gurney/ | A 1988 paddock/track photo (Dan Gurney). Photo hunt candidate. |
| YouTube `yJ84S9eTHRs` (1987), `e8zZ3brQpac` (1988) | ESPN Speedworld broadcasts. Corner-by-corner landmark source (plan step 4), not yet watched. |
| https://racingyears.com/race/1991_IMSA_Supercar_Del_Mar | "Del Mar Fairgrounds Road Circuit, 2.57 km", 1991-10-13. |

## Disagreements (plan §1), status

- Length: 2.570 km (RSC, racingyears) vs 2.579 km (Fastlane) vs "1.6 mi" (Motor Sport). 9 m apart; the drawing cannot resolve it. Take 2.57 km until the aerial trace measures it.
- Direction: **counter-clockwise** (Fastlane snippet) and the NA-Motorsports drawing's start-line arrow agree.
- Dates: Wikipedia's season tables give the Saturday support race; RSC gives the Sunday GTP race. Both right.
- Did the course change 1987→1992? Unknown. The old grandstand came down in 1991 and the new one opened 1993; the 1991–92 course may differ. Not yet checked.

## Georeferencing state

No georeferenced evidence yet. The NA-Motorsports drawing gives shape, direction and start position only.
Candidates, in order: the Fastlane's aerial-survey layout (blocked here), Google Earth Pro historical imagery
1989–1994 (Kevin's machine), USGS NAPP frames, UCSB FrameFinder. Current NAIP is public domain and is the
base the trace will sit on; the 1980s lot edges are what must be confirmed against the old imagery.

## Data pulled (2026-11-01, scratch only, not committed)

- OSM drivable + service network for the box S 32.9690 W -117.2670 N 32.9790 E -117.2530, fetched fresh
  (`tools/fetch_osm.py --bbox … --service`, overpass-api.de, OSM data as of 2026-11-01T19:35Z): 299 ways,
  1217 nodes. Named: Jimmy Durante Boulevard (secondary), San Dieguito Drive, Turf Road (service), Infield
  Tunnel (service), the 24th–28th Street grid west of the grounds, Heather Lane. The fairgrounds' lot aisles
  are unnamed service ways. Via de la Valle lies just north of the box.
- Read on Google Maps imagery (2026): Jimmy Durante Blvd leaves Via de la Valle at the north-east corner by
  the Hilton, runs south-west along the east side of the main lot, turns west along the San Dieguito River
  south of the exhibit halls, and crosses the river at the bridge by Viewpoint Brewing. Turf Rd is the
  north-east service entrance by the golf centre. The horse oval and grandstand occupy the west half; the
  exhibit halls the south-west; the big lot the east. **Working hypothesis, unproven:** the IMSA drawing's
  long straight (north-east → south-west, counter-clockwise) lies along that east side, with one loop at the
  Turf Rd corner and the other by the grandstand end. To be tested against 1989–92 imagery, not assumed.

## The drawing, fitted (2026-11-01, provisional)

- The NA-Motorsports 1987–92 GIF was reduced to an ordered one-pixel loop (1190 points; pit lane, flag, start
  arrow and north arrow masked), scaled by the 2.570 km lap: **1.886 m per drawing pixel**, loop extent
  **885 × 424 m**. Scratch: `drawing_loop.json`, `extract_loop.py`, `overlay.py`, `refine.py`.
- Placed north-up as drawn, the loop crosses the horse oval and the lagoon: **the sketch's north arrow is wrong.**
  Rotated ~45° (long axis north-east → south-west) it lies on the grounds: the long straight along the east lot,
  one hairpin at the Turf Rd corner, the other around today's exhibit halls by the river. 40° puts the north
  hairpin in the dirt overflow lot east of Jimmy Durante Blvd, 50° puts it in the barns. Because the event was
  billed a "street circuit", the boulevard itself may have been part of the course; the 2012 lots are not the
  1988 lots. **Not yet pinned**; the drawing's aspect may also be distorted.

## Video (ESPN Speedworld, 1988 race, YouTube e8zZ3brQpac, 2:26:14, read 2026-11-01)

| t | What it shows |
|---|---|
| 0:12 | Pre-race stand-up in front of the fairgrounds' Spanish tower (the old grandstand entrance tower), balloons. |
| 3:30 | Start/finish straight from behind the grid: white concrete walls both sides, palms, the tower ahead-left, a Camel bridge banner across the track. |
| 8:00–10:00 | Grid rows 3–13 graphics. |
| **11:00–12:00** | **ESPN track map: "10 Turns, 1.6 Miles"**, camera positions marked. Same general shape and orientation as the NA-Motorsports sketch. Captured for comparison. |
| 13:20 | Cars past a wooden fence line with white walls, palms, a house roof behind: a residential edge is visible from the course. |
| 15:00 | A Dodge bridge over a long sweeping curve, team transporters on the inside. |

Viewer comment (sergioleone3583): "action in turn one that day". NavyCorpsman1967: "Del Mar was like a cage match."
| 12:15 | Pace lap, high camera: a wide parking-lot section, painted stall lines beyond the walls, team transporters parked in the lot to the right (the paddock was in the lot). |
| 12:30–12:45 | Rolling start on the main straight: temporary bleachers full on the left (outside), pit wall on the right (inside), Camel banners. Pits on the inside agrees with the sketch's pit lane. |
| 13:10 | Entry to a curve with hills behind. |
| 25:00 | A hairpin with bleachers and a sponsor-board wall on the outside, red/white kerbs, lot paint lines under the cars. |
| 55:00 | A straight running toward a hillside of white houses (Del Mar village bluff or the Solana Beach side; not yet resolved). |
| 1:10:00 | The Spanish tower shot against eucalyptus hills, race title card. |
| 2:10:00 | A corner's sponsor wall (Miller, Quaker State, Camel, Goodyear, Yokohama) with a **flat-topped mesa and bare cut face** behind it: the bluff at the I-5 / Via de la Valle interchange. The corner complex looks north-east over open ground → it sits at the north-east end of the grounds. |

Captions: none on the video. Seeking triggers mid-roll ads, so sampling in the browser is slow; a local copy
(yt-dlp, ~1–2 GB per broadcast) sampled every 10 s into contact sheets is the efficient route — Kevin's call
(download). The 1987 broadcast (`yJ84S9eTHRs`) is unwatched.

**Dressing seen (for the asset plan):** white concrete K-rail both sides with debris fence on top at corners;
wooden plank fence lines on the outside; temporary aluminium bleachers along the main straight and at the
hairpin; sponsor-board walls at corners (Dodge, Chevron, Yokohama, Toyota, Miller, Quaker State, Camel,
Goodyear — trademarks, to be rendered as period-coloured generic boards); Camel and Dodge sponsor bridges;
red/white painted kerbs; parking-lot stall paint under the racing line; palms; the fairgrounds' Spanish tower;
team transporters in the paddock lot.

## The 1987 broadcast (ESPN, YouTube yJ84S9eTHRs, 2:00, downloaded 2026-11-01 with Kevin's OK, 480p) — AERIALS

ESPN flew the course from a helicopter and had the Goodyear blimp up. Reference stills (broadcast frames, research
reference only, never shipped) are in `frames/`. What they establish, read 2026-11-01:

| t | Frame | What it shows |
|---|---|---|
| 2:09–2:12 | title aerial, looking south along the coast | The oval lower-left with its infield lakes; the course in the lots **south-east of the oval**, between the oval and the river; Del Mar village on the bluff beyond. |
| 3:30 | aerial of the pit straight | Pit lane with striped awnings over the pit boxes, a footbridge, bleachers, the start/finish gantry. |
| 7:27–7:30 | "T.2" | The big exhibit hall (today's hall at NAIP px 1450–1700 × 530–800) with **a block of bleachers between it and the main straight**; the straight ends in a near right-angle turn by the hall's end; paddock tents (striped) beyond; a return road along the far side. |
| 7:35–7:38 | "T.3" (near nadir) | A pointed hairpin wrapping the **paddock** (transporters, striped tents) with **the horse oval's track immediately beside it on the left** — the paddock hairpin sits against the oval's south-east curve. |
| 7:43–7:46 | over the hall | Order across the block, west → east: Spanish buildings and paddock tents / **pit lane** / **main straight** (walls both sides) / **bleachers** / **the big hall** / paddock trailers / **return leg** (walled, curving) / dirt lot with spectator cars. The hall is *inside* the loop; pits and paddock *outside*, as the sketch has them. |
| 7:51–7:54 | "T.6" | Oval's east turn and lake upper-left, barns top, the halls centre, the river right; the course visible along the halls and in the north-east lot. |
| 7:59–8:08 | "T.7", "T.8" (widest) | The **north-east hairpin** in the lot north-east of the halls, **west of Jimmy Durante Blvd** (dirt lot and the lagoon beyond it); the long straight past the halls; the return along the east. |
| 8:10 | "T.9" | A corner on open dirt by a red/white circus tent with a sponsor wall: the **south lot by the river**. |
| 21:05–21:08 | helicopter over the oval, looking north-east | Oval foreground with lakes; the paddock hairpin and tents against the oval; the straight and halls beyond. |
| 32:05 | blimp, wide, from the west | The whole grounds: oval, course lots, dirt lots, I-5, the river; too small to trace. |

Corner order from the tour (counter-clockwise): main straight → T1 near the hall's south-west end → T2 by the tents →
T3 the paddock hairpin against the oval → … → T6 by the halls → T7 → T8 the north-east hairpin → T9 on the river lot → T10 → straight.

### Fits tried and what they said
- Uniform scale from the 2.57 km lap puts the sketch at 885 × 424 m: too long for the grounds in any rotation.
- Affine fit to five ground anchors read off the frames (S/F by the hall, NE hairpin at NAIP px (1890,280), paddock
  hairpin at (1120,940), SE extreme at (1800,950)) **implies a lap of 1.43 km** — those anchors span too little ground.
  So the course used more than the strip between oval and boulevard: the T9 frame says it ran down to the river lot.
- A homography from by-eye control points on the 8:07 frame diverged (rms 950 px): the oblique VHS frame needs
  carefully clicked correspondences, not eyeballed ones.

**Status:** location and topology established from imagery; the centreline is **not yet georeferenced**. The clean
way is a click-to-georeference pass on frames 7:36, 7:45, 8:07 and 21:07 against the 2012 NAIP (hall corners, oval
rail, lake, road junctions), then tracing the walls; a small HTML page can do it and export GeoJSON.

## Georeferencing pass 2 (2026-11-01 afternoon): the tool, and what stopped it

- **Tool built:** `tools/georef.html` (+ `naip_2012_z18.jpg`, `naip_roads.js`): frame and NAIP side by side, click
  control-point pairs, Solve (normalized DLT homography, least squares), today's OSM roads reprojected onto the 1987
  frame as the sanity check, Trace mode for walls, Export (GeoJSON-ready lon/lat via the z18 tile georef), Save
  (localStorage), scripted API (`G.*`). Serve the research folder (`python -m http.server 8765 --directory docs/research/del-mar`)
  and open `/tools/georef.html`; a `.claude/launch.json` entry `del-mar-georef` does this. `fit_frame.py` in the
  scratchpad is the same solve in Python with a check image.
- **Result on the 7:45 frame:** four hall corners solve exactly but extrapolate badly (the straight landed on the
  oval). More points are needed away from the hall, and that exposed the real problem:
- **Today's fairgrounds are not 1987's.** On the 2012 NAIP the gap between the horse oval's outer rail and the big
  hall's west wall is ~58 m at the hall's north end and widens southward. In the 1987 frames (7:45, 7:54) the pit
  lane, main straight and a bleacher block all sit in that gap, and the gap *widens northward*. East of the hall the
  frames show transporters, the return leg and a deep spectator lot before Jimmy Durante Blvd; today the round arcade
  and ~60 m of lot fill that space. So the hall was rebuilt on a larger/shifted footprint and/or the lots and the
  boulevard were realigned in the 1991–93 grandstand rebuild. **Fixed features on today's imagery cannot be trusted
  as 1987 control points**, except the horse oval, the infield lakes and the barn rows.
- **What will settle it:** georeferenced imagery from the era. USGS NAPP/DOQQ frames (1989–1996) exist for the
  quad but EarthExplorer needs a login; Google Earth Pro (desktop) holds 1994 and ~1989 San Diego frames under the
  historical slider. One north-up frame from either, with the fairgrounds filling it, gives the 1987-era hall,
  lots and boulevard; the 7:45 / 8:07 / 7:36 broadcast frames then pair against *that* in the tool, and the oval
  ties it to today's NAIP. Alternatively 8–10 oval-and-lake-only control points on the 8:07 frame, which is slower
  and less certain.
- The sketch-based 45° overlay from the morning remains the only full-loop placement and is **not** to be built from.

## Build record (2026-11-01, Kevin: "Commit and build to an estimated historical layout")

- `tracks/del-mar/` scaffolded on the Exotics pattern (source.type aerial over the 2012 NAIP crop, trace_px = the
  sketch loop placed; DOSSIER.md marks every fact measured / video / estimated).
- Placements E2 → E4 (DOSSIER §2): each red drive_test pointed at the estimate touching fixed ground the course
  could not have used (the oval's dirt, the boulevard's river-side bank); the engine's stone-lip guards and
  wooden fences were the symptoms. E4 draft drive_test PASS. `scenery.fences: false` (the 1987 course was K-rail).
- Engine fix on the way: `scripts/ac/write_ai_line.py` fillet window lookback (IndexError, run 1), a03cbc3.
- Lap as built ~2.0 km vs 2.57 published: the open question for the correction pass (era imagery).

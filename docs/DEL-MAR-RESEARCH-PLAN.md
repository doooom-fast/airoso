# Del Mar temporary circuits — research plan

Status: **research only, nothing built, no track slug yet.** Opened 2026-11-01 from a Kevin aside (a YouTube
channel mentioned Del Mar as a historic temporary car-racing circuit; web search is polluted by the horse
track). This file records what is known, what is *not*, and how another agent finds the maps. It is the
precursor to a `fleet/templates/LOCATION-DOSSIER.md` if Kevin decides it is worth a track
(`street_port`/`circuit_port` question is open — see §6). Nothing here changes the Lake Murray priority
(ledger 0054).

## 1. What we think we know (from search snippets only — no page was actually read)

There were **two** temporary road courses on the Del Mar Fairgrounds. Keep them apart.

| | A. SCCA parking-lot course | B. IMSA street circuit |
|---|---|---|
| Era | ~1959–1964 (Racing Sports Cars lists regional/divisional events in 1959, 1960, 1963, 1964; e.g. 22 Nov 1964) | 1987–1992, each October |
| Where | the large parking area **west of Jimmy Durante Blvd** (per a John Straub blog post) | fairgrounds grounds; exact route unknown |
| Length | unknown | ~1.6 mi (Motor Sport Magazine DB) = 2.570 km (Racing Sports Cars, "Del Mar Fairgrounds Road Circuit") |
| Events | SCCA regionals | Camel Grand Prix of Southern California (1987–88), Nissan Grand Prix of Southern California (1989), Grand Prix of Greater San Diego → Vons Grand Prix of San Diego (1990–92) |
| Origin | — | 1985 CEQA filing "Southern California Grand Prix at Del Mar" (10-day interim-use lease, fairgrounds as lead agency) — state clearinghouse no. 1985110612 |

Disagreements to resolve, not paper over: 1988 race date (Oct 22 vs 23), 1987–88 class/duration
(GTO 1 h vs GTU 45 min vs GTP/Lights), and whether the IMSA course used the parking lots. Related but
**separate**: Torrey Pines road races (1951–56, old Army base streets); the 1951 race was first meant for
the Del Mar fairgrounds. A "Del Mar airport" race was *not* found — treat as unverified.

## 2. What is missing (the deliverables)

1. A **layout**: centerline, direction, corner count, pit/paddock/grandstand location, per year (the
   course likely changed 1987→1992).
2. **Georeferenced evidence**: at least one historic aerial or plan drawing that can be tied to today's
   fairgrounds with two control points (see `.claude/skills/aerial-tracing`).
3. **Photos/video** with enough landmarks to confirm the route.
4. Which structures existed then vs now (fairgrounds buildings, Jimmy Durante Blvd, the Via de la Valle
   / San Dieguito River edge, the racetrack/infield).

## 3. How another agent finds the maps

**Preflight — network.** In the cloud session, `motorsportmagazine.com`, `racingsportscars.com`,
`wikipedia.org`, `blogspot.com` and `ceqanet.lci.ca.gov` were **blocked** (DNS/403 from the proxy), so
every fact above is search-snippet level. Run `mcp__claude-code-remote__read_documentation` topic
`environment.network`, and ask Kevin to allow those hosts (or work from astra/a machine with open
internet). Do not claim a layout from snippets.

**Search terms that beat "Del Mar"** (the horse track swamps it): `"Camel Grand Prix of Southern
California"`, `"Grand Prix of Greater San Diego"`, `"Vons Grand Prix of San Diego"`, `"Nissan Grand Prix
of Southern California" 1989`, `IMSA "Del Mar Fairgrounds" 1988 circuit map`, `"Del Mar" IMSA GTP
Fangio Gordon 1991`. Use `site:` filters for the hosts below.

**Where maps actually live, in order of likely yield:**

1. **CEQA filing** — `https://ceqanet.lci.ca.gov/1985110612` (and `/1985110612/3`). Environmental
   reviews carry a site plan/vicinity map; request the full document from the 22nd District
   Agricultural Association (Del Mar Fairgrounds) if only the summary is online. Later years' leases
   and noise studies (City of Del Mar, San Diego County, California Coastal Commission files for the
   fairgrounds) often reprint the course outline.
2. **Racing Sports Cars** — track page `racingsportscars.com/track/Del Mar.html` and the per-event photo
   galleries (e.g. `/photo/Del_Mar-1988-10-23u.html`); event pages sometimes include a circuit diagram.
3. **Motor Sport Magazine database** — `motorsportmagazine.com/database/circuits/del-mar/` ("map, history
   and latest races").
4. **Event programs and period press** — IMSA race programs, *Autoweek*, *Road & Track*, *Motorsport
   Magazine* / *Racer* / *AutoWeek* archives (Google Books, archive.org full text), *San Diego
   Union-Tribune* and *Los Angeles Times* (Oct 1987–1992; LAT race stories often describe turns by
   name and the pit location). Archive.org full-text search: `"Del Mar" "IMSA" "turn"`.
5. **Historic aerial photography** (the true georeferencing source):
   - USGS EarthExplorer — NAPP/NHAP and high-altitude series, 1987–1992 frames over Del Mar.
   - Google Earth Pro "Historical imagery" slider (earliest coverage around 1989–1994) — check the
     October weeks if any frame lands then; stable fairgrounds markings may show course remnants.
   - historicaerials.com, UCSB FrameFinder / Map & Imagery Lab, SANDAG/County of San Diego aerial
     archive, Bing/Esri Wayback.
6. **Video** — YouTube "IMSA Camel GTP Del Mar 1987" (`yJ84S9eTHRs`) and "1988" (`e8zZ3brQpac`); also
   search `Del Mar 1991 IMSA`, `Vons Grand Prix San Diego`. Extract landmarks per corner; this is the
   cheapest layout evidence. Record timestamps in the notes.
7. **Local history** — John Straub's blog posts "Del Mar Road Races" (2010-12) and "Torrey Pines road
   races" (2011-08) for the SCCA course; San Diego History Center; Del Mar Historical Society; San
   Diego Auto Museum; ex-drivers' forum threads (Autosport Nostalgia Forum, The Chicane, Grand Prix
   Globetrotter columns).
8. **Photo hunt** — racingsportscars.com galleries, Getty/Alamy/Motorsport Images (search "Del Mar 1988
   IMSA"), IMSA/SCCA archives, Flickr, and the YouTube channel that prompted this (ask Kevin for the
   channel/video).

**Rules for whoever does this:** record every source URL with the date fetched and a one-line "what it
gave"; mark each fact *verified (read page)* vs *snippet only*; do not infer the route from today's
fairgrounds roads alone (L5 — never validate geometry against the data that placed it). Pull a map image
only when its licence allows storing it; otherwise store the URL and a hand-traced readable intermediate.

## 4. Plan

| Step | Output | Who/tier |
|---|---|---|
| 0 | Network preflight; confirm hosts reachable | session model |
| 1 | Read the 8 source groups above; fill `docs/research/del-mar/SOURCES.md` (URL, date, finding, verified?) | `sonnet`, effort medium (scouting) |
| 2 | Resolve the §1 disagreements; one table per circuit (A, B) per year | session model |
| 3 | Obtain ≥1 georeferenceable aerial/plan for IMSA course; two control points; trace per `aerial-tracing` → `data/centerline.geojson` candidate | session model, effort high |
| 4 | Corner-by-corner notes from the 1987/88 video | `sonnet` |
| 5 | Hand Kevin a go/no-go + a filled `LOCATION-DOSSIER.md`. File a ledger entry (`track-feedback`) only if Kevin wants it tracked | session model |

Exit criteria: a layout drawn on a georeferenced aerial that Kevin can eyeball, with sources, or an
honest "no recoverable plan" with the list of what was checked.

## 5. Not doing

No geometry, no kn5, no engine changes, no GPS-spline invention (docs/history/HANDOFF.md bans stand). No
new `tracks/` directory until Kevin approves the dossier.

## 6. Open questions for Kevin

- Which channel/video mentioned it, and which era did they mean (A or B)?
- Is this a track candidate (San Diego network side-quest) or just curiosity? Kind would be `circuit_port`
  if a defined course is recoverable (a shut-down temporary facility), else not buildable.

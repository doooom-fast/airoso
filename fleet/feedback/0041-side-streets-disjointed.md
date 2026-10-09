---
id: 0041
title: Side streets disjointed — built one OSM name at a time, not along Kevin's routes
status: in-progress
scope: tracks/san-diego-lake-murray (the Del Cerro neighbourhood sub-loop); tools
layer: track + tools
train: -
---

## Symptom (Kevin, seat, 2026-10-08, `san_diego_lake_murray_v3`)

> "side streets need to be cleaned up, do another pass, make sure they're not have sidewalks
> blocking them and that they connect correctly — right now there's a bunch of disjointed streets
> that don't connect in the path that I defined for you."

## Evidence

Top-down render of the pre-divide connectors + an end-to-road measurement:

| street (per-name connector) | problem |
|---|---|
| del_cerro_ave | ends 119 m from Del Cerro Blvd — the real path continues on **Madra Avenue** (never configured) |
| colorado | east end 132 m from anything; the route turns onto **Pennsylvania Lane** (never configured — OSM name is "Lane", not "Avenue") |
| connecticut | north end 140 m from Pennsylvania's — the link is **Delaware Avenue** (never configured) |
| wisconsin | ends 1.6 m short of Lake Murray Blvd's pavement edge |
| del_cerro_blvd | two carriageways as a loop ([0039](0039-del-cerro-is-a-divided-boulevard.md)) |

OSM lengths match the connector lengths exactly (nothing was dropped): the per-name method
(`extra_lines.py`: merge every way called X) simply cannot know which streets *link*. The links are
in `tools/route_tracks.py` / `data/routes.json` — Kevin's three confirmed routes as continuous
OSM node paths (medium: Airoso → Del Cerro Ave → Madra → Del Cerro Blvd; short: Airoso → Adelante
→ Colorado → Pennsylvania → Delaware → Connecticut → Wisconsin → Lake Murray Blvd).

## Fix (built this day)

`tools/route_connectors.py` (config `route.route_connectors`): the medium/short routes' off-loop
runs become connector polylines — judged against the FULL route's own raw node path (the built
mainline is median-shifted up to 12 m, which leaked 2 km of loop into the first attempt); 1.5 km
out-and-back routing spurs dropped; duplicates (medium/short share the chain) dropped BEFORE
end-to-end merging (merging first chained the chain to its own duplicate); live 3DEP elevation,
despiked/smoothed/grade-capped like extra_lines. Result: ONE 2,550 m polyline for the whole
neighbourhood chain + Del Cerro Blvd kept as the divided trunk. `tools/trim_connectors.py` now
trims against the mainline AND divided trunks (two passes), extends an end that stops short of a
host to the host's centreline, records mouths per host, and gaps the trunk's island at each mouth;
`tools/gap_mouths_blend.py` gaps the host's curb strip for connector hosts too (per-connector CURB
vertex blocks in connectors.local.json order).

## Verification

Kevin drives the medium and short routes end to end: no sidewalk across any mouth, every turn
onto the next street is paved through, Del Cerro Blvd is one boulevard. Audit K/I not up.

**Built 2026-10-08:** 4 mouths (Del Cerro × College both sides; chain × Lake Murray Blvd at
mainline vert 4424; chain × Del Cerro trunk at del_cerro_blvd#1 vert 82), 192 host curb faces
gapped, trunk island gapped on 11 points. Audit K 169 → 147, I 167 → 138, F 61 → 57; drive-test
unchanged (severe 0, obstruction 0). Installed as `san_diego_lake_murray_v3`.

**2026-10-09 (seat):** Kevin on the rebuilt V3 (TreeFX vegetation, dimmed lights, route-derived side streets): **"incredible."** Detailed verdicts (palm species/height, lamp style, each mouth) still to come from a full drive.

**2026-10-09 — "side street intersections, lots of hovering" (Kevin, seat).** Measured on the gate
OBJ: every side-street end sat BELOW its host deck — Del Cerro × College −0.23 / −0.70 m, Wisconsin ×
Lake Murray −0.10 m, Madra × Del Cerro trunk **−0.91 m** — the cuts had never been height-matched.
`trim_connectors` now lands each cut on the host's centreline height and blends the piece's last
30 m onto it. After: all four mouths flush (host deck +0.10..+0.12 m over the side-street end, i.e.
the two ribbons' own 0.10 m lift — level). Seating: the Del Cerro hilltop loop 28 pokes / 37 floats
(worst 2.58 m) → 7 / 5 (worst 0.55 m); the neighbourhood chain 3 / 3 → 0 / 3 (0.40 m) —
`tools/seat_terrain_blend.py` (connector corridors only: the kn5 prep already seats the mainline)
+ `tools/slim_far_terrain_blend.py` (far terrain decimated 0.35 so the prep's grass tiles stay
under the 65,535-position cap — it refused twice at 67–72k).

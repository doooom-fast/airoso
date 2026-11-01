---
id: 0064
title: Del Mar Grand Prix — the 1987-92 IMSA fairgrounds circuit as an estimated layout, gate-green through the chain
status: in-progress
scope: tracks/del-mar; scripts/ac/write_ai_line.py; docs/research/del-mar
layer: project + engine
train: -
---

## Ask (Kevin, 2026-11-01)

> "Del Mar should be a historic racetrack from the 80s to the 90s that existed, likely including the Del Mar Fairgrounds in some way."

> "You can figure out from the shape of the track and the aerial map how they would go, right?"

> "Commit and build to an estimated historical layout of the city that would match."

## What was found (docs/research/del-mar/SOURCES.md)

- The IMSA Camel GT ran the **Camel Grand Prix of Southern California / Grand Prix of (Greater) San Diego** on a temporary
  walled circuit through the Del Mar Fairgrounds lots each October 1987–1992: 2.570 km published, counter-clockwise,
  10 turns, Jaguar XJR-9 pole 1:06.5 (1988), 33,000 people. Nothing of it survives; the 1991–93 rebuild moved the hall
  and the lots, so today's imagery holds 1987's fixed features only in the horse oval, its lakes and the barn rows.
- The only layout drawings (NA-Motorsports; ESPN's 1988 on-air map) are the same TV-graphic shape, not to scale.
- The **1987 ESPN broadcast's helicopter aerials** (downloaded with Kevin's OK) fix the topology: pit straight along the
  hall block with pits outside and bleachers inside, a pointed paddock hairpin against the oval, the body of the loop
  south and east of the hall, the east lobe toward I-5, one corner on the river lot. No frame can be georeferenced
  by eye against today's ground (that is what moved: `docs/research/del-mar/tools/georef.html` is the tool for when a
  1989–96 frame exists).

## What was built

`tracks/del-mar/` (circuit_port, `race_circuit`): the sketch loop skeletonised to 1 px, placed north-up on the 2012 NAIP,
x-scaled hairpin apex → east lobe apex, y-capped at the bottom, inside the envelope the aerials and the fixed ground allow.
Four placements: E2 and E3 red on `drive_test` because the estimate touched ground the course could not have used (the
oval's dirt; Jimmy Durante's river-side bank — the engine's stone-lip guards and fences were the symptoms); **E4 green**.
`scenery.fences: false` (the course was K-rail; the engine's wooden warning fences floated over the boulevard cut).
Through `tools/ship_track.sh del-mar --no-install` on the Windows box, workshop `D:/k10-workshops/del-mar`, 2026-11-01
15:23 MST: `verify_kn5` PASS, **`drive_test` PASS** (lap 1.97 km, ground on top 0, floating 0, severe 7 at s 1131–1137
of ≤7.9 cm, bumps 22.8/km, excursion drops 1 gated (0.20 m at s 301, the north boulevard crossing) / 2 far ledges,
obstructed 0, replication 0.02 / 0.38 / 2.48 m), **`audit_mesh` CLEAN**, **`kn5_ground_check` PASS** (walls 106 /
hovering 0, shoulder underside 100 %, deck-vs-mountain p95 +0.014, road-over-ground 3/581). kn5 124.4 MB, md5 d924754d….
**Not installed** — Kevin's call.

## Open, by design of an estimate

- **Lap 2.0 km as built against 2.57 km published.** The TV map's proportions do not fit the grounds at 2.57 km; the real
  course may have used more of the north-east lot, or run differently in the east. The correction pass needs one
  georeferenced era frame (USGS NAPP 1989–96 behind an EarthExplorer login; Google Earth Pro's 1994 / ~1989 San Diego
  history). Then: pair the broadcast frames in the georef tool, re-place, re-run from `aerial`.
- Dressing (DOSSIER §8: K-rail + debris fence, bleachers, sponsor bridges as plain spans, palms, the Spanish tower) is
  bespoke work, none done.
- 7 severe steps of 6–8 cm at s 1131–1137 (the bottom lot's edge in 3DEP) pass the gate but are a real bump to feel for.

## Engine fix carried

`scripts/ac/write_ai_line.py` `fillet_corners`: run 1 died in `build_line` (IndexError) — after a splice shortened the
line within a sweep, a cluster at index 3–4 built a window whose heading lookback `P[wrap(s - 2)]` wrapped past the new
end. Guard widened to `s < 2 / e + 2 >= n` (a03cbc3). Same family as ledger 0060's seam fix, other trigger.

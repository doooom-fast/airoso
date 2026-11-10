---
id: 0059
title: "i have concerns our high plains isn't accurate" — High Plains rebuilt on the full 2.54-mile OSM course, the real start line and a measured 10.5 m width
status: diagnosed — all four gates PASS on v0.67.0 (drive_test, audit CLEAN, verify_kn5, kn5_ground_check); packed build/high_plains_v0.67.0.zip; not installed, no seat verdict
scope: tracks/high-plains (proof case); engine scripts/gps/centerline.py (start_at foot point) and scripts/geometry/build_mesh.py (shoulder over corner runoff) reach every track that builds through them
layer: project + engine
train: -
---

## Symptom

Kevin, 2026-10-27 (to astra) and 2026-10-28: "sand creek first and then high plains, i have concerns our high plains
isn't accurate". The July build (v0.66.3) was the 2.00-mile short course: its config itself said the north section
was left out because OSM had a 110 m gap there (L1), its width 12.0 m was "INHERITED FROM THE FABRICATED CONFIG and
unverified", and its `route.start_at` still pointed at the old fabricated frame ~77 km away.

## Evidence

**The course (OSM, fetched 2026-10-28, snapshot `data/osm.cache.json`).** Ladder To Heaven (289314483) now ends on
node 1454637805, which is vertex 7 of Prarie Corkscrew (132189632): the north section closes, nothing invented. The
full course, every way `oneway=yes` so OSM also records direction, in driving order: High Plains Drifter, To Hell On
A Bobsled, Ladder To Heaven, Prarie Corkscrew from node 1454637805, Full West, unnamed 289314485, Short North, Bikers
Berm, Niagara, Dannys Lesson = **4,092 m = 2.54 mi** (published 2.55; 51gt3 lists 4.104 km). Signed area negative:
**clockwise**, as the July research found from the PCA turn guide / LapMeta and the SCCA / 51gt3 listings say. Not in
the lap: unnamed 132189634 (172 m, the short-course cut-through) and Pit Lane 289311751 (691 m).

**The start.** The front straight is OSM "Full West": one 371 m segment at 101.7° (WSW→ENE), its midpoint
39.73504, −103.89449 — the July research's "REAL S/F: mid front straight ~39.7350, −103.8946". Pit lane 9–25 m
north of it (the July note: hot pits on the north side, driver's left).

**The width** (NAIP m_3910317_ne_13_060_20190913, 2019-09-13, 0.6 m, USGS/USDA public domain; cross-profiles every
0.3 m, median over ±10 m along each station). Every straight shows the same three layers: dark asphalt (NDVI
−0.25) to ~±4.2 m, a sharp bright non-yellow peak at ~±5 m (brightness 157–173: a white edge line blurred by the
0.6 m pixel — paint over asphalt predicts ~175), then dry grass at once. Edge-line centres: Short North 10.8 / 10.2 /
10.2, Bobsled 10.5, Dannys Lesson 10.5, Bikers Berm 10.5 → **10.5 m (34 ft), ±0.6 m**. Wider: the front straight
11.7 / 12.0 m (pit wall concrete at +9…+12 m north, pit-lane asphalt from +13 m) and the corner exit after it 12.6 m.
Two cruder reads were tried first and set aside, both recorded so they stay dead: NDVI half-max 9.9 m (it stops
inside the white line) and grass-yellowness half-max 12.3–12.9 m (it runs into the blurred verge). The overlays —
OSM line red, the found edge lines cyan — are `build/naip_width_edge_lines.png` (+ the two set-aside reads,
`build/naip_width_check*.png`; build/ is not committed).

**Elevation.** 3DEP: 1514.2–1540.2 m, 26 m of relief (SCCA: "70 feet" max difference), max grade 9.0 %.

## Diagnosis and fixes (in the order the build hit them)

1. **Project** — `source` from `from_track` (the July 2.00-mile `source/osm_fixes.json`) to `osm` with
   `route.roads` = the ten way ids in driving order (`build_ring` trims the Corkscrew at node 1454637805; all ten
   corner gaps 0.0 m); `route.start_at` = the front straight's midpoint; `default_width_m` 12.0 → 10.5;
   version 0.66.3 → 0.67.0. `source/osm_fixes.json` and `source/high_plains.kml` stay on disk, superseded.
2. **Engine, `centerline.build_centerline`: the start line on a segment.** The gps stage rotated the ring to the
   nearest *vertex* to `start_at` — the Full West node 185 m before mid-straight — and the projection stage, which
   rotates to the nearest resampled point, then rotated it again by 62 points (186 m) AFTER the elevation stage had
   sampled the line. Everything reading `centerline.elevation.json` by station read 186 m off: drive_test's
   replication vs measured road median **3.03 m**, p95 10.3 m (with the 62-point shift applied the same deck reads
   median 0.00, |median| 0.01 m — the geometry was right, the bookkeeping was not), and build_mesh's bridge
   detector judged every station against the wrong ground. Fix: when no vertex is within one resample step (3 m)
   of the start line, insert its foot on the nearest segment and make that station 0. After: no projection
   rotation, replication median **0.01 m**. The Lariat (nearest vertex 2.7 m) is unchanged by construction.
3. **Engine, `build_mesh`: the shoulder stood as a fin over the corner runoff.** drive_test then failed on 5
   excursion drops (limit 4). The worst, st 3450 on Ladder To Heaven, +11.0/+11.5 m, 0.32/0.75 m: the shoulder
   climbs a cut face to +1.15 m at +10 m and ends at +0.81 m at +11 m, while a flat `1RUNOFF_corners` apron at
   +0.05 m covers +8…+14.5 m under it — the shoulder drapes onto the bank as it stood before the grass is pinned
   down to the apron. Fix: a shoulder vertex standing over a corner runoff apron and above it snaps just under it
   (28 vertices). Applies only where `runoff.enabled` (race circuits; Sand Creek's street circuit has none).

## Verification

| | v0.67.0 first build | after fix 2 | after fix 3 |
|---|---|---|---|
| drive_test | FAIL | FAIL | **PASS** |
| replication vs measured (median / p95) | 3.03 / 10.33 m | 0.01 / 1.75 m | 0.01 / 1.75 m |
| excursion drops (limit 4) | 9 | 5 | **3** |
| soft-top / floating / obstructions / undrivable / daylight | 0 | 0 | 0 |
| severe steps | — | 1 (0.24 /km) | 1 (st 3712, 6.4 cm; limit 12 /km) |

`audit_mesh` CLEAN; `verify_kn5` PASS; `kn5_ground_check` PASS (every group 0.00 m, 368 walls 0 hovering,
road-over-ground 0/1172 > 0.05 m). The first build ran at 9.9 m (the NDVI read); the gated builds at 10.5 m.

The three excursions left (st 3752 +11.5, 2401 −10.0, 2703 −10.5; 0.13–0.15 m) are fill-edge seams on the
shoulder's embankment face with a 0025 stone lip standing on or just outboard of the drop rather than inboard of
it — inside the budget, not fixed here.

## Open

- **Not modelled:** the front straight's extra ~1.2 m and the wider corners (one constant width — `width_overrides`
  is parsed by `scripts/config.py` and consumed by nothing); the pit lane (OSM 289311751); camber (L10's 1.5–4 %,
  the off-camber T1 the July notes name). Each is its own change.
- Install on Windows and drive it: the tier is T1 (gates green) until a seat verdict.

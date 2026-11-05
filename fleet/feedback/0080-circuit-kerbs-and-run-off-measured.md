---
id: 0080
title: Racing kerbs and run-off for the circuits, measured off NAIP at its best (0.3 m 2023) and built on Lake Murray's engine
status: in-progress
scope: tracks/high-plains-lm, exotics-racing-lv-lm, aspen-lm, pueblo-lm, grand-junction-lm, milford-road-course-lm, pikes-peak-lm (not Sand Creek, the freeway, the rally stages or Lake Murray)
layer: project (measured inputs per track) + tools (opt-in keys only the circuits set)
train: -
---

Cites ledger 0078 (Owed: "Racing kerbs and run-off outlines for the circuits, measured off NAIP / lidar"). Kevin,
2026-11-05: "Yes, start it." His standing words decide every call: "I just want real" — a circuit without real kerbs
gets none; a run-off that cannot be measured stays unbuilt and is reported; every invented number is marked
(`fleet/GATES-CHANGELOG.md` 2026-11-05).

## The data: NAIP at its best year and resolution per site

Round 4 read High Plains off NAIP 2023 as z18 web tiles (0.46 m at 39.7° N) and the other Colorado circuits off USGS's
NAIP ImageServer, which serves only Colorado's 2019 flight (0.6 m). Microsoft's Planetary Computer carries every NAIP year
as USDA delivered it (public domain, USDA FSA): **Colorado's 2023 flight is 0.3 m.** `tools/naip_crop.py` crops one STAC
item to a lon/lat box at native resolution (the data API, tiled, EPSG:4326, corners exact; certificate verification on).

| site | best NAIP (Planetary Computer) | used before |
|---|---|---|
| High Plains, Aspen, Pueblo, Grand Junction, Pikes Peak | 2023, **0.3 m** | 2023 z18 (HP), 2019 0.6 m (rest) |
| Nevada Nights (Las Vegas) | 2022, 0.6 m (2019 0.6 m; 2013 1.0 m is the course's year) | 2019 / 2013 |
| Milford (Michigan) | 2022, 0.6 m | 2022 0.6 m |

No higher-resolution public, licence-clean orthoimagery was found for these sites in reach of this Mac (county / regional
programmes either do not cover the sites or carry no clear public licence); NAIP is the source of record.

New tools (none in any chain; Lake Murray runs none of them): `tools/naip_crop.py` (the crop), `tools/edge_sheet.py`
(station-labelled zooms with the line's lane edges, to check spans by eye), `tools/kerb_spans.py` (measures each
hand-checked span: in / out of the paint across the lane edge, the edge in lon/lat, colour, profile),
`tools/built_beside.py` (the aerial beside the BUILT kn5's faces, per kerb object).

## High Plains (`high-plains-lm` 0.1.2): 20 measured runs, two paint schemes; no run-off

**What is really there (NAIP 2023-09-28, 0.3 m):** two kinds of edge paint, each checked by eye on
`tracks/high-plains/source/edges/kerbs_2023_030_sheet.jpg` (all 20 cells):
- **11 blue / white kerbs**, 1.3-2.9 m of paint across the edge (the wide blocks round the apexes): L s 212-239, 1,680-1,716,
  2,636-2,666, 2,845-2,856, 2,950-2,975; R s 448-486, 623-638, 1,519-1,540, 2,000-2,019, 2,328-2,411, 2,892-2,914;
- **9 blue / yellow edge stripes**, 0.45-1.05 m of paint on the asphalt edge (entries and exits): L s 517-537, 690-699,
  1,567-1,592, 2,038-2,073, 2,453-2,490; R s 263-299, 1,747-1,768, 2,678-2,697, 3,013-3,044.

Round 4's 12 runs are all inside these; its L s 2,056-2,071 "blue_white" kerb is a blue / yellow stripe at 0.3 m.

**Run-off: none paved, none built** (`runoff_2023_030_sheet.jpg`): the colour reader's 21 "asphalt past the edge" runs are the
other configurations' pavement (the north course's branches at s 1,348 / 2,722 / 2,832, the parallel loop beside s 265-322
and s 456-474), the pit lane (s 3,040-3,082) and dirt; beyond every kerb is graded dirt and prairie, which the ground already is.

**Built:** the 11 kerbs as before (the config's 0.08 m, invented); the 9 stripes **flat** (`"profile": "paint"`: lip only,
no height is seen), each in its colour through one atlas texture (`kerb.atlas`, `textures/kerb_atlas_hp.png`, made by
`make_kerb_atlas.py`: the blue / white file as it was beside a blue / yellow cell, the yellow NAIP's median stripe colour
(205, 194, 137)). 20 runs, 515 m built (round 4: 12, 243 m). Stills: `kerbs_built_beside_0.1.2.jpg` (each kerb: aerial |
built kn5 faces).

| High Plains (from an EMPTY workshop, `tools/ship_track.sh --no-install`, Mac) | 0.1.1 | **0.1.2** |
|---|---|---|
| soft top / severe / bumps /km / kinks /km | 0 / 0 / 0 / 1.87 | 0 / 0 / 0 / 1.87 |
| vertex bumps / drops / far ledges / obstructed / floating | 2 / 0 / 0 / 0 / 0 | 2 / 0 / 0 / 0 / 0 |
| audit_mesh / verify_kn5 / kn5_ground_check (road over ground p95) / house_seat | CLEAN / PASS / PASS (0.021) / PASS | CLEAN / PASS / PASS (0.021) / PASS |
| edge report: at 1 m strip or kerb / rise within 2 m p95 | 100 % / 0.014 m | 100 % / 0.015 m |
| kn5 | 15.6 MB | 15.6 MB (15,616,494 B) |

No gate is worse. **Not real yet (owed):** the build lays every run OUTSIDE the lane edge (round 4's placement), but the
measured paint sits mostly across or inside the live line's edge (in_m down to -2.05 m): the stills show the built kerbs up
to ~1.5-2 m outboard of the paint at s 1,680, 2,000, 2,328 and 2,950. Placing them at their measured offset puts a raised
kerb over the lane ribbon, which drive_test's wheel paths would then cross; that wants its own round.

## Owed (start here)

- Nevada Nights: the 2013 concrete apron as a physical run-off surface (round 5 built it visual-only).
- Aspen, Pueblo, Grand Junction, Pikes Peak on NAIP 2023 0.3 m (crops and colour scans done on the Mac); Milford stands
  on 2022 0.6 m.

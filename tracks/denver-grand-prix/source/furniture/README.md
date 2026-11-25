# Denver Grand Prix 0.1.1 — furniture placements, planned (data only)

*2026-11-24, on the Mac, for the furniture step once Codex's base lands (Tracks:Mac's brief). Nothing is placed.*

```bash
PYTHONUTF8=1 /Volumes/Sundowning/Claude/airoso-data/venv/bin/python \
  tracks/denver-grand-prix/source/furniture/plan_placements.py \
  [--survey <dir with lamps.json + signals.json>] [--models <dir with signals.json + streetlight_posts.json>]
```

The defaults are the integration branch's paths once PR 66 and PR 60 are merged: `source/survey/` and `assets/models/`.
This file was made with both read from their branches (PR 66 at `claude/kind-turing-5xrxlc`, PR 60 at
`claude/dgp-street-furniture-20261123`), against the widths of `1becc3a0`.

`placements.plan.json` has one row per surveyed post, 735 rows:

| Field | Meaning |
|---|---|
| `s`, `side` | lap station on OSM's line; driver's left or right |
| `offset_from_line_m` | across the line; + is left |
| `edge_of_record_m`, `edge_grade` | the edge of record from `source/widths/widths.json`, and its grade |
| `offset_from_edge_m` | **+ is beyond the kerb (on the walk)**, − is inside it |
| `fronts` | `lap`, `opposing_carriageway` (the same street's other direction), `cross_street` or `off_corridor` |
| `nearest_cross_carriageway` | the nearest other OSM carriageway: way id, name, distance |
| `class`, `model`, `model_basis` | what stands there, which PR 60 model fits, and why |
| `arm_bearing_deg`, `arm_needed_m` | masts only |
| `also_lamp` | a signal pole that also carries a luminaire |
| `flags` | `inside_edge`, `covered_span` |
| `grade` | the survey's own grade |
| `height_from_shadow_m` | height read from the shadow, scaled by the masts |
| `eye_note` | the survey's note on the post |

## Counts

| Class | n | Model |
|---|---|---|
| signal mast | 119 | `signal_mast_arm_45` 31, `_35` 87, `_25` 1 |
| signal pole, tall, no arm | 60 | **GAP** (PR 60 has none); `signal_pedestal` named as a stand-in |
| signal pedestal | 22 | `signal_pedestal` |
| lamp, pedestrian | 179 | `ped_globe` |
| lamp, arterial | 135 | `arterial_single` 95, `led_cobra` 31 (owned), `arterial_twin` 9 |
| lamp, unknown | 9 | none: no note word and no shadow |
| sign post | 142 | a post plus a `sign_plate_*`. Face not read; it comes from the junction's OSM rule (`signs.json`, tagged grade) |
| utility pole | 18 | **GAP** |
| post, unknown | 51 | not placed |

Signal poles that also carry a luminaire: 58 (`also_lamp: arterial_single`).

- **What each post fronts:** 482 the lap, 71 the opposing carriageway, 111 a cross street, 71 off the corridor.
- **Distance behind the kerb** for posts that front the lap: p10 0.16 m, p50 1.37 m, p90 5.62 m.
- **Grades** (from the survey): 603 measured, 132 detected.

## How the model was chosen

**Signal masts:**
- The arm's direction comes from the eye's note, e.g. "arm reaches south over Colfax" or "arm reaching NNE". 105 of the
  119 notes give one.
- When the arm points across the lap (within 45° of the lap's inward normal) and the post fronts the lap, the arm needed
  is the distance behind the kerb plus 0.75 × the carriageway's width (the tip over the far lanes). The shortest model
  that reaches is chosen. That applies to 40 masts.
  - **17 of them need more than 45 ft:** Speer, 15th and Kalamath are 15–21 m wide. They get the 45 ft model and are
    marked short. Denver's real arms there are likely longer; a 55–65 ft arm is a PR 60 follow-up.
- Every other mast (an arm over a cross street or the opposing carriageway, or no direction in the note) gets 35 ft
  `[typical]`.
- Heads are not read. The placer hangs `signal_head_3` per approach lane `[typical]`, lit steady at night (E2).

**Lamps:** the eye's words first:
- "cobra" → `led_cobra`;
- "two arms" or "twin" → `arterial_twin`;
- "acorn" → `ped_acorn` (none on this lap);
- "globe", "pedestrian" or "round" → `ped_globe`;
- "arm", "luminaire" or "tall" → `arterial_single`.

Failing a word, the height from the shadow decides: under 5.5 m is pedestrian. The height is the shadow over that year's
median signal-mast shadow, times a 7.6 m mast pole `[typical]`.

**Signal posts:** a pedestal when short (under 0.55 × the mast pole) or when the eye named a pedestal or pedestrian post.
Otherwise a tall pole, which is a gap.

## Checked by eye

The placements were drawn on the 2022 aerial at Colfax / Sherman and at 14th Ave / Kalamath:
- the masts stand on the corners;
- their drawn arms lie along the arm shadows in the picture;
- the lamps and sign posts sit on the walks.

## Read before placing

- **`inside_edge`, 53 posts:** they stand more than 0.5 m inside the edge of record. They are on medians and islands
  where the record runs to the far kerb (paint-only divided streets), at junction mouths where the edge is bridged
  straight across, or they are readings to check (17 of them masts on median noses or islands).
- **`fronts: cross_street` and `off_corridor`:** these belong to the side streets and the free-roam grid. They are
  listed so nothing is lost; the race corridor needs only `lap` and `opposing_carriageway`.
- **Heights** come from the model, not the survey (the survey has no clean sun elevation).
- **Facing:** a support turns to its arm bearing, or square to the road it fronts.
- **Under Stout's roof** nothing is surveyed; the survey declares that span.

Every threshold is `[invented]` and is written in `meta.tuning_invented`.

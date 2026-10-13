---
id: 0050
title: "The small steps are a problem at Jackson/Navajo" — the mended fold's pinch left a 0-0.5 m lip across the inside half of the corner
status: in-progress — fixed and rehearsed in v0.18.0 (2026-10-13, full scratch ship, not installed); closes on Kevin's drive
scope: tracks/san-diego-lake-murray (proof: the Navajo/Jackson box v2307-2332, s 6930-6982; also the hairpin v763-773, College/Navajo v1508-1516); tools/{mouth_weld,weld_mouths_blend,verify_fold_fans,ship_sd.sh,ship_track.sh}, scripts/geometry/drive_test.py (opt-in by data/mouth_welds.json); fleet/LAWS.md L3 corollary
layer: project + engine
train: -
---

## Status

**Fixed and rehearsed, not installed** (v0.18.0 integration, 2026-10-13). A full `ship_sd.sh --no-install` (no
`--skip-blend`) on a fresh scratch copy of the workshop, with ENG a fresh copy of engine-july plus the snapshot's
pending files: the lip is gone on all three layouts, `tools/verify_fold_fans.py` (new, hard) passes every levelled fan on
every layout, both race layouts stay sealed (`no_route` BUILT PASS), and race `drive_test` severe drops 31 → 22
(race_cw) and 28 → 20 (race_acw). The judge's design (the midpoint leveller) is what shipped, with the review's two
blockers resolved (below). Kevin's drive closes it.

## Symptom

Kevin, 2026-10-12, from the seat, verbatim:

> "the small steps are a problem at jackson/navajo and arrow signs are only placed for one direction of driving. no flickers at all that i can see, load time and frame rate are great"
>
> "i didn't notice anything off other than jackson/navajo"

Earlier, in 0049: "the track width and race track layouts are incredible". The corridor model stays.
The signs are 0051, the AI races 0052 and the race kerbs 0053.

## Evidence

All numbers were measured read-only on the installed v0.17.1 build's gate OBJs (`k10-sd-v021/project/data/track.obj`,
`track.race_cw.obj`, `track.race_acw.obj`; the same ship run as the installed kn5s).

**Method.** The top physics surface (1ROAD, 1KERB, 1GRASS); wheel paths every 0.25 m across each layout's driven lane
(street ±(w/2 − 0.5) less the median island; race `barrier_bands` lanes), each cut at its own self-intersection so it is
a line a wheel can actually take (drive_test's fixed offsets run backwards on the inside of a 7.4 m corner), sampled
every 5 cm. A FINE step is the rise over 10 cm beyond the grade of the metre before it (≥ 2 cm). DT is drive_test's own
1 m second difference.

**Navajo/Jackson.** ONE step feature in the driven lanes of all three layouts, a lip along row 2315's cross line
(s 6945.5 forward; race_acw s ≈ 6534.6): 45 of 101 street paths and 44 of 95 race paths cross it, 0.13 m at 3 m in from
the centre line, 0.26 at 6 m, 0.38 at 9 m, 0.47 at 11 m; DT 0.48. It is one road triangle: corners 108.811 / 108.811 /
109.310 m, 0.33 m² of plan, 901 % slope. Grass showed through it (1GRASS 0.19 m over the road at 11 m in). The street's
0.24 m of it was filed by drive_test as an exempt "apron step" (w ≥ 9.5 m, |off| > 3.5 m), which is why street severe
read 0; the race layouts counted it (race_cw s 6946-6947, race_acw s 6535-6536).

**The other fans.** Hairpin (pinch, legs 0.042 m apart), College/Navajo (pinch, 0.053 m), Jackson/Lake Murray Blvd and
the seam (chord mends, legs level): no road step ≥ 2 cm.

**The real intersection** (USGS 3DEP 1 m, TLS verified, 14,641 samples over 120 × 120 m): one smooth surface, 2.91 %
toward the east, 0.049 m rms within 25 m; the real inside corner is 108.98 m (109.08 with the 0.10 m deck lift), where
the build carried 108.81 and 109.31. Along row 2315's cross line the real ground rises smoothly (1.7 %): no step.

## Diagnosis

In plain terms: the road is laid like a 24 m-wide ribbon swung round the Navajo→Jackson corner, every slice level
across at the centre line's height. The corner is tighter than half the ribbon (7.4 m radius, 12 m half-width), so the
inside edge would fold back over itself. The 2026-10-11 weld pinched it to one point. The two sides of that pinch come
from road about 19 m apart on a 2.7 % climb, so they arrive half a metre apart in height; the weld put the point at the
higher one and left the last slice before it at the lower one, 6 cm away. That is a near-vertical lip from the centre
line to the inside kerb: a step up driving forward (street, race_cw), a drop for race_acw.

Chain: `ribbon.py:42-55` (L, C, R at the row's centre height) → `weld_mouths_blend.py` → `mouth_weld.unfold_line`
(the apex took `max(...)` of its legs; row 2315 stayed on the low leg) → `seat_terrain_blend.py` cleared grass under
the fan but not under the low leg → `drive_test.py`'s street apron exemption.

Why the MIDPOINT: `tools/no_route.py` judges each race wall against "the nearest centre-line point + 0.10". X lies on the
medial axis, so walls either side of it are judged against legs 0.50 m apart. A 1.20 m K-rail buried 0.05 m must cover
+0.20…+0.90 over its reference, so it passes only within about ±0.30 m. Only the midpoint keeps both sides inside;
"keep the high apex, raise the low leg" leaks (the rejected 2026-10-11 re-grade, 316,401 m²).

## Fix (v0.18.0, the judge's Design 2 + grafts)

**The leveller** (`tools/mouth_weld.py`). `unfold_line(..., level=None)`: `level` follows `strict`, so only the weld's
MAINLINE calls level; connectors and the paint-plan unfold keep the 2026-10-11 rule bit for bit. Each pinch X takes the
midpoint of its line's two leg heights; each leg's last `FOLD_LEVEL_ROWS` = 8 rows are eased to it with a smoothstep,
heights only (nothing moves in plan). Refusals (WeldError): half the jump over `FOLD_HALF_JUMP_MAX_M` 0.28 m; an eased
row tilting more than 4 % over its distance to the centre row; a leg window overlapping another cut on the line.
`check_levelled` (one height per shared plan point, no backward segment, nothing outside the windows moved) runs as the
weld's self-check on every levelled line and stops the build on a failure. `weld_mouths_blend.py` passes `level`
explicitly, prints one `[weld] LEVEL` line per pinch and records them in `data/mouth_welds.json`
(`folds.MAINLINE.levelled`, `level_rows`, `rows`). L3 gains its corollary (fleet/LAWS.md): a road surface is a
function of plan position; the inside corner is one point with one height.

**The review's BLOCKER 1, resolved by measurement.** The 0.28 m cap on every curb line would have stopped the build: on
the real weld the Navajo/Jackson half-jumps are ROAD 0.248, curb p0 (lane edge) 0.248, p1 (curb top) 0.251,
**p2 (sidewalk back) 0.317, p3 (grass meet) 0.359** — the review's numbers to the millimetre. The cap now applies only
to the lines that carry the walls and the curb face (ROAD edges, p0, p1); p2 and p3 level uncapped (they carry no wall;
the sidewalk slab tilts by at most 0.07 m over its 1.8 m). Every levelled line passed its self-check. Jackson/Lake
Murray Blvd's p2/p3 are pinches too (rows 3290-3301) and level by 0.019-0.020 m.

**The gate** (`tools/verify_fold_fans.py`, new; hard in `ship_sd.sh` / `ship_track.sh` after the race gates;
`--force-install` does not cover it). Per levelled pinch, rows k − 8 − 4 … l + 1 + 8 + 4, on every layout's BUILT gate
OBJ: (1) FINE steps ≥ 0.02 m and (2) 1 m second differences > 0.06 m on the real wheel paths, an authored race kerb lip
≤ 0.05 m allowed; (3) two road vertices within 0.10 m in plan at different heights; (4) grass more than 0.02 m over the
pavement in the lane on the rows the leveller moves; (5) a road triangle steeper than 25 %; (6) X not within 0.01 m of
its legs' midpoint; (7) a race-wall cell (0.5 m, 3×3 base) within 25 m of X outside ±0.28 m of no_route's reference.
Pure Python (the chain's interpreter has no numpy).

**The review's BLOCKER 2, resolved: calibrated so it passes the fixed build for the right reason.**
- *Scoped by the driven lane, never by exempting a curb that stands in one.* The street lane excludes the median island
  (island half + 0.4 m, as drive_test keeps the inner wheel off its face): the real 0.20 m median curb at Navajo
  (rows 2266-2295) is not driven surface. Every curb inside a lane still counts; only the authored 0.05 m race kerb lip is
  allowed.
- *Scoped to the levelled pinches.* The chord mends (Jackson/Lake Murray Blvd, the seam) and their pre-existing
  0.07-0.08 m race DT are not 0050's and stay drive_test's.
- *Grass by depth, on the moved rows.* The prep pins grass 0.02 m under the deck at its vertices, so big facets graze the
  deck by millimetres between them; v0.17.1 has grass 0.01-0.03 m over the hairpin's road at row 755 (k − 8, a row the
  leveller does not move). (4) counts every graze, fails only above 0.02 m, and reads the rows the leveller moves.
- *Teeth on the installed v0.17.1 OBJs (copied to the scratchpad):* FAIL — Navajo/Jackson 45 / 44 / 44 paths with a
  step, FINE 0.422, DT 0.481 (street) / 0.465 (race), the 901 % triangle, two road vertices 0.055 m apart standing
  0.499 m apart, grass 0.192 m over the road, X at 109.310 against the midpoint 109.061, two wall cells at +0.498;
  the hairpin and College/Navajo fail (6) only (X 0.021 / 0.027 m off the midpoint: the leveller had not run).
  Synthetic teeth in `tests/tools/test_verify_fold_fans.py` (riser, grass, X off, wall δ 0.5, a 0.08 m kerb lip fail;
  the levelled fan, a 0.045 m race kerb lip, a wall at δ 0.25 pass; exit 0 / 1 / 2).

**drive_test** (engine, opt-in by `data/mouth_welds.json`; every other track byte-identical). Inside a levelled fan
(rows k − 8 … l + 1 + 8, half-width + 0.5 m) a SEVERE step (> 6 cm) is never an "apron step". Teeth: on the pre-fix
v0.18.0 build the street's 0.237 m riser at s 6946-6947 lat −6 becomes severe. Bumps (2.5-6 cm) keep the apron rule,
measured: with the exemption fully off, the fixed-station paths read 56 street "bumps" in the two fans (all apron bumps
before) — round a corner tighter than the offset the station-to-station spacing of a fixed-offset path changes (0.2 m
inside a 7.4 m corner at 6 m, 1.8 m outside), and on a 2-3 % grade that alone reads 2.5-4.7 cm — where
verify_fold_fans' arc-length wheel paths read a 1 m second difference of at most 0.025 m. The seam's pre-existing
0.06-0.07 m street apron step (s 12-13, a chord mend) keeps the old rule too; race_cw already counts it.

## Results (v0.18.0 rehearsal, 2026-10-13; v0.17.1 → v0.18.0)

**verify_fold_fans PASS**, 3 levelled pinches × 3 layouts:

| fan | layout | paths with a step | FINE max | DT max | race kerb lip | grass over the road (max) | X built / midpoint | walls worst |
|---|---|---|---|---|---|---|---|---|
| Navajo/Jackson 2315..2324 | street | 45 → **0** of 101 | 0.422 → 0.000 | 0.481 → 0.018 | — | 0.192 → 0.002 | 109.310 → **109.0615** / 109.0615 | — |
| | race_cw / race_acw | 44 → **0** of 95 | 0.422 → 0.000 | 0.465 → 0.018 | 0.041 | 0.192 → 0.002 | 109.0615 / 109.0615 | +0.498 → **+0.263** |
| hairpin 763..774 | all | 0 | 0 | 0.025 | 0.025 | 0.030 → 0.013 | 9.934 → 9.9125 / 9.9125 | −0.136 → −0.116 |
| College/Navajo 1508..1517 | all | 0 | 0 | 0.021 | 0 | 0.016 → 0.005 | 24.471 → 24.4447 / 24.4446 | −0.045 → −0.032 |

- **The weld:** legs 108.813 / 109.310 → X 109.062 (the real corner + lift is 109.08); 16 rows eased, largest move
  0.248 m (road), 0.359 m (curb p3). Hairpin and College/Navajo: 0.021 / 0.027 m.
- **Locality** (street gate OBJ, v0.18.0 before / after 0050): plan positions identical for every road, curb and paint
  vertex; heights moved only in the fans — 1ROAD 51 vertices (max 0.248 m, all in the windows), MARKINGS 273 (max
  0.238), 1KERB_sidewalk 238 (max 0.359); `mouth_welds.json` cuts identical; `verify_mouths.json` byte-identical to
  v0.17.1.
- **Real ground:** deck vs 3DEP + 0.10 within 15 m of the box, p95 |Δ| **0.274 → 0.197 m** (the judge's ≤ 0.20); within
  25 m 0.325 → 0.292.
- **no_route BUILT:** race_cw and race_acw PASS — 0 leaks, 0 doors, 0 / 406 probes, every spawn reached. The walls'
  worst offset from no_route's reference near X is +0.263 m: inside ±0.28 by 0.017 m, inside no_route's own ±0.30 by
  0.037 m (the review measured 0.032 m on its simulation). Thin, and it is the reason (7) exists.
- **drive_test:** race_cw severe 31 → **22** (2.30 → 1.63 /km), race_acw 28 → **20** (2.08 → 1.48 /km); no severe at
  s 6946-6947 / 6535-6536. What remains in the fans (s 6954-6959 lat −9.3/−10, s 2299-2302 lat −12.3/−13, and the
  reverse) are fixed-offset paths running backwards over the fan beyond a 6.6-7.4 m centre radius — the diagnosis'
  sampling artefacts; real wheel paths there read DT ≤ 0.025 m. Soft top: race 23 → **9**, 22 → **9**; street 42 →
  **41**. Street severe 0 with the in-fan severe exemption off; street bumps 0.15 → 0.0 /km, kinks 3.86 → 3.41 /km.
- **Race seating:** deck vs data max 0.463 → **0.238 m** (≤ 0.30); 0 interpolated; verify_race OK.
- **Audits:** street 512 / 20 / 20 / 13, race 0 / 20 / 20 / 13, W 0 — unchanged.
- **Signs (0051):** M4-fwd / M4-rev (the corner's outside) placed, clear the race curb strip by +1.853 / +1.762 m.
- **AI (0052):** the writer re-seats on the levelled deck; `verify_ai_line` PASS on both race layouts, every number as
  on v0.17.1's world (wall min 2.549 / 2.387 m, flips 0.743 / 0.521 per km).

## Later (JUNCTIONS §2.0 B, REALISM §8)

Author Navajo/Jackson as a junction pad in loop.blend (an AUTH_ layer): arms cut straight, one surface heighted from
3DEP (2.91 % toward the east, rms 0.049 m), an inside curb return at a real 9-15 m radius. This mend makes the draft
drivable now and keeps the corridor model.

## Kevin's drive (the only verdict that closes it)

- Street and race_cw: Navajo → Jackson right turn, inside lane, at speed. race_acw: the reverse left turn.
- Also the hairpin and College/Navajo in each layout. No step felt, no gap in the barriers at the corner.
- Ask specifically (the review): "small steps" was plural. Besides the lip (gone), the box holds the Navajo approach's
  0.02-0.03 m grass-to-road lip at the lane edge (s 6843) and, on the street layout, the real 0.20 m median curb at
  ±1 m. Neither was changed; if either is what he felt, 0050 is not closed.

---
id: 0052
title: "ai races need tuning, they tend to crash and slow down weirdlu" — the generated race lines aim at the K-rail, brake for bends that aren't there, and carry five payload fields in the wrong meaning
status: in-progress — fix built and gated on a scratch copy (branch worktree-wf_b86dbf3d-dfa-7); not installed; Kevin's race is the judge
scope: tracks/san-diego-lake-murray race_cw + race_acw (proof); scripts/ac/write_ai_line.py (opt-in `ai` block; every k10 generated line has the old payload — 15 of 15 installed); new scripts/ac/ai_built.py, tools/verify_ai_line.py
layer: engine (opt-in per track) + project (config opt-in, ship-chain gate)
train: -
relates: 0023 (generated AI never proven to lap — stays open; this settles its speed-unit question), 0047/0049 (the race corridor lines), 0050 (Navajo/Jackson steps on race_acw's exit line)
---

## Status

The fix is built and committed on its branch. On a scratch copy of the workshop it regenerates both race lines from
the v0.17.1 gate OBJs, and `tools/verify_ai_line.py` passes both (it fails the installed v0.17.1 lines on 12 counts
each). Nothing is installed.

Three changes in held files remain: `track.config.json`, `ship_sd.sh` / `ship_track.sh`, and the chain test. They
are written out exactly under **Held files** and the integration run applies them. Ledger 0023 stays open: these are
still GENERATED drafts, never a recording.

## Symptom

Kevin, 2026-10-12, from the seat, after a 7-AI race on the installed v0.17.1 race layouts:

> "ai races need tuning, they tend to crash and slow down weirdlu"

Same session: "the track width and race track layouts are incredible" (so the corridor model stays) and "i didn't
notice anything off other than jackson/navajo" (that is 0050).

## Evidence

All of it was measured read-only on the INSTALLED files. The installed race lines are md5-identical to the workshop
drafts (race_cw `8d4696a4…`, race_acw `c234c87c…`), and the airoso writer at 5ccf20b reproduces them byte for byte
on a scratch copy. The walls are the v0.17.1 gate OBJs `track.race_{cw,acw}.obj`. The reference is every AI line
installed on this PC (217 files); the Kunos tracks were measured against their own `NNWALL` physics meshes.

**1. The payload: five fields carry the wrong meaning.** A `fast_lane.ai` stores 18 numbers per point besides its
position (actools `AiPointExtra`).

| field | every Kunos / third-party line (131 + 55 files) | ours (`write_ai_line.py` at 5ccf20b) |
|---|---|---|
| `length` | distance to the previous point (1.5 m; newer files a 5-segment window, ~7.5 m) | **cumulative lap distance, 0 → 13,467 m** (`:1912`, written at `:1989`); none of 186 reference files does this |
| `direction` | ±1, the side the bend turns toward (= −sign of the heading change in the kn5 frame on 99.0-99.5 % of bending points) | **0 everywhere** |
| `camber`, `normal` | the road surface's real tilt (camber = asin(normal·right), ratio 0.94-0.99) | **0 and (0,1,0)** |
| `radius` | the plain 3-point circumradius | min of a 5-point window (`:1896-1898`), biased low |
| header lapTime / sampleCount | 0 / 0 | 281085 / 8979 |

The `speed` unit question from 0023 is settled: m/s, as Kunos. `speed` is not what drives the AI either: Kunos ships
recorded speeds of 31-63 % of a physics profile, and those AI still race.

**2. The line is aimed at the K-rail at every box corner.** Distance from the line (the car's centre) to the nearest
BUILT wall face:

| | min | lap under 2.0 m | lap under 2.5 m |
|---|---|---|---|
| race_cw | **1.506 m** | 114 m | 186 m (1.4 %) |
| race_acw | **1.504 m** | 177 m | 239 m (1.8 %) |
| ks_black_cat_county (11.2 km, walled) | 2.066 m | 0 m | 64 m (0.58 %) |
| ks_monza66 road | 1.981 m | 10.7 m | 182 m |

A car is about 1.9 m wide, so a line 1.5 m from the wall leaves about half a metre between the door and the
concrete. It happens three times at each box: on the approach along the outside wall, at the apex off the K-rail
end, and on the exit. The cause is a choice, not the room available: the corridor is 6.86 m wall-to-wall at its
narrowest. `FILLET_COMFORT_CLEAR_M = 1.5` feeds the box approach and the box arcs.

**3. Bends that aren't there.** Compare two speed profiles for the same line: one from the radius the file gives the
AI, one from a car-sized look at the line (±6 m).
- Points where the file says "slow down" by more than 10 % with no real corner there: race_cw **160**, race_acw
  **875**. Black Cat County, Vallelunga, Highlands: 0, 0, 0.
- Left/right flips of the bend within 30 m: race_cw 1.71 per km, race_acw 0.97 per km (BCC 0.72).

The worst was race_cw approaching College→Navajo: 74 km/h where the line allows 130.

**4. Sides — not the problem (the diagnosis' 23 points corrected).** The diagnosis counted 23 race_acw points whose
`sideLeft` reached past a built wall. It used the nearest wall anywhere on the left half-plane. Every one of the 23
is a wall 16-18 m BEHIND the point and 0.1-0.9 m to its side. Measured the way a car would dodge — straight out
sideways, perpendicular to the line — the v0.17.1 sides stop 1.2 m (the margin) short of the wall at the median,
with 0 overreach in either layout.

## Diagnosis

In plain terms: the AI follows an invisible rail with a list of numbers every 1.5 m.

**Why they crash.** The rail was laid half a metre from the concrete three times per corner. An AI at the limit
wanders more than half a metre, so every box corner was a K-rail hit waiting to happen.

**Why they slow down weirdly.** The rail wiggled before each corner. On top of that, the "how tight is this bend"
number was pinched to the tightest of five neighbours. So the AI saw phantom corners and braked 60-100 m early.

**Underneath both.** Five numbers meant something different from AC's own lines. The worst is `length`: it should say
"1.5 m to the next point" and instead said "13 km from the start". Which of the five AC actually reads cannot be
proven offline. All five disagreed with every one of 186 working reference lines, and all are now cheap to match.

## Fix (built)

The line is still generated from the BUILT corridor (gate_centerline + the corridor faces + the built gate OBJ),
never from GPS. It stays a GENERATED DRAFT under 0023 and HANDOFF. An in-game recording with CSP's AI recorder
(`fast_lane.ai.candidate` in `race_cw/ai/` and `race_acw/ai/`) replaces it file-for-file whenever Kevin wants;
that is still the end state.

The engine change is opt-in per track and per layout: `track.config.json` `ai` (with `ai.layouts`). Absent, the
writer produces today's bytes, proven below.

- **Payload (`ai.payload: "kunos"`).** In the file the AI reads:
  - `length` = the 3D distance to the previous point (point 0 gets the seam segment, L13); the point record keeps the
    cumulative lap distance;
  - `direction` = ±1, the side the bend turns toward; a straight keeps the last bend's sign, never 0;
  - `normal` / `camber` = the BUILT road surface's tilt under the point, and the point's height is seated on that
    surface;
  - `radius` = the plain 3-point circumradius of the points as AC reads them (float32);
  - header lapTime = sampleCount = 0; hasGrid stays 0, as in three working third-party lines.
- **Off the K-rail (`ai.wall_clear_m: 2.5`).** A corridor line's comfort clearance (box approach, box arcs, floor
  fillets) becomes 2.5 m instead of 1.5 m: about 1.5 m of air between the door and the wall instead of 0.5 m.
- **No bends that aren't there (`ai.fair: true`).** A new `fair_line` pass runs on the finished line. Think of
  bending a thin flexible ruler through the corridor:
  - It must stay at least `wall_clear` + 0.5 m from every wall, or no closer than the line already was. It may move
    each point at most 3 m sideways.
  - Within that room it takes the shape with the least change of curvature, plus a pull toward the least curvature.
  - The S-wiggles, kinks and point-to-point jitter go. A corner now tightens progressively, the way a driver turns
    the wheel, instead of switching from straight to full lock in one step.
  - A light polish pass (0.3 m leash) takes out the last millimetre steps where the line touched its bounds.
  - It never makes a radius tighter than min(12 m, what was there).
- **Sides.** Each side is clamped at the first BUILT wall a perpendicular ray meets, minus the 1.2 m margin. On SD
  this cuts at most 9 mm: the declared faces and the built K-rail feet differ by millimetres.
- **The gate, `tools/verify_ai_line.py`.** It checks the written line against the BUILT gate OBJ, with the
  thresholds below, exits 1 on FAIL and writes `data/ai_verify.<layout>.json`. The shared reader is
  `scripts/ac/ai_built.py`: gate OBJ walls (layer-filtered footprints, perpendicular rays), the road surface, the
  `.ai` decoder.

Not done, and why:
- The diagnosis' "smooth box-approach envelope" (F3 part 1) is not needed. The fairing removes the envelope's kinks,
  and the gate shows 0 dips without it.
- `ai_hints.ini` is a tuning lever for after the race, not a fix for a bad line.
- `--lat-g` is unchanged, because the payload speed isn't the AI's target.

### Measured on the regenerated lines (scratch copy, v0.17.1 gate OBJs; `tools/verify_ai_line.py`)

| | race_cw before → after | race_acw before → after |
|---|---|---|
| closest approach to a built wall | 1.506 → **2.517 m** | 1.504 → **2.387 m** |
| lap within 2.5 m of a wall | 186 m (1.38 %) → **0 m** | 239 m (1.77 %) → **6 m (0.04 %)** |
| side widths past a built wall (perpendicular ray) | 0 → 0 | 0 → 0 |
| spurious speed dips (> 10 % slower than the car-scale line) | 160 → **0** | 875 → **0** |
| bend flips within 30 m | 1.71 → **0.67 / km** | 0.97 → **0.52 / km** |
| payload semantics (length / direction / header / radius / camber) | all 5 FAIL → **all PASS** | all 5 FAIL → **all PASS** |
| line's min radius | 12.56 → 13.78 m | 12.55 → 14.33 m |
| lap estimate, μ 1.0 physics profile on the car-scale line | 328.0 → **279.2 s** | 321.0 → **272.4 s** |
| the same profile on the payload's radius (what the AI is told) | 337.8 → **280.0 s** | 338.0 → **273.3 s** |
| writer's own estimate (lat-g 1.6) | 281.1 → 242.1 s | 281.3 → 235.5 s |
| gate | **FAIL (12)** → **PASS** | **FAIL (12)** → **PASS** |

The lap gets 42-49 s quicker on paper because the phantom brake points are gone, not because any corner got faster.

Per corner (car-scale radius / μ 1.0 corner speed), before → after:

| corner | race_cw | race_acw |
|---|---|---|
| Lake Murray / Alvarado (seam box) | R 45.1 m, 76 km/h → R 37.3 m, 69 km/h | R 47.5 m, 78 → R 39.0 m, 70 |
| College hairpin (floor fillet) | R 12.6, 40 → R 14.0, 42 | R 12.6, 40 → R 14.6, 43 |
| College → Navajo | R 28.7, 60 → R 24.2, 56 | R 52.3, 82 → R 44.1, 75 |
| Navajo / Jackson | R 32.8, 65 → R 26.9, 58 | R 52.3, 82 → R 41.4, 73 |
| Jackson / Lake Murray | R 44.5, 75 → R 37.0, 69 | R 58.5, 86 → R 51.1, 81 |

The cost is honest: each box's tightest point is 4-9 km/h slower on paper. There are two reasons.
- The arc now keeps 2.5 m off the apex K-rail instead of 1.5 m. That alone takes R 28.7 → 26.1 m at College→Navajo,
  and every box arc is still ≥ 0.885 × today's, which meets the diagnosis' 0.85 rule.
- The fairing replaces "straight, then instantly full lock" with a progressive turn-in. That puts the tightest
  radius in the middle: 0.79-0.87 × today's peak, measured on the line.

No car could take the old instant-lock arc at its paper speed. The hairpin gets faster (14.0 / 14.6 m vs 12.6).

0050 interlock: race_acw's Navajo/Jackson exit passes next to the fold-fan steps. The new line is ≥ 2.39 m from every
built wall, but the steps are a road-surface defect, so AI crashes there should be judged only after 0050 lands.

### Held files (another job owns them this round; the integration run applies these)

1. **`tracks/san-diego-lake-murray/track.config.json`** — add a top-level block. `ship_sd.sh:126` already copies the
   config into the workshop project, so it travels.

   ```json
   "ai": {
     "_note": "ledger 0052: Kunos payload semantics, 2.5 m off the K-rail, faired, seated on and clamped at the BUILT gate OBJ; still GENERATED drafts (0023)",
     "layouts": ["race_cw", "race_acw"],
     "payload": "kunos",
     "wall_clear_m": 2.5,
     "fair": true,
     "surface": "gate_obj"
   }
   ```
   The street layout is not listed, so its line keeps today's bytes. (`ai.verify` can override any gate threshold;
   none is needed on SD.)

2. **`tools/ship_sd.sh`**, the AI step (`:250-254`). **Order matters.** Today the AI step (`:251`) runs BEFORE the
   race gate OBJs are extracted: the `rm` is at `:289` and `kn5_to_gate_obj` at `:304`. With `ai.surface:
   "gate_obj"` the writer would refuse (missing OBJ), or read last run's OBJ, which its staleness guard refuses
   when a kn5 is newer. So extract each race layout's gate OBJ first. Its three kn5s already exist at that point:
   road kn5 earlier, race kn5 `:238`, closure `:243`. Replace the race loop with:

   ```sh
   for lid in $RACE_IDS; do
     (cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" --kn5 "$PROJ/build/${SLUG}_race.kn5" --kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --out "$PROJ/data/track.$lid.obj")
     (cd "$AIROSO" && python -m scripts.ac.write_ai_line "$PROJ" --layout "$lid" | grep -v "^  v\|^frame")
     step "gate: verify_ai_line --layout $lid (hard; ledger 0052 — the written line vs the BUILT walls and road)"
     (cd "$AIROSO" && python tools/verify_ai_line.py "$PROJ" --layout "$lid")
   done
   ```
   - Under `set -e` a FAIL from either python step aborts the chain.
   - The later `rm` (`:289`) and re-extraction (`:304`) can stay; they rebuild the identical file from the same kn5s.
   - Optionally drop `track.$lid.obj` from the `:289` rm and skip the `:304` call.
   - Add `ai_verify.$lid.json` to the data files synced back (the `:346` list) if Kevin wants the verdict in the repo.
   - Each race layout adds ~25 s for extraction, ~35 s more in the writer (OBJ read + fairing) and ~10 s for the gate.

3. **`tools/ship_track.sh`**, `ship_ai()` (`:291-296`): the same three lines per race layout. `gate_race_gates`
   (`:361`) keeps its extraction. A track without `ai` keeps today's behaviour. The gate is still worth running on
   such a track, but it will FAIL V1 on any legacy line by design, so wire it only for tracks that opt in: test
   `ai` in the config, the way `RACE_IDS` is read.

4. **`tests/tools/test_ship_sd_chain.py`**: the ordered step list (`:47` neighbourhood) gains
   `scripts.modkit.kn5_to_gate_obj` (the per-layout form) before `scripts.ac.write_ai_line`, and
   `tools/verify_ai_line.py "$PROJ" --layout "$lid"` right after it. The same goes for `test_ship_track_chain.py`
   if it pins `ship_ai`.

5. **`fleet/LAWS.md`**: no change needed. Optional, Kevin's call: L5's gate table could gain a row "verify_ai_line —
   the written fast_lane.ai vs the built gate OBJ — a line aimed at a wall, phantom corners, payload fields in the
   wrong meaning".

## Scope

- Proof: Lake Murray race_cw and race_acw.
- The payload defect is on every k10 generated line (15 of 15 installed: Lake Murray ×3, Lookout Lariat ×2, Sand
  Creek ×2, IMI, Pueblo, High Plains, Second Creek, ats-colorado-seam, airoso_* ×3). Only tracks that add the `ai`
  block change.
- The street layout's line keeps today's bytes unless Kevin asks.
- The Lariat's race version (0048 D3) inherits the opt-in when it ships.

## Verification

Decided before the fix (the diagnosis), measured by `tools/verify_ai_line.py`: see the table in
`fleet/GATES-CHANGELOG.md` (2026-10-12) for every threshold and its flag (MEASURED / INVENTED).

Byte identity (no `ai` block):
- The real workshop: race_cw `8d4696a4…`, race_acw `c234c87c…` and street `93a09e5a…` regenerate md5-identical,
  together with every `side_*.csv` and `ai_draft.json`.
- The test fixtures: 25 golden md5s in `tests/ac/test_write_ai_line_payload.py`.

`tests/run_tests.py`: all green, including the 9 new tests.

The judge (rule 0, Kevin): a 7-AI, 3-lap race on race_cw and on race_acw after this and 0050's step fix are
installed. This entry closes on "no repeated wall crashes at the corners and no weird slowdowns", or when an in-game
recorded line replaces the draft.

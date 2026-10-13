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

The fix is built and committed on its branch, and was repaired on 2026-10-13 after an independent check refuted
three things in it (see **Repair** below: the camber sign, the gate's MEASURED labels, the box rule on the line as
written). On a fresh scratch copy of the workshop it regenerates both race lines from the v0.17.1 gate OBJs, and
`tools/verify_ai_line.py` passes both (it fails the installed v0.17.1 lines on 10 counts each). Nothing is
installed.

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
| `camber`, `normal` | the road surface's real tilt, measured toward the bend: camber = −direction × asin(normal·right) (sign agrees on 0.95-1.00 of tilted points, every reference line; corrected 2026-10-13) | **0 and (0,1,0)** |
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
  - `direction` = ±1, the side the bend turns toward, read from the LOCAL turn (±1 point, as Kunos); a straight
    keeps the last bend's sign, never 0;
  - `normal` = the BUILT road surface's normal under the point, and the point's height is seated on that surface;
  - `camber` = that surface's tilt measured toward the bend: −direction × asin(normal·right). In plain terms: a
    positive number means the road leans into the corner (like a banked turn), negative means it leans away. Every
    reference line on this PC stores it that way;
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
  - At each box corner it never makes the car-scale radius tighter than 0.86 × the arc the v0.17.1 rule (1.5 m
    comfort) lays at that corner in the same world. The writer then REFUSES the line if any box ends under
    0.85 × that arc — the box rule the diagnosis declared before the fix, held on the line as written.
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

### Measured on the regenerated lines (fresh scratch copy, v0.17.1 gate OBJs; `tools/verify_ai_line.py`)

Repaired writer, 2026-10-13. Lines: race_cw `88a9da4c…`, race_acw `985da589…` (deterministic: a second run gives
the same md5s). The baseline is the installed v0.17.1 pair.

| | race_cw before → after | race_acw before → after |
|---|---|---|
| closest approach to a built wall (car centre) | 1.506 → **2.549 m** | 1.504 → **2.387 m** |
| lap within 2.0 m / 2.5 m of a wall | 114 / 186 m (1.38 %) → **0 / 0 m** | 177 / 239 m (1.77 %) → **0 / 6 m (0.04 %)** |
| side widths past a built wall (perpendicular ray) | 0 → 0 | 0 → 0 |
| spurious speed dips (> 10 % slower than the car-scale line) | 160 → **0** | 875 → **0** |
| bend flips within 30 m | 1.71 → **0.74 / km** | 0.97 → **0.52 / km** |
| payload: length / direction / header / radius / camber | all FAIL → **all PASS** (camber: 34 tilted points, ratio 1.00) | all FAIL → **all PASS** (62 tilted points, ratio 1.00; all 62 now carry AC's sign) |
| line's min radius | 12.56 → 13.78 m | 12.55 → 14.33 m |
| every box ≥ 0.85 × today's (V6, car-scale minimum within ±60 points) | — → **0.860 / 0.860 / 0.861 / 0.863** | — → **0.876 / 0.877 / 0.860 / 0.873** |
| lap estimate, μ 1.0 physics profile on the car-scale line | 328.0 → **279.4 s** | 321.0 → **272.7 s** |
| the same profile on the payload's radius (what the AI is told) | 337.8 → **280.1 s** | 338.0 → **273.6 s** |
| writer's own estimate (lat-g 1.6) | 281.1 → 242.2 s | 281.3 → 235.9 s |
| gate | **FAIL (10)** → **PASS** | **FAIL (10)** → **PASS** |

An independent measurement (the diagnosis' numpy `wallclear.py`) agrees: wall min 2.549 / 2.387 m, 0 points under
2.0 m, no side past a wall. The lap gets ~48 s quicker on paper because the phantom brake points are gone, not because
any corner got faster.

Per corner (car-scale radius / μ 1.0 corner speed), before → after:

| corner | race_cw | race_acw |
|---|---|---|
| Lake Murray / Alvarado (seam box) | R 45.1 m, 76 km/h → R 38.8 m, 70 km/h | R 47.5 m, 78 → R 41.6 m, 73 |
| College hairpin (floor fillet) | R 12.6, 40 → R 14.0, 42 | R 12.6, 40 → R 14.6, 43 |
| College → Navajo | R 28.7, 60 → R 24.7, 56 | R 52.3, 82 → R 45.8, 76 |
| Navajo / Jackson | R 32.8, 65 → R 28.2, 60 | R 52.3, 82 → R 45.0, 76 |
| Jackson / Lake Murray | R 44.5, 75 → R 38.4, 70 | R 58.5, 86 → R 51.1, 81 |

**The cost, plainly (Kevin's call).** Each box's tightest point is now 4-6 km/h slower on paper than v0.17.1's. The
diagnosis declared, before the fix, that no box may drop below 0.85 × today's radius; on the line as written every
box is 0.860-0.877 ×, so the rule holds. (The first version reached it only on the pre-fairing arcs and was
0.79-0.87 × on the written line — that was a redefinition after the fact. It is fixed in the line, not reworded.)
Two reasons the corners are tighter at all:
- The arc keeps 2.5 m off the apex K-rail instead of 1.5 m. That alone takes R 28.7 → 26.1 m at College→Navajo.
- The fairing replaces "straight, then instantly full lock" with a progressive turn-in, which puts the tightest
  radius mid-corner. No car could take the old instant-lock arc at its paper speed anyway.

If the AI now race clean but feel slow through the boxes, the lever is `ai.wall_clear_m` (for example 2.0 m), or
`ai_hints.ini` after the drive. The hairpin gets faster (14.0 / 14.6 m vs 12.6).

0050 interlock: race_acw's Navajo/Jackson exit passes next to the fold-fan steps. The new line is ≥ 2.39 m from every
built wall, but the steps are a road-surface defect, so AI crashes there should be judged only after 0050 lands. The
v0.18.0 world (0046 terrain, 0050 steps, 0053 kerbs) is a different built world: the writer re-reads it and the gate
re-judges at ship time. These numbers are the v0.17.1 world's.

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
   - Each race layout adds ~25 s for extraction, ~60-100 s more in the writer (OBJ read + fairing with the box
     floor) and ~10 s for the gate.
   - The chain does not pass `--baseline` (V6): the writer itself refuses a box under the declared rule. `--baseline`
     is for a one-off comparison against a previous line, as done here.
   - This is MANDATORY with the config block, not optional: without the reorder the writer's missing/stale-OBJ
     guard stops the chain at the AI step (fail-closed).

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

`tests/run_tests.py`: 561 passed, 2 failed. The two failures are the engine-july seam tests
(`test_engine_july_mirror_is_byte_identical`, `test_snapshot_copies_match_their_manifest_and_stay_small`). They fail
identically on the base 5ccf20b, and this branch touches neither file. The 12 tests of
`tests/ac/test_write_ai_line_payload.py` and every other AI test file (44 tests) pass.

The judge (rule 0, Kevin): a 7-AI, 3-lap race on race_cw and on race_acw after this and 0050's step fix are
installed. This entry closes on "no repeated wall crashes at the corners and no weird slowdowns", or when an in-game
recorded line replaces the draft.

## Repair, 2026-10-13 (the independent check's three refutations)

1. **Camber sign.** The first version stored plain asin(normal·right). Every reference line on this PC (33 Kunos,
   ~90 third-party) stores −direction × asin(normal·right): the tilt measured toward the bend (sign agreement
   0.95-1.00, against ~0.5 for the plain form). On race_acw all 62 tilted points had the opposite sign. Fixed in the
   writer, the gate and the test; the plain form now FAILS the gate on race_acw. The tilts are small (≤ 0.021 rad,
   about 1.2°).
2. **The gate's MEASURED labels.** A threshold may say MEASURED only if every Kunos line it cites passes it. Re-run on
   all 34 Kunos lines installed (scratch `v018/ai/kunos/kunos_v1.txt`):
   - V1 now passes **34 of 34**. Direction is read from the local turn (±1 point: Kunos 0.9977-1.0; the first
     version's ±10 window gave 0.968-0.995, 23 of 33 under its own 0.99). The last point (AC's recorder seam:
     ~5 × spacing, direction 0.1) is not judged; a spacing gap is reported, not gated.
   - AC's lines come in two families, told apart by the length field: SEGMENT (33 Kunos lines and ours: one
     segment, 3-point radius) and WINDOW (ks_silverstone/international and 33 third-party lines: 5 segments summed,
     radius through ±5 points, a direction ramp over 10 points at each end, normal stored up). The gate judges each
     by its own family, so an in-game recording of either kind passes V1. Window-family camber is not judged (no
     Kunos reference shows what it is measured from).
   - Relabelled INVENTED: wall min 2.0 m (ks_monza66 measures 1.981, so 2.0 is a choice between the two walled
     references, not a measurement both pass); spurious dips = 0 (14 of 34 Kunos lines have 5-885); bend flips
     ≤ 0.75 / km (Kunos 0-1.24); sides 0; radius 11.4 m; the box rule 0.85.
   - Every v0.17.1 defect still fails: V1 length / direction / header / radius, V2 min and the 2.5 m band, V3 dips
     and flips (10 FAILs per layout). Planted defects on the new lines (scratch `v018/ai/planted/plant.txt`):
     cumulative length, direction 0 / flipped, header set, min-of-5 radius, camber 0, camber sign flipped, the
     plain-asin camber (race_acw), a 0.8 m bump toward the K-rail, 0.25 m and 0.6 m S-wiggles, 3 cm jitter, a 1.5 m
     kink, sides +3 m, and one length 0.5 m off — every one FAILS. The same line re-expressed in the window family
     PASSES.
3. **The box rule on the written line.** See "The cost, plainly" above: 0.860-0.877 × on the line as written, held
   by the fairing (a 0.86 floor at each box) and enforced by a writer refusal at 0.85.

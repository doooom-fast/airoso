---
id: 0051
title: "Arrow signs are only placed for one direction of driving" — race_acw drives the lap anticlockwise and had no arrows; the 0044 rule, run for the reverse approach too, adds five W1-6L at M1–M5
status: in-progress
scope: tracks/san-diego-lake-murray (signs.json both_directions_mainline; the road kn5's SIGN* meshes, all three layouts); tools/{place_signs,signs_mesh,author_signs_blend,verify_signs,plot_signs}.py
layer: project + engine
train: -
---

## Status

The code and the config are done on branch `worktree-wf_b86dbf3d-dfa-5`. A scratch copy of the workshop project has
been run through the chain's signs step, then `verify_race` and `verify_race --scenery-only`. No kn5 was exported
and nothing was installed.

The five new plates reach the game only through a FULL `tools/ship_sd.sh` (never `--skip-blend`), because the
signs step sits inside the SKIP_BLEND block. The integration run's full rehearsal covers it. The entry closes on
Kevin's drive.

## Symptom (Kevin, seat, 2026-10-12, recorded in ledger 0049)

> "the small steps are a problem at jackson/navajo and arrow signs are only placed for one direction of driving.
> no flickers at all that i can see, load time and frame rate are great"
>
> "i didn't notice anything off other than jackson/navajo"

The placement rule itself is approved and stays. Kevin on 0044, 2026-10-10: "placement looks right, keep the
cul-de-sac sign off". This entry is about the missing direction only.

## Evidence

All measurements below are read-only, on scratch copies of the workshop project. Nothing in airoso main, the
workshop, engine-july or the AC folder was written. Blender 4.2 ran with `--python-exit-code 1`.

### One set of signs serves all three layouts

- On the installed v0.17.1, only the road kn5 (`san_diego_lake_murray.kn5`) holds
  `SIGNPLATE_0 / SIGNARROW_0 / SIGNPOST_0` (checked with `scripts.modkit.extract_kn5`).
- `models_race_acw.ini` loads that road kn5 as MODEL_0. So race_acw shows the same 18 posts as the other two
  layouts.
- The 6 mainline plates all faced the clockwise approach.

### Why the reverse corners were never signed

- **The knob.** `signs.json` had `both_directions_mainline: false`. That was 0044's choice, made when only the
  clockwise lap existed. With it false, `tools/place_signs.py` never scanned the reversed mainline.
- **Turning the knob alone gave nothing.** With it on and the overrides as they were: 18 placed, 48 skipped.
  - M1-rev…M5-rev were each skipped with "expect_arrow=right but the rule computed left" (D +85.8 / +177.5 /
    +92.6 / +106.4 / +85.0).
  - The cause: `assign_overrides` matches an entry by ribbon name, so the forward `expect_arrow: right` also landed
    on the reverse approach. The reverse of a right-hander is always a left-hander.
- **Gate blindness.** `verify_signs` (h) checked only that ids are unique and not skipped. Nothing asked whether
  every driven direction got its arrows.

### A latent defect any full ship would hit, with or without this entry

- `tools/signs_mesh.py` counted `1KERB` as ground.
- The workshop `loop.blend` was saved by the race-furniture pass 23 s after v0.17.1's signs pass. It now carries
  8 `1KERB_race_*` kerbs at exactly these corners.
- `ship_sd.sh` runs signs (:170) before the race re-author (:202).
- Re-authoring the old signs.json on that file moved the approved posts 0.140 / 0.229 / 0.160 / **0.319** / 0.160 /
  0.160 m. M3's move is over 0044's 0.3 m hold.
- `verify_signs --blend` still printed PASS.
- Those race kerbs ship only in the race kn5s. The street layout's signs never stand beside them.

### Side finding

A mis-pathed `--signs` silently ran with no overrides, and placed DCL-2's pair against Kevin's "keep the cul-de-sac
sign off".

## Diagnosis

The rule was built for one direction (0044: "mainline signs the driven direction only — clockwise"). Then 0047/0049
added a layout that drives the lap the other way.

The signs live in the one road model that every layout loads, so race_acw inherited the clockwise set. The knob
that fixes this was never exercised. When it is turned on, the forward-only `expect_arrow` vetoes every reverse
corner. And no gate read which directions are driven.

**In plain terms, for Kevin.** An arrow sign is a flat board that you can only read from the side it faces. Every
board was turned toward cars going clockwise. Going anticlockwise, you reach each corner from the other street, so
you see the board's thin edge, or nothing at all.

The fix stands a second board at each of the five main corners. It goes on the far curb as you arrive from the
other street, faces you, and points left.

## Fix (what changed)

1. **`tracks/san-diego-lake-murray/signs.json`**
   - `both_directions_mainline: true`.
   - `_doc`: an entry speaks for the corner's FORWARD approach. Mainline ids become M<k>-fwd / M<k>-rev.
   - New `_0051` note with Kevin's words and the M2 escape hatch (below).
   - `_approved`, DCL-2 (off), MED-16 and DCL-1 are unchanged.
2. **`tools/place_signs.py`**
   - On a reversed scan, an entry's `arrow` / `expect_arrow` are mirrored (`effective_override`). The record carries
     the mirrored value and a "mirrored" note.
   - A per-approach sub-object (`"fwd": {…}` / `"rev": {…}`) adds keys for one approach only and is never mirrored.
     This is how a single plate is dropped, e.g. `"rev": {"skip": true, "reason": "…"}`.
   - A pin key (`base_xz`, `face_bearing_deg`, `slide_along_curb_m`) at the top level of a corner signed both ways
     is a `SignsConfigError`. It must go into `fwd` or `rev`. No SD entry has one.
   - An explicit `--signs` path that does not exist is an error.
   - `DEFAULTS` is unchanged (false), so the change is opt-in per track.
3. **`tools/signs_mesh.py`**
   - Race furniture is never ground or road. That covers names starting `1KERB_RACE` / `1WALL_RACE`, and the members
     of RACE / RACE_CLOSE_*.
   - The name test (`surface_class` / `is_race_furniture`) is pure Python, so it is tested outside Blender.
   - `tools/author_signs_blend.py` prints the left-out count. It records `blender.race_excluded` only when the list
     is non-empty, so a track with no race furniture keeps its bytes.
4. **`tools/verify_signs.py`**
   - New check (k), direction coverage.
   - (j) is re-read from signs.json and mirrored for -rev.
   - FAIL when race furniture appears in the authoring pass's or the scan's ground / road lists.
   - Section appended at the end of `fleet/GATES-CHANGELOG.md`. It adds no number.
5. **`tools/plot_signs.py`**
   - Each picture says who the plate is for, e.g. "drivers going anticlockwise — race_acw".
   - The overview counts the plates per direction and rings the -rev posts.
6. **Tests**: `tests/tools/test_place_signs.py` +5. Covered:
   - a synthetic clockwise square signed both ways;
   - the mirror;
   - the expect_arrow trap firing (k);
   - a per-approach skip counting as coverage;
   - pins;
   - a missing `--signs`;
   - the race-name filter;
   - the verifier's id, expectation and direction readers.

Not changed:
- the rule's numbers;
- the connector plates (already signed both ways);
- DCL-2 (Kevin: off);
- the deferred W1-7 / W1-8 / W1-1 devices.

`tools/ship_sd.sh` / `ship_track.sh` are held and need no edit.

## Rehearsal (2026-10-12, scratch copy `scratchpad/round2/signs/project`, `loop.blend` with 35 race objects)

| step | result |
|---|---|
| `place_signs` (polyline) | 23 posts / 23 plates (12 W1-6R, 11 W1-6L), 44 skipped. The new plates are exactly M1-rev…M5-rev, all W1-6L. M2-rev-2 is skipped by the hairpin ≥ 12 m clause (1.1 m). M-c5-rev is skipped (R 42, 16°). DCL-2, MED-16 and DCL-1 are skipped. No pairs. Every base is 0.000 m from the diagnosis dry run. With the knob off, the output is **byte-identical** to HEAD's (57,212 bytes). |
| `author_signs_blend` | Ground CURB + TERRAIN, road ROAD; 35 race objects left out. **The 18 v0.17.1 posts moved 0.000 m.** The approved mainline walk-behind is −0.27…−0.40 m and built clearance 1.74–1.80 m (both unchanged). 1357 SIGN vertices (was 1062), one mesh per kind, normals OK. |
| `verify_signs --blend` | **PASS, 23 posts.** Ray-lat 0.00. Face-err ≤ 0.01°. (k): 6 fwd (street, race_cw), 5 rev (race_acw). |
| `verify_race` (full) | OK |
| `verify_race --scenery-only` | OK on make_treefx's plan **and** on the trees.txt installed with v0.17.1 (read-only copy): 0 in a lane or a wall. |

The new posts, as built:

| new | turn (anticlockwise) | race_acw lap metre | base (E, N) | faces | built clear | walk-behind | disc | G margin (both race layouts) |
|---|---|---|---|---|---|---|---|---|
| M1-rev | Alvarado eastbound → 70th St | 897 | (4.73, −1673.15) | 299.2° | 1.83 m | −0.49 | +3.49 | +1.84 (curb strip) |
| M5-rev | Lake Murray Blvd → Jackson | 4,493 | (2629.09, 518.48) | 215.6° | 1.75 m | −0.35 | +7.58 | +1.42 |
| M4-rev | Jackson → Navajo | 7,421 | (59.84, 1735.05) | 158.7° | 1.65 m | −0.41 | +6.91 | +1.76 |
| M3-rev | Navajo → College | 9,836 | (−1990.92, 602.11) | 60.5° | 1.65 m | −0.39 | +9.92 | +1.75 |
| M2-rev | College → Alvarado hairpin | 12,076 | (−2004.97, −1283.42) | 21.9° | 1.77 m | −0.33 | +9.94 | +1.58 |

Every base lies within 0.005 m of the diagnosis dry run, and every facing within 0.00°. All five count as "beside"
in G, so all five were actually measured.

Forward/reverse distances:
- M1: 5.01 m
- M4: 6.13 m
- M3: 10.61 m
- M2-fwd-2 to M2-rev: 10.98 m
- M5: 13.27 m

None is under 2.0 m, so no pair merges.

**Teeth.** All are record-level runs, logged in `scratchpad/round2/signs/teeth_*.log`.
- (k) FAILs on v0.17.1's record: 5 corners with "no record at all for rev (race_acw)".
- The race-ground check FAILs on the unfiltered diagnosis run: 8 kerbs.
- (j) FAILs on a -rev plate given a right arrow.
- (k) FAILs with M3-rev removed.
- (k) FAILs when M5-rev is skipped by expect_arrow.

**Seat-height stills, race_acw.** These were rendered with `scratchpad/stills/work/render_stills.py` on a copy of
the v0.17.1 split road scene with the new SIGN meshes swapped in, plus the race and closure scenes. The files are
in `scratchpad/round2/signs/stills/`. The camera sits on the race_acw AI line, 1.1 m up, with a 70° view.

| still | what it shows (0° = square to the camera, 90° = edge-on) |
|---|---|
| `acw_M1rev_70thSt_close` | 35 m before the first corner. M1-rev's LEFT arrow is 43 m out, 9° right of the nose, 1° off square. M1-fwd is 84° off square, so only its edge shows. |
| `acw_M4rev_JacksonNavajo_close` | Kevin's corner. M4-rev's LEFT arrow is 47 m out, 6° off square. M4-fwd's right arrow is 72° off square, a narrow sliver beside it. |
| `acw_M2rev_hairpin_close` | College into the hairpin. M2-rev's LEFT arrow is 54 m out, 6° off square. M2-fwd-2's right arrow is 61° off square. In the wider still (`acw_M2rev_hairpin`), M2-fwd's right arrow for the other leg shows across the bend. |

The three `…` stills without `_close` are the same corners from 55–60 m.

## Scope

- **Project**: Lake Murray. Proof cases:
  - M1-rev: the seam, with a 6.30 m mesh correction where the 0034 width step is.
  - M2-rev: the reverse hairpin, one plate by the ≥ 12 m clause, plus the cross-view.
  - M4-rev: shares Navajo/Jackson with 0050.
- **Regression cases**: all 18 v0.17.1 posts (0.000 m).
- **Tools**: the sign tools are shared with `ship_track.sh`.
  - A track with no signs.json keeps DEFAULTS, and its output bytes are unchanged.
  - The Lookout Lariat's config declares reverse layouts. When its chain gains the signs step, (k) will FAIL until
    its signs.json opts in. That is deliberate: it is the same defect.

## Interaction with 0050 (the steps at Navajo/Jackson)

M4-fwd and M4-rev stand at Navajo/Jackson (v2319), where 0050 will change the geometry. The signs pass runs after the
geometry passes and re-measures on the built mesh, so the posts follow the new curb.

After 0050 lands, re-check that M4-fwd and M4-rev:
- still PASS `verify_signs`;
- still clear G by ≥ +1.0 m.

## Verification (decided before the fix; the rehearsal above already meets 1–4 and 6)

1. **place_signs (polyline):** 23 posts, 23 plates (12 R / 11 L), 44 skipped. The new plates are M1-rev…M5-rev, all
   W1-6L. M2-rev-2 is skipped by the hairpin clause. DCL-2, MED-16 and DCL-1 are skipped. No pair.
2. **author_signs_blend** on `loop.blend` as it is, race furniture present:
   - `ground_objects == [CURB, TERRAIN]`;
   - the 18 v0.17.1 posts ≤ 0.01 m from v0.17.1's record;
   - the approved mainline walk-behind within −0.45…−0.20 m;
   - the 5 new bases within 0.30 m of the dry run, facings within 0.1°.
3. **verify_signs --blend:** PASS on 23. (k) FAILs on v0.17.1's record, and the race-ground check FAILs on an
   unfiltered run.
4. **verify_race G:** 0 hits. Every M*-rev is ≥ +1.0 m from the curb strip, lane and closure in BOTH race layouts,
   and is measured ("beside").
5. **Integration run (FULL ship, owed):**
   - drive_test / audit_mesh / verify_kn5 per layout no worse than v0.17.1;
   - the road kn5 holds 1357 ± 5 SIGN vertices before the prep's weld (v0.17.1's prepped scene carried 786 after
     it), one SIGNPLATE / SIGNARROW / SIGNPOST mesh;
   - the race, closure and spawn kn5s hold 0 SIGN meshes;
   - `verify_race --scenery-only` on the written trees.txt passes.
6. **tests/run_tests.py**: the sign tests are green.
7. **Kevin's drive** (the only ground truth):
   - Drive race_acw from its grid. At the first corner (Alvarado eastbound into 70th St, 897 m past the line) he
     should see a LEFT arrow straight ahead, just past the far curb, as he reaches the turn.
   - Then Lake Murray Blvd → Jackson (4.5 km), Jackson → Navajo (7.4 km), Navajo → College (9.8 km), and the
     College → Alvarado hairpin (12.1 km).
   - In street and race_cw, the new boards should read as thin edges.
   - At the hairpin he judges the cross-view. If it reads wrong, add `"rev": {"skip": true, "reason": "<his
     words>"}` to M2 in signs.json (one line, no code), or use the deferred W1-8 chevrons.
   - A wrong corner is a per-approach override with his reason. A wrong pattern reopens this entry.

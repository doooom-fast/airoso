---
id: 0049
title: "We need full intersections available for turning. And the entire other lane blocked off from access" — the race versions as an Alvarado-wide corridor per direction, open boxes at the corners, nothing reachable on the other side
status: shipped
scope: tracks/san-diego-lake-murray (proof: race.corridor, race.kerbs.trims, layouts[].closure_token); tools/{barrier_bands,race_corridor,no_route}.py (declaration v2 + the containment gate), tools/{race_furniture,author_race_furniture_blend,split_exports_blend,verify_race,check_race_kn5,plot_race_furniture}.py, tools/{ship_sd.sh,make_treefx.py}, scripts/geometry/{median_zone,drive_test,audit_mesh}.py, scripts/ac/{verify_kn5,track_folder,write_ai_line}.py, tools/pack_release.py
layer: project + engine
train: -
supersedes: 0047's shared centre K-rail chain (0047 Q2 and Q7 moot; Q1 stays answered — side streets sealed; Q5, Q6, Q9, Q11 stand; Q10 settled by Kevin's stance, 2026-10-11)
---

## Status

**Shipped and installed; Kevin's first drive verdict is positive (2026-10-12, "Drive verdict 1" at the end).**
Installed as v0.17.0 (`da3fe9b`, 2026-10-11 18:26) and again as v0.17.1 with the mouth weld (`b14abb9`, 21:12).
No tier is claimed: T3 needs the full drive report (three clean laps per layout), which is still blank. The
history below is kept as written.

**(History) Open — committed at `c0361f7`, fix round applied (2026-10-11), built and gated end to end on a SCRATCH copy
only; NOT shipped from the workshop, NOT installed.** The fix round (the critic's findings on `c0361f7`): no kerb
under a road sheet any more (the 1514 / 2319 inside kerbs dropped, the hairpin's pulled back — race audit K back
to **154**, the installed build's), a new scenery gate (TreeFX trunks and sign posts out of every race lane and
wall), the release texts and the licence wording per Kevin's stance, build version 0.17.0, and a pre-filled drive
report. The fix-round rehearsal ("Fix-round rehearsal" below) passes every race layout's own gate; the street
layout's gates are identical to the installed build. The workshop `loop.blend` and the AC folder were not
touched. **Next: the real ship — exactly `bash tools/ship_sd.sh --skip-blend --force-install`, with Assetto
Corsa and Content Manager closed ("Ship" below) — then Kevin's drive
(`tracks/san-diego-lake-murray/drive-reports/2026-10-1x-race-corridors.md`).** No tier is claimed; Kevin's
drive is the only ground truth.

**The installed race layouts are not sealed today, independent of anything new.** The containment fill on
today's installed build (the gate OBJ of road kn5 + race kn5, `track.race.obj`) reaches 752,562 m² outside
race_cw's corridor (752,263 m² for race_acw) through 11 doors per layout — see Evidence.

## Symptom

Kevin, 2026-10-11, verbatim:

> "racetrack versions of these, we need full intersections available for turning. And the entire other lane
> blocked off from access."
>
> "We want more or less an Alvarado's width for the entire track with deviances in various areas."
>
> Intersections: "Corners the race turns at" (side streets stay sealed).

Earlier (0047): "The barriers are for wide roads, Alvarado should be the entire street"; "With Barriers between
directions, leading up to medians but not on them"; "The tracks will get additional race curbs and barriers
along the inside of the sidewalks".

## Evidence

`python tools/no_route.py <scratch copy of the workshop> --layout race_cw --obj track.race.obj` (the installed
build's gate OBJ, read with the 0047 declaration's own corridor: race-side curb face .. chain / island face):

| Door (race_cw) | Class | Why |
|---|---|---|
| v606-620 L and R (≈ 44 m) | off_road, escapes | Alvarado bridge span: both curb strips gapped, and the road kn5 has NO rail there |
| v854-903 R (race side) | off_road, escapes | College bridge: strips gapped over v856-902, the deck panel only covers v864-887 |
| v4438-4493 L, v4441-4493 R | off_road / opposite, escapes | I-8 bridge (rail only v4454-4474) + the chain's free end at v4440 (`BRIDGE_CLEAR_M` 9 m) |
| v779-781 L | opposite, escapes | the chain's free end at v780 |
| v845-1074, v1095-1258, v1373-1487, v1539-1739, v2182-2297 R | island, escapes | every island race face nose to nose: the island curb is 0.18 m, the deck is drivable grass, the 1WALL_guard beam (0.63-0.93 m) is not a wall, and the chain stops ON the nose vertex, 3 vertices short of the beam |

race_acw: the mirror, 11 doors, 752,263 m². Spawns reached, lap complete — the corridor is drivable; it is just
not closed. The design study's prototype found the same places (it reported 51 "clusters" by bucketing door
cells per 4 vertices; the gate clusters them spatially).

## Diagnosis

Three independent holes, none of them visible to the gates that existed (all of which measure the lane the car is
supposed to drive, none of which ask whether it can leave):

1. **Bridge gaps.** `barrier_bands.py` v1 gapped both curb strips over every declared bridge span on the premise
   that "the authored rails are the barrier"; the only rails are the 1WALL_guard panels at College v864-887 and
   I-8 v4454-4474, Alvarado's span has none.
2. **Free chain ends** at v780 and v4440 — a free end is a doorway into the opposite carriageway.
3. **Islands.** The shared median's beam is the only physical thing on an island and it is a 0.24 m beam
   0.63-0.93 m above the road with 0.65 m under it; it stops 8.5-9.5 m short of all ten noses.

## Fix (the judged spec, Appendix A; the declaration half is built)

- **One corridor per direction.** The race-side boundary is that direction's right-hand curb strip, the whole
  lap; the far boundary is a CLOSURE — the same jersey strip standing 11.36 m face to face from it (Alvarado as
  raced: 13.00 m curb to curb minus the two 0.82 m strip insets — MEASURED, re-measured by the writer), measured
  against a flare-free base width so it stays straight where the curb wiggles.
- **Whole street** on v4454 → v0 → v777 (I-8 deck, seam box, Alvarado, hairpin box): no closure (the pocket behind
  one would be under 2 m). **Open boxes** at the three other corners (v1506-1521, v2311-2328, v3289-3304): the full
  intersection between both curb strips. **Closure runs** College v777-1506, Navajo v1521-2311, Jackson
  v2328-3289, Lake Murray Blvd v3304-4454 (10.9 km per direction), each end PINNED on the far curb strip.
- **Islands**: the closure runs on the pavement 0.15 m off the island's race-side curb, nose tip to nose tip, so
  every nose, the deck and the beam's bare ends lie behind it (6.86 m minimum beside the island).
- **Curb strips** continuous over all three bridge spans (one closed loop per side); kerbs at all five corners, cut
  back where either closure stands on them — 8 since the fix round: the College/Navajo and Navajo/Jackson inside
  kerbs are DROPPED and the hairpin's inside kerb is pulled back to v751-763, each because it lay across a ribbon
  fold (track.config.json `race.kerbs.trims`, measured; "Fix round" below).
- **Packaging**: common `_race.kn5` (strips + kerbs) + `_closure_race_cw.kn5` / `_closure_race_acw.kn5`; each race
  ini lists only its own closure.
- **Gates**: `tools/no_route.py` on each layout's built gate OBJ (planned inside the band writer), `verify_race`
  C′ / J / K / L / M / N, kn5 roles, per-layout drive_test / audit; a race layout red on these is never installed.

### What this round measured on the v2 declaration (scratch copy, the spec's config block)

| | race_cw | race_acw |
|---|---|---|
| closure | 10,907 m in 4 runs, 2,456 m along island faces | the same, mirrored |
| clear width min / median | 6.86 / 11.36 m | 6.86 / 11.36 m |
| pin rates (1:x) | 6.0, 4.69 (v1506), 3.56 (v1521), 3.29 (v2311), 6.0 ×3, 10.0 (v4454) | the mirror |
| min plan radius | 22.4 m at v1543 | 24.1 m |
| mirror y_acw = −y_cw on running vertices | max 0.113 m (2.49 m incl. the convergences, which lead each island in each layout's own travel) | |
| planned no_route | **0 leaks**, 139,130 m² reached, lap complete | **0 leaks**, 138,826 m² |
| kerbs | 10; the four L outside kerbs clipped to the boxes (770: v744-776, 1514: v1507-1520, 2319: v2312-2327, 3297: v3290-3303) by race_cw's funnels | inside kerbs unclipped |
| virtual BUILT fill (declared strips + closure on the deck + today's guard rails) | 0 leaks, 0 / 406 probes reached | 0 leaks, 0 / 406 |

The same v2 declaration with today's bridge gaps put back FAILS the planned fill at exactly the uncovered span
ends — the continuous strips are load-bearing.

### Full scratch rehearsal (spec P7, 2026-10-11)

`SHIP_PROJ=<fresh copy of k10-sd-v021/project minus build/> bash tools/ship_sd.sh --skip-blend`, run twice on
fresh copies, identical numbers, about 5 minutes each. Every gate line:

| Gate | race_cw | race_acw | street |
|---|---|---|---|
| planned no_route | PASS — 0 leaks, 0 blocked, 0 / 406 probes, 139,130 m² | PASS — 138,826 m² | — |
| verify_race | OK: closure 3,637 rings ≤ 0.007 m off its line, pins ≤ 0.006 m | OK: 3,636 rings, ≤ 0.007 m, ≤ 0.005 m | — |
| (common) | 15 curb-strip objects, closed loops, bridges seated 328 hit / 0 interpolated, 0 free ends, 16 pins 0.000 m off the far strip, 10 kerbs | | |
| check_race_kn5 | common OK (`_race.kn5` 10,283,552 B); closure `cw` OK (5,433,534 B) | closure `acw` OK (5,432,722 B) | — |
| verify_kn5 / `--inis` | OK / OK (ini = road + `_race` + `_closure_race_cw` + spawn) | OK / OK | OK / OK |
| drive_test | barrier_missing 0 of 37,869, obstruction 0, severe 0 | 0 of 37,870, 0, 0 | 82 / 391 / 0 / 101 — identical |
| audit | D 0 / K 158 / I 145 / F 15, W 0 | the same | D 512 / K 154 / I 145 / F 15 — identical |
| **no_route BUILT** | **PASS — 0 leaks, 0 doors, 0 / 406 probes, lap complete, spawns reached** | **PASS — the same** | — |
| RACE_RED | not red | not red | — |

- **(Resolved by the fix round: K 154.)** **K 158 > 154 is a ribbon defect, named, not exempted:** 4 verts of the new `1KERB_race_1514_in` at v1518, where
  the road is two `1ROAD` sheets 0.093 m apart (College/Navajo inside-corner fold, 0033/0046 class). The kerb sits
  flush on the upper (driven) sheet; K measures it against the lower one (+0.133 / +0.136 m). Fix = one sheet
  at the fold (the ribbon's owner).
- **D 0 is an exemption effect:** the street's 512 D verts are all the road kn5's `1WALL_guard`, every one inside
  a race layout's declared band; the street audit keeps counting them.
- **Teeth on the real kn5s:** race_cw without its closure kn5 FAILS (81,466 m², 5 doors, 390 / 406 probes); with
  the other direction's closure FAILS (60,266 m², 10 doors, 311 / 406 probes, the lap blocked in 20 spans).

### Fix round (2026-10-11, after the critic of `c0361f7`)

**1. No kerb under a road sheet.** Measured on the P7 rehearsal's BUILT road kn5 (scratchpad `corr2/m/kerb_sheets2.py`:
every non-shoulder 1ROAD sheet under each kerb station's footprint, at its lane lip, mid-line and outer edge, every
0.3 m; "under" = a second sheet more than 0.02 m away standing over the kerb's top):

| kerb (inside, side R) | stations | on one sheet | under the other sheet | decision (`race.kerbs.trims`) |
|---|---|---|---|---|
| `1KERB_race_1514_in` College/Navajo | 34 | 18 — about 1.5 m at each end (v1508-1509, v1518-1519) | 13 at v1517-1518, ≤ 0.05 m; 4 verts +0.13 m over the lower sheet (race K 158) | **dropped** — no single-sheet stretch reaches the apex |
| `1KERB_race_2319_in` Navajo/Jackson | 51 | 43, but in two pieces: 4.5 m on entry (v2313-2314), about 5 m on exit (v2324-2326) | 8 at v2315 / v2323-2324, up to **0.42 m** (sheets 0.46 m apart) — the kerb vanishes under the asphalt at the apex race_cw's AI uses | **dropped** — neither piece is at the apex |
| `1KERB_race_770_in` hairpin (installed since 0047) | 139 | 126 | 13 at v764 (≤ 0.04 m) and v774 (≤ 0.14 m; the installed `race_authored.json` lists 0.166 m of other deck over it at v774) | **pulled back to v751-763**: 111 stations, all one sheet; a 26 m kerb on the entry that stops 4 m short of the old trimmed corner (the 4 m exit leg goes) |
| `1KERB_race_3297_in` Jackson/Lake Murray | 46 | 40 | 0 — two sheets 0.026-0.028 m apart at v3298-3299, the kerb's top 0.012 m clear of the upper one | kept |
| `1KERB_race_0_in` seam, all five outside kerbs | — | all | 0 | kept |

The folds themselves stay a named ribbon defect (0033/0046 class, the ribbon's owner) — not fixed here. A kerb can
now only leave or shorten through `race.kerbs.trims` (each entry carries its measured why; `barrier_bands` refuses a
trim that lengthens a run or names no kerb), and `verify_race` E fails any authored kerb station under another ROAD
sheet (the author measures it on the real deck: `race_authored.json objects[].under_road`).

**2. Scenery vs the race lanes.** `verify_race` G now also checks every CSP TreeFX trunk (r 0.30 m) and every W1-6
sign post (r 0.03 m) against each race layout's lane and wall footprints — before Blender from
`make_treefx.plan`, and again on the WRITTEN `trees.txt` right after `make_treefx` in the ship
(`--scenery-only`). On this build: 15,261 trees + 18 posts, 394 beside the race road, **0 in a lane or a wall**,
nearest 0.655 m (a median bush beside the closure). Teeth: the raw scatter palms the critic named (v763 on the
hairpin kerb, v4495 at the seam) FAIL it.

**3. Release + licensing per Kevin's stance** (2026-10-11: "No one actually cares about assets in free mods for a
13 year old game" — provenance never withholds or degrades a release; the CC0/full split is a tool; publishing is
his go per release). The release READMEs' VERSIONS blocks describe the corridors (own-side Alvarado-wide lane,
whole street on Alvarado and the I-8 deck, open boxes at the three corners, closure along the medians), both
CREDITS / LICENSES name the K-rail on `_race.kn5` AND both `_closure_race_*.kn5`, and
`tools/pack_release.py --with-race` keeps the race layouts in the CC0 package (default still street-only, only
because the prodrive-server catalog text describes one layout). What the K-rail is, for the record: Kevin's
owned asset pack, the 4 m jersey module (`assets/models/concrete_barrier_4m.obj` + `concrete_barrier_diffuse /
normal.png`), whose licence terms are not recorded in `assets/licenses.json` — a fact, not a blocker.

**4. Version** `track.config.json` 0.16.0 → **0.17.0** (Content Manager shows `[build 0.17.0]`; the installed 0047
build is 0.16.0).

### Fix-round rehearsal (2026-10-11, 14:41:36-14:46:56)

A fresh copy of `k10-sd-v021/project` minus `build/` (scratchpad `corr2/project`), `SHIP_PROJ=<copy> bash
tools/ship_sd.sh --skip-blend`, log `corr2/ship.log`. Every gate line, against the installed build (`8fbfa0e`,
`tracks/san-diego-lake-murray/data/`: 0047's one `track.race.obj` for both race layouts):

| Gate | race_cw | race_acw | street |
|---|---|---|---|
| planned no_route | PASS — 0 leaks, 0 doors, 139,130 m² (read-back: 0 leak cells / 0 blocked / 0 probes / 0 spawns) | PASS — 138,826 m² (the same zeros) | — |
| verify_race | OK: 8 kerbs, every `under_road` 0; closure 3,637 rings ≤ 0.007 m off its line, 8 pins ≤ 0.006 m; G scenery 0 of 15,279 in a lane / wall | OK: 3,636 rings, ≤ 0.007 m, pins ≤ 0.005 m | — |
| (common) | 15 curb-strip objects / 9,054 rings, 0 free ends, 16 pins 0.000 m, bridges 328 hit / 0 interpolated; F 0.48 m (floor 0.30); G lamps 0 inside, nearest closure 2.365 m | | |
| check_race_kn5 | common OK — `_race.kn5` 10,253,588 B, 23 meshes (15 strips + **8** kerbs); closure `cw` OK 5,433,534 B | closure `acw` OK 5,432,722 B | — |
| verify_kn5 / `--inis` | OK / OK (16 START/PIT in the lane, nearest face 0.48 m) | OK / OK | OK / OK |
| scenery re-check (written `trees.txt`) | OK — 0 in a lane / wall, nearest 0.656 m | OK | — |
| drive_test barrier_missing / obstruction / severe | 0 of 37,869 / 0 / 0 (installed: 0 of 34,833 / 0 / 0) | 0 of 37,870 / 0 / 0 (installed: the same zeros) | — / 0 / 0 |
| drive_test soft top / floating / excursion / kinks per km | **44** / 391 / **1** / **1.48** (installed 67 / 391 / 4 / 5.27) | **40** / 391 / 0 / **1.34** (installed **13** / 391 / 0 / 2.82) | 82 / 391 / 101 / 4.97 — identical (only an informational `lane` key added) |
| audit A / B / C / E / J | 0 | 0 | 0 |
| audit D / K / I / F | **0 / 154 / 145 / 15**, W 0 = 314 (installed `audit.race.json` 512 / 154 / 145 / 15 = 826) | the same | 512 / 154 / 145 / 15 = 826 — `audit.json` byte-identical (md5 `296a2bc1…`) |
| **no_route BUILT** | **PASS** — 0 leaks, 0 doors, 0 / 406 probes, 0 blocked, 0 spawns unreached, 139.1k m² | **PASS** — 138.8k m² | — |
| RACE_RED | not red | not red | — |

Final line: `GATES: street drive_test exit 1, street audit exit 1, race drive_test exit 1, race audit exit 1, race
no_route exit 0; race layouts red on their own gates: none; NOT INSTALLED` — the inherited counters only, as on
every build of this track. Street AI `fast_lane.ai` byte-identical (md5 `93a09e5a…`); workshop `loop.blend` md5
`fbcbbff4…` before and after; nothing in the AC folder newer than the run.

**No worse than the installed build — the per-metric comparison the `--force-install` rule asks for:**
- Street: every gate value identical.
- Race audit: D 512 → 0 (exemption on each layout's own bands; the street audit keeps all 512), K 154 = 154, I 145
  = 145, F 15 = 15, A/B/C/E/J 0 = 0, W 0 (new). No worse.
- Race drive_test, race_cw: soft top 67 → 44, excursion drops 4 → 1, kinks 5.27 → 1.48 /km; floating 391 = 391;
  barrier_missing, obstruction, severe 0 = 0. No worse.
- Race drive_test, race_acw: excursion 0 = 0, kinks 2.82 → 1.34 /km, floating 391 = 391, barrier_missing,
  obstruction, severe 0 = 0 — but **soft top 13 → 40 is a higher count.** Every one of the 40 is grass poking
  through the UNCHANGED road kn5 (the street layout counts 82 on it, identical to the installed build), now inside
  the race lane because the lane changed: 25 in the College/Navajo intersection (v1511-1514), 11 in the hairpin
  (v754-756) and 2 in the Navajo/Jackson intersection (v2317) — the boxes are the whole intersection now, where
  0047's centre chain cut them in half — and 2 at the left lane edge by the Del Cerro West mouth (v1082). No new
  geometry; a wider window onto the same inherited defect. **Kevin's call** whether that counts as "no worse"
  for `--force-install` — it is stated here so the call is made on the number.

### Ship (the exact command)

On the workshop, with **Assetto Corsa and Content Manager closed** (the install now refuses while `acs.exe` or
Content Manager runs):

```bash
bash tools/ship_sd.sh --skip-blend --force-install
```

`--skip-blend` resumes from the authored `loop.blend` (the race author step still runs — it is what this
rehearsal exercised); without it the chain regenerates the draft `loop.blend` and re-runs every authoring stage,
which no rehearsal has run under the v2 config. `--force-install` is needed only for the inherited street / race
counters above; RACE_RED and a failing no_route are never forced. The sync-back then writes `loop.blend`,
`data/` (incl. `race_verify.scenery.json`) and `ai/` into `tracks/san-diego-lake-murray/` — commit those
separately ("Reinstalled: …", the 8fbfa0e pattern).

## Decisions left (defaults encoded — Kevin's call)

1. **L8 wording** (layouts add kn5s, never alter the road) — built under the proposed wording (0047 Q9).
2. **Barrier height** 1.20 m (Kevin's module).
3. **Publishing the race versions** — whenever he wants: `tools/pack_release.py --with-race` puts them in the CC0
   zip (update the prodrive-server catalog text with it). Not a licence question (Kevin's stance, 2026-10-11).
4. **race_acw soft top 40 vs 13** for the `--force-install` comparison (above).

Tune after the drive, not before (spec §17): `clear_width_m` (own side only ≈ 7.7 m on 17 m roads),
`island_mode` (island top, +0.97 m beside the medians, after three proofs), the steep exit funnels, a centred grid.

## Who does what (2026-10-11 work split)

| Part | Files | State |
|---|---|---|
| Declaration v2 + gates | `tools/barrier_bands.py`, `tools/race_corridor.py` (new), `tools/no_route.py` (new), `scripts/geometry/{median_zone,drive_test,audit_mesh}.py`, their tests, `fleet/GATES-CHANGELOG.md` | built, tested on scratch copies |
| Authoring / packaging / AI | `tools/{race_furniture,author_race_furniture_blend,split_exports_blend,verify_race,check_race_kn5,plot_race_furniture}.py`, `scripts/ac/{verify_kn5,track_folder,write_ai_line}.py`, `tools/pack_release.py` | built, tested on scratch copies |
| Ship chain | `tools/ship_sd.sh`, `tests/tools/test_ship_sd_chain.py` | wired and rehearsed end to end on a scratch copy (above) |
| Config | `tracks/san-diego-lake-murray/track.config.json` `race.corridor` + `layouts[].closure_token`, `run` / `ui_description` | applied (spec §9.1) |
| Fix round (critic of `c0361f7`) | `track.config.json` (`race.kerbs.trims`, version 0.17.0), `tools/{barrier_bands,race_furniture,author_race_furniture_blend,verify_race,make_treefx,pack_release}.py`, `tools/ship_sd.sh`, release texts, tests, `fleet/GATES-CHANGELOG.md`, ledger 0047's status, the drive report | rehearsed on scratch (above); not committed, not shipped |

## Scope

Lake Murray only (the only track with race layouts). The containment gate is general: any race layout with a
v2 declaration and a gate OBJ.

## Verification

Decided before the build: for each race layout on its BUILT gate OBJ — `no_route` 0 leaks with the lap complete
and every forbidden probe unreached, `barrier_missing` 0, `obstruction_stations` 0, audit D / K / I / F no higher
than 512 / 154 / 145 / 15 and W 0; the street layout's gates identical to the pre-change build (drive_test
82 / 391 / 0 / 101, audit 512 / 154 / 145 / 15); since the fix round also no kerb under a road sheet and no
TreeFX trunk / sign post in a race lane or wall. Then Kevin's drive — pre-filled for both directions by street
name in `tracks/san-diego-lake-murray/drive-reports/2026-10-1x-race-corridors.md`: the cw Navajo exit funnel
(v1521); acw Navajo/Jackson and College/Navajo exits (v2311 / v1506); the acw 1:10 funnel off the I-8 deck at
speed (v4454-4427); the 6.86 m island carriageways; the 17 m roads with the dead lane behind the closure; every
box in and out; the grid on Alvarado; a wall hit at speed (does the K-rail's sloped foot launch the car into the
closed lanes?); flicker where the closure meets the curb strip; an AI race with 7 opponents; load time and FPS at
College/Navajo and on the I-8 deck.

---

## Appendix A — the judged spec (2026-10-11, verbatim from the read-only design run)

`SCR` paths in it point at the design run's scratchpad, which does not outlive the session; the prototype solver's
output is preserved as `tests/tools/fixtures/sd_corridor_proto.json` and ported as `tools/race_corridor.py`.

### Lake Murray race corridors: final spec (ledger 0049, to be filed)

**Status:** design only, 2026-10-11. No repo file has been modified, and nothing has been built, exported or installed.

**What it replaces:** 0047's shared centre K-rail chain.
- 0047 Q2 and Q7 become moot.
- Q1 stays answered: side streets are sealed.
- Q5, Q6, Q9, Q10 and Q11 stand.

**What it is built from:** a synthesis of three candidate specs, all of them read-only measurements of `k10-sd-v021/project`:
- `centerline.local.json`: 4,499 points, closed, clockwise = increasing index, lap 13,480 m;
- `widths_m`, `median_bands.json`, `barrier_bands.json` (2026-10-11);
- the built `data/track.race.obj`.

`SCR` below means `C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/scratchpad/corridor/`. In it:
- `work/corridor.py` is the reference closure solver (pavement mode). Its tables are in `work/report_tables.txt`.
- `spec/corridor_it.py` is the island-top variant.
- `noroute_proto.py` is the containment-fill prototype.
- Pictures: `corridor_overview_{cw,acw}.png`, `corridor_closeup_1..8_*.png`, `leak_*.png`, `junction_v*.png`. The junction plates show a rejected cross-barrier variant, but their leg and OSM data stand.

> Kevin, 2026-10-11, verbatim: "racetrack versions of these, we need full intersections available for turning. And the entire other lane blocked off from access."
>
> Width: "We want more or less an Alvarado's width for the entire track with deviances in various areas."
>
> Intersections: "Corners the race turns at" (side streets stay sealed).
>
> Earlier (0047): "The barriers are for wide roads, Alvarado should be the entire street"; "With Barriers between directions, leading up to medians but not on them"; "The tracks will get additional race curbs and barriers along the inside of the sidewalks".

Anything marked **INVENTED** has no measurement behind it and is recorded as INVENTED in `fleet/GATES-CHANGELOG.md`.

---

#### 0. What changes

| | Today (0047, installed) | This spec |
|---|---|---|
| Centre K-rail chain shared by both race layouts | 8.5 km in 6 runs; free ends at v780 and v4440 | **retired** |
| Curb-line strips | both curbs, gapped over 3 bridge spans (v609-619, v856-902, v4444-4491) | both curbs, **one closed loop per side, no gaps** |
| Closure (the wall that shuts off the other direction) | none | **one per direction**: 4 runs, about 10.9 km |
| Race kerbs | 7 | **10**: the inside kerbs at v1514, v2319 and v3297 come back |
| kn5 files `race_cw` loads | road + `_race` + spawn | road + `_race` (common) + `_closure_race_cw` + spawn |
| Containment gate | none | **`no_route`** flood fill per layout on the BUILT gate OBJ; hard, blocks install |

**Today's installed race layouts already break Kevin's rule.** The prototype fill on today's built `track.race.obj` (race_cw) reached 750k m² outside the corridor through 51 door clusters:
- **Three bridge strip gaps.** The Alvarado span v609-619 has no rail at all. The College rail covers only v864-887 of v856-902, and the I-8 rail only v4454-4474 of v4444-4491.
- **Two chain free ends,** at v780 and v4440.
- **All ten island noses.** The island beam stops 3 vertices (8.5-9.5 m) short of every tip, and the island curb is only 0.18 m tall.

The street layout is unaffected.

---

#### 1. The rule

**R1. Width.** "Alvarado's width" = **11.36 m clear**, wall face to wall face. It is MEASURED:
- Alvarado v25-723 is 13.00 m curb to curb at all 699 vertices.
- The curb strips' road faces sit at ±5.68 (`race.edge_inset_m` 0.82) on 688/688 built stations.
- Using 13.0 instead would make every other street 1.64 m wider than Alvarado as raced.

The closure centre stands 0.82 + 11.36 + 0.335 = **12.515 m** from the race-side curb line. On 13.0 m Alvarado that is exactly where the far strip already stands, so Alvarado is the whole street by construction.

**R2. Race side.** The race-side boundary is the existing curb strip on that direction's right-hand curb, the whole lap: centre at `w/2 − 0.485`, road face at `w/2 − 0.82`.

**R3. Closure.** The far boundary is the same jersey strip (1.20 m tall, 0.67 m base). Its road face stands 11.36 m from the race-side strip face. The distance is measured against a flare-free **base width**, so the wall stays straight where the curb wiggles; race-side flare pockets widen the lane behind the moving curb strip instead. Everything beyond the closure is unreachable.

**R4. Whole street.** There is no closure where the base width is under **15.67 m** (11.36 + 2×0.82 + 2×0.335 + a 2.0 m pocket, INVENTED). Below that, less than a 2 m lane would remain behind the wall. This makes all of Alvarado and the I-8 deck whole street.

**R5. Islands.** Beside a median island, the corridor is that direction's own carriageway. The closure runs **on the pavement along the island's race-side curb**, 0.15 m off it ("leading up to medians but not on them"). It runs nose tip to nose tip and crosses each tip on the race side, so every nose, the island deck and the beam's bare ends lie behind it.

**R6. Open boxes.** At the five corners the race turns at, the whole intersection is open, curb strip to curb strip. Each leg closure ends **pinned on the far curb strip at the box edge**:
- There are no square cross barriers and no dead-end pockets.
- Funnels are 1:6 or gentler wherever the geometry allows.

**R7. Side streets.** Side streets stay sealed.
- On the race side, the strip runs straight across the mouth.
- On the far side, the mouth is also behind the closure.
- Both strips are continuous in the common kn5, so every mouth is sealed at full height in both race layouts regardless.

**R8. No way across.** No reachable point leads to the other side:
- Every wall end is buried in another wall: closure pins are buried in a continuous curb strip, and the curb strips are closed loops.
- `no_route` proves it on each BUILT gate OBJ.

**R9. Per-direction closures.** On 17 m roads the cw and acw corridors overlap by 7.36 m, so each direction's closure stands inside the other's lane. Each race layout therefore loads only its own closure kn5, and the centre chain is retired.

##### 1.1 Constants

| Constant | Value | Status |
|---|---|---|
| strip road face / centre / K-rail half base | 0.82 / 0.485 / 0.335 | measured asset + current declaration |
| clear width W | 11.36 | MEASURED (Alvarado as raced) |
| running band | 10.86-12.86 (W −0.5/+1.5) | INVENTED |
| whole-street threshold (base width) | < 15.67 | derived; the 2.0 m pocket is INVENTED |
| base width | `widths_m` opened (erosion then dilation) over ±60 m, Gaussian σ 20 m, clamped ≤ real width | INVENTED |
| rate limits, lateral per metre of travel | toward the race side ≤ 1:12; away ≤ 1:6; within 120 m of a pin ≥ 1:6 where feasible; I-8 pin 1:10 | INVENTED |
| island offset | closure centre = authored island race-face + 0.485 (0.15 m off the island curb); island face enveloped over ±30 m; authored nose taper `NOSE_HALF` 0.25 over `NOSE_VERTS` 3 | 0.485 / 0.25 / 3 measured; 30 m INVENTED |
| box | the place_signs corner PC−2..PT+2 | INVENTED pad |

##### 1.2 Frames

- **v** = centreline vertex.
- **y** = metres forward-LEFT of the increasing-v tangent (`race_furniture.left_normal`): the frame the author already sweeps in.
- **r** = metres RIGHT of the layout's own travel: cw `r = −y`, acw `r = +y`. Declarations and gates use r.

| Layout | Travel | Race side (fwd frame) | Closure side | Turns at the 5 corners |
|---|---|---|---|---|
| race_cw | increasing v | R (lake side; the INSIDE of every bend) | L | right; pins on the outside lip |
| race_acw | decreasing v | L (the outer carriageway) | R | left; pins on the inside lip, so it gets the apex |

`y_acw(v) ≈ −y_cw(v)`, within 0.3 m in running zones.

---

#### 2. Zones (vertex ranges identical for both layouts)

| Zone | Vertices | Road (m) | Corridor |
|---|---|---|---|
| **WHOLE** | **v4454 → v0 → v777** | I-8 deck 13.5-15.4; seam box 17-27.5; Alvarado 13.0-13.5; hairpin box to 30 | both curb strips. Alvarado 11.36 (11.86 on v730-757); deck 11.86-13.76; seam and hairpin full width |
| **BOX** | **[1506,1521] [2311,2328] [3289,3304]** | 20-30 | the full intersection between both strips, including today's trimmed inside corners |
| **CLOSURE** | **A [777,1506] College, B [1521,2311] Navajo, C [2328,3289] Jackson, D [3304,4454] Lake Murray Blvd** | 16.4-32.5 | race-side strip face to closure face. Both ends of each run are pinned on the far strip. |

- **Boxes.** Each box is PC−2..PT+2 of the place_signs corners (PC/PT 1508/1519, 2313/2326, 3291/3302). Each contains every junction cut measured at that corner. The seam corner (PC 4493..PT 7) and the hairpin (PC 751..PT 775) lie inside WHOLE.
- **Pins.** There are 8 pins: v777, 1506, 1521, 2311, 2328, 3289, 3304 and 4454. All are on real strip rings, and none is in an `edge_corners` removed set (R folds 763-774, 1508-1517, 2314-2324, 3292-3300, 4495-5).

---

#### 3. The closure line, per street (race_cw, pavement mode)

This table is from `SCR/work/report_tables.txt`. For race_acw, mirror y; its differences are listed after the tables. "Clear" is face to face; "behind" is the sealed dead pocket.

**Run A, College, v777 → v1506 (2,215 m)**

| v | Feature | y_cw (m) | Clear (m) |
|---|---|---|---|
| 777 | pin on the L strip, road 30 | +14.52 | – |
| 778-823 | 1:6 funnel (+6.0 at v800, +4.7 at v810) | +14.0 → +3.48 | 19.4 → 10.8 |
| 823-845 | 1:12 convergence onto College-1's R face | +3.48 → −2.04 | → **7.9** at v845 |
| 846-1258 | College-1; Del Cerro opening v1074-1095, nose to nose; College-2 | −1.5 … −4.0 (opening −1.6 … −2.4) | **6.86 min** / 7.8 median (opening 11.2-11.7) |
| 1259-1278 | 1:8 divergence across the centreline | → +3.44 | ≥ 10.86 |
| 1279-1346 | 17 m neck | +3.51 … +3.94 | 10.86-11.28 (behind: 3.4) |
| 1347-1373 | 1:12 convergence | → −2.99 | ≥ 9.23 (v1355) |
| 1374-1487 | College-3 | −2.1 … −4.0 | 8.81 min / 9.21 median |
| 1488-1506 | divergence **1:4.7 (forced)** to the pin | → +10.03 (road 21) | ≥ 12.45 |

**Run B, Navajo, v1521 → v2311 (2,381 m)**

| v | Feature | y_cw (m) | Clear (m) |
|---|---|---|---|
| 1521 | pin, road 30 | +14.52 | – |
| 1522-1539 | funnel **1:3.6 (forced: the island tip is 57 m from the box)**, passing 0.7 m clear of the tip | → −0.43 | ≥ 11.43 |
| 1540-1739 | Navajo-1 | −0.7 … −3.9 | **6.86** |
| 1740-1756 | 1:6 divergence | → +3.32 | ≥ 8.77 |
| 1757-2164 | 17 m road (1,222 m) | +3.41 … +4.01 | 10.86-11.36 (behind: 3.3-4.0) |
| 2165-2182 | 1:12 convergence | → −0.48 | ≥ 10.46 |
| 2183-2297 | Navajo-2 | −0.73 … −3.45 | 6.86 min / 9.72 median |
| 2298-2311 | divergence **1:3.3 (forced)** to the pin | → +11.88 | ≥ 12.08 |

**Run C, Jackson, v2328 → v3289 (2,882 m), no islands**

| v | Feature | y_cw (m) | Clear (m) |
|---|---|---|---|
| 2328 | pin, road 24 | +11.52 | – |
| 2329-2356 | 1:6 funnel | → +2.54 | ≥ 13.38 |
| 2384-2528 | 17 m | +3.51 … +4.01 | 10.86-11.36 |
| 2529-2756 | 24-29 m section, tapers ≤ 1:19 | +1.5 … +3.5 | ≥ 10.86 |
| 2757-3268 | 17 m with 24 m flares. Flares are not tracked: the curb strip moves out and the closure stays put. | +3.53 … +4.63 | 10.88-11.36 (14.9 in flare pockets) |
| 3269-3289 | 1:6 divergence to the pin | → +9.77 (road 20.5) | ≥ 14.27 |

**Run D, Lake Murray Blvd, v3304 → v4454 (3,450 m)**

| v | Feature | y_cw (m) | Clear (m) |
|---|---|---|---|
| 3304 | pin, road 30 | +14.52 | – |
| 3305-3349 | 1:6 funnel | → −1.33 | ≥ 12.52 |
| 3350-3664 | 30/24 m alternation. The closure stays inside cw's own half, because that half alone is 14.2 m clear. | −2.47 … +0.02 | 10.86-13.2 (behind: 11-16) |
| 3665-3693 | to the 17 m road | → +3.51 | ≥ 10.86 |
| 3694-4338 | 17 m with 24 m flares | +3.52 … +4.02 | 10.87-11.36 |
| 4339-4426 | to 24-30 m. The Parkway/Wisconsin mouth v4424 (R) is sealed by the race strip. | +0.66 … +1.60 | 11.53-14.76 |
| 4427-4454 | ≤ 1:7.7 divergence to the deck pin (trailing) | → +7.22 (road 15.4) | ≥ 13.75 |

**race_acw differences from the mirror**
- **Convergences** come before islands in acw's own travel:
  - v1285→1259 at 1:12 (minimum clear 9.16);
  - v1759→1740 at 1:12 (minimum **7.78**).
- **Divergences:** v1373→1354 (1:8) and v2182→2165 (1:6).
- **Pins** are on the R (inside) curb: −14.52 / −10.03 / −14.52 / −11.88 / −11.52 / −9.77 / −14.52 / −7.22.
- **Steep exit funnels** sit on the INSIDE of acw's exits, away from the car's drift: 1:4.7 onto College-3 and 1:3.3 onto Navajo-2.
- **I-8:** acw peels off the R deck strip at v4454 and converges **1:10** to −1.6 by v4427. This is the only at-speed funnel on the lap.
- **Del Cerro:** the closure runs at +1.6 … +3.2. The Del Cerro W mouth (v1085 L) is on acw's race side and is sealed by its strip.

**Totals per direction:**
- About 10.9 km of closure, about 2.47 km of it along island faces.
- Inside the running band: 6,684 m (cw) / 6,715 m (acw).
- Narrower than the band: 148 m (cw) / 115 m (acw). All of it is in the 1:12 convergences into island noses.
- Minimum plan radius of the closure centre: 22.4 m at cw v1543. It is ≥ 30.8 m at every other pin and ≥ 33 m in running zones. 0 folds.

---

#### 4. Deriving the closure line: `tools/race_corridor.py` (new, pure, no bpy)

Port `SCR/work/corridor.py`, dropping its `RAILS` special case (the strips are now continuous over the decks). `barrier_bands.py` calls it.

Per direction, the work is done in `g` = lateral toward the race side, over each run in travel order, with arc-metre stations.

1. **Base width.** `B = min(w, gauss_σ20(open_±60m(w)))`. Every flare or notch shorter than 120 m disappears.
2. **Target.** `g_t = B/2 − 0.82 − 0.335 − 11.36`.
   - Beside islands: `max(g_t, F + 0.485)`, where F is the island race-face half-width closed then opened over ±30 m.
   - Across the Del Cerro opening (v1074-1095), F is interpolated linearly from nose to nose.
3. **Hard bounds.**
   - `L = max(far strip centre −(w/2 − 0.485), authored island half-width + 0.485)`. The authored half-width includes the nose taper.
   - `U = B/2 − 0.82 − 0.335 − 10.86` (the floor), with `U ≥ L`.
   - At pins, `L = U =` the far strip centre.
4. **Rates.** Slope-limited envelopes on L and U:
   - ≤ 1:12 toward the race side and ≤ 1:6 away;
   - within 120 m of a pin, `max(1:6, forced × 1.02)`;
   - v4454 at 1:10.
   - Expected forced rates are exactly 1:4.7 (v1506), 1:3.6 (v1521) and 1:3.3 (v2311). Anything steeper than 1:3 FAILS.
5. **Solve.** Minimise `Σ(Δg)²/Δs + Σ Δs(g − g_t)²/40²` within [L, U]:
   - projected SOR, ω 1.8, to 1e-6 (≤ 190 sweeps on SD);
   - then a 4 m Gaussian, re-clamp, re-pin.
6. **Emit.** `closure_y_by_vertex` and `lane_by_vertex = [y_lo, y_hi]` (the corridor faces, forward frame):
   - cw: `y_lo = −(w/2 − 0.82)`, `y_hi = y − 0.335`;
   - acw: `y_lo = y + 0.335`, `y_hi = +(w/2 − 0.82)`;
   - WHOLE / BOX / pin vertices: `±(w/2 − 0.82)`.

**Acceptance for the port.**
- **First step:** before porting, dump the prototype's per-vertex g for both directions to `tests/tools/fixtures/sd_corridor_proto.json` while SCR still exists.
- The test pins: runs and pins exactly; pin y within 0.01 m; the §3 segment minima within 0.05 m; 0 backward steps; radius ≥ 20 m (INVENTED floor); mirror ≤ 0.3 m; fixture equality.

---

#### 5. Islands

**Default: pavement (R5).**
- The closure seats on the ROAD mainline rows like every strip today, so no new seating code is needed. It never touches the island curb ridge, the planting, the beam or the posts.
- The shared `1WALL_guard` beam (0.24 m, 0.63-0.93 m above the road) stays as scenery. Nothing relies on it, and the road kn5 is unchanged (L8).
- Clear width beside the median, minimum / median: College-1/2 6.86 / 7.8; College-3 8.81 / 9.21; Navajo-1 6.86; Navajo-2 6.86 / 9.72.

**Post-drive option (not part of this ship): `island_mode: "island_top"`.**
- Closure centre 0.485 m inside the island curb, on the ROAD slab under the island.
- It gains 0.97 m (7.83 m minimum).
- It is offered only if Kevin finds 6.86 m too tight, and only after three proofs:
  - (a) the two disagreeing measurements of island deck height are resolved on the built OBJ at v900, v1600 and v2250;
  - (b) the closure keeps ≥ 0.05 m off the beam where an island is narrower than 1.88 m (Navajo-2's minimum is 1.50 m);
  - (c) it reverts to the pavement line around every 0.5 m nose.
- The reference solver is `SCR/spec/corridor_it.py`.

**Rejected:** extending the beam to the tips. Cars climb the 0.18 m curb onto the deck, and karts pass under the beam.

---

#### 6. The five corners

| Corner | Box | Inside corner X (R, trimmed) | race_cw (right turn): in / out | race_acw (left turn): in / out | Unbuilt legs sealed by the outer (L) strip |
|---|---|---|---|---|---|
| v0 seam, 70th / Alvarado / LMB (98°) | in WHOLE (v4491-9) | extend corner 4495→X→5 | no closure; the deck pin v4454 is 113 m upstream | same | 70th St S, Alvarado E (the I-8 ramps tee 90-190 m away) |
| v770 hairpin, Alvarado → College (~170-177°) | in WHOLE (v749-777) | loop corner 763→X→774 | in whole street; out pin v777 +14.52 at 1:6 | in pin v777 −14.52 at 1:6 (outside the trimmed corner); out whole street | College SB/S, Canyon Crest, East Campus |
| v1514 College / Navajo (97°) | [1506,1521] | loop corner 1508→X→1517 | in v1506 +10.03, 1:4.7 trailing; out v1521 +14.52, **1:3.6** | in v1521, 1:3.6 trailing; out v1506, 1:4.7 (inside) | Waring Rd |
| v2319 Navajo / Jackson (89.5°) | [2311,2328] | loop corner 2314→X→2324 | in v2311 +11.88, 1:3.3 trailing; out v2328 +11.52, 1:6 | in v2328, 1:6; out v2311, **1:3.3** (inside) | Navajo E, Jackson N |
| v3297 Jackson / LMB (107°) | [3289,3304] | extend corner 3292→X→3300 | in v3289 +9.77, 1:6; out v3304 +14.52, 1:6 | mirror, 1:6 both ends | LMB N, Jackson S, LMB frontage roads |

- **Pin ends.** The last ring of each closure is centred ON the far strip's centre line at the pin vertex, at full height with no taper. At crossing angles of 1:6 to 1:3.3, its half-extent across the strip is 0.32-0.335 m, inside the strip's 0.335 m half base. So the end cap is buried: no gap and no blunt end.
- **cw exit funnels** stand on the OUTSIDE of cw's exits, glancing at ≤ 17°. These are the drive-test items.
- **At the seam,** the built ribbon covers only the turning half of the real intersection. "Full intersection" there means all the pavement that is built.

**Rejected: square cross barriers at the junction cuts.** They are 10-17 m walls standing head-on to every cw exit, and they leave 66-97 m² dead-end pockets at each acw apex.

**Kerbs: 10, all common.**
- Today's 7: 0 in/out, 770 in/out, and the outside kerbs at 1514/2319/3297.
- Three inside kerbs come back (R, PC..PT): 1514 v1508-1519, 2319 v2313-2326, 3297 v3291-3302. `detect_kerb_corners` emits them once the chain is gone.
- Kerb geometry is unchanged: 1.0 × 0.05 m.
- **Clip rule:** each kerb is cut to the longest contiguous run of stations containing the apex whose footprint stands ≥ 0.05 m clear of EVERY race layout's closure footprint. Expect the L outside kerbs near cw's pins to lose about 1-5 vertices per end; the exact amount is measured and recorded in `race_authored.json`.
- No kerbs go on closure faces in this ship.

---

#### 7. Containment prerequisites (load-bearing)

- **C1. Bridges.** `race.edge_gaps: "none"`. Both curb strips run over all three spans, seated on the mainline deck rows.
  - They stand 0.82 m inboard of the College panel (lateral 10.32) and about 0.15 m inboard of the I-8 deck rail (6.75-7.70). Audit's wall-crossing check gates any clash.
  - verify_race **L** fails any interpolated ring inside a span.
- **C2. No free ends.**
  - Each side's curb strip is ONE closed loop, cut into pieces at street boundaries that share rings, with no caps.
  - Closures end only at pins.
  - `BRIDGE_CLEAR_M` (9 m, INVENTED) and the free-end and nose tapers retire.
- **C3. Islands** per §5.
- **C4. Boxes and WHOLE.** Both strips are present, because they are full lap in the common kn5.
- **C5. Mouths.** v1085 (L, Del Cerro W), v1086 (R, Del Cerro E) and v4424 (R, Parkway/Wisconsin) are covered by their side's strip. The medium-connector loop v1086↔v4424 (a 2.5 km shortcut if opened) is unreachable in both layouts. The Del Cerro opening stays closed nose to nose; it is a 4-way, not a turn.
- **Carried defects (reported, not fixed here):**
  - At the seam, 4.16 m of the inside strip's extend corner stands off the ribbon over the 27.5 → 17 m width-step notch. The fix is a ribbon taper in the draft layer.
  - The Del Cerro W connector deck stands 0.28-0.54 m above the mainline behind edge_L. The strip is still 1.2 m tall on the race side.
  - At the Navajo/Jackson apex v2314, the ribbon fold stands 0.46 m over the strip base (0033/0046 class).

---

#### 8. Files and packaging

| File | Holds | Loaded by |
|---|---|---|
| `<slug>.kn5` | road, unchanged | all 3 layouts |
| `<slug>_race.kn5` (name kept) | COMMON: both curb strips (closed loops, no gaps) + 10 kerbs | race_cw, race_acw |
| `<slug>_closure_race_cw.kn5` | race_cw closure objects only | race_cw |
| `<slug>_closure_race_acw.kn5` | race_acw closure objects only | race_acw |
| `<slug>__<id>.kn5` ×3 | spawn nodes, unchanged | own layout |

**INIs:**
- `models_race_cw.ini` = [road, `_race`, `_closure_race_cw`, `__race_cw`], with spawn last as today. acw is the mirror.
- `models_street.ini` is unchanged.
- **No ini ever lists the other direction's closure kn5;** loading both would block both lanes.

**Why one common kn5 plus one closure kn5 per direction** (rather than two self-contained kn5s):
- the common part is identical by construction;
- today's race-kn5 path keeps its name and checks;
- a closure change does not re-export about 27 km of strip.

**Names:** all start with `RACE_PREFIXES`, so the `pbr.py` rows `1WALL_RACE` / `1KERB_RACE` are unchanged and there is no new texture.
- `1WALL_race_edge_<L|R>_<street>_<start>_<part>`: unchanged.
- `1KERB_race_<apex>_<in|out>`: unchanged.
- **New:** `1WALL_race_close_<token>_<street>_<start>_<part>`.
  - `token` comes from `layouts[].closure_token` ("cw" / "acw").
  - Objects are split at ≤ 800 rings with shared boundary rings (`split_plan`): about 7 objects per direction.
- `1WALL_race_kbar_*` is retired; its presence anywhere FAILS.

**Budget (estimates at 63.8 B per render vert):**
- Common kn5 about 155k verts, about 9.9 MB (today 196,763 verts / 12.56 MB, minus the 45,768-vert chain, plus bridge fill and kerbs).
- Each closure kn5 about 59k verts, about 3.8 MB.
- The FULL package grows about 5 MB. CC0 is unchanged.

---

#### 9. Declaration

##### 9.1 `tracks/san-diego-lake-murray/track.config.json`

Remove `race.centre_runs`, `race.wide_threshold_m` and `race.interior_corners`; barrier_bands FAILS if `centre_runs` is still present. Then add:

```json
"race": {
  "edge_gaps": "none",
  "corridor": {
    "clear_width_m": 11.36, "clear_width_source": "alvarado",
    "island_mode": "pavement",
    "whole": [4454, 777],
    "boxes": [{"apex": 1514, "i": 1506, "j": 1521},
              {"apex": 2319, "i": 2311, "j": 2328},
              {"apex": 3297, "i": 3289, "j": 3304}],
    "closure_runs": [[777, 1506], [1521, 2311], [2328, 3289], [3304, 4454]],
    "rate_toward_race_side": 12, "rate_away": 6,
    "pin_zone_m": 120, "pin_rate_min": 6, "pin_rate": {"4454": 10}, "steepest_pin_rate": 3,
    "base_open_m": 60, "base_sigma_m": 20, "island_env_m": 30, "attract_m": 40, "smooth_sigma_m": 4,
    "clear_floor_m": 10.86, "clear_hard_min_m": 6.5, "pocket_min_m": 2.0
  }
}
```

- **`clear_width_source: "alvarado"`** makes the writer re-measure `median(w − 2×0.82)` over v25-723. It FAILS if the result is more than 0.02 m off `clear_width_m`.
- **`closure_runs`** is pinned. The writer FAILS if the derived runs differ ("declared, validated, never derived silently").
- **Layouts:** add `layouts[].closure_token` ("cw" / "acw"). Rewrite `run` and `ui_description` to drop "centre barrier".

Proposed `ui_description` for race_cw (acw is the mirror):

> "...an Alvarado-wide lane on your own side of every road: concrete barriers along your curb and a second line closing off the opposite lanes (along the medians where there is one); the whole street on Alvarado and the I-8 bridge; the full intersection open at the five corners; side streets sealed. The AI line is a generated draft."

##### 9.2 `data/barrier_bands.json` version 2

**Kept:** `params` (with `params.corridor` echoed), `streets`, `corners`, `edge_corners` (the 5 R folds), `closed_mouths`, and `bridge_spans_m` (informational only).

**Changed:**
- `edge_strip_by_vertex`: all 1. `edge_inset_by_vertex`: all 0.82. `edge_gaps`: [].
- `centre_w_by_vertex`: all 0 for one version (asserted by verify_race; removed in v3). `runs`: [].
- `kerbs`: 10, with i/j after clipping.

**New `corridors.<layout id>`:**
- `token`, `direction`, `race_side`, `closure_side`
- `zone_by_vertex`: whole | box | pin | closure | island
- `closure_y_by_vertex`: null outside closure and pin vertices
- `lane_by_vertex`: [y_lo, y_hi]
- `runs`: [{i, j, street, length_m, ends: [{vertex, y, joins: "edge_L" | "edge_R"}], island_spans, max_rate {toward, away, pin_in, pin_out}, clear_min_m, below_floor: [[i, j, reason]]}]
- `mouths`: [{host_vertex, side, policy: "sealed_race_strip" | "behind_closure"}]
- `no_route`: {seed "AC_START_0", forbidden_probes: [{vertex, y, why: pocket | island | side_street}]}. The probes are a pocket centre every 25 m where the pocket is ≥ 2 m, every island top every 25 m, and 10 m into each of the 3 connector mouths.

**`summary`:** per layout, closure and island length, clear minimum and median, pin rates and kerb clips.

---

#### 10. Authoring

**`tools/race_furniture.py`** (pure):
- Retire `chain_plans`, `SPEC_CENTRE_RUNS`, `SPEC_CHAIN_LEN_M`, the chain parts of `check_bands`, and the `nose` / free-end tapers.
- `edge_plans`: an all-ones band gives ONE closed run per side that wraps the seam, cut at street boundaries with joins. Fold trim and `match_declared_corners` are unchanged.
- New `closure_plans(pts, widths, bands, layout_id)`:
  - one `_plan_run` per run, with `lat_fn = closure_y_by_vertex` (lerped) and `start_kind = end_kind = "pin"` (full width and height, cap kept and buried);
  - then `trim_folded_rings`: expect 0 trimmed rings, and any trim raises;
  - then `densify_rings` (≤ 3.5 m, chord ≤ 0.10 m on the declared curve), then `split_plan`.
- `object_name` gains kind `close`. New `race_owner(name)` returns the token, or None.

**`tools/author_race_furniture_blend.py`:**
- Collections: `RACE` (common), `RACE_CLOSE_CW`, `RACE_CLOSE_ACW`, so Kevin can toggle a direction in Blender. The name token is authoritative, because the prep re-links objects to the scene root.
- Idempotent: it removes every `1WALL_RACE*` / `1KERB_RACE*` object and the three collections first.
- Seating is unchanged: lowest ROAD mainline sheet, ±0.4 m probe, interpolation counted.
- New counter: rings seated inside the three bridge spans, split into hit / near / interp.
- `race_authored.json` gains per object: `owner`, `kind`, `run`, and `ends[] {vertex, joins, gap_m, h, ls}`.
- It never writes `tracks/*/loop.blend` (unchanged guard).

**`tools/split_exports_blend.py`:**
- Writes `loop_main.blend` (unchanged).
- Writes `loop_race.blend`: RACE objects that are not `1WALL_RACE_CLOSE_*`.
- Writes `loop_close_<id>.blend` per race layout: `1WALL_RACE_CLOSE_<TOKEN>_*` only.
- Spawn blends are unchanged.
- The manifest records a problem (exit 1) for:
  - an undeclared token;
  - a KBAR object;
  - an empty closure blend;
  - a closure object in `loop_race.blend`;
  - (race ∪ closures) ≠ all RACE objects;
  - an orphan material.

**`tools/plot_race_furniture.py`:** writes `data/race_plots/<id>/`: an overview, the 5 corners, Del Cerro, the I-8 end, the 10 noses and the 8 pins. `--planned` works before Blender. The draft renderer is `SCR/work/plot_corridor.py` / `SCR/spec/plot_corridor.py`.

---

#### 11. Gates

##### 11.1 Three invariants, four stages

| Invariant | Plan (`barrier_bands`) | Authored (`verify_race`) | kn5 | Built (gate OBJ) |
|---|---|---|---|---|
| **CONTAINED:** from AC_START_0, nothing outside the corridor is reachable | planned no_route = 0 | D, J, L | owner + ini (g) | **no_route = 0**, `barrier_missing` = 0 |
| **CLEAR:** the lane is open end to end | closure never in BOX/WHOLE; floors | C′, F, G | – | `obstruction_stations` = 0; no_route lap complete |
| **OWNED:** each layout loads only its own closure | tokens declared | K | `check_race_kn5` roles, verify_kn5 (f)/(g) | per-layout gate OBJ |

##### 11.2 Plan-time self-gates: `tools/barrier_bands.py` v2 (exit 1)

1. **Zones.** WHOLE ∪ BOX ∪ runs covers every vertex exactly once. Each box contains its PC..PT. WHOLE contains the PC..PT of the seam and the hairpin. The runs equal the pinned `closure_runs`.
2. **Pins.** Each pin's y equals the far strip centre within 0.01 m. The pin vertex has `edge_strip` = 1 and is not in a removed set.
3. **Rates.** As in §4, outside pin zones. Pin-zone rates match the forced rates. Anything steeper than 1:3 FAILS.
4. **Clear width.**
   - ≥ 6.5 m everywhere (INVENTED).
   - ≥ 10.86 m except on island, pin-zone and convergence vertices, each listed in `below_floor` with its reason.
   - Pocket ≥ 2.0 m wherever a closure stands outside pin zones and islands.
5. **Islands.** The closure footprint is ≥ 0.15 m off the AUTHORED island outline at every vertex, and on the race side at all 10 tips.
6. **Shape.** 0 backward steps. Plan radius ≥ 20 m.
7. **Mouths.** Each mouth matches its declared policy.
8. **Spawns.** Every grid, pit and hotlap car (half-width 0.95) is ≥ 0.30 m off every strip and closure face.
9. **Kerbs.** Exactly 10, each ≥ 0.05 m off every closure footprint.
10. **Strips.** `edge_strip_by_vertex` all 1.
11. **Alvarado width.** The re-measure holds (see §9.1).
12. **Planned no_route** per layout.
    - Footprints: both strip polylines (with the trimmed corners) plus this layout's closure, each ±0.335.
    - Pass: 0 leaks and the lap complete.
    - This is the declaration checking its own topology. It is not an L5 gate.

##### 11.3 `tools/verify_race.py` (after authoring, before any kn5; exit 1)

Runs on the common set and on each layout.

| Check | Rule |
|---|---|
| A, B | as today (≤ 900 rings, < 60k positions, < 65,535 render verts per object) |
| **C′ closure** | Every ring within 0.05 m of the declared curve. One object chain per run, joined on shared rings. First and last ring at the pin vertex within 0.05 m of the far strip line, with `h == BARRIER_H` and `ls == 1`. No ring in BOX or WHOLE. |
| **D strips** | Every vertex covered on both sides except the removed sets, **bridge spans included**. This inverts today's "no ring inside a span". |
| E | the 10 declared kerbs with their clipped i/j |
| F, G | spawn clearance; lamps checked against closure footprints too (nearest measured 1.48 m, at v1523) |
| H, I | extended to closures |
| **J** | Zero free ends in the RACE set. Every edge end is a join; every closure end is a pin with gap ≤ 0.05 m. |
| **K** | Each closure token is declared and its rings lie on that layout's curve. Nothing crosses collections. |
| **L** | 0 interpolated rings inside the three bridge spans |
| **M** | mouths per policy, re-measured on the authored rings |
| **N** | no `1WALL_race_kbar_*`; `centre_w_by_vertex` all 0 |

##### 11.4 kn5 content

**`tools/check_race_kn5.py <json> --role common`** FAILs if:
- any mesh is not RACE;
- any mesh is CLOSE or KBAR;
- there is no edge mesh;
- the count is not exactly 10 `1KERB_RACE_*`;
- any texture is outside the race rows;
- any `AC_*` node is present.

**`--role closure --owner <t>`** FAILs unless:
- every mesh is `1WALL_RACE_CLOSE_<T>_*`;
- there is at least one;
- there are no kerbs or edges;
- the race textures are the only ones and there is no `AC_*` node.

Both roles WARN above 20 MB.

**`scripts/ac/verify_kn5.py`:**
- **(f)** checks the common kn5 as today, plus per race layout `<slug>_closure_<id>.kn5`: it exists; it carries this layout's token only; it has RACE-only materials; and no 1-prefixed name is duplicated across road + common + closure.
- **New (g):**
  - each race ini lists exactly [road, `_race`, `_closure_<id>`, `__<id>`];
  - the street ini lists exactly [road, `__street`];
  - no ini lists another layout's closure kn5.
- **(d)** for race layouts: START and PIT positions lie inside `lane_by_vertex`, ≥ 0.30 m from each face, car half-width included. This replaces "right of travel" and `CHAIN_CLEAR_M` (retired).

##### 11.5 Built gates, per race layout

**Gate OBJ.** Build it with:

```
kn5_to_gate_obj <proj> --kn5 <slug>.kn5 --kn5 <slug>_race.kn5 --kn5 <slug>_closure_<id>.kn5 --out data/track.<id>.obj
```

The name uses a dot because the prep merges `data/track_*.obj`. `track.race.obj` is retired.

**`scripts/geometry/median_zone.py`:**
- `MedianZone.load(project, layout=None)`. With a layout, it uses both edge bands (full lap, trimmed corners) plus that layout's closure band, continuous between consecutive declared vertices.
- New `closure_at(i)` and `lane_r(i) -> (lo, hi)`, right of the zone's own travel.
- Without a layout it is byte-identical to today's street zone.

**`drive_test --layout <id>`:**
- The lane is `lane_r`, lerped at each station, with `DIVIDER_CLEAR_M` 0.4 inside each face. Box and WHOLE zones are full width, with the 6.3 m disc cap kept.
- Funnels and island faces are outside the lane by declaration, so anything of them inside the lane is an obstruction.
- `barrier_missing` keys `edge_L`, `edge_R` (all 13.5 km, bridges included) and `closure` at its lateral. It keeps the 4.04 m continuity rule and the seam wrap.

**`audit_mesh --race --layout <id> --obj track.<id>.obj --out audit.<id>.json`:**
- D is exempt only on this layout's bands.
- Acceptance: D / K / I / F no higher than today's `audit.race.json` (512 / 154 / 145 / 15). These are measured, and identical to the street `audit.json`.
- The wall-crossing check shows 0 race-strip × `1WALL_guard` crossings.

**New `scripts/geometry/no_route.py`** (pure Python). CLI: `python -m scripts.geometry.no_route <proj> --layout <id> [--planned] [--obj ...]`. It writes `data/no_route.<id>.json` and exits 1 on any leak or block.

1. **Domain.** 0.25 m cells within `w/2 + 25 m` of `gate_centerline.json` (the built line, L5).
   - Every domain cell is treated as drivable: AC lets a car onto 1GRASS and 1KERB, so a gap in the walls is a door whatever lies beyond it.
   - Leaving the domain counts as an escape.
   - Storage: lazily created 64 m tiles, target < 300 MB. The flat prototype used about 1.1 GB.
2. **Walls.**
   - Rasterise every `1WALL*` triangle (edges sampled every 0.1 m, plus interiors), keeping per cell the min and max height relative to the local deck (deck = nearest gate-centreline y + 0.10).
   - A cell is a WALL only if its union spans **[deck + 0.20, deck + 0.90]**. This is deliberately strict: the island beam (0.63-0.93 m) alone must NOT count, or a missing island closure would pass. Beam posts become isolated dots, not a seal.
   - Dilate walls by PROBE_R 0.5 m, so gaps under 1.0 m close; 1.0-1.9 m gaps still read as doors (conservative).
   - `--planned` uses the declared polylines ±0.335 instead of the OBJ.
3. **Seed.** `AC_START_0` from `dummies_<id>.json`. It must be a free cell.
4. **Fill.** 4-connected scanline fill.
5. **Allowed.** Per-segment quads between the `lane_by_vertex` faces, plus the BOX and WHOLE full-road polygons, dilated by TOL 0.75 m.
6. **FAIL** on any reached cell outside the allowed region. Door clusters are reported {v0, v1, side, lateral, cells, gap estimate}, each classed opposite / island / side_street / off_road / escaped.
7. **Forbidden probes** from the declaration must be unreached.
8. **Lap complete.** The lane-centre cell at every vertex, and every `AC_START_n` / `AC_PIT_n`, must be reached. Otherwise FAIL "corridor blocked at v…".

**Teeth.** These are the prototype results the gate must reproduce:
- Today's `track.race.obj` FAILS with doors at v608-620, v855-864, v887-903, v4443-4454 and v4474-4492, at the chain ends and at the noses: 51 clusters.
- The planned v2 passes for both layouts (138.8k / 138.4k m², 25-29 s).
- v2 with today's bridge gaps put back FAILS with 27 clusters at exactly those span ends.

**Limits (stated plainly).**
- The gate works in 2D with a height band. A low car passing under a beam is excluded by the span rule, not modelled.
- It assumes no terrain ramp lifts a car over a 1.2 m wall; none exists beside a race strip today.

##### 11.6 Install rule

`RACE_RED` in `ship_sd.sh` gains two conditions. Today it is `barrier_missing > 0`, or `obstruction_stations > 0`, or drive_test not run. It now also turns red on:
- `no_route` leaks > 0, a blocked lap, or a missing `no_route.<id>.json`;
- `check_race_kn5` / verify_kn5 (g) failing.

A red race layout is never installed, `--force-install` or not.

Note: today every layout's `drive_test.*.json` already has `fail: true` from pre-existing counters (soft tops, floating furniture, ledges). `RACE_RED` keys on the counters listed above, not on `fail`.

**Street regression:** the street layout's `drive_test.street.json` must equal the pre-change build (soft_top 82, floating 391, severe 0, excursion_drops 101), and so must `audit.json` (D 512, K 154, I 145, F 15). The road kn5 and the street ini do not change.

##### 11.7 `fleet/GATES-CHANGELOG.md`, in the same commit

- **New:** `no_route`; corridor lanes in drive_test, median_zone and audit; verify_race C′/D/J/K/L/M/N; verify_kn5 (d)/(f)/(g); check_race_kn5 roles; the barrier_bands v2 self-gates.
- **Retired:** `BRIDGE_CLEAR_M` 9 m; "edge gaps == bridge spans"; `CHAIN_CLEAR_M`; the 17 m wide threshold; the nose butt joint.
- **INVENTED:** PROBE_R 0.5, TOL 0.75, wall span 0.20-0.90, domain +25 m, tile 64 m, pocket 2.0, hard minimum 6.5, band −0.5/+1.5, rates 1:12 / 1:6 / 1:10, steepest pin 1:3, pin zone 120 m, base ±60 m / σ 20, island envelope 30 m, radius floor 20 m, box pad 2, join 0.05.
- **MEASURED:** 11.36, 0.82, 0.485, 0.335, NOSE_HALF 0.25 / 3.

---

#### 12. AI: `scripts/ac/write_ai_line.py --layout race_cw|race_acw`

- **Lane.** For race layouts the lane comes from `corridors.<id>.lane_by_vertex`, converted to right of travel; lo may be negative past the centreline. The target is the lane centre: about 2.0 m right of the centreline on a 17 m road, and 0 on Alvarado, the deck and in boxes.
- **Transitions.** `ramp_offsets` cosine tapers of ≥ 40 m carry the line through funnels and convergences.
- **Boxes.**
  - The lane is the full road in a box, so `corner_approach` / `fillet_corners` see the whole intersection.
  - Turn in from the corridor's outside edge and apex at X + 0.335 + clearance. For acw that is its far strip, which bounds it only inside the box.
  - Exit wide inside the box.
  - `RADIUS_FLOOR_M` 12 stays as the floor. The fillet targets the largest radius that keeps `FILLET_COMFORT_CLEAR_M` off every face.
- **Estimated radii** (approximate, not a gate):

| Corner | race_cw (m), today → open box | race_acw (m), today → open box |
|---|---|---|
| v1514 | 20.6 → ~34 | 32.5 → ~52 |
| v2319 | 14.2 → ~35 | 25.2 → ~52 |
| v3297 | 28.1 → ~39 | none → ~55 |

- **Hard refusals:**
  - a point < 0.6 m from any corridor face, including funnels and island faces;
  - a point beyond a closure or across a mouth line;
  - plus today's backward-step, self-crossing, turn and radius checks.
- sideLeft / sideRight are the distances to the lane faces.
- These are still GENERATED drafts: ledger 0023 stays open, no tier is claimed, and `pit_lane.ai` remains a copy. The street AI is unchanged.

#### 13. Grids, pits, timing

**Unchanged.** Both grids are on Alvarado (WHOLE), whose furniture is unchanged in shape.
- race_cw: pole v291, 3.25 m right of travel, columns 2.25 / 4.25, line v300, pits v274→257.
- race_acw: pole v310, mirror, pits v327→344.
- Outer column 0.48 m off the strip face (floor 0.30). The nearest closure is about 1.3 km away.
- Sectors v1803 and v3310 are unchanged. The timing planes span the full road; they are not physical.

**Later option, no decision needed now:** centre both grids (`start.offset_right_m: 0`, columns ±1.75, new `start.grid_stagger_m`), giving 2.98 m clear per side.

#### 14. `tools/ship_sd.sh`, in order

1. `barrier_bands.py` v2: the corridor solve, the self-gates and the planned no_route (exit 1 on failure).
2. `layout_dummies.py`: unchanged.
3. Author: three collections.
4. `verify_race.py`: common plus each layout.
5. `plot_race_furniture.py`.
6. Prep: unchanged.
7. Split: `loop_race.blend` + `loop_close_<id>.blend` ×2 + spawn ×3. `--dry-run` stops here and echoes the new names.
8. Export:
   - the road kn5;
   - `loop_race.blend` → `${SLUG}_race.kn5`, then `inspect_kn5` → `data/race_kn5.json`, then `check_race_kn5 --role common`;
   - for each `$RACE_IDS`: `loop_close_$lid.blend` → `${SLUG}_closure_$lid.kn5`, then `inspect_kn5` → `data/closure_$lid.kn5.json`, then `check_race_kn5 --role closure --owner <token>`.
9. Spawn kn5 ×3; AI per layout; `verify_kn5` (d)/(f)/(g).
10. `track_folder`:
    - per-layout extras are [race, closure_<id>];
    - a missing closure kn5 is a HARD error;
    - `pack_release.strip_race_layouts` also strips `${SLUG}_closure_*.kn5`.
11. `make_map`, `make_treefx`.
12. Gates:
    - street: unchanged;
    - per race id: `kn5_to_gate_obj` (3 kn5s) → `track.$lid.obj` → `drive_test --layout` → `audit_mesh --race --layout` → `no_route --layout`.
13. `RACE_RED` (§11.6).
14. Sync back:
    - adds `no_route.<id>.json`, `audit.<id>.json`, `closure_<id>.kn5.json` and `race_plots/<id>/`;
    - drops `audit.race.json`;
    - never syncs `track.<id>.obj` (about 78 MB each).
15. Install as today; the previous build is parked in `D:/k10-track-archive/<stamp>/`.

Runtime: about +3 min per ship.

#### 15. Tests (`tests/run_tests.py`)

| File | Pins |
|---|---|
| `tests/geometry/test_no_route.py` (new) | Synthetic L-corridors: sealed passes. A 1.5 m door FAILS at the right vertex and side. A 0.8 m crack passes. A beam-only island (0.63-0.93 m) FAILS. An unpinned closure end FAILS. A wall across the lane gives "blocked at v". A seed in a wall is an error. A reverse layout works. A reached forbidden probe FAILS. An escape is classed "escaped". |
| `tests/tools/test_race_corridor.py` (new) | The prototype fixture. SD runs, pins ±0.01, §3 minima ±0.05, rates, radius, mirror. Synthetic: 13 m gives whole street; 17 m gives y ±4.015 and clear 11.36; an island gives face + 0.485; a box gives pins; a flare shorter than 120 m does not move the closure. |
| `tests/tools/test_barrier_bands.py` | Each v2 self-gate fires on a crafted defect: closure in a box, pin off the line, a 1:2 rate, a far mouth not behind the closure, a kerb on a closure, a missing strip ring (planned leak), `centre_runs` present, a perturbed Alvarado width. |
| `tests/tools/test_race_furniture.py` | Closed edge loops with no free ends; closure names carry the token; pin rings are full height; shared split rings; closed solid and outward normals on closures. |
| `tests/tools/test_verify_race.py` | Each of C′ / J / K / L / M / N with a passing and a failing case. |
| `check_race_kn5`, `tests/ac/test_kn5_gates.py` | Roles and owner; (g): another layout's closure in the ini FAILS, a missing closure kn5 FAILS; (d) corridor check. |
| `test_drive_test_layouts.py`, `test_median_zone_kinds.py` | Lane from the declaration; a gap in the closure gives `barrier_missing`; the street zone is byte-identical. |
| `tests/ac/test_ai_line_geometry.py` | A point 0.5 m from a closure face is refused. |
| `test_ship_sd_chain.py`, `test_pack_release_cc0.py` | New names and steps; no `track.race.obj`; `RACE_RED` includes no_route; closure kn5s are stripped from CC0. |

#### 16. Order of work

Each phase ends green on `PYTHONUTF8=1 python tests/run_tests.py`. Until P7, Blender runs only on scratch copies, with `--python-exit-code 1`.

- **P0. Record.**
  - File ledger 0049: the brief verbatim, the answers, this spec, and the honest note that today's installed race layouts are not sealed.
  - Dump the prototype fixture (§4).
  - Pin the street baseline (§11.6).
- **P1. Gate first.** `no_route.py` + tests. Run it on today's `track.race.obj` and confirm the 51-cluster FAIL, which proves it has teeth.
- **P2. Declaration** (pure Python). `race_corridor.py`, barrier_bands v2, the config, the planned no_route and plots. Exit: 0 planned leaks for both layouts, and the §3 tables reproduced. Send Kevin the per-layout plots before any Blender work.
- **P3. Authoring.** race_furniture, the author tool, verify_race v2, on a scratch copy of loop.blend.
- **P4. Packaging.** Split, exports, check_race_kn5, verify_kn5, track_folder, pack_release. Exit: a scratch `--dry-run` has problems [], then a full scratch export.
- **P5. Built gates.** median_zone, drive_test, audit and no_route per layout; `RACE_RED`.
- **P6. AI.** Corridor lanes, box approach, refusals.
- **P7. Full scratch rehearsal.** `SHIP_PROJ=<scratch> bash tools/ship_sd.sh`. Exit:
  - both race layouts: no_route 0 / 0 with the lap complete, `barrier_missing` 0, `obstruction_stations` 0, audit at or below baseline;
  - street gates identical.
- **P8. Docs, ship, drive.**
  - Rewrite `docs/RACE-FURNITURE.md` (§1, §3, §5, §9, §10) and add GATES-CHANGELOG entries.
  - Real ship and install.
  - Kevin's drive (`fleet/templates/DRIVE-TEST-REPORT.md`). Drive items: the cw Navajo exit funnel v1521; acw v2311 / v1506; the 6.86 m island carriageways; the 17 m roads; every box.
  - No tier is claimed before that drive.

**Size:** about 2,400 lines plus docs, over 2-3 sessions.

#### 17. Tune after the drive, not before

Each of these is one knob, changed only after Kevin has driven the build:

| Knob | Setting | Alternative |
|---|---|---|
| width on 17 m roads | `clear_width_m` 11.36 | own side only, about 7.7 m with the wall on the centre line |
| median width | `island_mode` pavement | island_top, +0.97 m, after the §5 proofs |
| steep exit funnels | as solved | start the funnel inside the box edge, which gives a gentler wall and a smaller box |
| grid | as today | centred grid (§13) |

#### Appendix: where the three candidate specs disagreed, and what this spec takes

| Topic | Options | Taken | Why |
|---|---|---|---|
| Island placement | island top (7.83); strip face on the island curb (7.68); pavement (6.86) | pavement, island top as a post-drive option | Kevin's "leading up to medians but not on them"; same seating as the curb strips; the deck-height measurements disagree; no beam clash at Navajo-2 |
| Packaging | two self-contained kn5s; common + per-direction closure | common `_race.kn5` + `_closure_<id>.kn5` | smallest diff; common identical by construction; smaller package |
| Far strip | only in WHOLE and boxes, with joins; full lap | full lap, closed loops | no far-strip ends anywhere; pockets sealed twice; it is today's strip minus the gaps |
| Box gating | square cross barriers; funnels onto the far strip | funnels | no head-on exit walls, no acw pockets |
| Box extent | PC−3..PT+3; junction cuts; PC−2..PT+2 | PC−2..PT+2 | contains every cut; pins land on real strip rings; it is the solved line |
| Kerbs | per-owner parts plus exit and pocket kerbs; common and clipped | common, clipped | one kerb set, no ownership splitting; exit kerbs can come later |
| no_route wall rule | overlap [0.15, 1.0]; drop floating objects; span [0.20, 0.90] | span [0.20, 0.90] | a beam-only island must fail the gate |
| I-8 end / hairpin start | v4451 / v4453 / v4454; v777 / v782 / v797 | v4454 / v777 | the solved line's pins |

---

## Drive verdict 1 (2026-10-12)

Kevin, after driving the installed build (v0.17.1: the race corridors plus the mouth weld), verbatim from dictation:

> "is tracked with and race track layouts are incredible"

Read as **"the track width and race track layouts are incredible"** (voice dictation; "tracked with" ≈ "track
width"). What it confirms, in his seat: the per-direction corridor at Alvarado's width (11.36 m clear, wall face to
wall face, spec §1), the whole-street Alvarado + I-8 deck, the open boxes at the corners the race turns at, the
closures on the other side, and the three-layout split (0047). **Consequences:** the post-drive tuning knobs
("Tune after the drive, not before": `clear_width_m`, `island_mode`, a centred grid) stay as built; the corridor
model is the one the Lariat's race version (0048 D3 a, Drive 3) adapts.

**Not covered by the verdict** (no comment either way, so still open in
`tracks/san-diego-lake-murray/drive-reports/2026-10-1x-race-corridors.md`): the steep exit funnels (cw v1521,
acw v2311 / v1506, the acw 1:10 funnel off the I-8 deck), a wall hit at speed (the K-rail foot), closure / curb-strip
flicker, the race_acw fold-fan steps the mouth weld named (Navajo/Jackson up to 0.40 m), an AI race with 7
opponents, load time and FPS. Anything he reports there becomes its own entry.

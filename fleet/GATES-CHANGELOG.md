# Gates changelog

Every change to a gate threshold, bypass, exclusion or wiring gets an entry here **in the same
commit**: what changed, the measurement that justifies it, and how it was proven. Silent weakening
is how a gate goes vacuous while still printing green — the failure REALISM §1 was written about.
Append-only, newest first.

Gate *results* don't belong here; they live with the built artifact (`data/drive_test.json`,
`data/audit.json`) and in the ledger entry that provoked them.

**The standing rule:** a threshold calibrated against our own output is not a threshold, it is a
mirror. REALISM §3 and §5 exist to replace these numbers with envelopes measured off tracks that
feel right (`fleet/reference/MEASURED.md`). Until that lands, the ⚠ items below are known-invented.

---

## 2026-08-10 — Baseline inventory (no changes; recording current state)

Re-derived directly from the engine at `v0.66.3`+, not inherited. The v2-reboot draft that seeded
this file cited line numbers from prodrive-ac-builder `3e1aa52`; all but one had moved, so every
row below was re-read from the current source. Nothing here is endorsed by being listed.

### Bypass environment variables — both still live

| Var | Where | Effect | Flag |
|---|---|---|---|
| `GATE_EXCURSIONS_ADVISORY=1` | [drive_test.py:718](../scripts/geometry/drive_test.py:718) | Unguarded off-road drops report but don't gate. Comment says "NEVER set for a full (non-rc) release" | ⚠ remove once the construction selector lands |
| `GATE_CONTACT_ADVISORY=1` | [kn5_ground_check.py:648](../scripts/ac/kn5_ground_check.py:648) | Overrides the measured road-contact fraction | ⚠ remove |

A bypass that outlives the reason it was added is indistinguishable from a lowered bar. Both carry
a named owner in their comment; neither has a removal date.

### `drive_test` — the seat-time proxy

| Threshold | Value | Flag |
|---|---|---|
| bump step | 2.5 cm ([:39](../scripts/geometry/drive_test.py:39)) | |
| severe step | 6.0 cm ([:40](../scripts/geometry/drive_test.py:40)), gate at **>12/km** ([:728](../scripts/geometry/drive_test.py:728)) | ⚠ invented |
| bumps/km | **75 tarmac / 150 gravel** ([:713](../scripts/geometry/drive_test.py:713)) | ⚠ **self-referential** — the 75 line is calibrated against Sand Creek's own output (~19/km), and the code says so |
| excursion drops | >1 per km fails ([:724](../scripts/geometry/drive_test.py:724)) | ⚠ a car-destroyer allowance |
| obstructions / undrivable corners / floating furniture / soft-top-in-lane / daylight gaps | gate at 0 | correct shape — count, not tolerance |
| cornering model | 1.3 lat-g, 30–260 km/h, calibrated at 100 km/h ([:49–52](../scripts/geometry/drive_test.py:49)) | hand-calibrated |

The gravel split (150/km) is the one threshold here with a real argument behind it: Dragon Tail
measures ~114/km straight off 1 m lidar of the actual road while its severe rate and replication
both sit well inside their limits — holding a rally stage to the tarmac line would mean smoothing
it until it drove like a circuit. That reasoning is in the source; it is the model the other
numbers should follow.

**Open against this gate:** ledger 0031 — Bathurst builds to 2.38 m RMS against the Kunos scan and
still fails at 94.4 bumps/km. Two hypotheses (elevation source, profile smoothing) are dead with
evidence. The limit itself is a live suspect precisely because of the ⚠ above.

### `audit_mesh`

| Threshold | Value | Flag |
|---|---|---|
| grass poke above road | 0.10 m within 5.0 m ([:29–30](../scripts/geometry/audit_mesh.py:29)) | |
| pier "standing in the road" | within 3.5 m xz, 1.5–45 m below deck ([:31–32](../scripts/geometry/audit_mesh.py:31)) | |
| wall float | a 0.6 m column floats only if no supported column within reach ([:338–362](../scripts/geometry/audit_mesh.py:338)) | neighbour-forgiveness — bought by a real false positive (a seated wooden fence read as +1.6 m floating because min-y was the rail) |

Historical note: this repo's k10-colorado fork grepped a `KERB` prefix against groups named
`1KERB_*` for months, so the curb-flush check reported "0 of 0" — a gate that passes by finding
nothing is worse than no gate. Fixed by the un-forking (`registry.json`).

### `verify_kn5`

| Threshold | Value | Flag |
|---|---|---|
| vertex cap | 65,535/mesh | AC hard limit |
| drivable faces pointing up | ≥90% ([:33](../scripts/ac/verify_kn5.py:33)) | |
| pit/start box to road | ≤13.5 m xz, ≤1.0 m dy ([:34–37](../scripts/ac/verify_kn5.py:34)) | |
| terrain pokes tolerated | **20** ([:40](../scripts/ac/verify_kn5.py:40)) | ⚠ the one line the draft cited that hasn't moved — still a nonzero hole allowance in a shipped kn5 |

### `kn5_ground_check`

| Threshold | Value | Flag |
|---|---|---|
| import/export float tolerance | 0.08 m ([:35](../scripts/ac/kn5_ground_check.py:35)) | |
| sampling | every 23rd vert per bucket ([:36](../scripts/ac/kn5_ground_check.py:36)) | sampled, not exhaustive |
| deck vs mountain | 0.05 m, fraction over it must be **0** ([:37–40](../scripts/ac/kn5_ground_check.py:37)) | correct shape |
| p95 gate | 0.10 m ([:51](../scripts/ac/kn5_ground_check.py:51)) | measured — set from imi/second-creek/pueblo/high-plains p95s recorded in the source |
| bridge-span exemption | span half-length + **170 m** of approach ([:264](../scripts/ac/kn5_ground_check.py:264)) | review — a large blanket, and 0008 was a phantom gate born of exactly this kind of carve-out |

### Wiring

`build.sh` runs all four gates hard under `set -euo pipefail`. Stage-resume (`build.sh <dir> mesh`)
skips gates bound to earlier stages — a resumed build is not a gated build. `build_network.sh` and
`build_loop.sh` are separate paths and do not run the full set; REALISM §4 folds them into one
gated export path (`scripts/blender/export.py`, R3, not started).

## 2026-10-08 — median island awareness (ledger 0037)

**Change.** `scripts/geometry/median_zone.py` (new) reads `data/median_bands.json` — the per-vertex
island width `tools/median_envelope.py` writes for divided roads — and the gates consult it:

| Gate | Before | After |
|---|---|---|
| audit **D** walls-on-road | every median-barrier vert counted (25,896 on Lake Murray r2) | verts on the declared island band exempt |
| audit **K** kerb-in-carriageway | island curb counted (4,213 incl. ~3,100 island) | island band exempt — K measures *intrusions* again |
| audit **I** sidewalk-isolating | island curb counted (pavement on both sides, by design) | island band exempt |
| drive_test wheel paths | centre pair swept over the island (curb = "severe step", deck = "soft top in lane") | on island stations the ten paths move into the driven lane; step/kink memory resets at island boundaries |
| drive_test obstruction scan | 6.3 m disc on the centreline — the barrier/planting at every island station (2,670 + 2,589 hits) | on island stations, and within 2 stations of one (the disc otherwise reaches the nose), the scan covers the driven lane instead |

**Why it is not a bypass.** The exemption is a *band* (island half-width + 0.6 m, laterally,
±2 m along), only where the track declares an island, only for the three checks whose invariant
("nothing that is not road stands on the road") the island legitimately breaks. The island's own
correctness is still gated: the kn5 rename pass enforces its curb is `1KERB` (collidable) and its
deck `1GRASS`; `verify_kn5` still checks the spawn and face-up; F (curb flush) is untouched. A
track that declares no island gets no exemption (`median_bands.json` absent → zone `None`).

**Measured basis.** rt_macau / union_island / ks_black_cat_county dissections
(docs/JUNCTIONS.md): islands and traffic islands stand ON continuous pavement in every pro track
measured; a gate that forbids that forbids the professional pattern.

**Still owed (0036 / C2).** K becomes part of the *hard* exit total once the connector-mouth
sidewalk sweeps are gapped — until then K would fail every street track on inherited defects.

### Same day — gate centreline frame (a wrong-frame gate, found while measuring the above)

`drive_test` prefers `data/finished_centerline.json` (the line the ribbon was swept along). On the
loop path that file is written by `build_kn5_loop` **in the kn5 frame (z mirrored)** for
`kn5_ground_check`, while `kn5_to_gate_obj` un-mirrors the kn5 into the **engine frame** for
`drive_test`/`audit_mesh`. Result on Lake Murray r2: the drive test swept a z-mirrored path over a
local-frame OBJ — "14 obstructed stations", a 0.4 m step at the median run end, island soft-tops
— **all from the wrong side of the map**; the correct-frame run finds different, real defects
(a 1.5 m step and palm trunks at the College/I-8 approach). The median-zone exemption inherited
the same mismatch and exempted nothing (D 25,896 → 25,812).

Fix: `kn5_to_gate_obj` now also writes `data/gate_centerline.json` (finished_centerline with z
un-mirrored, i.e. the OBJ's frame) and `drive_test` + `median_zone` prefer it. Nothing else
changes: `finished_centerline.json` stays in the kn5 frame for its kn5-reading consumers. A gate
walking a line in a different frame than its mesh is the phantom-gate class (0008); this entry
exists so the next person who sees a "clean" OBJ-gate run on a Blender-first track asks which
frame it walked.

## 2026-10-10 — GrassFX occluder allow-list: `BUILDINGS` → `BUILDING` prefix, `HOUSE` added (ledger 0045)

`scripts/ac/ext_config.py` `OCCLUDE_PREFIXES` (airoso + the engine-july build-of-record copy,
md5-identical) is the crash guard: a far-field or oversized mesh enrolled as a GrassFX occluder
explodes the occlusion volume at session load and freezes the whole PC (shipped v0.12.1–v0.12.6).
It is an allow-list of near-field, ground-seated solids and stays one.

| | Before | After |
|---|---|---|
| building prefix | `BUILDINGS` (Sand Creek's plural) — Lake Murray V3's singular `BUILDING` mesh **not** matched, blades through every building pad | `BUILDING` — a prefix, so `BUILDINGS`, `BUILDING_a..` and `BUILDING` all match |
| houses | no prefix — V3's `HOUSE` mesh skipped | `HOUSE` added (`WAREHOUSE` does not start with it; listed separately as before) |

**Measured basis** (gate OBJ `k10-sd-v021/project/data/track.obj`, 2026-10-10): `BUILDING` 1,637
verts, X −2174..452 / Z −1591..1774; `HOUSE` 10,335 verts, X −2078..2532 / Z −1740..1787 — both
inside the 1ROAD lap extent. The V3 occluder envelope grows from 4,698 × 3,413 m / 140,338 verts
(16.0 km²) to 4,805 × 3,527 m / ~152k verts (16.9 km²): still exactly the lap, nothing elevated,
nothing far-field, against the v0.12.x failure's 24,000 × 1,450 m MOUNTAINS backdrop. Every dry-track
author in the census lists building floors/walls (nohesi `?Building?`, Targa, PCH).

**Why not a per-track add list.** The add list is the crash class; the only way to enrol a mesh
stays the prefix table plus `tests/ac/test_ext_config_occluders.py` (which now pins `BUILDING`,
`HOUSE` in and `LIGHTPOST_0` out). Review discipline unchanged: every ship diff shows the
`OCCLUDING_MESHES` line, and a future far-field mesh named `HOUSE*` / `BUILDING*` would be
auto-enrolled — the same class of review `BUILDINGS` already carried.

Same commit: the `[GRASS_FX]` writer (`scripts/environment/treefx.py`) moves to the grammar every
shipped CSP config uses and rejects unknown/retired keys; `lighting.grassfx = {"enabled": false, …}`
takes the OFF branch. Not a gate change — recorded in ledger 0045 and `docs/TREEFX-FORMAT.md`.

## 2026-10-10 — `verify_signs` ship gate (ledger 0044)

**Change.** A new gate, `tools/verify_signs.py`, runs in `tools/ship_sd.sh` right after the W1-6
authoring step (after the lamps step, inside the `SKIP_BLEND` block) and before the prep/export. It
reads `data/signs.local.json` — the record `tools/place_signs.py` writes and
`tools/author_signs_blend.py` extends with the Blender measurements — and exits 1 on any FAIL;
under the script's `set -euo pipefail` that exit propagates through `| tail -3` and **aborts the
ship before a kn5 exists**. Per sign:

| Check | Threshold | Flag |
|---|---|---|
| (a) ray strike | the failed-to-turn ray from A along t passes within ±0.61 m of the plate centre (half the 48 in plate), tested at the **un-slid** post point base − slid_m·u (the lamp/plant slide along the curb, ≤ 1.0 m, is the only lateral deviation the rule allows; a paired post adds half its pair split) | the sign stands where a car that did not turn would hit it (MUTCD 2C.09) |
| (b) facing | \|angle(f, −t)\| ≤ 1° — the plate looks straight back down the approach heading | |
| (c) built-edge clearance | mainline 1.3–3.0 m, connectors ≥ 1.0 m, **measured two ways and both must pass**: (1) the minimum distance from the base to the built outside-edge polyline the authoring pass recorded (`built.outside_edge_xz`, ROAD-top probes per station); (2) with `--blend`, an independent BVH top-surface scan inside Blender (ROAD vs CURB/SIDEWALK/TERRAIN, 5° polar scan at 0.25 m steps, bisected; `tools/signs_mesh.py`, `data/signs_measured.json`). Nothing self-reported is read. | ⚠ tautological in the first dry run — see below |
| (d) outside of turn | cross(t_local, C − P) > 0 for D < 0 — the side is a geometric test, never a convention | |
| (e) / (f) heights | plate bottom = y_base + 2.13 ± 0.05 m; post base = y_base − 0.30 ± 0.05 m (n/a on an analytic run with no Blender section) | |
| (g) obstacle disc | no SIGN* vertex inside drive_test's min(lane_half, 6) + 0.3 m disc of **any** centreline, the post's own side street included (4.9 m on a 10 m street) — recomputed by the verifier from the centreline/connector json over the plate footprint (base ± 0.61 m along every plate's right vector); and the base is off pavement (measured clearance > 0, scan `on_road` false). Connector posts can now trip it; the authoring pass marches a post along its ray until both the clearance and the disc hold and SKIPS a corner that cannot satisfy both within 6 m of the built curb | extended this round: connectors were "measured for the record" only |
| (h) one per approach | exactly one record per id (+1 under the hairpin clause), none at a `signs.json` `skip` id, no `-fwd`/`-rev` twin of a paired post | |
| (i) spacing | no two posts' bases closer than 2.0 m, across approaches and ribbons — not only the hairpin clause's ≥ 12 m. A two-way corner whose two posts would stand < 2.0 m apart on the built mesh is emitted as ONE post carrying both plates (`place_signs.merge_pairs`) | added this round (absent at `ac8975d`) |
| (j) expect_arrow | the placed arrow (left / right) equals `signs.json`'s per-corner `expect_arrow` where one is declared; the placement itself skips such a corner with a logged reason rather than relocating it | added this round (the key existed in `signs.json`; nothing read it) |
| Blender normals | `blender.normal_mismatches` = 0 — every plate, arrow and post polygon faces as emitted | |
| harness | every `"$BL" --background --python` call in `tools/ship_sd.sh` carries `--python-exit-code 1`; `author_signs_blend.py` unlinks `signs.local.json` / `signs_preview.svg` / `signs_measured.json` at start, so a Python exception inside Blender can neither exit 0 nor leave the previous run's record for the gate to pass | added this round |

**Measured basis.** The thresholds are the sign's own dimensions (0.61 m = half of 48 in), the
MUTCD mounting rule (2.13 m = 7 ft over a walk, 2A.15), the walk section the loop is built with
(curb face 0.08 + walk 1.8 / 1.5 − 0.25 set-back = 1.63 / 1.33 m;
`scripts-v021/blender/build_loop_blend.py:658/677`) and drive_test's existing disc. None of them is
calibrated against our own output.

**⚠ Check (c) was tautological in the first dry run — fixed this round.**
`author_signs_blend.mesh_sign_point` wrote `mesh_clear_m` as `(curb_face + walk_w) × frac`, i.e.
the design constant (1.63 / 1.33), and the verifier preferred that key, so `1.3 ≤ clear ≤ 3.0`
compared the target with itself and was green on all 20 signs — including seven connector posts the
polyline field put ON pavement (`edge_clear_m` −0.06 … −1.74 at DCL-2 fwd/rev, MED-6 fwd/rev,
MED-8-rev, MED-10-fwd, MED-13-rev) and the DCL-2 pair standing 0.44 m apart. That is the mirror
class the standing rule at the top of this file describes: a value written by the thing being
checked is not a measurement. This round (c) becomes the perpendicular distance from the post to
the built curb face found by the ray-cast, and the spacing and `expect_arrow` rows are added so the
DCL-2 overlap and a mirrored plate fail by number. The six mainline signs (M1, M2, M2-2, M3, M4,
M5) passed on the built mesh with 0.06–0.61 m mesh shifts and are held to ±0.3 m through the fix.

**Not changed.** `drive_test`, `audit_mesh` (never reads `SIGN*`) and `verify_kn5` are untouched.
`kn5_ground_check`'s `SIGNPOST` bucket (0.08 m) is not run by `ship_sd.sh` and would flag the
0.30 m post sink if it ever is — exempt the bucket or sink 0.08 m then (0044, Verification §3).

## 2026-10-11 — race layouts: divider bands, per-layout drive test, spawn kn5 checks (ledger 0047)

**Change.** `data/barrier_bands.json` (the centre chain's 0.67 m base per vertex, the kerb-line
barrier strip on both curb faces with its 0.82 m lane inset, the three sealed-mouth polylines, the
seven race-kerb runs — written by `tools/barrier_bands.py` from the declared `race.centre_runs`
and VALIDATED there, the file `tools/author_race_blend.py` builds the strips from) joins
`median_bands.json` as a second divider kind in `scripts/geometry/median_zone.py`. The kinds load
independently; default `contains()` kinds stay `('island',)`, so every existing caller and every
track without the file gets byte-identical numbers; a length mismatch disables that kind only,
loudly. The gates consult the barrier kind only for layouts with `race_furniture: true`:

| Gate | Before | After |
|---|---|---|
| audit **D** walls-on-road | every race 1WALL vert counted (the strips would add ~117k) | `--race [--obj track.race.obj --out audit.race.json]`: verts on the declared centre band (0.335 + 0.6 m laterally, 2 m along), edge band (\|lat − (w/2 − 0.485)\| ≤ 0.935) or a mouth polyline exempt; K/I island-only (the 0.05 m race kerb is under K's 0.10 m); **E and F unchanged** — E is the strips' seating gate |
| drive_test lanes | ten paths about the centreline, clamped ±6 m of it; island stations move right | one run **per layout** (`run(project, layout)`; CLI `--layout <id>` repeatable, default every `layouts[]` entry); `direction: reverse` walks the lap backwards (points, widths, bands, bridge spans, replication); kind `race` is judged on `data/track.race.obj`; lane = (dh + 0.4 + 0.75) .. (w/2 − inset − 0.4 − 0.75) with dh = max(island half, chain half 0.335), inset the kerb-line strip's; no divider + no inset = today's lines verbatim; clamp lane-relative \|off − mid\| ≤ min((hi − lo)/2, 6); step/kink memory resets when the lane moves > 0.5 m |
| drive_test obstruction disc | centreline disc; lane disc on island stations ±2 vertices | lane disc on every divider/edge station and within **7 m** along the line of one (`NEAR_DIVIDER_M`: the 6.3 m disc reaches a strip end or nose from 6 m out); a station with no divider of its own borrows the nearest one's; inner edge 0.1 m off the divider face, outer edge 0.1 m off the kerb-line strip's face |
| drive_test `barrier_missing` (new) | — | race layouts: at every station whose BOTH bracketing vertices declare a band, a 1WALL must stand within ±0.3 m of the band centre (chain: centreline; strip: w/2 − 0.485 each side) rising > 0.25 m over the deck; no hit within half a module (4.04 / 2 m) along the band = missing; **gate 0**; per-layout files `data/drive_test.<id>.json`, `data/drive_test.json` becomes the summary (`fail` = any layout) |
| verify_kn5 | spawns within 13.5 m of road, main or `__*.kn5`, no facing read | `len(layouts) > 1`: (a) road and race kn5 spawn-free, exactly one `<slug>__<id>.kn5` per id, no stray; (b) each spawn kn5 nodes-only, carrying exactly `dummies_<id>.json`'s set, START/PIT/HOTLAP on the road kn5's 1ROAD; (c) heading: local +Z (node matrix row 2) · the layout's kn5-frame travel at the nearest `finished_centerline.json` vertex ≥ cos 30° ⚠, dot printed; (d) START/PIT right of travel ((−t.z, t.x) in the kn5 frame), ≥ 0.335 + 1.0 m ⚠ off the centreline where the chain is declared; (e) AC_TIME_0 within 2 m of `start.line_vertex`, 0 < d ≤ 35 m ahead of AC_START_0, sectors increasing in driving order (L11); (f) race kn5: every mesh and material RACE-named, ≥ 1 1WALL_RACE and 1KERB_RACE, under the cap, no dup name across road + race, no spawn node, < 20 MB. Single-layout tracks: unchanged. `_parse()` keeps its 2-tuple shape; `_parse_full()` adds the heading and the material names |
| tools (self-gates, exit 1) | — | `barrier_bands.py`: every run vertex ≥ 17 m wide, off any island except a run END on the nose vertex (one short = fail), not on a narrow street, not inside a hairpin arc (\|D\| ≥ 135°), ≥ 9 m ⚠ clear of a declared bridge span; edge gaps == bridge spans; grid columns clear of the strip face. `layout_dummies.py`: ids unique and never `full`/`freeroam`, direction ∈ {forward, reverse}, kind ∈ {street, race}, `race_furniture ⇒ race`, vertices in range, AC_TIME_0 0 < d ≤ 35 m ahead of the pole, sectors increasing in driving order on a < 1°/vertex ⚠ straight off any island |

**Why it is not a bypass.** Bands only where the track declares a strip and only for the layouts
that load it; a strip off its band still fails D; the strip must be present (`barrier_missing`,
with the 4.04 m continuity rule), seated (E, floating furniture) and clear of the swept lane (the
lane disc); the anticlockwise carriageway of College/Navajo/Jackson/Lake Murray is swept for the
first time. The street layout never reads the bands and never loads the race kn5.

**Measured basis.** centerline.local.json 4,499 verts / 13,480.1 m; Alvarado 13.0 m on v25–723,
every other mainline run 17–32.5 m; five islands 2,474 m; declared chain 6 runs / 8,525 m on 2,851
verts ending on the ten nose vertices (v780 and v4440 the free ends); kerb-line strip on 4,393
verts, gapped only inside the three declared spans (v609–619, v856–902, v4444–4491); module
0.67 × 1.20 × 4.04 m (249 verts, measured off `assets/models/concrete_barrier_4m.obj`); grid
clearance +0.08 m at 8 slots (car edge 5.60 m vs strip face 5.68 m on 13.0 m Alvarado).

**Dry run (2026-10-11, a scratch copy of the 2026-10-09 workshop build under the three-layout
config; no kn5 exported, nothing installed).** street: ground-through-lane 82, floating 391,
severe 0, excursions 101 (79 far), obstruction 0, kinks 4.97/km — every key identical to the
2026-10-09 `data/drive_test.json`; audit D 512 / K 154 / I 145 / F 15 identical; `--race` audit on
the same OBJ: D 512 (no existing wall stands on a declared band). race_cw / race_acw on the same
OBJ (no strip built yet): obstruction 0 in BOTH carriageways, ground-through-lane 65 / 13 (today's
82 split by lane), `barrier_missing` 34,833 / 34,833 → FAIL — the gate has teeth. Wall time:
street 11 s, both race runs 21 s, audits 10 + 9 s, verify_kn5 7 s on the 92 MB kn5. verify_kn5 on
today's road kn5 under the three-layout config: refused (16 spawn/timing nodes in the road kn5, no
race kn5, three spawn kn5s missing) — exactly the state the ship chain must not pass.

**Still owed.** The 30° heading, 0.4 m lane clearance, 1.0 m chain straddle, 4.04 m continuity,
7 m transition window, 9 m bridge clearance, 1°/vertex sector straightness and the kerb lengths
are ⚠ invented pending a measured envelope; `kn5_ground_check` still not in the SD chain; the
race-run wall time with ~153k 1WALL verts (strips built) is to be re-measured on the first ship.
engine-july mirrors of `median_zone.py` (new there), `drive_test.py`, `audit_mesh.py`,
`verify_kn5.py` are plain copies of airoso's (engine-july is a dangling worktree: nothing there is
committed; the md5s live in the 0047 handoff/commit).

### Same day — the lane sweep's centre clamp

`drive_test.py` clamped every wheel path to ±6 m about the centreline, written for the centred sweep
and never made lane-relative when the island sweep landed (2026-10-08): seven of ten island paths
collapsed onto 6.0 m and the inner wheel LINE at isl + 0.4 sat the wheel 0.35 m inside the island
curb. Fixed with the lane-relative clamp and the wheel-line at dh + 0.4 + 0.75. Measured on
Lake Murray: no island-station count moved (82 / 82 ground-through-lane, 0 / 0 obstruction).

### Same day — spawn facing

Measured on the workshop road kn5 (2026-10-09 ENG prep): AC_START_0 local +Z · AI travel =
−1.00. Two stacked causes. (1) The prep yaws every facing dummy with the SEAM tangent
`cl[0]→cl[1]` (ledger 0016's class) while `place_dummies` put the grid on Jackson — the Alvarado
westbound heading applied 5.5 km away. (2) The add-on's `convert_matrix` (decompose → quaternion
axis (x, z, −y)) maps `rotation_euler.z = ψ` to kn5 local +Z = (sin ψ, cos ψ): predicted
(−0.952, −0.307) for the seam ψ, measured (−0.95, −0.31). With ψ = atan2(tx, tz) (the prep and
`tools/set_start_blend.py`) +Z = (tx, tz) while the kn5-frame travel is (tx, −tz): +0.81 on the
seam heading, −0.98 on north-south College (the installed build's −0.91). Fixed in
`tools/layout_dummies.py` (ψ = atan2(tx, −tz) at the dummy's OWN vertex, +π for `reverse`),
gated by verify_kn5 (c); `tests/ac/test_verify_kn5_layouts.py` pins the derivation on the real
centreline. k10-colorado's reverse layouts (`kn5_write.py:362`) share the reflection — ledgered,
not fixed here.

### Same day — the ship chain's own gates (ledger 0047, wiring)

`tools/ship_sd.sh` is now the three-version chain (street + race_cw + race_acw; one road kn5,
one race-furniture kn5, three spawn kn5s). What it gates on, beyond the entry above:

| Gate | What it checks | Exit |
|---|---|---|
| `tools/verify_race.py` (new, after the author step, before any kn5 exists) | `data/race_authored.json` vs `data/barrier_bands.json`: A provenance (not a stand-in, same edge_mode / height, RACE prefixes, no failed run, ≤ 1 % interpolated rings); B budgets per object (≤ 900 rings, < 60,000 positions, loops × 1.5 < 65,535 render verts, unique RACE name, seating gap ≤ 0.05 m); C chain (one object per declared run, every ring on a declared vertex, never on an island beyond the nose, never on Alvarado / inside the hairpin arc, run ends within 1.5 m of the declared vertices, parts joined); D kerb-line strips (every declared vertex has a ring on each side except the author's fold-dropped count, no ring inside a bridge span, every `join` end met, every `free` end at a declared gap); E kerbs (declared set == authored, corners match); F spawn clearance (no overlap, real dummies) | 1 on any miss |
| race kn5 size | `build/<slug>_race.kn5` < 20 MB ⚠ (a leak of road geometry or the texture table into it) | 1 |
| `kn5_to_gate_obj --kn5 road --kn5 race --out data/track.race.obj` | ONE gate OBJ for the kn5 set a race layout loads (vertex offset carried across files); the name has a DOT because the loop prep merges every `data/track_*.obj` into the scene — the tool refuses a `track_*.obj` output | 1 |
| `--force-install` | never covers a race layout red on `barrier_missing` or obstruction (no reference exists to be "no worse than"); the street layout keeps the July-reference comparison rule | 1 |

**Not a gate, but load-bearing.** The prep (`build_kn5_loop.py`, both the engine-july pin and
airoso's copy) creates NO `AC_*` empties and writes `data/dummies.json = {}` when `len(layouts) > 1`,
and keeps the authored UVs of `1WALL_RACE*` / `1KERB_RACE*`; `export_kn5_addon.py` takes `--blend`
/ `--out` and runs once per split scene with one `.ini` per pass; the race author step runs on
every ship (also `--skip-blend`) so `loop.blend` never drifts from `race.*` in the config.

**Dry run (2026-10-11, scratch copy, `--skip-blend --dry-run` then the gate half by hand).**
bands → dummies → author (36 objects / 122,338 positions, 0 interpolated) → verify_race OK → prep
(`multi-layout (3 layouts) … dummies.json = {}`) → split on the PREPPED scene (race: 36 meshes /
36 RACE-named materials / 0 AC nodes; main: 0 race / 0 AC; problems []) in 23 s. Gates on the
existing road kn5: street 82 / 391 / 0 / 101 and audit 512 / 154 / 145 / 15 — identical to
2026-10-09; race_cw / race_acw `barrier_missing` 34,833 / 34,833 FAIL (nothing built yet) →
`RACE_RED = race_cw race_acw` → the install block refuses even with `--force-install`; verify_kn5
refuses (16 spawn nodes in the road kn5, no race kn5, three spawn kn5s missing). Wall: gate OBJ
5 s, street drive_test 11 s, audits 9 s, both race drive_tests 20 s, verify_kn5 5 s, packer 7 s.

### Same day — race gates tightened and extended (ledger 0047 fix round)

| Gate | Was | Now | Basis |
|---|---|---|---|
| `verify_race` F spawn clearance | the AUTHOR's record only: FAIL on overlap (clear < 0), a note below 0.30 m | **re-measured by verify_race itself** from every race layout's `data/dummies_<id>.json` (what `build_spawn_kn5` ships) against the declared strip faces (bands params: `half_w + edge_centre_from_lip_m − barrier_half_m`; chain `centre_w / 2`); FAIL when a 1.9 m car on any grid / pit / hotlap slot is < **0.30 m** off a face; the author tool's record fails on the same floor | ⚠ 0.30 m is invented (no measured reference grid-to-wall gap yet); it replaces a 0.08 m clearance (1.4 m stagger) that passed. Proven: synthetic slots at 0.73 / 0.23 / −0.27 m pass / fail / fail-OVERLAP (`tests/tools/test_verify_race.py`); real data 0.48 m on AC_START_1/3/5/7 of both race layouts |
| `barrier_bands` no-gap zone | FAIL when the outer grid column overlaps the strip face (clear < 0) | FAIL below **0.30 m** (the same floor); the stagger / pitch / pit constants are now READ from `tools/layout_dummies.py` instead of restated (a stale 1.4 m copy would have declared a clearance the grid does not have) | as above; `no_gap_zones.grid_clearance_m` 0.08 → 0.48 on all three layouts, nothing else in `barrier_bands.json` changed |
| `verify_race` G lamp masts (new) | — | every lamp mast (base = `lights.local.json` head set back road-ward by `author_lamps_blend.ARM_M`, parsed from that file; footprint radius from `assets/models/lamp_post.obj` at `POST_H`, 0.585 m) stands OUTSIDE every kerb-line strip and centre-chain footprint; FAIL on any overlap (margin < 0), minimum margin reported | geometric (an overlap is a mast inside a barrier), not a tuned number. Real data: 238 of 239 masts beside a strip, minimum margin 2.36 m, none inside |
| `verify_race --pre-author` (new mode) | — | F + G alone, no `race_authored.json` needed | wiring only; the ship chain still runs the full check after the author step |

**Texture binding (not a gate, found while auditing what ships).** `pbr.network_walls: true` (Lake
Murray, for the merged freeway's barriers) reskins the generic `1WALL` key; the race strips had no row
of their own and fell through to it. The prepped dry-run scene of 2026-10-11 00:47 bound
`building_diffuse/normal.jpg` on 29/29 `1WALL_race_*` materials. `scripts/ac/pbr.py` (airoso and the
engine-july copy, byte-identical) gained `1WALL_RACE` / `1KERB_RACE` rows ahead of the generic ones;
the re-run binds `concrete_barrier_*` on 29/29 and `kerb_diffuse.png` on 7/7.
`tests/ac/test_pbr_race_rows.py` resolves both names with network_walls on and off.

### Same day — race kn5 judged on content; ring density becomes a gate (ledger 0047 weld pass)

| Gate | Was | Now | Basis |
|---|---|---|---|
| race kn5 guard (`tools/ship_sd.sh`, after the race export) | `build/<slug>_race.kn5` < 20 MB ⚠, "the split leaked road geometry or textures into it" | **content**: `python -m scripts.modkit.inspect_kn5 <race kn5> --json data/race_kn5.json`, then `tools/check_race_kn5.py`: FAIL unless every mesh upper-starts with `1WALL_RACE` / `1KERB_RACE`, every embedded texture is in the race set READ from `scripts/ac/pbr.py`'s `1WALL_RACE*` / `1KERB_RACE*` rows (kerb_diffuse.png, concrete_barrier_diffuse.png, concrete_barrier_normal.png), no node (transform or mesh) is named `AC_*`, and at least one mesh exists; the size is printed with verts / tris / ratio and WARNs at ≥ 20 MB, never fails | the size cap fired on the first real rehearsal for a kn5 that leaked nothing (36 RACE meshes, 3 race textures, 35,553,024 B — flat shading made it 2.98 verts per triangle); size measures shading, not leaks. `inspect_kn5`'s parse gained a `nodes` list (class-1 node names: the root `BlenderFile` here) so the AC_* check is not blind. Proven: `tests/tools/test_ship_sd_chain.py::test_race_kn5_guard_is_a_content_check` (clean passes with a size WARN; a road mesh, a road texture, an `AC_START_0` node, no mesh, a parse without `nodes` each FAIL); the old kn5 passes content with the WARN, the road kn5 fed to it FAILS on 31 meshes / 14 textures; the rebuilt race kn5 passes (12,558,972 B, 0.81 per triangle) |
| `verify_race` H ring density (new; was the "spacing reaches 7.02 m … chords ~0.39 m" note) | reported, never gated (estimate gap² / (8 × 16 m)) | every consecutive pair of chain / kerb-line strip ring centres vs the DECLARED offset curve, rebuilt in verify_race from the bands + centreline alone (centre lerped along each centreline segment, left normal of the normalised lerp of the two vertex tangents, declared lateral `half_w + edge_centre_from_lip_m` lerped; lat 0 for the chain; 32 samples per interval): chord error > **0.15 m** FAILS; spans where the declared curve folds back (inside lips the author chords on purpose) are counted, not judged; rings > 0.5 m off the curve or spans > 40 intervals are counted unmeasured (C / D judge those); spacing above 3.5 m is a note | ⚠ 0.15 m is invented (the author's target is 0.10 m, `race_furniture.CHORD_MAX_M`; 0.15 leaves room for the 0.01 m rounding of `ring_centres`). Measured: the pre-densify authored file chords 0.271 m at the seam corner's outside lip (`1WALL_race_edge_L_lakemurray_4492_0`) and 0.171 m at the hairpin → FAIL; the densified one 0.043 m, spacing 3.50 m → OK. `tests/tools/test_verify_race.py::test_ring_density_is_judged_against_the_declared_offset_curve` (on-curve strip passes, one ring dropped on a 109.5 m lip 0.05 m passes, five dropped 0.49 m FAILS, a ring shoved 0.31 m off FAILS, H never runs without widths) |
| `audit_mesh --race` D exemption (`scripts/geometry/median_zone.py` barrier kind) | each declared band POINT owns a ±2 m-along × (0.335 + 0.6) m-lateral rectangle; the closure duplicate of a closed lap was a band point of its own (the LAST street's width, 27.5 m vs v0's 17.0 m on SD) with one-sided tangents at both seam vertices (6.8° off) | the band is **continuous between consecutive declared vertices of the same kind** (distance to the segment between their band points, the same 0.935 m reach; the ±2 m rectangles still own a run's ends); on a closed lap the duplicate is vertex 0's band and the seam tangents wrap (central difference) | no widening: same lateral reach, nothing past a run's end. The ±2 m rectangles only covered the declared strip where band points stand ≤ 4 m apart; on the outside lips of the five corners they stand ~7 m apart, and the densified rings in those gaps read as **460** walls on the road (race D 512 → 972 on the first weld-pass rehearsal); with the continuity 28 remained, all on `1WALL_race_edge_L_lakemurray_4492_0` at the seam — the duplicate's width put its band point 5 m inboard. Both fixed: race D 512 on the new kn5 set AND on the pre-weld one (`track.race.base.obj`, i.e. nothing the old build counted is exempted now), street D untouched (it never reads the barrier kind). `tests/geometry/test_median_zone_kinds.py` (mid-gap points inside, 2.5 m past a run's end still outside, the closed-lap seam band at vertex 0's width with a wrapped normal; the three tests fail on the previous module). drive_test reads only the per-vertex lookups, not `contains`, so its numbers cannot move. engine-july's copy (`dc1b2ef1…`, not run by the ship chain's gates) is NOT edited — the two copies now differ |

**Not a gate, but load-bearing.** `tools/author_race_furniture_blend.py` now smooth-shades every RACE
object (`Mesh.shade_smooth`) and marks hard only the edges `race_furniture.sharp_edges` (> 30°) and
`kerb_outline_edges` return, and refuses to save if the flags did not land. The prep was read, not
edited: `DOUBLE_SIDE` (`1WALL`, `HWYSTRUCT`) appends reversed faces only to groups merged from
`data/track_*.obj` / `env_*.obj` (none on SD), so a `1WALL_race_*` from `loop.blend` is never
doubled — the 241,190 triangles the old race kn5 carried are exactly the authored quads × 2 + caps;
its bmesh round trip keeps the smooth / sharp flags (measured on `loop_race.blend` after prep + split:
7,158 / 7,158 smooth faces and 4,300 hard edges on `1WALL_race_kbar_navajo_2297_0`, as authored), its
face-up pass reverses 2 of 4,545 kerb faces (the hairpin fold of `1KERB_race_770_in`), and it only ever
sets `use_smooth = True` (above 65,535 loops; no RACE object comes near). engine-july
`scripts/ac/build_kn5_loop.py` md5 2dcc8e8b9d4024ec9a9ee3fadb1236b8 and airoso's
8752e96360b2882021c089322f0e5771, both unchanged.

### Same day — the race furniture gates measure the built lane and the built corner (ledger 0047 red-gates round)

The first full REAL rehearsal of `tools/ship_sd.sh` (scratch `SHIP_PROJ`, `--skip-blend`) passed everything
except the race layouts' own furniture gates: race_cw obstruction **220** / `barrier_missing` **22**,
race_acw **175** / **32** (34,833 probes each). Three read-only diagnoses replayed the gates on the built
OBJ; the stations split into two gate bugs and one geometry bug, and every fix below is measured on that
rehearsal.

| Gate | Was | Now | Basis |
|---|---|---|---|
| `drive_test` race lane width (race layouts only — the street layout and every single-layout track read `widths` exactly as before) | the lane and the scan disc at a station between vertices i-1 and i used `widths[i]`, the vertex AHEAD | `_wl` lerped at the station (`w_lane`); on a closed lap the closure duplicate is vertex 0 (it carried Lake Murray's 27.5 m vs Alvarado's 17.0 m — median_zone's rule) | not a threshold. SD's mouth flares grow 0.55–1.50 m per ~3 m vertex, so the lane was up to 1.36 m too wide and the disc reached the PREVIOUS ring of a strip standing on its declaration (OBJ footprint minus declared face: median +0.009 m, 332 of 341 within ±0.03 m): **341 of the 395** obstruction stations |
| `drive_test` race lane clip (new `TriField.rising_in(keep=)`) | a round disc mid-lane (radius half-lane + 0.3, cap 6.3 m) | an obstacle vertex inside the disc counts only if it stands inside the declared lane AT ITS OWN STATION (projected onto the walked line, ±8 segments ⚠, wrapped on a closed lap), with the disc's existing 0.1 m off each face (no new margin) | can only DROP a vertex outside the declared lane; one inside it still fails. The disc reaches as far along the road as across it, so on a steep flare it caught strip rings on their declaration up to 1.33 m behind the station (s2271, s4534) |
| `drive_test` barrier presence (`barrier_missing`) | probe at `widths[i]/2 + edge_centre_from_lip` (the closure duplicate's 27.5 m put the seam probe 5.25 m outboard of the strip); continuity check linear in station, blind across the seam | probe at the lerped width; a station inside a declared trimmed corner (`edge_corners`, below) probes the declared in → X → out polyline at the same fraction of its length, the ±0.3 m spread along the polyline's normal (every declared metre still probed, nothing skipped); on a closed lap a miss within half a module of the seam is covered by hits across it | the seam station s13480 (race_cw edge_L) / s0 (race_acw edge_R) was a gate bug: the forward-left strip there is complete. Skipping the fold stations instead was measured 0 / 0 and REJECTED as a bypass (chords up to 5.26 m > one 4.04 m module would go unprobed) |
| `scripts/geometry/median_zone.py` barrier kind (audit D `--race` exemption, drive_test lookups) | an edge band point at every flagged vertex, incl. the folded inside-lip offsets | `edge_corners` loaded: a trimmed vertex has NO band point on that side; the band across it is the polyline in-vertex band point → X → out-vertex band point (same 0.935 m reach, no extension); `edge_corner_spans(kind)`; `reversed()` swaps the side and maps k → (n−1−k) mod (n−1) | the exemption stands on the built corner only. audit `--race` D 512 → **512** |
| `tools/barrier_bands.py` (the declaration) | inside-lip band points declared on the folded offset curve at every vertex | `edge_corners` (+ `edge_fold_vertices`, `summary.edge_corners`) from `race_furniture.edge_fold_corners` — the author's own plan + trim; FAIL when a fold's removed vertices are > 15 ⚠ vertices from every inside corner apex of that side | SD declares 5, all side R: loop v763→774 (hairpin, −74.9°), loop v1508→1517 (−66.8°), loop v2314→2324 (−92.8°), extend v3292→3300 (−85.7°, 3.09 m), extend v4495→5 (seam, −73.1°, 6.99 m); 41 vertices |
| `tools/verify_race.py` D | `len(missing) ≤` the AUTHOR's own `fold_skipped_run` count — passed 23 missing against 27 self-reported drops that were not the same vertices | a SET check: every declared edge vertex without a ring must be in a declared corner's `removed` (a ring within 0.05 m ⚠ `CORNER_TOL_M` of the vertex's declared band point also covers it — inside a tight corner the nearest-vertex map loses the leg rings); every declared corner must have a ring of that side within 0.05 m ⚠ of its X | ⚠ 0.05 m: `ring_centres` are rounded to 0.01 m and the corner ring stands ON X by construction (measured 0.002–0.006 m) |
| `tools/verify_race.py` H | fold spans counted, not judged (5 fold + 4 unmeasured on the rehearsal) | across a declared trimmed corner the declared curve IS the in → X → out polyline (X a sample), so those spans are measured | rehearsal: 5 fold / 4 unmeasured → **0 / 0**, chord max 0.0428 m unchanged |
| `tools/verify_race.py` I (new) | nothing failed an inverted span | from `ring_centres` + `ring_frames` (tangent + lateral scale per ring, written by the author tool): both extreme profile columns (±`barrier_half_m` × ls; a kerb ±`kerb_width_m`/2 × ls about its mid-line) must advance along each span's mean tangent; any inside-out span FAILS; an object without matching frames FAILS | geometric, not tuned. Built blend (all 36 RACE objects, their own vertices; before = the weld-pass blend authored by HEAD's plan code): **7 → 0** (`edge_R_alvarado_620_0` ×3, `college_903_0`, `navajo_1519_0`, `jackson_2324_1`, `1KERB_race_0_in`) |

**The geometry fix (not a gate, load-bearing).** `race_furniture.drop_folded_rings` tested a ring only
against its own tangent, kept the "ear" rings past the offset curve's self-intersection (v768, v1512,
v2317, v3295) and chorded BACKWARDS from them: the inside-out spans above and a hook of wall standing
1–3.5 m inside the exit carriageway of the three chained right-handers (**52** of race_cw's 220). It is
replaced by `_trim_folds` (strips and the inside kerbs): two-sided backward test, folds within 6 m ⚠
merged, the cluster cut where the in- and out-leg cross (`loop`) or where their last real steps extended
≤ 8 m ⚠ meet (`extend`), ONE mitred corner record at X (lateral scale 1/cos(ψ/2), cap 2.0 ⚠), every leg
record nearer X than the mitre's reflex tip + 0.25 m ⚠ dropped; fill rings on a corner chord stand square
to the chord and keep their leg's width. The author refuses a declaration whose `edge_corners` differ
from what it trims (`match_declared_corners`). Kerbs: `1KERB_race_770_in` one loop corner,
`1KERB_race_0_in` one extend corner (+59°, it follows the ribbon's width-step jog at the seam).

**Measured on the rehearsal** (same scratch project, `bash tools/ship_sd.sh --skip-blend`, before →
after):

| line | before | after |
|---|---|---|
| street drive_test: ground-on-top / floating / obstruction / excursion | 82 / 391 / 0 / 101 | 82 / 391 / 0 / 101 (`drive_test.street.json` byte-identical) |
| street audit D / F / I / K (total) | 512 / 15 / 145 / 154 (826) | 512 / 15 / 145 / 154 (826) (`audit.json` byte-identical) |
| race_cw obstruction / barrier_missing | 220 / 22 | **0 / 0** |
| race_acw obstruction / barrier_missing | 175 / 32 | **0 / 0** |
| race_cw ground-on-top / floating / excursion / kinks per km | 65 / 391 / 4 / 5.12 | 67 / 391 / 4 / 5.27 |
| race_acw ground-on-top / floating / excursion / kinks per km | 13 / 391 / 0 / 2.74 | 13 / 391 / 0 / 2.82 |
| audit `--race` D / F / I / K (total) | 512 / 15 / 145 / 154 (826) | 512 / 15 / 145 / 154 (826) |
| verify_race edge missing / fold spans / unmeasured / inside-out | R 23 vs author 27 / 5 / 4 / (not measured) | R 30, all declared (41 trimmed) / 0 / 0 / 0 |
| verify_kn5 | passed | passed |

The race ground-on-top rows moved only in their wheel offsets (the lane is now the declared one): the
same stations before and after (College/Navajo s4535-4539 and Lake Murray s10242-10243, ribbon folds /
ground through the road — inherited, also in the street layout's 82). Gate-only on the OLD build:
52 / 24 and 0 / 28 (all at the folds); geometry-only (old gate on the NEW build): 170 / 60 and 175 / 54 —
neither half alone reaches 0. **Known ribbon defect, not gated:** the seam closure steps 27.5 → 17.0 m in
one 2.29 m segment inside the right-hander, so 4.16 m of the seam corner's 6.99 m polyline stands off
the ROAD ribbon over the curb notch (1 ring seated by interpolation; Jackson/Lake Murray's Z-fold leaves
0.40 m); the fix is a width taper over the seam corner in the centreline data and a ribbon rebuild.
Tests: `tests/geometry/test_drive_test_layouts.py` (a 17 → 24 m flare with strips on their declaration
has 0 obstructions, a ring 1 m in the lane fails; a trimmed corner built by race_furniture passes
presence + obstruction both ways, cut away it fails, undeclared it fails, the untrimmed knot is an
obstruction), `tests/geometry/test_median_zone_kinds.py`, `tests/tools/test_barrier_bands.py`,
`tests/tools/test_race_furniture.py` (an R 8 m / 11.5 m right-hander trims to one mitred corner, no ring on
the lane side of either leg, no inside-out span; the inside kerb too; a drifted declaration is refused),
`tests/tools/test_verify_race.py` (D needs the declaration's trim, not the author's count; a declared
corner must be built; H on the polyline; I fails a turned ring, a backward ring, missing frames).

## 2026-10-11 — `write_ai_line` write-time self-check: geometry refusals, segment ruler (ledger 0047 fix round)

**Change.** The AI draft writer's self-check (it refuses to write; it is not one of the four build
gates) gains geometry refusals and a truer lateral ruler. The audit of the installed three-version
build found race_cw's draft folding at the three chained right-handers (R 0.3 m, 7 km/h at
College/Navajo) and the street draft jogging 21–27° in one step at twelve island noses; both had
passed the old check, which measured only lane clearance.

| Check | Before | After |
|---|---|---|
| fold | — | **refuse** any backward step (a step against the nearest station's tangent) or self-crossing (segments 2–200 apart) |
| curvature | — | **refuse** a step turning > `TURN_MAX_DEG` 10° ⚠ where the road is not that tight (road radius at the point's place ≥ 8.6 m, the radius a 10° step means at 1.5 m), or a 3-point radius < `RADIUS_CHECK` 0.95 ⚠ × min(road radius there, `RADIUS_FLOOR_M` 12 m ⚠). "There" = the tightest raw centreline radius (6 m chord) within ±(3 stations + the point's lateral offset): a lane line rounding a corner sits ~its offset along the leg from the apex. With `--lane-offset none` only the fold refusal applies (the legacy centreline is not reshaped) |
| lateral ruler | nearest declared VERTEX, its central tangent, its own channels | nearest declared SEGMENT (among the segments of every vertex within 4 m of the nearest), signed point-to-segment distance; width interpolated along the segment, divider / island / inset the larger end (the resampler's declaration rule). The apex vertex's diagonal normal overstated a corner-cutting point's lateral by up to (1 − 1/√2) of it |
| edge | kerb-line barrier face − 0.6 m only where an inset is declared | also the pavement edge − 0.6 m where none is (the street layout's lane is "inside the pavement − 0.6 m") |
| divider hits | island hits only | + `divider_hits` (on the island or the chain), reported |

**Why it is not a bypass.** Every old refusal stands (island, divider face + 0.6 m, barrier face −
0.6 m, right side 100 %); the ruler change only removes the vertex ruler's overstatement inside
tight corners (measured: one street point at College/Navajo read 0.34 m from the edge by the
vertex ruler, 0.83 m by the segment it actually sits beside — the ribbon edge is straight between
edge vertices). The new refusals are added, not traded.

**Measured basis (scratch copy of the workshop, `write_ai_line --layout <id>`).** street / race_cw /
race_acw: 0 backward steps, 0 self-crossings, 0 steps > 10° (installed: 29 / 17 / 16), min radius
12.5 / 12.6 / 10.3 m (installed 3.28 / 0.27 / 4.27), min divider clearance 4.21 / 1.51 / 3.39 m, min
edge clearance 0.83 / 3.60 / 3.61 m; Dragon Tail and Under the Dragon (gravel) drafts written, 0 refusals
(Dragon Tail was refused by an intermediate version whose Laplacian smoother dragged R 10 m bends onto
the lane edge — the shipped smoother is a Taubin pair that returns its best state). ⚠ 10° / 12 m /
0.95 are the ledger-0047 audit's numbers, not measured envelopes. Tests:
`tests/ac/test_ai_line_geometry.py`, `tests/ac/test_write_ai_line_layouts.py`.

## 2026-10-11 — race corridors: `no_route` containment gate, barrier_bands v2 self-gates, per-layout lanes (ledger 0049)

**Change.** Kevin's race brief ("the entire other lane blocked off from access", "an Alvarado's width for
the entire track", open intersections at the corners the race turns at) replaces 0047's shared centre
chain with one closure per direction. Nothing gated containment before this: every gate checked the lane
the car is *supposed* to drive, none checked that it cannot leave it. New and changed gates:

| Gate | Before | After |
|---|---|---|
| **`tools/no_route.py`** (new, hard) | — | flood fill per race layout from `AC_START_0` on the layout's BUILT gate OBJ (`track.<id>.obj` = road + common race + that layout's closure kn5): FAIL on any cell reached outside the declared corridor, on a reached forbidden probe, or when a lane-centre cell / `AC_START_n` / `AC_PIT_n` is not reached ("corridor blocked at v…"). Writes `data/no_route.<id>.json`, exit 1. A v1 declaration is read with its own semantics (chain / island face) |
| no_route PLANNED (new, inside `barrier_bands.py`) | — | the same fill on the declared polylines (both strips with trimmed corners + this layout's closure + mouth lines, ±0.335 m) before any authoring; `data/no_route.<id>.planned.json`. Not an L5 gate: the declaration checking its own topology |
| `barrier_bands.py` | v1: chain runs validated (17 m threshold, nose butt joints, hairpin arc, `BRIDGE_CLEAR_M`), strips gapped at the bridge spans | v2 self-gates (exit 1): zones cover every vertex once, boxes hold their corner arcs, derived runs == `race.corridor.closure_runs`; pins on the far strip centre ±0.01 m and not on a trimmed fold vertex; rates (toward the race side ≤ 1:12, away ≤ 1:6, pin zones ≤ their forced rate +2 %, nothing steeper than 1:3); clear ≥ 6.5 m everywhere, ≥ 10.86 m except listed island / pin-zone / convergence vertices; pocket ≥ 2.0 m behind every running closure; closure ≥ 0.15 m off the AUTHORED island (nose taper included) at every vertex; 0 backward steps; plan radius ≥ 20 m; mouth policies; grid + pit slots ≥ 0.30 m off both lane faces; exactly 10 kerbs ≥ 0.05 m off every closure; strips on every vertex; `centre_runs` refused; the Alvarado re-measure within 0.02 m of `clear_width_m`; planned no_route 0 leaks, lap complete |
| `median_zone` | one barrier zone for every race layout | `MedianZone.load(project, layout=<id>)`: both curb strips + THAT layout's closure band (same ±(0.335 + 0.6) m, continuous between declared vertices); `lane_r(i)`, `closure_at(i)`, `zone_at(i)`. Without a layout: unchanged. A v2 file without the asked layout: SystemExit |
| `drive_test --layout` (race, v2) | lane = divider face .. kerb-line face, neighbour borrowing near dividers; OBJ `track.race.obj` | lane = the declared `lane_by_vertex` faces lerped at the station, `DIVIDER_CLEAR_M` 0.4 inside each face, no borrowing (the declared lane is continuous; boxes / whole street are full width, 6.3 m disc cap kept); `barrier_missing` adds key `closure` (probed on the line between the two declared ring centres); OBJ default `track.<id>.obj`; report `lane`. v1 files: unchanged |
| `audit_mesh --layout <id>` | `--race`: D exempt on every declared band | D exempt on that layout's bands only (its closure, never the other direction's); defaults `track.<id>.obj` → `audit.<id>.json`; **new W** = a race-strip vert inside another wall's footprint or vice versa (plan ±0.05 m, inside its height range), hard under `--layout`, reported under `--race` |

**Retired.** `BRIDGE_CLEAR_M` 9 m (invented); "edge gaps == declared bridge spans"; the 17 m
`wide_threshold_m`; the nose butt-joint rule; the hairpin-arc chain rule; `declared_open`. The three
bridge spans had no rail on most of their length (Alvarado v609-619 none at all; College rail only
v864-887 of v856-902; I-8 only v4454-4474 of v4444-4491): a strip gap there was a door.

**Teeth (measured 2026-10-11 on scratch copies; nothing built, exported or installed).**

| Run | Result |
|---|---|
| TODAY's installed race build (`track.race.obj`, v1 semantics), race_cw | **FAIL** 752,562 m² outside the corridor, 11 door clusters: Alvarado bridge v606-620 L+R, College bridge v854-903 (race side), I-8 bridge + chain end v4438-4493 L+R, chain end v779-781, all five islands' race faces nose to nose (the beam alone is not a wall) — every door escapes to the open map |
| same, race_acw | **FAIL** 752,263 m², 11 clusters, the mirror |
| planned v2, race_cw / race_acw | **PASS** 0 / 0 leaks, 139,130 / 138,826 m² reached (the study's prototype: 138.8 k / 138.4 k), lap complete |
| planned v2 with today's bridge gaps put back | **FAIL** 5 clusters per layout at exactly the uncovered spans (v608-619 L+R, v855-902 race side, v4443-4491 L+R), 210 / 406 probes reached |
| v2 swept into a virtual BUILT OBJ (declared strips + closure seated on the deck + today's road-kn5 `1WALL_guard`) | **PASS** 0 leaks both layouts, 0 / 406 probes reached, spawns reached |
| synthetic (tests) | sealed L-corridor passes both ways; 1.5 m door FAILS at its vertex/side (off_road, escapes); 0.8 m crack passes; beam-only closure (0.63-0.93 m) FAILS, posts or not; unpinned closure end FAILS (opposite); cross wall → "blocked"; seed in a wall → exit 2; reached probe FAILS |

The prototype counted 51 "clusters" because it bucketed door cells per 4 vertices and never merged
same-side buckets; the gate clusters door cells spatially (cells within 2 m), so the same doors read as 11.

**Regression floor.** The street layout's paths are untouched (no layout → the zone, lanes and OBJ are
today's). Today's race OBJ re-audited under `--race`: D / K / I / F = 512 / 154 / 145 / 15 (the stored
`audit.race.json`), W = 0. Planned v2 strips stand 0.15 m inboard of the College and I-8 deck rails in plan.

**Wall rule detail (measured).** Per cell the union of the height ranges of the wall triangles touching it
and its 8 neighbours must cover every 0.05 m bin of [deck + 0.20, deck + 0.90] (deck = the centreline y at
the projection + 0.10). One cell alone sees only one face of the jersey profile (the steep face is 0.47-1.20,
the toe 0-0.38), so the 3 × 3 union is what makes a K-rail a wall; the beam (0.63-0.93) stays open. Today's
race strips measured: base -0.05 m, top +1.15 m relative to that deck (the v2323 ribbon fold: base -0.52, top
1.16 — still spans).

| Value | Status |
|---|---|
| cell 0.25 m, tile 64 m, domain w/2 + 25 m, PROBE_R 0.5 m, TOL 0.75 m, wall band 0.20-0.90 m, height bin 0.05 m + 3 × 3 union, door link 2 m | ⚠ INVENTED |
| pocket 2.0 m, hard minimum 6.5 m, floor 10.86 m (band −0.5 / +1.5), rates 1:12 / 1:6 / I-8 1:10, steepest 1:3, pin zone 120 m, base ±60 m / σ 20 m, island envelope 30 m, attract 40 m, smooth 4 m, opening ≤ 100 m, radius floor 20 m on a ±6 m stencil, box pad 2, kerb clip 0.05 m, convergence reach 150 m, W tolerance 0.05 m, mirror report window 100 m | ⚠ INVENTED |
| clear width 11.36 m (re-measured 11.36: median w − 2 × 0.82 on Alvarado), strip inset 0.82, strip centre 0.485, K-rail half base 0.335, nose 0.25 m over 3 vertices | MEASURED |

Tests: `tests/tools/test_no_route.py`, `tests/tools/test_race_corridor.py` (the port reproduces the study's
solution, fixture `tests/tools/fixtures/sd_corridor_proto.json`, to 1 mm), `tests/tools/test_barrier_bands.py`
(every v2 self-gate fires on its crafted defect), `tests/geometry/test_median_zone_kinds.py`,
`tests/geometry/test_drive_test_layouts.py`, `tests/geometry/test_audit_race_flag.py`.

### Same day — the authored furniture, the export split and the kn5 checks (ledger 0049, geometry)

**Change.** The furniture behind the corridors: both curb strips authored as ONE closed loop per side (across
all three bridges), each race layout's closure authored into its own collection (`RACE_CLOSE_CW` /
`RACE_CLOSE_ACW`) and exported to its own kn5, the 10 race kerbs clipped against every closure. The gates that
judge it before and after the export:

| Gate | Before | After |
|---|---|---|
| `verify_race` C (chain) → **C′ closures** | one chain object per declared centre run, rings on centre_w vertices, never on an island / Alvarado / the hairpin arc, ends within 1.5 m of the run's vertices | per race layout: one object chain per declared closure run, parts joined on a shared ring (0.05 m); EVERY ring within `CLOSE_TOL_M` 0.05 m of the declared closure line (closure_y lerped between vertices, the densify curve); no declared closure vertex in a BOX / WHOLE zone; each run's first / last ring AT its pin: within `PIN_TOL_M` 0.05 m of the declared far curb-strip line, at the pin vertex ±1 |
| `verify_race` D | every DECLARED edge vertex covered (gaps allowed), "no ring inside a bridge span", a `free` end must stand at a declared gap | EVERY centreline vertex covered on both sides, bridge spans included (C1 — the inversion), except the declaration's `edge_corners[].removed` (set check, unchanged); declared corners built (unchanged) |
| `verify_race` E | declared (apex, in/out) set == authored | + each kerb's run == the declaration's (clipped) i/j; + every kerb footprint (mid-line ± 0.5 m × ls) ≥ `KERB_CLEAR_M` 0.05 m off EVERY layout's AUTHORED closure footprint (re-measured on the ring centres) |
| **`verify_race` J** (new) | — | zero free ends: every curb-strip end is a `join` met by a same-side neighbour's end (0.05 m, re-measured); every closure end is a join with its run's next part or a PIN whose centre stands ≤ 0.05 m off the AUTHORED far strip's centre polyline, full height (`h == barrier_height_m`) and full width (`ls == 1`) |
| **`verify_race` K** (new) | — | every closure's name token is a declared corridor token, its record's owner / layout / collection (`RACE_CLOSE_<TOKEN>`) agree; common furniture owns no token and sits in `RACE`; no RACE object of an unknown kind (the old `1WALL_racecol_*` collider included) |
| **`verify_race` L** (new) | — | 0 interpolated rings inside the declared bridge spans (`race_authored.bridge_seating`, the author's new per-ring seat record); every span carries seated strip rings |
| **`verify_race` M** (new) | — | every `closed_mouths` line lies ≤ `MOUTH_TOL_M` 0.10 m from the authored strip of its side (both strips are common: sealed in both layouts); every mouth has a policy per layout; `behind_closure` = that layout's authored closure runs past the whole mouth (on its declared line, the lane on the race side of it) |
| **`verify_race` N** (new) | — | no `1WALL_race_kbar_*` object; `centre_w_by_vertex` all 0; no centre run |
| `verify_race` F / G | edge faces + centre chain | + the layout's declared lane (`lane_by_vertex`) ≥ 0.30 m off each face; lamps vs every layout's closure footprint (lerped at the mast) |
| `verify_race` H / I | chain + strips | strips + closures (closure curve = the declared closure line) |
| `check_race_kn5` | role-free: RACE meshes, race textures, no AC_* | `--role common` (default in the CLI): no CLOSE / KBAR mesh, ≥ 1 `1WALL_RACE_EDGE_*`, exactly the declared kerb count (`--expect-kerbs`, else `len(kerbs)` of `--bands` / the barrier_bands.json beside the parse); `--role closure --owner <t>`: every mesh `1WALL_RACE_CLOSE_<T>_*`, ≥ 1. `check(parsed, allowed)` without a role is unchanged |
| `verify_kn5` (d) | START/PIT right of travel; ≥ barrier_half + `CHAIN_CLEAR_M` 1.0 m off a declared chain | race layout with a declared lane: every START/PIT car (half-width 0.95) inside the lane, ≥ `LANE_MARGIN_M` 0.30 m off each face (kn5 frame converted: lateral-left = (X−PX)·f.z − (Z−PZ)·f.x on the forward kn5 tangent); otherwise right of travel. `CHAIN_CLEAR_M` retired |
| `verify_kn5` (f) | `<slug>_race.kn5`: RACE meshes ≥ 1 wall + 1 kerb, RACE materials, no dup across road + race | common kn5: + ≥ 1 `1WALL_RACE_EDGE_*`, no CLOSE, no KBAR; per race layout `<slug>_closure_<id>.kn5` present, every mesh `1WALL_RACE_CLOSE_<TOKEN>_*` of that layout's declared token (corridors.<id>.token, else layouts[].closure_token), ≥ 1, RACE materials, no spawn node, < 20 MB, no 1-prefixed name shared with road + common; a stray `<slug>_closure_*.kn5` fails |
| **`verify_kn5 --inis` (g)** (new) | — | on the packed `build/<slug>/`: each race `models_<id>.ini` lists exactly [road, `_race`, `_closure_<id>`, `__<id>`], the street's [road, `__street`]; no ini lists another layout's closure; every listed kn5 is in the folder |
| `split_exports_blend` manifest | race scene RACE-only | + `loop_closure_<id>.blend` per race layout; problems for an undeclared token, a KBAR object, an empty closure blend, a closure in `loop_race.blend` (or the other layout's in a closure blend), (race ∪ closures) ≠ every RACE object, a material no kept object uses |

**Retired.** verify_race's chain checks (C), "no ring inside a declared gap (bridge span)", "a free end must
stand at a declared gap"; verify_kn5's `CHAIN_CLEAR_M` 1.0 m (⚠ invented) centre-chain spawn check; the
author's `--standin-bands` and `--collider` (Q11 not built for per-direction closures).

**Teeth (dry run 2026-10-11, scratch copies only; the workshop loop.blend untouched).** Authored on a copy of
the workshop `loop.blend` against barrier_bands.py v2's own declaration: verify_race OK — 15 curb-strip
objects (closed loops, 0 free ends, every vertex covered but the 41 declared trims), 6 + 6 closure objects off
their declared lines by ≤ 0.007 m, 16 pins ≤ 0.006 m off the far strip line and 0.000 m off the authored
strip, 328 bridge rings seated by direct hit, 0 interpolated. Prep + split: `loop_race.blend` 25 meshes,
`loop_closure_race_cw.blend` / `_acw` 6 meshes each, problems []. Exported: `check_race_kn5` OK for all three
roles; the cw closure file checked as `acw` or as `common` FAILS. With the road and spawn kn5s exported too, `verify_kn5` passes on the full scratch build (every race START/PIT inside its lane, nearest face 0.48 m — verify_race F's number), and `verify_kn5 --inis` passes on the folder track_folder packed (after the road kn5 is copied in); the same folder with race_cw's ini pointed at the acw closure FAILS twice. Synthetic tests: every new check with a
passing and a failing case (`tests/tools/test_verify_race.py`, `tests/tools/test_check_race_kn5.py`,
`tests/ac/test_verify_kn5_layouts.py`, `tests/tools/test_race_furniture.py`).

| Value | Status |
|---|---|
| `CLOSE_TOL_M` 0.05, `PIN_TOL_M` 0.05, `MOUTH_TOL_M` 0.10, `KERB_CLEAR_M` / `KERB_CLOSURE_CLEAR_M` 0.05, loop-start margin `FOLD_SEARCH_RINGS` + 2 vertices | ⚠ INVENTED |
| `LANE_MARGIN_M` 0.30 = `SPAWN_MARGIN_M` (2026-10-11), car half-width 0.95 | as before |

### Same day — `write_ai_line` inside the race corridors: face refusals walked along the line (ledger 0049, AI)

**Change.** With a version-2 `data/barrier_bands.json` a race layout's AI draft is written inside
`corridors.<id>.lane_by_vertex` (the retired centre chain is never used; a version-2 file without the
layout's corridor, or with no corridors at all, REFUSES; a version-1 file keeps the 0047 lane byte for
byte). The write-time self-check (it refuses to write; it is not one of the four build gates) gains:

| Check | Before (0047) | After (0049 race layouts) |
|---|---|---|
| ruler | the line's POINTS against per-vertex divider / inset channels | every point of the LINE, walked every `CHECK_STEP_M` 0.25 m ⚠ along each 1.5 m segment, against the corridor's two wall FACES as polylines on the walls' own vertex frame (race_furniture's tangent v−1 → v+1, densified 1 m on the declared curve, fold-trimmed at the five inside lips like the strips) — a chord can pass the sharp trimmed corner X much closer than either end point (measured: 0.53 m between two points both ≥ 0.71 m) |
| corridor | — | **refuse** any probe beyond a face (past a closure, in a side street) or < `CHECK_CLEAR_M` 0.6 m from one (funnels, island faces and the trimmed inside corners included) |
| islands | raw `island_w_by_vertex` (no nose taper) | the island as AUTHORED (author_median_blend: NOSE_HALF 0.25 over NOSE_VERTS 3, MEASURED) is an obstacle of its own: **refuse** a probe on it or < 0.6 m from it; the legacy segment check also uses the authored outline for race corridors |
| sealed mouths | — | **refuse** a probe < 0.6 m from a `closed_mouths` mouth line |
| shape | today's fold / turn / radius refusals | unchanged, and apply |

Line-shaping constants (not refusals, all ⚠ INVENTED): lane-centre smoothing `CORRIDOR_MU_M` 25 m;
open-corner outside hold `BOX_APPROACH_M` 60 m, held `BOX_EDGE_IN_M` 0.25 m inside the comfort edge,
slope-limited at `BOX_EDGE_SLOPE` 1:10 (an earlier version chased the 1:3.3 funnel face and put a
58 km/h flick before an 88 km/h corner); box arcs searched from `BOX_R_MAX_M` 150 m down a 0.92 ladder to
the 12.6 m floor fillet, bisected 8 steps, comfort clearance `FILLET_COMFORT_CLEAR_M` 1.5 m first;
corners turning > `BOX_TURN_MAX_DEG` 170° (the hairpin) keep the floor fillet; an arc window never
reaches into another corner's arc.

**Why it is not a bypass.** Every 0047 refusal stands for the street layout and for a version-1 race
declaration (both drafts byte-identical to the installed ones on the scratch copy). For a corridor the
divider/inset ruler is replaced by the faces it approximated, and judged along the line instead of at its
points — strictly more probes, same 0.6 m floor.

**Measured basis (scratch copy of the workshop; barrier_bands v2 on the ledger-0049 config).**
race_cw / race_acw: 0 probes outside / under 0.6 m / on an island; wall clearance minimum 1.48 / 1.49 m;
sealed mouths ≥ 5.85 / 5.72 m; box arcs v0 45.1 / 47.5 m, v1514 28.7 / 52.3 m, v2319 32.8 / 52.3 m, v3297
44.5 / 58.5 m (0047 drafts floor-limited at 12.6 / 10.3 m there); min radius 12.57 / 12.54 m (the
hairpin), min target speed 50.6 / 50.5 km/h; 0 backward steps, 0 self-crossings, 0 steps > 10°; point 0
on the start/finish line. An independent check against the per-vertex declaration (not the writer's
faces) found 0 violations. Tests: `tests/ac/test_ai_corridor.py`,
`tests/ac/test_ai_line_geometry.py::test_a_point_half_a_metre_from_a_closure_face_is_refused`.

| Value | Status |
|---|---|
| `CHECK_STEP_M` 0.25, `CORRIDOR_MU_M` 25, `BOX_APPROACH_M` 60, `BOX_EDGE_IN_M` 0.25, `BOX_EDGE_SLOPE` 0.10, `BOX_R_MAX_M` 150, `BOX_R_LADDER` 0.92, `BOX_R_BISECT` 8, `BOX_TURN_MAX_DEG` 170, box window up to 108 points | ⚠ INVENTED |
| `CHECK_CLEAR_M` 0.6, `FILLET_COMFORT_CLEAR_M` 1.5, `RADIUS_FLOOR_M` 12 | as before (ledger 0047) |
| island nose `NOSE_HALF` 0.25 over `NOSE_VERTS` 3 | MEASURED (tools/author_median_blend.py) |

### Same day — `tools/ship_sd.sh`: the corridor chain wired, per-layout BUILT gates, RACE_RED on containment (ledger 0049, integration)

**Change.** The ship chain now builds and judges what ledger 0049 declares: barrier_bands v2 (with its planned
no_route) → layout_dummies → the author (`RACE` + `RACE_CLOSE_CW` / `RACE_CLOSE_ACW`) → verify_race → plots →
prep → split (road / common race / one closure blend per race layout / spawns) → exports, each kn5
content-checked → spawn kn5s → AI per layout → verify_kn5 → track_folder → verify_kn5 `--inis` → make_map →
make_treefx → the gates per layout → RACE_RED → sync → install (unchanged mechanics).

| Gate / rail | Before (0047 chain) | After |
|---|---|---|
| planned no_route read-back (new, hard) | — | after `barrier_bands.py` (which already exits 1 on a planned leak) the ship reads every race layout's `data/no_route.<id>.planned.json` and stops before Blender unless it exists, is a report, says `fail` false with 0 leak cells, nothing blocked, no probe reached, no spawn unreached. `--no-planned-route` never appears in the ship |
| closure exports (new) | — | per race layout: `loop_closure_<id>.blend` must exist after the split, is exported to `${SLUG}_closure_<id>.kn5`, parsed with `inspect_kn5` to `data/closure_<id>.kn5.json` and judged by `check_race_kn5 --role closure --owner <token>`, the token read from the DECLARATION (`barrier_bands.json corridors.<id>.token`) |
| common race kn5 check | role-free content guard | `check_race_kn5 --role common --bands data/barrier_bands.json` (kerb count pinned to the declaration) |
| `verify_kn5 --inis` (wired) | — | after track_folder AND after the road kn5 is copied into `build/<slug>/` (before that copy it fails, correctly: the ini names a kn5 not yet in the folder) |
| race gate OBJ | ONE `data/track.race.obj` (road + race kn5) for both race layouts | one per race layout: `data/track.<id>.obj` = road + common race + THAT layout's closure kn5 (the set its ini loads) |
| race drive_test / audit | one drive_test call over both layouts on `track.race.obj`; `audit_mesh --race` → `audit.race.json` | per layout `drive_test --layout <id>` → `drive_test.<id>.json`, `audit_mesh --layout <id>` → `audit.<id>.json` (D exempt on that layout's bands only, W hard) |
| no_route BUILT (wired, hard) | — | per race layout, `python tools/no_route.py "$PROJ" --layout <id>` on `track.<id>.obj` → `data/no_route.<id>.json` |
| stale verdicts | the gates read whatever per-layout file was on disk | every `drive_test.<id>.json`, `audit.<id>.json`, `no_route.<id>.json`, `no_route.<id>.planned.json` and `track.<id>.obj` is deleted before the step that rewrites it, so a gate that does not run reads "not run" (red), never last run's pass |
| `RACE_RED` | rows of `drive_test.json` with `kind == race`: `barrier_missing` > 0, `obstruction_stations` > 0, or `fail` null; checked only when some gate exit was nonzero | keyed on the DECLARED race ids (a race layout missing from `drive_test.json`, or no `drive_test.json` at all, is red) + `no_route.<id>.json` missing, `fail` not false, `leak_cells` > 0, or any `blocked` / `forbidden_reached` / `spawns_unreached`; decided FIRST, independent of the other exits, and never overridden by `--force-install`; a no_route exit ≠ 0 (2 = input error) also stops the install |
| sync back | + `audit.race.json` | + `no_route.<id>.json`, `no_route.<id>.planned.json`, `audit.<id>.json`, `closure_<id>.kn5.json`, `race_kn5.json`; the retired `audit.race.json` is removed from the repo copy; gate OBJs (66-78 MB) are never synced |

**Retired.** `data/track.race.obj` and `data/audit.race.json` (removed from the project at the gate step and from
`tracks/san-diego-lake-murray/data/` at the sync). No constant was added: the ship only wires the gates above.

**Measured — the full scratch rehearsal (P7), 2026-10-11.** A fresh copy of the workshop project (minus
`build/`), `SHIP_PROJ=<copy> bash tools/ship_sd.sh --skip-blend`, run twice on fresh copies with identical
numbers (about 5 min each; the workshop `loop.blend` and the AC folder untouched):

| Gate | race_cw | race_acw | street |
|---|---|---|---|
| planned no_route | PASS 0 leaks, 139,130 m² | PASS 0 leaks, 138,826 m² | — |
| verify_race | OK (common + both layouts) | | — |
| check_race_kn5 | common OK (10,283,552 B, 15 strips + 10 kerbs); closure `cw` OK (5,433,534 B, 6 meshes) | closure `acw` OK (5,432,722 B, 6 meshes) | — |
| verify_kn5 / `--inis` | OK / OK | OK / OK | OK / OK |
| drive_test | barrier_missing 0 / 37,869, obstruction 0, severe 0 (soft top 44, floating 391, excursion 1 — inherited counters) | 0 / 37,870, 0, 0 (soft top 40, floating 391, excursion 0) | 82 / 391 / 0 / 101 — identical |
| audit | D 0 / K 158 / I 145 / F 15, W 0 | the same | D 512 / K 154 / I 145 / F 15 — identical, `audit.json` byte-identical |
| no_route BUILT | **PASS** 0 leaks, 0 / 406 probes, lap complete, spawns reached | **PASS** the same | — |
| RACE_RED | not red | not red | — |

The run ends `NOT INSTALLED` (exit 1) only on the inherited street / race drive_test and audit counters, exactly
as every build of this track has; a scratch project is never installed anyway.

**Named, not exempted.** Race K 158 vs the 154 baseline = 4 verts of the new inside kerb `1KERB_race_1514_in`
at v1518: the road there is two `1ROAD` sheets 0.093 m apart (the College/Navajo inside-corner fold, 0033/0046
class); the kerb sits flush on the upper (driven) sheet and K measures it against the lower one (+0.133 /
+0.136 m). Race D 0 vs the street's 512: all 512 are the road kn5's own `1WALL_guard`, every one inside a race
layout's declared band, where `--layout` exempts D by design — the street audit keeps counting them.

**Teeth on the real kn5s.** `no_route --layout race_cw` on road + common WITHOUT the closure kn5: FAIL, 81,466 m²
through 5 doors (4 opposite, 1 island), 390 / 406 probes reached. On road + common + the OTHER direction's
closure: FAIL, 60,266 m² through 10 opposite doors, 311 / 406 probes, the lap blocked in 20 spans. Tests:
`tests/tools/test_ship_sd_chain.py` (stage order, the per-layout gate loop, RACE_RED and the planned read-back
RUN on crafted verdict files — clean passes, every red condition turns red, a missing `drive_test.json` turns
both layouts red).

### Same day — fix round: no kerb under a road sheet, scenery out of the race lanes (ledger 0049, critic round)

**Change.**

| Gate / rail | Before | After |
|---|---|---|
| `barrier_bands` self-gate 9 (kerbs) | exactly 10 kerbs (hard-coded), each clear of every closure | every detected kerb (2 per corner) is either DECLARED or DROPPED (`kerbs_dropped`, each with its why); none both; each declared kerb clear of every closure. `track.config.json race.kerbs.trims` is the only way a kerb leaves or shortens: `{apex, kind, why}` + `drop: true` or `i` / `j` — a PULL-BACK inside the detected run, in walk order. A trim that matches no kerb, names one twice, lengthens a run, reverses it, mixes drop with i/j or carries no `why` FAILS |
| `verify_race` E (kerbs) | declared set == authored set, i/j equal, clear of the authored closures | + no kerb station under another ROAD sheet: the author measures `objects[].under_road` on the real deck (lip, mid-line and outer edge of every 0.3 m station: two ROAD sheets more than 0.02 m apart within 1.5 m, the upper one more than 0.005 m over the kerb's top) and E FAILS any; a declared-dropped kerb that was authored FAILS by name. An authored file without the measure is a warning (pre-fix-round author), never a pass of the check |
| `verify_race` G (scenery, new) | lamp masts only | + every CSP TreeFX trunk (r 0.30 m, INVENTED: palm trunks are 0.3-0.5 m across) and every W1-6 sign post (`signs.local.json base_xz`, r 0.03 m: the 2 in post) against EACH race layout's lane (`lane_by_vertex`, lerped) and its wall footprints (both curb strips; that layout's closure): a disk overlapping the lane or a wall FAILS. Items farther than half-width + 2.0 m (INVENTED) from the centreline are counted, not measured. The trees come from `make_treefx.plan` (every species assumed present: positions only) at author time |
| `ship_sd.sh` scenery re-check (new, hard) | — | right after `make_treefx`: `verify_race --scenery-only --trees build/<slug>/extension/trees/trees.txt` judges the WRITTEN file (kn5 frame x, y, -z flipped back) → `data/race_verify.scenery.json` (synced back) |
| `ship_sd.sh` install guard (new) | — | the REAL install refuses (exit 1) while `acs.exe` / `acs_x86.exe` / `Content Manager*.exe` runs (`tasklist`): the park is a `mv`, which fails half-way on a held folder. Scratch runs never reach it |

**Why.** The critic of the 0049 build: race audit K 158 vs the installed 154 = 4 verts of the new
`1KERB_race_1514_in` at v1518, and `1KERB_race_2319_in` sitting up to 0.44 m UNDER the folded ribbon at the
Navajo/Jackson apex (a red/white kerb vanishing under the asphalt) — no gate failed either. And no gate checked
scenery against the race lanes: two scatter palms (v763 on the hairpin kerb, v4495 at the seam) were kept out
of `trees.txt` only because `make_treefx`'s centreline guard happened to catch them.

**Measured** (scratchpad `corr2/m/kerb_sheets2.py`: every 1ROAD sheet under each kerb station's footprint on the
previous rehearsal's built road kn5): `1KERB_race_1514_in` 18 of 34 stations single-sheet (about 1.5 m each side
of the fold), 13 under the upper sheet (≤ 0.05 m) — DROPPED; `1KERB_race_2319_in` 8 of 51 stations under the upper
sheet by up to 0.42 m, single-sheet pieces 4.5 m on entry and about 5 m on exit, neither at the apex — DROPPED;
`1KERB_race_770_in` (installed since 0047) 13 of 139 stations under the hairpin fold's upper sheet (v764 ≤ 0.04 m,
v774 ≤ 0.14 m) — PULLED BACK to v751-763 (111 stations, all one sheet); `3297_in` has two sheets 0.026-0.028 m
apart at v3298-3299 with its top 0.012 m clear of the upper one — kept, under-road 0. The ribbon folds stay a
named ribbon defect (0033/0046 class) for the ribbon's owner.

**The rehearsal** (fresh copy of the workshop minus `build/`, `SHIP_PROJ=<copy> bash tools/ship_sd.sh --skip-blend`,
14:41:36-14:46:56): every kerb `under_road` 0 (8 kerbs); verify_race OK incl. G scenery (15,261 TreeFX entries +
18 sign posts, 394 beside the race road, 0 in a lane or a wall, nearest 0.655 m — a median bush vs the
closure); the written-trees re-check OK (nearest 0.656 m); race audit K **154** both layouts (D 0 / I 145 / F 15,
W 0); no_route BUILT PASS both; street gates identical to the installed build (`audit.json` md5 `296a2bc1…`).

**Teeth.** `kerb_sheets2.py` on the previous build reproduces the author's reports; `scenery_margins` on the RAW
(unguarded) scatter palms FAILS exactly the two the critic found (v763 lane −0.52 m, v4495 lane −2.18 m, both
layouts). Tests: `tests/tools/test_barrier_bands.py` (the 8 declared + 2 dropped + 770 pull-back; every trim
refusal; neither/both declared-and-dropped), `test_verify_race.py` (E under-road and dropped-but-authored; G
scenery: lane, curb strip, closure, open box, the far tree uncounted; trees.txt frame; the `--scenery-only` CLI),
`test_race_furniture.py` (a dropped kerb leaves its corner), `test_make_treefx_plan.py` (`plan()` is what
`build()` writes), `test_ship_sd_chain.py` (the re-check after `make_treefx`, hard; the install guard).

## 2026-10-11 — side-street mouths: the weld, `verify_mouths`, `verify_race` O hard, the race step check on the whole lane

**Why.** The read-only mouth diagnosis (2026-10-11) on the installed build: `del_cerro_blvd#0` (the W leg, College
v1085, 76.9°, College grade 4.56 %) ended as a LEVEL ribbon square to Del Cerro, so its south corner stood up to
+0.51 m over College 3.4 m inside College's pavement (2.33 m past the race_acw lane face) and its north corner left a
grass notch 0.3-0.6 m below; its sidewalk ran 2.78 m further in at +0.67..+0.75; the prep then pinned a grass
triangle up through College by +0.07..+0.37. Mechanisms: `trim_connectors` took the cut height from the host's
NEAREST vertex; its 30 m blend pulled only the centreline, and never ran when the cut was a piece's START
(`del_cerro_blvd#1` dropped 0.58 m in 2.1 m, `medium#2+0#0#0` 0.33 m in 3.3 m); the assembler sweeps connectors with no
cross-fall; `seat_terrain`'s clamp made a cut end a 14.6 m disc of "connector"; `gap_mouths` sized the sidewalk gap as
if square. None of it failed a gate: the race author listed "another deck above the strip" (0.539 m at v1081) as a
WARNING. The same list carried 0.458 m at Navajo v2314 — not a mouth: the mainline ribbon folding on the inside of the
Navajo / Jackson corner (half-width 12 m round a 7.4 m centreline radius), one of five such folds on the lap.

**Change — gates.**

| Gate / rail | Before | After |
|---|---|---|
| `tools/verify_mouths.py` (NEW; in `ship_sd.sh` hard, right after the street gate OBJ; its stale `data/verify_mouths.json` removed first) | — | every `data/mouths.json` record judged on the BUILT road (`data/track.obj`), heights from its triangles only; HD = the host's lowest 1ROAD sheet ON its centreline, level across. MOUTH LINE: every 1ROAD sheet on the host edge − 0.2 m across the connector's span (where its two edges cross that line, corners 0.75 m in) within **0.05 m** of HD. HOST LANE: over the span ± 3 m, centre to half-width − **0.45 m** on the mouth side (the island excluded), no 1ROAD / 1KERB top > HD + **0.02 m**, no 1GRASS ≥ HD − 0.005 m. NOTCH: at half-width + 0.15 m across the span the top sheet is 1ROAD within 0.05 m of HD. APPROACH: along the connector's centreline and both wheel lines (half-width − 1 m), −3..30 m, the grade over a 2.5 m wheelbase changes ≤ **3 %/m** (the 1 m figure reported beside it), and no 1GRASS within 0.005 m of the road from 0.5 m out (samples of a wheel line folding round a tight corner — plan step off ±40 % — not measured). SIDE: mouths.json's side = the side the piece approaches from. Exit 1 on any FAIL, 2 on an input error |
| `verify_race` O (+ `author_race_furniture_blend.OTHER_DECK_M`) | reported only, at 0.15 m | **HARD**: any strip / kerb ring with another ROAD sheet > **0.05 m** over its base fails; the author records `other_deck_threshold_m`, and an authored file measured looser (or that does not say) fails |
| `drive_test` race-corridor step check | ten wheel paths clamped to ±6 m about the lane middle; the lane-edge paths excluded from steps / kinks; a step at `w ≥ 9.5 and |off| > 3.5` (off the CENTRELINE) reported as an exempt "apron" step — most of a race lane | the WHOLE declared lane, face to face: no 6 m cap, the edge paths gate, no apron exemption inside a declared race lane. Street layout and single-layout tracks unchanged |
| `tools/ship_sd.sh` | `AIROSO` hard-coded | `AIROSO="${AIROSO:-<main checkout>}"` (rehearse a worktree's tools); the weld step; verify_mouths; `mouth_welds.json` + `verify_mouths.json` synced back; the street audit floor re-stated (below) |

⚠ Invented: verify_mouths' 0.05 / 0.02 / 0.45 m are the diagnosis's own numbers; mine are the 0.005 m "grass at the
deck" (the prep pins grass 0.02 m under a deck at its vertices; between them it rose to 0.009 m under College's edge on
the welded mouths), the 0.15 m notch reach, the 0.75 m corner inset, the 2.5 m wheelbase (a 1 m difference on a 3 m-row
triangulated deck reads every row crease as a kink) and the 3 %/m approach limit. O's 0.05 m is the task's.

**Change — geometry** (no gate reads these differently; they are why the gates move). `trim_connectors`: the cut height
interpolated along the host segment; the blend walks FROM the cut whichever end it is; an earlier pass's cut is frozen;
the side is the approach's (`medium#2+0#0` at `del_cerro_blvd#1` v82 was recorded +1 while arriving from −1, so
gap_mouths gapped the far sidewalk and the near one stood across the mouth); mouths.json gains host_seg / host_t /
angle_deg / host_grade / piece / end. `weld_mouths_blend` + `mouth_weld` (NEW, after the trimmed rebuild, before the
seat): refuses unless every connector block equals the assembler's own sweep vertex for vertex; mends every ribbon line
that runs backwards (a swallowtail cut at its self-intersection, the apex at the higher leg's height; a hook replaced by
the cheapest forward chord); mitres each connector end onto the host edge − 0.4 m (road) / the edge (curb); warps road
+ curb + paint by (host deck − level end) × smoothstep(1 − s / 30 m); turns twisted quads to their ridge diagonal;
self-checks before saving. `seat_terrain`: the deck read off the welded ROAD; a cut end no longer seats its host's
pavement; terrain densified to 1.5 m under the welded approaches (0.75 m under a connector corner tighter than 3 ×
its half-width), 0.6 m along the host edge at each mouth, and cleared from under the inside half of each mended
mainline fold (its fan is no plane a 4.5 m grass facet can lie under; densifying it instead put the prep's western
1GRASS tile at 80,362 positions and the prep refused). `gap_mouths`: half-width / sin(angle) + 3 m by arc from the cut's
station, plus the first station past each end.

**Measured — the full scratch rehearsal** (a fresh copy of the workshop minus `build/`, `AIROSO=<worktree>
SHIP_PROJ=<copy> bash tools/ship_sd.sh --no-install`, no `--skip-blend`: median → build → route → divide → trim →
rebuild → WELD → seat → … → gates; 20:27-20:35 on the last run; the workshop `loop.blend` md5 `fbf091e3…` before and
after; nothing installed). Baseline = the installed build of 18:26 (same config, same inputs).

| Gate | installed | this build |
|---|---|---|
| verify_mouths `del_cerro_blvd#0` (W) | FAIL: mouth line 0.534 m, host lane +0.752 m road/curb + 124 grass samples at/above (+0.371), notch 94 / 95 (0.539), approach 19.4 %/m, 11 grass on the approach | PASS: 0.015 / 0.0 (grass −0.006) / notch 0.020 / 1.13 %/m |
| verify_mouths `del_cerro_blvd#1` (E) | FAIL: 0.680, notch 72 / 78 (0.739), approach 33.2 %/m, 25 grass | PASS: 0.016 / 0.0 (−0.009) / 0.016 / 0.98 %/m |
| verify_mouths `medium#2+0#0#0` start (Lake Murray Blvd v4424) | FAIL: host lane +0.124, notch 1 / 34 | PASS: 0.003 / 0.0 / 0.005 / 1.82 %/m |
| verify_mouths `medium#2+0#0#0` end (`del_cerro_blvd#1` v82) | FAIL: SIDE (+1 recorded, −1 real), host lane +0.147, notch 40 / 42 (the host's sidewalk +0.14 across the mouth) | PASS: 0.004 / 0.0 / 0.010 / 0.97 %/m |
| verify_race O (other deck over the strip) | 4 rings, max 0.539 m (v1081-1083 W mouth, v2314 Navajo fold) — then a warning | **0 rings** at 0.05 m; verify_race OK, both layouts |
| race author seating | 17,498 hit / 1 interpolated (the seam) | 17,499 hit / 0 interpolated; deck vs data max 0.463 m (was 0.194: strip rings on the mended fold fans) |
| no_route BUILT race_cw / race_acw | PASS / PASS | **PASS / PASS** (0 leaks, 0 / 406 probes, lap complete, spawns reached) |
| RACE_RED | none | **none** |
| street drive_test soft top / severe / kinks/km / excursions / floating / daylight | 82 / 0 / 4.97 / 101 / 391 / 0 | **42** / 0 / 3.86 / 100 / 391 / 0 (apron steps 22 → 7) |
| street audit D / K / I / F | 512 / 154 / 145 / 15 (826 total) | **512 / 20 / 20 / 13** (565) |
| race_cw drive_test soft top / severe / bumps/km / kinks/km | 44 / 0 / 0.37 / 1.48 | 23 / 31 / 7.42 / 6.45 |
| race_acw drive_test soft top / severe / bumps/km / kinks/km | 40 / 0 / 0.30 / 1.34 | 22 / 28 / 10.24 / 7.57 |
| race audits D / K / I / F, W | 0 / 154 / 145 / 15, 0 | 0 / 20 / 20 / 13, 0 (both layouts) |

**The street audit floor, re-stated** (`ship_sd.sh`'s audit step now says D 512 / K 20 / I 20 / F 13): every K and I
sample was located (scratchpad `classify_ki.py` on both builds). Installed K 154 = 81 at the five mainline folds
(hairpin v763-773 31, Navajo / Jackson 23, v3292-3297 17, the seam 5, College / Navajo 5: the inside sidewalk folded
back over the road), 20 at the mouths (12 at the medium end — the host sidewalk left standing across it —, 6 at the W
mouth, 2 at v4424) and 53 where the connectors' own ribbons fold (the Del Cerro hilltop loop rows 65-85 and 145, the
medium route rows 200-207, `del_cerro_blvd#1` row 240). This build: 0 at the mainline folds, 2 per mouth (the curb
return at each corner, 8) and 12 on the hilltop loop (its outer curb line at rows 72-74 overlaps itself across a
hairpin narrower than the ribbon: the weld reports it "left as built") + `del_cerro_blvd#1` row 240. I 145 → 20 the
same way (81 → 0 at the folds, 19 → 8 at the mouths, 45 → 12 on the connectors). F 15 → 13: two fewer not-flush curb
verts (counted, not located). D 512 untouched (the road kn5's own guard rails, as before).

**Named, not exempted.** The race drive_test moves for two reasons, separated by running each code on each build:
(a) the step check now covers the whole declared lane — the NEW check on the INSTALLED race_acw OBJ finds 94 severe
steps (the W mouth's floating corner at s 10249-10250 up to 0.60 m, the seam, the Navajo fold up to 0.70 m, the hairpin
33, …) where the old one found 0; (b) the geometry — the OLD check on THIS build's race_acw OBJ finds soft top 11
(was 40), severe 2. What the new check still finds on this build (31 / 28) stands on the inside of three mended mainline
folds: the Navajo / Jackson fan (v2310-2329: up to 0.40 m where the low leg's slivers rise to the apex — the legs meet
there 0.5 m apart, which the fold used to hide as a 0.46 m sheet edge), the hairpin fan (v760s) and the seam (v0 /
v4490s); race_acw's 22 soft tops are all on the hairpin (11) and College / Navajo (11) fans. A re-grade of the fan's inside line over
8 rows each side was tried and REJECTED: soft top fell to 6 / 11 but severe rose to 46 / 44, and it lifted the strip
rings 0.69 m off the centreline height no_route bands walls against — 3 doors, 316,424 m² leaked. The fold fans are the
next owner's (ledger 0033 / 0046 class); race severe/km 2.3 / 2.1 stays under drive_test's 12/km.

**Found by the independent verify, not in the rows above.** (1) Street drive_test worst slope kink 11.3 % → **23.7 %**
at s 6946 (v2315, the Navajo fold mend: the overlapping sheet became a crease; new kinks also at the seam, s 11-13) and
bumps/km 0 → 0.15; kinks/km overall still fell 4.97 → 3.86. (2) The OLD race step check on this build's race_acw OBJ
finds 2 new 0.10 m severe steps at s 6535-6536, offset 2.6 m (the Navajo fold) where the installed build had 0 — a
small regression inside the swath that was checked before, against the installed build's hidden 0.70 m fold edge
there. (3) `medium#2+0#0#0` start: a triangle crease on the inside of the connector's own 64° corner, 25-29 m from the
Lake Murray Blvd mouth (slope 5 → 16 %, installed 3 → 11.6 %); verify_mouths leaves a wheel line folding round a tight
corner unmeasured (21 samples on each ±4 m line), so APPROACH does not see the inside of tight corners. (4) HOST LANE
stops 0.45 m inside the host edge and the weld puts the connector's end row at edge − 0.4 m: a raised end row is caught
by MOUTH LINE / NOTCH / APPROACH (all three fired on the verifier's planted defect), not by HOST LANE. **Shipped anyway
(2026-10-11, v0.17.1):** every one is smaller than what it replaced, all are under drive_test's thresholds, and the
drive is the judge; the Navajo fold fan is the next owner's.

**Teeth.** verify_mouths on the installed build: all four mouths FAIL, each where the diagnosis put it.
`tests/tools/test_verify_mouths.py` (a synthetic built road: the assembler's square level end fails mouth line / host
lane / notch, the welded one passes; a wrong side, an approach step, grass in the lane, grass on the approach, the host
sidewalk left across the mouth each fail), `test_mouth_weld.py` (the defect reproduced then mended: every line on the
host edge at the deck, nothing over the host, no fold, the approach under 3 %/m, rows past 30 m untouched; the swallowtail
cut at the legs' crossing, the hook's chord, a U-turn refused; the gap window's skew and its end stations),
`test_trim_connectors.py` (interpolated cut height, the START blend, the frozen cut, the approach side — each fails on
the previous trim), `test_verify_race.py` (O: a 0.458 m and a 0.06 m ring fail, a 0.15 m author threshold fails),
`test_ship_sd_chain.py` (the weld between the rebuild and the seat with the workshop on sys.path; verify_mouths after
the street gate OBJ, hard; the AIROSO default). engine-july is not edited: no file `ship_sd.sh` runs from ENG changed.

## 2026-10-11 — Lookout Lariat P0: `route_oneway_check`, the OSM staleness guard (ledger 0048)

Both landed in 324ec41 / 0e96423 without an entry here; recorded now.

**`tools/route_oneway_check.py` (NEW; not yet wired into a ship chain — the Lariat's P1 chain will run it
before any geometry).** The July route list drove the Lariat's lap ~100 m the wrong way up a one-way at the
US-6 ramp end and 84 m at I-70 exit 259, and no gate could see it: every gate measures the built road, none
asks which way the real road runs. This asks it of the route itself. Per **street** layout (race layouts are
closed roads, not checked), each centreline segment is matched to the OSM way it runs along in the route
stage's own Overpass snapshot (`data/osm.cache.json`); runs against a `oneway=yes|-1` or roundabout way must
lie on a stretch the layout declares (`layouts[].against_oneway` → `divided.stretches[].ways`), every
declared stretch must actually be driven against (a stale declaration FAILs), and a layout that declares
nothing must drive against nothing. Exit 1 on any FAIL, 2 on a usage/config error; `data/oneway_check.json`.

| Item | Value | Flag |
|---|---|---|
| verdict | the real road's direction, from its OSM `oneway` / `junction` tags; `reversible` / `alternating` listed, never judged | [std] |
| `SNAP_M` | 3.0 m — both segment ends within this of the way | ⚠ invented (a matching parameter, not a threshold) |
| `MIN_COS` | 0.7 — \|cos\| between the segment and the way's local direction (~45°) | ⚠ invented (matching parameter) |
| unmatched segments | a segment straddling a junction corner matches no single way: reported as a junction gap, never as a run | |

Proven on the P0 line: Full 0 m against; Reverse 4,486.5 m against on the four declared divided stretches
(D2 (a), Kevin's call), 0 undeclared.

**OSM staleness guard (`scripts/gps/widths_from_osm.py` `OSM_MAX_AGE_DAYS`; also `overpass.py`,
`centerline.py`).** 2026-10-11: overpass.kumi.systems served OSM as of 2026-07-28 while overpass-api.de was
minutes old, and the width/route stages fell back to it without a word. A live Overpass answer whose
`osm3s.timestamp_osm_base` is older than the limit (or carries none) is never written to a snapshot: the stage
stops, naming the mirror and its data date. Per track `route.osm_max_age_days`; one-off `--allow-stale-osm`.
A snapshot already on disk is never judged by age (pinning old data on purpose is what a snapshot is for).

| Item | Value | Flag |
|---|---|---|
| `OSM_MAX_AGE_DAYS` | 7.0 days — healthy mirrors lag minutes to hours; a week behind means the copying stopped | ⚠ invented |
| without a cache path | warns only | |

## 2026-10-11 — paint gate: `tools/verify_centreline_paint.py` replaces the fitter's 1.5 m-from-OSM ceiling (ledger 0048, Lariat P2)

The aerial pass (NAIP 2019, airoso e82ff8c) traced the Lariat's painted centre line. It found the OSM line, which the fitter's position check measured against, 7.6 m off the paint at C4 and 4.8 m at C10. OSM cuts those hairpins. So the ceiling passed fits that missed the real road and failed C9, where OSM was within 0.60 m of the paint. Position is now judged against the paint.

| Gate | Before | After | Flag |
|---|---|---|---|
| `tools/fit_hairpins.py` `max_move_m` | a fitted corner FAILS beyond 1.5 m from the OSM line, both ways; the radius scan picks the nearest radius inside it | **removed**. Status = the step gate only. `lateral_move_m` is reported with `judged_by: tools/verify_centreline_paint.py`. The radius scan picks the nearest radius that passes the step gate. `hairpin_fit.gate.max_move_m` is deleted from the Lariat config | the 1.5 m was ⚠ invented. Measured against the paint, it passed C4 at 7.25 m and C10 at 4.35 m, and failed C9 (2.06 m from OSM, OSM 0.60 m from the paint) |
| `verify_centreline_paint` (a) paint (new) | — | every high/medium yellow point of `data/aerial/paint_traces.json` within **0.75 m**, measured to the nearest segment running the same way (\|angle\| < 60°) | ⚠ invented. Context: OSM scatters 0.74 m rms / 1.35 m p90 about the paint on straight road (862 points). The judged point set depends on the confidence rules in `tools/aerial/traces.py`, all ⚠ invented: a run of >= 4 profiles, within 0.3 m over ±4 m, prominence >= 0.5 × the window's median, drift <= 0.15 m/m; unusable width stations count as low |
| (b) curvature on the climb (new) | the fitter's two rules, on fitted spans only | over `hairpin_fit.climb_st_m` (stations on the OSM source line, via `osm_station_m`): step <= spacing × \|k_local\| × 57.3 + **1°**, where k_local is the line's turn over **±5 m** divided by that window's length; neighbouring steps differ by <= **1.5°**; climb spacing **0.95-1.05 m** | all ⚠ invented. The spacing band exists because the neighbour rule depends on spacing (at 3 m it fails real spirals, denser makes it trivial) |
| (c) topology (new) | — | no vertex turning >= **120°**, no segment < **1 mm**, no crossing of non-adjacent segments | ⚠ invented. The OSM line's largest single step is 78.5°, a junction node |
| (d) closure (new) | — | `coords[0] == coords[-1]` exactly, and the seam vertex passes (b) across the wrap, v[-2] -> v0 -> v1 (L13) | [std: L13] |

Proof:
- `tests/tools/test_verify_centreline_paint.py` (5): 0.3 m passes and 1.0 m fails; a lost leg is not rescued by the stacked opposite leg; facets, curvature jumps and 3 m spacing fail while a 1 m clothoid passes; a figure that crosses itself and a fold both fail; an open seam and a seam kink fail while a smooth lap passes.
- `tests/tools/test_fit_hairpins.py`: a kink with a radius now PASSes and is spliced, its >1.5 m move reported.
- On the Lariat, the OSM line fails: (a) 1,320 points over 0.75 m, worst 7.56 m; (b) 444 step + 971 neighbour + 2,367 spacing fails; (d) the seam neighbour rule, at 1.84°.
- The paint centreline (`tools/paint_centreline.py`) passes all four: worst 0.61 m; 0 / 0 / 0 on 7,114 climb points; seam 2.20° against a limit of 3.16°.

Wiring: not in build.sh or any ship chain yet. It runs by hand after `tools/paint_centreline.py` (Lariat build order: gps -> paint_centreline -> remap_centreline_config --write -> elev). Exit 1 on any fail. Output goes to `data/aerial/paint_gate.json`.

## 2026-10-11 — Lariat P1: a ship chain that isn't San Diego, and the loop prep's three preconditions (ledger 0048)

### The ship chain (`tools/ship_track.sh <track>`, driven by `tracks/<track>/ship.json`)

Wiring only; no threshold moves. `tools/ship_sd.sh` is untouched (byte-identical) and stays San Diego's chain
of record. `ship_track.sh` carries every gate `ship_sd.sh` runs, with the same exit semantics (set -e on the hard
ones; drive_test / audit exits collected; `--force-install` never covers a race layout red on its own gates or a
no_route input error). New in the chain:

| Gate | Where | Exit |
|---|---|---|
| ship.json vocabulary | a step name with no `<phase>_<name>` function in the script, or a value outside `tools/ship_track_spec.py`'s patterns (unknown key, `..`, absolute or shell-shaped path, unknown phase, `prep` other than exactly `[prep, split]`) | 2, before any file operation |
| race furniture declared but not authored | a layout declares `race_furniture` and `steps.author` has no `race_author` | 2 |
| `no blend yet` | no `loop.blend` in the project and nothing in the run can build one (`--skip-blend`, or no available blend builder) | 0 on `--dry-run`, 1 otherwise; nothing synced in |
| Lariat draft: `verify_centreline_paint` + `route_oneway_check` | after `gps -> paint_centreline -> remap_config --write`, before `elev` (the paint gate's "wiring: not in any ship chain yet" above is now wired, for the Lariat) | 1 on FAIL |

Proof: `tests/tools/test_ship_track_chain.py` (19). San Diego parity at airoso 8a2f076: the step headers
`tracks/san-diego-lake-murray/ship.json` selects equal `ship_sd.sh`'s, every branch, in order (static), and a real
`--skip-blend --dry-run` of both scripts on the same scratch copy of the workshop printed identical step headers
(7) and wrote an md5-identical `split_manifest.json` (`37e960f0…` on that scratch path; the manifest embeds absolute paths, so the hash is per-path — the independent verify got `d8c5c490…` for BOTH scripts on another path). The Lariat's route draft
rehearsed with `--draft-only` on a scratch project reproduces `data/centerline.geojson`, `data/centerline.osm.geojson`
and `track.config.json` byte for byte, paint gate and one-way check PASS.

### The loop prep (`scripts/ac/build_kn5_loop.py`, airoso's copy only; engine-july's and the snapshot untouched)

| Gate / guard | Before | After | Flag |
|---|---|---|---|
| 0020 corridor discipline (`_corridor_hash`: kerb faces carved out of carriageways, trunks and canopies cleared from the driving envelope) | built from `data/finished_centerline.json` (KN5 frame, north negated) and queried in Blender's frame: the mainline corridor stood at the north-south mirror image of the road; connectors (local frame) were right | the mainline is un-negated before hashing; mainline, connectors and queries share Blender's (east, north) | a frame bug, no number. `tests/ac/test_build_kn5_loop_prep.py` fails on the old function: a point on the road read 1e9 m from any carriageway, its mirror image read inside one |
| over-cap tiling (`_split_large`) | > 60,000 positions -> K = n // 60,000 + 1 equal-width bands along the longer axis; a band holding a switchback knot overflowed (the FATAL `assert_under_cap` then stopped the build) | > `PIECE_CAP` **50,000** positions -> `balanced_tiles`: halve at the median face centre along the longer side until every piece is <= 50,000 positions | ⚠ 50,000 is invented (the plan's number; 15,535 of headroom under AC's hard 65,535 for the weld and smooth-shading after the split). Proven: a strip + dense knot whose equal bands overflow a 2,000 cap tiles under it by halving |
| terrain seat on stacked legs (L4) | the deck under a ground vertex = the highest road within `LAYER_WIN` 30 m vertically; the contact-band target = the nearest road point in 3D (any leg); the band weight from the nearest road vertex in plan (any leg) | **station matching**: every ground vertex carries the leg + station of the nearest centreline / connector segment in plan (`LegIndex`); it seats only on road triangles of that leg within `STATION_WIN_M` **40 m** of its station (cyclic on a closed lap); the band weight is the plan distance to that leg's footprint. `LAYER_WIN` is gone | ⚠ 40 m is invented. Bounds: a same-leg seat can be off by at most 0.115 × 40 = 4.6 m of grade (the lap's steepest 20 m, -11.5 %), under the smallest stacked gap (6.5 m); on the Lariat's paint centreline every pair of distinct stretches within 30 m in plan is >= **79.9 m** apart in station (closest in plan 19.4 m, station gap 113.9 m at st 5,472 / 5,586). Blender proof on a synthetic switchback (legs 20.5 m apart, 6.5 m road, leg B on a fill): ground vertices 0.3-9 m outside a leg's edge more than 0.5 m off a seat on their own leg: HEAD prep **459 of 3,509, worst 21.11 m**; this prep **28 of 3,509, worst 0.63 m** (the residue is the footprint-distance approximation of the check itself) |

Not changed (no stacked-leg exposure on a road whose legs never overlap in plan): the anti-poke clamp (lowest
drivable sheet within ±20 m, push-down only), the corridor query's 3.5 m / 7 m deck windows (bridges), the props'
terrain-delta ride (±40 m).

Which kn5s these change: only kn5s prepped by airoso's `scripts/ac/build_kn5_loop.py` (`scripts/build_loop.sh`,
and `tools/ship_track.sh` for every track but San Diego). Today that is **none that ships**: San Diego preps with
engine-july's copy (`ship_sd.sh`, and `ship_track.sh` keeps that for SD), the Colorado circuits, rally stages and
Sand Creek build through `scripts/build.sh` -> `scripts/ac/build_kn5.py` (the OBJ program, its own
`_split_over_cap`, untouched), and the only `loop.blend` in the fleet is San Diego's. The first kn5 this prep
writes will be the Lariat's.

**Post-merge fix (independent verify finding).** `LegIndex.neighbour_keys` on a closed lap returned (k−1, k, k+1);
the last chunk is short whenever the lap is not a multiple of `STATION_WIN_M`, so near the seam a point's 40 m window
reached a chunk that set missed (1,010 m lap: station 5 is same-leg with 985, chunk 24, outside (25, 0, 1)). It now
collects every chunk the station interval [start − 40, end + 40] touches round the lap.
`tests/ac/test_build_kn5_loop_prep.py::test_seam_chunks_hold_every_same_leg_station_when_the_last_chunk_is_short`
walks every station pair within the window on such a lap; it fails on the merged code, passes on the fix. No
threshold changed.

## 2026-10-12 — `verify_signs` (k) direction coverage, (j) read from signs.json, race furniture never the signs' ground (ledger 0051)

**Why.** Kevin, from the seat: "arrow signs are only placed for one direction of driving". All signs ship in the one
road kn5 that all three layouts load, and every mainline plate faced the clockwise approach. race_acw drives the lap
anticlockwise, and `verify_signs` passed v0.17.1 anyway, because no check read which directions are driven.

No numeric threshold is added or moved. Every number below is an existing rule constant.

| Check | Before | After | Flag |
|---|---|---|---|
| (k) direction coverage (new) | — | Driven directions come from `<project>/track.config.json` `layouts[].direction` (forward → fwd, reverse → rev; absent or null = forward; any other word FAILs). Every MAINLINE corner with a plate in one driven direction needs, in every other driven direction, either a plate or a skip record EVERY one of whose reasons is the rule finding no arrow corner on that approach (`RULE_SKIP_RES`: R_apex, \|D\|, mouth flare, or the ray never leaving pavement / leaving it out of range / ending at a T / landing outside [PC, PT]) or a signs.json skip with a non-empty reason that signs.json itself still makes for that approach. FAIL: a skip caused by `expect_arrow`; a placement that failed (OUTSIDE ASSERTION, base ON pavement, obstacle disc, lamp clearance: the rule wanted an arrow there); a reasonless signs.json skip; a direction with no record at all. `place_signs` also refuses a signs.json `skip` with no reason at load. | no number |
| (j) expect_arrow | compared the record's own `expect_arrow` with its arrow | Re-read from signs.json here (`--signs`, else `tracks/<slug>/signs.json`). The entry names the FORWARD approach, so a -rev plate expects the mirror image unless the entry's `rev` sub-object names its own. A record whose `expect_arrow` disagrees with signs.json FAILs. An explicit `--signs` that does not exist FAILs. | no number |
| race furniture as ground (new) | `tools/signs_mesh.py` counted `1KERB` (race kerbs included) as ground | `load_bvhs` leaves race furniture out of ground and road: 1KERB_RACE / 1WALL_RACE names, and the RACE / RACE_CLOSE_* collections. `verify_signs` FAILs if the authoring record or its own scan lists one. | no number |

**Proof that the checks bite.** All runs were record-level, on a scratch copy, logs in
`scratchpad/round2/signs/teeth_*.log`.
- (k) FAILs on v0.17.1's record: 5 corners with "no record at all for rev (race_acw)".
- The race-ground check FAILs on the diagnosis's unfiltered authoring run: 8 × `1KERB_race_*`.
- (j) FAILs on a -rev plate given a right arrow.
- (k) FAILs with one -rev plate removed, and again with a -rev skip whose reason is `expect_arrow`.
- Added after review (the reviewer planted `"M4": {"rev": {"skip": true}}` with no reason and the first cut of (k)
  PASSed with race_acw's Jackson/Navajo arrow gone). `place_signs` now exits 1 on that signs.json, and on a blank
  reason. (k) FAILs on records whose M4-rev skip reads `signs.json skip: (no reason given)`, `sign base is ON
  pavement`, `OUTSIDE ASSERTION FAILED`, or a signs.json skip that signs.json does not make. A reasoned
  `"rev": {"skip": true, "reason": "…"}` still places 22 and PASSes. Logs: `scratchpad/round2/signs/fix2/teeth2_*.log`.
- `parse_id` no longer reads a corner named `…-2` (e.g. a merged `DCL-2` post) as a hairpin's second arrow: the
  record's `corner.second_arrow` decides, and for a skip, whether the id minus `-2` was placed.
- The 0051 record PASSes.
- `tests/tools/test_place_signs.py` covers each case on a synthetic square loop.

**Rehearsal.** On a scratch copy of the workshop's `loop.blend` as it is, with 35 race objects present.
- `verify_signs --blend` PASS: 23 posts, 23 plates.
- The 18 v0.17.1 posts moved 0.000 m. Ground was CURB + TERRAIN, with no race kerb in it.

**Who else this reaches.**
- The Lookout Lariat's config declares reverse layouts (street_reverse, race_cw). When its chain gains the signs
  step, (k) will FAIL until its own signs.json sets `both_directions_mainline: true`.
- `place_signs.DEFAULTS` is unchanged (false), so a track with no signs.json still writes the same bytes. This
  was checked on SD with the knob off: the output was byte-identical to HEAD's.

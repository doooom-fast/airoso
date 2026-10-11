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

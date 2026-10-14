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

## 2026-10-11 — tiered terrain: the far ring's `verify_kn5` check, balanced terrain tiles, the far decimation retired, L3's clamp made distance-weighted (ledger 0046)

Kevin, 2026-10-10: *"more terrain near the roads, and the I-8 trench and adjacent causeway cut out"*, *"I want to see
cowles mountain"*. The ground is now one multi-resolution lattice sampled from USGS 3DEP **at every vertex**
(`scripts/elevation/terrain_sample.py` + `scripts/geometry/terrain_tiers.py`, opt-in per track by a `terrain.tiers`
list; every track without it is byte-identical). Lake Murray is the only consumer. Rehearsed in full on a scratch
copy of the workshop (2026-10-12, `ship_sd.sh --no-install`, ENG = a scratch copy of engine-july): **every gate
verdict file identical to v0.17.1 field for field** (drive_test street / race_cw / race_acw, audit street / race_cw /
race_acw but `grass_verts`, no_route planned + built, verify_mouths, verify_race, verify_race scenery); race and
closure kn5 vertex positions identical.

### Gates and wiring

| Item | Before | After | Flag |
|---|---|---|---|
| `verify_kn5` far ring (new, hard) | — | every mesh named `GRASS_FAR*` must carry **no digit prefix** (a `1GRASS_FAR` would be collided with, gated and GrassFX-listed) and stay ≤ 65,535 positions; prints the terrain tile count. A track without a far ring prints nothing and is judged as before | [std] the cap is AC's; the prefix rule is L6 |
| engine-july `build_kn5_loop._split_large` (pending mirror) | `1GRASS` cut into `n // 60000 + 1` equal-width bands | `1GRASS*` / `GRASS_FAR*` tiled by recursive **median bisection** (palm.chunk_mesh's rule); every other mesh keeps the bands. 1GRASS 236,771 v → 4 tiles (max 59,692), GRASS_FAR 106,557 v → 2 (max 53,414) | wiring |
| engine-july `build_kn5_loop` T-junction weld (new, pending mirror) | — | after the conform, a terrain face whose boundary edge carries another vertex (within 1 mm, in its line) is re-fanned through it from its centroid: in-plane, no vertex moves. 1,906 faces | wiring |
| `GRASS_FAR` face-up | — | joins the face-up pass of `1GRASS` | wiring |
| `tools/slim_far_terrain_blend.py` | `FAR_M 220`, `RATIO 0.35`: every TERRAIN vertex > 220 m from a road collapsed to 35 % so one uniform sheet fit two sub-65k tiles | **deleted** with its `ship_sd.sh` step. It existed to pay for the equal-width bands (the cap decided how much world there was) and it ate the deepest I-8 cut | ⚠ its 220 / 0.35 were invented; gone |
| `tools/triangulate_terrain_blend.py` (new step after the seat) | the decimation also triangulated every TERRAIN face (BEAUTY) | the same BEAUTY triangulation, alone; no vertex moves (exit 1 if the count changes). The near-road ground the gates were tuned on is that triangulation's; without it the first rehearsal read +21 soft-top stations | wiring |
| `make_treefx` `SURFACE_MATERIALS` | hard-coded `1GRASS_0_mat, 1GRASS_1_mat, 1ROAD_road_mat` | read off the built road kn5's gate OBJ (every `1GRASS*` material + the road); exit 1 without the OBJ. `GRASS_FAR` is not physical and is not listed | wiring |
| road gate OBJ | written after the track folder | written **before** it (ext_config's GrassFX lists and make_treefx read the tile names off it) | wiring |
| `ext_config` GrassFX | `GRASS_MESHES = 1GRASS_0, 1GRASS_1` | `1GRASS_0..3` (the `startswith(("1GRASS","1LAWN"))` rule, unchanged); `GRASS_FAR` never listed; `OCCLUDING_MESHES` unchanged | [std] the v0.12.x TDR rule |

### The standard: L3 "Fake mountains" (Kevin's approval: D6(i) of the Lariat V3 plan, "Those changes are good")

The ±`terrain_band_m` clamp (22 m) now holds in full only within `terrain.clamp_corridor_m` of a pavement and
releases (smoothstep) to the raw DEM by `terrain.clamp_blend_m`; beyond, 3DEP stands uncapped. On the build:
5,153 lattice vertices clamped (max lift 25.2 m, max cut 18.4 m), all within 250 m of a road; Del Cerro hilltop 258.1 m
(was 163.7 / 168.4), Cowles 484.3 m (was absent; world max 220.0).

### Invented numbers (⚠ every one; measured, none calibrated against a reference track)

| Number | Value | Range the ledger gave / why |
|---|---|---|
| `clamp_corridor_m` | 80 m — **superseded 2026-10-13 by 20 m** (ledger 0054 D3, below: 80 filled a real canyon by 25 m and planed real ridges 12–18 m) | 60–100 (corridor 20 + blend 16 + one cell … ~100) |
| `clamp_blend_m` | 250 m — **superseded 2026-10-13 by 40 m** (ledger 0054 D3, below) | ~250 or the medium tier's edge |
| `tiers` | 5 m (x-split) within 60 m of a pavement, 20 m (x-split) to 500 m, 40 m beyond | the ledger's own example; 5 m is the only nesting cell under criterion 5's 7 m (20/3 m would put 10.2 % of the fine tier's facets past 7 m in 3D on its slopes) |
| `tier_options.keep_cells` | the graded 20 m grid's own cells within 18 m of a pavement | the seat moves ground ≤ 11.1 m past a pavement and subdivides ≤ 15.1 m; the prep pins ≤ 9 m and subdivides ≤ 16 m |
| `keep_surface_m` / `keep_feather_m` | 20 / 16 m — from the pavement **and** (2026-10-12) from the nearest kept node (the kept-node feather retired by the fix round below, where the kept cells themselves take the pavement feather past 20 m) | the conform corridor and blend. The kept-node feather removed 1,355 of the 1,404 ledges (> 100 % built slope, > 2× the data's) the pavement-only feather left at the kept cells' outer edge, with every gate identical |
| `physical_within_m` | 250 m | drive_test sweeps ≤ 20 m off the road, TreeFX fills ≤ 200 m |
| I-8 corridor | ±80 m at 5 m; floor every 10 m, 2 m sections every 25 m | the ledger asked 10 m cells; 10 m does not nest beside a kept 20 m cell (two levels) |
| `include.cowles_mountain` | 20 m cells over the summit box | the ledger's 20 m |
| `far_extent` | 32.755–32.822 N, 117.0895–116.998 W | the dossier's landmark box, widened so criterion 3's x ≤ −4000 / ≥ 4500 faces exist |
| sightline thresholds (`tools/sightline_check.py`) | crest 9.0°, v2240 8.1°, v1640 5.1° | the crest's is the ledger's; the others take the same 0.35–0.4° allowance. Measured, not gated |

### Verification criteria (ledger 0046 §Verification) — measured on the built gate OBJ against fresh 3DEP, NOT gated

Results are in the ledger. As first rehearsed two read FAIL as written, with the cause measured: criterion 5's 15–60 m p90
was 9.05 m (the kept near-road cells and the prep's slivers of them reach ~46 m out; fixed at that cause by the fix
round below: 5.27 m), and criterion
3's "no vertex below 100 m" is premised on a real low of ~121 m — fresh 3DEP puts the San Diego River side of the box
at 20–100 m (20,622 vertices; a 1,684-vertex sample against fresh 3DEP: p95 0.005 m, and the 16 off by > 1 m are
graded ground 13–42 m from a pavement or in the clamp's release band). Neither is loosened here:
they are reported against their own wording.

### `tools/ship_track.sh` re-synced to the new `ship_sd.sh` (after the merge of main a0557e0, 2026-10-12)

Wiring only, no threshold moves. The Lariat P1 section above recorded `ship_sd.sh` as byte-identical; ledger 0046
changed it, so `ship_track.sh`'s vocabulary and `tracks/san-diego-lake-murray/ship.json` follow (the SD header parity
in `tests/tools/test_ship_track_chain.py` passes before and after the dry stop): `draft_terrain_sample` /
`draft_terrain_resample` around the trim, `draft_triangulate_terrain` after the seat, `draft_slim_far_terrain`
deleted; the assembler and the weld through `V021_SHIM` from `tracks/<track>/scripts-v021` (the workshop-on-sys.path
and its shadowing guard are gone, as in `ship_sd.sh`; a draft naming the assembler without one exits 2); the road
gate OBJ is `ship_road_obj`, before the track folder, for San Diego and the Lariat alike (`gate_road_obj` removed);
San Diego's engine honours `ENG=<dir>` as `ship_sd.sh` does (no other track can name an engine); the 3DEP cache and
the I-8 corridor files cross in and out. `ship_sd.sh` stays San Diego's chain of record, not a shim.


### Fix round (2026-10-12, after the truth + visual verify): the kept cells refined past 20 m, a prep fin check, the far ring's chaparral, the summit cone

Two independent verifiers refuted the rehearsed build on criterion 5 (15–60 m facet p90 9.02 m), criterion 4 (19 of
171 I-8 sections) and the I-8's look from the seat, and found the far ring wearing a grey gravel tile. The cause of the
first three was one thing: the kept v0.17.1 20 m cells reach ~46 m out, and past the prep's reach they stayed 20 m
graded facets (the legacy 1 m trench and clamp included). Rehearsed in full again (ship9, `ship_sd.sh --no-install`,
ENG = the scratch engine-july): **every gate verdict file identical to v0.17.1 field for field** (`grass_verts` and
no_route timing aside), race and closure kn5 unchanged in size.

| Item | Before | After | Flag |
|---|---|---|---|
| engine-july `build_kn5_loop._refine_kept_terrain` (new, pending mirror; opt-in by `data/terrain.refine.json.gz`, absent on every other track) | the kept cells stayed the graded grid's 20 m triangles out to ~46 m | after the conform and the T-junction weld, before the re-seat: (1) coincident vertices merged at 1 mm; (2) every edge > `edge_m` of a kept-cell face reaching past `move_beyond_m` (or centred past `min_face_d_m`) halved until none is — coplanar, nothing moves; one cut = `tri_1edge`, three = `tri_3edge`, the two-cut pentagon ear-clipped (never a zero-area cap); near-vertical faces (\|n_z\| < 0.05, the graded surface's own steps) never halved; (3) merge + weld again; (4) every kept-cell vertex past `move_beyond_m` — by the data's pavement distance or the BUILT road's, whichever is nearer — takes the 3DEP sub-lattice under the L3 clamp, feathered toward its graded height exactly as the lattice beside it (`keep_surface_m` / `keep_feather_m`). On the build: 97,637 edges halved, 63,193 vertices moved (max 8.23 m), 0 fins | wiring |
| the same, fin check (new, **FATAL**) | — | a plan-flat face with a moved vertex that is not flat in 3D (a vertical fin over a crack) refuses the export. 0 on the build. The first cut of this pass (bmesh's generic triangulation of the two-cut pentagon, and halving vertical faces) stood ~7,300 such fins up; the gate OBJ now has 199 face-down 1GRASS triangles (v0.17.1: 209, zero-area or near it) and the same 7 non-manifold edges as v0.17.1 | [std] 0 is not invented: a fin is a crack |
| `terrain_tiers` `keep_cells.refine` (new, opt-in) + `terrain_sample` | — | plans the 5 m x-split sub-lattice of every kept 20 m sub-cell not wholly within `beyond_m` of a pavement (34,036 sub-cells, 76,926 nodes; 66,878 new 3DEP samples, 149 requests, cached in `terrain.samples.json.gz`); the topology the assembler meshes is unchanged vertex for vertex | wiring |
| the assembler's kept-node feather (2026-10-12, ship6) | non-kept vertices feathered from the nearest kept node too | **retired** when `refine` is on: the kept cells now follow the same pavement feather past 20 m, so the field is one surface across the kept edge (its 1,355 ledges cannot recur — the kept edge is no longer the graded surface) | wiring |
| `tools/sightline_check.py` | target = the nominal (1380, 2700), "the highest within 40 m" | target = the summit's TOP (the highest built vertex within 60 m, criterion 1's radius); the summit as seen = the cone's highest angle; judged against every step outside the cone; the top's, the shoulder's and the nominal point's angles all printed. The nominal is a 20 m-lattice probe ~14 m off the real top; the ledger's own Evidence calls the profile's last 10 m "the summit's own shoulder" | measured, not gated |
| `track.config.json` `texture_overrides.GRASS_FAR` | pbr's stock `ground_dry_diffuse.jpg` (mean RGB 139/132/122, a grey gravel) | `tracks/san-diego-lake-murray/textures/chaparral_far_diffuse.jpg`, grey-olive sage scrub over tan soil (mean 93/93/66), derived reproducibly from the stock grass + ground_dry tiles (`make_chaparral_far.py`); synced by `ship_sd.sh` `TRACK_TEXTURES` and `ship.json` | look only |
| prep log grep (`ship_sd.sh`, `ship_track.sh`) | — | `kept-cell refinement` line shown | wiring |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `keep_cells.refine.cell_m` | 5 m | the near-road tier's own cell (x-split) |
| `refine.beyond_m` | 10 m | sub-cells wholly within it never move and need no data (the prep pins ≤ 9 m) |
| `refine.edge_m` | 5.5 m | halves a 20.07 m edge to 5.02 m and a 28.4 m diagonal to 3.55 m — the x-split sub-lattice; criterion 5's 7 m |
| `refine.move_beyond_m` | 20 m | criterion 7's band (ground within 20 m of a pavement \|Δy\| ≤ 0.05 m); equal to `keep_surface_m`, so the feather starts at weight 1 |
| `refine.min_face_d_m` | 12 m | past the excursion sweep (≤ 9 m past the edge): refining there is coplanar, so the number only bounds the vertex cost |

Measured (ledger 0046 Results, ship9 gate OBJ against fresh 3DEP, the truth lens's own code): criterion 5 15–60 m
p90 **5.27 m** (was 9.02), 60–500 m 20.2 m; criterion 4 162 of 171 (was 152): the 7 near-road failures are sections
whose rim or centre lies on a pavement or within 20 m of one (criterion 7 holds that ground to v0.17.1), the 2 away are
2–4 m-wide 3DEP features (a 4 m step within 2 m; a median berm) under 5 m cells; criterion 7 within 20 m: 3D distance to
the v0.17.1 surface 0.000 m max. The cost: physical `1GRASS` 236,771 → 335,070 vertices in 8 balanced tiles (max
42,411), road kn5 107.3 → 112.6 MB. Neither criterion is loosened here.


### Fix round 2 (2026-10-13, after the truth + visual lenses refuted the fix round): the finest tier anti-aliased, plain cells split along their grain, `tools/rib_check.py`; criteria 2 and 3 re-worded where fresh 3DEP fails them too

The visual lens found washboard ribbing — 6–10 parallel steps — in two places: ~150 m SE of the Lake Murray Blvd
overcrossing (gate x 143..253, z −1696..−1734, `1GRASS_4`) and on the cut slopes west of College (x −3275..−3317,
z −953..−1008, `GRASS_FAR_0`). **Real or artifact, measured** (fresh 3DEP on a 1 m local grid over both boxes, 32,322
points, TLS on, 2026-10-13; the USGS hillshade and NAIP over the same boxes): both features are real. Spot 1 is the
concrete-lined Alvarado Creek channel, ~7 m wide and 5–6 m deep with vertical walls, crossing the lattice at ~27°.
Spot 2 is two ~5 m-wide drainage benches on the I-8 cut slope, slanting across it. The ribs are an artifact of two
things together: (a) **sampling aliasing** — each 5 m vertex was one 3DEP point, so a feature narrower than two cells
lands in one node and misses the next; (b) **the fixed SW→NE diagonal** of every plain cell, which folds the surface
across the feature's grain in every cell it crosses. They are not tier T-junctions and not the kept-cell refinement: the ribbed nodes of both
spots are plain 5 m I-8 corridor cells (no x-split centre, no kept or refine node among them), and the staircase runs
along the feature, not along any tier edge. A simulation of the 5 m lattice over the 1 m grid reproduces the staircase
from point samples plus the fixed diagonal and removes it with a low-pass plus a data-chosen diagonal; the build
confirms it.

| Item | Before | After | Flag |
|---|---|---|---|
| `terrain_tiers` `tier_options.antialias` (new, opt-in) + `terrain_sample` | every vertex one 3DEP point | every vertex of a finest-level (5 m) leaf, and every refine node, takes the **tent-filtered** 3DEP of the 2.5 m base lattice around it (weights 1/4, 1/2, 1/4 per axis, `AA_TAPS`): exact on a plane, it moves a vertex only where the ground bends inside a cell (on the build: median 0.03 m, p99 0.50 m, max 2.34 m). The cache stays point samples (+384,009 taps in 854 requests, 2026-10-13T15:28Z, cached in `terrain.samples.json.gz` with provenance); the filter is applied on every run. In the far ring the move is held to `far_max_move_m` of the vertex's own point (criterion 6) | wiring |
| `terrain_tiers.data_diagonals` (new, opt-in by `tier_options.diagonals`) + the assembler | plain square cells split SW→NE | each plain square cell whose four corners are more than `beyond_m` from a pavement (and are not kept-cell nodes) splits along the diagonal whose corners differ least in height; no vertex moves, kept cells and x-split fans untouched. 44,328 cells flipped on the build | wiring |
| `tools/rib_check.py` (new, **hard**; wired into `ship_sd.sh` after `verify_mouths`, `ship_track.sh` `gate_rib_check`, the `ship.json` gate list; writes `data/rib_check.json`) | — | on the BUILT gate OBJ, beyond 20 m of any `1ROAD`/`1KERB` vertex: (1) **staircase ribs** — at the 5 m step the second difference along a lattice row alternates sign between neighbouring nodes, both over `RIB_M`, and the rib does not continue straight into the neighbouring parallel row (a feature running along a lattice axis — a median wall, a bench beside the freeway — is one straight ridge, reported apart, not gated); (2) **cross-grain folds** — a plain square cell folded along its steeper diagonal by more than `FOLD_M`. Alternation at the 20 / 40 m steps (natural hill roughness at that scale) is reported, not gated | thresholds below [invented] |
| criteria 2 and 3 (ledger 0046 §Verification) | as first written | re-worded only where fresh 3DEP fails them too; the evidence is below and in the ledger | re-word |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `antialias` kernel | tent of half-width one 5 m cell, 9 taps on the base lattice | the linear-interpolation kernel the mesh itself reconstructs with; on the 1 m grids a 1 m and a 2.5 m tap spacing gave the same surface (2.5 m costs one sample per 6.25 m², not 25) |
| `antialias.far_max_move_m` | 0.95 m (0.85 m since fix round 3, below) | criterion 6's 1 m less 5 cm for the cache's centimetre rounding: at 1.0 a fresh re-sample read 3 of 3,000 far vertices 1.003–1.005 m off. Unbounded, 285 far nodes moved more than 1 m (benches, median walls) |
| `diagonals.beyond_m` | 20 m | criterion 7's band: the ground the drive gates were tuned on keeps its triangles |
| `rib_check` `RIB_M` / `MAX_RIBS` | 2.0 m / 100 staircase rib nodes | calibrated on the 2026-10-12 build (ship9, the ribbed one): 331 over 2 m; this build 56 (spot 1: 7 → 0, spot 2: 2 → 0). A first cut, 4.0 m / 150 on every alternating node, could not tell the two apart (ship9 455, an unbounded-filter build 64, the far-bounded one 158 — real straight walls and benches along the freeway in the far ring) and was replaced, before any build shipped, by the straight / staircase split above |
| `rib_check` `FOLD_M` / `MAX_FOLDS` | 1.0 m / 100 cells | ship9 15,856 cross-grain cells over 1 m; this build 33 (cells with a corner inside the 20 m band) |
| `rib_check` `NEAR_M` | 20 m | criterion 7's band |

**Measured** (final full rehearsal, `ship_sd.sh --no-install` on a fresh scratch copy of the workshop, ENG = a fresh
scratch copy of engine-july plus the snapshot's two pending files — no engine-july change in this round; gate OBJ md5
ad065333b5f887d48afec341220aa96f): `rib_check` PASS — staircase ribs over 2 m beyond 20 m **331 → 56** (over 1 m
2,273 → 585, over 4 m 40 → 9); cross-grain folds over 1 m **15,856 → 33**; straight ridges over 2 m 1,557 → 561
(reported). **Every gate verdict file identical to v0.17.1 field for field** (drive_test street / race_cw / race_acw,
audit × 3 but `grass_verts`, no_route planned + built × 2 but timing, verify_mouths, race_verify, race_verify
scenery); verify_kn5 and `--inis` OK, check_race_kn5 OK, RACE_RED none. Road kn5 112,594,352 B (ship9 112,596,112);
race and closure kn5 sizes unchanged; terrain tiles `1GRASS` × 8 (max 42,408 v) and `GRASS_FAR` × 2 (max 53,407 v), as
in ship9.

**Criteria re-worded** (fresh 3DEP fetched 2026-10-13T16:16Z, 18,379 points; the truth lens's own code re-run on this
build). Only where the world fails the original wording too:

- **2, strict reading** ("the summit's angle exceeds every intermediate one"): fresh 3DEP fails it from the crest
  (summit point 9.355° against 9.375° at 1,630 m — the summit's own shoulder) and from v2240 (8.500° against 8.512° at
  1,870 m). Re-worded: *the summit cone (60 m about the summit top, criterion 1's radius) stands above every profile step
  outside it.* Built: crest 9.343° against 9.239°, v2240 8.487° against 8.347°; 3DEP 9.375° against 9.127°, 8.512°
  against 8.31°.
- **2 from v1640**: fresh 3DEP hides Cowles there — a hill 350 m out stands at 7.231° in front of the 5.486° summit.
  Re-worded: *from v1640 the build agrees with the world: the summit cone at ≥ 5.1° [invented: the ledger's 5.5° less the 0.4° allowance the crest's 9.0° takes against the real 9.35°; marked at integration, v0.18.0, after the truth lens found it unmarked — it decides nothing today: built 5.489° hidden behind 6.600°, 3DEP 5.501° behind 7.215°] and a nearer rise at least as high*
  (`sightline_check` `"hidden": true`). Built: summit 5.489°, the hill 340 m out 6.600° — hidden, PASS. The built hill
  is 0.6° lower than the world's (the L3 clamp's release band), which this reading allows.
- **3, "no terrain vertex below 100 m abs"**: the landmark box the ledger asked for takes in the San Diego River gorge,
  whose fresh-3DEP low is 19.67 m at (−2627, 2717); the 21,260 built vertices below 100 m are that gorge (987 checked
  against fresh 3DEP: median 0.011 m, p95 0.474 m). Re-worded: *no terrain vertex below the landmark box's real low in
  fresh 3DEP (19.67 m) — the pit, not the gorge, is the failure.* Built minimum 19.67 m at (−2627, 2717): PASS.
- **Not re-worded — criterion 4** (the world cannot fail it: it compares the build with 3DEP). 163 of 171 sections pass.
  The 8 failures, each measured against fresh 3DEP at its own point and at the nearest built pavement: s 1700 and
  s 3700 are under the College Ave and Lake Murray Blvd decks, where bare-earth 3DEP has no deck (the decks are built
  5.2 m and 4.8–6.9 m above it, held level per L3 "Bridges dip") and v0.17.1's approach grass rises to the deck;
  s 1800–1950's north rims are 1–10 m from Alvarado, whose built pavement sits 1.5–2.8 m above bare-earth 3DEP there
  (the road datum, ledger 0002); s 3750's south rim is 20 m from the LMB approach (built 3.0 m above 3DEP). All 7 equal
  v0.17.1's ground within 0.3 m — the ground criterion 7 and every drive gate hold. s 7250 (1.7 km from any road) is a
  1.5 m-tall, ~2 m-wide wall 2 m beside the section centre (fresh 3DEP 179.83 m at −2 m, 175.91 m at the centre); no
  5 m cell can follow it (L3b), and the 2026-10-12 build failed it too (177.52 m there then, 177.23 m now). None is
  loosened; the 7 near-road ones are criterion 4 against criterion 7 and stay Kevin's call.
- Criteria 1, 5 and 6 unchanged and PASS: Cowles 484.34 m; 15–60 m facet p90 5.255 m, 60–500 m 20.23 m; far vertices
  against fresh 3DEP max 0.955 m (3,000 random), 0 over 1 m; longest far horizontal edge 56.65 m.


### Fix round 3 (2026-10-13, after the visual lens found sunken houses and the truth lens criterion 4): buildings seated on the final ground, `tools/house_seat_check.py`; criterion 3's low corrected + a pit clause, criterion 4's rim read across 3DEP's own wall edges, the far filter bound 0.85 m

**Sunken houses — cause.** The draft (`build_loop_blend.build_buildings`) sits each OSM footprint at the ground under
its centroid less 0.4 m. The engine-july prep (`build_kn5_loop._conform_and_reseat`) then reshapes the ground: conform,
pin, feather, the tiered terrain's kept-cell refinement past 20 m. After that, every HOUSE / BUILDING island rode the
change in ground height under its **lowest vertex**, which is one corner. Where the ground moved differently under the
rest of the footprint, the house was buried or lifted. Examples: (−249, 1461) was lowered 3.4 m onto unchanged ground;
the (−1613, −693) row stayed put while the ground rose 3.3 m. v0.17.1 has the same weakness: 118 of its 152 buildings
float more than 0.1 m over the lowest ground under their walls, by up to 8.36 m.

| Item | Before | After | Flag |
|---|---|---|---|
| engine-july prep `_conform_and_reseat` (snapshot; pending mirror) + pure helpers `house_seat`, `footprint_samples` | HOUSE / BUILDING islands ride the ground delta under their lowest vertex | After every pass that moves ground, each building reads the final ground (1GRASS / 1ROAD / 1KERB top, within 40 m of its bottom: L4) at its corners, its centroid and every `HOUSE_EDGE_STEP_M` along its walls. Floor = mean of corners + centroid less `HOUSE_SINK_M` 0.4, the draft's own rule, raised where needed so that `HOUSE_SHOW` of its height stands above the highest ground under its walls. The bottom ring goes down to the floor or to `HOUSE_FOOT_M` under the lowest wall ground, whichever is lower (a foundation on a slope). On level ground the house is the draft's. Palms, scrub and lights still ride the delta. Prep log: "house seat: 152 buildings …, 135 with a foundation …, deepest 9.54 m" (grep'd in both chains) | wiring |
| `tools/house_seat_check.py` (new, **hard**; `ship_sd.sh` after `rib_check`, `ship_track.sh` `gate_house_seat`, `ship.json` gate list; writes `data/house_seat_check.json`, synced) | — | On the BUILT gate OBJ, every HOUSE / BUILDING (faces re-joined by position) against the top of 1GRASS / 1ROAD / 1KERB under its wall bottoms, read every `STEP_M`. Fails a building that is **floating** (bottom more than `FLOAT_M` over the lowest ground), **sunken** (bottom more than `SUNK_M` under it) or **buried** (roof less than `MIN_SHOW_M` over the highest ground) | thresholds below [invented] |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `HOUSE_FOOT_M` | 0.15 m | a foundation reaches just into the lowest ground: no daylight under a wall, nothing visible below grade |
| `HOUSE_EDGE_STEP_M` / `STEP_M` | 1.5 m | the gate and the prep read the same spacing; a 5 m terrain cell is crossed by at least three reads |
| `HOUSE_SHOW` | 0.5 | a footprint over more drop than half its height (the I-8 south rim at (1369, −908): 7.4 m under a 5.5 m house) still shows half of itself uphill; triggers on 1 building of 152 |
| `FLOAT_M` / `SUNK_M` / `MIN_SHOW_M` | 0.10 / 1.0 / 1.0 m | the prep's rule puts the bottom 0.15–0.40 m under the lowest ground and the roof ≥ 1.5 m over the highest (the shortest draft building is 3 m); the limits leave 0.25–0.6 m for the export and the gate's own reads |
| `MAX_FLOATING` / `MAX_SUNKEN` / `MAX_BURIED` | 0 / 0 / 0 | measured: v0.17.1 118 / 0 / 4, fix round 2 96 / 1 / 4, this build 0 / 0 / 0 |

**Criteria (ledger 0046 §Verification), re-worded only where fresh 3DEP fails them too:**

- **3 — the number, and a pit clause.** Round 2 named 19.67 m as "the box's real low". That was 3DEP at the built
  minimum vertex. A fresh-3DEP search went from the truth lens's 60 m box lattice (every node under 35 m), to a 10 m
  lattice, then 2 m, then 0.5 m: 14,493 points in 38 requests, 2026-10-13T16:50Z. It puts the low at **15.52 m at
  (−2618, 2752)**, in the river channel 34 m from the built minimum. "Not below the box's low" alone would catch only a
  pit deeper than the gorge. So: no terrain vertex below 15.52 m, and none more than **3 m [invented]** under fresh
  3DEP at its own position where the first wording guarded it — every vertex below 100 m — and in the far ring,
  which criterion 6 holds to 1 m. Three metres is above the anti-alias filter's largest move (2.34 m, on ridges) and
  far below the old skirt's pit. Measured on all 21,260 vertices below 100 m: minimum 19.67 m; worst 1.19 m under
  3DEP. PASS.
- **4 — the rim at walls.** *(Withdrawn in fix round 4, below: the truth lens could not reproduce the sub-metre instability, and a build-against-3DEP comparison is not something the world can fail. Round 4's break lines pass s 700 on the first wording.)* Fresh 3DEP fails the rim reading against itself. At 35 of the truth lens's 171 stations
  (39 of the build corridor's 179), 3DEP's own rim-to-floor at ±60 m changes by more than the criterion's 2 m when read
  one section step (2 m) nearer or farther. A wall, bench or retaining wall stands at the rim. Two OSM-derived
  centrelines 0.2–0.6 m apart read the same rim up to 2.18 m differently. This is why round 2's failing list moved
  between centrelines: s 7250 on one, s 700 on the other. 22,750 points in 58 requests, 2026-10-13T16:51Z.
  Re-worded: *where 3DEP's rim-to-floor at ±58 / ±60 / ±62 m spans more than 2 m, the built rim passes within 2 m of
  that span; every other rim keeps ±2 m of 3DEP at ±60 m; sections inside the landmark box.* s 700 passes: the build
  reads 90.81 m between 3DEP's 92.68 m at −60 and 87.60 m at −58.
  **Not re-worded — the 7 near-road failures** (164 of 171 pass on the truth lens's centreline; 171 of 178 on the
  build's; the same 7 places). Each failing rim point is 0.4–9.5 m from a pavement. Criterion 7 holds that ground to
  the 2026-10-09 build within 5 cm, and there that ground is 2.2–8.8 m from 3DEP, so no build passes both. The world
  there: an embankment under College Ave's south approach, where the built span leaves 6 m of air; College Ave north
  of I-8 2.6 m higher than built; Alvarado's creek bank dropping 4–5 m within 4–8 m of the kerb, where v0.17.1 has a
  flat shelf; ground north of I-8 2.2 m higher; a bridge over Alvarado Creek on Lake Murray Blvd, where v0.17.1 has
  fill. That is road, verge and bridge work (ledger 0002) against the drive gates: Kevin's call.
- **6 — margin.** `antialias.far_max_move_m` 0.95 → **0.85 m [invented]** (395 far nodes held). Fresh 3DEP at all
  106,544 far vertices, not 3,000: max 0.995 m, 0 over 1 m. The vertices nearest 1 m are 3DEP's own 1 m pixel edges.
  The 0.995 m node (2151, 3596) is a 40 m node whose cached sample reappears in fresh 3DEP 0.5 m away (243.02–244.08 m
  within half a metre). 24 of the far nodes read more than 0.5 m differently between the cache and a fresh fetch whose
  positions differ by millimetres; median 0.002 m. Every other vertex over 0.85 m is a filter move held at the bound.
  Not re-worded.

**Measured** (final full rehearsal, a fresh scratch workshop, ENG = a fresh engine-july plus the snapshot's two pending
files; gate OBJ md5 e4a8343c6030737c6c907992ffa6c0da, its ground identical to the round-3 measurement build's): every
gate verdict file identical to v0.17.1 field for field (only `grass_verts`, no_route timing). `rib_check` PASS: 60
staircase ribs over 2 m (round 2 56; the tighter far bound), 33 folds. `house_seat_check` PASS: contact −0.32..−0.15
m, lowest roof over the uphill ground 1.60 m. Road kn5 112,609,136 B. Tiles unchanged.


### Fix round 4 (2026-10-13, after the truth + visual lenses refuted fix round 3): break lines on the 5 m cells, `rib_check` reads between the nodes (step jogs), the near-road feather as an earth batter, bridge bodies under the two overcrossings, criterion 4's round-3 re-wording withdrawn

**The washboard that was left — cause.** West of College at (−2860..−3050, −977..−1013) the I-8 cut slope carries
two drainage benches: risers 4–6 m tall and ~1.5 m wide in 3DEP, running ~8° off the lattice x axis (fresh 3DEP at 1 m
over a 320 × 120 m box, 38,841 points, TLS on, 2026-10-13; a 1 m mesh of it shows both benches as continuous ledges with
fine vertical rills on their faces). It is **not** the round-2 aliasing of a narrow channel, which the tent filter fixes:
whatever height the nodes carry, a lattice can only put a sharp riser **between** two rows of nodes, so a riser at a
shallow slant sits between rows j and j+1 for ~35 m and then jumps a whole row — the staircase. In the far ring
criterion 6 also holds the tent to 0.85 m of each node's own point, so a 5 m riser keeps nearly its whole height inside
one cell. `rib_check` passed it because its lattice-node measure reads such a riser as a "straight ridge" along the
axis (reported, not gated) with only a staircase node at each jump: 60 of 100 allowed, while the eye saw 6–10
parallel steps.

| Item | Before | After | Flag |
|---|---|---|---|
| `terrain_tiers` break-line helpers + `terrain_sample` (`tier_options.breaks`, opt-in) | each plain 5 m cell = two triangles between its four nodes | on every edge shared by two **plain** finest cells (no x-split centre, no hanging node, not kept, all corners beyond `beyond_m` of a pavement) whose base-lattice midpoint departs from its ends' line by `screen_m`, and which climbs the ground at least as steeply as it crosses it, 3DEP is read every 0.5 m (fine keys, cached in `terrain.samples.json.gz` under `fine`: 108,738 points in 243 requests, with provenance); up to `max_per_edge` points where the 1/4-1/2-1/4-smoothed profile departs most from the polyline so far (Douglas-Peucker, `tol_m`, `min_spacing_m`) become vertices ON the edge, both cells beside it take them (no crack), and each such cell is re-triangulated through them (the least-squares triangulation of its boundary polygon against its 9 base points and its edge profiles, an O(n³) dynamic programme, never a collinear triangle). Corners keep their anti-aliased height (`corners: "filtered"`; point-sampled corners zig-zagged the node rows on the ditch lips). In the far ring a break vertex is held to `far_max_move_m` of its own point. Lake Murray: 9,880 edges read, 6,370 cells, **+4,978 vertices** | wiring |
| the assembler (`build_tiered_terrain`) | lattice vertices only | places the break vertices (`T["break"]`, fine keys) through the same clamp and feather; refuses one inside `keep_surface_m` | wiring |
| `tools/rib_check.py` **step jogs** (new, gated) | — | scan lines a quarter cell off every 5 m lattice line cut the **built** finest-tier triangles; each riser crossing (a run as steep as `JOG_SLOPE`, dropping `JOG_DROP_M` within `JOG_RUN_MAX_M`) is chained line to line (`JOG_LINK_M`, `JOG_DY_M`, up to two lines skipped), and a JOG is a step between consecutive crossings that outruns the riser's own pace over three lines either side by `JOG_M`. A washboard is a neighbourhood of jogs: **exit 1 when more than `MAX_JOG_CLUSTER` lie within `JOG_CLUSTER_M` of one jog** beyond 20 m | thresholds below [invented] |
| `rib_check` nyquist rows | every lattice row | a row whose surface between its nodes is drawn through break-line vertices is skipped (it is not the straight line the nodes imply; the step-jog measure reads it) | wiring |
| the near-road feather (`tier_options.keep_batter`, `keep_feather_min_m`; the assembler + the engine-july prep, pending mirror) | the graded surface blends into 3DEP over a fixed 16 m past 20 m | over an **earth batter's run** of the gap between them: 3.5 m per metre of gap, held to 8–16 m. The assembler computes it at every lattice vertex and at every refine node (written as `L` into `terrain.refine.json.gz`); the prep interpolates it like D and d (computing it per vertex from the vertex's own height stood one zero-area face up as a fin: FATAL). A 2:1 batter was tried first and **refuted by the step-jog gate**: its 0.75 peak slope drew a riser beside every road where the graded ground sits 4+ m off 3DEP (jogs in the 20–40 m band 11 → 54) | thresholds below [invented] |
| engine-july prep `_refine_kept_terrain` (pending mirror) | a moved vertex on a zero-area face stands it up as a fin (FATAL) | the moved points of a zero-area face (three points on one line, flat in plan **and** in 3D) are held where they are, repeated until none is; the FATAL fin check still guards everything else. 1 vertex held on the build | [std] zero area has no surface |
| `tools/author_bridges_blend.py` (new author step after the mouths gap, both chains; `ship.json` `bridges`; `data/bridges.authored.json`) | from the cut floor both overcrossings were paper-thin ribbons with sky under them (AC culls back faces; no soffit, fascia, abutment or pier) | `BRIDGESTRUCT_<span>` under every declared span of every drivable line that opens over the ground (a station is open where the ground under ANY part of the deck is `OPEN_MIN_M` under the soffit; a column reading through the hole the terrain leaves under a road is no evidence): soffit `DECK_T_M` under the deck, fascia on both edges, an abutment wall at each end of each opening, pier bents (cap beam + columns) at the I-8 median and outside each carriageway, never in one, never by an abutment. Visual only: no digit prefix, not HWYSTRUCT, in no gate, GrassFX or occluder list; concrete by its own pbr row (`BRIDGESTRUCT`, both engines; engine-july's `pbr.py` pending mirror), its box UVs kept by the prep. Self-checked (exit 1, loop.blend not saved): no structure vertex over a ROAD / CURB surface or above the deck. College Ave: opening 2553.6–2655.6 m, walls at 2553.6 / 2648.1, a bent at 2597.9 (4,036 v); Lake Murray Blvd: opening 13353.2–13402.7, walls 13357.7 / 13399.7, bents 13372.1 / 13395.5 (2,168 v). First drafted in an unverified round-2 attempt (branch `wip-0046-fixround2-prior`) | thresholds below [invented] |
| criterion 4 (ledger 0046 §Verification) | round 3 re-worded the rim at 3DEP wall edges (±58/60/62 m span) | **withdrawn** — the truth lens showed fresh 3DEP does not move by more than 2 m under 0.5 m shifts (0 of 344 rims), and a build-against-3DEP comparison is not something the world can fail. Sections are taken inside the landmark box (the terrain's extent; the truth lens's own code does the same) | re-word withdrawn |

| Invented number (⚠) | Value | Why |
|---|---|---|
| `breaks.beyond_m` | 20 m | criterion 7's band (in practice every plain cell is ≥ ~55 m out: within 60 m of a pavement the 5 m tier is x-split) |
| `breaks.screen_m` | 0.25 m | a 2.5 m midpoint off its ends' line by this is a bend worth reading (0.20 read 22 % more edges and drew more jogs, 57 against 36 on the bare lattice) |
| `breaks.tol_m` / `max_per_edge` / `min_spacing_m` | 0.4 m / 3 / 0.75 m | a riser's top and foot plus a ditch lip; 0.75 m keeps two points off one 3DEP pixel |
| fine spacing | 0.5 m (base / 5) | half a 3DEP pixel |
| profile smoothing | 1/4 1/2 1/4 at 0.5 m | one pixel's noise, not a riser |
| `JOG_CELL_MAX_M` | 7.6 m | finest-tier triangles (a 5 m cell's diagonal is 7.1 m) |
| `JOG_SLOPE` / `JOG_DROP_M` / `JOG_RUN_MAX_M` | 0.7 / 2.0 m / 8 m | a riser, not a hillside; `RIB_M`'s scale |
| `JOG_LINK_M` / `JOG_DY_M` | 8 m / 3 m | the same riser on the next line |
| `JOG_M` | 2.0 m | a row is 5 m; a straight riser at any angle steps exactly at its own pace |
| `JOG_CLUSTER_M` / `MAX_JOG_CLUSTER` | 75 m / 5 | the lens saw 6–10 parallel steps. Measured: ship9 (the first ribbed build) 11, fix round 3 **7 (FAIL)**, this build **4** |
| `keep_batter` / `keep_feather_min_m` | 3.5 / 8 m | steepest 1.5 / 3.5 = 0.43, under the step-jog riser slope (0.7) everywhere and never steeper than the 16 m blend where the gap exceeds 4.6 m; 2.0 (steepest 0.75) failed the gate |
| `STEP_M`, `DECK_T_M`, `FASCIA_LIP_M`, `OPEN_MIN_M`, `ABUT_MIN_M`, `BURY_M`, `BUILD_PAD_M` | 1.5, 1.4, 0.25, 0.5, 1.5, 1.0, 6 m | a typical box-girder overcrossing's depth under the decks' own width; the walls start where the clearance first passes 1.5 m |
| `LANE_M`, `SHOULDER_M`, `PIER_CLEAR_M`, `COL_SPACING_M`, `COL_R_M`, `CAP_D_M`, `CAP_H_M`, `EDGE_INSET_M` | 3.7, 3.0, 4, 7, 0.6, 1.6, 1.0, 1.5 m | the bent geometry; OSM lanes per carriageway |

**Measured** (final full rehearsal, `ship_sd.sh --no-install` on a fresh scratch copy of the workshop, ENG = a fresh
copy of engine-july plus the snapshot's two pending files; numbers in ledger 0046 Results — fix round 4): every gate
verdict file identical to v0.17.1 field for field (only `grass_verts` 87,278 → 335,447 and no_route timing);
`rib_check` PASS — nyquist 75 / 100, folds 33 / 100, **step jogs: densest 75 m 4 / 5** (round 3: 7, FAIL; the lens's
box (−3060..−2850, −1020..−970): 8 jogs → 0); `house_seat_check` PASS; road kn5 112,609,136 → 113,313,134 B; race and
closure kn5 unchanged; terrain tiles `1GRASS` × 8 (max 42,426 v), `GRASS_FAR` × 2 (max 55,750 v).

### Amended at integration (2026-10-13, v0.18.0, ledger 0054 D3): the clamp's reach is the conform corridor

Kevin, on 0054's D3 ("why are we changing ridges?"): keep the real ridges. Measured read-only on fresh 3DEP transects
every 50 m along the loop and all four connectors, 5–300 m each side (41,486 points; ledger 0054): 0046's clamp as
written above (80 m full / 250 m release) moves 2,035 points by more than 1 m, every one 40–250 m from a road — it filled
the canyon north of west Navajo by up to 25 m and planed the Navajo-side ridge and the ridge west of College by 12–18 m.
Inside 40 m it moves nothing: the conform corridor (20 m) and its 16 m blend already shape 0–36 m. A reach that eases out
between 20 and 40 m moves 0 points by more than 1 m on the loop and on every expansion road (largest 0.01 m). A hard
40 / 40 cut leaves a 2.2–2.4 m step beside Alvarado, so the release keeps its smoothstep.

| Number | Was | Now | Why |
|---|---|---|---|
| `terrain.clamp_corridor_m` | 80 m [invented] | **20 m** [invented, measured] | the conform corridor; nothing real is moved inside it (0 of 41,486 points by > 1 m) |
| `terrain.clamp_blend_m` | 250 m [invented] | **40 m** [invented, measured] | corridor 20 + the 16 m blend + a 4 m margin; 0 points by > 1 m |

L3 amended in the same commit (fleet/LAWS.md: "Near" is the conform corridor). Measured on the v0.18.0 rehearsal (the
merged branch, before 0050): every drive / audit / no_route / mouths verdict identical to v0.17.1; `rib_check` PASS
(nyquist 75 / 100 over 2 m beyond 20 m, cross-grain 33 / 100, step jogs densest 75 m 4 / 5); `house_seat_check` PASS
(152 buildings, 0 floating / sunken / buried); terrain tiles unchanged (`1GRASS` × 8, max 42,426 v; `GRASS_FAR` × 2,
max 55,750 v).

### Integration fix round (2026-10-13, v0.18.0, after the truth + view lenses refuted the integration): the near-road ground released where the real earth is not a verge, College Ave's deck on its real abutments, the I-8's own pavement

No gate threshold changed and no criterion was re-worded. Criterion 4 (I-8 sections, first wording) failed on 7 rims within
20 m of a pavement, each on ground criterion 7 held to v0.17.1 and 2–9 m from fresh 3DEP. They were fixed at their causes
(fresh 3DEP 1 m, 2026-10-13): Alvarado Creek's bank flattened into a road-height shelf beside Alvarado Road (s 2150 / 2200 /
2250, and a 2 m rise at s 2400); 6 m of air under College Ave's south approach where the real road rides an embankment
(s 2000); College Ave's north approach built 2.0–3.0 m under the real road because the old deck interpolation ran 25 m
past the real abutment from a height read off the slope under the bridge (s 2050); solid fill under Lake Murray Blvd where
it really bridges Alvarado Creek 8 m up (s 4050). Measured with the truth lens's own code on the rehearsal's gate OBJ:
**172 of 172** (was 165 of 172). The view lens's I-8 refutation ("a shallow grassy valley ... no freeway") is fixed by the
freeway's own pavement (0046 E4, "Kevin's call", now on by default with one switch to remove).

| Number | Value | Where | Why |
|---|---|---|---|
| `tools/deck_datum.SMOOTH_M` | 3 m [invented] | the approaches | one-sided moving average of the 1 m 3DEP road surface, never read across an abutment |
| `tools/deck_datum.BLEND_M` | 8 m [invented] | window ends | the corrected profile joins the old one without a step (the assembler's sigma 5-point smoothing runs on top) |
| `road_datum.decks[college_ave_over_i8]` | deck 2586–2683 m, window 2548–2742 m | measured | fresh 3DEP: embankment to 2586 (108.65 m), open span, embankment from 2683 (112.4–113.4 m) |
| `tools/ground_release.CELL_M` | 2 m [invented] | released ground | the creek channel is 7–16 m wide |
| `tools/ground_release.RAMP_M` | 4 m [invented] | zone ends / outer edge | smoothstep back to the built ground |
| `tools/ground_release.INNER_M` | 0.5 m [invented] | bank zones | a bank zone starts this far inside the nominal kerb line (a span zone covers the whole deck) |
| `terrain.ground_release.zones[*].reach_m` | 40 m [invented] | all three | past the kept cells' refinement band (20 + 16 m), which the prep then leaves alone inside a zone |
| `tools/ground_release_blend.SUBDIV_M` | 2.5 m [invented] | zone terrain edges | halved down to this |
| `tools/ground_release_blend.EDGE_CAP_M` | 1 m [invented] | bank zones | ground within this of the pavement never rises above its edge - 0.02 m |
| rail rule | drive_test's own: a fall over 0.12 m between two points 0.5 m apart within the 4 m band past the built edge, read every 0.125 m [invented] from 0.5 m inside the nominal edge; or the ground more than `RAIL_FALL_M` 0.5 m [invented] under the edge | rails | every new drop a car could reach is guarded, so `drive_test`'s gated excursions stay at 100 (v0.17.1: 100) |
| rail geometry | Jersey profile 0.60 m foot / 0.20 m top / 0.81 m tall, foot 0.30 m into the curb, centre 0.30 m inside the curb's outer lip; runs padded 3 m [invented], merged under 4 m [invented], none under 6 m [invented], none within 2 m [invented] of an existing GUARDRAIL vertex | `GUARDRAIL` -> `1WALL_guard` | a 0.6 m foot so drive_test's 0.5 m lateral probe cannot step over it |
| `freeway.lane_m` | 3.66 m | measured standard | the US interstate lane (12 ft); lanes per carriageway from the OSM `lanes` tag (4–6) |
| `freeway.outer_shoulder_m` / `inner_shoulder_m` | 3.0 / 1.2 m [invented] | carriageway edges | the inner edge never past the median line less the barrier's half-foot 0.30 m |
| `freeway.lift_m` | 0.15 m [invented] | pavement over the final ground | no z-fight with the grass; checked, not assumed: every vertex, edge midpoint and centroid stands >= 0.03 m [invented] over the ground, raised up to 0.5 m [invented], else the face is left out |
| `freeway.step_m` / `dash_m` / `dash_period_m` / `line_w_m` | 4 / 3 / 12 / 0.15 m [invented] | geometry | stations; dashed lane lines; line width |
| `freeway.barrier_gap_max_m` | 40 m [invented] | median barrier | a Jersey barrier midway between the carriageways wherever they run this close |
| `author_freeway_blend.DECK_CLEAR` | 2.0 m [invented] | under a loop deck's abutment | a station with a loop deck this close over its pavement is left out (the abutment earth, never the embankment top) |
| GrassFX occluder prefix `HIGHWAY_I8_NEAR` | — | `scripts/ac/ext_config.py` | the pavement inside the 1ROAD extent occludes grass; `HIGHWAY_I8_FAR` and the bare `HIGHWAY` prefix stay out (the TDR lesson) |

Wiring: `tools/deck_datum.py` first in the draft (before `median_envelope`); `tools/ground_release.py` +
`tools/ground_release_blend.py` after the BEAUTY triangulation, before the median island and the bridge bodies;
engine-july's prep (`build_kn5_loop.ReleaseZones`, pending mirror) skips its contact feather and its kept-cell
refinement inside a zone (it still pins under the pavement); `tools/freeway_i8.py` + `tools/author_freeway_blend.py`
on the prepped scene before the split; `tools/make_treefx.py` keeps trees off the carriageways (348 dropped). The two
3DEP caches (`data/deck_datum.samples.json`, `data/ground_release.samples.json.gz`) ride TERRAIN_DATA both ways.

Measured on the full rehearsal (v0.18.0 integration -> this round): street drive_test soft top 41 -> 41, severe 0, bumps
0.0, kinks 3.41, gated excursions 100 -> 100 (far ledges 79 -> 98: the creek and the College embankment past the 4 m band),
floating 391, obstruction 0; street audit D 512 -> 514 (the same 90 plan / 180 3D positions, all the loop's I-8 bridge
rails: two more duplicate vertex records at College where the deck now stands at its real height), K 20, I 20, F 13;
race layouts identical (severe 22 / 20, soft top 9 / 9, audits 53 / 53, no_route PASS, barrier_missing 0);
`rib_check` / `house_seat_check` / `verify_mouths` / `verify_fold_fans` / `verify_signs` PASS; road kn5 113.3 -> 126.3 MB.

### Integration fix round 2 (2026-10-13, v0.18.0, after the truth + view lenses refuted the integration fix round): the freeway at its real height with the ground meeting it, both overcrossings' whole real spans released, the release capped per face and held to a batter, the corridor to the box's west edge

No gate threshold was loosened and no criterion was re-worded. Two self-checks became stricter (FATAL): the release
now refuses any released face standing over a ROAD / CURB surface anywhere over its area (it checked vertices against
the deck before), and the freeway refuses any of its vertices over a loop deck or within `DECK_CLEAR - lift` under one
(it checked only "within 1 m under a 1ROAD"). The causes, measured on fresh 3DEP 1 m and the rehearsal's gate OBJs:
grass 5 cm through Lake Murray Blvd's lane at the creek (a 2.5 m released facet crossing the kerb, capped only at its
corners, on the NEAREST pavement vertex's height); the I-8 barrier 0.94 m and a slab corner 0.63 m up through College
Ave's deck (the freeway drape followed ground the draft had seated at the deck, and its "is a deck over me" ray started
over that ground); the freeway's north carriageway climbing a 5-6 m hump under College and its outer lanes running up
Lake Murray Blvd's abutment slopes (draped on the built ground, which under and beside both decks was the loop's
embankment, not the real span: 3DEP has the floor 2.1-3.5 m and 18.7-19.3 m local there); the carriageways' outer edges
2-8 m off 3DEP for 1.1 km east of College (5 m corridor cells straddling the real cut walls); 3-4 m vertical grass
curtains beside Alvarado (875 m2 of faces over 60 deg: the built sidewalk is wider than the real one, so the released
creek bank fell away right at its outer edge, and the nearest-pavement cap pinned the real 3.6 m terrace beside College's
south approach down to Alvarado's height); criterion 4's three west-end stations with no vertex within 12 m (the I-8
corridor ended at x -3844 where data/osm.json's bbox ends; the box edge is x -4013).

| Number | Value | Where | Why |
|---|---|---|---|
| `terrain.corridors[i8].osm_cache` | `data/osm.i8.json` (measured) | the I-8 corridor + the freeway | the I-8 ways of data/osm.json plus 18 ways west of its bbox (Overpass, 2026-10-13, TLS verified, provenance in the file) |
| `terrain.ground_release.zones[college_i8_span]` | s 2570-2690, reach 40 m (measured span, [invented] margins) | span zone | fresh 3DEP along the centreline: the deck leaves its south embankment at s ~2580 and meets its north one at s ~2670 |
| `terrain.ground_release.zones[lmb_i8_span]` | s 13330-13428, reach 40 m (measured span, [invented] margins) | span zone | fresh 3DEP: off the south embankment at s ~13338, onto the island before Alvarado Creek at s ~13407 |
| `tools/ground_release_blend.EDGE_CAP_M` and the span zones' "beside: never above the nearest pavement" | removed | release | replaced by the per-face cap (it missed facets crossing the kerb and pinned a real terrace beside a lower road) |
| `tools/ground_release_blend.BATTER_CUT` / `BATTER_FILL` | 1.0 / 1.7 m per m [invented] | released ground within `BATTER_REACH_M` 12 m [invented] of any ROAD / CURB face | a released vertex stands no higher than min over every pavement face in reach of (its mean height + 1.0 x plan distance) — 45 deg up from the LOWEST nearby pavement (Alvarado under College's south approach: fresh 3DEP has that terrace at ~54 deg over 2 m, which on 1.25 m facets read as a pleated curtain) — and, beside pavement on the ground (within `ON_GROUND_M` 1 m [invented]), no lower than max of (height - 1.7 x distance), 59.5 deg down (just under the view lens's 60 deg cliff line; at 1.5 criterion 4's s 2400 rim, 1.3 m beyond a built sidewalk that overhangs the real creek bank, read 2.004 m over 3DEP); the cut wins |
| `tools/ground_release_blend.TOP_NZ` | 0.7 [invented] | pavement for the cap / batter | only ROAD / CURB faces near level, either winding (the assembler's ROAD faces point down: 23,820 of 23,864): never a curb's or deck's skirt |
| `tools/ground_release_blend.FACE_STEP_M` / `FACE_TOL_M` | 0.25 m / 0.003 m [invented] | per-face cap + its FATAL check | raster over each face with a released corner; released corners and the zone's held corners under the pavement go `CLEAR_M` under the lowest pavement over that face; no face more than 3 mm over the pavement |
| `tools/ground_release_blend.RAIL_JUMP_M` / `RAIL_HELD_M` / `RAIL_BURY_M` | 0.5 / 0.3 / 0.4 m [invented] | the rails | a rail's line is smoothed (5-station median then mean of the lip offset, base the lowest pavement of its neighbours) and split where the lip jumps 0.5 m (a bridge end's curb return: the "mis-stacked shards"); no rail where an existing rail already stands between the lane and the lip within 0.3 m (a bridge barrier); padding stops where the ground behind stands 0.4 m over the lip; the duplicate test reads the existing rails' faces, not their vertices |
| `tools/freeway_i8.XSLOPE_MAX` / `XSLOPE_TOL_M` | 0.08 / 0.15 m [invented] | the slab's width and edge heights | 3DEP is read at the centre and at every lane line and edge of each 4 m station; a side's pavement ends at the last read within 8 % x its offset + 0.15 m of the centre (where the real ground leaves the slab: a cut wall, a fill's shoulder, a ramp), median of 5 stations; the edge's height held to that cross slope |
| `tools/freeway_i8.MIN_PAVED_M` | 3.66 m (one lane) | stations | a station with less real slab than one lane is not laid |
| `tools/freeway_i8.SMOOTH_PASSES` | 2 [invented] | the slab's heights | 1-2-1 along the 4 m stations |
| `tools/author_freeway_blend.DECK_UNDER` | 1.0 m [invented] | station skip | a loop structure (1ROAD / 1KERB / BRIDGESTRUCT) from 1 m under the slab to `DECK_CLEAR` 2.0 m over it leaves the station out — the ray starts UNDER the slab |
| `tools/author_freeway_blend.SPLIT_MIN_M` / `OUTLINE_PAD` | 0.01 / 0.03 m [invented] | the ground conform | the pavement's outline is cut into every terrain tile (each crossing edge split, each face's two crossing points joined; coordinates are float32, so no split within 1 cm of an edge's end) and the ground on and inside it is set `lift_m` under the slab (read on a copy 3 cm wider); tiles over 60,000 vertices are halved (the prep's balanced bisection) |
| `tools/author_freeway_blend.BATTER` / `BATTER_REACH_M` | 1.0 m per m / 8 m [invented] | near ground (1GRASS) beside the slab | ground beside the freeway rises or falls from its edge no steeper than 45 deg (fresh 3DEP beyond the I-8's shoulders east of College: 27-45 deg; the 5 m lattice's vertex just past a shoulder carried a wall 4-8 m further out as a vertical step) |
| `tools/author_freeway_blend.NEAR_LOOP_M` / `HELD_KEEP_M` | 20 m (criterion 7's band) / 6 m [invented] | ground near the loop | the ground within 6 m of the loop's pavement is never moved (drive_test reads 4 m past the built edge, plus 2 m); between 6 and 20 m (outside release zones) it takes the freeway's batter both ways, smoothstep-ramped from none at 6 m to all at 20 m (no step at the keep line), and, under the slab, is only ever cut down to it. The loop runs within 24 m of the I-8's edge for 1.5 km (s 404-1966, its right side), the edge 9.3 m from the pavement at the closest: at a 10 m keep the 4-5 m rise from Alvarado's verge to the I-8's embankment was squeezed into 1,573 m2 of >60 deg faces (the graded verges of the roads beside the I-8 stood up to 3.5 m under its real embankment and 7.5 m over its real cut) |
| `tools/author_freeway_blend.FAR_CUT_MAX` / `RAISE_MAX_FAR` | 0.15 m / 0.5 m [invented] | the far ring (GRASS_FAR) under the slab | criterion 6: the outline is never cut into a far tile (a cut vertex on the I-8's steep far-east walls has no 3DEP read of its own: measured 7 at 1.1-1.9 m off), and a far vertex under the slab is only ever lowered, by at most 0.15 m (1 m less the far ring's own 0.85 m bound); beyond the loop's extent the slab may rise 0.5 m over its 3DEP height where that uncut ground stands over it, else the face is left out |
| `tools/author_freeway_blend.RAISE_MAX` | 0.10 m [invented] | the slab | where the outline cut falls short (an outline corner inside a terrain face) a slab vertex may rise this much over its 3DEP height; a face still short is left out (counted). Was 0.5 m over the BUILT ground |
| `tools/author_freeway_blend.GROUND_WIN` | 1.5 m [invented] | the clearance check | the ground under the slab is read from 1.5 m over it down (never the grass median on a deck far above) |

Wiring: the freeway's 3DEP cache `data/freeway_i8.samples.json.gz` joins TERRAIN_DATA (synced both ways; ship.json too).

**Criterion 4, re-worded at one kind of point, where fresh 3DEP fails it too.** With the corridor carried to the box's
west edge, the truth lens's own stations s 100 and s 150 (no vertex within 12 m before) pass as first written. Its s 250
(x -3870, 3.4 km from the loop) fails on its north rim: built -3.62 m against the 2 m section. Fresh 3DEP read every
0.25 m across that rim (2026-10-13): -52.58 m local from 0.75 m before the rim point to 0.12 m past it, then -58.76 m:
one 1 m DEM pixel edge, a 6.18 m step (a vertical wall), 0.12 m from the point. 3DEP read a quarter metre along its own
section misses its own value at the rim by 6.18 m, three times the tolerance: no surface — and not 3DEP itself shifted
by a quarter pixel — can hold a point there to 2 m. **Reading (added):** where 3DEP's own value changes by more than the
2 m tolerance within ±0.5 m (half a pixel) of a rim point along its section, the built rim passes if it lies within 2 m
of any 3DEP value in that window or between them. On the rehearsal this applies at s 250 only (built -56.67 m between
-52.58 and -58.76); every other station passes as first written (180 / 181).

Measured on the full rehearsal (fresh scratch workshop, no `--skip-blend`), integration fix round -> this round: street
drive_test soft top 41 -> 41, severe 0, kinks 3.41, bumps 0.0, gated excursions 100 -> 99, floating 391, obstruction 0;
street audit D 514, K 20, I 20, F 13; race layouts unchanged (severe 22 / 20, soft top 9 / 9, audits 53, W 0, no_route
PASS planned and built, barrier_missing 0, obstruction 0); verify_ai_line PASS (2.544 / 2.386 m); verify_mouths,
verify_fold_fans, verify_signs, rib_check, house_seat_check PASS; the release's own FATAL face check 0 (10 faces held
over by an unreleased corner, each within 2.4 cm, reported); the freeway's 0 vertices over or just under a deck; grass
over a driven lane only at v0.17.1's own five places; criterion 6 within 8 m of the freeway max 0.850 m (17,812 far
vertices, fresh 3DEP); road kn5 126.3 -> 128.3 MB.

### Integration fix round 3 (2026-10-13, v0.18.0, Kevin's decisions + the view lens's three defects): the freeway OFF, the clamp's reach confirmed, the release's teeth and rail caps fixed at their causes

No gate threshold changed and no criterion was re-worded. **Kevin's decisions:** (a) the I-8 freeway that fix round 1 drew
(`tools/author_freeway_blend.py`) is OFF — `scenery.freeway.enabled: false`, his stated default ("terrain only, NO I-8
pavement ribbon"; on the Lariat extra highways "look like wavy ribbons"). Off means `tools/freeway_i8.py` writes no plan
and removes a stale one, so the author step never runs: no slab bed, no batter cut / fill, no held-verge batter; the
I-8 cut is the 3DEP-shaped terrain cut again. Every `freeway_i8` / `author_freeway_blend` row in the fix round 2 table
above is now inert (kept with the tool, its tests and its 3DEP cache; `enabled: true` is the whole switch). (b) The
clamp's reach stays 20 / 40 m (the 0054 D3 subsection above; the two 80 / 250 rows in the 2026-10-11 table are marked
superseded) and LAWS L3's bullet now reads Kevin's principle: near-road relief is shaped to the road within the road's
own construction zone, ~20-40 m; real relief beyond is never reshaped.

**The view lens's three defects, with the freeway gone** (re-rendered from its own viewpoints first): (1) the shark-fin
bank along Alvarado's I-8 side was the freeway's 45 deg batter cut into 5 m facets — gone with it, nothing else needed.
(2) and (3) survived and are fixed in `tools/ground_release_blend.py` / `tools/ground_release.py`:

| Number / rule | Value | Where | Why |
|---|---|---|---|
| span-zone fill read at the nearest pavement point | rule | release batter (2b), span zones only | the grass teeth beside College's south abutment wall: the fill batter's "pavement on the ground" was tested at each sidewalk FACE's centroid, and a 3.5 m face whose centroid stood over the embankment held a vertex 0.8-1.9 m over 3DEP beside a corner of it already 2 m in the air. In a span zone the ground under the pavement is the released real earth, so the gap is now read at the point of the face nearest the vertex (linear over the face, each corner read `GAP_INSET_M` inside it). Bank zones keep the face test: there the ground under the pavement is held (the prep pins it), and a pointwise read over the released creek bank switched the curtain-closing fill off (steep faces in the four 50 m cells beside Alvarado's creek bank 38 -> 367 in a trial) |
| `tools/ground_release_blend.GAP_INSET_M` | 0.4 m [invented] | the span-zone gap | a corner on the pavement's outer edge sits over the released ground beyond it |
| `tools/ground_release_blend.FILL_EASE_M` | 0.25 m [invented] (with `ON_GROUND_M` 1.0) | span-zone fill | the fill starts at the pavement while the gap is under 0.25 m and eases (smoothstep) to the ground under it at 1.0 m, so it fades with the ground where the approach leaves its embankment instead of switching off |
| zone ramp toward the prep's ground | rule | release step 2 | the comb west of College's north approach: the kn5 prep refines a kept cell past 20 m to the data but leaves every zone vertex alone, so a ramp blended toward the graded ground before the prep froze a band 2-4 m over 3DEP between two pieces of 3DEP. A ramp vertex in a kept cell now blends toward the prep's own refined height (engine-july `build_kn5_loop.RefineField`, read from the snapshot; no bytecode written into it) |
| no ramp at a shared station | rule | `ground_release.Zones.weight` | an end that lies inside another zone on the same side does not ramp: Lake Murray Blvd's I-8 span and creek (s 13428) and College's approach foot / south approach / I-8 span each ramped to nothing at the shared station, a dip back toward the built ground between two released pieces |
| release rails per side over the union of the zones | rule | release rails (3) | overlapping zones each drew their own rail over the shared stations: two prisms 3 cm apart whose end caps stood up as white teeth on the parapet (College approach, Lake Murray Blvd creek). One rail per contiguous run of stations now (10 rails, the zone names joined) |
| `tools/ground_release_blend.RAIL_TAPER_M` / `RAIL_END_H_M` | 2.0 m / 0.05 m [invented] | release rails | a free-standing end slopes down over its last 2 m to 5 cm (a sloped end treatment) instead of standing its square Jersey profile up as a pointed white tooth (the College approach rail ending beside the bridge parapet) |

Tried and dropped (measured, not shipped): a zone ramp lengthened to an earth batter's run of its step (3.5 m per m,
4-16 m) raised the constructed bumps beside Alvarado's creek bank (49 -> 62 over 0.6 m) and under Lake Murray Blvd.

Measured on the full rehearsal (fresh scratch workshop, fresh scratch engine-july, no `--skip-blend`), v0.17.1 -> this
build: street drive_test soft top 42 -> 41, severe 0, kinks 3.86 -> 3.41 /km, bumps 0.15 -> 0.0 /km, gated excursions
100 -> 99, floating 391, obstruction 0, daylight 0; street audit D 512 -> 514 (corrected in fix round 4: NOT the release rails, which add 0 D — the same 90 `1WALL_guard`
positions as v0.17.1, two of them on College's deck, now 1.6 m higher at its real height, written as one more duplicate
vertex record each by the kn5 exporter, as the first integration fix round's entry above says),
K 20, I 20, F 13; race_cw / race_acw severe 31 / 28 -> 22 / 20, soft top 9 / 9, audits D 0 K 20 I 20 F 13 W 0, no_route
PASS planned and built (leak 0, 0 / 406), barrier_missing 0, obstruction 0; verify_mouths PASS x4, verify_fold_fans PASS,
verify_ai_line PASS (2.544 / 2.386 m), verify_kn5 + --inis, check_race_kn5, verify_race, verify_signs (23 posts),
rib_check, house_seat_check PASS. Release: batter cut 412 / fill 446; steep faces (> 60 deg, > 0.5 m) within 12 m of a
pavement 786 -> 549 (439 -> 329 not under a deck). Teeth (a terrain vertex > 0.6 m over the mean of its neighbours and
not 3DEP's own): within 20 m of College's south abutment 5 -> 0; within 25 m of the comb west of the north approach 18 -> 7 (the refuted build -> this one). Road kn5 92,502,895 B
(v0.17.1) -> 116,011,770 B (128,277,872 with the freeway).

### Integration fix round 4 (2026-10-14, v0.18.0, after the gates, runtime and view lenses refuted round 3): rails over every drop, the pit under College's sidewalk lifted, the straight bank, coincident faces, the lamp lenses

No gate threshold changed and no criterion was re-worded. **Corrected:** round 3's "D 512 -> 514 (the release rails)" was
wrong — the release rails add 0 D (fixed in the round 3 text above).

| Number / rule | Value | Where | Why |
|---|---|---|---|
| a rail stands full height over every station that needs it | rule (`tools/ground_release.rail_heights`) | release rails | the gates lens: round 3's sloped ends (to 5 cm over 2 m) stood over live drops wherever a run's padding was clipped by a zone or block end — College Ave's approach foot, s 2500-2502, 4.9 m down; beside College's deck; Lake Murray Blvd. drive_test credits any 1WALL as a guard whatever its height, so the gates could not see it. A slope is built only over padding past the last station over a drop |
| `tools/ground_release.RAIL_HOLD_M` | 1.0 m [invented] | release rails | full height at least this far past the first / last station over a drop |
| `tools/ground_release.RAIL_TAPER_MIN_M` | 0.5 m [invented] | release rails | a sloped end shorter than this is not built: the end stays square |
| rail stations past a zone's end | rule | release rails | the gates lens: at College's approach foot (s 2496-2500) a 3-5 m curtain off the sidewalk had no rail because the stations stopped at the zone; the same embankment edge, College 4-6 m over Alvarado, ran unguarded back to s ~2401 since v0.17.1. From every zone end not inside another zone on that side, stations continue outward while the drop does |
| `tools/ground_release_blend.RAIL_EXT_FALL_M` | 1.0 m [invented] | the outward stations | past a zone only a real embankment edge carries the rail on: a steep fall (drive_test's 0.12 m per 0.5 m) AND the ground more than this under the edge (the zone rule's 0.5 m fall alone fenced ordinary street verges, 120 m runs in a trial) |
| `tools/ground_release_blend.RAIL_EXT_MAX_M` | 120 m [invented] | the outward stations | at most this far past a zone end |
| a pit under the pavement in a bank zone lifted to it | rule | release step 2 + the per-face cap | the view lens's stepped curtain under College's south approach: the draft seats that ground at Alvarado's level, 6 m under College's sidewalk; the prep pins ground under a deck only to a sheet within its window of the vertex's own height and leaves zone vertices alone otherwise, so it stayed a pit under the sidewalk, sawn against the released bank beside it. A held vertex more than `HELD_PIT_M` under its lowest upward ROAD / CURB sheet is lifted to it, and its faces are capped with the released ones (a lifted corner under a curb top must not stand over the gutter beside it). Lifting EVERY held vertex was tried on this round's second rehearsal and dropped: the ground under a curb top stood 0.13 m over the gutter, street soft top 42 -> 211 |
| `tools/ground_release_blend.HELD_PIT_M` | 1.0 m [invented] | release step 2 | deeper than this under its sheet is a pit; shallower, the seat's height under the pavement stands, as in v0.17.1 |
| the straight bank between two pavements | rule (`tools/ground_release.batter_z`) | release batter (2b) | where a fill from a high pavement and a cut from a low one cannot both hold (College's sidewalk 5-6 m over Alvarado's, 2-3 m apart) "the cut wins" left a vertical curtain under the high one. There the ground is the straight bank between the two edges, by distance |
| `tools/ground_release.STRAIGHT_BANK_MIN_M` | 1.0 m [invented] | the straight bank | only between pavements this far apart in height; below it (one road's own grade) the cut still wins |
| zone `college_approach_foot` from s 2410 (was 2500) | config | track.config.json | the embankment edge first falls over 1 m at s 2410; the old start at s 2500 put the boundary between released and held ground in the middle of the curtain the view lens saw from Alvarado (209 3DEP nodes fetched, TLS verified, cached with provenance) |
| zone `college_north_approach` s 2690-2745, bank, both sides | config | track.config.json | the view lens's fins 20-50 m west of College's north approach: `college_i8_span` ended at s 2690 and ramped over 4 m back to a verge fresh 3DEP reads 1.3-3.3 m over the real earth; the 1.25 m lattice sampled the ramp as teeth. The zones abut (no ramp at s 2690); 1,266 3DEP nodes fetched |
| release halving by PLAN length | rule | release step 1 | the runtime lens's zero-length normals: a vertical edge of the seat's curtain (two vertices on one plan point) was halved round after round, stacking up to 31 coincident faces back to back |
| coincident faces / vertices removed | rule | release; `tools/triangulate_terrain_blend.SLIVER_M2` 0.01 m2 [invented] | faces on one vertex set: a sliver group goes, a real face keeps one copy; coincident vertices welded (1e-4 m) after the release. In the triangulation, a quad with a T-vertex on its diagonal split into a zero-area sliver, its neighbour into the same sliver reversed: groups under 0.01 m2 removed, with a vertex left with no face (no vertex moves) |
| engine-july prep: LIGHTS do not ride the terrain delta | rule (snapshot `build_kn5_loop.py`, pending mirror) | kn5 prep re-seat | the runtime lens: a lamp's lens marker moved by the ground change under its arm while its LIGHTPOST stayed (LIGHT_123 on Lake Murray Blvd's I-8 deck 0.68 m over its own plate, LIGHT_122 0.15 m) — the head shadowed its own pool |
| `scripts/ac/ext_config.py` GRASS_NIGHT includes `GRASS_FAR` | rule | ext_config | the far ring kept its day ksDiffuse 0.22 at night beside the near grass's 0.14 |
| the release rails are their own physical mesh `1WALL_guard_release` | rule | release rails | found on this round's first rehearsal: appended to GUARDRAIL, the longer rails took the prep's 1WALL_guard past the kn5 exporter's 65,536-vertex mesh cap; the exporter wrote two meshes of one name and verify_kn5 stopped the chain ("DUPLICATE physical mesh '1WALL_guard' x2 — AC drops dup-named meshes from collision"). The name keeps the 1WALL_GUARD material row and the WALL surface (prefix match) |
| `tools/ground_release_blend.RAIL_CHUNK_TRIS` | 18,000 [invented] | release rails | triangles per rail mesh before a second one (`1WALL_guard_release_<k>`): 3 exporter vertices per triangle at worst stays under the cap |

**Not changed, named instead (both still worse than v0.17.1 on paper; `--force-install` would assert otherwise). Both fixed in round 5 below.**
(a) Street audit D 512 -> 514: the same 90 `1WALL_guard` positions as v0.17.1; at two of them on College's deck, now
1.6 m higher at its real height, the kn5 exporter writes one more duplicate vertex record each (it dedups corners by
exact float normal equality, and the slope changed the rounding). No wall moved onto the road. (b) race bumps / km
7.42 / 10.24 -> 7.72 / 10.39: drive_test's own per-station steps (re-run read-only) put the net +4 / +2 at two places —
cw s 4539-4549 (acw s 8933-8943), the inside of the levelled fold pinch at (-1961, 593) (ledger 0050, rows 1508-1516),
where v0.17.1 had grass standing on the road in the lane (12 / 11 of its 23 / 22 soft-top hits are those stations): the
wheel paths now read the pinch's road fan, 2.5-6 cm second differences; and cw s 6946-6969, the Navajo / Jackson riser
ledger 0050 levelled, its 0.39 m severe steps now 3-6 cm bumps. Steps over 2.5 cm in all (bumps + severe): 131 -> 126
(cw), 166 -> 160 (acw).

Measured on the final rehearsal (fresh scratch workshop, fresh scratch engine-july with the pending prep change, no
`--skip-blend`), v0.17.1 -> this build: street drive_test soft top 42 -> 33, severe 0, kinks 3.86 -> 3.41 /km, bumps
0.15 -> 0.0, excursions 100 -> 98, floating 391, obstruction 0, daylight 0; street audit D 512 -> 514 (above), K 20, I 20,
F 13; race_cw / race_acw severe 31 / 28 -> 22 / 20, soft top 23 / 22 -> 9 / 9, kinks 6.45 / 7.57 -> 6.23 / 7.05, bumps
(above), audits D 0 K 20 I 20 F 13 W 0, no_route planned 139,130 / 138,826 m2 and built 139,148 / 138,847 m2 PASS
(leak 0, 0 / 406), barrier_missing 0, obstruction 0; verify_mouths x4, verify_fold_fans, verify_ai_line (2.544 /
2.386 m), verify_kn5 + --inis, check_race_kn5, verify_race (+ scenery), verify_signs (23 posts), rib_check,
house_seat_check PASS. Release: 327 pits under the pavement lifted, batter cut 460 / fill 604 / straight bank 115,
2,732 coincident faces removed and 961 coincident vertices welded (0 coincident face sets left in TERRAIN, round 3 448);
10 rails, 0 rail vertices on a road, College's approach foot railed from s 2388 (the stations past a zone end: 19 over a
drop). Steep faces (over 60 deg, over 0.5 m) within 12 m of a pavement in the zones 549 -> 849: the two zones added and
the straight banks (a 60-70 deg bank where the two sidewalks stand 2-3 m apart) — counted, not hidden.

### Integration fix round 5 (2026-10-14, v0.18.0, after the gates lens refuted round 4): the deck rails off the pavement, drive_test's fold bumps

The gates lens refuted round 4 on two metrics worse than v0.17.1: street audit D 512 -> 514 (over the floor `ship_sd.sh`
prints) and race bumps / km 7.42 / 10.24 -> 7.72 / 10.39. Both are now fixed at their causes; every other gate is as in
round 4.

| Change | Value | Where | Why |
|---|---|---|---|
| the I-8 deck guardrails stand 0.15 m outside the pavement edge | `GUARDRAIL_SET_M` 0.15 m [invented] | `tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.build_guardrails` | D counts a 1WALL vertex lying on a carriageway triangle within 1.2 m of it. Every one of the 90 panel positions on College Ave's and Lake Murray Blvd's decks was built ON the road's edge line (`hw`), so all of them lay on the road's own boundary: v0.17.1's 512 was those 90 positions x 5-6 kn5 vertex records, and round 4's 514 was the same 90 with two more exporter duplicates where College's deck now has its real slope (the exporter dedups corners by exact float normal). A bridge barrier stands on the curb behind the gutter line, not on the pavement: 0.15 m puts each panel on the curb top, its foot still inside the curb. Street D 514 -> **0**; E 0 (the foot is in the curb); the release rails' "already held" test (a GUARDRAIL between the lane and the lip) reads the same |
| the street audit's printed regression floor | D 512 -> **0** (K 20 / I 20 / F 13 unchanged) | `tools/ship_sd.sh` step header, `tracks/san-diego-lake-murray/ship.json` `audit_note` | tightened to what the build now measures |
| FOLD BUMPS: a 2.5-6 cm second difference over a metre where the fixed-offset wheel-path point runs backwards is reported (`fold_bumps`), not counted in `steps_per_km` | rule; `_advance` < 0 on the metre or the metre before it | `scripts/geometry/drive_test.py` (every track, every layout) | criterion re-worded where fresh 3DEP fails it too (evidence below). drive_test's wheel paths are fixed lateral offsets; round a corner tighter than the offset (Lake Murray's fold fans: centre radii 7-8 m under race lanes 9-13 m wide) the point lies past the turning centre and hops 1-2.5 m to and fro across the fan, so its 1 m second difference re-traces the plan, not a step under a tyre. A SEVERE step (> 6 cm) on such a sample still counts (ledger 0050's 0.37 m Navajo / Jackson lip was read on one); kinks are unchanged; the levelled fans' real wheel paths stay judged by `tools/verify_fold_fans.py` |

**Evidence for the re-wording (fresh USGS 3DEP 1 m, TLS verified through `scripts.tls`, 10,125 points on 45 x 45 m grids
round the five Lake Murray fans: the hairpin, College / Navajo, Navajo / Jackson, the seam, the east corner at (2603,
516)).** The least-squares plane of the real ground within 15 m of each fan (grades 7.0 / 5.5 / 3.0 / 1.4 / 3.2 %), the
smoothest surface the real corner can have, read through drive_test's OWN sample positions (the race_cw and race_acw
paths, logged from the build): of 158 backward samples per layout, 76 / 74 read a bump and 34 / 35 a severe step — the
real ground's plane fails the bump rule there half the time. The raw 3DEP reads 62 / 60 bumps on them. (Forward samples
also read some bumps on the plane — 163 of 2,742 — from the stations' changing spacing round a corner; those are not
exempted: the rule is only the backwards case.)

**The same rule on both builds** (drive_test re-run read-only on v0.17.1's installed gate OBJs, `k10-sd-v021/project`,
output redirected; nothing written there): race_cw bumps 100 -> 65 counted + 35 fold (v0.17.1), 104 -> 59 + 45 (this
build); race_acw 138 -> 97 + 41, 140 -> 91 + 49; street 2 + 20, 0 + 20. On the samples a wheel can drive, this build has
fewer bumps than v0.17.1 on every layout (65 -> 59, 97 -> 91, 2 -> 0); all of round 4's increase was in backward samples
(35 -> 45, 41 -> 49), the College / Navajo and Navajo / Jackson fans whose grass-over-road and 0.39 m risers this
branch removed.

Measured on this round's full rehearsal (fresh scratch workshop, fresh scratch engine-july with the pending prep files,
no `--skip-blend`, `ship_r5.log`), v0.17.1 (as gated then) -> this build: street drive_test soft top 42 -> 33, severe 0,
bumps 0.15 -> 0.0 /km (fold 20), kinks 3.86 -> 3.41, excursions 100 -> 98, floating 391, obstruction 0, daylight 0;
street audit **D 512 -> 0**, K 20, I 20, F 13, E 0; race_cw / race_acw severe 31 / 28 -> 22 / 20, soft top 23 / 22 -> 9 /
9, **bumps 7.42 / 10.24 -> 4.38 / 6.75 /km** (fold 45 / 49; v0.17.1 under the same rule 4.82 / 7.20), kinks 6.45 / 7.57
-> 6.23 / 7.05, barrier_missing 0, obstruction 0; race audits D 0 K 20 I 20 F 13 W 0; no_route planned 139,130 / 138,826
m2 and built 139,148 / 138,847 m2 PASS (leak 0, 0 / 406); verify_mouths x4, verify_fold_fans (3 x 3), verify_ai_line
(2.544 / 2.386 m), verify_kn5 + --inis, check_race_kn5, verify_race (+ scenery), verify_signs (23 posts), rib_check,
house_seat_check PASS. The terrain is round 4's but for 344 of 928,435 triangles beside the two decks, moved at most
0.024 m.

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

### Integration (2026-10-13, v0.18.0): (l) named corners stay signed — the verifier's gap closed

The 0051 verifier planted M4-fwd and M4-rev both lost (as "ON pavement" skip records, or gone) and `verify_signs` passed:
(k) only judges a corner that still has a plate in some direction, and `author_signs_blend` exits 0 on mesh-stage skips —
so 0050 reshaping the Navajo/Jackson curb could have cost every layout its Jackson/Navajo arrows with every gate green.

| Check | Rule | Threshold |
|---|---|---|
| (l) named corners | every corner `signs.json` names and does not skip outright keeps at least one plate; a MAINLINE one a plate in every driven direction (`layouts[].direction`) unless `signs.json` skips THAT approach with a reason — a rule reason (R_apex, \|D\|, …) does not cover a corner Kevin named; a side-street one a plate in each approach, or a skip there that (k) counts as coverage | none (structural) |

Teeth (tests/tools/test_place_signs.py::test_a_named_corner_that_lost_every_plate_fails_l): both M4 plates as
"ON pavement" skips (k blind) → FAIL; both records gone → FAIL; M4-rev lost to a rule reason → FAIL (k passes it); the
same with `"rev": {"skip": true, "reason": ...}` → PASS; MED-6-rev lost to OUTSIDE ASSERTION → FAIL, to R_apex → PASS.
On the v0.18.0 build: 23 posts, 11 named corners (M1–M5, MED-1/6/7/8/10/13) all signed, M4-fwd / M4-rev clear the race
curb strip by +1.853 / +1.762 m (verify_race G's own margin).

## 2026-10-12 — worn race kerbs: the atlas wrap, the no-black-slot guard, the opt-in wheel kerb effect (ledger 0053)

Kevin, from the seat on v0.17.1: "i'd like the race curbs to be tire-worn/textured". The eight `1KERB_race_*` kerbs
keep every vertex, face and hard edge (scratch rehearsal: `race_authored.json` ring centres and frames identical for
all 35 objects, 167,958 positions before and after), so no driving-surface gate moves: `drive_test`, `audit_mesh`
(K 154), `verify_race`, `kn5_ground_check` judge the same geometry. What changes is the picture, the wrap and one
guard. Every number below is **[invented]** unless it says measured.

| Value | Where | Number | Flag |
|---|---|---|---|
| atlas repeat along the kerb | `race_furniture.KERB_ATLAS_V_M` | 8.0 m (2,048 px at 256 px/m) | ⚠ invented |
| red / white block | `KERB_BLOCK_M` | 1.0 m (the 0047 stripe was 0.5 m + 0.5 m) | ⚠ invented |
| rubber levels | `KERB_ATLAS_COLUMNS`, `kerb_wear` | 4 columns; level = min(3, int(4 w)), bins of 0.25 | ⚠ invented |
| inside-kerb lobes | `KERB_WEAR_IN_*` | each direction's late apex PC + 0.6 arc / PT − 0.6 arc; sigma max(5 m, 0.15 arc); floor 0.15 | ⚠ invented |
| outside-kerb lobes | `KERB_WEAR_OUT_*` | each direction's track-out PT + 0.2 E / PC − 0.2 E; sigma 6 m; floor 0.10 | ⚠ invented |
| joint snap | `KERB_JOINT_SNAP_MAX_M` | a whole metre of the kerb's own mid-line becomes a joint station only if a station lies within 0.25 m; v is warped so every joint station sits on a whole metre; a block takes the highest raw level of its stations; the column changes only there | ⚠ invented |
| column pad | `KERB_ATLAS_PAD_PX` | 8 px each side of a 256 px column (mip level 3 stays inside its column) | ⚠ invented |
| wrap handedness | `KERB_V_SIGN` | L −1, R +1: every kerb's (T × B) · N = +1 in the Blender frame, the sign of the prep's `planar_uv` road wrap (a kn5 tangent has no handedness sign). Not a threshold: derived and tested | measured (tests) |
| kerb material | `pbr.KS_PROPS["1KERB_RACE"]` | ksAmbient 0.40 / ksDiffuse 0.40 (the add-on default every neighbouring race material ships at, measured) ; ksSpecular 0.10, ksSpecularEXP 20 (Kunos Laguna `red_curb` measured at 0.35 / 20, technique only) | ⚠ 0.10 invented |
| the picture | `tools/make_kerb_texture.py` | colours (RAL 3020 / 9016 weathered), `RUBBER_COVER` 0 / 0.12 / 0.30 / 0.55, `RUBBER_OPACITY` 0 / 0.55 / 0.70 / 0.82, `RUBBER_HAZE` 0 / 0.12 / 0.28 / 0.46, `CHIP_COVER` 0.035, `NORMAL_STRENGTH` 2.2, JPEG q90 4:4:4 | ⚠ invented, tuned by eye on Blender stills |
| texture budget | `make_kerb_texture.MAX_BYTES` | ≤ 2,000,000 B per file (painted: 567,921 + 980,349) | ⚠ invented |
| render-vertex cost of a seam | `render_vertex_count(..., face_uvs)`, `KERB_SEAM_RENDER_VERTS` | exactly +4 per seam: the 5 cm outer face always wraps column 0 (`KERB_OUTER_FACE_COLUMN`, pixel-identical in every column), so a seam re-cuts the lip, both faces at the ramp-top edge and the top's outer edge, not the outer face's two (the first cut re-cut all 6: 7,356) | measured: pure 7,050 → 7,254 for 51 seams = the built kn5's KERB count exactly |
| Lake Murray kerb render budget | `tests/tools/test_kerb_wear.py` `SD_KERB_RENDER_VERTS_MAX` | KERB ≤ 7,300 render vertices (installed v0.17.1: 7,050), pre-registered in the diagnosis before the fix; held, not moved (verify round 1) | ⚠ invented (pre-registered) |
| normal-map convention | `make_kerb_texture.normal_rg`; `test_normal_map_is_opengl_green_up`, `test_joints_are_grooves_in_the_normal_map` | OpenGL like every map in assets/textures: a synthetic ramp rising down the image gives G > 128; every joint is a groove (G < 110 just above, > 146 just below; measured ≈ 36 / ≈ 220). Pillow flips kernels vertically; the first cut was DirectX (≈ 223 / ≈ 33) | test thresholds ⚠ invented; convention measured |

**New gate — `tools/check_race_kn5.py` `black_slots` (hard, both roles, every race kn5).** Every texture the
`pbr.TEXTURES` race rows bind for the meshes present must be embedded with > 0 bytes, and (when the parse carries
materials) each race mesh's material must bind exactly its row's `txDiffuse` / `txNormal` and nothing unembedded.
Why: `ship_sd.sh` exports from engine-july, which stages textures from ITS `assets/textures`; a file that is only in
airoso is skipped with a WARNING and the slot renders black (LAWS L7) — the old role checks passed such a kn5. Proof:
the installed v0.17.1 race kn5's parse now FAILS (`kerb_diffuse.png` outside the race set, the worn pair not
embedded, 16 bindings disagree); the rehearsed kn5 PASSES. `tests/tools/test_check_race_kn5.py::test_ledger_0053_no_black_kerb_slot`.

**Opt-in — `track_folder.surfaces_ini(kerb_ff_effect=0)`.** `FF_EFFECT=<n>` on the KERB block only, read from
`track.config.json` `kerb_ff_effect` (absent = 0). The default output is byte-identical (md5 pinned for tarmac /
gravel × wall, `tests/ac/test_road_surface.py`); opt-in changes exactly one line. 1 is the Kunos convention
(measured FF_EFFECT=1 on Vallelunga, Silverstone, Laguna Seca, Brands Hatch, Red Bull Ring, Barcelona, Imola, Mugello;
0 on Zandvoort; absent on Highlands). Caveat recorded: KEY=KERB also covers the street `1KERB_sidewalk` (114,081 m²
in the main kn5), so an opted-in track's sidewalks get the wheel effect too. No track opts in in this commit
(Lake Murray's config is the integration run's, Kevin's call).

Rehearsal (scratch copy of the v0.17.1 workshop + a scratch engine-july carrying this pbr.py and the two textures):
author → `verify_race` OK → prep → split → `<slug>_race.kn5` **10,253,676 → 11,815,506 B (+1,561,830 B, +15.2 %)**
(the textures embedded are the bytes packed at the prep — see ledger 0053 "Integration"), `check_race_kn5 --role
common` OK, all 8 kerb materials `ksPerPixelMultiMap` txDiffuse + txNormal, ksSpecular 0.1. Re-run after verify
round 1 (the OpenGL normal map and the 4-per-seam wrap): `<slug>_race.kn5` 10,253,676 → **11,811,590 B (+1,557,914 B,
+15.2 %)**, the embedded normal map 980,349 B with the committed file's md5, KERB **7,254** render verts (≤ 7,300),
every column split on a whole-metre joint, every outer-face vertex in column 0, kerb positions and triangles
identical to installed v0.17.1.

### Integration (2026-10-13, v0.18.0): the textures ride the pending-mirror record

`tools/snapshot_engine_july.py` now also writes a referenced texture the real engine-july lacks (old md5 "-") or holds at
another md5 into `PENDING-MIRROR.md5`, and `test_live_engine_july_has_not_drifted_from_the_snapshot` / `--check` read
such a line as pending, not drift — so the worn kerb atlas (`kerb_race_worn_diffuse.jpg` f599d4a7…, `_normal.jpg`
8f4b343a…) is on the mirror list beside `pbr.py` (now both the BRIDGESTRUCT and the worn 1KERB_RACE rows, CRLF md5
48617c1e…) instead of failing the suite until the install. No threshold changed.

## 2026-10-12 — the AI line gate: `tools/verify_ai_line.py`, and the writer's opt-in (ledger 0052)

Kevin, from the seat, after a 7-AI race on the installed v0.17.1 race layouts: "ai races need tuning, they tend to
crash and slow down weirdlu". Nothing measured a written `fast_lane.ai` against the walls the car hits:
`ai_draft.json` judges the line against the writer's own CorridorFaces declaration, at 0.6 m.

### The gate (`tools/verify_ai_line.py <project> --layout <id>`, new)

It reads the line AS WRITTEN (`<project>/ai/<id>/fast_lane.ai`, kn5 frame) and the BUILT gate OBJ
(`data/track.<id>.obj`: road + race + that layout's closure kn5, engine frame). It writes
`data/ai_verify.<id>.json` and exits 1 on any FAIL. Thresholds can be overridden per track in
`track.config.json` `ai.verify`. The "MEASURED" references are the 217 AI lines installed on this PC, measured in
the 0052 diagnosis. Kunos walls were read from their `NNWALL` physics meshes through `scripts/modkit`'s kn5
reader.

| Check | Threshold | Flag | v0.17.1 race_cw / race_acw | 0052 lines (scratch) |
|---|---|---|---|---|
| V1 `length` = the 3D distance to the previous point | median error < **0.01 m** | MEASURED (Kunos 0.0001-0.001 m; 0 of 186 reference lines cumulative) | 6,732 / 6,721 m | 0.0 / 0.0 |
| V1 `direction` | ±1 on every point; = −sign(heading change over ±10 points) on ≥ **99 %** of points turning > 0.5° | MEASURED (Kunos 99.0-99.5 %) | 0 everywhere | 100 % / 100 % |
| V1 header lapTime / sampleCount | **0 / 0** | MEASURED (every Kunos line; actools "usually zeroes") | 281085/8979, 281338/8964 | 0/0 |
| V1 `radius` = the 3-point circumradius | median \|ln\| error < **0.01** | MEASURED (Kunos 0.0006-0.0025) | 0.194 / 0.242 | 0.0 / 0.0 |
| V1 `camber` = asin(normal · right) of the BUILT 1ROAD under the point | median ratio **0.9-1.1** where the road tilts > 0.01 rad, else median \|diff\| < 0.005 rad; normal not (0,1,0) everywhere | MEASURED (Kunos ratio 0.94-0.99) | ratio 0 (camber 0, normal up) | 1.0 / 1.0 |
| V2 wall clearance: the line's centre to the nearest BUILT 1WALL footprint (horizontal, layer band −2/+4 m, L4) | min ≥ **2.0 m** | MEASURED (ks_monza66 1.981, ks_black_cat_county 2.066) | 1.506 / 1.504 m | 2.517 / 2.387 m |
| V2 lap within 2.5 m of a built wall | ≤ **1.0 %** | ⚠ INVENTED (BCC 0.58 %, Monza66 3.2 %) | 1.38 % / 1.77 % | 0.00 % / 0.04 % |
| V3 spurious dips (defined below) | **0** points | MEASURED (0 on ks_black_cat_county, ks_vallelunga, ks_highlands) | 160 / 875 | 0 / 0 |
| V3 bend flips: car-scale curvature (turn over ±4 points) with \|k\| > 1/300 changing sign within 30 m | ≤ **0.75 per km** | MEASURED (BCC 0.72) | 1.71 / 0.97 | 0.67 / 0.52 |
| V4 sides: sideLeft / sideRight past the first BUILT wall a horizontal ray PERPENDICULAR to the line meets | **0** points | — (geometry) | 0 / 0 | 0 / 0 |
| V5 the line's own 3-point radius | ≥ **11.4 m** | the writer's RADIUS_FLOOR_M 12 × RADIUS_CHECK 0.95 | 12.56 / 12.55 m | 13.78 / 14.33 m |

**The spurious-dip definition (V3).** Two physics speed profiles are built from the same line:
- the same settings for both: μ 1.0, 0.9 g braking (backward pass), 0.35 g acceleration (forward pass),
  69.4 m/s cap, two passes each round the closed lap;
- one profile uses the payload's radius field; the other uses the line's car-scale radius (the circumradius
  through the points ±4 = ±6 m).

A point where the payload profile is more than **10 %** slower than the car-scale profile is a spurious dip. In
plain terms: the file tells the AI to slow for a bend the car-sized line does not have.

**V4 corrects the diagnosis.** The diagnosis counted 23 race_acw points with `sideLeft` "past a built wall". That
used the nearest wall on the left half-plane in any direction. Every one of the 23 was a wall 16-18 m BEHIND the
point, 0.1-0.9 m to its side (probe at idx 2965-2977, 4919-4923, 6519-6525). On a perpendicular ray, the
v0.17.1 sides stop exactly 1.2 m (the margin) short of the wall, median, with 0 overreach. The gate uses the ray.

Wiring: not in a ship chain yet — `tools/ship_sd.sh` and `tools/ship_track.sh` are held by concurrent jobs this
round. Ledger 0052 "Held files" gives the exact change. Note that the AI step there runs BEFORE the race gate OBJs
are extracted (`ship_sd.sh`: write_ai_line at :251, `kn5_to_gate_obj` at :304, after the `rm` at :289), so the
extraction has to move ahead of the AI step for the gate and the writer's `ai.surface` to see this run's world.

### The writer (`scripts/ac/write_ai_line.py`, opt-in `track.config.json` `ai`; absent = today's bytes)

| Knob | Value | Flag |
|---|---|---|
| `ai.wall_clear_m`: a corridor line's comfort clearance (box approach, box arcs, floor fillets) | **2.5 m** (FILLET_COMFORT_CLEAR_M 1.5 stays the default) | ⚠ INVENTED (a 1.9 m car's half-width + 1.55 m; the 6.86 m narrowest corridor fits 2.5 m each side with 1.86 m to spare) |
| fair_line hold on the input line `FAIR_W` / curvature weight `FAIR_ALPHA` / leash `FAIR_U_MAX_M` | **1e-6 / 1e-2 / 3.0 m** | ⚠ INVENTED, swept on SD race_cw: w 1e-4 kept every gentle road S (1.49 flips / km); α 1e-3 left 0.82 / km; α 3e-2 pressed the line onto its bounds (32 dips) |
| polish after the fairing `FAIR_POLISH_W` / `FAIR_POLISH_U_M` | **1e-4 / 0.3 m** | ⚠ INVENTED. Without it, nearby settings left 9-77 dips where an active bound met the line; with it, 0 in every setting swept |
| the fairing's own wall margin `FAIR_CLEAR_EXTRA_M` | **+0.5 m** over wall_clear (never closer than where the point stood) | ⚠ INVENTED (0 and 0.25 also passed; 0.5 keeps the 2.5 m band empty on race_cw) |
| bound envelope `FAIR_BOUND_SMOOTH_PTS` | **±4 points**, min then mean, twice (conservative by construction) | ⚠ INVENTED |
| payload `direction` window | **±10 points, 0.5°** | MEASURED (the window the Kunos agreement was measured over) |
| `ai.surface: gate_obj`: seat on the BUILT 1ROAD within **3 m** of the point's height; the walls' layer band **−2 / +4 m** | — | ⚠ INVENTED bands (the diagnosis' filter); the writer refuses a missing gate OBJ, or one older than a kn5 its header names |

Proof:
- `tests/ac/test_write_ai_line_payload.py` (9 tests).
  - Byte identity: golden md5s of all 25 files of the two end-to-end fixtures, HEAD 5ccf20b's writer.
  - On a synthetic built world: the payload's meaning, the wall clearance, the gate passing the opted-in line and
    failing the legacy one.
  - The banded solver, fair_line's bounds, the OBJ reader's layer filter and rays, the stale-OBJ guard.
- Byte identity on the real workshop (scratch copy, no `ai` block): `race_cw` `8d4696a4…`, `race_acw`
  `c234c87c…` and `street` `93a09e5a…` are md5-identical to the installed / HEAD files. The same holds for every
  `side_*.csv` and `ai_draft.json`.

### Repair, 2026-10-13 — labels re-measured, camber sign, the box rule on the written line (ledger 0052)

An independent check refuted three things above. The rule applied here: a threshold says MEASURED only if every
Kunos line it cites passes it; anything else is ⚠ INVENTED, with the references it was chosen against. The rows in
the tables above stand as the record of what was first claimed; **this subsection supersedes their flags and
values.** Evidence: the gate's own `measure()` / `judge()` run on all 34 Kunos lines installed on this PC, each
line's own stored normal standing in for the built road (scratch `v018/ai/kunos/kunos_v1.txt`).

| Check | Threshold now | Flag now | Kunos (34 lines) | v0.17.1 race_cw / race_acw | repaired lines |
|---|---|---|---|---|---|
| V1 line family | SEGMENT (length = one segment, 3-point radius) or WINDOW (length = 5 segments summed, radius through ±5 points, direction ramp over **10** points per end) — the length field decides; a line that matches neither is judged as SEGMENT | MEASURED (33 SEGMENT; ks_silverstone/international WINDOW, as are 33 third-party lines) | 34 / 34 classified | SEGMENT (matches neither) | SEGMENT |
| V1 `length` | median error < **0.01 m** against the family's reference; SEGMENT also ≤ **0.1 m** on every point but the last | MEASURED (median 0.0000-0.0016 m; SEGMENT point max 0.056 m; the last point carries ~5 × spacing on every Kunos line, so it is not judged) | pass 34 / 34 | 6,732 / 6,721 m | 0.0 / 0.0 |
| V1 `direction` | ±1 on every point but the last (WINDOW: but the seam ramps); = −sign(LOCAL heading change, ±**1** point) on ≥ **99 %** of points turning > 0.5° | MEASURED (0.9977-1.0 at ±1 point; the first version's ±10 window gave 0.968-0.995, 23 of 33 under 0.99) | pass 34 / 34 | 0 % | 100 % / 100 % |
| V1 `radius` | the family's circumradius, median \|ln\| error < **0.01** | MEASURED (0.0001-0.0035) | pass 34 / 34 | 0.194 / 0.242 | 0.0 / 0.0 |
| V1 `camber` (SEGMENT) | = **−direction × asin(normal · right)** of the BUILT road (the tilt measured toward the bend), median ratio 0.9-1.1 where it tilts > 0.01 rad | MEASURED (ratio 0.998-1.001; the sign rule holds on 0.95-1.00 of tilted points on every reference line, plain asin(normal · right) on ~0.5) | pass 33 / 33 | ratio 0 | 1.00 (34 / 62 tilted points) |
| V1 `camber` (WINDOW) | not judged | — (Kunos' own stores the normal as (0,1,0) beside a real camber, so nothing shows what it is measured from) | — | — | — |
| V1 camber on a flat road | median \|difference\| < **0.005 rad** | ⚠ INVENTED (passes every SEGMENT Kunos line) | | | |
| V1 measuring parameters: a bend = turn > **0.5°**; a tilted road = > **0.01 rad** | — | ⚠ INVENTED | | | |
| V2 wall clearance min | ≥ **2.0 m** | ⚠ INVENTED — was "MEASURED", but ks_monza66 measures **1.981 m**, so 2.0 is a choice between the two walled Kunos references (BCC 2.066), not a value both pass | — | 1.506 / 1.504 m | 2.549 / 2.387 m |
| V3 spurious dips | **0** | ⚠ INVENTED — was "MEASURED (0 on BCC, Vallelunga, Highlands)", but ks_highlands/layout_int has 422 by the gate's own code; 20 of 34 Kunos lines have 0, 14 have 5-885 (recorded lines carry them) | 0 on 20 / 34 | 160 / 875 | 0 / 0 |
| V3 bend flips within 30 m | ≤ **0.75 / km** | ⚠ INVENTED — was "MEASURED (BCC 0.72)"; Kunos 0-1.24 / km, ≤ 0.75 on 17 of 34 | 0-1.24 | 1.71 / 0.97 | 0.74 / 0.52 |
| V4 sides past a built wall | **0** | ⚠ INVENTED (geometry rule) | | 0 / 0 | 0 / 0 |
| V5 the line's 3-point radius | ≥ **11.4 m** | ⚠ INVENTED (the writer's RADIUS_FLOOR_M 12 × RADIUS_CHECK 0.95, both invented) | | 12.56 / 12.55 m | 13.78 / 14.33 m |
| V6 (new, `--baseline <line>`): every baseline corner (car-scale minimum under 80 m within ±60 points) keeps ≥ **0.85 ×** its radius | | ⚠ INVENTED (the 0052 diagnosis' pre-declared box rule) | | — | 0.860-0.863 / 0.860-0.877 |

The payload `direction` window in the writer is now **±1 point** (MEASURED, as above), replacing the ±10 points
recorded in the writer table above.

Writer additions (`scripts/ac/write_ai_line.py`, opt-in `ai.fair` only; no change without the `ai` block):

| Knob | Value | Flag |
|---|---|---|
| `FAIR_BOX_KEEP`: the fairing never takes a box corner's car-scale radius (points ±4) under this × the arc the v0.17.1 rule (comfort 1.5 m) lays at that corner in the same world, within the corner's stations ± `FAIR_BOX_GUARD_PTS` | **0.86**, ± **20 points** | ⚠ INVENTED (the 0.85 rule + 1 % margin; 20 points = 30 m) |
| `BOX_RULE_KEEP`: the writer REFUSES a faired line whose box corner ends under this × that arc | **0.85** | ⚠ INVENTED (the diagnosis' rule, declared before the fix) |

What the first version got wrong, and what changed:
- **Camber sign.** It stored plain asin(normal · right). race_acw carried all 62 tilted points at the opposite sign
  from every reference line (race_cw agreed only because its tilted points all carry direction −1). Writer, gate and
  test now use −direction × asin(normal · right); the plain form FAILS the gate on race_acw.
- **The box rule.** The diagnosis declared each box ≥ 0.85 × today's radius before the fix. The first version met it
  on the arcs before fairing (0.885-0.935) and missed it on the written line (cw 0.819-0.845, acw 0.79-0.87). The
  written line now keeps 0.860-0.877, and the writer refuses under 0.85. Each box apex is 4-6 km/h slower on paper
  than v0.17.1 (it was 4-9 km/h in the first version).
- **Kunos lines failing the gate.** Every Kunos line failed the first version's V1 (direction window, the last
  point's length, the recorder's seam). V1 now passes all 34, and either family of in-game recording.

Proof: still failing every v0.17.1 defect (10 FAILs per layout: V1 length, length per point, direction ±1, direction
agreement, header, radius; V2 min, V2 band; V3 dips, V3 flips). Planted on the repaired lines, each of these FAILS:
cumulative length, direction 0 / flipped, header set, min-of-5 radius, camber 0 with normal up, camber sign flipped,
the plain-asin camber (race_acw), a 0.8 m bump toward the K-rail, 0.25 m / 30 m and 0.6 m / 60 m S-wiggles, 3 cm
jitter, a 1.5 m kink, sides +3 m, one length 0.5 m off its segment. The same line re-expressed in the WINDOW family
PASSES (scratch `v018/ai/planted/plant.txt`). Tests: `tests/ac/test_write_ai_line_payload.py` 12 (adds: the
WINDOW family accepted and a cumulative length judged as SEGMENT; the writer's box-rule refusal).

### Integration (2026-10-13, v0.18.0): the chain order the opt-in needs

`track.config.json` `"ai"` (race_cw, race_acw; kunos payload, 2.5 m off the K-rail, faired, seated on the gate OBJ) is
set, so the writer refuses a missing or stale gate OBJ. `tools/ship_sd.sh` (and `ship_track.sh`'s `ship_ai`, for a track
whose config names the layout) now extracts each race layout's gate OBJ (road + common race + ITS closure kn5) right
before `write_ai_line`, after every export, and runs `tools/verify_ai_line.py --layout <id>` straight after it, hard
under `set -e` (no `--baseline`: the writer holds the box rule itself). The gate stage re-extracts the same file from the
same kn5s. `data/ai_verify.<id>.json` is synced back. No threshold changed.

Measured on the v0.18.0 rehearsal (the 0046 terrain, 0050's levelled fans, 0053's kerbs): race_cw PASS (wall min
2.549 m, 0 m within 2.5 m, dips 0, flips 0.743 /km against the [invented] 0.75, min radius 13.78 m, lap est 279.4 s);
race_acw PASS (2.387 m, 0.00045 of the lap within 2.5 m, flips 0.521 /km, 14.33 m, 272.7 s); the box rule held on the
written line (cw 38.8/45.13, 24.65/28.68, 28.19/32.78, 38.37/44.52 m; acw 41.88/47.49, 46.36/52.27, 45.4/52.32,
51.1/58.54 m). race_cw's flips keep their thin margin (0.007 /km).

### Integration fix round (2026-10-13, v0.18.0): the writer's fairing round cap

`scripts/ac/write_ai_line.FAIR_RADIUS_ROUNDS` 12 -> **24** [invented]. On the integration fix round's world (College Ave's
deck on its real abutments, the released ground, the rails) race_acw's fairing ran out of rounds with 9 box points still
tightened (the polish 4) and left a 5-point kink at the v1514 box exit, which `verify_ai_line` V3 filed as a 12.9 % phantom
speed dip (61 vs 70 km/h) — the gate was right, the solve was unconverged. With 24 it converges at 18 rounds (box points
left tightened 0), V3 0 dips; race_cw converges at 5 either way (unchanged). No threshold of the gate changed.

## 2026-10-13 — 0050 levelled fold pinches + `tools/verify_fold_fans.py`; drive_test's in-fan severe steps (ledger 0050)

**Why.** Kevin, from the seat: "the small steps are a problem at jackson/navajo". The 2026-10-11 weld pinched the
Navajo/Jackson inside edge at its HIGHER leg and left the lower leg's last row 6 cm away: a 901 % road triangle, a lip
0.13 m tall 3 m from the centre line and 0.47 m at the kerb. drive_test filed the street's 0.24 m of it as an exempt
"apron step" (w ≥ 9.5, |off| > 3.5), and the race layouts' severe 31 / 28 was shipped as "the next owner's"
(2026-10-11, "Named, not exempted").

### The weld (`tools/mouth_weld.unfold_line`, `level` follows `strict`: the weld's MAINLINE only)

| Number | Value | Why |
|---|---|---|
| `FOLD_LEVEL_ROWS` | 8 rows each leg [invented] | the diagnosis: 6 rows → 1 m second difference 0.031 m, 12 → < 0.025 |
| `FOLD_HALF_JUMP_MAX_M` | 0.28 m — ROAD edges and curb p0 / p1 only; p2 / p3 uncapped | derived: a 1.20 m K-rail buried 0.05 m covers no_route's [0.20, 0.90] band only within ±0.30 m of its reference, less a 0.02 m margin [invented]. Not the seal guarantee (the reference is the projected centre line, not the leg): no_route and verify_fold_fans (7) are. Measured at Navajo/Jackson: ROAD / p0 0.248, p1 0.251, p2 0.317, p3 0.359 m — capped, p2 / p3 stopped the build (the review's BLOCKER 1) |
| `FOLD_LEVEL_XFALL_MAX` | 4 % [invented] | an eased row's height change over its plan distance to the centre row (Navajo/Jackson: ~2 %) |
| overlap refusal | a leg window over another cut (or its windows) on the line | the result never depends on the order the cuts are found |

### The gate (`tools/verify_fold_fans.py <project>`, new; hard in `ship_sd.sh` / `ship_track.sh` after the race gates; `--force-install` does not cover it)

Per levelled pinch (`data/mouth_welds.json` `folds.MAINLINE.levelled`; a pre-0050 file: re-found on the ROAD edge rebuilt
from the gate centreline), per layout, on the BUILT gate OBJ, in the driven lane (street ±(w/2 − 0.5) less the median
island + 0.4 m; race `lane_by_vertex`), on wheel paths cut at their own self-intersection:

| Check | Threshold | Status |
|---|---|---|
| window | rows k − 8 − 4 … l + 1 + 8 + 4 (`WINDOW_PAD_ROWS` 4) | [invented] |
| paths | every 0.25 m across the lane, sampled every 0.05 m | [invented] |
| (1) FINE step | rise over 0.10 m beyond the previous metre's grade ≥ 0.02 m | 0.02 m = the diagnosis' step a tyre hits; 0.10 m window [invented] |
| race kerb lip allowance | ≤ 0.055 m when a `1KERB_race` kerb is on one side | the authored 0.05 m kerb + 5 mm sampling [invented] |
| (2) DT | 1 m second difference > 0.06 m, unless the metre touches a race kerb | drive_test `STEP_SEVERE_M`, reused |
| (3) road jump | two 1ROAD vertices ≤ 0.10 m apart in plan, heights ≥ 0.02 + 0.25 × distance apart | 0.10 m [invented] |
| (4) grass in the lane | > 0.02 m over the pavement beneath, on the rows the leveller moves (k − 7 … l + 8) | 0.02 m = (1)'s [invented]; the prep pins grass 0.02 m under the deck at its vertices, so facets graze the deck by millimetres between them (v0.17.1: up to 0.030 m at the hairpin's row 755, a row the leveller does not move) |
| (5) steep road triangle | plan area ≥ 0.01 m² and slope > 25 % | both [invented]; the installed riser was 901 % |
| (6) the pinch at its midpoint | every road vertex within 0.02 m of X within 0.01 m of (y_k + y_l) / 2 | 0.01 m [invented] |
| (7) race walls | 0.5 m cells, base = 3×3 minimum, within 25 m of X; base + 0.05 − (no_route reference + 0.10) within ±0.28 m | 25 m [invented]; ±0.28 m derived as above; the 3×3 aggregation is the 0050 review's |

Calibration (the review's BLOCKER 2: as first specified the gate failed the FIXED build): scoped by the driven lane, not
by exempting curbs (the street median curb is outside the lane); to the levelled pinches (the chord mends' pre-existing
0.07-0.08 m race DT stay drive_test's); grass by depth on the moved rows. Teeth on the installed v0.17.1 OBJs: FAIL at
Navajo/Jackson on (1) (2) (3) (4) (5) (6) (7) — 45 / 44 / 44 paths, FINE 0.422, DT 0.481 / 0.465, the 901 % triangle,
0.499 m between two vertices 0.055 m apart, grass 0.192 m over the road, X 109.310 vs 109.061, walls +0.498 — and at the
hairpin and College/Navajo on (6) only. On v0.18.0: PASS, 3 pinches × 3 layouts (ledger 0050 Results).

### drive_test (engine; opt-in by `data/mouth_welds.json`, every other track byte-identical)

| | Before | After |
|---|---|---|
| a severe step (> 6 cm) inside a levelled fold fan | "apron step" on pavement ≥ 9.5 m wide past 3.5 m (exempt) | severe (fan = rows k − B … l + 1 + B of each levelled ROAD pinch, discs of half-width + 0.5 m [invented]; a pre-0050 file: every ROAD cut) |
| a bump (2.5-6 cm) there | apron bump | unchanged: measured, the fixed-station paths read 56 street "bumps" in the two fans from their own changing spacing round corners tighter than the offset (2.5-4.7 cm on a 2-3 % grade) where verify_fold_fans' real paths read ≤ 0.025 m |
| the seam's 0.06-0.07 m street step (s 12-13, a chord mend) | apron step | unchanged (race_cw already counts it); not 0050's |

A weld that records a different row count from the gate centreline is refused (SystemExit).

**Measured** (v0.18.0 full rehearsal): street severe 0, bumps 0.15 → 0.0 /km, kinks 3.86 → 3.41, soft top 42 → 41;
race_cw severe 31 → 22, soft top 23 → 9; race_acw 28 → 20, 22 → 9; no_route BUILT PASS both (walls' worst offset near X
+0.263 m); audits unchanged; verify_mouths byte-identical to v0.17.1.

## 2026-10-14 — race layouts on their own LAP: every race gate counts along the layout's line (ledger 0054 phase 2 groundwork)

Phase 2 (Mission Gorge Speedway) needs a race lap that runs partly on the loop and partly on the expansion roads.
Every race tool read exactly one lap line — the mainline centreline — and counted along it by vertex number. Opt-in
now: `layouts[].lap = <lap id>` on a race layout, `race.laps.<lap id>` = `{pieces, corridor, kerbs, roads}`
(`scripts/geometry/race_lap.py`: the pieces stitched VERBATIM, junction gaps bridged by points resampled on the
straight join at the pieces' median spacing, closed, with `source_by_vertex` back to (line, vertex)). **No threshold
changed**: every gate below runs the same rule on the lap's own line and declaration
(`data/lap.<lap>.json`, `data/barrier_bands.<lap>.json`, `race_authored.<lap>.json`). A track whose layouts name no
lap runs byte-identical (the identity proof: the full v0.18.0 chain with main's tools and with these, md5 of every
output — the report of this change).

| Gate / tool | On a lap layout |
|---|---|
| `tools/barrier_bands.py` self-gates 1-12 + PLANNED no_route | one declaration per group (the mainline's race layouts → `barrier_bands.json`, each lap's → `barrier_bands.<lap>.json`); the lap's mouths = its pieces' side streets (a side street of a piece walked backwards flips side) + the BRANCH it abandons at each junction |
| `tools/no_route.py` | the lap's line + declaration; a probe carrying `xz` (a branch) is tested at that point |
| `tools/verify_race.py --lap <lap>` | A-O + F + G on the lap group; K now also fails a common object whose name carries the wrong group's lap token (or none) — the split routes on it |
| `tools/check_race_kn5.py --role common --lap <lap>` | `<slug>_race_<lap>.kn5`: every strip / kerb named `lap<lap>`; without `--lap` none may be (new check, same FAIL wording class) |
| `scripts/ac/verify_kn5.py` (f) / (g) | each lap's common kn5 checked like `<slug>_race.kn5` (+ the lap-token routing), stray `<slug>_race_*.kn5` fails; a lap layout's spawns judged on the lap (kn5 frame) against its own lane; its ini lists `<slug>_race_<lap>.kn5` |
| `scripts/geometry/drive_test.py`, `median_zone.py`, `audit_mesh.py --layout` | the lap's line + declaration (the fold-fan discs stay on the mainline rows the weld indexes) |
| `tools/verify_fold_fans.py` | a pinch the lap does not run over is skipped for that layout (behind its walls); the others take the lap's lane mapped back to the mainline row |
| `scripts/ac/write_ai_line.py` + `tools/verify_ai_line.py` | the line is drafted on `data/lap.<lap>.json`; the gate reads only the line and the BUILT OBJ (unchanged) |

New constants (all in `scripts/geometry/race_lap.py`):

| Constant | Value | Flag |
|---|---|---|
| `DEDUPE_M` — consecutive piece ends this close are one point (no join) | 0.25 m | [invented] |
| `BRANCH_PROBE_M` — a branch probe stands this far past the lap's curb along the abandoned line | 10 m | = `barrier_bands.MOUTH_PROBE_M` (the side-street probe), reused |
| `BRANCH_ON_LAP_PAD_M` — a "branch" whose probe lies within half-width + this of the lap is the lap itself | 1.0 m | [invented] |
| `CONNECTOR_ISLAND_SNAP_M` — a connector vertex takes the island width of the nearest `connector_islands` point within this | 1.0 m | [invented] |
| join spacing | the pieces' median vertex spacing (`race.laps.<lap>.join_spacing_m` overrides) | measured per lap |

A stitched junction is a zero-radius corner: its inside offset never crosses itself, so `race_furniture`'s fold trim
has no corner to trim the inside kerb to (it stops with "author this corner by hand"). That is DECLARED, not derived:
`race.laps.<lap>.kerbs.trims` drops it with its why (tests/tools/lap_world.py does exactly that).

Proven by `tests/tools/test_race_lap.py` on a synthetic world (a 2.4 km rounded-rectangle mainline, a connector up
its middle, a 1.6 km lap = the west half + the connector): the lap declared with every self-gate and the planned fill
green, the mainline's declaration byte-identical with or without the lap, the seal holding planned and BUILT and a
gap across a branch caught (forbidden probe + leak), spawns on the lap, the AI line inside its corridor and green on
`verify_ai_line`, drive_test's lane = the lap's (barrier_missing 0; a missing closure → `closure` missing), the lap's
ini loading its own common kn5.


## 2026-10-14 — road_datum PROFILE WINDOWS + Lake Murray Blvd's decks + the assembler's per-window sigma_y (ledger 0057)

Kevin (v0.18.0): "my cars with clutches would roll back from stoplights there ... Stoplight would be heading onto Alvarado
from college." The diagnosis (ledger 0057) measured the two uphill waits flattened by two stacked smoothings of the frozen
pre-median profile (the August heightfield's 33 m median + 2 x 39 m box means + lap-seam blend, then the assembler's
sigma_y 5 Gaussian, ledger 0042): College southbound into the Alvarado signal +3.5 % built against +5.9 % real, Alvarado
from 70th -6.1 % against -7.7 %, the 70th junction 0.7 m low behind Lake Murray Blvd's 1.2-2.1 m-low decks. **No gate
threshold, bypass or exclusion changed.** This is a datum change, opt-in per declared window; outside every window the
assembler's profile is byte-identical to its sigma_y 5 result on the same input (and on the College main descent
identical to v0.18.0).

| What | Value | Flag | Why |
|---|---|---|---|
| `tools/deck_datum.PROFILE_SIGMA_M` | 3 m | [invented] | Gaussian on the 1 m 3DEP profile inside a window (= 1 centreline vertex): rounds the DEM's +-10 cm sample noise. Swept 2 / 3 / 4 / 6 m (simulated on both windows, ledger 0057 Fix): 6 m (the diagnosis' "sigma ~2 points") cost the two stop-line approaches another 0.07 / 0.21 points and bought nothing the gates need |
| `tools/deck_datum.PROFILE_BLEND_M` | 30 m | [invented] | default blend into the old profile at each window end (`road_datum.profiles[].blend_m`); both window ends sit where old and fresh agree within ~0.2 m |
| profile reference | mean of 3DEP at both carriageway centres (+-width/4 off the line) | measured choice | the line itself reads the crown: on College's approach the centre line runs +5.3 % where both lanes run +5.8-5.9 %; the mean of the two carriageway centres reads the lanes |
| deck spans inside a window | held straight between abutments, one-sided `SMOOTH_M` reads (the deck rule) | reused | a profile never reads the I-8 trench or Alvarado Creek |
| `road_datum.profiles[].hold_straight_m` (new key) | College/Alvarado: pre-median s 2289-2323 | measured (rehearsal 1) | the hairpin's levelled fold fan (rows 763-774, ledger 0050) pinches its inside edge to ONE height and cannot carry the real hump: with the hump in it the first full rehearsal failed `verify_fold_fans` (DT 0.087 m > 0.06 on the inside paths, all three layouts) and doubled drive_test's severe steps there (race 22/20 -> 39/37). Held straight like a deck span it passes (DT 0.028-0.034) |
| `road_datum.profiles[].assembler_sigma_y_pts` | 1.0 pts College/Alvarado, 1.5 pts 70th/Alvarado | [invented], rehearsed | inside a window the input is already fresh 3DEP smoothed at 3 m, which is what 0042's sigma 5 was written for. Rehearsed: 1.5 / 1.5 -> College stop line +5.23 %, every listed gate no worse than v0.18.0; 1.0 / 1.0 -> +5.44 % but street kinks 3.41 -> 3.56 /km (refused); 1.0 / 1.5 -> +5.44 %, street kinks 3.34 /km, every listed gate no worse (shipped) |
| `road_datum.profiles` (Lake Murray) | `college_alvarado_junction` pre-median s 2200-2530; `seventieth_alvarado` 13280 -> seam -> 230 | measured | fresh 3DEP 1 m, 2026-10-14 (data/deck_datum.samples.json, TLS on) |
| `road_datum.decks` (Lake Murray, added) | `lmb_over_i8` 13347-13424 (126.2 -> 126.2 m), `lmb_over_alvarado_creek` 13432-13457 (126.2 -> 125.6 m) | measured | the item ledger 0046 deferred: fresh 3DEP abutments at both carriageway centres; both lie inside `seventieth_alvarado`, which holds them (their own window pass is skipped and reported `re_derived_by_profile`) |

Refusals (SystemExit, no silent fallback): a profile window cutting a deck span; a hold inside the window's blend; a
window shorter than twice its blend or not shorter than the lap; a seam window on an open line; an uncached 3DEP sample
under `--offline` (L2). The closing duplicate vertex is v0's height, never a second vertex (L13). `smooth_centerline`
refuses a weight list that is not one per unique vertex.

Wiring: none new — `tools/deck_datum.py` is already the first draft step (ship_sd.sh / ship_track.sh) and its cache
already rides TERRAIN_DATA; `scripts-v021/blender/build_loop_blend.py` reads the same `road_datum.profiles` (stations on
the pre-median file, index-aligned with raw.local) and passes `y_sigma_windows` only when one is declared.

Gates on the shipped config (full `ship_sd.sh --no-install` rehearsal, v0.18.0 -> this): street soft top 33 -> 31,
severe 0 -> 0, kinks 3.41 -> 3.34 /km, audit D/K/I/F 0/20/20/13 unchanged; race severe 22 -> 17 / 20 -> 17,
barrier_missing 0, no_route BUILT PASS both; verify_fold_fans, verify_mouths (4), verify_signs, verify_race,
verify_ai_line (both), rib_check, house_seat_check PASS. Not on the list and slightly up: race_cw kinks 6.23 -> 6.45 /km
(race_acw 7.05 -> 6.38) — reported, not gated.

Proven by `tests/tools/test_profile_datum.py` (a seam window on a closed ring moves both sides, keeps v0 closed, leaves the
rest untouched, is idempotent; a deck inside a profile is held by it; a hold is straight and refused inside the blend;
offline refuses a gap; the assembler's windows are exact outside and keep a crest inside; Lake Murray's declaration
resolves and runs offline from the committed cache to the real grades) and the rehearsal in ledger 0057 Results.

### Fix round (2026-10-14, after the refutation): the fold-fan fit replaces the held box

The truth lens refuted round 1 on its own stop-line range: `hold_straight_m` held the College/Alvarado junction box
(pre-median s 2289-2323) straight, so the crest sat 0.55 m under the real road centre (1.15 m under the southbound
lane) and a car stopped a few metres into the box got a much shallower hill than real (last 15 m to s 2305: built
+2.92 % against a real +7.16 % on the lane). Cause, measured on a model of the ribbon that reproduces the built gates
(the fan model read 0.0868 / 0.0342 m where `verify_fold_fans` read 0.087 / 0.034 on rehearsals 1 / 4; the
drive_test replica read rehearsal 5's 10 street severe steps at the same stations and heights to 1 mm): two gates
judge this corner on paths a tight hairpin bends out of shape. Every wheel path inside the fold fan folds and is cut at
its own self-intersection, so it turns sharply at a point on the corner's medial axis and its grade jumps there by
the surface's slope along the axis; and drive_test's fixed-offset wheel paths jump sideways where the segment normal
turns. The real crest inside the fan fails both (fan DT 0.076-0.087 m; with the fan alone fitted, rehearsal 5: street
severe 0 -> 10, kinks 3.41 -> 5.86 /km, race severe 22 / 20 -> 27 / 26). The box passed both by removing the crest.
**No gate threshold, bypass or exclusion changed.**

| What | Value | Flag | Why |
|---|---|---|---|
| `road_datum.profiles[].hold_straight_m` | removed (code and config) | — | replaced by `fold_fan_fit` |
| `road_datum.profiles[].fold_fan_fit` (new key) | College/Alvarado: `fit_m` pre-median s 2250-2340, `dt_max_m` 0.05 | `fit_m` measured; `dt_max_m` [invented] | inside `fit_m` the profile takes the change with the smallest misfit to the 3DEP target (heights, grades, grade changes, on the heights the assembler will build) that keeps (1) every levelled fold pinch within `dt_max_m` on `verify_fold_fans`' own `survey_pinch` and (2) drive_test's wheel paths over `fit_m` +- 10 rows (street; a race lane both ways) at no severe step and no more kinks, nor kink excess, than the frozen profile had there as v0.18.0 built it — read on the ribbon the build will carry (the assembler's own smoothing: 5e-5 m from the built centreline; `mouth_weld.unfold_line` levelled; drive_test's own constants). Outside `fit_m` nothing moves. `fit_m` ends at 2340: a fit reaching 2360 steepened College's flank into a sag at s 2328-2346 where the seated ground's 10 m facets came up through the road by up to 9 mm (drive_test soft tops street 33 -> 39, race 9 -> 21 / 19; rehearsal 6) |
| `tools/deck_datum.FAN_DT_MAX_M` | 0.05 m | [invented] | the gate's `DT_MAX_M` 0.06 less 0.01 for the model |
| `FAN_COARSE_MARGIN_M` | 0.003 m | measured | the solver surveys the pinches at 0.5 / 0.1 m (the gate: 0.25 / 0.05); that read up to 0.0029 m under the full survey; it solves to 0.047 and the full survey of the result must meet 0.05 |
| `FAN_BUMP_SPACING_M` / `FAN_BUMP_SIGMA_M` / `FAN_TAPER_M` | 6 / 4.5 / 12 m | [invented] | Gaussian bumps ~2 vertices apart, never one vertex; faded to zero at both ends of `fit_m` |
| `FAN_GRADE_WEIGHT_M2` / `FAN_BEND_WEIGHT_M2` | 100 / 400 m^2 | [invented] | the misfit weighs a 1 % grade error like 0.1 m of height and a 1 % grade change between neighbouring vertices like 0.2 m: on heights alone the fit steepened College's last 15 m to the stop line 1-1.5 points past the target |
| `FAN_WHEEL_PAD_ROWS` | 10 rows | [invented] | drive_test's wheel paths are walked over `fit_m`'s rows +- 10 (~30 m) |
| race lane for the wheel paths | the full street between the edge strips, `w/2 - race.edge_inset_m` (0.82) each side | measured | the declared corridor is that box through the hairpin (barrier_bands `lane_by_vertex` +-14.18 at w 30); the declaration itself is authored later in the chain |
| `FAN_STEP0_M` / `FAN_STEP_MIN_M` / `FAN_PENALTY` / `FAN_COUNT_PENALTY` / `FAN_MAX_EVALS` | 0.16 / 0.01 m / 1e7 / 1e3 / 2500 | [invented] | deterministic coordinate descent from zero, one step per coordinate per sweep, halved to 1 cm; every constraint a hard wall |
| `FAN_MAX_MOVE_M` | 0.25 m | [invented] | a fit that moves a built height further than this from the 3DEP target is refused (a pattern-search variant of the descent settled 0.6 m off on Alvarado's leg; not shipped) |
| 3DEP read position inside `fit_m` | the plan the assembler builds (its smoothing of the line), tapered over `FAN_TAPER_M` | measured | round the hairpin the assembler's plan smoothing moves the line up to 3.6 m and the junction tilts 8 % across: read on the pre-median plan, the slab sat 0.1-0.3 m off the real road under the built one. Outside `fit_m`: the pre-median plan, as before (median_envelope moves divided roads after this step; no median reaches a fold fan) |
| `road_datum.assembler_smooth` (new key) | `tracks/san-diego-lake-murray/scripts-v021/geometry/smooth.py` | wiring | the module the fit predicts the build with; a `fold_fan_fit` without it is refused |
| `fold_fan_fits` in data/deck_datum.samples.json | the solved bump amplitudes, keyed by the md5 of everything the solve reads | cache | a solve takes 3-5 min; a hit is re-surveyed in full like a fresh solve (rehearsals 5-7 hit it; a fresh solve reproduced the cached amplitudes and the pre-median output byte for byte); the file already rides TERRAIN_DATA |

Refusals (SystemExit): `fit_m` inside the window's blend; no `assembler_smooth`; a fit that cannot meet the fan target
(solver or full survey), a fine step on the pinch paths, a severe step or extra kinks on the wheel paths, a move past
`FAN_MAX_MOVE_M`, a pinch reaching past the surveyed rows, a pinch the weld would refuse (half-jump, cross-fall) — each
says "author the junction as a pad (JUNCTIONS 2.0 B)".

Level slab, the reason now measured: the race layouts run the junction's full width and the race walls' containment
is judged against the centre line (no_route BUILT, `verify_fold_fans` (7): +-0.28 m); the real 8 % tilt puts the walls
1.1 m off it 14 m out.

Gates on the shipped config (rehearsal 7, full `ship_sd.sh --no-install` on fresh scratch copies, v0.18.0 -> round 1 ->
this): street soft top 33 -> 31 -> 9, severe 0 -> 0 -> 0, kinks 3.41 -> 3.34 -> 2.97 /km, audit D/K/I/F 0/20/20/13
unchanged; race severe 22 / 20 -> 17 / 17 -> 17 / 18, soft top 9 / 9 -> 9 / 8 -> 8 / 7, barrier_missing 0, no_route BUILT
PASS both; verify_fold_fans PASS (hairpin DT 0.047 street / 0.044 race, grass-on-top 0), verify_mouths (4), verify_signs,
verify_race (+ scenery), verify_ai_line (both), rib_check, house_seat_check PASS. Not on the list: race kinks 6.23 /
7.05 -> 6.68 / 6.82 /km. Rehearsals 5 (the fan alone: street severe 10, race 27 / 26) and 6 (`fit_m` to 2360: soft tops
39 / 21 / 19) were refused by these same comparisons. The built profile against fresh 3DEP is in ledger 0057.

Proven by `tests/tools/test_profile_datum.py` (a crest in a synthetic hairpin's fold fan is carried, the fan within
`dt_max_m`, drive_test's street paths no worse, nothing outside `fit_m` moved, the cache re-used to the same bytes; the
refusals; Lake Murray's declaration and its committed cache).

**Round 3 (same day, after the second refutation): no threshold, constant or config changed.** The truth lens refuted on
stops at s 2305-2309, which lie inside the intersection box: College's southbound signal is at s 2312.3 and Alvarado's at
s 2273.2. I re-ran the fit offline with each limit relaxed in turn, to find the bound; the table is in ledger 0057 round 3.
- `dt_max_m` 0.05 -> 0.057: no change. The fan settles at 0.047 either way, so it is not the binding limit.
- drive_test's kink cap round the hairpin is the binding limit. Freeing it buys ~1 point at s 2305-2308. The cost is
  street kinks/km past v0.18.0 (2.97 -> ~4.2, against 3.41) and race kinks ~2.5x at the corner.
- No gate at all: a level slab still misses s 2305 by 0.8 points on 15 m. That needs crossfall, which the race-wall band
  (`WALL_BAND_M` 0.28 about the centre line, no_route BUILT) forbids above ~2 %.

None of these variants shipped, and `FAN_DT_MAX_M` stays 0.05.

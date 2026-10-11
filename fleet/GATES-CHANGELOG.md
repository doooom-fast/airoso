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

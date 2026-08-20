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

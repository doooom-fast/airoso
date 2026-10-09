---
id: 0042
title: "Smooth out the roughness" — 3DEP sample noise read as texture under the wheels
status: in-progress
scope: tracks/san-diego-lake-murray (route.smooth_sigma_y_pts; tools/route_connectors.py smoothing)
layer: track + tools
train: -
---

## Symptom (Kevin, seat, 2026-10-09, on the locked V3 build)

> "lock this all in and smooth out the roughness"

## Diagnosis

The road profile is USGS 3DEP sampled every 3 m (noise ~±10 cm); the assembler's vertical
smoothing was `smooth_sigma_y_pts` 1.5 (~4.5 m) — every sample step is a felt event
(fleet/reference/MEASURED.md: pro road grids 0.3–1.1 m with smooth profiles). Side streets were
smoothed once over 45 m. The locked build measured kinks 8.09/km, bumps 2.37/km.

## Fix (built this day)

`route.smooth_sigma_y_pts` 1.5 → 5.0 (~15 m: rounds sample noise, keeps the real grades — the
climbs are hundreds of metres long); side-street elevation smoothing 45 m ×1 → 75 m ×2
(`tools/route_connectors.py`). Measured on the gate OBJ: **kinks 8.09 → 4.97/km**, soft-ground-
in-lane 130 → 82, excursion drops 103 → 101, severe 0, no metric worse than the July reference
(kinks 47.18/km there). Replication vs measured road: median 0.05 m, p95 0.42 m.

## Verification

Kevin's seat. If still rough: next levers are denser stations (3 → 1.5 m resample, with the same
smoothing) and the kerb/edge seams; ledger 0031 (bumps not in the profile) stays open for what
smoothing cannot explain.

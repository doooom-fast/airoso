---
id: 0031
title: The drive test's bumps are not in the elevation profile — a recorded negative result
status: open — cause not yet located; the profile is ruled out with evidence
scope: both calibration tracks; likely every track, since the metric is mesh-side
layer: engine
train: R5
---

## Symptom

With the elevation source fixed (0030), Mount Panorama builds to 2.38 m vertical RMS against its
reference — and still fails `drive_test`:

```
bumps >2.5 cm /km      : 94.43 (limit 75 for tarmac)
severe steps (>6 cm)   : 140
```

Everything else in the gate is clean: 0 obstructed stations, 0 daylight gaps, 0 floating furniture,
0 undrivable corners, replication vs measured road median 0.00 m / p95 0.21 m.

So the track is accurate and correctly seated, and still reads as rough to a car.

## The hypothesis, and why it was wrong

The obvious suspect was the centerline profile. SRTM has 30 m posts and we interpolate them to a
3 m centerline, so it is natural to assume the leftover ripple is what the wheels feel.

That was tested properly rather than assumed. An offline proxy for the bump metric — local
non-linearity `|z[i+1] - 2z[i] + z[i-1]| > 2.5 cm`, per km — was swept across 19 filter settings on
both calibration tracks, and it looked like a clean win on both axes at once:

| | Bathurst RMS | Bathurst proxy bumps/km | Nords RMS | Nords proxy bumps/km |
|---|---|---|---|---|
| `snap_to_ground` (shipped) | 2.43 m | 79.4 | 4.79 m | 78.6 |
| pre-smoothed at DEM scale | **2.17 m** | **0.0** | **4.57 m** | **0.0** |

More accurate *and* apparently 79x smoother. It was implemented, both tracks were rebuilt, and the
gate was re-run:

| | replication vs measured road | ground-on-top | real bumps/km |
|---|---|---|---|
| `snap_to_ground` | median 0.00 m, p95 0.21, max 1.56 | 31 | 94.4 |
| pre-smoothed | median **0.81 m**, p95 2.20, max 3.81 | **94** | 90.1 |

**The real bump count moved 94.4 → 90.1.** Four percent, not ninety-nine. And the cost was the one
thing that is not negotiable: the deck came off the ground by a median 0.81 m, and terrain
poked through the road in three times as many places. That is precisely the float
`snap_to_ground` was written to prevent, and its docstring already says so in Kevin's words —
*road touching ground takes precedence*.

Reverted. `scripts/elevation/heightfield.py` carries the measurements inline so the next person
does not re-run the experiment.

## What this establishes

1. **The centerline elevation profile is ruled out as the source of the bumps.** Changing it by
   enough to move the proxy from 79 to 0 moved the real metric by 4%.
2. **The offline proxy was invalid.** It measured curvature of the centerline z profile;
   `drive_test` sweeps 10 wheel paths across the *built triangles*. Those are different surfaces —
   the wheel paths cross the road ribbon laterally, pick up crossfall, the shoulder/ring joins and
   the terrain grid, none of which the centerline profile knows about.
3. Therefore the roughness is **mesh-side**, downstream of elevation.

## Where to look next

Unproven, in rough order of suspicion — the point of this entry is that none of these have been
tested yet, so none should be treated as the answer:

- the 40 m terrain heightfield being sampled under a 3 m road, so every grid cell boundary is a
  potential step where road meets terrain;
- crossfall/superelevation applied per station, which can kink between adjacent stations;
- the shoulder / ring-annulus joins, which the gate already reports as `severe` step locations;
- the lap seam — the worst severe step on Bathurst sits at station 2.0 m, and the git history
  already has a lap-seam entry (0017).

The correct next move is to instrument `drive_test` to report *which mesh group* each bump lands
on, rather than to guess and filter again.

## The transferable lesson

0030's lesson was "score the data before tuning the code". This is its twin: **score against the
real gate, not a proxy you built for speed.** The proxy agreed with the hypothesis and was wrong by
a factor of twenty-five, and the only reason that was caught is that the change was pushed all the
way through a rebuild and re-gated instead of being accepted at the sweep.

A gate-green number obtained from a stand-in is not evidence. Run the gate.

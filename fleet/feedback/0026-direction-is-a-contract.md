---
id: 0026
title: Direction is a contract — the AI writer had no concept of it, and IMI ran backwards
status: diagnosed
scope: k10-colorado/imi (fixed); k10-san-diego/project (canon question OPEN)
layer: engine
train: R2
---

## Symptom (Kevin, from the IMI cockpit, 2026-08-07 ~1:30pm)

> "the cars appear to start in the wrong direction for the race, or the course is set the wrong
> direction, one or the other. also the direction complains periodically no matter which
> direction i drive"

## Evidence

Measured on the installed artifact: the grid→timing-line heading vs the generated AI line's
forward vector at the same spot — **alignment dot = −0.93, exactly opposite.** The installed
v0.16-era IMI kn5 predates today's start-placement heuristic entirely (its start complex sits
~240 m from both of today's dummy candidates), and `write_ai_line` had no direction parameter:
it always ran the centerline order. Cars gridded facing one way, the spline ran the other, and
AC's direction logic (spline-based) contradicted the track (dummy-based) — the intermittent
wrong-way complaint in both directions.

## Fix (landed same hour)

`write_ai_line --reverse` reverses points+widths before the build (L13-safe). IMI regenerated
reversed and reinstalled: **dot now +0.96**. Verification: restart the session; the field should
launch the way the grid faces and lap in ~65 s.

## The open half — Lake Murray canon (needs Kevin's word)

The sd-restart canon records Kevin drives **Jackson → Navajo → College → Alvarado — the REVERSE
of the OSM-stitched centerline order** the current build runs (grid, AI, and timing all follow
forward order; the spawn wore a wrong-way icon). If the loop should run his direction, the fix is
a rebuild on the reversed centerline (the engine already computes `dummies_reverse`) plus a
`--reverse` AI line. Traffic lanes are unaffected (both directions exist by construction).
One question decides it; this entry holds until he answers.

## The durable rule

A track's driving direction is REQUIREMENTS (the memory's mistake #4, learned the hard way),
and every direction-bearing artifact — dummies, AI spline, cameras' IN/OUT windows, ui `run` —
must derive from ONE declared direction in `track.config.json`, not from whatever order the
source data arrived in. Wiring that key through the writers is the engine follow-up.

---
id: 0057
title: "Coming down college toward 8 should be pretty steep and doesn't feel that way, same with heading down Alvarado from 70th"
status: open
scope: tracks/san-diego-lake-murray mainline profile (College southbound v1506 -> v761; Alvarado westbound v0 -> v761)
layer: project or engine (to be diagnosed)
train: -
---

## Symptom (Kevin, 2026-10-14, v0.18.0)

> "Also diagnose some of the hills? Coming down college toward 8 should be pretty steep and doesn't feel that way, same
> with heading down Alvarado from 70th. It could be perceptual, real world vs sim but I know on those hills my cars with
> clutches would roll back from stoplights there"

> "Stoplight would be heading onto Alvarado from college" (Kevin, same day)

The roll-back spot is the **College -> Alvarado signal** at the bottom of College by I-8 (the College hairpin / College
interchange area, ~v761): the approach grade to that signal, in the direction a car waits facing uphill, is the number
that has to match the real hill.

## Diagnosis

Open — read-only measurement running: built grade (v0.18.0 gate OBJ) vs fresh 3DEP on the pavement, per 25 m and at
every signal approach, the pipeline stage where any flattening happens, and the perceptual case if the grades match.

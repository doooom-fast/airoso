---
id: 0056
title: "Make lighter lamp model" / "more modern" — the streetlight is 57 % of the track's vertices
status: open
scope: tracks/san-diego-lake-murray lamps (tools/author_lamps_blend.py, the lamp asset, LIGHTPOST / LIGHTS meshes, data/lights.local.json, ext_config [LIGHT_n]); every later lamp (expansion D4, phase 3/4)
layer: project + asset
train: -
---

## Request (Kevin, 2026-10-14)

> "make lightr lamp moidel" — "morew modern" — "Taller too"

## Evidence

Installed v0.18.0 road kn5 (116.3 MB; 1,697,179 verts / 2,026,253 tris): LIGHTPOST = 17 meshes, 966,725 verts (57.0 %),
899,835 tris (44.4 %), for 243 lamps (~4,000 points each); six LIGHTPOST meshes at AC's 65,535 cap (ledger 0054).
Both expansion plans make a lighter lamp the precondition for more lamps (Phase 4 projects 161-174 MB without it).

## Fix (defaults)

A modern street light (a contemporary LED cobra-head / shoebox fixture on a tapered steel pole with a mast arm, the
kind San Diego streets carry now) at about a tenth of today's points, same positions and heights, same light: the 80s
low-pressure-sodium colour, intensity and pool shape Kevin approved (ledger 0043) stay exactly as they are — only the
fixture changes. CSP light sources stay at the lens.

## Verification

Per-lamp and total LIGHTPOST points; road kn5 size before/after; ext_config [LIGHT_n] positions unchanged (or moved with
the lens by a recorded offset); lamps out of every lane (verify_race scenery gate, drive_test obstruction 0); day and
night stills; Kevin's seat (look, load time, FPS).

**Taller (Kevin, same day: "Taller too").** Mounting height raised from today's 9 m to a modern San Diego arterial
height (~11-12 m / 35-40 ft, justified and recorded), arm reach to match; the CSP light rises with the lens, and the
on-road brightness Kevin approved is kept within ~±10 % by scaling the intensity only if needed (recorded).

**Kevin on the preview stills (2026-10-14): "Excellent".** Built and verified on branch worktree-wf_e79d8855-406-1
(2ca5363): LED cobra head, Caltrans ES-6A Type 21 35 ft pole + 12 ft arms, 371 kn5 points per lamp (was 4,045), road
kn5 116.3 -> 72.7 MB, light 11.33 m over the road, intensity unchanged (0.013), twin arms kept as shown. Ships in
v0.18.1 with 0055 and 0057; the seat (look at night, pool brightness, load time) closes it.

> "They could be a little brighter" (Kevin, same day, on the preview)

Intensity 0.013 -> **0.015** (+15 %, the ladder's next step after 0043's 0.010 -> 0.013), committed on the lamp branch
(4992d16); colour and pool shape unchanged. Seat-tune from there (config-only, no rebuild).

# Realism — the doctrine, and the plan to get there

*Written 2026-08-06, the day the original Lake Murray came back from `loop.blend`. This is the
course correction after three weeks that ended with "delete the code. start over."*

`fleet/LAWS.md` is how a track is built *correctly*. `fleet/STANDARDS.md` is how a repo is shaped.
This file is about the thing neither of them measures: **whether the track is believable** — whether
Kevin gets out of the car and says it felt like the real place. Everything below serves that one
test.

---

## 1. The verdict of the last three weeks

What was tried: a fully procedural pipeline — real centerline, real elevation, generated ribbon,
generated terrain, generated furniture, four gates, straight to kn5. It produced nineteen ledger
entries of geometry chasing (junction flares, floating edges, sawtooth widths, seam bugs, roughness
with no found mechanism) and, in the week of 2026-08-01, three consecutive builds of Kevin's
childhood neighbourhood that were each *worse to drive than the original* while every gate was
green. The attempt to eject Blender entirely (generated OBJ → native kn5 writer, no hand pass)
shipped floating roads, seams in curves, and jumps. Kevin's verdict, verbatim: **"we need to keep
blender in the loop because this shit was god awful."**

The structural insight, stated plainly so it never gets optimised away:

> **The gates measure self-consistency. Believability is authored, and nothing in a fully
> procedural pipeline authors it.** No great AC track mod — not one — was generated end-to-end
> from data. The greats put real-world data underneath a human author. Our advantage is that the
> author's hands can be Claude's, working live inside Blender, with Kevin directing from the
> driver's seat.

So we stop trying to eject from Blender and lean in. This was already SD law
(`loop.blend` is truth, the hand pass is part of the product — "Kevin designs, Claude operates");
it is now fleet doctrine.

## 2. The three jobs

Every piece of work in this repo now belongs to exactly one of these:

**Job 1 — The engine prepares truth.** The pipeline's product is no longer a finished track; it is
a **data underlay**: perfectly-registered real-world data dropped into an editable `.blend`.
Real centerlines with per-vertex width/crown/superelevation, real elevation (and where the point
clouds support it, real road *surface*), terrain, aerial imagery draped for reference, OSM
furniture positions, junction polygons, reference photos pinned in space. Everything the engine
generates is **regenerable and unprecious** — it exists to be corrected.

**Job 2 — Authorship happens in Blender.** The `.blend` is the canonical per-track artifact.
Junction mouths, edge treatments, medians, driveways, landmark massing, the thousand small reads
that make a place recognisable — these are *authored*, by Claude operating Blender through the
live bridge with Kevin directing, or by Kevin's own hands. The engine never overwrites authored
work (see the collection contract, §4).

**Job 3 — The game is the judge.** Rule 0, institutionalised: nothing is true about a track until
seen in game. Gates still run on every exported artifact (a Blender-first track gates like any
other — 0013 bought that lesson). Above the gates sits an in-game harness on the Windows box: the
AI drives the track and telemetry judges the lap; fixed camera stations produce the same
screenshots every build for the eyeball pass; and Kevin's drive remains the only verdict that
closes an entry.

## 3. Learn from the masters, quantitatively

The fastest route to knowing what "good" measures like is sitting in
`D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks`: every Kunos laser-scanned circuit,
plus whatever reference mods we install beside them. `scripts/modkit/extract_kn5.py` already parses
kn5 (it is the exporter's exact inverse). It grows into a **study kit**:

- `modkit.inspect_kn5` — for any track: triangle density on the drivable surface (vertex spacing in
  metres, near-line vs far), object naming and hierarchy, per-material shader + params + texture
  sizes, mesh counts vs the 65k cap, total budget.
- `modkit.inspect_track` — the folder beside the kn5: `surfaces.ini` values (FRICTION, DAMPING,
  WAV_PITCH per surface), `ext_config.ini` features (GrassFX, RainFX, LightsFX, TreeFX, VAO patch
  presence), cameras, sections, AI line presence and point spacing.
- A **reference shelf** — a curated set per archetype, studied with the tools above, findings
  recorded in `fleet/reference/` as measured numbers, not impressions.

Those numbers become three things: **gate thresholds** (drive_test's bumps/km limits stop being
invented — they become "within the envelope measured on Kunos tarmac"), **Blender templates**
(road cross-section profiles, kerb sections, material setups that match what the good tracks
actually use), and **a presentation floor checklist** per archetype (§6).

Clean-room rule: we measure and imitate *technique*; we do not ship extracted third-party meshes or
textures. Mined props stay in private builds; anything shipped comes from Kevin's own Dropbox
library (ledger 0005) or license-clean sources.

And the study set is **already installed** — Kevin has curated the references himself, sitting in
`content/tracks` beside our own builds, one or more per archetype we build:

| Our archetype | Installed references |
|---|---|
| SD freeway network | `shuto_revival_project_beta` (the highway standard), `nohesi_110` (LA freeway + traffic) |
| Street / canyon ports | `la_canyons`, `pacific_coast_hwy`, `mulholland_v1`, `rt_california_highway`, `union_island` |
| Rally stages | `muracciole_vezzani` (Corsica roads), `Kruth_Larcenaire`, `glencoe`, `bilsen_road` |
| US club circuits | `oregon_raceway_park`, `willow_springs` — the direct IMI / High Plains / Pueblo analogs |
| Ground truth | every `ks_*` laser-scanned Kunos track; `ks_black_cat_county` + `ks_highlands` for how Kunos builds fictional road *networks* to scanned-track standard |

Worth acquiring: **Project Kaido's 2025 scratch rebuild of US-129** (Tail of the Dragon, v1.1,
rally layout planned) — the direct reference for our Dragon Tail stages — plus its community
traffic plan.

First R1 acts: inspect the k10 tracks with the same tools, side by side with their nearest
reference — the gap, in numbers, is the work list.

*Measured findings land in `fleet/reference/` as the study kit produces them; the web-research
notes that seeded this section are in `fleet/reference/RESEARCH.md`.*

## 4. The Blender seam, made first-class

What exists today, scattered: SD's `build_loop_blend.py` (data → editable .blend, deliberately not
an exporter), SD's `scripts/blender/live/` view tools (flythrough, render_still, inspect),
Colorado's `blender/live_server.py` operator bridge (Claude sends Python to a running Blender,
mainline-thread safe, state persists between calls). These are the right ideas living in the wrong
places. They move into the engine as `scripts/blender/`:

- **`underlay.py`** — the generalisation of `build_loop_blend.py` to every track kind: build or
  refresh the data underlay in a `.blend`, from the same `track.config.json` + `data/` the rest of
  the pipeline reads. *Landed 2026-10-28 (`scripts/blender/underlay.py`): the engine's `data/track.obj` into
  `loop.blend` as `GEN_*` collections, `AUTH_*` untouched, the scene never reset; `tools/ship_track.sh` runs it as
  the last draft step.*
- **`live_server.py` / `live_client.py`** — the operator bridge, promoted engine-side so every repo
  gets the same one.
- **`views.py`** — flythrough, fixed-station stills, section cuts. The same stations every time, so
  two builds are comparable frame by frame.
- **`export.py`** — `.blend` → `track.obj` → **all four gates** → kn5 → track folder. One path for
  every track; Blender-first no longer means gate-free.

This is not a bet against the grain — it is how the best in the community already work. LilSki
ships Kunos-adjacent US circuits from **Blender splines hand-matched to lidar** ("Blender's spline
functionality is superior to 3ds Max" — and even with lidar, he still authors the road on a spline).
Fat-Alfie's celebrated circuits are a loft along a hand-digitized centerline with three
cross-section profiles, drive-tested in AC from the first week. Our engine is the programmatic
version of exactly that loft; the underlay keeps it editable where their hands were
(`fleet/reference/RESEARCH.md` §A1, §A5).

**The collection contract** (the rule that makes regeneration safe):

| Collection prefix | Who writes it | Regeneration |
|---|---|---|
| `GEN_*` (road, terrain, kerbs, furniture, underlay refs) | the engine | replaced freely on re-run |
| `AUTH_*` (anything hand-shaped or Claude-authored) | Kevin / Claude-in-Blender | **never touched by the engine** |

Promoting a `GEN_` object to `AUTH_` is the author saying "this is mine now." A refreshed underlay
regenerates beside authored work, never through it. `loop.blend` (56.4 MB of Kevin's hands) is the
existing proof that a `.blend` can be the track's source of truth; the contract is what lets the
engine keep contributing to a file it doesn't own.

## 5. The surface is the feel

A sim track is felt through the tyres before it is seen. Three upgrades, in order of felt impact:

1. **Stop inventing smoothness.** Today the elevation stage samples a 1 m bare-earth DEM and
   smooths until gates pass — which is how 0018 ends up with "rough everywhere, mechanism not
   found" and the tarmac rally stages blocked on a bumps/km number we made up. The reference shelf
   gives us *measured* roughness envelopes from tracks that feel right; the elevation stage targets
   those envelopes (by surface class: interstate ≠ city street ≠ county gravel), and drive_test
   judges against them.
2. **Real cross-slope.** Crown on streets, superelevation on engineered curves (from the standards
   tables by curve radius and road class), gutter and shoulder profiles per archetype — in the
   underlay as per-vertex attributes, authored where reality disagrees with the tables.
3. **Point clouds where they pay.** 3DEP's source lidar (not the rasterised DEM) carries what the
   raster averages away: measured crown and superelevation (statistically, from corridor ground
   returns), embankments, cut/fill shapes, bridge decks. It does **not** carry IRI-scale bumps —
   those sit below the lidar noise floor and are synthesised to the measured envelope (layer 1)
   rather than shipped as DEM noise. Access is free and unrestricted (AWS EPT bucket); densities
   at our sites run ~2–21.6 pts/m². Details: `fleet/reference/RESEARCH.md` §B1–B3.

## 6. The presentation floor

What a 2026 player unconsciously expects from a finished track, per archetype — the things that
make a road read as *a place* rather than a ribbon in a void. Street ports: signage, utility poles,
driveways, mailboxes, the buildings that make a neighbourhood recognisable. Freeway: gantries,
barriers, lane striping, streetlights that light at night. Rally: nothing urban — spectator
clusters, hazard tape, the sparse high-desert reality of Rangely. Circuits: kerbs with real
sections, tyre walls, marshal posts, paddock mass.

For street ports the floor includes their actual product mode — **living traffic** (Kevin,
2026-08-07: "2real traffic is far more interesting to me than track day or races"): a CSP lane
graph (`traffic.json`) generated from the same centerline/width/junction data the underlay holds,
so the neighbourhood and the freeway are *cruised through moving traffic*, not lapped.

The floor is: real assets wired in (ledger 0005 — the Dropbox library, not the 1.1 MB stand-ins),
CSP `ext_config` per track (GrassFX, RainFX, LightsFX for the night freeway, TreeFX-grade trees,
baked VAO), **SurfacesFX gravel physics on the rally stages** (CSP ≥0.2.4 makes gravel feel like
gravel — we run 0.2.12.1), AI lines shipped (§7), UI + preview + cameras. The study kit turns this
from taste into a checklist with numbers; the checklist becomes part of `fleet.cli lint` so a
track can't quietly ship below the floor.

## 7. The in-game harness (rule 0 with teeth)

The Windows box is where truth lives, so the Windows box gets the harness:

1. **`fast_lane.ai` writer** — the engine holds the racing line in world metres
   (`data/finished_centerline.json`); the .ai format is a documented binary. Generate it offline.
   This is the keystone: without it nothing can drive a k10 track but a human. (Every k10 track
   ships without AI today — the generator died with the deleted week.)
2. **`ac_drive_test`** — launch `acs.exe` directly (`cfg/race.ini`, no CM UI), let the AI lap, read
   `acpmf_physics`/`acpmf_graphics` shared memory at ~100 Hz. Agreed gate scope (Kevin,
   2026-07-28): lap completes · tyres stay on the surface (catches mesh holes like 0017) · no
   unexplained contact (invisible wall/prop in the corridor) · speed and smoothness against the
   reference envelope (the in-sim counterpart to the metric 0018 fights blind).
3. **The eyeball pass** — the same fixed camera stations, every build, screenshotted in game (CSP
   free camera): junctions, known landmarks, the places feedback came from. Diffable by eye, or by
   Claude on this box before Kevin ever launches the sim.

The harness never replaces Kevin's drive; it decides whether a build is *worth* his drive.

## 8. What we stop doing

- **No more end-to-end generated releases.** The generated mesh is an underlay, not a product.
- **No more "gates green, therefore good."** Gates gate; only the game verdicts.
- **No more junction whack-a-mole in engine code.** The engine provides junction *data* (polygons,
  approach widths) and audits the result; the junction itself — sidewalk gaps, median noses, flare
  shapes — is authored in Blender once, per place, and stays authored. (0013's sidewalks-through-
  intersections is the class of bug this retires: sweeping one ribbon through every junction was
  the procedural pipeline doing authorship badly.)
- **No more asserting offline claims as track truth.** "The data says X; unverified in game" is the
  strongest sentence the pipeline may utter.

## 9. The trains

Sequenced so each train's output de-risks the next, with the proof track named up front. Ledger
entries ride their train per `fleet/feedback/README.md`; nothing ships per-item.

| Train | Lands | Proof, in game |
|---|---|---|
| **R1 — Study kit** | `modkit.inspect_kn5` / `inspect_track`, reference shelf under `fleet/reference/`, measured envelopes per archetype | n/a (produces the numbers the others gate on) |
| **R2 — In-game harness** | MSYS path fix re-landed · `fast_lane.ai` writer · `ac_drive_test` telemetry gate · fixed-station screenshots | AI laps **Lake Murray** (installed today) and a Colorado circuit; screenshots diff clean |
| **R3 — Blender seam** | engine `scripts/blender/` (underlay, live bridge, views, export), collection contract, S9 in STANDARDS ("Blender-first tracks run all four gates"), registry `method` fields updated | **Lake Murray**: underlay refreshed under `loop.blend` without touching Kevin's authored work; exported; gated; driven |
| **R4 — Surface truth** | roughness envelopes replace invented limits · crown/superelevation in the underlay · point-cloud corridor sampling where coverage allows | **0018 closes**: GJ + Pikes Peak inside the measured envelope, felt from the car; **Dragon Tail gravel** feels like a county road, not DEM noise |
| **R5 — Presentation floor** | 0005 real assets · archetype furniture (incl. the proposed `rally_stage` archetype) · CSP floor per track · lint checks for the floor | **Sand Creek** furniture reads as real (0005's own criterion); rally stages gain nothing urban (its regression case) |

R1 and R2 run in parallel — R1 is measurement (Mac or Windows, offline), R2 is Windows plumbing.
R3 is the structural change and waits for both (it wants R1's templates and R2's judge). R4 and R5
ride the reshaped seam. Pilot-first discipline throughout: every train proves on its named track
**in game** before any fleet-wide application; a train that hasn't been driven hasn't landed.

## 10. What this doesn't change

The fleet machinery stays exactly as it is: the engine seam (`scripts/` paths untouchable, consumers
run from `.engine/` at a pin), the registry, discovery by scanning, the four gates on every build,
the feedback ledger, trains, `fleet.cli`. The laws all stand — especially L1 (no invented roads),
L5 (gate the artifact), L12 (trust Kevin over the data). This plan changes **what the pipeline's
product is** (an underlay for authorship, not a finished track) and **what counts as done** (seen
in game), not how the fleet coordinates.

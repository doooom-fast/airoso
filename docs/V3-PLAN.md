# V3 Plan — One repo, white-glove authoring, deterministic gates

**Written 2026-08-19.** V3 = everything lives in **one repo (airoso)**; the engine is demoted to a
first-draft generator; Claude hand-edits geometry (in Blender and in readable intermediates);
deterministic gates (mesh-audit, drive-test, kn5 checks) are the quality bar; Kevin's seat is the
only thing that closes a loop. San Diego first, Sand Creek second.

This is not a new idea — it is the execution of a decision the fleet already made in writing:
`fleet/REALISM.md` (2026-08-06, in k10-track-agents) — *"gates measure self-consistency;
believability is authored"* — and k10-colorado's CLAUDE.md — *"Kevin is the designer. Claude is
the Blender operator."* V3 collapses the seven-repo topology those decisions were trapped in.

---

## 0. The actual map (recon findings, 2026-08-19)

Nine parallel recon agents inventoried everything. The short version:

| Repo | What it really is | Verdict |
|---|---|---|
| **k10-track-agents** | THE canonical engine (28k LOC, v0.66.3, 172 tags — it absorbed prodrive-ac-builder's full history) + the fleet doctrine (REALISM, LAWS L1–L13, DoD ladder, 36-entry feedback ledger, MEASURED.md reference numbers, gates, modkit, diag, tests+CI) | **Primary donor.** Its history becomes airoso's history |
| **prodrive-ac-builder** | Frozen 2026-07-25; verified strict git ancestor of k10-track-agents; **zero unique files** | Archive. Never source from it |
| **k10-colorado** | Thin engine consumer (already un-forked, M3 done); 9 track configs+sources; the **live Blender bridge** (only copy anywhere); PRO-KN5-CONSTRUCTION / ROAD-CONSTRUCTION / PIT-LANES docs | Harvest tracks, bridge, docs |
| **k10-colorado-rally** | Thin consumer; 4 rally stage configs with the best-annotated configs in the fleet | Harvest tracks + config style. ⚠ tracks/ is deleted-uncommitted in its working tree |
| **airoso** | V2 docs (HANDOFF, V1-AUTOPSY, gate changelog) + junction-preserving OSM graph + the three confirmed routes. ⚠ **Entire tree is uncommitted** (the repo's one commit contains only `.gitattributes`) | The destination. Commit it first |
| **prodrive-agents** | The telemetry/overlay product's docs. Zero track content (grep-verified) | **Out of scope entirely** |
| **k10-sd-v021** (not in the six!) | Broken git worktree — the **only copy on this machine** of the vanished k10-san-diego repo: `loop.blend` (56 MB), the San Diego project data, and the scripts that built the track you actually drive | **Hand-salvage. This is the crown jewel** |
| **engine-july** | Broken worktree of k10-track-agents; verified stale | Delete after salvage check |

**Provenance of the San Diego track you drive:** `san_diego_lake_murray` (installed, ~66 MB kn5,
Jul 26) was built on your Mac from **k10-san-diego** at engine pin v0.24.3 — not from any of the
six repos you pointed at. The Windows snapshot `k10-sd-v021` holds its sources, and its
`project/loop.blend` is already the intended hand-edit surface (that repo's own CLAUDE.md pivoted
to Blender-first before it vanished).

---

## Phase 0 — RESCUE (do first, ~30 min; five live landmines)

Work that exists in exactly one fragile place. Nothing else proceeds until these are safe.

1. **airoso is uncommitted.** `git add -A && git commit` in airoso — docs/, tools/, data/
   (including this file and HANDOFF.md) exist only on disk today.
2. **The newest engine geometry code is in a gitignored clone.**
   `k10-colorado/.engine/scripts/geometry/build_mesh.py` carries an **87-line uncommitted diff**
   (the `natural_ground` archetype + cut-edge excavation, with Kevin's 2026-08-09 verbatim
   diagnosis). It exists in **no git history anywhere**. Copy the patch into k10-track-agents and
   commit before anything re-clones or copies over it.
3. **Feedback ledger 0032–0036 are untracked** in k10-track-agents/fleet/feedback/ — today's San
   Diego diagnosis. Commit them.
4. **k10-colorado-rally's tracks/ is deleted in the working tree** (44 uncommitted `D` entries).
   `git checkout -- tracks/` restores; a careless `commit -a` would erase the repo's only content.
5. **k10-sd-v021 is a dangling worktree** (its `.git` points at a repo that no longer exists —
   git cannot read it). Copy the whole directory to a safe location now; it holds loop.blend,
   all San Diego project data, and 6.5k LOC of the scripts that built the reference track.

Also flagged, lower urgency: `k10-colorado/tracks/*/blender/` holds ~3.5 GB of gitignored .blend
workspaces — the only surviving record of the Colorado live-refinement work. Archive to external
storage before that clone is ever deleted.

---

## Phase 1 — Consolidation (one repo, curated, history preserved)

### Principle: merge and delete — never rename in the same pass

The engine runs as `python -m scripts.<pkg>.<mod>` and every skill, wrapper, and doc assumes that
path. The migration **copies trees and deletes dead ones; it does not move/rename anything that
works**. Renames (e.g. `scripts/` → `engine/`) are optional later, one audited pass each.

### Git mechanics

airoso has one trivial commit; k10-track-agents has the real history (which itself contains all
of prodrive-ac-builder's). So airoso adopts that history — the same absorption trick that already
worked once (MIGRATION M0):

```
cd airoso
git add -A && git commit                       # Phase 0 item 1
git remote add engine ../k10-track-agents
git fetch engine --tags
git merge engine/main --allow-unrelated-histories
```

No filename collisions exist between the two docs/ trees (verified). Then curated import commits,
one donor at a time (plain copies, each its own commit):

| From | To (in airoso) | Notes |
|---|---|---|
| k10-sd-v021 `project/` (config, data/, loop.blend) | `tracks/san-diego-lake-murray/` | The memorial track's source of truth |
| k10-sd-v021 `scripts/` (extra_lines, ribbon, build_loop_blend, build_kn5_win.sh …) | `tracks/san-diego-lake-murray/scripts-v021/` | **Quarantined snapshot**, not merged into the engine — it's the build tooling of record for the installed reference, pinned to an old engine era |
| k10-colorado `tracks/*/` (9 configs + source/) | `tracks/<slug>/` | Derived data was already deleted upstream; carry the honesty flags (FABRICATED coords on a few) forward |
| k10-colorado `blender/live_server.py + live_client.py` | `tools/blender-bridge/` | The white-glove enabler; exists nowhere else |
| k10-colorado docs (PRO-KN5-CONSTRUCTION, ROAD-CONSTRUCTION, PIT-LANES, ENGINE-MIGRATION) | `docs/` (+`docs/history/`) | Measured pro standards + the migration playbook's watch-outs |
| k10-colorado-rally `tracks/*/` (restored from HEAD) | `tracks/rally-<stage>/` | Fix the tarmac-config drift during import, don't carry it |
| k10-colorado-rally STAGE-SOURCING.md + CLAUDE.md rally sections | `docs/` + stage dossiers | The annotated-config style (`_doc` keys) becomes the standard |

**prodrive-agents: excluded entirely.** prodrive-ac-builder: nothing extracted (k10-track-agents
supersedes every byte).

### Reduction (staged, honest)

Delete in the first cut — verified dead:
- `scripts/ac/kn5_native.py` (orphan exporter), `capture/synth.py`, `capture/segment_textures.py`,
  `gps/mapmatch.py` (superseded), `fleet` pin/bootstrap/drift machinery + `engine-pin` +
  `fleet-builder` agents, root `.engine-version`, stale `projects/` duplicates (after the M4
  spot-check that live owners carry every input), airoso's `parse_kn5.py`, `map_data*.json`, the
  empty `maps/`, `build_track.py`'s kn5 writer (keep only its `.ai`-format knowledge as docs and
  its ini emitters if the engine lacks equivalents).
- The **two gate-bypass env vars** (`GATE_CONTACT_ADVISORY`, `GATE_EXCURSIONS_ADVISORY`) die on
  the way in, and `build_kn5_win.sh`'s "verify FAIL — reported (not gating)" demotion is
  re-hardened. Gates that can be silenced aren't gates.
- Reconcile the two quality-bar doc lineages: **fleet's DoD/GATES-CHANGELOG win** (older,
  battle-tested); airoso's 2026-08-10 copies fold into them.

Park — plausible but not on the critical path (delete later if the SD campaign proves them dead):
- `build_network.sh` + the network second-implementation (~3k LOC) — Lake Murray *is* a network,
  but the loop+hand-edit path built the drivable reference; decide after the campaign.
- `scripts/scs/` (stubbed), `capture/` + `apps/prodrive-scan`, dashcam path, `gala-seed` +
  `scripts/game/` (**external contract** with the k10-1978 game repo — leave in place, clearly
  marked, don't break it).
- Built kn5s do not live in monorepo git; builds land in gitignored `tracks/<slug>/build/`.
  Exception: preserve the installed San Diego kn5 somewhere durable — it is the standing
  drive-feel reference (ledger 0029).

### The ONE pipeline

Four build pipelines existed. V3 keeps one flow with three verbs, matching REALISM's three jobs:

- **`draft`** — engine regenerates the data underlay (`GEN_*` collections/layers only:
  centerline, terrain, first-pass road ribbon). Never touches `AUTH_*`.
- **`author`** — the hand-edit seam: loop.blend (or track.obj for scripted fixes). Claude's
  hands, Kevin directing. `AUTH_*` collections are never regenerated — the GEN/AUTH contract from
  REALISM.md is what makes "engine drafts, we edit" safe. **The trap it fixes:**
  `build_loop_blend.py` factory-resets the scene today (k10-sd-v021 line 758) — any hand surgery
  is destroyed by a rebuild. Freezing regeneration of authored layers is rule #1 of V3.
- **`ship`** — prep (AC naming, 65k-vert splits) → kn5 export → **all four gates** →
  install into AC → tell Kevin it's ready. One command, exits nonzero on any gate.

### Hazards checklist (from recon, all verified)

- Import path `scripts.*` is load-bearing — copy, don't rename.
- The .sh entrypoints have accreted Windows fixes unevenly (`PYTHONUTF8=1`, MSYS path
  normalization only in build_network.sh) — test `ship` end-to-end on this box early.
- AC `content/tracks` junctions (mklink /J) dangle when source folders move — re-point after
  migration or installed tracks silently stop updating.
- `credits.py`/`track_folder.py` still brand tracks "Built with prodrive-ac-builder" — fix
  branding once, in the monorepo.
- fleet/registry.json's relative repo paths die with the topology; keep only the track-discovery
  + S5–S8 lint (config keys, archetype, unique slugs, gates-wired). S0–S4 existed only because
  there were multiple repos.

---

## Phase 2 — Study: how real authors build multi-street networks

The infrastructure already exists and already produced results — extend it, don't rebuild it:
- `scripts/modkit/` extracts and inspects any installed kn5 (mesh density per surface, materials,
  AI lines, surfaces.ini feel params).
- `fleet/reference/MEASURED.md` already measured 22 installed tracks: good references mesh the
  driven road at **0.3–1.1 m grid** with an invisible physics layer; ours were 2.9–4.7 m
  single-layer — "at 4.7 m spacing every vertex step is a felt event."
- `docs/PRO-KN5-CONSTRUCTION.md` already measured seam welding, physics/visual splits, terrain
  density gradients, chunking.

What's missing is the **junction study** — nobody ever measured how the masters handle the exact
thing that kills us. Kevin's install includes `shuto_revival_project_beta` (the premier
multi-street network mod) plus ~70 other tracks. The work:

1. modkit-extract 5–10 real junctions (SRP interchanges + surface streets, LA Canyons turnouts,
   any Kunos pit entries) into OBJ snippets.
2. Measure: how is the junction pavement built (one welded polygon? overlapping ribbons?), where
   do sidewalks/curbs stop relative to the corner radius, how are crosswalks/markings layered,
   what's collidable vs visual.
3. Write **docs/JUNCTIONS.md** — the junction construction standard, with the extracted snippets
   kept as a pattern library to imitate in Blender (`tracks/_reference/junctions/`).
4. Encode the falsifiable parts as gate checks (see audit K below).

ELI15 for the core concept: today our engine draws each street as an independent paper streamer
and just lays them across each other at intersections — curbs, sidewalks, paint and all. Real
tracks build each intersection as its own patch of pavement, like a puzzle piece cut to fit,
with the streamers welded to its edges and the sidewalks stopping where the corner starts.
That puzzle-piece pattern is what we study, then reproduce by hand.

---

## Phase 3 — The pit-wall loop (the "HMR" workflow)

Goal: Kevin drives → describes what he sees → Claude edits → Kevin reloads. Target cycle
**under 5 minutes**, most of it export time.

**What AC allows (honest constraints):** AC cannot hot-swap a kn5 mid-session — a mesh change
means restarting the session (fast via Content Manager, ~30–60 s on a track this size). Pure
look/config tweaks (CSP `ext_config.ini`) CAN hot-reload in-session via CSP. So: geometry edits =
one session restart; nothing more.

**The loop, concretely:**

1. **Kevin drives.** Reports by voice (Win+H dictation into the session, or type between stints).
   Format doesn't matter — place + symptom is enough ("College at Del Cerro, sidewalk crossing
   the road"). Screenshots/clips welcome, never required.
2. **Claude locates.** A corner-name map per track (dossier: named corners/junctions ↔ stations ↔
   coordinates, built once from the route legs) plus `scripts/diag/` point-probes
   (`what_covers_point`, `deck_float_window`) turn "the turn onto Alvarado" into exact vertices.
3. **Claude edits.** Two modes:
   - **Pit lane** (Kevin stays in the sim): headless edit of loop.blend / track.obj, scripted.
   - **Design bench** (Kevin in Blender, second screen): the live bridge —
     `tools/blender-bridge/` — Claude sends Python into Kevin's running Blender scene
     (localhost:9761) and both look at the same mesh while talking.
4. **`ship` runs.** Gates must pass (drive-test, mesh-audit incl. K, kn5 checks) — Kevin never
   loads a build the machine already knows is broken. Driver's-eye renders
   (`render_drive_views.py`) let Claude *look* at the fix before handoff.
5. **Kevin restarts the session.** CM relaunch; junction-installed folder means the new build is
   just there.
6. Repeat. Every accepted fix appends to the feedback ledger entry it closes; every regression
   gets a check so it stays fixed (the V1 lesson: unlocked bugs come back).

Session rules carried from V2: one defect class per session; two failed attempts at the same
defect → stop and write findings; claims require artifacts.

---

## Phase 4 — San Diego cleanup campaign (the current ledger, in fix order)

The mechanisms are all diagnosed (entries 0032–0036 filed 2026-08-19, on top of 0029's decisions).
Ordered so each fix can't be undone by the next:

**C1 — Delete the split carriageways** (executes 0029's standing decision; closes 0032 + 0035).
`college_avenue_opp` and `navajo_road_opp` are the phantom floating ribbons, and the sawtooth on
College is the narrow-stripe machinery that exists only because of them (35 disjoint width
stripes from a per-vertex clamp with no taper). One regeneration of the GEN_ road layer with
split carriageways off — College becomes one honest two-way ribbon at OSM width. Verify: sawtooth
gone in drive-test edge sweep; no disconnected road components in audit.

**C2 — Junction mouths** (closes 0033, executes 0036's fix). Two parts:
- *Draft rule:* sidewalk/curb sweeps gap at every junction mouth (the engine change 0036
  routes) — the streamer stops short of the intersection instead of running through it.
- *Authored junctions:* Navajo/Jackson and College/Del Cerro get hand-built junction pavement in
  Blender per the Phase-2 pattern library (Del Cerro's connector currently meets College twice,
  12 m apart, each leg dragging raised sidewalks across the road — that's the criss-cross).
- *Gate:* audit check K (kerb/sidewalk inside carriageway) currently **prints but does not
  gate** (`audit_mesh.py:671–675`) — make it gate. This class can never ship green again.

**C3 — The turn onto Alvarado** (0034). Two candidate mechanisms, both measured: the lap-seam
width mismatch (27.5 m vs 17.0 m at the same physical point — a known engine defect class, L13,
fixed at engine HEAD but absent at the old pin) and the inside-corner fold (the ribbon's edge
folds over itself when the corner is tighter than half the road width). Kevin's drive verdict
picks which; likely both get fixed in the same session.

**C4 — Full-loop drive report.** Kevin drives the cleaned loop, files worst-3; the next defect
classes get their own sessions. DoD tier target: T3 (clean laps) for San Diego before polish.

**Then Sand Creek:** the installed v0.26.0 build (137 MB, Jul 26) has never had an in-seat
report. First step is the cheapest possible: Kevin drives it 10 minutes, files worst-3, and the
same loop runs. Its known open item: one soft-top gate failure (un-excavated cut-corridor grass,
ledger 0025).

---

## Decisions Kevin owns

1. **Green-light Phase 0 now** (rescue commits + k10-sd-v021 salvage copy). Everything else waits
   on this.
2. Monorepo identity: airoso adopts k10-track-agents' history via merge (recommended, above) —
   or a fresh curated start with donors archived (loses easy history access).
3. After migration: archive prodrive-ac-builder, k10-colorado, k10-colorado-rally,
   k10-track-agents on GitHub (read-only), matching the never-finished M5.
4. Big binaries in git: loop.blend is 56 MB and is source-of-truth (it gets versioned); plain git
   vs LFS. (Plain git is fine for a private repo; LFS if clone size starts to hurt.)
5. The ~3.5 GB k10-colorado .blend workspaces — archive location (external disk / NAS)?
6. gala-seed / k10-1978 external contract — confirm "park in place, clearly marked" is right.

---

## What V3 explicitly does not do

- No new kn5 writers, no binary reverse-engineering, no GPS-generated AI splines (HANDOFF bans
  stand). AI lines get recorded in-game once a track is drivable.
- No second implementations, ever. Extending or deleting the canonical path are the only moves.
- No "done" without a drive-test report. Gates are pre-checks; the seat is the truth.

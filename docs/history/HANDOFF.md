> **History (moved 2026-10-28).** Superseded by docs/V3-PLAN.md and docs/ONE-CHAIN.md; kept as the record of the 2026-08-19 agent handoff. Nothing here is current.

# Airoso Project Handoff — State of the System

**Written 2026-08-19.** This document is for the next agent session. It covers the full project
state, every recurring failure, the key decision to change approach, and what needs to happen
next to make San Diego driveable in Assetto Corsa.

---

## What this project is

Kevin is building Assetto Corsa tracks of the Lake Murray loop area in San Diego — his childhood
neighborhood. His father died on these streets in 1981. This is a memorial/grieving project.
Kevin is an experienced AC player and sim racer with a full rig (MOZA R9 wheel, Heusinkveld
pedals, DS-8X shifter). He wants driveable tracks, not discussions.

Three routes are confirmed and must not be changed:
- **Full Loop** (~13.5 km): Alvarado, College, Navajo, Jackson, Lake Murray
- **Medium** (~16.3 km): Airoso -> Del Cerro -> College -> Navajo -> Jackson -> Lake Murray -> back
- **Short** (~7.8 km): Airoso -> Del Cerro -> Lake Murray -> Alvarado -> College -> back

## The key decision: stop one-shotting, start guiding

**The automated pipeline approach failed twice.** V1 (prodrive-ac-builder, Jun-Jul 2026) spent
two months and produced three kn5 binaries that were never verified in-game. The car-falls-through
bug was "fixed" six separate times without ever actually testing in AC. V2 (airoso, Aug 2026)
took a lighter approach — a Python script that generates minimal kn5/AI-spline files from OSM
data. It got further: the track loads, the car renders on the road surface, the AI spline is
recognized. But the car is stuck in a respawn loop and can't drive.

**The new approach is white-glove, agent-guided.** Instead of writing code that converts maps to
tracks, the agent guides Kevin through using established AC modding tools step by step — Blender
with the AC Tools addon, 3ds Max, the AC SDK, or whatever combination actually produces a track
that works. The agent operates as a knowledgeable co-pilot, not as a one-shot converter.

---

## Kevin's system

| Component | Detail |
|---|---|
| OS | Windows 11 Home (3440x1440 ultrawide) |
| AC | 1.16.4, installed at `D:\SteamLibrary\steamapps\common\assettocorsa\` |
| CSP | Custom Shaders Patch v0.2.12-preview1 |
| CM | Content Manager (custom launcher), at `D:\Content Manager.exe` |
| Blender | 4.2 and 5.1, with `blender-assetto-corsa-tools` addon installed |
| Sim rig | MOZA R9 Base, Heusinkveld Sim Pedals Ultimate, DS-8X Shifter |
| Other | SimHub (runs elevated, always-on-top — blocks UI clicks) |
| Project repo | `C:\Users\Owner\Documents\GitHub\airoso\` |
| AC tracks dir | `D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\` |

**Important:** Kevin's wheel disables keyboard throttle/brake. To test a track without manual
driving, use Ctrl+C for CSP AI auto-drive (requires working AI spline + functioning physics).

---

## What exists today

### The airoso codebase (`tools/`)

| File | Purpose |
|---|---|
| `build_track.py` | Main script — generates kn5, AI spline, surfaces.ini, models.ini, map.ini, ui_track.json. Builds all three tracks from routes.json. |
| `route_tracks.py` | Defines the three routes as ordered lists of OSM junction nodes, uses Dijkstra routing on the OSM graph |
| `network.py` | OSM road graph with Dijkstra shortest-path routing |
| `fetch_osm.py` | Downloads OSM data for the Lake Murray area |
| `validate_kn5.py` | Dumps kn5 binary structure for debugging |
| `parse_kn5.py` | Minimal kn5 reader |

### Data files (`data/`)

| File | Purpose |
|---|---|
| `osm.json` | OSM extract (~2MB, 2827 ways, 21168 nodes) |
| `routes.json` | Generated route coordinates and distances for all three tracks |
| `routes.geojson` | GeoJSON visualization of routes |

### Installed track files (airoso_full)

```
airoso_full/
  airoso_full.kn5      45 KB    ← the problem: 45 KB vs 66 MB for a working track
  models.ini           65 B
  ai/
    fast_lane.ai       41 KB    ← loads successfully, recognized by AC
    side_l.csv         11 KB
    side_r.csv         11 KB
  data/
    surfaces.ini       661 B
    map.ini            123 B
  ui/
    ui_track.json      467 B
```

### Reference track (san_diego_lake_murray — WORKING)

```
san_diego_lake_murray/
  san_diego_lake_murray.kn5   66 MB   ← 1,500x larger than airoso
  models.ini                  71 B
  ai/
    fast_lane.ai              827 KB   ← 20x more data points than airoso
    pit_lane.ai               827 KB   ← we DON'T have this
    side_l.csv                225 KB
    side_r.csv                225 KB
  data/
    surfaces.ini              1.1 KB   ← more surface definitions
    map.ini                   118 B
  extension/
    ext_config.ini            1.7 KB   ← CSP config, we don't have this
  ui/
    outline.png               46 KB    ← we don't have these
    preview.png               31 KB
    ui_track.json             798 B
```

---

## Every recurring failure, in detail

### 1. Car falls through the road (V1: 6 times. V2: still happening)

**V1 history:** The car-falls-through defect was "fixed" in PR #5 (Jun 10), PR #7 (Jun 20),
commits v0.6.1, v0.8.0, v0.12.1, and k10 v0.8.1 (Jul 3). None of these fixes was ever verified
in-game. Each fix addressed winding order, normals, or mesh connectivity — but the actual cause
was never confirmed because no one ever drove the track.

**V2 state:** The airoso_full track loads and renders. The car is visible sitting on the road. But
the AC log shows a continuous `goToSpawnPosition PIT` loop — the car keeps being teleported back
to the spawn point every frame. The speedometer reads 0 km/h. The car cannot move.

**Root cause analysis (V2):** The road mesh is a flat 12m-wide strip generated from coordinates,
45 KB total. A working AC track mesh is 66 MB. Our mesh likely lacks:
- Sufficient polygon density for AC's physics raycasting
- Proper collision mesh properties
- Correct material-to-surface binding that AC's physics engine expects
- Terrain underneath/around the road for the car to interact with

The `surfaces.ini` defines ROAD (friction 0.98, IS_VALID_TRACK=1) but AC may not be correctly
mapping our kn5 material "ROAD" to this surface definition. The constant PIT respawn suggests
the physics engine can't find valid ground under the car.

### 2. "NO POSITION DATA FOUND" (every session)

AC logs `WARNING: TRACK :: NO POSITION DATA FOUND` every launch. We write AC_START_0, AC_PIT_0,
and AC_HOTLAP_START_0 as transform nodes (class=1) in the kn5 with proper 4x4 matrices. Byte-
level comparison with the working track shows our node format matches. But AC doesn't read them.

**Workaround:** We center all mesh coordinates around the first route point, so the car's default
spawn at origin (0,0,0) lands on the road. This works for rendering but doesn't solve the
respawn loop.

**Possible causes:**
- Our nodes might need to be at a specific depth in the node tree
- AC might require specific parent node naming
- The node might need additional child nodes or properties we haven't reverse-engineered
- There may be a separate position data file we're not generating

### 3. Shadow map rendering crash (fixed, but fragile)

When the road mesh was 2400+ meters from origin and the car spawned at origin, AC crashed in
`CameraShadowMapped::renderPass` — the shadow camera had no geometry in range. Fixed by
centering coordinates, but this fix is load-bearing: if position data ever works and moves the
car away from origin without also moving the mesh, the crash returns.

### 4. AI auto-drive doesn't work (Ctrl+C)

CSP's AI takeover feature (Ctrl+C) doesn't engage. The car sits at 0 km/h. This blocks testing
because Kevin's wheel disables keyboard driving.

**Possible causes:**
- The AI spline might have insufficient data (41 KB vs 827 KB for the reference track)
- No pit_lane.ai file (the reference track has one; AC logs "NO PIT LANE FOUND")
- The constant PIT respawn loop might prevent the AI from taking control
- The spline might have incorrect direction vectors or speed parameters
- CSP AI drive might require additional configuration

### 5. Missing pit_lane.ai

The reference track has a pit_lane.ai file identical in size to fast_lane.ai. Our track doesn't
have one. AC logs "NO PIT LANE FOUND" at startup. The constant `goToSpawnPosition PIT` loop may
be related — the car is told to go to pit but there's no pit lane to follow.

### 6. Content Manager issues

- **Go! button disabled:** CM sometimes disables the Go! button for unclear reasons. Killing and
  relaunching CM fixes it, but CM must be launched through Steam (not directly) or the Steam API
  fails to initialize.
- **SimHub blocks clicks:** SimHub runs elevated and sets its overlay windows as always-on-top.
  Win32 API calls (ShowWindow, SetWindowPos, SetForegroundWindow) all return False because of
  UIPI. PowerShell Stop-Process also fails. The only workarounds are: (a) click in areas not
  covered by SimHub, or (b) have Kevin minimize SimHub manually.
- **Steam API initialization:** Launching acs.exe directly or launching CM directly both fail
  with "Steam API has failed to initialize." Must launch via `steam://rungameid/244210` or
  through Steam's library.

### 7. The 45 KB vs 66 MB gap

Our generated kn5 is 45 KB. The working reference track's kn5 is 66 MB. This 1,500x size
difference is the core problem. A real AC track mesh has:
- Textured terrain (not just a flat gray strip)
- Multiple materials with proper shaders and textures
- Road, sidewalk, grass, barriers, buildings as separate mesh objects
- Proper UV mapping and normal maps
- Collision geometry that AC's physics engine can interact with
- Dozens of nodes in the kn5 tree (not just root + road + 3 position nodes)

Our script generates the absolute minimum viable kn5 binary, and it's not enough for the physics
engine to work with.

---

## What the V1 autopsy already knew

The `docs/history/V1-AUTOPSY.md` (read it in full — it's excellent and honest) identified these lessons
that are still true:

1. **The human drive test is the only ground truth.** Proxies (geometry checks, winding analysis,
   kn5 parsers) are pre-checks, not verification. V1 ran six rounds of fall-through "fixes"
   without ever testing in-game.
2. **One place, finished, beats six places started.** V1 had 10 workstreams. V2 has three tracks
   but zero are driveable.
3. **Generated code cannot self-certify.** The agent that writes the kn5 cannot also declare it
   works. Only Kevin driving closes the loop.
4. **Scope explodes when the core doesn't work.** Both V1 and V2 expanded sideways (new routes,
   new tools, new formats) instead of making one track driveable.

---

## The AC track-building ecosystem (for the next agent)

### Tools that actually produce working AC tracks

1. **3ds Max + AC SDK** — Kunos's official pipeline. Most community tracks use this. The AC SDK
   includes a 3ds Max exporter that produces valid kn5 files. This is the gold standard.
2. **Blender + blender-assetto-corsa-tools** — Community addon (Kevin has it installed in Blender
   4.2). Can export kn5 from Blender scenes. The addon is at
   `C:\Users\Owner\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blender-assetto-corsa-tools\`
3. **ksEditor** — Kunos's kn5 editor. Can open, inspect, and modify kn5 files.
4. **Content Manager** — Can install tracks, configure sessions, launch AC.

### What a working track actually needs (learned from the reference)

- A kn5 with real geometry: terrain, road surface, barriers, scenery
- Multiple materials with textures (the reference has 12 textures, 24 materials)
- A `fast_lane.ai` recorded in-game (not generated from coordinates)
- A `pit_lane.ai` for pit stop functionality
- An `ext_config.ini` for CSP features
- Preview images (outline.png, preview.png) for Content Manager

### The AI spline reality

The correct way to create an AI spline is to **record it in-game**: drive the track with the AI
spline recording tool, and AC generates the fast_lane.ai file. Our approach of generating the
binary from GPS coordinates produces a file that AC loads but the AI can't follow properly.
This is a Phase T4 task (per DEFINITION-OF-DONE.md) — it requires a driveable track first.

---

## What needs to happen next

### The recommended path: Blender-first, agent-guided

1. **Start in Blender.** Kevin has Blender 4.2 with the AC Tools addon. Import the route
   coordinates as a curve. Build a road mesh along the curve. Apply materials. Export as kn5
   using the addon. This produces a kn5 that AC's physics engine can actually work with.

2. **Iterate in small steps.** Don't try to build the full track at once. Start with a 500m
   straight road segment. Export. Test in AC. Confirm the car drives on it. Then extend.

3. **Use the reference track.** The san_diego_lake_murray track is installed and working.
   Examine its kn5 in Blender (import with the AC Tools addon) to understand what a valid
   track mesh looks like. Copy its material setup, node structure, and export settings.

4. **Record the AI spline in-game.** Once the road is driveable, drive it to record
   fast_lane.ai. Don't generate it from coordinates.

5. **Let Kevin drive at every step.** The drive test is the only ground truth. Don't proceed
   to the next segment until the current one is confirmed driveable.

### What the agent should NOT do

- Don't write Python scripts to generate kn5 binaries. That approach has failed twice.
- Don't reverse-engineer binary formats. Use existing exporters (Blender addon, 3ds Max SDK).
- Don't generate AI splines from GPS data. Record them in-game.
- Don't build all three tracks at once. Get one segment working first.
- Don't explain the plan at length. Kevin wants progress, not discussion.

---

## File locations quick reference

| What | Where |
|---|---|
| Project repo | `C:\Users\Owner\Documents\GitHub\airoso\` |
| AC install | `D:\SteamLibrary\steamapps\common\assettocorsa\` |
| AC tracks | `D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\` |
| AC logs | `C:\Users\Owner\Documents\Assetto Corsa\logs\log.txt` |
| CSP logs | `C:\Users\Owner\Documents\Assetto Corsa\logs\custom_shaders_patch.log` |
| AC config | `C:\Users\Owner\Documents\Assetto Corsa\cfg\` |
| Blender AC addon | `C:\Users\Owner\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blender-assetto-corsa-tools\` |
| Content Manager | `D:\Content Manager.exe` (must launch via Steam) |
| Reference track | `D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\san_diego_lake_murray\` |
| Memory files | `C:\Users\Owner\.claude\projects\C--Users-Owner-Documents-GitHub-airoso\memory\` |
| Route data | `C:\Users\Owner\Documents\GitHub\airoso\data\routes.json` |
| SimHub | `C:\Program Files (x86)\SimHub\SimHubWPF.exe` (runs elevated) |

---

## The V1/V2 documentation (read these)

- `docs/history/V1-AUTOPSY.md` — brutally honest post-mortem of the first two months. Every lesson
  applies to the next attempt.
- `docs/history/V2-OPERATING-MODEL.md` — the process framework. Phase R/P/B/H/D/I cycle.
- `docs/DEFINITION-OF-DONE.md` — tier ladder T0-T5. No track has reached T2.
- `docs/ASSET-LIBRARY.md` — Kevin's owned 3D assets in Dropbox.

## Kevin's working style

- Wants results, not discussion. Build and test, don't plan at length.
- Gets frustrated when progress stalls or work is repeated across sessions.
- Has confirmed the three routes — never change them without explicit approval.
- Drives a full sim rig — keyboard input won't work for testing.
- Save progress to memory immediately. Don't let context loss erase findings.

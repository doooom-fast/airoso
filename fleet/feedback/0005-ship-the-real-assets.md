---
id: 0005
title: Ship the real Dropbox assets, not small derived stand-ins
status: open
scope: all kinds
layer: engine
train: 02
---

## Symptom

> "We don't want the small derived versions"

The props and textures the tracks ship are minimal stand-in geometry, while a real asset library
already exists.

## Evidence

`assets/models/` holds 10 models totalling **1.1 MB** — placeholder-scale geometry for a concrete
barrier, lamp post/lens, pine, poplar trunk/leaves, pylon, and two fence panels.

Dropbox `/Blender/` holds the real library:

| Path | Contents |
|---|---|
| `/Blender/obj/` | `traffic signs-01.obj` (4.1 MB) + `.mtl` + ~57 texture maps (`001.jpg`–`057.jpg`, ~150 KB each) |
| `/Blender/Textures/`, `/Blender/textures-2/` | full-res textures, e.g. `concrete_wall/concrete_wall_008_diff_4k.jpg` (11 MB) |
| `/Blender/Concrete Barrier and Transition Barrier OBJ/` | the real barrier set, with a 10 MB base-colour map |

So the barrier the tracks place today is a stand-in for a real modelled barrier that already exists,
and a whole traffic-sign library has never been wired in at all.

No local Dropbox folder exists on the Mac — access is via the Dropbox MCP connector.

## Constraints this has to respect

Not "use the originals as-is" — three real limits decide how much resolution survives:

1. **Power-of-two textures or AC hard-crashes the GPU** on load (L7). 4k source maps are already
   PoT; the sign pack's JPEGs are almost certainly not, and must be resized before they ship.
   `scripts/build.sh` pre-flights this and refuses to build — keep that.
2. **65,535 verts per mesh, hard** (L7). Props are instanced hundreds of times: `POPLARBARK`
   already reaches 671,876 verts and splits into 11 meshes at the current placeholder complexity.
   A high-poly source model multiplied by the same instance count will not fit — props need a
   decimated LOD for placement even when the source is detailed.
3. **kn5 size and load time.** A 10 MB texture per prop class is fine; per prop instance is not.

The honest framing: **textures can go to full resolution almost for free; prop geometry cannot.**
Those are separate decisions and should land as separate changes.

## Fix

1. Pull `/Blender/obj/traffic signs-01.obj` + maps, resize maps to PoT, and wire signs into
   `scripts/environment/props.py` — the biggest visible gain, since street furniture is currently
   absent rather than crude.
2. Replace `concrete_barrier_4m.obj` with the real barrier set, decimated to an instance-safe vert
   count, with its real base-colour map at PoT.
3. Raise the shared texture set to full resolution where each is already PoT.
4. Record provenance per asset (which Dropbox path, what was done to it) so a re-export is
   repeatable — `assets/README.md`.

## Scope

All tracks — props and textures are engine-shared. Sand Creek is the proof case (it already places
barriers, lamps and poplars, so the change is immediately visible); the rally stages are the
regression case, since Rangely is sparse high desert and must NOT gain street furniture.

## Verification

- `scripts/build.sh`'s PoT pre-flight passes with every new texture in place.
- No mesh exceeds 65 k verts after instancing (the build's own over-cap guard is fatal, so this
  gates itself).
- kn5 size and AC load time stay within reach of the current build.
- Kevin looks at Sand Creek and the furniture reads as real.

## 2026-10-31: the first self-made batch (Nevada Nights 0.3.0)

Kevin: "There should be instructions in here for Astra on how to create some assets for our tracks. Let's do it here." The
instructions were `.claude/skills/bespoke-assets` on the unmerged branch `claude/skill-bespoke-assets`; they now live on this
branch and were run on the Windows box.

Built, all CC0, each with its source: two 2013 buildings from NAIP footprints (29.3 x 26.0 m flat, 54.1 x 20.4 m gabled),
20 corner cones, 36 creosote / bursage clumps at the count measured on NAIP, and the caliche ground in its measured colour.
`tools/make_bespoke_assets.py`, `tracks/exotics-racing-lv/textures/make_caliche_ground.py`, `tools/plan_cones.py`,
`tools/author_bespoke_blend.py`, `tests/tools/test_bespoke_assets.py`. `fleet/DEFINITION-OF-DONE.md` has the gate numbers.

Still borrowed in this kn5: `asphalt_cracked_*` (LA Canyons) and `building_*` (Hamburg, on `BARRIER_warning` only).
Not built from DOSSIER section 8: the Tec-Pro line, the gravel trap, the LVMS grandstands, the fence. Not yet
driven.

## 2026-10-31 (later): the second batch, every chain track

Kevin: "Keep going until you're done for all tracks", then "Add lariat to the list", "Are you also setting grassfx based on the
aerials", "Work as long as you need, we want quality work over speed". Built and installed the same day, all CC0, each number with
its source in the config or the planner's file: Milford 0.3.0, High Plains 0.69.0, Sand Creek 0.29.0, Nevada Nights 0.5.0
(`fleet/DEFINITION-OF-DONE.md` has the gate numbers and md5s). New in `assets/textures/` (`tools/make_bespoke_assets.py`): tilt-up
and ribbed-metal walls, stucco and lap-siding house bays with a window, three flat roofs and a shingle roof, a paddock pad, W-beam,
Tec-Pro and K-rail skins, laid dry stone, and three card atlases (hardwoods, prairie, foothill conifers). Per track: a ground tile
in the NAIP's measured colour (`tools/make_ground_tile.py`), GrassFX zones read off the aerial (`tools/plan_grassfx_aerial.py`),
vegetation positions by a colour rule on the aerial (`tools/plan_bespoke_vegetation.py`), buildings by the pipeline below.

Lookout Lariat has its ground tile and a wiring note (`tracks/lookout-lariat/textures/README.md`) and no build: its P2 road
work is on the branches `worktree-wf_0b6149fb-898-1..4`, pushed 2026-10-31 for the cloud session. Lake Murray: the six Mission
Gorge apartment blocks OSM lacks are traced in `data/buildings.traced.json` and carried into the assembler's cache by
`tools/merge_traced_buildings.py` (0.19.2).

Still borrowed on every chain track: `asphalt_cracked_*` (LA Canyons) on the road; the Hamburg concrete is off Milford and High
Plains (`BARRIER` overridden to our tilt-up) and stays on Sand Creek's `1WALL_barrier` and Nevada's `BARRIER_warning`. The fleet-wide
swap remains Kevin's call.

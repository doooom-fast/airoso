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

# Assets

> **Policy: ship the real assets, not small derived stand-ins.** The 10 models currently in
> `models/` are minimal placeholder geometry — that is a stopgap, not the target. The full-resolution
> library in Dropbox `/Blender/` is what should reach the tracks, resized only where AC's own limits
> force it (power-of-two textures; the 65 k vert per-mesh cap on props instanced hundreds of times).
> Tracked in `fleet/feedback/0005-ship-the-real-assets.md`.

## Source of truth: Dropbox `/Blender/`

| Dropbox path | What |
|---|---|
| `/Blender/obj/` | source models |
| `/Blender/Textures/`, `/Blender/textures-2/` | source textures, 4k+ |
| `/Blender/Concrete Barrier and Transition Barrier OBJ/` | the concrete barrier set |
| `/Blender/Concrete Barrier and Transition Barrier - Models and Textures/` | the same, with textures |

These are full-resolution originals — single textures run over 10 MB. Reach for them when an asset
is missing, needs re-exporting at a different resolution, or a new prop is wanted. **A build never
consumes them directly**; it consumes the derived copies here.

There is no local Dropbox folder on the Mac — access is through the Dropbox MCP connector.

## Two rules when bringing something across

1. **Resize to a power of two.** A non-power-of-two texture can hard-crash the GPU on AC load —
   the mipmap/DXT upload hangs the driver. `scripts/build.sh` pre-flights this and refuses to build;
   keep it that way (LAWS L7).
2. **Force-add models to git.** `*.obj` is gitignored in every repo, so the 10 models in
   `models/` are tracked only because they were added with `git add -f`. A new model that is merely
   copied in will be invisible to every consumer:
   ```bash
   git add -f assets/models/<new>.obj
   ```

That second rule is not theoretical: `k10-colorado` builds failed with
`FileNotFoundError: assets/models/concrete_barrier_4m.obj` because it runs its own shadow copy of
the pipeline (MIGRATION M3) and never received the tracked models the engine carries. A repo
consuming `.engine/` gets them automatically.

## What's here

- `models/` — 10 props: concrete barrier, lamp post/lens/head, pine, poplar trunk/leaves, pylon,
  ranch and wood fence panels.
- `textures/` — the shared texture set, power-of-two.

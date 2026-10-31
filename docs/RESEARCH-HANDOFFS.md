# Research handoffs — and the chain they build through

*Written 2026-10-28; rewritten the same day after Kevin's correction.*

The three research documents below were handed to build sessions on 2026-10-28. **Their first build
plans were wrong**: they prescribed the engine-era pipeline (trace → elevation → mesh → gates → kn5,
`scripts/build.sh`), and the four tracks built that day came out that way. Kevin, the same evening:
*"what I wanted and what I told you to do was build these the same way that we build Lake Murray
0.19.1"*, then *"rebuild all four with the Lake Murray chain"*.

**The chain** is `tools/ship_track.sh <track>`, driven by `tracks/<track>/ship.json` (V3-PLAN P1):

| Phase | What runs | Where |
|---|---|---|
| draft | the engine, as a DRAFT only: `gps` / `aerial` → `elev` → `project` → `mesh` → **`underlay`** (`scripts/blender/underlay.py`: `data/track.obj` into `loop.blend` as `GEN_*` collections) | Windows box, Blender 4.2 |
| author | hand and scripted authoring in `loop.blend`, in `AUTH_*` collections the engine never touches (REALISM §4) | Blender |
| prep · split | `scripts/ac/build_kn5_loop.py` (AC naming, terrain conform, 50k tiles, materials), `tools/split_exports_blend.py` | Blender |
| ship | `export_kn5_addon` → AI line → `verify_kn5` → gate OBJ → track folder → `make_map` | Blender + Python |
| gate | `drive_test` → `audit_mesh` → `kn5_ground_check` on the **built** kn5 (L5) | Python |
| install | into `content/tracks/<install_folder>`, the previous build parked in the archive | Windows |

Until 2026-10-28 the chain stopped at "no blend yet" for every track but San Diego, because the
underlay was never written. It is written now; this is its first use on anything but a test fixture.

| Track | Research | Where it stands |
|---|---|---|
| [`tracks/milford-road-course/`](../tracks/milford-road-course/DOSSIER.md) | GM proving grounds (deep on Milford) + every Michigan road course; Part D is the Milford dossier, approved ("Build Milford first") | engine-era v0.1.0 at T1 retired; `ship.json` written, chain run owed |
| [`tracks/exotics-racing-lv/`](../tracks/exotics-racing-lv/DOSSIER.md) | Exotics Racing LVMS 2015–2021 (target A; Kevin: dress it as in 2013) | engine-era v0.1.0 at T1 retired; `ship.json` written, chain run owed |
| [`tracks/sand-creek/`](../tracks/sand-creek/ship.json), [`tracks/high-plains/`](../tracks/high-plains/ship.json) | the Colorado tracks Kevin named with the other two | engine-era builds (v0.27.0 / v0.67.0, draft release) retired; `ship.json` written, chain run owed |
| [`fleet/reference/SATELLITE-ROAD-TEXTURES.md`](../fleet/reference/SATELLITE-ROAD-TEXTURES.md) | orthoimagery as the road's macro colour layer | the proposed modules land in the **authoring** stage (a texture on `GEN_road` / `AUTH_road`), not in the engine's mesh step |

Ledger: [0060](../fleet/feedback/0060-engine-era-tracks-look-terrible-rebuild-through-the-ship-chain.md).

## Caveats shared by the research (2026-10-28)

The research session's network policy denied every direct page fetch and returned 403 for Overpass,
Nominatim, the USGS National Map, Clark County GIS and Michigan open data. Every row is sourced from
web-search results and tagged (`·snip`, `[unverified]`, `[derived]`) accordingly. The build sessions
since filled in what they measured (both dossiers carry "Answered 2026-10-28" blocks).

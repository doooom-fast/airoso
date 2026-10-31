# San Diego freeway network — through the chain

The I-5 / SR-52 / SR-163 / I-8 box of central San Diego, both carriageways and every ramp and interchange
connector, as one Free Roam network. Shipped once, engine-era, as `san_diego_freeway_v0.5.0.zip` (unchanged since
v0.21.0, re-zipped by `tools/pack_release.py` from the installed `content/tracks/san_diego_freeway`). Kevin,
2026-10-28: rebuild it through the chain, by an agent (`docs/ONE-CHAIN.md` §2 row 5, §4 row 8).

**Tier: none claimed.** Nothing has been built through the chain yet (`fleet/DEFINITION-OF-DONE.md`: a tier is
claimed through the chain, with its artifact, or not at all).

| File | What |
|---|---|
| `track.config.json` | the network's config. Its `_doc` and `*_doc` keys say where every value came from |
| `ship.json` | the chain spec: draft `net → classify → network_elev → network_mesh → underlay`, no authoring yet, prep/split, ship/gate as the four chain tracks |
| `source/` | `realworld_capture.json` (the concrete deck / wall / line texture overrides) and its four CC0 procedural textures, as shipped |

`fleet/registry.json`: airoso's `tracks_glob` lists this config, `k10-san-diego` lists `project_freeway_net` under
`moved_out`, and `track_annotations` `airoso/san-diego-freeway` carries the kind (`street_port`, `network: true`),
so `python3 -m fleet.cli tracks` discovers it once, here.

```bash
bash tools/ship_track.sh san-diego-freeway --draft-only     # the four data steps (Overpass + 3DEP), stops at the underlay
bash tools/ship_track.sh san-diego-freeway --dry-run        # + underlay, prep, split; nothing exported or installed
```

## The source of truth, and how sure that is

The network's config of record lived in the retired `k10-san-diego` repo (archived under doooom-fast since the org move), not in airoso:
`project_freeway_net/track.config.json` at that repo's HEAD `64161fc` (2026-07-28; engine pin `.engine-version`
v0.66.3), built by its `scripts/build_network.sh project_freeway_net`. It was read for this change through a
read-only shallow clone (public repo); nothing there was changed. What ties it to the shipped zip:

- its `slug` is `san_diego_freeway` and its `version` `0.5.0` — the zip's name, and the kn5 `tools/pack_release.py`
  copies (`FREEWAY_FILES`: `san_diego_freeway.kn5`, a single-layout folder);
- `fleet/registry.json` `track_annotations` names `k10-san-diego/project_freeway_net` as the freeway network
  (`network: true`), and `project_freeway` as RETIRED, superseded by it;
- k10-san-diego's `CLAUDE.md`: "the shipped track uses the network freeway"; "The freeway network MUST be built
  `mirror_x=false`".

`projects/san-diego-freeway-loop/track.config.json` (airoso's engine copy, `fleet/registry.json` `engine_projects`
"stale duplicate") has the same `source`, `network`, `scenery`, `location` and `layouts` values and an identical
`source/`, but `slug san_diego_freeway_loop`, `mirror_x true` and `true_north_rotation_deg 180` — the frame the
shipped network was not built in. It is the stale copy; this config does not follow it.

**What is NOT established from anything in reach:**

1. **The OSM snapshot the 0.5.0 kn5 was built from.** `scripts.gps.network`'s `osm-network` source fetches
   Overpass live with no snapshot (`scripts/gps/overpass.py` `fetch_highways_by_class` takes no `cache`), and
   `project_freeway_net/` in k10-san-diego commits no `data/`. The chain's first `net` step will build from
   today's OSM, which is not the July 2026 OSM. The same holds for 3DEP (sampled live, never cached for this box).
   No freeway-box cache exists in airoso either (`tracks/san-diego-lake-murray/data/network.cache.json` and
   `freeway_i8.samples.json.gz` are Lake Murray's, ~10 km east, outside `source.bbox`).
2. **Whether the installed `san_diego_freeway` folder was a plain `build_network.sh` output.** k10-san-diego
   also built a combined loop + freeway kn5 (`scripts/build_combined.sh`, `merge_freeway.py`); the zip's file list
   says single track, single layout, and its kn5 is named for this slug, so the standalone build is the likely
   one, but the folder itself is on the Windows box (`D:/SteamLibrary/.../content/tracks/san_diego_freeway`) and
   was not read.
3. **Two k10-san-diego-only pieces of that build are not in airoso:** its local audit's `H_grade_launch` check
   (sustained deck grade = launch ramp; `build_network.sh`'s audit gate required `H == 0`) and its Blender program
   `scripts/ac/build_network_kn5.py`. The chain replaces the second with the underlay + `build_kn5_loop.py` prep;
   the first has no counterpart in airoso's `audit_mesh` today.

Changed from `project_freeway_net`, each by a named rule (the `*_doc` keys): `name` "San Diego Freeway Free
Roam" and `layouts[0].name` "Freeway Free Roam" (Kevin's `<Area> Free Roam`; installed as "doooom San Diego —
Freeway Free Roam" — the exact words are Kevin's call), `ui_series` "doooom San Diego", `install_folder` =
the slug, `author` airoso. The layout id stays `freeroam` (ids stay stable). `version` stays 0.5.0 until the
chain ships (then 0.6.0). The `scenery` keys only the retired `build_network_env` read (gantries, bushes, trees,
Mission Bay's water) are kept as the record and are inert: the chain never runs `build_network_env`.

## What ran offline (2026-10-29, container without Overpass / USGS: both refuse the connection, 403)

1. **The chain on the real spec**, `SHIP_PROJ=<scratch> bash tools/ship_track.sh san-diego-freeway --draft-only`:
   the spec validates, the rails pass (scratch project, no sync-back, no install), inputs sync, the layouts read
   (`freeroam`, no race), and `draft: road network graph (scripts.gps.network ...)` runs — and stops on
   `urlopen error Tunnel connection failed: 403 Forbidden` (exit 1). Nothing past it can run on this box without
   the freeway's own OSM.
2. **A stand-in rehearsal of the same four modules + the underlay**, on real data of another stretch of San
   Diego freeway that airoso does carry (outside the repo, never committed; not this track): Lake Murray's cached
   OSM motorway + motorway_link ways (I-8 / SR-125, La Mesa; no `ref` tags, so `source.refs` was null) clipped to
   its 3DEP 40 m grid's box, with only the two fetches replaced (Overpass → that cache, 3DEP `getSamples` → a
   bilinear read of `tracks/san-diego-lake-murray/data/heightfield.npy`). Everything else is the freeway config
   (snap 7 m, resample 5 m, walls 1.1 m, viaduct layer 5.5 m, `mirror_x` false):
   - `net`: 30 edges, 7.3 km; `classify`: 25 ramp + 5 motorway edges (74 OSM ways indexed);
   - `network_elev`: 1,494 edge vertices, terrain grid 79×23 @ 55 m, z 95.8–143.9 m;
   - `network_mesh`: `data/track.obj` 28,917 verts / 38,315 tris, groups `1GRASS_0_0`, `1GRASS_0_95`,
     `1GRASS_skirt`, `1ROAD_part_0`, `1GRASS_verge_0`, `1WALL_part_0`, `1RUNOFF_median_0`, `MARKINGS_part_0`,
     `HWYSTRUCT_via_0`; its own audit A 0, B 0, C 0, D 12 (walls on a road), E 0; one swallowed warning
     ("track grass clear skipped: string indices must be integers, not 'str'", `build_network_mesh.py` ~1210);
   - `underlay` (`python -m scripts.blender.underlay`, the `bpy` 4.2 module): 9 GEN objects (GEN_road 2,
     GEN_terrain 4, GEN_wall 1, GEN_misc 2: markings + viaduct structure), 0 refs (a network has no single
     centreline), a 3.0 MB `loop.blend`, under 1 s; re-run: "9 old GEN objects replaced". The underlay needed no
     change: the network mesh writes `data/track.obj`, the file it reads.
   - **the prep then fails** — `scripts/ac/build_kn5_loop.py` `declare_bridge_spans` (line 146, from `main` line
     866) reads `data/centerline.local.json`, which no network draft writes (`FileNotFoundError`). See below.

## What the Windows run owes

- **Overpass and USGS.** `net`, `classify` and `network_elev` fetch live. Run `--draft-only` first. `data/network.geojson` and `data/network.elevation.json` sync back through
  `ship.json` `sync_out` on the first real ship, so the route of record lands in `tracks/san-diego-freeway/data/`
  (the heightfield `.npy` is gitignored and stays in the workshop). A snapshot cache in `scripts.gps.network` (as `overpass.fetch_ways` has) would make the route
  reproducible; it is not written.
- **The ship phase for a network** (found by the stand-in, not fixed here): the prep (`build_kn5_loop.py`: lines
  146, 228, 607, 1016), `scripts.ac.write_ai_line`, `tools/make_map.py` and `scripts.geometry.drive_test` all read
  `data/centerline.local.json` or the prep's `data/finished_centerline.json`; a network draft writes
  `network.geojson` + `network.local.json` instead. Until the prep and those steps learn a network (or the config
  declares a reference line on the real road — never an invented one), `--dry-run` stops at `prep`. This is the
  next engine change for this track.
- **Blender 4.2 with the AC add-on** for the export, then the gates on the built kn5 and Kevin's seat. The
  launch-grade check k10-san-diego's audit carried (`H_grade_launch`) is not in airoso's gates.
- **Authoring** (none yet): gantries, Mission Bay and the Pacific, lane-level detail — in `loop.blend` `AUTH_*`,
  never `build_network_env`.

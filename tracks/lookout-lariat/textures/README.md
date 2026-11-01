# The Lariat's own textures, and what is waiting for its road

`foothill_diffuse.jpg` + `foothill_normal.jpg`: tawny foothill grass and decomposed granite (DOSSIER section 8, the CC0 ground D7 asks
for). Drawn by `tools/make_ground_tile.py` (seeded, Pillow only, CC0). The one measured number is the colour, mean RGB (145, 135, 92): the open
south-facing slope below the Lariat, box lon -105.2359..-105.2343, lat 39.7362..39.7369, on USDA NAIP 2023-09-25
(`co_m_3910523_nw_13_030_20230925_20240104`).

**Not yet on a track.** The Lariat has no draft (`loop.blend`); its P2 road work is on the pushed branches `worktree-wf_0b6149fb-898-*`
(`-4` holds the other three; ledger 0048). When a draft exists, wire the dressing the way Milford does:

- `ship.json`: `steps.author` gains `bespoke`, `steps.gate` gains `house_seat`, `steps.ship` gains `grassfx_aerial` before `track_folder`,
  `sync_in.optional` the two ground files, `sync_out.files` `data/bespoke.report.json`, `data/house_seat_check.json`, `data/grassfx.aerial.json`.
- `track.config.json`: `texture_overrides` for `1GRASS`, `GRASS_FAR`, `SHOULDERUND`, and `scenery.bespoke` (tools/author_bespoke_blend.py's
  header has the grammar).

What exists for it, all in `assets/textures/` (`tools/make_bespoke_assets.py`, CC0):

| DOSSIER section 8 row | Asset | How it is placed |
|---|---|---|
| W-beam guardrail | `wbeam_rail_diffuse.png`, swept by the author tool | `guardrail` along guard lips; a rail where the draft has none still needs a rule (DOSSIER 5a) |
| 1917 stone pylons, dry-stone walls | `drystone_diffuse.jpg` + `_normal` | a `blocks` entry with `"skin": "drystone"`; the pylons stand at 39.7424, -105.2285 (DOSSIER 3), size not measured yet, no arch modelled |
| Ponderosa, Douglas-fir, juniper, mahogany | `conifer_foothill_atlas.png` | `cards` with `"prefix": "TREECARD_CONIFER"`, planned by `tools/plan_bespoke_vegetation.py` off NAIP, cells 0-3 |
| Buildings on the town stretches | `tiltup_*`, `metal_*`, `roof_*` | `tools/plan_bespoke_buildings.py` from OSM footprints, then `blocks` |

Not made: the Sensation Point wall, the C-470 decks, the skyline and the race closures, which are road or layout authoring rather than textures.

# Lake Murray's own textures

`chaparral_far_diffuse.jpg` — the far ring's ground (`GRASS_FAR*`, the visual-only terrain past 250 m: Cowles, Del
Cerro's far side, the valley walls). Ledger 0046 fix round, 2026-10-12: the visual verify found the far ring wearing
pbr's stock `ground_dry_diffuse.jpg`, a neutral grey gravel (mean RGB 139/132/122) — Cowles read as bare grey rock
beside the green turf. This tile is grey-olive coastal sage scrub / chamise over tan decomposed-granite soil (mean
93/93/66, ~21 % bare), 1024², tileable.

Derived, not captured: `make_chaparral_far.py` builds it deterministically from two owned stock tiles —
`assets/textures/grass_diffuse.jpg` (ambientCG Grass001, CC0: the fine vegetation detail) and
`assets/textures/ground_dry_diffuse.jpg` (LA Canyons dirt: the soil detail) — with a wrapped low-frequency clump
field for the bare patches. Rerunning it reproduces the file byte for byte.

Bound by `track.config.json` `texture_overrides.GRASS_FAR` (a project-relative path: pbr.load_overrides resolves it
against the workshop project) and carried into the workshop by `tools/ship_sd.sh` (`TRACK_TEXTURES`) and
`ship.json` `sync_in.optional`. `1GRASS` keeps its own green turf override; the two keys never cross.

`sandstone_cut_diffuse.jpg` + `sandstone_cut_normal.jpg` — the road cuts' rock faces (`1GRASS_ROCK_*`, ledger 0054 P4
buildings + rock, 2026-10-26): the steep faces of the north network's cut walls, split out of the ground tiles by
`tools/rock_faces_blend.py` and bound by `track.config.json texture_overrides["1GRASS_ROCK"]` (pbr row `1GRASS_ROCK`, stock
skin `stone_tan.png`). The real walls stand in the Stadium Conglomerate and the Friars / Mission Valley sandstones of the
Mission Gorge: tan bedded sandstone with rounded cobbles, dark weathering streaks under the rim. Drawn, not captured, by
`make_sandstone_cut.py` (seeded, PIL only; re-running reproduces both files byte for byte): 1024², one tile = 4 m on the
face (u along the wall, v up it), mean RGB 161/138/105, ~20 % cobbles; the normal map is OpenGL (green up) from the same
bedding + cobble height field. Ours outright, CC0 (`assets/licenses.json`). Synced in by `tools/ship_sd.sh`
(`TRACK_TEXTURES`) and `ship.json` `sync_in.optional`.

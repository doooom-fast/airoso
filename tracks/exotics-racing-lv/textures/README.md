# Nevada Nights' own textures

`caliche_diffuse.jpg` + `caliche_normal.jpg`: the Mojave ground (`1GRASS*`, `GRASS_FAR*`, `SHOULDERUND`) in place of the
stock dry dirt, Kevin's dressing call in `DOSSIER.md` section 11. Pale caliche with a gravel lag, no green (section 6).

Drawn, not captured, by `make_caliche_ground.py` (seeded, Pillow only; re-running reproduces both files byte for byte):
1024 x 1024, one tile = 4 m, the prep's `UV_TILE`. CC0. The one measured number is the colour: mean RGB (172, 163, 149),
the pale soil pixels of the undisturbed strip north of the lap on USDA NAIP 2019-07-06 (`source/naip_2019_exr.png`, the scrub
polygon in `track.config.json` `scenery.bespoke.scrub`). The lag's stone colours are `[invented]`.

Bound by `track.config.json` `texture_overrides` (project-relative paths: `pbr.load_overrides` resolves them against the
workshop project), carried into the workshop by `ship.json` `sync_in.optional`. `1GRASS` keeps its GRASS physics.

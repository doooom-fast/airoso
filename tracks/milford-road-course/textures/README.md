# Milford's own textures

`turf_diffuse.jpg` + `turf_normal.jpg`: the mown verges and infield (`1GRASS*`, `GRASS_FAR*`, `SHOULDERUND`) in place of the stock
dry dirt. Drawn by `tools/make_ground_tile.py` (seeded, Pillow only, CC0). The one measured number is the colour, mean RGB
(169, 168, 131): the mown grass east of the pad, box lon -83.6620..-83.6614, lat 42.5660..42.5668, on USDA NAIP 2022-08-16
(`source/naip_2022_mrc.jpg` on its true extent, `source/trace/unsquash_frame.py`). `1GRASS` keeps its GRASS physics.

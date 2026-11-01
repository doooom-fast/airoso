# How the Exotics Racing LVMS lap was traced (2026-10-28)

The photo is USDA NAIP 2019-07-06 (public domain, 0.6 m native), scene
`nv_m_3611548_se_11_060_20190706_20191118`. It is the only sub-metre vintage inside the track's
2015–2021 life: 2015 and 2017 are 1 m, and 2022 shows the ground after Nuro took it over.

1. `pc_tiles.py` stitches the scene's Microsoft Planetary Computer tiles at Web Mercator z18
   (0.481 m/px here) over `-115.0235,36.2785,-115.0135,36.2865` into a 2048×2304 PNG. The tile
   origin is in `naip_2019_z18.georef.json` (`x0`/`y0`), and `geo.py` converts pixels to lon/lat
   from it.
2. `seeds.json` holds 68 hand-placed points along the rubbered lap, clockwise from the NW end of
   the straight. Where the edge lines were ambiguous, the points were measured from brightness
   scans across the painted lines: the straight, the NW corner exit, and the pit-lane merge.
   `zones` narrow the snap there, as does the outer side of T2, where a small building sits
   beside the edge line.
3. `refine_trace.py` snaps the seeded spline to the two painted edge lines every ~1 m. It takes
   the best pair of bright ridges 8–22 m apart with darker asphalt between them, re-centres on
   the pair, and repeats. Widths are measured line to line.
4. The config takes every second station, cropped to `../naip_2019_exr.png` (orig px
   x 440–1720, y 530–1850). The two control points are that crop's corners, read from the tile
   georeference. Widths are floored at 11.5 m, because three spots picked an internal line
   where a connector or the pit lane joins, and capped at 20 m. They are then smoothed over
   11 stations.

Re-run, from this folder (`python -I`, Pillow only):

```bash
python -I pc_tiles.py nv_m_3611548_se_11_060_20190706_20191118 18 -115.0235 36.2785 -115.0135 36.2865 naip_2019_z18.png
python -I refine_trace.py naip_2019_z18.png seeds.json trace
```

`trace_preview.jpg` is the result drawn back onto the photo.

**What the photo settles and what it doesn't:**
- **Settled:** the lap is 1,825 m against the published "1.2 mi" (1,931 m), and the straight is
  about 470 m against "1,800 ft" (549 m). The georeference comes from the photo itself, so those
  gaps are the published figures, not the trace.
- **Inferred:** the direction is clockwise (see `route._orientation_doc` in the config).
- **Confirmed by lidar:** T2's bank. USGS 3DEP corridor samples (`data/corridor.elev.json`,
  ±5 m across the centreline) read +10.0 to +10.9 % across the whole NE corner, against about
  +2 % on the rest of the lap. That matches the published 11 %. The bank builds over about 80 m
  each side, so `road_profile` uses 6.0° (10.5 %) over s 215–525 with 85 m ramps. It is negative
  in the config because the build frame is mirrored (`scripts/geometry/profile.py`).

**The two 2013 buildings (`buildings_2013_measured.png`, 2026-10-31):** NAIP 2013-09-28 (1 m native), scene
`nv_m_3611548_se_11_1_20130928_20131122`, fetched with `pc_tiles.py` over z18 tile origin x0 47314, y0 102685, read at 0.481
m/px; the corners are in `track.config.json` `scenery.bespoke.buildings`, in lon/lat. A (red) is 29.3 x 26.0 m with a flat
white roof; B (blue) is 54.1 x 20.4 m, gabled along its length. Heights come from the shadows: the poles' shadows run to azimuth about 302 deg,
which `scripts/lighting/solar.py` puts at about 09:30 PDT, sun elevation 33 deg. The photo's 1 m pixel leaves about +-0.6 m
on any height read this way, and each building's `_source` line says what was taken and why.

**2013 cross-check (Kevin drove it in 2013):** `trace_on_2013.jpg` draws this trace onto USDA NAIP
2013-09-28 (1 m), fetched over the same z18 tile grid. The circuit was already paved, edge-lined
and kerbed, and the lap is unchanged. Only the buildings on the south-west corner differ: in 2013,
two smaller buildings stood where the 2015 Welcome Center and covered pit went.

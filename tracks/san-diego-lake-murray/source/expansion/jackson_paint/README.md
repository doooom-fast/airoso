# Jackson Dr north (piece D): the painted lines, read off the 2024 lidar's intensity

Ledger 0099, round 3, item 4. Lane wear found that the northbound side of piece D (connector
`north_J5_jackson_north#0`, reversed) has no room for a lane over connector rows 496-579 and 234-239.
The cause is the piece's median columns: an aerial read caught one edge of a hatched median, not its middle,
over s 230-500, and read a 4.6-6.2 m painted median under the canopy at s 1245-1295. The aerial can't edge
the band per station, so these files read the paint from the lidar.

Road paint is retroreflective, so a painted line reads as a narrow intensity peak over the asphalt.

- `jackson_intensity.py`: s 1245-1295 every 5 m (the canopy stretch).
  Output: `jackson_intensity_s1245-1295.lidar.g10.json`.
- `jackson_intensity_full.py`: piece D s 225-505 and s 1240-1300 every 2.5 m, from D's own rows (`stations_D.json`:
  x, z -> lon / lat by scripts/geometry/projection's series at the origin; +u = left of J4->J5 travel; u from
  right_m - 1 to left_m + 1). Output: `jackson_intensity_D_full.lidar.g10.json`. Per station:
  - every peak's u, with its along-road share (about 1 for a solid line, 0.25-0.5 for a dash);
  - any band of raised mean intensity;
  - the 0.10 m profile;
  - the data's own median and lanes columns, for comparison.

Source: USGS 3DEP CA_SanDiegoCo_D24 (2024, public domain), the LAST returns: class 2 is thin under the canopy.
Every threshold and window is in each script's docstring and marked [invented]. Read on the G10 on 2026-11-23,
`python -I <script> <tiles dir> [stations.json] <out.json>` with laspy, numpy and pyproj.

Findings:
- s 1245-1295: a single centre line at u -0.05 (range -0.5..+0.1), lines at +4.4 and -7.3, then curbs and walks.
  No painted median there.
- s 225-300: two solid lines at about -3.5 and +1.4, likely the hatched band's edges.
- Past s 300: the right-hand edge fades out of the lidar, while a solid line climbs from +1.9 to +3.2.
- The band test finds few bands, because diagonal stripes barely raise a ±3 m mean.
The band's edges past s 300 are read by eye on the aerial and snapped to these solid lines. Where neither shows
an edge, the edge is marked [inferred] (ledger 0099).

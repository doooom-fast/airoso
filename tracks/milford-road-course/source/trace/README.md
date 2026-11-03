# How `source/mrc_fixes.json` was traced (2026-10-28)

Aerial trace, because OSM's outline of this course is wrong (see `../route-notes.md`). Scratch
scripts, not engine code: they run once per re-trace, from a scratch directory.

1. **Imagery.** USDA NAIP 2022-08-16, exported north-up in EPSG:4326 so the raster corners are the
   georeference (no control points to estimate):
   ```
   https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage?bbox=-83.6700,42.5630,-83.6570,42.5770&bboxSR=4326&imageSR=4326&size=2130,3112&format=png&f=image
   ```
   Save as `mrc_wide.png`; write its raw RGB bytes to `mrc_wide.rgb` (PIL `im.tobytes()`).
   `../naip_2022_mrc.jpg` is the same frame at JPEG q88, for reference.
2. **Paved mask.** `net_extract.py` (Blender 4.2's python: it has numpy, the system python doesn't).
   Light-grey, low-chroma, not-green pixels, closed and opened by 2 px, components over 3,000 m².
   Writes `mask.raw`. About 6 minutes; the skeleton graph it also writes was too fragmented to use.
   Then `shadow_patch.py` (system python) adds the east side's tree-shadowed half, which reads
   dark blue (B-R 31-38; shadowed grass 5-14). Delete any `dist.npy` before step 3.
3. **Centre line.** `tracer.py F1.json` (Blender python). The waypoints in `F1.json` choose the
   branch at every junction; between them a shortest path whose cost falls toward the middle of
   the pavement follows the road. Writes `F1.path.json`.
4. **Centre + width.** `finalize.py F1` (system python). Smooths, then three rounds of
   perpendicular scans re-centre the line and measure the paved width every 2 m. Stations wider
   than 18 m (aprons, merges) keep the tracer's line. `ZONES` adds wide smoothing where a branch
   joins: at the serpentine exit, and at the east side's gore and cross-connector. Writes
   `F1.final.json` (4,072 m).
5. **Fixes.** `to_fixes.py F1 <repo>/tracks/milford-road-course/source/mrc_fixes.json` clamps the
   widths and rotates the S/F to station 0.
6. **Pipeline.** `python -m scripts.gps.from_track tracks/milford-road-course
   tracks/milford-road-course/source/mrc_fixes.json --loop`, then `scripts/build.sh
   tracks/milford-road-course elev` (the `gps` stage needs OSM road names, which this track has
   none of).

Check every re-trace by overlaying the path on the image, especially at junctions. The first
pass took the left fork at the serpentine exit and made a 14 m hook onto the top straight, which
showed up as the tightest corner on the lap. The trace's 3DEP relief must stay 40 ± 2 m.

Two one-run corrections sit on top of step 5's output, in this order; a re-trace must apply both
(or fix their causes in `to_fixes.py`):

- `unsquash_frame.py` (2026-10-31, ledger 0062): the export's true latitude extent.
- `apron_corner.py` (2026-11-03, ledger 0069): the scans read the run-off apron outside the
  left-hander at about s 1,000 as road (21 m wide, the line on the asphalt's outer edge). The
  apron rule in step 5 (over 22 m) did not catch it: in the squashed frame it read 15.7 m.
  Check every corner whose traced width jumps above its approaches the same way.

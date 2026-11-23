# The far-clip test: result (PC, 2026-11-22)

**Answer:** Assetto Corsa with CSP draws geometry at 25, 60 and 105 km, but only when the **track** marks those meshes
to ignore the far plane. Without that, this PC stops drawing between 19 and 25 km. The track's own
`extension/ext_config.ini` can carry the setting, so true distance (PLAN D6) works without touching the player's settings.

```ini
[SHADER_REPLACEMENT_...]
MESHES = FARCLIP_?            ; the backdrop's meshes
DISTANT_FIX = 1
DISABLE_FAR_PLANE_CLIPPING = 1
```

**Kevin's look is still the verdict on how it looks.** He drove the first version (three 2° walls, no setting) toward
Colorado Boulevard at dusk and saw nothing: "There's no mountains there." He has not seen the working version; the
pictures below are the PC's.

## What was run

- PC: Assetto Corsa + CSP **0.3.0-preview581** (`dwrite.dll` 0.3.0.581), 3440 × 1440, started from Content Manager.
- Host: a copy of the installed Sand Creek Raceway 0.2.8 as `content/tracks/zz_farclip_test`, layout `race`, with
  `farclip.kn5` listed last in both `models_*.ini`. The real install was not touched. The copy is out of AC again
  (`D:/k10-track-archive/2026-11-22_211253_zz_farclip_test`).
- Weather: Kevin's own setup, the Pure controller (`pureCtrl`, CM weather type 15). Two times of day: **16:54-16:55**
  (his default; dusk in late November) and **11:59:40**. The weather preset itself was not changed, so the spec's
  "clear midday preset" was run as "Pure at midday".
- Views: from the grid, cockpit and chase camera, car standing. The grid is at AC (-528, 27.4, 717), heading 282° true,
  890 m from the track origin, so the near markers sit a few degrees off their nominal bearing (parallax); the far ones
  do not.
- The piece was made with the chain's own export (`scripts/ac/export_kn5_addon.py` and the vendored AC add-on), no new
  exporter: `tools/make_farclip_blend.py` builds the scene, `tools/export_farclip.py` runs the export with one material
  hook (`ksPerPixel`, the checker as `txDiffuse`, `ksAmbient 1 / ksDiffuse 0 / ksSpecular 0`). 15 quads, 45 KB.

## Where this departs from the spec

1. **The spec's viewpoint does not work.** The Sand Creek grid is in a K-rail corridor with buildings to the west.
   Walls 2° tall with their bottom edge at the origin's height are hidden behind the track's own buildings and ground
   from there. Kevin: "You won't see them from here in real life either. You're going to have to go further towards
   Colorado Boulevard". So the piece got two additions, and the car was not driven:
   - a **beacon** above each wall, 2° to 10°, same bearing and width (`FARCLIP_025_HI` and so on);
   - a **distance ladder** (`FARLAD_<km>_<R|G|B>`): beacons 2° wide, 2° to 10° tall, at 2, 5, 10, 15, 19, 25, 40, 60
     and 105 km on bearings 262° to 302°, colours cycling red / green / blue, with no setting on them.
2. **Not done:** driving 500 m and turning the camera (no popping test in motion); the frame rate with and without
   (no frame-rate readout on screen; not measured).

## Results

| Mesh | Distance | No track setting | With the setting, present at load |
|---|---|---|---|
| ladder | 2, 5, 10, 15, 19 km | draws | (not set) |
| ladder | 25 km | **does not draw** | (not set) |
| ladder | 40, 60, 105 km | **does not draw** | (not set) |
| `FARCLIP_025` + beacon | 25 km | does not draw | **draws** |
| `FARCLIP_060` + beacon | 60 km | does not draw | **draws** |
| `FARCLIP_105` + beacon | 105 km | does not draw | **draws** |

1. **Which draw.** With nothing set, drawing stops between 19 and 25 km. That matches the player's CSP Graphics
   Adjustments, `[ADAPTIVE_CLIP_PLANES] FAR_PLANE=20000,30000` (with `FOV_RANGE=0.5,12`): 20 km at a driving field of
   view. AC's own `video.ini FARPLANE=600` is not what limits it.
2. **The setting that makes them draw** is the block at the top, in the track's `ext_config.ini`. Shots 03 and 04: the
   60 and 105 km walls (and the 25 km one at the left edge of 04) stand with the setting on `FARCLIP_?`. Shot 05: the
   setting on `FARCLIP_025?, FARCLIP_060?` only; those two draw and the 105 km wall, unset in that run, does not.
   - It is per mesh and the track carries it. The player changes nothing.
   - **It has to be there when the track loads.** Added mid-session, CSP reloaded the config (its log: "Reloading
     settings", "Loading configs for zz_farclip_test") and the walls still did not appear (shot 02).
   - Not separated: which of the two keys is the one that matters. Both were set together, as `nohesi_110`'s
     "Mountain Fix" and CSP's own `Material_DistantGeometry` template do.
   - Not tested: the player-side route (raising `FAR_PLANE` in CSP's Graphics Adjustments).
3. **Steady or not.** In stills taken seconds apart and from two cameras the panels are solid: no depth-fighting
   stripes, no edge cut by a clip plane, and nearer ladder beacons sit in front of farther ones (the 5 km beacon hides
   most of the 10 km one). The walls cover the clouds behind them, at every distance. Motion was not tested.
4. **Haze.**
   - Midday (shots 05, 06): colour runs to one saturated blue with distance. The 2 km beacon is its true red and
     white; 5 km is tinted but readable; from 10 to 19 km the panels are blue with the checker faint; the red 25 km
     wall and the green 60 km wall are the same flat blue. They do not fade into the pale sky at the horizon: they
     read as blue slabs, darker than the sky behind them. 25 km and 60 km look alike, so the fog is saturated by
     about 15 to 20 km.
   - Dusk (shots 03, 04; the sun down behind the walls): everything from 10 km out is a near-black navy silhouette
     against the bright sky; 5 km is grey-green; 2 km is its true colours.
   - What follows for the backdrop [the PC's reading, not Kevin's]: past about 15 km under Pure, the backdrop's own
     colour and texture barely show. Its outline and the fog colour are what read.
5. **Frame rate:** not measured.

## Settings in force

- CSP 0.3.0-preview581. `cfg/extension/graphics_adjustments.ini`: `[ADAPTIVE_CLIP_PLANES] FAR_PLANE=20000,30000`,
  `FOV_RANGE=0.5,12`, `NEAR_PLANE=0.1,10` (CSP's defaults: `extension/config/graphics_adjustments.ini` has the same).
- `cfg/video.ini`: `FARPLANE=600`.
- Weather FX with the Pure controller; no fog or clip key in the test track's `ext_config.ini` beyond the block above.

## Pictures (`shots/`, 1568 px wide)

- `01_dusk_noflag_none_draw.jpg`: walls and beacons at 25 / 60 / 105 km in the file, no setting: nothing draws.
- `02_dusk_flag_added_live_no_change.jpg`: the setting added while the session ran: still nothing.
- `03_dusk_flag_at_load_cockpit.jpg`: the ladder to 19 km, and the 60 and 105 km walls with the setting.
- `04_dusk_flag_at_load_chase.jpg`: the same from the chase camera, the 25 km wall at the left edge (the white box is
  a Content Manager dialog the capture masked).
- `05_midday_flag_025_060_only_chase.jpg`: midday; 25 and 60 km set and drawn, 105 km unset and absent, and no
  ladder beacon right of the red 2 km one (25, 40, 60, 105 km unset).
- `06_midday_zoom_walls.jpg`: the same, closer.

## What went wrong on the way (for the next test in AC)

- Starting `acs.exe` directly from a tool shell fails ("Steam API has failed to initialize") and took Kevin's Steam
  down. Start the game from Content Manager's Go, nothing else.
- Ending the session by closing the process leaves a Content Manager result dialog open each time. Close them after.

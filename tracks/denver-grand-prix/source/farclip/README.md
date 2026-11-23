# The far-clip test (PLAN §3 "Unknown, tested first")

**Question:** does Assetto Corsa with CSP draw geometry 25, 60 and 105 km from the car, and how does it look
(clipped, flickering, fogged out)? The Front Range backdrop's design depends on the answer (PLAN D6): true distance
if 105 km draws, a uniform shrink toward the track origin if it does not.

**Kevin, 2026-11-23:** "have the pc run the far-clip test".

## The test piece

A scratch copy of an installed track with one extra visual-only kn5. Nothing in the repo's tracks changes and
nothing is published.

- **Host:** a copy of the installed Sand Creek Raceway folder, as `content/tracks/zz_farclip_test` (its own
  `ui_track.json` name "ZZ far-clip test"), so the real install is untouched. Sand Creek because its west is open.
- **Add `farclip.kn5`** to that copy and list it in every layout's `models_*.ini`. Three flat vertical walls, no
  digit prefix (visual only, no physics), each facing the track origin, each **2° tall and 4° wide** as seen from
  the origin so they are the same size on screen if all three draw, bottom edge at the origin's height:

  | Mesh | Distance | Bearing (true, from the origin) | Height × width | Colour (unlit, flat) |
  |---|---|---|---|---|
  | `FARCLIP_025` | 25 km | 250° | 873 m × 1,746 m | red |
  | `FARCLIP_060` | 60 km | 270° | 2,095 m × 4,190 m | green |
  | `FARCLIP_105` | 105 km | 290° | 3,667 m × 7,333 m | blue |

  2° is the real Front Range's height on the skyline. Each wall gets a 10 × 5 checker of two shades so depth
  flicker shows. Flat on purpose: this tests the renderer's reach, not Earth curvature (the real bake drops
  vertices by curvature, 785 m at 105 km; a wall that tall still stands 2,880 m clear).
- Build it however the PC's chain makes a kn5 from Blender (the AC add-on export the ship phase uses). No new
  exporter, no kn5 writer.

## What to record

From the grid, facing west, in a clear midday weather preset and again in the default one:

1. Which of the three walls draw at all.
2. For each that draws: steady, flickering (depth fighting against the sky or the ground), or cut by a clip edge.
   Drive 500 m and turn the camera; note any popping.
3. How much haze or fog fades each (a screenshot per wall, and one wide shot with all three).
4. The settings in force: CSP version, and any far-plane / clip-distance / fog-distance values in the video,
   CSP graphics-adjustments, weather-FX and track `ext_config.ini` settings that govern it. If a wall does not
   draw, find the one setting that makes it draw, and say whether a track's own `ext_config.ini` can set it
   (so the track carries it) or only the player's settings can.
5. The frame rate with and without `farclip.kn5`.

Write the result to `tracks/denver-grand-prix/source/farclip/RESULT.md` on branch `claude/kind-turing-5xrxlc`
(screenshots beside it, small JPEGs), and delete `zz_farclip_test` from AC afterwards unless Kevin wants to look.

**Kevin's look is the verdict** on "how it looks"; the session's screenshots answer "does it draw".

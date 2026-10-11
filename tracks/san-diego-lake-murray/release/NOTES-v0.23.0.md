**Lake Murray V3 — the loop hand-finished.** Same 13.5 km route as before (Alvarado → College → Navajo → Lake Murray Blvd, Del Cerro side loop); everything on it rebuilt by hand in Blender on top of the engine's draft.

**What changed since v0.22.0**

- **College Ave and Navajo Rd are single full-width streets** with raised median islands — curbs, barriers and planting — where the real ones have them, with gaps at every junction mouth. The sawtooth edges and the phantom opposing lane are gone.
- **Del Cerro Blvd is one divided boulevard** instead of two skinny roads.
- **Side streets follow the real route** (Madra, Delaware, Pennsylvania Lane and the rest), butt-welded into the mainline at height; sidewalks stop at every mouth instead of crossing it. Terrain is seated under every road.
- **Smoother profile**: 4.97 kinks/km (was 47), zero severe steps, zero obstructions on the driving line.
- **Street lamps** at 11.5 m with ~240 CSP lights, dimmed to street level (no glowing balls).
- **Minimap** is drawn in the car's frame (the old one was mirrored).
- Start/finish and the pit row sit at the lap seam, the turn onto Alvarado. `ai/fast_lane.ai` ships.

**Known**: a little terrain float (< 0.6 m) on a couple of Del Cerro side streets; the College south hairpin and the lap seam are rougher than the rest.

**Needs Custom Shaders Patch** (lights; TreeFX vegetation where present). Pure or Sol recommended. Drag the zip into Content Manager or unzip into `content/tracks/`.

| Track | Length | Layouts | AI line |
|---|---|---|---|
| Lake Murray loop | 13.5 km | Full | yes |
| San Diego freeway network | 223 km network | free roam | no — carried forward unchanged from v0.21.0 (byte-identical kn5) |

Credits and licences are in each zip (`CREDITS.txt`, `LICENSES.md`).

_Source: the `airoso` repo (local, not on GitHub yet) `tracks/san-diego-lake-murray` (the V3 line; this is airoso build 0.16.0). This public zip is the CC0 variant: no third-party tree models or textures — see its `LICENSES.md`._

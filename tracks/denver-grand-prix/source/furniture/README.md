# Denver Grand Prix — street furniture made for PLAN §4b (2026-11-23)

The asset half of "streetlights, signals and signs as accurate as possible". Everything here is generated,
self-made and CC0; nothing is placed on the track, no config changed, nothing installed. Ledger 0096.

| Still | Shows |
|---|---|
| `stills/signal_mast_arms_25_35_45.jpg` | the three mast arms with heads at the spec's default stations and a pedestrian head on the pole |
| `stills/signal_heads.jpg` | every vehicle head, the light-rail head, the pedestrian head (hand lit, walk lit) |
| `stills/signal_pedestal_and_pushbutton.jpg` | the pedestal recipe and the pushbutton post |
| `stills/streetlight_classes.jpg`, `stills/streetlight_pedestrian_posts.jpg` | the four provisional lamp classes |
| `stills/sign_faces.jpg` | all 28 faces on their plates, eight of the blades |
| `stills/rail_crossing_set.jpg` | W10-1, the crossbuck, the light-rail signal on a pedestal |

The grey box in a still is 1.8 m tall. Stills are Blender 4.2.9 renders (`tools/street_furniture_stills_blend.py`),
built from the committed OBJs through the JSON specs' own recipes, so a still also proves the spec assembles. They
are previews of the assets, not of the track, and not what Assetto Corsa will draw: no export has been made.

## What was made, and what each dimension rests on

| Asset | Files (`assets/models/`) | Tris | Rests on |
|---|---|---|---|
| Mast arms, 25 / 35 / 45 ft | `signal_mast_arm_<ft>.obj` | 146 each | **typical**: three lengths chosen for 2, 3, 4 lanes; arm at 19 ft rising 1.5 deg; 22 ft pole, 13 in OD. Set so that every head clears MUTCD 4D.15 (15 ft under, 25.6 ft over): the test proves it for all three. Denver's standard arms are not checked |
| Pedestal | `signal_pedestal.obj` | 32 | NPS 4 pipe (4.5 in OD); 10 ft height and the cast base **typical**; the head on it sits inside MUTCD 4D.15's 8 to 19 ft |
| Vehicle heads: 3-section, 3-section arrow, 4-section flashing-yellow-arrow, 5-section cluster left and right | `signal_head_*.obj` | 154 to 254 | lens 12 in, MUTCD 4D.07; backplate per 4D.12 (the optional yellow edge is not drawn); housing 13.5 x 14 x 8 in, 10 in tunnel visor, 5 in backplate border **typical** |
| Pedestrian head | `signal_ped_head.obj` | 56 | the 16 x 18 in class, drawn 18 wide x 16 high (**typical** which way round); symbols 9 in, MUTCD 4E.04; mounted 8 ft, inside 4E.05's 7 to 10 ft |
| Pushbutton post | `signal_pushbutton_post.obj` | 60 | button at 3.5 ft, MUTCD 4E.08; R10-3 plate 9 x 12 in, Table 2B-1; post **typical** |
| Light-rail signal | `signal_head_lrt_2.obj` | 112 | white bar aspects, MUTCD 8C.11; the same 12 in sections |
| Lamp: pedestrian post, acorn or globe | `streetlight_ped_acorn.obj`, `_ped_globe.obj` | 310, 270 | **all typical, class provisional**: 12 ft post, 16 x 30 in acorn, 18 in globe |
| Lamp: arterial bracket-arm post, single or twin | `streetlight_arterial_single.obj`, `_twin.obj` | 96, 144 | **all typical, class provisional**: 30 ft pole, 8 ft arms, 32.5 ft mounting, 0.14 in/ft taper |
| Sign faces (28) | `assets/textures/mutcd_<code>.png` | plates 4 to 28 | sizes from MUTCD Table 2B-1 / 2C-2 / 8B (single-lane sizes); layouts and letters approximate, not sheet-exact |
| Street-name blades (38) | `../../textures/blades/` | 4 | 36 x 9 in **typical**; **style unverified** |
| Crossbuck | `rail_crossbuck.obj` | 30 | two 48 x 9 in blades at right angles, MUTCD 8B.03; centre at 9 ft recalled from Figure 8B-2 |

**The MUTCD was not opened in the session that made these.** Section numbers and values were written from knowledge
of the 2009 edition. They are stated in each maker's docstring so they can be checked; check one before a gate
leans on it.

## Checked against the library first

- `led_cobra` (`tools/make_streetlight_led.py`) already is the 35 ft cobra-head light, single or twin. Not remade.
- The Dropbox "US traffic signs pack" (57 sign JPGs) covers much of the sign set, but its licence is unrecorded,
  so it cannot ship in the CC0 package. The faces here are its owned replacement.
- No signal furniture of any kind was owned.

## DOSSIER §8, row by row

| §8 row | After this |
|---|---|
| Signal masts, pedestal and pedestrian heads | **models exist.** Still open: Denver's real arm lengths, pole type and finish; whether masts carry a luminaire or an overhead street-name sign; the engine's pbr rows; placement from `source/survey/signals.json` |
| Streetlight classes | `led_cobra` plus two **provisional** families. Still a gap until the survey names the fixtures on the lap; then one `CLASSES` row per class |
| Regulatory and guide sign faces | **regulatory and warning faces exist.** Still open: guide signs beyond street-name blades (none drawn: route markers, overhead guide panels, parking signs), blade style, the bus-lane legend, and plate UVs through the prep |
| Tower facades | not touched (out of scope) |
| Landmarks | not touched (out of scope) |
| Concrete street, brick crosswalk, rail-in-street surfaces | not touched (out of scope) |
| Trees | not touched (out of scope) |

Not in §8 and still not made: crossing gates and flashing-light rail signals, the light-rail catenary on Stout, bus
shelters, hydrants, parking meters, sign posts and mast-arm sign brackets (the existing sign tool draws its own post).

## What the engine has to do before any of this shows in a build

1. Keep the UVs of sign plates, signal lenses and the pedestrian face through the prep (PLAN §4b engine work 8).
2. Add the pbr rows listed in `assets/models/signals.json` `bindings_proposed` and one per sign face.
3. Split each OBJ into its objects (`tools/street_furniture_mesh.read_obj_objects`); `load_obj_full` merges them.
4. Choose which lens is lit at night (E2: steady) and give it the CSP emissive; the unlit lenses use `_off` textures.

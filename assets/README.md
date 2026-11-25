# Asset provenance

Real assets from Kevin's Dropbox library (`C:\Users\Owner\Dropbox\Blender\`), converted
2026-08-07 per fleet/feedback/0005 (PoT textures, instance-safe decimation, base at y=0,
Y-up, heights normalized). Conversion scripts: session scratchpad `convert_dropbox_props.py`
+ `convert2.py` (headless Blender 4.2).

| engine file | source | processing |
|---|---|---|
| models/poplar_trunk.obj | tree_topol.rar → tree_poplar.glb (bark material part) | split by material, decimated to 1,800 tris, height 14 m |
| models/poplar_leaves.obj | tree_topol.rar → tree_poplar.glb (leaf material part) | decimated to 2,382 tris |
| models/lamp_post.obj | Street_Lamp.zip → Street_Lamp.blend (94,587 tris) | decimated to 3,783 tris, height 9 m (build_env rescales per config) |
| textures/poplar_bark.png | glb-embedded BARK_tex_uv_COLOR 4096² | PoT 2048² |
| textures/poplar_leaves.png | glb-embedded TexturesCom_Branches0025 1366×1600 | PoT 1024² |
| textures/pine_leaves.png | pine_tree.zip → assets/PinesLeaves.png 1800×1200 | PoT 1024² (existing pine model, real needles) |
| textures/pine_bark.png | pine_tree.zip → assets/Bark.jpg 4600×1960 | PoT 1024² (staged for the pine two-part upgrade) |
| textures/street_lamp_new.png | Street_Lamp.zip → Textures/lamp_basecolor.png 4096² | PoT 1024² |

Still placeholder (0005 remainder): concrete barrier set, traffic-sign pack (`Dropbox/Blender/obj/`),
fences, pine trunk geometry (Small_Pine.blend has unlabeled materials — needs a hand pass),
Street_Lamp full PBR (ao/metal/norm/emiss staged in Dropbox, engine shader path is diffuse-only today).

## Generated street furniture (ledger 0096, 2026-11-23) — self-made, CC0

Not from Dropbox. Deterministic generators; `--check` on each compares the committed files, and
`tests/tools/test_street_furniture.py` runs them.

| engine files | generator | notes |
|---|---|---|
| models/signal_*.obj, signals.json; textures/signal_lens_*.png, ped_signal_*.png | tools/make_signals.py | mast arms, pedestal, pushbutton post, heads with each lens a separate mesh; MUTCD where it fixes a number, `[typical]` elsewhere |
| models/streetlight_ped_*.obj, streetlight_arterial_*.obj, streetlight_posts.json | tools/make_streetlight_posts.py | two provisional lamp classes beside led_cobra |
| textures/mutcd_r*.png, mutcd_w10-1.png, mutcd_w11-2*.png; models/sign_plate_*.obj, sign_faces.json | tools/make_sign_faces.py | 28 MUTCD faces and their plates; Denver's blades go to tracks/denver-grand-prix/textures/blades/ |
| models/rail_crossbuck.obj, rail_crossing.json | tools/make_rail_crossing.py | the crossbuck |

Stills and the per-asset table: `tracks/denver-grand-prix/source/furniture/README.md`. None of it is bound by
`scripts/ac/pbr.py` yet.

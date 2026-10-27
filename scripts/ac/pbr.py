"""Shared PBR material setup for the Blender render/export scripts.

Maps an imported object's name prefix to a texture set under ``assets/textures/`` and builds a
Principled material with a tiling diffuse + normal map driven by the mesh's UVs (generated in the
geometry pass). Falls back to a flat colour when a texture is missing, so it degrades gracefully.

Not a Blender entry point — import it (``from scripts.ac import pbr``) and call ``setup_material``.
"""

from __future__ import annotations

import json
from pathlib import Path

# name-prefix -> (diffuse, normal, roughness, fallback_rgba, metallic, water)
TEXTURES = {
    "1ROAD":   ("asphalt_cracked_diffuse.jpg", "asphalt_cracked_normal.jpg", 0.80, (0.10, 0.10, 0.11, 1), 0.0, False),  # cracked/alligator asphalt (LA Canyons lac_tarmac_cracked)
    "1RUNOFF": ("asphalt_cracked_diffuse.jpg", "asphalt_cracked_normal.jpg", 0.85, (0.16, 0.15, 0.14, 1), 0.0, False),
    "CALIB":   (None, None, 0.4, (1.0, 0.05, 0.6, 1), 0.9, False),  # bright emissive magenta — temp orientation poles
    # 1KERB_SIDEWALK BEFORE 1KERB: prefix order = match priority. The loop-path street curb+sidewalk
    # (build_kn5_loop renames CURB -> 1KERB_sidewalk) binds CONCRETE (grey), not the red racing kerb,
    # and MUST carry a diffuse — a textureless kn5 material renders BLACK in-engine (the "curbs are
    # black" bug). Bound to the documented-CC0 concrete tile (building_*); San Diego's local
    # concrete_diffuse.jpg has no provenance entry in its licenses.json, so it stays out of the engine.
    "1KERB_SIDEWALK": ("building_diffuse.jpg", "building_normal.jpg", 0.75, (0.66, 0.66, 0.64, 1), 0.0, False),
    # 1KERB_RACE BEFORE 1KERB (ledger 0047): the race layouts' flat rumble kerbs
    # (tools/author_race_furniture_blend.py) bind by their OWN row, so no change to the generic 1KERB
    # row (or an override keyed "1KERB") can reach them. Ledger 0053 (Kevin: "i'd like the race curbs
    # to be tire-worn/textured"): the worn atlas from tools/make_kerb_texture.py (CC0) — 4 columns of
    # tyre-rubber level x 8 m of 1 m red/white blocks — plus its normal map, so the exporter picks
    # ksPerPixelMultiMap (diffuse + normal, the path 1WALL_RACE already renders through in game). The
    # kerbs carry their own per-face-corner UVs (race_furniture.kerb_atlas_face_uvs: the column by
    # wear, v along the kerb's real length), kept by the prep's planar_uv skip.
    "1KERB_RACE": ("kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg", 0.55, (0.62, 0.10, 0.08, 1), 0.0, False),
    "1KERB":   ("kerb_diffuse.png",    None,                 0.55, (0.62, 0.10, 0.08, 1), 0.0, False),
    "CURB":    ("building_diffuse.jpg", "building_normal.jpg", 0.70, (0.64, 0.64, 0.66, 1), 0.0, False),   # concrete street curb (fallback if a loop mesh keeps this name)
    "SIDEWALK": ("building_diffuse.jpg", "building_normal.jpg", 0.75, (0.68, 0.68, 0.66, 1), 0.0, False),  # concrete sidewalk slab
    "MARKINGS": ("line_white.png", None, 0.45, (0.88, 0.88, 0.85, 1), 0.0, False),  # white lane lines — solid-colour TEXTURE, not a bare colour: texture-less kn5 materials render BLACK in-engine (the San Diego lines-end-up-black bug)
    "YLINE":   ("line_yellow.png", None, 0.45, (0.85, 0.68, 0.10, 1), 0.0, False),  # double-yellow centreline (two-way roads, Lake Murray style)
    "ROADTEXT": ("roadtext_atlas.png", None, 0.5, (0.92, 0.92, 0.90, 1), 0.0, False),  # painted street-name decals (alpha cutout)
    "1LAWN":   ("grass_diffuse.jpg", "grass_normal.jpg",     0.90, (0.30, 0.42, 0.20, 1), 0.0, False),  # irrigated suburban green turf (SoCal neighbourhood tiles)
    # 1GRASS_ROCK BEFORE 1GRASS (ledger 0054 P4 buildings + rock): the steep faces of a road cut, split out of the
    # physical ground tiles by tools/rock_faces_blend.py after the kn5 prep. They keep the 1GRASS prefix on purpose —
    # same surfaces.ini key (GRASS), same physics, read as ground by every gate — and bind their OWN row here, so a
    # track's "1GRASS" turf override never reaches them (overrides bind by the matched key). Stock skin: the tan stone
    # tile; Lake Murray overrides it with its own sandstone / conglomerate cut (texture_overrides["1GRASS_ROCK"]).
    "1GRASS_ROCK": ("stone_tan.png", None,                   0.92, (0.62, 0.54, 0.42, 1), 0.0, False),
    "1GRASS":  ("ground_dry_diffuse.jpg", None,              0.95, (0.42, 0.38, 0.29, 1), 0.0, False),  # dry dirt/chaparral (canyon/hill/freeway-cut tiles)
    # GRASS_FAR: the visual-only far ring of a tiered terrain (ledger 0046 E3; Cowles, the valley walls). No digit
    # prefix = no physics, never a gate / GrassFX / occluder mesh. TEXTURED dry chaparral — never the MOUNTAINS
    # slot, whose texture-less material renders black in-engine (fleet/LAWS.md L7). A config override keyed
    # "1GRASS" (Lake Murray's green turf) does not reach it: overrides bind by the matched key.
    "GRASS_FAR": ("ground_dry_diffuse.jpg", None,            0.95, (0.42, 0.38, 0.29, 1), 0.0, False),
    "SHOULDERUND": ("ground_dry_diffuse.jpg", None, 0.95, (0.36, 0.32, 0.25, 1), 0.0, False),  # embankment/cut mass seen from BELOW (visual underside of the shoulder strip)
    "ROCKCUT":  ("rock_granite_red.png", None, 0.92, (0.45, 0.30, 0.24, 1), 0.0, False),  # blasted red granite cut faces (Kevin's stone-wall asset harvest) — task #17 consumer
    "RETWALL":  ("stone_tan.png", None, 0.85, (0.55, 0.48, 0.38, 1), 0.0, False),           # retaining wall body — task #17 consumer
    "1WALL_PARA": ("stone_tan.png", None, 0.85, (0.58, 0.51, 0.41, 1), 0.0, False),          # 1913 stone guard parapets (collidable; MUST precede the generic 1WALL entry — prefix match is dict-ordered)
    "1WALL_CHAINL": ("chainlink_diffuse.png", None, 0.6, (0.55, 0.56, 0.58, 1), 0.3, False),  # chain-link warning fences (Kevin: 'use chain link, not wood') — before 1WALL, dict-ordered
    # 1WALL_GUARD BEFORE 1WALL: build_kn5_loop renames GUARDRAIL -> 1WALL_guard before materials
    # bind, and prefix order = match priority — without the sub-prefix first it would fall through
    # to the barrier-module tile. Low grey concrete rail (the loop's I-8 bridge rail).
    "1WALL_GUARD": ("building_diffuse.jpg", "building_normal.jpg", 0.55, (0.74, 0.75, 0.77, 1), 0.10, False),
    # 1WALL_RACE BEFORE 1WALL (ledger 0047): the race K-rail (centre chain + kerb-line strips,
    # 1WALL_race_*) is Kevin's concrete barrier module swept as a strip (u = arc / 4.04 m). Without its
    # own row it fell through to the generic 1WALL key, and a track whose config sets
    # pbr.network_walls (Lake Murray does, for the merged freeway's 1WALL_fw barriers) overrides THAT
    # key with the cast-concrete building tile — the race strips would have shipped as building
    # concrete, not K-rail. Overrides are looked up by the MATCHED key (setup_material /
    # export_kn5_addon.shader_and_textures), so a row of its own is immune to the network-wall skin
    # (load_overrides only ever writes "1WALL"). NOTE: a future 1WALL_RACECOL collider (Q11) also
    # starts with 1WALL_RACE — it needs its own row ABOVE this one (alpha-tested invisible), or it
    # would render as visible K-rail.
    "1WALL_RACE": ("concrete_barrier_diffuse.png", "concrete_barrier_normal.png", 0.85, (0.72, 0.72, 0.70, 1), 0.0, False),
    # 1WALL_STUB BEFORE 1WALL (ledger 0054 phase 5, tools/author_stubs_blend.py): the barrier across every unbuilt side
    # road's stub is the same K-rail module swept as a strip (u = arc / 4.04 m) — its own row for the reason above
    # (the network-wall override reskins only the generic 1WALL key). It ships in the ROAD kn5 (all layouts).
    "1WALL_STUB": ("concrete_barrier_diffuse.png", "concrete_barrier_normal.png", 0.85, (0.72, 0.72, 0.70, 1), 0.0, False),
    "BUSHES":  ("bushes_atlas.png", None, 0.9, (0.36, 0.37, 0.24, 1), 0.0, False),  # dry scrub billboards (LA Canyons bo_bushes_11)
    "HIGHWAY": ("asphalt_cracked_diffuse.jpg", "asphalt_cracked_normal.jpg", 0.80, (0.30, 0.30, 0.32, 1), 0.0, False),  # I-70 deck
    "HWYSTRUCT": ("building_diffuse.jpg", "building_normal.jpg", 0.85, (0.68, 0.68, 0.66, 1), 0.0, False),  # concrete parapets/piers
    # BRIDGESTRUCT: the loop's overcrossing bodies (soffit, fascia, abutment walls, pier bents; tools/author_bridges_blend.py,
    # ledger 0046 fix round 4). Visual only (no digit prefix) and NOT HWYSTRUCT, which the gates read as structure.
    "BRIDGESTRUCT": ("building_diffuse.jpg", "building_normal.jpg", 0.85, (0.66, 0.66, 0.63, 1), 0.0, False),
    "BUILDING": ("building_diffuse.jpg", "building_normal.jpg", 0.88, (0.60, 0.60, 0.58, 1), 0.0, False),  # tilt-up concrete (mined Hamburg)
    "WAREHOUSE": ("warehouse_diffuse.jpg", "warehouse_normal.jpg", 0.90, (0.56, 0.56, 0.54, 1), 0.0, False),  # weathered concrete warehouse walls (mined Hamburg)
    "WHMETAL":  ("warehouse_metal_diffuse.jpg", "warehouse_metal_normal.jpg", 0.65, (0.58, 0.60, 0.62, 1), 0.10, False),  # corrugated-metal warehouse (CC0 CorrugatedSteel) — warehouse variety
    "BRICK":   ("brick_diffuse.jpg",   "brick_normal.jpg",   0.90, (0.45, 0.28, 0.22, 1), 0.0, False),  # red brick (mined Hamburg) — building variety
    "STUCCO":  ("stucco_diffuse.jpg",  "stucco_normal.jpg",  0.88, (0.62, 0.32, 0.28, 1), 0.0, False),  # painted stucco (mined Hamburg) — building variety
    "BARRIER": ("building_diffuse.jpg", "building_normal.jpg", 0.85, (0.74, 0.74, 0.72, 1), 0.0, False),  # concrete jersey K-rail
    "1WALL_WOODF": ("wood_fence.png", "wood_fence_normal.png", 0.9, (0.42, 0.33, 0.24, 1), 0.0, False),  # wooden warning fences (must precede 1WALL — dict-ordered prefix match)
    "1WALL":   ("concrete_barrier_diffuse.png", "concrete_barrier_normal.png", 0.85, (0.72, 0.72, 0.70, 1), 0.0, False),  # Kevin's 4 m concrete barrier modules (props.concrete_barriers)
    "FENCEWOOD": ("ranch_fence_diffuse.png", "ranch_fence_normal.png", 0.9, (0.45, 0.35, 0.25, 1), 0.0, False),  # split-rail ranch fence panels (scenery.fences, right-of-way line)
    "WOODFENCE": ("wood_fence.png", "wood_fence_normal.png", 0.9, (0.42, 0.33, 0.24, 1), 0.0, False),  # Kevin's modular wooden fence (replaces most barriers off the driving surface)
    "PINETREE": ("pine_leaves.png", None, 0.95, (0.15, 0.28, 0.14, 1), 0.0, False),   # 3D pine (near-corridor forest), alpha-cut
    "POPLARLEAF": ("poplar_leaves.png", None, 0.95, (0.24, 0.34, 0.15, 1), 0.0, False),  # poplar canopy (SC creek riparian band)
    "POPLARBARK": ("poplar_bark.png", None, 0.92, (0.42, 0.38, 0.32, 1), 0.0, False),
    "LAMPNEW": ("street_lamp_new.png", None, 0.55, (0.30, 0.31, 0.33, 1), 0.25, False),  # purpose-modeled street lamp (emissive baked into diffuse, opacity in alpha)
    "EUROSIGN": ("eurosign_atlas.png", None, 0.5, (0.85, 0.85, 0.85, 1), 0.1, False),  # circular sign faces, alpha-cut (scenery.road_signs)
    "USSIGN": ("mutcd_atlas.png", None, 0.5, (0.94, 0.70, 0.14, 1), 0.1, False),  # MUTCD yellow-diamond curve/hairpin warnings (Kevin: signage where turns irl are)
    "DANGERLITE": ("solid_red_glow.png", None, 0.3, (1.0, 0.10, 0.06, 1), 0.0, False),  # danger boards at extreme straight-into-hairpin entries (flashing model TBD from Kevin)
    "CONTAINER": ("container_diffuse.jpg", "container_normal.jpg", 0.70, (0.55, 0.30, 0.26, 1), 0.0, False),  # mined Hamburg shipping-container stacks (warehouse yards)
    "CHAINLINK": ("chainlink_diffuse.png", None, 0.60, (0.55, 0.56, 0.58, 1), 0.30, False),  # procedural alpha-cutout chain-link (warehouse yard fences)
    "ROOF":    ("roof_diffuse.jpg",    "roof_normal.jpg",    0.55, (0.26, 0.32, 0.45, 1), 0.10, False),  # PVC membrane roof (mined Hamburg)
    "RFMETAL": ("warehouse_metal_diffuse.jpg", "warehouse_metal_normal.jpg", 0.60, (0.55, 0.57, 0.60, 1), 0.15, False),  # corrugated-metal roof (on metal warehouses)
    "WATER":   (None, None, 0.04, (0.02, 0.10, 0.20, 1), 0.0, True),
    "GUARDRAIL": ("guardrail_diffuse.png", "guardrail_normal.png", 0.45, (0.74, 0.75, 0.77, 1), 0.35, False),  # swept freeway W-beam guardrail (metal)
    "GANTRY":  ("warehouse_metal_diffuse.jpg", "warehouse_metal_normal.jpg", 0.50, (0.66, 0.68, 0.70, 1), 0.40, False),  # galvanized-steel overhead sign portal (SRP-style expressway gantry)
    "FWSIGN":  (None, None, 0.55, (0.06, 0.30, 0.16, 1), 0.0, False),  # green US freeway overhead sign panel
    "PALMS":   ("palms_atlas.png", None, 0.85, (0.20, 0.34, 0.14, 1), 0.0, False),  # California fan palm billboards (SoCal surface streets)
    # loop-path 3D vegetation (San Diego Blender-first scenes): tapered palm trunks + drooping
    # fan-crown frond cards, broadleaf yard trees, dry chaparral scrub.
    "PALMTRUNK": ("palm_bark.png", None, 0.90, (0.45, 0.38, 0.28, 1), 0.0, False),  # tapered palm trunk (procedural bark)
    "PALMFROND": ("palm_frond.png", None, 0.72, (0.24, 0.40, 0.16, 1), 0.0, False),  # drooping fan-crown leaf cards (alpha cutout)
    "TREETRUNK": ("palm_bark.png", None, 0.92, (0.34, 0.26, 0.18, 1), 0.0, False),  # broadleaf shade-tree trunk (bark)
    "TREECANOPY": (None, None, 0.94, (0.21, 0.36, 0.16, 1), 0.0, False),            # opaque green shade canopy (off-road, in yards)
    "SCRUB":    (None, None, 0.95, (0.40, 0.42, 0.25, 1), 0.0, False),              # dry chaparral bush on the open hillsides
    "HOUSE": ("house_diffuse.png", None, 0.88, (0.60, 0.55, 0.48, 1), 0.0, False),  # plaster house props on residential streets (no normal map shipped — CC0 diffuse only)
    "BLDGPLAIN": (None, None, 0.90, (0.72, 0.71, 0.68, 1), 0.0, False),  # extruded OSM footprints, FLAT concrete colour, NO mined sample texture
    "GREEN": (None, None, 0.92, (0.24, 0.42, 0.18, 1), 0.0, False),       # lush green grass over golf/park/open-space OSM zones (flat colour, ksGrass-like)
    "TREES":   ("trees_atlas.png", None, 0.90, (0.13, 0.30, 0.11, 1), 0.0, False),  # mined Colorado 2x2 broadleaf cutout atlas
    "CONIFER": ("conifer_atlas.png", None, 0.90, (0.09, 0.20, 0.09, 1), 0.0, False),  # pine/spruce billboards (mountain tracks, scenery.tree_style "conifer")
    "LIGHTS":  ("solid_lens_warm.png", None, 0.40, (0.95, 0.82, 0.42, 1), 0.4, False),  # cobra-head lamp lens — SOLID TEXTURE (texture-less = renders BLACK); CSP adds ksEmissive at night
    "LIGHTPOST": ("solid_metal_dark.png", None, 0.60, (0.28, 0.29, 0.31, 1), 0.5, False),  # galvanized streetlight mast + arm — SOLID TEXTURE (was texture-less -> BLACK -> invisible posts, v0.7.5)
    "LAMPHEAD": ("solid_metal_dark.png", None, 0.55, (0.32, 0.33, 0.35, 1), 0.3, False),  # luminaire housing — faint CSP night emissive so the lens reads attached
    "SIGNS":   ("signs_atlas.png", None, 0.55, (0.12, 0.40, 0.18, 1), 0.0, False),  # green street-name panels
    "MOUNTAINS": (None, None, 0.95, (0.52, 0.57, 0.66, 1), 0.0, False),  # hazy blue Front Range backdrop (flat silhouette)
    "SIGNPOST": ("solid_metal_grey.png", None, 0.60, (0.45, 0.46, 0.48, 1), 0.0, False),      # grey metal posts — SOLID TEXTURE (texture-less renders black)
    "SIGNPLATE": ("solid_sign_yellow.png", None, 0.35, (1.0, 0.80, 0.0, 1), 0.0, False),   # W1-6 Large Arrow plate + OM1-3 diamond (tools/author_signs_blend.py) — SOLID TEXTURE: the arrow is geometry, the prep's planar UVs would collapse artwork
    "SIGNARROW": ("solid_sign_black.png", None, 0.45, (0.05, 0.05, 0.05, 1), 0.0, False),  # the black arrow + border standing 2-4 mm proud of that plate
    "POLE":    (None, None, 0.85, (0.34, 0.24, 0.16, 1), 0.0, False),               # wooden utility/power pole
    "WIRE":    (None, None, 0.50, (0.06, 0.06, 0.07, 1), 0.0, False),               # overhead power cable
}

# materials drawn as alpha-cutout — wire the texture alpha + clip the transparent bg (trees as
# billboards; painted street names as flat road decals). The export addon also reads this set to set
# ALPHATEST=1 on these materials so the kn5 cuts out the transparent background in-engine.
BILLBOARD = {"TREES", "CONIFER", "ROADTEXT", "BUSHES", "CHAINLINK", "PALMS", "EUROSIGN", "PALMFROND"}

# Shader property overrides written into the kn5 material (export_kn5_addon persistence INI).
# WHY: materials shipped with NO properties -> AC falls back to shader defaults (ksDiffuse ~1.0).
# Vegetation billboards at full diffuse response turned the Lariat's roadside forest radioactive
# green under the streetlight cones while the pools on the near-black asphalt looked correct.
# Real AC vegetation runs ksAmbient-heavy / ksDiffuse-low (LA Canyons convention) so directional
# light (sun OR CSP lamps) grazes it instead of blasting it. Fence wood damped for the same reason.
KS_PROPS = {
    "CONIFER":  {"ksAmbient": 0.55, "ksDiffuse": 0.10, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "TREES":    {"ksAmbient": 0.55, "ksDiffuse": 0.10, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "BUSHES":   {"ksAmbient": 0.55, "ksDiffuse": 0.10, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "PALMS":    {"ksAmbient": 0.55, "ksDiffuse": 0.10, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "PALMFROND": {"ksAmbient": 0.55, "ksDiffuse": 0.10, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "FENCEWOOD": {"ksAmbient": 0.45, "ksDiffuse": 0.35, "ksSpecular": 0.05, "ksSpecularEXP": 8.0},
    "1GRASS_ROCK": {"ksAmbient": 0.50, "ksDiffuse": 0.22, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},   # as the ground it was cut from (ledger 0054 P4)
    "1GRASS":   {"ksAmbient": 0.50, "ksDiffuse": 0.22, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "GRASS_FAR": {"ksAmbient": 0.50, "ksDiffuse": 0.22, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "POLE":     {"ksAmbient": 0.40, "ksDiffuse": 0.15, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    "SIGNPOST": {"ksAmbient": 0.40, "ksDiffuse": 0.25, "ksSpecular": 0.0, "ksSpecularEXP": 1.0},
    # ledger 0053: the worn race kerbs — ambient / diffuse at the 0.4 / 0.4 every neighbouring material ships at
    # (the add-on default), a faint paint sheen well under Kunos red_curb's 0.35 [invented]
    "1KERB_RACE": {"ksAmbient": 0.40, "ksDiffuse": 0.40, "ksSpecular": 0.10, "ksSpecularEXP": 20.0},
}


def texture_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "textures"


def load_overrides(project_dir: str | Path) -> dict[str, dict]:
    """Real-world captured textures to use in place of the stock ``assets/textures`` set, keyed by mesh
    prefix. Read from ``<project>/source/realworld_capture.json`` (texture_overrides[], written by
    scripts/capture/textures.py); paths resolve relative to the project. Empty when no capture exists →
    the build uses the stock textures unchanged. Pure (no bpy) so it's unit-testable."""
    project_dir = Path(project_dir)
    out: dict[str, dict] = {}
    # 1) config-level overrides (track.config.json texture_overrides) — swap a stock texture per
    #    track without renaming meshes (the Lariat's terrain renders alpine grass instead of dry
    #    dirt while staying 1GRASS for physics/audits/GrassFX). Paths resolve vs the REPO root
    #    (assets/textures/...) or the project dir.
    cfgp = project_dir / "track.config.json"
    if cfgp.exists():
        cfg = json.loads(cfgp.read_text())
        repo = Path(__file__).resolve().parents[2]
        for mat, o in (cfg.get("texture_overrides", {}) or {}).items():
            ent = {}
            for k in ("diffuse", "normal"):
                if o.get(k):
                    p = repo / o[k] if (repo / o[k]).exists() else project_dir / o[k]
                    ent[k] = str(p)
            if ent:
                out[str(mat).upper()] = ent
        # 1b) network-track wall look — freeway 1WALL barriers on network builds read as cast
        #     concrete (building texture, the original PAB mapping), not Kevin's 4 m portable
        #     barrier modules. Default = stock table (barrier modules); auto-on when the config
        #     carries a top-level "network" block, overridable either way via pbr.network_walls.
        #     An explicit texture_overrides["1WALL"] entry still wins (skipped above via `out`).
        #     ONLY the generic "1WALL" key is reskinned: every sub-prefix row (1WALL_RACE, _GUARD,
        #     _PARA, ...) matches first in setup_material and keeps its own texture.
        net_walls = (cfg.get("pbr", {}) or {}).get("network_walls")
        if net_walls is None:
            net_walls = "network" in cfg
        if net_walls and "1WALL" not in out:
            td = texture_dir()
            out["1WALL"] = {"diffuse": str(td / "building_diffuse.jpg"),
                            "normal": str(td / "building_normal.jpg")}
        # 1c) road_surface: gravel — the stock 1ROAD/1RUNOFF textures are all asphalt, so a rally
        #     stage built on the same geometry would LOOK paved while driving like dirt. One config
        #     knob drives both halves of the fork (physics live in track_folder.ROAD_SURFACES). An
        #     explicit texture_overrides entry is the human's word and still wins.
        if str(cfg.get("road_surface", "tarmac")) == "gravel":
            td = texture_dir()
            for mat in ("1ROAD", "1RUNOFF"):
                if mat not in out:
                    out[mat] = {"diffuse": str(td / "gravel_road_diffuse.png"),
                                "normal": str(td / "gravel_road_normal.png")}
    # 2) capture-level overrides (real-world textures) fill in ONLY where the config didn't
    #    speak — an explicit track.config.json override is the human's word and wins (Kevin:
    #    Sand Creek uses the Lariat's road/grass look, not the phone-captured pavement).
    cap = project_dir / "source" / "realworld_capture.json"
    if not cap.exists():
        return out
    for o in json.loads(cap.read_text()).get("texture_overrides", []):
        if str(o.get("material", "")).upper() in out:
            continue
        ent = {}
        if o.get("diffuse"):
            ent["diffuse"] = str(project_dir / o["diffuse"])
        if o.get("normal"):
            ent["normal"] = str(project_dir / o["normal"])
        if ent:
            out[str(o["material"]).upper()] = ent
    return out


def match_key(name: str) -> str | None:
    """The TEXTURES row an object/material name binds: the FIRST prefix (dict order) its upper-case
    name starts with — the same expression export_kn5_addon.shader_and_textures uses."""
    up = str(name).upper()
    return next((k for k in TEXTURES if up.startswith(k)), None)


def resolve(name: str, overrides: dict | None = None, tex_dir: Path | None = None) -> dict:
    """Pure (no bpy): what ``setup_material`` / the exporter bind for ``name`` — the matched key and
    the diffuse / normal FILE paths (an override for the matched key wins, else the stock row)."""
    tex_dir = Path(tex_dir) if tex_dir else texture_dir()
    key = match_key(name)
    diff, norm, rough, color, metal, water = TEXTURES.get(
        key, (None, None, 0.8, (0.5, 0.5, 0.5, 1), 0.0, False))
    ov = (overrides or {}).get(key or "", {})
    return {
        "key": key,
        "diffuse": Path(ov["diffuse"]) if ov.get("diffuse") else (tex_dir / diff if diff else None),
        "normal": Path(ov["normal"]) if ov.get("normal") else (tex_dir / norm if norm else None),
        "roughness": rough, "color": color, "metallic": metal, "water": water,
        "overridden": bool(ov),
    }


def setup_material(bpy, obj, tex_dir: Path | None = None, overrides: dict | None = None):
    """Assign a Principled material (diffuse + normal from ``tex_dir``) to ``obj`` by name prefix.
    ``overrides`` (from :func:`load_overrides`) swaps in real captured textures for matching prefixes.
    Returns the material so callers can stamp AC metadata (e.g. ``mat['shaderName']``) on it."""
    tex_dir = Path(tex_dir) if tex_dir else texture_dir()
    key = match_key(obj.name)
    diff, norm, rough, color, metal, water = TEXTURES.get(
        key, (None, None, 0.8, (0.5, 0.5, 0.5, 1), 0.0, False))
    ov = (overrides or {}).get(key or "", {})

    mat = bpy.data.materials.new(obj.name + "_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")

    dpath = Path(ov["diffuse"]) if ov.get("diffuse") else (tex_dir / diff if diff else None)
    if dpath and dpath.exists():
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(dpath), check_existing=True)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if key in BILLBOARD:  # cutout billboard: wire alpha + clip the transparent background
            nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
            for attr, val in (("blend_method", "CLIP"), ("shadow_method", "CLIP"),
                              ("surface_render_method", "DITHERED")):
                try:
                    setattr(mat, attr, val)
                except Exception:
                    pass
    else:
        bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.05 if water else rough
    bsdf.inputs["Metallic"].default_value = metal
    if water and "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.4

    npath = Path(ov["normal"]) if ov.get("normal") else (tex_dir / norm if norm else None)
    if npath and npath.exists():
        ntex = nt.nodes.new("ShaderNodeTexImage")
        nimg = bpy.data.images.load(str(npath), check_existing=True)
        nimg.colorspace_settings.name = "Non-Color"
        ntex.image = nimg
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat

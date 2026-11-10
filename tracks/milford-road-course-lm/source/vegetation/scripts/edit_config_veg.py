"""Ledger 0082 vegetation pass: the config and ship.json edits, as a script so the change is reviewable and re-runnable.

    python edit_config_veg.py <track dir>

track.config.json: the name without "(LM engine)" (Kevin 2026-11-07: "LM is the airoso engine"); version 0.1.3; the TREECARD
cards (0.1.0's invented scatter) out; the measured crowns as TreeFX (scenery.treefx.planted, make_treefx's grammar, with the
opt-in native_h_m: size = measured height / the model's height); the trunk colliders (scenery.bespoke.trunks); the GrassFX zones
read off the measured class map (scenery.bespoke.grassfx_zones) with a fourth look, D (no grass). ship.json: grassfx_aerial and
treefx run; the vegetation files sync in, the TreeFX models by glob (personal use, gitignored, the PC's), the records out.
"""
import json
import sys
from pathlib import Path

track = Path(sys.argv[1])
cfg_p, ship_p = track / "track.config.json", track / "ship.json"
before = cfg_p.read_text(encoding="utf-8")
cfg = json.loads(before)
assert json.dumps(cfg, indent=2, ensure_ascii=False) == before, "the config's formatting is not json.dumps(indent=2)"  # no final newline
gc = json.loads((track / "source" / "vegetation" / "grass_classes.json").read_text(encoding="utf-8"))

cfg["name"] = "Milford Road Course (unofficial)"
cfg["_name_doc"] = ("Kevin 2026-11-07: \"Get rid of Lm Version from names, nothing should be on any other engine now\" / \"LM is the "
                    "airoso engine\". The install folder and slug stay milford_road_course_lm until the merge with the edges branch "
                    "(0.1.4) renames both to milford_road_course and the PC removes the old copies (ledger 0082 vegetation pass, Owed)")
cfg["version"] = "0.1.3"
sc = cfg["scenery"]
b = sc["bespoke"]
b.pop("cards", None)
b["_cards_dropped"] = ("ledger 0082 vegetation pass: 0.1.0's 4,457 TREECARD cards (NAIP colour rule, a 9 m grid with 3 m jitter, 30 % "
                       "interior keep, heights 14-24 m invented) are replaced by the crowns the 2017 lidar measures, planted as TreeFX "
                       "(scenery.treefx.planted)")
b["trunks"] = {"file": "source/vegetation/trunks.json", "radius_m": 0.3, "height_m": 3.0,
               "_source": "ledger 0082 vegetation pass: an unseen collider round every planted tree within 30 m [invented reach] of the "
                          "build's paved surface (source/vegetation/scripts/veg_plan.py COLLIDER_REACH_M): TreeFX trees have no physics. "
                          "radius 0.30 m [invented: tools/verify_race.py TREE_TRUNK_R_M, the fleet's trunk], 3.0 m over the ground "
                          "[invented: over any car's roof]"}
b["grassfx_zones"] = {
    "image": "source/vegetation/grass_classes.png", "bbox_lonlat": gc["bbox_lonlat"], "margin_m": 250, "cell_m": 12,
    "max_rects": 96, "fade_m": 6,
    "classes": [{"map": "C", "mean": [30, 50], "g_over_r": [50, 999], "g_over_b": [50, 999]},
                {"map": "B", "mean": [120, 150], "g_over_r": [0.9, 1.1], "g_over_b": [50, 999]},
                {"map": "D", "mean": [50, 80], "g_over_r": [0, 0.5], "g_over_b": [0, 0.5]}],
    "_source": "ledger 0082 vegetation pass: the image is the MEASURED class map (source/vegetation/scripts/veg_plan.py), one pixel "
               "per 2 m cell, coded so the colour rules here read each class back exactly: C (0,120,0) the wood floor, NAIP 2022's "
               "canopy (its rule calibrated on the 2017 lidar, 97 % / 97 %); B (200,200,0) long grass, NAIP 2022 by 0.1.0's own rule "
               "(the lidar, flown 2017-05-03, holds no standing grass to confirm it); D (0,0,200) no grass, pavement or gravel the "
               "build carries as ground (lidar ground intensity at or under the build's own pavement p75 AND NAIP grey); white = "
               "the base look (mown)"}
sc["treefx"] = {
    "planted": {"file": "source/vegetation/trees.lm.json", "clear_m": 3.0, "zones": {"1": "planted_neighbourhood"},
                "native_h_m": {"Oak3.bin": 8.673, "SycamoreV2.bin": 8.194,
                               "_doc": "the model's height at size 1, m: MEASURED on the PC 2026-11-07 off the installed files "
                                       "(san_diego_lake_murray_v4/extension/trees/<model>/tree.ini HEIGHT; the mesh's y spans "
                                       "-0.29..8.67 m (Oak3, the root flare under the origin) and -0.08..8.19 m (SycamoreV2), in units "
                                       "of HEIGHT; md5 Oak3 24111ede..., SycamoreV2 7010d61f..., equal to Sand Creek's copies; "
                                       "cross-check PalmV1 HEIGHT 20.053 = make_treefx's 'nohesi V1 20 m native'). Every tree's "
                                       "size is its measured height over this"},
                "native_w_m": {"Oak3.bin": 6.089, "SycamoreV2.bin": 6.620,
                               "_doc": "the model's crown width at size 1, m: tree.ini WIDTH (the mesh's horizontal extent is about "
                                       "WIDTH / 2 per unit either side), measured with native_h_m. Every tree's width multiplier is "
                                       "its measured crown over (this x its size): TreeFX's width = <mult>, width-only (the "
                                       "format's own words, docs/TREEFX-FORMAT.md). That it multiplies on top of size is VERIFY "
                                       "IN-GAME"}},
    "_doc": "Ledger 0082 vegetation pass (Kevin 2026-11-07: \"When does Milford get a vegetation pass?\"; \"I just want real\"): one "
            "TreeFX tree per crown the USGS 3DEP lidar (flown 2017-05-03) measures, at its measured top's height, checked against "
            "NAIP 2022 (source/vegetation/inventory.json). Lake Murray's models (personal use, on the PC only; ship.json globs "
            "source/trees/*.bin): planted_neighbourhood = Oak3 3 : SycamoreV2 1, the stand-ins for SE Michigan's oak-hickory-maple "
            "woods (no maple or hickory model exists). clear_m = scenery.corridor_margin_m"}
g = cfg["lighting"]["grassfx"]
g["configurations"]["D"] = {"mask_min_luminance": 2.0, "mask_max_luminance": 2.0,
                            "_doc": "ledger 0082 vegetation pass: no blades (no ground texel is that bright): the pavement and gravel "
                                    "the build carries as ground. VERIFY IN-GAME"}
g["_zones_doc"] = ("ledger 0082 vegetation pass: the zones are the measured class map (scenery.bespoke.grassfx_zones), written by "
                   "tools/plan_grassfx_aerial.py (ship step grassfx_aerial, which 0.1.0-0.1.2 never ran: their B / C looks bound "
                   "nothing)")
cfg_p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

ship_before = ship_p.read_text(encoding="utf-8")
ship = json.loads(ship_before)
assert json.dumps(ship, indent=2, ensure_ascii=False) == ship_before, "ship.json's formatting is not json.dumps(indent=2)"
st = ship["steps"]["ship"]
if "grassfx_aerial" not in st:
    st.insert(st.index("track_folder"), "grassfx_aerial")
if "treefx" not in st:
    st.append("treefx")
si = ship["sync_in"]
si.setdefault("optional", [])
for f in ("source/vegetation/trees.lm.json", "source/vegetation/trunks.json", "source/vegetation/grass_classes.png"):
    if f not in si["optional"]:
        si["optional"].append(f)
si.setdefault("globs", [])
if "source/trees/*.bin" not in si["globs"]:
    si["globs"].append("source/trees/*.bin")
si["_vegetation_doc"] = ("ledger 0082 vegetation pass: the planted crowns, the trunk colliders and the grass class map (committed); "
                         "the TreeFX models (source/trees/*.bin: Lake Murray's Oak3.bin and SycamoreV2.bin, personal use, gitignored) "
                         "the PC copies into tracks/milford-road-course-lm/source/trees/ before the chain (runbook 0082-3)")
so = ship["sync_out"]["files"]
for f in ("data/treefx.report.json", "data/grassfx.aerial.json"):
    if f not in so:
        so.append(f)
ship["_vegetation_doc"] = ("ledger 0082 vegetation pass: grassfx_aerial (the measured grass zones, before the track folder's "
                           "ext_config) and treefx (the measured crowns as TreeFX, after the map) run")
ship_p.write_text(json.dumps(ship, indent=2, ensure_ascii=False), encoding="utf-8")
print("[edit] track.config.json + ship.json written")

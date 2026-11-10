"""edit_config.py <repo> <class>: write furniture pass 1's entries into tracks/milford-road-course-lm/track.config.json
(ledger 0082), one class per run: rails | tyres | sheds | version"""
import json, sys
from pathlib import Path
REPO, CLS = sys.argv[1], sys.argv[2]
P = Path(REPO) / "tracks/milford-road-course-lm/track.config.json"
cfg = json.loads(P.read_text(encoding="utf-8"))
inv = {i["id"]: i for i in json.loads((Path(REPO) / "tracks/milford-road-course-lm/source/furniture/inventory.json").read_text())["items"]}
b = cfg["scenery"]["bespoke"]
SRC = "source/furniture/inventory.json"
if CLS == "rails":
    rails = b.setdefault("rails", [])
    for gid, key in (("G1", "nw_corner_outside"), ("G2", "front_straight_east"), ("G3", "front_straight_west"), ("G4", "infield_esses")):
        it = inv[gid]
        rails.append({"key": f"{gid.lower()}_{key}", "kind": "wbeam", "auto": True, "height_m": 0.70,
                      "polyline_lonlat": it["polyline_lonlat"],
                      "_source": f"{SRC} {gid}: line off NAIP 2022 (+-1 px, {it['length_m']} m; {it['evidence']}); "
                                 "height 0.70 m [invented: an NCHRP-350-era strong-post W-beam's 27-28 in, a standard, not measured here]"})
    b["_rails_doc"] = ("ledger 0082 pass 1: the W-beam (kind wbeam) and tyre walls (kind tyres) on the lines NAIP 2022 shows "
                       "(source/furniture/README.md); auto: a post or module that would stand on a road or off the ground is left out")
elif CLS == "tyres":
    rails = b.setdefault("rails", [])
    for tid, key, dep in (("T1", "nw_hairpin_exit", 1.5), ("T2", "esses_east_leg", 1.2), ("T3", "s1000_apron_back", 1.5)):
        it = inv[tid]
        rails.append({"key": f"{tid.lower()}_{key}", "kind": "tyres", "auto": True, "height_m": 1.0, "depth_m": dep,
                      "polyline_lonlat": it["polyline_lonlat"],
                      "_source": f"{SRC} {tid}: line off NAIP 2022 (+-1 px, {it['length_m']} m); width {dep} m off NAIP (the bar's "
                                 f"width less a pixel of blur); height 1.0 m [invented: five tyres]; identity {it['identity_confidence']}"})
    ov = cfg.setdefault("texture_overrides", {})
    ov["1WALL_TECPRO"] = {"diffuse": "assets/textures/tyre_wall_diffuse.png",
                          "_doc": "ledger 0082: the tyre walls (rails kind tyres, 1WALL_TECPRO_TYRES_*) ride the Tec-Pro row, whose UVs "
                                  "engine-july's prep keeps; Milford has no Tec-Pro, so the row is the tyre skin here "
                                  "(tools/make_bespoke_assets.py tyre_wall, CC0)"}
elif CLS == "sheds":
    blocks = b.setdefault("blocks", [])
    for sid, key, roof in (("S1", "pad_shed_north", "tan"), ("S2", "pad_shed_south", "white")):
        it = inv[sid]
        blocks.append({"key": key, "footprint_lonlat": it["footprint_lonlat"], "wall_h_m": 2.6, "skin": "metal", "roof": roof,
                       "_source": f"{SRC} {sid}: footprint off NAIP 2022 ({it['sides_m'][0]} x {it['sides_m'][1]} m, +-1 px), the roof "
                                  f"colour as the photo shows it; height 2.6 m [invented: a container / site trailer, no shadow "
                                  f"resolvable on the tree side]"})
elif CLS == "version":
    cfg["version"] = sys.argv[3]
P.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print("ok", CLS)

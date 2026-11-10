"""Furniture pass 2 (ledger 0082): write the lidar's findings into track.config.json scenery.bespoke.

- F1, the screen along the NW boundary, as three "screen" rails at the heights the lidar measured (source/lidar/f1.json;
  the pieces: source/lidar/f1_entries.json, made by source/lidar/scripts/f1_entries.py).
- Every rail / tyre wall / shed entry gets the lidar's word in its _source: the 2017-05-03 flight holds no return on any
  rail or tyre line (they postdate it), and the sheds lie outside the 45 m read: their heights stay [invented].
Idempotent (a re-run replaces the F1 entries and the notes).   python edit_config_pass2.py <airoso>"""
import json
import sys
from pathlib import Path

A = Path(sys.argv[1])
cfgp = A / "tracks/milford-road-course-lm/track.config.json"
cfg = json.loads(cfgp.read_text(encoding="utf-8"))
lid = A / "tracks/milford-road-course-lm/source/lidar"
counts = json.loads((lid / "sumitems.json").read_text(encoding="utf-8"))
pieces = json.loads((lid / "f1_entries.json").read_text(encoding="utf-8"))
b = cfg["scenery"]["bespoke"]
NOTE = " | LIDAR (ledger 0082 pass 2): "
ID_OF = {"g1_nw_corner_outside": "G1", "g2_front_straight_east": "G2", "g3_front_straight_west": "G3", "g4_infield_esses": "G4",
         "t1_nw_hairpin_exit": "T1", "t2_esses_east_leg": "T2", "t3_s1000_apron_back": "T3"}


def per_m(i):
    c = counts[i]
    return sum(c[k][0] for k in ("0.35-0.6 on/ctl per m", "0.6-1.0 on/ctl per m", "1.0-1.6 on/ctl per m"))


rails = [r for r in b["rails"] if r.get("kind") != "screen"]
for r in rails:
    i = ID_OF[r["key"]]
    r["_source"] = r["_source"].split(NOTE)[0] + NOTE + (
        f"the 3DEP flight of 2017-05-03 (source/lidar/) holds {per_m(i):.2f} returns per metre 0.35-1.6 m over the ground within"
        " 1 m of this line (a W-beam or a tyre stack would hold ~0.5-1.0 / m at the 1.4-2.9 ground returns / m2 there; the F1"
        " screen 3.1 / m): nothing stood here in May 2017, five years before the NAIP that shows it. The height is NOT"
        " measurable from it and stays [invented]")
LEN = {"ne": "NE", "step": "step", "sw": "SW"}
for p in pieces:
    rails.append({
        "key": f"f1_nw_screen_{p['tag']}", "kind": "screen", "auto": True, "height_m": p["height_m"],
        "polyline_lonlat": p["polyline_lonlat"],
        "_source": (f"source/lidar/f1.json F1 ({LEN[p['tag']]} piece, along {p['a'][0]:.0f}-{p['a'][1]:.0f} m of the 197 m the read"
                    f" covers): the line fitted through the structure's own returns every 4 m (3-point mean), off the 3DEP flight"
                    f" of 2017-05-03; height {p['height_m']} m = the median of {p['bins']} bins' p90 top over the lidar ground"
                    f" (range {p['top_p90_range'][0]}-{p['top_p90_range'][1]} m) [measured]; a thin (plan sd 0.39 m), opaque"
                    " (93 % single-pulse tops, face returns), level-topped structure, light grey on NAIP 2022: a screen wall /"
                    " screened fence, not a hedge. Panel 4.0 m and thickness 0.20 m [invented]. Beyond the read (the NE"
                    " ~60 m, 45-74 m off the edge) and SW of the trees: not built"),
    })
b["rails"] = rails
b["_rails_doc"] = ("ledger 0082 pass 1: the W-beam (kind wbeam) and tyre walls (kind tyres) on the lines NAIP 2022 shows (source/furniture/"
                   "README.md); auto: a post or module that would stand on a road or off the ground is left out. Pass 2: F1 (kind"
                   " screen) on the line and at the heights the lidar measured (source/lidar/README.md); the 2017 lidar predates the"
                   " rails and tyre walls, whose heights stay [invented]")
for blk in b["blocks"]:
    if blk["key"].startswith("pad_shed"):
        blk["_source"] = blk["_source"].split(NOTE)[0] + NOTE + (
            "207-257 m from the lap, outside the approved 45 m read: the height stays [invented]")
cfgp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print("rails:", [(r["key"], r["kind"], r.get("height_m")) for r in rails])

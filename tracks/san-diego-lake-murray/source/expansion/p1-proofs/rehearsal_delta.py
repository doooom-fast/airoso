"""Ledger 0054 P1 step 5: the weld rehearsal's configuration delta, applied to / removed from airoso's
tracks/san-diego-lake-murray/{track.config.json, signs.json} around ONE scratch run of tools/ship_sd.sh:

    python rehearsal_delta.py apply  <airoso>      # writes <track>/.p1-rehearsal.bak/ first
    SHIP_PROJ=<scratch copy of the workshop project> AIROSO=<airoso> bash tools/ship_sd.sh --no-install
    python rehearsal_delta.py restore <airoso>     # puts both files back byte for byte

The delta (the committed config keeps `north` HELD until P3; this is what P3 turns on for the welds):
  route.route_connectors.authored_take {"north": ["W1", "W5"]}   the two weld stubs of data/expansion.north.json
                                                                  become connectors (tools/route_connectors.py)
  race.swept_mouths ["north_"]                                    their mouths declared where their swept edges
                                                                  open the loop edge, policy per vertex (A7 split)
  route.weld_exact_deck ["north_"]                                the weld reads the loop deck off its triangles
                                                                  (the J1 corner's fanned outer edge)
  race.kerbs.trims += apex 1514 / 2319 outside, drop             A7: the two outside kerbs inside the openings
  signs.json corners M3 / M4 skip                                 A7: both arrows stand in the new openings. Until P4
                                                                  (adapted author_signs_blend writes plates into the
                                                                  race files) a sign can only ship in the road kn5
                                                                  every layout loads, so the rehearsal has them in
                                                                  NONE of the three layouts (not "Free Roam only")
P1 fix round (2026-10-14):
  route.aprons {"AP1": "data/expansion.north.json"}               J1's R 30 return as an authored apron
                                                                  (tools/author_aprons_blend.py): the opening now runs
                                                                  to v1527, the A5 extent
  route.trim_blend_grade_cap ["north_"]                           the two stubs' blends onto the loop deck lengthened
                                                                  until they stay within route_connectors' 11 % cap
                                                                  (A6; Waring fell 14.8 % in 30 m: the loop stands
                                                                  1.44 m over 3DEP at J1)
  route.mouth_fill ["north_"]                                     the two stubs' strips over the loop's pavement
                                                                  replaced by one piece from the loop's own edge (no
                                                                  road sheet within 2 cm over another; J5 overlapped
                                                                  the loop's outer lane by up to 2.55 m)
  drive_test.fold_fan_severe "verify_fold_fans"                   a severe reading on a fixed-offset path running
                                                                  backwards inside a levelled fan is judged by
                                                                  verify_fold_fans' real wheel paths (drive_test doc)
"""
import json
import shutil
import sys
from pathlib import Path

DELTA = {
    "authored_take": {"north": ["W1", "W5"]},
    "aprons": {"AP1": "data/expansion.north.json"},
    "trim_blend_grade_cap": ["north_"],
    "mouth_fill": ["north_"],
    "drive_test": {"fold_fan_severe": "verify_fold_fans"},
    "swept_mouths": ["north_"],
    "weld_exact_deck": ["north_"],
    "kerb_drops": [
        {"apex": 1514, "kind": "outside", "drop": True,
         "why": "Ledger 0054 A7: the J1 Waring opening (W1, v1514-v1526 on the outer curb) takes the whole outside of "
                "the College/Navajo corner the kerb ran along (v1507-1520); a kerb that ends at a road opening reads "
                "wrong. The inside kerb stays dropped for its own reason (above)."},
        {"apex": 2319, "kind": "outside", "drop": True,
         "why": "Ledger 0054 A7: the J5 Jackson-north opening (W5, v2312-v2322) covers the outside apex of the "
                "Navajo/Jackson corner (the kerb ran v2312-2327); only a 14 m exit stub would be left."},
    ],
    "sign_skips": {
        "M3": "Ledger 0054 A7: M3-fwd / M3-rev stand inside the new J1 Waring opening (straight on is now a real "
              "road in Free Roam). A sign ships only in the road kn5 all three layouts load, so until P4's adapted "
              "author_signs_blend writes plates into the race files this skips it in EVERY layout.",
        "M4": "Ledger 0054 A7: M4-fwd / M4-rev stand inside the new J5 Jackson-north opening. A sign ships only in the "
              "road kn5 all three layouts load, so until P4's adapted author_signs_blend writes plates into the race "
              "files this skips it in EVERY layout.",
    },
}


def main():
    cmd, airoso = sys.argv[1], Path(sys.argv[2])
    track = airoso / "tracks" / "san-diego-lake-murray"
    bak = track / ".p1-rehearsal.bak"
    files = ["track.config.json", "signs.json"]
    if cmd == "apply":
        if bak.exists():
            raise SystemExit(f"{bak} exists: restore first")
        bak.mkdir()
        for f in files:
            shutil.copy2(track / f, bak / f)
        cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
        cfg["route"]["route_connectors"]["authored_take"] = DELTA["authored_take"]
        cfg["race"]["swept_mouths"] = DELTA["swept_mouths"]
        cfg["route"]["weld_exact_deck"] = DELTA["weld_exact_deck"]
        cfg["route"]["aprons"] = DELTA["aprons"]
        cfg["route"]["trim_blend_grade_cap"] = DELTA["trim_blend_grade_cap"]
        cfg["route"]["mouth_fill"] = DELTA["mouth_fill"]
        cfg["drive_test"] = DELTA["drive_test"]
        cfg["race"]["kerbs"]["trims"] = list(cfg["race"]["kerbs"]["trims"]) + DELTA["kerb_drops"]
        (track / "track.config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        sg = json.loads((track / "signs.json").read_text(encoding="utf-8"))
        for k, why in DELTA["sign_skips"].items():
            sg["corners"][k] = dict(sg["corners"][k], skip=True, reason=why)
        (track / "signs.json").write_text(json.dumps(sg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("applied the P1 rehearsal delta; backup in", bak)
    elif cmd == "restore":
        for f in files:
            shutil.copy2(bak / f, track / f)
        shutil.rmtree(bak)
        print("restored", files)
    else:
        raise SystemExit("apply | restore")


if __name__ == "__main__":
    main()

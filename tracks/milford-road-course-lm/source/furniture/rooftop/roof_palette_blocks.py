"""Milford's MEASURED roof colours (ledger 0094 item 4): Del Mar's route (ledger 0083 pass 4, tools/plan_buildings.py
roof_palette) on the blocks this track lists by hand, where NAIP 2022 covers them.

    /path/to/venv/python source/furniture/rooftop/roof_palette_blocks.py <track-dir>        (Pillow)

Each roof wholly on source/road_wear/naip_2022_mrc.jpg (data/road_wear.json's aerial extent) takes the median pixel inside
its footprint, 2 px clear of its edge (plan_buildings.roof_colour), as one solid cell of PALETTE; its row becomes "roof":
"NAIP" with that cell's "roof_uv" and "roof_rgb" (the author stands it as ROOFTOP_NAIP_<k>, bound by texture_overrides
["ROOF"]). A roof off the photograph (pass 4's, west of it) keeps its class and says so. Rows already measured are measured
again, so a re-run reproduces the same file. Writes PALETTE and NORMAL (a flat normal map: a palette cell has no relief to
draw), edits track.config.json's inline blocks and source/furniture/pass3/blocks.json in place (json, each file's own indent).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PALETTE = "source/furniture/rooftop/roof_naip_palette.png"
NORMAL = "source/furniture/rooftop/roof_flat_normal.png"
PASS3 = "source/furniture/pass3/blocks.json"


def _load(path: Path):
    """(data, indent): the file's own indent, so a rewrite changes only the keys this script sets"""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    for ind in (2, 1, 4):
        if json.dumps(data, indent=ind, ensure_ascii=False) + "\n" == text:
            return data, ind
    raise SystemExit(f"{path}: no byte-identical json round trip at indent 1, 2 or 4")


def _dump(path: Path, data, indent):
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")


def main(track: Path, airoso: Path) -> int:
    sys.path.insert(0, str(airoso / "tools"))
    import plan_buildings as pb
    aer = json.loads((track / "data" / "road_wear.json").read_text(encoding="utf-8"))["spec"]["aerial"]
    plan = {"image": aer["image"], "bbox_lonlat": aer["bbox_lonlat"]}
    photo = pb.Photo(track, plan)
    cfg_p = track / "track.config.json"
    cfg, cfg_ind = _load(cfg_p)
    inline = [g for g in cfg["scenery"]["bespoke"]["blocks"] if not g.get("file")]
    p3_p = track / PASS3
    p3, p3_ind = _load(p3_p)
    rows = inline + p3
    for r in rows:                                     # a re-run starts from each row's class, as first planned
        if r.get("roof") == "NAIP":
            r["roof"] = r.get("_roof_class", "white")
    for r in rows:
        r.setdefault("_roof_class", r.get("roof"))
    spec = {"atlas": PALETTE, "normal": NORMAL, "_photo": "NAIP 2022-08-16, source/road_wear/naip_2022_mrc.jpg"}
    counts = pb.roof_palette(rows, photo, spec, track)
    for r in rows:
        if r.get("roof") != "NAIP":
            r.pop("_roof_class", None)
    _dump(cfg_p, cfg, cfg_ind)
    _dump(p3_p, p3, p3_ind)
    print("[roof palette]", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), Path(__file__).resolve().parents[5]))

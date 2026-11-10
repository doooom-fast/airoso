"""Milford 0.1.5 (ledger 0082 vegetation Owed 4): how much of each MEASURED grass zone the GrassFX rectangles cover.

    python grass_coverage.py <workshop or project dir> [<out.json>]

Reads <dir>/track.config.json (scenery.bespoke.grassfx_zones: the class map, its bbox, margin_m), <dir>/data/centerline.local.json
and <dir>/data/grassfx.aerial.json (tools/plan_grassfx_aerial.py's rectangles, kn5 frame: z mirrored). Every 2 m pixel of the
class map inside the plan's box (the lap +- margin_m) is a measured cell of its zone; it is COVERED when a rectangle bound to
its own look contains it, WRONG when a rectangle of another look does. The geometry is plan_grassfx_aerial's own (the same
metres per degree), so the count is what the plan wrote, not a second opinion on the frame.
"""
import json, math, sys
from pathlib import Path

import numpy as np
from PIL import Image

CODE = {"C": (0, 120, 0), "B": (200, 200, 0), "D": (0, 0, 200)}


def main():
    d = Path(sys.argv[1])
    cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
    spec = cfg["scenery"]["bespoke"]["grassfx_zones"]
    cl = json.loads((d / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    o = cl["origin"]
    xs = [p[0] for p in cl["points_xyz_m"]]; zs = [p[2] for p in cl["points_xyz_m"]]
    m = float(spec.get("margin_m", 150.0))
    x0, x1, z0, z1 = min(xs) - m, max(xs) + m, min(zs) - m, max(zs) + m
    root = d if (d / spec["image"]).exists() else Path(__file__).resolve().parents[3]
    img = np.asarray(Image.open(root / spec["image"]).convert("RGB"))
    H, W = img.shape[:2]
    Wl, S, E, N = spec["bbox_lonlat"]
    m_lat = 111320.0
    m_lon = m_lat * math.cos(math.radians(o["lat"]))
    u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H
    lon = Wl + u * (E - Wl); lat = N - v * (N - S)
    X = (lon - o["lon"]) * m_lon; Z = (lat - o["lat"]) * m_lat
    XX, ZZ = np.meshgrid(X, Z)
    inbox = (XX >= x0) & (XX <= x1) & (ZZ >= z0) & (ZZ <= z1)
    px_m2 = abs((E - Wl) / W * m_lon) * abs((N - S) / H * m_lat)
    adj = json.loads((d / "data" / "grassfx.aerial.json").read_text(encoding="utf-8"))["adjustments"]
    look = np.full((H, W), "", dtype=object)
    cover = {k: np.zeros((H, W), bool) for k in CODE}
    for a in adj:
        cx, _, cz = a["rect"]["center"]; sw, sd = a["rect"]["size"]
        z = -cz
        r = (XX >= cx - sw / 2) & (XX <= cx + sw / 2) & (ZZ >= z - sd / 2) & (ZZ <= z + sd / 2)
        if a["map"] in cover:
            cover[a["map"]] |= r
    out = {"rectangles": len(adj), "by_look": {k: sum(1 for a in adj if a["map"] == k) for k in CODE}, "zones": {}}
    for k, rgb in CODE.items():
        cls = (img == np.array(rgb, np.uint8)).all(-1) & inbox
        own = cls & cover[k]
        other = cls & np.any([cover[q] for q in CODE if q != k], axis=0)
        out["zones"][k] = {"measured_ha": round(float(cls.sum()) * px_m2 / 1e4, 2),
                           "covered_ha": round(float(own.sum()) * px_m2 / 1e4, 2),
                           "covered_pct": round(100 * float(own.sum()) / max(1, int(cls.sum())), 1),
                           "under_another_look_ha": round(float(other.sum()) * px_m2 / 1e4, 2)}
    for k in CODE:
        spill = cover[k] & inbox & ~(img == np.array(CODE[k], np.uint8)).all(-1)
        out["zones"][k]["rect_area_off_zone_ha"] = round(float(spill.sum()) * px_m2 / 1e4, 2)
    print(json.dumps(out, indent=1))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

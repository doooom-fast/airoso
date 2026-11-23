"""Road wear's aerial over the Full layout's north loop (ledger 0097 round 4, item 3): the 0.3 m crop mosaicked with the
z18 photos of the same NAIP item, so the north loop's tone comes from a photo and not from the bake's flat fill.

    python -I make_aerial_mosaic.py <repo>      (numpy + Pillow; writes naip_2023_hp_mosaic.png + .json beside itself)

  lattice   the 0.3 m crop's own (naip_2023_030_hp.png, EPSG:4326, corners in its .json): the same W, E, S and pixel size,
            carried NORTH by whole rows until the north loop's top + MARGIN_M is inside, so every pixel of the crop is
            copied unchanged into the mosaic's bottom rows (the West lap reads the very pixels it read before)
  the rest  the rows above the crop: the z18 photos (tracks/high-plains/source/naip_2023_hp_z18.png and, above it,
            source/full/naip_2023_hp_north_z18.png: web-mercator tiles of the SAME NAIP item, 0.46 m a pixel here, read as
            one mosaic by measure_north.z18_reader), bilinear at each pixel's centre, within CORRIDOR_M of the north loop's
            line (source/full/connectors.full.json); black (0, 0, 0) elsewhere, which no road reads
  registered  the z18 photos against the crop, measured where both hold a pixel (REG_BOX_LONLAT, the fork and the merge
            and the loop's first and last metres): the (dx, dy) shift of the z18 read that best correlates its luminance with
            the crop's (coarse COARSE_M then FINE_M steps within REACH_M), and the two photos' luminance ratio over that box
            (reported, not applied: one item, one radiometry)
The bake (tools/road_wear_blend.py) and its gate (tools/road_wear_check.py) read it as road_wear.aerial, unchanged: one
north-up lon/lat image and its box. Every UPPER-CASE number is [invented] extent / search tuning; the photos are the
measurement (USDA NAIP 2023-09-28, co_m_3910317_ne_13_030_20230928_20240104, public domain).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
MARGIN_M = 40.0           # past the north loop's northernmost point
CORRIDOR_M = 40.0         # z18 pixels copied within this of the north loop's line (the bake reads at most ~13 m off a road)
REG_BOX_LONLAT = (-103.9010, 39.7357, -103.8975, 39.7368)   # W, S, E, N: the crop's top edge over the fork and the merge
REACH_M, COARSE_M, FINE_M = 2.0, 0.5, 0.1
OUT = "naip_2023_hp_mosaic"


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def build(repo: Path):
    P = repo / "tracks" / "high-plains-lm"
    sys.path.insert(0, str(P / "source" / "full"))
    import measure_north as mn    # noqa: E402  (the z18 mosaic reader round 3 measured the north loop with)
    meta = json.loads((HERE / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    W, N, E, S = meta["corners"]
    crop = np.asarray(Image.open(HERE / "naip_2023_030_hp.png").convert("RGB"))
    h, w, _ = crop.shape
    dlon, dlat = (E - W) / w, (N - S) / h
    origin = json.loads((P / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["origin"]
    mlon, mlat = mpd(origin["lat"])
    z18, _north = mn.z18_reader(repo)
    conn = json.loads((P / "source" / "full" / "connectors.full.json").read_text(encoding="utf-8"))["connectors"][0]
    line = np.array([[origin["lon"] + p[0] / mlon, origin["lat"] + p[2] / mlat] for p in conn["points_xyz_m"]])

    # 1. the z18 photos registered against the crop where both hold a pixel
    bw, bs, be, bn = REG_BOX_LONLAT
    c0, c1 = int((bw - W) / dlon), int((be - W) / dlon)
    r0, r1 = int((N - bn) / dlat), int((N - bs) / dlat)
    rr, cc = np.mgrid[r0:r1, c0:c1]
    lon = W + (cc + 0.5) * dlon
    lat = N - (rr + 0.5) * dlat
    C = crop[r0:r1, c0:c1].astype(np.float64).mean(axis=2)

    def ncc(dx, dy):
        Z = np.nanmean(z18(lon + dx / mlon, lat + dy / mlat), axis=-1)
        ok = np.isfinite(Z)
        a = C[ok] - C[ok].mean()
        b = Z[ok] - Z[ok].mean()
        return float((a * b).sum() / math.sqrt((a * a).sum() * (b * b).sum())), Z, ok
    best = (-2.0, 0.0, 0.0)
    for dx in np.arange(-REACH_M, REACH_M + 1e-9, COARSE_M):
        for dy in np.arange(-REACH_M, REACH_M + 1e-9, COARSE_M):
            r = ncc(dx, dy)[0]
            if r > best[0]:
                best = (r, float(dx), float(dy))
    bx, by = best[1], best[2]
    for dx in np.arange(bx - COARSE_M, bx + COARSE_M + 1e-9, FINE_M):
        for dy in np.arange(by - COARSE_M, by + COARSE_M + 1e-9, FINE_M):
            r = ncc(dx, dy)[0]
            if r > best[0]:
                best = (r, float(dx), float(dy))
    r_at0 = ncc(0.0, 0.0)[0]
    rb, sx, sy = best
    _r, Z, ok = ncc(sx, sy)
    gain = float(np.median(Z[ok]) / np.median(C[ok]))

    # 2. the lattice carried north
    top = float(line[:, 1].max()) + MARGIN_M / mlat
    k = int(math.ceil((top - N) / dlat))
    Nm = N + k * dlat
    out = np.zeros((k + h, w, 3), dtype=np.uint8)
    out[k:] = crop
    # 3. the rows above the crop from the z18 photos, within CORRIDOR_M of the north loop
    lon_c = W + (np.arange(w) + 0.5) * dlon
    lx = (line[:, 0] - origin["lon"]) * mlon
    ly = (line[:, 1] - origin["lat"]) * mlat
    cols = np.nonzero((lon_c >= line[:, 0].min() - CORRIDOR_M / mlon) & (lon_c <= line[:, 0].max() + CORRIDOR_M / mlon))[0]
    filled = 0
    for r in range(k):
        la = Nm - (r + 0.5) * dlat
        y = (la - origin["lat"]) * mlat
        near = np.abs(ly - y) <= CORRIDOR_M
        if not near.any():
            continue
        x = (lon_c[cols] - origin["lon"]) * mlon
        d = np.min(np.hypot(x[:, None] - lx[near][None, :], y - ly[near][None, :]), axis=1)
        use = cols[d <= CORRIDOR_M]
        if not len(use):
            continue
        v = z18(lon_c[use] + sx / mlon, np.full(len(use), la) + sy / mlat)
        good = np.isfinite(v).all(axis=1)
        out[r, use[good]] = np.clip(np.round(v[good]), 0, 255).astype(np.uint8)
        filled += int(good.sum())
    rec = {"_doc": "ledger 0097 round 4 (make_aerial_mosaic.py): road_wear.aerial over both layouts, the 0.3 m crop "
                   "(naip_2023_030_hp.png, its pixels unchanged in the bottom rows) carried north on its own lattice, the rows "
                   "above it from the z18 photos of the same NAIP item (0.46 m, bilinear, registered) within CORRIDOR_M of the "
                   "north loop; black elsewhere",
           "item": meta.get("item"), "datetime": meta.get("datetime"),
           "corners": [W, Nm, E, S], "w": w, "h": k + h, "m_per_px": meta.get("m_per_px"),
           "crop_rows": [k, k + h], "z18_px_filled": filled,
           "registration": {"box_lonlat": list(REG_BOX_LONLAT), "z18_shift_m": [round(sx, 2), round(sy, 2)],
                            "ncc_at_0": round(r_at0, 4), "ncc_best": round(rb, 4),
                            "lum_ratio_z18_over_crop": round(gain, 4), "applied": "shift only"},
           "params": {k_: v_ for k_, v_ in globals().items() if k_.isupper() and k_ not in ("OUT", "HERE")},
           "source": "USDA NAIP 2023-09-28 (public domain): the Planetary Computer 0.3 m crop and its z18 web-mercator tiles"}
    return out, rec


if __name__ == "__main__":
    repo = Path(sys.argv[1]).resolve()
    img, rec = build(repo)
    Image.fromarray(img).save(HERE / (OUT + ".png"), optimize=True)
    (HERE / (OUT + ".json")).write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(f"[mosaic] {rec['w']} x {rec['h']} px, corners {rec['corners']}, z18 px {rec['z18_px_filled']}, "
          f"registration {rec['registration']}")

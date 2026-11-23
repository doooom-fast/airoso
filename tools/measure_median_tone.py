"""The colour of a raised median island on the NAIP z18 mosaic: mean, median, p10 / p90 per channel, and the ratio to a
texture's own mean, so a builder can match a downloaded texture's tone to a measured number instead of a guess.

Written for Mission Gorge Rd's terracotta median on Lake Murray (MD11 / MD13 in data/expansion.north.json) and the
CC0 paver pair `assets/textures/terracotta_paver_*` (see assets/textures/terracotta_paver.md for the numbers).

    python -I tools/measure_median_tone.py --mosaic <naip_*_z18.jpg> [--georef <.georef.json>] \
        [--expansion tracks/san-diego-lake-murray/data/expansion.north.json] [--islands MD11,MD13] \
        [--texture assets/textures/terracotta_paver_diffuse.jpg] [--out <json>] [--overlay <dir>]

HOW
  * The islands are the `medians[].polygon_xz` rings of the expansion intermediate (local ENU metres, x east, z north,
    about its `frame.origin`). A ring goes to mosaic pixels exactly as tools/naip_edge.py's Naip.px does: the WGS84
    metres-per-degree series of scripts/geometry/projection.py at the origin's latitude, then Web Mercator tiles of the
    georef's z / x0 / y0. Pixel (i, j) covers [i, i+1) x [j, j+1); a pixel is sampled when its centre is inside.
  * INSET_M [invented]: the ring is shrunk by one NAIP pixel (0.5 m) before sampling, so no sampled pixel straddles
    the curb or the asphalt beside it.
  * Canopy [invented]: G - R > CANOPY_G_MINUS_R (5 levels). Measured on NAIP 2022 (2026-11-23): the asphalt beside
    Mission Gorge's median reads G - R +1.6..+3.7 (bin means 3.5-6 m from the centre line: both sides of two MD13
    stretches, and south-east of MD11), MD13's lit pixels
    (luminance > 110) G - R -29 / -20 / -7 (p10 / p50 / p90), and the pixels the rule takes inside MD13's ring
    G - R +6 / +10 / +18 at luminance 54 / 64 / 103: the median's shrubs and tree crowns. The 5 is a margin above
    the asphalt's own value, not a measured split.
  * Shadow: luminance (Rec. 709, as scripts/aerial/road_wear.py) under SHADOW_SHARE of the island's own median
    luminance after the canopy cut. 0.72 is road_wear's tone.shadow_lum, measured on Milford's NAIP asphalt; it was
    not measured on terracotta, so here it is [invented].
  * Both masks grow by one pixel (8-neighbour), road_wear's own rule ("a shadow's edge is a mixed pixel that meets
    neither rule"), within the island's full ring.
  * The texture's mean is over every pixel of the file. Ratios are island / texture per channel, on the 8-bit sRGB
    values and on linear light (the sRGB curve undone per pixel before averaging). NAIP is a sensor product, not
    albedo: the ratio matches the texture to how the 2022 photo shows the median, which is the look the aerial-led
    builds compare against.

Numpy, Pillow and shapely only (the repo venv). Reads only; writes --out / --overlay when given.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from PIL import Image

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

EXPANSION = AIROSO / "tracks/san-diego-lake-murray/data/expansion.north.json"
INSET_M = 0.5                # [invented] one NAIP pixel off the island's ring
CANOPY_G_MINUS_R = 5.0       # [invented] green over red by more than this: canopy
SHADOW_SHARE = 0.72          # road_wear tone.shadow_lum (measured on asphalt, Milford); [invented] on terracotta
GROW_PX = 1                  # road_wear's own one-pixel growth of the shadow / paint masks


class Mosaic:
    def __init__(self, image: Path, georef: Path, origin: dict):
        g = json.loads(georef.read_text(encoding="utf-8"))
        with open(image, "rb") as fh:
            if fh.read(40).startswith(b"version https://git-lfs"):
                raise SystemExit(f"{image} is a Git LFS pointer: pull it, or pass the real file")
        Image.MAX_IMAGE_PIXELS = None
        self.a = np.asarray(Image.open(image).convert("RGB"))
        self.z, self.x0, self.y0 = int(g["z"]), int(g["x0"]), int(g["y0"])
        self.lat0, self.lon0 = float(origin["lat"]), float(origin["lon"])
        self.m_lon, self.m_lat = _meters_per_degree(self.lat0)
        self.georef = g

    def px(self, E, N):
        """tools/naip_edge.py Naip.px: local (E, N) metres -> mosaic pixel coordinates (u right, v down)."""
        lon = self.lon0 + np.asarray(E, dtype=float) / self.m_lon
        lat = np.radians(self.lat0 + np.asarray(N, dtype=float) / self.m_lat)
        tx = (lon + 180.0) / 360.0 * 2 ** self.z
        ty = (1.0 - np.log(np.tan(lat) + 1.0 / np.cos(lat)) / math.pi) / 2.0 * 2 ** self.z
        return (tx - self.x0) * 256.0, (ty - self.y0) * 256.0

    def to_px_poly(self, poly):
        def ring(coords):
            c = np.asarray(coords)
            u, v = self.px(c[:, 0], c[:, 1])
            return np.column_stack([u, v])
        parts = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
        return shapely.MultiPolygon([shapely.Polygon(ring(p.exterior.coords), [ring(h.coords) for h in p.interiors])
                                     for p in parts if not p.is_empty])


def lum(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def srgb_to_linear(v):
    v = np.asarray(v, dtype=np.float64) / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def grow(mask, n):
    out = mask.copy()
    for _ in range(n):
        p = np.pad(out, 1)
        out = np.zeros_like(out)
        for dj in (0, 1, 2):
            for di in (0, 1, 2):
                out |= p[dj:dj + mask.shape[0], di:di + mask.shape[1]]
    return out


def stats(rgb):
    r = lambda x: [round(float(v), 1) for v in x]  # noqa: E731
    return {"mean": r(rgb.mean(axis=0)), "median": r(np.median(rgb, axis=0)), "p10": r(np.percentile(rgb, 10, axis=0)),
            "p90": r(np.percentile(rgb, 90, axis=0)), "std": r(rgb.std(axis=0)),
            "mean_linear": [round(float(v), 5) for v in srgb_to_linear(rgb).mean(axis=0)]}


def measure_island(mos: Mosaic, med: dict, overlay: Path | None = None) -> dict:
    ring = shapely.Polygon(med["polygon_xz"])
    if not ring.is_valid:
        ring = shapely.make_valid(ring)
    inset = ring.buffer(-INSET_M)
    full_px, inset_px = mos.to_px_poly(ring), mos.to_px_poly(inset)
    u0, v0, u1, v1 = full_px.bounds
    i0, j0 = int(math.floor(u0)) - 2, int(math.floor(v0)) - 2
    i1, j1 = int(math.ceil(u1)) + 2, int(math.ceil(v1)) + 2
    I, J = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1))
    in_full = shapely.contains_xy(full_px, I + 0.5, J + 0.5)
    in_inset = shapely.contains_xy(inset_px, I + 0.5, J + 0.5) & in_full
    rgb = mos.a[j0:j1, i0:i1].astype(np.float64)
    canopy = in_full & ((rgb[..., 1] - rgb[..., 0]) > CANOPY_G_MINUS_R)
    canopy = grow(canopy, GROW_PX) & in_full
    L = lum(rgb)
    ref = float(np.median(L[in_inset & ~canopy]))
    shadow = in_full & ~canopy & (L < SHADOW_SHARE * ref)
    shadow = grow(shadow, GROW_PX) & in_full & ~canopy
    keep = in_inset & ~canopy & ~shadow
    out = {"id": med["id"], "piece": med["piece"], "type": med["type"], "s": [med["s_from"], med["s_to"]],
           "declared_width_m": med["width_m"], "area_m2": round(ring.area, 1), "inset_area_m2": round(inset.area, 1),
           "px_in_ring": int(in_full.sum()), "px_in_inset": int(in_inset.sum()),
           "px_canopy": int((in_inset & canopy).sum()), "px_shadow": int((in_inset & shadow).sum()),
           "px_kept": int(keep.sum()), "shadow_ref_lum": round(ref, 1),
           "inset_unmasked": stats(rgb[in_inset]), "kept": stats(rgb[keep])}
    if overlay is not None:
        overlay.mkdir(parents=True, exist_ok=True)
        vis = rgb.copy()
        vis[canopy & in_inset] = (0, 255, 0)
        vis[shadow & in_inset] = (0, 0, 255)
        vis[in_full & ~in_inset] = vis[in_full & ~in_inset] * 0.5 + np.array([255, 255, 0]) * 0.5
        side = np.concatenate([rgb, vis], axis=0 if rgb.shape[1] > rgb.shape[0] else 1).astype(np.uint8)
        Image.fromarray(side).resize((side.shape[1] * 3, side.shape[0] * 3), Image.NEAREST).save(
            overlay / f"{med['id']}_masks.png")
    return out


def texture_stats(path: Path) -> dict:
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64).reshape(-1, 3)
    s = stats(a)
    s.update({"file": path.name, "size_px": list(Image.open(path).size),
              "md5": hashlib.md5(path.read_bytes()).hexdigest()})
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mosaic", required=True, type=Path)
    ap.add_argument("--georef", type=Path)
    ap.add_argument("--expansion", type=Path, default=EXPANSION)
    ap.add_argument("--islands", default="MD11,MD13")
    ap.add_argument("--texture", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--overlay", type=Path)
    a = ap.parse_args(argv)
    georef = a.georef or a.mosaic.with_suffix(".georef.json")
    exp = json.loads(a.expansion.read_text(encoding="utf-8"))
    mos = Mosaic(a.mosaic, georef, exp["frame"]["origin"])
    meds = {m["id"]: m for m in exp["medians"]}
    rep = {"mosaic": {"file": a.mosaic.name, "sha256": hashlib.sha256(a.mosaic.read_bytes()).hexdigest(),
                      "item": mos.georef.get("item"), "z": mos.z, "x0": mos.x0, "y0": mos.y0},
           "frame_origin": exp["frame"]["origin"],
           "rules": {"inset_m": INSET_M, "canopy_g_minus_r": CANOPY_G_MINUS_R, "shadow_share": SHADOW_SHARE,
                     "grow_px": GROW_PX, "invented": ["inset_m", "canopy_g_minus_r", "shadow_share (on terracotta)"]},
           "islands": [measure_island(mos, meds[k], a.overlay) for k in a.islands.split(",")]}
    if a.texture:
        t = texture_stats(a.texture)
        rep["texture"] = t
        for isl in rep["islands"]:
            k = isl["kept"]
            isl["ratio_to_texture"] = {
                "srgb_mean": [round(x / y, 3) for x, y in zip(k["mean"], t["mean"])],
                "srgb_median": [round(x / y, 3) for x, y in zip(k["median"], t["median"])],
                "linear_mean": [round(x / y, 3) for x, y in zip(k["mean_linear"], t["mean_linear"])]}
    text = json.dumps(rep, indent=1)
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

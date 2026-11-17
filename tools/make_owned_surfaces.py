"""Owned (generated, CC0) replacements for the borrowed surface textures: the road's detail asphalt and the concrete.

Kevin, 2026-11-07: "sampling the entire road's texture from aerial data ... instead of a repeating pattern that's not
realistic"; 2026-11-16: "see what you can set off to build overnight ... possibly textures for roads and or buildings".
Road wear (ledger 0084, scripts/aerial/road_wear.py) already lays the aerial's tone and the rubber under the road as the
MACRO layer. The DETAIL layer on top of it, on the prep's 4 m planar grid (UV_TILE 4.0), is still
asphalt_cracked_diffuse/_normal.jpg, mined from LA Canyons and personal-use only (assets/textures/SOURCES.txt). Its
alligator cracks are big, dark, one-of-a-kind shapes, so the same crack shows every 4 m. And every curb, sidewalk,
parapet, pier and building that binds building_diffuse.jpg wears Hamburg's board-formed wall concrete (tie holes on a
grid), also mined.

This generator paints replacements from seeded noise and polygons (Pillow only, no numpy, no photo, no third-party
pixel), so the result is ours and CC0. Same seed -> same bytes under the same Pillow.

    PYTHONUTF8=1 python tools/make_owned_surfaces.py --out-dir DIR            # write all pairs
    PYTHONUTF8=1 python tools/make_owned_surfaces.py --out-dir DIR --check    # exit 1 if DIR's files differ
    PYTHONUTF8=1 python tools/make_owned_surfaces.py --out-dir DIR --only asphalt_dense

THE PAIRS (all tile seamlessly in u and v; one tile = TILE_M of ground, the prep's planar grid):

  asphalt_dense_diffuse.jpg / _normal.jpg    2048 px, ~1.95 mm per pixel. A weathered dense-graded hot-mix surface: dark
                                             oxidised binder and fines, with the coarse aggregate showing through.
                                             MEANT FOR the 1ROAD / 1RUNOFF / HIGHWAY detail slot.
  concrete_plain_diffuse.jpg / _normal.jpg   1024 px, ~3.9 mm per pixel. Plain cast concrete, no joints or tie holes
                                             (the planar grid would put them anywhere). MEANT FOR CURB, SIDEWALK,
                                             1KERB_SIDEWALK, HWYSTRUCT, BRIDGESTRUCT, 1WALL_GUARD, BUILDING.
  concrete_aged_diffuse.jpg / _normal.jpg    1024 px. The same concrete weathered: stained, exposed fines. MEANT FOR
                                             WAREHOUSE.

Nothing binds them yet: swapping a pbr.TEXTURES row changes every track's look on its next build, and that is
Kevin's call (.claude/skills/bespoke-assets section 1).

WHAT IS MEASURED AND WHAT IS NOT
  * Mean colour, per channel, is the mean of the file each pair would replace (measured 2026-11-16 on the G10:
    asphalt_cracked_diffuse 0.3806 / 0.3871 / 0.3962, building_diffuse 0.5286 / 0.5156 / 0.4891, warehouse_diffuse
    0.3826 / 0.3710 / 0.3358). Road wear divides the detail by m0 so that "macro x detail' at the median road texel is
    today's look exactly" (road_wear.py); keeping the mean keeps that calibration.
  * Relief strength is tuned to the replaced normal map's tilt (measured: asphalt_cracked_normal p50 12.9 deg,
    p90 23.5; building_normal p50 3.5, p90 8.9; warehouse_normal p50 11.7, p90 36.1).
  * Aggregate sizes follow the control points of a 12.5 mm nominal-maximum dense-graded mix (AASHTO M 323 /
    Superpave 12.5 mm: 100 % passing 19 mm, 90-100 % passing 12.5 mm, at most 90 % passing 9.5 mm, 28-58 % passing
    2.36 mm), the common surface course in Colorado and California. A plane through the mix shows each size class in
    about its volume share; how much of that share shows on a worn surface (STONE_SHOW) is [invented].
  * Everything else (stone tones, exposure, pores, mottling) is [invented], to be tuned by eye from stills and Kevin's
    drive, like make_kerb_texture.py's look numbers.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

AIROSO = Path(__file__).resolve().parents[1]
OUT_DIR = AIROSO / "assets" / "textures"
TILE_M = 4.0                 # the kn5 prep's planar UV tile (engine-july UV_TILE)
JPEG_Q = 90
MAX_BYTES = 4_000_000        # per file; asphalt_cracked_diffuse.jpg, the file it replaces, is 2.37 MB

# means of the files these replace (measured, see the docstring)
MEAN_ASPHALT = (0.3806, 0.3871, 0.3962)
MEAN_CONCRETE = (0.5286, 0.5156, 0.4891)
MEAN_AGED = (0.3826, 0.3710, 0.3358)

# AASHTO M 323 12.5 mm NMAS: (sieve range mm, share of the mix's volume in that range) - a mid-band gradation:
# 95 % passing 12.5, 80 % passing 9.5, 55 % passing 4.75, 40 % passing 2.36
GRADATION = ((12.5, 19.0, 0.05), (9.5, 12.5, 0.15), (4.75, 9.5, 0.25), (2.36, 4.75, 0.15))
STONE_SHOW = 0.62            # [invented] fraction of a class's volume share that reads as stone on a worn surface
SECTION = (0.55, 0.95)       # [invented] a cut stone shows 55-95 % of its sieve size across
SEEDS = {"asphalt_dense": 84, "concrete_plain": 85, "concrete_aged": 86}


# ---------------------------------------------------------------- helpers (all periodic in u and v)

def _clamp(v):
    return max(0, min(255, int(round(v))))


def _pad(im, m):
    """im with an m-pixel border copied from the opposite edges (the torus unrolled)"""
    w, h = im.size
    out = Image.new(im.mode, (w + 2 * m, h + 2 * m))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out.paste(im, (m + dx * w, m + dy * h))
    return out


def _wrapf(im, f, m=16):
    """apply filter f as if im tiled forever: pad from the opposite edges, filter, crop the middle"""
    w, h = im.size
    return f(_pad(im, m)).crop((m, m, m + w, m + h))


def _noise(rng, cells, n, blur=0.0):
    """smooth value noise: a cells x cells grid of seeded bytes upscaled bicubic to n x n, periodic (cells divides n)"""
    assert n % cells == 0
    k = n // cells
    lo = Image.frombytes("L", (cells, cells), rng.randbytes(cells * cells))
    big = _pad(lo, 2).resize(((cells + 4) * k, (cells + 4) * k), Image.BICUBIC)
    big = big.crop((2 * k, 2 * k, 2 * k + n, 2 * k + n))
    if blur > 0:
        big = _wrapf(big, lambda im: im.filter(ImageFilter.GaussianBlur(blur)), int(3 * blur) + 2)
    return big


def _white(rng, n, blur=0.0):
    """per-pixel seeded noise, optionally softened (periodic)"""
    im = Image.frombytes("L", (n, n), rng.randbytes(n * n))
    if blur > 0:
        im = _wrapf(im, lambda x: x.filter(ImageFilter.GaussianBlur(blur)), int(3 * blur) + 2)
    return im


def _levels(im, lo, hi, out_lo=0, out_hi=255):
    span = max(1e-6, hi - lo)
    lut = [_clamp(out_lo + (out_hi - out_lo) * min(1.0, max(0.0, (p - lo) / span))) for p in range(256)]
    return im.point(lut)


def _percentile(im, frac):
    hist = im.histogram()
    total, acc = sum(hist), 0
    for v, c in enumerate(hist):
        acc += c
        if acc >= frac * total:
            return v
    return 255


def _stretch(im):
    """an L noise image stretched so its p1..p99 spans 0..255 (bicubic noise is narrow around 128)"""
    return _levels(im, _percentile(im, 0.01), _percentile(im, 0.99))


def _mod(base, grey, amp):
    """base (RGB or L) times (1 + amp * (grey - 128) / 128): a +-amp modulation by a grey field"""
    lut = [_clamp(255 * min(1.0, max(0.0, 0.5 * (1 + amp * (p - 128) / 128)))) for p in range(256)]
    g = grey.point(lut)                                   # 0.5 * factor, stored so 255 = 2x
    chans = base.split() if base.mode == "RGB" else (base,)
    out = [ImageChops.multiply(c, g).point(lambda p: min(255, p * 2)) for c in chans]
    return Image.merge("RGB", out) if base.mode == "RGB" else out[0]


def _mean_rgb(im):
    st = [sum(i * c for i, c in enumerate(ch.histogram())) / (im.size[0] * im.size[1]) for ch in im.split()]
    return tuple(v / 255.0 for v in st)


def _match_mean(im, target, rounds=4):
    """per-channel gain so the image's mean is the target (0..1), iterated because the top clips"""
    for _ in range(rounds):
        have = _mean_rgb(im)
        chans = []
        for ch, h, t in zip(im.split(), have, target):
            g = t / max(1e-6, h)
            chans.append(ch.point([_clamp(p * g) for p in range(256)]))
        im = Image.merge("RGB", chans)
    return im


# OpenGL tangent-space normal from a height picture (bright = high), exactly as tools/make_kerb_texture.py: PIL's
# ImageFilter.Kernel flips the kernel vertically, so SOBEL_GY is written upside down from the correlation it performs
# (ledger 0053; tests/tools/test_make_kerb_texture.py pins the convention on a synthetic ramp)
SOBEL_GX = (1, 0, -1, 2, 0, -2, 1, 0, -1)
SOBEL_GY = (1, 2, 1, 0, 0, 0, -1, -2, -1)


def _normal(hgt, strength):
    """RGB OpenGL normal map of hgt; `strength` is the Sobel divisor (lower = steeper). B is set from R and G so the
    vector has unit length (the kerb's constant 250 is fine for its gentle relief, not for stones)"""
    kx = ImageFilter.Kernel((3, 3), SOBEL_GX, scale=strength, offset=128)
    ky = ImageFilter.Kernel((3, 3), SOBEL_GY, scale=strength, offset=128)
    r = _wrapf(hgt, lambda im: im.filter(kx), 2)
    g = _wrapf(hgt, lambda im: im.filter(ky), 2)
    # B = 127.5 + 127.5 * sqrt(1 - x^2 - y^2), x = (R - 127.5) / 127.5. Without numpy: square R and G through
    # lookup tables into "L" (x^2 * 127.5), add them, and map the sum through the sqrt table
    r2 = r.point([_clamp(((p - 127.5) / 127.5) ** 2 * 127.5) for p in range(256)])
    g2 = g.point([_clamp(((p - 127.5) / 127.5) ** 2 * 127.5) for p in range(256)])
    ss = ImageChops.add(r2, g2)                                           # (x^2 + y^2) * 127.5, clipped at 255
    b = ss.point([_clamp(127.5 + 127.5 * math.sqrt(max(0.0, 1.0 - p / 127.5))) for p in range(256)])
    return Image.merge("RGB", (r, g, b))


def _polygon(rng, cx, cy, r):
    """an irregular crushed-stone outline round (cx, cy), radius ~r px"""
    k = rng.randint(5, 8)
    a0 = rng.random() * math.tau
    pts = []
    for i in range(k):
        a = a0 + math.tau * (i + rng.uniform(-0.28, 0.28)) / k
        rr = r * rng.uniform(0.72, 1.12)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _draw_wrapped(draws, pts, r, n, fills):
    """draw polygon pts on every ImageDraw in draws (with its fill), plus its copies across the edges it touches"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    offs_x = [0] + ([n] if min(xs) < 0 else []) + ([-n] if max(xs) >= n else [])
    offs_y = [0] + ([n] if min(ys) < 0 else []) + ([-n] if max(ys) >= n else [])
    for ox in offs_x:
        for oy in offs_y:
            q = [(x + ox, y + oy) for x, y in pts]
            for d, f in zip(draws, fills):
                d.polygon(q, fill=f)


# ---------------------------------------------------------------- the surfaces

def asphalt_dense(scale=1.0, seed=SEEDS["asphalt_dense"]):
    """(diffuse RGB, normal RGB, height L): weathered dense-graded asphalt, one tile = TILE_M"""
    n = int(round(2048 * scale))
    px_mm = n / (TILE_M * 1000.0)
    rng = random.Random(seed)

    # 1. binder and fines: dark grey, mottled at 3-12 cm, grainy at the pixel (sand, fines, pores)
    mott_a = _stretch(_noise(rng, 32, n))                 # 12.5 cm cells
    mott_b = _stretch(_noise(rng, 128, n))                # 3.1 cm cells
    sand = _white(rng, n, blur=0.55 * scale + 0.15)
    binder = Image.new("L", (n, n), BINDER)               # [invented] oxidised binder + fines, before the mean match
    binder = _mod(binder, mott_a, 0.06)
    binder = _mod(binder, mott_b, 0.07)
    binder = _mod(binder, _stretch(sand), 0.30)
    base = Image.merge("RGB", (binder, binder, binder))

    # 2. coarse aggregate: polygons by size class, each a stone tone partly coated in binder
    stones = base.copy()
    mask = Image.new("L", (n, n), 0)
    hgt_st = Image.new("L", (n, n), 0)
    ds, dm, dh = ImageDraw.Draw(stones), ImageDraw.Draw(mask), ImageDraw.Draw(hgt_st)
    area_mm2 = (TILE_M * 1000.0) ** 2
    counts = {}
    for lo, hi, share in GRADATION:
        d_mean = 0.5 * (lo + hi) * 0.5 * (SECTION[0] + SECTION[1])
        a_mean = math.pi * (0.5 * d_mean) ** 2
        cnt = int(round(STONE_SHOW * share * area_mm2 / a_mean))
        counts[f"{lo}-{hi} mm"] = cnt
        for _ in range(cnt):
            d_mm = rng.uniform(lo, hi) * rng.uniform(*SECTION)
            r = max(0.6, 0.5 * d_mm * px_mm)
            cx, cy = rng.random() * n, rng.random() * n
            agg = rng.uniform(105, 195)                   # [invented] crushed granite / quartzite greys
            tint = rng.uniform(-6, 6)
            # [invented] how much binder has worn off its top: traffic wears the coarse stones' tops bare first
            expo = rng.random() ** (0.45 if d_mm > 6.0 else 0.8)
            g = BINDER + (agg - BINDER) * expo
            fill = (_clamp(g + tint), _clamp(g + 0.3 * tint), _clamp(g - tint))
            top = _clamp(134 + 44 * min(1.0, d_mm / 12.0) * (0.45 + 0.55 * expo))
            pts = _polygon(rng, cx, cy, r)
            _draw_wrapped((ds, dm, dh), pts, r, n, (fill, 255, top))

    # 3. the binder meniscus round each stone, and fine sand speckle over everything
    edge = ImageChops.subtract(mask, _wrapf(mask, lambda im: im.filter(ImageFilter.MinFilter(3)), 2))
    edge = _wrapf(edge, lambda im: im.filter(ImageFilter.GaussianBlur(0.6)), 3)
    dark = Image.new("RGB", (n, n), (52, 52, 54))
    diffuse = Image.composite(dark, stones, edge.point(lambda p: p * 55 // 100))
    speck = _levels(_white(rng, n), 238, 255, 0, 255)     # ~3 % of pixels: light sand grains
    diffuse = Image.composite(Image.new("RGB", (n, n), (150, 150, 152)), diffuse, speck.point(lambda p: p * 45 // 100))
    pores = _levels(_white(rng, n, blur=0.7), 0, _percentile(_white(random.Random(seed + 1), n, 0.7), 0.025) + 2, 255, 0)
    diffuse = Image.composite(Image.new("RGB", (n, n), (26, 26, 27)), diffuse, pores.point(lambda p: p * 70 // 100))
    diffuse = _match_mean(diffuse, MEAN_ASPHALT)

    # 4. relief: the matrix sits low and grainy, stones stand up as soft domes, pores are holes
    mat = _levels(_stretch(sand), 0, 255, 100, 128)
    domes = _wrapf(hgt_st, lambda im: im.filter(ImageFilter.GaussianBlur(1.4 * scale + 0.3)), 6)
    hgt = ImageChops.lighter(mat, domes)
    hgt = ImageChops.subtract(hgt, pores.point(lambda p: p * 50 // 255))
    normal = _normal(hgt, strength=ASPHALT_NORMAL_DIV)
    return diffuse, normal, hgt, counts


def concrete(scale=1.0, seed=SEEDS["concrete_plain"], aged=False):
    """(diffuse RGB, normal RGB, height L): plain cast concrete, or aged; one tile = TILE_M"""
    n = int(round(1024 * scale))
    rng = random.Random(seed)
    mott_big = _stretch(_noise(rng, 8, n))                # 50 cm: curing / stain patches
    mott_a = _stretch(_noise(rng, 32, n))                 # 12.5 cm
    mott_b = _stretch(_noise(rng, 128, n))                # 3 cm
    sand = _stretch(_white(rng, n, blur=0.5 * scale + 0.2))
    paste = Image.new("L", (n, n), 150)
    paste = _mod(paste, mott_big, 0.05 if aged else 0.025)
    paste = _mod(paste, mott_a, 0.07 if aged else 0.035)
    paste = _mod(paste, mott_b, 0.05 if aged else 0.03)
    paste = _mod(paste, sand, 0.16 if aged else 0.10)
    warm = Image.merge("RGB", (paste, paste, paste))
    # aged: exposed fines and dark stain blotches; plain: a few bugholes (air pockets against the form)
    if aged:
        fines = _levels(_white(rng, n), 200, 255, 0, 255)
        warm = Image.composite(Image.new("RGB", (n, n), (182, 176, 164)), warm, fines.point(lambda p: p * 40 // 100))
        stain = _levels(_stretch(_noise(rng, 16, n, blur=2.0)), 150, 245, 0, 255)
        warm = Image.composite(Image.new("RGB", (n, n), (70, 66, 58)), warm, stain.point(lambda p: p * 45 // 100))
    holes = Image.new("L", (n, n), 0)
    dh = ImageDraw.Draw(holes)
    px_mm = n / (TILE_M * 1000.0)
    for _ in range(int((900 if aged else 420) * scale * scale)):   # [invented] bugholes per tile
        r = max(0.5, rng.uniform(1.0, 4.5) * px_mm)
        cx, cy = rng.random() * n, rng.random() * n
        _draw_wrapped((dh,), _polygon(rng, cx, cy, r), r, n, (255,))
    holes = _wrapf(holes, lambda im: im.filter(ImageFilter.GaussianBlur(0.5)), 2)
    diffuse = Image.composite(Image.new("RGB", (n, n), (60, 58, 55)), warm, holes.point(lambda p: p * 60 // 100))
    diffuse = _match_mean(diffuse, MEAN_AGED if aged else MEAN_CONCRETE)
    hgt = _levels(sand, 0, 255, 112, 144) if aged else _levels(sand, 0, 255, 120, 136)
    hgt = _mod(hgt, mott_a, 0.06 if aged else 0.02)
    hgt = ImageChops.subtract(hgt, holes.point(lambda p: p * 40 // 255))
    normal = _normal(hgt, strength=AGED_NORMAL_DIV if aged else CONCRETE_NORMAL_DIV)
    return diffuse, normal, hgt, {}


ASPHALT_NORMAL_DIV = 1.25    # [tuned] to the replaced map's tilt, see the docstring
CONCRETE_NORMAL_DIV = 2.2
AGED_NORMAL_DIV = 1.5
BINDER = 66                  # [invented] the binder's grey before the mean match (darker = stones stand out more)

PAIRS = {
    "asphalt_dense": lambda: asphalt_dense(),
    "concrete_plain": lambda: concrete(seed=SEEDS["concrete_plain"], aged=False),
    "concrete_aged": lambda: concrete(seed=SEEDS["concrete_aged"], aged=True),
}


def encode(im):
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=JPEG_Q, subsampling=0, optimize=True)
    return buf.getvalue()


def md5(b):
    return hashlib.md5(b).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--check", action="store_true", help="compare fresh paints with the files on disk (exit 1 on any difference)")
    ap.add_argument("--only", default=None, help="one pair name: " + ", ".join(PAIRS))
    ap.add_argument("--height-dir", default=None, help="also write each height picture (PNG) here, for stills")
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    bad = 0
    for name, make in PAIRS.items():
        if a.only and name != a.only:
            continue
        dif, nor, hgt, counts = make()
        for suffix, im in (("diffuse", dif), ("normal", nor)):
            data = encode(im)
            p = out / f"{name}_{suffix}.jpg"
            if len(data) > MAX_BYTES:
                print(f"[owned-tex] FAIL {p.name}: {len(data):,} B > {MAX_BYTES:,}")
                bad += 1
            if a.check:
                have = p.read_bytes() if p.exists() else b""
                same = have == data
                print(f"[owned-tex] {p.name}: on disk {md5(have) if have else 'missing'}, fresh {md5(data)} -> {'same' if same else 'DIFFERENT'}")
                bad += 0 if same else 1
            else:
                out.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                print(f"[owned-tex] wrote {p} ({len(data):,} B, md5 {md5(data)}, {im.size[0]}x{im.size[1]})")
        if counts:
            print(f"[owned-tex] {name} stones per tile: {counts}")
        if a.height_dir:
            Path(a.height_dir).mkdir(parents=True, exist_ok=True)
            hgt.save(Path(a.height_dir) / f"{name}_height.png")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""Mission Gorge Rd's terracotta median top: the CC0 paver, toned to the aerial and laid on the prep's 4 m grid
(ledger 0099 round 3, item 1; 2026-11-23).

    python -I tracks/san-diego-lake-murray/textures/make_terracotta_median.py [<out dir>] [--check]

IN   assets/textures/terracotta_paver_diffuse.jpg / _normal.jpg: ambientCG PavingStones135, CC0, 2048 px, untinted and
     bound to no track (assets/textures/terracotta_paver.md holds its provenance and every number used here).
OUT  terracotta_median_diffuse.jpg / terracotta_median_normal.jpg beside this file (or in <out dir>), 2048 px, bound by
     track.config.json texture_overrides["1KERB_PAVER"] (scripts/ac/pbr.py row 1KERB_PAVER).

TWO THINGS ARE DONE, and nothing else:
  * THE TONE. Each channel of the diffuse is multiplied by one gain so the file's mean is the mean NAIP 2022 shows on
    the long island MD13 after its canopy and shadow are masked out: TARGET below, 8-bit sRGB, measured by
    tools/measure_median_tone.py (28,392 pixels). The gain is on the 8-bit values and iterated, because the top clips:
    the method of tools/make_owned_surfaces.py `_match_mean`. NAIP is a sensor product, not albedo: this matches the
    paver to how the 2022 photo shows the median, the look the aerial-led builds are compared against. MD11, the short
    island, is narrower than the photo's colour resolution, so its own tone could not be measured: it wears MD13's
    [inferred from MD13].
  * THE SCALE. The prep lays every 1KERB mesh on a top-down grid of one image per 4.0 m (engine-july
    scripts/ac/build_kn5_loop.py UV_TILE; the meshes it leaves alone are a list in the prep, which is not touched). The
    paver image is "ca. 1.9 m" across (its asset page), so the output holds 2 x 2 repeats of it, each reduced to half
    size by a box average (what the first mip level is): one repeat = 2.0 m on the ground, 5 % over the asset's own
    figure, 512 px per metre as the road's own tile. The normal map is reduced and repeated the same way; its vectors
    are not re-normalised (a mip level is not either).

--check: nothing is written; the files beside this script are measured against TARGET and the 2 x 2 repeat (exit 1 if
a channel's mean is more than TOL levels off, or the four quarters differ inside their outermost pixel ring). JPEG bytes depend on the Pillow that wrote
them, so the check is on what the files hold, not on their md5.
PIL only."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parents[2] / "assets" / "textures"
TARGET = (147.9, 127.8, 115.6)     # MD13 on NAIP 2022, mean 8-bit sRGB of its kept pixels (assets/textures/terracotta_paver.md)
SOURCE_MEAN = (166.0, 123.7, 107.8)  # the untinted diffuse's own mean, same file (checked below to 0.1)
TOL = 0.5                          # [invented] levels: what one 8-bit rounding step and the JPEG leave of the match
REPEATS = 2                        # per side: 4.0 m grid / 2 = 2.0 m per repeat (the asset says ca. 1.9 m)
SIZE = 2048
QUALITY = 92                       # as the track's other tiles (make_sandstone_cut.py)


def mean(im):
    return tuple(round(v, 2) for v in ImageStat.Stat(im).mean)


def toned(src):
    """(image at one repeat's size, the three gains): each band times one gain, its mean on TARGET"""
    half = src.resize((SIZE // REPEATS, SIZE // REPEATS), Image.BOX)
    bands, gains = [], []
    for band, want in zip(half.split(), TARGET):
        g = want / ImageStat.Stat(band).mean[0]
        best = None
        for _ in range(12):
            b = band.point([min(255, int(round(v * g))) for v in range(256)])
            m = ImageStat.Stat(b).mean[0]
            if best is None or abs(m - want) < abs(best[1] - want):
                best = (b, m, g)
            if abs(m - want) < 0.02:
                break
            g *= want / m
        bands.append(best[0])
        gains.append(round(best[2], 4))
    return Image.merge("RGB", bands), gains


def repeat(tile):
    out = Image.new("RGB", (SIZE, SIZE))
    n = SIZE // REPEATS
    for j in range(REPEATS):
        for i in range(REPEATS):
            out.paste(tile, (i * n, j * n))
    return out


def quarters_equal(im):
    """the four quarters hold the same pixels, but for each quarter's outermost pixel ring: a JPEG decoder smooths the
    half-resolution colour across a quarter's edge with its neighbour, and the image's own border has none (measured
    2026-11-23: the quarters differ on that one ring only, by up to 9 levels on the diffuse and 21 on the normal)"""
    n = SIZE // REPEATS
    first = im.crop((1, 1, n - 1, n - 1))
    return all(ImageChops.difference(first, im.crop((i * n + 1, j * n + 1, (i + 1) * n - 1, (j + 1) * n - 1))).getbbox() is None
               for j in range(REPEATS) for i in range(REPEATS))


def check(folder):
    bad = []
    d = Image.open(folder / "terracotta_median_diffuse.jpg").convert("RGB")
    n = Image.open(folder / "terracotta_median_normal.jpg").convert("RGB")
    m = mean(d)
    off = [round(a - b, 2) for a, b in zip(m, TARGET)]
    print(f"[terracotta-median] diffuse {d.size}, mean {m}, off the target by {off} (tolerance {TOL})")
    if d.size != (SIZE, SIZE) or n.size != (SIZE, SIZE):
        bad.append("size")
    if any(abs(o) > TOL for o in off):
        bad.append("tone")
    for name, im in (("diffuse", d), ("normal", n)):
        if not quarters_equal(im):
            bad.append(f"{name}: the four quarters differ (not {REPEATS} x {REPEATS} repeats)")
    nm = mean(n)
    print(f"[terracotta-median] normal {n.size}, mean {nm} (the source's own mean {mean(Image.open(ASSETS / 'terracotta_paver_normal.jpg').convert('RGB'))})")
    if bad:
        print("[terracotta-median] FAIL " + "; ".join(bad))
        return 1
    print("[terracotta-median] OK")
    return 0


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    out = Path(args[0]) if args else HERE
    if "--check" in argv:
        return check(out)
    src = Image.open(ASSETS / "terracotta_paver_diffuse.jpg").convert("RGB")
    sm = mean(src)
    if src.size != (SIZE, SIZE) or any(abs(a - b) > 0.1 for a, b in zip(sm, SOURCE_MEAN)):
        print(f"[terracotta-median] FAIL the source diffuse is {src.size}, mean {sm}: not the file terracotta_paver.md measured {SOURCE_MEAN}")
        return 1
    tile, gains = toned(src)
    repeat(tile).save(out / "terracotta_median_diffuse.jpg", quality=QUALITY, optimize=True)
    nrm = Image.open(ASSETS / "terracotta_paver_normal.jpg").convert("RGB")
    repeat(nrm.resize((SIZE // REPEATS, SIZE // REPEATS), Image.BOX)).save(out / "terracotta_median_normal.jpg", quality=QUALITY, optimize=True)
    print(f"[terracotta-median] source mean {sm}; gains R / G / B {gains}; toned tile mean {mean(tile)} (target {TARGET}); "
          f"{REPEATS} x {REPEATS} repeats in {SIZE} px = {4.0 / REPEATS:.1f} m per repeat on the 4 m grid")
    return check(out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

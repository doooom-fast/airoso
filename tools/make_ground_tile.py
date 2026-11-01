"""A tileable ground pair for a track's own textures/ folder (.claude/skills/bespoke-assets section 4 step 3): the colour is
measured off the track's NAIP, everything else is a seeded drawing (Pillow only, no captured pixel, CC0); re-running with the
same arguments reproduces the bytes.

    PYTHONUTF8=1 python tools/make_ground_tile.py <out-dir> <name> <style> <R> <G> <B> [seed]

  style  turf     mown grass: fine blades, faint mowing bands, no bare soil. Milford (DOSSIER Part D section 6)
         prairie  shortgrass on dry soil: straw tufts over bare patches. High Plains
         foothill tawny grass and decomposed granite. Lookout Lariat (DOSSIER section 8, D7)

Writes <name>_diffuse.jpg + <name>_normal.jpg, 1024 x 1024, one tile = 4 m (the kn5 prep's UV_TILE); the tile's mean is brought
back onto the measured colour, so the ground reads the photograph's colour from a car. Bound by track.config.json
texture_overrides["1GRASS"], ["GRASS_FAR"], ["SHOULDERUND"], synced into the workshop by ship.json sync_in.optional.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

N = 1024
STYLES = {
    #            blades, blade len px, blade colours relative to the mean, field contrast, soil share of the base
    "turf":     (26000, (6, 16), ((0.82, 0.88, 0.76), (1.0, 1.04, 0.92), (1.12, 1.14, 1.0), (0.92, 0.98, 0.84)), 26, 0.0),
    "prairie":  (9000, (10, 30), ((1.14, 1.08, 0.94), (0.96, 0.92, 0.76), (1.26, 1.18, 1.0), (0.82, 0.84, 0.66)), 44, 0.55),
    "foothill": (11000, (8, 26), ((1.16, 1.06, 0.88), (0.94, 0.88, 0.70), (1.28, 1.16, 0.96), (0.78, 0.76, 0.58)), 40, 0.4),
}


def noise(rng, small, blur):
    s = Image.frombytes("L", (small, small), bytes(rng.randrange(256) for _ in range(small * small)))
    t = Image.new("L", (3 * small, 3 * small))
    for a in range(3):
        for b in range(3):
            t.paste(s, (a * small, b * small))
    t = t.resize((3 * N, 3 * N), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    return ImageOps.autocontrast(t.crop((N, N, 2 * N, 2 * N)), cutoff=1)


def main() -> int:
    out, name, style = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    mean = tuple(int(v) for v in sys.argv[4:7])
    seed = int(sys.argv[7]) if len(sys.argv) > 7 else 20261031
    rng = random.Random(seed)
    blades, (l0, l1), palette, contrast, soil_share = STYLES[style]
    field = Image.blend(noise(rng, 6, 60), noise(rng, 48, 7), 0.5)
    g = field.point(lambda v: 255 - contrast + v * contrast // 255)
    soil = (min(255, int(mean[0] * 1.12)), min(255, int(mean[1] * 1.04)), min(255, int(mean[2] * 0.96)))
    img = ImageChops.multiply(Image.new("RGB", (N, N), soil if soil_share else mean), Image.merge("RGB", (g, g, g)))
    height = field.point(lambda v: v // 4)
    d, dh = ImageDraw.Draw(img), ImageDraw.Draw(height)
    for _ in range(blades):
        x, y = rng.uniform(0, N), rng.uniform(0, N)
        ln = rng.uniform(l0, l1)
        a = rng.uniform(0, 2 * math.pi) if style == "turf" else rng.uniform(-2.2, -0.9)
        c = palette[rng.randrange(len(palette))]
        col = tuple(min(255, int(mean[i] * c[i])) for i in range(3))
        for ox in (-N, 0, N) if (x < l1 or x > N - l1) else (0,):
            for oy in (-N, 0, N) if (y < l1 or y > N - l1) else (0,):
                seg = (x + ox, y + oy, x + ox + math.cos(a) * ln, y + oy + math.sin(a) * ln)
                d.line(seg, fill=col, width=2 if style == "turf" else 1)
                dh.line(seg, fill=rng.randint(120, 220), width=2)
    st = ImageStat.Stat(img)
    img = Image.merge("RGB", [b.point(lambda v, f=mean[i] / st.mean[i]: min(255, int(v * f))) for i, b in enumerate(img.split())])
    img.save(out / f"{name}_diffuse.jpg", quality=88, optimize=True)
    hp = height.filter(ImageFilter.GaussianBlur(0.7)).load()
    nrm = Image.new("RGB", (N, N))
    np_ = nrm.load()
    for y in range(N):
        yu, yd = (y - 1) % N, (y + 1) % N
        for x in range(N):
            xl, xr = (x - 1) % N, (x + 1) % N
            dx = (hp[xr, y] - hp[xl, y]) / 255.0 * 1.8
            dy = (hp[x, yd] - hp[x, yu]) / 255.0 * 1.8
            ln = math.sqrt(dx * dx + dy * dy + 1.0)
            np_[x, y] = (int(127.5 - dx / ln * 127.5), int(127.5 + dy / ln * 127.5), int(127.5 + 127.5 / ln))
    nrm.save(out / f"{name}_normal.jpg", quality=88, optimize=True)
    final = ImageStat.Stat(img).mean
    print(f"{name}: {style}, mean RGB {[round(v) for v in final]} (measured {list(mean)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

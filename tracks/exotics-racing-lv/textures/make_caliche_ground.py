"""Nevada Nights' Mojave ground: a tileable caliche + gravel-lag pair (diffuse + OpenGL normal) in place of the stock dry
dirt (LA Canyons bytes). Kevin's dressing call, DOSSIER section 11 step 2: "the Mojave ground in place of the default
grass"; DOSSIER section 6: calcic horizon shallow to the surface with a gravel / cobble lag, tan / ochre, no green.

COLOUR: measured, not chosen. The undisturbed strip north of the lap on USDA NAIP 2019-07-06 (the scrub polygon in
track.config.json scenery.bespoke.scrub; source/naip_2019_exr.png) reads mean RGB (172, 163, 149) over its pale soil
pixels (brightness above the polygon's median - 8). The lots inside the lap read darker and greener on NAIP 2013 (151, 150,
128), which is the paving, not the desert, so they do not set this tile. The lag's stone colours are [invented].

Nothing here is captured: drawn by a seeded generator (Pillow only), owned outright, CC0; re-running reproduces the bytes.

usage (from the airoso root):
    python tracks/exotics-racing-lv/textures/make_caliche_ground.py tracks/exotics-racing-lv/textures

Writes caliche_diffuse.jpg + caliche_normal.jpg (1024 x 1024, one tile = 4 m: the kn5 prep's UV_TILE). Bound by
track.config.json texture_overrides["1GRASS"], ["GRASS_FAR"], ["SHOULDERUND"]; synced into the workshop by ship.json.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

N = 1024                      # px per 4 m tile (3.9 mm / px)
SEED = 20190706               # the NAIP date the colour is measured from
SOIL = (172, 163, 149)        # measured, above
out = Path(sys.argv[1])
rng = random.Random(SEED)


def noise(small, blur):
    """a tileable grey field: a seeded small grid, tiled 3x3, enlarged, blurred, the centre kept (wraps at the edges)"""
    s = Image.frombytes("L", (small, small), bytes(rng.randrange(256) for _ in range(small * small)))
    t = Image.new("L", (3 * small, 3 * small))
    for a in range(3):
        for b in range(3):
            t.paste(s, (a * small, b * small))
    t = t.resize((3 * N, 3 * N), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    return ImageOps.autocontrast(t.crop((N, N, 2 * N, 2 * N)), cutoff=1)


def stones():
    """the gravel lag: angular stones drawn with wrap-around, into a colour layer, a mask and a height bump"""
    mask = Image.new("L", (N, N), 0)
    height = Image.new("L", (N, N), 0)
    tint = Image.new("RGB", (N, N), SOIL)
    dm, dh, dt = ImageDraw.Draw(mask), ImageDraw.Draw(height), ImageDraw.Draw(tint)
    palette = ((152, 140, 124), (166, 154, 136), (142, 130, 116), (188, 178, 160), (148, 128, 108))
    for _ in range(2200):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        r = rng.uniform(1.5, 5.0) if rng.random() < 0.96 else rng.uniform(5.0, 10.0)      # 6 mm .. 4.7 cm radius
        col = palette[rng.randrange(len(palette))]
        sides = rng.randint(5, 7)
        phase = rng.uniform(0, math.pi)
        radii = [r * rng.uniform(0.7, 1.15) for _ in range(sides)]
        for ox in (-N, 0, N) if (cx < 16 or cx > N - 16) else (0,):
            for oy in (-N, 0, N) if (cy < 16 or cy > N - 16) else (0,):
                pts = [(cx + ox + radii[k] * math.cos(phase + 2 * math.pi * k / sides),
                        cy + oy + radii[k] * math.sin(phase + 2 * math.pi * k / sides)) for k in range(sides)]
                dm.polygon(pts, fill=255)
                dt.polygon(pts, fill=col)
                dh.polygon(pts, fill=int(120 + r * 12))
    return mask.filter(ImageFilter.GaussianBlur(0.5)), height.filter(ImageFilter.GaussianBlur(0.8)), tint


broad = noise(6, 60)                                          # low: kept faint, a 4 m tile repeats across a lot
mid = noise(40, 8)
fine = noise(256, 1.0)
field = Image.blend(Image.blend(broad, mid, 0.45), fine, 0.40)
stone_mask, stone_h, stone_col = stones()

# +-7 % around the measured soil, so the tile's mean stays on the measurement
G = field.point(lambda v: 219 + v * 36 // 255)
soil = ImageChops.multiply(Image.new("RGB", (N, N), SOIL), Image.merge("RGB", (G, G, G)))
img = Image.composite(stone_col, soil, stone_mask)
rim = ImageChops.subtract(stone_mask.filter(ImageFilter.MaxFilter(3)), stone_mask)
img = Image.composite(Image.new("RGB", (N, N), (132, 124, 110)), img, rim.point(lambda v: v // 3))
# bring the mean back onto the measured soil (the stones and the rims pull it down a little)
st = ImageStat.Stat(img)
img = Image.merge("RGB", [band.point(lambda v, f=SOIL[i] / st.mean[i]: min(255, int(v * f))) for i, band in enumerate(img.split())])
img.save(out / "caliche_diffuse.jpg", quality=90, optimize=True)

h = ImageChops.add(field.point(lambda v: v // 4), stone_h)
hp = h.filter(ImageFilter.GaussianBlur(0.6)).load()
nrm = Image.new("RGB", (N, N))
npx = nrm.load()
STRENGTH = 2.0
for y in range(N):
    yu, yd = (y - 1) % N, (y + 1) % N
    for x in range(N):
        xl, xr = (x - 1) % N, (x + 1) % N
        dx = (hp[xr, y] - hp[xl, y]) / 255.0 * STRENGTH
        dy = (hp[x, yd] - hp[x, yu]) / 255.0 * STRENGTH
        L = math.sqrt(dx * dx + dy * dy + 1.0)
        npx[x, y] = (int(127.5 - dx / L * 127.5), int(127.5 + dy / L * 127.5), int(127.5 + 127.5 / L))
nrm.save(out / "caliche_normal.jpg", quality=90, optimize=True)
final = ImageStat.Stat(img)
print(f"caliche_diffuse.jpg: {N}x{N}, mean RGB {[round(m) for m in final.mean]} (measured soil {list(SOIL)}), stone share "
      f"{sum(1 for v in stone_mask.tobytes() if v > 127) / (N * N):.2f}; caliche_normal.jpg written")

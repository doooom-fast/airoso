"""Derive a tileable sandstone / conglomerate ROAD-CUT texture pair (diffuse + OpenGL normal) for the north network's
cut faces (ledger 0054 P4 buildings + rock; EXPANSION-PLAN A9/A10's REALISM rule: lean in, never eject).

The real walls beside Mission Gorge Rd (s 1475-1560, south side) and Jackson Dr north (the five south-west walls) are
cut into the Stadium Conglomerate and the Friars / Mission Valley sandstones of the Mission Gorge: a pale tan to warm
brown bedded sandstone with rounded cobble inclusions (fist to melon size), dark vertical weathering streaks under the
rim, in bands a hand to a metre thick. Nothing here is captured: the tile is drawn deterministically (a seeded
generator, no library randomness), owned outright and CC0 — the same path as tools/make_kerb_texture.py and
make_chaparral_far.py. Re-running reproduces the files byte for byte.

usage (from the airoso root):
    python tracks/san-diego-lake-murray/textures/make_sandstone_cut.py tracks/san-diego-lake-murray/textures

Writes sandstone_cut_diffuse.jpg and sandstone_cut_normal.jpg (1024 x 1024, one tile = 4 m on the face: the kn5 prep's
UV_TILE; tools/rock_faces_blend.py projects u along the wall, v up it). Bound by track.config.json
texture_overrides["1GRASS_ROCK"]; synced into the workshop by tools/ship_sd.sh (TRACK_TEXTURES) and ship.json.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat

N = 1024                      # px per 4 m tile (3.9 mm / px)
SEED = 20261026               # ledger 0054 P4, the day the barriers were approved
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


def fbm(scales):
    """fractal noise: a weighted sum of tileable fields at several scales, 0..255"""
    acc = Image.new("L", (N, N), 128)
    for small, blur, w in scales:
        f = noise(small, blur)
        acc = Image.blend(acc, f, w)
    return ImageOps.autocontrast(acc, cutoff=1)


def strata():
    """bedding: brightness that steps along v (up the face) in bands a hand to a metre thick, slightly tilted"""
    rows = []
    v = 128
    while len(rows) < N:
        h = rng.randint(20, 240)                  # 8 cm .. 94 cm per bed
        v = max(60, min(200, v + rng.randint(-55, 55)))
        rows += [v] * h
    rows = rows[:N]                                 # the bands wrap in v (the tile's v runs up the face)
    # a gentle tilt and ragged bed edges: shift each column by a tileable low-frequency amount
    tilt = noise(6, 60)
    tp = tilt.load()
    out_ = Image.new("L", (N, N))
    op = out_.load()
    for x in range(N):
        dy = int((tp[x, 0] - 128) / 128.0 * 14)
        for y in range(N):
            op[x, y] = rows[(y + dy) % N]
    return out_.filter(ImageFilter.GaussianBlur(1.2))


def cobbles():
    """rounded clasts of the conglomerate: ellipses drawn with wrap-around, into a mask and a height bump"""
    mask = Image.new("L", (N, N), 0)
    height = Image.new("L", (N, N), 0)
    tint = Image.new("L", (N, N), 128)            # per-cobble colour shift (grey-brown .. rust)
    dm, dh, dt = ImageDraw.Draw(mask), ImageDraw.Draw(height), ImageDraw.Draw(tint)
    for _ in range(150):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        r = rng.uniform(7, 30) if rng.random() < 0.85 else rng.uniform(30, 44)                    # 3.5 .. 14 cm radius
        ar = rng.uniform(0.65, 1.0)
        ang = rng.uniform(0, math.pi)
        t = rng.randint(60, 200)
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                pts = []
                for k in range(24):
                    a_ = 2 * math.pi * k / 24
                    ex, ey = r * math.cos(a_), r * ar * math.sin(a_)
                    pts.append((cx + ox + ex * math.cos(ang) - ey * math.sin(ang),
                                cy + oy + ex * math.sin(ang) + ey * math.cos(ang)))
                dm.polygon(pts, fill=255)
                dt.polygon(pts, fill=t)
                for q in range(6, 0, -1):          # a domed bump: concentric rings
                    s_ = q / 6.0
                    ring = [(cx + ox + (px_ - cx - ox) * s_, cy + oy + (py_ - cy - oy) * s_) for px_, py_ in pts]
                    dh.polygon(ring, fill=int(255 * (1.0 - s_ * s_) ** 0.5 * 0.9 + 25))
    return mask.filter(ImageFilter.GaussianBlur(0.8)), height.filter(ImageFilter.GaussianBlur(1.5)), tint


def streaks():
    """dark weathering streaks running down the face: a 1-D tileable field along u, smeared along v"""
    col = noise(32, 10).resize((N, 1), Image.BOX).resize((N, N), Image.NEAREST)
    fade = Image.linear_gradient("L").rotate(180).resize((N, N))      # strongest under the rim (top of the tile)
    col = ImageChops.multiply(col, fade)
    return col.point(lambda v: max(0, min(255, int((v - 150) * 3)))).filter(ImageFilter.GaussianBlur(3))


grain = fbm([(256, 1.0, 0.55), (64, 3.0, 0.35), (16, 12.0, 0.12)])   # sand grain + faint blotches
beds = strata()
cob_mask, cob_h, cob_t = cobbles()
streak = streaks()

# --- colour --------------------------------------------------------------------------------------------------
SAND_LIT = (196, 172, 132)      # pale tan bed in the sun
SAND_DARK = (134, 110, 78)      # the warm brown beds / shade
COB_GREY = (122, 114, 104)      # a grey quartzite cobble
COB_RUST = (150, 104, 70)       # an iron-stained one
base = Image.composite(Image.new("RGB", (N, N), SAND_LIT), Image.new("RGB", (N, N), SAND_DARK), beds)
G = grain.point(lambda v: 205 + v // 5)                             # +-10 % grain, never over 1.0
base = ImageChops.multiply(base, Image.merge("RGB", (G, G, G)))
cob = Image.composite(Image.new("RGB", (N, N), COB_RUST), Image.new("RGB", (N, N), COB_GREY), cob_t)
cob = ImageChops.multiply(cob, Image.merge("RGB", (G, G, G)))
rim = ImageChops.subtract(cob_mask, cob_mask.filter(ImageFilter.MinFilter(5)))    # a dark rim round each clast
cob = Image.composite(Image.new("RGB", (N, N), (92, 80, 64)), cob, rim.point(lambda v: v * 3 // 4))
img = Image.composite(cob, base, cob_mask)
dark = Image.new("RGB", (N, N), (84, 70, 54))
img = Image.composite(dark, img, streak.point(lambda v: v // 2))
img = ImageEnhance.Brightness(img).enhance(1.06)
img.save(out / "sandstone_cut_diffuse.jpg", quality=92, optimize=True)

# --- height -> OpenGL normal (green up) ---------------------------------------------------------------------------
h = ImageChops.add(beds.point(lambda v: v // 3), grain.point(lambda v: v // 5))
h = ImageChops.lighter(h, cob_h)
h = h.filter(ImageFilter.GaussianBlur(0.6))
hp = h.load()
nrm = Image.new("RGB", (N, N))
npx = nrm.load()
STRENGTH = 2.2
for y in range(N):
    yu, yd = (y - 1) % N, (y + 1) % N
    for x in range(N):
        xl, xr = (x - 1) % N, (x + 1) % N
        dx = (hp[xr, y] - hp[xl, y]) / 255.0 * STRENGTH
        dy = (hp[x, yd] - hp[x, yu]) / 255.0 * STRENGTH
        L = math.sqrt(dx * dx + dy * dy + 1.0)
        nx, ny, nz = -dx / L, dy / L, 1.0 / L          # OpenGL: +y = up the image (v), as Poly Haven "nor_gl"
        npx[x, y] = (int(127.5 + nx * 127.5), int(127.5 + ny * 127.5), int(127.5 + nz * 127.5))
nrm.save(out / "sandstone_cut_normal.jpg", quality=92, optimize=True)
st = ImageStat.Stat(img)
print(f"sandstone_cut_diffuse.jpg: {N}x{N}, mean RGB {[round(m) for m in st.mean]}, cobble share "
      f"{sum(1 for v in cob_mask.tobytes() if v > 127) / (N * N):.2f}; sandstone_cut_normal.jpg written")

"""Paint the worn race-kerb atlas (ledger 0053): assets/textures/kerb_race_worn_diffuse.jpg + _normal.jpg.

Kevin, 2026-10-12, from the seat: "i'd like the race curbs to be tire-worn/textured". The race kerbs shipped a
771-byte picture of two flat colours. This generator paints the replacement from nothing but seeded noise and
straight lines (Pillow only, no numpy, no photo, no third-party pixel), so the result is ours and CC0
(assets/licenses.json "Worn race kerb (generated)"). Same seed -> same bytes.

    PYTHONUTF8=1 python tools/make_kerb_texture.py                 # (re)write both files in assets/textures/
    PYTHONUTF8=1 python tools/make_kerb_texture.py --check         # exit 1 if the committed files differ from a fresh paint
    PYTHONUTF8=1 python tools/make_kerb_texture.py --preview p.png # also a half-size preview of the colour atlas

THE PICTURE (layout constants live in tools/race_furniture.py, the wrap's own module, so picture and wrap agree):
  * 1024 x 2048 (power of two, LAWS L7). Four COLUMNS of 256 px across = tyre-rubber level 0..3. Each column is
    the kerb's full cross-section (lane lip at the left, 8 px pad each side so far-away mipmaps don't bleed the
    neighbouring column in), by real surface length: ramp, flat top, the 5 cm outer face.
  * Down the image: 8 m of kerb at 256 px per metre — eight 1 m blocks, weathered traffic red and white, with a
    grime-filled joint (~1.5 cm) at every block end. The picture repeats seamlessly every 8 m.
  * Every column shares the SAME paint, chips, joints and dirt; only the rubber differs, and level c's rubber is a
    superset of level c-1's (one streak field, falling thresholds). So where the wrap switches column — always at a
    block joint — marks are only ever ADDED.
  * Paint chipped to the grey concrete mostly on the lane-side ramp and next to the joints; dirt on the outer edge;
    rubber as streaks drawn out ~10:1 along the kerb in the band tyres actually ride (the ramp and the lane half).
  * The NORMAL map (a picture that tells the lighting which way each pixel of surface faces, so flat geometry
    shows grooves and grain): joints are grooves, chips sit a little lower, fine grain everywhere, rubber fills the
    grain. OpenGL convention (green = up the image), like every normal map in assets/textures (SOURCES.txt).

Every look number here is [invented] (GATES-CHANGELOG 0053) and meant to be tuned by eye from Blender stills and
Kevin's drive — not measured from anybody's kerb.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO / "tools") not in sys.path:
    sys.path.insert(0, str(AIROSO / "tools"))
import race_furniture as rf  # noqa: E402  (pure: the atlas layout + the profile u)

OUT_DIR = AIROSO / "assets" / "textures"
DIFFUSE_NAME = "kerb_race_worn_diffuse.jpg"
NORMAL_NAME = "kerb_race_worn_normal.jpg"
SEED = 53
JPEG_DIFFUSE_Q = 90
JPEG_NORMAL_Q = 90
MAX_BYTES = 2_000_000           # per file (V1 d)

# colours [invented]: RAL 3020 traffic red / RAL 9016 traffic white, weathered
RED = (172, 36, 31)
WHITE = (214, 212, 204)
CONCRETE = (142, 139, 132)
GRIME = (52, 47, 41)
DIRT = (104, 94, 78)
RUBBER = (27, 25, 24)
# rubber coverage of the tyre band per level (fraction of band pixels under a streak) and opacity [invented]
RUBBER_COVER = (0.0, 0.12, 0.30, 0.55)
RUBBER_OPACITY = (0.0, 0.55, 0.70, 0.82)
RUBBER_HAZE = (0.0, 0.12, 0.28, 0.46)
CHIP_COVER = 0.035              # fraction of the kerb's pixels chipped to concrete
NORMAL_STRENGTH = 2.2           # Sobel divisor: lower = stronger relief


def _clamp(v):
    return max(0, min(255, int(round(v))))


def _tall(im):
    """the image stacked three times down v — filter it, then crop the middle copy: seamless along the kerb"""
    w, h = im.size
    out = Image.new(im.mode, (w, 3 * h))
    for k in range(3):
        out.paste(im, (0, k * h))
    return out


def _mid(im):
    w, h3 = im.size
    h = h3 // 3
    return im.crop((0, h, w, 2 * h))


def _wrap(im, f):
    return _mid(f(_tall(im)))


def _noise(rng, cells_u, cells_v, w, h, blur=0.0):
    """smooth value noise: a cells_u x cells_v grid of seeded bytes, upscaled bicubic to w x h, periodic along v"""
    lo = Image.frombytes("L", (cells_u, cells_v), rng.randbytes(cells_u * cells_v))
    big = _tall(lo).resize((w, 3 * h), Image.BICUBIC)
    if blur > 0:
        big = big.filter(ImageFilter.GaussianBlur(blur))
    return _mid(big)


def _levels(im, lo, hi, out_lo=0, out_hi=255):
    """linear remap lo..hi -> out_lo..out_hi (clamped)"""
    span = max(1e-6, hi - lo)
    lut = [_clamp(out_lo + (out_hi - out_lo) * min(1.0, max(0.0, (p - lo) / span))) for p in range(256)]
    return im.point(lut)


def _percentile(im, frac, mask=None):
    """the grey value below which `frac` of the (masked) pixels lie"""
    hist = im.histogram(mask)
    total = sum(hist)
    acc = 0
    for v, c in enumerate(hist):
        acc += c
        if acc >= frac * total:
            return v
    return 255


def _u_mask(fn, w, h, pad):
    """an L image whose value at column x is 255 * fn(u) — u = the profile coordinate (pads clamp to 0 / 1)"""
    row = Image.new("L", (w, 1))
    inner = max(1, w - 2 * pad)
    for x in range(w):
        u = min(1.0, max(0.0, (x + 0.5 - pad) / inner))
        row.putpixel((x, 0), _clamp(255 * fn(u)))
    return row.resize((w, h), Image.NEAREST)


def _smooth01(x, a, b):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _rgb(c, size):
    return Image.new("RGB", size, c)


def _mul(rgb, grey):
    return ImageChops.multiply(rgb, Image.merge("RGB", [grey] * 3))


def render(scale=1.0, seed=SEED):
    """{diffuse, normal (RGB atlases), alphas (rubber per column, L), joints, chips (L, one column)} — pre-JPEG.
    `scale` < 1 paints the same picture smaller (tests); the noise grids are counted per metre, so the content
    does not change with scale, only its resolution."""
    s = float(scale)
    pxm = rf.KERB_ATLAS_PX_M * s                       # px per metre along v
    w = int(round(rf.KERB_ATLAS_COL_PX * s))
    h = int(round(rf.KERB_ATLAS_V_M * rf.KERB_ATLAS_PX_M * s))
    pad = int(round(rf.KERB_ATLAS_PAD_PX * s))
    size = (w, h)
    rng = random.Random(seed)
    pu = rf.kerb_profile_u()                           # (0, ramp top, outer top, 1)
    n_blocks = int(round(rf.KERB_ATLAS_V_M / rf.KERB_BLOCK_M))
    block_px = rf.KERB_BLOCK_M * pxm

    # 1. paint: alternating 1 m blocks, each repainted a touch differently, sun-faded in broad patches, fine grain
    paint = Image.new("RGB", size)
    d = ImageDraw.Draw(paint)
    for b in range(n_blocks):
        c = RED if b % 2 == 0 else WHITE
        j = rng.uniform(-5.0, 5.0)
        d.rectangle([0, int(round(b * block_px)), w, int(round((b + 1) * block_px)) - 1],
                    fill=tuple(_clamp(v + j) for v in c))
    fade = _levels(_noise(rng, 5, 40, w, h, blur=2 * s), 40, 215, 242, 255)          # ~0.2 m patches, -5 %
    grain = _levels(_noise(rng, 160, 1280, w, h), 30, 225, 240, 255)                # ~6 mm grain, -6 %
    paint = _mul(_mul(paint, fade), grain)
    # the lane-side ramp and the outer face read darker (road film / shadowed dirt)
    paint = _mul(paint, _u_mask(lambda u: 0.88 if u < pu[1] else (0.80 if u > pu[2] else 1.0), w, h, pad))

    # 2. joints: a grime-filled gap at every block end (1.5 cm), soft-edged; wraps across v = 0
    joints = Image.new("L", (w, 3 * h), 0)
    dj = ImageDraw.Draw(joints)
    half = max(1.0, 0.0075 * pxm)
    for b in range(3 * n_blocks + 1):
        y = b * block_px
        dj.rectangle([0, int(round(y - half)), w, int(round(y + half))], fill=255)
    joints = _mid(joints.filter(ImageFilter.GaussianBlur(max(0.4, 0.6 * s))))
    near_joint = Image.new("L", (w, 3 * h), 0)
    dn = ImageDraw.Draw(near_joint)
    for b in range(3 * n_blocks + 1):
        y = b * block_px
        dn.rectangle([0, int(round(y - 0.05 * pxm)), w, int(round(y + 0.05 * pxm))], fill=255)
    near_joint = _mid(near_joint.filter(ImageFilter.GaussianBlur(0.03 * pxm)))

    # 3. chips: paint gone to the grey concrete — on the ramp lip, next to the joints, a few on the outer edge
    lip_w = _u_mask(lambda u: 0.62 + 0.26 * (1.0 - _smooth01(u, pu[1] * 0.5, pu[1] * 2.0))
                    + 0.12 * _smooth01(u, 0.93, 0.99), w, h, pad)
    chip_w = ImageChops.lighter(lip_w, near_joint.point(lambda p: p * 84 // 100))
    clusters = _levels(_noise(rng, 10, 90, w, h, blur=1.0 * s), 40, 220, 150, 255)   # ~9 cm: chips come in groups
    chip_field = ImageChops.multiply(ImageChops.multiply(_noise(rng, 64, 512, w, h, blur=0.4 * s), chip_w), clusters)
    t = _percentile(chip_field, 1.0 - CHIP_COVER)
    chips = _levels(chip_field, t - 3, t + 5)
    concrete = _mul(_rgb(CONCRETE, size), _levels(_noise(rng, 128, 1024, w, h), 20, 235, 215, 255))
    base = Image.composite(concrete, paint, chips)

    # 4. dirt: along the outer edge and down the outer face, patchy; the joints' grime on top
    edge = _u_mask(lambda u: 0.75 * _smooth01(u, 0.86, 0.95) + 0.25 * (1.0 - _smooth01(u, 0.0, pu[1])), w, h, pad)
    dirt = ImageChops.multiply(edge, _levels(_noise(rng, 24, 240, w, h, blur=1.5 * s), 50, 220, 70, 230))
    base = Image.composite(_rgb(DIRT, size), base, dirt)
    base = Image.composite(_rgb(GRIME, size), base, joints.point(lambda p: p * 92 // 100))

    # 5. rubber: one streak field (long along the kerb), in the tyre band, patchy; levels are nested thresholds
    band = _u_mask(lambda u: _smooth01(u, 0.0, 0.07) * (1.0 - _smooth01(u, 0.34, 0.58)), w, h, pad)
    streak = _noise(rng, 140, 48, w, h, blur=0.5 * s)                               # ~1.8 px x 17 cm: long, thin
    smear = _levels(_noise(rng, 24, 64, w, h, blur=1.0 * s), 40, 215, 110, 255)     # ~4 cm x 12 cm smears
    patches = _levels(_noise(rng, 3, 20, w, h, blur=4 * s), 30, 225, 80, 255)       # 0.4 m: where it builds up
    field = ImageChops.multiply(ImageChops.multiply(ImageChops.multiply(streak, smear), patches), band)
    band_mask = band.point(lambda p: 255 if p > 128 else 0)
    soft = ImageChops.multiply(band, patches)
    alphas = [Image.new("L", size, 0)]
    for lv in range(1, rf.KERB_ATLAS_COLUMNS):
        t = _percentile(field, 1.0 - RUBBER_COVER[lv], band_mask)
        marks = _levels(field, t - 18, t + 30).point(lambda p, o=RUBBER_OPACITY[lv]: int(p * o))
        haze = soft.point(lambda p, k=RUBBER_HAZE[lv]: int(p * k))
        alphas.append(ImageChops.lighter(alphas[-1], ImageChops.lighter(marks, haze)))   # strict superset

    # 6. relief for the normal map: grain, grooves at the joints, chips a little lower; rubber fills the grain
    rel = _levels(_noise(rng, 192, 1536, w, h), 0, 255, 116, 140)
    rel = ImageChops.subtract(rel, joints.point(lambda p: p * 60 // 255))
    rel = ImageChops.subtract(rel, chips.point(lambda p: p * 14 // 255))
    rel_smooth = _wrap(rel, lambda im: im.filter(ImageFilter.GaussianBlur(1.5 * s + 0.5)))
    # GL: R = -dh/du (x right), G = +dh/drow (green points UP the image = +v_gl)
    kx = ImageFilter.Kernel((3, 3), [1, 0, -1, 2, 0, -2, 1, 0, -1], scale=NORMAL_STRENGTH, offset=128)
    ky = ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=NORMAL_STRENGTH, offset=128)
    blue = Image.new("L", size, 250)
    width = w * rf.KERB_ATLAS_COLUMNS
    diffuse = Image.new("RGB", (width, h))
    normal = Image.new("RGB", (width, h))
    for lv in range(rf.KERB_ATLAS_COLUMNS):
        col = Image.composite(_rgb(RUBBER, size), base, alphas[lv])
        diffuse.paste(col, (lv * w, 0))
        hgt = Image.composite(rel_smooth, rel, alphas[lv].point(lambda p: min(255, p * 3 // 2)))
        nx = _wrap(hgt, lambda im: im.filter(kx))
        ny = _wrap(hgt, lambda im: im.filter(ky))
        normal.paste(Image.merge("RGB", (nx, ny, blue)), (lv * w, 0))
    return {"diffuse": diffuse, "normal": normal, "alphas": alphas, "joints": joints, "chips": chips,
            "column_px": w, "pad_px": pad}


def encode(im, quality):
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, subsampling=0, optimize=True)
    return buf.getvalue()


def paint(scale=1.0, seed=SEED):
    """(diffuse jpg bytes, normal jpg bytes, render dict)"""
    r = render(scale, seed)
    return encode(r["diffuse"], JPEG_DIFFUSE_Q), encode(r["normal"], JPEG_NORMAL_Q), r


def md5(b):
    return hashlib.md5(b).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--check", action="store_true", help="compare a fresh paint with the files on disk (exit 1 on any difference)")
    ap.add_argument("--preview", default=None, help="also write a half-size PNG of the colour atlas here")
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    dif, nor, r = paint()
    rows = ((DIFFUSE_NAME, dif), (NORMAL_NAME, nor))
    bad = 0
    for name, data in rows:
        p = out / name
        if len(data) > MAX_BYTES:
            print(f"[kerb-tex] FAIL {name}: {len(data):,} B > {MAX_BYTES:,}")
            bad += 1
        if a.check:
            have = p.read_bytes() if p.exists() else b""
            same = md5(have) == md5(data)
            print(f"[kerb-tex] {name}: on disk {md5(have) if have else 'missing'}, fresh {md5(data)} -> {'same' if same else 'DIFFERENT'}")
            bad += 0 if same else 1
        else:
            out.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            print(f"[kerb-tex] wrote {p} ({len(data):,} B, md5 {md5(data)}, {r['diffuse'].size[0]}x{r['diffuse'].size[1]})")
    if a.preview:
        r["diffuse"].resize((r["diffuse"].size[0] // 2, r["diffuse"].size[1] // 2), Image.LANCZOS).save(a.preview)
        print(f"[kerb-tex] preview {a.preview}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

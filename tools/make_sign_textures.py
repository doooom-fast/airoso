"""Sign textures for the W1-6 pass (Kevin, 2026-10-10: arrow signs AT tight corners) — run once,
PNGs committed, not a ship step.

Two kinds of output, both deterministic (same pixels every run):

  1. the two 64x64 SOLIDS the shipped signs actually bind — solid_sign_yellow.png (255, 205, 0,
     the #FFCC00 Type III/IV sheeting convention; the 23 CFR 655 chromaticity centroid #D49400 is
     too dull in AC daylight) and solid_sign_black.png (20, 20, 20). The arrow is GEOMETRY
     (tools/author_signs_blend.py) because the kn5 prep overwrites every non-exempt mesh's UVs
     with a planar (x/4, y/4) projection, which would collapse a textured plate to a line — the
     same reason the lamps use solids. Bound by the pbr.TEXTURES keys SIGNPLATE / SIGNARROW.
  2. the full MUTCD artwork at 1024 px width, public-domain designs drawn procedurally (MUTCD
     Introduction para 04; FHWA SHS 2004 sheets 2-7/2-8/2-9): mutcd_w1-6r.png / mutcd_w1-6l.png
     (48x24 Large Arrow), mutcd_w1-7.png (Two-Direction Large Arrow), mutcd_w1-8l.png /
     mutcd_w1-8r.png (18x24 chevron, no border). RGBA with transparent rounded corners — NOT bound
     by anything today: to put them on a plate the prep must exempt the mesh prefix from its
     planar-UV pass and the material must sit in pbr.BILLBOARD (alpha test), else the transparent
     corners render black under ksPerPixel.

Written into every assets/textures the pipeline reads: airoso (source of record, assets/
licenses.json "generated, CC0-1.0") and engine-july (what the prep and the exporter stage from;
the kn5 add-on embeds only what the exporter copied into build/texture/).

    python tools/make_sign_textures.py [--out DIR ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

AIROSO = Path(__file__).resolve().parents[1]
ENGINE_JULY = AIROSO.parent / "engine-july"
OUT_DIRS = [AIROSO / "assets" / "textures"] + ([ENGINE_JULY / "assets" / "textures"] if ENGINE_JULY.is_dir() else [])

YELLOW = (255, 205, 0, 255)
BLACK = (20, 20, 20, 255)
SOLIDS = {"solid_sign_yellow.png": YELLOW[:3], "solid_sign_black.png": BLACK[:3]}
SS = 4                       # supersample, then LANCZOS down
# plates in inches: (w, h, corner radius, border inset, border width)
W16 = (48, 24, 1.875, 0.5, 0.75)
W18 = (18, 24, 1.5, None, None)
# W1-6R arrow on the 48x24 plate, origin bottom-left, y up (SHS sheet 2-7 / the PD Commons master)
ARROW_R = [(43.5, 12.0), (29.4, 21.0), (30.0, 15.33), (4.5, 15.33), (4.5, 8.67), (30.0, 8.67), (29.4, 3.0)]
# W1-7 double-headed arrow, tips at 5.0 and 43.0 of 48, heads ~11.5 long x 15.5 tall, shaft 6 tall
ARROW_2 = [(5.0, 12.0), (16.5, 19.75), (17.1, 15.0), (30.9, 15.0), (31.5, 19.75), (43.0, 12.0),
           (31.5, 4.25), (30.9, 9.0), (17.1, 9.0), (16.5, 4.25)]
# W1-8L chevron on the 18x24 plate, origin top-left, y DOWN (SHS sheet 2-9)
CHEVRON_L = [(17.25, 0.75), (9.0, 0.75), (0.75, 12.0), (9.0, 23.25), (17.25, 23.25), (9.0, 12.0)]


def plate(w_in, h_in, radius_in, border_inset, border_w, polys_in, width_px=1024, y_up=True):
    ppi = width_px * SS / w_in
    W, H = int(round(w_in * ppi)), int(round(h_in * ppi))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=radius_in * ppi, fill=YELLOW)
    if border_inset is not None:
        i0 = border_inset * ppi
        d.rounded_rectangle([i0, i0, W - 1 - i0, H - 1 - i0], radius=(radius_in - border_inset) * ppi,
                            outline=BLACK, width=int(round(border_w * ppi)))

    def px(p):
        return (p[0] * ppi, (h_in - p[1]) * ppi if y_up else p[1] * ppi)

    for poly in polys_in:
        d.polygon([px(p) for p in poly], fill=BLACK)
    return img.resize((W // SS, H // SS), Image.LANCZOS)


def mirror_x(poly, w_in):
    return [(w_in - x, y) for (x, y) in poly]


def artwork():
    w, h, r, bi, bw = W16
    out = {
        "mutcd_w1-6r.png": plate(w, h, r, bi, bw, [ARROW_R]),
        "mutcd_w1-6l.png": plate(w, h, r, bi, bw, [mirror_x(ARROW_R, w)]),
        "mutcd_w1-7.png": plate(w, h, r, bi, bw, [ARROW_2]),
    }
    w, h, r, bi, bw = W18
    out["mutcd_w1-8l.png"] = plate(w, h, r, bi, bw, [CHEVRON_L], y_up=False)
    out["mutcd_w1-8r.png"] = plate(w, h, r, bi, bw, [mirror_x(CHEVRON_L, w)], y_up=False)
    return out


def main():
    argv = sys.argv[1:]
    dirs = [Path(a) for a in argv[argv.index("--out") + 1:]] if "--out" in argv else OUT_DIRS
    imgs = {name: Image.new("RGB", (64, 64), rgb) for name, rgb in SOLIDS.items()}
    imgs.update(artwork())
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        for name, im in imgs.items():
            im.save(d / name, optimize=True)
        print("[sign-textures] %s: %s" % (d, ", ".join("%s %dx%d" % (n, im.size[0], im.size[1]) for n, im in imgs.items())))


if __name__ == "__main__":
    main()

"""Shared 2-D drawing for the street-furniture makers (ledger 0096): a self-made stroke alphabet, supersampled
canvases, and the write / --check tail for PNG outputs. Needs Pillow.

THE ALPHABET. Sign legends need letters, and every pixel has to be ours (CC0), so no font file is read: each glyph
is a handful of centre-line strokes (lines and elliptical arcs) drawn at a constant stroke width with square ends,
which is how the FHWA Standard Alphabets are built. The proportions follow Series C/D (letter width about half the
height, stroke about 1/6.5 of it). It is an APPROXIMATION of the Standard Alphabets, not their outlines: nothing was
traced. Upper case, digits, and a few marks only.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

SS = 4                       # supersample, then LANCZOS down (as tools/make_sign_textures.py)


def _arc(cx, cy, rx, ry, a0, a1, n=14):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _glyphs():
    """centre-line strokes in a box ``w`` wide and 1 tall (y up). Returns {char: (w, [stroke, ...])}"""
    w = 0.52
    h = w / 2
    stadium = _arc(h, 1 - h, h, h, 0, 180) + _arc(h, h, h, h, 180, 360) + [(w, 1 - h)]
    g = {
        "A": (w, [[(0, 0), (h, 1), (w, 0)], [(0.15 * w, 0.3), (0.85 * w, 0.3)]]),
        "B": (w, [[(0, 0), (0, 1), (w - 0.25, 1)] + _arc(w - 0.25, 0.76, 0.25, 0.24, 90, -90) + [(0, 0.52)],
                  [(w - 0.27, 0.52)] + _arc(w - 0.27, 0.26, 0.27, 0.26, 90, -90) + [(0, 0)]]),
        "C": (w, [_arc(h, 1 - h, h, h, 25, 180) + _arc(h, h, h, h, 180, 335)]),
        "D": (w, [[(0, 0), (0, 1), (w - 0.3, 1)] + _arc(w - 0.3, 0.7, 0.3, 0.3, 90, 0) + _arc(w - 0.3, 0.3, 0.3, 0.3, 0, -90) + [(0, 0)]]),
        "E": (0.9 * w, [[(0.9 * w, 1), (0, 1), (0, 0), (0.9 * w, 0)], [(0, 0.52), (0.72 * w, 0.52)]]),
        "F": (0.9 * w, [[(0.9 * w, 1), (0, 1), (0, 0)], [(0, 0.52), (0.72 * w, 0.52)]]),
        "G": (w, [_arc(h, 1 - h, h, h, 25, 180) + _arc(h, h, h, h, 180, 360) + [(w, 0.46), (0.55 * w, 0.46)]]),
        "H": (w, [[(0, 0), (0, 1)], [(w, 0), (w, 1)], [(0, 0.52), (w, 0.52)]]),
        "I": (0.0, [[(0, 0), (0, 1)]]),
        "J": (0.85 * w, [[(0.85 * w, 1), (0.85 * w, 0.22)] + _arc(0.425 * w, 0.22, 0.425 * w, 0.22, 0, -165)]),
        "K": (w, [[(0, 0), (0, 1)], [(w, 1), (0, 0.38)], [(0.3 * w, 0.58), (w, 0)]]),
        "L": (0.85 * w, [[(0, 1), (0, 0), (0.85 * w, 0)]]),
        "M": (0.66, [[(0, 0), (0, 1), (0.33, 0.22), (0.66, 1), (0.66, 0)]]),
        "N": (w, [[(0, 0), (0, 1), (w, 0), (w, 1)]]),
        "O": (w, [stadium]),
        "P": (w, [[(0, 0), (0, 1), (w - 0.25, 1)] + _arc(w - 0.25, 0.74, 0.25, 0.26, 90, -90) + [(0, 0.48)]]),
        "Q": (w, [stadium, [(0.55 * w, 0.26), (w + 0.03, -0.03)]]),
        "R": (w, [[(0, 0), (0, 1), (w - 0.25, 1)] + _arc(w - 0.25, 0.74, 0.25, 0.26, 90, -90) + [(0, 0.48)], [(0.5 * w, 0.48), (w, 0)]]),
        "S": (w, [_arc(h, 0.75, h, 0.25, 25, 270) + _arc(h, 0.25, h, 0.25, 90, -205)[1:]]),
        "T": (w, [[(0, 1), (w, 1)], [(h, 1), (h, 0)]]),
        "U": (w, [[(0, 1), (0, h)] + _arc(h, h, h, h, 180, 360) + [(w, 1)]]),
        "V": (w, [[(0, 1), (h, 0), (w, 1)]]),
        "W": (0.74, [[(0, 1), (0.17, 0), (0.37, 0.8), (0.57, 0), (0.74, 1)]]),
        "X": (w, [[(0, 0), (w, 1)], [(0, 1), (w, 0)]]),
        "Y": (w, [[(0, 1), (h, 0.45), (w, 1)], [(h, 0.45), (h, 0)]]),
        "Z": (w, [[(0, 1), (w, 1), (0, 0), (w, 0)]]),
        "0": (w, [stadium]),
        "1": (0.3 * w, [[(0, 0.8), (0.3 * w, 1), (0.3 * w, 0)]]),
        "2": (w, [_arc(h, 0.74, h, 0.26, 165, -40) + [(0, 0), (w, 0)]]),
        "3": (w, [_arc(h, 0.75, h, 0.25, 150, -90) + _arc(h, 0.25, h, 0.25, 90, -150)[1:]]),
        "4": (w, [[(0.75 * w, 0), (0.75 * w, 1), (0, 0.3), (w, 0.3)]]),
        "5": (w, [[(w, 1), (0.08 * w, 1), (0, 0.52)] + _arc(h, 0.3, h, 0.3, 135, -150)]),
        "6": (w, [_arc(h, 0.3, h, 0.3, 180, -180), [(0, 0.3), (0, 0.7)] + _arc(h, 0.7, h, 0.3, 180, 30)]),
        "7": (w, [[(0, 1), (w, 1), (0.3 * w, 0)]]),
        "8": (w, [_arc(h, 0.76, 0.46 * w, 0.24, 0, 360), _arc(h, 0.27, h, 0.27, 0, 360)]),
        "-": (0.6 * w, [[(0, 0.5), (0.6 * w, 0.5)]]),
        "/": (0.7 * w, [[(0, 0), (0.7 * w, 1)]]),
        ".": (0.0, [[(0, 0), (0, 0.001)]]),
        " ": (0.34, []),
    }
    w6, s6 = g["6"]
    g["9"] = (w6, [[(w6 - x, 1 - y) for x, y in s] for s in s6])
    return g


GLYPHS = _glyphs()
STROKE = 1 / 6.5             # stroke width as a share of the letter height
GAP = 0.19                   # clear space between letters, share of the height
OPEN_R, OPEN_L = "TAVWYLPF7/", "TAVWYJ7/"     # letters with open air on that side sit closer (a crude kerning)


def _gap(prev: str, ch: str) -> float:
    return GAP * (0.55 if (prev in OPEN_R or ch in OPEN_L) and " " not in (prev, ch) else 1.0)


def text_width(text: str, cap: float, squeeze: float = 1.0, stroke: float = STROKE) -> float:
    """width of ``text`` at letter height ``cap`` (any unit), outer edge to outer edge"""
    n = 0.0
    for i, ch in enumerate(text):
        w = GLYPHS[ch][0] * (1 - stroke) * squeeze
        n += w + (stroke if ch != " " else 0) + (_gap(text[i - 1], ch) * squeeze if i else 0)
    return n * cap


def draw_text(d: ImageDraw.ImageDraw, text: str, cx: float, y_top: float, cap: float, fill, squeeze: float = 1.0,
              max_w: float | None = None, stroke: float = STROKE, anchor: str = "c") -> float:
    """draw ``text`` (pixels, y down) with its top at ``y_top`` and its height ``cap``; ``max_w`` narrows the
    letters until the legend fits. Returns the squeeze used."""
    if max_w is not None and text_width(text, cap, squeeze, stroke) > max_w:
        fixed = text_width(text, cap, 0.0, stroke)                      # the strokes themselves do not narrow
        squeeze *= max(max_w - fixed, 0.0) / (text_width(text, cap, squeeze, stroke) - fixed)
    total = text_width(text, cap, squeeze, stroke)
    x = cx - total / 2 if anchor == "c" else (cx if anchor == "l" else cx - total)
    sw = stroke * cap
    inner = cap - sw
    for i, ch in enumerate(text):
        if i:
            x += _gap(text[i - 1], ch) * squeeze * cap
        w, strokes = GLYPHS[ch]
        w = w * (1 - stroke) * squeeze
        for s in strokes:
            pts = [(x + sw / 2 + (px / GLYPHS[ch][0] * w if GLYPHS[ch][0] else 0) * cap, y_top + sw / 2 + (1 - py) * inner) for px, py in s]
            thick_line(d, pts, sw, fill)
        x += w * cap + (sw if ch != " " else 0)
    return squeeze


def thick_line(d: ImageDraw.ImageDraw, pts, width: float, fill, round_ends: bool = False):
    """a polyline of constant width with square ends and round inner joints"""
    r = width / 2
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            d.rectangle([a[0] - r, a[1] - r, a[0] + r, a[1] + r], fill=fill)
            continue
        nx, ny = -dy / L * r, dx / L * r
        d.polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], fill=fill)
    joints = pts if round_ends else pts[1:-1]
    if len(pts) > 2 and math.dist(pts[0], pts[-1]) < 1e-6:
        joints = pts
    for p in joints:
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)


def pot(n: float, cap: int = 512) -> int:
    """nearest power of two (in log space), at most ``cap`` and at least 32 (L7: power-of-two textures)"""
    return int(min(cap, max(32, 2 ** round(math.log2(max(n, 1))))))


def finish(rgb: Image.Image, mask: Image.Image | None, size) -> Image.Image:
    """downsample a supersampled RGB drawing (and its coverage mask) to ``size``. The colour is NOT premultiplied:
    outside the mask the plate's own colour runs on, so an alpha-tested or an untested plate shows no dark fringe."""
    out = rgb.resize(size, Image.LANCZOS)
    if mask is None:
        return out
    out = out.convert("RGBA")
    out.putalpha(mask.resize(size, Image.LANCZOS))
    return out


def write_or_check_png(out_dir: Path, images: dict, argv, tag: str) -> int:
    """write the PNGs, or with --check compare the committed pixels (not the bytes: Pillow versions differ in how
    they compress and by a level or two in LANCZOS) and exit 1 when one is missing, resized or visibly different"""
    if "--check" in argv:
        bad = []
        for n, im in images.items():
            p = out_dir / n
            if not p.exists():
                bad.append(n + " (missing)")
                continue
            old = Image.open(p)
            if old.size != im.size or old.mode != im.mode:
                bad.append(n + " (size/mode)")
            elif max(ImageStat.Stat(ImageChops.difference(old, im)).mean) > 1.0:
                bad.append(n + " (pixels)")
        print(f"{tag} --check: " + ("differs: " + ", ".join(bad) if bad else f"{len(images)} committed textures match"))
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, im in images.items():
        im.save(out_dir / n, optimize=True)
    print(f"[{tag}] wrote {len(images)} textures to {out_dir}")
    return 0
